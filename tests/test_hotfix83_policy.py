"""hotfix83 — 사용자 실무 판단 넷 (2026-10-10).

  1. Typical 상세 수량 × 유닛 승수 — **곱한다** (이미 그렇게 돈다 · 여기서 못박는다)
  2. PSV 는 식별하지 않는다
  3. 별표의 공급자는 NOTES 가 특정하면 그 이름, 아니면 그냥 VENDOR (검토 사유 없음)
  4. 제어실 기능 버블(LICA · PICA …)은 리스트에 넣지 않는다 — 그 도면의 ISA 표로 가른다
"""
import ast
import inspect
import types

import pymupdf
import pytest

from app import pipeline as P


class _Isa:
    """그 도면의 ISA 표 흉내 — QFE 범례가 실제로 읽힌 꼴 (A 의 뜻이 깨져 읽힌 것까지)."""

    first = {"L": ("LEVEL",), "P": ("PRESSURE",), "T": ("TEMPERATURE",), "F": ("FLOW",),
             "G": ("GAUGING",), "PD": ("PRESSURE", "DIFFERENTIAL"), "Z": ("POSITION",)}
    succeeding = {"I": ("INDICATOR",), "T": ("DEVICE", "TRANSMITTER"), "C": ("CONTROLLER",),
                  "A": ("DEVICE", "LOW"), "S": ("SWITCH",), "E": ("SENSING", "PRIMARY", "ELEMENT"),
                  "K": ("CONTROL", "STATION"), "L": ("DEVICE", "LOW")}

    def decompose(self, tag):
        t = tag.upper()
        for n in (2, 1):
            head, rest = t[:n], t[n:]
            if head in self.first and rest and all(c in self.succeeding for c in rest):
                return head, rest
        return None


ISA = _Isa()


@pytest.mark.parametrize("anchor,lines,hit", [
    ("LICA", 1, True), ("PICA", 0, True), ("PIC", 1, True), ("GTC", 2, True),
    ("FIC", 0, True), ("TK", 0, True),
    ("LA", 1, True), ("LIA", 1, True), ("TIA", 2, True),
    ("LA", 0, False),                      # 선 없는 버블은 (나) 갈래가 아니다
    ("PIT", 1, False), ("LIT", 1, False),  # 선 있는 현장 전송기 (AL NOUF1 108행)
    ("LS", 1, False), ("PDIT", 1, False), ("FE", 1, False),
    ("PI", 0, False), ("TI", 0, False),
    ("ZOCL", 2, False),                    # 표가 O 를 정의하지 않는다 — 판정하지 않는다
])
def test_control_function_reads_the_drawing_isa_table(anchor, lines, hit):
    assert bool(P.control_function_reason(anchor, lines, ISA)) is hit


def test_no_table_no_judgement():
    assert P.control_function_reason("LICA", 2, None) == ""


def _row(key, *, tab="FIELD", type_="", anchor="", tag="", lines=0, body=""):
    ev = {"anchor": anchor} if anchor else {}
    if tag:
        ev["tag"] = tag
    if body:
        ev["body"] = body
    if lines:
        ev["detail"] = {"bubble_lines": lines}
    return P.Row(key=key, tab=tab, page_no=6, drawing_no="D-1", type=type_,
                 rect=(0, 0, 10, 10), evidence=ev)


def _with_policy(monkeypatch, **pol):
    monkeypatch.setitem(P.CFG.data, "policy", pol)


def test_apply_policy_drops_psv_and_control_functions(monkeypatch):
    _with_policy(monkeypatch, not_identified_tags=["PSV"], control_room_functions="exclude")
    rows = [_row("a", type_="PIT", anchor="PIT", lines=1),
            _row("b", type_="LICA", anchor="LICA", lines=1),
            _row("c", tab="REVIEW", type_="CHECK", tag="PSV", body="CHECK"),
            _row("d", tab="REVIEW", type_="", tag="PSV"),
            _row("e", tab="MOV", type_="GATE", tag="MOV", body="GATE"),
            _row("f", type_="LA", anchor="LA", lines=1)]
    kept, facts = P.apply_policy(rows, ISA)
    assert [r.key for r in kept] == ["a", "e"]
    assert facts["by_reason"] == {"CONTROL_FUNCTION": 2, "NOT_IDENTIFIED_TAG": 2}
    assert {d["key"] for d in facts["rows"]} == {"b", "c", "d", "f"}
    assert all(d["note"] for d in facts["rows"])


def test_apply_policy_switches_off(monkeypatch):
    _with_policy(monkeypatch, not_identified_tags=[], control_room_functions="keep")
    rows = [_row("b", type_="LICA", anchor="LICA", lines=1), _row("c", tag="PSV", body="CHECK")]
    kept, facts = P.apply_policy(rows, ISA)
    assert [r.key for r in kept] == ["b", "c"] and facts["rows"] == []


def test_valve_body_rows_are_never_control_functions(monkeypatch):
    """밸브 행은 몸체 갈래로 서므로 기능 글자 판정에 걸리지 않는다 (PCV · TCV 는 남는다)."""
    _with_policy(monkeypatch, not_identified_tags=["PSV"], control_room_functions="exclude")
    rows = [_row("v", tab="PNEUMATIC", type_="GLOBE", anchor="TIC", tag="TCV", body="GLOBE")]
    kept, _facts = P.apply_policy(rows, ISA)
    assert [r.key for r in kept] == ["v"]


