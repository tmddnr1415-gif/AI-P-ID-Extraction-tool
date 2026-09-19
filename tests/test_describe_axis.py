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


def test_mid_branch_is_read_once(monkeypatch):
    """탭한 런의 **몸통**에 붙는 가지를 한 단계 읽는다 (9회차).

    p6 실측 구조를 합성으로 옮긴 것: 계기는 세로 라인에 탭하고, 커넥터로 가는
    가로 라인은 그 세로의 **중간**에 T 로 붙는다.  세로의 두 끝은 아무것도
    읽지 못한다.
    """
    rect = (100, 100, 130, 130)
    leader = ("H", 115, 130, 200)          # 버블 → 오른쪽, 세로 라인에 착지
    stem = ("V", 200, 50, 400)             # 탭한 세로 라인 (양 끝 무명)
    branch = ("H", 300, 20, 200)           # 중간 y=300 에서 왼쪽으로 갈라짐
    conns = [((0, 292, 18, 308), "TO HRSG#12 BD TANK")]
    v = ax.judge_row(rect, [stem, branch], [leader], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45, min_run=17.0)
    assert v["axis"] == ax.AX_TO_ONLY and v["dst"] == "HRSG#12 BD TANK"
    assert v["ev"]["ends"][0]["via"] == "mid"
    assert v["ev"]["mid_branches"] == 1


def test_mid_branch_does_not_step_twice():
    """가지에서 또 갈라지는 것은 따라가지 않는다 — 깊이는 1 이다."""
    rect = (100, 100, 130, 130)
    leader = ("H", 115, 130, 200)
    stem = ("V", 200, 50, 400)
    branch = ("H", 300, 120, 200)          # 중간 가지, 끝(120,300)은 무명
    second = ("V", 120, 300, 600)          # 그 가지에서 또 갈라지는 라인
    conns = [((0, 592, 18, 608), "TO CLEAN DRAIN TANK")]   # 두 단계 뒤에 있음
    v = ax.judge_row(rect, [stem, branch, second], [leader], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45, min_run=17.0)
    assert v["axis"] == ax.AX_UNKNOWN, "두 단계를 걸으면 안 된다"


def test_two_mid_branches_with_different_names_stay_unknown():
    """가지가 둘이고 이름이 다르면 고르지 않는다 — ④ 로 남긴다."""
    rect = (100, 100, 130, 130)
    leader = ("H", 115, 130, 200)
    stem = ("V", 200, 50, 500)
    b1 = ("H", 300, 20, 200)
    b2 = ("H", 400, 20, 200)
    conns = [((0, 292, 18, 308), "TO HRSG#12 BD TANK"),
             ((0, 392, 18, 408), "TO CLEAN DRAIN TANK")]
    v = ax.judge_row(rect, [stem, b1, b2], [leader], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45, min_run=17.0)
    assert v["axis"] == ax.AX_UNKNOWN
    assert "중간 접합에서 이름이 2개" in v["ev"]["why"]
    assert set(v["ev"]["mid_names"]) == {"HRSG#12 BD TANK", "CLEAN DRAIN TANK"}


def test_mid_branch_only_when_ends_read_nothing():
    """끝점이 읽힌 행은 건드리지 않는다 — 기존 ②·②a·②b 판정 불변."""
    rect = (200, 95, 240, 125)
    runs = [("H", 110, 20, 199), ("H", 110, 241, 400), ("V", 300, 110, 300)]
    conns = [((0, 100, 18, 120), "FROM HRSG#12"),
             ((402, 100, 460, 120), "TO HP BYPASS#12"),
             ((280, 292, 340, 308), "TO SOMEWHERE ELSE")]
    v = ax.judge_row(rect, runs, [], conns, [],
                     join_slack=JS, conn_reach=70, eq_reach=45, min_run=17.0)
    assert v["axis"] == ax.AX_FROMTO
    assert v["src"] == "HRSG#12" and v["dst"] == "HP BYPASS#12"


def test_mid_branch_does_not_override_equipment_direct():
    """기기 직결(①)로 답이 서는 행은 중간 접합이 덮지 않는다 (9회차 실측:
    이 조건이 없으면 ① 11행이 ②b 로 끌려갔다)."""
    class Eq2:
        def __init__(self, label, rect): self.label, self.rect = label, rect
    rect = (100, 100, 130, 130)
    leader = ("H", 115, 130, 200)
    stem = ("V", 200, 50, 400)
    branch = ("H", 300, 20, 200)
    conns = [((0, 292, 18, 308), "TO CLEAN DRAIN TANK")]
    tank = Eq2("HOTWELL", (180, 40, 400, 60))      # 탭한 런이 라벨에 닿는다
    v = ax.judge_row(rect, [stem, branch], [leader], conns, [tank],
                     join_slack=JS, conn_reach=70, eq_reach=45, min_run=17.0)
    assert v["axis"] == ax.AX_EQUIP and v["equip"] == "HOTWELL"


