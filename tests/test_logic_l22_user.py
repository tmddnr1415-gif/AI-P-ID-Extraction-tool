"""L22 — 사람이 정한다 (게이트 종류 · FM/TO 칸 · 타이머 시간) · 첫 화면 지우기 · 학습 사전.

사용자 지시:
  * Gate 식별이 되지 않으면 사용자가 눌러 무엇인지 고르면 그 게이트로 표현된다.
  * 분석된 사항을 부서원이 첫 화면에서 지울 수 있다.
  * FM · TO 식별이 안 되면 사용자가 그 칸에 값을 적어 linking 된다.
  * time delay 는 게이트마다 사용자가 넣는다 — 기본 5초.
  * Signal Processing symbols · MACRO 를 학습해 두고 다른 프로젝트 Logic 도 그 기준으로 분석한다.
"""
from __future__ import annotations

import json
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import api, library, overrides, sim, store


def _P(b, n, d, role="", cell=0, at=(0, 0)):
    return {"block": b, "net": n, "dir": d, "role": role, "cell": cell, "at": list(at)}


def _sheet(page, no, rows, blocks, ports, table=None):
    nets = sorted({p["net"] for p in ports} | {r["net"] for r in rows})
    return {"page": page, "sheet_no": no, "title": f"T{no}", "logic": [100, 0, 500, 800], "pitch": 10, "frame": None,
            "nets": {n: {"segs": [], "dashed": False} for n in nets}, "order": {}, "blocks": blocks, "ports": ports,
            "rows": rows, "table": table if table is not None else [dict(r) for r in rows],
            "dangling": [], "stray_arrows": [], "findings": []}


def _blk(func, logic, bbox=(200, 100, 230, 130), key="", cells=None):
    return {"kind": "RECT", "func": func, "logic": logic, "label": "", "read": "", "score": 0, "bbox": list(bbox),
            "cells": cells or [list(bbox)], "param": {}, "group": "", "pointer": None, "roles": {}, "key": key}


def _bundle():
    """G001: 입력 1·2 → (판정 못 한 블록 X) → 출력 30 (TO G002-5) · 입력 3 → PD(시간 없음) → 출력 31.
    G002: 입력 5 (FM 을 못 읽음 — 빈 칸) → 출력 40 · 입력 6 FM 'G001-31'."""
    s1 = _sheet(1, "G001",
                [{"n": 1, "side": "L", "net": "1", "desc": "A", "fm": ""}, {"n": 2, "side": "L", "net": "2", "desc": "B", "fm": ""},
                 {"n": 3, "side": "L", "net": "3", "desc": "C", "fm": ""},
                 {"n": 30, "side": "R", "net": "9", "desc": "OUT X", "to": "G002-5"},
                 {"n": 31, "side": "R", "net": "4", "desc": "OUT P", "to": "G002-6"}],
                {"X": _blk("UNKNOWN", "unknown", key="|SRST"), "Y": _blk("UNKNOWN", "unknown", (300, 300, 330, 330), key="|SRST"),
                 "PD": _blk("PD", "pulse", (200, 400, 230, 430))},
                [_P("X", "1", "in", at=(200, 110)), _P("X", "2", "in", at=(200, 120)), _P("X", "9", "out", at=(230, 115)),
                 _P("PD", "3", "in"), _P("PD", "4", "out")])
    s2 = _sheet(2, "G002",
                [{"n": 5, "side": "L", "net": "5", "desc": "OUT X", "fm": ""},
                 {"n": 6, "side": "L", "net": "6", "desc": "OUT P", "fm": "G001-31"},
                 {"n": 40, "side": "R", "net": "5", "desc": "FINAL", "to": ""}],
                {}, [])
    return {"pdf_pages": 2, "sheets": [s1, s2], "kinds": {"1": "LOGIC", "2": "LOGIC"}, "dictionary": {},
            "legend": {"pages": [], "symbols": {}, "figures": []}, "seconds": 1, "note": ""}


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _job(res):
    job, d = store.new_job("toy.pdf")
    store.write_result(d, res)
    st = store.read_status(d)
    st.update({"state": "done", "sheets": len(res["sheets"]), "seconds": 1})
    store.write_status(d, st)
    return job, d


