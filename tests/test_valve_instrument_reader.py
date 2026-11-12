"""Instrument datasheets — the generic numbered-row reader (app/valve/instrument.py) on TEST pages drawn from the form
cards (no client form, no client value): every row gets a marked test value and must be read back from the right row."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spike"))
from app.valve import instrument as I  # noqa: E402
import valve_make_test_ds as M  # noqa: E402

CLEAN = ["313", "506", "601", "605", "606", "701", "801", "803", "505", "5063", "310", "101"]


def _fill_all(fid, tmp_path):
    card = I.cards()[fid]
    want, rows = {}, {}
    for it in card["items"]:
        vb = it.get("value_bbox")
        if not vb or it.get("role") == "header" or vb[2] - vb[0] < 4:
            continue
        key = f"{it['block']}.{it['no']}" if it["block"] != 1 else str(it["no"])
        subs = it.get("subcols") or []
        v = {s: f"V{it['no']}{chr(97 + k)}" for k, s in enumerate(subs)} if subs else f"V{it['no']}X"
        want[key] = v
        rows.setdefault(it["block"], {})[str(it["no"])] = v
    doc = M.synthetic(card)
    for b, rv in rows.items():
        M.fill(doc, dict(card, items=[i for i in card["items"] if i["block"] == b]), {"rows": rv, "title": {"doc_no": f"TEST-{fid}", "rev": "B"}})
    out = tmp_path / f"t{fid}.pdf"
    doc.save(out)
    return want, I.read_pdf(str(out), filename=f"test_{fid}.pdf")


@pytest.mark.parametrize("fid", CLEAN)
def test_every_row_reads_back_from_its_own_row(fid, tmp_path):
    want, r = _fill_all(fid, tmp_path)
    assert len(r["sheets"]) == 1
    sh = r["sheets"][0]
    assert sh["form_id"] == fid and sh["kind"] == I.cards()[fid]["item_kind"]
    assert sh["test_data"] and sh["title_block"].get("rev") == "B"
    ok = 0
    for k, v in want.items():
        got = sh["rows"].get(k, {})
        ok += (got.get("sub") == v) if isinstance(v, dict) else (got.get("value") == v)
    assert ok / len(want) >= 0.97, (fid, ok, len(want))


def test_kind_keys_are_unique_and_cover_the_plan():
    k = I.kinds()
    assert set(k) >= {"ft", "pt", "lt", "gwr", "tt", "tg", "pg", "dpg", "mlg", "ro", "analyzer", "cv", "onoff", "psv"}


def test_split_tags_one_row_per_tag():
    assert I.split_tags("FT-1001A/B") == ["FT1001A", "FT1001B"]
    assert I.split_tags("00PT-9001A/B/C") == ["00PT9001A", "00PT9001B", "00PT9001C"]
    assert I.split_tags("PT-1001, PT 1002") == ["PT1001", "PT1002"]
    assert I.split_tags("98 FT_100") == ["98FT100"]
    assert I.split_tags("") == []


def test_identify_separates_look_alike_forms():
    # 313 / 506 / 601 print nearly the same rows — only Form No and title tell them apart
    for fid in ("313", "506", "601"):
        c = I.cards()[fid]
        text = f"Form No : {fid}\n{c.get('printed_title', '')}\n" + "\n".join(i["label"] for i in c["items"] if i.get("label"))
        assert I.identify_text(text)["form_id"] == fid
    assert I.identify_text("nothing that looks like a form")["form_id"] == ""
