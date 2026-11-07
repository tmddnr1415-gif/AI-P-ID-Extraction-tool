// Every interaction, click -> screen settled (no fetch in flight, no DOM change for 80 ms; the 80 ms is subtracted).
// Also the longest main-thread block (long task) during it — what the user feels as a freeze.
//   node spike/valve_speed.cjs http://127.0.0.1:8000 [ds_id]
const { chromium } = require('playwright');
(async () => {
  const base = process.argv[2] || 'http://127.0.0.1:8000', ds = process.argv[3] || '117';
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
  await p.addInitScript(() => {
    window.__lt = []; new PerformanceObserver(l => l.getEntries().forEach(e => window.__lt.push(Math.round(e.duration)))).observe({ entryTypes: ['longtask'] });
    window.__inf = 0; const f = window.fetch; window.fetch = (...a) => { window.__inf++; return f(...a).finally(() => setTimeout(() => window.__inf--, 0)); };
    window.__last = performance.now(); new MutationObserver(() => { window.__last = performance.now(); }).observe(document, { subtree: true, childList: true, attributes: true, characterData: true });
    window.__settle = (t0) => new Promise(res => { const tick = () => { const n = performance.now();
      if (window.__inf === 0 && n - window.__last > 80 && n - t0 > 400) res(Math.round(Math.max(window.__last, t0) - t0)); else if (n - t0 > 30000) res(-1); else setTimeout(tick, 10); }; tick(); });
  });
  const R = {}, errs = []; p.on('pageerror', e => errs.push(String(e).slice(0, 200)));
  const act = async (name, fn) => {
    await p.evaluate(() => { window.__lt.length = 0; window.__t0 = performance.now(); window.__last = window.__t0; });
    try { await fn(); } catch (e) { R[name] = 'ERR ' + String(e).slice(0, 80); return; }
    const ms = await p.evaluate(() => window.__settle(window.__t0)); const lt = await p.evaluate(() => window.__lt.length ? Math.max(...window.__lt) : 0);
    R[name] = { ms, block: lt };
  };
  const t = Date.now(); await p.goto(base + '/valve/?user=speed#dash'); await p.waitForSelector('#v-dash .kpis'); await p.evaluate(() => window.__settle(0)); R.first_load = { ms: Date.now() - t };
  const V = ['docs', 'list', 'review', 'rev', 'proc', 'pms', 'rules', 'export', 'settings', 'dash'];
  for (const pass of ['1st', '2nd']) for (const v of V) await act(`menu_${v}_${pass}`, () => p.click(`#menu button[data-v="${v}"]`));
  await p.click('#menu button[data-v="list"]'); await p.waitForTimeout(500);
  await act('list_tab_issues', () => p.click('[data-lm="issues"]'));
  await act('list_issue_search', () => p.fill('#iq', '98ESDV'));
  await act('list_issue_search_clear', () => p.fill('#iq', ''));
  await act('list_issue_row_click', () => p.click('#ig tbody tr:not(.vsp) >> nth=3'));
  await act('list_issue_scroll', () => p.evaluate(() => { const w = document.querySelector('#ig')?.closest('.xg-wrap'); if (w) w.scrollTop = w.scrollHeight / 2; }));
  await act('list_tab_req', () => p.click('[data-lm="req"]'));
  await act('list_tab_grid', () => p.click('[data-lm="grid"]'));
  await act('list_grid_search', () => p.fill('#gq', '98'));
  await act('list_grid_search_clear', () => p.fill('#gq', ''));
  await act('list_grid_row_click', () => p.click('#xg tbody tr:not(.vsp) >> nth=5'));
  await p.goto(`${base}/valve/?user=speed&ds=${ds}#review`); await p.waitForSelector('#wlist .ti'); await p.evaluate(() => window.__settle(0));
  for (let i = 0; i < 8; i++) await act(`review_next_tag_${i}`, () => p.keyboard.press('j'));
  for (const [k] of [['iss'], ['chk'], ['sum'], ['data'], ['proc'], ['pms'], ['mat'], ['rev'], ['notes'], ['cmt'], ['hist'], ['iss']]) await act(`review_tab_${k}`, () => p.click(`#wtabs [data-t="${k}"]`));
  await act('review_issue_card', () => p.click('#wbody .iss >> nth=1'));
  await act('review_compare_open', () => p.click('#wbody .iss .ibtn >> nth=0'));
  await act('review_dialog_close', () => p.keyboard.press('Escape'));
  await act('review_tag_search', () => p.fill('#wq', 'SDV'));
  await act('review_tag_search_clear', () => p.fill('#wq', ''));
  await act('review_zoom_in', () => p.keyboard.press('+'));
  await act('review_page_down', () => p.keyboard.press('PageDown'));
  const ms = Object.entries(R).filter(([, v]) => v && v.ms >= 0).map(([k, v]) => [k, v.ms, v.block]).sort((a, b) => b[1] - a[1]);
  console.log(JSON.stringify({ R, slowest: ms.slice(0, 15), errs }));
  await b.close();
})().catch(e => { console.log(JSON.stringify({ error: String(e).slice(0, 300) })); process.exit(0); });
