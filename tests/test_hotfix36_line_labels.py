"""hotfix36 — 배관 라인 번호 깃발 라벨 (QFE p46 · p10 실측 모양).

  ① 닫힌 사각형 안의 코드 + 그 아래 줄 + 평행한 배관 런 = 라인 라벨.  조각으로
     나뉘어 인쇄된 글자(`12`·`LBB`·`50`)는 글자 높이의 0.15배 안의 틈이면 잇는다.
  ② 세로 배관의 깃발(글자가 90° 돈 것)도 같은 규칙으로 읽힌다.
  ③ 표의 칸은 라벨이 아니다 — 둘째 줄이 또 사각형 안이면 깃발이 아니다.
  ④ 어느 모양이 라인 번호인지는 두 장 이상에서 되풀이되는 것으로 정한다.
  ⑤ 계기가 탭한 런 위의 라벨 중 가장 가까운 것이 그 행의 Line No. 이고, 지문 밖이다.
  ⑥ 파이프라인은 판정이 쓰는 **같은 런**을 넘긴다 (두 벌 금지) · 열은 Type·Tag 옆.
"""
from __future__ import annotations

import ast
import pathlib
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
import pidcache                                   # noqa: E402
import line_labels as LL                          # noqa: E402
from app import db                                # noqa: E402

H = 8.0  # 글자 높이


def _rect_lines(page, r):
    """사각형을 선분 넷으로 — 도면이 그리는 방식이고 `pc.segments()` 가 보는 것은 `l` 항목뿐이다."""
    page.draw_line((r.x0, r.y0), (r.x1, r.y0), width=0.5)
    page.draw_line((r.x1, r.y0), (r.x1, r.y1), width=0.5)
    page.draw_line((r.x1, r.y1), (r.x0, r.y1), width=0.5)
    page.draw_line((r.x0, r.y1), (r.x0, r.y0), width=0.5)


def _flag(page, x, y, system, line, spec, vertical=False):
    """깃발 하나 — 닫힌 사각형(system) · 아래 줄(line) · 깃대 · 배관 런 · 건너편 글줄(spec).
    QFE 와 같이 글자를 조각으로 나눠 찍는다 (`12`·`LBB`·`50`)."""
    if not vertical:
        box = pymupdf.Rect(x, y, x + 42, y + 12)
        _rect_lines(page, box)
        # 조각 셋: 틈 0.3pt (0.04h) — 낱말 사이(≥0.24h)보다 훨씬 좁다
        cx = x + 3
        for piece in (system[:2], system[2:5], system[5:]):
            page.insert_text((cx, y + 9.5), piece, fontsize=H)
            cx += pymupdf.get_text_length(piece, fontsize=H) + 0.3
        page.insert_text((x + 4, y + 24), line, fontsize=H)
        pole_y = y + 30
        page.draw_line((x, box.y1), (x, pole_y), width=0.5)        # 깃대
        page.draw_line((x - 80, pole_y), (x + 300, pole_y), width=0.5)   # 배관 런
        page.insert_text((x + 4, pole_y + 11), spec, fontsize=H)
        return box, ("H", pole_y, x - 80, x + 300)
    box = pymupdf.Rect(x, y, x + 12, y + 42)
    _rect_lines(page, box)
    page.insert_text((x + 9.5, y + 39), system, fontsize=H, rotate=90)
    page.insert_text((x + 24, y + 39), line, fontsize=H, rotate=90)
    pole_x = x + 30
    page.draw_line((box.x1, box.y1), (pole_x, box.y1), width=0.5)
    page.draw_line((pole_x, y - 80), (pole_x, y + 300), width=0.5)
    page.insert_text((pole_x + 11, y + 39), spec, fontsize=H, rotate=90)
    return box, ("V", pole_x, y - 80, y + 300)


