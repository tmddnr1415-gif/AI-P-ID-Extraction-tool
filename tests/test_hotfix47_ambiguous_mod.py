"""hotfix47 — 같은 도면에서 짝 없는 태그가 양쪽에 남으면 **전부 '수정'(MOD)** 이다.

사용자 (QFE p41 `30GKC10-M05-0203` ↔ Rev.A p40 — 추가 4 · 삭제 34 가 ADD/DEL? 로 보이던 것):
*"이런 사항들은 tag 가 변경된 것이다.  하지만 tag 변경인지, 삭제 추가인지 확인이 어려우니
이런 사항들은 모두 MOD 로 변경으로만 표기한다."*
그리고 (QFE p89 PI): *"이 PI 는 Tag number 도 이전과 최신이 같다.  변경된 것은 단순 pdf 에서의
위치이다.  이런 사항은 변경으로 표기하지 않는다."*

지키는 것:
  ① 같은 (TYPE, 태그)가 양쪽에 있으면 어디로 움직였든 변경 없음 (hotfix46 그대로)
  ② 한 도면에 새 태그와 사라진 태그가 **함께** 남으면 — 새 태그 행은 MODIFIED(basis AMBIGUOUS),
     사라진 태그 기록은 `deleted_candidates` 에 `state: MODIFIED`(이전 태그) 로.  추가 0 · 삭제 후보 0
  ③ 같은 TYPE 의 짝 없는 행·기록이 **하나씩**이면 태그가 바뀐 한 항목으로 잇는다 (basis TYPE · 안정 ID 유지)
  ④ 한쪽만 남으면 예전 그대로 — 새 태그만 = 추가 (p89 20PGD46/56) · 사라진 태그만 = 삭제 후보
  ⑤ 위치는 어디서도 보지 않는다 (판정 함수에 좌표를 읽는 줄이 없다)
  ⑥ 화면·Excel 은 서버의 `state` 를 읽어 MOD 로 그린다 — DEL? 는 삭제 후보에만
"""
from __future__ import annotations

import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import revisions as R
from app import excel_out
from app import revision_export

JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
DWG = "1A1Y-30GKC10-M05-0203"


def row(key, type_, x, y, tag="", dwg=DWG):
    return {"key": key, "drawing_no": dwg, "type": type_, "page_no": 1, "tab": "FIELD",
            "rect": [x, y, x + 34, y + 11], "tag_no": tag, "description": ""}


def _ab(a, b):
    reg = R.Registry()
    R.compare(a, reg, "Rev.A", compared_with="")
    return R.compare(b, reg, "Rev.B", compared_with="Rev.A"), reg


# ------------------------------------------------------------------ ①
def test_same_tag_anywhere_on_the_sheet_is_unchanged_even_next_to_changes():
    a = [row("a1", "PI", 648, 486, "20PGD41CP501"), row("a2", "LS", 100, 900, "31GKC41CL101")]
    b = [row("b1", "PI", 401, 486, "20PGD41CP501"), row("b2", "LSN", 100, 900, "31GKC41CL102")]
    out, _ = _ab(a, b)
    assert out["states"]["b1"]["state"] == R.UNCHANGED and out["states"]["b1"]["basis"] == "TAG"
    assert out["states"]["b1"]["moved_pt"] == 247.0           # 기록만


