"""L75 — 작도: 꺾인 선의 토막을 끌어 꺾인 자리를 옮긴다 · 추천 경로가 기호에 바짝 붙어 꺾지 않는다 (화면 전용).

사용자 지시: 선을 그리면 꺾인 선을 왼쪽 · 오른쪽으로 조절할 수 있도록 · 지금 너무 기호에 붙어 있다.
화면 확인은 spike/ui_audit_l75.py (크롬) — 여기서는 화면 소스가 그 길을 갖고 있는지 · PDF 양식이 그대로인지를 못박는다.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic_draw.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/logic_draw.css").read_text(encoding="utf-8")


def test_selected_wire_gets_a_handle_per_segment():
    assert 'class: "seghd " + (vert ? "ax-x" : "ax-y")' in JS
    assert ".seghd.ax-x { cursor: ew-resize; }" in CSS


def test_segment_drag_moves_both_points_on_one_axis_and_keeps_end_points():
    assert "function segDragStart(" in JS and "function segDragMove(" in JS
    assert "w.pts[d.i][k] = v; w.pts[d.i + 1][k] = v;" in JS, "토막의 두 점을 같은 축으로 함께 — 선은 가로/세로만"
    assert "const stub = (end, nxt)" in JS, "끝 토막은 끝점에 짧은 토막을 남긴다 (단자 · 행 자리에서 떨어지지 않게)"
    assert "if (S.drag.seg) { segDragMove(p, e.shiftKey); return; }" in JS
    assert "S.drag.seg) { const w = S.doc.wires.find(w => w.id === S.drag.id); if (w) { w.pts = orthoPts(w.pts)" in JS


def test_route_prefers_bending_a_pitch_away_from_the_symbol():
    assert "L75 — 기호 앞 한 행 간격 안에서 세로로 가지 않는다" in JS
    assert "if (run < P) sc += 6 * (1 - run / P);" in JS


def test_pdf_writer_does_not_know_about_handles():
    assert "seghd" not in (ROOT / "app/logic/draw.py").read_text(encoding="utf-8")
