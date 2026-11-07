// Regression screenshots: every preset (assembled + wheel-exploded), plus info card, cutaway and isolate.
//   node dev/shots.mjs <out dir>      (all network blocked: proves the page works offline)
import { createRequire } from 'node:module';
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const [outDir] = process.argv.slice(2).filter((a) => !a.endsWith('.js'));
fs.mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 920 } });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
const net = []; await page.route(/^(https?|wss?):/, (r) => { net.push(r.request().url()); r.abort(); });
await page.goto('file://' + path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../index.html'));
await page.waitForTimeout(800);
const vp = page.locator('#viewport');
const box = await vp.boundingBox();
const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
const settle = () => page.waitForTimeout(900);

const ids = await page.$$eval('#preset option', (os) => os.map((o) => o.value));
for (const id of ids) {
  await page.selectOption('#preset', id); await settle();
  await vp.screenshot({ path: `${outDir}/${id}.png` });
  await page.mouse.move(center.x, center.y);
  for (let i = 0; i < 7; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(80); }
  await settle();
  const e = await page.evaluate(() => Viewer.getExplode());
  await vp.screenshot({ path: `${outDir}/${id}_x.png` });
  const n = await page.evaluate(() => IC3D.S.model.parts.length);
  console.log(id.padEnd(10), String(n).padStart(3), 'parts  explode', e.toFixed(2));
}

// control valve deep-dive
await page.selectOption('#preset', 'cv_globe'); await settle();
await page.mouse.move(center.x, center.y);
for (let i = 0; i < 7; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(80); }
await settle();
await page.evaluate(() => IC3D.selectPart('plug', false)); await page.waitForTimeout(400);
await vp.screenshot({ path: `${outDir}/cv_info.png` });
// further wheel-in now zooms the camera
for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, -120); await page.waitForTimeout(60); }
await settle();
await vp.screenshot({ path: `${outDir}/cv_zoom.png` });
// wheel out: back to framed, then re-assemble
for (let i = 0; i < 14; i++) { await page.mouse.wheel(0, 120); await page.waitForTimeout(60); }
await settle();
console.log('after wheel-out explode', (await page.evaluate(() => Viewer.getExplode())).toFixed(2));
await page.check('#opt-section'); await settle();
await page.evaluate(() => IC3D.selectPart(null));
await vp.screenshot({ path: `${outDir}/cv_section.png` });
await page.uncheck('#opt-section');
await page.evaluate(() => Viewer.focus('spring')); await settle();
await vp.screenshot({ path: `${outDir}/cv_isolate.png` });
await page.evaluate(() => Viewer.focus(null)); await settle();
const exp = await page.evaluate(async () => ({ stl: (await Viewer.toSTL().arrayBuffer()).byteLength, objGroups: (await Viewer.toOBJ('x').text()).split('\n').filter((l) => l.startsWith('g ')).length }));
console.log('export', exp);
await page.screenshot({ path: `${outDir}/_full.png` });
console.log('errors', errors); console.log('network requests (blocked)', net);
await browser.close();
