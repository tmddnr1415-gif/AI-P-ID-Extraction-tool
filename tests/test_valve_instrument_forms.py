"""Instrument datasheet form cards (app/valve/forms/*.json) — made by spike/valve_form_learn.py from the blank forms.

The blank PDFs are client material and are not in the repository, so these tests read the committed cards only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

FORMS = Path(__file__).resolve().parents[1] / "app" / "valve" / "forms"
CARDS = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(FORMS.glob("*.json"))
         if p.stem not in ("index", "lists")}
INDEX = json.loads((FORMS / "index.json").read_text(encoding="utf-8"))
LISTS = json.loads((FORMS / "lists.json").read_text(encoding="utf-8"))

EXPECTED = {"80": 61, "101": 100, "701": 50, "203": 40, "310": 41, "313": 48, "505": 50, "506": 48, "5063": 50,
            "601": 48, "605": 47, "606": 47, "801": 30, "803": 45}          # last row number printed (block 1)
# Owner / project / contractor words printed in the title blocks must never reach a card.  Only their hashes are kept
# here (sha256 of the lower-case word, first 16 hex) so this test file does not carry the names either.
FORBIDDEN_HASHES = {"1aadf006fccec7e8", "709e8e532a85a053", "968e2d5b08687bf4", "9732ee712bdc35a6", "9f98cf0d10158817", "f31aa9a53ec2a713", "f958d859cf0fbe2a"}


def _tokens(text):
    return {t for t in re.findall(r"[a-z0-9_/]+", text.lower()) if len(t) >= 5}


def test_all_forms_have_a_card():
    assert set(CARDS) == set(EXPECTED)
    assert [r["form_id"] for r in INDEX] and {r["form_id"] for r in INDEX} == set(EXPECTED)


@pytest.mark.parametrize("fid", sorted(EXPECTED))
def test_card_identity(fid):
    c = CARDS[fid]
    assert c["form_id"] == fid and c["title"] and c["item_kind"]
    assert c["footer_tag"] or c["identify"]
    assert any(i["kind"] == "file_name" for i in c["identify"])
    assert c["page_size"] in ("A4", "Letter") and c["pages"] >= 1
    assert c["required"]["status"].startswith("suggested")


@pytest.mark.parametrize("fid", sorted(EXPECTED))
def test_items_numbered_without_gaps(fid):
    c = CARDS[fid]
    allowed = {str(k): set(v) for k, v in c["numbering"].get("allowed_gaps", {}).items()}
    blocks = sorted({it["block"] for it in c["items"]})
    for b in blocks:
        nos = [it["no"] for it in c["items"] if it["block"] == b]
        assert len(nos) == len(set(nos)), f"{fid} block {b}: duplicate numbers"
        missing = set(range(1, max(nos) + 1)) - set(nos)
        assert missing <= allowed.get(str(b), set()), f"{fid} block {b}: missing {sorted(missing)}"
    assert max(it["no"] for it in c["items"] if it["block"] == 1) == EXPECTED[fid]


@pytest.mark.parametrize("fid", sorted(EXPECTED))
def test_labels_and_sections(fid):
    c = CARDS[fid]
    ambiguous = {(a["block"], a["no"]) for a in c["ambiguous"]}
    for it in c["items"]:
        assert it["section"], f"{fid} {it['no']}: no section"
        if not it["label"]:                                   # only allowed when the card says why
            assert (it["block"], it["no"]) in ambiguous, f"{fid} {it['no']}: empty label not listed as ambiguous"
        assert it["label_bbox"] is None or len(it["label_bbox"]) == 4
        assert len(it["value_bbox"]) == 4


def test_kinds_unique_and_short():
    kinds = [c["item_kind"] for c in CARDS.values()]
    assert len(kinds) == len(set(kinds))
    assert all(re.fullmatch(r"[a-z]{2,8}", k) for k in kinds)


@pytest.mark.parametrize("fid", sorted(EXPECTED))
def test_std_key_coverage(fid):
    c = CARDS[fid]
    keys = {it["std_key"] for it in c["items"]} | {k for it in c["items"] for k in it.get("std_keys_also", [])}
    labels = " | ".join(it["label"].lower() for it in c["items"])
    assert "tag" in keys and "service" in keys
    if "p&id" in labels or "pid no" in labels:
        assert "pid_no" in keys
    if "line no" in labels or "line number" in labels:
        assert "line_no" in keys
    if "service class" in labels or "piping class" in labels or "serviceclass" in labels:
        assert "piping_class" in keys
    if "quantity tags" in labels or "tag quantity" in labels:
        assert "tag_qty" in keys
    assert "manufacturer" in keys or any(k.endswith("manufacturer") for k in keys)
    process = [it for it in c["items"] if it["process"]]
    if any(it["section"].upper().startswith("PRO") for it in c["items"]):     # 203 / 801 have no process block
        assert process, f"{fid}: no process items"
    assert all(it["label"] for it in process)
    subs = {s.get("std_key") for it in c["items"] for s in it.get("sublabels", [])}
    if "quantity tags" in " ".join(s.get("text", "").lower() for it in c["items"] for s in it.get("sublabels", [])):
        assert "tag_qty" in subs


def test_no_owner_or_project_names_written():
    import hashlib
    for p in FORMS.glob("*.json"):
        toks = _tokens(p.read_text(encoding="utf-8"))
        hit = {t for t in toks if hashlib.sha256(t.encode()).hexdigest()[:16] in FORBIDDEN_HASHES}
        assert not hit, p.name


def test_lists_headers_only():
    for k in ("instrument_index", "io_list"):
        x = LISTS[k]
        heads = " ".join(c["header"].upper() for c in x["columns"])
        assert "TAG NO" in heads and "P&ID NO" in heads and x["orientation"] == "landscape"
    for side in ("north", "south"):
        t = next(t for t in LISTS["process_line_list"][side]["tables"] if t.get("columns"))
        cols = {c["header"] for c in t["columns"]}
        assert {"LINE NUMBER", "PIPE CLASS"} <= cols
        assert any(h.startswith("DESIGN CONDITIONS / PRESSURE") for h in cols)
        assert len(t["example_line_no"]) <= 3
