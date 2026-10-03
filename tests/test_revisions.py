"""리비전 골격 — ID 부여 · 매칭 · 상태 판정.

개정 도면이 없으므로 실측 대조는 하지 않는다.  여기서 지키는 것은 규칙 자체다:
같은 입력이면 같은 ID, 번호는 재부여하지 않는다, 비교 대상이 없으면 표기가
붙지 않는다, 삭제는 후보까지만.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import revisions as R


def row(key, dwg, type_, x, y, **kw):
    return dict({"key": key, "drawing_no": dwg, "type": type_, "page_no": 1,
                 "tab": "FIELD", "rect": [x, y, x + 68, y + 22.6],
                 "description": ""}, **kw)


def base_rows():
    return [row("a", "D00P-10LBA10-M05-0001", "PI", 100, 100),
            row("b", "D00P-10LBA10-M05-0001", "PI", 100, 400),
            row("c", "D00P-10LBA10-M05-0001", "TIT", 600, 100),
            row("d", "D00P-00PAB10-M05-0001", "PIT", 100, 100)]


def test_the_system_code_comes_from_the_drawing_number():
    assert R.system_code("D00P-10LBA10-M05-0001")[0] == "10LBA10"
    assert R.system_code("1A46-00PAB10-M05-0002")[0] == "00PAB10"
    # 형식이 다르면 조용히 실패하지 않고 도면번호 전체를 쓰고 그 사실을 적는다
    code, basis = R.system_code("weird")
    assert code == "weird" and "떼지 못함" in basis


def test_ids_are_stable_across_two_identical_runs():
    """부여 순서가 결정적이어야 두 번 넣은 같은 도면이 같은 장부를 만든다."""
    made = []
    for _ in range(2):
        reg = R.Registry()
        R.compare(base_rows(), reg, "Rev.A", compared_with="")
        made.append(json.dumps(reg.data["ids"], sort_keys=True))
    assert made[0] == made[1]


def test_a_first_revision_marks_nothing():
    """Rev.A 는 비교 대상이 없다.  어디에도 표기가 붙지 않아야 한다."""
    reg = R.Registry()
    out = R.compare(base_rows(), reg, "Rev.A", compared_with="")
    assert out["baseline"] is True
    assert {s["state"] for s in out["states"].values()} == {R.BASELINE}
    assert out["deleted_candidates"] == []


def test_the_same_drawing_twice_is_all_unchanged():
    """가장 값싼 검증: 같은 것을 두 번 넣으면 아무 변화도 없어야 한다."""
    reg = R.Registry()
    R.compare(base_rows(), reg, "Rev.A", compared_with="")
    out = R.compare(base_rows(), reg, "Rev.B", compared_with="Rev.A")
    assert out["counts"][R.UNCHANGED] == 4
    assert out["counts"][R.ADDED] == 0
    assert out["counts"][R.MODIFIED] == 0
    assert out["counts"][R.DELETED_CANDIDATE] == 0


def test_new_rows_take_the_next_number_and_deletions_never_give_theirs_back():
    """번호는 단조 증가한다 - 가운데에 끼워 넣으면 뒤가 전부 밀린다."""
    reg = R.Registry()
    R.compare(base_rows(), reg, "Rev.A", compared_with="")
    first = {r["id"] for r in reg.data["ids"].values()}
    # 하나 지우고 하나 더한다
    rows = [r for r in base_rows() if r["key"] != "a"]
    rows.append(row("new", "D00P-10LBA10-M05-0001", "PI", 900, 900))
    out = R.compare(rows, reg, "Rev.B", compared_with="Rev.A")
    added = [s["id"] for s in out["states"].values() if s["state"] == R.ADDED]
    assert added == ["10LBA10-004"], added         # 003 다음이지 001 재사용이 아니다
    assert first <= set(reg.data["ids"])           # 옛 ID 는 그대로 남는다
    assert out["counts"][R.DELETED_CANDIDATE] == 1


def test_a_changed_value_is_a_modification_but_a_move_is_not():
    """움직인 거리는 기록만 한다 - 임계값에 근거가 없다."""
    reg = R.Registry()
    R.compare(base_rows(), reg, "Rev.A", compared_with="")
    rows = base_rows()
    rows[0]["description"] = "고쳐진 문장"
    rows[1]["rect"] = [105, 405, 173, 427.6]        # 반경 안에서 이동
    out = R.compare(rows, reg, "Rev.B", compared_with="Rev.A")
    assert out["states"]["a"]["state"] == R.MODIFIED
    assert out["states"]["a"]["changed"][0]["field"] == "description"
    assert out["states"]["b"]["state"] == R.UNCHANGED
    assert out["states"]["b"]["moved_pt"] > 0       # 기록은 남는다


def test_a_deleted_candidate_carries_the_evidence_a_person_needs():
    """검출 실패와 실제 삭제를 사람이 가르려면 셋이 필요하다."""
    reg = R.Registry()
    R.compare(base_rows(), reg, "Rev.A", compared_with="")
    out = R.compare([r for r in base_rows() if r["key"] != "c"], reg, "Rev.B",
                    compared_with="Rev.A")
    d = out["deleted_candidates"][0]
    assert d["anchor"] and d["radius"] > 0 and d["radius_source"]
    assert "nearest_distance" in d
    assert d["confirmed"] is False                  # 자동으로 굳지 않는다


def test_the_match_radius_is_measured_on_the_drawing_not_chosen():
    info = R.match_radius(base_rows())
    assert info["source"] == "DRAWING_BUBBLE"
    assert info["radius"] == pytest.approx(68.0)    # 이 행들의 버블 긴변
    assert info["nearest_same_type"] is not None    # 다른 쪽 값도 함께 보고된다


def test_a_project_is_not_overwritten(tmp_path):
    R.create_project(tmp_path, "AL NOUF1")
    with pytest.raises(FileExistsError):
        R.create_project(tmp_path, "AL NOUF1")
    assert [p["name"] for p in R.list_projects(tmp_path)] == ["AL NOUF1"]


def test_a_project_name_cannot_escape_its_directory(tmp_path):
    for bad in ("../evil", "a/b", "", "..", "x\0y"):
        with pytest.raises(ValueError):
            R.create_project(tmp_path, bad)


def test_the_registry_is_byte_identical_when_saved_twice(tmp_path):
    reg = R.Registry()
    R.compare(base_rows(), reg, "Rev.A", compared_with="")
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    reg.save(a)
    reg.save(b)
    assert a.read_bytes() == b.read_bytes()


def test_excel_numbers_follow_the_same_rule_as_ids():
    reg = R.Registry()
    rows = base_rows()
    out = R.compare(rows, reg, "Rev.A", compared_with="")
    for r in rows:
        r["stable_id"] = out["states"][r["key"]]["id"]
        r["system"] = ""
    nums = R.assign_excel_numbers(rows, reg)
    assert sorted(nums.values()) == [1, 2, 3, 4]
    # 다시 매기지 않는다: 같은 행은 같은 번호를 유지한다
    again = R.assign_excel_numbers(rows, reg)
    assert again == nums
