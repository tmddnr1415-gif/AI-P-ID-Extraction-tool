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
const STC = { Changed: 'st-c', 'No Change': 'st-0', New: 'st-n', Delete: 'st-d' };
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
function goCmp(doc, o, n) { P.cdoc = doc; P.old = o || null; P.nw = n || null; P.st = ''; P.lv = ''; P.only = null; P.open = new Set(); V.go('pcmp'); }
const counts = c => c ? `<span class="pcnt">${['High', 'Med', 'Min'].map(l => c[`changed_${l.toLowerCase()}`] ? `${lv(l)} ${c[`changed_${l.toLowerCase()}`]}` : '').filter(Boolean).join(' ')}
  · ${stp('Changed')} ${c.Changed || 0} · ${stp('No Change')} ${c['No Change'] || 0} · ${stp('New')} ${c.New || 0} · ${stp('Delete')} ${c.Delete || 0}</span>` : '';

/* ── PDS 현황 ─────────────────────────────────────────────────────────── */
async function renderDash() {
  const el = $('#v-pdash');
  el.innerHTML = '<div class="vh"><h2>PDS 현황</h2></div><div class="soft">불러오는 중…</div>';
  const s = await api('GET', `/projects/${S.pid}/pds/summary`);
  P.sum = s;
  const T = s.totals;
  const kpi = (l, n, sub) => `<div class="pk"><div class="pkl">${l}</div><div class="pkn">${n}</div>${sub ? `<div class="soft">${sub}</div>` : ''}</div>`;
  el.innerHTML = `<div class="vh"><h2>PDS 현황</h2><span class="soft">문서 번호마다 가장 새로 올린 Rev. 을 모든 Valve · Instrument 검토가 씁니다 · 같은 번호의 수정 PDS 를 올리면 앞 Rev. 과 비교합니다</span>
      <span class="sp"></span>${T.revised ? xlBtns('') : ''}</div>
    <div class="pkpis">${kpi('PDS 문서', T.documents, '문서 번호 기준')}${kpi('올린 파일', T.uploads, 'Rev. 포함')}${kpi('Tag (최신 Rev.)', T.tags, '검토에 쓰는 Tag')}${kpi('수정본 있는 문서', T.revised, 'Rev. 비교 가능')}</div>
    ${s.documents.length ? s.documents.map(d => { const L = d.revs[0];
      return `<div class="card pdoc"><h3>${esc(d.doc_no)} ${d.area ? `<span class="parea">${esc(d.area)}</span>` : ''} <span class="soft" style="font-weight:400">최신 Rev.${esc(L.rev || '?')} · Tag ${L.tags}</span>
        <span class="sp"></span>${d.compare ? `<button data-cmp="${esc(d.doc_no)}">⇆ Rev. 비교 보기</button>${xlBtns(d.doc_no)}` : '<span class="soft">Rev. 하나 — 수정 PDS 를 올리면 비교</span>'}</h3>
        ${d.compare ? `<div class="pline">Rev.${esc(d.revs[1].rev || '?')} → Rev.${esc(L.rev || '?')} : ${counts(d.compare.counts)}</div>` : ''}
        <table class="t"><thead><tr><th>Rev.</th><th>파일</th><th>올린 날 · 사람</th><th>Tag</th><th>On-Off</th><th>MOV</th><th>Control Valve · PSV</th><th>표</th><th></th></tr></thead><tbody>
        ${d.revs.map((r, i) => `<tr><td><b>Rev.${esc(r.rev || '?')}</b></td><td>${esc(r.filename)}</td><td class="mono">${esc(day(r.uploaded_at))} · ${esc(r.uploaded_by)}</td><td>${r.tags}</td>
          <td>${r.sections['On-Off'] || ''}</td><td>${r.sections.MOV || ''}</td><td>${r.sections['Control Valve · PSV'] || ''}</td><td>${r.tables}</td>
          <td>${i === 0 ? '<span class="puse">검토에 사용</span>' : `<button data-cmp="${esc(d.doc_no)}" data-o="${r.id}" data-n="${L.id}" title="이 Rev. 과 최신 Rev. 비교">⇆ 최신과 비교</button>`}</td></tr>`).join('')}
        </tbody></table></div>`; }).join('')
      : `<div class="card"><div class="empty">아직 올린 PDS 가 없습니다 — 왼쪽 <b>PDS 올리기</b> 에서 PDF 를 넣으세요 (공통 자료와 같은 곳에 보관됩니다).</div></div>`}`;
  $$('[data-cmp]', el).forEach(b => b.onclick = () => goCmp(b.dataset.cmp, +b.dataset.o || null, +b.dataset.n || null));
  bindXl(el);
}

