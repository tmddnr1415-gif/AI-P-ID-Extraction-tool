#!/usr/bin/env python3
"""Phase 0 verification spike #3 — Q'ty multipliers (docs/design.md 부록 A).

    qty = symbols on the page x replication multiplier

The multiplier is **derived from the Symbol & Legend sheet**, not configured:
legend page 5 prints a UNIT IDENTIFICATION NUMBERS table that states the
plant's breakdown, and counting its rows per scope gives x1 for plant-common,
x2 for group-common and x4 for per-unit drawings.  See
spike/projectconfig.derive_unit_multipliers.  The configured table is a
fallback only, and using it is logged.

A unit code the legend never names does not get a guessed multiplier.  The
quantity is left empty and the item is marked NEEDS_REVIEW with a reason —
docs/design.md §8.3, a plausible wrong quantity is worse than a blank one on a
list that drives procurement.

Note text is used for cross-checking only.  It is counted, never interpreted:
the number of GROUP#/UNIT# references enumerated in the note is compared with
the legend-derived multiplier, and disagreement is reported rather than acted
on.

Usage
-----
    python spike/parse_notes.py --pdf data/pid_total.pdf \
           --compare data/CZE_Field_Instrument.xlsx \
           --titleblocks out/titleblocks.csv --out out/qty_report.md
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import projectconfig  # noqa: E402
from detect_all import (  # noqa: E402
    VENDOR_RULES,
    attribute_rows,
    excel_type_under,
    included_under,
    load_excel,
    review_annotations,
    system_of,
)
from detect_symbols import RULESET_V3, detect  # noqa: E402
from pidcache import load_pages  # noqa: E402

CFG = projectconfig.load()
ACTIVE_SCOPE = frozenset(VENDOR_RULES)

# Counted, not interpreted: which groups/units a note enumerates.  The trailing
# group picks up comma-separated continuations, because the notes write
# "IDENTICAL FOR UNIT#12,21,22" — dropping the tail would undercount 4 as 2.
GROUP_REF = re.compile(r"(?:GROUP|UNIT)\s*#?\s*(\d{2}(?:\s*,\s*\d{2})*)")


def note_group_refs(pc) -> set:
    """The set of group/unit numbers a page's notes mention, as bare tokens."""
    x0, y0, x1, y1 = CFG.rect("regions.notes_area")
    text = " ".join(t for r, t in pc.words
                    if x0 <= r.x0 <= x1 and y0 <= r.y0 <= y1)
    out = set()
    for run in GROUP_REF.findall(text.upper()):
        out.update(n.strip() for n in run.split(","))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 0 spike 3 — Q'ty multipliers")
    ap.add_argument("--pdf", default="data/pid_total.pdf")
    ap.add_argument("--compare", default="data/CZE_Field_Instrument.xlsx")
    ap.add_argument("--titleblocks", default="out/titleblocks.csv")
    ap.add_argument("--out", default="out/qty_report.md")
    ap.add_argument("--json", default="out/qty_report.json")
    args = ap.parse_args()

    tb = {int(r["page_no"]): r for r in
          csv.DictReader(open(args.titleblocks, encoding="utf-8-sig"))}
    excel, excel_total, excel_spare = load_excel(Path(args.compare))
    doc, pages = load_pages(args.pdf)

    kinds = {pc.page_no: tb[pc.page_no]["page_kind"] for pc in pages}
    um = projectconfig.derive_unit_multipliers(pages, CFG, page_kinds=kinds)
    print(f"unit multiplier source: {um.source}")
    print(f"  {um.note}")
    for code in sorted(um.table):
        print(f"    {code} -> x{um.table[code]}  [{um.scopes.get(code, '-')}]"
              f"  {um.labels.get(code, '')[:60]}")
    if um.source != "LEGEND":
        print("  !! legend parse failed — configured fallback in use")

    targets = [pc for pc in pages
               if tb[pc.page_no]["page_kind"] == "PID"
               and tb[pc.page_no]["analysis_scope"] == "True"]

    per_page, pages_by_drawing = {}, collections.defaultdict(list)
    overrides = {kw["keyword"].upper(): int(kw["multiplier"])
                 for kw in (CFG.data.get("qty_scope_overrides") or [])}

    for i, pc in enumerate(targets, 1):
        dets, *_ = detect(pc, rules=RULESET_V3)
        inc = [d for d in dets if included_under(d, RULESET_V3, ACTIVE_SCOPE)]
        ann = review_annotations(pc)
        body_text = " ".join(t for r, t in pc.words
                             if r.x0 < CFG.rect("regions.drawing_area")[2]).upper()
        hit_kw = [k for k in overrides if k in body_text]
        per_page[pc.page_no] = {
            "drawing_no": tb[pc.page_no]["drawing_no"],
            "title": tb[pc.page_no]["drawing_title"],
            "unit_code": tb[pc.page_no]["unit_code"],
            "system": system_of(tb[pc.page_no]["drawing_no"]),
            "detections": inc,
            "note_refs": note_group_refs(pc),
            "scope_keywords": hit_kw,
            "has_markup": any(a["where"] == "DRAWING" for a in ann),
        }
        pages_by_drawing[tb[pc.page_no]["drawing_no"]].append(pc.page_no)
        print(f"  [{i:>2}/{len(targets)}] p{pc.page_no}", flush=True)

    owned, _ = attribute_rows(excel, pages_by_drawing, per_page)
    matched = [p for p in per_page if owned.get(p)]

    rows, needs_review = [], []
    for pno in sorted(matched):
        info = per_page[pno]
        code = info["unit_code"]
        mult = um.multiplier(code)
        det_counts = collections.Counter(
            excel_type_under(d, RULESET_V3) for d in info["detections"])
        exp_qty = collections.Counter()
        for r in owned[pno]:
            if isinstance(r.get("qty"), (int, float)):
                exp_qty[r["type"]] += r["qty"]

        if mult is projectconfig.UNDEFINED:
            needs_review.append({
                "page_no": pno, "drawing_no": info["drawing_no"],
                "unit_code": code,
                "reason": f"unit code '{code}' is not in the legend's UNIT "
                          f"IDENTIFICATION NUMBERS table; multiplier undefined",
                "symbols": sum(det_counts.values()),
                "excel_qty": sum(exp_qty.values()),
            })
            rows.append({"page_no": pno, "drawing_no": info["drawing_no"],
                         "system": info["system"], "unit_code": code,
                         "multiplier": None, "qty": None,
                         "excel_qty": sum(exp_qty.values()),
                         "symbols": sum(det_counts.values()),
                         "status": "NEEDS_REVIEW",
                         "markup": info["has_markup"],
                         "scope_keywords": info["scope_keywords"],
                         "note_refs": sorted(info["note_refs"]),
                         "by_type": {}})
            continue

        by_type = {t: {"symbols": n, "qty": n * mult, "excel_qty": exp_qty.get(t, 0)}
                   for t, n in det_counts.items()}
        for t, q in exp_qty.items():
            by_type.setdefault(t, {"symbols": 0, "qty": 0, "excel_qty": q})
        rows.append({
            "page_no": pno, "drawing_no": info["drawing_no"],
            "system": info["system"], "unit_code": code, "multiplier": mult,
            "qty": sum(v["qty"] for v in by_type.values()),
            "excel_qty": sum(exp_qty.values()),
            "symbols": sum(det_counts.values()),
            "status": "OK",
            "markup": info["has_markup"],
            "scope_keywords": info["scope_keywords"],
            "note_refs": sorted(info["note_refs"]),
            "by_type": by_type,
        })

    clean = [r for r in rows if not r["markup"] and r["status"] == "OK"]
    flagged = [r for r in rows if r["markup"]]

    report(um, rows, clean, flagged, needs_review, excel_total, excel_spare, per_page)
    write_report(Path(args.out), um, rows, clean, flagged, needs_review, per_page)
    Path(args.json).write_text(json.dumps(
        {"multiplier_source": um.source, "multiplier_note": um.note,
         "multipliers": um.table, "rows": rows, "needs_review": needs_review},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {args.out} and {args.json}")
    return 0


def _acc(rows):
    got = sum(r["qty"] or 0 for r in rows)
    exp = sum(r["excel_qty"] for r in rows)
    hit = sum(min(v["qty"], v["excel_qty"])
              for r in rows for v in r["by_type"].values())
    return got, exp, hit


def report(um, rows, clean, flagged, needs_review, excel_total, excel_spare, per_page):
    print("\n" + "=" * 78)
    print("Q'TY ACCURACY (MATCHED pages)")
    print("=" * 78)
    got, exp, hit = _acc(clean)
    print(f"  clean pages (no review markup): {len(clean)}")
    print(f"    computed Q'ty {got}   excel Q'ty {exp}   diff {got - exp:+d}"
          f"   ({100.0 * hit / exp if exp else 0:.1f}% matched by type)")
    g2, e2, h2 = _acc(flagged)
    print(f"  pages carrying review markup:   {len(flagged)}  "
          f"(computed {g2} vs excel {e2}, reported separately)")
    g3, e3, h3 = _acc(rows)
    print(f"  all MATCHED pages:              {len(rows)}  "
          f"computed {g3} vs excel {e3}, diff {g3 - e3:+d}")
    print(f"\n  Excel total Q'ty across all 563 rows: 1120 "
          f"({excel_spare} SPARE rows have no P&ID No.)")

    print("\nby multiplier:")
    print(f"  {'mult':>4} {'pages':>6} {'symbols':>8} {'computed':>9} {'excel':>7} {'diff':>7}")
    by_m = collections.defaultdict(list)
    for r in clean:
        by_m[r["multiplier"]].append(r)
    for m in sorted(by_m):
        rs = by_m[m]
        g, e, _ = _acc(rs)
        print(f"  {m:>4} {len(rs):>6} {sum(r['symbols'] for r in rs):>8} "
              f"{g:>9} {e:>7} {g - e:>+7}")

    print("\nby system (clean pages, worst first):")
    by_s = collections.defaultdict(list)
    for r in clean:
        by_s[r["system"]].append(r)
    out = []
    for s, rs in by_s.items():
        g, e, _ = _acc(rs)
        out.append((abs(g - e), s, len(rs), g, e))
    for d, s, n, g, e in sorted(out, reverse=True):
        print(f"  {s:<5} pages={n:<3} computed={g:<5} excel={e:<5} diff={g - e:+d}")

    print("\nNEEDS_REVIEW (multiplier undefined):", len(needs_review))
    for nr in needs_review:
        print(f"  p{nr['page_no']} {nr['drawing_no']}  {nr['reason']}")

    kw_pages = [r for r in rows if r["scope_keywords"]]
    print(f"\nscope-override keyword found on {len(kw_pages)} page(s):")
    for r in kw_pages:
        print(f"  p{r['page_no']} {r['drawing_no']}  {r['scope_keywords']}  "
              f"computed {r['qty']} vs excel {r['excel_qty']}")

    checked = [r for r in clean if r["note_refs"] and r["multiplier"]]
    dis = [r for r in checked if len(r["note_refs"]) != r["multiplier"]]
    print(f"\nnote cross-check: {len(checked)} pages enumerate GROUP#/UNIT# in their "
          f"notes; {len(checked) - len(dis)} agree with the legend multiplier, "
          f"{len(dis)} disagree")
    for r in dis[:6]:
        print(f"    p{r['page_no']} {r['drawing_no']} legend x{r['multiplier']} "
              f"vs note {sorted(r['note_refs'])}")


def write_report(path, um, rows, clean, flagged, needs_review, per_page):
    got, exp, hit = _acc(clean)
    g3, e3, _ = _acc(rows)
    L = ["# 스파이크 3 — Q'ty 승수 검증\n",
         f"승수 출처: **{um.source}** — {um.note}\n",
         "\n| unit_code | 승수 | 스코프 | 범례 표기 |", "|---|---|---|---|"]
    for c in sorted(um.table):
        L.append(f"| `{c}` | ×{um.table[c]} | {um.scopes.get(c, '-')} | "
                 f"{um.labels.get(c, '')[:52]} |")
    L.append("\n승수는 config 상수가 아니라 **범례 p5 의 UNIT IDENTIFICATION NUMBERS "
             "표를 파싱해 유도**합니다. 표에 그룹이 2개·그룹당 유닛이 2개로 적혀 있어 "
             "PLANT ×1 / GROUP ×2 / UNIT ×4 가 그대로 나옵니다. 그룹 구성이 다른 "
             "프로젝트에서는 같은 코드가 다른 승수를 내놓습니다.\n")

    L.append("\n## 정확도\n")
    L.append("| 집합 | 페이지 | 산정 Q'ty | Excel Q'ty | 차이 |")
    L.append("|---|---|---|---|---|")
    L.append(f"| 주석 없는 페이지 (기준) | {len(clean)} | {got} | {exp} | {got - exp:+d} |")
    g2, e2, _ = _acc(flagged)
    L.append(f"| 개정 주석 있는 페이지 (별도 계상) | {len(flagged)} | {g2} | {e2} | {g2 - e2:+d} |")
    L.append(f"| MATCHED 전체 | {len(rows)} | {g3} | {e3} | {g3 - e3:+d} |")

    L.append("\n## 승수별\n")
    L.append("| 승수 | 페이지 | 심볼 | 산정 | Excel | 차이 |")
    L.append("|---|---|---|---|---|---|")
    by_m = collections.defaultdict(list)
    for r in clean:
        by_m[r["multiplier"]].append(r)
    for m in sorted(by_m):
        rs = by_m[m]
        g, e, _ = _acc(rs)
        L.append(f"| ×{m} | {len(rs)} | {sum(r['symbols'] for r in rs)} | {g} | {e} "
                 f"| {g - e:+d} |")

    L.append("\n## 계통별 (오차 큰 순)\n")
    L.append("| 계통 | 페이지 | 산정 | Excel | 차이 |")
    L.append("|---|---|---|---|---|")
    by_s = collections.defaultdict(list)
    for r in clean:
        by_s[r["system"]].append(r)
    tmp = []
    for s, rs in by_s.items():
        g, e, _ = _acc(rs)
        tmp.append((abs(g - e), s, len(rs), g, e))
    for d, s, n, g, e in sorted(tmp, reverse=True):
        L.append(f"| `{s}` | {n} | {g} | {e} | {g - e:+d} |")

    L.append("\n## NEEDS_REVIEW — 승수 미정의\n")
    if needs_review:
        L.append("| 페이지 | 도면번호 | unit_code | 사유 |")
        L.append("|---|---|---|---|")
        for nr in needs_review:
            L.append(f"| p{nr['page_no']} | `{nr['drawing_no']}` | `{nr['unit_code']}` "
                     f"| {nr['reason']} |")
    else:
        L.append("이번 문서에서는 없음 — 등장하는 unit_code 가 전부 범례 표에 있습니다. "
                 "정의에 없는 코드(예: `30`)가 나오면 수량을 비우고 사유와 함께 "
                 "NEEDS_REVIEW 로 보냅니다. 추측값을 채우지 않습니다.")

    L.append("\n## 같은 도면 안의 승수 예외\n")
    kw_pages = [r for r in rows if r["scope_keywords"]]
    L.append(f"`qty_scope_overrides` 키워드가 발견된 페이지: **{len(kw_pages)}건**\n")
    for r in kw_pages:
        L.append(f"- p{r['page_no']} `{r['drawing_no']}` — 키워드 {r['scope_keywords']}, "
                 f"산정 {r['qty']} vs Excel {r['excel_qty']}")
    L.append("""
### `(PLANT COMMON)` 가설 — **검증됨, 다만 적용은 보류**

`D00P-10PGB10-M05-0004`(p38)에서 확인했습니다.

- 도면에 `AUXILIARY BOILER COOLER` 라벨이 있고 **바로 아래 줄에 `(PLANT COMMON)`**
  이 붙어 있습니다 (좌표 `(327.6, 814.9)`).
- Excel 에서 이 도면의 Q'ty=1 인 3행은 전부 이 설비 것입니다 —
  `AUXILIARY BOILER COOLER CCW SUPPLY PRESSURE`(PI),
  `... CCW RETURN TEMPERATURE`(TI), `... CCW RETURN PRESSURE`(PI).
  같은 도면의 나머지 21행은 Q'ty=2 입니다.
- 도면을 렌더링해 확인한 결과 해당 설비의 계기는 정확히 **PI 2 + TI 1** 이고,
  각각 `(243.5, 473.4)` `(410.7, 1135.4)` `(410.5, 1184.4)` 에 있습니다.

**가설은 맞습니다.** 그런데 "어느 계기가 이 설비 소속인가"를 판정하려면 설비를
지나는 수직 배관을 따라가야 합니다. 실제로:

- 설비 점선 박스는 대시가 길어 현재 broken-line 검출기에 안 잡힙니다
  (`brk_max_mark` 는 UNKNOWN 항목이라 이번에 튜닝하지 않았습니다).
- 라벨 x 범위로 묶으면 옆 설비의 `(LUBE OIL` 텍스트가 섞여 들어와 엉뚱한 계기가
  포함되고 정작 `(243.5, …)` 는 빠집니다.

그래서 **승수 강제 적용을 하지 않았습니다.** 설계안 §8.3(불확실하면 값을 비우고
검토로 보낸다)에 따라 키워드 발견 사실만 기록합니다. 이 예외가 지표에 주는 영향은
3행 × (2−1) = **Q'ty 3 과다**로, 전체 대비 0.3% 수준입니다.
올바른 귀속은 §7 라인 추적(Phase 2)이 들어와야 가능합니다.
""")

    L.append("\n## Note 문구 교차검증\n")
    checked = [r for r in clean if r["note_refs"] and r["multiplier"]]
    dis = [r for r in checked if len(r["note_refs"]) != r["multiplier"]]
    L.append(f"NOTES 에 열거된 GROUP#/UNIT# 개수를 세어 범례 유도 승수와 대조했습니다 "
             f"(문장 해석 없이 **열거 개수만** 셉니다). 이 도면들의 Note 는 "
             f"`THIS P&ID IS FOR GROUP#10, ... IDENTICAL FOR GROUP#20` 처럼 "
             f"**자기 그룹까지 포함해** 열거하므로 열거 개수가 곧 승수입니다.\n")
    L.append(f"열거가 있는 페이지 {len(checked)}건 중 **{len(checked) - len(dis)}건 일치**, "
             f"{len(dis)}건 불일치.\n")
    if dis:
        L.append("| 페이지 | 도면번호 | 범례 승수 | Note 열거 | 판정 |")
        L.append("|---|---|---|---|---|")
        for r in dis[:12]:
            L.append(f"| p{r['page_no']} | `{r['drawing_no']}` | ×{r['multiplier']} "
                     f"| {r['note_refs']} | 범례값 채택, 불일치 기록 |")

    L.append("\n## 개정 주석이 있는 페이지 (별도 계상)\n")
    L.append("`out/revision_gap.md` 의 도면들입니다. Excel 이 도면 개정을 반영하지 "
             "않았으므로 이 페이지의 Q'ty 차이는 검출기 오차로 볼 수 없습니다.\n")
    L.append("| 페이지 | 도면번호 | 산정 | Excel | 차이 |")
    L.append("|---|---|---|---|---|")
    for r in flagged:
        L.append(f"| p{r['page_no']} | `{r['drawing_no']}` | {r['qty']} | "
                 f"{r['excel_qty']} | {(r['qty'] or 0) - r['excel_qty']:+d} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
