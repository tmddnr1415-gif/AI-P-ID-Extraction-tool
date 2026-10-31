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


# ---------------------------------------------------------------------------
# 사람이 지정한 승수 — 읽는 곳이 둘이면 갈린다 (현장 결함)
#
# `app/main.py` 의 `_user_multipliers` 는 **프로젝트에 묶인 분석에서만**
# `{"table": …, "who": …}` 를 주고, 안 묶였으면 `{}` 를 준다.  DXF 경로가 그
# 바깥 dict 를 `{유닛: 배수}` 로 착각해 읽어서, **프로젝트를 골라 올린 DXF 분석이
# 전부** `KeyError: 'value'` 로 죽었다.  회귀 하네스는 이 인자를 안 넘기고
# 55회차 업로드 시험은 프로젝트 없이 올려서 둘 다 그 자리를 안 지났다.
# ---------------------------------------------------------------------------

def test_user_multipliers_are_read_in_one_place():
    """두 경로가 같은 접근자를 쓴다 — DXF 쪽에 사본이 없다."""
    src = (ROOT / "app" / "dxf_pipeline.py").read_text(encoding="utf8")
    assert "P.user_multiplier_tables(" in src, "DXF 경로가 공용 접근자를 안 쓴다"
    assert '"value"' not in src.split("user_multiplier_tables")[0][-400:], \
        "DXF 경로에 승수를 제 식으로 읽는 사본이 남아 있다"


def test_the_shape_the_server_actually_sends_is_accepted():
    """서버가 실제로 넘기는 세 모양이 전부 통해야 한다."""
    from app import pipeline as P
    assert P.user_multiplier_tables(None) == ({}, {})
    # 프로젝트에 묶였지만 아직 아무도 지정하지 않은 상태 — 현장에서 죽던 모양
    assert P.user_multiplier_tables({"table": {}, "who": {}}) == ({}, {})
    assert P.user_multiplier_tables(
        {"table": {"00": 4}, "who": {"00": "누구 · 2026-09-27"}}) == (
        {"00": 4}, {"00": "누구 · 2026-09-27"})


# ---------------------------------------------------------------------------
# 호로 그린 버블 — 마주 본 캡 둘이 버블 하나다 (9차 DXF 피드백 2번)
# ---------------------------------------------------------------------------

def _stadium_sheet(tmp_path, *, vertical=False):
    """반원 캡 둘 + 옆면으로 그린 버블 하나와 그 안의 글자."""
    import ezdxf
    doc = ezdxf.new("R2018")
    msp = doc.modelspace()
    r, gap = 4.0, 16.0
    if vertical:
        msp.add_arc((0, 0), r, 0, 180)
        msp.add_arc((0, -gap), r, 180, 360)
        msp.add_text("PIT").set_placement((0, -gap / 2))
    else:
        msp.add_arc((0, 0), r, 90, 270)
        msp.add_arc((gap, 0), r, 270, 90)
        msp.add_text("PIT").set_placement((gap / 2, 0))
    f = tmp_path / ("v.dxf" if vertical else "h.dxf")
    doc.saveas(f)
    return f


def test_opposing_arcs_become_one_bubble(tmp_path):
    """호 하나가 아니라 **짝**이 버블이다 — 가로든 세로든."""
    from app.engine import dxf_reader as R
    for vertical in (False, True):
        sheets, _m = R.open_set(_stadium_sheet(tmp_path, vertical=vertical))
        loops = [l for l in R.loops(sheets[0]) if l.kind == "ARC"]
        assert len(loops) == 1, f"호 짝이 버블 하나로 안 섰다 ({loops})"
        w = loops[0].rect[2] - loops[0].rect[0]
        h = loops[0].rect[3] - loops[0].rect[1]
        assert {round(w), round(h)} == {24, 8}, (w, h)


def test_a_lone_arc_still_gives_its_own_circle(tmp_path):
    """짝이 없는 호는 제 원으로 둔다 — 버리지 않는다."""
    import ezdxf
    from app.engine import dxf_reader as R
    doc = ezdxf.new("R2018")
    doc.modelspace().add_arc((0, 0), 4.0, 0, 90)
    f = tmp_path / "lone.dxf"
    doc.saveas(f)
    sheets, _m = R.open_set(f)
    loops = [l for l in R.loops(sheets[0]) if l.kind == "ARC"]
    assert len(loops) == 1
    assert round(loops[0].rect[2] - loops[0].rect[0]) == 8


def test_only_is_for_drawing_not_for_analysis():
    """`open_set(only=)` 은 **그림**에만 쓴다 — 분석이 쓰면 장 종류·범례가 흔들린다."""
    src = (ROOT / "app" / "dxf_pipeline.py").read_text(encoding="utf8")
    assert "only=" not in src, "분석이 open_set(only=) 을 쓴다"
    main = (ROOT / "app" / "main.py").read_text(encoding="utf8")
    assert "open_set(path, only=page_no)" in main, "그림 경로가 한 장만 파지 않는다"


# ---------------------------------------------------------------------------
# 경보 신호는 계기가 아니다 (9차 DXF 피드백)
# ---------------------------------------------------------------------------

def _isa_for_alarm():
    from app.engine import isa_table
    return isa_table.IsaTable(
        first={"L": ("LEVEL",), "A": ("ANALYSIS",), "T": ("TEMPERATURE",),
               "P": ("PRESSURE",), "PD": ("PRESSURE", "DIFFERENTIAL")},
        succeeding={"S": (), "A": (), "I": (), "T": (), "C": (), "Z": ()})


