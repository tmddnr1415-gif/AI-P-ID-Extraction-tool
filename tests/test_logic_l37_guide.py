"""L37 — 순차 동작 안내: 한 단계씩 '이 신호를 활성시키겠습니까?' 와 함께 이 신호가 무엇인지 · 왜 필요한지 ·
켜면 무엇이 달라지는지 (지금까지의 답 + 이 신호만으로 묶음 시뮬레이터를 앞뒤로 돌린 차이 — 판정 0줄)."""
from __future__ import annotations

from pathlib import Path

from app.logic import sequence
from tests.test_logic_l32_sequence import _bundle, _client, _job, _own_data  # noqa: F401  (fixture)

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


def test_effect_reports_gate_progress_and_target_only_when_conditions_are_all_given():
    sh = _bundle()
    # 허가만 — 첫 AND(허가 · NOT TRIP) 출력이 서지만 최종 출력(A2)은 아직
    e = sequence.effect(sh, 1, "cmd", 1, {}, {1: {"row:1": 1}}, gate={"block": "A1", "page": 1})
    assert e["target"] == {"before": 0, "after": 0, "steady": False}
    assert e["gate"] == {"inputs": 2, "on_before": 1, "on_after": 2, "out_before": 0, "out_after": 1}
    # 허가가 있는 상태에서 누름단추 — 최종 출력이 선다 · 목표 행이 '새로 켜지는 출력' 맨 앞
    e = sequence.effect(sh, 1, "cmd", 1, {1: {"row:1": 1}}, {1: {"block:PB": 1}}, gate={"block": "O", "page": 1})
    assert e["target"]["after"] == 1 and e["target"]["steady"]
    assert e["gained"][0]["row"] == 90 and e["gained"][0]["sheet"] == "G001"
    assert e["gate"]["out_before"] == 0 and e["gate"]["out_after"] == 1
    # TRIP 이 있으면 누름단추를 눌러도 서지 않는다 — 게이트가 판정한다 (L18)
    e = sequence.effect(sh, 1, "cmd", 1, {1: {"row:1": 1, "row:2": 1}}, {1: {"block:PB": 1}})
    assert e["target"]["after"] == 0 and "gate" not in e


def test_effect_follows_signals_to_other_sheets():
    sh = _bundle()
    # G002 의 두 입력을 주면 90행 AUTO REQ 가 서고 G001-3 으로 넘어간다
    e = sequence.effect(sh, 1, "cmd", 1, {2: {"row:1": 1}}, {2: {"row:2": 1}})
    assert any(x["sheet"] == "G002" and x["row"] == 90 for x in e["gained"])
    assert any(x["sheet"] == "G001" and x["row"] == 3 for x in e["linked"])


def test_effect_api_and_screen_wiring():
    job = _job(_bundle())
    c = _client()
    r = c.post(f"/logic/api/jobs/{job}/sequence/effect", json={
        "page": 1, "net": "cmd", "want": 1, "forces": {"1": {"row:1": 1}}, "add": {"1": {"block:PB": 1}},
        "gate": {"block": "O", "page": 1}}).json()
    assert r["target"]["after"] == 1 and r["gate"]["out_after"] == 1
    assert c.post(f"/logic/api/jobs/{job}/sequence/effect", json={"page": "x"}).status_code == 400
    # 화면: 안내 카드 · 질문 · 진행 막대 · 활성은 흐름을 그린다 · 미리 돌려 본 결과로 선 출력은 남은 질문 없이 끝
    for k in ("seqGuideHtml", "이 신호를 활성시키겠습니까?", "seqBarHtml", "/sequence/effect", "seqApply(false, a.v === \"yes\")",
              "reachedEarly"):
        assert k in JS, k
