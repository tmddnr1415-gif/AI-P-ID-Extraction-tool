"""hotfix110 — LOGIC 브랜치 H1회차의 HMI 화면을 /dcs 로.  장면은 실제 P&ID 배치(app/hmi/scene.py) · 저장 · LOGIC 연동 계약.

판정 0줄: 장면은 분석 결과의 자리·태그·런을 옮긴 것이고 심볼은 사전 하나(hmi_symbols.js), 참고 PNG 는 쓰지 않는다."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from app import dcs
from app.hmi import scene, store
from app.main import app

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"


def _sym_names():
    src = (STATIC / "hmi" / "hmi_symbols.js").read_text(encoding="utf-8")
    return set(re.findall(r'def\("([a-z_0-9]+)"', src))


def _line_kinds():
    src = (STATIC / "hmi" / "hmi_symbols.js").read_text(encoding="utf-8")
    body = src.split("const LINES = {")[1].split("};")[0]
    return set(re.findall(r"^\s*([a-z]+):\s*\{", body, re.M))


def _model():
    """build_sheet 꼴 — 버블 22.6pt (AL NOUF1 A1) 넷이 나란히 · 밸브 하나 · 기기 라벨 하나 · 런 둘 · TO 커넥터."""
    def inst(k, x, y, typ, tag, tap=None, line="10LBA10", lines=0):
        return {"key": k, "tag": tag, "type": typ, "rect": [x, y, x + 22.6, y + 22.6], "scope": "SCT", "line_no": line,
                "line_size": "DN 400", "lines": lines, "equip": "", "review": False, "tap": tap}
    run = [100.0, 300.0, 500.0, 300.0]
    return {"page_no": 5, "drawing_no": "D00P-10LBA10-M05-0001", "title": "HP STEAM", "width": 2384.0, "height": 1684.0,
            "instruments": [inst("i1", 120, 250, "PIT", "10LBA10CP001", run), inst("i2", 145, 250, "TIT", "10LBA10CT001", run),
                            inst("i3", 170, 250, "PIC", "10LBA10CP001", None, "", 1), inst("i4", 300, 420, "LIT", "", None, "10PGB10")],
            "valves": [{"key": "v1", "tag": "10LBA10AA001", "body": "GATE", "actuator": "MOTOR", "state": "", "rect": [380, 292, 396, 308],
                        "tag_rect": None, "scope": "SCT", "tab": "MOV"}],
            "pipes": [{"seg": run, "role": "tap"}, {"seg": [500.0, 300.0, 500.0, 500.0], "role": "line"}],
            "equipment": [{"name": "COMPRESSOR 10LBA10AN001", "rect": [200, 380, 290, 392], "noun": "COMPRESSOR"}],
            "connectors": [{"name": "HP HEADER", "dir": "TO", "at": [500.0, 302.0]}],
            "line_labels": [{"line_no": "10LBA10", "size": "DN 400", "rect": [130, 290, 170, 298]}], "tagged": 4}


def test_scene_keeps_pid_layout_at_one_scale_and_never_invents():
    sc = scene.from_model(_model())
    assert sc["counts"] == {"instruments": 4, "tagged": 3, "valves": 1, "equipment": 1, "pipes": 2}
    k = sc["scale"]
    assert abs(k - 40 / 22.6) < 1e-3                                       # 버블 중앙값 = 화면 버블 지름 40
    i1, i2 = sc["instruments"][0], sc["instruments"][1]
    assert abs((i2["x"] - i1["x"]) - 25 * k) < 0.2                        # 같은 배율 — P&ID 간격 그대로
    assert i1["on"] == "R1" and i1["kind"] == "field" and sc["instruments"][2]["kind"] == "dcs"
    assert sc["instruments"][3]["tag"] == ""                               # 태그 없는 계기는 비운다 (TYPE 으로 지어내지 않는다)
    tap = next(p for p in sc["pipes"] if p["id"] == "R1")
    assert tap["kind"] == "steam" and tap["arrow"] is True                  # 라인 깃발 10LBA10 → 증기 · TO 커넥터 → 화살
    sig = [p for p in sc["pipes"] if p["kind"] == "signal"]
    assert len(sig) == 1 and sig[0]["id"] == "S-i3"                        # PIC ← 같은 태그 PIT 신호선만
    assert sc["valves"][0]["sym"] == "valve_control_electric" and sc["valves"][0]["tag"] == "10LBA10AA001"
    assert sc["equipment"][0]["sym"] == "compressor" and sc["equipment"][0]["tag"] == "COMPRESSOR 10LBA10AN001"
    assert all(v[0] is None for v in sc["equipment"][0]["params"].values())     # 모터 값은 지어내지 않는다
    assert {l["kind"] for l in sc["labels"]} == {"line", "conn"}
    assert any(l["text"] == "To HP HEADER" for l in sc["labels"])
    # 사전에 없는 심볼 · 배관 종류를 쓰지 않는다
    syms, kinds = _sym_names(), _line_kinds()
    assert {e["sym"] for e in sc["equipment"]} | {v["sym"] for v in sc["valves"]} <= syms
    assert {p["kind"] for p in sc["pipes"]} <= kinds


def test_value_boxes_do_not_cover_each_other():
    sc = scene.from_model(_model())
    boxes = [scene.face_box(i["x"], i["y"], i["face"]) for i in sc["instruments"]]
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            assert not scene._hit(boxes[a], boxes[b])
    assert {i["face"] for i in sc["instruments"][:3]} != {"above"}          # 나란한 세 버블 — 다 위에 두면 덮는다


def test_hotfix109_people_values_are_kept():
    sc = scene.from_model(_model(), {"tags": {"i4": "10PGB10CL001"}, "names": {"COMPRESSOR 10LBA10AN001": "Main Compressor"},
                                     "params": {"5": ["10LBA10CT001"]}, "trend": {"5": "10LBA10CT001"}})
    assert sc["instruments"][3]["tag"] == "10PGB10CL001"
    assert sc["equipment"][0]["tag"] == "Main Compressor" and sc["equipment"][0]["orig_name"] == "COMPRESSOR 10LBA10AN001"
    assert sc["panels"]["key"] == ["10LBA10CT001"] and sc["panels"]["trend"]["tag"] == "10LBA10CT001"


def test_example_scene_uses_only_dictionary_symbols():
    ex = json.loads((ROOT / "config" / "hmi_example_compressor_train.json").read_text(encoding="utf-8"))
    syms, kinds = _sym_names(), _line_kinds()
    assert {e["sym"] for e in ex["equipment"]} | {v["sym"] for v in ex["valves"]} <= syms
    assert {p["kind"] for p in ex["pipes"]} <= kinds
    assert "png" not in json.dumps(ex).lower()


def test_store_needs_author_and_keeps_analysis_untouched(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "root", lambda: tmp_path)
    with pytest.raises(ValueError):
        store.save("ab12cd34ef56", 5, {"title": "x"}, "")
    out = store.save("ab12cd34ef56", 5, {"title": "x"}, "홍길동")
    assert out["saved_by"] == "홍길동" and store.load("ab12cd34ef56", 5)["title"] == "x"
    assert store.delete("ab12cd34ef56", 5) and store.load("ab12cd34ef56", 5) is None
    with pytest.raises(KeyError):
        store.path("../x", 1)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "root", lambda: tmp_path)
    with TestClient(app) as c:
        yield c


def test_scene_api_roundtrip(client, monkeypatch):
    monkeypatch.setattr(dcs, "_eligibility", lambda j: ({"id": j}, {"eligible": True}) if j == "ab12cd34ef56" else (None, {"error": "no such job"}))
    monkeypatch.setattr(dcs, "_sheet", lambda j, p: _model() if int(p) == 5 else None)
    monkeypatch.setattr(dcs, "hmi_load", lambda j: {})
    r = client.get("/dcs/api/jobs/ab12cd34ef56/scene/5")
    assert r.status_code == 200 and r.json()["saved"] is False and r.json()["counts"]["instruments"] == 4
    assert client.get("/dcs/api/jobs/ab12cd34ef56/scene/9").status_code == 404
    assert client.get("/dcs/api/jobs/zzzz/scene/5").status_code == 404
    sc = r.json(); sc["instruments"][0]["tag"] = "10LBA10CP099"
    assert client.post("/dcs/api/jobs/ab12cd34ef56/scene/5", json={"scene": sc}).status_code == 401       # 작성자 없음
    r2 = client.post("/dcs/api/jobs/ab12cd34ef56/scene/5", json={"scene": sc}, headers={"X-Author": quote("홍길동")})
    assert r2.status_code == 200 and r2.json()["saved_by"] == "홍길동"
    back = client.get("/dcs/api/jobs/ab12cd34ef56/scene/5").json()
    assert back["saved"] is True and back["instruments"][0]["tag"] == "10LBA10CP099"
    assert client.get("/dcs/api/jobs/ab12cd34ef56/scene/5?fresh=1").json()["saved"] is False
    assert client.delete("/dcs/api/jobs/ab12cd34ef56/scene/5").json()["removed"] is True
    assert client.get("/dcs/api/jobs/ab12cd34ef56/scene/5").json()["saved"] is False


def test_pages_and_example_served(client):
    for u in ("/dcs", "/dcs/demo", "/hmi"):
        r = client.get(u)
        assert r.status_code == 200 and "/static/hmi/hmi.js" in r.text and "Symbol Library" in r.text
        assert r.text.index("/static/offline.js") < r.text.index("/static/hmi/hmi.js")   # 절전모드 감싸기가 먼저
    ex = client.get("/dcs/api/example").json()
    assert ex["panels"]["control"]["tag"] == "PIC-101"


def test_hmi_package_reads_only_no_engine():
    for f in (ROOT / "app" / "hmi").glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
               {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        assert not any("engine" in m or "pipeline" in m for m in mods), f


def test_screen_keeps_logic_contract():
    js = (STATIC / "hmi" / "hmi.js").read_text(encoding="utf-8")
    for needle in ('kind: "dcs-ready"', '"dcs-states"', 'kind: "dcs-go"', "/dcs/api/jobs/${v}/tags", "applyLogic", "location.origin"):
        assert needle in js, needle
    assert "/hmi/api/" not in js                                            # H1 의 옛 주소가 남지 않는다
    assert "X-Author" in js and "OFFLINE.prefetchUrls" in js
