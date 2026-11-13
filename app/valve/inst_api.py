"""Instrument datasheet review — API (valve40).  Same server, same project spaces, same Document Management as the
Valve tool; the instrument rows live in their own table so the Valve review is untouched.

Upload kinds (Document Management):  instrument (Instrument Datasheet PDF) · linelist (Process Line List xlsx) ·
instlist (Instrument Index / IO List PDF — which one is read from the page).
"""
from __future__ import annotations

import io
import json
import threading
import re
import time
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response

from app.valve import instlists, instreview, instrument, linelist, store

router = APIRouter()
SCHEMA = """
CREATE TABLE IF NOT EXISTS inst_sheet (id INTEGER PRIMARY KEY, project_id INTEGER, document_id INTEGER, form_id TEXT,
  kind TEXT, tag TEXT, tag_key TEXT, doc_no TEXT, rev TEXT, rev_date TEXT, pages TEXT, sheet TEXT, test_data INTEGER,
  status TEXT DEFAULT 'Not Reviewed', created_at TEXT);
CREATE INDEX IF NOT EXISTS inst_tag ON inst_sheet(project_id, tag_key);
CREATE TABLE IF NOT EXISTS inst_decision (sheet_id INTEGER, fkey TEXT, decision TEXT, reason_cat TEXT, reason TEXT, text TEXT,
  by TEXT, at TEXT, PRIMARY KEY (sheet_id, fkey));
CREATE TABLE IF NOT EXISTS inst_reply (sheet_id INTEGER, fkey TEXT, reply TEXT, reply_date TEXT, status TEXT, closed_by TEXT,
  file TEXT, by TEXT, at TEXT, PRIMARY KEY (sheet_id, fkey));
"""
# valve40 — engineer decisions on a finding (Bluebeam-style status per comment).  'Dismissed' takes the finding out of the
# counts, the mark-up PDF and the CRS; 'Modified' replaces the comment wording; 'Confirmed' keeps it as a comment to the vendor.
DECISIONS = ("Confirmed", "Modified", "Dismissed")
REASONS = ["Project specification exception", "Vendor clarification", "Not applicable", "Incorrect data extraction",
           "Duplicate finding", "Other"]
# document review codes — they differ per project, so the set is a project setting; this default is one published scheme
DEFAULT_CODES = [{"code": "1", "label": "Rejected"}, {"code": "2", "label": "Revise and Resubmit"},
                 {"code": "3", "label": "Approved with Comments"}, {"code": "4", "label": "Approved"},
                 {"code": "5", "label": "Information Only"}]
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
        cols = {r["name"] for r in store.rows(con, "PRAGMA table_info(inst_sheet)")}
        if "review_code" not in cols:                      # valve40: document review code per datasheet
            con.execute("ALTER TABLE inst_sheet ADD COLUMN review_code TEXT")
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
    invalidate(pid)
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
    """valve40: Line List · Instrument Index · IO List are shared by the project family (the 공통 자료 menu keeps them on the
    base project); older uploads into this project itself still count (oldest first → the newest wins)."""
    from app.valve import api
    rp = api.ref_pid(con, pid)
    return store.rows(con, "SELECT id, filename, uploaded_at, info FROM document WHERE project_id IN (?,?) AND kind=? AND status='done' ORDER BY id",
                      pid, rp, kind)


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
    from app.valve import api
    a = store.one(con, "SELECT COUNT(*) n, MAX(id) m FROM document WHERE project_id IN (?,?) AND status='done'", pid, api.ref_pid(con, pid))
    b = store.one(con, "SELECT COUNT(*) n, MAX(id) m FROM inst_sheet WHERE project_id=?", pid)
    s = store.one(con, "SELECT group_concat(key || length(value) || at) value FROM project_setting WHERE project_id IN (?,?)"
                       " AND key IN ('inst.required', 'inst.arearule.table')", pid, api.ref_pid(con, pid))
    dd = store.one(con, "SELECT COUNT(*) n, MAX(at) m FROM inst_decision WHERE sheet_id IN (SELECT id FROM inst_sheet WHERE project_id=?)", pid)
    rr = store.one(con, "SELECT COUNT(*) n, MAX(at) m FROM inst_reply WHERE sheet_id IN (SELECT id FROM inst_sheet WHERE project_id=?)", pid)
    return (a["n"], a["m"], b["n"], b["m"], (s or {}).get("value"), dd["n"], dd["m"], rr["n"], rr["m"])


def _ck(pid):
    return (str(store.root()), pid)                       # one cache per data folder (tests · several servers)


def invalidate(pid):
    """A write (decision · code · status · settings · upload) — the next read recomputes."""
    _CTX.pop(_ck(pid), None)


def invalidate_family():
    """A shared reference document changed (공통 자료) — every project of this data folder recomputes."""
    root = str(store.root())
    for k in [k for k in _CTX if k[0] == root]:
        _CTX.pop(k, None)


def context(con, pid) -> dict:
    from app.valve import api
    hit = _CTX.get(_ck(pid))
    now = time.monotonic()
    if hit and now - hit[3] < 0.5:                         # one request walks hundreds of tags: check the version once
        return hit[1]
    v = _ver(con, pid)
    if hit and hit[0] == v:
        _CTX[_ck(pid)] = (hit[0], hit[1], hit[2], now)
        return hit[1]
    pds, pds_ref = api._process_for(con, pid)
    pms, pms_ref = api._pms_for(con, pid)
    ll, ll_ref = _merged_linelist(con, pid)
    ctx = {"pds": pds, "pds_ref": pds_ref, "pms": pms, "pms_ref": pms_ref, "ll": ll, "ll_ref": ll_ref,
           "lists": _lists(con, pid), "required": _required(con, pid), "arearule": area_rule_cached(con, pid)}
    _CTX[_ck(pid)] = (v, ctx, {}, now)
    return ctx


_LIGHT = ("s.id, s.project_id, s.document_id, s.form_id, s.kind, s.tag, s.tag_key, s.doc_no, s.rev, s.rev_date, s.pages, s.test_data,"
          " s.status, s.created_at, s.review_code")


