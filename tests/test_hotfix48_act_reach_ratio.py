"""hotfix48 — 액추에이터 사정거리는 **그 울타리 자기 크기의 몇 배**인가 (절대 pt 가 아니다).

사용자(회사 PC 사진 · QFE p10 `1A1Y-00EKG00-M05-0005`): *"`(*)` 표기가 있음에도 SCT 로 분류함.
이런 일이 일어나지 않도록 수정."*

원인 — QFE 는 범례를 **A3**, 본문을 **A1** 로 그린다.  범례 M 원 7.08 · centre_to_body 13.62 에서
`act_reach = 13.62 × 2 = 27.2` 가 나왔는데, 본문 M 원은 14.2 · 몸체 중심까지 30.5 라 전부 거부됐다.
액추에이터가 없으니 별표 창이 몸체 사각형뿐이고, M 원 옆에 찍힌 `(*)` 는 그 창 밖(5.5pt 위)이라
SCT 가 됐다.  네 범례의 `centre_to_body / 원 지름` 은 1.90 · 1.91 · 1.92 로 같다 — 비율은 축척을
넘고 절대 pt 는 못 넘는다 (§9 ⑥).

못박는 것:
  ① `_act_reach` — 비율이 없으면 절대값 그대로, 있으면 비율 × 스템축을 가로지르는 변
  ② 범례와 같은 크기의 울타리에서는 옛 절대값과 **같은 수** (AL NOUF1 게이트의 산술)
  ③ `derive_layout` 안에 사정거리 리터럴이 없다 — 범례 값의 식이다
  ④ 출처(`act_reach_source`)가 layout 과 결과 `valve_layout` 에 남는다
  ⑤ QFE p10 꼴 — 범례 7.08/13.62 로 유도한 비율이 본문 14.2 원 · 30.5 떨어진 몸체를 받아들인다
"""
from __future__ import annotations

import ast
import dataclasses
import inspect
import pathlib
import sys

import pymupdf
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.engine import detect_valves as dv


def _body(x0, y0, x1, y1, axis="H"):
    return dv.Body("BALL", pymupdf.Rect(x0, y0, x1, y1), axis)


# ------------------------------------------------------------------ ①
def test_without_a_ratio_the_absolute_reach_is_used():
    lay = dataclasses.replace(dv.ValveLayout(), act_reach=27.24, act_reach_ratio=0.0)
    assert dv._act_reach(pymupdf.Rect(0, 0, 14.2, 14.2), _body(0, 30, 17, 37), lay) == 27.24


def test_with_a_ratio_the_reach_scales_with_the_enclosure_across_the_stem():
    lay = dataclasses.replace(dv.ValveLayout(), act_reach=27.24, act_reach_ratio=3.8475)
    # 흐름 가로(H) → 스템 세로 → 가로지르는 변은 폭
    assert abs(dv._act_reach(pymupdf.Rect(0, 0, 14.2, 14.2), _body(0, 30, 17, 37, "H"), lay) - 3.8475 * 14.2) < 1e-9
    # 상자 10 × 30 — H 몸체면 폭 10, V 몸체면 높이 30
    box = pymupdf.Rect(0, 0, 10, 30)
    assert abs(dv._act_reach(box, _body(0, 40, 17, 47, "H"), lay) - 3.8475 * 10) < 1e-9
    assert abs(dv._act_reach(box, _body(40, 0, 47, 17, "V"), lay) - 3.8475 * 30) < 1e-9


# ------------------------------------------------------------------ ②
def test_an_enclosure_the_size_of_the_legend_circle_keeps_the_old_absolute_reach():
    """AL NOUF1 — 범례 원 14.22 · centre_to_body 26.97: 옛 절대값 53.94 가 그대로 나온다."""
    ratio = 26.97 / 14.22 * dv.REACH_FACTOR
    lay = dataclasses.replace(dv.ValveLayout(), act_reach=26.97 * dv.REACH_FACTOR, act_reach_ratio=ratio)
    got = dv._act_reach(pymupdf.Rect(0, 0, 14.22, 14.22), _body(0, 40, 17, 47), lay)
    assert abs(got - 26.97 * dv.REACH_FACTOR) < 1e-9


# ------------------------------------------------------------------ ③
def test_derive_layout_builds_the_ratio_from_legend_values_not_literals():
    src = inspect.getsource(dv.derive_layout)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            tgt = ast.unparse(node.targets[0])
            if "act_reach_ratio" in tgt and "0.0" not in ast.unparse(node.value):
                txt = ast.unparse(node.value)
                assert "ctb" in txt and "act" in txt and "REACH_FACTOR" in txt, txt
                for n in ast.walk(node.value):
                    assert not (isinstance(n, ast.Constant) and isinstance(n.value, float)), txt
    assert "act_reach_source" in src


