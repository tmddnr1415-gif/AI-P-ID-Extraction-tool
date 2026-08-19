"""The contract around the Description selector, enforced rather than promised.

Six rules were set for letting a model near this column.  Five of them are
checkable without a network, and they are checked here, because every one of them
is a rule about what the code may *not* do - and that kind of rule rots silently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

import describe_llm  # noqa: E402
import describe as desc  # noqa: E402


def payload(candidates, system="HP STEAM", variable="PRESSURE"):
    return {
        "type": "PIT", "variable": variable, "system": system, "unit_code": "10",
        "candidates": [{"text": t, "kind": k, "distance": 10.0, "direction": "LEFT"}
                       for t, k in candidates],
        "examples": [],
    }


def test_no_candidates_means_no_call(tmp_path):
    """Rule 2: with no evidence the model is not asked, even when it is available."""
    sel = describe_llm.Selector(cache_dir=tmp_path, enabled=True)
    answer, reason = describe_llm.select(sel, payload([]))
    assert answer is None
    assert reason == describe_llm.NO_CANDIDATES
    assert sel.stats["calls"] == 0
    assert not list(tmp_path.glob("*.json"))


def test_a_word_that_is_not_in_the_candidates_is_rejected():
    """Rule 3: the answer is re-checked against the words the rules collected."""
    p = payload([("CLEAN DRAIN TANK", "CONNECTOR")])
    ok, _unit, why = describe_llm.validate(
        {"middle": "CLEAN DRAIN TANK"}, p, {"10"})
    assert ok == "CLEAN DRAIN TANK" and not why
    bad, _u, why = describe_llm.validate(
        {"middle": "CLEAN DRAIN VESSEL"}, p, {"10"})
    assert bad == ""
    assert why.startswith(describe_llm.REJECT_UNKNOWN_WORD)
    assert "VESSEL" in why


def test_a_unit_number_not_on_the_drawing_is_rejected():
    """Rule 3: the unit marking has to be one the page actually prints."""
    p = payload([("HRSG#11", "UNIT_MARK"), ("BD TANK", "CONNECTOR")])
    _m, unit, why = describe_llm.validate(
        {"middle": "BD TANK", "unit": "#11"}, p, {"10", "11"})
    assert unit == "#11" and not why
    _m, unit, why = describe_llm.validate(
        {"middle": "BD TANK", "unit": "#13"}, p, {"10", "11"})
    assert unit == "" and why == describe_llm.REJECT_UNIT


def test_repeating_the_system_or_the_variable_is_rejected():
    """The template puts those around the answer; repeating them doubles the line."""
    p = payload([("HP STEAM HEADER", "PIPE_LABEL")])
    _m, _u, why = describe_llm.validate({"middle": "HP STEAM HEADER"}, p, {"10"})
    assert why == describe_llm.REJECT_ORDER


def test_declining_is_a_valid_answer():
    p = payload([("DN550", "PIPE_LABEL")])
    m, _u, why = describe_llm.validate(
        {"middle": describe_llm.INSUFFICIENT}, p, {"10"})
    assert m == "" and why == describe_llm.MODEL_DECLINED


def test_the_cache_answers_without_a_client(tmp_path):
    """Rule 4: same input, same bytes, and no call - the cache is the guarantee."""
    sel = describe_llm.Selector(cache_dir=tmp_path)      # not enabled: no key
    p = payload([("BD TANK", "CONNECTOR")])
    stored = {"middle": "BD TANK", "unit": "", "used": ["BD TANK"], "why": "x"}
    (tmp_path / f"{sel.key(p)}.json").write_text(
        json.dumps(stored, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    answer, reason = describe_llm.select(sel, p)
    assert answer == stored and not reason
    assert sel.stats["cache_hits"] == 1 and sel.stats["calls"] == 0
    # the key depends on the inputs only, so a second identical call hits again
    answer2, _ = describe_llm.select(sel, dict(p))
    assert answer2 == answer


def test_a_missing_key_is_reported_not_raised(monkeypatch):
    """Rule 2 again: no key is a state to report, never an exception mid-run."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    import projectconfig
    cfg = projectconfig.load()
    sel = describe_llm.build(cfg)
    assert sel.enabled is False and sel.reason
    answer, reason = describe_llm.select(sel, payload([("BD TANK", "CONNECTOR")]))
    assert answer is None and reason == sel.reason


