"""Instrument review — planted-error scenario over EVERY form card (test data only, nothing from a client).

For each of the 14 forms two TEST datasheets are written (spike/valve_make_test_ds.py):
  tag A  every value consistent with the test PDS · Line List · PMS · Instrument Index · IO List  → expect NO finding
  tag B  planted errors (only where the form has the row):
         E1 a required row blank                      → IN-REQ-01
         E2 PDS operating pressure 30 barg ≠ datasheet → IN-PDS-01
         E3 design pressure 2.0 < Line List 3.5 barg   → IN-LL-02
         E4 pipe class 'TX9' (not in PMS · ≠ line)     → IN-PMS-01 · IN-LL-01
         E5 design temperature 60 < Line List 80 °C    → IN-LL-03
         E6 (PT/PG/DPG) range 0-10 < max operating 12  → IN-ITM-01 · (PSV) set 25 > design 2.0 → IN-ITM-02
         E7 Instrument Index service differs · not in IO List → LIST-01 · LIST-00
  plus one tag only in the lists                       → LIST-02
Everything is uploaded through the real API (Document Management upload → reading → review) into a scratch data
folder, then every finding is matched against the plan: missed (false negative) and extra (false positive) are listed.

    python3 spike/valve_inst_scenario.py <work dir> [--forms <folder of blank forms>] [--keep]

--forms writes onto the blank forms (client files: the PDFs stay in <work dir>, never in the repository); without it
plain pages are drawn from the cards.  --keep leaves <work dir>/data for a server (PID_DATA_DIR=<work dir>/data).
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spike"))

import openpyxl  # noqa: E402
import pymupdf  # noqa: E402

PREFIX = {"ft": "FT", "pt": "PT", "lt": "LT", "gwr": "LIT", "tt": "TT", "tg": "TG", "pg": "PG", "dpg": "PDG", "mlg": "LG",
          "ro": "RO", "analyzer": "AT", "cv": "FV", "onoff": "SDV", "psv": "PSV"}
NAMES = {"80": "80-On-Off", "101": "101_-_Control", "203": "203_-_Ana", "310": "310_-_RO", "313": "313_-_FT", "505": "505_-_Mag",
         "506": "506_-_LT", "5063": "5063_-_GWR", "601": "601_-_PT", "605": "605_-_PG", "606": "606_-_DPG", "701": "701_-_Pressure",
         "801": "801_-_TT", "803": "803_-_TG"}
LINE = 'TS1001-6"-TC1A-N'


def tags(kind: str, n: int) -> tuple[str, str]:
    return f"71{PREFIX[kind]}-{9000 + n * 10}A", f"71{PREFIX[kind]}-{9000 + n * 10}B"


def spec(kind: str, bad: bool) -> dict:
    """Semantic values of one test tag."""
    s = {"op": {"max": "12", "nor": "10.5", "min": "8", "unit": "barg"},
         "design_p": "2.0" if bad else "19.6", "op_t": {"max": "65", "nor": "45", "min": "10", "unit": "degC"},
         "design_t": ("60" if bad else "85", "-29"), "fluid": "CO2", "phase": "Vapor", "density": "45.2 kg/m3", "flow": "120 m3/h",
         "class": "TX9" if bad else "TC1A", "line": LINE, "rating": "CL300", "set": "25 barg" if bad else "18 barg",
         "range": {"pt": "0-10 barg" if bad else "0-25 barg", "pg": "0-10 barg" if bad else "0-25 barg", "dpg": "0-10 barg" if bad else "0-25 barg",
                   "ft": "0-200 m3/h", "tt": "0-150 degC", "tg": "0-150 degC"}.get(kind, "0-100 %")}
    return s


def _subcols(card, it):
    if it.get("subcols_from"):
        h = next((x for x in card["items"] if x["no"] == it["subcols_from"] and x["block"] == it["block"]), None)
        return (h or {}).get("subcols") or []
    return it.get("subcols") or []


def cell(card, it, key, S, req_fill="TEST VALUE"):
    """The value to write into one row, in the row's own format."""
    subs, sl = _subcols(card, it), [z["text"] for z in it.get("sublabels") or [] if isinstance(z, dict)]
    op, ot = S["op"], S["op_t"]
    opt = f"{op['max']} / {op['nor']} / {op['min']} {op['unit']}"
    ott = f"{ot['max']} / {ot['nor']} / {ot['min']} {ot['unit']}"
    dpt, dtt = f"{S['design_p']} barg", f"{S['design_t'][0]} / {S['design_t'][1]} degC"
    mnm = lambda q, unit_first=False: {"Max": q["max"], "Nor": q["nor"], "Min": q["min"], "Unit": q["unit"]}   # noqa: E731
    has_mnm = any(x in subs for x in ("Max", "Nor", "Min"))
    if key in ("op_pressure", "upstream_pressure"):
        if has_mnm:
            return mnm(op)
        if "Design Pressure" in sl:
            return {"_": opt, "Design Pressure": dpt}
        if "Oper." in sl or "Oper." in subs:
            d = {"Oper.": opt}
            for c in sl + subs:
                if c.startswith("Des"):
                    d[c] = dpt
            return d
        return opt
    if key == "design_pressure":
        return {"Max": S["design_p"], "Unit": "barg"} if has_mnm else dpt
    if key in ("op_temp", "temperature"):
        if has_mnm:
            return mnm(ot)
        if "Design Temperature" in sl:
            return {"_": ott, "Design Temperature": dtt}
        if "Oper." in sl or "Oper." in subs:
            d = {"Oper.": ott}
            for c in sl + subs:
                if c.startswith("Des"):
                    d[c] = dtt
            return d
        return ott
    if key == "design_temp":
        return {"Max": S["design_t"][0], "Min": S["design_t"][1], "Unit": "degC"} if has_mnm else dtt
    if key == "piping_class":
        for c in ("High", "Inlet"):
            if c in subs:
                return {c: S["class"]}
        if sl:
            return {"_": S["class"]}
        return S["class"]
    if key == "fluid":
        if "phase" in it["label"].lower():
            return f"{S['fluid']} / {S['phase']}"
        if has_mnm:
            return {"Nor": S["fluid"]}
        return {"_": S["fluid"]} if sl else S["fluid"]
    if key == "fluid_state":
        if has_mnm:
            return {"Nor": S["phase"]}
        return {"_": S["phase"]} if sl else S["phase"]
    if key in ("density", "flow"):
        v = S[key]
        if has_mnm:
            n, u = v.split(" ", 1)
            return {"Max": n, "Nor": n, "Min": n, "Unit": u}
        return v
    if key == "line_no":
        return S["line"]
    if key in ("line_size_inlet", "line_size"):
        return {"_": '6"'} if sl else '6"'
    if key == "rating":
        return {"_": S["rating"]} if sl else S["rating"]
    if key in ("range", "calibration_range", "range_adj_range"):
        return S["range"]
    if key == "set_pressure":
        return S["set"]
    if subs:
        return {subs[0]: req_fill}
    return {"_": req_fill} if sl else req_fill


