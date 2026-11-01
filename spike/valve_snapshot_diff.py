#!/usr/bin/env python3
"""Findings guard — compare the live server's findings with a frozen snapshot, field by field (valve29).

    python3 spike/valve_snapshot_diff.py save <out.json> [--base http://127.0.0.1:8000] [--pid 1]
    python3 spike/valve_snapshot_diff.py check <snapshot.json> [--base …] [--pid 1]

A snapshot holds, for every finding of the newest revisions: tag · rev · ikey · check · type · severity · description ·
expected · status.  `check` lists findings added / removed / changed (which field).  New fields (op · tol · result ·
decision …) are ignored on purpose: Phase 1 adds information and must not change a judgement.
The snapshot holds client values — keep it outside the repository (out/ is git-excluded).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

KEYS = ("tag", "rev", "ikey", "check", "type", "severity", "description", "expected", "status")


def fetch(base, pid):
    I = json.load(urllib.request.urlopen(f"{base}/api/valve/projects/{pid}/issues"))["issues"]
    return {(i["tag"], i["ikey"]): {k: i.get(k) for k in KEYS} for i in I}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["save", "check"])
    ap.add_argument("path")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--pid", type=int, default=1)
    a = ap.parse_args()
    now = fetch(a.base, a.pid)
    if a.mode == "save":
        json.dump({"issues": list(now.values())}, open(a.path, "w"), ensure_ascii=False, indent=0)
        print(f"saved {len(now)} findings -> {a.path}")
        return 0
    old = {(i["tag"], i["ikey"]): i for i in json.load(open(a.path))["issues"]}
    added = sorted(set(now) - set(old))
    removed = sorted(set(old) - set(now))
    changed = []
    for k in sorted(set(now) & set(old)):
        d = [f for f in KEYS if (now[k].get(f) or None) != (old[k].get(f) or None)]
        if d:
            changed.append((k, d))
    print(f"findings: snapshot {len(old)} · now {len(now)} · added {len(added)} · removed {len(removed)} · changed {len(changed)}")
    for k in added[:10]:
        print("  + ", k, now[k]["type"], (now[k]["description"] or "")[:90])
    for k in removed[:10]:
        print("  - ", k, old[k]["type"], (old[k]["description"] or "")[:90])
    for k, d in changed[:15]:
        print("  ~ ", k, {f: (old[k].get(f), now[k].get(f)) for f in d})
    return 1 if (added or removed or changed) else 0


if __name__ == "__main__":
    sys.exit(main())
