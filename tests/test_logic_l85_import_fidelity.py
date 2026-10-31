"""L85 — 분석 시트 → 그림 들여오기가 시뮬레이션 뜻을 잃지 않는다 (19VA 846쪽 차등 시뮬레이션에서 찾은 것).

같은 장을 분석 결과(검토 화면)와 다시 그린 그림(Logic 작성)으로 같은 입력을 넣어 돌리면 출력 행 42,850개 중 386개가 달랐다 → 62.
남은 것은 분석 쪽이 막대 게이트 · 파선 입력을 잘못 읽은 것 (원본 PDF 로 확인)."""
from app.logic import draw as D
from app.logic import draw_sim as DS
from app.logic import aops, sim


def _doc(blocks, wires, left=None, right=None, N=62):
    return {"N": N, "form": "a5j", "blocks": blocks, "wires": wires, "left": left or {}, "right": right or {}}


def _box(bid, x, y, text, w=22.0, h=17.0, **param):
    return {"id": bid, "kind": "BOX", "x": x, "y": y, "w": w, "h": h, "text": text, "label": "", "param": dict(param)}


def test_number_text_keeps_digits():
    assert D._numtxt(99999999.9999) == "99999999.9999" and D._numtxt(5.0) == "5" and D._numtxt(-1) == "-1"


def test_figure_operator_becomes_symbol_box():
    assert D._fig_symbol({"aop": "diff"}) in ("△", "Δ", "∆")
    assert D._fig_symbol({"param": {"aop_fig": {"op": "integral"}}}) == "∫"
    assert D._fig_symbol({}) == ""


def test_reversed_constant_drives_its_line():
    """상수 'A' 의 선이 블록 쪽으로 들어오게 그려져도(화살을 거꾸로) 상수가 그 선을 몬다 — 표시 글자(DISPLAY)가 아니다."""
    y = D.ry(10, 62)
    a = _box("B1", 500.0, y - 8.5, "A")
    w = {"id": "w1", "pts": [[400.0, y], [500.0, y]]}               # A 의 왼쪽 변에 닿는 선 — 변 규칙으로는 '입력'
    s = DS.to_sheet(_doc([a, {**_box("B2", 378.0, y - 8.5, "X")}], [w]), 1, {})
    assert s["blocks"]["B1"]["func"] != "DISPLAY"
    assert [p["dir"] for p in s["ports"] if p["block"] == "B1"] == ["out"]
    aops.identify([s])
    assert s["blocks"]["B1"].get("aop") == "const"


def test_top_bottom_line_direction_follows_arrow():
    """위 · 아래 변에 닿은 선 — 화살이 다른 끝에만 있으면 이 블록에서 나가는 선."""
    y = D.ry(10, 62)
    a = _box("B1", 500.0, y - 8.5, "A")
    b = _box("B2", 500.0, y + 40.0, "∑")
    w = {"id": "w1", "pts": [[511.0, y + 8.5], [511.0, y + 40.0]], "arrow": "end"}
    s = DS.to_sheet(_doc([a, b], [w]), 1, {})
    dirs = {(p["block"], p["side"]): p["dir"] for p in s["ports"]}
    assert dirs[("B1", "B")] == "out" and dirs[("B2", "T")] == "in"


def test_vertical_not_gets_its_output_at_the_bottom():
    """세로로 놓인 게이트: 화살 없이 위로 들어와 아래로 나가면 아래가 출력 (나가는 선이 하나도 없을 때만)."""
    y = D.ry(20, 62)
    g = {"id": "G1", "kind": "NOT", "x": 500.0, "y": y, "w": 9.0, "h": 9.0, "text": "", "label": "", "param": {}}
    top = {"id": "w1", "pts": [[504.5, y - 30.0], [504.5, y]]}
    bot = {"id": "w2", "pts": [[504.5, y + 9.0], [504.5, y + 40.0]]}
    s = DS.to_sheet(_doc([g], [top, bot]), 1, {})
    dirs = {p["side"]: p["dir"] for p in s["ports"] if p["block"] == "G1"}
    assert dirs.get("T") == "in" and dirs.get("B") == "out"


def test_monitor_is_imported_as_monitor_with_setpoint():
    """감시 블록(H/ · B.Q)은 운전 버튼(PB)이 아니다 — 설정값 글이 위에 남고 시뮬레이션이 같은 함수로 읽는다."""
    m = DS._block(_box("B1", 500, 300, "H/", above="HH : 64m"))
    assert m["func"] == "SIGNAL MONITOR"
    q = DS._block(_box("B2", 500, 300, "B.Q", mon=1))
    assert q["func"] == "SIGNAL MONITOR"
    cl = D.clean(_doc([_box("B2", 500, 300, "B.Q", mon=1)], []))
    assert cl["blocks"][0]["param"].get("mon") == 1                # 저장해도 남는다


def test_pin_names_round_trip_through_text():
    """분석이 읽은 입력 이름(IN1 · FLAG · IN2) · 상수는 그림에 같은 글로 옮겨지고 작성 시뮬레이션이 분석기 함수로 다시 읽는다."""
    y = D.ry(10, 62)
    t = _box("B1", 500.0, y - 8.5, "T")
    w_in1 = {"id": "w1", "pts": [[600.0, y], [522.0, y]], "arrow": "end"}           # 오른쪽 변 IN1
    w_flag = {"id": "w2", "pts": [[511.0, y + 40.0], [511.0, y + 8.5]], "arrow": "end"}  # 아래 변 FLAG
    w_in2 = {"id": "w3", "pts": [[511.0, y - 40.0], [511.0, y - 8.5]], "arrow": "end"}   # 위 변 IN2
    w_out = {"id": "w4", "pts": [[500.0, y], [420.0, y]], "arrow": "end"}           # 왼쪽 변으로 나감
    doc = _doc([t], [w_in1, w_flag, w_in2, w_out])
    s0 = DS.to_sheet(doc, 1, {})
    nets = {p["side"]: p["net"] for p in s0["ports"] if p["block"] == "B1"}
    # 분석 결과 꼴로 이름을 달아 _aop_texts 로 글을 만든다 (좌표는 그림 좌표 그대로)
    sheet = {"blocks": {"B1": {"param": {"pins": {nets["R"]: {"name": "IN1"}, nets["B"]: {"name": "FLAG"}, nets["T"]: {"name": "IN2"}}}}},
             "ports": [{**p, "at": p["at"]} for p in s0["ports"]]}
    D._aop_texts(sheet, doc, lambda x: x, lambda y_: y_)
    texts = sorted(b["text"] for b in doc["blocks"] if b["kind"] == "TEXT")
    assert texts == ["FLAG", "IN1", "IN2"]
    s = DS.to_sheet(doc, 1, {})
    pins = (s["blocks"]["B1"].get("param") or {}).get("pins") or {}
    got = {next(p["side"] for p in s["ports"] if p["block"] == "B1" and p["net"] == n): v["name"] for n, v in pins.items()}
    assert got == {"R": "IN1", "B": "FLAG", "T": "IN2"}


def test_multiline_title_still_works():
    b = DS._block(_box("B1", 0, 0, "EQUAL IN1 OUT IN2", w=55, h=56, lines=[[17.8, 4.7, "EQUAL", 4.46], [2.3, 6.3, "IN1", 4.46], [40.6, 6.3, "OUT", 4.46]]))
    assert b["label"] == "EQUAL"
