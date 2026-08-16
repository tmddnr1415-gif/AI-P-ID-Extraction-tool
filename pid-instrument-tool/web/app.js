/* P&ID Instrument List — 브라우저 단독 파이프라인.
 *
 * PDF 넣기 → 도면별 판독 → 템플릿 서식 그대로의 Excel 다운로드까지 브라우저에서 끝난다.
 * 파이썬 파이프라인과 같은 규칙·같은 프롬프트·같은 Excel 쓰기 방식을 쓴다.
 */
'use strict';

const $ = (id) => document.getElementById(id);

const state = {
  server: null,       // 공유 링크 서버 모드일 때 /api/config 응답
  settings: {
    apiKey: '', model: 'claude-opus-5', effort: 'high', maxTokens: 32000,
    tiles: '3x2', dpi: 200,
  },
  rules: {},          // 파일명 → 본문 (기본값은 RULES_DEFAULT)
  pdf: null,          // {name, bytes}
  template: null,     // {name, bytes}
  spec: null,         // 템플릿 해부 결과
  doc: null,          // pdf.js 문서
  pages: [],
  selected: new Set(),
  result: null,       // {rows, excluded, findings, pages, usage}
  controller: null,
  ruleTab: null,
};

/* ── pdf.js 워커 ───────────────────────────────────────────
 * 단일 파일 빌드에서는 워커 소스가 base64로 들어 있어 blob URL로 올린다.
 * (file:// 에서는 워커 파일을 fetch할 수 없기 때문)
 */
(function setupWorker() {
  if (typeof pdfjsLib === 'undefined') return;
  if (typeof window.PDF_WORKER_B64 === 'string' && window.PDF_WORKER_B64) {
    const bin = atob(window.PDF_WORKER_B64);
    const buf = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    pdfjsLib.GlobalWorkerOptions.workerSrc =
      URL.createObjectURL(new Blob([buf], { type: 'application/javascript' }));
  } else {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'vendor/pdf.worker.min.js';
  }
})();

/* ── 저장소 ────────────────────────────────────────────── */
const DB = { name: 'pid-tool', store: 'files' };

function idb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB.name, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(DB.store);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
/* 보관은 편의 기능이다. file:// 처럼 저장소가 막힌 환경에서도 앱 자체는 계속
   동작해야 하므로, 실패해도 예외를 위로 올리지 않는다. */
async function idbPut(key, value) {
  try {
    const db = await idb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(DB.store, 'readwrite');
      tx.objectStore(DB.store).put(value, key);
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  } catch (err) {
    console.info('브라우저 보관을 쓸 수 없습니다. 다음에 열 때 파일을 다시 넣어야 합니다.', err);
  }
}
async function idbGet(key) {
  try {
    const db = await idb();
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(DB.store, 'readonly');
      const r = tx.objectStore(DB.store).get(key);
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
  } catch {
    return null;
  }
}

function loadSettings() {
  try { Object.assign(state.settings, JSON.parse(localStorage.getItem('pid.web.settings') || '{}')); }
  catch { /* 기본값 사용 */ }
  try { state.rules = { ...RULES_DEFAULT, ...JSON.parse(localStorage.getItem('pid.web.rules') || '{}') }; }
  catch { state.rules = { ...RULES_DEFAULT }; }
}
const saveSettings = () => localStorage.setItem('pid.web.settings', JSON.stringify(state.settings));
const saveRules = () => localStorage.setItem('pid.web.rules', JSON.stringify(state.rules));

/* ── 설정 다이얼로그 ───────────────────────────────────── */
$('btn-settings').addEventListener('click', () => {
  $('api-key').value = state.settings.apiKey;
  $('model').value = state.settings.model;
  $('effort').value = state.settings.effort;
  $('max-tokens').value = state.settings.maxTokens;
  $('tiles').value = state.settings.tiles;
  $('dpi').value = state.settings.dpi;
  $('dlg-settings').showModal();
});
$('dlg-settings').addEventListener('close', () => {
  if ($('dlg-settings').returnValue !== 'save') return;
  Object.assign(state.settings, {
    apiKey: $('api-key').value.trim(),
    model: $('model').value,
    effort: $('effort').value,
    maxTokens: Math.max(4096, Math.min(128000, +$('max-tokens').value || 32000)),
    tiles: $('tiles').value,
    dpi: Math.max(100, Math.min(400, +$('dpi').value || 200)),
  });
  saveSettings();
  updateSubtitle();
});