def _table(page, x, y, texts):
    """표 — 칸마다 닫힌 사각형, 칸 안에 코드."""
    for i, t in enumerate(texts):
        r = pymupdf.Rect(x, y + i * 14, x + 60, y + (i + 1) * 14)
        _rect_lines(page, r)
        page.insert_text((x + 3, y + i * 14 + 10), t, fontsize=H)


def _doc(tmp_path):
    doc = pymupdf.open()
    runs = {}
    for pno in (1, 2):
        page = doc.new_page(width=800, height=600)
        _b, r1 = _flag(page, 120, 100, "12LBB50", "BR010", "DN800H LBB1")
        _b, r2 = _flag(page, 500, 100, "12LBB50", "BR011", "DN800H LBB1")   # 같은 런 위 둘째 깃발
        _b, r3 = _flag(page, 150, 300, "11MBP01", "BR534", "DN25P MBP4", vertical=True)
        _table(page, 600, 400, ["AA203", "AA204", "AA205"])                # 표 — 라벨 아님
        # 계기 버블 (PIT) — 깃발 BR010 의 런에 인출선으로 탭
        _rect_lines(page, pymupdf.Rect(300, 40, 340, 60))
        page.draw_line((320, 60), (320, 130), width=0.5)
        runs[pno] = (r1, r2, r3)
    path = tmp_path / "flags.pdf"; doc.save(path); doc.close()
    _d, pages = pidcache.load_pages(str(path))
    return pages, runs


def _labels(pc, runs):
    return LL.find_labels(pc, list(runs), 0.8)


def test_horizontal_flag_is_read_with_its_fragments_joined(tmp_path):
    pages, runs = _doc(tmp_path)
    labels = _labels(pages[0], runs[1])
    texts = {L.text for L in labels}
    assert "12LBB50 BR010" in texts and "12LBB50 BR011" in texts
    L = next(L for L in labels if L.text == "12LBB50 BR010")
    assert L.parts == ("12LBB50", "BR010") and L.run is not None and L.run[0] == "H"
    assert L.spec.replace(" ", "") == "DN800HLBB1"


def test_vertical_flag_reads_the_same_way(tmp_path):
    pages, runs = _doc(tmp_path)
    labels = _labels(pages[0], runs[1])
    L = next((L for L in labels if L.text == "11MBP01 BR534"), None)
    assert L is not None and L.dir[0] == 0 and L.run is not None and L.run[0] == "V"
    assert "DN25P" in L.spec.replace(" ", "")


def test_table_cells_are_not_flags(tmp_path):
    pages, runs = _doc(tmp_path)
    labels = _labels(pages[0], runs[1])
    assert not any("AA20" in L.text for L in labels)


def test_shape_must_recur_on_two_pages(tmp_path):
    pages, runs = _doc(tmp_path)
    by_page = {pc.page_no: _labels(pc, runs[pc.page_no]) for pc in pages}
    system = LL.systematic(by_page)
    assert "D2L3D2L2D3" in system
    one = {1: by_page[1]}
    assert LL.systematic(one) == set()


def test_nearest_label_on_the_tapped_run(tmp_path):
    pages, runs = _doc(tmp_path)
    labels = _labels(pages[0], runs[1])
    # BR010 과 BR011 은 한 배관 위다 — 파이프라인이 넘기는 탭 런은 병합된 한 구간이다
    run = ("H", runs[1][0][1], 40.0, 800.0)
    L, n = LL.nearest_on_run((300, 40, 340, 60), run, labels, 0.8)
    assert L.text == "12LBB50 BR010" and n == 2
    L2, n2 = LL.nearest_on_run((640, 40, 680, 60), run, labels, 0.8)
    assert L2.text == "12LBB50 BR011"
    none, zero = LL.nearest_on_run((300, 40, 340, 60), ("H", 999.0, 0.0, 800.0), labels, 0.8)
    assert none is None and zero == 0


