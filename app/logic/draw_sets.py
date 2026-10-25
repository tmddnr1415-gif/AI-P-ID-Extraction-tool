"""LOGIC 작도 묶음 (L56) — 여러 장을 한 묶음으로: 묶음 들여오기 · FROM/TO 잇기 · 다장 PDF · 묶음 되읽기 검증 · 크기 학습.

* 묶음 = 같은 `set` id 를 가진 그림들 (저장은 그림마다 그대로 · 장부 없음).  `order` 로 순서.
* FROM/TO 판정은 분석기의 `fromto.check` **그대로** — 그림의 표를 분석 결과 모양(가짜 시트)으로 넘긴다.  판정을 두 벌 두지 않는다.
* 매크로 팔레트 = 이 묶음의 Typical 그림(`typical`) + 학습 사전의 Typical (library.typicals).
"""
from __future__ import annotations

import json
import re
import statistics
import time
import uuid

import pymupdf

from . import draw, library
from .draw import PITCH, _txt

OLD_SHEET = re.compile(r"^[A-Z]+\d{3}[A-Z]?$")


def ref_text(sheet_no: str, n: int, sep: str | None = None) -> str:
    """FM/TO 칸에 적는 참조 — 옛 꼴 시트 이름(G031)은 `G031-81`, 그 밖은 `LD-001/2` (분석기 refs 가 둘 다 읽는다).
    sep 를 주면 그 구분자 (L62 — 묶음이 이미 쓰는 꼴을 따른다: 알다프라는 `FG_G-201-61`)."""
    if sep:
        return f"{sheet_no}{sep}{n}"
    return f"{sheet_no}-{n}" if OLD_SHEET.match(sheet_no or "") else f"{sheet_no}/{n}"


def ref_sep(docs: list) -> str | None:
    """L62 — 묶음의 FM/TO 칸이 시트 이름 뒤에 쓰는 구분자 중 가장 많은 것 (없으면 None — ref_text 의 기본 꼴)."""
    names = sorted({(d.get("sheet_no") or "").upper() for d in docs if d.get("sheet_no")}, key=len, reverse=True)
    cnt: dict = {}
    for d in docs:
        for side, f in (("left", "fm"), ("right", "to")):
            for r in (d.get(side) or {}).values():
                for part in str(r.get(f) or "").upper().split(","):
                    v = part.strip()
                    k = next((nm for nm in names if v.startswith(nm)), None)
                    c = v[len(k):len(k) + 1] if k else ""
                    if c in ("-", "/"):
                        cnt[c] = cnt.get(c, 0) + 1
    return max(cnt, key=cnt.get) if cnt else None


# ─────────────────────────── 묶음 ───────────────────────────

_SET_DOCS: dict = {}           # L65 — 묶음 → (그림 파일들의 도장, 그림 목록).  shared=True 는 고치지 않는 쪽(시뮬레이션)만 쓴다


def set_docs(sid: str, shared: bool = False) -> list:
    if shared:
        stamps = []
        for d in sorted(draw.root().iterdir()):
            try:
                st = (d / "drawing.json").stat()
            except OSError:
                continue
            stamps.append((d.name, st.st_mtime_ns, st.st_size, st.st_ino))
        stamps = tuple(stamps)
        hit = _SET_DOCS.get(sid)
        if hit and hit[0] == stamps:
            return hit[1]
        docs = set_docs(sid)
        if len(_SET_DOCS) > 16:
            _SET_DOCS.clear()
        _SET_DOCS[sid] = (stamps, docs)
        return docs
    out = []
    for d in sorted(draw.root().iterdir()):
        p = d / "drawing.json"
        if not d.is_dir() or not p.exists():
            continue
        doc = draw.read_doc(p)
        if doc and doc.get("set") == sid:
            out.append(doc)
    out.sort(key=lambda x: (x.get("order") or 0, x.get("sheet_no") or "", x.get("created") or 0))
    return out


