"""hotfix44 — 결과 화면의 `대조 다시` 버튼 (재분석 없이 대조만 · 서버 API 는 13회차부터 있었다)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def test_the_switch_has_a_recompare_button_that_calls_the_existing_endpoint_once():
    assert 'class="recmp"' in JS and "async function recompare(" in JS
    body = JS[JS.index("async function recompare("):]
    body = body[:body.index("\n}\n") + 3]
    assert "fetch(`/jobs/${jobId}/revision`, { method: \"POST\"" in body
    assert body.count("method: \"POST\"") == 1
    # 판정을 화면에서 다시 하지 않는다 — 서버가 준 counts 를 그대로 적는다
    assert "out.counts" in body and "compare(" not in body.replace("recompare(", "")


def test_recompare_asks_first_and_drops_the_stale_memory_cache():
    body = JS[JS.index("async function recompare("):]
    body = body[:body.index("\n}\n") + 3]
    assert "confirm(" in body                 # 사람이 누른 뒤 한 번 더 묻는다
    assert "S.viewCache = {}" in body          # 옛 판정을 든 화면 캐시를 버린다
    assert "await open(jobId)" in body          # 다시 연다 — 상태를 손으로 고치지 않는다
    assert "프로젝트에 묶인 분석이 아니라" in body


def test_recompare_acts_on_the_current_revision_even_while_viewing_the_previous_one():
    m = re.search(r"rb\.onclick = \(\) => recompare\((pr\.current), ", JS)
    assert m, "버튼은 짝의 '현재' 분석을 대조한다 (직전 결과를 보는 중이어도)"
