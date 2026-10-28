"""HMI 그래픽 (app/hmi · app/static/hmi) — 식별된 P&ID 를 DCS 화면처럼 다시 그린다.

판정 0줄: 장면은 분석 결과의 자리·태그를 옮긴 것이고, 심볼은 개별 SVG 컴포넌트(사전 하나)이며, 참고 PNG 는 쓰지 않는다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import db
from app.hmi import scene, store

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static" / "hmi"


def _sym_names():
    src = (STATIC / "hmi_symbols.js").read_text(encoding="utf-8")
    return set(re.findall(r'def\("([a-z_0-9]+)"', src))


def _rows():
    def inst(k, typ, tag, x, y, line, size, system, desc, noun=None, dist=None):
        ev = {}
        if noun:
            ev["description_selected"] = {"equipment": {"noun": noun, "ordinal": "A"}, "distance": dist, "direction": "BELOW"}
            ev["candidates"] = [{"text": f"{noun} 10LBA10AP001", "kind": "EQUIPMENT", "distance": dist, "direction": "BELOW",
                                 "rect": [x - 40, y + 70, x + 40, y + 120], "equipment": {"noun": noun, "ordinal": "A"}}]
        return {"key": k, "tab": "FIELD", "page_no": 6, "drawing_no": "D-1", "rect": [x, y, x + 22, y + 22],
                "type": typ, "qty": 2, "system": system, "scope": "SCT", "description": desc, "tag_no": tag,
                "line_no": line, "line_size": size, "valve_type": "", "vendor_supply": "", "description_grade": "", "remark": "",
                "needs_review": "", "annotation": "", "evidence": ev}
    rows = [
        inst("r1", "PIT", "10LBA10CP001", 150, 200, "10LBA10", "DN 400", "HP STEAM", "HP STEAM PRESSURE A", "COMPRESSOR", 90),
        inst("r2", "TIT", "10LBA10CT001", 260, 200, "10LBA10", "DN 400", "HP STEAM", "HP STEAM TEMPERATURE A"),
        inst("r3", "PIC", "10LBA10CP001", 400, 420, "", "", "HP STEAM", "PRESSURE CONTROL"),
        inst("r4", "TI", "10PGB10CT001", 740, 480, "10PGB10", "DN 150", "CLOSED COOLING WATER", "CCW RETURN TEMPERATURE"),
        inst("r5", "PI", "10GHC10CP001", 600, 560, "10GHC10", "DN 80", "CLEAN DRAIN", "DRAIN PRESSURE"),
    ]
    rows.append(dict(inst("v1", "MOV(GATE)", "10LBA10AA001", 380, 200, "10LBA10", "DN 400", "HP STEAM", ""), tab="MOV"))
    rows.append(dict(inst("v2", "BUTTERFLY", "10PGB10AA201", 960, 480, "10PGB10", "DN 150", "CLOSED COOLING WATER", ""), tab="BFV"))
    return rows


def _merged(rows):
    """store_result 가 읽는 꼴 → scene.build 가 읽는 꼴(merged row) 로 — DB 를 거치지 않고."""
    out = []
    for r in rows:
        v = {k: r.get(k) for k in db.EDITABLE}
        out.append({"key": r["key"], "tab": r["tab"], "page_no": r["page_no"], "rect": r["rect"], "values": v, "evidence": r["evidence"]})
    return out


def test_scene_places_and_tags_everything_from_the_pid():
    sc = scene.build(_merged(_rows()), {"width": 1190, "height": 842}, "D-1", "HP STEAM")
    assert sc["counts"] == {"instruments": 5, "valves": 2, "equipment": 1, "pipes": 3}
    tags = {i["tag"] for i in sc["instruments"]}
    assert "10LBA10CP001" in tags and all(i.get("pid_rect") for i in sc["instruments"])     # 태그 · 자리는 P&ID 것
    eq = sc["equipment"][0]
    assert eq["tag"] == "COMPRESSOR 10LBA10AP001" and eq["sym"] == "compressor"                # 기기 이름도 도면이 인쇄한 라벨
    kinds = {p["id"]: p["kind"] for p in sc["pipes"]}
    assert kinds["10LBA10"] == "process" and kinds["10PGB10"] == "cooling" and kinds["10GHC10"] == "drain"
    assert any(p["kind"] == "signal" for p in sc["pipes"])                                     # PIT → 같은 태그 PIC 신호선
    sym = {v["sym"] for v in sc["valves"]}
    assert sym == {"valve_control_electric", "valve_manual"}
    assert sc["panels"]["control"]["tag"] == "10LBA10CP001" and sc["panels"]["motor"] == eq["id"]
    assert all(i["logic"] is None for i in sc["instruments"]) and sc["links"]["logic"] is None   # LOGIC 연결 자리 (추후)
    # 자리는 행이 차지하는 범위를 캔버스에 맞춘 것 — 한구석에 모이지 않는다
    xs = [i["x"] for i in sc["instruments"]] + [v["x"] for v in sc["valves"]]
    assert max(xs) - min(xs) > scene.W * 0.5


def test_scene_symbols_exist_in_the_component_library():
    names = _sym_names()
    sc = scene.build(_merged(_rows()), {"width": 1190, "height": 842})
    used = {e["sym"] for e in sc["equipment"]} | {v["sym"] for v in sc["valves"]}
    assert used <= names
    ex = json.loads((ROOT / "config" / "hmi_example_compressor_train.json").read_text(encoding="utf-8"))
    assert {e["sym"] for e in ex["equipment"]} | {v["sym"] for v in ex["valves"]} <= names
    for req in ("compressor", "separator", "valve_control_pneumatic", "pump", "heat_exchanger", "instrument", "motor"):
        assert req in names


def test_reference_png_is_not_used_as_background():
    for f in ("hmi.html", "hmi.css", "hmi.js", "hmi_symbols.js"):
        assert ".png" not in (STATIC / f).read_text(encoding="utf-8").lower()
    assert not list((ROOT / "app" / "static").rglob("*.png")) or all("hmi" not in str(p) for p in (ROOT / "app" / "static").rglob("*.png"))


def test_store_requires_author_and_round_trips(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from app import paths
    assert paths.data_dir() == tmp_path.resolve() or str(tmp_path) in str(paths.data_dir())
    with pytest.raises(ValueError):
        store.save("job1", 6, {"a": 1}, "")
    out = store.save("job1", 6, {"instruments": [{"tag": "X"}]}, "홍길동")
    assert out["saved_by"] == "홍길동" and out["generated"] is False
    assert store.load("job1", 6)["instruments"][0]["tag"] == "X"
    assert store.delete("job1", 6) and store.load("job1", 6) is None


def test_api_builds_saves_and_resets_a_scene(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from fastapi.testclient import TestClient
    from app.hmi import api as hmi_api
    con = db.connect(tmp_path / "t.db")
    pdf = tmp_path / "x.pdf"; pdf.write_bytes(b"%PDF-1.4\n")
    db.create_job(con, "j", "pid.pdf", "sha", pdf)
    db.store_result(con, "j", {"fingerprint": "f", "rows": _rows(), "layers": {"6": {}}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
                                "pages": [{"page_no": 6, "drawing_no": "D-1", "title": "HP STEAM", "page_kind": "PID", "in_scope": 1,
                                           "scope_reason": "", "width": 1190, "height": 842}]})
    con.commit()
    from fastapi import FastAPI
    app = FastAPI()
    hmi_api.bind(con)
    app.include_router(hmi_api.router)
    c = TestClient(app)
    assert c.get("/hmi").status_code == 200
    assert c.get("/hmi/api/example").json()["title"].startswith("DCS Graphic")
    jobs = c.get("/hmi/api/jobs").json()
    assert jobs and jobs[0]["id"] == "j" and jobs[0]["filename"] == "pid.pdf"
    pages = c.get("/hmi/api/jobs/j/pages").json()
    assert pages[0]["rows"] == 7 and pages[0]["saved"] is False
    sc = c.get("/hmi/api/jobs/j/scene/6").json()
    assert sc["generated"] and sc["counts"]["instruments"] == 5
    sc["instruments"][0]["x"] = 999
    assert c.post("/hmi/api/jobs/j/scene/6", json={"scene": sc, "author": ""}).status_code == 400
    r = c.post("/hmi/api/jobs/j/scene/6", json={"scene": sc, "author": "홍길동"}).json()
    assert r["ok"]
    again = c.get("/hmi/api/jobs/j/scene/6").json()
    assert again["saved"] and again["instruments"][0]["x"] == 999 and again["saved_by"] == "홍길동"
    assert c.get("/hmi/api/jobs/j/scene/6?fresh=1").json()["instruments"][0]["x"] != 999
    assert c.delete("/hmi/api/jobs/j/scene/6").json()["removed"] is True
    assert c.get("/hmi/api/jobs/j/scene/6").json()["generated"] is True


def test_hmi_does_not_import_the_pid_engine():
    import ast
    for f in (ROOT / "app" / "hmi").glob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(tree):
            mods = [n.module] if isinstance(n, ast.ImportFrom) else [a.name for a in n.names] if isinstance(n, ast.Import) else []
            for m in mods:
                assert not (m or "").startswith("app.engine") and not (m or "").startswith("app.pipeline"), f
