"""hotfix56 시험이 자식 프로세스에 넘기는 가짜 분석 함수들 (pytest 가 모으지 않는 이름)."""
import os
import time


def ok(pdf, progress=None, **kw):
    progress(1, 3, "layout", sheets=(1, 3), plan=[{"page": 1}], drawing="D-1")
    progress(2, 3, "detect")
    return {"pid": os.getpid(), "pdf": str(pdf), "kw": kw, "rows": [{"a": (1, 2)}]}


def legend_missing(pdf, progress=None, **kw):
    from app import pipeline
    raise pipeline.LegendUnavailable("범례도 프로필도 없습니다 — 시험")


def boom(pdf, progress=None, **kw):
    raise ValueError("zero-size array — 시험")


def dies(pdf, progress=None, **kw):
    progress(1, 2, "layout")
    os._exit(3)


def slow(pdf, progress=None, **kw):
    for i in range(600):
        progress(i, 600, "layout")
        time.sleep(0.05)
    return {}


def busy(pdf, progress=None, **kw):
    t = time.time()
    n = 0
    while time.time() - t < 3.0:             # 파이썬 코드로 CPU 를 쥔다 (GIL)
        n += 1
    return {"n": n}
