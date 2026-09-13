"""38회차 [D] — Typical 참조.  모양으로 읽고, 캡션이 있는 id 만 참조로 센다, 곱하는 곳은 하나."""
from __future__ import annotations
import ast, inspect, re, sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine")); sys.path.insert(0, str(ROOT))
import typical  # noqa: E402
from app import pipeline as P  # noqa: E402


class _PC:
    """words · drawings() · segments() 만 가진 가짜 쪽."""
    def __init__(self, words, circles, hlines):
        self.words = [(pymupdf.Rect(*r), t) for r, t in words]
        self._c = circles; self._h = hlines
    def drawings(self):
        return [{"items": [("c",)] * 4, "bbox": pymupdf.Rect(x - d / 2, y - d / 2, x + d / 2, y + d / 2)}
                for x, y, d in self._c]
    def segments(self):
        return [(pymupdf.Point(x0, y), pymupdf.Point(x1, y)) for x0, x1, y in self._h]


AREA = pymupdf.Rect(0, 0, 900, 800)


def _tc2_like():
    # 라인 표식 D 셋(y=300) · 캡션 D (600,660) + 제목 · 상자 y 650~800 x 500~900 · 모터 M 원 하나
    words = [((598, 658, 602, 662), "D"), ((607, 658, 618, 662), "HRH"), ((620, 658, 640, 662), "TYPICAL"),
             ((642, 658, 680, 662), "CONFIGURATION"),
             ((198, 298, 202, 302), "D"), ((398, 298, 402, 302), "D"), ((498, 298, 502, 302), "D"),
             ((298, 398, 302, 402), "M")]
    circles = [(600, 660, 7.1), (200, 300, 7.1), (400, 300, 7.1), (500, 300, 7.1), (300, 400, 7.1)]
    # 라인 표식 둘은 선 위에 그려져 있고(지나가는 선), 하나(500,300)는 TC2 처럼 배관에서 내려온
    # 리더 하나에 매달려 있다.  모터 M 도 스템 하나가 닿는다 — 갈리는 것은 모양이 아니라 캡션 짝이다.
    hlines = [(500, 900, 650), (500, 900, 800), (0, 450, 300)]
    pc = _PC(words, circles, hlines)
    pc.segments = lambda: [(pymupdf.Point(x0, y), pymupdf.Point(x1, y)) for x0, x1, y in pc._h] + [
        (pymupdf.Point(500, 296.5), pymupdf.Point(500, 280)),      # D 리더
        (pymupdf.Point(300, 403.5), pymupdf.Point(300, 430))]      # M 스템
    return pc


def test_marks_captions_boxes_and_refs_are_read_by_shape():
    t = typical.analyse(_tc2_like(), AREA, ceiling=11.4)
    assert sorted(m.id for m in t.marks) == ["D", "D", "D", "D", "M"]
    assert len(t.details) == 1 and t.details[0].id == "D"
    assert t.details[0].caption.startswith("HRH TYPICAL")           # ':' 없이도 캡션
    assert [round(v) for v in t.details[0].box] == [500, 650, 900, 800]
    assert t.refs == {"D": 3} and "M" not in t.refs                 # 캡션 없는 M 은 참조가 아니다
    assert not t.ambiguous


def test_a_circle_as_big_as_a_bubble_is_not_a_mark():
    t = typical.analyse(_tc2_like(), AREA, ceiling=7.0)             # 상한이 원보다 작다
    assert t.marks == [] and t.details == []


def test_two_captions_with_the_same_id_are_ambiguous_not_multiplied():
    pc = _tc2_like()
    pc.words += [((598, 708, 602, 712), "D"), ((607, 708, 630, 712), "OTHER"), ((632, 708, 660, 712), "DETAIL")]
    pc._c.append((600, 710, 7.1))
    t = typical.analyse(pc, AREA, ceiling=11.4)
    assert t.ambiguous == {"D"}


class _Row:
    def __init__(self, page_no, rect, qty):
        self.page_no, self.rect, self.qty, self.evidence, self.needs_review = page_no, rect, qty, {"qty_basis": "1 symbol x 8 (NOTES)"}, ""


