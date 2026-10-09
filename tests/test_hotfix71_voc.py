"""hotfix71 — VOC: 부서원이 남긴 오류·요청이 운영 폴더의 함에 쌓이고, 반영하면 다시 반영되지 않는다."""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _voc():
    from app import voc
    return voc


# ---------------------------------------------------------------- 저장 · 읽기
def test_write_makes_one_folder_per_voc_and_refuses_empty_reason(tmp_path):
    voc = _voc()
    rec = voc.write({"category": "MISSING", "source": "MARKUP_ADD", "reason": "PIT 를 못 읽음",
                     "author": "홍길동", "context": {"job_id": "j1", "page_no": 6}},
                    crop_png=b"\x89PNG fake", root=tmp_path)
    d = tmp_path / "inbox" / rec["id"]
    assert voc.ID_RE.match(rec["id"]) and (d / "voc.json").is_file() and (d / "crop.png").is_file()
    back = json.loads((d / "voc.json").read_text(encoding="utf-8"))
    assert back["reason"] == "PIT 를 못 읽음" and back["category_label"].startswith("㉡")
    assert back["has_crop"] is True and back["author"] == "홍길동"
    for bad in ({"category": "MISSING", "reason": "  "}, {"category": "NOPE", "reason": "x"},
                {"category": "UI", "reason": "x", "source": "NOPE"}):
        with pytest.raises(ValueError):
            voc.write(bad, root=tmp_path)
    assert [p.name for p in (tmp_path / "inbox").iterdir()] == [rec["id"]]   # 실패는 흔적이 없다


def test_half_written_and_foreign_folders_are_ignored(tmp_path):
    voc = _voc()
    a = voc.write({"category": "UI", "reason": "느림"}, root=tmp_path)
    ib = tmp_path / "inbox"
    (ib / ".tmp-VOC-20260101-000000-abcdef").mkdir()
    (ib / "notes").mkdir()
    (ib / "VOC-20260101-000000-123456").mkdir()             # voc.json 없음
    assert list(voc.scan([ib])) == [a["id"]]


def test_same_id_in_two_inboxes_counts_once(tmp_path):
    voc = _voc()
    ops, dev = tmp_path / "PID" / "voc", tmp_path / "PID_dev" / "voc"
    a = voc.write({"category": "QTY", "reason": "x2 이어야 함"}, root=ops)
    (dev / "inbox").mkdir(parents=True)
    import shutil
    shutil.copytree(ops / "inbox" / a["id"], dev / "inbox" / a["id"])       # 복사해 와도
    items = voc.scan([ops / "inbox", dev / "inbox"])
    assert list(items) == [a["id"]] and len(items[a["id"]]["_also"]) == 1


# ---------------------------------------------------------------- 장부 — 중복 반영 방지
def test_resolve_once_then_never_again(tmp_path):
    voc = _voc()
    root = tmp_path / "PID" / "voc"
    a = voc.write({"category": "SCOPE", "reason": "별표 있는데 SCT"}, root=root)
    b = voc.write({"category": "UI", "reason": "버튼이 작음"}, root=root)
    ledger = tmp_path / "PID_dev" / "voc" / "ledger.json"
    items = voc.scan([root / "inbox"])
    assert [r["id"] for r in voc.pending(items, voc.load_ledger(ledger))] == [a["id"], b["id"]]
    done = voc.mark(items, [a["id"]], status="RESOLVED", by="Claude Code (회사)",
                    release="hotfix72", note="mark_rects 에 태그 버블", ledger_file=ledger)
    assert done == [(a["id"], "RESOLVED 표시")]
    assert (root / "inbox" / a["id"] / "resolution.json").is_file()   # 운영 화면이 '반영됨' 을 읽는다
    items = voc.scan([root / "inbox"])
    L = voc.load_ledger(ledger)
    assert [r["id"] for r in voc.pending(items, L)] == [b["id"]]
    # 두 번째 반영 시도는 건드리지 않는다
    again = voc.mark(items, [a["id"]], status="RESOLVED", by="다른 사람", release="hotfix73",
                     ledger_file=ledger)
    assert "이미 처리됨" in again[0][1]
    assert voc.load_ledger(ledger)["entries"][a["id"]]["release"] == "hotfix72"
    # 장부가 없어도(새 개발 폴더) inbox 의 표시가 막는다
    assert [r["id"] for r in voc.pending(items, voc.load_ledger(tmp_path / "none.json"))] == [b["id"]]
    # 장부만 있어도(표시를 못 쓴 운영 폴더) 막는다
    (root / "inbox" / a["id"] / "resolution.json").unlink()
    items = voc.scan([root / "inbox"])
    assert [r["id"] for r in voc.pending(items, voc.load_ledger(ledger))] == [b["id"]]
    with pytest.raises(ValueError):
        voc.mark(items, [b["id"]], status="DUPLICATE", by="x", ledger_file=ledger)   # --of 없음
    with pytest.raises(ValueError):
        voc.mark(items, [b["id"]], status="RESOLVED", by=" ", ledger_file=ledger)    # 누가 없음