def build_sheet(card, kind, tag, service, bad, blank_key):
    S = spec(kind, bad)
    rows = {}
    keys_set = {"op_pressure", "upstream_pressure", "design_pressure", "op_temp", "temperature", "design_temp", "piping_class", "fluid",
                "fluid_state", "density", "flow", "line_no", "line_size_inlet", "line_size", "rating", "range", "calibration_range",
                "range_adj_range", "set_pressure"}
    req = set((card.get("required") or {}).get("keys", []))
    for it in card["items"]:
        k = it.get("std_key")
        if not k or it.get("role") == "header" or not it.get("value_bbox"):
            continue
        rk = f"{it['block']}.{it['no']}" if it["block"] != 1 else str(it["no"])
        sls = [z for z in it.get("sublabels") or [] if isinstance(z, dict) and z.get("bbox")]
        first_at_start = sls and sls[0]["bbox"][0] - it["value_bbox"][0] < 8 and not it.get("pair_cells")   # no room for the row's own value
        if k == "tag":
            v = {sls[0]["text"]: tag} if first_at_start else tag
        elif k == "tag_qty":
            v = "1"
        elif k == "service":
            v = service
        elif k == "pid_no":
            v = "TEST-PID-0001"
        elif k == "manufacturer":
            v = "TEST MFR"
        elif k == "model":
            v = "TEST-MODEL-1" if not _subcols(card, it) else {_subcols(card, it)[0]: "TEST-MODEL-1"}
        elif k in keys_set or k in req:
            v = cell(card, it, k, S)
        else:
            continue
        extra = {z["text"]: "TEST VALUE" for z in sls if z.get("std_key") in req and z.get("std_key") not in (blank_key if bad else None,)}
        if k == "model" and first_at_start:
            pass
        if extra and k != "tag":
            v = dict({"_": v} if isinstance(v, str) else v, **{t: x for t, x in extra.items() if t not in (v if isinstance(v, dict) else {})})
        if bad and k == blank_key:
            continue
        rows.setdefault(it["block"], {})[str(it["no"])] = v
        _ = rk
    return rows


