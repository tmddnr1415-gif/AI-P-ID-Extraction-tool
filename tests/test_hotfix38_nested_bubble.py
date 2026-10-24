"""hotfix38 (#40) — 버블 안의 버블: 다른 윤곽을 품는 윤곽은 그 낱말의 버블이 아니다.

QFE 260326 p51 의 탱크 외곽(둥근 사각형 296×801pt)이 버블로 서서 안의 LIT 셋이
"버블 2개에 걸림" 으로 미판정이 됐다 — 개정 대조가 그 셋을 삭제 후보로 올려 눈 확인
크롭이 잡았다.  규칙은 관계뿐이고 크기 창(37회차가 지움)은 다시 두지 않는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.engine import detect_symbols as ds       # noqa: E402


def test_the_innermost_outline_wins_when_a_word_falls_in_two():
    inner = pymupdf.Rect(676, 871, 751, 898)
    tank = pymupdf.Rect(560, 288, 856, 1090)
    assert ds._innermost([tank, inner]) == [inner]
    assert ds._innermost([inner, tank]) == [inner]


def test_two_side_by_side_outlines_are_still_ambiguous():
    """품는 관계가 없으면 예전 그대로 둘이다 — 그 낱말은 미판정으로 남는다."""
    a = pymupdf.Rect(100, 100, 175, 126)
    b = pymupdf.Rect(170, 100, 245, 126)
    assert ds._innermost([a, b]) == [a, b]
    assert ds._innermost([a]) == [a] and ds._innermost([]) == []


def test_qfe_p51_level_instruments_stand_inside_the_tank_outline():
    """실물 — 260326 p51 LIT·LIT·LI 가 탱크 외곽 안에서도 행이 된다 (260112 와 같게)."""
    pdf = ROOT / "data" / "QFE_260326.pdf"
    if not pdf.exists():
        import pytest
        pytest.skip("QFE PDF 가 이 기계에 없다")
    import dataclasses
    from app.engine import pidcache
    _d, pages = pidcache.load_pages(str(pdf), only=[51])
    lay = dataclasses.replace(ds.LAYOUT, anchor_slack=1.485, side_slack=0.742)
    dets = ds.detect(pages[0], lay=lay)[0]
    near = sorted(d.anchor for d in dets if 560 < d.center[0] < 870 and 840 < d.center[1] < 920)
    assert near == ["LI", "LIT", "LIT"]
