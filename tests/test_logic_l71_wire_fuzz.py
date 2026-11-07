"""L71 — 선 연결은 축척 · 굵기 · 홉 모양 · 연결점 모양 · 회전이 바뀌어도 같게 읽힌다.

`spike/logic_wire_fuzz.py` 가 무작위 합성 장을 만들고 정답(경로마다 왼쪽 행 → 오른쪽 행)과 맞댄다.  여기서는
퍼징이 결함을 잡았던 씨앗을 고정해 다시 돌린다 — 이 씨앗들이 다시 실패하면 그 결함이 돌아온 것이다.

  1148  꺾은선 홉 → 짧은 토막 → 모서리 (고친 홉이 글자 무리에 남아 끊김)
  1009  교차 둘을 연달아 끊어 그림 (바깥 두 끝이 가운데 토막을 건너뛰어 이음)
  1000  곡선으로만 칠한 연결점 · 270° (점을 못 읽어 배선이 만든 네모가 AND 로 섬)
  3895  점 없는 갈래 T · 꺾임 · 교차가 둘러싼 네모 (가짜 AND)
  3316  넓은 틈을 지나는 선이 바로 옆 홉으로 끊김 (지나는 선이 틈보다 짧아 보임)
  5923  LOGIC 영역의 긴 신호선이 표 괘선으로 섞여 표를 못 찾음
  10192 홉 → 토막 → 홉 → 토막 이 파선으로 읽혀 끝이 매달림
  11680 넓은 틈을 지나는 선이 두 선 사이의 짧은 꺾임 토막 (틈보다 짧음)
"""
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import pymupdf
import pytest

from app.logic import geom, graph

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("logic_wire_fuzz", ROOT / "spike" / "logic_wire_fuzz.py")
fuzz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fuzz)

SEEDS = [1, 7, 23, 42, 1000, 1009, 1044, 1045, 1061, 1077, 1084, 1125, 1136, 1148, 3316, 3895, 5003, 5923, 6111, 6755, 10192, 11680]


@pytest.mark.parametrize("seed", SEEDS)
def test_fuzz_seed_reads_every_path(seed, tmp_path):
    pdf, meta = fuzz.build(seed, tmp_path)
    assert fuzz.check(pdf, meta) == [], meta


def test_filled_curve_circle_is_a_dot():
    """테두리 없이 곡선으로만 칠한 원도 연결점이다 (예전엔 꼭짓점이 없어 통째로 버렸다)."""
    doc = pymupdf.open()
    pg = doc.new_page(width=400, height=300)
    pg.set_rotation(270)
    sh = pg.new_shape()
    sh.draw_circle(pymupdf.Point(100, 100), 2.0)
    sh.finish(color=None, fill=(0, 0, 0), width=0)
    sh.commit()
    pr = geom.read(pg, 0)
    assert len(pr.circles) == 1
    c = pr.circles[0]
    assert getattr(c, "poly_dot", False) and math.isclose(c.r, 2.0, abs_tol=0.05)


def test_open_corners_make_wiring_not_a_box():
    """모서리 셋에서 선이 바깥으로 이어지면 네 선이 둘러싼 배선이다 — 상자 변은 모서리에서 끝난다."""
    S = geom.Seg
    P = 11.3
    polys = [geom.Poly([S(0, 0, 0, 200)], (0, 0, 0, 200)),            # 왼쪽 세로선 — 위아래로 지나감
             geom.Poly([S(0, 50, 100, 50)], (0, 50, 100, 50)),         # 위 — 왼쪽 T 에서 시작해 모서리
             geom.Poly([S(100, 50, 100, 300)], (100, 50, 100, 300)),   # 오른쪽 — 아래로 계속
             geom.Poly([S(10, 90, 100, 90), S(10, 90, 10, 250)], (10, 90, 100, 250)),   # 아래 — 왼쪽 끝에서 아래로 꺾임
             geom.Poly([S(100, 90, 300, 90)], (100, 90, 300, 90))]
    out, _ = graph._assemble_rects(polys, [], P, 0.9)
    assert not any(abs(r.x0 - 0) < 1 and abs(r.y0 - 50) < 1 for r in out)
    # 진짜 상자 (모서리에서 끝나는 네 변) 는 그대로 선다
    box = [geom.Poly([S(200, 10, 230, 10), S(230, 10, 230, 30), S(230, 30, 200, 30), S(200, 30, 200, 10)][k:k + 1],
                     (200, 10, 230, 30)) for k in range(4)]
    out, _ = graph._assemble_rects(box, [], P, 0.9)
    assert len(out) == 1
