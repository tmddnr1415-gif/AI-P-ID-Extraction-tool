"""hotfix82 — 식별 VOC 탭의 Excel (요약 · 식별 VOC · 누락 추가 · 출력 제외).

사용자: *"식별 VOC 탭을 만들어 … 식별되는 게 맞는지, 수량은 맞는지 O/X 로 표기하고 누락된 게 있으면 행추가로
마크업해서 식별되어야 한다는 것을 보여 줄 수 있고 그 결과는 저장 그리고 Excel 출력."*  여기서 판정하지 않는다 —
`row_verdict`(식별 O/X · 수량 O/X · 비고 · 평가자) 와 행(검출 · 사람이 더한 행 · 지운 행)을 그대로 옮겨 적는다.
발주처 양식(`excel_out`)과 다른 파일이다 — 그 양식에는 평가 열이 없다.
"""
from __future__ import annotations

import io
import time
from typing import Iterable

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

HEAD_FILL = PatternFill("solid", fgColor="EFE8D8")
FILL = {"O": "E3F1E6", "X": "F8E1DF", "ADDED": "FFF1D6"}

COLS = [("No", "no"), ("P&ID No.", "drawing_no"), ("쪽", "page_no"), ("탭", "tab"), ("Type", "type"),
        ("Tag No.", "tag_no"), ("Line No.", "line_no"), ("Line Size", "line_size"),
        ("Q'ty (도면)", "qty_ai"), ("Q'ty (사람)", "qty_user"), ("식별 O/X", "verdict"), ("수량 O/X", "qty_verdict"),
        ("평가자", "author"), ("평가 시각", "at"), ("비고", "note"), ("SCOPE", "scope"),
        ("출처", "origin"), ("출력", "output"), ("Description", "description")]


def _cell(row: dict, pages: dict, vx: dict, name: str, no: int):
    vals = row.get("values") or {}
    ai = row.get("ai") or {}
    user = row.get("user") or {}
    if name == "no":
        return no
    if name == "drawing_no":
        return pages.get(row.get("page_no")) or row.get("drawing_no") or ""
    if name in ("page_no", "tab"):
        return row.get(name)
    if name == "qty_ai":
        return ai.get("qty", vals.get("qty", ""))
    if name == "qty_user":
        return user.get("qty", "") if user.get("qty") is not None else ""
    if name in ("verdict", "qty_verdict", "author", "note"):
        return vx.get(name, "")
    if name == "at":
        t = vx.get("at")
        return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else ""
    if name == "origin":
        return "사람 추가 (마크업)" if row.get("added") else "검출"
    if name == "output":
        if row.get("deleted"):
            return "삭제"
        if row.get("removed"):
            return "제외 (X 또는 오검출)"
        return "출력"
    return vals.get(name, "")


def _sheet(wb, title: str, header: Iterable[str]):
    ws = wb.create_sheet(title)
    ws.append(list(header))
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = HEAD_FILL
    ws.freeze_panes = "A2"
    return ws


def _fill_rows(ws, rows, pages, vxs):
    for i, row in enumerate(rows, 1):
        vx = vxs.get(row["key"], {})
        ws.append([_cell(row, pages, vx, name, i) for _h, name in COLS])
        r = ws.max_row
        for ci, (_h, name) in enumerate(COLS, 1):
            if name in ("verdict", "qty_verdict") and vx.get(name) in FILL:
                ws.cell(r, ci).fill = PatternFill("solid", fgColor=FILL[vx[name]])
            if name == "origin" and row.get("added"):
                ws.cell(r, ci).fill = PatternFill("solid", fgColor=FILL["ADDED"])
    widths = {"A": 6, "B": 24, "C": 5, "D": 10, "E": 9, "F": 16, "G": 12, "H": 10, "I": 10, "J": 10,
              "K": 9, "L": 9, "M": 10, "N": 16, "O": 28, "P": 24, "Q": 16, "R": 18, "S": 60}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def build(job: dict, rows: list, pages: dict, vxs: dict, counts: dict) -> bytes:
    """워크북 바이트.  `rows` 는 `db.merged_rows(…, "ALL")`(지운 행 포함) · `vxs` 는 `db.verdicts`."""
    live = [r for r in rows if not r.get("deleted")]
    added = [r for r in live if r.get("added")]
    excluded = [r for r in live if r.get("removed")]
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "요약"
    lines = [
        ("프로젝트", job.get("project") or ""), ("리비전", job.get("revision") or ""),
        ("PDF", job.get("pdf_name") or ""), ("만든 시각", time.strftime("%Y-%m-%d %H:%M")),
        ("", ""),
        ("식별 행 (지운 행 제외)", len(live)),
        ("식별 O — 맞게 식별됨", counts.get("O", 0)),
        ("식별 X — 식별되면 안 됨 (출력에서 뺌)", counts.get("X", 0)),
        ("식별 미평가", counts.get("open", 0)),
        ("수량 O", counts.get("qty_O", 0)), ("수량 X — 수량이 틀림", counts.get("qty_X", 0)),
        ("누락 — 사람이 마크업으로 더한 행", len(added)),
        ("출력 제외 행 (X · 오검출 · 식별 지움)", len(excluded)),
        ("", ""),
        ("읽는 법", "식별 O/X 는 그 행이 식별되어야 하는가, 수량 O/X 는 Q'ty 가 맞는가.  "
                  "'사람 추가' 행은 프로그램이 못 읽어 사람이 더한 것 — 다음 학습의 누락 자료.  "
                  "평가는 VOC 함에 쌓여 개발이 읽는다 (spike/voc.py verdicts)."),
    ]
    for k, v in lines:
        ws.append([k, v])
    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 90
    ws["B15"].alignment = Alignment(wrap_text=True, vertical="top")
    for r in range(1, 14):
        ws.cell(r, 1).font = Font(bold=True)

    ws2 = _sheet(wb, "식별 VOC", [h for h, _n in COLS])
    _fill_rows(ws2, live, pages, vxs)
    ws3 = _sheet(wb, "누락 추가", [h for h, _n in COLS])
    _fill_rows(ws3, added, pages, vxs)
    ws4 = _sheet(wb, "출력 제외", [h for h, _n in COLS])
    _fill_rows(ws4, excluded, pages, vxs)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
