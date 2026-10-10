"""마크업 제안은 **같은 답을 더 빠르게** 낸다 (46회차 [D]).

지키는 것 넷:
    ① 값이 바뀌지 않는다 — 같은 자리 두 번은 글자 그대로 같은 dict
    ② `only=` 는 제안 전용이다 — 분석 경로가 쓰면 `_scope_by_project`(다수결)가
       무력해져 44회차 [C] 가 조용히 깨진다
    ③ 캐시는 **한 장만** 든다 (33회차 `_INK_LAST` 와 같은 규율)
    ④ 제안 뒤 잉크 인덱스를 놓는다 — 서버가 마지막 장을 계속 들지 않게
"""
from __future__ import annotations

import inspect
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import pipeline  # noqa: E402
from app.engine import pidcache  # noqa: E402

PDF = ROOT / "data" / "pid_total.pdf"


def test_only_is_not_used_by_the_analysis():
    src = inspect.getsource(pipeline._analyse)
    assert "load_pages" in src
    assert "only=" not in src


def test_load_pages_takes_only():
    assert "only" in inspect.signature(pidcache.load_pages).parameters


def test_the_cache_holds_one_page():
    src = inspect.getsource(pipeline._propose_page)
    # 한 칸짜리 dict — 새 장을 넣을 때 앞 장이 밀려난다
    assert '_PROPOSE_CACHE["entry"]' in src
    assert "append" not in src


def test_the_proposal_releases_the_ink_index():
    assert "release_ink" in inspect.getsource(pipeline._ProposeCleanup)


@pytest.mark.slow
def test_the_same_rectangle_gives_the_same_answer():
    if not PDF.exists():
        pytest.skip("도면이 없는 기계")
    a = pipeline.propose_at(PDF, 6, (330, 250, 360, 275))
    b = pipeline.propose_at(PDF, 6, (330, 250, 360, 275))
    assert a == b
    # 다른 장을 거쳐 캐시가 밀려난 뒤에도 같아야 한다
    pipeline.propose_at(PDF, 7, (100, 100, 140, 140))
    assert pipeline.propose_at(PDF, 6, (330, 250, 360, 275)) == a
