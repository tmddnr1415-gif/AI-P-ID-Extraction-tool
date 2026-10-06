"""hotfix46 — 개정 대조는 **태그로만** · 실행 프로젝트만.

사용자: *"나란히 대조는 실행 프로젝트만 해당되며 tag 위주로 비교한다.  동일 tag 와
abbreviation 기준 (TIT 등).  PDF 상의 위치 좌표로는 비교하지 않는다."*

지키는 것:
  ① 짝의 열쇠는 (TYPE, 태그) 하나 — 반경·최근접·거리 코드가 대조 경로에 없다
  ② 입찰 프로젝트는 대조하지 않는다 (NOT_COMPARED 전부 · 추가·삭제 후보 0 · basis NONE)
  ③ 실행 프로젝트에서 태그 없는 행은 NOT_COMPARED — 추가도 삭제도 아니다
  ④ `_run_comparison` 은 `_mode_facts` 의 effective 로 tagged 를 정한다 · `/revision` 이 `compare_basis` 를 낸다
  ⑤ 화면 — 나란히 버튼·자동 켜짐은 `compare_basis === "TAG"` 일 때만
  ⑥ Excel REMARK · 변경 내역 요약은 NOT_COMPARED 를 빈칸으로
"""
from __future__ import annotations

import inspect
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import revisions as R
from app import excel_out

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
DWG = "1A1Y-10LBB50-M05-0001"


def row(key, type_, x, y, tag="", **kw):
    return dict({"key": key, "drawing_no": DWG, "type": type_, "page_no": 1, "tab": "FIELD",
                 "rect": [x, y, x + 34, y + 11], "tag_no": tag, "description": ""}, **kw)


def _ab(a, b, tagged=True):
    reg = R.Registry()
    R.compare(a, reg, "Rev.A", compared_with="", tagged=tagged)
    return R.compare(b, reg, "Rev.B", compared_with="Rev.A", tagged=tagged), reg


# ------------------------------------------------------------------ ①
def test_the_comparison_path_has_no_distance_code():
    src = inspect.getsource(R.compare) + inspect.getsource(R._match_one_drawing) + inspect.getsource(R._tag_matches)
    for word in ("radius", "nearest", "_pairs_within", "match_radius("):
        assert word not in src, word
    assert not hasattr(R, "_pairs_within")
    # 움직인 거리는 **기록**으로만 — 짝을 정한 뒤에 센다 (판정 전에 anchor 를 비교하는 줄이 없다)
    body = inspect.getsource(R.compare)
    assert body.index("_match_one_drawing(cur, recs)") < body.index("moved = round(")


def test_same_tag_different_type_is_not_a_pair():
    """동일 tag 와 abbreviation 기준 — PI 와 PIT 는 같은 태그를 들어도 다른 항목이다."""
    a = [row("a", "PI", 100, 100, "11LBB50CP001")]
    b = [row("b", "PIT", 100, 100, "11LBB50CP001")]
    out, _ = _ab(a, b)
    assert out["states"]["b"]["state"] == R.ADDED
    assert [(d["type"], d["tag_no"]) for d in out["deleted_candidates"]] == [("PI", "11LBB50CP001")]


def test_same_tag_same_type_far_away_is_unchanged():
    a = [row("a", "TIT", 50, 50, "11LBB50CT001")]
    b = [row("b", "TIT", 1900, 1300, "11LBB50CT001")]
    out, _ = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.UNCHANGED and st["basis"] == "TAG" and st["moved_pt"] > 2000


# ------------------------------------------------------------------ ②
def test_a_bid_project_is_not_compared_at_all():
    a = [row("a1", "PI", 100, 100), row("a2", "PI", 100, 400, "11LBB50CP002")]
    b = [row("b1", "PI", 100, 100), row("b3", "TIT", 900, 900, "11LBB50CT009")]
    out, reg = _ab(a, b, tagged=False)
    assert out["basis"] == "NONE"
    assert {v["state"] for v in out["states"].values()} == {R.NOT_COMPARED}
    assert all("입찰" in v["reason"] for v in out["states"].values())
    assert out["deleted_candidates"] == []
    assert out["counts"][R.ADDED] == 0 and out["counts"][R.NOT_COMPARED] == 2
    assert len(reg.data["ids"]) == 4                 # 새 행은 ID 를 받는다 (산출물 NO) — 옛 ID 는 남는다


def test_a_baseline_is_a_baseline_in_both_modes():
    for tagged in (True, False):
        reg = R.Registry()
        out = R.compare([row("a", "PI", 1, 1, "11LBB50CP001"), row("b", "PI", 9, 9)], reg, "Rev.A",
                        compared_with="", tagged=tagged)
        assert {v["state"] for v in out["states"].values()} == {R.BASELINE}


