import { chromium } from 'playwright';
import { FIXTURE_P6 } from './fixture_p6.mjs';
import { execSync } from 'child_process';

const gt = JSON.parse(execSync(`python3 -c "
import openpyxl, json
ws = openpyxl.load_workbook('/home/user/AI-P-ID-Extraction-tool/pid-extractor/ref/example_instrument_list.xlsx')['2.0_Instrument List']
print(json.dumps([{'type':ws.cell(r,8).value,'qty':ws.cell(r,9).value,'desc':ws.cell(r,10).value,
                  'system':ws.cell(r,6).value,'pid':ws.cell(r,7).value} for r in range(8,20)], ensure_ascii=False))
"`).toString());

const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await (await b.newContext()).newPage();
await p.goto('http://localhost:8124/');
await p.evaluate((fx) => { window.__STUB_FIXTURE = fx; }, FIXTURE_P6);
await p.setInputFiles('#in-pdf', '/home/user/AI-P-ID-Extraction-tool/pid-extractor/ref/PID_Total.pdf');
await p.waitForSelector('#pdf-state.ok', { timeout: 240000 });
await p.evaluate(() => { document.querySelectorAll('.thumb').forEach(e => {
  if (e.querySelector('.no').textContent.includes('10LBA10-M05-0001')) e.click(); }); });
await p.click('#btn-run');
await p.waitForSelector('#sec-result:not(.hidden)', { timeout: 120000 });
await p.check('#opt-vendor');
await p.waitForTimeout(300);
const got = await p.evaluate(() => [...document.querySelectorAll('#result tbody tr')].map(tr => ({
  type: tr.querySelector('select').value, qty: +tr.children[4].textContent,
  desc: tr.children[5].textContent.trim(), system: tr.children[1].textContent.trim(),
  pid: tr.children[2].textContent.trim() })));
await b.close();

const key = r => `${r.type}|${r.qty}|${(r.desc||'').toUpperCase()}`;
const cnt = a => a.reduce((m, r) => (m[key(r)] = (m[key(r)] || 0) + 1, m), {});
const G = cnt(gt), M = cnt(got);
let hit = 0;
for (const k of Object.keys(G)) hit += Math.min(G[k], M[k] || 0);
console.log(`정답 ${gt.length}행 / 판독 ${got.length}행 / 완전일치 ${hit}`);
console.log(`SYSTEM  정답 "${gt[0].system}"  판독 "${got[0]?.system}"`);
console.log(`P&ID    정답 "${gt[0].pid}"  판독 "${got[0]?.pid}"`);
for (const k of Object.keys(G)) if ((M[k]||0) !== G[k]) console.log(`  차이 정답${G[k]} 판독${M[k]||0}  ${k}`);
for (const k of Object.keys(M)) if (!G[k]) console.log(`  오탐 ${M[k]}  ${k}`);