def write_pdf(card, kind, tag, service, bad, blank_key, out, blank_form=None):
    import valve_make_test_ds as M
    doc = pymupdf.open(blank_form) if blank_form else M.synthetic(card)
    rows = build_sheet(card, kind, tag, service, bad, blank_key)
    for b, rv in rows.items():
        sub = dict(card, items=[i for i in card["items"] if i["block"] == b])
        M.fill(doc, sub, {"rows": rv, "title": {"doc_no": f"TEST-IN-DS-{card['form_id']}{'B' if bad else 'A'}", "rev": "A", "date": "12-Nov-2026"}})
    doc.save(out, garbage=3, deflate=True)


def write_pds(out, rows):
    """A ruled 'Process Data for Instruments' table (same layout rules as the real PDS reader expects)."""
    doc = pymupdf.open()
    pg = doc.new_page(width=1190, height=842)
    pg.insert_text((400, 30), "TEST DATA - NOT A REAL PROCESS DATA SHEET", fontsize=10, color=(0.85, 0.1, 0.1))
    pg.insert_text((540, 60), "Process Data for Instruments", fontsize=9)
    heads = [("Sr no.", ""), ("Tag Number", ""), ("PID No", ""), ("Line No", ""), ("Pipe Class", ""), ("Service Fluid", ""),
             ("Process Fluid Phase", ""), ("Flow Rate", "m3/h"), ("Operating Pressure", "bar(g)"), ("Design Pressure", "bar(g)"),
             ("Operating Temperature", "°C"), ("Design Temperature", "°C"), ("Density at T&P", "kg/m3")]
    xs = [20, 50, 130, 200, 300, 350, 420, 490, 560, 640, 720, 800, 880, 960]
    y1 = 150 + 14 * len(rows) + 10
    for x in xs:
        pg.draw_line((x, 70), (x, y1), width=0.5)
    for y in (70, 110, 125, 140, y1):
        pg.draw_line((20, y), (960, y), width=0.5)
    for (h, u), x0 in zip(heads, xs):
        words = h.split()
        half = (len(words) + 1) // 2
        pg.insert_text((x0 + 2, 85), " ".join(words[:half]), fontsize=5.5)
        if words[half:]:
            pg.insert_text((x0 + 2, 100), " ".join(words[half:]), fontsize=5.5)
        if u:
            pg.insert_text((x0 + 2, 120), u, fontsize=5.5)
    for n, r in enumerate(rows):
        vals = [str(n + 1), r["tag"], "TEST-PID-0001", LINE, "TC1A", "CO2", "Vapor", "120", r["op"], r["dp"], "45", r["dt"], "45.2"]
        for v, x0 in zip(vals, xs):
            pg.insert_text((x0 + 2, 160 + n * 14), v, fontsize=5.5)
    doc.save(out)


