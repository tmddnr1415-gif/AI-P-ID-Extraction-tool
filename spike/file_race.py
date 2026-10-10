"""hotfix74 — 파일을 만드는 요청을 여럿이 같은 순간에 (6동시 × 2회).

    python3 spike/file_race.py <data_dir 사본>

진단 zip · 피드백 zip · 변경 내역 Excel · 장 그림 · 스냅샷 · 메모 저장 · VOC · 같은 칸 편집.
보는 것: 5xx 0 · 내려받은 zip/xlsx/png 가 전부 열린다.
"""
import io, os, sys, json, threading, zipfile
os.environ.update(PID_DATA_DIR=sys.argv[1], PID_PAGE_WARM="0", PID_RENDER_POOL="0", PID_ANALYSIS_INPROCESS="1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient  # noqa: E402
from app import main  # noqa: E402
import openpyxl  # noqa: E402

c = TestClient(main.app, raise_server_exceptions=False)
JOB = main.CON.execute("select id from job where status='done' order by created_at desc").fetchone()[0]
rows = json.loads(c.get(f"/jobs/{JOB}/rows?slim=1").content)
KEY, PAGE = rows[0]["key"], rows[0]["page_no"]
BAD = []


def check(name, r):
    if r.status_code >= 500:
        BAD.append(f"{name} {r.status_code} {r.text[:160]}"); return
    if r.status_code != 200:
        return
    ct = r.headers.get("content-type", "")
    try:
        if "zip" in ct:
            z = zipfile.ZipFile(io.BytesIO(r.content)); z.testzip()
        elif "spreadsheet" in ct:
            openpyxl.load_workbook(io.BytesIO(r.content))
        elif ct.startswith("image/png"):
            assert r.content[:8] == b"\x89PNG\r\n\x1a\n" and len(r.content) > 1000
    except Exception as e:                                     # noqa: BLE001
        BAD.append(f"{name} 깨진 파일 {type(e).__name__}: {e}")


def diag(i):
    r = c.post(f"/jobs/{JOB}/diagnostic", json={})
    if r.status_code == 200 and "filename" in r.text:
        fn = r.json()["filename"]
        check("diag-get", c.get(f"/jobs/{JOB}/diagnostic/{fn}"))
    else:
        check("diag", r)


CASES = {
    "diag": diag,
    "feedback": lambda i: check("feedback", c.get(f"/jobs/{JOB}/feedback_export")),
    "changes": lambda i: check("changes", c.get(f"/jobs/{JOB}/revision/changes.xlsx")),
    "page": lambda i: check("page", c.get(f"/jobs/{JOB}/pages/{PAGE}.png")),
    "snapshot": lambda i: check("snapshot", c.post(f"/jobs/{JOB}/snapshot", json={"label": f"race{i}"})),
    "memo": lambda i: check("memo", c.post(f"/jobs/{JOB}/memo/{PAGE}", json={"text": f"동시 {i}", "author": f"u{i}"})),
    "voc": lambda i: check("voc", c.post("/voc", json={"category": "UI", "reason": f"동시 {i}", "author": f"u{i}", "job_id": JOB})),
    "edit": lambda i: check("edit", c.patch(f"/jobs/{JOB}/rows/{KEY}", json={"field": "qty", "value": i + 1, "author": f"u{i}"})),
}
for name, fn in CASES.items():
    for rnd in range(2):
        if name == "page":
            import shutil
            shutil.rmtree(main.DATA_DIR / "page_cache", ignore_errors=True)
        ts = [threading.Thread(target=fn, args=(i,)) for i in range(6)]
        [t.start() for t in ts]; [t.join() for t in ts]
    print(name, "ok" if not any(b.startswith(name) for b in BAD) else "★", flush=True)
memo = c.get(f"/jobs/{JOB}/memo/{PAGE}").json()
print("memo versions", len(memo.get("versions") or memo.get("history") or []))
print("결함", len(BAD))
for b in BAD[:20]:
    print(" -", b)
