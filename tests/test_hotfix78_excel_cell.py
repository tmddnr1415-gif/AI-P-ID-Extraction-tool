"""hotfix78 — 목록 칸을 엑셀처럼 고친다.

사용자: *"출력된 List 의 값 수정은 해당 셀을 더블클릭하면 엑셀 셀과 같이 사용자가 편집할 수 있도록
excel 과 같은 유사한 느낌으로 구현해줘라"*.
한 번 누르면 칸이 골라지고(녹색 테두리) · 두 번 누르거나 F2 · 바로 타자를 치면 편집 · Enter 저장 후 아래 ·
Tab 저장 후 오른쪽 · Esc 되돌림 · 화살표 칸 이동 · Ctrl+C/Ctrl+V 한 칸.  저장 길은 그대로 `saveEdit` 하나.
화면 동작은 `spike/ui_audit_excel_cell.py` 가 띄워서 누른다.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    return JS[i:JS.index("\n}\n", i) + 2]


def _iife(name):
    i = JS.index(f"(function {name}()")
    return JS[i:JS.index("\n})();", i)]


def test_cells_are_not_editable_until_asked():
    row = _fn("rowHtml")
    assert "contenteditable" not in row.lower()                   # 한 번 누름은 고르기 — 편집이 아니다
    assert "' data-ed=\"1\"'" in row and "editable && canEdit" in row
    assert "S.cell.col === key ? ' data-cur=\"1\"'" in row        # 다시 그려도 골라진 칸이 남는다
    start = _fn("startCellEdit")
    assert 'td.dataset.ed !== "1"' in start                       # 고칠 수 없는 칸 · 지운 행은 열리지 않는다
    assert "r.deleted || r.removed" in start
    assert 'td.contentEditable = "true"' in start


def test_double_click_opens_the_cell_at_the_click():
    body = _iife("bindGridBody")
    assert 'addEventListener("dblclick"' in body
    assert "startCellEdit(td, { x: ev.clientX, y: ev.clientY })" in body
    assert "caretRangeFromPoint" in _fn("startCellEdit")         # 누른 자리에 커서


def test_enter_tab_escape_while_editing():
    body = _iife("bindGridBody")
    assert "commitAndMove(td, ev.shiftKey ? -1 : 1, 0)" in body  # Enter → 아래 (Shift 위)
    assert "commitAndMove(td, 0, ev.shiftKey ? -1 : 1)" in body  # Tab → 오른쪽 (Shift 왼쪽)
    assert "CELL.cancel = true" in body                          # Esc → 되돌림
    assert "ev.isComposing" in body                              # 한글 조합 중 Enter 는 건드리지 않는다
    end = _fn("endCellEdit")
    assert "td.textContent = CELL.orig" in end and "return false" in end


def test_single_save_path_is_kept():
    body = _iife("bindGridBody")
    assert "const commit = endCellEdit(td)" in body
    assert "if (commit && r) saveEdit(r, td.dataset.col, td)" in body
    keys = _iife("bindGridKeys")
    assert "fetch(" not in keys and "PATCH" not in body           # 칸 저장은 saveEdit → saveField 하나
    assert "saveEdit(r, td.dataset.col, td)" in keys              # 편집 아닐 때의 붙이기도 같은 길


def test_selected_cell_keyboard_like_a_spreadsheet():
    keys = _iife("bindGridKeys")
    assert "gw.tabIndex = 0" in keys
    for k in ("ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"):
        assert k in keys
    assert 'k === "F2"' in keys and 'startCellEdit(td, "end")' in keys
    assert 'startCellEdit(td, "replace")' in keys                 # 바로 타자 · Backspace
    assert 'k === "v" || k === "V"' in keys and "CELL.pasteCommit = true" in keys
    assert 'addEventListener("copy"' in keys and 'addEventListener("paste"' in keys
    assert 'split(/\\r?\\n/)[0].split("\\t")[0]' in keys          # 엑셀 여러 칸 → 첫 칸만


def test_row_arrows_yield_to_cell_arrows():
    i = JS.index("hotfix26")
    # 행 화살표(hotfix26)는 칸 화살표가 받은 키를 다시 쓰지 않는다
    assert "if (ev.defaultPrevented) return;" in JS
    assert "S.cell = null; CELL.editing = null;" in JS            # 결과를 다시 열면 고른 칸을 잊는다
    assert i > 0


def test_look_is_excel_green():
    assert "td[data-cur]" in CSS and "td.editing" in CSS
    assert "#217346" in CSS                                       # 엑셀의 고른 칸 녹색
    assert "td[data-ed] { cursor: cell; }" in CSS
