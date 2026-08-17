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
    deleted       INTEGER NOT NULL DEFAULT 0,
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

CREATE INDEX IF NOT EXISTS item_job_tab ON item(job_id, tab);
CREATE INDEX IF NOT EXISTS item_job_page ON item(job_id, page_no);
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
    for key in existing:
        if key not in seen:
            con.execute(
                "UPDATE item SET deleted=1, needs_review=? WHERE job_id=? AND key=?",
                ("this row was not found by the latest analysis", job_id, key))
            gone += 1

    con.execute("UPDATE job SET status='done', progress=1.0, message='done',"
                " fingerprint=?, engine_json=? WHERE id=?",
                (result.get("fingerprint", ""),
                 json.dumps({k: result.get(k) for k in
                             ("multipliers", "legend", "glyphs", "job_review")},
                            default=str),
                 job_id))
    con.commit()
    return {"rows": len(result["rows"]), "conflicts": conflicts,
            "kept_edits": kept_edits, "vanished": gone}


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
    out = []
    for r in con.execute(sql + " ORDER BY page_no, key", args).fetchall():
        ai = json.loads(r["ai_json"])
        user = json.loads(r["user_json"])
        merged = dict(ai)
        merged.update({k: v for k, v in user.items() if v is not None})
        out.append({
            "key": r["key"], "tab": r["tab"], "page_no": r["page_no"],
            "drawing_no": r["drawing_no"], "origin": r["origin"],
            "rect": json.loads(r["rect_json"]),
            "values": merged, "ai": ai, "user": user,
            "evidence": json.loads(r["evidence_json"]),
            "needs_review": r["needs_review"], "annotation": r["annotation"],
            "conflict": json.loads(r["conflict_json"]),
            "deleted": bool(r["deleted"]),
        })
    return out


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
        "SELECT COUNT(*) FROM item WHERE job_id=? AND (needs_review<>'' OR deleted=1)",
        (job_id,)).fetchone()[0]


# --------------------------------------------------------------------------
# Revisions - the only thing Excel is ever generated from
# --------------------------------------------------------------------------

# Which page-origin sets a snapshot covers.  The default is everything: the
# tool has no opinion about whether a drawing the client's Excel does not cover
# should be delivered, so a reviewer takes sets *out* rather than adding them.
ALL_ORIGINS = ("MATCHED", "REVISION_GAP", "PDF_ONLY")


def snapshot(con, job_id: str, label: str = "", origins=None) -> int:
    origins = tuple(origins) if origins else ALL_ORIGINS
    # A row whose origin could not be determined is kept, not dropped: silently
    # losing rows from a delivered workbook is the one failure mode this gate
    # exists to prevent, and an unknown origin is a reason to look, not to omit.
    rows = [r for r in merged_rows(con, job_id)
            if not r["origin"] or r["origin"] in origins]
    job = get_job(con, job_id)
    payload = {
        "origins_included": list(origins),
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
