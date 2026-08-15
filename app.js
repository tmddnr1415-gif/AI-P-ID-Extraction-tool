/* P&ID Instrument Extractor — browser client for the Anthropic Messages API. */
'use strict';

const API_URL = 'https://api.anthropic.com/v1/messages';
const API_VERSION = '2023-06-01';
const MAX_IMAGE_EDGE = 2576;   // 모델이 지원하는 이미지 최대 장변(px)
const REQUEST_SOFT_LIMIT = 28 * 1024 * 1024; // 요청 32MB 제한에 대한 안전 마진

/* ── 기본 출력 포맷 (ISA-5.1 계기 목록) ───────────────────────────── */
const DEFAULT_COLUMNS = [
  { key: 'tag_no',        label: 'Tag No.',        desc: '도면의 계기 버블에 표기된 태그 번호 그대로 (예: PT-1001, FIC-2010A)' },
  { key: 'function',      label: 'Function',       desc: '태그 문자의 의미를 풀어쓴 계기 기능 (예: Pressure Transmitter, Flow Indicating Controller)' },
  { key: 'measured_var',  label: 'Measured Var.',  desc: '측정 변수 (Pressure, Temperature, Flow, Level, Analysis 등)' },
  { key: 'service',       label: 'Service',        desc: '계기가 담당하는 서비스/용도. 도면상 인접 라인·장비 설명에서 판단' },
  { key: 'line_equip',    label: 'Line / Equip.',  desc: '계기가 설치된 라인 번호 또는 장비 번호 (예: 6"-P-1201-A1A, V-101)' },
  { key: 'pid_no',        label: 'P&ID No.',       desc: '해당 계기가 나타난 도면 번호. 타이틀 블록에서 읽되 없으면 "-"' },
  { key: 'loop_type',     label: 'Signal / Loop',  desc: '신호 종류 및 결선 형태 (Electric, Pneumatic, Software link, Capillary 등)' },
  { key: 'location',      label: 'Location',       desc: '설치 위치 구분 (Field mounted, Local panel, DCS/Control room, Behind panel)' },
  { key: 'io_type',       label: 'I/O Type',       desc: '제어시스템 I/O 유형 추정 (AI, AO, DI, DO, None)' },
  { key: 'remarks',       label: 'Remarks',        desc: '인터록/알람/SIL/판독 불확실 등 특기 사항. 없으면 "-"' },
];

const SEVERITIES = ['high', 'medium', 'low'];

/* ── 상태 ─────────────────────────────────────────────────────────── */
const state = {
  files: [],        // { id, name, kind: 'image'|'pdf', mediaType, base64, bytes, previewUrl }
  columns: structuredClone(DEFAULT_COLUMNS),
  result: null,
  settings: {
    apiKey: '',
    model: 'claude-opus-5',
    effort: 'high',
    maxTokens: 32000,
    downscale: true,
  },
  controller: null,
};

const $ = (id) => document.getElementById(id);
const els = {};
['btn-settings', 'settings', 'api-key', 'model', 'effort', 'max-tokens', 'downscale',
 'dropzone', 'file-input', 'file-list', 'size-warn',
 'cols-body', 'btn-add-col', 'btn-reset-col',
 'instructions', 'btn-run', 'btn-cancel', 'status', 'error',
 'results', 'summary', 'result-head', 'result-body', 'filter',
 'findings', 'findings-count', 'findings-wrap', 'raw-json',
 'btn-csv', 'btn-tsv', 'btn-json'].forEach((id) => {
  els[id.replace(/-(\w)/g, (_, c) => c.toUpperCase())] = $(id);
});

/* ── 설정 저장/복원 ───────────────────────────────────────────────── */
function loadPersisted() {
  try {
    const s = JSON.parse(localStorage.getItem('pid.settings') || '{}');
    Object.assign(state.settings, s);
  } catch { /* 손상된 값은 무시하고 기본값 사용 */ }
  try {
    const c = JSON.parse(localStorage.getItem('pid.columns') || 'null');
    if (Array.isArray(c) && c.length) state.columns = c;
  } catch { /* 기본 컬럼 사용 */ }
}

function persistSettings() {
  localStorage.setItem('pid.settings', JSON.stringify(state.settings));
}
function persistColumns() {
  localStorage.setItem('pid.columns', JSON.stringify(state.columns));
}

