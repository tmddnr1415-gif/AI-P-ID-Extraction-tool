/* L88 — 기호 · 매크로 창.  그림 창(logic_draw.js · palSync)이 보낸 목록을 보이고, 누르면 그림 창에 '놓기' 를 부탁한다.
   말은 BroadcastChannel("logic.draw.palette") — 같은 주소의 창끼리.  그림 창이 여럿이면 마지막으로 만진(active) 창이 대상. */
"use strict";
const $ = s => document.querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const P = { items: null, wins: {}, target: null, shut: {}, gshut: {} };
let ch = null;
try { ch = new BroadcastChannel("logic.draw.palette"); } catch (e) { ch = null; }
try { P.shut = JSON.parse(localStorage.getItem("logic.draw.pal.shut") || "{}"); P.gshut = JSON.parse(localStorage.getItem("logic.draw.pal.gshut") || "{}"); } catch (e) {}

function say(m) { if (ch) ch.postMessage(m); }
function tgt() { return P.target && P.wins[P.target]; }
if (ch) ch.onmessage = ev => {
  const m = ev.data || {};
  if (m.t === "ping") { say({ t: "alive" }); return; }
  if (m.t === "items") { P.wins[m.win] = { ...(P.wins[m.win] || {}), items: m.items }; if (!P.target) P.target = m.win; if (m.win === P.target) { P.items = m.items; render(); } return; }
  if (m.t === "state") {
    const w = P.wins[m.win] = { ...(P.wins[m.win] || {}), state: m, seen: Date.now() };
    if (m.active || !P.target || !P.wins[P.target] || !P.wins[P.target].state) { if (P.target !== m.win && w.items) P.items = w.items; P.target = m.win; }
    if (m.win === P.target) { if (!P.items && w.items) P.items = w.items; render(); }
  }
};
say({ t: "hello" });
setInterval(() => {
  say({ t: "alive" });
  for (const k of Object.keys(P.wins)) if (Date.now() - (P.wins[k].seen || 0) > 15000 && k !== P.target) delete P.wins[k];
}, 1500);
window.addEventListener("beforeunload", () => say({ t: "bye" }));

function matches(it, q) { return !q || it.q.includes(q); }
function tileSym(it) { return `<div class="pl-tile" draggable="true" data-key="${esc(it.key)}" title="${esc(it.name)} — 누르면 그림 창에서 놓을 자리를 누르세요 · 두 번 누르면 화면 가운데">${it.icon}<span class="nm">${esc(it.name)}</span></div>`; }
function tilePre(it) { return `<div class="pl-tile" draggable="true" data-key="${esc(it.key)}" title="${esc(it.name)} — ${esc(it.hint)}"><span class="pl-chip">${esc(it.text)}</span><span class="nm">${esc(it.name)}</span><span class="sub">${esc(it.hint).slice(0, 40)}</span></div>`; }
function tileMac(it) { return `<div class="pl-tile" draggable="true" data-key="${esc(it.key)}" data-mac="1" title="${esc(it.title)}${it.desc ? "\n" + esc(it.desc) : ""}${it.desc_ko ? " — " + esc(it.desc_ko) : ""}\n입력 ${it.nin} → 출력 ${it.nout}${it.sheet ? " · 시트 " + esc(it.sheet) : ""}\n누르면 놓기 · 두 번 누르면 내부 동작">${it.thumb}<span class="nm">${esc(it.short)}</span><span class="sub">${esc(it.desc || it.title)}${it.desc_ko ? " · " + esc(it.desc_ko) : ""}</span></div>`; }

