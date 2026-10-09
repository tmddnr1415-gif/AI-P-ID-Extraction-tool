"""hotfix69 — 장 그림을 미리 그려 둔다 (처음 넘기는 장도 기다리지 않게).

왜
    장 그림은 처음 볼 때 서버가 PDF 를 열어 그린다 (QFE A1 한 장 그리기 0.26초 + PNG 0.21초).  사람이 장을
    넘길 때마다 그만큼 기다렸다 — 시뮬레이션(spike/perf_sim.py) 의 장 넘기기 중앙 1.19초가 거의 이것이었다.
    hotfix45 가 한 번 그린 장을 디스크에 두게 했으므로, **사람이 보기 전에 한 번씩 그려 두면** 모든 장이
    디스크에서 바로 나온다.

어떻게
    결과를 처음 열 때(`GET /jobs/{id}/pages`) 그 분석의 장 그림을 **별도 프로세스**가 차례로 그린다.  서버
    안의 스레드로 그리면 PyMuPDF 가 그리는 동안 파이썬 인터프리터 잠금을 쥐어 다른 요청이 그만큼 늦는다
    (hotfix56 이 분석을 자식 프로세스로 옮긴 것과 같은 이유).  자식은 이 모듈만 읽고 `app.main` 을
    읽지 않는다.  사람이 지금 보는 장 → 그 앞뒤 → 나머지 순서로, 이미 있는 그림은 건너뛴다.  쓰는 방법은
    `page_png` 와 같다 — 임시 파일에 쓰고 `os.replace` (쓰다 만 파일이 캐시로 읽히지 않게).  판정과 무관하다
    — 그림은 화면의 배경일 뿐이고, 지워도 다시 그린다.

끄는 스위치: `PID_PAGE_WARM=0`.
"""
from __future__ import annotations

import multiprocessing as mp
import os
import threading
import uuid
from pathlib import Path

_LOCK = threading.Lock()
_PROC: dict = {"p": None, "job": ""}


def enabled() -> bool:
    return os.environ.get("PID_PAGE_WARM", "1") != "0"


def cache_file(cache_root: Path, job_id: str, page_no: int, zoom: float) -> Path:
    # `main._page_cache_file` 과 같은 이름 — 두 곳이 같은 파일을 가리켜야 미리 그린 것이 쓰인다
    return Path(cache_root) / job_id / f"p{page_no}_z{zoom:g}.png"


def order(pages: list, first: int) -> list:
    """지금 보는 장부터 앞뒤로 번갈아 넓혀 간다 (다음 · 이전 장이 먼저 준비된다)."""
    pages = sorted(set(pages))
    if first not in pages:
        return pages
    i = pages.index(first)
    out = [first]
    for d in range(1, len(pages)):
        for j in (i + d, i - d):
            if 0 <= j < len(pages):
                out.append(pages[j])
    return out


def _child(pdf: str, cache_root: str, job_id: str, pages: list, zoom: float) -> None:
    try:
        os.nice(10)                       # 사람이 쓰는 서버보다 뒤에 선다 (Windows 에는 없다 — 그냥 지나간다)
    except (AttributeError, OSError):
        pass
    import pymupdf
    doc = pymupdf.open(pdf)
    try:
        for n in pages:
            out = cache_file(Path(cache_root), job_id, n, zoom)
            if out.is_file() or not 1 <= n <= doc.page_count:
                continue
            pm = doc[n - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
            data = pm.tobytes("png")
            try:
                out.parent.mkdir(parents=True, exist_ok=True)
                tmp = out.with_name(out.name + f".{uuid.uuid4().hex[:8]}.tmp")
                tmp.write_bytes(data)
                os.replace(tmp, out)
            except OSError:
                return
    finally:
        doc.close()


def _render_one(pdf: str, out: str, page_no: int, zoom: float) -> bool:
    """자식 프로세스에서 장 하나를 그려 캐시 파일로 둔다 (`render_now` 가 부른다)."""
    target = Path(out)
    if target.is_file():
        return True
    import pymupdf
    doc = pymupdf.open(pdf)
    try:
        if not 1 <= page_no <= doc.page_count:
            return False
        data = doc[page_no - 1].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).tobytes("png")
    finally:
        doc.close()
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + f".{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return True


