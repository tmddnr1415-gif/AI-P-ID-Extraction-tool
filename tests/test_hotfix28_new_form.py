"""hotfix28 — 캡션 없는 양식 · 종이가 섞인 PDF 에서도 도면번호 칸을 찾는다.

현장: QFE 93장(A3 5장 + A1 88장)이 `TitleBlockUnreadable` 로 멈췄다 — 양식이
`PROJECT DWG NO.` 캡션을 안 찍어 캡션 유도가 비었고, AL NOUF1 좌표가 그대로 쓰였다.

  ① 종이가 섞이면 **다수 크기의 장**으로 잰다 (`_form_pages`)
  ② 캡션이 없으면 **장마다 같은 자리에 되풀이되며 값이 장마다 다른** 코드 번호의
     자리가 도면번호 칸이다 (`_recurring_numbers`) — 프로젝트 번호(값이 같다)와
     오프페이지 커넥터(자리가 다르다)는 걸리지 않는다
  ③ 그 칸에서 `formats.drawing_no` 도 그대로 유도된다
합성 PDF 로 돈다 — `data/` 없이.
"""
from __future__ import annotations
import re, sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
import derive_layout as dl                 # noqa: E402
from app.engine.pidcache import load_pages, in_region   # noqa: E402

A1 = (2384.0, 1684.0)
A3 = (1191.0, 842.0)


def _new_form(path: Path, n_sheets=6, n_covers=2, caption="DWG. NO.", numbers=None,
              inline=False, title_caption="SHEET TITLE"):
    """AL NOUF1 과 다른 양식: 타이틀블록이 오른쪽 아래 상자이고 캡션이 `DWG. NO.` 다.

    각 도면 장에 (가) 도면번호를 같은 자리에 (나) 프로젝트 번호를 같은 자리에 같은 값으로
    (다) 오프페이지 커넥터 번호 둘을 장마다 다른 자리에 인쇄한다.
    """
    doc = pymupdf.open()
    for _ in range(n_covers):                       # 표지 — A3 · 번호 없음
        pg = doc.new_page(width=A3[0], height=A3[1])
        pg.insert_text(pymupdf.Point(300, 300), "COVER SHEET", fontsize=30)
    W, H = A1
    for i in range(n_sheets):
        pg = doc.new_page(width=W, height=H)
        for a, b in (((40, 40), (W - 40, 40)), ((40, H - 40), (W - 40, H - 40)),
                     ((40, 40), (40, H - 40)), ((W - 40, 40), (W - 40, H - 40))):   # 테두리 (선 넷)
            pg.draw_line(pymupdf.Point(*a), pymupdf.Point(*b), width=1.0)
        pg.draw_line(pymupdf.Point(W - 420, 40), pymupdf.Point(W - 420, H - 40), width=0.8)  # 표제란 세로 괘선
        num = (numbers[i] if numbers else f"QFE-P1-PID-{i + 1:03d}")
        x = W - 400
        if inline:                                   # `DWG NO. : XXXX` 한 줄
            pg.insert_text(pymupdf.Point(x, H - 275), caption, fontsize=9)
            pg.insert_text(pymupdf.Point(x + 90, H - 275), num, fontsize=12)
        else:
            if caption:
                pg.insert_text(pymupdf.Point(x, H - 300), caption, fontsize=9)
            pg.insert_text(pymupdf.Point(x, H - 275), num, fontsize=16)
        pg.insert_text(pymupdf.Point(x, H - 240), "PROJECT NO.", fontsize=9)
        pg.insert_text(pymupdf.Point(x, H - 215), "QFE-2026-001", fontsize=14)   # 장마다 같은 값
        if title_caption:
            pg.insert_text(pymupdf.Point(x, H - 180), title_caption, fontsize=9)
        pg.insert_text(pymupdf.Point(x, H - 155), f"FUEL GAS SYSTEM {i + 1}", fontsize=14)
        # 오프페이지 커넥터 — 같은 모양의 번호가 도면 안 **다른 자리**에
        pg.insert_text(pymupdf.Point(200 + 90 * i, 300 + 40 * i), f"QFE-P1-PID-{(i + 2) % n_sheets + 1:03d}", fontsize=10)
        pg.insert_text(pymupdf.Point(900 - 50 * i, 1200 - 30 * i), f"QFE-P1-PID-{(i + 3) % n_sheets + 1:03d}", fontsize=10)
        pg.insert_text(pymupdf.Point(300, 600), "PT", fontsize=10)
    doc.save(path); doc.close()
    return path


