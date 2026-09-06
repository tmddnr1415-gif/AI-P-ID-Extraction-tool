"""15회차 — 프로젝트 범례 프로필.

지키는 것은 다섯이다:

  · **프로필이 없으면 반드시 유도한다.**  없는데 기본값으로 조용히 도는 일이
    없어야 한다 — 그것이 [B]4 가 실측한 지금의 결함이고 이 회차의 동기다.
  · **프로필은 프로젝트 폴더 안에만 산다.**  `app/_data/projects/{이름}/` 이므로
    갈음(코드 덮어쓰기)으로 사라지지 않고, 다른 프로젝트가 공유할 길이 없다.
  · **되쓴 값은 잰 값과 같다.**  프로필을 통과시켜 되살린 것이 원본과 다르면
    세 경로(유도·재사용·강제유도)의 지문이 갈린다.
  · **유도 실패를 성공인 척하지 않는다.**  기본값으로 채우고 넘어가지 않고
    `failed` 에 남긴다.
  · **범례가 달라져도 자동으로 갱신하지 않는다.**  `diff` 는 말하기만 한다.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import legend_profile as LP
from app import revisions as R

import legend_rules  # noqa: E402
import isa_table  # noqa: E402
import projectconfig  # noqa: E402
import describe_equipment as dequip  # noqa: E402


# --------------------------------------------------------------------------
# 한 벌 만들기 — AL NOUF1 실측값을 그대로 쓴다 (base.json 의 `legend` 칸)
# --------------------------------------------------------------------------

def sample_pieces():
    butterfly = legend_rules.Derived(
        values={"tick_length": 3.0, "tick_reach_radii": 1.498,
                "bar_reach_radii": 2.822, "bar_min_radii": 2.378,
                "circle_diameter": 6.06},
        source="LEGEND", evidence={"page_no": 2})
    stem = legend_rules.Derived(
        values={"stem_gap": 0.0, "stem_offaxis": 0.03, "stem_length": 19.86,
                "centre_to_body": 26.97}, source="LEGEND")
    pneumatic = legend_rules.Derived(
        values={"dome_flat": 14.22, "dome_depth": 7.11, "dome_aspect": 0.5,
                "cylinder_side": 14.16, "cylinder_aspect": 1.003,
                "cylinder_divider": 0.5}, source="LEGEND")
    # `connector_reach` 를 섞기 **전** 값 — 이것이 범례가 말한 것이다.
    style = legend_rules.Derived(
        values={"dash_len": 7.2, "dash_gap": 3.6, "min_run": 16.968,
                "join_slack": 0.8}, source="LEGEND")
    isa = isa_table.IsaTable(first={"T": ("TEMPERATURE",), "P": ("PRESSURE",)},
                             succeeding={"I": ("INDICATE",)},
                             page_no=3, source="LEGEND",
                             note="legend p3 identification matrix")
    equip = [dequip.EquipSymbol(name="HORIZONTAL CENTRIFUGAL PUMP", page_no=2,
                                anchor=(40.5, 38.5), kinds=(("c", 4),),
                                footprint=(40.5, 38.5), paths=3),
             dequip.EquipSymbol(name="VERTICAL PUMP", page_no=2,
                                anchor=(14.2, 31.2), kinds=(("l", 2),),
                                footprint=(14.2, 31.2), paths=1)]
    words = {"STRAINER": "LEGEND", "FILTER": "DRAWING"}
    mult = projectconfig.UnitMultipliers(
        "LEGEND", {"00": 1, "10": 2, "11": 4}, {"00": "PLANT", "10": "GROUP"},
        {"00": "PLANT COMMON", "10": "GROUP 1"},
        note="legend p5: GROUPx2, PLANTx1, UNITx4")
    return butterfly, stem, pneumatic, style, isa, equip, words, mult


def sample_profile(**over):
    bf, st, pn, style, isa, equip, words, mult = sample_pieces()
    prof = LP.capture(butterfly=bf, actuator_stem=st, pneumatic=pn,
                      line_styles=style, isa=isa, equip_symbols=equip,
                      component_words=words, multipliers=mult,
                      meta={"pdf": "pid_total.pdf", "legend_sheets": [2, 3, 4, 5]})
    prof.update(over)
    return prof


# --------------------------------------------------------------------------
# 1. 프로필이 없으면 반드시 유도한다
# --------------------------------------------------------------------------

def test_no_profile_means_derive_not_default(tmp_path):
    """없으면 `None` 이고, `None` 이면 파이프라인이 잰다.  지어내지 않는다."""
    assert LP.load(tmp_path, "없는프로젝트") is None
    assert LP.load(tmp_path, "") is None
    from app import pipeline
    sig = inspect.signature(pipeline.analyse)
    assert sig.parameters["legend_profile"].default is None, (
        "`legend_profile` 의 기본값이 None 이 아니면 프로필 없는 분석이 "
        "무엇을 쓰는지 알 수 없다")


def test_a_corrupt_or_future_profile_is_ignored_rather_than_trusted(tmp_path):
    path = LP.profile_path(tmp_path, "P")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ this is not json", encoding="utf-8")
    assert LP.load(tmp_path, "P") is None
    path.write_text(json.dumps({"version": LP.VERSION + 99}), encoding="utf-8")
    assert LP.load(tmp_path, "P") is None, (
        "모르는 판의 프로필을 읽어 쓰면 무엇으로 분석했는지 말할 수 없다")


# --------------------------------------------------------------------------
# 2. 프로젝트 폴더 안에만 산다
# --------------------------------------------------------------------------

def test_the_profile_lives_inside_the_project_folder(tmp_path):
    path = LP.profile_path(tmp_path, "AL NOUF1")
    assert path.parent == R.project_dir(tmp_path, "AL NOUF1")
    assert R.projects_root(tmp_path) in path.parents
    assert path.name == LP.FILENAME


def test_projects_never_share_a_profile(tmp_path):
    LP.save(tmp_path, "가", sample_profile())
    assert LP.load(tmp_path, "가") is not None
    assert LP.load(tmp_path, "나") is None, (
        "다른 프로젝트가 프로필을 물려받으면 그 프로젝트의 범례가 아닌 "
        "규칙으로 분석하고도 아무도 모른다")


def test_what_is_saved_is_what_comes_back(tmp_path):
    """저장한 것과 다시 읽은 것이 같아야 한다.

    JSON 은 튜플을 배열로, dict 키를 문자열로 바꾼다 (`dash_histogram` 의
    7.2 -> "7.2").  `capture` 가 그 변환을 미리 겪지 않으면 "프로필이 무엇을
    담았나" 에 메모리 답과 파일 답 두 가지가 생긴다.
    """
    prof = sample_profile()
    LP.save(tmp_path, "P", prof)
    assert LP.load(tmp_path, "P") == prof


def test_saving_the_same_profile_twice_gives_the_same_file(tmp_path):
    prof = sample_profile(saved_at=1.0)
    first = LP.save(tmp_path, "P", prof).read_bytes()
    second = LP.save(tmp_path, "P", prof).read_bytes()
    assert first == second


# --------------------------------------------------------------------------
# 3. 되쓴 값은 잰 값과 같다 — 세 경로의 지문이 갈리지 않는 근거
# --------------------------------------------------------------------------

def test_round_trip_keeps_every_value(tmp_path):
    bf, st, pn, style, isa, equip, words, mult = sample_pieces()
    LP.save(tmp_path, "P", sample_profile())
    back = LP.load(tmp_path, "P")

    derived = LP.restore_derived(back)
    for key, want in (("butterfly", bf), ("actuator_stem", st),
                      ("pneumatic", pn)):
        assert derived[key].values == want.values
        assert derived[key].source == want.source
        assert derived[key].note == want.note

    got_style = LP.restore_line_styles(back)
    assert got_style.values == style.values
    assert got_style.source == style.source

    got_isa = LP.restore_isa(back)
    assert got_isa.as_dict() == isa.as_dict()
    assert got_isa.words_for("TIT") == isa.words_for("TIT")

    got_equip = LP.restore_equipment(back)
    assert [s.name for s in got_equip] == [s.name for s in equip]
    assert [s.key() for s in got_equip] == [s.key() for s in equip]

    got_mult = LP.restore_multipliers(back)
    assert (got_mult.source, got_mult.table, got_mult.scopes, got_mult.labels,
            got_mult.note) == (mult.source, mult.table, mult.scopes,
                               mult.labels, mult.note)


def test_the_vocabulary_is_rebuilt_from_the_symbols_not_stored_twice(tmp_path):
    """값을 두 곳에 두면 언젠가 갈린다 — 어휘는 심볼에서 다시 만든다."""
    _bf, _st, _pn, _sty, _isa, equip, _w, _m = sample_pieces()
    back = LP.restore_equipment(sample_profile())
    assert (dequip.derive_vocabulary(back, None)
            == dequip.derive_vocabulary(equip, None))
    assert "equipment_vocab" not in LP.ITEMS


def test_component_words_take_the_legend_half_from_the_profile(tmp_path):
    """범례 몫은 프로필, 도면 몫은 이번 도면.  순서는 원래 코드와 같다."""
    prof = sample_profile()
    # 범례 장이 없는 개정본: 도면에서만 낱말이 나온다
    merged = LP.merge_component_words(prof, {"FILTER": "DRAWING"})
    assert merged == {"STRAINER": "LEGEND", "FILTER": "DRAWING"}
    # 같은 문서를 다시 돌린 경우: 결과가 유도했을 때와 같다
    same = LP.merge_component_words(prof, {"STRAINER": "LEGEND",
                                           "FILTER": "DRAWING"})
    assert same == {"STRAINER": "LEGEND", "FILTER": "DRAWING"}


# --------------------------------------------------------------------------
# 4. 유도 실패를 성공인 척하지 않는다
# --------------------------------------------------------------------------

def test_a_failed_derivation_is_recorded_not_filled_in():
    bf, st, pn, style, isa, equip, words, mult = sample_pieces()
    broken = legend_rules.Derived(
        values={"tick_length": 3.0}, source="CONFIG_FALLBACK",
        note="범례 시트를 찾지 못했습니다; valves.legend_fallback.butterfly 사용")
    prof = LP.capture(butterfly=broken, actuator_stem=st, pneumatic=pn,
                      line_styles=style, isa=isa, equip_symbols=equip,
                      component_words=words, multipliers=mult)
    assert "butterfly" in prof["failed"]
    assert prof["items"]["butterfly"]["source"] == "CONFIG_FALLBACK"
    assert prof["items"]["butterfly"]["note"], "왜 실패했는지가 남아야 한다"
    assert "유도 실패" in "\n".join(LP.describe(prof))


def test_a_missing_equipment_table_is_named_not_blank():
    bf, st, pn, style, isa, _equip, words, mult = sample_pieces()
    prof = LP.capture(butterfly=bf, actuator_stem=st, pneumatic=pn,
                      line_styles=style, isa=isa, equip_symbols=[],
                      component_words={}, multipliers=mult)
    assert prof["items"]["equipment_symbols"]["source"] == "MISSING"
    assert "equipment_symbols" in prof["failed"]
    assert "component_words" in prof["failed"]


# --------------------------------------------------------------------------
# 5. 달라지면 말한다 — 그러나 고치지 않는다
# --------------------------------------------------------------------------

def test_diff_names_what_changed_from_what_to_what():
    stored = sample_profile()
    fresh = json.loads(json.dumps(stored))
    fresh["items"]["butterfly"]["values"]["tick_length"] = 4.5
    fresh["items"]["unit_multipliers"]["table"]["11"] = 6
    changes = LP.diff(stored, fresh)
    got = [(c["item"], c["key"], c["was"], c["now"]) for c in changes]
    assert ("butterfly", "values.tick_length", 3.0, 4.5) in got
    assert ("unit_multipliers", "table.11", 4, 6) in got
    # **고치지 않는다** — 원본은 그대로다
    assert stored["items"]["butterfly"]["values"]["tick_length"] == 3.0


def test_an_item_this_pdf_could_not_read_is_not_called_a_change():
    """못 읽은 것을 "바뀌었다" 로 세면 개정본마다 거짓 경보가 뜨고, 그러면
    진짜 변경이 그 안에 묻힌다.  못 읽었다는 사실은 따로 말한다."""
    stored = sample_profile()
    fresh = json.loads(json.dumps(stored))
    fresh["items"]["isa_table"] = {"source": "MISSING", "note": "없음",
                                   "page_no": 0, "first": {}, "succeeding": {}}
    assert LP.uncompared(fresh) == ["isa_table"]
    assert [c for c in LP.diff(stored, fresh) if c["item"] == "isa_table"] == []


def test_read_pages_comes_from_what_was_read_not_the_page_kind():
    """"몇 장을 읽었나" 는 읽은 쪽이 답한다.

    15회차 캡처가 그 차이를 잡았다 — 다시 그린 범례 장은 `page_kind` 가
    LEGEND 가 아니게 되는데, 유도는 인쇄된 머리말로 그 장을 찾아 읽는다.
    """
    prof = sample_profile()
    # butterfly·equip p2 · isa p3 · 승수는 자기 근거 문장이 `legend p5` 라고 적었다
    assert LP.read_pages(prof) == [2, 3, 5]
    broken = json.loads(json.dumps(prof))
    for key in LP.ITEMS:
        broken["items"][key]["source"] = "CONFIG_FALLBACK"
    assert LP.read_pages(broken) == []
    assert LP.uncompared(broken) == list(LP.ITEMS)


def test_identical_legends_report_no_change():
    stored = sample_profile()
    assert LP.diff(stored, json.loads(json.dumps(stored))) == []


def test_a_new_or_removed_isa_letter_is_a_change():
    stored = sample_profile()
    fresh = json.loads(json.dumps(stored))
    fresh["items"]["isa_table"]["first"]["Z"] = ["POSITION"]
    del fresh["items"]["isa_table"]["first"]["P"]
    keys = [(c["key"], c["was"], c["now"]) for c in LP.diff(stored, fresh)]
    assert ("first.Z", None, ["POSITION"]) in keys
    assert ("first.P", ["PRESSURE"], None) in keys


# --------------------------------------------------------------------------
# 6. 경계 — 파이프라인은 프로필 파일을 쓰지 않는다
# --------------------------------------------------------------------------

def test_the_pipeline_never_writes_the_profile_file():
    """취소한 분석이 아무것도 남기지 않는 것과 같은 이유 (§12회차 5).

    파일을 쓰는 곳은 `app/main.py` 하나이고, 그것은 `analyse` **뒤**에 온다.
    """
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert "legend_profile_store.save(" not in src
    assert "legend_profile_store.capture(" in src


def test_the_screen_and_the_server_read_one_judgement():
    """`_legend_facts` 하나가 판정한다 — 화면이 따로 판정하지 않는다."""
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert src.count("def _legend_facts(") == 1
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "legend_profile" in js


def test_the_fingerprint_still_ignores_the_profile():
    """지문은 `legend`·`multipliers`·행만 본다.  프로필 칸을 읽으면 안 된다."""
    from app import pipeline
    src = inspect.getsource(pipeline.fingerprint)
    assert "legend_profile" not in src
    assert '"legend"' in src and '"multipliers"' in src


def test_summary_counts_items_and_failures():
    prof = sample_profile()
    s = LP.summary(prof)
    assert s["item_count"] == len(LP.ITEMS)
    assert [i["key"] for i in s["items"]] == list(LP.ITEMS)
    assert all(i["label"] for i in s["items"]), "항목마다 사람이 읽을 이름"
    assert s["failed"] == []
