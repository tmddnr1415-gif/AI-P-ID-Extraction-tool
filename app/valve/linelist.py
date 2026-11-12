"""Process Line List (xlsx) — one row per line: Line No → Pipe Class · Size · Fluid Phase · Density · Design/Operating P·T.

The header is found on the sheet itself (the row whose first cell says 'LINE NUMBER'; the two rows under it carry the
sub-captions and units).  Columns are named by those captions, never by letter, because North and South sheets differ:
in one of them the 'MM' and 'INCH' columns hold each other's values — the size cell is therefore read by what it says
(a value with '"' is inches, a bare number is millimetres), not by which column it sits in.

Line numbers are written differently per area ('AG1442-24"(1C3AS-A)E(47.25)' · '12DHC-1001-2"-1C3AS2-A-N').  A line is
matched by its full key (letters + digits only) or, failing that, by its 'core' — the part before the size ('AG1442',
'12DHC-1001') — and the match is said in the result.
"""
from __future__ import annotations

import io
import re

import openpyxl

_CAPS = [  # (words that must all be in the joined caption, key)
    (("LINE", "NUMBER"), "line_no"), (("REVISION",), "rev"), (("SERVICE",), "service"), (("LINE", "SIZE", "MM"), "size_mm"),
    (("LINE", "SIZE", "INCH"), "size_inch"), (("PIPE", "CLASS"), "pipe_class"), (("P&ID",), "pid_no"), (("FROM",), "from"),
    (("TO",), "to"), (("FLUID", "PHASE"), "phase"), (("FLUID", "DENSITY"), "density"),
    (("DESIGN", "PRESSURE"), "design_p"), (("DESIGN", "TEMPERATURE", "MAX"), "design_t_max"),
    (("DESIGN", "TEMPERATURE", "MIN"), "design_t_min"), (("OPERATING", "PRESSURE"), "op_p"),
    (("OPERATING", "TEMPERATURE"), "op_t"), (("TEST", "PRESSURE"), "test_p"), (("REMARKS",), "remarks"),
]
_SIZE = re.compile(r"-\s*\d+(?:\.\d+)?\s*(?:\"|”|'')")


def key(s: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", str(s or "").upper())


def core(line_no: str) -> str:
    """'AG1442-24"(1C3AS-A)E(47.25)' → 'AG1442' · '12DHC-1001-2"-1C3AS2-A-N' → '12DHC1001'."""
    s = str(line_no or "").upper()
    m = _SIZE.search(s)
    return key(s[:m.start()]) if m else ""


def _txt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return re.sub(r"\s+", " ", str(v)).strip()


def _caption_of(cols: list[list[str]]) -> dict[int, str]:
    """Header caption per column: a merged parent caption carries to the right until the next one."""
    out, parent = {}, ["", "", ""]
    for c, parts in enumerate(cols):
        for r in range(3):
            if parts[r]:
                parent[r] = parts[r]
                for q in range(r + 1, 3):
                    parent[q] = ""
        out[c] = " ".join(p for p in parent if p).upper()
    return out


def read(data: bytes, filename: str = "") -> dict:
    """→ {sheets: [{sheet, header_row, rows: n}], lines: [{line_no, key, core, sheet, row, …}], by_key, by_core}."""
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    lines, sheets = [], []
    for ws in wb.worksheets:
        hdr = None
        for r in range(1, min(ws.max_row, 40) + 1):
            if _txt(ws.cell(r, 1).value).upper().startswith("LINE NUMBER"):
                hdr = r
                break
        if not hdr:
            continue
        ncol = min(ws.max_column, 60)
        cols = [[_txt(ws.cell(hdr + k, c).value) for k in range(3)] for c in range(1, ncol + 1)]
        cap = _caption_of(cols)
        colkey = {}
        for c, text in cap.items():
            words = set(re.findall(r"[A-Z&]+", text))
            for need, k in _CAPS:
                if k not in colkey.values() and all(n in words for n in need):
                    if k == "line_no" and c != 0:
                        continue
                    if k in ("to", "from") and len(words) > 2:
                        continue
                    colkey[c] = k
                    break
        n = 0
        for r in range(hdr + 3, ws.max_row + 1):
            a = _txt(ws.cell(r, 1).value)
            if not a:
                continue
            if a.upper().startswith("NOTE"):
                break
            row = {"line_no": a, "key": key(a), "core": core(a), "sheet": ws.title, "row": r}
            for c, k in colkey.items():
                if k != "line_no":
                    row[k] = _txt(ws.cell(r, c + 1).value)
            sizes = [row.pop("size_mm", ""), row.pop("size_inch", "")]  # read by what the cell says (one area swaps them)
            row["size_inch"] = next((s for s in sizes if '"' in s), "")
            row["size_mm"] = next((s for s in sizes if s and '"' not in s), "")
            lines.append(row)
            n += 1
        sheets.append({"sheet": ws.title, "header_row": hdr, "rows": n, "columns": sorted(set(colkey.values()))})
    by_key, by_core = {}, {}
    for i, ln in enumerate(lines):
        by_key.setdefault(ln["key"], i)
        if ln["core"]:
            by_core.setdefault(ln["core"], []).append(i)
    return {"file": filename, "sheets": sheets, "lines": lines, "by_key": by_key, "by_core": by_core}


def find(ll: dict, line_no: str) -> tuple[dict | None, str]:
    """(line row, how) for a datasheet's line number — '' how when the full number matched."""
    if not ll or not line_no:
        return None, ""
    k = key(line_no)
    if k in ll["by_key"]:
        return ll["lines"][ll["by_key"][k]], ""
    c = core(line_no) or k
    hits = ll["by_core"].get(c, [])
    if len(hits) == 1:
        return ll["lines"][hits[0]], f"Line No 앞부분 '{c}' 로 찾음 (전체 번호는 다름: Line List '{ll['lines'][hits[0]]['line_no']}')"
    if len(hits) > 1:
        return None, f"Line No 앞부분 '{c}' 인 줄이 {len(hits)}개 — 전체 번호로 구분할 수 없음"
    for kk, i in ll["by_key"].items():                    # datasheet wrote only the core ('AG1442')
        if kk.startswith(k) and len(k) >= 5 and ll["lines"][i]["core"] == k:
            return ll["lines"][i], f"Datasheet 는 앞부분 '{line_no}' 만 적음 → Line List '{ll['lines'][i]['line_no']}'"
    return None, ""
