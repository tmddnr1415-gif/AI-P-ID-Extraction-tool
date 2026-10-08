"""hotfix49 — 대시보드형 화면 (왼쪽 메뉴 · 지표 카드 · 그래프).  화면 회차 · 엔진 0줄.

사용자: *"UI 를 이런 식으로 바꿔줘"* (사내 주간업무 Dashboard 사진 두 장 — 남색 왼쪽 메뉴 ·
제목 + 회색 부제 · 오른쪽 위 파란 버튼 · 붉은 알림 알약 · 큰 숫자 카드 · 막대·도넛 그래프).

지키는 것:
  ① 옛 화면의 요소 id 는 하나도 사라지지 않는다 (153개 — 다른 코드와 UI 시험이 그 id 로 찾는다)
  ② 결과 탭(`#tabs`)은 왼쪽 메뉴 안으로 옮겼고 `buildTabs` 는 그대로다
  ③ 대시보드는 새로 세는 값이 없다 — 서버가 이미 내던 `/home` · `/audit` · `/version` 만 읽는다
  ④ 도넛 색은 개정 상태마다 고정이고 서버의 `counts` 열쇠를 그대로 쓴다 (순위로 칠하지 않는다)
  ⑤ 엔진·서버 파일은 이 회차에 바뀌지 않는다
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")

# hotfix48 화면(9a58e21)의 id 전부 (153개).  하나라도 빠지면 그 id 로 찾는 코드가 조용히 null 을 받는다.
OLD_IDS = """
audit-line bar-fill body build build-text chips cmp cmp-changes cmp-foot cmp-head cmp-ov
cmp-sheet cmp-stage cmp-wrap colmenu count del-cands desc-groups diag drop drop-bubble
drop-head drop-lock drop-note drop-zone empty-note evidence excel fb-badge feedback-export file
filter gate-check grid gridwrap gutter-h gutter-m gutter-r gutter-v head infobars
infobars-toggle input-kind job-meta job-name joblist left legend-bar main markup-note
markup-toggle modal modal-body modal-title mode-bar mode-field mode-note mult-panel notes-band
notes-body notes-sum only-changed only-changed-wrap only-review open-review origin-filter ov
ovl-bytab ovl-fold ovl-items ovl-sum ovl-trace ovlegend page-note page-select pick-cancel
pick-note prog-actions prog-cancel prog-cancelwrap prog-done prog-elapsed prog-error
prog-error-body prog-hint prog-home prog-jobs prog-msg prog-now prog-pages prog-sheets
prog-skip prog-skip-body prog-tbfix prog-title prog-what progress proj-cancel proj-dup proj-msg
proj-name proj-new proj-new-btn proj-pick proj-rev proj-save reanalyse report-list report-n
rev-base rev-export rev-filter rev-label rev-note rev-switch review-badge review-codes
review-panel right row-add row-copy row-delete rules rules-body save-final scope sheet
sheet-panel side-left-tag split stage symbol-n symbols tabs tbfix tbfix-boxes tbfix-clear
tbfix-close tbfix-img tbfix-msg tbfix-next tbfix-page tbfix-prev tbfix-preview tbfix-save
tbfix-save-run tbfix-sizes tbfix-stage tbfix-who tmpl tmpl-body to-home wrap
""".split()


def _ids(src: str) -> list[str]:
    return re.findall(r'\bid="([^"]+)"', src)


def _block(src: str, start: str) -> str:
    i = src.index(start)
    return src[i:]


def test_old_ids_survive_and_are_unique():
    ids = _ids(HTML)
    assert len(ids) == len(set(ids)), "같은 id 가 둘"
    missing = [i for i in OLD_IDS if i not in ids]
    assert not missing, missing


def test_tabs_live_inside_the_sidebar():
    side = HTML[HTML.index('<aside id="sidebar"'):HTML.index("</aside>")]
    assert 'id="tabs"' in side
    assert 'id="nav-home"' in side and 'id="nav-projects"' in side
    # 결과 탭은 결과 화면이 열려 있을 때만 메뉴에 보인다
    assert "body.in-results #tabs" in CSS   # :has() 없이 — 오래된 브라우저에서도 결과 탭이 선다
    assert not any(":has(" in ln and "#tabs" in ln for ln in CSS.splitlines())
    assert "function watchMain()" in JS


def test_dashboard_reads_only_existing_endpoints():
    block = _block(JS, "hotfix49 — 대시보드형 화면")
    urls = set(re.findall(r'fetch\(\s*[`"]([^`"$?]+)', block))
    assert urls <= {"/version"}, urls          # /home · /audit 은 listHome · showAudit 가 받아 DASH 에 둔다
    assert "DASH.home = home" in JS and "DASH.audit =" in JS
    for verb in ("method: \"POST\"", "method: \"PATCH\"", "method: \"DELETE\""):
        assert verb not in block, verb


def test_donut_colours_follow_the_state_not_the_rank():
    block = _block(JS, "const DONUT_PARTS")
    head = block[:block.index("];")]
    keys = re.findall(r'\[\s*"([A-Z_]+)"', head)
    assert keys[:5] == ["UNCHANGED", "ADDED", "MODIFIED", "DELETED_CANDIDATE", "NOT_COMPARED"]
    cols = re.findall(r'#[0-9a-fA-F]{6}', head)
    assert len(set(cols)) == len(cols) >= 5
    # 이전 태그(MODIFIED_BEFORE)는 수정 칸에 더해진다 — 서버 counts 열쇠 그대로
    assert "MODIFIED_BEFORE" in block[:4000]


def test_nav_collapse_is_remembered_per_viewer_and_guarded():
    assert 'const NAV_KEY = "pid.nav.collapsed"' in JS
    block = _block(JS, "(function navCollapse()")[:900]
    assert block.count("try {") >= 2       # 저장소가 막힌 창에서도 화면이 선다
