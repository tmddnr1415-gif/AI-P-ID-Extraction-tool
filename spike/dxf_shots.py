"""UAD DXF 32장 — 원본 렌더 + 식별 오버레이 두 장씩 (55회차 [F]).

    python3 spike/dxf_shots.py out/round55/UAD_DXF.json out/round55_uad_dxf

저장된 DXF 결과로 임시 DB 를 세우고 서버를 띄워, 장마다
  p<번호>_raw.png      서버가 그린 배경 (`/jobs/{id}/page/{n}.png`)
  p<번호>_overlay.png  화면의 `#stage` (오버레이 포함) 스크린샷
를 찍는다.  범례 패널 숫자와 그 장 행 수를 함께 적는다 (33회차 등식).
★ 실 DB 를 열지 않는다 (`PID_DATA_DIR` 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/round55/UAD_DXF.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round55_uad_dxf")
OUT.mkdir(parents=True, exist_ok=True)
ZIP = ROOT / "data" / "uad_dxf.zip"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="dxfshots-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

res = json.loads(src.read_text()); res = res.get("result", res)
con = db.connect(data / "app.db")
job = "dxfshots0001"
revisions.create_project(data, "UAD-DXF")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision, input_kind)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,'DXF')",
            (job, ZIP.name, hashlib.sha256(ZIP.read_bytes()).hexdigest(), str(ZIP.resolve()),
             time.time(), res.get("fingerprint", ""), "UAD-DXF", "A"))
con.commit(); db.store_result(con, job, res); con.commit(); con.close()
revisions.record_revision(data, "UAD-DXF", "A", job_id=job, pdf_name=ZIP.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
table = []
try:
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    rows = res["rows"]
    # ① 원본 렌더 — 서버가 그린 것 그대로 (좌표 변환은 렌더러 하나)
    for p in res["pages"]:
        n = p["page_no"]
        if (OUT / f"p{n:02d}_raw.png").exists():
            continue                                    # 이미 그린 장은 다시 안 그린다
        t = time.perf_counter()
        raw = urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{job}/page/{n}.png", timeout=300).read()
        (OUT / f"p{n:02d}_raw.png").write_bytes(raw)
        print(f"p{n} raw {len(raw):,}B {time.perf_counter()-t:.1f}s", flush=True)
    # ② 오버레이 — 화면
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector(f"a.revrow[href*='{job}']") or pg.query_selector("a.revrow")
        assert rr is not None, "결과 행 없음"
        rr.click(); pg.wait_for_timeout(8000)
        pg.add_style_tag(content="#ovlegend { font-size: 11px; }")
        for p in res["pages"]:
            n = p["page_no"]
            pg.select_option("#page-select", str(n))
            # 배경 그림이 **실제로 실릴 때까지** 기다린다 — 새 분석의 첫 렌더는 장당 6초라
            # 고정 대기(3.5초)로는 `S.natural` 이 아직 없다 (실측: 둘째 실행이 거기서 죽었다).
            pg.wait_for_function("() => S.page && S.page.page_no === %d && S.natural && S.natural.w > 0" % n,
                                 timeout=90000)
            pg.wait_for_timeout(1200)
            facts = pg.evaluate("""() => {
                const legend = [...document.querySelectorAll('.ovl-row')]
                    .filter(r => !/\\(그중\\)/.test(r.innerText))
                    .map(r => r.innerText.replace(/\\s+/g, ' ').trim());
                const nums = legend.map(t => Number((t.match(/(\\d+)\\s*$/) || [0, 0])[1]));
                return {legend: legend.slice(0, 5), sum: nums.slice(0, 5).reduce((a, b) => a + b, 0),
                        boxes: document.querySelectorAll('#ov rect.det').length,
                        natural: [S.natural.w, S.natural.h], page: [S.page.width, S.page.height]};
            }""")
            pg.locator("#stage").screenshot(path=str(OUT / f"p{n:02d}_overlay.png"))
            nrows = sum(1 for r in rows if r["page_no"] == n)
            tier = (res["dxf"]["tiers"].get(str(n)) or {}).get("tier", "-")
            table.append({"page": n, "drawing_no": p["drawing_no"], "kind": p["page_kind"], "tier": tier,
                          "rows": nrows, "boxes": facts["boxes"], "legend_sum": facts["sum"],
                          "legend": facts["legend"], "natural": facts["natural"], "page_size": facts["page"]})
            print(f"p{n} overlay rows {nrows} boxes {facts['boxes']} legend {facts['sum']}", flush=True)
        print("페이지 오류:", errs[:2] or "없음")
        br.close()
finally:
    srv.terminate()
    (OUT / "table.json").write_text(json.dumps(table, ensure_ascii=False, indent=1))
print("→", OUT)
