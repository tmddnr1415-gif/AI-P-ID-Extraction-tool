"""hotfix94 — Shift 로 묶은 범위 안의 상자를 Shift + 왼쪽 클릭하면 SCT · VENDOR · 둘 다 아님 판이 묶음 전체에.

사용자: *"키보드 Shift 로 범위를 지정하고 Shift 를 누른 상태에서 마우스 왼쪽을 클릭하면 이 화면이 뜨게 하고
그 결과는 Shift 로 범위 지정된 식별된 계기에 모두 일괄 적용 및 추출 List 도 반영되게"*.
판은 고르기만 하고 저장은 묶음 판과 같은 길(`applyScopeToMulti` · `dismissRows` · `_restoreKeys`) 이다.
화면 자기검증: `spike/ui_audit_shift_group.py` (띄워서 누른다).
"""
from pathlib import Path
import re

JS = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")


def _body(name):
    i = JS.index(f"function {name}(")
    j = JS.index("\n}\n", i)
    return JS[i:j]


def test_shift_click_inside_selection_opens_group_pop_before_toggling():
    i = JS.index("r.onclick = (ev) => {")
    blk = JS[i:i + 1500]
    g = blk.index("scopePopGroup(it.key)")
    t = blk.index("toggleMulti(it.key)")
    assert g < t, "묶음 안 Shift + 클릭이 묶음에서 빼기보다 먼저 판을 열어야 한다"
    cond = blk[:g]
    for need in ("ev.shiftKey", "!ev.ctrlKey", "S.multi.size > 1", "S.multi.has(it.key)", "!S.markup"):
        assert need in cond, need


def test_group_pop_saves_through_the_bulk_paths_only():
    body = _body("scopePopGroup")
    assert "applyScopeToMulti(SCOPE_DELIVERED)" in body
    assert "applyScopeToMulti(name ?" in body
    assert "dismissRows(live.map(r => r.key))" in body
    assert "_restoreKeys(keys)" in body
    assert "fetch(" not in body, "판은 서버를 직접 부르지 않는다 — 묶음 판과 같은 길로"


def test_bulk_scope_skips_removed_rows():
    body = _body("applyScopeToMulti")
    assert re.search(r"multiRows\(\)\.filter\(r => !r\.removed && !r\.deleted\)", body)


def test_shortcut_help_names_the_new_gesture():
    assert "Shift + 고른 상자 누름" in JS and "Ctrl + 고른 상자 누름" in JS
