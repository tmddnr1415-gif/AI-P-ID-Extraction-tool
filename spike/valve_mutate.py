"""Real-data mutation replay — change ONE thing on a real datasheet and demand that ONLY the right findings move.

    python3 spike/valve_mutate.py [--pickle /tmp/ds_cache.pkl] [--pms /tmp/ext/pms_now.json] [--pd /tmp/ext/pd/Process_Data.pdf]
                                  [--only seat_peek,esdv_fail_open] [--show 5]

For every real datasheet (extraction cache (res, dss)) the review runs as the tool does (matreview · expert · tagrules ·
issues · requirements · pms · process) → the BASELINE finding set.  Then each mutation an engineer would recognise
(seat RTFE→PEEK, design temperature +80 °C, body 316→WCB, RF↔RTJ, 150#→300#, 2"→10" floating, ESDV fail open, HOLD in a
field, a required field blanked, tag prefix 99, the tag duplicated into another document, the fugitive-emission general
note removed, an elastomer seal …) is applied alone and the DELTA (added · removed findings) is compared with what the
mutation is allowed to move and what it must add.  Anything else that moved is an unexpected delta = a defect candidate.
"""
from __future__ import annotations

import argparse
import collections
import copy
import json
import pickle
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.valve import expert, issues, location, matreview, pms as pmsmod, process, requirements, tagrules  # noqa: E402

SKIP_ISSUE_TYPES = {"Material Review", "Valve Review", "Extraction Review"}       # duplicates of the R findings / internal


# ----------------------------------------------------------------------------- context (learned once from all datasheets)
def load(pickle_path: str, pms_path: str, pd_path: str | None):
    res, dss = pickle.load(open(pickle_path, "rb"))
    P = json.load(open(pms_path)) if pms_path and Path(pms_path).exists() else None
    PD = process.read_process_data(pd_path) if pd_path and Path(pd_path).exists() else None
    return res, dss, P, PD


def tag_item(d: dict, res: dict) -> dict:
    F = d["fields"]
    v = lambda k: (F.get(k) or {}).get("value") or ""                        # noqa: E731
    title = location.title_for(d["doc_no"], res["docs"])
    L = location.locate(d["doc_no"], title, v("pid_no"), d["tag_key"], " ".join(n["text"] for n in d["notes"]))
    return {"tag_raw": v("tag") or d["tag_key"], "tag_key": d["tag_key"], "area": L["area"], "site": L["site"], "unit": L["unit"],
            "system": L["system"], "pid_no": v("pid_no"), "doc_no": d["doc_no"], "valve_type": d.get("valve_type", ""),
            "fail": v("fail_position"), "page": (F.get("tag") or {}).get("page"), "bbox": (F.get("tag") or {}).get("bbox"), "_loc": L}


def context(res, dss):
    peers = expert.build_peers([{"tag": d["tag_key"], "fields": {k: (v.get("value") or "") for k, v in d["fields"].items()}} for d in dss])
    items = [tag_item(d, res) for d in dss]
    return {"peers": peers, "items": items, "tagprof": tagrules.learn(items)}


# ----------------------------------------------------------------------------- one review → a set of findings
def findings(d: dict, res: dict, P, PD, ctx: dict, me: dict | None = None, tagprof=None) -> set:
    doc = res["docs"].get(d["doc_no"], {})
    F = d["fields"]
    area = pmsmod.area_of_title(doc.get("title", ""))
    c, _ = pmsmod.find_class(P, (F.get("piping_class") or {}).get("value") or "", (F.get("line_no") or {}).get("value") or "", area) if P else (None, "")
    ds = {"fields": [dict(v, key=k, edited_value=None) for k, v in F.items()], "notes": d["notes"], "tag_key": d["tag_key"],
          "pages": d.get("pages") or [1], "sheets": d.get("sheets", []), "doc_no": d["doc_no"], "comments": [],
          "process_ref": d.get("process_ref"), "location": (me or tag_item(d, res))["_loc"]}
    gn = doc.get("general_notes", {})
    pr = process.check(ds, PD) if PD else None
    row = ((PD or {}).get("by_tag") or {}).get(d["tag_key"])
    reqs = requirements.find(ds, gn)
    R = matreview.review(ds, gn, c, pr, row, reqs) + expert.review(ds, gn, c, pr, row, reqs, ctx["peers"]) \
        + tagrules.check(me or tag_item(d, res), tagprof or ctx["tagprof"])
    out = set()
    for m in R:
        assert len(m["short"]) <= 120, (m["rule"], m["short"])
        out.add(("R", m["rule"], m["level"], m["key"]))
    Fd = {f["key"]: f for f in ds["fields"]}
    prow = pmsmod.check(Fd, P, area, ds["notes"]) if P else None
    for i in issues.compute(ds, gn, P, area, None, None, pms_rows=prow, process_rows=pr, material_rows=R):
        if i["type"] not in SKIP_ISSUE_TYPES:
            out.add(("I", i["type"], i["key"]))
    for r in reqs:
        out.add(("Q", r["key"]))
    for r in prow or []:
        out.add(("P", r["item"], r["result"]))
    return out


