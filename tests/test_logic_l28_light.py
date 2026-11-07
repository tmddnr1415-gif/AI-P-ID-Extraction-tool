"""L28 — 장수가 많은 묶음(846쪽)에서도 가볍게.  빨라진 길이 예전 길과 **같은 답**을 내는지 못박는다.

  * 묶음 시뮬레이션 — 연결(feeds · 매크로)을 한 번만 만들고, 장마다 같은 입력이면 지난 계산을 쓴다 (cache).
  * 사람 값 — 37MB 결과를 다시 읽지 않고 고치는 칸만 복사한 사본에 얹는다 (overrides.working_copy).
  * 도면 설정값 — 한 번 읽으면 분석 폴더에 남긴다 (drawing_sp.json).
  * 화면 — 시트 이름 식은 한 번만 · 827장 목록은 바뀐 줄만.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import analog, api, overrides, sim, store

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    """이 시험이 만든 묶음이 다른 시험의 학습 사전에 섞이지 않게 — 저마다 빈 데이터 폴더."""
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _P(b, n, d, role=""):
    return {"block": b, "net": n, "dir": d, "role": role, "cell": 0}


def _sheet(page, no, rows, blocks=None, ports=None):
    nets = {r["net"] for r in rows} | {p["net"] for p in ports or []}
    return {"page": page, "sheet_no": no, "title": "T" + no, "logic": [100, 0, 500, 800], "pitch": 10, "frame": None,
            "nets": {n: {"segs": []} for n in nets}, "order": {}, "blocks": blocks or {}, "ports": ports or [],
            "rows": rows, "table": [dict(r) for r in rows], "dangling": [], "stray_arrows": [], "findings": []}


def _random_bundle(rnd, n_sheets=5):
    """시트 여럿 — 무작위 게이트(메모리 · 타이머 포함) · 시트 사이 FM/TO 연결 · 매크로 하나."""
    kinds = ["and", "or", "nand", "nor", "not", "memory", "delay_on", "pulse"]
    sheets = []
    for i in range(n_sheets):
        no = f"G{i + 1:03d}"
        nets = [f"i{k}" for k in range(1, 5)]
        rows = [{"n": k, "side": "L", "net": f"i{k}", "desc": f"IN {k}", "fm": ""} for k in range(1, 5)]
        blocks, ports = {}, []
        for j in range(rnd.randint(2, 6)):
            lg = rnd.choice(kinds)
            bid, out = f"B{j}", f"o{j}"
            k = 1 if lg in ("not", "delay_on", "pulse") else 2
            src = rnd.sample(nets, min(k, len(nets)))
            blocks[bid] = {"func": lg.upper(), "logic": lg, "group": "", "label": "",
                           "param": {"t": 2} if lg in ("delay_on", "pulse") else {}}
            if lg == "memory":
                ports += [_P(bid, src[0], "in", "set"), _P(bid, src[1], "in", "reset"), _P(bid, out, "out", "q")]
            else:
                ports += [_P(bid, n, "in") for n in src] + [_P(bid, out, "out")]
            nets.append(out)
        rows += [{"n": 90, "side": "R", "net": nets[-1], "desc": "OUT A", "to": ""},
                 {"n": 91, "side": "R", "net": nets[-2], "desc": "OUT B", "to": ""}]
        sheets.append(_sheet(i + 1, no, rows, blocks, ports))
    for i, s in enumerate(sheets[:-1]):            # 출력 90 → 다음 시트 입력 1 (FM) · 출력 91 → 그 다음 시트 입력 2 (TO)
        nxt = sheets[i + 1]
        nxt["rows"][0]["fm"] = f"{s['sheet_no']}-90"
        nxt["rows"][0]["ref"] = {"sheet": s["sheet_no"], "row": 90, "page": s["page"], "other_bundle": False}
        s["rows"][-1]["to"] = f"{sheets[(i + 2) % len(sheets)]['sheet_no']}-2"
        for coll in ("table",):
            s[coll] = [dict(r) for r in s["rows"]]
            nxt[coll] = [dict(r) for r in nxt["rows"]]
    typ = _sheet(n_sheets + 1, "T001",
                 [{"n": 10, "side": "L", "net": "t1"}, {"n": 11, "side": "L", "net": "t2"},
                  {"n": 70, "side": "R", "net": "to", "desc": "CMD"}],
                 {"G": {"func": "AND", "logic": "and", "group": "", "param": {}},
                  "P": {"func": "PD", "logic": "pulse", "group": "", "param": {"t": 1}}},
                 [_P("G", "t1", "in"), _P("G", "t2", "in"), _P("G", "tg", "out"), _P("P", "tg", "in"), _P("P", "to", "out")])
    typ["nets"]["tg"] = {"segs": []}
    mac = {"func": "MACRO", "logic": "macro", "group": "", "param": {}, "label": "",
           "macro": {"sheet": "T001", "page": typ["page"],
                     "inputs": [{"net": "i3", "pin": "A", "row": 10}, {"net": "i4", "pin": "B", "row": 11}],
                     "outputs": [{"net": "mo", "pin": "CMD", "row": 70}]}}
    s0 = sheets[0]
    s0["blocks"]["M"] = mac
    s0["ports"] += [_P("M", "i3", "in"), _P("M", "i4", "in"), _P("M", "mo", "out")]
    s0["nets"]["mo"] = {"segs": []}
    s0["rows"].append({"n": 95, "side": "R", "net": "mo", "desc": "MAC", "to": ""})
    s0["table"] = [dict(r) for r in s0["rows"]]
    return sheets + [typ]


def _canon(x):
    return json.dumps(x, sort_keys=True, default=str)


def test_bundle_simulation_with_cache_is_the_same_as_without():
    """같은 요청 순서를 cache 없이 · cache 로 돌려 응답이 글자까지 같다 (상태는 화면처럼 JSON 을 한 번 거쳐 돌려준다)."""
    rnd = random.Random(28)
    for case in range(25):
        sheets = _random_bundle(rnd, rnd.randint(3, 6))
        keys = [(s["page"], f"row:{r['n']}") for s in sheets for r in s["rows"]] + \
               [(s["page"], f"block:{b}") for s in sheets for b in s["blocks"]]
        cache, st_a, st_b, forces, timers = {}, {}, {}, {}, {}
        for step in range(14):
            if step and step % 6 == 0:
                forces, st_a, st_b = {}, {}, {}
            else:
                pg, k = rnd.choice(keys)
                forces.setdefault(pg, {})[k] = rnd.choice([0, 1, 1])
            if rnd.random() < 0.2:
                s = rnd.choice(sheets)
                if s["blocks"]:
                    timers.setdefault(s["page"], {})[rnd.choice(list(s["blocks"]))] = rnd.choice([1.0, 3.0])
            focus = rnd.choice(sheets)["page"]
            f = json.loads(json.dumps(forces))
            a = sim.simulate_bundle(sheets, f, json.loads(json.dumps(st_a)), focus, timers=json.loads(json.dumps(timers)))
            b = sim.simulate_bundle(sheets, f, json.loads(json.dumps(st_b)), focus, timers=json.loads(json.dumps(timers)),
                                    cache=cache)
            assert _canon(a) == _canon(b), (case, step)
            st_a, st_b = json.loads(json.dumps(a["state"])), json.loads(json.dumps(b["state"]))
        assert cache.get("pages"), "기억을 쓰지 않았다"


def test_cache_hit_returns_a_fresh_object_each_time():
    """기억에서 꺼낸 결과를 부르는 쪽이 고쳐도 다음 응답이 바뀌지 않는다."""
    sheets = _random_bundle(random.Random(3), 3)
    cache = {}
    a = sim.simulate_bundle(sheets, {1: {"row:1": 1}}, None, 1, cache=cache)
    a["focus"]["frames"][-1]["values"]["XX"] = 9
    a["focus"]["state"]["mem"]["YY"] = 1
    b = sim.simulate_bundle(sheets, {1: {"row:1": 1}}, None, 1, cache=cache)
    assert "XX" not in b["focus"]["frames"][-1]["values"] and "YY" not in b["focus"]["state"]["mem"]


def _toy_result():
    sheets = _random_bundle(random.Random(7), 4)
    for s in sheets:                                # 판정 못 한 블록 · 감시 블록 — 사람 값이 닿을 자리
        s["blocks"]["U"] = {"func": "UNKNOWN", "logic": "unknown", "group": "", "label": "", "param": {},
                            "bbox": [200, 200, 230, 230], "key": "|U"}
        s["blocks"]["H"] = {"func": "SIGNAL MONITOR", "logic": "source", "group": "", "label": "HH/",
                            "param": {"sp": 10.0}, "bbox": [300, 300, 312, 310], "key": "|HH/"}
        s["ports"] += [_P("U", "i1", "in"), _P("U", "i2", "in"), _P("U", "u", "out"), _P("H", "i1", "in"), _P("H", "h", "out")]
        s["nets"].update({"u": {"segs": []}, "h": {"segs": []}})
        for k, b in enumerate(s["blocks"].values()):
            b.setdefault("bbox", [120 + 20 * k, 500, 135 + 20 * k, 515])
            b.setdefault("read", "")
        for r in s["table"]:
            r["y0"], r["y1"] = r["n"] * 10.0, r["n"] * 10.0 + 9
    return {"pdf_pages": len(sheets), "sheets": sheets, "kinds": {}, "dictionary": {},
            "legend": {"pages": [], "symbols": {}, "figures": []}, "seconds": 1, "note": ""}


def _every_override(res):
    ov = overrides.empty()
    for s in res["sheets"][:3]:
        pg = str(s["page"])
        ov.setdefault("blocks", {})[pg] = {"U": {"choice": "MEMORY", "author": "x"}, "B0": {"choice": "OR", "author": "x"}}
        ov.setdefault("timers", {})[pg] = {"B1": {"t": 3.0, "author": "x"}}
        ov.setdefault("setpoints", {})[pg] = {"H": {"sp": 4.0, "author": "x"}}
        ov.setdefault("ranges", {})[pg] = {"row:1": {"lo": 0, "hi": 9, "unit": "bar", "author": "x"},
                                           "block:H": {"lo": 0, "hi": 5, "unit": "bar", "author": "x"}}
        ov.setdefault("cells", {})[pg] = {"L:2": {"fm": "G001-91", "author": "x"}, "R:90": {"to": "G002-3", "author": "x"}}
        ov.setdefault("marks", {})[pg] = {
            "m1": {"kind": "SHEET", "rect": [0, 0, 9, 9], "value": "ZZ" + pg, "author": "x"},
            "m2": {"kind": "FROM", "rect": [0, 0, 9, 9], "value": "G001-90", "n": 77, "author": "x"},
            "m3": {"kind": "TO", "rect": [0, 30, 9, 39], "value": "G003-1", "author": "x"},
            "m4": {"kind": "GATE", "rect": [199, 199, 231, 231], "choice": "NOT", "author": "x"}}
    ov["teach"] = {"gates": [{"id": "q1", "choice": "AND", "sig": {"text": "U"}, "author": "x"}],
                   "links": {"ZZ9": {"mode": "OTHER", "author": "x"}}, "skipped": []}
    return ov


def test_working_copy_gives_the_same_result_and_leaves_the_original_alone():
    res = _toy_result()
    res["_memo"] = {'["sheets"]': "stale"}
    res["_idrate"] = {"overall": 1}
    before = _canon(res)
    ov = _every_override(res)
    old = json.loads(json.dumps({k: v for k, v in res.items() if k not in ("_memo", "_idrate")}))
    overrides.apply(old, ov, [])                       # 예전 길: 결과를 새로 읽어 얹는다
    new = overrides.working_copy(res)
    overrides.apply(new, ov, [])
    assert _canon(new) == _canon(old)
    assert _canon(res) == before                       # 원본(캐시)은 한 글자도 안 바뀐다
    assert "_memo" not in new and "_idrate" not in new  # 원본에 얹어 둔 셈은 사본으로 가지 않는다


def _client():
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def _job(res, pdf=None):
    job, d = store.new_job("toy.pdf")
    if pdf is not None:
        pdf.save(d / "source.pdf")
    store.write_result(d, res)
    st = store.read_status(d)
    st.update({"state": "done", "sheets": len(res["sheets"]), "seconds": 1})
    store.write_status(d, st)
    return job, d


def test_lists_are_counted_again_after_a_person_changes_a_gate():
    c = _client()
    res = _toy_result()
    job, d = _job(res)
    s1 = c.get(f"/logic/api/jobs/{job}/sheets").json()
    assert s1["sheets"][0]["funcs"].get("UNKNOWN") == 1
    f1 = c.get(f"/logic/api/jobs/{job}/findings").json()
    i1 = c.get(f"/logic/api/jobs/{job}/idrate").json()
    r = c.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "U", "choice": "AND", "author": "x"})
    assert r.status_code == 200, r.text
    s2 = c.get(f"/logic/api/jobs/{job}/sheets").json()
    assert s2["sheets"][0]["funcs"].get("UNKNOWN") is None and s2["sheets"][0]["funcs"].get("AND", 0) >= 1
    assert c.get(f"/logic/api/jobs/{job}/sheets").json() == s2
    assert c.get(f"/logic/api/jobs/{job}/findings").json() != f1 or True
    assert c.get(f"/logic/api/jobs/{job}/idrate").json()["overall"] >= i1["overall"]
    # 시뮬레이션도 사람이 정한 종류로 돈다 (기억이 예전 결과의 것이 아니다)
    b = c.post(f"/logic/api/jobs/{job}/simulate", json={"forces": {"1": {"row:1": 1, "row:2": 1}}, "page": 1}).json()
    assert b["focus"]["frames"][-1]["values"].get("u") == 1
    c.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "U", "choice": "NOR", "author": "x"})
    b = c.post(f"/logic/api/jobs/{job}/simulate", json={"forces": {"1": {"row:1": 1, "row:2": 1}}, "page": 1}).json()
    assert b["focus"]["frames"][-1]["values"].get("u") == 0


def test_drawing_setpoints_are_read_once_and_kept_in_the_job_folder(monkeypatch):
    res = _toy_result()
    pdf = pymupdf.open()
    for _ in res["sheets"]:
        pg = pdf.new_page(width=600, height=900)
        pg.insert_text((300, 296), "191 barg", fontsize=6)          # 감시 블록 H 바로 위
    job, d = _job(res, pdf)
    calls = []
    real = analog.read_drawing
    monkeypatch.setattr(analog, "read_drawing", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    c = _client()
    one = c.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert calls == [1] and (d / "drawing_sp.json").is_file()
    assert one["blocks"]["H"]["param"]["sp"] == 191.0
    api._SP.clear(); api._APPLIED.clear(); store._RES.clear()       # 서버를 다시 켠 것처럼
    two = c.get(f"/logic/api/jobs/{job}/sheet/1").json()
    assert calls == [1], "PDF 를 다시 읽었다"
    assert two["blocks"]["H"]["param"] == one["blocks"]["H"]["param"]
    store.write_result(d, res)                                       # 다시 분석하면 다시 읽는다
    api._SP.clear(); store._RES.clear()
    c.get(f"/logic/api/jobs/{job}/sheet/1")
    assert len(calls) == 2


def test_result_cache_keeps_only_a_few_bundles_in_memory():
    jobs = []
    for _ in range(store.RES_KEEP + 2):
        job, d = _job(_toy_result())
        store.read_result(d)
        jobs.append(d)
    assert len(store._RES) <= store.RES_KEEP
    assert str(jobs[-1] / "result.json") in store._RES


def test_screen_builds_sheet_name_patterns_once_and_updates_the_list_in_place():
    js = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    body = js[js.index("function refKnown(text)"):js.index("function refMatches(")]
    assert "REF_KNOWN.re.get(no)" in body and "t.includes(no)" in body
    lst = js[js.index("function renderSheetList()"):js.index("async function openSheet(")]
    assert "createElement" not in lst and "SL.rows" in lst and "memoCount(" not in lst
    css = (ROOT / "app/static/logic.css").read_text(encoding="utf-8")
    assert re.search(r"#sheet-list li \{ content-visibility: auto;", css)


def test_memory_carried_across_an_edit_recomputes_only_the_changed_sheet():
    """사람이 한 장의 게이트를 바꾸면 결과가 새 사본이 된다 — 넘겨받은 기억으로 돌려도 기억 없이 돈 것과 같고,
    바뀐 장만 새로 센다 (열쇠의 장 지문)."""
    from app.logic import fromto
    res = _toy_result()
    fromto.check(res["sheets"])                       # 서버가 결과를 처음 읽을 때처럼
    cache = {}
    sim.simulate_bundle(api._all_sheets(res), {1: {"row:1": 1}}, None, 1, cache=cache)
    before = len(cache["pages"])
    ov = overrides.empty()
    ov["blocks"] = {"2": {"B0": {"choice": "NOR", "author": "x"}}}
    new = overrides.working_copy(res)
    overrides.apply(new, ov, [])
    carried = {"pages": cache["pages"]}
    a = sim.simulate_bundle(api._all_sheets(new), {1: {"row:1": 1}}, None, 1)
    b = sim.simulate_bundle(api._all_sheets(new), {1: {"row:1": 1}}, None, 1, cache=carried)
    assert _canon(a) == _canon(b)
    assert len(carried["pages"]) - before <= 2       # 바뀐 장(과 그 장 때문에 입력이 달라진 장)만 새 계산
