"""L94 — 모든 기호가 동작해야 한다: 19VA 827장의 기호 8,719개 가운데 동작이 없던 것(146)을 줄인 규칙들.

전체 수는 원본 PDF 로 다시 분석해 센다 (기록 logic_log.md L94) — 여기서는 규칙마다 작은 예로 본다."""
import json
import os
import tempfile

from app.logic import analyse as AN
from app.logic import aops, draw

P, T = draw.PITCH, draw.TOP


def test_auto_manual_station_passes_the_input_or_the_manual_value():
    """범례 ◇A◇T AUTO/MANUAL CONTROL STATION — 자동이면 들어온 값을 그대로, 사람이 넣은 수동 값이 있으면 그 값."""
    b = {"func": "AUTO/MANUAL CONTROL STATION", "logic": "unknown", "label": "T A", "param": {}}
    assert aops.op_of(b) == "amstation" and aops.info("amstation")["ko"]
    ins = [("6", None), ("5", {"name": "SP"})]
    v, why = aops.compute("amstation", b, ins, {"5": 42.0, "6": 1.0})
    assert v == 42.0 and "자동" in why                                   # 이름이 SP 인 입력을 먼저
    assert aops.compute("amstation", b, ins, {"6": 7.0})[0] == 7.0       # 없으면 값이 있는 첫 입력
    assert aops.compute("amstation", b, ins, {})[0] is None
    man = {**b, "param": {"a_user": {"out": 55.0}}}
    assert aops.compute("amstation", man, ins, {"5": 42.0})[0] == 55.0   # 수동 값 (사람이 넣은 출력값)


def test_limit_named_by_the_printed_parameter():
    """안 그림을 못 맞댄 기호라도 바로 옆에 `LL : 0` · `HL : 4` 가 인쇄돼 있으면 하한 · 상한 제한이고 그 값으로 계산한다."""
    def sheet(text):
        return {"pitch": 11.3, "blocks": {"B1": {"func": "UNKNOWN", "logic": "unknown", "label": "?", "bbox": [627, 389, 649, 406], "param": {}}},
                "ports": [{"block": "B1", "net": "1", "dir": "in", "at": [627, 397.6]}, {"block": "B1", "net": "2", "dir": "out", "at": [649, 397.6]}]}, \
               [(651 + 9 * i, 390, 658 + 9 * i, 396, w, 0, 0, i) for i, w in enumerate(text.split())]
    s, ws = sheet("LL : 0")
    aops.read_pins(s, ws)
    b = s["blocks"]["B1"]
    assert aops.op_of(b) == "lolim" and b["param"]["a_drawing"]["l"]["v"] == 0.0
    assert aops.compute("lolim", b, [("1", None)], {"1": -5.0})[0] == 0.0 and aops.compute("lolim", b, [("1", None)], {"1": 7.0})[0] == 7.0
    s, ws = sheet("HL : 4")
    aops.read_pins(s, ws)
    b = s["blocks"]["B1"]
    assert aops.op_of(b) == "hilim" and aops.compute("hilim", b, [("1", None)], {"1": 9.0})[0] == 4.0
    s, ws = sheet("K : 2")                                               # 다른 이름은 연산을 정하지 않는다
    aops.read_pins(s, ws)
    assert aops.op_of(s["blocks"]["B1"]) is None


def _analyse(doc, edit=None):
    import pymupdf
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "d.pdf")
        d = pymupdf.open(stream=draw.to_pdf(doc), filetype="pdf")
        if edit:
            edit(d[0])
        d.save(p)
        return AN.analyse(p)["sheets"][0]


def _doc(blocks, wires, left=None, right=None):
    doc = draw.new_doc("p", "t", "", 59)
    doc["form"] = "a5j"
    doc["blocks"], doc["wires"] = blocks, wires
    doc["left"], doc["right"] = left or {}, right or {}
    return {**doc, **draw.clean(doc)}


def test_pulse_box_with_a_line_on_one_side_only_is_still_a_pulse():
    """⎍ 상자의 출력 파선이 상자에 닿지 못해도(선이 한쪽만 붙어도) 펄스로 읽는다 — '판정 못 함' 으로 남지 않는다."""
    y = T + 3 * P - P / 2
    doc = _doc([{"id": "p", "kind": "PD", "x": 500, "y": y - P / 2, "w": 1.15 * P, "h": P, "text": "PD", "label": "", "param": {"t": 1}}],
               [{"id": "w1", "pts": [[draw.LX0, y], [500, y]]}], {"3": {"fm": "", "kks": "", "desc": "IN"}})
    s = _analyse(doc)
    (bid, b), = s["blocks"].items()
    assert b["logic"] == "pulse" and [q["dir"] for q in s["ports"] if q["block"] == bid] == ["in"]


def test_open_circle_on_a_continuous_line_is_a_mark_not_an_unknown_symbol():
    """선이 끊기지 않고 지나가는 속 빈 작은 원 — 기능이 아니라 그 선 위의 표시다 (19VA ST10_G009 의 ○ 14개)."""
    import pymupdf
    y = T + 4 * P - P / 2
    doc = _doc([], [{"id": "w1", "pts": [[draw.LX0, y], [draw.LX1, y]]}], {"4": {"fm": "", "kks": "", "desc": "A"}}, {str(59 + 4): {"desc": "A OUT", "kks": "", "to": ""}})

    def edit(pg):
        sh = pg.new_shape()
        sh.draw_circle(pymupdf.Point(560, y), 0.3 * P)
        sh.finish(color=(0, 0, 0), width=0.71)
        sh.commit()
    s = _analyse(doc, edit)
    assert not s["blocks"] and len(s["nets"]) == 1 and len(s["rows"]) == 2


def test_stroke_letter_figures_are_in_the_shipped_library():
    """글자를 선으로 그린 기호(19VA Typical 의 T · DEV · AVG)를 들고 있는 도면에서 배워 사전 씨앗에 실었다."""
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "logic_library.json")
    L = json.load(open(root, encoding="utf-8"))
    learned = {f["name"]: f for f in L["figures"] if "L94" in (f.get("from") or "")}
    assert set(learned) == {"TRANSFER", "DEVIATION", "AVERAGE", "LOW LIMITING"} and all(len(f["fig"]) > 10 for f in learned.values())
    assert aops.name_op("TRANSFER") == "transfer" and aops.name_op("AVERAGE") == "mean"
