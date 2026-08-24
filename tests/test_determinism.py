"""Guards on the two properties a reviewer has to be able to trust.

1. Re-analysing the same PDF gives the same answer, byte for byte.  Without
   that, a reviewer cannot tell a genuine change from a reshuffle, and every
   comparison between two runs is noise.

2. Re-analysing keeps human edits.  The engine owns `ai_values` and a person
   owns `user_values`; a re-run replaces the first and never the second.  When
   the engine's new answer contradicts an edit, that is surfaced as a conflict
   rather than resolved silently in either direction.

The full-document tests are slow (about seven minutes each), so they are marked
`slow` and the analysis is computed once and shared.  Run everything with
`pytest -q`, or the fast ones only with `pytest -q -m "not slow"`.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db, pipeline            # noqa: E402

PDF = ROOT / "data" / "pid_total.pdf"
pytestmark = pytest.mark.skipif(not PDF.exists(), reason="sample PDF not present")


@pytest.fixture(scope="session")
def first_run():
    return pipeline.analyse(PDF)


@pytest.fixture(scope="session")
def second_run():
    return pipeline.analyse(PDF)


@pytest.mark.slow
def test_reanalysis_is_byte_identical(first_run, second_run):
    """Same PDF in, same JSON out - not merely the same numbers."""
    a = json.dumps(first_run["rows"], sort_keys=True, default=str)
    b = json.dumps(second_run["rows"], sort_keys=True, default=str)
    assert a == b, "row payload differs between two runs of the same PDF"
    assert pipeline.fingerprint(first_run) == pipeline.fingerprint(second_run)
    assert first_run["multipliers"] == second_run["multipliers"]
    assert first_run["legend"] == second_run["legend"]
    assert first_run["glyphs"]["letters"] == second_run["glyphs"]["letters"]


@pytest.mark.slow
def test_a_real_run_needs_no_answer_key(first_run):
    """End to end, with nothing supplied but the PDF."""
    origins = {r["origin"] for r in first_run["rows"]}
    assert origins <= {pipeline.ORIGIN_DRAWING, pipeline.ORIGIN_REVISION_GAP}, origins
    kinds = {f["kind"] for f in first_run["job_review"]}
    assert "ORIGIN_REFERENCE_MISSING" not in kinds, (
        "a normal run must not report a missing verification input")


@pytest.mark.slow
def test_pneumatic_valves_are_found(first_run):
    """The legend's two letterless actuator shapes reach the deliverable.

    Before they were measured, the Pneumatic tab was empty on a document with 35
    domes and 25 XV tags in it, because the enclosure search only accepted
    shapes big enough to hold a letter.
    """
    pneumatic = [r for r in first_run["rows"] if r["tab"] == "PNEUMATIC"]
    assert pneumatic, "no pneumatic valve reached the deliverable"
    basis = {r["evidence"].get("actuator_basis", "") for r in pneumatic}
    assert any("dome" in b for b in basis)
    assert any("cylinder" in b for b in basis)


@pytest.mark.slow
def test_description_words_all_come_from_the_drawing(first_run):
    """No word in a Description is invented.

    Every word must come from a source the run can point at: the sheet's unit
    code, its title, legend p3's ISA table, or the candidate text the row was
    actually built from - which is the drawing's own equipment label or its
    `TO` / `FROM` line.  The grade has to match what was used, so a row cannot
    claim CONFIRMED without an equipment subject behind it.
    """
    written = [r for r in first_run["rows"] if r["description"]]
    assert written, "no Description was written at all"
    isa = first_run["description_build"]["isa_table"]
    assert isa["source"] == "LEGEND" and isa["first"]
    for r in written:
        axisv = r["evidence"].get("axis") or {}
        if axisv.get("source") == "신규문형":
            # 5회차 판정축 문형(혼합 적용): 낱말의 출처는 후보 목록이 아니라
            # 판정 근거다 - 탭한 런의 끝점이 닿은 커넥터/기기 이름, ISA 풀네임,
            # 순번, 그리고 문형 자체의 FROM/TO/DISCHARGE.
            import describe_axis as ax
            allowed = {"FROM", "TO", "DISCHARGE"}
            allowed |= set(ax.isa_fullname(r["type"] or r["valve_type"]).split())
            for name in (axisv.get("src"), axisv.get("dst"),
                         axisv.get("equip"), axisv.get("up"),
                         axisv.get("suffix")):
                if name:
                    allowed |= set(str(name).upper().split())
            extra = set(r["description"].upper().split()) - allowed
            assert not extra, f"axis row {r['key']} words from no source: {extra}"
            assert r["description_grade"] == pipeline.GRADE_CONFIRMED
            assert r["remark"].startswith("판정축")
            assert axisv.get("old_description") is not None, "현행 문장 미보존"
            continue
        allowed = set(desc_words(r, first_run))
        for c in (r["evidence"].get("candidates") or []):
            allowed |= set(str(c["text"]).upper().split())
            eq = c.get("equipment") or {}
            if eq.get("ordinal"):
                allowed.add(eq["ordinal"])
            if eq.get("position_word"):
                allowed.add(eq["position_word"])
        if r["evidence"].get("instrument_ordinal"):
            allowed.add(r["evidence"]["instrument_ordinal"])
        extra = set(r["description"].upper().split()) - allowed
        assert not extra, f"row {r['key']} has words from no source: {extra}"
        assert r["evidence"]["description_sources"], "no sources recorded"
        sel = r["evidence"].get("description_selected") or {}
        if r["description_grade"] == pipeline.GRADE_CONFIRMED:
            assert sel.get("kind") == "EQUIPMENT", (
                "CONFIRMED must rest on equipment the drawing names")
            assert r["evidence"]["description_axis"] == "EQUIPMENT"
        elif r["description_grade"] == pipeline.GRADE_LOW:
            assert sel.get("kind") == "CONNECTOR"
            assert r["remark"], "a LOW row must say what it rests on"
    # an item we do not describe gets no draft either
    for r in first_run["rows"]:
        if r["evidence"].get("description_needed") is False:
            assert not r["description"]


def desc_words(row, run) -> set:
    """Every word the row's rule-side sources could legitimately contribute."""
    page = next(p for p in run["pages"] if p["page_no"] == row["page_no"])
    tb_row = next(t for t in run["titleblocks"] if t["page_no"] == row["page_no"])
    isa = run["description_build"]["isa_table"]
    out = {"UNIT", f"#{tb_row['unit_code']}"}
    # The unit number may be the one printed beside the instrument rather than the
    # one on the title block.  The row records which text it was read off, and only
    # a number out of that text is allowed.
    mark = row["evidence"].get("unit_mark_source") or ""
    out |= {f"#{n}" for n in re.findall(r"#\s*(\d{1,2})\b", mark)}
    out |= set(str(page["title"]).upper().split())
    for words in isa["first"].values():
        out |= set(words)
    # The client's own spelling for a variable, where the legend's matrix does not
    # carry the tag at all - `FE` -> `FLOW ELEMENT`, `RO` -> `RESTRICTION ORIFICE`.
    # It is a declared source (`config description.variable_words`, counted on the
    # client's 557 lines) and the row records it in `description_sources`.
    for words in (pipeline.CFG.data.get("description") or {}).get(
            "variable_words", {}).values():
        out |= {str(w).upper() for w in words}
    # A switch's own trailing letters: `LSHH` reads `LEVEL HIGH HIGH`.  The legend
    # defines no H or L modifier, so the words are declared in
    # `config description.alarm_suffix` with the client's counts beside them.
    for words in (pipeline.CFG.data.get("description") or {}).get(
            "alarm_suffix", {}).values():
        out |= {str(w).upper() for w in words}
    # Three more tables the client's own list settles, each recorded in config with
    # the rows behind it: its short form for a title phrase (`CCW`), the word a
    # whole system uses (`CCW TI` -> RETURN), and the word for a side that geometry
    # cannot name (`PIT ABOVE` -> DISCHARGE).
    for table in ("system_abbreviations", "position_by_system", "position_by_side",
                  "position_by_noun"):
        out |= {str(w).upper() for w in
                (pipeline.CFG.data.get("description") or {}).get(table, {}).values()}
    return out


