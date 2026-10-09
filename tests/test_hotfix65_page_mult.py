"""hotfix65 — 수량 승수 판의 '페이지별 승수': 여러 장을 고르고 장마다 승수를 적어 **지금 결과의
Q'ty 가 바로** 바뀐다.

못박는 것:
  1. 서버(`POST /jobs/{id}/qty_bulk`)는 PATCH 와 같은 db 함수로 적기만 한다 — 다시 계산하지
     않고, 추출값(`ai`)을 건드리지 않고, 편집 이력에 작성자·사유가 남고, 빈 값은 도면 값으로.
  2. 새 Q'ty = 기본 개수 × 승수 — 기본 개수는 엔진 근거(`N symbol x F`)에서 읽는다 (화면 한 곳).
  3. 저장은 요청 하나 · 작성자 한 번 · 뒤에 목록과 도면을 같은 값에서 다시 그린다.
  4. 유닛코드 승수(다음 분석부터)는 그대로 남는다 — 다른 길이다.
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _row(key, page, qty, basis):
    return {"key": key, "tab": "FIELD", "page_no": page, "rect": [10, 10, 30, 40],
            "drawing_no": f"D-{page}", "type": "PIT", "qty": qty, "system": "", "valve_type": "",
            "vendor_supply": "", "scope": "SCT", "description": "", "tag_no": "",
            "needs_review": "", "annotation": "", "evidence": {"qty_basis": basis}}


def _job(tmp_path, monkeypatch):
    from app import db, main
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", {
        "pages": [{"page_no": n, "drawing_no": f"D-{n}", "title": "t", "page_kind": "PID",
                   "in_scope": True, "scope_reason": "", "width": 10.0, "height": 10.0} for n in (6, 7)],
        "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [_row("a", 6, 2, "1 symbol x 2 (NOTES: 11, 12)"),
                 _row("b", 6, 8, "1 symbol x 2 (NOTES: 10, 20) x 4 (( D ) 상세 한 벌 × 본문 표식 4개)"),
                 _row("c", 7, 1, "1 symbol x 1 (unit code 00, CONFIG_FALLBACK)")]})
    return con, main, db


def test_bulk_writes_like_patch_and_never_touches_the_extracted_value(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    out = asyncio.run(main.qty_bulk("j", {"author": "홍길동", "items": [
        {"key": "a", "value": 3, "reason": "PAGE_MULTIPLIER: p6 x3"},
        {"key": "b", "value": "12", "reason": "PAGE_MULTIPLIER: p6 x3"},
        {"key": "zz", "value": 5}]}))
    assert set(out["users"]) == {"a", "b"}               # 없는 행은 건너뛴다
    a, b = db.get_row(con, "j", "a"), db.get_row(con, "j", "b")
    assert (a["user"]["qty"], b["user"]["qty"]) == (3, 12)
    assert (a["ai"]["qty"], b["ai"]["qty"]) == (2, 8)    # 추출값 그대로
    hist = db.row_edit_history(con, "j", "a")
    assert hist and hist[-1]["author"] == "홍길동" and "PAGE_MULTIPLIER: p6 x3" in json.dumps(hist[-1], ensure_ascii=False)
    # 빈 값 = 도면 값으로 (PATCH 와 같은 규칙)
    asyncio.run(main.qty_bulk("j", {"author": "홍길동", "items": [{"key": "a", "value": ""}]}))
    assert "qty" not in (db.get_row(con, "j", "a")["user"] or {})


def test_bulk_rejects_non_integers(tmp_path, monkeypatch):
    from fastapi import HTTPException
    con, main, db = _job(tmp_path, monkeypatch)
    for bad in ("x2", -1):
        with pytest.raises(HTTPException):
            asyncio.run(main.qty_bulk("j", {"items": [{"key": "a", "value": bad}]}))
    assert "qty" not in (db.get_row(con, "j", "a")["user"] or {})   # 하나도 안 적었다
    with pytest.raises(HTTPException):
        asyncio.run(main.qty_bulk("j", {"items": []}))


def test_the_server_only_writes_what_the_screen_computed():
    body = MAIN[MAIN.index("async def qty_bulk("):MAIN.index('@app.get("/jobs/{job_id}/rows/{key}/history")')]
    # hotfix75 — PATCH · qty_bulk · rows_edit 가 같은 `_edit_one` 을 부른다
    assert "_edit_one(" in body
    one = MAIN[MAIN.index("def _edit_one("):MAIN.index('@app.delete("/jobs/{job_id}/rows/{key}")')]
    assert "db.set_user_value(" in one and "db.record_feedback(" in one
    assert "qty_basis" not in body and "multiplier" not in body   # 다시 계산하지 않는다


def _fn(name):
    m = re.search(rf"function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def test_base_count_comes_from_the_engines_basis():
    """Typical 상세 한 벌(x4)은 승수가 아니라 남는다 · 근거를 못 읽으면 1."""
    src = _fn("qtyBase") + """
