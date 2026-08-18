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
    subject = {"text": "CLEAN DRAIN TANK", "kind": dcand.EQUIPMENT, "distance": 40.0,
               "direction": dcand.LEFT,
               "equipment": {"noun": "TANK", "ordinal": "",
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
