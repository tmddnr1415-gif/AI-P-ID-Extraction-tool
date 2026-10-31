"""L58 — 알다프라(1A5J · 삼성 C&T) 양식 재현.

* `form: "a5j"` 그림은 모양 게이트(AND = 막대 + 빈 네모 · OR = 막대 + 원 · NOT = ⊠) · PB 칸 · ANN 타원 · LOGIC 머리글 · 삼성 타이틀블록으로
  내보내고, 분석기가 (범례 없이 학습 사전으로) 같은 종류 · 같은 단자 · 같은 시트 이름 · 제목으로 되읽는다.
* 막대 게이트 입력선은 막대의 그 높이에 그대로 닿는다 — 자석 자리로 옮겨 반 행 다리를 막대 위에 겹쳐 그리지 않는다
  (입력 29개 AND 가 신호원으로 읽히던 원인).
* 선 위 인터페이스 표시 ◆ ■ 는 분석 결과(`markers`)에 남고, 그림의 선에 `marks` 로 붙어 PDF 에 그대로 나가며, 다시 읽어도 표시로 읽힌다.
* 개정 삼각형의 숫자가 FM/TO 칸에 걸쳐 읽힌 것은 들여올 때 뺀다 · 교차 틈으로 끊긴 실선은 파선이 아니다 · 매크로 상자의 이름 줄과
  선 없는 단자도 그림에 실린다.
"""
from __future__ import annotations

import pymupdf

from app.logic import analyse, draw, draw_sets, geom, graph

N = 50
P = draw.PITCH


def ry(n):
    return draw.ry(n, N)


def _a5j_doc():
    doc = draw.new_doc("A5J", "tester", N=N)
    doc.update({"sheet_no": "FG_G-901", "title": "FUEL GAS TEST READY", "doc_no": "1A5J-00GEN00-J09-0002", "form": "a5j",
                "project_name": "AL DHAFRA POWER PLANT", "rev": "2", "project": "1A5J"})
    L, R = doc["left"], doc["right"]
    for n, d in {2: "MOV A OPND", 3: "MOV B OPND", 12: "CAB FLT", 7: "PERMIT A", 8: "PERMIT B", 10: "PB IN"}.items():
        L[str(n)] = {"fm": "FG_G-501-89" if n < 5 else "", "kks": "", "desc": d}
    R["51"] = {"desc": "SYSTEM RDY", "kks": "", "to": "FG_G-102-17"}      # 오른쪽 행 50+k 는 왼쪽 행 k 와 같은 높이
    R["53"] = {"desc": "NOT FLT", "kks": "", "to": ""}
    R["57"] = {"desc": "ALARM", "kks": "", "to": "HMI"}
    B, Wn = doc["blocks"], doc["wires"]
    aw, ah = draw.BASE_SIZES["AND"]
    ow, oh = draw.BASE_SIZES["OR"]
    nw_, nh = draw.BASE_SIZES["NOT"]
    LX0, LX1 = draw.LX0, draw.LX1
    # OR (행 2 · 3) → AND (행 2.5 와 7·8) → 출력 51
    B.append({"id": "OR1", "kind": "OR", "x": 420, "y": round(ry(2.5) - oh / 2, 2), "w": ow, "h": oh, "text": "OR", "label": "", "param": {"bar": [round(-0.5 * P, 2), round(oh + 0.5 * P, 2)]}})
    B.append({"id": "AND1", "kind": "AND", "x": 600, "y": round(ry(5) - ah / 2, 2), "w": aw, "h": ah, "text": "AND", "label": "",
              "param": {"bar": [round(ry(2.5) - ry(5) - 0.4 * P, 2), round(ry(8) - ry(5) + ah / 2 + 0.4 * P, 2)]}})
    B.append({"id": "NOT1", "kind": "NOT", "x": 480, "y": round(ry(12) - nh / 2, 2), "w": nw_, "h": nh, "text": "NOT", "label": "", "param": {}})
    B.append({"id": "PB1", "kind": "PB", "x": 420, "y": round(ry(10) - 4.5, 2), "w": 28, "h": 9, "text": "PB", "label": "AUTO", "param": {}})
    B.append({"id": "ANN1", "kind": "ANN", "x": 700, "y": round(ry(57) - 4.5, 2), "w": 18, "h": 9, "text": "ANN", "label": "", "param": {}})
    Wn.append({"id": "w1", "pts": [[LX0, ry(2)], [420, ry(2)]], "marks": [[LX0 + 0.6 * P, ry(2), "diamond"]]})
    Wn.append({"id": "w2", "pts": [[LX0, ry(3)], [420, ry(3)]]})
    Wn.append({"id": "w3", "pts": [[420 + ow, ry(2.5)], [600, ry(2.5)]]})
    Wn.append({"id": "w4", "pts": [[LX0, ry(7)], [600, ry(7)]]})
    Wn.append({"id": "w5", "pts": [[LX0, ry(8)], [600, ry(8)]]})
    Wn.append({"id": "w6", "pts": [[600 + aw, ry(5)], [760, ry(5)], [760, ry(51)], [LX1, ry(51)]], "marks": [[LX1 - 0.6 * P, ry(51), "square"]]})
    Wn.append({"id": "w7", "pts": [[LX0, ry(12)], [480, ry(12)]]})
    Wn.append({"id": "w8", "pts": [[480 + nw_, ry(12)], [840, ry(12)], [840, ry(53)], [LX1, ry(53)]]})
    Wn.append({"id": "w9", "pts": [[LX0, ry(10)], [420, ry(10)]]})
    Wn.append({"id": "w10", "pts": [[448, ry(10)], [690, ry(10)], [690, ry(57)], [700, ry(57)]]})
    Wn.append({"id": "w11", "pts": [[718, ry(57)], [LX1, ry(57)]]})
    doc.update(draw.clean(doc))
    return doc


