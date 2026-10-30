"""L83 — 두 파선이 엇갈리는 자리는 연결이 아니다.
들여온 파선은 토막마다 선 하나라, 엇갈리는 자리에서 한 줄의 토막 끝이 다른 줄 토막의 몸통 · 끝에 우연히 닿으면
예전엔 한 그물이 되었다 (19VA 0006 '매크로 틀' 파선 × 신호 파선 — 틀에 걸친 957 토막이 신호 하나로).
분석기(graph.joinable)처럼 파선의 안쪽 토막 끝은 제 줄의 다음 토막에만 잇는다.  파선의 바깥 끝은 그대로 이을 수 있다."""
import gzip
import json
import re
from pathlib import Path

from app.logic import draw_sim as DS


def _nets(wires):
    net_of, _ = DS._nets_of(wires)
    return {w["id"]: net_of[i] for i, w in enumerate(wires)}


def test_two_dashed_lines_crossing_stay_apart():
    # 0006 그대로 — 가로 신호 파선(44)과 세로 틀 파선(123)이 843, 505.6 에서 엇갈린다.  CAD 가 교차 자리에서 토막을 끊어
    # 두 줄의 토막 끝이 0.55pt 안에 모였다 (끝-끝 · 끝-몸통 모두 닿음)
    h = [{"id": "h_a", "pts": [[855.4, 505.61], [851.7, 505.61]], "dashed": True},
         {"id": "h_b", "pts": [[849.85, 505.61], [842.9, 505.61]], "dashed": True},
         {"id": "h_c", "pts": [[842.9, 505.61], [839.43, 505.61]], "dashed": True},
         {"id": "h_d", "pts": [[837.56, 505.61], [833.82, 505.61]], "dashed": True}]
    v = [{"id": "v_a", "pts": [[843.01, 495.82], [843.01, 499.56]], "dashed": True},
         {"id": "v_b", "pts": [[843.01, 501.43], [843.01, 505.17]], "dashed": True},
         {"id": "v_c", "pts": [[843.01, 505.17], [843.01, 507.04]], "dashed": True},
         {"id": "v_d", "pts": [[843.01, 508.91], [843.01, 512.65]], "dashed": True}]
    n = _nets(h + v)
    assert n["h_b"] == n["h_c"] and n["v_b"] == n["v_c"], "한 줄의 맞닿은 토막은 한 선이다"
    assert n["h_b"] != n["v_b"], "엇갈린 두 파선이 한 그물이 되었다"


def test_dash_end_touching_its_neighbour_stays_one_line():
    a = {"id": "a", "pts": [[0.0, 10.0], [5.0, 10.0]], "dashed": True}
    b = {"id": "b", "pts": [[5.0, 10.0], [9.0, 10.0]], "dashed": True}       # 교차 자리에서 끊긴 토막 (틈 0)
    n = _nets([a, b])
    assert n["a"] == n["b"]


def test_dashed_line_free_end_still_joins_a_solid_line():
    d = [{"id": "d_0", "pts": [[0.0, 20.0], [3.7, 20.0]], "dashed": True},        # 바깥 끝 x=0 · 안쪽 끝 3.7
         {"id": "d_1", "pts": [[5.6, 20.0], [9.3, 20.0]], "dashed": True}]
    s = {"id": "s", "pts": [[0.0, 0.0], [0.0, 40.0]]}
    n = _nets(d + [s])
    assert n["d_0"] == n["s"], "파선의 바깥 끝이 세로선 몸통에 닿으면 연결이다"


def test_amiral_0006_macro_frame_is_not_a_signal():
    """시드 묶음 0006 (CIRCUIT LOGIC DUAL) — 매크로 틀 파선(분석 선 123)이 신호 파선(44)과 한 그물이 되지 않는다."""
    seed = Path(__file__).resolve().parents[1] / "config" / "logic_draw_seed" / "amiral_19va_r1.json.gz"
    doc = next(d for d in json.load(gzip.open(seed))["docs"] if d["name"] == "0006")
    wires = DS._drop_inside([w for w in doc["wires"] if len(w.get("pts") or []) >= 2], doc["blocks"])
    net_of, members = DS._nets_of(wires)
    src = [re.match(r"n(\d+)_", w["id"]).group(1) for w in wires]
    frame = {net_of[i] for i, s in enumerate(src) if s == "123"}
    assert all({src[i] for i in members[k]} == {"123"} for k in frame)
