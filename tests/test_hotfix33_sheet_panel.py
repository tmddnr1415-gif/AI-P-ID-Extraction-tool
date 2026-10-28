"""hotfix33 — 장 도면번호 지정 **화면**과 DXF 경로의 PIT/PI 접기·게이지.

45회차가 저장·엔진·API 를 두고 *"패널은 다음 회차"* 라고 적어 둔 자리(§7 코드 지도 ·
47회차 [9] "UAD s28~s34 는 … 화면 패널이 아직 없습니다")를 닫는다.  규율은 승수 판과
같다 — 서버가 낸 목록만 보이고(읽힌 장은 서버가 빼므로 화면이 다시 가르지 않는다) ·
작성자는 `askAuthor` 로 · 저장은 있던 API 하나 · "다시 분석해야" 는 판에 상주한다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
DXF = (ROOT / "app" / "dxf_pipeline.py").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    m = re.search(rf"async function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def test_the_panel_exists_and_is_loaded_with_the_review_panel():
    assert 'id="sheet-panel"' in HTML
    assert "loadSheetNumbers();" in JS
    # 승수 판과 같은 자리에서 같이 불린다 — 결과 화면이 열릴 때마다.
    body = re.search(r"function renderReviewPanel\(.*?\n}\n", JS, re.S).group(0)
    assert "loadMultipliers();" in body and "loadSheetNumbers();" in body


def test_the_panel_reads_and_writes_the_existing_api_only():
    fn = _fn("loadSheetNumbers")
    assert "/sheet_numbers`" in fn and 'method: "POST"' in fn and 'method: "DELETE"' in fn
    # 저장 경로는 45회차 API 하나 — 다른 경로로 적지 않는다.
    assert "/rows" not in fn and "PATCH" not in fn
    # 작성자는 13회차 규율대로 askAuthor 가 묻는다.
    assert "askAuthor(" in fn
    # 폼 필드 이름은 서버 서명과 같다.
    for f in ('"page"', '"drawing_no"', '"author"', '"note"'):
        assert f in fn, f


def test_the_screen_does_not_decide_which_sheets_are_targets():
    """읽힌 장은 **서버**가 뺀다 (`_sheet_number_targets`).  화면이 `drawing_no` 로 다시
    가르면 두 벌이 되고 언젠가 갈린다."""
    fn = _fn("loadSheetNumbers")
    assert "out.sheets" in fn
    assert re.search(r"filter\(\s*\w+\s*=>\s*!\w+\.drawing_no", fn) is None


def test_the_pending_fact_lives_in_the_panel_not_only_in_a_notice():
    fn = _fn("loadSheetNumbers")
    assert "mpending" in fn and "다시 분석하면" in fn
    # 이번 분석이 이미 사람 값으로 읽은 장에는 "아직 반영 안 됨" 을 말하지 않는다.
    assert "sh.from_user ? \"\" :" in fn


def test_typed_values_are_attribute_safe():
    fn = _fn("loadSheetNumbers")
    assert "attr(set ? (set.drawing_no" in fn and "attr(set ? (set.note" in fn
    assert "const attr = " in JS and "&quot;" in JS


def test_dxf_path_folds_readouts_with_the_same_function_after_the_tags():
    """hotfix31 의 규칙(PIT ⊃ PI 접기 · 표시기만 있는 라인은 게이지)이 DXF 에도 — 함수는
    PDF 경로의 `_fold_readouts` **하나**이고 태그를 붙인 뒤 한 곳에서 부른다."""
    assert DXF.count("P._fold_readouts(") == 1
    assert DXF.index("_attach_tags(rows, targets, declared_mode)") < DXF.index("P._fold_readouts(")
    assert '"readouts": readout_facts' in DXF
    # 표가 없으면(isa_ok 거짓) None 을 넘겨 아무 것도 접지 않는다.
    assert "isa if isa_ok else None" in DXF.split("P._fold_readouts(")[1][:60]


def _result(pages):
    return {"pages": [{"page_no": n, "drawing_no": d, "title": "T", "page_kind": k,
                       "in_scope": bool(d), "scope_reason": "", "width": 10.0, "height": 10.0}
                      for n, d, k in pages],
            "layers": {}, "rows": [], "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
            "fingerprint": "f",
            "user_sheet_numbers": {"table": {3: "D-3"}, "who": {3: "감사"}}}


def test_the_targets_come_from_the_stored_pages_of_a_real_job(tmp_path, monkeypatch):
    """★ 45회차의 API 는 `engine_json["pages"]` 를 읽었는데 그 열쇠는 저장 화이트리스트에
    없다 — 실제 분석에서는 **언제나 빈 목록**이었다 (hotfix33 화면 자기검증이 잡았다).
    장 목록은 `/pages` 와 같은 `pid_page` 표에서 온다."""
    from app import db, main
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", _result([(1, "D-1", "PID"), (2, "", "UNKNOWN"), (3, "D-3", "PID")]))
    out = main._sheet_number_targets("j")
    pages = {s["page_no"]: s for s in out["sheets"]}
    assert 2 in pages and 1 not in pages, "읽힌 장은 자리를 내지 않는다 · 못 읽은 장만"
    assert pages[2]["from_user"] is False
    # 사람이 적어 채워진 장은 되돌릴 수 있게 낸다 — 그 사실은 저장된 `user_sheet_numbers` 가 말한다.
    assert 3 in pages and pages[3]["from_user"] is True
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    body = src[src.index("def _sheet_number_targets"):src.index("def _user_title_block")]
    assert "FROM pid_page" in body
    assert '"user_sheet_numbers"' in (ROOT / "app" / "db.py").read_text(encoding="utf-8")
