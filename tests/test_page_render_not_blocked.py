"""2026-11-18 — 장 그림은 무거운 PDF 읽기 뒤에 줄 서지 않는다 ("List 는 나오는데 P&ID 가 안 나온다").

예전에는 장 그림(render_now)과 무거운 일(call)이 같은 일꾼 둘을 썼다.  무거운 일 둘이 돌면 장 그림은 그것이 끝날
때까지(최대 60초) 오지 않았고, 화면은 아무 말 없이 비어 있었다.
"""
import threading
import time

import pymupdf
import pytest

from app import page_warm


@pytest.fixture()
def pools(monkeypatch):
    monkeypatch.setenv("PID_RENDER_POOL", "1")
    monkeypatch.setitem(page_warm._RENDER_SKIP, "until", 0.0)
    yield
    for k in ("render", "heavy"):
        p = page_warm._POOL.get(k)
        if p is not None:
            p.terminate()
            page_warm._POOL[k] = None


def _pdf(tmp_path):
    d = pymupdf.open()
    d.new_page(width=300, height=200).insert_text((40, 80), "P&ID")
    p = tmp_path / "a.pdf"
    d.save(p)
    return p


@pytest.mark.slow
def test_render_does_not_wait_behind_heavy_calls(tmp_path, pools):
    pdf = _pdf(tmp_path)
    page_warm.prime()
    assert page_warm.render_now(pdf, tmp_path / "warm.png", 1, 1.6) is True      # 일꾼을 깨워 둔다
    busy = [threading.Thread(target=lambda: page_warm.call(time.sleep, (6,))) for _ in range(2)]
    for t in busy:
        t.start()
    time.sleep(1.0)                                   # 무거운 일 둘이 일꾼을 다 차지한 뒤
    t0 = time.monotonic()
    ok = page_warm.render_now(pdf, tmp_path / "p1.png", 1, 1.6)
    took = time.monotonic() - t0
    for t in busy:
        t.join()
    assert ok is True and (tmp_path / "p1.png").is_file()
    assert took < 3.0, f"장 그림이 무거운 일 뒤에서 {took:.1f}초 기다렸다"


def test_stuck_worker_is_skipped_next_time(tmp_path, pools, monkeypatch):
    """일꾼이 답하지 않으면(시간 초과) None — 그리고 한동안은 일꾼을 기다리지 않는다 (서버가 직접 그린다)."""
    import multiprocessing as mp

    class Never:
        def apply_async(self, *a, **k):
            class R:
                def get(self, timeout):
                    raise mp.TimeoutError()
            return R()
    calls = []
    monkeypatch.setattr(page_warm, "_pool", lambda kind="render": calls.append(kind) or Never())
    assert page_warm.render_now(tmp_path / "a.pdf", tmp_path / "x.png", 1, 1.6) is None
    assert page_warm.render_now(tmp_path / "a.pdf", tmp_path / "x.png", 1, 1.6) is None
    assert calls == ["render"]                        # 두 번째는 일꾼을 부르지도 않았다


def test_wait_is_short():
    assert page_warm.RENDER_WAIT <= 20


def test_viewer_says_it_is_waiting_and_guards_zoom():
    """화면: 도면 칸이 말없이 비지 않는다 · 그림이 오기 전 [맞춤] 이 배율을 무한대로 만들지 않는다."""
    from app import paths
    js = paths.resource("app", "static", "app.js").read_text(encoding="utf-8")
    assert "도면 그림을 받는 중입니다" in js and "다시 받기" in js
    assert "if (!S.natural.w) return;" in js
    assert "Number.isFinite(S.zoom)" in js
    assert "pre.onload = () => setTimeout(go, 800);" in js
    css = paths.resource("app", "static", "styles.css").read_text(encoding="utf-8")
    assert ".sheet-err.wait" in css


def test_rev_switch_restores_where_you_were():
    """직전/현재 결과를 오갈 때 배율과 함께 보던 자리도 되살린다 (확대한 채 돌아오면 왼쪽 위 빈 구석만 보이던 것)."""
    from app import paths
    js = paths.resource("app", "static", "app.js").read_text(encoding="utf-8")
    assert "snap._scroll = st ? [st.scrollLeft, st.scrollTop] : null;" in js
    assert "S.pendingScroll = snap._scroll" in js
    i = js.index("if (S.pendingScroll) {")
    block = js[i:i + 400]
    assert "void st.scrollWidth;" in block and block.index("void st.scrollWidth;") < block.index("st.scrollLeft = S.pendingScroll[0]")
