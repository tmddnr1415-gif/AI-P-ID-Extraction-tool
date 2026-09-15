"""시험이 실 데이터에 닿지 않는다 — 그 사실을 시험으로 못박는다 (17회차 [A-2]).

배경은 저장소 뿌리의 `conftest.py` 머리 주석에 있다.  요지: `app/main.py` 는
import 시점에 `db.connect(paths.data_dir() / "app.db")` 를 부르고, 그것을
하는 시험이 다섯 자리 있었다.  16회차에 실 DB 의 sha256 이 실제로 바뀌었다.

여기서 확인하는 것은 셋이고 **전부 건너뛰지 않고 실패한다** — 건너뛰기가
14회차까지 세 회차 동안 침묵을 만들었다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import db, paths                       # noqa: E402

REAL_DATA = (ROOT / "app" / "_data").resolve()


def test_the_writing_root_is_not_the_real_one():
    """`PID_DATA_DIR` 이 시험용으로 돌아가 있는가.

    이것이 1겹이다.  `app/paths.py` 가 이미 그 용도로 둔 변수를 쓰는 것이지
    새 개념을 만든 것이 아니다.
    """
    assert os.environ.get("PID_DATA_DIR"), (
        "PID_DATA_DIR 이 비어 있습니다 — 저장소 뿌리의 conftest.py 가 안 실려 "
        "있거나 rootdir 이 다릅니다")
    assert paths.data_dir().resolve() != REAL_DATA, (
        f"시험이 실 데이터 디렉터리에 쓰려 합니다: {paths.data_dir()}")


def test_opening_the_real_database_is_an_error():
    """2겹 — 경로를 계산해 여는 코드도 막힌다.

    1겹은 환경변수를 읽는 코드만 돌린다.  `ROOT / "app" / "_data"` 처럼
    경로를 직접 만드는 코드는 그것을 지나치므로, **여는 행위 자체**를 막는다.
    """
    with pytest.raises(RuntimeError) as err:
        db.connect(REAL_DATA / "app.db")
    assert "실 데이터베이스" in str(err.value)


def test_reading_the_real_database_is_still_allowed(tmp_path):
    """읽기는 막지 않는다 — UI 스위트가 사본을 만들어 붙는 방식이 그대로 돈다.

    막아야 하는 것은 *여는 것*이다: `db.connect` 는 `journal_mode=WAL` 과
    스키마 실행을 하므로 읽기 전용이 아니다.  파일을 바이트로 읽어 사본을
    만드는 것은 원본을 건드리지 않는다.
    """
    real = REAL_DATA / "app.db"
    if not real.exists():
        # 실 DB 가 없는 기계(CI·새 체크아웃)에서는 사본 자체가 성립하지 않는다.
        # 건너뛰지 않고, 빈 파일로 같은 경로를 시험한다.
        copy = tmp_path / "app.db"
        copy.write_bytes(b"")
    else:
        copy = tmp_path / "app.db"
        copy.write_bytes(real.read_bytes())
    con = db.connect(copy)                       # 사본은 열려야 한다
    con.execute("SELECT 1")
    con.close()
