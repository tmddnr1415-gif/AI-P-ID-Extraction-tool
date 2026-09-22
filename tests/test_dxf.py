"""DXF 입력 경로 (55회차).

무엇을 못박나:
  * 블록 이름 · 레이어 이름을 코드에 적지 않는다 (AST) — 뜻은 범례에서, 거를 층은
    레이어 표 플래그에서 온다 (§9).
  * 버전 셋(AC1032 · AC1027 · AC1024)이 전부 열린다 · zip 하나 · 개별 파일 여러 장.
  * 레이어 표가 끈 층은 낱말·심볼에 `hidden` 이 붙는다.
  * 속성 역할은 값이 정한다 — TYPE 은 태그 역할 속성과 짝일 때만.
  * 폴백(닫힌 도형 + 안의 글자) · 속성 없는 블록 · 한 장 실패해도 나머지는 계속.
  * PDF 경로: `pipeline.analyse` 는 DXF 가 아니면 예전 갈래로 간다.
"""
from __future__ import annotations

import ast
import io
import pathlib
import sys
import zipfile

import ezdxf
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.engine import dxf_reader as R          # noqa: E402

# 이 문서(UAD DXF)가 쓰는 이름들 — **코드에 있으면 안 된다**
FORBIDDEN = ("INST_LOCAL", "MOUNTED ON MCP", "LOCAL_MOUNTED", "AS_INST", "AS_LAB",
             "BREAKER_SCOPE", "PIP MOTOR", "Flow Arrow", "Gate Valve", "Ball Valve",
             "REV.4", "REV.5", "HIDE", "AS_NONPLOT", "BID_NOTE", "PDF_Geometry",
             "TargetObject.Type", "LoopNumber", "PNPAttribute")