def sets_listing() -> list:
    groups = {}
    for it in draw.listing():
        sid = it.get("set") or ""
        if not sid:
            continue
        g = groups.setdefault(sid, {"id": sid, "name": it.get("set_name") or "", "project": it.get("project") or "",
                                    "sheets": [], "updated": 0})
        g["sheets"].append({k: it.get(k) for k in ("id", "sheet_no", "title", "typical", "order", "blocks", "wires", "rows")})
        g["updated"] = max(g["updated"], it.get("updated") or 0)
    for g in groups.values():
        g["sheets"].sort(key=lambda x: (x.get("order") or 0, x.get("sheet_no") or ""))
        if not g["name"]:
            g["name"] = g["sheets"][0].get("sheet_no") or g["id"]
    return sorted(groups.values(), key=lambda g: -g["updated"])


def new_set(name: str) -> str:
    return uuid.uuid4().hex[:12]


def import_bundle(res: dict, name: str, author: str, project: str = "", job: str = "") -> dict:
    """분석한 묶음의 모든 시트를 이 양식의 그림으로 (사전 Typical 사본은 뺀다).  매크로가 이어진 시트는 `typical`."""
    sid = new_set(name)
    typ_pages = set()
    for s in res.get("sheets") or []:
        for b in s["blocks"].values():
            m = b.get("macro") or {}
            if b.get("func") == "MACRO" and m.get("page") and not m.get("library"):
                typ_pages.add(m["page"])
    docs = []
    for i, s in enumerate(sorted(res.get("sheets") or [], key=lambda q: q["page"])):
        if s.get("library") or s["page"] >= library.LIB_PAGE0:
            continue
        doc = draw.from_sheet(s, s.get("sheet_no") or f"p{s['page']}", author, project)
        doc.update({"set": sid, "set_name": _txt(name, 80) or "묶음", "order": i + 1, "typical": s["page"] in typ_pages,
                    "source": {"job": job, "page": s["page"], "sheet_no": s.get("sheet_no", "")}})
        draw.save_new(doc)
        docs.append(doc)
    return {"id": sid, "name": name, "sheets": len(docs), "typicals": sum(1 for d in docs if d["typical"])}


# ─────────────────────────── FROM / TO ───────────────────────────

def pseudo_sheets(docs: list) -> list:
    """그림의 표를 분석 결과 시트 모양으로 — fromto.check 가 그대로 읽는다 (행마다 at 는 없다)."""
    out = []
    for i, doc in enumerate(docs):
        N = doc["N"]
        table, rows = [], []
        for k, v in (doc.get("left") or {}).items():
            n = int(k)
            table.append({"side": "L", "n": n, "fm": v.get("fm", ""), "kks": v.get("kks", ""), "desc": v.get("desc", "")})
            if v.get("desc") or v.get("fm"):
                rows.append({"side": "L", "n": n, "fm": v.get("fm", ""), "desc": v.get("desc", "")})
        for k, v in (doc.get("right") or {}).items():
            n = int(k)
            table.append({"side": "R", "n": n, "to": v.get("to", ""), "kks": v.get("kks", ""), "desc": v.get("desc", "")})
            if v.get("desc") or v.get("to"):
                rows.append({"side": "R", "n": n, "to": v.get("to", ""), "desc": v.get("desc", "")})
        out.append({"page": i + 1, "sheet_no": doc.get("sheet_no") or "", "N": N, "table": table, "rows": rows,
                    "findings": [], "blocks": {}, "did": doc["id"]})
    return out


def links(docs: list) -> dict:
    """묶음 안 FROM/TO 연결 — 그림마다 {left: {n: {ref, ft}}, right: {n: {targets, ft}}} 와 찾은 것."""
    from . import fromto, refs as RF
    sheets = pseudo_sheets(docs)
    fromto.check(sheets)
    by_no = {s["sheet_no"]: s for s in sheets if s["sheet_no"]}
    out = {"docs": {}, "findings": [], "sheets": {s["sheet_no"]: s["did"] for s in sheets if s["sheet_no"]}}
    for s in sheets:
        L, R = {}, {}
        for r in s["rows"]:
            if r["side"] == "L":
                ref = r.get("ref")
                L[r["n"]] = {"ref": ({"sheet": ref["sheet"], "row": ref["row"], "src_row": ref.get("src_row"),
                                      "did": (by_no.get(ref["sheet"]) or {}).get("did"), "other": ref.get("other_bundle", False)} if ref else None),
                             "ft": r.get("ft")}
            else:
                tg = [{"sheet": a, "row": b, "did": (by_no.get(a) or {}).get("did")} for a, b in RF.find(r.get("to"), wide=True, known=by_no)]
                R[r["n"]] = {"targets": tg, "ft": r.get("ft"), "refs_in": r.get("refs_in") or []}
        out["docs"][s["did"]] = {"left": L, "right": R, "sheet_no": s["sheet_no"]}
        for f in s["findings"]:
            out["findings"].append({**f, "did": s["did"], "sheet_no": s["sheet_no"]})
    out["missing"] = missing_sheets(out)
    return out


