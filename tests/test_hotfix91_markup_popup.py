"""hotfix91 — 마크업: 사각형을 놓으면 판이 **바로** 뜨고, 제안값은 뒤에 채워진다.

* 서버: 제안·행추가 엔드포인트는 `async def` 가 아니다 (그 장을 처음 읽는 3~5초 동안
  이벤트 루프를 잡으면 서버 전체가 멈춘다).  같은 장을 동시에 읽는 둘은 자물쇠가 줄 세운다.
* 화면: `markupDialog` 는 `openModal` 을 `fetch` 보다 먼저 부르고, 사람이 손댄 칸은 덮지 않는다.
"""
from __future__ import annotations
import inspect, re, threading, time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    i = JS.index(f"async function {name}(")
    j = JS.index("\nfunction ", i + 10)
    k = JS.index("\nasync function ", i + 10)
    return JS[i:min(j, k)]


def test_endpoints_run_in_the_threadpool_not_on_the_event_loop():
    from app import main
    assert not inspect.iscoroutinefunction(main.markup_propose)
    assert not inspect.iscoroutinefunction(main.add_row)


def test_propose_and_probe_share_one_lock():
    from app import pipeline
    assert isinstance(pipeline._PROPOSE_LOCK, type(threading.RLock()))
    assert "_PROPOSE_LOCK" in inspect.getsource(pipeline.propose_at)
    assert "_PROPOSE_LOCK" in inspect.getsource(pipeline.probe_point)


def test_two_threads_do_not_read_the_same_page_at_once(monkeypatch):
    """미리 읽기와 사람이 그린 사각형이 겹쳐도 한 번에 하나만 장을 읽는다."""
    from app import pipeline
    inside, peak, lock = [0], [0], threading.Lock()

    def fake(pdf_path, page_no, layout_moved):
        with lock:
            inside[0] += 1; peak[0] = max(peak[0], inside[0])
        time.sleep(0.15)
        with lock:
            inside[0] -= 1
        return None            # "그 장이 없다" — 제안은 error 로 돌아온다

    monkeypatch.setattr(pipeline, "_propose_page", fake)
    outs = []
    ts = [threading.Thread(target=lambda: outs.append(
        pipeline.propose_at(Path("x.pdf"), 1, [0, 0, 1, 1]))) for _ in range(3)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert peak[0] == 1
    assert all("error" in o for o in outs)


def test_dialog_opens_before_the_proposal_is_fetched():
    src = _fn("markupDialog")
    assert src.index("openModal(") < src.index("fetch(`/jobs/${S.job.id}/markup/propose`")
    # 제안이 오기 전에도 칸은 있다 — 그리고 제안이 오면 사람이 손댄 칸은 덮지 않는다
    assert "mk-status" in src and "도면에서 제안값을 읽는 중" in src
    assert "dataset.touched" in src and "untouched(" in src
    # 저장은 제안을 기다린 뒤 출처를 적는다
    assert "await propPromise" in src
    assert src.index("await propPromise") < src.index('scope_source = (prop.scope_source')


def test_the_prewarm_still_uses_the_same_endpoint():
    src = JS[JS.index("async function prewarmMarkup("):JS.index("function updateMarkupNote(")]
    assert "/markup/propose" in src
