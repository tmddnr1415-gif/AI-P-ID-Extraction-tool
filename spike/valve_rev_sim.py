#!/usr/bin/env python3
"""Revision simulation — Rev A reviewed by an engineer, then Rev B / C arrives (valve26).

    python3 spike/valve_rev_sim.py [--n 500] [--seed 1] [--chain 2]

For every case a synthetic datasheet (the valve22 PDF generator) is read as Rev A and reviewed by the rules; the
'engineer' dismisses / confirms some issues.  The 'designer' then issues Rev B with 1–4 edits — fills a blank process
value, changes a material / size / rating, blanks a value, re-spells a material the same way (no real change), edits a
note — and the chain may go on to Rev C.  Both PDFs go through the real reader, compare, issues and
app.valve.revisions.  The oracle is what the engineer expects:

  · compare: exactly the edited fields change (equivalent spellings count as unchanged);
  · carry:   a Dismissed / Confirmed decision follows to the next revision iff that field did not change and the
             same issue is raised again; a Resolved one never does;
  · counts:  filling a blank that was 'Data Missing' resolves it; a Confirmed issue on an unchanged field is
             'still open'; an issue first raised in Rev B is 'new'.
Every disagreement is listed by edit type so a wrong rule shows up as a pattern, not a number.
"""
from __future__ import annotations

import argparse
import collections
import copy
import random
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import valve_sim_pdf as G  # noqa: E402
from app.valve import extract, issues, material, revisions  # noqa: E402
from app.valve.api import compare  # noqa: E402

EDITS = {
    "fill_blank": ["op_pressure", "design_pressure", "op_temp", "design_temp", "fluid", "fluid_state", "max_dp_closed"],
    "change_value": ["body_size", "rating", "seat_material", "body_material", "piping_class", "fail_position", "line_no", "nace"],
    "blank_value": ["op_pressure", "design_temp", "fluid", "body_material"],
    "respell_same": {"ball_material": ["316 SS / HF", "SS 316/HF"], "stem_material": ["316 SS/HF", "SS316 / HF"],
                     "body_material": ["316/316L SS A351-CF8M/CF3M", "A351 CF8M/CF3M 316/316L SS"]},
}
STABLE = ["baseline", "font_large", "extra_blank_rows", "note_style_dash", "unit_appended", "sheet2_continuation"]


def _ds(res):
    dss = extract.group_datasheets(res)
    if not dss:
        return None
    d = dss[0]
    return {"fields": [dict(v, key=k, edited_value=None) for k, v in d["fields"].items()], "notes": d["notes"], "tag_key": d["tag_key"],
            "pages": d["pages"], "sheets": d.get("sheets"), "comments": [], "rev": d["rev"], "doc_no": d["doc_no"],
            "general_notes": res["docs"].get(d["doc_no"], {}).get("general_notes", {})}


def _read(spec):
    data, _ = G.make_pdf(spec)
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
        fh.write(data)
        path = fh.name
    try:
        return _ds(extract.read_pdf(path))
    finally:
        Path(path).unlink(missing_ok=True)


def _edit(rng, spec, k):
    """-> (new spec, [(edit type, key, old, new)])"""
    s = copy.deepcopy(spec)
    log = []
    kinds = rng.sample(list(EDITS), min(k, len(EDITS)))
    touched = set()
    for kind in kinds:
        if kind == "respell_same":
            key = rng.choice(list(EDITS[kind]))
            a, b = EDITS[kind][key]
            if s["fields"].get(key) == a and key not in touched:
                s["fields"][key] = b
                touched.add(key)
                log.append((kind, key, a, b))
            continue
        pool = [x for x in EDITS[kind] if x not in touched]
        if not pool:
            continue
        key = rng.choice(pool)
        touched.add(key)
        old = s["fields"].get(key, "")
        if kind == "fill_blank":
            if old.strip():
                continue
            new = rng.choice([v for v in G.VALUES[key] if v.strip()])
        elif kind == "blank_value":
            if not old.strip():
                continue
            new = ""
        else:
            opts = [v for v in G.VALUES[key] if v != old and not (old and material.same(old, v))]
            if not opts:
                continue
            new = rng.choice(opts)
        s["fields"][key] = new
        log.append((kind, key, old, new))
    return s, log


def _issues(ds, states=None, prev=None):
    return issues.compute(ds, ds["general_notes"], None, "", prev, states or {})


