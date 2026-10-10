"""hotfix80 — 목록을 가볍게: 서버는 표(item)를 안 건드린 쓰기에 행 메모를 안 풀고 · 목록용 행은 SQL 이 근거를 덜어낸 뒤
파싱하고 · `/rows` 본문은 행마다 직렬화한 글자를 잇는다.  화면은 검색을 한 번만 거르고 손이 멈춘 뒤 세우며 · 목록을
굴릴 때 새로 보이는 행만 넣고 뺀다 (브라우저 대조는 `spike/ui_audit_hotfix80.py` · `spike/perf_ab.py`).

답이 같은지를 여기서 맞댄다 — 덜어낸 행 = 온전한 행에서 뺀 것 · 본문 = 통째로 직렬화한 것.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(r"(?:async )?function " + re.escape(name) + r"\(", JS)
    assert m, name
    nxt = re.search(r"\n(?:async )?function \w+\(", JS[m.end():])
    return JS[m.start(): m.end() + (nxt.start() if nxt else 4000)]


def _row(key, page, qty, extra=None):
    ev = {"qty_basis": "1 symbol x 1", "candidates": [{"a": 1}], "trace": {"dead_ends": [1]}, "axis": {"x": 1},
          "tag_rect": [1, 2, 3, 4], "review_codes": []}
    ev.update(extra or {})
    return {"key": key, "tab": "FIELD", "page_no": page, "rect": [10, 10, 30, 40],
            "drawing_no": f"D-{page}", "type": "PIT", "qty": qty, "system": "", "valve_type": "",
            "vendor_supply": "", "scope": "SCT", "description": "", "tag_no": "",
            "needs_review": "", "annotation": "", "evidence": ev}


def _job(tmp_path, monkeypatch):
    from app import db, main
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    main._ROWS_BODY.clear()
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", {
        "pages": [{"page_no": 6, "drawing_no": "D-6", "title": "t", "page_kind": "PID",
                   "in_scope": True, "scope_reason": "", "width": 10.0, "height": 10.0}],
        "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [_row(k, 6, 2) for k in ("a", "b", "c", "d")]})
    return con, main, db


def _report(db, con, key):
    db.add_report(con, "j", next(iter(db.REPORT_KINDS)), next(iter(db.REPORT_WHAT)), "메모", row_key=key)


# ── 서버: 어느 표를 건드렸는지 센다 ─────────────────────────────────────────
def test_connection_counts_writes_per_table(tmp_path):
    from app import db
    con = db.connect(tmp_path / "w.db")
    before = dict(con.writes)
    con.execute("INSERT INTO review_state (job_id, row_key, code, state, note, updated_at) VALUES ('j','a','X','CONFIRMED','',0)")
    con.execute("UPDATE review_state SET note='n' WHERE job_id='j'")
    con.execute("DELETE FROM review_state WHERE job_id='j'")
    con.execute("SELECT count(*) FROM item").fetchone()                 # 읽기는 안 센다
    assert con.writes["review_state"] - before.get("review_state", 0) == 3
    assert con.writes["item"] == before.get("item", 0)
    s_item = db._db_stamp(con, ("item",))
    con.execute("INSERT INTO review_state (job_id, row_key, code, state, note, updated_at) VALUES ('j','a','X','CONFIRMED','',0)")
    assert db._db_stamp(con, ("item",)) == s_item                       # item 도장은 그대로
    assert db._db_stamp(con, ("item", "review_state")) != s_item        # 그 표를 넣으면 움직인다
    assert db._db_stamp(con)[1][0] == con.total_changes                 # 표를 안 주면 예전 도장 (hotfix45 호출자)


def test_unknown_statements_move_every_stamp(tmp_path):
    from app import db
    con = db.connect(tmp_path / "w.db")
    s = db._db_stamp(con, ("item",))
    con.execute("CREATE TABLE IF NOT EXISTS zz (a INTEGER)")
    assert db._db_stamp(con, ("item",)) != s


# ── 서버: 덜어낸 행 = 온전한 행에서 뺀 것 ─────────────────────────────────
def test_slim_rows_equal_slim_copy_of_full_rows(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    full = db.merged_rows(con, "j")
    slim = db.merged_rows(con, "j", slim=True)
    assert slim == [db.slim_copy(r) for r in full]
    assert all(not any(k in r["evidence"] for k in db.SLIM_DROP) for r in slim)
    assert all("tag_rect" in r["evidence"] and "qty_basis" in r["evidence"] for r in slim)
    assert main.SLIM_DROP == db.SLIM_DROP                                 # 덜어내는 칸의 정의는 한 곳
    assert "json_remove(evidence_json" in db._SLIM_SQL


def test_row_memo_survives_writes_outside_the_item_table(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    a = db.merged_rows_cached(con, "j", "ALL", slim=True)
    db.set_review_state(con, "j", "a", "ROW_DELETED", "CONFIRMED", "")   # 검토 상태 — item 밖
    _report(db, con, "a")                                                  # 신고 — item 밖
    assert db.merged_rows_cached(con, "j", "ALL", slim=True) is a          # 메모 그대로
    with db.memo_follow(con, "j") as keys:                                 # item 쓰기는 그 행만 바뀐다
        db.set_user_value(con, "j", "b", "qty", 9); keys.append("b")
    b = db.merged_rows_cached(con, "j", "ALL", slim=True)
    assert b is not a
    nb = next(r for r in b if r["key"] == "b")
    assert nb["values"]["qty"] == 9 and "candidates" not in nb["evidence"]   # 덜어낸 메모에는 덜어낸 행
    assert [r for r in b if r["key"] != "b"] == [r for r in a if r["key"] != "b"]
    assert all(x is y for x, y in zip([r for r in b if r["key"] != "b"], [r for r in a if r["key"] != "b"]))  # 같은 객체


def test_slim_and_full_memos_are_separate_entries(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    s = db.merged_rows_cached(con, "j", "ALL", slim=True)
    f = db.merged_rows_cached(con, "j", "ALL")
    assert s is not f and "candidates" in f[0]["evidence"] and "candidates" not in s[0]["evidence"]
    assert db.merged_rows_cached(con, "j", "ALL", slim=True) is s


# ── 서버: /rows 본문 ────────────────────────────────────────────────────────
def _body(main, slim):
    return main.rows("j", "ALL", "", 1 if slim else 0, None).body


def test_rows_body_equals_whole_serialisation_and_reuses_row_strings(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    body = _body(main, True)
    pay = [main._slim_row(x) for x in main._rows_payload("j", "ALL", None, slim=True)]
    assert body == json.dumps(pay, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    parts0 = dict(main._ROWS_BODY[("j", "ALL", True)]["parts"])
    # 검토 상태 한 칸 — 그 행만 다시 직렬화하고 나머지 글자는 그대로 잇는다
    db.set_review_state(con, "j", "a", "ROW_DELETED", "CONFIRMED", "")
    body2 = _body(main, True)
    parts1 = main._ROWS_BODY[("j", "ALL", True)]["parts"]
    assert body2 != body and json.loads(body2)[0]["review_state"]["ROW_DELETED"]["state"] == "CONFIRMED"
    assert parts1["a"][2] != parts0["a"][2]
    assert all(parts1[k][2] is parts0[k][2] for k in ("b", "c", "d"))
    pay = [main._slim_row(x) for x in main._rows_payload("j", "ALL", None, slim=True)]
    assert body2 == json.dumps(pay, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    # 신고(report) 는 본문이 읽는 표가 아니다 — 본문 객체 그대로
    hit = main._ROWS_BODY[("j", "ALL", True)]
    _report(db, con, "a")
    _body(main, True)
    assert main._ROWS_BODY[("j", "ALL", True)] is hit
    # 온전한 본문(slim=0)도 같은 규칙
    full = _body(main, False)
    assert full == json.dumps(main._rows_payload("j", "ALL", None), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert "candidates" in json.loads(full)[0]["evidence"]


def test_rows_body_tables_and_callers():
    from app import main
    assert main.ROWS_BODY_TABLES == ("item", "review_state", "revision_state", "feedback")
    # 읽기 전용 호출자는 덜어낸 행을 받는다 (온전한 근거를 쓰는 곳은 `?keys=` 뿐)
    for call in re.findall(r"db\.merged_rows_cached\([^)]*\)", MAIN):
        assert "slim=" in call, call


def test_startup_warmer_is_read_only_and_switchable():
    body = MAIN[MAIN.index("def _warm_recent_rows("):]
    body = body[:body.index("\n\n\n")]
    assert 'os.environ.get("PID_ROWS_WARM", "1") == "0"' in body
    assert "_rows_body_cached(" in body and "INSERT" not in body and "UPDATE" not in body and "DELETE" not in body
    assert 'name="rows-warm"' in MAIN
    assert "with _ROWS_BODY_LOCK:" in MAIN[MAIN.index("def _rows_body_cached("):MAIN.index("def _rows_body_cached(") + 600]


# ── 화면 ───────────────────────────────────────────────────────────────────
def test_grid_filters_once_per_render_and_search_waits_for_the_hand_to_stop():
    rg = _fn("renderGrid")
    assert "updateEmptyNote(rows.length)" in rg and rg.count("visibleRows()") == 1
    assert 'const n = typeof nVisible === "number" ? nVisible : visibleRows().length;' in _fn("updateEmptyNote")
    i = JS.index('$req("#filter").addEventListener("input"')
    handler = JS[i:i + 400]
    assert "clearTimeout(_filterTimer)" in handler and "FILTER_DEBOUNCE_MS" in handler and "renderGrid()" in handler
    assert re.search(r"const FILTER_DEBOUNCE_MS = \d+;", JS)


def test_grid_scroll_inserts_only_the_newly_visible_rows():
    pw = _fn("paintWindow")
    assert "body.children.length === (prevE - prevS) + hadTop + hadBot + 1" in pw   # 기대와 다르면 통째로
    assert 'top.insertAdjacentHTML("afterend", add)' in pw and '(bot || measure).insertAdjacentHTML("beforebegin", add)' in pw
    assert "else if (top) top.remove();" in pw and "else if (bot) bot.remove();" in pw   # 빈 줄은 0 이 되면 뺀다
    assert "firstRow().remove()" in pw and "lastRow().remove()" in pw
    assert "let html = _vpad(start * h, n);" in pw                       # 통째 그리기는 그대로 (hotfix69 시험)
    assert "px > 0 ?" in _fn("_vpad")                                     # 맨 위가 빈 줄이면 `#body tr` 이 그 줄을 집는다 (UI 시험)


def test_column_widths_come_from_every_row_and_are_measured_once():
    rg = _fn("renderGrid")
    assert "_measureRowHtml(all, cols)" in rg and "VROW.measureOf !== S.rows" in rg
    assert "_gradeLabel(b).length - _gradeLabel(a).length" in _fn("_measureRowHtml")   # 배지는 글자가 가장 긴 등급으로


# ── 편의: 저장 상태 · Ctrl+F ───────────────────────────────────────────────
def test_save_state_is_read_off_the_write_requests_in_one_place():
    hook = JS[JS.index("(function hookFetch()"):JS.index("(function hookFetch()") + 2000]
    assert 'saveState("saving")' in hook and 'saveState(res && res.ok ? "saved" : "failed")' in hook
    assert "SAVE_SKIP_RE.test(u)" in hook                                  # 미리 읽기 · 업로드 · 취소는 저장이 아니다
    assert JS.count("saveState(") == 4                                     # hookFetch 셋 + 정의 — 저장 함수마다 따로 적지 않는다
    assert 'id="save-state"' in HTML
    body = _fn("saveState")
    assert "저장 중…" in body and "저장 실패" in body and "저장됨" in body
    assert re.search(r"SAVE_SKIP_RE = /.*propose.*upload.*cancel", JS)


def test_ctrl_f_goes_to_the_search_box_only_on_the_result_screen():
    i = JS.index("hotfix80 — Ctrl+F")
    h = JS[i:i + 700]
    assert 'ev.key !== "f" && ev.key !== "F" && ev.key !== "ㄹ"' in h
    assert "if (!f || !S.job || !f.offsetParent) return;" in h              # 첫 화면 · 숨긴 목록 창에서는 브라우저 찾기 그대로
    assert "f.focus(); f.select();" in h
    i = JS.index("const SHORTCUTS = [")
    assert "Ctrl + F" in JS[i:JS.index("];", i)]


# ── 자: perf_sim 은 분석 id 가 아니면 멈춘다 (저장소를 지운 그 줄) ───────────
def test_perf_sim_refuses_to_delete_outside_the_data_dir():
    src = (ROOT / "spike/perf_sim.py").read_text(encoding="utf-8")
    assert 're.fullmatch(r"[0-9a-f]{6,}", JOB)' in src
    assert "data.resolve() not in _cache.parents" in src
    ab = (ROOT / "spike/perf_ab.py").read_text(encoding="utf-8")
    assert "from perf_sim import" not in ab and "import perf_sim" not in ab   # import 하면 그 argv 로 모듈이 돈다
