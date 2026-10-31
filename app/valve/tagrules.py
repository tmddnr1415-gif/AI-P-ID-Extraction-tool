"""Tag numbering — learned per Area / Unit from the project's own tags, then each tag checked against it.

No tag-numbering procedure document is needed (none was supplied with the CO2 PJT files): the tool reads every tag
of the uploaded datasheets and learns, per (Area, Unit):
  · the structure   prefix + function code + separator + number + suffix    '98' 'ESDV' ' ' '980002' ''
  · where the prefix comes from    = Unit · = SYSTEM in the title · = system in the P&ID / Doc. No.  (whichever holds)
  · the number      length, fixed leading digits ('98' + 4 digits), suffix letters (A/B for parallel valves)
  · the separator   none / space / '-' as printed on the datasheets
  · the series      leading digits of the loop number ↔ the P&ID sheets they appear on
Then a tag that breaks its group's learned rule is flagged (TG rules), and the function code is checked against the
valve's fail action (general practice: ESDV/SDV fail-close, BDV fail-open — the project spec governs).
When a project tagging procedure is uploaded later, its rules replace nothing here automatically: the reviewer compares.
"""
from __future__ import annotations

import collections
import re

from app.valve import knowledge

_P = re.compile(r"^\s*(\d+)\s*([A-Z]{2,6})\s*([-–]?)\s*(\d+)\s*([A-Z]?)\s*$")
FUNC = {  # function code → (meaning, usual fail action) — ISA-5.1 style letters, project tagging spec governs
    "ESDV": ("Emergency shutdown valve", "CLOSE"), "SDV": ("Shutdown valve", "CLOSE"), "BDV": ("Blowdown valve", "OPEN"),
    "XV": ("On/off (automated block) valve", ""), "MOV": ("Motor-operated valve", ""), "HV": ("Hand-operated valve", ""),
    "PV": ("Pressure control valve", ""), "FV": ("Flow control valve", ""), "LV": ("Level control valve", ""), "TV": ("Temperature control valve", ""),
}
MIN_N, SHARE = 3, 0.8


def parse(raw: str) -> dict | None:
    m = _P.match(str(raw or "").upper())
    if not m:
        return None
    pre, fn, dash, num, suf = m.groups()
    sep = "-" if dash else (" " if re.search(r"[A-Z]\s+\d", str(raw).upper()) else "")
    return {"prefix": pre, "func": fn, "sep": sep, "number": num, "suffix": suf}


def _sources(it: dict) -> dict:
    """Document values the prefix may come from."""
    pid = it.get("pid_no") or ""
    m = re.match(r"^\s*(\d+)-(\d+)-", pid)
    d = re.match(r"^\s*(\d+)-(\d+)-", it.get("doc_no") or "")
    return {"Unit": it.get("unit") or "", "System (title)": it.get("system") or "",
            "System (P&ID No.)": m.group(1) if m else "", "System (Doc. No.)": d.group(1) if d else ""}


def learn(items: list[dict]) -> dict:
    """items: [{tag_raw, tag_key, area, site, unit, system, pid_no, doc_no, valve_type, fail}] (one per datasheet, all revisions
    allowed — duplicates are counted once per tag).  -> {"groups": [...], "docs_by_tag": {...}}"""
    groups: dict[tuple, dict] = {}
    docs_by_tag = collections.defaultdict(set)
    seen = set()
    for it in items:
        docs_by_tag[it["tag_key"]].add(it.get("doc_no") or "")
        if it["tag_key"] in seen:
            continue
        seen.add(it["tag_key"])
        p = parse(it.get("tag_raw") or it["tag_key"])
        key = (it.get("area") or "", it.get("site") or "", it.get("unit") or "")      # Brownfield North U84 ≠ Brownfield South U84
        g = groups.setdefault(key, {"area": key[0], "site": key[1], "unit": key[2], "items": []})
        g["items"].append((it, p))
    out = []
    for (area, site, unit), g in sorted(groups.items()):
        ok = [(it, p) for it, p in g["items"] if p]
        n = len(ok)
        rule = {"area": area, "unit": unit, "site": site, "n": len(g["items"]), "unparsed": len(g["items"]) - n,
                "functions": collections.Counter(p["func"] for _, p in ok).most_common(), "examples": [it["tag_raw"] for it, _ in ok[:4]]}
        # prefix source: the document value the prefix equals in (nearly) every tag of the group
        src_hits = collections.Counter()
        for it, p in ok:
            for k, v in _sources(it).items():
                if v and v.lstrip("0") == p["prefix"].lstrip("0") or (v and v == p["prefix"]):
                    src_hits[k] += 1
        best = [k for k, c in src_hits.most_common() if n and c / n >= SHARE]
        rule["prefix_source"] = best[0] if best else ""
        rule["prefixes"] = collections.Counter(p["prefix"] for _, p in ok).most_common()
        lens = collections.Counter(len(p["number"]) for _, p in ok)
        L, lc = lens.most_common(1)[0] if lens else (0, 0)
        rule["number_len"] = L if n and lc / n >= SHARE else None
        lead = ""
        if rule["number_len"]:
            nums = [p["number"] for _, p in ok if len(p["number"]) == L]
            for k in range(1, max(1, L - 2)):             # always leave ≥ 3 loop digits free (few tags must not over-fit)
                c = collections.Counter(x[:k] for x in nums).most_common(1)[0]
                if c[1] / len(nums) >= SHARE and len(nums) >= MIN_N:
                    lead = c[0]
                else:
                    break
        rule["number_lead"] = lead
        seps = collections.Counter(p["sep"] for _, p in ok)
        rule["sep"] = seps.most_common(1)[0][0] if seps else ""
        rule["suffixes"] = sorted({p["suffix"] for _, p in ok if p["suffix"]})
        # series: the digits after the fixed lead that change with the P&ID sheet
        ser = collections.defaultdict(set)
        if rule["number_len"]:
            k = len(lead) + (2 if L - len(lead) >= 4 else 1)
            for it, p in ok:
                if len(p["number"]) == L:
                    ser[p["number"][len(lead):k]].add((it.get("pid_no") or "").strip())
        rule["series"] = {s: sorted(x for x in v if x)[:6] for s, v in sorted(ser.items())}
        pre_txt = {"Unit": "Unit", "System (title)": "System (title)", "System (P&ID No.)": "System (P&ID)", "System (Doc. No.)": "System (Doc. No.)"}
        rule["format"] = (f"[{pre_txt.get(rule['prefix_source'], 'prefix')}={'/'.join(x for x, _ in rule['prefixes'][:3])}]"
                          f"[{'/'.join(f for f, _ in rule['functions'][:5])}]"
                          + {"": "", " ": "␣", "-": "-"}[rule["sep"]]
                          + (f"{lead}{'n' * (L - len(lead))}" if rule["number_len"] else "n…")
                          + (f"[{'/'.join(rule['suffixes'])}]" if rule["suffixes"] else ""))
        rule["learned_from"] = n
        out.append(rule)
    return {"groups": out, "docs_by_tag": {k: sorted(v) for k, v in docs_by_tag.items()}}


