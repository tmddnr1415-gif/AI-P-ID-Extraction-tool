"""hotfix59 — 도면의 `x N` 라벨로 승수(Q'ty)를 고친다: 이 태그만 · 이 페이지 전체 · Shift 로 묶은 범위.

화면 코드라 소스로 지킨다.  눌러서 확인한 것은 `spike/ui_audit_qty_scope.py` → `out/hotfix59/ui/`.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    i = JS.index(f"function {name}(")
    j = JS.index("\nfunction ", i + 1)
    return JS[i:j]


def test_popover_offers_this_tag_this_page_and_the_shift_range():
    body = _fn("editQtyOnDrawing")
    for scope in ('data-scope="one"', 'data-scope="page"', 'data-scope="multi"', 'data-scope="cancel"'):
        assert scope in body
    assert "pageQtyRows(row.page_no)" in body and "multiRows()" in body
    # 오버레이가 다시 그려져도 판은 지금 그려진 라벨에 붙는다
    assert 'g.qtytag[data-key=' in body


def test_page_scope_is_the_rows_that_carry_a_label():
    body = _fn("pageQtyRows")
    assert "r.page_no === pageNo" in body and "!r.deleted" in body and "!r.removed" in body


def test_label_click_routes_shift_and_range():
    body = _fn("drawQtyTag")
    assert "isAddClick(ev)" in body and "toggleMulti(it.key)" in body
    assert "S.multi.has(it.key)" in body and "{ multi: true }" in body


def test_one_save_path_updates_both_sides():
    save = _fn("applyQtyToRows")
    assert 'field: "qty"' in save and save.count("askAuthor(") == 1      # 작성자는 한 번만
    assert "renderGrid()" in save and "drawOverlay()" in save
    assert 'value === "" ? (r.ai || {}).qty' in save                      # 비우면 도면 값


def test_right_panel_range_has_the_same_control():
    body = _fn("showMultiScope")
    assert 'id="mq-val"' in body and "applyQtyToRows(" in body


def test_labels_are_raised_above_every_box():
    body = _fn("drawOverlay")
    assert 'querySelectorAll("g.qtytag").forEach(g => ov.appendChild(g))' in body
