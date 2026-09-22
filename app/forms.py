"""Make the blank forms the exporter fills.

    python3 -m app.forms

Reads the client's workbooks from `data/` and writes emptied copies to
`data/blank/`.  Neither directory is in the repository: both hold the client's
material, and the blank copy is still the client's form.

`excel_out.blank_form` does the work and says what it cleared; this is only the
place that names which file goes with which deliverable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import excel_out                                   # noqa: E402

SOURCES = {
    "FIELD": ("data/CZE_Field_Instrument.xlsx", "2.0_Instrument List"),
    "BFV": ("data/CZI_Butterfly_Valve.xlsx", "3.0_Valve List"),
    "MOV": ("data/CZH_MOV_Gate_Globe.xlsx", "3.0_Valve List"),
}


def main() -> int:
    out_dir = ROOT / "data" / "blank"
    missing = []
    for kind, (rel, sheet) in SOURCES.items():
        src = ROOT / rel
        if not src.exists():
            missing.append(rel)
            print(f"{kind}: 원본 없음 {rel}")
            continue
        info = excel_out.blank_form(src, out_dir / f"{kind}.xlsx", sheet)
        print(f"{kind}: {Path(info['src']).name} -> {Path(info['out']).name}  "
              f"데이터 {info['data_rows']}행 x {info['columns']}열, "
              f"값 {info['values_cleared']}칸 · 음영 {info['fills_cleared']}칸 · "
              f"취소선 {info['strikes_cleared']}칸 제거")
    if missing:
        print(f"\n원본이 없어 만들지 못한 양식: {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
