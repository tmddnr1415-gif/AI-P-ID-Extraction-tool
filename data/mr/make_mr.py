# 사용: python data/mr/make_mr.py <ItemKey> [values.json] [--type ESDV]
# ItemKey: DCS IPS MMS CCS FGS BallValve GlobeValve ButterflyValve PSV FieldGauge Transmitter BulkMaterial
# values.json: {"필드명": {"value":"..","source":"문서/Rev/절","status":"확인|미확인"}}  (Item 에이전트 출력)
import sys, json, os, datetime
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_COLOR_INDEX, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DIMMAP = {"BallValve":"BallValve_ESDV","GlobeValve":"GlobeValve_Control","ButterflyValve":"ButterflyValve_Control","PSV":"PSV",
          "Transmitter":"Transmitter","FieldGauge":"FieldGauge","BulkMaterial":"BulkMaterial","DCS":"DCS","IPS":"IPS","MMS":"MMS","CCS":"CCS","FGS":"FGS"}
BLUE = RGBColor(0x14,0x28,0xA0)

def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement("w:shd")
    s.set(qn("w:val"),"clear"); s.set(qn("w:color"),"auto"); s.set(qn("w:fill"),hexcolor); tcPr.append(s)

def put(cell, value, status="미확인"):
    cell.text = ""; p = cell.paragraphs[0]; r = p.add_run(str(value)); r.font.size = Pt(9.5)
    if status != "확인" or str(value).strip() in ("", "미확인"):
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW

def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    key = a[0]; vals = json.load(open(a[1], encoding="utf-8")) if len(a) > 1 else {}
    fmt = json.load(open(os.path.join(HERE, f"MR_Format_{key}.json"), encoding="utf-8"))
    d = Document()
    for s in d.sections: s.left_margin = s.right_margin = Cm(2); s.top_margin = s.bottom_margin = Cm(2)
    st = d.styles["Normal"]; st.font.name = "맑은 고딕"; st.element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕"); st.font.size = Pt(10)
    # 머리글/바닥글
    hp = d.sections[0].header.paragraphs[0]; hr = hp.add_run("DRAFT — 초안, 담당자 확인·승인 전 발행 금지"); hr.bold = True; hr.font.color.rgb = RGBColor(0xC0,0,0); hr.font.size = Pt(9)
    fp = d.sections[0].footer.paragraphs[0]; fp.add_run(f"MR {fmt['item']} — 계측제어 통합 사양 검토 멀티에이전트 자동 생성 초안").font.size = Pt(8)
    t = d.add_paragraph(); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("MATERIAL REQUISITION (초안)"); r.bold = True; r.font.size = Pt(18); r.font.color.rgb = BLUE
    t2 = d.add_paragraph(); t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t2.add_run(f"{fmt['item']}  /  Type: {', '.join(fmt['types'])}").font.size = Pt(11)
    if fmt["safety"]:
        b = d.add_paragraph(); br = b.add_run("⚠ 안전 계통 — 초안, 담당자 확인 필수. 확정 표현 금지. SIS 담당자 검토 후 사용."); br.bold = True; br.font.color.rgb = RGBColor(0xC0,0,0)
    # 표지 표
    tb = d.add_table(rows=0, cols=2); tb.style = "Table Grid"
    today = datetime.date.today().strftime("%Y-%m-%d")
    for h in fmt["header"]:
        c = tb.add_row().cells; c[0].text = h; shade(c[0], "E8EBF8"); c[0].paragraphs[0].runs[0].bold = True
        if h == "Date": put(c[1], today, "확인")
        elif h.startswith(("검토","승인")): c[1].text = ""   # 사람이 서명 — 비움
        elif h.startswith("작성"): put(c[1], "AI 초안 (담당자 지정 필요)", "미확인")
        elif h.startswith("Item"): put(c[1], f"{fmt['item']} / {', '.join(fmt['types'])}", "확인")
        else: put(c[1], vals.get(h, {}).get("value", "미확인"), vals.get(h, {}).get("status", "미확인"))
    for sec in fmt["sections"]:
        h = d.add_heading(sec["title"], level=2)
        for r in h.runs: r.font.color.rgb = BLUE; r.font.name = "맑은 고딕"
        if sec["id"] == "tech":
            dimf = os.path.join(ROOT, "data", "dim", f"Dim_{DIMMAP[key]}.json")
            rows = []
            if os.path.exists(dimf):
                dj = json.load(open(dimf, encoding="utf-8"))
                for k, v in dj.get("dims", {}).items():
                    rows.append((f"치수/Dim: {k}", v if not isinstance(v, dict) else v.get("value", "미확인"), "Dim_" + DIMMAP[key] + ".json(벤더·표준 참고, 프로젝트 Spec 대조 필요)"))
            for f in ["Design Pressure/Temp", "Service/Fluid", "재질(Body/Trim)", "Tag/수량"]:
                rows.append((f, vals.get(f, {}).get("value", "미확인"), vals.get(f, {}).get("source", "")))
            tab = d.add_table(rows=1, cols=3); tab.style = "Table Grid"
            for i, x in enumerate(["항목", "값", "출처(문서·Rev·절)"]):
                tab.rows[0].cells[i].text = x; shade(tab.rows[0].cells[i], "1428A0")
                rr = tab.rows[0].cells[i].paragraphs[0].runs[0]; rr.bold = True; rr.font.color.rgb = RGBColor(255,255,255)
            for f, v, s in rows:
                c = tab.add_row().cells; c[0].text = f; put(c[1], v, "확인" if v not in ("", "미확인") and not isinstance(v,(dict,list)) and vals.get(f,{}).get("status")=="확인" else "미확인"); c[2].text = s
            continue
        tab = d.add_table(rows=1, cols=3); tab.style = "Table Grid"
        for i, x in enumerate(["요구 항목", "내용", "출처·상태"]):
            tab.rows[0].cells[i].text = x; shade(tab.rows[0].cells[i], "E8EBF8"); tab.rows[0].cells[i].paragraphs[0].runs[0].bold = True
        for f in sec["fields"]:
            v = vals.get(f, {}); c = tab.add_row().cells; c[0].text = f
            put(c[1], v.get("value", "미확인"), v.get("status", "미확인")); c[2].text = v.get("source", "프로젝트 Spec 대조 필요")
    if fmt.get("note"): d.add_paragraph().add_run("비고: " + fmt["note"]).italic = True
    d.add_heading("승인 (사람 서명 — 자동 발행 금지)", level=2)
    ap = d.add_table(rows=2, cols=3); ap.style = "Table Grid"
    for i, x in enumerate(["작성", "검토", "승인"]): ap.rows[0].cells[i].text = x; shade(ap.rows[0].cells[i], "E8EBF8")
    d.add_heading("양식 근거 (웹 검토, " + today + ")", level=2)
    for s in fmt["sources"]: d.add_paragraph(f"{s['title']} — {s['url']}", style="List Bullet").runs[0].font.size = Pt(8.5)
    d.add_paragraph("※ 위 자료는 일반 MR 구성 파악용이다. 회사 MR 양식·승인 조항은 미확인이며, 노란색 칸은 근거 없음/미확인을 뜻한다.").runs[0].font.size = Pt(8.5)
    out = os.path.join(ROOT, "output", f"MR_{key}_{datetime.date.today():%Y%m%d}_DRAFT.docx")
    d.save(out); d.save(os.path.join(ROOT,"output",f"MR_{key}_latest_DRAFT.docx")); print(out)
main()
