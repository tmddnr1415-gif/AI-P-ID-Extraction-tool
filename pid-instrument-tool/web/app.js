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
    if (state.result?.rows?.length) renderResult();   // 템플릿을 기다리던 결과를 이제 그린다
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
  updateCostNote();
}

/* 판독 전에 이번 요청이 얼마나 큰지 알려 준다. 대형 도면 이미지가 입력 토큰의 대부분이라
 * 타일 수와 DPI가 비용을 좌우한다. 단가는 계정마다 다르므로 토큰 수만 보여 준다. */
function estimateTokens() {
  const [cols, rows] = state.settings.tiles.split('x').map(Number);
  const dpi = state.settings.dpi;
  const px = (w, h) => Math.min(w * h, 2576 * 2576);
  // A1 가로 도면 기준 (594×841mm). 전체 1장 + 타일 cols×rows
  const fullPx = px(2576, 1820);
  const tileW = (841 / 25.4) * dpi / cols * 1.08;
  const tileH = (594 / 25.4) * dpi / rows * 1.08;
  const perDrawing = (fullPx + cols * rows * px(tileW, tileH)) / 750;
  const n = state.selected.size;
  return { perDrawing: Math.round(perDrawing), total: Math.round(perDrawing * n), tiles: cols * rows, n };
}

function updateCostNote() {
  const el = $('cost-note');
  if (!el) return;
  if (!state.selected.size || $('opt-dry').checked) { el.textContent = ''; return; }
  const e = estimateTokens();
  el.innerHTML =
    `이번 판독 예상 입력 <b>약 ${(e.total / 1000).toFixed(0)}k 토큰</b> `
    + `(도면당 ${(e.perDrawing / 1000).toFixed(0)}k × ${e.n}장). `
    + `대부분이 도면 이미지라 <b>타일 ${e.tiles}장 · ${state.settings.dpi}dpi</b> 설정이 비용을 좌우합니다. `
    + `줄이려면 ⚙ 설정에서 타일을 2x2, dpi를 150으로 낮추거나 모델을 Sonnet으로 바꾸세요. `
    + `단가는 <a href="https://console.anthropic.com/settings/billing" target="_blank" rel="noopener">Console</a>에서 확인하세요.`;
}
$('opt-dry').addEventListener('change', updateCostNote);
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

  /* 판독 결과는 쌓인다. 58장을 5장씩 끊어 돌려도 이어지도록, 이전 결과를 이어받되
     이번에 다시 판독하는 도면의 옛 행은 걷어낸다(같은 도면이 두 번 들어가지 않게). */
  const redo = new Set(targets.map((p) => p.page));
  const prev = state.result;
  const acc = prev
    ? {
        rows: prev.rows.filter((r) => !redo.has(r._page)),
        excluded: prev.excluded.filter((e) => !redo.has(e._page)),
        findings: prev.findings.filter((f) => !redo.has(f._page)),
        pages: prev.pages.filter((p) => !redo.has(p.page)),
        usage: { ...prev.usage },
      }
    : { rows: [], excluded: [], findings: [], pages: [], usage: { input: 0, output: 0, cached: 0 } };

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
    setResult(acc);
    setRunning(false, `완료 · 이번 ${targets.length}장 · 누적 도면 ${acc.pages.length}장 → ${acc.rows.length}행`);
  } catch (err) {
    setRunning(false, err.name === 'AbortError' ? '중지했습니다.' : '');
    if (err.name !== 'AbortError') {
      $('run-error').textContent = err.message;
      $('run-error').classList.remove('hidden');
    }
    if (acc.rows.length) setResult(acc);   // 중간까지 나온 결과는 살린다
  } finally {
    state.controller = null;
    if (!dry) refreshQuota();
  }
}

/** 결과를 갈아끼우고 화면과 브라우저 보관을 함께 갱신한다. */
function setResult(acc) {
  state.result = acc;
  renderResult();
  idbPut('result', acc);                   // 브라우저를 닫아도 남는다
}

$('btn-clear').addEventListener('click', () => {
  if (!state.result) return;
  const n = state.result.pages.length;
  if (!confirm(`쌓인 판독 결과를 모두 비웁니다.\n도면 ${n}장 · ${state.result.rows.length}행이 사라집니다.`)) return;
  state.result = null;
  idbPut('result', null);
  $('sec-result').classList.add('hidden');
  $('run-status').textContent = '결과를 비웠습니다.';
});

/* ── 결과 불러오기 ─────────────────────────────────────────
 * 앱이 내보낸 검토용 JSON(result_*.json)과 파이썬 파이프라인의 extraction.json
 * 둘 다 받는다. 형식이 달라 보여도 결국 같은 판독 결과다.
 */
