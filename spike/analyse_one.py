"""한 프로젝트를 분석해 결과 json 을 남긴다 — 하네스가 부르는 자식 프로세스.

프로세스를 나누는 이유는 메모리다.  TC2 혼자 최대 RSS 7.2GB 를 쓰므로 한
프로세스에서 셋을 이어 돌리면 위험하고, 나눠야 각각의 최대 RSS 를 따로 잴 수
있다.  분석 자체는 `pipeline.analyse` 하나이고 여기서 아무것도 바꾸지 않는다.

    python3 spike/analyse_one.py <pdf> <out.json> [장도면번호.json]

세 번째 인자는 45회차에 늘었다 — `{"12": "1A5J-...", ...}` 꼴로 **사람이 적은
장 도면번호**를 넘긴다.  **하네스는 넘기지 않는다**: 사람 값이 없는 상태의
불변이 구조적으로 보장되어야 하기 때문이다 (31회차 승수와 같은 규율).
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
    sheets = None
    if len(sys.argv) > 3:
        sheets = json.loads(Path(sys.argv[3]).read_text())
    from app import pipeline

    t0 = time.time()
    timings: dict = {}
    result = pipeline.analyse(pdf, timings=timings, sheet_numbers=sheets)
    took = time.time() - t0
    result["fingerprint"] = pipeline.fingerprint(result)

    # 낱말은 축3 ①·③ 의 분모다.  결과에는 없으므로 여기서 함께 담는다 —
    # 하네스가 PDF 를 다시 여는 것을 피하기 위해서다 (58장 재독 3분).
    from app.engine import dxf_reader
    if dxf_reader.is_dxf_input(Path(pdf)):
        # 55회차 — DXF 는 낱말을 `dxf_reader` 가 준다 (표시 좌표 · PDF 와 같은 모양)
        sheets, _meta = dxf_reader.open_set(Path(pdf))
        words = {sh.no: [([round(v, 2) for v in w.rect], w.text)
                         for w in dxf_reader.words(sh) if not w.hidden]
                 for sh in sheets if not sh.error}
    else:
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
