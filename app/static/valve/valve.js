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
    this.ovs = []; this.show = Object.assign({ revision: true, pms: true, process: true, comment: true }, LS.get('ovshow', {}));
    host.innerHTML = `<div class="tbar">
      <button data-a="prev" title="이전 쪽 (PgUp)">◀</button><input class="pno" value="1" aria-label="쪽"><span class="lbl tot">/ 0</span>
      <button data-a="next" title="다음 쪽 (PgDn)">▶</button><span class="sep"></span>
      <button data-a="out" title="축소 (-)">−</button><span class="lbl zl">100%</span><button data-a="in" title="확대 (+)">＋</button>
      <button data-a="fit" title="폭 맞춤">↔</button><span class="sep"></span>
      <input class="q" placeholder="PDF 검색" aria-label="PDF 검색"><button data-a="find" title="검색">⌕</button>
      <span class="sep"></span>${opts.tools ? `<button data-a="draw" title="주석 상자 그리기 (A)">▭ 주석</button><span class="sep"></span>` : ''}
      <span class="chk" title="표시 켜기/끄기"><label><input type="checkbox" data-c="revision"> <i style="background:var(--rev)"></i>Rev</label></span>
      <span class="chk"><label><input type="checkbox" data-c="pms"> <i style="background:var(--pms)"></i>PMS</label></span>
      <span class="chk"><label><input type="checkbox" data-c="process"> <i style="background:var(--proc)"></i>Proc</label></span>
      <span class="chk"><label><input type="checkbox" data-c="comment"> <i style="background:var(--usr)"></i>Comment</label></span>
      <span style="flex:1"></span>${opts.extra || ''}</div><div class="stage"></div>`;
    this.stage = $('.stage', host);
    $$('.chk input', host).forEach(i => { i.checked = this.show[i.dataset.c]; i.onchange = () => { this.show[i.dataset.c] = i.checked; LS.set('ovshow', this.show); this.paintOv(); }; });
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
    this.stage.addEventListener('mousedown', e => this.drawStart(e));
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
    this.paintOv();
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
  toggleDraw(on) {
    this.drawing = on ?? !this.drawing;
    this.stage.classList.toggle('drawing', this.drawing);
    $('[data-a="draw"]', this.host)?.classList.toggle('on', this.drawing);
    if (this.drawing) toast('PDF 위에서 끌어 주석 상자를 그리세요 (Esc 취소)');
  }
  drawStart(e) {
    if (!this.drawing || e.button !== 0) return;
    const pg = e.target.closest('.pg'); if (!pg) return;
    e.preventDefault();
    const r = pg.getBoundingClientRect(), x0 = e.clientX - r.left, y0 = e.clientY - r.top;
    const box = document.createElement('div'); box.className = 'draw'; pg.append(box);
    const move = ev => {
      const x = ev.clientX - r.left, y = ev.clientY - r.top;
      box.style.cssText = `left:${Math.min(x, x0)}px;top:${Math.min(y, y0)}px;width:${Math.abs(x - x0)}px;height:${Math.abs(y - y0)}px`;
    };
    const up = ev => {
      removeEventListener('mousemove', move); removeEventListener('mouseup', up); box.remove();
      const x = ev.clientX - r.left, y = ev.clientY - r.top, z = this.zoom * 1.3333;
      if (Math.abs(x - x0) < 6 || Math.abs(y - y0) < 6) return;
      const bb = [Math.min(x, x0) / z, Math.min(y, y0) / z, Math.max(x, x0) / z, Math.max(y, y0) / z].map(v => Math.round(v * 10) / 10);
      this.toggleDraw(false);
      this.opts.onDraw?.(+pg.dataset.p, bb);
    };
    addEventListener('mousemove', move); addEventListener('mouseup', up);
  }
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
  S.sum = await api('GET', `/projects/${S.pid}/summary`);
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
    ['Process Data Mismatch', null, '∿', '#ffe8d6', 'proc', 'Phase 3'], ['PMS Non-Compliant', null, '⛭', '#fbe3e1', 'pms', 'Phase 4'],
    ['Pending Review', k.pending, '◔', '#fff1d6', 'review'], ['Completed Review', k.completed, '✔', '#dcf3e5', 'review']];
  const by = {}; s.tags.forEach(t => { by[t.review_status] = (by[t.review_status] || 0) + 1; });
  const cols = { 'Not Reviewed': '#c4cad6', 'Under Review': '#f0a43a', Accepted: '#1aa35a', Rejected: '#d9443a', Commented: '#2f5bd8', Resolved: '#0f7a43' };
  el.innerHTML = `<div class="vh"><h2>Project Dashboard</h2><span class="soft">${esc(s.project.name)} · Ball Valve Datasheet</span><span class="sp"></span>
      <button data-go="docs">자료 올리기</button><button class="pri" data-go="review">Datasheet Review 열기</button></div>
    ${!k.datasheets ? `<div class="banner info">아직 데이터시트가 없습니다 — <b>Document Management</b> 에서 Datasheet PDF · Valve List · Process Data · PMS 를 올리세요.</div>` : ''}
    <div class="kpis">${tiles.map(([l, n, ic, bg, v, sub]) => `<div class="kpi" data-go="${v}" tabindex="0"><div class="ic" style="background:${bg}">${ic}</div>
      <div class="l">${l}</div><div class="n ${n === null ? 'na' : ''}">${n === null ? (sub || '—') + ' 연결 전' : n}</div></div>`).join('')}</div>
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
  const g = e.target.closest('[data-go]'); if (g && !e.target.closest('.tbar')) { go(g.dataset.go); return; }
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
      <td>${d.status === 'error' ? `<button data-retry="${d.id}">재처리</button>` : ''}${d.kind !== 'valvelist' ? ` <a href="/api/valve/documents/${d.id}/file" target="_blank">원본</a>` : ''}</td></tr>`).join('') || '<tr><td colspan="9" class="empty">아직 없습니다</td></tr>'}
    </tbody></table></div>`;
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
  $('#jobs')?.prepend(box);
  const tick = async () => {
    let j; try { j = await api('GET', `/jobs/${job.id}`); } catch (e) { box.innerHTML = `<b style="color:var(--bad)">${esc(e.message)}</b>`; return; }
    const pct = Math.round(100 * j.done / Math.max(1, j.total));
    box.innerHTML = `<b>처리 중</b> <span class="soft">${esc(j.file)} · ${esc(j.msg)}</span><div class="prog"><i style="width:${pct}%"></i></div>${pct}% (${j.done}/${j.total} 쪽)
      ${j.warn ? `<div style="color:var(--warn)">${esc(j.warn)}</div>` : ''}${j.errors.map(e => `<div style="color:var(--bad)">✖ ${esc(e.file)} — ${esc(e.error)}</div>`).join('')}`;
    if (j.status === 'done') {
      box.querySelector('b').textContent = j.errors.length ? '끝 (오류 있음 — 아래 표에서 재처리)' : '끝';
      await refresh(); setTimeout(() => box.remove(), j.errors.length ? 20000 : 5000);
    } else setTimeout(tick, 700);
  };
  tick();
}

/* ── 3. Valve List (Excel-like grid) ──────────────────────────────────── */
const G = { sort: LS.get('gsort', { k: 'tag', d: 1 }), flt: {}, sel: new Set(), last: null };
async function renderList() {
  const el = $('#v-list');
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
  el.innerHTML = `<div class="vh"><input type="search" id="gq" placeholder="Search Tag Number…" style="width:200px" value="${esc(keepQ)}">
      <select id="gt"><option value="">All Valve Types</option>${types.map(t => `<option ${t === keepT ? 'selected' : ''}>${esc(t)}</option>`).join('')}</select>
      <select id="gs"><option value="">All Status</option>${STATUSES.map(t => `<option ${t === keepS ? 'selected' : ''}>${t}</option>`).join('')}</select>
      <span class="soft">${rows.length} / ${S.grid.rows.length} rows · 선택 <b id="gsel">${G.sel.size}</b></span><span class="sp"></span>
      <select id="gbulk" ${G.sel.size ? '' : 'disabled'}><option value="">선택 행 상태 바꾸기…</option>${STATUSES.map(t => `<option>${t}</option>`).join('')}</select>
      <button id="greset" title="열 순서·너비 처음대로">열 초기화</button>
      <button id="gopen" ${G.sel.size ? '' : 'disabled'}>Open Datasheet</button><button class="pri" id="gx">⇩ Export Excel</button></div>
    <div class="xg-wrap"><table class="xg" id="xg" style="width:${70 + cols.reduce((a, c) => a + c.w, 0)}px"><colgroup><col style="width:30px"><col style="width:40px">${cols.map(c => `<col style="width:${c.w}px">`).join('')}</colgroup>
      <thead><tr><th class="fz" style="left:0"><input type="checkbox" id="gall" aria-label="전체 선택"></th><th class="fz" style="left:30px">#</th>${cols.map((c, i) => `<th draggable="true" data-k="${c.key}" ${i === 0 ? 'class="fz" style="left:70px"' : ''} title="${esc(c.title)} — 눌러 정렬 · 끌어 순서 바꾸기">${esc(c.title)}${G.sort.k === c.key ? (G.sort.d > 0 ? ' ▲' : ' ▼') : ''}<span class="rz"></span></th>`).join('')}</tr>
      <tr class="flt"><th class="fz" style="left:0"></th><th class="fz" style="left:30px"></th>${cols.map((c, i) => `<th ${i === 0 ? 'class="fz" style="left:70px"' : ''}><input data-f="${c.key}" value="${esc(G.flt[c.key] || '')}" placeholder="filter" aria-label="${esc(c.title)} filter"></th>`).join('')}</tr></thead>
      <tbody>${rows.map((r, n) => `<tr data-id="${r.id}" class="${G.sel.has(r.id) ? 'sel' : ''}"><td class="fz" style="left:0"><input type="checkbox" ${G.sel.has(r.id) ? 'checked' : ''} aria-label="선택"></td><td class="fz" style="left:30px">${n + 1}</td>
        ${cols.map((c, i) => {
          if (c.key === 'tag') return `<td class="fz" style="left:70px"><a class="tag" href="#review" data-open="${r.id}">${esc(r.tag)}</a></td>`;
          if (c.key === 'status') return `<td>${pill(r.status)}</td>`;
          if (c.key in r) return `<td>${esc(r[c.key])}</td>`;
          const x = r.cells[c.key]; if (!x) return '<td class="ph">—</td>';
          return `<td data-fid="${x.id}" data-k="${c.key}" class="${x.ed ? 'ed' : ''} ${x.st === 'placeholder' || x.st === 'blank' ? 'ph' : ''} ${x.st === 'review' ? 'rv' : ''}" title="${esc(x.v + (x.u ? ' ' + x.u : ''))}${x.ed ? ' (사용자 수정)' : ''} · p.${x.p} — 두 번 눌러 고치기">${esc(x.v || (x.st === 'blank' ? 'Not Found' : ''))}${x.u && x.v ? ' <small>' + esc(x.u) + '</small>' : ''}</td>`;
        }).join('')}</tr>`).join('')}</tbody></table></div>`;
  const wrap = $('.xg-wrap', el); wrap.scrollLeft = keepX; wrap.scrollTop = keepY;
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
    <div class="wb-right" style="width:${w.r}%"><div class="tabs" id="wtabs">${[['sum', 'Summary'], ['data', 'Datasheet Data'], ['proc', 'Process Data'], ['pms', 'PMS'], ['rev', 'Revision'], ['notes', 'Notes'], ['cmt', 'Comments'], ['hist', 'History']]
      .map(([k, l]) => `<button data-t="${k}" class="${W.tab === k ? 'on' : ''}">${l}</button>`).join('')}</div><div class="rbody" id="wbody"></div>
      <div class="statusbar" id="wstat"></div></div></div>`;
  W.viewer = new Viewer($('#wview'), { tools: true,
    extra: `<button data-a2="prevrev" title="이전 Revision">◁ Rev</button><button data-a2="nextrev" title="다음 Revision">Rev ▷</button><button data-a2="pdf" title="표시한 PDF 내보내기">⇩ Mark-up PDF</button>`,
    onDraw: addAnnot, onOverlay: o => { if (o.cmId) { W.selCm = o.cmId; setTab('cmt'); } else if (o.key) selectField(o.key); } });
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
      <span class="iss">${t.issues ? pill('review', '⚠ ' + t.issues) : ''}</span><small>${esc(t.valve_type)} · Rev.${esc(t.revs.join('→'))} · ${pill(t.review_status)}</small></div>`).join('')
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
  for (const c of S.ds.comments.filter(c => c.page && c.bbox)) ov.push({ cat: 'comment', page: c.page, bbox: c.bbox, title: `${c.by} · ${c.at}`, text: c.text, cmId: c.id, sel: W.selCm === c.id });
  for (const r of W.prevCmp?.rows || []) if (r.change !== 'Unchanged' && r.new_page && r.new_bbox) ov.push({ cat: 'revision', page: r.new_page, bbox: r.new_bbox, key: r.key, title: `${r.change}: ${r.display}`, text: `Rev.${W.prevCmp.prev.rev}: ${r.previous || '(blank)'}\nRev.${W.prevCmp.new.rev}: ${r.new || '(blank)'}` });
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
  if (W.tab === 'sum') {
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
    h = `<div class="banner">${MOCK} PMS 준수 검토 엔진(Phase 4)은 아직 연결 전입니다. Piping Class · Datasheet 값 · 위치는 실제입니다. 판정은 비워 두고, 예시는 버튼으로만 봅니다. ${mockBtn()}</div>
      <p>Piping Class <b>${esc(val('piping_class') || 'Not Found')}</b></p>
      <table class="t"><thead><tr><th>Item</th><th>PMS Requirement ${MOCK}</th><th>Datasheet</th><th>Result</th></tr></thead><tbody>
      ${mockPms(F).map(r => `<tr class="click" data-k="${esc(r.key)}"><td>${esc(r.item)}</td><td>${esc(r.req)}</td><td>${esc(r.ds)}</td><td>${pill(r.res.replace(/[^A-Za-z]/g, ''), r.res)}</td></tr>`).join('')}</tbody></table>`;
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
        <div style="display:flex;gap:6px;margin-top:4px"><button class="pri" id="cmadd">의견 남기기</button><button id="cmdraw">▭ PDF 위에 표시하며 남기기</button></div></div>
      ${d.comments.map(c => `<div class="cm ${W.selCm === c.id ? 'sel' : ''}" data-cm="${c.id}"><div class="h"><b>${esc(c.by)}</b><span>${esc(c.at.replace('T', ' ').slice(0, 16))}</span>${c.page ? `<a href="#" data-cmgo="${c.id}">p.${c.page} ▭</a>` : ''}<span class="sp"></span>
        <button data-cmed="${c.id}" title="고치기">✎</button><button data-cmdel="${c.id}" title="지우기">✕</button></div><div class="ct">${esc(c.text)}</div></div>`).join('') || '<div class="soft">아직 의견이 없습니다</div>'}`;
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
      if (r?.text) { S.ds = await api('PUT', `/comments/${c.id}`, { text: r.text }); paintDsOverlays(); drawRight(); } return; }
    const cd = e.target.closest('[data-cmdel]'); if (cd) { if (await modal('의견 지우기', '이 의견(과 PDF 표시)을 지울까요? 기록은 History 에 남습니다.', [['취소', 0], ['지우기', 1, 1]])) {
      S.ds = await api('PUT', `/comments/${cd.dataset.cmdel}`, { delete: true }); paintDsOverlays(); drawRight(); } return; }
    const k = e.target.closest('[data-k]'); if (k) selectField(k.dataset.k);
  };
  $('#cmadd') && ($('#cmadd').onclick = async () => { const t = $('#cmtx').value.trim(); if (!t) return;
    S.ds = await api('POST', `/datasheets/${d.id}/comments`, { text: t }); drawRight(); toast('의견을 남겼습니다'); });
  $('#cmdraw') && ($('#cmdraw').onclick = () => W.viewer.toggleDraw(true));
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
async function addAnnot(page, bbox) {
  const r = await modal('PDF 주석 (Engineering Comment)', `<p class="soft">p.${page} 에 표시합니다 (파란색).</p><textarea name="text" rows="4" placeholder="의견"></textarea>`, [['취소', null], ['남기기', 'form', 1]]);
  if (!r?.text) return;
  S.ds = await api('POST', `/datasheets/${S.ds.id}/comments`, { text: r.text, page, bbox });
  W.selCm = S.ds.comments.at(-1)?.id; setTab('cmt'); paintDsOverlays();
}
async function exportMarkup() {
  const items = W.viewer.ovs.filter(o => ['comment', 'revision'].includes(o.cat) && W.viewer.show[o.cat])
    .map(o => ({ page: o.page, bbox: o.bbox, category: o.cat, title: `${S.ds.tag} · ${o.cat === 'comment' ? 'Engineering Comment' : 'Revision Change'}`, text: o.text || o.title }));
  try { await download('/markup.pdf', 'POST', { document_id: S.ds.document_id, pages: S.ds.pages, items }); toast(`표시 ${items.length}개 — 원본은 그대로, 별도 파일로 내려받았습니다`); }
  catch (e) { toast(e.message, 1); }
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
function mockPms(F) {
  const rows = [['Body Material', 'body_material', 'ASTM A351 CF8M'], ['Trim (Ball) Material', 'ball_material', '316 SS / HF'], ['Stem Material', 'stem_material', '316 SS / HF'],
    ['Seat Material', 'seat_material', 'RTFE'], ['Gasket / Bolting', 'bolting_gasket', 'Spiral Wound 316 SS / Graphite'], ['Pressure Class', 'rating', '150#']];
  return rows.filter(([, k]) => F[k]).map(([item, key, req]) => {
    const ds = F[key].edited_value ?? F[key].value, n = s => String(s).toUpperCase().replace(/[^0-9A-Z]/g, '');
    if (!SHOWMOCK) return { item, key, req: 'Phase 4 연결 전', ds, res: 'Not Evaluated' };
    const res = !ds ? 'Review Required' : n(ds).includes(n(req)) || n(req).includes(n(ds)) ? 'Compliant' : /NOTE|VTA/i.test(ds) ? 'Review Required' : 'Non-Compliant';
    return { item, key, req, ds, res };
  });
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
  const el = $('#v-pms'); el.classList.remove('full');
  el.innerHTML = `<div class="vh"><h2>PMS Compliance</h2>${MOCK}<span class="soft">Reference: 98-98-PI-SPC-00001 (업로드 시)</span></div>
    <div class="banner">Phase 4 엔진(PMS Class 표 구조화 · Line No. → Class 연결 · ASTM 등급 비교)은 아직 연결 전입니다. Tag · Piping Class · Datasheet 값과 쪽은 실제입니다. 결과는 'Not Evaluated' 로 두고, 예시는 ${mockBtn()} 으로만 봅니다.
      동등 재질은 임의로 판정하지 않고 Review Required 로 둡니다.</div><div class="card"><div class="empty">불러오는 중…</div></div>`;
  const dss = await allFields(40);
  const rows = dss.flatMap(d => { const F = Object.fromEntries(d.fields.map(f => [f.key, f]));
    return mockPms(F).map(r => ({ ...r, d, pc: F.piping_class?.edited_value ?? F.piping_class?.value ?? '', page: F[r.key].page })); });
  $('.card', el).innerHTML = `<table class="t"><thead><tr><th>Tag Number</th><th>Piping Material Class</th><th>Item</th><th>PMS Requirement ${MOCK}</th><th>Datasheet Value</th><th>Compliance Result</th><th>PMS Ref. Page ${MOCK}</th><th>DS Ref. Page</th></tr></thead><tbody>
    ${rows.map(r => `<tr class="click" data-g="${r.d.id}"><td><b>${esc(r.d.tag_key)}</b></td><td>${esc(r.pc)}</td><td>${esc(r.item)}</td><td>${esc(r.req)}</td><td>${esc(r.ds)}</td><td>${pill(r.res.replace(/[^A-Za-z]/g, ''), r.res)}</td><td>—</td><td>${r.page}</td></tr>`).join('')}</tbody></table>
    <p class="soft">처음 40개 Tag 를 보여 줍니다. 행을 누르면 그 데이터시트의 해당 위치로 갑니다 (PMS 쪽 동시 열기는 Phase 4).</p>`;
  $$('#v-pms tr[data-g]').forEach(tr => tr.onclick = () => openDs(+tr.dataset.g));
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
      <h3 style="margin-top:14px">Mark-up PDF</h3><p class="soft">Datasheet Review 화면 PDF 도구줄의 <b>⇩ Mark-up PDF</b> (그 Tag 의 주석 · Revision 변경 표시), Revision Comparison 의 <b>Export Mark-up PDF</b>.
      원본은 그대로 두고 별도 파일로 만듭니다. 색: <span style="color:#b38f00">노랑 Revision</span> · <span style="color:var(--pms)">빨강 PMS</span> · <span style="color:var(--proc)">주황 Process</span> · <span style="color:var(--usr)">파랑 Comment</span>.</p></div></div>`;
  $('#ex1').onclick = exportValveList;
  $('#ex1p').onclick = async () => {
    $('#ex1r').innerHTML = '<p class="soft">계산 중…</p>';
    const p = await api('GET', `/projects/${S.pid}/valvelist/preview`), r = p.report;
    $('#ex1r').innerHTML = `<p>갱신 ${r.updated.length} · 신규 ${r.new.length} · 변화 없음 ${r.unchanged.length} · 데이터시트 없음 ${r.not_in_datasheets.length} · 바뀐 칸 <b>${r.changes.length}</b> · 목록 값 유지 ${r.kept.length}</p>
      <div style="max-height:320px;overflow:auto"><table class="t"><thead><tr><th>Tag</th><th>Column</th><th>Previous</th><th>New</th></tr></thead><tbody>
      ${r.changes.slice(0, 400).map(c => `<tr><td>${esc(c.tag)}</td><td>${esc(c.column)}</td><td class="chg-old">${esc(c.previous.slice(0, 80))}</td><td>${esc(String(c.new).slice(0, 80))}</td></tr>`).join('')}</tbody></table></div>`;
  };
  $('#ex2').onclick = () => download(`/projects/${S.pid}/extracted.csv`).catch(e => toast(e.message, 1));
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
  if (e.key === 'Escape') { $('#modal').hidden = true; W.viewer?.toggleDraw(false); return; }
  if (e.target.closest('input, textarea, select') || !$('#modal').hidden || e.ctrlKey || e.metaKey || e.altKey) return;
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
  else if (e.key === 'a') W.viewer.toggleDraw();
});

/* ── start ────────────────────────────────────────────────────────────── */
if (EMBED) document.body.classList.add('embed');
$('#who').innerHTML = `<b>${esc((USER || '?').slice(0, 1))}</b>${esc(USER || '이름 없음')}`;
loadProjects().then(() => go((location.hash.slice(1) || LS.get('view', 'dash')).split('?')[0], false))
  .catch(e => { document.querySelector('#views').innerHTML = `<div class="empty" style="color:var(--bad)">${esc(e.message)}</div>`; });
})();
