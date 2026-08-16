/* dist/app.html 회귀 — **스텁이 아닌 진짜 호출 경로**를 확인한다.
 *
 * api.anthropic.com 을 가로채 모델 응답 모양 그대로 돌려준다. 여기서 재는 것은
 * 모델의 판독력이 아니라 ① 요청이 API 규격대로 나가는지 ② 응답을 받아 중복 제거·
 * DESCRIPTION 조립·Excel 쓰기까지 이어지는지 ③ **기록이 없는 아무 도면**에서도
 * 도는지다. 기록 있는 6쪽이 아니라 9쪽을 쓴다.
 */
import { chromium } from 'playwright';
import { writeFileSync } from 'fs';

const ROOT = '/home/user/AI-P-ID-Extraction-tool/pid-extractor';
const PAGE = Number(process.argv[2] || 9);
const OUT = process.argv[3];

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await (await b.newContext()).newPage();
const errs = []; p.on('pageerror', (e) => errs.push(e.message.slice(0, 160)));

const seen = [];
await p.route('https://api.anthropic.com/**', async (route) => {
  const body = route.request().postDataJSON();
  seen.push(body);
  const isPass1 = JSON.stringify(body).includes('타이틀블록');
  const text = isPass1
    ? JSON.stringify({ drawing_no: 'D00P-10LBA30-M05-0001', system: 'HP STEAM SYSTEM', notes: '1. THIS P&ID IS FOR GROUP#10, CONFIGURATION IS IDENTICAL FOR GROUP#20.' })
    : JSON.stringify([
        { type: 'PIT', x: 0.30, y: 0.40, line_context: 'FROM HRSG#11', equipment: 'HP STEAM', position: null, redundancy: null, vendor_scope: null, note_ref: null },
        { type: 'TIT', x: 0.70, y: 0.60, line_context: 'TO CLEAN DRAIN TANK', equipment: 'HP STEAM', position: 'DRAIN', redundancy: null, vendor_scope: '*', note_ref: null },
      ]);
  await route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ content: [{ type: 'text', text }], stop_reason: 'end_turn' }) });
});

await p.goto('file://' + ROOT + '/dist/app.html');
await p.setInputFiles('#in-pdf', ROOT + '/ref/PID_Total.pdf');
await p.waitForSelector('#sec-pages:not(.hidden)', { timeout: 180000 });
await p.setInputFiles('#in-tpl', ROOT + '/ref/example_instrument_list.xlsx');
await p.waitForFunction(() => document.querySelector('#tpl-state').className.includes('ok'), null, { timeout: 30000 });

await p.evaluate((n) => {
  state.selected.clear();
  document.querySelectorAll('.thumb.sel').forEach((t) => t.classList.remove('sel'));
  toggle(n, state.pages.find((x) => x.page === n)._el);
}, PAGE);
await p.click('#btn-tiles');
await p.waitForSelector('#sec-run:not(.hidden)', { timeout: 60000 });
await p.click('#btn-run');
await p.waitForSelector('#sec-result:not(.hidden)', { timeout: 300000 });

const req = seen.find((r) => !JSON.stringify(r).includes('타이틀블록')) || seen[0];
const img = req.messages[0].content.find((c) => c.type === 'image');
console.log(`도면            ${PAGE}쪽 (기록 없음)`);
console.log(`호출            ${seen.length}회  (Pass1 + 타일 16)`);
console.log(`model           ${req.model}`);
console.log(`max_tokens      ${req.max_tokens}`);
console.log(`이미지 블록     ${img.source.type}/${img.source.media_type} · ${Math.round(img.source.data.length / 1365)} KB`);
console.log(`행              ${await p.evaluate(() => run.rows.length)}`);
console.log(`표본 행         ${await p.evaluate(() => { const r = run.rows[0]; return `${r.system} | ${r.pid_no} | ${r.type} | ${r.qty} | ${r.description}`; })}`);
console.log(`공급 역무 표기  ${await p.evaluate(() => run.rows.filter((r) => r.vendor_scope).length)}`);

if (OUT) {
  const b64 = await p.evaluate(async () => {
    const bytes = await buildXlsx(visibleRows());
    let s = ''; for (const x of new Uint8Array(bytes)) s += String.fromCharCode(x);
    return btoa(s);
  });
  writeFileSync(OUT, Buffer.from(b64, 'base64'));
  console.log(`Excel           ${OUT}`);
}
console.log(`pageerror       ${errs.length ? errs.join(' | ') : '없음'}`);
await b.close();
