"""56회차 [G1] — 프로필은 도면이 고르고, 빌린 값은 장부에 남는다.

넷째 프로젝트까지 겪은 범용성의 첫 자리: 모르는 문서가 `PID_PROJECT_CONFIG`
미지정이면 **AL NOUF1 설정으로 조용히** 돌았다 (14회차 [8]).  이제
① 도면번호의 프로젝트 코드로 `config/project_*.yaml` 을 고르고
② 맞는 것이 없으면 "새 프로젝트" 로 선언하되, 지금 실린 프로필에서 빌려 쓴
   잎을 **전부 장부에 적는다** (`result["borrowed"]` · 지문 밖)
③ 되돌리는 곳은 `_own_config` 하나이고 **파일도** 되돌린다
④ 사람이 `PID_PROJECT_CONFIG` 로 못박았으면 자동으로 바꾸지 않는다.
"""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import pipeline                                    # noqa: E402
from app.engine import projectconfig                        # noqa: E402


@pytest.fixture
def unpinned(monkeypatch):
    monkeypatch.delenv("PID_PROJECT_CONFIG", raising=False)
    monkeypatch.delenv("PID_PROFILE_AUTO", raising=False)


def test_the_build_lists_its_profiles_by_code():
    got = {c["code"]: c["path"].name for c in projectconfig.profiles()}
    assert got.get("D00P") == "project_alnouf1.yaml"
    assert got.get("1A46") == "project_sadara.yaml"


def test_a_matching_code_switches_the_profile_and_own_config_puts_it_back(unpinned):
    before = (pipeline.CFG.path, pipeline.CFG.data.get("project", {}).get("code"))
    with pipeline._own_config():
        info = pipeline._select_profile("1A46")
        assert info["switched"] and info["matched"]
        assert pipeline.CFG.path.name == "project_sadara.yaml"
        assert pipeline.CFG.data["project"]["code"] == "1A46"
        # 발주처 몫만 적은 프로필 — 필수 잎은 바탕(AL NOUF1)에서 물려받아 죽지 않는다
        assert pipeline.CFG.get("vendor_marks.glyph_sizes")
        assert pipeline.CFG.states("project.code") and not pipeline.CFG.states("vendor_marks.glyph_sizes")
        assert info["borrowed_from"] == "project_alnouf1.yaml"   # 물려받은 바탕을 적는다
        pipeline.CFG.get("vendor_marks.glyph_sizes")
        led = pipeline._borrowed_ledger(info, {"moved": []})
        assert "vendor_marks.glyph_sizes" in led["keys"]         # 물려받은 것은 빌린 값이다
        assert led["from"] == "project_alnouf1.yaml"
    # 되돌리기 — 파일도, 값도, 적은 잎도
    assert (pipeline.CFG.path, pipeline.CFG.data.get("project", {}).get("code")) == before
    assert pipeline.CFG.states("vendor_marks.glyph_sizes")


def test_an_unknown_code_is_a_new_project_that_borrows_and_says_so(unpinned):
    with pipeline._own_config():
        info = pipeline._select_profile("ZZZZ")
        assert not info["matched"] and not info["switched"]
        assert info["document_code"] == "ZZZZ"
        assert info["borrowed_from"] == pipeline.CFG.path.name   # 지금 실린 것에서 빌린다
        codes = {c["code"] for c in info["candidates"]}
        assert {"D00P", "1A46"} <= codes


def test_no_code_at_all_is_also_a_new_project(unpinned):
    with pipeline._own_config():
        info = pipeline._select_profile("")
        assert not info["matched"] and info["borrowed_from"]


def test_a_pinned_env_profile_is_never_switched(monkeypatch):
    monkeypatch.setenv("PID_PROJECT_CONFIG", str(ROOT / "config" / "project_alnouf1.yaml"))
    monkeypatch.delenv("PID_PROFILE_AUTO", raising=False)
    with pipeline._own_config():
        info = pipeline._select_profile("1A46")
        assert info["env_pinned"] and not info["auto"] and not info["switched"]
        assert pipeline.CFG.path.name == "project_alnouf1.yaml"


def test_auto_can_be_switched_off(monkeypatch):
    monkeypatch.delenv("PID_PROJECT_CONFIG", raising=False)
    monkeypatch.setenv("PID_PROFILE_AUTO", "0")
    with pipeline._own_config():
        info = pipeline._select_profile("1A46")
        assert not info["auto"] and not info["switched"]


def test_the_ledger_records_reads_and_drops_what_the_sheet_replaced(unpinned):
    with pipeline._own_config():
        info = pipeline._select_profile("ZZZZ")
        pipeline.CFG.get("sheet.width_pt")
        pipeline.CFG.get("formats.drawing_no")
        pipeline.CFG.lookup("unit_multiplier_fallback", "00")
        led = pipeline._borrowed_ledger(
            info, {"moved": [{"key": "sheet.width_pt", "was": 1, "now": 2}]})
    assert "sheet.width_pt" in led["replaced_by_sheet"]
    assert "sheet.width_pt" not in led["keys"]             # 도면이 대신 답한 것은 뺀다
    assert "formats.drawing_no" in led["keys"]
    assert led["count"] == len(led["keys"]) and led["read"] >= 3
    assert led["by_section"].get("formats") == 1
    # 밖에서는 장부가 꺼져 있다 — 다음 분석에 새지 않는다
    assert pipeline.CFG.recording is False


def test_the_own_profile_borrows_nothing(unpinned):
    with pipeline._own_config():
        info = pipeline._select_profile("D00P")
        pipeline.CFG.get("sheet.width_pt")
        led = pipeline._borrowed_ledger(info, {"moved": []})
    assert led["matched"] and led["keys"] == [] and led["read"] >= 1
    assert info["borrowed_from"] == ""


def test_a_code_default_is_counted_apart_from_a_borrowed_value(unpinned):
    with pipeline._own_config():
        info = pipeline._select_profile("ZZZZ")
        pipeline.CFG.get_or("no.such.leaf", 1.0)             # 어느 프로필에도 없다
        led = pipeline._borrowed_ledger(info, {"moved": []})
    assert "no.such.leaf" in led["code_defaults"] and "no.such.leaf" not in led["keys"]


def test_the_facts_are_stored_and_the_dxf_branch_is_guarded_too():
    db_src = (ROOT / "app" / "db.py").read_text(encoding="utf-8")
    assert '"profile", "borrowed"' in db_src
    src = inspect.getsource(pipeline.analyse)
    i = src.index("dxf_pipeline.analyse(")
    assert "with _own_config():" in src[:i]                # DXF 도 같은 되돌리기 안
    guard = inspect.getsource(pipeline._own_config)
    assert "CFG.path, CFG.stated = path0, stated0" in guard and "CFG.recording = False" in guard
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '"profile_line": profile_line' in main_src       # 문장은 화면 쪽이 만든다
