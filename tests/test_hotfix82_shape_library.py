"""hotfix82 [C] — 밸브 모양 사전: 사전이 없으면 예전 그대로 · 있으면 규칙이 못 가른 중공 몸체를 확정된 보기에 맞댄다."""
from __future__ import annotations

import ast
import json
import pathlib
import sys

import pymupdf
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app" / "engine"))


def _page_with(tmp_path, name, draw):
    import pidcache
    doc = pymupdf.open()
    pg = doc.new_page(width=600, height=400)
    draw(pg)
    path = tmp_path / f"{name}.pdf"
    doc.save(str(path)); doc.close()
    _d, pages = pidcache.load_pages(path)
    return pages[0]


def _bars(pg, x0, y0, x1, y1):
    pg.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x0, y1), width=0.3)
    pg.draw_line(pymupdf.Point(x1, y0), pymupdf.Point(x1, y1), width=0.3)


def _poly(pg, pts):
    """한 path 에 선 여럿 (`get_drawings` 가 'l' 항목 n 개인 path 하나로 낸다 — 실물의 "한 객체 · 선 여섯")."""
    sh = pg.new_shape()
    for a, b in zip(pts, pts[1:]):
        sh.draw_line(a, b)
    sh.finish(width=0.3, fill=None); sh.commit()


def _box_body(pg, x0, y0, x1, y1):
    """한 path 에 선 넷(사각 테두리) — 규칙의 어느 갈래도 아닌 중공 몸체.  끝막대는 따로 (사각형 변과 같은 x)."""
    # 윗변을 두 토막으로 (PyMuPDF 는 닫힌 선 넷을 'qu' 하나로 접어 'l' 항목이 사라진다)
    cx = (x0 + x1) / 2
    _poly(pg, [pymupdf.Point(x0, y0 + 1), pymupdf.Point(cx, y0 + 1), pymupdf.Point(x1, y0 + 1), pymupdf.Point(x1, y1 - 1),
               pymupdf.Point(x0, y1 - 1), pymupdf.Point(x0, y0 + 1)])
    _bars(pg, x0, y0, x1, y1)


def _vbox_body(pg, x0, y0, x1, y1):
    """세로 몸체 — 같은 사각이 90° 돌아 있고 끝막대는 위아래."""
    cy = (y0 + y1) / 2
    _poly(pg, [pymupdf.Point(x0 + 1, y0), pymupdf.Point(x0 + 1, cy), pymupdf.Point(x0 + 1, y1), pymupdf.Point(x1 - 1, y1),
               pymupdf.Point(x1 - 1, y0), pymupdf.Point(x0 + 1, y0)])
    pg.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x1, y0), width=0.3)
    pg.draw_line(pymupdf.Point(x0, y1), pymupdf.Point(x1, y1), width=0.3)


def _box_body_mid(pg, x0, y0, x1, y1):
    """사각 테두리 + 가운데 세로선 — 같은 종류(GATE)의 조금 다른 그림 (같은 그림은 하나로 접히므로)."""
    cx = (x0 + x1) / 2
    _poly(pg, [pymupdf.Point(x0, y0 + 1), pymupdf.Point(cx, y0 + 1), pymupdf.Point(x1, y0 + 1), pymupdf.Point(x1, y1 - 1),
               pymupdf.Point(x0, y1 - 1), pymupdf.Point(x0, y0 + 1), pymupdf.Point(cx, y0 + 1), pymupdf.Point(cx, y1 - 1)])
    _bars(pg, x0, y0, x1, y1)