def test_default_timer_is_five_seconds():
    assert sim.DEFAULT_T == 5.0
    b = {"param": {}}
    assert sim.timer_seconds(b) == 5.0
    assert sim.timer_seconds({"param": {"t": 3}}) == 3
    assert sim.timer_seconds({"param": {"t": 3, "t_user": 7}}) == 7, "사람이 저장한 시간이 도면 값을 이긴다"
    assert sim.timer_seconds({"param": {"t": 3, "t_user": 7}}, 2) == 2, "요청에 실린 시간이 가장 앞"


def test_user_picks_gate_and_it_behaves_as_that_gate(client):
    job, d = _job(_bundle())
    s = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert s["blocks"]["X"]["func"] == "UNKNOWN"
    # 이름이 없으면 저장하지 않는다
    assert client.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "X", "choice": "AND"}).status_code == 400
    assert client.post(f"/logic/api/jobs/{job}/overrides/block",
                       json={"page": 1, "block": "X", "choice": "WHAT", "author": "홍길동"}).status_code == 400
    r = client.post(f"/logic/api/jobs/{job}/overrides/block",
                    json={"page": 1, "block": "X", "choice": "AND", "author": "홍길동", "same_shape": True}).json()
    assert {(x["page"], x["block"]) for x in r["set"]} == {(1, "X"), (1, "Y")}, "같은 모양 · 같은 글자의 판정 못 한 블록에도"
    s = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    b = s["blocks"]["X"]
    assert b["func"] == "AND" and b["logic"] == "and" and b["user"]["author"] == "홍길동" and b["user"]["was_func"] == "UNKNOWN"
    assert not any(f["code"] == "BLOCK_UNKNOWN" and f.get("block") == "X" for f in s["findings"])
    # 그 게이트대로 돈다 — AND 는 둘 다 1 일 때만
    one = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:1": 1}}).json()
    assert one["frames"][-1]["values"]["9"] == 0
    both = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:1": 1, "row:2": 1}}).json()
    assert both["frames"][-1]["values"]["9"] == 1
    # 분석 결과 파일은 그대로 · 사람 값은 따로 남는다
    assert json.loads((d / "result.json").read_text(encoding="utf-8"))["sheets"][0]["blocks"]["X"]["func"] == "UNKNOWN"
    assert overrides.load(d)["blocks"]["1"]["X"]["choice"] == "AND"
    # 학습 사전에 그 모양이 남는다 (블록 안 글자가 있는 열쇠만)
    assert library.load()["symbols"]["|SRST"]["logic"] == "and"
    # OR 로 바꾸면 한 입력으로 1 · 되돌리면 판정 못 함
    client.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "X", "choice": "OR", "author": "김"})
    assert client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:1": 1}}).json()["frames"][-1]["values"]["9"] == 1
    client.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "X", "choice": None, "author": "김"})
    assert client.get(f"/logic/api/jobs/{job}/sheet/1").json()["blocks"]["X"]["func"] == "UNKNOWN"
    hist = overrides.load(d)["history"]
    assert [h["value"] for h in hist if h["key"] == "X"] == ["AND", "OR", None]


def test_vote_and_memory_choices():
    res = _bundle()
    ov = overrides.empty()
    ov["blocks"] = {"1": {"X": {"choice": "VOTE", "param": {"a": 1, "b": 2}, "label": "1/2", "author": "a"}}}
    overrides.apply(res, ov)
    s = res["sheets"][0]
    assert s["blocks"]["X"]["logic"] == "vote" and s["blocks"]["X"]["param"]["a"] == 1
    assert sim.simulate(s, {"row:2": 1})["frames"][-1]["values"]["9"] == 1
    res = _bundle()
    ov["blocks"] = {"1": {"X": {"choice": "MEMORY_R", "author": "a"}}}
    overrides.apply(res, ov)
    s = res["sheets"][0]
    roles = {p["net"]: p["role"] for p in s["ports"] if p["block"] == "X"}
    assert roles == {"1": "set", "2": "reset", "9": "q"}, "위 단자 = SET · 아래 = RESET · 출력 Q"
    st = sim.simulate(s, {"row:1": 1})
    assert st["frames"][-1]["values"]["9"] == 1
    assert sim.simulate(s, {}, st["state"])["frames"][-1]["values"]["9"] == 1, "래치"
    with pytest.raises(ValueError):
        overrides._vote({"a": 3, "b": 2})