def test_fragment_gap_rule_is_a_ratio_of_glyph_height():
    f = lambda x0, x1, t: LL.Frag(pymupdf.Rect(x0, 100, x1, 108), t, (1, 0))   # noqa: E731
    joined = LL.join_fragments([f(10, 18, "12"), f(18.3, 30, "LBB"), f(30.6, 38, "50"), f(41, 50, "DN")])
    assert sorted(x.text for x in joined) == ["12LBB50", "DN"]        # 0.04h 는 잇고 0.37h 는 띄운다


def test_pipeline_hands_the_same_runs_to_labels_and_judgement_and_line_no_is_outside_the_fingerprint():
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert "geometry = daxis.page_runs(pc, style)" in src
    assert "geometry=geometry" in src and "line_labels.find_labels(" in src
    assert "line_no" in db.EDITABLE
    tree = ast.parse(src)
    fp = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "fingerprint")
    assert "line_no" not in ast.get_source_segment(src, fp)
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    cols = js[js.index("const COLS = ["):js.index("];", js.index("const COLS = ["))]
    assert cols.index('["tag_no"') < cols.index('["line_no", "Line No."') < cols.index('["valve_type"')


# ---------------------------------------------------------------- ISA 표 (QFE p3)
import isa_table                                   # noqa: E402

R = pymupdf.Rect


def _cell_words(x, y, letter, meaning, repeat=1):
    """`( ) X` 칸 하나 + 그 위 뜻 — 낱말 셋으로 갈라져 오고 `repeat` 번 겹쳐 찍힌다."""
    out = []
    for _ in range(repeat):
        out += [(R(x, y, x + 2, y + 6), "("), (R(x + 3, y, x + 5, y + 6), ")"),
                (R(x + 6, y, x + 12, y + 6), letter), (R(x, y - 14, x + 30, y - 8), meaning)]
    return out


def test_overprinted_cells_still_read_as_cells():
    """QFE 범례는 글자를 세 번 겹쳐 인쇄한다 — `( ( ( ) ) ) E E E` 는 칸 꼴이 아니다."""
    words = []
    for i, (k, m) in enumerate([("E", "ELEMENT"), ("T", "TRANSMITTER"), ("I", "INDICATOR"), ("S", "SWITCH")]):
        words += _cell_words(100 + i * 80, 300, k, m, repeat=3)
    succ = isa_table.succeeding_from_cells(words)
    assert succ["I"] == ("INDICATOR",) and succ["T"] == ("TRANSMITTER",) and "S" in succ


def test_cells_printed_as_a_turned_column_read_the_same():
    """표를 90° 돌려 인쇄한 판 — 칸이 한 열로 서고 뜻은 글자의 위쪽(돌린 뒤 +x)에 있다."""
    words = []
    for i, (k, m) in enumerate([("E", "ELEMENT"), ("T", "TRANSMITTER"), ("I", "INDICATOR")]):
        for r, t in _cell_words(100 + i * 80, 300, k, m):
            words.append((isa_table._turn_ccw(r), t))     # (0,1) 로 돌려 놓은 좌표
    succ = isa_table.succeeding_from_cells(words)
    assert succ.get("I") == ("INDICATOR",) and succ.get("E") == ("ELEMENT",)


