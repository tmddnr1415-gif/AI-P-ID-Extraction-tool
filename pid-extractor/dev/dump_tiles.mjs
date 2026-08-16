/* 고른 도면의 타일을 앱과 **똑같은 설정**으로 뽑아 PNG 로 저장한다.
 * (4×4 · 겹침 10% · 긴 변 1560px — index.html 의 tileRects/renderTile 그대로)
 * 사람이나 Claude 가 그 이미지를 직접 보고 읽으려고 만든다. */
import { chromium } from 'playwright';
import { writeFileSync, mkdirSync } from 'fs';

const ROOT = '/home/user/AI-P-ID-Extraction-tool/pid-extractor';
const PAGE = Number(process.argv[2]);
const OUT = process.argv[3];
mkdirSync(OUT, { recursive: true });

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await (await b.newContext()).newPage();
await p.goto('http://localhost:8124/');
await p.setInputFiles('#in-pdf', ROOT + '/ref/PID_Total.pdf');
await p.waitForSelector('#sec-pages:not(.hidden)', { timeout: 180000 });

const meta = await p.evaluate((n) => {
  const x = state.pages.find((q) => q.page === n);
  return { drawing_no: x.drawing_no, title: x.title, notes: (x.notes || '').slice(0, 1200) };
}, PAGE);
console.log(JSON.stringify(meta, null, 1));

const shots = await p.evaluate(async (n) => {
  const out = [];
  for (const rect of tileRects(4, 4)) {
    const cv = await renderTile(n, rect, 1560);
    out.push({ k: `r${rect.r}c${rect.c}`, b64: cv.toDataURL('image/png').split(',')[1] });
  }
  return out;
}, PAGE);
for (const s of shots) writeFileSync(`${OUT}/${s.k}.png`, Buffer.from(s.b64, 'base64'));
console.log(`타일 ${shots.length}장 → ${OUT}`);
await b.close();