const rows = [
  {ai: {qty: 2}, evidence: {qty_basis: "1 symbol x 2 (NOTES: 11, 12)"}},
  {ai: {qty: 8}, evidence: {qty_basis: "1 symbol x 2 (NOTES: 10, 20) x 4 (( D ) 상세 한 벌)"}},
  {ai: {qty: 2}, evidence: {qty_basis: "맞닿은 신호 버블 3개 = 물리 기기 1개; Q'ty 는 1 x 시트 승수 2"}},
  {ai: {qty: null}, evidence: {qty_basis: "1 symbol x 1 (unit code 30 — 승수 미상)"}},
  {ai: {qty: 3}, evidence: {qty_basis: "1 point x 3 (Typical 'D' 부품 점)"}},
];
console.log(JSON.stringify(rows.map(qtyBase)));"""
    out = subprocess.run(["node", "-e", src], capture_output=True, text=True, timeout=30)
    if out.returncode != 0 and "not found" in (out.stderr or ""):
        pytest.skip("node 없음")
    assert json.loads(out.stdout) == [1, 4, 1, 1, 1]


def test_apply_is_one_request_one_author_and_redraws_both_sides():
    save = _fn("_saveQtyItems")
    assert save.count("askAuthor(") == 1 and save.count("fetch(") == 1 and "/qty_bulk`" in save
    assert "renderGrid();" in save and "drawOverlay();" in save   # 오른쪽 목록 · 왼쪽 라벨 같은 값
    plan = _fn("pageMultPlan")
    assert "qtyBase(r) * m" in plan                       # Q'ty = 기본 개수 × 승수
    ui = _fn("renderPageMult")
    assert "ev.shiftKey" in ui and "st.last" in ui        # Shift 로 사이의 장
    assert "st.checked.add(no)" in ui                     # 칸에 적으면 그 장이 골라진다
    assert '"pm-fill' in ui or "pm-fill" in ui            # 고른 장에 같은 값


def test_panel_shows_even_without_unit_groups_and_keeps_the_unit_path():
    lm = re.search(r"async function loadMultipliers\(.*?\n}\n", JS, re.S).group(0)
    assert "renderPageMult(box)" in lm
    assert "!groups.length && !hasRows" in lm             # 유닛 승수가 없는 문서에도 보인다
    assert "/multipliers`, { method: \"POST\", body }" in lm   # 유닛코드 승수(다음 분석부터)는 그대로
    assert "다음 분석부터" in lm
    # 다른 길(라벨 · 목록 칸 · 카드)로 Q'ty 가 바뀌어도 판이 같은 값을 말한다
    assert "_refreshPageMult();" in _fn("applyQtyToRows")
    assert 'if (field === "qty") _refreshPageMult();' in JS
    assert '"pageMult"' in JS[JS.index("const VIEW_KEYS"):][:600]
