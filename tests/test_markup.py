"""44회차 — 사용자 마크업은 편집값 층에 산다.

세 가지를 못박는다:
  1. 마크업(추가 · 오검출 표시)은 추출값(`ai_json`) · 지문 · 축을 건드리지 않는다
     — 소스 검사 + DB 실측.
  2. 오검출 표시는 행을 지우지 않고, Excel 제외는 선택이며, 되돌릴 수 있다.
  3. Excel REMARK 의 표시는 결정적이고(시각 없음) 마크업이 없으면 예전과 같다.
그리고 제안값은 도면에서 먼저 읽는다 (§9 ①②) — `pipeline.propose_at`.
"""
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db, excel_out, markup, pipeline, revisions   # noqa: E402

PDF = ROOT / "data" / "pid_total.pdf"


def _base(rows=None):
    return {
        "pages": [{"page_no": 6, "drawing_no": "D00P-11HAD10-M05-0001", "title": "t",
                   "page_kind": "PID", "in_scope": True, "scope_reason": "",
                   "width": 2384.0, "height": 1684.0}],
        "layers": {}, "multipliers": {}, "legend": {},
        "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": rows if rows is not None else [
            {"key": "k1", "tab": "FIELD", "page_no": 6, "rect": [10, 10, 30, 40],
             "drawing_no": "D00P-11HAD10-M05-0001",
             "type": "PIT", "qty": 2, "system": "", "valve_type": "",
             "vendor_supply": "", "scope": "SCT", "description": "",
             "tag_no": "", "needs_review": "", "annotation": "",
             "evidence": {"qty_basis": "1 symbol x 2 (unit code 11, LEGEND)"}}],
    }


def _job(tmp_path):
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", _base())
    return con


# --------------------------------------------------------------------------
# 1. 마크업은 추출값 · 지문 · 축에 닿지 않는다
# --------------------------------------------------------------------------

def _code_only(path: Path) -> str:
    """주석과 docstring 을 뺀 소스 — 설명 문장에 적힌 낱말이 검사에 걸리지 않게."""
    import ast
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(body, list) and body and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)):
            body.pop(0)
    return ast.unparse(tree)


def test_markup_modules_never_touch_the_extracted_layer():
    """`app/markup.py` 는 `ai_json` 을 쓰지 않고 `store_result` 를 부르지 않는다.
    축 채점기 둘은 DB 도 markup 도 모른다 — 결과 json 만 읽는다."""
    src = _code_only(ROOT / "app" / "markup.py")
    assert "ai_json" not in src
    assert "store_result" not in src
    assert "fingerprint(" not in src
    for scorer in ("spike/accuracy.py", "spike/identification.py"):
        text = (ROOT / scorer).read_text(encoding="utf-8")
        assert "from app import db" not in text and "app.db" not in text, scorer
        assert "markup" not in text, scorer


def test_fingerprint_is_computed_from_the_result_not_the_db():
    """지문 함수는 인자 하나(`result`)만 보고, DB 를 열지 않는다."""
    import inspect
    src = inspect.getsource(pipeline.fingerprint)
    assert "db." not in src and "sqlite" not in src


def test_markup_row_is_all_user_values_and_survives_reanalysis(tmp_path):
    con = _job(tmp_path)
    before = db.get_job(con, "j")["fingerprint"]
    key = db.add_row(con, "j", 6, "FIELD", "", "D00P-11HAD10-M05-0001",
                     {"type": "TIT", "qty": 2, "scope": "VENDOR(HRSG)"},
                     rect=[100, 100, 120, 140],
                     evidence={"markup": {"scope_source": "DRAWING",
                                          "qty_source": "DRAWING",
                                          "author": "홍길동", "class": "MISSING"}},
                     needs_review="")
    row = db.get_row(con, "j", key)
    assert row["added"] and row["rect"] == [100, 100, 120, 140]
    assert all(v is None for v in row["ai"].values()), "추출값 층은 전부 None"
    assert row["needs_review"] == "", "사람이 만든 행은 검토 사유가 없다"
    assert row["evidence"]["markup"]["scope_source"] == "DRAWING"
    # 재분석 — 같은 결과를 다시 넣어도 마크업 행은 남고 지문은 그대로다
    db.store_result(con, "j", _base())
    rows = {r["key"]: r for r in db.merged_rows(con, "j")}
    assert key in rows and rows[key]["values"]["type"] == "TIT"
    assert rows["k1"]["ai"]["scope"] == "SCT", "기존 행의 도면 유도값은 그대로"
    assert db.get_job(con, "j")["fingerprint"] == before
    s = markup.summary(con, "j")
    assert s["added"] == 1 and s["added_with_rect"] == 1 and s["scope_user"] == 0


