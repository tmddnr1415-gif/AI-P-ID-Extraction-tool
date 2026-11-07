/* Claude Messages API client for the I&C expert chat (browser, raw HTTP, streaming).
 *
 * - System prompt = expert persona + answer rules + the built-in knowledge base (prompt-cached).
 * - Project context (client, site, spec files) rides in a second system block.
 * - Server-side web search fills gaps and checks recent vendor data; citations are kept.
 * - The full assistant content (thinking, server_tool_use, web_search_tool_result, text + citations)
 *   is rebuilt from the stream and appended unchanged, so multi-turn history stays valid.
 * - pause_turn is resumed automatically (up to 4 times); a server-side fallback restarts collection.
 */
'use strict';

const ExpertAPI = (() => {
  const API_URL = 'https://api.anthropic.com/v1/messages';

  const PERSONA = `You are a senior Instrumentation & Control (I&C) lead engineer with 25+ years on oil & gas, LNG,
refinery and petrochemical EPC projects in the Middle East — Saudi Aramco, QatarEnergy / QatarEnergy LNG, ADNOC,
Shell-standard and KOC projects. You know field instruments, control valves, ESD/on-off valves, MOVs, PSVs,
analyzers, F&G, machinery protection, DCS/SIS/F&G systems, cabinets, cabling, hook-ups and the vendor landscape
(Emerson, Yokogawa, Honeywell, Bently Nevada, WIKA, Endress+Hauser, Siemens, ABB, Krohne, VEGA, Rotork, Valmet …).

People bring you project specifications, datasheets, P&ID notes and questions. Act as the expert reviewer:
give a clear opinion and a straight answer, then the basis.

# Sources and honesty
1. Use the <knowledge_base> below first. Cite it as [KB-nn §section] (nn = file number).
2. Use web search when the knowledge base does not cover the point, when current vendor data / model status /
   editions matter, or when the user asks. Cite web sources with the citations the tool returns.
3. Client standards (Saudi Aramco SAES/SAMSS/SAEP, QatarEnergy, ADNOC, Shell DEP) are controlled documents.
   Never invent clause numbers or quote text you do not have. Say what is commonly required and tell the user
   to confirm against the project-controlled copy (name the document if known).
4. Separate clearly: **Requirement** (code / client standard) · **Recommendation** (engineering judgement) ·
   **Vendor data** (catalogue values — confirm with the vendor's certified datasheet).
5. If the spec is ambiguous or data is missing (fluid, ranges, design pressure/temperature, area class, SIL),
   say exactly what you need and give a provisional answer with the assumption stated.
6. Safety-related topics (SIS/SIL, hazardous areas, PSVs, F&G, sour service): flag the risk and the check.
   You support the engineer of record; you do not replace design verification or client approval.

# Answer format (Markdown)
- Start with **Answer** — 1–5 sentences, the opinion/decision.
- Then **Basis** — bullets with citations.
- Then **Check / risks** — what to verify, typical client review comments.
- When reviewing a spec or datasheet, add a findings table:
  | # | Item / clause | Spec says | Expert opinion | Basis | Severity (High/Med/Low) | Action |
  followed by **Open questions** for the client/vendor.
- When comparing vendors, use a table (model · key specs · approvals/SIL · fit · notes) and state that final
  selection follows the project AVL / approved manufacturer list.
- Reply in the user's language (Korean if they write Korean). Keep standard names, model numbers and
  engineering terms in English. Use SI units with imperial in brackets where the project uses both.
- Be concise; no filler. Numbers over adjectives.`;

  function systemBlocks(kbText, projectCtx) {
    const blocks = [{
      type: 'text',
      text: `${PERSONA}\n\n<knowledge_base>\n${kbText}\n</knowledge_base>`,
      cache_control: { type: 'ephemeral' },
    }];
    if (projectCtx && projectCtx.trim()) blocks.push({ type: 'text', text: `# Current project context (from the user)\n${projectCtx}` });
    return blocks;
  }

  async function fileBlock(file) {
    const b64 = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(String(r.result).split(',')[1]);
      r.onerror = () => rej(r.error);
      r.readAsDataURL(file);
    });
    if (file.type === 'application/pdf') {
      return { type: 'document', source: { type: 'base64', media_type: 'application/pdf', data: b64 }, title: file.name };
    }
    if (file.type.startsWith('image/')) {
      const mt = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(file.type) ? file.type : 'image/png';
      return { type: 'image', source: { type: 'base64', media_type: mt, data: b64 } };
    }
    const text = await file.text();
    return { type: 'document', source: { type: 'text', media_type: 'text/plain', data: text }, title: file.name };
  }

  /**
   * Send the conversation; stream the reply.
   * messages: [{role, content}] — the last one is the new user turn.
   * onText(fullTextSoFar), onStatus(str) — UI callbacks.
   * Returns { content (assistant blocks), usage, stopReason }.
   */
  async function send({ apiKey, model, effort, kbText, projectCtx, messages, webSearch, signal, onText, onStatus }) {
    if (!apiKey) throw new Error('Enter your Anthropic API key in ⚙ Settings.');
    let assistant = [];
    let usage = {};
    for (let round = 0; round < 5; round++) {
      const body = {
        model,
        max_tokens: 32000,
        stream: true,
        thinking: { type: 'adaptive' },
        output_config: { effort },
        system: systemBlocks(kbText, projectCtx),
        cache_control: { type: 'ephemeral' },
        fallbacks: 'default',
        messages: assistant.length ? [...messages, { role: 'assistant', content: assistant }] : messages,
      };
      if (webSearch) body.tools = [{ type: 'web_search_20260209', name: 'web_search', max_uses: 6 }];
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
      if (!res.ok) throw new Error(await describeError(res));
      const prior = assistant;
      const r = await consume(res, signal, (blocks) => onText?.(textOf([...prior, ...blocks])), onStatus);
      assistant = [...prior, ...r.blocks];
      for (const [k, v] of Object.entries(r.usage || {})) if (typeof v === 'number') usage[k] = (usage[k] || 0) + v;
      if (r.stopReason === 'pause_turn') { onStatus?.('Searching the web… (continuing)'); continue; }
      if (r.stopReason === 'refusal') throw new Error('The model declined this request (refusal).');
      return { content: assistant, usage, stopReason: r.stopReason };
    }
    return { content: assistant, usage, stopReason: 'pause_turn' };
  }

  const textOf = (blocks) => blocks.filter((b) => b.type === 'text').map((b) => b.text).join('');

  /** rebuild complete content blocks from the SSE stream */
  async function consume(res, signal, onBlocks, onStatus) {
    const reader = res.body.getReader(); const dec = new TextDecoder();
    let buf = ''; let blocks = []; let json = {}; let usage = {}; let stopReason = null;
    for (;;) {
      if (signal?.aborted) { await reader.cancel(); throw new DOMException('aborted', 'AbortError'); }
      const { done, value } = await reader.read(); if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n\n')) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const line = chunk.split('\n').find((l) => l.startsWith('data:')); if (!line) continue;
        let ev; try { ev = JSON.parse(line.slice(5).trim()); } catch { continue; }
        switch (ev.type) {
          case 'message_start':
            blocks = []; json = {};                 // a fallback model starts a fresh message
            usage = { ...(ev.message?.usage || {}) };
            break;
          case 'content_block_start': {
            const b = JSON.parse(JSON.stringify(ev.content_block));
            if (b.type === 'text' && !b.text) b.text = '';
            if (b.type === 'thinking' && b.thinking == null) b.thinking = '';
            if (b.type === 'server_tool_use') { json[ev.index] = ''; onStatus?.('Searching the web…'); }
            if (b.type === 'web_search_tool_result') onStatus?.(`Reading ${Array.isArray(b.content) ? b.content.length : 0} search results…`);
            blocks[ev.index] = b;
            break;
          }
          case 'content_block_delta': {
            const b = blocks[ev.index]; const d = ev.delta; if (!b) break;
            if (d.type === 'text_delta') { b.text += d.text; onBlocks(blocks.filter(Boolean)); }
            else if (d.type === 'citations_delta') (b.citations ||= []).push(d.citation);
            else if (d.type === 'thinking_delta') b.thinking += d.thinking;
            else if (d.type === 'signature_delta') b.signature = (b.signature || '') + d.signature;
            else if (d.type === 'input_json_delta') json[ev.index] = (json[ev.index] || '') + d.partial_json;
            break;
          }
          case 'content_block_stop': {
            const b = blocks[ev.index];
            if (b && b.type === 'server_tool_use' && json[ev.index]) { try { b.input = JSON.parse(json[ev.index]); } catch { /* keep */ } }
            break;
          }
          case 'message_delta':
            if (ev.delta?.stop_reason) stopReason = ev.delta.stop_reason;
            if (ev.usage) usage = { ...usage, ...ev.usage };
            break;
          case 'error':
            throw new Error(ev.error?.message || 'Streaming error');
          default:
        }
      }
    }
    return { blocks: blocks.filter(Boolean), usage, stopReason };
  }

  async function describeError(res) {
    let msg = '';
    try { const j = await res.json(); msg = j?.error?.message || JSON.stringify(j); } catch { msg = await res.text().catch(() => ''); }
    const tip = { 400: 'Check the request (file type / size).', 401: 'Check the API key.', 404: 'Check the model ID.', 413: 'Attachments too large.', 429: 'Rate limited — try again shortly.', 529: 'API overloaded — try again shortly.' }[res.status];
    return `HTTP ${res.status} — ${msg}${tip ? '\n' + tip : ''}`;
  }

  return { send, fileBlock, textOf, PERSONA };
})();
