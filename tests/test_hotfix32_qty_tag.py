"""hotfix32 — 식별 표기 옆의 수량 `x N` · 도면 위에서 고친 값이 목록에 ✎ 와 함께 반영.

화면 코드라 소스로 지키는 것 셋:
  ① 도면 라벨의 값은 그리드와 **같은 접근자**(`cellValue(row, "qty")`)에서 온다
  ② 도면 위 편집은 그리드와 **같은 저장 길**(`saveEdit(row, "qty", …)`)로 간다 — PATCH 를
     따로 부르지 않는다 (두 벌을 두면 갈린다)
  ③ 범례 칸(`QTY_MARK`)이 있고, 그리드 칸이 `data-col` 로 자기 열을 말한다 (도면 쪽이 같은 칸을 찾는다)
눌러서 확인한 것은 `spike/ui_audit_qty.py` · `out/hotfix32/ui/README.md`.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    i = JS.index(f"function {name}(")
    j = JS.index("\nfunction ", i + 1)
    return JS[i:j]


def test_the_label_reads_qty_through_the_grid_accessor():
    body = _fn("drawQtyTag")
    assert 'cellValue(row, "qty")' in body
    assert "row.values.qty" not in body          # 접근자를 우회하지 않는다


def test_editing_on_the_drawing_uses_the_grid_save_path_only():
    """hotfix59 — 도면 편집은 범위(이 태그 · 이 페이지 · Shift 묶음)를 고르는 판이 됐고, 저장은
    `applyQtyToRows` 한 곳이 그리드와 같은 PATCH(`field: "qty"`)로 한다.  판 자체는 PATCH 를 모른다."""
    body = _fn("editQtyOnDrawing")
    assert "fetch(" not in body and "PATCH" not in body
    assert "applyQtyToRows(" in body
    save = _fn("applyQtyToRows")
    assert 'field: "qty"' in save and "askAuthor(" in save
    assert "renderGrid()" in save and "drawOverlay()" in save   # 왼쪽·오른쪽 같은 값으로


def test_legend_has_its_own_toggle_and_it_is_a_mark_not_a_colour_cell():
    assert re.search(r'const QTY_MARK = \["QTY", "수량 x N \(그중\)"', JS)
    assert "row(...QTY_MARK, qtyTags, \"badge\")" in JS
    assert "S.ovOff.has(QTY_MARK[0])" in _fn("drawOverlay")


def test_grid_cells_say_their_column():
    body = _fn("renderGrid")
    assert "td.dataset.col = key;" in body


def test_edited_label_shares_the_grid_pencil():
    assert 'edited ? " ✎" : ""' in _fn("drawQtyTag")
    assert "g.qtytag.edited text { fill: var(--ok); }" in CSS
    assert "td.edited::after { content: \" ✎\"" in CSS