# --------------------------------------------------------------------------
# 2. 오검출 표시 — 행은 남고 Excel 제외는 선택
# --------------------------------------------------------------------------

def test_reject_keeps_the_row_and_excel_exclusion_is_a_choice(tmp_path):
    con = _job(tmp_path)
    rj = {"class": "FALSE_POSITIVE", "note": "도면에 없음", "author": "홍길동", "at": 1.0}
    out = db.remove_row(con, "j", "k1", reject=rj, exclude=False)
    assert out["flagged"] and not out["removed"]
    row = db.get_row(con, "j", "k1")
    assert row["reject"]["class"] == "FALSE_POSITIVE" and row["removed"] is False
    assert row["ai"]["scope"] == "SCT", "표시가 추출값을 바꾸지 않는다"
    rev = db.snapshot(con, "j")
    assert [r["key"] for r in db.get_revision(con, rev)["rows"]] == ["k1"], "Excel 유지"
    # Excel 제외를 고르면 빠진다 — 그래도 행은 남는다
    db.remove_row(con, "j", "k1", reject=rj, exclude=True)
    row = db.get_row(con, "j", "k1")
    assert row["removed"] is True and row["reject"]["note"] == "도면에 없음"
    rev = db.snapshot(con, "j")
    assert db.get_revision(con, rev)["rows"] == []
    assert markup.summary(con, "j")["rejected_excluded"] == 1
    # 되돌리기 — 둘 다 지운다
    db.restore_row(con, "j", "k1")
    row = db.get_row(con, "j", "k1")
    assert row["removed"] is False and row["reject"] == {}


# --------------------------------------------------------------------------
# 3. Excel REMARK — 앞머리 표시 · 시각 없음 · 마크업 없으면 그대로
# --------------------------------------------------------------------------

def _row(**kw):
    base = {"key": "k", "tab": "FIELD", "page_no": 6, "drawing_no": "D",
            "values": {"type": "PIT"}, "user": {}, "evidence": {},
            "review_codes": [], "review_state": {}, "review_label": {},
            "review_axis": {}, "added": False, "removed": False, "reject": {}}
    base.update(kw)
    return base


def test_remark_marks_markup_rows_without_a_timestamp():
    plain = _row()
    assert excel_out._remark(plain, plain["values"]) is None, "마크업이 없으면 예전과 같다"
    added = _row(added=True, review_codes=["MANUAL_ADD"],
                 evidence={"markup": {"author": "홍길동", "at": 1757800000.0}})
    text = excel_out._remark(added, added["values"])
    assert text == "사용자 추가 · 홍길동", text
    assert not re.search(r"\d{4}", text), "시각을 적지 않는다 (결정성)"
    assert excel_out._remark(added, added["values"]) == text
    rejected = _row(reject={"class": "FALSE_POSITIVE", "note": "도면에 없음",
                            "author": "김", "at": 1.0},
                    review_codes=["MANUAL_REJECT"])
    text = excel_out._remark(rejected, rejected["values"])
    assert text.startswith("사용자 표시: 오검출 의심 (도면에 없음) · 김"), text
    assert "미처리" not in text, "MANUAL_* 코드는 검토 사유 목록에 끼지 않는다"


def test_no_new_excel_columns_for_markup():
    """발주처 양식에 없는 열을 만들지 않는다 — 표시는 REMARK 열 안이다."""
    src = (ROOT / "app" / "excel_out.py").read_text(encoding="utf-8")
    assert "markup" not in src.split("def _remark")[0], "열 정의 쪽에 마크업이 없다"
    assert "사용자 추가" in src


# --------------------------------------------------------------------------
# 4. 안정 ID — 같은 장부 · 같은 규칙
# --------------------------------------------------------------------------

