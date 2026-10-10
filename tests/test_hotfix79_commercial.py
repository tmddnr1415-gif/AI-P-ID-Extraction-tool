"""hotfix79 — 상용 수준 다듬기: 가볍게(고른 것 · 고친 것만 다시 그림) · 되돌리기 · 칸 범위 · 단축키.

화면 동작은 띄워서 맞댄다 — `spike/ui_audit_overlay_incr.py`(고친 것만 다시 그린 그림 = 전부 다시 그린 그림)
· `spike/ui_audit_convenience.py`(Ctrl+Z/Y · Shift+↓ 범위 · Ctrl+Enter · 여러 줄 붙이기 · Delete · ?).
여기는 그 길이 소스에서 지켜지는지만 본다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(r"(?:async )?function " + re.escape(name) + r"\(", JS)
    assert m, name
    nxt = re.search(r"\n(?:async )?function \w+\(", JS[m.end():])
    return JS[m.start(): m.end() + (nxt.start() if nxt else 4000)]


# ── 가볍게 ────────────────────────────────────────────────────────────────
def test_selection_does_not_rebuild_the_overlay():
    """행을 고르는 길에서 오버레이 전체를 다시 만들지 않는다 (칠하기가 행 누르기 시간의 대부분이었다)."""
    for name in ("select", "deselect", "toggleMulti", "clearMulti", "applySel"):
        body = _fn(name)
        assert "drawOverlay()" not in body, name
        assert "refreshSel()" in body, name


def test_refresh_sel_falls_back_when_the_overlay_is_another_page():
    body = _fn("refreshSel")
    assert "ov.dataset.page !== String(S.page.page_no)" in body and "drawOverlay(); return;" in body
    assert "drawTrace(trG, scale)" in body and "drawFromTo(ftG, scale)" in body


def test_one_item_is_drawn_by_one_function():
    """전부 그릴 때와 몇 개만 다시 그릴 때가 같은 함수를 쓴다 — 두 벌을 두면 갈린다."""
    assert "drawItem(ov, scale, it);" in _fn("drawOverlay")
    assert "drawItem(ov, scale, it);" in _fn("restyleItems")
    assert "n.dataset.own = it.key" in _fn("drawItem")


def test_edits_redraw_only_the_edited_rows():
    assert "restyleItems([row.key])" in _fn("saveField")
    for name in ("applyScopeToMulti", "applyQtyToRows", "_saveQtyItems", "fillCells", "_applyEdits"):
        body = _fn(name)
        assert "restyleItems(" in body and "drawOverlay()" not in body, name


def test_pins_redraw_alone():
    assert "redrawPins();" in _fn("showMemo") and "drawOverlay()" not in _fn("showMemo")
    body = _fn("redrawPins")
    assert '[data-pin]' in body and "drawPins(ov" in body and "buildOverlayLegend()" in body


def test_arrow_keys_select_the_row_after_they_stop():
    body = _fn("gotoCell")
    assert "setTimeout(" in body and "KEY_SELECT_MS" in body and "clearTimeout(gotoCell._t)" in body
    assert 'classList.add("sel")' in body                       # 목록의 행 표시는 바로


# ── 되돌리기 ──────────────────────────────────────────────────────────────
def test_every_write_path_records_undo():
    for name in ("saveField", "editRowsBulk", "_saveQtyItems", "deleteRows", "restoreRow"):
        assert "undoRecord(" in _fn(name), name
    # 기록하는 값은 사람 값 (빈 값 = 도면 값) — 엔진 값은 건드리지 않는다
    assert "_userVal(row, field)" in _fn("saveField")


def test_undo_writes_through_the_same_paths():
    body = _fn("undoStep") + _fn("_applyEdits")
    assert "saveField(" in body and "editRowsBulk(" in body
    assert "deleteRows(" in body and "_restoreKeys(" in body
    assert "fetch(" not in body                                  # 저장 길을 새로 만들지 않는다
    assert "UNDO.busy" in _fn("undoRecord")                      # 되돌리는 동안은 기록하지 않는다


def test_undo_is_per_result_and_spares_text_fields():
    assert "UNDO.job !== id" in _fn("_undoJob")
    i = JS.index('if (k !== "z" && k !== "y") return;')
    assert "t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName)" in JS[i:i + 400]
    assert 'id="undo-btn"' in HTML and 'id="redo-btn"' in HTML


# ── 칸 범위 · 붙이기 · Delete ─────────────────────────────────────────────
def test_range_is_one_column_and_painted_from_state():
    assert 'S.cellRange.col === key && S.rangeKeys && S.rangeKeys.has(r.key)' in _fn("rowHtml")
    assert "if (!opts.keepRange && S.cellRange) clearRange();" in _fn("setCell")
    assert "td[data-rng]" in CSS


def test_range_keys():
    i = JS.index("(function bindGridKeys()")
    keys = JS[i:JS.index("\n})();", i)]
    assert 'extendRange(k === "ArrowDown" ? 1 : -1)' in keys
    assert 'k === "Delete"' in keys and "revertCells()" in keys
    assert "pasteValues(raw)" in keys
    assert 'rng.map(r => String(cellValue(r, S.cell.col) ?? "")).join("\\n")' in keys


def test_fill_skips_deleted_rows_and_uses_bulk_save():
    body = _fn("fillCells")
    assert "!r.deleted && !r.removed && !r.delCand" in body
    assert "editRowsBulk(rows, col" in body and "saveField(pairs[0][0], col" in body
    assert "fetch(" not in body


def test_shortcut_help_lists_the_new_keys():
    i = JS.index("const SHORTCUTS = [")
    table = JS[i:JS.index("];", JS.index('["메모", [', i))]
    for k in ("Ctrl + Z", "Shift + ↑ ↓", "Ctrl + Enter (편집 중)", "Delete", "F2"):
        assert k in table, k
    assert 'id="kbd-btn"' in HTML


# ── 닫기 전에 묻기 ───────────────────────────────────────────────────────
def test_close_guard_asks_only_when_something_is_unsaved():
    i = JS.index('window.addEventListener("beforeunload"')
    body = JS[i:i + 400]
    assert "CELL.editing.textContent !== CELL.orig" in body       # 편집 중인 칸에 바뀐 글자
    assert "NET.writing > 0" in body                              # 서버에 쓰는 요청이 아직 날아가는 중
    assert "if (!typing && !(NET.writing > 0)) return;" in body   # 아무것도 없으면 묻지 않는다
    hook = JS[JS.index("(function hookFetch()"):JS.index("(function hookFetch()") + 1500]
    assert "NET.writing = (NET.writing || 0) + 1" in hook and "p.finally(" in hook
