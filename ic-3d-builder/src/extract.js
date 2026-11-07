/* GA / dimensional drawing → Anatomy parameters + parts list, via the Claude Messages API (browser).
 *
 * Rule: the model returns only what is written on the drawing. Filling gaps with standard
 * values is the app's job (RefData), recorded with source 'standard', so drawing values
 * and assumptions never mix.
 */
'use strict';

const Extract = (() => {
  const API_URL = 'https://api.anthropic.com/v1/messages';

  const SCHEMA = {
    type: 'object',
    properties: {
      item_type: { type: 'string', enum: ['valve', 'cabinet', 'hookup'], description: 'Item category of the drawing' },
      title_block: {
        type: 'object',
        properties: {
          tag: { type: 'string' }, dwg_no: { type: 'string' }, rev: { type: 'string' },
          vendor: { type: 'string' }, model_no: { type: 'string' }, description: { type: 'string' },
        },
        required: ['tag', 'dwg_no', 'rev', 'vendor', 'model_no', 'description'],
        additionalProperties: false,
      },
      size_row: { type: 'string', description: 'Row chosen from a size-dependent dimension table and why; "-" if not applicable' },
      params: {
        type: 'array',
        description: 'Only values read directly from the drawing. Never fill from standards or estimates',
        items: {
          type: 'object',
          properties: {
            key: { type: 'string', description: 'Parameter key from the dictionary' },
            value: { type: 'string', description: 'Lengths: number in mm only. Enums: one of the listed options' },
            as_drawn: { type: 'string', description: 'Text exactly as on the drawing, e.g. "A = 11.50 in", "Ø 356"' },
            evidence: { type: 'string', description: 'Which view / table / note it was read from' },
            confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
          },
          required: ['key', 'value', 'as_drawn', 'evidence', 'confidence'],
          additionalProperties: false,
        },
      },
      parts_list: {
        type: 'array',
        description: 'Bill of materials / parts list on the drawing (balloon item numbers), mapped to part ids',
        items: {
          type: 'object',
          properties: {
            item_no: { type: 'string', description: 'Balloon / item number as printed' },
            name: { type: 'string', description: 'Part name as printed' },
            material: { type: 'string', description: 'Material as printed, "-" if none' },
            qty: { type: 'string', description: 'Quantity as printed, "-" if none' },
            part_id: { type: 'string', description: 'Best matching part id from the part catalogue, or "none"' },
          },
          required: ['item_no', 'name', 'material', 'qty', 'part_id'],
          additionalProperties: false,
        },
      },
      unmapped_dimensions: {
        type: 'array', description: 'Dimensions on the drawing that no key captures (e.g. bolt length, nozzle orientation)',
        items: { type: 'string' },
      },
      review_findings: {
        type: 'array',
        items: {
          type: 'object',
          properties: { severity: { type: 'string', enum: ['high', 'medium', 'low'] }, finding: { type: 'string' } },
          required: ['severity', 'finding'], additionalProperties: false,
        },
      },
      summary: { type: 'string', description: 'Two or three sentences' },
    },
    required: ['item_type', 'title_block', 'size_row', 'params', 'parts_list', 'unmapped_dimensions', 'review_findings', 'summary'],
    additionalProperties: false,
  };

  function systemPrompt() {
    const L = [
      'You are an instrumentation & control engineer. You read General Arrangement (GA) and dimensional',
      'drawings of I&C items and transfer them into the parameters of a parametric 3D model.',
      '',
      'The result is used for plant layout and clash checks. Inventing a dimension is worse than leaving it out.',
      'Do not put values that are not on the drawing into params; the app fills gaps from standard tables and labels them.',
      '',
      '# Rules',
      '1. Convert every length to a number in mm (inch × 25.4, one decimal). Keep the original text in as_drawn.',
      '2. If there is a size-dependent dimension table (columns A, B, C, H …), use the row for the size/class in the user hint',
      '   and state it in size_row. With no hint and several rows, decide from the tag / title block; if unsure, add a high finding.',
      '3. Before mapping a dimension letter to a key, check in the view what the dimension line measures.',
      '   E.g. valve "A" flange-face to flange-face → ftf; centreline to top → overall_h.',
      '4. Dimensions marked MAX, APPROX or REF get confidence medium or lower.',
      '5. Also read operator parts (actuator, handwheel, positioner) when dimensioned.',
      '6. Cabinets: separate the plinth from the body height; overall drawing height = h + plinth_h.',
      '7. Hook-ups carry few dimensions; read configuration first (instrument, manifold, fluid, tap orientation).',
      '8. Parts list: copy every row of the drawing\'s BOM / parts list. Map each to the closest part_id from the',
      '   catalogue below (by function, not only by name), or "none".',
      '',
      '# Parameter dictionary by item_type',
    ];
    for (const [id, T] of Object.entries(Anatomy.TYPES)) {
      L.push('', `## item_type = ${id} (${T.label})`, Anatomy.describeSchema(id));
      L.push('', `Part catalogue (part_id: name) for ${id}:`, Anatomy.partCatalog(id).map((p) => `${p.id}: ${p.name}`).join(' · '));
    }
    return L.join('\n');
  }

  async function fileBlock(file) {
    const b64 = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result).split(',')[1]);
      r.onerror = () => rej(r.error);
      r.readAsDataURL(file);
    });
    if (file.type === 'application/pdf') return { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: b64 } };
    const mt = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type) ? file.type : 'image/png';
    return { type: 'image', source: { type: 'base64', media_type: mt, data: b64 } };
  }

  async function run({ apiKey, model, effort, files, typeHint, hint, signal, onProgress }) {
    if (!apiKey) throw new Error('Enter your Anthropic API key in ⚙ Settings.');
    if (!files.length) throw new Error('Add a drawing file first.');
    const content = [];
    for (const f of files) {
      content.push({ type: 'text', text: `## Drawing file: ${f.name}` });
      content.push(await fileBlock(f));
    }
    content.push({
      type: 'text',
      text: [`Selected item category: ${typeHint || 'auto-detect'}`, `User hint: ${hint || '(none)'}`,
        'Read the dimensions, configuration values and parts list from the drawing(s) above.'].join('\n'),
    });
    const body = {
      model, max_tokens: 32000, stream: true,
      thinking: { type: 'adaptive' },
      system: [{ type: 'text', text: systemPrompt(), cache_control: { type: 'ephemeral' } }],
      output_config: { effort, format: { type: 'json_schema', schema: SCHEMA } },
      fallbacks: 'default',
      messages: [{ role: 'user', content }],
    };
    const res = await fetch(API_URL, {
      method: 'POST', signal, credentials: 'omit',
      headers: {
        'content-type': 'application/json',
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'anthropic-beta': 'server-side-fallback-2026-07-01',
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      let msg = '';
      try { const j = await res.json(); msg = j?.error?.message || JSON.stringify(j); } catch { msg = await res.text().catch(() => ''); }
      const tip = { 401: 'Check the API key.', 404: 'Check the model ID.', 413: 'File too large.', 429: 'Rate limited — try again shortly.', 529: 'API overloaded — try again shortly.' }[res.status];
      throw new Error(`HTTP ${res.status} — ${msg}${tip ? '\n' + tip : ''}`);
    }
    const { text, usage, stopReason } = await consume(res, signal, onProgress);
    if (stopReason === 'refusal') throw new Error('The model declined this request (refusal).');
    if (stopReason === 'max_tokens') throw new Error('The response was cut off (max_tokens).');
    try { return { data: JSON.parse(text), usage }; } catch { throw new Error(`Could not parse JSON\n${text.slice(0, 300)}`); }
  }

  async function consume(res, signal, onProgress) {
    const reader = res.body.getReader(); const dec = new TextDecoder();
    const textBlocks = new Set(); let buf = ''; let text = ''; let usage = null; let stopReason = null;
    for (;;) {
      if (signal?.aborted) { await reader.cancel(); throw new DOMException('aborted', 'AbortError'); }
      const { done, value } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = chunk.split('\n').find((l) => l.startsWith('data:')); if (!line) continue;
        let ev; try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
        if (ev.type === 'message_start') {
          // a server-side fallback starts a fresh message: collect text again
          text = ''; textBlocks.clear(); usage = { ...(ev.message?.usage || {}) };
        } else if (ev.type === 'content_block_start' && ev.content_block?.type === 'text') textBlocks.add(ev.index);
        else if (ev.type === 'content_block_delta' && ev.delta?.type === 'text_delta' && textBlocks.has(ev.index)) {
          text += ev.delta.text; onProgress?.(text.length);
        } else if (ev.type === 'message_delta') {
          if (ev.delta?.stop_reason) stopReason = ev.delta.stop_reason;
          if (ev.usage) usage = { ...(usage || {}), ...ev.usage };
        } else if (ev.type === 'error') throw new Error(ev.error?.message || 'Streaming error');
      }
    }
    return { text, usage, stopReason };
  }

  /** extraction result → resolve() inputs + parts list */
  function toInputs(data, typeId) {
    const keys = new Set(Anatomy.TYPES[typeId].params.map((p) => p.key));
    const inputs = {}; const dropped = [];
    for (const p of data.params || []) {
      if (!keys.has(p.key)) { dropped.push(`${p.key}=${p.value}`); continue; }
      inputs[p.key] = { value: p.value, src: 'drawing', evidence: `${p.as_drawn} · ${p.evidence}`, confidence: p.confidence };
    }
    if (data.title_block?.tag && keys.has('tag') && !inputs.tag) inputs.tag = { value: data.title_block.tag, src: 'drawing', evidence: 'title block' };
    const ids = new Set(Anatomy.partCatalog(typeId).map((p) => p.id));
    const partsList = (data.parts_list || []).map((r) => ({
      item_no: r.item_no, name: r.name,
      material: r.material && r.material !== '-' ? r.material : '',
      qty: r.qty && r.qty !== '-' ? r.qty : '',
      part_id: ids.has(r.part_id) ? r.part_id : 'none',
    }));
    return { inputs, dropped, partsList };
  }

  return { run, toInputs, systemPrompt, SCHEMA };
})();
