"""hotfix37 — 사용자 정의: **Line No. = 사각형 안 코드(`12LBB50`)** · **Line Size = `DN 800`**.

깃발 건너편 글줄 `DN800H LBB1` 은 범례 p5 가 정의한 세 조각(직경 · 보온 H/P/N · 설계 코드)이다.
보온 글자는 **그 범례**의 `- H :` 글줄에서, 직경 접두는 범례 예시가 획이라 **본문 깃발 다수**에서
배운다 (§9 ④).  코드에 `DN`·`H`·`P`·`N` 을 적지 않는다 (AST 시험).
"""
from __future__ import annotations

import ast
import pathlib
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app" / "engine"))
import pidcache                                   # noqa: E402
import line_labels as LL                          # noqa: E402
from app import db                                # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_hotfix36_line_labels import _doc, _labels   # noqa: E402

FMT = {"source": "LEGEND", "insulation": ["H", "N", "P"], "diameter_prefix": "DN"}


def test_parse_spec_user_definition():
    assert LL.parse_spec("DN800H LBB1", FMT) == {"size": "DN 800", "diameter_prefix": "DN", "insulation": "H",
                                                 "design_code": "LBB1", "raw": "DN800H LBB1"}
    assert LL.parse_spec("DN 800 H LBB1", FMT)["size"] == "DN 800"
    p = LL.parse_spec("DN150NGKB4", FMT)                       # 붙여 쓴 꼴 — 범례 글자가 있어야 가른다
    assert (p["size"], p["insulation"], p["design_code"]) == ("DN 150", "N", "GKB4")
    assert LL.parse_spec("NOTE 2 DN50H LBB1", FMT)["size"] == "DN 50"
    assert LL.parse_spec("DN XX H LBB1", FMT)["size"] == "DN XX"
    assert LL.parse_spec("DN200H LAB3 11LAB21", FMT)["design_code"] == "LAB3"   # 꼬리 라인 번호는 코드가 아니다
    assert LL.parse_spec("", FMT)["size"] == "" and LL.parse_spec("LBB1", FMT)["size"] == ""


def test_generic_fallback_does_not_split_a_glued_code():
    g = LL.parse_spec("DN150NGKB4", None)
    assert g["size"] == "DN 150" and g["insulation"] == "" and g["design_code"] == "NGKB4"
    assert LL.parse_spec("DN800 H LBB1", None)["insulation"] == "H"   # 홀로 선 한 글자만


def _legend(tmp_path, example_as_text: bool):
    doc = pymupdf.open(); page = doc.new_page(width=800, height=600)
    page.insert_text((100, 80), "PIPING INSULATION", fontsize=8)
    y = 95
    for letter, meaning in (("H", "INSULATION FOR HEAT CONSERVATION"),
                            ("P", "INSULATION FOR PERSONAL PROTECTION"), ("N", "NO INSULATION")):
        for tok, dx in (("-", 0), (letter, 6), (":", 12), (meaning, 18)):
            page.insert_text((100 + dx, y), tok, fontsize=8)
        y += 10
    if example_as_text:
        page.insert_text((100, 140), "DN250H LAB1", fontsize=8)
    path = tmp_path / "legend.pdf"; doc.save(path); doc.close()
    return pidcache.load_pages(str(path))[1]


def test_insulation_letters_come_from_the_legend_and_prefix_from_its_example(tmp_path):
    fmt = LL.learn_flag_format(_legend(tmp_path, True))
    assert fmt["source"] == "LEGEND" and fmt["insulation"] == ["H", "N", "P"]
    assert fmt["diameter_prefix"] == "DN" and fmt["prefix_source"] == "LEGEND"


def test_prefix_is_learned_from_the_drawing_when_the_legend_draws_its_example(tmp_path):
    fmt = LL.learn_flag_format(_legend(tmp_path, False))          # QFE — 예시가 획이라 글자 없음
    assert fmt["source"] == "LEGEND" and fmt["diameter_prefix"] == ""
    pages, runs = _doc(tmp_path)
    labels = {pc.page_no: _labels(pc, runs[pc.page_no]) for pc in pages}
    out = LL.learn_prefix_from_labels(labels, fmt)
    assert out["diameter_prefix"] == "DN" and out["prefix_source"] == "BODY" and out["prefix_pages"] == 2
    one = LL.learn_prefix_from_labels({1: labels[1]}, fmt)        # 한 장뿐이면 배우지 않는다
    assert one["diameter_prefix"] == ""
    assert LL.learn_flag_format([])["source"] == "GENERIC"


def test_attach_writes_line_no_and_line_size_as_the_user_defined(tmp_path):
    from app import pipeline as P
    pages, runs = _doc(tmp_path)
    labels = {pc.page_no: _labels(pc, runs[pc.page_no]) for pc in pages}
    run = ("H", runs[1][0][1], 40.0, 800.0)
    r = P.Row(key="k", tab=P.TAB_FIELD, page_no=1, drawing_no="D", type="PIT", qty=1,
              rect=(300, 40, 340, 60), evidence={"axis": {"ev": {"run": run}}})
    facts = P._attach_line_numbers([r], labels, 0.8, line_fmt=LL.learn_flag_format([]))
    assert r.line_no == "12LBB50" and r.line_size == "DN 800"
    e = r.evidence["line"]
    assert e["pipe_no"] == "BR010" and e["insulation"] == "H" and e["design_code"] == "LBB1"
    assert facts["sized"] == 1 and facts["format"]["prefix_source"] == "BODY"


def test_sources_keep_the_letters_out_of_the_code():
    src = (ROOT / "app" / "engine" / "line_labels.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for fn in ("parse_spec", "learn_flag_format", "learn_prefix_from_labels"):
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn)
        consts = {c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        assert not consts & {"DN", "H", "P", "N", "NPS"}, (fn, consts)
    assert "line_size" in db.EDITABLE
    psrc = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    fp = next(n for n in ast.walk(ast.parse(psrc)) if isinstance(n, ast.FunctionDef) and n.name == "fingerprint")
    assert "line_size" not in ast.get_source_segment(psrc, fp)
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    cols = js[js.index("const COLS = ["):js.index("];", js.index("const COLS = ["))]
    assert cols.index('["line_no"') < cols.index('["line_size", "Line Size"') < cols.index('["valve_type"')