def write_linelist(out, south_swap=True):
    wb = openpyxl.Workbook()
    wb.active.title = "COVER SHT"
    ws = wb.create_sheet("TEST_LINE_LIST")
    ws["A1"] = "TEST DATA - NOT A REAL LINE LIST"
    hdr = ["LINE NUMBER", "REVISION", "SERVICE", "SERIAL NO.", "LINE SIZE", None, "PIPE CLASS", "P&ID NUMBER", "FROM", "TO",
           "FLUID PHASE", "FLUID DENSITY", "DESIGN CONDITIONS", None, None, "OPERATING CONDITIONS", None]
    sub = [None] * 12 + ["PRESSURE", "TEMPERATURE (MAX.)", "TEMPERATURE (MIN.)", "PRESSURE", "TEMPERATURE"]
    unit = [None] * 4 + ["MM", "INCH"] + [None] * 5 + ["KG / M3", "BARG", "DEG C", "DEG C", "BARG", "DEG C"]
    for c, v in enumerate(hdr, 1):
        ws.cell(7, c, v)
    for c, v in enumerate(sub, 1):
        ws.cell(8, c, v)
    for c, v in enumerate(unit, 1):
        ws.cell(9, c, v)
    data = [[LINE, "A", "TS", "1001", '6"' if south_swap else 150, 150 if south_swap else '6"', "TC1A", "TEST-PID-0001", "", "", "Vapor", 45.2, 3.5, 80, -20, 0.4, 45],
            ['TS1002-2"-TC2B-N', "A", "TS", "1002", 50, '2"', "TC2B", "TEST-PID-0002", "", "", "Liquid", 900, 45, 120, -29, 30, 60]]
    for r, row in enumerate(data, 10):
        for c, v in enumerate(row, 1):
            ws.cell(r, c, v)
    ws.cell(13, 1, "NOTES:")
    wb.save(out)


def write_pms(out):
    doc = pymupdf.open()
    for code, rating in (("TC1A", 300), ("TC2B", 600)):
        pg = doc.new_page(width=595, height=842)
        pg.insert_text((10, 20), "TEST DATA - NOT A REAL PMS", fontsize=9, color=(0.85, 0.1, 0.1))
        pg.insert_text((10, 40), "PIPING MATERIAL SPECIFICATION - TEST AREA", fontsize=8)
        pg.insert_textbox(pymupdf.Rect(10, 60, 400, 200), f"Class: {code}\nClass {rating}, TEST CS\nFlange Class: CLASS {rating}\n"
                          "Material: CARBON STEEL (TEST)\nValve Trim: TRIM 8 (TEST)", fontsize=7)
    doc.save(out)


def plan(cards, kinds, blank_forms):
    """Datasheets to write + what each tag B must raise."""
    items = []
    for n, (kind, fid) in enumerate(sorted(kinds.items())):
        card = cards[fid]
        has = {it.get("std_key") for it in card["items"] if it.get("std_key")}
        req = (card.get("required") or {}).get("keys", [])
        blank_key = next((k for k in ("manufacturer", "model", "pid_no", "service") if k in req and k in has), None)
        a, b = tags(kind, n)
        exp = set()
        if blank_key:
            exp.add(("IN-REQ-01", blank_key))
        if has & {"op_pressure", "upstream_pressure"}:
            exp.add(("IN-PDS-01", "op_pressure"))
        line_ok = True                                    # Line No from the form, else the PDS row of the tag
        if has & {"design_pressure"} or (fid in ("80", "310", "505")):
            if line_ok:
                exp.add(("IN-LL-02", "design_pressure"))
        if "piping_class" in has:                         # a form without the row takes the PDS class (consistent) — nothing planted
            exp.add(("IN-PMS-01", "piping_class"))
            exp.add(("IN-LL-01", "piping_class"))
        if has & {"design_temp"} or fid in ("80", "310", "505"):
            exp.add(("IN-LL-03", "design_temp"))
        if kind in ("pt", "pg", "dpg") and has & {"range", "range_adj_range", "calibration_range"}:
            exp.add(("IN-ITM-01", "range"))
        if kind == "psv":
            exp.add(("IN-ITM-02", "set_pressure"))
        items.append({"kind": kind, "fid": fid, "a": a, "b": b, "blank_key": blank_key, "expect_b": exp,
                      "blank_form": blank_forms.get(fid)})
    return items


