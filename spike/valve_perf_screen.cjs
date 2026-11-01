// Screen timing (valve29): menu click -> view drawn and network idle.  Usage: node spike/valve_perf_screen.cjs http://127.0.0.1:8003
const { chromium } = require('playwright');
(async () => {
  const base = process.argv[2] || 'http://127.0.0.1:8000';
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
  await p.addInitScript(() => { window.__lt = []; new PerformanceObserver(l => l.getEntries().forEach(e => window.__lt.push(Math.round(e.duration)))).observe({ entryTypes: ['longtask'] }); });
  const out = {}; const lt = async () => { const x = await p.evaluate(() => { const v = window.__lt.slice(); window.__lt.length = 0; return v; }); return x.length ? Math.max(...x) : 0; };
  const idle = async (sel) => { await p.waitForLoadState('networkidle'); if (sel) await p.waitForSelector(sel, { timeout: 300000 }); await p.waitForLoadState('networkidle'); };
  let t = Date.now(); await p.goto(base + '/valve/#dash', { timeout: 600000 }); await idle('#v-dash .kpis');
  out.first_load_dashboard = Date.now() - t; out.first_load_longest_task = await lt();
  const views = [['docs', '#v-docs table, #v-docs .card'], ['list', '#xg tbody tr'], ['review', '#wlist .ti'], ['rev', '#v-rev .card, #v-rev .empty, #v-rev table'], ['proc', '#v-proc .vh'],
    ['pms', '#v-pms .vh'], ['rules', '.rp tbody tr'], ['export', '#v-export .card'], ['settings', '#v-settings .card'], ['dash', '#v-dash .kpis']];
  for (const [v, sel] of views) {
    if (!(await p.locator(`#menu button[data-v="${v}"]`).count())) continue;     // an older version without this view
    t = Date.now(); await p.click(`#menu button[data-v="${v}"]`); await idle(sel);
    out['view_' + v] = Date.now() - t; out['view_' + v + '_longest_task'] = await lt();
  }
  await p.click('#menu button[data-v="review"]'); await idle('#wlist .ti'); await lt();
  const nav = []; for (let i = 0; i < 12; i++) { t = Date.now(); await p.keyboard.press('j'); await p.waitForLoadState('networkidle'); nav.push(Date.now() - t); }
  nav.sort((a, b) => a - b); out.tag_nav_median = nav[6]; out.tag_nav_max = nav[11]; out.tag_nav_longest_task = await lt();
  await p.click('#menu button[data-v="list"]'); await idle('#xg tbody tr');
  t = Date.now(); await p.click('[data-lm="issues"]'); await idle('#ig tbody tr'); out.issue_list_render = Date.now() - t; out.issue_list_longest_task = await lt();
  console.log(JSON.stringify(out)); await b.close();
})().catch(e => { console.log(JSON.stringify({ error: String(e).slice(0, 300) })); process.exit(0); });
