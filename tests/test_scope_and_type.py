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


# --------------------------------------------------------------------------
# 11회차 — 밸브 SCOPE · 발주처 양식의 SCT 필터 · 측정축
# --------------------------------------------------------------------------

def test_valve_scope_uses_the_same_function_as_instruments():
    """밸브용 SCOPE 로직을 따로 두지 않는다 — 두 벌이 되면 규칙이 갈린다."""
    src = inspect.getsource(pipeline._valve_rows)
    assert "_scope_of(marked)" in src
    assert "VENDOR" not in src, "밸브 경로가 SCOPE 값을 스스로 만들고 있다"


def test_valve_scope_does_not_touch_the_description_axis():
    """`vendor_supply` 는 밸브에 쓰지 않는다.

    쓰면 `_axis_pass` 가 그 행을 ⓪(벤더 · 현행 유지)로 돌려 **Description 이
    지워진다** — 실측 1행(p7 CHECK 의 `TO HRSG#11 CRH CHECK VALVE`).  11회차는
    열 채움까지이므로 여기서 멈춘다.
    """
    src = inspect.getsource(pipeline._valve_rows)
    assert "vendor_supply=" not in src


def test_vendor_mark_is_read_above_the_actuator_when_there_is_one():
    """별표는 그 항목의 **심볼 위**에 찍힌다.  작동 밸브에서 맨 위 심볼은
    몸체가 아니라 액추에이터다 (실측 p6: 별표 y=526 · M 원 y0=534.4 ·
    몸체 y0=563.5, 허용치 mark_above 25.0pt)."""
    src = inspect.getsource(pipeline._valve_rows)
    assert "b.actuator_rect" in src, "허용치를 늘리는 대신 재는 자리를 바로잡는다"


class _Cfg:
    """설정 하나만 든 가짜 config — 시험이 **어느 설정에서 도는지** 말하게 한다."""

    def __init__(self, mode):
        self.data = {"client_form": {"scope_filter": mode}}


def test_the_client_workbook_scope_is_a_setting_with_all_as_default():
    """무엇을 담느냐는 발주처가 정한다 — 11회차 `sct`, 18회차 `all`.

    11회차는 "타사 공급분은 발주처 문서에 자리가 없다"고 보고 SCT 만 담았다.
    18회차에 발주처가 뒤집었다: 계기는 타사가 대도 **설치 자재(Bulk material)는
    SCT 가 대므로** 물량을 뽑으려면 그 행이 리스트에 있어야 한다.

    그래서 11회차 규칙을 **지우지 않고 껐다.**  이 시험이 두 모드를 다 지킨다 —
    한쪽만 시험하면 되돌릴 수 있다는 말이 빈말이 된다.
    """
    from app import excel_out
    row = lambda scope: {"values": {"scope": scope}}

    # 기본값: 설정 파일이 무엇이든 알 수 없는 값이면 전량으로 떨어진다
    assert excel_out.form_scope_mode(_Cfg("이상한값")) == excel_out.FORM_SCOPE_ALL

    all_cfg = _Cfg(excel_out.FORM_SCOPE_ALL)
    for scope in ("SCT", "VENDOR", "VENDOR(HRSG)", ""):
        assert excel_out.in_client_scope(row(scope), all_cfg), (
            f"전량 모드인데 {scope!r} 행이 빠졌다")

    sct_cfg = _Cfg(excel_out.FORM_SCOPE_SCT)
    assert excel_out.in_client_scope(row("SCT"), sct_cfg)
    assert not excel_out.in_client_scope(row("VENDOR"), sct_cfg)
    assert not excel_out.in_client_scope(row("VENDOR(HRSG)"), sct_cfg)
    assert excel_out.in_client_scope(row(""), sct_cfg), "빈 값은 '판정 없음'이다"


def test_scope_state_still_names_the_supplier_under_either_mode():
    """`scope_state` 는 **공급 주체**를 세지 "양식에 나가는가"를 세지 않는다.

    18회차에 그 둘이 갈렸다 — 전량 모드에서 벤더 행은 `out_of_scope` 이면서
    동시에 양식에 나간다.  한 함수로 묶으면 "벤더 공급분이 몇 행인가"를 물을
    수 없게 되고, 완료 화면이 260행을 "빠진다"고 거짓말한다.
    """
    from app import excel_out
    row = lambda scope: {"values": {"scope": scope}}
    assert excel_out.scope_state(row("SCT")) == "delivered"
    assert excel_out.scope_state(row("VENDOR(HRSG)")) == "out_of_scope"
    assert excel_out.scope_state(row("")) == "legacy"
    # 그러면서도 전량 모드에서는 그 행이 나간다
    assert excel_out.in_client_scope(row("VENDOR(HRSG)"),
                                     _Cfg(excel_out.FORM_SCOPE_ALL))


