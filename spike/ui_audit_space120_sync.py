"""hotfix120 — 대시보드처럼 다른 사이트(file://) 안 iframe 으로 연 ROOM SIZE 계산에서 3D 새 창 ↔ 2D 가 이어지는지 (Edge 저장소 분할 대응)."""
import os,sys,subprocess,tempfile,time,urllib.request,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent.parent; OUT=ROOT/"out/hotfix120/ui"; PORT=8766
DATA=Path(tempfile.mkdtemp(prefix="s120_"))
ENV={**os.environ,"PID_DATA_DIR":str(DATA),"PID_LOGIC_WARM":"0","PID_PAGE_WARM":"0","PID_ROWS_WARM":"0","PID_RENDER_POOL":"0"}
srv=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port",str(PORT)],cwd=ROOT,env=ENV,stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
res=[];errs=[]
try:
    for _ in range(120):
        try: urllib.request.urlopen(f"http://127.0.0.1:{PORT}/version",timeout=1);break
        except OSError: time.sleep(0.5)
    dash=DATA/"dash.html"
    dash.write_text(f'<!doctype html><meta charset=utf-8><body style="margin:0"><iframe id=f style="width:100vw;height:100vh;border:0" src="http://127.0.0.1:{PORT}/space?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"></iframe>',encoding="utf-8")
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx=b.new_context(viewport={"width":1600,"height":950})
        pg=ctx.new_page(); pg.on("pageerror",lambda e:errs.append("2D:"+str(e)))
        pg.goto(dash.as_uri()); pg.wait_for_timeout(2500)
        f=pg.frame(url=lambda u:"/space" in u)
        f.click("#hmNewBtn"); f.fill("#hmNewName","SYNC"); f.click("#hmCreate"); pg.wait_for_timeout(700)
        f.click("#hmRoomNew"); f.fill("#hmRoomName","R1"); f.click("#hmRoomCreate"); pg.wait_for_timeout(700)
        f.click("#hmRevNew"); f.fill("#hmRevName","A"); f.click("#hmRevCreate"); pg.wait_for_timeout(700)
        f.click("#hmGo"); pg.wait_for_timeout(1500)
        P="window.crspaceSpeed().panels"
        n=f.evaluate(P); res.append(("2D 판넬 수",n))
        with ctx.expect_page() as pi: f.click("#b3dWin")
        pop=pi.value; pop.on("pageerror",lambda e:errs.append("3D:"+str(e))); pop.wait_for_timeout(2500)
        res.append(("3D 새 창 주소에 embed · user 유지","embed=1" in pop.url and "user=" in pop.url and "view=3d" in pop.url))
        res.append(("3D 창이 2D 배치를 받음",pop.evaluate(P)==n))
        f.click("#bFit"); f.locator("svg").first.click(position={"x":5,"y":5}) if False else None
        f.evaluate("document.activeElement&&document.activeElement.blur()")
        pg.keyboard.press("Control+a"); pg.wait_for_timeout(200); f.click("#bDup"); pg.wait_for_timeout(1200)
        n2=f.evaluate(P); res.append(("2D 복제 뒤 판넬 수",n2))
        res.append(("2D 복제 → 3D 창 반영",n2>n and pop.evaluate(P)==n2))
        f.click("#bUndo"); pg.wait_for_timeout(1200)
        res.append(("2D 되돌리기 → 3D 창 반영",pop.evaluate(P)==f.evaluate(P)==n))
        pop.screenshot(path=str(OUT/"9_3d_window.png")); pg.screenshot(path=str(OUT/"9_2d_iframe.png"))
        b.close()
finally:
    srv.terminate(); shutil.rmtree(DATA,ignore_errors=True)
res.append(("페이지 오류 0",not errs))
for k,v in res: print(("✔" if v not in (False,0,None) else "✘"),k,v)
for e in errs: print("오류",e)