def area_rule(con, pid) -> dict:
    """Area by the tag's leading number, learned from the project family's Valve datasheets and Process Data parts
    (their areas come from the documents' own titles — the Valve first screen).  app/valve/arearule.py."""
    from app.valve import api, arearule, docreg
    me = store.one(con, "SELECT name FROM project WHERE id=?", pid)
    if not me:
        return {}
    base = docreg.base_name(me["name"])
    ev = []
    for p in store.rows(con, "SELECT id, name FROM project"):
        if docreg.base_name(p["name"]) != base:
            continue
        try:
            cov = api._coverage(con, p["id"])
        except Exception:                                  # noqa: BLE001 — no evidence from a project that cannot be read
            continue
        ev += [{"tag": t["tag"], "doc_no": t.get("doc_no", ""), "zone": t.get("zone", "")} for t in cov.get("tags", [])]
        ev += [{"doc_no": x["doc_no"], "zone": x.get("zone", "")} for x in cov.get("ds_docs", [])]
        for d in cov.get("pds_docs", []):
            ev += [{"doc_no": x.get("doc_no", ""), "zone": x.get("zone", "")} for x in d.get("parts", [])]
    idx = (_lists(con, pid).get("instrument_index") or {}).get("by_tag", {})          # valve40: the Index AREA column, per tag
    ev += [{"tag": x.get("tag", ""), "sub": x.get("area", "")} for x in idx.values() if x.get("area")]
    return arearule.learn(ev, arearule.parse_table(area_table_text(con, pid)))


_AR: dict = {}
_AR_TL = threading.local()


def area_rule_cached(con, pid) -> dict:
    """The family's area rule, recomputed only when a family document / datasheet / the rule table changes (valve40: the
    Valve screens use it too).  Re-entry while it is being built (the evidence reads the Valve coverage) returns {}."""
    from app.valve import api
    fam = api.family(con, pid)
    q = ",".join("?" * len(fam))
    v = (tuple(store.one(con, f"SELECT COUNT(*) n, MAX(id) m FROM document WHERE project_id IN ({q}) AND status='done'", *fam).values())
         + tuple(store.one(con, f"SELECT COUNT(*) n, MAX(id) m FROM datasheet WHERE project_id IN ({q})", *fam).values())
         + ((store.one(con, "SELECT at FROM project_setting WHERE project_id=? AND key='inst.arearule.table'", fam[0]) or {}).get("at"),))
    k = (str(store.root()), fam[0])
    hit = _AR.get(k)
    if hit and hit[0] == v:
        return hit[1]
    if getattr(_AR_TL, "busy", False):
        return {}
    _AR_TL.busy = True
    try:
        r = area_rule(con, pid)
    finally:
        _AR_TL.busy = False
    _AR[k] = (v, r)
    return r


def area_table_text(con, pid) -> str:
    """The engineer's area rule table (pasted on the By Area screen) — kept once per project family, like 공통 자료."""
    from app.valve import api
    r = store.one(con, "SELECT value FROM project_setting WHERE project_id=? AND key='inst.arearule.table'", api.ref_pid(con, pid))
    return (r or {}).get("value") or ""


@router.get("/api/valve/projects/{pid}/inst/arearule")
def arearule_get(pid: int):
    """The learned 'tag prefix → area' rule, for the engineer to see (and judge) before trusting the By Area view."""
    from app.valve import arearule
    con = con_ready()
    r = context(con, pid)["arearule"]
    return _j({"rows": arearule.table(r), "systems": r.get("system", {}), "evidence": r.get("n", 0), "index_rows": r.get("n_index", 0),
               "table": arearule.check_table(r), "text": area_table_text(con, pid)})


@router.put("/api/valve/projects/{pid}/inst/arearule")
async def arearule_put(pid: int, request: Request):
    """Save the engineer's rule table (pasted text).  Every tag is re-classified on the next read."""
    from app.valve import api, arearule
    body = await request.json()
    text = str(body.get("text") or "")
    rows = arearule.parse_table(text)
    if text.strip() and not rows:
        return Response('{"error":"규칙 줄을 찾지 못했습니다 — \'Tag 접두어 | Area | Unit | 메모\' 표나 \'QS: 98GTD- / 98SD-\' 줄로 넣어 주세요"}',
                        status_code=400, media_type="application/json")
    con = con_ready()
    rp = api.ref_pid(con, pid)
    con.execute("INSERT OR REPLACE INTO project_setting(project_id, key, value, by, at) VALUES (?,?,?,?,?)",
                (rp, "inst.arearule.table", text, api._user(request), store.now()))
    store.audit(con, rp, None, "inst.arearule.table", "inst-arearule", None, f"{len(rows)} rows", api._user(request), "")
    con.commit()
    invalidate_family()
    return arearule_get(pid)


def _sheet_rows(con, pid, kind: str = ""):
    """Rows without the stored sheet (its JSON is the bulk; reviewed() reads it only when the review is not cached)."""
    q = f"SELECT {_LIGHT}, d.filename FROM inst_sheet s LEFT JOIN document d ON d.id=s.document_id WHERE s.project_id=?"
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
    memo = _CTX[_ck(pid)][2]
    if r["id"] not in memo:
        raw = r.get("sheet") or (store.one(con, "SELECT sheet FROM inst_sheet WHERE id=?", r["id"]) or {}).get("sheet") or "{}"
        sh = json.loads(raw)
        rv = instreview.review(sh, r["tag"], ctx)
        apply_decisions(con, r, rv)
        memo[r["id"]] = (sh, rv)
    return memo[r["id"]]


def fkey(x: dict) -> str:
    """A finding's identity across re-reads and revisions: rule · field · item (not the values, which a new Rev changes)."""
    return f"{x['rule']}|{x.get('key') or ''}|{x.get('item') or ''}"