/* ── 규칙 다이얼로그 ───────────────────────────────────── */
$('btn-rules').addEventListener('click', () => {
  state.ruleTab = state.ruleTab || Object.keys(state.rules)[0];
  renderRuleTabs();
  $('dlg-rules').showModal();
});
function renderRuleTabs() {
  const wrap = $('rule-tabs');
  wrap.innerHTML = '';
  for (const name of Object.keys(state.rules)) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'tab' + (name === state.ruleTab ? ' on' : '');
    b.textContent = name;
    b.addEventListener('click', () => {
      state.rules[state.ruleTab] = $('rule-text').value;
      state.ruleTab = name;
      renderRuleTabs();
    });
    wrap.append(b);
  }
  $('rule-text').value = state.rules[state.ruleTab] || '';
}
$('dlg-rules').addEventListener('close', () => {
  const v = $('dlg-rules').returnValue;
  if (v === 'save') {
    state.rules[state.ruleTab] = $('rule-text').value;
    saveRules();
  } else if (v === 'reset') {
    state.rules[state.ruleTab] = RULES_DEFAULT[state.ruleTab] || '';
    saveRules();
    renderRuleTabs();
    $('dlg-rules').showModal();
  }
});

/* ── 파일 넣기 ─────────────────────────────────────────── */
function wireDrop(zoneId, inputId, handler, accept) {
  const zone = $(zoneId); const input = $(inputId);
  const locked = () => zone.classList.contains('locked');   // 서버가 정해주는 파일
  zone.addEventListener('click', () => { if (!locked()) input.click(); });
  input.addEventListener('change', (e) => { if (e.target.files[0]) handler(e.target.files[0]); e.target.value = ''; });
  ['dragenter', 'dragover'].forEach((ev) =>
    zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) =>
    zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove('over'); }));
  zone.addEventListener('drop', (e) => {
    if (locked()) return;
    const f = e.dataTransfer.files[0];
    if (!f) return;
    if (accept && !accept.test(f.name)) { alert(`${accept} 형식의 파일이 필요합니다.`); return; }
    handler(f);
  });
}

wireDrop('dz-pdf', 'in-pdf', async (file) => {
  const bytes = new Uint8Array(await file.arrayBuffer());
  state.pdf = { name: file.name, bytes };
  await idbPut('pdf', { name: file.name, bytes });
  await scanPdf();
}, /\.pdf$/i);

wireDrop('dz-tpl', 'in-tpl', async (file) => {
  const bytes = new Uint8Array(await file.arrayBuffer());
  await useTemplate(file.name, bytes);
  await idbPut('template', { name: file.name, bytes });
}, /\.xlsx$/i);

async function useTemplate(name, bytes) {
  try {
    const spec = XLSX.analyzeTemplate(bytes);
    state.template = { name, bytes };
    state.spec = spec;
    $('tpl-state').textContent = `${name} · 컬럼 ${spec.columns.length}개`;
    $('tpl-state').classList.add('ok');
    const drawing = spec.columns.filter((c) => c.source === 'drawing').map((c) => c.label || c.key);
    const blanks = spec.columns.filter((c) => c.source === 'design_table').length;
    $('spec-info').classList.remove('hidden');
    $('spec-info').innerHTML =
      `템플릿 분석 완료 — 기존 <b>${spec.templateRowCount}</b>행에서 규칙을 배웠습니다. `
      + `모델이 도면에서 판독할 컬럼 <b>${drawing.length}</b>개(${drawing.join(', ')}), `
      + `TYPICAL TYPE으로 채울 컬럼 <b>${spec.columns.filter((c) => c.source === 'typical').length}</b>개, `
      + `Design Table 조인이 필요해 비워 둘 컬럼 <b>${blanks}</b>개.`;
  } catch (err) {
    $('tpl-state').textContent = `읽지 못했습니다: ${err.message}`;
    $('tpl-state').classList.remove('ok');
    state.template = null; state.spec = null;
  }
  updateRunnable();
}