def link_rows(from_doc: dict, n_out: int, to_doc: dict, n_in: int, author: str) -> dict:
    """보내는 그림의 오른쪽 n_out 행 TO ↔ 받는 그림의 왼쪽 n_in 행 FM 을 서로 가리키게 적는다 (비어 있는 칸만 · 설명은 없으면 베낀다).
    두 그림을 저장한다 — 같은 그림이면 한 번."""
    fs, ts = from_doc.get("sheet_no") or "", to_doc.get("sheet_no") or ""
    if not fs or not ts:
        raise ValueError("두 장 다 시트 이름이 있어야 잇습니다.")
    N1, N2 = from_doc["N"], to_doc["N"]
    if not (N1 < n_out <= 2 * N1) or not (1 <= n_in <= N2):
        raise ValueError("행 번호가 표 밖입니다.")
    r_out = from_doc.setdefault("right", {}).setdefault(str(n_out), {"desc": "", "kks": "", "to": ""})
    r_in = to_doc.setdefault("left", {}).setdefault(str(n_in), {"fm": "", "kks": "", "desc": ""})
    want_to, want_fm = ref_text(ts, n_in), ref_text(fs, n_out)
    changed = []
    if want_to.upper() not in (r_out.get("to") or "").upper():
        r_out["to"] = (r_out.get("to") + ", " + want_to).strip(", ") if r_out.get("to") else want_to
        changed.append("to")
    if (r_in.get("fm") or "").strip().upper() != want_fm.upper():
        r_in["fm"] = want_fm
        changed.append("fm")
    if not (r_in.get("desc") or "").strip() and (r_out.get("desc") or "").strip():
        r_in["desc"] = r_out["desc"]
        changed.append("desc→")
    elif not (r_out.get("desc") or "").strip() and (r_in.get("desc") or "").strip():
        r_out["desc"] = r_in["desc"]
        changed.append("desc←")
    draw.save(from_doc["id"], from_doc, author)
    if to_doc["id"] != from_doc["id"]:
        draw.save(to_doc["id"], to_doc, author)
    return {"from": {"did": from_doc["id"], "n": n_out, "to": r_out["to"]}, "to": {"did": to_doc["id"], "n": n_in, "fm": r_in["fm"]},
            "changed": changed}


