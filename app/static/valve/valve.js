/* Valve Datasheet Review — screen.  Data: /api/valve/* (app/valve/api.py).
 * Screens: Dashboard · Document Management · Valve List · Datasheet Review · Revision Comparison ·
 *          Process Data Verification · PMS Compliance · Reports & Export · Settings.
 * Everything shown comes from the server, except the Process Data / PMS reference values, which are
 * MOCK until the Phase 3 / 4 engines exist — those are labelled MOCK wherever they appear. */
(() => {
'use strict';
const Q = new URLSearchParams(location.search);
const LS = {
  get(k, d) { try { const v = localStorage.getItem('valve.' + k); return v === null ? d : JSON.parse(v); } catch (_) { return d; } },
  set(k, v) { try { localStorage.setItem('valve.' + k, JSON.stringify(v)); } catch (_) {} },
};
const USER = Q.get('user') || LS.get('user', '');
const EMBED = Q.get('embed') === '1';
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const cls = s => String(s || 'none').replace(/[^A-Za-z]/g, '');
const pill = (s, label) => `<span class="pill p-${cls(s)}">${esc(label ?? s)}</span>`;
let SHOWMOCK = false;   // example verdicts only when the user asks to see them
const MOCK = '<span class="mock" title="Phase 3·4 엔진 연결 전의 예시 값입니다 — 판정에 쓰지 마세요">MOCK</span>';

async function api(method, path, body, raw) {
  const opt = { method, headers: { 'X-Author': encodeURIComponent(USER || '') } };
  if (body instanceof FormData) opt.body = body;
  else if (body !== undefined) { opt.body = JSON.stringify(body); opt.headers['Content-Type'] = 'application/json'; }
  let r;
  try { r = await fetch('/api/valve' + path, opt); } catch (e) { throw new Error('서버에 닿지 못했습니다 — P&ID 서버(8000)가 켜져 있는지 확인하세요'); }
  if (raw) { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r; }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return j;
}
function toast(msg, bad) {
  const t = $('#toast'); t.textContent = msg; t.className = 'on' + (bad ? ' bad' : '');
  clearTimeout(toast.t); toast.t = setTimeout(() => { t.className = ''; }, bad ? 6000 : 2600);
}
function modal(title, html, buttons) {
  return new Promise(res => {
    $('#mTitle').textContent = title; $('#mBody').innerHTML = html; $('#mAct').innerHTML = '';
    for (const [label, val, pri] of buttons) {
      const b = document.createElement('button'); b.textContent = label; if (pri) b.className = 'pri';
      b.onclick = () => { $('#modal').hidden = true; res(val === 'form' ? Object.fromEntries($$('#mBody [name]').map(i => [i.name, i.value])) : val); };
      $('#mAct').append(b);
    }
    $('#modal').hidden = false;
    const f = $('#mBody input, #mBody textarea'); if (f) setTimeout(() => f.focus(), 30);
  });
}
async function download(path, method = 'GET', body) {
  const r = await api(method, path, body, true);
  const cd = r.headers.get('Content-Disposition') || '';
  const m = cd.match(/filename\*=UTF-8''([^;]+)/) || cd.match(/filename=([^;]+)/);
  const name = m ? decodeURIComponent(m[1]) : 'download';
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 4000);
  return r;
}

/* ── state ─────────────────────────────────────────────────────────────── */
const S = { pid: null, projects: [], sum: null, grid: null, ds: null, dsId: null, view: 'dash', compare: null };
const VIEWS = ['dash', 'docs', 'list', 'review', 'rev', 'proc', 'pms', 'export', 'settings'];
const STATUSES = ['Not Reviewed', 'Under Review', 'Accepted', 'Rejected', 'Commented', 'Resolved'];
const NOT_PROCESS = new Set(['body_size', 'rating', 'body_material', 'ball_material', 'seat_material', 'seal_material', 'stem_material',
  'bolting_gasket', 'packing_material', 'packing_type', 'connections', 'line_size_inlet', 'line_size_outlet', 'piping_class', 'pipe_material']);
const SECTION_NAMES = { general: 'General Information', process: 'Process Data', mechanical: 'Valve Mechanical Data',
  actuator: 'Actuator', special: 'Special Requirements', accessories: 'Accessories' };

/* ── PDF viewer (server-rendered pages + overlays in PDF points) ───────── */
const pageInfo = {};
async function sizes(docId) { return pageInfo[docId] ||= (await api('GET', `/documents/${docId}/pageinfo`)).sizes; }
class Viewer {
  constructor(host, opts = {}) {
    this.host = host; this.opts = opts; this.zoom = LS.get('zoom', 1.15); this.pages = []; this.docId = null;
    this.ovs = []; this.show = Object.assign({ error: true, missing: true, revision: true, comment: true, extract: true }, LS.get('ovshow2', {}));
    host.innerHTML = `<div class="tbar">
      <button data-a="prev" title="이전 쪽 (PgUp)">◀</button><input class="pno" value="1" aria-label="쪽"><span class="lbl tot">/ 0</span>
      <button data-a="next" title="다음 쪽 (PgDn)">▶</button><span class="sep"></span>
      <button data-a="out" title="축소 (-)">−</button><span class="lbl zl">100%</span><button data-a="in" title="확대 (+)">＋</button>
      <button data-a="fit" title="폭 맞춤">↔</button><span class="sep"></span>
      <input class="q" placeholder="PDF 검색" aria-label="PDF 검색"><button data-a="find" title="검색">⌕</button>
      <span class="sep"></span>
      <span class="chk" title="빨강: 데이터 오류 · PMS 부적합"><label><input type="checkbox" data-c="error"> <i style="background:var(--pms)"></i>Error</label></span>
      <span class="chk" title="주황: 데이터 누락 · HOLD/TBC"><label><input type="checkbox" data-c="missing"> <i style="background:var(--proc)"></i>Missing</label></span>
      <span class="chk" title="노랑: 이전 Revision 대비 변경"><label><input type="checkbox" data-c="revision"> <i style="background:var(--rev)"></i>Rev</label></span>
      <span class="chk" title="파랑: 검토자 수정 · 의견"><label><input type="checkbox" data-c="comment"> <i style="background:var(--usr)"></i>Comment</label></span>
      <span style="flex:1"></span>${opts.extra || ''}</div>${opts.tools ? MKBAR : ''}<div class="stage"></div>`;
    this.stage = $('.stage', host);
    $$('.chk input', host).forEach(i => { i.checked = this.show[i.dataset.c]; i.onchange = () => { this.show[i.dataset.c] = i.checked; LS.set('ovshow2', this.show); this.paintOv(); this.paintMarks(); }; });
    host.querySelector('.tbar').addEventListener('click', e => {
      const a = e.target.closest('button')?.dataset.a; if (!a) return;
      if (a === 'prev') this.step(-1); else if (a === 'next') this.step(1);
      else if (a === 'in') this.setZoom(this.zoom * 1.2); else if (a === 'out') this.setZoom(this.zoom / 1.2);
      else if (a === 'fit') this.fit(); else if (a === 'find') this.find();
      else if (a === 'draw') this.toggleDraw();
    });
    $('.q', host).addEventListener('keydown', e => { if (e.key === 'Enter') this.find(); });
    $('.pno', host).addEventListener('change', e => { const i = (+e.target.value || 1) - 1; this.goIndex(i); });
    this.stage.addEventListener('scroll', () => { this.syncNo(); this.opts.onScroll?.(this); });
    this.stage.addEventListener('mousedown', e => this.mkDown(e));
    this.marks = []; this.tool = 'select'; this.mkCat = LS.get('mkcat', 'comment');
    if (opts.tools) {
      const bar = $('.mkbar', host);
      bar.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return;
        if (b.dataset.tool) this.setTool(b.dataset.tool); else if (b.dataset.mk) this.opts.onMarkCmd?.(b.dataset.mk); });
      $('.mkcat', bar).value = this.mkCat;
      $('.mkcat', bar).onchange = e => { this.mkCat = e.target.value; LS.set('mkcat', this.mkCat);
        const m = this.marks.find(m => m.sel); if (m && m.editable) this.opts.onMarkChange?.(m, { category: this.mkCat }); };
      this.setTool('select');
    }
  }
  async load(docId, pages) {
    this.docId = docId; this.pages = pages; this.size = await sizes(docId);
    $('.tot', this.host).textContent = `/ ${pages.length}`;
    this.render();
  }
  render() {
    const z = this.zoom, imgZ = Math.min(3, Math.max(1, Math.ceil(z * (window.devicePixelRatio || 1) * 1.34 * 2) / 2));
    this.stage.innerHTML = this.pages.map(p => {
      const [w, h] = this.size[p - 1] || [595, 842];
      return `<div class="pg" data-p="${p}" style="width:${w * z * 1.3333}px;height:${h * z * 1.3333}px"><span class="lab">p.${p}</span>
        <img loading="lazy" alt="page ${p}" src="/api/valve/documents/${this.docId}/page/${p}.png?zoom=${imgZ}"></div>`;
    }).join('') || '<div class="empty" style="color:#d6dbe5">표시할 쪽이 없습니다</div>';
    $('.zl', this.host).textContent = Math.round(z * 100) + '%';
    this.paintOv(); this.paintMarks();
  }
  setZoom(z) { const p = this.current(); this.zoom = Math.max(0.4, Math.min(4, z)); LS.set('zoom', this.zoom); this.render(); this.goPage(p, null, false); }
  fit() { const w = this.size[(this.pages[0] || 1) - 1]?.[0] || 595; this.setZoom((this.stage.clientWidth - 40) / (w * 1.3333)); }
  current() {
    const top = this.stage.scrollTop + 20;
    let cur = this.pages[0];
    for (const el of $$('.pg', this.stage)) { if (el.offsetTop <= top) cur = +el.dataset.p; }
    return cur;
  }
  syncNo() { const i = this.pages.indexOf(this.current()); $('.pno', this.host).value = i + 1; }
  step(d) { const i = this.pages.indexOf(this.current()); this.goIndex(i + d); }
  goIndex(i) { if (i >= 0 && i < this.pages.length) this.goPage(this.pages[i]); }
  goPage(p, bbox, smooth = true) {
    const el = $(`.pg[data-p="${p}"]`, this.stage); if (!el) return;
    let y = el.offsetTop - 10, x = this.stage.scrollLeft;
    if (bbox) {
      const z = this.zoom * 1.3333;
      y = el.offsetTop + bbox[1] * z - this.stage.clientHeight / 3;
      x = el.offsetLeft + bbox[0] * z - this.stage.clientWidth / 3;
    }
    this.stage.scrollTo({ top: Math.max(0, y), left: Math.max(0, x), behavior: smooth ? 'smooth' : 'auto' });
  }
  setOverlays(list) { this.ovs = list; this.paintOv(); }
  focus(page, bbox, label) {          // one blinking box for 'where was this read'
    this.ovs = this.ovs.filter(o => o.cat !== 'field').concat(bbox ? [{ cat: 'field', page, bbox, title: label }] : []);
    this.paintOv(); this.goPage(page, bbox);
  }
  paintOv() {
    $$('.ov', this.stage).forEach(e => e.remove());
    const z = this.zoom * 1.3333;
    this.ovs.forEach((o, i) => {
      if (o.cat !== 'field' && o.cat !== 'search' && !this.show[o.cat]) return;
      const el = $(`.pg[data-p="${o.page}"]`, this.stage); if (!el || !o.bbox) return;
      const [x0, y0, x1, y1] = o.bbox, d = document.createElement('div');
      d.className = `ov ${o.cat}${o.sel ? ' sel' : ''}`;
      d.style.cssText = `left:${x0 * z - 2}px;top:${y0 * z - 2}px;width:${(x1 - x0) * z + 4}px;height:${(y1 - y0) * z + 4}px`;
      d.title = [o.title, o.text].filter(Boolean).join('\n');
      if (o.tip) d.innerHTML = `<span class="tip">${esc(o.tip)}</span>`;
      if (o.no) d.insertAdjacentHTML('beforeend', `<span class="ovno">${o.no}</span>`);
      d.onclick = ev => { ev.stopPropagation(); this.opts.onOverlay?.(o, i); };
      el.append(d);
    });
  }
  async find() {
    const q = $('.q', this.host).value.trim(); if (!q || !this.docId) return;
    const hits = [];
    for (const p of this.pages) hits.push(...(await api('GET', `/documents/${this.docId}/search?q=${encodeURIComponent(q)}&page=${p}`)).hits);
    this.ovs = this.ovs.filter(o => o.cat !== 'search').concat(hits.map(h => ({ cat: 'search', page: h.page, bbox: h.bbox, title: q })));
    this.paintOv();
    if (hits.length) { this.goPage(hits[0].page, hits[0].bbox); toast(`'${q}' ${hits.length}곳`); } else toast(`'${q}' 없음`);
  }
  /* ── user mark-up (SVG in PDF points over each page; saved as comments, exported as real PDF annotations) ── */
  setTool(t) {
    this.tool = t; this.stage.classList.toggle('drawing', t !== 'select');
    $$('.mkbar [data-tool]', this.host).forEach(b => b.classList.toggle('on', b.dataset.tool === t));
    this.stage.dataset.tool = t; this.paintMarks();
  }
  toggleDraw(on) { this.setTool((on ?? this.tool === 'select') ? 'rect' : 'select'); }
  setMarks(list) { this.marks = list; this.paintMarks(); }
  paintMarks() {
    $$('svg.mk', this.stage).forEach(e => e.remove());
    const z = this.zoom * 1.3333, hs = 4.5 / z;
    const byPage = {};
    for (const m of this.marks) if (m.page && m.bbox && this.show[MKCAT[m.category] || 'comment'] !== false) (byPage[m.page] ||= []).push(m);
    for (const [p, list] of Object.entries(byPage)) {
      const el = $(`.pg[data-p="${p}"]`, this.stage); if (!el) continue;
      const [w, h] = this.size[p - 1] || [595, 842];
      const svg = document.createElementNS(SVGNS, 'svg');
      svg.setAttribute('class', 'mk' + (this.tool === 'select' ? ' sel-mode' : '')); svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
      svg.innerHTML = `<defs><marker id="mkar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10" fill="none" stroke="context-stroke" stroke-width="1.8"/></marker></defs>`
        + list.map(m => mkSvg(m, hs)).join('');
      el.append(svg);
    }
  }
  pt(pg, e) { const r = pg.getBoundingClientRect(), z = this.zoom * 1.3333; return [Math.round((e.clientX - r.left) / z * 10) / 10, Math.round((e.clientY - r.top) / z * 10) / 10]; }
  mkDown(e) {
    if (e.button !== 0) return;
    const pg = e.target.closest('.pg'); if (!pg) return;
    const page = +pg.dataset.p, p0 = this.pt(pg, e), t = this.tool;
    if (t === 'select') return this.mkSelectDown(e, pg, page, p0);
    e.preventDefault();
    if (t === 'note') { this.opts.onMark?.({ page, kind: 'note', bbox: [p0[0], p0[1], p0[0] + 16, p0[1] + 16] }); return; }
    const tmp = { page, kind: t, category: this.mkCat, bbox: [...p0, ...p0], points: t === 'pen' ? [[p0]] : [p0, p0], tmp: true };
    this.marks = this.marks.concat(tmp);
    const move = ev => {
      const q = this.pt(pg, ev);
      if (t === 'pen') { const st = tmp.points[0], l = st.at(-1); if (Math.hypot(q[0] - l[0], q[1] - l[1]) > 1.2) st.push(q); tmp.bbox = bboxOf(st); }
      else { tmp.points = [p0, q]; tmp.bbox = [Math.min(p0[0], q[0]), Math.min(p0[1], q[1]), Math.max(p0[0], q[0]), Math.max(p0[1], q[1])]; }
      this.paintMarks();
    };
    const up = () => {
      removeEventListener('mousemove', move); removeEventListener('mouseup', up);
      this.marks = this.marks.filter(m => m !== tmp); this.paintMarks();
      const [x0, y0, x1, y1] = tmp.bbox, line = t === 'line' || t === 'arrow';
      if (t === 'pen' ? tmp.points[0].length < 3 : line ? Math.hypot(x1 - x0, y1 - y0) < 5 : (x1 - x0 < 4 || y1 - y0 < 4)) {
        if (t === 'text') this.opts.onMark?.({ page, kind: 'text', bbox: [p0[0], p0[1], p0[0] + 140, p0[1] + 28] });
        return;
      }
      const g = { page, kind: t, bbox: tmp.bbox.map(v => Math.round(v * 10) / 10) };
      if (t === 'pen') g.points = tmp.points; else if (line) g.points = tmp.points;
      this.opts.onMark?.(g);
    };
    addEventListener('mousemove', move); addEventListener('mouseup', up);
  }
  mkSelectDown(e, pg, page, p0) {
    const hEl = e.target.closest('[data-hd]'), sEl = e.target.closest('[data-mid]');
    const id = +(hEl || sEl)?.closest('[data-mid]')?.dataset.mid;
    const m = this.marks.find(x => x.id === id);
    this.marks.forEach(x => x.sel = x === m); this.paintMarks();
    this.opts.onMarkSelect?.(m || null);
    if (!m) return;
    e.preventDefault(); e.stopPropagation();
    if (!m.editable) return;
    const before = { bbox: [...m.bbox], points: m.points ? JSON.parse(JSON.stringify(m.points)) : null }, hd = hEl?.dataset.hd;
    let moved = false;
    const move = ev => {
      const q = this.pt(pg, ev), dx = q[0] - p0[0], dy = q[1] - p0[1];
      if (!moved && Math.hypot(dx, dy) < 2) return; moved = true;
      Object.assign(m, mkTransform(before, m.kind, hd, dx, dy)); this.paintMarks();
    };
    const up = () => {
      removeEventListener('mousemove', move); removeEventListener('mouseup', up);
      if (moved) this.opts.onMarkChange?.(m, { bbox: m.bbox, points: m.points }, before);
    };
    addEventListener('mousemove', move); addEventListener('mouseup', up);
  }
}

