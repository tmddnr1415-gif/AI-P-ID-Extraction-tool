"""L56 — 작도 재현율: 분석한 묶음 → 그림 묶음(들여오기) → PDF → 다시 분석 → 원래 분석과 얼마나 같은가.

  PID_DATA_DIR=<데이터 폴더> python3 spike/draw_roundtrip.py <job …>  [--out <보고서.md>]

장마다 센다: 시트 이름 · 표 행 글(FM · 설명 · TO) · 블록 종류(기능) 수 · 블록의 입출력 단자 수 · 그물 수 · 매달린 선 끝 ·
FROM/TO 점검(FT_MISMATCH 수) · 매크로 → Typical 연결.  읽기만 한다 — 판정 코드는 분석기 그대로.
"""
from __future__ import annotations

import collections
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PID_LOGIC_WARM", "0")

from app.logic import analyse, draw, draw_sets, store  # noqa: E402


def _rows(s):
    out = {}
    for r in s.get("table") or []:
        if r.get("desc") or r.get("fm") or r.get("to"):
            out[(r["side"], r["n"])] = ((r.get("fm") or "").strip().upper(), (r.get("desc") or "").strip().upper(), (r.get("to") or "").strip().upper())
    return out


def _key(b):
    """비교 열쇠 — 기능 이름이 묶음마다 다르다 (ALM ↔ ANN · PUSH BUTTON ↔ PB) → 동작(logic)으로, 동작이 없으면 기능 이름."""
    lg = b.get("logic") or ""
    if lg and lg != "unknown":
        return lg
    return "?" + (b.get("func") or "")


def _funcs(s):
    return collections.Counter(_key(b) for b in s["blocks"].values())


def _io(s):
    c = collections.Counter()
    for p in s.get("ports") or []:
        f = _key(s["blocks"].get(p["block"], {}))
        c[(f, p["dir"])] += 1
    return c


def compare(orig, back):
    o_by = {s["sheet_no"]: s for s in orig["sheets"] if s.get("sheet_no")}
    b_by = {s["sheet_no"]: s for s in back["sheets"] if s.get("sheet_no")}
    rep = {"sheets_orig": len(o_by), "sheets_back": len(b_by), "sheets_same": len(set(o_by) & set(b_by)), "per": [],
           "sheets_lost": sorted(set(o_by) - set(b_by))[:20], "sheets_new": sorted(set(b_by) - set(o_by))[:20]}
    tot = collections.Counter()
    for no, s in o_by.items():
        t = b_by.get(no)
        row_o = _rows(s)
        row_b = _rows(t) if t else {}
        rows_ok = sum(1 for k, v in row_o.items() if row_b.get(k) == v)
        fo, fb = _funcs(s), _funcs(t) if t else collections.Counter()
        f_ok = sum(min(fo[k], fb[k]) for k in fo)
        io_o, io_b = _io(s), _io(t) if t else collections.Counter()
        io_ok = sum(min(io_o[k], io_b[k]) for k in io_o)
        mac_o = [(b.get("macro") or {}).get("sheet") for b in s["blocks"].values() if b.get("func") == "MACRO" and (b.get("macro") or {}).get("sheet")]
        mac_b = [(b.get("macro") or {}).get("sheet") for b in (t["blocks"].values() if t else []) if b.get("func") == "MACRO" and (b.get("macro") or {}).get("sheet")]
        mac_ok = sum(min(collections.Counter(mac_o)[k], collections.Counter(mac_b)[k]) for k in set(mac_o))
        ft_o = sum(1 for f in s.get("findings") or [] if f.get("code") == "FT_MISMATCH")
        ft_b = sum(1 for f in (t or {}).get("findings") or [] if f.get("code") == "FT_MISMATCH")
        per = {"sheet": no, "found": t is not None, "rows": (rows_ok, len(row_o)), "blocks": (f_ok, sum(fo.values()), sum(fb.values())),
               "io": (io_ok, sum(io_o.values()), sum(io_b.values())), "nets": (len(s.get("nets") or {}), len((t or {}).get("nets") or {})),
               "dangling": (len(s.get("dangling") or []), len((t or {}).get("dangling") or [])),
               "macro": (mac_ok, len(mac_o)), "ft_mismatch": (ft_o, ft_b),
               "missing_funcs": sorted((fo - fb).elements()), "extra_funcs": sorted((fb - fo).elements())}
        rep["per"].append(per)
        for k in ("rows", "blocks", "io", "macro"):
            tot[k + "_ok"] += per[k][0]
            tot[k + "_all"] += per[k][1]
        tot["nets_o"] += per["nets"][0]; tot["nets_b"] += per["nets"][1]
        tot["dang_o"] += per["dangling"][0]; tot["dang_b"] += per["dangling"][1]
        tot["ft_o"] += ft_o; tot["ft_b"] += ft_b
    rep["total"] = dict(tot)
    miss = collections.Counter()
    for per in rep["per"]:
        miss.update(per["missing_funcs"])
    rep["missing_funcs"] = miss.most_common(12)
    return rep