def test_apply_multiplies_only_rows_inside_the_detail_box():
    t = typical.analyse(_tc2_like(), AREA, ceiling=11.4)
    inside, outside, none = _Row(1, (600, 700, 630, 712), 8), _Row(1, (100, 100, 130, 112), 8), _Row(1, (610, 700, 640, 712), None)
    stats = P._apply_typical([inside, outside, none], {1: t})
    assert inside.qty == 24 and outside.qty == 8 and none.qty is None
    assert inside.evidence["typical"]["refs"] == 3 and "x 3 (( D ) 상세 한 벌 × 본문 표식 3개)" in inside.evidence["qty_basis"]
    assert stats["rows_multiplied"] == 1 and stats["rows_in_detail"] == 2


def test_ambiguous_rows_are_flagged_not_multiplied():
    pc = _tc2_like()
    pc.words += [((598, 708, 602, 712), "D"), ((607, 708, 630, 712), "OTHER"), ((632, 708, 660, 712), "DETAIL")]
    pc._c.append((600, 710, 7.1))
    t = typical.analyse(pc, AREA, ceiling=11.4)
    r = _Row(1, (600, 700, 630, 712), 8)
    P._apply_typical([r], {1: t})
    assert r.qty == 8 and "TYPICAL_AMBIGUOUS" in r.evidence["review_codes"]


def test_the_only_place_that_multiplies_is_apply_typical():
    src = (ROOT / "app" / "pipeline.py").read_text()
    assert src.count("typical.analyse(") == 1 and src.count("= _apply_typical(") == 1


# ---------------------------------------------------------------------------------------------
# 보정 프롬프트 게이트 — 글자가 아니라 구조로 찾는다
# ---------------------------------------------------------------------------------------------

_LETTER_LIKE = re.compile(r"^[\(\[ ]*(D\d?|T\d?|TYP[-A-Z0-9]*|TYPICAL|DETAIL)[\)\] ]*$")   # 표식 글자 그대로


