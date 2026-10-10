"""hotfix76 — 위치 메모: 도면의 한 자리에 메모를 달고, 메모를 누르면 그 자리로 가서 표시한다 (Word 메모처럼).

못박는 것:
  1. 저장 — 자리(그 장 PDF 좌표)를 그 장 안으로 맞추고 · 글이 비면 거부 · 고친 글은 이력으로 · 완료/숨김은
     표시일 뿐 지우지 않는다 · 열쇠는 메모장과 같은 도면번호라 다른 Rev 에서 보인다.
  2. API — 장 메모 응답에 `pins` · 종이 크기가 다른 판에서 단 자리는 비례로 옮겨 그린다 · 없는 메모는 404 ·
     장 목록 요약에 열린 위치 메모 수.
  3. 화면 — 위치 메모는 행이 아니라 자기 범례 칸이고(33회차 등식) · 목록에서 누르면 도면이 그 자리로 가고 ·
     도면 깃발을 누르면 목록이 그 메모로 간다.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")

KEY = "1A1Y-00EKG00-M05-0005"


def test_store_clamps_rect_keeps_history_and_never_deletes(tmp_path):
    from app import sheet_memo
    p = sheet_memo.add_pin(tmp_path, "QFE", "jobA", key=KEY, rect=[500, 900, 100, -20], text="  여기 MOV 확인  ",
                           author="홍길동", revision="Rev.A", page_no=10, drawing_no=KEY, page_w=800, page_h=600)
    assert p["rect"] == [100.0, 0.0, 500.0, 600.0]           # 순서 맞춤 · 종이 안으로
    assert p["text"] == "여기 MOV 확인" and p["state"] == "open" and p["id"].startswith("P")
    for bad in ([1, 2, 3], ["a", 1, 2, 3], None, [1, 2, float("nan"), 4]):
        with pytest.raises(ValueError):
            sheet_memo.add_pin(tmp_path, "QFE", "jobA", key=KEY, rect=bad, text="t", author="", revision="",
                               page_no=10, drawing_no=KEY, page_w=800, page_h=600)
    with pytest.raises(ValueError):
        sheet_memo.add_pin(tmp_path, "QFE", "jobA", key=KEY, rect=[0, 0, 1, 1], text="   ", author="",
                           revision="", page_no=10, drawing_no=KEY, page_w=800, page_h=600)
    sheet_memo.update_pin(tmp_path, "QFE", "jobB", keys=[KEY], pin_id=p["id"], author="김철수",
                          revision="Rev.B", text="MOV 둘 다 GTG 공급")
    sheet_memo.update_pin(tmp_path, "QFE", "jobB", keys=[KEY], pin_id=p["id"], author="김철수",
                          revision="Rev.B", state="hidden")
    got = sheet_memo.pins(sheet_memo.load(tmp_path, "QFE", "jobX"), [KEY])
    assert len(got) == 1 and got[0]["text"] == "MOV 둘 다 GTG 공급" and got[0]["state"] == "hidden"
    assert got[0]["history"][0]["text"] == "여기 MOV 확인"      # 앞 글은 이력으로
    assert got[0]["history"][1]["to"] == "hidden"               # 숨김도 기록 — 지우지 않는다
    with pytest.raises(KeyError):
        sheet_memo.update_pin(tmp_path, "QFE", "jobB", keys=[KEY], pin_id="nope", author="", revision="", state="open")
    with pytest.raises(ValueError):
        sheet_memo.update_pin(tmp_path, "QFE", "jobB", keys=[KEY], pin_id=p["id"], author="", revision="", state="gone")
    # 메모장(한 장 한 판)과 섞이지 않는다
    assert sheet_memo.entries(sheet_memo.load(tmp_path, "QFE", "jobX"), [KEY]) == []


def _job(con, db, job_id, page_w, page_h, revision):
    db.create_job(con, job_id, "qfe.pdf", "sha" + job_id, Path("/nonexistent.pdf"))
    db.store_result(con, job_id, {
        "pages": [{"page_no": 10, "drawing_no": KEY, "title": "t", "page_kind": "PID", "in_scope": True,
                   "scope_reason": "", "width": page_w, "height": page_h}],
        "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}}, "fingerprint": "f", "rows": []})
    con.execute("UPDATE job SET project=?, revision=? WHERE id=?", ("QFE", revision, job_id))
    con.commit()


def test_api_round_trip_scales_other_paper_and_counts(tmp_path, monkeypatch):
    from fastapi import HTTPException
    from app import db, main
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    monkeypatch.setattr(main, "DATA_DIR", tmp_path)
    monkeypatch.setattr(main, "_note_aliases", lambda project: {})
    _job(con, db, "A", 1191.0, 842.0, "Rev.A")        # A3
    _job(con, db, "B", 2382.0, 1684.0, "Rev.B")       # 같은 도면번호 · A1

    v = main.add_memo_pin("A", 10, {"rect": [100, 200, 150, 260], "text": "PIT 확인", "author": "홍길동"})
    assert len(v["pins"]) == 1
    pin = v["pins"][0]
    assert pin["rect"] == [100, 200, 150, 260] and pin["here"] and not pin["scaled"] and not pin["other_rev"]

    w = main.page_memo("B", 10)                        # 다른 Rev · 종이 두 배
    assert w["pins"][0]["rect"] == [200.0, 400.0, 300.0, 520.0]
    assert w["pins"][0]["scaled"] and w["pins"][0]["other_rev"] and not w["pins"][0]["here"]

    x = main.update_memo_pin("B", 10, pin["id"], {"state": "resolved", "author": "김철수"})
    assert x["pins"][0]["state"] == "resolved" and x["pins"][0]["state_by"] == "김철수"
    assert "10" not in main.job_memos("A")["pages"]                # 열린 것만 센다 (메모장도 없으면 장이 안 뜬다)
    main.update_memo_pin("A", 10, pin["id"], {"state": "open"})
    assert main.job_memos("A")["pages"]["10"]["pins"] == 1

    for bad, code in (({"rect": [1, 2], "text": "t"}, 400), ({"rect": [1, 2, 3, 4], "text": ""}, 400)):
        with pytest.raises(HTTPException) as e:
            main.add_memo_pin("A", 10, bad)
        assert e.value.status_code == code
    with pytest.raises(HTTPException) as e:
        main.update_memo_pin("A", 10, "P-none", {"state": "open"})
    assert e.value.status_code == 404
    with pytest.raises(HTTPException) as e:
        main.update_memo_pin("A", 10, pin["id"], {})
    assert e.value.status_code == 400
    with pytest.raises(HTTPException) as e:
        main.add_memo_pin("A", 99, {"rect": [1, 2, 3, 4], "text": "t"})
    assert e.value.status_code == 404


def _fn(name):
    i = JS.index(f"function {name}(")
    return JS[i:JS.index("\n}\n", i) + 2]


def test_screen_links_note_and_place_both_ways():
    assert 'id="memo-pin"' in HTML and 'id="pin-list"' in HTML and 'id="pin-note"' in HTML
    sel = _fn("selectPin")
    assert "if (!opts.fromDrawing) focusPin(p);" in sel          # 목록에서 → 도면이 그 자리로
    assert "showPinPop(p)" in sel                               # 자리 옆 말풍선
    draw = _fn("drawPins")
    assert "selectPin(p.id, { fromDrawing: true })" in draw      # 도면 깃발 → 목록의 그 메모
    focus = _fn("focusPin")
    assert "scrollTo(" in focus and "S.pinFlash" in focus          # hotfix77 — 두 번 깜박임은 시각으로
    # 위치 메모는 행이 아니다 — SCOPE 색 칸에 섞지 않고 자기 범례 칸 (33회차 등식)
    legend = _fn("buildOverlayLegend")
    assert "row(...PIN_MARK" in legend
    assert "counts[" not in draw
    # 그리기는 오버레이 맨 위 · 범례에서 끌 수 있다
    assert "drawPins(ov, scale);" in _fn("drawOverlay")
    assert "S.ovOff.has(PIN_MARK[0])" in draw
    # 자리 긋기는 마크업과 같은 고무줄 · 그 클릭이 아래 상자를 고르지 않는다
    assert "if (S.pinMode) {" in JS[JS.index("async function _rubberEnd("):]
    assert "S.pinJust" in JS
    # 저장 길은 둘뿐 — 새로 달기 · 고치기/상태
    assert JS.count("/memo/${pageNo}/pins") == 2


def test_pin_add_returns_through_the_same_page_view():
    from app import main
    src = Path(main.__file__).read_text(encoding="utf-8")
    body = src[src.index("def add_memo_pin("):src.index("def update_memo_pin(")]
    assert "return page_memo(job_id, page_no)" in body          # 화면은 메모장과 같은 응답 하나를 읽는다
    assert "_pin_view(" in src[src.index("def page_memo("):src.index("def _page_size(")]
