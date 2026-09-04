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
from openpyxl.styles import Font, PatternFill

from app import pipeline           # TYPE 표기(`type_display`) 한 곳에서만 만든다

# 개정 표기.  세 곳(리스트 · 도면 · Excel)이 같은 낱말과 같은 색을 쓰도록
# 상태 이름은 `app/revisions.py` 것을 그대로 받아 쓴다.
REVISION_FILL = {
    "ADDED": PatternFill("solid", fgColor="FFF2A8"),      # 노랑
    "MODIFIED": PatternFill("solid", fgColor="CDEFD3"),   # 연녹
}
DELETED_FILL = PatternFill("solid", fgColor="F6C9C6")     # 붉은 기 — 취소선과 같이

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


def _clear_row(ws, row: int, last_col: int) -> None:
    """Empty one data row across *every* column, not only the mapped ones.

    Clearing only the mapped columns is what let the template's own values ride
    out under our rows: a column the config does not map kept whatever the
    client had at that row number, and that row is now a different instrument.
    Measured on AL NOUF1 before this changed: 14,121 cells in 65 columns, so an
    ACW pump row carried 601.9 degC, P92 chrome steel and STEAM.

    Values only.  Borders, alignment and number formats are the form's and stay.
    """
    for c in range(1, last_col + 1):
        ws.cell(row, c).value = None


def _mark_revision(ws, r: int, last_col: int, row: dict, marked: dict) -> None:
    """개정 표기.  Rev.A 는 여기서 아무것도 하지 않는다.

    상태가 없거나 BASELINE·UNCHANGED 이면 칠하지 않는다 - Rev.A 산출물에
    음영과 취소선이 하나도 없어야 한다는 조건이 그것이다.  삭제는 **사용자가
    확정한 것만** 여기 들어온다 (`deleted_confirmed`); 확정 전 '삭제 후보' 는
    산출물에 나가지 않는다.
    """
    state = (row.get("rev") or {}).get("state") or ""
    if row.get("deleted_confirmed"):
        for c in range(1, last_col + 1):
            cell = ws.cell(r, c)
            cell.fill = DELETED_FILL
            f = cell.font
            cell.font = Font(name=f.name, size=f.size, bold=f.bold,
                             italic=f.italic, color=f.color, strike=True)
        marked["DELETED"] += 1
        return
    fill = REVISION_FILL.get(state)
    if fill is None:
        return
    for c in range(1, last_col + 1):
        ws.cell(r, c).fill = fill
    marked[state] += 1


