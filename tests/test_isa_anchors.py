"""무엇이 계기 태그인가를 **그 도면의 ISA 문자표**가 답한다 (50회차 · §9 ①).

지금까지는 `anchors.type_map` 24종을 손으로 적어 정했고, 그래서 도면이 버블에
인쇄한 `AIT`·`PP`·`ZS`·`PDI` 가 행이 되지 못했다 (실측 AL NOUF1 32 · TC2 25).
범례는 그 답을 **이미 인쇄하고 있다** — FIRST LETTER 열이 측정 변수를,
SUCCEEDING LETTERS 열이 기능을 정의한다.

이 시험이 지키는 것 넷:

  ① 표로 풀리는 낱말은 앵커가 된다 (`AIT`)
  ② 표가 정의하지 않은 글자가 하나라도 있으면 앵커가 아니다 (`NOTE`·`ZSO`)
  ③ 설정이 답하는 낱말은 설정이 이긴다 (`TT → TIT`)
  ④ 스위치를 끄면 **24종 사전만 쓰던 때와 정확히 같아진다**
"""
from __future__ import annotations

import ast
import pathlib
import sys

import pymupdf
import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))
import detect_symbols as ds      # noqa: E402
import isa_table                 # noqa: E402
import pidcache                  # noqa: E402


# 범례가 인쇄한 그대로의 최소 표 — 지어낸 글자가 없다.
TABLE = isa_table.IsaTable(
    first={"A": ("ANALYSIS",), "P": ("PRESSURE", "OR", "VACUUM"),
           "PD": ("PRESSURE", "DIFFERENTIAL"), "T": ("TEMPERATURE",),
           "Z": ("POSITION",), "L": ("LEVEL",)},
    succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",), "S": ("SWITCH",),
                "P": ("TEST", "POINT"), "C": ("CONTROLLER",)},
    page_no=3, note="test")


def _stadium(page, x0, y0, w, h):
    r = h / 2
    sh = page.new_shape()
    sh.draw_line((x0 + r, y0), (x0 + w - r, y0)); sh.finish(width=0.3)
    sh.draw_line((x0 + r, y0 + h), (x0 + w - r, y0 + h)); sh.finish(width=0.3)
    sh.commit()
    for cx, side in ((x0 + r, -1), (x0 + w - r, 1)):
        sh = page.new_shape()
        sh.draw_sector((cx, y0 + r), (cx, y0), 180 if side < 0 else -180,
                       fullSector=False)
        sh.finish(width=0.3, closePath=False); sh.commit()


@pytest.fixture
def sheet(tmp_path):
    """버블 넷 — 사전에 있는 것 하나, 표로만 풀리는 것 둘, 안 풀리는 것 하나."""
    doc = pymupdf.open(); page = doc.new_page(width=700, height=400)
    for i, word in enumerate(("TT", "AIT", "PP", "NOTE")):
        x = 100 + i * 120
        _stadium(page, x, 150, 68, 22)
        page.insert_text((x + 16, 166), word, fontsize=9)
    path = tmp_path / "isa.pdf"; doc.save(path); doc.close()
    _d, pages = pidcache.load_pages(str(path))
    return pages[0]


def _detect(pc, rules, isa):
    dets, *_ = ds.detect(pc, lay=ds.LAYOUT, rules=rules, isa=isa)
    return {d.anchor: d for d in dets}


def _rules(**kw):
    base = dict(name="t", field_type_map={"TT": "TIT"}, not_field=frozenset(),
                valves=frozenset(), disabled=frozenset(), derive_from_isa=True)
    base.update(kw)
    return ds.Ruleset(**base)


def test_a_tag_the_table_explains_becomes_an_anchor(sheet):
    got = _detect(sheet, _rules(), TABLE)
    assert "AIT" in got, "범례가 A·I·T 를 전부 정의하는데 앵커가 되지 못했다"
    d = got["AIT"]
    assert d.category == "FIELD_INSTRUMENT"
    assert d.excel_type == "AIT"          # 설정에 없으면 도면이 쓴 글자 그대로
    src = d.evidence["anchor_source"]
    assert src["rule"] == "ISA_TABLE" and src["page_no"] == 3
    assert src["first"].startswith("A = ANALYSIS")
    assert "ANCHOR_FROM_ISA_TABLE" in d.rules_hit


def test_two_letters_of_the_same_kind_still_decompose(sheet):
    """`PP` 는 P(측정 변수) + P(TEST POINT) 다 — 같은 글자라도 열이 다르다."""
    assert "PP" in _detect(sheet, _rules(), TABLE)


def test_a_word_the_table_cannot_explain_is_not_an_anchor(sheet):
    """`NOTE` 는 `N` 이 FIRST LETTER 에 없다 — 도면이 스스로 걸러낸다."""
    assert "NOTE" not in _detect(sheet, _rules(), TABLE)


