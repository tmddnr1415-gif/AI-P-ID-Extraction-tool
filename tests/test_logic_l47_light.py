"""L47 — LOGIC 을 가볍게: 학습 · 그룹 시험 · 순차 동작이 부르는 묶음 시뮬레이션의 군더더기를 뺐다.  답은 그대로다.

  * light 호출 — 설계 오류 · 현황 글 · 매크로 보기를 만들지 않고, 상태는 풀지 않은 채(_LazyState) 돌려준다.
    그 상태를 그대로 다시 넘겨도 보통 dict 로 넘긴 것과 **같은 값**이다.
  * 아무 입력도 안 받은 장은 기억 열쇠를 다시 만들지 않는다 (quiet) — 같은 입력이면 같은 답.
  * 설계 오류 찾기는 신호가 닿은 장만 본다 (예전엔 매번 모든 장을 훑고 모든 장의 결과를 풀었다) — 같은 목록.
  * 배우는 동안 결과 · 사람 값이 바뀌면 멈춘다(Stale) · 사람 값이 조용해진 뒤에 배운다(wait_quiet).
"""
from __future__ import annotations

import json
import random

import pytest

from app.logic import api, behavior, sim, store
from tests.test_logic_l28_light import _canon, _random_bundle


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _strip_light(a):
    """light 가 만들지 않는 칸을 뺀 나머지 — 두 호출을 맞댈 때."""
    return {k: v for k, v in a.items() if k not in ("design_errors", "pages", "macros", "macro_inner")}


def test_light_call_matches_the_full_call_and_its_lazy_state_round_trips():
    rnd = random.Random(47)
    for case in range(20):
        sheets = _random_bundle(rnd, rnd.randint(3, 6))
        keys = [(s["page"], f"row:{r['n']}") for s in sheets for r in s["rows"]] + \
               [(s["page"], f"block:{b}") for s in sheets for b in s["blocks"]]
        cache_a, cache_b, forces = {}, {}, {}
        st_a, st_b = {}, None
        for step in range(10):
            pg, k = rnd.choice(keys)
            forces.setdefault(pg, {})[k] = rnd.choice([0, 1, 1])
            focus = rnd.choice(sheets)["page"]
            f = json.loads(json.dumps(forces))
            a = sim.simulate_bundle(sheets, f, json.loads(json.dumps(st_a)), focus, cache=cache_a)
            b = sim.simulate_bundle(sheets, f, st_b, focus, cache=cache_b, light=True)
            assert isinstance(b["state"], sim._LazyState)
            assert _canon(_strip_light(a)) == _canon(_strip_light(b)), (case, step)
            assert b["design_errors"] == [] and b["pages"] == []
            st_a = json.loads(json.dumps(a["state"]))
            st_b = b["state"]                          # 풀지 않은 채 그대로 다음 호출로
            assert json.loads(json.dumps(st_b.items() and dict(st_b.items()))) == st_a


def test_quiet_sheets_reuse_their_memo_key_and_still_answer_the_same():
    sheets = _random_bundle(random.Random(5), 6)
    cache = {}
    sim.simulate_bundle(sheets, {}, None, 1, cache=cache, light=True)
    ak = next(iter(cache["quiet"]))
    assert len(cache["quiet"][ak]) == len(sheets)      # 모든 장이 조용한 열쇠를 가졌다
    before = dict(cache["quiet"][ak])
    a = sim.simulate_bundle(sheets, {2: {"row:1": 1}}, None, 2, cache=cache)
    b = sim.simulate_bundle(sheets, {2: {"row:1": 1}}, None, 2)
    assert _canon(a) == _canon(b)
    # 신호가 닿지 않은 장의 열쇠는 그대로 · 닿은 장(들어오는 값이 달라진 장)만 바뀔 수 있다
    same = sum(1 for p, v in before.items() if cache["quiet"][ak].get(p) == v)
    assert same >= len(sheets) - 3


def test_design_errors_only_look_at_reached_sheets_but_find_the_same_list():
    """`only` 로 좁힌 설계 오류 = 전부 훑어 `page in only` 로 거른 것."""
    rnd = random.Random(9)
    for case in range(12):
        sheets = _random_bundle(rnd, rnd.randint(3, 6))
        cache = {}
        f = {rnd.choice(sheets)["page"]: {"row:1": 1, "row:2": 1}}
        out = sim.simulate_bundle(sheets, f, None, 1, cache=cache)
        by_page = {s["page"]: s for s in sheets}
        by_no = {s["sheet_no"]: s for s in sheets}
        results = cache["_last_results"]
        out_rows = {p: sim._row_values(by_page[p], results[p]["frames"][-1]["values"]) for p in results}
        hop = {e["page"] for e in out["design_errors"]} | set(f)
        full = [e for e in sim._design_errors(sheets, by_page, by_no, out_rows, results) if e["page"] in hop]
        narrow = sim._design_errors(sheets, by_page, by_no, out_rows, results, only=hop,
                                    ref_in=sim._ref_index(sheets, by_page))
        assert full == narrow, case


def test_learner_stops_when_the_result_changes_underneath(tmp_path, monkeypatch):
    from tests.test_logic_l32_sequence import _bundle, _job
    job = _job(_bundle())
    d = api._dir(job)
    n = [0]
    real = behavior.learn_one

    def bump(*a, **k):
        n[0] += 1
        if n[0] == 1:                                   # 첫 명령을 배우는 사이에 사람 값이 바뀐다
            (d / "overrides.json").write_text("{}", encoding="utf-8")
        return real(*a, **k)
    monkeypatch.setattr(behavior, "learn_one", bump)
    assert behavior.learn_dir(d, check_every=1) is None
    assert not (d / behavior.FILE).exists() and not (d / behavior.RUNNING).exists()
    monkeypatch.setattr(behavior, "learn_one", real)
    out = behavior.learn_dir(d)
    assert out and (d / behavior.FILE).exists() and out["key"] == behavior.key_of(d)


def test_wait_quiet_waits_for_edits_to_settle(tmp_path):
    import time
    from app.logic import overrides
    d = tmp_path / "j"
    d.mkdir()
    assert behavior.wait_quiet(d, quiet_s=1.0, max_s=5) < 0.5          # 사람 값 파일이 없다 — 바로
    overrides._path(d).write_text("{}", encoding="utf-8")               # 방금 고쳤다
    slept = []
    waited = behavior.wait_quiet(d, quiet_s=0.6, max_s=5, sleep=lambda s: (slept.append(s), time.sleep(s)))
    assert slept and 0.5 <= waited < 3
