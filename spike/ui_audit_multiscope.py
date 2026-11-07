"""Shift 다중 선택 + 공급 주체 일괄 변경을 **실제로 눌러서** 확인한다 (56회차).

    python3 spike/ui_audit_multiscope.py out/regression_3p/TC2.json out/round56/ui

확인하는 것 여섯 — 코드가 도는 것과 화면이 그렇게 말하는 것은 다른 일이다:
    ① 그냥 누르면 묶음이 아니다 (한 행 · 근거 패널)
    ② Shift + 클릭이 **더한다** — 첫 Shift 는 이미 고른 행과 둘이다
    ③ 한 번 더 누르면 **뺀다** (토글)
    ④ 패널이 몇 개인지와 지금 값을 **사실대로** 말한다
    ⑤ 적용하면 그 행들이 전부 바뀌고 **오버레이 색·범례 숫자가 따라간다**
    ⑥ 작성자 줄이 뜨고, **취소하면 한 행도 안 바뀐다**

★ 실 DB 를 열지 않는다 (17회차 격리) — 끝에서 sha256 을 대조해 증명한다.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/TC2.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round56/ui")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="msui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "msaudit00001"
pdf = ROOT / "data" / "TC2_260821.pdf"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "TC2")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(),
             result.get("fingerprint", ""), "TC2", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "TC2", "A", job_id=job, pdf_name=pdf.name,
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
        pg.on("console", lambda m: errs.append("console:" + m.text)
              if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt')"
                    ".forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_첫화면_행없음.png"))
            note("★ 결과로 들어갈 행이 없다"); raise SystemExit(2)
        rr.click()
        pg.wait_for_timeout(9000)

        # 상자가 여럿인 장을 고른다 (그 장의 행 수가 가장 많은 쪽).
        page_no = pg.evaluate("""() => {
            const by = {};
            for (const r of S.rows) by[r.page_no] = (by[r.page_no]||0)+1;
            return Object.entries(by).sort((a,b)=>b[1]-a[1])[0][0];
        }""")
        pg.select_option("#page-select", str(page_no))
        pg.wait_for_timeout(5000)
        # ⚠ 상자는 누를 때마다 다시 그려진다 (`drawOverlay`) — 손잡이를 들고
        # 있으면 두 번째 클릭에서 "DOM 에 안 붙어 있다" 로 죽는다.  키로 찾는다.
        ks = pg.evaluate("""() => [...document.querySelectorAll('rect.det')]
              .filter(n => !n.classList.contains('excluded'))
              .map(n => n.dataset.key)""")
        note(f"p{page_no} · 상자 {len(ks)}개")
        if len(ks) < 4:
            note("★ 상자가 모자라 시험할 수 없다"); raise SystemExit(2)
        def box(i, shift=False):
            sel = 'rect.det[data-key="%s"]' % ks[i]
            pg.click(sel, modifiers=["Shift"] if shift else [])
            pg.wait_for_timeout(600)

        # ── ① 그냥 클릭 — 묶음이 아니다 ───────────────────────────────
        box(0)
        note("① 그냥 클릭 — multi %d · sel 있음 %s"
             % (pg.evaluate("() => S.multi.size"),
                pg.evaluate("() => !!S.sel")))

        # ── ② Shift — 첫 Shift 는 이미 고른 행과 둘이다 ───────────────
        box(1, True); n2 = pg.evaluate("() => S.multi.size")
        box(2, True); n3 = pg.evaluate("() => S.multi.size")
        note(f"② Shift 한 번 → {n2} · 두 번 → {n3}")

        # ── ③ 토글 — 같은 것을 또 누르면 빠진다 ───────────────────────
        box(2, True); n4 = pg.evaluate("() => S.multi.size")
        box(2, True)
        note(f"③ 다시 누르면 → {n4} · 또 누르면 → "
             + str(pg.evaluate("() => S.multi.size")))

        # ── ④ 패널이 사실대로 말하는가 ────────────────────────────────
        head = pg.inner_text("#evidence")
        painted = pg.evaluate("() => document.querySelectorAll('rect.det.multi').length")
        note(f"④ 패널 첫 줄 “{head.splitlines()[0]}” · 짙게 칠해진 상자 {painted}")
        pg.screenshot(path=str(OUT / "1_선택.png"))

        keys = pg.evaluate("() => [...S.multi]")
        was = pg.evaluate("(ks) => ks.map(k => (S.rows.find(r=>r.key===k)||{}).values.scope)", keys)

        # ── ⑥ 취소하면 한 행도 안 바뀐다 ──────────────────────────────
        pg.click("#evidence button.mc-b[data-mc='SCT']")
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / "2_작성자줄.png"))
        pg.click(".author-bar .cancel")
        pg.wait_for_timeout(700)
        now = pg.evaluate("(ks) => ks.map(k => (S.rows.find(r=>r.key===k)||{}).values.scope)", keys)
        note(f"⑥ 취소 — 값이 그대로인가: {now == was} ({was} → {now})")

        # ── ⑤ 적용 — **지금과 다른 값**으로 눌러야 바뀐 것이 보인다 ──
        legend_before = pg.inner_text("#ovl-items")
        pg.click("#evidence button.mc-b[data-mc='VENDOR']")
        pg.wait_for_timeout(700)
        pg.fill(".author-bar input", "감사")
        pg.click(".author-bar .ok")
        pg.wait_for_timeout(3000)
        after = pg.evaluate("(ks) => ks.map(k => (S.rows.find(r=>r.key===k)||{}).values.scope)", keys)
        server = pg.evaluate("""async (ks) => {
            const rows = await (await fetch(`/jobs/${S.job.id}/rows?tab=ALL`)).json();
            return ks.map(k => (rows.find(r=>r.key===k)||{}).values.scope);
        }""", keys)
        note(f"⑤ 적용 — 전 {was} · 화면 {after} · 서버 {server}")
        note("⑤ 오버레이 범례 — 전 “%s” → 후 “%s”"
             % (" ".join(legend_before.split()), " ".join(pg.inner_text("#ovl-items").split())))
        colours = pg.evaluate("""(ks) => ks.map(k => (document.querySelector(
            `rect.det[data-key="${k}"]`)||{getAttribute:()=>null}).getAttribute('stroke'))""", keys)
        note(f"⑤ 상자 색 — {colours}")
        pg.screenshot(path=str(OUT / "3_적용후.png"))

        # ── ⑦ Shift + 끌기 — 띠 안의 것이 전부 묶인다 ────────────────
        clearMulti = "() => clearMulti()"
        pg.evaluate(clearMulti)
        pg.wait_for_timeout(400)
        # 그 장 상자들을 전부 덮는 띠를 SVG 좌표로 계산해 빈 자리에서 끈다.
        bb = pg.evaluate("""() => {
            const ns = [...document.querySelectorAll('rect.det')];
            const r = ns.map(n => n.getBoundingClientRect());
            return {x0: Math.min(...r.map(v=>v.left)), y0: Math.min(...r.map(v=>v.top)),
                    x1: Math.max(...r.map(v=>v.right)), y1: Math.max(...r.map(v=>v.bottom)),
                    n: ns.length};
        }""")
        st = pg.eval_on_selector("#stage", "el => el.getBoundingClientRect().toJSON()")
        x0 = max(bb["x0"] - 6, st["x"] + 4); y0 = max(bb["y0"] - 6, st["y"] + 4)
        x1 = min(bb["x1"] + 6, st["x"] + st["width"] - 4)
        y1 = min(bb["y1"] + 6, st["y"] + st["height"] - 4)
        pg.keyboard.down("Shift")
        pg.mouse.move(x0, y0); pg.mouse.down()
        pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=6)
        pg.mouse.move(x1, y1, steps=6)
        pg.mouse.up()
        pg.keyboard.up("Shift")
        pg.wait_for_timeout(1200)
        note("⑦ Shift + 끌기 — 화면의 상자 %d개 중 묶인 것 %d · 짙게 칠해진 상자 %d"
             % (bb["n"], pg.evaluate("() => S.multi.size"),
                pg.evaluate("() => document.querySelectorAll('rect.det.multi').length")))
        note("⑦ 패널 — " + pg.inner_text("#evidence").splitlines()[0])
        pg.screenshot(path=str(OUT / "4_띠선택.png"))

        # 작성자가 이력에 남았는가
        hist = pg.evaluate("""async (k) => {
            const r = await (await fetch(`/jobs/${S.job.id}/rows/${k}/history`)).json();
            return (r.history || []).map(h => `${h.field}:${h.author || '이름없음'}`);
        }""", keys[0])
        note(f"⑤ 편집 이력 — {hist}")

        note("콘솔 오류: " + (" | ".join(errs[:5]) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=20)

real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 — 시작 {real_before[:12]} · 끝 {real_after[:12]} · "
     f"같은가: {real_before == real_after}")
(OUT / "README.md").write_text(
    "# 56회차 — Shift 다중 선택 · 공급 주체 일괄 변경 (화면 자기검증)\n\n"
    + "\n".join("- " + s for s in FOUND) + "\n", encoding="utf-8")
print("→", OUT)
