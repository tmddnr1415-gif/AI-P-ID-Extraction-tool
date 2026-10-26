/* hotfix108 — 절전모드 (P&ID 분석 · LOGIC 검토 · 판넬 공간확보 · DCS 그래픽 공용).
 *
 * 서버(8000)가 꺼져 있어도 이 PC 에 보관된 화면·자료로 계속 보고 고친다.  고친 것(서버에 쓰는 요청)은 이 브라우저의
 * 대기열(IndexedDB `pid-offline`)에 **그대로** 보관했다가, 서버가 켜지면 **보관한 순서대로 다시 보내 서버 값을 덮어쓴다**
 * (마지막에 쓴 사람이 이긴다 — 사용자 지시 "서버 켜지면 서버에 덮어쓰기").
 *
 *  · 이 파일은 각 화면의 다른 스크립트보다 **먼저** 실린다 (`window.fetch` 를 가장 안쪽에서 감싼다).
 *  · 판정 0 — 요청을 보관하고 되보낼 뿐, 값을 바꾸지 않는다.  요청에 `X-Offline-Replay`(보관한 시각)를 붙여 서버가 안다.
 *  · 서버가 켜져야만 되는 일(분석 · 시뮬레이션 · Excel · 제안 · 삭제)은 보관하지 않고 그 자리에서 사람 말로 거절한다.
 *  · 화면마다 `OFFLINE.synth.push(fn)` 으로 보관한 요청의 **임시 응답**을 만들고(그 화면이 바로 보이게),
 *    `OFFLINE.prefetchUrls = () => [...]` 로 [절전 대비 보관] 이 담을 자료를 댄다.
 *  · 띠(`#offline-banner`)는 이 파일이 혼자 그린다 — 꺼짐 · 보관 N건 · 되보내는 중 · 덮어씀 · 못 보낸 것. */
