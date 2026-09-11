"""승수를 사람이 지정하는 자리 — **범례를 못 이긴다** (31회차).

이 시험이 지키는 것 넷:

    ① 작성자 없이 저장되지 않는다 (팀이 공유하는 값이다 · 13회차 자기신고)
    ② 끄면 없던 때와 **정확히** 같아진다 (읽는 곳이 `table()` 하나다)
    ③ **읽는 순서**: 범례 → NOTES → 사람 → 설정 폴백 → 빈칸.
       범례나 노트가 답하면 사람 값은 **무시된다** — 이것이 §9 의 핵심이고,
       AL NOUF1 의 `Q'ty 1931` 이 사람 값에 흔들리지 않는 이유다
    ④ 파이프라인은 파일을 읽지 않는다 (15회차 `legend_profile` 과 같은 모양)
"""
from __future__ import annotations

import inspect
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import unit_multipliers as um  # noqa: E402
from app import pipeline  # noqa: E402
from app.engine import projectconfig  # noqa: E402


# --------------------------------------------------------------------------
# ① 작성자
# --------------------------------------------------------------------------
def test_an_author_is_required(tmp_path):
    with pytest.raises(ValueError):
        um.set_unit(tmp_path, "P", unit="10", multiplier=4, author="")
    assert um.table(tmp_path, "P") == {}


def test_a_multiplier_below_one_is_refused(tmp_path):
    with pytest.raises(ValueError):
        um.set_unit(tmp_path, "P", unit="10", multiplier=0, author="sc.y")


def test_a_project_is_required(tmp_path):
    with pytest.raises(ValueError):
        um.set_unit(tmp_path, "", unit="10", multiplier=4, author="sc.y")


# --------------------------------------------------------------------------
# ② 저장 · 되돌리기 · 끄기
# --------------------------------------------------------------------------
def test_it_stores_who_and_when(tmp_path):
    rec = um.set_unit(tmp_path, "P", unit="10", multiplier=4,
                      author="sc.y", note="발주처 회신 2026-09-11", job_id="J1")
    assert rec["multiplier"] == 4 and rec["author"] == "sc.y"
    assert rec["note"] and rec["set_at"] and rec["origin_job"] == "J1"
    assert um.table(tmp_path, "P") == {"10": 4}


def test_clearing_returns_to_the_state_before(tmp_path):
    um.set_unit(tmp_path, "P", unit="10", multiplier=4, author="sc.y")
    assert um.clear_unit(tmp_path, "P", "10") is True
    assert um.table(tmp_path, "P") == {}
    assert um.clear_unit(tmp_path, "P", "10") is False


def test_disabling_is_exactly_the_same_as_never_having_set_it(tmp_path):
    um.set_unit(tmp_path, "P", unit="10", multiplier=4, author="sc.y")
    um.set_enabled(tmp_path, "P", False)
    assert um.table(tmp_path, "P") == {}          # 없던 때와 같다
    um.set_enabled(tmp_path, "P", True)
    assert um.table(tmp_path, "P") == {"10": 4}


def test_an_unbound_analysis_reads_nothing(tmp_path):
    assert um.table(tmp_path, "") == {}


# --------------------------------------------------------------------------
# ③ 읽는 순서 — ★ 이 회차의 핵심
# --------------------------------------------------------------------------
def _note(n):
    """`note_unit_span` 이 내는 모양 — (개수, 유닛 표기들, 원문, 범위인가)."""
    return (n, ["3-1", "3-2"], "…", False) if n else (None, [], "", False)


def test_the_legend_wins_over_the_person():
    """범례가 답했으면(undefined 도 borrowed 도 아님) 사람 값은 안 쓰인다."""
    out = pipeline._note_factor(4, False, False, _note(None), user=9)
    assert out[0] == 4                      # 범례 값 그대로
    assert out[4] is False                  # 사람 값 안 씀


def test_the_note_wins_over_the_person():
    """노트가 답했으면 사람 값은 안 쓰인다 (§9 ② > ③)."""
    out = pipeline._note_factor(1, False, True, _note(8), user=9)
    assert out[0] == 8 and out[3] is True and out[4] is False