async function scanPdf() {
  $('pdf-state').textContent = 'PDF 훑는 중…';
  $('pdf-state').classList.remove('ok');
  try {
    // pdf.js가 버퍼를 가져가므로 사본을 넘긴다.
    const scan = await PDFScan.scan(state.pdf.bytes.slice().buffer, (done, total) => {
      $('pdf-state').textContent = `PDF 훑는 중… ${done}/${total}쪽`;
    });
    state.doc = scan.doc;
    state.pages = scan.pages;
    state.selected = new Set(scan.pages.filter((p) => !p.is_legend && p.candidates.length).map((p) => p.page));
    $('pdf-state').textContent = `${state.pdf.name} · ${scan.pageCount}쪽`;
    $('pdf-state').classList.add('ok');
    renderPages();
  } catch (err) {
    $('pdf-state').textContent = `읽지 못했습니다: ${err.message}`;
  }
  updateRunnable();
}

/* ── 도면 목록 ─────────────────────────────────────────── */
function renderPages() {
  $('sec-pages').classList.remove('hidden');
  const tb = document.querySelector('#pages tbody');
  tb.innerHTML = '';
  for (const p of state.pages) {
    const tr = document.createElement('tr');
    if (p.is_legend) tr.classList.add('legend');

    const tdC = document.createElement('td');
    tdC.className = 'st';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = state.selected.has(p.page);
    cb.addEventListener('change', () => {
      cb.checked ? state.selected.add(p.page) : state.selected.delete(p.page);
      updateRunnable();
    });
    tdC.append(cb);

    const cells = [
      ['idx', String(p.page)],
      ['mono', p.drawing_no || '—'],
      ['', p.title || (p.is_legend ? '(레전드/목록)' : '—')],
      ['idx mono', String(p.candidates.length)],
    ].map(([cls, text]) => {
      const td = document.createElement('td');
      td.className = cls;
      td.textContent = text;
      return td;
    });

    const tdW = document.createElement('td');
    if (p.conflicts.length) {
      tdW.className = 'warn';
      tdW.textContent = p.conflicts.join(' / ');
    }
    tr.append(tdC, ...cells, tdW);
    tb.append(tr);
  }
  const legend = state.pages.filter((p) => p.is_legend).length;
  const conf = state.pages.filter((p) => p.conflicts.length).length;
  $('pages-note').textContent =
    `${state.pages.length}쪽 중 레전드/목록 ${legend}쪽은 기본 제외했습니다.`
    + (conf ? ` 도면번호·제목이 어긋난 ${conf}쪽은 사람이 확인해야 합니다.` : '');
  updateRunnable();
}

$('btn-all').addEventListener('click', () => {
  state.selected = new Set(state.pages.filter((p) => !p.is_legend).map((p) => p.page));
  renderPages();
});
$('btn-none').addEventListener('click', () => { state.selected.clear(); renderPages(); });
$('btn-conflicts').addEventListener('click', () => {
  state.selected = new Set(state.pages.filter((p) => p.conflicts.length).map((p) => p.page));
  renderPages();
});

function updateRunnable() {
  const ready = state.pages.length && state.spec && state.selected.size;
  $('sec-run').classList.toggle('hidden', !state.pages.length || !state.spec);
  $('btn-run').disabled = !ready;
  $('btn-run').textContent = ready ? `선택한 ${state.selected.size}장 판독` : '선택한 도면 판독';
  updateSubtitle();
}
function updateSubtitle() {
  const s = state.settings;
  let text = `${s.model} · effort ${s.effort} · 타일 ${s.tiles} · ${s.dpi}dpi`;
  const q = state.server?.quota;
  if (q?.enabled) text += ` · 오늘 남은 판독 ${q.remaining}/${q.limit}장`;
  $('subtitle').textContent = text;
}

/* ── 판독 ──────────────────────────────────────────────── */
$('btn-run').addEventListener('click', run);
$('btn-stop').addEventListener('click', () => state.controller?.abort());

