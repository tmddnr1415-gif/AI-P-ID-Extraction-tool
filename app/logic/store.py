"""LOGIC 묶음의 저장 자리 — `{data}/logic/<job>/` (P&ID 의 uploads · DB 와 따로).

  source.pdf     올린 PDF (그대로)
  status.json    상태 · 진행 (분석 프로세스가 쓴다)
  result.json    analyse.py 결과
  pages/p<n>_z<zoom>.png   장 그림 캐시

DB 를 쓰지 않는다 — 기존 표에 손대지 않고(지시문 §3), 이 회차에 필요한 것은 파일로 충분하다.
"""
from __future__ import annotations

import gc
import json
import os
import re
import time
import uuid
from pathlib import Path

from app import paths

JOB_RE = re.compile(r"^[0-9a-f]{12}$")
ZOOM = 2.5                      # 장 그림 배율 (A3 1191pt → 약 2980px) — api · run 이 같은 값을 쓴다


def root() -> Path:
    p = paths.data_dir() / "logic"
    p.mkdir(parents=True, exist_ok=True)
    return p


def job_dir(job: str) -> Path:
    if not JOB_RE.match(job or ""):
        raise KeyError(job)
    d = root() / job
    if not d.is_dir():
        raise KeyError(job)
    return d


def new_job(name: str) -> tuple[str, Path]:
    job = uuid.uuid4().hex[:12]
    d = root() / job
    d.mkdir(parents=True)
    write_status(d, {"state": "queued", "name": name, "created": time.time(), "stage": "", "done": 0, "total": 0})
    return job, d


REPLACE_TRIES = 20             # Windows: 다른 프로세스(화면이 진행을 읽는 서버 · 백신)가 그 파일을 잠깐 열고 있으면
REPLACE_WAIT = 0.05            # os.replace 가 WinError 5 로 거절된다 — 잠깐 기다렸다 다시 (P&ID jsonstore 와 같은 길)


def _replace(tmp: Path, path: Path):
    wait = REPLACE_WAIT
    for i in range(REPLACE_TRIES):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == REPLACE_TRIES - 1:
                raise
            time.sleep(wait)
            wait = min(wait * 2, 0.5)


