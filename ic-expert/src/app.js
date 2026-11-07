/* I&C Expert chat — UI, project context, attachments, conversation history. */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const store = {
    get(k, d) { try { const v = localStorage.getItem(`icx.${k}`); return v == null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(`icx.${k}`, v); } catch { /* storage unavailable */ } },
  };

  const STARTERS = [
    'Review the attached control valve datasheet against Saudi Aramco practice and ISA-75 — findings table please.',
    'DP flow transmitter vs Coriolis for a 6" fuel gas custody line at 55 °C ambient — which and why?',
    'What does API 670 require for proximity probes on a centrifugal compressor? Compare Bently Nevada 3500 options.',
    'Thermowell for 8 m/s hydrocarbon gas, 3/4" bore, 300 mm insertion — what checks per ASME PTC 19.3 TW-2016?',
    'ESD valve (SDV) spec checklist for a QatarEnergy LNG project: actuator, SOV, partial stroke, closure time, fire-safe.',
    '압력 트랜스미터 Emerson 3051S, Yokogawa EJX, Honeywell ST800 비교 — SIL 2 서비스, 사우디 아람코 프로젝트',
  ];

  const S = { messages: [], view: [], files: [], busy: false, abort: null };
  const kbText = (typeof KB !== 'undefined' ? KB : []).map((k) => `<kb file="${k.file}" n="${k.n}">\n${k.text}\n</kb>`).join('\n\n');

  // ───────── context ─────────
  const CTX = ['client', 'project', 'site', 'area', 'notes'];
  function initContext() {
    for (const k of CTX) {
      const el = $(`ctx-${k}`); el.value = store.get(`ctx.${k}`, el.value || '');
      el.addEventListener('change', () => store.set(`ctx.${k}`, el.value));
    }
  }
  function projectCtx() {
    const v = Object.fromEntries(CTX.map((k) => [k, $(`ctx-${k}`).value.trim()]));
    return [`Client / standard basis: ${v.client}`, v.project && `Project / unit: ${v.project}`, v.site && `Site conditions: ${v.site}`,
      v.area && `Area classification / SIL: ${v.area}`, v.notes && `Notes: ${v.notes}`].filter(Boolean).join('\n');
  }

  // ───────── files ─────────
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
      if (f.size > 25 * 1024 * 1024) { setStatus(`${f.name}: larger than 25 MB`); continue; }
      S.files.push(f);
    }
    renderFiles();
  }
  function renderFiles() {
    const ul = $('files'); ul.innerHTML = ''; const chips = $('pending'); chips.innerHTML = '';
    S.files.forEach((f, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<span>${f.type === 'application/pdf' ? '📄' : f.type.startsWith('image/') ? '🖼' : '📝'} ${MD.esc(f.name)}</span>`;
      const rm = document.createElement('button'); rm.textContent = '✕'; rm.title = 'Remove';
      rm.onclick = () => { S.files.splice(i, 1); renderFiles(); };
      li.appendChild(rm); ul.appendChild(li);
      const c = document.createElement('span'); c.className = 'chip'; c.textContent = f.name; chips.appendChild(c);
    });
  }

  // ───────── rendering ─────────
  function addBubble(role, html, extra = '') {
    $('welcome')?.remove();
    const d = document.createElement('div'); d.className = `msg ${role}`;
    d.innerHTML = `<div class="who">${role === 'user' ? 'You' : 'I&amp;C Expert'}</div><div class="body">${html}</div>${extra}`;
    $('log').appendChild(d); d.scrollIntoView({ block: 'end' });
    return d;
  }
  function sourcesHtml(content) {
    const seen = new Map();
    for (const b of content) {
      if (b.type === 'text') for (const c of b.citations || []) if (c.url && !seen.has(c.url)) seen.set(c.url, c.title || c.url);
    }
    if (!seen.size) return '';
    return `<details class="sources"><summary>Web sources (${seen.size})</summary><ol>${[...seen].map(([u, t]) => `<li><a href="${MD.esc(u)}" target="_blank" rel="noopener noreferrer">${MD.esc(t)}</a></li>`).join('')}</ol></details>`;
  }
  function searchesHtml(content) {
    const qs = content.filter((b) => b.type === 'server_tool_use' && b.input?.query).map((b) => b.input.query);
    return qs.length ? `<div class="searched small muted">Searched: ${qs.map((q) => `“${MD.esc(q)}”`).join(' · ')}</div>` : '';
  }

  // ───────── send ─────────
  async function send(text) {
    text = (text ?? $('input').value).trim();
    if (S.busy || (!text && !S.files.length)) return;
    $('input').value = '';
    const files = S.files.splice(0); renderFiles();
    const content = [];
    for (const f of files) content.push(await ExpertAPI.fileBlock(f));
    content.push({ type: 'text', text: text || 'Please review the attached documents.' });
    S.messages.push({ role: 'user', content });
    S.view.push({ role: 'user', text, files: files.map((f) => f.name) });
    addBubble('user', MD.render(text || '_(attachments)_') + (files.length ? `<div class="att small muted">📎 ${files.map((f) => MD.esc(f.name)).join(', ')}</div>` : ''));

    const bubble = addBubble('assistant', '<div class="typing">Thinking…</div>');
    const body = bubble.querySelector('.body');
    S.busy = true; S.abort = new AbortController();
    $('btn-send').disabled = true; $('btn-stop').hidden = false;
    const t0 = Date.now();
    setStatus('Thinking…');
    try {
      const r = await ExpertAPI.send({
        apiKey: store.get('key', ''), model: store.get('model', 'claude-opus-5-5'), effort: store.get('effort', 'high'),
        kbText, projectCtx: projectCtx(), messages: S.messages, webSearch: $('opt-web').checked, signal: S.abort.signal,
        onText: (t) => { body.innerHTML = MD.render(t); },
        onStatus: (s) => setStatus(s),
      });
      S.messages.push({ role: 'assistant', content: r.content });
      const answer = ExpertAPI.textOf(r.content);
      S.view.push({ role: 'assistant', text: answer, sources: r.content });
      body.innerHTML = MD.render(answer || '_(no text returned)_');
      bubble.insertAdjacentHTML('beforeend', searchesHtml(r.content) + sourcesHtml(r.content));
      const u = r.usage || {};
      setStatus(`Done in ${((Date.now() - t0) / 1000).toFixed(0)} s · ${(u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0)} in (${u.cache_read_input_tokens || 0} cached) / ${u.output_tokens || 0} out tokens${r.stopReason === 'max_tokens' ? ' · answer cut off (max tokens)' : ''}`);
    } catch (e) {
      S.messages.pop(); S.view.pop();                    // keep history valid: drop the unanswered turn
      if (e.name === 'AbortError') { body.innerHTML = '<p class="muted">Stopped.</p>'; setStatus('Stopped.'); }
      else { body.innerHTML = `<p class="err">${MD.esc(e.message)}</p>`; setStatus('Error'); }
    } finally {
      S.busy = false; S.abort = null; $('btn-send').disabled = false; $('btn-stop').hidden = true;
    }
  }

  function setStatus(s) { $('status').textContent = s; }

  function exportMd() {
    const L = [`# I&C Expert conversation`, '', `_${new Date().toISOString().slice(0, 16).replace('T', ' ')}_`, '', '## Project context', '', projectCtx(), ''];
    for (const m of S.view) {
      L.push(`## ${m.role === 'user' ? 'Question' : 'Answer'}`, '');
      if (m.files?.length) L.push(`Attachments: ${m.files.join(', ')}`, '');
      L.push(m.text, '');
      if (m.sources) {
        const urls = new Map();
        for (const b of m.sources) if (b.type === 'text') for (const c of b.citations || []) if (c.url) urls.set(c.url, c.title || c.url);
        if (urls.size) { L.push('Sources:', ...[...urls].map(([u, t]) => `- [${t}](${u})`), ''); }
      }
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([L.join('\n')], { type: 'text/markdown' }));
    a.download = `ic-expert-${Date.now()}.md`; document.body.appendChild(a); a.click(); a.remove();
  }

  function initUI() {
    const st = $('starters');
    for (const q of STARTERS) {
      const b = document.createElement('button'); b.className = 'starter'; b.textContent = q;
      b.onclick = () => { $('input').value = q; $('input').focus(); };
      st.appendChild(b);
    }
    const kb = typeof KB !== 'undefined' ? KB : [];
    $('kb-list').innerHTML = kb.length
      ? `Built-in knowledge base (${kb.length} files, ~${Math.round(kbText.length / 4 / 1000)}k tokens):<ul>${kb.map((k) => `<li>KB-${k.n} ${MD.esc(k.title)}</li>`).join('')}</ul>`
      : 'No built-in knowledge base found — answers rely on the model and web search.';
    $('input').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); } });
    $('btn-send').onclick = () => send();
    $('btn-stop').onclick = () => S.abort?.abort();
    $('btn-new').onclick = () => { if (S.busy) return; S.messages = []; S.view = []; location.reload(); };
    $('btn-export').onclick = exportMd;
    $('opt-web').checked = store.get('web', '1') === '1';
    $('opt-web').onchange = (e) => store.set('web', e.target.checked ? '1' : '0');
    const dlg = $('dlg-settings');
    $('btn-settings').onclick = () => {
      $('set-key').value = store.get('key', ''); $('set-model').value = store.get('model', 'claude-opus-5-5');
      $('set-effort').value = store.get('effort', 'high'); dlg.showModal();
    };
    $('set-save').onclick = () => {
      store.set('key', $('set-key').value.trim()); store.set('model', $('set-model').value.trim() || 'claude-opus-5-5');
      store.set('effort', $('set-effort').value); dlg.close(); setStatus('Settings saved.');
    };
    $('set-close').onclick = () => dlg.close();
  }

  initContext(); initFiles(); initUI();
  window.ICX = { S, send, projectCtx };
})();