def test_markup_rows_take_ids_from_the_same_registry(tmp_path):
    con = _job(tmp_path)
    data = tmp_path / "data"
    revisions.create_project(data, "P")
    con.execute("UPDATE job SET project='P', revision='A' WHERE id='j'")
    con.commit()
    job = db.get_job(con, "j")
    row = {"type": "TIT", "qty": 2, "tab": "FIELD", "page_no": 6,
           "rect": [100, 100, 120, 140], "drawing_no": "D00P-11HAD10-M05-0001"}
    a = markup.assign_stable_id(data, con, job, "uAAA", row)
    b = markup.assign_stable_id(data, con, job, "uBBB", row)
    assert a["stable_id"] and b["stable_id"] and a["stable_id"] != b["stable_id"]
    reg = revisions.Registry.load(revisions.project_dir(data, "P") / "id_registry.json")
    recs = reg.data["ids"]
    assert recs[a["stable_id"]]["origin"] == "user"
    assert recs[a["stable_id"]]["seq"] + 1 == recs[b["stable_id"]]["seq"]
    code = recs[a["stable_id"]]["system_code"]
    assert reg.next_seq(code) == recs[b["stable_id"]]["seq"] + 1, "회수 없음 · 단조 증가"
    assert a["excel_no"] == 1 and b["excel_no"] == 2
    st = db.revision_states(con, "j")
    assert st["uAAA"]["id"] == a["stable_id"] and st["uAAA"]["state"] == "BASELINE"
    # 프로젝트가 없으면 ID 없이 그렇게 말한다
    con.execute("UPDATE job SET project='' WHERE id='j'"); con.commit()
    c = markup.assign_stable_id(data, con, db.get_job(con, "j"), "uCCC", row)
    assert c["stable_id"] == "" and "장부가 없" in c["why"]


# --------------------------------------------------------------------------
# 5. 내보내기 — 있는 표를 zip 하나로
# --------------------------------------------------------------------------

def test_feedback_export_zip_has_json_and_md(tmp_path):
    con = _job(tmp_path)
    db.add_row(con, "j", 6, "FIELD", "", "D", {"type": "TIT", "scope": "VENDOR"},
               rect=[100, 100, 120, 140],
               evidence={"markup": {"scope_source": "USER", "qty_source": "USER",
                                    "author": "홍", "class": "MISSING", "at": 1.0}},
               needs_review="")
    db.remove_row(con, "j", "k1", reject={"class": "FALSE_POSITIVE", "author": "홍",
                                          "at": 2.0, "note": ""})
    info = markup.export_zip(con, db.get_job(con, "j"), tmp_path / "fb")
    with zipfile.ZipFile(info["path"]) as z:
        names = z.namelist()
        assert "feedback.json" in names and "feedback.md" in names
        fb = json.loads(z.read("feedback.json"))
    kinds = sorted(it["kind"] for it in fb["items"])
    assert kinds == ["false_positive", "missing"]
    assert fb["fingerprint"] == "f" and fb["rows_total"] == 1
    m = [it for it in fb["items"] if it["kind"] == "missing"][0]
    assert m["scope_source"] == "USER" and m["qty_source"] == "USER"
    assert info["clips"] == 0, "PDF 가 없으면 조각도 없다 — 지어내지 않는다"
    # 내보낸 뒤에도 마크업은 남는다
    assert markup.summary(con, "j")["added"] == 1
    assert info["name"].startswith("feedback_pid_")


# --------------------------------------------------------------------------
# 6. 제안값 — 도면에서 먼저 읽는다
# --------------------------------------------------------------------------

@pytest.mark.skipif(not PDF.exists(), reason="data/pid_total.pdf 가 없는 기계")
def test_propose_at_reads_the_star_before_asking(tmp_path):
    """p6 의 FIT (VENDOR(HRSG) 행 자리) 에서는 별표를 읽어 `DRAWING` 이고,
    같은 장 SCT PIT 자리에서는 별표가 없어 **빈칸 + USER** 다 — 별표 없음을
    SCT 로 지어내지 않는다."""
    v = pipeline.propose_at(PDF, 6, [431.3, 437.4, 499.3, 460.1])
    assert v["scope"].startswith("VENDOR"), v
    assert v["scope_source"] == "DRAWING" and v["stars"] >= 1
    s = pipeline.propose_at(PDF, 6, [656.6, 440.9, 679.2, 508.9])
    assert s["scope"] == "" and s["scope_source"] == "USER", s
    # 도면은 `PT` 로 인쇄하고 엔진 사전(`anchors.type_map`)이 `PIT` 로 바꾼다 —
    # 제안도 같은 사전을 읽어야 한다 (23회차 축3 채점기가 겪은 것과 같은 자리).
    assert any(w["text"].upper() == "PT" for w in s["words"]), s["words"]
    assert markup._type_from_words(s["words"])["type"] == "PIT"
    # 아무것도 저장하지 않았고 config 도 그대로다
    assert pipeline.CFG.get("sheet.width_pt") == 2384.0
