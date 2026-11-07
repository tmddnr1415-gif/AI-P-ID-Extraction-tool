"""hotfix39 — 직전 P&ID 결과 ↔ 현재 결과 스위치 (오른쪽 상단 · 메모리 캐시).

사용자: *"개정된 P&ID 가 들어오면 오른쪽 list 및 속성란을 … 이전 직전 P&ID 를 불러와서 선택
가능하도록 … 오른쪽 상단에 이전 P&ID 표기와 현재 P&ID 출력 결과 표기 … 화면 전환이 무겁지
않고 가볍고 빠르게."*  소스로 못박는다 — 자기검증 첫 실행이 함수 하나가 통째로 사라진 것을
잡았다 (`renderRevSwitch is not defined`): 리팩터가 그 사이 블록을 지웠다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def test_the_switch_and_its_four_functions_exist():
    for name in ("function snapshotView", "function restoreView", "function renderRevSwitch",
                 "async function switchView", "function renderRevLabel", "const VIEW_KEYS"):
        assert name in JS, name
    assert 'id="rev-switch"' in HTML
    # 오른쪽 맨 위 — 검토 띠보다 앞에 선다
    assert HTML.index('id="rev-switch"') < HTML.index('id="review-panel"')


def test_a_cached_result_is_restored_without_result_requests():
    """메모리 복원 경로에는 결과를 다시 읽는 fetch 가 없다 — 그리기만 한다."""
    body = JS[JS.index("function restoreView"):JS.index("function renderRevSwitch")]
    assert "fetch(" not in body and "await " not in body
    assert "renderRevLabel()" in body and "renderGrid()" in body and "buildPageSelect()" in body
    # 주소는 바꾸되 hashchange 로 다시 열지 않는다
    assert "history.replaceState" in body and "location.hash =" not in body


def test_the_first_visit_uses_the_ordinary_open_then_caches():
    body = JS[JS.index("async function switchView"):]
    body = body[:body.index("\n}\n") + 3]
    assert "await open(jobId)" in body and "snapshotView()" in body
    # 장은 쪽 번호가 아니라 같은 도면번호를 따라간다 (13회차 — 개정 때 장 순서가 바뀐다)
    assert "p.drawing_no === want" in body


def test_the_revision_label_is_drawn_by_one_function():
    """열기와 복원이 같은 라벨 함수를 부른다 — 두 벌을 두면 갈린다 (11회차 규칙)."""
    assert JS.count("renderRevLabel()") >= 2
    assert len(re.findall(r"el\.textContent = S\.rev\.label", JS)) == 1


def test_the_server_names_the_previous_and_next_jobs():
    body = MAIN[MAIN.index("def job_revision"):MAIN.index("def confirm_deleted")]
    assert '"previous_job_id": previous_job' in body and '"next_jobs": next_jobs' in body
    # 장부(project.json)의 사실이고 여기서 판정하지 않는다
    assert "revisions.load_project" in body
