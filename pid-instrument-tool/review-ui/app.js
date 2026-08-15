/* Instrument List 검토 UI
 *
 * build_excel.py가 만든 result.json을 불러와 사람이 셀 단위로 고치고,
 * 고칠 때마다 "사유"와 "앞으로 어떻게 출력되어야 하는지(규칙 코멘트)"를 함께 남긴다.
 * 내보낸 피드백은 scripts/apply_feedback.py 가 review_log.md와 판독 규칙에 반영한다.
 */
'use strict';

const $ = (id) => document.getElementById(id);
const LS_KEY = (runId) => `pid-review:${runId}`;

const CATEGORY_LABEL = {
  wrong_value: '값 오류',
  description_error: 'DESCRIPTION 오류',
  type_error: 'TYPE 오류',
  qty_error: '수량 오류',
  typical_error: 'TYPICAL TYPE 오류',
  format_error: '형식 오류',
  other: '기타',
  false_positive: '오탐 (있지도 않은 계기)',
  miss: '누락 (빠뜨린 계기)',
};

const state = {
  data: null,            // result.json
  corrections: new Map(),// "rowIndex:colKey" → correction
  deletions: new Map(),  // rowIndex → {reason, rule_comment}
  additions: [],         // {tempId, values, reason, rule_comment}
  editing: null,         // {rowIndex, colKey}
  seen: new Set(),       // 사용자가 한 번이라도 연 행
};

/* ── 파일 로드 ─────────────────────────────────────────────── */
$('btn-load').addEventListener('click', () => $('file-input').click());
$('dropzone').addEventListener('click', () => $('file-input').click());
$('file-input').addEventListener('change', (e) => {
  if (e.target.files[0]) readFile(e.target.files[0]);
  e.target.value = '';
});
['dragenter', 'dragover'].forEach((ev) =>
  $('dropzone').addEventListener(ev, (e) => { e.preventDefault(); $('dropzone').classList.add('over'); }));
['dragleave', 'drop'].forEach((ev) =>
  $('dropzone').addEventListener(ev, (e) => { e.preventDefault(); $('dropzone').classList.remove('over'); }));
$('dropzone').addEventListener('drop', (e) => {
  if (e.dataTransfer.files[0]) readFile(e.dataTransfer.files[0]);
});

function readFile(file) {
  const r = new FileReader();
  r.onload = () => {
    let data;
    try {
      data = JSON.parse(r.result);
    } catch (err) {
      alert(`JSON을 읽지 못했습니다: ${err.message}`);
      return;
    }
    if (!data.rows || !data.columns) {
      alert('result.json 형식이 아닙니다. build_excel.py가 만든 result.json을 여세요.');
      return;
    }
    load(data);
  };
  r.readAsText(file);
}

function load(data) {
  state.data = data;
  state.corrections.clear();
  state.deletions.clear();
  state.additions = [];
  state.seen = new Set();
  restore();

  $('empty').classList.add('hidden');
  $('main').classList.remove('hidden');
  $('run-info').textContent =
    `${data.run_id} · ${data.rows.length}행 · 도면 ${data.pages.length}장 · 모델 ${data.model}` +
    (data.xlsx ? ` · ${data.xlsx}` : '');

  const sel = $('f-drawing');
  sel.innerHTML = '<option value="">전체</option>';
  for (const p of data.pages) {
    const o = document.createElement('option');
    o.value = p.drawing_no;
    o.textContent = `${p.drawing_no} (${p.count})`;
    sel.append(o);
  }

  renderExcluded();
  renderFindings();
  render();
}

/* ── 저장/복원 (브라우저 새로고침에도 검토 내용 유지) ──────── */
function persist() {
  if (!state.data) return;
  const payload = {
    corrections: [...state.corrections.values()],
    deletions: [...state.deletions.entries()].map(([k, v]) => ({ row_index: k, ...v })),
    additions: state.additions,
    seen: [...state.seen],
    reviewer: $('reviewer').value,
  };
  localStorage.setItem(LS_KEY(state.data.run_id), JSON.stringify(payload));
}

