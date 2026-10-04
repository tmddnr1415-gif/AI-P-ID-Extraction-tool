"""hotfix38 — 추가·삭제 판정을 **눈으로** 확인할 크롭.  같은 도면의 A(직전)·B(이번) 자리를 나란히.

    python3 spike/rev_crops.py <flow_dir> <pdf_A> <pdf_B> <out_dir> [n]

추가 행은 B 좌표를 B 에서, 같은 좌표를 A 에서 잘라 "A 에는 없었나" 를 보이고,
삭제 후보는 A 좌표(장부 anchor)를 A 에서, 같은 좌표를 B 에서 잘라 "B 에서 사라졌나" 를 보인다.
"""
from __future__ import annotations
import json, sys, random
from pathlib import Path
import pymupdf

flow, pdf_a, pdf_b, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], Path(sys.argv[4])
n = int(sys.argv[5]) if len(sys.argv) > 5 else 6
out.mkdir(parents=True, exist_ok=True)
rows = json.loads((flow / "B_rows_new.json").read_text()) if (flow / "B_rows_new.json").exists() else json.loads((flow / "B_rows.json").read_text())
rev = json.loads((flow / "B_revision_new.json").read_text()) if (flow / "B_revision_new.json").exists() else json.loads((flow / "B_revision.json").read_text())
pa = {p["drawing_no"]: p["page_no"] for p in json.loads((flow / "A_pages.json").read_text()) if p["drawing_no"]}
pb = {p["drawing_no"]: p["page_no"] for p in json.loads((flow / "B_pages.json").read_text()) if p["drawing_no"]}
renum = {e["before"]: e["now"] for e in (rev.get("sheets") or {}).get("renumbered") or []}
da, db = pymupdf.open(pdf_a), pymupdf.open(pdf_b)


def crop(doc, pno, cx, cy, path, half=110, z=2.5):
    page = doc[pno - 1]
    clip = pymupdf.Rect(cx - half, cy - half, cx + half, cy + half) & page.rect
    page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip).save(path)


random.seed(38)
added = [r for r in rows if (r.get("rev") or {}).get("state") == "ADDED"]
dels = rev.get("deleted_candidates") or []
lines = ["# 추가·삭제 판정 눈 확인 크롭", ""]
for i, r in enumerate(random.sample(added, min(n, len(added)))):
    x0, y0, x1, y1 = r["rect"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = r["drawing_no"]; pb_no = pb.get(d); old_d = next((k for k, v in renum.items() if v == d), d); pa_no = pa.get(old_d)
    tag = (r["values"] or {}).get("tag_no") or "(태그 없음)"
    crop(db, pb_no, cx, cy, out / f"add{i}_B_p{pb_no}.png")
    if pa_no: crop(da, pa_no, cx, cy, out / f"add{i}_A_p{pa_no}.png")
    lines.append(f"- add{i}: {d} p{pb_no} {r['values'].get('type')} {tag} · 근거 {r['rev'].get('basis')} — {r['rev'].get('reason')} · A 쪽 {('p%s' % pa_no) if pa_no else '장 없음'}")
for i, dd in enumerate(random.sample(dels, min(n, len(dels)))):
    cx, cy = dd["anchor"]; d = dd["drawing_no"]; pa_no = pa.get(d); pb_no = pb.get(renum.get(d, d))
    if pa_no: crop(da, pa_no, cx, cy, out / f"del{i}_A_p{pa_no}.png")
    if pb_no: crop(db, pb_no, cx, cy, out / f"del{i}_B_p{pb_no}.png")
    lines.append(f"- del{i}: {d} p{pa_no} {dd.get('type')} {dd.get('tag_no') or '(태그 없음)'} · 근거 {dd.get('basis')} · 다른 도면 {dd.get('tag_elsewhere')} · 최근접 {dd.get('nearest_distance')} / 반경 {dd.get('radius')} · B 쪽 {('p%s' % pb_no) if pb_no else '장 없음'}")
(out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