def _apply_style(ws, row: int, style) -> None:
    """Give one row the data region's formatting, column by column."""
    for i, st in enumerate(style, start=1):
        ws.cell(row, i)._style = copy(st)


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
    last_col = ws.max_column
    last_row = _last_data_row(ws, first_row, no_col)
    template_rows = last_row - first_row + 1
    style_row = last_row if template_rows > 0 else first_row

    # The row's formatting is read *before* any insertion.  A blank form has no
    # row whose NO column holds an integer, so `template_rows` is 0 and every row
    # is inserted at `first_row` - which pushes the one formatted row out of the
    # way before it can be copied from, and the data region comes out with no
    # borders at all.  Taking the style first makes the blank form work.
    style = [ws.cell(style_row, c)._style for c in range(1, last_col + 1)]

    wanted = len(rows)
    if wanted > template_rows:
        extra = wanted - template_rows
        ws.insert_rows(last_row + 1, extra)
        for i in range(extra):
            _apply_style(ws, last_row + 1 + i, style)

    marked = {"ADDED": 0, "MODIFIED": 0, "DELETED": 0}
    for i, row in enumerate(rows):
        r = first_row + i
        values = row["values"]
        # Every column first, so nothing of the template's own data survives
        # under a row that is now a different instrument, then our values on top.
        _clear_row(ws, r, last_col)
        # NO: the row's own number when the revision layer has given it one,
        # NO 는 **이 파일 안에서** 1부터 이어진다 (11회차).
        #
        # `excel_no`(리비전을 넘어 고정되는 번호)는 위 정렬에서 **자리**를 정하는
        # 데 그대로 쓰이고, 여기 찍히는 숫자만 달라진다.  발주처 양식이 이제
        # SCOPE=SCT 만 담으므로(`in_client_scope`), 고정 번호를 그대로 찍으면
        # 1 · 3 · 7 처럼 구멍 난 표가 나간다 — 발주처가 받는 것은 리스트이지
        # 우리 내부 대장이 아니다.
        #
        # §7.3 의 "확정 삭제 행은 원래 NO 를 유지한다"와 다른 이야기다: 그쪽은
        # 리비전 사이의 정체성이고, 이것은 한 파일의 출력 범위다.  삭제 행은
        # 여전히 `excel_no` 가 정한 **자리**에 남는다.
        ws.cell(r, no_col).value = i + 1
        for name, col in cols.items():
            if name == "no":
                continue
            ws.cell(r, int(col)).value = _value_for(name, row, values)
        _mark_revision(ws, r, last_col, row, marked)

    # Anything left over from the template's own data is cleared, not deleted:
    # deleting would drag the note block up with it.
    for r in range(first_row + wanted, max(last_row, first_row + wanted) + 1):
        _clear_row(ws, r, last_col)

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

    # A value a reviewer typed that this deliverable's form has no column for.
    # It cannot be written anywhere, so it is named rather than dropped in
    # silence - e.g. Vendor Supply, which no form carries a column for (the
    # instrument form's 'Scope of Supply' takes `scope` since the 10th round,
    # because that is the value the client asked that column to hold).
    mapped = set(cols) | {"body", "actuator"}
    unmapped: dict[str, int] = {}
    for row in rows:
        for field, value in (row.get("user") or {}).items():
            if value in (None, ""):
                continue
            if field in mapped:
                continue
            if field == "type" and "body" in cols:
                continue
            if field == "valve_type" and "actuator" in cols:
                continue
            unmapped[field] = unmapped.get(field, 0) + 1

    wb.save(out_path)
    return {"kind": kind, "sheet": sheet, "rows": wanted,
            "template_rows": template_rows, "path": str(out_path),
            "revision_marks": marked,
            "unmapped_values": unmapped}


# How a snapshot row maps onto the client's column names.  Description and Tag
# No. come through as whatever a reviewer typed; the engine leaves them empty.
def _value_for(name: str, row: dict, values: dict):
    if name == "pid_no":
        return row.get("drawing_no") or None
    # The client's own column names, mapped to what the app read.
    if name == "body":
        # 10회차: 도면이 버블에 인쇄한 기능 문자가 있으면 `MOV(GLOBE)` 로 적는다
        # (사용자 요구).  판정값은 그대로이고 여기서 표기만 만든다 —
        # `pipeline.type_display` 머리 주석에 왜 저장 필드가 아닌지 적어 두었다.
        return pipeline.type_display(values, row.get("evidence")) or None
    if name == "actuator":
        return values.get("valve_type") or None    # MOTOR / HYDRAULIC
    if name == "valve_type":
        # Column C's MOV / MOV_I / HOV vocabulary; the app does not produce it,
        # so it is left for a reviewer rather than guessed from the actuator.
        return values.get("valve_type_code") or None
    if name == "remark":
        return _remark(row, values)
    if name == "type":
        return pipeline.type_display(values, row.get("evidence")) or None
    return values.get(name) or None


def _remark(row: dict, values: dict):
    """The client's REMARK column: why this row was flagged, and what was decided.

    The column is the client's own - both templates print REMARK in row 6 - so
    this is filling a column they asked for rather than adding one.  What goes in
    is the axis the reason belongs to, the reason, and the reviewer's decision,
    because a remark that says only "확인 필요" is not something the client can
    act on.  A row nobody flagged and nobody touched gets an empty cell.
    """
    codes = row.get("review_codes") or []
    # A folded signal stack is not a flag - nobody has to decide anything - but
    # the row now stands for bubbles the reader can count on the drawing and will
    # not find in the list.  So it says which signals it covers, on every row,
    # whether or not anything else was flagged.
    members = (row.get("evidence") or {}).get("signal_members") or []
    fold = (f"맞닿은 신호 버블 {len(members)}개 = 물리 기기 1개 "
            f"({' / '.join(members)})") if len(members) > 1 else None
    if not codes:
        # Nothing was flagged: whatever the reviewer typed in the Remark box is
        # theirs and goes through untouched, with the fold noted beside it.
        typed = values.get("remark") or None
        return " · ".join([p for p in (fold, typed) if p]) or None
    states = row.get("review_state") or {}
    labels = row.get("review_label") or {}
    parts = []
    for code in codes:
        axis = (row.get("review_axis") or {}).get(code) or "검토"
        state = (states.get(code) or {}).get("state") or "미처리"
        parts.append(f"[{axis}] {labels.get(code, code)} → "
                     f"{REVIEW_STATE_KO.get(state, state)}")
    # A cell is read at a glance, so it carries the question and the answer.  The
    # engine's full reasoning is on the review screen, where there is room for it.
    return " · ".join(([fold] if fold else []) + parts)


