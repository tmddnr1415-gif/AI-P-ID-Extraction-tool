"""hotfix31 — AIT 가 식별 안 되던 것 · PIT/PI 한 라인 규칙 (QFE 화면).

  ① SUCCEEDING 열을 `( ) X` 칸으로 인쇄한 범례(FICHTNER 양식 — UAD · QFE)도
     PDF 경로의 `isa_table.derive` 가 읽는다.  `TYPICAL SYMBOL` 머리줄로 읽힌
     문서는 이 갈래에 오지 않는다 (AL NOUF1 · TC2 · SADARA 불변의 근거).
  ② 그 표로 `AIT` 가 `A` + `IT` 로 풀린다 — 그래야 앵커가 된다.
  ③ 같은 태그에 `PIT` 와 `PI` 가 있으면 `PIT` 가 남고 `PI` 는 접힌다 (기록은 남는다).
  ④ 같은 태그에 `PI` 만 있으면 게이지 — TYPE 표기 `PG`, `values["type"]` 은 `PI`.
  ⑤ 태그가 없는 행은 접지도 게이지로 부르지도 않는다 (2급 문서 불변).
  ⑥ PDF 와 DXF 가 같은 함수 하나를 부른다 (규칙 두 벌 금지).
"""
from __future__ import annotations

import ast
import pathlib
import sys

import pymupdf
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
import isa_table                 # noqa: E402
import pidcache                  # noqa: E402
from app import pipeline as P    # noqa: E402

R = pymupdf.Rect


# ---------------------------------------------------------------- ① ② ⑥
def _cell_legend(tmp_path):
    """FIRST LETTER 열 + `( ) X` 칸 한 줄 — TYPICAL SYMBOL 머리줄은 없다."""
    doc = pymupdf.open(); page = doc.new_page(width=800, height=600)
    page.insert_text((60, 60), "FIRST LETTER", fontsize=10)
    rows = [("A", "ANALYSIS"), ("P", "PRESSURE"), ("T", "TEMPERATURE"), ("L", "LEVEL")]
    for i, (k, w) in enumerate(rows):
        y = 100 + i * 20
        page.insert_text((60, y), k, fontsize=9)
        page.insert_text((100, y), w, fontsize=9)
        page.insert_text((260, y), k, fontsize=9)    # 첫 태그 열이 글자를 되풀이한다
    # 칸 한 줄 (x 로 나란히) · 그 위에 뜻
    cells = [("I", "INDICATOR"), ("T", "TRANSMITTER"), ("S", "SWITCH"), ("AL", "ALARM LOW")]
    for i, (k, meaning) in enumerate(cells):
        x = 400 + i * 90
        page.insert_text((x, 300), meaning, fontsize=7)
        page.insert_text((x, 330), f"( ) {k}", fontsize=9)
    path = tmp_path / "cells.pdf"; doc.save(path); doc.close()
    _d, pages = pidcache.load_pages(str(path))
    return pages


def test_cell_layout_fills_succeeding_and_ait_decomposes(tmp_path):
    isa = isa_table.derive(_cell_legend(tmp_path))
    assert isa.source == "LEGEND"
    assert "( ) X" in isa.note
    assert isa.succeeding["I"] == ("INDICATOR",)
    assert isa.succeeding["T"] == ("TRANSMITTER",)
    assert isa.succeeding["AL"] == ("ALARM", "LOW") and isa.succeeding["A"] == ("ALARM", "LOW")
    assert isa.decompose("AIT") == ("A", "IT")
    assert isa.decompose("AI") == ("A", "I")
    assert isa.decompose("PIT") == ("P", "IT")


def test_split_tokens_read_the_same_as_one_piece():
    one = [(R(10, 100, 40, 108), "( ) AL"), (R(10, 80, 40, 88), "ALARM LOW"),
           (R(60, 100, 90, 108), "( ) T"), (R(60, 84, 110, 92), "TRANSMITTER"),
           (R(120, 100, 150, 108), "( ) I"), (R(118, 84, 160, 92), "INDICATOR")]
    split = [(R(10, 100, 16, 108), "("), (R(18, 100, 24, 108), ")"), (R(28, 100, 40, 108), "AL"),
             (R(10, 80, 40, 88), "ALARM LOW"),
             (R(60, 100, 90, 108), "()T"), (R(60, 84, 110, 92), "TRANSMITTER"),
             (R(120, 100, 126, 108), "("), (R(128, 100, 150, 108), ") I"), (R(118, 84, 160, 92), "INDICATOR")]
    assert isa_table.succeeding_from_cells(one) == isa_table.succeeding_from_cells(split)
    assert isa_table.succeeding_from_cells(one)["I"] == ("INDICATOR",)


def test_fewer_than_three_cells_is_not_the_table():
    ws = [(R(10, 100, 40, 108), "( ) A"), (R(60, 100, 90, 108), "( ) B")]
    assert isa_table.succeeding_from_cells(ws) == {}


