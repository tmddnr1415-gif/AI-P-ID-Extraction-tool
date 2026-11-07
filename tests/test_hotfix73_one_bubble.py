"""hotfix73 — 버블 하나는 계기 하나다 (`detect_symbols._one_function_per_bubble`).

QFE 실측으로 세 갈래가 나왔다 (AL NOUF1 · TC2 는 한 버블에 두 행이 0 이라 안 닿는다):
  ① 본문을 두 번 인쇄한 장(p42)의 같은 낱말 → 같은 행 둘
  ② 버블 옆 라벨이 여유로 들어와 버블을 차지 (p51 `SC` · p69 `DN`)
  ③ 기기 외곽 안의 낱말 둘 (p58 `FLASH`·`SPARE`)
"""
from __future__ import annotations

import pymupdf

from app.engine import detect_symbols as ds


def _det(anchor, bubble, cx, cy):
    return ds.Detection(anchor=anchor, bbox=bubble, center=(cx, cy))


def _w(t, cx, cy, h=6.0):
    return (pymupdf.Rect(cx - 6, cy - h / 2, cx + 6, cy + h / 2), t)


def test_single_detections_pass_through_unchanged():
    b1, b2 = pymupdf.Rect(0, 0, 60, 20), pymupdf.Rect(100, 0, 160, 20)
    dets = [_det("PIT", b1, 30, 8), _det("TIT", b2, 130, 8)]
    assert ds._one_function_per_bubble(dets, words=[]) is dets


def test_overprinted_word_is_one_instrument():
    b = pymupdf.Rect(0, 0, 60, 20)
    dets = [_det("LIT", b, 30, 8), _det("LIT", b, 30.2, 8.1)]
    out = ds._one_function_per_bubble(dets, words=[_w("LIT", 30, 8), _w("LIT", 30.2, 8.1)])
    assert len(out) == 1 and out[0].evidence["overprinted"] == 2


def test_label_outside_the_bubble_loses_to_the_word_inside():
    b = pymupdf.Rect(0, 0, 25, 73)
    inside, outside = _det("AIT", b, 12, 30), _det("SC", b, 27, 2)
    out = ds._one_function_per_bubble([outside, inside], words=[])
    assert out == [inside]
    assert inside.evidence["outside_labels"][0]["anchor"] == "SC"


def test_two_different_functions_inside_one_outline_are_not_an_instrument():
    b = pymupdf.Rect(0, 0, 180, 600)
    unv: list = []
    out = ds._one_function_per_bubble([_det("FLASH", b, 90, 100), _det("SPARE", b, 90, 300)],
                                      words=[], unverified=unv)
    assert out == []
    assert {u["anchor"] for u in unv} == {"FLASH", "SPARE"}
    assert all(u["bubbles_matched"] == 1 and "외곽" in u["why"] for u in unv)


def test_same_word_far_apart_in_one_outline_is_not_an_overprint():
    # 같은 글자라도 제 높이 밖이면 겹침이 아니다 — 지우지 않는다 (둘 다 남는다)
    b = pymupdf.Rect(0, 0, 60, 60)
    dets = [_det("PI", b, 30, 10), _det("PI", b, 30, 50)]
    out = ds._one_function_per_bubble(dets, words=[_w("PI", 30, 10), _w("PI", 30, 50)])
    assert len(out) == 2


# --- Typical 표식 이름표 (`typical._label_below`) --------------------------------
from app.engine import typical  # noqa: E402


def _mark(x, y=100.0, d=16.0):
    return typical.Mark(id="D", rect=pymupdf.Rect(x - d / 2, y - d / 2, x + d / 2, y + d / 2),
                        d=d, kind="line")


def _word(t, x0, y0=112.0, cw=5.4, h=7.0):
    return (pymupdf.Rect(x0, y0, x0 + cw * len(t), y0 + h), t)


def test_side_by_side_marks_each_keep_their_own_label():
    # QFE p47 — `DRAIN 2 DRAIN 3` 가 한 줄로 붙어 인쇄된다
    m2, m3 = _mark(300), _mark(347)
    words = [_word("DRAIN", 280), _word("2", 310), _word("DRAIN", 327), _word("3", 357)]
    assert typical._label_below(m2, words, [m2, m3])[0] == "DRAIN 2"
    assert typical._label_below(m3, words, [m2, m3])[0] == "DRAIN 3"


def test_an_unrelated_note_on_the_same_line_is_not_part_of_the_label():
    # QFE p47 — `DRAIN 4` 오른쪽 멀리 `ASME SEC.I`
    m = _mark(300)
    words = [_word("DRAIN", 280), _word("4", 310), _word("ASME", 340), _word("SEC.I", 365)]
    label, num = typical._label_below(m, words, [m])
    assert label == "DRAIN 4" and num == 4


# --- 버블 가운데 선 · 같은 태그 같은 TYPE 접기 ----------------------------------
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent / "app" / "engine"))
import isa_table  # noqa: E402
import pidcache  # noqa: E402
from app import pipeline as P  # noqa: E402

_TABLE = isa_table.IsaTable(first={"F": ("FLOW",)},
                            succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",)},
                            page_no=3, note="test")


def _frow(key, anchor, typ, lines, y):
    return P.Row(key=key, tab=P.TAB_FIELD, page_no=41, drawing_no="D", type=typ, qty=1,
                 rect=(100, y, 160, y + 20), tag_no="31GKC20CF001",
                 evidence={"anchor": anchor, "detail": ({"bubble_lines": lines} if lines else {})})


def test_panel_bubble_with_the_same_tag_and_type_folds_into_the_field_bubble():
    # QFE p41 — `FIT`(가운데 선 한 줄) 위 · `FT`(선 없음 → 사전으로 FIT) 아래
    panel, field = _frow("a", "FIT", "FIT", 1, 100), _frow("b", "FT", "FIT", 0, 160)
    facts, folded = P._fold_readouts([panel, field], _TABLE)
    assert folded == {"a"}
    assert field.evidence["readout_folded"][0]["basis"] == "TAG_LOCATION"


def test_no_fold_when_the_drawing_does_not_say_which_is_the_field_one():
    a, b = _frow("a", "FIT", "FIT", 0, 100), _frow("b", "FT", "FIT", 0, 160)
    assert P._fold_readouts([a, b], _TABLE)[1] == set()


def test_bubble_lines_counts_distinct_lines_across_the_middle(tmp_path):
    d = pymupdf.open(); pg = d.new_page(width=600, height=400)
    pg.draw_line((100, 110), (160, 110))                    # 한 줄 (가운데)
    pg.draw_line((300, 108.5), (360, 108.5)); pg.draw_line((300, 111.5), (360, 111.5))   # 두 줄
    pg.draw_line((300, 111.6), (360, 111.6))                # 같은 선을 겹쳐 그림 — 한 줄로
    pg.draw_line((500, 101), (560, 101))                    # 위 테두리 — 가운데 띠 밖
    p = tmp_path / "b.pdf"; d.save(p)
    _doc, pcs = pidcache.load_pages(p)
    pc = pcs[0]
    assert ds.bubble_lines(pc, (100, 100, 160, 120)) == 1
    assert ds.bubble_lines(pc, (300, 100, 360, 120)) == 2
    assert ds.bubble_lines(pc, (500, 100, 560, 120)) == 0
