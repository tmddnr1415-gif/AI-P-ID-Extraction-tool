"""Write deliverables by editing the client's own workbook, not by rebuilding it.

The client's Excel is not a table.  It is a form: a title block of four merged
rows, a two-level header, an autofilter, tuned column widths, and - below the
data - a numbered block of technical requirements that belongs to the
deliverable and must survive.  Five further sheets (PKG interface, cabling,
raceway, routing) sit alongside and have nothing to do with this tool.

So nothing here builds a workbook.  The uploaded file is copied byte for byte
and only the data rows inside it are replaced:

  * the data region is found by the config's `first_data_row` and by walking
    down while the NO column holds an integer, which is what stops at the blank
    line above the notes;
  * writing into existing rows keeps their formatting automatically;
  * if the new data is longer, rows are inserted *above* the note block and
    styled from the last original data row, so the notes move down intact;
  * if it is shorter, the surplus rows are cleared rather than deleted, again
    to leave the note block where it is;
  * every other sheet is untouched.

Output comes only from a revision snapshot (`app/db.py`), never from live data.
"""

from __future__ import annotations

import shutil
from copy import copy
from pathlib import Path

import openpyxl

# One entry per deliverable: which rows go in it and where its template's data
# lives.  Sheet name and column numbers are the client's, so they come from the
# project config rather than being written here.
DELIVERABLES = {
    "FIELD": {
        "title": "Field Instrument",
        "config": "excel",
        "sheet_key": "sheet",
        "tabs": ("FIELD",),
    },
    "BFV": {
        "title": "I&C Butterfly Valve",
        "config": "valves.excel",
        "sheet_key": "sheet",
        "tabs": ("BFV",),
    },
    "MOV": {
        "title": "MOV (Gate & Globe)",
        "config": "valves.excel",
        "sheet_key": "sheet",
        "tabs": ("MOV",),
    },
    "PNEUMATIC": {
        "title": "Control / Shutoff Valve",
        "config": "valves.excel",
        "sheet_key": "sheet",
        "tabs": ("PNEUMATIC",),
    },
    "MASTER": {
        "title": "Valve List (master)",
        "config": "valves.excel",
        "sheet_key": "sheet",
        "tabs": ("BFV", "MOV", "PNEUMATIC"),
    },
}


class TemplateMissing(RuntimeError):
    """Raised rather than inventing a layout for a deliverable with no template."""


def _cfg_columns(cfg, base: str) -> tuple:
    block = cfg.get(base)
    return str(block["sheet"]), int(block["first_data_row"]), dict(block["columns"])


def _last_data_row(ws, first_row: int, no_col: int) -> int:
    """Last row whose NO column is an integer: the data stops above the notes."""
    last = first_row - 1
    for r in range(first_row, ws.max_row + 1):
        v = ws.cell(r, no_col).value
        if isinstance(v, int):
            last = r
        elif last >= first_row:
            break                       # the blank line before the note block
    return last


def _clear_row(ws, row: int, columns) -> None:
    for c in columns:
        ws.cell(row, c).value = None


def _copy_style(ws, src_row: int, dst_row: int, columns) -> None:
    for c in columns:
        s, d = ws.cell(src_row, c), ws.cell(dst_row, c)
        d._style = copy(s._style)


def write_deliverable(template: Path, out_path: Path, rows: list, cfg,
                      kind: str) -> dict:
    """Fill one deliverable from snapshot rows.  Returns what was written."""
    spec = DELIVERABLES[kind]
    if template is None or not Path(template).exists():
        raise TemplateMissing(
            f"{kind}: no template uploaded.  This tool fills the client's own "
            f"workbook; it does not invent a layout, so nothing is written.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(template, out_path)          # keeps every byte we don't touch

    sheet, first_row, cols = _cfg_columns(cfg, spec["config"])
    wb = openpyxl.load_workbook(out_path)
    if sheet not in wb.sheetnames:
        raise TemplateMissing(f"{kind}: template has no sheet named '{sheet}'")
    ws = wb[sheet]

    no_col = int(cols["no"])
    used = sorted(int(v) for v in cols.values())
    last_row = _last_data_row(ws, first_row, no_col)
    template_rows = last_row - first_row + 1
    style_row = last_row if template_rows > 0 else first_row

    wanted = len(rows)
    if wanted > template_rows:
        extra = wanted - template_rows
        ws.insert_rows(last_row + 1, extra)
        for i in range(extra):
            _copy_style(ws, style_row, last_row + 1 + i, used)

    for i, row in enumerate(rows):
        r = first_row + i
        values = row["values"]
        ws.cell(r, no_col).value = i + 1
        for name, col in cols.items():
            if name == "no":
                continue
            ws.cell(r, int(col)).value = _value_for(name, row, values)

    # Anything left over from the template's own data is cleared, not deleted:
    # deleting would drag the note block up with it.
    for r in range(first_row + wanted, max(last_row, first_row + wanted) + 1):
        _clear_row(ws, r, used)

    if ws.auto_filter.ref:
        # Extend the filter over the new row count, keeping the template's own
        # column range.  Rebuilding it from `ws.max_column` widened it by one
        # column (AO -> AP on the instrument sheet) purely because openpyxl
        # counts a column the template leaves empty.
        from openpyxl.utils.cell import range_boundaries
        min_c, min_r, max_c, _ = range_boundaries(ws.auto_filter.ref)
        left = openpyxl.utils.get_column_letter(min_c)
        right = openpyxl.utils.get_column_letter(max_c)
        ws.auto_filter.ref = f"{left}{min_r}:{right}{first_row + max(wanted, 1) - 1}"

    wb.save(out_path)
    return {"kind": kind, "sheet": sheet, "rows": wanted,
            "template_rows": template_rows, "path": str(out_path)}


# How a snapshot row maps onto the client's column names.  Description and Tag
# No. come through as whatever a reviewer typed; the engine leaves them empty.
def _value_for(name: str, row: dict, values: dict):
    if name == "pid_no":
        return row.get("drawing_no") or None
    if name == "type":
        return values.get("type")
    if name == "valve_type":
        return values.get("valve_type")
    if name == "qty":
        return values.get("qty")
    if name == "system":
        return values.get("system")
    if name == "description":
        return values.get("description") or None
    return values.get(name)


def write_all(snapshot: dict, templates: dict, out_dir: Path, cfg) -> dict:
    """Write every deliverable a template was supplied for."""
    # The snapshot was already filtered to the chosen origins when it was
    # taken; this re-checks rather than trusting, because a snapshot is the
    # thing a delivered workbook is answerable to.
    origins = set(snapshot.get("origins_included") or [])
    by_tab: dict[str, list] = {}
    for row in snapshot["rows"]:
        if row.get("deleted"):
            continue
        if origins and row.get("origin") and row["origin"] not in origins:
            continue
        by_tab.setdefault(row["tab"], []).append(row)

    written, skipped = [], []
    for kind, spec in DELIVERABLES.items():
        rows = [r for tab in spec["tabs"] for r in by_tab.get(tab, [])]
        rows.sort(key=lambda r: (r["values"].get("system") or "",
                                 r["page_no"], r["key"]))
        template = templates.get(kind)
        name = f"{kind.lower()}_{Path(snapshot['pdf_name']).stem}.xlsx"
        try:
            written.append(write_deliverable(
                Path(template) if template else None, out_dir / name, rows, cfg, kind))
        except TemplateMissing as exc:
            skipped.append({"kind": kind, "rows": len(rows), "reason": str(exc)})
    return {"written": written, "skipped": skipped}
