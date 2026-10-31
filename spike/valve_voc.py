"""Score the Valve tool against reviewers' feedback (P&ID hotfix82 'VOC → 재학습 경로', borrowed).

    python3 spike/valve_voc.py <valve_feedback_*.json> [--ds Datasheet.pdf ...] [--out /tmp/valve_voc]

The feedback file comes from Reports & Export › Review Feedback (`/api/valve/projects/{pid}/feedback.json`):
  verdicts     issue Confirmed / Resolved (= the rule was right) or Dismissed (= false alarm), with the reviewer's note
  corrections  a field the reviewer corrected (read value → corrected value)
  missed       a mark-up in category error / missing — something the rules did not raise

Prints (and writes report.md — it holds client values, keep it out of the repository):
  A. rule precision per issue type and per (type, field)        — from the verdicts as they were given
  B. reading errors per field                                   — from the corrections
  C. replay with the CURRENT code (only with --ds, the same PDFs): corrections now read right / still wrong / other,
     misses now raised by a rule near the same place (PMS checks are not replayed — no PMS here)

The rule code (app/valve/*) never reads this file — tests/test_valve.py checks that no judging module mentions it.
A reference axis, not a gate: a reviewer can be wrong, and one project's verdicts are not every project's.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _overlap(a, b, pad=6.0):
    if not a or not b:
        return False
    return not (a[2] + pad < b[0] or b[2] + pad < a[0] or a[3] + pad < b[1] or b[3] + pad < a[1])


def score(fb: dict) -> tuple[list[str], dict]:
    rep, out = [f"# Valve feedback — {fb.get('project')} · {fb.get('generated')} · by {fb.get('by')}", "",
                f"datasheets {fb['datasheets']} · issues raised {fb['issues_raised']} · verdicts {len(fb['verdicts'])} · "
                f"corrections {len(fb['corrections'])} · missed {len(fb['missed'])}", "", "## A. Rule precision (verdicts)", ""], {}
    by_type, by_rule = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for v in fb["verdicts"]:
        ok = "right" if v["verdict"] in ("Confirmed", "Resolved") else "false" if v["verdict"] == "Dismissed" else "other"
        by_type[v["type"]][ok] += 1
        by_rule[(v["type"], v["key"])][ok] += 1
    rep += ["| issue type | right | false alarm | precision |", "|---|---|---|---|"]
    for t, c in sorted(by_type.items()):
        n = c["right"] + c["false"]
        rep.append(f"| {t} | {c['right']} | {c['false']} | {100 * c['right'] / n:.0f}% |" if n else f"| {t} | 0 | 0 | — |")
    worst = sorted(((c["false"], t, k) for (t, k), c in by_rule.items() if c["false"]), reverse=True)[:20]
    rep += ["", "### most dismissed (type · field)"] + [f"- {t} · {k}: {n}" for n, t, k in worst]
    notes = collections.Counter(v["note"].strip() for v in fb["verdicts"] if v["verdict"] == "Dismissed" and v.get("note"))
    rep += ["", "### reviewers' reasons for dismissing"] + [f"- {n} × {k}" for k, n in notes.most_common(15)]
    out["precision"] = {t: dict(c) for t, c in by_type.items()}
    corr = collections.Counter(c["key"] for c in fb["corrections"])
    rep += ["", "## B. Reading errors (corrections)", ""] + [f"- {k}: {n}" for k, n in corr.most_common(30)]
    out["corrections"] = dict(corr)
    out["missed"] = dict(collections.Counter(m["category"] for m in fb["missed"]))
    return rep, out


def replay(fb: dict, pdfs: list[str]) -> tuple[list[str], dict]:
    from app.valve import extract, issues, schema
    cur, gns = {}, {}
    for p in pdfs:
        res = extract.read_pdf(p)
        for d in extract.group_datasheets(res):
            cur[(d["tag_key"], d["rev"])] = d
            gns[d["doc_no"]] = res["docs"].get(d["doc_no"], {}).get("general_notes", {})
    rep, st = ["", "## C. Replay with the current code", ""], collections.Counter()
    for c in fb["corrections"]:
        d = cur.get((c["tag"], c["rev"]))
        if not d:
            st["correction: datasheet not in the given PDFs"] += 1
            continue
        now = (d["fields"].get(c["key"]) or {}).get("value") or ""
        if schema.norm_tag(now) == schema.norm_tag(c["corrected"]):
            st["correction: now read right"] += 1
        elif now == (c["read"] or ""):
            st["correction: still read as before"] += 1
        else:
            st["correction: read differently, still not the correction"] += 1
    for m in fb["missed"]:
        d = cur.get((m["tag"], m["rev"]))
        if not d:
            st["missed: datasheet not in the given PDFs"] += 1
            continue
        ds = dict(d, fields=[dict(f, key=k, edited_value=None) for k, f in d["fields"].items()], comments=[])
        hit = any(i["page"] == m["page"] and _overlap(i.get("bbox"), m["bbox"]) and i["color"] == m["category"]
                  for i in issues.compute(ds, gns.get(d["doc_no"])))
        st["missed: now raised by a rule" if hit else "missed: still not raised"] += 1
    rep += [f"- {k}: {n}" for k, n in sorted(st.items())]
    return rep, dict(st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feedback")
    ap.add_argument("--ds", nargs="*", default=[])
    ap.add_argument("--out", default="/tmp/valve_voc")
    a = ap.parse_args()
    fb = json.loads(Path(a.feedback).read_text(encoding="utf-8"))
    if fb.get("kind") != "valve-feedback":
        sys.exit("not a valve feedback file")
    rep, out = score(fb)
    if a.ds:
        r2, o2 = replay(fb, a.ds)
        rep += r2
        out["replay"] = o2
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / "report.md").write_text("\n".join(rep) + "\n", encoding="utf-8")
    print("\n".join(rep[:60]))
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
