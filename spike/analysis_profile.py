"""hotfix70 — 분석 한 번이 어디에 시간을 쓰는가 (단계별 · 함수별).

    python3 spike/analysis_profile.py <pdf> <out_dir> [--no-cprofile]

`pipeline.Timings` 가 단계마다 잰 시간을 적고, cProfile 로 함수별 자기 시간 · 누적 시간 상위를 적는다.
cProfile 은 파이썬 코드를 약 1.5~2배 느리게 만든다 — 비율을 보려는 것이고 절대값은 `--no-cprofile` 로 잰다.
실 DB 를 열지 않는다 (임시 PID_DATA_DIR).
"""
import cProfile, io, json, os, pstats, sys, tempfile, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PID_DATA_DIR", tempfile.mkdtemp(prefix="pid-prof-"))
os.environ.setdefault("PID_PAGE_WARM", "0"); os.environ.setdefault("PID_RENDER_POOL", "0")
pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
use_cp = "--no-cprofile" not in sys.argv
from app import pipeline
t = pipeline.Timings()
pr = cProfile.Profile() if use_cp else None
t0 = time.time()
if pr: pr.enable()
res = pipeline.analyse(pdf, timings=t)
if pr: pr.disable()
wall = time.time() - t0
rep = t.report()
rep["wall_s"] = round(wall, 1)
rep["rows"] = len(res.get("rows", []))
rep["fingerprint"] = res.get("fingerprint")
(out / "stages.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n".join(t.summary_lines()))
print("wall", round(wall, 1), "rows", rep["rows"], "fp", rep["fingerprint"])
if pr:
    pr.dump_stats(str(out / "profile.prof"))
    for key in ("tottime", "cumulative"):
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats(key).print_stats(45)
        (out / f"top_{key}.txt").write_text(s.getvalue(), encoding="utf-8")