# ------------------------------------------------------------------ ②
def test_new_and_vanished_tags_on_one_sheet_are_all_modifications():
    """p41 꼴 — LS/LSN/LSLL 이 새로 서고 LSHH/LSH/LSN/LSL/LSLL/LICA 가 사라졌다 (TYPE 수가 안 맞는다)."""
    a = [row(f"a{i}", t, 100, 100 + 30 * i, f"31GKC41CL1{i:02d}")
         for i, t in enumerate(["LSHH", "LSH", "LSN", "LSL", "LSLL", "LICA"])]
    b = [row(f"b{i}", t, 500, 100 + 30 * i, f"31GKC42CL2{i:02d}") for i, t in enumerate(["LS", "LSN", "LSLL"])]
    out, reg = _ab(a, b)
    assert out["counts"][R.ADDED] == 0 and out["counts"][R.DELETED_CANDIDATE] == 0
    assert out["counts"][R.MODIFIED] == 3 and out["counts"]["MODIFIED_BEFORE"] == 4
    # LSN · LSLL 은 하나씩이라 태그가 바뀐 한 항목으로 이어진다 (ID 유지) · LS 는 짝 없이 변경
    st = out["states"]
    assert st["b1"]["basis"] == R.BASIS_TYPE and st["b1"]["changed"][0]["was"] == "31GKC41CL102"
    assert st["b2"]["basis"] == R.BASIS_TYPE and st["b2"]["changed"][0]["was"] == "31GKC41CL104"
    assert st["b0"]["basis"] == R.BASIS_AMBIGUOUS and st["b0"]["changed"] == []
    assert "가르지 않아 변경으로만 표기" in st["b0"]["reason"]
    # 사라진 넷은 삭제 후보가 아니라 '수정 (이전 태그)' — 같은 도면의 새 태그를 후보로 든다
    gone = out["deleted_candidates"]
    assert sorted(d["type"] for d in gone) == ["LICA", "LSH", "LSHH", "LSL"]
    assert all(d["state"] == R.MODIFIED and d["basis"] == R.BASIS_AMBIGUOUS and d["ambiguous"] for d in gone)
    assert all(d["tag_candidates"] == ["31GKC42CL200"] for d in gone)     # 짝지어진 LSN·LSLL 은 후보가 아니다
    assert all(d["confirmed"] is False for d in gone)                     # 삭제로 굳히는 길은 사람에게 남는다
    assert out["radii"][DWG]["ambiguous"] is True and out["radii"][DWG]["type_pairs"] == 2
    # 장부: 짝지어진 둘은 새 태그를, 나머지 넷은 변경 기록을 든다
    assert sum(1 for r in reg.data["ids"].values() if r["history"][-1].get("ambiguous")) == 4


# ------------------------------------------------------------------ ③
def test_the_only_pair_of_a_type_keeps_its_stable_id():
    a = [row("a", "LICA", 100, 100, "31GKC41CL105")]
    b = [row("b", "LICA", 900, 900, "31GKC42CL205")]
    out, reg = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.MODIFIED and st["basis"] == R.BASIS_TYPE
    assert st["id"] == next(iter(reg.data["ids"]))
    assert "유일한 LICA" in st["reason"] and "위치는 보지 않음" in st["reason"]
    assert reg.data["ids"][st["id"]]["values"]["tag_no"] == "31GKC42CL205"


def test_two_of_a_type_on_each_side_are_not_paired():
    a = [row("a1", "LS", 100, 100, "T1"), row("a2", "LS", 100, 200, "T2")]
    b = [row("b1", "LS", 100, 100, "T3"), row("b2", "LS", 100, 200, "T4")]
    out, reg = _ab(a, b)
    assert all(v["basis"] == R.BASIS_AMBIGUOUS and v["state"] == R.MODIFIED for v in out["states"].values())
    assert len(out["deleted_candidates"]) == 2 and len(reg.data["ids"]) == 4


# ------------------------------------------------------------------ ④
def test_a_sheet_with_only_new_tags_is_still_additions():
    """p89 — Rev.A 에 20PGD46/56 이 인쇄돼 있지 않다 (PDF 낱말 0).  사라진 태그가 없으니 추가다."""
    a = [row("a1", "PI", 648, 486, "20PGD41CP501")]
    b = [row("b1", "PI", 401, 486, "20PGD41CP501"), row("b2", "PI", 797, 486, "20PGD46CP501")]
    out, _ = _ab(a, b)
    assert out["states"]["b2"]["state"] == R.ADDED and out["deleted_candidates"] == []
    assert out["radii"][DWG]["ambiguous"] is False


def test_a_sheet_with_only_vanished_tags_is_still_deletion_candidates():
    a = [row("a1", "PI", 100, 100, "T1"), row("a2", "TI", 100, 200, "T2")]
    b = [row("b1", "PI", 100, 100, "T1")]
    out, _ = _ab(a, b)
    d = out["deleted_candidates"][0]
    assert d["state"] == R.DELETED_CANDIDATE and d["basis"] == "TAG" and d["tag_candidates"] == []
    assert out["counts"][R.DELETED_CANDIDATE] == 1 and out["counts"]["MODIFIED_BEFORE"] == 0