function restore() {
  const raw = localStorage.getItem(LS_KEY(state.data.run_id));
  if (!raw) return;
  try {
    const p = JSON.parse(raw);
    for (const c of p.corrections || []) state.corrections.set(`${c.row_index}:${c.column}`, c);
    for (const d of p.deletions || []) state.deletions.set(d.row_index, d);
    state.additions = p.additions || [];
    state.seen = new Set(p.seen || []);
    if (p.reviewer) $('reviewer').value = p.reviewer;
    if (state.corrections.size || state.deletions.size || state.additions.length) {
      console.info('이전 검토 내용을 복원했습니다.');
    }
  } catch { /* 손상된 저장본은 무시 */ }
}

/* ── 렌더링 ────────────────────────────────────────────────── */
function visibleColumns() {
  const compact = $('f-compact').checked;
  return state.data.columns.filter((c) => {
    if (c.source === 'blank') return false;
    if (compact) return ['auto_index', 'drawing', 'typical'].includes(c.source);
    return true;
  });
}

function editable(col) {
  // 판독/사양 컬럼은 고칠 수 있다. 자동 번호와 Design Table 조인 값은 여기서 고치지 않는다.
  return col.source === 'drawing' || col.source === 'typical' || col.source === 'review';
}

function allRows() {
  const base = state.data.rows.map((r) => ({ ...r, _kind: 'model' }));
  const added = state.additions.map((a, i) => ({
    index: `A${i}`, values: a.values, confidence: 'added',
    source_tokens: '사람이 추가한 행', page: a.page || null, drawing_title: '', _kind: 'added', _add: a,
  }));
  return base.concat(added);
}