function syncSettingsForm() {
  els.apiKey.value = state.settings.apiKey;
  els.model.value = state.settings.model;
  els.effort.value = state.settings.effort;
  els.maxTokens.value = state.settings.maxTokens;
  els.downscale.checked = state.settings.downscale;
}

els.btnSettings.addEventListener('click', () => { syncSettingsForm(); els.settings.showModal(); });
els.settings.addEventListener('close', () => {
  if (els.settings.returnValue !== 'save') return;
  state.settings.apiKey = els.apiKey.value.trim();
  state.settings.model = els.model.value;
  state.settings.effort = els.effort.value;
  state.settings.maxTokens = Math.max(4096, Math.min(128000, Number(els.maxTokens.value) || 32000));
  state.settings.downscale = els.downscale.checked;
  persistSettings();
});

/* ── 파일 업로드 ──────────────────────────────────────────────────── */
els.dropzone.addEventListener('click', () => els.fileInput.click());
els.fileInput.addEventListener('change', (e) => { addFiles(e.target.files); els.fileInput.value = ''; });

['dragenter', 'dragover'].forEach((ev) =>
  els.dropzone.addEventListener(ev, (e) => { e.preventDefault(); els.dropzone.classList.add('over'); }));
['dragleave', 'drop'].forEach((ev) =>
  els.dropzone.addEventListener(ev, (e) => { e.preventDefault(); els.dropzone.classList.remove('over'); }));
els.dropzone.addEventListener('drop', (e) => addFiles(e.dataTransfer.files));

async function addFiles(fileList) {
  for (const file of Array.from(fileList || [])) {
    const isPdf = file.type === 'application/pdf';
    const isImage = file.type.startsWith('image/');
    if (!isPdf && !isImage) {
      showError(`지원하지 않는 파일 형식입니다: ${file.name} (${file.type || '알 수 없음'})`);
      continue;
    }
    try {
      const entry = isPdf ? await readPdf(file) : await readImage(file);
      state.files.push(entry);
    } catch (err) {
      showError(`${file.name} 을(를) 읽지 못했습니다: ${err.message}`);
    }
  }
  renderFiles();
}

function readAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(r.result);
    r.onerror = () => reject(new Error('파일 읽기 실패'));
    r.readAsDataURL(file);
  });
}

async function readPdf(file) {
  const dataUrl = await readAsDataUrl(file);
  const base64 = dataUrl.split(',')[1];
  return {
    id: crypto.randomUUID(), name: file.name, kind: 'pdf',
    mediaType: 'application/pdf', base64, bytes: base64.length * 0.75, previewUrl: null,
  };
}

async function readImage(file) {
  const dataUrl = await readAsDataUrl(file);
  const img = await new Promise((resolve, reject) => {
    const i = new Image();
    i.onload = () => resolve(i);
    i.onerror = () => reject(new Error('이미지 디코딩 실패'));
    i.src = dataUrl;
  });

  const longEdge = Math.max(img.naturalWidth, img.naturalHeight);
  let mediaType = file.type;
  let base64 = dataUrl.split(',')[1];

  // 장변이 모델 최대 해상도를 넘으면 축소한다. 넘지 않으면 원본을 그대로 보낸다
  // (재인코딩은 도면의 얇은 선을 뭉개기 때문).
  if (state.settings.downscale && longEdge > MAX_IMAGE_EDGE) {
    const scale = MAX_IMAGE_EDGE / longEdge;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.naturalWidth * scale);
    canvas.height = Math.round(img.naturalHeight * scale);
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
    base64 = canvas.toDataURL('image/png').split(',')[1];
    mediaType = 'image/png';
  }

  return {
    id: crypto.randomUUID(), name: file.name, kind: 'image', mediaType, base64,
    bytes: base64.length * 0.75, previewUrl: dataUrl,
    dims: `${img.naturalWidth}×${img.naturalHeight}`,
  };
}

