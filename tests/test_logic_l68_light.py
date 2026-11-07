"""L68 — LOGIC 을 다시 가볍게 (사용자: *"로직이 여전히 무겁다 가볍게 해줘"*).  답은 그대로다.

  * 준비한 결과 사본(prepared.bin · marshal) — 다시 열 때 37MB JSON 을 풀고 설정값 · 연산자 이름 · from-to 를
    다시 얹지 않는다.  JSON 길과 **같은 결과**이고, result.json 이 바뀌면 · 코드가 바뀌면 · 깨졌으면 쓰지 않는다.
  * 동작 예시(/scenario) 는 묶음 기억을 넘긴다 — 없이 돌린 것과 같은 답.
  * 작도 화면은 바뀐 선 · 기호만 새로 짓는다 · 검토 화면은 곁 정보를 첫 시트 뒤에 받는다 (소스 검사).
"""
from __future__ import annotations

import gc
import json
import re
from pathlib import Path

import pytest

from app.logic import api, overrides, sim, store
from tests.test_logic_l28_light import _canon, _client, _every_override, _job, _toy_result

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear(); api._SIZES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear(); api._SIZES.clear()


def _wait_prepared(d):
    import time
    for _ in range(100):
        if (d / api.PREPARED).exists():
            return
        time.sleep(0.02)
    raise AssertionError("준비한 사본이 생기지 않았다")


def _fresh(d):
    store._RES.clear(); api._APPLIED.clear(); api._SP.clear(); api._SIZES.clear()


def test_prepared_copy_gives_the_same_result_as_reading_the_json():
    res = _toy_result()
    job, d = _job(res)
    a = api._result(job)
    snap_a = _canon({k: v for k, v in a.items() if k != "_memo"})
    _wait_prepared(d)
    _fresh(d)
    b = api._result(job)                               # 이번에는 준비한 사본에서
    assert _canon({k: v for k, v in b.items() if k != "_memo"}) == snap_a
    assert b.get("_ft") and b.get("_aop") and b.get("_sp")
    assert gc.isenabled()                              # 읽는 동안 끈 수거기는 다시 켜져 있다


def test_prepared_copy_is_not_used_when_the_result_or_the_code_changes(monkeypatch):
    res = _toy_result()
    job, d = _job(res)
    api._result(job); _wait_prepared(d)
    seen = []
    real = json.loads
    monkeypatch.setattr(store.json, "loads", lambda t, *a, **k: (seen.append(1), real(t, *a, **k))[1])
    _fresh(d); api._result(job)
    assert not seen, "사본이 맞는데 JSON 을 다시 읽었다"
    res2 = json.loads(json.dumps(res)); res2["sheets"][0]["title"] = "BUMPED"
    store.write_result(d, res2)                        # 다시 분석하면 그 결과를 읽는다
    _fresh(d)
    assert api._result(job)["sheets"][0]["title"] == "BUMPED"
    assert seen
    _wait_prepared(d)
    seen.clear()
    monkeypatch.setattr(api, "_code_fp_cached", lambda: "other-code")   # 업데이트로 코드가 바뀌면 다시 준비한다
    _fresh(d); api._result(job)
    assert seen
    import time
    for _ in range(200):                               # 새 열쇠로 다시 쓴 사본을 기다린 뒤 (뒤에서 쓴다)
        if b"other-code" in (d / api.PREPARED).read_bytes()[:200]:
            break
        time.sleep(0.02)
    (d / api.PREPARED).write_bytes(b"garbage\n\x00\x01")                # 깨진 사본은 그냥 버린다
    _fresh(d); seen.clear()
    assert api._result(job)["sheets"][0]["title"] == "BUMPED" and seen


def test_prepared_copy_with_human_values_is_the_same_as_before():
    res = _toy_result()
    job, d = _job(res)
    overrides._save(d, _every_override(res))
    a = _canon({k: v for k, v in api._result(job).items() if k != "_memo"})
    _wait_prepared(d)
    _fresh(d)
    b = _canon({k: v for k, v in api._result(job).items() if k != "_memo"})
    assert a == b


def test_scenario_endpoint_answers_like_the_uncached_search():
    res = _toy_result()
    job, d = _job(res)
    r = api._result(job)
    sheets = api._all_sheets(r)
    n = 0
    for s in r["sheets"]:
        for row in s["rows"]:
            if row["side"] != "R" or row.get("net") is None:
                continue
            a = sim.scenario(s, f"row:{row['n']}", 1, sheets=sheets)
            b = api.scenario(job, s["page"], {"target": f"row:{row['n']}"})
            assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
            n += 1
    assert n


def test_screen_sources_keep_the_light_paths():
    js = (ROOT / "app/static/logic_draw.js").read_text(encoding="utf-8")
    body = js[js.index("function render() {"):js.index("function hopIndex()")]
    assert "wireNode(w)" in body and "blockNode(b," in body and "renderWire(wg" not in body
    assert "simOn()" in js[js.index("function wireKey"):js.index("function wireNode")]
    lj = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
    oj = lj[lj.index("async function openJob"):lj.index("async function goLoc")]
    assert re.search(r"openSheet\(p\)\.finally\(side\)", oj)
    assert oj.index("const side = () =>") < oj.index("loadReview(id);")
