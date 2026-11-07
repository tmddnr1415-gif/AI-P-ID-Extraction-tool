"""valve22 — extraction robustness gate: synthetic On/Off-form PDFs with layout variations (spike/valve_sim_pdf.py).
Measures the reader against the values it placed; the thresholds are what the generator honestly reaches
(missing row numbers are a known weakness — a row without a number is not read — and are excluded here)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike"))

import valve_sim_pdf as sim  # noqa: E402


def test_extraction_robustness_gate():
    vars_ = [v for v in sim.VARIATIONS if v != "missing_row_numbers"]
    agg, _ = sim.run(len(vars_) * 2, 7, None, vars_)          # 36 PDFs, fixed seed
    tot = {"n": 0, "fields": 0, "hit": 0, "mapped": 0, "map_ok": 0, "false_review": 0, "exc": 0, "tag": 0, "doc": 0, "scanned_ok": 0}
    for var, a in agg.items():
        for k in tot:
            tot[k] += a[k]
        assert a["exc"] == 0, var
        if var == "scanned":
            assert a["scanned_ok"] == a["n"], "a scanned page must be reported as scanned, never misread"
        else:
            assert a["tag"] == a["n"] and a["doc"] == a["n"], var
    assert tot["hit"] / tot["fields"] >= 0.98 and tot["map_ok"] / tot["mapped"] >= 0.98
    assert tot["false_review"] == 0                              # vendor wording is kept for review, never misread as a key


def test_variations_the_reader_now_handles():
    """Each of these was a defect before valve22: a Max/Nor/Min sub-block under the rows sent the page down the Form 102
    path, 'Note-1' / 'NOTE-01' numbering was not a note, a 0.1° skewed form lost its rules, a note on the NOTES line was lost."""
    for var in ("max_nor_min_block", "note_style_dash", "note_style_upper", "skew", "font_large"):
        agg, _ = sim.run(3, 11, None, [var])
        a = agg[var]
        assert a["exc"] == 0 and a["hit"] == a["fields"] and a["notes"] == a["n"], (var, dict(a))
