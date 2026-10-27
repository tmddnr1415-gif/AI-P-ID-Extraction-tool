"""hotfix123 — 판넬 10-27 판(b8bcef2): Equipment List Excel 내보내기 → 그 파일을 Option A 에 다시 읽기 · 🛠 스펙 맞추기 창 (/space · 빈 데이터 폴더)."""
import os,sys,subprocess,tempfile,time,urllib.request,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent; OUT=ROOT/"out/hotfix123/ui"; PORT=8767
DATA=Path(tempfile.mkdtemp(prefix="s123_"))
ENV={**os.environ,"PID_DATA_DIR":str(DATA),"PID_LOGIC_WARM":"0","PID_PAGE_WARM":"0","PID_ROWS_WARM":"0","PID_RENDER_POOL":"0"}
srv=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(PORT)],cwd=ROOT,env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
res=[];errs=[]
try:
    OUT.mkdir(parents=True,exist_ok=True)
    for _ in range(120):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/version",timeout=1);break
        except OSError: time.sleep(0.5)
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx=b.new_context(viewport={"width":1600,"height":950},accept_downloads=True)
        f=ctx.new_page(); f.on("pageerror",lambda e:errs.append(str(e)))
        f.goto(f"http://127.0.0.1:{PORT}/space?user=%ED%99%8D%EA%B8%B8%EB%8F%99"); f.wait_for_timeout(2500)
        f.click("#hmNewBtn"); f.fill("#hmNewName","EQX"); f.click("#hmCreate"); f.wait_for_timeout(700)
        f.click("#hmRoomNew"); f.fill("#hmRoomName","R1"); f.click("#hmRoomCreate"); f.wait_for_timeout(700)
        f.click("#hmRevNew"); f.fill("#hmRevName","A"); f.click("#hmRevCreate"); f.wait_for_timeout(700)
        f.click('#hmStart li[data-st="sample"]'); f.wait_for_timeout(200)
        f.click("#hmGo"); f.wait_for_timeout(1500)
        if f.is_visible("#autodlg"): f.click("#aClose"); f.wait_for_timeout(300)
        P="window.crspaceSpeed().panels"; n=f.evaluate(P); res.append(("예시 배치 판넬 수",n))
        with f.expect_download() as di: f.evaluate("document.getElementById('bEqx').click()")
        x=DATA/"eq.xlsx"; di.value.save_as(x); res.append(("Equipment List xlsx 내려받음",x.stat().st_size>0))
        f.click("#bAuto"); f.wait_for_timeout(400); f.set_input_files("#aFileIn",str(x)); f.wait_for_timeout(1000)
        res.append(("내보낸 xlsx 를 Option A 가 다시 읽음",f.input_value("#aIn").count("\n")>=n and f.text_content("#aCnt")))
        f.screenshot(path=str(OUT/"1_optionA_xlsx.png")); f.click("#aClose"); f.wait_for_timeout(300)
        f.click("#bFix"); f.wait_for_timeout(600); res.append(("🛠 스펙 맞추기 창",f.is_visible("#fixdlg")))
        f.screenshot(path=str(OUT/"2_fix.png")); f.click("#fixClose")
        b.close()
finally:
    srv.terminate(); shutil.rmtree(DATA,ignore_errors=True)
res.append(("페이지 오류 0",not errs))
for k,v in res: print(("✔" if v not in (False,0,None) else "✘"),k,v)
for e in errs: print("오류",e)
