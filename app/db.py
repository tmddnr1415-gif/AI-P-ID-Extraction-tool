"""Storage (docs/design.md section 4), with AI output and human edits kept apart.

The one rule that shapes this file: **what the engine decided and what a person
decided are never written to the same column.**  Re-analysing a PDF replaces
`ai_values` wholesale and does not touch `user_values`, so a reviewer's work
survives a re-run; and because both are kept, the UI can always show what the
engine said even after someone overrode it.

When a re-analysis changes a field a reviewer had already edited, that is a
conflict: the row is flagged NEEDS_REVIEW with both values recorded, and
neither is silently preferred.

`revision` holds output snapshots.  Excel is generated only from a snapshot,
never from the live table, so a delivered file always corresponds to a state
someone signed off.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS job (
    id           TEXT PRIMARY KEY,
    pdf_name     TEXT NOT NULL,
    pdf_sha256   TEXT NOT NULL,
    pdf_path     TEXT NOT NULL,
    created_at   REAL NOT NULL,
    status       TEXT NOT NULL,          -- queued | running | done | failed
    progress     REAL NOT NULL DEFAULT 0,
    message      TEXT NOT NULL DEFAULT '',
    fingerprint  TEXT NOT NULL DEFAULT '',
    engine_json  TEXT NOT NULL DEFAULT '{}'   -- multipliers, legend, glyphs
);

CREATE TABLE IF NOT EXISTS pid_page (
    job_id       TEXT NOT NULL,
    page_no      INTEGER NOT NULL,
    drawing_no   TEXT,
    title        TEXT,
    page_kind    TEXT,
    in_scope     INTEGER NOT NULL DEFAULT 1,
    scope_reason TEXT NOT NULL DEFAULT '',
    width        REAL, height REAL,
    layers_json  TEXT NOT NULL DEFAULT '{}',
    PRIMARY KEY (job_id, page_no)
);

CREATE TABLE IF NOT EXISTS item (
    job_id        TEXT NOT NULL,
    key           TEXT NOT NULL,          -- stable across re-analysis
    tab           TEXT NOT NULL,
    page_no       INTEGER NOT NULL,
    drawing_no    TEXT NOT NULL DEFAULT '',
    origin        TEXT NOT NULL DEFAULT '',   -- MATCHED | PDF_ONLY | REVISION_GAP
    rect_json     TEXT NOT NULL DEFAULT '[]',
    ai_json       TEXT NOT NULL,          -- what the engine decided
    user_json     TEXT NOT NULL DEFAULT '{}',   -- what a person decided
    evidence_json TEXT NOT NULL DEFAULT '{}',
    needs_review  TEXT NOT NULL DEFAULT '',
    annotation    TEXT NOT NULL DEFAULT '',
    conflict_json TEXT NOT NULL DEFAULT '{}',
    deleted       INTEGER NOT NULL DEFAULT 0,   -- engine no longer finds it
    added         INTEGER NOT NULL DEFAULT 0,   -- a reviewer created it
    removed       INTEGER NOT NULL DEFAULT 0,   -- a reviewer struck it out
    PRIMARY KEY (job_id, key)
);

CREATE TABLE IF NOT EXISTS revision (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    created_at  REAL NOT NULL,
    label       TEXT NOT NULL DEFAULT '',
    row_count   INTEGER NOT NULL,
    review_count INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);

-- Every correction a reviewer makes, with the evidence that was in front of the
-- engine when it got it wrong.  This table is written and never read back by the
-- app: it exists so that a later pass over a *finished* project can ask which
-- rules keep failing, and that question is unanswerable after the fact unless
-- the geometry is captured at the moment of the correction.  No judgement is
-- stored - `pattern` is a mechanical key so occurrences can be counted later,
-- not a diagnosis.
CREATE TABLE IF NOT EXISTS feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id       TEXT NOT NULL,
    created_at   REAL NOT NULL,
    kind         TEXT NOT NULL,          -- ADDED | REMOVED | EDITED
    row_key      TEXT NOT NULL DEFAULT '',
    page_no      INTEGER,
    drawing_no   TEXT NOT NULL DEFAULT '',
    rect_json    TEXT NOT NULL DEFAULT '[]',
    field        TEXT NOT NULL DEFAULT '',   -- EDITED: which column
    ai_value     TEXT NOT NULL DEFAULT '',   -- EDITED: what the engine said
    user_value   TEXT NOT NULL DEFAULT '',   -- EDITED / ADDED: what a person said
    reason       TEXT NOT NULL DEFAULT '',   -- optional, typed by the reviewer
    pattern      TEXT NOT NULL DEFAULT '',   -- countable key, see _pattern()
    basis_json   TEXT NOT NULL DEFAULT '{}', -- the row's whole evidence
    geometry_json TEXT NOT NULL DEFAULT '{}' -- ADDED: what is drawn there
);

CREATE INDEX IF NOT EXISTS item_job_tab ON item(job_id, tab);
CREATE INDEX IF NOT EXISTS item_job_page ON item(job_id, page_no);
CREATE INDEX IF NOT EXISTS feedback_job ON feedback(job_id, kind);
CREATE INDEX IF NOT EXISTS feedback_pattern ON feedback(job_id, pattern);
"""