def test_ambiguity_is_per_drawing():
    """다른 도면의 새 태그는 이 도면의 사라진 태그와 무관하다."""
    other = "1A1Y-20PGD10-M05-0002"
    a = [row("a1", "LS", 100, 100, "T1")]
    b = [row("b1", "PI", 100, 100, "T9", dwg=other)]
    out, _ = _ab(a, b)
    assert out["states"]["b1"]["state"] == R.ADDED
    assert out["deleted_candidates"][0]["state"] == R.DELETED_CANDIDATE


# ------------------------------------------------------------------ ⑤
def test_the_leftover_rule_reads_no_coordinates():
    src = inspect.getsource(R._leftovers)
    for word in ("rect", "anchor", "radius", "nearest", "dist"):
        assert word not in src, word


# ------------------------------------------------------------------ ⑥
def test_excel_remark_and_export_say_modification_not_addition_or_deletion():
    rv = {"state": "MODIFIED", "basis": "AMBIGUOUS", "changed": [], "reason": "변경 — …"}
    r = excel_out.revision_remark({"rev": rv, "rev_against": "Rev.A"})
    assert r.startswith("Rev.A 대비 수정") and "추가" not in r.split("(")[0] and "→" not in r
    # 짝이 선 태그 변경은 전 → 후 그대로 (hotfix43)
    rv2 = {"state": "MODIFIED", "basis": "TYPE", "changed": [{"field": "tag_no", "was": "X", "now": "Y"}]}
    assert excel_out.revision_remark({"rev": rv2, "rev_against": "Rev.A"}) == "Rev.A 대비 수정 (태그 X → Y)"
    # 변경 내역 Excel — 사라진 태그 쪽은 '수정 (이전 태그)' 로 적힌다
    import io, openpyxl
    deleted = [{"id": "30GKC10-001", "drawing_no": DWG, "page_no": 41, "type": "LSHH", "tag_no": "31GKC41CL100",
                "state": "MODIFIED", "basis": "AMBIGUOUS", "ambiguous": True, "tag_candidates": ["31GKC42CL200"],
                "tag_elsewhere": [], "tab": "FIELD", "values": {}, "anchor": [1, 2], "confirmed": False},
               {"id": "30GKC10-002", "drawing_no": DWG, "page_no": 41, "type": "PI", "tag_no": "T2",
                "state": "DELETED_CANDIDATE", "basis": "TAG", "ambiguous": False, "tag_candidates": [],
                "tag_elsewhere": [], "tab": "FIELD", "values": {}, "anchor": [1, 2], "confirmed": False}]
    data = revision_export.build({"revision": "Rev.B", "compared_with": "Rev.A", "pdf_name": "x.pdf"},
                                 [], {}, deleted, {}, {}, {"TAG": 0, "NOT_COMPARED": 0})
    wb = openpyxl.load_workbook(io.BytesIO(data))
    states = [wb["삭제"].cell(row=i, column=2).value for i in (2, 3)]
    assert states == ["수정 (이전 태그)", "삭제 후보"]
    summary = {wb["요약"].cell(row=i, column=1).value: wb["요약"].cell(row=i, column=2).value for i in range(1, 14)}
    assert summary["수정 (이전 태그 — 이번 분석에 없음)"] == 1 and summary["삭제 후보"] == 1


def test_the_screen_reads_the_record_state_in_one_place():
    assert "function delState(d)" in JS
    # 그리는 곳들이 그 함수를 읽는다 — DEL? 글자는 삭제 후보에만, 이전 태그는 MOD
    for fn in ("pageChanges", "drawCmpOverlay", "showDeletedEvidence", "deletedRemark", "buildPageSelect"):
        body = JS[JS.index(f"function {fn}("):]
        body = body[:body.index("\nfunction ", 1)]
        assert "delState(" in body, fn
    assert 'tag.textContent = isMod ? "MOD" : (d.confirmed ? "DEL" : "DEL?")' in JS
    assert 'return "수정 (이전 태그)"' in JS
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert "이전 태그 포함" in html