REVIEW_STATE_KO = {"CONFIRMED": "확인함", "EDITED": "수정함", "HELD": "보류",
                   "미처리": "미처리"}


# --------------------------------------------------------------------------
# Blank forms
# --------------------------------------------------------------------------
#
# A template is a *form*, and the client's own list is a filled-in one.  Filling
# a filled-in form is what produced 14,121 cells of somebody else's design data
# riding out under our rows, so the form is emptied once and that empty copy is
# what the app fills.
#
# What is emptied is the data region's values, all columns.  What is kept is
# everything else: rows 1-7, the note block, the five side sheets, the merged
# ranges, the column widths, the autofilter, and the data region's borders,
# alignment and number formats.
#
# Two things in the data region are *also* cleared, and this is a decision rather
# than housekeeping - see `KEEP_WORKING_MARKS`.

# Whether the client's own working marks stay in the blank form.
#
# Measured on AL NOUF1's three workbooks: there is no grey attribute shading in
# any of them.  The only fills in the data region are green FF92D050 and yellow
# FFFF00, they sit on scattered single cells and whole rows rather than on
# columns, and they do not line up with the strikethrough rows.  They are the
# client's own working annotation - the kind the round called "손으로 넣은 음영,
# 발주처 규칙이 아니다" - and a deliverable that carried them would open with
# shading and strikethrough on rows they were never about.
#
# So they are cleared, which is what "Rev.A 출력에는 음영·취소선이 하나도 없어야
# 한다" requires.  Set this True to keep them instead; nothing else changes.
KEEP_WORKING_MARKS = False


def blank_form(src: Path, out: Path, sheet: str, first_row: int = 8,
               no_col: int = 1) -> dict:
    """Copy a workbook and empty its data region, keeping the form."""
    from openpyxl.styles import Font, PatternFill

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out)
    wb = openpyxl.load_workbook(out)
    ws = wb[sheet]
    last_row = _last_data_row(ws, first_row, no_col)
    last_col = ws.max_column
    cleared = fills = strikes = 0
    for r in range(first_row, last_row + 1):
        for c in range(1, last_col + 1):
            cell = ws.cell(r, c)
            if cell.value not in (None, ""):
                cell.value = None
                cleared += 1
            if KEEP_WORKING_MARKS:
                continue
            if cell.fill is not None and cell.fill.patternType is not None:
                cell.fill = PatternFill(fill_type=None)
                fills += 1
            if cell.font is not None and cell.font.strike:
                f = copy(cell.font)
                f.strike = False
                cell.font = f
                strikes += 1
    wb.save(out)
    return {"src": str(src), "out": str(out), "sheet": sheet,
            "data_rows": last_row - first_row + 1, "columns": last_col,
            "values_cleared": cleared, "fills_cleared": fills,
            "strikes_cleared": strikes}


# 발주처 양식에 담기는 SCOPE (11회차, 사용자 결정).
#
# "검출은 전부 한다 · 표기는 SCOPE 열이 한다 · **출력은 SCT 만**".  화면 · DB ·
# 검토 UI 는 1029행 전량을 그대로 들고 있고, 여기서만 거른다 — 발주처 양식은
# 발주처가 발주한 범위의 문서이고, 타사 공급분은 그 문서에 들어갈 자리가 없다.
#
# 왜 검출 단계에서 지우지 않는가: 지우면 도면에 그려진 것과 화면이 어긋나
# 검토자가 "이건 왜 없나"를 물을 수 없게 된다.  10회차가 벤더 마크를 행 삭제가
# 아니라 열 표기로 옮긴 것과 같은 판단이다.
#
# 안정 ID 는 **1029행 전량에 부여된 그대로**다.  걸러진 행의 ID 를 회수하거나
# 다시 매기지 않는다 (`app/revisions.py` — Rev.A 에서 한 번만 부여).  거르는
# 것은 출력 범위이지 행의 정체가 아니다.
SCOPE_DELIVERED = "SCT"


