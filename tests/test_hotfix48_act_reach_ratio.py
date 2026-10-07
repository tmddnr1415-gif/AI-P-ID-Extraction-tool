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
