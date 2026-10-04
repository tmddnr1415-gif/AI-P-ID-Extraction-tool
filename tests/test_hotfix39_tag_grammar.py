"""hotfix39 — 실행 프로젝트는 태그가 우선.

사용자: *"QFE 는 실행 프로젝트이다.  실행 프로젝트 출력 시에는 tag number 가 우선시 되어야
하며 tag number 에 계기 타입이 명시되어 있다."*  그 표(KKS 기능코드)를 코드에 적지 않는다 —
태그와 버블 글자가 함께 있는 행에서 **그 도면이** 가르쳐 준다 (QFE: CP→P 721 · CT→T 263 ·
CL→L 312 · CF→F 105 · 순도 0.98).
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import pipeline as P                       # noqa: E402
from app import revisions as R                      # noqa: E402
from app.engine import isa_table, tags as T, detect_symbols as ds   # noqa: E402

TABLE = isa_table.IsaTable(
    first={"P": ("PRESSURE",), "T": ("TEMPERATURE",), "L": ("LEVEL",), "F": ("FLOW",),
           "PD": ("PRESSURE", "DIFFERENTIAL"), "Z": ("POSITION",), "H": ("HAND",)},
    succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",), "S": ("SWITCH",), "C": ("CONTROLLER",)},
    page_no=3, note="test")


def _samples():
    out = []
    for i in range(6):
        out += [(f"11LBB5{i}CP00{i}", "P"), (f"11LBB5{i}CT00{i}", "T"), (f"11LBB5{i}CL00{i}", "L")]
    out.append(("11LBB59CP009", "PD"))          # 차압도 P 가족이다 — 머리 첫 글자
    return out


def test_grammar_finds_the_letter_run_that_names_the_variable():
    g = T.grammar(_samples())
    assert g["learned"] and g["run_index"] == 1 and g["purity"] >= 0.9
    assert g["majority"]["CP"]["head"] == "P" and g["majority"]["CT"]["head"] == "T"
    assert g["class_letter"] == "C"
    assert T.code_of("22GMB04CL501", g) == "CL" and T.code_of("AA301", g) == ""


def test_grammar_needs_two_samples_and_says_so():
    assert T.grammar([("11LBB50CP001", "P")]) == {"learned": False, "samples": 1}
    assert T.grammar([]) == {"learned": False, "samples": 0}


def test_no_instrument_code_table_is_written_in_the_code():
    """KKS 기능코드(CP·CT·CL·CF·CG)를 문자열로 적지 않는다 — 도면이 가르친다."""
    for f in ("app/engine/tags.py", "app/pipeline.py"):
        tree = ast.parse((ROOT / f).read_text(encoding="utf-8"))
        lits = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        assert not ({"CP", "CT", "CL", "CF", "CG", "CQ"} & lits), f


def _row(key, anchor, tag, page=5, rect=(100, 100, 168, 123), tab=P.TAB_FIELD):
    return P.Row(key=key, tab=tab, page_no=page, drawing_no="D-1", type=anchor, qty=2,
                 system="SYS", rect=tuple(rect), tag_no=tag,
                 evidence={"anchor": anchor, "tag_no": {"value": tag}})


def _rows_from_samples():
    rows = []
    for i, (tag, head) in enumerate(_samples()):
        anchor = {"P": "PIT", "T": "TIT", "L": "LIT", "PD": "PDIT"}[head]
        rows.append(_row(f"k{i}", anchor, tag, rect=(100, 100 + 30 * i, 168, 123 + 30 * i)))
    return rows


def test_a_row_whose_tag_code_disagrees_with_its_bubble_is_flagged_not_changed():
    """QFE `PI 22GMB04CL501` — 레벨 코드에 PI.  행은 그대로, 검토 사유만 붙는다."""
    rows = _rows_from_samples() + [_row("odd", "PI", "11LBB70CL777", rect=(100, 900, 168, 923))]
    facts = P._tag_grammar_pass(rows, [], TABLE, {"effective": "epc", "shapes": []}, [])
    odd = next(r for r in rows if r.key == "odd")
    assert facts["enabled"] and facts["grammar"]["learned"]
    assert "TAG_TYPE_MISMATCH" in odd.needs_review and odd.type == "PI"
    assert odd.evidence["tag_check"] == {"code": "CL", "expected": "L", "seen": "P", "n": 6, "of": 7}
    assert [m["tag_no"] for m in facts["mismatch"]] == ["11LBB70CL777"]
    assert all("TAG_TYPE_MISMATCH" not in r.needs_review for r in rows if r.key != "odd")


def test_bid_mode_or_no_isa_table_does_nothing():
    rows = _rows_from_samples()
    assert P._tag_grammar_pass(rows, [], TABLE, {"effective": "bid"}, [])["enabled"] is False
    assert P._tag_grammar_pass(rows, [], None, {"effective": "epc"}, [])["enabled"] is False
    assert all(not r.needs_review for r in rows)


class _Page:
    def __init__(self, page_no, words):
        self.page_no = page_no
        self.words = [(pymupdf.Rect(*r), t) for r, t in words]


def test_a_tag_below_an_unreadable_bubble_word_makes_one_row_per_tag():
    """QFE p39 `ZSOC` / `ZOCL` 이 한 태그 `30GKC11CG001` 을 든다 — ISA 표에 O·C 가 없어
    풀리지 않지만 태그가 증거다.  같은 태그는 한 행이고 공급 주체는 비운다."""
    rows = _rows_from_samples()
    words = [((300, 500, 330, 509), "ZSOC"), ((296, 511, 360, 520), "30GKC11CG001"),
             ((300, 530, 330, 539), "ZOCL"), ((296, 541, 360, 550), "30GKC11CG001"),
             # 밸브 태그(AA) 아래 글자 — 계기 코드 첫 글자가 아니라 행이 아니다
             ((600, 500, 630, 509), "ESDV"), ((596, 511, 660, 520), "00EKG02AA251")]
    unjudged = [{"kind": "INSTRUMENT_TAG", "page_no": 5, "label": "ZSOC", "center": [315, 504.5],
                 "why": "ISA 태그 모양인데 이 프로젝트 사전에 없음"},
                {"kind": "INSTRUMENT_TAG", "page_no": 5, "label": "ZOCL", "center": [315, 534.5],
                 "why": "ISA 태그 모양인데 이 프로젝트 사전에 없음"},
                {"kind": "INSTRUMENT_TAG", "page_no": 5, "label": "ESDV", "center": [615, 504.5],
                 "why": "ISA 태그 모양인데 이 프로젝트 사전에 없음"}]
    tier = {"effective": "epc", "shapes": [T.shape("30GKC11CG001")]}
    n0 = len(rows)
    facts = P._tag_grammar_pass(rows, [_Page(5, words)], TABLE, tier, unjudged)
    new = [r for r in rows[n0:]]
    assert len(new) == 1 and new[0].tag_no == "30GKC11CG001" and new[0].type == "ZSOC"
    assert new[0].qty == 2 and new[0].scope == "" and new[0].system == "SYS"
    assert "TAG_EVIDENCE_ROW" in new[0].needs_review and "ZOCL" in new[0].needs_review
    assert new[0].evidence["tag_evidence"]["words"] == ["ZSOC", "ZOCL"]
    assert facts["evidence_rows"] == [{"page_no": 5, "tag_no": "30GKC11CG001", "anchor": "ZSOC",
                                       "folded": ["ZOCL"]}]
    assert facts["evidence_skipped"] == {"tag_not_instrument_code": 1}


def test_a_tag_already_on_a_row_does_not_make_a_second_row():
    rows = _rows_from_samples()
    tag = rows[0].tag_no
    words = [((300, 500, 330, 509), "ZSO"), ((296, 511, 360, 520), tag)]
    unjudged = [{"kind": "INSTRUMENT_TAG", "page_no": 5, "label": "ZSO", "center": [315, 504.5],
                 "why": "ISA 태그 모양인데 이 프로젝트 사전에 없음"}]
    n0 = len(rows)
    facts = P._tag_grammar_pass(rows, [_Page(5, words)], TABLE,
                                {"effective": "epc", "shapes": [T.shape(tag)]}, unjudged)
    assert len(rows) == n0 and facts["evidence_skipped"] == {"tag_already_on_a_row": 1}


def test_a_container_outline_is_not_a_bubble():
    tank = ds.Outline(pymupdf.Rect(560, 288, 856, 1090), "V", None, None, "SOLID")
    inner = ds.Outline(pymupdf.Rect(676, 871, 751, 898), "H", None, None, "SOLID")
    kept = ds._without_containers([tank, inner])
    assert [o.rect for o in kept] == [inner.rect]
    assert ds._without_containers([inner]) == [inner]
    # 나란한 둘은 둘 다 남는다 — 품는 관계가 없다
    a = ds.Outline(pymupdf.Rect(100, 100, 175, 126), "H", None, None, "SOLID")
    b = ds.Outline(pymupdf.Rect(170, 100, 245, 126), "H", None, None, "SOLID")
    assert ds._without_containers([a, b]) == [a, b]
    # QFE p42 — 버블의 양 끝 호 캡이 따로 윤곽으로 서도 버블은 남는다 (변을 나눈다)
    bub = ds.Outline(pymupdf.Rect(1548, 1302, 1608, 1323), "H", None, None, "SOLID")
    capL = ds.Outline(pymupdf.Rect(1548, 1302, 1557, 1323), "V", None, None, "SOLID")
    capR = ds.Outline(pymupdf.Rect(1599, 1302, 1608, 1323), "V", None, None, "SOLID")
    assert bub in ds._without_containers([bub, capL, capR])


def test_qfe_p51_words_inside_the_tank_outline_are_not_rows():
    pdf = ROOT / "data" / "QFE_260326.pdf"
    if not pdf.exists():
        import pytest
        pytest.skip("QFE PDF 가 이 기계에 없다")
    import dataclasses
    from app.engine import pidcache
    _d, pages = pidcache.load_pages(str(pdf), only=[51])
    lay = dataclasses.replace(ds.LAYOUT, anchor_slack=1.485, side_slack=0.742)
    dets, *_rest, bubbles = ds.detect(pages[0], lay=lay)
    assert not any(b.width > 200 for b in bubbles)                     # 탱크 외곽이 버블 목록에 없다
    assert sorted(d.anchor for d in dets if 560 < d.center[0] < 870 and 840 < d.center[1] < 920) == ["LI", "LIT", "LIT"]


def test_excel_order_puts_tagged_rows_first_by_tag_and_leaves_untagged_documents_alone():
    rows = [{"system": "S", "page_no": 1, "key": "b", "tag_no": "11LBB50CT001"},
            {"system": "S", "page_no": 1, "key": "a", "tag_no": ""},
            {"system": "S", "page_no": 1, "key": "c", "tag_no": "11LBB50CP001"}]
    assert [r["key"] for r in sorted(rows, key=R.excel_sort_key)] == ["c", "b", "a"]
    plain = [{"system": "S", "page_no": 1, "key": k} for k in ("b", "a", "c")]
    assert [r["key"] for r in sorted(plain, key=R.excel_sort_key)] == ["a", "b", "c"]
