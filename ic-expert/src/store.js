/* Persistence: chats in IndexedDB (they can carry attachments), projects / prompts / settings in localStorage.
 * Every access is guarded: in a private window or with storage blocked the app keeps working in memory. */
'use strict';

const Store = (() => {
  const LS = {
    get(k, d) { try { const v = localStorage.getItem(`icx.${k}`); return v == null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(`icx.${k}`, v); } catch { /* unavailable */ } },
    json(k, d) { try { const v = localStorage.getItem(`icx.${k}`); return v ? JSON.parse(v) : d; } catch { return d; } },
    setJson(k, v) { try { localStorage.setItem(`icx.${k}`, JSON.stringify(v)); } catch { /* unavailable */ } },
  };

  let dbp = null;
  const mem = new Map();
  function db() {
    if (dbp) return dbp;
    dbp = new Promise((res) => {
      try {
        const r = indexedDB.open('ic-expert', 1);
        r.onupgradeneeded = () => r.result.createObjectStore('chats', { keyPath: 'id' });
        r.onsuccess = () => res(r.result);
        r.onerror = () => res(null);
      } catch { res(null); }
    });
    return dbp;
  }
  async function tx(mode, fn) {
    const d = await db();
    if (!d) return fn(null);
    return new Promise((res, rej) => {
      const t = d.transaction('chats', mode); const st = t.objectStore('chats');
      const out = fn(st);
      t.oncomplete = () => res(out?.result ?? out);
      t.onerror = () => rej(t.error);
    });
  }
  const chats = {
    async all() {
      const d = await db();
      if (!d) return [...mem.values()];
      return new Promise((res) => {
        const r = d.transaction('chats').objectStore('chats').getAll();
        r.onsuccess = () => res(r.result || []); r.onerror = () => res([...mem.values()]);
      });
    },
    async put(c) { mem.set(c.id, c); try { await tx('readwrite', (st) => st && st.put(c)); } catch { /* memory only */ } },
    async del(id) { mem.delete(id); try { await tx('readwrite', (st) => st && st.delete(id)); } catch { /* memory only */ } },
  };
  const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
  return { LS, chats, uid };
})();