async function run() {
  const dry = $('opt-dry').checked;
  if (!dry && !state.server && !state.settings.apiKey) {
    alert('API 키가 없습니다. ⚙ 설정에서 입력하거나 "API 없이 시험 실행"을 켜세요.');
    return;
  }
  // 도중에 한도가 걸려 반만 판독되는 일이 없도록 시작 전에 알린다.
  const q = state.server?.quota;
  if (!dry && q?.enabled && state.selected.size > q.remaining) {
    const msg = q.remaining === 0
      ? `오늘 판독 한도(${q.limit}장)를 모두 썼습니다. 자정 이후 다시 시도하세요.`
      : `오늘 ${q.remaining}장만 더 판독할 수 있는데 ${state.selected.size}장을 선택했습니다.\n`
        + `${q.remaining}장까지만 판독되고 나머지는 한도 초과로 실패합니다. 계속할까요?`;
    if (q.remaining === 0) { alert(msg); return; }
    if (!confirm(msg)) return;
  }
  $('run-error').classList.add('hidden');
  $('run-log').classList.remove('hidden');
  $('run-log').innerHTML = '';
  setRunning(true);

  const [cols, rows] = state.settings.tiles.split('x').map(Number);
  const schema = ClaudeAPI.buildSchema(state.spec);
  const system = ClaudeAPI.systemPrompt(state.spec, state.rules);
  const targets = state.pages.filter((p) => state.selected.has(p.page));

  state.controller = new AbortController();
  const acc = { rows: [], excluded: [], findings: [], pages: [], usage: { input: 0, output: 0, cached: 0 } };

  try {
    for (let i = 0; i < targets.length; i++) {
      const p = targets[i];
      const line = logLine(`p${p.page} ${p.drawing_no || '—'}`, `${i + 1}/${targets.length}`);
      let data;
      if (dry) {
        data = baseline(p);
        line.set('기준선 생성', 'ok');
      } else {
        line.set('이미지 만드는 중…');
        const images = await PDFScan.renderPage(state.doc, p.page,
          { cols, rows, dpi: state.settings.dpi });
        line.set(`판독 중 (이미지 ${1 + images.tiles.length}장)…`);
        const res = await ClaudeAPI.extractDrawing({
          apiKey: state.settings.apiKey,
          endpoint: state.server ? '/api/extract' : null,
          model: state.settings.model,
          effort: state.settings.effort,
          maxTokens: state.settings.maxTokens,
          system, schema, page: p, images,
          signal: state.controller.signal,
          onDelta: (n) => line.set(`판독 중… ${n.toLocaleString()}자`),
        });
        data = res.data;
        if (res.usage) {
          acc.usage.input += (res.usage.input_tokens || 0);
          acc.usage.cached += (res.usage.cache_read_input_tokens || 0);
          acc.usage.output += (res.usage.output_tokens || 0);
        }
        line.set(`계기 ${data.instruments.length}행 · 제외 ${data.excluded.length} · 확인 ${data.review_findings.length}`, 'ok');
      }

      for (const row of data.instruments) {
        if (!row.pid_no) row.pid_no = p.drawing_no || '';
        row._page = p.page;
        acc.rows.push(row);
      }
      acc.excluded.push(...data.excluded.map((e) => ({ ...e, _page: p.page })));
      acc.findings.push(...data.review_findings.map((f) => ({ ...f, _page: p.page })));
      acc.pages.push({ page: p.page, drawing_no: p.drawing_no, title: p.title,
                       count: data.instruments.length, summary: data.page_summary });
    }
    state.result = acc;
    renderResult();
    setRunning(false, `완료 · 도면 ${targets.length}장 → ${acc.rows.length}행`);
  } catch (err) {
    setRunning(false, err.name === 'AbortError' ? '중지했습니다.' : '');
    if (err.name !== 'AbortError') {
      $('run-error').textContent = err.message;
      $('run-error').classList.remove('hidden');
    }
    if (acc.rows.length) {                 // 중간까지 나온 결과는 살린다
      state.result = acc;
      renderResult();
    }
  } finally {
    state.controller = null;
    if (!dry) refreshQuota();
  }
}

function setRunning(on, msg = '') {
  $('btn-run').disabled = on || !state.selected.size;
  $('btn-stop').classList.toggle('hidden', !on);
  $('run-status').textContent = msg;
  $('run-status').classList.toggle('busy', on);
}

