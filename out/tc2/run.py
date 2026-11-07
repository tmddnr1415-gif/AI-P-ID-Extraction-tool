import json, sys, time, traceback, os, resource
sys.path.insert(0, os.getcwd())
from app import pipeline

pdf = sys.argv[1]
tag = sys.argv[2]
t0 = time.time()
timings = {}
def say(done, total, msg, *a, **kw):
    print("[%6.1fs] %s (%s/%s)" % (time.time()-t0, msg, done, total), flush=True)
try:
    res = pipeline.analyse(pdf, progress=say, timings=timings)
    out = "out/tc2/%s.json" % tag
    json.dump(res, open(out, "w"), default=str)
    rows = res["rows"]
    print("완주 · 행", len(rows), "지문", res.get("fingerprint"), flush=True)
except Exception as exc:
    print("멈춤:", type(exc).__name__, exc, flush=True)
    traceback.print_exc()
finally:
    print("시간:", json.dumps({k: round(v,1) for k,v in sorted(timings.items(), key=lambda x:-x[1])}, ensure_ascii=False), flush=True)
    print("총", round(time.time()-t0,1), "초", flush=True)
    print("최대 RSS", round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1048576.0,2), "GB", flush=True)
