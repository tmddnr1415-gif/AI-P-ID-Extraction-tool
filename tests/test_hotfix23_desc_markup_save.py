"""hotfix23 — Description From/To 마크업 · 최종 저장.

사용자: *"From 마크업을 해서 범위를 지정하면 그 범위에 있는 description 을 따고 … To …
하나만 마크업하더라도 그 Description 이 나타나면 된다"* · *"최종 저장 버튼을 누르면 최초
출력 프로그램 page 에서 해당 프로젝트가 언제 누구에 의해 저장되어 업데이트되었는지"*.
"""
from __future__ import annotations
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import axis_overrides, db  # noqa: E402


def test_one_side_is_enough_for_a_sentence():
    assert axis_overrides.sentence_for("FROM HRSG#12", "", "PIT") == "FROM HRSG#12 PRESSURE TRANSMITTER"
    assert axis_overrides.sentence_for("", "TO HRSG#12 BD TANK", "PIT") == "TO HRSG#12 BD TANK PRESSURE TRANSMITTER"
    assert (axis_overrides.sentence_for("FROM HRSG#12", "TO HRSG#12 BD TANK", "PIT")
            == "FROM HRSG#12 TO HRSG#12 BD TANK PRESSURE TRANSMITTER")
    assert axis_overrides.sentence_for("", "", "PIT") == ""


def test_text_in_a_drawn_box_is_read_in_line_order_without_drawing_numbers():
    from app import main
    words = [((100, 10, 120, 14), "FROM"), ((122, 10, 150, 14), "HRSG#12"),
             ((100, 20, 190, 24), "1A46-10LBA10-M05-0001"),      # 도면번호 줄은 뺀다
             ((100, 30, 110, 34), "(C-2)"),
             ((300, 10, 320, 14), "OUTSIDE")]
    got = main._text_in_rect(words, [95, 5, 200, 40])
    assert got["text"] == "FROM HRSG#12"
    assert "1A46-10LBA10-M05-0001" in got["dropped"]
    assert main._text_in_rect(words, [500, 500, 600, 600])["text"] == ""


def test_save_is_logged_with_who_when_and_how_much(tmp_path):
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "p.pdf", "sha", tmp_path / "p.pdf")
    db.store_result(con, "j", {
        "pages": [], "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
        "fingerprint": "f",
        "rows": [{"key": "k1", "tab": "FIELD", "page_no": 1, "rect": [0, 0, 1, 1], "drawing_no": "D",
                  "type": "PI", "qty": 1, "system": "", "valve_type": "", "vendor_supply": "",
                  "scope": "SCT", "description": "", "tag_no": "", "needs_review": "",
                  "annotation": "", "evidence": {}}]})
    assert db.last_save(con, "j") is None
    db.set_user_value(con, "j", "k1", "description", "FROM X PRESSURE INDICATOR")
    sv = db.record_save(con, "j", "홍길동")
    assert sv["author"] == "홍길동" and sv["edits"] == 1 and sv["at"] <= time.time()
    time.sleep(0.01)
    db.record_save(con, "j", "")
    assert db.last_save(con, "j")["author"] == ""                # 이름은 지어내지 않는다
    assert "save_log" in db._JOB_TABLES                           # 분석을 지우면 같이 지워진다


def test_home_carries_the_last_save_and_the_screen_shows_it():
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '"last_save": db.last_save(CON, job["id"])' in src
    assert 'j["last_save"] = db.last_save(CON, j["id"])' in src
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "function saveWords" in js and "p.last_save" in js and "getElementById(\"save-final\")" in js
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert 'id="save-final"' in html


def test_markup_confirm_does_not_need_both_sides():
    import inspect
    from app import main
    src = inspect.getsource(main.confirm_axis)
    assert 'via == "markup"' in src and "author=author" in src
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    # 긋는 동안 도면이 끌려 가면 끝점이 틀어진다 — 팬·띠 선택이 이 모드를 안다
    assert "S.markup || S.ftMark || ev.shiftKey" in js