def _blocks(sheet):
    return sorted((b.get("logic") or b.get("func")) for b in sheet["blocks"].values())


def test_a5j_form_shape_gates_round_trip_through_the_analyser():
    doc = _a5j_doc()
    assert doc["form"] == "a5j" and doc["project_name"] == "AL DHAFRA POWER PLANT"
    pdf = draw.to_pdf(doc)
    res = analyse.analyse(_tmp(pdf))
    s = res["sheets"][0]
    assert s["sheet_no"] == "FG_G-901"
    assert s["title"].endswith("FUEL GAS TEST READY")          # 한 장 묶음은 되풀이 줄(프로젝트 이름)을 못 뺀다 — 세 장부터 뺀다
    kinds = _blocks(s)
    assert kinds.count("and") == 1 and kinds.count("or") == 1 and kinds.count("not") == 1, kinds
    assert "source" in kinds and "sink" in kinds, kinds          # PB · ANN
    ins = {}
    for pt in s["ports"]:
        ins.setdefault(s["blocks"][pt["block"]].get("logic"), []).append(pt["dir"])
    assert ins["and"].count("in") == 3 and ins["or"].count("in") == 2
    rows = {(r["side"], r["n"]): r for r in s["table"] if r.get("desc")}
    assert rows[("L", 2)]["fm"] == "FG_G-501-89" and rows[("R", 51)]["to"] == "FG_G-102-17"
    # ◆ ■ 표시는 되읽어도 표시다 (선을 끊지 않는다)
    kinds_m = sorted(m[4] for m in s.get("markers") or [])
    assert kinds_m == ["diamond", "square"], kinds_m
    assert not s.get("dangling")