function renderFiles() {
  els.fileList.innerHTML = '';
  for (const f of state.files) {
    const li = document.createElement('li');

    if (f.previewUrl) {
      const img = document.createElement('img');
      img.className = 'thumb';
      img.src = f.previewUrl;
      img.alt = '';
      li.append(img);
    } else {
      const box = document.createElement('span');
      box.className = 'thumb pdf';
      box.textContent = 'PDF';
      li.append(box);
    }

    const name = document.createElement('span');
    name.className = 'name';
    name.textContent = f.name;

    const meta = document.createElement('span');
    meta.className = 'meta';
    meta.textContent = [f.dims, formatBytes(f.bytes)].filter(Boolean).join(' · ');

    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'ghost';
    del.textContent = '삭제';
    del.addEventListener('click', () => {
      state.files = state.files.filter((x) => x.id !== f.id);
      renderFiles();
    });

    li.append(name, meta, del);
    els.fileList.append(li);
  }
  checkSize();
}

function checkSize() {
  const total = state.files.reduce((n, f) => n + f.bytes, 0);
  if (total > REQUEST_SOFT_LIMIT) {
    els.sizeWarn.textContent =
      `업로드 총 용량이 ${formatBytes(total)} 입니다. 요청 크기 한도(32MB)에 가까우니 도면을 나눠서 실행하세요.`;
    els.sizeWarn.classList.remove('hidden');
  } else {
    els.sizeWarn.classList.add('hidden');
  }
}

const formatBytes = (n) => n > 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.round(n / 1024)} KB`;

/* ── 컬럼(출력 포맷) 편집 ─────────────────────────────────────────── */
function renderColumns() {
  els.colsBody.innerHTML = '';
  state.columns.forEach((col, i) => {
    const tr = document.createElement('tr');
    tr.append(
      colCell(col, 'key', i, 'tag_no'),
      colCell(col, 'label', i, 'Tag No.'),
      colCell(col, 'desc', i, '이 컬럼에 무엇을 채울지 모델에게 설명'),
    );

    const tdDel = document.createElement('td');
    const del = document.createElement('button');
    del.type = 'button';
    del.className = 'ghost';
    del.textContent = '✕';
    del.title = '컬럼 삭제';
    del.addEventListener('click', () => {
      if (state.columns.length <= 1) return;
      state.columns.splice(i, 1);
      persistColumns();
      renderColumns();
    });
    tdDel.append(del);
    tr.append(tdDel);

    els.colsBody.append(tr);
  });
}

function colCell(col, field, index, placeholder) {
  const td = document.createElement('td');
  const input = document.createElement('input');
  input.type = 'text';
  input.value = col[field];
  input.placeholder = placeholder;
  input.addEventListener('change', () => {
    state.columns[index][field] = input.value.trim();
    persistColumns();
  });
  td.append(input);
  return td;
}

els.btnAddCol.addEventListener('click', () => {
  state.columns.push({ key: `field_${state.columns.length + 1}`, label: '새 컬럼', desc: '' });
  persistColumns();
  renderColumns();
});

els.btnResetCol.addEventListener('click', () => {
  state.columns = structuredClone(DEFAULT_COLUMNS);
  persistColumns();
  renderColumns();
});

/* ── 구조화 출력 스키마 생성 ──────────────────────────────────────── */
function validateColumns() {
  const seen = new Set();
  for (const col of state.columns) {
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(col.key)) {
      throw new Error(`컬럼 키 "${col.key}" 는 영문자/숫자/밑줄만 사용할 수 있고 숫자로 시작할 수 없습니다.`);
    }
    if (seen.has(col.key)) throw new Error(`컬럼 키 "${col.key}" 가 중복되었습니다.`);
    seen.add(col.key);
  }
}

function buildSchema() {
  const properties = {};
  for (const col of state.columns) {
    properties[col.key] = {
      type: 'string',
      description: `${col.label}. ${col.desc || ''} 도면에서 확인할 수 없으면 "-" 로 채운다.`.trim(),
    };
  }
  return {
    type: 'object',
    properties: {
      instruments: {
        type: 'array',
        description: '도면에서 식별한 모든 계기. 도면상 위치 순서(좌→우, 상→하)로 나열한다.',
        items: {
          type: 'object',
          properties,
          required: state.columns.map((c) => c.key),
          additionalProperties: false,
        },
      },
      review_findings: {
        type: 'array',
        description: '태그 누락·중복, 번호 체계 불일치, ISA-5.1 위반, 판독 불가 영역 등 검토 의견.',
        items: {
          type: 'object',
          properties: {
            severity: { type: 'string', enum: SEVERITIES, description: '영향도' },
            location: { type: 'string', description: '해당 태그 번호 또는 도면상 위치' },
            finding: { type: 'string', description: '무엇이 문제인지 한 문장' },
            recommendation: { type: 'string', description: '권고 조치' },
          },
          required: ['severity', 'location', 'finding', 'recommendation'],
          additionalProperties: false,
        },
      },
      summary: { type: 'string', description: '도면 범위와 추출 결과를 2~3문장으로 요약.' },
    },
    required: ['instruments', 'review_findings', 'summary'],
    additionalProperties: false,
  };
}

/* ── 프롬프트 ─────────────────────────────────────────────────────── */
const SYSTEM_PROMPT = `당신은 ISA-5.1 표준에 따라 P&ID를 판독하는 계장 엔지니어입니다.

