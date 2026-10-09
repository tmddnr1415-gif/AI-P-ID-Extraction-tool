"""hotfix56 — 분석을 **다른 프로세스**에서 돌린다.  서버는 분석 중에도 대답한다.

## 왜 — 현장에서 이것 때문에 "서버가 꺼져 있습니다" 가 떴습니다

부서 대시보드(포트 8080)는 P&ID 메뉴를 누를 때마다 `GET /version` 을 **3초** 안에 받아야
iframe 을 띄운다 (`docs/dashboard_embed.md` §4).  분석은 지금까지 서버 프로세스 안의 스레드
하나가 돌렸고, 파이썬은 한 프로세스에서 한 번에 한 스레드만 파이썬 코드를 돌린다 (GIL).
분석의 `layout` 단계("도면 치수를 재는 중")는 PyMuPDF 가 한 장의 도형을 통째로 읽는 동안 그
자물쇠를 몇 초씩 쥐고 놓지 않는다 — 그동안 서버는 `/version` 에 대답하지 못한다.

실측 (TC2 60장 · 4코어 · 이 저장소 hotfix54): 분석 시작 53초에 `/version` 이 **3초를 넘겨
끊겼고**, 그 밖에도 1.2~2.1초가 여러 번 나왔다.  대시보드는 그것을 "P&ID 서버가 꺼져
있습니다" 로 말한다 — 분석 중에 다른 메뉴로 갔다가 돌아오면 다시 묻기 때문이다.

## 무엇이 바뀌나

* 분석은 **새 파이썬 프로세스**(`spawn`)가 돌린다.  서버 프로세스의 스레드는 진행 소식을
  받아 예전과 **같은 `progress` 함수**를 부르기만 한다 — 진행 표시 · 취소 · 실패 문장 ·
  멈춘 단계가 전부 그대로다.
* 취소는 예전처럼 진행 소식 사이에서 걸리고, 그때 자식을 끝낸다 (`terminate`).
* 결과는 파일 하나(피클)로 받는다 — 큰 dict 를 파이프로 넘기면 받는 쪽이 읽기 전에 자식이
  끝나기를 기다리다 서로 막힐 수 있다 (파이썬 문서가 경고하는 모양).
* 자식이 죽으면(메모리 부족 등) **서버는 살아 있고** 그 분석만 실패로 적힌다.  예전에는 서버가
  함께 죽었다.  그리고 분석이 끝나면 그 메모리(TC2 7GB)가 운영체제로 돌아간다.

## 판정은 한 줄도 바뀌지 않는다

자식이 부르는 것은 `pipeline.analyse` 그 함수이고 인자도 같다.  다른 점은 그 프로세스가
**매번 새것**이라는 것뿐인데, 22회차가 `_own_config` 로 막아 둔 "앞 분석의 config 가 다음
분석으로 샌다" 가 구조적으로 사라진다 — 같은 결과를 내는 쪽으로만 다르다.

끄는 스위치: `PID_ANALYSIS_INPROCESS=1` (예전처럼 서버 안 스레드에서 돈다 · 시험·진단용).
"""
from __future__ import annotations

import multiprocessing as mp
import os
import pickle
import queue as queue_mod
import traceback
from pathlib import Path

# 자식이 다시 세울 수 있는 예외 — 파이프라인이 **직접 검사한 조건**이고 문장도 거기서 썼다.
# 이 둘은 `main._worker` 가 문장 그대로 화면에 보내므로 종류를 잃으면 안 된다.
_KNOWN = ("LegendUnavailable", "TitleBlockUnreadable", "NoTextLayer")


def inprocess() -> bool:
    return os.environ.get("PID_ANALYSIS_INPROCESS", "").strip() not in ("", "0")


class ChildFailed(RuntimeError):
    """자식 프로세스 안에서 알 수 없는 예외가 났다.  `detail` 은 자식의 트레이스 원문."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


TARGET = "app.pipeline:analyse"


def _resolve(target: str):
    import importlib
    mod, _, name = target.partition(":")
    return getattr(importlib.import_module(mod), name)


def _child(out_path: str, events, kwargs: dict, target: str = TARGET) -> None:
    """자식 프로세스의 본체.  **app.main 을 import 하지 않는다** (DB 연결 · 작업 스레드 ·
    끊긴 분석 정리가 import 때 돈다 — 자식이 그것을 하면 서버가 둘이 된다)."""
    try:
        from app import console
        console.safe_stdio()
    except Exception:                                   # noqa: BLE001
        pass
    try:
        analyse = _resolve(target)

        def progress(done, total, message, sheets=None, plan=None, drawing=None):
            events.put(("progress", (done, total, message, sheets, plan, drawing)))

        kwargs = dict(kwargs)
        pdf = Path(kwargs.pop("pdf_path"))
        result = analyse(pdf, progress=progress, **kwargs)
        tmp = out_path + ".part"
        with open(tmp, "wb") as fh:
            pickle.dump(result, fh, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, out_path)
        events.put(("done", out_path))
    except BaseException as exc:                        # noqa: BLE001
        kind = type(exc).__name__
        events.put(("error", (kind if kind in _KNOWN else "", str(exc),
                              traceback.format_exc())))


def run(pdf_path: Path, progress, work_dir: Path, *, target: str = TARGET,
        **kwargs) -> dict:
    """`pipeline.analyse(pdf_path, progress=progress, **kwargs)` 와 같은 일을 자식 프로세스에서.

    `progress` 는 부모 쪽 함수이고 예전과 같이 불린다 — 그 안에서 예외(취소)가 나면 자식을
    끝내고 그 예외를 그대로 올린다.  `target` 은 시험이 바꿔 끼우는 자리다 ("모듈:함수").
    """
    if inprocess():
        return _resolve(target)(Path(pdf_path), progress=progress, **kwargs)

    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    out_path = work_dir / f"result_{os.getpid()}_{id(kwargs):x}.pkl"
    ctx = mp.get_context("spawn")
    events = ctx.Queue()
    proc = ctx.Process(target=_child, name="pid-analysis",
                       args=(str(out_path), events,
                             dict(kwargs, pdf_path=str(pdf_path)), target),
                       daemon=True)
    proc.start()
    try:
        while True:
            try:
                kind, payload = events.get(timeout=1.0)
            except queue_mod.Empty:
                if not proc.is_alive():
                    # 소식 없이 끝났다 — 큐에 늦게 도착한 것이 있을 수 있으니 한 번 더 본다.
                    try:
                        kind, payload = events.get(timeout=2.0)
                    except queue_mod.Empty:
                        raise ChildFailed(
                            f"분석 프로세스가 결과 없이 끝났습니다 (종료 코드 {proc.exitcode}) — "
                            "메모리가 모자랐을 수 있습니다",
                            f"analysis child exited with code {proc.exitcode} and sent nothing")
                else:
                    continue
            if kind == "progress":
                progress(*payload[:3], sheets=payload[3], plan=payload[4],
                         drawing=payload[5])
            elif kind == "done":
                with open(payload, "rb") as fh:
                    result = pickle.load(fh)
                return result
            elif kind == "error":
                name, message, detail = payload
                if name:
                    from app import pipeline
                    exc = getattr(pipeline, name)(message)
                    exc.child_traceback = detail
                    raise exc
                raise ChildFailed(message, detail)
    finally:
        if proc.is_alive():
            proc.terminate()
        proc.join(timeout=10)
        for p in (out_path, Path(str(out_path) + ".part")):
            try:
                p.unlink()
            except OSError:
                pass
        try:
            events.close()
        except Exception:                               # noqa: BLE001
            pass
