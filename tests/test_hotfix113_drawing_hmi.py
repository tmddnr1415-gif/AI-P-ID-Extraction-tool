"""hotfix113 — 식별이 끝난 P&ID 의 **도면 기하**로 HMI 그래픽을 (예시 Overview 결).

배관은 도면이 그린 선 전체 · 장비는 그 이름이 인쇄된 닫힌 외곽의 자리와 크기 · 커넥터 · 직경 글은 도면 그대로.
그래픽 전용 — 판정 0줄 · 엔진 import 0 · 분석 결과와 지문에 닿지 않는다.  합성 PDF 로 재고 실물(08b · AL NOUF1)은
`spike/ui_audit_hmi113.py` 화면 확인으로 본다."""
from __future__ import annotations

import ast
import copy
from pathlib import Path

import pymupdf
import pytest

from app.hmi import pidgeom, scene

ROOT = Path(__file__).resolve().parent.parent
BUB = 22.0
AREA = [40.0, 40.0, 1160.0, 800.0]


def _page(doc, rotate=0):
    """합성 도면 한 장 — 탱크(닫힌 외곽 · 안에 이름) · 펌프 상자 둘(`A`·`B` · 밑에 명사 글줄) · 배관 · 점선 연장 ·
    커넥터 상자 · 직경 글 · 계기 버블과 인출선 · 테두리 · 공급 범위 짧은 선."""
    pg = doc.new_page(width=1200, height=840)
    sh = pg.new_shape()
    sh.draw_rect(pymupdf.Rect(*AREA))                                   # 테두리
    sh.draw_rect(pymupdf.Rect(500, 200, 700, 420))                       # 탱크
    sh.draw_line((100, 300), (500, 300))                                 # 배관 — 커넥터에서 탱크로
    sh.draw_line((700, 300), (900, 300))
    sh.draw_line((900, 300), (900, 600))
    sh.draw_line((900, 600), (1000, 600))
    sh.draw_rect(pymupdf.Rect(300, 560, 420, 610))                       # 펌프 A 상자
    sh.draw_rect(pymupdf.Rect(300, 660, 420, 710))                       # 펌프 B 상자
    sh.draw_line((420, 585), (900, 585))                                 # 펌프 A 토출 → 세로 배관
    sh.draw_line((600, 100), (600, 140))                                 # 짧은 외톨이 선 (공급 범위 표시 따위)
    for k in range(10):                                                  # 실선 끝에서 이어지는 점선 배관 (협력사 범위)
        sh.draw_line((1000 + k * 14, 600), (1000 + k * 14 + 8, 600))
    sh.draw_rect(pymupdf.Rect(40 + 10, 285, 100, 315))                   # 커넥터 상자 (글 TO …)
    sh.draw_oval(pymupdf.Rect(760, 240, 760 + BUB * 2, 240 + BUB))       # 계기 버블
    sh.draw_line((782, 262), (782, 300))                                 # 인출선 — 버블에서 배관으로
    sh.finish(color=(0, 0, 0), width=0.5)
    sh.commit()
    pg.insert_text((540, 310), "FEED TANK", fontsize=10)
    pg.insert_text((356, 590), "A", fontsize=10)
    pg.insert_text((356, 690), "B", fontsize=10)
    pg.insert_text((300, 740), "BOOSTER PUMP (A/B)", fontsize=9)
    pg.insert_text((54, 304), "TO DRAIN", fontsize=8)
    pg.insert_text((760, 296), "DN100", fontsize=7)
    if rotate:
        pg.set_rotation(rotate)
    return pg


def _read(rotate=0):
    doc = pymupdf.open()
    pg = _page(doc, rotate)
    W, H = pg.rect.width, pg.rect.height
    bubble = [760, 240, 760 + BUB * 2, 240 + BUB]
    if rotate == 90:                                                     # 표시 좌표로 (행 사각형과 같은 틀)
        T = lambda x, y: (840 - y, x)                                    # noqa: E731 — rotation_matrix (0,1,-1,0,840,0)
        a, b = T(bubble[0], bubble[1]), T(bubble[2], bubble[3])
        bubble = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
        c, d = T(AREA[0], AREA[1]), T(AREA[2], AREA[3])
        area = [min(c[0], d[0]), min(c[1], d[1]), max(c[0], d[0]), max(c[1], d[1])]
    else:
        area = AREA
    return pidgeom.read_page(pg, {"area": area, "bubble": BUB, "avoid": [bubble], "bubbles": [bubble]}), W, H


