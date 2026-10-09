"""hotfix26 — 가독성 · 편의 (1366×768 실측에서 나온 다섯).

  ① 범례 판 접기 (372px → 요약 한 줄 63px · pid.ovl.fold)
  ② 정보 띠 한 줄 (88px → 27px · 범례 변경/모드 충돌이면 접지 않는다)
  ③ 목록 ↔ 근거 패널 손잡이 (#gutter-r · pid.split.ev · 목록에 네 줄은 남긴다)
  ④ ↑ ↓ 로 행 이동 (입력칸에서는 잡지 않는다)
  ⑤ 목록 첫 두 열 고정 (둘째 열 자리는 첫 열의 실측 폭)
실제 동작은 `spike/ui_audit_hotfix26.py` 가 띄워서 확인한다 — 여기서는 구조만 못박는다.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def test_legend_fold_has_a_summary_that_counts_the_same_things_as_the_rows():
    assert 'id="ovl-fold"' in HTML and 'id="ovl-sum"' in HTML and 'id="ovl-trace"' in HTML
    seg = JS.split("function buildOverlayLegend() {", 1)[1].split("\n}\n", 1)[0]
    assert '$("#ovl-sum")' in seg and "counts.SCT" in seg and "counts.VENDOR_EXCLUDED" in seg
    assert '"pid.ovl.fold"' in JS
    assert "#ovlegend.folded #ovl-items, #ovlegend.folded #ovl-trace" in CSS
    assert ".ovl-row .ovl-label { white-space: nowrap; }" in CSS


def test_infobars_compact_by_default_but_never_when_something_changed():
    assert '<div id="infobars" class="compact">' in HTML and 'id="infobars-toggle"' in HTML
    seg = JS.split("function applyInfobars() {", 1)[1].split("\n}\n", 1)[0]
    assert '".legend-bar.changed:not(.hidden)"' in seg
    assert 'bars.classList.toggle("compact", !open && !changed)' in seg
    assert "#infobars.compact details.lb-saved, #infobars.compact .lb-changes { display: none; }" in CSS


def test_evidence_gutter_keeps_four_rows_of_the_grid():
    assert 'id="gutter-r"' in HTML
    seg = JS.split('const SPLIT_KEY = "pid.split";', 1)[1]
    assert '_dragGutter(ge, "row"' in seg and "share - 120" in seg
    assert "{ ...state, ev: null }" in seg
    assert "if (v.ev) { ev.style.height" in seg


def test_arrow_keys_skip_inputs_and_follow_grid_order():
    seg = JS.split('if (ev.key !== "ArrowDown" && ev.key !== "ArrowUp") return;', 1)[1].split("\n});", 1)[0]
    assert 'tag === "input" || tag === "textarea" || tag === "select"' in seg
    # hotfix69 — 목록은 보이는 행만 그리므로 순서는 목록(`S.vlist`)에서 읽고, 화면 밖 행은 굴려 그린다
    assert "const list = S.vlist || [];" in seg and "select(k, true)" in seg and "revealRow(k)" in seg


def test_first_two_columns_are_sticky_and_the_second_offset_is_measured():
    assert "#grid th:nth-child(2), #grid td:nth-child(2) { left: var(--c1w, 79px)" in CSS
    assert 'grid.style.setProperty("--c1w"' in JS
    # 고정 열의 행 음영은 반투명을 종이색에 미리 섞은 값 — 색 이름을 새로 정하지 않는다
    assert "tbody tr.sel td:nth-child(-n+2) { background: color-mix(in srgb, var(--panel) 90%, #1a5fb4); }" in CSS


def test_evidence_sections_do_not_change_values():
    seg = JS.split("function showEvidence(row) {", 1)[1].split("\nfunction ", 1)[0]
    assert seg.count('sec("') >= 4 and 'const sec = (t) => pairs.push(["§" + t, "§"]);' in seg
    assert 'k.startsWith("§")' in seg and '<dt class="ev-sec">' in seg