def test_public_state_says_whether_the_fix_is_on_this_server(tmp_path):
    voc = _voc()
    a = voc.write({"category": "UI", "reason": "x"}, root=tmp_path)
    items = voc.scan([tmp_path / "inbox"])
    assert voc.public(items[a["id"]], None, None)["state"] == "OPEN"
    voc.mark(items, [a["id"]], status="RESOLVED", by="c", release="hotfix72",
             ledger_file=tmp_path / "ledger.json")
    rec = voc.scan([tmp_path / "inbox"])[a["id"]]
    assert "다음 업데이트" in voc.public(rec, None, {"name": "hotfix71"})["state_label"]
    assert "이 서버에 적용됨" in voc.public(rec, None, {"name": "hotfix72"})["state_label"]


# ---------------------------------------------------------------- 회사 Claude Code 의 도구
def test_cli_lists_resolves_and_skips_resolved(tmp_path):
    voc = _voc()
    ops = tmp_path / "PID" / "voc"
    a = voc.write({"category": "MISSING", "reason": "AIT 못 읽음",
                   "context": {"pdf_name": "x.pdf", "page_no": 3}}, root=ops)
    ledger = tmp_path / "ledger.json"
    run = lambda *args: subprocess.run(  # noqa: E731
        [sys.executable, str(ROOT / "spike" / "voc.py"), "--inbox", str(ops / "inbox"),
         "--ledger", str(ledger), *args], capture_output=True, text=True, encoding="utf-8",
        env=dict(os.environ, PYTHONUTF8="1"))
    out = run("list")
    assert a["id"] in out.stdout and "미반영 1건" in out.stdout
    out = run("brief", "--out", str(tmp_path / "brief.md"))
    assert "AIT 못 읽음" in (tmp_path / "brief.md").read_text(encoding="utf-8")
    out = run("resolve", a["id"], "--by", "Claude Code", "--release", "hotfix72", "--note", "앵커")
    assert out.returncode == 0 and "RESOLVED" in out.stdout
    assert "반영할 VOC 가 없습니다" in run("list").stdout
    out = run("resolve", a["id"], "--by", "Claude Code", "--release", "hotfix73")
    assert "이미 처리됨" in out.stdout
    assert json.loads(ledger.read_text(encoding="utf-8"))["entries"][a["id"]]["release"] == "hotfix72"


# ---------------------------------------------------------------- 서버
def _app(tmp_path):
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    os.environ.pop("PID_VOC_DIR", None)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main
    return TestClient(main.app), main


def _job(main, job="jv"):
    from app import db
    import pymupdf
    main.UPLOADS.mkdir(parents=True, exist_ok=True)
    pdf = main.UPLOADS / f"{job}_x.pdf"
    doc = pymupdf.open()
    pg = doc.new_page(width=300, height=200)
    pg.insert_text((40, 60), "PIT")
    doc.save(str(pdf)); doc.close()
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,"
        "progress,message,fingerprint,project,revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'','fp','QFE','B')",
        (job, "x.pdf", job, str(pdf), time.time()))
    key = db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no="D-1",
                     values={"type": "PIT", "qty": 1}, rect=[35, 45, 70, 65])
    main.CON.commit()
    return job, key


