"""hotfix132 (D7) — 분석 실패 사유의 파이썬 예외 원문을 사람 말로 · 올리는 파일 크기 상한(413) · 디스크 여유 사전 점검(507)."""
from __future__ import annotations

import io
import json
import shutil
from collections import namedtuple

import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import api, store


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _failed(err):
    job, d = store.new_job("toy.pdf")
    st = store.read_status(d)
    st.update({"state": "failed", "error": err, "trace": "Traceback ..."})
    store.write_status(d, st)
    return job, d


def test_python_exception_text_is_hidden(client):
    job, d = _failed("분석 중 오류: KeyError: 'rows'")
    r = client.get(f"/logic/api/jobs/{job}").json()
    assert "KeyError" not in r["error"] and job in r["error"] and "다시 분석" in r["error"]
    assert "trace" not in r
    lst = [j for j in client.get("/logic/api/jobs").json()["jobs"] if j["id"] == job][0]
    assert "KeyError" not in lst["error"] and job in lst["error"]
    assert "KeyError" in json.loads((d / "status.json").read_text(encoding="utf-8"))["error"]   # 원문은 서버에 남는다


def test_disk_full_reason(client):
    job, d = _failed("분석 중 오류: [Errno 28] No space left on device")
    assert "디스크" in client.get(f"/logic/api/jobs/{job}").json()["error"]


def test_korean_not_logic_reason_is_kept(client):
    msg = "Logic 표를 한 장도 찾지 못했습니다 — Logic Diagram PDF 인지 확인하세요."
    job, d = _failed(msg)
    assert client.get(f"/logic/api/jobs/{job}").json()["error"] == msg


def _pdf_bytes(pad=0):
    doc = pymupdf.open()
    doc.new_page()
    b = doc.tobytes()
    return b + b"\n%" + b"x" * pad if pad else b


def test_upload_over_limit_is_413_and_folder_removed(client, monkeypatch):
    monkeypatch.setattr(api, "MAX_UPLOAD", 2000)
    monkeypatch.setattr(api, "MAX_UPLOAD_MB", 0)
    before = {p.name for p in store.root().iterdir()}
    r = client.post("/logic/api/jobs", files={"logic": ("big.pdf", io.BytesIO(_pdf_bytes(5000)), "application/pdf")})
    assert r.status_code == 413 and "너무 큽니다" in r.json()["detail"]
    assert {p.name for p in store.root().iterdir()} == before


def test_upload_under_limit_ok(client, monkeypatch):
    monkeypatch.setattr(api, "_start", lambda d: None)
    r = client.post("/logic/api/jobs", files={"logic": ("ok.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")})
    assert r.status_code == 200 and (store.root() / r.json()["id"] / "source.pdf").exists()


def test_no_disk_space_is_507(client, monkeypatch):
    U = namedtuple("usage", "total used free")
    monkeypatch.setattr(api.shutil, "disk_usage", lambda p: U(1, 1, 10))
    before = {p.name for p in store.root().iterdir()}
    r = client.post("/logic/api/jobs", files={"logic": ("x.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")})
    assert r.status_code == 507 and "디스크" in r.json()["detail"]
    assert {p.name for p in store.root().iterdir()} == before


def test_disk_usage_failure_does_not_block(client, monkeypatch):
    def boom(p):
        raise OSError("no")
    monkeypatch.setattr(api.shutil, "disk_usage", boom)
    monkeypatch.setattr(api, "_start", lambda d: None)
    r = client.post("/logic/api/jobs", files={"logic": ("x.pdf", io.BytesIO(_pdf_bytes()), "application/pdf")})
    assert r.status_code == 200