function logLine(label, counter) {
  const div = document.createElement('div');
  div.className = 'log-line';
  const a = document.createElement('span');
  a.className = 'log-label mono';
  a.textContent = label;
  const b = document.createElement('span');
  b.className = 'log-msg';
  const c = document.createElement('span');
  c.className = 'log-count mono';
  c.textContent = counter;
  div.append(a, b, c);
  $('run-log').append(div);
  div.scrollIntoView({ block: 'nearest' });
  return { set: (t, cls) => { b.textContent = t; if (cls) div.classList.add(cls); } };
}

/** API 없이 텍스트 레이어만으로 만드는 기준선. 파이프라인 점검용. */
const TOKEN_TO_TYPE = {
  PT: 'PIT', TT: 'TIT', LT: 'LIT', FT: 'FIT', AT: 'AIT',
  PIT: 'PIT', TIT: 'TIT', LIT: 'LIT', FIT: 'FIT', AIT: 'AIT',
  PI: 'PI', TI: 'TI', LI: 'LI', FI: 'FI',
  PDIT: 'PDIT', PDI: 'PDIT', PDT: 'PDIT',
  FE: 'FE', RO: 'RO', LS: 'LS', FS: 'FS', PS: 'PS', TS: 'TS',
};
const NOT_FIELD = new Set(['ZS', 'ZSC', 'ZSO', 'HS', 'XS']);

function baseline(p) {
  const counts = {}; const excluded = [];
  for (const c of p.candidates) {
    if (NOT_FIELD.has(c.token)) {
      excluded.push({ token: c.token, location: `x=${c.x},y=${c.y}`,
                      reason: '밸브 리밋스위치 계열이라 Field Instrument 범위 밖' });
      continue;
    }
    const t = TOKEN_TO_TYPE[c.token];
    if (!t) {
      excluded.push({ token: c.token, location: `x=${c.x},y=${c.y}`, reason: '매핑에 없는 문자' });
      continue;
    }
    counts[t] = (counts[t] || 0) + 1;
  }
  const instruments = Object.entries(counts).sort().map(([type, n]) => ({
    system: '', pid_no: p.drawing_no || '', type, qty: String(n), description: '-',
    inst_typical_type: '', remark: '-',
    source_tokens: `텍스트 레이어 ${type} ${n}건`, confidence: 'low',
  }));
  return {
    instruments, excluded,
    review_findings: [{
      severity: 'high', location: p.drawing_no || '',
      finding: '시험 실행 결과입니다. DESCRIPTION과 수량 통합이 반영되지 않았습니다.',
      recommendation: '실제 판독은 API 키를 넣고 "API 없이 시험 실행"을 끈 뒤 실행하세요.',
    }],
    page_summary: `기준선: 후보 ${p.candidates.length}건 → ${instruments.length}행`,
  };
}

/* ── 결과 ──────────────────────────────────────────────── */
const MONO_KEYS = new Set(['pid_no', 'type', 'qty', 'inst_typical_type', 'signal_type']);

function shownColumns() {
  return state.spec.columns.filter((c) => ['auto_index', 'drawing', 'typical'].includes(c.source));
}

function withTypicals(row) {
  const x = (row.inst_typical_type || '').trim();
  return { ...row, ...(state.spec.typicals[x] || {}) };
}

