"""hotfix38 — 개정 대조에서 태그가 곧 이름이다 (§10 1급).

사용자 요구: QFE 260112(Rev.A) 뒤에 260326(Rev.B)을 넣으면 **무엇이 삭제되고
추가됐는지** 정확히 가르고, 삭제는 목록 + Remark 로, 추가는 도면 라벨 + 목록으로.

지키는 규칙:
  · 태그가 유일하면 태그로 짝짓고 거리는 보지 않는다 (옮겨도 같은 항목).
  · 같은 태그가 둘 이상이면 어느 것이 어느 것인지 도면이 말하지 않으므로 기하로.
  · 둘 다 태그가 있는데 다르면 가까워도 짝이 아니다 — 삭제 + 추가이고 근거에 남는다.
  · 태그 없는 행(2급 문서 전부)은 예전 그대로 — 기하 결과가 한 칸도 안 바뀐다.
  · 근거(basis · reason · tag_elsewhere)는 결과에 그대로 실린다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import revisions as R
from app import excel_out

DWG = "1A1Y-10LBB50-M05-0001"


def row(key, type_, x, y, tag="", dwg=DWG, **kw):
    return dict({"key": key, "drawing_no": dwg, "type": type_, "page_no": 1,
                 "tab": "FIELD", "rect": [x, y, x + 34, y + 11],
                 "tag_no": tag, "description": ""}, **kw)


def _ab(rows_a, rows_b):
    reg = R.Registry()
    R.compare(rows_a, reg, "Rev.A", compared_with="")
    return R.compare(rows_b, reg, "Rev.B", compared_with="Rev.A"), reg


def test_a_tagged_symbol_that_moved_across_the_sheet_keeps_its_id():
    """반경(심볼 한 개 크기) 밖으로 옮겨도 같은 태그면 같은 항목이다."""
    a = [row("a", "PIT", 100, 100, "11LBB50CP001")]
    b = [row("b", "PIT", 900, 700, "11LBB50CP001")]
    out, reg = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.UNCHANGED and st["basis"] == "TAG"
    assert st["moved_pt"] > 500
    assert out["deleted_candidates"] == []
    assert len(reg.data["ids"]) == 1


def test_a_loop_shared_tag_is_split_by_type():
    """hotfix35 — PI 와 PIT 가 같은 태그를 든다.  (TYPE, 태그) 라야 둘이 갈린다."""
    a = [row("a1", "PI", 100, 100, "11LBB50CP001"),
         row("a2", "PIT", 100, 140, "11LBB50CP001")]
    b = [row("b1", "PIT", 500, 500, "11LBB50CP001"),
         row("b2", "PI", 500, 540, "11LBB50CP001")]
    out, _ = _ab(a, b)
    assert {k: v["state"] for k, v in out["states"].items()} == {
        "b1": R.UNCHANGED, "b2": R.UNCHANGED}
    assert all(v["basis"] == "TAG" for v in out["states"].values())


def test_duplicate_tags_fall_back_to_geometry_and_say_so():
    """한 태그를 두 버블에 찍는 문서(UAD p30) — 태그로는 못 가르고 기하로 간다."""
    a = [row("a1", "LS", 100, 100, "00GKB01CL001"),
         row("a2", "LS", 100, 400, "00GKB01CL001")]
    b = [row("b1", "LS", 102, 101, "00GKB01CL001"),
         row("b2", "LS", 101, 402, "00GKB01CL001")]
    out, _ = _ab(a, b)
    assert all(v["state"] == R.UNCHANGED and v["basis"] == "GEOMETRY"
               for v in out["states"].values())
    info = out["radii"][DWG]
    assert info["tag_duplicates"]["rows"] == [("LS", "00GKB01CL001")]
    assert info["matched_by"] == {"TAG": 0, "GEOMETRY": 2}


def test_a_different_tag_at_the_same_spot_is_delete_plus_add_not_modify():
    """1급 문서에서 이름이 다른 것은 다른 항목이다.  막은 쌍은 근거에 남는다."""
    a = [row("a", "PIT", 100, 100, "11LBB50CP001")]
    b = [row("b", "PIT", 101, 100, "11LBB50CP009")]
    out, _ = _ab(a, b)
    assert out["states"]["b"]["state"] == R.ADDED
    assert "11LBB50CP009" in out["states"]["b"]["reason"]
    assert len(out["deleted_candidates"]) == 1
    d = out["deleted_candidates"][0]
    assert d["tag_no"] == "11LBB50CP001" and d["basis"] == "TAG"
    assert d["tag_elsewhere"] == []
    blocked = out["radii"][DWG]["tag_blocked"]
    assert blocked and blocked[0]["was"] == "11LBB50CP001" \
        and blocked[0]["now"] == "11LBB50CP009"


def test_a_tag_that_moved_to_another_drawing_is_named_in_the_candidate():
    """삭제 후보가 든 태그가 다른 도면에 섰으면 '옮김일 수 있다' 고 말할 재료다."""
    other = "1A1Y-10LBB60-M05-0001"
    a = [row("a", "TIT", 100, 100, "11LBB50CT001")]
    b = [row("b", "TIT", 100, 100, "11LBB50CT001", dwg=other)]
    out, _ = _ab(a, b)
    d = out["deleted_candidates"][0]
    assert d["tag_elsewhere"] == [other]
    # 다른 도면이라 짝은 아니다 — 안정 ID 는 도면 단위이고 (§7.3), 새 행은 추가다
    assert out["states"]["b"]["state"] == R.ADDED


def test_untagged_rows_are_judged_exactly_as_before():
    """2급 문서(AL NOUF1 · TC2 · SADARA)는 태그가 없다.  기하 판정이 그대로다."""
    a = [row("a1", "PI", 100, 100), row("a2", "PI", 100, 400),
         row("a3", "TIT", 600, 100)]
    b = [row("b1", "PI", 103, 101), row("b2", "TIT", 600, 100),
         row("b3", "PI", 900, 900)]
    out, _ = _ab(a, b)
    st = {k: v["state"] for k, v in out["states"].items()}
    assert st == {"b1": R.UNCHANGED, "b2": R.UNCHANGED, "b3": R.ADDED}
    assert all(v["basis"] == "GEOMETRY" for v in out["states"].values())
    assert "태그 없음" in out["states"]["b3"]["reason"]
    assert [d["basis"] for d in out["deleted_candidates"]] == ["GEOMETRY"]
    assert out["radii"][DWG]["tag_blocked"] == []


def test_a_tagged_row_and_an_untagged_record_can_still_meet_by_geometry():
    """한쪽만 태그를 들면(옛 장부 · 마크업 행) 태그가 막지 않는다 — 기하로 간다."""
    a = [row("a", "PIT", 100, 100)]
    b = [row("b", "PIT", 102, 100, "11LBB50CP001")]
    out, _ = _ab(a, b)
    assert out["states"]["b"]["state"] == R.MODIFIED        # tag_no 칸이 찼다
    assert out["states"]["b"]["basis"] == "GEOMETRY"


def test_the_excel_remark_leads_with_the_revision_state():
    """Excel REMARK 앞머리 — 추가 · 수정(바뀐 칸) · 삭제(확정).  Rev.A 는 빈칸."""
    assert excel_out.revision_remark({"rev": {"state": "BASELINE"}}) == ""
    assert excel_out.revision_remark({"rev": {"state": "UNCHANGED"},
                                      "rev_against": "Rev.A"}) == ""
    assert excel_out.revision_remark({"rev": {"state": "ADDED"},
                                      "rev_against": "Rev.A"}) == "Rev.A 대비 추가"
    assert excel_out.revision_remark(
        {"rev": {"state": "MODIFIED", "changed": [{"field": "qty"}]},
         "rev_against": "Rev.A"}) == "Rev.A 대비 수정 (qty)"
    assert excel_out.revision_remark({"deleted_confirmed": True,
                                      "rev": {"state": "DELETED"},
                                      "rev_against": "Rev.A"}) == "Rev.A 대비 삭제 (확정)"
    # 앞머리는 `_remark` 를 지나 REMARK 열로 나간다
    r = {"rev": {"state": "ADDED"}, "rev_against": "Rev.A", "review_codes": []}
    assert excel_out._remark(r, {}) == "Rev.A 대비 추가"


def test_the_screen_marks_added_symbols_and_filters_by_state():
    """화면 — 링 위 'ADD' 글자 · '개정' 열 · 개정 필터 · 삭제 행 Remark.  소스로 못박는다."""
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert '["rev_state", "개정", false]' in js
    assert re.search(r'FILTER_COLS = \[[^\]]*"rev_state"', js)
    assert 'tag.textContent = rev === "ADDED" ? "ADD" : "MOD"' in js
    assert "function deletedRemark" in js and "remark: deletedRemark(d, against)" in js
    assert 'id="rev-filter"' in html and 'value="DELETED">삭제만' in html
    # 개정 표기는 한 접근자(`revLabel`)에서 온다 — 그리드 열과 근거 패널이 같이 읽는다
    assert js.count("revLabel(row)") >= 2