# ------------------------------------------------------------------ ④
def test_the_layout_and_the_result_carry_the_source():
    assert hasattr(dv.ValveLayout(), "act_reach_source")
    pipe = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    block = pipe[pipe.index('"valve_layout": {'):]
    block = block[:block.index("}")]
    for key in ("act_reach", "act_reach_ratio", "act_reach_source"):
        assert f'"{key}"' in block, key


# ------------------------------------------------------------------ ⑤
def test_qfe_p10_geometry_is_accepted_by_the_ratio_and_rejected_by_the_absolute():
    """범례 7.08 원 · 13.62 스템(A3) → 비율 3.85.  본문 14.2 원이 몸체 중심에서 30.5 떨어져 있다."""
    ratio = 13.62 / 7.08 * dv.REACH_FACTOR
    enclosure = pymupdf.Rect(562.6, 710.9, 576.8, 725.1)
    body = _body(561.2, 744.9, 578.2, 752.0)
    along = (body.rect.y0 + body.rect.y1) / 2 - (enclosure.y0 + enclosure.y1) / 2
    assert 30 < along < 31
    absolute = dataclasses.replace(dv.ValveLayout(), act_reach=13.62 * dv.REACH_FACTOR, act_reach_ratio=0.0)
    scaled = dataclasses.replace(absolute, act_reach_ratio=ratio)
    assert along > dv._act_reach(enclosure, body, absolute)          # 옛 규칙 — 거부
    assert along <= dv._act_reach(enclosure, body, scaled)           # 비율 — 수용


def test_attach_actuators_reads_the_reach_through_one_function():
    src = inspect.getsource(dv.attach_actuators)
    assert "_act_reach(rect, b, lay)" in src and "lay.act_reach" not in src


# ================================================================== [B]
# 범례 장 종이 → 본 도면 종이 배율.  QFE 는 범례 5장을 A3 로, 도면 88장을 A1 로
# 냈고, 범례에서 잰 길이(별표 창 · 액추에이터 원 · 나비 · 스템)는 범례 장의 축척이라
# 그대로 본문에 쓰면 절반이다 — p10 MOV 의 `(*)` 는 액추에이터 원에서 5.06pt 인데
# 창이 10.0 x 0.495 = 4.95 로 줄어 있었다.
from app.engine import legend_rules as lr   # noqa: E402


class _Page:
    def __init__(self, page_no, w, h, heading=None):
        self.page_no, self.width, self.height = page_no, w, h
        self.analysis_scope = True
        self.heading = heading


def _pages(legend_size, form_size, n_form=6, legend_headings=lr.LEGEND_HEADINGS):
    pages = [_Page(i + 1, *legend_size, heading=h) for i, h in enumerate(legend_headings)]
    pages += [_Page(len(pages) + i + 1, *form_size) for i in range(n_form)]
    return pages


def _with_headings(monkeypatch):
    def page_with(pages, heading):
        for pc in pages:
            if getattr(pc, "heading", None) == heading:
                return pc
        return None
    monkeypatch.setattr(lr, "_page_with", page_with)


def test_legend_on_the_form_paper_scales_by_one(monkeypatch):
    _with_headings(monkeypatch)
    s, why = lr.legend_paper_scale(_pages((2384.0, 1684.0), (2384.0, 1684.0)))
    assert s == 1.0 and "form paper" in why
    s, why = lr.legend_paper_scale(_pages((1191.0, 842.0), (1191.0, 842.0)))      # TC2 꼴
    assert s == 1.0


def test_a3_legend_under_a1_sheets_scales_by_two(monkeypatch):
    _with_headings(monkeypatch)
    s, why = lr.legend_paper_scale(_pages((1191.0, 842.0), (2384.0, 1684.0), n_form=88))
    assert abs(s - 2.0) < 0.01 and "x2.0" in why
    # 본 도면이 다수여야 한다 — 범례가 다수면 범례 종이가 양식이다
    s, _ = lr.legend_paper_scale(_pages((1191.0, 842.0), (2384.0, 1684.0), n_form=1))
    assert s == 1.0


