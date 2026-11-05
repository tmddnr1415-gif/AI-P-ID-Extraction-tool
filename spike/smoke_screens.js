// hotfix132 — 전 화면 눈 점검 (출시 전 점검표 항목).  서버를 띄운 뒤:
//   NODE_PATH=$(npm root -g) node spike/smoke_screens.js http://localhost:8000 out/smoke [--embed]
// 화면마다 1440x900 캡처를 <저장폴더>/<이름>.png 로 남기고, 콘솔 오류 · 400 이상 응답 · 공통 띠 유무 ·
// 띠 때문에 화면이 넘치는지(문서 세로 넘침 px)를 JSON 으로 찍는다.  오류가 하나라도 있으면 끝 코드 1.
// --embed 를 주면 부서 대시보드 안처럼 `?embed=1&user=홍길동` 을 붙여 연다 (띠가 없어야 한다).
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const args = process.argv.slice(2);
const embed = args.includes('--embed');
const [base, out] = args.filter((a) => !a.startsWith('--'));
if (!base || !out) { console.error('사용법: node spike/smoke_screens.js <서버주소> <저장폴더> [--embed]'); process.exit(2); }
fs.mkdirSync(out, { recursive: true });

// [이름, 주소, 띠가 있어야 하나]
const PAGES = [['pid', '/', true], ['logic', '/logic', true], ['logic_draw', '/logic/draw', true], ['logic_test', '/logic/test', true],
  ['logic_commission', '/logic/commission', true], ['logic_signal', '/logic/signal', true], ['space', '/space', true],
  ['space3d', '/space?view=3d', true], ['dcs', '/dcs', true], ['books', '/books/', true], ['valve', '/valve/', false],
  ['plaza', '/plaza', false]];

function withEmbed(p) {
  if (!embed) return p;
  return p + (p.includes('?') ? '&' : '?') + 'embed=1&user=' + encodeURIComponent('홍길동');
}

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, locale: 'ko-KR' });
  const report = [];
  let bad = 0;
  for (const [name, p0, wantShell] of PAGES) {
    const p = withEmbed(p0);
    const page = await ctx.newPage();
    const errs = [];
    page.on('pageerror', (e) => errs.push(e.message));
    page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text().slice(0, 200)); });
    page.on('response', (r) => { if (r.status() >= 400 && !/favicon/.test(r.url())) errs.push('HTTP ' + r.status() + ' ' + r.url().replace(base, '')); });
    let status = 'ok';
    try {
      const r = await page.goto(base + p, { waitUntil: 'load', timeout: 30000 });
      status = r ? r.status() : 'noresp';
      await page.waitForTimeout(2500);
    } catch (e) { status = 'ERR ' + e.message.split('\n')[0]; }
    await page.screenshot({ path: path.join(out, name + '.png') }).catch(() => {});
    const m = await page.evaluate(() => {
      const bar = document.getElementById('pidShell');
      const se = document.scrollingElement || document.documentElement;
      return { shell: !!(bar && bar.offsetHeight), shellOn: document.body.classList.contains('pid-shell-on'),
               overflow: Math.max(0, se.scrollHeight - window.innerHeight), api: !!window.PID_SHELL };
    }).catch(() => ({}));
    const expectShell = wantShell && !embed;
    if (m.shell !== expectShell) errs.push(expectShell ? '공통 띠가 없다' : '띠가 있으면 안 되는 화면에 띠가 있다');
    if (wantShell && !m.api) errs.push('window.PID_SHELL 이 없다');
    if (errs.length || status !== 200) bad++;
    report.push({ name, path: p, status, title: await page.title().catch(() => ''), ...m, errors: errs.slice(0, 6) });
    await page.close();
  }
  console.log(JSON.stringify(report, null, 1));
  console.log(bad ? `문제 있는 화면 ${bad}개` : '모든 화면 이상 없음');
  await b.close();
  process.exit(bad ? 1 : 0);
})();