def _has(pipes, x0, y0, x1, y1, tol=2.0):
    return any(abs(p[0] - x0) <= tol and abs(p[1] - y0) <= tol and abs(p[2] - x1) <= tol and abs(p[3] - y1) <= tol for p in pipes)


def test_reads_the_pipe_network_equipment_connectors_and_sizes():
    g, _, _ = _read()
    pipes = g["pipes"]
    assert _has(pipes, 100, 300, 500, 300) and _has(pipes, 700, 300, 900, 300) and _has(pipes, 900, 300, 900, 600)
    assert not any(p[0] == p[2] == 782.0 for p in pipes)                 # 인출선(버블 → 배관)은 배관이 아니다
    assert not any(p[0] == p[2] == 600 and p[1] < 200 for p in pipes)    # 어디에도 안 닿는 짧은 선
    assert not any(abs(p[1] - AREA[1]) < 3 or abs(p[0] - AREA[0]) < 3 for p in pipes)   # 테두리
    assert not any(p[1] == p[3] and 280 <= p[1] <= 320 and p[2] <= 110 for p in pipes)  # 커넥터 상자 변
    dashed = [p for p in pipes if len(p) > 4 and p[4] == "dashed"]
    assert len(dashed) == 1 and dashed[0][1] == 600 and dashed[0][0] >= 999      # 실선 끝에서 이어 그린 점선만
    names = {s["name"]: s for s in g["shapes"]}
    tank = names["FEED TANK"]
    assert tank["noun"] == "TANK" and 495 <= tank["rect"][0] <= 505 and 695 <= tank["rect"][2] <= 705
    assert "BOOSTER PUMP (A/B) (A)" in names and "BOOSTER PUMP (A/B) (B)" in names     # 상자 글 + 가까운 명사 글줄 (형제 상자도)
    assert names["BOOSTER PUMP (A/B) (A)"]["noun"] == "PUMP"
    assert not any(p[1] == p[3] and 200 < p[1] < 420 and p[0] >= 505 and p[2] <= 695 for p in pipes)  # 탱크 외곽은 배관이 아니다
    assert [c["dir"] + " " + c["name"] for c in g["conns"]] == ["TO DRAIN"]
    assert [s["text"] for s in g["sizes"]] == ["DN100"]


def test_rotated_sheet_reads_in_display_coordinates():
    g0, _, _ = _read(0)
    g9, W, H = _read(90)
    t0 = next(s for s in g0["shapes"] if s["name"] == "FEED TANK")["rect"]
    t9 = next(s for s in g9["shapes"] if s["name"] == "FEED TANK")["rect"]
    # 90° 돌린 장: 표시 x = 원래 높이 − y · 표시 y = x
    assert abs(t9[0] - (840 - t0[3])) <= 2 and abs(t9[1] - t0[0]) <= 2
    # 주 배관이 돌린 자리에 그대로 선다 (가로 → 세로)
    for x0, y0, x1, y1 in ([100, 300, 500, 300], [900, 300, 900, 600], [420, 585, 900, 585]):
        a, b = (840 - y0, x0), (840 - y1, x1)
        assert _has(g9["pipes"], min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])), (x0, y0, x1, y1)


