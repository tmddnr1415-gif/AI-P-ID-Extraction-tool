"""27회차 — 그 장 NOTES 가 말하는 "유닛 몇 개" 를 수량에 쓴다 (§9 ②).

현장 보고: *"Note 에 `THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS
APPLICABLE TO UNIT 3-2 … UNIT 6-2` 라는 말은 해당 page 가 동일한 유닛 8개라는
말이다 … TC2 에 대해 현재 프로그램은 노트를 식별하지 못하고 있다."*

세 문서 실측 문형 (전부 같은 뜻):

    AL NOUF1  THIS P&ID IS FOR GROUP #10, CONFIGURATION IS IDENTICAL FOR GROUP #20.
    AL NOUF1  THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22.
    TC2       THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO
              UNIT 3-2, UNIT 4-1, … UNIT 6-2.
    TC2       … SHALL BE IDENTICAL TO UNIT 3-1 AS SHOWN IN THIS P&ID.
"""
import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import pidcache          # noqa: E402
import projectconfig     # noqa: E402


# --------------------------------------------------------------------------
# 세는 규칙 — 낱말 뒤의 꼬리까지
# --------------------------------------------------------------------------
@pytest.mark.parametrize("text,want", [
    ("THIS P&ID IS FOR GROUP #10, CONFIGURATION IS IDENTICAL FOR GROUP #20.",
     ["10", "20"]),
    # ★ 꼬리를 버리면 4를 2로 센다 (옛 스파이크 주석이 경고해 둔 자리)
    ("THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22.",
     ["11", "12", "21", "22"]),
    ("THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO UNIT 3-2,"
     " UNIT 4-1, UNIT 4-2, UNIT 5-1, UNIT 5-2, UNIT 6-1, UNIT 6-2.",
     ["3-1", "3-2", "4-1", "4-2", "5-1", "5-2", "6-1", "6-2"]),
    ("THIS P&ID IS APPLICABLE FOR UNIT 3 & 4, SAME WILL BE APPLICABLE FOR UNIT 5& 6.",
     ["3", "4", "5", "6"]),
    # 낱말 없이 이어지는 목록 — 뒤 여섯이 `UNIT` 없이 나온다 (TC2 p35)
    ("5. THE P & ID IS TYPICAL FOR UNIT 3-1 & 3-2, SIMILAR P & ID IS APPLICABLE"
     " FOR 4-1 & 4-2, 5-1 & 5-2 AND 6-1 & 6-2.",
     ["3-1", "3-2", "4-1", "4-2", "5-1", "5-2", "6-1", "6-2"]),
    # `UNITS NO.3-1` 의 `NO.` · 앞 둘이 낱말 없이 나온다 (TC2 p38·p39)
    ("2. THIS P&ID IS COMMON FOR UNITS NO.3-1 & 3-2. AN IDENTICAL SYSTEM SHALL BE"
     " DUPLICATED FOR UNIT 4-1 & 4-2, 5-1 & 5-2, 6-1 & 6-2, ONE UNIT BASED ON 1X1"
     " CONFIGURATION",
     ["3-1", "3-2", "4-1", "4-2", "5-1", "5-2", "6-1", "6-2"]),
    ("10. THIS P&ID IS APPLICABLE FOR UNIT 3-1 ONLY, SAME WILL BE APPLICABLE FOR"
     " UNIT 3-2, 4-1, 4-2, 5-1, 5-2, 6-1 & 6-2.",
     ["3-1", "3-2", "4-1", "4-2", "5-1", "5-2", "6-1", "6-2"]),
    # 도면번호·범례 참조·치수·날짜에서는 아무 것도 세지 않는다
    ("1. REFER TO SYMBOL & LEGEND DWG.NO. 00GEN00-M05-0002~0005.", []),
    ("2. THIS P&ID IS BASED ON CONFIGURATION WITH ONE (1) COMBINED CYCLE POWER"
     " GENERATION UNIT WHICH CONSISTING OF ONE (1) GTG", []),
    ("REV 2026-08-21 ISSUED FOR REVIEW, 20 DIAMETERS OF STRAIGHT PIPE", []),
])
def test_the_note_counts_every_unit_it_lists(text, want):
    got = list(dict.fromkeys(projectconfig._unit_tokens(text)))
    assert got == want


# --------------------------------------------------------------------------
# 도면에서 읽기 — 두 줄로 접힌 노트 · 덧인쇄된 노트
# --------------------------------------------------------------------------
NOTE = ("1. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO",
        "UNIT 3-2, UNIT 4-1, UNIT 4-2, UNIT 5-1, UNIT 5-2, UNIT 6-1, UNIT 6-2.")
AREA = (900.0, 20.0, 1190.0, 800.0)


def _page(tmp_path, twice=False):
    doc = pymupdf.open()
    pg = doc.new_page(width=1191, height=842)
    for i, line in enumerate(NOTE):
        for _ in range(2 if twice else 1):     # 덧인쇄 (TC2 p10·p12)
            pg.insert_text(pymupdf.Point(910, 60 + i * 9.3), line, fontsize=5)
    path = tmp_path / ("twice.pdf" if twice else "once.pdf")
    doc.save(path)
    doc.close()
    _d, pages = pidcache.load_pages(path)
    return pages[0]


def test_a_note_wrapped_over_two_lines_is_read_whole(tmp_path):
    got = projectconfig.note_unit_span(_page(tmp_path), AREA, 1190.0)
    assert (got.count, got.units[0], got.units[-1]) == (8, "3-1", "6-2")


def test_a_note_printed_twice_is_still_eight(tmp_path):
    """TC2 p10·p12 는 NOTES 를 두 번 인쇄한다 — 같은 자리의 같은 낱말은 하나다."""
    got = projectconfig.note_unit_span(_page(tmp_path, twice=True), AREA, 1190.0)
    assert got.count == 8