def apply_decisions(con, r, rv):
    """Overlay the engineer's decisions; a tag's newer revision inherits the decisions of its older ones (same fkey),
    marked with the revision they came from.  Dismissed findings leave the counts."""
    own = {d["fkey"]: d for d in store.rows(con, "SELECT * FROM inst_decision WHERE sheet_id=?", r["id"])}
    replies = {d["fkey"]: d for d in store.rows(con, "SELECT * FROM inst_reply WHERE sheet_id=?", r["id"])}   # this revision only
    older = store.rows(con, "SELECT id, rev FROM inst_sheet WHERE project_id=? AND tag_key=? AND id<>?", r["project_id"], r["tag_key"], r["id"])
    older = [o for o in older if store.rev_key(o["rev"]) < store.rev_key(r["rev"])]
    inherited = {}
    for o in sorted(older, key=lambda o: store.rev_key(o["rev"])):
        for d in store.rows(con, "SELECT * FROM inst_decision WHERE sheet_id=?", o["id"]):
            inherited[d["fkey"]] = dict(d, origin=f"Rev {o['rev'] or '-'}")
    for x in rv["rows"]:
        if x["result"] not in (instreview.MISMATCH, instreview.MISSING, instreview.REVIEW):
            continue
        d = own.get(fkey(x)) or inherited.get(fkey(x))
        x["fkey"] = fkey(x)
        rp_ = replies.get(x["fkey"])
        if rp_:
            x["reply"] = {"reply": rp_["reply"], "date": rp_["reply_date"], "status": rp_["status"], "closed_by": rp_["closed_by"], "file": rp_["file"], "at": rp_["at"]}
            if rp_["status"] == "Closed" and not (d and d["decision"] == "Dismissed"):
                x["result_tool"], x["result"] = x["result"], "Closed"
        if not d:
            continue
        x["decision"] = {"decision": d["decision"], "reason_cat": d["reason_cat"], "reason": d["reason"], "text": d["text"],
                         "by": d["by"], "at": d["at"], "origin": d.get("origin", "")}
        if d["decision"] == "Modified" and d["text"]:
            x["reason_tool"], x["reason"] = x["reason"], d["text"]
        if d["decision"] == "Dismissed":
            x["result_tool"], x["result"] = x["result"], "Dismissed"
    n = {k: sum(1 for x in rv["rows"] if x["result"] == k) for k in (instreview.MISMATCH, instreview.MISSING, instreview.REVIEW,
                                                                    instreview.NOT_IN, instreview.BLANK, instreview.OK, "Dismissed", "Closed")}
    rv["counts"] = n
    rv["issues"] = n[instreview.MISMATCH] + n[instreview.MISSING] + n[instreview.REVIEW]
    n = rv["counts"]
    rv["suggested"] = "revise" if n.get(instreview.MISMATCH) else "comments" if (n.get(instreview.MISSING) or n.get(instreview.REVIEW)) else "approved"
    rv["suggested_code"] = suggest_code(rv["suggested"], codes_for(con, r["project_id"]))


_MEANING = {"revise": re.compile(r"revis|resubmit|재제출|보완", re.I), "comments": re.compile(r"with\s+comment|comments?|조건부|코멘트", re.I),
            "approved": re.compile(r"^\s*(approved|accepted|승인)\s*$", re.I)}


def suggest_code(meaning: str, codes: list[dict]) -> str:
    """The project's code whose meaning fits the open findings: any Mismatch → 'Revise and Resubmit' · only Missing / Review
    → 'Approved with Comments' · nothing open → 'Approved'.  Matched by the code's label (projects number them differently);
    '' when no label fits.  Only a suggestion — the engineer sets the code."""
    rx = _MEANING[meaning]
    hit = [c for c in codes if rx.search(c.get("label", ""))]
    if meaning == "comments":
        hit = [c for c in hit if not _MEANING["revise"].search(c["label"])]
    return hit[0]["code"] if hit else ""


def codes_for(con, pid) -> list[dict]:
    r = store.one(con, "SELECT value FROM project_setting WHERE project_id=? AND key='inst.codes'", pid)
    try:
        v = json.loads(r["value"]) if r and r["value"] else None
    except ValueError:
        v = None
    return v if isinstance(v, list) and v else DEFAULT_CODES


def _brief(con, pid, r, hist) -> dict:
    sh, rv = reviewed(con, pid, r)
    C = rv["canonical"]
    from app.valve import location
    vals = instrument.values(sh)
    from app.valve import arearule
    pidno = (vals.get("pid_no") or {}).get("value", "")
    loc = location.locate(doc_no=r["doc_no"] or "", pid_no=pidno, tag=r["tag"])
    ctx = context(con, pid)
    isub = ((ctx.get("lists", {}).get("instrument_index") or {}).get("by_tag", {}).get(r["tag_key"]) or {}).get("area", "")
    A = arearule.classify(ctx.get("arearule") or {}, r["tag"], r["doc_no"] or "", pidno, isub)    # table · Index AREA · tag prefix rule
    area = A["area"] or location.zone(loc)
    return {"area": area, "sub_area": A["sub"], "unit": A["unit"] or loc.get("unit") or "", "area_note": A["note"],
            "loc_basis": A["basis"] or loc.get("basis") or "",
            "id": r["id"], "tag": r["tag"], "kind": r["kind"], "form_id": r["form_id"], "doc_no": r["doc_no"], "rev": r["rev"],
            "rev_date": r["rev_date"], "file": r.get("filename"), "document_id": r["document_id"], "pages": json.loads(r["pages"] or "[]"),
            "test_data": bool(r["test_data"]), "status": r["status"], "service": (instrument.values(sh).get("service") or {}).get("value", ""),
            "counts": rv["counts"], "issues": rv["issues"], "in_pds": rv["in_pds"], "revs": hist.get(r["tag_key"], []),
            "review_code": r.get("review_code") or "", "suggested_code": rv.get("suggested_code", ""),
            "piping_class": C.get("piping_class", ""), "line_no": C.get("line_no", ""),
            "vals": {"pid_no": (vals.get("pid_no") or {}).get("value", ""), "fluid": C.get("fluid", ""), "phase": C.get("fluid_state", ""),
                     "op_pressure": (C.get("op_pressure") or {}).get("text", ""), "design_pressure": (C.get("design_pressure") or {}).get("text", ""),
                     "op_temp": (C.get("op_temp") or {}).get("text", ""), "design_temp": (C.get("design_temp") or {}).get("text", ""),
                     "range": (C.get("range") or {}).get("text", ""), "manufacturer": (vals.get("manufacturer") or {}).get("value", ""),
                     "model": (vals.get("model") or {}).get("value", "") or next((v for v in ((vals.get("model") or {}).get("sub") or {}).values() if v), "")}}


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
               "issues": 0, "missing": 0, "mismatch": 0, "review": 0, "not_in_pds": 0, "ok_tags": 0, "test": 0, "status": {},
               "reviewed": 0, "issue_tags": 0, "pending": 0, "closed": 0, "dismissed": 0} for k in ORDER}
    cats = {g: 0 for g in CATEGORY}
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
        done = r["status"] in ("Accepted", "Resolved") or bool(r.get("review_code"))   # review finished: status or a code given
        p["reviewed"] += 1 if done else 0
        p["pending"] += 0 if done else 1
        p["issue_tags"] += 1 if rv["issues"] else 0
        p["closed"] += rv["counts"].get("Closed", 0)
        p["dismissed"] += rv["counts"].get("Dismissed", 0)
        for x in rv["rows"]:
            if x["result"] in (instreview.MISMATCH, instreview.MISSING, instreview.REVIEW):
                cats[category(x["rule"])] += 1
    L = ctx["lists"]
    refs = {"pds": (ctx["pds_ref"] or {}).get("filename"), "pms": (ctx["pms_ref"] or {}).get("filename"),
            "linelist": (ctx["ll_ref"] or {}).get("filename"), "n_lines": len((ctx["ll"] or {}).get("lines", [])),
            "instrument_index": " · ".join(L.get("instrument_index", {}).get("files", [])), "io_list": " · ".join(L.get("io_list", {}).get("files", [])),
            "required_confirmed": sorted(ctx["required"])}
    tot = {k: sum(p[k] for p in per.values()) for k in ("sheets", "tags", "issues", "missing", "mismatch", "review", "not_in_pds", "ok_tags", "test",
                                                         "reviewed", "issue_tags", "pending", "closed", "dismissed")}
    return _j({"kinds": [per[k] for k in ORDER], "total": tot, "refs": refs, "categories": cats, "at": store.now()})


