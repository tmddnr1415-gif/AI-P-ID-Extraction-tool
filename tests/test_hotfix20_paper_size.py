"""hotfix20 — 다른 프로젝트 · 다른 종이 크기의 PDF 도 같은 판정을 낸다.

실측 방법: 같은 도면을 종이만 바꿔 다시 낸 PDF (`spike/rescale_pdf.py`) 로
TC2 A4·A3·A2·A1 · AL NOUF1 A2·A1·A0 를 분석해 행을 대조했다.  고치기 전에는
아는 프로젝트를 다른 크기로 내면 도면번호 0/12 로 멈추고(프로필 좌표를 종이 확인
없이 믿음), 밸브는 A1 에서 정한 고정 pt 허용치 때문에 크기에 따라 빠졌다.

규칙: ① 프로필 좌표는 그 프로필이 잰 종이와 크기가 같을 때만 ② 고정 pt 허용치는
그 문서 범례의 나비(짧은 변 9.9 · 원 6.06 — AL NOUF1 의 값)로 잰 **길이 단위**를
곱한다 — AL NOUF1 은 1.0 이라 소수점까지 그대로.
"""
import inspect

import pytest

from app import pipeline as P
from app.engine import detect_valves as dv, legend_rules as lr


def test_unit_is_one_for_the_reference_legend():
    """AL NOUF1 범례 값을 그대로 넣으면 단위 1.0 — 기준선이 구조적으로 안 움직인다."""
    bf = lr.Derived(values={"circle_diameter": lr.BUTTERFLY_CIRCLE_BASIS})
    assert lr.legend_unit(bf) == 1.0
    assert lr.legend_unit(lr.Derived(values={})) == 1.0          # 못 재면 1.0 (예전 그대로)
    assert lr.legend_unit(None) == 1.0
    assert round(lr.legend_unit(lr.Derived(values={"circle_diameter": 3.03})), 3) == 0.5


def test_valve_tolerances_scale_with_the_document_unit(monkeypatch):
    lay = dv.ValveLayout()
    empty = {"butterfly": lr.Derived(values={}), "actuator_stem": lr.Derived(values={}),
             "pneumatic": lr.Derived(values={})}
    monkeypatch.setattr(dv, "legend_bowtie_short", lambda pages, lay_: (4.95, "half"))
    monkeypatch.setattr(dv, "legend_actuator_circle", lambda pages, lay_: (None, "none"))
    out, _ = dv.derive_layout([], lay=lay, derived=empty)
    assert out.unit == 0.5 and out.unit_source.startswith("LEGEND")
    for k in ("centre_tol", "bar_cover", "bar_axis_tol", "arc_above"):
        assert getattr(out, k) == pytest.approx(getattr(lay, k) * 0.5)
    assert out.seg_span == pytest.approx((lay.seg_span[0] * 0.5, lay.seg_span[1] * 0.5))
    # AL NOUF1 의 나비 그대로면 한 칸도 안 움직인다
    monkeypatch.setattr(dv, "legend_bowtie_short", lambda pages, lay_: (dv.BODY_SHORT_BASIS, "ref"))
    same, _ = dv.derive_layout([], lay=lay, derived=empty)
    assert same.unit == 1.0 and same.centre_tol == lay.centre_tol and same.seg_span == lay.seg_span


def test_split_groups_cross_the_waist_and_reject_flat_pieces():
    src = inspect.getsource(dv._split_groups)
    assert "first_tol = lay.waist_ratio[1] / 2.0 * basis" in src      # 허리 원반 반지름 — 범례 정의
    assert "meet = max(tol, first_tol)" in src
    assert "1.0 / r1 <= abs(m) <= 1.0 / r0 or r0 <= abs(m) <= r1" in src   # 몸체 비가 허락하는 기울기만
    # 교점 기록은 몸체가 섰을 때만 — 앞쪽에서 `seen_c.add` 를 먼저 하지 않는다
    assert src.index("out[key] = [(s[0], s[1]) for s in keep]") < src.index("seen_c.add(ck)")


def test_scaled_config_keys_have_no_new_numbers():
    """곱하는 목록의 기본값은 각 모듈 dataclass 기본값과 같은 수다 — 새 값이 없다."""
    ds = P.ds.Layout()
    assert P._UNIT_SCALED_KEYS["vendor_marks.side"] == ds.mark_side
    assert P._UNIT_SCALED_KEYS["broken_line.brk_max_gap"] == ds.brk_max_gap
    assert P._UNIT_SCALED_KEYS["broken_line.brk_bridge"] == ds.brk_bridge
    assert P._UNIT_SCALED_KEYS["broken_line.brk_min_span"] == ds.brk_min_span
    assert P._UNIT_SCALED_KEYS["broken_line.brk_corner_tol"] == ds.brk_corner_tol
    assert P._UNIT_SCALED_KEYS["bubbles.side_slack"] == ds.side_slack
    assert P._UNIT_SCALED_KEYS["bubbles.anchor_slack"] == ds.anchor_slack
    assert P._scale_value([[4.0, 4.0], 2.5], 0.5) == [[2.0, 2.0], 1.25]


def test_legend_measurements_take_a_unit():
    assert "unit" in inspect.signature(lr.derive_actuator_stem).parameters
    assert "legend_unit(bf)" in inspect.getsource(lr.derive_all)
    src = inspect.getsource(P.pipe_graph.derive_line_styles)
    assert "6 * unit" in src and "200 * unit" in src