DETECTORS = ("detect_symbols.py", "detect_valves.py", "detect_all.py",
             "legend_rules.py", "extract_titleblocks.py", "projectconfig.py",
             "pidcache.py", "stroke_bootstrap.py", "parse_notes.py")


@pytest.mark.parametrize("name", DETECTORS)
def test_detection_cannot_reach_the_model(name):
    """Rule 5: no detector may import the selector, directly or by name.

    Checked as a fact about the source rather than as a promise in a comment: a
    single `import describe_llm` in a detector would put a model in the path that
    decides what a symbol is, and nothing else in the test suite would notice.
    """
    src = (ROOT / "app" / "engine" / name).read_text(encoding="utf-8")
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            assert "describe_llm" not in stripped, f"{name}: {stripped}"
            assert "anthropic" not in stripped, f"{name}: {stripped}"


def test_the_selector_only_ever_sees_candidate_text():
    """Rule 1: the prompt carries the candidates and nothing else to copy from."""
    p = payload([("BD TANK", "CONNECTOR")])
    text = describe_llm._user_text(p)
    assert "BD TANK" in text
    # the system prompt is what forbids invention; check it says so in as many
    # words, since that is the half a reader will look for
    assert "Use only words that appear in the candidate list" in describe_llm.SYSTEM
    assert describe_llm.INSUFFICIENT in describe_llm.SYSTEM


# --------------------------------------------------------------------------
# The two-axis subject rule: equipment first, the line second
# --------------------------------------------------------------------------

import describe_equipment as dequip  # noqa: E402
import describe_candidates as dcand  # noqa: E402


def test_a_route_line_is_not_equipment():
    """`TO HRSG#12 BD TANK` says where the pipe goes, not what sits here.

    Taken as equipment it collected an ordinal and a position word - `TO CLEAN
    DRAIN TANK C INLET` - a phrase the client never writes, so route lines are left
    to the line axis.
    """
    assert dequip.ROUTE_RE.match("TO HRSG#12 BD TANK")
    assert dequip.ROUTE_RE.match("FROM METERING SYSTEM")
    assert not dequip.ROUTE_RE.match("CLEAN DRAIN TANK")


def test_the_count_note_and_the_plural_come_off_the_name():
    """Both rules are the client's own: `(3X50%)` in 0 of 557 lines, PUMPS in 0."""
    name, note = dequip.clean_label("GT FUEL OIL FORWARDING PUMPS (3X50%)")
    assert name == "GT FUEL OIL FORWARDING PUMP"
    assert note == "(3X50%)"
    name, note = dequip.clean_label("CLEAN DRAIN TANK")
    assert name == "CLEAN DRAIN TANK" and note == ""


def test_position_words_follow_the_equipment_kind():
    """PUMP -> SUCTION / DISCHARGE (115 of 115), anything else -> INLET / OUTLET."""
    import projectconfig
    pos = dcand.derive_position_words(projectconfig.load())
    pump = dequip.Equipment(kind="PUMP", rect=(100, 100, 140, 140), page_no=1)
    hx = dequip.Equipment(kind="EXCHANGER", rect=(100, 100, 140, 140), page_no=1)
    assert dcand.position_word(pump, dcand.LEFT, pos) == "SUCTION"
    assert dcand.position_word(pump, dcand.RIGHT, pos) == "DISCHARGE"
    assert dcand.position_word(hx, dcand.LEFT, pos) == "INLET"
    assert dcand.position_word(hx, dcand.RIGHT, pos) == "OUTLET"
    # a side the client never writes a word for gets none
    assert dcand.position_word(pump, dcand.ABOVE, pos) == ""


def test_side_is_read_off_the_two_centres():
    equip = (100.0, 100.0, 140.0, 140.0)
    assert dcand.side_of((10, 110, 30, 130), equip) == dcand.LEFT
    assert dcand.side_of((200, 110, 220, 130), equip) == dcand.RIGHT
    assert dcand.side_of((110, 10, 130, 30), equip) == dcand.ABOVE