# Columns a reviewer may edit.  Description and Tag No. are in the list because
# they are deliberately left empty by the engine (Phase 2 / not assigned on
# these drawings), so a human filling them in is the expected case.
EDITABLE = ("type", "qty", "system", "valve_type", "vendor_supply", "scope",
            "description", "tag_no")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(SCHEMA)
    return con


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------

def create_job(con, job_id: str, pdf_name: str, pdf_sha: str, pdf_path: Path):
    con.execute(
        "INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status)"
        " VALUES (?,?,?,?,?,?)",
        (job_id, pdf_name, pdf_sha, str(pdf_path), time.time(), "queued"))
    con.commit()


def set_progress(con, job_id: str, progress: float, message: str,
                 status: str = "running"):
    con.execute("UPDATE job SET progress=?, message=?, status=? WHERE id=?",
                (progress, message, status, job_id))
    con.commit()


def get_job(con, job_id: str):
    return con.execute("SELECT * FROM job WHERE id=?", (job_id,)).fetchone()


def list_jobs(con):
    return con.execute("SELECT * FROM job ORDER BY created_at DESC").fetchall()


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------

def _ai_of(row: dict) -> dict:
    return {k: row.get(k) for k in EDITABLE}


def store_result(con, job_id: str, result: dict) -> dict:
    """Write an analysis in, preserving anything a reviewer already changed.

    Returns a summary of what happened, including the conflicts - fields where
    the engine's new answer differs from one a person had overridden.  Those are
    not resolved here: both values are kept and the row goes to review.
    """
    con.execute("DELETE FROM pid_page WHERE job_id=?", (job_id,))
    for p in result["pages"]:
        con.execute(
            "INSERT INTO pid_page (job_id,page_no,drawing_no,title,page_kind,"
            "in_scope,scope_reason,width,height,layers_json) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (job_id, p["page_no"], p["drawing_no"], p["title"], p["page_kind"],
             int(p["in_scope"]), p["scope_reason"], p["width"], p["height"],
             json.dumps(result["layers"].get(str(p["page_no"]), {}), sort_keys=True)))

    existing = {r["key"]: r for r in con.execute(
        "SELECT * FROM item WHERE job_id=?", (job_id,)).fetchall()}
    seen, conflicts, kept_edits = set(), [], 0

    for row in result["rows"]:
        key = row["key"]
        seen.add(key)
        ai = _ai_of(row)
        prev = existing.get(key)
        user = json.loads(prev["user_json"]) if prev else {}
        conflict = {}
        if prev:
            prev_ai = json.loads(prev["ai_json"])
            for field, value in user.items():
                # The engine changed its mind about a field a person had already
                # overridden.  Keeping the edit silently would hide a real
                # change; overwriting it would throw away review work.
                if prev_ai.get(field) != ai.get(field):
                    conflict[field] = {"was_ai": prev_ai.get(field),
                                       "now_ai": ai.get(field),
                                       "user": value}
            kept_edits += len(user)
        if conflict:
            conflicts.append({"key": key, "fields": conflict})
        review = row.get("needs_review", "")
        if conflict:
            review = "; ".join(filter(None, [
                review,
                "re-analysis changed " + ", ".join(sorted(conflict)) +
                " under an edit you made"]))
        con.execute(
            "INSERT INTO item (job_id,key,tab,page_no,drawing_no,origin,rect_json,"
            "ai_json,user_json,evidence_json,needs_review,annotation,conflict_json,"
            "deleted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,0)"
            " ON CONFLICT(job_id,key) DO UPDATE SET"
            "   tab=excluded.tab, page_no=excluded.page_no,"
            "   drawing_no=excluded.drawing_no, origin=excluded.origin,"
            "   rect_json=excluded.rect_json, ai_json=excluded.ai_json,"
            "   evidence_json=excluded.evidence_json,"
            "   needs_review=excluded.needs_review,"
            "   annotation=excluded.annotation,"
            "   conflict_json=excluded.conflict_json, deleted=0",
            (job_id, key, row["tab"], row["page_no"], row.get("drawing_no", ""),
             row.get("origin", ""), json.dumps(row["rect"]), json.dumps(ai, sort_keys=True),
             json.dumps(user, sort_keys=True),
             json.dumps(row["evidence"], sort_keys=True, default=str),
             review, row.get("annotation", ""),
             json.dumps(conflict, sort_keys=True)))

    # A row the engine no longer finds is marked rather than deleted: it may be
    # carrying a reviewer's edit, and losing that silently would be worse than
    # showing a row that has gone away.
    gone = 0
    for key, prev in existing.items():
        if prev["added"]:
            # A reviewer-created row is not something the engine can find, so
            # its absence from an analysis says nothing.  Marking it would have
            # struck out every hand-added row on each re-run.
            continue
        if key not in seen:
            con.execute(
                "UPDATE item SET deleted=1, needs_review=? WHERE job_id=? AND key=?",
                ("this row was not found by the latest analysis", job_id, key))
            gone += 1

    con.execute("UPDATE job SET status='done', progress=1.0, message='done',"
                " fingerprint=?, engine_json=? WHERE id=?",
                (result.get("fingerprint", ""),
                 json.dumps({k: result.get(k) for k in
                             ("multipliers", "legend", "glyphs", "job_review",
                              "applied_rules", "timings", "pipe_trace",
                              "description_scope", "description_build")},
                            default=str),
                 job_id))
    con.commit()
    return {"rows": len(result["rows"]), "conflicts": conflicts,
            "kept_edits": kept_edits, "vanished": gone}