# --------------------------------------------------------------------------
# 10회차 — 라인 전후단 최근접 커넥터 (`nearest_conn`)
# --------------------------------------------------------------------------

def test_nearest_conn_reads_both_sides_of_the_line():
    """전단·후단 양쪽을 보고, 버블에서 더 가까운 쪽 하나를 고른다."""
    rect = (200, 95, 240, 125)
    run = ("H", 110, 20, 400)
    conns = [((0, 100, 18, 120), "FROM UPSTREAM PLACE"),      # 왼쪽 182pt
             ((260, 100, 320, 120), "TO DOWNSTREAM PLACE")]   # 오른쪽 20pt
    got = ax.nearest_conn(rect, run, [], conns, 70)
    assert got["dir"] == "TO" and got["name"] == "DOWNSTREAM PLACE"
    assert got["side"] == "뒤" and got["candidates"] == 2


def test_nearest_conn_is_bounded_across_the_line_not_along_it():
    """축과 **직교**하는 방향은 conn_reach 로 막고, 축을 따라가는 방향은 막지
    않는다 — 이 문서의 런은 엘보에서 끊겨 조각의 길이가 계통의 길이가 아니다."""
    rect = (200, 95, 240, 125)
    run = ("H", 110, 190, 250)                    # 60pt 짜리 스터브
    far_on_line = [((2000, 100, 2100, 120), "TO FAR PLACE")]
    got = ax.nearest_conn(rect, run, [], far_on_line, 70)
    assert got is not None and got["name"] == "FAR PLACE"     # 축을 따라서는 닿는다

    off_line = [((260, 300, 320, 320), "TO OFF LINE PLACE")]  # 직교 190pt
    assert ax.nearest_conn(rect, run, [], off_line, 70) is None


def test_nearest_conn_ignores_text_that_is_not_a_connector():
    rect = (200, 95, 240, 125)
    run = ("H", 110, 20, 400)
    conns = [((250, 100, 300, 120), "CLEAN DRAIN TANK")]      # TO/FROM 없음
    assert ax.nearest_conn(rect, run, [], conns, 70) is None


def test_nearest_conn_tie_break_is_deterministic():
    """같은 거리면 §5.1 정렬(위→아래 · 왼→오)로 하나를 고른다.  임의 선택 없음."""
    rect = (200, 95, 240, 125)
    run = ("H", 110, 0, 500)
    a = ((100, 100, 160, 120), "TO ALPHA")       # 왼쪽 40pt
    b = ((280, 100, 340, 120), "TO BETA")        # 오른쪽 40pt
    first = ax.nearest_conn(rect, run, [], [a, b], 70)
    second = ax.nearest_conn(rect, run, [], [b, a], 70)
    assert first == second and first["name"] == "ALPHA"


def test_nearest_conn_does_not_walk_the_pipe():
    """§2.2 상시 금지 — 순회하지 않는다.  주어진 선(탭한 런 · 모선 · 중간 가지)
    바깥의 런은 보지 않으므로, 두 단계 떨어진 커넥터는 읽히지 않는다."""
    rect = (200, 95, 240, 125)
    run = ("H", 110, 20, 400)
    second_hop = ("V", 400, 110, 900)            # 이 런은 넘겨주지 않는다
    conns = [((380, 880, 460, 900), "TO TWO HOPS AWAY")]
    assert ax.nearest_conn(rect, run, [], conns, 70) is None
    # 한 단계(모선)로 넘겨주면 그때는 읽힌다 — 깊이 1 은 허용된 범위다
    got = ax.nearest_conn(rect, run, [second_hop], conns, 70)
    assert got is not None and got["name"] == "TWO HOPS AWAY"


def test_nearest_conn_source_has_no_traversal_machinery():
    """경계를 소스로 강제한다 (§2.3 과 같은 방식)."""
    import inspect
    src = inspect.getsource(ax.nearest_conn)
    for banned in ("while ", "def ", "append(L", "recurs"):
        if banned == "def ":
            assert src.count("def ") == 1, "내부 함수를 두지 않는다"
            continue
        assert banned not in src, f"{banned!r} 가 들어왔다"
