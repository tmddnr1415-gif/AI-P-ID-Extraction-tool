"""Revision lifecycle — what happens when Rev B / C / D of a tag arrives after Rev A was reviewed (valve26).

The new revision is read and reviewed by the same rules automatically (every datasheet is).  What the engineer
would otherwise redo by hand is carried over here, deterministically:

  · an issue the reviewer DISMISSED in Rev A stays dismissed in Rev B when the same issue is raised on the same
    field and that field did not change (the objection still holds: nothing to re-decide);
  · an issue CONFIRMED (sent to the contractor) in Rev A that is raised again in Rev B on an unchanged field is
    "not addressed" — it stays Confirmed, is marked `since` Rev A and its one-line comment says so;
  · an issue that is no longer raised in Rev B counts as RESOLVED by the revision; one not raised in Rev A is NEW;
  · a reviewer's text comment on a field is copied to the new revision when that field did not change (anchored to
    the field's new position); free-hand mark-ups are not copied — they belong to the old page.
  · 'Resolved' states are not carried: if the issue comes back, it is open again.

Only contractor-facing issue types take part in the counts (not Extraction Review · Revision Change · reviewer rows).
"""
from __future__ import annotations

COUNTED = {"Data Missing", "Open Item", "Data Error", "PMS Non-Compliance", "PMS Review", "Process Mismatch",
           "Material Review", "Valve Review"}


def _field_of(ikey: str) -> str:
    """'Data Missing:design_temp.nor' -> 'design_temp' (the compare row key); 'Material Review:seat_material.MR-01' -> 'seat_material'."""
    key = ikey.split(":", 1)[1] if ":" in ikey else ikey
    if key.startswith("note."):
        return key
    base = key.split(".")[0]
    return base


def changed_keys(cmp_rows: list[dict]) -> set[str]:
    """Field / note keys whose value differs between the two revisions (material-equivalent spellings are unchanged)."""
    out = set()
    for r in cmp_rows or []:
        if r.get("change") != "Unchanged":
            out.add(r["key"])
            out.add(r["key"].split(".")[0] if not r["key"].startswith("note.") else r["key"])
    return out


def carry_states(prev_states: dict, cmp_rows: list[dict], new_ikeys: set[str], prev_rev: str) -> list[dict]:
    """-> [{ikey, status, note, since}] to store on the new revision."""
    chg = changed_keys(cmp_rows)
    out = []
    for ikey, st in (prev_states or {}).items():
        status = (st or {}).get("status")
        if status not in ("Dismissed", "Confirmed") or ikey not in new_ikeys:
            continue
        if _field_of(ikey) in chg:
            continue                                         # the field changed: the reviewer decides again
        note = (st.get("note") or "").strip()
        keep = {k: st.get(k) for k in ("decision", "reason_cat", "conclusion", "modified_text", "modified_severity", "rule_ver", "modified_expected") if st.get(k)}
        if status == "Dismissed":                            # valve29: the engineer decision and its reason category travel too
            out.append({"ikey": ikey, "status": "Dismissed", "since": prev_rev, **keep,
                        "note": f"Carried from Rev {prev_rev}" + (f": {note}" if note else "")})
        else:
            out.append({"ikey": ikey, "status": "Confirmed", "since": prev_rev, **keep,
                        "note": f"Confirmed in Rev {prev_rev} — not addressed in this revision" + (f" ({note})" if note else "")})
    return out


def rev_review(prev_issues: list[dict], new_issues: list[dict], prev_states: dict, cmp_rows: list[dict], prev_rev: str) -> dict:
    """Counts an engineer wants on opening Rev B: resolved · still open (confirmed before, unchanged) · new · changed fields."""
    chg = changed_keys(cmp_rows)
    p_all = {i["ikey"] for i in prev_issues or [] if i.get("type") in COUNTED}
    p = {k for k in p_all if (prev_states.get(k) or {}).get("status") != "Dismissed"}      # a dismissed one was never 'open'
    n = {i["ikey"]: i for i in new_issues or [] if i.get("type") in COUNTED}
    resolved = sorted(p - set(n))
    new = sorted(set(n) - p_all)
    still = sorted(k for k in p & set(n) if (prev_states.get(k) or {}).get("status") == "Confirmed" and _field_of(k) not in chg)
    return {"prev_rev": prev_rev, "resolved": len(resolved), "new": len(new), "still_open": len(still),
            "changed_fields": sum(1 for r in cmp_rows or [] if r.get("change") != "Unchanged"),
            "still": still, "resolved_keys": resolved, "new_keys": new}


def carry_comments(prev_comments: list[dict], cmp_rows: list[dict], new_fields: dict) -> list[dict]:
    """Text comments anchored to an unchanged field -> same comment on the new revision at the field's new place."""
    chg = changed_keys(cmp_rows)
    out = []
    for c in prev_comments or []:
        fk = c.get("field_key")
        if not fk or c.get("deleted") or c.get("kind") not in (None, "", "rect", "note", "text"):
            continue
        if fk.split(".")[0] in chg or fk not in new_fields:
            continue
        f = new_fields[fk]
        out.append({"field_key": fk, "text": c.get("text") or "", "by": c.get("by"), "category": c.get("category") or "comment",
                    "page": f.get("page"), "bbox": f.get("bbox") if c.get("bbox") else None, "kind": c.get("kind") if c.get("bbox") else None})
    return out
