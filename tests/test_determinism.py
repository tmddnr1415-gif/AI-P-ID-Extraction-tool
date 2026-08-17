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
