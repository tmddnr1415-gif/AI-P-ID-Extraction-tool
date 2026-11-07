"""L78 — 시운전 화면 자기검증: 사본 데이터로 서버를 띄워 계통 목록 · 장비 단계 · 단계 시뮬레이션 · LOGIC 창 연동 · Word 만들기를 누른다.

  python3 spike/ui_audit_l78.py <데이터 폴더(사본)> <job> <그림 폴더>
"""
import os, socket, subprocess, sys, time, urllib.request, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data, job, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=data, PYTHONPATH=ROOT, PID_PAGE_WARM="0", PID_LOGIC_WARM="0", PID_ROWS_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env,
                       stdout=subprocess.DEVNULL, stderr=open(os.path.join(out, "server.log"), "w"))
B = f"http://127.0.0.1:{port}"
log = []
def say(*a):
    t = " ".join(str(x) for x in a); print(t); log.append(t)
try:
    for _ in range(120):
        try: urllib.request.urlopen(B + "/version", timeout=2).read(); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch()
        ctx = br.new_context(viewport={"width": 1700, "height": 1000})
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"{B}/logic/commission#job={job}")
        pg.wait_for_selector("#tree li[data-eq]", state="attached", timeout=120000)
        say("계통·장비", pg.evaluate("() => [document.querySelectorAll('.cm-sys').length, document.querySelectorAll('#tree li').length]"))
        say("요약", pg.inner_text("#facts"))
        pg.screenshot(path=f"{out}/1_목록.png")
        pg.fill("#q", "DRN MOV 1"); time.sleep(0.3)
        pg.click('#tree li[data-eq="AB HHP MAIN STM DRN MOV 1"]')
        pg.wait_for_selector(".cm-step", timeout=60000)
        say("단계", pg.evaluate("() => C.steps.length"))
        t = time.time(); pg.click("#run-all")
        pg.wait_for_function("() => !C.running", timeout=120000)
        say("차례로", round(time.time() - t, 1), "초 ·", pg.inner_text("#runline"))
        pg.screenshot(path=f"{out}/2_단계_MOV.png", full_page=True)
        # LOGIC 창 — 인터록 단계를 도면에서 보기
        i = pg.evaluate("() => C.steps.findIndex(s => s.kind === 'block')")
        with ctx.expect_page() as pinfo:
            pg.click(f'button[data-show="{i}"]')
        lw = pinfo.value; lerr = []
        lw.on("pageerror", lambda e: lerr.append(str(e)))
        lw.wait_for_function("() => /시운전/.test((document.querySelector('#status')||{}).textContent||'')", timeout=120000)
        time.sleep(1.5)
        say("LOGIC 창", lw.evaluate("() => (document.querySelector('#status')||{}).textContent"))
        lw.set_viewport_size({"width": 1700, "height": 1000})
        lw.screenshot(path=f"{out}/3_LOGIC_인터록.png")
        # 다른 장비 — 시트를 넘는 조건 (CCW 펌프 STOP 은 앞 시트 그룹 명령에서)
        pg.fill("#q", "SPRAY PUMP A"); time.sleep(0.3)
        pg.click('#tree li[data-eq="CCW FFC SPRAY PUMP A"]')
        pg.wait_for_selector(".cm-step", timeout=60000)
        k = pg.evaluate("() => C.steps.findIndex(s => s.action === 'STOP' && s.kind === 'perm')")
        pg.click(f'button[data-run="{k}"]'); pg.wait_for_function("() => !C.running && C.results", timeout=120000)
        say("CCW STOP 단계", pg.evaluate(f"() => [C.steps[{k}].title, C.results[{k}].got, C.results[{k}].status]"))
        pg.screenshot(path=f"{out}/4_단계_CCW.png", full_page=True)
        # Word
        pg.click("#doc-make")
        t = time.time()
        pg.wait_for_function("() => !document.querySelector('#doc-get').hidden", timeout=600000)
        say("Word", round(time.time() - t, 1), "초")
        r = urllib.request.urlopen(f"{B}/logic/api/jobs/{job}/sysdesc.docx").read()
        open(f"{out}/AMIRAL_System_Description.docx", "wb").write(r)
        say("Word 크기", len(r))
        say("화면 오류", errs[:3], lerr[:3])
        br.close()
finally:
    srv.terminate()
    open(os.path.join(out, "result.txt"), "w").write("\n".join(log))
