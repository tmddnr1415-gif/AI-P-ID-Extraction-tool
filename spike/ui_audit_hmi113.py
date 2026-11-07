"""hotfix113 — 도면 기하 HMI 그래픽 화면 확인 (사본 데이터 · 버릴 포트).
python3 spike/ui_audit_hmi113.py <base> <pid_job> <out_dir>

확인: ① 장 하나(p5) 전체 — 배관 전체 · 장비(도면 외곽 크기) · 커넥터 · 직경 글  ② 맞춤(계기가 모인 곳)
      ③ 장비 가까이 확대  ④ 시스템 한 장  ⑤ 예시(압축기 트레인) 나란히 · 페이지 오류 0."""
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
        await pg.goto(f"{BASE}/dcs?job={JOB}&page=5&view=sheet&user={USER}")
        await pg.wait_for_selector("#svg g.node.inst", timeout=60000)
        await asyncio.sleep(1.5)
        res["sheet"] = await pg.evaluate("""({page: document.querySelector('#page').value, geom: HMI.A.scene.geom || null,
            counts: HMI.A.scene.counts, basis: HMI.A.scene.basis,
            pipes: document.querySelectorAll('#svg .pipe.base').length, dashed: document.querySelectorAll('#svg .pipe.base[stroke-dasharray]').length,
            equip: [...document.querySelectorAll('#svg g.node.equip')].map(g=>g.querySelector('.tag').textContent),
            conns: document.querySelectorAll('#svg .lbl-conn').length, pipeLabels: document.querySelectorAll('#svg .pipe-label').length,
            arrows: HMI.A.scene.pipes.filter(p=>p.arrow).length})""")
        await pg.screenshot(path=str(OUT / "1_sheet_whole.png"))
        await pg.click("#fit"); await asyncio.sleep(0.6)
        await pg.screenshot(path=str(OUT / "2_sheet_fit_cluster.png"))
        await pg.evaluate("""(()=>{const e=HMI.A.scene.equipment[0]; if(!e) return; const xs=HMI.A.scene.equipment.map(q=>[q.x,q.x+q.w]).flat(), ys=HMI.A.scene.equipment.map(q=>[q.y,q.y+q.h]).flat();
            const x0=Math.min(...xs)-250,x1=Math.max(...xs)+250,y0=Math.min(...ys)-200,y1=Math.max(...ys)+700; HMI.setVB([x0,y0,x1-x0,(x1-x0)*0.55])})()""")
        await asyncio.sleep(0.6)
        await pg.screenshot(path=str(OUT / "3_sheet_equipment.png"))
        await pg.goto(f"{BASE}/dcs?job={JOB}&page=5&user={USER}")
        await pg.wait_for_selector("#svg g.frame", timeout=60000); await asyncio.sleep(1.5)
        res["system"] = await pg.evaluate("""({frames: document.querySelectorAll('#svg g.frame').length, equip: document.querySelectorAll('#svg g.node.equip').length,
            pipes: document.querySelectorAll('#svg .pipe.base').length})""")
        await pg.screenshot(path=str(OUT / "4_system_whole.png"))
        await pg.goto(f"{BASE}/dcs/demo")
        await asyncio.sleep(2.5)
        await pg.screenshot(path=str(OUT / "5_example.png"))
        await b.close()
    (OUT / "result.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))

asyncio.run(main())
