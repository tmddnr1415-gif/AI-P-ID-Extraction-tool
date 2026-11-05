"""hotfix132 — 전체 자료 백업·복구 도구 (spike/backup_data.py · backup_pid_data.bat)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
import backup_data as bd  # noqa: E402


def _make_data(d: Path) -> None:
    d.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(d / "app.db")
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("create table t(x)")
    con.executemany("insert into t values (?)", [(i,) for i in range(50)])
    con.commit()
    # 연결을 열어 둔 채(=wal 이 남은 채) 백업해야 한다 — 서버가 도는 상황
    (d / "uploads").mkdir()
    (d / "uploads" / "a.pdf").write_bytes(b"%PDF-1.4 drawing")
    (d / "logic" / "drawings" / "j1" / "pages").mkdir(parents=True)
    (d / "logic" / "drawings" / "j1" / "source.pdf").write_bytes(b"%PDF logic")
    (d / "logic" / "drawings" / "j1" / "pages" / "p1.png").write_bytes(b"png")
    (d / "logic" / "projects.json").write_text('{"p": 1}', encoding="utf-8")
    (d / "space").mkdir()
    (d / "space" / "rooms.json").write_text("[1,2]", encoding="utf-8")
    (d / "books").mkdir()
    (d / "books" / "config.json").write_text(json.dumps({"roots": ["X"], "translate": {"on": True, "apiKey": "sk-secret"}}),
                                             encoding="utf-8")
    (d / "books" / "secret.json").write_text('{"apiKey": "sk-secret2"}', encoding="utf-8")
    (d / "page_cache").mkdir()
    (d / "page_cache" / "c.png").write_bytes(b"x")
    (d / "backups").mkdir()
    (d / "backups" / "app.db.20261101.bak").write_bytes(b"old")
    return con


def _tree(d: Path) -> dict:
    return {p.relative_to(d).as_posix(): p.read_bytes() for p in d.rglob("*") if p.is_file()}


def test_backup_then_restore_brings_back_every_screen(tmp_path, monkeypatch):
    data, dest = tmp_path / "data", tmp_path / "bk"
    con = _make_data(data)
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": False)
    out = bd.backup(dest, src=data, voc=tmp_path / "novoc", stamp="20261105_0930")
    con.close()
    man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert man["integrity"] == "ok" and man["files"] >= 5
    got = _tree(out)
    assert "page_cache/c.png" not in got and "backups/app.db.20261101.bak" not in got
    assert "logic/drawings/j1/pages/p1.png" not in got and "logic/drawings/j1/source.pdf" in got
    assert "books/secret.json" not in got and "app.db-wal" not in got and "app.db-shm" not in got
    cfg = json.loads(got["books/config.json"])
    assert "apiKey" not in json.dumps(cfg) and cfg["translate"]["on"] is True and cfg["roots"] == ["X"]
    before = _tree(data)

    # 사고: uploads 와 space 를 잃었다 → 복구
    import shutil
    shutil.rmtree(data / "uploads")
    (data / "space" / "rooms.json").write_text("[]", encoding="utf-8")
    assert bd.restore(out, dst=data, voc=tmp_path / "novoc") == 0
    after = _tree(data)
    for rel in ("uploads/a.pdf", "space/rooms.json", "logic/projects.json", "logic/drawings/j1/source.pdf"):
        assert after[rel] == before[rel], rel
    assert "backups/app.db.20261101.bak" in after                       # 서버의 DB 사본은 제자리
    assert json.loads(after["books/secret.json"])["apiKey"] == "sk-secret2"   # 지금 키를 옮겨 준다
    assert json.loads(after["books/config.json"])["translate"]["apiKey"] == "sk-secret"
    assert not (data / "app.db-wal").exists() and not (data / "app.db-shm").exists()
    c = sqlite3.connect(data / "app.db")
    assert c.execute("select count(*) from t").fetchone()[0] == 50
    assert c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    c.close()
    aside = [p for p in tmp_path.iterdir() if p.name.startswith("data_before_restore_")]
    assert len(aside) == 1 and (aside[0] / "space" / "rooms.json").read_text() == "[]"   # 지우지 않고 옮겨 둔다


def test_restore_refuses_while_the_server_answers(tmp_path, monkeypatch, capsys):
    data, dest = tmp_path / "data", tmp_path / "bk"
    _make_data(data).close()
    out = bd.backup(dest, src=data, voc=tmp_path / "novoc")
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": True)
    before = _tree(data)
    assert bd.restore(out, dst=data, voc=tmp_path / "novoc") == 2
    assert "서버를 먼저 끄세요" in capsys.readouterr().out
    assert _tree(data) == before


def test_restore_dry_run_changes_nothing(tmp_path, monkeypatch):
    data, dest = tmp_path / "data", tmp_path / "bk"
    _make_data(data).close()
    out = bd.backup(dest, src=data, voc=tmp_path / "novoc")
    (data / "uploads" / "new.pdf").write_bytes(b"new")
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": False)
    before = _tree(data)
    assert bd.restore(out, dry=True, dst=data, voc=tmp_path / "novoc") == 0
    assert _tree(data) == before


def test_keep_prunes_old_sets_and_default_dest_inside_data_is_not_copied(tmp_path):
    data = tmp_path / "data"
    _make_data(data).close()
    dest = data / "backups"                                           # 기본 자리 — 자료 폴더 안
    for i in range(4):
        bd.backup(dest, keep=2, src=data, voc=tmp_path / "novoc", stamp=f"2026110{i}_0000")
    have = bd.listing(dest)
    assert [p.name for p in have] == ["pid_backup_20261102_0000", "pid_backup_20261103_0000"]
    assert not any("pid_backup_" in k for k in _tree(have[-1]))       # 백업이 백업을 담지 않는다


def test_source_mode_voc_is_kept(tmp_path, monkeypatch):
    data, voc = tmp_path / "data", tmp_path / "voc"
    _make_data(data).close()
    voc.mkdir()
    (voc / "2026-11.jsonl").write_text('{"t": "의견"}\n', encoding="utf-8")
    out = bd.backup(tmp_path / "bk", src=data, voc=voc)
    assert (out / "_voc" / "2026-11.jsonl").is_file()
    (voc / "2026-11.jsonl").unlink()
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": False)
    assert bd.restore(out, dst=data, voc=voc) == 0
    assert "의견" in (voc / "2026-11.jsonl").read_text(encoding="utf-8")


def test_not_a_backup_folder_is_refused(tmp_path):
    assert bd.restore(tmp_path) == 1


def test_bat_passes_one_destination_and_is_ascii_crlf():
    raw = (ROOT / "backup_pid_data.bat").read_bytes()
    raw.decode("ascii")
    assert b"\r\n" in raw and raw.count(b"\n") == raw.count(b"\r\n")
    body = raw.decode("ascii")
    assert "spike\\backup_data.py" in body and "PID_BACKUP_DIR" in body
    assert "%PID_BACKUP_DIR% %*" not in body                          # 목적지가 둘이 되지 않게