def test_equipment_of_one_name_is_numbered_along_its_own_axis():
    """A column of pumps is A to C top-down; a row of them left to right."""
    col = [dequip.Equipment(kind="PUMP", label="CLEAN DRAIN PUMP", page_no=1,
                            rect=(100, y, 200, y + 20)) for y in (300, 100, 200)]
    dequip.group(col)
    assert [e.ordinal for e in sorted(col, key=lambda e: e.rect[1])] == ["A", "B", "C"]
    assert col[0].evidence["ordinal_axis"] == "top-to-bottom"
    row = [dequip.Equipment(kind="PUMP", label="CCW PUMP", page_no=1,
                            rect=(x, 100, x + 20, 120)) for x in (300, 100, 200)]
    dequip.group(row)
    assert [e.ordinal for e in sorted(row, key=lambda e: e.rect[0])] == ["A", "B", "C"]
    assert row[0].evidence["ordinal_axis"] == "left-to-right"


def test_a_single_piece_of_equipment_gets_no_ordinal():
    one = [dequip.Equipment(kind="TANK", label="CLEAN DRAIN TANK", page_no=1,
                            rect=(10, 10, 50, 50))]
    dequip.group(one)
    assert one[0].ordinal == ""


def test_the_sentence_puts_each_part_where_the_client_puts_it():
    """`UNIT #n | system | equipment ordinal position | variable | suffix`.

    Counted in the client's 557 lines: the equipment ordinal follows its noun (172
    lines), the variable comes last (357 of 538 end on it) and an instrument
    ordinal follows the variable (117 lines).
    """
    import isa_table
    isa = isa_table.IsaTable(first={"P": ("PRESSURE",)}, page_no=3)
    pat = describe_pattern()
    subject = {"text": "CLEAN DRAIN PUMP", "kind": dcand.EQUIPMENT, "distance": 40.0,
               "direction": dcand.LEFT,
               "equipment": {"noun": "PUMP", "ordinal": "A",
                             "position_word": "SUCTION", "evidence": {}}}
    out = desc.assemble("10", "P&ID FOR CLEAN DRAIN SYSTEM GROUP 10", "PIT", isa,
                        pat, subject=subject, suffix="B", type_="PIT")
    # the system name is not repeated: the subject already carries CLEAN DRAIN, and
    # only 29 of the client's 557 lines say any word twice
    assert out["text"] == "UNIT #10 CLEAN DRAIN PUMP A SUCTION PRESSURE B"
    assert out["middle"] == "CLEAN DRAIN PUMP A SUCTION"
    assert out["complete"] is True


def test_the_position_word_is_attached_only_for_the_types_that_use_one():
    """PIT carries one in 70.8% of the client's lines; LIT in 0 of 29."""
    import isa_table
    isa = isa_table.IsaTable(first={"P": ("PRESSURE",), "L": ("LEVEL",)}, page_no=3)
    pat = describe_pattern()
    # a cooler, whose two sides the client does name - a tank's it never does, and
    # that is the other rule (`position_by_noun`), tested below
    subject = {"text": "CLEAN DRAIN COOLER", "kind": dcand.EQUIPMENT, "distance": 40.0,
               "direction": dcand.LEFT,
               "equipment": {"noun": "COOLER", "ordinal": "",
                             "position_word": "INLET", "evidence": {}}}
    on = desc.assemble("10", "P&ID FOR CLEAN DRAIN SYSTEM GROUP 10", "PIT", isa,
                       pat, subject=subject, type_="PIT")
    off = desc.assemble("10", "P&ID FOR CLEAN DRAIN SYSTEM GROUP 10", "LIT", isa,
                        pat, subject=subject, type_="LIT")
    assert "INLET" in on["text"]
    assert "INLET" not in off["text"]


def test_the_ordinal_sits_where_the_duty_note_says():
    """Three pumps and three instruments -> the letter numbers the pump (middle).

    Two instruments on one pump set -> it numbers the instrument (end).  The duty
    note the drawing prints beside the label is what separates the two cases.
    """
    trio = [dequip.Equipment(kind="PUMP", label="GT FUEL OIL FORWARDING PUMP",
                             page_no=33, rect=(100, 100, 200, 140),
                             count_note="3X50%")]
    rows = [(f"k{i}", (100.0, 200.0 + i * 50, 140.0, 220.0 + i * 50), "PDIT")
            for i in range(3)]
    cands = {k: [{"kind": dcand.EQUIPMENT, "text": "GT FUEL OIL FORWARDING PUMP"}]
             for k, _r, _t in rows}
    out = dcand.instrument_ordinals(rows, cands, trio)
    assert [out[k][0] for k, _r, _t in rows] == ["A", "B", "C"]
    assert {w for _o, w in out.values()} == {"MIDDLE"}
    # two instruments against a three-unit set: the letter is the instrument's
    pair = rows[:2]
    out2 = dcand.instrument_ordinals(pair, cands, trio)
    assert {w for _o, w in out2.values()} == {"END"}


