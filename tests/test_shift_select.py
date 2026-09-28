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


def test_ctrl_and_cmd_add_like_shift():
    """hotfix13 — Ctrl(맥은 Cmd) + 클릭도 묶음에 더하거나 뺀다."""
    helper = JS.split("function isAddClick(ev)", 1)[1].split("\n", 1)[0]
    assert "ev.shiftKey" in helper and "ev.ctrlKey" in helper and "ev.metaKey" in helper
    assert "if (isAddClick(ev) && it.row !== false) { toggleMulti(it.key); return; }" in JS
    assert "if (isAddClick(ev)) { toggleMulti(r.key); return; }" in JS
    # 더하기 키로 빈 자리를 빗맞혀도 묶음을 비우지 않는다
    click = JS.split('$req("#stage").addEventListener("click", ev => {', 1)[1].split("});", 1)[0]
    assert click.index("if (isAddClick(ev)) return;") < click.index("deselect()")
    # 맥 Ctrl + 클릭은 contextmenu 로 온다 — 신고가 아니라 더하기
    menu = JS.split("r.oncontextmenu = (ev) => {", 1)[1].split("};", 1)[0]
    assert "ev.ctrlKey && ev.button === 0" in menu and "toggleMulti" in menu
    # Firefox Ctrl + 누르기가 표 칸을 고르지 않게
    guard = JS.split("function _noNativeShiftSelect", 1)[1].split("\n}\n", 1)[0]
    assert "isAddClick(ev)" in guard


def test_scroll_extent_follows_the_drawing_not_its_natural_size():
    """hotfix16 — 확대는 transform 이라 흐름 안에 두면 원래 그림 크기가 스크롤 범위다."""
    assert "#wrap { position: absolute; left: 0; top: 0; transform-origin: 0 0; }" in CSS
