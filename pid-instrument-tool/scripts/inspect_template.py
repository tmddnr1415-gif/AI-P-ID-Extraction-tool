#!/usr/bin/env python3
"""Excel 템플릿(`2.0_Instrument List`)을 해부해서 파이프라인 설정을 생성한다.

생성물:
  config/excel_format.json  — 컬럼 스펙 (열 문자, 키, 라벨, 값의 출처)
  config/typicals.json      — INST. TYPICAL TYPE → 하위 사양 컬럼 값 (템플릿에서 학습)
  samples/test_set_v1/ground_truth.json — 사람이 작성한 정답 계기 목록

값의 출처(source)를 구분하는 것이 이 스크립트의 핵심이다. 템플릿 563행을 분석하면
컬럼은 네 부류로 나뉘고, 모델이 판독해야 하는 건 그중 일부뿐이다:

  drawing      P&ID 도면에서 판독 (SYSTEM, P&ID No., TYPE, Q'ty, DESCRIPTION 등)
  typical      INST. TYPICAL TYPE 값이 정해지면 결정되는 사양 (SENSING/ELEMENT/Signal 등)
  design_table 별도 Design Table에서 조인 (운전/설계조건, 배관 정보) — 도면에 없음
  blank        템플릿에서 전부 비어 있음 (UNIT, TAG, MAKER, MODEL, STATUS 등)
  auto_index   행 번호
  review       사람이 검토하며 채우는 칸

사용:
  python3 scripts/inspect_template.py inputs/<template>.xlsx
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
SHEET = "2.0_Instrument List"
HEADER_ROW, SUBHEADER_ROW, DATA_START = 6, 7, 8

# 열 문자 → (키, 값의 출처). 라벨은 템플릿에서 읽어 검증한다.
COLUMN_PLAN: dict[str, tuple[str, str]] = {
    "A":  ("no",                    "auto_index"),
    "B":  ("unit",                  "blank"),
    "C":  ("system_code",           "blank"),
    "D":  ("system_sequence",       "blank"),
    "E":  ("tag",                   "blank"),
    "F":  ("system",                "drawing"),
    "G":  ("pid_no",                "drawing"),
    "H":  ("type",                  "drawing"),
    "I":  ("qty",                   "drawing"),
    "J":  ("description",           "drawing"),
    "K":  ("design_table_no",       "design_table"),
    "L":  ("op_mass_flow",          "design_table"),
    "M":  ("op_pressure",           "design_table"),
    "N":  ("op_temperature",        "design_table"),
    "O":  ("des_mass_flow",         "design_table"),
    "P":  ("des_pressure",          "design_table"),
    "Q":  ("des_temperature",       "design_table"),
    "R":  ("pipe_material",         "design_table"),
    "S":  ("pipe_nb",               "design_table"),
    "T":  ("pipe_sch",              "design_table"),
    "U":  ("rating",                "design_table"),
    "V":  ("velocity_criteria",     "design_table"),
    "W":  ("fluid",                 "design_table"),
    "X":  ("inst_typical_type",     "drawing"),
    "Y":  ("sensing_type",          "typical"),
    "Z":  ("element_type",          "typical"),
    "AA": ("mounting_type",         "typical"),
    "AB": ("signal_type",           "typical"),
    "AC": ("calibration_range",     "design_table"),
    "AD": ("calibration_unit",      "typical"),
    "AE": ("element_material",      "typical"),
    "AF": ("connection_type",       "typical"),
    "AG": ("tw_chamber_spec",       "typical"),
    "AH": ("explosion_proof",       "typical"),
    "AI": ("base_option",           "typical"),
    "AJ": ("body_material",         "blank"),
    "AK": ("scope_of_supply",       "blank"),
    "AL": ("maker",                 "blank"),
    "AM": ("model",                 "blank"),
    "AN": ("status",                "blank"),
    "AO": ("remark",                "drawing"),
    "AP": ("note",                  "review"),
}

# typical 후보 중 실제로 X 값 하나당 값이 하나로 고정되는 컬럼만 typicals.json에 넣는다.
TYPICAL_CANDIDATES = [c for c, (_, s) in COLUMN_PLAN.items() if s == "typical"]


def clean(v) -> str:
    if v is None:
        return ""
    return str(v).replace("\n", " ").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template", type=Path, help="Field Instrument 템플릿 xlsx")
    ap.add_argument("--sheet", default=SHEET)
    args = ap.parse_args()

    wb = load_workbook(args.template, data_only=True)
    if args.sheet not in wb.sheetnames:
        print(f"[!] 시트 '{args.sheet}' 없음. 있는 시트: {wb.sheetnames}", file=sys.stderr)
        return 1
    ws = wb[args.sheet]

    # ── 1. 컬럼 스펙 ──────────────────────────────────────────────
    columns = []
    warnings = []
    for col, (key, source) in COLUMN_PLAN.items():
        label = clean(ws[f"{col}{HEADER_ROW}"].value)
        sub = clean(ws[f"{col}{SUBHEADER_ROW}"].value)
        if not label and sub:
            # L~T 처럼 상위 헤더가 병합된 그룹의 하위 헤더
            label = sub
        columns.append({"col": col, "key": key, "label": label, "sub_label": sub, "source": source})
        if not label and source not in ("review",):
            warnings.append(f"{col}열에 헤더가 없습니다 (key={key})")

    # ── 2. 데이터 행 읽기 ─────────────────────────────────────────
    rows = []
    for r in range(DATA_START, ws.max_row + 1):
        if not str(ws[f"A{r}"].value or "").strip().isdigit():
            continue
        rec = {}
        for c in columns:
            v = ws[f"{c['col']}{r}"].value
            rec[c["key"]] = clean(v)
        rec["_row"] = r
        rows.append(rec)
    print(f"[i] 데이터 행 {len(rows)}건 (r{rows[0]['_row']}~r{rows[-1]['_row']})")

    # ── 3. typical 매핑 학습 ──────────────────────────────────────
    by_typ: dict[str, dict[str, collections.Counter]] = collections.defaultdict(
        lambda: collections.defaultdict(collections.Counter))
    for rec in rows:
        x = rec.get("inst_typical_type", "")
        if not x:
            continue
        for c in TYPICAL_CANDIDATES:
            key = COLUMN_PLAN[c][0]
            by_typ[x][key][rec.get(key, "")] += 1

    typicals, inconsistent = {}, collections.Counter()
    for x, fields in sorted(by_typ.items()):
        entry, n = {}, sum(next(iter(fields.values())).values()) if fields else 0
        for key, counter in fields.items():
            if len(counter) == 1:
                entry[key] = next(iter(counter))
            else:
                inconsistent[key] += 1        # X만으로 결정되지 않는 컬럼
        entry["_count"] = n
        typicals[x] = entry

    if inconsistent:
        print("[i] X(TYPICAL TYPE)만으로 값이 결정되지 않아 typicals에서 제외한 컬럼:")
        for key, n in inconsistent.most_common():
            print(f"      {key}: {n}개 typical에서 값이 갈림 → source를 design_table로 두거나 사람이 채워야 함")
        drop = {k for k, _ in inconsistent.items()}
        for x in typicals:
            for k in drop:
                typicals[x].pop(k, None)
        for c in columns:
            if c["source"] == "typical" and c["key"] in drop:
                c["source"] = "design_table"
                warnings.append(f"{c['col']}({c['key']}): typical→design_table 로 강등 (X만으로 결정 불가)")

    # ── 4. TYPE → 허용 TYPICAL TYPE ──────────────────────────────
    type_to_typicals = collections.defaultdict(collections.Counter)
    for rec in rows:
        if rec.get("type") and rec.get("inst_typical_type"):
            type_to_typicals[rec["type"]][rec["inst_typical_type"]] += 1

    fmt = {
        "sheet": args.sheet,
        "header_row": HEADER_ROW,
        "subheader_row": SUBHEADER_ROW,
        "data_start_row": DATA_START,
        "template_file": args.template.name,
        "columns": columns,
        "instrument_types": sorted({r["type"] for r in rows if r.get("type")}),
        "systems": sorted({r["system"] for r in rows if r.get("system")}),
        "type_to_typical_types": {t: sorted(c) for t, c in sorted(type_to_typicals.items())},
    }

    gt = {
        "source": args.template.name,
        "sheet": args.sheet,
        "row_count": len(rows),
        "rows": [{k: v for k, v in r.items() if k != "_row" and v != ""} | {"_row": r["_row"]} for r in rows],
    }

    (ROOT / "config").mkdir(exist_ok=True)
    (ROOT / "samples/test_set_v1").mkdir(parents=True, exist_ok=True)
    write(ROOT / "config/excel_format.json", fmt)
    write(ROOT / "config/typicals.json", typicals)
    write(ROOT / "samples/test_set_v1/ground_truth.json", gt)

    print(f"\n[✓] config/excel_format.json      컬럼 {len(columns)}개")
    print(f"[✓] config/typicals.json          typical {len(typicals)}종")
    print(f"[✓] samples/test_set_v1/ground_truth.json  {len(rows)}행")
    src_count = collections.Counter(c["source"] for c in columns)
    print("\n[i] 컬럼 출처 분포:", dict(src_count))
    print(f"[i] 모델이 도면에서 판독할 컬럼: "
          f"{[c['key'] for c in columns if c['source'] == 'drawing']}")
    for w in warnings:
        print(f"[!] {w}")
    return 0


def write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
