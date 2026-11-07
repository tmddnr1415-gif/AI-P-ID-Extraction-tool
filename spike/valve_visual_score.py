"""Score a visual check (spike/valve_visual_pack.py packs + reviewers' pNNN.json verdicts).

    python3 spike/valve_visual_score.py /tmp/vis/res [--json out.json]

error rate = errors / items checked (header items + every field line + every note line + every MISSING item added).
Prints per-kind and per-label counts; the verdict files hold client values — keep them out of the repository.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
from pathlib import Path


def score(folder: str) -> dict:
    files = sorted(glob.glob(str(Path(folder) / "p*.json")))
    n = e = 0
    kinds, labels, pages_err = collections.Counter(), collections.Counter(), 0
    for f in files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        n += int(d.get("checked") or 0)
        errs = d.get("errors") or []
        e += len(errs)
        pages_err += bool(errs)
        for x in errs:
            kinds[x.get("kind")] += 1
            labels[(x.get("kind"), str(x.get("label") or x.get("item"))[:40])] += 1
    return {"pages": len(files), "pages_with_errors": pages_err, "checked": n, "errors": e,
            "error_rate_pct": round(100 * e / n, 2) if n else None, "accuracy_pct": round(100 - 100 * e / n, 2) if n else None,
            "kinds": dict(kinds.most_common()), "top": [[k[0], k[1], v] for k, v in labels.most_common(40)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--json")
    a = ap.parse_args()
    s = score(a.folder)
    print(f"pages {s['pages']} (with errors {s['pages_with_errors']}) · items {s['checked']} · errors {s['errors']} · "
          f"error rate {s['error_rate_pct']} % · accuracy {s['accuracy_pct']} %")
    print("by kind:", s["kinds"])
    for k, lab, v in s["top"][:25]:
        print(f"  {v:4d}  {k:12s} {lab}")
    if a.json:
        Path(a.json).write_text(json.dumps(s, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
