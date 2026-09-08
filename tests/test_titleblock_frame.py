"""타이틀블록 칸이 그 도면에 맞지 않을 때 (21회차).

증상: 다른 회사의 새 프로젝트 PDF 를 올리면 17분 뒤에
`이 PDF 를 분석하지 못했습니다. 사유를 특정하지 못했습니다.` 한 줄만 남았다.
회사 PC 터미널에서 확보한 원본 예외는

    ValueError: zero-size array to reduction operation minimum which has no
    identity        (extract_titleblocks.py `_ink_mask`, `a.min()`)

이고, 스택은 `build_glyph_library` -> `segment_chars` -> `_ink_mask` 의
**이력 행 갈래**를 가리켰다.

여기 있는 시험은 그 조건을 **합성 PDF 로 재현**한다 - `data/` 없이 돈다.
"""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app.engine import extract_titleblocks as tb          # noqa: E402
from app.engine.pidcache import load_pages                 # noqa: E402

LAY = tb.LAYOUT


def _sheet(path: Path, width=2384.0, height=1684.0, rule_ys=(1210.0, 1240.0)):
    """한 장짜리 PDF. `rule_ys` 자리에 이력 표의 가로 괘선을 긋는다.

    괘선 조건은 `history_rows` 가 쓰는 것 그대로다 - 높이 1pt 미만 ·
    x0 < hist_rule_x0_max · x1 > hist_rule_x1_min · y 가 hist_rule_y 안.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    for y in rule_ys:
        page.draw_line(pymupdf.Point(LAY.hist_rule_x0_max - 5, y),
                       pymupdf.Point(LAY.hist_rule_x1_min + 5, y), width=0.4)
    page.insert_text(pymupdf.Point(100, 100), "X", fontsize=40)
    doc.save(path)
    doc.close()
    return path


# --------------------------------------------------------------------------
# (b) 0픽셀에 .min() 을 부르지 않는다 - 이것은 무조건이다
# --------------------------------------------------------------------------
def _degenerate_clips(page):
    """0픽셀이 나오는 다섯 모양.  전부 같은 ValueError 를 내던 자리다."""
    w, h = page.rect.width, page.rect.height
    inset = LAY.hist_row_inset
    return {
        "종이 오른쪽 밖": pymupdf.Rect(w + 10, 100, w + 110, 200),
        "종이 아래 밖": pymupdf.Rect(100, h + 10, 200, h + 110),
        "높이 0": pymupdf.Rect(1971, 1300.0, 1988, 1300.0),
        "높이 음수": pymupdf.Rect(1971, 1301.2, 1988, 1300.8),
        # 이력 행이 2*inset 보다 얇으면 안쪽 여백을 뺀 순간 뒤집힌다.
        "이력 행 2.0pt": pymupdf.Rect(1971, 1300 + inset, 1988, 1302 - inset),
    }


def test_a_zero_pixel_clip_returns_none_instead_of_raising(tmp_path):
    doc = pymupdf.open(_sheet(tmp_path / "a.pdf"))
    page = doc[0]
    for name, clip in _degenerate_clips(page).items():
        pm = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(LAY.zoom, LAY.zoom),
                             colorspace=pymupdf.csGRAY, alpha=False)
        a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width)
        assert a.size == 0, f"{name}: 0픽셀이어야 이 시험이 뜻이 있다"
        with pytest.raises(ValueError):          # 고치기 전에는 이렇게 죽었다
            a.min()
        assert tb._ink_mask(page, clip, LAY) is None, name
        assert tb.segment_chars(page, clip, LAY) == [], name
    doc.close()


def test_a_normal_cell_still_reads(tmp_path):
    """막은 것이 0픽셀뿐이라는 확인 - 잉크가 있는 칸은 그대로 읽힌다."""
    doc = pymupdf.open(_sheet(tmp_path / "b.pdf"))
    mask = tb._ink_mask(doc[0], pymupdf.Rect(90, 60, 130, 110), LAY)
    assert mask is not None and int(mask.sum()) >= LAY.min_ink_px
    doc.close()


def test_the_guard_does_not_write_a_sentence():
    """한 칸이 비는 것은 정상이므로 `_ink_mask` 는 사유를 말하지 않는다.

    여기서 문장을 쓰면 그것이 곧 조용한 폴백이 된다 - 문서 전체가 안 읽히는
    경우만 시끄럽게 멈춰야 하고, 그 판단은 파이프라인이 한다.
    """
    src = (ROOT / "app/engine/extract_titleblocks.py").read_text(encoding="utf-8")
    body = src.split("def _ink_mask(")[1].split("\ndef ")[0]
    code = "\n".join(ln for ln in body.splitlines()
                     if not ln.lstrip().startswith("#") and '"""' not in ln)
    assert "raise" not in code
    assert "TitleBlockUnreadable" not in code