def test_user_types_fm_to_and_it_links(client):
    job, d = _job(_bundle())
    s2 = client.get(f"/logic/api/jobs/{job}/sheet/2").json()
    r5 = next(r for r in s2["rows"] if r["n"] == 5)
    assert not r5.get("ref"), "FM 을 못 읽은 행은 어디서 오는지 모른다"
    # 도면이 TO 로 보냈지만 받는 쪽 FM 이 비어 있다 — 설계 오류(불일치)
    s1 = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert next(r for r in s1["rows"] if r["n"] == 30)["ft"]["ok"] is False
    r = client.post(f"/logic/api/jobs/{job}/overrides/cell",
                    json={"page": 2, "side": "L", "row": 5, "value": "g001-30", "author": "홍길동"}).json()
    assert r["saved"]["fm"] == "G001-30" and r["ref"]["sheet"] == "G001" and r["ref"]["row"] == 30
    assert r["ft"]["ok"] is True
    s1 = client.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert next(r for r in s1["rows"] if r["n"] == 30)["ft"]["ok"] is True, "보내는 쪽도 이제 맞는다"
    t5 = next(t for t in client.get(f"/logic/api/jobs/{job}/sheet/2").json()["table"] if t["side"] == "L" and t["n"] == 5)
    assert t5["fm"] == "G001-30" and t5["user"]["fm"]["author"] == "홍길동" and t5["user"]["fm"]["was"] == ""
    # 시트 사이로 이어진다 — G001 에서 X 를 OR 로 정하고 입력 1 을 주면 G002 5행 · 40행이 1
    client.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "X", "choice": "OR", "author": "홍길동"})
    out = client.post(f"/logic/api/jobs/{job}/simulate", json={"forces": {"1": {"row:1": 1}}, "page": 2}).json()
    assert out["linked"]["2"]["5"] == 1 if "2" in out["linked"] else out["linked"][2][5] == 1
    # TO 칸도 적을 수 있다 · 되돌리면 도면 글자
    r = client.post(f"/logic/api/jobs/{job}/overrides/cell",
                    json={"page": 1, "side": "R", "row": 31, "value": "G002-6", "author": "김"}).json()
    assert r["saved"]["to"] == "G002-6"
    client.post(f"/logic/api/jobs/{job}/overrides/cell", json={"page": 2, "side": "L", "row": 5, "value": None, "author": "김"})
    t5 = next(t for t in client.get(f"/logic/api/jobs/{job}/sheet/2").json()["table"] if t["side"] == "L" and t["n"] == 5)
    assert t5["fm"] == "" and "user" not in t5
    assert client.post(f"/logic/api/jobs/{job}/overrides/cell",
                       json={"page": 2, "side": "L", "row": 99, "value": "X", "author": "김"}).status_code == 404


def test_timer_per_gate_is_saved_on_the_server(client):
    job, d = _job(_bundle())
    ov = client.get(f"/logic/api/jobs/{job}/overrides").json()
    assert ov["default_t"] == 5.0 and any(c["key"] == "AND" for c in ov["choices"])
    r = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:3": 1}}).json()
    assert r["frames"][-1]["t"] == pytest.approx(5.0), "도면에 시간이 없으면 기본 5초"
    assert client.post(f"/logic/api/jobs/{job}/overrides/timer",
                       json={"page": 1, "block": "PD", "sec": -1, "author": "홍길동"}).status_code == 400
    client.post(f"/logic/api/jobs/{job}/overrides/timer", json={"page": 1, "block": "PD", "sec": 2.5, "author": "홍길동"})
    r = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:3": 1}}).json()
    assert r["frames"][-1]["t"] == pytest.approx(2.5), "저장된 시간 — 요청에 시간을 안 실어도"
    assert client.get(f"/logic/api/jobs/{job}/overrides").json()["timers_flat"] == {"1": {"PD": 2.5}}
    client.post(f"/logic/api/jobs/{job}/overrides/timer", json={"page": 1, "block": "PD", "sec": None, "author": "홍길동"})
    r = client.post(f"/logic/api/jobs/{job}/sheet/1/simulate", json={"forces": {"row:3": 1}}).json()
    assert r["frames"][-1]["t"] == pytest.approx(5.0)


def test_delete_refuses_while_running_and_logs(client):
    job, d = _job(_bundle())
    st = store.read_status(d)
    st["state"] = "running"
    store.write_status(d, st)
    assert client.delete(f"/logic/api/jobs/{job}", params={"author": "홍길동"}).status_code == 409
    st["state"] = "done"
    store.write_status(d, st)
    assert client.delete(f"/logic/api/jobs/{job}").status_code == 400
    assert client.delete(f"/logic/api/jobs/{job}", params={"author": "홍길동"}).status_code == 204
    assert not d.exists()
    log = json.loads((store.root() / "deletion_log.json").read_text(encoding="utf-8"))
    assert log[-1]["job"] == job and log[-1]["author"] == "홍길동" and log[-1]["name"] == "toy.pdf"


