/* I&C Expert chat — UI modelled on chatbot-ui (sidebar switcher, grouped chat history, prompt library with
 * "/" picker and {{variables}}, hover actions copy / edit / regenerate, scroll buttons, hotkeys), adapted to
 * engineering review: per-project client context, spec attachments, findings tables → Excel / CSV,
 * knowledge-base viewer, cited web sources. */
'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const { LS } = Store;
  const esc = MD.esc;
  const kbList = typeof KB !== 'undefined' ? KB : [];
  const kbText = kbList.map((k) => `<kb file="${k.file}" n="${k.n}">\n${k.text}\n</kb>`).join('\n\n');

  const DEFAULT_PROMPTS = [
    { id: 'p-review', name: 'Spec / datasheet review', text: 'Review the attached {{document type}} for {{instrument / item}} against {{client standard}} practice and the international codes. Give the findings table and open questions.' },
    { id: 'p-select', name: 'Instrument type selection', text: 'Recommend the measurement principle for {{service}}: fluid {{fluid}}, line {{line size}}, range {{range}}, design {{design P / T}}, accuracy need {{accuracy}}. Compare the top 2–3 options and say which you would choose.' },
    { id: 'p-vendor', name: 'Vendor comparison', text: 'Compare {{vendor models}} for {{application}} (SIL {{SIL}}, area {{area classification}}). Table: key specs, approvals/SIL, materials, fit, notes.' },
    { id: 'p-cv', name: 'Control valve check', text: 'Check this control valve: {{size / class}}, Cv required {{Cv}}, ΔP {{dP}}, fluid {{fluid}}, noise limit {{dBA}}. Is the body/trim/actuator selection right? What about cavitation, noise, leakage class and fail action?' },
    { id: 'p-esd', name: 'ESD / on-off valve checklist', text: 'Give the specification checklist for an ESD valve (SDV/ZV) on {{service}} for a {{client}} project: actuator sizing margin, SOV arrangement, partial stroke test, closure time, fire-safe, tight shut-off, SIL.' },
    { id: 'p-tw', name: 'Thermowell (PTC 19.3 TW)', text: 'Thermowell check: velocity {{velocity m/s}}, fluid {{fluid}}, density {{density}}, insertion {{insertion length}}, bore {{bore}}, connection {{connection}}. What does ASME PTC 19.3 TW-2016 require and is a velocity collar acceptable for this client?' },
    { id: 'p-api670', name: 'Machinery protection (API 670)', text: 'Define the API 670 machinery protection for {{machine}}: probes per bearing, axial position voting, keyphasor, overspeed, rack modules. Compare Bently Nevada 3500 options.' },
    { id: 'p-std', name: 'What does the client standard say?', text: 'For a {{client}} project, what are the typical requirements for {{topic}}? Name the governing documents and mark what must be confirmed in the controlled copy.' },
    { id: 'p-ko', name: '한국어 질의 템플릿', text: '{{프로젝트 발주처}} 프로젝트에서 {{계기 / 아이템}} 사양을 검토해줘. 서비스는 {{서비스 조건}}. 의견, 근거, 확인사항 순서로.' },
  ];

  const S = { chat: null, chats: [], busy: false, abort: null, files: [], pick: { open: false, items: [], i: 0, start: 0 } };

  // ───────── projects ─────────
  function projects() {
    let list = LS.json('projects', null);
    if (!list) {
      list = [{ id: Store.uid(), name: 'Default project', client: LS.get('ctx.client', 'Saudi Aramco (SAES / SAMSS)'),
        site: LS.get('ctx.site', ''), area: LS.get('ctx.area', ''), notes: LS.get('ctx.notes', '') }];
      LS.setJson('projects', list); LS.set('project', list[0].id);
    }
    return list;
  }
  const activeProject = () => projects().find((p) => p.id === LS.get('project', '')) || projects()[0];
  const projectOf = (chat) => projects().find((p) => p.id === chat?.projectId) || activeProject();
  function projectCtx(p = projectOf(S.chat)) {
    return [`Client / standard basis: ${p.client}`, p.name && `Project / unit: ${p.name}`, p.site && `Site conditions: ${p.site}`,
      p.area && `Area classification / SIL: ${p.area}`, p.notes && `Notes: ${p.notes}`].filter(Boolean).join('\n');
  }
  function renderProjects() {
    const list = projects(); const act = activeProject();
    $('project-list').innerHTML = '';
    for (const p of list) {
      const d = document.createElement('div'); d.className = 'item' + (p.id === act.id ? ' active' : '');
      d.innerHTML = `<div class="it-main"><div class="it-title">${esc(p.name || 'Untitled')}</div><div class="it-sub">${esc(p.client)}</div></div>`;
      const del = mkBtn('🗑', 'Delete project', () => {
        if (list.length < 2) return;
        if (!confirm(`Delete project "${p.name}"? Its chats stay in the history.`)) return;
        LS.setJson('projects', list.filter((x) => x.id !== p.id)); if (p.id === act.id) LS.set('project', list.find((x) => x.id !== p.id).id);
        renderProjects(); renderHeader();
      });
      d.appendChild(Object.assign(document.createElement('div'), { className: 'it-acts' })).appendChild(del);
      d.onclick = () => { LS.set('project', p.id); renderProjects(); if (S.chat && !S.chat.turns.length) S.chat.projectId = p.id; renderHeader(); };
      $('project-list').appendChild(d);
    }
    for (const k of ['name', 'client', 'site', 'area', 'notes']) $(`ctx-${k}`).value = act[k] || '';
  }
  function bindProjectForm() {
    for (const k of ['name', 'client', 'site', 'area', 'notes']) {
      $(`ctx-${k}`).addEventListener('input', () => {
        const list = projects(); const p = list.find((x) => x.id === activeProject().id); p[k] = $(`ctx-${k}`).value;
        LS.setJson('projects', list); renderHeader();
        const it = $('project-list').querySelector('.item.active .it-title'); if (it && k === 'name') it.textContent = p.name || 'Untitled';
      });
    }
    $('btn-new-project').onclick = () => {
      const list = projects(); const p = { id: Store.uid(), name: 'New project', client: 'International codes only', site: '', area: '', notes: '' };
      list.push(p); LS.setJson('projects', list); LS.set('project', p.id); renderProjects(); renderHeader(); $('ctx-name').select();
    };
  }

  // ───────── prompts ─────────
  const prompts = () => LS.json('prompts', null) || DEFAULT_PROMPTS;
  function renderPrompts() {
    const box = $('prompt-list'); box.innerHTML = '';
    for (const p of prompts()) {
      const d = document.createElement('div'); d.className = 'item';
      d.innerHTML = `<div class="it-main"><div class="it-title">${esc(p.name)}</div><div class="it-sub">${esc(p.text.slice(0, 90))}…</div></div>`;
      const acts = document.createElement('div'); acts.className = 'it-acts';
      acts.appendChild(mkBtn('✎', 'Edit', (e) => { e.stopPropagation(); editPrompt(p); }));
      d.appendChild(acts);
      d.onclick = () => usePrompt(p, null);
      box.appendChild(d);
    }
  }
  function editPrompt(p) {
    const dlg = $('dlg-prompt'); const isNew = !p;
    $('dp-title').textContent = isNew ? 'New prompt' : 'Edit prompt';
    $('dp-name').value = p?.name || ''; $('dp-text').value = p?.text || '';
    $('dp-del').hidden = isNew;
    $('dp-save').onclick = () => {
      const list = prompts().slice(); const rec = { id: p?.id || Store.uid(), name: $('dp-name').value.trim() || 'Untitled', text: $('dp-text').value };
      const i = list.findIndex((x) => x.id === rec.id); if (i >= 0) list[i] = rec; else list.push(rec);
      LS.setJson('prompts', list); dlg.close(); renderPrompts();
    };
    $('dp-del').onclick = () => { LS.setJson('prompts', prompts().filter((x) => x.id !== p.id)); dlg.close(); renderPrompts(); };
    $('dp-close').onclick = () => dlg.close();
    dlg.showModal();
  }
  /** insert a prompt; {{variables}} are asked for first. replaceFrom = index of the "/" being replaced */
  function usePrompt(p, replaceFrom, replaceTo = replaceFrom != null ? $('input').selectionStart : null) {
    const vars = [...new Set([...p.text.matchAll(/\{\{([^}]+)\}\}/g)].map((m) => m[1].trim()))];
    const insert = (txt) => {
      const el = $('input');
      if (replaceFrom != null) el.value = el.value.slice(0, replaceFrom) + txt + el.value.slice(replaceTo);   // caret captured before any dialog
      else el.value = el.value ? `${el.value}\n${txt}` : txt;
      autosize(); el.focus();
    };
    closePicker();
    if (!vars.length) { insert(p.text); return; }
    const box = $('dv-fields'); box.innerHTML = '';
    vars.forEach((v, i) => { box.insertAdjacentHTML('beforeend', `<label>${esc(v)}<input data-v="${esc(v)}" ${i === 0 ? 'autofocus' : ''}></label>`); });
    const dlg = $('dlg-vars');
    const ok = () => {
      let t = p.text;
      for (const inp of box.querySelectorAll('input')) t = t.split(`{{${inp.dataset.v}}}`).join(inp.value || `[${inp.dataset.v}]`);
      t = t.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (m, v) => { const inp = box.querySelector(`input[data-v="${CSS.escape(v)}"]`); return inp?.value || `[${v}]`; });
      dlg.close(); insert(t);
    };
    $('dv-ok').onclick = ok; $('dv-close').onclick = () => dlg.close();
    box.onkeydown = (e) => { if (e.key === 'Enter') { e.preventDefault(); ok(); } };
    dlg.showModal();
  }

  // "/" picker in the message box
  function updatePicker() {
    const el = $('input'); const before = el.value.slice(0, el.selectionStart);
    const m = /(^|\s)\/([^\s/]*)$/.exec(before);
    if (!m) { closePicker(); return; }
    const q = m[2].toLowerCase();
    const items = prompts().filter((p) => !q || p.name.toLowerCase().includes(q) || p.text.toLowerCase().includes(q)).slice(0, 8);
    if (!items.length) { closePicker(); return; }
    S.pick = { open: true, items, i: Math.min(S.pick.i, items.length - 1), start: before.length - m[2].length - 1 };
    const pk = $('picker'); pk.hidden = false;
    pk.innerHTML = items.map((p, i) => `<div class="pk-item${i === S.pick.i ? ' on' : ''}" role="option" data-i="${i}"><b>${esc(p.name)}</b><span>${esc(p.text.slice(0, 110))}</span></div>`).join('');
    for (const d of pk.querySelectorAll('.pk-item')) d.onmousedown = (e) => { e.preventDefault(); usePrompt(items[+d.dataset.i], S.pick.start); };
  }
  function closePicker() { S.pick.open = false; S.pick.i = 0; $('picker').hidden = true; }

  // ───────── knowledge ─────────
  function renderKB() {
    const box = $('kb-list');
    if (!kbList.length) { box.innerHTML = '<p class="small muted">No built-in knowledge base found — answers rely on the model and web search.</p>'; return; }
    box.innerHTML = `<p class="small muted">${kbList.length} files · ~${Math.round(kbText.length / 4 / 1000)}k tokens, sent (cached) with every question.</p>`;
    for (const k of kbList) {
      const d = document.createElement('div'); d.className = 'item';
      const words = k.text.split(/\s+/).length; const links = (k.text.match(/\]\(https?:/g) || []).length;
      d.innerHTML = `<div class="it-main"><div class="it-title">KB-${k.n} · ${esc(k.title)}</div><div class="it-sub">${words.toLocaleString()} words · ${links} source links</div></div>`;
      d.onclick = () => { $('dk-title').textContent = `KB-${k.n} · ${k.title}`; $('dk-body').innerHTML = MD.render(k.text); $('dlg-kb').showModal(); };
      box.appendChild(d);
    }
  }

  // ───────── chats ─────────
  function newChat() {
    if (S.busy) return;
    S.chat = { id: Store.uid(), title: 'New chat', projectId: activeProject().id, created: Date.now(), updated: Date.now(), turns: [] };
    S.files = []; renderFiles(); renderChat(); renderChatList(); $('input').focus();
  }
  async function saveChat() {
    if (!S.chat || !S.chat.turns.length) return;
    S.chat.updated = Date.now();
    await Store.chats.put(S.chat);
    const i = S.chats.findIndex((c) => c.id === S.chat.id); if (i >= 0) S.chats[i] = S.chat; else S.chats.unshift(S.chat);
    renderChatList();
  }
  function groupOf(t) {
    const d0 = new Date(); d0.setHours(0, 0, 0, 0); const day = 864e5;
    if (t >= d0.getTime()) return 'Today';
    if (t >= d0.getTime() - day) return 'Yesterday';
    if (t >= d0.getTime() - 7 * day) return 'Previous 7 days';
    return 'Older';
  }
  function renderChatList() {
    const q = $('chat-search').value.trim().toLowerCase();
    const list = S.chats.slice().sort((a, b) => b.updated - a.updated)
      .filter((c) => !q || c.title.toLowerCase().includes(q) || c.turns.some((t) => (t.user.text + (t.asst?.text || '')).toLowerCase().includes(q)));
    const box = $('chat-list'); box.innerHTML = '';
    if (!list.length) { box.innerHTML = `<p class="small muted">${q ? 'No matching chats.' : 'No chats yet.'}</p>`; return; }
    let g = null;
    for (const c of list) {
      const gg = groupOf(c.updated);
      if (gg !== g) { g = gg; box.insertAdjacentHTML('beforeend', `<div class="grp">${g}</div>`); }
      const d = document.createElement('div'); d.className = 'item' + (S.chat?.id === c.id ? ' active' : '');
      const p = projects().find((x) => x.id === c.projectId);
      d.innerHTML = `<div class="it-main"><div class="it-title">${esc(c.title)}</div><div class="it-sub">${esc(p?.name || '')}</div></div>`;
      const acts = document.createElement('div'); acts.className = 'it-acts';
      acts.appendChild(mkBtn('✎', 'Rename', (e) => {
        e.stopPropagation(); const t = prompt('Rename chat', c.title); if (!t) return;
        c.title = t.trim(); Store.chats.put(c); renderChatList(); if (S.chat?.id === c.id) renderHeader();
      }));
      acts.appendChild(mkBtn('🗑', 'Delete', async (e) => {
        e.stopPropagation(); if (!confirm(`Delete "${c.title}"?`)) return;
        await Store.chats.del(c.id); S.chats = S.chats.filter((x) => x.id !== c.id);
        if (S.chat?.id === c.id) newChat(); else renderChatList();
      }));
      d.appendChild(acts);
      d.onclick = () => { if (S.busy) return; S.chat = c; renderChat(); renderChatList(); if (innerWidth < 860) toggleSidebar(false); };
      box.appendChild(d);
    }
  }
  function renderHeader() {
    const p = projectOf(S.chat);
    $('chat-title').textContent = S.chat?.title || 'New chat';
    $('chat-sub').textContent = `${p.name || 'Project'} · ${p.client}`;
    $('ctx-badge').textContent = p.area ? `Context: ${p.client.split(' (')[0]} · ${p.area}` : `Context: ${p.client.split(' (')[0]}`;
    document.title = `${S.chat?.title && S.chat.turns.length ? S.chat.title + ' · ' : ''}I&C Expert`;
  }

  // ───────── message rendering ─────────
  const ICON = { copy: '⧉', edit: '✎', regen: '↻', ok: '✓' };
  function mkBtn(label, title, onclick) {
    const b = document.createElement('button'); b.type = 'button'; b.className = 'act'; b.textContent = label; b.title = title; b.setAttribute('aria-label', title);
    b.onclick = onclick; return b;
  }
  function copyText(t, btn) {
    const done = () => { if (btn) { const o = btn.textContent; btn.textContent = ICON.ok; setTimeout(() => { btn.textContent = o; }, 1500); } };
    try { navigator.clipboard.writeText(t).then(done, () => fallbackCopy(t, done)); } catch { fallbackCopy(t, done); }
  }
  function fallbackCopy(t, done) {
    const ta = document.createElement('textarea'); ta.value = t; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); } catch { /* ignore */ } ta.remove(); done();
  }
  /** answer HTML with copy buttons on code blocks and Copy / CSV on tables */
  function enhance(el) {
    for (const pre of el.querySelectorAll('pre')) {
      if (pre.previousElementSibling?.classList.contains('blk-bar')) continue;
      const bar = document.createElement('div'); bar.className = 'blk-bar';
      bar.appendChild(mkBtn('⧉ Copy', 'Copy code', (e) => copyText(pre.innerText, e.currentTarget)));
      pre.before(bar);
    }
    el.querySelectorAll('.tbl').forEach((w, ti) => {
      if (w.querySelector('.blk-bar')) return;
      const rows = [...w.querySelectorAll('tr')].map((tr) => [...tr.children].map((c) => c.innerText.trim()));
      const bar = document.createElement('div'); bar.className = 'blk-bar';
      bar.appendChild(mkBtn('⧉ Copy table', 'Copy as tab-separated text — paste straight into Excel', (e) => copyText(rows.map((r) => r.join('\t')).join('\n'), e.currentTarget)));
      bar.appendChild(mkBtn('⤓ CSV', 'Download as CSV', () => {
        const csv = '﻿' + rows.map((r) => r.map((c) => `"${c.replace(/"/g, '""')}"`).join(',')).join('\r\n');
        download(new Blob([csv], { type: 'text/csv' }), `${slug(S.chat?.title)}-table-${ti + 1}.csv`);
      }));
      w.prepend(bar);
    });
  }
  function sourcesHtml(content) {
    const seen = new Map();
    for (const b of content || []) if (b.type === 'text') for (const c of b.citations || []) if (c.url && !seen.has(c.url)) seen.set(c.url, c.title || c.url);
    if (!seen.size) return '';
    return `<details class="sources"><summary>Web sources (${seen.size})</summary><ol>${[...seen].map(([u, t]) => `<li><a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(t)}</a></li>`).join('')}</ol></details>`;
  }
  function searchesHtml(content) {
    const qs = (content || []).filter((b) => b.type === 'server_tool_use' && b.input?.query).map((b) => b.input.query);
    return qs.length ? `<div class="searched small muted">🔎 ${qs.map((q) => `“${esc(q)}”`).join(' · ')}</div>` : '';
  }
  function welcome() {
    const p = projectOf(S.chat);
    const starters = prompts().slice(0, 6);
    const div = document.createElement('div'); div.className = 'welcome';
    div.innerHTML = `<h1>I&amp;C Expert</h1>
      <p class="muted">Senior instrumentation &amp; control reviewer for <b>${esc(p.client)}</b> projects. Paste a spec clause, attach a datasheet or describe the service —
      the answer states the opinion first, then the basis (code · client standard · vendor data) and what to verify. Client standards are controlled
      documents: the expert names them but never invents clause text.</p>
      <div class="starters"></div>`;
    const st = div.querySelector('.starters');
    for (const sp of starters) {
      const b = document.createElement('button'); b.className = 'starter';
      b.innerHTML = `<b>${esc(sp.name)}</b><span>${esc(sp.text.replace(/\{\{([^}]+)\}\}/g, '[$1]').slice(0, 120))}</span>`;
      b.onclick = () => usePrompt(sp, null);
      st.appendChild(b);
    }
    return div;
  }
  function renderChat() {
    const log = $('log'); log.innerHTML = '';
    renderHeader();
    if (!S.chat.turns.length) { log.appendChild(welcome()); updateScrollBtns(); return; }
    S.chat.turns.forEach((t, i) => { log.appendChild(userEl(t, i)); log.appendChild(asstEl(t, i)); });
    log.scrollTop = log.scrollHeight; updateScrollBtns();
  }
  function userEl(t, i) {
    const d = document.createElement('div'); d.className = 'msg user'; d.dataset.i = i;
    d.innerHTML = `<div class="who">You</div><div class="body">${MD.render(t.user.text || '_(attachments)_')}${t.user.files?.length ? `<div class="att small muted">📎 ${t.user.files.map(esc).join(', ')}</div>` : ''}</div>`;
    const acts = document.createElement('div'); acts.className = 'acts';
    acts.appendChild(mkBtn(ICON.copy, 'Copy', (e) => copyText(t.user.text, e.currentTarget)));
    acts.appendChild(mkBtn(ICON.edit, 'Edit and resend', () => startEdit(d, i)));
    d.appendChild(acts);
    return d;
  }
  function asstEl(t, i) {
    const d = document.createElement('div'); d.className = 'msg assistant'; d.dataset.i = i;
    const a = t.asst;
    const body = a?.error ? `<p class="err">${esc(a.error)}</p>` : a?.text != null ? MD.render(a.text || '_(no text returned)_') : '<div class="typing"><span></span><span></span><span></span></div>';
    d.innerHTML = `<div class="who">I&amp;C Expert</div><div class="body">${body}</div>${a?.content ? searchesHtml(a.content) + sourcesHtml(a.content) : ''}`;
    enhance(d.querySelector('.body'));
    if (a && (a.text != null || a.error)) {
      const acts = document.createElement('div'); acts.className = 'acts';
      if (a.text) acts.appendChild(mkBtn(ICON.copy, 'Copy answer (Markdown)', (e) => copyText(a.text, e.currentTarget)));
      if (i === S.chat.turns.length - 1) acts.appendChild(mkBtn(ICON.regen, 'Regenerate', () => regenerate()));
      if (a.meta) acts.insertAdjacentHTML('beforeend', `<span class="meta">${esc(a.meta)}</span>`);
      d.appendChild(acts);
    }
    return d;
  }
  function startEdit(el, i) {
    if (S.busy) return;
    const t = S.chat.turns[i]; const body = el.querySelector('.body');
    body.innerHTML = `<textarea class="edit" rows="4"></textarea><div class="row small"><button class="primary sm">Save &amp; submit</button><button class="ghost-btn sm">Cancel</button>${t.user.files?.length ? `<span class="muted">Attachments are kept.</span>` : ''}</div>`;
    const ta = body.querySelector('textarea'); ta.value = t.user.text; ta.focus();
    const [save, cancel] = body.querySelectorAll('button');
    cancel.onclick = () => renderChat();
    save.onclick = () => {
      const text = ta.value.trim(); if (!text) return;
      const blocks = t.user.content.filter((b) => b.type !== 'text');   // keep the attachments
      S.chat.turns = S.chat.turns.slice(0, i);
      run({ content: [...blocks, { type: 'text', text }], text, files: t.user.files });
    };
    ta.onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); save.onclick(); } if (e.key === 'Escape') cancel.onclick(); };
  }
  function regenerate() {
    if (S.busy || !S.chat.turns.length) return;
    const last = S.chat.turns.pop();
    run(last.user);
  }

  // ───────── send / run ─────────
  function apiMessages(turns) {
    const out = [];
    turns.forEach((t, i) => {
      const last = i === turns.length - 1;
      if (!last && !t.asst?.content) return;                    // drop failed turns so roles alternate
      out.push({ role: 'user', content: t.user.content });
      if (!last) out.push({ role: 'assistant', content: t.asst.content });
    });
    return out;
  }
  async function send() {
    const text = $('input').value.trim();
    if (S.busy || (!text && !S.files.length)) return;
    closePicker();
    const files = S.files.splice(0); renderFiles();
    $('input').value = ''; autosize();
    const content = [];
    try { for (const f of files) content.push(await ExpertAPI.fileBlock(f)); } catch (e) { setStatus(`Could not read a file: ${e.message}`); return; }
    content.push({ type: 'text', text: text || 'Please review the attached documents.' });
    run({ content, text, files: files.map((f) => f.name) });
  }
  async function run(user) {
    if (!S.chat.turns.length && S.chat.title === 'New chat') S.chat.title = (user.text || user.files?.[0] || 'Review').replace(/\s+/g, ' ').slice(0, 60);
    const turn = { user, asst: null, at: Date.now() };
    S.chat.turns.push(turn);
    renderChat(); renderChatList();
    const log = $('log'); const el = log.lastElementChild; const body = el.querySelector('.body');
    S.busy = true; S.abort = new AbortController(); stick = true;
    $('btn-send').disabled = true; $('btn-stop').hidden = false;
    const t0 = Date.now(); setStatus('Thinking…');
    try {
      const r = await ExpertAPI.send({
        apiKey: LS.get('key', ''), model: $('q-model').value, effort: $('q-effort').value,
        kbText, projectCtx: projectCtx(), messages: apiMessages(S.chat.turns), webSearch: $('opt-web').checked, signal: S.abort.signal,
        onText: (t) => { body.innerHTML = MD.render(t); follow(); },
        onStatus: (s) => setStatus(s),
      });
      const u = r.usage || {};
      const meta = `${((Date.now() - t0) / 1000).toFixed(0)} s · ${$('q-model').selectedOptions[0].text} · ${(u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0)} in (${u.cache_read_input_tokens || 0} cached) / ${u.output_tokens || 0} out`;
      turn.asst = { content: r.content, text: ExpertAPI.textOf(r.content), meta: meta + (r.stopReason === 'max_tokens' ? ' · cut off' : '') };
      setStatus(`Done · ${meta}`);
    } catch (e) {
      turn.asst = { error: e.name === 'AbortError' ? 'Stopped.' : e.message };
      setStatus(e.name === 'AbortError' ? 'Stopped.' : 'Error');
    } finally {
      S.busy = false; S.abort = null; $('btn-send').disabled = false; $('btn-stop').hidden = true;
      el.replaceWith(asstEl(turn, S.chat.turns.indexOf(turn)));
      // only the last assistant message offers Regenerate
      const prev = log.querySelectorAll('.msg.assistant'); if (prev.length > 1) prev[prev.length - 2].querySelector('.act[title="Regenerate"]')?.remove();
      follow(); await saveChat();
    }
  }

  // ───────── files ─────────
  function addFiles(list) {
    for (const f of list) { if (f.size > 25 * 1024 * 1024) { setStatus(`${f.name}: larger than 25 MB`); continue; } S.files.push(f); }
    renderFiles();
  }
  function renderFiles() {
    const box = $('pending'); box.innerHTML = '';
    S.files.forEach((f, i) => {
      const c = document.createElement('span'); c.className = 'chip';
      c.textContent = `${f.type === 'application/pdf' ? '📄' : f.type.startsWith('image/') ? '🖼' : '📝'} ${f.name}`;
      c.appendChild(mkBtn('✕', 'Remove', () => { S.files.splice(i, 1); renderFiles(); }));
      box.appendChild(c);
    });
  }

  // ───────── scrolling ─────────
  let stick = true;
  function follow() { const log = $('log'); if (stick) log.scrollTop = log.scrollHeight; updateScrollBtns(); }
  function updateScrollBtns() {
    const log = $('log'); const over = log.scrollHeight > log.clientHeight + 8;
    $('btn-top').hidden = !over || log.scrollTop < 40;
    $('btn-bottom').hidden = !over || log.scrollTop + log.clientHeight > log.scrollHeight - 40;
  }

  // ───────── misc ─────────
  function setStatus(s) { $('status').textContent = s; }
  const slug = (s) => (s || 'chat').replace(/[^\w가-힣-]+/g, '_').slice(0, 40);
  function download(blob, name) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  function exportMd() {
    if (!S.chat) return;
    const L = [`# ${S.chat.title}`, '', `_${new Date(S.chat.created).toISOString().slice(0, 16).replace('T', ' ')}_`, '', '## Project context', '', projectCtx(), ''];
    for (const t of S.chat.turns) {
      L.push('## Question', '');
      if (t.user.files?.length) L.push(`Attachments: ${t.user.files.join(', ')}`, '');
      L.push(t.user.text, '', '## Answer', '', t.asst?.text || t.asst?.error || '', '');
      const urls = new Map();
      for (const b of t.asst?.content || []) if (b.type === 'text') for (const c of b.citations || []) if (c.url) urls.set(c.url, c.title || c.url);
      if (urls.size) L.push('Sources:', ...[...urls].map(([u, tt]) => `- [${tt}](${u})`), '');
    }
    download(new Blob([L.join('\n')], { type: 'text/markdown' }), `${slug(S.chat.title)}.md`);
  }
  function autosize() { const el = $('input'); el.style.height = 'auto'; el.style.height = `${Math.min(220, el.scrollHeight)}px`; }
  function toggleSidebar(force) { const app = $('app'); app.classList.toggle('no-side', force === undefined ? !app.classList.contains('no-side') : !force); }
  function setTheme(t) {
    if (t === 'system') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', t);
    LS.set('theme', t);
  }
  function showTab(name) {
    for (const b of document.querySelectorAll('.sw-btn[data-tab]')) b.classList.toggle('active', b.dataset.tab === name);
    for (const s of document.querySelectorAll('.tab')) s.hidden = s.dataset.tab !== name;
    if ($('app').classList.contains('no-side')) toggleSidebar(true);
  }

  function bind() {
    for (const b of document.querySelectorAll('.sw-btn[data-tab]')) b.onclick = () => showTab(b.dataset.tab);
    $('btn-new').onclick = newChat;
    $('chat-search').oninput = renderChatList;
    $('btn-new-prompt').onclick = () => editPrompt(null);
    $('btn-sidebar').onclick = () => toggleSidebar();
    $('btn-export').onclick = exportMd;
    $('btn-help').onclick = () => $('dlg-help').showModal();
    $('dh-close').onclick = () => $('dlg-help').close();
    $('dk-close').onclick = () => $('dlg-kb').close();
    $('btn-theme').onclick = () => { const order = ['system', 'light', 'dark']; setTheme(order[(order.indexOf(LS.get('theme', 'system')) + 1) % 3]); };
    $('btn-settings').onclick = () => { $('set-key').value = LS.get('key', ''); $('dlg-settings').showModal(); };
    $('set-save').onclick = () => { LS.set('key', $('set-key').value.trim()); $('dlg-settings').close(); setStatus('Settings saved.'); };
    $('set-close').onclick = () => $('dlg-settings').close();
    $('q-model').value = LS.get('model', 'claude-opus-5-5'); $('q-model').onchange = (e) => LS.set('model', e.target.value);
    $('q-effort').value = LS.get('effort', 'high'); $('q-effort').onchange = (e) => LS.set('effort', e.target.value);
    $('opt-web').checked = LS.get('web', '1') === '1'; $('opt-web').onchange = (e) => LS.set('web', e.target.checked ? '1' : '0');
    $('btn-send').onclick = send;
    $('btn-stop').onclick = () => S.abort?.abort();
    $('btn-attach').onclick = () => $('file').click();
    $('file').onchange = () => { addFiles($('file').files); $('file').value = ''; };
    $('btn-top').onclick = () => { $('log').scrollTop = 0; };
    $('btn-bottom').onclick = () => { stick = true; follow(); };
    $('log').addEventListener('scroll', () => { const l = $('log'); stick = l.scrollTop + l.clientHeight > l.scrollHeight - 60; updateScrollBtns(); });

    const input = $('input');
    input.addEventListener('input', () => { autosize(); updatePicker(); });
    input.addEventListener('click', updatePicker);
    input.addEventListener('keydown', (e) => {
      if (S.pick.open) {
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          e.preventDefault(); S.pick.i = (S.pick.i + (e.key === 'ArrowDown' ? 1 : -1) + S.pick.items.length) % S.pick.items.length; updatePicker(); return;
        }
        if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); usePrompt(S.pick.items[S.pick.i], S.pick.start); return; }
        if (e.key === 'Escape') { closePicker(); return; }
      }
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) { e.preventDefault(); send(); }
    });

    // drag & drop anywhere on the chat
    const chat = document.querySelector('.chat'); let dragN = 0;
    chat.addEventListener('dragenter', (e) => { if (e.dataTransfer?.types?.includes('Files')) { dragN++; $('dropzone').hidden = false; } });
    chat.addEventListener('dragleave', () => { if (--dragN <= 0) { dragN = 0; $('dropzone').hidden = true; } });
    chat.addEventListener('dragover', (e) => e.preventDefault());
    chat.addEventListener('drop', (e) => { e.preventDefault(); dragN = 0; $('dropzone').hidden = true; addFiles(e.dataTransfer.files); });
    input.addEventListener('paste', (e) => { const f = [...(e.clipboardData?.files || [])]; if (f.length) { e.preventDefault(); addFiles(f); } });

    // hotkeys (Ctrl/Cmd + Shift + key), Esc to stop
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && S.busy) { S.abort?.abort(); return; }
      if (!(e.ctrlKey || e.metaKey) || !e.shiftKey) return;
      const k = e.key.toLowerCase();
      if (k === 'o') { e.preventDefault(); newChat(); }
      else if (k === 's') { e.preventDefault(); toggleSidebar(); }
      else if (k === 'l') { e.preventDefault(); input.focus(); }
      else if (k === '/' || k === '?') { e.preventDefault(); $('dlg-help').showModal(); }
    });
  }

  async function init() {
    setTheme(LS.get('theme', 'system'));
    if (innerWidth < 860) toggleSidebar(false);
    bindProjectForm(); bind();
    renderProjects(); renderPrompts(); renderKB();
    S.chats = await Store.chats.all();
    renderChatList();
    newChat();
  }
  init();
  window.ICX = { S, send, projectCtx, newChat };
})();
