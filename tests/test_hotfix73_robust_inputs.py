"""hotfix73 — 비정상 입력이 원인을 말하며 멈춘다 (`spike/hostile_inputs.py` 가 실제 업로드 경로로 잰 것).

못박는 것:
  1. 업로드에서 막는다 — 암호 걸린 PDF · 열리지 않는 PDF · 쪽이 0 인(잘린) PDF 는 줄에 들어가지 않고 400 과
     원인 문장.  예전에는 "손상되었을 수 있습니다" · "쪽이 하나도 없습니다" 로 분석 하나를 차지했다.
  2. 디스크 이름은 어느 운영체제에서나 쓸 수 있다 (한글 200자 → 500 이었다) · 화면 이름은 원래 그대로.
  3. 글자층이 한 장에도 없으면 `NoTextLayer` 로 곧장 멈추고 스캔인지 획 글자인지 말한다 (예전: 4분 뒤 좌표 문장).
  4. 선이 한 장에도 없는 문서는 "P&ID 가 아닌 문서" 라고 말한다.
  5. 한글 파일 이름의 내려받기 헤더가 500 을 내지 않는다.
"""
from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest

from app import analysis_proc, pipeline
from app import main

ROOT = Path(__file__).resolve().parent.parent


def _pdf_bytes(build) -> bytes:
    d = pymupdf.open()
    build(d)
    return d.tobytes()


def test_display_and_disk_names():
    assert main._display_name("../../evil.pdf") == "evil.pdf"
    assert main._display_name("..\\..\\evil.pdf") == "evil.pdf"
    assert main._display_name("tab\tname.pdf") == "tab name.pdf"
    assert main._safe_name('a:b*c?"<>|.pdf') == "a_b_c_.pdf"
    assert main._safe_name(" spaced .pdf") == "spaced.pdf"
    assert main._safe_name("x.pdf.") == "x.pdf"
    long = main._safe_name("가" * 200 + ".pdf")
    assert long.endswith(".pdf") and len(long.encode("utf-8")) <= main._NAME_BYTES
    # 금지 글자가 하나도 남지 않는다
    for nm in ['a:b*c?"<>|.pdf', "..\\x\\y.pdf", "\x00\x1fz.pdf"]:
        assert not any(ch in main._safe_name(nm) for ch in '<>:"/\\|?*\x00\x1f')


def test_upload_check_names_the_real_cause(tmp_path):
    ok = _pdf_bytes(lambda d: d.new_page())
    assert main._pdf_problem(ok) == ""
    d = pymupdf.open(); d.new_page()
    enc = tmp_path / "enc.pdf"
    d.save(enc, encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="u", owner_pw="o")
    assert "암호" in main._pdf_problem(enc.read_bytes())
    # 소유자 암호만(권한) 걸린 PDF 는 열린다 — 막지 않는다
    own = tmp_path / "own.pdf"
    d.save(own, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="o", permissions=0)
    assert main._pdf_problem(own.read_bytes()) == ""
    assert "열 수 없습니다" in main._pdf_problem(b"%PDF-1.7\n" + bytes(range(256)) * 50)
    big = _pdf_bytes(lambda d: [d.new_page().insert_text((72, 72), "x" * 50) for _ in range(30)])
    cut = main._pdf_problem(big[: len(big) // 3])
    assert cut == "" or "손상" in cut or "쪽" in cut


def test_upload_rejects_before_queueing_and_keeps_the_display_name():
    src = main.create_job.__code__
    body = Path(main.__file__).read_text(encoding="utf-8")
    fn = body[body.index("async def create_job("):body.index("def _probe_or_none(")]
    assert fn.index("_pdf_problem(raw)") < fn.index("db.create_job(")       # 줄·기록 전에 막는다
    assert "_safe_name(name)" in fn and "_display_name(f.filename)" in fn
    assert src is not None


def test_empty_and_multiple_non_dxf_files_get_korean_reasons():
    with pytest.raises(main.HTTPException) as e:
        main._pack_input([("a.pdf", b"")])
    assert "빈 파일" in e.value.detail
    with pytest.raises(main.HTTPException) as e:
        main._pack_input([("a.pdf", b"%PDF-1"), ("b.pdf", b"%PDF-1")])
    assert "하나만" in e.value.detail


def test_attachment_header_is_latin1_safe():
    h = main._attachment("changes_리비전B_vs_Rev.A.xlsx")
    h.encode("latin-1")                                   # 예외가 나면 실패
    assert "filename*=UTF-8''" in h


def _write(tmp_path, name, build):
    p = tmp_path / name
    d = pymupdf.open(); build(d); d.save(p)
    return p


def test_scan_stops_at_once_with_the_scan_sentence(tmp_path):
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 30), False)
    pix.clear_with(200)
    def build(d):
        for _ in range(2):
            pg = d.new_page(width=1191, height=842)
            pg.insert_image(pg.rect, pixmap=pix)
    p = _write(tmp_path, "scan.pdf", build)
    with pytest.raises(pipeline.NoTextLayer) as e:
        pipeline.analyse(p)
    assert "스캔" in str(e.value)


def test_outlined_text_says_strokes(tmp_path):
    def build(d):
        pg = d.new_page(width=1191, height=842)
        pg.draw_line((10, 10), (500, 500)); pg.draw_rect(pymupdf.Rect(50, 50, 200, 120))
    p = _write(tmp_path, "strokes.pdf", build)
    with pytest.raises(pipeline.NoTextLayer) as e:
        pipeline.analyse(p)
    assert "획" in str(e.value)


def test_a_document_without_lines_is_named_as_not_a_drawing(tmp_path):
    def build(d):
        for i in range(2):
            d.new_page().insert_text((72, 72), f"Meeting minutes {i}")
    p = _write(tmp_path, "a4.pdf", build)
    with pytest.raises(pipeline.TitleBlockUnreadable) as e:
        pipeline.analyse(p)
    assert "P&ID 도면이 아닌" in str(e.value)


def test_child_process_keeps_the_new_failure_kind():
    assert "NoTextLayer" in analysis_proc._KNOWN
    w = Path(main.__file__).read_text(encoding="utf-8")
    assert "pipeline.NoTextLayer) as exc:" in w
    # 글자가 한 장이라도 있으면 걸지 않는다 — 검사는 '전부 비었을 때' 뿐
    src = Path(pipeline.__file__).read_text(encoding="utf-8")
    assert "if pages and not any(pc.words for pc in pages):" in src
