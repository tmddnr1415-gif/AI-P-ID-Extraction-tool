"""13회차 — 개정 판별과 편집 승계.

지키는 것은 셋이다:
  · **추출값 층은 편집이 닿지 않는다.**  지문·축1·축2·Q'ty 축이 그 층만 읽으므로
    이것이 깨지면 회귀 검사 체계 전체가 무의미해진다.
  · **승계는 빈 자리를 채우는 것이지 덮어쓰는 것이 아니다.**
  · **못 읽은 개정은 추정하지 않는다.**  대표값 규칙은 도면에서 유도되지 않아
    config 에 있고, 그 사실이 코드 주석과 config 주석에 적혀 있다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import db as D
from app import revisions as R


# AL NOUF1 실측 분포 (58장 · 전부 신뢰도 HIGH).  숫자를 바꾸지 말 것 —
# 이것이 "규칙마다 답이 갈린다"는 증거다.
def alnouf_pages():
    counts = {"A": 11, "A1": 1, "B": 18, "C": 16, "D": 7}
    pages, n = [], 0
    for rev, k in counts.items():
        for _ in range(k):
            n += 1
            pages.append({"page_no": n, "drawing_no": f"D{n:04d}", "rev": rev,
                          "page_kind": "PID"})
    return pages


def test_document_rules_disagree_on_this_document():
    """세 규칙이 서로 다른 답을 낸다 — 그래서 도면이 답을 주지 않는다."""
    pages = alnouf_pages()
    assert R.document_revision(pages, "max")["rev"] == "D"
    assert R.document_revision(pages, "mode")["rev"] == "B"
    assert R.document_revision(pages, "first_sheet")["rev"] == "A"


def test_the_fold_keeps_the_distribution():
    """대표값만 남기지 않는다 — 접기 전 분포가 함께 나와야 화면이 둘 다 적는다."""
    out = R.document_revision(alnouf_pages(), "max")
    assert out["distribution"] == {"A": 11, "A1": 1, "B": 18, "C": 16, "D": 7}
    assert out["read"] == 53 and out["unread"] == 0
    assert "7/53" in out["why"]


def test_unreadable_revision_is_not_guessed():
    pages = [{"page_no": 1, "drawing_no": "X", "rev": "", "page_kind": "PID"}]
    out = R.document_revision(pages, "max")
    assert out["rev"] == "" and out["unread"] == 1


def test_a_before_a1_before_b():
    """형식이 `^[A-Z][0-9]?$` 라 사전순이 곧 개정순이다."""
    assert R.compare_document_revision("A1", "A")["verdict"] == "NEWER"
    assert R.compare_document_revision("B", "A1")["verdict"] == "NEWER"
    assert R.compare_document_revision("C", "C")["verdict"] == "SAME"
    assert R.compare_document_revision("B", "C")["verdict"] == "OLDER"
    assert R.compare_document_revision("", "C")["verdict"] == "UNKNOWN"
    assert R.compare_document_revision("C", "")["verdict"] == "UNKNOWN"


def test_sheet_comparison_pairs_by_drawing_number():
    """장 단위 대조에는 임의값이 없다 — 도면번호로만 짝을 짓는다."""
    before = [{"drawing_no": "A", "rev": "B", "page_kind": "PID"},
              {"drawing_no": "B", "rev": "B", "page_kind": "PID"},
              {"drawing_no": "C", "rev": "C", "page_kind": "PID"},
              {"drawing_no": "L", "rev": "A", "page_kind": "LEGEND"}]
    now = [{"drawing_no": "A", "rev": "C", "page_kind": "PID"},
           {"drawing_no": "B", "rev": "B", "page_kind": "PID"},
           {"drawing_no": "C", "rev": "B", "page_kind": "PID"},
           {"drawing_no": "D", "rev": "A", "page_kind": "PID"},
           {"drawing_no": "E", "rev": "", "page_kind": "PID"}]
    out = R.compare_sheet_revisions(now, before)
    assert [r["drawing_no"] for r in out["raised"]] == ["A"]
    assert out["unchanged"] == 1
    assert [r["drawing_no"] for r in out["lowered"]] == ["C"]
    assert out["new_sheets"] == 2          # D 와 E 는 이전에 없던 도면
    assert out["unreadable"] == 0          # E 는 새 도면이라 짝이 없다


def test_a_drawing_number_on_two_sheets_is_not_judged():
    """실측: 같은 도면번호를 쓰는 PID 장이 3쌍 있고 개정이 서로 다르다.

    한쪽을 골라 비교하면 **같은 PDF 를 두 번 넣어도 개정으로 읽힌다** —
    13회차 캡처가 잡은 결함이다.  고르지 않고 판정하지 않는다.
    """
    pages = [{"drawing_no": "D00P-10LBG10-M05-0001", "rev": "B", "page_kind": "PID"},
             {"drawing_no": "D00P-10LBG10-M05-0001", "rev": "A", "page_kind": "PID"},
             {"drawing_no": "X", "rev": "A", "page_kind": "PID"}]
    out = R.compare_sheet_revisions(pages, list(pages))
    assert out["raised"] == [] and out["lowered"] == []
    assert out["unchanged"] == 1                       # X 만 판정됐다
    assert [a["drawing_no"] for a in out["ambiguous"]] == ["D00P-10LBG10-M05-0001"]
    assert out["ambiguous"][0]["now_sheets"] == 2


# --------------------------------------------------------------------------
# 편집 승계
# --------------------------------------------------------------------------

def make_db(tmp_path):
    con = D.connect(tmp_path / "t.db")
    D.create_job(con, "j1", "a.pdf", "sha", tmp_path / "a.pdf")
    return con


def add_item(con, job, key, ai, user=None):
    con.execute(
        "INSERT INTO item (job_id,key,tab,page_no,drawing_no,origin,rect_json,"
        "ai_json,user_json,evidence_json,needs_review,annotation,conflict_json,"
        "deleted,added,removed) VALUES (?,?,'FIELD',1,'D1','','[]',?,?,'{}','','','{}',0,0,0)",
        (job, key, json.dumps(ai, sort_keys=True),
         json.dumps(user or {}, sort_keys=True)))
    con.commit()


def test_carry_fills_blanks_and_never_overwrites(tmp_path):
    con = make_db(tmp_path)
    add_item(con, "j1", "k1", {"qty": 2, "scope": "SCT", "description": "엔진"},
             {"description": "이번에 내가 고침"})
    filled = D.carry_user_values(con, "j1", {
        "k1": {"description": "지난 Rev 의 문장", "qty": 9, "scope": ""}})
    row = con.execute("SELECT ai_json, user_json FROM item WHERE key='k1'").fetchone()
    user = json.loads(row["user_json"])
    # 이번 리비전에서 이미 고친 칸은 그대로다
    assert user["description"] == "이번에 내가 고침"
    # 비어 있던 칸은 이어받는다
    assert user["qty"] == 9
    # 빈 값은 승계하지 않는다 - 편집이 아니라 없는 것이다
    assert "scope" not in user
    assert filled == 1
    # ★ 추출값 층은 그대로다
    assert json.loads(row["ai_json"]) == {"qty": 2, "scope": "SCT",
                                          "description": "엔진"}


def test_carry_ignores_columns_that_are_not_editable(tmp_path):
    con = make_db(tmp_path)
    add_item(con, "j1", "k1", {"qty": 2})
    D.carry_user_values(con, "j1", {"k1": {"page_no": 99, "qty": 3}})
    user = json.loads(con.execute(
        "SELECT user_json FROM item WHERE key='k1'").fetchone()["user_json"])
    assert user == {"qty": 3}


def test_carry_conflict_goes_to_review_without_choosing(tmp_path):
    """이어받은 칸을 이번 도면이 다르게 읽었으면 **고르지 않고** 둘 다 보인다."""
    con = make_db(tmp_path)
    add_item(con, "j1", "k1", {"qty": 4}, {"qty": 9})
    D.flag_carry_conflicts(con, "j1", {
        "k1": {"qty": {"was_ai": 2, "now_ai": 4, "user": 9}}})
    row = con.execute("SELECT conflict_json, needs_review, user_json FROM item"
                      " WHERE key='k1'").fetchone()
    conflict = json.loads(row["conflict_json"])["qty"]
    assert conflict == {"was_ai": 2, "now_ai": 4, "user": 9}
    assert "이어받은" in row["needs_review"]
    # 편집값은 살아 있다 - 검토로 올릴 뿐 되돌리지 않는다
    assert json.loads(row["user_json"])["qty"] == 9


def test_edit_history_keeps_the_author(tmp_path):
    con = make_db(tmp_path)
    add_item(con, "j1", "k1", {"qty": 2})
    D.record_feedback(con, "j1", "EDITED", row_key="k1", field="qty",
                      ai_value=2, user_value=9, author="홍길동",
                      pattern_args={"field": "qty", "ai": 2, "user": 9})
    D.record_feedback(con, "j1", "EDITED", row_key="k1", field="scope",
                      ai_value="", user_value="SCT",
                      pattern_args={"field": "scope", "ai": "", "user": "SCT"})
    hist = D.row_edit_history(con, "j1", "k1")
    assert [h["field"] for h in hist] == ["scope", "qty"]     # 최신이 먼저
    assert hist[1]["author"] == "홍길동"
    # 이름 없이 저장한 편집은 빈 채로 남는다 - 서버가 이름을 지어내지 않는다
    assert hist[0]["author"] == ""


def test_last_author_per_field(tmp_path):
    """승계할 때 이름을 이으려면 칸마다 마지막에 고친 사람을 알아야 한다."""
    con = make_db(tmp_path)
    add_item(con, "j1", "k1", {"qty": 2})
    for who, val in (("홍길동", 5), ("김검토", 9)):
        D.record_feedback(con, "j1", "EDITED", row_key="k1", field="qty",
                          ai_value=2, user_value=val, author=who,
                          pattern_args={"field": "qty", "ai": 2, "user": val})
    assert D.last_authors(con, "j1", "k1")["qty"]["author"] == "김검토"


def test_counts_that_the_home_screen_reads(tmp_path):
    con = make_db(tmp_path)
    add_item(con, "j1", "k1", {"qty": 2}, {"qty": 9, "scope": "SCT"})
    add_item(con, "j1", "k2", {"qty": 2})
    con.execute("UPDATE item SET removed=1 WHERE key='k2'")
    con.commit()
    assert D.row_count(con, "j1") == 1        # 지운 행은 빼고 센다
    assert D.edited_cell_count(con, "j1") == 2


def test_the_fingerprint_never_reads_the_edit_layer():
    """지문은 추출값만 해싱한다 — 소스로 강제한다 (10회차 type_display 와 같은 방식)."""
    import inspect
    from app import pipeline
    src = inspect.getsource(pipeline.fingerprint)
    for forbidden in ("user_json", "user_values", "merged", "edited"):
        assert forbidden not in src, f"지문이 편집 층을 읽고 있습니다: {forbidden}"
