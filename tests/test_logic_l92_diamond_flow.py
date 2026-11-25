"""L92 — ① 열린 마름모 ◇ 기호(19VA 의 아날로그 설정 A · 전환 T)를 분석기가 블록으로 읽고, 작도가 같은 모양으로 그린다
② 그려진 차례에서 '다음 기호' 를 배운다 (draw_sets.learn_flow · GET /logic/api/drawings/{id}/flow).

19VA 827장 전체의 수(마름모 81개 · 재현 정확도)는 원본 PDF 로 `spike/fidelity_l89.py` 가 잰다 — 여기서는 작은 그림으로 규칙을 본다."""
import os
import tempfile
from pathlib import Path

from app.logic import analyse as AN
from app.logic import draw, draw_sets, draw_sim

P, T = draw.PITCH, draw.TOP


def _doc(blocks, wires, right=None):
    doc = draw.new_doc("p", "t", "", 59)
    doc["form"] = "a5j"
    doc["blocks"], doc["wires"] = blocks, wires
    doc["right"] = right or {}
    return {**doc, **draw.clean(doc)}


def _analyse(doc):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "d.pdf")
        open(p, "wb").write(draw.to_pdf(doc))
        return AN.analyse(p)["sheets"][0]


def _diamond_doc():
    y = T + 5 * P - P / 2
    return _doc([{"id": "b1", "kind": "BOX", "x": 400, "y": y - P, "w": 2 * P, "h": 2 * P, "text": "A", "label": "", "param": {"form": "diamond"}},
                 {"id": "b2", "kind": "BOX", "x": 520, "y": y - P, "w": 2 * P, "h": 2 * P, "text": "T", "label": "", "param": {"form": "diamond"}}],
                [{"id": "w1", "pts": [[400 + 2 * P, y], [520, y]]}, {"id": "w2", "pts": [[520 + 2 * P, y], [draw.LX1, y]]}],
                {str(59 + 5): {"desc": "OUT", "kks": "", "to": ""}})


def test_open_diamond_is_read_as_a_block_and_drawn_back_as_a_diamond():
    """◇ 안에 글자 = 블록 (예전엔 '선 위의 표시' 로 버려져 그 기호와 둘레 선 끝이 사라졌다 · 19VA HS10_P131 등 52장 81개)."""
    doc = _diamond_doc()
    assert [b["param"].get("form") for b in doc["blocks"]] == ["diamond", "diamond"]          # 저장(clean)이 모양을 지킨다
    g = draw.block_geometry(doc["blocks"][0])
    assert g["box"] and len(g["diamond"]) == 4 and g["diamond"][0] == [400 + P, doc["blocks"][0]["y"]]   # 상자(단자 자리)는 그대로 · 그리는 모양만 ◇
    s = _analyse(doc)
    got = {b.get("label"): b for b in s["blocks"].values()}
    assert set(got) == {"A", "T"} and all(b.get("form") == "diamond" and b["kind"] == "RECT" for b in got.values()), s["blocks"]
    assert got["A"]["func"] == "ANALOG SIGNAL GENERATOR" and got["T"]["func"] == "TRANSFER"    # 뜻은 안의 글자 (사전의 |A · |T)
    ports = {(next(k for k, v in s["blocks"].items() if v is b), q["dir"]): q["net"] for b in got.values() for q in s["ports"] if s["blocks"][q["block"]] is b}
    a_id = next(k for k, v in s["blocks"].items() if v is got["A"]); t_id = next(k for k, v in s["blocks"].items() if v is got["T"])
    assert ports[(a_id, "out")] == ports[(t_id, "in")] and (t_id, "out") in ports             # 꼭짓점에 닿은 선이 단자로 붙는다
    back = draw.from_sheet(s, "x", "t")
    assert [(b["kind"], b["text"], b["param"].get("form")) for b in back["blocks"]] == [("BOX", "A", "diamond"), ("BOX", "T", "diamond")]


def test_unknown_form_is_dropped_and_plain_boxes_stay_boxes():
    doc = _doc([{"id": "b1", "kind": "BOX", "x": 400, "y": 200, "w": 22, "h": 22, "text": "A", "label": "", "param": {"form": "star"}},
                {"id": "b2", "kind": "AND", "x": 500, "y": 200, "w": 14, "h": 22, "text": "AND", "label": "", "param": {"form": "diamond"}}], [])
    assert all("form" not in b["param"] for b in doc["blocks"])                                # 모르는 모양 · 글자 상자가 아닌 기호는 그대로
    assert "diamond" not in draw.block_geometry(doc["blocks"][0])


