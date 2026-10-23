"""hotfix109 — DCS HMI 화면 자기검증 (사본 데이터 · 버릴 포트).  python3 spike/ui_audit_hmi.py <base> <job> <out_dir>"""
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
        ctx = await b.new_context(viewport={"width": 1600, "height": 1000})
        pg = await ctx.new_page(); pg.on("pageerror", lambda e: res["errors"].append(str(e)))
        # ── 예시 화면 (참고 그림 재구성)
        await pg.goto(f"{BASE}/dcs/demo?user={USER}")
        await pg.wait_for_selector("#stage svg g.hmi-inst", timeout=20000)
        await asyncio.sleep(0.8)
        res["demo"] = await pg.evaluate("({inst: document.querySelectorAll('#stage g.hmi-inst').length, valves: document.querySelectorAll('#stage g[data-kind=valve]').length, equip: document.querySelectorAll('#stage g[data-kind=equipment]').length, pipes: document.querySelectorAll('#stage .hmi-pipe').length, arrows: document.querySelectorAll('#stage .hmi-pipe[marker-end],#stage .hmi-pipe[marker-start]').length, legendRows: document.querySelectorAll('#legend .row').length, libRows: document.querySelectorAll('#library .row').length, trendPts: (document.querySelector('#trend polyline.ln')||{getAttribute:()=>''}).getAttribute('points').split(' ').length, params: document.querySelectorAll('#params tr').length, chip: document.querySelector('#chip').textContent})")
        await pg.screenshot(path=str(OUT / "1_demo.png"))
        # 상태 색 — 트립으로 칠하면 모터가 붉고 칩이 Alarm
        await pg.click("#stage g[data-id=mtr] use", force=True)
        await pg.wait_for_selector("#pick [data-set=alarm]")
        await pg.click("#pick [data-set=alarm]")
        await asyncio.sleep(0.4)
        res["trip"] = await pg.evaluate("({cls: document.querySelector('#stage g[data-id=mtr]').className.baseVal, chip: document.querySelector('#chip').textContent, fp: !!document.querySelector('.hmi-faceplate')})")
        await pg.screenshot(path=str(OUT / "2_demo_trip.png"))
        # 예시 값 흐르기 → 추이에 점이 는다
        await pg.click("#live"); await asyncio.sleep(4.6); await pg.click("#live")
        res["trend_after_live"] = await pg.evaluate("(document.querySelector('#trend polyline.ln')||{getAttribute:()=>''}).getAttribute('points').split(' ').length")
        # 태그 편집 (예시 — 화면에만)
        await pg.dblclick("#stage g[data-id=pt101] .tag")
        await pg.wait_for_selector("input.hmi-inline-edit")
        await pg.fill("input.hmi-inline-edit", "PT-101A"); await pg.keyboard.press("Enter")
        await asyncio.sleep(0.4)
        res["demo_tag_edit"] = await pg.evaluate("document.querySelector('#stage g[data-id=pt101] .tag').textContent")
        # ── 식별 P&ID
        await pg.goto(f"{BASE}/dcs?job={JOB}&user={USER}")
        await pg.wait_for_selector("#stage svg g.hmi-inst", timeout=30000)
        await asyncio.sleep(1)
        res["pid"] = await pg.evaluate("({title: document.querySelector('#title').textContent, inst: document.querySelectorAll('#stage g.hmi-inst').length, tagged: document.querySelectorAll('#stage g.hmi-inst:not(.untagged)').length, valves: document.querySelectorAll('#stage g[data-kind=valve]').length, equip: document.querySelectorAll('#stage g[data-kind=equipment]').length, pipes: document.querySelectorAll('#stage .hmi-pipe').length, svc: [...new Set([...document.querySelectorAll('#stage .hmi-pipe')].map(p=>[...p.classList].find(c=>c.startsWith('svc-'))))], legendRows: document.querySelectorAll('#legend .row').length, params: document.querySelectorAll('#params tr').length, pretag: document.querySelector('#stage g[data-id=\"0371833bbe306097\"] .tag').textContent})")
        await pg.screenshot(path=str(OUT / "3_pid.png"))
        # 태그 편집 → 서버에 남는다
        await pg.dblclick('#stage g[data-id="0371833bbe306097"] .tag', force=True)
        await pg.wait_for_selector("input.hmi-inline-edit")
        new_tag = "14LBA16CP0" + str(int(asyncio.get_event_loop().time() * 10) % 90 + 10)
        await pg.fill("input.hmi-inline-edit", new_tag); await pg.keyboard.press("Enter")
        await pg.wait_for_function("document.querySelector('#paint-msg').textContent.includes('저장')", timeout=10000)
        res["pid_tag_edit"] = {"shown": await pg.evaluate("document.querySelector('#stage g[data-id=\"0371833bbe306097\"] .tag').textContent"), "msg": await pg.inner_text("#paint-msg")}
        r = await pg.request.get(f"{BASE}/dcs/api/jobs/{JOB}/hmi"); res["server_hmi_tags"] = (await r.json()).get("tags")
        # 예시 값 · Key Parameters 고르기 · Trend 로
        await pg.click("#demo"); await asyncio.sleep(0.5)
        res["pid_painted"] = await pg.evaluate("[...document.querySelectorAll('#stage g.hmi-inst .val:not(.dim)')].length")
        await pg.evaluate("document.querySelector('#stage g.hmi-inst:not(.untagged) circle.face').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        try:
            await pg.wait_for_selector("#pick [data-trend]", timeout=8000)
        except Exception:
            res["diag"] = {"pick": (await pg.inner_html("#pick"))[:500], "errors": res["errors"], "sel": await pg.evaluate("document.querySelectorAll('#stage .hmi-sel').length")}
            print(json.dumps(res, ensure_ascii=False, indent=1)); raise
        await pg.click("#pick [data-trend]"); await asyncio.sleep(0.3)
        res["trend_tag"] = await pg.inner_text("#trend h3")
        await pg.click("#params [data-pick]"); await pg.wait_for_selector("#modal input")
        res["pick_options"] = await pg.evaluate("document.querySelectorAll('#modal input').length")
        await pg.click("#m-ok"); await asyncio.sleep(0.5)
        r = await pg.request.get(f"{BASE}/dcs/api/jobs/{JOB}/hmi"); j = await r.json(); res["server_hmi_params_trend"] = {"params": j.get("params"), "trend": j.get("trend")}
        await pg.screenshot(path=str(OUT / "4_pid_painted.png"))
        # 새로 열어도 사람이 고친 태그가 남는다
        await pg.goto(f"{BASE}/dcs?job={JOB}&user={USER}"); await pg.wait_for_selector("#stage svg g.hmi-inst", timeout=30000); await asyncio.sleep(0.8)
        res["tag_persists"] = await pg.evaluate("document.querySelector('#stage g[data-id=\"0371833bbe306097\"] .tag').textContent")
        # PNG 내려받기 (브라우저)
        async with pg.expect_download(timeout=20000) as dl:
            await pg.click("#dl-png")
        d = await dl.value; path = OUT / "5_pid_download.png"; await d.save_as(str(path)); res["png_bytes"] = path.stat().st_size
        await b.close()
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