def _merged(r) -> dict:
    """One item row as the reviewer sees it: engine values with edits laid over."""
    ai = json.loads(r["ai_json"])
    user = json.loads(r["user_json"])
    merged = dict(ai)
    merged.update({k: v for k, v in user.items() if v is not None})
    return {
        "key": r["key"], "tab": r["tab"], "page_no": r["page_no"],
        "drawing_no": r["drawing_no"], "origin": r["origin"],
        "rect": json.loads(r["rect_json"]),
        "values": merged, "ai": ai, "user": user,
        "evidence": json.loads(r["evidence_json"]),
        "needs_review": r["needs_review"], "annotation": r["annotation"],
        "conflict": json.loads(r["conflict_json"]),
        "deleted": bool(r["deleted"]),
        "added": bool(r["added"]), "removed": bool(r["removed"]),
    }


def get_row(con, job_id: str, key: str):
    """One merged row.  `merged_rows` builds all 893 of them, which is right for
    the grid and wasteful for an endpoint that needs only the row being edited -
    and that waste showed up as a race: the PATCH took long enough that a
    reviewer typing down a column had the next cell rebuilt under them."""
    r = con.execute("SELECT * FROM item WHERE job_id=? AND key=?",
                    (job_id, key)).fetchone()
    return _merged(r) if r else None


def merged_rows(con, job_id: str, tab: str = None) -> list:
    """Rows as the reviewer sees them: engine values with edits laid over."""
    sql = "SELECT * FROM item WHERE job_id=?"
    args = [job_id]
    if tab and tab != "ALL":
        if tab == "REVIEW":
            sql += " AND (needs_review<>'' OR deleted=1)"
        else:
            sql += " AND tab=?"
            args.append(tab)
    return [_merged(r) for r in
            con.execute(sql + " ORDER BY page_no, key", args).fetchall()]


def add_row(con, job_id: str, page_no: int, tab: str, origin: str = "",
            drawing_no: str = "", values: dict = None, source_key: str = None) -> str:
    """A row a reviewer created, by hand or by copying one.

    It has no `ai_values` - the engine never proposed it - so every value in it
    is a user value, and a re-analysis leaves it alone for the same reason it
    leaves an edit alone.  Reviewer-created rows are marked so a later reader can
    tell them from detections; nothing in the grid hides the difference.
    """
    import uuid
    key = "u" + uuid.uuid4().hex[:15]
    values = dict(values or {})
    con.execute(
        "INSERT INTO item (job_id,key,tab,page_no,drawing_no,origin,rect_json,"
        "ai_json,user_json,evidence_json,needs_review,annotation,conflict_json,"
        "deleted,added,removed) VALUES (?,?,?,?,?,?,'[]',?,?,?,?,'','{}',0,1,0)",
        (job_id, key, tab, page_no, drawing_no, origin,
         json.dumps({k: None for k in EDITABLE}, sort_keys=True),
         json.dumps(values, sort_keys=True),
         json.dumps({"added_by": "reviewer",
                     "copied_from": source_key} if source_key else
                    {"added_by": "reviewer"}, sort_keys=True),
         "reviewer-added row: no detection stands behind it"))
    con.commit()
    return key


