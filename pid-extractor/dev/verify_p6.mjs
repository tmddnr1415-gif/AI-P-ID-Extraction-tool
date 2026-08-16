import { chromium } from 'playwright';
import { fixtureFor } from '/home/user/AI-P-ID-Extraction-tool/pid-extractor/dev/fixture_p6.mjs';
import { execSync } from 'child_process';

const gt = JSON.parse(execSync(`python3 -c "
import openpyxl, json
ws = openpyxl.load_workbook('/home/user/AI-P-ID-Extraction-tool/pid-extractor/ref/example_instrument_list.xlsx')['2.0_Instrument List']
print(json.dumps([{'type':ws.cell(r,8).value,'qty':ws.cell(r,9).value,'desc':ws.cell(r,10).value} for r in range(8,20)], ensure_ascii=False))
"`).toString());
const key = r => `${r.type}|${r.qty}|${(r.desc||'').toUpperCase()}`;
const cnt = a => a.reduce((m,r)=>(m[key(r)]=(m[key(r)]||0)+1,m),{});
const G = cnt(gt);

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
for (const grid of ['3x3', '4x4', '5x4']) {
  const [c, r] = grid.split('x').map(Number);
  const p = await (await b.newContext()).newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message.slice(0,100)));
  await p.goto('http://localhost:8124/');
  await p.evaluate((fx) => { window.__STUB_FIXTURE = fx; }, fixtureFor(c, r));
  await p.setInputFiles('#in-pdf', '/home/user/AI-P-ID-Extraction-tool/pid-extractor/ref/PID_Total.pdf');
  await p.waitForSelector('#pdf-state.ok', { timeout: 300000 });
  await p.evaluate(() => { document.querySelectorAll('.thumb').forEach(e => {
    if (e.querySelector('.no').textContent.includes('10LBA10-M05-0001')) e.click(); }); });
  await p.selectOption('#opt-grid', grid);
  await p.click('#btn-run');
  await p.waitForSelector('#sec-result:not(.hidden)', { timeout: 180000 });
  await p.check('#opt-vendor');
  await p.waitForTimeout(300);
  const got = await p.evaluate(() => [...document.querySelectorAll('#result tbody tr')].map(tr => ({
    type: tr.querySelector('select').value, qty: +tr.children[4].textContent,
    desc: tr.children[5].textContent.trim() })));
  const M = cnt(got);
  let hit = 0; for (const k of Object.keys(G)) hit += Math.min(G[k], M[k]||0);
  const bad = Object.keys(G).filter(k => (M[k]||0) !== G[k]).map(k => `정답${G[k]}/판독${M[k]||0} ${k}`);
  console.log(`${grid}  판독 ${got.length}행 · 일치 ${hit}/12  ${bad.length ? '차이: ' + bad.join(' | ') : ''}${errs.length ? ' errs:'+errs : ''}`);
  await p.close();
}
await b.close();
