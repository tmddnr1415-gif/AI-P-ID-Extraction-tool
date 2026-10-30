/* hotfix108 — 절전모드 서비스워커.  서버(8000)가 꺼져 있어도(부서장 PC 절전 · 서버 멈춤) 이 PC 에 보관해 둔
 * 화면과 자료로 P&ID 분석 · LOGIC 검토 · 판넬 공간확보 · DCS 그래픽을 연다.
 *
 * 규칙 (판정은 하나도 없다 — 같은 주소에 같은 응답을 돌려줄 뿐이다):
 *  · 같은 출처의 GET 만 다룬다.  쓰기(POST · PATCH · DELETE)는 손대지 않는다 — 보관 대기열은 화면의 offline.js 몫.
 *  · 화면 뼈대(`/` · `/logic` · `/space` · `/dcs` · `/static/*`)는 설치 때 `/offline/shell` 목록으로 미리 담고,
 *    평소에는 네트워크 먼저(6초 안에 안 오면 보관본) · 서버가 꺼졌다고 알려진 동안은 보관본 먼저.
 *  · 장 그림(PNG)은 보관본 먼저 — 분석 결과마다 같은 그림이다.
 *  · 그 밖의 GET(JSON 자료)은 네트워크 먼저, 성공하면 보관, 실패하면 보관본, 없으면 503 과 사람 말.
 *  · 서버 상태 확인(`/version` · `/running` · `/events`) · 광장(`/plaza`) · 내려받기(.xlsx · .pdf · .zip)는 보관하지 않는다.
 *  · 네트워크가 실패하거나 돌아오면 열린 화면들에 `{type:"net", down}` 을 알린다 (화면이 띠와 대기열을 맡는다). */
"use strict";
const VERSION = "pid-offline-v1";
const SHELL = VERSION + "-shell";
const DATA = VERSION + "-data";
const PAGES = VERSION + "-pages";
const NAV_TIMEOUT_MS = 6000;
const DOWN_TIMEOUT_MS = 1500;           // 꺼짐이 기억된 동안 화면을 서버에 먼저 묻는 시간 (hotfix129)
let DOWN = false;                       // 화면이 알려 준 "서버 꺼짐" — 그동안은 보관본 먼저

const HTML_PATHS = new Set(["/", "/logic", "/logic/", "/logic/test", "/space", "/space/", "/dcs", "/dcs/demo"]);
const NEVER_RE = /^\/(version|running|sw\.js|offline\/|plaza)|\/events(\?|$)|\.(xlsx|pdf|zip)(\?|$)|\/(diagnostic|feedback_export|export\.zip|report\.xlsx|grouptest\.xlsx|review\.pdf|review\.xlsx|changes\.xlsx|verdicts\.xlsx|excel)(\?|$)/;
const PNG_RE = /\.png(\?|$)/;

