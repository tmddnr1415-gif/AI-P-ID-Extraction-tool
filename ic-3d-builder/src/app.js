/* 앱 — 품목 선택, 도면 판독, 파라미터 폼, 뷰어 연결. */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const SRC_LABEL = { drawing: '도면', user: '입력', standard: '표준', estimate: '추정', default: '기본', none: '없음' };

  const store = {
    get(k, d) { try { const v = localStorage.getItem(`ic3d.${k}`); return v == null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(`ic3d.${k}`, v); } catch { /* 저장 불가 환경 */ } },
  };

  const S = {
    presetId: store.get('preset', 'cv_globe'),
    type: 'valve',
    inputs: {},
    files: [],
    extraction: null,
    model: null,
    abort: null,
  };

  // ───────── 품목 ─────────
  function initPresets() {
    const sel = $('preset');
    const groups = { valve: '밸브', cabinet: '캐비닛', hookup: '계기 훅업' };
    for (const [t, name] of Object.entries(groups)) {
      const og = document.createElement('optgroup'); og.label = name;
      for (const p of Anatomy.PRESETS.filter((x) => x.type === t)) {
        const o = document.createElement('option'); o.value = p.id; o.textContent = p.label; og.appendChild(o);
      }
      sel.appendChild(og);
    }
    if (!Anatomy.PRESETS.some((p) => p.id === S.presetId)) S.presetId = 'cv_globe';
    sel.value = S.presetId;
    sel.addEventListener('change', () => applyPreset(sel.value, true));
  }

  function applyPreset(id, resetInputs) {
    const p = Anatomy.PRESETS.find((x) => x.id === id) || Anatomy.PRESETS[0];
    const typeChanged = p.type !== S.type;
    S.presetId = p.id; S.type = p.type; store.set('preset', p.id);
    if (resetInputs) {
      S.inputs = {};
      for (const [k, v] of Object.entries(p.set)) S.inputs[k] = { value: v, src: 'default' };
    }
    $('preset-note').textContent = `${Anatomy.TYPES[p.type].label} · 프리셋은 구성만 정합니다. 치수는 도면 → 입력 → 표준표 → 추정 순서로 결정됩니다.`;
    rebuild({ refit: typeChanged || resetInputs });
  }

  // ───────── 폼 ─────────
  function renderForm() {
    const T = Anatomy.TYPES[S.type];
    const { values, meta } = S.model;
    const form = $('form'); form.innerHTML = '';
    let grp = null;
    for (const p of T.params) {
      if (p.group !== grp) {
        grp = p.group;
        const g = document.createElement('div'); g.className = 'grp'; g.textContent = grp; form.appendChild(g);
      }
      const m = meta[p.key] || {};
      const row = document.createElement('div');
      row.className = 'prm' + (m.active ? '' : ' inactive');
      const id = `p-${p.key}`;
      const lab = document.createElement('label'); lab.htmlFor = id; lab.textContent = p.label;
      if (p.desc) lab.title = p.desc;
      let input;
      if (p.type === 'enum') {
        input = document.createElement('select');
        for (const o of p.options) { const op = document.createElement('option'); op.value = o; op.textContent = o; input.appendChild(op); }
        input.value = String(values[p.key] ?? '');
      } else if (p.type === 'bool') {
        input = document.createElement('input'); input.type = 'checkbox'; input.checked = !!values[p.key];
      } else {
        input = document.createElement('input');
        input.type = p.type === 'num' ? 'number' : 'text';
        if (p.step) input.step = p.step; else if (p.type === 'num') input.step = 'any';
        if (p.min != null) input.min = p.min; if (p.max != null) input.max = p.max;
        const v = values[p.key];
        input.value = v == null || Number.isNaN(v) ? '' : (p.type === 'num' ? +(+v).toFixed(2) : v);
      }
      input.id = id;
      input.addEventListener('change', () => {
        let val;
        if (p.type === 'bool') val = input.checked;
        else val = input.value;
        if (val === '' && p.type !== 'bool') delete S.inputs[p.key];
        else S.inputs[p.key] = { value: val, src: 'user' };
        rebuild({});
      });
      const badge = document.createElement('span');
      badge.className = `src src-${m.src || 'none'}`;
      badge.textContent = (p.unit ? p.unit + ' ' : '') + (SRC_LABEL[m.src] || '');
      badge.title = [m.ref, m.evidence, m.confidence && `확신도 ${m.confidence}`].filter(Boolean).join('\n') || SRC_LABEL[m.src] || '';
      if (m.src && m.src !== 'default') {
        badge.style.cursor = 'pointer';
        badge.title += '\n(클릭: 이 값 지우고 표준/추정으로 되돌리기)';
        badge.addEventListener('click', () => { delete S.inputs[p.key]; rebuild({}); });
      }
      row.append(lab, input, badge);
      if (m.src === 'drawing' && m.evidence) {
        const ev = document.createElement('div'); ev.className = 'ev'; ev.textContent = `↳ ${m.evidence}${m.confidence ? ` (${m.confidence})` : ''}`;
        row.appendChild(ev);
      } else if (m.ref && m.active) {
        const ev = document.createElement('div'); ev.className = 'ev'; ev.textContent = `↳ ${m.ref}`;
        row.appendChild(ev);
      }
      form.appendChild(row);
    }
  }

  // ───────── 빌드 ─────────
  /** 도면/입력으로 바디·조작기가 바뀌면 프리셋 표시와 프리셋 기본값(src 'default')을 맞춘다 */
  function syncPreset() {
    if (S.type !== 'valve') return;
    const val = (k) => S.inputs[k]?.value;
    const cur = Anatomy.PRESETS.find((p) => p.id === S.presetId);
    if (cur && cur.set.body === val('body') && cur.set.operator === val('operator')) return;
    const p = Anatomy.PRESETS.find((x) => x.type === 'valve' && x.set.body === val('body') && x.set.operator === val('operator'));
    if (!p) return;
    S.presetId = p.id; $('preset').value = p.id; store.set('preset', p.id);
    for (const [k, v] of Object.entries(p.set)) if (!S.inputs[k] || S.inputs[k].src === 'default') S.inputs[k] = { value: v, src: 'default' };
  }

  function rebuild({ refit }) {
    syncPreset();
    try {
      S.model = Anatomy.build({ type: S.type, inputs: S.inputs });
    } catch (e) {
      console.error(e);
      setStatus(`모델 생성 실패: ${e.message}`, true);
      return;
    }
    renderForm();
    if (window.THREE) Viewer.show(S.model, { keepView: !refit });
    if (refit && window.THREE) { Viewer.setView('iso', true); Viewer.fit(); }
    renderParts();
    renderSummary();
  }

  function renderParts() {
    const ul = $('parts'); ul.innerHTML = '';
    const parts = S.model.parts;
    $('parts-count').textContent = `${parts.length}개 부품`;
    for (const p of parts) {
      const li = document.createElement('li'); li.dataset.id = p.id;
      const cb = document.createElement('input'); cb.type = 'checkbox'; cb.checked = true; cb.title = '표시';
      cb.addEventListener('click', (e) => { e.stopPropagation(); Viewer.setVisible(p.id, cb.checked); });
      const sw = document.createElement('span'); sw.className = 'sw'; sw.style.background = Viewer.matColor(p.mat);
      if (['ghost', 'clear'].includes(p.mat)) sw.style.opacity = '0.4';
      const t = document.createElement('span'); t.textContent = p.label; t.title = p.desc || '';
      li.append(cb, sw, t);
      li.addEventListener('click', () => selectPart(p.id));
      ul.appendChild(li);
    }
  }

  function selectPart(id) {
    Viewer.select(id);
    for (const li of $('parts').children) li.classList.toggle('sel', li.dataset.id === id);
  }

  function renderSummary() {
    const { values, meta, bbox } = S.model;
    const cnt = {};
    for (const m of Object.values(meta)) if (m.active) cnt[m.src] = (cnt[m.src] || 0) + 1;
    const rows = [
      ['품목', Anatomy.PRESETS.find((p) => p.id === S.presetId)?.label || S.type],
      ['Tag', values.tag || '-'],
      ['외곽 (L × W × H)', bbox && isFinite(bbox.size[0]) ? bbox.size.map((v) => Math.round(v)).join(' × ') + ' mm' : '-'],
      ['치수 출처', ['drawing', 'user', 'standard', 'estimate', 'default'].filter((k) => cnt[k]).map((k) => `${SRC_LABEL[k]} ${cnt[k]}`).join(' · ')],
    ];
    if (S.extraction?.title_block) {
      const tb = S.extraction.title_block;
      rows.push(['도면', [tb.dwg_no, tb.rev && `Rev.${tb.rev}`].filter(Boolean).join(' ') || '-']);
      rows.push(['벤더/모델', [tb.vendor, tb.model_no].filter(Boolean).join(' / ') || '-']);
    }
    const tbl = rows.map(([k, v]) => `<tr><td class="muted">${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
    const warn = cnt.estimate
      ? `<p class="small" style="color:var(--s-estimate)">추정 치수 ${cnt.estimate}개 — 형상 참고용입니다. 도면값으로 확인되기 전에는 간섭 검토 결론에 쓰지 마세요.</p>` : '';
    const std = cnt.standard
      ? `<p class="small muted">표준 치수는 내장 참고표(검증 전) 값입니다. 벤더 도면이 우선입니다.</p>` : '';
    const chk = (S.model.warnings || []).map((w) => `<p class="small sev-high">⚠ ${esc(w)}</p>`).join('');
    $('summary').innerHTML = `<table class="kv">${tbl}</table>${chk}${warn}${std}`;
  }

  // ───────── 파일 / 판독 ─────────
  function initFiles() {
    const drop = $('drop'); const file = $('file');
    drop.addEventListener('click', () => file.click());
    drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') file.click(); });
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => { e.preventDefault(); drop.classList.remove('over'); addFiles(e.dataTransfer.files); });
    file.addEventListener('change', () => { addFiles(file.files); file.value = ''; });
  }

  function addFiles(list) {
    for (const f of list) {
      if (!(f.type === 'application/pdf' || f.type.startsWith('image/'))) continue;
      if (f.size > 30 * 1024 * 1024) { setStatus(`${f.name}: 30MB 초과`, true); continue; }
      S.files.push(f);
    }
    renderFiles();
  }

  function renderFiles() {
    const ul = $('files'); ul.innerHTML = '';
    S.files.forEach((f, i) => {
      const li = document.createElement('li');
      const left = document.createElement('div');
      left.textContent = `${f.type === 'application/pdf' ? '📄' : '🖼'} ${f.name} · ${(f.size / 1024).toFixed(0)} KB`;
      if (f.type.startsWith('image/')) {
        const img = document.createElement('img'); img.src = URL.createObjectURL(f); img.alt = f.name; left.appendChild(img);
      }
      const rm = document.createElement('button'); rm.textContent = '✕'; rm.title = '빼기';
      rm.addEventListener('click', () => { S.files.splice(i, 1); renderFiles(); });
      li.append(left, rm); ul.appendChild(li);
    });
  }

  async function runExtract() {
    const btn = $('btn-extract'); const cancel = $('btn-cancel');
    btn.disabled = true; cancel.hidden = false;
    S.abort = new AbortController();
    const t0 = Date.now();
    setStatus('도면을 보내는 중…');
    try {
      const { data, usage } = await Extract.run({
        apiKey: store.get('key', ''), model: store.get('model', 'claude-opus-5-5'), effort: store.get('effort', 'high'),
        files: S.files, typeHint: S.type, hint: $('hint').value.trim(), signal: S.abort.signal,
        onProgress: (n) => setStatus(`판독 중… 응답 ${n.toLocaleString()}자 · ${((Date.now() - t0) / 1000).toFixed(0)}s`),
      });
      S.extraction = data;
      // 품목 분류가 다르면 그 분류의 첫 프리셋으로 바꾸고 구성값은 도면 것을 쓴다
      if (data.item_type && data.item_type !== S.type) {
        const p = Anatomy.PRESETS.find((x) => x.type === data.item_type);
        if (p) { $('preset').value = p.id; applyPreset(p.id, true); }
      }
      const { inputs, dropped } = Extract.toInputs(data, S.type);
      // 도면값이 사람이 손댄 값보다 우선하지 않도록: user 값은 남긴다
      for (const [k, v] of Object.entries(inputs)) if (S.inputs[k]?.src !== 'user') S.inputs[k] = v;
      rebuild({ refit: true });
      renderFindings(data, dropped);
      const n = Object.keys(inputs).length;
      setStatus(`완료 — 도면에서 ${n}개 값을 읽었습니다. (${((Date.now() - t0) / 1000).toFixed(0)}s, 입력 ${usage?.input_tokens ?? '?'} / 출력 ${usage?.output_tokens ?? '?'} 토큰)`);
    } catch (e) {
      if (e.name === 'AbortError') setStatus('중지했습니다.');
      else setStatus(e.message, true);
    } finally {
      btn.disabled = false; cancel.hidden = true; S.abort = null;
    }
  }

  function renderFindings(data, dropped) {
    const box = $('findings'); box.innerHTML = '';
    $('findings-card').hidden = false;
    const add = (html) => { const d = document.createElement('div'); d.className = 'find'; d.innerHTML = html; box.appendChild(d); };
    if (data.summary) add(esc(data.summary));
    if (data.size_row && data.size_row !== '-') add(`<b>사용한 치수표 행:</b> ${esc(data.size_row)}`);
    for (const f of data.review_findings || []) add(`<span class="sev-${f.severity}">[${f.severity}]</span> ${esc(f.finding)}`);
    if (data.unmapped_dimensions?.length) add(`<b>3D에 반영하지 않은 치수:</b> ${data.unmapped_dimensions.map(esc).join(', ')}`);
    if (dropped?.length) add(`<b>사전에 없는 key (무시):</b> ${dropped.map(esc).join(', ')}`);
  }

  function setStatus(msg, err) { const s = $('status'); s.textContent = msg; s.classList.toggle('err', !!err); }
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // ───────── 내보내기 / 불러오기 ─────────
  function fileBase() {
    const tag = (S.model.values.tag || S.presetId).replace(/[^\w.-]+/g, '_');
    return `${tag}_3d`;
  }
  function download(blob, name) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function specJSON() {
    const { values, meta, bbox } = S.model;
    return {
      tool: 'ic-3d-builder', version: 1,
      type: S.type, preset: S.presetId,
      inputs: S.inputs,
      resolved: Object.fromEntries(Object.entries(values).map(([k, v]) => [k, { value: v, ...meta[k] }])),
      bbox_mm: bbox,
      extraction: S.extraction,
      note: '출처 drawing/user 외의 값은 표준 참고표 또는 비례 추정입니다. 제작·구매 치수로 쓰지 마세요.',
    };
  }

  function loadSpec(obj) {
    if (!obj || !Anatomy.TYPES[obj.type]) throw new Error('type 이 valve / cabinet / hookup 중 하나여야 합니다.');
    const preset = Anatomy.PRESETS.find((p) => p.id === obj.preset) || Anatomy.PRESETS.find((p) => p.type === obj.type);
    S.presetId = preset.id; S.type = obj.type; $('preset').value = preset.id;
    S.inputs = {};
    for (const [k, v] of Object.entries(obj.inputs || {})) {
      S.inputs[k] = (v && typeof v === 'object' && 'value' in v) ? v : { value: v, src: 'user' };
    }
    S.extraction = obj.extraction || null;
    applyPreset(preset.id, false);
    if (S.extraction) renderFindings(S.extraction, []);
  }

  function initToolbar() {
    for (const b of document.querySelectorAll('[data-view]')) b.addEventListener('click', () => Viewer.setView(b.dataset.view));
    $('explode').addEventListener('input', (e) => Viewer.setExplode(+e.target.value));
    $('opt-labels').addEventListener('change', (e) => Viewer.setLabels(e.target.checked));
    $('opt-dims').addEventListener('change', (e) => Viewer.setDims(e.target.checked));
    $('opt-edges').addEventListener('change', (e) => Viewer.setEdges(e.target.checked));
    $('ex-stl').addEventListener('click', () => download(Viewer.toSTL(), `${fileBase()}.stl`));
    $('ex-obj').addEventListener('click', () => download(Viewer.toOBJ(fileBase()), `${fileBase()}.obj`));
    $('ex-png').addEventListener('click', async () => download(await (await fetch(Viewer.toPNG())).blob(), `${fileBase()}.png`));
    $('ex-json').addEventListener('click', () => download(new Blob([JSON.stringify(specJSON(), null, 2)], { type: 'application/json' }), `${fileBase()}.json`));
    $('btn-reset').addEventListener('click', () => { S.extraction = null; $('findings-card').hidden = true; applyPreset(S.presetId, true); });
    $('load-json').addEventListener('change', async (e) => {
      const f = e.target.files[0]; e.target.value = ''; if (!f) return;
      try { loadSpec(JSON.parse(await f.text())); setStatus(`${f.name} 불러옴`); } catch (err) { setStatus(`JSON 불러오기 실패: ${err.message}`, true); }
    });
    $('btn-extract').addEventListener('click', runExtract);
    $('btn-cancel').addEventListener('click', () => S.abort?.abort());
  }

  function initSettings() {
    const dlg = $('dlg-settings');
    $('btn-settings').addEventListener('click', () => {
      $('set-key').value = store.get('key', ''); $('set-model').value = store.get('model', 'claude-opus-5-5');
      $('set-effort').value = store.get('effort', 'high'); dlg.showModal();
    });
    $('set-save').addEventListener('click', () => {
      store.set('key', $('set-key').value.trim()); store.set('model', $('set-model').value.trim() || 'claude-opus-5-5');
      store.set('effort', $('set-effort').value); dlg.close(); setStatus('설정을 저장했습니다.');
    });
    $('set-close').addEventListener('click', () => dlg.close());
  }

  function initViewer() {
    if (!window.THREE) {
      const n = $('noscene'); n.hidden = false;
      n.textContent = '3D 엔진(three.js)을 cdnjs.cloudflare.com 에서 불러오지 못했습니다. 네트워크에서 이 주소가 막혀 있는지 확인하세요. 파라미터 편집과 JSON 저장은 계속 쓸 수 있습니다.';
      return;
    }
    const tip = $('tip');
    Viewer.init($('viewport'), {
      onHover: (id, e) => {
        if (!id) { tip.hidden = true; return; }
        const p = S.model.parts.find((x) => x.id === id);
        const r = $('viewport').getBoundingClientRect();
        tip.hidden = false;
        tip.innerHTML = `<b>${esc(p.label)}</b>${p.desc ? `<br>${esc(p.desc)}` : ''}`;
        tip.style.left = `${e.clientX - r.left + 14}px`; tip.style.top = `${e.clientY - r.top + 14}px`;
      },
      onPick: (id) => selectPart(id),
    });
    const bg = () => Viewer.setBackground(getComputedStyle(document.documentElement).getPropertyValue('--stage').trim() || '#e9edf1');
    bg();
    window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', bg);
  }

  initPresets(); initFiles(); initToolbar(); initSettings(); initViewer();
  applyPreset(S.presetId, true);
  window.IC3D = { S, loadSpec, specJSON, rebuild };   // 디버깅·자동화용
})();
