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
    tag = bd.tag_of(data)
    assert [p.name for p in have] == [f"pid_backup_20261102_0000_{tag}", f"pid_backup_20261103_0000_{tag}"]
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
    # 운영 자료가 있으면 그것을 · 없으면 이 폴더의 app\_data — 어느 폴더인지 맨 먼저 말한다
    assert 'if exist "C:\\Claude\\PID\\app\\_data\\*" set "DATA=C:\\Claude\\PID\\app\\_data"' in body
    assert body.index("echo Data folder") < body.index(":given")
    assert body.count('--data "%DATA%"') == 3                         # 백업 · 목적지 · 복구 모두 같은 자료 폴더


# ---------------------------------------------------------------- --data · 같이 쓰는 목적지 · 폴더째 복구
def test_data_option_backs_up_and_restores_that_folder(tmp_path, monkeypatch, capsys):
    ops = tmp_path / "PID" / "app" / "_data"
    _make_data(ops).close()
    (tmp_path / "PID" / "voc").mkdir()
    (tmp_path / "PID" / "voc" / "a.jsonl").write_text("의견\n", encoding="utf-8")
    monkeypatch.delenv("PID_BACKUP_DIR", raising=False)
    monkeypatch.delenv("PID_VOC_DIR", raising=False)
    bk = tmp_path / "bk"
    # bat 이 앞에 붙인 기본 --data 보다 사용자가 뒤에 준 --data 가 이긴다
    assert bd.main(["--data", str(tmp_path / "nowhere"), str(bk), "--data", str(ops)]) == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith(f"자료 폴더: {ops.resolve()}")
    made = bd.listing(bk)
    assert len(made) == 1 and made[0].name.endswith("_" + bd.tag_of(ops))
    assert (made[0] / "_voc" / "a.jsonl").is_file()                    # 운영의 voc (도구 폴더의 voc 가 아니라)
    (ops / "space" / "rooms.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": False)
    assert bd.main(["--restore", str(made[0]), "--data", str(ops), "--port", "9000"]) == 0
    assert (ops / "space" / "rooms.json").read_text(encoding="utf-8") == "[1,2]"


def test_restore_checks_the_given_port(tmp_path, monkeypatch, capsys):
    data = tmp_path / "data"
    _make_data(data).close()
    out = bd.backup(tmp_path / "bk", src=data, voc=tmp_path / "novoc")
    asked = []
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": asked.append(port) or True)
    assert bd.main(["--restore", str(out), "--data", str(data), "--port", "9000"]) == 2
    assert asked == [9000]
    assert bd.main(["--restore", str(out), "--data", str(data), "--port", "abc"]) == 2
    assert asked[-1] == 8000                                           # 숫자가 아니면 기본값


def test_shared_destination_keeps_the_other_folders_sets(tmp_path):
    a, b, dest = tmp_path / "dev" / "app" / "_data", tmp_path / "ops" / "app" / "_data", tmp_path / "shared"
    _make_data(a).close()
    _make_data(b).close()
    for i in range(3):
        bd.backup(dest, keep=2, src=a, voc=tmp_path / "novoc", stamp=f"2026110{i}_0000")
    bd.backup(dest, keep=2, src=b, voc=tmp_path / "novoc", stamp="20261101_0000")
    assert len(bd.listing(dest, bd.tag_of(a))) == 2 and len(bd.listing(dest, bd.tag_of(b))) == 1
    assert bd.tag_of(a) != bd.tag_of(b)


def test_restore_moves_the_folder_whole_and_undoes_a_failed_copy(tmp_path, monkeypatch, capsys):
    data = tmp_path / "data"
    _make_data(data).close()
    out = bd.backup(data / "backups", src=data, voc=tmp_path / "novoc")
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": False)
    (data / "uploads" / "new.pdf").write_bytes(b"new")
    before = _tree(data)
    real = bd.shutil.copy2
    calls = []

    def flaky(src, dst, *a, **k):
        calls.append(src)
        if len(calls) == 3:
            raise OSError(28, "No space left on device")
        return real(src, dst, *a, **k)
    monkeypatch.setattr(bd.shutil, "copy2", flaky)
    assert bd.restore(out, dst=data, voc=tmp_path / "novoc") == 4
    said = capsys.readouterr().out
    assert "원래 자료로 되돌려 놓았습니다" in said and "Traceback" not in said
    assert _tree(data) == before                                       # 한 파일도 갈라지지 않았다
    assert not [p for p in tmp_path.iterdir() if "_before_restore_" in p.name]


def test_restore_refuses_cleanly_when_the_folder_cannot_be_renamed(tmp_path, monkeypatch, capsys):
    data = tmp_path / "data"
    _make_data(data).close()
    out = bd.backup(tmp_path / "bk", src=data, voc=tmp_path / "novoc")
    monkeypatch.setattr(bd, "server_answers", lambda port=8000, host="127.0.0.1": False)
    before = _tree(data)
    real = bd.os.replace

    def locked(a, b):
        if Path(a) == data:
            raise PermissionError(13, "The process cannot access the file")
        return real(a, b)
    monkeypatch.setattr(bd.os, "replace", locked)
    assert bd.restore(out, dst=data, voc=tmp_path / "novoc") == 4
    said = capsys.readouterr().out
    assert "이름을 바꾸지 못했습니다" in said and "아무것도 바꾸지 않았습니다" in said
    assert _tree(data) == before
