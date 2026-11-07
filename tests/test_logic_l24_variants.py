"""LOGIC L23b — 처음 보는 양식의 Logic Diagram (spike/logic_variants.py 의 변형) 이 분석 · 연결 · 시뮬레이션을 버티는가.

변형 하나 = 두 장짜리 합성 묶음.  검사는 spike 의 check() 그대로 (시트 이름 · 표 칸 · B 장 FM → A 장 출력 ·
게이트 판정 · 시뮬레이션 · 게이트가 입력과 어긋나지 않음).
"""
from __future__ import annotations

import importlib.util
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _lv():
    spec = importlib.util.spec_from_file_location("logic_variants", os.path.join(ROOT, "spike", "logic_variants.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LV = _lv()
NAMES = ["base", "rot90", "blue_lines", "hdr_source", "ref_dot", "ref_paren", "sheet_dotted", "cap_page",
         "gate_iec", "gate_ansi", "lower", "row_start0", "cols_reversed", "mixed"]


@pytest.mark.parametrize("name", NAMES)
def test_unforeseen_form_is_read_and_simulates(name, tmp_path):
    from app.logic import analyse
    v = next(x for x in LV.VARIANTS if x.name == name)
    p = str(tmp_path / f"{name}.pdf")
    LV.make(v, p)
    got = LV.check(v, analyse.analyse(p))
    for k in ("sheet_ids", "cells", "link", "gates", "sim", "logical"):
        assert got.get(k), (k, {x: got[x] for x in got if x != "funcs"})


def test_pdf_without_text_says_why(tmp_path):
    from app.logic import analyse
    v = next(x for x in LV.VARIANTS if x.name == "no_text")
    p = str(tmp_path / "nt.pdf")
    LV.make(v, p)
    res = analyse.analyse(p)
    assert "글자 층이 없습니다" in res["note"]


def test_pdf_without_logic_table_stops_clearly(tmp_path):
    from app.logic import analyse
    v = next(x for x in LV.VARIANTS if x.name == "no_table")
    p = str(tmp_path / "nb.pdf")
    LV.make(v, p)
    with pytest.raises(analyse.NotLogic):
        analyse.analyse(p)


def test_reference_forms():
    from app.logic import refs
    assert refs.find("G049-40") == [("G049", 40)]
    assert refs.find("0016/72 0016/77") == [("0016", 72), ("0016", 77)]
    assert refs.find("SH.AB-101 NO.51") == [("AB-101", 51)]
    assert refs.find("(AB-101 / 12)") == [("AB-101", 12)]
    assert refs.find("LD.01.001-51") == [("LD.01.001", 51)]
    assert refs.find("10.5 SEC") == []                     # 숫자만의 '.' 는 참조가 아니다
    assert refs.find("ab-101 7", known={"AB-101"}) == [("AB-101", 7)]
    assert refs.full("HMI") is None
