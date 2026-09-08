"""실패 화면이 **어디서 멈췄는지** 말하는가 (21회차).

## 왜 이 파일이 있나

회사 PC 에서 새 프로젝트 PDF 가 17분 만에 실패했고, 화면에 남은 것은 이것이
전부였다:

    이 PDF 를 분석하지 못했습니다. 사유를 특정하지 못했습니다.
    도면을 한 장도 읽기 전에 멈췄습니다 (17분 11초)

**"한 장도 읽기 전" 이 덮는 구간이 실제로는 여섯 단계다** — 문서 열기 ·
치수 재기 · 타이틀블록 · 범례 규칙 · 유닛 승수 · 대상 선별.  그 여섯 중
어디인지를 말하지 않으면 다음에 할 일이 서지 않는다.

## 고친 방법 — 없는 것을 만들지 않았다

파이프라인은 단계마다 `set_progress` 로 그 이름을 `job.message` 에 적고
있었고(`measuring sheet 37 of 60` 처럼), **실패 처리가 같은 칸을 사유 문장으로
덮어써서 그 사실이 사라지고 있었다.**  덮기 전에 한 번 읽어 `stopped_stage`
에 옮겨 적기만 한다.

담는 것은 파이프라인이 쓴 **원문 그대로**이고 화면 문장이 아니다 — 한국어로
옮기는 것은 화면의 `stageWords()` 가 이미 하고, 모르는 값은 그대로 쓴다
(15회차 `compare_note` 가 가르친 것: 문장을 저장하면 문구를 고쳐도 옛 분석이
옛 문장을 계속 말한다).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))


@pytest.fixture()
def con(tmp_path):
    from app import db
    c = db.connect(tmp_path / "app.db")
    c.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, status,"
              " created_at) VALUES ('j1','x.pdf','sha','/x.pdf','running',0)")
    c.commit()
    return c


def test_the_stage_column_starts_empty_and_takes_the_raw_stage_name(con):
    """빈 값은 "모른다" 이지 "없다" 가 아니다 — 옛 분석은 빈 채로 남는다."""
    from app import db
    assert db.get_job(con, "j1")["stopped_stage"] == ""
    db.set_stopped_stage(con, "j1", "measuring sheet 37 of 60")
    assert db.get_job(con, "j1")["stopped_stage"] == "measuring sheet 37 of 60"


def test_the_stage_is_stored_as_the_pipeline_wrote_it_not_as_a_sentence(con):
    """저장하는 것은 **사실**이고 화면 문장이 아니다 (15회차)."""
    from app import db
    db.set_stopped_stage(con, "j1", "measuring rules off the legend sheets")
    got = db.get_job(con, "j1")["stopped_stage"]
    assert got == "measuring rules off the legend sheets"
    # 한국어가 데이터에 들어가면 문구를 고쳐도 옛 분석이 옛 문장을 말한다.
    assert not any("가" <= ch <= "힣" for ch in got)


def test_the_failure_reason_does_not_erase_the_stage(con):
    """★ 이것이 이번 회차의 결함이다.

    `set_progress` 는 `message` 를 사유로 덮는다.  덮기 **전에** 읽어 두지
    않으면 단계가 사라진다 — 실패 처리의 순서가 곧 이 시험의 대상이다.
    """
    from app import db
    db.set_progress(con, "j1", 0.5, "measuring rules off the legend sheets")
    before = db.get_job(con, "j1")["message"]          # 덮기 전에 읽는다
    db.set_stopped_stage(con, "j1", before)
    db.set_progress(con, "j1", 0.0, "이 PDF 를 분석하지 못했습니다.", "failed")
    row = db.get_job(con, "j1")
    assert row["message"].startswith("이 PDF 를 분석하지 못했습니다")
    assert row["stopped_stage"] == "measuring rules off the legend sheets"


def test_both_failure_branches_read_the_stage_before_overwriting():
    """소스 검사 — 두 갈래 다 `set_progress` **앞**에서 단계를 읽는가.

    한쪽만 고치면 다음 회차에 갈린다.  `LegendUnavailable` 갈래와 일반 예외
    갈래가 **둘 다** 그 순서를 지키는지를 소스에서 본다.
    """
    src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert src.count("_stopped_stage(job_id)") == 2, "실패 갈래는 둘이다"
    for chunk in src.split("_stopped_stage(job_id)")[1:]:
        head = chunk[:400]
        assert "db.set_progress(" in head, "같은 갈래 안에서 사유를 적어야 한다"
        assert head.index("db.set_progress(") < head.index("db.set_stopped_stage("), \
            "단계를 읽는 것이 사유로 덮기보다 먼저여야 한다"


def test_the_screen_makes_the_sentence_not_the_server():
    """화면이 `stageWords()` 로 옮기는가 — 서버는 원문만 보낸다."""
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    fn = js.split("async function showFailure(")[1].split("\nasync function ")[0]
    assert "stageWords(d.stopped_stage)" in fn, "화면이 옮겨야 한다"
    py = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert '"stopped_stage": stage' in py, "서버는 사실만 실어 보낸다"


def test_every_stage_name_the_pipeline_writes_has_a_korean_word():
    """파이프라인이 쓰는 단계 이름을 화면이 전부 옮길 수 있는가.

    옮기지 못하면 `stageWords` 가 원문을 그대로 쓴다 — 틀리지는 않지만
    영어가 그대로 나간다.  **도면을 읽기 전** 구간의 이름은 전부 덮는다.
    """
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    before_sheets = [
        "opening the document",
        "measuring the sheet",
        "reading title blocks",
        "measuring rules off the legend sheets",
        "deriving unit multipliers from legend page 5",
    ]
    for name in before_sheets:
        assert f'"{name}"' in js, f"STAGE_KO 에 {name} 이 없다"
    # 쪽 번호가 붙는 둘은 정규식이 받는다.
    assert "measuring sheet (\\d+) of (\\d+)" in js
    assert "^\\d+ sheets to read$" in js
    # 그리고 그 이름들이 실제로 파이프라인이 쓰는 것과 같아야 한다.
    pipe = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    for name in before_sheets:
        assert name in pipe, f"파이프라인이 {name} 을 쓰지 않는다"