function filtered() {
  const drawing = $('f-drawing').value;
  const conf = $('f-conf').value ? $('f-conf').value.split(',') : null;
  const st = $('f-state').value;
  const q = $('f-text').value.trim().toLowerCase();

  return allRows().filter((row) => {
    if (drawing && row.values.pid_no !== drawing) return false;
    if (conf && !conf.includes(row.confidence)) return false;
    if (st === 'edited' && !hasEdit(row.index)) return false;
    if (st === 'untouched' && (state.seen.has(String(row.index)) || hasEdit(row.index))) return false;
    if (st === 'deleted' && !state.deletions.has(String(row.index))) return false;
    if (st === 'added' && row._kind !== 'added') return false;
    if (q) {
      const hay = Object.values(row.values).join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function hasEdit(rowIndex) {
  const key = String(rowIndex);
  if (state.deletions.has(key)) return true;
  for (const c of state.corrections.keys()) if (c.startsWith(`${key}:`)) return true;
  return false;
}

function valueOf(row, colKey) {
  const c = state.corrections.get(`${row.index}:${colKey}`);
  return c ? c.after : (row.values[colKey] ?? '');
}

function render() {
  const cols = visibleColumns();

  const head = $('grid-head');
  head.innerHTML = '';
  head.append(th('상태', 'st'), th('#', 'idx'));
  for (const c of cols) {
    const el = th(c.label || c.key);
    el.title = `${c.col}열 · ${c.key} · ${c.source}`;
    if (!editable(c)) el.classList.add('ro');
    head.append(el);
  }
  head.append(th('처리'));

  const body = $('grid-body');
  body.innerHTML = '';
  for (const row of filtered()) {
    const tr = document.createElement('tr');
    const key = String(row.index);
    if (state.deletions.has(key)) tr.classList.add('deleted');
    if (row._kind === 'added') tr.classList.add('added');

    const tdSt = document.createElement('td');
    tdSt.className = 'st';
    tdSt.append(badge(row));
    tr.append(tdSt);

    const tdIdx = document.createElement('td');
    tdIdx.className = 'idx';
    tdIdx.textContent = row._kind === 'added' ? '추가' : row.values.no;
    tdIdx.title = row.page ? `PDF p${row.page} · ${row.drawing_title || ''}` : '';
    tr.append(tdIdx);

    for (const c of cols) {
      const td = document.createElement('td');
      const corrected = state.corrections.has(`${row.index}:${c.key}`);
      td.textContent = valueOf(row, c.key);
      if (!editable(c)) {
        td.classList.add('ro');
      } else {
        td.classList.add('edit');
        td.tabIndex = 0;
        td.addEventListener('click', () => openEditor(row, c));
        td.addEventListener('keydown', (e) => { if (e.key === 'Enter') openEditor(row, c); });
      }
      if (corrected) {
        td.classList.add('corrected');
        td.title = `수정 전: ${row.values[c.key] ?? ''}`;
      }
      tr.append(td);
    }

    const tdAct = document.createElement('td');
    tdAct.className = 'act';
    if (row._kind === 'added') {
      tdAct.append(btn('편집', () => openRowDialog('add', row._add)),
                   btn('제거', () => {
                     state.additions = state.additions.filter((a) => a !== row._add);
                     persist(); render();
                   }, 'danger'));
    } else if (state.deletions.has(key)) {
      tdAct.append(btn('삭제 취소', () => { state.deletions.delete(key); persist(); render(); }));
    } else {
      tdAct.append(btn('오탐 삭제', () => openRowDialog('delete', row), 'danger'));
    }
    tr.append(tdAct);
    body.append(tr);
  }

  renderStats();
  persist();
}

function badge(row) {
  const s = document.createElement('span');
  const key = String(row.index);
  if (state.deletions.has(key)) { s.className = 'tag del'; s.textContent = '삭제'; }
  else if (row._kind === 'added') { s.className = 'tag add'; s.textContent = '추가'; }
  else if (hasEdit(row.index)) { s.className = 'tag fix'; s.textContent = '수정'; }
  else if (row.confidence === 'low') { s.className = 'tag low'; s.textContent = 'low'; }
  else if (row.confidence === 'medium') { s.className = 'tag med'; s.textContent = 'med'; }
  else { s.className = 'tag ok'; s.textContent = '·'; }
  return s;
}

function th(text, cls) {
  const el = document.createElement('th');
  el.textContent = text;
  if (cls) el.className = cls;
  return el;
}

function btn(label, onClick, cls) {
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'ghost' + (cls ? ' ' + cls : '');
  b.textContent = label;
  b.addEventListener('click', onClick);
  return b;
}

function renderStats() {
  const total = state.data.rows.length;
  const shown = filtered().length;
  const cells = state.corrections.size;
  const dels = state.deletions.size;
  const adds = state.additions.length;
  const low = state.data.rows.filter((r) => r.confidence === 'low').length;
  $('stats').innerHTML =
    `<span>표시 <b>${shown}</b> / 전체 ${total}행</span>` +
    `<span>셀 수정 <b>${cells}</b></span>` +
    `<span>오탐 삭제 <b>${dels}</b></span>` +
    `<span>누락 추가 <b>${adds}</b></span>` +
    `<span>확신도 low <b>${low}</b></span>`;

  const touched = new Set([...state.seen]);
  for (const k of state.corrections.keys()) touched.add(k.split(':')[0]);
  for (const k of state.deletions.keys()) touched.add(k);
  const pct = total ? Math.round(100 * Math.min(touched.size, total) / total) : 0;
  $('progress').innerHTML =
    `<div class="bar"><i style="width:${pct}%"></i></div><span>검토 진행 ${pct}% (${Math.min(touched.size, total)}/${total}행)</span>`;
}

function renderExcluded() {
  const rows = state.data.excluded || [];
  $('excl-count').textContent = String(rows.length);
  const tb = document.querySelector('#excluded tbody');
  tb.innerHTML = '';
  for (const e of rows) {
    const tr = document.createElement('tr');
    for (const v of [drawingOfPage(e._page), e.token, e.location, e.reason]) {
      const td = document.createElement('td');
      td.textContent = v ?? '';
      tr.append(td);
    }
    const td = document.createElement('td');
    td.append(btn('이건 누락임 → 행 추가', () => {
      openRowDialog('add', {
        values: { pid_no: drawingOfPage(e._page) || '', type: e.token, qty: '1', description: '', remark: '-' },
        page: e._page,
        reason: `제외 목록에 있었으나 실제로는 Field Instrument임 (제외 사유: ${e.reason})`,
      });
    }));
    tr.append(td);
    tb.append(tr);
  }
}

function renderFindings() {
  const rows = state.data.review_findings || [];
  $('find-count').textContent = String(rows.length);
  const ul = $('findings');
  ul.innerHTML = '';
  for (const f of rows) {
    const li = document.createElement('li');
    const b = document.createElement('span');
    b.className = `tag sev-${f.severity}`;
    b.textContent = f.severity;
    const t = document.createElement('span');
    t.textContent = ` [${f.location}] ${f.finding} → ${f.recommendation}`;
    li.append(b, t);
    ul.append(li);
  }
}

function drawingOfPage(page) {
  const p = (state.data.pages || []).find((x) => x.page === page);
  return p ? p.drawing_no : '';
}

/* ── 셀 수정 패널 ──────────────────────────────────────────── */
function openEditor(row, col) {
  state.editing = { row, col };
  state.seen.add(String(row.index));

  const existing = state.corrections.get(`${row.index}:${col.key}`);
  $('ed-title').textContent = `${col.label || col.key} 수정`;
  $('ed-drawing').textContent = row.values.pid_no || '-';
  $('ed-row').textContent = row._kind === 'added' ? '사람이 추가한 행' : `${row.values.no}행 (PDF p${row.page ?? '?'})`;
  $('ed-col').textContent = `${col.label || col.key} (${col.col}열)`;
  $('ed-conf').textContent = row.confidence || '-';
  $('ed-evidence').textContent = row.source_tokens || '-';
  $('ed-before').textContent = row.values[col.key] === '' ? '(비어 있음)' : row.values[col.key];

  $('ed-after').value = existing ? existing.after : (row.values[col.key] ?? '');
  $('ed-category').value = existing ? existing.category : defaultCategory(col.key);
  $('ed-reason').value = existing ? existing.reason : '';
  $('ed-rule').value = existing ? existing.rule_comment : '';
  $('ed-hint').textContent = hintFor(col.key);
  $('ed-delete').classList.toggle('hidden', !existing);

  $('editor').classList.remove('hidden');
  $('ed-after').focus();
  render();
}

function defaultCategory(key) {
  return ({ description: 'description_error', type: 'type_error', qty: 'qty_error',
            inst_typical_type: 'typical_error' })[key] || 'wrong_value';
}

function hintFor(key) {
  const d = state.data;
  if (key === 'type') return `허용 TYPE: ${d.instrument_types.join(', ')}`;
  if (key === 'system') return `허용 SYSTEM: ${d.systems.slice(0, 8).join(', ')} …`;
  if (key === 'inst_typical_type') {
    const t = state.editing?.row.values.type;
    const list = d.type_to_typical_types[t];
    return list ? `TYPE ${t}의 허용 TYPICAL: ${list.join(', ')}` : '';
  }
  if (key === 'qty') return '숫자만 입력하세요.';
  if (key === 'description') return 'UNIT 번호 + 설비/계통 + 측정 대상 + 서브 식별자, 영문 대문자';
  return '';
}

$('ed-close').addEventListener('click', closeEditor);
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !$('editor').classList.contains('hidden')) closeEditor();
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey) && !$('editor').classList.contains('hidden')) saveEdit();
});
function closeEditor() {
  $('editor').classList.add('hidden');
  state.editing = null;
}

