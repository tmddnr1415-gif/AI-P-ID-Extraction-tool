// Excel-style column filter on every list — open ▾, keep one value, OK; counts + time.  node spike/valve_filter_check.cjs <base> <shotdir>
const { chromium } = require('playwright');
(async () => {
  const [base, OUT] = [process.argv[2], process.argv[3]];
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 900 } }); const errs = []; p.on('pageerror', e => errs.push(String(e)));
  const R = {};
  const pick = async (sel, value, shot) => {        // open ▾, keep only `value`, OK — time until rows redrawn
    await p.click(sel); await p.waitForSelector('.xfpop');
    if (shot) await p.screenshot({ path: `${OUT}/${shot}.png` });
    await p.click('.xfpop .xfall input'); if ((await p.isChecked('.xfpop .xfall input'))) await p.click('.xfpop .xfall input');
    await p.fill('.xfpop .xfq', value); await p.waitForTimeout(150);
    const t = await p.evaluate(() => performance.now()); await p.click('.xfpop .xfok');
    await p.evaluate(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))));
    return Math.round(await p.evaluate(() => performance.now()) - t);
  };
  await p.goto(base + '/valve/?user=xf#list'); await p.waitForSelector('#xg tbody tr[data-id]'); await p.waitForTimeout(800);
  R.grid_ms = await pick('#xg th[data-k="area"] .xfb', 'North', 'xf_1_valve_list_popup');
  R.grid = await p.textContent('#gcnt'); await p.screenshot({ path: `${OUT}/xf_2_valve_list_north.png` });
  await p.click('[data-lm="issues"]'); await p.waitForSelector('#ig tbody tr[data-i]');
  R.iss_ms = await pick('#ig thead th:nth-child(9) .xfb', 'Data Error', 'xf_3_issue_popup');
  R.iss = await p.textContent('#icnt'); await p.screenshot({ path: `${OUT}/xf_4_issue_data_error.png` });
  // sort descending on Tag
  await p.click('#ig thead th:nth-child(2) .xfb'); const t0 = Date.now(); await p.click('.xfpop [data-s="-1"]'); await p.waitForTimeout(100); R.iss_sort_first = await p.textContent('#ig tbody tr[data-i] td:nth-child(2)'); R.iss_sort_ms = Date.now() - t0;
  await p.click('[data-lm="req"]'); await p.waitForSelector('#rqt tbody tr[data-id]');
  R.req_ms = await pick('#rqt thead th:nth-child(3) .xfb', 'North'); R.req = (await p.$$('#rqt tbody tr[data-id]')).length;
  await p.click('#menu button[data-v="proc"]'); await p.waitForSelector('#pdtb tr[data-n]');
  R.proc_ms = await pick('#v-proc thead th:nth-child(5) .xfb', 'Mismatch', 'xf_5_process_popup'); R.proc = (await p.$$('#pdtb tr[data-n]')).length;
  await p.click('#menu button[data-v="pms"]'); await p.waitForSelector('#pmtb tr[data-n]');
  R.pms_ms = await pick('#v-pms thead th:nth-child(7) .xfb', 'Review Required'); R.pms = (await p.$$('#pmtb tr[data-n]')).length; await p.screenshot({ path: `${OUT}/xf_6_pms_filtered.png` });
  await p.click('#menu button[data-v="dash"]'); await p.waitForSelector('#v-dash .kpis'); await p.waitForTimeout(500);
  R.dash_buttons = await p.$$eval('#v-dash .xfb', x => x.length);
  R.dash_ms = await pick('#v-dash .card:has(h3:text("By Area")) thead th:nth-child(1) .xfb', 'North', 'xf_7_dashboard_popup');
  R.dash_vis = await p.$$eval('#v-dash .card:has(h3:text("By Area")) tbody tr', x => x.filter(r => !r.hidden).length);
  await p.click('#menu button[data-v="docs"]'); await p.waitForTimeout(500); R.docs_buttons = await p.$$eval('#v-docs .xfb', x => x.length);
  await p.click('#menu button[data-v="rules"]'); await p.waitForTimeout(800); R.rules_buttons = await p.$$eval('#v-rules .xfb', x => x.length);
  await p.click('#menu button[data-v="rev"]'); await p.waitForTimeout(1500); R.rev_buttons = await p.$$eval('#v-rev .xfb', x => x.length);
  // the filter is kept when coming back
  await p.click('#menu button[data-v="list"]'); await p.waitForTimeout(800); R.req_kept = (await p.$$('#rqt tbody tr[data-id]')).length;
  console.log(JSON.stringify({ R, errs })); await b.close();
})();
