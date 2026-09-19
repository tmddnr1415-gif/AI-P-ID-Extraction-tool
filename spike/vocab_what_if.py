"""SIMILAR 을 빼면 무엇이 달라지나 — 계산으로만 (파이프라인 재실행 없음).

Q'ty 모형은 저장된 결과에서 **검산**한다: 모든 행이 `1 symbol`이므로 Q'ty = Σ(그 장의 배수).
TC2 실측 검산 3047 = 301x8 + 187x1 + 66x4 + 28x4 + 16x1 + 6x8 + 2x2 + 1x8 ✓
"""
import json, re, sys, collections
from pathlib import Path
sys.path.insert(0, ".")
from app.engine import pidcache, projectconfig

class Cfg:
    def __init__(self, same): self.data = {"qty_note": {"same_words": list(same)}}

FULL = ("IDENTICAL", "SIMILAR", "SAME", "TYPICAL")
CASES = {"현행 (넷 다 같게)": FULL,
         "SIMILAR 제외": tuple(w for w in FULL if w != "SIMILAR"),
         "IDENTICAL 만": ("IDENTICAL",)}
PROJ = {"AL NOUF1": ("data/pid_total.pdf", "AL_NOUF1", [1960.0, 35.0, 2384.0, 1250.0], 2330.0),
        "TC2": ("data/TC2_260821.pdf", "TC2", None, None),
        "UAD": ("data/UAD_binding.pdf", "UAD", None, None),
        "SADARA": ("app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf", "SADARA", None, None)}
out = {}
for name, (pdf, tag, area0, xmax0) in PROJ.items():
    res = json.load(open(f"out/regression_3p/{tag}.json"))["result"]
    lay = (res.get("applied_rules") or {}).get("layout") or {}
    moved = {m["key"]: m["now"] for m in (lay.get("moved") or []) if isinstance(m, dict)}
    area = area0 or moved["regions.notes_area"]
    xmax = xmax0 or moved["regions.notes_text_x_max"]
    table = (res["multipliers"] or {}).get("table") or {}
    legend = (res["multipliers"] or {}).get("source") == "LEGEND"
    rows = res["rows"]
    per_page = collections.Counter(r["page_no"] for r in rows)
    code = {}
    for r in rows:
        dn = r.get("drawing_no") or ""
        code[r["page_no"]] = (dn.split("-")[1][:2] if "-" in dn else None)
    doc, pages = pidcache.load_pages(Path(pdf))
    spans = {}
    for pc in pages:
        if pc.page_no not in per_page:
            continue
        spans[pc.page_no] = {k: projectconfig.note_unit_span(pc, area, xmax, cfg=Cfg(v))
                             for k, v in CASES.items()}
    doc.close()
    rec = {"legend_answers": legend, "rows": len(rows), "cases": {}}
    for case in CASES:
        qty = 0; undef = 0; from_note = 0; from_cfg = 0
        for p, n in per_page.items():
            sp = spans.get(p)
            f = None
            if legend:                                   # ① 범례가 이기면 노트를 아예 안 본다
                f = table.get(code.get(p))
            else:
                if sp and sp[case].count:
                    f = sp[case].count; from_note += n
                else:
                    f = table.get(code.get(p)); from_cfg += n
            if f is None: undef += n
            else: qty += f * n
        rec["cases"][case] = {"qty": qty, "undefined_rows": undef,
                              "note_rows": from_note, "config_rows": from_cfg,
                              "note_pages": sum(1 for p in spans if spans[p][case].count)}
    out[name] = rec
    print(f"== {name} (범례가 답함: {legend}) · 행 {len(rows)}")
    for case, v in rec["cases"].items():
        print(f"   {case:16s} Q'ty {v['qty']:6d} · 노트 장 {v['note_pages']:3d} · "
              f"노트 행 {v['note_rows']:4d} · 설정폴백 행 {v['config_rows']:4d} · 빈칸 {v['undefined_rows']:4d}")
json.dump(out, open("out/round36_what_if.json", "w"), ensure_ascii=False, indent=1)