def test_api_writes_under_the_data_dir_with_context_and_crop(tmp_path):
    c, main = _app(tmp_path)
    from app import voc
    assert voc.voc_root() == tmp_path / "voc"                      # 시험은 저장소의 voc/ 에 안 쓴다
    job, key = _job(main)
    r = c.post("/voc", json={"job_id": job, "source": "MARKUP_REJECT", "category": "FALSE_POSITIVE",
                             "reason": "배관 주석을 계기로 읽음", "author": "홍길동", "row_keys": [key]})
    assert r.status_code == 200, r.text
    vid = r.json()["id"]
    rec = json.loads((tmp_path / "voc" / "inbox" / vid / "voc.json").read_text(encoding="utf-8"))
    ctx = rec["context"]
    assert (ctx["job_id"], ctx["project"], ctx["revision"], ctx["page_no"], ctx["drawing_no"]) == \
        (job, "QFE", "B", 1, "D-1")
    assert ctx["pdf_path"].endswith("_x.pdf") and "build" in ctx["server"]
    assert rec["rows"][0]["identity"]["row_key"] == key and rec["rect"] == [35.0, 45.0, 70.0, 65.0]
    assert r.json()["has_crop"] and c.get(f"/voc/{vid}/crop.png").status_code == 200
    # 일반 VOC — 분석 없이도
    g = c.post("/voc", json={"category": "SLOW", "reason": "장 넘기기가 느림"})
    assert g.status_code == 200 and not g.json()["has_crop"]
    assert c.post("/voc", json={"category": "SLOW", "reason": ""}).status_code == 400
    assert c.post("/voc", json={"job_id": "nope", "category": "UI", "reason": "x"}).status_code == 400
    lst = c.get("/voc").json()
    assert lst["counts"] == {"total": 2, "open": 2} and {i["id"] for i in lst["items"]} >= {vid}
    assert [i["id"] for i in c.get(f"/voc?job_id={job}").json()["items"]] == [vid]
    assert c.get("/voc/../../etc/crop.png").status_code == 404


def test_error_report_also_lands_in_the_voc_inbox(tmp_path):
    c, main = _app(tmp_path)
    job, key = _job(main, "jr")
    r = c.post(f"/jobs/{job}/reports", json={"what": "SCOPE", "detail": "별표 있음", "row_key": key,
                                             "author": "김철수"})
    assert r.status_code == 200 and r.json()["voc_id"]
    rec = json.loads((tmp_path / "voc" / "inbox" / r.json()["voc_id"] / "voc.json")
                     .read_text(encoding="utf-8"))
    assert (rec["source"], rec["category"], rec["author"], rec["report_id"]) == \
        ("ROW_REPORT", "SCOPE", "김철수", r.json()["id"])


# ---------------------------------------------------------------- 화면
def test_every_entrance_goes_through_vocsend():
    for fn in ("async function markupDialog(", "function rejectDialog("):
        body = JS[JS.index(fn):][:9000]
        assert "vocCheckHtml(" in body and "vocReasonOk(" in body and "vocSend(" in body, fn
    assert JS.count('fetch("/voc", { method: "POST"') == 1              # 쓰는 길은 하나
    assert 'author: currentAuthor(), screen: vocScreen()' in JS          # 신고도 이름 · 화면 상태를 싣는다
    for bid in ('id="voc-btn"', 'id="home-voc"', 'id="prog-voc"'):
        assert bid in HTML
    assert 'vocDialog({ jobId, source: "ANALYSIS_FAILED"' in JS


def test_voc_folder_is_never_committed_or_packed():
    gi = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "\nvoc/\n" in gi
    s = (ROOT / "app/voc.py").read_text(encoding="utf-8")
    assert 'paths._SRC_ROOT / "voc"' in s and "paths.data_dir() / \"voc\"" in s
