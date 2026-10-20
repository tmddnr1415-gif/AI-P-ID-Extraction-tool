"""L43 — 시트를 옮기는 동안 한 장의 선이 다른 장의 그림 위에 서지 않는다 (화면 소스 검사).

표 칸은 장마다 같아 표는 맞고 LOGIC 영역 선만 어긋나 보였다 (현장 사진 1A5J FO_G-524 · 순차 동작).
띄워서 잰 것은 spike 가 아니라 이 회차 기록에 있다 (그림을 0.5초 늦게 줄 때 옛 화면 128/297 ↔ 지금 0)."""
from pathlib import Path

JS = (Path(__file__).resolve().parents[1] / "app/static/logic.js").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    j = JS.index("\nfunction ", i + 10) if "\nfunction " in JS[i + 10:] else len(JS)
    k = JS.find("\nasync function ", i + 10)
    return JS[i:min(j, k) if k > 0 else j]


def test_overlay_waits_for_its_own_picture():
    f = _fn("openSheet")
    assert 'ov.style.visibility = "hidden"' in f            # 그림이 서기 전에는 선도 숨긴다
    assert "img.decode" in f and "img.dataset.page" in f     # 그 장 그림이 풀린 뒤에 보인다
    assert f.index("stopAnim()") < f.index("L.sheet = s")     # 앞 장의 흐름이 새 장의 선을 칠하지 않게


def test_sim_skips_while_sheet_and_page_differ():
    f = _fn("runSim")
    assert "L.sheet.page !== L.page" in f
    assert "L.sheet !== askSheet" in f


def test_sequence_does_not_simulate_twice_on_sheet_change():
    assert "openSheet(n.page, { noSim: true })" in JS
    assert "openSheet(t.page, { noSim: true })" in JS
