"""2026-11-19 — [심볼] 판을 여는 준비(GET /jobs/{id}/teach · 58장에서 11초)를 분석 + 프로그램 판 단위로 기억한다.

메모리 기억은 서버를 다시 켜면 사라졌다 → 파일에도 둔다.  가르친 값 · PDF · 프로그램 판이 바뀌면 다시 센다.
"""
import time

import pytest

from app import main


@pytest.fixture()
def env(tmp_path, monkeypatch):
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    calls = []

    def slow(fn, args, timeout=0):
        calls.append(args)
        time.sleep(1.2)                                   # 무거운 일 흉내
        return {"needs": ["legend"] if not (args[1] or {}).get("legend") else [], "suggest": {"page": len(calls)}}
    monkeypatch.setattr(main.page_warm, "call", slow)
    monkeypatch.setattr(main, "PAGE_CACHE", tmp_path / "page_cache")
    monkeypatch.setattr(main, "_NEEDS_CACHE", {})
    job = {"id": "job0000000aa", "pdf_path": str(pdf), "message": ""}
    return job, calls


def test_second_call_is_fast(env):
    job, calls = env
    a = main._needs_and_suggest(job, {})
    t = time.monotonic()
    b = main._needs_and_suggest(job, {})
    assert time.monotonic() - t < 1.0 and a == b and len(calls) == 1


def test_survives_restart(env, monkeypatch):
    job, calls = env
    a = main._needs_and_suggest(job, {})
    monkeypatch.setattr(main, "_NEEDS_CACHE", {})         # 서버를 다시 켠 것처럼
    t = time.monotonic()
    b = main._needs_and_suggest(job, {})
    assert time.monotonic() - t < 1.0 and a == b and len(calls) == 1
    assert main._needs_file(job["id"]).is_file()


def test_changed_input_recounts(env, monkeypatch):
    job, calls = env
    a = main._needs_and_suggest(job, {})
    b = main._needs_and_suggest(job, {"legend": {"SYMBOL": {"page_no": 2, "rect": [0, 0, 1, 1]}}})   # 사람이 범례를 가르침
    assert len(calls) == 2 and a["needs"] != b["needs"]
    monkeypatch.setattr(main, "_NEEDS_CACHE", {})
    monkeypatch.setattr(main, "_needs_engine_tag", lambda: "다음 업데이트")                             # 프로그램이 바뀜
    c = main._needs_and_suggest(job, {})
    assert len(calls) == 3 and c["suggest"] == {"page": 3}


def test_new_analysis_does_not_share(env):
    job, calls = env
    main._needs_and_suggest(job, {})
    main._needs_and_suggest(dict(job, id="job0000000bb"), {})                                         # 재분석 = 새 분석 id
    assert len(calls) == 2


def test_broken_cache_file_is_ignored(env, monkeypatch):
    job, calls = env
    main._needs_and_suggest(job, {})
    main._needs_file(job["id"]).write_text("{깨진", encoding="utf-8")
    monkeypatch.setattr(main, "_NEEDS_CACHE", {})
    main._needs_and_suggest(job, {})
    assert len(calls) == 2