def describe_pattern():
    import projectconfig
    return desc.derive_pattern(projectconfig.load())


def test_no_subject_leaves_the_rules_only_line_unchanged():
    import isa_table
    isa = isa_table.IsaTable(first={"P": ("PRESSURE",)}, page_no=3)
    out = desc.assemble("10", "P&ID FOR HP STEAM SYSTEM GROUP 10", "PIT", isa,
                        describe_pattern())
    assert out["text"] == "UNIT #10 HP STEAM PRESSURE"
    assert out["middle"] == "" and out["complete"] is False


def test_the_equipment_layer_does_not_use_the_pipe_graph():
    """This round's rule: both axes are geometric, neither walks the graph."""
    for name in ("describe_equipment.py", "describe_candidates.py"):
        src = (ROOT / "app" / "engine" / name).read_text(encoding="utf-8")
        for line in src.splitlines():
            if line.strip().startswith(("import ", "from ")):
                assert "pipe_graph" not in line, f"{name}: {line.strip()}"


def test_a_trailing_letter_only_goes_on_the_types_that_write_one():
    """LIT repeats its sentence rather than letter it: 20 repeats against 5 ends."""
    import isa_table
    isa = isa_table.IsaTable(first={"L": ("LEVEL",), "P": ("PRESSURE",)}, page_no=3)
    pat = describe_pattern()
    subject = {"text": "FUEL OIL STORAGE TANK A", "kind": dcand.EQUIPMENT,
               "distance": 100.0, "direction": "ABOVE",
               "equipment": {"noun": "TANK", "ordinal": "", "position_word": ""}}
    lit = desc.assemble("00", "P&ID FOR FUEL OIL SYSTEM", "LIT", isa, pat,
                        subject=subject, suffix="B", type_="LIT")
    assert lit["text"] == "FUEL OIL STORAGE TANK A LEVEL"
    pit = desc.assemble("00", "P&ID FOR FUEL OIL SYSTEM", "PIT", isa, pat,
                        subject=subject, suffix="B", type_="PIT")
    assert pit["text"].endswith("PRESSURE B")


def test_the_unit_prefix_survives_a_label_that_repeats_it():
    """`#10 CLEAN DRAIN TANK` on the drawing is still `UNIT #10 CLEAN DRAIN TANK`."""
    import isa_table
    isa = isa_table.IsaTable(first={"L": ("LEVEL",)}, page_no=3)
    subject = {"text": "#10 CLEAN DRAIN TANK", "kind": dcand.EQUIPMENT,
               "distance": 80.0, "direction": "LEFT",
               "equipment": {"noun": "TANK", "ordinal": "", "position_word": ""}}
    out = desc.assemble("10", "P&ID FOR CLEAN DRAIN SYSTEM", "LIT", isa,
                        describe_pattern(), subject=subject, type_="LIT")
    assert out["text"] == "UNIT #10 CLEAN DRAIN TANK LEVEL"


def test_only_a_pdit_is_offered_an_intermediate_symbol():
    """All 13 of the client's intermediate symbols are a PDIT's SUCTION STRAINER."""
    import types
    e = types.SimpleNamespace(rect=(400.0, 100.0, 500.0, 130.0), label="PUMP A",
                              kind="PUMP", ordinal="A", count_note="", evidence={})
    comps = [{"rect": (250.0, 100.0, 270.0, 130.0), "word": "STRAINER",
              "text": "SUCTION STRAINER"}]
    rows = [("pdit", (100.0, 100.0, 130.0, 130.0), "PDIT"),
            ("pit", (100.0, 200.0, 130.0, 230.0), "PIT")]
    pc = types.SimpleNamespace(words=[], segments=lambda: [], page_no=33)
    pos = {"pump_nouns": ("PUMP",),
           "pump": {dcand.LEFT: "SUCTION", dcand.RIGHT: "DISCHARGE"},
           "other": {dcand.LEFT: "INLET", dcand.RIGHT: "OUTLET"}}
    out = dcand.collect(pc, rows, [e], (0.0, 0.0, 2384.0, 1684.0), pos, limit=None,
                        components=comps, between_types=("PDIT",))
    assert (out["pdit"][0]["equipment"]["between"]) == "SUCTION STRAINER"
    assert (out["pit"][0]["equipment"]["between"]) == ""


