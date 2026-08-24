"""④ 행 FROM/TO 사용자 확정(6회차)의 빠른 단위 시험 — 합성 값만 쓴다."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import axis_overrides as ov


def test_source_classification_uses_only_drawing_text():
    cands = ["FROM HRSG#12", "HP TURBINE IP TURBINE", "TO CLEAN DRAIN TANK"]
    assert ov.classify_source("FROM HRSG#12", cands) == ov.SOURCE_PICK
    # 병합된 도면 텍스트에서 일부만 쓰면 — 도면 문구이되 다듬은 것
    assert ov.classify_source("HP TURBINE", cands) == ov.SOURCE_PICK_PART
    assert ov.classify_source("MY OWN WORDS", cands) == ov.SOURCE_FREE
    assert ov.classify_source("  from   hrsg#12 ", cands) == ov.SOURCE_PICK


def test_sentence_strips_leading_from_to():
    s = ov.sentence_for("FROM HRSG#12", "TO HP TURBINE", "TIT")
    assert s == "FROM HRSG#12 TO HP TURBINE TEMPERATURE TRANSMITTER"
    # 방향어 없는 후보(기기 라벨)도 그대로 통한다
    s = ov.sentence_for("HRSG#12", "HP TURBINE", "TIT", "A")
    assert s == "FROM HRSG#12 TO HP TURBINE TEMPERATURE TRANSMITTER A"


def test_suffix_positional_and_only_in_groups():
    rows = [("k1", (10, 50, 20, 60)), ("k2", (10, 10, 20, 20))]
    assert ov.suffix_for(rows, "k2") == "A"    # 위쪽이 A
    assert ov.suffix_for(rows, "k1") == "B"
    assert ov.suffix_for([("k1", (0, 0, 1, 1))], "k1") == ""   # 혼자면 없음


def test_record_is_deterministic(tmp_path):
    p = tmp_path / "axis_overrides.json"
    kw = dict(from_text="FROM HRSG#12", to_text="HP TURBINE",
              source_from=ov.SOURCE_PICK, source_to=ov.SOURCE_PICK_PART,
              type_="TIT", sentence="FROM HRSG#12 TO HP TURBINE ...",
              origin_job="job-a")
    ov.record(p, "10LBA10-001", **kw)
    first = p.read_bytes()
    ts = json.loads(first.decode())["10LBA10-001"]["confirmed_at"]
    time.sleep(1.1)
    ov.record(p, "10LBA10-001", **kw)          # 같은 값 재확정
    assert p.read_bytes() == first, "두 번 저장하면 같은 파일이어야 한다"
    ov.record(p, "10LBA10-001", **dict(kw, to_text="LP TURBINE",
                                       sentence="…"))
    changed = json.loads(p.read_text())["10LBA10-001"]
    assert changed["to"] == "LP TURBINE"
    assert changed["confirmed_at"] >= ts       # 값이 바뀌면 시각이 갱신된다


def test_clear_removes_entry(tmp_path):
    p = tmp_path / "axis_overrides.json"
    ov.record(p, "X-001", from_text="A", to_text="B", source_from="자유입력",
              source_to="자유입력", type_="PI", sentence="s", origin_job="j")
    assert ov.clear(p, "X-001") is True
    assert ov.load(p) == {}
    assert ov.clear(p, "X-001") is False


def test_inherit_rules():
    overrides = {
        "10LBA10-001": {"sentence": "S1", "origin_job": "job-a"},
        "10LBA10-002": {"sentence": "S2", "origin_job": "job-a"},
        "10LBA10-003": {"sentence": "S3", "origin_job": "job-b"},
    }
    states = {"k1": {"id": "10LBA10-001"},     # 매칭 → 승계
              "k2": {"id": "10LBA10-002"},     # 사람이 이미 고침 → 승계 안 함
              "k3": {"id": "10LBA10-003"},     # 이 job 의 원본 확정 → 승계 아님
              "k4": {"id": "10LBA10-009"}}     # ID 가 장부에 없음 → 지어내지 않음
    rows = {"k1": {"user": {}}, "k2": {"user": {"description": "손으로"}},
            "k3": {"user": {}}, "k4": {"user": {}}}
    got = ov.inherit(overrides, states, rows, job_id="job-b")
    assert got == [("k1", overrides["10LBA10-001"])]


def test_candidate_noise_filter_keeps_names(monkeypatch):
    """후보 목록의 잡음 필터 — 거르기만 하고 아무것도 만들지 않는다.

    p6 실측(38건)에서 그리드 셀 · 점선 리더 · DN 치수 · 도면번호 · 배관 치수 ·
    ASME 코드 · 버블 안 ISA 글자가 빠지고 이름이 남는지 본다.
    """
    from app import main
    noise = ["(G-8)", ".", "..... .....", "550X700 700X550", "ASME ASME",
             "B31.1 SEC.I", "D00P-10MAN10-M05-0001", "DN300", "DN 50",
             "PT PT", "TT TT TT PT PT PT TT", "C", "FE"]
    names = ["HP TURBINE IP TURBINE", "LP TURBINE", "HRSG", "STG#10",
             "SCT", "SUPPLIER", "MOV", "CEP", "#10 SURFACE CONDENSER"]
    for t in noise:
        assert main._axis_text_noise(t), f"잡음인데 남았습니다: {t!r}"
    for t in names:
        assert not main._axis_text_noise(t), f"이름인데 걸렸습니다: {t!r}"
