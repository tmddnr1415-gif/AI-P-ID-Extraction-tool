/* Instrument datasheet review — screens (valve40).  Data: /api/valve/projects/{pid}/inst/* · /api/valve/inst/* (app/valve/inst_api.py).
 * Instrument 현황판 (all item kinds at a glance) · Instrument Review (tag list · PDF · findings · read values) · List 대조.
 * Uses the Valve page's helpers through window.VALVE (valve.js) — same project spaces, same Document Management. */
(() => {
'use strict';
const V = window.VALVE;
if (!V) return;
const { S, Q, LS, api, esc, pill, toast, $, $$ } = V;
const QK = (Q.get('kind') || '').toLowerCase();
const I = { kinds: null, kind: V.INST_KINDS.has(QK) ? QK : LS.get('inst.kind', 'ft') || 'ft', list: QK === 'iolist' ? 'io_list' : QK === 'instindex' ? 'instrument_index' : LS.get('inst.list', 'instrument_index'), ltab: 'cmp', rows: null, sel: null, d: null, tab: 'find', filt: '', lfilt: '' };
const RES = { 'Mismatch': ['bad', '값 다름'], 'Missing': ['miss', '누락'], 'Review Required': ['rev', '확인 필요'], '없음': ['na', '없음'], 'Datasheet Blank': ['na', 'DS 비어 있음'], 'OK': ['ok', 'OK'],
  '값 다름': ['bad', '값 다름'], '누락': ['miss', '누락'], 'List 에만': ['lo', 'List 에만'] };
const rp = r => `<span class="ir ir-${(RES[r] || ['na'])[0]}">${esc((RES[r] || [, r])[1])}</span>`;
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
      <button class="pri" data-g="ireview">Instrument Review 열기</button></div>
    <div class="irefs">${ref('Process Data (PDS)', R.pds, 'Document Management › Process Data')}${ref('PMS', R.pms, 'Document Management › PMS')}
      ${ref(`Process Line List${R.n_lines ? ` (${R.n_lines} Line)` : ''}`, R.linelist, 'Document Management › Process Line List')}${ref('Instrument Index', R.instrument_index, 'Document Management › Instrument Index · IO List')}${ref('IO List', R.io_list, 'Document Management › Instrument Index · IO List')}</div>
    ${!t.tags ? '<div class="banner info">아직 Instrument Datasheet 가 없습니다 — <b>Document Management › Instrument Datasheet PDF</b> 에 올리면 양식(FT · PT · LT · TT · PG · PSV …)을 알아보고 Tag 별로 검토합니다.</div>' : ''}
    ${t.test ? `<div class="banner warn">시험 자료(TEST DATA 도장) ${t.test}개 Tag 가 들어 있습니다 — 실제 Datasheet 가 아닙니다.</div>` : ''}
    <div class="kpis">${tile('Item 종류', used.length + ' / ' + s.kinds.length, '', '자료가 있는 계기 종류 / 양식 카드 수')}${tile('Tag', t.tags, '', '최신 Rev 기준 Tag 수')}${tile('Datasheet', t.sheets, '', '읽은 Datasheet (모든 Rev)')}
      ${tile('지적 없음', t.ok_tags, 'okk', '지적이 하나도 없는 Tag')}${tile('누락', t.missing, t.missing ? 'warn' : '', '필수 칸이 빈 곳 (IN-REQ-01)')}${tile('값 다름', t.mismatch, t.mismatch ? 'warn' : '', 'PDS · PMS · Line List · Item 규칙과 다름')}
      ${tile('확인 필요', t.review, '', '단위 · 기준이 불명확하거나 PMS/Line 에서 정확히 찾지 못함')}${tile('PDS 없음', t.not_in_pds, '', 'Process Data 에 Tag 가 없는 수')}</div>
    <div class="card"><h3>계기 Type 별 현황 <small class="soft">— 칸을 누르면 그 종류의 Review 가 열립니다</small></h3>
      <div class="itypes">${s.kinds.map(k => {
        const iss = k.missing + k.mismatch + k.review, pct = k.tags ? Math.round(100 * k.ok_tags / k.tags) : 0;
        const revs = Object.entries(k.revs).sort().map(([r, n]) => `Rev ${esc(r)} ${n}`).join(' · ');
        return `<div class="itype ${k.tags ? '' : 'none'}" data-k="${k.kind}" tabindex="0" title="${esc(k.name)} — 양식 ${k.form_id}">
          <div class="ih"><span class="ico">${ICON[k.kind] || '•'}</span><b>${esc(k.kind.toUpperCase())}</b><span class="soft">${esc(k.name)}</span></div>
          <div class="inum"><b>${k.tags}</b><span>Tag</span>${k.sheets !== k.tags ? `<small class="soft">DS ${k.sheets}</small>` : ''}</div>
          <div class="ibar" title="지적 없는 Tag ${k.ok_tags}/${k.tags}"><i style="width:${pct}%"></i></div>
          <div class="icnt">${k.tags ? `<span class="ir ir-miss">누락 ${k.missing}</span><span class="ir ir-bad">값 다름 ${k.mismatch}</span><span class="ir ir-rev">확인 ${k.review}</span>${k.not_in_pds ? `<span class="ir ir-na">PDS 없음 ${k.not_in_pds}</span>` : ''}` : '<span class="soft">자료 없음</span>'}</div>
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
    const k = e.target.closest('[data-k]'); if (k) { I.kind = k.dataset.k; LS.set('inst.kind', I.kind); I.rows = null; I.sel = null; V.go('ireview'); return; }
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
    <div class="wb iwb"><div class="wb-left"><input class="iq" placeholder="Tag 찾기" value="${esc(I.filt)}"><div class="itags" id="itags"></div></div>
      <div class="wb-center" id="iview"></div><div class="wb-right"><div class="tabs" id="itabs">${[['find', '검토 결과'], ['vals', '읽은 값'], ['rev', 'Rev · 문서']].map(([k, l]) => `<button data-t="${k}" class="${I.tab === k ? 'on' : ''}">${l}</button>`).join('')}</div><div class="rbody" id="ibody"></div></div></div>`;
  I.viewer = new V.Viewer($('#iview'), { onOverlay: o => { if (o.key) { I.selKey = o.key; drawRight(); } } });
  drawTags();
  $('.iq', el).oninput = e => { I.filt = e.target.value; drawTags(); };
  $('#itabs').onclick = e => { const b = e.target.closest('[data-t]'); if (!b) return; I.tab = b.dataset.t; $$('#itabs button').forEach(x => x.classList.toggle('on', x === b)); drawRight(); };
  const want = I.rows.find(r => r.id === I.sel) || I.rows[0];
  if (want) await openSheet(want.id); else { $('#ibody').innerHTML = '<div class="empty">이 종류의 Datasheet 가 없습니다.</div>'; $('#iview .stage').innerHTML = '<div class="empty" style="color:#fff">Document Management 에 Instrument Datasheet PDF 를 올리세요.</div>'; }
}
function drawTags() {
  const q = (I.filt || '').toUpperCase().replace(/[\s_-]/g, '');
  $('#itags').innerHTML = I.rows.filter(r => !q || r.tag.toUpperCase().replace(/[\s_-]/g, '').includes(q)).map(r => {
    const c = r.counts;
    return `<div class="itag ${r.id === I.sel ? 'on' : ''}" data-id="${r.id}"><div><b>${esc(r.tag)}</b>${r.test_data ? '<span class="tst">TEST</span>' : ''}<span class="sp"></span><small>Rev ${esc(r.rev || '-')}</small></div>
      <div class="soft">${esc(r.kind.toUpperCase())} · ${esc((r.service || '').slice(0, 30))}</div>
      <div>${r.issues ? `${c.Missing ? `<span class="ir ir-miss">${c.Missing}</span>` : ''}${c.Mismatch ? `<span class="ir ir-bad">${c.Mismatch}</span>` : ''}${c['Review Required'] ? `<span class="ir ir-rev">${c['Review Required']}</span>` : ''}` : '<span class="ir ir-ok">지적 없음</span>'}${r.in_pds ? '' : '<span class="ir ir-na">PDS 없음</span>'}</div></div>`;
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
function rowOf(key) { return (I.d?.rows || []).find(r => r.std_key === key && r.bbox) || null; }
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
function drawRight() {
  const d = I.d, b = $('#ibody'); if (!d || !b) return;
  const head = `<div class="ihead"><b>${esc(d.tag)}</b> ${pill(d.status)} <span class="soft">${esc(kname(d.kind))} · 양식 ${esc(d.form_id)}</span>
    <div class="soft">${esc(d.doc_no || '(문서번호 못 읽음)')} · Rev ${esc(d.rev || '-')}${d.rev_date ? ' · ' + esc(d.rev_date) : ''}${d.test_data ? ' · <b class="tst">TEST DATA</b>' : ''}</div>
    <div class="ist"><a class="btnlink" href="/api/valve/inst/sheets/${d.id}/markup.pdf" download title="이 Datasheet 에 지적을 표시한 PDF — 칸 음영 + 화살표 설명선(이유)">⇩ 이 Tag Mark-up PDF</a> <select id="ists">${['Not Reviewed', 'Under Review', 'Accepted', 'Rejected', 'Commented', 'Resolved'].map(s => `<option ${s === d.status ? 'selected' : ''}>${s}</option>`).join('')}</select></div></div>`;
  if (I.tab === 'find') {
    const sec = GROUPS.map(([p, l]) => {
      const rs = d.review.map((f, i) => [f, i]).filter(([f]) => f.rule.startsWith(p));
      if (!rs.length) return '';
      const bad = rs.filter(([f]) => ['Mismatch', 'Missing', 'Review Required'].includes(f.result)).length;
      return `<div class="igrp"><h4>${l} <span class="soft">${rs.length}</span>${bad ? `<span class="ir ir-bad">${bad}</span>` : '<span class="ir ir-ok">OK</span>'}</h4>${rs.map(([f, i]) => `
        <div class="ifind ${I.selKey === f.key ? 'sel' : ''} r-${(RES[f.result] || ['na'])[0]}" data-key="${esc(f.key)}"><div><span class="no">${i + 1}</span>${rp(f.result)} <b>${esc(f.item)}</b><span class="sp"></span><small class="soft" title="${esc(d.rules[f.rule] || '')}">${esc(f.rule)}</small></div>
          <div class="cmp"><span>Datasheet</span><b>${esc(f.ds || '—')}</b><span>기준</span><b>${esc(f.ref || '—')}</b></div>
          <div class="soft">${esc(f.reason)}${f.human ? ' · <b>사람 확인</b>' : ''}</div><div class="src">${esc(f.source || '')}</div></div>`).join('')}</div>`;
    }).join('');
    b.innerHTML = head + (sec || '<div class="empty">검토할 기준 문서가 없습니다</div>');
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
  $('#ists').onchange = async e => { await api('PUT', `/inst/sheets/${d.id}/status`, { status: e.target.value }); d.status = e.target.value; const r = I.rows.find(x => x.id === d.id); if (r) r.status = d.status; toast('상태 저장'); drawRight(); };
  b.onclick = e => {
    const o = e.target.closest('[data-open]'); if (o) { openSheet(+o.dataset.open); return; }
    const f = e.target.closest('[data-key]'); if (!f || !f.dataset.key) return;
    I.selKey = f.dataset.key; const r = rowOf(I.selKey) || (I.selKey.startsWith('line') ? rowOf('line_no') : null);
    paintOv(); $$('#ibody [data-key]').forEach(x => x.classList.toggle('sel', x.dataset.key === I.selKey));
    if (r) I.viewer.focus(r.page, r.bbox, r.label);
  };
}

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
        ${rows.map(x => `<tr ${x.sheet_id ? `data-sid="${x.sheet_id}" data-sk="${x.kind}" class="link"` : ''}><td>${rp(x.result)}</td><td><b>${esc(x.tag)}</b></td><td>${esc((x.kind || '').toUpperCase())}</td><td>${esc(x.field)}</td>
          <td>${esc(x.ds)}</td><td>${esc(x.lst)}</td><td class="soft">${esc(x.reason)}</td><td class="soft">${esc(x.rule)}</td></tr>`).join('') || '<tr><td colspan="8" class="empty">차이 없음</td></tr>'}</tbody></table></div>`;
    } else {
      const io = L === 'io_list';
      body = `<div class="card" style="padding:0;overflow:auto"><table class="t"><thead><tr><th>Tag</th><th>Loop</th><th>Type</th><th>Service</th><th>P&amp;ID</th><th>Line</th><th>Range</th>
        ${io ? '<th>IO</th><th>Logic</th>' : '<th>Datasheet No</th><th>Manufacturer</th><th>Model</th>'}<th>Datasheet</th><th>대조</th><th>p.</th></tr></thead><tbody>
        ${d.records.map(r => `<tr ${r.sheet_id ? `data-sid="${r.sheet_id}" data-sk="${r.ds_kind}" class="link"` : ''}><td><b>${esc(r.tag)}</b></td><td>${esc(r.loop || '')}</td><td>${esc(r.inst_type || '')}</td><td>${esc(r.service || '')}</td>
          <td>${esc(r.pid_no || '')}</td><td>${esc(r.line_no || '')}</td><td>${esc(r.range || '')}</td>
          ${io ? `<td>${esc(r.io_typical || '')}</td><td>${esc(r.logic_no || '')}</td>` : `<td>${esc(r.datasheet_no || '')}</td><td>${esc(r.manufacturer || '')}</td><td>${esc(r.model || '')}</td>`}
          <td>${r.ds_kind ? esc(r.ds_kind.toUpperCase()) : '<span class="ir ir-lo">없음</span>'}</td><td>${r.findings ? `<span class="ir ir-bad">${r.findings}</span>` : '<span class="ir ir-ok">OK</span>'}</td><td class="soft">${r.page || ''}</td></tr>`).join('')}</tbody></table></div>`;
    }
    el.innerHTML = head + `<div class="ilhead"><div class="tabs ltabs">${tabs}</div><div class="ilc">${kpi}</div></div>` + body;
  }
  el.onclick = e => {
    const g = e.target.closest('[data-g]'); if (g) { V.go(g.dataset.g); return; }
    const t = e.target.closest('[data-lt]'); if (t) { I.ltab = t.dataset.lt; renderLists(); return; }
    const b = e.target.closest('[data-lf]'); if (b) { I.lfilt = I.lfilt === b.dataset.lf ? '' : b.dataset.lf; I.ltab = 'cmp'; renderLists(); return; }
    const r = e.target.closest('[data-sid]'); if (r) { I.sel = +r.dataset.sid; I.kind = r.dataset.sk || I.kind; I.rows = null; V.go('ireview'); }
  };
}

/* left menu: one entry per item and per list (like the Valve kinds) */
function markMenu(v) {
  $$('#menu button[data-ik]').forEach(b => b.classList.toggle('on', v === 'ireview' && b.dataset.ik === I.kind));
  $$('#menu button[data-il]').forEach(b => b.classList.toggle('on', v === 'ilist' && b.dataset.il === I.list));
}
$('#menu').addEventListener('click', e => {                 // capture: set the item / list before the view renders
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.ik) { if (I.kind !== b.dataset.ik) { I.kind = b.dataset.ik; I.sel = null; I.rows = null; } LS.set('inst.kind', I.kind); }
  if (b.dataset.il) { I.list = b.dataset.il; LS.set('inst.list', I.list); I.lfilt = ''; }
}, true);

window.INST = { render(v) { markMenu(v); (v === 'inst' ? renderBoard() : v === 'ireview' ? renderReview() : renderLists()).catch(e => { console.error(e); toast(e.message, 1); }); } };
})();