def test_shape_geometry_and_pb_cell_have_no_centre_text():
    # L67 — AND / OR 모양 게이트에는 가운데 글자를 단다 (사용자: 게이트에 AND · OR 표기) · 되읽기는 위 시험이 같은 종류로 확인한다
    doc = _a5j_doc()
    by = {b["id"]: b for b in doc["blocks"]}
    g = draw.shape_geometry(draw.block_geometry(by["AND1"]), by["AND1"])
    assert g["bar"] and g["box"] and [t for t in g["texts"] if t[2] == "AND"]
    g = draw.shape_geometry(draw.block_geometry(by["OR1"]), by["OR1"])
    assert [t for t in g["texts"] if t[2] == "OR"]
    assert g["circle"] and g["box"] is None and abs(g["circle"][0] - g["circle"][2] - by["OR1"]["x"]) < 1e-6   # 원 왼쪽 = 막대 x
    g = draw.shape_geometry(draw.block_geometry(by["NOT1"]), by["NOT1"])
    assert len(g["lines"]) == 2
    g = draw.shape_geometry(draw.block_geometry(by["PB1"]), by["PB1"])
    assert [t[2] for t in g["texts"]] == ["P", "B", "AUTO"] and g["lines"]
    g = draw.shape_geometry(draw.block_geometry(by["ANN1"]), by["ANN1"])
    assert g["ellipse"] and g["box"] is None
    # 기본 양식은 글자 그대로
    g0 = draw.block_geometry(by["AND1"])
    assert [t for t in g0["texts"] if t[2] == "AND"]


def _tmp(pdf_bytes):
    import tempfile
    f = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    f.write(pdf_bytes)
    f.close()
    return f.name


def test_bar_inputs_touch_the_bar_at_their_own_height():
    """from_sheet: 막대 게이트 입력은 막대의 그 높이에 닿는다 — 반 행 다리가 막대 위에 겹치지 않는다 (29입력 AND 가 신호원으로 읽히던 것)."""
    doc = _a5j_doc()
    res = analyse.analyse(_tmp(draw.to_pdf(doc)))
    s = res["sheets"][0]
    back = draw.from_sheet(s, "FG_G-901", "tester", "1A5J")
    and_ = next(b for b in back["blocks"] if b["kind"] == "AND")
    bar = draw.bar_of(and_)
    # 막대 x 위에 놓인 세로 토막은 없어야 한다 (막대 자신은 블록이 그린다)
    stubs = [w for w in back["wires"] if abs(w["pts"][0][0] - bar[0]) < 0.3 and abs(w["pts"][1][0] - bar[0]) < 0.3]
    assert not stubs, stubs
    res2 = analyse.analyse(_tmp(draw.to_pdf(back)))
    s2 = res2["sheets"][0]
    ins = [pt for pt in s2["ports"] if s2["blocks"][pt["block"]].get("logic") == "and" and pt["dir"] == "in"]
    assert len(ins) == 3


def test_from_sheet_drops_revision_marks_keeps_markers_and_solid_hopped_lines():
    s = {"page": 1, "sheet_no": "X1", "title": "T", "logic": [320.0, 70.0, 870.0, 736.7], "pitch": P, "frame": None,
         "table": [{"side": "L", "n": 1, "y0": 70.0, "y1": 70.0 + P, "fm": "2", "desc": "", "kks": ""},
                   {"side": "L", "n": 2, "y0": 70.0 + P, "y1": 70.0 + 2 * P, "fm": "G1-5", "desc": "REAL", "kks": ""},
                   {"side": "R", "n": 60, "y0": 70.0, "y1": 70.0 + P, "to": "2", "desc": "", "kks": ""}],
         "rows": [{"n": 2, "side": "L", "net": "1", "at": [320.0, ry(2)]}],
         "blocks": {}, "ports": [],
         "nets": {"1": {"segs": [[320.0, ry(2), 330.0, ry(2)], [333.0, ry(2), 400.0, ry(2)], [403.0, ry(2), 500.0, ry(2)]], "jumps": [], "dashed": True},
                  "2": {"segs": [[520.0, ry(4) + i * 2.8 * 2, 520.0, ry(4) + i * 2.8 * 2 + 2.8] for i in range(8)], "jumps": [], "dashed": True}},
         "markers": [[335.0, ry(2) - 3.5, 342.0, ry(2) + 3.5, "diamond"]], "dangling": [], "stray_arrows": []}
    doc = draw.from_sheet(s, "X1", "tester", "")
    assert "1" not in doc["left"] and "60" not in doc["right"] and doc["left"]["2"]["fm"] == "G1-5"
    ws = {w["id"]: w for w in doc["wires"]}
    assert all(not w["dashed"] for w in ws.values() if w["id"].startswith("n1_"))    # 교차 틈으로 끊긴 실선
    assert all(w["dashed"] for w in ws.values() if w["id"].startswith("n2_"))        # 짧은 토막뿐 = 진짜 파선
    marks = [m for w in doc["wires"] for m in (w.get("marks") or [])]
    assert marks and marks[0][2] == "diamond"


