"""L33 — 배운 동작: 묶음의 모든 명령을 켜 보며 서는 조합(꼭 필요한 신호만)과 막는 자리를 배운다."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.logic import api, behavior, store
from tests.test_logic_l32_sequence import _B, _P, _bundle, _client, _job, _sheet

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def test_learner_finds_a_minimal_set_that_raises_the_command():
    sheets = _bundle()
    r = behavior.learn_one(sheets, 1, 90, 1, {})
    assert r["reached"], r
    F = r["forces"]
    keys = {(pg, k) for pg, v in F.items() for k in v}
    assert (1, "row:1") in keys                 # PERMISSIVE 는 꼭 필요
    assert (1, "row:2") not in keys or F[1]["row:2"] == 0   # TRIP 은 1 이면 안 된다 — 주지 않거나 0
    # 꼭 필요한 것만 — 하나라도 빼면 안 선다
    for pg, v in F.items():
        for k in v:
            G = {p: dict(x) for p, x in F.items()}
            del G[pg][k]
            hit, _, _ = behavior._hit(sheets, G, 1, "cmd", 1, {}, None)
            assert not hit, (pg, k)
    assert r["labels"]


def test_undriven_target_is_not_a_success():
    g = _sheet(1, "G001", [{"n": 1, "side": "L", "net": "a", "desc": "X", "fm": ""},
                           {"n": 90, "side": "R", "net": "cut", "desc": "PUMP C START CMD", "to": ""}],
               {"A": _B("and")}, [_P("A", "a", "in"), _P("A", "b", "out")])
    r = behavior.learn_one([g], 1, 90, 1, {})
    assert not r["reached"] and r.get("undriven")


def test_conflicting_wants_prefer_the_one_that_lets_the_command_stand():
    sheets = _bundle()
    tree = {"t": "and", "id": "r", "kids": [
        {"t": "leaf", "kind": "row", "key": "row:1", "page": 1, "want": 0},
        {"t": "leaf", "kind": "row", "key": "row:1", "page": 1, "want": 1}]}
    assert behavior._forces(tree, {}, 1)[1]["row:1"] == 1
    assert behavior._forces(tree, {}, 0)[1]["row:1"] == 0


def test_learn_whole_bundle_and_api():
    out = behavior.learn(_bundle(), {})
    assert out["total"] >= 2 and out["reached"] >= 1
    job = _job(_bundle())
    c = _client()
    r = c.get(f"/logic/api/jobs/{job}/behavior").json()
    assert r["state"] == "done" and r["result"]["total"] == out["total"]
    assert any(x["reached"] and x["equip"] == "PUMP A" for x in r["result"]["items"])
    assert c.get(f"/logic/api/jobs/{job}/behavior?start=0").json()["state"] == "done"


def test_wizard_shows_learned_behavior():
    for f in ("seqLoadLearn", "seqLearnCard", "seqRunLearned", "seqLearned"):
        assert f"function {f}" in JS or f"{f} =" in JS, f
    assert "/behavior" in JS