def test_two_labels_on_one_baseline_are_separated_by_the_word_that_repeats():
    """`#10 ST` printed four times is four coolers, not one long name."""
    import types
    class R:
        def __init__(s, x0, y0, x1, y1): s.x0, s.y0, s.x1, s.y1 = x0, y0, x1, y1
    words = [(R(508, 788, 538, 800), "#10"), (R(526, 788, 545, 800), "ST"),
             (R(649, 788, 679, 800), "#10"), (R(667, 788, 686, 800), "ST"),
             (R(497, 800, 550, 813), "HYDRAULIC"),
             (R(638, 800, 687, 813), "HYDRAULIC"),
             (R(819, 800, 838, 813), "#10"), (R(837, 800, 850, 813), "ST"),
             (R(851, 800, 876, 813), "LUBE"), (R(877, 800, 893, 813), "OIL"),
             (R(894, 800, 933, 813), "COOLER"),
             (R(1234, 800, 1251, 813), "#10"), (R(1252, 800, 1265, 813), "ST"),
             (R(1266, 800, 1325, 813), "GENERATOR"),
             (R(1326, 800, 1365, 813), "COOLER"),
             (R(1650, 800, 1667, 813), "#10"), (R(1668, 800, 1681, 813), "ST"),
             (R(1682, 800, 1720, 813), "STATOR"),
             (R(1721, 800, 1756, 813), "WATER"),
             (R(1757, 800, 1796, 813), "COOLER"),
             (R(495, 813, 511, 826), "OIL"), (R(512, 813, 551, 826), "COOLER"),
             (R(636, 813, 652, 826), "OIL"), (R(653, 813, 692, 826), "COOLER")]
    pc = types.SimpleNamespace(words=words, page_no=37, segments=lambda: [])
    found = dequip.find_labels(pc, {"COOLER": "LEGEND"},
                               (0.0, 0.0, 2384.0, 1684.0), 15.3)
    names = sorted(e.label for e in found)
    assert names == ["#10 ST GENERATOR COOLER", "#10 ST HYDRAULIC OIL COOLER",
                     "#10 ST HYDRAULIC OIL COOLER", "#10 ST LUBE OIL COOLER",
                     "#10 ST STATOR WATER COOLER"], names


def test_the_line_pitch_is_measured_over_the_whole_set():
    """A sparse sheet's own modal gap is 2.0 pt, which is not a line pitch."""
    class R:
        def __init__(s, x0, y0, x1, y1): s.x0, s.y0, s.x1, s.y1 = x0, y0, x1, y1
    import types
    sparse = types.SimpleNamespace(page_no=1, words=[
        (R(10, 100, 40, 110), "A"), (R(60, 102, 90, 112), "B")])
    dense = types.SimpleNamespace(page_no=2, words=[
        (R(10, y, 40, y + 10), "X") for y in (100, 115, 130, 145, 160)])
    pitch = dequip.derive_line_pitch([sparse, dense], (0.0, 0.0, 500.0, 500.0))
    assert pitch == 15.0


def test_a_switch_reads_its_own_alarm_letters():
    """`LSHH` is `LEVEL HIGH HIGH` in 11 of the client's lines, `LSH` `LEVEL HIGH`."""
    import isa_table
    isa = isa_table.IsaTable(first={"L": ("LEVEL",)}, page_no=3)
    pat = describe_pattern()
    assert desc.variable_words("LSHH", isa, pat) == ("LEVEL", "HIGH", "HIGH")
    assert desc.variable_words("LSH", isa, pat) == ("LEVEL", "HIGH")
    assert desc.variable_words("LS", isa, pat) == ("LEVEL",)


