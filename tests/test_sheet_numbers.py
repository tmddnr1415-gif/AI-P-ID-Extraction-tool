"""장 도면번호를 사람이 적는 자리 — **도면을 못 이긴다** (45회차).

이 시험이 지키는 것 다섯:

    ① 작성자 없이 저장되지 않는다 (팀이 공유하는 값이다 · 13회차 자기신고)
    ② 끄면 없던 때와 **정확히** 같아진다 (읽는 곳이 `table()` 하나다)
    ③ **읽는 순서**: 그 장의 타이틀블록 → 사람 → 그대로 빠짐.
       도면에서 읽힌 장은 사람 값이 **무시된다** — 이것이 §9 의 핵심이고,
       AL NOUF1·SADARA·TC2 가 이 경로에 닿을 수 없는 이유다(빈 칸 0개)
    ④ 파이프라인은 파일을 읽지 않는다 (15회차 `legend_profile` 과 같은 모양)
    ⑤ 사람이 적은 값으로 선 행은 **그렇게 말한다** (`DRAWING_NO_BY_USER`)
"""
from __future__ import annotations

import inspect
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import sheet_numbers as sn  # noqa: E402
from app import pipeline  # noqa: E402


# --------------------------------------------------------------------------
# ① 작성자
# --------------------------------------------------------------------------
def test_an_author_is_required(tmp_path):
    with pytest.raises(ValueError):
        sn.set_sheet(tmp_path, "P", page=11, drawing_no="A-B-C-0001", author="")
    assert sn.table(tmp_path, "P") == {}


def test_an_empty_number_is_refused(tmp_path):
    with pytest.raises(ValueError):
        sn.set_sheet(tmp_path, "P", page=11, drawing_no="   ", author="sc.y")


def test_a_project_is_required(tmp_path):
    with pytest.raises(ValueError):
        sn.set_sheet(tmp_path, "", page=11, drawing_no="X", author="sc.y")


def test_it_stores_who_and_when(tmp_path):
    rec = sn.set_sheet(tmp_path, "UAD", page=16,
                       drawing_no="1A5J-00PGB10-M05-0001", author="sc.y",
                       note="타이틀블록이 획")
    assert rec["author"] == "sc.y" and rec["set_at"]
    assert sn.table(tmp_path, "UAD") == {16: "1A5J-00PGB10-M05-0001"}


# --------------------------------------------------------------------------
# ② 끄기·되돌리기
# --------------------------------------------------------------------------
def test_clearing_returns_to_the_state_before(tmp_path):
    sn.set_sheet(tmp_path, "UAD", page=16, drawing_no="X-Y-Z-0001", author="a")
    assert sn.clear_sheet(tmp_path, "UAD", 16) is True
    assert sn.table(tmp_path, "UAD") == {}


def test_disabling_is_exactly_the_same_as_never_having_set_it(tmp_path):
    sn.set_sheet(tmp_path, "UAD", page=16, drawing_no="X-Y-Z-0001", author="a")
    sn.set_enabled(tmp_path, "UAD", False)
    assert sn.table(tmp_path, "UAD") == {}
    sn.set_enabled(tmp_path, "UAD", True)
    assert sn.table(tmp_path, "UAD") == {16: "X-Y-Z-0001"}


def test_an_unbound_analysis_reads_nothing(tmp_path):
    assert sn.table(tmp_path, "") == {}


# --------------------------------------------------------------------------
# ③ 도면이 이긴다 — 파이프라인이 **읽힌 칸을 덮지 않는다**
# --------------------------------------------------------------------------
def test_the_drawing_wins_over_the_person():
    """`_analyse` 의 적용 루프는 `drawing_no` 가 비었을 때만 채운다."""
    src = inspect.getsource(pipeline._analyse)
    i = src.index("user_sheets = {")
    body = src[i: i + 1200]
    assert 'if row.get("drawing_no") or page_no not in user_sheets' in body
    assert "continue" in body


def test_the_form_check_comes_first():
    """21회차 `TitleBlockUnreadable` 이 **앞**에 선다 — 사람이 적은 한 줄이
    "이 양식은 이 문서의 것이 아니다" 를 덮으면 안 된다."""
    src = inspect.getsource(pipeline._analyse)
    assert src.index("raise TitleBlockUnreadable") < src.index("user_sheets = {")


# --------------------------------------------------------------------------
# ④ 파이프라인은 파일을 읽지 않는다
# --------------------------------------------------------------------------
def test_the_pipeline_never_opens_the_file():
    src = inspect.getsource(pipeline)
    assert "sheet_numbers.load" not in src
    assert "sheet_numbers.table" not in src
    assert "sheet_numbers" in inspect.signature(pipeline.analyse).parameters


def test_the_harness_passes_nothing():
    """회귀 하네스는 사람 값을 넘기지 않는다 — 불변이 구조적으로 보장된다."""
    src = (ROOT / "spike" / "regression_3p.py").read_text()
    assert "sheet" not in src.split("def run_one")[1].split("def score")[0].lower()


# --------------------------------------------------------------------------
# ⑤ 행이 그렇게 말한다
# --------------------------------------------------------------------------
def test_the_row_says_the_number_came_from_a_person():
    src = inspect.getsource(pipeline._analyse)
    assert "_USER_SHEET_CODE" in src
    assert pipeline._USER_SHEET_CODE == sn.REVIEW_CODE


def test_the_reason_is_written_in_one_place():
    """행을 만드는 두 자리(`_field_rows`·`_valve_rows`)가 아니라 한 곳이다."""
    assert "_USER_SHEET_CODE" not in inspect.getsource(pipeline._field_rows)
    assert "_USER_SHEET_CODE" not in inspect.getsource(pipeline._valve_rows)


# --------------------------------------------------------------------------
# 세 문서는 이 경로에 닿을 수 없다 — 빈 칸이 0개다 (실측)
# --------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["AL_NOUF1", "SADARA", "TC2"])
def test_the_three_documents_have_no_empty_drawing_number(name):
    src = ROOT / "out" / "regression_3p" / f"{name}.json"
    if not src.exists():
        pytest.skip("결과 json 이 없는 기계")
    pages = json.loads(src.read_text())["result"]["pages"]
    assert [p["page_no"] for p in pages if not p["drawing_no"]] == []
