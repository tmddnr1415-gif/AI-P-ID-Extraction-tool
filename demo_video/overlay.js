// Demo overlay: chapter cards, still shots (Ken Burns), captions, chapter bar, cursor.
// Injected into the top frame of every page the recorder opens. Designed on a
// 1920x1080 canvas and scaled to the 1600x900 viewport (recorded at DPR 1.2).
(() => {
  if (window.top !== window || window.__dv) return;
  const CSS = `
@font-face{font-family:DemoKR;font-weight:400;src:url(/__demo/f/k400.woff2) format('woff2')}
@font-face{font-family:DemoKR;font-weight:700;src:url(/__demo/f/k700.woff2) format('woff2')}
@font-face{font-family:DemoKR;font-weight:900;src:url(/__demo/f/k900.woff2) format('woff2')}
@font-face{font-family:DemoLat;font-weight:400;src:url(/__demo/f/l400.woff2) format('woff2')}
@font-face{font-family:DemoLat;font-weight:700;src:url(/__demo/f/l700.woff2) format('woff2')}
@font-face{font-family:DemoLat;font-weight:900;src:url(/__demo/f/l900.woff2) format('woff2')}
#dv-root,#dv-root *{box-sizing:border-box;margin:0;padding:0;font-family:DemoLat,DemoKR,sans-serif;letter-spacing:normal}
#dv-root{position:fixed;inset:0;z-index:2147483646;pointer-events:none;width:auto;height:auto;margin:0;border:0;padding:0;background:transparent;overflow:visible;max-width:none;max-height:none}
#dv-c{position:absolute;left:0;top:0;width:1920px;height:1080px;transform-origin:0 0}
#dv-scene{position:absolute;inset:0;opacity:0;background:#0d1230;overflow:hidden}
#dv-scene .shot{position:absolute;left:0;top:0;transform-origin:0 0}
#dv-scene .shot img{display:block}
#dv-scene .hl{position:absolute;border:solid #ffcc33;border-radius:6px;opacity:0}
#dv-root .dv-card{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 160px;color:#fff;
  background:radial-gradient(1200px 700px at 80% 20%,#2c3d8f 0%,#141b3d 55%,#0b1029 100%)}
#dv-root .dv-card .kicker{font-size:30px;letter-spacing:.3em;color:#9fb3ff;font-weight:700}
#dv-root .dv-card h1{font-size:96px;font-weight:900;line-height:1.15;margin-top:18px;color:#fff}
#dv-root .dv-card h1 em{font-style:normal;color:#ffcc33}
#dv-root .dv-card p{font-size:38px;color:#d7defb;margin-top:28px;line-height:1.5;font-weight:400}
#dv-root .dv-card .num{font-size:220px;font-weight:900;color:rgba(255,255,255,.08);position:absolute;right:140px;bottom:60px;line-height:1}
#dv-root .dv-card .mods{display:flex;gap:26px;margin-top:64px}
#dv-root .dv-card .mod{border:2px solid rgba(255,255,255,.25);border-radius:18px;padding:22px 30px;min-width:300px;background:rgba(255,255,255,.04)}
#dv-root .dv-card .mod b{display:block;font-size:40px;font-weight:900}
#dv-root .dv-card .mod span{display:block;font-size:24px;color:#b9c5f5;margin-top:6px}
#dv-root .dv-card .mod i{font-style:normal;font-size:22px;color:#ffcc33;font-weight:700;letter-spacing:.15em}
#dv-root .dv-card ul{margin-top:40px;list-style:none}
#dv-root .dv-card li{font-size:34px;color:#e6ebff;margin:10px 0;font-weight:700}
#dv-root .dv-card li::before{content:'▸ ';color:#ffcc33}
#dv-cap{position:absolute;left:50%;bottom:64px;transform:translateX(-50%);max-width:1660px;
  background:rgba(13,18,48,.92);color:#fff;border-radius:18px;padding:20px 36px 22px;
  font-size:36px;font-weight:700;line-height:1.4;box-shadow:0 12px 40px rgba(0,0,0,.35);
  display:flex;gap:22px;align-items:center;opacity:0;border:1px solid rgba(255,255,255,.14);transition:opacity .35s}
#dv-cap .tag{flex:none;background:#3563e9;color:#fff;font-size:24px;padding:6px 16px;border-radius:10px;font-weight:900;white-space:nowrap}
#dv-cap .tag.live{background:#e5484d}
#dv-cap small{display:block;font-size:26px;font-weight:400;color:#c7d0f6;margin-top:2px}
#dv-prog{position:absolute;left:0;right:0;bottom:0;height:40px;display:flex;background:rgba(10,14,36,.94);opacity:0;transition:opacity .3s}
#dv-prog div{flex:1;position:relative;color:#7f8bc0;font-size:19px;font-weight:700;display:flex;align-items:center;justify-content:center;letter-spacing:.12em;border-right:1px solid rgba(255,255,255,.08)}
#dv-prog div.on{color:#fff}
#dv-prog .bar{position:absolute;left:0;top:0;height:4px;background:#ffcc33;width:0}
#dv-hl{position:absolute;border:3px solid #ffcc33;border-radius:8px;box-shadow:0 0 0 4px rgba(255,204,51,.25),0 0 22px rgba(255,204,51,.6);opacity:0;transition:all .35s}
#dv-cur{position:absolute;left:0;top:0;width:26px;height:34px;opacity:0;transition:opacity .25s;will-change:transform;filter:drop-shadow(0 2px 3px rgba(0,0,0,.45))}
#dv-ring{position:absolute;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;border:3px solid #ffcc33;opacity:0}
#dv-ring.go{animation:dvring .5s ease-out}
@keyframes dvring{0%{opacity:1;transform:scale(.3)}100%{opacity:0;transform:scale(1.6)}}`;
  const st = document.createElement('style'); st.textContent = CSS;
  const root = document.createElement('div'); root.id = 'dv-root';
  root.innerHTML = `<div id="dv-c"><div id="dv-scene"></div><div id="dv-cap"><span class="tag"></span><span class="txt"></span></div><div id="dv-prog"></div></div>
    <div id="dv-hl"></div><div id="dv-ring"></div>
    <svg id="dv-cur" viewBox="0 0 26 34"><path d="M2 2 L2 27 L8.5 21 L13 31 L17.5 29 L13 19.5 L22 19.5 Z" fill="#fff" stroke="#111" stroke-width="2" stroke-linejoin="round"/></svg>`;
  const mount = () => { (document.head || document.documentElement).appendChild(st); document.documentElement.appendChild(root); root.popover = 'manual'; try { root.showPopover(); } catch (_) {} fit(); };
  const fit = () => { const k = innerWidth / 1920; root.querySelector('#dv-c').style.transform = `scale(${k})`; };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
  addEventListener('resize', fit);
  const $ = s => root.querySelector(s);
  const ease = x => x < 0 ? 0 : x > 1 ? 1 : x < .5 ? 2 * x * x : 1 - Math.pow(-2 * x + 2, 2) / 2;
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  let cur = null, curX = 800, curY = 450;
  const CH = ['DASHBOARD', 'PID', 'LOGIC', 'PANEL'];
  window.__dv = {
    top() { if (document.querySelector('dialog[open]')) { try { root.hidePopover(); root.showPopover(); } catch (_) {} } },
    ready: () => document.fonts.ready.then(() => !!root.isConnected),
    scene(spec) {
      const sc = $('#dv-scene'); sc.innerHTML = ''; cur = spec;
      if (!spec) { sc.style.opacity = 0; return; }
      if (spec.type === 'card') { sc.innerHTML = `<div class="dv-card">${spec.html}</div>`; }
      else {
        const sh = document.createElement('div'); sh.className = 'shot'; sh.style.width = spec.iw + 'px'; sh.style.height = spec.ih + 'px';
        sh.innerHTML = `<img src="${spec.img}" width="${spec.iw}" height="${spec.ih}">`;
        spec.hlEls = (spec.hl || []).map(h => { const d = document.createElement('div'); d.className = 'hl'; const [x, y, w, hh] = h[2];
          Object.assign(d.style, { left: x + 'px', top: y + 'px', width: w + 'px', height: hh + 'px' }); sh.appendChild(d); return d; });
        sc.appendChild(sh); spec.el = sh;
      }
      return new Promise(r => { const im = sc.querySelector('img'); if (!im || im.complete) r(); else { im.onload = r; im.onerror = r; } });
    },
    // lt = seconds into the scene, op = scene opacity
    render(lt, op) {
      const sc = $('#dv-scene'); sc.style.opacity = op; const s = cur; if (!s) return;
      if (s.type === 'card') {
        const card = sc.firstChild; card.style.transform = `scale(${1.04 - .04 * ease(clamp(lt / 1.2, 0, 1))})`;
        [...card.querySelectorAll('.mod,li')].forEach((m, i) => { const k = ease(clamp((lt - 1 - i * .3) / .6, 0, 1)); m.style.opacity = k; m.style.transform = `translateY(${(1 - k) * 24}px)`; });
        return;
      }
      const keys = s.keys; let r = keys[keys.length - 1][1];
      if (lt <= keys[0][0]) r = keys[0][1];
      else for (let i = 0; i < keys.length - 1; i++) { const [a, ra] = keys[i], [b, rb] = keys[i + 1]; if (lt <= b) { const k = ease((lt - a) / (b - a)); r = ra.map((v, j) => v + (rb[j] - v) * k); break; } }
      const [cx, cy, w] = r, k = 1920 / w;
      s.el.style.transform = `translate(${960 - cx * k}px,${540 - cy * k}px) scale(${k})`;
      (s.hl || []).forEach((h, i) => { const e = s.hlEls[i], a = clamp((lt - h[0]) / .35, 0, 1) * clamp((h[1] - lt) / .35, 0, 1);
        e.style.opacity = a; e.style.borderWidth = (5 / k) + 'px'; e.style.boxShadow = `0 0 ${18 * (1 + .25 * Math.sin(lt * 5)) / k}px ${6 / k}px rgba(255,204,51,.55)`; });
    },
    cap(tag, text, sub, live) {
      const c = $('#dv-cap'); if (!tag) { c.style.opacity = 0; return; }
      c.querySelector('.tag').textContent = tag; c.querySelector('.tag').classList.toggle('live', !!live);
      c.querySelector('.txt').innerHTML = text + (sub ? `<small>${sub}</small>` : ''); c.style.opacity = 1;
    },
    prog(idx, frac) {
      const p = $('#dv-prog');
      if (!p.children.length) CH.forEach(n => { const d = document.createElement('div'); d.innerHTML = `<span class="bar"></span>${n}`; p.appendChild(d); });
      p.style.opacity = idx < 0 ? 0 : 1;
      [...p.children].forEach((d, i) => { d.classList.toggle('on', i === idx); d.querySelector('.bar').style.width = (i < idx ? 100 : i === idx ? frac * 100 : 0) + '%'; });
    },
    hl(r) { const h = $('#dv-hl'); if (!r) { h.style.opacity = 0; return; } Object.assign(h.style, { left: r.x - 6 + 'px', top: r.y - 6 + 'px', width: r.w + 12 + 'px', height: r.h + 12 + 'px', opacity: 1 }); },
    curShow(v) { $('#dv-cur').style.opacity = v ? 1 : 0; },
    curMove(x, y, ms) { const c = $('#dv-cur'); c.style.transition = `opacity .25s, transform ${ms}ms cubic-bezier(.45,.05,.25,1)`; c.style.transform = `translate(${x}px,${y}px)`; curX = x; curY = y; },
    curAt: () => [curX, curY],
    ring() { const r = $('#dv-ring'); r.style.left = curX + 'px'; r.style.top = curY + 'px'; r.classList.remove('go'); void r.offsetWidth; r.classList.add('go'); },
  };
})();