CATEGORY = {"Process Data": "IN-PDS", "Line List": "IN-LL", "PMS": "IN-PMS", "Required Field": "IN-REQ", "Open Item": "IN-OPN",
            "Sizing (CV · PSV)": ("IN-CV", "IN-PSV"), "Item Rule": ("IN-ITM", "IN-UNIT")}


def category(rule: str) -> str:
    for name, pre in CATEGORY.items():
        if rule.startswith(pre if isinstance(pre, tuple) else (pre,)):
            return name
    return "Item Rule"


@router.get("/api/valve/projects/{pid}/inst/sheets")
def sheets(pid: int, kind: str = ""):
    con = con_ready()
    latest, hist = _latest(_sheet_rows(con, pid, kind))
    return _j({"rows": [_brief(con, pid, r, hist) for r in sorted(latest.values(), key=lambda r: r["tag_key"])]})


GROUPS = {"req": "IN-REQ", "pds": "IN-PDS", "pms": "IN-PMS", "line": "IN-LL", "item": "IN-ITM"}


@router.get("/api/valve/projects/{pid}/inst/findings")
def findings(pid: int, kind: str = "", group: str = ""):
    """Every check row of the latest datasheets of one item, for one reference (pds · pms · line · req · item) —
    the item's Process Data Verification · PMS Compliance · Line List screens."""
    con = con_ready()
    latest, _ = _latest(_sheet_rows(con, pid, kind))
    pre = GROUPS.get(group, "")
    out, cnt = [], {}
    for r in sorted(latest.values(), key=lambda r: r["tag_key"]):
        _, rv = reviewed(con, pid, r)
        for x in rv["rows"]:
            if pre and not x["rule"].startswith(pre):
                continue
            out.append({"sheet_id": r["id"], "tag": r["tag"], "rev": r["rev"], "kind": r["kind"], "rule": x["rule"], "item": x["item"], "key": x["key"],
                        "ds": str(x["ds"] or ""), "ref": str(x["ref"] or ""), "result": x["result"], "reason": x["reason"], "source": x["source"],
                        "human": bool(x.get("human"))})
            cnt[x["result"]] = cnt.get(x["result"], 0) + 1
    ctx = context(con, pid)
    ref = {"pds": ctx["pds_ref"], "pms": ctx["pms_ref"], "line": ctx["ll_ref"]}.get(group)
    return _j({"rows": out, "counts": cnt, "tags": len(latest), "ref": (ref or {}).get("filename", ""), "rules": instreview.RULES})


@router.get("/api/valve/inst/compare")
def compare(prev: int, new: int):
    """Row-by-row difference of two revisions of one tag (values as read)."""
    con = con_ready()
    a = store.one(con, "SELECT * FROM inst_sheet WHERE id=?", prev)
    b = store.one(con, "SELECT * FROM inst_sheet WHERE id=?", new)
    if not a or not b:
        return Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
    ca, cb = {r["no"]: r for r in _cells(json.loads(a["sheet"]))}, {r["no"]: r for r in _cells(json.loads(b["sheet"]))}
    txt = lambda r: " ".join([r.get("value", "")] + [f"{k}: {v}" for k, v in (r.get("sub") or {}).items()]).strip() if r else ""   # noqa: E731
    rows = []
    for no in list(cb) + [k for k in ca if k not in cb]:
        x, y = txt(ca.get(no)), txt(cb.get(no))
        if x == y:
            continue
        r = cb.get(no) or ca.get(no)
        rows.append({"no": no, "label": r["label"], "section": r.get("section", ""), "std_key": r.get("std_key"), "prev": x, "new": y,
                     "change": "Added" if not x else "Deleted" if not y else "Modified", "page": r.get("page"), "bbox": r.get("bbox")})
    return _j({"prev": {"id": a["id"], "rev": a["rev"], "doc_no": a["doc_no"], "date": a["rev_date"]},
               "new": {"id": b["id"], "rev": b["rev"], "doc_no": b["doc_no"], "date": b["rev_date"]}, "tag": b["tag"], "rows": rows})


@router.get("/api/valve/inst/sheets/{sid}")
def sheet(sid: int):
    con = con_ready()
    r = store.one(con, "SELECT s.*, d.filename FROM inst_sheet s LEFT JOIN document d ON d.id=s.document_id WHERE s.id=?", sid)
    if not r:
        return Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
    pid = r["project_id"]
    _, hist = _latest(_sheet_rows(con, pid, r["kind"]))
    sh, rv = reviewed(con, pid, r)
    rows = _cells(sh)
    return _j(dict(_brief(con, pid, r, hist), title=sh.get("title"), title_block=sh.get("title_block"), identify=sh.get("identify"),
                   rows=rows, review=rv["rows"], canonical=rv["canonical"], rules=instreview.RULES, rule_ver=instreview.RULE_VER,
                   codes=codes_for(con, pid), reasons=REASONS))


