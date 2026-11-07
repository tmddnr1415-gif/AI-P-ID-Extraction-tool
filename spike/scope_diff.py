"""두 회귀 결과(json)의 행을 키로 맞춰 움직인 칸을 센다 — 특히 SCOPE.

    python3 spike/scope_diff.py out/hotfix58/before/TC2.json out/regression_3p/TC2.json
"""
import collections
import json
import sys


def rows(path):
    r = json.load(open(path, encoding="utf-8"))["result"]
    return {x["key"]: x for x in r["rows"]}, r.get("fingerprint", "")


def main(a, b):
    ra, fa = rows(a)
    rb, fb = rows(b)
    print(f"지문 {fa[:8]} → {fb[:8]} · 행 {len(ra)} → {len(rb)} · "
          f"사라진 {len(set(ra) - set(rb))} · 새 {len(set(rb) - set(ra))}")
    moved = collections.Counter()
    scope = []
    for k in sorted(set(ra) & set(rb)):
        x, y = ra[k], rb[k]
        for f in sorted(set(x) | set(y)):
            if f in ("evidence",):
                continue
            if x.get(f) != y.get(f):
                moved[f] += 1
        if x.get("scope") != y.get("scope"):
            scope.append((y.get("page_no"), y.get("tab"), y.get("type"),
                          (y.get("evidence") or {}).get("tag") or "",
                          x.get("scope"), y.get("scope"), y.get("rect")))
    print("움직인 칸:", dict(moved))
    for s in sorted(scope, key=lambda t: (t[0] or 0)):
        print(f"  p{s[0]} {s[1]} {s[2]} {s[3]}  {s[4]} → {s[5]}  {s[6]}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
