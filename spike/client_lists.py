"""발주처 정답지 파서 — 세 리스트를 (P&ID No. · 항목) 단위로 읽는다.

검증 전용이다.  실사용 입력은 PDF + 빈 양식뿐이고, 이 파일이 읽는
`data/*.xlsx` 는 리포지터리에 없다 (.gitignore).  그러므로 이 스크립트는
발주처 자료를 가진 기계에서만 돌아가고, 없으면 그렇게 말하고 멈춘다.

취소선은 두 경로로 본다.  openpyxl 이 셀에 붙은 폰트만 보여 주므로, 문자열
안의 일부 글자에만 취소선이 걸린 경우를 놓친다.  그래서 xl/styles.xml 의
cellXfs -> fontId -> strike 도 직접 읽어 두 결과를 합친다 (둘 중 하나라도
취소선이면 취소선).
"""
import collections
import re
import zipfile
import xml.etree.ElementTree as ET

import openpyxl

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

FILES = {
    "FIELD": ("data/CZE_Field_Instrument.xlsx", "2.0_Instrument List",
              {"pid": 7, "type": 8, "qty": 9, "desc": 10, "system": 6}),
    "BFV": ("data/CZI_Butterfly_Valve.xlsx", "3.0_Valve List", None),
    "MOV": ("data/CZH_MOV_Gate_Globe.xlsx", "3.0_Valve List", None),
}


def _strike_rows(path, sheet_name):
    """Row numbers whose data cells carry a struck font, read from styles.xml."""
    with zipfile.ZipFile(path) as z:
        styles = ET.fromstring(z.read("xl/styles.xml"))
        fonts = [f.find(NS + "strike") is not None
                 for f in styles.find(NS + "fonts")]
        xfs = [int(x.get("fontId", 0))
               for x in styles.find(NS + "cellXfs")]
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid = {s.get("name"): s.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            for s in wb.find(NS + "sheets")}[sheet_name]
        target = {r.get("Id"): r.get("Target") for r in rels}[rid]
        target = "xl/" + target.lstrip("/").replace("worksheets/", "worksheets/") \
            if not target.startswith("xl/") else target
        sheet = ET.fromstring(z.read(target))
    out = set()
    for row in sheet.iter(NS + "row"):
        n = int(row.get("r"))
        for c in row.iter(NS + "c"):
            s = c.get("s")
            if s is not None and fonts[xfs[int(s)]]:
                out.add(n)
                break
    return out


def _cols(ws):
    """Find the header columns by name rather than by position."""
    want = {"P&ID NO.": "pid", "TYPE": "type", "Q'TY": "qty",
            "DESCRIPTION": "desc", "SYSTEM": "system", "NO": "no",
            "VALVE TYPE": "valve_type", "ACTUATOR": "actuator",
            "UNIT NO.": "unit", "OPERATION MODE": "opmode"}
    cols = {}
    for r in (5, 6, 7):
        for c in range(1, ws.max_column + 1):
            v = ws.cell(r, c).value
            if isinstance(v, str):
                key = want.get(v.strip().replace("\n", " ").upper())
                if key and key not in cols:
                    cols[key] = c
    return cols


def load(kind):
    path, sheet, _ = FILES[kind]
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet]
    cols = _cols(ws)
    struck_xml = _strike_rows(path, sheet)
    rows = []
    for r in range(8, ws.max_row + 1):
        no = ws.cell(r, 1).value
        if not isinstance(no, int):
            continue
        strike = r in struck_xml or any(
            ws.cell(r, c).font and ws.cell(r, c).font.strike
            for c in range(1, ws.max_column + 1))
        rec = {"row": r, "no": no, "strike": bool(strike), "kind": kind}
        for name, c in cols.items():
            v = ws.cell(r, c).value
            rec[name] = v.strip() if isinstance(v, str) else v
        rows.append(rec)
    return rows, cols


if __name__ == "__main__":
    for kind in FILES:
        rows, cols = load(kind)
        struck = [r for r in rows if r["strike"]]
        print(f"{kind}: {len(rows)}행  취소선 {len(struck)}  열 {cols}")
        pid = collections.Counter(r.get("pid") for r in rows if not r["strike"])
        print(f"   P&ID No. {len(pid)}종")
        if kind == "FIELD":
            t = collections.Counter(r["type"] for r in rows if not r["strike"])
            print(f"   TYPE {dict(t.most_common(12))}")
            pi = [r for r in rows if not r["strike"] and r["type"] == "PI"]
            print(f"   PI {len(pi)}행, 도면별 "
                  f"{dict(collections.Counter(r['pid'] for r in pi))}")
