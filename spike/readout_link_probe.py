"""#39 — 한 가지의 표시기(PI)와 전송기(PIT/PT)가 **이어 그려져** 있는가.

    python3 spike/readout_link_probe.py <result.json | sqlite:app.db:job> <pdf> [out.md]

규칙 후보(순회 없음): 같은 장 · 같은 머리(P/T/PD/L/F) · 한쪽은 표시기(…I) · 다른 쪽은
전송기(…T/…IT) · 두 버블이 한 축으로 겹치고(가로 겹침 ≥ 좁은 쪽 절반 또는 세로) ·
가까운 두 변 사이 틈이 **그 버블의 긴변 이하** · 그 틈 띠 안에 축 방향 잉크(선분)가 틈의
절반 이상을 덮는다.  같은 태그로 이미 접히는 짝과 새로 걸리는 짝을 따로 센다.
"""
from __future__ import annotations
import json, sqlite3, sys, collections
from pathlib import Path
import pymupdf

src, pdf = sys.argv[1], sys.argv[2]
out_md = Path(sys.argv[3]) if len(sys.argv) > 3 else None
rows = []
if src.startswith("sqlite:"):
    _, dbp, job = src.split(":")
    con = sqlite3.connect(f"file:{dbp}?mode=ro", uri=True); con.row_factory = sqlite3.Row
    for r in con.execute("select key,page_no,ai_json,evidence_json,rect_json from item where job_id=?", (job,)):
        v = json.loads(r["ai_json"]); e = json.loads(r["evidence_json"])
        rows.append({"key": r["key"], "page_no": r["page_no"], "tag_no": v.get("tag_no") or "",
                     "type": v.get("type"), "rect": json.loads(r["rect_json"]), "evidence": e})
    eng = json.loads(con.execute("select engine_json from job where id=?", (job,)).fetchone()[0])
else:
    d = json.loads(Path(src).read_text()); eng = d.get("result", d); rows = eng["rows"]
folded_keys = {f.get("folded_key") for f in (eng.get("readouts") or {}).get("folded") or []}
doc = pymupdf.open(pdf)
IND = {"PI", "TI", "PDI", "LI", "FI"}
def head(a):
    return a[:-1] if a in IND else (a[:-2] if a.endswith("IT") else (a[:-1] if a.endswith("T") else None))
inst = [r for r in rows if not (r.get("evidence") or {}).get("body") and r.get("rect")]
by_page = collections.defaultdict(list)
for r in inst:
    a = str((r.get("evidence") or {}).get("anchor") or r.get("type") or "").upper()
    r["_a"] = a
    by_page[r["page_no"]].append(r)
seg_cache = {}
def segs(pno):
    if pno not in seg_cache:
        page = doc[pno - 1]; m = page.rotation_matrix
        out = []
        for dr in page.get_drawings():
            for it in dr["items"]:
                if it[0] == "l":
                    p, q = pymupdf.Point(it[1]) * m, pymupdf.Point(it[2]) * m
                    out.append((p.x, p.y, q.x, q.y))
        seg_cache[pno] = out
    return seg_cache[pno]
def link(a, b, pno):
    """a, b rect.  돌려줌: (축, 틈, 덮인 비율) 또는 None."""
    long_side = max(a[2]-a[0], a[3]-a[1])
    ov_x = min(a[2], b[2]) - max(a[0], b[0]); ov_y = min(a[3], b[3]) - max(a[1], b[1])
    if ov_x >= 0.5 * min(a[2]-a[0], b[2]-b[0]):            # 세로로 쌓임
        gap0, gap1 = (a[3], b[1]) if a[1] < b[1] else (b[3], a[1])
        if gap1 - gap0 > long_side or gap1 <= gap0: return None
        x0, x1 = max(a[0], b[0]), min(a[2], b[2]); cov = []
        for sx0, sy0, sx1, sy1 in segs(pno):
            if abs(sx0 - sx1) > 0.5 or not (x0 <= sx0 <= x1): continue
            lo, hi = max(min(sy0, sy1), gap0), min(max(sy0, sy1), gap1)
            if hi > lo: cov.append((lo, hi))
        return ("V", round(gap1 - gap0, 1), _cover(cov, gap0, gap1))
    if ov_y >= 0.5 * min(a[3]-a[1], b[3]-b[1]):            # 나란히
        gap0, gap1 = (a[2], b[0]) if a[0] < b[0] else (b[2], a[0])
        if gap1 - gap0 > long_side or gap1 <= gap0: return None
        y0, y1 = max(a[1], b[1]), min(a[3], b[3]); cov = []
        for sx0, sy0, sx1, sy1 in segs(pno):
            if abs(sy0 - sy1) > 0.5 or not (y0 <= sy0 <= y1): continue
            lo, hi = max(min(sx0, sx1), gap0), min(max(sx0, sx1), gap1)
            if hi > lo: cov.append((lo, hi))
        return ("H", round(gap1 - gap0, 1), _cover(cov, gap0, gap1))
    return None
def _cover(cov, g0, g1):
    cov.sort(); tot = 0; cur = None
    for lo, hi in cov:
        if cur is None or lo > cur[1]:
            if cur: tot += cur[1] - cur[0]
            cur = [lo, hi]
        else: cur[1] = max(cur[1], hi)
    if cur: tot += cur[1] - cur[0]
    return round(tot / (g1 - g0), 2) if g1 > g0 else 0
found = []
for pno, items in sorted(by_page.items()):
    inds = [r for r in items if r["_a"] in IND]
    for i in inds:
        h = head(i["_a"])
        for t in items:
            if t is i or head(t["_a"]) != h or t["_a"] in IND: continue
            if not (t["_a"].endswith("T")): continue
            L = link(i["rect"], t["rect"], pno)
            if L and L[2] >= 0.5:
                found.append((pno, i["_a"], i["tag_no"], t["_a"], t["tag_no"], L, i["key"] in folded_keys, i["key"], t["key"]))
same = [f for f in found if f[2] and f[2] == f[4]]
new = [f for f in found if not (f[2] and f[2] == f[4])]
lines = [f"# 표시기↔전송기 이어 그린 짝 — {Path(pdf).name}", "",
         f"- 계기 행 {len(inst)} · 표시기 {sum(1 for r in inst if r['_a'] in IND)} · 이어진 짝 {len(found)} (같은 태그 {len(same)} · 태그 다름/없음 {len(new)}) · 이미 접힌 표시기 {sum(1 for f in found if f[6])}",
         f"- 틈 분포 {sorted(set(f[5][1] for f in found))[:12]}", ""]
for f in new:
    lines.append(f"- p{f[0]} {f[1]} {f[2] or '(태그 없음)'} ↔ {f[3]} {f[4] or '(태그 없음)'} · {f[5]} · 접힘 {f[6]}")
txt = "\n".join(lines); print(txt)
if out_md: out_md.write_text(txt + "\n", encoding="utf-8")
