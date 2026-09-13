"""한 프로젝트를 분석해 결과 json 을 남긴다 — 하네스가 부르는 자식 프로세스.

프로세스를 나누는 이유는 메모리다.  TC2 혼자 최대 RSS 7.2GB 를 쓰므로 한
프로세스에서 셋을 이어 돌리면 위험하고, 나눠야 각각의 최대 RSS 를 따로 잴 수
있다.  분석 자체는 `pipeline.analyse` 하나이고 여기서 아무것도 바꾸지 않는다.

    python3 spike/analyse_one.py <pdf> <out.json>
"""
import json
import os
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    pdf, out = sys.argv[1], sys.argv[2]
    from app import pipeline

    t0 = time.time()
    timings: dict = {}
    result = pipeline.analyse(pdf, timings=timings)
    took = time.time() - t0
    result["fingerprint"] = pipeline.fingerprint(result)

    # 낱말은 축3 ①·③ 의 분모다.  결과에는 없으므로 여기서 함께 담는다 —
    # 하네스가 PDF 를 다시 여는 것을 피하기 위해서다 (58장 재독 3분).
    from app.engine import pidcache
    doc, pages = pidcache.load_pages(pdf)
    words = {pc.page_no: [([round(v, 2) for v in (r.x0, r.y0, r.x1, r.y1)], t)
                          for r, t in pc.words] for pc in pages}

    Path(out).parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as fh:
        json.dump({"result": result, "words": words,
                   "seconds": round(took, 1),
                   "max_rss_gb": round(
                       resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0, 2),
                   "timings": {k: round(v, 1) for k, v in timings.items()}},
                  fh, default=str)
    print("%s  행 %d  지문 %s  %.1f초  최대 RSS %.2fGB"
          % (os.path.basename(pdf), len(result["rows"]), result["fingerprint"],
             took, resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0),
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
