"""hotfix61 — 첫 화면 '저장된 프로젝트' 를 카드 + 리비전 타임라인으로 (화면 전용 · 엔진 0줄).

값은 전부 `/home` 이 이미 주는 것이고 새로 세는 것이 없다.  눌러서 여는 길(`a.revrow`) ·
지워진 리비전 갈래(링크 없음) · 프로젝트 삭제 버튼 · 도면 종류 칩은 그대로다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _block(start, end):
    return JS[JS.index(start):JS.index(end, JS.index(start))]


def test_cards_read_only_the_home_response():
    home = _block("async function listHome(", "const listJobs = listHome;")
    rev = _block("function revRow(", "function delButton(")
    # 한 번 받고(`/home`) 그 응답만 그린다 — 카드·타임라인이 따로 요청하지 않는다
    assert home.count("fetch(") == 1 and 'fetch("/home")' in home
    assert "fetch(" not in rev
    assert "pj-card" in home and "pj-stat" in home and "modeChip(projectMode(p))" in home
    assert "qtyDelta(r, revs[i + 1])" in home          # hotfix62 — 행 수가 아니라 계기 Q'ty


def test_the_ways_in_and_out_are_unchanged():
    rev = _block("function revRow(", "function delButton(")
    assert 'class="revrow"' in rev and "delButton(r.job_id)" in rev        # 여는 링크 · 분석 삭제
    branch = rev[rev.index("r.missing || r.deleted"):rev.index("return `<div class=\"revwrap")]
    assert "href" not in branch and "delButton" not in branch             # 지워진 리비전은 링크 없음
    home = _block("async function listHome(", "const listJobs = listHome;")
    assert "del-project" in home and 'data-project="${escape(p.name)}"' in home


def test_row_delta_is_neutral_and_skips_missing_revisions():
    d = _block("function qtyDelta(", "const TOP_BASIS")
    assert "before.missing || before.deleted" in d                       # 지워진 리비전과 견주지 않는다
    assert "▲" in d and "▼" in d
    # 행 수 변화는 좋고 나쁨이 아니다 — 위·아래가 같은 색
    rule = CSS[CSS.index(".rv-delta.up, .rv-delta.down"):].split("}")[0]
    assert "color" in rule


def test_mode_is_said_in_words_not_only_colour():
    css = CSS[CSS.index("hotfix61"):]
    for m in ("bid", "epc", "auto"):
        assert f".pj-card.{m}" in css
    assert "prefers-reduced-motion" in css