def in_client_scope(row: dict) -> bool:
    """이 행이 발주처 양식에 들어가는가.

    `SCT` 면 담고, **다른 값이 적혀 있으면** 뺀다.  값이 **아예 없는** 행은
    담는다 — "타사 공급"이 아니라 "아직 판정한 적 없음"이기 때문이다.

    빈 값을 빼지 않는 이유는 실측으로 드러났다: SCOPE 열이 없던 회차에 저장된
    분석(회사 PC 의 기존 결과가 그렇다)은 모든 행의 scope 가 빈 문자열이라,
    빈 값을 빼면 **발주처 양식 네 개가 통째로 빈 파일로 나간다** (UI 스위트가
    실 DB 사본으로 돌다가 `rows: 0` 으로 잡아냈다).  없는 판정을 "타사 공급"
    으로 읽는 것은 근거 없는 값 생성이다.

    담긴 옛 행이 몇 개인지는 MANIFEST 의 `legacy_no_scope_rows` 에 실려 나가고,
    거기에 숫자가 있으면 **다시 분석해야 한다**는 뜻이다.
    """
    scope = str((row.get("values") or {}).get("scope") or "").strip()
    return scope in ("", SCOPE_DELIVERED)


def scope_state(row: dict) -> str:
    """`in_client_scope` 가 어느 갈래로 판정했는지 — 집계용."""
    scope = str((row.get("values") or {}).get("scope") or "").strip()
    return ("delivered" if scope == SCOPE_DELIVERED
            else "legacy" if not scope else "out_of_scope")


def write_all(snapshot: dict, templates: dict, out_dir: Path, cfg) -> dict:
    """Write every deliverable a template was supplied for."""
    # The snapshot was already filtered to the chosen origins when it was
    # taken; this re-checks rather than trusting, because a snapshot is the
    # thing a delivered workbook is answerable to.
    origins = set(snapshot.get("origins_included") or [])
    by_tab: dict[str, list] = {}
    scope_counts: dict[str, int] = {}
    for row in snapshot["rows"]:
        if row.get("deleted"):
            continue
        if origins and row.get("origin") and row["origin"] not in origins:
            continue
        state = scope_state(row)
        scope_counts[state] = scope_counts.get(state, 0) + 1
        if not in_client_scope(row):
            continue
        by_tab.setdefault(row["tab"], []).append(row)
    # 확정된 삭제 행은 원래 자리에 남는다 - 표 끝으로 모으지 않는다.  자리를
    # 정하는 것은 그 행이 처음 받은 NO 이고, 아래 정렬이 그것을 쓴다.
    for row in snapshot.get("deleted_rows") or []:
        by_tab.setdefault(row["tab"], []).append(row)

    written, skipped = [], []
    for kind, spec in DELIVERABLES.items():
        rows = [r for tab in spec["tabs"] for r in by_tab.get(tab, [])]
        # 번호를 받은 행은 그 번호가 자리를 정한다.  아직 못 받은 행(리비전을
        # 안 쓰는 분석)은 예전 순서 그대로 - 그래야 리비전 이전과 이후의
        # Rev.A 산출물이 같은 순서로 나온다.
        rows.sort(key=lambda r: (0, r["excel_no"], "", 0, "")
                  if r.get("excel_no") else
                  (1, 0, r["values"].get("system") or "", r["page_no"], r["key"]))
        template = templates.get(kind)
        name = f"{kind.lower()}_{Path(snapshot['pdf_name']).stem}.xlsx"
        try:
            written.append(write_deliverable(
                Path(template) if template else None, out_dir / name, rows, cfg, kind))
        except TemplateMissing as exc:
            skipped.append({"kind": kind, "rows": len(rows), "reason": str(exc)})
    return {"written": written, "skipped": skipped,
            "scope_filter": SCOPE_DELIVERED,
            "out_of_scope_rows": scope_counts.get("out_of_scope", 0),
            # 0 이 아니면 그 분석은 SCOPE 열이 생기기 전 것이다 — 다시 분석해야
            # 발주처 양식이 제 범위로 나온다.
            "legacy_no_scope_rows": scope_counts.get("legacy", 0)}