(function () {
  "use strict";
  if (window.OFFLINE) return;
  const scriptEl = document.currentScript;
  const APP = (scriptEl && scriptEl.dataset.app) || "pid";
  const LS_KEY = "pid.offline.down";
  const LS_LAST = "pid.offline.lastReplay";
  const O = window.OFFLINE = {
    app: APP, down: false, ready: false, queue: [], failed: [], replaying: false, sw: null,
    synth: [], prefetchUrls: null, prefetching: null, listeners: {},
    on(ev, fn) { (O.listeners[ev] = O.listeners[ev] || []).push(fn); },
  };
  const emit = (ev, d) => { (O.listeners[ev] || []).forEach((f) => { try { f(d); } catch (e) { /* 듣는 쪽 결함은 여기 일이 아니다 */ } });
    try { window.dispatchEvent(new CustomEvent("offline:" + ev, { detail: d })); } catch (e) { /* 옛 브라우저 */ } };
  const fetch0 = window.fetch.bind(window);
  O.fetch0 = fetch0;

  /* ---------------- 무엇을 보관하나 — 화면마다 서버가 켜져야 하는 일(NO)만 적고 나머지 쓰기는 전부 보관 */
  const NO = {
    pid: /^\/jobs\/?(\?|$)|\/(cancel|reanalyse|propose|preview|diagnostic|snapshot|save|revision|legend_profile|axis_text|titleblock|teach|rows\/[^/]+\/copy)(\/|\?|$)|^\/jobs\/[^/]+\/rows(\?|$)|^\/templates|^\/jobs\/[^/]+$|^\/projects\/[^/]+$|^\/reports\/|^\/symbols/,
    logic: /\/(simulate|press|scenario|trace|sequence|aop|grouptest|teach|sample)(\/|\?|$)|^\/logic\/api\/jobs\/?(\?|$)|^\/logic\/api\/jobs\/[^/]+$|^\/logic\/api\/projects\/[^/]+$/,
    space: /\/import_dashboard/,
    dcs: /\/render(\/|\?|$)/,
  };
  const QUEUE_METHODS = new Set(["POST", "PATCH", "PUT", "DELETE"]);
  function queueable(method, path) {
    if (!QUEUE_METHODS.has(method)) return false;
    const app = path.startsWith("/logic/") ? "logic" : path.startsWith("/space/") ? "space" : path.startsWith("/dcs/") ? "dcs" : "pid";
    // 삭제는 '되돌릴 수 없는 일' 이라 보관하지 않는다 — 단 행 삭제(rows_delete · 노트)는 표시뿐이라 보관한다
    if (method === "DELETE" && !/\/(notes|rows)\//.test(path)) return false;
    return !NO[app].test(path);
  }

  /* ---------------- 대기열 (IndexedDB · 없으면 localStorage) */
  const DB_NAME = "pid-offline", STORE = "queue", FAILED = "failed";
  let dbp = null;
  function db() {
    if (dbp) return dbp;
    dbp = new Promise((res, rej) => {
      if (!window.indexedDB) return rej(new Error("no idb"));
      const r = indexedDB.open(DB_NAME, 1);
      r.onupgradeneeded = () => { const d = r.result; if (!d.objectStoreNames.contains(STORE)) d.createObjectStore(STORE, { keyPath: "id", autoIncrement: true }); if (!d.objectStoreNames.contains(FAILED)) d.createObjectStore(FAILED, { keyPath: "id" }); };
      r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error);
    });
    return dbp;
  }
  function tx(store, mode, fn) {
    return db().then((d) => new Promise((res, rej) => {
      const t = d.transaction(store, mode), s = t.objectStore(store);
      let out; try { out = fn(s); } catch (e) { rej(e); return; }
      t.oncomplete = () => res(out && out.result !== undefined ? out.result : out);
      t.onerror = () => rej(t.error);
    }));
  }
  const lsKey = "pid.offline.queue";
  async function allQueued() {
    try { return await tx(STORE, "readonly", (s) => s.getAll()); }
    catch (e) { try { return JSON.parse(localStorage.getItem(lsKey) || "[]"); } catch (e2) { return []; } }
  }
  async function allFailed() {
    try { return await tx(FAILED, "readonly", (s) => s.getAll()); } catch (e) { return []; }
  }
  async function put(item) {
    try { item.id = await tx(STORE, "readwrite", (s) => s.add(item)); }
    catch (e) { const q = JSON.parse(localStorage.getItem(lsKey) || "[]"); item.id = Date.now(); q.push(item); localStorage.setItem(lsKey, JSON.stringify(q)); }
    O.queue = await allQueued(); render();
    return item;
  }
  async function drop(id) {
    try { await tx(STORE, "readwrite", (s) => s.delete(id)); }
    catch (e) { const q = JSON.parse(localStorage.getItem(lsKey) || "[]").filter((x) => x.id !== id); localStorage.setItem(lsKey, JSON.stringify(q)); }
  }
  async function fail(item, why, status) {
    await drop(item.id);
    try { await tx(FAILED, "readwrite", (s) => s.put({ ...item, why, status, failedAt: Date.now() })); } catch (e) { /* 없으면 띠에만 */ }
  }
  O.discardFailed = async (id) => { try { await tx(FAILED, "readwrite", (s) => s.delete(id)); } catch (e) { /* */ } O.failed = await allFailed(); render(); };
  O.retryFailed = async (id) => {
    const f = (await allFailed()).find((x) => x.id === id); if (!f) return;
    await O.discardFailed(id); delete f.why; delete f.status; delete f.failedAt; delete f.id; await put(f); replay();
  };
  O.discardQueued = async (id) => { await drop(id); O.queue = await allQueued(); render(); };

  /* ---------------- 서버 상태 */
  let probeTimer = null;
  function setDown(down, why) {
    if (O.down === down) return;
    O.down = down;
    try { localStorage.setItem(LS_KEY, down ? String(Date.now()) : ""); } catch (e) { /* */ }
    if (O.sw) O.sw.postMessage({ type: "offline-mode", down });
    render();
    emit(down ? "down" : "up", { why });
    if (down) { if (!probeTimer) probeTimer = setInterval(probe, 10000); }
    else { if (probeTimer) { clearInterval(probeTimer); probeTimer = null; } replay(); }
  }
  O.setDown = setDown;
  async function probe() {
    try {
      const c = new AbortController(); const t = setTimeout(() => c.abort(), 5000);
      const r = await fetch0("/version", { cache: "no-store", signal: c.signal });
      clearTimeout(t);
      if (r.ok) setDown(false, "probe");
    } catch (e) { setDown(true, "probe"); }
  }
  O.probe = probe;

  /* ---------------- fetch 감싸기 — 쓰기 요청을 보관한다 */
  function headersOf(init, input) {
    const h = {};
    const src = (init && init.headers) || (input && input.headers);
    if (!src) return h;
    if (src instanceof Headers) src.forEach((v, k) => { h[k] = v; });
    else if (Array.isArray(src)) src.forEach(([k, v]) => { h[k] = v; });
    else Object.assign(h, src);
    return h;
  }
  function synthesize(item) {
    let body = {};
    for (const fn of O.synth) { try { const r = fn(item); if (r) { body = r; break; } } catch (e) { /* 합성 결함은 보관을 막지 않는다 */ } }
    const out = Object.assign({ ok: true, offline: true, queued: true, queued_at: item.at }, body);
    return new Response(JSON.stringify(out), { status: 200, headers: { "Content-Type": "application/json; charset=utf-8", "X-Offline-Queued": "1" } });
  }
  function refuse(path) {
    const d = { detail: "절전모드 — 서버가 켜져야 할 수 있는 일입니다 (분석 · 시뮬레이션 · 내보내기 · 제안 · 삭제).  고친 값은 보관됩니다.", offline: true, url: path };
    return new Response(JSON.stringify(d), { status: 503, headers: { "Content-Type": "application/json; charset=utf-8", "X-Offline": "refused" } });
  }
  async function bodyText(input, init) {
    if (init && init.body !== undefined && init.body !== null) {
      if (typeof init.body === "string") return init.body;
      if (init.body instanceof URLSearchParams) return init.body.toString();
      return null;                                   // FormData · Blob 은 보관하지 않는다 (업로드)
    }
    if (input instanceof Request) { try { return await input.clone().text(); } catch (e) { return null; } }
    return "";
  }
  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : (input && input.url) || String(input);
    let u; try { u = new URL(url, location.href); } catch (e) { return fetch0(input, init); }
    const method = String((init && init.method) || (input && input.method) || "GET").toUpperCase();
    if (u.origin !== location.origin || !QUEUE_METHODS.has(method)) {
      const p = fetch0(input, init);
      p.catch((e) => { if (e && e.name !== "AbortError" && u.origin === location.origin) setDown(true, "get"); });
      return p;
    }
    const path = u.pathname + u.search;
    const canQueue = queueable(method, u.pathname);
    const text = canQueue ? await bodyText(input, init) : null;
    const item = { app: APP, method, url: path, headers: headersOf(init, input), body: text, at: Date.now(), page: location.pathname };
    const ready = canQueue && text !== null;
    for (const fn of O.synth) { try { fn(item, "before"); } catch (e) { /* */ } }   // 화면이 id 를 미리 정할 자리 (판넬 · 메모)
    if (item.body !== text && init) init = Object.assign({}, init, { body: item.body });
    if (O.down) return ready ? synthesize(await put(item)) : refuse(path);
    try {
      const c = new AbortController(); const t = setTimeout(() => c.abort(), 12000);
      const r = await fetch0(input, Object.assign({}, init || {}, { signal: (init && init.signal) || c.signal }));
      clearTimeout(t);
      return r;
    } catch (e) {
      if (e && e.name === "AbortError" && init && init.signal) throw e;     // 화면이 스스로 끊은 요청
      setDown(true, "write");
      if (ready) return synthesize(await put(item));
      throw e;
    }
  };

  /* ---------------- 서버가 켜지면 — 보관한 순서대로 다시 보내 덮어쓴다 */
  async function replayOnce() {
    const items = (await allQueued()).sort((a, b) => a.id - b.id);
    let sent = 0, failed = 0;
    for (const it of items) {
      try {
        const c = new AbortController(); const t = setTimeout(() => c.abort(), 30000);
        const r = await fetch0(it.url, { method: it.method, headers: Object.assign({}, it.headers, { "X-Offline-Replay": String(it.at), "X-Offline-App": it.app }),
                                        body: it.body === "" ? undefined : it.body, signal: c.signal, cache: "no-store" });
        clearTimeout(t);
        if (r.ok) { await drop(it.id); sent++; }
        else if (r.status >= 500) { setDown(true, "replay"); break; }
        else { let why = `서버 응답 ${r.status}`; try { why = (await r.json()).detail || why; } catch (e) { /* */ } await fail(it, why, r.status); failed++; }
      } catch (e) { setDown(true, "replay"); break; }
    }
    O.queue = await allQueued(); O.failed = await allFailed();
    return { sent, failed, left: O.queue.length };
  }
  async function replay() {
    if (O.replaying) return;
    if (!(await allQueued()).length) { O.failed = await allFailed(); render(); return; }
    O.replaying = true; render();
    const run = async () => {
      let r = { sent: 0, failed: 0, left: 0 };
      try { r = await replayOnce(); } finally { O.replaying = false; }
      if (r.sent || r.failed) {
        O.lastReplay = Object.assign({ at: Date.now() }, r);
        try { localStorage.setItem(LS_LAST, JSON.stringify(O.lastReplay)); } catch (e) { /* */ }   // 다른 탭도 같은 결과를 보인다
        emit("replayed", O.lastReplay);
      }
      render();
    };
    if (navigator.locks && navigator.locks.request) await navigator.locks.request("pid-offline-replay", run);
    else await run();
  }
  O.replay = replay;

  /* ---------------- 절전 대비 보관 (이 화면이 댄 주소를 서비스워커가 담는다) */
  O.prefetch = async function () {
    const urls = typeof O.prefetchUrls === "function" ? (await O.prefetchUrls()) || [] : [];
    if (!urls.length) { O.prefetching = { done: 0, failed: 0, total: 0, finished: true, note: "보관할 자료가 없습니다 — 결과를 먼저 여세요" }; render(); return; }
    if (!O.sw) { O.prefetching = { done: 0, failed: urls.length, total: urls.length, finished: true, note: "이 브라우저는 보관을 지원하지 않습니다 (http 주소로 여세요)" }; render(); return; }
    O.prefetching = { done: 0, failed: 0, total: urls.length }; render();
    O.sw.postMessage({ type: "prefetch", urls });
  };

  /* ---------------- 서비스워커 */
  async function registerSw() {
    if (!("serviceWorker" in navigator) || location.protocol === "file:") return;
    try {
      const reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
      await navigator.serviceWorker.ready;
      O.sw = reg.active || navigator.serviceWorker.controller || (reg.installing || reg.waiting);
      navigator.serviceWorker.addEventListener("controllerchange", () => { O.sw = navigator.serviceWorker.controller; });
      navigator.serviceWorker.addEventListener("message", (ev) => {
        const d = ev.data || {};
        if (d.type === "net") setDown(!!d.down, "sw");
        else if (d.type === "prefetch") { O.prefetching = d; render(); if (d.finished) emit("prefetched", d); }
        else if (d.type === "stats") { O.stats = d; render(); }
      });
      try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (e) { /* */ }
      if (O.sw) O.sw.postMessage({ type: "offline-mode", down: O.down });
    } catch (e) { O.swError = String(e && e.message || e); }
  }

  /* ---------------- 띠 */
  let bannerEl = null, listEl = null;
  function fmt(t) { const d = new Date(t); return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`; }
  function what(it) {
    const p = it.url.split("?")[0];
    const m = p.match(/\/(rows_edit|rows_delete|qty_bulk|verdicts|memo|pins|multipliers|sheet_numbers|review|restore|axis|overrides\/[a-z]+|saves|notes|projects|voc|reports|mark)/);
    return (it.method === "DELETE" ? "지움 " : "") + (m ? m[1] : p.split("/").slice(-1)[0]) + (it.app === "logic" ? " (LOGIC)" : it.app === "space" ? " (판넬)" : "");
  }
  function ensure() {
    if (bannerEl) return bannerEl;
    bannerEl = document.createElement("div");
    bannerEl.id = "offline-banner";
    bannerEl.setAttribute("role", "status");
    // 화면 위에 떠 있는 알약 — 머리줄을 덮지 않게 가운데 좁게 (전체 폭 띠는 P&ID 머리줄 첫 줄을 가렸다 · 시뮬레이션 캡처)
    bannerEl.style.cssText = "position:fixed;top:6px;left:50%;transform:translateX(-50%);max-width:min(960px,94vw);z-index:100000;display:none;"
      + "align-items:center;gap:10px;flex-wrap:wrap;padding:6px 14px;border-radius:999px;font:13px/1.4 'Malgun Gothic',system-ui,sans-serif;"
      + "color:#fff;background:#5b4a1f;box-shadow:0 3px 10px rgba(0,0,0,.35)";
    bannerEl.innerHTML = '<span id="ob-icon">⏾</span><b id="ob-msg"></b><span id="ob-sub" style="opacity:.9"></span>'
      + '<span style="flex:1"></span>'
      + '<button id="ob-list" type="button" style="font:inherit;padding:2px 9px;border:1px solid rgba(255,255,255,.6);background:transparent;color:#fff;border-radius:4px;cursor:pointer">보관된 변경</button>'
      + '<button id="ob-keep" type="button" style="font:inherit;padding:2px 9px;border:1px solid rgba(255,255,255,.6);background:transparent;color:#fff;border-radius:4px;cursor:pointer">⏾ 절전 대비 보관</button>'
      + '<button id="ob-retry" type="button" style="font:inherit;padding:2px 9px;border:1px solid rgba(255,255,255,.6);background:transparent;color:#fff;border-radius:4px;cursor:pointer">서버 다시 확인</button>'
      + '<button id="ob-x" type="button" title="접기" style="font:inherit;border:0;background:transparent;color:#fff;cursor:pointer">✕</button>';
    document.body.appendChild(bannerEl);
    bannerEl.querySelector("#ob-list").onclick = showList;
    bannerEl.querySelector("#ob-keep").onclick = () => O.prefetch();
    bannerEl.querySelector("#ob-retry").onclick = () => { probe(); replay(); };
    bannerEl.querySelector("#ob-x").onclick = () => { bannerEl.dataset.folded = "1"; bannerEl.style.display = "none"; };
    return bannerEl;
  }
  let lastState = "";
  function render() {
    if (!document.body) { document.addEventListener("DOMContentLoaded", render, { once: true }); return; }
    const b = ensure();
    const nq = O.queue.length, nf = O.failed.length, p = O.prefetching;
    let msg = "", sub = "", bg = "#5b4a1f", show = false, state;
    if (O.down) {
      show = true; state = "down";
      msg = "절전모드 — 서버에 연결할 수 없습니다";
      sub = `이 PC 에 보관된 자료로 봅니다 · 고친 값은 보관했다가 서버가 켜지면 서버에 덮어씁니다${nq ? ` · 보관된 변경 ${nq}건` : ""}`;
    } else if (O.replaying) {
      show = true; state = "replay"; bg = "#1d4f91";
      msg = "서버 연결됨 — 보관한 변경을 서버에 덮어쓰는 중…"; sub = `${nq}건`;
    } else if (nq) {
      show = true; state = "queued"; bg = "#1d4f91";
      msg = `보관된 변경 ${nq}건 — 서버에 아직 안 보냈습니다`; sub = "[서버 다시 확인] 을 누르거나 잠시 기다리세요";
    } else if (nf) {
      show = true; state = "failed"; bg = "#8a2a1d";
      msg = `서버가 받지 않은 변경 ${nf}건`; sub = "[보관된 변경] 에서 다시 보내거나 버리세요";
    } else if (O.lastReplay && Date.now() - O.lastReplay.at < 8000) {
      show = true; state = "done"; bg = "#1f6b3a";
      msg = `서버에 덮어썼습니다 — ${O.lastReplay.sent}건`; sub = O.lastReplay.failed ? `못 보낸 ${O.lastReplay.failed}건` : "";
      setTimeout(render, 8500);
    } else if (p && !p.finished) {
      show = true; state = "prefetch"; bg = "#1d4f91";
      msg = "절전 대비 보관 중…"; sub = `${p.done + p.failed} / ${p.total}`;
    } else if (p && p.finished && Date.now() - (p.shownAt || (p.shownAt = Date.now())) < 8000) {
      show = true; state = "prefetched"; bg = "#1f6b3a";
      msg = p.note || `절전 대비 보관 끝 — ${p.done}건${p.failed ? ` · 못 담은 ${p.failed}건` : ""}`; sub = "서버가 꺼져도 이 PC 에서 열립니다";
      setTimeout(render, 8500);
    }
    if (state !== lastState) { delete b.dataset.folded; lastState = state || ""; }
    b.style.background = bg;
    b.querySelector("#ob-msg").textContent = msg;
    b.querySelector("#ob-sub").textContent = sub;
    b.querySelector("#ob-list").style.display = (nq || nf) ? "" : "none";
    b.querySelector("#ob-keep").style.display = (O.down || O.replaying) ? "none" : "";
    b.querySelector("#ob-retry").style.display = O.down || nq ? "" : "none";
    b.style.display = show && !b.dataset.folded ? "flex" : "none";
    document.body.classList.toggle("offline-down", !!O.down);
    document.documentElement.style.setProperty("--offline-banner-h", show && !b.dataset.folded ? "34px" : "0px");
  }
  O.render = render;
  function showList() {
    if (listEl) listEl.remove();
    listEl = document.createElement("div");
    listEl.style.cssText = "position:fixed;top:40px;right:12px;z-index:100001;width:min(560px,96vw);max-height:70vh;overflow:auto;background:#fff;color:#222;"
      + "border:1px solid #999;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.3);padding:12px 14px;font:13px/1.5 'Malgun Gothic',system-ui,sans-serif";
    const row = (it, kind) => `<tr><td style="white-space:nowrap">${fmt(it.at)}</td><td>${what(it)}</td><td style="font-family:monospace;font-size:11px;word-break:break-all">${it.method} ${it.url}</td>`
      + (kind === "failed" ? `<td style="color:#8a2a1d">${it.why || ""}</td><td><button data-retry="${it.id}">다시</button> <button data-dropf="${it.id}">버림</button></td>`
                           : `<td></td><td><button data-dropq="${it.id}">버림</button></td>`) + "</tr>";
    listEl.innerHTML = `<div style="display:flex;align-items:center"><b>보관된 변경</b><span style="flex:1"></span><button id="ob-close">닫기</button></div>`
      + `<p style="margin:6px 0;color:#555">서버가 켜지면 위에서부터 차례로 다시 보내 서버 값을 덮어씁니다.  '버림' 은 이 PC 의 보관만 지웁니다.</p>`
      + `<table style="width:100%;border-collapse:collapse"><thead><tr><th>시각</th><th>무엇</th><th>요청</th><th>사유</th><th></th></tr></thead><tbody>`
      + O.queue.map((it) => row(it, "queued")).join("") + O.failed.map((it) => row(it, "failed")).join("") + "</tbody></table>"
      + (!O.queue.length && !O.failed.length ? '<p style="color:#555">보관된 변경이 없습니다.</p>' : "");
    document.body.appendChild(listEl);
    listEl.querySelector("#ob-close").onclick = () => { listEl.remove(); listEl = null; };
    listEl.addEventListener("click", async (ev) => {
      const t = ev.target; if (!(t instanceof HTMLElement)) return;
      if (t.dataset.retry) await O.retryFailed(Number(t.dataset.retry));
      else if (t.dataset.dropf) await O.discardFailed(Number(t.dataset.dropf));
      else if (t.dataset.dropq) await O.discardQueued(Number(t.dataset.dropq));
      else return;
      showList();
    });
  }
  O.showList = showList;

  /* ---------------- 시작 */
  (async () => {
    try { O.down = !!localStorage.getItem(LS_KEY); } catch (e) { /* */ }
    O.queue = await allQueued().catch(() => []);
    O.failed = await allFailed().catch(() => []);
    O.ready = true;
    render();
    await registerSw();
    if (O.down) { probeTimer = setInterval(probe, 10000); probe(); }
    else if (O.queue.length) replay();
    window.addEventListener("storage", async (ev) => {      // 다른 탭이 되보냈다 — 이 탭도 다시 받고 같은 띠를 보인다
      if (ev.key !== LS_LAST || !ev.newValue) return;
      try { O.lastReplay = JSON.parse(ev.newValue); } catch (e) { return; }
      O.queue = await allQueued().catch(() => []); O.failed = await allFailed().catch(() => []);
      if (O.down) setDown(false, "peer"); else render();
      emit("replayed", O.lastReplay);
    });
    window.addEventListener("online", () => probe());
    window.addEventListener("offline", () => setDown(true, "browser"));
    emit("ready", {});
  })();
})();
