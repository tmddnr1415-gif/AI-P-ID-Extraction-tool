"""hotfix38 — 개정 대조의 독립 검사.  `revisions.compare` 를 부르지 않는다.

    python3 spike/rev_tag_diff.py <A_rows.json> <B_rows.json> <B_revision.json> [out.md]

두 판의 행을 **태그만으로** 도면 단위 집합 대조한다 — (도면번호, TYPE, 태그).
A 에만 있으면 삭제, B 에만 있으면 추가.  그 답을 compare() 의 상태와 맞춰
어디서 갈리는지 센다.  태그 없는 행은 이 검사가 답하지 못하므로 따로 센다.
"""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path

a_rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
b_rows = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
rev = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
out_md = Path(sys.argv[4]) if len(sys.argv) > 4 else None


def key(r):
    v = r.get("values") or {}
    tag = str(v.get("tag_no") or "").strip()
    return (r.get("drawing_no") or "", str(v.get("type") or ""), tag) if tag else None


def tagset(rows):
    c = Counter(k for k in (key(r) for r in rows) if k)
    return c


A, B = tagset(a_rows), tagset(b_rows)
a_untagged = sum(1 for r in a_rows if not key(r))
b_untagged = sum(1 for r in b_rows if not key(r))
only_a = {k: n for k, n in A.items() if k not in B}
only_b = {k: n for k, n in B.items() if k not in A}
dup_a = {k: n for k, n in A.items() if n > 1}
dup_b = {k: n for k, n in B.items() if n > 1}

# compare() 가 낸 상태
states = {r["key"]: (r.get("rev") or {}) for r in b_rows}
st_by_tag = defaultdict(list)
for r in b_rows:
    k = key(r)
    if k:
        st_by_tag[k].append(states.get(r["key"], {}).get("state", ""))
cands = rev.get("deleted_candidates") or []
del_tags = Counter((d.get("drawing_no") or "", d.get("type") or "",
                    str(d.get("tag_no") or (d.get("values") or {}).get("tag_no") or "").strip())
                   for d in cands)

# 대조 — 태그 기준 추가 ↔ compare ADDED
agree_add = sum(1 for k in only_b if k not in dup_b and st_by_tag[k] == ["ADDED"])
agree_del = sum(1 for k in only_a if k not in dup_a and del_tags.get(k, 0) >= 1)
same_tags = [k for k in A if k in B and k not in dup_a and k not in dup_b]
agree_same = sum(1 for k in same_tags if st_by_tag[k] and st_by_tag[k][0] in ("UNCHANGED", "MODIFIED"))

lines = []
P = lines.append
P("# 독립 태그 대조 ↔ compare() 상태")
P("")
P(f"- A 행 {len(a_rows)} (태그 {sum(A.values())} · 태그 없음 {a_untagged}) · B 행 {len(b_rows)} (태그 {sum(B.values())} · 태그 없음 {b_untagged})")
P(f"- 태그 열쇠 종류 A {len(A)} · B {len(B)} · 겹침 {len(set(A)&set(B))} · 중복 열쇠 A {len(dup_a)} · B {len(dup_b)}")
P(f"- 태그만으로: 추가 {len(only_b)} 열쇠 · 삭제 {len(only_a)} 열쇠")
c = rev.get("counts") or {}
P(f"- compare(): 추가 {c.get('ADDED',0)} · 수정 {c.get('MODIFIED',0)} · 불변 {c.get('UNCHANGED',0)} · 삭제 후보 {c.get('DELETED_CANDIDATE',0)} · 짝 {rev.get('matched_by')}")
P("")
P("## 일치")
P(f"- 태그 추가(유일 열쇠) 중 compare 도 ADDED: {agree_add}/{len([k for k in only_b if k not in dup_b])}")
P(f"- 태그 삭제(유일 열쇠) 중 compare 도 삭제 후보: {agree_del}/{len([k for k in only_a if k not in dup_a])}")
P(f"- 양쪽에 있는 유일 태그 중 compare 가 짝지은 것: {agree_same}/{len(same_tags)}")
P("")
P("## 갈리는 자리")
for k in sorted(only_b):
    if k in dup_b: continue
    if st_by_tag[k] != ["ADDED"]:
        P(f"- B 에만 있는 태그인데 상태 {st_by_tag[k]}: {k}")
for k in sorted(only_a):
    if k in dup_a: continue
    if not del_tags.get(k):
        P(f"- A 에만 있는 태그인데 삭제 후보 아님: {k}")
for k in sorted(same_tags):
    if not st_by_tag[k] or st_by_tag[k][0] not in ("UNCHANGED", "MODIFIED"):
        P(f"- 양쪽에 있는 태그인데 상태 {st_by_tag[k]}: {k}")
P("")
P("## 태그 없는 행의 compare 상태 (B)")
cu = Counter(states.get(r["key"], {}).get("state", "") for r in b_rows if not key(r))
P(f"- {dict(cu)}")
P(f"- 태그 없는 삭제 후보: {sum(1 for d in cands if not str(d.get('tag_no') or '').strip())}")
P("")
P("## 도면별 추가/삭제 (태그 기준)")
by = defaultdict(lambda: [0, 0])
for k in only_b: by[k[0]][0] += 1
for k in only_a: by[k[0]][1] += 1
for d in sorted(by):
    P(f"- {d}: 추가 {by[d][0]} · 삭제 {by[d][1]}")
text = "\n".join(lines)
print(text)
if out_md:
    out_md.write_text(text + "\n", encoding="utf-8")
