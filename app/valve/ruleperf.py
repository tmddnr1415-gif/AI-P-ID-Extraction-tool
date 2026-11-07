"""Rule performance — how engineers judged each rule's findings (valve29, directive §1.3).

Statistics only.  Nothing here feeds back into a rule: the judging modules (issues · matreview · expert · pms · process ·
tagrules · checks) never import this module or read the decision log (tests/test_valve.py guards it).

Wording: the dismissal rate is NOT called a false-positive rate.  An engineer dismisses for many reasons (project
exception, vendor clarification, duplicate …); only the categories 'Incorrect Rule Logic' and 'Incorrect Data
Extraction' point at the tool, and they are counted separately as `tool_cause`.
"""
from __future__ import annotations

import collections
import datetime as dt

from app.valve import checks

CONFIRM_LIKE = {"Confirmed", "Modified"}          # + status Resolved (the vendor fixed it: the finding was right)
DISMISS_LIKE = {"Dismissed", "Not Applicable"}
TOOL_CAUSE = {"Incorrect Rule Logic", "Incorrect Data Extraction"}
DEFAULTS = {"rp_min_n": 10, "rp_dismiss_rate": 0.30}     # tool defaults for the 'review this rule' flag — shown, editable


def _month(at: str) -> str:
    return (at or "")[:7]


def performance(findings: list[dict], log: list[dict], settings: dict | None = None, today: dt.date | None = None) -> dict:
    """findings: current findings of the newest revisions (each with check · decision · status · reason_cat).
    log: decision_log rows of the project.  -> {"rules": [...], "settings": {...}, "months": [...]}"""
    cfg = dict(DEFAULTS, **{k: v for k, v in (settings or {}).items() if v not in (None, "")})
    min_n, rate = int(cfg["rp_min_n"]), float(cfg["rp_dismiss_rate"])
    today = today or dt.date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(3):
        months.insert(0, f"{y:04d}-{m:02d}")
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    by = collections.defaultdict(lambda: {"total": 0, "Confirmed": 0, "Modified": 0, "Dismissed": 0, "Deferred": 0,
                                          "Not Applicable": 0, "Resolved": 0, "undecided": 0, "reasons": collections.Counter()})
    for f in findings:
        rid = checks.rule_of(f.get("check") or "")
        if not rid or f.get("comment_id"):
            continue
        b = by[rid]
        b["total"] += 1
        d = f.get("decision") or ""
        if f.get("status") == "Resolved" and d not in DISMISS_LIKE:
            b["Resolved"] += 1
        elif d in b:
            b[d] += 1
        else:
            b["undecided"] += 1
        if f.get("reason_cat") and (d in DISMISS_LIKE or d == "Modified"):
            b["reasons"][f["reason_cat"]] += 1
    trend = collections.defaultdict(lambda: {mm: collections.Counter() for mm in months})
    for r in log:
        mm = _month(r.get("at"))
        if mm in months and r.get("rule"):
            trend[r["rule"]][mm][r.get("decision") or r.get("status") or "?"] += 1
    rows = []
    for cid, title, group, _need in checks.REGISTRY:
        b = by.get(cid)
        if not b and cid not in trend:
            rows.append({"rule": cid, "title": title, "group": group, "version": checks.RULE_VERSION[cid],
                         "source": checks.RULE_SOURCE[cid]["kind"], "total": 0, "decided": 0})
            continue
        b = b or by[cid]
        conf = b["Confirmed"] + b["Modified"] + b["Resolved"]
        dis = b["Dismissed"] + b["Not Applicable"]
        decided = conf + dis                                   # Deferred is not a verdict on the rule
        tool = sum(n for k, n in b["reasons"].items() if k in TOOL_CAUSE)
        rows.append({"rule": cid, "title": title, "group": group, "version": checks.RULE_VERSION[cid],
                     "source": checks.RULE_SOURCE[cid]["kind"], "total": b["total"],
                     "confirmed": b["Confirmed"], "modified": b["Modified"], "resolved": b["Resolved"], "dismissed": b["Dismissed"],
                     "not_applicable": b["Not Applicable"], "deferred": b["Deferred"], "undecided": b["undecided"], "decided": decided,
                     "confirmation_rate": round(conf / decided, 3) if decided else None,
                     "dismissal_rate": round(dis / decided, 3) if decided else None,
                     "tool_cause": tool, "reasons": dict(b["reasons"].most_common()),
                     "trend": {mm: dict(trend[cid][mm]) for mm in months} if cid in trend else {},
                     "review_suggested": bool(decided >= min_n and dis / decided >= rate) if decided else False})
    rows.sort(key=lambda r: (not r.get("review_suggested"), -(r.get("dismissal_rate") or 0), -r["total"]))
    return {"rules": rows, "months": months, "settings": {"rp_min_n": min_n, "rp_dismiss_rate": rate,
                                                           "defaults": DEFAULTS}}


# ── rule change procedure (directive §1.4) — a record, never an automatic change ──────────────────────────────────
STEPS = ["current_logic", "proposed_logic", "reason", "regression", "simulation"]
STATUSES = ["Proposed", "Tested", "Approved", "Applied", "Rejected"]


def next_status(row: dict, want: str) -> tuple[str | None, str]:
    """Validate a status move.  -> (new status or None, why not)."""
    if want not in STATUSES:
        return None, "unknown status"
    if want == "Rejected":
        return want, ""
    if want == "Proposed":
        return (want, "") if all(row.get(k) for k in ("current_logic", "proposed_logic", "reason")) else \
            (None, "기존 규칙 · 변경안 · 변경 이유를 모두 적어야 합니다")
    if want == "Tested":
        return (want, "") if row.get("regression") and row.get("simulation") else \
            (None, "실자료 Regression 결과와 Simulation 결과를 모두 적어야 합니다")
    if want == "Approved":
        if row.get("status") != "Tested":
            return None, "Regression · Simulation 을 마친(Tested) 변경만 승인할 수 있습니다"
        return want, ""
    if want == "Applied":
        if row.get("status") != "Approved":
            return None, "승인된 변경만 적용 표시할 수 있습니다"
        if checks.RULE_VERSION.get(row.get("rule"), "") != (row.get("to_ver") or ""):
            return None, f"코드의 규칙 버전이 아직 {checks.RULE_VERSION.get(row.get('rule'), '?')} 입니다 — 개발 쪽이 버전을 올린 뒤 적용 표시"
        return want, ""
    return None, "?"
