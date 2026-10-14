"""LOGIC L24 — 식별률 · 마크업 (못 읽은 10% 를 사람이 도면 위에서 넣는다).

합성 두 장 묶음(spike/logic_variants.py 의 base): A 장 51행 → B 장 2행 (FM AB_G-101-51).
읽기가 실패한 상황을 결과에서 지워 흉내 내고(시트 이름 · FM 칸 · 블록 종류), 마크업 하나로 연결 · 시뮬레이션 ·
식별률이 돌아오는지 본다.  분석 결과 파일은 바뀌지 않는다.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def base(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("logic_variants", os.path.join(ROOT, "spike", "logic_variants.py"))
    lv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lv)
    from app.logic import analyse
    p = str(tmp_path_factory.mktemp("l24") / "base.pdf")
    lv.make(next(x for x in lv.VARIANTS if x.name == "base"), p)
    return analyse.analyse(p)


def _apply(res, marks, tmp_path):
    from app.logic import overrides
    d = tmp_path / "job"
    d.mkdir(exist_ok=True)
    for m in marks:
        overrides.set_mark(d, m["page"], m.get("id"), m["kind"], m["rect"], m.get("value"), "홍길동",
                           m.get("row"), m.get("choice"), m.get("param"))
    out = copy.deepcopy(res)
    from app.logic import fromto
    fromto.check(out["sheets"])
    overrides.apply(out, overrides.load(d))
    return out, d


def _sheet(res, page):
    return next(s for s in res["sheets"] if s["page"] == page)


def test_idrate_counts_and_flags_a_silent_failure(base):
    from app.logic import fromto, idrate
    good = copy.deepcopy(base)
    fromto.check(good["sheets"])
    m = idrate.measure(good)
    assert m["rate"]["sheet"] == 1.0 and m["rate"]["link"] == 1.0 and not m["low"]
    bad = copy.deepcopy(base)
    for s in bad["sheets"]:
        s["sheet_no"] = ""                        # 옛 1A5J 처럼 시트 이름을 못 읽음
    fromto.check(bad["sheets"])
    m = idrate.measure(bad)
    assert "sheet" in m["low"] and "link" in m["low"]
    assert any(it["kind"] == "SHEET" for it in m["items"])


def test_sheet_name_markup_restores_the_link(base, tmp_path):
    res = copy.deepcopy(base)
    _sheet(res, 1)["sheet_no"] = ""
    a_rect = [700, 20, 800, 40]
    out, _ = _apply(res, [{"page": 1, "kind": "SHEET", "rect": a_rect, "value": "ab_g-101"}], tmp_path)
    b = _sheet(out, 2)
    r2 = next(r for r in b["rows"] if r["side"] == "L" and r["n"] == 2)
    assert _sheet(out, 1)["sheet_no"] == "AB_G-101"
    assert r2["ref"]["page"] == 1 and r2["ft"]["ok"] is True


def test_from_markup_on_unread_cell_links_and_simulates(base, tmp_path):
    from app.logic import sim
    res = copy.deepcopy(base)
    t = next(x for x in _sheet(res, 2)["table"] if x["side"] == "L" and x["n"] == 2)
    t["fm"] = ""                                  # FM 칸을 못 읽음
    rect = [t["fm_box"][0], t["y0"], t["fm_box"][2], t["y1"]]
    out, d = _apply(res, [{"page": 2, "kind": "FROM", "rect": rect, "value": "AB_G-101-51"}], tmp_path)
    r2 = next(r for r in _sheet(out, 2)["rows"] if r["side"] == "L" and r["n"] == 2)
    assert r2["ref"]["page"] == 1 and r2["user"]["fm"]["author"] == "홍길동"
    mk = _sheet(out, 2)["marks"][0]
    assert mk["ok"] and mk["n"] == 2
    # A 장 51행(AND 출력)을 1 로 → 마크업으로 이은 B 장 2행이 1
    got = sim.simulate_bundle(out["sheets"], {1: {"row:2": 1, "row:3": 1}}, {}, None)
    assert got["linked"].get(2, {}).get(2) == 1 or got["linked"].get("2", {}).get("2") == 1, got["linked"]
    # 분석 결과는 그대로 · 지우면 도면 값으로
    assert next(x for x in _sheet(res, 2)["table"] if x["side"] == "L" and x["n"] == 2)["fm"] == ""
    from app.logic import overrides
    overrides.set_mark(d, 2, mk["id"], None, None, None, "홍길동")
    assert not overrides.load(d)["marks"]


def test_from_markup_on_a_row_the_table_missed_makes_the_row(base, tmp_path):
    from app.logic import idrate
    res = copy.deepcopy(base)
    b = _sheet(res, 2)
    b["table"] = [x for x in b["table"] if not (x["side"] == "L" and x["n"] == 2)]
    b["rows"] = [x for x in b["rows"] if not (x["side"] == "L" and x["n"] == 2)]
    out, _ = _apply(res, [{"page": 2, "kind": "FROM", "rect": [40, 60, 90, 72], "value": "AB_G-101-51", "row": 2}], tmp_path)
    b2 = _sheet(out, 2)
    mk = b2["marks"][0]
    assert mk["made_row"] and any(x["n"] == 2 and x["side"] == "L" and x["fm"] == "AB_G-101-51" for x in b2["table"])
    r2 = next(r for r in b2["rows"] if r["side"] == "L" and r["n"] == 2)
    assert r2["ref"]["page"] == 1
    idrate.measure(out)                            # 선이 없는 행이어도 세기가 죽지 않는다


def test_from_markup_without_row_where_there_is_no_row_says_why(base, tmp_path):
    out, _ = _apply(copy.deepcopy(base), [{"page": 2, "kind": "FROM", "rect": [10, 900, 40, 910], "value": "AB_G-101-51"}], tmp_path)
    mk = _sheet(out, 2)["marks"][0]
    assert mk["ok"] is False and "행 번호" in mk["why"]


def test_gate_markup_sets_the_block_under_the_box(base, tmp_path):
    res = copy.deepcopy(base)
    blk = _sheet(res, 1)["blocks"]["B4"]
    blk["func"], blk["logic"] = "UNKNOWN", "unknown"
    x0, y0, x1, y1 = blk["bbox"]
    out, _ = _apply(res, [{"page": 1, "kind": "GATE", "rect": [x0 - 1, y0 - 1, x1 + 1, y1 + 1], "choice": "OR"}], tmp_path)
    b4 = _sheet(out, 1)["blocks"]["B4"]
    assert b4["func"] == "OR" and b4["logic"] == "or" and b4["user"]["author"] == "홍길동"


def test_markup_validation(tmp_path):
    from app.logic import overrides
    with pytest.raises(ValueError):
        overrides.set_mark(tmp_path, 1, None, "FROM", [0, 0, 10, 10], "X-1", "")          # 작성자 없음
    with pytest.raises(ValueError):
        overrides.set_mark(tmp_path, 1, None, "WHAT", [0, 0, 10, 10], "X-1", "a")
    with pytest.raises(ValueError):
        overrides.set_mark(tmp_path, 1, None, "FROM", [0, 0, 0.1, 0.1], "X-1", "a")      # 너무 작음
    with pytest.raises(ValueError):
        overrides.set_mark(tmp_path, 1, None, "GATE", [0, 0, 10, 10], None, "a", choice="NOPE")


def test_overprinted_words_are_one_word():
    from app.logic import geom
    ws = [(1, 2, 3, 4, "AND", 0, 0, 0), (1.01, 2, 3, 4, "AND", 0, 0, 1), (5, 2, 7, 4, "AND", 0, 0, 2)]
    assert [w[4] for w in geom._one_print(ws)] == ["AND", "AND"]


def test_api_markup_and_idrate(base, tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.logic import api, store
    d = store.root() / "a24b24c24d24"
    d.mkdir(parents=True, exist_ok=True)
    res = copy.deepcopy(base)
    next(x for x in _sheet(res, 2)["table"] if x["side"] == "L" and x["n"] == 2)["fm"] = ""
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    ir = c.get("/logic/api/jobs/a24b24c24d24/idrate").json()
    assert "rate" in ir and ir["counts"]["sheet"]["all"] == 2
    t = next(x for x in res["sheets"][1]["table"] if x["side"] == "L" and x["n"] == 2)
    body = {"page": 2, "kind": "FROM", "rect": [t["fm_box"][0], t["y0"], t["fm_box"][2], t["y1"]],
            "value": "AB_G-101-51", "author": "홍길동"}
    r = c.post("/logic/api/jobs/a24b24c24d24/overrides/mark", json=body).json()
    assert r["mark"]["ok"] and r["ref"]["page"] == 1
    assert c.post("/logic/api/jobs/a24b24c24d24/overrides/mark", json={**body, "author": ""}).status_code == 400
    sh = c.get("/logic/api/jobs/a24b24c24d24/sheet/2").json()
    assert sh["marks"][0]["value"] == "AB_G-101-51"