def test_macro_import_keeps_head_lines_and_unwired_pins():
    s = {"page": 1, "sheet_no": "X2", "title": "T", "logic": [320.0, 70.0, 870.0, 736.7], "pitch": P, "frame": None, "table": [], "rows": [],
         "nets": {"1": {"segs": [[320.0, ry(10), 500.0, ry(10)]], "jumps": [], "dashed": False}},
         "ports": [{"block": "M", "dir": "in", "at": [500.0, ry(10)], "net": "1"}],
         "blocks": {"M": {"kind": "RECT", "func": "MACRO", "logic": "macro", "bbox": [500.0, ry(3), 580.0, ry(14)], "label": "", "read": "",
                          "lines": [[ry(4) - 3, ry(4) + 3, 505.0, 520.0, "FG"], [ry(4) - 3, ry(4) + 3, 522.0, 545.0, "COMPR"], [ry(5) - 3, ry(5) + 3, 530.0, 545.0, "GRP"],
                                    [ry(8) - 3, ry(8) + 3, 502.0, 520.0, "A_MODE"], [ry(8) - 3, ry(8) + 3, 560.0, 578.0, "S_AUTO"],
                                    [ry(10) - 3, ry(10) + 3, 502.0, 520.0, "EN_STRT"], [ry(6) - 3, ry(6) + 3, 530.0, 536.0, "2"]],
                          "macro": {"sheet": "0012", "title": "MACRO GRP", "inputs": [{"at": "500.0,%s" % ry(10), "pin": "EN_STRT", "row": 19}], "outputs": []}}},
         "dangling": [], "stray_arrows": []}
    doc = draw.from_sheet(s, "X2", "tester", "")
    m = next(b for b in doc["blocks"] if b["kind"] == "MACRO")
    assert m["param"]["title"] == "FG COMPR | GRP"
    assert [q["name"] for q in m["param"]["pins_in"]] == ["A_MODE", "EN_STRT"]
    assert [q["name"] for q in m["param"]["pins_out"]] == ["S_AUTO"]
    g = draw.block_geometry(m)
    assert [t[2] for t in g["texts"][:2]] == ["FG COMPR", "GRP"] and g["texts"][0][3] > g["texts"][1][3]


def test_filled_small_square_item_is_a_marker_not_a_rect():
    """■ 를 PDF 라이브러리가 `re` 항목으로 접어도 인터페이스 표시로 읽는다 (3pt 미만의 칠한 조각은 예전처럼 버린다)."""
    pdf = pymupdf.open()
    page = pdf.new_page(width=300, height=200)
    for x, size in ((50.0, 6.0), (150.0, 1.4)):
        sh = page.new_shape()
        sh.draw_rect(pymupdf.Rect(x, 100 - size / 2, x + size, 100 + size / 2))
        sh.finish(color=(0, 0, 0), fill=(0, 0, 0), width=0)
        sh.commit()
    pr = geom.read(page, 1)
    assert len(pr.markers) == 1 and list(pr.marker_kind.values()) == ["square"]


def test_set_export_keeps_form_per_sheet():
    doc = _a5j_doc()
    doc2 = _a5j_doc()
    doc2["form"] = ""
    doc2["sheet_no"] = "FG_G-902"
    pdf = pymupdf.open(stream=draw_sets.to_pdf_set([doc, doc2]), filetype="pdf")
    t1, t2 = pdf[0].get_text(), pdf[1].get_text()
    assert "PROJECT DWG NO." in t1 and "LOGIC" in t1 and "PROJECT DWG NO." not in t2 and "SHEET NO." in t2
