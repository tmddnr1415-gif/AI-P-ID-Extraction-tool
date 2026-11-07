"""L70 — 최종 명령(Output · START · RUN · STOP · TRIP · OPEN · CLOSE · CMD)에서 최초 입력까지 게이트 단계별로 거슬러 올라가기.

  * 출력 행 찾기 — 동작 낱말이 없는 출력도 고른다 (한두 글자 낱말은 낱말 통째로 · Typical 은 뒤로).
  * 게이트 단계 — 조건 나무(L32 와 같은 서버 길)의 게이트 마디마다 한 단계: AND 는 '모두 · 거슬러 올라갈까' ·
    OR 는 '어느 것을 켤까' · 건너뛰기.  판정 0줄 — 신호를 주는 것은 잎에서뿐이다 (화면 소스로 못박는다).
"""
from __future__ import annotations

from pathlib import Path

from app.logic import sequence
from tests.test_logic_l32_sequence import _bundle, _client, _job, _own_data  # noqa: F401  (픽스처를 그대로 쓴다)

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/logic.js").read_text(encoding="utf-8")


def test_outputs_finds_any_output_row_and_matches_short_words_whole():
    r = sequence.outputs(_bundle(), "PUMP A")
    descs = [x["desc"] for x in r["items"]]
    assert "PUMP A START CMD" in descs and "PUMP A FAULT" not in descs
    assert "PUMP A FAIL TO START FAULT" in descs                 # 동작 낱말이 아니어도 출력이면 고른다
    assert all(x["action"] in (None, "START") for x in r["items"])
    r2 = sequence.outputs(_bundle(), "A")                         # 'A' 는 낱말 통째 — VALVE 의 A 에 맞지 않는다
    assert all("VALVE" not in x["desc"] for x in r2["items"])
    assert sequence.outputs(_bundle(), "")["total"] == 4          # 설명 있는 출력 행 전부
    assert r["items"][0]["action"] == "START"                     # 동작 행이 먼저


def test_outputs_api():
    job = _job(_bundle())
    r = _client().get(f"/logic/api/jobs/{job}/outputs", params={"q": "OPEN"}).json()
    assert [x["desc"] for x in r["items"]] == ["VALVE B OPEN CMD"]


def test_plan_has_a_gate_node_per_gate_for_the_gate_by_gate_walk():
    p = sequence.plan(_bundle(), 1, 90, 1)
    gates = [v for v in p["nodes"].values() if v.get("gate")]
    logic = sorted(v["gate"]["logic"] for v in gates)
    assert {"and", "or"} <= set(logic)                            # AND(최종) · OR(AUTO REQ · START 단추)
    orn = next(v for v in gates if v["gate"]["logic"] == "or")
    assert orn["t"] == "any" or any(p["nodes"][k]["t"] == "any" for k in orn.get("kids", []))
    assert all(v.get("asks", 0) > 0 for v in gates)               # 묻는 게이트는 아래에 답할 것이 있다


def test_gate_steps_never_force_signals_themselves():
    i = JS.index("async function seqAnswer(a)")
    body = JS[i:JS.index("\nasync function seqBack", i)]
    gate = body[:body.index("a.key = seqKeyOf(n)")]
    assert "seqForces" not in gate and "L.allForces" not in gate  # 게이트 단계는 갈 길만 정한다
    assert "seqGateMode" in JS and "seqGateStepHtml" in JS and "seqPathHtml" in JS
    fz = JS[JS.index("function seqForces("):JS.index("async function seqTryLeaf")]
    assert 'v === "skip") return' in fz                           # 건너뛴 게이트 아래는 주지 않는다


def test_pulse_command_counts_as_reached_when_any_frame_hit():
    f = JS[JS.index("async function seqFinish("):]
    assert "frames.findIndex" in f and "pulsed" in f
