// 모든 프리셋을 헤드리스로 렌더해 스크린샷을 남긴다. three.js 는 로컬 사본으로 대체.
//   node dev/shots.mjs <three.min.js 경로> <출력 폴더>
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import fs from 'node:fs'; import path from 'node:path'; import url from 'node:url';
const [threePath, outDir] = process.argv.slice(2);
fs.mkdirSync(outDir, { recursive: true });
const page = await (await chromium.launch({ args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader'] })).newPage({ viewport: { width: 1400, height: 900 } });
const errors = [];
page.on('pageerror', (e) => errors.push(String(e)));
page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
await page.route('**/three.min.js', (r) => r.fulfill({ body: fs.readFileSync(threePath), contentType: 'text/javascript' }));
const file = path.resolve(path.dirname(url.fileURLToPath(import.meta.url)), '../index.html');
await page.goto('file://' + file);
await page.waitForTimeout(800);
const ids = await page.$$eval('#preset option', (os) => os.map((o) => o.value));
for (const id of ids) {
  await page.selectOption('#preset', id);
  await page.waitForTimeout(300);
  const info = await page.evaluate(() => ({ parts: IC3D.S.model.parts.length, size: IC3D.S.model.bbox.size.map(Math.round) }));
  await page.locator('#viewport').screenshot({ path: `${outDir}/${id}.png` });
  console.log(id.padEnd(10), info.parts, 'parts', info.size.join('x'));
}
// 분해 + 라벨 + 내보내기
await page.selectOption('#preset', 'mov_gate');
await page.fill('#explode', '0.6'); await page.dispatchEvent('#explode', 'input');
await page.check('#opt-labels'); await page.waitForTimeout(300);
await page.locator('#viewport').screenshot({ path: `${outDir}/mov_gate_exploded.png` });
const exp = await page.evaluate(async () => ({ stl: (await Viewer.toSTL().arrayBuffer()).byteLength, obj: (await Viewer.toOBJ('x').text()).split('\n').length }));
console.log('export', exp);
await page.screenshot({ path: `${outDir}/_full.png` });
console.log('errors', errors);
process.exit(0);
