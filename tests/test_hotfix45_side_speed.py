"""hotfix45 — 나란히 보기 · 이전/현재 전환을 가볍게.

사용자: *"이전 Rev.A, 현재 Rev.B 나란히 대조 누르면 너무 시간이 오래 걸리고 렉 걸린다."*
QFE 실측(Rev.B 2,041행): 나란히 켬 4.6초 · 14.6MB(직전 결과 `/rows?tab=ALL` 13.7MB) →
0.2초 · 1MB.  장 바꾸기 1.2~1.9초 → 0.1초 (장 그림 디스크 캐시).  이전 결과 전환 8.5초 →
3.5초 (옛 행으로 목록을 한 번 더 그리던 것 · 머리글 관찰자의 강제 레이아웃 0.9초×2 ·
한 요청에 행을 다섯 번 파싱하던 서버).

지키는 것:
  ① `/anchors` 는 안정 ID → 장·사각형만 (판정 없음 · 작다)
  ② 장 그림은 한 번 그리면 디스크에 두고 같은 바이트를 준다 · 분석을 지우면 같이 지운다 ·
     고아는 위생 감사가 센다
  ③ 행 목록 메모는 편집 한 칸(이 연결) · 다른 연결의 커밋 어느 쪽에도 묵은 값을 주지 않는다 ·
     읽기 전용 호출자만 쓰고 `/rows` 는 복사를 뜬다
  ④ 화면: 나란히는 `/rows` 를 읽지 않는다 · 스크롤 동기는 프레임에 한 번 · 읽는 중 hashchange
     는 목록을 그리지 않는다 · 머리글 재기는 그려진 뒤
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _app(tmp_path):
    import os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main


def _job(main, job="jx", pages=1):
    """done 상태의 분석 하나 — 진짜 PDF(한 장) 와 행 셋."""
    from app import db
    import pymupdf
    up = main.UPLOADS
    up.mkdir(parents=True, exist_ok=True)
    pdf = up / f"{job}_x.pdf"
    doc = pymupdf.open()
    for i in range(pages):
        pg = doc.new_page(width=200, height=120)
        pg.insert_text((20, 40), f"SHEET {i + 1}")
    doc.save(str(pdf)); doc.close()
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,"
        "progress,message,fingerprint,project,revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'','','','A')",
        (job, "x.pdf", job, str(pdf), time.time()))
    keys = [db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no="D-1",
                       values={"type": "PI", "qty": 1}, rect=[10 * i, 20, 10 * i + 5, 30])
            for i in range(3)]
    main.CON.commit()
    return job, pdf, keys


# ---------------------------------------------------------------- ① anchors
def test_anchors_are_stable_id_to_page_and_rect_only(tmp_path):
    c, main = _app(tmp_path)
    from app import db
    job, _, keys = _job(main)
    db.store_revision_result(main.CON, job, {"states": {
        keys[0]: {"id": "D-1-001", "state": "BASELINE"},
        keys[1]: {"id": "D-1-002", "state": "BASELINE"},
        keys[2]: {"id": "", "state": "BASELINE"}}, "deleted_candidates": []})
    r = c.get(f"/jobs/{job}/anchors")
    assert r.status_code == 200
    out = r.json()
    assert set(out) == {"D-1-001", "D-1-002"}          # ID 가 빈 행은 없다
    assert out["D-1-001"] == {"page_no": 1, "rect": [0, 20, 5, 30], "key": keys[0]}
    assert set(out["D-1-002"]) == {"page_no", "rect", "key"}   # evidence · values 는 싣지 않는다
    assert c.get("/jobs/nope/anchors").status_code == 404


# ---------------------------------------------------------------- ② page cache
def test_page_png_is_rendered_once_and_served_from_disk_after(tmp_path):
    c, main = _app(tmp_path)
    job, _, _ = _job(main)
    cache = main.PAGE_CACHE / job / "p1_z1.6.png"
    assert not cache.exists()
    a = c.get(f"/jobs/{job}/page/1.png?zoom=1.6")
    assert a.status_code == 200 and a.headers["content-type"].startswith("image/png")
    assert cache.is_file() and cache.read_bytes() == a.content
    # 둘째 요청은 그 파일 그대로 — 바이트가 같고 PDF 를 열지 않는다
    import pymupdf
    opened = []
    real_open = pymupdf.open
    pymupdf.open = lambda *a, **k: (opened.append(a), real_open(*a, **k))[1]
    try:
        b = c.get(f"/jobs/{job}/page/1.png?zoom=1.6")
    finally:
        pymupdf.open = real_open
    assert b.content == a.content and opened == []
    assert not list((main.PAGE_CACHE / job).glob("*.tmp"))   # 쓰다 만 파일이 남지 않는다
    # 배율이 다르면 다른 파일
    c.get(f"/jobs/{job}/page/1.png?zoom=1")
    assert (main.PAGE_CACHE / job / "p1_z1.png").is_file()


def test_deleting_the_job_removes_its_page_cache_and_orphans_are_counted(tmp_path):
    c, main = _app(tmp_path)
    from app import audit
    job, _, _ = _job(main)
    c.get(f"/jobs/{job}/page/1.png?zoom=1.6")
    assert (main.PAGE_CACHE / job).is_dir()
    # 고아 — 어느 분석도 가리키지 않는 캐시 폴더는 위생 감사가 센다
    (main.PAGE_CACHE / "ghost").mkdir()
    (main.PAGE_CACHE / "ghost" / "p1_z1.6.png").write_bytes(b"x" * 10)
    left = audit.run(main.CON, main.DATA_DIR)["leftovers"]
    assert left["orphan_page_cache"] == ["ghost"] and left["reclaimable_bytes"] >= 10
    assert any("고아 그림 캐시 1" in ln for ln in audit.summary(audit.provenance(main.CON), left))
    r = c.request("DELETE", f"/jobs/{job}", data={"confirm": job, "author": "a"})
    assert r.status_code == 200 and r.json()["page_cache_removed"] is True
    assert not (main.PAGE_CACHE / job).exists()


# ---------------------------------------------------------------- ③ rows memo
def test_rows_memo_is_reused_until_this_connection_writes(tmp_path):
    c, main = _app(tmp_path)
    from app import db
    job, _, keys = _job(main)
    a = db.merged_rows_cached(main.CON, job, "ALL")
    assert db.merged_rows_cached(main.CON, job, "ALL") is a          # 같은 목록
    assert db.merged_rows_cached(main.CON, job) is a                 # tab None == ALL
    db.set_user_value(main.CON, job, keys[0], "qty", 7)
    b = db.merged_rows_cached(main.CON, job, "ALL")
    assert b is not a and next(r for r in b if r["key"] == keys[0])["values"]["qty"] == 7
    # 화면이 읽는 길도 새 값이다 — 편집 직후 `/rows`
    rows = {r["key"]: r for r in c.get(f"/jobs/{job}/rows?tab=ALL").json()}
    assert rows[keys[0]]["values"]["qty"] == 7 and "review_codes" in rows[keys[0]]


def test_rows_memo_notices_commits_from_another_connection(tmp_path):
    c, main = _app(tmp_path)
    from app import db
    job, _, keys = _job(main)
    a = db.merged_rows_cached(main.CON, job, "ALL")
    other = db.connect(main.DB_PATH)
    db.set_user_value(other, job, keys[1], "qty", 9)
    other.close()
    b = db.merged_rows_cached(main.CON, job, "ALL")
    assert b is not a and next(r for r in b if r["key"] == keys[1])["values"]["qty"] == 9


def test_rows_endpoint_copies_and_the_memo_is_not_mutated_by_it(tmp_path):
    c, main = _app(tmp_path)
    from app import db
    job, _, _ = _job(main)
    c.get(f"/jobs/{job}/rows?tab=ALL")
    cached = db.merged_rows_cached(main.CON, job, "ALL")
    assert all("review_codes" not in r and "rev" not in r for r in cached)
    # 소스 — `/rows` 는 복사를 뜨고, 메모를 쓰는 다른 곳은 읽기 전용 엔드포인트뿐
    # hotfix68 — 행을 만드는 일은 `_rows_payload` 로 갈라졌다 (`/rows` 가 본문을 메모하고 `?keys=` 로 몇 행만 낸다)
    body = MAIN[MAIN.index("def _rows_payload("):]
    body = body[:body.index("\n@app.")]
    assert "src = db.merged_rows_cached(CON, job_id, tab, slim=slim)" in body      # hotfix80 — 목록용은 덜어낸 행
    assert "[dict(r) for r in src if keys is None or r[\"key\"] in keys]" in body
    users = [m.start() for m in re.finditer(r"merged_rows_cached\(", MAIN)]
    assert len(users) >= 4
    for pos in users:
        head = MAIN[max(0, pos - 2500):pos]
        name = re.findall(r"\ndef (\w+)\(", head)[-1]
        assert name in {"rows", "_rows_payload", "_rows_body", "job_review", "axis_override_map", "_multiplier_targets"}, name   # hotfix80 — 본문 조립


# ---------------------------------------------------------------- ④ screen
def _fn(name):
    i = JS.index(name)
    return JS[i:JS.index("\n}\n", i) + 3]


def test_side_by_side_reads_anchors_not_the_full_rows():
    body = _fn("async function cmpLoad(jobId)")
    calls = re.findall(r"fetch\(`([^`]*)`", body)          # 주석이 아니라 실제 요청만
    assert calls == ["/jobs/${jobId}/pages", "/jobs/${jobId}/anchors"]


def test_scroll_sync_writes_once_per_frame_and_only_when_different():
    body = _fn("function cmpSyncScroll(from)")
    assert "requestAnimationFrame" in body and "S._cmpRaf" in body
    assert "if (dst.scrollLeft !== src.scrollLeft)" in body


def test_hashchange_during_open_does_not_render_the_old_rows():
    i = JS.index('window.addEventListener("hashchange"')
    body = JS[i:i + 1200]
    assert "if (S.loading) return;" in body


def test_header_measure_runs_after_paint_not_inside_the_render():
    i = JS.index("// hotfix26 — 목록 첫 두 열 고정")
    body = JS[i:i + 1400]
    assert "requestAnimationFrame(() => requestAnimationFrame(" in body
    assert "new MutationObserver(later)" in body and "new MutationObserver(measure)" not in body


def test_stale_page_loads_do_not_draw_over_the_newer_one():
    body = _fn("async function cmpShow()")
    assert "S._cmpSeq" in body and "if (seq !== S._cmpSeq) return;" in body
    assert "cmpPrefetch(data, page)" in body
    pf = _fn("function cmpPrefetch(data, page)")
    assert "setTimeout(" in body or "setTimeout(" in pf      # 쉬는 동안만 미리 받는다
