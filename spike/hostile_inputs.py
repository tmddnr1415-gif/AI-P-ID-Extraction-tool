"""hotfix73 — 비정상 입력이 실제 업로드 경로에서 어떻게 끝나는지 잰다.

    python3 spike/hostile_inputs.py <입력 폴더> <out_dir>

빈 데이터 폴더로 서버를 띄우고(실 DB 를 안 연다) 폴더의 파일을 하나씩 올린다.
각 파일마다: 업로드 응답 · 끝난 상태 · 화면 문장 · 멈춘 단계 · 걸린 시간 · 그 뒤 서버가 살아 있는가.
이상한 파일 이름(경로 · Windows 금지 글자 · 아주 긴 이름)도 같은 PDF 로 한 번씩 올린다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, tempfile, time, urllib.request, urllib.error, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = Path(sys.argv[1]), Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
DATA = Path(tempfile.mkdtemp(prefix="hostile-"))
s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
BASE = f"http://127.0.0.1:{PORT}"
env = dict(os.environ, PID_DATA_DIR=str(DATA), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
log = open(OUT / "server.log", "w")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=str(ROOT), env=env, stdout=log, stderr=subprocess.STDOUT)


def call(method, path, files=None, timeout=60):
    body = None; headers = {}
    if files:
        b = "----h" + str(random.randint(1, 10**9)); parts = []
        for fname, blob in files:
            parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"{fname}\"\r\n"
                         f"Content-Type: application/pdf\r\n\r\n".encode("utf-8") + blob + b"\r\n")
        parts.append(f"--{b}--\r\n".encode()); body = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={b}"
    rq = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:300].decode("utf-8", "replace")
    except Exception as e:                       # noqa: BLE001
        return -1, repr(e)


def alive():
    st, _ = call("GET", "/version", timeout=5)
    return st == 200


rows = []
try:
    for _ in range(90):
        if alive():
            break
        time.sleep(1)
    cases = [(p.name, p.read_bytes()) for p in sorted(SRC.iterdir()) if p.is_file()]
    good = (SRC / "a4_text.pdf").read_bytes() if (SRC / "a4_text.pdf").exists() else None
    if good:
        for nm in ["../../evil.pdf", "..\\..\\evil.pdf", 'a:b*c?"<>|.pdf', "con.pdf", "가" * 200 + ".pdf",
                   " spaced .pdf", "tab\tname.pdf"]:
            cases.append(("NAME::" + nm, good))
    for name, blob in cases:
        fname = name[6:] if name.startswith("NAME::") else name
        t0 = time.time()
        st, body = call("POST", "/jobs", files=[(fname, blob)])
        rec = {"case": name, "upload_status": st, "upload_body": body if st != 200 else None}
        if st == 200:
            jid = body["job_id"]
            rec["stored_name"] = body.get("pdf_name"); rec["pages"] = body.get("page_count")
            end = time.time() + 600
            while time.time() < end:
                s2, j = call("GET", f"/jobs/{jid}")
                if s2 == 200 and j.get("status") in ("done", "failed", "cancelled"):
                    break
                time.sleep(1.5)
            rec.update(status=j.get("status"), message=j.get("message"), stopped=j.get("stopped_stage"),
                       rows=j.get("row_count"), secs=round(time.time() - t0, 1))
            s3, det = call("GET", f"/jobs/{jid}/error_detail")
            if s3 == 200 and isinstance(det, dict):
                rec["error_tail"] = (det.get("detail") or "")[-400:]
            stored = list((DATA / "uploads").glob(f"{jid}_*")) if (DATA / "uploads").exists() else []
            rec["stored_inside_uploads"] = bool(stored) and all(p.resolve().parent == (DATA / "uploads").resolve() for p in stored)
        rec["alive_after"] = alive()
        print(json.dumps(rec, ensure_ascii=False)[:600], flush=True)
        rows.append(rec)
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "result.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
escaped = [p for p in DATA.rglob("evil.pdf")]
print("files escaped uploads/:", escaped)
