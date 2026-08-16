/* pdf.js 를 어디서 가져오는지, 막히면 어떻게 되는지 본다.
   시나리오: (a) cdnjs 만 막힘 → 다음 CDN 으로 넘어가야 한다
             (b) 전부 막힘     → 원인을 화면에 쓰고 멈춰야 한다
             (c) 심어 둔 배포본 → CDN 을 아예 안 건드려야 한다 */
import { chromium } from 'playwright';
import { readFileSync, writeFileSync } from 'fs';
const ROOT = '/home/user/AI-P-ID-Extraction-tool/pid-extractor';
const SP = process.argv[2];
const VENDOR = '/home/user/AI-P-ID-Extraction-tool/pid-instrument-tool/web/vendor';

const wrap = (f, out) => writeFileSync(out,
  '<!doctype html><html lang="ko"><head><meta charset="utf-8"></head><body>'
  + readFileSync(f, 'utf8') + '</body></html>');
wrap(ROOT + '/dist/artifact.html', SP + '/w_built.html');

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
async function trial(name, file, blockHosts) {
  const p = await (await b.newContext()).newPage();
  const hit = [], blocked = [];
  // CDN 요청은 실제로 나가지 않게 하고, 막을 것과 살릴 것을 나눈다.
  await p.route('**/pdf.min.js', async (r) => {
    const host = new URL(r.request().url()).host;
    if (blockHosts.some((h) => host.includes(h))) { blocked.push(host); return r.abort('failed'); }
    hit.push(host);
    await r.fulfill({ status: 200, contentType: 'application/javascript',
      body: readFileSync(VENDOR + '/pdf.min.js', 'utf8') });
  });
  await p.route('**/pdf.worker.min.js', (r) => r.fulfill({ status: 200,
    contentType: 'application/javascript', body: readFileSync(VENDOR + '/pdf.worker.min.js', 'utf8') }));
  await p.goto('file://' + file);
  await p.setInputFiles('#in-pdf', ROOT + '/ref/PID_Total.pdf');
  await p.waitForFunction(() => !/여는 중/.test(document.querySelector('#pdf-state').textContent),
                          null, { timeout: 240000 }).catch(() => {});
  const st = (await p.textContent('#pdf-state')).trim();
  console.log(`${name}`);
  console.log(`   막은 곳 ${blocked.join(', ') || '없음'} · 가져온 곳 ${hit.join(', ') || '없음'}`);
  console.log(`   결과    ${st.slice(0, 110)}`);
  await p.close();
}
wrap(ROOT + '/index.html', SP + '/w_raw.html');
await trial('(a) cdnjs 만 막힘', SP + '/w_raw.html', ['cdnjs']);
await trial('(b) 전부 막힘', SP + '/w_raw.html', ['cdnjs', 'jsdelivr', 'unpkg']);
await trial('(c) 심어 둔 배포본', SP + '/w_built.html', ['cdnjs', 'jsdelivr', 'unpkg']);
await b.close();