document.querySelectorAll('.quick button').forEach((b) =>
  b.addEventListener('click', () => { $('ed-rule').value = b.dataset.quick; }));

$('ed-save').addEventListener('click', saveEdit);
function saveEdit() {
  const { row, col } = state.editing || {};
  if (!row) return;
  const after = $('ed-after').value.trim();
  const reason = $('ed-reason').value.trim();
  const rule = $('ed-rule').value.trim();

  if (!reason || !rule) {
    alert('사유와 규칙 코멘트는 반드시 입력해야 합니다.\n\n'
        + '이 두 칸이 다음 판독 규칙 개정의 근거가 됩니다.');
    (!reason ? $('ed-reason') : $('ed-rule')).focus();
    return;
  }
  const before = row.values[col.key] ?? '';
  if (after === String(before)) {
    alert('값이 바뀌지 않았습니다. 값을 고치거나 창을 닫으세요.');
    return;
  }

  state.corrections.set(`${row.index}:${col.key}`, {
    row_index: String(row.index),
    row_kind: row._kind,
    row_key: { pid_no: row.values.pid_no, type: row.values.type, description: row.values.description },
    page: row.page ?? null,
    column: col.key,
    column_label: col.label || col.key,
    column_letter: col.col,
    before: String(before),
    after,
    category: $('ed-category').value,
    reason,
    rule_comment: rule,
    confidence: row.confidence,
    source_tokens: row.source_tokens,
    at: new Date().toISOString(),
  });
  closeEditor();
  render();
}

$('ed-delete').addEventListener('click', () => {
  const { row, col } = state.editing || {};
  if (!row) return;
  state.corrections.delete(`${row.index}:${col.key}`);
  closeEditor();
  render();
});

/* ── 행 처리 다이얼로그 (오탐 삭제 / 누락 추가) ────────────── */
let rowDialogMode = null;
let rowDialogTarget = null;