# ------------------------------------------------------------------ ③
def test_untagged_rows_in_an_epc_project_are_neither_added_nor_deleted():
    a = [row("a1", "PIT", 100, 100, "11LBB50CP001"), row("a2", "GATE", 300, 300)]
    b = [row("b1", "PIT", 100, 100, "11LBB50CP001"), row("b2", "GATE", 700, 700), row("b3", "GATE", 800, 800)]
    out, _ = _ab(a, b)
    st = {k: v["state"] for k, v in out["states"].items()}
    assert st == {"b1": R.UNCHANGED, "b2": R.NOT_COMPARED, "b3": R.NOT_COMPARED}
    assert out["deleted_candidates"] == []
    assert out["radii"][DWG]["matched_by"] == {"TAG": 1, "GEOMETRY": 0, "NOT_COMPARED": 2}


# ------------------------------------------------------------------ ④ end to end
def _app(tmp_path):
    import os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main


def _job(main, job, project, revision, compared_with, rows):
    from app import db
    up = main.UPLOADS
    up.mkdir(parents=True, exist_ok=True)
    pdf = up / f"{job}.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,progress,message,"
        "fingerprint,project,revision,compared_with) VALUES (?,?,?,?,?,'done',1.0,'','',?,?,?)",
        (job, "x.pdf", job, str(pdf), time.time(), project, revision, compared_with))
    for i, (type_, tag) in enumerate(rows):
        db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no=DWG,
                   values={"type": type_, "tag_no": tag, "qty": 1}, rect=[100 * i, 100, 100 * i + 34, 111])
    main.CON.commit()


def test_run_comparison_follows_the_project_mode(tmp_path):
    c, main = _app(tmp_path)
    from app import revisions
    # 실행 프로젝트 — 태그로 대조
    revisions.create_project(main.DATA_DIR, "EPC")
    revisions.set_mode(main.DATA_DIR, "EPC", "epc", "tester")
    _job(main, "ea", "EPC", "A", "", [("PIT", "11LBB50CP001"), ("TIT", "11LBB50CT001"), ("GATE", "")])
    _job(main, "eb", "EPC", "B", "A", [("PIT", "11LBB50CP001"), ("LIT", "11LBB50CL001"), ("GATE", "")])
    main._run_comparison("ea")
    out = main._run_comparison("eb")
    assert out["counts"][R.ADDED] == 1 and out["counts"][R.DELETED_CANDIDATE] == 1
    assert out["counts"][R.NOT_COMPARED] == 1 and out["counts"][R.UNCHANGED] == 1
    rev = c.get("/jobs/eb/revision").json()
    assert rev["compare_basis"] == "TAG"
    assert rev["matched_by"] == {"TAG": 1, "GEOMETRY": 0, "NOT_COMPARED": 1}
    assert [d["tag_no"] for d in rev["deleted_candidates"]] == ["11LBB50CT001"]
    # 입찰 프로젝트 — 대조하지 않는다
    revisions.create_project(main.DATA_DIR, "BID")
    revisions.set_mode(main.DATA_DIR, "BID", "bid", "tester")
    _job(main, "ba", "BID", "A", "", [("PI", ""), ("TI", "")])
    _job(main, "bb", "BID", "B", "A", [("PI", ""), ("TI", ""), ("LI", "")])
    main._run_comparison("ba")
    out = main._run_comparison("bb")
    assert out["counts"][R.ADDED] == 0 and out["counts"][R.DELETED_CANDIDATE] == 0
    assert out["counts"][R.NOT_COMPARED] == 3
    rev = c.get("/jobs/bb/revision").json()
    assert rev["compare_basis"] == "NONE" and rev["deleted_candidates"] == []
    rows = c.get("/jobs/bb/rows?tab=ALL").json()
    assert {r["rev"]["state"] for r in rows} == {R.NOT_COMPARED}


def test_run_comparison_passes_tagged_from_mode_facts():
    body = MAIN[MAIN.index("def _run_comparison("):]
    body = body[:body.index("\ndef ")]
    assert 'tagged = _mode_facts(job).get("effective") == "epc"' in body
    assert "tagged=tagged" in body


# ------------------------------------------------------------------ ⑤ screen
def test_side_by_side_is_offered_only_for_tag_comparisons():
    i = JS.index("function renderRevSwitch()")
    body = JS[i:JS.index("\n}\n", i) + 3]
    assert 'const tagOnly = (S.rev || {}).compare_basis === "TAG";' in body
    assert "(tagOnly ? `<button type=\"button\" class=\"side" in body
    for fn in ("function autoSide()", "function toggleSide(on, manual)"):
        j = JS.index(fn)
        fb = JS[j:JS.index("\n}\n", j) + 3]
        assert 'compare_basis !== "TAG") return;' in fb, fn
    assert "NOT_COMPARED" in JS and "대조 안 함" in JS


# ------------------------------------------------------------------ ⑥ output
def test_not_compared_rows_leave_excel_and_export_untouched():
    assert excel_out.revision_remark({"rev": {"state": "NOT_COMPARED", "reason": "태그 없음"},
                                      "rev_against": "Rev.A"}) == ""
    assert excel_out.REVISION_FILL.get("NOT_COMPARED") is None
    src = (ROOT / "app/revision_export.py").read_text(encoding="utf-8")
    assert "대조 안 함 (태그 없음)" in src and "짝 — 기하" not in src