function render() {
  const w = tgt(), st = w && w.state, I = P.items;
  const t = $("#tgt");
  if (!st) { t.className = "pl-tgt none"; t.textContent = "그림 창을 찾는 중 … (LOGIC 작성 창을 열어 두세요)"; }
  else if (!st.doc) { t.className = "pl-tgt none"; t.textContent = "그림 창에서 그림을 여세요"; }
  else { t.className = "pl-tgt"; t.innerHTML = `놓을 곳 → <b>${esc(st.doc.sheet_no || st.doc.name)}</b> ${esc(st.doc.sheet_no ? st.doc.name : "")}${st.doc.sim ? " · <b>시뮬레이션 중</b>" : ""}`; }
  const conn = $("#conn"), on = !!(st && st.sel);
  conn.classList.toggle("off", !on);
  $("#conn-t").innerHTML = on ? `고른 기호 <b>${esc(st.sel.name)}</b> 뒤에 이어 놓기 (＋)` : "고른 기호 뒤에 이어 놓기 — 그림 창에서 기호를 고르면 켜집니다";
  const pl = st && st.placing, plIt = pl && I && [...I.sym, ...I.pre, ...I.mac].find(x => x.key === pl);
  $("#placing").hidden = !pl;
  if (pl) $("#placing-t").textContent = `${plIt ? (plIt.name || plIt.short) : pl} — 그림 창에서 놓을 자리를 누르세요`;
  if (!I) return;
  const q = $("#q").value.trim().toUpperCase();
  const sig = JSON.stringify([q, I.sym.length, I.pre.length, I.mac.map(m => m.key), (st && st.recent) || [], P.shut, P.gshut]);
  if (sig !== P._sig) {
    P._sig = sig;
    const all = new Map([...I.sym, ...I.pre, ...I.mac].map(x => [x.key, x]));
    const rec = q ? [] : ((st && st.recent) || []).map(k => all.get(k)).filter(Boolean);
    const tile = x => x.key.startsWith("m:") ? tileMac(x) : x.key.startsWith("p:") ? tilePre(x) : tileSym(x);
    sec("s-rec", rec.map(tile), rec.length); $("#s-rec").hidden = !rec.length;
    const sy = I.sym.filter(x => matches(x, q)), pr = I.pre.filter(x => matches(x, q)), ma = I.mac.filter(x => matches(x, q));
    sec("s-sym", sy.map(tileSym), sy.length); sec("s-pre", pr.map(tilePre), pr.length);
    const groups = {}; for (const m of ma) (groups[m.group] = groups[m.group] || { name: m.gname, order: m.order, items: [] }).items.push(m);
    const gk = Object.keys(groups).sort((a, b) => groups[a].order - groups[b].order || a.localeCompare(b));
    $("#s-mac .pl-groups").innerHTML = gk.length ? gk.map(k => { const shut = !q && (P.gshut[k] ?? !(k === "이 묶음" || k === "19VA"));
      return `<div class="g${shut ? " shut" : ""}" data-g="${esc(k)}"><h3>${esc(groups[k].name)} · ${groups[k].items.length}</h3><div class="pl-grid pl-mac">${groups[k].items.map(tileMac).join("")}</div></div>`; }).join("") : `<p class="pl-none">${q ? "찾는 매크로가 없습니다" : "매크로가 없습니다"}</p>`;
    $("#s-mac .n").textContent = ma.length;
    for (const id of ["s-rec", "s-sym", "s-pre", "s-mac"]) $("#" + id).classList.toggle("shut", !q && !!P.shut[id]);
  }
  document.querySelectorAll(".pl-tile").forEach(e => e.classList.toggle("on", !!pl && e.dataset.key === pl));
}
function sec(id, tiles, n) { const s = $("#" + id); s.querySelector(".pl-grid").innerHTML = tiles.join("") || `<p class="pl-none">없음</p>`; s.querySelector("h2 .n").textContent = n; }

/* 누르기 — 한 번 = 놓기 (또는 이어 놓기) · 두 번 = 가운데 (매크로는 내부 동작) */
let clickT = null;
document.addEventListener("click", e => {
  const h2 = e.target.closest(".pl-sec > h2"); if (h2) { const id = h2.parentElement.id; P.shut[id] = !h2.parentElement.classList.contains("shut"); try { localStorage.setItem("logic.draw.pal.shut", JSON.stringify(P.shut)); } catch (x) {} P._sig = null; render(); return; }
  const h3 = e.target.closest(".pl-groups h3"); if (h3) { const k = h3.parentElement.dataset.g; P.gshut[k] = !h3.parentElement.classList.contains("shut"); try { localStorage.setItem("logic.draw.pal.gshut", JSON.stringify(P.gshut)); } catch (x) {} P._sig = null; render(); return; }
  const tl = e.target.closest(".pl-tile"); if (!tl) return;
  const st = tgt() && tgt().state; if (!st || !st.doc) return;
  clearTimeout(clickT);
  const key = tl.dataset.key, conn = !!st.sel && $("#c-conn").checked && !tl.dataset.mac;
  clickT = setTimeout(() => { say({ t: "pick", win: P.target, key, mode: conn ? "connect" : "place" }); if (!conn) { try { window.opener && window.opener.focus(); } catch (x) {} } }, 230);
});
document.addEventListener("dblclick", e => {
  const tl = e.target.closest(".pl-tile"); if (!tl) return;
  clearTimeout(clickT); e.preventDefault();
  if (tl.dataset.mac) say({ t: "inside", win: P.target, key: tl.dataset.key });
  else say({ t: "pick", win: P.target, key: tl.dataset.key, mode: "center" });
});
document.addEventListener("dragstart", e => { const tl = e.target.closest(".pl-tile"); if (!tl) return; e.dataTransfer.setData("text/plain", "logicpal:" + tl.dataset.key); e.dataTransfer.effectAllowed = "copy"; });
$("#q").addEventListener("input", () => render());
$("#q").addEventListener("keydown", e => { if (e.key === "Escape") { $("#q").value = ""; render(); } });
$("#placing-x").onclick = () => say({ t: "cancel", win: P.target });
document.addEventListener("keydown", e => { if (e.key === "Escape" && tgt() && tgt().state && tgt().state.placing) say({ t: "cancel", win: P.target }); });
render();
