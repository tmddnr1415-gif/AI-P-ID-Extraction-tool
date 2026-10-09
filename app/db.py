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
import threading
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
    engine_json  TEXT NOT NULL DEFAULT '{}',  -- multipliers, legend, glyphs
    error_detail TEXT NOT NULL DEFAULT ''     -- the traceback, for the log and
                                              -- the diagnostic export only
);

-- 한 리비전의 대조 결과.  행마다 상태 하나.
CREATE TABLE IF NOT EXISTS revision_state (
    job_id       TEXT NOT NULL,
    row_key      TEXT NOT NULL,
    stable_id    TEXT NOT NULL DEFAULT '',
    state        TEXT NOT NULL DEFAULT '',   -- BASELINE|UNCHANGED|ADDED|MODIFIED
    excel_no     INTEGER NOT NULL DEFAULT 0, -- 그 행이 처음 받은 산출물 NO
    moved_pt     REAL NOT NULL DEFAULT 0,
    changed_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (job_id, row_key)
);

-- 매칭이 안 된 직전 리비전의 ID.  '삭제' 가 아니라 '삭제 후보' 다: 검출 실패와
-- 실제 삭제를 기계가 가르지 못하므로 사람이 확정해야 굳는다.
CREATE TABLE IF NOT EXISTS deleted_candidate (
    job_id       TEXT NOT NULL,
    stable_id    TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    confirmed    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (job_id, stable_id)
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

-- What a reviewer has decided about one flagged row.  A row can be flagged for
-- more than one reason and each is decided on its own, so the key is (row, code).
-- `OPEN` is not stored: absence is open, which keeps the table the size of the
-- work actually done rather than the size of the work outstanding.
CREATE TABLE IF NOT EXISTS review_state (
    job_id      TEXT NOT NULL,
    row_key     TEXT NOT NULL,
    code        TEXT NOT NULL,
    state       TEXT NOT NULL,          -- CONFIRMED | EDITED | HELD
    note        TEXT NOT NULL DEFAULT '',
    updated_at  REAL NOT NULL,
    PRIMARY KEY (job_id, row_key, code)
);
CREATE INDEX IF NOT EXISTS review_state_job ON review_state(job_id, code);

-- An error report: "this is wrong, and here is why".
--
-- Distinct from `feedback`, which is written by the act of correcting and never
-- read back.  A report is written on purpose, is meant to be looked at again -
-- listed, edited, withdrawn - and is what leaves the machine in the diagnostic
-- export.  So it is its own table with its own lifecycle.
--
-- Two of these columns are typed by a person and no more: `what` (which axis is
-- wrong) and `detail` (why, or what the right value is).  Everything else is
-- captured by the server at the moment the button is pressed, because a report
-- filed without the evidence that was on screen is a report nobody can act on -
-- and asking a reviewer to copy it out by hand is how it stops being filed.
CREATE TABLE IF NOT EXISTS report (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    created_at  REAL NOT NULL,
    updated_at  REAL NOT NULL,
    kind        TEXT NOT NULL,              -- ROW | SYMBOL | MISSED
    what        TEXT NOT NULL,              -- SCOPE | QTY | TYPE | DESCRIPTION | OTHER
    detail      TEXT NOT NULL DEFAULT '',   -- the one line a person writes
    row_key     TEXT NOT NULL DEFAULT '',
    page_no     INTEGER,
    drawing_no  TEXT NOT NULL DEFAULT '',
    rect_json   TEXT NOT NULL DEFAULT '[]',
    capture_json TEXT NOT NULL DEFAULT '{}' -- everything gathered automatically
);
CREATE INDEX IF NOT EXISTS report_job ON report(job_id, id);

-- 지운 기록의 기록 (17회차 [E]).
--
-- 지우는 것은 되돌릴 수 없고, 이 파일에는 팀원 여러 명의 프로젝트가 함께 있다.
-- 그래서 **무엇을 지웠는지는 남긴다** — 행은 사라져도 "누가 언제 무엇을
-- 몇 행 지웠나" 는 남아야 다음 사람이 빈 자리를 설명할 수 있다.
-- 작성자는 13회차와 같은 자기신고이고, 화면이 "자칭" 이라고 적는다.
-- hotfix23 — 사람이 "최종 저장" 을 누른 기록.  편집은 칸마다 곧바로 저장되고 있으므로
-- 이것은 **저장 동작이 아니라 선언**이다: 누가 · 언제 · 그때 몇 칸을 고쳐 둔 상태였는가.
-- 첫 화면이 프로젝트마다 마지막 것을 보인다.
CREATE TABLE IF NOT EXISTS save_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL,
    at          REAL NOT NULL,
    author      TEXT NOT NULL DEFAULT '',
    edits       INTEGER NOT NULL DEFAULT 0,
    added       INTEGER NOT NULL DEFAULT 0,
    removed     INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS deletion_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    at          REAL NOT NULL,
    author      TEXT NOT NULL DEFAULT '',
    job_id      TEXT NOT NULL,
    project     TEXT NOT NULL DEFAULT '',
    revision    TEXT NOT NULL DEFAULT '',
    pdf_name    TEXT NOT NULL DEFAULT '',
    summary_json TEXT NOT NULL DEFAULT '{}'  -- 사라진 것의 수 (행·편집·검토 …)
);
"""

# Columns a reviewer may edit.  Description and Tag No. are in the list because
# they are deliberately left empty by the engine (Phase 2 / not assigned on
# these drawings), so a human filling them in is the expected case.
EDITABLE = ("type", "qty", "system", "valve_type", "vendor_supply", "scope",
            "description", "tag_no", "line_no", "line_size", "description_grade", "remark")


# Columns added after a database already existed in the field.  `CREATE TABLE IF
# NOT EXISTS` leaves an existing table exactly as it is, so these have to be added
# by hand.  Additive only: nothing here drops, renames or retypes a column, so an
# older build reading a newer file still finds everything it knew about.
_ADDED_COLUMNS = (
    ("job", "error_detail", "TEXT NOT NULL DEFAULT ''"),
    # 어느 프로젝트의 어느 리비전인가, 그리고 무엇과 비교했는가.  세 값이 다
    # job 에 붙는 이유는 하나의 분석이 곧 하나의 리비전이기 때문이다.
    ("job", "project", "TEXT NOT NULL DEFAULT ''"),
    ("job", "revision", "TEXT NOT NULL DEFAULT ''"),
    ("job", "compared_with", "TEXT NOT NULL DEFAULT ''"),
    # 38회차 — 프로젝트에 안 묶인 분석의 입찰/실행 선언.  프로젝트가 있으면
    # 그 장부(`project.json`)의 선언이 이기고 이 칸은 비어 있다.
    ("job", "mode", "TEXT NOT NULL DEFAULT ''"),
    # 55회차 — 입력 종류 (PDF | DXF).  DXF 는 zip 하나로 저장되고 `pdf_path` 가
    # 그 zip 을 가리킨다 (이름은 옛 것 그대로 — 열이 바뀌면 옛 DB 가 못 읽는다).
    ("job", "input_kind", "TEXT NOT NULL DEFAULT 'PDF'"),
    ("revision_state", "excel_no", "INTEGER NOT NULL DEFAULT 0"),
    # hotfix38 — 어느 길로 짝지었나(TAG | GEOMETRY)와 추가의 근거 한 줄.  둘 다
    # 화면·Excel 이 그대로 읽는 사실이고 판정은 `revisions.compare` 한 곳이다.
    ("revision_state", "basis", "TEXT NOT NULL DEFAULT ''"),
    ("revision_state", "reason", "TEXT NOT NULL DEFAULT ''"),
    ("revision_state", "sheet_from", "TEXT NOT NULL DEFAULT ''"),   # 도면번호가 바뀐 장의 옛 번호
    ("revision_state", "diffs_json", "TEXT NOT NULL DEFAULT '[]'"),  # hotfix43 — 상태에 안 쓰는 값 차이
    # 몇 장짜리 문서인가, 그중 몇 장을 읽었는가, 얼마나 걸렸는가.  네 값 다
    # 화면에 그대로 나가므로 추정하지 않는다: `page_count` 는 업로드 직후 PDF
    # 에서 세고 (못 세면 0 이고, 0 은 "모른다"이지 "0쪽"이 아니다),
    # `sheets_total` 은 파이프라인이 분석 대상을 확정한 순간 한 번 적힌 뒤
    # 끝날 때까지 바뀌지 않는다.
    ("job", "page_count", "INTEGER NOT NULL DEFAULT 0"),
    ("job", "sheets_done", "INTEGER NOT NULL DEFAULT 0"),
    ("job", "sheets_total", "INTEGER NOT NULL DEFAULT 0"),
    ("job", "started_at", "REAL NOT NULL DEFAULT 0"),
    ("job", "finished_at", "REAL NOT NULL DEFAULT 0"),
    # 58쪽 중 52장을 걷는다면 나머지 6장이 어디로 갔는지가 여기 있다.
    # 쪽 번호까지 들고 있으므로 화면에서 묶어 숨길 필요가 없다.
    ("job", "sheet_plan", "TEXT NOT NULL DEFAULT ''"),
    # 실패했을 때 **어느 단계에서** 멈췄는가 (21회차).
    #
    # 새로 만드는 값이 아니다: 파이프라인은 단계마다 `set_progress` 로 그 이름을
    # `message` 에 적고 있었고, 실패 처리가 같은 칸을 사유로 덮어써서 그 사실이
    # 사라지고 있었다.  덮기 **전에** 옮겨 적기만 한다.
    #
    # 담는 것은 파이프라인이 쓴 **원문 그대로**(`measuring sheet 37 of 60`)이고
    # 화면 문장이 아니다 - 15회차가 `compare_note` 로 겪은 것과 같은 이유다:
    # 문장을 저장하면 문구를 고쳐도 옛 분석이 옛 문장을 계속 말한다.  한국어로
    # 옮기는 것은 화면의 `stageWords()` 가 이미 하고 있고, 모르는 값은 그대로
    # 쓴다.
    ("job", "stopped_stage", "TEXT NOT NULL DEFAULT ''"),
    # 도면이 스스로 말하는 개정 (13회차).  `extract_titleblocks` 는 처음부터
    # 이 값을 읽고 있었는데(58장 전부 신뢰도 HIGH) 저장하는 곳이 없어 분석이
    # 끝나면 다시 볼 수 없었다.  판정에는 쓰이지 않는다 - 지문에도 들어가지
    # 않고, 화면이 "이 PDF 가 개정본인가"를 말할 때만 읽는다.
    ("pid_page", "rev", "TEXT NOT NULL DEFAULT ''"),
    # 44회차 — 사람이 "오검출" 로 표시한 검출 행의 사유.  `removed` 는 "Excel
    # 에서 뺀다" 는 뜻 하나만 갖고, 왜 뺐는지(㉢ 오검출 · ㉣ 값 틀림 · 미지정
    # 심볼)와 누가·언제는 여기 산다.  행은 지워지지 않는다 (`remove_row`).
    ("item", "reject_json", "TEXT NOT NULL DEFAULT '{}'"),
    ("pid_page", "rev_method", "TEXT NOT NULL DEFAULT ''"),
    ("pid_page", "rev_confidence", "TEXT NOT NULL DEFAULT ''"),
    ("pid_page", "rev_date", "TEXT NOT NULL DEFAULT ''"),
    # 문서 한 장으로 접은 값.  이 문서는 장마다 Rev 가 다르므로(A 15 · A1 1 ·
    # B 19 · C 16 · D 7) 접는 규칙이 필요하고, 그 규칙은 도면에서 유도되지
    # 않는다 - 사용자가 "가장 앞서간 장이 문서 Rev" 로 확정했다(13회차).
    # 접은 값만 두지 않고 장별 값도 위에 그대로 남긴다.
    ("job", "doc_rev", "TEXT NOT NULL DEFAULT ''"),
    # 누가 고쳤나.  인증이 아니라 자기신고다 - 이 앱에는 로그인도 사용자
    # 테이블도 없고, 없는 것을 지어내지 않는다.  화면이 "자칭"이라고 적는다.
    ("feedback", "author", "TEXT NOT NULL DEFAULT ''"),
    # hotfix62 — 첫 화면 카드가 말하는 도면 사실 (`app/pdf_facts.py`): PDF 의 프로젝트 제목 ·
    # 장마다 현재 개정의 날짜 · 이력 표가 말하는 개정 순서.  판정에 안 쓰이고 지문 밖이다.
    # 빈 문자열은 "아직 안 읽었다" — 시작 때 한 번 채운다 (예전 분석도 재분석 없이).
    ("job", "facts_json", "TEXT NOT NULL DEFAULT ''"),
)


class DatabaseCorrupt(RuntimeError):
    """DB 파일이 깨져 열 수 없다.  문장은 `_corrupt_message` 가 만든다 (hotfix74)."""


BACKUP_DIR = "backups"
BACKUP_KEEP = 3


def backups(path: Path) -> list:
    """`backup_daily` 가 떠 둔 판 — 새것부터."""
    d = Path(path).parent / BACKUP_DIR
    return sorted(d.glob(Path(path).name + ".*.bak"), reverse=True) if d.is_dir() else []


def _corrupt_message(path: Path, exc) -> str:
    have = backups(path)
    hint = (f"가장 최근 백업은 {have[0]} 입니다 — 서버를 끄고 깨진 {Path(path).name} 를 다른 이름으로 옮긴 뒤 "
            f"그 백업을 {Path(path).name} 로 복사하고 다시 켜세요 (그 뒤의 분석·편집은 다시 해야 합니다)."
            if have else
            f"자동 백업이 아직 없습니다 — 서버를 끄고 깨진 {Path(path).name} 를 다른 이름으로 옮기면 빈 DB 로 "
            f"켜집니다 (프로젝트 장부는 projects 폴더에 그대로 남습니다).")
    return (f"분석 기록 DB 가 깨져 열 수 없습니다 ({path}: {exc}).  지우거나 덮지 않고 멈춥니다.  " + hint)


def backup_daily(path: Path, keep: int = BACKUP_KEEP):
    """하루 한 번 DB 를 `backups/` 에 떠 둔다 — sqlite backup API 라 쓰는 중에도 일관된 판이다 (hotfix74).

    운영 서버는 이 DB 하나에 모든 분석 기록이 있는데 백업이 없었다.  디스크 오류·정전으로 깨지면 되살릴
    판이 없었다.  읽기 전용 연결을 따로 열어 뜨므로 요청을 막지 않는다.  최근 `keep` 판만 남긴다.
    """
    path = Path(path)
    if not path.exists():
        return None
    d = path.parent / BACKUP_DIR
    d.mkdir(parents=True, exist_ok=True)
    dest = d / f"{path.name}.{time.strftime('%Y-%m-%d')}.bak"
    if dest.exists():
        return dest
    tmp = dest.with_name(dest.name + ".tmp")
    # URI 는 `as_uri()` 로 — Windows 경로(`C:\…` · 한글 · 공백)를 손으로 붙이면 SQLite 가 잘못 읽는다.
    src = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30.0)
    try:
        out = sqlite3.connect(tmp)
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    import os as _os2
    _os2.replace(tmp, dest)
    for old in backups(path)[keep:]:
        try:
            old.unlink()
        except OSError:
            pass
    return dest


class _SerialConnection(sqlite3.Connection):
    """한 연결을 여러 스레드가 함께 쓴다 — 호출 하나하나를 잠금으로 줄 세운다 (hotfix74).

    `main.CON` 하나를 요청 스레드들 · 분석 작업 스레드 · 도면 사실 채우기 스레드가 같이 쓴다
    (`check_same_thread=False`).  sqlite3 모듈은 쓰기 앞에 "트랜잭션이 열려 있나" 를 보고 BEGIN 을
    거는데, 그 사이에 다른 스레드가 끼면 `cannot start a transaction within a transaction` ·
    `cannot commit - no transaction is active` 로 실패한다.  실측(6스레드 × 2000 쓰기): 잠금 없이
    **362건 실패** ↔ 잠금 **0건**.  두 사람이 동시에 칸을 고치면 500 이 날 수 있었다 — 빠른 시험이
    세 번에 한 번 꼴로 이 경합에 걸려 드러났다 (`test_hotfix68_dualpane`).
    """
    _lock = threading.RLock()

    def execute(self, *a, **k):
        with self._lock:
            return super().execute(*a, **k)

    def executemany(self, *a, **k):
        with self._lock:
            return super().executemany(*a, **k)

    def executescript(self, *a, **k):
        with self._lock:
            return super().executescript(*a, **k)

    def commit(self):
        with self._lock:
            return super().commit()

    def rollback(self):
        with self._lock:
            return super().rollback()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    # hotfix74 — 다른 프로세스(두 번 켠 서버 · DB 를 연 다른 도구)가 쓰기 잠금을 쥐면 기본 5초 뒤
    # `database is locked` 로 실패했다 (돌발상황 시뮬레이션 S5).  30초까지 기다리고, 그래도 안 되면
    # `main` 이 503 과 사람 말로 답한다.
    con = sqlite3.connect(path, check_same_thread=False, timeout=30.0, factory=_SerialConnection)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite3.DatabaseError as exc:
        # hotfix74 — 돌발상황 시뮬레이션(`spike/state_chaos.py` K3): DB 머리가 깨지면 영문
        # `file is not a database` 로만 멈춰 서비스 창이 10초마다 같은 줄을 되풀이했다.
        # **지우지도 덮지도 않는다** — 무엇을 하면 되는지와 가장 최근 백업을 말하고 멈춘다.
        con.close()
        raise DatabaseCorrupt(_corrupt_message(path, exc)) from exc
    con.executescript(SCHEMA)
    for table, column, decl in _ADDED_COLUMNS:
        have = {r["name"] for r in con.execute(f"PRAGMA table_info({table})")}
        if column not in have:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    con.commit()
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
                 status: str = "running", error_detail: str = None,
                 sheets: tuple = None):
    """`message` is what a person reads.  `error_detail` is the raw text.

    They are separate columns because they have different audiences: the message
    goes on screen, the detail goes to the log and the diagnostic export.  Putting
    a traceback in `message` is what the failure screen used to show, and it told
    the reviewer nothing they could act on.

    `sheets` is `(done, total)` for the sheet loop, stored rather than only
    emitted because a listener that connects late - or a failure screen asked how
    far it got - reads this row, not the event that has already gone past.
    """
    con.execute("UPDATE job SET progress=?, message=?, status=? WHERE id=?",
                (progress, message, status, job_id))
    if sheets is not None:
        con.execute("UPDATE job SET sheets_done=?, sheets_total=? WHERE id=?",
                    (int(sheets[0]), int(sheets[1]), job_id))
    if error_detail is not None:
        con.execute("UPDATE job SET error_detail=? WHERE id=?",
                    (error_detail, job_id))
    con.commit()


def set_stopped_stage(con, job_id: str, stage: str) -> None:
    """실패했을 때 마지막으로 돌던 단계 이름을 적는다 (21회차).

    `set_progress` 와 따로 있는 이유는 **시점**이다: 사유를 적는 순간 `message`
    는 이미 덮여 있으므로, 부르는 쪽이 덮기 전에 읽어 두었다가 여기로 넘긴다.
    값은 파이프라인이 쓴 원문 그대로이고 화면 문장이 아니다.
    """
    con.execute("UPDATE job SET stopped_stage=? WHERE id=?", (str(stage or ""), job_id))
    con.commit()


def set_sheet_plan(con, job_id: str, plan: dict) -> None:
    """어느 쪽을 걷고 어느 쪽을 왜 안 걷는지.  한 번 적히고 바뀌지 않는다."""
    con.execute("UPDATE job SET sheet_plan=? WHERE id=?",
                (json.dumps(plan, ensure_ascii=False, sort_keys=True), job_id))
    con.commit()


def set_page_count(con, job_id: str, pages: int) -> None:
    """How many pages the uploaded PDF has, counted from the file itself."""
    con.execute("UPDATE job SET page_count=? WHERE id=?", (int(pages), job_id))
    con.commit()


def mark_started(con, job_id: str) -> None:
    con.execute("UPDATE job SET started_at=?, finished_at=0, sheets_done=0"
                " WHERE id=?", (time.time(), job_id))
    con.commit()


def mark_finished(con, job_id: str) -> None:
    con.execute("UPDATE job SET finished_at=? WHERE id=?", (time.time(), job_id))
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
    # 장별 개정은 파이프라인이 이미 읽어 `titleblocks` 로 넘겨준다 (13회차).
    # 여기서 하는 일은 그것을 쪽 행에 옮겨 적는 것뿐이고, 값을 만들거나 고치지
    # 않는다 - 읽지 못한 장은 빈 문자열로 남고 빈 문자열은 "모른다"는 뜻이다.
    tb = {t["page_no"]: t for t in (result.get("titleblocks") or [])}
    for p in result["pages"]:
        t = tb.get(p["page_no"], {})
        con.execute(
            "INSERT INTO pid_page (job_id,page_no,drawing_no,title,page_kind,"
            "in_scope,scope_reason,width,height,layers_json,"
            "rev,rev_method,rev_confidence,rev_date)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, p["page_no"], p["drawing_no"], p["title"], p["page_kind"],
             int(p["in_scope"]), p["scope_reason"], p["width"], p["height"],
             json.dumps(result["layers"].get(str(p["page_no"]), {}), sort_keys=True),
             str(t.get("rev") or ""), str(t.get("rev_method") or ""),
             str(t.get("rev_confidence") or ""), str(t.get("rev_date") or "")))

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
                              "description_scope", "description_build",
                              "description_grades",
                              # 15회차 - 이 분석이 범례를 재서 왔는지 물려받아
                              # 왔는지, 그리고 프로필과 어디가 다른지.  화면이
                              # 이것을 읽어 "어느 규칙으로 나온 결과인가" 를
                              # 말한다.  지문에는 들어가지 않는다.
                              "legend_profile",
                              # 18회차 [D] - 범례에 없어 판정하지 못한 심볼.
                              # 등록 화면이 이것을 읽는다.  판정이 아니라
                              # "판정하지 못했다" 는 기록이므로 지문에는
                              # 들어가지 않는다.
                              "unjudged_symbols",
                              # 29회차 [D] 의 증거 등급이 여기 빠져 있었다 — 38회차 [B] 의
                              # 모드 띠가 그것을 읽어야 해서 드러났다.  선언 · 실측 ·
                              # 불일치 사실이 이제 저장된다 (지문 밖).
                              "evidence_tier",
                              # 38회차 [D] — Typical 참조 사실(장 → 표식·상세·참조 수)과 집계.
                              "typical", "typical_stats",
                              # 53회차 [E] — 그 장 NOTES 에서 읽은 "이 도면은 유닛
                              # 몇 개에 같이 쓰이는가" (27회차가 계산해 놓고
                              # **저장하지 않아** 화면이 못 읽었다 — 38회차
                              # `evidence_tier` 와 같은 결함).  8차 피드백 s3 이
                              # *"식별 값도 표기한다 · 해석된 내용을 표기한다"* 다.
                              # 지문 밖이다 (`multipliers` 에 넣으면 지문이 움직인다).
                              # 56회차 [G1] — 어느 프로필로 돌았고 무엇을 남의
                              # 설정에서 빌렸나.  화면 띠가 읽는다 (지문 밖).
                              "profile", "borrowed",
                              # hotfix31 — 같은 태그의 표시기(PI)를 전송기(PIT)로
                              # 접은 내역 · 게이지 수 (지문 밖).
                              "readouts",
                              # hotfix33 — 45회차 사람 지정 도면번호가 이번 분석에
                              # 실제로 쓰였는지 (`table`·`who`).  화면 판이 "이번 분석은
                              # 사람이 적은 번호로 읽었다" 를 이것으로 가른다 (지문 밖).
                              "user_sheet_numbers",
                              # hotfix39 — 태그 문법 · 교차 검증 · 태그가 증거인 행 (지문 밖)
                              "tag_grammar",
                              "unit_notes")},
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
        # 44회차 — 오검출 표시.  옛 DB(열이 없던 파일)는 빈 dict 다.
        "reject": (json.loads(r["reject_json"] or "{}")
                   if "reject_json" in r.keys() else {}),
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


def merged_rows_on_page(con, job_id: str, page_no: int) -> list:
    """`merged_rows` 중 그 장의 행만 — 같은 행 · 같은 순서 (hotfix75 · 행 추가가 그 장만 본다)."""
    return [_merged(r) for r in con.execute(
        "SELECT * FROM item WHERE job_id=? AND page_no=? ORDER BY page_no, key", (job_id, page_no)).fetchall()]


def engine_tag_numbers(con, job_id: str) -> list:
    """엔진이 붙인 태그(`ai.tag_no`) 만 — 마크업 제안이 이 문서의 태그 체계를 볼 때 (hotfix75 · 분석 전체를 파싱하지 않는다).
    `merged_rows(...)[i]["ai"]["tag_no"]` 와 같은 값 · 같은 순서."""
    return [raw for (raw,) in con.execute(
        "SELECT json_extract(ai_json, '$.tag_no') FROM item WHERE job_id=? ORDER BY page_no, key", (job_id,))]


def engine_parts(con, job_id: str, paths: dict) -> dict:
    """`engine_json` 의 몇 칸만 (`{이름: JSON 경로}`).  hotfix75 — 그 칸 하나를 위해 분석 기록 전체를 파이썬으로
    파싱하지 않는다 (SQLite 의 json_extract 가 C 에서 한 번 읽는다).  없는 분석 · 없는 칸 · 깨진 기록은 None."""
    cols = ", ".join(f"json_extract(engine_json, ?) AS c{i}" for i in range(len(paths)))
    try:
        row = con.execute(f"SELECT {cols} FROM job WHERE id=?", (*paths.values(), job_id)).fetchone()
    except sqlite3.Error:
        row = None
    out = {}
    for i, name in enumerate(paths):
        v = row[i] if row is not None else None
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                pass
        out[name] = v
    return out


def merged_rows_by_keys(con, job_id: str, keys, tab: str = None) -> list:
    """`merged_rows` 와 같은 행 · 같은 순서 — 그 열쇠의 행만 DB 에서 읽는다 (hotfix74).

    부하 시뮬레이션(`spike/soak.py` — 6명이 칸을 고치며 근거를 연다): 행 하나의 근거(`/rows?keys=`)가
    **p50 4초**였다.  편집 한 칸마다 메모가 풀리고, 행 하나를 위해 분석 전체(QFE 2천 행 · evidence 11MB)를
    다시 파싱했기 때문이다.  행 몇 개면 그 몇 개만 읽는다."""
    keys = [k for k in dict.fromkeys(keys or []) if k]
    out = []
    for i in range(0, len(keys), 500):
        part = keys[i:i + 500]
        sql = f"SELECT * FROM item WHERE job_id=? AND key IN ({','.join('?' * len(part))})"
        args = [job_id, *part]
        if tab and tab != "ALL":
            if tab == "REVIEW":
                sql += " AND (needs_review<>'' OR deleted=1)"
            else:
                sql += " AND tab=?"
                args.append(tab)
        out += con.execute(sql, args).fetchall()
    out.sort(key=lambda r: (r["page_no"], r["key"]))
    return [_merged(r) for r in out]


# hotfix45 — 같은 분석의 행을 **한 요청 안에서 다섯 번** 파싱하고 있었다.  결과 화면을
# 열 때 `/rows` · `/review` · `/markup` · `/drawings` · `/multipliers` · `/axis_overrides`
# 가 저마다 `merged_rows` 를 불러 evidence 10.9MB(QFE 2,041행)를 다시 읽는다 — 서버에서
# 각 0.3~0.4초, 직렬로 1.75초.  읽기 전용인 곳은 마지막으로 파싱한 목록을 다시 쓴다.
#
# 묵은 값을 주지 않는 장치는 **도장**이다: 이 연결의 `total_changes`(이 연결이 바꾼 행 수)
# 와 `PRAGMA data_version`(다른 연결이 커밋하면 바뀐다) — 둘 중 하나라도 움직이면 다시
# 파싱한다.  편집 한 칸(UPDATE 한 행)도 `total_changes` 를 올리므로 편집 직후의 읽기는
# 언제나 새 값이다.  받은 목록은 **고치지 않는다** — 고쳐야 하는 곳(`/rows` 가 열을 더한다)
# 은 얕은 복사를 떠서 쓴다 (시험이 소스로 못박는다).  둘까지만 든다 (분석 하나 약 60MB).
import collections as _collections
import os as _os
_ROWS_MEMO: "_collections.OrderedDict" = _collections.OrderedDict()
_ROWS_MEMO_MAX = 2


def _db_stamp(con) -> tuple:
    path = con.execute("PRAGMA database_list").fetchone()[2]
    dv = con.execute("PRAGMA data_version").fetchone()[0]
    return path, (con.total_changes, dv)


# hotfix69 — 결과를 열면 화면이 읽기 요청 열 개를 **한꺼번에** 보내고 그중 넷(`/rows` · 검토 · 마크업 · FROM/TO
# 확정)이 이 메모를 읽는다.  메모가 비어 있으면 넷이 **같은 파싱(0.4초)을 동시에** 하며 인터프리터 잠금을 다퉈
# 결과 열기가 4초가 됐다 (QFE 실측 — 따로 부르면 각 0.01~0.03초).  잠금 하나로 한 요청만 파싱하고 나머지는 그
# 결과를 받는다.
import threading as _threading
_ROWS_MEMO_LOCK = _threading.Lock()


def merged_rows_cached(con, job_id: str, tab: str = None) -> list:
    """`merged_rows` 와 같은 목록 — 읽기 전용 호출자를 위한 것.  **받은 목록을 고치지 마라.**"""
    tab = tab or "ALL"
    with _ROWS_MEMO_LOCK:
        path, stamp = _db_stamp(con)
        key = (id(con), path, job_id, tab)
        hit = _ROWS_MEMO.get(key)
        if hit is not None and hit[0] == stamp:
            _ROWS_MEMO.move_to_end(key)
            return hit[1]
        if _os.environ.get("PID_DEBUG_MEMO"):
            print(f"[memo] rebuild {job_id} {tab} stamp={stamp} had={hit[0] if hit else None}", flush=True)
        rows = merged_rows(con, job_id, tab)
        _ROWS_MEMO[key] = (stamp, rows)
        _ROWS_MEMO.move_to_end(key)
        while len(_ROWS_MEMO) > _ROWS_MEMO_MAX:
            _ROWS_MEMO.popitem(last=False)
        return rows


class memo_follow:
    """hotfix75 — 행 몇 개를 고치는 쓰기 뒤에 **메모를 그 행만 고쳐** 둔다 (다음 읽기가 분석 전체를 다시 파싱하지 않게).

    편집·지우기·되살리기·행 추가 한 번마다 메모가 풀려, 그 뒤 화면이 읽는 검토 · 마크업 · 그림 목록 요청이
    분석 전체(QFE 2천 행 · 근거 11MB)를 다시 파싱했다 — 지우기 한 번이 1초 남짓 멈춘 몫의 대부분이다.

        with db.memo_follow(con, job_id) as keys:
            ...쓰기...
            keys.append(key)          # 이 블록이 바꾼(더한 · 지운) 행

    안전 규칙: 블록 동안 이 연결의 잠금을 쥔다 (다른 스레드의 쓰기가 끼지 않는다) · 다른 연결이 그 사이 썼으면
    (`data_version`) 고치지 않는다 · 메모가 블록 **직전** 상태였을 때만 고친다 · 고친 메모에는 블록 **직후** 도장을
    찍는다 — 그 뒤 누가 무엇을 쓰든 도장이 달라져 예전처럼 전부 다시 읽는다.  예외가 나면 아무것도 고치지 않는다
    (메모는 도장이 안 맞아 저절로 버려진다).  잠금이 없는 연결(시험의 맨 sqlite3)이면 하는 일이 없다."""

    def __init__(self, con, job_id: str):
        self.con, self.job_id, self.keys = con, job_id, []
        self.lock = getattr(con, "_lock", None)

    _depth = _threading.local()   # 겹친 블록(묶음 안의 이력 쓰기)은 바깥 블록이 끝에 한 번 고친다

    def __enter__(self):
        if self.lock is not None:
            self.lock.acquire()
            memo_follow._depth.n = getattr(memo_follow._depth, "n", 0) + 1
            try:
                self.pre = _db_stamp(self.con)
            except Exception:
                self.lock.release(); raise
        return self.keys

    def __exit__(self, et, ev, tb):
        if self.lock is None:
            return False
        memo_follow._depth.n -= 1
        fresh = None
        try:
            # 바깥 블록이 아직 연결 잠금을 쥐고 있으면 여기서 메모 잠금을 잡지 않는다 (잠금 순서: 메모 → 연결 이
            # `merged_rows_cached` 의 순서다 — 거꾸로 잡으면 서로 기다린다).  바깥 블록이 끝에 한 번 고친다.
            if et is None and memo_follow._depth.n == 0:            # 바꾼 행이 없으면(이력 표만 썼다) 도장만 옮긴다
                post = _db_stamp(self.con)
                if post[0] == self.pre[0] and post[1][1] == self.pre[1][1]:   # 같은 파일 · 다른 연결이 안 썼다
                    fresh = (post, merged_rows_by_keys(self.con, self.job_id, self.keys) if self.keys else [])
        except Exception:
            fresh = None
        finally:
            self.lock.release()
        if fresh is not None:
            _patch_memo(self.con, self.job_id, self.pre, fresh[0], set(self.keys), fresh[1])
        return False


def _in_tab(r: dict, tab: str) -> bool:
    if tab == "ALL":
        return True
    if tab == "REVIEW":
        return bool(r["needs_review"]) or bool(r["deleted"])
    return r["tab"] == tab


def _patch_memo(con, job_id, pre, post, keys: set, fresh: list) -> None:
    by = {r["key"]: r for r in fresh}
    with _ROWS_MEMO_LOCK:
        for mk, (stamp, rows) in list(_ROWS_MEMO.items()):
            if mk[0] != id(con) or mk[1] != pre[0] or mk[2] != job_id or stamp != pre[1]:
                continue
            tab = mk[3]
            out = [by[r["key"]] if r["key"] in by else r for r in rows if r["key"] not in keys or r["key"] in by]
            have = {r["key"] for r in out}
            out = [r for r in out if r["key"] not in by or _in_tab(r, tab)]
            for r in fresh:                                    # 새 행 · 이제 이 탭에 드는 행 — 같은 자리 (page_no, key)
                if r["key"] in have or not _in_tab(r, tab):
                    continue
                at = next((i for i, x in enumerate(out) if (x["page_no"], x["key"]) > (r["page_no"], r["key"])), len(out))
                out.insert(at, r)
            _ROWS_MEMO[mk] = (post[1], out)


def add_row(con, job_id: str, page_no: int, tab: str, origin: str = "",
            drawing_no: str = "", values: dict = None, source_key: str = None,
            rect=None, evidence: dict = None, needs_review: str = None) -> str:
    """A row a reviewer created, by hand or by copying one.

    It has no `ai_values` - the engine never proposed it - so every value in it
    is a user value, and a re-analysis leaves it alone for the same reason it
    leaves an edit alone.  Reviewer-created rows are marked so a later reader can
    tell them from detections; nothing in the grid hides the difference.
    """
    import uuid
    key = "u" + uuid.uuid4().hex[:15]
    values = dict(values or {})
    # 44회차 — 마크업 행은 도면 위 사각형을 갖는다 (표시 좌표 · pt).  옛 `＋행`
    # 경로는 rect 없이 오고 그때는 예전처럼 `[]` 다.  근거(`evidence`)에는
    # 제안값과 출처(`scope_source` · `qty_source`) · 작성자가 실린다 — 그 칸은
    # 지문·축이 읽지 않는 자리다.  `needs_review` 를 넘기면 그 문장을 쓰고,
    # 안 넘기면 예전 문장 그대로다 (마크업은 사람이 이미 본 행이라 빈 문자열).
    ev = {"added_by": "reviewer"}
    if source_key:
        ev["copied_from"] = source_key
    ev.update(evidence or {})
    con.execute(
        "INSERT INTO item (job_id,key,tab,page_no,drawing_no,origin,rect_json,"
        "ai_json,user_json,evidence_json,needs_review,annotation,conflict_json,"
        "deleted,added,removed) VALUES (?,?,?,?,?,?,?,?,?,?,?,'','{}',0,1,0)",
        (job_id, key, tab, page_no, drawing_no, origin,
         json.dumps([round(float(v), 1) for v in (rect or [])]),
         json.dumps({k: None for k in EDITABLE}, sort_keys=True),
         json.dumps(values, sort_keys=True),
         json.dumps(ev, sort_keys=True, default=str),
         ("reviewer-added row: no detection stands behind it"
          if needs_review is None else needs_review)))
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


def remove_row(con, job_id: str, key: str, reject: dict = None,
               exclude: bool = True) -> dict:
    """Strike a row out.  Reviewer-created rows go for good; detections do not.

    A detection is never really deleted, because the next analysis would just
    bring it back and the reviewer's decision would be lost.  It is marked
    `removed`, which keeps it visible and out of the export.

    44회차 — `reject` 는 사람이 적은 사유(㉢ 오검출 · ㉣ 값 틀림 · 미지정
    심볼 · 기타)와 누가·언제다.  `exclude=False` 면 **표시만** 한다 — 행은
    Excel 에 그대로 나가고 `reject` 만 남는다 (요구: "Excel 제외 선택").
    """
    row = con.execute("SELECT added FROM item WHERE job_id=? AND key=?",
                      (job_id, key)).fetchone()
    if row is None:
        raise KeyError(key)
    if row["added"]:
        con.execute("DELETE FROM item WHERE job_id=? AND key=?", (job_id, key))
        con.commit()
        return {"key": key, "dropped": True}
    con.execute("UPDATE item SET removed=?, reject_json=? WHERE job_id=? AND key=?",
                (1 if exclude else 0,
                 json.dumps(reject or {}, ensure_ascii=False, sort_keys=True,
                            default=str), job_id, key))
    con.commit()
    return {"key": key, "removed": bool(exclude), "flagged": bool(reject)}


def restore_row(con, job_id: str, key: str) -> None:
    """되돌린다 — `removed` 와 오검출 표시를 함께 지운다."""
    con.execute("UPDATE item SET removed=0, reject_json='{}' WHERE job_id=? AND key=?",
                (job_id, key))
    con.commit()


def set_row_revision_state(con, job_id: str, key: str, stable_id: str,
                           state: str = "", excel_no: int = 0) -> None:
    """한 행의 안정 ID 를 적는다 (44회차 — 마크업 행).

    `store_revision_result` 는 분석 직후 **전부 갈아 끼우는** 함수라 뒤에 생긴
    행에는 쓸 수 없다.  여기는 한 행만 넣고 다른 행은 건드리지 않는다.
    """
    con.execute(
        "INSERT INTO revision_state (job_id,row_key,stable_id,state,excel_no,"
        "moved_pt,changed_json) VALUES (?,?,?,?,?,0,'[]')"
        " ON CONFLICT(job_id,row_key) DO UPDATE SET stable_id=excluded.stable_id,"
        " state=excluded.state, excel_no=excluded.excel_no",
        (job_id, key, stable_id or "", state or "", int(excel_no or 0)))
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


REVIEW_STATES = ("CONFIRMED", "EDITED", "HELD")


def set_review_state(con, job_id: str, row_key: str, code: str, state: str,
                     note: str = "") -> None:
    """Record one decision.  An empty state clears it back to open."""
    if not state:
        con.execute("DELETE FROM review_state WHERE job_id=? AND row_key=? AND code=?",
                    (job_id, row_key, code))
    else:
        if state not in REVIEW_STATES:
            raise ValueError(f"unknown review state {state!r}")
        con.execute(
            "INSERT INTO review_state (job_id, row_key, code, state, note, updated_at)"
            " VALUES (?,?,?,?,?,?)"
            " ON CONFLICT(job_id, row_key, code) DO UPDATE SET"
            " state=excluded.state, note=excluded.note, updated_at=excluded.updated_at",
            (job_id, row_key, code, state, note, time.time()))
    con.commit()


def review_states(con, job_id: str) -> dict:
    """`{row_key: {code: {"state", "note"}}}` for one job."""
    out: dict = {}
    for r in con.execute(
            "SELECT row_key, code, state, note FROM review_state WHERE job_id=?",
            (job_id,)):
        out.setdefault(r["row_key"], {})[r["code"]] = {
            "state": r["state"], "note": r["note"]}
    return out


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
                    geometry: dict = None, pattern_args: dict = None,
                    author: str = "") -> int:
    args = dict(pattern_args or {})
    # hotfix75 — 이력 표만 쓰고 행(item)은 안 건드린다 → 행 메모를 버리지 않고 도장만 옮긴다 (`memo_follow`).
    with memo_follow(con, job_id):
        return _insert_feedback(con, job_id, kind, row_key, page_no, drawing_no, rect, field, ai_value,
                                user_value, reason, args, basis, geometry, author)


def _insert_feedback(con, job_id, kind, row_key, page_no, drawing_no, rect, field, ai_value,
                     user_value, reason, args, basis, geometry, author) -> int:
    cur = con.execute(
        "INSERT INTO feedback (job_id, created_at, kind, row_key, page_no,"
        " drawing_no, rect_json, field, ai_value, user_value, reason, pattern,"
        " basis_json, geometry_json, author)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (job_id, time.time(), kind, row_key, page_no, drawing_no,
         json.dumps(list(rect or []), default=str), field,
         "" if ai_value is None else str(ai_value),
         "" if user_value is None else str(user_value),
         reason, _pattern(kind, **args),
         json.dumps(basis or {}, default=str, sort_keys=True),
         json.dumps(geometry or {}, default=str, sort_keys=True),
         " ".join(str(author or "").split())[:60]))
    con.commit()
    return cur.lastrowid


def last_authors(con, job_id: str, row_key: str) -> dict:
    """그 행의 각 칸을 마지막으로 고친 사람.  승계할 때 이름을 잇기 위한 것이다."""
    out = {}
    for r in con.execute(
            "SELECT field, author, created_at FROM feedback WHERE job_id=?"
            " AND row_key=? AND kind='EDITED' ORDER BY id", (job_id, row_key)):
        out[r["field"]] = {"author": r["author"], "at": r["created_at"]}
    return out


def row_edit_history(con, job_id: str, row_key: str, limit: int = 40) -> list:
    """한 행의 편집 이력 — 누가 · 언제 · 어느 칸 · 무엇에서 무엇으로.

    근거 스냅숏(`basis_json`)은 빼고 돌려준다: 화면이 묻는 것은 "누가 고쳤나"
    이고, 근거는 이미 근거 패널이 따로 보이고 있다.
    """
    return [{"at": r["created_at"], "author": r["author"], "field": r["field"],
             "from": r["ai_value"], "to": r["user_value"], "reason": r["reason"]}
            for r in con.execute(
                "SELECT created_at, author, field, ai_value, user_value, reason"
                " FROM feedback WHERE job_id=? AND row_key=? AND kind='EDITED'"
                " ORDER BY id DESC LIMIT ?", (job_id, row_key, limit))]


def last_editors(con, job_id: str) -> dict:
    """hotfix66 — 행·칸마다 **마지막으로 고친 사람과 때** ({row_key: {field: {author, at}}}).

    화면이 고친 칸(✎)과 도면 라벨에 누가 고쳤는지 붙이는 데 쓴다.  새로 적는 것은 없다 —
    `feedback` 의 EDITED 기록(13회차부터 작성자 칸이 있다)을 읽기만 한다.  한 번의 질의로
    읽는다 (행마다 묻지 않는다)."""
    out: dict = {}
    for key, field, author, at in con.execute(
            "SELECT row_key, field, author, created_at FROM feedback"
            " WHERE job_id=? AND kind='EDITED' AND row_key<>'' ORDER BY id", (job_id,)):
        out.setdefault(key, {})[field] = {"author": author or "", "at": at}
    return out


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
# Error reports
# --------------------------------------------------------------------------

REPORT_WHAT = ("SCOPE", "QTY", "TYPE", "DESCRIPTION", "OTHER")
REPORT_KINDS = ("ROW", "SYMBOL", "MISSED")


def add_report(con, job_id: str, kind: str, what: str, detail: str, *,
               row_key: str = "", page_no: int = None, drawing_no: str = "",
               rect=None, capture: dict = None) -> int:
    """File one report.  Rejects an unknown axis rather than storing a typo."""
    if kind not in REPORT_KINDS:
        raise ValueError(f"unknown report kind '{kind}'")
    if what not in REPORT_WHAT:
        raise ValueError(f"unknown report subject '{what}'")
    now = time.time()
    cur = con.execute(
        "INSERT INTO report (job_id, created_at, updated_at, kind, what, detail,"
        " row_key, page_no, drawing_no, rect_json, capture_json)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (job_id, now, now, kind, what, detail, row_key, page_no, drawing_no,
         json.dumps(list(rect or []), default=str),
         json.dumps(capture or {}, default=str, sort_keys=True)))
    con.commit()
    return cur.lastrowid


def report_count(con, job_id: str) -> int:
    return con.execute("SELECT COUNT(*) FROM report WHERE job_id=?",
                       (job_id,)).fetchone()[0]


def list_reports(con, job_id: str) -> list:
    out = []
    for r in con.execute("SELECT * FROM report WHERE job_id=? ORDER BY id DESC",
                         (job_id,)):
        d = dict(r)
        d["rect"] = json.loads(d.pop("rect_json"))
        d["capture"] = json.loads(d.pop("capture_json"))
        out.append(d)
    return out


def get_report(con, report_id: int):
    r = con.execute("SELECT * FROM report WHERE id=?", (report_id,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["rect"] = json.loads(d.pop("rect_json"))
    d["capture"] = json.loads(d.pop("capture_json"))
    return d


def update_report(con, report_id: int, what: str = None, detail: str = None):
    """Change what a person wrote.  The capture is never rewritten - it is what
    the engine said at the time, and editing it would make the record a story."""
    cur = get_report(con, report_id)
    if cur is None:
        raise KeyError(report_id)
    if what is not None and what not in REPORT_WHAT:
        raise ValueError(f"unknown report subject '{what}'")
    con.execute("UPDATE report SET what=?, detail=?, updated_at=? WHERE id=?",
                (what if what is not None else cur["what"],
                 detail if detail is not None else cur["detail"],
                 time.time(), report_id))
    con.commit()
    return get_report(con, report_id)


def delete_report(con, report_id: int) -> None:
    if get_report(con, report_id) is None:
        raise KeyError(report_id)
    con.execute("DELETE FROM report WHERE id=?", (report_id,))
    con.commit()


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
    for r in merged_rows_cached(con, job_id):      # 읽기만 한다 (hotfix45)
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
    # The review state travels with the snapshot: a delivered workbook has to be
    # able to say, per row, what was asked and what was decided, and a snapshot
    # taken later must not pick up decisions made after it.
    states = review_states(con, job_id)
    rev = revision_states(con, job_id)
    job = get_job(con, job_id)
    for r in rows:
        r["review_state"] = states.get(r["key"], {})
        r["rev"] = rev.get(r["key"], {})
        r["excel_no"] = (r["rev"] or {}).get("excel_no") or None
        # hotfix38 — REMARK 의 "Rev.A 대비 추가" 가 읽는 비교 대상.  job 의 칸을
        # 행마다 옮겨 적는 것뿐이다 (스냅샷 행 하나가 혼자서도 말할 수 있게).
        r["rev_against"] = job["compared_with"] or ""
    # 사용자가 확정한 삭제만 산출물로 간다.  '삭제 후보' 는 검출 실패와 실제
    # 삭제를 기계가 가르지 못한다는 뜻이므로, 확정 전에는 표기하지 않는다.
    deleted_rows = []
    for d in deleted_candidates(con, job_id):
        if not d.get("confirmed"):
            continue
        deleted_rows.append({
            "key": f"deleted:{d['id']}", "tab": d.get("tab") or "FIELD",
            "page_no": d.get("page_no") or 0,
            "drawing_no": d.get("drawing_no") or "",
            "origin": "", "rect": [], "excel_no": d.get("excel_no"),
            "values": dict(d.get("values") or {},
                           description=d.get("description") or ""),
            "ai": {}, "user": {}, "evidence": {}, "needs_review": "",
            "annotation": "", "conflict": {}, "deleted": False,
            "added": False, "removed": False,
            "deleted_confirmed": True, "stable_id": d["id"],
            "rev": {"id": d["id"], "state": "DELETED"},
            "rev_against": job["compared_with"] or "",
        })
    payload = {
        "origins_included": list(origins),
        "drawings_included": sorted(wanted) if wanted else None,
        "review_held_back": bool(hold_review),
        "job_id": job_id,
        "pdf_name": job["pdf_name"],
        "pdf_sha256": job["pdf_sha256"],
        "fingerprint": job["fingerprint"],
        "engine": json.loads(job["engine_json"]),
        "project": job["project"], "revision": job["revision"],
        "compared_with": job["compared_with"],
        "revision_label": (f"{job['revision']} vs {job['compared_with']}"
                           if job["compared_with"] else
                           (f"{job['revision']} (비교 대상 없음)"
                            if job["revision"] else "")),
        "rows": rows,
        "deleted_rows": deleted_rows,
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


def replace_revision(con, revision_id: int, payload: dict) -> None:
    """Write a snapshot back after the API has annotated it.

    A snapshot is what a delivered workbook is answerable to, so it is written
    once and then only ever completed - never edited after a workbook exists.
    """
    con.execute("UPDATE revision SET payload_json=? WHERE id=?",
                (json.dumps(payload, ensure_ascii=False, default=str), revision_id))
    con.commit()


def get_revision(con, revision_id: int):
    r = con.execute("SELECT * FROM revision WHERE id=?", (revision_id,)).fetchone()
    return json.loads(r["payload_json"]) if r else None


# --------------------------------------------------------------------------
# 리비전 대조 결과
# --------------------------------------------------------------------------

def row_count(con, job_id: str) -> int:
    """살아 있는 행 수.  검토자가 지운 행은 빼고 센다 - 목록이 말하는 수와
    화면에 뜨는 수가 갈리면 안 된다."""
    return con.execute("SELECT COUNT(*) FROM item WHERE job_id=? AND removed=0"
                       " AND deleted=0", (job_id,)).fetchone()[0]


def edited_cell_count(con, job_id: str) -> int:
    """사람이 고친 **칸**의 수 (행이 아니라).  첫 화면이 "손댄 적 있는 분석"을
    구분할 수 있어야 한다."""
    n = 0
    for r in con.execute("SELECT user_json FROM item WHERE job_id=?"
                         " AND user_json<>'{}'", (job_id,)):
        n += len([v for v in json.loads(r["user_json"]).values()
                  if v not in (None, "")])
    return n


def record_save(con, job_id: str, author: str) -> dict:
    """최종 저장 한 번 (hotfix23).  그 순간의 편집 상태를 센다 — 칸 · 추가 행 · 지운 행."""
    edits = edited_cell_count(con, job_id)
    added = con.execute("SELECT COUNT(*) FROM item WHERE job_id=? AND added=1",
                        (job_id,)).fetchone()[0]
    removed = con.execute("SELECT COUNT(*) FROM item WHERE job_id=? AND removed=1",
                          (job_id,)).fetchone()[0]
    at = time.time()
    con.execute("INSERT INTO save_log (job_id, at, author, edits, added, removed)"
                " VALUES (?,?,?,?,?,?)", (job_id, at, (author or "").strip(), edits, added, removed))
    con.commit()
    return {"at": at, "author": (author or "").strip(), "edits": edits,
            "added": added, "removed": removed}


def last_save(con, job_id: str) -> dict | None:
    r = con.execute("SELECT at, author, edits, added, removed FROM save_log WHERE job_id=?"
                    " ORDER BY at DESC, id DESC LIMIT 1", (job_id,)).fetchone()
    return dict(r) if r else None


def page_revisions(con, job_id: str) -> list:
    """장별 개정 — 도면이 스스로 말한 값 그대로 (13회차).

    분석 대상이 아닌 쪽(범례 · 도면 목록)도 함께 돌려준다.  대표값은 PID 장만
    보고 접지만, 사람이 화면에서 확인할 때는 전부 보여야 한다.
    """
    return [dict(r) for r in con.execute(
        "SELECT page_no, drawing_no, page_kind, in_scope, rev, rev_method,"
        " rev_confidence, rev_date FROM pid_page WHERE job_id=? ORDER BY page_no",
        (job_id,))]


def set_facts(con, job_id: str, facts: dict) -> None:
    con.execute("UPDATE job SET facts_json=? WHERE id=?",
                (json.dumps(facts or {}, ensure_ascii=False, sort_keys=True), job_id))
    con.commit()


def output_qty(con, job_id: str, tabs, keep=None) -> dict:
    """발주처 양식에 나가는 행의 Q'ty 합 — 사람이 고친 값이 이긴다 (`_merged` 와 같은 규칙).

    행을 통째로 파싱하지 않고 두 칸만 꺼낸다 (QFE 2,041행에서 `merged_rows` 0.3초 ↔ 이것 0.02초).
    `keep(scope)` 는 `excel_out.in_client_scope` 의 판정을 넘겨받는다 (세는 기준이 두 벌이 되지 않게).
    """
    total, rows, missing = 0.0, 0, 0
    for tab, ai_q, user_q, ai_s, user_s in con.execute(
            "SELECT tab, json_extract(ai_json,'$.qty'), json_extract(user_json,'$.qty'),"
            " json_extract(ai_json,'$.scope'), json_extract(user_json,'$.scope')"
            " FROM item WHERE job_id=? AND deleted=0 AND removed=0", (job_id,)):
        if tab not in tabs:
            continue
        scope = user_s if user_s is not None else ai_s
        if keep is not None and not keep(scope or ""):
            continue
        q = user_q if user_q not in (None, "") else ai_q
        rows += 1
        try:
            total += float(q)
        except (TypeError, ValueError):
            missing += 1
    return {"qty": int(total) if total == int(total) else round(total, 2),
            "rows": rows, "qty_missing": missing}


def set_doc_rev(con, job_id: str, doc_rev: str) -> None:
    con.execute("UPDATE job SET doc_rev=? WHERE id=?", (doc_rev or "", job_id))
    con.commit()


def carry_user_values(con, job_id: str, values: dict) -> int:
    """이전 리비전의 편집을 이 리비전 행에 얹는다 (13회차 [D]).

    `values` 는 `{행 키: {열: 값}}`.  **이미 이 리비전에서 사람이 고친 칸은
    건드리지 않는다** — 승계는 빈 자리를 채우는 것이지 덮어쓰는 것이 아니다.
    `ai_json` 도 건드리지 않으므로 추출값 층은 그대로다.

    돌려주는 것은 실제로 채운 칸의 수다.  화면이 "N칸을 이어받았습니다" 라고
    적을 수 있어야 하고, 그 수가 0 이면 0 이라고 적어야 한다.
    """
    filled = 0
    for key, fields in values.items():
        row = con.execute("SELECT user_json FROM item WHERE job_id=? AND key=?",
                          (job_id, key)).fetchone()
        if row is None:
            continue
        user = json.loads(row["user_json"])
        for field, value in fields.items():
            if field not in EDITABLE or value in (None, ""):
                continue
            if field in user:               # 이 리비전에서 이미 고친 칸
                continue
            user[field] = value
            filled += 1
        con.execute("UPDATE item SET user_json=? WHERE job_id=? AND key=?",
                    (json.dumps(user, sort_keys=True), job_id, key))
    con.commit()
    return filled


def user_values_of(con, job_id: str) -> dict:
    """그 리비전에서 사람이 고친 칸 전부.  `{행 키: {열: 값}}`."""
    out = {}
    for r in con.execute("SELECT key, user_json FROM item WHERE job_id=?"
                         " AND user_json<>'{}'", (job_id,)):
        vals = {k: v for k, v in json.loads(r["user_json"]).items()
                if v not in (None, "")}
        if vals:
            out[r["key"]] = vals
    return out


def ai_values_of(con, job_id: str) -> dict:
    """그 리비전에서 엔진이 읽은 값 전부.  승계한 칸이 그 사이 바뀌었는지
    보려면 두 리비전의 이 값을 견줘야 한다."""
    return {r["key"]: json.loads(r["ai_json"])
            for r in con.execute("SELECT key, ai_json FROM item WHERE job_id=?",
                                 (job_id,))}


def flag_carry_conflicts(con, job_id: str, conflicts: dict) -> None:
    """승계한 칸에서 엔진의 답이 이전 리비전과 달라진 것을 검토로 올린다.

    재분석의 `store_result` 가 하는 것과 **같은 규칙**이다 (§13-D): 값을 고르지
    않고 둘 다 들고 사람에게 보인다.  다른 것은 비교 상대뿐이다 - 저기서는
    같은 job 의 이전 분석이고, 여기서는 이전 리비전이다.
    """
    for key, fields in conflicts.items():
        row = con.execute("SELECT needs_review, conflict_json FROM item"
                          " WHERE job_id=? AND key=?", (job_id, key)).fetchone()
        if row is None:
            continue
        conflict = json.loads(row["conflict_json"])
        conflict.update(fields)
        note = ("이전 리비전에서 이어받은 " + ", ".join(sorted(fields))
                + " 칸을 이번 도면이 다르게 읽었습니다")
        review = "; ".join(filter(None, [row["needs_review"], note]))
        con.execute("UPDATE item SET conflict_json=?, needs_review=?"
                    " WHERE job_id=? AND key=?",
                    (json.dumps(conflict, sort_keys=True), review, job_id, key))
    con.commit()


def set_job_mode(con, job_id: str, mode: str) -> None:
    con.execute("UPDATE job SET mode=? WHERE id=?", (mode or "", job_id))
    con.commit()


def set_job_revision(con, job_id: str, project: str, revision: str,
                     compared_with: str) -> None:
    con.execute("UPDATE job SET project=?, revision=?, compared_with=? WHERE id=?",
                (project, revision, compared_with, job_id))
    con.commit()


def store_revision_result(con, job_id: str, result: dict) -> None:
    """대조 결과를 갈아 끼운다.  같은 job 을 다시 대조하면 이전 것은 지워진다."""
    con.execute("DELETE FROM revision_state WHERE job_id=?", (job_id,))
    con.execute("DELETE FROM deleted_candidate WHERE job_id=?", (job_id,))
    for key, st in result["states"].items():
        con.execute(
            "INSERT INTO revision_state (job_id,row_key,stable_id,state,"
            "excel_no,moved_pt,changed_json,basis,reason,sheet_from,diffs_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (job_id, key, st.get("id", ""), st.get("state", ""),
             int(st.get("excel_no") or 0), float(st.get("moved_pt") or 0),
             json.dumps(st.get("changed") or [], ensure_ascii=False),
             st.get("basis") or "", st.get("reason") or "",
             st.get("sheet_renumbered_from") or "",
             json.dumps(st.get("field_diffs") or [], ensure_ascii=False)))
    for d in result["deleted_candidates"]:
        con.execute(
            "INSERT INTO deleted_candidate (job_id,stable_id,payload_json,confirmed)"
            " VALUES (?,?,?,0)",
            (job_id, d["id"], json.dumps(d, ensure_ascii=False)))
    con.commit()


def revision_states(con, job_id: str) -> dict:
    return {r["row_key"]: {"id": r["stable_id"], "state": r["state"],
                           "excel_no": r["excel_no"], "moved_pt": r["moved_pt"],
                           "changed": json.loads(r["changed_json"]),
                           # hotfix43 — 상태를 정하지 않는 값 차이 (옛 행은 빈 목록)
                           "field_diffs": json.loads(r["diffs_json"] or "[]"),
                           "basis": r["basis"], "reason": r["reason"],
                           "sheet_renumbered_from": r["sheet_from"]}
            for r in con.execute(
                "SELECT * FROM revision_state WHERE job_id=?", (job_id,))}


def deleted_candidates(con, job_id: str) -> list:
    out = []
    for r in con.execute(
            "SELECT * FROM deleted_candidate WHERE job_id=? ORDER BY stable_id",
            (job_id,)):
        d = json.loads(r["payload_json"])
        d["confirmed"] = bool(r["confirmed"])
        out.append(d)
    return out


def confirm_deleted(con, job_id: str, stable_id: str, confirmed: bool) -> dict:
    """사람이 '삭제 후보' 를 확정하거나 되돌린다.  확정 전에는 산출물에 안 나간다."""
    row = con.execute("SELECT payload_json FROM deleted_candidate"
                      " WHERE job_id=? AND stable_id=?",
                      (job_id, stable_id)).fetchone()
    if row is None:
        raise KeyError(stable_id)
    con.execute("UPDATE deleted_candidate SET confirmed=? WHERE job_id=? AND stable_id=?",
                (1 if confirmed else 0, job_id, stable_id))
    con.commit()
    d = json.loads(row["payload_json"])
    d["confirmed"] = confirmed
    return d


# --------------------------------------------------------------------------
# 삭제 (17회차 [E])
# --------------------------------------------------------------------------
#
# **지우는 것은 분석 하나(job)뿐이다.**  프로젝트 전체를 지우는 길은 만들지
# 않았다 — `revisions.Registry` 의 안정 ID 장부(`id_registry.json`)가 프로젝트
# 폴더에 있고, 그것이 사라지면 같은 이름으로 다시 만든 프로젝트가 번호를 1부터
# 다시 발급한다.  §7.3 이 "ID 는 Rev.A 에서 한 번만 부여" 라고 정한 것이 거기서
# 깨지고, 이미 나간 Excel 의 NO 와 충돌한다.  근거는 `docs/round17_delete.md`.
#
# 분석 하나를 지우는 것은 그 불변식을 **깨지 않는다**: `Registry.next_seq` 가
# 장부 전체의 최대 순번 + 1 을 쓰고 **상태를 보지 않으므로**(그 함수의 주석이
# "삭제된 번호도 최대값 계산에 넣는다" 라고 적어 두었다) 번호가 재사용되지
# 않는다.  그래서 이 함수는 `app/_data/projects/…` 의 어떤 파일도 건드리지
# 않는다 — DB 안의 그 분석만 지운다.
_JOB_TABLES = ("item", "revision_state", "deleted_candidate", "pid_page",
               "revision", "feedback", "review_state", "report", "save_log")


def deletion_preview(con, job_id: str) -> dict:
    """지우면 무엇이 사라지는가.  세기만 하고 아무것도 바꾸지 않는다."""
    job = get_job(con, job_id)
    if job is None:
        raise KeyError(job_id)
    counts = {}
    for t in _JOB_TABLES:
        counts[t] = con.execute(
            f"SELECT COUNT(*) FROM {t} WHERE job_id = ?", (job_id,)).fetchone()[0]
    edited = 0
    for (uj,) in con.execute(
            "SELECT user_json FROM item WHERE job_id = ? AND user_json != '{}'",
            (job_id,)):
        try:
            edited += len(json.loads(uj) or {})
        except ValueError:
            pass
    return {
        "job_id": job_id,
        "pdf_name": job["pdf_name"],
        "project": job["project"] or "",
        "revision": job["revision"] or "",
        "created_at": job["created_at"],
        "rows": counts["item"],
        "edited_cells": edited,
        "review_marks": counts["review_state"],
        "feedback": counts["feedback"],
        "reports": counts["report"],
        "revision_snapshots": counts["revision"],
        "pages": counts["pid_page"],
        "pdf_path": job["pdf_path"],
        # 같은 PDF 를 다른 분석도 쓰고 있으면 파일은 지울 수 없다.
        "pdf_shared_with": [r["id"] for r in con.execute(
            "SELECT id FROM job WHERE pdf_path = ? AND id != ?",
            (job["pdf_path"], job_id))],
        # 안정 ID 장부는 건드리지 않는다 — 지워도 번호가 재사용되지 않는다.
        "id_registry": "건드리지 않습니다 (번호는 재사용되지 않습니다)",
    }


def delete_job(con, job_id: str, author: str = "") -> dict:
    """분석 하나를 지운다.  되돌릴 수 없다.  무엇을 지웠는지는 남긴다."""
    summary = deletion_preview(con, job_id)
    for t in _JOB_TABLES:
        con.execute(f"DELETE FROM {t} WHERE job_id = ?", (job_id,))
    con.execute("DELETE FROM job WHERE id = ?", (job_id,))
    con.execute(
        "INSERT INTO deletion_log (at, author, job_id, project, revision,"
        " pdf_name, summary_json) VALUES (?,?,?,?,?,?,?)",
        (time.time(), author or "", job_id, summary["project"],
         summary["revision"], summary["pdf_name"],
         json.dumps(summary, ensure_ascii=False, sort_keys=True)))
    con.commit()
    return summary


def project_deletion_preview(con, project: str) -> dict:
    """그 프로젝트를 지우면 무엇이 사라지는가.  **세기만 한다** (46회차 [C]).

    분석 하나짜리 `deletion_preview` 를 그 프로젝트의 모든 분석에 돌려 합친다 —
    세는 코드를 두 벌 두지 않는다.
    """
    jobs = [r["id"] for r in con.execute(
        "SELECT id FROM job WHERE project = ? ORDER BY created_at", (project,))]
    each = [deletion_preview(con, j) for j in jobs]
    uploads = sorted({e["pdf_path"] for e in each if not e["pdf_shared_with"]})
    authors = sorted({r[0] for r in con.execute(
        "SELECT DISTINCT author FROM feedback f JOIN job j ON j.id = f.job_id"
        " WHERE j.project = ? AND author != ''", (project,))})
    return {
        "project": project,
        "jobs": each,
        "job_count": len(each),
        "rows": sum(e["rows"] for e in each),
        "edited_cells": sum(e["edited_cells"] for e in each),
        "feedback": sum(e["feedback"] for e in each),
        "revision_snapshots": sum(e["revision_snapshots"] for e in each),
        "uploads_to_remove": uploads,
        "authors": authors,
    }


def delete_project(con, project: str, author: str = "") -> dict:
    """그 프로젝트의 분석을 **하나씩** 지운다.  되돌릴 수 없다.

    `delete_job` 을 그대로 부르므로 `deletion_log` 에 분석마다 한 줄이 남는다 —
    지운 단위를 나중에 세려면 그 로그가 답이다.
    """
    summary = project_deletion_preview(con, project)
    for e in summary["jobs"]:
        delete_job(con, e["job_id"], author=author)
    return summary


def deletion_log(con, limit: int = 50) -> list:
    return [dict(r) for r in con.execute(
        "SELECT id, at, author, job_id, project, revision, pdf_name, summary_json"
        " FROM deletion_log ORDER BY id DESC LIMIT ?", (limit,))]
