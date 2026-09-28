"""도면 창 경계 손잡이 · 목록 행 음영을 실제로 띄워 본다 (hotfix17 · hotfix18).

    python3 spike/ui_audit_gutter.py out/regression_3p/UAD-DXF.json out/hotfix18/ui_gutter

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
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix18/ui_gutter")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="gutterui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "gutter000001"
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

        def geo():
            return pg.evaluate("""() => { const g = s => { const r = document.querySelector(s).getBoundingClientRect();
                return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]; };
                return {left: g('#left'), right: g('#right'), stage: g('#stage'), bars: g('#infobars'),
                        gv: g('#gutter-v'), gh: g('#gutter-h'), zoom: S.zoom, sel: S.sel || null}; }""")
        pg.wait_for_timeout(1500)
        g0 = geo(); note(f"처음 — 도면 창 {g0['stage'][2]}x{g0['stage'][3]} · 목록 폭 {g0['right'][2]} · 안내 띠 높이 {g0['bars'][3]}")
        pg.screenshot(path=str(OUT / "1_처음.png"))
        # 손잡이 위에 마우스를 대면 커서가 바뀌는가
        cur = pg.evaluate("() => [getComputedStyle(document.querySelector('#gutter-v')).cursor, getComputedStyle(document.querySelector('#gutter-h')).cursor]")
        note(f"커서 — 가운데 {cur[0]} · 위 {cur[1]}")
        # ① 가운데 손잡이를 오른쪽으로 400px
        x = g0['gv'][0] + 3; y = g0['gv'][1] + 200
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 200, y, steps=5); pg.mouse.move(x + 400, y, steps=5); pg.mouse.up()
        pg.wait_for_timeout(600)
        g1 = geo(); note(f"① 가운데를 오른쪽으로 400px — 도면 창 폭 {g0['stage'][2]} → {g1['stage'][2]} · 목록 폭 {g0['right'][2]} → {g1['right'][2]}")
        # ② 위 손잡이를 위로 끝까지
        x = g1['gh'][0] + 300; y = g1['gh'][1] + 3
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x, y - 400, steps=8); pg.mouse.up()
        pg.wait_for_timeout(600)
        g2 = geo(); note(f"② 위를 위로 끝까지 — 안내 띠 높이 {g1['bars'][3]} → {g2['bars'][3]} · 도면 창 높이 {g1['stage'][3]} → {g2['stage'][3]}")
        pg.screenshot(path=str(OUT / "2_넓힌뒤.png"))
        # ③ 새로 고쳐도 기억하는가
        pg.reload(); pg.wait_for_timeout(2500)
        # 주소에 분석 id 가 있으면 새로 고침이 곧장 결과 화면으로 간다
        if not pg.is_visible("#stage"):
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.query_selector("a.revrow").click()
        pg.wait_for_timeout(6000)
        g3 = geo(); note(f"③ 새로 고친 뒤 — 도면 창 {g3['stage'][2]}x{g3['stage'][3]} (넓힌 값 {g2['stage'][2]}x{g2['stage'][3]} 과 같은가: {abs(g3['stage'][2]-g2['stage'][2])<=2 and abs(g3['stage'][3]-g2['stage'][3])<=2})")
        # ④ 두 번 누르면 원래대로
        pg.dblclick("#gutter-v"); pg.dblclick("#gutter-h"); pg.wait_for_timeout(600)
        g4 = geo(); note(f"④ 두 번 눌러 되돌림 — 도면 창 {g4['stage'][2]}x{g4['stage'][3]} (처음 {g0['stage'][2]}x{g0['stage'][3]})")
        # ⑤ 끝까지 끌어도 목록이 사라지지 않는가
        x = g4['gv'][0] + 3; y = g4['gv'][1] + 200
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(5000, y, steps=5); pg.mouse.up(); pg.wait_for_timeout(400)
        g5 = geo(); note(f"⑤ 오른쪽 끝까지 — 목록 폭 {g5['right'][2]} (하한 260)")
        pg.mouse.move(g5['gv'][0] + 3, y); pg.mouse.down(); pg.mouse.move(-500, y, steps=5); pg.mouse.up(); pg.wait_for_timeout(400)
        g6 = geo(); note(f"⑤ 왼쪽 끝까지 — 도면 창 폭 {g6['left'][2]} (하한 260)")
        pg.dblclick("#gutter-v"); pg.wait_for_timeout(500)
        # ⑥ hotfix18 — 끄는 동안 도면이 창에 맞춰 커지고, 창 최대치는 도면이 꽉 차는 폭
        def fitinfo():
            return pg.evaluate("""() => { const st = document.querySelector('#stage');
                return {zoom: S.zoom, want: (st.clientWidth - 16) / S.natural.w,
                        dw: Math.round(S.natural.w * S.zoom), dh: Math.round(S.natural.h * S.zoom),
                        cw: st.clientWidth, ch: st.clientHeight,
                        sw: st.scrollWidth, sh: st.scrollHeight}; }""")
        f0 = fitinfo()
        gv = geo()['gv']; x = gv[0] + 3; y = gv[1] + 200
        pg.mouse.move(x, y); pg.mouse.down(); pg.mouse.move(x + 150, y, steps=6)
        pg.wait_for_timeout(200)
        mid = fitinfo()
        pg.mouse.move(x + 300, y, steps=4); pg.mouse.up(); pg.wait_for_timeout(500)
        f1 = fitinfo()
        note(f"⑥ 끄는 도중 — 도면 폭 {f0['dw']} → {mid['dw']} (창 {mid['cw']}) · 맞춤 배율과 같은가: {abs(mid['zoom']-mid['want'])<1e-6}")
        note(f"⑥ 놓은 뒤 — 도면 {f1['dw']}x{f1['dh']} · 창 {f1['cw']}x{f1['ch']} · 스크롤 범위 {f1['sw']}x{f1['sh']}")
        pg.screenshot(path=str(OUT / "3_끌면_도면도_커짐.png"))
        # ⑦ 끝까지 끌면 도면이 창을 꽉 채우는 폭에서 멈춘다
        gv = geo()['gv']
        pg.mouse.move(gv[0] + 3, y); pg.mouse.down(); pg.mouse.move(5000, y, steps=6); pg.mouse.up()
        pg.wait_for_timeout(600)
        f2 = fitinfo(); g7 = geo()
        note(f"⑦ 오른쪽 끝까지 — 도면 {f2['dw']}x{f2['dh']} · 창 {f2['cw']}x{f2['ch']} · 목록 폭 {g7['right'][2]} · "
             f"높이 꽉 참: {abs((f2['dh'] + 16) - f2['ch']) <= 3} · 세로 스크롤 없음: {f2['sh'] <= f2['ch'] + 1}")
        pg.screenshot(path=str(OUT / "4_최대치.png"))
        pg.dblclick("#gutter-v"); pg.wait_for_timeout(500)

        # ⑧ 목록 행 음영 — 사람이 고침(노랑) · 삭제(붉음+취소선) · 마크업 추가(녹색)
        keys = pg.evaluate("() => S.rows.filter(r => r.page_no === S.page.page_no).slice(0, 3).map(r => r.key)")
        jid = pg.evaluate("() => S.job.id")
        import urllib.parse as up
        req = lambda m, u, body=None: pg.evaluate(
            "async ([m,u,b]) => { const r = await fetch(u, {method:m, headers:{'Content-Type':'application/json'},"
            " body: b ? JSON.stringify(b) : undefined}); return r.status; }", [m, u, body])
        st_edit = req("PATCH", f"/jobs/{jid}/rows/{up.quote(keys[0])}", {"field": "qty", "value": "7", "author": "시험"})
        st_del = req("DELETE", f"/jobs/{jid}/rows/{up.quote(keys[1])}?reason_class=FALSE_POSITIVE&author=%EC%8B%9C%ED%97%98&exclude=true")
        pno = pg.evaluate("() => S.page.page_no")
        st_add = req("POST", f"/jobs/{jid}/rows", {"page_no": pno, "rect": [100, 100, 120, 110], "author": "시험",
                     "values": {"type": "PI", "qty": 1, "scope": "SCT"},
                     "scope_source": "USER", "qty_source": "USER"})
        note(f"⑧ API — 고침 {st_edit} · 삭제 {st_del} · 추가 {st_add}")
        pg.evaluate("async () => { await refreshRows(); }")
        pg.wait_for_timeout(1200)
        shade = pg.evaluate("""(ks) => { const q = k => document.querySelector(`#body tr[data-key="${CSS.escape(k)}"]`);
            const bg = tr => tr ? getComputedStyle(tr).backgroundColor : null;
            const add = [...document.querySelectorAll('#body tr.added')][0];
            const d = q(ks[1]);
            return {edit: [q(ks[0]) && q(ks[0]).className, bg(q(ks[0]))],
                    del: [d && d.className, bg(d), d ? getComputedStyle(d.querySelector('td')).textDecorationLine : null],
                    add: [add && add.className, bg(add)]}; }""", keys)
        note(f"⑧ 고친 행 — class '{shade['edit'][0]}' · 배경 {shade['edit'][1]}")
        note(f"⑧ 삭제한 행 — class '{shade['del'][0]}' · 배경 {shade['del'][1]} · 글자 {shade['del'][2]}")
        note(f"⑧ 추가한 행 — class '{shade['add'][0]}' · 배경 {shade['add'][1]}")
        pg.evaluate("(k) => { const tr = document.querySelector(`#body tr[data-key=\"${CSS.escape(k)}\"]`); if (tr) tr.scrollIntoView({block:'center'}); }", keys[0])
        pg.wait_for_timeout(400)
        el = pg.query_selector("#right")
        if el: el.screenshot(path=str(OUT / "5_목록_음영.png"))
        note("콘솔 오류: " + (" | ".join(errs[:4]) if errs else "없음"))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=20)

real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 — 같은가: {real_before == real_after}")
(OUT / "README.md").write_text("# hotfix17 — 도면 창 경계 손잡이 (화면 자기검증)\n\n"
    + "\n".join("- " + s for s in FOUND) + "\n", encoding="utf-8")
print("→", OUT)
