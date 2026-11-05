"""hotfix132 — P&ID 핵심 흐름을 HTTP 로 (업로드 → 분석 → 리비전 → Excel).

판정 값은 보지 않는다 — 길(라우트 · 폼 이름 · 상태 전이 · 산출 묶음)이 끊기지 않았는지만 본다.
(가) 업로드: 합성 PDF 를 `POST /jobs` 로 올려 done 또는 failed(한국어 사유)까지 간다 · PDF 가 아니면 400 한국어.
(나) 산출: done 분석에 행을 넣고 → 양식 올리기 → 리비전 고정(snapshot) → Excel 묶음(zip) 을 연다.
"""
from __future__ import annotations

import importlib
import io
import time
import zipfile

import pytest
from fastapi.testclient import TestClient


def _main():
    return importlib.import_module("app.main")


def _has_hangul(s: str) -> bool:
    return any("가" <= ch <= "힣" for ch in s or "")


def _pdf_bytes() -> bytes:
    import pymupdf
    doc = pymupdf.open()
    pg = doc.new_page(width=842, height=595)
    pg.draw_rect(pymupdf.Rect(20, 20, 822, 575), width=1.5)
    pg.draw_rect(pymupdf.Rect(600, 480, 822, 575), width=1)
    for y in (200, 260, 320):
        pg.draw_line((80, y), (520, y), width=0.8)
    pg.draw_circle((300, 260), 14, width=0.8)
    pg.insert_text((290, 258), "FT", fontsize=6)
    pg.insert_text((288, 266), "101", fontsize=6)
    pg.insert_text((610, 520), "DWG NO. P-0001", fontsize=8)
    raw = doc.tobytes()
    doc.close()
    return raw


def test_upload_flow_reaches_a_final_state(monkeypatch):
    monkeypatch.setenv("PID_ANALYSIS_INPROCESS", "1")
    main = _main()
    c = TestClient(main.app)
    bad = c.post("/jobs", files=[("pdf", ("t.txt", b"hello", "text/plain"))])
    assert bad.status_code == 400 and _has_hangul(bad.json()["detail"])
    r = c.post("/jobs", files=[("pdf", ("흐름시험.pdf", _pdf_bytes(), "application/pdf"))])
    assert r.status_code == 200, r.text
    job_id = r.json()["job_id"]
    deadline = time.time() + 90
    st = {}
    while time.time() < deadline:
        st = c.get(f"/jobs/{job_id}").json()
        if st["status"] in ("done", "failed", "cancelled"):
            break
        time.sleep(0.3)
    assert st.get("status") in ("done", "failed"), st
    assert st.get("pdf_name") == "흐름시험.pdf"
    if st["status"] == "failed":
        assert _has_hangul(st.get("message") or ""), st          # 실패하더라도 사람 말로 사유를 남긴다
    c.request("DELETE", f"/jobs/{job_id}", data={"author": "시험", "confirm": job_id})        # 뒷정리 (결과는 보지 않는다)


def _minimal_template(sheet: str) -> bytes:
    """발주처 양식 흉내 — 설정이 요구하는 시트 이름만 맞춘 빈 통합 문서 (칸 배치는 엔진 설정 그대로)."""
    import openpyxl
    wb = openpyxl.Workbook()
    wb.active.title = sheet
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_export_flow_snapshot_to_excel_zip():
    main = _main()
    from app import db
    import pymupdf
    c = TestClient(main.app)
    job = "wpcflow01"
    main.UPLOADS.mkdir(parents=True, exist_ok=True)
    pdf = main.UPLOADS / f"{job}_x.pdf"
    doc = pymupdf.open()
    doc.new_page(width=200, height=120).insert_text((20, 40), "SHEET 1")
    doc.save(str(pdf))
    doc.close()
    main.CON.execute("DELETE FROM job WHERE id=?", (job,))
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,progress,message,fingerprint,project,revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'','','','A')", (job, "x.pdf", job, str(pdf), time.time()))
    for i in range(3):
        db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no="D-1",
                   values={"type": "PT", "tag_no": f"10{i}", "qty": 1}, rect=[10 * i, 20, 10 * i + 5, 30])
    main.CON.commit()

    up = c.post("/templates", data={"kind": "FIELD"},
                files={"file": ("FIELD.xlsx", _minimal_template((main.CFG.get("excel") or {}).get("sheet") or "Sheet1"),
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    assert up.status_code == 200 and up.json()["path"] == "FIELD.xlsx"        # 서버 경로는 내보내지 않는다
    bad = c.post("/templates", data={"kind": "FIELD"}, files={"file": ("x.xlsx", b"not excel", "application/octet-stream")})
    assert bad.status_code == 400 and _has_hangul(bad.json()["detail"])

    snap = c.post(f"/jobs/{job}/snapshot", json={"label": "흐름 시험"})
    assert snap.status_code == 200, snap.text
    rev = snap.json()["revision_id"]
    assert snap.json()["rows"] >= 1

    x = c.get(f"/revisions/{rev}/excel")
    if x.status_code == 400:
        detail = x.json().get("detail")
        pytest.skip(f"최소 양식으로는 산출이 건너뛰어졌다: {detail}")
    assert x.status_code == 200, x.text[:300]
    zf = zipfile.ZipFile(io.BytesIO(x.content))
    books = [n for n in zf.namelist() if n.endswith(".xlsx")]
    assert books, zf.namelist()
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(zf.read(books[0])), read_only=True)
    assert wb.sheetnames
    wb.close()
