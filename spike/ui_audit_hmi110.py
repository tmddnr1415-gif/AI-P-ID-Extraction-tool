"""hotfix110 — H1 HMI 화면(/dcs) 자기검증 (사본 데이터 · 버릴 포트).
python3 spike/ui_audit_hmi110.py <base> <pid_job> <logic_job> <out_dir>

확인: ① 예시(압축기 트레인) Overview — 심볼 · 배관 흐름 · 값 상자 · Trend · Key · Control Mode · 모터 창 · Plant 알약
      ② Symbol Library 탭 ③ 식별된 실행 P&ID 장 — 실제 배치 · 값 상자 자리 · 라벨 · 확대 ④ 고르기 → 속성 판 · 태그 두 번 눌러 고침 →
      저장(작성자) → 다시 열면 저장본 → 식별 결과로 다시 ⑤ LOGIC 창 🖥 → 새 창 · dcs-ready · 시뮬레이션 1/0 이 같은 태그에 칠해짐 ·
      그래픽에서 누르면 LOGIC 이 그 행으로 · 페이지 오류 0."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BASE, JOB, LJOB, OUT = sys.argv[1], sys.argv[2], sys.argv[3], Path(sys.argv[4])
OUT.mkdir(parents=True, exist_ok=True)
USER = "%ED%99%8D%EA%B8%B8%EB%8F%99"


async def main():
    from playwright.async_api import async_playwright
    res = {"errors": []}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx = await b.new_context(viewport={"width": 1600, "height": 1000})
        pg = await ctx.new_page(); pg.on("pageerror", lambda e: res["errors"].append("dcs: " + str(e)))
        # ① 예시
        await pg.goto(f"{BASE}/dcs/demo?user={USER}")
        await pg.wait_for_selector("#svg g.node.inst", timeout=20000)
        await asyncio.sleep(2.5)
        res["example"] = await pg.evaluate("""({inst: document.querySelectorAll('#svg g.node.inst').length, valves: document.querySelectorAll('#svg g.node.valve').length,
            equip: document.querySelectorAll('#svg g.node.equip').length, pipes: document.querySelectorAll('#svg .pipe.base').length,
            flow: document.querySelectorAll('#svg .pipe.flow').length, key: document.querySelectorAll('#key tr').length,
            trend: !!document.querySelector('#trend polyline'), motor: !document.querySelector('#motor-panel').hidden,
            plant: document.querySelector('#plant').textContent, title: document.querySelector('#title').textContent})""")
        await pg.screenshot(path=str(OUT / "1_example_overview.png"))
        # ② 라이브러리
        await pg.click("#tabs [data-tab=library]"); await asyncio.sleep(0.4)
        res["library"] = await pg.evaluate("({cats: document.querySelectorAll('#library .lib-cat').length, items: document.querySelectorAll('#library .lib-item').length})")
        await pg.screenshot(path=str(OUT / "2_symbol_library.png"))
        await pg.click("#tabs [data-tab=overview]")
        # ③ 식별된 P&ID
        await pg.goto(f"{BASE}/dcs?job={JOB}&page=5&user={USER}")
        await pg.wait_for_selector("#svg g.node.inst", timeout=30000)
        await asyncio.sleep(1.5)
        res["pid"] = await pg.evaluate("""({inst: document.querySelectorAll('#svg g.node.inst').length, valves: document.querySelectorAll('#svg g.node.valve').length,
            equip: document.querySelectorAll('#svg g.node.equip').length, pipes: document.querySelectorAll('#svg .pipe.base').length,
            labels: document.querySelectorAll('#svg #l-labels > *').length, notag: document.querySelectorAll('#svg .notag').length,
            who: document.querySelector('#who').textContent, page: document.querySelector('#page').value, vb: document.querySelector('#svg').getAttribute('viewBox'),
            pages: [...document.querySelectorAll('#page option')].map(o=>o.textContent)})""")
        # 값 상자끼리 겹침 — 화면 좌표로 센다
        res["pid_face_overlaps"] = await pg.evaluate("""(()=>{const b=[...document.querySelectorAll('#svg .valbox')].map(r=>r.getBBox());let n=0;
            for(let i=0;i<b.length;i++)for(let j=i+1;j<b.length;j++){const a=b[i],c=b[j];if(a.x<c.x+c.width&&c.x<a.x+a.width&&a.y<c.y+c.height&&c.y<a.y+a.height)n++}return n})()""")
        await pg.screenshot(path=str(OUT / "3_pid_p5_fit.png"))
        await pg.click("#fit"); await asyncio.sleep(0.4)
        await pg.screenshot(path=str(OUT / "4_pid_p5_whole.png"))
        await pg.click("#fit"); await asyncio.sleep(0.3)
        for _ in range(2):
            await pg.click("#zin"); await asyncio.sleep(0.2)
        # ④ 고르기 → 속성 판
        g = await pg.evaluate("""(()=>{const st=document.querySelector('#stage').getBoundingClientRect();
            const n=[...document.querySelectorAll('#svg g.node.inst')].find(g=>{if(!g.dataset.tag)return false;const r=g.querySelector('.valbox').getBoundingClientRect();
              return r.x>st.x+20&&r.right<st.right-20&&r.y>st.y+20&&r.bottom<st.bottom-20});return n?n.dataset.id:null})()""")
        if not g:
            await pg.evaluate("""(()=>{const i=HMI.A.scene.instruments.find(x=>x.tag);HMI.setVB([i.x-500,i.y-260,1000,520])})()"""); await asyncio.sleep(0.3)
            g = await pg.evaluate("HMI.A.scene.instruments.find(x=>x.tag).id")
        res["picked"] = g
        box = await pg.evaluate(f"""(()=>{{const r=document.querySelector('#svg g.node.inst[data-id="{g}"] .valbox').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()""")
        await pg.mouse.click(box[0], box[1])
        await asyncio.sleep(0.4)
        res["props"] = await pg.inner_text("#props")
        await pg.screenshot(path=str(OUT / "5_pid_selected_props.png"))
        # 태그 두 번 눌러 고침
        t = await pg.evaluate(f"""(()=>{{const r=document.querySelector('#svg g.node.inst[data-id="{g}"] .tagtext').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()""")
        await pg.mouse.dblclick(t[0], t[1])
        await pg.wait_for_selector("#tagedit:not([hidden])", timeout=5000)
        await pg.fill("#tagedit", "14LBA99CP999"); await pg.keyboard.press("Enter")
        await asyncio.sleep(0.4)
        res["save_enabled"] = await pg.evaluate("!document.querySelector('#save').disabled")
        await pg.click("#save"); await asyncio.sleep(1.0)
        res["after_save_who"] = await pg.inner_text("#who")
        await pg.goto(f"{BASE}/dcs?job={JOB}&page=5&user={USER}")
        await pg.wait_for_selector("#svg g.node.inst", timeout=30000); await asyncio.sleep(1)
        res["reload_who"] = await pg.inner_text("#who")
        res["reload_has_tag"] = await pg.evaluate("[...document.querySelectorAll('#svg .tagtext')].some(t=>t.textContent==='14LBA99CP999')")
        await pg.click("#reset"); await asyncio.sleep(1.5)
        res["after_reset_who"] = await pg.inner_text("#who")
        res["after_reset_has_tag"] = await pg.evaluate("[...document.querySelectorAll('#svg .tagtext')].some(t=>t.textContent==='14LBA99CP999')")
        # p6 — 기기 심볼이 있는 장
        await pg.select_option("#page", "6"); await asyncio.sleep(1.5)
        res["p6"] = await pg.evaluate("({inst: document.querySelectorAll('#svg g.node.inst').length, equip: document.querySelectorAll('#svg g.node.equip').length, valves: document.querySelectorAll('#svg g.node.valve').length})")
        await pg.screenshot(path=str(OUT / "6_pid_p6.png"))
        # ⑤ LOGIC 창 → 그래픽 새 창 · 연동
        lg = await ctx.new_page(); lg.on("pageerror", lambda e: res["errors"].append("logic: " + str(e)))
        await lg.goto(f"{BASE}/logic?user={USER}#job={LJOB}")
        await lg.wait_for_selector("#dcs-btn", timeout=20000)
        await lg.wait_for_function("typeof L !== 'undefined' && L.sheet && L.sheet.rows && L.sheet.rows.length > 0", timeout=20000)
        await lg.evaluate("for (const m of document.querySelectorAll('#ft-modal, #teach, #rv-modal')) m.hidden = true")
        async with ctx.expect_page(timeout=20000) as np_:
            await lg.click("#dcs-btn")
        dcs = await np_.value
        dcs.on("pageerror", lambda e: res["errors"].append("dcs2: " + str(e)))
        await dcs.set_viewport_size({"width": 1600, "height": 1000})
        await dcs.wait_for_selector("#svg g.node.inst", timeout=30000)
        await dcs.wait_for_function("document.querySelector('#linkinfo').textContent.includes('LOGIC')", timeout=10000)
        await lg.wait_for_function("typeof DCS !== 'undefined' && DCS.tags && DCS.tags.size > 0", timeout=10000)
        res["logic_tags_known"] = await lg.evaluate("DCS.tags.size")
        await lg.evaluate("setMode('sim', true); setForce('row:2', 1)")
        await lg.wait_for_function("document.querySelector('#dcs-n').textContent.includes('태그')", timeout=10000)
        await asyncio.sleep(1.8)
        res["btn_linked"] = await lg.inner_text("#dcs-btn")
        res["dcs_linkinfo"] = await dcs.inner_text("#linkinfo")
        res["dcs_live"] = await dcs.evaluate("[...document.querySelectorAll('#svg .valtext.v.live')].map(t=>[t.closest('g.node').dataset.tag,t.textContent])")
        res["dcs_on"] = await dcs.evaluate("[...document.querySelectorAll('#svg .valtext.v.on')].map(t=>t.closest('g.node').dataset.tag)")
        res["dcs_sim_button"] = await dcs.inner_text("#sim")
        # 켜진 태그가 화면에 보이게
        if res["dcs_on"]:
            await dcs.evaluate(f"""(()=>{{const g=document.querySelector('#svg g.node.inst[data-tag="{res['dcs_on'][0]}"]');const i=HMI.A.scene.instruments.find(x=>x.id===g.dataset.id);HMI.setVB([i.x-700,i.y-380,1400,760])}})()""")
            await asyncio.sleep(0.3)
        await lg.screenshot(path=str(OUT / "7_logic_linked.png"))
        await dcs.screenshot(path=str(OUT / "8_dcs_from_logic.png"))
        if res["dcs_on"]:
            pos = await dcs.evaluate(f"""(()=>{{const r=document.querySelector('#svg g.node.inst[data-tag="{res['dcs_on'][0]}"] .valbox').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()""")
            await dcs.mouse.click(pos[0], pos[1]); await asyncio.sleep(0.8)
            res["logic_focus"] = await lg.evaluate("L.focus ? {row: L.focus.row, side: L.focus.side} : null")
            res["dcs_props_after_pick"] = await dcs.inner_text("#props")
        await lg.evaluate("setForce('row:2', 0)"); await asyncio.sleep(1.8)
        res["dcs_off"] = await dcs.evaluate("[...document.querySelectorAll('#svg .valtext.v.off')].map(t=>t.closest('g.node').dataset.tag)")
        await dcs.close()
        await lg.wait_for_function("!document.querySelector('#dcs-btn').classList.contains('on')", timeout=5000)
        res["btn_after_close"] = await lg.inner_text("#dcs-btn")
        await b.close()
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