def check(it: dict, prof: dict | None) -> list[dict]:
    """Findings (same shape as expert.review) for one datasheet's tag."""
    from app.valve.matreview import ACTION, CONFIRM, NOTE, SEVERITY
    out = []
    kb = knowledge.get("tag.numbering")

    def add(rule, level, title, short, comment, ev):
        out.append({"rule": rule, "level": level, "severity": SEVERITY[level], "title": title, "key": "tag", "short": short,
                    "comment": comment, "basis": "Tag numbering learned from this project's datasheets (per Area / Unit)",
                    "kb": "tag.numbering", "kb_title": kb["title"], "kb_text": kb["text"], "evidence": ev})
    ev = [{"doc": "Datasheet", "where": "Tag No.", "page": it.get("page"), "bbox": it.get("bbox"), "text": it.get("tag_raw", "")}]
    p = parse(it.get("tag_raw") or it.get("tag_key"))
    if not p:
        add("TG-01", CONFIRM, "Tag does not follow the tag structure", f"Tag '{it.get('tag_raw')}' does not follow prefix + function + number. Confirm.",
            "The tag cannot be split into prefix (system/unit) + function code + loop number (+ suffix) like the other tags.", ev)
        return out
    # function code vs fail action
    f = FUNC.get(p["func"])
    fail = (it.get("fail") or "").upper()
    if f and f[1] and fail:
        if f[1] == "CLOSE" and re.match(r"\s*(OPEN|FO\b|FAIL\s*OPEN)", fail):
            add("TG-05", CONFIRM, f"{p['func']} with fail-open action", f"{p['func']} tag with fail position '{it.get('fail')}'. Confirm tag or fail action.",
                f"{f[0]} ({p['func']}) normally fails closed; this datasheet says '{it.get('fail')}'. Either the tag function or the fail position is wrong.", ev)
        if f[1] == "OPEN" and re.match(r"\s*(CLOSE|FC\b|FAIL\s*CLOSE)", fail):
            add("TG-05", CONFIRM, f"{p['func']} with fail-close action", f"{p['func']} tag with fail position '{it.get('fail')}'. Confirm tag or fail action.",
                f"{f[0]} ({p['func']}) normally fails open (depressurises on ESD); this datasheet says '{it.get('fail')}'.", ev)
    if not prof:
        return out
    docs = prof["docs_by_tag"].get(it["tag_key"], [])
    if len([d for d in docs if d]) > 1:
        add("TG-04", ACTION, "Same tag in two datasheet documents", f"Tag also in {', '.join(d for d in docs if d != it.get('doc_no'))}. One tag per valve — correct.",
            f"The tag {it['tag_key']} appears in documents {', '.join(docs)}: two valves must not share a tag (or the same valve is specified twice).", ev)
    g = next((g for g in prof["groups"] if (g["area"], g["site"], g["unit"]) == (it.get("area") or "", it.get("site") or "", it.get("unit") or "")), None)
    if not g or g["learned_from"] < MIN_N:
        return out
    src = _sources(it).get(g["prefix_source"]) if g["prefix_source"] else None
    if src and src.lstrip("0") != p["prefix"].lstrip("0"):
        add("TG-02", CONFIRM, "Tag prefix differs from its system / unit", f"Tag prefix {p['prefix']} vs {g['prefix_source']} {src}. Confirm tag.",
            f"In {g['area']} Unit {g['unit']} the tag prefix is the {g['prefix_source']} ({g['learned_from']} tags); here it is {p['prefix']} "
            f"while the {g['prefix_source']} is {src}.", ev)
    L, lead = g["number_len"], g["number_lead"]
    if L and (len(p["number"]) != L or (lead and not p["number"].startswith(lead))):
        add("TG-03", CONFIRM, "Loop number differs from the Area / Unit pattern", f"Number {p['number']} vs pattern {lead}{'n' * (L - len(lead))} ({g['area']} Unit {g['unit']}). Confirm.",
            f"Tags of {g['area']} Unit {g['unit']} use {L}-digit numbers" + (f" starting '{lead}'" if lead else "")
            + f" ({g['format']}); this tag's number is {p['number']}.", ev)
    return out

