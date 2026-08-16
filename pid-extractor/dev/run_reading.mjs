/* 손으로(또는 Claude 가) 읽은 판독을 앱의 **실호출 자리**에 넣고 나머지를 시킨다.
 *
 *   node dev/run_reading.mjs <쪽> <판독.json> [<출력.xlsx>]
 *
 * 판독 JSON 은 `{"p9:r1c0": [ {type,x,y,line_context,equipment,position,
 * redundancy,vendor_scope,note_ref}, ... ], ...}` 꼴로 **타일 16칸을 모두** 적는다
 * (계기가 없으면 `[]`). 타일 이미지는 `dev/dump_tiles.mjs` 로 뽑는다.
 *
 * 이걸로 재는 것은 중복 제거·정렬·Q'ty·DESCRIPTION 조립·공급 역무 분리·Excel 쓰기다.
 * 모델이 실제로 얼마나 잘 읽는지는 이 경로로 잴 수 없다 — 판독을 밖에서 넣기 때문이다.
 *
 * 판독 JSON 은 도면의 계기 배치 자체라 **저장소에 넣지 않는다.** 공개 저장소다.
 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'fs';

const [PAGE, READ_PATH, OUT] = [Number(process.argv[2]), process.argv[3], process.argv[4]];
if (!PAGE || !READ_PATH) throw new Error('사용: node dev/run_reading.mjs <쪽> <판독.json> [<출력.xlsx>]');
const ROOT = '/home/user/AI-P-ID-Extraction-tool/pid-extractor';
const READ = JSON.parse(readFileSync(READ_PATH, 'utf8'));

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await (await b.newContext()).newPage();
const errs = []; p.on('pageerror', (e) => errs.push(e.message.slice(0, 140)));

let calls = 0;
await p.route('https://api.anthropic.com/**', async (route) => {
  const body = route.request().postDataJSON();
  calls++;
  let out;
  if (JSON.stringify(body).includes('타이틀블록')) {
    out = JSON.stringify({ drawing_no: '', system: '', notes: '' });   // 텍스트 레이어가 이미 준다
  } else {
    const lab = body.__label;
    if (!(lab in READ)) throw new Error(`판독 JSON 에 ${lab} 가 없습니다`);
    out = JSON.stringify(READ[lab]);
  }
  await route.fulfill({ status: 200, contentType: 'application/json',
    body: JSON.stringify({ content: [{ type: 'text', text: out }], stop_reason: 'end_turn' }) });
});

await p.goto('http://localhost:8124/');
/* 어느 타일의 요청인지 가로채는 쪽이 알아야 한다. callClaude 는 label 을 이미 받고,
   그 안에서 fetch 는 **첫 await 이전에** 동기로 불린다. 그래서 호출 직전에 라벨을
   심어 두면 일꾼 둘이 동시에 돌아도 섞이지 않는다. */
await p.evaluate(() => {
  const call = window.callClaude, fetch0 = window.fetch;
  window.fetch = function (u, o) {
    if (String(u).includes('api.anthropic.com') && window.__label) {
      const b = JSON.parse(o.body); b.__label = window.__label;
      o = { ...o, body: JSON.stringify(b) };
    }
    return fetch0.call(this, u, o);
  };
  window.callClaude = function (content, opts) {
    window.__label = (opts || {}).label || '';
    return call(content, opts);
  };
});

await p.setInputFiles('#in-pdf', ROOT + '/ref/PID_Total.pdf');
await p.waitForSelector('#sec-pages:not(.hidden)', { timeout: 180000 });
await p.setInputFiles('#in-tpl', ROOT + '/ref/example_instrument_list.xlsx');
await p.waitForFunction(() => document.querySelector('#tpl-state').className.includes('ok'), null, { timeout: 30000 });
await p.evaluate((n) => { state.selected.clear(); toggle(n, state.pages.find((x) => x.page === n)._el); }, PAGE);
await p.click('#btn-tiles');
await p.waitForSelector('#sec-run:not(.hidden)', { timeout: 60000 });
await p.click('#btn-run');
await p.waitForSelector('#sec-result:not(.hidden)', { timeout: 300000 });

const rows = await p.evaluate(() => run.rows.map((r) =>
  `${(r.vendor_scope || '-').padEnd(3)} ${r.type.padEnd(5)} ${r.qty} ${r.description}`));
console.log(`호출 ${calls}회 · 전체 ${rows.length}행`);
console.log(rows.join('\n'));

if (OUT) {
  await p.evaluate(() => { document.querySelector('#opt-vendor').checked = true; renderResult(); });
  const n = await p.evaluate(() => visibleRows().length);
  const b64 = await p.evaluate(async () => {
    const bytes = await buildXlsx(visibleRows());
    let s = ''; for (const x of new Uint8Array(bytes)) s += String.fromCharCode(x);
    return btoa(s);
  });
  writeFileSync(OUT, Buffer.from(b64, 'base64'));
  console.log(`공급 역무 제외 ${n}행 → ${OUT}`);
}
console.log('pageerror:', errs.length ? errs : '없음');
await b.close();
