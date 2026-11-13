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
import time
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
CREATE TABLE IF NOT EXISTS decision_log (id INTEGER PRIMARY KEY, project_id INTEGER, datasheet_id INTEGER, tag TEXT, rev TEXT,
  ikey TEXT, rule TEXT, rule_ver TEXT, issue_type TEXT, finding TEXT, severity TEXT, actual TEXT, reference TEXT, source_doc TEXT,
  evidence TEXT, decision TEXT, status TEXT, reason_cat TEXT, reason TEXT, conclusion TEXT, modified_text TEXT,
  modified_severity TEXT, by TEXT, at TEXT);
CREATE INDEX IF NOT EXISTS dlog_rule ON decision_log(project_id, rule);
CREATE TABLE IF NOT EXISTS rule_change (id INTEGER PRIMARY KEY, project_id INTEGER, rule TEXT, from_ver TEXT, to_ver TEXT,
  current_logic TEXT, proposed_logic TEXT, reason TEXT, regression TEXT, simulation TEXT, status TEXT,
  approved_by TEXT, approved_at TEXT, created_by TEXT, created_at TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS project_setting (project_id INTEGER, key TEXT, value TEXT, by TEXT, at TEXT,
  PRIMARY KEY (project_id, key));
"""
# valve29 — engineer decisions sit BESIDE the issue status (status keeps driving exports · carry-over · counts)
DECISIONS = ["Confirmed", "Modified", "Dismissed", "Deferred", "Not Applicable"]
DECISION_STATUS = {"Confirmed": "Confirmed", "Modified": "Confirmed", "Dismissed": "Dismissed", "Not Applicable": "Dismissed",
                   "Deferred": "Open"}
REASON_CATS = ["Project Specification Exception", "Vendor Clarification", "Incorrect Rule Logic", "Incorrect Data Extraction",
               "Not Applicable", "Duplicate Finding", "Other"]
NEEDS_REASON = {"Dismissed", "Not Applicable", "Modified"}


def root() -> Path:
    return paths.data_dir() / "valve"


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


_READY: set = set()                      # db paths whose schema / migration ran in this process (once, not per request)
_READY_LOCK = threading.Lock()
WRITES = [0]                             # valve29: bumped on every commit in this process — the key of the screen response caches


class _Con(sqlite3.Connection):
    """A connection that counts its commits (store.WRITES): a screen answer computed before the last write is stale."""
    def commit(self):
        super().commit()
        WRITES[0] += 1


def connect() -> sqlite3.Connection:
    root().mkdir(parents=True, exist_ok=True)
    path = str(root() / "valve.db")
    con = sqlite3.connect(path, timeout=30, check_same_thread=False, factory=_Con)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=30000")
    if path not in _READY:
        with _READY_LOCK:                                    # first use of a NEW database: the warm-up thread and the first
            if path not in _READY:                           # request must not both add the same columns (valve29 fix)
                con.executescript(_SCHEMA)
                _migrate(con)
                _READY.add(path)
    return con


def backup(keep: int = 7) -> Path | None:
    """Daily copy of valve.db (SQLite online backup, safe while in use) → valve/backups/valve.db.<date>.bak; keeps the
    newest `keep`.  Called from the warm-up at server start; returns the file made today, or None when it exists."""
    src = root() / "valve.db"
    if not src.exists():
        return None
    bdir = root() / "backups"
    bdir.mkdir(parents=True, exist_ok=True)
    dst = bdir / f"valve.db.{dt.date.today().isoformat()}.bak"
    if dst.exists():
        return None
    con = sqlite3.connect(str(src), timeout=30)
    try:
        out = sqlite3.connect(str(dst))
        with out:
            con.backup(out)
        out.close()
    finally:
        con.close()
    for old in sorted(bdir.glob("valve.db.*.bak"))[:-keep]:
        old.unlink(missing_ok=True)
    return dst


_ADDED = {"datasheet": [("sheets", "TEXT"), ("parser_version", "TEXT")],
          "comment": [("page", "INTEGER"), ("bbox", "TEXT"), ("category", "TEXT DEFAULT 'comment'"),
                      ("deleted", "INTEGER DEFAULT 0"), ("kind", "TEXT"), ("points", "TEXT"), ("style", "TEXT"),
                      ("origin", "TEXT")],                   # valve26: 'Rev A' when copied from the previous revision
          "issue_state": [("since", "TEXT"), ("decision", "TEXT"), ("reason_cat", "TEXT"), ("conclusion", "TEXT"),   # valve29
                          ("modified_text", "TEXT"), ("modified_severity", "TEXT"), ("rule_ver", "TEXT"),
                          ("modified_expected", "TEXT")]}    # since = valve26 (carried from)


def _migrate(con):
    """Columns added after a database was first made (older valve.db keeps working)."""
    for table, cols in _ADDED.items():
        have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
        for name, typ in cols:
            if name not in have:
                try:
                    con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {typ}")
                except sqlite3.OperationalError as e:       # another process added it meanwhile
                    if "duplicate column" not in str(e):
                        raise
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

def file_ok(p: Path, sha: str, size: int | None = None) -> bool:
    """The stored original still holds exactly the uploaded bytes (size, then content hash)."""
    try:
        if size is not None and p.stat().st_size != size:
            return False
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest() == sha
    except OSError:
        return False


_GOOD: dict[tuple, tuple[bool, str]] = {}
BAD_SEEN: dict[str, dict] = {}                              # path → diagnosis, for the start-up report and /health


def stored_good(path) -> tuple[bool, str]:
    """valve40 (company PC 2026-11-13: the server restarted in a loop — MuPDF died natively on damaged stored copies during
    warm-up).  Before ANY reader hands a file to MuPDF: it exists, is not empty, has a PDF header, and — for a stored
    original — still holds exactly the uploaded bytes (sha256 of its document row).  Checked once per (path, mtime, size)."""
    p = Path(path)
    try:
        st = p.stat()
    except (OSError, TypeError, ValueError):
        return False, "파일이 없습니다"
    k = (str(p), st.st_mtime_ns, st.st_size)
    if k in _GOOD:
        return _GOOD[k]
    r = (True, "")
    if st.st_size == 0:
        r = (False, "빈 파일입니다")
    else:
        try:
            with open(p, "rb") as f:
                head = f.read(1024)
        except OSError as e:
            head, r = b"", (False, f"읽을 수 없습니다 ({type(e).__name__})")
        if r[0] and b"%PDF" not in head:
            r = (False, "PDF 내용이 아닙니다 — 저장본이 바뀌었습니다 (보안 프로그램 의심)")
        if r[0] and p.parent == root() / "files":
            try:
                c = sqlite3.connect(str(root() / "valve.db"), timeout=30)
                row = c.execute("SELECT sha256 FROM document WHERE path=? AND sha256<>'' LIMIT 1", (str(p),)).fetchone()
                c.close()
            except sqlite3.Error:
                row = None
            if row and not file_ok(p, row[0], None):
                r = (False, "저장본이 올린 파일과 다릅니다 (원본 손상 — 같은 파일 다시 올리기)")
    if not r[0]:
        BAD_SEEN[str(p)] = dict(diagnose(p), why=r[1])
    _GOOD[k] = r
    return r


def stored_ext(filename: str) -> str:
    """valve38: a PDF original is stored as '.bin' — on the company PC the stored '<hash>.pdf' copy no longer opened
    (pymupdf FileDataError) although the same bytes opened at upload: something on that PC changes files named *.pdf
    after they are written (document security / DRM suspected).  The bytes are the same; every reader opens it as PDF
    explicitly (filetype='pdf').  Excel files keep their extension (openpyxl reads by extension)."""
    ext = Path(filename).suffix.lower()[:6] or ".bin"
    return ".bin" if ext == ".pdf" else ext


def diagnose(p, sha: str | None = None, size: int | None = None) -> dict:
    """What the stored copy looks like now — size, whether it still holds the uploaded bytes, its first 32 bytes
    (hex + printable).  Only the head bytes: never the document's content."""
    p = Path(p)
    out = {"file": p.name, "exists": p.exists()}
    if not out["exists"]:
        return out
    try:
        out["size"] = p.stat().st_size
        with open(p, "rb") as f:
            head = f.read(32)
        out["head_hex"] = head.hex(" ")
        out["head_txt"] = "".join(chr(b) if 32 <= b < 127 else "." for b in head)
        out["pdf_header"] = head.startswith(b"%PDF")
        if size is not None:
            out["expected_size"] = size
        if sha:
            out["sha_match"] = file_ok(p, sha)
    except OSError as e:
        out["read_error"] = f"{type(e).__name__}: {e}"
    return out


def save_original(data: bytes, filename: str) -> tuple[str, Path]:
    """Store bytes once under their hash.  An existing file with the same hash is kept — unless it no longer holds those
    bytes (valve34: a damaged or truncated copy was reused for every later upload of the same file, so every re-upload
    failed the same way); then it is written again from the upload."""
    sha = hashlib.sha256(data).hexdigest()
    ext = stored_ext(filename)
    p = root() / "files" / f"{sha[:16]}{ext}"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or not file_ok(p, sha, len(data)):
        tmp = p.with_suffix(p.suffix + ".part")
        tmp.write_bytes(data)
        for k in range(5):                                   # Windows: a viewer / antivirus may hold the old copy for a moment
            try:
                tmp.replace(p)
                break
            except PermissionError:
                if k == 4:
                    raise
                time.sleep(0.5 * (k + 1))
    return sha, p


def repoint_originals(con, sha: str, path) -> int:
    """valve38: every document with these bytes reads the fresh stored copy (a re-upload repairs the older rows too —
    their datasheets, mark-ups and decisions stay as they are)."""
    with _LOCK:
        n = con.execute("UPDATE document SET path=? WHERE sha256=? AND path<>?", (str(path), sha, str(path))).rowcount
        con.commit()
    return n


def migrate_originals(con) -> dict:
    """valve38: stored '<hash>.pdf' copies that still hold the uploaded bytes are copied to '<hash>.bin' and the documents
    re-pointed (the old copy is removed only after the new one is verified).  A copy that no longer holds its bytes is
    left untouched — it is reported, and a re-upload of the same file writes a good one."""
    out = {"moved": 0, "broken": [], "kept": 0}
    rows = con.execute("SELECT DISTINCT sha256, path FROM document WHERE lower(path) LIKE '%.pdf'").fetchall()
    for sha, path in rows:
        p = Path(path)
        if not p.exists() or p.parent != root() / "files":
            out["kept"] += 1
            continue
        if not file_ok(p, sha):
            out["broken"].append(p.name)
            BAD_SEEN[str(p)] = dict(diagnose(p, None, None), why="저장본이 올린 파일과 다릅니다")
            continue
        q = p.with_suffix(".bin")
        try:
            if not (q.exists() and file_ok(q, sha)):
                tmp = q.with_suffix(".bin.part")
                tmp.write_bytes(p.read_bytes())
                tmp.replace(q)
            if not file_ok(q, sha):
                out["broken"].append(q.name)
                continue
            repoint_originals(con, sha, q)
            try:
                p.unlink()
            except OSError:
                pass                                         # held by another program: harmless, nothing reads it any more
            out["moved"] += 1
        except OSError:
            out["kept"] += 1
    return out


# ── datasheets ─────────────────────────────────────────────────────────────────

def _parser_version() -> str:
    from app.valve import extract
    return extract.PARSER_VERSION


def insert_datasheet(con, project_id: int, document_id: int, ds: dict) -> int:
    cur = con.execute(
        "INSERT INTO datasheet(project_id, document_id, tag, tag_key, valve_type, doc_no, rev, rev_date, title, form,"
        " pages, notes, rev_history, created_at, sheets, parser_version) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (project_id, document_id, ds["tag"], ds["tag_key"], ds["valve_type"], ds["doc_no"], ds["rev"], ds.get("date", ""),
         ds.get("title", ""), ds.get("form", ""), J(ds["pages"]), J(ds["notes"]), J(ds.get("rev_history", [])), now(),
         J(ds.get("sheets")), _parser_version()))
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
                " rev_history=?, sheets=?, parser_version=? WHERE id=?",
                (ds["tag"], ds["valve_type"], ds["doc_no"], ds.get("date", ""), ds.get("title", ""), ds.get("form", ""),
                 J(ds["pages"]), J(ds["notes"]), J(ds.get("rev_history", [])), J(ds.get("sheets")), _parser_version(), dsid))
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