def test_a_prefix_set_is_only_made_of_names_that_share_a_tail():
    import types
    def eq(label):
        return types.SimpleNamespace(label=label, rect=(0.0, 0.0, 1.0, 1.0))
    sets = dcand.prefix_groups([eq("AUX FUEL OIL FORWARDING PUMP"),
                                eq("GT FUEL OIL FORWARDING PUMP"),
                                eq("SLOP OIL TRANSFER PUMP")])
    assert list(sets) == [("FUEL", "OIL", "FORWARDING", "PUMP")]
    assert sorted(sets[("FUEL", "OIL", "FORWARDING", "PUMP")]) == ["AUX", "GT"]


def test_the_title_phrase_is_written_the_way_the_client_writes_it():
    """`CLOSED COOLING WATER` is `CCW` on 127 client lines and never written out."""
    pat = describe_pattern()
    words, _how = desc.system_words(
        "P&ID FOR CLOSED COOLING WATER SYSTEM GROUP 10 (3 OF 7)", pat)
    assert words == ["CCW"]
    # a phrase the client writes in full stays in full - HP STEAM, 12 lines of 12
    words, _how = desc.system_words("P&ID FOR HP STEAM SYSTEM GROUP 10", pat)
    assert words == ["HP", "STEAM"]


def test_a_system_can_carry_its_own_position_word():
    """Every CCW TI the client writes is on the RETURN - 51 lines of 54."""
    import isa_table
    isa = isa_table.IsaTable(first={"T": ("TEMPERATURE",), "P": ("PRESSURE",)},
                             page_no=3)
    pat = describe_pattern()
    subject = {"text": "#10 ST HYDRAULIC OIL COOLER", "kind": dcand.EQUIPMENT,
               "distance": 90.0, "direction": "BELOW",
               "equipment": {"noun": "COOLER", "ordinal": "A", "position_word": ""}}
    title = "P&ID FOR CLOSED COOLING WATER SYSTEM GROUP 10 (3 OF 7)"
    ti = desc.assemble("10", title, "TI", isa, pat, subject=subject, type_="TI")
    assert "RETURN" in ti["text"]
    # its PI is an even split, 49 SUPPLY against 51 RETURN, so nothing is attached
    pi = desc.assemble("10", title, "PI", isa, pat, subject=subject, type_="PI")
    assert "RETURN" not in pi["text"] and "SUPPLY" not in pi["text"]


def test_a_tank_takes_no_position_word_whatever_side_it_is_on():
    """The client writes one against 0 of its 59 TANK lines, and DOWNSTREAM on a
    valve where left/right would have said OUTLET."""
    import isa_table
    isa = isa_table.IsaTable(first={"P": ("PRESSURE",)}, page_no=3)
    pat = describe_pattern()
    tank = {"text": "CLEAN DRAIN TANK", "kind": dcand.EQUIPMENT, "distance": 40.0,
            "direction": dcand.LEFT,
            "equipment": {"noun": "TANK", "ordinal": "",
                          "position_word": "INLET", "evidence": {}}}
    out = desc.assemble("10", "P&ID FOR CLEAN DRAIN SYSTEM GROUP 10", "PIT", isa,
                        pat, subject=tank, type_="PIT")
    assert "INLET" not in out["text"]
    valve = {"text": "HP BYPASS VALVE", "kind": dcand.EQUIPMENT, "distance": 40.0,
             "direction": dcand.RIGHT,
             "equipment": {"noun": "VALVE", "ordinal": "",
                           "position_word": "OUTLET", "evidence": {}}}
    out = desc.assemble("12", "P&ID FOR BYPASS STEAM SYSTEM GROUP 10", "PIT", isa,
                        pat, subject=valve, type_="PIT")
    assert "DOWNSTREAM" in out["text"] and "OUTLET" not in out["text"]


def test_a_noun_that_only_names_equipment_in_company():
    """The client writes BYPASS VALVE 54 times and BRETHER VALVE never; the
    drawings print BRETHER VALVE 42 times."""
    import types
    class R:
        def __init__(s, x0, y0, x1, y1): s.x0, s.y0, s.x1, s.y1 = x0, y0, x1, y1
    # two labels on their own baselines, as they sit on different parts of a sheet
    words = [(R(100, 100, 150, 112), "BYPASS"), (R(152, 100, 195, 112), "VALVE"),
             (R(400, 400, 455, 412), "BRETHER"), (R(457, 400, 500, 412), "VALVE")]
    pc = types.SimpleNamespace(words=words, page_no=11, segments=lambda: [])
    area = (0.0, 0.0, 2384.0, 1684.0)
    both = dequip.find_labels(pc, {"VALVE": "CLIENT"}, area, 15.3)
    assert sorted(e.label for e in both) == ["BRETHER VALVE", "BYPASS VALVE"]
    gated = dequip.find_labels(pc, {"VALVE": "CLIENT"}, area, 15.3,
                               {"VALVE": ["BYPASS", "LETDOWN"]})
    assert [e.label for e in gated] == ["BYPASS VALVE"]


