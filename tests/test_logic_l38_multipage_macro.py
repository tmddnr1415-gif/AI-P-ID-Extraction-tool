"""L38 — 내부 동작을 여러 장에 나눠 그린 매크로 (1A5J MACRO-PS3 <PRESELECTION (1/4)> … (4/4)).

부모 장 G001 의 매크로 상자 M: 입력 단자 IN(선 i) → Typical 첫 장(p2) 입력 1행 → NOT → 출력 9행 (TO p3) →
둘째 장(p3) 입력 2행 FM p2-9 → NOT → 출력 5행 → 상자 출력 단자 OUT(선 o) → 부모 출력 20행.
둘째 장의 출력 5행은 첫 장에 없다 — 예전에는 OUT 이 '연결 못 함' 이라 o 가 영영 0 이었다.
"""
from __future__ import annotations

from app.logic import macro, sequence, sim
from tests.test_logic_l22_user import _P, _blk, _sheet


def _bundle(parts=True):
    s1 = _sheet(1, "G001", [{"n": 1, "side": "L", "net": "i", "desc": "START"},
                            {"n": 20, "side": "R", "net": "o", "desc": "PUMP START CMD"}],
                {"M": {**_blk("MACRO", "macro", (200, 100, 260, 200)), "macro": {
                    "sheet": "T1", "page": 2, "title": "MACRO-PS9 <X (1/2)>",
                    "inputs": [{"at": "200,110", "net": "i", "pin": "IN", "row": 1}],
                    "outputs": [{"at": "260,150", "net": "o", "pin": "OUT", "row": 3 * macro.ROW_PAGE + 5 if parts else None}],
                    **({"parts": [2, 3]} if parts else {})}}},
                [_P("M", "i", "in", at=(200, 110)), _P("M", "o", "out", at=(260, 150))])
    s2 = _sheet(2, "T1", [{"n": 1, "side": "L", "net": "a", "desc": "START"},
                          {"n": 9, "side": "R", "net": "b", "desc": "MID", "to": "T2-2"}],
                {"N1": _blk("NOT", "not")}, [_P("N1", "a", "in"), _P("N1", "b", "out")])
    s2["title"] = "MACRO-PS9 <X (1/2)>"
    s3 = _sheet(3, "T2", [{"n": 2, "side": "L", "net": "c", "desc": "MID", "fm": "T1-9",
                           "ref": {"sheet": "T1", "row": 9, "page": 2, "src_row": 9}},
                          {"n": 5, "side": "R", "net": "d", "desc": "OUT"}],
                {"N2": _blk("NOT", "not")}, [_P("N2", "c", "in"), _P("N2", "d", "out")])
    s3["title"] = "MACRO-PS9 <X (2/2)>"
    return [s1, s2, s3]


def _out(sheets, v):
    r = sim.simulate_bundle(sheets, {1: {"row:1": v}}, None, 1)["focus"]
    return r["frames"][-1]["values"].get("o")


def test_body_joins_the_pages_and_the_macro_output_follows_its_input():
    sh = _bundle()
    by = {s["page"]: s for s in sh}
    b = macro.body(by, sh[0]["blocks"]["M"]["macro"])
    assert b["parts"] == [2, 3]
    assert not any(r["n"] == 3 * macro.ROW_PAGE + 2 for r in b["rows"])      # 장 사이 FM 입력 행은 본문 안의 선이 됐다
    assert _out(sh, 1) == 1 and _out(sh, 0) == 0                            # NOT · NOT — 두 장을 지나 입력 그대로


def test_without_parts_the_output_stays_unlinked():
    assert _out(_bundle(parts=False), 1) == 0


def test_family_needs_same_head_and_part_mark_and_same_type():
    t = {"title": "MACRO-PS3 <PRESELECTION (1/4)>"}
    assert macro._family(t, {"title": "MACRO-PS3 <PRESELECTION (2/4)>"}, "")
    assert not macro._family(t, {"title": "MACRO-PS4 <PRESELECTION (2/4)>"}, "")
    assert not macro._family({"title": "MOV BLOCK <TYPE-III-1>"}, {"title": "MOV BLOCK <TYPE-III-2>"}, "")
    assert not macro._family({"title": "MOV BLOCK <TYPE-III-1>"}, {"title": "MOV BLOCK <TYPE-III-1>"}, "")


def test_guided_walk_enters_the_second_page():
    sh = _bundle()
    p = sequence.plan(sh, 1, 20, 1)
    assert p.get("ok")
    keys = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("key"):
                keys.append(n["key"])
            for k in n.get("kids") or []:
                walk(k)
    tree = sequence.link(p)
    walk(tree)
    assert "row:1" in keys
