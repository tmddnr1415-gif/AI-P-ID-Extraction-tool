"""10회차 — SCOPE 열과 TYPE 표기.

두 가지를 회귀로 못박는다:
  · SCOPE 열의 공급자 이름은 **그 장 NOTES 원문에서만** 나온다.  프로젝트
    이름(HRSG · ST SUPPLIER …)이 코드에 들어오면 다음 프로젝트에서 틀린다.
  · TYPE 표기(`MOV(GLOBE)`)는 **출력 전용**이다.  §8 의 대조 단위인 판정값
    `values["type"]` 은 한 글자도 바뀌지 않는다.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app" / "engine"))
from app import pipeline


# --------------------------------------------------------------------------
# SCOPE 열
# --------------------------------------------------------------------------

class Det:
    def __init__(self, rules, meaning=None):
        self.rules_hit = list(rules)
        self.evidence = {} if meaning is None else {
            "vendor_mark": {"stars": 1, "meaning": meaning}}


def test_supplier_name_comes_from_the_notes_sentence():
    assert pipeline._supplier_name(
        "DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG.") == "HRSG"
    assert pipeline._supplier_name(
        "DENOTES EQUIPMENT WILL BE SUPPLIED BY ST SUPPLIER.") == "ST SUPPLIER"
    assert pipeline._supplier_name(
        "SYMBOL INDICATES COMPONENTS FURNISHED BY TANK VENDOR."
    ) == "TANK VENDOR"


def test_supplier_name_is_empty_when_the_sentence_has_no_by_clause():
    """지어내지 않는다 — 형태가 다르면 ③(그냥 VENDOR)으로 떨어진다.
    이 문서에도 그런 장이 있다: p52~56 은 `SUPPLIED FROM SUMP` 라고 쓴다."""
    assert pipeline._supplier_name("DENOTED INSTRUMENTS WILL BE SUPPLIED FROM SUMP") == ""
    assert pipeline._supplier_name("") == ""


def test_scope_column_follows_the_four_rules():
    named = Det(["VENDOR_MARK_GLYPH"], "MARKED ITEM TO BE SUPPLIED BY BFP SUPPLIER.")
    assert pipeline._scope_of(named) == "VENDOR(BFP SUPPLIER)"          # ②
    unnamed = Det(["VENDOR_MARK_GLYPH"], "SUPPLIED FROM SUMP")
    assert pipeline._scope_of(unnamed) == "VENDOR"                      # ③
    undefined = Det(["VENDOR_MARK_UNDEFINED"])
    assert pipeline._scope_of(undefined) == "VENDOR"                    # ③
    assert pipeline._scope_of(Det([])) == "SCT"                         # ④
    assert pipeline._scope_of(Det(["SCT_SUPPLIER_SCOPE"])) == "SCT"     # ④


def test_no_supplier_name_is_written_into_the_code():
    """이름은 런타임 값이지 소스 상수가 아니다."""
    src = (Path(pipeline.__file__).read_text(encoding="utf-8")
           + Path("config/project_alnouf1.yaml").read_text(encoding="utf-8"))
    # config 주석의 NOTES 원문 인용은 근거라서 남긴다 — 규칙으로 쓰이는지를 본다.
    for name in ("HRSG", "ST SUPPLIER", "SEAWATER INTAKE", "TANK VENDOR"):
        for quoted in (f'"{name}"', f"'{name}'"):
            assert quoted not in src, f"{name} 이 코드/설정의 값으로 들어왔다"


# --------------------------------------------------------------------------
# TYPE 표기
# --------------------------------------------------------------------------

def test_type_display_prefixes_only_with_a_tag_printed_on_the_drawing():
    assert pipeline.type_display({"type": "GLOBE"}, {"tag": "MOV"}) == "MOV(GLOBE)"
    assert pipeline.type_display({"type": "GLOBE"}, {"tag": "PCV"}) == "PCV(GLOBE)"
    # 태그가 없는 밸브 — [C] 의 M 심볼 단독 인식 행.  도면에 `MOV` 글자가
    # 없으므로 접두를 붙이지 않는다 (근거 생성 금지).
    assert pipeline.type_display({"type": "GLOBE"}, {"tag": ""}) == "GLOBE"
    assert pipeline.type_display({"type": "GLOBE"}, {}) == "GLOBE"
    assert pipeline.type_display({"type": "PIT"}, None) == "PIT"


def test_type_display_never_promotes_a_judged_value_to_a_prefix():
    """액추에이터 판정값은 도면이 인쇄한 낱말이 아니다."""
    assert pipeline.type_display({"type": "GLOBE", "valve_type": "MOTOR"},
                                 {"tag": "MOTOR"}) == "GLOBE"
    assert pipeline.type_display({"type": "GLOBE"}, {"tag": "PNEUMATIC"}) == "GLOBE"


def test_type_display_does_not_touch_the_judged_value():
    """§8 의 대조 단위는 `values["type"]` 이다 — 표기 함수가 그것을 고치면
    정밀도·재현율이 통째로 무의미해진다."""
    values = {"type": "GLOBE"}
    pipeline.type_display(values, {"tag": "MOV"})
    assert values == {"type": "GLOBE"}


def test_type_display_is_not_called_while_rows_are_built():
    """행을 만드는 코드가 이 함수를 부르면 판정값이 오염될 수 있다.
    부르는 곳은 산출물(excel_out)과 화면 응답(main) 뿐이어야 한다."""
    for fn in (pipeline._field_rows, pipeline._valve_rows,
               pipeline._axis_pass, pipeline._apply_axis):
        assert "type_display" not in inspect.getsource(fn)
