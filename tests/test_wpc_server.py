"""hotfix132 — 서버 견고함 · 보안 · API (작업 묶음 C).

C1 백업 루프 · C2 본문 상한 · C3 장 그림 배율 · C4 도서 폴더 지정 · C5 API 키 분리 · C6 한국어 오류 ·
C7 공개 범위 · C8 진행 SSE · C9 동기 라우트 · C10 설명서·보안 머리말 · C11 목록 메모 상한.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import threading
import time
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import audit, books, db, main, paths, version

ROOT = Path(__file__).resolve().parent.parent
MAIN_SRC = (ROOT / "app" / "main.py").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _fresh_modules():
    """다른 시험이 app 모듈을 다시 읽어 들였을 수 있다 — 지금 올라 있는 판을 쓴다 (main · db · audit 가 같은 판이게)."""
    import importlib
    g = globals()
    for n in ("audit", "books", "db", "main", "paths", "version"):
        g[n] = importlib.import_module(f"app.{n}")


@pytest.fixture()
def client():
    return TestClient(main.app)


def _job(job_id: str, pages: int = 1) -> tuple[str, Path]:
    """done 상태의 분석 하나 — 진짜 PDF 와 행 하나 (test_hotfix45 의 꼴)."""
    import pymupdf
    main.UPLOADS.mkdir(parents=True, exist_ok=True)
    pdf = main.UPLOADS / f"{job_id}_x.pdf"
    doc = pymupdf.open()
    for i in range(pages):
        pg = doc.new_page(width=200, height=120)
        pg.insert_text((20, 40), f"SHEET {i + 1}")
    doc.save(str(pdf))
    doc.close()
    main.CON.execute("DELETE FROM job WHERE id=?", (job_id,))
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,progress,message,fingerprint,project,revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'','','','A')", (job_id, "x.pdf", job_id, str(pdf), time.time()))
    db.add_row(main.CON, job_id, page_no=1, tab="FIELD", drawing_no="D-1", values={"type": "PI", "qty": 1},
               rect=[10, 20, 15, 30])
    main.CON.commit()
    return job_id, pdf


def _has_hangul(s: str) -> bool:
    return any("가" <= ch <= "힣" for ch in s)


# ---------------------------------------------------------------- C1 백업 루프
def test_backup_loop_runs_every_interval_until_stopped(monkeypatch):
    calls = []
    stop = threading.Event()

    def fake_backup(path):
        calls.append(path)
        if len(calls) >= 2:
            stop.set()
        return None

    monkeypatch.setattr(db, "backup_daily", fake_backup)
    main._daily_backup(stop=stop, interval=0.01)
    assert len(calls) == 2                       # 한 번이 아니라 바퀴마다 확인한다


def test_backup_loop_records_failure_and_audit_shows_one_line(monkeypatch):
    stop = threading.Event()

    def boom(path):
        stop.set()
        raise OSError("디스크 없음")

    monkeypatch.setattr(db, "backup_daily", boom)
    monkeypatch.setattr(db, "LAST_BACKUP", {})
    main._daily_backup(stop=stop, interval=0.01)
    assert db.LAST_BACKUP["ok"] is False and "디스크 없음" in db.LAST_BACKUP["err"]
    out = audit.run(main.CON, main.DATA_DIR)
    assert out["backup"]["ok"] is False
    assert any(line.startswith("DB 백업 실패") for line in out["lines"])


def test_backup_dir_override_and_keep_seven(monkeypatch, tmp_path):
    import sqlite3
    src = tmp_path / "data" / "app.db"
    src.parent.mkdir()
    sqlite3.connect(src).close()
    other = tmp_path / "other_drive"
    monkeypatch.setenv("PID_BACKUP_DIR", str(other))
    monkeypatch.setattr(db, "LAST_BACKUP", {})
    made = db.backup_daily(src)
    assert made is not None and made.parent == other and made.exists()
    assert db.backups(src) == [made]             # 깨진 DB 복구 안내도 같은 폴더를 본다
    assert db.LAST_BACKUP["ok"] is True
    assert db.BACKUP_KEEP == 7
    # 정상 백업은 줄로 내지 않는다 (화면이 숫자 없는 줄을 '확인할 항목' 으로 센다) — backup 키로만
    st = audit.backup_status(src.parent)
    assert st["ok"] is True and st["stale"] is False and audit._backup_lines(st) == []


def test_shared_backup_dir_keeps_each_data_folders_own_sets(monkeypatch, tmp_path):
    """같은 PID_BACKUP_DIR 를 두 서버(PID_dev · 운영)가 같이 써도 서로의 판을 건너뛰거나 지우지 않는다."""
    import sqlite3
    a, b = tmp_path / "dev" / "app.db", tmp_path / "ops" / "app.db"
    for p in (a, b):
        p.parent.mkdir()
        sqlite3.connect(p).close()
    shared = tmp_path / "shared"
    monkeypatch.setenv("PID_BACKUP_DIR", str(shared))
    monkeypatch.setattr(db, "LAST_BACKUP", {})
    ma, mb = db.backup_daily(a), db.backup_daily(b)
    assert ma != mb and ma.exists() and mb.exists()                  # 같은 날이어도 둘 다 뜬다
    assert db.data_tag(a.parent) in ma.name and db.data_tag(b.parent) in mb.name
    old = shared / f"app.db.{db.data_tag(a.parent)}.2026-01-01.bak"
    old.write_bytes(b"x")
    ma.unlink()
    ma = db.backup_daily(a, keep=1)                                  # a 의 정리는 a 의 판만
    assert not old.exists() and mb.exists()
    assert db.backups(a) == [ma] and db.backups(b) == [mb]
    monkeypatch.delenv("PID_BACKUP_DIR")
    assert db.backup_daily(a).name.startswith("app.db.2")            # DB 옆 backups/ 는 옛 이름 그대로


def test_startup_tasks_switch_exists():
    assert 'os.environ.get("PID_STARTUP_TASKS", "1") != "0"' in MAIN_SRC
    i = MAIN_SRC.index("def _start_background")
    body = MAIN_SRC[i:i + 2000]
    assert body.index("if _STARTUP_TASKS:") < body.index("target=_daily_backup")
    assert body.index("target=_worker") > 0       # 작업 스레드는 그대로 import 때


# ---------------------------------------------------------------- C2 본문 상한
def test_json_body_over_limit_is_413_in_korean(client, monkeypatch):
    monkeypatch.setenv("PID_MAX_JSON_MB", "0.001")          # ≈ 1KB
    r = client.patch("/jobs/nojob/rows/nokey", content=b"{" + b" " * 4000 + b"}",
                     headers={"content-type": "application/json"})
    assert r.status_code == 413 and "너무 큽니다" in r.json()["detail"]


def test_chunked_body_without_length_is_cut(client, monkeypatch):
    monkeypatch.setenv("PID_MAX_JSON_MB", "0.001")

    def gen():
        for _ in range(10):
            yield b" " * 1000

    r = client.patch("/jobs/nojob/rows/nokey", content=gen(), headers={"content-type": "application/json"})
    assert r.status_code == 413 and "너무 큽니다" in r.json()["detail"]


def test_upload_limit_is_separate_and_covers_valve():
    assert main._body_limit("/jobs", "multipart/form-data; boundary=x") == 500 * 1024 * 1024
    assert main._body_limit("/api/valve/projects/p/upload", "multipart/form-data; boundary=x") == 500 * 1024 * 1024
    assert main._body_limit("/api/books/book", "application/gzip") == 500 * 1024 * 1024
    assert main._body_limit("/jobs/x/rows/y", "application/json") == 20 * 1024 * 1024


def test_small_bodies_pass_through(client, monkeypatch):
    monkeypatch.setenv("PID_MAX_JSON_MB", "0.001")
    r = client.patch("/jobs/nojob/rows/nokey", json={"field": "qty", "value": 1})
    assert r.status_code == 404                 # 상한에 걸리지 않고 라우트까지 갔다


# ---------------------------------------------------------------- C3 장 그림 배율
def test_page_zoom_is_validated_and_cache_is_normalised(client):
    job, _ = _job("wpczoom")
    for bad in ("0", "-1", "100", "abc"):
        r = client.get(f"/jobs/{job}/page/1.png", params={"zoom": bad})
        assert r.status_code == 400 and _has_hangul(r.json()["detail"]), bad
    r = client.get(f"/jobs/{job}/page/1.png", params={"zoom": "0.75"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert (main.PAGE_CACHE / job / "p1_z0.75.png").is_file()          # 0.75 는 0.8 로 바뀌지 않는다
    for z in ("1.6", "1.60001"):
        assert client.get(f"/jobs/{job}/page/1.png", params={"zoom": z}).status_code == 200
    names = sorted(p.name for p in (main.PAGE_CACHE / job).iterdir())
    assert names == ["p1_z0.75.png", "p1_z1.6.png"]


# ---------------------------------------------------------------- C4 · C5 도서검토
@pytest.fixture()
def books_dir():
    import shutil
    shutil.rmtree(paths.data_dir() / "books", ignore_errors=True)
    yield paths.data_dir() / "books"
    shutil.rmtree(paths.data_dir() / "books", ignore_errors=True)


def test_books_root_needs_the_server_pc_even_for_managers(books_dir, tmp_path):
    books_dir.mkdir(parents=True, exist_ok=True)
    (books_dir / "config.json").write_text(json.dumps({"managers": ["홍길동"]}, ensure_ascii=False), encoding="utf-8")
    lib = tmp_path / "lib"
    lib.mkdir()
    other = TestClient(main.app, client=("127.0.0.2", 1))
    r = other.put("/api/books/root", json={"root": str(lib)}, headers={"X-Author": quote("홍길동")})
    assert r.status_code == 403 and "서버 PC" in r.json()["error"]


def test_books_root_refuses_broad_or_private_folders(books_dir, tmp_path, monkeypatch):
    monkeypatch.setattr(books, "_LOOPBACK", books._LOOPBACK | {"testclient"})
    c = TestClient(main.app)
    data = paths.data_dir()
    (data / "books").mkdir(parents=True, exist_ok=True)
    for bad in ("/", str(Path.home()), str(paths.resource_root()), str(data), str(data / "books")):
        r = c.put("/api/books/root", json={"root": bad})
        assert r.status_code == 400 and "지정할 수 없습니다" in r.json()["error"], bad
    lib = tmp_path / "lib"
    lib.mkdir()
    assert c.put("/api/books/root", json={"root": str(lib)}).status_code == 200


def test_api_key_lives_only_in_secret_file(books_dir, monkeypatch):
    monkeypatch.setattr(books, "_LOOPBACK", books._LOOPBACK | {"testclient"})
    c = TestClient(main.app)
    key = "sk-ant-TESTKEY123"
    r = c.put("/api/books/translate-config", json={"apiKey": key, "enabled": True})
    assert r.status_code == 200
    for name in ("config.json", "config.json.bak"):
        f = books_dir / name
        assert not f.exists() or key not in f.read_text(encoding="utf-8"), name
    secret = books_dir / "secret.json"
    assert key in secret.read_text(encoding="utf-8")
    assert not (books_dir / "secret.json.bak").exists()
    if os.name != "nt":
        assert (secret.stat().st_mode & 0o777) == 0o600
    assert key not in c.get("/api/books/info").text


def test_old_key_in_config_is_moved_on_first_read(books_dir, monkeypatch):
    books_dir.mkdir(parents=True, exist_ok=True)
    old = {"translate": {"enabled": True, "apiKey": "sk-ant-OLD"}}
    (books_dir / "config.json").write_text(json.dumps(old), encoding="utf-8")
    (books_dir / "config.json.bak").write_text(json.dumps(old), encoding="utf-8")
    info = TestClient(main.app).get("/api/books/info")
    assert info.status_code == 200 and "sk-ant-OLD" not in info.text
    assert "sk-ant-OLD" in (books_dir / "secret.json").read_text(encoding="utf-8")
    for name in ("config.json", "config.json.bak"):
        assert "sk-ant-OLD" not in (books_dir / name).read_text(encoding="utf-8"), name


# ---------------------------------------------------------------- C6 한국어 오류
def test_default_errors_are_korean(client):
    r = client.get("/nope")
    assert r.status_code == 404 and r.json()["detail"] == "없는 주소입니다"
    r = client.get("/jobs/abc/page/xyz.png")
    assert r.status_code == 400 and "요청 값이 올바르지 않습니다" in r.json()["detail"]
    assert r.json()["fields"][0]["field"] == "page_no" and "정수" in r.json()["fields"][0]["problem"]
    r = client.post("/projects", data={})
    assert r.status_code == 400 and "name" in r.json()["detail"] and _has_hangul(r.json()["detail"])
    r = client.delete("/version")
    assert r.status_code == 405 and r.json()["detail"] == "허용되지 않은 방식입니다"
    r = client.get("/jobs/nojob-wpc")
    assert r.status_code == 404 and r.json()["detail"] == main.NO_JOB


def test_route_detail_dict_passes_untouched():
    assert '@app.exception_handler(StarletteHTTPException)' in MAIN_SRC
    i = MAIN_SRC.index("async def _http_error")
    body = MAIN_SRC[i:i + 900]
    assert 'if d == "Not Found"' in body and "headers=exc.headers" in body


def test_upload_checks_disk_room_first(client, monkeypatch):
    import pymupdf
    import shutil as _sh
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 50), "FT-101")
    raw = doc.tobytes()
    doc.close()
    real = _sh.disk_usage
    monkeypatch.setattr(main.shutil, "disk_usage", lambda p: real(p)._replace(free=1024 * 1024))
    r = client.post("/jobs", files=[("pdf", ("t.pdf", raw, "application/pdf"))])
    assert r.status_code == 507 and "디스크" in r.json()["detail"] and "관리자" in r.json()["detail"]


def test_english_404_sentences_are_gone():
    for s in ('"no such job"', '"no such page"', '"no such row"', '"no such revision"',
              '"that export has not been built"', '"unknown reason class'):
        assert f"HTTPException(404, {s}" not in MAIN_SRC and f"HTTPException(400, f{s}" not in MAIN_SRC, s


# ---------------------------------------------------------------- C7 공개 범위
def test_version_is_public_but_small(client):
    v = client.get("/version").json()
    text = json.dumps(v, ensure_ascii=False)
    assert v["product"]["name"] and "ui" in v
    for k in ("base_commit", "branch", '"zip"', '"python"'):
        assert k not in text, k
    if v.get("update"):
        assert set(v["update"]) <= {"name", "rev", "created_at"}


def test_product_file_is_the_single_source():
    p = json.loads((ROOT / "config" / "product.json").read_text(encoding="utf-8"))
    assert p["name"] == "계장 설계 도구" and p["version"]
    assert version.product()["name"] == p["name"]
    assert version.product(ROOT / "nope.json")["name"] == "계장 설계 도구"       # 없으면 기본값


def test_api_docs_are_off_by_default(client):
    if os.environ.get("PID_DEV_DOCS") == "1":
        pytest.skip("개발 문서가 켜져 있다")
    for u in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(u).status_code == 404, u


def test_no_absolute_paths_in_job_and_templates(client):
    job, pdf = _job("wpcpub")
    r = client.get(f"/jobs/{job}")
    assert r.status_code == 200 and "pdf_path" not in r.json() and str(pdf) not in r.text
    for k, v in client.get("/templates").json().items():
        assert v is None or ("/" not in v and "\\" not in v), k
    other = TestClient(main.app, client=("10.0.0.9", 1))
    assert other.get("/voc").json()["voc_dir"] == ""


# ---------------------------------------------------------------- C8 진행 SSE
def test_events_for_missing_job_is_404(client):
    for i in range(5):
        r = client.get(f"/jobs/nojob-sse-{i}/events")
        assert r.status_code == 404 and r.json()["detail"] == main.NO_JOB
    assert not any(k.startswith("nojob-sse-") for k in main._LISTENERS)


def test_events_stream_holds_no_thread():
    job, _ = _job("wpcsse")
    resp = main.events(job)
    it = resp.body_iterator
    assert inspect.isasyncgen(it)                 # 스레드풀을 쓰지 않는다

    async def first_two():
        first = await it.__anext__()
        main._emit(job, {"progress": 0.5, "message": "x", "status": "running"})
        second = await asyncio.wait_for(it.__anext__(), 3)
        await it.aclose()
        return first, second

    first, second = asyncio.run(first_two())
    assert first.startswith("data:") and '"done"' in first
    assert second.startswith("data:") and '"running"' in second
    assert not main._LISTENERS.get(job)           # 끊으면 리스너가 빠진다


# ---------------------------------------------------------------- C9 동기 라우트
def test_blocking_routes_are_plain_def():
    for fn in (main.create_job, main.upload_template, main.patch_row, main.qty_bulk, main.rows_edit,
               main.confirm_axis):
        assert not inspect.iscoroutinefunction(fn), fn.__name__


def test_offline_shell_skips_heavy_folders(client):
    urls = client.get("/offline/shell").json()["urls"]
    assert not any(u.startswith(("/static/valve/", "/static/img/teach/", "/static/img/r-", "/static/books/vendor/"))
                   for u in urls)
    # DCS 화면(/dcs · 절전모드에서 여는 화면)의 필수 셋은 담는다
    for need in ("/static/hmi/hmi.css", "/static/hmi/hmi.js", "/static/hmi/hmi_symbols.js"):
        assert need in urls, need
    dcs = (main.STATIC / "dcs.html").read_text(encoding="utf-8")
    assert all(f"static/hmi/{n}" in dcs for n in ("hmi.css", "hmi.js", "hmi_symbols.js"))
    total = 0
    for u in urls:
        if u.startswith("/static/"):
            f = main.STATIC / u.split("?")[0][len("/static/"):]
            total += f.stat().st_size if f.is_file() else 0
    assert len(urls) <= 55 and total <= 3 * 1024 * 1024, (len(urls), total)


# ---------------------------------------------------------------- C10 설명서 · 머리말
def test_help_manual_page(client):
    r = client.get("/help/manual")
    assert r.status_code == 200 and "<h1" in r.text and "사용 설명서" in r.text
    assert client.head("/help/manual").status_code == 200        # 셸 · 다른 도구가 HEAD 로 물어도 405 가 아니다
    assert "원문: user_manual.md" in r.text                       # 설명서는 config/ (운영 업데이트가 싣는 곳) 에서


def test_help_manual_without_the_file_never_shows_the_readme(monkeypatch, tmp_path):
    monkeypatch.setattr(main.paths, "resource", lambda *parts: tmp_path.joinpath(*parts))
    (tmp_path / "README.md").write_text("# 옛 개발 기록 hotfix", encoding="utf-8")
    md, src = main._manual_text()
    assert src == "" and "설명서 파일이 없습니다" in md and "hotfix" not in md
    assert "<script>alert" not in main._md_to_html("<script>alert(1)</script>")
    h = main._md_to_html("# 시작하기\n\n- 하나\n- 둘\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n`code` **굵게**")
    assert '<h1 id="시작하기">' in h and "<ul><li>하나</li><li>둘</li></ul>" in h and "<td>1</td>" in h
    assert "<code>code</code>" in h and "<strong>굵게</strong>" in h


def test_security_and_cache_headers(client):
    r = client.get("/version")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "same-origin"
    tagged = client.get("/static/app.js?v=abc")
    assert "immutable" in tagged.headers["cache-control"]
    assert tagged.headers["content-type"].startswith("text/javascript")       # nosniff 와 함께라 형식이 맞아야 한다
    assert client.get("/static/styles.css").headers["cache-control"] == "no-cache"
    assert "frame-ancestors" not in json.dumps(dict(client.get("/").headers))   # 대시보드 iframe


def test_index_goes_through_page_stamp(client):
    r = client.get("/")
    assert r.status_code == 200 and "/static/app.js?v=" in r.text and r.headers["cache-control"] == "no-store"


# ---------------------------------------------------------------- C11 목록 메모
def test_rows_memo_limits():
    assert main._ROWS_BODY_MAX == 12 and main._ROWS_BODY_BYTES == 200 * 1024 * 1024
    assert db._ROWS_MEMO_MAX == 8


def test_rows_body_evicts_by_bytes(monkeypatch):
    monkeypatch.setattr(main, "_ROWS_BODY_BYTES", 1)
    saved = dict(main._ROWS_BODY)
    try:
        main._ROWS_BODY.clear()
        for j in ("wpcm1", "wpcm2"):
            _job(j)
            main._rows_body_cached(j, "ALL", True)
        assert len(main._ROWS_BODY) == 1          # 합계가 넘으면 오래된 것부터 뺀다 (마지막 하나는 둔다)
    finally:
        main._ROWS_BODY.clear()
        main._ROWS_BODY.update(saved)


# ---------------------------------------------------------------- 숫자 환경변수 · 루프백
def test_non_numeric_env_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("PID_BACKUP_EVERY_S", "an hour")
    assert main._env_num("PID_BACKUP_EVERY_S", 3600) == 3600
    monkeypatch.setenv("PID_BACKUP_EVERY_S", "-5")
    assert main._env_num("PID_BACKUP_EVERY_S", 3600) == 3600
    monkeypatch.setenv("PID_BACKUP_EVERY_S", "120")
    assert main._env_num("PID_BACKUP_EVERY_S", 3600) == 120
    from app.logic import api
    monkeypatch.setenv("LOGIC_MAX_UPLOAD_MB", "300MB")
    assert api._upload_mb() == 300
    monkeypatch.setenv("LOGIC_MAX_UPLOAD_MB", "450")
    assert api._upload_mb() == 450


def test_ipv4_mapped_loopback_is_the_server_pc():
    from types import SimpleNamespace
    from app import books
    req = SimpleNamespace(client=SimpleNamespace(host="::ffff:127.0.0.1"))
    assert main._is_loopback(req) and "::ffff:127.0.0.1" in books._LOOPBACK
    assert not main._is_loopback(SimpleNamespace(client=SimpleNamespace(host="::ffff:10.0.0.5")))