def _string_literals(path: pathlib.Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node.value


@pytest.mark.parametrize("module", ["app/engine/dxf_reader.py", "app/dxf_pipeline.py",
                                    "app/engine/dxf_render.py"])
def test_no_block_or_layer_names_in_code(module):
    lits = list(_string_literals(ROOT / module))
    hits = [(w, lit[:40]) for lit in lits for w in FORBIDDEN if w.lower() in lit.lower()]
    assert not hits, f"{module} 가 이 문서의 이름을 외웠다: {hits[:5]}"


# ── 합성 DXF ────────────────────────────────────────────────────────────

def _make(version: str, hidden_layer=False, with_attr=True, exploded=False,
          break_it=False) -> bytes:
    doc = ezdxf.new(version)
    msp = doc.modelspace()
    doc.layers.add("Instrument")
    if hidden_layer:
        lay = doc.layers.add("REV.9")
        lay.off()
    # 종이 틀 — 시트를 덮는 블록 · 타이틀 캡션 아래 칸
    fr = doc.blocks.new("FRAME")
    fr.add_lwpolyline([(0, 0), (841, 0), (841, 594), (0, 594)], close=True)
    fr.add_text("PROJECT DWG NO.", height=2).set_placement((696, 37))
    fr.add_text("1A5J-00ABC10-M05-0001", height=2.5).set_placement((707, 31))
    fr.add_text("REV.", height=2).set_placement((812, 37))
    fr.add_text("3", height=2.5).set_placement((814, 31))
    fr.add_text("DRAWING TITLE", height=2).set_placement((696, 53))
    fr.add_text("P&ID FOR TEST", height=2.5).set_placement((728, 49))
    msp.add_blockref("FRAME", (0, 0))
    # 계기 블록 — 원 + 속성 둘
    b = doc.blocks.new("INSTR")
    b.add_circle((0, 0), 4)
    b.add_attdef("KIND_ATTR", (0, 1), height=2)
    b.add_attdef("CODE_ATTR", (0, -3), height=2)
    for i, (t, c) in enumerate((("PI", "00AAA01CP001"), ("TI", "00AAA02CT001"), ("LIT", "00AAA03CL001"))):
        ref = msp.add_blockref("INSTR", (100 + 30 * i, 300), dxfattribs={"layer": "Instrument"})
        if with_attr:
            ref.add_attrib("KIND_ATTR", t, (100 + 30 * i, 301))
            ref.add_attrib("CODE_ATTR", c, (100 + 30 * i, 297))
    if exploded:
        msp.add_circle((300, 300), 4)
        msp.add_text("PT", height=2).set_placement((300, 300), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)
    if hidden_layer:
        msp.add_text("9", height=2, dxfattribs={"layer": "REV.9"}).set_placement((50, 50))
    buf = io.StringIO()
    doc.write(buf)
    raw = buf.getvalue().encode("utf-8")
    if break_it:
        raw = raw[: len(raw) // 2]
    return raw


@pytest.mark.parametrize("version", ["AC1032", "AC1027", "AC1024"])
def test_three_versions_open(tmp_path, version):
    f = tmp_path / f"001. sheet_{version}.dxf"
    f.write_bytes(_make(version))
    sheets, meta = R.open_set(f)
    assert len(sheets) == 1 and not sheets[0].error
    assert sheets[0].version == version
    assert round(sheets[0].width) == 841 and round(sheets[0].height) == 594


def test_zip_and_loose_files_read_the_same(tmp_path):
    a, b = _make("AC1032"), _make("AC1027")
    d = tmp_path / "loose"; d.mkdir()
    (d / "002. two.dxf").write_bytes(b)
    (d / "001. one.dxf").write_bytes(a)
    (d / "readme.txt").write_text("skip me")
    z = tmp_path / "set.zip"
    with zipfile.ZipFile(z, "w") as zz:
        zz.writestr("sub/002. two.dxf", b)
        zz.writestr("sub/001. one.dxf", a)
        zz.writestr("sub/notes.txt", "skip")
    s1, m1 = R.open_set(d)
    s2, m2 = R.open_set(z)
    assert [s.file for s in s1] == [s.file for s in s2] == ["001. one.dxf", "002. two.dxf"]
    assert m1["order_rule"] == m2["order_rule"] == "파일명 앞 번호"
    assert m1["skipped"] == ["readme.txt"] and m2["skipped"] == ["sub/notes.txt"]
    assert R.is_dxf_input(z) and R.is_dxf_input(d)


def test_one_broken_sheet_does_not_stop_the_rest(tmp_path):
    z = tmp_path / "set.zip"
    with zipfile.ZipFile(z, "w") as zz:
        zz.writestr("001. good.dxf", _make("AC1032"))
        zz.writestr("002. bad.dxf", b"this is not a dxf at all\n" * 20)
        zz.writestr("003. good.dxf", _make("AC1024"))
    sheets, _ = R.open_set(z)
    assert [bool(s.error) for s in sheets] == [False, True, False]


def test_hidden_layers_come_from_the_layer_table(tmp_path):
    f = tmp_path / "001. s.dxf"; f.write_bytes(_make("AC1032", hidden_layer=True))
    sh, _ = R.open_set(f)
    sh = sh[0]
    assert "REV.9" in sh.hidden_layers
    hidden = [w for w in R.words(sh) if w.hidden]
    assert [w.text for w in hidden] == ["9"]


def test_title_fields_read_the_cell_under_the_caption(tmp_path):
    f = tmp_path / "001. s.dxf"; f.write_bytes(_make("AC1032"))
    sh, _ = R.open_set(f)
    t = R.title_fields(sh[0])
    assert t["drawing_no"] == "1A5J-00ABC10-M05-0001"
    assert t["rev"] == "3"
    assert t["title"] == "P&ID FOR TEST"


def test_symbol_rect_excludes_attribute_text(tmp_path):
    f = tmp_path / "001. s.dxf"; f.write_bytes(_make("AC1032"))
    sh, _ = R.open_set(f)
    syms = [s for s in R.symbols(sh[0]) if s.block == "INSTR"]
    assert len(syms) == 3
    for s in syms:
        assert abs((s.rect[2] - s.rect[0]) - 8.0) < 0.5, "원만의 사각형이어야 한다"
        assert s.attrs["KIND_ATTR"] in ("PI", "TI", "LIT")


def test_attribute_roles_need_a_tag_partner():
    from app import dxf_pipeline as D
    import types

    class _Isa:
        def decompose(self, t):
            return (t[0], t[1:]) if t in ("PI", "TI", "LIT", "AG", "UG") else None

    _no = [0]

    def sheet(attrs_list):
        _no[0] += 1
        sh = types.SimpleNamespace(error="", no=_no[0], _cache={})
        sh._cache["symbols"] = [R.Symbol("B", (0, 0, 1, 1), (0, 0, 1, 1), "0", a, 0.0)
                                for a in attrs_list]
        return sh
    # TYPE 값이 풀리지만 짝 속성이 없는 블록(스코프 선) → TYPE 역할이 아니다
    lone = [sheet([{"SIDE": "AG"}, {"SIDE": "UG"}, {"SIDE": "AG"}]),
            sheet([{"SIDE": "AG"}, {"SIDE": "UG"}])]
    roles = D.attribute_roles(lone, _Isa())
    assert "SIDE" not in roles["type"]
    paired = [sheet([{"K": "PI", "C": "00AAA01CP001"}, {"K": "TI", "C": "00AAA02CT001"}]),
              sheet([{"K": "LIT", "C": "00AAA03CL001"}, {"K": "PI", "C": "00AAA04CP001"}])]
    roles = D.attribute_roles(paired, _Isa())
    assert "K" in roles["type"] and "C" in roles["tag"]


def test_pipeline_routes_dxf_and_leaves_pdf_alone(tmp_path):
    from app import pipeline as P
    src = ast.parse((ROOT / "app" / "pipeline.py").read_text(encoding="utf-8"))
    fn = next(n for n in ast.walk(src) if isinstance(n, ast.FunctionDef) and n.name == "analyse")
    text = ast.get_source_segment((ROOT / "app" / "pipeline.py").read_text(encoding="utf-8"), fn)
    assert "is_dxf_input" in text and "dxf_pipeline.analyse" in text
    # 갈림 뒤의 본문은 옛 그대로 — `_own_config` 안에서 `_analyse` 를 부른다
    assert "with _own_config():" in text and "_analyse(pdf_path" in text
    assert not R.is_dxf_input(tmp_path / "x.pdf")


def test_geometry_fallback_and_no_attr_block_still_count(tmp_path):
    """속성 없는 계기 블록은 2급, 닫힌 원 + 안의 글자는 기하 폴백."""
    from app import dxf_pipeline as D
    f = tmp_path / "001. s.dxf"; f.write_bytes(_make("AC1032", with_attr=False, exploded=True))
    sh, _ = R.open_set(f)
    sh = sh[0]
    loops = [l for l in R.loops(sh) if l.kind == "CIRCLE"]
    assert len(loops) == 1
    words = R.words(sh)
    inside = [w for w in words if D._inside(D._center(w.rect), loops[0].rect, pad=0.3)]
    assert [w.text for w in inside] == ["PT"]
    syms = [s for s in R.symbols(sh) if s.block == "INSTR"]
    assert all(not any(s.attrs.values()) for s in syms)
