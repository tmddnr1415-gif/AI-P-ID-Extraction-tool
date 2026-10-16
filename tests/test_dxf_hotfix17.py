"""hotfix17 — UAD DXF p19: 같은 라벨인데 한 줄만 식별되던 원인들 (범용 규칙).

① 회전된 글자(90°/270°)의 사각형을 회전대로 놓는다 — 세로 버블 안 태그.
② LEADER 엔티티의 꼭짓점을 읽는다 — 예외가 삼켜져 전부 빠지고 있었다.
③ 버블 블록은 **모양(크기 + 곡선)** 으로 알아본다 — 호·스플라인·타원 무엇으로 그렸든.
④ 블록 정의 안에 든 글자도 그 버블의 글자다 (`insert_words`).
⑤ 2급 경로도 1급과 같은 순서로 묻는다: ISA 표 → 밸브 사전 → 앵커 사전 (`RO`).
⑥ 범례 VALVE STATUS 구획의 블록은 칠을 뺀 윤곽이 같은 밸브의 몸체를 잇는다.
⑦ 같은 태그의 루프에서 전송기가 있으면 기능 표시(`FIR`)는 행이 아니다.
⑧ 도면 창 경계 손잡이 — 폭·높이를 끌어 바꾸고 이 브라우저에만 기억한다.
"""
from pathlib import Path

import ezdxf
import pytest

from app.engine import dxf_reader as R
from app import dxf_pipeline as D

ROOT = Path(__file__).resolve().parent.parent
SRC = (ROOT / "app/dxf_pipeline.py").read_text(encoding="utf-8")


def _sheet(doc):
    return R.Sheet(no=1, order_key="t", file="t.dxf", doc=doc, msp=doc.modelspace(),
                   extents=(0.0, 0.0, 100.0, 100.0))


def test_rotated_text_rect_stands_up():
    doc = ezdxf.new()
    msp = doc.modelspace()
    e = msp.add_text("00GHB34BP101", dxfattribs={"height": 2.0, "rotation": 90.0,
                                                  "insert": (50, 50)})
    x0, y0, x1, y1 = R._text_rect(_sheet(doc), e, 2.0, e.dxf.text)
    assert (y1 - y0) > 5 * (x1 - x0)          # 세로로 선다
    e2 = msp.add_text("00GHB34BP101", dxfattribs={"height": 2.0, "insert": (50, 50)})
    a0, b0, a1, b1 = R._text_rect(_sheet(doc), e2, 2.0, e2.dxf.text)
    assert (a1 - a0) > 5 * (b1 - b0)          # 회전 0 은 예전처럼 가로


def test_leader_vertices_are_read():
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_leader([(10, 10), (20, 30), (40, 30)])
    segs = R.lines(_sheet(doc))
    # 지시선은 한 걸음 — 첫 꼭짓점에서 끝 꼭짓점까지 (표시 좌표 · y 아래)
    assert [(a, b) for a, b, _l in segs] == [((10.0, 90.0), (40.0, 70.0))]


def test_insert_words_reads_text_inside_block_definition():
    doc = ezdxf.new()
    b = doc.blocks.new("BUBBLE_X")
    b.add_circle((0, 0), 4)
    b.add_text("MOV", dxfattribs={"height": 2.0, "insert": (-2, 0)})
    ins = doc.modelspace().add_blockref("BUBBLE_X", (50, 50))
    sh = _sheet(doc)
    sym = next(s for s in R.symbols(sh) if s.block == "BUBBLE_X")
    assert [w.text for w in R.insert_words(sh, sym)] == ["MOV"]
    assert ins is not None


