"""47회차 — 액추에이터 울타리의 크기 창을 그 문서 범례가 정한다.

6차 피드백의 최다 지적(“MOV 가 식별되지 않는다” · TC2 9장 · AL NOUF1 1장)의
원인은 `ValveLayout.act_box = (9.0, 34.0)` 이 **절대 pt** 였다는 것이다.
그 값은 AL NOUF1 범례가 그린 액추에이터 원 14.22pt 에서 잰 것이고, 같은 모터
원을 A3 로 7.08(TC2) · 7.02(UAD) 로 그리는 문서에서는 하한 9.0 이 **제대로
찾아 둔 M 원을 전부 거부**했다 (23회차 §6 — 절대 pt 는 축척을 넘지 못한다).

여기서 못박는 것 넷:

1. 창은 **범례 원의 배수**다 — 코드에 새 절대 pt 가 없다.
2. AL NOUF1 을 재현한다 — 14.22 × 배율이 옛 (9.0, 34.0) 과 같다 (게이트).
3. **두 번 이상 그려진 크기만** 받는다 (18·25회차 규율).  못 찾으면 `None` 과
   **사유**이지 조용한 폴백이 아니다.
4. 유도 결과의 출처가 결과에 남는다 (`act_box_source` · `act_box_basis`).
"""
import ast
from pathlib import Path

import pymupdf
import pytest

from app.engine import detect_valves as dv
from app.engine import legend_rules as lr
from app.engine import pidcache

SRC = Path("app/engine/detect_valves.py")


def _legend_page(diameters, *, heading=lr.ACTUATOR_HEADING):
    """`ACTUATORS` 열에 지름이 그 목록인 원을 그린 가짜 범례 장."""
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    page.insert_text((300, 40), heading, fontsize=8)
    page.insert_text((300, 60), "ACTUATORS", fontsize=8)
    for i, d in enumerate(diameters):
        sh = page.new_shape()                   # 원마다 따로 — 한 객체가 한 원이다
        sh.draw_circle(pymupdf.Point(200.0, 100.0 + i * 40), d / 2)
        sh.finish(width=0.3)
        sh.commit()
    words = [(pymupdf.Rect(r[:4]), r[4]) for r in page.get_text("words")]
    pc = pidcache.PageCache(page=page, page_no=1, source_rotation=0,
                            width=600, height=400, words=words, project_name="")
    return doc, pc


def test_the_window_is_a_multiple_of_the_legend_circle():
    """새 절대 pt 가 아니라 배수다 — 같은 원을 절반으로 그리면 창도 절반이다."""
    doc_a, big = _legend_page([14.22, 14.22, 5.7])
    doc_b, small = _legend_page([7.11, 7.11, 2.85])
    got_big, _ = dv.legend_actuator_circle([big])
    got_small, _ = dv.legend_actuator_circle([small])
    assert round(got_big, 2) == 14.22 and round(got_small, 2) == 7.11
    lo_b, hi_b = (got_big * b for b in dv.ACT_BOX_BAND)
    lo_s, hi_s = (got_small * b for b in dv.ACT_BOX_BAND)
    assert abs(lo_b / lo_s - 2.0) < 1e-6 and abs(hi_b / hi_s - 2.0) < 1e-6
    doc_a.close(); doc_b.close()


def test_al_nouf1_reproduces_the_old_absolute_window():
    """게이트 — 14.22pt 범례에서 옛 (9.0, 34.0) 이 그대로 나와야 지문이 안 움직인다."""
    lo, hi = (round(14.22 * b, 2) for b in dv.ACT_BOX_BAND)
    assert (lo, hi) == (9.0, 34.0)
    assert dv.ValveLayout().act_box == (9.0, 34.0)      # 설정 폴백도 같은 값


def test_a_size_drawn_once_is_not_the_actuator_circle():
    """되풀이되지 않으면 그 장의 다른 그림일 수 있다 — SADARA 가 이 경우다."""
    doc, pc = _legend_page([15.52, 17.71])
    got, why = dv.legend_actuator_circle([pc])
    assert got is None
    assert "twice" in why and "15.52" in why            # 조용하지 않다
    doc.close()


def test_no_actuator_sheet_says_so():
    doc, pc = _legend_page([7.0, 7.0], heading="LINE VALVES")
    got, why = dv.legend_actuator_circle([pc])
    assert got is None and lr.ACTUATOR_HEADING in why
    doc.close()


def test_the_derivation_records_where_the_value_came_from():
    """`act_box_source` · `act_box_basis` — 유도인지 폴백인지 결과가 말한다."""
    lay = dv.ValveLayout()
    assert lay.act_box_source == "CONFIG" and lay.act_box_basis == 0.0
    fields = {f for f in dv.ValveLayout.__dataclass_fields__}
    assert {"act_box", "act_box_source", "act_box_basis"} <= fields


def test_derive_layout_bands_the_window_and_never_writes_a_new_absolute_pt():
    """`derive_layout` 안에서 act_box 에 들어가는 것은 곱셈뿐이다 (리터럴 금지)."""
    tree = ast.parse(SRC.read_text())
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "derive_layout")
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Store)):
            continue
        key = getattr(node.slice, "value", None)
        if key != "act_box":
            continue
        assign = next(a for a in ast.walk(fn)
                      if isinstance(a, ast.Assign) and node in ast.walk(a))
        text = ast.dump(assign.value)
        assert "Mult" in text, "창은 범례 원의 배수여야 한다"
        assert "ACT_BOX_BAND" in ast.unparse(assign.value)


@pytest.mark.parametrize("band", [dv.ACT_BOX_BAND])
def test_the_band_itself_is_traceable_to_the_legend(band):
    """배율 자체가 AL NOUF1 실측에서 나왔다는 것을 근거 주석이 아니라 산술로 본다."""
    lo, hi = band
    assert abs(lo - 9.0 / 14.22) < 5e-4 and abs(hi - 34.0 / 14.22) < 5e-4
