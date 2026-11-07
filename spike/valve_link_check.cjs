// valve29 window live-link check: pop-out PDF + second window follow the main window and each other.
// Usage: node spike/valve_link_check.cjs [http://127.0.0.1:8002]   (run on a DATA COPY — it records one decision)
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 1500, height: 900 } });
  const A = await ctx.newPage(); const errs = []; A.on('pageerror', e => errs.push('A ' + e.message));
  const base = process.argv[2] || 'http://127.0.0.1:8002';
  await A.goto(base + '/valve/?ds=117#review'); await A.waitForLoadState('networkidle'); await A.waitForTimeout(1200);
  // 1. pop-out PDF
  const t0 = Date.now();
  const [P] = await Promise.all([ctx.waitForEvent('page'), A.click('#wview [data-a2="popout"]')]);
  P.on('pageerror', e => errs.push('P ' + e.message));
  await P.waitForLoadState('networkidle'); await P.waitForSelector('.pg img'); const popMs = Date.now() - t0;
  const popTitle1 = await P.title();
  const heap = await P.evaluate(() => performance.memory ? Math.round(performance.memory.usedJSHeapSize / 1048576) : -1);
  // 2. next tag in main -> pop follows
  await A.keyboard.press('j'); await A.waitForTimeout(1200);
  const mainTag = (await A.locator('#whead .hk.tag b').innerText()).trim(); const popTag = (await P.locator('#ptag').innerText()).trim();
  // 3. main selects a field -> pop shows it
  await A.evaluate(() => { const x = [...document.querySelectorAll('#wtabs button')].find(b => b.dataset.t === 'data'); x && x.click(); });
  await A.waitForTimeout(300); await A.locator('#wbody .fl[data-k="seat_material"]').first().click(); await A.waitForTimeout(600);
  const popField = await P.locator('.ov.field, .ov[class*="field"]').count();
  // 4. pop clicks an issue box -> main selects that issue
  const box = P.locator('.ov').filter({ hasNot: P.locator('.nothing') }).first();
  const ovs = await P.locator('.ov[data-i], .ov').count();
  const iv = P.locator('.ov.missing, .ov.error, .ov.process, .ov.material').first(); await iv.scrollIntoViewIfNeeded(); await iv.click({ force: true }); await P.waitForTimeout(900);
  const mainTab = await A.evaluate(() => [...document.querySelectorAll('#wtabs button')].find(b => b.classList.contains('on'))?.dataset.t);
  const mainSel = await A.locator('#wview .ov.sel').count();
  // 5. second full window: Issue List row click -> main (review) follows
  const B = await ctx.newPage(); B.on('pageerror', e => errs.push('B ' + e.message));
  await B.goto(base + '/valve/#list'); await B.waitForLoadState('networkidle'); await B.click('[data-lm="issues"]'); await B.waitForSelector('#ig tbody tr[data-i]');
  const allRows = await B.locator('#ig tbody tr[data-i]').evaluateAll(trs => trs.map(t => t.dataset.i));
  const pickI = allRows.findIndex(x => !/^\d+\|(Data Missing|Reviewer|Revision)/.test(x));
  const row = B.locator('#ig tbody tr[data-i]').nth(pickI); const di = await row.getAttribute('data-i'); await row.locator('td').nth(2).click(); await A.waitForTimeout(1500);
  const wantDs = +di.split('|')[0]; const mainDs = await A.evaluate(() => new URL(location.href).searchParams.get('ds'));
  const mainTag2 = (await A.locator('#whead .hk.tag b').innerText()).trim(); const popTag2 = (await P.locator('#ptag').innerText()).trim();
  const bTag = await B.locator('#ig tbody tr[data-i]').nth(pickI).locator('td').nth(1).innerText();
  // 6. decision in window B -> main and pop refresh
  const ikey = di.slice(di.indexOf('|') + 1);
  await B.locator(`#ig tbody tr[data-i="${di}"] select[data-ist]`).selectOption('Confirmed'); await B.waitForTimeout(400);
  await B.locator('#mAct button.pri').click(); await B.waitForTimeout(1500);
  await A.evaluate(() => { const x = [...document.querySelectorAll('#wtabs button')].find(b => b.dataset.t === 'iss'); x && x.click(); }); await A.waitForTimeout(500);
  const mainShows = await A.locator(`#wbody select[data-ist="${ikey}"]`).inputValue().catch(() => 'not-found');
  if (process.argv[3]) { await A.screenshot({ path: process.argv[3] + '_main.png' }); await P.screenshot({ path: process.argv[3] + '_pop.png' }); }
  const ok = mainTag === popTag && popField > 0 && mainTab === 'iss' && mainSel > 0 && mainTag2 === popTag2 && mainShows === 'Confirmed' && !errs.length;
  console.log(ok ? 'LINK OK' : 'LINK FAIL');
  console.log(JSON.stringify({ decisionInB: 'Confirmed', mainShows, popMs, popTitle1, popHeapMB: heap, mainTag, popTag, popField, ovs, mainTab, mainSel, rowTagInB: bTag.trim(), mainTag2, popTag2, errs }));
  await b.close();
})();