@pytest.mark.slow
def test_the_equipment_axis_wins_when_both_are_available(first_run):
    """The reviewer's rule: equipment beats the line whenever both are there."""
    both = 0
    for r in first_run["rows"]:
        if (r["evidence"].get("axis") or {}).get("source") == "신규문형":
            # 5회차 판정축 문형: 문장이 후보 선호 규칙이 아니라 판정 트리에서
            # 나온다.  근거는 evidence["axis"] 가 들고 있고, 낱말 검사는
            # test_description_words_all_come_from_the_drawing 쪽이 한다.
            continue
        kinds = {c["kind"] for c in (r["evidence"].get("candidates") or [])}
        if {"EQUIPMENT", "CONNECTOR"} <= kinds and r["description"]:
            both += 1
            sel = r["evidence"].get("description_selected") or {}
            assert sel.get("kind") == "EQUIPMENT", (
                f"row {r['key']} had equipment and a line and chose the line")
    assert both, "no row had both axes available"


@pytest.mark.slow
def test_a_stack_of_signal_bubbles_is_one_physical_instrument(first_run):
    """One switch reporting LSHH, LSH and LSL is one row, not three.

    The user confirmed it against plant practice; the drawing cannot say it -
    legend p3 draws a multi-function instrument as a single bubble and never
    draws a stack.  So the grouping stays a measurement (touching, stacked, same
    variable) and only the *answer* to it comes from config.
    """
    groups = first_run["signal_groups"]
    assert groups, "no stacked bubble group found on a document that has 34"
    by_key = {r["key"]: r for r in first_run["rows"]}
    for g in groups:
        assert len(set(m["anchor"][:1] for m in g["members"])) == 1
        assert all(gap <= g["basis"]["slack_pt"]
                   for gap in g["basis"]["touching_gaps_pt"])
        kept = [m for m in g["members"] if m["key"] in by_key]
        if not pipeline.MULTI_SIGNAL_MERGE:
            assert len(kept) == len(g["members"])
            for m in kept:
                assert pipeline.MULTI_SIGNAL_REASON in by_key[m["key"]]["needs_review"]
            continue
        # merged: one row survives, named what the client names it, carrying the
        # multiplier for one device and the signals it stands for
        assert len(kept) == 1, f"{len(kept)} rows survived a {len(g['members'])}-bubble stack"
        row = by_key[kept[0]["key"]]
        assert row["type"] == pipeline.MULTI_SIGNAL_TYPE
        assert row["evidence"]["signal_members"] == [m["anchor"] for m in g["members"]]
        assert pipeline.MULTI_SIGNAL_REASON not in (row["needs_review"] or "")
        assert row["qty"] == g["basis"]["qty_applied"][0], (
            "the surviving row must carry one device's multiplier, not the sum")


