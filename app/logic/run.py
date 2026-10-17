"""분석 프로세스 — `python -m app.logic.run <job 폴더>`.  서버 프로세스와 따로 돈다 (hotfix56 과 같은 이유:
분석이 GIL 을 오래 쥐면 화면 요청이 늦어진다)."""
from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path


def _prerender(d: Path, res: dict):
    """인식한 시트의 장 그림을 미리 그린다 — 실패해도 분석 결과는 그대로다 (요청 때 다시 그린다)."""
    from app.logic import store
    try:
        import pymupdf
        doc = pymupdf.open(d / "source.pdf")
    except Exception:
        return
    with doc:
        for s in res.get("sheets", []):
            try:
                store.page_png(d, s["page"], doc=doc)
            except Exception:
                return


def _note(d: Path, st: dict):
    """진행 한 줄 — 무슨 일이 있어도 분석을 멈추지 않는다 (L20 · 현장 WinError 5 가 두 번 분석을 죽였다)."""
    from app.logic import store
    try:
        store.write_status(d, st)
    except Exception:
        pass


def _final(d: Path, st: dict):
    """끝 상태(완료 · 실패)는 반드시 남아야 화면이 기다림을 멈춘다 — 막히면 30초까지 다시."""
    from app.logic import store
    for _ in range(60):
        try:
            if store.write_status(d, st):
                return
        except Exception:
            pass
        time.sleep(0.5)


def run(d: Path):
    from app.logic import analyse, store
    st = store.read_status(d)
    st.update({"state": "running", "started": time.time()})
    _note(d, st)
    last = [0.0]

    try:
        import pymupdf
        st["pages"] = len(pymupdf.open(d / "source.pdf"))      # 남은 시간 어림에 쓴다 (장당 시간 × 장수)
    except Exception:
        pass

    def progress(stage, done, total):
        now = time.time()
        if now - last[0] < 0.5 and done != total:
            return
        last[0] = now
        st.update({"stage": stage, "done": done, "total": total})
        _note(d, st)
    try:
        res = analyse.analyse(str(d / "source.pdf"), progress=progress,
                              partial=lambda part: (store.write_partial(d, part), st.update({"preview": len(part["sheets"])}), _note(d, st)))
        store.write_result(d, res)
        store.drop_partial(d)
        st.update({"state": "done", "sheets": len(res["sheets"]), "seconds": res["seconds"], "stage": "", "error": "",
                   "pages": res.get("pdf_pages")})
        try:                                         # L24 — 식별률을 끝날 때 한 번 센다 (조용한 실패를 첫 화면에서 말한다)
            from app.logic import aops, fromto, idrate
            _bp = {s["page"]: s for s in res["sheets"]}
            for _pg in aops.identify(res["sheets"]):  # L30 — 화면이 결과를 읽을 때와 같은 이름 (아날로그 연산자 · 표시등)
                _bp[_pg]["findings"] = analyse._findings(_bp[_pg])
            fromto.check(res["sheets"])
            m = idrate.measure(res)
            st.update({"idrate": m["overall"], "idrate_low": m["low"]})
        except Exception:
            pass
        _final(d, st)
        _prerender(d, res)                           # 화면이 처음 열 때 장마다 0.5초씩 기다리지 않게 (L7)
        try:                                         # L22 — 학습 사전에 보탠다 (범례 표 · Typical) · 실패해도 결과는 그대로
            from app.logic import library
            library.learn_from_result(res, d, st.get("name") or d.name, job=d.name)
        except Exception:
            pass
        try:                                         # L33 — 동작 학습 (START · STOP · OPEN · CLOSE · TRIP 마다 무엇이 그 명령을 내는가)
            from app.logic import behavior
            behavior.learn_dir(d)
        except Exception:
            pass
        try:                                         # L39 — 정합성 검토 결과 한 장 + 원본 PDF 에 마크업
            from app.logic import review
            review.after_learning(d)
            st = store.read_status(d)
        except Exception:
            pass
    except analyse.NotLogic as e:
        st.update({"state": "failed", "error": str(e)})
    except Exception as e:                               # 사유를 남기고 멈춘다
        st.update({"state": "failed", "error": f"분석 중 오류: {e}", "trace": traceback.format_exc()[-4000:]})
    _final(d, st)


def prerender_missing(d: Path):
    """L31 — 그림이 아직 없는 시트만 그린다 (L7 이전 분석 · 미리 그리기가 중간에 끊긴 분석).  서버와 따로 돌아
    화면 요청을 막지 않는다.  이미 있는 그림은 건드리지 않는다."""
    try:
        res = json.loads((d / "result.json").read_text(encoding="utf-8"))
    except Exception:
        return
    _prerender(d, res)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--pages":
        prerender_missing(Path(sys.argv[2]))
    elif len(sys.argv) > 2 and sys.argv[1] == "--behavior":
        from app.logic import behavior, review
        behavior.learn_dir(Path(sys.argv[2]))
        try:
            review.after_learning(Path(sys.argv[2]))
        except Exception:
            pass
    else:
        run(Path(sys.argv[1]))