_POOL: dict = {"pool": None}


def _pool():
    with _LOCK:
        if _POOL["pool"] is None:
            _POOL["pool"] = mp.get_context("spawn").Pool(processes=2)
        return _POOL["pool"]


def _ready() -> bool:
    import pymupdf  # noqa: F401  — 일꾼이 처음 일을 받을 때 읽을 것을 미리 읽어 둔다
    return True


def prime() -> None:
    """결과를 열 때 일꾼을 미리 깨운다 — 첫 장을 그리는 사람이 일꾼이 뜨는 1초를 기다리지 않게."""
    if os.environ.get("PID_RENDER_POOL", "1") == "0":
        return
    try:
        p = _pool()
        for _ in range(2):
            p.apply_async(_ready)
    except Exception:                            # noqa: BLE001
        pass


def call(fn, args: tuple, timeout: float = 120.0):
    """PDF 를 읽는 무거운 일을 서버 밖 일꾼에게 맡기고 기다린다 (기다리는 동안 서버는 다른 요청을 받는다).
    `fn` 은 모듈 맨 위 함수여야 한다 (일꾼에게 이름으로 보낸다).  일꾼을 못 쓰면 `RuntimeError` — 부른 쪽이
    서버 안에서 직접 한다."""
    if os.environ.get("PID_RENDER_POOL", "1") == "0":
        raise RuntimeError("render pool off")
    try:
        return _pool().apply_async(fn, args).get(timeout)
    except Exception as exc:                     # noqa: BLE001
        raise RuntimeError(str(exc)) from exc


def render_now(pdf: Path, out: Path, page_no: int, zoom: float, timeout: float = 60.0):
    """사람이 지금 연 장 — 서버 프로세스 밖(일꾼 둘)에서 그리고 기다린다.

    서버 안에서 그리면 PyMuPDF 가 그리는 동안(A1 한 장 0.5초) 인터프리터 잠금을 쥐어, 그 사이 들어온 다른
    요청(칸 저장 · 목록)이 줄을 선다.  시뮬레이션에서 이웃 장 미리 받기와 겹치자 칸 저장이 0.4초 → 5.6초가
    됐다 (spike/perf_sim.py).  기다리는 동안 서버는 잠금을 놓는다.  일꾼을 못 띄우면 None — 부른 쪽이 예전처럼
    그린다.  돌려주는 것: True(그렸다 · 캐시 파일이 있다) / False(그런 장이 없다) / None(일꾼 없음)."""
    if os.environ.get("PID_RENDER_POOL", "1") == "0":
        return None
    try:
        return _pool().apply_async(_render_one, (str(pdf), str(out), page_no, zoom)).get(timeout)
    except Exception:
        return None


def start(pdf: Path, cache_root: Path, job_id: str, pages: list, first: int, zoom: float = 1.6) -> bool:
    """그릴 장이 남아 있으면 자식 프로세스 하나를 띄운다.  이미 도는 것이 있으면 띄우지 않는다
    (같은 분석이면 그것이 다 그리고, 다른 분석이면 다음에 결과를 열 때 그 분석 차례가 온다)."""
    if not enabled() or not pdf or not Path(pdf).is_file():
        return False
    todo = [n for n in order(pages, first) if not cache_file(cache_root, job_id, n, zoom).is_file()]
    if not todo:
        return False
    with _LOCK:
        p = _PROC["p"]
        if p is not None and p.is_alive():
            return False
        ctx = mp.get_context("spawn")
        proc = ctx.Process(target=_child, name="pid-page-warm", daemon=True,
                           args=(str(pdf), str(cache_root), job_id, todo, zoom))
        proc.start()
        _PROC.update(p=proc, job=job_id)
    return True


def stop() -> None:
    """분석을 지울 때 — 그 분석의 그림을 그리는 중이면 멈춘다 (지운 폴더에 다시 쓰지 않게)."""
    with _LOCK:
        p = _PROC["p"]
        if p is not None and p.is_alive():
            p.terminate()
        _PROC.update(p=None, job="")


def running_job() -> str:
    p = _PROC["p"]
    return _PROC["job"] if p is not None and p.is_alive() else ""
