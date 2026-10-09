"""hotfix69 — PDF-XChange 처럼 가볍게 (시뮬레이션 spike/perf_sim.py 로 다섯 번 재며 고친 것).

못박는 것:
  1. 장 그림을 미리 그린다 — 별도 프로세스가 지금 장부터 앞뒤로, 이미 있는 그림은 건너뛴다.
  2. 사람이 연 장도 서버 **밖** 일꾼이 그린다 (그리는 동안 서버가 다른 요청을 받는다) · 없는 장은 False.
  3. `/rows?slim=1` 은 고른 행에만 쓰는 근거 칸 셋을 빼고 `_slim` 을 붙인다 · `?keys=` 는 온전히 준다.
  4. 행 메모는 동시에 불려도 한 번만 파싱한다 (결과 열기 때 네 요청이 같은 0.4초를 동시에 하던 것).
  5. 화면: 목록은 보이는 행만 그리고 · 장 그림은 풀어 놓은 뒤 걸고 · 목록 폭은 크기가 바뀔 때만 재고 ·
     근거 패널은 고른 행만 온전히 받는다.
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(rf"(?:async )?function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def _pdf(path: Path, pages=3):
    import pymupdf
    doc = pymupdf.open()
    for i in range(pages):
        pg = doc.new_page(width=200, height=120)
        pg.insert_text((20, 40), f"SHEET {i + 1}")
    doc.save(str(path)); doc.close()
    return path


# ---------------------------------------------------------------- ① · ② 장 그림
def test_warm_order_starts_at_the_page_in_view_and_widens():
    from app import page_warm
    assert page_warm.order([1, 2, 3, 4, 5, 6], 3) == [3, 4, 2, 5, 1, 6]
    assert page_warm.order([5, 1, 3], 9) == [1, 3, 5]          # 모르는 장이면 순서대로


def test_warm_draws_every_missing_page_in_another_process(tmp_path, monkeypatch):
    from app import page_warm
    monkeypatch.setenv("PID_PAGE_WARM", "1")
    pdf = _pdf(tmp_path / "x.pdf", 3)
    root = tmp_path / "cache"
    pre = page_warm.cache_file(root, "j1", 2, 1.6)
    pre.parent.mkdir(parents=True)
    pre.write_bytes(b"already")                                  # 이미 있는 장은 건너뛴다
    assert page_warm.start(pdf, root, "j1", [1, 2, 3], 2) is True
    assert page_warm.running_job() == "j1"
    deadline = time.time() + 60
    while time.time() < deadline and not all(page_warm.cache_file(root, "j1", n, 1.6).is_file() for n in (1, 3)):
        time.sleep(0.2)
    assert page_warm.cache_file(root, "j1", 1, 1.6).read_bytes()[:4] == b"\x89PNG"
    assert page_warm.cache_file(root, "j1", 3, 1.6).read_bytes()[:4] == b"\x89PNG"
    assert pre.read_bytes() == b"already"
    assert page_warm.start(pdf, root, "j1", [1, 2, 3], 2) is False      # 할 일이 없으면 안 띄운다
    page_warm.stop()


def test_warm_is_off_by_switch(tmp_path, monkeypatch):
    from app import page_warm
    monkeypatch.setenv("PID_PAGE_WARM", "0")
    assert page_warm.start(_pdf(tmp_path / "x.pdf", 1), tmp_path / "c", "j", [1], 1) is False


def test_render_now_draws_outside_the_server_and_says_no_such_page(tmp_path, monkeypatch):
    from app import page_warm
    monkeypatch.setenv("PID_RENDER_POOL", "1")
    pdf = _pdf(tmp_path / "x.pdf", 2)
    out = tmp_path / "c" / "j" / "p2_z1.6.png"
    assert page_warm.render_now(pdf, out, 2, 1.6) is True
    assert out.read_bytes()[:4] == b"\x89PNG"
    assert page_warm.render_now(pdf, tmp_path / "c" / "j" / "p9_z1.6.png", 9, 1.6) is False
    # 무거운 읽기도 같은 일꾼이 한다 (모듈 맨 위 함수)
    from app import pdf_facts
    assert isinstance(page_warm.call(pdf_facts.read, (str(pdf), {})), dict)
    monkeypatch.setenv("PID_RENDER_POOL", "0")
    assert page_warm.render_now(pdf, out, 2, 1.6) is None                  # 꺼져 있으면 부른 쪽이 그린다
    with pytest.raises(RuntimeError):
        page_warm.call(pdf_facts.read, (str(pdf), {}))


def test_server_uses_the_worker_and_falls_back_in_process():
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    seg = main[main.index("def page_png("):main.index("_DXF_RENDER_LOCK")]
    assert seg.index("page_warm.render_now(") < seg.index("import pymupdf")
    assert "page_warm.call(pdf_facts.read," in main and "except RuntimeError:" in main
    assert "_warm_pages(job_id, out)" in main and "page_warm.prime()" in main
    conf = (ROOT / "conftest.py").read_text(encoding="utf-8")
    assert 'os.environ.setdefault("PID_PAGE_WARM", "0")' in conf
    assert 'os.environ.setdefault("PID_RENDER_POOL", "0")' in conf


# ---------------------------------------------------------------- ③ slim · ④ 메모 잠금
def _app(tmp_path):
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main


def test_slim_rows_drop_selected_row_fields_and_keys_gives_them_back(tmp_path):
    c, main = _app(tmp_path)
    from app import db
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,progress,message,fingerprint,project,revision)"
        " VALUES ('js','x.pdf','js','',?,'done',1.0,'','','','A')", (time.time(),))
    ev = {"candidates": [{"text": "A"}] * 50, "trace": {"run": [1, 2]}, "axis": {"axis": "④"}, "qty_basis": "1 symbol x 2"}
    k = db.add_row(main.CON, "js", page_no=1, tab="FIELD", drawing_no="D", values={"type": "PI", "qty": 2},
                   rect=[1, 2, 3, 4], evidence=ev)
    main.CON.commit()
    slim = json.loads(c.get("/jobs/js/rows?tab=ALL&slim=1").content)[0]
    assert slim["_slim"] == 1
    for f in main.SLIM_DROP:
        assert f not in slim["evidence"], f
    assert slim["evidence"]["qty_basis"] == "1 symbol x 2"                 # 목록이 쓰는 근거는 남는다
    full = json.loads(c.get(f"/jobs/js/rows?tab=ALL&keys={k}").content)[0]
    assert "_slim" not in full and full["evidence"]["candidates"] and full["evidence"]["axis"]["axis"] == "④"
    plain = json.loads(c.get("/jobs/js/rows?tab=ALL").content)[0]
    assert "_slim" not in plain and "trace" in plain["evidence"]           # 다른 호출자는 예전 그대로


def test_row_memo_parses_once_under_concurrent_readers(tmp_path, monkeypatch):
    from app import db
    con = db.connect(tmp_path / "m.db")
    calls = []
    real = db.merged_rows

    def slow(con_, job_id, tab=None):
        calls.append(job_id)
        time.sleep(0.3)
        return real(con_, job_id, tab)
    monkeypatch.setattr(db, "merged_rows", slow)
    db._ROWS_MEMO.clear()
    got = []
    ts = [threading.Thread(target=lambda: got.append(db.merged_rows_cached(con, "j"))) for _ in range(4)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert len(calls) == 1 and len(got) == 4 and all(g is got[0] for g in got)


# ---------------------------------------------------------------- ⑤ 화면
def test_grid_paints_only_the_rows_in_view():
    pw = _fn("paintWindow")
    assert "let html = _vpad(start * h, n);" in pw and "_vpad((rows.length - end) * h, n) + VROW.measure" in pw
    assert "body.contains(document.activeElement)" in pw                    # 타자 중에는 다시 그리지 않는다
    rv = _fn("revealRow")
    assert "S.vlist" in rv and "paintWindow(true)" in rv
    assert "#grid tr.vmeasure { visibility: collapse; }" in CSS
    i = JS.index("(function bindGridScroll()")
    assert 'gw.addEventListener("scroll", later, { passive: true })' in JS[i:i + 600]
    # 화면 밖 행으로 가야 하는 곳은 굴려 그린다 (고르기 · 추가한 행 · 화살표)
    assert "const tr = revealRow(key);" in _fn("select")
    assert "revealRow(selectKey)" in _fn("refreshRows")


def test_sheet_is_decoded_before_it_is_shown_and_neighbours_are_prefetched():
    sw = _fn("swapSheet")
    assert ("pre.decode().then(go, go)" in sw or "pre.decode().then(go, failed)" in sw) and "seq === _sheetSeq" in sw
    pf = _fn("prefetchNeighbours")
    assert "requestIdleCallback" in pf and "im.decode()" in pf
    assert "prefetchNeighbours(page);" in _fn("showPage")


def test_list_width_is_observed_not_measured_on_every_click():
    lh = _fn("listHidden")
    assert "getBoundingClientRect" in lh and "_rightW === null" in lh      # 처음 한 번만
    assert "new ResizeObserver(" in JS


def test_open_reads_slim_rows_and_the_evidence_panel_fills_the_selected_row():
    assert "/rows?tab=ALL&slim=1" in _fn("open")
    ef = _fn("ensureFull")
    assert "rows?tab=ALL&keys=${encodeURIComponent(row.key)}" in ef and "delete row._slim" in ef
    se = JS[JS.index("function showEvidence(row) {"):JS.index("function showEvidence(row) {") + 400]
    assert "if (row && row._slim)" in se and "ensureFull(row)" in se
