"""hotfix115 — 계장도서검토(도서 검토)가 P&ID · LOGIC · 판넬과 같은 서버(8000)의 /books 로 돈다."""
from __future__ import annotations

import gzip
import json
import shutil
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import books, books_api, paths
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
ME = {"X-Author": quote("홍길동")}


@pytest.fixture()
def client(monkeypatch):
    shutil.rmtree(paths.data_dir() / "books", ignore_errors=True)
    with TestClient(app) as c:
        yield c
    shutil.rmtree(paths.data_dir() / "books", ignore_errors=True)


def _as_server_pc(monkeypatch):
    monkeypatch.setattr(books, "_LOOPBACK", books._LOOPBACK | {"testclient"})


def test_page_and_static_files(client):
    r = client.get("/books?embed=1&user=홍길동", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/books/?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"
    page = client.get("/books/?embed=1")
    assert page.status_code == 200 and "/api/books/" in page.text and "X-Author" in page.text
    for f in ("kb.js", "vendor/pdf.min.js", "vendor/pdf.worker.min.js"):
        assert client.get(f"/books/{f}").status_code == 200
    assert client.get("/books/../app/main.py").status_code == 404
    assert client.get("/books/secret.txt").status_code == 404


def test_api_module_is_the_dashboard_file_unchanged():
    """API 코드는 고치지 않고 들여온다 — 대시보드 쪽 서명 그대로."""
    src = (ROOT / "app" / "books_api.py").read_text(encoding="utf-8")
    assert "def handle(h, m, seg, q):" in src and "def setup(P, LOCK, ApiError, read_json, write_json):" in src


def test_info_and_permissions(client, tmp_path):
    info = client.get("/api/books/info").json()
    assert info["enabled"] is False and info["canManage"] is False
    lib = tmp_path / "계장도서"
    lib.mkdir()
    r = client.put("/api/books/root", json={"root": str(lib)}, headers=ME)
    assert r.status_code == 403 and "운영자" in r.json()["error"]          # 부서원은 폴더를 못 정한다
    assert client.post("/api/books/translate", json={"text": "x"}).status_code == 401   # 이름 없음


def test_library_round_trip(client, monkeypatch, tmp_path):
    _as_server_pc(monkeypatch)
    lib = tmp_path / "계장도서"
    (lib / "sub").mkdir(parents=True)
    (lib / "sub" / "전송기 교재.pdf").write_bytes(b"%PDF-1.4 test")
    (lib / "note.exe").write_bytes(b"x")
    r = client.put("/api/books/root", json={"root": str(lib)})
    assert r.status_code == 200 and r.json()["folder"] == "계장도서"
    files = client.get("/api/books/files").json()["files"]
    assert [f["rel"] for f in files] == ["계장도서/sub/전송기 교재.pdf"]
    got = client.get("/api/books/file", params={"rel": "계장도서/sub/전송기 교재.pdf"})
    assert got.status_code == 200 and got.content == b"%PDF-1.4 test" and got.headers["content-type"] == "application/pdf"
    assert client.get("/api/books/file", params={"rel": "계장도서/../x.pdf"}).status_code == 400
    assert client.get("/api/books/file", params={"rel": "계장도서/note.exe"}).status_code == 400
    rec = {"sig": "s1", "rel": "계장도서/sub/전송기 교재.pdf", "pages": [{"p": 1, "t": "4-20 mA"}], "v": 1}
    up = client.put("/api/books/book", content=gzip.compress(json.dumps(rec).encode()), headers={"Content-Type": "application/gzip"})
    bid = up.json()["id"]
    assert up.status_code == 200 and bid == books_api.book_id("s1")
    man = client.put("/api/books/manifest", json={"books": [{"sig": "s1", "rel": rec["rel"], "nPages": 1}], "final": True})
    assert man.json()["count"] == 1
    assert client.get("/api/books/manifest").json()["books"][0]["id"] == bid
    b = client.get(f"/api/books/book/{bid}")
    assert b.status_code == 200 and b.json()["pages"][0]["t"] == "4-20 mA"     # gzip 그대로 보내고 받는 쪽이 푼다
    assert (paths.data_dir() / "books" / "index" / f"{bid}.json.gz").exists()
    assert client.get("/api/books/book/zz").status_code == 400