function openRowDialog(mode, target) {
  rowDialogMode = mode;
  rowDialogTarget = target;
  const dlg = $('rowdlg');
  const fields = $('rd-fields');
  fields.innerHTML = '';
  $('rd-error').classList.add('hidden');

  if (mode === 'delete') {
    $('rd-title').textContent = '오탐으로 삭제';
    const p = document.createElement('p');
    p.className = 'rd-summary';
    p.textContent = `${target.values.pid_no} · ${target.values.type} · ${target.values.description}`;
    fields.append(p);
    $('rd-reason').value = '';
    $('rd-rule').value = '';
  } else {
    $('rd-title').textContent = target.tempId ? '추가한 행 편집' : '누락 계기 추가';
    const vals = target.values || {};
    for (const c of state.data.columns.filter((c) => c.source === 'drawing')) {
      const wrap = document.createElement('label');
      wrap.className = 'field';
      const s = document.createElement('span');
      s.textContent = c.label || c.key;
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.dataset.key = c.key;
      inp.value = vals[c.key] ?? '';
      if (c.key === 'pid_no' && !inp.value) inp.value = $('f-drawing').value || '';
      wrap.append(s, inp);
      fields.append(wrap);
    }
    $('rd-reason').value = target.reason || '';
    $('rd-rule').value = target.rule_comment || '';
  }
  dlg.showModal();
}

$('rowdlg').addEventListener('close', () => {
  if ($('rowdlg').returnValue !== 'ok') return;
  const reason = $('rd-reason').value.trim();
  const rule = $('rd-rule').value.trim();
  if (!reason || !rule) {
    alert('사유와 규칙 코멘트는 반드시 입력해야 합니다.');
    openRowDialog(rowDialogMode, rowDialogTarget);
    return;
  }

  if (rowDialogMode === 'delete') {
    state.deletions.set(String(rowDialogTarget.index), {
      row_index: String(rowDialogTarget.index),
      row_key: {
        pid_no: rowDialogTarget.values.pid_no,
        type: rowDialogTarget.values.type,
        description: rowDialogTarget.values.description,
      },
      page: rowDialogTarget.page ?? null,
      category: 'false_positive',
      reason, rule_comment: rule, at: new Date().toISOString(),
    });
  } else {
    const values = {};
    $('rd-fields').querySelectorAll('input[data-key]').forEach((i) => { values[i.dataset.key] = i.value.trim(); });
    const rec = rowDialogTarget.tempId ? rowDialogTarget
      : { tempId: `add-${Date.now()}`, page: rowDialogTarget.page ?? null };
    Object.assign(rec, { values, category: 'miss', reason, rule_comment: rule, at: new Date().toISOString() });
    if (!state.additions.includes(rec)) state.additions.push(rec);
  }
  render();
});

$('btn-add-row').addEventListener('click', () => openRowDialog('add', { values: {} }));

/* ── 필터 ──────────────────────────────────────────────────── */
['f-drawing', 'f-conf', 'f-state', 'f-compact'].forEach((id) => $(id).addEventListener('change', render));
$('f-text').addEventListener('input', render);
$('reviewer').addEventListener('change', persist);

/* ── 내보내기 ──────────────────────────────────────────────── */
function feedback() {
  return {
    run_id: state.data.run_id,
    source_xlsx: state.data.xlsx || null,
    reviewer: $('reviewer').value.trim() || '(이름 미입력)',
    reviewed_at: new Date().toISOString(),
    stats: {
      total_rows: state.data.rows.length,
      cell_corrections: state.corrections.size,
      row_deletions: state.deletions.size,
      row_additions: state.additions.length,
    },
    cell_corrections: [...state.corrections.values()],
    row_deletions: [...state.deletions.values()],
    row_additions: state.additions,
  };
}

$('btn-export-feedback').addEventListener('click', () => {
  const fb = feedback();
  if (!fb.stats.cell_corrections && !fb.stats.row_deletions && !fb.stats.row_additions) {
    if (!confirm('수정 내역이 없습니다. 그래도 내보낼까요?')) return;
  }
  download(JSON.stringify(fb, null, 2), `feedback_${state.data.run_id}.json`, 'application/json');
});

