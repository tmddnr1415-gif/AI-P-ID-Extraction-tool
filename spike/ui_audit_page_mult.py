"""hotfix65 — 수량 승수 판의 '페이지별 승수': 여러 장을 고르고 장마다 승수를 적어 적용하면
Q'ty 가 바로 바뀌는가 (눌러서 확인).

    python3 spike/ui_audit_page_mult.py <data_dir 사본> <job> out/hotfix65/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND = []
def note(x): print(x, flush=True); FOUND.append(x)

def server_rows():
    return {r["key"]: r for r in json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows?tab=ALL").read())}

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1920, "height": 1080}); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.add_init_script("try{localStorage.setItem('pid.author','홍길동');localStorage.setItem('pid.mult.fold','0');"
                           "if(!sessionStorage.getItem('x')){localStorage.removeItem('pid.split');sessionStorage.setItem('x','1')}}catch(e){}")
        pg.goto(base + "/"); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(3000)
        pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(600)
        # 판을 넉넉히 (손잡이로 끈 것과 같은 상태)
        pg.evaluate("() => { const mp = document.getElementById('mult-panel'); mp.style.height='360px'; mp.style.maxHeight='none'; }")
        pg.wait_for_selector("#mult-panel .pm-row", timeout=20000)
        n_rows = pg.evaluate("() => document.querySelectorAll('#mult-panel .pm-row').length")
        note(f"① 판에 장 {n_rows}줄 (행이 있는 장)")
        pg.screenshot(path=str(OUT / "1_판.png"))
        rows_el = pg.query_selector_all("#mult-panel .pm-row")
        pages = [int(r.get_attribute("data-page")) for r in rows_el]
        # ② 두 장 고르고 장마다 다른 승수 · 셋째 장은 Shift 범위로
        p_a, p_b = pages[0], pages[1]
        pg.fill(f'#mult-panel .pm-row[data-page="{p_a}"] .pm-val', "3")
        pg.fill(f'#mult-panel .pm-row[data-page="{p_b}"] .pm-val', "5")
        prev = pg.inner_text("#mult-panel .pm-preview")
        chk = pg.evaluate(f"() => [...S.pageMult.checked]")
        note(f"② p{p_a} x3 · p{p_b} x5 입력 → 저절로 고름 {chk} · 미리보기 '{prev}'")
        before = server_rows()
        ra = [k for k, r in before.items() if r["page_no"] == p_a and not r.get("deleted") and not r.get("removed")]
        rb = [k for k, r in before.items() if r["page_no"] == p_b and not r.get("deleted") and not r.get("removed")]
        pg.screenshot(path=str(OUT / "2_입력.png"))
        pg.click("#mult-panel .pm-apply"); pg.wait_for_timeout(400)
        ab = pg.query_selector(".author-bar")
        if ab and ab.is_visible(): ab.query_selector("button.ok").click()
        pg.wait_for_timeout(2500)
        after = server_rows()
        def qtys(keys, src): return sorted({(src[k].get("user") or {}).get("qty", src[k]["values"].get("qty")) for k in keys})
        note(f"③ 적용 → 서버 p{p_a} Q'ty {qtys(ra, after)} ({len(ra)}행) · p{p_b} {qtys(rb, after)} ({len(rb)}행)")
        grid = pg.evaluate(f"""() => {{ const out = {{}}; for (const p of [{p_a}, {p_b}]) {{
            const ks = S.rows.filter(r => r.page_no === p && !r.deleted && !r.removed).map(r => r.key);
            out[p] = [...new Set(ks.map(k => {{ const td = document.querySelector('#body tr[data-key="'+CSS.escape(k)+'"] td[data-col="qty"]');
                       return td ? td.textContent + (td.classList.contains('edited') ? '✎' : '') : '(목록에 없음)'; }}))]; }}
            return out; }}""")
        note(f"   목록 칸 Q'ty {grid}")
        # 도면 라벨 — p_a 를 띄워 x N 라벨
        pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {p_a}))"); pg.wait_for_timeout(2500)
        labs = pg.evaluate("() => [...new Set([...document.querySelectorAll('g.qtytag')].map(g => g.textContent))]")
        note(f"   p{p_a} 도면 라벨 {labs}")
        nowtxt = pg.inner_text(f'#mult-panel .pm-row[data-page="{p_a}"] .pm-now')
        note(f"   판 p{p_a} '{nowtxt}' · 고름 풀림 {pg.evaluate('() => S.pageMult.checked.size')}")
        pg.screenshot(path=str(OUT / "3_적용뒤.png"))
        # ④ Shift 범위 고르기 + 같은 값 채우기
        p3, p6 = pages[2], pages[min(5, len(pages) - 1)]
        pg.click(f'#mult-panel .pm-row[data-page="{p3}"] .pm-chk')
        pg.click(f'#mult-panel .pm-row[data-page="{p6}"] .pm-chk', modifiers=["Shift"])
        chk = pg.evaluate("() => [...S.pageMult.checked].sort((a,b)=>a-b)")
        note(f"④ p{p3} 누르고 Shift+p{p6} → 고른 장 {chk}")
        pg.fill("#mult-panel .pm-fillv", "2"); pg.click("#mult-panel .pm-fill"); pg.wait_for_timeout(300)
        vals = pg.evaluate("() => Object.fromEntries(Object.entries(S.pageMult.vals))")
        note(f"   같은 승수 x2 채우기 → {vals}")
        pg.click("#mult-panel .pm-apply"); pg.wait_for_timeout(400)
        ab = pg.query_selector(".author-bar")
        if ab and ab.is_visible(): ab.query_selector("button.ok").click()
        pg.wait_for_timeout(2500)
        after2 = server_rows()
        rng = {p: qtys([k for k, r in after2.items() if r["page_no"] == p and not r.get("deleted") and not r.get("removed")], after2) for p in chk}
        note(f"   적용 → 서버 {rng}")
        # ⑤ 도면 값으로 되돌리기 (p_a)
        pg.click(f'#mult-panel .pm-row[data-page="{p_a}"] .pm-chk'); pg.click("#mult-panel .pm-revert"); pg.wait_for_timeout(400)
        ab = pg.query_selector(".author-bar")
        if ab and ab.is_visible(): ab.query_selector("button.ok").click()
        pg.wait_for_timeout(2500)
        after3 = server_rows()
        note(f"⑤ p{p_a} 도면 값으로 → 서버 {qtys(ra, after3)} (처음 {qtys(ra, before)}) · user.qty 남은 행 "
             f"{sum(1 for k in ra if 'qty' in (after3[k].get('user') or {}))}")
        hist = json.loads(urllib.request.urlopen(f"{base}/jobs/{JOB}/rows/{rb[0]}/history").read())["history"]
        note(f"⑥ p{p_b} 한 행의 편집 이력 {[(h.get('author'), h.get('reason') or '', h.get('user_value')) for h in hist][-2:]}")
        pg.screenshot(path=str(OUT / "4_범위_되돌림.png"))
        note(f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
(OUT / "audit.txt").write_text("\n".join(FOUND), encoding="utf-8")
