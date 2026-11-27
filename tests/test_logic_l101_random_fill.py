"""L101 — 동작 우선: 사용자가 값을 넣지 않은 자리는 임의값으로 동작시킨다 (사용자 지시).  임의값은 도면 값이 아니다 — 근거 글에 '임의값' 이라고 적는다."""
from app.logic import aops


def _pid():
    return {"func": "PID", "label": "PID", "read": "PID", "param": {}}


def test_off_by_default_in_tests_and_exact_compute_never_invents(monkeypatch):
    monkeypatch.setenv("PID_LOGIC_RANDOM_FILL", "0")
    v, why = aops.compute("pid", _pid(), [("n1", None)], {"n1": 50.0})
    assert v is None and "PID" in why
    assert aops._compute_exact("pid", _pid(), [("n1", None)], {"n1": 50.0})[0] is None


def test_unset_value_runs_on_a_labelled_random_value_and_a_user_value_wins(monkeypatch):
    monkeypatch.setenv("PID_LOGIC_RANDOM_FILL", "1")
    v, why = aops.compute("pid", _pid(), [("n1", None)], {"n1": 50.0})
    assert v is not None and 10.0 <= v <= 90.0 and why.startswith("임의값") and "PID 출력" in why      # 원래 사유도 같이 남는다
    assert aops.compute("pid", _pid(), [("n1", None)], {"n1": 50.0})[0] == v                            # 같은 자리는 같은 값 (계산 기억 · 화면이 흔들리지 않게)
    b = {**_pid(), "param": {"a_user": {"out": 33.0}}}
    if aops.params(b).get("out") is not None:                                                           # 사람이 넣은 출력값이 있으면 그 값
        assert aops.compute("pid", b, [("n1", None)], {"n1": 50.0}) == (33.0, "사람이 정한 출력값")


def test_random_value_depends_on_meaning_not_on_position():
    """원본 분석 · 똑같이 그린 그림 · 그 그림을 다시 올린 것이 같은 값을 받아야 서로 견줄 수 있다 — 좌표는 씨에 넣지 않는다."""
    a = aops.stable_random("pid")
    assert a == aops.stable_random("pid") and a != aops.stable_random("const")
    import os
    os.environ["PID_LOGIC_RANDOM_FILL"] = "1"
    try:                                                    # 상자 글자가 달라도(되읽기) 같은 연산 · 같은 단자면 같은 값
        v1 = aops.compute("pid", {"func": "PID", "label": "PID", "param": {}}, [("n", None)], {"n": 1.0})[0]
        v2 = aops.compute("pid", {"func": "UNKNOWN", "label": "", "param": {}}, [("m", None)], {"m": 1.0})[0]
    finally:
        os.environ["PID_LOGIC_RANDOM_FILL"] = "0"
    assert v1 == v2
    assert all(10.0 <= aops.stable_random("x", i) <= 90.0 for i in range(200))


def test_computable_operator_is_never_replaced_by_a_random_value(monkeypatch):
    monkeypatch.setenv("PID_LOGIC_RANDOM_FILL", "1")
    b = {"func": "SUMMING", "label": "Σ", "read": "Σ", "param": {}}
    v, why = aops.compute("sum", b, [("a", None), ("b", None)], {"a": 1.5, "b": 2.0})
    assert v == 3.5 and "임의값" not in why