def test_a_row_with_no_scope_at_all_is_still_delivered():
    """빈 값은 "타사 공급"이 아니라 "아직 판정한 적 없음"이다.

    SCOPE 열이 생기기 전에 저장된 분석(회사 PC 의 기존 결과)이 그렇고, 빼면
    발주처 양식 네 개가 통째로 빈 파일이 된다 — UI 스위트가 실 DB 사본으로
    돌다가 `rows: 0` 으로 잡아냈다.  담되 MANIFEST 가 몇 행인지 말한다.
    """
    from app import excel_out
    assert excel_out.in_client_scope({"values": {"scope": ""}})
    assert excel_out.in_client_scope({"values": {}})
    assert excel_out.scope_state({"values": {}}) == "legacy"


def test_the_export_filter_does_not_touch_stable_ids():
    """걸러진 행의 안정 ID 를 회수하거나 다시 매기지 않는다 — Rev.A 에서 한 번만
    부여한다는 규칙이 깨지면 리비전 승계가 통째로 무너진다."""
    from app import excel_out
    src = inspect.getsource(excel_out.write_all) + inspect.getsource(
        excel_out.in_client_scope)
    for banned in ("stable_id", "assign_excel_numbers", "registry"):
        assert banned not in src


def test_the_two_accuracy_axes_share_one_scoring_path():
    """축을 더하는 것이지 기존 정의를 고치는 것이 아니다 (§2.1 ⑧).

    두 축은 `score()` 하나를 통과하고, 축마다 다른 것은 `keep` 하나뿐이다 —
    정답지 쪽 모수는 어느 축에서도 같다.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "spike"))
    import accuracy
    names = [n for n, _ in accuracy.AXES]
    assert names == ["전량", "SCT"]
    src = inspect.getsource(accuracy.score)
    assert src.count("client_lists.load") == 1, "정답지 쪽이 축마다 갈렸다"
    assert "keep(r)" in src and "scope" not in src, \
        "축의 조건은 AXES 에만 있어야 한다"
    # 전량 축의 `keep` 은 아무것도 거르지 않는다.
    assert dict(accuracy.AXES)["전량"]({"scope": ""}) is True
    assert dict(accuracy.AXES)["SCT"]({"scope": "SCT"}) is True
    assert dict(accuracy.AXES)["SCT"]({"scope": "VENDOR(HRSG)"}) is False


def test_the_angle_valve_definition_catches_the_legend_that_defines_it():
    """앵글 밸브 규칙은 **범례에서 나왔고 범례가 그것을 확인해 준다** (18회차).

    범례 page 2 의 밸브 표는 `GATE`(중공 나비넥타이) · `GLOBE`(나비 + 검은 원)
    다음에 **`ANGLE`** 을 그린다.  검출기 어휘에 그것이 없어서 두 삼각형 중
    하나만 `CHECK` 로 읽혔고, 그러면 rect 중심이 진짜 스템축에서 벗어나
    `act_offaxis`(범례 유도 0.83pt)가 **제대로 찾아 둔 공압 실린더를 거부**한다.

    이 시험이 지키는 것은 정의의 출처다: `_angle_figures` 의 정의가
    **범례 자신의 ANGLE 그림**을 잡아야 한다.  못 잡으면 그 정의는 도면에
    맞춘 것이지 범례에서 유도한 것이 아니다 (§2.1 ①).

    소스 검사로 한다 — 이 시험은 PDF 없이도 돌아야 하고, 실물 확인은
    `-m slow` 의 전량 분석이 한다.
    """
    from app.engine import detect_valves as dv
    src = inspect.getsource(dv._angle_figures)
    # 꼭짓점은 **네 개**의 선분 끝점이 모이는 점이다 (삼각형마다 두 변).
    assert "!= 4" in src, "꼭짓점 조건이 사라졌다"
    # 두 삼각형은 **직각**이어야 한다.  일직선이면 나비넥타이(GATE/GLOBE)다.
    assert "dirs[0] == dirs[1]" in src, "직각 조건이 사라졌다"
    # 페이지·도면번호·태그로 분기하지 않는다
    for banned in ("page_no", "drawing_no", "XV", "FCV", "PCV"):
        assert banned not in src, f"{banned} 로 분기하고 있다"


def test_the_actuator_offset_is_measured_from_the_apex_not_the_rect():
    """허용치를 늘리는 대신 **재는 점**을 바로잡았다 (18회차).

    실측: rect 중심에서 잰 어긋남 4.86~5.02pt ↔ 꼭짓점에서 잰 것 0.01~0.07pt.
    허용치 `act_offaxis` 는 0.83pt 이고 **건드리지 않았다** — 16회차 벤더
    별표에서 "허용치는 건드리지 않고 읽는 사각형만 바꿨다" 와 같은 판단이다.
    """
    from app.engine import detect_valves as dv
    src = inspect.getsource(dv.attach_actuators)
    assert '.get("apex")' in src, "꼭짓점을 읽지 않는다"
    assert "act_offaxis" in src, "허용치 검사가 사라졌다"
