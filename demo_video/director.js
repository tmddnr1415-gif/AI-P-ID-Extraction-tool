// Records the demo: the real Dashboard (8080) with the P&ID / LOGIC tools (8000)
// embedded, driven by a visible cursor, plus chapter cards and stored result
// screens. Live parts are captured in real time; cards/stills frame by frame.
//   node director.js <out.mp4> [onlyChapter]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');
const OUT = process.argv[2], ONLY = process.argv[3] || '';
const DIR = __dirname, FPS = 30;
const DASH = 'http://127.0.0.1:8080/';
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ---------------- chapters (estimated lengths for the progress bar) ----------------
const CHAP = { dash: [0, 44], pid: [1, 44], logic: [2, 50], panel: [3, 54] };
let chap = null, chapT0 = 0;

(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1440, height: 810 }, deviceScaleFactor: 4 / 3 });
  await ctx.route('**/__demo/**', r => {
    const u = new URL(r.request().url()); const f = path.join(DIR, u.pathname.replace('/__demo/', ''));
    r.fulfill({ path: f, headers: { 'access-control-allow-origin': '*' } });
  });
  await ctx.addInitScript({ path: path.join(DIR, 'overlay.js') });
  const p = await ctx.newPage();
  p.on('dialog', d => d.accept());
  p.on('pageerror', e => console.log('pageerror', e.message.slice(0, 120)));

  // fresh state: logged out, no space project, no saved drawings named like ours
  await p.goto(DASH, { waitUntil: 'load' });
  await p.evaluate(() => { localStorage.clear(); });
  await p.reload({ waitUntil: 'load' });
  await p.waitForTimeout(1500);
  if (ONLY && ONLY !== 'dash') {
    const r = await (await p.request.post(DASH + 'api/auth/login', { data: { id: 'demo', password: 'demo1234!' } })).json();
    await p.evaluate(r => { localStorage.setItem('dept-auth', JSON.stringify({ token: r.token, id: 'demo', name: '홍길동' })); localStorage.setItem('dept-todo-hide', new Date().toISOString().slice(0, 10) + '|홍길동'); }, r);
    await p.reload({ waitUntil: 'load' }); await p.waitForTimeout(2500);
  }
  await p.evaluate(() => window.__dv.ready());

  // ---------------- recorder ----------------
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS), OUT], { stdio: ['pipe', 'inherit', 'inherit'] });
  const write = buf => new Promise(r => ff.stdin.write(buf) ? r() : ff.stdin.once('drain', r));
  let frames = 0;
  const T = () => frames / FPS;
  const capLog = [];
  const dv = (fn, ...a) => (fn === 'cap' && capLog.push([T(), a[0] || null, a[1] || '', a[2] || '']), _dv(fn, ...a));
  const _dv = (fn, ...a) => p.evaluate(([fn, a]) => window.__dv[fn](...a), [fn, a]).catch(e => console.log('dv', fn, e.message.slice(0, 100)));
  async function snap() {
    await p.evaluate(([c, f]) => { window.__dv.top(); window.__dv.prog(c, f); },
      [chap ? CHAP[chap][0] : -1, chap ? Math.min(1, (T() - chapT0) / CHAP[chap][1]) : 0]).catch(() => {});
    return p.screenshot({ type: 'jpeg', quality: 92 });
  }
  const startChap = k => { chap = k; chapT0 = T(); };

  // deterministic segment: scene spec + captions [[t, tag, text, sub]]
  async function still(dur, spec, caps = [], { fadeIn = .45, fadeOut = .45 } = {}) {
    await p.evaluate(s => window.__dv.scene(s), spec);
    let ci = -1;
    const n = Math.round(dur * FPS);
    for (let i = 0; i < n; i++) {
      const lt = i / FPS;
      const op = Math.min(fadeIn ? Math.min(1, lt / fadeIn) : 1, fadeOut ? Math.min(1, (dur - lt) / fadeOut) : 1);
      let k = -1; caps.forEach((c, j) => { if (lt >= c[0]) k = j; });
      if (k !== ci) { ci = k; if (k >= 0) await dv('cap', caps[k][1], caps[k][2], caps[k][3]); }
      if (caps.length && dur - lt < .4 && ci >= 0) { await dv('cap', null); ci = -2; }
      await p.evaluate(([lt, op]) => window.__dv.render(lt, op), [lt, op]);
      await write(await snap()); frames++;
    }
    await p.evaluate(() => window.__dv.scene(null));
  }
  // real-time segment: capture continuously while fn drives the page
  async function live(fn) {
    let run = true; const t0 = Date.now(), f0 = frames;
    const loop = (async () => {
      while (run) {
        const buf = await snap();
        const target = f0 + Math.floor((Date.now() - t0) / 1000 * FPS) + 1;
        const k = Math.max(1, target - frames);
        for (let j = 0; j < k; j++) await write(buf);
        frames += k;
        const wait = t0 + (frames - f0) * 1000 / FPS - Date.now(); if (wait > 0) await sleep(wait);
      }
    })();
    try { await fn(); } catch (e) { console.log('live error', e.message.slice(0, 300)); }
    run = false; await loop;
  }

  // ---------------- cursor helpers ----------------
  async function boxOf(loc) { await loc.scrollIntoViewIfNeeded({ timeout: 4000 }).catch(() => {}); return loc.boundingBox({ timeout: 4000 }); }
  async function moveTo(loc, fx = .5, fy = .5) {
    const bb = typeof loc.x === 'number' ? loc : await boxOf(loc);
    if (!bb) { console.log('no box'); return null; }
    const x = bb.x + bb.width * fx, y = bb.y + bb.height * fy;
    const [cx, cy] = await p.evaluate(() => window.__dv.curAt());
    const ms = Math.round(Math.max(350, Math.min(900, Math.hypot(x - cx, y - cy) * 1.1)));
    await dv('curMove', x, y, ms); await p.mouse.move(x, y, { steps: 6 }); await sleep(Math.max(0, ms - 60));
    return { x, y };
  }
  async function click(loc, fx, fy) {
    const pt = await moveTo(loc, fx, fy); if (!pt) return;
    await dv('ring'); await p.mouse.click(pt.x, pt.y); await sleep(300);
  }
  async function type(loc, text, delay = 75) { await click(loc); await loc.pressSequentially(text, { delay }); await sleep(200); }
  async function wheel(dy, steps = 12) { for (let i = 0; i < steps; i++) { await p.mouse.wheel(0, dy / steps); await sleep(35); } }
  const cap = (tag, text, sub, l = true) => dv('cap', tag, text, sub, l);
  const KEYS = { '수행': 'perform', 'P&ID 분석': 'pid', 'LOGIC 분석': 'logic', 'LOGIC 작성': 'logicdraw', 'ROOM SIZE 계산': 'space' };
  const side = t => p.locator(`#menu button.mi[data-k="${KEYS[t]}"]`).first();
  const menu = t => p.locator(`text=${t}`).first();
  const frame = re => p.frames().find(f => re.test(f.url()));

  const tbMin = () => p.evaluate(() => { const b = document.querySelector('#taskbar [data-tb="min"]'); if (b) b.click(); }).catch(() => {});
  const card = (html) => ({ type: 'card', html });
  const img = (n, iw, ih, keys, hl) => ({ type: 'shot', img: '/__demo/img/' + n, iw, ih, keys, hl });

  // =====================================================================
  // INTRO
  if (!ONLY) await still(6, card(`
   <div class="kicker">계장ENG그룹 · 시연</div>
   <h1>하나의 <em>Dashboard</em> 에서<br>도면 · 로직 · 판넬까지</h1>
   <p>주간업무 현황판 안에 P&amp;ID 분석 · LOGIC 분석 · 판넬 공간확보 도구가 함께 들어 있습니다.</p>
   <div class="mods">
     <div class="mod"><i>01</i><b>Dashboard</b><span>주간업무 · 현황판</span></div>
     <div class="mod"><i>02</i><b>PID</b><span>계기·밸브 리스트 추출</span></div>
     <div class="mod"><i>03</i><b>Logic</b><span>로직 분석 · 작성</span></div>
     <div class="mod"><i>04</i><b>Panel</b><span>ROOM SIZE 계산</span></div>
   </div>`), [], { fadeIn: 0 });

  // =====================================================================
  // CH1 DASHBOARD
  if (!ONLY || ONLY === 'dash') {
    startChap('dash');
    await still(2.6, card(`<div class="kicker">CHAPTER 01</div><h1>Dashboard</h1><p>계장ENG그룹 주간업무 · 현황판</p><div class="num">01</div>`));
    await live(async () => {
      await dv('curMove', 800, 600, 10); await dv('curShow', true);
      await cap('로그인', '부서원 계정으로 로그인 — 모두 같은 서버의 데이터를 봅니다');
      await type(p.locator('#aId'), 'demo');
      await click(p.locator('button:has-text("다음")'));
      await sleep(500);
      await type(p.locator('#aPw'), 'demo1234!', 55);
      await click(p.locator('button:has-text("로그인")').first());
      await sleep(1800);
      await cap('내 업무', '로그인하면 이번 주 내 업무부터 — 작성하면 자동으로 완료 처리');
      await sleep(2600);
      await click(p.locator('button:has-text("닫고 툴바로 보기")'));
      await sleep(600);
      await cap('현황판', '수행 · 입찰 PJT 수, 금주 업데이트, 사업군별 · 담당자별 PJT 를 한 화면에');
      await moveTo(p.locator('text=수행 PJT 수').first());
      await sleep(1500);
      await moveTo({ x: 700, y: 560, width: 0, height: 0 }); await sleep(1300);
      await wheel(520); await sleep(1800);
      await wheel(-520); await sleep(500);
      await click(side('수행'));
      await sleep(900);
      await cap('수행 PJT 보드', '시트마다 보드 + 엑셀 형태 그대로 편집하는 표 — 수정 이력 · 금주 마감까지');
      await sleep(1800);
      await moveTo({ x: 1000, y: 470, width: 0, height: 0 }); await sleep(600);
      await wheel(640); await sleep(2400);
      await wheel(-640); await sleep(400);
      // the analysis tools sit in the same menu
      const boxes = [];
      for (const t of ['P&ID 분석', 'LOGIC 분석', 'LOGIC 작성', 'ROOM SIZE 계산']) { const bb = await side(t).boundingBox().catch(() => null); if (bb) boxes.push(bb); }
      if (boxes.length) {
        const x = Math.min(...boxes.map(b => b.x)) - 8, y = Math.min(...boxes.map(b => b.y)) - 6;
        const r = { x, y, w: 224, h: Math.max(...boxes.map(b => b.y + b.height)) - y + 6 };
        await moveTo({ x: r.x + 120, y: r.y + r.h / 2, width: 0, height: 0 });
        await dv('hl', r);
      }
      await cap('분석 도구', 'P&ID 분석 · LOGIC 분석 · LOGIC 작성 · ROOM SIZE 계산 — 같은 메뉴에서 바로 엽니다');
      await sleep(3200); await dv('hl', null); await cap(null);
      await sleep(300);
    });
  }

  // =====================================================================
  // CH2 PID
  if (!ONLY || ONLY === 'pid') {
    startChap('pid');
    await dv('curShow', false); await tbMin();
    // tidy: minimise the floating '내 업무' toolbar while the card is up
    await still(2.6, card(`<div class="kicker">CHAPTER 02</div><h1>PID</h1><p>P&amp;ID 도면 → 발주처 양식 계기·밸브 리스트</p><div class="num">02</div>`));
    await live(async () => {
      await dv('curShow', true);
      await click(side('P&ID 분석'));
      await sleep(2200);
      await cap('P&ID 분석', '대시보드 안에서 P&ID 추출 도구가 그대로 열립니다', '프로젝트를 고르고 PDF · DXF 를 놓으면 분석 — 도면 58장 약 5분');
      const f = frame(/:8000\/\?embed/);
      if (f) {
        await moveTo(f.locator('#home-new, button:has-text("새 분석")').first()); await sleep(900);
        await moveTo(f.locator('text=여기에 PDF').first()); await sleep(1600);
        await moveTo(f.locator('text=저장된 프로젝트').first()); await sleep(1200);
      } else await sleep(3500);
      await cap(null); await dv('curShow', false); await sleep(300);
    });
    const S1 = '실제 분석 화면 — QFE 프로젝트 (93장)';
    await still(15, img('result.png', 1920, 1080,
      [[0, [960, 540, 1920]], [4.5, [960, 540, 1920]], [6.5, [660, 500, 1100]], [10, [660, 500, 1100]], [12, [1430, 300, 1000]], [15, [1430, 300, 1000]]],
      [[0.8, 4.4, [10, 180, 192, 215]], [6.9, 9.9, [240, 225, 792, 552]], [12.4, 14.7, [1078, 175, 700, 62]]]),
      [[0, '결과 화면', '왼쪽 도면 · 오른쪽 리스트 — 1,991행을 Field · BFV · MOV · Pneumatic 으로', S1],
       [6.5, '도면 오버레이', '검출한 계기 버블과 공급 범위(SCT · VENDOR)를 도면 위에 색으로', S1],
       [12, '검토 항목', '스코프 판정 · 수량 · Description — 사람이 확인할 곳만 모아서', S1]]);
    await still(7.5, img('evidence.png', 1920, 1080, [[0, [1430, 795, 1000]], [7.5, [1430, 795, 1000]]], [[0.5, 7.2, [1074, 720, 834, 30]], [0.5, 7.2, [1074, 980, 834, 80]]]),
      [[0, '판정 근거', '행을 누르면 근거가 바로 — 무엇을 보고 그렇게 읽었는지 행마다 남습니다', '검출에 LLM 을 쓰지 않고, 그 도면의 범례 · NOTES · 타이틀블록에서 규칙을 읽습니다']]);
    await still(9, img('sbs.png', 1920, 1080, [[0, [960, 540, 1920]], [3.5, [960, 540, 1920]], [5.5, [1430, 795, 1000]], [10, [1430, 795, 1000]]],
      [[0.6, 3.4, [1190, 140, 150, 26]], [5.8, 9.7, [1078, 748, 560, 22]]]),
      [[0, '개정 대조', 'Rev.A ↔ Rev.B 나란히 — 확대 · 스크롤이 함께 움직입니다', S1],
       [5.5, '변경 내역', '이 장 추가 4 · 삭제 후보 34 — 확인이 끝나면 발주처 양식 Excel 로 출력', S1]]);
  }

  // =====================================================================
  // CH3 LOGIC
  if (!ONLY || ONLY === 'logic') {
    startChap('logic'); await tbMin();
    await still(2.6, card(`<div class="kicker">CHAPTER 03</div><h1>Logic</h1><p>Logic Diagram 분석 · 시뮬레이션 · 작성</p><div class="num">03</div>`));
    await live(async () => {
      await dv('curShow', true);
      await click(side('LOGIC 분석'));
      await sleep(2200);
      await cap('LOGIC 분석', 'Logic Diagram · Loop · System Description · IO List 를 넣고 분석', 'Logic 50장 약 40초~1분 — 끝나면 From-To 점검 보고부터');
      const f = frame(/:8000\/logic(\?|$)/);
      if (f) { await moveTo(f.locator('text=Logic Diagram').first()); await sleep(1200); await moveTo(f.locator('text=Signal Processing').first().or(f.locator('text=학습 사전').first())); await sleep(1500); }
      else await sleep(3000);
      await cap(null); await dv('curShow', false); await sleep(300);
    });
    const S2 = '실제 분석 화면 — HRSG Logic 50장';
    await still(11, img('logic_and.png', 1600, 1000,
      [[0, [800, 520, 1640]], [3, [800, 520, 1640]], [4.5, [330, 230, 800]], [6.5, [330, 230, 800]], [7.8, [1100, 420, 1000]], [11, [1100, 420, 1000]]],
      [[4.7, 6.5, [10, 58, 210, 105]], [8, 10.8, [1272, 340, 316, 130]], [8, 10.8, [1272, 620, 316, 140]]]),
      [[0, '분석 결과', '시트 · FROM/TO · 게이트를 읽어 시트 사이 신호를 잇습니다', S2],
       [4.5, '식별률', '시트 이름 100% · FROM/TO 100% · 시트 사이 연결 99.5% · 게이트 99.2%', S2],
       [7.8, '게이트 근거', '게이트를 누르면 종류 · 동작(범례) · S-R 래치 진리표까지', S2]]);
    await still(8, img('logic_trace.png', 1700, 1000, [[0, [850, 500, 1720]], [2, [850, 500, 1720]], [4, [1200, 500, 1000]], [8, [1200, 500, 1000]]],
      [[0.5, 3, [630, 55, 170, 30]], [4.2, 7.8, [1210, 700, 456, 195]]]),
      [[0, '동작 시뮬레이션', '최종 명령에서 최초 입력까지 게이트를 단계별로 거슬러 올라갑니다', '실제 분석 화면 — 19VA 827장']]);
    await live(async () => {
      await dv('curShow', true);
      await click(side('LOGIC 작성'));
      await sleep(1600);
      await click(p.locator('#sideHide')); await sleep(700);
      await cap('LOGIC 작성', '분석한 로직과 같은 양식으로 새 시트를 그립니다');
      const f = frame(/:8000\/logic\/draw/);
      if (!f) { await sleep(3000); return; }
      await click(f.locator('#new'));
      await sleep(500);
      await type(f.locator('#m-name'), '급수펌프 A 기동', 60);
      await type(f.locator('#m-sheet'), 'G-301', 60);
      await type(f.locator('#m-dtitle'), 'FW PUMP A START', 50);
      await click(f.locator('#m-ok'));
      await sleep(1500);
      await cap('기호 배치', '팔레트에서 누르면 LOGIC 영역에 놓이고, 끌어서 자리를 잡습니다', 'TAG NO. 자동완성 · 선 긋기 경로 추천 · 되읽기 검증 · PDF / DXF');
      const names = ['AND', 'OR', 'NOT', '메모리 S-R'];
      for (const t of names) { await click(f.locator(`#palette button:has(span:text-is("${t}"))`)); await sleep(250); }
      const blk = f.locator('#svg g.blk');
      let bb = await blk.first().boundingBox();
      if (bb) {
        let topY = bb.y; for (let j = 0, n = await blk.count(); j < n; j++) { const b2 = await blk.nth(j).boundingBox(); if (b2) topY = Math.min(topY, b2.y); }
        await moveTo({ x: bb.x + bb.width / 2, y: topY - 4, width: 0, height: 0 });
        await cap('기호 배치', '팔레트에서 누르면 놓이고, 휠로 확대해 끌어서 자리를 잡습니다', '자석 격자 · 정렬 안내선 · TAG NO. 자동완성 · 선 경로 추천');
        for (let i = 0; i < 8; i++) { await p.keyboard.down('Control'); await p.mouse.wheel(0, -120); await p.keyboard.up('Control'); await sleep(110); }
        await sleep(500);
        const fb = await p.locator('iframe').first().boundingBox();
        const sb = await f.locator('#svg').boundingBox();
        const x0 = Math.max(fb.x, sb.x), y0 = Math.max(fb.y, sb.y), x1 = Math.min(fb.x + fb.width, sb.x + sb.width), y1 = Math.min(fb.y + fb.height, sb.y + sb.height);
        const cx = (x0 + x1) / 2, cy = y0 + (y1 - y0) * .42;
        const tgt = [[cx - 230, cy - 90], [cx - 230, cy + 80], [cx - 20, cy - 5], [cx + 200, cy - 5]];
        const stackX = (await blk.first().boundingBox()).x;
        for (let i = 0; i < 4; i++) {
          await f.locator('body').press('Escape').catch(() => {});
          const all = [];
          for (let j = 0, n = await blk.count(); j < n; j++) { const b2 = await blk.nth(j).boundingBox(); if (b2 && Math.abs(b2.x - stackX) < 30) all.push(b2); }
          if (!all.length) break;
          all.sort((a, b) => b.y - a.y); bb = all[0];
          const sx = bb.x + bb.width / 2, sy = bb.y + bb.height / 2, [tx, ty] = tgt[i];
          await moveTo({ x: sx, y: sy, width: 0, height: 0 });
          await p.mouse.down();
          await dv('curMove', tx, ty, 700);
          for (let k = 1; k <= 16; k++) { await p.mouse.move(sx + (tx - sx) * k / 16, sy + (ty - sy) * k / 16); await sleep(40); }
          await p.mouse.up(); await sleep(350);
        }
        await cap('저장 · 검증', '저장하면 PDF 로 다시 읽어 같은 블록 · 선 · 행이 읽히는지 되읽기 검증', '분석한 시트를 같은 양식으로 가져와 고치기도 합니다 (⇩ 분석 시트에서)');
        await moveTo(f.locator('#verify'));
      }
      await sleep(1800);
      await cap(null); await dv('curShow', false); await sleep(300);
    });
    await still(6.5, img('draw_sim.png', 1700, 1000, [[0, [850, 500, 1720]], [2.5, [850, 500, 1720]], [4.5, [900, 440, 1050]], [8, [900, 440, 1050]]],
      [[0.5, 2.6, [1050, 4, 420, 30]], [4.7, 7.8, [700, 195, 320, 460]]]),
      [[0, '작성한 로직 시뮬레이션', '완성한 시트는 그 자리에서 1/0 을 눌러 동작 확인 — 활성 신호가 파랗게', '실제 작성 화면 — FG_G-201']]);
  }

  // =====================================================================
  // CH4 PANEL
  if (!ONLY || ONLY === 'panel') {
    startChap('panel'); await tbMin();
    await still(2.6, card(`<div class="kicker">CHAPTER 04</div><h1>Panel</h1><p>ROOM SIZE 계산 — 판넬 공간확보</p><div class="num">04</div>`));
    await live(async () => {
      await dv('curShow', true);
      if (await p.evaluate(() => document.body.classList.contains('nav-closed'))) { await click(p.locator('#burger')); await sleep(600); }
      await click(side('ROOM SIZE 계산'));
      await sleep(1800);
      await click(p.locator('#sideHide'));
      await sleep(800);
      await cap('ROOM SIZE 계산', '계장 판넬을 배치해 필요 면적 · 권장 실 크기를 건축에 전달합니다');
      const f = frame(/apps\/space/);
      if (!f) { await sleep(3000); return; }
      await click(f.locator('#hmNewBtn'));
      await type(f.locator('#hmNewName'), 'DEMO 복합화력 #1', 60);
      await click(f.locator('#hmCreate'));
      await sleep(600);
      await type(f.locator('#hmRoom'), 'CCR', 80);
      await type(f.locator('#hmRev'), 'A', 80);
      await click(f.locator('li[data-st=sample]'));
      await sleep(400);
      await click(f.locator('#hmGo'));
      await sleep(1800);
      await cap('예시 배치', 'System · Marshalling · Network · PD · UPS 판넬 23대가 21 × 18 m 실 안에');
      await sleep(2600);
      // add three server racks
      await cap('판넬 추가', 'Type 을 고르고 도면을 누르면 그 자리에 — 연속 3 EA');
      const q = f.locator('#qty'); await click(q); await q.fill(''); await q.pressSequentially('3', { delay: 100 });
      await click(f.locator('text=Network / Server Rack').first());
      await sleep(400);
      const cv = await boxOf(f.locator('#cv'));
      if (cv) { await click(cv, .52, .62); await sleep(900); }
      await f.locator('body').press('Escape').catch(() => {});
      await sleep(1200);
      await cap('검토 결과 (자동 계산)', '판넬 수 · 바닥면적 · 필요 영역 · 권장 실 크기 — 배치가 바뀌면 바로 다시 계산');
      const res = f.locator('text=검토 결과').first();
      await res.scrollIntoViewIfNeeded().catch(() => {});
      await sleep(400);
      const rb = await res.boundingBox().catch(() => null);
      if (rb) { await dv('hl', { x: rb.x - 6, y: rb.y - 4, w: 300, h: 250 }); await moveTo({ x: rb.x + 120, y: rb.y + 70, width: 0, height: 0 }); }
      await sleep(3000); await dv('hl', null);
      await cap('유지보수 공간', '판넬 앞 · 뒤 유지보수 공간을 켜고 끄며 간섭을 확인');
      const mc = f.locator('#vClr'); await click(mc); await sleep(1300); await click(mc); await sleep(900);
      await cap('실 치수', '실 크기를 바꾸면 권장 크기 수용 여부를 바로 판정');
      const rw = f.locator('#rW'); await click(rw); await rw.fill(''); await rw.pressSequentially('16000', { delay: 110 }); await rw.press('Tab');
      await sleep(1600);
      await click(f.locator('#bFit')).catch(() => {}); await sleep(1200);
      await cap('서버에 저장', '프로젝트별 · 날짜별로 서버에 저장 — 부서원 모두 저장 이력과 노트를 봅니다');
      await click(f.locator('#bSrvSave')); await sleep(900);
      await type(f.locator('#hMemo'), '건축 1차 전달본', 70);
      await click(f.locator('#hSave')); await sleep(2000);
      await f.locator('body').press('Escape').catch(() => {}); await sleep(700);
      await cap('출력', '건축 전달 요약(TXT) · DXF · 판넬 List(CSV) · 배치안(JSON) 으로 바로 내보내기');
      await f.locator('#bReq').scrollIntoViewIfNeeded().catch(() => {}); await sleep(400);
      const ob = await f.locator('#bReq').boundingBox().catch(() => null);
      if (ob) { await dv('hl', { x: ob.x - 4, y: ob.y - 4, w: 300, h: 150 }); await moveTo(ob); }
      await sleep(2800); await dv('hl', null); await cap(null); await dv('curShow', false); await sleep(300);
    });
  }

  // =====================================================================
  if (!ONLY) {
    chap = null;
    await still(7, card(`
     <div class="kicker">계장ENG그룹 Dashboard</div>
     <h1>하나의 화면에서<br><em>업무 · 도면 · 로직 · 판넬</em></h1>
     <p>근거는 도면에 · 판단은 사람에게 — 모든 출력은 사람이 검토합니다.</p>
     <div class="mods">
       <div class="mod"><i>01</i><b>Dashboard</b><span>주간업무 · 현황판</span></div>
       <div class="mod"><i>02</i><b>PID</b><span>리스트 · 근거 · Excel</span></div>
       <div class="mod"><i>03</i><b>Logic</b><span>분석 · 시뮬레이션 · 작성</span></div>
       <div class="mod"><i>04</i><b>Panel</b><span>ROOM SIZE · 건축 전달</span></div>
     </div>`), [], { fadeOut: 0 });
  }
  capLog.push([T(), null, '', '']);
  fs.writeFileSync(OUT.replace(/\.mp4$/, '.caps.json'), JSON.stringify(capLog));
  ff.stdin.end(); await new Promise(r => ff.on('close', r));
  await b.close();
  console.log('done', OUT, (frames / FPS).toFixed(1) + 's');
})();
