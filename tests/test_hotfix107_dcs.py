"""hotfix107 — 간략화 DCS 그래픽: 저장된 식별 결과(태그 있는 실행 P&ID)만 옮겨 그린다."""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app import dcs

ROOT = Path(__file__).resolve().parent.parent


def _row(key, tab, rect, tag="", type_="PIT", scope="SCT", ev=None, **values):
    deleted = values.pop("deleted", 0)
    v = {"tag_no": tag, "type": type_, "scope": scope, "line_no": "", "line_size": ""}
    v.update(values)
    return {"key": key, "tab": tab, "page_no": 5, "rect": rect, "values": v, "evidence": ev or {},
            "deleted": deleted, "removed": 0, "needs_review": ""}


PAGE = {"page_no": 5, "drawing_no": "1A1Y-10LBB50-M05-0001", "title": "HP STEAM", "width": 2384.0, "height": 1684.0}


def _rows():
    axis = {"axis": "②b", "equip": "", "ev": {"run": ["V", 844.4, 568.5, 805.2], "trunk": [["H", 568.5, 624.7, 962.3]],
                                             "mid_runs": [["H", 724.4, 528.4, 844.4]],
                                             "ends": [{"kind": "CONN", "dir": "TO", "name": "BD TANK", "at": [528, 724]}]}}
    cands = [{"kind": "EQUIPMENT", "text": "HRSG#12 BD TANK", "rect": [1774.6, 770.6, 1852.5, 785.1], "equipment": {"noun": "TANK"}},
             {"kind": "CONNECTOR", "text": "TO X", "rect": [1, 1, 2, 2]}]
    line = {"line_no": "12LBB50", "size": "DN 800", "rect": [600, 500, 640, 512], "run": ["H", 520.0, 300.0, 900.0]}
    return [
        _row("k1", "FIELD", [431.3, 437.4, 499.3, 460.1], "12LBB50CP001", "PIT", "SCT",
             {"axis": axis, "candidates": cands, "line": line, "detail": {"bubble_lines": 1}}, line_no="12LBB50", line_size="DN 800"),
        _row("k2", "FIELD", [431.3, 480.0, 499.3, 502.0], "12LBB50CT001", "TIT", "VENDOR(HRSG)", {"axis": axis}),
        _row("k3", "FIELD", [200, 200, 223, 223], "", "LS", "SCT"),                       # 태그 없음 · 좁은 버블
        _row("k4", "MOV", [666.4, 719.4, 683.5, 729.3], "12LBB50AA105", "GLOBE", "SCT",
             {"body": "GLOBE", "actuator": "MOTOR", "state": "CLOSED", "tag_rect": [595, 664, 663, 687]}, valve_type="MOTOR"),
        _row("k5", "FIELD", [900, 900, 968, 922], "12LBB50CP999", "PIT", "SCT", deleted=1),  # 지운 행
    ]


def test_sheet_model_takes_only_saved_facts():
    s = dcs.build_sheet(PAGE, _rows())
    assert [i["tag"] for i in s["instruments"]] == ["", "12LBB50CP001", "12LBB50CT001"]   # 지운 행은 없다 · 위→아래
    assert s["instruments"][1]["line_no"] == "12LBB50" and s["instruments"][1]["lines"] == 1
    assert s["valves"][0]["actuator"] == "MOTOR" and s["valves"][0]["tag"] == "12LBB50AA105"
    roles = {tuple(p["seg"]): p["role"] for p in s["pipes"]}
    assert roles[(844.4, 568.5, 844.4, 805.2)] == "tap" and roles[(300.0, 520.0, 900.0, 520.0)] == "line"
    assert roles[(624.7, 568.5, 962.3, 568.5)] == "branch" and len(s["pipes"]) == 4      # 같은 런은 한 번
    assert s["equipment"] == [{"name": "HRSG#12 BD TANK", "rect": [1774.6, 770.6, 1852.5, 785.1], "noun": "TANK"}]
    assert s["connectors"] == [{"name": "BD TANK", "dir": "TO", "at": [528.0, 724.0]}]
    assert s["line_labels"][0]["line_no"] == "12LBB50" and s["tagged"] == 3


def test_svg_names_every_tagged_element_and_paints_states():
    s = dcs.build_sheet(PAGE, _rows())
    svg = dcs.render_svg(s)
    assert svg.count('data-tag="12LBB50CP001"') == 1 and 'data-tag="12LBB50AA105"' in svg
    assert "----" in svg and "(태그 없음)" not in svg and "100%" not in svg          # 값은 비어 있다 · MuPDF 가 못 그리는 % 없음
    assert "HRSG#12 BD TANK" in svg and "BD TANK" in svg and "12LBB50 DN 800" in svg
    painted = dcs.render_svg(s, {"12LBB50CP001": {"v": 52.3, "u": "barg", "alarm": True},
                                 "12LBB50AA105": {"open": True}, "12LBB50CT001": {"s": 0}})
    assert "52.30 barg" in painted and "<animate" in painted and ">OFF<" in painted
    assert painted.count(f'fill="{dcs.C["open"]}"') >= 2                       # 밸브 나비 두 쪽이 열림 색


def test_png_renders_without_a_browser():
    s = dcs.build_sheet(PAGE, _rows())
    png = dcs.render_png(dcs.render_svg(s), dpi=40)
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 2000


def test_narrow_bubble_gets_a_narrow_faceplate():
    s = dcs.build_sheet(PAGE, _rows())
    svg = dcs.render_svg(s)
    narrow = svg.split('data-key="k3"')[1].split("</g>")[0]
    assert 'width="28.0"' in narrow and 'stroke-dasharray' in narrow             # 23pt 버블 → 하한 28 · 태그 없음 = 점선


def test_tag_index_is_what_logic_links_by():
    idx = dcs.tag_index([dcs.build_sheet(PAGE, _rows())])
    assert {t["tag"] for t in idx} == {"12LBB50CP001", "12LBB50CT001", "12LBB50AA105"}
    v = next(t for t in idx if t["kind"] == "VALVE")
    assert v["actuator"] == "MOTOR" and v["drawing_no"] == PAGE["drawing_no"]


def test_only_epc_results_are_eligible(monkeypatch):
    from app import main
    calls = {}
    class _Job(dict):
        def __getitem__(self, k): return dict.get(self, k)
    monkeypatch.setattr(main.db, "get_job", lambda con, j: _Job(status="done", pdf_name="x.pdf", project="P"))
    monkeypatch.setattr(main, "_mode_facts", lambda job: {"effective": "bid", "tagged_rows": 0})
    job, el = dcs._eligibility("j")
    assert el["eligible"] is False and "실행" in el["reason"]
    monkeypatch.setattr(main, "_mode_facts", lambda job: {"effective": "epc", "tagged_rows": 12})
    assert dcs._eligibility("j")[1]["eligible"] is True


def test_module_imports_no_engine_and_routes_are_mounted():
    tree = ast.parse((ROOT / "app/dcs.py").read_text(encoding="utf-8"))
    mods = {n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | \
           {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert not any("engine" in m or "pipeline" in m for m in mods)
    main_src = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "include_router(_dcs.router)" in main_src
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    assert 'id="dcs-btn"' in html
    page = (ROOT / "app/static/dcs.html").read_text(encoding="utf-8")
    assert "dcs-states" in page and "/hmi" in page                               # 로직 연동 자리(postMessage) · 사람 값 저장 (hotfix109)
    for part in ("hmi-symbols.js", "hmi-core.js", "hmi-pid-adapter.js", "hmi-demo.js", "hmi.css"):
        assert part in page and (ROOT / "app/static/hmi" / part).exists()