def autolink(docs: list, did: str, author: str) -> dict:
    """저장 직후 — 이 장의 FM/TO 참조가 가리키는 상대 장의 칸을 채운다 (빈 칸만).  판정은 refs/fromto 와 같은 꼴 읽기."""
    from . import refs as RF
    by_id = {d["id"]: d for d in docs}
    me = by_id.get(did)
    if me is None:
        return {"changed": []}
    by_no = {d.get("sheet_no"): d for d in docs if d.get("sheet_no")}
    my_no = me.get("sheet_no") or ""
    changed = []
    if not my_no:
        return {"changed": []}
    N = me["N"]
    sep = ref_sep(docs)
    # 왼쪽 FM → 보내는 장의 오른쪽 행 TO 에 나를 적는다
    for k, v in list((me.get("left") or {}).items()):
        ref = RF.full(v.get("fm"), by_no)
        if not ref or ref[0] not in by_no:
            continue
        src = by_no[ref[0]]
        if src["id"] == did:
            continue
        r_out = src.setdefault("right", {}).setdefault(str(ref[1]), {"desc": "", "kks": "", "to": ""})
        want = ref_text(my_no, int(k), sep)
        if want.upper() not in (r_out.get("to") or "").upper():
            r_out["to"] = (r_out["to"] + ", " + want).strip(", ") if r_out.get("to") else want
            if not (r_out.get("desc") or "").strip() and (v.get("desc") or "").strip():
                r_out["desc"] = v["desc"]
            draw.save(src["id"], src, author)
            changed.append({"sheet": src.get("sheet_no"), "n": ref[1], "field": "to"})
    # 오른쪽 TO → 받는 장의 왼쪽 행 FM 에 나를 적는다
    for k, v in list((me.get("right") or {}).items()):
        for sh, n in RF.find(v.get("to"), wide=True, known=by_no):
            if sh not in by_no or by_no[sh]["id"] == did:
                continue
            dst = by_no[sh]
            if not (1 <= n <= dst["N"]):
                continue
            r_in = dst.setdefault("left", {}).setdefault(str(n), {"fm": "", "kks": "", "desc": ""})
            want = ref_text(my_no, int(k), sep)
            if (r_in.get("fm") or "").strip():
                continue                                   # 이미 적힌 FM 은 덮지 않는다 (틀렸으면 검증이 붉게 말한다)
            r_in["fm"] = want
            if not (r_in.get("desc") or "").strip() and (v.get("desc") or "").strip():
                r_in["desc"] = v["desc"]
            draw.save(dst["id"], dst, author)
            changed.append({"sheet": sh, "n": n, "field": "fm"})
    # L62 — 들어오는 쪽: 다른 장이 이미 이 장(이름)을 가리키고 있으면 이 장의 빈 칸을 채운다
    #   (그 장을 나중에 만들었거나 이름을 붙였을 때 — 미작성이던 참조가 저절로 이어진다)
    mine = False
    for o in docs:
        if o["id"] == did or not o.get("sheet_no"):
            continue
        ono = o["sheet_no"]
        for k, v in (o.get("right") or {}).items():          # 그 장의 TO → 이 장의 입력 행 FM
            for sh, n in RF.find(v.get("to"), wide=True, known=by_no):
                if sh != my_no or not (1 <= n <= N):
                    continue
                r_in = me.setdefault("left", {}).setdefault(str(n), {"fm": "", "kks": "", "desc": ""})
                if (r_in.get("fm") or "").strip():
                    continue
                r_in["fm"] = ref_text(ono, int(k), sep)
                if not (r_in.get("desc") or "").strip() and (v.get("desc") or "").strip():
                    r_in["desc"] = v["desc"]
                mine = True
                changed.append({"sheet": my_no, "n": n, "field": "fm", "from": ono})
        for k, v in (o.get("left") or {}).items():           # 그 장의 FM → 이 장의 출력 행 TO
            ref = RF.full(v.get("fm"), by_no)
            if not ref or ref[0] != my_no or not (N < ref[1] <= 2 * N):
                continue
            r_out = me.setdefault("right", {}).setdefault(str(ref[1]), {"desc": "", "kks": "", "to": ""})
            want = ref_text(ono, int(k), sep)
            if want.upper() in (r_out.get("to") or "").upper():
                continue
            r_out["to"] = (r_out["to"] + ", " + want).strip(", ") if r_out.get("to") else want
            if not (r_out.get("desc") or "").strip() and (v.get("desc") or "").strip():
                r_out["desc"] = v["desc"]
            mine = True
            changed.append({"sheet": my_no, "n": ref[1], "field": "to", "from": ono})
    if mine:
        draw.save(did, me, author)
    return {"changed": changed}


def missing_sheets(lk: dict) -> dict:
    """L62 — 묶음에 아직 없는 시트를 가리키는 FM/TO (시트 이름 → 그 자리들).  links() 결과에서 센다."""
    out = {}
    for did, d in (lk.get("docs") or {}).items():
        for n, v in (d.get("left") or {}).items():
            ref = v.get("ref")
            if ref and not ref.get("did") and ref.get("sheet"):
                out.setdefault(ref["sheet"], []).append({"did": did, "sheet_no": d.get("sheet_no"), "side": "left", "n": n, "row": ref.get("row")})
        for n, v in (d.get("right") or {}).items():
            for t in v.get("targets") or []:
                if not t.get("did") and t.get("sheet"):
                    out.setdefault(t["sheet"], []).append({"did": did, "sheet_no": d.get("sheet_no"), "side": "right", "n": n, "row": t.get("row")})
    return out


# ─────────────────────────── 매크로 팔레트 ───────────────────────────