@pytest.mark.slow
def test_merging_a_stack_leaves_every_other_row_alone(first_run):
    """The client's own 22 level-switch rows are on sheets with no stack at all."""
    groups = first_run["signal_groups"]
    folded = {m["key"] for g in groups for m in g["members"][1:]}
    kept = {r["key"] for r in first_run["rows"]}
    assert not (folded & kept), "a folded bubble is still in the row set"
    stacked_pages = {g["page_no"] for g in groups}
    others = [r for r in first_run["rows"]
              if r["type"] == pipeline.MULTI_SIGNAL_TYPE
              and r["page_no"] not in stacked_pages]
    assert others, "no un-stacked level switch left to check"
    for r in others:
        assert not (r["evidence"] or {}).get("signal_members"), (
            "a switch on a sheet with no stack was folded")


@pytest.mark.slow
def test_description_scope_is_a_separate_axis_from_the_list(first_run):
    """A row exempt from Description is still a row, and is not traced.

    Whether an item is in the list and whether it needs a Description are two
    different questions; mixing them would drop other-party items out of the
    deliverable, which is the opposite of what the client does with them.
    """
    exempt = [r for r in first_run["rows"]
              if r["evidence"].get("description_needed") is False]
    # An empty set is a legitimate outcome, not a failure: `supplier_interface_span
    # .description: keep` (config, with the client rows that decided it) means a
    # document can exempt nothing at all.  What this test guards is the shape of an
    # exemption when one exists, so it must not also demand that one exists.
    for r in exempt:
        assert r["tab"] != pipeline.TAB_REVIEW or r["needs_review"]
        assert r["evidence"]["trace"]["status"] == pipeline.SKIPPED, (
            "an item we do not describe should not be traced")
        assert r["evidence"]["description_note"], "no reason given for the skip"
    stats = first_run["pipe_trace"]
    assert stats["skipped_not_needed"] == len(exempt)
    assert stats["description_needed"] + stats["skipped_not_needed"] <= len(
        first_run["rows"])
    # both denominators are reported, and the honest one is the larger rate
    assert stats["rate_of_needed"] >= stats["rate_of_all_rows"]


