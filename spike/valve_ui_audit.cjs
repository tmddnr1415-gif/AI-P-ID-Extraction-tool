// Valve tool — screen self-audit (LOGIC L84 'ui_audit' borrowed): drive every screen and the mark-up tools like a
// reviewer, check the server state after each step, save screenshots, fail on any page error.
//
//   (PID_DATA_DIR=<COPY of a data folder> python3 -m uvicorn app.main:app --port 8000 &)   ← it writes mark-ups: use a copy
//   node spike/valve_ui_audit.cjs [base=http://127.0.0.1:8000] [shots=/tmp/valve_ui] [chrome=<path>]
//
// Needs: playwright (in the cloud container: require('playwright') works), a project with at least one analysed datasheet.
const { chromium } = require('playwright');
const fs = require('fs');
const [base = 'http://127.0.0.1:8000', shots = '/tmp/valve_ui', chrome] = process.argv.slice(2);
fs.mkdirSync(shots, { recursive: true });
const steps = [];
const ok = (name, cond, info = '') => { steps.push([cond ? 'PASS' : 'FAIL', name, info]); console.log(cond ? 'PASS' : 'FAIL', name, info); };

(async () => {
  const b = await chromium.launch(chrome ? { executablePath: chrome } : {});
  const p = await b.newPage({ viewport: { width: 1600, height: 950 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const api = (u, o) => p.evaluate(([u, o]) => fetch('/api/valve' + u, o).then(r => r.json()), [u, o || {}]);
  await p.addInitScript(() => { localStorage.setItem('valve.mkquick', '0'); localStorage.setItem('valve.mkbar', '1'); });   // dialog path first; quick mode checked below
  await p.goto(`${base}/valve/?embed=1&user=UI-AUDIT`); await p.waitForTimeout(1500);
  const projects = (await api('/projects')).projects;
  ok('project exists', projects.length > 0);
  const pid = projects[0].id, sum = await api(`/projects/${pid}/summary`);
  const tag = sum.tags.find(t => t.id) || {};
  ok('datasheet exists', !!tag.id, tag.tag);

  // 1. every screen opens without an error
  for (const v of ['dash', 'docs', 'list', 'review', 'rev', 'proc', 'pms', 'export', 'settings']) {
    const n = errs.length;
    await p.goto(`${base}/valve/?embed=1&user=UI-AUDIT&project=${encodeURIComponent(projects[0].name)}#${v}`); await p.waitForTimeout(v === 'review' ? 3000 : 1500);
    await p.screenshot({ path: `${shots}/${v}.png` });
    ok(`screen ${v}`, errs.length === n, errs.slice(n).join(' | ').slice(0, 200));
  }

  // 2. mark-up tools on one datasheet
  await p.goto(`${base}/valve/?embed=1&user=UI-AUDIT&ds=${tag.id}#review`); await p.waitForTimeout(3500);
  const ds = () => api(`/datasheets/${tag.id}`);
  const n0 = (await ds()).comments.length;
  const pg = await (await p.$('#wview .pg')).boundingBox();
  async function draw(tool, x0, y0, x1, y1, text, cat) {
    await p.click(`#wview .mkbar [data-tool="${tool}"]`);
    await p.mouse.move(pg.x + x0, pg.y + y0); await p.mouse.down();
    if (tool === 'pen') for (let i = 1; i <= 6; i++) await p.mouse.move(pg.x + x0 + i * 10, pg.y + y0 + (i % 2) * 12);
    await p.mouse.move(pg.x + x1, pg.y + y1, { steps: 4 }); await p.mouse.up();
    await p.waitForSelector('#modal:not([hidden])', { timeout: 3000 });
    await p.selectOption('#mBody select[name=category]', cat); await p.fill('#mBody textarea', text);
    await p.click('#mAct button.pri'); await p.waitForTimeout(600);
  }
  const kinds = [['rect', 'comment'], ['cloud', 'error'], ['ellipse', 'comment'], ['highlight', 'missing'], ['line', 'comment'],
    ['arrow', 'comment'], ['pen', 'missing'], ['text', 'question']];
  for (const [i, [k, cat]] of kinds.entries()) await draw(k, 120 + (i % 4) * 150, 300 + Math.floor(i / 4) * 120, 220 + (i % 4) * 150, 360 + Math.floor(i / 4) * 120, `audit ${k}`, cat);
  await p.click('#wview .mkbar [data-tool="note"]'); await p.mouse.click(pg.x + 700, pg.y + 200);
  await p.waitForSelector('#modal:not([hidden])'); await p.fill('#mBody textarea', 'audit note'); await p.click('#mAct button.pri'); await p.waitForTimeout(600);
  let d = await ds();
  const mine = d.comments.filter(c => (c.text || '').startsWith('audit'));
  ok('9 mark-up kinds saved', mine.length === 9 && new Set(mine.map(c => c.kind)).size === 9, mine.map(c => c.kind).join(','));
  const cl = mine.find(c => c.kind === 'cloud');
  // move the cloud: click inside it in select mode and drag
  const sz = await p.evaluate(id => { const g = document.querySelector(`#wview g[data-mid="${id}"]`); const r = g.getBoundingClientRect(); return [r.x, r.y, r.width, r.height]; }, cl.id);
  await p.keyboard.press('v');
  await p.mouse.move(sz[0] + sz[2] / 2, sz[1] + sz[3] / 2); await p.mouse.down(); await p.mouse.move(sz[0] + sz[2] / 2 + 40, sz[1] + sz[3] / 2 + 30, { steps: 5 }); await p.mouse.up(); await p.waitForTimeout(700);
  const moved = (await ds()).comments.find(c => c.id === cl.id).bbox;
  ok('select + move', moved[0] > cl.bbox[0] + 10, `${cl.bbox} → ${moved}`);
  await p.keyboard.press('Control+z'); await p.waitForTimeout(700);
  ok('undo move', JSON.stringify((await ds()).comments.find(c => c.id === cl.id).bbox) === JSON.stringify(cl.bbox));
  await p.keyboard.press('Control+y'); await p.waitForTimeout(700);
  ok('redo move', JSON.stringify((await ds()).comments.find(c => c.id === cl.id).bbox) === JSON.stringify(moved));
  await p.keyboard.press('Delete'); await p.waitForTimeout(700);
  ok('delete', !(await ds()).comments.some(c => c.id === cl.id));
  await p.keyboard.press('Control+z'); await p.waitForTimeout(700);
  ok('undo delete', (await ds()).comments.some(c => c.id === cl.id));
  await p.screenshot({ path: `${shots}/markup.png` });
  d = await ds();
  const mi = d.issues.filter(i => i.comment_id && mine.some(m => m.id === i.comment_id));
  ok('mark-ups become issues', mi.length === 9 && mi.some(i => i.type === 'Data Error') && mi.some(i => i.type === 'Data Missing'));
  // valve23: quick mode (no dialog) · underline · stamp · eraser · style
  await p.check('#wview .mkbar .mkquick'); await p.click('#wview .mkbar .mkcols i[data-col="#1aa35a"]');
  const nq0 = (await ds()).comments.length;
  await p.click('#wview .mkbar [data-tool="underline"]'); await p.mouse.move(pg.x + 120, pg.y + 420); await p.mouse.down(); await p.mouse.move(pg.x + 260, pg.y + 428, { steps: 4 }); await p.mouse.up(); await p.waitForTimeout(700);
  await p.click('#wview .mkbar [data-tool="stamp"]'); await p.selectOption('#wview .mkbar .mkst', 'HOLD'); await p.mouse.click(pg.x + 420, pg.y + 160); await p.waitForTimeout(700);
  const cq = (await ds()).comments; const und = cq.find(c => c.kind === 'underline'), stp = cq.find(c => c.kind === 'stamp');
  ok('quick mark-ups (underline · stamp) with style', cq.length === nq0 + 2 && und?.style?.color === '#1aa35a' && stp?.style?.stamp === 'HOLD');
  await p.click('#wview .mkbar [data-tool="eraser"]'); const gb = await p.evaluate(id => { const g = document.querySelector(`svg.mk [data-mid="${id}"]`); const r = g?.getBoundingClientRect(); return r && [r.x, r.y, r.width, r.height]; }, stp?.id);
  if (gb) await p.mouse.click(gb[0] + gb[2] / 2, gb[1] + gb[3] / 2); await p.waitForTimeout(700);
  ok('eraser deletes a mark-up', (await ds()).comments.length === nq0 + 1);
  await p.click('#wview .mkbar [data-tool="select"]'); await p.uncheck('#wview .mkbar .mkquick');

  // 3. deliverables carry them
  const pdf = await p.evaluate(u => fetch(u).then(r => r.status), `/api/valve/projects/${pid}/markup.pdf?tag=${encodeURIComponent(d.tag_key)}`);
  ok('mark-up PDF', pdf === 200);
  const xl = await p.evaluate(u => fetch(u).then(r => r.status), `/api/valve/projects/${pid}/issues.xlsx`);
  ok('issue list xlsx', xl === 200);
  const fb = await api(`/projects/${pid}/feedback.json`);
  ok('review feedback', fb.kind === 'valve-feedback' && fb.missed.length >= 2);

  // 4. clean up what the audit drew (soft delete — History keeps it)
  for (const m of mine) await api(`/comments/${m.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ delete: true }) });
  ok('no page errors', errs.length === 0, errs.slice(0, 5).join(' | '));
  fs.writeFileSync(`${shots}/result.json`, JSON.stringify(steps, null, 1));
  await b.close();
  const fails = steps.filter(s => s[0] === 'FAIL').length;
  console.log(`${steps.length - fails}/${steps.length} passed · screenshots ${shots}`);
  process.exit(fails ? 1 : 0);
})();