# ---------------------------------------------------------------- 인출선 폴백 (QFE p46 PIT)
def test_leader_fallback_reads_the_line_the_leader_crosses_through_root_valves():
    """판정축은 인출선이 처음 가로지르는 뿌리 밸브의 10pt 획을 탭으로 잡는다 — 라인 번호는
    그 인출선이 (뿌리 밸브 둘을 지나) 닿는 배관의 깃발이다.  한 직선이고 순회가 아니다."""
    rect = (524.0, 290.0, 598.0, 316.0)                       # PIT 버블
    # 인출선 x=561: 세 토막 — 밸브 둘이 18pt 씩 끊는다
    leaders = [("V", 561.2, 315.8, 337.1), ("V", 561.2, 355.2, 379.6), ("V", 561.2, 397.7, 417.0)]
    runs = [("H", 315.8, 535.6, 586.6),                      # 버블 자신의 아랫변 — 몸통
            ("H", 337.1, 555.8, 566.4), ("H", 355.2, 555.8, 566.4),   # 밸브 끝 바 (짧다)
            ("H", 379.6, 555.8, 566.4), ("H", 397.7, 555.8, 566.4),
            ("H", 416.9, 248.0, 654.8),                      # 배관
            ("H", 600.0, 0.0, 800.0)]                        # 그 너머 다른 배관
    def label(text, y, x):
        L = LL.LineLabel(text=text, box=pymupdf.Rect(x, y - 30, x + 40, y - 18),
                         rect=pymupdf.Rect(x, y - 30, x + 40, y - 6), dir=(1, 0), h=8.0)
        L.run = next(r for r in runs if r[1] == y)
        return L
    labels = [label("12LBB50 BR010", 416.9, 320.0), label("99XXX99 BR999", 600.0, 100.0)]
    L, n, run = LL.via_leader(rect, leaders, runs, labels, 0.4)
    assert L.text == "12LBB50 BR010" and n == 1 and run[1] == 416.9


def test_leader_fallback_stops_at_an_unlabelled_pipe():
    """진짜 탭(배관)에 깃발이 없으면 그 너머 배관의 깃발을 집지 않는다."""
    rect = (524.0, 290.0, 598.0, 316.0)
    leaders = [("V", 561.2, 315.8, 417.0)]
    runs = [("H", 416.9, 248.0, 654.8), ("H", 600.0, 0.0, 800.0)]
    L = LL.LineLabel(text="99XXX99 BR999", box=pymupdf.Rect(100, 570, 140, 582),
                     rect=pymupdf.Rect(100, 570, 140, 594), dir=(1, 0), h=8.0)
    L.run = runs[1]
    got, n, run = LL.via_leader(rect, leaders, runs, [L], 0.4)
    assert got is None and n == 0 and run is None


def test_extension_bridges_only_inked_gaps_within_the_symbol_size():
    leaders = [("V", 10.0, 100.0, 120.0), ("V", 10.0, 135.0, 160.0), ("V", 10.0, 240.0, 300.0)]
    runs = [("H", 120.0, 5.0, 15.0), ("H", 135.0, 5.0, 15.0)]          # 첫 틈만 획이 가로지른다
    lo, hi = LL._extend_through_symbols("V", 10.0, 100.0, 120.0, True, leaders, runs, 26.0, 0.4)
    assert (lo, hi) == (100.0, 160.0)                                   # 둘째 틈(80pt · 획 없음)은 안 잇는다


# ---------------------------------------------------------------- 접기와 라인 번호 (QFE p59)
def test_folded_readout_hands_its_line_number_to_the_transmitter():
    from app import pipeline as P
    TABLE = isa_table.IsaTable(first={"P": ("PRESSURE",)}, succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",)},
                               page_no=3, note="t")
    def row(key, anchor, y, line=""):
        r = P.Row(key=key, tab=P.TAB_FIELD, page_no=59, drawing_no="D", type=anchor, qty=1,
                  rect=(900, y, 974, y + 26), tag_no="11LAB11CP001", evidence={"anchor": anchor})
        if line:
            r.line_no = line; r.evidence["line"] = {"line_no": line, "via": "leader", "candidates": 1}
        return r
    pit = row("a", "PIT", 72); pi = row("b", "PI", 113, line="11LAB11 BR001")
    _facts, folded = P._fold_readouts([pit, pi], TABLE)
    assert folded == {"b"}
    assert pit.line_no == "11LAB11 BR001" and pit.evidence["line"]["via"] == "readout"
    pit2 = row("c", "PIT", 72, line="11LAB11 BR007"); pi2 = row("d", "PI", 113, line="11LAB11 BR001")
    P._fold_readouts([pit2, pi2], TABLE)
    assert pit2.line_no == "11LAB11 BR007"                # 전송기가 이미 읽었으면 그대로