@pytest.mark.slow
def test_row_keys_are_unique_and_stable(first_run, second_run):
    """A row's identity has to survive a re-run, or edits cannot be carried."""
    ka = [r["key"] for r in first_run["rows"]]
    kb = [r["key"] for r in second_run["rows"]]
    assert len(ka) == len(set(ka)), "row keys collide within one run"
    assert set(ka) == set(kb), "row keys changed between runs"


@pytest.mark.slow
def test_user_edits_survive_reanalysis(tmp_path, first_run, second_run):
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", PDF)
    db.store_result(con, "j", first_run)

    row = db.merged_rows(con, "j")[0]
    db.set_user_value(con, "j", row["key"], "description", "hand written")
    db.set_user_value(con, "j", row["key"], "tag_no", "PT-0001")

    summary = db.store_result(con, "j", second_run)

    after = next(r for r in db.merged_rows(con, "j") if r["key"] == row["key"])
    assert after["values"]["description"] == "hand written"
    assert after["values"]["tag_no"] == "PT-0001"
    assert after["ai"] == row["ai"], "the engine's own values should be refreshed as-is"
    assert summary["kept_edits"] >= 2
    assert summary["conflicts"] == [], "an unchanged re-run cannot conflict"


def test_segments_are_not_mutated_by_the_engine():
    """`segments()` hands out the drawing cache's own points; nothing may move them.

    On an unrotated page the rotation matrix is the identity, so `segments()`
    skips building a multiplied copy of every point - which is where most of the
    analysis time went.  The price is that the points it returns belong to the
    cached drawings.  This runs the three modules that consume them over a real
    page and checks that not one coordinate moved.
    """
    sys.path.insert(0, str(ROOT / "app" / "engine"))
    import pidcache                      # noqa: E402
    import detect_symbols as ds          # noqa: E402
    import detect_valves as dv           # noqa: E402
    import legend_rules                  # noqa: E402

    doc, pages = pidcache.load_pages(PDF)
    pc = next(p for p in pages if p.page_no == 6)
    before = [(p0.x, p0.y, p1.x, p1.y) for p0, p1 in pc.segments()]
    ids = [(id(p0), id(p1)) for p0, p1 in pc.segments()]

    ds.detect(pc, rules=ds.RULESET_V3)
    dv.analyse(pc, dv.LAYOUT)
    legend_rules.stroke_index(pc.segments())

    after = [(p0.x, p0.y, p1.x, p1.y) for p0, p1 in pc.segments()]
    assert after == before, "a caller moved a point in the shared drawing cache"
    assert ids == [(id(p0), id(p1)) for p0, p1 in pc.segments()], \
        "the segment list was rebuilt; the cache is not being reused"


