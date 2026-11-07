// Screens of every menu, starting from Import on an EMPTY server (8007) and then a data copy (8000):  node spike/valve_menu_shots.cjs <outdir>
// Real files are read from /tmp/ext (client data — never committed); screenshots go to a git-excluded folder.
const { chromium } = require('playwright');
const OUT = process.argv[2], FRESH = 'http://127.0.0.1:8007', BASE = 'http://127.0.0.1:8000';
const F = { datasheet: '/tmp/ext/datasheet/Datasheet.pdf', valvelist: '/tmp/ext/vl/TBE.xlsx', pms: '/tmp/ext/pms/98-98-PI-SPC-00001_0001_0.pdf', process: '/tmp/ext/pd/Process_Data.pdf' };
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1600, height: 900 } });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  const shot = async n => { await p.waitForTimeout(400); await p.screenshot({ path: `${OUT}/${n}.png` }); console.log('shot', n); };
  const menu = async v => { await p.click(`button[data-v="${v}"]`); await p.waitForTimeout(v === 'review' ? 3500 : 1800); };
  // ── Import (빈 설치) ──
  await p.goto(`${FRESH}/valve/?user=engineer`); await p.waitForTimeout(2000);
  await menu('docs'); await shot('01_import_empty');
  await p.setInputFiles('label.drop[data-k="datasheet"] input', F.datasheet); await p.waitForTimeout(2500); await shot('02_import_datasheet_progress');
  for (const k of ['pms', 'process', 'valvelist']) { await p.setInputFiles(`label.drop[data-k="${k}"] input`, F[k]); await p.waitForTimeout(800); }
  for (let i = 0; i < 400; i++) {
    const r = await p.evaluate(async () => { const pr = (await (await fetch('/api/valve/projects')).json()).projects[0];
      const s = await (await fetch(`/api/valve/projects/${pr.id}/summary`)).json(); return s.documents.map(d => d.status); });
    if (r.length >= 4 && r.every(s => s === 'done' || s === 'error')) break; await p.waitForTimeout(3000);
  }
  await p.reload(); await p.waitForTimeout(2500); await menu('docs'); await shot('03_import_done');
  await menu('dash'); await shot('04_dashboard_after_import');
  // ── 각 메뉴 (실자료 사본) ──
  await p.goto(`${BASE}/valve/?user=engineer`); await p.waitForTimeout(2500);
  await menu('dash'); await shot('05_dashboard');
  await menu('docs'); await shot('06_document_management');
  await menu('list'); await p.click('[data-lm="grid"]'); await p.waitForTimeout(1500); await shot('07_valve_list');
  await p.click('[data-lm="issues"]'); await p.waitForTimeout(2000); await shot('08_issue_list');
  await p.click('[data-lm="req"]'); await p.waitForTimeout(1500); await shot('09_special_requirements');
  await p.goto(`${BASE}/valve/?user=engineer&ds=117#review`); await p.waitForTimeout(4000); await shot('10_datasheet_review');
  await menu('rev'); await shot('11_revision_comparison');
  await menu('proc'); await shot('12_process_data_verification');
  await menu('pms'); await shot('13_pms_compliance');
  await menu('rules'); await shot('14_rule_performance');
  await menu('export'); await shot('15_reports_export');
  await menu('settings'); await shot('16_settings');
  console.log(JSON.stringify({ errs })); await b.close();
})();
