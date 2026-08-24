"""판정축(describe_axis)의 빠른 단위 시험 — 합성 기하로 판정 트리를 검사한다.

전부 합성 좌표다: PDF 도, 발주처 자료도 필요 없다.  §2.3 경계(순회 없음)와
문형 규칙(FROM 중복 제거 · TYPE 풀네임 · Suffix)이 회귀 대상이다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "engine"))
import describe_axis as ax


class Eq:
    def __init__(self, label, rect):
        self.label, self.rect = label, rect


JS = 0.8


def test_isa_fullname_assembles_from_function_letters():
    assert ax.isa_fullname("PI") == "PRESSURE GAUGE"
    assert ax.isa_fullname("PIT") == "PRESSURE TRANSMITTER"
    assert ax.isa_fullname("PDIT") == "DIFFERENTIAL PRESSURE TRANSMITTER"
    assert ax.isa_fullname("LS") == "LEVEL SWITCH"
    assert ax.isa_fullname("FE") == "FLOW ELEMENT"
    assert ax.isa_fullname("RO") == "RESTRICTION ORIFICE"
    assert ax.isa_fullname("GATE") == "GATE VALVE"


def test_own_body_strokes_do_not_testify():
    # 계기 사각형의 제 변은 후보에서 빠진다 - p6 PIT 가 ④ 가 되던 원인.
    rect = (100, 100, 130, 160)
    edge = ("V", 100.1, 105, 155)          # rect 안의 세로 변
    line = ("V", 90, 50, 300)              # 바깥 세로 라인
    assert ax._own_body(edge, rect, JS)
    assert not ax._own_body(line, rect, JS)


def test_leader_crossing_beats_proximity():
    # 인출선이 라인을 지나쳐 그려져도(실측 4.9pt) 교차는 교차다.
    rect = (100, 100, 120, 120)
    leader = ("V", 110, 120, 140)          # 버블 아래로 내려가 라인을 5pt 지나침
    main = ("H", 135, 20, 400)
    run, how = ax.pick_tap(rect, [main], [leader], JS)
    assert run == main and how == "leader"


def test_inline_symbol_taps_the_line_through_it():
    # 라인이 심볼에서 끊겨 마주보면 - 한 라인으로 병합해 탭한다.
    rect = (200, 95, 240, 125)
    left = ("H", 110, 20, 199)
    right = ("H", 110, 241, 400)
    run, how = ax.pick_tap(rect, [left, right], [], JS)
    assert how == "inline" and run[2] == 20 and run[3] == 400


def test_fromto_reads_both_connector_ends():
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 400)]
    conns = [((0, 100, 18, 120), "FROM HRSG#12"),
             ((402, 100, 460, 120), "TO HP BYPASS#12")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_FROMTO
    # 선두 FROM/TO 는 벗겨져 문장에서 중복되지 않는다
    assert v["src"] == "HRSG#12" and v["dst"] == "HP BYPASS#12"
    s = ax.sentence(v, "PIT")
    assert s == "FROM HRSG#12 TO HP BYPASS#12 PRESSURE TRANSMITTER"
    assert "FROM FROM" not in s and "TO TO" not in s


def test_equipment_direct_when_run_touches_the_label():
    rect = (100, 100, 120, 120)
    stem = ("V", 110, 120, 200)
    tank = Eq("CLEAN DRAIN TANK", (80, 195, 300, 260))
    v = ax.judge_row(rect, [stem], [], [], [tank],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_EQUIP and v["equip"] == "CLEAN DRAIN TANK"
    assert ax.sentence(v, "LIT") == "CLEAN DRAIN TANK LEVEL TRANSMITTER"


def test_trunk_inherits_both_ends_once():
    # 스템 → 모선 T 접합: 모선의 양끝을 딱 한 번 이어받아 ② 가 된다.
    rect = (100, 60, 130, 90)
    stem = ("V", 115, 90, 150)
    main = ("H", 152, 20, 400)             # 스템 끝에서 2pt 아래 (min_run 안)
    conns = [((0, 145, 18, 160), "FROM A PUMP"),
             ((402, 145, 460, 160), "TO B TANK")]
    v = ax.judge_row(rect, [stem, main], [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45, min_run=17.0)
    assert v["axis"] == ax.AX_FROMTO
    assert v["src"] == "A PUMP" and v["dst"] == "B TANK"
    assert all(e.get("inherited") for e in v["ev"]["ends"])


def test_branch_from_plus_two_tees_goes_upstream():
    # FROM 하나 + 내 런 안쪽에 끝을 대는 직교 분기 2개 = ③ 상류 DISCHARGE.
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 500),
            ("V", 300, 110, 180), ("V", 380, 110, 180)]   # 분기 스텁 2개
    conns = [((0, 100, 18, 120), "FROM CEP DISCHARGE")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_BRANCH and v["up"] == "CEP DISCHARGE"
    assert v["ev"]["tees"] >= 2
    # 이음매 중복 제거: 상류 이름이 이미 DISCHARGE 로 끝나면 다시 붙이지 않는다
    assert ax.sentence(v, "FIT") == "CEP DISCHARGE FLOW TRANSMITTER"
    assert ax.sentence({"axis": ax.AX_BRANCH, "up": "CEP"}, "FIT") \
        == "CEP DISCHARGE FLOW TRANSMITTER"


def test_unknown_stays_blank_and_invents_nothing():
    rect = (100, 100, 120, 120)
    stem = ("V", 110, 120, 200)            # 어디에도 닿지 않는 스템
    v = ax.judge_row(rect, [stem], [], [], [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_UNKNOWN
    assert ax.sentence(v, "PIT") == ""


def test_no_traversal_in_the_module():
    # §2.3: 재귀·큐·방문 집합 없음.  모선 승계는 한 단계뿐이다.
    src = (Path(__file__).resolve().parent.parent
           / "app" / "engine" / "describe_axis.py").read_text()
    for banned in ("while frontier", "deque", "visited", "seen.add"):
        assert banned not in src, f"순회 구조 발견: {banned}"


def test_standard_break_derives_from_the_distribution():
    # 최빈 끊김 18pt · 19pt 칸 0 → 상한 18.5.  봉우리가 없으면 None.
    runs = ([("H", 100, i * 40.0, i * 40.0 + 22.0) for i in range(30)]
            )  # 간격 18pt 가 29회
    br = ax.standard_break(runs, JS)
    assert br == 18.5
    assert ax.standard_break([("H", 0, 0, 10)], JS) is None
    merged = ax.bridge_collinear(runs, JS, br)
    assert len(merged) == 1 and merged[0][2] == 0.0


def test_suffix_only_within_same_attribution_and_type():
    v1 = {"axis": ax.AX_EQUIP, "equip": "CEP"}
    v2 = {"axis": ax.AX_EQUIP, "equip": "CEP"}
    v3 = {"axis": ax.AX_EQUIP, "equip": "FLASH BOX"}
    items = [("k1", 16, "RO", (10, 50, 20, 60), v1),
             ("k2", 16, "RO", (10, 10, 20, 20), v2),
             ("k3", 16, "RO", (10, 90, 20, 99), v3)]
    got = ax.assign_suffixes(items)
    assert got == {"k2": "A", "k1": "B"}   # 위→아래, 혼자면 없음


def test_one_sided_from_keeps_the_half_it_read():
    """출발만 읽히면 ②a — 없는 도착지를 지어내지 않고 읽은 반쪽만 쓴다 (7회차)."""
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 400)]
    conns = [((0, 100, 18, 120), "FROM HRSG #11 IP ECO OUTLET")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_FROM_ONLY and v["src"] == "HRSG #11 IP ECO OUTLET"
    assert ax.sentence(v, "GLOBE") == "FROM HRSG #11 IP ECO OUTLET GLOBE VALVE"
    assert ax.attribution(v) == "HRSG #11 IP ECO OUTLET→"


def test_one_sided_to_keeps_the_half_it_read():
    """도착만 읽히면 ②b.  LS 는 확정대로 LEVEL SWITCH 로 끝난다."""
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 400)]
    conns = [((402, 100, 470, 120), "TO CLEAN DRAIN TANK")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_TO_ONLY and v["dst"] == "CLEAN DRAIN TANK"
    assert ax.sentence(v, "GLOBE") == "TO CLEAN DRAIN TANK GLOBE VALVE"
    assert ax.sentence(v, "LS") == "TO CLEAN DRAIN TANK LEVEL SWITCH"
    assert ax.attribution(v) == "→CLEAN DRAIN TANK"


def test_branch_still_wins_over_one_sided_from():
    """분기가 둘 이상이면 ③ 이 먼저다 — ②a 가 ③ 을 가로채지 않는다."""
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 500),
            ("V", 300, 110, 180), ("V", 380, 110, 180)]
    conns = [((0, 100, 18, 120), "FROM CEP DISCHARGE")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_BRANCH


def test_suffix_groups_include_one_sided_axes():
    v1 = {"axis": ax.AX_TO_ONLY, "dst": "CLEAN DRAIN TANK"}
    v2 = {"axis": ax.AX_TO_ONLY, "dst": "CLEAN DRAIN TANK"}
    got = ax.assign_suffixes([("k1", 6, "GLOBE", (10, 50, 20, 60), v1),
                              ("k2", 6, "GLOBE", (10, 10, 20, 20), v2)])
    assert got == {"k2": "A", "k1": "B"}


def test_two_same_direction_connectors_stay_unknown():
    """양 끝이 다 `TO …` 면 어느 쪽인지 도면이 말하지 않는다 — 고르지 않는다."""
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 400)]
    conns = [((0, 100, 18, 120), "TO CLEAN DRAIN TANK"),
             ((402, 100, 480, 120), "TO ST #10 GLAND SEAL HEADER")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45)
    assert v["axis"] == ax.AX_UNKNOWN
    assert "같은 방향" in v["ev"]["why"]
    assert ax.sentence(v, "TIT") == ""