def test_origin_needs_no_answer_key():
    """Attribution must not depend on a finished list the user does not have.

    In real use the inputs are the drawings and an empty output form; a filled-in
    instrument list exists only in verification.  So with no reference every page
    is DRAWING, and REVISION_GAP - which is read off the drawing itself - still
    works.  MATCHED and PDF_ONLY may not appear.
    """
    per_page = {6: {"drawing_no": "D-6", "annotations": []},
                7: {"drawing_no": "D-7", "annotations": [{"where": "DRAWING"}]}}

    plain = pipeline._page_origins(None, None, dict(per_page))
    assert plain[6] == pipeline.ORIGIN_DRAWING
    assert plain[7] == pipeline.ORIGIN_REVISION_GAP
    assert pipeline.ORIGIN_MATCHED not in plain.values()
    assert pipeline.ORIGIN_PDF_ONLY not in plain.values()

    # A reference that is named but absent must not silently read as PDF_ONLY.
    missing = pipeline._page_origins(None, None, dict(per_page),
                                     reference=Path("no/such/list.xlsx"))
    assert missing[6] == pipeline.ORIGIN_DRAWING


def test_the_answer_key_is_opt_in():
    """The verification-only input cannot creep back in as a default."""
    import inspect
    assert not hasattr(pipeline, "REFERENCE_EXCEL"), (
        "the answer key is a verification argument, not a module constant")
    sig = inspect.signature(pipeline.analyse)
    assert sig.parameters["reference"].default is None
    from app import main
    assert (main.VERIFY_AGAINST is None) == (not os.environ.get("PID_VERIFY_EXCEL"))


def test_conflicting_reanalysis_is_flagged(tmp_path):
    """When the engine changes a field a person had overridden, say so.

    Built from two small synthetic results rather than the PDF: the point is the
    merge rule, and forcing the engine to change its mind about a real drawing
    would mean changing detection logic.
    """
    def result(type_):
        return {
            "pages": [{"page_no": 1, "drawing_no": "D", "title": "T",
                       "page_kind": "PID", "in_scope": True, "scope_reason": "",
                       "width": 10.0, "height": 10.0}],
            "layers": {},
            "rows": [{"key": "k1", "tab": "FIELD", "page_no": 1, "rect": [0, 0, 1, 1],
                      "type": type_, "qty": 2, "system": "S", "valve_type": "",
                      "vendor_supply": "", "scope": "", "description": "",
                      "tag_no": "", "needs_review": "", "annotation": "",
                      "evidence": {}}],
            "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
            "fingerprint": "f",
        }

    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", result("PIT"))
    db.set_user_value(con, "j", "k1", "type", "PDIT")

    summary = db.store_result(con, "j", result("TIT"))

    assert len(summary["conflicts"]) == 1
    fields = summary["conflicts"][0]["fields"]
    assert fields["type"] == {"was_ai": "PIT", "now_ai": "TIT", "user": "PDIT"}

    row = db.merged_rows(con, "j")[0]
    assert row["values"]["type"] == "PDIT", "the edit still wins until reviewed"
    assert row["ai"]["type"] == "TIT", "and the engine's new answer is kept too"
    assert "re-analysis changed" in row["needs_review"]
    assert db.review_count(con, "j") == 1

    # Touching the field settles it: the person has now looked at the conflict.
    db.set_user_value(con, "j", "k1", "type", "TIT")
    assert db.merged_rows(con, "j")[0]["conflict"] == {}


