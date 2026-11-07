// L85 — Logic 작성 화면에서 묶음의 모든 장을 차례로 열고(휠 넘기기와 같은 openDoc) · 시뮬레이션을 켜 본다.
// 장마다 걸린 시간 · 화면 오류 · SVG 수를 적는다.   node spike/ui_sweep_l85.mjs <주소> <묶음 id> [CPU 배율=4] [out.json] [sim=1]
import { createRequire } from "module"; const require = createRequire(process.env.PW_NODE_MODULES || "/opt/node22/lib/node_modules/");
const { chromium } = require("playwright");
import fs from "fs";
const [B, sid, rate = "4", out = "ui_sweep.json", simOnArg = "1"] = process.argv.slice(2);
const set = await (await fetch(`${B}/logic/api/drawings/sets/${sid}`)).json();
const sheets = set.sheets;
const br = await chromium.launch(); const pg = await br.newPage({ viewport: { width: 1600, height: 950 } });
const cdp = await pg.context().newCDPSession(pg); await cdp.send("Emulation.setCPUThrottlingRate", { rate: +rate });
const errs = []; let cur = "";
pg.on("pageerror", e => errs.push({ sheet: cur, err: String(e).slice(0, 300) }));
pg.on("console", m => { if (m.type() === "error") errs.push({ sheet: cur, console: m.text().slice(0, 300) }); });
await pg.goto(`${B}/logic/draw?user=sweep#d=${sheets[0].id}`);
await pg.waitForFunction(() => S.doc && S.setInfo, null, { timeout: 120000 });
const rows = [];
for (const sh of sheets) {
  cur = sh.sheet_no;
  const r = await pg.evaluate(async ([id, simOn]) => {
    const fr = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    const t0 = performance.now();
    await openDoc(id); await fr();
    const open = performance.now() - t0;
    const o = { open: Math.round(open), n: document.querySelectorAll("#svg *").length, wires: S.doc.wires.length, blocks: S.doc.blocks.length };
    if (simOn) {
      const t1 = performance.now();
      try { simStart(); await runSim(false); o.simErr = S.sim.res ? undefined : "결과 없음"; } catch (e) { o.simErr = String(e); }
      o.sim = Math.round(performance.now() - t1);
      try { toggleSim(); } catch (e) {}
    }
    return o;
  }, [sh.id, simOnArg === "1"]).catch(e => ({ fail: String(e).slice(0, 200) }));
  rows.push({ sheet: sh.sheet_no, id: sh.id, ...r });
  if (rows.length % 50 === 0) console.log(rows.length, "장", JSON.stringify(r));
}
const st = k => { const v = rows.map(r => r[k]).filter(x => typeof x === "number").sort((a, b) => a - b); return { p50: v[Math.floor(v.length / 2)], p95: v[Math.floor(v.length * .95)], max: v[v.length - 1] }; };
const sum = { sheets: rows.length, open: st("open"), sim: st("sim"), errors: errs.length, fails: rows.filter(r => r.fail).length,
  slowest: rows.slice().sort((a, b) => (b.open || 0) - (a.open || 0)).slice(0, 8).map(r => [r.sheet, r.open, r.wires]),
  slowestSim: rows.slice().sort((a, b) => (b.sim || 0) - (a.sim || 0)).slice(0, 8).map(r => [r.sheet, r.sim]) };
fs.writeFileSync(out, JSON.stringify({ sum, rows, errs }, null, 1));
console.log(JSON.stringify(sum)); console.log("errors", JSON.stringify(errs.slice(0, 5)));
await br.close();
