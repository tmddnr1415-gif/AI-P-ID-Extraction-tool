// 스펙 JSON → PNG (헤드리스 크로미움). 도면 뷰와 3D 를 나란히 비교할 때 쓴다.
//
//   node ic-3d-builder/dev/render.mjs <spec.json> <out.png> [--views iso,front,side,top] [--three <three.min.js>] [--explode 0.5]
//
// three.js 는 cdnjs 에서 받는다. 네트워크가 막혀 있으면 --three 로 로컬 사본을 준다
// (npm i three@0.128.0 → node_modules/three/build/three.min.js).
// --views 를 여러 개 주면 out 이름 뒤에 _iso, _front … 를 붙여 따로 저장한다.
import { createRequire } from 'node:module';
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(`--${k}`); return i >= 0 ? args[i + 1] : d; };
const [specPath, out] = args;
if (!specPath || !out) { console.log('사용법: render.mjs <spec.json> <out.png> [--views iso,front] [--three path] [--explode 0..1]'); process.exit(1); }
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
  console.error('three.js 를 불러오지 못했습니다. --three 로 로컬 사본 경로를 주세요.');
  await browser.close(); process.exit(1);
}
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
await page.evaluate((s) => IC3D.loadSpec(s), spec);
if (explode) await page.evaluate((k) => { document.getElementById('explode').value = k; Viewer.setExplode(k); }, explode);
for (const v of views) {
  await page.evaluate((name) => { Viewer.setView(name, true); Viewer.fit(); }, v);
  await page.waitForTimeout(250);
  const file = views.length > 1 ? out.replace(/\.png$/i, `_${v}.png`) : out;
  await page.locator('#viewport').screenshot({ path: file });
  console.log(`→ ${file}`);
}
const info = await page.evaluate(() => ({ size: IC3D.S.model.bbox.size.map(Math.round), warnings: IC3D.S.model.warnings }));
console.log(`외곽 L×W×H ${info.size.join(' × ')} mm`);
for (const w of info.warnings) console.log(`⚠ ${w}`);
if (errors.length) console.log('페이지 오류:', errors);
await browser.close();