def main(argv):
    work = Path(argv[0])
    forms = argv[argv.index("--forms") + 1] if "--forms" in argv else ""
    keep = "--keep" in argv
    work.mkdir(parents=True, exist_ok=True)
    data = work / "data"
    if data.exists():
        import shutil
        shutil.rmtree(data)
    os.environ["PID_DATA_DIR"] = str(data)
    from app.valve import instrument
    cards, kinds = instrument.cards(), instrument.kinds()
    blank = {fid: (glob.glob(f"{forms}/*{nm}*") or [None])[0] for fid, nm in NAMES.items()} if forms else {}
    P = plan(cards, kinds, blank)
    ds_files = []
    for p in P:
        card = cards[p["fid"]]
        for tag, bad in ((p["a"], False), (p["b"], True)):
            out = work / f"TEST_{p['fid']}_{tag.replace('-', '')}.pdf"
            write_pdf(card, p["kind"], tag, f"TEST SERVICE {p['kind'].upper()}", bad, p["blank_key"], out, p["blank_form"])
            ds_files.append(out)
    pds_rows = []
    for p in P:
        pds_rows.append({"tag": p["a"], "op": "10.5", "dp": "19.6", "dt": "85"})
        pds_rows.append({"tag": p["b"], "op": "30", "dp": "2.0", "dt": "60"})
    write_pds(work / "TEST_PDS.pdf", pds_rows)
    write_linelist(work / "TEST_LINE_LIST.xlsx")
    write_pms(work / "TEST_PMS.pdf")
    import valve_make_test_list as ML
    idx = [{"tag": p["a"], "service": f"TEST SERVICE {p['kind'].upper()}", "pid_no": "TEST-PID-0001", "manufacturer": "TEST MFR",
            "model": "TEST-MODEL-1", "datasheet_no": f"TEST-IN-DS-{p['fid']}A"} for p in P]
    idx += [{"tag": p["b"], "service": "TEST OTHER SERVICE", "pid_no": "TEST-PID-0001"} for p in P]
    no_service = {p["b"] for p in P if p["blank_key"] == "service"}            # nothing to compare when the datasheet left it blank
    idx += [{"tag": "71XX-9999", "service": "LIST ONLY TAG", "pid_no": "TEST-PID-0009"}]
    io_ = [{"tag": p["a"], "service": f"TEST SERVICE {p['kind'].upper()}", "pid_no": "TEST-PID-0001", "io_typical": "AI"} for p in P]
    io_ += [{"tag": "71XX-9999", "service": "LIST ONLY TAG", "pid_no": "TEST-PID-0009", "io_typical": "DI"}]
    for kind, recs, nm in (("instrument_index", idx, "TEST_INSTRUMENT_INDEX.pdf"), ("io_list", io_, "TEST_IO_LIST.pdf")):
        pages = [recs[i:i + 9] for i in range(0, len(recs), 9)]
        doc = pymupdf.open()
        for chunk in pages:
            d1 = ML.synthetic(kind)
            ML.fill(d1, kind, chunk)
            doc.insert_pdf(d1)
        doc.save(work / nm)
    # ── through the real API ───────────────────────────────────────────────────────────────────────
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    pid = c.post("/api/valve/projects", json={"name": "TEST INSTRUMENT"}).json()["id"]

    def up(kind, files):
        r = c.post(f"/api/valve/projects/{pid}/upload", data={"kind": kind},
                   files=[("files", (f.name, f.read_bytes())) for f in files]).json()
        for _ in range(600):
            j = c.get(f"/api/valve/jobs/{r['id']}").json()
            if j["status"] == "done":
                return j
            time.sleep(0.1)
        raise RuntimeError("job did not finish")
    t0 = time.time()
    errs = []
    for kind, files in (("process", [work / "TEST_PDS.pdf"]), ("pms", [work / "TEST_PMS.pdf"]), ("linelist", [work / "TEST_LINE_LIST.xlsx"]),
                        ("instlist", [work / "TEST_INSTRUMENT_INDEX.pdf", work / "TEST_IO_LIST.pdf"]), ("instrument", ds_files)):
        j = up(kind, files)
        errs += j.get("errors", [])
    t_up = time.time() - t0
    summ = c.get(f"/api/valve/projects/{pid}/inst/summary").json()
    sheets = c.get(f"/api/valve/projects/{pid}/inst/sheets").json()["rows"]
    by_tag = {s["tag"]: s for s in sheets}
    lc = c.get(f"/api/valve/projects/{pid}/inst/listcmp").json()
    report, tot = [], {"expected": 0, "found": 0, "missed": 0, "extra": 0}
    for p in P:
        line = {"form": p["fid"], "kind": p["kind"], "read": [], "missed": [], "extra": [], "a_issues": None, "b_found": []}
        for tag, bad in ((p["a"], False), (p["b"], True)):
            s = by_tag.get(tag.replace("-", "")) or by_tag.get(tag) or next((x for x in sheets if instrument.tag_key(x["tag"]) == instrument.tag_key(tag)), None)
            if not s:
                line["missed"].append(f"{tag}: 읽히지 않음")
                continue
            d = c.get(f"/api/valve/inst/sheets/{s['id']}").json()
            got = {(r["rule"], r["key"]) for r in d["review"] if r["result"] in ("Mismatch", "Missing", "Review Required")}
            if not bad:
                line["a_issues"] = len(got)
                line["extra"] += [f"A {g[0]} {g[1]}: " + next(r["reason"] for r in d["review"] if (r["rule"], r["key"]) == g) for g in sorted(got)]
            else:
                exp = p["expect_b"]
                line["b_found"] = sorted(f"{a}" for a, _ in got & exp)
                line["missed"] += [f"B {a} {k}" for a, k in sorted(exp - got)]
                line["extra"] += [f"B {g[0]} {g[1]}: " + next(r["reason"] for r in d["review"] if (r["rule"], r["key"]) == g) for g in sorted(got - exp)]
                tot["expected"] += len(exp)
                tot["found"] += len(got & exp)
        tot["missed"] += len(line["missed"])
        tot["extra"] += len(line["extra"])
        report.append(line)
    want_list = {("Instrument Index", "LIST-01", p["b"]) for p in P if p["b"] not in no_service} | {("IO List", "LIST-00", p["b"]) for p in P} | \
                {("Instrument Index", "LIST-02", "71XX-9999"), ("IO List", "LIST-02", "71XX-9999")}
    got_list = {(x["list"], x["rule"], x["tag"]) for x in lc["rows"] if x["result"] != "OK"}
    norm = lambda S: {(a, b, instrument.tag_key(t)) for a, b, t in S}   # noqa: E731
    out = {"upload_s": round(t_up, 1), "errors": errs, "total": tot, "forms": report,
           "list": {"expected": len(want_list), "found": len(norm(want_list) & norm(got_list)),
                    "missed": sorted(norm(want_list) - norm(got_list)), "extra": sorted(norm(got_list) - norm(want_list))},
           "summary_total": summ["total"], "pid": pid}
    (work / "scenario.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("upload_s", "total", "list", "summary_total")}, ensure_ascii=False, default=str))
    for ln in report:
        print(ln["form"], ln["kind"], "A_issues", ln["a_issues"], "B_found", ln["b_found"], "missed", ln["missed"], "extra", ln["extra"][:3])
    if not keep:
        import shutil
        shutil.rmtree(data, ignore_errors=True)
    return out


if __name__ == "__main__":
    main(sys.argv[1:])
