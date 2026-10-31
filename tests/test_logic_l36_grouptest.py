"""L36 — 블록 그룹 원 버튼 시험: 배운 것(켜기 · 막기 · 유지 · 끄기 · 다른 길 · 반대 명령)을 지금 결과로 다시 돌린다."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.logic import api, behavior, grouptest, store
from tests.test_logic_l32_sequence import _B, _P, _client, _job, _sheet
from tests.test_logic_l35_understand import _latched, _pair

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
TJS = (ROOT / "app/static/logic_test.js").read_text(encoding="utf-8")
THTML = (ROOT / "app/static/logic_test.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _fan_bundle():
    """FAN A: 래치 START (PB START + 허가, STOP · TRIP 이 끔) · 끊긴 선 명령 하나 · 다른 길(OR 요청 두 가지)."""
    g = _latched()[0]
    g["rows"].append({"n": 95, "side": "R", "net": "cut", "desc": "FAN B START CMD", "to": "", "at": [10, 950]})
    g["rows"] += [{"n": 3, "side": "L", "net": "ra", "desc": "VALVE C AUTO REQ", "fm": "", "at": [10, 30]},
                  {"n": 4, "side": "L", "net": "rb", "desc": "VALVE C MAN REQ", "fm": "", "at": [10, 40]},
                  {"n": 96, "side": "R", "net": "vc", "desc": "VALVE C OPEN CMD", "to": "", "at": [10, 960]}]
    g["blocks"]["OR2"] = _B("or")
    g["ports"] += [_P("OR2", "ra", "in"), _P("OR2", "rb", "in"), _P("OR2", "vc", "out")]
    g["nets"].update({n: {"segs": []} for n in ("cut", "ra", "rb", "vc")})
    return [g]


def test_learning_goes_deeper_alternatives_and_effects():
    out = behavior.learn(_fan_bundle(), {})
    by = {(x["equip"], x["action"]): x for x in out["items"]}
    v = by[("VALVE C", "OPEN")]
    assert v["reached"] and len(v["alts"]) == 1                      # AUTO REQ 또는 MAN REQ — 둘째 길
    first = {k for f in v["forces"].values() for k in f}
    second = {k for f in v["alts"][0]["forces"].values() for k in f}
    assert first != second and first | second == {"row:3", "row:4"}
    fan = by[("FAN A", "START")]
    assert fan["latch"] is True and fan["pulse_s"] is None
    assert by[("FAN B", "START")]["reached"] is False


def test_effects_list_outputs_that_turn_on_together():
    # 허가 + PB → SET → Q(90행) 이고 Q 가 다른 출력(97행)도 같이 몬다
    g = _latched()[0]
    g["rows"].append({"n": 97, "side": "R", "net": "q", "desc": "FAN A RUNNING LAMP", "to": "G002-1", "at": [10, 970]})
    r = behavior.learn_one([g], 1, 90, 1, {})
    assert [e["row"] for e in r["effects"]] == [97]


def test_group_test_checks_each_learned_fact():
    sheets = _latched()
    learned = behavior.learn(sheets, {})
    res = grouptest.test_group(sheets, grouptest.items_of(learned, "FAN A"), {})
    kinds = {(c["kind"], c["status"]) for c in res["checks"]}
    assert ("on", "pass") in kinds and ("hold", "pass") in kinds
    assert ("block", "pass") in kinds and ("stop", "pass") in kinds
    assert res["status"] == "pass" and res["counts"]["fail"] == 0


def test_unreachable_command_is_not_a_failure_but_untestable():
    learned = behavior.learn(_fan_bundle(), {})
    res = grouptest.test_group(_fan_bundle(), grouptest.items_of(learned, "FAN B"), {})
    assert res["status"] == "gap" and res["checks"][0]["status"] == "gap"


def test_regression_is_caught_when_the_logic_changes_after_learning():
    sheets = _latched()
    learned = behavior.learn(sheets, {})
    broken = _latched()
    broken[0]["ports"] = [p for p in broken[0]["ports"] if not (p["block"] == "A" and p["net"] == "ps")]
    broken[0]["ports"].append(_P("A", "trip", "in"))                 # 누가 AND 입력을 다른 선에 이었다
    res = grouptest.test_group(broken, grouptest.items_of(learned, "FAN A"), {})
    assert res["status"] == "fail"
    assert any(c["kind"] == "on" and c["status"] == "fail" for c in res["checks"])


def test_opposite_commands_are_tested_together():
    learned = behavior.learn(_pair(False), {})
    res = grouptest.test_group(_pair(False), grouptest.items_of(learned, "VALVE"), {})
    pair = [c for c in res["checks"] if c["kind"] == "pair"]
    assert pair and pair[0]["status"] == "warn"                       # 둘이 함께 나갈 수 있다 — 확인
    learned = behavior.learn(_pair(True), {})
    res = grouptest.test_group(_pair(True), grouptest.items_of(learned, "VALVE"), {})
    assert [c["status"] for c in res["checks"] if c["kind"] == "pair"] == ["pass"]


def test_api_groups_run_and_excel():
    job = _job(_fan_bundle())
    c = _client()
    d = c.get(f"/logic/api/jobs/{job}/groups").json()
    assert d["state"] == "done" and {g["equip"] for g in d["groups"]} >= {"FAN A", "FAN B", "VALVE C"}
    assert all(g["test"] is None for g in d["groups"])
    r = c.post(f"/logic/api/jobs/{job}/grouptest", json={"equip": "FAN A", "author": "홍길동"}).json()
    assert r["status"] == "pass" and r["author"] == "홍길동"
    d = c.get(f"/logic/api/jobs/{job}/groups").json()
    fan = next(g for g in d["groups"] if g["equip"] == "FAN A")
    assert fan["test"]["status"] == "pass" and fan["test"]["stale"] is False
    assert d["history"][-1]["equip"] == "FAN A"
    assert c.get(f"/logic/api/jobs/{job}/grouptest", params={"equip": "FAN A"}).json()["checks"]
    assert c.post(f"/logic/api/jobs/{job}/grouptest", json={"equip": "NOPE"}).status_code == 404
    x = c.get(f"/logic/api/jobs/{job}/grouptest.xlsx")
    assert x.status_code == 200 and x.content[:2] == b"PK"
    assert c.get("/logic/test").status_code == 200


def test_result_file_is_untouched_by_testing():
    job = _job(_fan_bundle())
    d = store.job_dir(job) if hasattr(store, "job_dir") else api._dir(job)
    before = (d / "result.json").read_bytes()
    _client().post(f"/logic/api/jobs/{job}/grouptest", json={"equip": "FAN A"})
    assert (d / "result.json").read_bytes() == before


def test_screens_have_one_button_test_and_replay():
    for f in ("runOne", "runAll", "detailHtml", "renderTop", "simLink"):
        assert f"function {f}" in TJS, f
    assert "prompt(" not in TJS and "confirm(" not in TJS             # 대시보드 iframe 은 브라우저 대화상자를 막는다 (L25c)
    assert 'id="run-all"' in THTML and 'id="kpis"' in THTML
    assert "function applyHashTest" in JS and 'id="gt-btn"' in (ROOT / "app/static/logic.html").read_text(encoding="utf-8")