def _hex_body(pg, x0, y0, x1, y1):
    """한 path 에 선 여섯(육각) — 다른 모양."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) / 2 - 1, (y1 - y0) / 2 - 1
    w = (x1 - x0) / 2
    pts = [pymupdf.Point(cx - w, cy), pymupdf.Point(cx - w / 2, cy - h), pymupdf.Point(cx + w / 2, cy - h),
           pymupdf.Point(cx + w, cy), pymupdf.Point(cx + w / 2, cy + h), pymupdf.Point(cx - w / 2, cy + h), pymupdf.Point(cx - w, cy)]
    _poly(pg, pts)
    _bars(pg, x0, y0, x1, y1)


def _lib_from(pc, rects_kinds):
    import shape_library as sl
    lib = sl.new_library()
    for rect, kind in rects_kinds:
        bm = sl.descriptor(pc, rect)
        assert bm is not None
        sl.add_exemplar(lib, bm, kind, "RULE", project="T", doc="abc", page_no=1, rect=rect)
    sl.derive_threshold(lib)
    return lib


def test_descriptor_is_size_position_and_rotation_free(tmp_path):
    import shape_library as sl
    pc = _page_with(tmp_path, "d", lambda pg: (_box_body(pg, 100, 100, 130, 116), _box_body(pg, 300, 200, 360, 232),
                                               _vbox_body(pg, 100, 300, 116, 330)))       # 2배 · 세로
    a = sl.descriptor(pc, [100, 101, 130, 115]); b = sl.descriptor(pc, [300, 201, 360, 231]); c = sl.descriptor(pc, [101, 300, 115, 330])
    assert a.shape == sl.GRID and sl.distance(a, b) < 0.08
    assert sl.nearest(c, b[None])[1] < 0.08                                      # 세로는 회전 변형으로 맞는다


def test_threshold_comes_from_the_library_itself(tmp_path):
    pc = _page_with(tmp_path, "t", lambda pg: (_box_body(pg, 100, 100, 130, 116), _box_body_mid(pg, 200, 100, 230, 116),
                                               _hex_body(pg, 300, 100, 330, 116), _hex_body(pg, 400, 100, 430, 116)))
    lib = _lib_from(pc, [([100, 101, 130, 115], "GATE"), ([200, 101, 230, 115], "GATE"),
                         ([300, 101, 330, 115], "BALL"), ([400, 101, 430, 115], "BALL")])
    assert len(lib.exemplars) == 3                                               # 같은 그림(육각 둘)은 하나로 — count 2
    b = lib.basis
    assert lib.threshold is not None and b["within_max"] is not None and b["cross_min"] is not None
    assert b["within_max"] < b["cross_min"] and b["gap"] is True and lib.threshold == min(b["within_max"], b["cross_min"])
    # 종류마다 보기 하나씩이면 같은 종류 짝이 없다 — 다른 종류 최솟값의 절반, 그렇다고 적는다
    two = _lib_from(pc, [([100, 101, 130, 115], "GATE"), ([300, 101, 330, 115], "BALL")])
    assert two.basis["within_max"] is None and two.threshold == round(two.basis["cross_min"] / 2, 4)
    # 보기 하나뿐이면 문턱이 없고 사전은 판정하지 않는다
    one = _lib_from(pc, [([100, 101, 130, 115], "GATE")])
    assert one.threshold is None and not one.usable()


def test_promote_only_what_the_rule_left_and_only_within_threshold(tmp_path):
    import detect_valves as dv, shape_library as sl
    ref = _page_with(tmp_path, "ref", lambda pg: (_box_body(pg, 100, 100, 130, 116), _box_body(pg, 200, 100, 230, 116),
                                                  _hex_body(pg, 300, 100, 330, 116), _hex_body(pg, 400, 100, 430, 116)))
    lib = _lib_from(ref, [([100, 101, 130, 115], "GATE"), ([200, 101, 230, 115], "GATE"),
                          ([300, 101, 330, 115], "BALL"), ([400, 101, 430, 115], "BALL")])
    # 새 장: 같은 사각 몸체 하나 · 전혀 다른 모양(지그재그) 하나
    def zig(pg, x0, y0, x1, y1):
        pts = [pymupdf.Point(x0, y1 - 1), pymupdf.Point(x0 + 6, y0 + 1), pymupdf.Point(x0 + 12, y1 - 1),
               pymupdf.Point(x0 + 18, y0 + 1), pymupdf.Point(x1, y1 - 1)]
        _poly(pg, pts); _bars(pg, x0, y0, x1, y1)
    pc = _page_with(tmp_path, "new", lambda pg: (_box_body(pg, 150, 150, 180, 166), zig(pg, 350, 150, 380, 166)))
    assert dv.find_bodies(pc, dv.LAYOUT) == []                                   # 규칙은 어느 쪽도 못 가른다
    cands = dv.unclassified_bodies(pc, dv.LAYOUT, [])
    assert len(cands) == 2
    hits = sl.promote(pc, cands, lib)
    assert [h["kind"] for h in hits] == ["GATE"] and hits[0]["evidence"]["body_source"] == "SHAPE_LIBRARY"
    assert hits[0]["evidence"]["exemplar"]["kind"] == "GATE" and hits[0]["evidence"]["distance"] <= lib.threshold
    # 사전 없음 → 아무것도 · 보기를 X 로 거르면 그 보기는 안 쓴다
    assert sl.promote(pc, cands, None) == []
    for e in list(lib.exemplars):
        if e.kind == "GATE":
            lib.vetoed[e.id] = "X"
    lib._live = None; lib._stack = None; sl.derive_threshold(lib)
    assert sl.promote(pc, cands, lib) == []


def test_analyse_is_byte_for_byte_the_same_without_a_library(tmp_path):
    import detect_valves as dv
    pc = _page_with(tmp_path, "same", lambda pg: _box_body(pg, 150, 150, 180, 166))
    a = dv.analyse(pc, dv.LAYOUT)
    b = dv.analyse(pc, dv.LAYOUT, shape_lib=None)
    assert [x.as_json() for x in a["bodies"]] == [x.as_json() for x in b["bodies"]] == []
    ref = _page_with(tmp_path, "ref2", lambda pg: (_box_body(pg, 100, 100, 130, 116), _box_body_mid(pg, 200, 100, 230, 116)))
    lib = _lib_from(ref, [([100, 101, 130, 115], "GATE"), ([200, 101, 230, 115], "GATE")])
    c = dv.analyse(pc, dv.LAYOUT, shape_lib=lib)
    assert [x.kind for x in c["bodies"]] == ["GATE"] and c["bodies"][0].evidence["body_source"] == "SHAPE_LIBRARY"
    assert dv.unclassified_bodies(pc, dv.LAYOUT, c["bodies"]) == []             # 사전이 세운 몸체는 미판정에서 빠진다


def test_library_file_round_trip_and_off_switches(tmp_path, monkeypatch):
    import shape_library as sl
    ref = _page_with(tmp_path, "rt", lambda pg: (_box_body(pg, 100, 100, 130, 116), _box_body_mid(pg, 200, 100, 230, 116)))
    lib = _lib_from(ref, [([100, 101, 130, 115], "GATE"), ([200, 101, 230, 115], "GATE")])
    f = tmp_path / "shape_library.json"
    sl.save(lib, f)
    back = sl.load(f)
    assert back is not None and back.threshold == lib.threshold and len(back.exemplars) == len(lib.exemplars)
    assert back.summary()["kinds"] == {"GATE": len(lib.exemplars)}
    assert sl.load(tmp_path / "none.json") is None
    monkeypatch.setenv(sl.ENV_OFF, "0")
    assert sl.load(f) is None
    monkeypatch.delenv(sl.ENV_OFF)
    monkeypatch.setenv(sl.ENV_FILE, str(f))                                     # 자리 지정 — 회귀 실험이 쓴다
    assert sl.default_path() == f and sl.load() is not None
    monkeypatch.delenv(sl.ENV_FILE)
    bad = tmp_path / "bad.json"; bad.write_text("{not json", encoding="utf-8")
    assert sl.load(bad) is None


def test_pipeline_passes_the_library_and_flags_rows_and_engine_stays_independent():
    pl = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    assert "shape_lib=shape_lib" in pl and "def _shape_library()" in pl and '"BODY_FROM_SHAPE_LIBRARY"' in pl
    assert '"shape_library": shape_lib.summary() if shape_lib is not None else None' in pl
    dvs = (ROOT / "app/engine/detect_valves.py").read_text(encoding="utf-8")
    body = dvs[dvs.index("def find_bodies("):dvs.index("def unclassified_bodies(")]
    assert "shape_library" not in body and "unclassified_bodies" not in body       # 규칙 자체는 사전을 모른다
    # 사전 모듈은 detect_valves 를 import 하지 않는다 (순환 없음) · 새 절대 pt 상수 없음 (격자 크기뿐)
    src = (ROOT / "app/engine/shape_library.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
            assert not any("detect_valves" in (x or "") for x in names)
    assert "REVIEW_CODE = \"BODY_FROM_SHAPE_LIBRARY\"" in src
    main_src = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert '"BODY_FROM_SHAPE_LIBRARY":' in main_src
    assert "BODY_FROM_SHAPE_LIBRARY: DETECTION" in (ROOT / "config/project_alnouf1.yaml").read_text(encoding="utf-8")


def test_train_tool_builds_a_usable_library_from_a_pdf(tmp_path):
    """합성 PDF 하나 — 규칙이 판정하는 나비 몸체 둘 → 보기 → 문턱.  학습 도구는 분석 경로 밖의 스크립트다."""
    import subprocess
    doc = pymupdf.open(); pg = doc.new_page(width=600, height=400)
    for cx in (150, 300, 450):
        w, h = 10, 5
        pg.draw_line(pymupdf.Point(cx - w, 100 - h), pymupdf.Point(cx + w, 100 + h), width=0.3)
        pg.draw_line(pymupdf.Point(cx - w, 100 + h), pymupdf.Point(cx + w, 100 - h), width=0.3)
        _bars(pg, cx - w, 100 - h, cx + w, 100 + h)
    pdf = tmp_path / "bow.pdf"; doc.save(str(pdf)); doc.close()
    out = tmp_path / "lib.json"
    p = subprocess.run([sys.executable, "spike/shape_train.py", "--pdf", str(pdf), "--out", str(out)],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["schema"] == 1 and d["exemplars"] and all(e["source"] == "RULE" for e in d["exemplars"])
    assert "보기" in p.stdout
