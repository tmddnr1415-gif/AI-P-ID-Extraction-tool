"""hotfix74 — 저장된 상태가 망가졌을 때 (`spike/state_chaos.py`).

① 상태 파일(JSON)은 원자적으로 쓰고 바로 앞 판을 `.bak` 으로 남긴다.  깨지면 옆에 떠 두고 백업으로 되살린다.
② 한 프로젝트 장부가 깨져도 첫 화면 전체가 500 이 되지 않는다.
③ 원본 PDF 가 사라지면 410 과 사람 말.
④ DB 가 깨지면 영문 예외가 아니라 무엇을 하면 되는지 말하고 멈춘다 · 하루 한 번 백업.
⑤ 공유 연결 호출을 줄 세운다 — 여러 스레드가 동시에 써도 실패 0.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import pytest

# 다른 시험이 `app.*` 를 다시 읽으면 모듈·예외 클래스가 두 벌이 된다 — 시험마다 지금 것을 집는다.
def _mods():
    import importlib
    return tuple(importlib.import_module(f"app.{n}") for n in ("db", "jsonstore", "main", "revisions"))


def test_write_is_atomic_and_keeps_the_previous_version(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "a.json"
    jsonstore.write(p, {"v": 1})
    jsonstore.write(p, {"v": 2})
    assert json.loads(p.read_text(encoding="utf-8")) == {"v": 2}
    assert json.loads((tmp_path / "a.json.bak").read_text(encoding="utf-8")) == {"v": 1}
    assert not list(tmp_path.glob("*.tmp*"))
    # 예전 write_text 와 바이트까지 같다 (두 번 저장하면 같은 파일)
    assert p.read_text(encoding="utf-8") == json.dumps({"v": 2}, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def test_corrupt_file_is_restored_from_backup_and_kept_aside(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "b.json"
    jsonstore.write(p, {"keep": "me"})
    jsonstore.write(p, {"keep": "me2"})
    p.write_bytes(b'{"keep": "me')                     # 저장 도중 끊김
    assert jsonstore.read(p, {}, what="시험") == {"keep": "me"}
    assert json.loads(p.read_text(encoding="utf-8")) == {"keep": "me"}
    assert list(tmp_path.glob("b.json.corrupt-*"))


def test_required_file_without_backup_stops_in_words(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "id_registry.json"
    p.write_bytes(b"\0\1garbage")
    with pytest.raises(jsonstore.StateFileCorrupt) as e:
        revisions.Registry.load(p)
    assert "안정 ID 장부" in str(e.value) and "백업" in str(e.value)
    assert list(tmp_path.glob("id_registry.json.corrupt-*"))


def test_wrong_shape_is_treated_like_corrupt(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "project.json"
    p.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(jsonstore.StateFileCorrupt):
        jsonstore.read(p, what="프로젝트 장부", required=True, expect=dict)


def test_one_broken_project_does_not_break_the_listing(tmp_path):
    db, jsonstore, main, revisions = _mods()
    root = tmp_path / "projects"
    (root / "GOOD").mkdir(parents=True)
    (root / "BAD").mkdir()
    jsonstore.write(root / "GOOD" / "project.json", {"name": "GOOD", "revisions": []})
    (root / "BAD" / "project.json").write_bytes(b'{"name": "BA')
    names = [p["name"] for p in revisions.list_projects(tmp_path)]
    assert names == ["GOOD"]
    assert any("BAD" in (r.get("what") or "") for r in jsonstore.incidents())


def test_corrupt_db_stops_with_what_to_do(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "app.db"
    p.write_bytes(b"\0" * 4096)
    with pytest.raises(db.DatabaseCorrupt) as e:
        db.connect(p)
    assert "지우거나 덮지 않고" in str(e.value)


def test_daily_backup_is_a_readable_copy(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "app.db"
    con = db.connect(p)
    db.create_job(con, "b1", "x.pdf", "sha", Path("/x.pdf"))
    made = db.backup_daily(p)
    assert made and made.exists()
    assert db.backup_daily(p) == made                 # 하루 한 번
    c2 = sqlite3.connect(made)
    assert c2.execute("select count(*) from job").fetchone()[0] == 1
    c2.close()
    con.close()
    p.write_bytes(b"\0" * 4096)
    with pytest.raises(db.DatabaseCorrupt) as e:
        db.connect(p)
    assert made.name in str(e.value)                   # 깨지면 그 백업을 가리킨다


def test_shared_connection_serialises_threads(tmp_path):
    db, jsonstore, main, revisions = _mods()
    con = db.connect(tmp_path / "t.db")
    con.execute("CREATE TABLE IF NOT EXISTS t (a)")
    con.commit()
    errs = []

    def w():
        for i in range(400):
            try:
                con.execute("INSERT INTO t VALUES (?)", (i,))
                con.commit()
            except Exception as exc:                  # noqa: BLE001
                errs.append(str(exc))
    ts = [threading.Thread(target=w) for _ in range(6)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errs == []
    assert con.execute("select count(*) from t").fetchone()[0] == 2400


def test_missing_source_answers_410_in_words():
    db, jsonstore, main, revisions = _mods()
    job = {"pdf_path": "/nonexistent/uploads/gone.pdf"}
    with pytest.raises(main.HTTPException) as e:
        main._require_source(job)
    assert e.value.status_code == 410 and "gone.pdf" in e.value.detail


def test_every_state_writer_goes_through_jsonstore():
    db, jsonstore, main, revisions = _mods()
    root = Path(main.__file__).resolve().parent
    for name in ("revisions.py", "axis_overrides.py", "global_symbols.py", "legend_profile.py", "sheet_memo.py",
                 "sheet_numbers.py", "title_block_cells.py", "unit_multipliers.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "jsonstore.write(" in src, name
        assert "json.loads(path.read_text" not in src and "json.loads(p.read_text" not in src, name


def test_template_upload_refuses_non_xlsx():
    db, jsonstore, main, revisions = _mods()
    assert "구형" in main._template_problem(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 64)
    assert main._template_problem(b"") == "빈 파일입니다"
    assert "아닙니다" in main._template_problem(b"hello")
    assert "열리지" in main._template_problem(b"PK\x03\x04garbage")
    import io as _io
    import openpyxl
    buf = _io.BytesIO()
    openpyxl.Workbook().save(buf)
    assert main._template_problem(buf.getvalue()) == ""


def test_downloads_do_not_navigate_away():
    js = (Path(__file__).resolve().parent.parent / "app/static/app.js").read_text(encoding="utf-8")
    assert "async function downloadUrl(" in js
    assert "location.href = `/revisions/" not in js and "location.href = `/jobs/" not in js
    assert 'id="sheet-err"' in (Path(__file__).resolve().parent.parent / "app/static/index.html").read_text(encoding="utf-8")


def test_disk_full_answers_507_in_words():
    import asyncio
    import errno
    db, jsonstore, main, revisions = _mods()

    class _Req:
        method = "POST"
        class url:                                     # noqa: N801
            path = "/x"
    r = asyncio.run(main._unexpected_error(_Req(), OSError(errno.ENOSPC, "No space left on device")))
    assert r.status_code == 507 and "디스크가 가득" in r.body.decode("utf-8")
    r = asyncio.run(main._db_busy(_Req(), sqlite3.OperationalError("database or disk is full")))
    assert r.status_code == 507


def test_environment_causes_are_named_in_failure_reason():
    db, jsonstore, main, revisions = _mods()
    assert "디스크" in main._known_cause("OSError: [Errno 28] No space left on device")
    assert "메모리" in main._known_cause("Traceback ...\nMemoryError")
    assert main._known_cause("ValueError: x") == ""


def test_reanalyse_twice_is_refused_while_queued(tmp_path):
    db, jsonstore, main, revisions = _mods()
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
    jid = "r" + "0" * 11
    db.create_job(main.CON, jid, "x.pdf", "sha", pdf)
    try:
        main.CON.execute("UPDATE job SET status='queued' WHERE id=?", (jid,))
        main.CON.commit()
        with pytest.raises(main.HTTPException) as e:
            main.reanalyse(jid)
        assert e.value.status_code == 409
    finally:
        main.CON.execute("DELETE FROM job WHERE id=?", (jid,))
        main.CON.commit()


def test_concurrent_mutations_do_not_lose_updates(tmp_path):
    import importlib
    um = importlib.import_module("app.unit_multipliers")
    (tmp_path / "projects" / "P").mkdir(parents=True)
    units = [f"{i:02d}" for i in range(10, 40)]
    errs = []

    def go(u):
        try:
            um.set_unit(tmp_path, "P", unit=u, multiplier=2, author="a")
        except Exception as exc:                      # noqa: BLE001
            errs.append(repr(exc))
    ts = [threading.Thread(target=go, args=(u,)) for u in units]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errs == []
    assert sorted(um.load(tmp_path, "P")["units"]) == units      # 30 개 전부 (예전엔 3개만 남았다)


def test_upload_reports_a_byte_identical_earlier_analysis():
    src = (Path(__file__).resolve().parent.parent / "app/main.py").read_text(encoding="utf-8")
    js = (Path(__file__).resolve().parent.parent / "app/static/app.js").read_text(encoding="utf-8")
    assert '"duplicate_of": duplicate_of' in src and "WHERE pdf_sha256=?" in src
    assert "job.duplicate_of" in js


def test_rows_by_keys_matches_the_full_parse(tmp_path):
    db, jsonstore, main, revisions = _mods()
    con = db.connect(tmp_path / "k.db")
    for i in range(30):
        con.execute("INSERT INTO item (job_id,key,tab,page_no,ai_json,user_json,needs_review) VALUES (?,?,?,?,?,?,?)",
                    ("J", f"k{i:02d}", "FIELD" if i % 3 else "MOV", 30 - i,
                     json.dumps({"type": "PIT", "qty": i}), json.dumps({"qty": 9} if i % 4 == 0 else {}),
                     "x" if i % 5 == 0 else ""))
    con.commit()
    keys = ["k03", "k10", "k00", "k29", "nope"]
    for tab in ("ALL", "FIELD", "MOV", "REVIEW"):
        full = [r for r in db.merged_rows(con, "J", tab) if r["key"] in keys]
        assert db.merged_rows_by_keys(con, "J", keys, tab) == full, tab


def test_repeated_reads_of_the_same_broken_file_record_once(tmp_path):
    db, jsonstore, main, revisions = _mods()
    p = tmp_path / "m.json"
    p.write_bytes(b'{"a": ')
    n0 = len(jsonstore.incidents())
    for _ in range(5):
        assert jsonstore.read(p, {}, what="시험") == {}
    assert len(jsonstore.incidents()) == n0 + 1
    assert len(list(tmp_path.glob("m.json.corrupt-*"))) == 1


def test_write_retries_a_briefly_locked_file(tmp_path, monkeypatch):
    db, jsonstore, main, revisions = _mods()
    import os as _os
    real = _os.replace
    calls = {"n": 0}

    def flaky(a, b):
        calls["n"] += 1
        if calls["n"] <= 2:
            raise PermissionError(13, "file in use")         # Windows: 백신·편집기가 잠깐 열고 있다
        return real(a, b)
    monkeypatch.setattr(jsonstore.os, "replace", flaky)
    p = tmp_path / "w.json"
    jsonstore.write(p, {"ok": 1})
    assert json.loads(p.read_text(encoding="utf-8")) == {"ok": 1} and calls["n"] == 3
    assert not list(tmp_path.glob("*.tmp*"))