def copy_row(con, job_id: str, key: str) -> str:
    src = con.execute("SELECT * FROM item WHERE job_id=? AND key=?",
                      (job_id, key)).fetchone()
    if src is None:
        raise KeyError(key)
    merged = json.loads(src["ai_json"])
    merged.update({k: v for k, v in json.loads(src["user_json"]).items()
                   if v is not None})
    return add_row(con, job_id, src["page_no"], src["tab"], src["origin"],
                   src["drawing_no"], merged, source_key=key)


def remove_row(con, job_id: str, key: str) -> dict:
    """Strike a row out.  Reviewer-created rows go for good; detections do not.

    A detection is never really deleted, because the next analysis would just
    bring it back and the reviewer's decision would be lost.  It is marked
    `removed`, which keeps it visible and out of the export.
    """
    row = con.execute("SELECT added FROM item WHERE job_id=? AND key=?",
                      (job_id, key)).fetchone()
    if row is None:
        raise KeyError(key)
    if row["added"]:
        con.execute("DELETE FROM item WHERE job_id=? AND key=?", (job_id, key))
        con.commit()
        return {"key": key, "dropped": True}
    con.execute("UPDATE item SET removed=1 WHERE job_id=? AND key=?", (job_id, key))
    con.commit()
    return {"key": key, "removed": True}


def restore_row(con, job_id: str, key: str) -> None:
    con.execute("UPDATE item SET removed=0 WHERE job_id=? AND key=?", (job_id, key))
    con.commit()


def set_user_value(con, job_id: str, key: str, field: str, value):
    if field not in EDITABLE:
        raise ValueError(f"{field} is not an editable column")
    row = con.execute("SELECT user_json, conflict_json FROM item"
                      " WHERE job_id=? AND key=?", (job_id, key)).fetchone()
    if row is None:
        raise KeyError(key)
    user = json.loads(row["user_json"])
    if value in (None, ""):
        user.pop(field, None)          # clearing an edit returns the AI value
    else:
        user[field] = value
    # Editing a field settles its conflict: the person has now looked at it.
    conflict = json.loads(row["conflict_json"])
    conflict.pop(field, None)
    con.execute("UPDATE item SET user_json=?, conflict_json=? WHERE job_id=? AND key=?",
                (json.dumps(user, sort_keys=True),
                 json.dumps(conflict, sort_keys=True), job_id, key))
    con.commit()
    return user


def review_count(con, job_id: str) -> int:
    return con.execute(
        "SELECT COUNT(*) FROM item WHERE job_id=? AND removed=0"
        " AND (needs_review<>'' OR deleted=1)", (job_id,)).fetchone()[0]


# --------------------------------------------------------------------------
# Correction history
# --------------------------------------------------------------------------

def _pattern(kind: str, **kw) -> str:
    """A countable key for one correction, derived mechanically.

    The point is that "the same thing was wrong 12 times" can be counted later
    without anybody having to interpret free text now.  Nothing here decides
    *why* something was wrong:

        EDITED|type|PIT>PDIT          a column changed from one value to another
        REMOVED|PIT|VENDOR_MARK_BOX   a detection struck out, with the rule that
                                      put it there
        ADDED|FIELD|PT                a row a person created, keyed by the nearest
                                      text the drawing has at that spot
    """
    if kind == "EDITED":
        return f"EDITED|{kw.get('field', '')}|{kw.get('ai', '')}>{kw.get('user', '')}"
    if kind == "REMOVED":
        return f"REMOVED|{kw.get('what', '')}|{kw.get('rule', '')}"
    return f"ADDED|{kw.get('tab', '')}|{kw.get('near', '')}"


def record_feedback(con, job_id: str, kind: str, *, row_key: str = "",
                    page_no: int = None, drawing_no: str = "", rect=None,
                    field: str = "", ai_value="", user_value="",
                    reason: str = "", basis: dict = None,
                    geometry: dict = None, pattern_args: dict = None) -> int:
    args = dict(pattern_args or {})
    cur = con.execute(
        "INSERT INTO feedback (job_id, created_at, kind, row_key, page_no,"
        " drawing_no, rect_json, field, ai_value, user_value, reason, pattern,"
        " basis_json, geometry_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (job_id, time.time(), kind, row_key, page_no, drawing_no,
         json.dumps(list(rect or []), default=str), field,
         "" if ai_value is None else str(ai_value),
         "" if user_value is None else str(user_value),
         reason, _pattern(kind, **args),
         json.dumps(basis or {}, default=str, sort_keys=True),
         json.dumps(geometry or {}, default=str, sort_keys=True)))
    con.commit()
    return cur.lastrowid


