"""What a shipped build has to be able to do, checked without shipping one.

Three separable things are pinned here:

  * an error report carries the evidence *automatically*.  The whole design
    depends on a person typing two fields and no more, so a change that quietly
    starts asking them for a coordinate should fail a test rather than a user.
  * the diagnostic export names what it leaves out.  "The drawings do not leave
    the PC" is a promise, and a promise that is only in a comment is not kept.
  * the packaging separates what is read from what is written, and does not
    bundle the client's documents.

None of this needs an analysis: the fixtures build a job by hand.
"""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db, paths, version    # noqa: E402


@pytest.fixture()
def con(tmp_path):
    return db.connect(tmp_path / "app.db")


@pytest.fixture()
def job(con, tmp_path):
    """One done job with one row, one edit and one review state."""
    pdf = tmp_path / "sheet.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    db.create_job(con, "j1", "sheet.pdf", "abc123", pdf)
    db.store_result(con, "j1", {
        "fingerprint": "ff00ff00",
        "pages": [{"page_no": 6, "drawing_no": "D00P-10LBA10-M05-0001",
                   "title": "P&ID FOR HP STEAM", "page_kind": "PID",
                   "in_scope": True, "scope_reason": "", "width": 2384.0,
                   "height": 1684.0}],
        "layers": {"6": {}},
        "rows": [{
            "key": "row1", "tab": "FIELD", "page_no": 6,
            "drawing_no": "D00P-10LBA10-M05-0001", "origin": "DRAWING",
            "rect": [10.0, 20.0, 30.0, 40.0],
            "type": "PIT", "qty": 2, "system": "HP Steam", "valve_type": "",
            "vendor_supply": "", "scope": "", "tag_no": "",
            "description": "UNIT #10 HP STEAM PRESSURE",
            "description_grade": "CONFIRMED", "remark": "",
            "needs_review": "", "annotation": "",
            "evidence": {"anchor": "PT", "rules_hit": ["VENDOR_MARK_GLYPH"],
                         "qty_basis": "sheet multiplier 2"},
        }],
        "applied_rules": {"instrument_ruleset": "v3-anchor-audit",
                          "layout": {"items": [
                              {"key": "sheet.width_pt", "value": 2384.0,
                               "source": "DERIVED", "evidence": "page rectangle"},
                              {"key": "broken_line.brk_max_mark", "value": 0,
                               "source": "UNAVAILABLE", "evidence": "not isolated"}],
                              "moved": [["sheet.width_pt", 1.0, 2384.0]]}},
        "multipliers": {}, "legend": {}, "glyphs": {}, "job_review": [],
        "timings": {}, "pipe_trace": {}, "description_scope": {},
        "description_build": {}, "description_grades": {},
    })
    db.set_user_value(con, "j1", "row1", "description", "UNIT #10 HP STEAM PRESSURE A")
    db.set_review_state(con, "j1", "row1", "DESC_GRADE_PARTIAL", "EDITED", "")
    return "j1"


# --------------------------------------------------------------------------
# reports
# --------------------------------------------------------------------------

def test_a_report_accepts_two_answers_and_refuses_a_third_kind(con, job):
    rid = db.add_report(con, job, "ROW", "DESCRIPTION", "발주처는 SUCTION 이라고 씁니다",
                        row_key="row1", page_no=6)
    assert db.report_count(con, job) == 1
    with pytest.raises(ValueError):
        db.add_report(con, job, "ROW", "COLOUR", "…")
    with pytest.raises(ValueError):
        db.add_report(con, job, "GUESS", "TYPE", "…")
    # editing changes what a person wrote and nothing else
    before = db.get_report(con, rid)
    after = db.update_report(con, rid, detail="고쳤습니다")
    assert after["detail"] == "고쳤습니다"
    assert after["capture"] == before["capture"]
    assert after["created_at"] == before["created_at"]
    db.delete_report(con, rid)
    assert db.report_count(con, job) == 0
    with pytest.raises(KeyError):
        db.delete_report(con, rid)