function renderResult() {
  $('sec-result').classList.remove('hidden');
  const cols = shownColumns();

  const head = $('result-head');
  head.innerHTML = '';
  const thIdx = document.createElement('th');
  thIdx.className = 'idx';
  thIdx.textContent = '#';
  head.append(thIdx);
  for (const c of cols) {
    const th = document.createElement('th');
    th.textContent = c.label || c.key;
    th.title = `${c.col}열 · ${c.source}`;
    head.append(th);
  }
  const thConf = document.createElement('th');
  thConf.textContent = '확신도';
  head.append(thConf);

  renderRows();

  const u = state.result.usage;
  const low = state.result.rows.filter((r) => r.confidence === 'low').length;
  $('result-stats').innerHTML =
    chip('', '행', state.result.rows.length)
    + chip('c-low', '확신도 low', low)
    + chip('c-del', '제외', state.result.excluded.length)
    + chip('c-add', '확인 필요', state.result.findings.length)
    + (u.output ? chip('', '토큰', `${(u.input + u.cached).toLocaleString()} / ${u.output.toLocaleString()}`) : '');

  $('excl-count').textContent = String(state.result.excluded.length);
  const et = document.querySelector('#excluded tbody');
  et.innerHTML = '';
  for (const e of state.result.excluded) {
    const tr = document.createElement('tr');
    for (const v of [drawingOf(e._page), e.token, e.location, e.reason]) {
      const td = document.createElement('td');
      td.textContent = v ?? '';
      tr.append(td);
    }
    et.append(tr);
  }

  $('find-count').textContent = String(state.result.findings.length);
  const ul = $('findings');
  ul.innerHTML = '';
  for (const f of state.result.findings) {
    const li = document.createElement('li');
    const b = document.createElement('span');
    b.className = `tag sev-${f.severity}`;
    b.textContent = f.severity;
    li.append(b, document.createTextNode(` [${f.location}] ${f.finding} → ${f.recommendation}`));
    ul.append(li);
  }
  $('sec-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRows() {
  const cols = shownColumns();
  const q = $('f-text').value.trim().toLowerCase();
  const tb = document.querySelector('#result tbody');
  tb.innerHTML = '';
  state.result.rows.forEach((raw, i) => {
    const row = withTypicals(raw);
    if (q && !Object.values(row).join(' ').toLowerCase().includes(q)) return;
    const tr = document.createElement('tr');
    const td0 = document.createElement('td');
    td0.className = 'idx';
    td0.textContent = String(i + 1);
    tr.append(td0);
    for (const c of cols) {
      const td = document.createElement('td');
      td.textContent = c.source === 'auto_index' ? i + 1 : (row[c.key] ?? '');
      if (MONO_KEYS.has(c.key)) td.classList.add('mono');
      if (c.source === 'typical') td.classList.add('ro');
      tr.append(td);
    }
    const tdC = document.createElement('td');
    const tag = document.createElement('span');
    tag.className = `tag ${row.confidence === 'low' ? 'low' : row.confidence === 'medium' ? 'med' : 'ok'}`;
    tag.textContent = row.confidence || '·';
    tag.title = row.source_tokens || '';
    tdC.append(tag);
    tr.append(tdC);
    tb.append(tr);
  });
}
$('f-text').addEventListener('input', () => state.result && renderRows());

const chip = (cls, label, value) => `<span class="chip ${cls}">${label} <b>${value}</b></span>`;
const drawingOf = (page) => (state.pages.find((p) => p.page === page) || {}).drawing_no || '';

/* ── 내보내기 ──────────────────────────────────────────── */
$('btn-xlsx').addEventListener('click', () => {
  const rows = state.result.rows.map((r) => ({ values: withTypicals(r) }));
  const bytes = XLSX.buildWorkbook(state.template.bytes, rows, state.spec);
  save(bytes, `instrument_list_${stamp()}.xlsx`,
       'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
});

$('btn-csv').addEventListener('click', () => {
  const cols = state.spec.columns.filter((c) => c.source !== 'blank');
  const head = cols.map((c) => c.label || c.key);
  const body = state.result.rows.map((r, i) => {
    const row = withTypicals(r);
    return cols.map((c) => (c.source === 'auto_index' ? String(i + 1)
      : ['drawing', 'typical'].includes(c.source) ? String(row[c.key] ?? '') : ''));
  });
  const csv = [head, ...body].map((r) => r.map((v) => `"${v.replace(/"/g, '""')}"`).join(',')).join('\r\n');
  save('﻿' + csv, `instrument_list_${stamp()}.csv`, 'text/csv;charset=utf-8');
});

$('btn-json').addEventListener('click', () => {
  const out = {
    run_id: `web_${stamp()}`,
    created_at: new Date().toISOString(),
    model: $('opt-dry').checked ? '(시험 실행)' : state.settings.model,
    sheet: state.spec.sheet,
    xlsx: `instrument_list_${stamp()}.xlsx`,
    columns: state.spec.columns.map(({ col, key, label, source }) => ({ col, key, label, source })),
    instrument_types: state.spec.instrumentTypes,
    systems: state.spec.systems,
    type_to_typical_types: state.spec.typeToTypicalTypes,
    pages: state.result.pages,
    excluded: state.result.excluded,
    review_findings: state.result.findings,
    rows: state.result.rows.map((raw, i) => {
      const row = withTypicals(raw);
      const values = {};
      for (const c of state.spec.columns) {
        values[c.key] = c.source === 'auto_index' ? i + 1
          : ['drawing', 'typical'].includes(c.source) ? (row[c.key] ?? '') : '';
      }
      return {
        index: i, values,
        confidence: raw.confidence || '', source_tokens: raw.source_tokens || '',
        page: raw._page ?? null, drawing_title: (state.result.pages.find((p) => p.page === raw._page) || {}).title || '',
      };
    }),
  };
  save(JSON.stringify(out, null, 2), `result_${stamp()}.json`, 'application/json');
});

const stamp = () => new Date().toISOString().slice(0, 16).replace(/[-:T]/g, '').replace(/(\d{8})(\d{4})/, '$1_$2');

function save(data, filename, mime) {
  const blob = data instanceof Uint8Array ? new Blob([data], { type: mime }) : new Blob([data], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* ── 공유 링크 서버 모드 ───────────────────────────────────
 * /api/config 가 응답하면 서버 배포본이다. 이때 API 키는 서버에만 있고,
 * 템플릿도 서버가 내려준다. 사용자는 비밀번호만 넣으면 된다.
 */
async function detectServer() {
  try {
    const res = await fetch('/api/config', { credentials: 'same-origin' });
    if (!res.ok) return null;
    const cfg = await res.json();
    return cfg.server ? cfg : null;
  } catch {
    return null;      // file:// 이거나 정적 배포 — 로컬 모드
  }
}

function applyServerMode(cfg) {
  state.server = cfg;
  Object.assign(state.settings, {
    model: cfg.model, effort: cfg.effort, maxTokens: cfg.maxTokens,
    tiles: cfg.tiles, dpi: cfg.dpi,
  });
  // 서버가 정하는 값이므로 브라우저에서 바꾸지 못하게 한다.
  $('btn-settings').classList.add('hidden');
  $('dz-tpl').classList.add('locked');
  document.body.classList.add('server-mode');
  updateSubtitle();
}

/** 남은 판독 수를 다시 받아 부제목에 반영한다. 실패해도 무시한다. */
async function refreshQuota() {
  if (!state.server) return;
  try {
    const res = await fetch('/api/config', { credentials: 'same-origin' });
    if (!res.ok) return;
    const cfg = await res.json();
    if (cfg.quota) { state.server.quota = cfg.quota; updateSubtitle(); }
  } catch { /* 부가 정보이므로 조용히 넘어간다 */ }
}

async function serverLogin(password) {
  const res = await fetch('/api/login', {
    method: 'POST', credentials: 'same-origin',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `로그인 실패 (HTTP ${res.status})`);
  return true;
}

async function loadServerTemplate() {
  const res = await fetch('/api/template', { credentials: 'same-origin' });
  if (!res.ok) throw new Error(`템플릿을 받지 못했습니다 (HTTP ${res.status})`);
  const bytes = new Uint8Array(await res.arrayBuffer());
  await useTemplate('서버 템플릿', bytes);
}

function showLogin(show) {
  $('login').classList.toggle('hidden', !show);
  document.querySelector('main').classList.toggle('hidden', show);
  if (show) setTimeout(() => $('login-password').focus(), 50);
}

$('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const err = $('login-error');
  err.classList.add('hidden');
  $('login-submit').disabled = true;
  try {
    await serverLogin($('login-password').value);
    showLogin(false);
    await refreshQuota();
    await loadServerTemplate();
  } catch (ex) {
    err.textContent = ex.message;
    err.classList.remove('hidden');
  } finally {
    $('login-submit').disabled = false;
    $('login-password').value = '';
  }
});

/* ── 시작 ──────────────────────────────────────────────── */
(async function init() {
  loadSettings();
  updateSubtitle();

  const cfg = await detectServer();
  if (cfg) {
    applyServerMode(cfg);
    if (!cfg.authed) { showLogin(true); return; }
    try { await loadServerTemplate(); } catch (err) { console.warn(err); }
  }

  const tpl = await idbGet('template');
  if (tpl && !state.spec) await useTemplate(tpl.name, tpl.bytes);
  const pdf = await idbGet('pdf');
  if (pdf) { state.pdf = pdf; await scanPdf(); }
})();
