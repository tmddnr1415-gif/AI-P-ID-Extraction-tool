"""두 결과 json 의 행을 칸 단위로 대조한다 — 어느 행이 사라지고 생겼고, 공통 행에서 어느 칸이 움직였나.

    python3 spike/diff_results.py <old.json> <new.json> [열,…]

행 짝은 (page_no, tab, 반올림한 rect) 로 짓는다 (키는 분석마다 같아야 하지만 접미가 흔들릴 수 있다).
"""
from __future__ import annotations
import json, sys, collections

old = json.load(open(sys.argv[1])); new = json.load(open(sys.argv[2]))
ro = (old.get("result") or old)["rows"]; rn = (new.get("result") or new)["rows"]
cols = sys.argv[3].split(",") if len(sys.argv) > 3 else ["tab", "scope", "qty", "needs_review", "description", "tag_no", "line_no", "remark"]
def k(r):
    rc = r.get("rect") or [0, 0, 0, 0]
    return (r["page_no"], r.get("tab"), tuple(round(v, 1) for v in rc))
def v(r, c):
    x = r.get(c)
    if x is None and isinstance(r.get("values"), dict): x = r["values"].get(c)
    return x
mo = {}; mn = {}
for r in ro: mo.setdefault(k(r), []).append(r)
for r in rn: mn.setdefault(k(r), []).append(r)
gone = [r for key, rs in mo.items() for r in rs[len(mn.get(key, [])):]]
born = [r for key, rs in mn.items() for r in rs[len(mo.get(key, [])):]]
print(f"old {len(ro)} · new {len(rn)} · 사라진 행 {len(gone)} · 생긴 행 {len(born)}")
for r in gone: print("  −", r["page_no"], r.get("tab"), v(r, "type") or (r.get("evidence") or {}).get("anchor"), v(r, "tag_no"), (r.get("description") or "")[:50], "rect", [round(x) for x in (r.get("rect") or [])])
for r in born: print("  +", r["page_no"], r.get("tab"), v(r, "type") or (r.get("evidence") or {}).get("anchor"), v(r, "tag_no"), (r.get("description") or "")[:50], "rect", [round(x) for x in (r.get("rect") or [])])
moved = collections.Counter(); examples = collections.defaultdict(list)
for key in mo.keys() & mn.keys():
    for a, b in zip(mo[key], mn[key]):
        for c in cols:
            if v(a, c) != v(b, c):
                moved[c] += 1
                if len(examples[c]) < 4: examples[c].append((a["page_no"], str(v(a, c))[:60], "→", str(v(b, c))[:60]))
print("공통 행에서 움직인 칸:", dict(moved) or "0")
for c, ex in examples.items():
    for e in ex: print("   ", c, e)