def run(job: str, keep_pdf: Path | None = None):
    d = store.root() / job
    orig = json.loads((d / "result.json").read_text(encoding="utf-8"))
    st = store.read_status(d)
    t0 = time.time()
    with tempfile.TemporaryDirectory() as td:
        os.environ["PID_DATA_DIR_DRAW"] = td
        # 들여오기는 저장소에 쓰지 않고 메모리에서 — from_sheet 만 쓴다
        docs = []
        typ_pages = set()
        for s in orig["sheets"]:
            for b in s["blocks"].values():
                m = b.get("macro") or {}
                if b.get("func") == "MACRO" and m.get("page") and not m.get("library"):
                    typ_pages.add(m["page"])
        for i, s in enumerate(sorted(orig["sheets"], key=lambda q: q["page"])):
            if s.get("library") or s["page"] >= 100000:
                continue
            doc = draw.from_sheet(s, s.get("sheet_no") or f"p{s['page']}", "roundtrip", "")
            doc["typical"] = s["page"] in typ_pages
            docs.append(doc)
        pdf = draw_sets.to_pdf_set(docs)
        if keep_pdf:
            keep_pdf.write_bytes(pdf)
        p = Path(td) / "set.pdf"
        p.write_bytes(pdf)
        back = analyse.analyse(str(p))
    rep = compare(orig, back)
    rep["job"] = job; rep["name"] = st.get("name"); rep["seconds"] = round(time.time() - t0, 1)
    rep["draw_docs"] = len(docs)
    return rep


def fmt(rep):
    t = rep["total"]
    def pct(a, b):
        return f"{100 * a / b:.1f}%" if b else "—"
    lines = [f"## {rep['name']} ({rep['job']}) — 시트 {rep['sheets_same']}/{rep['sheets_orig']} 이름 같음 · 그림 {rep['draw_docs']}장 · {rep['seconds']}초",
             f"- 표 행 글 같음 {t['rows_ok']}/{t['rows_all']} ({pct(t['rows_ok'], t['rows_all'])})",
             f"- 블록 종류 같음 {t['blocks_ok']}/{t['blocks_all']} ({pct(t['blocks_ok'], t['blocks_all'])})",
             f"- 블록 입출력 단자 같음 {t['io_ok']}/{t['io_all']} ({pct(t['io_ok'], t['io_all'])})",
             f"- 그물 {t['nets_b']}/{t['nets_o']} · 매달린 선 끝 {t['dang_b']}/{t['dang_o']} · FROM/TO 불일치 {t['ft_b']}/{t['ft_o']}",
             f"- 매크로 → Typical 연결 같음 {t['macro_ok']}/{t['macro_all']} ({pct(t['macro_ok'], t['macro_all'])})",
             f"- 못 읽은 블록 종류 (원래 → 되읽기 없음): {rep['missing_funcs']}",
             f"- 이름을 잃은 시트: {rep['sheets_lost']} · 새 이름: {rep['sheets_new']}"]
    bad = [p for p in rep["per"] if p["blocks"][0] < p["blocks"][1] or p["rows"][0] < p["rows"][1] or p["macro"][0] < p["macro"][1]]
    for p in bad[:12]:
        lines.append(f"  - {p['sheet']}: 행 {p['rows'][0]}/{p['rows'][1]} · 블록 {p['blocks'][0]}/{p['blocks'][1]} (되읽기 {p['blocks'][2]}) · 단자 {p['io'][0]}/{p['io'][1]} · 매크로 {p['macro'][0]}/{p['macro'][1]} · 빠짐 {p['missing_funcs'][:6]} · 더 읽힘 {p['extra_funcs'][:4]}")
    return "\n".join(lines)


if __name__ == "__main__":
    argv = sys.argv[1:]
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] not in ("--out", "--pdf"))]
    out = None
    if "--out" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--out") + 1])
    pdfdir = Path(sys.argv[sys.argv.index("--pdf") + 1]) if "--pdf" in sys.argv else None
    reports = []
    for job in args:
        rep = run(job, (pdfdir / f"{job}.pdf") if pdfdir else None)
        print(fmt(rep), flush=True)
        reports.append(rep)
    if out:
        out.write_text("\n\n".join(fmt(r) for r in reports) + "\n", encoding="utf-8")
        (out.with_suffix(".json")).write_text(json.dumps(reports, ensure_ascii=False, indent=1), encoding="utf-8")
