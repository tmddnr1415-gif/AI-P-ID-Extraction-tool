"""hotfix111 — 같은 시스템의 장들을 HMI 한 장으로 · 기기는 그 장이 인쇄한 이름 전부.

시스템 = 도면번호에서 장 일련번호(마지막 숫자 마디)만 뗀 것.  장 안의 배치는 P&ID 그대로 · 공통 배율 · 장 사이 선은 커넥터 글이
다른 장의 도면번호나 기기 이름을 담을 때만 (지어내지 않는다).  판정 0줄 — 지문에 닿는 칸이 없다."""
from __future__ import annotations

import ast
import copy
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


def _model(page=5, dwg="D00P-10LBA10-M05-0001", conn="HP HEADER", eq_name="COMPRESSOR 10LBA10AN001", title="P&ID FOR HP STEAM SYSTEM (1/2)"):
    def inst(k, x, y, typ, tag, tap=None):
        return {"key": f"{page}-{k}", "tag": tag, "type": typ, "rect": [x, y, x + 22.6, y + 22.6], "scope": "SCT", "line_no": "10LBA10",
                "line_size": "DN 400", "lines": 0, "equip": "", "review": False, "tap": tap}
    run = [100.0, 300.0, 500.0, 300.0]
    return {"page_no": page, "drawing_no": dwg, "title": title, "width": 2384.0, "height": 1684.0,
            "instruments": [inst("i1", 120, 250, "PIT", f"10LBA10CP00{page}", run), inst("i2", 300, 420, "TIT", f"10LBA10CT00{page}")],
            "valves": [{"key": f"{page}-v1", "tag": "", "body": "GATE", "actuator": "MOTOR", "state": "", "rect": [380, 292, 396, 308],
                        "tag_rect": None, "scope": "SCT", "tab": "MOV"}],
            "pipes": [{"seg": run, "role": "tap"}],
            "equipment": [{"name": eq_name, "rect": [200, 380, 290, 392], "noun": "COMPRESSOR"},
                          {"name": "BYPASS VALVE", "rect": [600, 380, 660, 392], "noun": "VALVE"}],
            "connectors": [{"name": conn, "dir": "TO", "at": [500.0, 302.0]}],
            "line_labels": [], "tagged": 2}


def test_system_is_the_drawing_number_without_its_serial():
    assert scene.system_of("D00P-10LBA10-M05-0001", 5) == ("D00P-10LBA10-M05", "10LBA10")
    assert scene.system_of("D00P-10LBA10-M05-0002", 6)[0] == "D00P-10LBA10-M05"
    assert scene.system_of("D00P-10LBC40-M05-0001", 7)[0] != "D00P-10LBA10-M05"
    assert scene.system_of("B-SBA-M-32-001", 1)[0] == "B-SBA-M-32"                 # Takhiatash 꼴 — KKS 를 외우지 않는다
    assert scene.system_of("D02J-31PGB0-M05-0003", 1) == ("D02J-31PGB0-M05", "31PGB0")
    assert scene.system_of("", 9) == ("p9", "p9")                                   # 못 읽은 장은 혼자
    assert scene.common_title(["P&ID FOR HP STEAM SYSTEM (1/2)", "P&ID FOR HP STEAM SYSTEM (2/2)"]) == "P&ID FOR HP STEAM SYSTEM"
    g = scene.group_systems([_model(5), _model(6, "D00P-10LBA10-M05-0002"), _model(7, "D00P-10LBC40-M05-0001")])
    assert [x["pages"] for x in g] == [[5, 6], [7]] and g[0]["code"] == "10LBA10"


def test_system_scene_keeps_each_sheet_layout_at_one_scale():
    a, b = _model(5), _model(6, "D00P-10LBA10-M05-0002", conn="D00P-10LBA10-M05-0001")
    one = scene.from_model(copy.deepcopy(a))
    sc = scene.from_system([a, b], key="D00P-10LBA10-M05")
    assert sc["view"] == "system" and sc["pages"] == [5, 6] and len(sc["frames"]) == 2
    assert abs(sc["scale"] - one["scale"]) < 1e-6                                   # 공통 배율 — 버블 크기가 장마다 같다
    i1 = next(i for i in sc["instruments"] if i["id"] == "5-i1")
    i2 = next(i for i in sc["instruments"] if i["id"] == "5-i2")
    o1, o2 = one["instruments"][0], one["instruments"][1]
    assert abs((i2["x"] - i1["x"]) - (o2["x"] - o1["x"])) < 0.2                      # 장 안의 배치 그대로 (옮긴 것뿐)
    ids = [p["id"] for p in sc["pipes"]] + [e["id"] for e in sc["equipment"]]
    assert len(ids) == len(set(ids))                                                # 장끼리 id 가 겹치지 않는다
    f5, f6 = sc["frames"]
    assert f6["x"] >= f5["x"] + f5["w"] or f6["y"] >= f5["y"] + f5["h"]               # 장끼리 겹치지 않는다
    # 기기: 그 장이 인쇄한 이름 전부 · VALVE 는 모양을 지어내지 않고 이름만
    assert sc["counts"]["equipment"] == 2 and {e["sym"] for e in sc["equipment"]} == {"compressor"}
    assert sum(1 for l in sc["labels"] if l["kind"] == "equip" and l["text"] == "BYPASS VALVE") == 2
    # 장 사이 선: p6 의 커넥터 글이 p5 의 도면번호를 담는다 → 하나 · p5 의 HP HEADER 는 아무 장도 말하지 않는다 → 없음
    links = [p for p in sc["pipes"] if p["kind"] == "link"]
    assert len(links) == 1 and links[0]["from_page"] == 6 and links[0]["to_page"] == 5 and links[0]["by"] == "drawing_no"
    assert sc["counts"]["links"] == 1 and sc["counts"]["sheets"] == 2
    kinds = set(re.findall(r"^\s*([a-z]+):\s*\{", (STATIC / "hmi" / "hmi_symbols.js").read_text(encoding="utf-8")
                           .split("const LINES = {")[1].split("};")[0], re.M))
    assert {p["kind"] for p in sc["pipes"]} <= kinds