def test_a_row_the_drawing_cannot_answer_says_so():
    """A PDIT on a pump and a PI on a CCW sheet each carry the measured reason."""
    from app import pipeline
    code, strainer = pipeline._user_input_note(
        "PDIT", "CLEAN DRAIN PUMP A", "PUMP", "CLEAN DRAIN")
    assert code == "DESC_BETWEEN_SYMBOL"
    assert "STRAINER" in strainer and "직접 입력" in strainer
    code, ccw = pipeline._user_input_note("PI", "", "COOLER", "CCW")
    assert code == "DESC_CCW_DIRECTION"
    assert "SUPPLY" in ccw and "RETURN" in ccw
    assert pipeline._user_input_note(
        "LIT", "SOME TANK", "TANK", "CLEAN DRAIN") == ("", "")


def test_a_standard_abbreviation_is_only_applied_where_the_project_chose_a_form():
    """The trade dictionary fixes no direction; the project file does."""
    standard = {"boiler_feedwater_pump": ["BFP", "BOILER FEEDWATER PUMP",
                                          "FEEDWATER PUMP"],
                "closed_cooling_water": ["CCW", "CLOSED COOLING WATER"]}
    # only the set the project chose a form for is applied
    aliases = dequip.derive_aliases(
        standard, {"boiler_feedwater_pump": "BOILER FEEDWATER PUMP"})
    assert aliases == {"BFP": "BOILER FEEDWATER PUMP",
                       "FEEDWATER PUMP": "BOILER FEEDWATER PUMP"}
    assert dequip.derive_aliases(standard, {}) == {}


def test_an_abbreviation_is_rewritten_only_when_it_is_the_name_itself():
    """`BFP A/B COOLER` is a cooler; the client writes BFP there and the long form
    only where the pump itself is the subject."""
    aliases = {"BFP": "BOILER FEED WATER PUMP",
               "FEEDWATER PUMP": "BOILER FEED WATER PUMP"}
    assert dequip.apply_alias("FEEDWATER PUMP", aliases) == (
        "BOILER FEED WATER PUMP", "FEEDWATER PUMP")
    assert dequip.apply_alias("BFP A/B COOLER", aliases) == ("BFP A/B COOLER", "")


def test_the_name_is_what_comes_before_the_for():
    """`FEEDWATER PUMP FOR HRSG UNIT #11 (2X50% PER HRSG)` names a pump."""
    name, note = dequip.clean_label(
        "FEEDWATER PUMP FOR HRSG UNIT #11 (A/B) (2X50% PER HRSG)")
    assert name == "FEEDWATER PUMP"
    name, _note = dequip.clean_label("SLOP OIL TANK FOR FORWARDING PUMP AREA (5m3)")
    assert name == "SLOP OIL TANK"


def test_the_standard_dictionary_carries_no_direction_of_its_own():
    """A confirmed set is applied only where the project names a member."""
    import projectconfig
    std = projectconfig.load_standard()
    assert std.get("confirmed"), "the standard file should carry confirmed sets"
    for name, forms in std["confirmed"].items():
        assert isinstance(forms, list) and len(forms) >= 2, name
    # nothing is applied without a choice, whatever the standard file says
    assert dequip.derive_aliases(std["confirmed"], {}) == {}


def test_a_row_the_drawing_cannot_answer_is_tagged_for_grouping():
    """The review screen groups on a generated tag, not on the sentence."""
    from app import pipeline
    _code, note = pipeline._user_input_note("PDIT", "CLEAN DRAIN PUMP A", "PUMP",
                                            "CLEAN DRAIN")
    assert note.startswith("[중간 심볼] ")
    _code, note = pipeline._user_input_note("PI", "", "COOLER", "CCW")
    assert note.startswith("[CCW 방향] ")