작업:
1. 도면에 그려진 모든 계기 버블(원형/사각 심볼)과 인라인 계기를 빠짐없이 찾아 계기 목록으로 정리한다.
2. 태그 문자는 ISA-5.1로 해석한다 (첫 문자 = 측정 변수, 뒤 문자 = 기능. 예: PT=Pressure Transmitter, FIC=Flow Indicating Controller, LSHH=Level Switch High High).
3. 버블 테두리로 설치 위치를 판단한다 (실선 없음/한 줄=Field, 가로선 1개=제어실 패널, 점선=Behind panel, 육각형/사각형=DCS·PLC 등 공유 표시).
4. 신호선 형태로 신호 종류를 판단한다 (실선=배선, 빗금=공압, 점선=전기, 원 연결선=소프트웨어 링크).
5. 판독하면서 발견한 문제(태그 중복·누락, 번호 체계 불일치, 심볼과 태그 불일치, 해상도 때문에 판독 불가한 영역)는 검토 의견으로 남긴다.

원칙:
- 도면에 실제로 보이는 것만 기재한다. 추론한 값은 비고에 근거를 밝히고, 확인 불가하면 "-" 로 둔다. 없는 계기를 만들어내지 않는다.
- 태그 번호는 도면 표기 그대로 옮긴다 (접미사 A/B, 하이픈, 접두 유닛 번호 포함).
- 같은 태그가 여러 도면에 반복되면 한 행으로 합치고 비고에 중복 도면을 적는다.
- 도면이 흐리거나 잘려 판독이 어려우면 추측하지 말고 검토 의견에 해당 영역을 보고한다.`;

function buildUserText(instructions) {
  const cols = state.columns.map((c) => `- ${c.key} (${c.label}): ${c.desc}`).join('\n');
  const extra = instructions ? `\n\n[추가 지시사항]\n${instructions}` : '';
  return `첨부한 P&ID 도면 ${state.files.length}건을 검토하고 계기 목록을 추출해 주세요.

