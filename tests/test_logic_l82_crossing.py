"""L82 — 지나가는 교차를 연결로 보지 않는다.
CAD 는 두 선이 엇갈리는 자리에서 한 선을 둘로 끊어 그린다 (끊긴 두 토막의 끝이 다른 선의 몸통 위 같은 점).
예전엔 '끝이 몸통에 닿으면 연결' 이라 엇갈린 두 신호가 한 그물이 되어 시뮬레이션이 엉뚱한 블록을 켰다
(827장 묶음 · 서로 다른 분석 선 둘 이상을 합친 그물 161개/73장 → 69개/9장, 남은 것은 화살촉 토막)."""
from app.logic import draw_sim as DS


def _nets(wires):
    net_of, _ = DS._nets_of(wires)
    return net_of


V = {"id": "v", "pts": [[50.0, 0.0], [50.0, 100.0]]}


def test_split_crossing_is_not_a_connection():
    left = {"id": "h1", "pts": [[0.0, 50.0], [50.0, 50.0]]}
    right = {"id": "h2", "pts": [[50.0, 50.0], [100.0, 50.0]]}
    n = _nets([V, left, right])
    assert n[0] != n[1] and n[0] != n[2], "엇갈림이 세로선과 이어졌다"
    assert n[1] == n[2], "끊긴 가로선 두 토막은 한 선이다"


def test_tee_is_a_connection():
    left = {"id": "h1", "pts": [[0.0, 50.0], [50.0, 50.0]]}
    n = _nets([V, left])
    assert n[0] == n[1], "T 자 맞닿음은 연결이다"


def test_dot_at_crossing_is_a_connection():
    left = {"id": "h1", "pts": [[0.0, 50.0], [50.0, 50.0]], "dots": [[50.0, 50.0]]}
    right = {"id": "h2", "pts": [[50.0, 50.0], [100.0, 50.0]]}
    n = _nets([V, left, right])
    assert n[0] == n[1] == n[2], "연결점(dot)이 있으면 연결이다"


def test_unnamed_input_coef_is_used_in_the_result():
    """L82 — 이름 없는 입력의 계수(−1)가 식에만 보이고 계산엔 빠지던 것 (−10 + 4 = 14 로 나왔다)."""
    from app.logic import aop_trace as T
    r = T.run_static("sum", [{"pin": "", "value": 10, "coef": -1}, {"pin": "", "value": 4}], {}, "")
    assert r["out"] == -6.0 and r["trace"]["sub"] == "−10 + 4"


def test_drawing_aop_endpoint_gives_inputs_and_trace(tmp_path, monkeypatch):
    """L82 — 그린 장의 신호 처리 블록 두 번 누름 판: 연산 · 입력선(어디서) · 지금 계산 과정."""
    from fastapi.testclient import TestClient
    from app.logic import draw
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app import main
    c = TestClient(main.app)
    doc = c.post("/logic/api/drawings", json={"name": "aop", "author": "t"}).json()
    did = doc["id"]
    N = doc.get("N") or 50
    y1, y2 = draw.ry(3, N), draw.ry(5, N)
    bx = {"id": "B1", "kind": "BOX", "x": 200.0, "y": y1 - 2, "w": 12.0, "h": (y2 - y1) + 4, "text": "Σ", "label": "", "param": {}}
    wires = [{"id": "w1", "pts": [[draw.LX0, y1], [200.0, y1]]}, {"id": "w2", "pts": [[draw.LX0, y2], [200.0, y2]]},
             {"id": "w3", "pts": [[212.0, y1 + 1], [draw.LX1, y1 + 1]]}]
    r = c.post(f"/logic/api/drawings/{did}/aop", json={"block": "B1", "doc": {**doc, "blocks": [bx], "wires": wires}}).json()
    assert r["op"] == "sum", r
    assert len(r["inputs"]) == 2 and r["trace"]["sym"].startswith("M =")
    assert all(v["kind"] == "row" for v in r["sources"].values()), r["sources"]