# ----------------------------------------------------------------------------- mutations
def _v(d, k):
    return (d["fields"].get(k) or {}).get("value") or ""


def _set(d, k, v):
    if k in d["fields"]:
        d["fields"][k]["value"] = v


def _cls_of(d, res, P):
    doc = res["docs"].get(d["doc_no"], {})
    F = d["fields"]
    c, _ = pmsmod.find_class(P, _v(d, "piping_class"), _v(d, "line_no"), pmsmod.area_of_title(doc.get("title", ""))) if P else (None, "")
    return c


def _item_fits(d, res, P):
    c = _cls_of(d, res, P)
    if not c:
        return None, None
    best, _, _ = pmsmod.select_item(c, lambda k: _v(d, k))
    return c, best


def _soft_limit(seat: str):
    for pat, name, lim in matreview.SEAT_LIMITS:
        if pat.search(seat):
            return lim
    return None


def _dt(d, PD):
    row = ((PD or {}).get("by_tag") or {}).get(d["tag_key"]) or {}
    v = (row.get("values") or {}).get("design_temp") or {}
    m = re.search(r"-?\d+(?:\.\d+)?", str(v.get("v") or ""))
    return float(m.group(0)) if m else None


# each mutation: name -> fn(d, res, P, PD, ctx) -> None (skip) | dict(ds=mutated, allowed=set of keys, must=set of keys, extra=...)
#   allowed / must keys: "R:<rule>" (any key) · "R:<rule>:<field>" · "I:<type>" · "I:<type>:<key>" · "Q:<key>" · "P:<item>"
def m_seat_peek(d, res, P, PD, ctx):
    seat = _v(d, "seat_material")
    if not re.search(r"R-?P?TFE|RPTFE|PTFE", seat, re.I):
        return None
    m = copy.deepcopy(d); _set(m, "seat_material", "PEEK")
    c, best = _item_fits(d, res, P)
    must = set()
    if best and best[2]["seat"] and "RTFE" in best[2]["seat"].upper():
        must.add("I:PMS Non-Compliance:seat_material")
    dt = _dt(d, PD)
    if dt is not None and dt > 230 and dt <= 260:
        must.add("-R:MR-01")                                                   # the 230 °C limit no longer applies
    return {"ds": m, "allowed": {"R:MR-01", "R:MR-02", "R:MR-13", "R:VR-14", "R:PC-01:seat_material", "P:Seat Material", "I:PMS Non-Compliance:seat_material",
                                 "I:PMS Review:seat_material"}, "must": must}


def m_seat_metal(d, res, P, PD, ctx):
    seat = _v(d, "seat_material")
    if not re.search(r"R-?P?TFE|RPTFE|PTFE|PEEK", seat, re.I):
        return None
    m = copy.deepcopy(d); _set(m, "seat_material", "Metal seated (TCC)")
    must = set()
    for r in ("MR-01", "MR-02", "MR-13", "VR-14"):
        must.add(f"-R:{r}")                                                    # metal seat: soft-seat rules must go
    c, best = _item_fits(d, res, P)
    if best and best[2]["seat"]:
        must.add("I:PMS Non-Compliance:seat_material")
    return {"ds": m, "allowed": {"R:MR-01", "R:MR-02", "R:MR-13", "R:VR-14", "R:VR-07", "R:PC-01:seat_material", "P:Seat Material",
                                 "I:PMS Non-Compliance:seat_material", "I:PMS Review:seat_material"}, "must": must}


