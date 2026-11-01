"""Verification report — the engine's own account of what it checked on a datasheet (valve28).

An engineer trusts a finding list only when the tool also says what it looked at and what it could NOT judge.
For every datasheet the registry below is walked and each check gets one of
    fail   — one or more findings (not dismissed) carry this check id
    pass   — the check ran on real inputs and found nothing
    n/a    — the check could not be evaluated (no PMS uploaded · class not in PMS · tag not in Process Data ·
             first revision · no design temperature anywhere …) — with the reason, never a silent pass
Findings keep their ids (issues.py `check`, matreview / expert / tagrules rule codes), so the two views agree by construction.
"""
from __future__ import annotations

# (id, title, group, needs) — needs: ds · pms · class · process · pd_row · prev · temp · peers
REGISTRY = [
    ("DM-01", "Required fields filled", "Datasheet", "ds"),
    ("DM-02", "PROCESS DATA block complete", "Datasheet", "ds"),
    ("OI-01", "No HOLD / TBC in a field", "Datasheet", "ds"),
    ("OI-02", "No HOLD / TBC in the notes", "Datasheet", "ds"),
    ("DE-01", "Line No. class = Piping class", "Datasheet", "ds"),
    ("DE-02", "Line No. size = Line Size", "Datasheet", "ds"),
    ("DE-03", "Operating ≤ design (pressure · temperature)", "Datasheet", "ds"),
    ("DE-04", "Fail position = action on air failure", "Datasheet", "ds"),
    ("DE-05", "One Document No. on every sheet", "Datasheet", "ds"),
    ("DE-06", "Header rows identical on every sheet", "Datasheet", "ds"),
    ("DE-07", "Referenced General Notes exist", "Datasheet", "ds"),
    ("DE-08", "Referenced Notes exist", "Datasheet", "ds"),
    ("DE-09", "Note reference points at the right note", "Datasheet", "ds"),
    ("PMS", "Piping class items: rating · body · trim · seat · fire-safe · NACE", "PMS", "class"),
    ("PD", "Process values = Process Data", "Process", "pd_row"),
    ("MR-01", "Seat vs PMS temperature limit", "Material", "temp+class"),
    ("MR-02", "Seat vs its service temperature", "Material", "temp"),
    ("MR-03", "Design P/T inside PMS class table", "Material", "temp+class"),
    ("MR-04", "Carbon steel body in a low-temperature line", "Material", "ds"),
    ("MR-05", "Body vs pipe material family", "Material", "ds"),
    ("MR-07", "316/316L in sour service (ISO 15156-3)", "Material", "ds"),
    ("MR-09", "Hard-facing type stated", "Material", "ds"),
    ("MR-10", "Dual-grade 316/316L where PMS requires", "Material", "class"),
    ("MR-11", "Bolting in sour / NACE service", "Material", "ds"),
    ("MR-13", "Fire-safe soft-seated valve", "Material", "ds"),
    ("MR-14", "Service fluid in PMS class service list", "Material", "class"),
    ("MR-15", "Carbon steel body in sour service", "Material", "ds"),
    ("VR-01", "Flange facing = PMS class", "Design", "class"),
    ("VR-02", "Flange standard vs size (B16.5 / B16.47)", "Design", "ds"),
    ("VR-03", "Floating ball size limit for the class", "Design", "ds"),
    ("VR-04", "Ball type = PMS item", "Design", "class"),
    ("VR-05", "Fail-safe position vs spring", "Design", "ds"),
    ("VR-06", "SIL valve: fail action · partial stroke test", "Design", "ds"),
    ("VR-07", "Leakage rate vs seat / tightness", "Design", "ds"),
    ("VR-09", "Fire-safe stated where service / PMS asks", "Design", "ds"),
    ("VR-10", "Seat configuration / cavity relief (trunnion)", "Design", "ds"),
    ("VR-11", "Extended stem on cold-insulated valve", "Design", "ds"),
    ("VR-12", "Full bore on a piggable line", "Design", "ds"),
    ("VR-13", "Valve size vs line size", "Design", "ds"),
    ("VR-14", "Seat type in erosive service", "Design", "ds"),
    ("VR-15", "Actuator sizing factor", "Design", "ds"),
    ("AC-01", "Limit switch where the General Notes forbid it", "Accessory", "ds"),
    ("AC-02", "Position transmitter where the General Notes require it", "Accessory", "ds"),
    ("AC-03", "Position transmitter SIL rating on a SIL valve", "Accessory", "ds"),
    ("AC-04", "Positioner make = the one the General Notes name", "Accessory", "ds"),
    ("AC-05", "Redundant solenoid valves: voting stated", "Accessory", "ds"),
    ("PC-01", "Same piping class → same values across datasheets", "Peer", "peers"),
    ("TG-01", "Tag structure (prefix + function + number)", "Tag", "ds"),
    ("TG-02", "Tag prefix = system / unit", "Tag", "tags"),
    ("TG-03", "Loop number pattern of the Area / Unit", "Tag", "tags"),
    ("TG-04", "One tag per valve (no duplicate)", "Tag", "tags"),
    ("TG-05", "Function code vs fail action", "Tag", "ds"),
    ("REV-01", "Changes vs previous revision", "Revision", "prev"),
]
GROUPS = ["Datasheet", "PMS", "Process", "Material", "Design", "Peer", "Tag", "Revision"]
TITLE = {c[0]: c[1] for c in REGISTRY}