def test_majority_size_pages_are_the_form():
    class _P:
        def __init__(self, w, h): self.width, self.height = w, h
    pages = [_P(*A3), _P(*A1), _P(*A1), _P(*A3), _P(*A1)]
    form, sizes = dl._form_pages(pages)
    assert len(form) == 3 and all(p.width == A1[0] for p in form)
    assert sizes == {(1191.0, 842.0): 2, (2384.0, 1684.0): 3}


def test_drawing_number_cell_is_found_by_recurrence_without_a_caption(tmp_path):
    pdf = _new_form(tmp_path / "qfe.pdf", caption="", title_caption="")     # 캡션이 아예 없다
    _doc, pages = load_pages(pdf)
    lay = dl.derive(pages)
    vals = lay.values()
    assert "title_block.dwg_no_region" in vals, lay.notes
    region = tuple(vals["title_block.dwg_no_region"])
    # 도면번호는 안에, 프로젝트 번호·커넥터·제목은 밖에
    for pc in pages[2:]:
        inside = [t for r, t in pc.words if in_region(r, region)]
        assert len(inside) == 1 and inside[0].startswith("QFE-P1-PID-"), (pc.page_no, inside)
    assert "QFE-2026-001" not in [t for pc in pages for r, t in pc.words if in_region(r, region)]
    # 그 칸에서 모양도 유도된다
    pat = vals.get("formats.drawing_no")
    assert pat and re.match(pat, "QFE-P1-PID-004") and not re.match(pat, "QFE-2026-001")
    item = lay.items["title_block.dwg_no_region"]
    assert "no DWG NO. caption" in item.evidence and "6 of 6 sheets" in item.evidence
    # 종이가 섞였다는 사실이 남는다 · 크기는 다수 장의 것
    assert any("mixed page sizes" in n for n in lay.notes)
    assert vals["sheet.width_pt"] == A1[0] and vals["sheet.height_pt"] == A1[1]


def test_the_caption_path_still_wins_when_the_form_prints_the_caption(tmp_path):
    pdf = _new_form(tmp_path / "cap.pdf", caption="PROJECT DWG NO.")
    _doc, pages = load_pages(pdf)
    lay = dl.derive(pages)
    item = lay.items["title_block.dwg_no_region"]
    assert "caption" in item.evidence and "no DWG NO. caption" not in item.evidence