def m_design_temp(d, res, P, PD, ctx):
    dt = _dt(d, PD)
    if dt is None:
        return None
    PD2 = copy.deepcopy(PD)
    PD2["by_tag"][d["tag_key"]]["values"]["design_temp"]["v"] = f"{dt + 80:.2f}"
    lim = _soft_limit(_v(d, "seat_material"))
    must = set()
    if lim and dt <= lim < dt + 80 and not _v(d, "seat_material").strip().lower().startswith("note"):
        must.add("R:MR-01|R:MR-02")                                            # one of the two seat-temperature rules
    c = _cls_of(d, res, P)
    if c and c.get("pt") and len(c["pt"]) >= 2 and dt + 80 > max(t for t, _ in c["pt"]) >= dt:
        must.add("R:MR-03")
    return {"ds": copy.deepcopy(d), "PD": PD2, "allowed": {"R:MR-01", "R:MR-02", "R:MR-03", "R:MR-07", "I:Process Mismatch:design_temp",
                                                           "I:Process Mismatch", "I:Data Missing"}, "must": must}


def m_body_wcb(d, res, P, PD, ctx):
    body = _v(d, "body_material")
    if "316" not in body:
        return None
    m = copy.deepcopy(d); _set(m, "body_material", "CS A216-WCB")
    c, best = _item_fits(d, res, P)
    must = set()
    if best and "316" in best[2]["body"]:
        must.add("I:PMS Non-Compliance:body_material")
    cnt = ctx["peers"]["groups"].get(("body_material", _v(d, "piping_class").upper()))
    if cnt and sum(cnt.values()) - 1 >= expert.PEER_MIN:
        must.add("R:PC-01:body_material")
    return {"ds": m, "allowed": {"R:MR-04", "R:MR-05", "R:MR-06", "R:MR-07", "R:MR-10", "R:MR-15", "R:PC-01:body_material", "P:Body Material",
                                 "I:PMS Non-Compliance:body_material", "I:PMS Review:body_material"}, "must": must}


def m_conn_swap(d, res, P, PD, ctx):
    conn = _v(d, "connections")
    if not re.search(r"\bRF\b|RTJ", conn):
        return None
    new = re.sub(r"\bRF\b", "RTJ", conn) if re.search(r"\bRF\b", conn) else re.sub(r"RTJ", "RF", conn)
    m = copy.deepcopy(d); _set(m, "connections", new)
    c = _cls_of(d, res, P)
    must = set()
    if c and c.get("facing"):
        must.add("~R:VR-01")                                                   # must toggle
    return {"ds": m, "allowed": {"R:VR-01", "R:PC-01:connections"}, "must": must}


def m_rating_300(d, res, P, PD, ctx):
    if not _v(d, "rating").startswith("150"):
        return None
    m = copy.deepcopy(d); _set(m, "rating", "300#")
    c = _cls_of(d, res, P)
    must = {"I:PMS Non-Compliance:rating"} if c and c.get("rating") == 150 else set()
    cnt = ctx["peers"]["groups"].get(("rating", _v(d, "piping_class").upper()))
    if cnt and sum(cnt.values()) - 1 >= expert.PEER_MIN:
        must.add("R:PC-01:rating")
    return {"ds": m, "allowed": {"R:VR-03", "R:PC-01:rating", "P:Pressure Class", "I:PMS Non-Compliance:rating", "I:PMS Review:rating"}, "must": must}


def m_size_floating(d, res, P, PD, ctx):
    if not re.match(r'\s*2\s*(?:"|in)', _v(d, "body_size")):
        return None
    m = copy.deepcopy(d); _set(m, "body_size", '10"'); _set(m, "body_type", "Ball (Full Bore) - Floating")
    _set(m, "trim_construction", "Floating Ball"); _set(m, "trim_type", "Ball (Full Bore)")        # MOV form says it in other rows
    rating = re.search(r"\d+", _v(d, "rating") or "")
    must = {"R:VR-03"} if rating else set()
    return {"ds": m, "allowed": {"R:VR-03", "R:VR-04", "R:VR-13", "R:VR-10", "R:VR-08", "R:VR-09", "R:PC-01:body_type", "P:Bore", "P:Ball Valve Item",
                                 "P:Body Material", "P:Seat Material", "P:Fire Safe", "P:Trim (Ball) Material", "P:Stem Material", "P:Pressure Class",
                                 "I:PMS Review", "I:PMS Non-Compliance", "I:Data Error:line_size_inlet"}, "must": must}


