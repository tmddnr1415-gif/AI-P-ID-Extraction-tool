"""L40 — 검토를 상업적으로 쓸 수 있게: 잡음 줄이기 · 사람 판단으로 툴 검토의 정밀도를 잰다.

* 이 묶음에 없는 시트를 가리키는 from-to 는 행마다 '설계 오류' 가 아니라 시트마다 '설계 확인' 한 건이다.
* 검토 항목마다 맞음 · 툴 오판 · 보류 — 다시 모아도 열쇠로 이어 붙고, 지우는 길이 없다 (이력).
"""
from __future__ import annotations

import openpyxl
import io

import pymupdf

from app.logic import behavior, fromto, review, store
from tests.test_logic_l32_sequence import _client, _job
from tests.test_logic_l39_review import _own_data, _pdf, _two_sheets  # noqa: F401  (픽스처)


def _missing_bundle():
    sheets = _two_sheets()
    for s in sheets:
        for r in s["rows"]:
            if r["side"] == "L":
                r["fm"] = "G099-7"
                r["ref"] = {"sheet": "G099", "row": 7, "page": None, "other_bundle": False, "src_row": 7}
        for t in s["table"]:
            if t["side"] == "L":
                t["fm"] = "G099-7"
    fromto.check(sheets)
    return sheets


def test_references_to_a_missing_sheet_become_one_check_per_sheet():
    sheets = _missing_bundle()
    rv = review.build({"sheets": sheets}, None, {})
    assert not any(it["code"] == "FT_MISMATCH" and "장이 없습니다" in it["text"] for it in rv["items"])
    grp = [it for it in rv["items"] if it["code"] == "FT_MISSING_SHEET"]
    assert len(grp) == 1 and grp[0]["cat"] == "CHECK" and grp[0]["target"] == "G099"
    assert len(grp[0]["refs"]) == 3 and "다른 문서" in grp[0]["text"]
    assert not any(it["code"] == "READ_LINK" and "G099" in it["text"] for it in rv["items"])    # 같은 것을 두 번 세지 않는다


def test_item_keys_are_stable_across_rebuilds():
    sheets = _two_sheets()
    a = review.build({"sheets": sheets}, None, {})
    b = review.build({"sheets": sheets}, None, {})
    assert [it["key"] for it in a["items"]] == [it["key"] for it in b["items"]]
    assert len({it["key"] for it in a["items"]}) == len(a["items"])


def test_marks_api_precision_history_and_exports():
    sh = _two_sheets()
    job = _job(sh)
    d = store.job_dir(job)
    _pdf(d / "source.pdf", 0)
    before = (d / "result.json").read_bytes()
    c = _client()
    j = c.get(f"/logic/api/jobs/{job}/review").json()
    design = [it for it in j["items"] if it["cat"] in ("ERROR", "CHECK")]
    assert design
    k = design[0]["key"]
    assert c.post(f"/logic/api/jobs/{job}/review/mark", json={"keys": [k], "verdict": "OK"}).status_code == 400   # 이름 필수
    assert c.post(f"/logic/api/jobs/{job}/review/mark", json={"keys": [k], "verdict": "X", "author": "a"}).status_code == 400
    r = c.post(f"/logic/api/jobs/{job}/review/mark", json={"keys": [k], "verdict": "WRONG", "author": "홍길동", "note": "다른 권"})
    assert r.status_code == 200 and r.json()["set"][k]["verdict"] == "WRONG"
    j = c.get(f"/logic/api/jobs/{job}/review").json()
    it = next(x for x in j["items"] if x["key"] == k)
    assert it["mark"]["author"] == "홍길동" and j["marks"]["design"]["WRONG"] == 1
    assert j["marks"]["design"]["precision"] == 0.0
    c.post(f"/logic/api/jobs/{job}/review/mark", json={"keys": [k], "verdict": "OK", "author": "홍길동"})
    j = c.get(f"/logic/api/jobs/{job}/review").json()
    assert j["marks"]["design"]["precision"] == 1.0
    # 판단을 거둬도 이력은 남는다
    c.post(f"/logic/api/jobs/{job}/review/mark", json={"keys": [k], "verdict": None, "author": "홍길동"})
    m = review.load_marks(d)
    assert k not in m["marks"] and [h["verdict"] for h in m["history"]] == ["WRONG", "OK", None]
    # 다시 판단 → PDF · Excel 에 실린다
    c.post(f"/logic/api/jobs/{job}/review/mark", json={"keys": [k], "verdict": "OK", "author": "홍길동", "note": "확인함"})
    p = c.get(f"/logic/api/jobs/{job}/review.pdf")
    doc = pymupdf.open(stream=p.content, filetype="pdf")
    assert "맞음" in doc[0].get_text()
    x = c.get(f"/logic/api/jobs/{job}/review.xlsx")
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    vals = [[cell.value for cell in row] for row in wb["항목"].iter_rows(values_only=False)]
    assert any(v[8] and "맞음" in v[8] and v[9] == "확인함" for v in vals[1:])
    assert (d / "result.json").read_bytes() == before                      # 분석 결과는 그대로


def test_screen_has_verdict_buttons():
    from tests.test_logic_l39_review import JS
    assert "review/mark" in JS and "rvMarkCell" in JS and "미처리" in JS
    assert "prompt(" not in JS and "confirm(" not in JS