출력할 컬럼 정의:
${cols}${extra}`;
}

/* ── API 호출 ─────────────────────────────────────────────────────── */
els.btnRun.addEventListener('click', run);
els.btnCancel.addEventListener('click', () => state.controller?.abort());

async function run() {
  clearError();

  if (!state.settings.apiKey) {
    showError('API Key가 없습니다. 우측 상단 ⚙ 설정에서 Anthropic API Key를 입력하세요.');
    return;
  }
  if (!state.files.length) {
    showError('검토할 도면을 먼저 업로드하세요.');
    return;
  }

  try {
    validateColumns();
  } catch (err) {
    showError(err.message);
    return;
  }

  const content = state.files.map((f) => (
    f.kind === 'pdf'
      ? { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: f.base64 } }
      : { type: 'image', source: { type: 'base64', media_type: f.mediaType, data: f.base64 } }
  ));
  content.push({ type: 'text', text: buildUserText(els.instructions.value.trim()) });

  const body = {
    model: state.settings.model,
    max_tokens: state.settings.maxTokens,
    stream: true,
    thinking: { type: 'adaptive' },
    system: [{ type: 'text', text: SYSTEM_PROMPT, cache_control: { type: 'ephemeral' } }],
    output_config: {
      effort: state.settings.effort,
      format: { type: 'json_schema', schema: buildSchema() },
    },
    messages: [{ role: 'user', content }],
  };

  setBusy(true, '도면 전송 중…');
  state.controller = new AbortController();

  try {
    const res = await fetch(API_URL, {
      method: 'POST',
      signal: state.controller.signal,
      headers: {
        'content-type': 'application/json',
        'x-api-key': state.settings.apiKey,
        'anthropic-version': API_VERSION,
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) throw new Error(await describeHttpError(res));

    const { text, usage, stopReason } = await consumeStream(res, state.controller.signal);

    if (stopReason === 'refusal') {
      throw new Error('모델이 이 요청을 거절했습니다(stop_reason: refusal). 도면 내용이나 지시사항을 확인해 주세요.');
    }
    if (stopReason === 'max_tokens') {
      throw new Error('최대 출력 토큰에 도달해 응답이 잘렸습니다. 설정에서 최대 출력 토큰을 늘리거나 도면을 나눠 실행하세요.');
    }

    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch {
      throw new Error(`응답을 JSON으로 해석하지 못했습니다.\n\n${text.slice(0, 500)}`);
    }

    state.result = parsed;
    renderResults(parsed, usage);
    setBusy(false, `완료 · 계기 ${parsed.instruments.length}건 · 검토 의견 ${parsed.review_findings.length}건`);
  } catch (err) {
    if (err.name === 'AbortError') {
      setBusy(false, '사용자가 중지했습니다.');
    } else {
      setBusy(false, '');
      showError(err.message);
    }
  } finally {
    state.controller = null;
  }
}

async function describeHttpError(res) {
  let detail = '';
  try {
    const j = await res.json();
    detail = j?.error?.message || JSON.stringify(j);
  } catch {
    detail = await res.text().catch(() => '');
  }
  const hints = {
    401: 'API Key를 확인하세요.',
    403: '이 API Key에 해당 모델 권한이 없을 수 있습니다.',
    404: '모델 ID를 확인하세요.',
    413: '요청이 너무 큽니다. 도면 수를 줄이거나 이미지 축소 옵션을 켜세요.',
    429: '요청 한도에 걸렸습니다. 잠시 후 다시 시도하세요.',
    529: 'API가 일시적으로 과부하 상태입니다. 잠시 후 다시 시도하세요.',
  };
  return `HTTP ${res.status} — ${detail}${hints[res.status] ? `\n\n${hints[res.status]}` : ''}`;
}

/* SSE 스트림을 읽어 텍스트 블록만 누적한다. */
async function consumeStream(res, signal) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  const textBlocks = new Set();   // 텍스트인 content block 인덱스
  let buffer = '';
  let text = '';
  let usage = null;
  let stopReason = null;

  while (true) {
    if (signal.aborted) { await reader.cancel(); throw new DOMException('aborted', 'AbortError'); }
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep;
    while ((sep = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);

      const line = chunk.split('\n').find((l) => l.startsWith('data:'));
      if (!line) continue;

      let ev;
      try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }

      switch (ev.type) {
        case 'content_block_start':
          if (ev.content_block?.type === 'text') textBlocks.add(ev.index);
          else if (ev.content_block?.type === 'thinking') setBusy(true, '도면 판독 중…');
          break;
        case 'content_block_delta':
          if (ev.delta?.type === 'text_delta' && textBlocks.has(ev.index)) {
            text += ev.delta.text;
            setBusy(true, `계기 목록 생성 중… (${text.length.toLocaleString()}자)`);
          }
          break;
        case 'message_delta':
          if (ev.delta?.stop_reason) stopReason = ev.delta.stop_reason;
          if (ev.usage) usage = { ...(usage || {}), ...ev.usage };
          break;
        case 'message_start':
          if (ev.message?.usage) usage = { ...ev.message.usage };
          break;
        case 'error':
          throw new Error(ev.error?.message || '스트리밍 중 오류가 발생했습니다.');
      }
    }
  }
  return { text, usage, stopReason };
}

/* ── 결과 렌더링 ──────────────────────────────────────────────────── */
function renderResults(data, usage) {
  els.results.classList.remove('hidden');

  const inTok = (usage?.input_tokens || 0) + (usage?.cache_read_input_tokens || 0) + (usage?.cache_creation_input_tokens || 0);
  const tok = usage ? ` · 토큰 입력 ${inTok.toLocaleString()} / 출력 ${(usage.output_tokens || 0).toLocaleString()}` : '';
  els.summary.textContent = `${data.summary}${tok}`;

  els.resultHead.innerHTML = '';
  const thIdx = document.createElement('th');
  thIdx.textContent = '#';
  els.resultHead.append(thIdx);
  for (const col of state.columns) {
    const th = document.createElement('th');
    th.textContent = col.label || col.key;
    els.resultHead.append(th);
  }

  renderRows(data.instruments);

  els.findings.innerHTML = '';
  els.findingsCount.textContent = String(data.review_findings.length);
  for (const f of data.review_findings) {
    const li = document.createElement('li');
    const badge = document.createElement('span');
    badge.className = `sev sev-${SEVERITIES.includes(f.severity) ? f.severity : 'low'}`;
    badge.textContent = f.severity;
    const body = document.createElement('span');
    body.textContent = `[${f.location}] ${f.finding} → ${f.recommendation}`;
    li.append(badge, body);
    els.findings.append(li);
  }
  els.findingsWrap.open = data.review_findings.some((f) => f.severity === 'high');

  els.rawJson.textContent = JSON.stringify(data, null, 2);
  els.results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderRows(rows) {
  els.resultBody.innerHTML = '';
  rows.forEach((row, i) => {
    const tr = document.createElement('tr');
    const td0 = document.createElement('td');
    td0.className = 'idx';
    td0.textContent = String(i + 1);
    tr.append(td0);
    for (const col of state.columns) {
      const td = document.createElement('td');
      td.textContent = row[col.key] ?? '-';
      tr.append(td);
    }
    els.resultBody.append(tr);
  });
}

els.filter.addEventListener('input', () => {
  if (!state.result) return;
  const q = els.filter.value.trim().toLowerCase();
  const rows = q
    ? state.result.instruments.filter((r) =>
        state.columns.some((c) => String(r[c.key] ?? '').toLowerCase().includes(q)))
    : state.result.instruments;
  renderRows(rows);
});

/* ── 내보내기 ─────────────────────────────────────────────────────── */
function tableRows() {
  const head = state.columns.map((c) => c.label || c.key);
  const body = state.result.instruments.map((r) => state.columns.map((c) => String(r[c.key] ?? '-')));
  return [head, ...body];
}

els.btnCsv.addEventListener('click', () => {
  if (!state.result) return;
  const csv = tableRows()
    .map((row) => row.map((v) => `"${v.replace(/"/g, '""')}"`).join(','))
    .join('\r\n');
  // Excel이 한글을 UTF-8로 인식하도록 BOM을 붙인다.
  download(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }), 'instrument_list.csv');
});