/* ── PDS Tag 목록 ─────────────────────────────────────────────────────── */
const TCOLS = ['location', 'pid_no', 'line_no', 'line_size', 'valve_size', 'bore', 'piping_class', 'fluid', 'fluid_state', 'op_pressure', 'design_pressure',
  'op_temp', 'design_temp', 'dp_open', 'dp_close', 'fail_position', 'tightness'];
async function renderTags() {
  const el = $('#v-ptags');
  if (!P.tags) { el.innerHTML = '<div class="vh"><h2>PDS Tag 목록</h2></div><div class="soft">불러오는 중…</div>'; P.tags = await api('GET', `/projects/${S.pid}/pds/tags`); }
  const D = P.tags, lab = Object.fromEntries(D.fields.map(f => [f.key, f.label]));
  const docs = [...new Set(D.rows.map(r => r.doc_no))], secs = [...new Set(D.rows.map(r => r.section))];
  const q = P.q.toUpperCase();
  const rows = D.rows.filter(r => (!P.doc || r.doc_no === P.doc) && (!P.sec || r.section === P.sec)
    && (!q || [r.tag, r.location, r.line_no, r.pid_no, r.fluid].join(' ').toUpperCase().includes(q)));
  const shown = rows.slice(0, 1500);
  el.innerHTML = `<div class="vh"><h2>PDS Tag 목록</h2><span class="soft">각 문서 번호의 최신 Rev. 이 적은 값 그대로 (검토에 쓰는 값)</span></div>
    <div class="ptools"><input class="tq" placeholder="Tag · Location · Line · P&ID 찾기" value="${esc(P.q)}">
      <select data-f="doc"><option value="">문서 전체 (${docs.length})</option>${docs.map(d => `<option ${P.doc === d ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select>
      <select data-f="sec"><option value="">구분 전체</option>${secs.map(d => `<option ${P.sec === d ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select>
      <span class="soft">표시 ${rows.length}${rows.length > shown.length ? ` (앞 ${shown.length}개만 그림 — 찾기로 좁히세요)` : ''} / ${D.rows.length}</span></div>
    <div class="xlwrap"><table class="xl xtags"><thead><tr class="xlet"><th class="xg xcorner"></th>${[...Array(4 + TCOLS.length)].map((_, j) => `<th>${j < 26 ? String.fromCharCode(65 + j) : 'A' + String.fromCharCode(39 + j)}</th>`).join('')}</tr>
      <tr class="xhd"><th class="xg"></th><th>Doc No.</th><th>Rev.</th><th>구분</th><th>Tag</th>${TCOLS.map(k => `<th>${esc(lab[k])}</th>`).join('')}</tr></thead><tbody>
      ${shown.map((r, n) => `<tr><th class="xg">${n + 1}</th><td>${esc(r.doc_no)}</td><td>Rev.${esc(r.rev || '?')}</td><td>${esc(r.section)}</td><td class="xtag">${esc(r.tag)}</td>${TCOLS.map(k => `<td>${esc(r[k] ?? '')}</td>`).join('')}</tr>`).join('')}
    </tbody></table></div>`;
  $('.tq', el).onchange = e => { P.q = e.target.value; renderTags(); };
  $$('select[data-f]', el).forEach(s => s.onchange = () => { P[s.dataset.f] = s.value; renderTags(); });
}

/* ── Rev. 비교 ────────────────────────────────────────────────────────── */
async function renderCmp() {
  const el = $('#v-pcmp');
  if (!P.sum) P.sum = await api('GET', `/projects/${S.pid}/pds/summary`);
  const many = P.sum.documents.filter(d => d.revs.length >= 2);
  if (!many.length) { el.innerHTML = `<div class="vh"><h2>Rev. 비교</h2></div><div class="card"><div class="empty">같은 문서 번호로 두 Rev. 이상 올린 PDS 가 없습니다 — 수정 PDS 를 <b>PDS 올리기</b> 에서 넣으면 여기서 비교합니다.</div></div>`; return; }
  if (!many.some(d => d.doc_no === P.cdoc)) P.cdoc = many[0].doc_no;
  const D = many.find(d => d.doc_no === P.cdoc);
  const nw = D.revs.find(r => r.id === P.nw) || D.revs[0];
  const old = D.revs.find(r => r.id === P.old && r.id < nw.id) || D.revs.find(r => r.id < nw.id) || D.revs[1];
  const key = `${P.cdoc}|${old.id}|${nw.id}`;
  if (P.ckey !== key) { el.innerHTML = '<div class="vh"><h2>Rev. 비교</h2></div><div class="soft">비교하는 중…</div>';
    P.c = await api('GET', `/projects/${S.pid}/pds/compare?doc_no=${encodeURIComponent(P.cdoc)}&old=${old.id}&new=${nw.id}`); P.ckey = key; P.open = new Set(); }
  const C = P.c, lab = Object.fromEntries(C.fields.map(f => [f.key, f.label])), keys = C.fields.map(f => f.key);
  const q = P.cq.toUpperCase();
  const items = C.items.filter(i => (!P.only || P.only.has(i.tag)) && (!P.st || i.status === P.st) && (!P.lv || i.overall === P.lv) && (!q || [i.tag, i.new?.location, i.old?.location].join(' ').toUpperCase().includes(q)));
  const cnt = s => C.items.filter(i => i.status === s).length, cl = l => C.items.filter(i => i.overall === l).length;
  const revOpt = (sel, cond) => D.revs.filter(cond).map(r => `<option value="${r.id}" ${r.id === sel.id ? 'selected' : ''}>Rev.${esc(r.rev || '?')} · ${esc(r.filename)}</option>`).join('');
  // valve47 (user 2026-11-27: '좀 더 엑셀스럽게 · 변경된 셀은 노랑색 음영 · 변경된 값은 붉은색') — the sheet of the Excel, on screen:
  // column letters · row numbers · gridlines · frozen header and Tag columns · three rows per tag (이전 · 최신 · 중요도)
  const cols = P.onlyChg ? keys.filter(k => items.some(i => i.imp[k])) : keys;
  const L0 = ['No', 'Status', 'Tag', 'Rev.', 'Row'], NC = L0.length + cols.length + 2;
  let rn = 0;
  const gut = () => `<th class="xg">${++rn}</th>`;
  const cell = (i, k, row) => {
    const v = row === 'o' ? i.old?.[k] : i.new?.[k], ch = !!i.imp[k];
    const cls = (ch ? 'xc' : '') + (row === 'n' && (ch || i.status === 'New') && v != null && v !== '' ? ' xr' : '');
    return `<td class="${(cls + (k === 'location' || k === 'remarks' || k === 'notes' ? ' xw' : '')).trim()}" title="${ch ? esc(`${lab[k]}: ${i.old?.[k] ?? ''} → ${i.new?.[k] ?? ''} (${i.imp[k]})`) : ''}">${esc(v ?? '')}</td>`;
  };
  const block = (i, no) => {
    const o = i.old, n = i.new, sp = 'rowspan="3"';
    const r1 = `<tr class="xt">${gut()}<td ${sp} class="xn">${no}</td><td ${sp} class="xs ${STC[i.status] || ''}">${esc(i.status)}</td><td ${sp} class="xtag">${esc(i.tag)}</td>
      <td>Rev.${esc(C.old.rev)}</td><td class="xrow">이전</td>${o ? cols.map(k => cell(i, k, 'o')).join('') : `<td class="xna" colspan="${cols.length}">(이전 Rev. 없음)</td>`}
      <td ${sp} class="xo">${['New', 'Delete'].includes(i.overall) ? esc(i.overall) : lv(i.overall)}</td><td ${sp} class="xnote">${esc(i.note || '')}</td></tr>`;
    const r2 = `<tr>${gut()}<td>Rev.${esc(C.new.rev)}</td><td class="xrow">최신</td>${n ? cols.map(k => cell(i, k, 'n')).join('') : `<td class="xna" colspan="${cols.length}">(Rev.${esc(C.new.rev)} 미확인)</td>`}</tr>`;
    const r3 = `<tr class="xi">${gut()}<td></td><td class="xrow">중요도</td>${cols.map(k => `<td class="${i.imp[k] ? 'xl-' + i.imp[k] : ''}">${esc(i.imp[k] || '')}</td>`).join('')}</tr>`;
    return r1 + r2 + r3;
  };
  const letters = Array.from({ length: NC }, (_, j) => { let x = j + 1, t = ''; while (x) { x--; t = String.fromCharCode(65 + x % 26) + t; x = Math.floor(x / 26); } return t; });
  el.innerHTML = `<div class="vh"><h2>Rev. 비교</h2><span class="soft">같은 Tag 번호끼리만 비교 · 이전에만 있으면 Delete · 최신에만 있으면 New (Tag 변경은 추정하지 않음)</span><span class="sp"></span>${xlBtns(C.doc_no, old.id, nw.id)}</div>
    <div class="ptools"><select data-c="doc">${many.map(d => `<option ${d.doc_no === P.cdoc ? 'selected' : ''}>${esc(d.doc_no)}</option>`).join('')}</select>
      <label>이전 <select data-c="old">${revOpt(old, r => r.id < nw.id)}</select></label>
      <label>최신 <select data-c="new">${revOpt(nw, r => r.id > D.revs[D.revs.length - 1].id)}</select></label>
      ${C.area ? `<span class="parea">${esc(C.area)}</span>` : ''}<span class="soft">Tag ${C.counts.old_tags} → ${C.counts.new_tags}</span>
      ${C.excluded_columns.length ? `<span class="soft" title="한쪽 Rev. 에만 있는 열 — 비교하지 않고 값만 표시">비교 제외 열: ${esc(C.excluded_columns.join(', '))}</span>` : ''}</div>
    <div class="rchips"><button data-st="" class="${P.st ? '' : 'on'}">전체<b>${C.items.length}</b></button>${['Changed', 'No Change', 'New', 'Delete'].map(s => `<button data-st="${s}" class="${P.st === s ? 'on' : ''}">${stp(s)}<b>${cnt(s)}</b></button>`).join('')}
      <span class="sp" style="width:14px"></span>${['High', 'Med', 'Min'].map(l => `<button data-lv="${l}" class="${P.lv === l ? 'on' : ''}" title="종합 중요도">${lv(l)}<b>${cl(l)}</b></button>`).join('')}
      <label class="xchk"><input type="checkbox" data-only ${P.onlyChg ? 'checked' : ''}> 바뀐 열만</label>
      <input class="tq" placeholder="Tag · Location 찾기" value="${esc(P.cq)}">
      ${P.only ? `<button data-clr title="변경 Summary 에서 고른 Tag ${P.only.size}개만 보는 중 — 누르면 모두">✕ 고른 Tag ${P.only.size}개만</button>` : ''}
      <span class="xleg"><i class="xc">　</i> 변경된 셀 <b class="xr">붉은 글씨</b> 변경된 값</span></div>
    <div class="xlwrap"><table class="xl">
      <thead><tr class="xlet"><th class="xg xcorner"></th>${letters.map(t => `<th>${t}</th>`).join('')}</tr>
        <tr class="xhd"><th class="xg"></th>${L0.map(h => `<th>${h}</th>`).join('')}${cols.map(k => `<th>${esc(lab[k])}</th>`).join('')}<th>중요도(종합)</th><th>비고 / 사유</th></tr></thead>
      <tbody>${items.map((i, n) => block(i, n + 1)).join('') || `<tr><th class="xg"></th><td colspan="${NC}" class="xna">해당 없음</td></tr>`}</tbody></table></div>
    <div class="soft" style="margin:6px 2px">노랑 음영 = 바뀐 칸 · 붉은 글씨 = 최신 Rev. 의 바뀐 값 (New 는 최신 값 전체). 셀에 마우스를 올리면 이전 → 최신 · 중요도.
      중요도 기준: High = Size · Bore · 설계 P/T · Max ΔP · Pipe Class Rating 문자 / Med = 운전 P/T · 유량 · 밀도 · 점도 · 상 · Fluid · 운전 시간 · Tightness · Fail · Actuator · 수량 · Class 코드 체계 /
      Min = 문서 정합성 · 2% 이하 변화는 한 단계 낮춤.</div>`;
  $('[data-only]', el).onchange = e => { P.onlyChg = e.target.checked; renderCmp(); };
  const clr = $('[data-clr]', el); if (clr) clr.onclick = () => { P.only = null; renderCmp(); };
  bindXl(el);
  $('select[data-c="doc"]', el).onchange = e => goCmp(e.target.value);
  $('select[data-c="old"]', el).onchange = e => { P.old = +e.target.value; P.nw = nw.id; renderCmp(); };
  $('select[data-c="new"]', el).onchange = e => { P.nw = +e.target.value; P.old = null; renderCmp(); };
  $$('[data-st]', el).forEach(b => b.onclick = () => { P.st = b.dataset.st; renderCmp(); });
  $$('[data-lv]', el).forEach(b => b.onclick = () => { P.lv = P.lv === b.dataset.lv ? '' : b.dataset.lv; renderCmp(); });
  $('.rchips .tq', el).onchange = e => { P.cq = e.target.value; renderCmp(); };
}

/* ── 변경 Summary (valve48, user 2026-11-27: '변경 summary 도 별도로') — the Excel's Summary · Sizing sheets on screen ─── */
async function renderSum() {
  const el = $('#v-psum');
  el.innerHTML = '<div class="vh"><h2>변경 Summary</h2></div><div class="soft">불러오는 중…</div>';
  const X = await api('GET', `/projects/${S.pid}/pds/change_summary`);
  const D = X.documents;
  if (!D.length) { el.innerHTML = `<div class="vh"><h2>변경 Summary</h2></div><div class="card"><div class="empty">같은 문서 번호로 두 Rev. 이상 올린 PDS 가 없습니다 — 수정 PDS 를 <b>PDS 올리기</b> 에서 넣으면 변경 Summary 가 나옵니다.</div></div>`; return; }
  const L = D.map((_, i) => String.fromCharCode(65 + i)), sum = f => D.reduce((a, d) => a + f(d), 0);
  const num = (d, n, st, lvl) => n ? `<a class="xnum" data-go="${esc(d.doc_no)}" data-o="${d.old.id}" data-n="${d.new.id}" data-st="${st || ''}" data-lv="${lvl || ''}" title="Rev. 비교에서 보기">${n}</a>` : '<span class="x0">0</span>';
  const C = [['old_tags', '이전 Tag 수'], ['new_tags', '최신 Tag 수'], ['High', 'Changed (High)', 'Changed', 'High'], ['Med', 'Changed (Med)', 'Changed', 'Med'],
    ['Min', 'Changed (Min)', 'Changed', 'Min'], ['No Change', 'No Change', 'No Change'], ['New', 'New', 'New'], ['Delete', 'Delete', 'Delete']];
  const grp = { Size: 'xg-size', 'Sizing 영향': 'xg-size', '추가/삭제': '' };
  const lst = (rows, cols, head) => rows.length ? `<div class="xlwrap" style="max-height:340px"><table class="xl"><thead><tr class="xhd"><th class="xg" style="top:0"></th>${head.map(h => `<th style="top:0">${h}</th>`).join('')}</tr></thead><tbody>
      ${rows.map((r, n) => `<tr><th class="xg">${n + 1}</th>${cols(r).map(([v, cls]) => `<td class="${cls || ''}">${esc(v ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>` : '<div class="soft">없음</div>';
  const high = D.flatMap((d, i) => d.high.map(r => ({ ...r, L: L[i], doc: d.doc_no }))), size = D.flatMap((d, i) => d.size.map(r => ({ ...r, L: L[i] })));
  el.innerHTML = `<div class="vh"><h2>변경 Summary</h2><span class="soft">문서 번호마다 최신 Rev. vs 바로 앞 Rev. · Tag 번호가 같은 것끼리만 비교 · 숫자를 누르면 Rev. 비교에서 그 Tag 들만</span><span class="sp"></span>${xlBtns('')}</div>
    <h3 class="xh3">1. Rev. 비교 Summary</h3>
    <div class="xlwrap" style="max-height:none"><table class="xl xsum"><thead><tr class="xhd" style="top:0"><th class="xg" style="top:0"></th>${['Doc', 'Doc No.', 'Area', '이전 Rev.', '최신 Rev.', ...C.map(c => c[1])].map(h => `<th style="top:0">${h}</th>`).join('')}</tr></thead><tbody>
      ${D.map((d, i) => `<tr><th class="xg">${i + 1}</th><td>${L[i]}</td><td class="xtag">${esc(d.doc_no)}</td><td>${esc(d.area || '')}</td><td>Rev.${esc(d.old.rev || '?')}</td><td>Rev.${esc(d.new.rev || '?')}</td>
        ${C.map(([k, , st, lvl]) => `<td class="xnc ${lvl ? 'xl-' + lvl : ''}">${st ? num(d, d.counts[k], st, lvl) : d.counts[k]}</td>`).join('')}</tr>`).join('')}
      <tr class="xtot"><th class="xg">${D.length + 1}</th><td colspan="5"><b>합계</b></td>${C.map(([k]) => `<td class="xnc"><b>${sum(d => d.counts[k])}</b></td>`).join('')}</tr></tbody></table></div>
    <h3 class="xh3">2. Summary (Sizing 영향)</h3>
    <div class="xlwrap" style="max-height:none"><table class="xl xsum xsz"><thead><tr class="xhd"><th class="xg" style="top:0"></th><th style="top:0">구분</th><th style="top:0">항목</th><th style="top:0">판단 기준</th>
        ${D.map((d, i) => `<th style="top:0">${L[i]}. ${esc(d.doc_no)}</th>`).join('')}<th style="top:0">합계</th></tr></thead><tbody>
      <tr><th class="xg">1</th><td>Tag 수</td><td>이전 Rev. Tag 수</td><td>이전 Rev. 문서 기준</td>${D.map(d => `<td class="xnc">${d.counts.old_tags}</td>`).join('')}<td class="xnc"><b>${sum(d => d.counts.old_tags)}</b></td></tr>
      <tr><th class="xg">2</th><td>Tag 수</td><td>최신 Rev. Tag 수</td><td>최신 Rev. 문서 기준</td>${D.map(d => `<td class="xnc">${d.counts.new_tags}</td>`).join('')}<td class="xnc"><b>${sum(d => d.counts.new_tags)}</b></td></tr>
      ${X.sizing_rows.map((r, j) => `<tr><th class="xg">${j + 3}</th><td class="${grp[r.group] || ''}">${esc(r.group)}</td><td>${esc(r.item)}</td><td class="soft">${esc(r.basis)}</td>
        ${D.map(d => { const t = d.sizing[r.key] || []; return `<td class="xnc" title="${esc(t.join(', '))}">${t.length ? `<a class="xnum" data-tags="${esc(t.join('|'))}" data-go="${esc(d.doc_no)}" data-o="${d.old.id}" data-n="${d.new.id}">${t.length}</a>` : '<span class="x0">0</span>'}</td>`; }).join('')}
        <td class="xnc"><b>${sum(d => (d.sizing[r.key] || []).length)}</b></td></tr>`).join('')}</tbody></table></div>
    <div class="xtwo"><div><h3 class="xh3">3. Line Size / Valve Size 변경 Tag 목록 <span class="soft">${size.length}</span></h3>
      ${lst(size, r => [[r.L], [r.tag, 'xtag'], [r.item], [r.old], [r.new, 'xc xr']], ['Doc', 'Tag', '항목', '이전 Rev.', '최신 Rev.'])}</div>
      <div><h3 class="xh3">4. High 변경 목록 <span class="soft">${high.length}</span></h3>
      ${lst(high, r => [[r.L], [r.tag, 'xtag'], [r.item], [r.old], [r.new, 'xc xr'], [r.status]], ['Doc', 'Tag', '항목', '이전 Rev. 값', '최신 Rev. 값', 'Status'])}</div></div>`;
  bindXl(el);
  $$('.xnum', el).forEach(a => a.onclick = () => {           // the tags a number stands for, in Rev. 비교
    Object.assign(P, { cdoc: a.dataset.go, old: +a.dataset.o, nw: +a.dataset.n, st: a.dataset.st || '', lv: a.dataset.lv || '', cq: '',
      only: a.dataset.tags ? new Set(a.dataset.tags.split('|')) : null, open: new Set() });
    V.go('pcmp'); });
}

buildMenu();
const RUN = { pdash: renderDash, psum: renderSum, ptags: renderTags, pcmp: renderCmp };
window.PDS = { render(v) { P.sum = null; P.tags = null; P.ckey = null;          // each menu visit reads afresh (a PDS just uploaded shows at once)
  (RUN[v] || renderDash)().catch(e => { console.error(e); toast(e.message, 1); }); } };
})();
