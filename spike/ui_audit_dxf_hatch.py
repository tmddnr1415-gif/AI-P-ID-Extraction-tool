"""DXF 오버레이가 **빗금**으로 칠해지는지 실제로 띄워서 본다 (56회차).

    python3 spike/ui_audit_dxf_hatch.py out/regression_3p/UAD-DXF.json out/round56/ui_dxf

확인하는 것 넷:
    ① 무늬가 실제로 걸렸는가 (`fill` 이 `url(#hatch-…)`)
    ② 무늬 색이 **테두리와 같은 값**인가 (색은 SCOPE 가 정한다 — 11회차)
    ③ 색마다 무늬가 하나씩만 서는가 (`defs` 의 `pattern` 수 = 쓰인 색 수)
    ④ 사람 눈으로 — 캡처

★ 실 DB 를 열지 않는다 (17회차 격리) — 끝에서 sha256 을 대조해 증명한다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/UAD-DXF.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round56/ui_dxf")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="dxfui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "dxfhatch0001"
pack = ROOT / "data" / "uad_dxf.zip"
sha = hashlib.sha256(pack.read_bytes()).hexdigest()
revisions.create_project(data, "UAD-DXF")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision, input_kind)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,'DXF')",
            (job, pack.name, sha, str(pack.resolve()), time.time(),
             result.get("fingerprint", ""), "UAD-DXF", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "UAD-DXF", "A", job_id=job, pdf_name=pack.name,
                          compared_with="",
                          result={"counts": {}, "states": {}, "radii": {},
                                  "deleted_candidates": []})

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_행없음.png")); note("★ 결과 행 없음"); raise SystemExit(2)
        rr.click()
        pg.wait_for_timeout(9000)
        note("입력 종류: " + str(pg.evaluate("() => S.job && S.job.input_kind")))

        page_no = pg.evaluate("""() => {
            const by = {}; for (const r of S.rows) by[r.page_no] = (by[r.page_no]||0)+1;
            return Object.entries(by).sort((a,b)=>b[1]-a[1])[0][0];
        }""")
        pg.select_option("#page-select", str(page_no))
        # ⚠ 고정 대기는 안 된다 — 그림은 장마다 한 번 그려지고 그 뒤에 오버레이가
        # 선다.  상자가 실제로 생길 때까지 기다린다 (44회차 [11] 과 같은 덫).
        try:
            pg.wait_for_selector("rect.det", timeout=120000)
        except Exception:
            note("★ 상자가 끝내 안 떴다")
        pg.wait_for_timeout(1500)
        got = pg.evaluate("""() => {
            const ns = [...document.querySelectorAll('rect.det')].filter(n => n.style.fill);
            const pats = [...document.querySelectorAll('#ov defs pattern')];
            const same = ns.every(n => {
                const f = n.style.fill || '';
                if (!f.includes('hatch-')) return false;
                const id = (f.match(/#([^)"']+)/) || [,''])[1];
                const ln = document.querySelector('#' + CSS.escape(id) + ' line');
                return ln && ln.getAttribute('stroke') === n.getAttribute('stroke');
            });
            return {boxes: ns.length, hatched: ns.filter(n =>
                      (n.style.fill||'').includes('hatch-')).length,
                    patterns: pats.length,
                    colours: new Set(ns.map(n => n.getAttribute('stroke'))).size,
                    sameColour: same};
        }""")
        note(f"p{page_no} — 칠한 상자 {got['boxes']} · 빗금 {got['hatched']} · "
             f"무늬 {got['patterns']}개 (쓰인 색 {got['colours']}종) · "
             f"무늬 색 = 테두리 색: {got['sameColour']}")
        pg.screenshot(path=str(OUT / "1_빗금.png"))
        # 확대해서 사람 눈으로 — **상자 하나에 맞춰** 가운데로 보낸다
        # (그냥 확대하면 왼쪽 위 여백이 찍힌다 — 첫 판이 그랬다).
        zoom_js = ("(pno) => { const r = S.rows.find(x => String(x.page_no) === String(pno));"
                   " S.zoom = 8.0; applyZoom(); if (r) select(r.key, true); }")
        pg.evaluate(zoom_js, str(page_no))
        pg.wait_for_timeout(2500)
        el = pg.query_selector("#stage")
        if el:
            el.screenshot(path=str(OUT / "2_빗금_확대.png"))
        # 고르지 **않은** 상자 하나를 그 자리에서 잘라 찍는다 — 고른 상자는
        # 테두리가 잉크색이라 무늬가 어떻게 보이는지 가린다.
        box = pg.evaluate("() => { const n = [...document.querySelectorAll('rect.det')]"
                          ".find(x => !x.classList.contains('sel') && x.getAttribute('fill'));"
                          " if (!n) return null; const r = n.getBoundingClientRect();"
                          " return {x: r.left, y: r.top, width: r.width, height: r.height,"
                          "         fill: n.style.fill, stroke: n.getAttribute('stroke')}; }")
        one = pg.query_selector("rect.det:not(.sel)")
        if one:
            one.scroll_into_view_if_needed()
            pg.wait_for_timeout(500)
            one.screenshot(path=str(OUT / "3_상자_한개.png"))
        if box:
            note(f"③ 상자 한 개 — {round(box['width'])}x{round(box['height'])}px · "
                 f"fill {box['fill']} · stroke {box['stroke']}")
        note("콘솔 오류: " + (" | ".join(errs[:4]) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=20)

real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 — 같은가: {real_before == real_after}")
(OUT / "README.md").write_text(
    "# 56회차 — DXF 오버레이 빗금 (화면 자기검증)\n\n"
    + "\n".join("- " + s for s in FOUND) + "\n", encoding="utf-8")
print("→", OUT)
