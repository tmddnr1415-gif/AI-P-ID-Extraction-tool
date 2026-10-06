"""hotfix43 — 개정의 '수정' 은 태그가 달라진 행뿐이다.

사용자 확정: *"위치변경이 아니라, tag number 변경 또는 기존에 없었던 tag 가
추가되었거나 삭제되었을 때만 수정사항으로 간주한다."*  QFE 실측에서 hotfix38 의
수정 458 중 411 이 Description 재생성이었다 — 도면이 아니라 우리 문장이 바뀐 것.
"""
import ast
import inspect
from pathlib import Path

from app import revisions as R
from app import excel_out

ROOT = Path(__file__).resolve().parents[1]
DWG = "1A1Y-11LBB50-M05-0001"


def row(key, type_, x, y, tag="", **kw):
    return dict({"key": key, "drawing_no": DWG, "type": type_, "page_no": 1, "tab": "FIELD",
                 "rect": [x, y, x + 34, y + 11], "tag_no": tag, "description": "",
                 "qty": 1, "scope": "SCT"}, **kw)


def _ab(a, b):
    reg = R.Registry()
    R.compare(a, reg, "Rev.A", compared_with="")
    return R.compare(b, reg, "Rev.B", compared_with="Rev.A"), reg


def test_only_tag_no_decides_the_state():
    """상태를 가르는 칸은 `tag_no` 하나다 — 튜플에 적혀 있고 다른 칸은 들지 않는다."""
    assert R.STATE_FIELDS == ("tag_no",)
    assert set(R.COMPARED_FIELDS) > set(R.STATE_FIELDS)


def test_description_qty_scope_changes_are_recorded_but_not_modifications():
    """같은 태그 · 수량 · SCOPE · Description 이 다 달라도 변경 없음.  차이는 `field_diffs` 로."""
    a = [row("a", "PIT", 100, 100, "11LBB50CP001", qty=1, scope="SCT", description="옛 문장")]
    b = [row("b", "PIT", 100, 100, "11LBB50CP001", qty=2, scope="VENDOR(X)", description="새 문장")]
    out, _ = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.UNCHANGED and st["basis"] == "TAG"
    assert st["changed"] == []
    assert sorted(c["field"] for c in st["field_diffs"]) == ["description", "qty", "scope"]
    assert out["counts"][R.MODIFIED] == 0 and out["counts"][R.UNCHANGED] == 1


def test_a_move_alone_is_never_a_modification_even_far_inside_the_radius():
    a = [row("a", "PIT", 100, 100, "11LBB50CP001")]
    b = [row("b", "PIT", 118, 104, "11LBB50CP001")]
    out, _ = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.UNCHANGED and st["moved_pt"] > 15 and st["changed"] == []


def test_a_tag_change_on_the_same_symbol_is_a_modification_with_was_and_now():
    a = [row("a", "PIT", 100, 100, "11LBB50CP001")]
    b = [row("b", "PIT", 101, 100, "11LBB50CP009")]
    out, _ = _ab(a, b)
    st = out["states"]["b"]
    assert st["state"] == R.MODIFIED
    assert st["changed"] == [{"field": "tag_no", "was": "11LBB50CP001", "now": "11LBB50CP009"}]
    assert st["field_diffs"] == []


def test_a_tag_that_appears_on_a_formerly_untagged_symbol_is_a_modification():
    """없던 태그가 생긴 것 — 태그가 달라진 것이다 (빈칸 → 값)."""
    a = [row("a", "PIT", 100, 100)]
    b = [row("b", "PIT", 100, 100, "11LBB50CP001")]
    out, _ = _ab(a, b)
    assert out["states"]["b"]["state"] == R.MODIFIED
    assert out["states"]["b"]["changed"][0]["now"] == "11LBB50CP001"


def test_added_and_deleted_tags_still_count_and_untagged_documents_only_add_or_delete():
    """태그 추가 → ADDED · 태그 사라짐 → 삭제 후보.  태그 없는 문서(AL NOUF1)는
    수정이 구조적으로 0 — 기하 짝은 태그가 둘 다 비어 달라질 수 없다."""
    a = [row("a1", "PIT", 100, 100, "11LBB50CP001"), row("a2", "TIT", 300, 100, "11LBB50CT001")]
    b = [row("b1", "PIT", 100, 100, "11LBB50CP001"), row("b3", "LIT", 500, 100, "11LBB50CL001")]
    out, _ = _ab(a, b)
    assert out["states"]["b3"]["state"] == R.ADDED
    assert [d["tag_no"] for d in out["deleted_candidates"]] == ["11LBB50CT001"]
    # 태그 없는 문서
    a = [row("a1", "PI", 100, 100, description="x"), row("a2", "PI", 100, 300, description="y")]
    b = [row("b1", "PI", 100, 102, description="x2"), row("b2", "PI", 104, 300, description="y2"),
         row("b3", "PI", 800, 800)]
    out, _ = _ab(a, b)
    assert out["counts"] == {R.UNCHANGED: 2, R.ADDED: 1, R.MODIFIED: 0, R.DELETED_CANDIDATE: 0} \
        or (out["counts"][R.MODIFIED] == 0 and out["counts"][R.ADDED] == 1 and out["counts"][R.UNCHANGED] == 2)


def test_the_history_and_the_db_keep_field_diffs_apart_from_the_state(tmp_path):
    """장부 이력과 DB 행이 `field_diffs` 를 따로 든다 — 상태 칸(`changed`)에 섞지 않는다."""
    a = [row("a", "PIT", 100, 100, "11LBB50CP001", qty=1)]
    b = [row("b", "PIT", 100, 100, "11LBB50CP001", qty=4)]
    out, reg = _ab(a, b)
    hist = next(iter(reg.data["ids"].values()))["history"][-1]
    assert hist["state"] == R.UNCHANGED and hist["changed"] == [] \
        and hist["field_diffs"][0]["field"] == "qty"
    # DB 왕복
    from app import db
    con = db.connect(tmp_path / "t.sqlite")
    db.store_revision_result(con, "j", {"states": out["states"], "deleted_candidates": []})
    back = db.revision_states(con, "j")["b"]
    assert back["state"] == R.UNCHANGED and back["changed"] == [] \
        and back["field_diffs"][0]["field"] == "qty"


def test_the_excel_remark_names_the_tag_change():
    assert excel_out.revision_remark(
        {"rev": {"state": "MODIFIED",
                 "changed": [{"field": "tag_no", "was": "", "now": "11LBB50CP001"}]},
         "rev_against": "Rev.A"}) == "Rev.A 대비 수정 (태그 (없음) → 11LBB50CP001)"
    # 값이 다른 칸은 REMARK 에 안 나간다
    assert excel_out.revision_remark(
        {"rev": {"state": "UNCHANGED", "field_diffs": [{"field": "qty", "was": 1, "now": 2}]},
         "rev_against": "Rev.A"}) == ""


def test_the_screen_reads_the_tag_change_and_shows_other_diffs_as_reference_only():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert "function tagChange(rev, side)" in js
    assert "값이 다른 칸 (개정 판정에는 쓰지 않음)" in js
    assert "자리 이동은 수정이 아님" in js
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert "수정만 (태그 바뀜)" in html


def test_compare_decides_the_state_in_one_place():
    """`compare` 안에서 MODIFIED 를 직접 고르는 줄이 없다 — `_revision_state` 하나."""
    src = inspect.getsource(R.compare)
    assert "MODIFIED if" not in src and "_revision_state(" in src