def test_small_tilted_square_without_text_is_not_a_block():
    """글자 없는 마름모 · 작은 마름모는 기호가 아니다 (선 위의 표시 ◆ ■ 는 예전 그대로)."""
    from app.logic import graph
    inside = lambda bb: True
    quad = lambda cx, cy, h: ([(cx, cy - h), (cx + h, cy), (cx, cy + h), (cx - h, cy)], False)
    word = lambda cx, cy, t: (cx - 2, cy - 3, cx + 2, cy + 3, t)
    found, _, _ = graph._open_diamonds([quad(100, 100, 11.3), quad(200, 100, 11.3), quad(300, 100, 3.0)], [], [word(100, 100, "A"), word(300, 100, "x")], [], 11.3, 0.9, inside)
    assert [[round(v) for v in bb] for bb in found] == [[89, 89, 111, 111]]                    # 글자 든 큰 것 하나만


def test_learn_flow_counts_what_follows_what():
    y = T + 3 * P - P / 2
    blocks = [{"id": "a", "kind": "NOT", "x": 380, "y": y - 4.5, "w": 9, "h": 9, "text": "NOT", "label": "", "param": {}},
              {"id": "b", "kind": "GT", "x": 380 + 9 + 4 * P, "y": y - P / 2, "w": 17.5, "h": P, "text": "GT", "label": "", "param": {"t": 5}},
              {"id": "c", "kind": "BOX", "x": 560, "y": y - P / 2, "w": 22, "h": P, "text": "H/", "label": "", "param": {}}]
    wires = [{"id": "w1", "pts": [[draw.LX0, y], [380, y]]}, {"id": "w2", "pts": [[389, y], [389 + 4 * P, y]]},
             {"id": "w3", "pts": [[389 + 4 * P + 17.5, y], [560, y]]}]
    docs = [_doc(blocks, wires) for _ in range(3)]
    sheets = [draw_sim.to_sheet({**d, "id": f"d{i}"}, i + 1) for i, d in enumerate(docs)]
    f = draw_sets.learn_flow(docs, sheets)
    assert f["next"]["k:NOT"] == [["k:GT", 3]] and f["next"]["k:GT"] == [["p:H/", 3]] and f["pairs"] == 6
    assert abs(f["gap_p"]["k:NOT"]["k:GT"] - 4.0) < 0.05                                      # 같은 행에서 곧게 이은 간격 (행 간격 배율)
    assert f["timer"]["GT"] == [[5.0, 3]]
    assert draw_sets.flow_key({"kind": "TEXT", "text": "x"}) is None and draw_sets.flow_key({"kind": "MACRO"}) is None


def test_shipped_flow_base_is_learned_from_the_held_diagrams():
    base = draw_sets.flow_base()
    assert base["pairs"] > 1000 and base["source"] and base["next"]["k:NOT"][0][0] == "k:AND"   # 들고 있는 19VA: NOT 뒤는 AND 가 가장 많다
    assert all(isinstance(n, int) and n > 0 for lst in base["next"].values() for _, n in lst)


def test_flow_endpoint_and_editor_wiring(tmp_path, monkeypatch):
    from tests.test_logic_l87_find import _client, _set_of_two
    c = _client(tmp_path, monkeypatch)
    sid, d1, d2 = _set_of_two(c)
    r = c.get(f"/logic/api/drawings/{d1}/flow")
    assert r.status_code == 200
    j = r.json()
    assert j["set"]["sheets"] == 2 and "next" in j["set"] and j["base"]["pairs"] > 1000
    root = Path(__file__).resolve().parents[1] / "app" / "static"
    main = (root / "logic_draw.js").read_text(encoding="utf-8")
    pal = (root / "logic_draw_palette.js").read_text(encoding="utf-8")
    for t in ("function flowNext(", "function flowTab(", "flowGap(flowKey(src), it.key)", "/flow`", 'form === "diamond"'):
        assert t in main, t
    assert "s-next" in pal and "st.next" in pal


