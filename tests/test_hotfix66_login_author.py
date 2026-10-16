"""hotfix66 — 편집마다 이름을 묻지 않는다 · 대시보드 로그인 이름으로 자동 기록 · 고친 칸에 이름이 붙는다.

못박는 것:
  1. `askAuthor` 는 이름을 알면(대시보드 `?user=` 가 이긴다 · 다음은 기억된 이름) 줄을 띄우지 않고 바로 돌려준다.
  2. 서버 `/rows` 가 칸마다 마지막으로 고친 사람을 싣는다 (`db.last_editors` — 기록을 읽기만 한다).
  3. 화면이 그 이름을 ✎ 툴팁 · 도면 라벨 · 근거 패널에 붙인다 — 이름은 `editorOf` 하나에서.
  4. 작성자를 안 싣던 Description 저장 길도 이제 싣는다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(rf"(?:async )?function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def test_ask_author_returns_the_known_name_without_a_prompt():
    cur = _fn("currentAuthor")
    assert cur.index("EMBED.user") < cur.index("lastAuthor()")          # 대시보드 로그인이 이긴다
    ask = _fn("askAuthor")
    head = ask[:ask.index("new Promise")]
    assert "const known = currentAuthor();" in head and "Promise.resolve(known)" in head
    # 줄은 이름이 하나도 없을 때만 (처음 한 번) — 그 뒤 기억된다
    assert "rememberAuthor(v)" in ask


def test_dashboard_login_wins_in_every_author_path():
    assert "if (EMBED.user) { S.ftWho = EMBED.user; return EMBED.user; }" in _fn("_ftAuthor")
    assert "if (EMBED.user) { editNotice(" in JS[JS.index('$req("#nav-rename")'):][:400]
    assert 'id="who-chip"' in HTML and "renderWhoChip();" in JS


def test_description_patch_now_carries_the_author():
    sd = JS[JS.index("async function setDescription("):][:1400]
    assert "author: currentAuthor()" in sd


def test_edited_cells_and_labels_name_the_editor():
    assert "stampEditor(row, field, author)" in _fn("saveField")
    assert 'editRowsBulk(rows, "qty", () => value, author)' in JS[JS.index("async function applyQtyToRows("):][:1500]
    assert "stampEditor(r, field, author)" in _fn("editRowsBulk")      # hotfix75 — 묶음 저장의 한 곳
    assert 'stampEditor(r, "qty", author)' in _fn("_saveQtyItems")
    assert "editedTitle(row, field, v)" in _fn("syncRowCell")
    tag = _fn("drawQtyTag")
    assert 'editorOf(row, "qty")' in tag and "ed.author" in tag
    assert "editorOf(row, f)" in JS[JS.index("const mark = (f, v) => wasEdited(f)"):][:200]


def test_rows_carry_the_last_editor_per_field(tmp_path, monkeypatch):
    from app import db, main
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    row = {"key": "a", "tab": "FIELD", "page_no": 6, "rect": [1, 1, 2, 2], "drawing_no": "D-6",
           "type": "PIT", "qty": 2, "system": "", "valve_type": "", "vendor_supply": "", "scope": "SCT",
           "description": "", "tag_no": "", "needs_review": "", "annotation": "",
           "evidence": {"qty_basis": "1 symbol x 2"}}
    db.store_result(con, "j", {"pages": [{"page_no": 6, "drawing_no": "D-6", "title": "t", "page_kind": "PID",
                                          "in_scope": True, "scope_reason": "", "width": 10.0, "height": 10.0}],
                               "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
                               "fingerprint": "f", "rows": [row]})
    import asyncio
    asyncio.run(main.patch_row("j", "a", {"field": "qty", "value": "5", "author": "김철수"}))
    asyncio.run(main.patch_row("j", "a", {"field": "qty", "value": "7", "author": "홍길동"}))
    import json
    out = json.loads(main.rows("j").body)
    eb = out[0]["edited_by"]
    assert eb["qty"]["author"] == "홍길동" and eb["qty"]["at"] > 0          # 마지막으로 고친 사람
    assert db.last_editors(con, "j") == {"a": eb}
