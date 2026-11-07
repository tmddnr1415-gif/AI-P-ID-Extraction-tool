"""L42 — 그룹 시험: 신호마다 '어느 시트 어느 행' · 펼친 장비만 받기 · 배운 것 읽기 캐시 · LOGIC 창 '자리로 가기'."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.logic import api, behavior, grouptest, store
from tests.test_logic_l32_sequence import _client, _job
from tests.test_logic_l35_understand import _latched
from tests.test_logic_l36_grouptest import _fan_bundle

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")
TJS = (ROOT / "app/static/logic_test.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/logic.css").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def test_every_check_says_where_its_command_and_signals_are():
    sheets = _latched()
    learned = behavior.learn(sheets, {})
    x = grouptest.items_of(learned, "FAN A")[0]
    assert all(l.get("row") == int(l["key"][4:]) for l in x["labels"] if l["key"].startswith("row:"))
    res = grouptest.test_group(sheets, grouptest.items_of(learned, "FAN A"), {})
    for c in res["checks"]:
        assert c["cmd"]["page"] == x["page"] and c["cmd"]["row"] == x["row"] and c["cmd"]["sheet"]
        assert c["signals"], c["title"]
        for l in c["signals"]:
            assert l["page"] and l["sheet"] and l["text"]
            if l["key"].startswith("row:"):
                assert l["row"] == int(l["key"][4:])
    blk = next(c for c in res["checks"] if c["kind"] == "block")
    assert any(l["key"] == blk["key"] for l in blk["signals"])          # 막는 신호 자신도 자리와 함께


def test_behavior_api_can_send_one_equipment_only():
    job = _job(_fan_bundle())
    c = _client()
    c.get(f"/logic/api/jobs/{job}/groups")
    full = c.get(f"/logic/api/jobs/{job}/behavior", params={"start": 0}).json()["result"]
    one = c.get(f"/logic/api/jobs/{job}/behavior", params={"start": 0, "equip": "FAN A"}).json()["result"]
    assert {x["equip"] for x in full["items"]} > {"FAN A"}
    assert one["items"] and {x["equip"] for x in one["items"]} == {"FAN A"}
    assert one["key"] == full["key"] and one["summary"] == full["summary"]
    assert len(full["items"]) > len(one["items"])                       # 원본은 그대로 (함께 쓰는 캐시를 고치지 않음)
    assert len(c.get(f"/logic/api/jobs/{job}/behavior", params={"start": 0}).json()["result"]["items"]) == len(full["items"])


def test_behavior_load_is_read_once_until_the_file_changes(tmp_path):
    d = tmp_path / "job"
    d.mkdir()
    (d / behavior.FILE).write_text('{"items": [1]}', encoding="utf-8")
    a = behavior.load(d)
    assert behavior.load(d) is a
    import os, time
    (d / behavior.FILE).write_text('{"items": [1, 2]}', encoding="utf-8")
    os.utime(d / behavior.FILE, ns=(time.time_ns() + 10**9, time.time_ns() + 10**9))
    assert behavior.load(d)["items"] == [1, 2]


def test_screens_link_locations_and_repaint_one_row():
    assert "function locHtml" in TJS and "a.loc" in TJS and 'type: "goto"' in TJS
    assert "명령 자리" in TJS and "sigsHtml(c)" in TJS
    assert "function paintRow" in TJS and "function renderHead" in TJS
    toggle = TJS.split("async function toggle")[1].split("\n}\n")[0]
    assert "render()" not in toggle                                   # 펼치기가 393줄 표를 다시 만들지 않는다
    run = TJS.split("async function runOne")[1].split("\n}\n")[0]
    assert "render()" not in run
    assert "equip=${encodeURIComponent(equip)}" in TJS                 # 펼친 장비만 받는다
    assert "async function goLoc" in JS and '"goto"' in JS
    assert "fromWin" in JS                                            # 자리를 짚어 왔으면 From-To 보고 · 가르치기 창을 덮지 않는다
    assert ".lg-rows li > .d { flex: 1 1 150px; min-width: 150px; }" in CSS   # 칩이 넓어도 설명이 세로로 접히지 않게
