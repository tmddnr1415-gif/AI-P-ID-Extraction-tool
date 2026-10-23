"""hotfix109 — LOGIC 창 ↔ DCS 그래픽 창 연동 자기검증 (사본 데이터 · 버릴 포트).
python3 spike/ui_audit_logic_dcs.py <base> <logic_job> <out_dir>
확인: 🖥 단추 → 같은 프로젝트의 P&ID 그래픽이 새 창으로 · 준비 신호(태그 목록) · 시뮬레이션 1/0 이 같은 태그에 칠해짐 ·
      흐름 틀마다 보냄 · 그래픽에서 태그를 누르면 LOGIC 이 그 행으로 · 창을 닫으면 단추가 돌아옴 · 페이지 오류 0."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

BASE, JOB, OUT = sys.argv[1], sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
USER = "%ED%99%8D%EA%B8%B8%EB%8F%99"


async def main():
    from playwright.async_api import async_playwright
    res = {"errors": []}
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
        ctx = await b.new_context(viewport={"width": 1500, "height": 950})
        lg = await ctx.new_page(); lg.on("pageerror", lambda e: res["errors"].append("logic: " + str(e)))
        await lg.goto(f"{BASE}/logic?user={USER}#job={JOB}")
        await lg.wait_for_selector("#dcs-btn", timeout=20000)
        await lg.wait_for_function("typeof L !== 'undefined' && L.sheet && L.sheet.rows && L.sheet.rows.length > 0", timeout=20000)
        res["btn_before"] = await lg.inner_text("#dcs-btn")
        await lg.evaluate("for (const m of document.querySelectorAll('#ft-modal, #teach, #rv-modal')) m.hidden = true")   # 처음 열 때 뜨는 From-To 보고 · 가르치기 창
        async with ctx.expect_page(timeout=20000) as np_:
            await lg.click("#dcs-btn")
        dcs = await np_.value
        dcs.on("pageerror", lambda e: res["errors"].append("dcs: " + str(e)))
        await dcs.wait_for_selector("#stage svg g.hmi-inst", timeout=30000)
        await dcs.wait_for_function("document.querySelector('#who').textContent.includes('연동')", timeout=10000)
        res["dcs_url"] = dcs.url
        res["dcs_who"] = await dcs.inner_text("#who")
        await lg.wait_for_function("typeof DCS !== 'undefined' && DCS.tags && DCS.tags.size > 0", timeout=10000)
        res["logic_tags_known"] = await lg.evaluate("DCS.tags.size")
        # 시뮬레이션 — 입력 행 2(PUMP A RUN · 태그 있음) 를 1 로 → 그래픽의 같은 태그가 ON
        await lg.evaluate("setMode('sim', true); setForce('row:2', 1)")
        await lg.wait_for_function("document.querySelector('#dcs-n').textContent.includes('태그')", timeout=10000)
        await asyncio.sleep(1.5)
        res["btn_linked"] = await lg.inner_text("#dcs-btn")
        res["dcs_msg"] = await dcs.inner_text("#paint-msg")
        res["dcs_states"] = await dcs.evaluate("JSON.parse(document.querySelector('#states').value || '{}')")
        on_tags = [t for t, v in res["dcs_states"].items() if v.get("s") == 1]
        res["on_tags"] = on_tags
        res["dcs_on_in_svg"] = await dcs.evaluate("[...document.querySelectorAll('#stage g.hmi-inst .val')].filter(e=>e.textContent.trim().startsWith('ON')).length")
        await lg.screenshot(path=str(OUT / "6_logic_linked.png"))
        await dcs.screenshot(path=str(OUT / "7_dcs_from_logic.png"))
        # 그래픽에서 태그를 누르면 LOGIC 이 그 행으로 (status 또는 focus)
        first_on = on_tags[0] if on_tags else None
        if first_on:
            await dcs.evaluate(f"(()=>{{const g=[...document.querySelectorAll('#stage g.hmi-inst')].find(g=>g.querySelector('.tag')&&g.querySelector('.tag').textContent.trim()==='{first_on}');g.querySelector('circle.face').dispatchEvent(new MouseEvent('click',{{bubbles:true}}))}})()")
            await asyncio.sleep(0.8)
            res["logic_focus"] = await lg.evaluate("L.focus ? {row: L.focus.row, side: L.focus.side} : null")
        # 입력을 0 으로 되돌리면 그래픽도 OFF
        await lg.evaluate("setForce('row:2', 0)")
        await asyncio.sleep(1.5)
        res["dcs_states_after_off"] = await dcs.evaluate("JSON.parse(document.querySelector('#states').value || '{}')")
        # 창을 닫으면 단추가 돌아온다
        await dcs.close()
        await lg.wait_for_function("!document.querySelector('#dcs-btn').classList.contains('on')", timeout=5000)
        res["btn_after_close"] = await lg.inner_text("#dcs-btn")
        await b.close()
    (OUT / "result_logic_dcs.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
