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
function goCmp(doc, o, n) { P.cdoc = doc; P.old = o || null; P.nw = n || null; P.st = ''; P.lv = ''; P.only = null; P.open = new Set(); V.go('pcmp'); }
const counts = c => c ? `<span class="pcnt">${['High', 'Med', 'Min'].map(l => c[`changed_${l.toLowerCase()}`] ? `${lv(l)} ${c[`changed_${l.toLowerCase()}`]}` : '').filter(Boolean).join(' ')}
  · ${stp('Changed')} ${c.Changed || 0} · ${stp('No Change')} ${c['No Change'] || 0} · ${stp('New')} ${c.New || 0} · ${stp('Delete')} ${c.Delete || 0}${c['Tag 변경'] ? ` · ${stp('Tag 변경')} ${c['Tag 변경']}` : ''}</span>` : '';

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

/* ── the grids (valve50: xgrid.js — every cell lives, only the rows on screen are drawn) ────────────────────────── */
const W = { location: 230, pid_no: 150, line_no: 190, notes: 200, remarks: 230, valve_type: 96, fluid: 110, fluid_state: 70 };
const fw = k => W[k] || 84;
const grids = {};
function grid(id, host, opt) { grids[id]?.destroy(); grids[id] = window.XGrid(host, opt); return grids[id]; }
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
  const D = await api('GET', `/projects/${S.pid}/pds/tags`);
  const docs = [...new Set(D.rows.map(r => r.doc_no))], secs = [...new Set(D.rows.map(r => r.section))];
  el.innerHTML = `<div class="vh"><h2>PDS Tag 목록</h2><span class="soft">각 문서 번호의 최신 Rev. 이 적은 값 그대로 (검토에 쓰는 값) · 셀을 누르고 화살표 · Shift · Ctrl+C 로 엑셀처럼</span></div>
    <div class="ptools"><input class="tq" placeholder="Tag · Location · Line · P&ID 찾기 (입력하는 대로)" value="${esc(P.q)}">
      <select data-f="doc"><option value="">문서 전체 (${docs.length})</option>${docs.map(d => `<option ${P.doc === d ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select>
      <select data-f="sec"><option value="">구분 전체</option>${secs.map(d => `<option ${P.sec === d ? 'selected' : ''}>${esc(d)}</option>`).join('')}</select>
      <span class="soft" data-cnt></span></div><div data-grid></div>`;
  const cols = [{ label: 'Doc No.', w: 140 }, { label: 'Rev.', w: 52 }, { label: '구분', w: 72 }, { label: 'Tag', w: 120 }, ...D.fields.map(f => ({ label: f.label, w: fw(f.key) }))];
  const rowsOf = () => {
    const q = P.q.toUpperCase();
    const rs = D.rows.filter(r => (!P.doc || r.doc_no === P.doc) && (!P.sec || r.section === P.sec)
      && (!q || [r.tag, r.location, r.line_no, r.pid_no, r.fluid].join(' ').toUpperCase().includes(q)));
    $('[data-cnt]', el).textContent = `표시 ${rs.length} / ${D.rows.length}`;
    return rs.map(r => ({ cells: [{ v: r.doc_no }, { v: `Rev.${r.rev || '?'}` }, { v: r.section }, { v: r.tag, c: 'xb' }, ...D.fields.map(f => ({ v: r[f.key] ?? '' }))] }));
  };
  const g = grid('tags', $('[data-grid]', el), { cols, rows: rowsOf(), freeze: 4 });
  let tm = 0;
  $('.tq', el).oninput = e => { clearTimeout(tm); tm = setTimeout(() => { P.q = e.target.value; g.setRows(rowsOf()); }, 120); };
  $$('select[data-f]', el).forEach(s => s.onchange = () => { P[s.dataset.f] = s.value; g.setRows(rowsOf()); });
}

/* ── Rev. 비교 ────────────────────────────────────────────────────────── */
async function renderCmp() {
  const el = $('#v-pcmp');
  el.innerHTML = '<div class="vh"><h2>Rev. 비교</h2></div><div class="soft">불러오는 중…</div>';
  const sum = await api('GET', `/projects/${S.pid}/pds/summary`);
  const many = sum.documents.filter(d => d.revs.length >= 2);
  if (!many.length) { el.innerHTML = `<div class="vh"><h2>Rev. 비교</h2></div><div class="card"><div class="empty">같은 문서 번호로 두 Rev. 이상 올린 PDS 가 없습니다 — 수정 PDS 를 <b>PDS 올리기</b> 에서 넣으면 여기서 비교합니다.</div></div>`; return; }
  if (!many.some(d => d.doc_no === P.cdoc)) P.cdoc = many[0].doc_no;
  const D = many.find(d => d.doc_no === P.cdoc);
  const nw = D.revs.find(r => r.id === P.nw) || D.revs[0];
  const old = D.revs.find(r => r.id === P.old && r.id < nw.id) || D.revs.find(r => r.id < nw.id) || D.revs[1];
  const C = await api('GET', `/projects/${S.pid}/pds/compare?doc_no=${encodeURIComponent(P.cdoc)}&old=${old.id}&new=${nw.id}`);
  const lab = Object.fromEntries(C.fields.map(f => [f.key, f.label])), keys = C.fields.map(f => f.key);
  const cnt = s => C.items.filter(i => i.status === s).length, cl = l => C.items.filter(i => i.overall === l).length;
  const revOpt = (sel, cond) => D.revs.filter(cond).map(r => `<option value="${r.id}" ${r.id === sel.id ? 'selected' : ''}>Rev.${esc(r.rev || '?')} · ${esc(r.filename)}</option>`).join('');
  el.innerHTML = `<div class="vh"><h2>Rev. 비교</h2><span class="soft">같은 Tag 번호끼리만 비교 · New 줄에서 '이전 Tag 지정' → Tag 변경 · 셀을 누르고 화살표 · Shift · Ctrl+C 로 엑셀처럼</span><span class="sp"></span>${xlBtns(C.doc_no, old.id, nw.id)}</div>
    <div class="ptools"><select data-c="doc">${many.map(d => `<option ${d.doc_no === P.cdoc ? 'selected' : ''}>${esc(d.doc_no)}</option>`).join('')}</select>
      <label>이전 <select data-c="old">${revOpt(old, r => r.id < nw.id)}</select></label>
      <label>최신 <select data-c="new">${revOpt(nw, r => r.id > D.revs[D.revs.length - 1].id)}</select></label>
      ${C.area ? `<span class="parea">${esc(C.area)}</span>` : ''}<span class="soft">Tag ${C.counts.old_tags} → ${C.counts.new_tags}</span>
      ${C.excluded_columns.length ? `<span class="soft" title="한쪽 Rev. 에만 있는 열 — 비교하지 않고 값만 표시">비교 제외 열: ${esc(C.excluded_columns.join(', '))}</span>` : ''}</div>
    <div class="rchips"><button data-st="">전체<b>${C.items.length}</b></button>${['Changed', 'Tag 변경', 'No Change', 'New', 'Delete'].map(s => `<button data-st="${s}">${stp(s)}<b>${cnt(s)}</b></button>`).join('')}
      <span class="sp" style="width:14px"></span>${['High', 'Med', 'Min'].map(l => `<button data-lv="${l}" title="종합 중요도">${lv(l)}<b>${cl(l)}</b></button>`).join('')}
      <label class="xchk"><input type="checkbox" data-only ${P.onlyChg ? 'checked' : ''}> 바뀐 열만</label>
      <input class="tq" placeholder="Tag · Location 찾기 (입력하는 대로)" value="${esc(P.cq)}"><span data-clr></span>
      <span class="xleg"><i class="xc">　</i> 변경된 셀 <b class="xr">붉은 글씨</b> 변경된 값 <b class="xbl">파랑 숫자</b> 변경된 Size</span><span class="soft" data-cnt></span></div>
    <div data-grid></div>
    <div class="soft" style="margin:6px 2px">중요도 기준: High = Size · Bore · 설계 P/T · Max ΔP · Pipe Class Rating 문자 / Med = 운전 P/T · 유량 · 밀도 · 점도 · 상 · Fluid · 운전 시간 · Tightness · Fail · Actuator · 수량 · Class 코드 체계 /
      Min = 문서 정합성 · 2% 이하 변화는 한 단계 낮춤.</div>`;
  const dels = C.items.filter(i => i.status === 'Delete');
  const prevH = i => i.status === 'Tag 변경'
    ? `<b>${esc(i.old_tag)}</b> <button class="xunl" data-unl="${esc(i.tag)}" title="Tag 변경 지정 해제 — 다시 New · Delete 로 (${esc(i.link?.by || '')} ${esc((i.link?.at || '').slice(0, 10))})">✕</button>`
    : i.status === 'New' && dels.length ? `<select class="xlink" data-new="${esc(i.tag)}" title="이 New Tag 가 이전 Rev. 의 어느 Tag 인지 지정 → Tag 변경으로 비교 · Summary 반영">
        <option value="">이전 Tag 지정…</option>${dels.map(d => `<option value="${esc(d.tag)}">${esc(d.tag)}${d.old?.location ? ' · ' + esc(String(d.old.location).slice(0, 28)) : ''}</option>`).join('')}</select>` : '';
  const view = () => {
    const q = P.cq.toUpperCase();
    const items = C.items.filter(i => (!P.only || P.only.has(i.tag)) && (!P.st || i.status === P.st) && (!P.lv || i.overall === P.lv)
      && (!q || [i.tag, i.old_tag, i.new?.location, i.old?.location].join(' ').toUpperCase().includes(q)));
    const fk = P.onlyChg ? keys.filter(k => items.some(i => i.imp[k])) : keys;
    const cols = [{ label: 'No', w: 40 }, { label: 'Status', w: 92 }, { label: 'Tag', w: 120 }, { label: '이전 Tag', w: 160 }, { label: 'Rev.', w: 54 }, { label: 'Row', w: 50 },
      ...fk.map(k => ({ label: lab[k], w: fw(k) })), { label: '중요도(종합)', w: 86 }, { label: '비고 / 사유', w: 300 }];
    const rows = [];
    items.forEach((i, n) => {
      const sc = STC[i.status] || '', o = i.old, nv = i.new;
      for (let j = 0; j < 3; j++) {
        const m = j ? ' xm' : '';
        const cells = [{ v: j ? '' : n + 1, c: 'xn' + m }, { v: j ? '' : i.status, c: `xs ${sc}${m}`, t: i.status }, { v: j ? '' : i.tag, c: 'xb' + m, t: i.tag },
          j ? { v: '', c: 'xm' } : { v: i.old_tag || '', h: prevH(i), c: 'xprev', t: i.status === 'Tag 변경' ? `이전 Tag ${i.old_tag} (지정: ${i.link?.by || ''} ${(i.link?.at || '').slice(0, 10)})` : i.status === 'New' ? 'New — 이전 Tag 를 지정하면 Tag 변경' : '' },
          { v: j === 0 ? `Rev.${C.old.rev}` : j === 1 ? `Rev.${C.new.rev}` : '' }, { v: ['이전', '최신', '중요도'][j], c: 'xrow' }];
        fk.forEach((k, x) => {
          const ch = !!i.imp[k], fxT = ch ? `${lab[k]}: ${o?.[k] ?? ''} → ${nv?.[k] ?? ''} (${i.imp[k]})` : null;
          if (j === 2) { cells.push({ v: i.imp[k] || '', c: lvC(i.imp[k]), t: fxT }); return; }
          const src = j ? nv : o;
          if (!src) { cells.push({ v: x ? '' : (j ? `(Rev.${C.new.rev} 미확인)` : '(이전 Rev. 없음)'), c: 'xna' }); return; }
          const raw = src[k] ?? '', szc = SIZEK.has(k) && ch && j === 1 && raw !== '';   // a changed size of the latest Rev.
          const v = szc ? sz(k, raw) : raw, red = !szc && j === 1 && (ch || i.status === 'New') && v !== '';
          // valve51 (user 2026-11-27: '변경 사항 노랑색 음영은 최신 값에만'): the earlier row keeps no shading
          cells.push({ v, c: (ch && j === 1 ? 'xc' : '') + (szc ? ' xsz' : red ? ' xr' : ''), t: fxT ?? raw });
        });
        cells.push({ v: j ? '' : (['New', 'Delete'].includes(i.overall) ? i.overall : i.overall || ''), c: (j ? 'xm ' : '') + (j ? '' : lvC(i.overall)) });
        cells.push({ v: j ? '' : i.note || '', c: 'xnote' + m, t: i.note || '' });
        rows.push({ cls: j ? '' : 'xt', cells });
      }
    });
    $('[data-cnt]', el).textContent = `Tag ${items.length}개 · ${rows.length}줄`;
    $('[data-clr]', el).innerHTML = P.only ? `<button data-clrb title="변경 Summary 에서 고른 Tag 만 보는 중 — 누르면 모두">✕ 고른 Tag ${P.only.size}개만</button>` : '';
    $$('[data-st]', el).forEach(b => b.classList.toggle('on', b.dataset.st === P.st));
    $$('[data-lv]', el).forEach(b => b.classList.toggle('on', b.dataset.lv === P.lv));
    return { cols, rows };
  };
  const setLink = async (nt, ot) => {
    try { await api('PUT', `/projects/${S.pid}/pds/links`, { doc_no: C.doc_no, new_tag: nt, old_tag: ot });
      toast(ot ? `${nt} ← 이전 ${ot} : Tag 변경으로 비교합니다 (Summary · Excel 반영)` : `${nt} Tag 변경 지정 해제`); renderCmp(); }
    catch (e) { toast(e.message, 1); } };
  const first = view();
  const g = grid('cmp', $('[data-grid]', el), { cols: first.cols, rows: first.rows, freeze: 3,
    onAction(t, e) { if (t.matches('select.xlink') && e.type === 'change' && t.value) setLink(t.dataset.new, t.value);
      else if (t.matches('[data-unl]') && e.type === 'click') setLink(t.dataset.unl, ''); } });
  const refresh = () => { const v = view(); g.setCols(v.cols, v.rows); };
  bindXl(el);
  $('select[data-c="doc"]', el).onchange = e => goCmp(e.target.value);
  $('select[data-c="old"]', el).onchange = e => { P.old = +e.target.value; P.nw = nw.id; renderCmp(); };
  $('select[data-c="new"]', el).onchange = e => { P.nw = +e.target.value; P.old = null; renderCmp(); };
  $$('[data-st]', el).forEach(b => b.onclick = () => { P.st = b.dataset.st; refresh(); });
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
  const D = X.documents;
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
    <h3 class="xh3">1. Rev. 비교 Summary</h3><div data-g1></div>
    <h3 class="xh3">2. Summary (Sizing 영향)</h3><div data-g2></div>
    <div class="xtwo"><div><h3 class="xh3">3. Line Size / Valve Size 변경 Tag 목록 <span class="soft">${size.length}</span></h3><div data-g3></div></div>
      <div><h3 class="xh3">4. High 변경 목록 <span class="soft">${high.length}</span></h3><div data-g4></div></div></div>
    <h3 class="xh3">5. Tag 변경 목록 (사용자 지정) <span class="soft">${ren.length} — Rev. 비교의 New 줄에서 '이전 Tag 지정' 으로 넣습니다</span></h3><div data-g5></div>`;
  const go = a => { Object.assign(P, { cdoc: a.dataset.go, old: +a.dataset.o, nw: +a.dataset.n, st: a.dataset.st || '', lv: a.dataset.lv || '', cq: '',
    only: a.dataset.tags ? new Set(a.dataset.tags.split('|')) : null }); V.go('pcmp'); };
  const onAction = t => { if (t.matches('a.xnum')) go(t); };
  grid('s1', $('[data-g1]', el), { cols: [{ label: 'Doc', w: 44 }, { label: 'Doc No.', w: 150 }, { label: 'Area', w: 60 }, { label: '이전 Rev.', w: 70 }, { label: '최신 Rev.', w: 70 },
    ...CC.map(c => ({ label: c[1], w: 96 }))], rows: t1, freeze: 2, maxH: 60 + t1.length * 21, onAction });
  grid('s2', $('[data-g2]', el), { cols: [{ label: '구분', w: 90 }, { label: '항목', w: 230 }, { label: '판단 기준', w: 360 }, ...D.map((d, i) => ({ label: `${L[i]}. ${d.doc_no}`, w: 150 })), { label: '합계', w: 70 }],
    rows: t2, freeze: 2, maxH: 60 + t2.length * 21, onAction });
  const small = (k, cols, rows) => rows.length ? grid(k, $(`[data-${k}]`, el), { cols, rows, maxH: 360 }) : ($(`[data-${k}]`, el).innerHTML = '<div class="soft">없음</div>');
  small('g3', [{ label: 'Doc', w: 44 }, { label: 'Tag', w: 120 }, { label: '이전 Tag', w: 110 }, { label: '항목', w: 90 }, { label: '이전 Rev.', w: 80 }, { label: '최신 Rev.', w: 80 }], size);
  small('g4', [{ label: 'Doc', w: 44 }, { label: 'Tag', w: 120 }, { label: '이전 Tag', w: 110 }, { label: '항목', w: 130 }, { label: '이전 Rev. 값', w: 100 }, { label: '최신 Rev. 값', w: 100 }, { label: 'Status', w: 80 }], high);
  small('g5', [{ label: 'Doc', w: 44 }, { label: 'Tag (최신)', w: 130 }, { label: '이전 Tag', w: 130 }, { label: '중요도(종합)', w: 90 }, { label: '비고', w: 480 }], ren);
  bindXl(el);
}

buildMenu();
const RUN = { pdash: renderDash, psum: renderSum, ptags: renderTags, pcmp: renderCmp };
window.PDS = { render(v) { P.sum = null; P.tags = null; P.ckey = null;          // each menu visit reads afresh (a PDS just uploaded shows at once)
  (RUN[v] || renderDash)().catch(e => { console.error(e); toast(e.message, 1); }); } };
})();