def test_a_number_that_never_changes_or_never_recurs_is_not_the_cell(tmp_path):
    # 모든 장이 같은 번호 → 구분이 안 되므로 칸이 아니다 (값이 장마다 달라야 한다)
    pdf = _new_form(tmp_path / "same.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
    _doc, pages = load_pages(pdf)
    lay = dl.derive(pages)
    assert "title_block.dwg_no_region" not in lay.values()
    assert any("could not be found by caption or by structure" in n for n in lay.notes)


def test_failure_message_names_the_structural_miss():
    from app import pipeline as P
    import inspect
    src = inspect.getsource(P._frame_reason)
    assert "could not be found by caption or by structure" in src and "sheet_numbers" in src
    # 제목을 한 장도 못 읽은 문서에서만 범례 머리말로 범례 장을 가른다
    body = inspect.getsource(P._analyse)
    assert 'if not any((r.get("drawing_title") or "").strip() for r in tb_rows.values()):' in body
    assert 'row["page_kind"] = "LEGEND"' in body


def _read(pages, region, codes_only=False):
    """칸 안 낱말 (파이프라인처럼 도면번호는 코드 모양 낱말만 본다 — 캡션 낱말은 칸에 있어도 무해)."""
    return [" ".join(t for r, t in sorted(pc.words, key=lambda w: (round(w[0].y0), w[0].x0))
                     if in_region(r, region) and (not codes_only or dl._code_shape(t)))
            for pc in pages[2:]]


def test_caption_vocabulary_finds_other_spellings_before_structure(tmp_path):
    """hotfix29 — `DWG. NO.` · `DRAWING NUMBER` · `DOC NO:` 는 전부 도면번호 캡션이다."""
    for cap in ("DWG. NO.", "DRAWING NUMBER", "DOC NO:", "CLIENT DRG. NO."):
        pdf = _new_form(tmp_path / f"v{abs(hash(cap))}.pdf", caption=cap)
        _doc, pages = load_pages(pdf)
        lay = dl.derive(pages)
        item = lay.items["title_block.dwg_no_region"]
        assert "caption vocabulary" in item.evidence, (cap, item.evidence)
        assert all(v.startswith("QFE-P1-PID-") for v in _read(pages, tuple(item.value), True)), cap
        assert any("captions found by vocabulary" in n and "dwg_no" in n for n in lay.notes)


def test_inline_caption_takes_the_value_on_the_same_line(tmp_path):
    pdf = _new_form(tmp_path / "inline.pdf", caption="DWG NO. :", inline=True)
    _doc, pages = load_pages(pdf)
    lay = dl.derive(pages)
    item = lay.items["title_block.dwg_no_region"]
    assert "same line" in item.evidence
    got = _read(pages, tuple(item.value))
    assert all(v.startswith("QFE-P1-PID-") for v in got) and "DWG" not in " ".join(got), got


def test_title_cell_by_vocabulary_and_by_structure(tmp_path):
    # `SHEET TITLE` 캡션 — 어휘로
    pdf = _new_form(tmp_path / "t1.pdf")
    _doc, pages = load_pages(pdf)
    lay = dl.derive(pages)
    it = lay.items["title_block.title_region"]
    assert "caption vocabulary" in it.evidence
    assert all("FUEL GAS SYSTEM" in v for v in _read(pages, tuple(it.value)))
    # 캡션 없음 — 되풀이 자리 · 값이 장마다 다름 · 가장 큰 글자
    pdf = _new_form(tmp_path / "t2.pdf", caption="", title_caption="")
    _doc, pages = load_pages(pdf)
    lay = dl.derive(pages)
    it = lay.items["title_block.title_region"]
    assert "no title caption" in it.evidence
    region = tuple(it.value)
    minh = lay.values()["title_block.title_min_height"]
    for pc in pages[2:]:
        big = [t for r, t in pc.words if in_region(r, region) and r.height >= minh]
        assert "FUEL" in big and "GAS" in big and "QFE-2026-001" not in big, (pc.page_no, big)


def test_the_exact_caption_pass_is_unchanged_for_the_reference_form():
    """1차(정확 일치)의 결과는 2차가 있어도 같다 — 기존 문서 불변의 근거."""
    lines = [(10.0, [(0.0, "PROJECT", 5.0, 8.0, 12.0, 30.0), (32.0, "DWG", 5.0, 8.0, 12.0, 45.0), (47.0, "NO.", 5.0, 8.0, 12.0, 60.0)]),
             (30.0, [(0.0, "D00P-10LBA10-M05-0001", 9.0, 26.0, 34.0, 120.0)])]
    caps = dl._caption_rows(lines)
    assert set(caps) == {"dwg_no"}
    assert dl._caption_rows_vocab(lines, caps) == {}            # 1차가 쓴 줄은 다시 쓰지 않는다