# --------------------------------------------------------------------------
# 문서 전체가 안 읽히면 시끄럽게 멈춘다
# --------------------------------------------------------------------------
def test_frame_report_states_facts_and_not_sentences(tmp_path):
    """`frame_report` 는 사실만 낸다 - 화면 문장은 저장하지 않는다 (15회차)."""
    doc, pages = load_pages(_sheet(tmp_path / "small.pdf", width=1191.0,
                                   height=842.0, rule_ys=()))
    fr = tb.frame_report(pages, LAY)
    doc.close()
    assert fr["pages"] == 1
    assert fr["page_sizes"] == [{"size": [1191.0, 842.0], "pages": 1}]
    # A3 한 장에는 A1 양식의 네 칸이 전부 종이 밖이다.
    for name, cell in fr["cells"].items():
        assert cell["off_page"] == 1, name
        assert cell["off_page_pages"] == [1], name
    assert fr["thin_history_rows"] == []
    flat = repr(fr)
    assert "습니다" not in flat and "합니다" not in flat


def test_frame_report_counts_thin_history_rows(tmp_path):
    """페이지 크기와 무관한 갈래 - 이력 행이 안쪽 여백보다 얇은 경우."""
    thin = 2 * LAY.hist_row_inset - 0.4
    doc, pages = load_pages(_sheet(tmp_path / "thin.pdf",
                                   rule_ys=(1210.0, 1210.0 + thin)))
    fr = tb.frame_report(pages, LAY)
    doc.close()
    assert [t["page_no"] for t in fr["thin_history_rows"]] == [1]
    # 그 얇은 행을 실제로 읽어도 죽지 않는다.
    doc, pages = load_pages(tmp_path / "thin.pdf")
    assert tb.build_glyph_library(pages, LAY) is not None
    doc.close()


def test_the_pipeline_stops_with_a_reason_when_no_sheet_is_read():
    """검사는 파이프라인이 직접 하고 문장도 거기서 쓴다 (`LegendUnavailable` 과 같은 자리)."""
    src = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    assert "class TitleBlockUnreadable(RuntimeError):" in src

    # ★ 검사는 **한 자리**다.  이른 검사(쪽 크기만 보고 곧장 끊기)를 넣었다가
    # 스스로 뒤집었다 — `tb.LAYOUT` 의 네 칸은 상수가 아니라 `_fit_layout` 이
    # 그 도면에서 유도한다 (SADARA 실측 7개).  유도 **전**의 칸으로 자르면
    # 될 분석을 못 하게 만든다.
    sites = [i for i in range(len(src))
             if src.startswith("raise TitleBlockUnreadable(", i)]
    assert len(sites) == 1, sites
    fit = src.index("layout = _fit_layout(pages)")
    lib = src.index("tb.build_glyph_library(")
    targets = src.index("targets = [pc for pc in pages")
    # 칸이 유도된 뒤에 서야 하고, 글리프로만 읽히는 REV 뒤에 서야 하고,
    # `targets` 가 비어 조용히 성공하기 전에 서야 한다.
    assert fit < lib < sites[0] < targets
    reason = src[src.index("def _frame_reason("):][:2400]
    assert "title_block" in reason
    # 잰 값인가 설정값인가에 따라 사람이 할 일이 다르므로 문장이 갈린다.
    assert 'title_block.dwg_no_region" in moved' in reason
    assert "if layout is None" in reason        # 모르면 그 문장을 안 쓴다


