/* XGrid — a light spreadsheet grid (valve50, user 2026-11-27: '모든 셀이 살아 있어야 하고 매우 가볍게 움직여야 한다').
 *
 *   const g = XGrid(host, { cols, rows, freeze, rowH, maxH, onAction });
 *   cols : [{ label, w }]                       rows : [{ cls, cells: [{ v, h, c, t }] }]
 *          v = text (copied · shown) · h = HTML instead of v (a link, a select) · c = cell class · t = the formula-bar text
 *   g.setRows(rows) · g.setCols(cols, rows) · g.destroy()
 *
 * Every cell lives: click selects (green frame), drag / Shift+click selects a range, arrows · Tab · Enter · PgUp/PgDn ·
 * Home/End · Ctrl+Home/End move, Ctrl+A selects all, Ctrl+C copies the range as tab-separated text (paste into Excel),
 * a column letter or a row number selects the whole column or row, the header edge resizes a column, and the name box +
 * formula bar above show the address and the whole value.  Light: only the rows on screen are drawn (fixed row height),
 * one listener per grid, a scroll redraws at most once per frame, a filter replaces the rows without a page redraw. */
(() => {
'use strict';
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const letter = j => { let x = j + 1, t = ''; while (x) { x--; t = String.fromCharCode(65 + x % 26) + t; x = Math.floor(x / 26); } return t; };
const GUT = 40;                                                // row-number column

function XGrid(host, opt) {
  // valve54 (user 2026-11-27: '열 고정 기능과 고정된 열을 기준으로 좌우 이동'): the viewer's own freeze, remembered per grid
  const FK = opt.key ? `xgrid.freeze.${opt.key}` : '';
  const saved = (() => { try { const v = FK && localStorage.getItem(FK); return v == null || v === '' ? null : +v; } catch (_) { return null; } })();
  const G = { cols: opt.cols, rows: opt.rows || [], freeze: Math.min(saved ?? opt.freeze ?? 0, opt.cols.length), rowH: opt.rowH || 21, sel: null, act: null, drag: false, raf: 0, win: [-1, -1] };
  host.classList.add('xgw');
  host.innerHTML = `<div class="xgbar"><input class="xgname" readonly value=""><span class="xgfxi">fx</span><div class="xgfx"></div>
      <span class="xgnav"><span class="xgfzt">열 고정</span><select class="xgfreeze" title="이 열까지 왼쪽에 고정 — 나머지 열이 그 오른쪽에서 좌우로 움직입니다 (Excel 의 틀 고정)"></select>
        <button class="xgfzb" title="고른 셀의 열까지 고정 (다시 누르면 해제)">❄</button><button class="xgl1" title="왼쪽으로 한 화면 (Alt+PgUp · Shift+휠)">◀</button><select class="xgjump" title="열로 가기"></select><button class="xgr1" title="오른쪽으로 한 화면 (Alt+PgDn · Shift+휠)">▶</button></span></div>
    <div class="xgs" tabindex="0"><table class="xgt"><colgroup></colgroup><thead></thead><tbody></tbody></table></div>`;
  const sc = host.querySelector('.xgs'), tb = host.querySelector('tbody'), th = host.querySelector('thead'), cg = host.querySelector('colgroup');
  const nameBox = host.querySelector('.xgname'), fx = host.querySelector('.xgfx');

  const lefts = () => { const L = [GUT]; for (let j = 0; j < G.cols.length; j++) L.push(L[j] + (G.cols[j].w || 80)); return L; };
  function size() {
    const H = 2 * 22 + G.rows.length * G.rowH + 18;
    sc.style.height = Math.max(120, Math.min(opt.maxH || (innerHeight - sc.getBoundingClientRect().top - 40), H)) + 'px';
  }
  function head() {
    G.L = lefts();
    cg.innerHTML = `<col style="width:${GUT}px">` + G.cols.map(c => `<col style="width:${c.w || 80}px">`).join('');
    sc.querySelector('table').style.width = G.L[G.cols.length] + 'px';
    const fz = j => j < G.freeze ? ` xfz${j === G.freeze - 1 ? ' xfzl' : ''}" style="left:${G.L[j]}px` : '';
    th.innerHTML = `<tr class="xgl"><th class="xgc xgcorner" title="모두 고르기 (Ctrl+A)"></th>${G.cols.map((c, j) => `<th class="xgc${fz(j)}" data-col="${j}">${letter(j)}</th>`).join('')}</tr>
      <tr class="xgh"><th class="xgc xgcorner"></th>${G.cols.map((c, j) => `<th class="xgh1${fz(j)}" data-col="${j}" title="${esc(c.label)}">${esc(c.label)}<i class="xrz" data-rz="${j}"></i></th>`).join('')}</tr>`;
  }
  function inSel(r, j) { const s = G.sel; return s && r >= Math.min(s.r0, s.r1) && r <= Math.max(s.r0, s.r1) && j >= Math.min(s.c0, s.c1) && j <= Math.max(s.c0, s.c1); }
  function draw(force) {
    const vh = sc.clientHeight, top = sc.scrollTop, H = G.rowH, n = G.rows.length, m = G.cols.length;
    const va = Math.floor(top / H), vb = Math.min(n, Math.ceil((top + vh) / H));
    // columns on screen (the frozen ones always): side scrolling is virtual too
    const x0 = sc.scrollLeft + (G.L[G.freeze] - GUT), x1 = sc.scrollLeft + sc.clientWidth;
    let ca = G.freeze; while (ca < m && G.L[ca + 1] - GUT <= x0) ca++;
    let cb = ca; while (cb < m && G.L[cb] - GUT < x1) cb++;
    // a buffer around the view: scrolling inside it draws nothing — a redraw only when the view nears its edge
    const W = G.win;
    if (!force && W[0] >= 0 && (va - W[0] >= 4 || W[0] === 0) && (W[1] - vb >= 4 || W[1] === n)
        && (ca - W[2] >= 1 || W[2] === G.freeze) && (W[3] - cb >= 1 || W[3] === m)) return;
    const a = Math.max(0, va - 14), b = Math.min(n, vb + 14), c0 = Math.max(G.freeze, ca - 6), c1 = Math.min(m, cb + 6);
    G.win = [a, b, c0, c1];
    const s = G.sel, rs = s ? Math.min(s.r0, s.r1) : -1, re = s ? Math.max(s.r0, s.r1) : -1, cs = s ? Math.min(s.c0, s.c1) : -1, ce = s ? Math.max(s.c0, s.c1) : -1;
    const ac = G.act, idx = [];
    for (let j = 0; j < G.freeze; j++) idx.push(j);
    for (let j = c0; j < c1; j++) idx.push(j);
    const pre = c0 > G.freeze ? `<td class="xgh0" colspan="${c0 - G.freeze}"></td>` : '', post = c1 < m ? `<td class="xgh0" colspan="${m - c1}"></td>` : '';
    const fzs = G.cols.map((_, j) => j < G.freeze ? ` xfz${j === G.freeze - 1 ? ' xfzl' : ''}" style="left:${G.L[j]}px` : '');
    const out = [];
    if (a) out.push(`<tr class="xgsp" style="height:${a * H}px"><td colspan="${m + 1}"></td></tr>`);
    for (let r = a; r < b; r++) {
      const R = G.rows[r], cells = R.cells, on = r >= rs && r <= re;
      let h = `<tr class="${R.cls || ''}" data-r="${r}"><th class="xgn${on ? ' xghl' : ''}">${r + 1}</th>`;
      for (let x = 0; x < idx.length; x++) {
        const j = idx[x];
        if (x === G.freeze) h += pre;
        const C = cells[j] || {};
        h += `<td data-c="${j}" class="${C.c || ''}${on && j >= cs && j <= ce ? ' xsel' : ''}${ac && ac.r === r && ac.c === j ? ' xact' : ''}${fzs[j]}">${C.h ?? esc(C.v)}</td>`;
      }
      if (idx.length === G.freeze) h += pre;
      out.push(h + post + '</tr>');
    }
    if (b < n) out.push(`<tr class="xgsp" style="height:${(n - b) * H}px"><td colspan="${m + 1}"></td></tr>`);
    tb.innerHTML = out.join('');
    if (G.hl !== `${cs},${ce}`) { G.hl = `${cs},${ce}`; th.querySelectorAll('[data-col]').forEach(e => e.classList.toggle('xghl', s ? +e.dataset.col >= cs && +e.dataset.col <= ce : false)); }
  }
  const paint = () => { if (!G.raf) G.raf = requestAnimationFrame(() => { G.raf = 0; draw(); }); };
  function status() {
    if (!G.act) { nameBox.value = ''; fx.textContent = ''; return; }
    const { r, c } = G.act, C = (G.rows[r]?.cells || [])[c] || {}, s = G.sel;
    const w = s ? Math.abs(s.c1 - s.c0) + 1 : 1, hh = s ? Math.abs(s.r1 - s.r0) + 1 : 1;
    nameBox.value = w * hh > 1 ? `${hh}R × ${w}C` : `${letter(c)}${r + 1}`;
    fx.textContent = C.t ?? C.v ?? '';
  }
  function select(r, c, extend) {
    const n = G.rows.length, m = G.cols.length;
    if (!n || !m) return;
    r = Math.max(0, Math.min(n - 1, r)); c = Math.max(0, Math.min(m - 1, c));
    if (extend && G.sel) G.sel = { ...G.sel, r1: r, c1: c }; else { G.sel = { r0: r, c0: c, r1: r, c1: c }; G.act = { r, c }; }
    if (!extend) G.act = { r, c };
    show(extend ? { r, c } : G.act); draw(true); status();
  }
  function show({ r, c }) {                                 // keep the moved-to cell on screen
    const H = G.rowH, top = r * H, hd = 44;
    if (top < sc.scrollTop) sc.scrollTop = top;
    else if (top + H > sc.scrollTop + sc.clientHeight - hd) sc.scrollTop = top + H - sc.clientHeight + hd;
    const fzW = G.L[G.freeze] - GUT, x0 = G.L[c] - GUT, x1 = G.L[c + 1] - GUT;
    if (c >= G.freeze) {
      if (x0 - fzW < sc.scrollLeft) sc.scrollLeft = x0 - fzW;
      else if (x1 + GUT > sc.scrollLeft + sc.clientWidth) sc.scrollLeft = x1 + GUT - sc.clientWidth;
    }
  }
  function text(C) { return String(C?.v ?? '').replace(/\s+/g, ' ').trim(); }
  function copy() {
    const s = G.sel; if (!s) return;
    const out = [];
    for (let r = Math.min(s.r0, s.r1); r <= Math.max(s.r0, s.r1); r++) {
      const row = [];
      for (let j = Math.min(s.c0, s.c1); j <= Math.max(s.c0, s.c1); j++) row.push(text(G.rows[r].cells[j]));
      out.push(row.join('\t'));
    }
    const t = out.join('\n');
    const done = () => { host.classList.add('xgcopied'); setTimeout(() => host.classList.remove('xgcopied'), 500); };
    if (navigator.clipboard?.writeText) navigator.clipboard.writeText(t).then(done, () => fallback(t, done)); else fallback(t, done);
  }
  function fallback(t, done) { const a = document.createElement('textarea'); a.value = t; document.body.append(a); a.select(); try { document.execCommand('copy'); done(); } catch (_) {} a.remove(); sc.focus(); }
  const cellOf = e => { const td = e.target.closest('td[data-c]'), tr = td?.parentElement; return td && tr?.dataset.r != null ? { r: +tr.dataset.r, c: +td.dataset.c } : null; };
  const live = e => e.target.closest('a, button, select, input, .xglive');

  sc.addEventListener('scroll', paint, { passive: true });
  // valve53 (user 2026-11-27: '좌우로 이동도 가능하게 · 가볍게'): Shift+wheel or a wheel over the header rows moves sideways
  sc.addEventListener('wheel', e => {
    if (e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;            // zoom · a trackpad's own side swipe
    if (e.shiftKey || e.target.closest('thead')) { e.preventDefault(); sc.scrollLeft += e.deltaY || e.deltaX; }
  }, { passive: false });
  const pageW = () => Math.max(80, sc.clientWidth - (G.L[G.freeze] || GUT) - 40);
  host.querySelector('.xgl1').onclick = () => { sc.scrollLeft -= pageW(); };
  host.querySelector('.xgr1').onclick = () => { sc.scrollLeft += pageW(); };
  const jump = host.querySelector('.xgjump');
  const fillJump = () => { jump.innerHTML = '<option value="">열로 가기…</option>' + G.cols.map((c, j) => j < G.freeze ? '' : `<option value="${j}">${letter(j)} · ${esc(c.label)}</option>`).join('');
    fz.innerHTML = `<option value="0" ${G.freeze ? '' : 'selected'}>없음</option>` + G.cols.map((c, j) => `<option value="${j + 1}" ${G.freeze === j + 1 ? 'selected' : ''}>${letter(j)}까지 · ${esc(c.label)}</option>`).join('');
    fzb.classList.toggle('on', G.freeze > 0); };
  const fz = host.querySelector('.xgfreeze'), fzb = host.querySelector('.xgfzb');
  function setFreeze(n) {
    n = Math.max(0, Math.min(G.cols.length, n | 0));
    const keepCol = Math.max(0, Math.floor(sc.scrollLeft) ? (() => { let j = G.freeze; const x = sc.scrollLeft + G.L[G.freeze]; while (j < G.cols.length && G.L[j + 1] <= x) j++; return j; })() : n);
    if (n && G.L && G.L[n] > sc.clientWidth - 120) {                  // frozen columns wider than the screen leave nothing to move
      fx.textContent = `${letter(n - 1)}까지 고정하면 고정 열이 화면보다 넓어 움직일 칸이 없습니다 — 더 왼쪽 열까지 고정하거나 열 너비를 줄여 주세요`;
      n = G.freeze; fz.value = String(n); host.classList.add('xgwarn'); setTimeout(() => host.classList.remove('xgwarn'), 1500); return; }
    G.freeze = n;
    try { if (FK) localStorage.setItem(FK, String(n)); } catch (_) {}
    head(); fillJump(); draw(true); status();
    sc.scrollLeft = Math.max(0, G.L[Math.max(keepCol, n)] - G.L[n]);   // the first moving column stays where it was
  }
  fz.onchange = () => setFreeze(+fz.value);
  fzb.onclick = () => setFreeze(G.act && G.act.c + 1 !== G.freeze ? G.act.c + 1 : G.freeze ? 0 : 1);   // the chosen cell's column · again = off
  jump.onchange = () => { const j = +jump.value; if (jump.value !== '') { sc.scrollLeft = Math.max(0, G.L[j] - G.L[G.freeze]);
    if (G.rows.length) { const r = G.act ? G.act.r : Math.floor(sc.scrollTop / G.rowH); G.sel = { r0: r, c0: j, r1: r, c1: j }; G.act = { r, c: j }; draw(true); status(); } }
    jump.value = ''; sc.focus({ preventScroll: true }); };
  sc.addEventListener('mousedown', e => {
    if (e.button !== 0 || live(e)) return;
    const rz = e.target.closest('[data-rz]');
    if (rz) { e.preventDefault(); const j = +rz.dataset.rz, x0 = e.clientX, w0 = G.cols[j].w || 80;
      const mv = ev => { G.cols[j].w = Math.max(36, w0 + ev.clientX - x0); head(); draw(true); };
      const up = () => { removeEventListener('mousemove', mv); removeEventListener('mouseup', up); };
      addEventListener('mousemove', mv); addEventListener('mouseup', up); return; }
    const hc = e.target.closest('th[data-col]');
    if (hc) { e.preventDefault(); const j = +hc.dataset.col; G.sel = { r0: 0, c0: j, r1: G.rows.length - 1, c1: j }; G.act = { r: 0, c: j }; draw(true); status(); sc.focus(); return; }
    if (e.target.closest('.xgcorner')) { e.preventDefault(); selectAll(); return; }
    const rn = e.target.closest('th.xgn');
    if (rn) { e.preventDefault(); const r = +rn.parentElement.dataset.r; G.sel = { r0: r, c0: 0, r1: r, c1: G.cols.length - 1 }; G.act = { r, c: 0 }; draw(true); status(); sc.focus(); return; }
    const p = cellOf(e); if (!p) return;
    e.preventDefault(); sc.focus({ preventScroll: true });
    select(p.r, p.c, e.shiftKey); G.drag = true;
  });
  sc.addEventListener('mousemove', e => { if (!G.drag) return; const p = cellOf(e); if (p && G.sel && (p.r !== G.sel.r1 || p.c !== G.sel.c1)) { G.sel = { ...G.sel, r1: p.r, c1: p.c }; draw(true); status(); } });
  const up = () => { G.drag = false; };
  addEventListener('mouseup', up);
  function selectAll() { if (!G.rows.length) return; G.sel = { r0: 0, c0: 0, r1: G.rows.length - 1, c1: G.cols.length - 1 }; G.act = G.act || { r: 0, c: 0 }; draw(true); status(); sc.focus(); }
  sc.addEventListener('keydown', e => {
    if (live(e)) return;
    const a = G.act || { r: 0, c: 0 }, end = G.sel && e.shiftKey ? { r: G.sel.r1, c: G.sel.c1 } : a, page = Math.max(1, Math.floor(sc.clientHeight / G.rowH) - 3);
    const k = e.key, ctrl = e.ctrlKey || e.metaKey;
    const mv = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1], PageUp: [-page, 0], PageDown: [page, 0] }[k];
    if (ctrl && (k === 'c' || k === 'C')) { e.preventDefault(); copy(); return; }
    if (ctrl && (k === 'a' || k === 'A')) { e.preventDefault(); selectAll(); return; }
    if (e.altKey && (k === 'PageDown' || k === 'PageUp')) { e.preventDefault(); sc.scrollLeft += (k === 'PageDown' ? 1 : -1) * pageW(); return; }
    if (mv) { e.preventDefault(); const big = ctrl && (k.startsWith('Arrow'));
      const r = big ? (mv[0] < 0 ? 0 : mv[0] > 0 ? G.rows.length - 1 : end.r) : end.r + mv[0], c = big ? (mv[1] < 0 ? 0 : mv[1] > 0 ? G.cols.length - 1 : end.c) : end.c + mv[1];
      select(r, c, e.shiftKey); return; }
    if (k === 'Tab') { e.preventDefault(); select(a.r, a.c + (e.shiftKey ? -1 : 1)); return; }
    if (k === 'Enter') { e.preventDefault(); const C = (G.rows[a.r]?.cells || [])[a.c];
      if (C?.h && opt.onAction) { const el = tb.querySelector(`tr[data-r="${a.r}"] td[data-c="${a.c}"]`)?.querySelector('a, button, select'); if (el) { el.focus(); if (el.tagName !== 'SELECT') el.click(); return; } }
      select(a.r + (e.shiftKey ? -1 : 1), a.c); return; }
    if (k === 'Home') { e.preventDefault(); select(ctrl ? 0 : a.r, 0, e.shiftKey); return; }
    if (k === 'End') { e.preventDefault(); select(ctrl ? G.rows.length - 1 : a.r, G.cols.length - 1, e.shiftKey); return; }
    if (k === 'Escape') { G.sel = null; G.act = null; draw(true); status(); }
  });
  if (opt.onAction) { host.addEventListener('click', e => { const t = live(e); if (t && host.contains(t)) opt.onAction(t, e); });
    host.addEventListener('change', e => { const t = e.target.closest('select, input'); if (t) opt.onAction(t, e); }); }
  const ro = new ResizeObserver(() => paint());
  ro.observe(sc);

  head(); fillJump(); size(); draw(true);
  return {
    setRows(rows) { G.rows = rows; G.sel = null; G.act = null; sc.scrollTop = 0; size(); draw(true); status(); },
    setCols(cols, rows, freeze) { G.cols = cols; if (freeze != null) G.freeze = freeze; G.freeze = Math.min(G.freeze, cols.length); if (rows) G.rows = rows; G.sel = null; G.act = null; head(); fillJump(); size(); draw(true); status(); },
    get rows() { return G.rows; }, focus() { sc.focus(); },
    getScroll() { return [sc.scrollTop, sc.scrollLeft]; }, setScroll(t, l) { sc.scrollTop = t; sc.scrollLeft = l; draw(true); },
    destroy() { ro.disconnect(); removeEventListener('mouseup', up); if (G.raf) cancelAnimationFrame(G.raf); host.innerHTML = ''; },
  };
}
window.XGrid = XGrid;
})();
