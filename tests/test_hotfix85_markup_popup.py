"""hotfix85 — 마크업 사각형을 그은 뒤 팝업이 **바로** 뜬다.

사용자: *"마크업 지정하고나서, 속성 입력 팝업 까지 너무 오랜 시간이 걸린다 개선해줘"*.
팝업은 제안(그 장을 처음 읽는 3~4초)을 기다리지 않고 먼저 열리고, 제안은 나중에 **빈 칸만** 채운다.
서버 쪽 제안·행추가는 작업 스레드에서 돌고(`async def` 가 아니다) 그 사이 다른 요청이 멈추지 않는다.
공유 sqlite 연결은 읽기 행을 잠금 안에서 가져온다 — 스레드가 겹치면 `fetchone` 이 None 을 내던 것.
화면 동작은 `spike/ui_audit_markup_popup.py` 가 띄워서 긋는다.
"""
from __future__ import annotations

import inspect
import re
import sqlite3
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    return JS[i:JS.index("\n}\n", i) + 2]


def test_popup_opens_before_the_proposal_is_fetched():
    # hotfix91 과 합친 판 — 판이 먼저 서고 제안은 그 뒤에 받는다 (`propPromise`).
    dlg = _fn("markupDialog")
    assert dlg.index("openModal(") < dlg.index("/markup/propose")      # 열고 나서 읽는다
    assert 'id="mk-status"' in dlg and "fillProposal" in dlg           # "읽는 중" 을 화면이 말한다


def test_late_proposal_fills_only_untouched_fields():
    dlg = _fn("markupDialog")
    # 사람이 한 번이라도 적은 칸은 표시가 남고, 제안은 표시 없는 칸만 채운다
    assert 'el.dataset.touched = "1"' in dlg and "!el.dataset.touched" in dlg
    assert 'untouched("#mk-tab")' in dlg and 'untouched("#mk-tag")' in dlg
    # 저장은 제안이 온 뒤의 값으로 출처를 가른다 (제안이 늦게 와도)
    assert "await propPromise" in dlg
    assert dlg.index("await propPromise") < dlg.index('scope_source === "DRAWING"')


def test_propose_and_add_row_run_off_the_event_loop():
    for name in ("markup_propose", "add_row"):
        m = re.search(rf"@app\.post\([^\n]*\)\ndef {name}\(", MAIN)
        assert m, f"{name} must be a plain def (threadpool), not async"
        body = MAIN[m.end(): MAIN.index("\n\n\n", m.end())]
        assert "await " not in body


def test_propose_borrows_config_under_one_lock():
    import sys
    sys.path.insert(0, str(ROOT / "app/engine"))
    from app import pipeline
    assert isinstance(pipeline._PROPOSE_LOCK, type(threading.RLock()))
    src = inspect.getsource(pipeline.propose_at)
    assert "with _PROPOSE_LOCK:" in src and src.index("with _PROPOSE_LOCK:") < src.index("with _own_config()")
    assert "with _PROPOSE_LOCK:" in inspect.getsource(pipeline._propose_page)


def test_shared_connection_reads_do_not_interleave(tmp_path):
    """스레드 6개가 같은 연결에서 읽어도 빈 행·None 칸이 없다 (잠금 안에서 행을 가져온다)."""
    from app import db
    con = db.connect(tmp_path / "t.db")
    con.execute("CREATE TABLE t (id TEXT PRIMARY KEY, v TEXT)")
    con.executemany("INSERT INTO t VALUES (?, ?)", [(f"k{i}", f"v{i}") for i in range(300)])
    con.commit()
    bad, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            r = con.execute("SELECT * FROM t WHERE id=?", ("k7",)).fetchone()
            if r is None or r["v"] != "v7":
                bad.append(r)
            if len(list(con.execute("SELECT * FROM t"))) != 300:
                bad.append("count")

    ths = [threading.Thread(target=reader) for _ in range(6)]
    [t.start() for t in ths]
    threading.Event().wait(1.5)
    stop.set()
    [t.join() for t in ths]
    assert not bad
    cur = con.execute("INSERT INTO t VALUES ('z', 'z')")
    assert cur.lastrowid                                           # 쓰기는 진짜 커서 그대로


def test_memo_panel_ignores_a_404():
    show = JS[JS.index("async function showMemo("):]
    show = show[:show.index("\n}\n")]
    assert "if (!r.ok) return;" in show
