#!/usr/bin/env python3
"""Phase 0 spike 2e — cross-validation: how much of the score is overfitting?

97.0% / 87.0% was reached while looking at all 53 drawings, and the FE, FT, LG
and DPIT mappings were each found by comparing against the full Excel.  That
makes the number an in-sample figure: it says how well the rules describe
*these* drawings, not how they would do on a drawing set nobody had looked at.

This measures the difference directly.  A ruleset is rebuilt using only what
the Steam systems (LBA / LBB / LBC / LBG / MAN) show — every rule whose
evidence came from another system is switched off — and then applied, unseen,
to Closed Cooling Water (PGB), Seawater Intake (PAB) and Fuel Oil (EGD).  The
drop from in-sample to out-of-sample is the proxy for "what happens when a new
project's P&ID arrives", and the rules that cause it are the overfitted ones.

No new detection rules.  No NOTES prose, no LLM.

Usage
-----
    python spike/crossval.py --pdf data/pid_total.pdf \
           --compare data/CZE_Field_Instrument.xlsx \
           --titleblocks out/titleblocks.csv --out out/crossval.md
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from detect_symbols import (  # noqa: E402
    KNOWN_GLYPH_SIZES,
    RULESET_V3,
    Ruleset,
    VALVE_ANCHORS,
    detect,
)
from detect_all import (  # noqa: E402
    VENDOR_RULES,
    attribute_rows,
    excel_type_under,
    included_under,
    ActiveScope,
    load_excel,
    system_of,
)
from pidcache import load_pages  # noqa: E402

STEAM = ("LBA", "LBB", "LBC", "LBG", "MAN")
HOLDOUT = ("PGB", "PAB", "EGD")

# What the Steam drawings alone can justify.
#
#   FE -> FE      p10/p11 (MAN) draw 3 FE each against 3 FE rows each.
#   FT -> FIT     p10 5/5, p11 5/5, p12 1/1.
#   LSH/LSHH/LSL  p7 (LBC40) draws 4 LSHH + 4 LSH against 4 LS rows.
#   TW excluded   no Steam drawing's rows contain TW.
#
# Withheld, because no Steam drawing shows them:
#
#   LG -> LI      evidence is p33 (EGD), p49 (GHB), p51 (GKB).
#   DPIT -> PDIT  evidence is p21 (LAC).
#   VENDOR_MARK_TEXT   no Steam page writes its mark legend as text.
#   glyph size 5.2     only page 49 (GHB) draws marks at that size.
_STEAM_MAP = {
    "TT": "TIT", "PT": "PIT", "LT": "LIT", "PDT": "PDIT",
    "TI": "TI", "PI": "PI", "LI": "LI", "FI": "FI",
    "TIT": "TIT", "PIT": "PIT", "LIT": "LIT", "PDIT": "PDIT", "FIT": "FIT",
    "LS": "LS", "FS": "FS", "RO": "RO",
    "FE": "FE", "LSH": "LS", "LSHH": "LS", "LSL": "LS",
    "FT": "FIT",
}
RULESET_STEAM = Ruleset("steam-only", _STEAM_MAP, frozenset({"TW"}), VALVE_ANCHORS)

STEAM_SCOPE = ActiveScope({"VENDOR_MARK_GLYPH", "VENDOR_MARK_BOX"})
FULL_SCOPE = ActiveScope(VENDOR_RULES)
STEAM_GLYPH_SIZES = ((4.0, 4.0),)


def score(pages_subset, per_page, owned, rules, scope):
    tp = det_tot = exp_tot = 0
    per_type = collections.Counter()
    for pno in pages_subset:
        key = (rules.name, scope)
        det = collections.Counter(
            excel_type_under(d, rules) for d in per_page[pno]["dets"][key]
            if included_under(d, rules, scope))
        exp = collections.Counter(r["type"] for r in owned.get(pno, []))
        for t in set(det) | set(exp):
            hit = min(det.get(t, 0), exp.get(t, 0))
            tp += hit
            per_type[t] += det.get(t, 0) - exp.get(t, 0)
        det_tot += sum(det.values())
        exp_tot += sum(exp.values())
    return {"tp": tp, "detected": det_tot, "expected": exp_tot,
            "recall": tp / exp_tot if exp_tot else 0.0,
            "precision": tp / det_tot if det_tot else 0.0,
            # Sorted so the report is byte-identical between runs: the key
            # -abs(v) alone leaves ties to dict insertion order.
            "delta_by_type": {k: v for k, v in
                              sorted(per_type.items(), key=lambda kv: (-abs(kv[1]), kv[0]))
                              if v}}


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0 spike 2e — cross-validation")
    ap.add_argument("--pdf", default="data/pid_total.pdf")
    ap.add_argument("--compare", default="data/CZE_Field_Instrument.xlsx")
    ap.add_argument("--titleblocks", default="out/titleblocks.csv")
    ap.add_argument("--out", default="out/crossval.md")
    args = ap.parse_args()

    tb = {int(r["page_no"]): r for r in
          csv.DictReader(open(args.titleblocks, encoding="utf-8-sig"))}
    excel, _, _ = load_excel(Path(args.compare))
    doc, pages = load_pages(args.pdf)
    targets = [pc for pc in pages
               if tb[pc.page_no]["page_kind"] == "PID"
               and tb[pc.page_no]["analysis_scope"] == "True"]

    per_page, pages_by_drawing = {}, collections.defaultdict(list)
    configs = [(RULESET_STEAM, STEAM_SCOPE, STEAM_GLYPH_SIZES),
               (RULESET_V3, FULL_SCOPE, KNOWN_GLYPH_SIZES)]
    for i, pc in enumerate(targets, 1):
        entry = {"drawing_no": tb[pc.page_no]["drawing_no"],
                 "title": tb[pc.page_no]["drawing_title"],
                 "system": system_of(tb[pc.page_no]["drawing_no"]), "dets": {}}
        for rules, scope, sizes in configs:
            dets, *_ = detect(pc, rules=rules, disabled=frozenset(),
                              allow_glyph_sizes=sizes)
            entry["dets"][(rules.name, scope)] = dets
        per_page[pc.page_no] = entry
        pages_by_drawing[entry["drawing_no"]].append(pc.page_no)
        print(f"  [{i:>2}/{len(targets)}] p{pc.page_no}", flush=True)

    owned, _ = attribute_rows(excel, pages_by_drawing, per_page)
    matched = [p for p in per_page if owned.get(p)]

    groups = {"STEAM (in-sample)": [p for p in matched
                                    if per_page[p]["system"] in STEAM]}
    for sysname in HOLDOUT:
        groups[f"{sysname} (held out)"] = [p for p in matched
                                           if per_page[p]["system"] == sysname]
    groups["ALL MATCHED"] = matched

    rows = []
    for label, pgs in groups.items():
        st = score(pgs, per_page, owned, RULESET_STEAM, STEAM_SCOPE)
        fu = score(pgs, per_page, owned, RULESET_V3, FULL_SCOPE)
        rows.append({"group": label, "pages": len(pgs), "steam": st, "full": fu,
                     "d_recall": st["recall"] - fu["recall"],
                     "d_precision": st["precision"] - fu["precision"]})

    print("\n" + "=" * 86)
    print("CROSS-VALIDATION — rules built from Steam only, applied to held-out systems")
    print("=" * 86)
    print(f"{'group':<22} {'pg':>3} | {'steam-only rules':^24} | {'full rules':^24}")
    print(f"{'':<22} {'':>3} | {'det':>5} {'excel':>6} {'rec':>6} {'prec':>6} "
          f"| {'det':>5} {'excel':>6} {'rec':>6} {'prec':>6}")
    print("-" * 86)
    for r in rows:
        s, f = r["steam"], r["full"]
        print(f"{r['group']:<22} {r['pages']:>3} | {s['detected']:>5} {s['expected']:>6} "
              f"{s['recall']:>6.1%} {s['precision']:>6.1%} | {f['detected']:>5} "
              f"{f['expected']:>6} {f['recall']:>6.1%} {f['precision']:>6.1%}")

    print("\nDROP when the held-out systems are scored with Steam-only rules:")
    print(f"{'group':<22} {'Δrecall':>9} {'Δprecision':>11}   biggest type gaps")
    for r in rows:
        gaps = sorted(r["steam"]["delta_by_type"].items(),
                      key=lambda kv: (-abs(kv[1]), kv[0]))[:4]
        gap_s = ", ".join(f"{k}{v:+d}" for k, v in gaps)
        print(f"{r['group']:<22} {r['d_recall']:>+8.1%} {r['d_precision']:>+10.1%}   {gap_s}")

    L = ["# 교차검증 — Steam 계통만으로 규칙을 세우고 미지 계통에 적용\n",
         "현재 97.0% / 87.0% 는 53개 도면을 모두 보면서 맞춘 값입니다. "
         "`FE`·`FT`·`LG`·`DPIT` 매핑이 전부 전수 대조에서 나왔다는 사실이 그 증거입니다. "
         "여기서는 **Steam 계통(LBA/LBB/LBC/LBG/MAN)만 보고** 규칙을 재구성한 뒤, "
         "본 적 없는 PGB·PAB·EGD 에 적용해 하락폭을 측정합니다.\n",
         "\n## Steam 만으로 정당화되는 규칙 / 꺼진 규칙\n",
         "| 규칙 | Steam 근거 | 상태 |", "|---|---|---|",
         "| `FE` → Field | p10·p11 각각 FE 3개 = Excel 3행 | 유지 |",
         "| `FT` → `FIT` | p10 5/5, p11 5/5, p12 1/1 | 유지 |",
         "| `LSH`/`LSHH`/`LSL` → `LS` | p7 LSHH 4 + LSH 4 = LS 4행 | 유지 |",
         "| `TW` 제외 | Steam 도면 행에 `TW` 없음 | 유지 |",
         "| `VENDOR_MARK_GLYPH` | p6 범례 글리프 | 유지 |",
         "| `VENDOR_MARK_BOX` | p6 HRSG 패키지 박스 | 유지 |",
         "| `LG` → `LI` | Steam 에 근거 없음 (p33/p49/p51) | **꺼짐** |",
         "| `DPIT` → `PDIT` | Steam 에 근거 없음 (p21) | **꺼짐** |",
         "| `VENDOR_MARK_TEXT` | Steam 에 텍스트 범례 페이지 없음 | **꺼짐** |",
         "| 글리프 크기 5.2pt | p49 에서만 관찰 | **꺼짐** (4.0pt 만) |",
         "\n## 결과\n",
         "| 대상 | 페이지 | Steam 규칙 재현율 | Steam 규칙 정밀도 | 전체 규칙 재현율 | 전체 규칙 정밀도 | Δ재현율 | Δ정밀도 |",
         "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        s, f = r["steam"], r["full"]
        L.append(f"| {r['group']} | {r['pages']} | {s['recall']:.1%} | {s['precision']:.1%} "
                 f"| {f['recall']:.1%} | {f['precision']:.1%} "
                 f"| {r['d_recall']:+.1%} | {r['d_precision']:+.1%} |")
    L.append("\n## TYPE 별 편차 (Steam 규칙 적용 시, 검출 − Excel)\n")
    L.append("| 대상 | 편차 |")
    L.append("|---|---|")
    for r in rows:
        gaps = sorted(r["steam"]["delta_by_type"].items(),
                      key=lambda kv: (-abs(kv[1]), kv[0]))
        L.append(f"| {r['group']} | " + ", ".join(f"`{k}` {v:+d}" for k, v in gaps) + " |")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    Path("out/crossval.json").write_text(json.dumps(
        [{"group": r["group"], "pages": r["pages"], "steam": r["steam"],
          "full": r["full"]} for r in rows], indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
