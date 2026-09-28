"""hotfix14 — DXF 에서 누락·오짝을 만들던 세 자리 (UAD DXF p11 · p12 · p21 실측).

① 태그 버블 → 밸브 몸체는 **짧은 선부터** 보고, 끝이 다른 심볼에 닿으면 멈춘다
   (신호선의 먼 끝이 남의 밸브를 집지 않게).
② TYPE·태그 속성 값이 거꾸로 든 인스턴스는 **값으로** 읽는다.
③ TYPE 역할 속성을 가진 블록은 속성이 비어도 계기 버블 블록이다.
"""
from pathlib import Path

SRC = (Path(__file__).resolve().parent.parent / "app/dxf_pipeline.py").read_text(encoding="utf-8")


def test_leader_is_read_shortest_first_and_stops_at_other_symbol():
    seg = SRC.split("# ── 밸브 행 — 태그 버블은 지시선 한 걸음으로 몸체에", 1)[1].split("# 태그 없는 액추에이터 밸브", 1)[0]
    assert "math.dist(a, b)" in seg and "ends.sort(key=lambda t: t[0])" in seg
    assert "stop = True" in seg and "if stop:" in seg
    # 한 걸음이다 — 찾은 끝에서 다시 선을 찾지 않는다 (54회차 규율)
    assert seg.count("for a, b, _layer in lines_") == 1


def test_type_and_tag_attributes_are_read_by_value():
    seg = SRC.split("# ── 계기 · 밸브 태그 버블 (1급 · 속성)", 1)[1].split("# ── 계기 (2급", 1)[0]
    assert "tv, tagv, swapped = tagv, tv, True" in seg
    assert "_isa_type(tv, isa) is None and tagsys._is_code(tv)" in seg
    assert "DXF_ATTRIB_ROLES_BY_VALUE" in seg


def test_type_role_blocks_are_bubble_blocks():
    assert 'type_named = set(roles["type"])' in SRC
    assert "inst_outside.add(s_.block)" in SRC
    seg = SRC.split("# ── 계기 (2급", 1)[1].split("# ── 기하 폴백", 1)[0]
    assert "in rules.valves), None)" in seg


def test_no_block_or_layer_names_in_the_new_rules():
    for name in ("Instrument line", "Pressure Relief", "INST_LOCAL", "Inline Instrument", "Gate Valve"):
        assert name not in SRC
