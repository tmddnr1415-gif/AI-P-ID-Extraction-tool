"""L98 — L97 뒤에도 남았던 판독 빈틈 셋: 긴 기운 파선 · 블록 변 바로 앞의 건너뛰기 · 마름모 빗변으로 들어가는 사선 파선."""
from app.logic import draw, sim
from tests.test_logic_l97_dash_stubs import D, G, P, T, _analyse, _doc, _stroke, _tipped


def test_long_slightly_tilted_dash_is_read_as_one_line_and_does_not_join_a_line_it_crosses():
    """0007: 100pt 에 0.5pt 기운 긴 파선.  토막마다 펴면 중간에서 끊기고, 끊긴 끝이 가로지르는 선 위에 놓여 따로인 두 신호가 한 선으로 묶였다 —
    줄을 통째로 한 높이로 편다."""
    y, y1, y6 = T + 3 * P - P / 2, T + 1 * P - P / 2, T + 6 * P - P / 2
    xs, xe = 560.0, 700.0
    blocks = [{"id": "n", "kind": "NOT", "x": xe, "y": y - 4.5, "w": 9, "h": 9, "text": "NOT", "label": "", "param": {}}]
    wires = [{"id": "w0", "pts": [[draw.LX0, y], [xs, y]]},                                   # 3행 → (여기서부터 기운 파선) → NOT
             {"id": "w1", "pts": [[xe + 9, y], [draw.LX1, y]]},
             {"id": "w2", "pts": [[draw.LX0, y6], [630, y6], [630, y1], [draw.LX1, y1]]}]     # 6행의 실선이 올라가며 기운 파선을 **가로지른다** (접합점 없음)
    doc = _doc(blocks, wires, {"3": {"fm": "", "kks": "", "desc": "A"}, "6": {"fm": "", "kks": "", "desc": "B"}},
               {str(59 + 3): {"desc": "OUT", "kks": "", "to": ""}, str(59 + 1): {"desc": "THRU", "kks": "", "to": ""}})
    slope = 0.5 / 100.0

    def edit(pg):
        x = xs
        while x < xe - 0.01:
            b = min(x + D, xe)
            _stroke(pg, [(x, y + (x - xs) * slope - 0.35), (b, y + (b - xs) * slope - 0.35)])
            x = b + G
    s = _analyse(doc, edit)
    nb = next(k for k, b in s["blocks"].items() if b["func"] == "NOT")
    inn = [q["net"] for q in s["ports"] if q["block"] == nb and q["dir"] == "in"]
    row = {r["n"]: r for r in s["rows"]}
    assert inn and inn[0] == row[3]["net"], (inn, [(r["side"], r["n"], r.get("net")) for r in s["rows"]])   # 3행 → (긴 기운 파선) → NOT
    assert row[6]["net"] != row[3]["net"]                                                   # 가로지르는 선과는 따로다
    val = lambda f: [sim.simulate(s, f)["frames"][-1]["values"][row[n]["net"]] for n in (59 + 3, 59 + 1)]
    assert [val({}), val({"row:3": 1}), val({"row:6": 1})] == [[1, 0], [0, 0], [1, 1]]


def test_slanted_dash_into_a_diamond_edge_is_an_input_of_that_diamond():
    """제어 루프 장의 A/M 스테이션: 가로 파선의 끝 토막이 45° 로 꺾여 사선 토막 · 촉을 지나 ◇ 의 빗변에 닿는다 (자동/수동 전환 입력).
    축에 나란한 토막만 보아 이 다리가 빠져 있었다 — ◇ 에 그 입력이 없었다."""
    y = T + 6 * P - P / 2
    cx = 600.0                                                                              # ◇ 의 가운데 x · 왼 꼭짓점 (cx - P, y) · 위 꼭짓점 (cx, y - P)
    blocks = [{"id": "b", "kind": "BOX", "x": cx - P, "y": y - P, "w": 2 * P, "h": 2 * P, "text": "T", "label": "", "param": {"form": "diamond"}}]
    wires = [{"id": "w1", "pts": [[cx + P, y], [draw.LX1, y]]}]
    doc = _doc(blocks, wires, {"4": {"fm": "", "kks": "", "desc": "AUTO"}}, {str(59 + 6): {"desc": "OUT", "kks": "", "to": ""}})
    ty = y - P / 2                                                                          # 촉 끝: 왼쪽 위 빗변의 한가운데 (cx - P/2, y - P/2)
    tip = (cx - P / 2, ty)
    k = 14.0                                                                                # 사선 다리의 가로 길이 — 꺾인 점은 그만큼 왼쪽 위
    bend = (tip[0] - k, tip[1] - k)
    yr = bend[1]

    def edit(pg):
        x = draw.LX0
        while x + D + G < bend[0] - 3.5:
            _stroke(pg, [(x, yr), (x + D, yr)])
            x += D + G
        _stroke(pg, [(bend[0] - 3.5, yr), bend, (bend[0] + 2.6, bend[1] + 2.6)])            # 끝 토막: 가로 몸통 + 사선
        _stroke(pg, [(bend[0] + 4.6, bend[1] + 4.6), (bend[0] + 8.6, bend[1] + 8.6)])       # 사선 토막
        h = (bend[0] + 10.6, bend[1] + 10.6)
        _stroke(pg, [h, tip, (tip[0] - 1.2, tip[1] - 0.6), (tip[0] - 0.6, tip[1] - 1.2), (tip[0] - 0.1, tip[1] - 0.3)])   # 사선 촉
    s = _analyse(doc, edit)
    bid, b = next((k_, v) for k_, v in s["blocks"].items() if v.get("form") == "diamond")
    row = min((r for r in s["rows"] if r["side"] == "L" and r.get("net") is not None), key=lambda r: abs(r["n"] - 4), default=None)
    assert row is not None, s["rows"]
    ins = [q["net"] for q in s["ports"] if q["block"] == bid and q["dir"] == "in"]
    assert row["net"] in ins, (ins, row["net"], [(q["side"], q["dir"], q["net"]) for q in s["ports"] if q["block"] == bid])
