"""hotfix111 — 시스템 한 장 화면 자기검증 (사본 데이터 · 버릴 포트).
python3 spike/ui_audit_hmi111.py <base> <pid_job> <logic_job> <out_dir>

확인: ① 주소의 장 번호로 열면 그 장이 든 시스템 한 장이 고르기에 · 장 테두리 둘 · 줌아웃(전체) ② 맞춤 → 계기가 모인 곳
      ③ 장 머리를 누르면 그 장 하나로 ④ 고르기로 다시 시스템 → 태그 고침 → 저장(작성자) → 다시 열면 저장본 → 식별 결과로 다시
      ⑤ LOGIC 창 🖥 → 시스템 한 장이 열리고 같은 태그가 칠해짐 · 페이지 오류 0."""
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
        await pg.goto(f"{BASE}/dcs?job={JOB}&page=5&user={USER}")
        await pg.wait_for_selector("#svg g.frame", timeout=30000)
        await asyncio.sleep(1.5)
        res["system"] = await pg.evaluate("""({page: document.querySelector('#page').value, frames: document.querySelectorAll('#svg g.frame').length,
            inst: document.querySelectorAll('#svg g.node.inst').length, equip: document.querySelectorAll('#svg g.node.equip').length,
            equipNames: [...document.querySelectorAll('#svg .lbl-equip')].map(t=>t.textContent),
            links: document.querySelectorAll('#svg .pipe.base').length, title: document.querySelector('#title').textContent,
            who: document.querySelector('#who').textContent, vb: document.querySelector('#svg').getAttribute('viewBox'),
            size: HMI.A.scene.size, groups: [...document.querySelectorAll('#page optgroup')].map(g=>g.label+': '+g.children.length),
            legend: [...document.querySelectorAll('#legend .lg-item, #legend li, #legend tr')].map(x=>x.textContent.trim()).filter(Boolean).slice(0,20)})""")
        await pg.screenshot(path=str(OUT / "1_system_whole.png"))
        await pg.click("#fit"); await asyncio.sleep(0.5)
        await pg.screenshot(path=str(OUT / "2_system_fit_cluster.png"))
        await pg.click("#fit"); await asyncio.sleep(0.4)
        # ③ 장 머리 → 그 장 하나로
        pos = await pg.evaluate("""(()=>{const t=[...document.querySelectorAll('#svg .frame-title')].find(x=>x.dataset.page==='6');const r=t.getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]})()""")
        await pg.mouse.click(pos[0], pos[1]); await asyncio.sleep(1.5)
        res["after_frame_click"] = await pg.evaluate("({page: document.querySelector('#page').value, frames: document.querySelectorAll('#svg g.frame').length, inst: document.querySelectorAll('#svg g.node.inst').length})")
        await pg.screenshot(path=str(OUT / "3_sheet_p6_from_frame.png"))
        # ④ 다시 시스템 → 태그 고침 → 저장
        await pg.select_option("#page", "sys:D00P-10LBA10-M05"); await asyncio.sleep(1.5)
        g = await pg.evaluate("HMI.A.scene.instruments.find(x=>x.tag && x.page_no===6).id")
        await pg.evaluate(f"""(()=>{{const i=HMI.A.scene.instruments.find(x=>x.id==='{g}');HMI.setVB([i.x-500,i.y-260,1000,520])}})()"""); await asyncio.sleep(0.3)
        t = await pg.evaluate(f"""(()=>{{const r=document.querySelector('#svg g.node.inst[data-id="{g}"] .tagtext').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()""")
        await pg.mouse.dblclick(t[0], t[1])
        await pg.wait_for_selector("#tagedit:not([hidden])", timeout=5000)
        await pg.fill("#tagedit", "14LBA99CP999"); await pg.keyboard.press("Enter"); await asyncio.sleep(0.3)
        await pg.click("#save"); await asyncio.sleep(1.0)
        res["after_save_who"] = await pg.inner_text("#who")
        await pg.goto(f"{BASE}/dcs?job={JOB}&page=sys:D00P-10LBA10-M05&user={USER}")
        await pg.wait_for_selector("#svg g.frame", timeout=30000); await asyncio.sleep(1)
        res["reload_who"] = await pg.inner_text("#who")
        res["reload_has_tag"] = await pg.evaluate("[...document.querySelectorAll('#svg .tagtext')].some(t=>t.textContent==='14LBA99CP999')")
        res["option_saved"] = await pg.evaluate("document.querySelector('#page option[value=\"sys:D00P-10LBA10-M05\"]').textContent")
        await pg.click("#reset"); await asyncio.sleep(1.5)
        res["after_reset_has_tag"] = await pg.evaluate("[...document.querySelectorAll('#svg .tagtext')].some(t=>t.textContent==='14LBA99CP999')")
        # ⑤ LOGIC 창
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
        await lg.wait_for_function("typeof DCS !== 'undefined' && DCS.tags && DCS.tags.size > 0", timeout=10000)
        await lg.evaluate("setMode('sim', true); setForce('row:2', 1)")
        await asyncio.sleep(2.5)
        res["logic_page"] = await dcs.evaluate("document.querySelector('#page').value")
        res["logic_on"] = await dcs.evaluate("[...document.querySelectorAll('#svg .valtext.v.on')].map(t=>t.closest('g.node').dataset.tag)")
        res["logic_frames"] = await dcs.evaluate("document.querySelectorAll('#svg g.frame').length")
        await dcs.screenshot(path=str(OUT / "4_logic_opens_system.png"))
        await b.close()
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
