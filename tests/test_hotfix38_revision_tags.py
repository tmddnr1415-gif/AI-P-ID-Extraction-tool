"""hotfix38 — 개정 대조에서 태그가 곧 이름이다 (§10 1급).

사용자 요구: QFE 260112(Rev.A) 뒤에 260326(Rev.B)을 넣으면 **무엇이 삭제되고
추가됐는지** 정확히 가르고, 삭제는 목록 + Remark 로, 추가는 도면 라벨 + 목록으로.

지키는 규칙 (hotfix46 — 위치로는 비교하지 않는다):
  · 태그가 유일하면 태그로 짝짓고 거리는 보지 않는다 (옮겨도 같은 항목).
  · 같은 태그가 둘 이상이면 어느 것이 어느 것인지 도면이 말하지 않으므로 **대조하지 않는다**.
  · 둘 다 태그가 있는데 다르면 가까워도 **태그 짝**은 아니다.  hotfix47 — 같은 도면에 새 태그와
    사라진 태그가 함께 남으면 태그 변경인지 추가/삭제인지 도면이 가르지 않아 전부 '수정' 이다
    (같은 TYPE 이 하나씩이면 태그가 바뀐 한 항목으로 잇고, 아니면 짝 없이 수정으로만 표기).
  · 태그 없는 행은 대조하지 않는다 (NOT_COMPARED — 추가도 삭제도 아니다).
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


def test_duplicate_tags_are_not_compared_and_say_so():
    """한 태그를 두 버블에 찍는 문서(UAD p30) — 태그로는 못 가르고, 위치로는 비교하지
    않으므로 **대조하지 않는다**."""
    a = [row("a1", "LS", 100, 100, "00GKB01CL001"),
         row("a2", "LS", 100, 400, "00GKB01CL001")]
    b = [row("b1", "LS", 102, 101, "00GKB01CL001"),
         row("b2", "LS", 101, 402, "00GKB01CL001")]
    out, _ = _ab(a, b)
    assert all(v["state"] == R.NOT_COMPARED and v["basis"] == "NONE" and "둘 이상" in v["reason"]
               for v in out["states"].values())
    info = out["radii"][DWG]
    assert info["tag_duplicates"]["rows"] == [("LS", "00GKB01CL001")]
    assert info["matched_by"] == {"TAG": 0, "GEOMETRY": 0, "NOT_COMPARED": 2}
    assert out["deleted_candidates"] == []          # 겹친 태그의 옛 기록도 삭제 후보가 아니다


def test_a_different_tag_on_the_only_symbol_of_its_type_is_a_modification():
    """같은 심볼에 번호만 다시 매긴 것 (QFE `00GHC36CF001` → `10GHC42CF101`).  hotfix46 은
    위치로 잇지 않아 삭제 후보 + 추가였고, hotfix47 은 **같은 도면의 유일한 PIT 끼리** 태그가
    바뀐 한 항목으로 잇는다 — 자리가 아니라 "그 TYPE 이 하나씩 남았다" 가 근거다."""
    a = [row("a", "PIT", 100, 100, "11LBB50CP001")]
    b = [row("b", "PIT", 900, 900, "11LBB50CP009")]        # 자리는 멀어도 같다
    out, reg = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.MODIFIED and st["basis"] == R.BASIS_TYPE
    assert st["changed"] == [{"field": "tag_no", "was": "11LBB50CP001", "now": "11LBB50CP009"}]
    assert out["deleted_candidates"] == []
    assert len(reg.data["ids"]) == 1
    assert out["radii"][DWG]["ambiguous"] is True and out["radii"][DWG]["type_pairs"] == 1


def test_a_tag_pair_that_agrees_is_the_only_pair():
    """태그가 같은 쌍만 짝이다.  자리를 바꿔 앉아도 태그가 가른다."""
    a = [row("a1", "PIT", 100, 100, "11LBB50CP001"),
         row("a2", "PIT", 100, 130, "11LBB50CP002")]
    # CP002 가 CP001 의 옛 자리로 왔고 CP001 은 사라졌다, 새 CP003 이 CP002 자리에
    b = [row("b1", "PIT", 100, 100, "11LBB50CP002"),
         row("b2", "PIT", 100, 130, "11LBB50CP003")]
    out, _ = _ab(a, b)
    assert out["states"]["b1"]["state"] == R.UNCHANGED and out["states"]["b1"]["basis"] == "TAG"
    assert out["states"]["b1"]["moved_pt"] == 30.0      # 기록만
    # hotfix47 — CP001 이 사라지고 CP003 이 섰다: 같은 도면의 유일한 PIT 끼리라 태그가 바뀐 한 항목
    assert out["states"]["b2"]["state"] == R.MODIFIED and out["states"]["b2"]["basis"] == R.BASIS_TYPE
    assert out["deleted_candidates"] == []


def test_a_renumbered_sheet_is_recognised_by_its_tags_and_keeps_its_ids():
    """QFE — `30GKC10-M05-0001` 이 `…-0201` 로 (같은 장 · 태그 17/22 공유).
    도면번호로만 묶으면 22행이 삭제 + 추가다."""
    old, new = "1A1Y-30GKC10-M05-0001", "1A1Y-30GKC10-M05-0201"
    a = [row(f"a{i}", "PIT", 100 + 40 * i, 100, f"31GKC20CP00{i}", dwg=old) for i in range(5)]
    b = [row(f"b{i}", "PIT", 300 + 40 * i, 500, f"31GKC20CP00{i}", dwg=new) for i in range(4)] \
        + [row("b9", "PIT", 700, 700, "31GKC20CP009", dwg=new)]
    out, reg = _ab(a, b)
    assert out["sheets"]["renumbered"] == [{"before": old, "now": new, "shared": 4,
                                           "before_tags": 5, "now_tags": 5}]
    assert out["sheets"]["only_before"] == [] and out["sheets"]["only_now"] == []
    st = {k: v["state"] for k, v in out["states"].items()}
    # hotfix47 — CP004 가 사라지고 CP009 가 섰다 (유일한 PIT 끼리) → 태그가 바뀐 한 항목
    assert st == {"b0": R.UNCHANGED, "b1": R.UNCHANGED, "b2": R.UNCHANGED,
                  "b3": R.UNCHANGED, "b9": R.MODIFIED}
    assert all(v.get("sheet_renumbered_from") == old for k, v in out["states"].items())
    assert out["deleted_candidates"] == []
    recs = [r for r in reg.data["ids"].values() if r["drawing_no"] == new]
    assert len(recs) == 5 and all(r["id"].startswith("30GKC10-") for r in recs)
    assert recs[0]["renumbered"] == [{"revision": "Rev.B", "from": old, "to": new}]


def test_sheets_without_shared_tags_are_not_paired_even_with_the_same_title():
    """`…-0004` ↔ `…-0204` — 공유 태그 0.  제목이 같아도 근거가 아니다."""
    old, new = "1A1Y-30GKC10-M05-0004", "1A1Y-30GKC10-M05-0204"
    a = [row("a", "PIT", 100, 100, "31GKC20CP001", dwg=old)]
    b = [row("b", "PIT", 100, 100, "31GKC20CP002", dwg=new)]
    out, _ = _ab(a, b)
    assert out["sheets"]["renumbered"] == []
    assert out["sheets"]["only_before"] == [old] and out["sheets"]["only_now"] == [new]
    assert out["states"]["b"]["state"] == R.ADDED and len(out["deleted_candidates"]) == 1


def test_a_tag_that_moved_to_another_drawing_is_named_in_the_candidate():
    """삭제 후보가 든 태그가 다른 도면에 섰으면 '옮김일 수 있다' 고 말할 재료다."""
    other = "1A1Y-10LBB60-M05-0001"
    a = [row("a", "TIT", 100, 100, "11LBB50CT001"), row("a2", "PIT", 500, 500, "11LBB50CP001"),
         row("o", "PIT", 100, 100, "11LBB60CP001", dwg=other)]
    b = [row("b", "TIT", 100, 100, "11LBB50CT001", dwg=other), row("b2", "PIT", 500, 500, "11LBB50CP001"),
         row("o2", "PIT", 100, 100, "11LBB60CP001", dwg=other)]
    out, _ = _ab(a, b)
    d = out["deleted_candidates"][0]
    assert d["tag_elsewhere"] == [other]
    # 다른 도면이라 짝은 아니다 — 안정 ID 는 도면 단위이고 (§7.3), 새 행은 추가다.
    # 두 장 다 양쪽에 있으므로 "도면번호가 바뀐 장" 도 아니다
    assert out["states"]["b"]["state"] == R.ADDED and out["sheets"]["renumbered"] == []


def test_untagged_rows_are_not_compared():
    """hotfix46 — 태그 없는 행은 대조할 열쇠가 없다.  추가도 삭제도 아니고(NOT_COMPARED),
    위치로 짝짓지 않는다.  태그 없던 옛 기록도 삭제 후보가 아니다."""
    a = [row("a1", "PI", 100, 100), row("a2", "PI", 100, 400),
         row("a3", "TIT", 600, 100)]
    b = [row("b1", "PI", 103, 101), row("b2", "TIT", 600, 100),
         row("b3", "PI", 900, 900)]
    out, _ = _ab(a, b)
    st = {k: v["state"] for k, v in out["states"].items()}
    assert st == {"b1": R.NOT_COMPARED, "b2": R.NOT_COMPARED, "b3": R.NOT_COMPARED}
    assert all(v["basis"] == "NONE" and "태그 없음" in v["reason"] for v in out["states"].values())
    assert out["deleted_candidates"] == []
    assert out["radii"][DWG]["matched_by"] == {"TAG": 0, "GEOMETRY": 0, "NOT_COMPARED": 3}
    assert out["counts"][R.NOT_COMPARED] == 3 and out["counts"][R.ADDED] == 0


def test_a_tagged_row_and_an_untagged_record_do_not_meet():
    """한쪽만 태그를 들면(옛 장부 · 마크업 행) 짝이 없다 — 위치로는 잇지 않는다.
    새 행은 추가이고, 태그 없던 기록은 삭제 후보가 아니다."""
    a = [row("a", "PIT", 100, 100)]
    b = [row("b", "PIT", 102, 100, "11LBB50CP001")]
    out, _ = _ab(a, b)
    assert out["states"]["b"]["state"] == R.ADDED and out["states"]["b"]["basis"] == "TAG"
    assert out["deleted_candidates"] == []


def test_the_excel_remark_leads_with_the_revision_state():
    """Excel REMARK 앞머리 — 추가 · 수정(바뀐 칸) · 삭제(확정).  Rev.A 는 빈칸."""
    assert excel_out.revision_remark({"rev": {"state": "BASELINE"}}) == ""
    assert excel_out.revision_remark({"rev": {"state": "UNCHANGED"},
                                      "rev_against": "Rev.A"}) == ""
    assert excel_out.revision_remark({"rev": {"state": "ADDED"},
                                      "rev_against": "Rev.A"}) == "Rev.A 대비 추가"
    assert excel_out.revision_remark(
        {"rev": {"state": "MODIFIED",
                 "changed": [{"field": "tag_no", "was": "11LBB50CP001", "now": "11LBB50CP009"}]},
         "rev_against": "Rev.A"}) == "Rev.A 대비 수정 (태그 11LBB50CP001 → 11LBB50CP009)"
    # 옛 분석(hotfix38 이전)이 남긴 다른 칸 이름은 이름 그대로
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


def test_a_recompare_starts_from_the_registry_as_it_was_before_that_revision(tmp_path):
    """같은 리비전을 두 번 대조해도 결과가 같다 — 장부 사본에서 시작하기 때문이다."""
    reg_path = tmp_path / "id_registry.json"
    reg = R.Registry(); R.compare(base_rows_a(), reg, "Rev.A", compared_with=""); reg.save(reg_path)
    before = R.registry_snapshot_path(reg_path, "Rev.B")
    assert before.name == "id_registry.before_Rev.B.json"
    results = []
    for _ in range(2):
        if before.exists():
            reg = R.Registry.load(before)
        else:
            reg = R.Registry.load(reg_path); reg.save(before)
        out = R.compare(base_rows_b(), reg, "Rev.B", compared_with="Rev.A")
        reg.save(reg_path)
        results.append(({k: v["state"] for k, v in out["states"].items()},
                        sorted(d["id"] for d in out["deleted_candidates"])))
    assert results[0] == results[1]
    # hotfix47 — TIT 하나가 사라지고 TIT 하나가 섰다 → 태그가 바뀐 한 항목(수정).  두 번째에도 같다
    assert results[0][0]["n"] == R.MODIFIED
    # 사본 없이 이어 대조하면 직전 대조가 장부에 적은 새 태그가 살아 있어 "변경 없음" 이 된다 (옛 결함)
    reg = R.Registry.load(reg_path)
    out = R.compare(base_rows_b(), reg, "Rev.B", compared_with="Rev.A")
    assert out["states"]["n"]["state"] == R.UNCHANGED


def base_rows_a():
    return [row("a", "PIT", 100, 100, "11LBB50CP001"), row("b", "TIT", 400, 100, "11LBB50CT001")]


def base_rows_b():
    return [row("a2", "PIT", 100, 100, "11LBB50CP001"), row("n", "TIT", 800, 800, "11LBB50CT009")]