def macro_types(docs: list) -> list:
    """이 묶음의 Typical 그림 + 학습 사전의 Typical → 팔레트 항목 (이름 · 단자)."""
    out = []
    for d in docs:
        if not d.get("typical"):
            continue
        ins, outs = draw.macro_pins(d)
        out.append({"typ": d.get("sheet_no") or "", "did": d["id"], "title": d.get("title") or d.get("sheet_no") or "",
                    "pins_in": ins, "pins_out": outs, "from": "이 묶음"})
    lib = library.load()
    for tid, ty in (lib.get("typicals") or {}).items():
        st = ty.get("sheet") or {}
        ins = [{"name": _txt(r.get("abv") or r.get("kks") or "".join(w[0] for w in (r.get("desc") or "").split() if w[:1].isalnum())[:8], 14),
                "row": r["n"]} for r in st.get("table", []) if r["side"] == "L" and r.get("desc")]
        outs = [{"name": _txt(r.get("abv") or r.get("kks") or "".join(w[0] for w in (r.get("desc") or "").split() if w[:1].isalnum())[:8], 14),
                 "row": r["n"]} for r in st.get("table", []) if r["side"] == "R" and r.get("desc")]
        if ins and outs:
            out.append({"typ": f"lib:{tid}", "did": None, "title": ty.get("title") or ty.get("sheet_no") or tid,
                        "pins_in": ins[:draw.MAX_PINS], "pins_out": outs[:draw.MAX_PINS],
                        "from": f"공통 Typical 사전 · {ty.get('from', '')}{' · 고침' if ty.get('origin') == 'user' else ''}",
                        "sheet": {"sheet_no": st.get("sheet_no") or ty.get("sheet_no", "")}})   # L63 — 시트 통째는 보내지 않는다 (24개면 2MB)
    return out


def typical_doc_from_library(tid: str, name: str, author: str, project: str, sid: str, order: int) -> dict | None:
    """사전 Typical 시트를 이 묶음의 그림으로 들여온다 (매크로를 놓으면 그 내부 동작이 묶음 안에 있어야 분석기가 잇는다)."""
    ty = (library.load().get("typicals") or {}).get(tid)
    if not ty or not (ty.get("sheet") or ty.get("doc")):
        return None
    if ty.get("doc"):                                 # L63 — 사람이 고친(또는 씨앗의) 작도 그림을 그대로
        base = ty["doc"]
        doc = draw.new_doc(name or ty.get("sheet_no") or tid, author, project, int(base.get("N") or draw.N_DEFAULT))
        doc.update({k: v for k, v in base.items() if k not in ("id", "name", "history", "author", "created", "updated", "saves", "set", "set_name", "order", "source", "project")})
    else:
        doc = draw.from_sheet(ty["sheet"], name or ty.get("sheet_no") or tid, author, project)
    doc.update({"set": sid, "order": order, "typical": True, "sheet_no": ty.get("sheet_no") or doc.get("sheet_no"),
                "title": ty.get("title") or doc.get("title"), "source": {"library": tid, "from": ty.get("from", "")}})
    draw.save_new(doc)
    return doc


# ─────────────────────────── 다장 PDF · 되읽기 ───────────────────────────

def to_pdf_set(docs: list) -> bytes:
    pdf = pymupdf.open()
    for d in docs:
        draw.draw_page(pdf, d)
    pdf.set_metadata({"title": (docs[0].get("set_name") if docs else "") or "LOGIC", "producer": "PID LOGIC 작도"})
    return pdf.tobytes()