def test_the_project_dictionary_still_wins_for_naming(sheet):
    """`TT` 는 표로도 풀리지만 이 발주처는 `TIT` 라고 부른다 (②층)."""
    d = _detect(sheet, _rules(), TABLE)["TT"]
    assert d.excel_type == "TIT"
    assert "anchor_source" not in d.evidence, "사전에 있는 낱말에 유도 근거를 달면 안 된다"


def test_switching_it_off_reproduces_the_dictionary_only_behaviour(sheet):
    got = _detect(sheet, _rules(derive_from_isa=False), TABLE)
    assert set(got) == {"TT"}


def test_no_table_means_no_derivation(sheet):
    """범례를 못 읽은 문서에서 사전 밖 낱말을 계기로 만들지 않는다."""
    assert set(_detect(sheet, _rules(), None)) == {"TT"}
    assert set(_detect(sheet, _rules(), isa_table.IsaTable())) == {"TT"}


# ---- 규칙 자체 (PDF 없이) ------------------------------------------------

@pytest.mark.parametrize("tag, ok", [
    ("AIT", True), ("AT", True), ("PP", True), ("ZS", True), ("ZSC", True),
    ("PDI", True), ("PDIT", True), ("TIT", True),
    ("NOTE", False),        # N 이 FIRST LETTER 에 없다
    ("ZSO", False),         # O 가 SUCCEEDING 에 없다 (경보 수식자 — 표가 정의 안 함)
    ("TO", False), ("M", False), ("V", False), ("", False), ("P1", False),
])
def test_decompose_reads_only_what_the_table_prints(tag, ok):
    assert (TABLE.decompose(tag) is not None) is ok


def test_two_letter_heads_are_tried_first():
    """`PDIT` 는 `PD` + `IT` 이지 `P` + `DIT` 가 아니다."""
    assert TABLE.decompose("PDIT") == ("PD", "IT")


def test_no_letter_dictionary_is_hardcoded():
    """글자 뜻을 코드에 적으면 그것이 곧 외워둔 값이다 (§9 ②)."""
    src = (ROOT / "app" / "engine" / "isa_table.py").read_text()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "decompose")
    body = ast.get_source_segment(src, fn) or ""
    body = body.replace(ast.get_docstring(fn) or "", "")
    for word in ("ANALYSIS", "PRESSURE", "TEMPERATURE", "SWITCH", "INDICATOR"):
        assert word not in body, f"{word} 가 코드에 박혀 있다"


# ---- 실제 두 문서의 ISA 표로 규칙이 무엇을 받아들이는지 못박는다 -----------
#
# PDF 없이도 정확한 이유: 저장된 결과의 `unjudged_symbols` 중 "사전에 없음" 은
# `detect()` 가 **버블 검증을 이미 통과시킨** 낱말이다 (`len(hit) == 1` 뒤에
# 모은다).  사전에 낱말만 있으면 같은 자리에서 그대로 검출이 된다.

REAL = [("AL NOUF1", "out/round20/run_base.json", 32,
         {"PP": 8, "ZSC": 7, "ZT": 6, "ZS": 5, "AIT": 4, "AT": 2}, {"ZSO": 11}),
        ("TC2", "out/round47/TC2_after.json", 25,
         {"PP": 12, "AIT": 8, "PDI": 3, "PS": 2},
         {"NOTE": 15, "VBV": 4, "SSV": 4, "TO": 2, "M": 2, "V": 2,
          "PDIA": 2, "BRPV": 1})]


def _real(path):
    import collections
    import json
    f = ROOT / path
    if not f.exists():
        pytest.skip(f"{path} 없음")
    r = json.loads(f.read_text())
    r = r.get("result", r)
    isa = (r.get("description_build") or {}).get("isa_table") or {}
    t = isa_table.IsaTable(
        first={k: tuple(v) for k, v in (isa.get("first") or {}).items()},
        succeeding={k: tuple(v) for k, v in (isa.get("succeeding") or {}).items()})
    took, left = collections.Counter(), collections.Counter()
    for x in r.get("unjudged_symbols", []):
        if x.get("kind") != "INSTRUMENT_TAG" or "사전에 없" not in (x.get("why") or ""):
            continue
        lab = (x.get("label") or "").strip()
        (took if t.decompose(lab) else left)[lab] += 1
    return took, left


@pytest.mark.parametrize("name, path, total, taken, rejected", REAL)
def test_the_rule_on_the_real_documents(name, path, total, taken, rejected):
    took, left = _real(path)
    assert dict(took) == taken, f"{name} — 받아들이는 낱말이 달라졌다"
    assert dict(left) == rejected, f"{name} — 걸러내는 낱말이 달라졌다"
    assert sum(took.values()) == total
