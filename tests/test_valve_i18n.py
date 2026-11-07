"""valve31 — every tool comment template has a Korean form (fixed templates, no machine translation)."""
from __future__ import annotations

import pytest

from app.valve import i18n

SAMPLES = [
    "Design Pressure: no value; ref. 08-84-PR-DTS-00002 (Note 8). Provide value.",
    "Flow Rate: no value (Max/Nor/Min); ref. 315-98-PR-DTS-00007 (Gen. Note 34). Provide value.",
    "Fluid: no value. Provide value.",
    "'Note-7, Hold-1' on HOLD/TBC. Release and give value.",
    "HOLD 2 'Torque values' on HOLD/TBC. Release and confirm.",
    "Note 9 'Fluid phase TBC' on HOLD/TBC. Release and confirm.",
    "Class in Line No. '3C3AS1' differs from Piping class '1C3AS1'",
    "Referenced General Note 33 does not exist in 08-84-IN-DTS-00003",
    "Referenced Note 12 does not exist on this datasheet",
    "Refers to Note 7 ('Painting as per spec'); should be Note 8 ('Leakage class').",
    "Line Number on p.2 is 'FG8404-3\"' — sheet 1 says 'FG8404-4\"'",
    "Label/value pairing of 'Fluid' could not be settled by the tool — check",
    "Modified: '2 sch. 40S' → '2 sch. 80S'",
    "Line No.: Datasheet 'A' vs Process Data 'B' (Ref. Process Data CO2S-SSG-IN-REQ-00009 p.54)",
    "Fluid: Partly the same words: Datasheet 'CO2 gas' vs Process Data 'CO2' (Ref. Process Data X p.3)",
    "Design Pressure: Different basis: 'barg' vs 'bara' (no atmospheric correction made) (Ref. Process Data X p.3)",
    "Flow Rate: Unit differs ('kg/h' vs 'Sm3/h') (Ref. Process Data X p.3)",
    "Safety (Fail) Position: Datasheet fail close, Process Data FO (fail open) (Ref. Process Data X p.12)",
    "Piping Material Class: Piping class '3C3AS1' not in PMS QN area but found in QS — please confirm (Class 3C3AS1)",
    "Piping Material Class: Piping class 'API5L-X65' is not defined in PMS QN (Class API5L-X65)",
    "Piping Material Class: Piping class '1C3AS2-A' not in PMS; matched '1C3AS2' — please confirm (Class 1C3AS2)",
    "Fire Safe: Datasheet fire-safe is on HOLD / TBC — PMS item requires fire test (Class 3C3AS1)",
    "Bore: PMS ball valve for 3\" in class 3C3AS1 is REDUCED PORT (item PVBC2S30RF02P009D003, 0.5–6\") — datasheet says FULL BORE; confirm the deviation (FULL PORT only as another valve type, e.g. DBB) (Class 3C3AS1)",
    "Ball Valve Item: No ball valve item for size 2\" in class 1R1B1 (Class 1R1B1)",
    "Seat Material: Different material: required RTFE, datasheet PEEK (Class 1C0K8)",
    "Body Material: Datasheet value is 'VTA' — nothing to verify · PMS item PVBSED (Class XC0K8)",
    "Pressure Class: PMS class 3C3AS1 is CLASS 300 (Class 3C3AS1)",
    "NACE: PMS class requires NACE (Class 3C3AS1)",
    "CS body in CO2 service (no CA). Confirm dry CO2 or use SS.",
    "CS body in sour service: max. 22 HRC, welds max. 250 HV10, NACE certified.",
    "17-4PH stem: state H1150D, max. 33 HRC (ISO 15156-3).",
    "State hard-facing type and thickness (e.g. TCC HVOF).",
    "Submit API 607 / ISO 10497 fire test certificate covering size and class.",
    "Based on Ref. Process Data CO2S (p.12) design temp. 170 °C, seat RTFE (limit 150 °C, PMS 1C3AS1 Note 4) shall be reviewed.",
    "Based on Ref. Process Data CO2S (p.12) design temp. 170 °C, exceeds PMS 1C0K8 max. 150 °C. Confirm piping class / design temp.",
    "Body CS A216-WCB not suitable for low-temp. line. Use A352 LCC / A350 LF2 (impact tested).",
    "Body CS vs pipe SS: different material. Confirm.",
    "B8M CL.2 bolting not acceptable if exposed (ISO 15156). Confirm non-exposed or use B8M CL.1 / B7M.",
    "State seal / O-ring materials, RGD qualified (ISO 23936-2 / NORSOK M-710).",
    "Based on Ref. Process Data CO2S (p.12) fluid 'H2S': not in PMS 1C3AS1 service list. Confirm piping class.",
    "Based on Datasheet design temp. 200 °C, seat PTFE (typ. max. 200 °C) shall be reviewed or P-T curve submitted.",
    "PMS 1C3AS1 Note 3: dual-grade 316/316L required. Material shall be reviewed.",
    "B7/2H bolting in NACE service: use B7M/2HM (max. 22 HRC) if exposed.",
    "Based on Ref. Process Data CO2S (p.12) design temp. 120 °C, close to RTFE seat limit (~150 °C). Submit seat P-T curve.",
    "Based on Ref. Process Data CO2S (p.12) design press. 50 barg, design temp. 60 °C, exceeds PMS 1R1B rating 46.0 barg. Confirm.",
    "Flange facing RTJ; PMS 1C3AS1 requires RF. Flange facing shall be reviewed.",
    "26\" valve: flanges to ASME B16.47 Series A/B. State series.",
    "Floating ball 8\" Class 600: confirm torque / design or use trunnion.",
    "Fail Close requires spring-return actuator. Actuator type shall be reviewed.",
    "Fail last with spring specified. Confirm fail action.",
    "SIL 2 with fail last. Confirm fail-safe position.",
    "SIL 2: confirm PST requirement and SIL certificate.",
    "Soft seat with ISO 5208 Rate B. Confirm Rate A.",
    "State anti-static device (API 6D / ISO 17292).",
    "Based on Ref. Process Data CO2S (p.12) fluid 'CO2': fire-safe (API 607) not stated on datasheet. State it.",
    "Based on Datasheet fluid phase 'Liquid': state seat design (SPE/DPE) and cavity relief.",
    "Cold insulation: specify extended stem / bonnet.",
    "Piggable line: reduced bore not acceptable, use full bore.",
    "Valve 4\" larger than line 3 sch. 40S. Valve size shall be reviewed.",
    "Full-bore valve 4\" in 6\" line. Confirm size.",
    "Erosive service with soft seat PEEK. Consider metal seat.",
    "Actuator safety factor 1.1 below 1.25. Confirm.",
    "Trunnion specified; PMS item PVB123 is floating. Align with PMS.",
    "'CS A216-WCB' differs from 5/6 1C0K8 datasheets ('SS 316'). Confirm.",
    "ESDV tag with fail position 'Open'. Confirm tag or fail action.",
    "Limit switch 'Required' specified; General Note 20 says limit switches shall not be used. Shall be reviewed.",
    "SIL 2 valve: position transmitter SIL rating shall be confirmed (General Note 20).",
    "2 SOVs (98ESDY-1A, 98ESDY-1B): voting (1oo2 / 2oo2 / 2oo3) and online test arrangement shall be stated.",
    "No position transmitter on the datasheet; General Note 20 requires one for XV. Shall be reviewed.",
    "Positioner in Note 3 is not the Fisher DVC required by General Note 15. Shall be reviewed.",
    "The tag cannot be split into prefix (system/unit) + function code + loop number (+ suffix) like the other tags.",
    "The tag 98ESDV001 appears in documents A, B: two valves must not share a tag (or the same valve is specified twice).",
    "Tags of North Unit 98 use 3-digit numbers starting '0' (NNN); this tag's number is 9801.",
    "Shut Down Valve (SDV) normally fails closed; this datasheet says 'Open'. Either the tag function or the fail position is wrong.",
]


