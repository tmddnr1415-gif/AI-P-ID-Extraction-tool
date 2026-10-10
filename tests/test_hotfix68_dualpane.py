"""hotfix68 — 도면 · 목록을 새 창으로 (듀얼 모니터) · 두 창의 연동 · 가볍게.

못박는 것:
  1. `/rows` 는 바뀐 것이 없으면 같은 본문을 다시 만들지 않고(메모), gzip 을 받으면 압축본을 준다.
     편집 한 칸이면 메모가 풀린다.  `?keys=a,b` 면 그 행만 준다 (다른 창이 바뀐 행만 다시 받는다).
  2. 큰 응답은 압축된다 (GZipMiddleware) — 이미 압축된 것(PNG · zip · xlsx)과 진행 소식(SSE)은 빼고.
  3. 새 창은 `?pane=drawing|list&link=…` 로 열리고 `body.pane-drawing` · `body.pane-list` 가 한 칸만 남긴다.
     `window.open` 은 이 파일의 `open(jobId)` 에 덮여 있으므로 숨은 iframe 의 손대지 않은 open 을 쓴다.
  4. 두 창은 `postMessage` 를 **이 서버와 같은 출처**로만 보내고, 받는 쪽은 출처와 `link` 를 본다.
  5. 다른 창에 알리는 것은 저장 함수마다가 아니라 **서버에 쓰는 요청이 끝난 것**을 보고 한다 (GET 은 안 본다).
  6. 목록 창(도면이 숨은 창)은 장 그림을 받지 않는다 · 숨은 칸에서 맞춤 배율을 음수로 만들지 않는다.
  7. 목록 그리기는 행을 글 한 줄로 만들어 한 번 붓고, 칸마다 듣던 저장 · Enter · 누르기는 몸통 하나가 받는다.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(rf"(?:async )?function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def _app(tmp_path):
    import os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main


def _job(main, job="jd", n=60):
    from app import db
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,"
        "progress,message,fingerprint,project,revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'','','','A')",
        (job, "x.pdf", job, "", time.time()))
    keys = [db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no="D-1",
                       values={"type": "PI", "qty": 1, "description": f"PRESSURE INDICATOR {i} " * 4},
                       rect=[10 * i, 20, 10 * i + 5, 30])
            for i in range(n)]
    main.CON.commit()
    return job, keys


# ---------------------------------------------------------------- ① /rows 메모 · 압축 · keys
def test_rows_body_is_memoised_gzipped_and_invalidated_by_an_edit(tmp_path):
    c, main = _app(tmp_path)
    job, keys = _job(main)
    a = c.get(f"/jobs/{job}/rows?tab=ALL", headers={"Accept-Encoding": "gzip"})
    assert a.headers.get("content-encoding") == "gzip"
    rows = json.loads(a.content)                      # TestClient 가 풀어 준다
    assert len(rows) == len(keys)
    hit = main._ROWS_BODY[(job, "ALL", False)]
    assert hit["gz"] is not None and gzip.decompress(hit["gz"]) == hit["raw"]
    b = c.get(f"/jobs/{job}/rows?tab=ALL", headers={"Accept-Encoding": "gzip"})
    assert main._ROWS_BODY[(job, "ALL", False)] is hit and b.content == a.content     # 다시 만들지 않았다
    # 압축을 안 받는 요청은 맨 본문
    plain = c.get(f"/jobs/{job}/rows?tab=ALL", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in plain.headers and json.loads(plain.content) == rows
    # 편집 한 칸 → 도장이 바뀌어 다시 만든다
    r = c.patch(f"/jobs/{job}/rows/{keys[3]}", json={"field": "qty", "value": "7", "author": "홍길동"})
    assert r.status_code == 200
    d = json.loads(c.get(f"/jobs/{job}/rows?tab=ALL").content)
    assert main._ROWS_BODY[(job, "ALL", False)] is not hit
    assert next(x for x in d if x["key"] == keys[3])["values"]["qty"] == 7


def test_rows_with_keys_returns_only_those_rows_with_the_same_columns(tmp_path):
    c, main = _app(tmp_path)
    job, keys = _job(main)
    full = {r["key"]: r for r in json.loads(c.get(f"/jobs/{job}/rows?tab=ALL").content)}
    part = json.loads(c.get(f"/jobs/{job}/rows?tab=ALL&keys={keys[1]},{keys[5]}").content)
    assert sorted(r["key"] for r in part) == sorted([keys[1], keys[5]])     # 순서는 목록 순서 그대로
    for r in part:
        assert r == full[r["key"]]                    # 같은 열 · 같은 값 (review_codes · rev · edited_by · type_display)


def test_gzip_middleware_skips_already_compressed_and_event_streams():
    assert "app.add_middleware(\n    GZipMiddleware, minimum_size=2048, compresslevel=5," in MAIN
    assert "DEFAULT_EXCLUDED_CONTENT_TYPES + (" in MAIN
    assert "spreadsheetml.sheet" in MAIN
    from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES
    for t in ("image/png", "application/zip", "text/event-stream"):
        assert t in DEFAULT_EXCLUDED_CONTENT_TYPES


# ---------------------------------------------------------------- ② 새 창 · 한 칸
def test_two_pop_buttons_and_the_pane_classes_hide_one_side():
    assert len(re.findall(r'class="ghost pop-btn" data-pane="(drawing|list)"', HTML)) == 2
    assert 'data-pane="drawing"' in HTML and 'data-pane="list"' in HTML
    assert "body.pane-drawing #right, body.pane-drawing #gutter-v," in CSS
    assert "body.pane-list #left, body.pane-list #gutter-v { display: none !important; }" in CSS
    assert "body.popout #sidebar" in CSS


def test_popup_is_opened_through_an_untouched_open_not_the_shadowed_one():
    # 이 파일의 `async function open(jobId)` 가 window.open 을 덮는다 — 그대로 부르면 결과 열기가 불린다
    assert re.search(r"\nasync function open\(jobId\)", JS)
    assert "window.open(" not in JS.replace("`window.open(url)`", "")
    nat = _fn("_nativeOpen")
    assert "_openFrame.contentWindow.open.call(window, url, name, features)" in nat
    assert "_nativeOpen(url, `pid-${role}-${link}`" in _fn("popOut")


def test_messages_go_only_to_the_same_origin_and_carry_the_link():
    post = _fn("syncPost")
    assert "w.postMessage({ ...m, __pid: SYNC.link" in post and "location.origin);" in post
    i = JS.index('window.addEventListener("message"')
    seg = JS[i:i + 400]
    assert "ev.origin !== location.origin" in seg and "d.__pid !== SYNC.link" in seg
    assert "d.from === SYNC.me" in seg                  # 자기 메아리는 안 받는다


def test_only_writes_are_announced_and_keys_come_from_the_url_or_body():
    i = JS.index("(function hookFetch()")
    seg = JS[i:i + 900]
    assert 'method !== "GET" && method !== "HEAD"' in seg and "res.ok" in seg
    note = _fn("syncNoteMutation")
    assert r"rest.match(/^rows\/([^/]+)(?:\/([a-z_]+))?$/)" in note
    assert "_bodyKeys(init && init.body)" in note
    rows = _fn("syncRows")
    assert "/rows?tab=ALL&keys=" in rows and "reloadRowsKeepView()" in rows
    # 받은 창은 같은 행 객체를 제자리에서 바꾼다 (다른 곳이 쥐고 있는 참조가 그대로 산다)
    assert "Object.assign(old, r);" in rows and "buildRowTr(old, cols)" in rows


def test_receivers_do_not_echo():
    for name in ("applySel", "applyPage", "reloadRowsKeepView"):
        body = _fn(name)
        assert "SYNC.muted++" in body and "SYNC.muted--" in body, name
    assert "if (!SYNC.link || SYNC.muted) return;" in _fn("syncPost")


def test_list_window_does_not_fetch_sheet_images_and_fit_ignores_a_hidden_stage():
    sp = _fn("showPage")
    assert "S.imgStale = drawingHidden();" in sp
    assert "if (!S.imgStale) swapSheet(img," in sp
    assert "if ($(\"#stage\").clientWidth < 20) return;" in _fn("fit")
    sel = _fn("select")
    assert "!drawingHidden()" in sel                     # 목록 창에서 행을 눌러도 장을 그리지 않는다
    assert "syncSel();" in sel and "syncSel();" in _fn("deselect")


def test_side_by_side_and_auto_side_stay_off_while_split():
    assert "if (paneSplit()) return;" in _fn("autoSide")
    assert "if (on && paneSplit())" in _fn("toggleSide")


# ---------------------------------------------------------------- ③ 가볍게 — 열기 · 목록 그리기
def test_open_starts_the_independent_reads_together():
    op = _fn("_open")
    assert op.index("const rowsP = fetch(") < op.index("await Promise.all([loadLegendProfile(), loadModeBar(), loadRevision()])")
    assert "rowSideFetches(jobId)" in op and "await loadRows(rowsP, sideP);" in op
    lr = _fn("loadRows")
    assert "await Promise.all([buildScope(), loadUnjudged(), showTemplates()]);" in lr


def test_grid_is_one_html_pour_and_the_body_listens_once():
    rg = _fn("renderGrid")
    # hotfix69 — 보이는 행만 글 한 줄로 이어 한 번 붓는다
    assert "S.vlist = rows;" in rg and "paintWindow(true);" in rg
    pw = _fn("paintWindow")
    assert "for (let i = start; i < end; i++) html += rowHtml(rows[i], cols);" in pw and "body.innerHTML = html;" in pw
    rh = _fn("rowHtml")
    assert "addEventListener" not in rh and "onclick" not in rh
    assert 'data-act="report"' in rh and 'data-act="restore"' in rh and 'data-act="del-confirm"' in rh
    i = JS.index("(function bindGridBody()")
    seg = JS[i:JS.index("\n})();", i)]          # hotfix78 — 두 번 누르기가 더해져 IIFE 끝까지 본다
    for ev in ('"focusout"', '"keydown"', '"click"'):
        assert f"body.addEventListener({ev}" in seg, ev
    assert "saveEdit(r, td.dataset.col, td)" in seg
    assert "toggleMulti(r.key)" in seg and "select(r.key, true)" in seg


def test_first_screen_reads_wait_until_the_result_is_open():
    assert "afterFirstOpen(showAudit);" in JS and "afterFirstOpen(listHome);" in JS
    after = _fn("afterFirstOpen")
    assert "if (PANE.role) return;" in after             # 새 창은 첫 화면을 안 쓴다
    assert "_runAfterOpen();" in _fn("_open") and "_runAfterOpen();" in _fn("toFirstScreen")
