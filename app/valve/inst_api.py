"""Instrument datasheet review — API (valve40).  Same server, same project spaces, same Document Management as the
Valve tool; the instrument rows live in their own table so the Valve review is untouched.

Upload kinds (Document Management):  instrument (Instrument Datasheet PDF) · linelist (Process Line List xlsx) ·
instlist (Instrument Index / IO List PDF — which one is read from the page).
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.valve import instlists, instreview, instrument, linelist, store

router = APIRouter()
SCHEMA = """
CREATE TABLE IF NOT EXISTS inst_sheet (id INTEGER PRIMARY KEY, project_id INTEGER, document_id INTEGER, form_id TEXT,
  kind TEXT, tag TEXT, tag_key TEXT, doc_no TEXT, rev TEXT, rev_date TEXT, pages TEXT, sheet TEXT, test_data INTEGER,
  status TEXT DEFAULT 'Not Reviewed', created_at TEXT);
CREATE INDEX IF NOT EXISTS inst_tag ON inst_sheet(project_id, tag_key);
"""
_READY: set = set()
KIND_NAMES = {"ft": "Flow Transmitter", "pt": "Pressure / DP Transmitter", "lt": "Level Transmitter (DP)",
              "gwr": "Level Transmitter (GWR/Radar)", "tt": "Temperature Transmitter", "tg": "Temperature Gauge",
              "pg": "Pressure Gauge", "dpg": "DP Gauge", "mlg": "Magnetic Level Gauge", "ro": "Restriction Orifice",
              "analyzer": "Analyzer", "cv": "Control Valve", "onoff": "On-Off Valve (SDV/BDV)", "psv": "Pressure Safety Valve"}
ORDER = ["ft", "pt", "lt", "gwr", "tt", "tg", "pg", "dpg", "mlg", "ro", "analyzer", "cv", "onoff", "psv"]
_DOCNO = re.compile(r"\b[0-9A-Z]{2,5}-[0-9A-Z]{2,4}-IN-[A-Z]{2,4}-\d{4,6}\b|\bTEST-IN-DS-\d{3,5}\b")
_CTX: dict[tuple, tuple] = {}


def con_ready():
    con = store.connect()
    key = str(store.root())
    if key not in _READY:
        con.executescript(SCHEMA)
        con.commit()
        _READY.add(key)
    return con


def _data_dir(name: str) -> Path:
    p = store.root() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


# ── reading uploads (called from api._process) ─────────────────────────────────────────────────────────────────
def process_doc(con, pid: int, doc_id: int, kind: str, name: str, path: Path, by: str) -> dict:
    con.executescript(SCHEMA)
    if kind == "instrument":
        res = instrument.read_pdf(str(path), filename=name)
        n_new, tags = 0, []
        for sh in res["sheets"]:
            tb = sh.get("title_block") or {}
            doc_no = tb.get("doc_no") or ""
            if not doc_no:                                   # forms without a title block: the file name / page text
                m = _DOCNO.search(Path(name).stem.upper()) or _DOCNO.search(sh.get("tag_raw") or "")
                doc_no = m.group(0) if m else ""
            ts = sh.get("tags") or [f"(Tag 없음 p.{sh['pages'][0]})"]
            slim = {k: sh[k] for k in ("form_id", "kind", "title", "pages", "identify", "title_block", "rows", "shift", "tag_raw", "tags", "test_data") if k in sh}
            for t in ts:
                tk = instrument.tag_key(t)
                dup = store.one(con, "SELECT id FROM inst_sheet WHERE project_id=? AND document_id=? AND tag_key=? AND rev=?",
                                pid, doc_id, tk, tb.get("rev") or "")
                if dup:
                    con.execute("UPDATE inst_sheet SET sheet=?, form_id=?, kind=? WHERE id=?", (store.J(slim), sh["form_id"], sh["kind"], dup["id"]))
                    continue
                con.execute("INSERT INTO inst_sheet(project_id, document_id, form_id, kind, tag, tag_key, doc_no, rev, rev_date, pages,"
                            " sheet, test_data, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (pid, doc_id, sh["form_id"], sh["kind"], t, tk, doc_no, tb.get("rev") or "", tb.get("date") or "",
                             store.J(sh["pages"]), store.J(slim), int(bool(sh.get("test_data"))), store.now()))
                n_new += 1
                tags.append(t)
        forms = {}
        for sh in res["sheets"]:
            forms[sh["kind"]] = forms.get(sh["kind"], 0) + 1
        unk = max(0, int(res.get("pages") or 0) - sum(len(sh["pages"]) for sh in res["sheets"]))
        note = " · ".join(f"{KIND_NAMES.get(k, k)} {n}장" for k, n in forms.items()) or "알아본 양식 없음"
        return {"datasheets": len(res["sheets"]), "tags": tags, "forms": forms, "unidentified_pages": unk,
                "note": f"Instrument Datasheet {len(res['sheets'])}장 · Tag {len(tags)}개 — {note}"}
    if kind == "linelist":
        parsed = linelist.read(Path(path).read_bytes(), name)
        store.write_json(_data_dir("linelist") / f"{doc_id}.json", parsed)
        return {"lines": len(parsed["lines"]), "sheets": [s["sheet"] for s in parsed["sheets"]],
                "note": f"Line {len(parsed['lines'])}개 읽음 ({' · '.join(s['sheet'] for s in parsed['sheets']) or '표 없음'})"}
    if kind == "instlist":
        parsed = instlists.read_pdf(str(path))
        if not parsed["kind"]:
            raise ValueError("Instrument Index 도 IO List 도 아닌 PDF 입니다 (머리글 'Instrument Index' / 'IO LIST' 를 찾지 못함)")
        store.write_json(_data_dir("instlist") / f"{doc_id}.json", parsed)
        nm = "Instrument Index" if parsed["kind"] == "instrument_index" else "IO List"
        return {"list_kind": parsed["kind"], "tags": parsed["n_tags"], "rev": parsed["rev"],
                "note": f"{nm} · Tag {parsed['n_tags']}개 · Rev {parsed['rev'] or '-'}"}
    raise ValueError(kind)


# ── project context: PDS · PMS · Line List · Lists ─────────────────────────────────────────────────────────────
def _docs(con, pid, kind):
    return store.rows(con, "SELECT id, filename, uploaded_at, info FROM document WHERE project_id=? AND kind=? AND status='done' ORDER BY id", pid, kind)


def _load(sub: str, doc_id: int):
    p = store.root() / sub / f"{doc_id}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _merged_linelist(con, pid):
    docs = _docs(con, pid, "linelist")
    lines, names = [], []
    for d in docs:
        ll = _load("linelist", d["id"])
        if ll:
            names.append(d["filename"])
            lines += [dict(x, file=d["filename"]) for x in ll["lines"]]
    if not lines:
        return None, None
    by_key, by_core = {}, {}
    for i, ln in enumerate(lines):
        by_key[ln["key"]] = i                              # newer upload wins
        if ln["core"]:
            by_core.setdefault(ln["core"], [])
            by_core[ln["core"]] = [j for j in by_core[ln["core"]] if lines[j]["key"] != ln["key"]] + [i]
    return {"lines": lines, "by_key": by_key, "by_core": by_core}, {"filename": " · ".join(names), "kind": "linelist"}


def _lists(con, pid) -> dict:
    out = {}
    for d in _docs(con, pid, "instlist"):
        L = _load("instlist", d["id"])
        if not L:
            continue
        cur = out.setdefault(L["kind"], {"by_tag": {}, "files": [], "rev": "", "doc_no": ""})
        cur["by_tag"].update(L["by_tag"])
        cur["files"].append(d["filename"])
        cur["rev"], cur["doc_no"] = L.get("rev") or cur["rev"], L.get("doc_no") or cur["doc_no"]
    return out


def _required(con, pid) -> dict:
    r = store.one(con, "SELECT value FROM project_setting WHERE project_id=? AND key='inst.required'", pid)
    try:
        return json.loads(r["value"]) if r and r["value"] else {}
    except ValueError:
        return {}


def _ver(con, pid) -> tuple:
    a = store.one(con, "SELECT COUNT(*) n, MAX(id) m FROM document WHERE project_id=? AND status='done'", pid)
    b = store.one(con, "SELECT COUNT(*) n, MAX(id) m FROM inst_sheet WHERE project_id=?", pid)
    s = store.one(con, "SELECT value FROM project_setting WHERE project_id=? AND key='inst.required'", pid)
    return (a["n"], a["m"], b["n"], b["m"], (s or {}).get("value"))


def context(con, pid) -> dict:
    from app.valve import api
    v = _ver(con, pid)
    hit = _CTX.get(pid)
    if hit and hit[0] == v:
        return hit[1]
    pds, pds_ref = api._process_for(con, pid)
    pms, pms_ref = api._pms_for(con, pid)
    ll, ll_ref = _merged_linelist(con, pid)
    ctx = {"pds": pds, "pds_ref": pds_ref, "pms": pms, "pms_ref": pms_ref, "ll": ll, "ll_ref": ll_ref,
           "lists": _lists(con, pid), "required": _required(con, pid)}
    _CTX[pid] = (v, ctx, {})
    return ctx


def _sheet_rows(con, pid, kind: str = ""):
    q = "SELECT s.*, d.filename FROM inst_sheet s LEFT JOIN document d ON d.id=s.document_id WHERE s.project_id=?"
    rows = store.rows(con, q + (" AND s.kind=?" if kind else "") + " ORDER BY s.id", *([pid, kind] if kind else [pid]))
    return rows


def _latest(rows):
    out, hist = {}, {}
    for r in sorted(rows, key=lambda r: (store.rev_key(r["rev"]), r["id"])):
        out[r["tag_key"]] = r
        hist.setdefault(r["tag_key"], []).append({"id": r["id"], "rev": r["rev"], "date": r["rev_date"], "doc_no": r["doc_no"], "file": r.get("filename")})
    return out, hist


def reviewed(con, pid, r) -> dict:
    ctx = context(con, pid)
    memo = _CTX[pid][2]
    if r["id"] not in memo:
        sh = json.loads(r["sheet"])
        rv = instreview.review(sh, r["tag"], ctx)
        memo[r["id"]] = (sh, rv)
    return memo[r["id"]]


def _brief(con, pid, r, hist) -> dict:
    sh, rv = reviewed(con, pid, r)
    C = rv["canonical"]
    return {"id": r["id"], "tag": r["tag"], "kind": r["kind"], "form_id": r["form_id"], "doc_no": r["doc_no"], "rev": r["rev"],
            "rev_date": r["rev_date"], "file": r.get("filename"), "document_id": r["document_id"], "pages": json.loads(r["pages"] or "[]"),
            "test_data": bool(r["test_data"]), "status": r["status"], "service": (instrument.values(sh).get("service") or {}).get("value", ""),
            "counts": rv["counts"], "issues": rv["issues"], "in_pds": rv["in_pds"], "revs": hist.get(r["tag_key"], []),
            "piping_class": C.get("piping_class", ""), "line_no": C.get("line_no", "")}


# ── endpoints ─────────────────────────────────────────────────────────────────────────────────────────────────
def _j(obj) -> Response:
    return Response(json.dumps(obj, ensure_ascii=False, default=str), media_type="application/json")


@router.get("/api/valve/inst/kinds")
def kinds_api():
    cs = instrument.cards()
    return _j([{"kind": k, "form_id": fid, "name": KIND_NAMES.get(k, k), "title": cs[fid].get("title"),
                "required": (cs[fid].get("required") or {}).get("keys", []),
                "fields": [{"key": it["std_key"], "no": it["no"], "label": it["label"]} for it in cs[fid]["items"] if it.get("std_key") and it.get("role") != "header"]}
               for k, fid in sorted(instrument.kinds().items(), key=lambda x: ORDER.index(x[0]) if x[0] in ORDER else 99)])


@router.get("/api/valve/projects/{pid}/inst/summary")
def summary(pid: int):
    con = con_ready()
    rows = _sheet_rows(con, pid)
    latest, hist = _latest(rows)
    ctx = context(con, pid)
    per = {k: {"kind": k, "name": KIND_NAMES[k], "form_id": instrument.kinds().get(k), "sheets": 0, "tags": 0, "revs": {},
               "issues": 0, "missing": 0, "mismatch": 0, "review": 0, "not_in_pds": 0, "ok_tags": 0, "test": 0, "status": {}} for k in ORDER}
    for r in rows:
        if r["kind"] in per:
            per[r["kind"]]["sheets"] += 1
    for r in latest.values():
        p = per.get(r["kind"])
        if not p:
            continue
        _, rv = reviewed(con, pid, r)
        p["tags"] += 1
        p["revs"][r["rev"] or "-"] = p["revs"].get(r["rev"] or "-", 0) + 1
        p["missing"] += rv["counts"][instreview.MISSING]
        p["mismatch"] += rv["counts"][instreview.MISMATCH]
        p["review"] += rv["counts"][instreview.REVIEW]
        p["issues"] += rv["issues"]
        p["not_in_pds"] += 0 if rv["in_pds"] else 1
        p["ok_tags"] += 1 if rv["issues"] == 0 else 0
        p["test"] += 1 if r["test_data"] else 0
        p["status"][r["status"]] = p["status"].get(r["status"], 0) + 1
    L = ctx["lists"]
    refs = {"pds": (ctx["pds_ref"] or {}).get("filename"), "pms": (ctx["pms_ref"] or {}).get("filename"),
            "linelist": (ctx["ll_ref"] or {}).get("filename"), "n_lines": len((ctx["ll"] or {}).get("lines", [])),
            "instrument_index": " · ".join(L.get("instrument_index", {}).get("files", [])), "io_list": " · ".join(L.get("io_list", {}).get("files", [])),
            "required_confirmed": sorted(ctx["required"])}
    tot = {k: sum(p[k] for p in per.values()) for k in ("sheets", "tags", "issues", "missing", "mismatch", "review", "not_in_pds", "ok_tags", "test")}
    return _j({"kinds": [per[k] for k in ORDER], "total": tot, "refs": refs})


@router.get("/api/valve/projects/{pid}/inst/sheets")
def sheets(pid: int, kind: str = ""):
    con = con_ready()
    latest, hist = _latest(_sheet_rows(con, pid, kind))
    return _j({"rows": [_brief(con, pid, r, hist) for r in sorted(latest.values(), key=lambda r: r["tag_key"])]})


@router.get("/api/valve/inst/sheets/{sid}")
def sheet(sid: int):
    con = con_ready()
    r = store.one(con, "SELECT s.*, d.filename FROM inst_sheet s LEFT JOIN document d ON d.id=s.document_id WHERE s.id=?", sid)
    if not r:
        return Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
    pid = r["project_id"]
    _, hist = _latest(_sheet_rows(con, pid, r["kind"]))
    sh, rv = reviewed(con, pid, r)
    card = instrument.cards()[sh["form_id"]]
    rows = []
    for it in card["items"]:
        if it.get("role") == "header" or not it.get("value_bbox"):
            continue
        key = f"{it['block']}.{it['no']}" if it["block"] != 1 else str(it["no"])
        got = sh["rows"].get(key) or {}
        rows.append({"no": key, "label": it["label"], "section": it.get("section") or "", "std_key": it.get("std_key"),
                     "value": got.get("value", ""), "sub": got.get("sub") or {}, "page": got.get("page") or it.get("page"),
                     "bbox": got.get("bbox"), "process": bool(it.get("process"))})
    return _j(dict(_brief(con, pid, r, hist), title=sh.get("title"), title_block=sh.get("title_block"), identify=sh.get("identify"),
                   rows=rows, review=rv["rows"], canonical=rv["canonical"], rules=instreview.RULES, rule_ver=instreview.RULE_VER))


@router.put("/api/valve/inst/sheets/{sid}/status")
async def sheet_status(sid: int, request: Request):
    body = await request.json()
    st = body.get("status")
    if st not in ("Not Reviewed", "Under Review", "Accepted", "Rejected", "Commented", "Resolved"):
        return Response('{"error":"상태 값이 잘못됨"}', status_code=400, media_type="application/json")
    con = con_ready()
    r = store.one(con, "SELECT project_id, status FROM inst_sheet WHERE id=?", sid)
    if not r:
        return Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
    con.execute("UPDATE inst_sheet SET status=? WHERE id=?", (st, sid))
    from app.valve import api
    store.audit(con, r["project_id"], None, f"inst:{sid}", "inst-status", r["status"], st, api._user(request), "")
    con.commit()
    return _j({"ok": True, "status": st})


@router.get("/api/valve/projects/{pid}/inst/required")
def required_get(pid: int):
    con = con_ready()
    return _j({"confirmed": _required(con, pid),
               "suggested": {fid: (c.get("required") or {}).get("keys", []) for fid, c in instrument.cards().items()}})


@router.put("/api/valve/projects/{pid}/inst/required")
async def required_put(pid: int, request: Request):
    body = await request.json()
    fid, keys = str(body.get("form_id") or ""), body.get("keys")
    if fid not in instrument.cards() or not isinstance(keys, list):
        return Response('{"error":"form_id · keys 가 필요합니다"}', status_code=400, media_type="application/json")
    con = con_ready()
    cur = _required(con, pid)
    cur[fid] = [str(k) for k in keys]
    from app.valve import api
    by = api._user(request)
    con.execute("INSERT OR REPLACE INTO project_setting(project_id, key, value, by, at) VALUES (?,?,?,?,?)",
                (pid, "inst.required", json.dumps(cur, ensure_ascii=False), by, store.now()))
    store.audit(con, pid, None, f"inst.required.{fid}", "inst-required", None, ",".join(cur[fid]), by, "")
    con.commit()
    return _j({"ok": True, "confirmed": cur})


def listcmp_rows(con, pid) -> dict:
    ctx = context(con, pid)
    latest, _ = _latest(_sheet_rows(con, pid))
    ds_rows = []
    for r in latest.values():
        sh, rv = reviewed(con, pid, r)
        vals, C = instrument.values(sh), rv["canonical"]
        g = lambda k: (vals.get(k) or {}).get("value", "")   # noqa: E731
        rng = C.get("range") or {}
        ds_rows.append({"tag": r["tag"], "tag_key": r["tag_key"], "kind": r["kind"], "sheet_id": r["id"],
                        "values": {"service": g("service"), "pid_no": g("pid_no"), "line_no": C.get("line_no", ""), "fluid": C.get("fluid", ""),
                                   "range": rng.get("text", ""), "datasheet_no": r["doc_no"], "manufacturer": g("manufacturer"),
                                   "model": g("model") or next((v for k, v in ((vals.get("model") or {}).get("sub") or {}).items() if v), "")}})
    out = []
    names = {"instrument_index": "Instrument Index", "io_list": "IO List"}
    for k, nm in names.items():
        out += instlists.compare(ds_rows, ctx["lists"].get(k), nm)
    cnt = {}
    for x in out:
        cnt.setdefault(x["list"], {}).setdefault(x["result"], 0)
        cnt[x["list"]][x["result"]] += 1
    return {"rows": out, "counts": cnt, "lists": {k: {"files": v["files"], "rev": v["rev"], "tags": len(v["by_tag"])} for k, v in ctx["lists"].items()}}


@router.get("/api/valve/projects/{pid}/inst/listcmp")
def listcmp(pid: int):
    return _j(listcmp_rows(con_ready(), pid))


def _xlsx(sheets: list[tuple[str, list[str], list[list]]]) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    fills = {"Mismatch": "F8D7DA", "값 다름": "F8D7DA", "누락": "FCE8D5", "Missing": "FCE8D5", "Review Required": "FFF3CD",
             "List 에만": "E2E3F5", "없음": "EEEEEE"}
    for title, head, rows in sheets:
        ws = wb.create_sheet(title[:31])
        ws.append(head)
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="1F3A5F")
        for r in rows:
            ws.append(r)
            res = next((v for v in r if isinstance(v, str) and v in fills), None)
            if res:
                for c in ws[ws.max_row]:
                    c.fill = PatternFill("solid", fgColor=fills[res])
        for i, h in enumerate(head, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = max(10, min(48, len(h) + 6))
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


@router.get("/api/valve/projects/{pid}/inst/listcmp.xlsx")
def listcmp_xlsx(pid: int):
    d = listcmp_rows(con_ready(), pid)
    head = ["List", "Rule", "Tag", "Kind", "Item", "Datasheet", "List value", "Result", "Reason", "List page"]
    rows = [[x["list"], x["rule"], x["tag"], KIND_NAMES.get(x["kind"], x["kind"]), x["field"], x["ds"], x["lst"], x["result"], x["reason"], x.get("page")] for x in d["rows"]]
    data = _xlsx([("List 대조", head, rows)])
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=instrument_list_compare.xlsx"})


@router.get("/api/valve/projects/{pid}/inst/review.xlsx")
def review_xlsx(pid: int, kind: str = ""):
    con = con_ready()
    latest, hist = _latest(_sheet_rows(con, pid, kind))
    head = ["Tag", "Kind", "Form", "Doc No", "Rev", "Rule", "Item", "Datasheet", "Reference", "Result", "Severity", "Reason", "Source", "Human check"]
    rows, summ = [], []
    for r in sorted(latest.values(), key=lambda r: (ORDER.index(r["kind"]) if r["kind"] in ORDER else 99, r["tag_key"])):
        _, rv = reviewed(con, pid, r)
        summ.append([r["tag"], KIND_NAMES.get(r["kind"], r["kind"]), r["form_id"], r["doc_no"], r["rev"], rv["issues"],
                     rv["counts"]["Missing"], rv["counts"]["Mismatch"], rv["counts"]["Review Required"], "있음" if rv["in_pds"] else "없음"])
        for x in rv["rows"]:
            if x["result"] == instreview.OK:
                continue
            rows.append([r["tag"], KIND_NAMES.get(r["kind"], r["kind"]), r["form_id"], r["doc_no"], r["rev"], x["rule"], x["item"],
                         str(x["ds"]), str(x["ref"]), x["result"], x["severity"], x["reason"], x["source"], "사람 확인" if x.get("human") else ""])
    data = _xlsx([("Summary", ["Tag", "Kind", "Form", "Doc No", "Rev", "Issues", "Missing", "Mismatch", "Review", "PDS"], summ),
                  ("Findings", head, rows)])
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=instrument_review{'_' + kind if kind else ''}.xlsx"})