$('btn-import').addEventListener('click', () => $('in-import').click());
$('in-import').addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const st = $('import-state');
  try {
    const data = JSON.parse(await file.text());
    const acc = normalizeImported(data);
    if (!acc.rows.length) throw new Error('계기 행을 찾지 못했습니다.');
    setResult(acc);
    st.textContent = `${file.name} · 도면 ${acc.pages.length}장 ${acc.rows.length}행`;
    st.className = 'state ok';
    $('sec-result').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    st.textContent = `읽지 못했습니다 — ${err.message}`;
    st.className = 'state bad';
  } finally {
    e.target.value = '';
  }
});

function normalizeImported(data) {
  const pages = data.pages || [];
  const drawingKeys = (state.spec?.columns || []).filter((c) => c.source === 'drawing').map((c) => c.key);
  let rows;
  if (Array.isArray(data.instruments)) {
    // 파이썬 extraction.json — 판독 키가 그대로 들어 있다
    rows = data.instruments.map((r) => ({ ...r }));
  } else if (Array.isArray(data.rows)) {
    // 앱이 내보낸 검토용 JSON — values 안에 컬럼 키로 들어 있다
    rows = data.rows.map((r) => {
      const out = { _page: r.page ?? null, confidence: r.confidence || '', source_tokens: r.source_tokens || '' };
      for (const k of drawingKeys.length ? drawingKeys : Object.keys(r.values || {})) {
        if (r.values && r.values[k] !== undefined) out[k] = r.values[k];
      }
      return out;
    });
  } else {
    throw new Error('instruments 또는 rows 배열이 없습니다.');
  }
  return {
    rows,
    excluded: data.excluded || [],
    findings: data.review_findings || data.findings || [],
    pages,
    usage: data.usage || { input: 0, output: 0, cached: 0 },
  };
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

/* NOTES의 "CONFIGURATION IS IDENTICAL FOR ..." 에서 Q'ty를 읽는다.
 *   FOR GROUP#10 … IDENTICAL FOR GROUP#20        → 2
 *   FOR UNIT#11  … IDENTICAL FOR UNIT#12,21,22   → 4
 * 이 도면이 몇 개 호기를 대표하는지가 곧 Q'ty다 (extraction_guide 5.1). */
function qtyFromNotes(notes) {
  const flat = (notes || '').replace(/\s+/g, ' ').toUpperCase();
  const m = flat.match(/CONFIGURATION IS IDENTICAL FOR\s+((?:GROUP|UNIT)?\s*#?\s*[\d,\s#]+)/);
  if (!m) return { qty: 1, why: 'IDENTICAL FOR 노트 없음' };
  const others = (m[1].match(/\d+/g) || []).length;
  return others
    ? { qty: others + 1, why: `NOTES: IDENTICAL FOR ... 다른 호기 ${others}개 → 이 도면 포함 ${others + 1}` }
    : { qty: 1, why: 'IDENTICAL FOR 노트를 읽었지만 호기 번호를 못 찾음' };
}

/** 도면 제목과 템플릿의 SYSTEM 목록을 맞춰 본다. 애매하면 비운다. */
function systemFromTitle(title, systems) {
  const t = (title || '').toUpperCase().replace(/^P&ID FOR\s+/, '');
  let best = '', score = 0;
  for (const s of systems || []) {
    const words = s.toUpperCase().split(/\s+/).filter((w) => w.length > 2);
    const hit = words.filter((w) => t.includes(w)).length / (words.length || 1);
    if (hit > score) { score = hit; best = s; }
  }
  return score >= 0.6 ? best : '';
}

/* DESCRIPTION 을 쓸 때 볼 근거 — 계기 옆에 있던 설비명과 배관 행선지.
 *
 * 이 라벨들로 DESCRIPTION 을 자동 조립해 보았으나 시험 3장에서 69행 중 6행만 맞았다.
 * 어느 라벨을 고를지와 뭐라고 부를지가 곧 판독이라 좌표만으로는 안 된다.
 * 그래서 문장을 지어내지 않고 재료만 붙인다. 사람이 도면을 뒤지지 않아도 되게.
 */
function describeHints(p, c) {
  const near = (kind, wx, wy) => {
    const pool = (p.labels || []).filter((l) => l.kind === kind);
    if (!pool.length) return null;
    const d = (l) => ((l.x - c.x) * wx) ** 2 + ((l.y - c.y) * wy) ** 2;
    return pool.reduce((a, b) => (d(b) < d(a) ? b : a));
  };
  const eq = near('equip', 3, 1);        // 설비 박스는 세로 열로 서 있어 x를 크게 본다
  const ln = near('line', 1, 1.5);
  const bits = [`'${c.token}' @ x=${c.x} y=${c.y}`];
  if (eq) bits.push(`설비 '${eq.t}'`);
  if (ln) bits.push(`배관 '${ln.t}'`);
  return bits.join(' · ');
}

/* API 없이 텍스트 레이어와 NOTES만으로 만드는 기준선.
 *
 * 도면에서 결정적으로 읽히는 것만 채운다 — SYSTEM · P&ID No. · TYPE · Q'ty ·
 * INST. TYPICAL TYPE. DESCRIPTION과 벤더 공급 범위 제외는 도면 그림을 봐야 하는
 * 판단이라 여기서 채우지 않고 사람이 검토 UI에서 채운다.
 */
function baseline(p) {
  const excluded = [];
  const { qty, why } = qtyFromNotes(p.notes);
  const system = systemFromTitle(p.title, state.spec?.systems);
  const top = state.spec?.typeToTopTypical || {};

  const instruments = [];
  for (const c of p.candidates) {
    if (NOT_FIELD.has(c.token)) {
      excluded.push({ token: c.token, location: `x=${c.x},y=${c.y}`,
                      reason: '밸브 리밋스위치 계열이라 Field Instrument 범위 밖' });
      continue;
    }
    const type = TOKEN_TO_TYPE[c.token];
    if (!type) {
      excluded.push({ token: c.token, location: `x=${c.x},y=${c.y}`, reason: '매핑에 없는 문자' });
      continue;
    }
    instruments.push({
      system, pid_no: p.drawing_no || '', type, qty: String(qty),
      description: '',                          // 사람이 채울 칸 — 아래 근거를 보고 쓴다
      inst_typical_type: top[`${system}||${type}`] || top[type] || '', remark: '-',
      source_tokens: describeHints(p, c),
      confidence: 'low',
    });
  }

  const findings = [{
    severity: 'high', location: p.drawing_no || '',
    finding: `API 없이 만든 기준선입니다. 계기 ${instruments.length}건의 SYSTEM · P&ID No. · TYPE · `
      + `Q'ty · INST. TYPICAL TYPE 은 도면에서 결정적으로 읽어 채웠고, DESCRIPTION 은 비어 있습니다.`,
    recommendation: 'DESCRIPTION 은 각 행의 근거 칸에 붙은 설비명·배관 행선지를 보고 쓰세요. '
      + '자동 조립도 시도했지만 시험 3장에서 69행 중 6행만 맞아 문장을 지어내지 않습니다. '
      + '함께 벤더 공급 범위 계기를 지우세요.',
  }, {
    severity: 'high', location: p.drawing_no || '',
    finding: `Q'ty ${qty} — ${why}`,
    recommendation: 'PLANT COMMON 처럼 호기 공용인 설비는 이 배수에서 빼고 1로 고치세요.',
  }];
  if (/DENOTES|MARKED ITEM|SUPPLIED BY/i.test(p.notes || '')) {
    const lines = (p.notes || '').split('\n')
      .filter((l) => /DENOTES|MARKED ITEM|SUPPLIED BY/i.test(l)).join(' / ');
    findings.push({
      severity: 'high', location: p.drawing_no || '',
      finding: `이 도면에 공급 범위 각주가 있습니다 — ${lines}`,
      recommendation: '도면에서 * / ** 표기가 붙은 계기를 찾아 목록에서 지우세요. '
        + '기준선은 표기를 못 읽으므로 그 계기들이 아직 남아 있습니다.',
    });
  }
  if (!system) {
    findings.push({
      severity: 'medium', location: p.drawing_no || '',
      finding: `제목('${p.title || '—'}')이 템플릿 SYSTEM 목록과 맞지 않아 SYSTEM을 비웠습니다.`,
      recommendation: '검토 UI에서 SYSTEM을 골라 주세요.',
    });
  }

  return {
    instruments, excluded, review_findings: findings,
    page_summary: `API 없이 만든 기준선 — 후보 ${p.candidates.length}건 중 ${instruments.length}건을 `
      + `행으로, ${excluded.length}건 제외. Q'ty ${qty}. DESCRIPTION은 비어 있습니다.`,
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
  // 표는 템플릿의 컬럼 정의로 그린다. 템플릿이 아직 없으면 결과만 들고 기다린다.
  if (!state.spec) return;
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
  const saved = await idbGet('result');           // 지난번에 쌓아둔 판독 결과
  if (saved?.rows?.length) { state.result = saved; renderResult(); }
  const pdf = await idbGet('pdf');
  if (pdf) { state.pdf = pdf; await scanPdf(); }
})();
