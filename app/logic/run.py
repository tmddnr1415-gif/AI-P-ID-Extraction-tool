"""분석 프로세스 — `python -m app.logic.run <job 폴더>`.  서버 프로세스와 따로 돈다 (hotfix56 과 같은 이유:
분석이 GIL 을 오래 쥐면 화면 요청이 늦어진다)."""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path


def run(d: Path):
    from app.logic import analyse, store
    st = store.read_status(d)
    st.update({"state": "running", "started": time.time()})
    store.write_status(d, st)
    last = [0.0]

    def progress(stage, done, total):
        now = time.time()
        if now - last[0] < 0.5 and done != total:
            return
        last[0] = now
        st.update({"stage": stage, "done": done, "total": total})
        store.write_status(d, st)
    try:
        res = analyse.analyse(str(d / "source.pdf"), progress=progress)
        store.write_result(d, res)
        st.update({"state": "done", "sheets": len(res["sheets"]), "seconds": res["seconds"], "stage": "", "error": ""})
    except analyse.NotLogic as e:
        st.update({"state": "failed", "error": str(e)})
    except Exception as e:                               # 사유를 남기고 멈춘다
        st.update({"state": "failed", "error": f"분석 중 오류: {e}", "trace": traceback.format_exc()[-4000:]})
    store.write_status(d, st)


if __name__ == "__main__":
    run(Path(sys.argv[1]))