self.addEventListener("install", (ev) => {
  ev.waitUntil((async () => {
    try {
      const r = await fetch("/offline/shell", { cache: "no-store" });
      const urls = r.ok ? (await r.json()).urls || [] : [];
      const c = await caches.open(SHELL);
      await Promise.all(urls.map((u) => c.add(u).catch(() => null)));   // 하나가 없어도 나머지는 담는다
    } catch (e) { /* 설치 때 서버가 없으면 평소 쓰면서 담는다 */ }
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (ev) => {
  ev.waitUntil((async () => {
    const keep = new Set([SHELL, DATA, PAGES]);
    for (const k of await caches.keys()) if (k.startsWith("pid-offline-") && !keep.has(k)) await caches.delete(k);
    await self.clients.claim();
  })());
});

self.addEventListener("message", (ev) => {
  const d = ev.data || {};
  if (d.type === "offline-mode") { DOWN = !!d.down; return; }
  if (d.type === "prefetch" && Array.isArray(d.urls)) ev.waitUntil(prefetch(d.urls, ev.source));
  if (d.type === "stats") ev.waitUntil(stats().then((s) => ev.source && ev.source.postMessage({ type: "stats", ...s })));
  if (d.type === "forget") ev.waitUntil(Promise.all([DATA, PAGES].map((k) => caches.delete(k))));
});

async function tell(down) {
  if (DOWN === down) return;
  DOWN = down;
  for (const c of await self.clients.matchAll({ includeUncontrolled: true })) c.postMessage({ type: "net", down });
}

async function stats() {
  let data = 0, pages = 0;
  try { data = (await (await caches.open(DATA)).keys()).length; pages = (await (await caches.open(PAGES)).keys()).length; } catch (e) { /* 없음 */ }
  return { data, pages };
}

async function prefetch(urls, client) {
  let done = 0, failed = 0;
  const missed = [];
  for (const u of urls) {
    try {
      const req = new Request(u, { cache: "no-store" });
      const r = await fetch(req);
      if (r.ok) await (await caches.open(PNG_RE.test(u) ? PAGES : DATA)).put(req, r.clone()), done++;
      else { failed++; missed.push(`${r.status} ${u}`); }
    } catch (e) { failed++; missed.push(`! ${u}`); }
    if (client && (done + failed) % 5 === 0) client.postMessage({ type: "prefetch", done, failed, total: urls.length });
  }
  if (client) client.postMessage({ type: "prefetch", done, failed, total: urls.length, finished: true, missed: missed.slice(0, 20) });
}

function withTimeout(p, ms) {
  return new Promise((res, rej) => {
    const t = setTimeout(() => rej(new Error("timeout")), ms);
    p.then((v) => { clearTimeout(t); res(v); }, (e) => { clearTimeout(t); rej(e); });
  });
}

function missing(url) {
  const body = JSON.stringify({ detail: "절전모드 — 이 자료는 이 PC 에 보관돼 있지 않습니다. 서버가 켜져 있을 때 한 번 열어 두거나 [절전 대비 보관] 을 누르세요.", offline: true, url });
  return new Response(body, { status: 503, headers: { "Content-Type": "application/json; charset=utf-8", "X-Offline": "missing" } });
}

function isHtml(req, url) {
  return req.mode === "navigate" || HTML_PATHS.has(url.pathname) || (req.headers.get("accept") || "").includes("text/html");
}

self.addEventListener("fetch", (ev) => {
  const req = ev.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (NEVER_RE.test(url.pathname + url.search)) return;
  const html = isHtml(req, url);
  if (html) ev.respondWith(serveShell(req, url));
  else if (url.pathname.startsWith("/static/")) ev.respondWith(serveShell(req, url));
  else if (PNG_RE.test(url.pathname)) ev.respondWith(servePage(req));
  else ev.respondWith(serveData(req));
});

async function fromCache(name, req, opts) {
  const c = await caches.open(name);
  return c.match(req, opts || {});
}

async function serveShell(req, url) {
  const html = isHtml(req, url);
  const opts = html ? { ignoreSearch: true } : {};
  const key = html ? new Request(url.pathname) : req;             // 화면은 query(?embed=1&user=) 와 무관하게 한 벌
  // hotfix129 — "서버 꺼짐" 이 기억된 동안에도 화면(HTML)은 서버에 짧게(1.5초) 먼저 묻는다.  업데이트 적용으로 서버를
  // 다시 켜는 사이 꺼짐이 기억되면, 다시 열 때 보관해 둔 옛 LOGIC 화면이 떴다.  스크립트·스타일은 딱지(?v=) 가 같을 때만
  // 보관본 먼저 — 딱지가 바뀌었으면 새 판이므로 서버에서 받는다.
  if (DOWN && !html) {
    const hit = await fromCache(SHELL, key, opts);
    if (hit) return hit;
  }
  try {
    const r = await withTimeout(fetch(req), DOWN ? DOWN_TIMEOUT_MS : NAV_TIMEOUT_MS);
    if (r.ok) { (await caches.open(SHELL)).put(key, r.clone()).catch(() => null); tell(false); }
    return r;
  } catch (e) {
    // 딱지 붙은 주소가 처음이면 설치 때 담은 딱지 없는 보관본으로 (절전모드에서도 화면이 열리게)
    const hit = (await fromCache(SHELL, key, opts)) || (await fromCache(SHELL, key, { ignoreSearch: true }));
    if (hit) { tell(true); return hit; }
    throw e;
  }
}

async function servePage(req) {
  const hit = await fromCache(PAGES, req);
  if (hit) return hit;
  try {
    const r = await fetch(req);
    if (r.ok) (await caches.open(PAGES)).put(req, r.clone()).catch(() => null);
    return r;
  } catch (e) { tell(true); return missing(req.url); }
}

async function serveData(req) {
  if (DOWN) {
    const hit = await fromCache(DATA, req);
    if (hit) return hit;
  }
  try {
    const r = await fetch(req);
    if (r.ok && (r.headers.get("content-type") || "").includes("json")) (await caches.open(DATA)).put(req, r.clone()).catch(() => null);
    if (r.ok) tell(false);
    return r;
  } catch (e) {
    tell(true);
    const hit = await fromCache(DATA, req);
    return hit || missing(req.url);
  }
}
