/* PDS 분석 — Process Data Sheet screens (valve46, user 2026-11-27: 'PDS 분석되는 메뉴도 새로 만들자').
 * ?kind=pds : PDS 현황 (document numbers · uploaded Revs · tags · sections) · PDS Tag 목록 (what the newest Rev. says) ·
 * Rev. 비교 (two Revs. of one number, tag by tag · column by column — app/valve/pdsrev.py) · PDS 올리기 (Document Management).
 * Data: /api/valve/projects/{pid}/pds/* .  Uses the Valve page's helpers through window.VALVE (valve.js). */
(() => {
'use strict';
const V = window.VALVE;
if (!V) return;
const { S, Q, LS, api, esc, toast, download, $, $$ } = V;
if ((Q.get('kind') || '').toLowerCase() !== 'pds') return;

const P = { q: '', doc: '', sec: '', cdoc: Q.get('doc') || '', old: null, nw: null, st: '', lv: '', cq: '', open: new Set() };
const LV = { High: 'lv-h', Med: 'lv-m', Min: 'lv-n' };
const STC = { Changed: 'st-c', 'No Change': 'st-0', New: 'st-n', Delete: 'st-d', 'Tag 변경': 'st-r' };
const day = t => (t || '').replace('T', ' ').slice(0, 16);
const lv = l => l ? `<span class="plv ${LV[l] || ''}">${esc(l)}</span>` : '';
const stp = s => `<span class="pst ${STC[s] || ''}">${esc(s)}</span>`;

function buildMenu() {
  const M = [['pdash', '▦', 'PDS 현황'], ['psum', 'Σ', '변경 Summary'], ['pcmp', '⇆', 'Rev. 비교'], ['ptags', '☷', 'PDS Tag 목록'], ['docs', '▤', 'PDS 올리기']];
  window.INST_VIEWS = M.map(m => m[0]);
  window.PDS_PAGE = true;
  window.DOC_KINDS = ['process'];                         // this page uploads PDS only (kept on the base project · 공통 자료)
  window.INST_CRUMB = 'PDS 분석';
  $('#menu').innerHTML = M.map(([v, ic, l]) => `<button data-v="${v}"><i>${ic}</i>${l}</button>`).join('');
  for (const [v] of M) if (!$('#v-' + v)) { const sec = document.createElement('section'); sec.className = 'view'; sec.id = 'v-' + v; $('#views').append(sec); }
  const sm = $('#nav .brand small'); if (sm) sm.textContent = 'PDS 분석';
  const bb = $('#nav .brand b'); if (bb) bb.textContent = 'Process Data Sheet';
  document.title = 'PDS 분석 — Process Data Sheet';
  const cb = $('#crumb > b:last-child'); if (cb) cb.textContent = 'PDS 분석';
}

const xl = (doc, lang, o, n) => download(`/projects/${S.pid}/pds_revcompare.xlsx?lang=${lang}` + (doc ? `&doc_no=${encodeURIComponent(doc)}` : '') + (o ? `&old=${o}` : '') + (n ? `&new=${n}` : ''))
  .then(r => toast(`PDS Rev. 비교 Excel (${lang === 'en' ? 'English' : '한글'}) — 문서 ${r.headers.get('X-Count')}개`)).catch(e => toast(e.message, 1));
const xlBtns = (doc, o, n) => `<button data-xl="ko" data-doc="${esc(doc || '')}" ${o ? `data-o="${o}" data-n="${n}"` : ''}>⇩ Excel (한글)</button>`
  + `<button data-xl="en" data-doc="${esc(doc || '')}" ${o ? `data-o="${o}" data-n="${n}"` : ''}>⇩ Excel (English)</button>`;
function bindXl(el) { $$('[data-xl]', el).forEach(b => b.onclick = e => { e.stopPropagation(); xl(b.dataset.doc, b.dataset.xl, +b.dataset.o || 0, +b.dataset.n || 0); }); }
/* valve58 (user 2026-11-28: '입력된 PDS title 별로 · 사용자 선택별로 · 전체를 볼 수 있도록') — one selector on every screen:
   [전체] and one chip per PDS (number · its title).  A chip's name = that PDS alone · its checkbox = add / remove (any set). */
P.docs = new Set(LS.get('pds.docs', []));                 // empty = all
const inSel = dn => !P.docs.size || P.docs.has(dn);
const short = t => { const m = String(t || '').match(/\b(?:IN|AT|FOR)\s+([A-Z0-9][A-Z0-9 \-]{2,40})$/i); return m ? m[1].trim() : ''; };   // '… IN <AREA>' → the area words
function docBar(docs, onlyRevised) {
  const list = docs.filter(d => !onlyRevised || d.revs.length >= 2);
  [...P.docs].forEach(dn => { if (!docs.some(d => d.doc_no === dn)) P.docs.delete(dn); });
  return `<div class="pdbar" title="PDS 고르기 — 이름을 누르면 그 PDS 만 · 네모를 누르면 여러 개 · '전체' 는 모두"><button data-pd="" class="${P.docs.size ? '' : 'on'}">전체 <b>${list.length}</b></button>
    ${list.map(d => `<span class="pdc ${P.docs.has(d.doc_no) ? 'on' : ''}" title="${esc(d.title || d.doc_no)}"><input type="checkbox" data-pdc="${esc(d.doc_no)}" ${P.docs.has(d.doc_no) ? 'checked' : ''}>
      <button data-pd="${esc(d.doc_no)}"><b>${esc(d.doc_no)}</b>${d.area ? ` <i>${esc(d.area)}</i>` : ''}${d.title ? ` <small>${esc(short(d.title) || d.title.slice(0, 44))}</small>` : ''}</button></span>`).join('')}</div>`;
}
function bindDocBar(el, redraw) {
  const done = () => { LS.set('pds.docs', [...P.docs]); redraw(); };
  $$('.pdbar [data-pd]', el).forEach(b => b.onclick = () => { P.docs = new Set(b.dataset.pd ? [b.dataset.pd] : []); done(); });
  $$('.pdbar [data-pdc]', el).forEach(c => c.onchange = () => { if (c.checked) P.docs.add(c.dataset.pdc); else P.docs.delete(c.dataset.pdc); done(); });
}
const getSum = async fresh => (!fresh && P.sumC) || (P.sumC = await api('GET', `/projects/${S.pid}/pds/summary`));
function goCmp(doc, o, n) { P.docs = new Set([doc]); LS.set('pds.docs', [doc]); P.cdoc = doc; P.old = o || null; P.nw = n || null; P.st = ''; P.lv = ''; P.only = null; P.sus = false; P.open = new Set(); V.go('pcmp'); }
const counts = c => c ? `<span class="pcnt">${['High', 'Med', 'Min'].map(l => c[`changed_${l.toLowerCase()}`] ? `${lv(l)} ${c[`changed_${l.toLowerCase()}`]}` : '').filter(Boolean).join(' ')}
  · ${stp('Changed')} ${c.Changed || 0} · ${stp('No Change')} ${c['No Change'] || 0} · ${stp('New')} ${c.New || 0} · ${stp('Delete')} ${c.Delete || 0}${c['Tag 변경'] ? ` · ${stp('Tag 변경')} ${c['Tag 변경']}` : ''}</span>` : '';

/* ── PDS 현황 ─────────────────────────────────────────────────────────── */
async function renderDash() {
  const el = $('#v-pdash');
  el.innerHTML = '<div class="vh"><h2>PDS 현황</h2></div><div class="soft">불러오는 중…</div>';
  const s0 = await getSum(true);
  const sd = s0.documents.filter(d => inSel(d.doc_no));
  const s = { documents: sd, totals: { documents: sd.length, uploads: sd.reduce((a, d) => a + d.revs.length, 0), tags: sd.reduce((a, d) => a + d.revs[0].tags, 0), revised: sd.filter(d => d.compare).length } };
  const T = s.totals;
  const kpi = (l, n, sub) => `<div class="pk"><div class="pkl">${l}</div><div class="pkn">${n}</div>${sub ? `<div class="soft">${sub}</div>` : ''}</div>`;
  el.innerHTML = `<div class="vh"><h2>PDS 현황</h2><span class="soft">문서 번호마다 가장 새로 올린 Rev. 을 모든 Valve · Instrument 검토가 씁니다 · 같은 번호의 수정 PDS 를 올리면 앞 Rev. 과 비교합니다</span>
      <span class="sp"></span>${T.revised ? xlBtns('') : ''}</div>
    ${docBar(s0.documents)}
    <div class="pkpis">${kpi('PDS 문서', T.documents, '문서 번호 기준')}${kpi('올린 파일', T.uploads, 'Rev. 포함')}${kpi('Tag (최신 Rev.)', T.tags, '검토에 쓰는 Tag')}${kpi('수정본 있는 문서', T.revised, 'Rev. 비교 가능')}</div>
    ${s.documents.length ? s.documents.map(d => { const L = d.revs[0];
      return `<div class="card pdoc"><h3>${esc(d.doc_no)} ${d.title ? `<span class="ptitle">${esc(d.title)}</span>` : ''} ${d.area ? `<span class="parea">${esc(d.area)}</span>` : ''} <span class="soft" style="font-weight:400">최신 Rev.${esc(L.rev || '?')} · Tag ${L.tags}</span>
        <span class="sp"></span>${d.compare ? `<button data-cmp="${esc(d.doc_no)}">⇆ Rev. 비교 보기</button>${xlBtns(d.doc_no)}` : '<span class="soft">Rev. 하나 — 수정 PDS 를 올리면 비교</span>'}</h3>
        ${d.compare ? `<div class="pline">Rev.${esc(d.revs[1].rev || '?')} → Rev.${esc(L.rev || '?')} : ${counts(d.compare.counts)}</div>` : ''}
        <table class="t"><thead><tr><th>Rev.</th><th>파일</th><th>올린 날 · 사람</th><th>Tag</th><th>On-Off</th><th>MOV</th><th>Control Valve · PSV</th><th>표</th><th></th></tr></thead><tbody>
        ${d.revs.map((r, i) => `<tr><td><b>Rev.${esc(r.rev || '?')}</b></td><td>${esc(r.filename)}</td><td class="mono">${esc(day(r.uploaded_at))} · ${esc(r.uploaded_by)}</td><td>${r.tags}</td>
          <td>${r.sections['On-Off'] || ''}</td><td>${r.sections.MOV || ''}</td><td>${r.sections['Control Valve · PSV'] || ''}</td><td>${r.tables}</td>
          <td>${i === 0 ? '<span class="puse">검토에 사용</span>' : `<button data-cmp="${esc(d.doc_no)}" data-o="${r.id}" data-n="${L.id}" title="이 Rev. 과 최신 Rev. 비교">⇆ 최신과 비교</button>`}</td></tr>`).join('')}
        </tbody></table></div>`; }).join('')
      : `<div class="card"><div class="empty">아직 올린 PDS 가 없습니다 — 왼쪽 <b>PDS 올리기</b> 에서 PDF 를 넣으세요 (공통 자료와 같은 곳에 보관됩니다).</div></div>`}`;
  bindDocBar(el, renderDash);
  $$('[data-cmp]', el).forEach(b => b.onclick = () => goCmp(b.dataset.cmp, +b.dataset.o || null, +b.dataset.n || null));
  bindXl(el);
}

/* ── the grids (valve50: xgrid.js — every cell lives, only the rows on screen are drawn) ────────────────────────── */
const W = { location: 230, pid_no: 150, line_no: 190, notes: 200, remarks: 230, valve_type: 96, fluid: 110, fluid_state: 70 };
const fw = k => W[k] || 84;
const grids = {};
function grid(id, host, opt) { grids[id]?.destroy(); grids[id] = window.XGrid(host, { key: 'pds.' + id, ...opt }); return grids[id]; }   // key: the viewer's freeze is remembered
const lvC = l => l ? 'xl-' + l : '';
// valve51 · 52 (user 2026-11-27: '사이즈 이전 대비 변경되었을 때만 최신 사이즈 변경된 값을 파랑색만, 이전 값은 그대로'):
// a Line / Valve Size of the latest Rev. that changed = the number alone, in blue · every other size stays as written
const SIZEK = new Set(['line_size', 'valve_size']);
const num = v => String(v ?? '').replace(/["'″”“]|''/g, '').replace(/\s*(inch|in)\b\.?/gi, '').trim();
const sz = (k, v) => SIZEK.has(k) && v !== '' && v != null ? num(v) : (v ?? '');
const SIZE_ITEMS = new Set(['Line Size', 'Valve Size']);

/* ── PDS Tag 목록 ─────────────────────────────────────────────────────── */
async function renderTags() {
  const el = $('#v-ptags');
  el.innerHTML = '<div class="vh"><h2>PDS Tag 목록</h2></div><div class="soft">불러오는 중…</div>';
  const [D, sm] = await Promise.all([api('GET', `/projects/${S.pid}/pds/tags`), getSum()]);
  const secs = [...new Set(D.rows.map(r => r.section))];
  el.innerHTML = `<div class="vh"><h2>PDS Tag 목록</h2><span class="soft">각 문서 번호의 최신 Rev. 이 적은 값 그대로 (검토에 쓰는 값) · 셀을 누르고 화살표 · Shift · Ctrl+C 로 엑셀처럼</span></div>
    ${docBar(sm.documents)}
    <div class="ptools"><input class="tq" placeholder="Tag · Location · Line · P&ID 찾기 (입력하는 대로)" value="${esc(P.q)}">
      <select data-f="sec"><option value="">구분 전체</option>${secs.map(d => `<option ${P.sec === d ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select>
      <span class="soft" data-cnt></span></div><div data-grid></div>`;
  const cols = [{ label: 'Doc No.', w: 140 }, { label: 'Rev.', w: 52 }, { label: '구분', w: 72 }, { label: 'Tag', w: 120 }, ...D.fields.map(f => ({ label: f.label, w: fw(f.key) }))];
  const rowsOf = () => {
    const q = P.q.toUpperCase();
    const rs = D.rows.filter(r => inSel(r.doc_no) && (!P.sec || r.section === P.sec)
      && (!q || [r.tag, r.location, r.line_no, r.pid_no, r.fluid].join(' ').toUpperCase().includes(q)));
    $('[data-cnt]', el).textContent = `표시 ${rs.length} / ${D.rows.length}`;
    return rs.map(r => ({ cells: [{ v: r.doc_no }, { v: `Rev.${r.rev || '?'}` }, { v: r.section }, { v: r.tag, c: 'xb' }, ...D.fields.map(f => ({ v: r[f.key] ?? '' }))] }));
  };
  const g = grid('tags', $('[data-grid]', el), { cols, rows: rowsOf(), freeze: 4 });
  let tm = 0;
  $('.tq', el).oninput = e => { clearTimeout(tm); tm = setTimeout(() => { P.q = e.target.value; g.setRows(rowsOf()); }, 120); };
  $$('select[data-f]', el).forEach(s => s.onchange = () => { P[s.dataset.f] = s.value; g.setRows(rowsOf()); });
  bindDocBar(el, renderTags);
}

/* ── Rev. 비교 ────────────────────────────────────────────────────────── */
async function renderCmp(keep) {                          // keep = after a link: no blank screen, the same place (valve57)
  const el = $('#v-pcmp'), at = keep && grids.cmp ? grids.cmp.getScroll() : null;
  if (!keep) { el.innerHTML = '<div class="vh"><h2>Rev. 비교</h2></div><div class="soft">불러오는 중…</div>'; P.sumC = null; }
  const sum = await getSum();
  const many = sum.documents.filter(d => d.revs.length >= 2);
  if (!many.length) { el.innerHTML = `<div class="vh"><h2>Rev. 비교</h2></div><div class="card"><div class="empty">같은 문서 번호로 두 Rev. 이상 올린 PDS 가 없습니다 — 수정 PDS 를 <b>PDS 올리기</b> 에서 넣으면 여기서 비교합니다.</div></div>`; return; }
  let pick = many.filter(d => inSel(d.doc_no));
  if (!pick.length) pick = many;                            // a chosen PDS without a second Rev.: show what can be compared
  const one = pick.length === 1, D = pick[0];
  const nw = (one && D.revs.find(r => r.id === P.nw)) || D.revs[0];
  const old = (one && D.revs.find(r => r.id === P.old && r.id < nw.id)) || D.revs.find(r => r.id < nw.id) || D.revs[1];
  // one PDS: the two Revs. chosen · several / all: each PDS's newest against the one before, in one sheet
  const CS = await Promise.all(pick.map(d => api('GET', `/projects/${S.pid}/pds/compare?doc_no=${encodeURIComponent(d.doc_no)}` + (one ? `&old=${old.id}&new=${nw.id}` : ''))));
  CS.forEach(c => c.items.forEach(i => { i._doc = c.doc_no; i._or = c.old.rev; i._nr = c.new.rev; }));
  const C = one ? CS[0] : { doc_no: '', area: '', fields: CS[0].fields, items: CS.flatMap(c => c.items), excluded_columns: [...new Set(CS.flatMap(c => c.excluded_columns))],
    counts: { old_tags: CS.reduce((a, c) => a + c.counts.old_tags, 0), new_tags: CS.reduce((a, c) => a + c.counts.new_tags, 0) } };
  const docOf = tag => (C.items.find(i => i.tag === tag) || {})._doc || C.doc_no;
  const lab = Object.fromEntries(C.fields.map(f => [f.key, f.label])), keys = C.fields.map(f => f.key);
  const cnt = s => C.items.filter(i => i.status === s).length, cl = l => C.items.filter(i => i.overall === l).length;
  const revOpt = (sel, cond) => D.revs.filter(cond).map(r => `<option value="${r.id}" ${r.id === sel.id ? 'selected' : ''}>Rev.${esc(r.rev || '?')} · ${esc(r.filename)}</option>`).join('');
  el.innerHTML = `<div class="vh"><h2>Rev. 비교</h2><span class="soft">같은 Tag 번호끼리만 비교 · New 줄에서 '이전 Tag 지정' → Tag 변경 · 셀을 누르고 화살표 · Shift · Ctrl+C 로 엑셀처럼</span><span class="sp"></span>${one ? xlBtns(C.doc_no, old.id, nw.id) : xlBtns('')}</div>
    ${docBar(sum.documents, true)}
    <div class="ptools">${one ? `<label>이전 <select data-c="old">${revOpt(old, r => r.id < nw.id)}</select></label>
      <label>최신 <select data-c="new">${revOpt(nw, r => r.id > D.revs[D.revs.length - 1].id)}</select></label>` : `<span class="soft">PDS ${pick.length}개 — 각 PDS 의 최신 Rev. vs 바로 앞 Rev. (Rev. 을 고르려면 PDS 하나만 선택)</span>`}
      ${C.area ? `<span class="parea">${esc(C.area)}</span>` : ''}<span class="soft">Tag ${C.counts.old_tags} → ${C.counts.new_tags}</span>
      ${C.excluded_columns.length ? `<span class="soft" title="한쪽 Rev. 에만 있는 열 — 비교하지 않고 값만 표시">비교 제외 열: ${esc(C.excluded_columns.join(', '))}</span>` : ''}</div>
    <div class="rchips"><button data-st="">전체<b>${C.items.length}</b></button>${['Changed', 'Tag 변경', 'No Change', 'New', 'Delete'].map(s => `<button data-st="${s}">${stp(s)}<b>${cnt(s)}</b></button>`).join('')}
      <button data-sus title="변경 의심 표시가 있는 New · Delete 만 — 줄의 ✓ 확정 / ✕ 아님 으로 정리"><span class="pst st-s">변경 의심</span><b>${C.items.filter(i => i.status === 'New' && (i.suspect || []).length).length}</b></button>
      <span class="sp" style="width:14px"></span>${['High', 'Med', 'Min'].map(l => `<button data-lv="${l}" title="종합 중요도">${lv(l)}<b>${cl(l)}</b></button>`).join('')}
      <label class="xchk"><input type="checkbox" data-only ${P.onlyChg ? 'checked' : ''}> 바뀐 열만</label>
      <input class="tq" placeholder="Tag · Location 찾기 (입력하는 대로)" value="${esc(P.cq)}"><span data-clr></span>
      <span class="xleg"><i class="xc">　</i> 변경된 셀 <b class="xr">붉은 글씨</b> 변경된 값 <b class="xbl">파랑 숫자</b> 변경된 Size</span><span class="soft" data-cnt></span></div>
    <div data-grid></div>
    <div class="soft" style="margin:6px 2px">중요도 기준: High = Size · Bore · 설계 P/T · Max ΔP · Pipe Class Rating 문자 / Med = 운전 P/T · 유량 · 밀도 · 점도 · 상 · Fluid · 운전 시간 · Tightness · Fail · Actuator · 수량 · Class 코드 체계 /
      Min = 문서 정합성 · 2% 이하 변화는 한 단계 낮춤.</div>`;
  const dels = C.items.filter(i => i.status === 'Delete'), delsOf = i => dels.filter(d => d._doc === i._doc);
  const prevH = i => i.status === 'Tag 변경'
    ? `<b>${esc(i.old_tag)}</b> <button class="xunl" data-unl="${esc(i.tag)}" title="Tag 변경 지정 해제 — 다시 New · Delete 로 (${esc(i.link?.by || '')} ${esc((i.link?.at || '').slice(0, 10))})">✕</button>`
    : i.status === 'New' && delsOf(i).length ? `<select class="xlink" data-new="${esc(i.tag)}" title="이 New Tag 가 이전 Rev. 의 어느 Tag 인지 지정 → Tag 변경으로 비교 · Summary 반영">
        <option value="">이전 Tag 지정…</option>${[...delsOf(i)].sort((a, b) => (i.suspect || []).includes(b.tag) - (i.suspect || []).includes(a.tag)).map(d => `<option value="${esc(d.tag)}">${(i.suspect || []).includes(d.tag) ? '★ 변경 의심 · ' : ''}${esc(d.tag)}${d.old?.location ? ' · ' + esc(String(d.old.location).slice(0, 28)) : ''}</option>`).join('')}</select>` : '';
  // valve55: the hint under the tag — same Location and Line Size as a tag of the other side (status unchanged)
  const susp = i => (i.suspect || []).length ? `(변경 의심 "${i.suspect.join('", "')}")` : '';
  const view = () => {
    const q = P.cq.toUpperCase();
    const items = C.items.filter(i => (!P.only || P.only.has(i.tag)) && (!P.sus || (i.suspect || []).length) && (!P.st || i.status === P.st) && (!P.lv || i.overall === P.lv)
      && (!q || [i.tag, i.old_tag, i.new?.location, i.old?.location].join(' ').toUpperCase().includes(q)));
    const fk = P.onlyChg ? keys.filter(k => items.some(i => i.imp[k])) : keys;
    const cols = [{ label: 'No', w: 40 }, ...(one ? [] : [{ label: 'Doc No.', w: 138 }]), { label: 'Status', w: 92 }, { label: 'Tag', w: 178 }, { label: '이전 Tag', w: 250 }, { label: 'Rev.', w: 54 }, { label: 'Row', w: 66 },
      ...fk.map(k => ({ label: lab[k], w: fw(k) })), { label: '중요도(종합)', w: 86 }, { label: '비고 / 사유', w: 300 }];
    const rows = [];
    items.forEach((i, n) => {
      const sc = STC[i.status] || '', o = i.old, nv = i.new;
      // valve56 (user 2026-11-27: '변경 의심 Tag 에 대해 이전 · 최신 · 변경 의심 값도 행을 추가'): one row per suspected tag, with its
      // own process data (New: the earlier tag in the earlier Rev. · Delete: the new tag in the latest Rev.) — orange where it differs
      const seq = ['o', 'n', ...(i.suspect_vals || []), 'i'];
      seq.forEach((kind, j) => {
        const m = j ? ' xm' : '', sv = typeof kind === 'object' ? kind : null;
        const rowLab = sv ? '변경 의심' : { o: '이전', n: '최신', i: '중요도' }[kind];
        const revLab = sv ? `Rev.${sv.side === 'old' ? i._or : i._nr}` : kind === 'o' ? `Rev.${i._or}` : kind === 'n' ? `Rev.${i._nr}` : '';
        const cells = [{ v: j ? '' : n + 1, c: 'xn' + m }, ...(one ? [] : [{ v: j ? '' : i._doc, c: 'xm0' + m, t: i._doc }]), { v: j ? '' : i.status, c: `xs ${sc}${m}`, t: i.status },
          j === 1 && susp(i) ? { v: susp(i), c: 'xsus xm', t: `${susp(i)} — Location 이 비슷하고 Line Size · (Line 번호 또는 P&ID) 가 같음 · 참고 표시, 상태는 그대로 · ${i.status === 'New' ? "'이전 Tag 지정' 에서 확정" : '최신 Rev. 의 그 Tag 에서 확정'}` }
            : sv ? { v: `↳ ${sv.tag}`, c: 'xsusr xm', t: `변경 의심 Tag ${sv.tag} — 아래 칸은 이 Tag 의 Process Data` }
            : { v: j ? '' : i.tag, c: 'xb' + m, t: i.tag },
          sv ? { v: (sv.why || []).join(' + '), h: `<button class="xok" data-ok="${esc(i.status === 'New' ? i.tag : sv.tag)}" data-old="${esc(i.status === 'New' ? sv.tag : i.tag)}" title="Tag 변경으로 확정 — 이 두 Tag 를 값끼리 비교 · Summary · Excel 반영">✓ 확정</button><button class="xno" data-no="${esc(i.status === 'New' ? i.tag : sv.tag)}" data-old="${esc(i.status === 'New' ? sv.tag : i.tag)}" title="변경 의심 아님 — 이 짝의 표시를 지움 (기록됨)">✕ 아님</button> <span class="xwhy">${esc((sv.why || []).join(' + '))}</span>`,
              c: 'xprev xm', t: `근거: ${(sv.why || []).join(' + ')} 같음 — ✓ 확정 = Tag 변경 · ✕ 아님 = 표시 지움` }
          : j ? { v: '', c: 'xm' } : { v: i.old_tag || '', h: prevH(i), c: 'xprev', t: i.status === 'Tag 변경' ? `이전 Tag ${i.old_tag} (지정: ${i.link?.by || ''} ${(i.link?.at || '').slice(0, 10)})` : i.status === 'New' ? 'New — 이전 Tag 를 지정하면 Tag 변경' : '' },
          { v: revLab, c: sv ? 'xsusr' : '' }, { v: rowLab, c: sv ? 'xrow xsusr' : 'xrow', t: sv ? `변경 의심 Tag ${sv.tag} 의 Process Data (${revLab}) — 주황 = 이 Tag 의 값과 다른 칸` : rowLab }];
        fk.forEach((k, x) => {
          const ch = !!i.imp[k], fxT = ch ? `${lab[k]}: ${o?.[k] ?? ''} → ${nv?.[k] ?? ''} (${i.imp[k]})` : null;
          if (kind === 'i') { cells.push({ v: i.imp[k] || '', c: lvC(i.imp[k]), t: fxT }); return; }
          if (sv) { const v = sv.values[k] ?? '', own = (i.status === 'New' ? nv : o)?.[k] ?? '', df = sv.diff.includes(k);
            cells.push({ v, c: 'xsusv' + (df ? ' xsusd' : ''), t: df ? `${lab[k]}: ${i.tag} = ${own} · ${sv.tag} = ${v}` : v }); return; }
          const src = kind === 'n' ? nv : o, jn = kind === 'n';
          if (!src) { cells.push({ v: x ? '' : (jn ? `(Rev.${i._nr} 미확인)` : '(이전 Rev. 없음)'), c: 'xna' }); return; }
          const raw = src[k] ?? '', szc = SIZEK.has(k) && ch && jn && raw !== '';   // a changed size of the latest Rev.
          const v = szc ? sz(k, raw) : raw, red = !szc && jn && (ch || i.status === 'New') && v !== '';
          // valve51 (user 2026-11-27: '변경 사항 노랑색 음영은 최신 값에만'): the earlier row keeps no shading
          cells.push({ v, c: (ch && jn ? 'xc' : '') + (szc ? ' xsz' : red ? ' xr' : ''), t: fxT ?? raw });
        });
        cells.push({ v: j ? '' : (['New', 'Delete'].includes(i.overall) ? i.overall : i.overall || ''), c: (j ? 'xm ' : '') + (j ? '' : lvC(i.overall)) });
        cells.push({ v: j ? '' : i.note || '', c: 'xnote' + m, t: i.note || '' });
        rows.push({ cls: j ? (sv ? 'xsusrow' : '') : 'xt', cells });
      });
    });
    $('[data-cnt]', el).textContent = `Tag ${items.length}개 · ${rows.length}줄`;
    $('[data-clr]', el).innerHTML = P.only ? `<button data-clrb title="변경 Summary 에서 고른 Tag 만 보는 중 — 누르면 모두">✕ 고른 Tag ${P.only.size}개만</button>` : '';
    $$('[data-st]', el).forEach(b => b.classList.toggle('on', b.dataset.st === P.st));
    $('[data-sus]', el).classList.toggle('on', !!P.sus);
    $$('[data-lv]', el).forEach(b => b.classList.toggle('on', b.dataset.lv === P.lv));
    return { cols, rows };
  };
  const setLink = async (nt, ot) => {
    try { await api('PUT', `/projects/${S.pid}/pds/links`, { doc_no: docOf(nt), new_tag: nt, old_tag: ot });
      toast(ot ? `${nt} ← 이전 ${ot} : Tag 변경으로 비교합니다 (Summary · Excel 반영)` : `${nt} Tag 변경 지정 해제`); renderCmp(true); }
    catch (e) { toast(e.message, 1); } };
  const notThis = async (nt, ot) => {
    try { await api('PUT', `/projects/${S.pid}/pds/links`, { doc_no: docOf(nt), new_tag: nt, old_tag: ot, dismiss: true });
      toast(`${nt} ↔ ${ot} : 변경 의심 아님으로 기록`); renderCmp(true); }
    catch (e) { toast(e.message, 1); } };
  const first = view();
  const g = grid('cmp', $('[data-grid]', el), { cols: first.cols, rows: first.rows, freeze: one ? 3 : 4, key: one ? 'pds.cmp' : 'pds.cmpN',
    onAction(t, e) { if (t.matches('select.xlink') && e.type === 'change' && t.value) setLink(t.dataset.new, t.value);
      else if (t.matches('[data-unl]') && e.type === 'click') setLink(t.dataset.unl, '');
      else if (t.matches('[data-ok]') && e.type === 'click') setLink(t.dataset.ok, t.dataset.old);
      else if (t.matches('[data-no]') && e.type === 'click') notThis(t.dataset.no, t.dataset.old); } });
  if (at) grids.cmp.setScroll(at[0], at[1]);
  const refresh = () => { const v = view(); g.setCols(v.cols, v.rows); };
  bindXl(el);
  bindDocBar(el, () => { P.old = P.nw = null; P.only = null; renderCmp(); });
  if (one) { $('select[data-c="old"]', el).onchange = e => { P.old = +e.target.value; P.nw = nw.id; renderCmp(); };
    $('select[data-c="new"]', el).onchange = e => { P.nw = +e.target.value; P.old = null; renderCmp(); }; }
  $$('[data-st]', el).forEach(b => b.onclick = () => { P.st = b.dataset.st; refresh(); });
  $('[data-sus]', el).onclick = () => { P.sus = !P.sus; refresh(); };
  $$('[data-lv]', el).forEach(b => b.onclick = () => { P.lv = P.lv === b.dataset.lv ? '' : b.dataset.lv; refresh(); });
  $('[data-only]', el).onchange = e => { P.onlyChg = e.target.checked; refresh(); };
  $('[data-clr]', el).onclick = e => { if (e.target.closest('[data-clrb]')) { P.only = null; refresh(); } };
  let tm = 0;
  $('.rchips .tq', el).oninput = e => { clearTimeout(tm); tm = setTimeout(() => { P.cq = e.target.value; refresh(); }, 120); };
}

/* ── 변경 Summary (valve48 · 50) — the Excel's Summary · Sizing sheets on screen, every cell alive ─────────────── */
async function renderSum() {
  const el = $('#v-psum');
  el.innerHTML = '<div class="vh"><h2>변경 Summary</h2></div><div class="soft">불러오는 중…</div>';
  const X = await api('GET', `/projects/${S.pid}/pds/change_summary`);
  const sm = await getSum();
  const D = X.documents.filter(d => inSel(d.doc_no)).length ? X.documents.filter(d => inSel(d.doc_no)) : X.documents;
  if (!D.length) { el.innerHTML = `<div class="vh"><h2>변경 Summary</h2></div><div class="card"><div class="empty">같은 문서 번호로 두 Rev. 이상 올린 PDS 가 없습니다 — 수정 PDS 를 <b>PDS 올리기</b> 에서 넣으면 변경 Summary 가 나옵니다.</div></div>`; return; }
  const L = D.map((_, i) => String.fromCharCode(65 + i)), sum = f => D.reduce((a, d) => a + f(d), 0);
  const link = (d, n, a) => n ? { v: n, h: `<a class="xnum" data-go="${esc(d.doc_no)}" data-o="${d.old.id}" data-n="${d.new.id}" ${a}>${n}</a>`, c: 'xnc' } : { v: 0, c: 'xnc x0' };
  const CC = [['old_tags', '이전 Tag 수'], ['new_tags', '최신 Tag 수'], ['High', 'Changed (High)', '', 'High'], ['Med', 'Changed (Med)', '', 'Med'],
    ['Min', 'Changed (Min)', '', 'Min'], ['No Change', 'No Change', 'No Change'], ['New', 'New', 'New'], ['Delete', 'Delete', 'Delete'], ['Tag 변경', 'Tag 변경', 'Tag 변경']];
  const t1 = D.map((d, i) => ({ cells: [{ v: L[i] }, { v: d.doc_no, c: 'xb' }, { v: d.area || '' }, { v: `Rev.${d.old.rev || '?'}` }, { v: `Rev.${d.new.rev || '?'}` },
    ...CC.map(([k, , st, lvl]) => k.endsWith('_tags') ? { v: d.counts[k], c: 'xnc' } : { ...link(d, d.counts[k] || 0, `data-st="${st || ''}" data-lv="${lvl || ''}"`), c: 'xnc ' + (lvl ? lvC(lvl) : '') })] }));
  t1.push({ cls: 'xtot', cells: [{ v: '합계', c: 'xb' }, { v: '' }, { v: '' }, { v: '' }, { v: '' }, ...CC.map(([k]) => ({ v: sum(d => d.counts[k] || 0), c: 'xnc xb' }))] });
  const t2 = [{ cells: [{ v: 'Tag 수' }, { v: '이전 Rev. Tag 수' }, { v: '이전 Rev. 문서 기준' }, ...D.map(d => ({ v: d.counts.old_tags, c: 'xnc' })), { v: sum(d => d.counts.old_tags), c: 'xnc xb' }] },
    { cells: [{ v: 'Tag 수' }, { v: '최신 Rev. Tag 수' }, { v: '최신 Rev. 문서 기준' }, ...D.map(d => ({ v: d.counts.new_tags, c: 'xnc' })), { v: sum(d => d.counts.new_tags), c: 'xnc xb' }] },
    ...X.sizing_rows.map(r => ({ cells: [{ v: r.group, c: r.group === '추가/삭제' ? '' : 'xg-size' }, { v: r.item }, { v: r.basis, c: 'soft' },
      ...D.map(d => { const t = d.sizing[r.key] || []; return { ...link(d, t.length, `data-tags="${esc(t.join('|'))}"`), t: t.join(', ') || '0' }; }),
      { v: sum(d => (d.sizing[r.key] || []).length), c: 'xnc xb' }] }))];
  const size = D.flatMap((d, i) => d.size.map(r => ({ cells: [{ v: L[i] }, { v: r.tag, c: 'xb' }, { v: r.old_tag || '' }, { v: r.item }, { v: r.old ?? '' }, { v: num(r.new), c: 'xc xsz', t: r.new ?? '' }] })));
  const high = D.flatMap((d, i) => d.high.map(r => { const S_ = SIZE_ITEMS.has(r.item); return { cells: [{ v: L[i] }, { v: r.tag, c: 'xb' }, { v: r.old_tag || '' }, { v: r.item },
    { v: r.old ?? '' }, { v: S_ ? num(r.new) : r.new ?? '', c: S_ ? 'xc xsz' : 'xc xr', t: r.new ?? '' }, { v: r.status }] }; }));
  const ren = D.flatMap((d, i) => (d.renamed || []).map(r => ({ cells: [{ v: L[i] }, { v: r.tag, c: 'xb' }, { v: r.old_tag }, { v: r.overall || '', c: lvC(r.overall) }, { v: r.note }] })));
  el.innerHTML = `<div class="vh"><h2>변경 Summary</h2><span class="soft">문서 번호마다 최신 Rev. vs 바로 앞 Rev. · 파란 숫자를 누르면 Rev. 비교에서 그 Tag 들만 · 셀은 엑셀처럼 고르고 Ctrl+C</span><span class="sp"></span>${xlBtns('')}</div>
    ${docBar(sm.documents, true)}
    <h3 class="xh3">1. Rev. 비교 Summary</h3><div data-g1></div>
    <h3 class="xh3">2. Summary (Sizing 영향)</h3><div data-g2></div>
    <div class="xtwo"><div><h3 class="xh3">3. Line Size / Valve Size 변경 Tag 목록 <span class="soft">${size.length}</span></h3><div data-g3></div></div>
      <div><h3 class="xh3">4. High 변경 목록 <span class="soft">${high.length}</span></h3><div data-g4></div></div></div>
    <h3 class="xh3">5. Tag 변경 목록 (사용자 지정) <span class="soft">${ren.length} — Rev. 비교의 New 줄에서 '이전 Tag 지정' 으로 넣습니다</span></h3><div data-g5></div>`;
  const go = a => { P.docs = new Set([a.dataset.go]); LS.set('pds.docs', [a.dataset.go]); Object.assign(P, { cdoc: a.dataset.go, old: +a.dataset.o, nw: +a.dataset.n, st: a.dataset.st || '', lv: a.dataset.lv || '', cq: '',
    only: a.dataset.tags ? new Set(a.dataset.tags.split('|')) : null }); V.go('pcmp'); };
  const onAction = t => { if (t.matches('a.xnum')) go(t); };
  grid('s1', $('[data-g1]', el), { cols: [{ label: 'Doc', w: 44 }, { label: 'Doc No.', w: 150 }, { label: 'Area', w: 60 }, { label: '이전 Rev.', w: 70 }, { label: '최신 Rev.', w: 70 },
    ...CC.map(c => ({ label: c[1], w: 96 }))], rows: t1, freeze: 2, maxH: 60 + t1.length * 21, onAction });
  grid('s2', $('[data-g2]', el), { cols: [{ label: '구분', w: 90 }, { label: '항목', w: 230 }, { label: '판단 기준', w: 360 }, ...D.map((d, i) => ({ label: `${L[i]}. ${d.doc_no}`, w: 150 })), { label: '합계', w: 70 }],
    rows: t2, freeze: 2, maxH: 60 + t2.length * 21, onAction });
  const small = (k, cols, rows) => rows.length ? grid(k, $(`[data-${k}]`, el), { cols, rows, maxH: 360 }) : ($(`[data-${k}]`, el).innerHTML = '<div class="soft">없음</div>');
  small('g3', [{ label: 'Doc', w: 44 }, { label: 'Tag', w: 120 }, { label: '이전 Tag', w: 110 }, { label: '항목', w: 90 }, { label: '이전 Rev.', w: 80 }, { label: '최신 Rev.', w: 80 }], size);
  small('g4', [{ label: 'Doc', w: 44 }, { label: 'Tag', w: 120 }, { label: '이전 Tag', w: 110 }, { label: '항목', w: 130 }, { label: '이전 Rev. 값', w: 100 }, { label: '최신 Rev. 값', w: 100 }, { label: 'Status', w: 80 }], high);
  bindDocBar(el, renderSum);
  small('g5', [{ label: 'Doc', w: 44 }, { label: 'Tag (최신)', w: 130 }, { label: '이전 Tag', w: 130 }, { label: '중요도(종합)', w: 90 }, { label: '비고', w: 480 }], ren);
  bindXl(el);
}

buildMenu();
const RUN = { pdash: renderDash, psum: renderSum, ptags: renderTags, pcmp: renderCmp };
window.PDS = { render(v) { P.sum = null; P.tags = null; P.ckey = null;          // each menu visit reads afresh (a PDS just uploaded shows at once)
  (RUN[v] || renderDash)().catch(e => { console.error(e); toast(e.message, 1); }); } };
})();
