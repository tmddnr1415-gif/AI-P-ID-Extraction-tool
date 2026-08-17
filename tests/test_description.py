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
