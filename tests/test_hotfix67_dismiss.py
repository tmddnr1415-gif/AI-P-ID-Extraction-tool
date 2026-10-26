"""hotfix67 — 도면 상자를 눌러 SCT · VENDOR · 둘 다 아님(식별 지우기).

못박는 것:
  1. 상자를 누르면(마크업 모드가 아닐 때) 판이 뜬다 — 저장은 목록 칸과 같은 `saveField`, 지우기는 `deleteRows`
     하나, 되돌리기는 `restoreRow` — 판은 고르기만 한다.
  2. '둘 다 아님' 은 사유 분류 `NOT_SUPPLY` 로 묻지 않고 지운다 (행은 남고 removed · Excel 에서 빠짐).
  3. 서버가 그 분류를 받는다 · 근거 패널과 묶음 판에도 같은 단추.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(rf"(?:async )?function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def test_box_click_opens_the_scope_pop():
    i = JS.index('if (S.markup && it.row !== false) rejectDialog(it);')
    assert "else if (it.row !== false) scopePop(it.key);" in JS[i:i + 200]


def test_pop_only_chooses_and_uses_the_one_save_path():
    pop = _fn("scopePop")
    assert "fetch(" not in pop                                  # 저장은 다른 함수가
    assert 'saveField(row, "scope", SCOPE_DELIVERED)' in pop and "dismissRows([key])" in pop and "restoreRow(key)" in pop
    assert "row.removed" in pop                                 # 지운 것은 되돌리기 판


def test_dismiss_is_delete_with_its_own_class_and_no_prompt():
    d = _fn("dismissRows")
    assert 'klass: "NOT_SUPPLY"' in d and "reason: NOT_SUPPLY_NOTE" in d
    dr = _fn("deleteRows")
    assert "opts.reason !== undefined ? opts.reason" in dr and 'opts.klass || "FALSE_POSITIVE"' in dr
    assert "/rows_delete" in dr and "exclude: true" in dr      # hotfix75 — 요청 하나


def test_same_button_in_the_panel_and_the_multi_panel():
    assert "sc-none" in _fn("scopeEditor") and "dismissRows([row.key])" in _fn("bindScopeEditor")
    assert 'id="mc-none"' in _fn("showMultiScope")
    assert 'document.querySelector("#mc-none")' in JS


def test_server_accepts_the_class_and_keeps_the_row(tmp_path, monkeypatch):
    from app import db, main, markup
    assert "NOT_SUPPLY" in markup.CLASSES
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    row = {"key": "a", "tab": "FIELD", "page_no": 6, "rect": [1, 1, 2, 2], "drawing_no": "D-6",
           "type": "PIT", "qty": 1, "system": "", "valve_type": "", "vendor_supply": "", "scope": "SCT",
           "description": "", "tag_no": "", "needs_review": "", "annotation": "", "evidence": {}}
    db.store_result(con, "j", {"pages": [{"page_no": 6, "drawing_no": "D-6", "title": "t", "page_kind": "PID",
                                          "in_scope": True, "scope_reason": "", "width": 10.0, "height": 10.0}],
                               "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
                               "fingerprint": "f", "rows": [row]})
    main.delete_row("j", "a", reason="SCT 도 VENDOR 도 아님", reason_class="NOT_SUPPLY", author="홍길동", exclude=True)
    r = db.get_row(con, "j", "a")
    assert r is not None and r.get("removed")                   # 지워지지 않고 표시만
    main.restore_row("j", "a")
    assert not db.get_row(con, "j", "a").get("removed")
