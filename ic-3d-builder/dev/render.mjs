// Spec JSON → PNG (headless Chromium), to compare the 3D with the drawing views.
//
//   node ic-3d-builder/dev/render.mjs <spec.json> <out.png> [--views iso,front,side,top] [--three <three.min.js>]
//                                     [--explode 0..1] [--section] [--labels auto|on|off]
//
// three.js is loaded from cdnjs. If the network blocks it, pass a local copy with --three
// (npm i three@0.128.0 → node_modules/three/build/three.min.js).
// Several --views write one file each with _iso, _front … appended.
import { createRequire } from 'node:module';
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const [specPath, out] = args;
if (!specPath || !out) { console.log('usage: render.mjs <spec.json> <out.png> [--views iso,front] [--three path] [--explode 0..1] [--section] [--labels on]'); process.exit(1); }
const views = opt('views', 'iso').split(',');
const three = opt('three');
const explode = Number(opt('explode', 0));

const browser = await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
if (three) await page.route('**/three.min.js', (r) => r.fulfill({ body: fs.readFileSync(three), contentType: 'text/javascript' }));
const html = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../index.html');
await page.goto('file://' + html);
await page.waitForTimeout(600);
if (!(await page.evaluate(() => !!window.THREE))) {
  console.error('Could not load three.js. Pass a local copy with --three.');
  await browser.close(); process.exit(1);
}
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
await page.evaluate((s) => IC3D.loadSpec(s), spec);
if (args.includes('--section')) await page.evaluate(() => Viewer.setOption('section', true));
await page.evaluate((l) => Viewer.setOption('labels', l), opt('labels', 'auto'));
for (const v of views) {
  await page.evaluate(([name, k]) => { Viewer.setView(name); Viewer.setExplode(k, true); }, [v, explode]);
  await page.waitForTimeout(700);
  const file = views.length > 1 ? out.replace(/\.png$/i, `_${v}.png`) : out;
  await page.locator('#viewport').screenshot({ path: file });
  console.log(`→ ${file}`);
}
const info = await page.evaluate(() => ({ size: IC3D.S.model.bbox.size.map(Math.round), warnings: IC3D.S.model.warnings }));
console.log(`Envelope L×W×H ${info.size.join(' × ')} mm`);
for (const w of info.warnings) console.log(`⚠ ${w}`);
if (errors.length) console.log('page errors:', errors);
await browser.close();
