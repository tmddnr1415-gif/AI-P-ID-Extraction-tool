"""hotfix12 — Shift + 누르기가 도면을 브라우저 선택으로 덮지 않는다 · 띠 끝은 가장자리에 붙는다.

현장 캡처: Shift 를 누른 채 도면을 누르면 장 전체가 파랗게 덮였다.  우리 띠가 아니라
브라우저의 "선택 넓히기" 가 그림(#sheet)을 통째로 고른 것이다
(`spike/ui_audit_shift_select.py` 가 고치기 전 코드에서 그대로 재현한다).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def test_stage_is_not_selectable():
    assert "#stage, #stage * { -webkit-user-select: none; user-select: none; }" in CSS
    assert 'id="sheet" alt="" draggable="false"' in HTML


def test_shift_mousedown_is_swallowed_on_stage_and_grid():
    assert '$req("#stage").addEventListener("mousedown", _noNativeShiftSelect, true)' in JS
    assert '$req("#grid").addEventListener("mousedown", _noNativeShiftSelect, true)' in JS
    body = JS.split("function _noNativeShiftSelect", 1)[1].split("\n}\n", 1)[0]
    assert "preventDefault()" in body and "removeAllRanges()" in body
    # pointerdown 은 막지 않는다 — 막으면 click(Shift 더하기)이 안 온다.
    down = JS.split('$req("#stage").addEventListener("pointerdown", ev => {\n  if (ev.button !== 0 || !ev.shiftKey', 1)[1]
    down = down.split("}, true);", 1)[0]
    code = "\n".join(l.split("//", 1)[0] for l in down.splitlines())
    assert "preventDefault" not in code


def test_band_end_clamps_to_sheet_edge():
    end = JS.split("function _bandEnd", 1)[1].split("\n}\n", 1)[0]
    assert "sheetPointClamped(ev)" in end
    move = JS.split('addEventListener("pointermove", ev => {\n  if (!_band', 1)[1].split("}, true);", 1)[0]
    assert "sheetPointClamped(ev)" in move