def test_delete_project_removes_its_jobs_only(client):
    assert client.post("/logic/api/projects", json={"name": "PJT-A", "author": "홍길동"}).status_code == 200
    client.post("/logic/api/projects", json={"name": "PJT-B", "author": "홍길동"})
    mine, other = [], []
    for proj, bag in (("PJT-A", mine), ("PJT-A", mine), ("PJT-B", other)):
        job, d = _job(_bundle())
        st = store.read_status(d)
        st["project"] = proj
        store.write_status(d, st)
        bag.append(d)
    pv = client.get("/logic/api/projects/PJT-A/delete_preview").json()
    assert pv["jobs"] == 2 and pv["running"] == []
    url = "/logic/api/projects/PJT-A"
    assert client.delete(url, params={"confirm": "PJT-A"}).status_code == 400, "이름 없이는 안 지운다"
    assert client.delete(url, params={"author": "홍길동", "confirm": "PJT"}).status_code == 400, "이름을 그대로 적어야"
    st = store.read_status(mine[0])
    st["state"] = "running"
    store.write_status(mine[0], st)
    assert client.delete(url, params={"author": "홍길동", "confirm": "PJT-A"}).status_code == 409
    st["state"] = "done"
    store.write_status(mine[0], st)
    r = client.delete(url, params={"author": "홍길동", "confirm": "PJT-A"})
    assert r.status_code == 200 and r.json()["jobs"] == 2
    assert not any(d.exists() for d in mine) and other[0].exists(), "다른 프로젝트 분석은 남는다"
    names = [p["name"] for p in client.get("/logic/api/projects").json()["projects"]]
    assert "PJT-A" not in names and "PJT-B" in names
    log = json.loads((store.root() / "deletion_log.json").read_text(encoding="utf-8"))
    assert log[-1]["kind"] == "project" and log[-1]["project"] == "PJT-A" and log[-1]["author"] == "홍길동"
    assert client.delete(url, params={"author": "홍길동", "confirm": "PJT-A"}).status_code == 404


def test_library_merge_keeps_the_bundle_legend_first():
    leg = {"map": {"BAR_BOX|": {"name": "AND", "logic": "and", "page": 3, "label": ""}}, "names": {},
           "figures": [{"fig": [[1, 1]], "name": "INTEGRAL", "logic": "", "page": 3, "label": ""}]}
    lib = {"map": {"BAR_BOX|": {"name": "OR", "logic": "or", "page": None, "lib": "x"},
                   "|SRST": {"name": "MEMORY", "logic": "memory", "page": None, "lib": "x"}},
           "names": {"|PID": "PID"},
           "figures": [{"fig": [[2, 2]], "name": "INTEGRAL", "logic": "", "lib": "x"},
                       {"fig": [[3, 3]], "name": "SUMMING", "logic": "", "lib": "x"}]}
    m = library.merge(leg, lib)
    assert m["map"]["BAR_BOX|"]["logic"] == "and", "묶음 범례가 이긴다"
    assert m["map"]["|SRST"]["logic"] == "memory" and m["names"]["|PID"] == "PID", "범례가 말하지 않은 열쇠만 보탠다"
    assert [f["name"] for f in m["figures"]] == ["INTEGRAL", "SUMMING"]
    assert library.specific("|SRST") and not library.specific("BAR_BOX|") and not library.specific("|?")


def test_library_learns_legend_and_typicals_once(tmp_path):
    res = _bundle()
    res["legend"]["learn"] = {"map": {"ROUND_BOX|ON": {"name": "ON DELAY", "logic": "delay_on", "label": "ON", "page": 3}},
                              "names": {"|PID": "PID"}, "figures": [{"fig": [[1, 2]], "name": "INTEGRAL", "logic": "", "label": ""}]}
    # G001 의 X 를 매크로로 만들어 G002 를 Typical 로 잇는다
    res["sheets"][0]["blocks"]["X"].update({"func": "MACRO", "logic": "macro", "macro": {"page": 2, "sheet": "G002"}})
    d = tmp_path / "job"
    (d / "pages").mkdir(parents=True)
    (d / "pages" / f"p2_z{store.ZOOM}.png").write_bytes(b"\x89PNG fake")
    got = library.learn_from_result(res, d, "toy bundle", job="toyjob")
    assert got == {"symbols": 2, "figures": 1, "typicals": 1}
    assert library.learn_from_result(res, d, "toy bundle", job="toyjob") == {"symbols": 0, "figures": 0, "typicals": 0}
    lib = library.load()
    assert lib["symbols"]["ROUND_BOX|ON"]["logic"] == "delay_on"
    ty = next(iter(lib["typicals"].values()))
    assert ty["sheet_no"] == "G002" and ty["from"] == "toy bundle"
    assert all("fm" not in r for r in ty["sheet"]["rows"]), "다른 묶음을 가리키는 FM/TO 는 뺀다"
    leg = library.as_legend(lib)
    assert leg["map"]["ROUND_BOX|ON"]["logic"] == "delay_on" and leg["map"]["ROUND_BOX|ON"]["lib"]


