"""Valve Datasheet Review — SQLite storage ({data}/valve/valve.db) and original files ({data}/valve/files/).

Originals are stored once by content hash and never written again (spec rule 12).  Everything the reviewer
changes is a new row in `audit` — the extracted value stays as read, the edited value sits beside it.

Tables
  project    id · name · created_at
  document   id · project_id · kind (datasheet|valvelist|process|pms) · filename · sha256 · path · pages ·
             uploaded_by · uploaded_at · status (queued|running|done|error) · error · info(json)
  datasheet  id · project_id · document_id · tag · tag_key · valve_type · doc_no · rev · rev_date · title · form ·
             pages(json) · notes(json) · rev_history(json) · review_status · created_at
  field      id · datasheet_id · key · section · display · label · row · value · unit · page · bbox(json) ·
             status (ok|blank|placeholder|review) · ref(json) · edited_value · edited_by · edited_at
  audit      id · project_id · datasheet_id · field_key · action · before · after · by · at · comment
  issue_state datasheet_id · ikey · status (Open|Confirmed|Dismissed|Resolved) · note · by · at  (computed issues' review state)
  comment    id · datasheet_id · field_key · text · by · at · page · bbox(json) · category · deleted · kind · points(json)
             (a user mark-up is a comment with a page and box; kind = rect/cloud/ellipse/highlight/line/arrow/pen/text/note,
              points = line ends or pen strokes in PDF points; category = comment/error/missing/question;
              deleting keeps the row, deleted=1)
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sqlite3
import threading
from pathlib import Path

from app import paths

_LOCK = threading.RLock()
REVIEW_STATUSES = ["Not Reviewed", "Under Review", "Accepted", "Rejected", "Commented", "Resolved"]

_SCHEMA = """
CREATE TABLE IF NOT EXISTS project (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, created_at TEXT);
CREATE TABLE IF NOT EXISTS document (id INTEGER PRIMARY KEY, project_id INTEGER, kind TEXT, filename TEXT,
  sha256 TEXT, path TEXT, pages INTEGER, uploaded_by TEXT, uploaded_at TEXT, status TEXT, error TEXT, info TEXT);
CREATE TABLE IF NOT EXISTS datasheet (id INTEGER PRIMARY KEY, project_id INTEGER, document_id INTEGER, tag TEXT,
  tag_key TEXT, valve_type TEXT, doc_no TEXT, rev TEXT, rev_date TEXT, title TEXT, form TEXT, pages TEXT,
  notes TEXT, rev_history TEXT, review_status TEXT DEFAULT 'Not Reviewed', created_at TEXT);
CREATE INDEX IF NOT EXISTS ds_tag ON datasheet(project_id, tag_key);
CREATE TABLE IF NOT EXISTS field (id INTEGER PRIMARY KEY, datasheet_id INTEGER, key TEXT, section TEXT, display TEXT,
  label TEXT, row INTEGER, value TEXT, unit TEXT, page INTEGER, bbox TEXT, status TEXT, ref TEXT,
  edited_value TEXT, edited_by TEXT, edited_at TEXT);
CREATE INDEX IF NOT EXISTS field_ds ON field(datasheet_id);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, project_id INTEGER, datasheet_id INTEGER, field_key TEXT,
  action TEXT, before TEXT, after TEXT, by TEXT, at TEXT, comment TEXT);
CREATE TABLE IF NOT EXISTS issue_state (datasheet_id INTEGER, ikey TEXT, status TEXT, note TEXT, by TEXT, at TEXT,
  PRIMARY KEY (datasheet_id, ikey));
CREATE TABLE IF NOT EXISTS comment (id INTEGER PRIMARY KEY, datasheet_id INTEGER, field_key TEXT, text TEXT,
  by TEXT, at TEXT, page INTEGER, bbox TEXT, category TEXT DEFAULT 'comment', deleted INTEGER DEFAULT 0);
