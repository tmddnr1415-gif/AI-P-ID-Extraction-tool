"""L89 — 분석한 Logic 을 불러와 똑같이 그리기: 정확도를 올린 고침들.

전체 정확도(19VA 827장 · 블록 · 표 · 연결 · 선 · 글 · 되읽기/직접)는 `spike/fidelity_l89.py` 가 원본 PDF 로 잰다 (저장소에 원본이 없어 여기서는
그 고침 하나하나를 작은 그림으로 확인한다)."""
import os
import tempfile

import pymupdf

from app.logic import analyse as AN
from app.logic import draw, draw_sim


def test_weld_moves_offset_junction_onto_the_line():
    """가로 행 선이 세로 선 옆 0.76pt 에서 끝나고 세로 조각의 끝도 가로 선에서 0.78pt 비켜 선 접합 (19VA CO01_P003) → 한 점으로."""
    segs = [[320.0, 120.98, 598.53, 120.98], [598.53, 120.98, 870.0, 120.98],
            [597.77, 120.2, 597.77, 91.22], [597.77, 120.2, 597.77, 165.56]]
    out = draw._weld(segs, terms=[(320.0, 120.98), (870.0, 120.98)])
    assert out[0][2] == 597.77 and out[1][0] == 597.77            # 가로 끝 → 세로 선 위로 (좌우로만)
    assert out[2][1] == 120.98 and out[3][1] == 120.98            # 세로 끝 → 가로 선 위로 (위아래로만)
    assert out[0][0] == 320.0 and out[1][2] == 870.0              # 행 자리 끝은 그대로
    assert all(abs(s[1] - s[3]) < 1e-9 or abs(s[0] - s[2]) < 1e-9 for s in out)   # 곧은 채


def test_weld_leaves_far_ends_and_terminals():
    segs = [[400.0, 100.0, 450.0, 100.0], [452.0, 80.0, 452.0, 120.0]]   # 2pt — 규칙(1.2pt)보다 멀다
    assert draw._weld(segs, terms=[]) == segs
    segs = [[400.0, 100.0, 451.0, 100.0], [451.8, 80.0, 451.8, 120.0]]
    assert draw._weld(segs, terms=[(451.0, 100.0)]) == segs       # 단자 끝은 옮기지 않는다


def _analyse(doc):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "d.pdf")
        open(p, "wb").write(draw.to_pdf({**doc, **draw.clean(doc)}))
        return AN.analyse(p)["sheets"][0]


def test_dashed_lines_are_not_box_edges():
    """분석기가 흩어진 선분 넷으로 상자를 짓는 규칙(_assemble_rects)은 파선을 쓰지 않는다 — 기호 테두리는 실선이다.
    (선 무늬로 그린 파선 신호선 넷이 네모를 둘러싸 없는 AND 가 읽혔다 · 19VA BL10_P303 등 13장)"""
    from app.logic import geom, graph
    P = 11.3
    x0, x1, y0, y1 = 497.75, 508.86, 291.05, 336.41

    def poly(a, b, dashed):
        sg = geom.Seg(a[0], a[1], b[0], b[1])
        return geom.Poly([sg], (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])), dashed=dashed)
    edges = [((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, y1))]
    solid = graph._assemble_rects([poly(a, b, False) for a, b in edges], [], P, 0.5)
    dashed = graph._assemble_rects([poly(a, b, True) for a, b in edges], [], P, 0.5)
    assert len(solid[0]) == 1 and dashed[0] == []                 # (상자들, 쓴 선) — 실선 넷은 상자 · 파선 넷은 아니다


def test_dashed_signal_lines_do_not_make_a_phantom_gate():
    """되읽기 보호 — 다시 그린 19VA BL10_P303 의 파선 토막 자리에서 없는 게이트가 읽히지 않는다 (그 장 전체 맥락의 재현은
    spike/fidelity_l89.py · 규칙 자체는 위 test_dashed_lines_are_not_box_edges 가 본다)."""
    doc = draw.new_doc("p", "t", "", 59)
    doc["form"] = "a5j"
    # 다시 그린 19VA BL10_P303 의 그 자리 그대로 (분석 그물 34 · 52 의 선 토막)
    doc["wires"] = [
        {"id": "n34_255", "pts": [[497.75, 336.41], [353.3, 336.41]], "dashed": True},
        {"id": "n34_277", "pts": [[508.86, 336.41], [497.75, 336.41]], "dashed": True},
        {"id": "n34_297", "pts": [[600.54, 336.41], [508.86, 336.41]], "dashed": True},
        {"id": "n52_127", "pts": [[497.75, 597.2], [497.75, 291.05], [508.86, 291.05]], "dashed": True},
        {"id": "n52_137", "pts": [[528.33, 291.05], [508.86, 291.05]], "dashed": True},
    ]
    s = _analyse(doc)
    assert not any(b.get("func") in ("AND", "OR") for b in s["blocks"].values()), s["blocks"]


