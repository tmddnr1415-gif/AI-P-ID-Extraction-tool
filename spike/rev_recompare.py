"""hotfix38 — 저장된 데이터 디렉터리에서 **분석 없이** 대조만 다시 돌린다.

    python3 spike/rev_recompare.py <data_dir> <job_B> <out_dir> [project] [compared_with]

새 compare() 코드로 다시 짝짓고 /rows · /revision 을 json 으로 둔다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, job_b, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
out.mkdir(parents=True, exist_ok=True)
os.environ["PID_DATA_DIR"] = str(data)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port),
                        "--log-level", "warning"], cwd=ROOT)
base = f"http://127.0.0.1:{port}"
for _ in range(60):
    try:
        urllib.request.urlopen(base + "/version", timeout=5); break
    except Exception:
        time.sleep(1)
try:
    import urllib.parse
    body = urllib.parse.urlencode({"project": sys.argv[4] if len(sys.argv) > 4 else "QFE",
                                   "compared_with": sys.argv[5] if len(sys.argv) > 5 else "Rev.A"}).encode()
    req = urllib.request.Request(f"{base}/jobs/{job_b}/revision", data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    print(json.loads(urllib.request.urlopen(req, timeout=600).read()).get("counts"))
    for name in ("rows?tab=ALL", "revision"):
        blob = urllib.request.urlopen(f"{base}/jobs/{job_b}/{name}", timeout=300).read()
        (out / f"B_{name.split('?')[0]}.json").write_bytes(blob)
    print("saved", out)
finally:
    srv.terminate(); srv.wait(timeout=30)