"""


def root() -> Path:
    return paths.data_dir() / "valve"


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    root().mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(root() / "valve.db"), timeout=30, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(_SCHEMA)
    _migrate(con)
    return con


_ADDED = {"datasheet": [("sheets", "TEXT")],
          "comment": [("page", "INTEGER"), ("bbox", "TEXT"), ("category", "TEXT DEFAULT 'comment'"),
                      ("deleted", "INTEGER DEFAULT 0"), ("kind", "TEXT"), ("points", "TEXT")]}


def _migrate(con):
    """Columns added after a database was first made (older valve.db keeps working)."""
    for table, cols in _ADDED.items():
        have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        for name, typ in cols:
            if name not in have:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
    con.commit()


def rows(con, sql, *args):
    return [dict(r) for r in con.execute(sql, args).fetchall()]


def one(con, sql, *args):
    r = con.execute(sql, args).fetchone()
    return dict(r) if r else None


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def J(v):
    return json.dumps(v, ensure_ascii=False) if v is not None else None


def unJ(v, default=None):
    if v is None:
        return default
    try:
        return json.loads(v)
    except ValueError:
        return default


# ── projects ───────────────────────────────────────────────────────────────────

def project_get_or_create(con, name: str) -> dict:
    name = " ".join((name or "").split())[:80]
    if not name:
        raise ValueError("프로젝트 이름이 비었습니다")
    with _LOCK:
        p = one(con, "SELECT * FROM project WHERE name=?", name)
        if p:
            return p
        con.execute("INSERT INTO project(name, created_at) VALUES (?, ?)", (name, now()))
        con.commit()
        return one(con, "SELECT * FROM project WHERE name=?", name)


# ── files ──────────────────────────────────────────────────────────────────────

def save_original(data: bytes, filename: str) -> tuple[str, Path]:
    """Store bytes once under their hash.  An existing file with the same hash is left untouched."""
    sha = hashlib.sha256(data).hexdigest()
    ext = Path(filename).suffix.lower()[:6] or ".bin"
    p = root() / "files" / f"{sha[:16]}{ext}"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        tmp = p.with_suffix(p.suffix + ".part")
        tmp.write_bytes(data)
        tmp.replace(p)
    return sha, p


# ── datasheets ─────────────────────────────────────────────────────────────────

def insert_datasheet(con, project_id: int, document_id: int, ds: dict) -> int:
    cur = con.execute(
        "INSERT INTO datasheet(project_id, document_id, tag, tag_key, valve_type, doc_no, rev, rev_date, title, form,"
        " pages, notes, rev_history, created_at, sheets) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (project_id, document_id, ds["tag"], ds["tag_key"], ds["valve_type"], ds["doc_no"], ds["rev"], ds.get("date", ""),
         ds.get("title", ""), ds.get("form", ""), J(ds["pages"]), J(ds["notes"]), J(ds.get("rev_history", [])), now(),
         J(ds.get("sheets"))))
    dsid = cur.lastrowid
    con.executemany(
        "INSERT INTO field(datasheet_id, key, section, display, label, row, value, unit, page, bbox, status, ref)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [(dsid, k, r.get("section"), r.get("display"), r.get("label"), r.get("row"), r.get("value"), r.get("unit"),
          r.get("page"), J(r.get("bbox")), r.get("status"), J(r.get("ref"))) for k, r in ds["fields"].items()])
    return dsid


def refresh_datasheet(con, dsid: int, ds: dict) -> dict:
    """Re-read of the same PDF (a newer reader): read values are replaced in place, everything a reviewer did stays —
    corrections (edited_*), comments · mark-ups, issue states, review status.  Field ids stay, so links keep working."""
    con.execute("UPDATE datasheet SET tag=?, valve_type=?, doc_no=?, rev_date=?, title=?, form=?, pages=?, notes=?,"
                " rev_history=?, sheets=? WHERE id=?",
                (ds["tag"], ds["valve_type"], ds["doc_no"], ds.get("date", ""), ds.get("title", ""), ds.get("form", ""),
                 J(ds["pages"]), J(ds["notes"]), J(ds.get("rev_history", [])), J(ds.get("sheets")), dsid))
    old = {r["key"]: r for r in rows(con, "SELECT id, key, value, edited_value FROM field WHERE datasheet_id=?", dsid)}
    changed = 0
    for k, r in ds["fields"].items():
        vals = (r.get("section"), r.get("display"), r.get("label"), r.get("row"), r.get("value"), r.get("unit"),
                r.get("page"), J(r.get("bbox")), r.get("status"), J(r.get("ref")))
        if k in old:
            changed += (old[k]["value"] or "") != (r.get("value") or "")
            con.execute("UPDATE field SET section=?, display=?, label=?, row=?, value=?, unit=?, page=?, bbox=?, status=?,"
                        " ref=? WHERE id=?", (*vals, old[k]["id"]))
        else:
            changed += 1
            con.execute("INSERT INTO field(datasheet_id, key, section, display, label, row, value, unit, page, bbox, status,"
                        " ref) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (dsid, k, *vals))
    gone = [o for k, o in old.items() if k not in ds["fields"] and o["edited_value"] is None]
    con.executemany("DELETE FROM field WHERE id=?", [(o["id"],) for o in gone])
    return {"changed": changed, "removed": len(gone)}


def audit(con, project_id, datasheet_id, field_key, action, before, after, by, comment=""):
    con.execute("INSERT INTO audit(project_id, datasheet_id, field_key, action, before, after, by, at, comment)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (project_id, datasheet_id, field_key, action, before, after, by, now(), comment))


_REV_ORDER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def rev_key(rev: str):
    """EPC revision order: A < B < … (pre-approval letters) < 0 < 1 < 2 … (numbered issues)."""
    r = (rev or "").strip().upper()
    if r.isdigit():
        return (1, int(r), "")
    if r and r[0] in _REV_ORDER:
        return (0, _REV_ORDER.index(r[0]), r)
    return (-1, 0, r)


def field_value(f: dict) -> str:
    return f["edited_value"] if f.get("edited_value") is not None else (f.get("value") or "")