def test_outline_ignores_fill():
    doc = ezdxf.new()
    open_ = doc.blocks.new("A1")
    closed = doc.blocks.new("A2")
    other = doc.blocks.new("A3")
    for blk in (open_, closed):
        blk.add_line((0, 0), (0, 4)); blk.add_line((0, 4), (6, 0))
        blk.add_line((6, 0), (6, 4)); blk.add_line((6, 4), (0, 0))
    h = closed.add_hatch()
    h.paths.add_polyline_path([(0, 0), (0, 4), (3, 2)], is_closed=True)
    other.add_line((0, 0), (6, 4)); other.add_circle((3, 2), 1)
    o1, o2, o3 = (R.block_geometry(doc, n)["outline"] for n in ("A1", "A2", "A3"))
    assert o1 and o1 == o2 and o1 != o3


def _legend(name, sections, outline, captions=()):
    import collections
    return name, {"sections": collections.Counter(sections),
                  "section_captions": {s: collections.Counter(captions) for s in sections},
                  "captions": collections.Counter(captions), "attdefs": [],
                  "geometry": {"outline": outline, "radii": []}}


def test_status_block_inherits_body_only_when_unique():
    legend = dict([
        _legend("V1", ["LINE VALVES"], "O1", ["BUTTERFLY"]),
        _legend("S1", ["VALVE STATUS SYMBOLS"], "O1", ["OPEN DURING NORMAL OPERATION"]),
        _legend("V2", ["LINE VALVES"], "O2", ["GATE"]),
        _legend("V3", ["LINE VALVES"], "O2", ["GLOBE"]),
        _legend("S2", ["VALVE STATUS SYMBOLS"], "O2", ["LOCKED CLOSED"]),
        _legend("X1", ["MISCELLANEOUS"], "O1", ["STRAINER"]),
    ])
    out = D.classify_blocks(legend, {"type": set(), "tag": set()})
    assert (out["S1"]["kind"], out["S1"]["body"]) == ("valve", "BUTTERFLY")
    assert out["S1"]["body_from"] == "STATUS_OUTLINE"
    assert out["S2"]["kind"] == "other"          # 윤곽이 두 몸체와 같다 — 고르지 않는다
    assert out["X1"]["kind"] == "other"          # 상태 구획이 아니면 윤곽이 같아도 잇지 않는다


def test_block_path_asks_anchor_dictionary_after_isa_and_valves():
    seg = SRC.split("# ── 계기 (2급", 1)[1].split("# ── 기하 폴백", 1)[0]
    i_isa = seg.index("_isa_type(w.text, isa)")
    i_valve = seg.index("in rules.valves), None)")
    i_dict = seg.index("in rules.anchors), None)")
    assert i_isa < i_valve < i_dict
    assert "ANCHOR_FROM_DICT" in seg and "rules.not_field" in seg


def test_bubble_blocks_are_known_by_shape_not_radius_only():
    assert "_bubble_shaped(g)" in SRC
    assert '_CURVES = ("ARC", "CIRCLE", "ELLIPSE", "SPLINE")' in SRC


def test_signal_function_rule_is_recorded_not_dropped_silently():
    assert '"SIGNAL_FUNCTION"' in SRC


def test_no_block_or_layer_names_in_the_new_rules():
    # 주석은 실측을 적는 자리라 이름이 나올 수 있다 — **판정에 쓰이는 문자열 상수**만 본다
    import ast
    consts = {n.value for n in ast.walk(ast.parse(SRC)) if isinstance(n, ast.Constant)
              and isinstance(n.value, str)}
    consts |= {n.value for n in ast.walk(ast.parse((ROOT / "app/engine/dxf_reader.py").read_text(
        encoding="utf-8"))) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    for name in ("Butterfly Valve (Open)", "Gate Valve (Close)", "EEE", "11", "QQ", "555",
                 "PIP MOTOR OPERATED", "Instrument line"):
        assert name not in consts


def test_split_gutters_exist_and_storage_is_guarded():
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'id="gutter-v"' in html and 'id="gutter-h"' in html and 'id="infobars"' in html
    seg = js.split('const SPLIT_KEY = "pid.split";', 1)[1]
    assert seg.count("try {") >= 2               # 저장소 읽기·쓰기 둘 다 감싼다
    assert "var(--left-w, 1fr)" in css and "col-resize" in css and "row-resize" in css