def feedback_count(con, job_id: str) -> int:
    return con.execute("SELECT COUNT(*) FROM feedback WHERE job_id=?",
                       (job_id,)).fetchone()[0]


def feedback_rows(con, job_id: str, limit: int = 200) -> list:
    """The history itself.  Returned as stored - no grouping, no counting by
    pattern: aggregating it is a later job, and doing it here would invite
    treating the aggregate as a finding."""
    out = []
    for r in con.execute(
            "SELECT * FROM feedback WHERE job_id=? ORDER BY id DESC LIMIT ?",
            (job_id, limit)):
        d = dict(r)
        for k in ("rect_json", "basis_json", "geometry_json"):
            d[k[:-5]] = json.loads(d.pop(k))
        out.append(d)
    return out


# --------------------------------------------------------------------------
# Revisions - the only thing Excel is ever generated from
# --------------------------------------------------------------------------

# Which page-origin sets a snapshot covers.  The default is everything: the
# tool has no opinion about whether a drawing the client's Excel does not cover
# should be delivered, so a reviewer takes sets *out* rather than adding them.
# DRAWING is what a page is when no answer key was supplied, which is every
# normal run; MATCHED and PDF_ONLY appear only in verification mode.
ALL_ORIGINS = ("DRAWING", "MATCHED", "REVISION_GAP", "PDF_ONLY")


def drawings_of(con, job_id: str) -> list:
    """Every drawing in the job with its row count, for the output-scope panel.

    The drawing is the unit a reviewer actually decides by: their contract covers
    some P&ID numbers and not others, and no amount of geometry can tell the tool
    which.  Grouped by system, because the client splits its packages that way.
    """
    out = {}
    for r in merged_rows(con, job_id):
        if r["removed"]:
            continue
        d = out.setdefault(r["drawing_no"], {
            "drawing_no": r["drawing_no"],
            "system": r["values"].get("system") or "",
            "pages": set(), "rows": 0, "review": 0})
        d["pages"].add(r["page_no"])
        d["rows"] += 1
        if r["needs_review"] or r["deleted"]:
            d["review"] += 1
    for d in out.values():
        d["pages"] = sorted(d["pages"])
    return sorted(out.values(), key=lambda d: (d["system"], d["drawing_no"]))


def snapshot(con, job_id: str, label: str = "", origins=None,
             drawings=None, hold_review: bool = False) -> int:
    """Freeze what is to be delivered.  Excel comes only from one of these.

    Three ways to narrow it, all of them the reviewer's decision and none of
    them the tool's: `origins` (the page-origin sets), `drawings` (P&ID numbers -
    the axis a contract is actually written on), and `hold_review`, which keeps
    rows whose judgement is still open out of the workbook.  Every one defaults
    to including everything: a reviewer takes rows *out*.
    """
    origins = tuple(origins) if origins else ALL_ORIGINS
    wanted = set(drawings) if drawings else None
    # A row whose origin could not be determined is kept, not dropped: silently
    # losing rows from a delivered workbook is the one failure mode this gate
    # exists to prevent, and an unknown origin is a reason to look, not to omit.
    rows = [r for r in merged_rows(con, job_id)
            if (not r["origin"] or r["origin"] in origins)
            and not r["removed"]
            and (wanted is None or r["drawing_no"] in wanted)
            and not (hold_review and (r["needs_review"] or r["deleted"]))]
    job = get_job(con, job_id)
    payload = {
        "origins_included": list(origins),
        "drawings_included": sorted(wanted) if wanted else None,
        "review_held_back": bool(hold_review),
        "job_id": job_id,
        "pdf_name": job["pdf_name"],
        "pdf_sha256": job["pdf_sha256"],
        "fingerprint": job["fingerprint"],
        "engine": json.loads(job["engine_json"]),
        "rows": rows,
    }
    cur = con.execute(
        "INSERT INTO revision (job_id, created_at, label, row_count, review_count,"
        " payload_json) VALUES (?,?,?,?,?,?)",
        (job_id, time.time(), label, len(rows), review_count(con, job_id),
         json.dumps(payload, sort_keys=True, default=str)))
    con.commit()
    return cur.lastrowid


def list_revisions(con, job_id: str):
    return con.execute(
        "SELECT id, created_at, label, row_count, review_count FROM revision"
        " WHERE job_id=? ORDER BY id DESC", (job_id,)).fetchall()


def get_revision(con, revision_id: int):
    r = con.execute("SELECT * FROM revision WHERE id=?", (revision_id,)).fetchone()
    return json.loads(r["payload_json"]) if r else None