# valve29 — rule version and source.  Every rule starts at version 1 (= the logic shipped in valve28).  A rule changes
# only through the rule-change procedure (proposal → comparison → reason → regression → simulation → engineer approval);
# the developer then bumps the version here and RULE_CHANGELOG.md records it.  The rule code never reads the
# decision log or the rule-change table (tests/test_valve.py guards this).
RULE_VERSION = {c[0]: "1" for c in REGISTRY}
# No project specification document is linked yet, so every rule is a General Engineering Check — never shown as a
# project-approved criterion (directive §5.3).  Project documents (Phase 2) will set {doc, rev, page, clause}.
GENERAL = "General Engineering Check"
RULE_SOURCE = {c[0]: {"kind": GENERAL, "doc": "", "rev": "", "page": "", "clause": ""} for c in REGISTRY}

# How each rule compares (source traceability): operator · tolerance.  Only what the rule code already does.
OPS = {"DM-01": ("present", ""), "DM-02": ("present", ""), "OI-01": ("released (no HOLD/TBC)", ""), "OI-02": ("released (no HOLD/TBC)", ""),
       "DE-01": ("=", ""), "DE-02": ("=", ""), "DE-03": ("≤", ""), "DE-04": ("=", ""), "DE-05": ("=", ""), "DE-06": ("=", ""),
       "DE-07": ("exists", ""), "DE-08": ("exists", ""), "DE-09": ("points at", ""),
       "PMS": ("≡ (material / spec equivalence)", ""), "PD": ("= (numbers)", "1 %"), "REV-01": ("=", ""),
       "MR-01": ("≤ (seat limit)", ""), "MR-02": ("≤ (seat limit)", ""), "MR-03": ("inside P-T table", "")}


def rule_of(check: str) -> str:
    """Finding check id -> registry rule id ('PMS-trim' -> 'PMS', 'PD-design_pressure' -> 'PD')."""
    c = check or ""
    return "PMS" if c.startswith("PMS-") else "PD" if c.startswith("PD-") else c


def _na_reason(need: str, ctx: dict) -> str | None:
    """Why a check could not run, or None when it could."""
    for n in need.split("+"):
        if n == "class":
            if not ctx.get("has_pms"):
                return "PMS not uploaded"
            if not ctx.get("pms_class"):
                return f"Piping class '{ctx.get('piping_class') or '—'}' not found in PMS"
        elif n == "pd_row":
            if not ctx.get("has_process"):
                return "Process Data not uploaded"
            if not ctx.get("pd_row"):
                return "Tag not in Process Data"
        elif n == "temp":
            if ctx.get("design_temp") is None:
                return "No design temperature (datasheet · Process Data)"
        elif n == "prev":
            if not ctx.get("has_prev"):
                return "First revision"
        elif n == "peers":
            if not ctx.get("has_peers"):
                return "No other datasheet with this piping class"
        elif n == "tags":
            if not ctx.get("has_tagrules"):
                return "Fewer than 3 tags in this Area / Unit"
    return None


def report(issues: list[dict], ctx: dict) -> dict:
    """-> {"checks": [{id, title, group, status, reason, findings}], "summary": {"pass", "fail", "na", "total"}}"""
    hits: dict[str, int] = {}
    for i in issues or []:
        c = i.get("check") or ""
        if not c or i.get("status") == "Dismissed":
            continue
        cid = rule_of(c)
        hits[cid] = hits.get(cid, 0) + 1
    out = []
    for cid, title, group, need in REGISTRY:
        n = hits.get(cid, 0)
        if n:
            out.append({"id": cid, "title": title, "group": group, "status": "fail", "reason": "", "findings": n})
            continue
        why = _na_reason(need, ctx)
        out.append({"id": cid, "title": title, "group": group, "status": "n/a" if why else "pass", "reason": why or "", "findings": 0})
    s = {"pass": sum(1 for c in out if c["status"] == "pass"), "fail": sum(1 for c in out if c["status"] == "fail"),
         "na": sum(1 for c in out if c["status"] == "n/a")}
    s["total"] = len(out)
    return {"checks": out, "summary": s}