def _model_with_geom():
    g, _, _ = _read()
    run = [100.0, 300.0, 500.0, 300.0]
    return {"page_no": 5, "drawing_no": "D00P-10LBA10-M05-0001", "title": "P&ID FOR FEED SYSTEM", "width": 1200.0, "height": 840.0,
            "instruments": [{"key": "5-i1", "tag": "10LBA10CP001", "type": "PIT", "rect": [760, 240, 760 + BUB * 2, 240 + BUB],
                             "scope": "SCT", "line_no": "", "line_size": "", "lines": 0, "equip": "", "review": False, "tap": [700.0, 300.0, 900.0, 300.0]}],
            "valves": [], "pipes": [{"seg": run, "role": "tap"}, {"seg": [700.0, 300.0, 900.0, 300.0], "role": "tap"}],
            "equipment": [{"name": "FEED TANK", "rect": [540, 300, 600, 312], "noun": "TANK"}],
            "connectors": [], "line_labels": [], "tagged": 1, "geom": g}


def test_scene_draws_the_drawing_not_just_tapped_runs():
    md = _model_with_geom()
    sc = scene.from_model(copy.deepcopy(md))
    drawn = [p for p in sc["pipes"] if p.get("from_drawing")]
    assert len(drawn) == len(md["geom"]["pipes"]) and sc["geom"]["pipes"] == len(drawn)
    assert not any(p.get("role") == "tap" for p in sc["pipes"])          # 탭한 런은 그 런을 품은 도면 배관으로 바뀐다
    ins = sc["instruments"][0]
    on = next(p for p in sc["pipes"] if p["id"] == ins["on"])
    assert on.get("from_drawing") and on["label"] == "DN100"             # 계기는 그 도면 배관에 · 직경 글이 이름표
    into_drain = next(p for p in drawn if p["pid_seg"][:4] == [100.0, 300.0, 500.0, 300.0])
    assert into_drain["arrow"] and into_drain["pts"][1][0] < into_drain["pts"][0][0]     # TO DRAIN 쪽으로 흐름
    assert sum(1 for p in drawn if p.get("arrow")) == 1                  # 화살은 도면의 TO/FROM 이 말한 곳만
    assert any(p.get("style") == "dashed" for p in drawn)
    # 장비 — 도면 외곽 자리 · 크기 그대로 (배율만) · 이름 자리 기기는 외곽이 있으면 두 번 그리지 않는다
    tanks = [e for e in sc["equipment"] if e["tag"] == "FEED TANK"]
    assert len(tanks) == 1 and tanks[0]["from_drawing"] and tanks[0]["sym"] == "storage_tank"
    assert abs(tanks[0]["w"] - 200 * sc["scale"]) <= 12 and abs(tanks[0]["h"] - 220 * sc["scale"]) <= 12
    pumps = [e for e in sc["equipment"] if "BOOSTER PUMP" in e["tag"]]
    assert {e["sym"] for e in pumps} == {"pump"} and len(pumps) == 2
    assert any(l["kind"] == "conn" and l["text"] == "To DRAIN" for l in sc["labels"])
    assert "도면 기하" in sc["basis"]


def test_shape_without_a_known_noun_is_a_plain_box_not_an_invented_vessel():
    assert scene.drawn_sym("") == "equipment_box" and scene.drawn_sym("EJECTOR") == "equipment_box"
    assert scene.drawn_sym("TANK") == "storage_tank" and scene.drawn_sym("TURBINE") == "turbine"
    js = (ROOT / "app" / "static" / "hmi" / "hmi_symbols.js").read_text(encoding="utf-8")
    assert 'def("equipment_box"' in js
    hmi = (ROOT / "app" / "static" / "hmi" / "hmi.js").read_text(encoding="utf-8")
    assert 'p.style === "dashed"' in hmi and "e.from_drawing" in hmi


def test_old_scene_unchanged_without_geom():
    md = _model_with_geom()
    md.pop("geom")
    sc = scene.from_model(md)
    assert "geom" not in sc and not any(p.get("from_drawing") for p in sc["pipes"])
    assert not any(e.get("from_drawing") for e in sc["equipment"])


