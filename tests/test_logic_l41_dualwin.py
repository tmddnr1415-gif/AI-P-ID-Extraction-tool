"""L41 — 듀얼 모니터: 검토 결과 창 · 그룹 시험 창이 LOGIC 창과 이어진다 (화면 코드 소스 검사)."""
from pathlib import Path

JS = Path(__file__).resolve().parents[1] / "app" / "static"


def test_review_pane_talks_to_the_logic_window():
    s = (JS / "logic.js").read_text(encoding="utf-8")
    assert "pane=review" in s and "startReviewPane" in s
    # 검토 결과 창의 항목을 누르면 LOGIC 창이 그 자리로 (없으면 새 LOGIC 창을 rvgo 로)
    assert 'type: "review-go"' in s and "rvgo=" in s
    assert '"review-go", "review-on", "review-marks", "grouptest-apply"' in s
    # 깜박임은 다시 그려도 지난 시간만큼 당긴다 (처음부터 다시 깜박이지 않게)
    assert "rv-halo" in s and "animation-delay:-" in s
    assert "postMessage(msg, location.origin)" in s


def test_group_test_window_sends_tests_to_logic():
    s = (JS / "logic_test.js").read_text(encoding="utf-8")
    assert 'type: "grouptest-apply"' in s and "location.origin" in s
    assert "data-chk" in s
    h = (JS / "logic_test.html").read_text(encoding="utf-8")
    assert 'id="link"' in h
    # LOGIC 쪽 단추는 새 창으로 연다
    js = (JS / "logic.js").read_text(encoding="utf-8")
    assert "popGroupTest" in js and "applyHashTest(L.job, d.equip" in js


def test_no_browser_dialogs():
    for f in ("logic.js", "logic_test.js"):
        s = (JS / f).read_text(encoding="utf-8")
        for bad in ("prompt(", "confirm(", "alert("):
            assert f"window.{bad}" not in s and f" {bad}" not in s.replace("askModal", ""), (f, bad)