def m_esdv_fail_open(d, res, P, PD, ctx):
    if not re.search(r"ESDV|SDV", d["tag_key"]) or not _v(d, "fail_position").upper().startswith("CLOSE"):
        return None
    m = copy.deepcopy(d); _set(m, "fail_position", "Open")
    must = {"R:TG-05"}
    if "CLOSE" in _v(d, "air_failure").upper():
        must.add("I:Data Error:air_failure")
    row = ((PD or {}).get("by_tag") or {}).get(d["tag_key"]) or {}
    if ((row.get("values") or {}).get("fail_position") or {}).get("v", "").upper().startswith("FC"):
        must.add("I:Process Mismatch:fail_position")
    me = dict(tag_item(d, res), fail="Open")
    return {"ds": m, "me": me, "allowed": {"R:TG-05", "R:VR-05", "R:VR-06", "I:Data Error:air_failure", "I:Process Mismatch:fail_position"}, "must": must}


def m_hold(d, res, P, PD, ctx):
    if "area_class" not in d["fields"]:
        return None
    m = copy.deepcopy(d); _set(m, "area_class", "HOLD")
    return {"ds": m, "allowed": {"I:Open Item:area_class", "I:Data Missing:area_class"}, "must": {"I:Open Item:area_class"}}


def m_blank_rating(d, res, P, PD, ctx):
    if not _v(d, "rating").strip():
        return None
    m = copy.deepcopy(d); _set(m, "rating", "")
    return {"ds": m, "allowed": {"I:Data Missing:rating", "R:VR-03", "R:PC-01:rating", "P:Pressure Class", "I:PMS Review:rating", "I:PMS Non-Compliance:rating"},
            "must": {"I:Data Missing:rating"}}


def m_tag_prefix(d, res, P, PD, ctx):
    me = tag_item(d, res)
    p = tagrules.parse(me["tag_raw"])
    if not p:
        return None
    new_raw = me["tag_raw"].replace(p["prefix"], "99", 1)
    me2 = dict(me, tag_raw=new_raw)
    m = copy.deepcopy(d); _set(m, "tag", new_raw)
    g = next((g for g in ctx["tagprof"]["groups"] if (g["area"], g["site"], g["unit"]) == (me["area"], me["site"], me["unit"])), None)
    must = {"R:TG-02"} if g and g["learned_from"] >= tagrules.MIN_N and g["prefix_source"] and p["prefix"].lstrip("0") != "99" else set()
    return {"ds": m, "me": me2, "allowed": {"R:TG-02", "I:Data Error:tag.1"}, "must": must}     # sheet 2 repeats the old tag → Data Error is right


def m_dup_tag(d, res, P, PD, ctx):
    me = tag_item(d, res)
    items = ctx["items"] + [dict(me, doc_no="999-98-IN-DTS-09999")]
    return {"ds": copy.deepcopy(d), "me": me, "tagprof": tagrules.learn(items), "allowed": {"R:TG-04"}, "must": {"R:TG-04"}}


def m_remove_fugitive_gn(d, res, P, PD, ctx):
    doc = res["docs"].get(d["doc_no"], {})
    gn = doc.get("general_notes", {})
    hits = [k for k, t in gn.items() if re.search(r"fugitive|ISO\s*15848", t, re.I)]
    if not hits:
        return None
    res2 = {"docs": dict(res["docs"])}                                       # keep the note numbers (rows refer to them): neutral text
    res2["docs"][d["doc_no"]] = dict(doc, general_notes={k: ("Packing shall be suitable for the service." if k in hits else t) for k, t in gn.items()})
    other = any(re.search(r"fugitive|ISO\s*15848", n["text"], re.I) for n in d["notes"]) or \
        any(re.search(r"fugitive|ISO\s*15848", (f.get("value") or "") + (f.get("display") or ""), re.I) for f in d["fields"].values())
    return {"ds": copy.deepcopy(d), "res": res2, "allowed": {"Q:fugitive", "Q:tightness", "Q:coating", "Q:hardness"}, "must": set() if other else {"-Q:fugitive"}}


def m_elastomer_seal(d, res, P, PD, ctx):
    if "seal_material" not in d["fields"]:
        return None
    m = copy.deepcopy(d); _set(m, "seal_material", "FKM O-ring")
    row = ((PD or {}).get("by_tag") or {}).get(d["tag_key"]) or {}
    fluid = ((row.get("values") or {}).get("fluid") or {}).get("v") or _v(d, "fluid") or ""
    co2 = bool(re.search(r"\bCO\s*2\b|CARBON\s+DIOXIDE", fluid + " " + _v(d, "service"), re.I))
    must = {"R:MR-12:Confirm"} if co2 else set()
    cnt = ctx["peers"]["groups"].get(("seal_material", _v(d, "piping_class").upper()))
    if cnt and sum(cnt.values()) - 1 >= expert.PEER_MIN:
        must.add("R:PC-01:seal_material")
    return {"ds": m, "allowed": {"R:MR-12", "R:PC-01:seal_material"}, "must": must}


