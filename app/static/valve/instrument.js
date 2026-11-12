/* Instrument datasheet review — screens (valve40).  Data: /api/valve/projects/{pid}/inst/* · /api/valve/inst/* (app/valve/inst_api.py).
 * Instrument 현황판 (all item kinds at a glance) · Instrument Review (tag list · PDF · findings · read values) · List 대조.
 * Uses the Valve page's helpers through window.VALVE (valve.js) — same project spaces, same Document Management. */
(() => {
'use strict';
const V = window.VALVE;
if (!V) return;
const { S, Q, LS, api, esc, pill, toast, $, $$ } = V;
const QK = (Q.get('kind') || '').toLowerCase();
const QSHEET = +Q.get('sheet') || 0;                  // deep link: ?kind=pt&sheet=<id> (or ?sheet=<id> alone)
const I = { showOk: LS.get('inst.showok', false), kinds: null, kind: V.INST_KINDS.has(QK) ? QK : LS.get('inst.kind', 'ft') || 'ft', list: QK === 'iolist' ? 'io_list' : QK === 'instindex' ? 'instrument_index' : LS.get('inst.list', 'instrument_index'), ltab: 'cmp', rows: null, sel: null, d: null, tab: 'find', filt: '', lfilt: '' };
/* One Instrument page = one dashboard menu entry: ?kind=<item> · ?kind=all (현황판) · ?kind=instindex|iolist (Lists).
   The page gets its OWN side menu, like a Valve kind page; the Valve page itself has no Instrument entries. */
const MODE = QK === 'all' ? 'all' : (QK === 'instindex' || QK === 'iolist') ? 'list' : (V.INST_KINDS.has(QK) || (QSHEET && !Q.get('ds'))) ? 'item' : '';
const ITEM_LABEL = { ft: 'FT · Flow Transmitter', pt: 'PT · Pressure / DP Tx', lt: 'LT · Level Tx (DP)', gwr: 'GWR · Level Tx (Radar)', tt: 'TT · Temperature Tx',
  tg: 'TG · Temperature Gauge', pg: 'PG · Pressure Gauge', dpg: 'DPG · DP Gauge', mlg: 'MLG · Mag. Level Gauge', ro: 'RO · Restriction Orifice',
  analyzer: 'AT · Analyzer', cv: 'CV · Control Valve', onoff: 'On-Off Valve', psv: 'PSV' };
const pageName = () => MODE === 'all' ? 'Instrument 현황판' : MODE === 'list' ? (I.list === 'io_list' ? 'IO List' : 'Instrument List') : (ITEM_LABEL[I.kind] || I.kind.toUpperCase());
const VK = { ball: 'Ball', globe: 'Globe', butterfly: 'Butterfly', psv: 'PSV' };
const kindLabel = k => VK[k] ? `${VK[k]} Valve`.replace('PSV Valve', 'PSV') : (k || '').toUpperCase();
function valveUrl(project, ds) {                            // a Valve tag: the Valve review screen of its project
  const u = new URL(location.href); u.searchParams.delete('kind'); u.searchParams.delete('sheet'); u.searchParams.set('project', project); u.searchParams.set('ds', ds); u.hash = 'review';
  return u.toString();
}
function pageUrl(kind, sheet) {                             // another Instrument page (same project · user · embed)
  const u = new URL(location.href); u.searchParams.set('kind', kind); u.searchParams.delete('ds'); u.hash = '';
  if (sheet) u.searchParams.set('sheet', sheet); else u.searchParams.delete('sheet');
  return u.toString();
}
function buildMenu() {
  if (!MODE) return;
  const code = () => (I.kind === 'analyzer' ? 'AT' : I.kind === 'onoff' ? 'On-Off' : I.kind.toUpperCase());
  const M = MODE === 'item' ? [['idash', '▦', 'Dashboard'], ['docs', '▤', 'Document Management'], ['itags', '☷', `${code()} List`], ['ireview', '◧', 'Datasheet Review'],
    ['irev', '⇆', 'Revision Comparison'], ['iproc', '∿', 'Process Data Verification'], ['ipms', '⛭', 'PMS Compliance'], ['iline', '≡', 'Line List Check'],
    ['ilists', '☰', 'Instrument List · IO List'], ['ireg', '❐', 'Document · Revision'], ['iexport', '⇩', 'Reports & Export'], ['isettings', '⚙', 'Settings']]
    : MODE === 'all' ? [['inst', '▥', 'Instrument 현황판'], ['docs', '▤', 'Document Management'], ['ireg', '❐', 'Document · Revision'], ['iexport', '⇩', 'Reports & Export']]
      : [['ilist', I.list === 'io_list' ? '⇄' : '☰', pageName()], ['docs', '▤', 'Document Management'], ['ireg', '❐', 'Document · Revision']];
  window.INST_VIEWS = M.map(m => m[0]);
  $('#menu').innerHTML = M.map(([v, ic, l]) => `<button data-v="${v}"><i>${ic}</i>${l}</button>`).join('');
  for (const [v] of M) if (!$('#v-' + v)) { const sec = document.createElement('section'); sec.className = 'view'; sec.id = 'v-' + v; $('#views').append(sec); }
  paintBrand();
}
function paintBrand() {
  if (!MODE) return;
  window.INST_CRUMB = pageName();
  const sm = $('#nav .brand small'); if (sm) sm.textContent = pageName();
  document.title = `${pageName()} — Instrument Review`;
  const cb = $('#crumb > b:last-child'); if (cb) cb.textContent = pageName();
}

const RES = { 'Mismatch': ['bad', '값 다름'], 'Missing': ['miss', '누락'], 'Review Required': ['rev', '확인 필요'], '없음': ['na', '없음'], 'Datasheet Blank': ['na', 'DS 비어 있음'], 'OK': ['ok', 'OK'],
  '값 다름': ['bad', '값 다름'], '누락': ['miss', '누락'], 'List 에만': ['lo', 'List 에만'], 'Dismissed': ['na', '무시함'] };
const RICO = { bad: '✕', miss: '◌', rev: '?', ok: '✓', na: '–', lo: '≡' };
const rp = (r, n) => { const c = (RES[r] || ['na'])[0]; return `<span class="ir ir-${c}"><i>${RICO[c]}</i>${esc((RES[r] || [, r])[1])}${n === undefined ? '' : ` <b>${n}</b>`}</span>`; };
const GROUPS = [['IN-REQ', '필수 칸'], ['IN-PDS', 'Process Data (PDS)'], ['IN-PMS', 'PMS'], ['IN-LL', 'Process Line List'], ['IN-ITM', 'Item 규칙 (사람 확인)']];
// valve37: these valves are reviewed on the Valve screens (?kind=) — the Instrument card points there
const VALVE_MENU = { cv: [['globe', 'Globe'], ['butterfly', 'Butterfly']], onoff: [['ball', 'Ball']], psv: [['psv', 'PSV']] };
const valveLink = k => { const base = (S.sum?.project?.name || 'CO2 PJT').replace(/\s*·\s*(Globe Valve|Butterfly Valve|PSV)$/, '');
  return (VALVE_MENU[k] || []).map(([vk, l]) => `<a class="vlink" href="/valve/?project=${encodeURIComponent(base)}${vk === 'ball' ? '' : '&kind=' + vk}" target="_top" title="Valve 화면의 ${l} 메뉴에서 검토 (Valve 규칙 · Anatomy)">→ Valve ${l}</a>`).join(' '); };
const ICON = { ft: '≋', pt: '⊙', lt: '▤', gwr: '▥', tt: '🌡', tg: '◔', pg: '◉', dpg: '◎', mlg: '▮', ro: '⊘', analyzer: '⚗', cv: '⧓', onoff: '⧗', psv: '⇑' };

async function kinds() { if (!I.kinds) I.kinds = await api('GET', '/inst/kinds'); return I.kinds; }
const kname = k => (I.kinds || []).find(x => x.kind === k)?.name || k;

/* ── Instrument 현황판 — every item kind at a glance ─────────────────────────────── */
async function renderBoard() {
  const el = $('#v-inst');
  el.innerHTML = '<div class="vh"><h2>Instrument 현황판</h2></div><div class="soft">불러오는 중…</div>';
  await kinds();
  const s = await api('GET', `/projects/${S.pid}/inst/summary`), t = s.total, R = s.refs;
  const ref = (l, v, hint) => `<div class="iref ${v ? 'on' : ''}" title="${esc(v || hint)}"><b>${l}</b><span>${v ? esc(v.length > 46 ? v.slice(0, 44) + '…' : v) : '없음'}</span></div>`;
  const tile = (l, n, cls, tip) => `<div class="kpi ${cls || ''}" title="${esc(tip || '')}"><div class="l">${l}</div><div class="n">${n}</div></div>`;
  const used = s.kinds.filter(k => k.tags);
  const maxI = Math.max(1, ...s.kinds.map(k => k.missing + k.mismatch + k.review));
  el.innerHTML = `<div class="vh"><h2>Instrument 현황판</h2><span class="soft">${esc(S.sum?.project?.name || '')} · 계기 Type 별 Datasheet 검토 현황</span><span class="sp"></span>
      <button data-g="docs">자료 올리기</button><button data-req>필수 칸 확인</button><a class="btnlink" href="/api/valve/projects/${S.pid}/inst/markup.pdf" download title="지적이 있는 Datasheet 전부 — 칸 음영 + 화살표 설명선(이유)">⇩ Mark-up PDF</a><a class="btnlink" href="/api/valve/projects/${S.pid}/inst/review.xlsx" download>⇩ 검토 결과 Excel</a>
</div>
    <div class="irefs">${ref('Process Data (PDS)', R.pds, 'Document Management › Process Data')}${ref('PMS', R.pms, 'Document Management › PMS')}
      ${ref(`Process Line List${R.n_lines ? ` (${R.n_lines} Line)` : ''}`, R.linelist, 'Document Management › Process Line List')}${ref('Instrument Index', R.instrument_index, 'Document Management › Instrument Index · IO List')}${ref('IO List', R.io_list, 'Document Management › Instrument Index · IO List')}</div>
    ${!t.tags ? '<div class="banner info">아직 Instrument Datasheet 가 없습니다 — <b>Document Management › Instrument Datasheet PDF</b> 에 올리면 양식(FT · PT · LT · TT · PG · PSV …)을 알아보고 Tag 별로 검토합니다.</div>' : ''}
    ${t.test ? `<div class="banner warn">시험 자료(TEST DATA 도장) ${t.test}개 Tag 가 들어 있습니다 — 실제 Datasheet 가 아닙니다.</div>` : ''}
    ${t.tags ? `<div class="isum ${t.tags === t.ok_tags ? 'allok' : ''}"><div class="big"><b>${t.ok_tags}</b><span>/ ${t.tags} Tag</span></div>
      <div class="txt"><b>${t.tags === t.ok_tags ? '모든 Tag 에 지적이 없습니다' : `${t.tags - t.ok_tags}개 Tag 에 확인할 지적이 있습니다`}</b>
        <span>지적 없음 ${t.ok_tags} · 지적 있음 ${t.tags - t.ok_tags} — ${rp('Mismatch', t.mismatch)}${rp('Missing', t.missing)}${rp('Review Required', t.review)}</span></div>
      <div class="prog" title="지적 없는 Tag 비율"><i style="width:${Math.round(100 * t.ok_tags / t.tags)}%"></i></div><div class="pct">${Math.round(100 * t.ok_tags / t.tags)}%</div></div>` : ''}
    <div class="kpis ikpis">${tile('Item 종류', used.length + ' / ' + s.kinds.length, '', '자료가 있는 계기 종류 / 양식 카드 수')}${tile('Tag', t.tags, '', '최신 Rev 기준 Tag 수')}${tile('Datasheet', t.sheets, '', '읽은 Datasheet (모든 Rev)')}
      ${tile('지적 없음', t.ok_tags, 'okk', '지적이 하나도 없는 Tag')}${tile('누락', t.missing, t.missing ? 'warn' : '', '필수 칸이 빈 곳 (IN-REQ-01)')}${tile('값 다름', t.mismatch, t.mismatch ? 'warn' : '', 'PDS · PMS · Line List · Item 규칙과 다름')}
      ${tile('확인 필요', t.review, '', '단위 · 기준이 불명확하거나 PMS/Line 에서 정확히 찾지 못함')}${tile('PDS 없음', t.not_in_pds, '', 'Process Data 에 Tag 가 없는 수')}</div>
    <div class="card"><h3>계기 Type 별 현황 <small class="soft">— 칸을 누르면 그 종류의 Review 가 열립니다</small></h3>
      <div class="itypes">${s.kinds.map(k => {
        const iss = k.missing + k.mismatch + k.review, pct = k.tags ? Math.round(100 * k.ok_tags / k.tags) : 0;
        const revs = Object.entries(k.revs).sort().map(([r, n]) => `Rev ${esc(r)} ${n}`).join(' · ');
        return `<div class="itype ${k.tags ? (iss ? 'has' : 'clean') : 'none'}" data-k="${k.kind}" tabindex="0" title="${esc(k.name)} — 양식 ${k.form_id}">
          <div class="ih"><span class="ico">${ICON[k.kind] || '•'}</span><b>${esc(k.kind.toUpperCase())}</b><span class="soft">${esc(k.name)}</span></div>
          <div class="inum"><b>${k.tags}</b><span>Tag</span>${k.sheets !== k.tags ? `<small class="soft">DS ${k.sheets}</small>` : ''}</div>
          <div class="ibar" title="지적 없는 Tag ${k.ok_tags}/${k.tags}"><i style="width:${pct}%"></i></div>
          <div class="icnt">${!k.tags ? '<span class="soft">자료 없음</span>' : !iss ? rp('OK') + '<span class="soft">지적 없음</span>' : `${k.mismatch ? rp('Mismatch', k.mismatch) : ''}${k.missing ? rp('Missing', k.missing) : ''}${k.review ? rp('Review Required', k.review) : ''}`}${k.tags && k.not_in_pds ? `<span class="ir ir-na"><i>–</i>PDS 없음 <b>${k.not_in_pds}</b></span>` : ''}</div>
          <div class="soft irev">${revs || '&nbsp;'}${k.test ? ' · <b class="tst">TEST</b>' : ''}</div>${VALVE_MENU[k.kind] ? `<div class="ivm">${valveLink(k.kind)}</div>` : ''}</div>`;
      }).join('')}</div></div>
    <div class="grid2"><div class="card"><h3>Type 별 지적 수</h3><div class="ichart">${s.kinds.filter(k => k.tags).map(k => {
        const w = x => (100 * x / maxI).toFixed(1);
        return `<div class="icr" data-k="${k.kind}"><span class="il">${esc(k.kind.toUpperCase())}</span><span class="ib"><i class="m" style="width:${w(k.missing)}%"></i><i class="b" style="width:${w(k.mismatch)}%"></i><i class="r" style="width:${w(k.review)}%"></i></span><span class="iv">${k.missing + k.mismatch + k.review}</span></div>`;
      }).join('') || '<div class="soft">자료 없음</div>'}<div class="ileg"><i class="m"></i>누락 <i class="b"></i>값 다름 <i class="r"></i>확인 필요</div></div></div>
      <div class="card"><h3>검토 기준 <small class="soft">IN-1.0</small></h3><table class="t"><tbody>
        <tr><td>필수 칸</td><td>양식 카드의 필수 목록 (${R.required_confirmed.length ? `확인된 양식 ${R.required_confirmed.map(esc).join(' · ')}` : '<b>제안값 — 사용자 확인 전</b>'})</td></tr>
        <tr><td>Process Data</td><td>Tag 로 PDS 행을 찾아 유체 · 상 · 압력 · 온도 · 밀도 · 유량 비교, 없으면 '없음'</td></tr>
        <tr><td>PMS</td><td>Pipe Class → PMS Class · Flange Rating</td></tr>
        <tr><td>Line List</td><td>Line No → Pipe Class · Design P/T · Size. <b>Line 의 Design 이 Datasheet 보다 높으면 지적</b> (Line No 칸이 없는 양식은 PDS 의 Line No)</td></tr>
        <tr><td>Item 규칙</td><td>같은 Datasheet 안의 값끼리만 (PT/PG Range ↔ 운전압력 · PSV Set ↔ Design) — 사람 확인 표시</td></tr></tbody></table></div></div>`;
  el.onclick = e => {
    if (e.target.closest('.vlink')) return;
    const k = e.target.closest('[data-k]'); if (k) { location.href = pageUrl(k.dataset.k); return; }      // each item is its own page
    const g = e.target.closest('[data-g]'); if (g) { V.go(g.dataset.g); return; }
    if (e.target.closest('[data-req]')) reqDialog();
  };
}

async function reqDialog() {
  const ks = await kinds(), cur = await api('GET', `/projects/${S.pid}/inst/required`);
  const fid = LS.get('inst.reqform', ks[0].form_id), k = ks.find(x => x.form_id === fid) || ks[0];
  const on = new Set(cur.confirmed[k.form_id] || k.required);
  const html = `<div class="soft" style="margin-bottom:6px">양식 카드가 제안한 필수 칸입니다. 고쳐서 저장하면 이 프로젝트에서는 그 목록으로 '누락'을 봅니다 (기록에 남음).</div>
    <select name="form" id="rqf">${ks.map(x => `<option value="${x.form_id}" ${x.form_id === k.form_id ? 'selected' : ''}>${esc(x.kind.toUpperCase())} · ${esc(x.name)} (양식 ${x.form_id})${cur.confirmed[x.form_id] ? ' ✓' : ''}</option>`).join('')}</select>
    <input type="hidden" name="keys" id="rqkeys" value="${esc([...on].join(','))}"><div class="rqlist">${k.fields.filter((f, i, a) => a.findIndex(y => y.key === f.key) === i).map(f => `<label><input type="checkbox" data-rk="${esc(f.key)}" ${on.has(f.key) ? 'checked' : ''}> ${f.no}. ${esc(f.label)} <small class="soft">${esc(f.key)}</small></label>`).join('')}</div>`;
  const p = V.modal(`필수 칸 확인 — ${k.kind.toUpperCase()}`, html, [['닫기', null], ['이 양식 저장', 'form', 1]]);
  setTimeout(() => {
    const s = $('#rqf'); if (s) s.onchange = () => { LS.set('inst.reqform', s.value); $('#modal').hidden = true; reqDialog(); };
    $('#mBody').onchange = e => { if (e.target.dataset.rk !== undefined) $('#rqkeys').value = $$('#mBody [data-rk]').filter(x => x.checked).map(x => x.dataset.rk).join(','); };
  }, 0);
  const r = await p;
  if (!r) return;
  const keys = (r.keys || '').split(',').filter(Boolean);
  await api('PUT', `/projects/${S.pid}/inst/required`, { form_id: k.form_id, keys });
  toast(`양식 ${k.form_id} 필수 칸 ${keys.length}개 저장`); renderBoard();
}

/* ── Instrument Review — tag list · PDF · findings ─────────────────────────────── */
async function renderReview() {
  const el = $('#v-ireview');
  await kinds();
  if (QSHEET && !I.deep) {                                 // open that datasheet once, on its item's screen
    I.deep = 1; I.sel = QSHEET;
    try { const d0 = await api('GET', `/inst/sheets/${QSHEET}`); if (d0.kind !== I.kind) { I.kind = d0.kind; I.rows = null; } paintBrand(); } catch (_) { /* not found: the item's first tag */ }
  }
  if (!I.rows || I.rowsKind !== I.kind || I.rowsPid !== S.pid) {
    I.rows = (await api('GET', `/projects/${S.pid}/inst/sheets${I.kind ? `?kind=${I.kind}` : ''}`)).rows; I.rowsKind = I.kind; I.rowsPid = S.pid;
  }
  if (!I.counts || I.countsPid !== S.pid) { const s = await api('GET', `/projects/${S.pid}/inst/summary`); I.counts = Object.fromEntries(s.kinds.map(k => [k.kind, k.tags])); I.countsPid = S.pid; }
  el.classList.add('full');
  const chips = '' && `<div class="ichips"><button data-kind="" class="${!I.kind ? 'on' : ''}">전체</button>${I.kinds.map(k => `<button data-kind="${k.kind}" class="${I.kind === k.kind ? 'on' : ''} ${I.counts[k.kind] ? '' : 'z'}" title="${esc(k.name)} · 양식 ${k.form_id}">${esc(k.kind.toUpperCase())}<small>${I.counts[k.kind] || 0}</small></button>`).join('')}</div>`;
  const kk = (I.kinds || []).find(x => x.kind === I.kind);
  el.innerHTML = `<div class="ivh"><span class="ikt">${esc(I.kind ? (I.kind === 'analyzer' ? 'AT' : I.kind.toUpperCase()) : 'Instrument')}<small>${I.kind ? esc(kname(I.kind)) + (kk ? ` · Form ${esc(kk.form_id)}` : '') : '모든 종류'} · Tag ${I.rows.length}</small></span>${chips}<span class="sp"></span>
      <a class="btnlink" href="/api/valve/projects/${S.pid}/inst/markup.pdf${I.kind ? `?kind=${I.kind}` : ''}" download title="지적이 있는 Datasheet 전부 — 칸 음영 + 화살표 설명선(이유), Acrobat 에서 고칠 수 있음">⇩ Mark-up PDF</a>
      <a class="btnlink" href="/api/valve/projects/${S.pid}/inst/review.xlsx${I.kind ? `?kind=${I.kind}` : ''}" download>⇩ Excel</a></div>
    <div class="wb iwb"><div class="wb-left"><div class="iqrow"><input class="iq" placeholder="Tag 찾기 ( / )" value="${esc(I.filt)}"><label title="지적이 남은 Tag 만"><input type="checkbox" id="ionly" ${I.onlyIss ? 'checked' : ''}> 지적만</label></div><div class="ikeys soft">J/K Tag · N/P 지적 · C 확인 · E 문구 · X 무시</div><div class="itags" id="itags"></div></div>
      <div class="wb-center" id="iview"></div><div class="wb-right"><div class="tabs" id="itabs">${[['find', '검토 결과'], ['vals', '읽은 값'], ['rev', 'Rev · 문서']].map(([k, l]) => `<button data-t="${k}" class="${I.tab === k ? 'on' : ''}">${l}</button>`).join('')}</div><div class="rbody" id="ibody"></div></div></div>`;
  I.viewer = new V.Viewer($('#iview'), { onOverlay: o => { if (o.key) { I.selKey = o.key; drawRight(); } } });
  drawTags();
  $('.iq', el).oninput = e => { I.filt = e.target.value; drawTags(); };
  $('#ionly').onchange = e => { I.onlyIss = e.target.checked; drawTags(); };
  $('#itabs').onclick = e => { const b = e.target.closest('[data-t]'); if (!b) return; I.tab = b.dataset.t; $$('#itabs button').forEach(x => x.classList.toggle('on', x === b)); drawRight(); };
  const want = I.rows.find(r => r.id === I.sel) || I.rows[0];
  if (want) await openSheet(want.id); else { $('#ibody').innerHTML = '<div class="empty">이 종류의 Datasheet 가 없습니다.</div>'; $('#iview .stage').innerHTML = '<div class="empty" style="color:#fff">Document Management 에 Instrument Datasheet PDF 를 올리세요.</div>'; }
}
function drawTags() {
  const q = (I.filt || '').toUpperCase().replace(/[\s_-]/g, '');
  $('#itags').innerHTML = I.rows.filter(r => (!q || r.tag.toUpperCase().replace(/[\s_-]/g, '').includes(q)) && (!I.onlyIss || r.issues)).map(r => {
    const c = r.counts;
    return `<div class="itag ${r.id === I.sel ? 'on' : ''}" data-id="${r.id}"><div><b>${esc(r.tag)}</b>${r.test_data ? '<span class="tst">TEST</span>' : ''}<span class="sp"></span>${r.review_code ? `<span class="icd" title="Review Code">${esc(r.review_code)}</span>` : ''}<small>Rev ${esc(r.rev || '-')}</small></div>
      <div class="soft">${esc(r.kind.toUpperCase())} · ${esc((r.service || '').slice(0, 30))}</div>
      <div>${r.issues ? `${c.Mismatch ? rp('Mismatch', c.Mismatch) : ''}${c.Missing ? rp('Missing', c.Missing) : ''}${c['Review Required'] ? rp('Review Required', c['Review Required']) : ''}` : '<span class="ir ir-ok"><i>✓</i>지적 없음</span>'}${r.in_pds ? '' : '<span class="ir ir-na"><i>–</i>PDS 없음</span>'}</div></div>`;
  }).join('') || '<div class="empty">없음</div>';
  $('#itags').onclick = e => { const t = e.target.closest('[data-id]'); if (t) openSheet(+t.dataset.id); };
}
async function openSheet(id) {
  I.sel = id; I.selKey = null;
  $$('#itags .itag').forEach(x => x.classList.toggle('on', +x.dataset.id === id));
  I.d = await api('GET', `/inst/sheets/${id}`);
  await I.viewer.load(I.d.document_id, I.d.pages);
  paintOv(); drawRight();
}
function rowOf(key) { if ((key || '').startsWith('row:')) return (I.d?.rows || []).find(r => r.no === key.slice(4) && r.bbox) || null; return (I.d?.rows || []).find(r => r.std_key === key && r.bbox) || null; }
function paintOv() {
  const cat = { Mismatch: 'error', Missing: 'missing', 'Review Required': 'missing' };
  const ov = [];
  I.d.review.forEach((f, i) => {
    if (!cat[f.result]) return;
    const r = rowOf(f.key) || (f.key === 'line_no' || f.key === 'line_size' ? rowOf('line_no') : null); if (!r) return;
    ov.push({ page: r.page, bbox: r.bbox, cat: cat[f.result], key: f.key, title: `${f.rule} · ${f.item}`, text: f.reason, sel: I.selKey === f.key, no: i + 1 });
  });
  I.viewer.setOverlays(ov);
}
async function reloadSheet() {                             // after a decision / code: same tag, fresh counts everywhere
  const keep = I.selKey; I.d = await api('GET', `/inst/sheets/${I.d.id}`); I.selKey = keep;
  const r = (I.rows || []).find(x => x.id === I.d.id); if (r) Object.assign(r, { counts: I.d.counts, issues: I.d.issues, review_code: I.d.review_code, suggested_code: I.d.suggested_code, status: I.d.status });
  drawTags(); paintOv(); drawRight();
}
async function setCode(code) { await api('PUT', `/inst/sheets/${I.d.id}/code`, { code }); toast(`Review Code ${code || '미정'} 저장`); await reloadSheet(); }
async function decide(fk, dec) {
  if (!fk) return;
  let body = { fkey: fk, decision: dec };
  if (dec === 'Dismissed' || dec === 'Modified') {
    const f = I.d.review.find(x => x.fkey === fk) || {};
    const html = `${dec === 'Modified' ? `<div class="soft">Vendor 에 보낼 문구 (Mark-up PDF · CRS 에 이 글이 나갑니다 — 영어로 쓰면 PDF 설명선에도 그대로)</div><textarea name="text" rows="4" style="width:100%">${esc(f.decision?.text || f.reason || '')}</textarea>` : ''}
      <div class="soft" style="margin-top:6px">이유</div><select name="reason_cat"><option value="">— 선택 —</option>${(I.d.reasons || []).map(r => `<option>${esc(r)}</option>`).join('')}</select>
      <input name="reason" placeholder="자세한 이유 (기록에 남음)" style="width:100%;margin-top:6px" value="${esc(f.decision?.reason || '')}">`;
    const r = await V.modal(dec === 'Modified' ? '지적 문구 수정' : '이 지적 무시', html, [['취소', null], [dec === 'Modified' ? '저장' : '무시', 'form', 1]]);
    if (!r) return;
    if (dec === 'Dismissed' && !r.reason_cat && !r.reason) { toast('무시하려면 이유가 필요합니다', 1); return; }
    body = Object.assign(body, r);
  }
  await api('PUT', `/inst/sheets/${I.d.id}/decisions`, body);
  toast({ Confirmed: '확인 — Vendor 에 지적으로 남김', Modified: '문구 수정 저장', Dismissed: '무시 — 지적 수 · PDF · CRS 에서 빠짐', Open: '결정 지움' }[dec]);
  await reloadSheet();
}
function drawRight() {
  const d = I.d, b = $('#ibody'); if (!d || !b) return;
  const head = `<div class="ihead"><b>${esc(d.tag)}</b> ${pill(d.status)} <span class="soft">${esc(kname(d.kind))} · 양식 ${esc(d.form_id)}</span>
    <div class="soft">${esc(d.doc_no || '(문서번호 못 읽음)')} · Rev ${esc(d.rev || '-')}${d.rev_date ? ' · ' + esc(d.rev_date) : ''}${d.test_data ? ' · <b class="tst">TEST DATA</b>' : ''}</div>
    <div class="ist"><a class="btnlink" href="/api/valve/inst/sheets/${d.id}/markup.pdf" download title="이 Datasheet 에 지적을 표시한 PDF — 칸 음영 + 화살표 설명선(이유)">⇩ 이 Tag Mark-up PDF</a> <select id="ists">${['Not Reviewed', 'Under Review', 'Accepted', 'Rejected', 'Commented', 'Resolved'].map(s => `<option ${s === d.status ? 'selected' : ''}>${s}</option>`).join('')}</select></div></div>
    <div class="icode"><span class="soft">Review Code</span><select id="icode"><option value="">— 미정 —</option>${(d.codes || []).map(c => `<option value="${esc(c.code)}" ${c.code === d.review_code ? 'selected' : ''}>${esc(c.code)} · ${esc(c.label)}</option>`).join('')}</select>${d.suggested_code && d.suggested_code !== d.review_code ? `<button class="ghost" data-sugg="${esc(d.suggested_code)}" title="남은 지적으로 계산한 제안 — 눌러 적용">제안 ${esc(d.suggested_code)} · ${esc((d.codes || []).find(c => c.code === d.suggested_code)?.label || '')}</button>` : ''}</div>`;
  if (I.tab === 'find') {
    const isBad = f => ['Mismatch', 'Missing', 'Review Required'].includes(f.result);
    const DEC = { Confirmed: ['ok', '✓ 확인 — Vendor 에 지적'], Modified: ['rev', '✎ 문구 수정'], Dismissed: ['na', '✕ 무시'] };
    const decLine = f => { const x = f.decision; if (!x) return ''; const [c, l] = DEC[x.decision] || ['na', x.decision];
      return `<div class="idec"><span class="ir ir-${c}">${l}</span><span class="soft">${esc(x.by || '')} · ${esc((x.at || '').replace('T', ' ').slice(0, 16))}${x.origin ? ` · <b>${esc(x.origin)} 에서 이어받음</b>` : ''}${x.reason_cat || x.reason ? ` · ${esc([x.reason_cat, x.reason].filter(Boolean).join(': '))}` : ''}</span></div>`; };
    const acts = f => (isBad(f) || f.result === 'Dismissed') ? `<div class="iacts" data-fk="${esc(f.fkey || '')}">${f.result === 'Dismissed' ? '<button data-dec="Open">되돌리기</button>' : `<button data-dec="Confirmed" class="${f.decision?.decision === 'Confirmed' ? 'on' : ''}" title="Vendor 에 보낼 지적으로 확정 (C)">✓ 확인</button><button data-dec="Modified" title="지적 문구를 고쳐 씀 (E)">✎ 문구</button><button data-dec="Dismissed" title="지적이 아님 — 이유를 남김 (X)">✕ 무시</button>${f.decision ? '<button data-dec="Open" class="ghost" title="결정 지우기">↺</button>' : ''}`}</div>` : '';
    const card = ([f, i]) => `
        <div class="ifind ${I.selKey === f.key ? 'sel' : ''} r-${(RES[f.result] || ['na'])[0]}" data-key="${esc(f.key)}"><div><span class="no">${i + 1}</span>${rp(f.result)} <b>${esc(f.item)}</b><span class="sp"></span><small class="soft" title="${esc(d.rules[f.rule] || '')}">${esc(f.rule)}</small></div>
          ${isBad(f) ? `<div class="cmp"><span>Datasheet</span><b>${esc(f.ds || '—')}</b><span>기준</span><b>${esc(f.ref || '—')}</b></div>
          <div class="why">${esc(f.reason)}${f.human ? ' · <b>사람 확인</b>' : ''}</div><div class="src">${esc(f.source || '')}</div>${decLine(f)}${acts(f)}` : f.result === 'Dismissed' ? `<div class="okline">${esc(f.ds || '—')} <span class="soft">/ ${esc(f.ref || '—')}</span></div>${decLine(f)}${acts(f)}` : `<div class="okline">${esc(f.ds || '—')} <span class="soft">= ${esc(f.ref || '—')}</span></div>`}</div>`;
    const n = { Mismatch: 0, Missing: 0, 'Review Required': 0 }; d.review.forEach(f => { if (isBad(f)) n[f.result]++; });
    const tot = n.Mismatch + n.Missing + n['Review Required'];
    const strip = `<div class="istrip ${tot ? '' : 'ok'}">${tot ? `<b>지적 ${tot}건</b>${n.Mismatch ? rp('Mismatch', n.Mismatch) : ''}${n.Missing ? rp('Missing', n.Missing) : ''}${n['Review Required'] ? rp('Review Required', n['Review Required']) : ''}` : '<b>✓ 지적 없음</b>'}<span class="sp"></span><label title="같다고 확인된 항목도 펼쳐 보기"><input type="checkbox" id="iok" ${I.showOk ? 'checked' : ''}> OK 항목 보기</label></div>`;
    const sec = GROUPS.map(([p, l]) => {
      const rs = d.review.map((f, i) => [f, i]).filter(([f]) => f.rule.startsWith(p));
      if (!rs.length) return '';
      const bad = rs.filter(([f]) => isBad(f)), ok = rs.filter(([f]) => !isBad(f) && f.result !== 'Dismissed'), dis = rs.filter(([f]) => f.result === 'Dismissed');
      return `<div class="igrp ${bad.length ? '' : 'allok'}"><h4>${l}${bad.length ? `<span class="ir ir-bad"><i>!</i>지적 <b>${bad.length}</b></span>` : '<span class="ir ir-ok"><i>✓</i>OK</span>'}<span class="soft cnt">${ok.length ? `같음 ${ok.length}` : ''}</span></h4>${bad.map(card).join('')}${I.showOk ? dis.map(card).join('') + ok.map(card).join('') : dis.length ? `<div class="soft dismissed">무시한 지적 ${dis.length} — 'OK 항목 보기' 로 펼침</div>` : ''}</div>`;
    }).join('');
    b.innerHTML = head + strip + (sec || '<div class="empty">검토할 기준 문서가 없습니다</div>');
    const ck = $('#iok'); if (ck) ck.onchange = () => { I.showOk = ck.checked; LS.set('inst.showok', I.showOk); drawRight(); };
  } else if (I.tab === 'vals') {
    let s0 = '';
    b.innerHTML = head + `<table class="t ivals"><tbody>${d.rows.map(r => {
      const sh = r.section && r.section !== s0 ? `<tr class="isec"><td colspan="3">${esc(r.section)}</td></tr>` : ''; if (r.section) s0 = r.section;
      const subs = Object.entries(r.sub || {}).map(([k, v]) => `<span class="isub"><small>${esc(k)}</small> ${esc(v)}</span>`).join('');
      return `${sh}<tr data-key="${esc(r.std_key || '')}" class="${r.value || subs ? '' : 'emp'}"><td class="soft">${esc(r.no)}</td><td>${esc(r.label)}</td><td>${esc(r.value)}${subs}</td></tr>`;
    }).join('')}</tbody></table>`;
  } else {
    b.innerHTML = head + `<div class="igrp"><h4>Revision</h4><table class="t"><thead><tr><th>Rev</th><th>Date</th><th>Doc No</th><th>File</th></tr></thead><tbody>${d.revs.map(r => `<tr class="${r.id === d.id ? 'on' : ''}" data-open="${r.id}"><td><b>${esc(r.rev || '-')}</b></td><td>${esc(r.date || '')}</td><td>${esc(r.doc_no || '')}</td><td>${esc(r.file || '')}</td></tr>`).join('')}</tbody></table></div>
      <div class="igrp"><h4>양식 식별</h4><div class="soft">점수 ${d.identify?.score} · ${esc((d.identify?.why || []).join(' · '))}<br>다음 후보 ${esc(d.identify?.runner_up || '-')} (${d.identify?.runner_up_score ?? '-'})</div></div>
      <div class="igrp"><h4>원본</h4><a href="/api/valve/documents/${d.document_id}/file" target="_blank">${esc(d.file || '')}</a> · 쪽 ${d.pages.join(', ')}</div>`;
  }
  const icode = $('#icode'); if (icode) icode.onchange = async e => { await setCode(e.target.value); };
  $('#ists').onchange = async e => { await api('PUT', `/inst/sheets/${d.id}/status`, { status: e.target.value }); d.status = e.target.value; const r = I.rows.find(x => x.id === d.id); if (r) r.status = d.status; toast('상태 저장'); drawRight(); };
  b.onclick = e => {
    const sg = e.target.closest('[data-sugg]'); if (sg) { setCode(sg.dataset.sugg); return; }
    const db = e.target.closest('[data-dec]'); if (db) { decide(db.closest('[data-fk]').dataset.fk, db.dataset.dec); return; }
    const o = e.target.closest('[data-open]'); if (o) { openSheet(+o.dataset.open); return; }
    const f = e.target.closest('[data-key]'); if (!f || !f.dataset.key) return;
    I.selKey = f.dataset.key; const r = rowOf(I.selKey) || (I.selKey.startsWith('line') ? rowOf('line_no') : null);
    paintOv(); $$('#ibody [data-key]').forEach(x => x.classList.toggle('sel', x.dataset.key === I.selKey));
    if (r) I.viewer.focus(r.page, r.bbox, r.label);
  };
}

/* keyboard: J/K next/prev tag · N/P next/prev finding · C confirm · E edit wording · X dismiss · / search */
addEventListener('keydown', e => {
  if (S.view !== 'ireview' || !I.d || e.ctrlKey || e.metaKey || e.altKey || !$('#modal').hidden || e.target.closest?.('input, textarea, select')) return;
  const k = e.key.toLowerCase();
  const vis = $$('#itags .itag').map(x => +x.dataset.id), at = vis.indexOf(I.d.id);
  if (k === 'j' || k === 'k') { const n = vis[at + (k === 'j' ? 1 : -1)]; if (n) { e.preventDefault(); openSheet(n).then(() => $(`#itags .itag[data-id="${n}"]`)?.scrollIntoView({ block: 'nearest' })); } return; }
  if (k === '/') { e.preventDefault(); $('#v-ireview .iq')?.focus(); return; }
  const cards = $$('#ibody .ifind').filter(c => c.querySelector('.iacts [data-dec="Confirmed"]'));
  const cur = cards.findIndex(c => c.classList.contains('sel'));
  if (k === 'n' || k === 'p') { const c = cards[cur < 0 ? 0 : Math.max(0, Math.min(cards.length - 1, cur + (k === 'n' ? 1 : -1)))]; if (c) { e.preventDefault(); c.click(); c.scrollIntoView({ block: 'nearest' }); } return; }
  const dec = { c: 'Confirmed', e: 'Modified', x: 'Dismissed' }[k];
  if (dec && cur >= 0) { e.preventDefault(); decide(cards[cur].querySelector('[data-fk]').dataset.fk, dec); }
});

/* ── Instrument List · IO List — one screen each: comparison with the datasheets + the list as read ─────────── */
async function renderLists() {
  const el = $('#v-ilist'), L = I.list, nm = L === 'io_list' ? 'IO List' : 'Instrument List', lname = L === 'io_list' ? 'IO List' : 'Instrument Index';
  el.innerHTML = `<div class="vh"><h2>${nm}</h2></div><div class="soft">불러오는 중…</div>`;
  await kinds();
  const d = await api('GET', `/projects/${S.pid}/inst/listcmp?list=${L}`);
  const info = d.lists[L], c = d.counts[lname] || {};
  const tabs = [['cmp', 'Datasheet 대조'], ['rec', 'List 내용']].map(([k, l]) => `<button data-lt="${k}" class="${I.ltab === k ? 'on' : ''}">${l}</button>`).join('');
  const head = `<div class="vh"><h2>${nm}</h2><span class="soft">${info ? esc([info.files.join(' · '), info.doc_no, info.rev ? 'Rev ' + info.rev : '', 'Tag ' + info.tags].filter(Boolean).join(' · ')) : '아직 없음'}</span><span class="sp"></span>
      <button data-g="docs">자료 올리기</button><a class="btnlink" href="/api/valve/projects/${S.pid}/inst/listcmp.xlsx?list=${L}" download>⇩ Excel</a></div>`;
  if (!info) {
    el.innerHTML = head + `<div class="card"><div class="empty">${nm} PDF 가 없습니다 — <b>Document Management › Instrument Index · IO List</b> 에 올리면 Tag 별로 읽고 Datasheet 와 대조합니다 (기준 = Datasheet: 누락 · 값 다름 · List 에만).</div></div>`;
  } else {
    const kpi = ['누락', '값 다름', 'List 에만', 'OK'].map(r => `<button data-lf="${r}" class="${I.lfilt === r ? 'on' : ''}">${rp(r)}<b>${c[r] || 0}</b></button>`).join('');
    let body;
    if (I.ltab === 'cmp') {
      const rows = d.rows.filter(x => I.lfilt ? x.result === I.lfilt : x.result !== 'OK');
      body = `<div class="card" style="padding:0;overflow:auto"><table class="t"><thead><tr><th>결과</th><th>Tag</th><th>Item</th><th>항목</th><th>Datasheet</th><th>${lname}</th><th>이유</th><th>Rule</th></tr></thead><tbody>
        ${rows.map(x => `<tr ${x.sheet_id ? `data-sid="${x.sheet_id}" data-sk="${x.kind}" class="link"` : x.valve_ds ? `data-vds="${x.valve_ds}" data-vp="${esc(x.valve_project)}" class="link"` : ''}><td>${rp(x.result)}</td><td><b>${esc(x.tag)}</b></td><td>${esc(kindLabel(x.kind))}</td><td>${esc(x.field)}</td>
          <td>${esc(x.ds)}</td><td>${esc(x.lst)}</td><td class="soft">${esc(x.reason)}</td><td class="soft">${esc(x.rule)}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">차이 없음</td></tr>'}</tbody></table></div>`;
    } else {
      const io = L === 'io_list';
      body = `<div class="card" style="padding:0;overflow:auto"><table class="t"><thead><tr><th>Tag</th><th>Loop</th><th>Type</th><th>Service</th><th>P&amp;ID</th><th>Line</th><th>Range</th>
        ${io ? '<th>IO</th><th>Logic</th>' : '<th>Datasheet No</th><th>Manufacturer</th><th>Model</th>'}<th>Datasheet</th><th>대조</th><th>p.</th></tr></thead><tbody>
        ${d.records.map(r => `<tr ${r.sheet_id ? `data-sid="${r.sheet_id}" data-sk="${r.ds_kind}" class="link"` : r.valve_ds ? `data-vds="${r.valve_ds}" data-vp="${esc(r.valve_project)}" class="link"` : ''}><td><b>${esc(r.tag)}</b></td><td>${esc(r.loop || '')}</td><td>${esc(r.inst_type || '')}</td><td>${esc(r.service || '')}</td>
          <td>${esc(r.pid_no || '')}</td><td>${esc(r.line_no || '')}</td><td>${esc(r.range || '')}</td>
          ${io ? `<td>${esc(r.io_typical || '')}</td><td>${esc(r.logic_no || '')}</td>` : `<td>${esc(r.datasheet_no || '')}</td><td>${esc(r.manufacturer || '')}</td><td>${esc(r.model || '')}</td>`}
          <td>${r.ds_kind ? esc(kindLabel(r.ds_kind)) : '<span class="ir ir-lo"><i>≡</i>없음</span>'}</td><td>${r.findings ? `<span class="ir ir-bad">${r.findings}</span>` : '<span class="ir ir-ok">OK</span>'}</td><td class="soft">${r.page || ''}</td></tr>`).join('')}</tbody></table></div>`;
    }
    el.innerHTML = head + `<div class="ilhead"><div class="tabs ltabs">${tabs}</div><div class="ilc">${kpi}</div><span class="soft">대조한 Datasheet: Instrument ${d.n_inst} Tag · Valve ${d.n_valve} Tag (Ball · Globe · Butterfly · PSV)</span></div>` + body;
  }
  el.onclick = e => {
    const g = e.target.closest('[data-g]'); if (g) { V.go(g.dataset.g); return; }
    const t = e.target.closest('[data-lt]'); if (t) { I.ltab = t.dataset.lt; renderLists(); return; }
    const b = e.target.closest('[data-lf]'); if (b) { I.lfilt = I.lfilt === b.dataset.lf ? '' : b.dataset.lf; I.ltab = 'cmp'; renderLists(); return; }
    const r = e.target.closest('[data-sid]'); if (r) { location.href = pageUrl(r.dataset.sk || I.kind, r.dataset.sid); return; }
    const v = e.target.closest('[data-vds]'); if (v) location.href = valveUrl(v.dataset.vp, v.dataset.vds);
  };
}

/* ── item page › Dashboard — this item only ───────────────────────────────────────────── */
async function renderItemDash() {
  const el = $('#v-idash');
  el.innerHTML = `<div class="vh"><h2>${esc(pageName())}</h2></div><div class="soft">불러오는 중…</div>`;
  await kinds();
  const [s, sh] = await Promise.all([api('GET', `/projects/${S.pid}/inst/summary`), api('GET', `/projects/${S.pid}/inst/sheets?kind=${I.kind}`)]);
  const k = s.kinds.find(x => x.kind === I.kind) || { tags: 0, ok_tags: 0, missing: 0, mismatch: 0, review: 0, not_in_pds: 0, sheets: 0, test: 0, revs: {} };
  const R = s.refs, rows = sh.rows; I.rows = rows; I.rowsKind = I.kind; I.rowsPid = S.pid;
  const ref = (l, v) => `<div class="iref ${v ? 'on' : ''}" title="${esc(v || '')}"><b>${l}</b><span>${v ? esc(v.length > 40 ? v.slice(0, 38) + '…' : v) : '없음'}</span></div>`;
  const tile = (l, n, cls) => `<div class="kpi ${cls || ''}"><div class="l">${l}</div><div class="n">${n}</div></div>`;
  const kk = (I.kinds || []).find(x => x.kind === I.kind);
  el.innerHTML = `<div class="vh"><h2>${esc(pageName())}</h2><span class="soft">${esc(S.sum?.project?.name || '')}${kk ? ` · Form ${esc(kk.form_id)}` : ''} · Datasheet 검토 현황</span><span class="sp"></span>
      <button data-g="docs">자료 올리기</button><button class="pri" data-g="ireview">Datasheet Review 열기</button></div>
    <div class="irefs">${ref('Process Data (PDS)', R.pds)}${ref('PMS', R.pms)}${ref('Process Line List', R.linelist)}${ref('Instrument Index', R.instrument_index)}${ref('IO List', R.io_list)}</div>
    ${!k.tags ? `<div class="banner info">아직 ${esc(pageName())} Datasheet 가 없습니다 — <b>Document Management › Instrument Datasheet PDF</b> 에 올리면 양식을 알아보고 Tag 별로 검토합니다.</div>` : ''}
    ${k.test ? `<div class="banner warn">시험 자료(TEST DATA 도장) ${k.test}개 Tag — 실제 Datasheet 가 아닙니다.</div>` : ''}
    ${k.tags ? `<div class="isum ${k.tags === k.ok_tags ? 'allok' : ''}"><div class="big"><b>${k.ok_tags}</b><span>/ ${k.tags} Tag</span></div>
      <div class="txt"><b>${k.tags === k.ok_tags ? '모든 Tag 에 지적이 없습니다' : `${k.tags - k.ok_tags}개 Tag 에 확인할 지적이 있습니다`}</b>
        <span>${rp('Mismatch', k.mismatch)}${rp('Missing', k.missing)}${rp('Review Required', k.review)}</span></div>
      <div class="prog"><i style="width:${Math.round(100 * k.ok_tags / k.tags)}%"></i></div><div class="pct">${Math.round(100 * k.ok_tags / k.tags)}%</div></div>
    <div class="kpis ikpis six">${tile('Tag', k.tags)}${tile('Datasheet', k.sheets)}${tile('지적 없음', k.ok_tags, 'okk')}${tile('값 다름', k.mismatch, k.mismatch ? 'warn' : '')}${tile('누락', k.missing, k.missing ? 'warn' : '')}${tile('PDS 없음', k.not_in_pds)}</div>
    <div class="card" style="padding:0;overflow:auto"><table class="t itbl"><thead><tr><th>Tag</th><th>Service</th><th>Rev</th><th>Area</th><th>Unit</th><th>Pipe Class</th><th>Line No</th><th>검토 결과</th><th>PDS</th><th>Status</th></tr></thead><tbody>
      ${rows.map(r => { const c = r.counts; return `<tr class="link" data-open="${r.id}"><td><b>${esc(r.tag)}</b>${r.test_data ? '<span class="tst">TEST</span>' : ''}</td><td>${esc(r.service || '')}</td><td>${esc(r.rev || '-')}</td><td>${esc(r.area || '')}</td><td>${esc(r.unit || '')}</td>
        <td>${esc(r.piping_class || '')}</td><td>${esc(r.line_no || '')}</td>
        <td>${r.issues ? `${c.Mismatch ? rp('Mismatch', c.Mismatch) : ''}${c.Missing ? rp('Missing', c.Missing) : ''}${c['Review Required'] ? rp('Review Required', c['Review Required']) : ''}` : '<span class="ir ir-ok"><i>✓</i>지적 없음</span>'}</td>
        <td>${r.in_pds ? '<span class="ir ir-ok"><i>✓</i>있음</span>' : '<span class="ir ir-na"><i>–</i>없음</span>'}</td><td>${pill(r.status)}</td></tr>`; }).join('')}</tbody></table></div>` : ''}`;
  el.onclick = e => {
    const g = e.target.closest('[data-g]'); if (g) { V.go(g.dataset.g); return; }
    const o = e.target.closest('[data-open]'); if (o) { I.sel = +o.dataset.open; V.go('ireview'); }
  };
}

/* ── Reports & Export ─────────────────────────────────────────────────────────────────── */
async function renderExport() {
  const el = $('#v-iexport'), q = MODE === 'item' ? `?kind=${I.kind}` : '', nm = pageName();
  const row = (t, d, href) => `<div class="iex"><div><b>${t}</b><div class="soft">${d}</div></div><a class="btnlink" href="${href}" download>⇩ 내려받기</a></div>`;
  el.innerHTML = `<div class="vh"><h2>Reports &amp; Export</h2><span class="soft">${esc(nm)}</span></div>
    <div class="card">${row('Mark-up PDF', '지적이 있는 Datasheet 에 칸 음영 + 영어 화살표 설명선(이유)을 PDF 주석으로 — Acrobat 에서 편집 가능', `/api/valve/projects/${S.pid}/inst/markup.pdf${q}`)}
      ${row('CRS — Comment Resolution Sheet', 'Vendor 에 보내는 지적 목록: 무시한 지적은 빠지고, 고친 문구 · Review Code · 빈 Vendor Reply / Close-out 칸', `/api/valve/projects/${S.pid}/inst/crs.xlsx${q}`)}
      ${row('검토 결과 Excel', 'Tag 별 요약 + 지적 목록 (Rule · Datasheet 값 · 기준 값 · 이유 · 출처)', `/api/valve/projects/${S.pid}/inst/review.xlsx${q}`)}
      ${row('Instrument List 대조 Excel', 'Datasheet → Instrument Index: 누락 · 값 다름 · List 에만 + List 내용', `/api/valve/projects/${S.pid}/inst/listcmp.xlsx?list=instrument_index`)}
      ${row('IO List 대조 Excel', 'Datasheet → IO List: 누락 · 값 다름 · List 에만 + List 내용', `/api/valve/projects/${S.pid}/inst/listcmp.xlsx?list=io_list`)}</div>
    <div class="card"><div class="iex"><div><b>필수 칸 확인</b><div class="soft">양식 카드가 제안한 필수 칸을 이 프로젝트 기준으로 확정합니다 (누락 판정에 쓰임)</div></div><button data-req>열기</button></div></div>`;
  el.onclick = e => { if (e.target.closest('[data-req]')) { const kk = (I.kinds || []).find(x => x.kind === I.kind); if (MODE === 'item' && kk) LS.set('inst.reqform', kk.form_id); kinds().then(reqDialog); } };
}

/* ── item page › <Item> List — every tag with its main values ─────────────────────────── */
async function itemRows() {
  if (!I.rows || I.rowsKind !== I.kind || I.rowsPid !== S.pid) { I.rows = (await api('GET', `/projects/${S.pid}/inst/sheets?kind=${I.kind}`)).rows; I.rowsKind = I.kind; I.rowsPid = S.pid; }
  return I.rows;
}
const openTag = id => { I.sel = +id; V.go('ireview'); };
const badges = r => { const c = r.counts; return r.issues ? `${c.Mismatch ? rp('Mismatch', c.Mismatch) : ''}${c.Missing ? rp('Missing', c.Missing) : ''}${c['Review Required'] ? rp('Review Required', c['Review Required']) : ''}` : '<span class="ir ir-ok"><i>✓</i>지적 없음</span>'; };
async function renderTags() {
  const el = $('#v-itags'); await kinds();
  const rows = await itemRows(), q = (I.tq || '').toUpperCase();
  const show = rows.filter(r => !q || [r.tag, r.service, r.doc_no, r.piping_class, r.line_no].join(' ').toUpperCase().includes(q));
  el.innerHTML = `<div class="vh"><h2>${esc(pageName())} — List</h2><span class="soft">최신 Rev 기준 Tag ${rows.length}개 · 줄을 누르면 Datasheet Review</span><span class="sp"></span>
      <input class="tq" placeholder="Tag · Service · Line 찾기" value="${esc(I.tq || '')}"><a class="btnlink" href="/api/valve/projects/${S.pid}/inst/review.xlsx?kind=${I.kind}" download>⇩ Excel</a></div>
    <div class="card" style="padding:0;overflow:auto"><table class="t itbl"><thead><tr><th>Tag</th><th>Service</th><th>Doc No</th><th>Rev</th><th>P&amp;ID</th><th>Pipe Class</th><th>Line No</th><th>Fluid</th>
      <th>Oper. P</th><th>Design P</th><th>Design T</th><th>Range</th><th>Manufacturer</th><th>Model</th><th>검토 결과</th><th>Code</th><th>Status</th></tr></thead><tbody>
      ${show.map(r => { const v = r.vals || {}; return `<tr class="link" data-open="${r.id}"><td><b>${esc(r.tag)}</b>${r.test_data ? '<span class="tst">TEST</span>' : ''}</td><td>${esc(r.service || '')}</td><td>${esc(r.doc_no || '')}</td><td>${esc(r.rev || '-')}</td>
        <td>${esc(v.pid_no || '')}</td><td>${esc(r.piping_class || '')}</td><td>${esc(r.line_no || '')}</td><td>${esc([v.fluid, v.phase].filter(Boolean).join(' / '))}</td><td>${esc(v.op_pressure || '')}</td><td>${esc(v.design_pressure || '')}</td>
        <td>${esc(v.design_temp || '')}</td><td>${esc(v.range || '')}</td><td>${esc(v.manufacturer || '')}</td><td>${esc(v.model || '')}</td><td>${badges(r)}</td><td>${r.review_code ? `<b>${esc(r.review_code)}</b>` : `<span class="soft" title="제안">(${esc(r.suggested_code || '')})</span>`}</td><td>${pill(r.status)}</td></tr>`; }).join('') || '<tr><td colspan="17" class="empty">Datasheet 가 없습니다 — Document Management 에 올리세요</td></tr>'}</tbody></table></div>`;
  $('.tq', el).oninput = e => { I.tq = e.target.value; clearTimeout(renderTags.t); renderTags.t = setTimeout(() => renderTags().then(() => { const i = $('#v-itags .tq'); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }), 200); };
  el.onclick = e => { const o = e.target.closest('[data-open]'); if (o) openTag(o.dataset.open); };
}

/* ── item page › Process Data Verification · PMS Compliance · Line List Check ─────────── */
const CHECK = { iproc: ['pds', 'Process Data Verification', 'Process Data (PDS)', 'Tag 로 PDS 행을 찾아 유체 · 상 · 압력 · 온도 · 밀도 · 유량을 비교합니다. PDS 에 Tag 가 없으면 \'없음\'.'],
  ipms: ['pms', 'PMS Compliance', 'PMS', 'Pipe Class 가 PMS 에 있는지 · Rating 이 Flange Class 와 같은지 봅니다.'],
  iline: ['line', 'Line List Check', 'Process Line List', 'Line No 로 Line List 줄을 찾아 Pipe Class · Design P/T · Size 를 봅니다. Line 의 Design 이 Datasheet 보다 높으면 지적.'] };
async function renderCheck(view) {
  const [grp, title, refName, help] = CHECK[view], el = $('#v-' + view); await kinds();
  el.innerHTML = `<div class="vh"><h2>${title}</h2></div><div class="soft">불러오는 중…</div>`;
  const d = await api('GET', `/projects/${S.pid}/inst/findings?kind=${I.kind}&group=${grp}`);
  const f = I.cf?.[view] || '', order = ['Mismatch', 'Missing', 'Review Required', '없음', 'Datasheet Blank', 'OK'];
  const rows = d.rows.filter(x => f ? x.result === f : true).sort((a, b) => order.indexOf(a.result) - order.indexOf(b.result) || a.tag.localeCompare(b.tag));
  const kpi = order.filter(r => d.counts[r]).map(r => `<button data-cf="${r}" class="${f === r ? 'on' : ''}">${rp(r)}<b>${d.counts[r]}</b></button>`).join('');
  el.innerHTML = `<div class="vh"><h2>${title}</h2><span class="soft">${esc(pageName())} · Tag ${d.tags}</span><span class="sp"></span><button data-g="docs">자료 올리기</button></div>
    <div class="irefs"><div class="iref ${d.ref ? 'on' : ''}"><b>기준 문서 — ${refName}</b><span>${d.ref ? esc(d.ref) : '아직 없음 — Document Management 에 올리세요'}</span></div><div class="iref"><b>무엇을 보나</b><span>${help}</span></div></div>
    <div class="ilhead"><div class="ilc">${kpi || '<span class="soft">검사 결과 없음</span>'}</div>${f ? '<button data-cf="">전체 보기</button>' : ''}</div>
    <div class="card" style="padding:0;overflow:auto"><table class="t itbl"><thead><tr><th>결과</th><th>Tag</th><th>Rev</th><th>항목</th><th>Datasheet</th><th>${refName}</th><th>이유</th><th>출처</th><th>Rule</th></tr></thead><tbody>
      ${rows.map(x => `<tr class="link r-${(RES[x.result] || ['na'])[0]}" data-open="${x.sheet_id}"><td>${rp(x.result)}</td><td><b>${esc(x.tag)}</b></td><td>${esc(x.rev || '-')}</td><td>${esc(x.item)}</td><td>${esc(x.ds || '—')}</td><td>${esc(x.ref || '—')}</td>
        <td class="soft">${esc(x.reason)}${x.human ? ' · <b>사람 확인</b>' : ''}</td><td class="soft">${esc(x.source || '')}</td><td class="soft" title="${esc(d.rules[x.rule] || '')}">${esc(x.rule)}</td></tr>`).join('') || '<tr><td colspan="9" class="empty">해당 줄이 없습니다</td></tr>'}</tbody></table></div>`;
  el.onclick = e => {
    const g = e.target.closest('[data-g]'); if (g) { V.go(g.dataset.g); return; }
    const b = e.target.closest('[data-cf]'); if (b) { (I.cf ||= {})[view] = f === b.dataset.cf ? '' : b.dataset.cf; renderCheck(view); return; }
    const o = e.target.closest('[data-open]'); if (o) openTag(o.dataset.open);
  };
}

/* ── item page › Instrument List · IO List (this item's tags) ─────────────────────────── */
async function renderItemLists() {
  const el = $('#v-ilists'); await kinds();
  const L = I.il2 || 'instrument_index', lname = L === 'io_list' ? 'IO List' : 'Instrument Index', io = L === 'io_list';
  el.innerHTML = `<div class="vh"><h2>Instrument List · IO List</h2></div><div class="soft">불러오는 중…</div>`;
  const d = await api('GET', `/projects/${S.pid}/inst/listcmp?list=${L}`), info = d.lists[L];
  const rows = d.rows.filter(x => x.kind === I.kind), recs = d.records.filter(r => r.ds_kind === I.kind);
  const c = {}; rows.forEach(x => { c[x.result] = (c[x.result] || 0) + 1; });
  const f = I.il2f || '', show = rows.filter(x => f ? x.result === f : x.result !== 'OK');
  el.innerHTML = `<div class="vh"><h2>Instrument List · IO List</h2><span class="soft">${esc(pageName())} 의 Tag 만 · 기준 = Datasheet</span><span class="sp"></span>
      <a class="btnlink" href="${pageUrl(io ? 'iolist' : 'instindex')}" title="모든 Item 이 들어 있는 List 전체 화면">List 전체 보기 →</a><a class="btnlink" href="/api/valve/projects/${S.pid}/inst/listcmp.xlsx?list=${L}" download>⇩ Excel</a></div>
    <div class="ilhead"><div class="tabs ltabs"><button data-l2="instrument_index" class="${io ? '' : 'on'}">Instrument List</button><button data-l2="io_list" class="${io ? 'on' : ''}">IO List</button></div>
      <span class="soft">${info ? esc([info.files.join(' · '), info.rev ? 'Rev ' + info.rev : '', 'Tag ' + info.tags].filter(Boolean).join(' · ')) : '아직 없음 — Document Management › Instrument Index · IO List'}</span>
      <div class="ilc">${['누락', '값 다름', 'OK'].map(r => `<button data-l2f="${r}" class="${f === r ? 'on' : ''}">${rp(r)}<b>${c[r] || 0}</b></button>`).join('')}</div></div>
    <div class="card" style="padding:0;overflow:auto"><h3 style="padding:10px 12px 0">Datasheet 대조</h3><table class="t itbl"><thead><tr><th>결과</th><th>Tag</th><th>항목</th><th>Datasheet</th><th>${lname}</th><th>이유</th><th>Rule</th></tr></thead><tbody>
      ${show.map(x => `<tr class="link" data-open="${x.sheet_id}"><td>${rp(x.result)}</td><td><b>${esc(x.tag)}</b></td><td>${esc(x.field)}</td><td>${esc(x.ds)}</td><td>${esc(x.lst)}</td><td class="soft">${esc(x.reason)}</td><td class="soft">${esc(x.rule)}</td></tr>`).join('') || `<tr><td colspan="7" class="empty">${info ? '차이 없음' : 'List 가 없습니다'}</td></tr>`}</tbody></table></div>
    <div class="card" style="padding:0;overflow:auto"><h3 style="padding:10px 12px 0">${lname} 내용 <small class="soft">— 이 Item 의 Tag ${recs.length}개</small></h3><table class="t itbl"><thead><tr><th>Tag</th><th>Loop</th><th>Type</th><th>Service</th><th>P&amp;ID</th><th>Line</th><th>Range</th>
      ${io ? '<th>IO</th><th>Logic</th>' : '<th>Datasheet No</th><th>Manufacturer</th><th>Model</th>'}<th>대조</th><th>p.</th></tr></thead><tbody>
      ${recs.map(r => `<tr class="link" data-open="${r.sheet_id}"><td><b>${esc(r.tag)}</b></td><td>${esc(r.loop || '')}</td><td>${esc(r.inst_type || '')}</td><td>${esc(r.service || '')}</td><td>${esc(r.pid_no || '')}</td><td>${esc(r.line_no || '')}</td><td>${esc(r.range || '')}</td>
        ${io ? `<td>${esc(r.io_typical || '')}</td><td>${esc(r.logic_no || '')}</td>` : `<td>${esc(r.datasheet_no || '')}</td><td>${esc(r.manufacturer || '')}</td><td>${esc(r.model || '')}</td>`}
        <td>${r.findings ? `<span class="ir ir-bad"><i>!</i>${r.findings}</span>` : '<span class="ir ir-ok"><i>✓</i>OK</span>'}</td><td class="soft">${r.page || ''}</td></tr>`).join('') || '<tr><td colspan="12" class="empty">이 Item 의 Tag 가 List 에 없습니다</td></tr>'}</tbody></table></div>`;
  el.onclick = e => {
    const t = e.target.closest('[data-l2]'); if (t) { I.il2 = t.dataset.l2; I.il2f = ''; renderItemLists(); return; }
    const b = e.target.closest('[data-l2f]'); if (b) { I.il2f = f === b.dataset.l2f ? '' : b.dataset.l2f; renderItemLists(); return; }
    const o = e.target.closest('[data-open]'); if (o && o.dataset.open !== 'null') openTag(o.dataset.open);
  };
}

/* ── item page › Revision Comparison ──────────────────────────────────────────────────── */
async function renderRev() {
  const el = $('#v-irev'); await kinds();
  const rows = (await itemRows()).filter(r => (r.revs || []).length > 1);
  if (!rows.length) { el.innerHTML = `<div class="vh"><h2>Revision Comparison</h2><span class="soft">${esc(pageName())}</span></div><div class="card"><div class="empty">Revision 이 2개 이상인 Tag 가 아직 없습니다.<br><span class="soft">같은 Tag 의 새 Rev Datasheet 를 올리면 줄 단위로 바뀐 값을 보여 줍니다.</span></div></div>`; return; }
  const cur = rows.find(r => r.id === I.rvTag) || rows[0], revs = cur.revs, nw = revs.find(x => x.id === I.rvNew) || revs[revs.length - 1], pv = revs.find(x => x.id === I.rvPrev && x.id !== nw.id) || revs[Math.max(0, revs.indexOf(nw) - 1)];
  const d = await api('GET', `/inst/compare?prev=${pv.id}&new=${nw.id}`);
  const opt = (sel) => revs.map(x => `<option value="${x.id}" ${x.id === sel.id ? 'selected' : ''}>Rev ${esc(x.rev || '-')} ${esc(x.date || '')}</option>`).join('');
  el.innerHTML = `<div class="vh"><h2>Revision Comparison</h2><span class="soft">${esc(pageName())} · Rev 가 2개 이상인 Tag ${rows.length}개</span></div>
    <div class="ilhead"><select id="rvt">${rows.map(r => `<option value="${r.id}" ${r.id === cur.id ? 'selected' : ''}>${esc(r.tag)} (${r.revs.length} Rev)</option>`).join('')}</select>
      <span class="soft">이전</span><select id="rvp">${opt(pv)}</select><span class="soft">→ 새</span><select id="rvn">${opt(nw)}</select><span class="ir ir-rev"><i>?</i>바뀐 줄 <b>${d.rows.length}</b></span></div>
    <div class="card" style="padding:0;overflow:auto"><table class="t itbl"><thead><tr><th>No</th><th>항목</th><th>Rev ${esc(pv.rev || '-')}</th><th>Rev ${esc(nw.rev || '-')}</th><th>변경</th></tr></thead><tbody>
      ${d.rows.map(x => `<tr><td class="soft">${esc(x.no)}</td><td>${esc(x.label)}</td><td>${esc(x.prev || '—')}</td><td><b>${esc(x.new || '—')}</b></td><td>${pill(x.change)}</td></tr>`).join('') || '<tr><td colspan="5" class="empty">두 Rev 의 값이 같습니다</td></tr>'}</tbody></table></div>`;
  $('#rvt').onchange = e => { I.rvTag = +e.target.value; I.rvNew = I.rvPrev = null; renderRev(); };
  $('#rvp').onchange = e => { I.rvPrev = +e.target.value; renderRev(); };
  $('#rvn').onchange = e => { I.rvNew = +e.target.value; renderRev(); };
}

/* ── item page › Settings ─────────────────────────────────────────────────────────────── */
async function renderSettings() {
  const el = $('#v-isettings'); const ks = await kinds(), kk = ks.find(x => x.kind === I.kind), cur = await api('GET', `/projects/${S.pid}/inst/required`), codes = await api('GET', `/projects/${S.pid}/inst/codes`);
  const on = new Set(cur.confirmed[kk.form_id] || kk.required), ok = !!cur.confirmed[kk.form_id];
  const fields = kk.fields.filter((f, i, a) => a.findIndex(y => y.key === f.key) === i);
  el.innerHTML = `<div class="vh"><h2>Settings</h2><span class="soft">${esc(pageName())} · Form ${esc(kk.form_id)}</span></div>
    <div class="card"><h3>필수 칸 <small class="soft">— 비어 있으면 '누락' 으로 지적하는 칸 · ${ok ? '<b style="color:var(--ok)">이 프로젝트에서 확정됨</b>' : '<b>양식 카드의 제안값 (확정 전)</b>'}</small><span class="sp"></span><button class="pri" id="rqsave">저장</button></h3>
      <div class="rqlist wide">${fields.map(f => `<label><input type="checkbox" data-rk="${esc(f.key)}" ${on.has(f.key) ? 'checked' : ''}> ${f.no}. ${esc(f.label)}</label>`).join('')}</div></div>
    <div class="card"><h3>Review Code <small class="soft">— 프로젝트마다 다름 · 이 프로젝트의 Vendor 문서 절차에 맞게 고치세요 (CRS · 제안 코드에 쓰임)</small><span class="sp"></span><button id="cdsave">저장</button></h3>
      <textarea id="cdtext" rows="6" style="width:100%;font-family:monospace">${esc(codes.codes.map(c => `${c.code} = ${c.label}`).join('\n'))}</textarea>
      <div class="soft">한 줄에 하나: <code>코드 = 뜻</code> · 기본값은 공개된 예시 (1 Rejected · 2 Revise and Resubmit · 3 Approved with Comments · 4 Approved · 5 Information Only). 제안 코드는 남은 지적이 '값 다름' 이면 2, '누락 · 확인 필요' 만이면 3, 없으면 4 — 코드 뜻을 바꾸면 제안도 그 번호를 따릅니다.</div></div>
    <div class="card"><h3>검토 기준 <small class="soft">IN-1.0</small></h3><table class="t"><tbody>
      <tr><td>Process Data</td><td>Tag 로 PDS 행을 찾아 유체 · 상 · 압력 · 온도 · 밀도 · 유량 비교 (Max/Nor/Min 중 하나와 1 % 안이면 같음), 없으면 '없음'</td></tr>
      <tr><td>미결 항목</td><td>값에 HOLD · TBA · TBC · TBD 가 남아 있으면 '확인 필요' (IN-OPN-01)</td></tr>
      <tr><td>압력 기준</td><td>운전압 · 설계압의 게이지/절대 기준이 다르면 '확인 필요' (IN-UNIT-01)</td></tr>
      <tr><td>PMS</td><td>Pipe Class → PMS Class · Flange Rating</td></tr>
      <tr><td>Line List</td><td>Line No → Pipe Class · Design P/T · Size. Line 의 Design 이 Datasheet 보다 높으면 지적 (Line No 칸이 없는 양식은 PDS 의 Line No)</td></tr>
      <tr><td>Item 규칙</td><td>같은 Datasheet 안의 값끼리만 — 사람 확인 표시</td></tr></tbody></table></div>`;
  $('#cdsave').onclick = async () => { const cs = $('#cdtext').value.split('\n').map(l => l.split('=')).filter(x => x.length >= 2).map(([c, ...l]) => ({ code: c.trim(), label: l.join('=').trim() }));
    try { await api('PUT', `/projects/${S.pid}/inst/codes`, { codes: cs }); toast(`Review Code ${cs.length}개 저장`); renderSettings(); } catch (e) { toast(e.message, 1); } };
  $('#rqsave').onclick = async () => { const keys = $$('#v-isettings [data-rk]').filter(x => x.checked).map(x => x.dataset.rk);
    await api('PUT', `/projects/${S.pid}/inst/required`, { form_id: kk.form_id, keys }); I.rows = null; toast(`필수 칸 ${keys.length}개 저장 — 누락 판정에 바로 반영`); renderSettings(); };
}

/* ── Document · Revision — the same register the dashboard shows (GET /api/valve/docreg) ───────────────── */
async function renderReg() {
  const el = $('#v-ireg');
  el.innerHTML = '<div class="vh"><h2>Document · Revision</h2></div><div class="soft">불러오는 중…</div>';
  const d = await api('GET', `/docreg?project=${encodeURIComponent(S.sum?.project?.name || '')}`);
  // same filters as the dashboard's 문서 · Revision 현황: group chips (one) + Item chips (several, OR) + 검토 대기
  const ORDER = ['ball', 'globe', 'butterfly', 'psv', 'ft', 'pt', 'lt', 'gwr', 'tt', 'tg', 'pg', 'dpg', 'mlg', 'ro', 'analyzer', 'cv', 'onoff', 'valvelist', 'instindex', 'iolist', 'pms', 'pds', 'linelist'];
  const CHIP = { ball: 'Ball', globe: 'Globe', butterfly: 'Butterfly', psv: 'PSV', analyzer: 'AT', onoff: 'On-Off', valvelist: 'Valve List', instindex: 'Instrument Index', iolist: 'IO List', pms: 'PMS', pds: 'PDS', linelist: 'Line List' };
  if (!I.rgi) I.rgi = new Set(MODE === 'item' ? [I.kind] : []);                 // an item page starts on its own item
  const q = (I.rgq || '').toUpperCase(), fg = I.rgg || '', fp = I.rgp, fi = I.rgi;
  const inG = r => !fg || r.group === fg;
  const rows = d.rows.filter(r => inG(r) && (!fi.size || fi.has(r.kind)) && (!fp || r.pending) && (!q || [r.tag, r.doc_no, r.kind_name, r.latest.file].join(' ').toUpperCase().includes(q)));
  const n = { ds: rows.filter(r => r.group === 'Datasheet').length, pend: rows.filter(r => r.pending).length };
  const gchips = ['Datasheet', 'List', 'PMS', 'Process Data', 'Line List'].map(g => `<button data-rgg="${g}" class="${fg === g ? 'on' : ''}">${g}<b>${d.rows.filter(r => r.group === g).length}</b></button>`).join('');
  const ichips = ORDER.map(k => { const rs = d.rows.filter(r => r.kind === k && inG(r)); if (!rs.length) return ''; const pd = rs.filter(r => r.pending).length;
    return `<button data-rgi="${k}" class="${fi.has(k) ? 'on' : ''}">${esc(CHIP[k] || k.toUpperCase())}<b>${rs.length}</b>${pd ? `<em title="검토 대기 ${pd}">${pd}</em>` : ''}</button>`; }).join('');
  const link = r => { const L = r.link, u = new URL(location.href); u.searchParams.set('project', L.project); u.hash = '';
    ['kind', 'sheet', 'ds'].forEach(k => u.searchParams.delete(k));
    if (L.sheet) { u.searchParams.set('kind', L.kind); u.searchParams.set('sheet', L.sheet); } else if (L.ds) { if (L.kind !== 'ball') u.searchParams.set('kind', L.kind); u.searchParams.set('ds', L.ds); u.hash = 'review'; }
    else if (L.view) { if (L.kind !== 'ball') u.searchParams.set('kind', L.kind); u.hash = L.view; } else u.searchParams.set('kind', L.kind);
    return u.toString(); };
  el.innerHTML = `<div class="vh"><h2>Document · Revision</h2><span class="soft">${esc(d.project)} · 입력된 최신 Rev 와 검토된 최신 Rev (검토 완료 = ${d.done_status.join(' · ')})</span><span class="sp"></span>
      <input class="tq" placeholder="Tag · Doc No · 파일 찾기" value="${esc(I.rgq || '')}"></div>
    <div class="rchips"><button data-rgg="" class="${fg ? '' : 'on'}">전체<b>${d.rows.length}</b></button>${gchips}<button data-rgp class="pend ${fp ? 'on' : ''}">⏳ 검토 대기<b>${d.rows.filter(r => r.pending).length}</b></button>
      <span class="soft">표시 ${rows.length} · Datasheet ${n.ds} · 검토 대기 ${n.pend}</span></div>
    <div class="rchips item"><button data-rgi="" class="${fi.size ? '' : 'on'}">Item 전체</button>${ichips}</div>
    <div class="card" style="padding:0;overflow:auto"><table class="t itbl"><thead><tr><th>구분</th><th>종류</th><th>Doc. No.</th><th>Tag</th><th>입력된 최신 Rev</th><th>Rev 날짜</th><th>파일</th><th>올린 날 · 사람</th>
      <th>검토된 최신 Rev</th><th>상태</th><th>검토한 날 · 사람</th><th>Rev 이력</th></tr></thead><tbody>
      ${rows.map(r => { const L = r.latest, R = r.reviewed; return `<tr class="link ${r.pending ? 'r-rev' : ''}" data-href="${esc(link(r))}"><td>${esc(r.group)}</td><td>${esc(r.kind_name)}</td><td>${esc(r.doc_no || '—')}</td><td><b>${esc(r.tag || '')}</b></td>
        <td><b>${esc(L.rev || '—')}</b></td><td>${esc(L.date || '')}</td><td title="${esc(L.file)}">${esc(L.file || '')}</td><td>${esc((L.uploaded_at || '').replace('T', ' ').slice(0, 16))} · ${esc(L.uploaded_by || '')}</td>
        <td>${r.group !== 'Datasheet' ? '<span class="soft">—</span>' : R ? `<b>${esc(R.rev || '-')}</b>` : '<span class="ir ir-rev"><i>?</i>검토 대기</span>'}${R && r.pending ? ' <span class="ir ir-rev"><i>?</i>새 Rev 검토 대기</span>' : ''}</td>
        <td>${r.group === 'Datasheet' ? pill(R ? R.status : L.status || 'Not Reviewed') : ''}</td><td>${R ? `${esc((R.reviewed_at || '').replace('T', ' ').slice(0, 16))} · ${esc(R.reviewed_by || '')}` : ''}</td><td>${esc((r.revs || []).join(' → '))}</td></tr>`; }).join('') || '<tr><td colspan="12" class="empty">문서가 없습니다</td></tr>'}</tbody></table></div>`;

  $('.tq', el).onchange = e => { I.rgq = e.target.value; renderReg(); };
  el.onclick = e => {
    if (e.target.closest('[data-rgp]')) { I.rgp = !I.rgp; renderReg(); return; }
    const g = e.target.closest('[data-rgg]'); if (g) { I.rgg = g.dataset.rgg; I.rgi = new Set(); renderReg(); return; }        // a new group clears the Item choice
    const c = e.target.closest('[data-rgi]'); if (c) { const k = c.dataset.rgi; if (!k) I.rgi = new Set(); else if (I.rgi.has(k)) I.rgi.delete(k); else I.rgi.add(k); renderReg(); return; }
    const r = e.target.closest('[data-href]'); if (r && !e.target.closest('select, input')) location.href = r.dataset.href;
  };
}

buildMenu();
const RUN = { ireg: renderReg, inst: renderBoard, ireview: renderReview, ilist: renderLists, idash: renderItemDash, iexport: renderExport, itags: renderTags, irev: renderRev,
  iproc: () => renderCheck('iproc'), ipms: () => renderCheck('ipms'), iline: () => renderCheck('iline'), ilists: renderItemLists, isettings: renderSettings };
window.INST = { render(v) { paintBrand(); (RUN[v] || renderBoard)().catch(e => { console.error(e); toast(e.message, 1); }); } };
})();
