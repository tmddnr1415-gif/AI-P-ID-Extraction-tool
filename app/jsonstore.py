"""프로젝트 상태 파일(JSON)을 깨지지 않게 쓰고, 깨졌으면 사람 말로 다룬다 (hotfix74).

돌발상황 시뮬레이션(`spike/state_chaos.py`) — 장부·승수·메모 같은 상태 파일은 전부
`path.write_text(...)` 로 **제자리에** 쓰고 있었다.  쓰는 도중 전원이 나가거나 프로세스가
죽으면 반쯤 쓴 파일이 남고, 그다음은 둘 중 하나였다:

* 안정 ID 장부(`id_registry.json`) · 프로젝트 장부(`project.json`) — 읽을 때 `JSONDecodeError`
  로 첫 화면·분석이 영문 예외로 멈춘다.
* 사람이 적은 값(승수 · 도면번호 · 칸 · 메모 …) — 읽기가 예외를 삼키고 **빈 값**을 돌려줘
  사람이 적은 것이 조용히 사라지고, 다음 저장이 깨진 원본을 덮어 증거까지 없어진다.

그래서 셋을 한다.

1. **쓰기는 원자적이다** — 같은 폴더의 임시 파일에 다 쓰고 `fsync` 한 뒤 `os.replace`.
   언제 죽어도 원본은 옛 판 그대로이거나 새 판 그대로다.  바로 앞 판은 `.bak` 으로 남긴다.
2. **깨진 파일은 지우지 않는다** — `<이름>.corrupt-<시각>` 으로 옆에 떠 둔다 (증거).
3. **백업이 있으면 그것으로 되살리고, 없으면** 꼭 있어야 하는 장부는 사람 말로 멈추고
   (`StateFileCorrupt` — 안정 ID 를 1부터 다시 내면 §7.3 이 깨진다), 사람 값 파일은 빈 값으로
   계속하되 **그 사실을 남긴다** (`INCIDENTS` → 위생 감사가 첫 화면에 말한다).
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path

log = logging.getLogger("pid.jsonstore")

_MISSING = object()
# 이 프로세스에서 만난 깨진 파일 — 위생 감사(`app/audit.py`)가 첫 화면에 말한다.
INCIDENTS: list = []
_LOCK = threading.Lock()
_SEEN: dict = {}            # 깨진 판의 (mtime, 크기) → 이미 떠 두고 기록했다


class StateFileCorrupt(RuntimeError):
    """꼭 있어야 하는 상태 파일이 깨졌고 되살릴 백업이 없다.  문장은 여기서 만든다."""


def _bak(path: Path) -> Path:
    return path.with_name(path.name + ".bak")


def write(path: Path, data, *, indent=1, sort_keys=True) -> Path:
    """원자적 저장.  내용은 예전 `write_text(json.dumps(...) + "\\n")` 와 바이트까지 같다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, sort_keys=sort_keys, indent=indent) + "\n"
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}-{threading.get_ident()}")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:                                 # 일부 파일 시스템은 fsync 를 못 한다
            pass
    with _LOCK:
        if path.exists():
            try:
                shutil.copy2(path, _bak(path))          # 바로 앞 판 — 복사가 반쯤이어도 원본은 그대로
            except OSError:
                pass
        # Windows 에서는 다른 프로그램(백신 · 편집기)이 그 파일을 잠깐 열고 있으면 `os.replace` 가
        # PermissionError 로 실패한다 — 잠깐씩 기다려 몇 번 더 해 본다.  그래도 안 되면 임시 파일을 치우고 알린다.
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 5:
                    try:
                        tmp.unlink()
                    except OSError:
                        pass
                    raise
                time.sleep(0.05 * (attempt + 1))
    return path