@router.put("/api/valve/inst/sheets/{sid}/decisions")
async def sheet_decision(sid: int, request: Request):
    """Engineer decision on one finding: {fkey, decision: Confirmed|Modified|Dismissed|Open, reason_cat, reason, text}.
    'Open' removes the decision.  Dismissed / Modified need a reason (kept in the audit log)."""
    from app.valve import api
    body = await request.json()
    fk, dec = str(body.get("fkey") or ""), body.get("decision")
    con = con_ready()
    r = store.one(con, "SELECT project_id FROM inst_sheet WHERE id=?", sid)
    if not r or not fk:
        return Response('{"error":"Datasheet · fkey 가 필요합니다"}', status_code=400, media_type="application/json")
    by = api._user(request)
    if dec == "Open":
        con.execute("DELETE FROM inst_decision WHERE sheet_id=? AND fkey=?", (sid, fk))
    elif dec in DECISIONS:
        if dec in ("Dismissed", "Modified") and not (body.get("reason") or body.get("reason_cat")) and not (dec == "Modified" and body.get("text")):
            return Response('{"error":"무시 · 문구 수정에는 이유가 필요합니다"}', status_code=400, media_type="application/json")
        con.execute("INSERT OR REPLACE INTO inst_decision(sheet_id, fkey, decision, reason_cat, reason, text, by, at) VALUES (?,?,?,?,?,?,?,?)",
                    (sid, fk, dec, body.get("reason_cat") or "", body.get("reason") or "", body.get("text") or "", by, store.now()))
    else:
        return Response('{"error":"decision 값이 잘못됨"}', status_code=400, media_type="application/json")
    store.audit(con, r["project_id"], None, f"inst:{sid}:{fk}", "inst-decision", None, dec, by, (body.get("reason_cat") or "") + " " + (body.get("reason") or ""))
    con.commit()
    invalidate(r["project_id"])
    return _j({"ok": True})


@router.put("/api/valve/inst/sheets/{sid}/code")
async def sheet_code(sid: int, request: Request):
    from app.valve import api
    body = await request.json()
    con = con_ready()
    r = store.one(con, "SELECT project_id, review_code FROM inst_sheet WHERE id=?", sid)
    if not r:
        return Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
    code = str(body.get("code") or "")
    if code and code not in {c["code"] for c in codes_for(con, r["project_id"])}:
        return Response('{"error":"이 프로젝트의 Review Code 가 아닙니다"}', status_code=400, media_type="application/json")
    con.execute("UPDATE inst_sheet SET review_code=? WHERE id=?", (code, sid))
    store.audit(con, r["project_id"], None, f"inst:{sid}", "inst-code", r["review_code"], code, api._user(request), "")
    con.commit()
    invalidate(r["project_id"])
    return _j({"ok": True, "review_code": code})


@router.get("/api/valve/projects/{pid}/inst/codes")
def codes_get(pid: int):
    con = con_ready()
    return _j({"codes": codes_for(con, pid), "default": DEFAULT_CODES, "reasons": REASONS})


@router.put("/api/valve/projects/{pid}/inst/codes")
async def codes_put(pid: int, request: Request):
    from app.valve import api
    body = await request.json()
    cs = [{"code": str(c.get("code", "")).strip()[:6], "label": str(c.get("label", "")).strip()[:40]} for c in body.get("codes") or []]
    cs = [c for c in cs if c["code"] and c["label"]]
    if not cs or len({c["code"] for c in cs}) != len(cs):
        return Response('{"error":"코드가 비었거나 겹칩니다"}', status_code=400, media_type="application/json")
    con = con_ready()
    by = api._user(request)
    con.execute("INSERT OR REPLACE INTO project_setting(project_id, key, value, by, at) VALUES (?,?,?,?,?)",
                (pid, "inst.codes", json.dumps(cs, ensure_ascii=False), by, store.now()))
    store.audit(con, pid, None, "inst.codes", "inst-codes", None, json.dumps(cs, ensure_ascii=False), by, "")
    con.commit()
    invalidate(pid)
    return _j({"ok": True, "codes": cs})


_CLOSED = {"closed", "close", "accepted", "resolved", "agreed", "done", "종결", "완료"}


