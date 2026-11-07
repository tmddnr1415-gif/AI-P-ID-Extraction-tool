"""hotfix38 — QFE 두 판을 **실제 경로**(프로젝트 → Rev.A → Rev.B 대조)로 돌린다.

    python3 spike/rev_flow_qfe.py <data_dir> <pdf_A> <pdf_B> <out_dir>

서버를 띄우고 업로드 API 로 올린다 (화면이 하는 그대로).  실 DB 를 열지 않는다 —
`PID_DATA_DIR` 을 버릴 폴더로 돌린다.  끝에 Rev.B 의 /revision · /rows 를 json 으로 둔다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, pdf_a, pdf_b, out = (Path(a) for a in sys.argv[1:5])
out.mkdir(parents=True, exist_ok=True)
data.mkdir(parents=True, exist_ok=True)
os.environ["PID_DATA_DIR"] = str(data)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def post(url, fields, files=None):
    import uuid
    b = uuid.uuid4().hex
    body = b""
    for k, v in fields.items():
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
    for k, (fn, blob) in (files or {}).items():
        body += (f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\n"
                 f"Content-Type: application/pdf\r\n\r\n").encode() + blob + b"\r\n"
    body += f"--{b}--\r\n".encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=120).read())


def wait_done(base, job_id, limit=3600):
    t0 = time.time()
    while time.time() - t0 < limit:
        j = get(f"{base}/jobs/{job_id}")
        if j.get("status") in ("done", "failed", "cancelled"):
            return j
        time.sleep(15)
    raise SystemExit("timeout")


port = free_port(); base = f"http://127.0.0.1:{port}"
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
log = open(out / "server.log", "w")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT)
try:
    for _ in range(90):
        try: get(f"{base}/home"); break
        except Exception: time.sleep(1)
    print("project", post(f"{base}/projects", {"name": "QFE"}).get("name"), flush=True)
    ja = post(f"{base}/jobs", {"project": "QFE"}, {"pdf": (pdf_a.name, pdf_a.read_bytes())})
    print("A", ja, flush=True); t = time.time()
    a = wait_done(base, ja["job_id"]); print("A done", a.get("status"), round(time.time() - t), "s", flush=True)
    (out / "A_job.json").write_text(json.dumps(a, ensure_ascii=False, indent=1))
    jb = post(f"{base}/jobs", {"project": "QFE", "compared_with": ja["revision"]}, {"pdf": (pdf_b.name, pdf_b.read_bytes())})
    print("B", jb, flush=True); t = time.time()
    b = wait_done(base, jb["job_id"]); print("B done", b.get("status"), round(time.time() - t), "s", flush=True)
    (out / "B_job.json").write_text(json.dumps(b, ensure_ascii=False, indent=1))
    for tag, jid in (("A", ja["job_id"]), ("B", jb["job_id"])):
        (out / f"{tag}_rows.json").write_text(json.dumps(get(f"{base}/jobs/{jid}/rows?tab=ALL"), ensure_ascii=False))
        (out / f"{tag}_revision.json").write_text(json.dumps(get(f"{base}/jobs/{jid}/revision"), ensure_ascii=False, indent=1))
        (out / f"{tag}_pages.json").write_text(json.dumps(get(f"{base}/jobs/{jid}/pages"), ensure_ascii=False))
    (out / "home.json").write_text(json.dumps(get(f"{base}/home"), ensure_ascii=False, indent=1))
    print("revision B:", get(f"{base}/jobs/{jb['job_id']}/revision").get("counts"), flush=True)
finally:
    srv.terminate(); srv.wait(timeout=15)