def test_system_scene_does_not_inflate_drawn_equipment():
    a = _model_with_geom()
    b = copy.deepcopy(a)
    b["page_no"], b["drawing_no"] = 6, "D00P-10LBA10-M05-0002"
    for i in b["instruments"]:
        i["key"] = "6-" + i["key"]
    one = scene.from_model(copy.deepcopy(a))
    sc = scene.from_system([a, b], key="D00P-10LBA10-M05")
    t1 = next(e for e in one["equipment"] if e["tag"] == "FEED TANK")
    t2 = next(e for e in sc["equipment"] if e["tag"] == "FEED TANK")
    assert abs(t1["w"] - t2["w"]) < 0.5 and abs(t1["h"] - t2["h"]) < 0.5


def test_graphics_only_no_engine_imports():
    for f in ("app/hmi/pidgeom.py", "app/hmi/scene.py"):
        tree = ast.parse((ROOT / f).read_text(encoding="utf-8"))
        mods = [n.module or "" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + \
               [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        assert not any(m.startswith("app.engine") or m in ("pipeline", "detect_symbols", "pidcache") or m == "app.pipeline"
                       for m in mods), (f, mods)


def test_geom_cache_is_outside_the_analysis(tmp_path, monkeypatch):
    """도면 기하는 `{data}/hmi/<분석>/geom/` 에 기억된다 — 분석 결과(행 · 지문)에 넣지 않는다."""
    from app import dcs
    src = (ROOT / "app" / "dcs.py").read_text(encoding="utf-8")
    assert 'paths.data_dir() / "hmi" / job_id / "geom"' in src
    assert "attach_geom(job_id, [s])" in src and "attach_geom(job_id, models)" in src
    h = dcs.geom_hints({"instruments": [{"rect": [0, 0, 40, 20]}], "valves": [{"rect": [50, 0, 60, 10], "tag_rect": [70, 0, 90, 10]}]}, [1, 2, 3, 4])
    assert h["bubble"] == 20 and h["area"] == [1, 2, 3, 4] and len(h["avoid"]) == 3 and h["bubbles"] == [[0, 0, 40, 20]]


def _pump_page():
    """펌프 둘 (원 + 받침 · path 구성 같음) · 그 아래 두 줄 이름표 하나 · 옆에 `M` 이 든 원(전동기 표시)."""
    doc = pymupdf.open()
    pg = doc.new_page(width=1200, height=840)
    for cy in (300, 420):
        sh = pg.new_shape()
        sh.draw_circle((600, cy), 18)
        sh.draw_line((585, cy + 18), (615, cy + 18))
        sh.finish(color=(0, 0, 0), width=0.5)
        sh.commit()
    sh = pg.new_shape()
    sh.draw_circle((800, 300), 18)
    sh.finish(color=(0, 0, 0), width=0.5)
    sh.commit()
    sh = pg.new_shape()
    sh.draw_line((300, 300), (582, 300))
    sh.draw_line((300, 420), (582, 420))
    sh.finish(color=(0, 0, 0), width=0.5)
    sh.commit()
    pg.insert_text((560, 462), "CLEAN DRAIN", fontsize=9)
    pg.insert_text((572, 474), "PUMP", fontsize=9)
    pg.insert_text((796, 304), "M", fontsize=9)
    return doc, pg


def test_pumps_named_below_their_round_body():
    doc, pg = _pump_page()
    g = pidgeom.read_page(pg, {"area": AREA, "bubble": BUB, "avoid": [], "bubbles": []})
    pumps = [s for s in g["shapes"] if s["noun"] == "PUMP"]
    assert len(pumps) == 2 and {s["name"] for s in pumps} == {"CLEAN DRAIN PUMP"}          # 두 줄 이름표 · 같은 꼴 형제
    assert sorted(round(s["rect"][1]) for s in pumps) == [282, 402]
    assert not any(s["rect"][0] > 700 for s in g["shapes"])                                # `M` 이 든 원은 펌프가 아니다
    assert pidgeom._noun_of("SLOP OIL TANK FOR TRANSFER PUMP AREA") == "TANK"
    assert pidgeom._noun_of("COGENERATION FEEDWATER PUMP A MOTOR") == "MOTOR"
    blocks = [b[4] for b in pidgeom.label_blocks(pidgeom.phrases(pidgeom.words(pg)))]
    assert "CLEAN DRAIN PUMP" in blocks
