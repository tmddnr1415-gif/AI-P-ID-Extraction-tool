"""L84 — 들여온 그림을 가볍게: 분석 선분 토막을 **연결 그대로** 적은 선으로 묶는다 (draw_compact) · 프로젝트 지우기.

19VA 를 다시 그린 827장은 토막 115,018개였다 (0007 한 장 3,549 · 파선 틀 하나가 토막 854).  화면은 선마다 SVG 서너 개를 그려
장을 넘길 때마다 무거웠다.  묶은 뒤에도 시뮬레이터 꼴(draw_sim.to_sheet)의 단자 · 행이 어느 그물에 붙는지가 같아야 하고,
저장(clean — 곧게 펴기)을 거쳐도 같아야 한다."""
import copy
import gzip
import json
from pathlib import Path

import pytest

from app.logic import draw as D
from app.logic import draw_compact as C

SEED = Path(__file__).resolve().parents[1] / "config" / "logic_draw_seed" / "amiral_19va_r1.json.gz"


def _dash(x0, x1, y, n, tag, dash=3.7, gap=1.9):
    """분석이 내는 파선 그물 꼴 — 토막과 그 틈을 메운 토막(분석 그물의 선분)이 끝끼리 맞닿는다."""
    out, x, k = [], x0, 0
    while x < x1 and k < n:
        e = min(x + dash, x1)
        out.append({"id": f"n{tag}_{k}", "pts": [[x, y], [e, y]], "dashed": True})
        if e + gap < x1:
            out.append({"id": f"n{tag}_{1000 + k}", "pts": [[e, y], [e + gap, y]], "dashed": True})
        x = e + gap
        k += 1
    return out


def _doc(wires, blocks=()):
    return {"N": 62, "form": "a5j", "blocks": list(blocks), "wires": wires, "left": {}, "right": {}}


def test_dashed_pieces_become_one_dashed_line():
    ws = _dash(400.0, 500.0, 300.5, 50, "9")
    out, rep = C.compact(_doc(ws))
    xs = sorted(p[0] for p in out[0]["pts"]) if len(out) == 1 else []
    assert rep["ok"] and len(out) == 1 and out[0]["dashed"] and len(out[0]["pts"]) == 2
    assert xs[0] == 400.0 and abs(xs[-1] - max(w["pts"][1][0] for w in ws)) < 0.01


def test_dashes_with_bare_gaps_stay_apart():
    """틈만 있는 파선 토막은 시뮬레이터에서 서로 다른 그물이다 — 묶으면 연결이 생기므로 묶지 않는다 (판정 불변)."""
    ws = [w for w in _dash(400.0, 500.0, 300.5, 50, "9") if int(w["id"].split("_")[1]) < 1000]
    out, rep = C.compact(_doc(ws))
    assert len(out) == len(ws)


def test_split_solid_pieces_join_but_t_junction_stays():
    a = {"id": "n1_0", "pts": [[400.0, 300.5], [450.0, 300.5]]}
    b = {"id": "n1_1", "pts": [[450.0, 300.5], [500.0, 300.5]]}
    c = {"id": "n1_2", "pts": [[500.0, 300.5], [500.0, 350.5]]}
    out, rep = C.compact(_doc([a, b, c]))
    assert rep["ok"] and len(out) == 1 and out[0]["pts"] in ([[400.0, 300.5], [500.0, 300.5], [500.0, 350.5]], [[500.0, 350.5], [500.0, 300.5], [400.0, 300.5]])
    t = {"id": "n1_3", "pts": [[450.0, 300.5], [450.0, 250.5]]}                    # 가운데 점에 세 번째 선 → 잇지 않는다
    out, rep = C.compact(_doc([a, b, t]))
    assert rep["ok"] and len(out) == 3


def test_different_analysis_nets_never_merge():
    a = {"id": "n1_0", "pts": [[400.0, 300.5], [450.0, 300.5]]}
    b = {"id": "n2_0", "pts": [[450.0, 300.5], [500.0, 300.5]]}
    out, _ = C.compact(_doc([a, b]))
    assert len(out) == 2