const SVGNS = 'http://www.w3.org/2000/svg';
const MKCAT = { comment: 'comment', question: 'comment', error: 'error', missing: 'missing' };
const MKCOL = { comment: '#2e66e6', question: '#2e66e6', error: '#db2626', missing: '#ff8c00' };
const MKTOOLS = [['select', '⬚', '선택 · 옮기기 · 크기 (V)'], ['rect', '▭', '사각형 (R)'], ['cloud', '☁', '구름 (C)'], ['ellipse', '◯', '원 (E)'],
  ['highlight', '▆', '형광펜 (H)'], ['line', '╱', '선 (L)'], ['arrow', '↗', '화살표 (W)'], ['pen', '✎', '펜 — 손글씨 (P)'], ['text', 'T', '글상자 (T)'], ['note', '🗨', '메모 (N)']];
const MKBAR = `<div class="tbar mkbar"><span class="lbl">Mark-up</span>${MKTOOLS.map(([k, i, t]) => `<button data-tool="${k}" title="${t}">${i}</button>`).join('')}
  <span class="sep"></span><select class="mkcat" title="분류 — 색과 Issue 종류가 정해집니다" aria-label="Mark-up 분류">
  <option value="comment">● Comment (파랑)</option><option value="error">● Error (빨강)</option><option value="missing">● Missing (주황)</option><option value="question">● Question (파랑)</option></select>
  <span class="sep"></span><button data-mk="undo" title="되돌리기 (Ctrl+Z)">↶</button><button data-mk="redo" title="다시 하기 (Ctrl+Y)">↷</button>
  <button data-mk="edit" title="선택한 표시의 의견 고치기 (Enter)">✎ 의견</button><button data-mk="del" title="선택한 표시 지우기 (Delete)">🗑</button></div>`;
const bboxOf = pts => { const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };
function mkTransform(b, kind, hd, dx, dy) {          // move (no handle) or resize by a corner / line end
  const [x0, y0, x1, y1] = b.bbox;
  if (!hd) return { bbox: [x0 + dx, y0 + dy, x1 + dx, y1 + dy], points: b.points && (kind === 'pen' ? b.points.map(st => st.map(([x, y]) => [x + dx, y + dy])) : b.points.map(([x, y]) => [x + dx, y + dy])) };
  if (hd === 'p0' || hd === 'p1') { const pts = b.points.map(p => [...p]); const i = hd === 'p0' ? 0 : pts.length - 1; pts[i] = [pts[i][0] + dx, pts[i][1] + dy]; return { points: pts, bbox: bboxOf(pts) }; }
  let n = [x0, y0, x1, y1];
  if (hd.includes('w')) n[0] += dx; if (hd.includes('e')) n[2] += dx; if (hd.includes('n')) n[1] += dy; if (hd.includes('s')) n[3] += dy;
  n = [Math.min(n[0], n[2]), Math.min(n[1], n[3]), Math.max(n[0], n[2]), Math.max(n[1], n[3])];
  if (n[2] - n[0] < 4) n[2] = n[0] + 4; if (n[3] - n[1] < 4) n[3] = n[1] + 4;
  let pts = b.points;
  if (kind === 'pen' && pts) {                       // scale the strokes with the box
    const sx = (n[2] - n[0]) / Math.max(1e-6, x1 - x0), sy = (n[3] - n[1]) / Math.max(1e-6, y1 - y0);
    pts = pts.map(st => st.map(([x, y]) => [n[0] + (x - x0) * sx, n[1] + (y - y0) * sy]));
  }
  return { bbox: n, points: pts };
}
function cloudPath([x0, y0, x1, y1]) {             // scalloped edge, arcs bulging outwards (clockwise)
  const r = Math.max(3, Math.min(8, Math.min(x1 - x0, y1 - y0) / 4)), corners = [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]];
  let d = `M${x0},${y0}`;
  for (let k = 0; k < 4; k++) {
    const [ax, ay] = corners[k], [bx, by] = corners[k + 1], n = Math.max(1, Math.round(Math.hypot(bx - ax, by - ay) / (r * 1.6)));
    for (let j = 1; j <= n; j++) { const x = ax + (bx - ax) * j / n, y = ay + (by - ay) * j / n, rr = Math.hypot(bx - ax, by - ay) / n / 2 * 1.15; d += ` A${rr},${rr} 0 0 1 ${x},${y}`; }
  }
  return d;
}
function mkSvg(m, hs) {
  const c = MKCOL[m.category] || MKCOL.comment, [x0, y0, x1, y1] = m.bbox, w = x1 - x0, h = y1 - y0;
  const st = `stroke="${c}" stroke-width="1.6" vector-effect="non-scaling-stroke"`;
  const hit = `fill="transparent" stroke="transparent" stroke-width="10" vector-effect="non-scaling-stroke"`;
  let g = '';
  if (m.kind === 'highlight') g = `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="${c}" fill-opacity=".32"/>`;
  else if (m.kind === 'line' || m.kind === 'arrow') { const [[a, b], [cx, cy]] = [m.points[0], m.points.at(-1)];
    g = `<line x1="${a}" y1="${b}" x2="${cx}" y2="${cy}" ${hit}/><line x1="${a}" y1="${b}" x2="${cx}" y2="${cy}" ${st} fill="none"${m.kind === 'arrow' ? ' marker-end="url(#mkar)"' : ''}/>`; }
  else if (m.kind === 'pen') g = (m.points || []).map(s => { const d = s.map(p => p.join(',')).join(' '); return `<polyline points="${d}" ${hit}/><polyline points="${d}" ${st} fill="none" stroke-linecap="round" stroke-linejoin="round"/>`; }).join('');
  else if (m.kind === 'cloud') g = `<path d="${cloudPath(m.bbox)}" ${st} fill="${c}" fill-opacity=".04"/>`;
  else if (m.kind === 'ellipse') g = `<ellipse cx="${x0 + w / 2}" cy="${y0 + h / 2}" rx="${w / 2}" ry="${h / 2}" ${st} fill="${c}" fill-opacity=".04"/>`;
  else if (m.kind === 'text') g = `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="#fff" stroke="${c}" stroke-width=".8" vector-effect="non-scaling-stroke"/>
    <foreignObject x="${x0}" y="${y0}" width="${w}" height="${h}"><div xmlns="http://www.w3.org/1999/xhtml" class="mktx" style="color:${c}">${esc(m.text || '')}</div></foreignObject>`;
  else if (m.kind === 'note') g = `<path d="M${x0},${y0} h16 v11 h-9 l-4,4 v-4 h-3 z" fill="${c}" stroke="#fff" stroke-width=".8"/><path d="M${x0 + 3},${y0 + 4} h10 M${x0 + 3},${y0 + 7.5} h7" stroke="#fff" stroke-width="1.1"/>`;
  else g = `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" ${st} fill="${c}" fill-opacity=".04"/>`;
  let hd = '';
  if (m.sel && m.editable) {
    const H = (x, y, k) => `<rect data-hd="${k}" class="hd hd-${k}" x="${x - hs}" y="${y - hs}" width="${hs * 2}" height="${hs * 2}"/>`;
    hd = (m.kind === 'line' || m.kind === 'arrow') ? H(...m.points[0], 'p0') + H(...m.points.at(-1), 'p1')
      : m.kind === 'note' ? '' : H(x0, y0, 'nw') + H(x1, y0, 'ne') + H(x1, y1, 'se') + H(x0, y1, 'sw');
  }
  const no = m.no ? `<g class="mkno"><rect x="${x0 - 15}" y="${y0 - 1}" width="13" height="10" rx="1.5" fill="${c}"/><text x="${x0 - 8.5}" y="${y0 + 6.8}" text-anchor="middle">${m.no}</text></g>` : '';
  return `<g data-mid="${m.id ?? ''}" class="mkg${m.sel ? ' sel' : ''}"><title>${esc((m.no ? '#' + m.no + ' ' : '') + (m.text || '') + (m.by ? `\n— ${m.by}` : ''))}</title>${m.sel ? `<rect class="selbox" x="${x0 - 2}" y="${y0 - 2}" width="${w + 4}" height="${h + 4}"/>` : ''}${g}${no}${hd}</g>`;
}

/* ── navigation ────────────────────────────────────────────────────────── */
function go(v, push = true) {
  if (!VIEWS.includes(v)) v = 'dash';
  S.view = v;
  $$('#menu button').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  $$('.view').forEach(s => s.classList.toggle('on', s.id === 'v-' + v));
  if (push && location.hash !== '#' + v) history.replaceState(null, '', location.pathname + location.search + '#' + v);
  LS.set('view', v);
  RENDER[v]?.();
}
$('#menu').addEventListener('click', e => { const b = e.target.closest('button'); if (b) go(b.dataset.v); });
addEventListener('hashchange', () => { const v = location.hash.slice(1); if (v && v !== S.view) go(v, false); });

async function loadProjects() {
  S.projects = (await api('GET', '/projects')).projects;
  const want = Q.get('project');
  let p = want ? S.projects.find(x => x.name === want) : null;
  if (want && !p) { p = await api('POST', '/projects', { name: want }); S.projects.push(p); }
  if (!p) p = S.projects.find(x => x.id === LS.get('pid')) || S.projects[0];
  if (!p) { p = await api('POST', '/projects', { name: 'CO2 PJT' }); S.projects.push(p); }
  $('#projSel').innerHTML = S.projects.map(x => `<option value="${x.id}">${esc(x.name)}</option>`).join('');
  await selectProject(p.id);
}
async function selectProject(pid) {
  S.pid = +pid; LS.set('pid', S.pid); $('#projSel').value = S.pid;
  $('#crumbProj').textContent = S.projects.find(p => p.id === S.pid)?.name || '';
  S.grid = null; S.ds = null; S.dsId = LS.get('tag.' + S.pid, null);
  await refresh();
}
async function refresh() {
  S.sum = await api('GET', `/projects/${S.pid}/summary`); S.issues = null; S.grid = null; S.pmsRows = null;
  $('#navfoot').innerHTML = `${esc(S.sum.project.name)} · Tag ${S.sum.kpi.tags} · DS ${S.sum.kpi.datasheets}<br>${esc(USER || '이름 없음')}`;
  RENDER[S.view]?.();
}
$('#projSel').onchange = e => selectProject(e.target.value);
$('#projNew').onclick = async () => {
  const r = await modal('새 프로젝트', '<input name="name" placeholder="예) CO2 PJT">', [['취소', null], ['만들기', 'form', 1]]);
  if (!r?.name) return;
  try { const p = await api('POST', '/projects', { name: r.name }); S.projects = (await api('GET', '/projects')).projects;
    $('#projSel').innerHTML = S.projects.map(x => `<option value="${x.id}">${esc(x.name)}</option>`).join(''); selectProject(p.id); }
  catch (e) { toast(e.message, 1); }
};

