"""UAD — 같은 장을 PDF 로 읽은 결과와 DXF 로 읽은 결과를 화면으로 나란히 찍는다.

    python3 spike/pdf_vs_dxf_shots.py out/pdf_vs_dxf

임시 DB 하나에 **분석 둘**을 넣는다 — 45회차에 저장된 UAD PDF 결과(301행)와
방금 잰 UAD DXF 결과(457행).  같은 UI · 같은 접근자로 읽으므로 두 화면의 차이는
입력 형식의 차이다.
⚠ 이 작업 환경에 **UAD PDF 파일이 없다** — PDF 쪽은 도면 그림을 띄울 수 없어
그리드(행 목록)만 찍는다.  그 사실을 그림에도 적는다.
★ 실 DB 를 열지 않는다 (`PID_DATA_DIR` 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/pdf_vs_dxf")
OUT.mkdir(parents=True, exist_ok=True)
PAGES = [11, 12, 13, 14, 15]
PDF_RES = ROOT / "out" / "round45" / "UAD_after.json"
DXF_RES = ROOT / "out" / "regression_3p" / "UAD-DXF.json"
ZIP = ROOT / "data" / "uad_dxf.zip"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="pvd-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

con = db.connect(data / "app.db")
jobs = {}
for kind, src, project, pdf_name, path in (
        ("PDF", PDF_RES, "UAD-PDF", "UAD_binding.pdf", str(ROOT / "data" / "UAD_binding.pdf")),
        ("DXF", DXF_RES, "UAD-DXF", ZIP.name, str(ZIP.resolve()))):
    res = json.loads(src.read_text()); res = res.get("result", res)
    job = f"pvd{kind.lower()}0001"
    jobs[kind] = (job, res)
    revisions.create_project(data, project)
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
                " progress, message, fingerprint, project, revision, input_kind)"
                " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,?)",
                (job, pdf_name, hashlib.sha256(str(src).encode()).hexdigest(), path,
                 time.time(), res.get("fingerprint", ""), project, "A", kind))
    con.commit(); db.store_result(con, job, res); con.commit()
    revisions.record_revision(data, project, "A", job_id=job, pdf_name=pdf_name, compared_with="",
                              result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})
con.close()

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
facts = []
try:
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        for kind in ("PDF", "DXF"):
            job, res = jobs[kind]
            rows = res["rows"]
            pages = {p["page_no"]: p for p in res["pages"]}
            pg = br.new_page(viewport={"width": 1500, "height": 1000})
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.wait_for_timeout(400)
            rr = pg.query_selector(f"a.revrow[href*='{job}']")
            assert rr is not None, f"{kind} 결과 행 없음"
            rr.click(); pg.wait_for_timeout(7000)
            pg.add_style_tag(content="#ovlegend { font-size: 11px; }")
            for n in PAGES:
                mine = [r for r in rows if r["page_no"] == n]
                p = pages.get(n)
                if p is not None:
                    pg.select_option("#page-select", str(n))
                    if kind == "DXF":
                        pg.wait_for_function(
                            "() => { const i = document.querySelector('#sheet');"
                            " return S.page && S.page.page_no === %d && i.complete"
                            " && i.naturalWidth > 0 && i.src.includes('/page/%d.png'); }" % (n, n),
                            timeout=120000)
                        pg.wait_for_timeout(1200)
                        pg.click("[data-z='0']"); pg.wait_for_timeout(600)
                        pg.locator("#left").screenshot(path=str(OUT / f"p{n}_DXF_overlay.png"))
                # 그리드 — 그 장만
                pg.fill("#filter", (p or {}).get("drawing_no", "") or f"  p{n}  ")
                pg.wait_for_timeout(800)
                got = pg.evaluate("() => document.querySelectorAll('#body tr').length")
                pg.add_style_tag(content="#gridwrap { overflow: visible; }")
                pg.locator("#right").screenshot(path=str(OUT / f"p{n}_{kind}_grid.png"))
                pg.fill("#filter", ""); pg.wait_for_timeout(400)
                facts.append({"kind": kind, "page": n, "rows": len(mine), "grid": got,
                              "drawing_no": (p or {}).get("drawing_no", ""), "sheet_in_result": p is not None})
                print(f"{kind} p{n} rows {len(mine)} grid {got}", flush=True)
            pg.close()
        br.close()
finally:
    srv.terminate()
    (OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1))
print("→", OUT)
