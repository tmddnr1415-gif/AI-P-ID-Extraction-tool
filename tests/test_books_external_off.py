"""도서검토 — 회사판 기본값: 외부 번역(Claude · api.anthropic.com) 은 화면에서 숨고 서버 경로도 막힌다 (CLAUDE.md §3)."""
from __future__ import annotations

import shutil
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import books, books_api, paths
from app.main import app

ME = {"X-Author": quote("홍길동")}


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("BOOKS_EXTERNAL_TRANSLATE", raising=False)
    shutil.rmtree(paths.data_dir() / "books", ignore_errors=True)
    with TestClient(app) as c:
        yield c
    shutil.rmtree(paths.data_dir() / "books", ignore_errors=True)


def _as_server_pc(monkeypatch):
    monkeypatch.setattr(books, "_LOOPBACK", books._LOOPBACK | {"testclient"})


def test_default_is_off_and_blocked(client, monkeypatch):
    assert books_api.external_allowed() is False
    info = client.get("/api/books/info").json()
    assert info["translate"] == {"claude": False, "model": "", "external": False}
    _as_server_pc(monkeypatch)                                         # 운영자(서버 PC)도
    info = client.get("/api/books/info").json()
    assert "translateCfg" not in info                                  # 설정 칸을 그리지 않는다
    r = client.put("/api/books/translate-config", json={"apiKey": "sk-ant-X", "enabled": True})
    assert r.status_code == 403 and "회사판" in r.json()["error"]
    assert not (paths.data_dir() / "books" / "secret.json").exists()   # 키가 저장되지 않는다
    r = client.post("/api/books/translate", json={"text": "pressure transmitter"}, headers=ME)
    assert r.status_code == 403 and "외부 번역" in r.json()["error"]


def test_no_name_still_401(client):
    assert client.post("/api/books/translate", json={"text": "x"}).status_code == 401


def test_translate_never_calls_out_when_off(monkeypatch):
    monkeypatch.delenv("BOOKS_EXTERNAL_TRANSLATE", raising=False)
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network")))
    with pytest.raises(Exception) as e:
        books_api.translate("pressure transmitter", "en", "", "t")
    assert "회사판" in str(e.value) or getattr(e.value, "code", None) == 403


def test_page_hides_claude_unless_allowed(client):
    page = client.get("/books/?embed=1").text
    assert "const trExternal = () => !!(SRV.on && SRV.info?.translate?.external);" in page
    assert "trEngines().map" in page and "회사판에서는 쓰지 않음" in page


def test_opened_only_by_the_env_flag(client, monkeypatch):
    monkeypatch.setenv("BOOKS_EXTERNAL_TRANSLATE", "1")
    _as_server_pc(monkeypatch)
    info = client.get("/api/books/info").json()
    assert info["translate"]["external"] is True and "translateCfg" in info
    assert client.put("/api/books/translate-config", json={"enabled": False}).status_code == 200
