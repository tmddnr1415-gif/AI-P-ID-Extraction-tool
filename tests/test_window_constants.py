"""37회차 [C] — 창 상수 셋의 판정.

`ds.cap_span` 은 지웠다: 네 문서에서 창을 해제해도(cap_span=(0,∞)) 행·지문·미판정·축3 가
한 칸도 안 움직였다 (`out/round37_windows.md` §4).  캡을 가르는 것은 크기가 아니라
모양(`cap_ratio`)과 짝짓기다.  `dv.seg_span` 은 **남긴다** — 상한 60 이 몸체 검출기의
결함(높이 2pt 선을 BUTTERFLY 몸체로 받음)을 가리고 있어, 그 결함을 고치기 전에는 열 수 없다.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine"))

import detect_symbols as ds   # noqa: E402
import detect_valves as dv    # noqa: E402


def test_cap_size_window_is_gone_but_shape_window_stays():
    assert not hasattr(ds.Layout, "cap_span")
    assert hasattr(ds.Layout, "cap_ratio")
    src = inspect.getsource(ds.bubble_outlines)
    assert "cap_span" not in src
    assert "cap_ratio" in src


def test_segment_window_stays_until_the_body_detector_rejects_lines():
    # 열면 TC2 p18 77.6x2.0 · UAD p30 229.5x2.1 짜리 "몸체" 가 행이 된다 (실측).
    lo, hi = dv.ValveLayout().seg_span
    assert lo == 1.0 and hi == 60.0