def test_an_off_page_connectors_sheet_reference_is_not_part_of_the_name():
    """`HRSG#11 HP BYPASS VALVE / D00P-10MAN10-M05-0001 / (H-2)` names a valve.

    The three lines are one off-page connector: where the pipe goes, the sheet it
    goes to, and the cell on that sheet.  The first line is equipment and stays;
    the other two are a reference and go.  The drawings write 26 of these numbers
    into 23 labels on 13 sheets, and the client writes 0 in its 557 Description
    lines - so nothing the client uses is being removed.
    """
    name, _note = dequip.clean_label(
        "HRSG#11 HP BYPASS VALVE D00P-10MAN10-M05-0001 (H-2)")
    assert name == "HRSG#11 HP BYPASS VALVE"


def test_the_sheet_reference_pattern_is_the_title_blocks_own():
    """One definition, read from the config the title block parser reads."""
    import projectconfig
    anchored = projectconfig.load().get("formats.drawing_no")
    assert dequip.DRAWING_NO.pattern == r"\b" + anchored.lstrip("^").rstrip("$") + r"\b"
    assert dequip.DRAWING_NO.search("D00P-10MAN10-M05-0001")


def test_a_bore_and_a_note_reference_go_the_same_way():
    """Both are the sheet's annotations, and the client writes neither."""
    assert dequip.clean_label("CCW EXPANSION TANK MAKE #20 UP DN50")[0] == (
        "CCW EXPANSION TANK MAKE #20 UP")
    assert dequip.clean_label("BALL STRAINER WITH PDIT NOTE 3")[0] == (
        "BALL STRAINER WITH PDIT")


def test_the_folded_rows_sentence_form_is_a_setting_with_three_named_options():
    """The client's list cannot settle it, so the choice is written down.

    Its 22 level-switch rows are 11 pairs - one `LEVEL HIGH HIGH` and one
    `LEVEL HIGH` per subject - so it writes one signal per row and never two, and
    `representative` is the form that matches.  The other two are named so a
    project that wants them does not have to edit code.
    """
    import projectconfig
    from app import pipeline
    cfg = projectconfig.load().data.get("multi_signal_bundle") or {}
    assert cfg.get("description_signal") in ("representative", "none", "all")
    assert pipeline.MULTI_SIGNAL_DESCRIPTION == cfg["description_signal"]


def test_the_isa_letter_column_is_found_by_what_it_holds():
    """The FIRST LETTER column, not the leftmost cluster of x offsets.

    The matrix prints one row per first letter and each letter once; a
    succeeding-letter column carries an entry only where that combination exists.
    So the first-letter column is the one with the most distinct entries, and that
    is a property of the table rather than of a sheet - which matters because the
    x distribution is not: a sheet whose border grid letters sit outside the frame
    offers those as a column, and a `SYMBOL` sub-heading offers itself 11 pt from
    the letters it is supposed to find.
    """
    import isa_table
    import pymupdf

    def word(x, y, t, w=8.0, h=14.0):
        return (pymupdf.Rect(x, y, x + w, y + h), t)

    body = []
    # the sheet's own grid letters, outside the table
    for i, t in enumerate("ABCDEF"):
        body.append(word(10, 100 + i * 30, t))
    # a sub-heading sitting over the column
    body.append(word(100, 60, "SYMBOL", w=40))
    # the FIRST LETTER column and one succeeding column beside it
    for i, t in enumerate("ABCDEFGHIJKLM"):
        body.append(word(112, 100 + i * 30, t))
        if t not in "HJ":                      # not every row has this function
            body.append(word(400, 100 + i * 30, t))
    col = isa_table._letter_column(body)
    assert col is not None
    assert [t for _r, t in col] == list("ABCDEFGHIJKLM")


def test_both_legends_yield_the_same_isa_letters():
    """The two documents print the same matrix, so they must read the same.

    This is the guard on the letter-column change: the words it produces are the
    Description's variable words, so one letter moving moves the score.
    """
    import json
    from pathlib import Path
    expected = json.loads(Path("tests/data/isa_first_letters.json").read_text())
    import isa_table
    import pidcache
    _doc, pages = pidcache.load_pages(Path("data/pid_total.pdf"))
    got = {k: list(v) for k, v in isa_table.derive(pages).first.items()}
    assert got == expected