def one(rng, chain):
    spec = G._spec(rng, rng.choice(STABLE))
    spec["rev"] = "A"
    ds = _read(spec)
    if ds is None:
        return [{"edit": "-", "check": "read_A", "ok": False, "why": "no datasheet read"}]
    out = []
    states = {}
    prev_issues = _issues(ds)
    counted = [i for i in prev_issues if i["type"] in revisions.COUNTED]
    for i in counted:                                   # the engineer's Rev A review
        r = rng.random()
        if r < 0.3:
            states[i["ikey"]] = {"status": "Dismissed", "note": "ok"}
        elif r < 0.55:
            states[i["ikey"]] = {"status": "Confirmed", "note": ""}
        elif r < 0.6:
            states[i["ikey"]] = {"status": "Resolved", "note": ""}
    rev = "A"
    for step in range(chain):
        nspec, log = _edit(rng, spec, rng.randint(1, 4))
        nspec["rev"] = chr(ord(rev) + 1)
        nds = _read(nspec)
        if nds is None:
            out.append({"edit": "-", "check": "read_B", "ok": False, "why": "no datasheet read"})
            break
        cmp_rows = compare(ds, nds)
        chg = revisions.changed_keys(cmp_rows)
        edited = {key for kind, key, _, _ in log if kind != "respell_same"}
        same = {key for kind, key, _, _ in log if kind == "respell_same"}
        # ① compare = exactly the edits (extraction can shift blank/'Not Found' rows: keys that read blank both times are ignored)
        for kind, key, old, new in log:
            want = kind != "respell_same"
            got = key in chg
            if want != got:
                rows = [(r["key"], r["previous"], r["new"], r["change"]) for r in cmp_rows if r["key"].split(".")[0] == key]
                out.append({"edit": kind, "check": "compare", "ok": False,
                            "why": f"[{spec['variation']}] {key}: '{old}' -> '{new}' read as {'changed' if got else 'unchanged'} {rows}"})
            else:
                out.append({"edit": kind, "check": "compare", "ok": True})
        extra = {k.split(".")[0] for k in chg if not k.startswith("note.")} - edited - same
        out.append({"edit": "none", "check": "compare_no_extra", "ok": not extra, "why": f"unedited fields read as changed: {sorted(extra)[:4]}" if extra else ""})
        # ② carry
        new_raw = _issues(nds, prev=cmp_rows)
        new_ikeys = {i["ikey"] for i in new_raw}
        carried = {c["ikey"]: c["status"] for c in revisions.carry_states(states, cmp_rows, new_ikeys, rev)}
        for ikey, st in states.items():
            f = revisions._field_of(ikey)
            want = st["status"] if st["status"] in ("Dismissed", "Confirmed") and ikey in new_ikeys and f not in edited and f not in chg else None
            got = carried.get(ikey)
            out.append({"edit": "carry_" + st["status"].lower(), "check": "carry", "ok": want == got,
                        "why": "" if want == got else f"{ikey}: expected {want}, got {got} (edited={f in edited})"})
        # ③ counts
        new_states = {k: {"status": v, "note": ""} for k, v in carried.items()}
        new_issues = _issues(nds, new_states, cmp_rows)
        rr = revisions.rev_review(prev_issues, new_issues, states, cmp_rows, rev)
        filled = [key for kind, key, _, _ in log if kind == "fill_blank"]
        for key in filled:
            had = [i["ikey"] for i in counted if i["type"] == "Data Missing" and i["key"].split(".")[0] == key
                   and states.get(i["ikey"], {}).get("status") != "Dismissed"]
            ok = all(k in rr["resolved_keys"] for k in had)
            out.append({"edit": "fill_blank", "check": "resolved", "ok": ok, "why": "" if ok else f"{key} filled but still raised: {had}"})
        still_ok = all(states.get(k, {}).get("status") == "Confirmed" and revisions._field_of(k) not in chg for k in rr["still"])
        out.append({"edit": "none", "check": "still_open_rule", "ok": still_ok, "why": "" if still_ok else str(rr["still"][:3])})
        new_ok = all(k not in {i["ikey"] for i in prev_issues} for k in rr["new_keys"]) and \
            not any(k in rr["new_keys"] for k, st in states.items() if st["status"] == "Dismissed" and k in new_ikeys and revisions._field_of(k) not in chg)
        out.append({"edit": "none", "check": "new_rule", "ok": new_ok})
        # next link of the chain: Rev B becomes the reviewed one (carried states + a few fresh decisions)
        spec, ds, rev, prev_issues = nspec, nds, nspec["rev"], new_issues
        states = {k: dict(v) for k, v in new_states.items()}
        for i in [x for x in new_issues if x["type"] in revisions.COUNTED and x["ikey"] not in states]:
            if rng.random() < 0.3:
                states[i["ikey"]] = {"status": rng.choice(["Dismissed", "Confirmed"]), "note": ""}
    return out


def run(n, seed, chain):
    rng = random.Random(seed)
    agg = collections.defaultdict(lambda: [0, 0])
    bad = collections.defaultdict(list)
    exc = 0
    for i in range(n):
        try:
            res = one(rng, chain)
        except Exception as e:                            # noqa: BLE001
            exc += 1
            bad["exception"].append(repr(e)[:200])
            continue
        for r in res:
            k = (r["edit"], r["check"])
            agg[k][0] += r["ok"]
            agg[k][1] += 1
            if not r["ok"] and len(bad[k]) < 4:
                bad[k].append(r.get("why", ""))
    return agg, bad, exc


def report(agg, bad, exc, n):
    lines = [f"revision simulation: {n} cases · exceptions {exc}", f"{'edit':18} {'check':18} {'ok':>6} {'n':>6}  rate"]
    tot_ok = tot_n = 0
    for (e, c), (ok, nn) in sorted(agg.items()):
        tot_ok += ok
        tot_n += nn
        lines.append(f"{e:18} {c:18} {ok:6} {nn:6}  {ok / nn:.3f}")
    lines.append(f"TOTAL {tot_ok}/{tot_n} = {tot_ok / max(1, tot_n):.4f}")
    for k, v in bad.items():
        if v:
            lines.append(f"  e.g. {k}: " + " | ".join(x for x in v if x)[:400])
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--chain", type=int, default=2)
    a = ap.parse_args()
    agg, bad, exc = run(a.n, a.seed, a.chain)
    print(report(agg, bad, exc, a.n))