def test_vanished_rows_are_marked_not_dropped(tmp_path):
    """A row that stops being detected may be carrying an edit."""
    base = {
        "pages": [], "layers": {}, "multipliers": {}, "legend": {},
        "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [{"key": "k1", "tab": "FIELD", "page_no": 1, "rect": [],
                  "type": "PIT", "qty": 1, "system": "", "valve_type": "",
                  "vendor_supply": "", "scope": "", "description": "",
                  "tag_no": "", "needs_review": "", "annotation": "",
                  "evidence": {}}],
    }
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", base)
    db.set_user_value(con, "j", "k1", "tag_no", "PT-1")

    db.store_result(con, "j", dict(base, rows=[]))

    row = db.merged_rows(con, "j")[0]
    assert row["deleted"] is True
    assert row["values"]["tag_no"] == "PT-1"
    assert db.review_count(con, "j") == 1


def test_reviewer_added_rows_survive_reanalysis(tmp_path):
    """A hand-added row is not a detection, so a re-run must leave it alone.

    Without this the vanished-row sweep struck out every reviewer-added row on
    each re-analysis, because the engine never proposes them and so they are
    always "missing" from a fresh result.
    """
    base = {
        "pages": [], "layers": {}, "multipliers": {}, "legend": {},
        "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [{"key": "k1", "tab": "FIELD", "page_no": 1, "rect": [],
                  "type": "PIT", "qty": 1, "system": "", "valve_type": "",
                  "vendor_supply": "", "scope": "", "description": "",
                  "tag_no": "", "needs_review": "", "annotation": "",
                  "evidence": {}}],
    }
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", base)
    added = db.add_row(con, "j", 1, "FIELD", "MATCHED", "D",
                       {"type": "HAND", "qty": 3})

    db.store_result(con, "j", base)          # same analysis again

    rows = {r["key"]: r for r in db.merged_rows(con, "j")}
    assert added in rows, "the hand-added row disappeared"
    assert rows[added]["deleted"] is False, "the hand-added row was struck out"
    assert rows[added]["values"]["type"] == "HAND"
    assert rows[added]["added"] is True


def test_removed_rows_leave_the_export_but_not_the_grid(tmp_path):
    base = {
        "pages": [], "layers": {}, "multipliers": {}, "legend": {},
        "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [{"key": "k1", "tab": "FIELD", "page_no": 1, "rect": [],
                  "type": "PIT", "qty": 1, "system": "", "valve_type": "",
                  "vendor_supply": "", "scope": "", "description": "",
                  "tag_no": "", "needs_review": "", "annotation": "",
                  "evidence": {}}],
    }
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", base)
    out = db.remove_row(con, "j", "k1")
    assert out.get("removed"), "a detection should be struck out, not dropped"
    assert db.merged_rows(con, "j")[0]["removed"] is True, "still visible in the grid"
    rev = db.snapshot(con, "j")
    assert db.get_revision(con, rev)["rows"] == [], "struck-out row must not export"


def test_excel_comes_only_from_a_snapshot(tmp_path):
    """A revision is a frozen copy; later edits must not leak into it."""
    base = {
        "pages": [], "layers": {}, "multipliers": {}, "legend": {},
        "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [{"key": "k1", "tab": "FIELD", "page_no": 1, "rect": [],
                  "type": "PIT", "qty": 1, "system": "", "valve_type": "",
                  "vendor_supply": "", "scope": "", "description": "",
                  "tag_no": "", "needs_review": "", "annotation": "",
                  "evidence": {}}],
    }
    con = db.connect(tmp_path / "t.db")
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", base)
    rev = db.snapshot(con, "j", "first")

    db.set_user_value(con, "j", "k1", "type", "CHANGED-AFTER")

    snap = db.get_revision(con, rev)
    assert snap["rows"][0]["values"]["type"] == "PIT"
    assert db.merged_rows(con, "j")[0]["values"]["type"] == "CHANGED-AFTER"