def test_a_document_with_the_typical_symbol_heading_never_reaches_the_cells():
    """머리줄로 읽힌 표는 그대로다 — AL NOUF1 · TC2 · SADARA 불변의 근거."""
    src = (ROOT / "app" / "engine" / "isa_table.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    derive = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "derive")
    calls = [n for n in ast.walk(derive) if isinstance(n, ast.Call)
             and getattr(n.func, "id", "") == "succeeding_from_cells"]
    assert len(calls) == 1
    guard = next(n for n in ast.walk(derive) if isinstance(n, ast.If)
                 and any(n2 is calls[0] for n2 in ast.walk(n)))
    assert ast.unparse(guard.test) == "not succeeding"


def test_dxf_path_calls_the_same_function():
    src = (ROOT / "app" / "dxf_pipeline.py").read_text(encoding="utf-8")
    assert "isa_table.succeeding_from_cells(" in src
    assert "_SUCC_CELL" not in src


# ---------------------------------------------------------------- ③ ④ ⑤
TABLE = isa_table.IsaTable(
    first={"P": ("PRESSURE", "OR", "VACUUM"), "T": ("TEMPERATURE",), "A": ("ANALYSIS",)},
    succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",), "C": ("CONTROLLER",)},
    page_no=4, note="test")


def _row(key, anchor, tag, page=6, y=100):
    return P.Row(key=key, tab=P.TAB_FIELD, page_no=page, drawing_no="D", type=anchor,
                 qty=1, rect=(100, y, 160, y + 20), tag_no=tag,
                 evidence={"anchor": anchor, "tag_no": {"value": tag}})


def test_pit_wins_over_pi_on_the_same_tag_and_the_fold_is_recorded():
    pit = _row("k1", "PIT", "11MBP01CP103", y=140)
    pi = _row("k2", "PI", "11MBP01CP103", y=100)
    rows = [pi, pit]
    facts, folded = P._fold_readouts(rows, TABLE)
    assert folded == {"k2"}
    assert pit.evidence["readout_folded"][0]["anchor"] == "PI"
    assert "PI 표시기" in pit.remark and "PIT" in pit.remark
    assert facts["folded"][0]["kept"] == "PIT" and facts["folded"][0]["readout"] == "PI"
    assert "gauge" not in pit.evidence and "gauge" not in pi.evidence
    assert P.type_display({"type": "PIT"}, pit.evidence) == "PIT"


def test_tit_ti_is_the_same_rule():
    tit = _row("a", "TIT", "11MBP01CT003", y=140)
    ti = _row("b", "TI", "11MBP01CT003", y=100)
    _facts, folded = P._fold_readouts([tit, ti], TABLE)
    assert folded == {"b"}


def test_a_lone_pi_is_a_gauge_in_display_only():
    pi = _row("k3", "PI", "11MBP01CP104")
    facts, folded = P._fold_readouts([pi], TABLE)
    assert not folded and facts["gauges"] == 1
    assert pi.evidence["gauge"]["display"] == "PG"
    assert pi.evidence["gauge"]["word"] == "PRESSURE GAUGE"
    assert pi.type == "PI"                                   # 측정 단위는 그대로
    assert P.type_display({"type": "PI"}, pi.evidence) == "PG"
    ti = _row("k4", "TI", "11MBP01CT009")
    P._fold_readouts([ti], TABLE)
    assert P.type_display({"type": "TI"}, ti.evidence) == "TG"


def test_same_tag_on_another_sheet_is_another_line():
    pit = _row("k1", "PIT", "X", page=6)
    pi = _row("k2", "PI", "X", page=7)
    _f, folded = P._fold_readouts([pit, pi], TABLE)
    assert not folded and pi.evidence["gauge"]["display"] == "PG"


def test_rows_without_a_tag_are_left_alone():
    """2급 문서 — 같은 라인인지 도면이 말하지 않는다.  AL NOUF1 · TC2 불변의 근거."""
    pit = _row("k1", "PIT", "", y=140); pi = _row("k2", "PI", "", y=100)
    facts, folded = P._fold_readouts([pi, pit], TABLE)
    assert not folded and facts["gauges"] == 0 and "gauge" not in pi.evidence
    assert P.type_display({"type": "PI"}, pi.evidence) == "PI"


def test_no_isa_table_folds_nothing():
    pit = _row("k1", "PIT", "X"); pi = _row("k2", "PI", "X")
    facts, folded = P._fold_readouts([pi, pit], None)
    assert not folded and "ISA" in facts["note"]


def test_gauge_naming_can_be_switched_off_but_the_fold_stays(monkeypatch):
    monkeypatch.setitem(P.CFG.data.setdefault("description", {}), "gauge_indicator",
                        {"enabled": False})
    pit = _row("k1", "PIT", "X", y=140); pi = _row("k2", "PI", "X", y=100); lone = _row("k3", "TI", "Y")
    facts, folded = P._fold_readouts([pi, pit, lone], TABLE)
    assert folded == {"k2"} and facts["gauges"] == 0 and "gauge" not in lone.evidence


def test_the_fold_lives_in_one_place_after_the_tags():
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert src.count("_fold_readouts(rows, isa)") == 1
    assert src.index("_attach_tags(rows, pages") < src.index("_fold_readouts(rows, isa)")
    assert '"readouts"' in (ROOT / "app" / "db.py").read_text(encoding="utf-8")