$('btn-export-result').addEventListener('click', () => {
  const out = structuredClone(state.data);
  out.rows = state.data.rows
    .filter((r) => !state.deletions.has(String(r.index)))
    .map((r) => {
      const c = { ...r, values: { ...r.values } };
      for (const col of state.data.columns) {
        const fix = state.corrections.get(`${r.index}:${col.key}`);
        if (fix) c.values[col.key] = fix.after;
      }
      return c;
    });
  for (const a of state.additions) {
    out.rows.push({ index: out.rows.length, values: { ...a.values }, confidence: 'human',
                    source_tokens: '검토자가 추가', page: a.page ?? null, drawing_title: '' });
  }
  out.rows.forEach((r, i) => { r.values.no = i + 1; r.index = i; });
  out.reviewed = { by: $('reviewer').value.trim(), at: new Date().toISOString(), ...feedback().stats };
  download(JSON.stringify(out, null, 2), `result_reviewed_${state.data.run_id}.json`, 'application/json');
});

$('btn-export-csv').addEventListener('click', () => {
  const cols = state.data.columns.filter((c) => c.source !== 'blank');
  const head = cols.map((c) => c.label || c.key);
  const body = allRows()
    .filter((r) => !state.deletions.has(String(r.index)))
    .map((r) => cols.map((c) => String(valueOf(r, c.key) ?? '')));
  const csv = [head, ...body]
    .map((row) => row.map((v) => `"${v.replace(/"/g, '""')}"`).join(','))
    .join('\r\n');
  download('﻿' + csv, `instrument_list_reviewed_${state.data.run_id}.csv`, 'text/csv;charset=utf-8');
});

$('btn-export-log').addEventListener('click', () => {
  download(logMarkdown(), `review_log_${state.data.run_id}.md`, 'text/markdown');
});

function logMarkdown() {
  const fb = feedback();
  const L = [`## ${fb.reviewed_at.slice(0, 16).replace('T', ' ')} — ${fb.run_id}`, '',
             `- 검토자: ${fb.reviewer}`,
             `- 대상: ${fb.stats.total_rows}행 (${state.data.xlsx || 'result.json'})`,
             `- 셀 수정 ${fb.stats.cell_corrections} · 오탐 삭제 ${fb.stats.row_deletions} · 누락 추가 ${fb.stats.row_additions}`,
             ''];
  if (fb.cell_corrections.length) {
    L.push('### 셀 수정', '', '| 도면 | 컬럼 | 모델 출력 | 정확한 값 | 유형 | 사유 | 향후 규칙 |',
           '|---|---|---|---|---|---|---|');
    for (const c of fb.cell_corrections) {
      L.push(`| ${c.row_key.pid_no || ''} | ${c.column_label} | ${esc(c.before)} | ${esc(c.after)} | `
           + `${CATEGORY_LABEL[c.category] || c.category} | ${esc(c.reason)} | ${esc(c.rule_comment)} |`);
    }
    L.push('');
  }
  if (fb.row_deletions.length) {
    L.push('### 오탐 (삭제)', '', '| 도면 | TYPE | DESCRIPTION | 사유 | 향후 규칙 |', '|---|---|---|---|---|');
    for (const d of fb.row_deletions) {
      L.push(`| ${d.row_key.pid_no || ''} | ${d.row_key.type || ''} | ${esc(d.row_key.description)} | `
           + `${esc(d.reason)} | ${esc(d.rule_comment)} |`);
    }
    L.push('');
  }
  if (fb.row_additions.length) {
    L.push('### 누락 (추가)', '', '| 도면 | TYPE | DESCRIPTION | 사유 | 향후 규칙 |', '|---|---|---|---|---|');
    for (const a of fb.row_additions) {
      L.push(`| ${a.values.pid_no || ''} | ${a.values.type || ''} | ${esc(a.values.description)} | `
           + `${esc(a.reason)} | ${esc(a.rule_comment)} |`);
    }
    L.push('');
  }
  return L.join('\n');
}

const esc = (s) => String(s ?? '').replace(/\|/g, '\\|').replace(/\n+/g, ' ');

$('btn-clear').addEventListener('click', () => {
  if (!confirm('이 실행에 대한 검토 내용(수정·삭제·추가)을 모두 지웁니다. 계속할까요?')) return;
  state.corrections.clear();
  state.deletions.clear();
  state.additions = [];
  state.seen.clear();
  localStorage.removeItem(LS_KEY(state.data.run_id));
  render();
});

function download(text, filename, mime) {
  const blob = new Blob([text], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

window.addEventListener('beforeunload', (e) => {
  if (state.data && (state.corrections.size || state.deletions.size || state.additions.length)) {
    e.preventDefault();
  }
});