def read_crs(data: bytes) -> list[dict]:
    """Rows of a returned CRS (our own layout; the vendor may add rows above or reorder columns): Ref · Tag · Rule ·
    Field · Vendor Reply · Reply Date · Status · Closed by — found by the header captions, not by position."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    ws = wb["CRS"] if "CRS" in wb.sheetnames else wb.worksheets[0]
    hdr, cols = None, {}
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=15, values_only=True), 1):
        caps = [str(v or "").strip().lower() for v in row]
        if "vendor reply" in caps and ("tag" in caps or any(c.startswith("ref") for c in caps)):
            hdr = i
            for j, c in enumerate(caps):
                key = {"tag": "tag", "rule": "rule", "field": "field", "vendor reply": "reply", "reply date": "date", "status": "status",
                       "closed by": "closed_by"}.get(c) or ("ref" if c.startswith("ref") else None)
                if key and key not in cols:
                    cols[key] = j
            break
    if not hdr:
        raise ValueError("CRS 머리글(Vendor Reply · Tag · Ref)을 찾지 못했습니다 — 이 도구에서 내려받은 CRS 를 고쳐 올려 주세요")
    out = []
    for row in ws.iter_rows(min_row=hdr + 1, values_only=True):
        g = lambda k: ("" if cols.get(k) is None or cols[k] >= len(row) or row[cols[k]] is None else str(row[cols[k]]).strip())   # noqa: E731
        if not any(g(k) for k in ("ref", "tag")):
            continue
        out.append({k: g(k) for k in ("ref", "tag", "rule", "field", "reply", "date", "status", "closed_by")})
    return out


@router.post("/api/valve/projects/{pid}/inst/crs")
async def crs_import(pid: int, request: Request, file: UploadFile = File(...)):
    """A returned CRS: vendor replies and Open / Closed per comment.  Matched by the Ref column (sheet id | finding key),
    else by Tag + Rule + Field on the newest revision.  Replies belong to that revision (a new Rev starts open again)."""
    from app.valve import api
    by = api._user(request)
    try:
        rows = read_crs(await file.read())
    except Exception as e:                                # noqa: BLE001
        return Response(json.dumps({"error": str(e)}, ensure_ascii=False), status_code=400, media_type="application/json")
    con = con_ready()
    latest, _ = _latest(_sheet_rows(con, pid))
    by_tag = {r["tag_key"]: r for r in latest.values()}
    ids = {r["id"] for r in store.rows(con, "SELECT id FROM inst_sheet WHERE project_id=?", pid)}
    n = {"rows": len(rows), "matched": 0, "replies": 0, "closed": 0, "unmatched": []}
    for x in rows:
        sid, fk = None, None
        if "|" in x["ref"]:
            a, b = x["ref"].split("|", 1)
            if a.isdigit() and int(a) in ids:
                sid, fk = int(a), b
        if sid is None and x["tag"]:
            r = by_tag.get(instrument.tag_key(x["tag"]))
            if r:
                _, rv = reviewed(con, pid, r)
                hit = next((f for f in rv["rows"] if f.get("fkey") and f["rule"] == x["rule"] and f["item"] == x["field"]), None)
                if hit:
                    sid, fk = r["id"], hit["fkey"]
        if sid is None:
            n["unmatched"].append(f"{x['tag']} {x['rule']} {x['field']}".strip())
            continue
        st = "Closed" if x["status"].lower() in _CLOSED else "Open"
        if not x["reply"] and st == "Open":
            n["matched"] += 1
            continue
        con.execute("INSERT OR REPLACE INTO inst_reply(sheet_id, fkey, reply, reply_date, status, closed_by, file, by, at) VALUES (?,?,?,?,?,?,?,?,?)",
                    (sid, fk, x["reply"], x["date"], st, x["closed_by"], file.filename, by, store.now()))
        n["matched"] += 1
        n["replies"] += 1 if x["reply"] else 0
        n["closed"] += 1 if st == "Closed" else 0
    store.audit(con, pid, None, "inst.crs", "inst-crs-import", None, file.filename, by, f"{n['replies']} replies · {n['closed']} closed")
    con.commit()
    invalidate(pid)
    n["unmatched"] = n["unmatched"][:20]
    return _j(n)


@router.get("/api/valve/projects/{pid}/inst/progress")
def progress(pid: int, kind: str = "", weeks: int = 12):
    """Review progress by ISO week: datasheets received · engineer decisions · review codes set · comments closed,
    plus today's open comments and code distribution (latest revision of each tag)."""
    import datetime as dt
    con = con_ready()
    ksql, kargs = (" AND s.kind=?", [kind]) if kind else ("", [])
    wk = lambda t: dt.date.fromisoformat(t[:10]).isocalendar()[:2] if t and len(t) >= 10 else None   # noqa: E731
    today = dt.date.fromisoformat(store.now()[:10])
    keys = []
    for i in range(weeks - 1, -1, -1):
        y, w, _ = (today - dt.timedelta(weeks=i)).isocalendar()
        keys.append((y, w))
    ser = {k: {"week": f"{k[0]}-W{k[1]:02d}", "received": 0, "decisions": 0, "codes": 0, "closed": 0, "issues": 0, "open": 0} for k in keys}
    for r in store.rows(con, f"SELECT {_LIGHT} FROM inst_sheet s WHERE s.project_id=?{ksql}", pid, *kargs):
        w = wk(r["created_at"])
        if w not in ser:
            continue
        ser[w]["received"] += 1
        _, rv = reviewed(con, pid, r)                      # findings raised on the datasheets received that week, and still open now
        ser[w]["issues"] += sum(1 for x in rv["rows"] if x["result"] in (instreview.MISMATCH, instreview.MISSING, instreview.REVIEW, "Closed", "Dismissed"))
        ser[w]["open"] += rv["issues"]
    for r in store.rows(con, f"SELECT d.at t FROM inst_decision d JOIN inst_sheet s ON s.id=d.sheet_id WHERE s.project_id=?{ksql}", pid, *kargs):
        if wk(r["t"]) in ser:
            ser[wk(r["t"])]["decisions"] += 1
    for r in store.rows(con, f"SELECT p.at t FROM inst_reply p JOIN inst_sheet s ON s.id=p.sheet_id WHERE p.status='Closed' AND s.project_id=?{ksql}", pid, *kargs):
        if wk(r["t"]) in ser:
            ser[wk(r["t"])]["closed"] += 1
    codes_set = store.rows(con, "SELECT a.at t, a.field_key f FROM audit a WHERE a.project_id=? AND a.action='inst-code'", pid)
    kind_of = {f"inst:{r['id']}": r["kind"] for r in store.rows(con, "SELECT id, kind FROM inst_sheet WHERE project_id=?", pid)}
    for r in codes_set:
        if (not kind or kind_of.get(r["f"]) == kind) and wk(r["t"]) in ser:
            ser[wk(r["t"])]["codes"] += 1
    latest, _ = _latest(_sheet_rows(con, pid, kind))
    now = {"tags": len(latest), "open": 0, "closed": 0, "dismissed": 0, "codes": {}, "no_code": 0}
    for r in latest.values():
        _, rv = reviewed(con, pid, r)
        now["open"] += rv["issues"]
        now["closed"] += rv["counts"].get("Closed", 0)
        now["dismissed"] += rv["counts"].get("Dismissed", 0)
        c = r.get("review_code") or ""
        if c:
            now["codes"][c] = now["codes"].get(c, 0) + 1
        else:
            now["no_code"] += 1
    return _j({"weeks": [ser[k] for k in keys], "now": now, "codes": codes_for(con, pid)})