def _parse(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class _WrongShape(ValueError):
    pass


def read(path: Path, default=_MISSING, *, what: str = "", required: bool = False, expect=None):
    """읽기.  없으면 `default` (주지 않았으면 FileNotFoundError).

    깨졌으면: 옆에 떠 두고 → `.bak` 이 읽히면 그것으로 되살려 돌려주고 → 아니면
    `required` 면 `StateFileCorrupt`, 아니면 `default` (그리고 `INCIDENTS` 에 남긴다).
    """
    path = Path(path)
    if not path.exists():
        if default is _MISSING:
            raise FileNotFoundError(path)
        return default
    try:
        data = _parse(path)
        if expect is not None and not isinstance(data, expect):
            # JSON 으로는 읽히지만 모양이 틀렸다 (사전 자리에 목록) — 깨진 것과 같게 다룬다.
            raise _WrongShape(f"{expect.__name__} 이 아니라 {type(data).__name__}")
        return data
    except (ValueError, UnicodeDecodeError) as exc:
        # 같은 깨진 판을 거듭 읽어도(첫 화면이 몇 초마다 묻는다) 떠 두기·기록은 한 번만.
        try:
            st = path.stat()
            sig = (st.st_mtime_ns, st.st_size)
        except OSError:
            sig = None
        seen = _SEEN.get(str(path))
        if sig is not None and seen is not None and seen[0] == sig:
            if seen[1] is not None:
                return seen[1]
            if required or default is _MISSING:
                raise StateFileCorrupt(seen[2]) from exc
            return default
        stamp = time.strftime("%Y%m%d-%H%M%S")
        aside = path.with_name(f"{path.name}.corrupt-{stamp}")
        try:
            shutil.copy2(path, aside)
        except OSError:
            aside = None
        label = what or path.name
        bak = _bak(path)
        restored = None
        if bak.exists():
            try:
                restored = _parse(bak)
                if expect is not None and not isinstance(restored, expect):
                    restored = None
            except (ValueError, UnicodeDecodeError, OSError):
                restored = None
        rec = {"path": str(path), "what": label, "error": f"{type(exc).__name__}: {exc}"[:200],
               "aside": aside.name if aside else "", "restored": restored is not None,
               "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        with _LOCK:
            INCIDENTS.append(rec)
        if restored is not None:
            log.warning("%s 가 깨져 있어 바로 앞 판(.bak)으로 되살렸습니다 — 깨진 파일은 %s", path, rec["aside"])
            try:
                with _LOCK:
                    shutil.copy2(bak, path)
            except OSError:
                _SEEN[str(path)] = (sig, restored, "")
            return restored
        log.error("%s 가 깨져 있고 되살릴 백업이 없습니다 — 깨진 파일은 %s", path, rec["aside"])
        msg = (f"{label} 파일이 깨져 있습니다 ({path.name}) — 저장 도중 전원이 꺼졌거나 디스크 문제일 수 "
               f"있습니다.  되살릴 백업(.bak)이 없어 멈춥니다 (지어낸 값으로 계속하면 안정 ID 가 어긋납니다).  "
               f"깨진 파일은 {rec['aside'] or '그 자리에'} 남겨 두었습니다 — 관리자에게 알려 주세요.")
        _SEEN[str(path)] = (sig, None, msg)
        if required or default is _MISSING:
            raise StateFileCorrupt(msg) from exc
        return default


# 읽고-고치고-쓰는 함수를 줄 세운다 (hotfix74).  요청은 스레드 여럿에서 오므로, 두 사람이 같은 파일의 다른 칸을
# 동시에 고치면 둘 다 옛 판을 읽고 각자 쓴 뒤 **나중 쓴 쪽만 남았다** — 실측: 유닛 승수 30개를 동시에 지정하면
# 3개만 남았다 (`spike/state_chaos.py` 의 동시 저장 · 시험 `test_concurrent_mutations_do_not_lose_updates`).
# 상태 파일은 작고 사람이 누르는 빈도로 쓰이므로 프로세스 전체에 잠금 하나로 충분하다.
STATE_LOCK = threading.RLock()


def serialized(fn):
    """상태 파일을 읽고-고치고-쓰는 함수에 붙인다."""
    import functools

    @functools.wraps(fn)
    def run(*a, **k):
        with STATE_LOCK:
            return fn(*a, **k)
    return run


def incidents() -> list:
    with _LOCK:
        return list(INCIDENTS)