def _string_constants(tree):
    """docstring 이 아닌 문자열 상수만 — 근거·주석에 적는 것은 허용이고 판정에만 못 쓴다."""
    doc_nodes = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                doc_nodes.add(id(node.body[0].value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_nodes]


def test_gate_no_marker_letters_in_the_judging_code():
    """★ D · D1 · D2 · T1 · TYP · TYPICAL 같은 글자가 판정 코드에 하나도 없다 (소스로 못박는다).
    25회차 `test_star_marks.py` 가 절대 pt 를 못박은 것과 같은 방식."""
    consts = _string_constants(ast.parse((ROOT / "app/engine/typical.py").read_text()))
    consts += _string_constants(ast.parse(inspect.getsource(P._apply_typical)))
    bad = [c for c in consts if _LETTER_LIKE.match(c.strip())]
    assert bad == [], bad                                  # 'typical'(근거 키) · 'TYPICAL_AMBIGUOUS'(사유 코드) 는 글자가 아니라 이름
    src = (ROOT / "app/engine/typical.py").read_text()
    assert "re.compile" not in src and "import re" not in src   # 글자 꼴 정규식도 없다


def test_gate_no_global_marker_list_anywhere():
    """표식 목록은 장마다 그 장에서 만든다 — 모듈에 글자 목록이 없고 config 도 읽지 않는다."""
    tree = ast.parse((ROOT / "app/engine/typical.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            assert not isinstance(node.value, (ast.List, ast.Tuple, ast.Set, ast.Dict)), ast.dump(node)[:80]
    src = (ROOT / "app/engine/typical.py").read_text()
    assert "CFG" not in src and "config" not in src.lower().replace("configuration", "")


def test_box_crossed_by_piping_is_not_an_island():
    """상세 상자는 본문 배관과 이어지지 않은 섬이다 — 안에서 밖으로 나가는 선이 있으면 상자가 아니다."""
    pc = _tc2_like()
    box = pymupdf.Rect(500, 650, 900, 800)
    assert typical.is_island(box, pc.segments())
    pipe = [(pymupdf.Point(700, 700), pymupdf.Point(1100, 700))]          # 안 → 밖
    assert not typical.is_island(box, pc.segments() + pipe)
    edge = [(pymupdf.Point(500, 650), pymupdf.Point(500, 800))]            # 자기 변 — 섬을 깨지 않는다
    assert typical.is_island(box, pc.segments() + edge)
    pc.segments = (lambda base=pc.segments: (lambda: base() + pipe))()
    t = typical.analyse(pc, AREA, ceiling=11.4)
    assert t.details and t.details[0].box is None                           # 후보가 섬이 아니면 상자 없음


def test_unpaired_marks_are_listed_not_counted():
    t = typical.analyse(_tc2_like(), AREA, ceiling=11.4)
    assert t.unpaired == {"M": 1} and "M" not in t.refs                     # 캡션 없는 라인 표식 — 기록만


# --- 합성 도면: 같은 구조에 글자만 바꾼다 (32회차 방식 — pymupdf 로 그린 PDF 를 pidcache 로 읽는다)
def _draw_sheet(page, ident: str):
    """상세 상자 + 캡션 원 + 라인 표식 셋(리더) + 모터 원(스템 · 캡션 없음).  요소마다 path 하나."""
    def one(fn, *a):
        sh = page.new_shape(); fn(sh, *a); sh.finish(color=(0, 0, 0), width=0.5); sh.commit()
    one(lambda sh: sh.draw_rect(pymupdf.Rect(400, 500, 780, 700)))                      # 상자
    one(lambda sh: sh.draw_line((50, 300), (750, 300)))                                # 배관
    one(lambda sh: sh.draw_circle((430, 520), 12))                                     # 캡션 원 (자유)
    for x in (150, 350, 550):
        one(lambda sh, x=x: sh.draw_line((x, 300), (x, 328)))                          # 리더
        one(lambda sh, x=x: sh.draw_circle((x, 340), 12))                              # 라인 표식
    one(lambda sh: sh.draw_line((250, 400), (250, 428))); one(lambda sh: sh.draw_circle((250, 440), 12))   # 모터 원
    one(lambda sh: sh.draw_line((600, 560), (700, 560))); one(lambda sh: sh.draw_circle((650, 600), 12))   # 상자 안 표식
    fs = 6 if len(ident) <= 2 else 4
    for cx, cy, txt in [(430, 520, ident), (150, 340, ident), (350, 340, ident), (550, 340, ident),
                        (250, 440, "M"), (650, 600, ident)]:
        w = pymupdf.get_text_length(txt, fontname="helv", fontsize=fs)
        page.insert_text((cx - w / 2, cy + fs * 0.35), txt, fontsize=fs, fontname="helv")
    page.insert_text((450, 523), "COLD REHEAT DRAIN ARRANGEMENT", fontsize=6, fontname="helv")


def test_synthetic_sheets_give_the_same_factor_whatever_the_letters_are(tmp_path):
    """★ 글자만 D1 · T1 · TYP-A · 1 · ⓐ 로 바꾼 같은 구조 → 같은 배수.  다르면 글자에 맞춰진 것이다."""
    import pidcache  # noqa
    ids = ["D1", "T1", "TYP-A", "1", "A"]
    doc = pymupdf.open()
    for ident in ids:
        page = doc.new_page(width=842, height=595)
        _draw_sheet(page, ident)
    pdf = tmp_path / "typical_synthetic.pdf"; doc.save(str(pdf)); doc.close()
    _d, pages = pidcache.load_pages(pdf)
    area = pymupdf.Rect(0, 0, 842, 595)
    got = {}
    for pc, ident in zip(pages, ids):
        t = typical.analyse(pc, area, ceiling=30.0)
        got[ident] = (t.refs.get(ident), [round(v) for v in t.details[0].box] if t.details and t.details[0].box else None,
                      sorted(t.unpaired))
    for ident in ids:
        assert got[ident] == (3, [400, 500, 780, 700], ["M"]), (ident, got[ident])
