"""hotfix132 (D2 · D3 · D5 · D6 · D8 · D9) — LOGIC 다섯 화면의 글 · 구조 (응답 HTML 과 정적 파일 내용으로 확인)."""
from __future__ import annotations

import re

import pytest

from app import paths


def _s(name):
    return paths.resource("app", "static", name).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app)


def test_names_are_unified_to_jakdo_and_test_link_is_in_logic_head(client):
    h = client.get("/logic").text
    assert 'href="/logic/test"' in h and "블록 시험" in h
    assert 'target="_blank"' not in h and "(새 창)" not in h
    assert 'placeholder="시트-행으로 이동 (예: G049-40)"' in h
    assert '<label for="lh-project">' in h
    dw = client.get("/logic/draw").text
    assert "<h1>LOGIC 작도</h1>" in dw and "<h2>LOGIC 작도</h2>" in dw and "Logic 작성" not in dw and "LOGIC 작성" not in dw
    assert '<label for="h-project">' in dw and 'id="modal" class="dw-modal" hidden tabindex="-1"' in dw
    sg = client.get("/logic/signal").text
    assert "LOGIC 작도" in sg and "Logic 작성" not in sg
    for path in ("/logic", "/logic/draw", "/logic/test", "/logic/commission", "/logic/signal"):
        body = client.get(path).text
        assert not re.search(r"(Logic|LOGIC) 작성", body), path


def test_sample_buttons_only_with_dev_and_dictionary_wording():
    js = _s("logic.js")
    assert "/[?&]dev=1(&|$)/.test(location.search)" in js
    assert "기호 사전 — 신호 처리 기호" in js and "학습 사전 — Signal Processing" not in js
    assert "내장 예제 Logic 을 분석합니다 (연습용)" in js


def test_errors_are_red_and_simulation_failure_is_visible():
    js, css = _s("logic.js"), _s("logic.css")
    assert "function status(t, kind)" in js and 'classList.toggle("err", kind === "err")' in js
    assert 'addEventListener("unhandledrejection"' in js
    assert "async function runSim_(" in js and '"시뮬레이션을 계산하지 못했습니다 — " + e.message, "err"' in js
    assert 'status("메모 저장 실패 — " + err.message, "err")' in js
    assert 'status(`분석 실패 — ${st.error || ""}`, "err")' in js
    assert ".lg-status.err" in css and "⚠" in css


def test_api_turns_server_errors_into_plain_korean_in_all_four_screens():
    for name in ("logic.js", "logic_draw.js", "logic_test.js", "logic_commission.js"):
        js = _s(name)
        assert "보낸 값의 형식이 올바르지 않습니다" in js, name
        assert '"서버 오류 (" + r.status + ")"' in js, name
        assert "서버와 연결하지 못했습니다 — 서버가 켜져 있는지 확인하고 새로 고침(F5) 하세요" in js, name
        assert "err.status = r.status" in js, name
    assert 'loadJobs().catch((e) => { const el = $("#empty"); el.hidden = false; el.textContent = e.message; })' in _s("logic_test.js")
    assert "openJob(e.target.value).catch(" in _s("logic_test.js") and "openJob(e.target.value).catch(" in _s("logic_commission.js")
    lj = _s("logic.js")
    assert 'const el = $("#empty"); if (el) { el.hidden = false; el.textContent = e.message; }' in lj


def test_empty_states_in_test_and_commission():
    assert "[hidden] { display: none !important; }" in _s("logic_test.css")
    for name in ("logic_test.js", "logic_commission.js"):
        js = _s(name)
        assert "아직 분석한 Logic 이 없습니다 — 먼저 <a href=\"/logic${esc(location.search)}\">LOGIC 검토</a>에서" in js, name
    assert "LOGIC 검토 화면과 연결 안 됨" in _s("logic_test.js")
    assert "장비 하나씩 기동·정지 신호를 넣어 로직이 맞게 동작하는지 봅니다" in _s("logic_test.html")


def test_seed_author_is_shown_as_builtin():
    js = _s("logic_draw.js")
    assert js.count('"Claude"') == 1 and 'const whoKo = a => (a === "Claude" ? "기본 제공"' in js
    assert "esc(whoKo(lu.author))" in js and js.count("esc(whoKo(it.author))") == 3
    assert "pv.authors.map(whoKo)" in js and "whoKo((it.edited || {}).author)" in js
    assert "esc(S.inst.author || \"\")" in js       # 계기 리스트 올린 사람은 그대로


def test_save_conflict_ui_sends_base_and_handles_409():
    js = _s("logic_draw.js")
    assert "base: baseOf()" in js and "force: true" in js and "e.status === 409" in js
    assert "다른 사람이 먼저 저장했습니다" in js and "내 판으로 덮기" in js and "새로 고침" in js


def test_keyboard_and_focus():
    lj, dj = _s("logic.js"), _s("logic_draw.js")
    assert '<label class="drop" tabindex="0" role="button">' in lj and "drop.onkeydown" in lj and "e.preventDefault(); inp.click();" in lj
    assert "const prev = document.activeElement;" in dj and 'querySelector("input,select,textarea,button") || $("#modal")).focus()' in dj
    assert 'lb.tabIndex = 0; lb.setAttribute("role", "button");' in dj
    assert ".dw-stage:focus-visible" in _s("logic_draw.css") and ".gt-who input:focus-visible" in _s("logic_test.css")
    assert ".lh-mats .drop:focus-visible" in _s("logic.css")
    sj, sc = _s("logic_signal.js"), _s("logic_signal.css")
    assert 'aria-label="${esc(String(name).replace(/<[^>]*>/g, ""))} 값"' in sj and "슬라이더" in sj and "계수\"" in sj
    assert "9.5px" not in sc and ".sym.sm { font-size: 10.5px" in sc


def test_shell_hides_back_links_only_when_shell_is_on():
    assert "body.pid-shell-on .lg-home { display: none; }" in _s("logic.css")
    assert "body.pid-shell-on .dw-back { display: none; }" in _s("logic_draw.css")
    assert "body.pid-shell-on .gt-back { display: none; }" in _s("logic_test.css")
    assert "body.pid-shell-on #back { display: none; }" in _s("logic_commission.css")
    assert "body.pid-shell-on .sp-back { display: none; }" in _s("logic_signal.css")


def test_screen_heads_use_the_one_set_of_names(client):
    """hotfix132 — 머리 이름도 한 벌(블록 시험 · 시운전 · 신호 처리) · 검토 새 창의 실패도 붉게."""
    assert "<h1>블록 시험</h1>" in client.get("/logic/test").text
    assert "<h1>시운전</h1>" in client.get("/logic/commission").text
    assert "<h1>신호 처리</h1>" in client.get("/logic/signal").text
    assert 'startReviewPane().catch((e) => status(e.message, "err"))' in _s("logic.js")
