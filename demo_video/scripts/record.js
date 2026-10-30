// Renders player.html frame by frame (30 fps) and pipes JPEG frames into ffmpeg.
// Live segments (iframes of the running app) are paced to real time so the app's
// own animation plays at normal speed.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const [, , html, out, fromArg, toArg] = process.argv;
const FPS = 30;

(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + html);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(8000); // let the live pages load and their sims warm up
  const scenes = await p.evaluate(() => window.SCENES);
  const END = fromArg ? +toArg : await p.evaluate(() => window.END);
  const START = fromArg ? +fromArg : 0;
  const frame = re => p.frames().find(f => re.test(f.url()));
  const sig = frame(/logic\/signal/), hmi = frame(/\/hmi/);

  const setRange = (f, idx, v) => f.evaluate(([idx, v]) => {
    const r = document.querySelectorAll('input[type=range]')[idx]; if (!r) return;
    r.value = v; r.dispatchEvent(new Event('input', { bubbles: true }));
  }, [idx, v]).catch(() => {});
  const click = (f, sel) => f.evaluate(sel => { const e = [...document.querySelectorAll(sel.css)].find(e => !sel.text || e.textContent.includes(sel.text)); if (e) e.click(); else console.log('missing', sel); window.scrollTo(0, 0); document.scrollingElement.scrollTop = 0; }, sel).catch(e => console.error('click', e.message));
  const done = new Set();
  const once = (k, fn) => { if (!done.has(k)) { done.add(k); fn(); } };

  // per-frame live actions; lt = seconds into the scene
  async function live(id, lt) {
    if (id === 'sig') {
      if (lt >= 0.6 && lt <= 4.6) await setRange(sig, 0, Math.round(25 + (lt - 0.6) / 4 * 55));
      if (lt >= 4.8 && lt < 5.2) once('sig-in2', () => {});
      if (lt >= 7) once('sig-ll', () => click(sig, { css: '#tabs button', text: 'LEAD/LAG' }));
      if (lt >= 7.4) once('sig-scroll', () => sig.evaluate(() => { document.scrollingElement.scrollTo({ top: 330, behavior: 'smooth' }); }).catch(() => {}));
      if (lt >= 8.5 && lt <= 12.5) await setRange(sig, 0, 10 + (lt - 8.5) / 4 * 60);
    }
    if (lt < 0.1) once('top-' + id, () => (id === 'sig' ? sig : hmi).evaluate(() => { document.scrollingElement.scrollTop = 0; }).catch(() => {}));
    if (id === 'hmi') {
      if (lt >= 6.5) once('hmi-man', () => click(hmi, { css: 'button.mode[data-mode=MAN]' }));
      if (lt >= 9) once('hmi-auto', () => click(hmi, { css: 'button.mode[data-mode=AUTO]' }));
      if (lt >= 11.5) once('hmi-lib', () => click(hmi, { css: 'button.tab[data-tab=library]' }));
    }
  }

  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const write = buf => new Promise(r => ff.stdin.write(buf) ? r() : ff.stdin.once('drain', r));

  const n0 = Math.round(START * FPS), n1 = Math.round(END * FPS);
  let liveAnchor = null; // {frame, ms} – real-time anchor while inside a live scene
  const t0 = Date.now();
  for (let i = n0; i < n1;) {
    const t = i / FPS;
    const sc = scenes.find(s => s.type === 'live' && t >= s.t0 && t < s.t1);
    await p.evaluate(t => render(t), t);
    if (sc) await live(sc.id, t - sc.t0);
    const buf = await p.screenshot({ type: 'jpeg', quality: 92 });
    if (sc) {
      if (!liveAnchor || liveAnchor.id !== sc.id) liveAnchor = { id: sc.id, frame: i, ms: Date.now() };
      // how many output frames does this screenshot cover in real time?
      const target = liveAnchor.frame + Math.floor((Date.now() - liveAnchor.ms) / 1000 * FPS) + 1;
      const k = Math.max(1, Math.min(target - i, n1 - i));
      for (let j = 0; j < k; j++) await write(buf);
      if (k === 1) { const wait = liveAnchor.ms + (i + 1 - liveAnchor.frame) * 1000 / FPS - Date.now(); if (wait > 0) await p.waitForTimeout(wait); }
      i += k;
    } else { liveAnchor = null; await write(buf); i++; }
    if (i % 300 < 1) console.log(`t=${(i / FPS).toFixed(1)}s  elapsed ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await b.close();
  console.log('done', out);
})();
