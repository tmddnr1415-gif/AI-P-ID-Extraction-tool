"""두 결과 json 의 행을 칸 단위로 대조한다 (hotfix27 — LS 묶음 SCOPE).

    python3 spike/diff_rows.py BEFORE.json AFTER.json

지문 대상 열 + scope 를 본다.  움직인 행마다 (장 · TYPE · 칸 · 전 → 후) 와
묶음이면 어느 신호의 별표를 따랐는지를 적는다.
"""
import json, sys, collections

COLS = ["tab", "page_no", "type", "qty", "valve_type", "vendor_supply", "scope",
        "description", "description_grade", "needs_review"]


def load(p):
    d = json.load(open(p)); r = d.get("result", d)
    return r, {x["key"]: x for x in r["rows"]}


rb, B = load(sys.argv[1]); ra, A = load(sys.argv[2])
print(f"전 {rb['fingerprint'][:8]} {len(B)}행 · 후 {ra['fingerprint'][:8]} {len(A)}행")
print(f"사라진 행 {len(set(B) - set(A))} · 새 행 {len(set(A) - set(B))}")
moved = collections.Counter()
for k in sorted(set(A) & set(B), key=lambda k: (A[k]["page_no"], k)):
    a, b = A[k], B[k]
    diff = [c for c in COLS if a.get(c) != b.get(c)]
    if not diff:
        continue
    for c in diff:
        moved[c] += 1
    bs = (a.get("evidence") or {}).get("bundle_scope") or {}
    sig = " + ".join((a.get("evidence") or {}).get("signal_members") or [])
    print(f"p{a['page_no']:<3} {a['type']:6} {k}  " + " · ".join(
        f"{c}: {str(b.get(c))[:40]!r} → {str(a.get(c))[:40]!r}" for c in diff if c != "needs_review")
        + (f"  [묶음 {sig} · 별표는 {bs.get('anchor')}]" if bs else "")
        + ("  (+검토 사유 변화)" if "needs_review" in diff else ""))
print("움직인 칸:", dict(moved))