MUTATIONS = {
    "seat_peek": m_seat_peek, "seat_metal": m_seat_metal, "design_temp_+80": m_design_temp, "body_wcb": m_body_wcb,
    "conn_rf_rtj": m_conn_swap, "rating_300": m_rating_300, "size_10_floating": m_size_floating, "esdv_fail_open": m_esdv_fail_open,
    "hold_field": m_hold, "blank_rating": m_blank_rating, "tag_prefix_99": m_tag_prefix, "dup_tag": m_dup_tag,
    "remove_fugitive_gn": m_remove_fugitive_gn, "elastomer_seal": m_elastomer_seal,
}


# ----------------------------------------------------------------------------- scoring
def _keys(f: tuple) -> set:
    """All the allow-keys a finding tuple answers to."""
    if f[0] == "R":
        return {f"R:{f[1]}", f"R:{f[1]}:{f[3]}", f"R:{f[1]}:{f[2]}"}
    if f[0] == "I":
        return {f"I:{f[1]}", f"I:{f[1]}:{f[2]}"}
    if f[0] == "Q":
        return {f"Q:{f[1]}"}
    if f[0] == "P":
        return {f"P:{f[1]}"}
    return {str(f)}


def judge(base: set, mut: set, allowed: set, must: set) -> list[str]:
    added, removed = mut - base, base - mut
    problems = []
    for f in sorted(added):
        if not (_keys(f) & allowed):
            problems.append(f"unexpected +{f}")
    for f in sorted(removed):
        if not (_keys(f) & allowed):
            problems.append(f"unexpected -{f}")
    for m in must:
        if m.startswith("~"):                                                  # must toggle (present in exactly one side)
            k = m[1:]
            if any(k in _keys(f) for f in added) == any(k in _keys(f) for f in removed):
                problems.append(f"expected toggle {k}")
        elif m.startswith("-"):
            k = m[1:]
            if any(k in _keys(f) for f in mut):
                problems.append(f"expected gone {k}")
        else:
            alts = m.split("|")
            if not any(any(k in _keys(f) for f in added) for k in alts):
                if not any(any(k in _keys(f) for f in base) for k in alts):   # already there before = not a defect of the delta
                    problems.append(f"expected +{m}")
    return problems


def replay(res, dss, P, PD, only: list[str] | None = None, show: int = 5, quiet: bool = False) -> dict:
    ctx = context(res, dss)
    base = {d["tag_key"]: findings(d, res, P, PD, ctx) for d in dss}
    stats = collections.OrderedDict()
    examples = collections.defaultdict(list)
    for name, fn in MUTATIONS.items():
        if only and name not in only:
            continue
        n = ok = 0
        for d in dss:
            m = fn(d, res, P, PD, ctx)
            if m is None:
                continue
            n += 1
            try:
                got = findings(m["ds"], m.get("res", res), P, m.get("PD", PD), ctx, m.get("me"), m.get("tagprof"))
                probs = judge(base[d["tag_key"]], got, m["allowed"], m["must"])
            except Exception as e:  # noqa: BLE001
                probs = [f"CRASH {type(e).__name__}: {str(e)[:100]}"]
            if probs:
                examples[name].append((d["tag_key"], probs[:4]))
            else:
                ok += 1
        stats[name] = (n, ok)
    if not quiet:
        tot_n = sum(n for n, _ in stats.values()); tot_ok = sum(k for _, k in stats.values())
        print(f"mutation replay · datasheets {len(dss)} · cases {tot_n} · pass {tot_ok} ({tot_ok / max(1, tot_n):.1%})")
        for name, (n, ok) in stats.items():
            print(f"  {name:20} {ok:4}/{n:<4} {ok / max(1, n):6.1%}")
            for tag, probs in examples[name][:show]:
                print(f"      {tag}: {'; '.join(probs)}")
    return {"stats": dict(stats), "examples": dict(examples)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pickle", default="/tmp/ds_cache.pkl")
    ap.add_argument("--pms", default="/tmp/ext/pms_now.json")
    ap.add_argument("--pd", default="/tmp/ext/pd/Process_Data.pdf")
    ap.add_argument("--only", default="")
    ap.add_argument("--show", type=int, default=5)
    a = ap.parse_args()
    res, dss, P, PD = load(a.pickle, a.pms, a.pd)
    replay(res, dss, P, PD, [x for x in a.only.split(",") if x], a.show)
