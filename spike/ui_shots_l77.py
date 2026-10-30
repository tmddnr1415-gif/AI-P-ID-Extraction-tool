import os,sys,socket,subprocess,time,urllib.request,shutil
ROOT="/home/user/AI-P-ID-Extraction-tool"; data=sys.argv[1]; out=sys.argv[2]
shutil.rmtree(data,ignore_errors=True); os.makedirs(data); os.makedirs(out,exist_ok=True)
s=socket.socket(); s.bind(("127.0.0.1",0)); port=s.getsockname()[1]; s.close()
env=dict(os.environ,PID_DATA_DIR=data,PYTHONPATH=ROOT,PID_PAGE_WARM="0",PID_LOGIC_WARM="0",PID_ROWS_WARM="0")
srv=subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--port",str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
B=f"http://127.0.0.1:{port}"
def shot(pg,name,**k): pg.screenshot(path=f"{out}/{name}.png",**k); print("찍음",name)
try:
    for _ in range(120):
        try: urllib.request.urlopen(B+"/version",timeout=2).read(); break
        except Exception: time.sleep(0.5)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br=pw.chromium.launch(); ctx=br.new_context(viewport={"width":1700,"height":980}); pg=ctx.new_page(); errs=[]
        pg.on("pageerror",lambda e: errs.append(str(e)))
        pg.goto(B+"/logic/draw"); pg.wait_for_function("() => typeof S!=='undefined' && S.allItems && S.allItems.length>0",timeout=90000)
        pg.evaluate("() => localStorage.setItem('pid.author','홍길동')")
        print("목록",pg.evaluate("() => S.allItems.length"))
        pg.evaluate("""() => { const o=[...document.querySelectorAll('#pick option')].map(o=>o.textContent).filter(t=>t.includes('AMIRAL'));
          const d=document.createElement('div'); d.style.cssText='position:fixed;left:300px;top:60px;width:1000px;max-height:900px;overflow:hidden;background:#fff;border:2px solid #2f5bd8;z-index:999;font:14px sans-serif;padding:10px';
          d.innerHTML='<b>그림 고르기 목록 — AMIRAL 묶음 '+o.length+'장</b><br>'+o.slice(0,40).map(t=>t.replace(/</g,'&lt;')).join('<br>')+'<br>… 외 '+(o.length-40)+'장'; document.body.appendChild(d); }""")
        time.sleep(0.5); shot(pg,"1_그리기목록")
        did=pg.evaluate("() => S.allItems.find(i=>i.sheet_no==='BL11_G131').id")
        pg.goto(B+f"/logic/draw#d={did}"); pg.reload()
        pg.wait_for_function("() => S.doc && S.doc.sheet_no==='BL11_G131'",timeout=60000); time.sleep(2)
        print("열림",pg.evaluate("() => [S.doc.project, S.doc.set_name, S.doc.blocks.length, S.doc.wires.length]"))
        shot(pg,"2_시트열기_BL11_G131")
        # 3) 블록 고름 + 속성
        pg.evaluate("() => { const b=S.doc.blocks.find(b=>b.kind==='MACRO')||S.doc.blocks[0]; S.sel=new Set([b.id]); S.selWire=null; render(); }"); time.sleep(0.7)
        shot(pg,"3_블록고름_속성판")
        # 4) 선 고름 — 토막 손잡이
        pg.evaluate("() => { const sp=w=>{const xs=w.pts.map(p=>p[0]),ys=w.pts.map(p=>p[1]);return (Math.max(...xs)-Math.min(...xs))+(Math.max(...ys)-Math.min(...ys));}; const w=S.doc.wires.filter(w=>w.pts.length>=3).sort((a,b)=>sp(b)-sp(a))[0]||S.doc.wires[0]; S.sel=new Set(); S.selWire=w.id; render(); }"); time.sleep(0.7)
        print("손잡이",pg.evaluate("() => document.querySelectorAll('.seghd').length"))
        bb=pg.evaluate("() => { const r=document.querySelector('#svg .wire.sel').getBoundingClientRect(); return [r.x,r.y,r.width,r.height]; }")
        pg.evaluate("() => { const r=document.querySelector('#svg .wire.sel').getBoundingClientRect(); }")
        shot(pg,"4_선고름_꺾인토막손잡이",clip={"x":max(0,bb[0]-120),"y":max(0,bb[1]-80),"width":min(1700,bb[2]+240),"height":min(900,bb[3]+160)})

        pg.evaluate("() => { S.selWire=null; render(); }")
        # 5) 시뮬레이션 — 14행 OP REQ = 1
        t1=time.time(); pg.click("#simtoggle"); pg.wait_for_function("() => S.sim && S.sim.res",timeout=120000); print("시뮬 켜기",round(time.time()-t1,1))
        pg.evaluate("() => setForce(S.id,'row:14',1)"); time.sleep(4)
        print("시뮬",pg.evaluate("() => [Object.values(S.sim.values).filter(v=>v===1).length, document.querySelector('#sim-out').innerText.slice(0,300)]"))
        shot(pg,"5_시뮬레이션_14행켬")
        # 6) 매크로 새 창
        info=pg.evaluate("() => { const sh=S.sim.res.sheet; for (const b of S.doc.blocks){ const sb=sh.blocks[b.id]; if (sb && sb.macro && sb.macro.did) return [b.id, sb.macro.did, sb.macro.sheet]; } return null; }")
        print("매크로",info)
        if info:
            with ctx.expect_page() as pi: pg.evaluate(f"() => openMacroWin('{info[0]}','{info[1]}')")
            w=pi.value; w.set_viewport_size({"width":1700,"height":980}); w.on("pageerror",lambda e: errs.append("새창 "+str(e)))
            w.wait_for_function("() => typeof S!=='undefined' && S.doc && S.mparent && S.mparent.inner",timeout=60000); t0=time.time()
            w.wait_for_function("() => S.sim && S.sim.res && Object.values(S.sim.values||{}).some(v=>v===1)",timeout=120000); print("새창 값 섬",round(time.time()-t0,1)); time.sleep(2)
            print("새창",w.evaluate("() => [S.doc.sheet_no, (S.mparent.inner.frames||[]).length, (S.mparent.inner.frames||[]).map(f=>Object.values(f.values||{}).filter(v=>v===1).length), Object.values(S.sim.values||{}).filter(v=>v===1).length, (S.mparent.inner.links||[]).length]"))
            pg.evaluate("() => setForce(S.id,'row:47',1)"); time.sleep(4)
            print("새창3",w.evaluate("() => [!!S.sim.res, S.sim.res && S.sim.res.error, S.sim.on, document.querySelector('#status')&&document.querySelector('#status').textContent, Object.keys(S.sim.values||{}).length, Object.keys((S.mparent.inner.frames||[{}])[0].values||{}).slice(0,8)]"))
            print("새창2",w.evaluate("() => [Object.values(S.sim.values||{}).filter(v=>v===1).length]"))
            w.screenshot(path=f"{out}/6_매크로_새창_내부동작.png"); print("찍음 6")
        pg.click("#simtoggle"); time.sleep(1)
        # 7) FROM/TO 연결 표기 — 표 부분 확대
        pg.evaluate("() => { const z=document.querySelector('#zoom-in'); }")
        badges=pg.evaluate("() => [...document.querySelectorAll('#svg .lbadge, #svg [class*=badge]')].map(e=>e.textContent).slice(0,12)")
        print("표기",badges)
        shot(pg,"7_FROM_TO_연결표기",clip={"x":0,"y":60,"width":900,"height":700})
        # 8) 고쳐 저장 → 다시 열기
        pg.evaluate("() => { S.doc.left[14]={...(S.doc.left[14]||{}), desc:'(테스트) 사용자가 고친 설명'}; markDirty(); render(); }")
        pg.click("#save"); time.sleep(2); pg.reload()
        pg.wait_for_function("() => S.doc && S.doc.sheet_no==='BL11_G131'",timeout=60000); time.sleep(2)
        print("다시열어",pg.evaluate("() => [(S.doc.left[14]||{}).desc, S.doc.saves]"))
        shot(pg,"8_고쳐저장_다시열기",clip={"x":0,"y":60,"width":900,"height":700})
        print("오류",errs[:5]); br.close()
finally: srv.terminate()
