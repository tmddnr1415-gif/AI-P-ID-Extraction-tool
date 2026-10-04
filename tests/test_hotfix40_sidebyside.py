"""hotfix40 — 나란히 보기: 왼쪽 최신 Rev 도면 · 오른쪽 직전 Rev 의 같은 도면번호 장.

사용자: *"좌측 화면은 최신 rev pid 가 출력되고 우측은 이전 rev pid 가 출력될 수 있는 기능."*
hotfix39 의 스위치(오가기)와 달리 **동시에** 본다.  소스로 못박는다 — 자기검증
(`spike/ui_audit_sidebyside.py`)이 실제로 띄워 본 것과 같은 전제들이다.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    i = JS.index(name)
    return JS[i:JS.index("\n}\n", i) + 3]


def test_the_pane_and_its_functions_exist():
    for name in ("function toggleSide", "async function cmpLoad", "async function cmpShow",
                 "function drawCmpOverlay", "function cmpApplyZoom", "function cmpSyncScroll"):
        assert name in JS, name
    for sid in ('id="cmp"', 'id="cmp-head"', 'id="cmp-stage"', 'id="cmp-sheet"', 'id="cmp-ov"'):
        assert sid in HTML, sid
    # 스위치 바로 다음 · 목록보다 앞
    assert HTML.index('id="rev-switch"') < HTML.index('id="cmp"') < HTML.index('id="review-panel"')
    # 켜면 오른쪽에서 스위치와 비교 창만 남는다 — 숨기기만 한다 (상태는 그대로)
    assert "#right.compare > :not(#rev-switch):not(#cmp) { display: none" in CSS


def test_the_switch_grows_a_third_button_that_toggles_side_mode():
    body = _fn("function renderRevSwitch")
    assert 'class="side' in body and "toggleSide(!S.side)" in body
    # 결과 전환 버튼은 data-job 이 있는 것만 — 세 번째 버튼이 switchView 로 흘러가면 안 된다
    assert 'querySelectorAll("button[data-job]")' in body


def test_left_is_always_the_current_result():
    """왼쪽이 직전 결과를 보는 중이면 현재로 돌아온 뒤 켠다 · 결과를 오가면 꺼진다."""
    body = _fn("function toggleSide")
    assert "S.job.id === pr.previous" in body and "switchView(pr.current).then(() => toggleSide(true))" in body
    sw = _fn("async function switchView")
    assert "if (S.side) toggleSide(false)" in sw
    op = _fn("async function open")
    assert 'S.side = false' in op


def test_the_right_page_follows_the_same_drawing_number_and_renumbered_sheets():
    body = _fn("async function cmpShow")
    assert "data.pages.find(p => p.drawing_no === want)" in body
    # hotfix38 의 도면번호 바뀐 장은 옛 번호로 찾는다 · 삭제 후보는 새 번호로 섰으므로 둘 다 본다
    assert "renumbered" in body and "ren.before" in body
    assert "d.drawing_no === page.drawing_no || d.drawing_no === want" in body
    # 장이 없으면 그렇게 말한다 — 첫 장으로 떨어지지 않는다
    assert "장이 이전 결과에 없습니다" in body
    # 왼쪽 장이 바뀌면 오른쪽도
    assert "if (S.side) cmpShow();" in _fn("function showPage(")


def test_zoom_and_scroll_are_shared_with_the_left():
    assert "cmpApplyZoom();" in JS[JS.index("function applyZoom()"):JS.index("function applyZoom()") + 120]
    body = _fn("function cmpSyncScroll")
    assert "scrollLeft = src.scrollLeft" in body and "S._cmpSyncing" in body


def test_the_previous_result_is_read_once_and_kept_in_memory():
    body = _fn("async function cmpLoad")
    assert "if (S.cmp[jobId]) return S.cmp[jobId];" in body
    assert "/pages" in body and "/rows" not in body       # 행은 읽지 않는다 — 층이 상자를 든다


def test_deleted_candidates_are_drawn_on_the_previous_sheet_not_judged_here():
    body = _fn("function drawCmpOverlay")
    assert '"delmark"' in body and '"DEL"' in body and '"DEL?"' in body
    # 판정은 서버의 deleted_candidates 그대로 — 여기서 거리·반경을 다시 재지 않는다
    assert "radius" not in body and "nearest" not in body
    assert "deletedRemark(d" in body
