/* Small, safe Markdown → HTML renderer for chat answers (escape first, then format).
 * Supports headings, bold/italic, inline code, code blocks, links, bullet/numbered lists, tables, rules, quotes. */
'use strict';

const MD = (() => {
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  function inline(s) {
    let t = esc(s);
    t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
    t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
    t = t.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    t = t.replace(/\[(KB-\d+[^\]]*)\]/g, '<span class="kbref">$1</span>');
    return t;
  }
  function render(src) {
    const lines = String(src || '').replace(/\r/g, '').split('\n');
    const out = []; let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (/^```/.test(l)) {
        const buf = []; i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        i++; out.push(`<pre><code>${esc(buf.join('\n'))}</code></pre>`); continue;
      }
      if (/^\s*\|.*\|\s*$/.test(l) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        const row = (r) => r.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
        const head = row(l); i += 2; const body = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) body.push(row(lines[i++]));
        out.push(`<div class="tbl"><table><thead><tr>${head.map((h) => `<th>${inline(h)}</th>`).join('')}</tr></thead><tbody>${
          body.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
        continue;
      }
      let m;
      if ((m = /^(#{1,4})\s+(.*)$/.exec(l))) { out.push(`<h${m[1].length + 2}>${inline(m[2])}</h${m[1].length + 2}>`); i++; continue; }
      if (/^\s*(-{3,}|\*{3,})\s*$/.test(l)) { out.push('<hr>'); i++; continue; }
      if (/^\s*>\s?/.test(l)) {
        const buf = []; while (i < lines.length && /^\s*>\s?/.test(lines[i])) buf.push(lines[i++].replace(/^\s*>\s?/, ''));
        out.push(`<blockquote>${inline(buf.join(' '))}</blockquote>`); continue;
      }
      if (/^\s*([-*+]|\d+[.)])\s+/.test(l)) {
        const ordered = /^\s*\d/.test(l); const items = [];
        while (i < lines.length && /^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) {
          let it = lines[i++].replace(/^\s*([-*+]|\d+[.)])\s+/, '');
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*+]|\d+[.)])\s+/.test(lines[i])) it += ' ' + lines[i++].trim();
          items.push(`<li>${inline(it)}</li>`);
        }
        out.push(ordered ? `<ol>${items.join('')}</ol>` : `<ul>${items.join('')}</ul>`); continue;
      }
      if (!l.trim()) { i++; continue; }
      const buf = [l]; i++;
      while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*([-*+]|\d+[.)])\s+|\s*\|.*\|\s*$|\s*>)/.test(lines[i])) buf.push(lines[i++]);
      out.push(`<p>${inline(buf.join(' '))}</p>`);
    }
    return out.join('\n');
  }
  return { render, esc };
})();
