"""L31 — 시트 사이 이동을 가볍게.

  * 시뮬레이션 중 시트만 옮기면 묶음을 다시 돌리지 않는다 — 같은 입력이면 묶음의 답은 같고 화면이 보는 장의 결과만 꺼낸다.
    꺼낸 답이 처음부터 돌린 답과 **글자까지 같은지** 못박는다.
  * 그림이 아직 없는 시트는 따로 된 프로세스가 미리 그린다 (서버가 그 자리에서 그리지 않게).
  * 화면 — 받은 시트는 기억 · 앞뒤 시트를 미리 받음 · 그림은 풀린 뒤 바꿈 · 사람 값을 고치면 기억을 비움.
"""
from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import api, sim, store
from tests.test_logic_l28_light import _random_bundle, _toy_result

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear(); api._PAGES_WARM.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear(); api._PAGES_WARM.clear()


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


def _bundle_result(rnd):
    sheets = _random_bundle(rnd)
    return {"pdf_pages": len(sheets), "sheets": sheets, "kinds": {}, "dictionary": {}, "note": "", "seconds": 1}


def _fresh(res, forces, state, focus):
    out = sim.simulate_bundle(res["sheets"], {int(k): v for k, v in forces.items()},
                              {int(k): v for k, v in state.items()}, focus, timers={}, analog={}, cache=None)
    out["default_t"] = sim.DEFAULT_T
    out.pop("macro_inner", None)          # L44 — 매크로 새 창 몫은 열린 창이 물을 때만 싣는다
    return json.loads(json.dumps(out))


def test_switching_sheets_with_the_same_inputs_gives_the_same_answer_as_a_full_run(monkeypatch):
    rnd = random.Random(31)
    for trial in range(6):
        res = _bundle_result(rnd)
        job, _ = _job(res)
        c = _client()
        pages = [s["page"] for s in res["sheets"]]
        state, forces = {}, {}
        for step in range(5):
            s = rnd.choice(res["sheets"][:-1])
            forces.setdefault(str(s["page"]), {})[f"row:{rnd.randint(1, 4)}"] = rnd.choice((0, 1))
            for focus in rnd.sample(pages, len(pages)):          # 같은 입력으로 시트만 옮긴다
                req = {"forces": forces, "state": state, "page": focus, "timers": {}, "analog": {}}
                got = c.post(f"/logic/api/jobs/{job}/simulate", json=req).json()
                assert got == _fresh(store.read_result(store.root() / job), forces, state, focus), (trial, step, focus)
            state = got["state"]
        api._BUNDLE.clear(); store._RES.clear()


def test_switching_sheets_does_not_run_the_bundle_again(monkeypatch):
    res = _bundle_result(random.Random(7))
    job, _ = _job(res)
    c = _client()
    calls = []
    real = sim.simulate_bundle
    monkeypatch.setattr(sim, "simulate_bundle", lambda *a, **k: (calls.append(1), real(*a, **k))[1])
    req = {"forces": {"1": {"row:1": 1}}, "state": {}, "timers": {}, "analog": {}}
    for p in (1, 2, 3, 1, 4):
        c.post(f"/logic/api/jobs/{job}/simulate", json={**req, "page": p})
    assert len(calls) == 1, "시트만 옮겼는데 묶음을 다시 돌렸다"
    c.post(f"/logic/api/jobs/{job}/simulate", json={**req, "forces": {"1": {"row:1": 0}}, "page": 2})
    assert len(calls) == 2, "준 신호가 바뀌면 다시 센다"


def test_reused_answer_is_a_new_object_each_time():
    res = _bundle_result(random.Random(9))
    job, _ = _job(res)
    c = _client()
    req = {"forces": {"1": {"row:1": 1}}, "page": 1}
    a = c.post(f"/logic/api/jobs/{job}/simulate", json=req).json()
    cache = api._BUNDLE[job][1]
    body_json, results, _inner = next(iter(cache["_last"].values()))
    before = json.dumps(results, sort_keys=True, default=str)
    a["focus"]["frames"].clear()
    b = c.post(f"/logic/api/jobs/{job}/simulate", json=req).json()
    assert b["focus"]["frames"] and json.dumps(results, sort_keys=True, default=str) == before


def test_a_person_change_drops_the_remembered_bundle():
    res = _toy_result()
    job, _ = _job(res)
    c = _client()
    req = {"forces": {"1": {"row:1": 1, "row:2": 1}}, "page": 1}
    c.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "U", "choice": "AND", "author": "x"})
    assert c.post(f"/logic/api/jobs/{job}/simulate", json=req).json()["focus"]["frames"][-1]["values"].get("u") == 1
    c.post(f"/logic/api/jobs/{job}/overrides/block", json={"page": 1, "block": "U", "choice": "NOR", "author": "x"})
    assert c.post(f"/logic/api/jobs/{job}/simulate", json=req).json()["focus"]["frames"][-1]["values"].get("u") == 0


def test_missing_page_images_are_drawn_by_a_separate_process(monkeypatch):
    res = _toy_result()
    pdf = pymupdf.open()
    for _ in res["sheets"]:
        pdf.new_page(width=300, height=200)
    job, d = _job(res, pdf)
    monkeypatch.setenv("PID_LOGIC_WARM", "1")
    monkeypatch.setattr(api, "_warm_bundle", lambda *a: None)
    launched = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **k: launched.append(args))
    c = _client()
    c.get(f"/logic/api/jobs/{job}/sheets")
    c.get(f"/logic/api/jobs/{job}/sheets")
    assert len(launched) == 1 and launched[0][-2:] == ["--pages", str(d)], launched
    # 그 프로세스가 하는 일 — 없는 그림만 그린다
    from app.logic import run
    run.prerender_missing(d)
    for s in res["sheets"]:
        assert (d / "pages" / f"p{s['page']}_z{store.ZOOM}.png").is_file()
    # 다 있으면 띄우지 않는다
    api._PAGES_WARM.clear(); launched.clear()
    c.get(f"/logic/api/jobs/{job}/sheets")
    assert launched == []


def test_no_prerender_when_warming_is_off(monkeypatch):
    res = _toy_result()
    job, _ = _job(res)
    launched = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **k: launched.append(args))
    _client().get(f"/logic/api/jobs/{job}/sheets")
    assert launched == []


def _fn(name):
    i = JS.index(f"function {name}(")
    j = JS.find("\nfunction ", i + 10)
    k = JS.find("\nasync function ", i + 10)
    ends = [x for x in (j, k) if x > 0]
    return JS[i:min(ends)] if ends else JS[i:]


def test_screen_keeps_sheets_prefetches_neighbours_and_swaps_the_image_after_decoding():
    o = _fn("openSheet")
    assert "getSheet(page)" in o and "preloadImg(page)" in o and "prefetchAround(page)" in o
    assert "im.ready" in o and 'visibility = "hidden"' in o, "그림은 풀린 뒤에 바꾼다"
    assert "if (L.page !== page) return" in o, "받는 동안 다른 시트로 옮기면 그 결과를 그리지 않는다"
    assert "runSim(false, true)" in o
    assert "sheetCacheClear()" in _fn("refreshSheet")
    assert "decode()" in _fn("preloadImg") and "IMG_KEEP" in _fn("preloadImg")
    assert "requestIdleCallback" in _fn("prefetchAround")


def test_sim_page_switch_resends_the_last_request_state():
    r = _fn("runSim")
    assert "pageOnly" in r and "last.state" in r and "last.inputs === inputs" in r