def test_alarm_tags_are_not_instruments():
    """뒤 글자에 경보 글자가 있으면 경보다 — 판정은 그 도면 ISA 표가 한다."""
    from app import pipeline as P
    isa = _isa_for_alarm()
    for t in ("LSA", "PDIA", "TIA", "PIA", "LIA", "TICA", "LICAZ"):
        assert P.is_alarm_tag(t, isa), t


def test_the_leading_a_is_a_measured_variable_not_an_alarm():
    """`AIT` 의 `A` 는 머리(ANALYSIS)다 — 계기로 남는다."""
    from app import pipeline as P
    isa = _isa_for_alarm()
    for t in ("AIT", "AT", "LS", "TIT", "PIT", "LIT", "PDIT"):
        assert not P.is_alarm_tag(t, isa), t


def test_no_isa_table_means_no_alarm_judgement():
    """표가 없으면 판정하지 않는다 — 지어내지 않는다."""
    from app import pipeline as P
    assert P.is_alarm_tag("LSA", None) is False


def test_a_printed_valve_tag_is_the_type_even_without_a_body():
    """몸체를 못 읽어도 도면이 버블에 붙인 이름이 TYPE 이다 (MOV·PSV·XV…)."""
    from app import pipeline as P
    assert P.type_display({"type": ""}, {"tag": "PSV"}) == "PSV"
    assert P.type_display({"type": "GATE"}, {"tag": "MOV"}) == "MOV(GATE)"
    assert P.type_display({"type": ""}, {}) == ""          # 근거가 없으면 비운다


# --------------------------------------------------------------------------
# 56회차 — 흰 종이에서 읽히는 밝기로 (현장 보고: "PIT · LIT 가 안 보인다")
# --------------------------------------------------------------------------

def test_paper_is_left_alone():
    """거의 흰 픽셀은 종이다 — 건드리지 않는다."""
    import numpy as np
    from PIL import Image
    import io as _io
    from app.engine import dxf_render
    a = np.full((8, 8, 3), 255, dtype="uint8")
    buf = _io.BytesIO(); Image.fromarray(a).save(buf, format="PNG")
    out = np.asarray(Image.open(_io.BytesIO(dxf_render.darken_ink(buf.getvalue()))))
    assert (out == 255).all()


def test_light_ink_comes_down_and_keeps_its_hue():
    """노랑·하늘색은 어두워지고 **색상은 남는다** — 층 색으로 읽는 값이다."""
    import numpy as np
    from PIL import Image
    import io as _io
    from app.engine import dxf_render
    a = np.zeros((2, 3, 3), dtype="uint8")
    a[:, 0] = (255, 255, 0)      # 노랑
    a[:, 1] = (0, 255, 255)      # 하늘색
    a[:, 2] = (0, 0, 0)          # 이미 어두운 잉크
    buf = _io.BytesIO(); Image.fromarray(a).save(buf, format="PNG")
    out = np.asarray(Image.open(_io.BytesIO(dxf_render.darken_ink(buf.getvalue()))))
    y, c, k = out[0, 0], out[0, 1], out[0, 2]
    assert y[0] == y[1] and y[2] == 0          # 노랑 그대로 (R=G, B=0)
    assert c[0] == 0 and c[1] == c[2]          # 하늘색 그대로
    assert max(y) < 255 and max(c) < 255       # 내려왔다
    assert tuple(k) == (0, 0, 0)               # 검정은 한 칸도 안 움직인다


def test_the_whole_picture_is_fixed_not_the_entities():
    """★ 엔티티 단계 덮어쓰기는 **글자에 닿지 않았다** (56회차에 뒤집은 것).

    `Frontend.push_property_override_function` 은 호출되는데(UAD p6 에서 TEXT
    221 · MTEXT 101) 그려진 글자 색이 한 픽셀도 안 바뀐다.  그래서 고치는 자리는
    그림이고, 그 사실이 코드에 남아 있어야 같은 길을 또 파지 않는다.
    """
    import inspect
    from app.engine import dxf_render
    body = inspect.getsource(dxf_render.render_png)
    assert "push_property_override_function" not in body   # 그 길은 닫혀 있다
    assert "darken_ink(" in body                           # 고치는 자리는 그림이다
    # 실패 기록은 코드에 남는다 — 같은 길을 또 파지 않게.
    assert "push_property_override_function" in dxf_render.darken_ink.__doc__


def test_a_star_inside_the_symbol_rect_still_counts():
    """56회차 — **별표는 그 심볼의 이름이 아니다.**

    심볼 사각형 안에 든 낱말을 별표 후보에서 빼던 장치가 진짜 별표를 삼켰다.
    도면은 별표를 **버블 모서리**에 찍고 그 자리는 바깥 사각형 **안**이다
    (30회차 §10-10 의 반대 방향).  UAD p30 실측: `LS` 12행 전부가 자기 별표를
    잃고 SCT 로 나갔고, 같은 장 `PI` 24행은 별표가 사각형 밖이라 VENDOR 였다.

    `stars` 는 `STAR_RE`(`*` · `(*)`)만 담으므로 라벨이 섞일 길이 애초에 없다.
    """
    import inspect
    from app import dxf_pipeline
    src = inspect.getsource(dxf_pipeline._sheet_rows)
    i = src.index("def scope_for(")
    block = src[i:i + 1400]
    assert "not in own_words" not in block          # 그 장치는 별표에 안 건다
    assert "stars if _overlap" in block             # 겹치면 그 심볼의 별표다
    assert "STAR_RE" in inspect.getsource(dxf_pipeline)