def test_equipment_name_link_and_no_invented_link():
    a = _model(5, conn="TO FEED PUMP A")
    b = _model(6, "D00P-10LBA10-M05-0002", conn="UNKNOWN PLACE", eq_name="FEED PUMP A")
    b["equipment"][0]["noun"] = "PUMP"
    sc = scene.from_system([a, b], key="D00P-10LBA10-M05")
    links = [p for p in sc["pipes"] if p["kind"] == "link"]
    assert len(links) == 1 and links[0]["by"] == "equipment" and links[0]["to_page"] == 6


def test_build_sheet_takes_every_printed_equipment_label():
    page = {"page_no": 5, "drawing_no": "D00P-10LBA10-M05-0001", "title": "T", "width": 100, "height": 100}
    row = {"key": "k1", "tab": "FIELD", "page_no": 5, "rect": [10, 10, 30, 30], "values": {"type": "PIT", "tag_no": "X1"}, "evidence": {}}
    m = dcs.build_sheet(page, [row], [{"name": "HP DRUM", "rect": [50, 50, 80, 58], "noun": "DRUM"}])
    assert [e["name"] for e in m["equipment"]] == ["HP DRUM"]
    assert dcs.build_sheet(page, [row])["equipment"] == []                         # 옛 분석 — 후보만 (여기선 없음)


def test_pipeline_records_equipment_labels_outside_the_fingerprint():
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert '"equipment_labels": {str(pno)' in src
    fp = src.split("def fingerprint(result: dict) -> str:")[1].split("return hashlib")[0]
    assert "equipment_labels" not in fp
    assert '"equipment_labels",' in (ROOT / "app" / "db.py").read_text(encoding="utf-8")   # 저장 화이트리스트


def test_system_store_path_is_guarded(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "root", lambda: tmp_path)
    assert store.sys_path("ab12cd34ef56", "D00P-10LBA10-M05").name == "s_D00P-10LBA10-M05.json"
    for bad in ("../x", "a/b", "..", ""):
        with pytest.raises(KeyError):
            store.sys_path("ab12cd34ef56", bad)
    store.save("ab12cd34ef56", "sys:D00P-10LBA10-M05", {"title": "s"}, "홍길동")
    assert store.load("ab12cd34ef56", "sys:D00P-10LBA10-M05")["title"] == "s"
    assert store.load("ab12cd34ef56", 5) is None                                     # 장 저장본과 따로


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "root", lambda: tmp_path)
    with TestClient(app) as c:
        yield c


def test_system_api_roundtrip(client, monkeypatch):
    models = [_model(5), _model(6, "D00P-10LBA10-M05-0002", conn="D00P-10LBA10-M05-0001"), _model(7, "D00P-10LBC40-M05-0001")]
    monkeypatch.setattr(dcs, "_eligibility", lambda j: ({"id": j, "pdf_name": "x.pdf", "project": "P"}, {"eligible": True})
                        if j == "ab12cd34ef56" else (None, {"error": "no such job"}))
    monkeypatch.setattr(dcs, "_sheets", lambda j: copy.deepcopy(models))
    monkeypatch.setattr(dcs, "hmi_load", lambda j: {})
    job = client.get("/dcs/api/jobs/ab12cd34ef56").json()
    assert [g["pages"] for g in job["systems"]] == [[5, 6], [7]]
    assert job["systems"][0]["equipment"] == 2 and job["sheets"][0]["system"] == "D00P-10LBA10-M05"
    u = "/dcs/api/jobs/ab12cd34ef56/system/D00P-10LBA10-M05/scene"
    sc = client.get(u).json()
    assert sc["saved"] is False and sc["pages"] == [5, 6] and sc["counts"]["sheets"] == 2
    assert client.get("/dcs/api/jobs/ab12cd34ef56/system/NOPE/scene").status_code == 404
    assert client.post(u, json={"scene": sc}).status_code == 401
    r = client.post(u, json={"scene": sc}, headers={"X-Author": quote("홍길동")})
    assert r.status_code == 200 and client.get(u).json()["saved"] is True
    assert client.get("/dcs/api/jobs/ab12cd34ef56").json()["systems"][0]["saved"] is True
    assert client.get(u + "?fresh=1").json()["saved"] is False
    assert client.delete(u).json()["removed"] is True


def test_screen_opens_systems_first():
    js = (STATIC / "hmi" / "hmi.js").read_text(encoding="utf-8")
    for needle in ("function sceneUrl()", "/system/${encodeURIComponent(", "시스템 한 장", "function drawFrame(", "sysOf(", 'Q.get("view") === "sheet"'):
        assert needle in js, needle
    assert ".frame-title" in (STATIC / "hmi" / "hmi.css").read_text(encoding="utf-8")


def test_hmi_package_still_reads_only():
    tree = ast.parse((ROOT / "app" / "hmi" / "scene.py").read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("engine" in m or "pipeline" in m or "dcs" in m for m in mods)