def _atomic(path: Path, data: str):
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    tmp.write_text(data, encoding="utf-8")
    try:
        _replace(tmp, path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_status(d: Path, st: dict) -> bool:
    """진행 상태 — 표시용이라 못 써도 분석을 멈추지 않는다 (L20 · 현장 WinError 5).  썼으면 True."""
    text = json.dumps(st, ensure_ascii=False)
    try:
        _atomic(d / "status.json", text)
        return True
    except OSError:
        pass
    try:                        # 바꿔 넣기가 끝내 막히면 그 자리에 바로 쓴다 (읽는 쪽은 깨진 글을 견딘다)
        (d / "status.json").write_text(text, encoding="utf-8")
        return True
    except OSError:
        return False            # 이번 진행 한 줄은 건너뛴다 — 다음 진행이 다시 쓴다


_LAST_STATUS: dict = {}
_DEL_LOCK = __import__("threading").Lock()


def read_status(d: Path) -> dict:
    """쓰는 중이라 못 읽거나(잠김 · 반쯤 쓴 글) 깨졌으면 직전에 읽은 상태를 돌려준다."""
    key = str(d)
    try:
        st = json.loads((d / "status.json").read_text(encoding="utf-8"))
    except Exception:
        return dict(_LAST_STATUS.get(key) or {"state": "unknown"})
    if len(_LAST_STATUS) > 256:
        _LAST_STATUS.clear()
    _LAST_STATUS[key] = st
    return st


def write_result(d: Path, res: dict):
    text = json.dumps(res, ensure_ascii=False)
    try:
        _atomic(d / "result.json", text)
    except OSError:             # 끝내 막히면 그 자리에 바로 쓴다 — 결과는 버리지 않는다
        (d / "result.json").write_text(text, encoding="utf-8")


def write_partial(d: Path, part: dict):
    """L25 — 분석 중 지금까지 읽은 장 (가르치기 질문을 분석이 끝나기 전에 낸다).  실패해도 분석은 그대로."""
    try:
        _atomic(d / "partial.json", json.dumps(part, ensure_ascii=False))
    except Exception:
        pass


def read_partial(d: Path):
    try:
        return json.loads((d / "partial.json").read_text(encoding="utf-8"))
    except Exception:
        return None


def drop_partial(d: Path):
    try:
        (d / "partial.json").unlink()
    except OSError:
        pass


from collections import OrderedDict

RES_KEEP = 3                   # L28 — 메모리에 들고 있는 결과 수 (846쪽 묶음 하나가 파이썬 객체로 약 200MB) · 가장 오래 안 본 것부터 놓는다
_RES = OrderedDict()
_RES_LOCK = __import__("threading").Lock()


def read_result(d: Path, fast=None) -> dict:
    """fast — L68 (api 가 준다): (load, prepare) · load(d) 가 준비해 둔 결과 사본을 돌려주면 37MB JSON 을 다시 읽지
    않는다 · 없으면 JSON 을 읽고 prepare(res) 가 준비해(설정값 · 연산자 이름 · from-to) 사본을 남긴다."""
    p = d / "result.json"
    st = p.stat().st_mtime
    key = str(p)
    hit = _RES.get(key)
    if hit and hit[0] == st:
        try:
            _RES.move_to_end(key)
        except KeyError:
            pass
        return hit[1]
    with _RES_LOCK:                # 두 요청이 같은 37MB 를 동시에 읽지 않게 (화면은 열 때 요청 대여섯을 함께 보낸다)
        hit = _RES.get(key)
        if hit and hit[0] == st:
            return hit[1]
        # L29 — 846쪽 결과는 파이썬 객체 수십만 개다.  순환 참조가 없는 나무라 쓰레기 수거기(GC)가 훑을 일이 없는데,
        # 그대로 두면 큰 수거 때마다 전부 훑어 화면 요청이 0.8초씩 멈췄다 — 영구 세대로 옮긴다 (놓으면 참조 수로 그대로 풀린다)
        # L68 — 읽는 동안에도 훑지 않게 꺼 둔다 (만드는 수십만 개마다 세대 수거가 돌던 것 · 0.2초 + α)
        was = gc.isenabled()
        gc.disable()
        try:
            res = fast[0](d) if fast else None
            if res is None:
                res = json.loads(p.read_text(encoding="utf-8"))
                if fast:
                    fast[1](res)
        finally:
            gc.freeze()
            if was:
                gc.enable()
        _RES[key] = (st, res)
        _RES.move_to_end(key)
        while len(_RES) > RES_KEEP:
            _RES.popitem(last=False)
    return res


# hotfix132 — 서버가 켜진 시각.  이 시각보다 앞서 시작된 '분석 중' 은 서버가 다시 뜨기 전 것이라 끊긴 것으로 본다
# (exe 는 분석이 서버 스레드라 서버가 죽으면 분석도 죽는다 · 따로 도는 분석 프로세스는 pid 로 살았는지 본다).
BOOT = time.time()
STALE_SEC = 10 * 60             # hotfix132 — status.json 이 이만큼 안 바뀌면 끊긴 것 (분석은 0.5초마다 진행을 쓴다)
STALE_PID_SEC = 30 * 60         # hotfix132 — 살아 있는 pid 라도 이만큼 조용하면 끊긴 것 (안전망)
STALE_ERROR = "분석이 중간에 끊겼습니다 (서버가 다시 시작됐거나 분석 프로그램이 멈춤) — 같은 파일로 다시 분석해 주세요"


def _alive(pid: int) -> bool:
    """hotfix132 — 그 pid 의 프로세스가 살아 있나.  Windows 는 os.kill 을 쓰지 않는다 (sig 가 CTRL_* 가 아니면
    TerminateProcess 가 되어 살아 있는 분석을 죽인다) — OpenProcess 로 물어만 본다."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return False
            try:
                code = ctypes.c_ulong()
                ok = k32.GetExitCodeProcess(h, ctypes.byref(code))
                return bool(ok) and code.value == 259         # STILL_ACTIVE
            finally:
                k32.CloseHandle(h)
        except Exception:
            return True                                       # 모르면 살아 있는 것으로 (분석을 함부로 실패로 적지 않는다)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _stale(st: dict, d: Path) -> bool:
    """hotfix132 — '분석 중' 인데 실제로는 끊긴 묶음인가.
    ① 따로 도는 분석 프로세스(pid 가 있고 서버 자신이 아님): 그 프로세스가 없거나 30분 조용하면.
    ② 그 밖(pid 없음 · exe 스레드): 지금 서버가 뜨기 전에 시작됐거나(boot 가 다름 · 기록이 BOOT 보다 오래됨) 10분 조용하면."""
    if st.get("state") not in ("queued", "running"):
        return False
    try:
        mtime = (d / "status.json").stat().st_mtime
    except OSError:
        return False
    quiet = time.time() - mtime
    pid = st.get("pid")
    if pid and pid != os.getpid() and not paths.frozen():
        return (not _alive(pid)) or quiet > STALE_PID_SEC
    boot = st.get("boot")
    if boot is not None and boot != BOOT:
        return True
    if boot is None:
        ref = st.get("started") or st.get("created") or mtime
        if ref < BOOT and mtime < BOOT:
            return True
    return quiet > STALE_SEC


def settle(d: Path, st: dict) -> dict:
    """hotfix132 — 끊긴 '분석 중' 을 failed 로 적어 돌려준다 (화면이 영원히 기다리지 않게 · 지울 수 있게).  아니면 그대로."""
    try:
        if not _stale(st, d):
            return st
    except Exception:
        return st
    st = {**st, "state": "failed", "error": STALE_ERROR, "stopped_stage": st.get("stage")}
    write_status(d, st)
    _LAST_STATUS[str(d)] = st
    return st


def jobs() -> list:
    out = []
    for d in sorted(root().iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if not d.is_dir() or not JOB_RE.match(d.name):
            continue
        st = settle(d, read_status(d))
        out.append({"id": d.name, **{k: st.get(k) for k in ("state", "name", "created", "stage", "done", "total",
                                                             "error", "sheets", "seconds", "project", "materials",
                                                             "pages", "author")}})
    return out


def page_png(d: Path, page: int, doc=None) -> Path:
    """장 그림 캐시 파일 — 없으면 그린다 (api 가 요청 때, run 이 분석 끝에 미리).  임시 파일 → replace.
    doc — 여러 장을 그릴 때 PDF 를 한 번만 연다 (L28 · 846쪽 묶음에서 장마다 다시 열던 것)."""
    import pymupdf
    cache = d / "pages" / f"p{page}_z{ZOOM}.png"
    if cache.exists():
        return cache
    cache.parent.mkdir(exist_ok=True)
    if doc is None:
        doc = pymupdf.open(d / "source.pdf")
    if not (1 <= page <= len(doc)):
        raise IndexError(page)
    pix = doc[page - 1].get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), alpha=False)
    tmp = cache.with_suffix(f".tmp{os.getpid()}.png")
    pix.save(tmp)
    try:
        _replace(tmp, cache)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        if not cache.exists():
            raise
    return cache


def log_deletion(entry: dict | list):
    """L22 — 누가 언제 어느 분석을 지웠는지 (지운 뒤에도 남는다) — `{data}/logic/deletion_log.json` (목록).
    L84 — 여러 줄을 한 번에 (list) · 작도 그림 지우기가 예전에 쓰던 꼴(`{"items": [...]}`)도 버리지 않고 이어 쓴다
    (두 꼴이 서로를 지우던 것: 그림을 지운 뒤 분석을 지우면 그림 기록이, 그 반대면 분석 기록이 사라졌다)."""
    p = root() / "deletion_log.json"
    with _DEL_LOCK:
        try:
            items = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(items, dict):
                items = items.get("items") if isinstance(items.get("items"), list) else []
            if not isinstance(items, list):
                items = []
        except Exception:
            items = []
        at = time.strftime("%Y-%m-%d %H:%M:%S")
        items += [{**e, "at": at} for e in (entry if isinstance(entry, list) else [entry])]
        _atomic(p, json.dumps(items, ensure_ascii=False, indent=1))