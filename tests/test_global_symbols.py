"""전역 심볼 사전 — 18회차 [D].

이 스위트가 지키는 것은 기능이 아니라 **금지**다.  §2.2 는 "전역 심볼 사전에
자동 등록" 과 "표준 사전에 프로젝트 표기 혼입" 을 금지하는데, 그 둘은 코드가
한 줄 늘어나는 것으로 조용히 깨진다.  그래서 여기서는

  (가) 사람 이름 없이는 들어가지 않는다        — `register` 가 거절한다
  (나) 넣는 코드가 **한 곳뿐**이다              — 소스 검사
  (다) 범례가 있으면 사전은 진다               — `resolve`
  (라) 끄면 사전이 없던 때와 **정확히 같다**   — `active`

를 각각 시험한다.  (나)가 이 중 유일하게 '미래' 를 지키는 시험이다.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app import global_symbols as gs

ROOT = Path(__file__).resolve().parents[1]


def test_a_symbol_cannot_be_registered_without_a_person(tmp_path):
    with pytest.raises(ValueError):
        gs.register(tmp_path, symbol_id="x", kind="VALVE_BODY",
                    name="ANGLE VALVE", author="")
    assert not gs.path(tmp_path).exists(), "거절했는데 파일이 생겼다"


def test_a_symbol_cannot_be_registered_without_saying_what_it_is(tmp_path):
    with pytest.raises(ValueError):
        gs.register(tmp_path, symbol_id="x", kind="VALVE_BODY",
                    name="   ", author="홍길동")


def test_registering_records_who_and_when(tmp_path):
    out = gs.register(tmp_path, symbol_id="VALVE_BODY:ANGLE", kind="VALVE_BODY",
                      name="ANGLE VALVE", type_value="XV", author="홍길동",
                      source_page=20)
    assert out["registered_by"] == "홍길동"
    assert out["registered_at"] > 0
    stored = json.loads(gs.path(tmp_path).read_text(encoding="utf-8"))
    assert stored["symbols"]["VALVE_BODY:ANGLE"]["name"] == "ANGLE VALVE"


def test_saving_twice_gives_the_same_file(tmp_path):
    gs.register(tmp_path, symbol_id="b", kind="VALVE_BODY", name="B", author="갑")
    gs.register(tmp_path, symbol_id="a", kind="VALVE_BODY", name="A", author="갑")
    first = gs.path(tmp_path).read_text(encoding="utf-8")
    gs.save(tmp_path, gs.load(tmp_path))
    assert gs.path(tmp_path).read_text(encoding="utf-8") == first


def test_the_legend_wins_over_the_global_dictionary(tmp_path):
    gs.register(tmp_path, symbol_id="k", kind="VALVE_BODY", name="A", author="갑")
    assert gs.resolve(tmp_path, "k", legend_has=False) is not None
    assert gs.resolve(tmp_path, "k", legend_has=True) is None, \
        "범례가 정의한 것을 전역 사전이 덮었다"


def test_turning_it_off_is_the_same_as_not_having_it(tmp_path):
    assert gs.active(tmp_path) == {}          # 없을 때
    gs.register(tmp_path, symbol_id="k", kind="VALVE_BODY", name="A", author="갑")
    assert gs.active(tmp_path) != {}
    gs.set_enabled(tmp_path, False)
    assert gs.active(tmp_path) == {}, "꺼도 사전이 살아 있다"


def test_a_broken_file_reads_as_empty_not_as_an_error(tmp_path):
    gs.path(tmp_path).parent.mkdir(parents=True, exist_ok=True)
    gs.path(tmp_path).write_text("{ this is not json", encoding="utf-8")
    assert gs.active(tmp_path) == {}


# --------------------------------------------------------------------------
# ★ 자동 등록이 생기지 않는다 — 소스 검사
# --------------------------------------------------------------------------

def test_only_one_place_in_the_tree_registers_a_symbol():
    """`register(` 를 부르는 곳은 **사람이 누른 API 하나**뿐이어야 한다.

    검출 코드나 파이프라인에서 부르기 시작하면 그 순간 자동 등록이 된다.
    시험 자신은 세지 않는다 (여기서 부르는 것은 시험이지 제품이 아니다).
    """
    callers = []
    for p in sorted((ROOT / "app").rglob("*.py")):
        text = p.read_text(encoding="utf-8")
        for m in re.finditer(r"global_symbols\.register\(|gs\.register\(", text):
            line = text[:m.start()].count("\n") + 1
            callers.append(f"{p.relative_to(ROOT)}:{line}")
    assert callers == ["app/main.py:" + callers[0].split(":")[1]], \
        f"등록을 부르는 곳이 하나가 아니다: {callers}"
    assert len(callers) == 1


def test_the_engine_never_reads_the_global_dictionary_to_decide():
    """검출 모듈은 이 사전을 **모른다**.

    18회차는 등록 화면까지만 만든다 — 사전이 검출에 닿는 순간 지문이
    사람이 누른 것에 따라 달라지고, 회귀 기준선이 성립하지 않는다.
    """
    use = re.compile(r"import\s+global_symbols|(?<![\w])global_symbols\s*\.")
    for p in sorted((ROOT / "app" / "engine").rglob("*.py")):
        assert not use.search(p.read_text(encoding="utf-8")), \
            f"{p.name} 이 전역 심볼 사전을 읽는다 — 18회차 범위 밖"


def test_finding_bodies_never_calls_the_unjudged_scan():
    """`unclassified_bodies` 는 **세는 함수**다.

    `find_bodies` 가 그것을 부르는 순간 "무엇인지 모르는 도형" 이 몸체가
    되고, 그 뜻은 아무도 정하지 않은 것이 된다.  그래서 부르는 곳은
    파이프라인의 **기록 자리 하나**뿐이어야 한다.
    """
    text = (ROOT / "app" / "engine" / "detect_valves.py").read_text(encoding="utf-8")
    body = text[text.index("def find_bodies("):text.index("def unclassified_bodies(")]
    assert "unclassified_bodies" not in body
    callers = [p.relative_to(ROOT).as_posix()
               for p in sorted((ROOT / "app").rglob("*.py"))
               if re.search(r"\.unclassified_bodies\(", p.read_text(encoding="utf-8"))]
    assert callers == ["app/pipeline.py"], f"부르는 곳: {callers}"


def test_the_pipeline_collects_unjudged_symbols_but_does_not_name_them():
    """파이프라인은 **모으기만** 한다 (§2.1 ③).

    `unjudged` 에 담기는 `why` 는 검출기가 스스로 붙인 이름을 그대로 옮긴
    것이고, 어디에도 "이것은 아마 …" 가 없어야 한다.
    """
    text = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert '"unjudged_symbols": unjudged' in text
    assert "global_symbols" not in text, "파이프라인이 전역 사전을 읽는다"
