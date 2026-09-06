"""시험은 실 데이터에 닿지 않는다 — 저장소 뿌리의 pytest 설정.

**왜 여기 있나 (17회차 [A-2]).**

16회차에 `app/_data/app.db` 의 sha256 이 시험을 돌리다 바뀌었다
(`df9875e5…` → `643748dc…`, 32MB → 15.7MB).  내용은 같았고 캡처는 그 전에
끝나 있어서 그 회차는 무해했지만, **운이 좋았던 것이다.**  회사 PC 에는
팀원 여러 명의 분석이 그 파일 하나에 들어 있고, 누가 시험을 한 번 돌리면
그 파일이 열린다.

닿는 길은 **하나**다 (전수 조사: `docs/round17_test_isolation.md`):

    app/main.py:50   CON = db.connect(DB_PATH)     ← import 시점에 실행된다
    DB_PATH = paths.data_dir() / "app.db"

`from app import main` 을 하는 시험이 다섯 자리 있고, 그 중 **가장 먼저 도는
하나**가 실 DB 를 연다 (그 뒤로는 모듈이 캐시되어 다시 열지 않는다).
`db.connect` 는 읽기 전용이 아니다 — `PRAGMA journal_mode=WAL` 과
`executescript(SCHEMA)` 를 돌리므로 **파일과 `-wal`/`-shm` 을 만든다.**

14회차의 `test_zzz_the_suite_left_the_real_database_alone` 은 **UI 스위트만**
지킨다.  그 다섯 자리는 전부 빠른 스위트에 있어서 그 방어 밖이었다.

**막는 방법 — 두 겹이고, 둘 다 이미 있는 것을 쓴다.**

1. `PID_DATA_DIR` 을 버릴 폴더로 돌린다.  이 변수는 `app/paths.py` 가
   **이미 그 용도로** 두고 문서화해 둔 것이고(14회차 UI 스위트가 쓴다),
   새 개념을 만들지 않는다.  세션이 끝나면 지운다.
2. 그래도 실 `app/_data` 밑을 열려고 하면 **예외를 던진다.**  1번은 경로를
   계산해 쓰는 코드(예: `ROOT / "app" / "_data"`)를 막지 못하기 때문이다.
   건너뛰지 않고 **실패**시킨다 — 14회차 [B]4 에서 확립한 방식이다
   (건너뛰기가 세 회차 동안 침묵을 만들었다).

**읽기는 막지 않는다.**  UI 스위트는 실 DB 를 *복사*해 그 사본에 서버를
붙이고, 끝에 원본이 바이트로 같은지 본다.  그것은 `connect` 가 아니라
`read_bytes` 이므로 이 걸림에 걸리지 않는다 — 막아야 하는 것은 **여는 것**
이다.

바깥에서 `PID_DATA_DIR` 을 이미 정해 두었으면 그것을 존중한다.  회사 PC 에서
따로 폴더를 잡아 돌리는 길을 닫지 않기 위해서다.
"""

from __future__ import annotations

import atexit
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve().parent
_REAL_DATA = (_REPO / "app" / "_data").resolve()

# ── 1겹: 쓰는 뿌리를 버릴 폴더로 ────────────────────────────────────────────
# 시험 모듈이 하나라도 import 되기 전에 정해야 한다.  `app/main.py` 는 import
# 시점에 `paths.data_dir()` 를 읽기 때문이다.
_OWNED_TMP = None
if not os.environ.get("PID_DATA_DIR"):
    _OWNED_TMP = tempfile.mkdtemp(prefix="pid-test-data-")
    os.environ["PID_DATA_DIR"] = _OWNED_TMP


@atexit.register
def _drop_tmp_data_dir():
    if _OWNED_TMP:
        shutil.rmtree(_OWNED_TMP, ignore_errors=True)


# ── 2겹: 실 DB 를 여는 것 자체를 실패로 만든다 ──────────────────────────────
def _install_guard():
    from app import db

    real_connect = db.connect

    def guarded(path):
        p = Path(path).resolve()
        if p == _REAL_DATA or _REAL_DATA in p.parents:
            raise RuntimeError(
                f"시험이 실 데이터베이스를 열려고 했습니다: {p}\n"
                f"이 파일에는 팀원의 분석이 들어 있고, `db.connect` 는 읽기 전용이 "
                f"아닙니다 (journal_mode=WAL · 스키마 실행).\n"
                f"시험은 `PID_DATA_DIR` 이 가리키는 곳에서만 돌아야 합니다 "
                f"(지금 값: {os.environ.get('PID_DATA_DIR')}).\n"
                f"실 DB 를 *읽기만* 하는 것은 막지 않습니다 — 사본을 만들어 그 "
                f"사본에 붙이세요 (tests/test_ui_edits.py 가 그렇게 합니다)."
            )
        return real_connect(path)

    guarded.__wrapped__ = real_connect
    db.connect = guarded


_install_guard()


# ── 합격 기준: 세션 전체에서 실 DB 가 바이트로 불변인가 ─────────────────────
#
# 걸림(2겹)이 여는 것을 막지만, 막았다는 것을 **증명**하는 것은 다른 일이다.
# 14회차 `test_zzz_the_suite_left_the_real_database_alone` 이 UI 스위트에서
# 하던 확인을 세션 전체로 넓힌다.  여기서만 할 수 있다 — 어느 시험 파일에
# 두어도 그 파일 뒤에 도는 시험은 못 본다.
_REAL_DB = _REAL_DATA / "app.db"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


_DIGEST_AT_START = _sha(_REAL_DB)


def pytest_sessionfinish(session, exitstatus):
    if not _DIGEST_AT_START:
        return
    after = _sha(_REAL_DB)
    if after != _DIGEST_AT_START:
        session.exitstatus = 1
        print(
            f"\n실 데이터베이스가 시험 도중 바뀌었습니다: {_REAL_DB}\n"
            f"  before {_DIGEST_AT_START[:16]}…\n  after  {after[:16]}…\n"
            f"시험은 `PID_DATA_DIR` 안에서만 써야 합니다."
        )