def test_the_tag_words_live_in_config_not_in_code():
    """PSV 라는 낱말은 사용자가 정한 값이라 config 에 있다 — 판정 함수에 글자로 없다."""
    for fn in (P.apply_policy, P.control_function_reason):
        tree = ast.parse(inspect.getsource(fn))
        lits = {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                and isinstance(n.value, str)}
        assert not {"PSV", "LICA", "PICA", "PIC", "LA"} & lits
    pol = P.CFG.data.get("policy") or {}
    assert "PSV" in [str(t).upper() for t in pol.get("not_identified_tags") or []]
    assert pol.get("control_room_functions") == "exclude"


@pytest.mark.parametrize("text,name", [
    ("DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG.", "HRSG"),
    ("MARKED ITEMS TO BE PROVIDED BY GTG SUPPLIER.", "GTG SUPPLIER"),
    ("DENOTED INSTRUMENTS WILL BE SUPPLIED FROM SUMP PUMP VENDOR.", "SUMP PUMP VENDOR"),
    ("DENOTED ITEMS WILL BE SUPPLIED FROM SUMP PUMPS VENDOR.", "SUMP PUMPS VENDOR"),
    ("THIS WILL BE IN EQUIPMENT VENDOR SCOPE.", "EQUIPMENT VENDOR"),
    ("PUMP SUPPLIER'S SCOPE", "PUMP SUPPLIER"),
    (": CONDENSER VENDOR SCOPE OF SUPPLY", "CONDENSER VENDOR"),
    ("PUMP VENDOR SHALL PROVIDE THE INSTRUMENT.", "PUMP VENDOR"),
    ("DENOTED INSTRUMENTS WILL BE SUPPLIED FROM SUMP", ""),   # 공급자를 말하지 않음
    ("ITEMS IN VENDOR SCOPE", ""),                           # 누구인지 말하지 않음
    ("UNDEFINED ON THIS PAGE", ""),
    ("", ""),
])
def test_supplier_is_whoever_the_notes_name(text, name):
    assert P._supplier_name(text) == name


def test_undefined_mark_is_plain_vendor_without_review():
    d = types.SimpleNamespace(rules_hit=["VENDOR_MARK_UNDEFINED"],
                              evidence={"vendor_mark": {"meaning": ""}})
    assert P._scope_of(d) == P.COL_VENDOR
    assert P._vendor_of(d) == "VENDOR"
    src = inspect.getsource(P)
    # 뜻 없는 별표에 검토 사유를 다는 자리가 남아 있지 않다
    assert 'codes.append("VENDOR_MARK_UNDEFINED")' not in src


def test_typical_multiplies_the_unit_multiplier():
    """사용자 확정 1 — Typical 상세 수량에 유닛 승수를 곱한다 (잘못된 것은 사람이 고친다)."""
    class _T:
        details = [types.SimpleNamespace(id="D", caption="D", box=(0, 0, 100, 100),
                                         component=False, points=[])]
        ambiguous = set()

        def factor_for(self, rect):
            return self.details[0], 4

    r = P.Row(key="k", tab="FIELD", page_no=6, drawing_no="D-1", type="PIT", qty=8,
              rect=(10, 10, 20, 20), evidence={"qty_basis": "1 symbol x 8 (NOTES: …)"})
    rows = [r]
    P._apply_typical(rows, {6: _T()})
    assert rows[0].qty == 32
    assert "x 4" in rows[0].evidence["qty_basis"]


def _desc_row(key, desc, letter, sentence, dwg="D-1"):
    return P.Row(key=key, tab="FIELD", page_no=6, drawing_no=dwg, type="LIT",
                 description=f"{desc} {letter}", rect=(0, 0, 1, 1),
                 evidence={"duplicate_suffix": {"letter": letter, "sentence": sentence},
                           "description_sources": ["DRAWING:X", "SUFFIX: …"]})


def test_dropping_a_row_relabels_the_rest_of_its_sentence_group():
    s = "UNIT #11 TANK LEVEL"
    a, b, c = _desc_row("a", s, "A", s), _desc_row("b", s, "B", s), _desc_row("c", s, "C", s)
    assert P._resuffix([a, c], [b]) == 2
    assert (a.description, c.description) == (f"{s} A", f"{s} B")
    # 남은 것이 하나면 접미를 뗀다 (가를 것이 없다)
    d, e = _desc_row("d", s, "A", s), _desc_row("e", s, "B", s)
    assert P._resuffix([d], [e]) == 1
    assert d.description == s and "duplicate_suffix" not in d.evidence
    assert d.evidence["description_sources"] == ["DRAWING:X"]
    # 다른 무리는 건드리지 않는다
    f = _desc_row("f", "OTHER", "A", "OTHER")
    assert P._resuffix([f], [e]) == 0 and f.description == "OTHER A"


def test_dropped_rows_leave_no_overlay_box():
    layers = {6: {"FIELD": [{"key": "a", "row": True}, {"key": "b", "row": True},
                            {"key": "b", "row": False}]}}
    P._drop_from_layers(layers, {"b"})
    assert layers[6]["FIELD"] == [{"key": "a", "row": True}, {"key": "b", "row": False}]


def test_the_policy_is_the_last_filter():
    """판정이 다 끝난 뒤 뺀다 — 앞에서 빼면 표시기 접기·거리 문턱이 달라진다 (QFE 실측)."""
    src = inspect.getsource(P._analyse)
    assert src.index("_fold_readouts(") < src.index("apply_policy(")
    assert src.index("_attach_tags(") < src.index("apply_policy(")
