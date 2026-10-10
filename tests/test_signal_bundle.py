"""39회차 — 맞닿은 버블 묶음은 그 문서의 ISA 표가 SWITCH 라고 읽는 글자에만.

사용자 확정은 *레벨 스위치* 하나가 여러 설정점을 보고하는 경우였다.  처음 쓴
규칙은 변수 글자만 봐서 TC2 의 `FIT`/`FIT`/`FE` 묶음(기기 셋)을 한 행으로
접었다.  기능 글자의 뜻은 코드에 적지 않고 그 문서의 ISA 표에서 읽는다.
"""
from app.engine.isa_table import IsaTable
from app import pipeline


def _table(succeeding):
    return IsaTable(first={"L": ("LEVEL",), "F": ("FLOW",), "P": ("PRESSURE",),
                           "PD": ("DIFFERENTIAL", "PRESSURE")},
                    succeeding=succeeding)


TABLE = _table({"S": ("SWITCH",), "I": ("INDICATOR",),
                "E": ("PRIMARY", "ELEMENT"), "T": ("TRANSMITTER",)})


def test_switch_letters_read_from_the_table():
    assert pipeline._is_switch("LSHH", TABLE)
    assert pipeline._is_switch("LSH", TABLE)
    assert pipeline._is_switch("LSL", TABLE)
    assert pipeline._is_switch("PDSH", TABLE)   # two-letter variable first


def test_transmitters_and_elements_are_not_switches():
    assert not pipeline._is_switch("FIT", TABLE)
    assert not pipeline._is_switch("FE", TABLE)
    assert not pipeline._is_switch("PIT", TABLE)
    assert not pipeline._is_switch("L", TABLE)       # no function letter


def test_no_table_or_no_switch_word_folds_nothing():
    assert not pipeline._is_switch("LSH", None)
    assert not pipeline._is_switch("LSH", _table({}))
    assert not pipeline._is_switch("LSH", _table({"S": ("SAFETY",)}))


class _Row:
    def __init__(self, key, anchor, rect, page_no=1):
        self.key, self.page_no, self.rect = key, page_no, rect
        self.evidence = {"anchor": anchor}
        self.type = anchor
        self.qty = 1
        self.needs_review = ""
        self.drawing_no = "X"


def _stack(anchors):
    rows, y = [], 100.0
    for i, a in enumerate(anchors):
        rows.append(_Row(f"k{i}", a, [100.0, y, 134.0, y + 11.0]))
        y += 11.0                                # touching: gap 0
    return rows


def test_level_switch_stack_folds_and_fit_stack_does_not():
    groups, folded = pipeline._signal_groups(_stack(["LSHH", "LSH", "LSL"]), TABLE)
    assert len(groups) == 1 and len(folded) == 2
    groups, folded = pipeline._signal_groups(_stack(["FIT", "FIT", "FE"]), TABLE)
    assert groups == [] and folded == set()


def test_same_stack_without_a_table_is_left_alone():
    groups, folded = pipeline._signal_groups(_stack(["LSHH", "LSH", "LSL"]), None)
    assert groups == [] and folded == set()