def test_non_proportional_or_missing_legend_is_not_scaled(monkeypatch):
    _with_headings(monkeypatch)
    s, why = lr.legend_paper_scale(_pages((1191.0, 842.0), (2384.0, 1000.0)))
    assert s == 1.0 and "not proportional" in why
    s, why = lr.legend_paper_scale(_pages((1191.0, 842.0), (2384.0, 1684.0), legend_headings=()))
    assert s == 1.0 and "no legend sheet" in why
    assert lr.legend_paper_scale([]) == (1.0, "no pages")


def test_derive_layout_multiplies_legend_lengths_by_the_scale(monkeypatch):
    """배율 2 면 범례 길이에서 오는 창이 전부 두 배 · 배율 1 이면 비트까지 그대로."""
    lay = dv.ValveLayout()
    derived = {"butterfly": lr.Derived(values={"tick_length": 2.0, "tick_reach_radii": 1.5,
                                               "bar_reach_radii": 2.8, "bar_min_radii": 1.0,
                                               "circle_diameter": 3.0}),
               "actuator_stem": lr.Derived(values={"stem_offaxis": 0.4, "stem_gap": 1.0,
                                                   "centre_to_body": 13.62}),
               "pneumatic": lr.Derived(values={"dome_flat": 6.0, "dome_aspect": 0.5})}
    monkeypatch.setattr(dv, "legend_bowtie_short", lambda pages, lay_: (4.95, "half"))
    monkeypatch.setattr(dv, "legend_actuator_circle", lambda pages, lay_: (7.08, "legend"))
    # 엔진은 `legend_rules` 를 맨 이름으로 가져온다 (15회차) — 그 모듈 객체를 막는다
    monkeypatch.setattr(dv.legend_rules, "legend_paper_scale", lambda pages: (1.0, "same"))
    one, _ = dv.derive_layout(["p"], lay=lay, derived=derived)
    monkeypatch.setattr(dv.legend_rules, "legend_paper_scale", lambda pages: (2.0, "A3 under A1"))
    two, _ = dv.derive_layout(["p"], lay=lay, derived=derived)
    assert one.legend_scale == 1.0 and two.legend_scale == 2.0
    assert two.act_box == pytest.approx((one.act_box[0] * 2, one.act_box[1] * 2))
    assert two.act_box_basis == pytest.approx(7.08 * 2)
    assert two.body_short == pytest.approx((one.body_short[0] * 2, one.body_short[1] * 2))
    assert two.act_reach == pytest.approx(one.act_reach * 2)
    assert two.act_reach_ratio == pytest.approx(one.act_reach_ratio)     # 비율은 배율과 무관
    assert two.disc_min == pytest.approx(one.disc_min * 2)
    assert two.dome_flat == pytest.approx((one.dome_flat[0] * 2, one.dome_flat[1] * 2))
    assert two.tick_span == pytest.approx((one.tick_span[0] * 2, one.tick_span[1] * 2))
    assert two.unit == pytest.approx(one.unit * 2)
    # 배율 1 은 배율이 없던 때(hotfix47)와 **같은 값**이다 — 네 기준 문서의 근거
    assert one.act_box == (round(7.08 * dv.ACT_BOX_BAND[0], 2), round(7.08 * dv.ACT_BOX_BAND[1], 2))
    assert one.unit == 0.5 and "(legend x" not in one.unit_source


def test_document_unit_takes_the_paper_scale(monkeypatch):
    import app.pipeline as P
    plr = P.legend_rules                       # 파이프라인이 쓰는 모듈 객체 (맨 이름 import)
    monkeypatch.setattr(plr, "derive_butterfly", lambda pages, cfg: plr.Derived(values={"circle_diameter": 3.0}))
    monkeypatch.setattr(plr, "legend_paper_scale", lambda pages: (1.0, "same"))
    u, why = P._document_unit(["p"])
    assert u == plr.legend_unit(plr.Derived(values={"circle_diameter": 3.0})) and " x " not in why
    monkeypatch.setattr(plr, "legend_paper_scale", lambda pages: (2.0017, "A3 under A1"))
    u2, why2 = P._document_unit(["p"])
    assert u2 == pytest.approx(round(u * 2.0017, 4)) and "x 2.0017" in why2


def test_paper_scale_has_no_new_lengths():
    """종이 크기 둘 말고는 숫자가 없다 — 1pt 동일 판정과 1% 비례 판정뿐."""
    src = inspect.getsource(lr.legend_paper_scale)
    nums = {float(n.value) for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant)
            and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
    assert nums <= {0, 1, 1.0, 2, 4, 0.01}, nums