def test_touching_diamonds_are_one_symbol_with_cells():
    """맞닿은 ◇ 한 쌍 = 한 기호 (범례 ◇A◇T = AUTO/MANUAL CONTROL STATION) — 칸 둘인 한 블록으로 읽고, 그림도 한 기호(칸 둘)로 그린다."""
    y = T + 6 * P - P / 2
    blk = {"id": "am", "kind": "BOX", "x": 500, "y": y - P, "w": 4 * P, "h": 2 * P, "text": "A | T", "label": "",
           "param": {"form": "diamond", "cells": [[0, 0, 0.5, 1, "A"], [0.5, 0, 0.5, 1, "T"]]}}
    doc = _doc([blk], [{"id": "w1", "pts": [[500 + 3 * P, y - P], [500 + 3 * P, y - 3 * P], [draw.LX0, y - 3 * P]], "arrow": "start"},
                       {"id": "w2", "pts": [[500 + 4 * P, y], [draw.LX1, y]]}],
               {str(59 + 6): {"desc": "OUT", "kks": "", "to": ""}})
    assert doc["blocks"][0]["param"]["cells"] == [[0, 0, 0.5, 1, "A"], [0.5, 0, 0.5, 1, "T"]]
    g = draw.block_geometry(doc["blocks"][0])
    assert len(g["diamonds"]) == 2 and sorted(t[2] for t in g["texts"]) == ["A", "T"]           # ◇ 둘 · 칸마다 글자
    sh = draw_sim.to_sheet({**doc, "id": "x"}, 1)                                              # 그림을 프로그램이 이해한 것
    assert sorted((q["dir"], q["side"], q["cell"]) for q in sh["ports"]) == [("in", "T", 1), ("out", "R", 1)]
    s = _analyse(doc)                                                                           # PDF 로 내보내 분석기가 다시 읽은 것
    (bid, b), = s["blocks"].items()
    assert b.get("form") == "diamond" and len(b["cells"]) == 2 and b["read"] == "A | T", b
    assert sorted((q["dir"], q["side"], q["cell"]) for q in s["ports"] if q["block"] == bid) == [("in", "T", 1), ("out", "R", 1)]
    back = draw.from_sheet(s, "x", "t")
    assert back["blocks"][0]["param"]["form"] == "diamond" and [c[4] for c in back["blocks"][0]["param"]["cells"]] == ["A", "T"]


def test_a5j_timers_and_lamp_are_drawn_the_way_the_held_diagrams_draw_them():
    """a5j 양식(19VA): 켜짐/꺼짐 지연 = 오른쪽이 둥근 상자에 ON/OFF · 펄스 = 상자 안 ⎍ · 표시등 = 원 + 네 귀 빗살.
    다시 그린 PDF 를 분석기가 원본과 같은 뜻 · 같은 시간으로 읽는다."""
    ys = [T + n * P - P / 2 for n in (3, 7, 11, 15)]
    blocks = [{"id": "g", "kind": "GT", "x": 450, "y": ys[0] - P / 2, "w": 1.51 * P, "h": P, "text": "GT", "label": "", "param": {"t": 15}},
              {"id": "d", "kind": "DT", "x": 450, "y": ys[1] - P / 2, "w": 1.51 * P, "h": P, "text": "DT", "label": "", "param": {"t": 2}},
              {"id": "p", "kind": "PD", "x": 450, "y": ys[2] - P / 2, "w": 1.15 * P, "h": P, "text": "PD", "label": "", "param": {"t": 1}},
              {"id": "l", "kind": "LAMP", "x": 450, "y": ys[3] - P / 2, "w": P, "h": P, "text": "G", "label": "", "param": {}}]
    wires = [{"id": f"w{i}", "pts": [[draw.LX0, y], [450, y]]} for i, y in enumerate(ys)] + \
            [{"id": f"o{i}", "pts": [[450 + w * P, y], [draw.LX1, y]]} for i, (y, w) in enumerate(zip(ys[:3], (1.51, 1.51, 1.15)))]
    doc = _doc(blocks, wires)
    g = draw.shape_geometry(draw.block_geometry(doc["blocks"][0]), doc["blocks"][0])
    assert g["shape"]["nobox"] and len(g["shape"]["arcs"]) == 2 and [t[2] for t in g["texts"]] == ["ON", "15 SEC"]
    p = draw.shape_geometry(draw.block_geometry(doc["blocks"][2]), doc["blocks"][2])
    assert not p["shape"]["nobox"] and len(p["shape"]["paths"][0]) == 6 and [t[2] for t in p["texts"]] == ["1 SEC"]
    lamp = draw.shape_geometry(draw.block_geometry(doc["blocks"][3]), doc["blocks"][3])
    assert len(lamp["lines"]) == 4
    s = _analyse(doc)
    got = {b["func"]: b for b in s["blocks"].values()}
    assert got["GT"]["logic"] == "delay_on" and got["GT"]["param"]["t"] == 15 and got["GT"]["label"] == "ON"
    assert got["DT"]["logic"] == "delay_off" and got["DT"]["param"]["t"] == 2
    assert got["PD"]["logic"] == "pulse" and got["PD"]["param"]["t"] == 1
    assert got["LIGHT"]["kind"] == "CIRCLE" and not s.get("dangling")                          # 빗살이 매달린 선으로 읽히지 않는다
