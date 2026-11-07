"""hotfix133 — 내보내는 엑셀: `=` 로 시작하는 글은 글 그대로 · 제어 문자는 빼고 멈추지 않는다."""
import io

import openpyxl
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE

from app import verdict_export, xlsx_safe

EVIL = '=HYPERLINK("http://x","열기")'


def _reload(raw: bytes):
    return openpyxl.load_workbook(io.BytesIO(raw))


def test_same_rule_as_openpyxl():
    assert xlsx_safe.ILLEGAL_CHARACTERS_RE.pattern == ILLEGAL_CHARACTERS_RE.pattern


def test_append_keeps_formula_like_text_as_text():
    wb = openpyxl.Workbook()
    ws = wb.active
    xlsx_safe.append(ws, [EVIL, "FT\x01-101", 3, None])
    b = io.BytesIO()
    wb.save(b)
    c = _reload(b.getvalue()).active
    assert c["A1"].value == EVIL and c["A1"].data_type == "s"
    assert c["B1"].value == "FT-101"
    assert c["C1"].value == 3


def test_put_leaves_template_formulas_alone():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "=SUM(B1:B2)"              # 발주처 양식에 원래 있던 수식
    xlsx_safe.put(ws["C1"], "=FT-101")    # 우리가 쓰는 칸
    assert ws["A1"].data_type == "f"
    assert ws["C1"].data_type == "s" and ws["C1"].value == "=FT-101"


def test_verdict_export_with_evil_note_and_control_char():
    rows = [{"key": "k1", "page_no": 1, "values": {"tag_no": "FT\x02-101", "type": "FT"}}]
    vxs = {"k1": {"verdict": "O", "note": EVIL, "author": "홍길동"}}
    raw = verdict_export.build({"project": "P", "pdf_name": "a.pdf"}, rows, {1: "D-001"}, vxs, {})
    wb = _reload(raw)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                assert cell.data_type != "f"
    vals = [c.value for ws in wb.worksheets for row in ws.iter_rows() for c in row]
    assert EVIL in vals and "FT-101" in vals
