"""hotfix22 — 압력 계기 임펄스 라인의 격막 씰 → Remark `Diaphragm Seal`.

모양은 그 문서 범례의 `DIAPHRAGM SEAL` 항목에서 읽는다 (AL NOUF1 p2 19.8×9.9 ·
TC2 p2 10.0×4.9 — 같은 모양, 다른 크기).  씰과 버블은 곧은 선 하나 또는 꺾임 하나.
"""
from __future__ import annotations
import inspect, sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine")); sys.path.insert(0, str(ROOT))
import diaphragm_seal as dsl  # noqa: E402
from app import pipeline as P, excel_out  # noqa: E402

S = 2.0      # 배율 — 같은 규칙이 크기를 넘는지 (A3 ↔ A1)


def _seal(pc, x, y, s=1.0):
    w, h = 10 * s, 5 * s
    r = pymupdf.Rect(x, y, x + w, y + h)
    pc._d.append({"items": [("qu", None)], "bbox": r, "fill": None})
    for k in range(3):   # 물결 셋
        pc._d.append({"items": [("c",), ("c",)], "fill": None,
                      "bbox": pymupdf.Rect(x + k * w / 3, y + 0.25 * h, x + (k + 1) * w / 3, y + 0.75 * h)})
    return r


class _PC:
    def __init__(self, page_no):
        self.page_no, self.words, self._d, self._s = page_no, [], [], []
    def drawings(self):
        return self._d
    def segments(self):
        return self._s
    def seg(self, x0, y0, x1, y1):
        self._s.append((pymupdf.Point(x0, y0), pymupdf.Point(x1, y1)))


def _legend(s=1.0):
    pc = _PC(2)
    _seal(pc, 100, 100, s)
    h = 4.2 * s
    pc.words += [(pymupdf.Rect(160 * s, 100, 160 * s + 23 * s, 100 + h), "DIAPHRAGM"),
                 (pymupdf.Rect(160 * s + 24 * s, 100, 160 * s + 34 * s, 100 + h), "SEAL"),
                 # 다른 항목의 문장 안에 든 같은 낱말은 캡션이 아니다
                 (pymupdf.Rect(100, 300, 115, 304), "WITH"),
                 (pymupdf.Rect(116, 300, 139, 304), "DIAPHRAGM"),
                 (pymupdf.Rect(140, 300, 150, 304), "SEAL")]
    return pc


def _sheet(s=1.0):
    pc = _PC(7)
    bubble = pymupdf.Rect(200, 100, 200 + 28 * s, 100 + 10 * s)
    cx = (bubble.x0 + bubble.x1) / 2
    seal = _seal(pc, cx - 5 * s, 150, s)
    pc.seg(cx, bubble.y1, cx, seal.y0)                    # 곧은 선 하나
    far = pymupdf.Rect(400, 100, 400 + 28 * s, 100 + 10 * s)
    seal2 = _seal(pc, 460, 150, s)
    pc.seg(far.x1, (far.y0 + far.y1) / 2, 465, (far.y0 + far.y1) / 2)   # 가로로 나와
    pc.seg(465, (far.y0 + far.y1) / 2, 465, seal2.y0)                   # 한 번 꺾여 씰로
    lonely = pymupdf.Rect(600, 100, 628, 110)
    _seal(pc, 700, 300, s)                                              # 아무 데도 안 이어진 씰
    return pc, {"a": bubble, "b": far, "c": lonely}


def test_shape_is_read_from_the_legend_line_that_prints_only_the_caption():
    sh = dsl.legend_shape([_legend()], "DIAPHRAGM SEAL")
    assert sh is not None and (round(sh.long), round(sh.short)) == (10, 5) and sh.page_no == 2
    assert dsl.legend_shape([_PC(2)], "DIAPHRAGM SEAL") is None      # 범례에 없으면 없다


def test_seals_link_by_one_segment_or_one_bend_at_any_scale():
    for s in (1.0, S):
        sh = dsl.legend_shape([_legend(s)], "DIAPHRAGM SEAL")
        pc, bubbles = _sheet(s)
        seals = dsl.find(pc, sh)
        assert len(seals) == 3
        hit = dsl.link(pc, seals, bubbles)
        assert set(hit) == {"a", "b"}                            # 이어지지 않은 버블 c 는 없다


def test_a_box_of_another_size_or_without_a_wave_is_not_a_seal():
    sh = dsl.legend_shape([_legend()], "DIAPHRAGM SEAL")
    pc = _PC(7)
    pc._d.append({"items": [("qu", None)], "bbox": pymupdf.Rect(0, 0, 10, 5), "fill": None})   # 물결 없음
    _seal(pc, 50, 50, 1.6)                                                                        # 크기 다름
    assert dsl.find(pc, sh) == []


def test_pipeline_writes_the_remark_only_for_the_configured_types():
    class R:
        def __init__(s, key, type_, rect):
            s.key, s.type, s.rect, s.tab, s.page_no = key, type_, rect, P.TAB_FIELD, 7
            s.remark, s.evidence = "도면 근거 있음", {}
    pc, bubbles = _sheet()
    rows = [R("a", "PI", tuple(bubbles["a"])), R("b", "FS", tuple(bubbles["b"]))]
    tb = {2: {"page_kind": "LEGEND"}, 7: {"page_kind": "PID"}}
    st = P._attach_diaphragm_seals(rows, [_legend(), pc], tb)
    assert rows[0].remark.startswith("Diaphragm Seal") and rows[0].evidence["diaphragm_seal"]["rects"]
    assert "diaphragm_seal" not in rows[1].evidence and st["other_types"] == {"FS": 1}
    assert st["rows"] == 1 and st["legend"]["page_no"] == 2


def test_excel_remark_says_it_once():
    ev = {"diaphragm_seal": {"remark": "Diaphragm Seal", "rects": [[0, 0, 1, 1]]}}
    no_code = excel_out._remark({"evidence": ev}, {"remark": "Diaphragm Seal · 도면 근거 있음"})
    assert no_code.count("Diaphragm Seal") == 1
    with_code = excel_out._remark({"evidence": ev, "review_codes": ["MULTIPLIER_DEFAULT_ONE"]}, {})
    assert with_code.startswith("Diaphragm Seal")


def test_no_traversal_beyond_one_bend():
    src = inspect.getsource(dsl.link)
    assert "while" not in src and "queue" not in src and "seen" not in src
