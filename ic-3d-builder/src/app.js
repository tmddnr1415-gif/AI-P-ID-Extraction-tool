/* App — item selection, drawing read-out, parameter form, part info card, parts list. */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const SRC = { drawing: 'Drawing', user: 'User', standard: 'Standard', estimate: 'Estimate', default: 'Default', none: '—' };
  const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const HINT = 'Scroll in to take it apart · click a part for details · double-click to isolate';

  const store = {
    get(k, d) { try { const v = localStorage.getItem(`ic3d.${k}`); return v == null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(`ic3d.${k}`, v); } catch { /* storage unavailable */ } },
  };

  const S = {
    presetId: store.get('preset', 'cv_globe'), type: 'valve',
    inputs: {}, partsList: [], files: [], extraction: null, model: null, abort: null, selected: null,
  };

  // ───────── item ─────────
  function initPresets() {
    const sel = $('preset');
    for (const [t, name] of Object.entries({ valve: 'Valves', cabinet: 'Cabinets', hookup: 'Instrument hook-ups' })) {
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
    S.presetId = p.id; S.type = p.type; store.set('preset', p.id);
    if (resetInputs) {
      S.inputs = {}; S.partsList = []; S.selected = null;
      for (const [k, v] of Object.entries(p.set)) S.inputs[k] = { value: v, src: 'default' };
    }
    $('preset-note').textContent = 'The preset only sets the configuration. Each dimension comes from the drawing, then your input, then the standard table, then an estimate.';
    rebuild({ refit: true });
  }

  /** if the drawing / user changes body or operator, follow with the matching preset */
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

  // ───────── form ─────────
  function renderForm() {
    const T = Anatomy.TYPES[S.type];
    const { values, meta } = S.model;
    const form = $('form'); form.innerHTML = '';
    let grp = null;
    for (const p of T.params) {
      if (p.group !== grp) { grp = p.group; const g = document.createElement('div'); g.className = 'grp'; g.textContent = grp; form.appendChild(g); }
      const m = meta[p.key] || {};
      const row = document.createElement('div'); row.className = 'prm' + (m.active ? '' : ' inactive');
      const id = `p-${p.key}`;
      const lab = document.createElement('label'); lab.htmlFor = id; lab.textContent = p.label; if (p.desc) lab.title = p.desc;
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
        if (p.type === 'num') input.step = p.step || 'any';
        if (p.min != null) input.min = p.min;
        if (p.max != null) input.max = p.max;
        const v = values[p.key];
        input.value = v == null || Number.isNaN(v) ? '' : (p.type === 'num' ? +(+v).toFixed(2) : v);
      }
      input.id = id;
      input.addEventListener('change', () => {
        const val = p.type === 'bool' ? input.checked : input.value;
        if (val === '' && p.type !== 'bool') delete S.inputs[p.key];
        else S.inputs[p.key] = { value: val, src: 'user' };
        rebuild({});
      });
      const badge = document.createElement('span');
      badge.className = `src src-${m.src || 'none'}`;
      badge.textContent = (p.unit ? `${p.unit} · ` : '') + (SRC[m.src] || '');
      badge.title = [m.ref, m.evidence, m.confidence && `confidence ${m.confidence}`].filter(Boolean).join('\n') || SRC[m.src] || '';
      if (m.src && m.src !== 'default') {
        badge.style.cursor = 'pointer';
        badge.title += '\n(click: clear this value and fall back to standard / estimate)';
        badge.addEventListener('click', () => { delete S.inputs[p.key]; rebuild({}); });
      }
      row.append(lab, input, badge);
      const note = m.src === 'drawing' && m.evidence ? `↳ ${m.evidence}${m.confidence ? ` (${m.confidence})` : ''}` : (m.ref && m.active ? `↳ ${m.ref}` : '');
      if (note) { const ev = document.createElement('div'); ev.className = 'ev'; ev.textContent = note; row.appendChild(ev); }
      form.appendChild(row);
    }
  }

  // ───────── build ─────────
  function rebuild({ refit }) {
    syncPreset();
    try {
      S.model = Anatomy.build({ type: S.type, inputs: S.inputs, parts_list: S.partsList });
    } catch (e) {
      console.error(e); setStatus(`Could not build the model: ${e.message}`, true); return;
    }
    renderForm();
    if (window.Viewer) {
      if (refit && Viewer.state.focus) Viewer.focus(null);
      Viewer.show(S.model, { keepView: !refit });
      if (refit) { Viewer.setExplode(0, true); $('explode').value = 0; Viewer.setView('iso'); $('hint-bar').hidden = false; }
    }
    renderBOM();
    renderSummary();
    if (S.selected && S.model.parts.some((p) => p.id === S.selected)) selectPart(S.selected, false, true); else hideInfo();
  }

  const keySize = (p) => {
    const d = p.dims.find((x) => x.unit === 'mm' && typeof x.v === 'number') || p.dims[0];
    return d ? `${d.k}: ${d.v}${d.unit ? ' ' + d.unit : ''}` : '';
  };

  function renderBOM() {
    const tb = $('bom').querySelector('tbody'); tb.innerHTML = '';
    const parts = S.model.parts.filter((p) => !['ghost', 'clear'].includes(p.look));
    $('parts-count').textContent = `${parts.length} parts — click a row to locate it`;
    for (const p of parts) {
      const tr = document.createElement('tr'); tr.dataset.id = p.id;
      const td0 = document.createElement('td');
      const cbx = document.createElement('input'); cbx.type = 'checkbox'; cbx.checked = true; cbx.title = 'Show / hide';
      cbx.addEventListener('click', (e) => { e.stopPropagation(); if (window.Viewer) Viewer.setVisible(p.id, cbx.checked); });
      td0.appendChild(cbx); tr.appendChild(td0);
      const sw = `<span class="sw" style="background:${window.Viewer ? Viewer.lookColor(p.look) : '#888'}"></span>`;
      const mat = p.dwgMaterial ? `${esc(p.dwgMaterial)} <span class="src src-drawing">Drawing</span>` : esc(p.material);
      tr.insertAdjacentHTML('beforeend', `<td class="no">${esc(p.no ?? '')}</td><td>${sw}${esc(p.dwgName || p.name)}</td><td class="muted">${esc(p.group)}</td>`
        + `<td>${esc(p.dwgQty || p.qty)}</td><td class="mat">${mat}</td><td class="muted">${esc(keySize(p))}</td>`);
      tr.addEventListener('click', () => selectPart(p.id, true));
      tr.addEventListener('dblclick', () => window.Viewer && Viewer.focus(p.id));
      tb.appendChild(tr);
    }
  }

  function selectPart(id, fromList, quiet) {
    S.selected = id;
    $('tip').hidden = true;
    if (id && !quiet && document.body.classList.contains('embed') && window.parent !== window) {
      try { window.parent.postMessage({ type: 'ic3d-pick', part: id, preset: S.presetId }, '*'); } catch { /* host gone */ }
    }
    if (window.Viewer) Viewer.select(id);
    for (const tr of $('bom').querySelectorAll('tbody tr')) tr.classList.toggle('sel', tr.dataset.id === id);
    if (!id) { hideInfo(); return; }
    showInfo(id);
    if (quiet) return;
    if (!fromList) $('bom').querySelector(`tr[data-id="${CSS.escape(id)}"]`)?.scrollIntoView({ block: 'nearest' });
    // picking an internal part from the list: take the assembly apart so it can be seen
    if (fromList && window.Viewer && Viewer.getExplode() < 0.9) {
      const p = S.model.parts.find((x) => x.id === id);
      if (p && (p.stage ?? 1) >= 1) { Viewer.setExplode(1); $('explode').value = 1; $('hint-bar').hidden = true; }
    }
  }

  function showInfo(id) {
    const p = S.model.parts.find((x) => x.id === id); if (!p) { hideInfo(); return; }
    const box = $('info'); box.hidden = false;
    if (window.Viewer) Viewer.setOption('insetRight', Math.min(360, $('viewport').clientWidth * 0.4));
    const dims = p.dims.map((d) => `<tr><td>${esc(d.k)}</td><td><b>${esc(d.v)}</b>${d.unit ? ' ' + esc(d.unit) : ''}</td><td><span class="src src-${esc(d.src)}">${esc(SRC[d.src] || d.src)}</span></td></tr>`).join('');
    const mat = p.dwgMaterial
      ? `${esc(p.dwgMaterial)} <span class="src src-drawing">Drawing</span><div class="muted small">Typical: ${esc(p.material)}</div>`
      : `${esc(p.material || '—')} <span class="muted small">(typical)</span>`;
    box.innerHTML = `
      <div class="info-head"><span class="info-no">${esc(p.no ?? '·')}</span><div class="info-title"><div class="info-name">${esc(p.dwgName || p.name)}</div>
        <div class="muted small">${esc(p.group)}${p.dwgName ? ` · ${esc(p.name)}` : ''} · Qty ${esc(p.dwgQty || p.qty)}</div></div>
        <button class="x" id="info-close" aria-label="Close">✕</button></div>
      ${p.fn ? `<p class="info-fn">${esc(p.fn)}</p>` : ''}
      <div class="info-k">Material</div><div class="info-v">${mat}</div>
      ${dims ? `<div class="info-k">Size-linked dimensions</div><table class="kv dims">${dims}</table>` : ''}
      ${p.note ? `<p class="muted small">${esc(p.note)}</p>` : ''}
      <div class="row small"><button class="ghost-btn" id="info-iso">Isolate</button><button class="ghost-btn" id="info-hide">Hide</button></div>`;
    $('info-close').onclick = () => selectPart(null);
    $('info-iso').onclick = () => window.Viewer && Viewer.focus(p.id);
    $('info-hide').onclick = () => {
      if (window.Viewer) Viewer.setVisible(p.id, false);
      const cbx = $('bom').querySelector(`tr[data-id="${CSS.escape(p.id)}"] input`); if (cbx) cbx.checked = false;
    };
  }
  function hideInfo() { $('info').hidden = true; if (window.Viewer) Viewer.setOption('insetRight', 0); }

  function renderSummary() {
    const { values, meta, bbox } = S.model;
    const cnt = {};
    for (const m of Object.values(meta)) if (m.active) cnt[m.src] = (cnt[m.src] || 0) + 1;
    const rows = [['Item', Anatomy.PRESETS.find((p) => p.id === S.presetId)?.label || S.type], ['Tag', values.tag || '—']];
    if (S.type === 'valve') {
      rows.push(['Size / rating', values.body === 'psv'
        ? `${values.nps}" CL${values.cls} × ${values.outlet_nps}" CL${values.outlet_cls}` : `${values.nps}" ASME CL${values.cls} RF`]);
    }
    rows.push(['Envelope L × W × H', bbox && isFinite(bbox.size[0]) ? bbox.size.map((v) => Math.round(v)).join(' × ') + ' mm' : '—']);
    rows.push(['Dimension sources', ['drawing', 'user', 'standard', 'estimate', 'default'].filter((k) => cnt[k]).map((k) => `${SRC[k]} ${cnt[k]}`).join(' · ')]);
    if (S.extraction?.title_block) {
      const tb = S.extraction.title_block;
      rows.push(['Drawing', [tb.dwg_no, tb.rev && `Rev. ${tb.rev}`].filter(Boolean).join(' ') || '—']);
      rows.push(['Vendor / model', [tb.vendor, tb.model_no].filter(Boolean).join(' / ') || '—']);
    }
    if (S.partsList.length) rows.push(['Parts list (drawing)', `${S.partsList.length} rows, ${S.partsList.filter((r) => r.part_id !== 'none').length} linked to 3D parts`]);
    const tbl = rows.map(([k, v]) => `<tr><td class="muted">${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
    const chk = (S.model.warnings || []).map((w) => `<p class="small sev-high">⚠ ${esc(w)}</p>`).join('');
    const warn = cnt.estimate ? `<p class="small est-note">${cnt.estimate} estimated dimensions — shape reference only. Do not base clash-check conclusions on them until confirmed from a drawing.</p>` : '';
    const std = cnt.standard ? '<p class="small muted">Standard values come from a built-in reference table not yet verified against the source standard. The vendor drawing governs.</p>' : '';
    $('summary').innerHTML = `<table class="kv">${tbl}</table>${chk}${warn}${std}`;
  }

  // ───────── files / extraction ─────────
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
      if (f.size > 30 * 1024 * 1024) { setStatus(`${f.name}: larger than 30 MB`, true); continue; }
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
      if (f.type.startsWith('image/')) { const img = document.createElement('img'); img.src = URL.createObjectURL(f); img.alt = f.name; left.appendChild(img); }
      const rm = document.createElement('button'); rm.textContent = '✕'; rm.title = 'Remove';
      rm.addEventListener('click', () => { S.files.splice(i, 1); renderFiles(); });
      li.append(left, rm); ul.appendChild(li);
    });
  }

  async function runExtract() {
    const btn = $('btn-extract'); const cancel = $('btn-cancel');
    btn.disabled = true; cancel.hidden = false;
    S.abort = new AbortController();
    const t0 = Date.now();
    setStatus('Sending drawing…');
    try {
      const { data, usage } = await Extract.run({
        apiKey: store.get('key', ''), model: store.get('model', 'claude-opus-5-5'), effort: store.get('effort', 'high'),
        files: S.files, typeHint: S.type, hint: $('hint').value.trim(), signal: S.abort.signal,
        onProgress: (n) => setStatus(`Reading… ${n.toLocaleString()} chars · ${((Date.now() - t0) / 1000).toFixed(0)} s`),
      });
      S.extraction = data;
      if (data.item_type && data.item_type !== S.type) {
        const p = Anatomy.PRESETS.find((x) => x.type === data.item_type);
        if (p) { $('preset').value = p.id; applyPreset(p.id, true); }
      }
      const { inputs, dropped, partsList } = Extract.toInputs(data, S.type);
      for (const [k, v] of Object.entries(inputs)) if (S.inputs[k]?.src !== 'user') S.inputs[k] = v;
      S.partsList = partsList;
      rebuild({ refit: true });
      renderFindings(data, dropped);
      setStatus(`Done — ${Object.keys(inputs).length} values and ${partsList.length} parts-list rows read from the drawing (${((Date.now() - t0) / 1000).toFixed(0)} s, ${usage?.input_tokens ?? '?'} in / ${usage?.output_tokens ?? '?'} out tokens).`);
    } catch (e) {
      setStatus(e.name === 'AbortError' ? 'Stopped.' : e.message, e.name !== 'AbortError');
    } finally {
      btn.disabled = false; cancel.hidden = true; S.abort = null;
    }
  }

  function renderFindings(data, dropped) {
    const box = $('findings'); box.innerHTML = '';
    $('findings-card').hidden = false;
    const add = (html) => { const d = document.createElement('div'); d.className = 'find'; d.innerHTML = html; box.appendChild(d); };
    if (data.summary) add(esc(data.summary));
    if (data.size_row && data.size_row !== '-') add(`<b>Table row used:</b> ${esc(data.size_row)}`);
    for (const f of data.review_findings || []) add(`<span class="sev-${esc(f.severity)}">[${esc(f.severity)}]</span> ${esc(f.finding)}`);
    const unlinked = (S.partsList || []).filter((r) => r.part_id === 'none');
    if (unlinked.length) add(`<b>Parts-list rows without a 3D part:</b> ${unlinked.map((r) => `${esc(r.item_no)} ${esc(r.name)}`).join(', ')}`);
    if (data.unmapped_dimensions?.length) add(`<b>Dimensions not used in 3D:</b> ${data.unmapped_dimensions.map(esc).join(', ')}`);
    if (dropped?.length) add(`<b>Unknown keys (ignored):</b> ${dropped.map(esc).join(', ')}`);
  }

  function setStatus(msg, err) { const s = $('status'); s.textContent = msg; s.classList.toggle('err', !!err); }

  // ───────── export / import ─────────
  const fileBase = () => `${(S.model.values.tag || S.presetId).replace(/[^\w.-]+/g, '_')}_3d`;
  function download(blob, name) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  function specJSON() {
    const { values, meta, bbox, parts } = S.model;
    return {
      tool: 'ic-3d-builder', version: 2, type: S.type, preset: S.presetId,
      inputs: S.inputs, parts_list: S.partsList,
      resolved: Object.fromEntries(Object.entries(values).map(([k, v]) => [k, { value: v, ...meta[k] }])),
      bom: parts.filter((p) => !['ghost', 'clear'].includes(p.look)).map((p) => ({
        no: p.no, id: p.id, name: p.dwgName || p.name, group: p.group, qty: p.dwgQty || p.qty,
        material: p.dwgMaterial || p.material, material_src: p.dwgMaterial ? 'drawing' : 'typical', function: p.fn, dims: p.dims,
      })),
      bbox_mm: bbox, extraction: S.extraction,
      note: 'Values not sourced from drawing/user come from a reference table or a proportional estimate. Not for fabrication or purchasing.',
    };
  }
  function loadSpec(obj) {
    if (!obj || !Anatomy.TYPES[obj.type]) throw new Error('type must be valve, cabinet or hookup.');
    const preset = Anatomy.PRESETS.find((p) => p.id === obj.preset) || Anatomy.PRESETS.find((p) => p.type === obj.type);
    S.presetId = preset.id; S.type = obj.type; $('preset').value = preset.id;
    S.inputs = {};
    for (const [k, v] of Object.entries(obj.inputs || {})) S.inputs[k] = (v && typeof v === 'object' && 'value' in v) ? v : { value: v, src: 'user' };
    S.partsList = Array.isArray(obj.parts_list) ? obj.parts_list : [];
    S.extraction = obj.extraction || null;
    applyPreset(preset.id, false);
    if (S.extraction) renderFindings(S.extraction, []);
  }

  function initToolbar() {
    for (const b of document.querySelectorAll('[data-view]')) b.addEventListener('click', () => Viewer.setView(b.dataset.view));
    $('explode').addEventListener('input', (e) => { Viewer.setExplode(+e.target.value); $('hint-bar').hidden = +e.target.value > 0.05; });
    $('opt-auto').addEventListener('change', (e) => Viewer.setOption('autoExplode', e.target.checked));
    $('opt-section').addEventListener('change', (e) => Viewer.setOption('section', e.target.checked));
    $('opt-labels').addEventListener('change', (e) => Viewer.setOption('labels', e.target.value));
    $('opt-dims').addEventListener('change', (e) => Viewer.setOption('dims', e.target.checked));
    $('opt-edges').addEventListener('change', (e) => Viewer.setOption('edges', e.target.checked));
    $('opt-style').value = store.get('style', 'real');
    $('opt-style').addEventListener('change', (e) => {
      store.set('style', e.target.value);
      Viewer.setOption('style', e.target.value);
      $('opt-edges').checked = e.target.value === 'tech'; Viewer.setOption('edges', $('opt-edges').checked);
    });
    $('ex-stl').addEventListener('click', () => download(Viewer.toSTL(), `${fileBase()}.stl`));
    $('ex-obj').addEventListener('click', () => download(Viewer.toOBJ(fileBase()), `${fileBase()}.obj`));
    $('ex-png').addEventListener('click', async () => download(await (await fetch(Viewer.toPNG())).blob(), `${fileBase()}.png`));
    $('ex-json').addEventListener('click', () => download(new Blob([JSON.stringify(specJSON(), null, 2)], { type: 'application/json' }), `${fileBase()}.json`));
    $('btn-reset').addEventListener('click', () => { S.extraction = null; $('findings-card').hidden = true; applyPreset(S.presetId, true); });
    $('load-json').addEventListener('change', async (e) => {
      const f = e.target.files[0]; e.target.value = ''; if (!f) return;
      try { loadSpec(JSON.parse(await f.text())); setStatus(`Loaded ${f.name}`); } catch (err) { setStatus(`Could not load JSON: ${err.message}`, true); }
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
      store.set('effort', $('set-effort').value); dlg.close(); setStatus('Settings saved.');
    });
    $('set-close').addEventListener('click', () => dlg.close());
  }

  function initViewer() {
    if (!window.Viewer) {
      const n = $('noscene'); n.hidden = false;
      n.textContent = 'The built-in 3D engine failed to start. Parameter editing and JSON export still work.';
      return;
    }
    const tip = $('tip');
    Viewer.init($('viewport'), {
      onHover: (id, e) => {
        if (!id || id === S.selected) { tip.hidden = true; return; }
        const p = S.model.parts.find((x) => x.id === id); if (!p) return;
        const r = $('viewport').getBoundingClientRect();
        tip.hidden = false;
        tip.innerHTML = `<b>${esc(p.no ?? '')} · ${esc(p.dwgName || p.name)}</b>${p.fn ? `<br>${esc(p.fn.length > 140 ? p.fn.slice(0, 140) + '…' : p.fn)}` : ''}`;
        tip.style.left = `${Math.max(4, Math.min(e.clientX - r.left + 14, r.width - tip.offsetWidth - 6))}px`; tip.style.top = `${Math.max(4, Math.min(e.clientY - r.top + 14, r.height - tip.offsetHeight - 6))}px`;
      },
      onPick: (id) => selectPart(id, false),
      onExplode: (k) => { $('explode').value = k; $('hint-bar').hidden = k > 0.05; },
      onFocus: (id) => { $('hint-bar').hidden = false; $('hint-bar').textContent = id ? 'Isolated — double-click the part again (or Isolate) to return' : HINT; },
    });
    const bg = () => Viewer.setBackground(getComputedStyle(document.documentElement).getPropertyValue('--stage').trim() || '#e9edf1');
    if (store.get('style', 'real') !== 'real') { Viewer.setOption('style', 'tech'); Viewer.setOption('edges', true); $('opt-edges').checked = true; }
    bg();
    window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', bg);
  }

  initPresets(); initFiles(); initToolbar(); initSettings(); initViewer();
  // ───────── embed mode: driven by a host page (I&C dashboard) via URL hash + postMessage ─────────
  //   #embed&preset=esdv_ball      → compact layout (viewport only) on that preset
  //   postMessage {type:'ic3d', cmd:'preset', id}          → switch preset
  //   postMessage {type:'ic3d', cmd:'highlight', part}     → select + explode to show + pulse
  //   postMessage {type:'ic3d', cmd:'explode', k} / {cmd:'view', name}
  //   posts back {type:'ic3d-ready'} and {type:'ic3d-pick', part}
  const hash = new URLSearchParams(location.hash.slice(1));
  if (!location.hash && /^ic3d-embed/.test(window.name || '')) { hash.set('embed', '1'); const pn = window.name.split(':')[1]; if (pn) hash.set('preset', pn); }
  const embedded = hash.has('embed');
  if (embedded) {
    document.body.classList.add('embed');
    const pr = hash.get('preset'); if (pr && Anatomy.PRESETS.some((p) => p.id === pr)) S.presetId = pr;
    $('preset').value = S.presetId;
  }
  applyPreset(S.presetId, true);
  const post = (m) => { try { if (window.parent !== window) window.parent.postMessage(m, '*'); } catch { /* cross-origin host */ } };
  window.addEventListener('message', (e) => {
    const m = e.data; if (!m || m.type !== 'ic3d') return;
    if (m.cmd === 'preset' && Anatomy.PRESETS.some((p) => p.id === m.id)) {
      if (m.id !== S.presetId) { $('preset').value = m.id; applyPreset(m.id, true); }
    } else if (m.cmd === 'highlight' && m.part && S.model.parts.some((p) => p.id === m.part)) {
      if (window.Viewer) Viewer.fit();   // a tag click always brings the whole model back into view
      selectPart(m.part, true);
      if (window.Viewer) { const el = document.getElementById('viewport'); el.classList.remove('pulse'); void el.offsetWidth; el.classList.add('pulse'); }
    } else if (m.cmd === 'explode' && window.Viewer) { Viewer.setExplode(+m.k || 0); $('explode').value = +m.k || 0; }
    else if (m.cmd === 'view' && window.Viewer) Viewer.setView(m.name);
  });
  post({ type: 'ic3d-ready', presets: Anatomy.PRESETS.map((p) => p.id) });
  window.IC3D = { S, loadSpec, specJSON, rebuild, selectPart };   // automation / debugging
})();