def test_hand_drawn_drawing_is_left_alone():
    ws = [{"id": "w1", "pts": [[400.0, 300.5], [450.0, 300.5]]}, {"id": "w2", "pts": [[450.0, 300.5], [500.0, 300.5]]}]
    out, rep = C.compact(_doc(ws))
    assert out == ws and not C.imported(_doc(ws))


def test_arrow_end_is_kept_and_dots_carry_over():
    a = {"id": "n1_0", "pts": [[400.0, 300.5], [450.0, 300.5]], "dots": [[420.0, 300.5]]}
    b = {"id": "n1_1", "pts": [[450.0, 300.5], [500.0, 300.5]], "arrow": "end"}
    out, rep = C.compact(_doc([a, b]))
    assert len(out) == 1 and out[0]["arrow"] == "end" and out[0]["dots"] == [[420.0, 300.5]] and out[0]["fx"] == 1


@pytest.fixture(scope="module")
def seed():
    return json.loads(gzip.decompress(SEED.read_bytes()))


def test_seed_is_compacted_and_light(seed):
    docs = seed["docs"]
    assert seed["rev"] >= 3 and all(d.get("compact") for d in docs)
    by = {d["name"]: d for d in docs}
    assert len(by["0007"]["wires"]) < 1500 and len(by["0006"]["wires"]) < 400          # 묶기 전 3,549 · 1,970
    assert sum(len(d["wires"]) for d in docs) < 40000                                   # 묶기 전 115,018


@pytest.mark.parametrize("name", ["0006", "0007", "0009", "0024", "CO01_P018"])
def test_seed_sheet_saves_without_changing_connections(seed, name):
    """씨앗 장을 사람이 열어 저장해도(clean → 곧게 펴기) 단자 · 행이 붙는 그물이 그대로.  묶은 선(fx)은 펴기에서 붙든다."""
    doc = next(d for d in seed["docs"] if d["name"] == name)
    once = D.clean(copy.deepcopy(doc))
    twice = D.clean(copy.deepcopy({**doc, **once}))
    s0 = C._signature(doc, doc["wires"])[:2]
    assert C._signature(doc, once["wires"])[:2] == s0
    assert C._signature(doc, twice["wires"])[:2] == s0


def test_compacted_seed_sheet_matches_uncompacted_connections():
    """묶기 전 판(씨앗 rev 2 는 이 저장소에 없다) 대신 — 묶은 장을 다시 토막으로 쪼개도 연결이 같다."""
    doc = next(d for d in json.loads(gzip.decompress(SEED.read_bytes()))["docs"] if d["name"] == "0013")
    pieces = []
    for w in doc["wires"]:
        for k, (a, b) in enumerate(zip(w["pts"], w["pts"][1:])):
            pieces.append({**{x: v for x, v in w.items() if x not in ("pts", "dots", "fx", "arrow")}, "id": f"{w['id']}{k}", "pts": [a, b],
                           **({"dots": w["dots"]} if k == 0 and w.get("dots") else {})})
    # 화살촉 자리는 쪼개도 끝에 남는다 — 화살 표시만 빼고 견준다
    assert C._signature(doc, pieces)[0] == C._signature(doc, [dict(w, arrow=None) for w in doc["wires"]])[0]