def test_library_typical_is_used_when_the_bundle_has_none():
    """매크로의 Typical 시트가 묶음에 없으면 사전의 Typical 을 단자 이름으로 맞대고, 그 안대로 돈다."""
    from app.logic import macro

    import pymupdf
    doc = pymupdf.open()
    doc.new_page()
    # 사전의 Typical: 입력 1 'AUTO OPEN' (A_OPN) → OR → 출력 20 'OPEN COMMAND' (C_OPN)
    typ = _sheet(7, "T07", [{"n": 1, "side": "L", "net": "a", "desc": "AUTO OPEN", "abv": "A_OPN"},
                            {"n": 20, "side": "R", "net": "c", "desc": "OPEN COMMAND", "abv": "C_OPN"}],
                 {"G": _blk("OR", "or")}, [_P("G", "a", "in"), _P("G", "c", "out")])
    lib = {"typicals": {"t1": {"sheet_no": "T07", "title": "SOV BLOCK", "caption": "", "from": "other", "png": None,
                               "sheet": library._typical_copy(typ)}}}
    s = _sheet(1, "A001", [{"n": 1, "side": "L", "net": "1", "desc": "X"}, {"n": 30, "side": "R", "net": "9", "desc": "Y"}],
               {"M": {**_blk("MACRO", "macro", (200, 100, 300, 200)), "read": "A_OPN C_OPN"}},
               [{**_P("M", "1", "in", at=(200, 120)), "pin": "A_OPN"}, {**_P("M", "9", "out", at=(300, 120)), "pin": "C_OPN"}])
    lib_sheets = macro.link(doc, [s], library=lib)
    m = s["blocks"]["M"]["macro"]
    assert m["library"]["id"] == "t1" and m["page"] == library.LIB_PAGE0 + 1 and len(lib_sheets) == 1
    assert lib_sheets[0]["sheet_no"] == "LIB T07"
    out = sim.simulate_bundle([s] + lib_sheets, {1: {"row:1": 1}}, None, 1)
    assert out["focus"]["frames"][-1]["values"]["9"] == 1, "사전 Typical 의 OR 로 상자 출력이 선다"


def test_project_without_its_own_legend_reads_gates_from_the_library(tmp_path, monkeypatch):
    """다른 프로젝트 — 범례 표가 없는 묶음도 학습 사전(씨앗: 19VA SIGNAL PROCESSING SYMBOLS)의 모양 열쇠로 게이트를 읽는다.
    사전이 비면 예전처럼 판정하지 못한다 (모양만으로 지어내지 않는다)."""
    import pymupdf
    from tests.test_logic_l21_form import _logic
    from app.logic import analyse
    doc = pymupdf.open()
    _logic(doc)                                    # 범례 장 없이 Logic 시트 한 장
    p = tmp_path / "nolegend.pdf"
    doc.save(p)
    s = analyse.analyse(str(p))["sheets"][0]
    got = sorted((b["func"], b["logic"], bool(b.get("learned"))) for b in s["blocks"].values())
    assert got == [("AND", "and", True), ("GT", "delay_on", True), ("NOT", "not", True), ("OR", "or", True)], got
    # analyse 가 쥔 사전 모듈을 바꾼다 (다른 시험이 app.* 를 다시 읽으면 이 파일의 library 와 다를 수 있다)
    monkeypatch.setattr(analyse.library, "load", lambda: {"symbols": {}, "figures": [], "typicals": {}, "learned_jobs": [], "conflicts": []})
    s = analyse.analyse(str(p))["sheets"][0]
    assert not any(b["logic"] in ("and", "or") for b in s["blocks"].values()), "사전이 없으면 모양만으로 게이트를 정하지 않는다"