def verify_set(docs: list) -> dict:
    """묶음을 한 PDF 로 내보내 분석기에 넣고 장마다 비교 + FROM/TO 점검(분석기의 것) + 매크로 ↔ Typical 연결."""
    import tempfile
    from pathlib import Path
    from . import analyse as AN
    pdf = to_pdf_set(docs)
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "set.pdf"
        p.write_bytes(pdf)
        try:
            res = AN.analyse(str(p))
        except AN.NotLogic as e:
            return {"ok": False, "why": str(e), "sheets": []}
    by_page = {s["page"]: s for s in res["sheets"]}
    out = {"ok": True, "sheets": [], "fromto": [], "seconds": res.get("seconds"), "read": len(res["sheets"]), "drawn": len(docs)}
    for i, d in enumerate(docs):
        s = by_page.get(i + 1)
        if s is None:
            out["sheets"].append({"did": d["id"], "sheet_no": d.get("sheet_no"), "ok": False, "why": "분석기가 이 장을 LOGIC 시트로 읽지 못했습니다"})
            out["ok"] = False
            continue
        c = draw.compare_sheet(d, s)
        c["did"] = d["id"]
        out["sheets"].append(c)
        out["ok"] = out["ok"] and c["ok"]
        for f in s.get("findings") or []:
            if f.get("code", "").startswith("FT_"):
                out["fromto"].append({**f, "did": d["id"], "sheet_no": d.get("sheet_no")})
    out["fromto_bad"] = sum(1 for f in out["fromto"] if f["code"] == "FT_MISMATCH")
    return out


# ─────────────────────────── 크기 · 배치 학습 ───────────────────────────

_STYLE_KIND = {"AND": "AND", "OR": "OR", "NAND": "NAND", "NOR": "NOR", "NOT": "NOT", "GT": "GT", "DT": "DT", "PD": "PD",
               "VOTE": "VOTE", "MEMORY": "MEMORY", "PB": "PB", "PUSH BUTTON": "PB", "ANN": "ANN", "ALM": "ANN", "SOE": "SOE",
               "CONNECTOR": "CONN", "SIGNAL": "BOX", "DISPLAY": "BOX", "MACRO": "MACRO"}


def learn_style(results: list, sources: list | None = None) -> dict:
    """분석한 묶음들에서 기호 크기(행 간격 배율) · 매크로 단자 간격 · 블록이 서는 세로 열(LOGIC 폭의 비율)을 잰다.
    값은 중앙값 — 어느 한 묶음의 수가 아니라 여러 묶음이 같이 말하는 수.  기호 모양은 바꾸지 않는다."""
    sizes = {}
    cols = []
    pin_gap = []
    for res in results:
        for s in res.get("sheets") or []:
            P = s.get("pitch") or 0
            lg = s.get("logic") or None
            if not P or not lg:
                continue
            W_ = max(1.0, lg[2] - lg[0])
            for bid, b in (s.get("blocks") or {}).items():
                k = _STYLE_KIND.get(b.get("func") or "")
                x0, y0, x1, y1 = b["bbox"]
                if k:
                    sizes.setdefault(k, []).append(((x1 - x0) / P, (y1 - y0) / P))
                if k and k not in ("MACRO", "CONN"):
                    cols.append(((x0 + x1) / 2 - lg[0]) / W_)
                if k == "MACRO":
                    ys = sorted(pt["at"][1] for pt in s.get("ports") or [] if pt["block"] == bid and pt["dir"] == "in")
                    pin_gap += [(b2 - a) / P for a, b2 in zip(ys, ys[1:]) if b2 - a > 0.3 * P]
    out = {"_about": "LOGIC 작도 기호 크기 · 배치 (L56) — 분석한 묶음에서 잰 중앙값 (행 간격 P 배율). spike/draw_style_learn.py 가 다시 만든다.",
           "sources": sources or [], "at": time.strftime("%Y-%m-%d %H:%M:%S"), "sizes": {}, "columns": [], "macro_pin_gap_p": None}
    for k, v in sizes.items():
        if len(v) < 3:
            continue
        out["sizes"][k] = {"w_p": round(statistics.median(a for a, _ in v), 2), "h_p": round(statistics.median(b for _, b in v), 2), "n": len(v)}
    if cols:
        # 블록 가운데가 서는 열 — 히스토그램(20칸)의 봉우리 (이웃보다 높고 전체 평균 이상)
        bins = [0] * 20
        for c in cols:
            bins[min(19, max(0, int(c * 20)))] += 1
        mean = sum(bins) / 20
        out["columns"] = [round((i + 0.5) / 20, 3) for i in range(20) if bins[i] >= mean and bins[i] >= bins[i - 1 if i else 0] and bins[i] >= (bins[i + 1] if i < 19 else 0)]
        out["columns_hist"] = bins
    if pin_gap:
        out["macro_pin_gap_p"] = round(statistics.median(pin_gap), 2)
    return out
