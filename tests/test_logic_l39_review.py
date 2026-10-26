"""L39 — 정합성 검토 결과 한 장 · 입력 PDF 마크업.

툴이 이미 낸 판정(from-to · 선 · 게이트 · 동작 학습)을 세 갈래로 모은다 — 설계 오류 · 설계 확인 · 읽기 빈틈.
판정을 새로 하지 않는다 · 분석 결과 파일을 바꾸지 않는다 · PDF 는 원본을 두고 새 파일을 만든다.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app.logic import api, behavior, fromto, markup_pdf, review, store
from tests.test_logic_l32_sequence import _client, _job
from tests.test_logic_l35_understand import _latched, _pair

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/logic.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _two_sheets():
    """G001-90 이 TO G002-5 로 보내는데 G002-5 의 FM 은 G001-91 (어긋남) · G002 에 판정 못 한 블록 · 매달린 선."""
    a = _latched()[0]
    a["rows"][2]["to"] = "G002-5"
    a["rows"][2]["to_box"] = [500, 85, 540, 95]
    a["rows"][2]["no_box"] = [480, 85, 500, 95]
    b = {"page": 2, "sheet_no": "G002", "title": "TG002", "logic": [100, 0, 500, 800], "pitch": 10, "frame": None,
         "nets": {"x": {"segs": [[100, 50, 300, 50]]}, "y": {"segs": [[300, 300, 400, 300]]}}, "order": {},
         "blocks": {"U": {"kind": "RECT", "func": "UNKNOWN", "logic": "unknown", "label": "", "read": "", "score": 0,
                          "bbox": [300, 40, 320, 60], "cells": [], "param": {}, "group": "", "pointer": None, "roles": {}, "key": ""}},
         "ports": [{"block": "U", "net": "x", "dir": "in", "at": [300, 50]}],
         "rows": [{"n": 5, "side": "L", "net": "x", "desc": "FAN A START CMD", "fm": "G001-91", "at": [100, 50],
                   "fm_box": [20, 45, 60, 55], "no_box": [60, 45, 80, 55]}],
         "table": [], "dangling": [], "stray_arrows": [],
         "findings": [{"code": "C1_DANGLING", "at": [400, 300], "net": "y", "text": "선 끝이 아무 데도 닿지 않습니다"},
                      {"code": "BLOCK_UNKNOWN", "block": "U", "text": "블록 U 판정 못 함"}]}
    b["table"] = [dict(r) for r in b["rows"]]
    for s in (a, b):
        s["table"] = [dict(r) for r in s["rows"]]
    sheets = [a, b]
    for s in sheets:
        for r in s["rows"]:
            if r.get("fm"):
                sh, n = r["fm"].split("-")
                r["ref"] = {"sheet": sh, "row": int(n), "page": 1, "other_bundle": False, "src_row": int(n)}
    fromto.check(sheets)
    return sheets


def test_three_categories_and_tool_rate():
    sheets = _two_sheets()
    res = {"sheets": sheets, "pdf_pages": 2}
    rv = review.build(res, behavior.learn(sheets, {}), {})
    cats = {(it["code"], it["cat"]) for it in rv["items"]}
    assert ("FT_MISMATCH", "ERROR") in cats                 # FM 이 가리키는 행에 신호 없음 — 도면이 어긋남
    assert ("BLOCK_UNKNOWN", "GAP") in cats and ("C1_DANGLING", "GAP") in cats
    assert rv["count"]["ERROR"] >= 1 and rv["count"]["GAP"] >= 2
    tl = rv["rate"]["tally"]
    assert tl["gate"]["all"] >= 1 and tl["line"]["done"] < tl["line"]["all"]      # 매달린 선 · 판정 못 한 블록은 툴이 못 끝냄
    assert 0 < rv["rate"]["judged"] < 1
    err = next(it for it in rv["items"] if it["code"] == "FT_MISMATCH")
    assert err["rect"] and err["sheet_no"] in ("G001", "G002")
    assert [it["id"] for it in rv["items"]] == list(range(1, len(rv["items"]) + 1))
    assert rv["items"][0]["cat"] == "ERROR"                   # 설계 오류가 맨 앞


def test_opposite_commands_both_on_is_a_design_check():
    sh = _pair(False)
    rv = review.build({"sheets": sh}, behavior.learn(sh, {}), {})
    assert any(it["code"] == "PAIR_BOTH" and it["cat"] == "CHECK" for it in rv["items"])
    sh = _pair(True)
    rv = review.build({"sheets": sh}, behavior.learn(sh, {}), {})
    assert not any(it["code"] == "PAIR_BOTH" for it in rv["items"])


def test_latched_command_without_stop_is_checked():
    sh = _latched()
    lb = behavior.learn(sh, {})
    x = next(i for i in lb["items"] if i.get("action") == "START")
    assert x["latch"] and x["stoppers"]
    assert not any(it["code"] == "CMD_NO_STOP" for it in review.build({"sheets": sh}, lb, {})["items"])
    x["stoppers"] = []
    assert any(it["code"] == "CMD_NO_STOP" for it in review.build({"sheets": sh}, lb, {})["items"])


def _pdf(path, rot=0, n=2):
    doc = pymupdf.open()
    for _ in range(n):
        p = doc.new_page(width=842, height=595)
        p.insert_text((50, 50), "LOGIC", fontsize=10)
        if rot:
            p.set_rotation(rot)
    doc.save(path)


@pytest.mark.parametrize("rot", [0, 270])
def test_markup_pdf_puts_boxes_on_the_drawing_and_a_summary_in_front(tmp_path, rot):
    src = tmp_path / "src.pdf"
    _pdf(src, rot)
    rv = {"items": [{"id": 1, "cat": "ERROR", "topic": "fromto", "code": "FT_MISMATCH", "page": 2, "sheet_no": "G002",
                     "title": "G002-5 from-to 불일치", "text": "FM G001-91 — 행이 비어 있습니다", "rect": [100, 200, 160, 212]},
                    {"id": 2, "cat": "INFO", "topic": "line", "code": "X", "page": 1, "sheet_no": "G001", "title": "참고",
                     "text": "", "rect": [10, 10, 20, 20]}],
          "count": {"ERROR": 1, "CHECK": 0, "GAP": 0, "INFO": 1}, "rate": {"read": 0.98, "judged": 0.95, "parts": {}, "tally": {}},
          "by_topic": {"fromto": {"ERROR": 1, "CHECK": 0, "GAP": 0}},
          "per_sheet": [{"page": 2, "sheet_no": "G002", "title": "T", "ERROR": 1, "CHECK": 0, "GAP": 0, "INFO": 0}]}
    out = tmp_path / "out.pdf"
    info = markup_pdf.build(str(src), rv, str(out), name="toy")
    d = pymupdf.open(out)
    n = info["cover_pages"]
    assert d.page_count == 2 + n and "정합성 검토 결과" in d[0].get_text()
    page = d[n + 1]                                           # 원래 2쪽
    annots = list(page.annots())
    assert len(annots) == 1 and "G002-5" in annots[0].info["content"]
    assert not list(d[n].annots())                            # 참고(INFO)는 기본으로 안 찍는다
    # 상자는 화면(회전 뒤) 좌표 그대로 그 자리에 서야 한다
    r = annots[0].rect * page.rotation_matrix
    r.normalize()
    assert abs(r.x0 - 98.5) < 1.5 and abs(r.y0 - 198.5) < 1.5
    assert "E1" in page.get_text()                            # 번호표
    assert d.get_toc()[0][1] == "정합성 검토 결과"
    assert pymupdf.open(src).page_count == 2                  # 원본은 그대로


def test_api_review_pdf_and_excel_and_result_untouched():
    sh = _two_sheets()
    job = _job(sh)
    d = store.job_dir(job)
    _pdf(d / "source.pdf", 0)
    before = (d / "result.json").read_bytes()
    c = _client()
    r = c.get(f"/logic/api/jobs/{job}/review")
    assert r.status_code == 200
    j = r.json()
    assert j["count"]["ERROR"] >= 1 and j["learning"]["state"] == "done"
    assert (d / "review.json").exists()
    p = c.get(f"/logic/api/jobs/{job}/review.pdf", params={"author": "홍길동"})
    assert p.status_code == 200 and p.content[:4] == b"%PDF"
    assert "정합성" in pymupdf.open(stream=p.content, filetype="pdf")[0].get_text()
    x = c.get(f"/logic/api/jobs/{job}/review.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    assert (d / "result.json").read_bytes() == before
    st = store.read_status(d)
    assert st["review"]["error"] == j["count"]["ERROR"]       # 첫 화면 이력 줄에 싣는 숫자


def test_screen_has_review_panel_and_pdf_link():
    assert 'id="rv-btn"' in HTML and 'id="rv-pdf"' in HTML and 'id="rv-modal"' in HTML
    assert "/review.pdf" in JS and "function renderReview" in JS and "function drawReview" in JS
    assert "검토 PDF" in JS