def test_the_person_beats_the_config_fallback():
    """남의 도면에서 온 폴백보다 사람 값이 세다 (26회차가 시끄럽게 말하던 행)."""
    out = pipeline._note_factor(1, False, True, _note(None), user=9)
    factor, undefined, borrowed, from_note, from_user = out
    assert factor == 9 and borrowed is False and from_user is True


def test_the_person_fills_an_undefined_unit():
    """SADARA 처럼 범례가 그 유닛을 정의하지 않은 경우."""
    out = pipeline._note_factor(projectconfig.UNDEFINED, True, False,
                                _note(None), user=4)
    factor, undefined, borrowed, from_note, from_user = out
    assert factor == 4 and undefined is False and from_user is True


def test_without_a_person_value_nothing_changes():
    """사람 값이 없으면 27회차와 글자 그대로 같다 — 게이트 1의 근거."""
    for args in ((4, False, False, _note(None)),
                 (1, False, True, _note(None)),
                 (projectconfig.UNDEFINED, True, False, _note(None)),
                 (1, False, True, _note(8))):
        assert pipeline._note_factor(*args, user=None)[:4] == \
               pipeline._note_factor(*args)[:4]


# --------------------------------------------------------------------------
# ④ 파이프라인은 파일을 읽지 않는다
# --------------------------------------------------------------------------
def test_the_pipeline_never_opens_the_file():
    """15회차 `legend_profile` 과 같은 모양 — 부르는 쪽이 읽어서 넘긴다.

    그래서 회귀 하네스(`spike/analyse_one.py`)는 아무 것도 넘기지 않고,
    **사람 값이 없는 상태의 불변이 구조적으로 보장된다.**
    """
    src = inspect.getsource(pipeline)
    assert "unit_multipliers.load" not in src
    assert "unit_multipliers.table" not in src
    assert "unit_multipliers" in inspect.signature(pipeline.analyse).parameters


# --------------------------------------------------------------------------
# ⑤ 화면이 묻는 단위 — **행이 아니라 유닛코드**
# --------------------------------------------------------------------------
def _tiny_job(tmp_path):
    """저장된 SADARA 결과로 임시 DB 하나.  실 DB 는 건드리지 않는다 (17회차)."""
    import os, time, json as J
    src = ROOT / "out" / "regression_3p" / "SADARA.json"
    if not src.exists():
        pytest.skip("SADARA 결과 json 이 없는 기계")
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    from app import db
    result = J.loads(src.read_text())["result"]
    con = db.connect(tmp_path / "app.db")
    job = "tmult0000001"
    con.execute("INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,"
                "status,progress,message,fingerprint,project,revision)"
                " VALUES (?,?,?,?,?,'done',1.0,'','','SADARA','A')",
                (job, "x.pdf", "x", "x", time.time()))
    con.commit()
    db.store_result(con, job, result)
    con.commit()
    return con, job


def test_the_screen_asks_once_per_unit_code_not_once_per_row(tmp_path):
    """SADARA 는 유닛 `10` 하나에 82행이다 — **82번 묻지 않는다.**

    ⚠ 이 시험이 있는 이유: 31회차에 이 API 가 행 접근자 때문에 두 번 깨졌고
    (`db.rows_for` 없음 · `r["qty"]` 없음), 화면은 조용히 빈 채로 떴다.
    """
    con, job = _tiny_job(tmp_path)
    from app import main
    main.CON, main.DATA_DIR = con, tmp_path
    out = main._multiplier_targets(job)
    assert len(out["groups"]) == 1, out["groups"]
    g = out["groups"][0]
    assert g["unit"] == "10"          # 도면번호에서 나온다 (parse_unit_code)
    assert g["rows"] == 82 and g["sheets"] == 4
    assert g["codes"] == ["MULTIPLIER_UNDEFINED"]
    assert g["set"] is None


def test_setting_and_clearing_shows_up_in_the_same_answer(tmp_path):
    con, job = _tiny_job(tmp_path)
    from app import main
    main.CON, main.DATA_DIR = con, tmp_path
    um.set_unit(tmp_path, "SADARA", unit="10", multiplier=4, author="sc.y",
                note="시험", job_id=job)
    g = main._multiplier_targets(job)["groups"][0]
    assert g["set"] and g["set"]["multiplier"] == 4 and g["set"]["author"] == "sc.y"
    um.clear_unit(tmp_path, "SADARA", "10")
    assert main._multiplier_targets(job)["groups"][0]["set"] is None
