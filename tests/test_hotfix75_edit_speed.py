"""hotfix75 — 고치는 일을 빠르게 (사용자: *"마크업과 사용자가 pid 에서 계기 선택 범위로 선택 그리고 수정시 list
변경과 같은 행위와 반영은 빨리 처리되어야지 프로그램으로서의 실효성이 생긴다"*).

못박는 것:
  1. 묶음 저장(`rows_edit`)·묶음 삭제(`rows_delete`)는 **한 행짜리와 같은 함수**(`_edit_one` · `_delete_one`)를 부른다 —
     같은 사람 값 · 같은 추출값 · 같은 편집 이력(작성자·사유) · 같은 `removed`/오검출 표시.
  2. 값을 하나라도 못 읽으면 한 행도 적지 않는다 · 없는 행은 건너뛰고 `missing` 으로 말한다.
  3. 화면은 묶음을 요청 하나로 보내고, 지우기·되살리기·행 추가 뒤에는 **그 행만** 다시 받는다 (목록 전체 아님).
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(r"(?:async )?function " + re.escape(name) + r"\(", JS)
    assert m, name
    nxt = re.search(r"\n(?:async )?function \w+\(", JS[m.end():])
    return JS[m.start(): m.end() + (nxt.start() if nxt else 4000)]


def _row(key, page, qty):
    return {"key": key, "tab": "FIELD", "page_no": page, "rect": [10, 10, 30, 40],
            "drawing_no": f"D-{page}", "type": "PIT", "qty": qty, "system": "", "valve_type": "",
            "vendor_supply": "", "scope": "SCT", "description": "", "tag_no": "",
            "needs_review": "", "annotation": "", "evidence": {"qty_basis": "1 symbol x 1"}}


def _job(tmp_path, monkeypatch):
    from app import db, main
    con = db.connect(tmp_path / "t.db")
    monkeypatch.setattr(main, "CON", con)
    db.create_job(con, "j", "pid.pdf", "sha", tmp_path / "x.pdf")
    db.store_result(con, "j", {
        "pages": [{"page_no": 6, "drawing_no": "D-6", "title": "t", "page_kind": "PID",
                   "in_scope": True, "scope_reason": "", "width": 10.0, "height": 10.0}],
        "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}}, "fingerprint": "f",
        "rows": [_row(k, 6, 2) for k in ("a", "b", "c", "d")]})
    return con, main, db


def test_bulk_edit_writes_exactly_what_patch_writes(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    asyncio.run(main.patch_row("j", "a", {"field": "scope", "value": "VENDOR", "author": "홍길동"}))
    out = asyncio.run(main.rows_edit("j", {"field": "scope", "author": "홍길동",
                                          "items": [{"key": "b", "value": "VENDOR"}, {"key": "zz", "value": "SCT"}]}))
    assert set(out["users"]) == {"b"} and out["missing"] == ["zz"]
    a, b = db.get_row(con, "j", "a"), db.get_row(con, "j", "b")
    assert a["user"] == b["user"] == {"scope": "VENDOR"}
    assert a["ai"]["scope"] == b["ai"]["scope"] == "SCT"            # 추출값 그대로
    ha, hb = db.row_edit_history(con, "j", "a"), db.row_edit_history(con, "j", "b")
    strip = lambda h: {k: v for k, v in h[-1].items() if k not in ("at", "id", "row_key", "ts", "created_at")}
    assert strip(ha) == strip(hb) and hb[-1]["author"] == "홍길동"
    assert out["review_count"] == db.review_count(con, "j")
    # 빈 값 = 도면 값으로
    asyncio.run(main.rows_edit("j", {"field": "scope", "author": "x", "items": [{"key": "b", "value": ""}]}))
    assert "scope" not in (db.get_row(con, "j", "b")["user"] or {})


def test_bulk_edit_refuses_bad_input_before_writing_anything(tmp_path, monkeypatch):
    from fastapi import HTTPException
    con, main, db = _job(tmp_path, monkeypatch)
    for body in ({"field": "qty", "items": [{"key": "a", "value": 3}, {"key": "b", "value": "x2"}]},
                 {"field": "qty", "items": [{"key": "a", "value": -1}]},
                 {"field": "evidence", "items": [{"key": "a", "value": "1"}]},
                 {"field": "scope", "items": []},
                 {"field": "scope", "items": ["a"]},
                 {"field": "scope", "items": [{"key": "a", "value": {"x": 1}}]}):
        with pytest.raises(HTTPException) as e:
            asyncio.run(main.rows_edit("j", body))
        assert e.value.status_code == 400
    assert "qty" not in (db.get_row(con, "j", "a")["user"] or {})   # 하나도 안 적었다
    with pytest.raises(HTTPException) as e:
        asyncio.run(main.rows_edit("nojob", {"field": "qty", "items": [{"key": "a", "value": 1}]}))
    assert e.value.status_code == 404


def test_bulk_delete_marks_rows_like_delete(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    one = main.delete_row("j", "a", reason="SCT 도 VENDOR 도 아님", reason_class="NOT_SUPPLY", author="홍길동")
    many = main.rows_delete("j", {"keys": ["b", "c", "zz"], "reason": "SCT 도 VENDOR 도 아님",
                                  "reason_class": "NOT_SUPPLY", "author": "홍길동", "exclude": True})
    assert set(many["rows"]) == {"b", "c"} and many["missing"] == ["zz"]
    per_row = {k: v for k, v in one.items() if k not in ("review_count", "feedback_count", "markup")}
    assert many["rows"]["b"] == {**per_row, "key": "b"}            # 한 행짜리와 같은 결과
    assert json.loads(json.dumps(db.get_row(con, "j", "b").get("reject") or {}, default=str)).get("class") in (None, "NOT_SUPPLY")
    ra, rb = db.get_row(con, "j", "a"), db.get_row(con, "j", "b")
    assert ra["removed"] and rb["removed"] and not db.get_row(con, "j", "d")["removed"]
    assert many["review_count"] == db.review_count(con, "j")
    assert many["feedback_count"] == db.feedback_count(con, "j") and "markup" in many


def test_bulk_delete_rejects_bad_input(tmp_path, monkeypatch):
    from fastapi import HTTPException
    con, main, db = _job(tmp_path, monkeypatch)
    for body in ({"keys": []}, {"keys": "a"}, {"keys": [1, 2]}, {"keys": ["a"], "reason_class": "NOPE"}):
        with pytest.raises(HTTPException) as e:
            main.rows_delete("j", body)
        assert e.value.status_code == 400
    assert not db.get_row(con, "j", "a")["removed"]


def test_screen_sends_one_request_for_a_whole_selection():
    for name in ("applyScopeToMulti", "applyQtyToRows"):
        body = _fn(name)
        assert "editRowsBulk(" in body and "for (const r of rows)" not in body, name
        assert 'method: "PATCH"' not in body, name
    bulk = _fn("editRowsBulk")
    assert "/rows_edit" in bulk and bulk.count("fetch(") == 1
    dr = _fn("deleteRows")
    assert "/rows_delete" in dr and dr.count("fetch(") == 1 and 'method: "DELETE"' not in dr


def test_after_delete_restore_add_only_those_rows_are_fetched():
    ref = _fn("refreshRows")
    assert "reloadKeys(opts.keys)" in ref
    rk = _fn("reloadKeys")
    assert "/rows?tab=ALL&keys=" in rk and "loadRows(Promise.resolve(list))" in rk
    assert "slim=1" not in rk                       # 그 행 몇 개는 온전히 받는다
    assert "refreshRows(keys.length === 1 ? keys[0] : null, { keys })" in _fn("deleteRows")
    assert "refreshRows(key, { keys: [key] })" in _fn("restoreRow")
    assert "refreshRows(out.key, { keys: [out.key] })" in _fn("createRow")
    assert "refreshRows(out.key, { toGrid: true, keys: [out.key] })" in JS


def test_markup_summary_reads_only_what_it_needs_and_says_the_same(tmp_path, monkeypatch):
    """예전 요약(분석 전체 파싱) 과 같은 답 — 사람이 더한 행 · 지운 행 · 표시만 한 행 · 장별."""
    con, main, db = _job(tmp_path, monkeypatch)
    from app import markup
    main.delete_row("j", "a", reason="x", reason_class="FALSE_POSITIVE", author="홍")
    main.delete_row("j", "b", reason="y", reason_class="FALSE_POSITIVE", author="홍", exclude=False)
    con.execute("UPDATE item SET added=1, evidence_json=? WHERE job_id='j' AND key='c'",
                (json.dumps({"markup": {"scope_source": markup.SOURCE_USER, "qty_source": "DRAWING"}}),))
    con.commit()

    def old(rows):
        out = {"added": 0, "added_with_rect": 0, "scope_user": 0, "qty_user": 0,
               "rejected": 0, "rejected_excluded": 0, "by_page": {}}
        for r in rows:
            mk = (r.get("evidence") or {}).get("markup") or {}
            pg = out["by_page"].setdefault(str(r["page_no"]), {"added": 0, "rejected": 0})
            if r["added"]:
                out["added"] += 1; pg["added"] += 1
                out["added_with_rect"] += bool(r.get("rect"))
                out["scope_user"] += mk.get("scope_source") == markup.SOURCE_USER
                out["qty_user"] += mk.get("qty_source") == markup.SOURCE_USER
            if r.get("reject") or r["removed"]:
                out["rejected"] += 1; pg["rejected"] += 1
                out["rejected_excluded"] += bool(r["removed"])
        return out
    new = markup.summary(con, "j")
    assert new == old(db.merged_rows(con, "j"))
    assert new["added"] == 1 and new["scope_user"] == 1 and new["rejected"] == 2 and new["rejected_excluded"] == 1


def test_new_rows_land_where_the_server_list_puts_them():
    rk = _fn("reloadKeys")
    assert "x.page_no < y.page_no || (x.page_no === y.page_no && x.key < y.key)" in rk
    from app import db
    import inspect
    assert 'ORDER BY page_no, key' in inspect.getsource(db.merged_rows)


def test_engine_near_reads_the_same_as_the_whole_job(tmp_path, monkeypatch):
    """행 추가가 쓰는 '그 장에서 엔진이 낸 것' — 장만 읽어도 분석 전체를 읽은 것과 같다."""
    con, main, db = _job(tmp_path, monkeypatch)
    eng = {"unjudged_symbols": [{"page_no": 6, "center": [1, 2], "word": "XX"}, {"page_no": 7, "center": [3, 4]},
                                {"page_no": 6, "word": "no centre"}],
           "applied_rules": {"layout": {"moved": [{"key": "title_block.x", "source": "DRAWING"}]}}}
    con.execute("UPDATE job SET engine_json=? WHERE id='j'", (json.dumps(eng),)); con.commit()

    def old(page_no):
        dets = []
        for r in db.merged_rows(con, "j"):
            if r.get("page_no") != page_no or not r.get("rect"):
                continue
            ev = r.get("evidence") or {}
            dets.append({"anchor": ev.get("anchor") or ev.get("tag") or "", "excel_type": r.get("type") or "",
                         "included": True, "rect": [round(float(v), 1) for v in r["rect"]],
                         "rules": list(ev.get("rules_hit") or []), "review_codes": list(ev.get("review_codes") or [])})
        e = json.loads(db.get_job(con, "j")["engine_json"])
        un = [u for u in e.get("unjudged_symbols") or [] if u.get("page_no") == page_no and u.get("center")]
        return dets, un, e["applied_rules"]["layout"]["moved"]
    for page in (6, 7, 99):
        assert main._engine_near("j", page) == old(page)
    con.execute("UPDATE job SET engine_json='{broken' WHERE id='j'"); con.commit()
    assert main._engine_near("j", 6)[1:] == ([], [])          # 깨진 기록은 빈 값 (죽지 않는다)


def test_memo_follows_edits_without_reparsing_and_matches_a_fresh_read(tmp_path, monkeypatch):
    """편집 · 지우기 · 되살리기 · 행 추가 · 묶음 뒤 메모 = 처음부터 다시 읽은 목록, 그리고 다시 파싱하지 않았다."""
    con, main, db = _job(tmp_path, monkeypatch)
    assert hasattr(con, "_lock")                      # 서버가 쓰는 연결
    for tab in ("ALL", "REVIEW", "FIELD"):
        db.merged_rows_cached(con, "j", tab)          # 데워 둔다
    calls = []
    real = db.merged_rows
    monkeypatch.setattr(db, "merged_rows", lambda *a, **k: calls.append(a) or real(*a, **k))
    asyncio.run(main.patch_row("j", "a", {"field": "qty", "value": 5, "author": "홍"}))
    main.delete_row("j", "b", reason="x", reason_class="NOT_SUPPLY", author="홍")
    main.restore_row("j", "b")
    asyncio.run(main.rows_edit("j", {"field": "scope", "author": "홍", "items": [{"key": "c", "value": "VENDOR"},
                                                                              {"key": "d", "value": "VENDOR"}]}))
    main.rows_delete("j", {"keys": ["c"], "reason_class": "FALSE_POSITIVE", "author": "홍"})
    added = asyncio.run(main.add_row("j", {"page_no": 6, "tab": "FIELD", "values": {"type": "PI"}}))["key"]
    con.execute("UPDATE item SET needs_review='x' WHERE job_id='j' AND key='d'"); con.commit()   # 메모가 모르는 쓰기
    got = {tab: db.merged_rows_cached(con, "j", tab) for tab in ("ALL", "REVIEW", "FIELD")}
    assert len(calls) == 3                            # 마지막 '모르는 쓰기' 만 전부 다시 읽게 했다 (탭 셋)
    for tab, rows in got.items():
        assert rows == real(con, "j", tab), tab
    assert added in {r["key"] for r in got["ALL"]}


def test_memo_is_not_patched_across_another_connection(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    db.merged_rows_cached(con, "j")
    other = db.connect(tmp_path / "t.db")
    with db.memo_follow(con, "j") as touched:
        db.set_user_value(con, "j", "a", "qty", 9); touched.append("a")
        other.execute("UPDATE item SET needs_review='z' WHERE job_id='j' AND key='b'"); other.commit()
    rows = db.merged_rows_cached(con, "j")
    assert rows == db.merged_rows(con, "j") and next(r for r in rows if r["key"] == "b")["needs_review"] == "z"


def test_batches_and_readers_in_parallel_never_deadlock_and_end_consistent(tmp_path, monkeypatch):
    """묶음 저장(연결 잠금 안에서 이력 쓰기가 겹친다) 과 메모 읽기가 동시에 — 서로 기다리다 멈추지 않는다."""
    import threading
    con, main, db = _job(tmp_path, monkeypatch)
    stop, errs = threading.Event(), []

    def writer():
        try:
            for i in range(40):
                asyncio.run(main.rows_edit("j", {"field": "qty", "author": "w",
                                                "items": [{"key": k, "value": i} for k in "abcd"]}))
                main.rows_delete("j", {"keys": ["a"], "author": "w"}); main.restore_row("j", "a")
        except Exception as e:                      # noqa: BLE001
            errs.append(e)
        finally:
            stop.set()

    def reader():
        while not stop.is_set():
            for tab in ("ALL", "REVIEW"):
                db.merged_rows_cached(con, "j", tab)
    ts = [threading.Thread(target=writer)] + [threading.Thread(target=reader) for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(60)
    assert not any(t.is_alive() for t in ts), "멈췄다 (교착)"
    assert not errs
    for tab in ("ALL", "REVIEW"):
        assert db.merged_rows_cached(con, "j", tab) == db.merged_rows(con, "j", tab)


def test_markup_proposal_helpers_read_the_page_and_say_the_same(tmp_path, monkeypatch):
    con, main, db = _job(tmp_path, monkeypatch)
    from app import markup
    con.execute("UPDATE item SET ai_json=json_set(ai_json, '$.tag_no', '10ABC01CP001') WHERE job_id='j' AND key='a'")
    con.execute("UPDATE item SET ai_json=json_set(ai_json, '$.tag_no', '10ABC01CT002') WHERE job_id='j' AND key='b'")
    con.commit()
    real = db.merged_rows
    calls = []
    monkeypatch.setattr(db, "merged_rows", lambda *a, **k: calls.append(a) or real(*a, **k))
    words = [{"text": "PIT 10ABC01CP009"}]
    q, sy, tg = (markup._qty_from_page(con, "j", 6), markup._system_from_page(con, "j", 6),
                 markup._tag_from_words(con, "j", words))
    assert not calls                                    # 분석 전체를 파싱하지 않았다
    assert tg["tag_no"] == "10ABC01CP009" and tg["tag_source"] == markup.SOURCE_DRAWING
    monkeypatch.setattr(db, "merged_rows_on_page", lambda c, j, p: [r for r in real(c, j) if r["page_no"] == p])
    assert (markup._qty_from_page(con, "j", 6), markup._system_from_page(con, "j", 6)) == (q, sy)