def test_the_report_captures_the_evidence_the_reporter_never_types(con, job, monkeypatch):
    """The two typed fields are the *only* two.  Everything else is taken."""
    import app.main as m
    monkeypatch.setattr(m, "CON", con)
    cap = m._capture_row(job, "row1")
    ident = cap["identity"]
    assert ident["drawing_no"] == "D00P-10LBA10-M05-0001"
    assert (ident["page_no"], ident["type"], ident["rect"]) == (6, "PIT", [10.0, 20.0, 30.0, 40.0])
    assert cap["applied_rules"] == ["VENDOR_MARK_GLYPH"]
    assert cap["evidence"]["qty_basis"] == "sheet multiplier 2"
    # both sides of every field the engine and the reviewer disagree on
    assert cap["ai_values"]["description"] == "UNIT #10 HP STEAM PRESSURE"
    assert cap["user_values"]["description"] == "UNIT #10 HP STEAM PRESSURE A"
    assert cap["review_state"]["DESC_GRADE_PARTIAL"]["state"] == "EDITED"
    ctx = m._capture_context(job)
    assert ctx["fingerprint"] == "ff00ff00"
    assert ctx["pdf_sha256"] == "abc123"
    assert ctx["build"]["version"] == version.VERSION
    assert ctx["layout"]["moved"] == [["sheet.width_pt", 1.0, 2384.0]]


# --------------------------------------------------------------------------
# diagnostic export
# --------------------------------------------------------------------------

def test_the_export_carries_the_decisions_and_not_the_documents(
        con, job, tmp_path, monkeypatch):
    import app.main as m
    monkeypatch.setattr(m, "CON", con)
    monkeypatch.setattr(m, "DIAGNOSTICS", tmp_path / "diagnostics")
    db.add_report(con, job, "ROW", "QTY", "승수가 4 여야 합니다", row_key="row1", page_no=6)
    out = m._diagnostic_zip(job)

    info = version.info()
    assert out["filename"].startswith(f"pid_diag_v{info['version']}_")
    assert job in out["filename"]
    assert out["bytes"] > 0

    z = zipfile.ZipFile(tmp_path / "diagnostics" / out["filename"])
    names = set(z.namelist())
    assert {"MANIFEST.json", "reports.json", "edits.json", "feedback.json",
            "analysis/rows.json", "analysis/derived_layout.json",
            "analysis/applied_rules.json", "logs/server.log"} <= names
    # nothing that is the client's, by extension or by content
    assert not [n for n in names if n.lower().endswith((".pdf", ".xlsx"))]

    man = json.loads(z.read("MANIFEST.json"))
    assert man["job"]["fingerprint"] == "ff00ff00"
    assert man["job"]["pdf_sha256"] == "abc123"      # the hash, not the file
    assert man["build"]["version"] == info["version"]
    assert man["build"]["built_at"]
    assert man["counts"]["reports"] == 1
    assert man["counts"]["edits"] == 1
    assert man["excluded"] == m.DIAGNOSTIC_EXCLUDED and man["excluded"]

    # the derived layout is in, because it is the only record of what *that* PC's
    # PDF stated - the whole point of collecting a report from another site
    lay = json.loads(z.read("analysis/derived_layout.json"))
    assert [i["key"] for i in lay["items"]] == ["sheet.width_pt",
                                                "broken_line.brk_max_mark"]
    assert man["counts"]["derived_layout_measured"] == 1
    assert man["counts"]["derived_layout_applied"] == 1
    assert json.loads(z.read("reports.json"))["reports"][0]["what"] == "QTY"


# --------------------------------------------------------------------------
# packaging
# --------------------------------------------------------------------------

def test_what_is_read_and_what_is_written_are_different_roots():
    """A one-file exe unpacks its bundle to a temp dir that is deleted on exit,
    so anything written there is lost.  The two roots must not be the same."""
    assert paths.resource_root() != paths.data_dir()
    assert paths.resource("config", "project_alnouf1.yaml").exists()
    assert not paths.frozen()          # the test suite runs from the checkout


def test_the_recipe_ships_the_code_and_none_of_the_clients_documents():
    spec = (ROOT / "pid_extract.spec").read_text(encoding="utf-8")
    assert '("app/static", "app/static")' in spec
    assert '("config", "config")' in spec
    # the drawings and the workbooks are the client's; `data/` is gitignored for
    # the same reason and must never be a datas entry
    assert '"data"' not in spec.split("datas += [")[1].split("]")[0]
    # the engine's bare-name modules have to be in the bundle under those names
    assert "ENGINE_MODULES" in spec and 'pathex=[".", "app/engine"]' in spec
    build = (ROOT / "build.bat").read_text(encoding="utf-8")
    assert "_build.json" in build and "pytest" in build


def test_the_build_says_which_build_it_is():
    i = version.info()
    assert i["version"] == version.VERSION
    assert i["kind"] in ("exe", "source")
    assert i["built_at"]
    assert version.label().startswith(f"v{i['version']}")