/* ── 1. Dashboard ──────────────────────────────────────────────────────── */
function donut(parts) {
  const tot = parts.reduce((a, p) => a + p.n, 0) || 1; let a0 = -Math.PI / 2;
  const arcs = parts.filter(p => p.n).map(p => {
    const a1 = a0 + 2 * Math.PI * p.n / tot, large = a1 - a0 > Math.PI ? 1 : 0;
    const P = a => [60 + 48 * Math.cos(a), 60 + 48 * Math.sin(a)];
    const [x0, y0] = P(a0), [x1, y1] = P(a1 - 0.0001); a0 = a1;
    return `<path d="M${x0} ${y0} A48 48 0 ${large} 1 ${x1} ${y1}" stroke="${p.c}" stroke-width="16" fill="none"/>`;
  }).join('');
  return `<svg width="120" height="120" viewBox="0 0 120 120" role="img" aria-label="review status"><circle cx="60" cy="60" r="48" stroke="#edf0f5" stroke-width="16" fill="none"/>${arcs}
    <text x="60" y="58" text-anchor="middle" font-size="20" font-weight="700" fill="#1b2333">${tot === 1 && !parts.some(p => p.n) ? 0 : tot}</text><text x="60" y="74" text-anchor="middle" font-size="11" fill="#5b6475">Tags</text></svg>`;
}
function renderDash() {
  const s = S.sum, k = s.kpi, el = $('#v-dash');
  const tiles = [
    ['Total Valve Tags', k.tags, '▣', '#e8eefc', 'list'], ['Total Datasheets', k.datasheets, '▤', '#e8eefc', 'docs'],
    ['New Tags', s.has_valvelist ? k.new_tags : null, '✚', '#fff1d6', 'list', s.has_valvelist ? '' : 'Valve List 없음'],
    ['Revision Changes', k.revision_changes, '⇆', '#fff4c2', 'rev'],
    ['Data Errors', k.data_errors ?? 0, '✖', '#fbe3e1', 'list:issues'], ['Data Missing', k.data_missing ?? 0, '◌', '#ffe8cc', 'list:issues'],
    ['PMS Non-Compliant', s.has_pms ? k.pms_noncompliant : null, '⛭', '#fbe3e1', 'pms', 'PMS 없음'], ['Process Data Mismatch', null, '∿', '#ffe8d6', 'proc', 'Phase 3'],
    ['Pending Review', k.pending, '◔', '#fff1d6', 'review'], ['Completed Review', k.completed, '✔', '#dcf3e5', 'review']];
  const by = {}; s.tags.forEach(t => { by[t.review_status] = (by[t.review_status] || 0) + 1; });
  const cols = { 'Not Reviewed': '#c4cad6', 'Under Review': '#f0a43a', Accepted: '#1aa35a', Rejected: '#d9443a', Commented: '#2f5bd8', Resolved: '#0f7a43' };
  el.innerHTML = `<div class="vh"><h2>Project Dashboard</h2><span class="soft">${esc(s.project.name)} · Ball Valve Datasheet</span><span class="sp"></span>
      <button data-go="docs">자료 올리기</button><button class="pri" data-go="review">Datasheet Review 열기</button></div>
    ${!k.datasheets ? `<div class="banner info">아직 데이터시트가 없습니다 — <b>Document Management</b> 에서 Datasheet PDF · Valve List · Process Data · PMS 를 올리세요.</div>` : ''}
    <div class="kpis">${tiles.map(([l, n, ic, bg, v, sub]) => `<div class="kpi" data-go="${v}" tabindex="0"><div class="ic" style="background:${bg}">${ic}</div>
      <div class="l">${l}</div><div class="n ${n === null ? 'na' : ''}">${n === null ? (sub || '—') + (sub === 'PMS 없음' ? '' : ' 연결 전') : n}</div></div>`).join('')}</div>
    <div class="dashrow">
      <div class="card"><h3>Review Status by Tag</h3><div class="donut">${donut(STATUSES.map(st => ({ n: by[st] || 0, c: cols[st] })))}
        <div class="legend">${STATUSES.map(st => `<div><i style="background:${cols[st]}"></i>${st}<b style="margin-left:auto;padding-left:10px">${by[st] || 0}</b></div>`).join('')}</div></div>
        <p class="soft" style="margin:10px 0 0">검토 필요 칸(라벨·값 짝이 불확실) <b>${k.review_required}</b>개 — 판정은 사용자가 확정합니다.</p></div>
      <div class="card" style="max-height:330px;overflow:auto"><h3>Review Status Table</h3>
        <table class="t"><thead><tr><th>Tag Number</th><th>Type</th><th>Rev.</th><th>Review Status</th><th>Issues</th></tr></thead><tbody>
        ${s.tags.slice().sort((a, b) => (b.issues - a.issues) || a.tag_key.localeCompare(b.tag_key)).slice(0, 200).map(t => `<tr class="click" data-ds="${t.id}"><td><b>${esc(t.tag_key)}</b></td><td>${esc(t.valve_type)}</td>
          <td>${esc(t.revs.join(' → '))}</td><td>${pill(t.review_status)}</td><td>${t.issues ? pill('review', t.issues) : '0'}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">없음</td></tr>'}</tbody></table></div>
      <div class="card" style="max-height:330px;overflow:auto"><h3>Recent Activity</h3>
        <table class="t"><thead><tr><th>Date</th><th>Tag</th><th>Action</th><th>By</th></tr></thead><tbody>
        ${s.activity.map(a => `<tr ${a.datasheet_id ? `class="click" data-ds="${a.datasheet_id}"` : ''}><td class="mono">${esc(a.at.replace('T', ' ').slice(0, 16))}</td><td>${esc(a.tag || '-')}</td>
          <td>${esc(a.action)}${a.field_key ? ' · ' + esc(a.field_key) : ''}${a.after && a.action !== 'comment' ? ` <span class="soft">→ ${esc(String(a.after).slice(0, 40))}</span>` : ''}</td><td>${esc(a.by)}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">기록이 없습니다</td></tr>'}</tbody></table></div>
    </div>`;
}
document.addEventListener('click', e => {
  const g = e.target.closest('[data-go]'); if (g && !e.target.closest('.tbar')) { const [v, m] = g.dataset.go.split(':'); if (m) G.mode = m; go(v); return; }
  const d = e.target.closest('tr[data-ds]'); if (d && !e.target.closest('#v-list')) openDs(+d.dataset.ds);
});

/* ── 2. Document Management ───────────────────────────────────────────── */
const KIND = { datasheet: ['Valve Datasheet PDF', '필수', '.pdf', true], valvelist: ['Valve List (TBE)', '선택', '.xlsx,.xlsm,.xls', false],
  process: ['Process Data', '선택', '.pdf,.xlsx,.xls', true], pms: ['Piping Material Spec (PMS)', '선택', '.pdf', false] };
function renderDocs() {
  const el = $('#v-docs'), docs = S.sum.documents;
  el.innerHTML = `<div class="vh"><h2>Document Management</h2><span class="soft">원본은 서버에 그대로 보관되고 절대 덮어쓰지 않습니다.</span></div>
    <div class="drops">${Object.entries(KIND).map(([k, [t, req, acc, multi]]) => `<label class="drop" data-k="${k}">
      <b>${t} <span class="${req === '필수' ? 'req' : 'opt'}">${req}</span></b><small>${acc.replace(/,/g, ' · ')}${multi ? ' · 여러 개' : ''}</small>
      <div class="soft" style="margin-top:6px">여기에 놓거나 <u>파일 선택</u></div><input type="file" hidden accept="${acc}" ${multi ? 'multiple' : ''}></label>`).join('')}</div>
    <div class="banner info">Valve Datasheet 는 수십~수백 장을 한 번에 넣어도 됩니다 (개별 PDF · 병합 PDF 모두). Tag 번호로 나누고, 같은 Tag 의 새 Revision 은 이전 판과 따로 보관됩니다.
      Valve List 는 <b>.xlsx</b> 를 그대로 고칩니다 (.xls 는 회사 PC 의 Excel 로 자동 변환 · 안 되면 Excel 에서 .xlsx 로 저장해 넣으세요).</div>
    <div id="jobs"></div>
    <div class="card"><h3>Uploaded Documents (${docs.length})</h3><table class="t"><thead><tr><th>#</th><th>Kind</th><th>File</th><th>Pages</th><th>Result</th><th>Status</th><th>By</th><th>Uploaded</th><th></th></tr></thead><tbody>
    ${docs.map(d => `<tr><td>${d.id}</td><td>${esc(KIND[d.kind]?.[0] || d.kind)}</td><td><b>${esc(d.filename)}</b></td><td>${d.pages || '-'}</td>
      <td>${d.kind === 'datasheet' && d.info ? `${d.info.datasheets ?? '-'} datasheets${d.info.scanned_pages ? ` · <span style="color:var(--bad)">스캔 쪽 ${d.info.scanned_pages}</span>` : ''}` :
        d.kind === 'valvelist' && d.info?.sheets ? d.info.sheets.filter(s => s.kind === 'appendix').map(s => `${esc(s.sheet)} (${s.tags.length})`).join(' · ') : esc(d.info?.note || '')}</td>
      <td>${pill(d.status === 'done' ? 'ok' : d.status === 'error' ? 'bad' : 'UnderReview', d.status)}${d.error ? `<div style="color:var(--bad)">${esc(d.error)}</div>` : ''}</td>
      <td>${esc(d.uploaded_by)}</td><td class="mono">${esc((d.uploaded_at || '').replace('T', ' ').slice(0, 16))}</td>
      <td>${d.status === 'error' ? `<button data-retry="${d.id}">재처리</button>` : d.kind === 'datasheet' && d.status === 'done' ? `<button data-retry="${d.id}" title="개선된 읽기로 다시 읽습니다 — 검토자 수정 · 의견 · Mark-up · 상태는 그대로">다시 읽기</button>` : ''}${d.kind !== 'valvelist' ? ` <a href="/api/valve/documents/${d.id}/file" target="_blank">원본</a>` : ''}</td></tr>`).join('') || '<tr><td colspan="9" class="empty">아직 없습니다</td></tr>'}
    </tbody></table></div>`;
  (S.jobEls || []).filter(b => b.isConnected || !b.dataset.gone).forEach(b => $('#jobs').append(b));
  $$('.drop', el).forEach(d => {
    const inp = $('input', d);
    inp.onchange = () => upload(d.dataset.k, [...inp.files]);
    d.ondragover = e => { e.preventDefault(); d.classList.add('over'); };
    d.ondragleave = () => d.classList.remove('over');
    d.ondrop = e => { e.preventDefault(); d.classList.remove('over'); upload(d.dataset.k, [...e.dataTransfer.files]); };
  });
  $$('[data-retry]', el).forEach(b => b.onclick = async () => { try { watch(await api('POST', `/documents/${b.dataset.retry}/retry`)); } catch (e) { toast(e.message, 1); } });
}
async function upload(kind, files) {
  if (!files.length) return;
  const fd = new FormData(); fd.append('kind', kind); files.forEach(f => fd.append('files', f));
  try { const j = await api('POST', `/projects/${S.pid}/upload`, fd); if (j.skipped?.length) toast(j.skipped.join(' / '), 1); watch(j); }
  catch (e) { toast(e.message, 1); }
}
function watch(job) {
  const box = document.createElement('div'); box.className = 'card'; box.style.marginBottom = '12px';
  (S.jobEls ||= []).unshift(box);                   // kept across re-renders of this screen
  $('#jobs')?.prepend(box);
  const tick = async () => {
    let j; try { j = await api('GET', `/jobs/${job.id}`); } catch (e) { box.innerHTML = `<b style="color:var(--bad)">${esc(e.message)}</b>`; return; }
    const pct = Math.round(100 * j.done / Math.max(1, j.total));
    box.innerHTML = `<b>처리 중</b> <span class="soft">${esc(j.file)} · ${esc(j.msg)}</span><div class="prog"><i style="width:${pct}%"></i></div>${pct}% (${j.done}/${j.total} 쪽)
      ${j.warn ? `<div style="color:var(--warn)">${esc(j.warn)}</div>` : ''}${j.errors.map(e => `<div style="color:var(--bad)">✖ ${esc(e.file)} — ${esc(e.error)}</div>`).join('')}`;
    if (j.status === 'done') {
      box.querySelector('b').textContent = j.errors.length ? '끝 (오류 있음 — 아래 표에서 재처리)' : '분석 끝';
      if (j.exports?.length) {                        // the Excel lists made with the analysis — downloaded right away
        box.insertAdjacentHTML('beforeend', `<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center"><b>결과 파일</b>${j.exports.map(f => `<a class="btnlink" href="${f.url}" download>⇩ ${esc(f.kind)}</a>`).join('')}
          <button data-go="list">Excel List 보기 (PDF 미리보기 연동)</button><button id="jmk">⇩ Mark-up PDF</button><span class="soft">Excel 의 칸 · 링크를 누르면 이 도구가 그 PDF 장 · 위치를 엽니다</span></div>`);
        j.exports.forEach((f, n) => setTimeout(() => { const a = document.createElement('a'); a.href = f.url; a.download = f.name; document.body.append(a); a.click(); a.remove(); }, 300 + n * 900));
        $('#jmk', box).onclick = () => { toast('Mark-up PDF 를 만드는 중…'); download(`/projects/${S.pid}/markup.pdf`).catch(e => toast(e.message, 1)); };
        await refresh(); return;
      }
      await refresh(); setTimeout(() => { box.dataset.gone = '1'; box.remove(); }, j.errors.length ? 20000 : 5000);
    } else setTimeout(tick, 700);
  };
  tick();
}

/* ── 3. Valve List (Excel-like grid) ──────────────────────────────────── */
const G = { sort: LS.get('gsort', { k: 'tag', d: 1 }), flt: {}, sel: new Set(), last: null };
/* live PDF preview beside the lists: one click on a cell / issue -> that page, that point */
function mountPreview() {
  const host = $('#lpv'); if (!host) return;
  S.pv = new Viewer(host, { extra: '<span class="lbl" id="pvcap"></span>', onOverlay: o => { if (o.iss && G.mode === 'issues') { G.selIss = o.iss; renderList(); } } });
  S.pvLoaded = null;
  const sp = $('#lpsplit');
  if (sp) sp.onmousedown = e => {
    e.preventDefault(); const box = $('.lp').getBoundingClientRect();
    const mv = ev => { const w = Math.max(22, Math.min(70, (box.right - ev.clientX) / box.width * 100)); host.style.width = w + '%'; LS.set('pvw', w); };
    const up = () => { removeEventListener('mousemove', mv); removeEventListener('mouseup', up); S.pv?.paintOv(); };
    addEventListener('mousemove', mv); addEventListener('mouseup', up);
  };
  if (S.pvTarget) preview(S.pvTarget);
  else $('#pvcap').textContent = '셀이나 지적 사항을 누르면 그 장 · 그 위치를 보여 줍니다';
}
async function preview(t) {
  S.pvTarget = t; if (!S.pv) return;
  const key = t.doc + ':' + t.pages.join(',');
  if (S.pvLoaded !== key) { await S.pv.load(t.doc, t.pages); S.pvLoaded = key; S.pv.fit(); }
  S.pv.setOverlays(t.ovs || []);
  if (t.bbox) S.pv.focus(t.page, t.bbox, t.label); else S.pv.goPage(t.page || t.pages[0]);
  const c = $('#pvcap'); if (c) c.textContent = t.label + (t.page ? ` · p.${t.page}` : '');
}
async function dsIssues(dsId) {                     // issues of one datasheet as preview overlays
  if (!S.issues) S.issues = (await api('GET', `/projects/${S.pid}/issues`)).issues;
  S.pv?.setMarks(S.issues.filter(i => i.ds_id === dsId && i.comment_id && i.bbox && i.status !== 'Dismissed').map(i => ({ id: i.comment_id, page: i.page, bbox: i.bbox,
    kind: i.kind || 'rect', points: i.points, category: i.category || 'comment', text: i.text_raw ?? i.description, by: i.by, no: i.no })));
  return S.issues.filter(i => i.ds_id === dsId && i.bbox && i.status !== 'Dismissed' && !i.comment_id && (IF.internal || i.type !== 'Extraction Review'))
    .map(i => ({ cat: i.color, page: i.page, bbox: i.bbox, no: i.no, iss: i.ikey, title: `#${i.no} ${i.type} · ${i.field}`, text: i.description, sel: G.selIss === i.ikey }));
}
const listTop = () => `<span class="segtab"><button data-lm="grid" class="${G.mode !== 'issues' ? 'on' : ''}">Valve List</button><button data-lm="issues" class="${G.mode === 'issues' ? 'on' : ''}">Issue List${S.sum?.kpi ? ` (${(S.sum.kpi.data_errors || 0) + (S.sum.kpi.data_missing || 0) + (S.sum.kpi.open_items || 0) + (S.sum.kpi.pms_noncompliant || 0) + (S.sum.kpi.pms_review || 0)})` : ''}</button></span>`;
const lpWrap = inner => `<div class="lp"><div class="lp-left">${inner}</div><div class="split" id="lpsplit" title="끌어 너비 조절"></div><div class="lp-right" id="lpv" style="width:${LS.get('pvw', 42)}%"></div></div>`;
async function renderList() {
  const el = $('#v-list');
  if (G.mode === 'issues') return renderIssues();
  if (!S.grid) { el.innerHTML = '<div class="empty">불러오는 중…</div>'; S.grid = await api('GET', `/projects/${S.pid}/grid`); }
  const base = [{ key: 'tag', title: 'Tag Number', w: 120 }, { key: 'valve_type', title: 'Valve Type', w: 80 }, { key: 'rev', title: 'Rev.', w: 50 },
    { key: 'status', title: 'Review Status', w: 110 }, { key: 'doc_no', title: 'DS Document No.', w: 150 }];
  const all = base.concat(S.grid.columns.filter(c => c.key !== 'valve_type').map(c => ({ key: c.key, title: c.title, w: 130 }))).concat([{ key: 'notes', title: 'Notes', w: 60 }]);
  const order = LS.get('gorder', null), widths = LS.get('gw', {});
  let cols = order ? order.map(k => all.find(c => c.key === k)).filter(Boolean).concat(all.filter(c => !order.includes(c.key))) : all;
  cols = cols.map(c => ({ ...c, w: widths[c.key] || c.w }));
  const val = (r, k) => k in r ? r[k] : (r.cells[k]?.v ?? '');
  const types = [...new Set(S.grid.rows.map(r => r.valve_type))].sort();
  let rows = S.grid.rows.filter(r => Object.entries(G.flt).every(([k, q]) => !q || String(val(r, k)).toLowerCase().includes(q.toLowerCase())));
  const tq = ($('#gq')?.value || '').trim().toUpperCase().replace(/[^0-9A-Z]/g, '');
  if (tq) rows = rows.filter(r => r.tag.includes(tq));
  const ft = $('#gt')?.value, fs = $('#gs')?.value;
  if (ft) rows = rows.filter(r => r.valve_type === ft);
  if (fs) rows = rows.filter(r => r.status === fs);
  rows.sort((a, b) => G.sort.d * String(val(a, G.sort.k)).localeCompare(String(val(b, G.sort.k)), undefined, { numeric: true }));
  const keepQ = $('#gq')?.value || '', keepT = ft || '', keepS = fs || '';
  const oldWrap = $('.xg-wrap', el), keepX = oldWrap?.scrollLeft || 0, keepY = oldWrap?.scrollTop || 0;
  el.innerHTML = `<div class="vh">${listTop()}<input type="search" id="gq" placeholder="Search Tag Number…" style="width:180px" value="${esc(keepQ)}">
      <select id="gt"><option value="">All Valve Types</option>${types.map(t => `<option ${t === keepT ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select>
      <select id="gs"><option value="">All Status</option>${STATUSES.map(t => `<option ${t === keepS ? 'selected' : ''}>${t}</option>`).join('')}</select>
      <span class="soft">${rows.length} / ${S.grid.rows.length} rows · 선택 <b id="gsel">${G.sel.size}</b></span><span class="sp"></span>
      <select id="gbulk" ${G.sel.size ? '' : 'disabled'}><option value="">선택 행 상태 바꾸기…</option>${STATUSES.map(t => `<option>${t}</option>`).join('')}</select>
      <button id="greset" title="열 순서·너비 처음대로">열 초기화</button>
      <button id="gopen" ${G.sel.size ? '' : 'disabled'}>Open Datasheet</button><button class="pri" id="gx">⇩ Export Excel</button></div>
    ${lpWrap(`<div class="xg-wrap"><table class="xg" id="xg" style="width:${70 + cols.reduce((a, c) => a + c.w, 0)}px"><colgroup><col style="width:30px"><col style="width:40px">${cols.map(c => `<col style="width:${c.w}px">`).join('')}</colgroup>
      <thead><tr><th class="fz" style="left:0"><input type="checkbox" id="gall" aria-label="전체 선택"></th><th class="fz" style="left:30px">#</th>${cols.map((c, i) => `<th draggable="true" data-k="${c.key}" ${i === 0 ? 'class="fz" style="left:70px"' : ''} title="${esc(c.title)} — 눌러 정렬 · 끌어 순서 바꾸기">${esc(c.title)}${G.sort.k === c.key ? (G.sort.d > 0 ? ' ▲' : ' ▼') : ''}<span class="rz"></span></th>`).join('')}</tr>
      <tr class="flt"><th class="fz" style="left:0"></th><th class="fz" style="left:30px"></th>${cols.map((c, i) => `<th ${i === 0 ? 'class="fz" style="left:70px"' : ''}><input data-f="${c.key}" value="${esc(G.flt[c.key] || '')}" placeholder="filter" aria-label="${esc(c.title)} filter"></th>`).join('')}</tr></thead>
      <tbody>${rows.map((r, n) => `<tr data-id="${r.id}" class="${G.sel.has(r.id) ? 'sel' : ''}"><td class="fz" style="left:0"><input type="checkbox" ${G.sel.has(r.id) ? 'checked' : ''} aria-label="선택"></td><td class="fz" style="left:30px">${n + 1}</td>
        ${cols.map((c, i) => {
          if (c.key === 'tag') return `<td class="fz" style="left:70px" data-tagcell="1"><span class="tag" style="color:var(--blue);font-weight:600">${esc(r.tag)}</span> <a href="#review" data-open="${r.id}" title="Datasheet Review 로 열기">↗</a></td>`;
          if (c.key === 'status') return `<td>${pill(r.status)}</td>`;
          if (c.key in r) return `<td>${esc(r[c.key])}</td>`;
          const x = r.cells[c.key]; if (!x) return '<td class="ph">—</td>';
          return `<td data-fid="${x.id}" data-k="${c.key}" class="${x.ed ? 'ed' : ''} ${x.st === 'placeholder' || x.st === 'blank' ? 'ph' : ''} ${x.st === 'review' ? 'rv' : ''}" title="${esc(x.v + (x.u ? ' ' + x.u : ''))}${x.ed ? ' (사용자 수정)' : ''} · p.${x.p} — 두 번 눌러 고치기">${esc(x.v || (x.st === 'blank' ? 'Not Found' : ''))}${x.u && x.v ? ' <small>' + esc(x.u) + '</small>' : ''}</td>`;
        }).join('')}</tr>`).join('')}</tbody></table></div>`)}`;
  const wrap = $('.xg-wrap', el); wrap.scrollLeft = keepX; wrap.scrollTop = keepY;
  $$('[data-lm]', el).forEach(b => b.onclick = () => { G.mode = b.dataset.lm; renderList(); });
  mountPreview();
  const re = () => renderList();
  $('#gq').oninput = () => { clearTimeout(G.t); G.t = setTimeout(() => { re(); $('#gq').focus(); const v = $('#gq').value; $('#gq').setSelectionRange(v.length, v.length); }, 200); };
  $('#gt').onchange = re; $('#gs').onchange = re;
  $('#greset').onclick = () => { LS.set('gorder', null); LS.set('gw', {}); re(); };
  $('#gx').onclick = exportValveList;
  $('#gopen').onclick = () => openDs([...G.sel][0]);
  $('#gbulk').onchange = async e => {
    const st = e.target.value; if (!st) return;
    for (const id of G.sel) await api('PUT', `/datasheets/${id}/status`, { status: st, comment: 'bulk (Valve List)' });
    toast(`${G.sel.size}개 → ${st}`); S.grid = null; await refresh(); renderList();
  };
  $('#gall').onchange = e => { rows.forEach(r => e.target.checked ? G.sel.add(r.id) : G.sel.delete(r.id)); paintSel(); };
  $$('thead tr.flt input', el).forEach(i => i.oninput = () => { G.flt[i.dataset.f] = i.value; clearTimeout(G.t); G.t = setTimeout(() => { re(); const f = $(`input[data-f="${i.dataset.f}"]`); f.focus(); f.setSelectionRange(f.value.length, f.value.length); }, 250); });
  const tb = $('#xg tbody');
  tb.onclick = e => {
    const a = e.target.closest('[data-open]'); if (a) { e.preventDefault(); openDs(+a.dataset.open); return; }
    const tr = e.target.closest('tr'); if (!tr) return;
    const id = +tr.dataset.id, ids = rows.map(r => r.id);
    if (e.shiftKey && G.last) { const [i0, i1] = [ids.indexOf(G.last), ids.indexOf(id)].sort((a, b) => a - b); ids.slice(i0, i1 + 1).forEach(x => G.sel.add(x)); }
    else if (e.ctrlKey || e.metaKey || e.target.type === 'checkbox') G.sel.has(id) ? G.sel.delete(id) : G.sel.add(id);
    else { G.sel.clear(); G.sel.add(id); }
    G.last = id; paintSel();
    const row = S.grid.rows.find(r => r.id === id), td = e.target.closest('td');   // live preview
    $$('td.hit', tb).forEach(x => x.classList.remove('hit')); td?.classList.add('hit');
    const x = td?.dataset.k ? row.cells[td.dataset.k] : null, col = cols.find(c => c.key === td?.dataset.k);
    dsIssues(row.id).then(ovs => preview({ doc: row.document_id, pages: row.pages, page: x?.p || row.page, bbox: x?.b, ovs,
      label: `${row.tag}${col ? ' · ' + col.title + ': ' + (x?.v || 'Not Found') : ''}` }));
  };
  function paintSel() {                     // selection without re-rendering (a re-render would eat the double-click)
    $$('tr[data-id]', tb).forEach(tr => { const on = G.sel.has(+tr.dataset.id); tr.classList.toggle('sel', on); $('input', tr).checked = on; });
    $('#gsel').textContent = G.sel.size; $('#gbulk').disabled = $('#gopen').disabled = !G.sel.size;
  }
  tb.onmousedown = e => { if (e.detail > 1) e.preventDefault(); };   // no text selection on double-click
  tb.ondblclick = e => {
    const td = e.target.closest('td[data-fid]'); if (!td || td.querySelector('input')) return;
    const tr = td.closest('tr'), row = S.grid.rows.find(r => r.id === +tr.dataset.id), x = row.cells[td.dataset.k];
    td.innerHTML = `<input class="cell" value="${esc(x.v)}">`; const inp = $('input', td); inp.focus(); inp.select();
    const save = async () => {
      if (inp.value === x.v) { re(); return; }
      try { await api('PUT', `/datasheets/${row.id}/fields/${x.id}`, { value: inp.value, comment: 'Valve List grid' });
        x.v = inp.value; x.ed = true; toast('저장 — 감사 기록에 남았습니다'); } catch (err) { toast(err.message, 1); }
      re();
    };
    let done = false;
    const once = f => () => { if (!done) { done = true; f(); } };
    inp.onkeydown = ev => { if (ev.key === 'Enter') once(save)(); if (ev.key === 'Escape') once(re)(); };
    inp.onblur = once(save);
  };
  // sort · reorder · resize
  let dragK = null;
  $$('#xg thead tr:first-child th[data-k]').forEach(th => {
    th.onclick = e => { if (e.target.classList.contains('rz')) return; const k = th.dataset.k; G.sort = { k, d: G.sort.k === k ? -G.sort.d : 1 }; LS.set('gsort', G.sort); re(); };
    th.ondragstart = e => { dragK = th.dataset.k; th.classList.add('drag'); e.dataTransfer.effectAllowed = 'move'; };
    th.ondragend = () => th.classList.remove('drag');
    th.ondragover = e => { e.preventDefault(); th.classList.add('dropL'); };
    th.ondragleave = () => th.classList.remove('dropL');
    th.ondrop = e => { e.preventDefault(); const keys = cols.map(c => c.key), from = keys.indexOf(dragK), to = keys.indexOf(th.dataset.k);
      if (from < 0 || to < 0 || from === to) return; keys.splice(to, 0, keys.splice(from, 1)[0]); LS.set('gorder', keys); re(); };
    $('.rz', th).onmousedown = e => {
      e.preventDefault(); e.stopPropagation(); th.draggable = false;
      const k = th.dataset.k, x0 = e.clientX, col = $$('#xg col')[cols.findIndex(c => c.key === k) + 2], w0 = parseFloat(col.style.width);
      const mv = ev => { col.style.width = Math.max(40, w0 + ev.clientX - x0) + 'px'; };
      const up = () => { removeEventListener('mousemove', mv); removeEventListener('mouseup', up); const w = LS.get('gw', {}); w[k] = parseFloat(col.style.width); LS.set('gw', w); th.draggable = true; };
      addEventListener('mousemove', mv); addEventListener('mouseup', up);
    };
  });
}
const IF = { type: '', sev: '', st: '', q: '', internal: false };
async function renderIssues() {
  const el = $('#v-list');
  if (!S.issues) { el.innerHTML = '<div class="empty">지적 사항을 계산하는 중…</div>'; S.issues = (await api('GET', `/projects/${S.pid}/issues`)).issues; }
  const all = S.issues.filter(i => IF.internal || i.type !== 'Extraction Review');
  const q = IF.q.toUpperCase().replace(/[^0-9A-Z]/g, '');
  const L = all.filter(i => (!IF.type || i.type === IF.type) && (!IF.sev || i.severity === IF.sev) && (!IF.st || i.status === IF.st) && (!q || i.tag.includes(q)));
  const types = [...new Set(all.map(i => i.type))];
  const cnt = t => all.filter(i => i.type === t && i.status !== 'Dismissed').length;
  const keepY = $('.xg-wrap', el)?.scrollTop || 0;
  el.innerHTML = `<div class="vh">${listTop()}<input type="search" id="iq" placeholder="Tag 검색" style="width:140px" value="${esc(IF.q)}">
      <select id="it"><option value="">All Issue Types</option>${types.map(t => `<option ${t === IF.type ? 'selected' : ''} value="${esc(t)}">${esc(t)} (${cnt(t)})</option>`).join('')}</select>
      <select id="isv"><option value="">All Severity</option>${['Major', 'Minor', 'Info', 'Internal'].map(t => `<option ${t === IF.sev ? 'selected' : ''}>${t}</option>`).join('')}</select>
      <select id="ist"><option value="">All Status</option>${['Open', 'Confirmed', 'Dismissed', 'Resolved'].map(t => `<option ${t === IF.st ? 'selected' : ''}>${t}</option>`).join('')}</select>
      <label class="soft"><input type="checkbox" id="iint" ${IF.internal ? 'checked' : ''}> 추출 확인(내부)</label>
      <span class="soft">${L.length} / ${all.length}</span><span class="sp"></span>
      <button id="ixl" title="지금 필터 그대로 · Dismissed 제외">⇩ Issue List Excel</button><button class="pri" id="ipdf" title="지금 필터 그대로 · 인쇄용 표시 + Issue Summary">⇩ Mark-up PDF</button></div>
    ${lpWrap(`<div class="xg-wrap"><table class="xg" id="ig" style="width:1500px"><colgroup>${[34, 110, 150, 40, 62, 46, 150, 150, 130, 330, 150, 64, 100].map(w => `<col style="width:${w}px">`).join('')}</colgroup>
      <thead><tr>${['No.', 'Tag Number', 'Doc. No.', 'Rev.', 'Sheet', 'Page', 'Field', 'Datasheet Value', 'Issue Type', 'Description', 'Required / Expected', 'Severity', 'Status'].map((h, n) => `<th ${n < 2 ? `class="fz" style="left:${n ? 34 : 0}px"` : ''}>${h}</th>`).join('')}</tr></thead>
      <tbody>${L.slice(0, 3000).map((i, n) => `<tr data-i="${esc(i.ds_id + '|' + i.ikey)}" class="${G.selIss === i.ikey && G.selDs === i.ds_id ? 'sel' : ''}">
        <td class="fz" style="left:0"><b class="no ${i.color}">${i.no}</b></td><td class="fz" style="left:34px"><b>${esc(i.tag)}</b></td><td>${esc(i.doc_no)}</td><td>${esc(i.rev)}</td><td>${i.sheet || ''} of ${i.of || ''}</td><td>${i.page || ''}</td>
        <td title="${esc(i.field)}">${esc(i.field)}${i.row ? ` <small>#${i.row}</small>` : ''}</td><td title="${esc(i.value)}">${esc(i.value || '(blank)')}</td>
        <td>${pill(i.type.replace(/[^A-Za-z]/g, ''), i.type)}</td><td title="${esc(i.description)}">${esc(i.description)}</td><td title="${esc(i.expected)}">${esc(i.expected)}</td>
        <td>${pill(i.severity)}</td><td><select data-ist="${esc(i.ds_id + '|' + i.ikey)}" aria-label="status">${['Open', 'Confirmed', 'Dismissed', 'Resolved'].map(x => `<option ${x === i.status ? 'selected' : ''}>${x}</option>`).join('')}</select></td></tr>`).join('')
        || '<tr><td colspan="13" class="empty">조건에 맞는 지적 사항이 없습니다</td></tr>'}</tbody></table></div>`)}`;
  $('.xg-wrap', el).scrollTop = keepY;
  $$('[data-lm]', el).forEach(b => b.onclick = () => { G.mode = b.dataset.lm; renderList(); });
  const re = () => renderIssues();
  $('#iq').oninput = e => { IF.q = e.target.value; clearTimeout(IF.t); IF.t = setTimeout(() => { re(); const f = $('#iq'); f.focus(); f.setSelectionRange(f.value.length, f.value.length); }, 250); };
  $('#it').onchange = e => { IF.type = e.target.value; re(); }; $('#isv').onchange = e => { IF.sev = e.target.value; re(); };
  $('#ist').onchange = e => { IF.st = e.target.value; re(); }; $('#iint').onchange = e => { IF.internal = e.target.checked; re(); };
  const qs = () => new URLSearchParams({ types: IF.type || (IF.internal ? [...types].join(',') : ''), severity: IF.sev, tag: q ? [...new Set(L.map(i => i.tag))].join(',') : '' }).toString();
  $('#ixl').onclick = () => download(`/projects/${S.pid}/issues.xlsx?${qs()}`).then(r => toast(`Issue List ${r.headers.get('X-Count')}행 — 설계사에게 바로 보낼 수 있습니다`)).catch(e => toast(e.message, 1));
  $('#ipdf').onclick = () => { toast('Mark-up PDF 를 만드는 중… (Tag 수에 따라 수십 초)'); download(`/projects/${S.pid}/markup.pdf?${qs()}`).then(() => toast('내려받음 — 인쇄하면 표시도 같이 나옵니다')).catch(e => toast(e.message, 1)); };
  const tb = $('#ig tbody');
  tb.onclick = async e => {
    if (e.target.closest('select')) return;
    const tr = e.target.closest('tr[data-i]'); if (!tr) return;
    const [dsId, ikey] = [+tr.dataset.i.split('|')[0], tr.dataset.i.slice(tr.dataset.i.indexOf('|') + 1)];
    const i = S.issues.find(x => x.ds_id === dsId && x.ikey === ikey);
    G.selIss = ikey; G.selDs = dsId; $$('tr.sel', tb).forEach(x => x.classList.remove('sel')); tr.classList.add('sel');
    const pages = (S.grid?.rows.find(r => r.id === dsId)?.pages) || (await api('GET', `/datasheets/${dsId}`)).pages;
    preview({ doc: i.document_id, pages, page: i.page, bbox: i.bbox, ovs: await dsIssues(dsId), label: `${i.tag} · #${i.no} ${i.type} · ${i.field}` });
  };
  tb.ondblclick = e => { const tr = e.target.closest('tr[data-i]'); if (tr) openDs(+tr.dataset.i.split('|')[0]); };
  tb.onchange = async e => {
    const sel = e.target.closest('[data-ist]'); if (!sel) return;
    const [dsId, ikey] = [+sel.dataset.ist.split('|')[0], sel.dataset.ist.slice(sel.dataset.ist.indexOf('|') + 1)];
    const note = sel.value === 'Open' ? '' : (await modal(`${sel.value} — 이유`, '<input name="note" placeholder="예) 설계사 확인 요청 / Process DS 참조로 문제 없음">', [['건너뛰기', { note: '' }], ['저장', 'form', 1]]))?.note || '';
    await api('PUT', `/datasheets/${dsId}/issues/${encodeURIComponent(ikey)}`, { status: sel.value, note });
    const i = S.issues.find(x => x.ds_id === dsId && x.ikey === ikey); i.status = sel.value; i.note = note; toast(`→ ${sel.value}`);
  };
  mountPreview();
}
async function exportValveList() {
  toast('Valve List 를 만드는 중… (164 태그 기준 수 초)');
  try {
    const r = await download(`/projects/${S.pid}/valvelist.xlsx`);
    const rep = JSON.parse(decodeURIComponent(r.headers.get('X-Report') || '%7B%7D'));
    toast(`내려받음 — 갱신 ${rep.updated ?? 0} · 신규 ${rep.new ?? 0} · 바뀐 칸 ${rep.changes ?? 0} · 목록 값 유지 ${rep.kept ?? 0}`);
  } catch (e) { toast(e.message, 1); }
}

/* ── 4. Datasheet Review Workbench ────────────────────────────────────── */
const W = { tab: LS.get('wtab', 'data'), q: '', type: '', st: '', viewer: null, selField: null, prevCmp: null, selCm: null };
function openDs(id) { if (!id) return; S.dsId = id; LS.set('tag.' + S.pid, id); go('review'); }
function wbLayout() {
  const el = $('#v-review'); el.classList.add('full');
  const w = LS.get('wbw', { l: 20, r: 25 });
  el.innerHTML = `<div class="wb"><div class="wb-left" style="width:${w.l}%"><div class="pane-h"><b>Tag List</b>
      <input type="search" id="wq" placeholder="Search Tag… (/)" value="${esc(W.q)}">
      <div class="row"><select id="wt"><option value="">All Types</option></select><select id="ws"><option value="">All Status</option>${STATUSES.map(s => `<option ${s === W.st ? 'selected' : ''}>${s}</option>`).join('')}</select></div></div>
      <div class="taglist" id="wlist"></div><div class="revinfo" id="wrev"></div></div>
    <div class="split" data-s="l"></div>
    <div class="wb-center" id="wview"></div>
    <div class="split" data-s="r"></div>
    <div class="wb-right" style="width:${w.r}%"><div class="tabs" id="wtabs">${[['iss', 'Issues'], ['sum', 'Summary'], ['data', 'Datasheet Data'], ['proc', 'Process Data'], ['pms', 'PMS'], ['rev', 'Revision'], ['notes', 'Notes'], ['cmt', 'Comments'], ['hist', 'History']]
      .map(([k, l]) => `<button data-t="${k}" class="${W.tab === k ? 'on' : ''}">${l}</button>`).join('')}</div><div class="rbody" id="wbody"></div>
      <div class="statusbar" id="wstat"></div></div></div>`;
  W.viewer = new Viewer($('#wview'), { tools: true,
    extra: `<button data-a2="prevrev" title="이전 Revision">◁ Rev</button><button data-a2="nextrev" title="다음 Revision">Rev ▷</button><button data-a2="pdf" title="표시한 PDF 내보내기">⇩ Mark-up PDF</button>`,
    onMark: addMark, onMarkChange: changeMark, onMarkSelect: m => { if ((m?.id ?? null) === W.selCm) return; W.selCm = m?.id ?? null; if (W.tab === 'cmt') drawRight(); }, onMarkCmd: markCmd,
    onOverlay: o => { if (o.cmId) { W.selCm = o.cmId; setTab('cmt'); } else if (o.iss) { W.selIss = o.iss; setTab('iss'); } else if (o.key) selectField(o.key); } });
  $('#wview .tbar').addEventListener('click', e => {
    const a = e.target.closest('[data-a2]')?.dataset.a2; if (!a || !S.ds) return;
    const rv = S.ds.revisions, i = rv.findIndex(r => r.id === S.ds.id);
    if (a === 'prevrev') rv[i - 1] ? openDs(rv[i - 1].id) : toast('이전 Revision 이 없습니다');
    if (a === 'nextrev') rv[i + 1] ? openDs(rv[i + 1].id) : toast('다음 Revision 이 없습니다');
    if (a === 'pdf') exportMarkup();
  });
  $('#wtabs').onclick = e => { const b = e.target.closest('button'); if (b) setTab(b.dataset.t); };
  $('#wq').oninput = e => { W.q = e.target.value; drawTagList(); };
  $('#wt').onchange = e => { W.type = e.target.value; drawTagList(); };
  $('#ws').onchange = e => { W.st = e.target.value; drawTagList(); };
  $$('.split', el).forEach(sp => sp.onmousedown = e => {
    e.preventDefault(); sp.classList.add('act');
    const box = $('.wb', el).getBoundingClientRect(), side = sp.dataset.s;
    const mv = ev => {
      const pct = side === 'l' ? (ev.clientX - box.left) / box.width * 100 : (box.right - ev.clientX) / box.width * 100;
      const v = Math.max(12, Math.min(40, pct)); (side === 'l' ? $('.wb-left', el) : $('.wb-right', el)).style.width = v + '%';
      const cur = LS.get('wbw', { l: 20, r: 25 }); cur[side] = v; LS.set('wbw', cur);
    };
    const up = () => { sp.classList.remove('act'); removeEventListener('mousemove', mv); removeEventListener('mouseup', up); W.viewer.paintOv(); };
    addEventListener('mousemove', mv); addEventListener('mouseup', up);
  });
}
function drawTagList() {
  const types = [...new Set(S.sum.tags.map(t => t.valve_type))].sort();
  $('#wt').innerHTML = '<option value="">All Types</option>' + types.map(t => `<option ${t === W.type ? 'selected' : ''}>${esc(t)}</option>`).join('');
  const q = W.q.toUpperCase().replace(/[^0-9A-Z]/g, '');
  const list = S.sum.tags.filter(t => (!q || t.tag_key.includes(q)) && (!W.type || t.valve_type === W.type) && (!W.st || t.review_status === W.st));
  W.list = list;
  $('#wlist').innerHTML = list.map(t => `<div class="ti ${t.id === S.dsId ? 'on' : ''}" data-id="${t.id}"><span class="bar"></span><b>${esc(t.tag_key)}</b>
      <span class="tiss">${t.problems ? `<span class="pill p-bad" title="오류 · 누락 · PMS 등 지적 사항">${t.problems}</span>` : ''}${t.issues ? ` <span class="pill p-ReviewRequired" title="추출 확인 필요 칸">⚠${t.issues}</span>` : ''}</span><small>${esc(t.valve_type)} · Rev.${esc(t.revs.join('→'))} · ${pill(t.review_status)}</small></div>`).join('')
    || '<div class="empty">조건에 맞는 Tag 가 없습니다</div>';
  $('#wlist').onclick = e => { const it = e.target.closest('.ti'); if (it) openDs(+it.dataset.id); };
  $('#wlist .ti.on')?.scrollIntoView({ block: 'nearest' });
}
async function renderReview() {
  if (!S.sum.tags.length) { const el = $('#v-review'); el.classList.remove('full'); el.innerHTML = '<div class="empty">데이터시트가 없습니다 — Document Management 에서 올리세요.</div>'; return; }
  if (!$('#wlist')) wbLayout();
  if (!S.dsId || !S.sum.tags.some(t => t.id === S.dsId) && !(S.ds && S.ds.id === S.dsId)) {
    const any = S.dsId ? await api('GET', `/datasheets/${S.dsId}`).catch(() => null) : null;
    if (!any || any.project_id !== S.pid) S.dsId = S.sum.tags[0].id;
  }
  drawTagList();
  if (!S.ds || S.ds.id !== S.dsId) {
    S.ds = await api('GET', `/datasheets/${S.dsId}`);
    W.prevCmp = null; W.selField = null;
    const rv = S.ds.revisions, i = rv.findIndex(r => r.id === S.ds.id);
    if (i > 0) W.prevCmp = await api('GET', `/compare?prev=${rv[i - 1].id}&new=${S.ds.id}`).catch(() => null);
    await W.viewer.load(S.ds.document_id, S.ds.pages);
  }
  paintDsOverlays(); drawRight(); drawRevInfo();
}
function paintDsOverlays() {
  const ov = [];
  const noOf = Object.fromEntries((S.ds.issues || []).filter(i => i.comment_id).map(i => [i.comment_id, i.no]));
  W.viewer.setMarks(S.ds.comments.filter(c => c.page && c.bbox).map(c => ({ id: c.id, page: c.page, bbox: c.bbox, kind: c.kind || 'rect',
    points: c.points, category: c.category || 'comment', text: c.text, by: c.by, no: noOf[c.id], editable: true, sel: W.selCm === c.id })));
  for (const i of S.ds.issues || []) {                // every issue in its colour, numbered like the exported PDF
    if (i.comment_id || !i.bbox || i.status === 'Dismissed' || (i.type === 'Extraction Review' && !W.showInternal)) continue;
    ov.push({ cat: i.color, page: i.page, bbox: i.bbox, key: i.key, no: i.no, title: `#${i.no} ${i.type} · ${i.field}`, text: i.description + (i.expected ? `\nRequired: ${i.expected}` : ''), iss: i.ikey, sel: W.selIss === i.ikey });
  }
  const sf = S.ds.fields.find(f => f.key === W.selField);
  if (sf?.bbox) ov.push({ cat: 'field', page: sf.page, bbox: sf.bbox, title: sf.display });
  W.viewer.setOverlays(ov);
}
function drawRevInfo() {
  const d = S.ds;
  $('#wrev').innerHTML = `<b>Revision Info</b><div>Doc. ${esc(d.doc_no)}</div><div>Current Rev.: <b>${esc(d.rev)}</b> ${d.rev_date ? `<small>(${esc(d.rev_date)})</small>` : ''}</div>
    <div>Revisions: ${d.revisions.map(r => r.id === d.id ? `<b>${esc(r.rev)}</b>` : `<a href="#" data-r="${r.id}">${esc(r.rev)}</a>`).join(' → ')}</div>
    ${d.rev_history.map(h => `<div class="soft">${esc(h)}</div>`).join('')}`;
  $$('#wrev [data-r]').forEach(a => a.onclick = e => { e.preventDefault(); openDs(+a.dataset.r); });
}
function setTab(t) { W.tab = t; LS.set('wtab', t); $$('#wtabs button').forEach(b => b.classList.toggle('on', b.dataset.t === t)); drawRight(); }
function fieldLine(f) {
  const v = f.edited_value ?? f.value, ref = f.ref;
  const st = f.status === 'ok' ? '' : f.status === 'blank' ? pill('NotFound', 'Not Found') : f.status === 'review' ? pill('ReviewRequired', 'Review Required') : pill('placeholder', 'VTA/NA');
  return `<div class="fl ${W.selField === f.key ? 'on' : ''}" data-k="${esc(f.key)}"><span class="k">${esc(f.display || f.label)}${f.row ? ` <small>#${f.row}</small>` : ''}</span>
    <span class="v ${f.edited_value != null ? 'ed' : ''}">${f.edited_value != null ? `<span class="was">${esc(f.value || '∅')}</span>` : ''}${esc(v)}${f.unit ? ` <small>${esc(f.unit)}</small>` : ''}
    ${ref?.text ? `<span class="ref">${ref.kind === 'general' ? 'General Note' : 'Note'} ${ref.no}: ${esc(ref.text.slice(0, 260))}${ref.text.length > 260 ? '…' : ''}</span>` : ''}
    ${f.edited_value != null ? `<small class="soft">✎ ${esc(f.edited_by)} ${esc((f.edited_at || '').replace('T', ' ').slice(0, 16))}</small>` : ''}</span>
    <span>${st} <span class="act"><button data-edit="${f.id}" title="고치기">✎</button></span></span></div>`;
}
function drawRight() {
  const d = S.ds, b = $('#wbody'); if (!d || !b) return;
  const F = Object.fromEntries(d.fields.map(f => [f.key, f])), val = k => F[k] ? (F[k].edited_value ?? F[k].value) : '';
  const cnt = s => d.fields.filter(f => f.status === s && f.edited_value == null).length;
  let h = '';
  if (W.tab === 'iss') {
    const L = (d.issues || []).filter(i => i.type !== 'Extraction Review' || W.showInternal);
    h = `<div class="sect" style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">${['error', 'missing', 'revision', 'comment'].map(c => {
        const n = L.filter(i => i.color === c).length; return n ? `<span class="pill p-${{ error: 'bad', missing: 'ReviewRequired', revision: 'Modified', comment: 'Commented' }[c]}">${{ error: 'Error', missing: 'Missing', revision: 'Rev', comment: 'Reviewer' }[c]} ${n}</span>` : ''; }).join('')}
        <label class="soft" style="margin-left:auto"><input type="checkbox" id="wint" ${W.showInternal ? 'checked' : ''}> 추출 확인(내부) ${(d.issues || []).filter(i => i.type === 'Extraction Review').length}</label></div>
      ${L.map(i => `<div class="iss ${i.color} ${W.selIss === i.ikey ? 'on' : ''} ${i.status === 'Dismissed' ? 'dis' : ''}" data-iss="${esc(i.ikey)}">
        <div class="ih"><b class="no ${i.color}">${i.no}</b><b>${esc(i.type)}</b><span class="soft">${esc(i.field)}${i.row ? ' #' + i.row : ''} · Sheet ${i.sheet || ''}/${i.of || ''} · p.${i.page || ''}</span><span class="sp"></span>
        <select data-ist="${esc(i.ikey)}" aria-label="status">${['Open', 'Confirmed', 'Dismissed', 'Resolved'].map(x => `<option ${x === i.status ? 'selected' : ''}>${x}</option>`).join('')}</select></div>
        <div>${esc(i.description)}</div>${i.expected ? `<div class="soft">Required / expected: <b>${esc(i.expected)}</b></div>` : ''}${i.note ? `<div class="soft">Note: ${esc(i.note)}</div>` : ''}</div>`).join('') || '<div class="empty">이 데이터시트에는 지적 사항이 없습니다</div>'}
      <p class="soft">Dismissed 는 설계사 전달본(Excel · Mark-up PDF)에서 빠집니다. 상태를 바꾸면 이유를 묻고 감사 기록에 남깁니다.</p>`;
  } else if (W.tab === 'sum') {
    h = `<div class="sect"><h4>Datasheet</h4><table class="t"><tbody>
      ${[['Tag Number', d.tag], ['Valve Type', d.valve_type], ['Form', d.title + (d.form ? ` (${d.form})` : '')], ['Document No.', d.doc_no], ['Revision', `${d.rev} ${d.rev_date ? '· ' + d.rev_date : ''}`],
        ['File', `${d.filename} · p.${d.pages.join(', ')}`], ['Service', val('service')], ['P&ID No.', val('pid_no')], ['Line No.', val('line_no')], ['Piping Class', val('piping_class')],
        ['Valve Size / Rating', `${val('body_size')} / ${val('rating')}`], ['Body Type', val('body_type') || val('instrument_type')]]
        .map(([k, v]) => `<tr><td class="soft" style="width:38%">${k}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table></div>
      <div class="sect"><h4>Extraction</h4>${pill('ok', `읽음 ${cnt('ok')}`)} ${pill('placeholder', `VTA/NA ${cnt('placeholder')}`)} ${pill('NotFound', `Not Found ${cnt('blank')}`)} ${pill('ReviewRequired', `Review Required ${cnt('review')}`)}
        <p class="soft">PDF 글자층에서 직접 읽어 신뢰도는 칸마다 '읽음/없음/검토 필요' 로 표시합니다 (추정하지 않음). 스캔 쪽은 읽지 않습니다.</p></div>
      <div class="sect"><h4>Review Required</h4>${d.fields.filter(f => f.status === 'review' && f.edited_value == null).map(fieldLine).join('') || '<div class="soft">없음</div>'}</div>`;
  } else if (W.tab === 'data') {
    const secs = {};
    d.fields.forEach(f => { if (f.section === 'process' && f.key.includes('.')) return; (secs[f.section] ||= []).push(f); });
    h = Object.keys(SECTION_NAMES).filter(s => secs[s]).map(s => `<div class="sect"><h4>${SECTION_NAMES[s]}</h4>${secs[s].map(fieldLine).join('')}</div>`).join('');
  } else if (W.tab === 'proc') {
    const pf = d.fields.filter(f => f.section === 'process' && !NOT_PROCESS.has(f.key));
    const ex = ['body_size', 'rating', 'body_material'].map(k => F[k]).filter(Boolean);
    h = `<div class="banner">${MOCK} Process Data 비교 엔진(Phase 3)은 아직 연결 전입니다. 아래 <b>Datasheet 값과 위치는 실제</b>입니다. 판정은 비워 두고, 화면 확인용 예시는 버튼으로만 봅니다. ${mockBtn()}</div>
      <table class="t"><thead><tr><th>Parameter</th><th>Process Data ${MOCK}</th><th>Datasheet</th><th>Unit</th><th>Result</th><th>Page</th></tr></thead><tbody>
      ${pf.map((f, i) => { const v = f.edited_value ?? f.value, m = mockProc(v, i); return `<tr class="click" data-k="${esc(f.key)}"><td>${esc(f.display)}</td><td>${esc(m.pv)}</td><td>${esc(v || 'Not Found')}</td><td>${esc(f.unit)}</td><td>${pill(m.r.replace(/ /g, ''), m.r)}</td><td>${f.page}</td></tr>`; }).join('') || '<tr><td colspan="6" class="empty">공정 항목 없음</td></tr>'}
      </tbody></table><div class="sect" style="margin-top:10px"><h4>Excluded — not process data (spec §6.3)</h4>
      <table class="t"><tbody>${ex.map(f => `<tr class="click" data-k="${esc(f.key)}"><td>${esc(f.display)}</td><td>${esc(f.edited_value ?? f.value)}</td><td>${pill('Excluded', 'N/A (Excluded)')}</td></tr>`).join('')}</tbody></table>
      <p class="soft">Valve Size · Rating · Material 은 Process Data 검증에서 비교하지 않습니다 (Datasheet · PMS 기준으로 관리).</p></div>`;
  } else if (W.tab === 'pms') {
    h = !d.pms ? `<div class="empty">PMS 문서가 아직 없습니다 — Document Management 에 Piping Material Specification PDF 를 올리면<br>Piping Class 의 Rating · NACE · Trim · Body · Seat 를 이 데이터시트와 비교합니다.</div>`
      : `<p>Piping Class <b>${esc(val('piping_class') || 'Not Found')}</b> · PMS ${esc(d.area || '지역 미상')} · <span class="soft">${esc(d.pms_doc?.filename || '')}</span></p>
      <table class="t"><thead><tr><th>Item</th><th>PMS Requirement</th><th>Datasheet</th><th>Result</th><th>PMS p.</th></tr></thead><tbody>
      ${d.pms.map(r => `<tr class="click" data-k="${esc(r.key)}" title="${esc(r.reason)}"><td>${esc(r.item)}</td><td>${esc(r.req)}</td><td>${esc(r.ds)}</td><td>${pill(r.result.replace(/[^A-Za-z]/g, ''), r.result)}<div class="soft" style="font-size:11px">${esc(r.reason)}</div></td><td>${r.pms_page ? `<a href="#" data-pmsp="${r.pms_page}" data-pmsb="${esc(JSON.stringify(r.pms_bbox))}">${r.pms_page}</a>` : ''}</td></tr>`).join('')}</tbody></table>
      <p class="soft">재질은 표기가 아니라 규격·등급으로 비교합니다 (A351 CF8M ⊂ 316/316L SS A351-CF8M/CF3M = Compliant). 같은 계열의 다른 등급은 Review Required.</p>`;
  } else if (W.tab === 'rev') {
    const c = W.prevCmp;
    h = c ? `<p>Rev.<b>${esc(c.prev.rev)}</b> → Rev.<b>${esc(c.new.rev)}</b> · ${['Modified', 'Added', 'Deleted'].map(k => pill(k, `${k} ${c.rows.filter(r => r.change === k).length}`)).join(' ')}</p>
      <table class="t"><thead><tr><th>Field</th><th>Previous</th><th>New</th><th>Type</th><th>p.</th></tr></thead><tbody>
      ${c.rows.filter(r => r.change !== 'Unchanged').map(r => `<tr class="click" data-k="${esc(r.key)}"><td>${esc(r.display)}</td><td class="chg-old">${esc(r.previous)}</td><td><b>${esc(r.new)}</b></td><td>${pill(r.change)}</td><td>${r.new_page || r.prev_page || ''}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">바뀐 칸이 없습니다</td></tr>'}</tbody></table>
      <p><button data-go="rev">Revision Comparison 화면에서 나란히 보기</button></p>`
      : `<div class="empty">이 Tag 는 Revision 이 하나뿐입니다 (Rev.${esc(d.rev)}).<br>새 Revision PDF 를 Document Management 에 올리면 여기서 이전 판과 칸별로 비교합니다.</div>`;
  } else if (W.tab === 'notes') {
    const gn = Object.entries(d.general_notes || {});
    h = `<div class="sect notes"><h4>Datasheet Notes (${d.notes.length})</h4>${d.notes.map(n => `<div class="n" data-np="${n.page}" data-nb="${esc(JSON.stringify(n.bbox))}"><b>${n.no}.</b>${esc(n.text)} <small class="soft">p.${n.page}</small></div>`).join('') || '<div class="soft">없음</div>'}</div>
      <div class="sect notes"><h4>General Notes — ${esc(d.doc_no)} (${gn.length})</h4>${gn.map(([no, t]) => `<div class="n"><b>${no}.</b>${esc(t)}</div>`).join('') || '<div class="soft">이 문서의 General Notes 를 찾지 못했습니다</div>'}</div>`;
  } else if (W.tab === 'cmt') {
    h = `<div class="sect"><textarea id="cmtx" rows="3" style="width:100%" placeholder="Review Comment (Engineering 의견)"></textarea>
        <div style="display:flex;gap:6px;margin-top:4px"><button class="pri" id="cmadd">의견 남기기</button><button id="cmdraw" title="PDF 위 Mark-up 도구 줄에서 다른 모양(구름 · 화살표 · 펜 · 글상자 …)도 고를 수 있습니다">▭ PDF 위에 표시하며 남기기</button></div></div>
      ${d.comments.map(c => `<div class="cm ${W.selCm === c.id ? 'sel' : ''}" data-cm="${c.id}"><div class="h"><i class="mkdot" style="background:${MKCOL[c.category] || MKCOL.comment}"></i><b>${esc(c.by)}</b>${c.bbox ? `<span class="soft">${KIND_KO[c.kind || 'rect'] || ''}</span>` : ''}<span>${esc(c.at.replace('T', ' ').slice(0, 16))}</span>${c.page ? `<a href="#" data-cmgo="${c.id}">p.${c.page} ▭</a>` : ''}<span class="sp"></span>
        <button data-cmed="${c.id}" title="고치기">✎</button><button data-cmdel="${c.id}" title="지우기">✕</button></div><div class="ct">${esc(c.text) || '<span class="soft">(표시만)</span>'}</div></div>`).join('') || '<div class="soft">아직 의견이 없습니다</div>'}`;
  } else if (W.tab === 'hist') {
    h = `<table class="t"><thead><tr><th>When</th><th>Who</th><th>What</th></tr></thead><tbody>${d.history.map(a => `<tr><td class="mono">${esc(a.at.replace('T', ' ').slice(5, 16))}</td><td>${esc(a.by)}</td>
      <td>${esc(a.action)} ${a.field_key ? `<b>${esc(a.field_key)}</b>` : ''}${a.before != null ? ` <span class="chg-old">${esc(String(a.before).slice(0, 60))}</span>` : ''}${a.after != null ? ` → ${esc(String(a.after).slice(0, 80))}` : ''}${a.comment ? ` <small class="soft">(${esc(a.comment)})</small>` : ''}</td></tr>`).join('') || '<tr><td colspan="3" class="empty">기록 없음</td></tr>'}</tbody></table>`;
  }
  b.innerHTML = h;
  b.onclick = async e => {
    const ed = e.target.closest('[data-edit]'); if (ed) { editField(+ed.dataset.edit); return; }
    const np = e.target.closest('[data-np]'); if (np) { W.viewer.focus(+np.dataset.np, JSON.parse(np.dataset.nb || 'null'), 'Note'); return; }
    const cg = e.target.closest('[data-cmgo]'); if (cg) { e.preventDefault(); const c = d.comments.find(x => x.id === +cg.dataset.cmgo); W.selCm = c.id; paintDsOverlays(); W.viewer.goPage(c.page, c.bbox); drawRight(); return; }
    const ce = e.target.closest('[data-cmed]'); if (ce) { const c = d.comments.find(x => x.id === +ce.dataset.cmed);
      const r = await modal('의견 고치기', `<textarea name="text" rows="4">${esc(c.text)}</textarea>`, [['취소', null], ['저장', 'form', 1]]);
      if (r) await changeMark({ id: c.id }, { text: r.text }, { text: c.text }); return; }
    const cd = e.target.closest('[data-cmdel]'); if (cd) { if (await modal('의견 지우기', '이 의견(과 PDF 표시)을 지울까요? 기록은 History 에 남습니다.', [['취소', 0], ['지우기', 1, 1]])) {
      W.selCm = +cd.dataset.cmdel; await markCmd('del'); } return; }
    const pp = e.target.closest('[data-pmsp]'); if (pp) { e.preventDefault(); openPmsRef(+pp.dataset.pmsp, JSON.parse(pp.dataset.pmsb || 'null')); return; }
    if (e.target.closest('select')) return;
    const is = e.target.closest('[data-iss]'); if (is) { const i = d.issues.find(x => x.ikey === is.dataset.iss); W.selIss = i.ikey; paintDsOverlays(); if (i.bbox) W.viewer.focus(i.page, i.bbox, i.field); $$('#wbody .iss').forEach(x => x.classList.toggle('on', x.dataset.iss === i.ikey)); return; }
    const k = e.target.closest('[data-k]'); if (k) selectField(k.dataset.k);
  };
  b.onchange = async e => {
    if (e.target.id === 'wint') { W.showInternal = e.target.checked; paintDsOverlays(); drawRight(); return; }
    const sel = e.target.closest('[data-ist]'); if (!sel) return;
    const note = sel.value === 'Open' ? '' : (await modal(`${sel.value} — 이유`, '<input name="note" placeholder="예) 설계사 확인 요청 / Process DS 참조로 문제 없음">', [['건너뛰기', { note: '' }], ['저장', 'form', 1]]))?.note || '';
    await api('PUT', `/datasheets/${d.id}/issues/${encodeURIComponent(sel.dataset.ist)}`, { status: sel.value, note });
    S.ds = await api('GET', `/datasheets/${d.id}`); S.issues = null; paintDsOverlays(); drawRight(); toast(`→ ${sel.value}`);
  };
  $('#cmadd') && ($('#cmadd').onclick = async () => { const t = $('#cmtx').value.trim(); if (!t) return;
    S.ds = await api('POST', `/datasheets/${d.id}/comments`, { text: t }); drawRight(); toast('의견을 남겼습니다'); });
  $('#cmdraw') && ($('#cmdraw').onclick = () => { W.viewer.setTool('rect'); toast('PDF 위에서 끌어 그리세요 — 위 Mark-up 줄에서 모양·분류를 고릅니다 (Esc: 선택 도구)'); });
  $('#wstat').innerHTML = `<b>${esc(d.tag)}</b><span class="soft">Rev.${esc(d.rev)}</span><span style="flex:1"></span>
    <select id="wst" aria-label="Review Status">${STATUSES.map(s => `<option ${s === d.review_status ? 'selected' : ''}>${s}</option>`).join('')}</select>`;
  $('#wst').onchange = async e => { S.ds = await api('PUT', `/datasheets/${d.id}/status`, { status: e.target.value });
    const t = S.sum.tags.find(t => t.id === d.id); if (t) t.review_status = e.target.value; drawTagList(); toast(`${d.tag} → ${e.target.value}`); };
}
function selectField(key) {
  const f = S.ds.fields.find(x => x.key === key);
  const r = W.prevCmp?.rows.find(x => x.key === key);
  W.selField = key; paintDsOverlays();
  if (f?.bbox) W.viewer.focus(f.page, f.bbox, f.display);
  else if (r?.new_bbox) W.viewer.focus(r.new_page, r.new_bbox, r.display);
  $$('#wbody [data-k]').forEach(x => x.classList.toggle('on', x.dataset.k === key));
}
async function editField(fid) {
  const f = S.ds.fields.find(x => x.id === fid);
  const r = await modal(`${f.display} 고치기`, `<p class="soft">PDF 에서 읽은 값: <b>${esc(f.value || '(빈칸)')}</b> · p.${f.page}<br>원래 값으로 되돌리려면 읽은 값과 똑같이 두세요.</p>
    <input name="value" value="${esc(f.edited_value ?? f.value)}"><input name="comment" placeholder="고친 이유 (감사 기록)" style="margin-top:6px">`, [['취소', null], ['저장', 'form', 1]]);
  if (!r) return;
  try { S.ds = await api('PUT', `/datasheets/${S.ds.id}/fields/${fid}`, { value: r.value, comment: r.comment }); S.grid = null; drawRight(); toast('저장 — 원래 읽은 값과 함께 남습니다'); }
  catch (e) { toast(e.message, 1); }
}
/* mark-up: every change is saved at once (comment rows); ↶/↷ replay the inverse request */
const KIND_KO = { rect: '사각형', cloud: '구름', ellipse: '원', highlight: '형광펜', line: '선', arrow: '화살표', pen: '펜', text: '글상자', note: '메모' };
const CAT_OPTS = sel => ['comment', 'error', 'missing', 'question'].map(c => `<option value="${c}" ${c === sel ? 'selected' : ''}>${{ comment: 'Comment — 의견 (파랑)', error: 'Error — 데이터 오류 (빨강)', missing: 'Missing — 데이터 누락 (주황)', question: 'Question — 질의 (파랑)' }[c]}</option>`).join('');
async function markText(title, kind, text, cat) {
  const need = kind === 'text' || kind === 'note';
  return modal(title, `<p class="soft">${KIND_KO[kind] || kind} · 분류에 따라 색과 Issue 종류(Comment / Data Error / Data Missing)가 정해지고, Issue List 와 Mark-up PDF 에 번호로 나갑니다.</p>
    <select name="category" style="width:100%;margin-bottom:6px">${CAT_OPTS(cat)}</select>
    <textarea name="text" rows="4" placeholder="${need ? '글 (필수)' : '설계사에게 전할 의견 (비워 두면 표시만 남습니다)'}">${esc(text || '')}</textarea>`, [['취소', null], ['저장', 'form', 1]]);
}
function pushUndo(op) { W.undo = (W.undo || []).concat(op).slice(-100); W.redo = []; }
async function addMark(g) {
  const r = await markText('Mark-up 의견', g.kind, '', W.viewer.mkCat);
  if (!r || ((g.kind === 'text' || g.kind === 'note') && !r.text.trim())) return;
  try {
    const out = await api('POST', `/datasheets/${S.ds.id}/comments`, { ...g, category: r.category, text: r.text });
    S.ds = out; S.issues = null; W.selCm = out.new_comment_id;
    pushUndo({ t: 'create', id: out.new_comment_id, ds: S.ds.id });
    paintDsOverlays(); if (W.tab === 'cmt') drawRight();
    toast('표시를 남겼습니다 — Ctrl+Z 되돌리기');
  } catch (e) { toast(e.message, 1); }
}
async function changeMark(m, after, before) {
  const c = S.ds.comments.find(x => x.id === m.id); if (!c) return;
  before = before || Object.fromEntries(Object.keys(after).map(k => [k, c[k]]));
  try { S.ds = await api('PUT', `/comments/${m.id}`, after); S.issues = null; pushUndo({ t: 'update', id: m.id, ds: S.ds.id, before, after }); }
  catch (e) { toast(e.message, 1); }
  paintDsOverlays(); if (W.tab === 'cmt') drawRight();
}
async function markCmd(cmd) {
  const c = S.ds?.comments.find(x => x.id === W.selCm);
  if (cmd === 'undo' || cmd === 'redo') {
    const from = cmd === 'undo' ? (W.undo ||= []) : (W.redo ||= []), to = cmd === 'undo' ? (W.redo ||= []) : (W.undo ||= []);
    const op = from.at(-1); if (!op) return toast(cmd === 'undo' ? '되돌릴 것이 없습니다' : '다시 할 것이 없습니다');
    if (op.ds !== S.ds.id) return toast('다른 Tag 에서 한 작업입니다 — 그 Tag 를 열고 되돌리세요', 1);
    from.pop();
    const body = op.t === 'update' ? (cmd === 'undo' ? op.before : op.after)
      : ((op.t === 'create') === (cmd === 'undo')) ? { delete: true } : { restore: true };
    try { S.ds = await api('PUT', `/comments/${op.id}`, body); S.issues = null; to.push(op); toast(cmd === 'undo' ? '되돌렸습니다' : '다시 했습니다'); }
    catch (e) { toast(e.message, 1); }
    paintDsOverlays(); drawRight(); return;
  }
  if (!c) return toast('먼저 표시를 선택하세요 (⬚ 선택 도구)');
  if (cmd === 'del') {
    try { S.ds = await api('PUT', `/comments/${c.id}`, { delete: true }); S.issues = null; pushUndo({ t: 'delete', id: c.id, ds: S.ds.id }); W.selCm = null; toast('지웠습니다 — Ctrl+Z 되돌리기'); }
    catch (e) { toast(e.message, 1); }
    paintDsOverlays(); drawRight();
  } else if (cmd === 'edit') {
    const r = await markText('Mark-up 의견 고치기', c.kind || 'rect', c.text, c.category || 'comment');
    if (!r) return;
    await changeMark({ id: c.id }, { text: r.text, category: r.category }, { text: c.text, category: c.category || 'comment' });
  }
}
async function exportMarkup() {
  toast('Mark-up PDF 를 만드는 중…');
  try { await download(`/projects/${S.pid}/markup.pdf?tag=${encodeURIComponent(S.ds.tag_key)}`); toast('내려받음 — 원본은 그대로, 번호 붙은 표시 + Issue Summary 쪽 (인쇄하면 표시도 같이 나옵니다)'); }
  catch (e) { toast(e.message, 1); }
}
async function openPmsRef(page, bbox) {               // PMS reference page in a pop-up viewer beside the datasheet
  const doc = S.ds?.pms_doc || S.pmsDoc; if (!doc) return;
  $('#mTitle').textContent = `PMS ${doc.filename} · p.${page}`; $('#mAct').innerHTML = '<button>닫기</button>';
  $('#mBody').innerHTML = '<div id="pmsv" style="height:70vh;display:flex;flex-direction:column;background:#525a68"></div>';
  $('.mbox').style.width = 'min(1000px,94vw)'; $('#modal').hidden = false;
  $('#mAct button').onclick = () => { $('#modal').hidden = true; $('.mbox').style.width = ''; };
  const v = new Viewer($('#pmsv')); await v.load(doc.id, [page]); v.fit(); if (bbox) v.focus(page, bbox, 'PMS');
}
/* MOCK helpers — deterministic so the same tag always shows the same example */
const mockBtn = () => `<button data-mock="1">${SHOWMOCK ? '예시 끄기 (판정 숨김)' : 'MOCK 예시 판정 보기'}</button>`;
document.addEventListener('click', e => { if (e.target.closest('[data-mock]')) { SHOWMOCK = !SHOWMOCK; RENDER[S.view]?.(); if (S.view === 'review') drawRight(); } });
function mockProc(v, i) {
  if (!SHOWMOCK) return { pv: 'Phase 3 연결 전', r: v ? 'Not Evaluated' : 'Missing in Datasheet' };
  if (!v) return { pv: '—', r: 'Missing in Datasheet' };
  if (i % 5 === 3) return { pv: String(v).replace(/\d+(\.\d+)?/, n => (+n * 1.1).toFixed(1)), r: 'Mismatch' };
  return { pv: v, r: 'Match' };
}

/* ── 5. Revision Comparison ───────────────────────────────────────────── */
const RC = { flt: LS.get('rcflt', { Modified: true, Added: true, Deleted: true, Unchanged: false }), hl: new Set(), mock: false };
async function renderRev() {
  const el = $('#v-rev'), multi = S.sum.tags.filter(t => t.revs.length > 1);
  if (!RC.mock && !multi.length) {
    el.classList.remove('full');
    el.innerHTML = `<div class="vh"><h2>Revision Comparison</h2></div><div class="card"><div class="empty">Revision 이 2개 이상인 Tag 가 아직 없습니다.<br>
      새 Revision Datasheet PDF 를 <b>Document Management</b> 에 올리면 같은 Tag 끼리 자동으로 연결해 칸별로 비교합니다 (Added · Deleted · Modified).<br><br>
      <button id="rcmock">${MOCK} 예시로 화면 보기</button></div></div>`;
    $('#rcmock').onclick = () => { RC.mock = true; renderRev(); };
    return;
  }
  el.classList.add('full');
  let prev, cur, rows;
  if (RC.mock && !multi.length) {
    const t = S.sum.tags.find(t => t.id === S.dsId) || S.sum.tags[0], d = await api('GET', `/datasheets/${t.id}`);
    const pick = ['body_size', 'rating', 'seat_material', 'fire_safe', 'nace'].map(k => d.fields.find(f => f.key === k)).filter(Boolean);
    rows = d.fields.map(f => ({ key: f.key, display: f.display, previous: f.value, new: f.value, unit: f.unit, change: 'Unchanged', prev_page: f.page, prev_bbox: f.bbox, new_page: f.page, new_bbox: f.bbox }));
    pick.forEach((f, i) => { const r = rows.find(r => r.key === f.key); r.previous = i === 0 ? String(f.value).replace(/\d+/, n => Math.max(1, n - 2)) : i === 3 ? '' : 'MOCK-OLD'; r.change = i === 3 ? 'Added' : 'Modified'; });
    prev = { ...d, rev: d.rev + ' (MOCK prev)' }; cur = d;
  } else {
    const t = multi.find(t => t.id === S.dsId) || multi[0];
    const revs = (await api('GET', `/datasheets/${t.id}`)).revisions;
    const ni = RC.newId && revs.some(r => r.id === RC.newId) ? RC.newId : revs.at(-1).id;
    const pi = RC.prevId && revs.some(r => r.id === RC.prevId) && RC.prevId !== ni ? RC.prevId : revs[revs.findIndex(r => r.id === ni) - 1]?.id ?? revs[0].id;
    const c = await api('GET', `/compare?prev=${pi}&new=${ni}`);
    prev = c.prev; cur = c.new; rows = c.rows; RC.revs = revs; RC.tag = t;
  }
  RC.rows = rows;
  if (!RC.hl.size) rows.forEach((r, i) => { if (r.change !== 'Unchanged') RC.hl.add(i); });
  el.innerHTML = `<div class="rc"><div class="rc-top"><div class="rc-side" id="rcL"></div><div class="rc-side" id="rcR"></div>
      <div class="rc-opts"><b>Highlight Options</b>${['Modified', 'Added', 'Deleted', 'Unchanged'].map(k => `<label><input type="checkbox" data-f="${k}" ${RC.flt[k] ? 'checked' : ''}> ${pill(k)}</label>`).join('')}
        <hr style="width:100%;border:0;border-top:1px solid var(--line)"><button class="pri" id="rcapply">Apply Highlight</button><button id="rcnone">Highlight 모두 끄기</button>
        <button id="rcpdf">⇩ Export Mark-up PDF</button>${RC.mock ? `<p>${MOCK} 예시 비교 — 같은 PDF 의 값 몇 개를 바꿔 만든 화면입니다.</p><button id="rcreal">예시 끄기</button>` : ''}</div></div>
    <div class="rc-bottom"><div class="hd"><b>Changes Summary</b>${RC.mock ? '' : `<select id="rctag">${multi.map(t => `<option value="${t.id}" ${t.id === RC.tag.id ? 'selected' : ''}>${esc(t.tag_key)}</option>`).join('')}</select>
      Prev <select id="rcp">${RC.revs.map(r => `<option value="${r.id}" ${r.id === prev.id ? 'selected' : ''}>Rev.${esc(r.rev)}</option>`).join('')}</select>
      New <select id="rcn">${RC.revs.map(r => `<option value="${r.id}" ${r.id === cur.id ? 'selected' : ''}>Rev.${esc(r.rev)}</option>`).join('')}</select>`}
      <span class="soft">${['Modified', 'Added', 'Deleted'].map(k => `${k} ${rows.filter(r => r.change === k).length}`).join(' · ')}</span></div>
      <div class="bd"><table class="t"><thead><tr><th style="width:30px">HL</th><th>Changed Field</th><th>Previous Value (Rev.${esc(prev.rev)})</th><th>New Value (Rev.${esc(cur.rev)})</th><th>Change Type</th><th>PDF Page</th><th>Review Status</th></tr></thead><tbody id="rcrows"></tbody></table></div></div></div>`;
  const L = new Viewer($('#rcL'), { extra: `<span class="lbl">Rev.${esc(prev.rev)}</span>` }), R = new Viewer($('#rcR'), { extra: `<span class="lbl">Rev.${esc(cur.rev)}</span>` });
  await Promise.all([L.load(prev.document_id, prev.pages), R.load(cur.document_id, cur.pages)]);
  RC.L = L; RC.R = R;
  const draw = () => {
    const vis = rows.map((r, i) => [r, i]).filter(([r]) => RC.flt[r.change]);
    $('#rcrows').innerHTML = vis.map(([r, i]) => `<tr class="click" data-i="${i}"><td><input type="checkbox" data-h="${i}" ${RC.hl.has(i) ? 'checked' : ''} aria-label="highlight"></td><td>${esc(r.display)}</td>
      <td class="${r.change !== 'Unchanged' ? 'chg-old' : ''}">${esc(r.previous)}</td><td>${r.change !== 'Unchanged' ? `<b>${esc(r.new)}</b>` : esc(r.new)}</td><td>${pill(r.change)}</td><td>${r.new_page || r.prev_page || ''}</td>
      <td>${pill(S.sum.tags.find(t => t.id === cur.id)?.review_status || 'Not Reviewed')}</td></tr>`).join('') || '<tr><td colspan="7" class="empty">조건에 맞는 칸이 없습니다</td></tr>';
    const mk = side => rows.map((r, i) => [r, i]).filter(([r, i]) => RC.hl.has(i) && RC.flt[r.change] && r.change !== 'Unchanged')
      .map(([r]) => ({ cat: 'revision', page: side === 'L' ? r.prev_page : r.new_page, bbox: side === 'L' ? r.prev_bbox : r.new_bbox, title: `${r.change}: ${r.display}`, text: `${r.previous} → ${r.new}` })).filter(o => o.bbox);
    L.setOverlays(mk('L')); R.setOverlays(mk('R'));
  };
  draw();
  $('#rcrows').onclick = e => {
    const h = e.target.closest('[data-h]'); if (h) { h.checked ? RC.hl.add(+h.dataset.h) : RC.hl.delete(+h.dataset.h); draw(); return; }
    const tr = e.target.closest('tr[data-i]'); if (!tr) return; const r = rows[+tr.dataset.i];
    if (r.prev_bbox) L.focus(r.prev_page, r.prev_bbox, r.display); if (r.new_bbox) R.focus(r.new_page, r.new_bbox, r.display);
  };
  $$('.rc-opts [data-f]').forEach(c => c.onchange = () => { RC.flt[c.dataset.f] = c.checked; LS.set('rcflt', RC.flt); draw(); });
  $('#rcapply').onclick = () => { rows.forEach((r, i) => { if (RC.flt[r.change] && r.change !== 'Unchanged') RC.hl.add(i); }); draw(); };
  $('#rcnone').onclick = () => { RC.hl.clear(); draw(); };
  $('#rcpdf').onclick = async () => {
    const items = R.ovs.filter(o => o.cat === 'revision').map(o => ({ ...o, category: 'revision', title: `Revision Change · ${o.title}` }));
    try { await download('/markup.pdf', 'POST', { document_id: cur.document_id, pages: cur.pages, items }); toast(`노란 표시 ${items.length}개 PDF`); } catch (e) { toast(e.message, 1); }
  };
  $('#rcreal') && ($('#rcreal').onclick = () => { RC.mock = false; RC.hl.clear(); renderRev(); });
  if (!RC.mock) {
    $('#rctag').onchange = e => { S.dsId = +e.target.value; RC.prevId = RC.newId = null; RC.hl.clear(); renderRev(); };
    $('#rcp').onchange = e => { RC.prevId = +e.target.value; RC.hl.clear(); renderRev(); };
    $('#rcn').onchange = e => { RC.newId = +e.target.value; RC.hl.clear(); renderRev(); };
  }
}

/* ── 6 · 7. Process Data / PMS (Phase 3 · 4 — MOCK reference values) ──── */
async function allFields(limit = 60) {
  return Promise.all(S.sum.tags.slice(0, limit).map(t => api('GET', `/datasheets/${t.id}`)));
}
async function renderProc() {
  const el = $('#v-proc'); el.classList.remove('full');
  el.innerHTML = `<div class="vh"><h2>Process Data Verification</h2>${MOCK}<span class="sp"></span><select id="ptag">${S.sum.tags.map(t => `<option value="${t.id}" ${t.id === S.dsId ? 'selected' : ''}>${esc(t.tag_key)}</option>`).join('')}</select></div>
    <div class="banner">Phase 3 엔진(Process Data PDF/Excel 읽기 · 단위 환산 · Tag 연결)은 아직 연결 전입니다. <b>Datasheet 값 · 쪽 · 위치는 실제</b>입니다. 근거 없는 판정을 만들지 않도록 결과는 'Not Evaluated' 로 두고, 화면 확인용 예시는 ${mockBtn()} 으로만 봅니다.
      절대압(bar a)과 게이지압(barg)은 대기압 보정 없이 비교하지 않고, 단위가 불명확하면 Review Required 로 둡니다 (설계 §6).</div><div id="pbody"></div>`;
  const draw = async () => {
    const d = await api('GET', `/datasheets/${$('#ptag').value}`);
    const pf = d.fields.filter(f => f.section === 'process' && !NOT_PROCESS.has(f.key));
    const ex = d.fields.filter(f => ['body_size', 'rating', 'body_material', 'ball_material', 'seat_material'].includes(f.key));
    $('#pbody').innerHTML = `<div class="card"><table class="t"><thead><tr><th>#</th><th>Parameter</th><th>Process Data ${MOCK}</th><th>Datasheet</th><th>Unit</th><th>Result</th><th>PDF Page</th></tr></thead><tbody>
      ${pf.map((f, i) => { const v = f.edited_value ?? f.value, m = mockProc(v, i); return `<tr class="click" data-g="${d.id}"><td>${i + 1}</td><td>${esc(f.display)}</td><td>${esc(m.pv)}</td><td>${esc(v || 'Not Found')}</td><td>${esc(f.unit)}</td><td>${pill(m.r.replace(/ /g, ''), m.r)}</td><td>${f.page}</td></tr>`; }).join('')}
      </tbody></table></div><div class="card" style="margin-top:12px;background:#fafbfc"><h3>Excluded Parameters — Process Data 검증 대상 아님</h3><table class="t"><tbody>
      ${ex.map(f => `<tr><td>${esc(f.display)}</td><td>${esc(f.edited_value ?? f.value)}</td><td>${pill('Excluded', 'N/A (Excluded)')}</td></tr>`).join('')}</tbody></table>
      <p class="soft">Valve Size · Valve Rating · Material 은 Process Data Verification 엔진이 비교하지 않습니다 (Mechanical 정보는 Datasheet 와 PMS 기준).</p></div>`;
    $$('#pbody tr[data-g]').forEach(tr => tr.onclick = () => openDs(+tr.dataset.g));
  };
  $('#ptag').onchange = draw; draw();
}
async function renderPms() {
  const el = $('#v-pms'); el.classList.add('full');
  if (!S.sum.has_pms) { el.classList.remove('full'); el.innerHTML = `<div class="vh"><h2>PMS Compliance</h2></div><div class="card"><div class="empty">PMS(Piping Material Specification) PDF 가 아직 없습니다.<br>Document Management 에 올리면 Class 시트(Rating · NACE · Valve Trim · Ball Valve 품목)를 읽어 모든 Tag 를 비교합니다.</div></div>`; return; }
  if (!S.pmsRows) { el.innerHTML = '<div class="empty">PMS 와 비교하는 중…</div>'; const r = await api('GET', `/projects/${S.pid}/pms`); S.pmsRows = r.rows; S.pmsDoc = r.pms_doc; }
  const P = S.pmsF ||= { res: '', q: '', item: '' };
  const q = P.q.toUpperCase().replace(/[^0-9A-Z]/g, '');
  const L = S.pmsRows.filter(r => (!P.res || r.result === P.res) && (!P.item || r.item === P.item) && (!q || r.tag.includes(q)));
  const cnt = x => S.pmsRows.filter(r => r.result === x).length;
  el.innerHTML = `<div style="display:flex;flex-direction:column;width:100%;height:100%"><div style="padding:10px 14px 6px;background:var(--bg)"><div class="vh" style="margin:0">
      <h2>PMS Compliance</h2><span class="soft">${esc(S.pmsDoc?.filename || '')}</span>
      ${['Non-Compliant', 'Review Required', 'Not Defined in PMS', 'Compliant'].map(x => `<button data-pr="${x}" class="${P.res === x ? 'pri' : ''}">${pill(x.replace(/[^A-Za-z]/g, ''), x)} ${cnt(x)}</button>`).join('')}
      <select id="pi"><option value="">All Items</option>${[...new Set(S.pmsRows.map(r => r.item))].map(x => `<option ${x === P.item ? 'selected' : ''}>${esc(x)}</option>`).join('')}</select>
      <input type="search" id="pq" placeholder="Tag 검색" value="${esc(P.q)}" style="width:140px"><span class="soft">${L.length}행 · 재질은 규격·등급으로 비교 (표기 차이 무시)</span></div></div>
    <div style="flex:1;min-height:0;overflow:auto;padding:0 14px"><table class="t"><thead><tr><th>Tag Number</th><th>Area</th><th>Piping Material Class</th><th>Item</th><th>PMS Requirement</th><th>Datasheet Value</th><th>Compliance Result</th><th>Reason</th><th>PMS Ref. Page</th><th>DS Ref. Page</th></tr></thead><tbody>
      ${L.slice(0, 3000).map((r, n) => `<tr class="click" data-n="${S.pmsRows.indexOf(r)}"><td><b>${esc(r.tag)}</b></td><td>${esc(r.area || '?')}</td><td>${esc(r.class)}</td><td>${esc(r.item)}</td><td>${esc(r.req)}</td><td>${esc(r.ds)}</td>
        <td>${pill(r.result.replace(/[^A-Za-z]/g, ''), r.result)}</td><td class="soft">${esc(r.reason)}</td><td>${r.pms_page || '—'}</td><td>${r.ds_page || ''}</td></tr>`).join('') || '<tr><td colspan="10" class="empty">없음</td></tr>'}</tbody></table></div>
    <div style="height:42%;min-height:200px;display:flex;border-top:3px solid #1d2330"><div class="rc-side" id="pmL"></div><div class="rc-side" id="pmR"></div></div></div>`;
  const L1 = new Viewer($('#pmL'), { extra: '<span class="lbl">Datasheet</span>' }), R1 = new Viewer($('#pmR'), { extra: '<span class="lbl">PMS</span>' });
  $$('[data-pr]', el).forEach(b => b.onclick = () => { P.res = P.res === b.dataset.pr ? '' : b.dataset.pr; renderPms(); });
  $('#pi').onchange = e => { P.item = e.target.value; renderPms(); };
  $('#pq').oninput = e => { P.q = e.target.value; clearTimeout(P.t); P.t = setTimeout(() => { renderPms().then(() => { const f = $('#pq'); f.focus(); f.setSelectionRange(f.value.length, f.value.length); }); }, 300); };
  $$('tr[data-n]', el).forEach(tr => tr.onclick = async () => {        // both references at once
    $$('tr.sel', el).forEach(x => x.classList.remove('sel')); tr.classList.add('sel');
    const r = S.pmsRows[+tr.dataset.n], pages = (await api('GET', `/datasheets/${r.ds_id}`)).pages;
    await L1.load(r.document_id, pages); L1.fit();
    L1.setOverlays([{ cat: r.result === 'Non-Compliant' ? 'error' : r.result === 'Compliant' ? 'comment' : 'missing', page: r.ds_page, bbox: r.ds_bbox, title: r.item }]);
    if (r.ds_bbox) L1.focus(r.ds_page, r.ds_bbox, r.item);
    if (r.pms_page) { await R1.load(S.pmsDoc.id, [r.pms_page]); R1.fit(); R1.setOverlays([]); if (r.pms_bbox) R1.focus(r.pms_page, r.pms_bbox, 'PMS'); }
  });
}
/* ── 8. Reports & Export · 9. Settings ─────────────────────────────────── */
async function renderExport() {
  const el = $('#v-export'); el.classList.remove('full');
  const vl = S.sum.documents.find(d => d.kind === 'valvelist' && d.status === 'done');
  el.innerHTML = `<div class="vh"><h2>Reports &amp; Export</h2></div><div class="grid2">
    <div class="card"><h3>Valve List (Excel)</h3><p>${vl ? `기준 양식: <b>${esc(vl.filename)}</b> — 시트·열 순서·병합·서식·필터를 그대로 두고 채웁니다.` : '<b>기준 Valve List 가 없습니다</b> — 도구 기본 양식(Valve List (tool format))으로 만듭니다. 회사 양식을 쓰려면 Document Management 에 올리세요.'}</p>
      <ul class="soft"><li>같은 Tag: 바뀐 칸만 덮고 노란색 + 'Previous:' 메모</li><li>새 Tag: 밸브 종류 시트 끝에 첫 블록 서식으로 추가 (Tool Status = NEW)</li>
      <li>'VTA' · 'General note - 3' 처럼 목록보다 덜 말하는 값은 덮지 않고 메모만</li><li>모든 칸에 출처(파일·쪽·행) 메모 · 오른쪽에 DS Doc No. · Rev. · Notes · Tool Status 열 · 'Datasheet Notes' 시트</li></ul>
      <button class="pri" id="ex1">⇩ Valve List 내려받기</button> <button id="ex1p">미리 보기 (바뀔 칸)</button><div id="ex1r"></div></div>
    <div class="card"><h3>Extracted Data · Audit Trail</h3><p>모든 Tag 의 추출 칸(읽은 값 · 수정 값 · 수정자 · 상태 · 쪽 · 파일)을 CSV 로.</p>
      <button id="ex2">⇩ Extracted Fields CSV</button> <button id="ex3">⇩ Audit Trail CSV</button>
      <h3 style="margin-top:14px">검토 피드백 (개발 쪽으로 보내기)</h3><p class="soft">검토자가 Issue 를 Confirmed / Dismissed 한 것, 고친 값, 도구가 못 잡아 직접 그린 Error · Missing 표시를 한 파일로.
      개발 쪽은 이것으로 규칙마다 맞은 비율 · 잘못 읽은 칸 · 놓친 것을 재고 고칩니다 (도구의 판정 규칙은 이 파일을 읽지 않습니다). 고객 값이 들어 있으니 사내 경로로만 보내세요.</p>
      <button id="ex6">⇩ Review Feedback (json)</button>
      <h3 style="margin-top:14px">Mark-up PDF</h3><p class="soft">Datasheet Review 화면 PDF 도구줄의 <b>⇩ Mark-up PDF</b> (그 Tag 의 주석 · Revision 변경 표시), Revision Comparison 의 <b>Export Mark-up PDF</b>.
      원본은 그대로 두고 별도 파일로 만듭니다.</p></div>
    <div class="card"><h3>설계사 전달 — 지적 사항 (Issue List · Mark-up)</h3><p>오류 · 누락 · HOLD/TBC · PMS 부적합 · Revision 변경 · 검토자 수정/의견. 각 행에 Tag · Doc. No. · Rev. · Sheet · PDF Page · 무엇이 문제인지 · 요구값.
      Dismissed 는 빠집니다. 색: <b style="color:var(--pms)">빨강</b> 오류/PMS · <b style="color:var(--proc)">주황</b> 누락/HOLD · <b style="color:#b38f00">노랑</b> Revision · <b style="color:var(--usr)">파랑</b> 검토자.</p>
      <button class="pri" id="ex4">⇩ Issue List Excel</button> <button id="ex5">⇩ Mark-up PDF (전체 · 인쇄용)</button> <button data-go="list:issues">Issue List 화면</button></div>
    <div class="card"><h3>분석할 때 자동으로 만든 파일</h3><div id="exl" class="soft">불러오는 중…</div></div></div>`;
  $('#ex1').onclick = exportValveList;
  $('#ex4').onclick = () => download(`/projects/${S.pid}/issues.xlsx`).then(r => toast(`Issue List ${r.headers.get('X-Count')}행`)).catch(e => toast(e.message, 1));
  $('#ex5').onclick = () => { toast('Mark-up PDF 를 만드는 중… (전체는 1분 안팎)'); download(`/projects/${S.pid}/markup.pdf`).then(() => toast('내려받음')).catch(e => toast(e.message, 1)); };
  api('GET', `/projects/${S.pid}/exports`).then(r => { $('#exl').innerHTML = r.files.map(f => `<div><a href="${f.url}" download>${esc(f.name)}</a> <span class="soft">${(f.size / 1024).toFixed(0)} KB · ${esc(f.at.replace('T', ' '))}</span></div>`).join('') || '아직 없습니다 — Datasheet PDF 를 분석하면 Valve List · Issue List 가 함께 만들어집니다'; });
  $('#ex1p').onclick = async () => {
    $('#ex1r').innerHTML = '<p class="soft">계산 중…</p>';
    const p = await api('GET', `/projects/${S.pid}/valvelist/preview`), r = p.report;
    $('#ex1r').innerHTML = `<p>갱신 ${r.updated.length} · 신규 ${r.new.length} · 변화 없음 ${r.unchanged.length} · 데이터시트 없음 ${r.not_in_datasheets.length} · 바뀐 칸 <b>${r.changes.length}</b> · 목록 값 유지 ${r.kept.length}</p>
      <div style="max-height:320px;overflow:auto"><table class="t"><thead><tr><th>Tag</th><th>Column</th><th>Previous</th><th>New</th></tr></thead><tbody>
      ${r.changes.slice(0, 400).map(c => `<tr><td>${esc(c.tag)}</td><td>${esc(c.column)}</td><td class="chg-old">${esc(c.previous.slice(0, 80))}</td><td>${esc(String(c.new).slice(0, 80))}</td></tr>`).join('')}</tbody></table></div>`;
  };
  $('#ex2').onclick = () => download(`/projects/${S.pid}/extracted.csv`).catch(e => toast(e.message, 1));
  $('#ex6').onclick = () => download(`/projects/${S.pid}/feedback.json`).then(() => toast('내려받음 — 개발 세션에 전달하면 규칙 정확도를 잽니다')).catch(e => toast(e.message, 1));
  $('#ex3').onclick = async () => {
    const a = (await api('GET', `/projects/${S.pid}/audit`)).audit;
    const csv = '﻿' + [['When', 'Who', 'Tag', 'Rev', 'Action', 'Field', 'Before', 'After', 'Comment']].concat(a.map(x => [x.at, x.by, x.tag, x.rev, x.action, x.field_key, x.before, x.after, x.comment]))
      .map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n');
    const u = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })), l = document.createElement('a'); l.href = u; l.download = 'audit_trail.csv'; l.click(); setTimeout(() => URL.revokeObjectURL(u), 3000);
  };
}
function renderSettings() {
  const el = $('#v-settings'); el.classList.remove('full');
  el.innerHTML = `<div class="vh"><h2>Settings</h2></div><div class="grid2"><div class="card"><h3>사용자 · 화면</h3>
      <p>이름: <b>${esc(USER || '(없음 — 대시보드에서 열면 로그인 이름이 자동으로 넘어옵니다)')}</b></p>
      ${Q.get('user') ? '' : `<p><input id="sname" placeholder="이름 (대시보드 밖에서 열 때만)" value="${esc(LS.get('user', ''))}"> <button id="ssave">저장</button></p>`}
      <p><button id="sreset">패널 너비 · 열 순서 · 확대 처음대로</button></p></div>
    <div class="card"><h3>단축키 (Datasheet Review)</h3><table class="t"><tbody>
      ${[['↑ / ↓ 또는 K / J', '이전 / 다음 Tag'], ['PgUp / PgDn', '이전 / 다음 쪽'], ['+ / −', '확대 / 축소'], ['/', 'Tag 검색'], ['F', 'PDF 검색'], ['A', '주석 상자 그리기'], ['Esc', '그리기 취소 · 창 닫기'], ['1 … 9', '왼쪽 메뉴 이동']]
        .map(([k, v]) => `<tr><td><kbd>${k}</kbd></td><td>${v}</td></tr>`).join('')}</tbody></table></div>
    <div class="card"><h3>원칙</h3><ul class="soft"><li>Tag Number 가 모든 문서의 연결 키입니다 (공백 · 하이픈 무시: 00XV 921 = 00XV-921 = 00XV921).</li>
      <li>추출은 PDF 글자층과 표 괘선만으로 합니다 (OCR · AI 추정 없음). 짝이 불확실한 칸은 Review Required.</li>
      <li>원본 파일은 덮어쓰지 않고, 수정은 읽은 값 옆에 수정자 · 시각과 함께 남습니다.</li><li>최종 판정 · 승인은 사용자가 합니다.</li></ul></div>
    <div class="card"><h3>정보</h3><p>Module 01 — Ball Valve (On/Off · MOV) Datasheet Review · Phase 1 (+ Revision 비교 기본)<br>서버: P&amp;ID 서버 /valve · 데이터: pid_data/valve/</p></div></div>`;
  $('#ssave') && ($('#ssave').onclick = () => { LS.set('user', $('#sname').value.trim()); location.reload(); });
  $('#sreset').onclick = () => { ['wbw', 'gorder', 'gw', 'zoom'].forEach(k => LS.set(k, null)); toast('처음대로 — 화면을 다시 엽니다'); setTimeout(() => location.reload(), 600); };
}
const RENDER = { dash: renderDash, docs: renderDocs, list: renderList, review: renderReview, rev: renderRev, proc: renderProc, pms: renderPms, export: renderExport, settings: renderSettings };
for (const k of Object.keys(RENDER)) { const f = RENDER[k]; RENDER[k] = () => { if (!S.sum) return; Promise.resolve(f()).catch(e => { console.error(e); toast(e.message, 1); }); }; }

/* ── keyboard ─────────────────────────────────────────────────────────── */
addEventListener('keydown', e => {
  if (e.key === 'Escape') { $('#modal').hidden = true; W.viewer?.setTool('select'); return; }
  if (e.target.closest('input, textarea, select') || !$('#modal').hidden || e.altKey) return;
  if (S.view === 'review' && W.viewer && (e.ctrlKey || e.metaKey)) {
    const k = e.key.toLowerCase();
    if (k === 'z' && !e.shiftKey) { e.preventDefault(); markCmd('undo'); } else if (k === 'y' || (k === 'z' && e.shiftKey)) { e.preventDefault(); markCmd('redo'); }
    return;
  }
  if (e.ctrlKey || e.metaKey) return;
  const MKKEY = { v: 'select', r: 'rect', c: 'cloud', e: 'ellipse', h: 'highlight', l: 'line', w: 'arrow', p: 'pen', t: 'text', n: 'note', a: 'rect' };
  if (S.view === 'review' && W.viewer && MKKEY[e.key]) { W.viewer.setTool(MKKEY[e.key]); return; }
  if (S.view === 'review' && W.viewer && W.selCm && (e.key === 'Delete' || e.key === 'Backspace')) { e.preventDefault(); markCmd('del'); return; }
  if (S.view === 'review' && W.viewer && W.selCm && e.key === 'Enter') { e.preventDefault(); markCmd('edit'); return; }
  if (/^[1-9]$/.test(e.key)) { go(VIEWS[+e.key - 1]); return; }
  if (S.view !== 'review' || !W.viewer) return;
  const list = W.list || [], i = list.findIndex(t => t.id === S.dsId);
  if (e.key === 'ArrowDown' || e.key === 'j') { e.preventDefault(); list[i + 1] && openDs(list[i + 1].id); }
  else if (e.key === 'ArrowUp' || e.key === 'k') { e.preventDefault(); list[i - 1] && openDs(list[i - 1].id); }
  else if (e.key === 'PageDown') { e.preventDefault(); W.viewer.step(1); }
  else if (e.key === 'PageUp') { e.preventDefault(); W.viewer.step(-1); }
  else if (e.key === '+' || e.key === '=') W.viewer.setZoom(W.viewer.zoom * 1.2);
  else if (e.key === '-') W.viewer.setZoom(W.viewer.zoom / 1.2);
  else if (e.key === '/') { e.preventDefault(); $('#wq').focus(); }
  else if (e.key === 'f') { e.preventDefault(); $('#wview .q').focus(); }
});

/* ── start ────────────────────────────────────────────────────────────── */
if (EMBED) document.body.classList.add('embed');
$('#who').innerHTML = `<b>${esc((USER || '?').slice(0, 1))}</b>${esc(USER || '이름 없음')}`;
loadProjects().then(async () => {
  const ds = +Q.get('ds');                              // deep link from the Excel lists: ?ds=…&key=…&page=…#review
  if (ds) {
    S.dsId = ds; LS.set('tag.' + S.pid, ds); go('review', false);
    const key = Q.get('key'), page = +Q.get('page');
    for (let n = 0; n < 40 && !(S.ds && S.ds.id === ds); n++) await new Promise(r => setTimeout(r, 150));
    if (key && S.ds?.fields.some(f => f.key === key)) selectField(key);
    else if (key && S.ds?.issues?.some(i => i.key === key)) { const i = S.ds.issues.find(x => x.key === key); W.selIss = i.ikey; setTab('iss'); paintDsOverlays(); if (i.bbox) W.viewer.focus(i.page, i.bbox, i.field); }
    else if (page) W.viewer?.goPage(page);
    return;
  }
  go((location.hash.slice(1) || LS.get('view', 'dash')).split('?')[0], false);
})
  .catch(e => { document.querySelector('#views').innerHTML = `<div class="empty" style="color:var(--bad)">${esc(e.message)}</div>`; });
})();
