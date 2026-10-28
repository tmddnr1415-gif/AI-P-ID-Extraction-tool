"""hotfix82 — VOC 함의 O/X 평가 · 마크업을 **프로젝트 정답지**로 모으고, 결과를 그 정답지로 잰다.

    python3 spike/verdict_set.py build [--inbox 경로 …] [--out out/verdicts]      # 프로젝트마다 out/verdicts/<이름>.json
    python3 spike/verdict_set.py score <결과.json | 회귀 blob> <정답지.json>        # 그 결과가 정답지를 얼마나 지키나

정답지의 한 줄 = 도면번호 · TYPE · (태그 또는 자리) · 판정.  판정은 셋 —
  O       사람이 "식별되어야 한다" 고 적은 행 (O/X 평가 O)                 → 다음 결과에도 있어야 한다
  X       "식별되면 안 된다" (O/X 평가 X · 마크업 오검출 표시)             → 다음 결과에 없어야 한다
  MISSED  프로그램이 못 읽어 사람이 더한 행 (마크업 누락 추가)             → 다음 결과가 스스로 읽어야 한다

같은 항목(도면번호·TYPE·태그/자리)에 여러 번 적혔으면 **나중 것**이 이긴다.  정답지는 재는 자이지 규칙이
아니다 — 판정 코드는 이 파일을 읽지 않는다 (§9 · 44회차 [E-5]).  이 모듈은 import 해도 아무 일도 하지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out" / "verdicts"

SOURCE_VERDICT = {"VERDICT": None, "MARKUP_REJECT": "X", "MARKUP_ADD": "MISSED"}


def _ident(i: dict) -> dict:
    rect = i.get("rect")
    return {"drawing_no": str(i.get("drawing_no") or ""), "page_no": i.get("page_no"),
            "type": str(i.get("type") or ""), "valve_type": str(i.get("valve_type") or ""),
            "tag_no": str(i.get("tag_no") or ""), "tab": i.get("tab"),
            "rect": [round(float(v), 1) for v in rect] if rect and len(rect) == 4 else None}


def _key(it: dict) -> tuple:
    """같은 항목인가 — 도면번호 · TYPE · 태그(있으면) · 자리(없으면 사각형 중심을 5pt 로 묶는다)."""
    if it["tag_no"]:
        return (it["drawing_no"], it["type"], "tag", it["tag_no"])
    r = it["rect"] or [0, 0, 0, 0]
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    return (it["drawing_no"] or f"p{it['page_no']}", it["type"], "at", round(cx / 5), round(cy / 5))


def items_of(rec: dict) -> list[dict]:
    """VOC 한 건 → 정답지 줄들.  VERDICT 는 행마다 O/X, 마크업은 그 행 하나."""
    src = str(rec.get("source") or "")
    if src not in SOURCE_VERDICT:
        return []
    ctx = rec.get("context") or {}
    base = {"voc_id": rec.get("id"), "author": rec.get("author") or "", "at": rec.get("created_ts") or 0,
            "project": ctx.get("project") or "", "revision": ctx.get("revision") or "",
            "pdf_sha256": ctx.get("pdf_sha256") or "", "source": src}
    out = []
    if src == "VERDICT":
        for row in rec.get("rows") or []:
            v = str(row.get("verdict") or "").upper()
            if v not in ("O", "X"):
                continue
            it = _ident(row.get("identity") or {}); it.update(base); it["verdict"] = v
            it["qty_verdict"] = str(row.get("qty_verdict") or "").upper() or ""   # 수량 O/X (식별 VOC 탭)
            it["note"] = str(row.get("note") or "")
            bb = row.get("body_basis") or {}
            if bb.get("body_source"):
                it["body_source"] = bb.get("body_source"); it["exemplar"] = bb.get("exemplar") or ""
                it["kind"] = bb.get("kind") or ""
            out.append(it)
        return out
    v = SOURCE_VERDICT[src]
    rows = rec.get("rows") or []
    if rows:
        it = _ident(rows[0].get("identity") or {})
    else:
        mk = (rec.get("markup") or {}).get("values") or {}
        it = _ident({"drawing_no": ctx.get("drawing_no"), "page_no": ctx.get("page_no"), "rect": rec.get("rect"),
                     "type": mk.get("type"), "tag_no": mk.get("tag_no"), "tab": (rec.get("markup") or {}).get("tab")})
    if not it["type"] and not it["rect"]:
        return []
    it.update(base); it["verdict"] = v
    return [it]


def build(recs, *, built_at: float | None = None) -> dict[str, dict]:
    """VOC 기록들 → {프로젝트: 정답지}.  같은 항목은 나중 것이 이긴다."""
    by: dict[str, dict[tuple, dict]] = {}
    seen_voc: dict[str, set] = {}
    for rec in sorted(recs, key=lambda r: r.get("created_ts") or 0):
        for it in items_of(rec):
            proj = it["project"] or "(프로젝트 없음)"
            by.setdefault(proj, {})[_key(it)] = it
            seen_voc.setdefault(proj, set()).add(it["voc_id"])
    out = {}
    now = built_at if built_at is not None else time.time()
    for proj, items in by.items():
        lst = sorted(items.values(), key=lambda x: (x["drawing_no"], x["page_no"] or 0, x["type"], x["tag_no"], str(x["rect"])))
        counts = {"O": 0, "X": 0, "MISSED": 0}
        for it in lst:
            counts[it["verdict"]] += 1
        out[proj] = {"project": proj, "built_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
                     "vocs": len(seen_voc[proj]), "counts": counts, "items": lst}
    return out


def _row_match(it: dict, row: dict) -> bool:
    if str(row.get("type") or "") != it["type"]:
        return False
    if it["drawing_no"] and str(row.get("drawing_no") or "") != it["drawing_no"]:
        return False
    if not it["drawing_no"] and row.get("page_no") != it["page_no"]:
        return False
    rt = str(row.get("tag_no") or "")
    if it["tag_no"] and rt:
        return rt == it["tag_no"]
    r, q = it["rect"], row.get("rect")
    if not r or not q or len(q) != 4:
        return bool(it["tag_no"]) is False and not q and not r      # 둘 다 자리가 없으면 같은 TYPE 뿐 — 아니다
    cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
    reach = max(r[2] - r[0], r[3] - r[1], 1.0)
    qx, qy = (q[0] + q[2]) / 2, (q[1] + q[3]) / 2
    return abs(cx - qx) <= reach and abs(cy - qy) <= reach


def score(rows, vset: dict) -> dict:
    """결과 행들이 정답지를 얼마나 지키는가.  지운 행(deleted/removed)은 결과에 없는 것으로 본다."""
    live = [r for r in rows if not r.get("deleted") and not r.get("removed")]
    out = {"O": {"n": 0, "kept": 0, "lost": []}, "X": {"n": 0, "excluded": 0, "back": []},
           "MISSED": {"n": 0, "found": 0, "still": []}}
    for it in vset.get("items") or []:
        hit = any(_row_match(it, r) for r in live)
        label = f"{it['drawing_no'] or 'p%s' % it['page_no']} {it['type']} {it['tag_no'] or it['rect']}"
        v = it["verdict"]
        out[v]["n"] += 1
        if v == "O":
            if hit: out["O"]["kept"] += 1
            else: out["O"]["lost"].append(label)
        elif v == "X":
            if not hit: out["X"]["excluded"] += 1
            else: out["X"]["back"].append(label)
        else:
            if hit: out["MISSED"]["found"] += 1
            else: out["MISSED"]["still"].append(label)
    total = sum(out[v]["n"] for v in out)
    good = out["O"]["kept"] + out["X"]["excluded"] + out["MISSED"]["found"]
    out["total"] = total
    out["agree"] = good
    out["pct"] = round(100.0 * good / total, 1) if total else None
    return out


def summary_line(sc: dict) -> str:
    if not sc or not sc.get("total"):
        return "정답지 없음"
    o, x, m = sc["O"], sc["X"], sc["MISSED"]
    return (f"일치 {sc['agree']}/{sc['total']} ({sc['pct']}%) — O 유지 {o['kept']}/{o['n']}"
            f" · X 제외 {x['excluded']}/{x['n']} · 누락 회수 {m['found']}/{m['n']}")


def verdict_file(project: str, out_dir: Path = OUT_DIR) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_ ." else "_" for c in project).strip() or "project"
    return out_dir / f"{safe}.json"


def load_rows(path: Path) -> list:
    blob = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(blob, dict) and "result" in blob:
        blob = blob["result"]
    return blob["rows"] if isinstance(blob, dict) else blob


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--inbox", action="append"); b.add_argument("--out", default=str(OUT_DIR))
    s = sub.add_parser("score"); s.add_argument("result"); s.add_argument("verdicts")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        sys.path.insert(0, str(ROOT))
        import voc as voc_cli                      # spike/voc.py — inbox 자리 규칙 하나
        from app import voc
        items = voc.scan(voc_cli.inboxes(a.inbox))
        sets = build(items.values())
        out_dir = Path(a.out); out_dir.mkdir(parents=True, exist_ok=True)
        if not sets:
            print("VOC 함에 O/X 평가 · 마크업이 없습니다."); return 0
        for proj, vs in sets.items():
            f = verdict_file(proj, out_dir)
            f.write_text(json.dumps(vs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            c = vs["counts"]
            print(f"{proj}: 정답지 {len(vs['items'])}줄 (O {c['O']} · X {c['X']} · 누락 {c['MISSED']}) · VOC {vs['vocs']}건 → {f}")
        return 0
    vs = json.loads(Path(a.verdicts).read_text(encoding="utf-8"))
    sc = score(load_rows(Path(a.result)), vs)
    print(summary_line(sc))
    for name, lst in (("식별되어야 하는데 없어진 행", sc["O"]["lost"]), ("빠져야 하는데 다시 선 행", sc["X"]["back"]),
                      ("여전히 못 읽는 행", sc["MISSED"]["still"])):
        if lst:
            print(f"  {name} {len(lst)}: " + " | ".join(lst[:20]) + (" …" if len(lst) > 20 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
