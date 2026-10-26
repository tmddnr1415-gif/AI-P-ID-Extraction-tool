"""L29 — 입력 신호를 줄 때 종류와 값을 분명히 (디지털 1 활성 / 0 비활성 · 아날로그 mA = 공학값) · 많은 묶음에서도 가볍게."""
from __future__ import annotations

import gc
import json
import random
from pathlib import Path

import pytest

from app.logic import api, store

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    j = JS.find("\nfunction ", i + 10)
    k = JS.find("\nasync function ", i + 10)
    ends = [x for x in (j, k) if x > 0]
    return JS[i:min(ends)] if ends else JS[i:]


def test_one_place_says_what_an_input_holds_now():
    """메뉴 · 행 목록 · 도면 꼬리표가 한 함수(signalNow)를 읽는다 — 서로 다른 말을 하지 않게."""
    sn = _fn("signalNow")
    assert '"digital"' in sn and '"analog"' in sn and "내가 줌" in sn and "기본값" in sn
    for f in ("forceMenu", "sigChip", "drawAnalogMarks"):
        assert "signalNow(" in _fn(f) or "nowLine(" in _fn(f), f


def test_analog_input_menu_takes_the_value_inline_with_presets():
    fm = _fn("forceMenu")
    assert "아날로그 입력" in fm and "디지털 입력" in fm
    assert 'id="an-q"' in fm and "MA_PRESETS" in fm and "data-ma" in fm
    assert "1</b> 활성" in fm and "0</b> 비활성" in fm


def test_one_input_holds_one_kind_of_signal():
    """디지털 1/0 을 주면 그 입력의 아날로그 값은 빠지고, 아날로그 값을 넣으면 디지털 강제는 풀린다."""
    sf = _fn("setForce")
    assert "delete L.analog[L.page][key]" in sf
    sa = _fn("setAnalog")
    assert "delete L.allForces[p][key]" in sa


def test_status_popup_lists_analog_values_from_every_sheet():
    assert "내가 넣은 아날로그 값" in JS and "data-an-off" in JS
    ag = _fn("analogGivenItems")
    assert "L.analog" in ag and "fmtMa(" in ag


def test_result_load_moves_the_big_tree_out_of_the_collector(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    store._RES.clear()
    job, d = store.new_job("x.pdf")
    store.write_result(d, {"sheets": [{"page": 1, "rows": [{"n": i} for i in range(50)]}]})
    calls = []
    real = gc.freeze
    monkeypatch.setattr(gc, "freeze", lambda: (calls.append(1), real())[1])
    res = store.read_result(d)
    assert calls == [1] and res["sheets"][0]["rows"][3]["n"] == 3
    store.read_result(d)
    assert calls == [1], "캐시에 있으면 다시 하지 않는다"
    gc.unfreeze()
    store._RES.clear()


def test_cache_key_is_the_rule_content_not_the_library_file_time():
    assert api._rules_key([]) == ""
    a = api._rules_key([{"choice": "AND", "sig": {"text": "X"}}])
    assert a == api._rules_key([{"sig": {"text": "X"}, "choice": "AND"}])
    assert a != api._rules_key([{"choice": "OR", "sig": {"text": "X"}}])