def _src_page(texts):
    pdf = pymupdf.open()
    pg = pdf.new_page(width=draw.W, height=draw.H)
    for x, y, t in texts:
        pg.insert_text((x, y), t, fontsize=4.5, fontname="helv")
    return pdf, pg


def _sheet():
    P, T = draw.PITCH, draw.TOP
    return {"page": 1, "sheet_no": "S1", "title": "", "pitch": P, "logic": [draw.LX0, T, draw.LX1, T + 59 * P],
            "table": [{"side": "L", "n": 1, "y0": T, "y1": T + P}, {"side": "R", "n": 60, "y0": T, "y1": T + P}],
            "rows": [], "nets": {}, "ports": [],
            "blocks": {"B1": {"kind": "RECT", "func": "SIGNAL MONITOR", "logic": "monitor", "label": "H/", "read": "H/", "bbox": [500.0, 200.0, 522.0, 211.0],
                              "param": {"sp_text": "HH : 145degC", "sp": 145}},
                       "B2": {"kind": "RECT", "func": "TRANSFER", "logic": "", "label": "T", "read": "T", "bbox": [600.0, 300.0, 612.0, 312.0], "param": {}}}}


def test_source_texts_copied_at_their_place():
    """원본 쪽 LOGIC 영역의 글 — 단자 이름 · 주석은 그 자리 그 글로 · 기호 상자 안 글은 기호가 그린다 · 설정값 글은 위 글 대신 원본 자리에."""
    s = _sheet()
    pdf, pg = _src_page([(560.0, 298.0, "IN1"), (603.0, 307.5, "T"), (530.0, 197.0, "HH : 145degC"), (700.0, 400.0, "NOTE.2")])
    doc = draw.from_sheet(s, "S1", "t", page=pg)
    tx = {b["text"]: b for b in doc["blocks"] if b["kind"] == "TEXT"}
    assert "IN1" in tx and "NOTE.2" in tx and "T" not in tx        # 상자 안 'T' 는 기호 글
    M = draw.sheet_maps(s)
    b = tx["IN1"]
    assert abs(b["x"] + b["w"] / 2 - M["X"](560.0 + pymupdf.get_text_length("IN1", "helv", 4.5) / 2)) < 1.5
    mon = next(b for b in doc["blocks"] if b["id"] == "B1")
    assert "HH : 145degC" in tx and not (mon.get("param") or {}).get("above")   # 설정값 글은 원본 자리로 · 위 글은 거둔다
    pdf.close()


def test_drawing_sim_reads_setpoint_from_free_text():
    """옮긴 설정값 글(TEXT)도 작성 시뮬레이션이 읽는다 — 분석기처럼 쪽의 모든 글로."""
    s = _sheet()
    pdf, pg = _src_page([(530.0, 197.0, "HH : 145degC")])
    doc = draw.from_sheet(s, "S1", "t", page=pg)
    sh = draw_sim.to_sheet({**doc, "id": "x"}, 1)
    mon = next(b for b in sh["blocks"].values() if b.get("func") == "SIGNAL MONITOR" or (b.get("param") or {}).get("sp") is not None)
    assert (mon.get("param") or {}).get("sp") == 145
    pdf.close()


def test_no_page_keeps_rule_based_pin_texts():
    """원본 PDF 가 없을 때(예전 길)는 예전처럼 규칙 자리의 입력 이름 (L85 _aop_texts) — 위 글도 그대로."""
    s = _sheet()
    doc = draw.from_sheet(s, "S1", "t")
    mon = next(b for b in doc["blocks"] if b["id"] == "B1")
    assert (mon.get("param") or {}).get("above") == "HH : 145degC"