# --------------------------------------------------------------------------
# 쓰는 자리 — 범례가 답하면 노트를 쓰지 않는다
# --------------------------------------------------------------------------
def test_the_legend_wins_when_it_answers():
    """★ AL NOUF1 이 한 칸도 안 움직이는 이유 (지문 `fb85b039`)."""
    from app import pipeline
    note = (8, ["3-1"], "…")
    # 범례가 답한 경우 — 그대로 둔다
    assert pipeline._note_factor(2, False, False, note) == (2, False, False, False)
    # 범례에 없는 코드 — 노트가 답한다
    assert pipeline._note_factor(projectconfig.UNDEFINED, True, False, note) \
        == (8, False, False, True)
    # 남의 설정에서 빌려온 값 — 노트가 이긴다 (§9 ①)
    assert pipeline._note_factor(1, False, True, note) == (8, False, False, True)
    # 노트가 없으면 아무 것도 달라지지 않는다
    assert pipeline._note_factor(1, False, True, None) == (1, False, True, False)


# --------------------------------------------------------------------------
# 어휘는 config 에 있다 — 다른 프로젝트의 P&ID 도 그 도면의 낱말로 읽는다
# --------------------------------------------------------------------------
class _Cfg:
    """`ProjectConfig` 처럼 `.data` 만 있는 최소 대역."""

    def __init__(self, **note):
        self.data = {"qty_note": note} if note else {}


def test_the_vocabulary_comes_from_config_not_from_code():
    """넷째 프로젝트가 유닛을 `BLOCK` 이라 부르면 **코드를 고치지 않는다**.

    기본값에는 실제로 본 낱말만 있고(§2.1 ③), 늘리는 자리는 `qty_note` 다.
    """
    text = ("THIS P&ID IS FOR BLOCK 1, AND THE ARRANGEMENT IS EQUIVALENT FOR"
            " BLOCK 2, BLOCK 3.")
    same, head, _rng = projectconfig.note_vocabulary(None)
    assert not same.search(text)                      # 기본 어휘로는 안 걸린다
    assert projectconfig._unit_tokens(text, head) == []

    cfg = _Cfg(same_words=["EQUIVALENT"], unit_words=["BLOCK"])
    same, head, _rng = projectconfig.note_vocabulary(cfg)
    assert same.search(text)
    assert list(dict.fromkeys(projectconfig._unit_tokens(text, head))) \
        == ["1", "2", "3"]


def test_the_shipped_config_lists_the_words_the_three_documents_print():
    """실제 프로필이 그 낱말을 담고 있는가 — 기본값과 어긋나면 조용히 갈린다."""
    import yaml
    data = yaml.safe_load((ROOT / "config" / "project_alnouf1.yaml").read_text())
    block = data["qty_note"]
    assert set(block["same_words"]) >= {"IDENTICAL", "SIMILAR"}
    assert set(block["unit_words"]) >= {"GROUP", "UNIT"}
    assert set(block["range_words"]) >= {"THRU", "THROUGH"}


def test_a_word_only_the_config_adds_does_not_leak_into_the_default():
    """config 를 준 호출이 **다음 호출의 기본값**을 바꾸지 않는다 (캐시 키)."""
    projectconfig.note_vocabulary(_Cfg(unit_words=["BLOCK"]))
    _same, head, _rng = projectconfig.note_vocabulary(None)
    assert projectconfig._unit_tokens("FOR BLOCK 1, BLOCK 2", head) == []


# --------------------------------------------------------------------------
# 범위 표기 — 세지 않고 검토로 올린다
# --------------------------------------------------------------------------
RANGE_NOTE = ("1. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS",
              "APPLICABLE TO UNIT 3-2 THRU UNIT 6-2.")


def _range_page(tmp_path):
    doc = pymupdf.open()
    pg = doc.new_page(width=1191, height=842)
    for i, line in enumerate(RANGE_NOTE):
        pg.insert_text(pymupdf.Point(910, 60 + i * 9.3), line, fontsize=5)
    path = tmp_path / "range.pdf"
    doc.save(path)
    doc.close()
    _d, pages = pidcache.load_pages(path)
    return pages[0]


def test_a_range_is_not_counted_it_is_raised(tmp_path):
    """★ `3-2 THRU 6-2` 의 두 끝을 세면 **2** 가 나온다 — 틀린 수가 맞는 얼굴을 한다.

    그 도면은 사이에 무엇이 있는지 말하지 않았으므로 세지 않는다 (§9 ④).
    """
    got = projectconfig.note_unit_span(_range_page(tmp_path), AREA, 1190.0)
    assert got.count is None and got.ambiguous
    assert "THRU" in got.text


def test_the_range_reason_is_raised_only_where_the_note_would_have_been_used():
    """범례가 답하는 문서에서는 노트를 아예 안 쓰므로 사유도 올리지 않는다."""
    from app import pipeline
    amb = projectconfig.UnitNote(None, ["3-2", "6-2"], "… THRU …", True)
    counted = projectconfig.UnitNote(8, ["3-1"], "…", False)
    assert pipeline._note_ambiguous(amb, True, False)      # 범례에 없는 코드
    assert pipeline._note_ambiguous(amb, False, True)      # 남의 설정에서 빌린 값
    assert not pipeline._note_ambiguous(amb, False, False)  # 범례가 답했다
    assert not pipeline._note_ambiguous(counted, True, False)
    assert not pipeline._note_ambiguous(None, True, False)
    # 범위 문단은 배수를 주지 않는다 — 빈칸 + 사유가 답이다
    assert pipeline._note_factor(projectconfig.UNDEFINED, True, False, amb) \
        == (projectconfig.UNDEFINED, True, False, False)