@router.get("/api/valve/projects/{pid}/inst/crs.xlsx")
def crs_xlsx(pid: int, kind: str = ""):
    """Comment Resolution Sheet — what goes back to the vendor: one row per open (not dismissed) finding, the engineer's
    wording, the document's review code, and empty Vendor Reply / Close-out columns for the next round."""
    from app.valve.instmarkup import callout_text, reason_en, _en
    con = con_ready()
    latest, _ = _latest(_sheet_rows(con, pid, kind))
    codes = {c["code"]: c["label"] for c in codes_for(con, pid)}
    p = store.one(con, "SELECT name FROM project WHERE id=?", pid)
    head = ["No", "Doc. No.", "Rev", "Tag", "Item", "Form", "Page", "Field", "Comment (EN)", "Comment (KO)", "Datasheet value", "Reference value",
            "Reference document", "Rule", "Result", "Engineer decision", "Comment by", "Date", "Review Code", "Vendor Reply", "Reply Date", "Status", "Closed by", "Ref (do not edit)"]
    rows, summ, n = [], [], 0
    for r in sorted(latest.values(), key=lambda r: (ORDER.index(r["kind"]) if r["kind"] in ORDER else 99, r["tag_key"])):
        _, rv = reviewed(con, pid, r)
        code = r.get("review_code") or ""
        open_ = [x for x in rv["rows"] if x["result"] in (instreview.MISMATCH, instreview.MISSING, instreview.REVIEW, "Closed")]
        summ.append([r["tag"], KIND_NAMES.get(r["kind"], r["kind"]), r["doc_no"], r["rev"], len(open_), code, codes.get(code, ""),
                     rv.get("suggested_code", ""), codes.get(rv.get("suggested_code", ""), ""), r["status"]])
        for x in open_:
            n += 1
            d = x.get("decision") or {}
            en = reason_en(x) if not (d.get("decision") == "Modified" and d.get("text")) else _en(d["text"]) or reason_en(x)
            rows.append([n, r["doc_no"], r["rev"], r["tag"], KIND_NAMES.get(r["kind"], r["kind"]), r["form_id"], x.get("page") or "", x["item"],
                         en, x["reason"], str(x["ds"] or ""), str(x["ref"] or ""), x.get("source") or "", x["rule"], x["result"],
                         (d.get("decision") or "Open") + (f" ({d['origin']})" if d.get("origin") else ""), d.get("by") or "", (d.get("at") or "")[:10],
                         f"{code} {codes.get(code, '')}".strip(), (x.get("reply") or {}).get("reply", ""), (x.get("reply") or {}).get("date", ""),
                         (x.get("reply") or {}).get("status", "Open") or "Open", (x.get("reply") or {}).get("closed_by", ""), f"{r['id']}|{x['fkey']}"])
    import io as _io
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CRS"
    ws.append([f"COMMENT RESOLUTION SHEET — {(p or {}).get('name', '')} · Instrument Datasheets{' · ' + KIND_NAMES.get(kind, kind) if kind else ''}"])
    ws.append([f"Generated {store.now()[:16].replace('T', ' ')} · {n} open comments · codes: " + " · ".join(f"{c} {l}" for c, l in codes.items())])
    ws.append(head)
    ws["A1"].font = Font(bold=True, size=13)
    for c in ws[3]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
    wrap = Alignment(wrap_text=True, vertical="top")
    for r_ in rows:
        ws.append(r_)
    for col in ("I", "J", "T"):                            # wrap only the long text columns
        for c in ws[col][3:]:
            c.alignment = wrap
    widths = {"A": 6, "B": 22, "C": 6, "D": 16, "E": 22, "F": 7, "G": 6, "H": 26, "I": 60, "J": 50, "K": 26, "L": 26, "M": 30, "N": 11,
              "O": 15, "P": 18, "Q": 14, "R": 11, "S": 26, "T": 40, "U": 11, "V": 9, "W": 12, "X": 14}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "E4"
    from openpyxl.worksheet.datavalidation import DataValidation
    dv = DataValidation(type="list", formula1='"Open,Closed"', allow_blank=True)   # the vendor / engineer picks, does not type
    ws.add_data_validation(dv)
    if ws.max_row >= 4:
        dv.add(f"V4:V{ws.max_row}")
    ws.auto_filter.ref = f"A3:{openpyxl.utils.get_column_letter(len(head))}{max(3, ws.max_row)}"
    ws2 = wb.create_sheet("Review Codes")
    ws2.append(["Tag", "Item", "Doc. No.", "Rev", "Open comments", "Code", "Code meaning", "Suggested", "Suggested meaning", "Review status"])
    for c in ws2[1]:
        c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A5F")
    for r_ in summ:
        ws2.append(r_)
    ws2.freeze_panes = "A2"
    b = _io.BytesIO()
    wb.save(b)
    return Response(b.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=instrument_CRS{'_' + kind if kind else ''}.xlsx"})


def _cells(sh: dict) -> list[dict]:
    """Every numbered row of the sheet's form with what was read and where (page · value cell)."""
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
    return rows


def _markup_response(con, pid, sheet_rows, name, flatten):
    from app.valve import instmarkup
    entries = []
    for r in sheet_rows:
        doc = store.one(con, "SELECT path FROM document WHERE id=?", r["document_id"])
        if not doc:
            continue
        sh, rv = reviewed(con, pid, r)
        entries.append({"path": doc["path"], "sheet": sh, "rows": _cells(sh), "findings": rv["rows"], "tag": r["tag"],
                        "kind": KIND_NAMES.get(r["kind"], r["kind"]), "doc_no": r["doc_no"], "rev": r["rev"]})
    if not entries:
        return Response('{"error":"표시할 Datasheet 가 없습니다"}', status_code=404, media_type="application/json")
    p = store.one(con, "SELECT name FROM project WHERE id=?", pid)
    data = instmarkup.build(entries, (p or {}).get("name", ""), flatten=bool(flatten))
    return Response(data, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={name}"})


@router.get("/api/valve/inst/sheets/{sid}/markup.pdf")
def sheet_markup(sid: int, flatten: int = 0):
    """This datasheet with every finding marked in the PDF: shaded cell + arrow callout with the reason."""
    con = con_ready()
    r = store.one(con, "SELECT s.*, d.filename FROM inst_sheet s LEFT JOIN document d ON d.id=s.document_id WHERE s.id=?", sid)
    if not r:
        return Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", r["tag"])
    return _markup_response(con, r["project_id"], [r], f"{safe}_Rev{r['rev'] or '-'}_markup.pdf", flatten)


@router.get("/api/valve/projects/{pid}/inst/markup.pdf")
def project_markup(pid: int, kind: str = "", flatten: int = 0, all: int = 0):
    """All latest datasheets (of one kind) that have findings — one PDF, summary page first."""
    con = con_ready()
    latest, _ = _latest(_sheet_rows(con, pid, kind))
    rows = sorted(latest.values(), key=lambda r: (ORDER.index(r["kind"]) if r["kind"] in ORDER else 99, r["tag_key"]))
    if not all:
        rows = [r for r in rows if reviewed(con, pid, r)[1]["issues"]]
    return _markup_response(con, pid, rows, f"instrument_markup{'_' + kind if kind else ''}.pdf", flatten)


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
    invalidate(r["project_id"])
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
    invalidate(pid)
    return _j({"ok": True, "confirmed": cur})


LIST_NAMES = {"instrument_index": "Instrument Index", "io_list": "IO List"}
VALVE_KINDS = {"ball": "Ball Valve", "globe": "Globe Valve", "butterfly": "Butterfly Valve", "psv": "PSV"}


def valve_rows(con, pid) -> list[dict]:
    """The Valve datasheets of this project and of its kind projects ('<name> · Globe Valve' …), newest revision per tag —
    so the Instrument List / IO List comparison covers Valve and Instrument together (user 2026-11-12)."""
    from app.valve import schema
    me = store.one(con, "SELECT name FROM project WHERE id=?", pid)
    if not me:
        return []
    base = re.sub(r"\s*·\s*(Globe Valve|Butterfly Valve|PSV)$", "", me["name"])
    out = []
    for p in store.rows(con, "SELECT id, name FROM project"):
        if re.sub(r"\s*·\s*(Globe Valve|Butterfly Valve|PSV)$", "", p["name"]) != base:
            continue
        vk = schema.project_kind(p["name"])
        dss = store.rows(con, "SELECT id, tag, tag_key, rev, doc_no FROM datasheet WHERE project_id=?", p["id"])
        latest = {}
        for d in sorted(dss, key=lambda d: (store.rev_key(d["rev"]), d["id"])):
            latest[d["tag_key"]] = d
        for d in latest.values():
            fs = {f["key"]: store.field_value(f) for f in store.rows(
                con, "SELECT key, value, edited_value FROM field WHERE datasheet_id=? AND key IN ('service','pid_no','line_no','fluid','manufacturer','model')", d["id"])}
            out.append({"tag": d["tag"], "tag_key": instrument.tag_key(d["tag"]), "kind": vk, "sheet_id": None, "valve_ds": d["id"], "valve_project": p["name"],
                        "values": {"service": fs.get("service", ""), "pid_no": fs.get("pid_no", ""), "line_no": fs.get("line_no", ""), "fluid": fs.get("fluid", ""),
                                   "range": "", "datasheet_no": d["doc_no"] or "", "manufacturer": fs.get("manufacturer", ""), "model": fs.get("model", "")}})
    return out


def listcmp_rows(con, pid, only: str = "") -> dict:
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
    inst_keys = {d["tag_key"] for d in ds_rows}
    vrows = [v for v in valve_rows(con, pid) if v["tag_key"] not in inst_keys]     # a tag read on both sides: the Instrument sheet stands
    ds_rows += vrows
    vmap = {v["tag_key"]: v for v in vrows}
    out = []
    for k, nm in LIST_NAMES.items():
        if not only or only == k:
            out += instlists.compare(ds_rows, ctx["lists"].get(k), nm)
    has_ds = {d["tag_key"]: d for d in ds_rows}
    for x in out:                                          # a Valve tag opens on the Valve screen (?ds=)
        v = vmap.get(instrument.tag_key(x["tag"]))
        if v:
            x["valve_ds"], x["valve_project"] = v["valve_ds"], v["valve_project"]
    cnt = {}
    for x in out:
        cnt.setdefault(x["list"], {}).setdefault(x["result"], 0)
        cnt[x["list"]][x["result"]] += 1
    recs = []
    if only and ctx["lists"].get(only):                    # the list itself, as read (one row per tag) + is there a datasheet
        for tk, r in sorted(ctx["lists"][only]["by_tag"].items()):
            d = has_ds.get(tk)
            recs.append(dict({k: v for k, v in r.items() if k not in ("bbox",)}, ds_kind=d["kind"] if d else "", sheet_id=d["sheet_id"] if d else None,
                             valve_ds=d.get("valve_ds") if d else None, valve_project=d.get("valve_project") if d else None,
                             findings=sum(1 for x in out if instrument.tag_key(x["tag"]) == tk and x["result"] not in ("OK",))))
    return {"rows": out, "counts": cnt, "records": recs, "only": only, "n_inst": len(inst_keys), "n_valve": len(vrows),
            "lists": {k: {"files": v["files"], "rev": v["rev"], "doc_no": v.get("doc_no", ""), "tags": len(v["by_tag"])} for k, v in ctx["lists"].items()}}


@router.get("/api/valve/projects/{pid}/inst/listcmp")
def listcmp(pid: int, list: str = ""):
    return _j(listcmp_rows(con_ready(), pid, list if list in LIST_NAMES else ""))


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
        pf = {k: PatternFill("solid", fgColor=v) for k, v in fills.items()}   # one fill object per colour
        for i, r in enumerate(rows, 2):
            ws.append(r)
            res = next((v for v in r if isinstance(v, str) and v in fills), None)
            if res:
                for j in range(1, len(r) + 1):             # by row/column number — ws[i] / ws.max_row walk every cell (O(n²))
                    ws.cell(row=i, column=j).fill = pf[res]
        for i, h in enumerate(head, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = max(10, min(48, len(h) + 6))
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


@router.get("/api/valve/projects/{pid}/inst/listcmp.xlsx")
def listcmp_xlsx(pid: int, list: str = ""):
    d = listcmp_rows(con_ready(), pid, list if list in LIST_NAMES else "")
    head = ["List", "Rule", "Tag", "Kind", "Item", "Datasheet", "List value", "Result", "Reason", "List page"]
    rows = [[x["list"], x["rule"], x["tag"], KIND_NAMES.get(x["kind"]) or VALVE_KINDS.get(x["kind"], x["kind"]), x["field"], x["ds"], x["lst"], x["result"], x["reason"], x.get("page")] for x in d["rows"]]
    sheets = [("List 대조", head, rows)]
    if d["records"]:
        rh = ["Tag", "Loop", "Type", "Service", "P&ID", "Line", "Range", "Datasheet No", "Manufacturer", "Model", "IO", "Datasheet", "Findings", "Page"]
        sheets.append(("List 내용", rh, [[r.get("tag"), r.get("loop"), r.get("inst_type"), r.get("service"), r.get("pid_no"), r.get("line_no"),
                                          r.get("range"), r.get("datasheet_no"), r.get("manufacturer"), r.get("model"), r.get("io_typical"),
                                          (KIND_NAMES.get(r["ds_kind"]) or VALVE_KINDS.get(r["ds_kind"], r["ds_kind"])) if r["ds_kind"] else "없음", r["findings"], r.get("page")] for r in d["records"]]))
    data = _xlsx(sheets)
    nm = {"instrument_index": "instrument_index", "io_list": "io_list"}.get(d["only"], "instrument_list")
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename={nm}_compare.xlsx"})


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


@router.get("/api/valve/inst/sheets/{sid}/json")
def inst_sheet_json(sid: int):
    """valve40: the Instrument datasheet as read — the same content as its JSON file (dsjson.py)."""
    from app.valve import dsjson
    r = dsjson.inst_record(con_ready(), sid)
    return _j(r) if r else Response('{"error":"없는 Datasheet"}', status_code=404, media_type="application/json")