@pytest.mark.parametrize("en", SAMPLES)
def test_every_template_has_korean(en):
    k = i18n.ko(en)
    assert k and k != en and any("가" <= ch <= "힣" for ch in k), en
    for q in __import__("re").findall(r"'([^']+)'", en):       # quoted values (the evidence) survive untouched
        assert q in k, (en, k)


def test_reviewer_words_are_not_translated_and_pick_rules():
    assert i18n.ko("check this torque please") is None
    assert i18n.pick("EN", "KO", "en") == "EN" and i18n.pick("EN", "KO", "ko") == "KO" and i18n.pick("EN", None, "ko") == "EN"
    assert i18n.pick("EN", "KO", "both") == "EN\nKO"
    rows = i18n.attach([{"description": SAMPLES[0], "type": "Data Missing"}, {"description": "my words", "type": "Reviewer Comment", "comment_id": 3},
                        {"description": SAMPLES[0], "type": "Data Missing", "edited": True}])
    assert "description_ko" in rows[0] and "description_ko" not in rows[1] and "description_ko" not in rows[2]


def test_exports_print_the_chosen_language(tmp_path, monkeypatch):
    import io

    import openpyxl
    import pymupdf

    from tests.test_valve_revision import _client, _pdf
    c, pid, up = _client(tmp_path, monkeypatch)
    up("ds_A.pdf", _pdf("A", values={2: ["HOLD", "TBC"]}))
    ds = c.get(f"/api/valve/projects/{pid}/summary").json()["tags"][0]["id"]
    iss = c.get(f"/api/valve/datasheets/{ds}").json()["issues"]
    assert any(i.get("description_ko") for i in iss)                       # the screen gets both
    def desc(lang):
        ws = openpyxl.load_workbook(io.BytesIO(c.get(f"/api/valve/projects/{pid}/issues.xlsx?lang={lang}").content))["Issue List"]
        h = [x.value for x in ws[1]]
        return [ws.cell(r, h.index("Description") + 1).value or "" for r in range(2, ws.max_row + 1)]
    en, ko, both = desc("en"), desc("ko"), desc("both")
    hangul = lambda s: any("가" <= ch <= "힣" for ch in s)   # noqa: E731
    assert not any(hangul(x) for x in en) and any(hangul(x) for x in ko)
    assert any("\n" in x and hangul(x) for x in both)
    pdf = pymupdf.open("pdf", c.get(f"/api/valve/projects/{pid}/markup.pdf?lang=ko").content)
    assert hangul("".join(p.get_text() for p in pdf))