els.btnJson.addEventListener('click', () => {
  if (!state.result) return;
  download(new Blob([JSON.stringify(state.result, null, 2)], { type: 'application/json' }), 'pid_review.json');
});

els.btnTsv.addEventListener('click', async () => {
  if (!state.result) return;
  const tsv = tableRows().map((row) => row.map((v) => v.replace(/[\t\n\r]+/g, ' ')).join('\t')).join('\n');
  try {
    await navigator.clipboard.writeText(tsv);
    setBusy(false, '엑셀에 붙여넣을 수 있도록 복사했습니다.');
  } catch {
    showError('클립보드 복사에 실패했습니다. CSV 저장을 사용하세요.');
  }
});

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/* ── UI 헬퍼 ──────────────────────────────────────────────────────── */
function setBusy(busy, message) {
  els.btnRun.disabled = busy;
  els.btnCancel.classList.toggle('hidden', !busy);
  els.status.textContent = message;
  els.status.classList.toggle('busy', busy);
}

function showError(message) {
  els.error.textContent = message;
  els.error.classList.remove('hidden');
}
function clearError() {
  els.error.classList.add('hidden');
  els.error.textContent = '';
}

/* ── 초기화 ───────────────────────────────────────────────────────── */
loadPersisted();
syncSettingsForm();
renderColumns();
if (!state.settings.apiKey) {
  setBusy(false, 'API Key를 설정하면 검토를 실행할 수 있습니다.');
}