def test_purge_project_removes_drawings_and_logs(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_DRAW_SEED", "0")
    from app import main
    c = TestClient(main.app)
    c.post("/logic/api/projects", json={"name": "지울PJ", "author": "t"})
    ids = [c.post("/logic/api/drawings", json={"name": f"g{k}", "author": "t", "project": "지울PJ"}).json()["id"] for k in range(3)]
    keep = c.post("/logic/api/drawings", json={"name": "남길", "author": "t", "project": "다른PJ"}).json()["id"]
    pv = c.get("/logic/api/drawings/purge_preview", params={"project": "지울PJ"}).json()
    assert pv["drawings"] == 3 and pv["confirm"] == "지울PJ"
    r = c.post("/logic/api/drawings/purge", json={"project": "지울PJ", "author": "t", "confirm": "틀림"})
    assert r.status_code == 400
    r = c.post("/logic/api/drawings/purge", json={"project": "지울PJ", "author": "", "confirm": "지울PJ"})
    assert r.status_code == 400
    r = c.post("/logic/api/drawings/purge", json={"project": "지울PJ", "author": "t", "confirm": "지울PJ"}).json()
    assert r["deleted"] == 3
    left = {i["id"] for i in c.get("/logic/api/drawings").json()["items"]}
    assert not (left & set(ids)) and keep in left
    assert not any(p["name"] == "지울PJ" for p in c.get("/logic/api/projects").json()["projects"])
    logs = [json.loads(f.read_text(encoding="utf-8")) for f in Path(tmp_path).rglob("deletion_log.json")]
    items = [it for lg in logs for it in lg]
    assert {it.get("id") for it in items} >= set(ids)          # 누가 무엇을 지웠는지 남는다


def test_get_drawing_compacts_imported_doc_once(tmp_path, monkeypatch):
    """예전에 들여온 그림(묶지 않은 판)은 처음 열 때 묶어 다시 적는다 — 고친 때 · 저장 횟수는 그대로."""
    from fastapi.testclient import TestClient
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PID_DRAW_SEED", "0")
    from app import main
    c = TestClient(main.app)
    did = c.post("/logic/api/drawings", json={"name": "옛", "author": "t"}).json()["id"]
    p = D._path(did)
    doc = json.loads(p.read_text(encoding="utf-8"))
    doc["wires"] = _dash(400.0, 500.0, D.ry(10, doc["N"]) + 2.0, 40, "5")
    doc.pop("compact", None)
    p.write_text(json.dumps(doc), encoding="utf-8")
    d1 = c.get(f"/logic/api/drawings/{did}").json()
    assert len(d1["wires"]) == 1 and d1["compact"] == C.VERSION
    assert (d1["updated"], d1.get("saves")) == (doc["updated"], doc.get("saves"))


def test_drawing_and_analysis_deletions_share_one_log(tmp_path, monkeypatch):
    """L84 — 그림 지우기 기록과 분석 지우기 기록이 서로를 지우지 않는다 (예전 그림 기록 꼴 `{"items": …}` 도 이어 쓴다)."""
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app.logic import store
    p = store.root() / "deletion_log.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"items": [{"kind": "drawing", "id": "old"}]}), encoding="utf-8")
    store.log_deletion({"job": "j1", "author": "t"})
    store.log_deletion([{"kind": "drawing", "id": "a"}, {"kind": "drawing", "id": "b"}])
    items = json.loads(p.read_text(encoding="utf-8"))
    assert [i.get("id") or i.get("job") for i in items] == ["old", "j1", "a", "b"]


def test_multiline_box_title_names_the_operator(seed):
    """L84 — 여러 줄 상자는 단자 이름까지 한 글로 붙어 와 연산 이름을 못 찾았다 (EQUAL · BIT_CNT · SPC 조절기 116개).
    가장 큰 글씨의 줄을 이름으로 — 사전에 있을 때만.  SPC 는 받기만 하는 그림이어도 표시 글자(DISPLAY)가 아니다."""
    from app.logic import aops, draw_sim as DS
    by = {d["name"]: d for d in seed["docs"]}
    found = {}
    for nm in ("CO02_G705", "CO02_P031", "HS10_P101"):
        s = DS.to_sheet(by[nm], 1, {})
        aops.identify([s])
        for b in s["blocks"].values():
            if b.get("aop"):
                found.setdefault(nm, set()).add(b["aop"])
    assert "equal" in found["CO02_G705"] and "count" in found["CO02_P031"] and "pid" in found["HS10_P101"]
    one = DS._block({"kind": "BOX", "text": "A", "x": 0, "y": 0, "w": 10, "h": 10, "param": {}})
    assert one["label"] == "A" and not one.get("title_op")          # 한 줄 상자는 그대로