def test_the_title_block_cells_are_derived_but_the_history_table_is_not():
    """★ 이 갈림이 21회차의 핵심이다.

    `derive_layout` 은 도면번호 · 제목 · REV · SHEET 칸을 **그 도면에서 유도**
    한다 (SADARA 실측 7개).  그러나 **이력 표 기하는 유도하지 않는다** —
    `hist_rule_*` · `hist_rev_col` · `hist_row_inset` 은 AL NOUF1 상수 그대로다.

    그래서 다른 회사 양식에서 `history_rows` 는 **그 표가 아닌 선**을 읽고,
    그 사이 간격이 `2 x hist_row_inset` 보다 좁으면 0픽셀 clip 이 나온다.
    TC2 가 죽은 자리가 정확히 거기다.
    """
    src = (ROOT / "app/engine/derive_layout.py").read_text(encoding="utf-8")
    derived = {k for k in
               ("dwg_no_region", "title_region", "project_name_region",
                "rev_box", "sheet_box")
               if f"title_block.{k}" in src or f'"{k}"' in src}
    assert "dwg_no_region" in derived and "rev_box" in derived
    for never in ("hist_rule_x0_max", "hist_rule_x1_min", "hist_rule_y",
                  "hist_rev_col", "hist_date_col", "hist_row_inset"):
        assert f"title_block.{never}" not in src, never

    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert "pipeline.TitleBlockUnreadable" in main
    # `_failure_reason` (알 수 없는 실패용 일반 문구)을 거치지 않는다.
    branch = main.split("pipeline.TitleBlockUnreadable")[1].split("except Exception")[0]
    code = "\n".join(ln for ln in branch.splitlines()
                     if not ln.lstrip().startswith("#"))
    assert "_failure_reason" not in code
    assert "str(exc)" in code                  # 파이프라인이 쓴 문장을 그대로 쓴다


# --------------------------------------------------------------------------
# 문서 사이로 새지 않는다
# --------------------------------------------------------------------------
def test_history_rows_do_not_leak_between_documents(tmp_path):
    """전역 캐시가 `page_no` 하나로 키를 삼아 두 번째 문서가 첫 문서 값을 받았다.

    실측(21회차): SADARA 9장을 혼자 읽으면 이력 행 0행인데, 같은 프로세스에서
    AL NOUF1 을 먼저 읽으면 9장 전부가 AL NOUF1 의 7행을 받았다.
    """
    a = _sheet(tmp_path / "doc_a.pdf", rule_ys=(1210.0, 1240.0, 1270.0))
    b = _sheet(tmp_path / "doc_b.pdf", rule_ys=())

    d1, p1 = load_pages(a)
    rows_a = tb.history_rows(p1[0], LAY)
    d2, p2 = load_pages(b)
    rows_b = tb.history_rows(p2[0], LAY)
    d1.close(); d2.close()

    assert p1[0].page_no == p2[0].page_no == 1      # 같은 키로 부딪히던 자리
    assert len(rows_a) == 2 and rows_b == []

    src = (ROOT / "app/engine/extract_titleblocks.py").read_text(encoding="utf-8")
    assert "_HIST_ROWS" not in src


def test_history_rows_are_still_cached_per_page(tmp_path):
    """캐시를 없앤 것이 아니라 자리를 옮긴 것이다 - 두 번 부르면 같은 객체."""
    doc, pages = load_pages(_sheet(tmp_path / "c.pdf", rule_ys=(1210.0, 1240.0)))
    first = tb.history_rows(pages[0], LAY)
    assert tb.history_rows(pages[0], LAY) is first
    doc.close()


def test_the_whole_pipeline_stops_instead_of_returning_zero_rows(tmp_path):
    """실제로 돌려 본다 - 예전에는 여기서 죽거나 행 0개로 조용히 성공했다.

    A3 세 장짜리 합성 PDF.  A1 양식의 타이틀블록 네 칸이 전부 종이 밖이라
    `page_kind` 가 한 장도 PID 가 되지 않는다.
    """
    from app import pipeline

    doc = pymupdf.open()
    for i in range(3):
        pg = doc.new_page(width=1191.0, height=842.0)
        pg.insert_text(pymupdf.Point(80, 80), f"SHEET {i + 1}", fontsize=18)
        pg.draw_line(pymupdf.Point(100, 400), pymupdf.Point(900, 400), width=0.5)
    path = tmp_path / "a3_no_titleblock.pdf"
    doc.save(path)
    doc.close()

    with pytest.raises(pipeline.TitleBlockUnreadable) as err:
        pipeline.analyse(path)
    msg = str(err.value)
    assert "3장" in msg                      # 몇 장을 봤는지
    assert "1191.0x842.0pt" in msg           # 이 문서의 쪽 크기
    assert "[1950.0, 1560.0, 2384.0, 1600.0]" in msg   # 어느 자리를 보고 있었는지
    assert "title_block" in msg              # 무엇을 하면 되는지
    # 이 합성 PDF 에는 재는 규칙이 찾는 캡션이 없으므로 설정값 갈래여야 한다.
    assert "재지 못해" in msg
