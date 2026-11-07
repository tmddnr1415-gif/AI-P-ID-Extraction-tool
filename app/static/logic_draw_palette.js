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
document.addEventListener("dblclick", e => {                   // L90 — 두 번 누르면 상세 (기호: 설명 · 해 보기 / 매크로: 상세 · 고치기)
  const tl = e.target.closest(".pl-tile"); if (!tl) return;
  clearTimeout(clickT); e.preventDefault();
  if (tl.dataset.mac) openMacDetail(tl.dataset.key); else openSymDetail(tl.dataset.key);
});
document.addEventListener("dragstart", e => { const tl = e.target.closest(".pl-tile"); if (!tl) return; e.dataTransfer.setData("text/plain", "logicpal:" + tl.dataset.key); e.dataTransfer.effectAllowed = "copy"; });
$("#q").addEventListener("input", () => render());
$("#q").addEventListener("keydown", e => { if (e.key === "Escape") { $("#q").value = ""; render(); } });
$("#placing-x").onclick = () => say({ t: "cancel", win: P.target });
document.addEventListener("keydown", e => { if (e.key === "Escape" && tgt() && tgt().state && tgt().state.placing) say({ t: "cancel", win: P.target }); });
render();

/* ───────── L90 — 두 번 누르면 상세 ─────────
   기호 · 글자 상자: 설명 + 직접 해 보기 (입력을 눌러 0/1 → 출력과 그 과정 · 시간 기호는 시간 틀).  계산은 작성 시뮬레이션 그대로
   (POST /logic/api/drawings/symbol_sim — 그 기호만 든 그림) · 래치 · 타이머는 앞 상태를 이어 간다 ('처음으로' 로 지움).
   매크로: 설명 · 입력/출력 단자 · 시트 + 내부 동작 열기 · 고치기 (이 창에서 바로 새 창 — 그림 창을 거치면 브라우저가 막는다). */
const LOGIC_DESC = {
  and: ["AND", "모든 입력이 1 이면 출력 1 · 하나라도 0 이면 0."],
  or: ["OR", "입력 중 하나라도 1 이면 1 · 모두 0 이면 0."],
  nand: ["NAND", "AND 의 반대 — 모든 입력이 1 일 때만 0, 그 밖에는 1."],
  nor: ["NOR", "OR 의 반대 — 모든 입력이 0 일 때만 1."],
  not: ["NOT", "입력을 뒤집는다 — 1 이면 0, 0 이면 1."],
  delay_on: ["켜짐 지연 (ON DELAY)", "입력이 1 이 되고 T 초 동안 계속 1 이면 출력 1 · 입력이 0 이 되면 바로 0."],
  delay_off: ["꺼짐 지연 (OFF DELAY)", "입력이 1 이면 바로 1 · 입력이 0 이 되고 T 초가 지나야 0 (입력을 1 → 0 으로 바꿔 보세요)."],
  pulse: ["펄스 (PULSE)", "입력이 1 이 되는 순간부터 T 초 동안만 출력 1 — 입력이 계속 1 이어도 T 초 뒤에는 0."],
  vote: ["투표 A/B", "B 개 입력 중 A 개 이상이 1 이면 1 (예: 2/3 = 셋 중 둘 이상)."],
  memory: ["메모리 S-R", "S 가 1 이면 기억(출력 1) · R 이 1 이면 지움(0) · 둘 다 0 이면 앞 상태를 그대로 · 둘 다 1 이면 우선 칸을 따른다."],
  source: ["신호원", "들어오는 선 없이 값을 낸다 — 누름단추는 누르면 1."],
  sink: ["받기만", "들어오는 신호를 표시 · 경보 · 기록한다 (나가는 선 없음)."],
  connector: ["연결 기호", "같은 글자의 연결 기호끼리 한 신호 — 선을 그리지 않고 잇는다 (원 몸통으로 들어가 꼭지로 나간다)."],
  toggle: ["토글", "입력이 순간 1 이 될 때마다 출력이 뒤집힌다 (장 NOTE 정의)."],
};
const DT = { key: null, it: null, k: 2, t: 5, a: 2, dom: "", inputs: [], press: 0, state: {}, hist: [], seq: 0 };
function itemOf(key) { const I = P.items || { sym: [], pre: [], mac: [] }; return [...I.sym, ...I.pre, ...I.mac].find(x => x.key === key); }
function detailBox() {
  let d = $("#detail");
  if (!d) {
    d = document.createElement("div"); d.id = "detail"; d.className = "pl-detail";
    d.innerHTML = `<div class="dt-card"><div class="dt-head"><span id="dt-title"></span><button type="button" id="dt-x" title="닫기 (Esc)">✕</button></div><div id="dt-body"></div></div>`;
    document.body.appendChild(d);
    $("#dt-x").onclick = closeDetail;
    d.addEventListener("click", e => { if (e.target === d) closeDetail(); });
  }
  d.hidden = false; return d;
}
function closeDetail() { const d = $("#detail"); if (d) d.hidden = true; DT.key = null; }
document.addEventListener("keydown", e => { if (e.key === "Escape" && $("#detail") && !$("#detail").hidden) { e.stopPropagation(); closeDetail(); } }, true);

function openSymDetail(key) {
  const it = itemOf(key); if (!it) return;
  Object.assign(DT, { key, it, k: 2, t: 5, a: 2, dom: "", press: 0, state: {}, hist: [], inputs: [], prevOut: null });   // 기호마다 처음부터
  const isPre = key.startsWith("p:");
  const lg = isPre ? "" : it.logic;
  DT.n = it.bar || it.ab ? DT.k : null;
  detailBox();
  $("#dt-title").textContent = it.name;
  const body = $("#dt-body");
  const desc = isPre ? it.hint : ((LOGIC_DESC[lg] || [])[1] || "");
  const icon = isPre ? `<span class="pl-chip big">${esc(it.text)}</span>` : (it.icon || "");
  if (isPre && it.analog) {
    body.innerHTML = `<div class="dt-top"><div class="dt-icon">${icon}</div><div><p class="dt-desc">${esc(desc)}</p></div></div>
      <p class="dt-note">아날로그 연산은 값(숫자)을 넣어 계산합니다 — <b>신호 처리 시뮬레이션</b>에서 입력 값을 넣고 식 · 값을 넣은 식 · 출력 · 시간 응답을 봅니다.</p>
      <div class="dt-acts"><button type="button" id="dt-sig" class="pri">∿ 신호 처리 시뮬레이션에서 해 보기</button><button type="button" id="dt-place">그림에 놓기</button></div>`;
    $("#dt-sig").onclick = async () => { const w = window.open("", "_blank"); const r = await simCall(); const op = (r && r.aop) || ""; w.location.href = "/logic/signal" + (op ? "?op=" + encodeURIComponent(op) : ""); };
    $("#dt-place").onclick = () => { closeDetail(); say({ t: "pick", win: P.target, key, mode: "place" }); };
    return;
  }
  body.innerHTML = `<div class="dt-top"><div class="dt-icon">${icon}</div><div><p class="dt-desc">${esc(desc)}</p><p class="dt-sub" id="dt-read"></p></div></div>
    <h4>직접 해 보기 <span class="dt-hint">입력을 눌러 0 ↔ 1 · 계산은 작성 시뮬레이션 그대로</span></h4>
    <div class="dt-params" id="dt-params"></div>
    <div class="dt-io"><div><div class="dt-lab">입력</div><div id="dt-in" class="dt-ins"></div></div><div class="dt-arrow">→</div><div><div class="dt-lab">출력</div><div id="dt-out" class="dt-outs"></div></div></div>
    <h4>과정</h4><ol id="dt-why" class="dt-why"></ol>
    <div id="dt-chart"></div>
    <div class="dt-acts"><button type="button" id="dt-reset">처음으로 (상태 지우기)</button><button type="button" id="dt-place" class="pri">그림에 놓기</button><button type="button" id="dt-center">가운데에 놓기</button></div>`;
  const pr = $("#dt-params"); let h = "";
  if (it.bar || it.ab) h += `<label>입력 수 <input type="number" id="dp-k" min="1" max="6" value="${DT.k}"></label>`;
  if (it.ab) h += `<label>A (몇 개 이상) <input type="number" id="dp-a" min="1" max="6" value="${DT.a}"></label>`;
  if (it.time) h += `<label>시간 T (초) <input type="number" id="dp-t" min="0" step="0.5" value="${DT.t}"></label>`;
  if (lg === "memory") h += `<label>우선 칸 <select id="dp-dom"><option value="">기본</option><option value="set">SET 우선</option><option value="reset">RESET 우선</option></select></label>`;
  pr.innerHTML = h; pr.hidden = !h;
  const on = (id, f) => { const e = $(id); if (e) e.onchange = () => { f(e); DT.state = {}; DT.hist = []; runSym(); }; };
  on("#dp-k", e => { DT.k = Math.max(1, Math.min(6, +e.value || 2)); DT.inputs = DT.inputs.slice(0, DT.k); });
  on("#dp-a", e => { DT.a = Math.max(1, Math.min(6, +e.value || 2)); });
  on("#dp-t", e => { DT.t = Math.max(0, +e.value || 0); });
  on("#dp-dom", e => { DT.dom = e.value; });
  $("#dt-reset").onclick = () => { DT.state = {}; DT.hist = []; DT.inputs = DT.inputs.map(() => 0); DT.press = 0; runSym(); };
  $("#dt-place").onclick = () => { closeDetail(); say({ t: "pick", win: P.target, key, mode: "place" }); };
  $("#dt-center").onclick = () => { closeDetail(); say({ t: "pick", win: P.target, key, mode: "center" }); };
  runSym();
}
async function simCall() {
  const it = DT.it, isPre = DT.key.startsWith("p:");
  const body = { kind: isPre ? (it.kind || "BOX") : it.kind, text: isPre ? it.text : "", noin: isPre && it.noin, state: DT.state,
    k: it.bar || it.ab ? DT.k : undefined, inputs: DT.inputs, param: { t: DT.t, a: DT.a, b: DT.k, dominant: DT.dom, above: isPre ? it.above : undefined } };
  if ((!isPre && it.logic === "source") || (isPre && it.noin && false)) body.press = DT.press;
  try { const r = await fetch("/logic/api/drawings/symbol_sim", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }); return await r.json(); }
  catch (e) { return { error: String(e) }; }
}
async function runSym() {
  const seq = ++DT.seq, r = await simCall(); if (seq !== DT.seq || !DT.key) return;
  if (r.error || r.detail) { $("#dt-why").innerHTML = `<li class="bad">${esc(r.error || r.detail)}</li>`; return; }
  const it = DT.it, lg = (r.block || {}).logic || it.logic || "", fr = r.frames || [], last = fr[fr.length - 1] || { in: [], out: [] };
  if (DT.inputs.length !== r.inputs.length) DT.inputs = r.inputs.map((_, i) => DT.inputs[i] || 0);
  $("#dt-read").textContent = `시뮬레이터가 읽은 블록: ${(r.block || {}).func || "?"}${lg ? " · 동작 " + lg : ""}${r.text && r.text !== it.text ? " · 글자 " + r.text : ""}`;
  const names = lg === "memory" ? ["S (SET)", "R (RESET)"] : r.inputs;
  const ins = $("#dt-in"); ins.innerHTML = "";
  names.forEach((nm, i) => { const b = document.createElement("button"); b.type = "button"; b.className = "dt-bit v" + (DT.inputs[i] ? 1 : 0); b.innerHTML = `<span>${esc(nm)}</span><b>${DT.inputs[i] ? 1 : 0}</b>`;
    b.onclick = () => { DT.inputs[i] = DT.inputs[i] ? 0 : 1; DT.state = r.state || {}; runSym(); }; ins.appendChild(b); });
  if (!names.length && lg === "source" && !(DT.key.startsWith("p:"))) {
    const b = document.createElement("button"); b.type = "button"; b.className = "dt-bit v" + (DT.press ? 1 : 0); b.innerHTML = `<span>누름</span><b>${DT.press ? 1 : 0}</b>`;
    b.onclick = () => { DT.press = DT.press ? 0 : 1; DT.state = r.state || {}; runSym(); }; ins.appendChild(b);
  } else if (!names.length) ins.innerHTML = `<span class="dt-hint">들어오는 선 없음</span>`;
  const outs = $("#dt-out"), sink = lg === "sink" || (DT.key.startsWith("p:") && it.sink);
  const onames = lg === "memory" ? ["OUT (S 칸)", "OUT (R 칸)"] : r.outputs;
  outs.innerHTML = sink ? `<div class="dt-val v${last.in[0] ? 1 : 0}"><span>받은 값</span><b>${last.in[0] ?? "?"}</b></div>`
    : (last.out || []).map((v, j) => `<div class="dt-val v${v ? 1 : 0}"><span>${esc(onames[j] || "OUT")}</span><b>${v == null ? "?" : v}</b></div>`).join("") || `<span class="dt-hint">나가는 선 없음</span>`;
  $("#dt-why").innerHTML = whyLines(lg, r, names).map(t => `<li>${t}</li>`).join("");
  $("#dt-chart").innerHTML = fr.length > 1 ? chart(fr, names) : "";
  DT.prevOut = last.out;
}
function whyLines(lg, r, names) {
  const fr = r.frames || [], f0 = fr[0] || { in: [], out: [] }, last = fr[fr.length - 1] || f0, I = f0.in || [], O = last.out || [];
  const ins = I.map((v, i) => `${esc(names[i] || "IN" + (i + 1))}=<b>${v ?? "?"}</b>`).join(" · ");
  const ones = I.filter(v => v === 1).length, zeros = I.map((v, i) => v === 0 ? esc(names[i] || "IN" + (i + 1)) : null).filter(Boolean);
  const o = O[0], out = `출력 <b>${o ?? "?"}</b>`, L = [];
  if (lg === "and") L.push(`${ins}`, zeros.length ? `${zeros.join(" · ")} 가 0 → AND 는 하나라도 0 이면 0 → ${out}` : `모든 입력이 1 → ${out}`);
  else if (lg === "or") L.push(`${ins}`, ones ? `1 인 입력이 ${ones}개 → OR 는 하나라도 1 이면 1 → ${out}` : `모든 입력이 0 → ${out}`);
  else if (lg === "nand") L.push(`${ins}`, zeros.length ? `0 인 입력이 있음 → AND 는 0 → 뒤집어 ${out}` : `모든 입력이 1 → AND 1 → 뒤집어 ${out}`);
  else if (lg === "nor") L.push(`${ins}`, ones ? `1 인 입력이 있음 → OR 는 1 → 뒤집어 ${out}` : `모든 입력이 0 → OR 0 → 뒤집어 ${out}`);
  else if (lg === "not") L.push(`${ins}`, `뒤집어 → ${out}`);
  else if (lg === "vote") L.push(`${ins}`, `1 인 입력 ${ones}개 ${ones >= DT.a ? "≥" : "<"} A(${DT.a}) → ${out}`);
  else if (lg === "memory") {
    const S_ = I[0], R_ = I[1], prev = (DT.prevOut || [])[0];
    L.push(`S=<b>${S_}</b> · R=<b>${R_}</b>${prev != null ? ` · 앞 상태 ${prev}` : ""}`);
    L.push(S_ && R_ ? `둘 다 1 → 우선 칸(${DT.dom === "set" ? "SET" : DT.dom === "reset" ? "RESET" : "기본"}) → ${out}` : S_ ? `S=1 → 기억(SET) → ${out}` : R_ ? `R=1 → 지움(RESET) → ${out}` : `둘 다 0 → 앞 상태를 그대로 → ${out}`);
  } else if (["delay_on", "delay_off", "pulse"].includes(lg)) {
    L.push(`T = ${DT.t}초 · 입력 ${ins}`);
    for (const f of fr) L.push(`t = ${(+f.t).toFixed(1)}초 → 출력 <b>${(f.out || [])[0] ?? "?"}</b>${f.note ? ` <span class="dt-hint">${esc(f.note)}</span>` : ""}`);
    if (lg === "delay_on") L.push(I[0] ? `입력이 1 로 ${DT.t}초 이어져야 1 이 된다` : `입력이 0 → 바로 0`);
    if (lg === "delay_off") L.push(I[0] ? `입력이 1 → 바로 1 (0 으로 바꾸면 ${DT.t}초 뒤 0)` : `입력이 0 → ${DT.t}초 뒤 0 (앞에서 1 이었을 때)`);
    if (lg === "pulse") L.push(I[0] ? `1 이 된 순간부터 ${DT.t}초 동안만 1` : `입력 0 → 0 (0 → 1 로 바꾸는 순간 펄스)`);
  } else if (lg === "source") L.push(`들어오는 선 없이 → ${out}`);
  else if (lg === "sink") L.push(`받은 값 ${I[0] ?? "?"} — 표시 · 경보 · 기록`);
  else if (lg === "connector") L.push(`${ins} → 그대로 넘김 → ${out}`);
  else L.push(`${ins || "입력 없음"} → ${out}`);
  for (const n of r.notes || []) L.push(`<span class="dt-hint">메모: ${esc(n)}</span>`);
  return L;
}
function chart(fr, names) {
  const W = 330, Hrow = 26, rows = [...names.map((n, i) => [n, f => (f.in || [])[i]]), ["출력", f => (f.out || [])[0]]];
  const tmax = Math.max(1, ...fr.map(f => +f.t)) * 1.25, X = t => 60 + (W - 70) * (+t) / tmax;
  let g = "";
  rows.forEach(([nm, get], k) => {
    const y0 = 8 + k * Hrow, yHi = y0 + 4, yLo = y0 + 18; let d = "";
    fr.forEach((f, i) => { const v = get(f) ? yHi : yLo, x = X(f.t); d += i ? ` H${x} V${v}` : `M${X(0)} ${v}`; });
    d += ` H${W - 6}`;
    g += `<text x="4" y="${y0 + 15}" class="ch-l">${esc(nm)}</text><path d="${d}" class="ch-w${k === rows.length - 1 ? " out" : ""}"/>`;
  });
  fr.forEach(f => { g += `<line x1="${X(f.t)}" y1="4" x2="${X(f.t)}" y2="${8 + rows.length * Hrow}" class="ch-t"/><text x="${X(f.t) + 2}" y="${10 + rows.length * Hrow}" class="ch-l">${(+f.t).toFixed(1)}s</text>`; });
  return `<svg viewBox="0 0 ${W} ${14 + rows.length * Hrow}" class="dt-chart">${g}</svg>`;
}

function openMacDetail(key) {
  const it = itemOf(key); if (!it) return;
  DT.key = key; DT.it = it;
  detailBox();
  $("#dt-title").textContent = `${it.short} — 매크로`;
  const pins = (lst, side) => lst.length ? `<table class="dt-pins"><tr><th>${side}</th><th>행</th></tr>${lst.map(q => `<tr><td>${esc(q.name)}</td><td>${q.row ?? ""}</td></tr>`).join("")}</table>` : `<p class="dt-hint">없음</p>`;
  let who = ""; try { who = localStorage.getItem("pid.author") || ""; } catch (e) {}
  const prj = targetSet();
  $("#dt-body").innerHTML = `<div class="dt-mthumb">${it.thumb}</div>
    <p class="dt-desc"><b>${esc(it.title)}</b>${it.desc ? `<br>${esc(it.desc)}` : ""}${it.desc_ko ? `<br><span class="dt-hint">${esc(it.desc_ko)}</span>` : ""}</p>
    <p class="dt-sub">${esc(it.gname)}${it.sheet ? " · Typical 시트 " + esc(it.sheet) : ""} · 입력 ${it.nin} → 출력 ${it.nout}</p>
    <div class="dt-pinwrap">${pins(it.pins_in || [], "입력 단자")}${pins(it.pins_out || [], "출력 단자")}</div>
    <h4>내부 동작 · 시뮬레이션 · 고치기</h4>
    ${scopeNote(it, prj)}
    ${it.did ? "" : `<label class="dt-who">작성자 <input id="dt-who" value="${esc(who)}" placeholder="이름 (고친 사람으로 남습니다)"></label>`}
    <div class="dt-acts"><button type="button" id="dt-inside" class="pri">${it.did || !prj ? "▣ 내부 동작 열기 · 고치기 (새 창)" : "▣ 이 프로젝트에서 열기 · 고치기 (새 창)"}</button>
      ${!it.did && prj && it.tid ? `<button type="button" id="dt-common">공통 사전을 고치기 (모든 프로젝트)</button>` : ""}
      <button type="button" id="dt-place">그림에 놓기</button></div><p id="dt-msg" class="dt-hint"></p>`;
  $("#dt-place").onclick = () => { closeDetail(); say({ t: "pick", win: P.target, key, mode: "place" }); };
  $("#dt-inside").onclick = () => openInside(it, prj ? "project" : "common");
  if ($("#dt-common")) $("#dt-common").onclick = () => openInside(it, "common");
}
/* L91 — 매크로를 어디에 고치나: 그림 창이 프로젝트(묶음)의 장이면 그 프로젝트에만 (Typical 장을 묶음에 들여와 거기서) ·
   공통 사전은 따로 고르는 단추 (모든 프로젝트) */
function targetSet() { const d = ((tgt() || {}).state || {}).doc; return d && d.set ? d : null; }
function scopeNote(it, prj) {
  const where = prj ? `<b>${esc(prj.project || prj.set_name || "이 프로젝트")}</b>` : "";
  const sim = "새 창에서 ▶ 시뮬레이션을 켜고 왼쪽 표의 입력 단자 칸을 눌러 0 · 1 을 주면 매크로 안의 값과 출력이 보입니다.";
  if (it.did) return `<p class="dt-note">이 매크로의 안(Typical 장)이 ${where || "이 묶음"} 에 있습니다 — 새 창에서 기호 · 선 · 단자를 고치고 <b>저장</b>하면
    ${where || "이 묶음"} 의 매크로만 바뀝니다 (공통 사전 · 다른 프로젝트는 그대로).  ${sim}</p>`;
  if (prj) return `<p class="dt-note">공통 Typical 사전의 매크로입니다.  '이 프로젝트에서 열기' 는 그 Typical 장을 ${where} 에 사본으로 들여와 엽니다 —
    고치고 <b>저장</b>하면 ${where} 의 매크로만 바뀝니다 (공통 사전 · 다른 프로젝트는 그대로).  ${sim}</p>`;
  return `<p class="dt-note">공통 Typical 사전의 매크로입니다 — 고친 뒤 '사전에 저장' 을 누르면 모든 프로젝트에 반영됩니다
    (한 프로젝트에만 고치려면 그 프로젝트의 장을 열어 둔 채 두 번 누르세요).  ${sim}</p>`;
}
async function openInside(it, scope) {
  const w = window.open("", "_blank");                            // 누른 그 순간에 연다 (팝업 차단을 피한다)
  const fail = t => { if (w) w.close(); $("#dt-msg").textContent = t; };
  let did = it.did;
  const prj = targetSet();
  if (!did && it.tid) {
    const a = (($("#dt-who") || {}).value || "").trim();
    if (!a) { fail("작성자 이름을 적어 주세요."); $("#dt-who").focus(); return; }
    try { localStorage.setItem("pid.author", a); } catch (e) {}
    try {
      const url = scope === "project" && prj ? `/logic/api/drawings/sets/${encodeURIComponent(prj.set)}/sheet` : `/logic/api/drawings/typicals/${encodeURIComponent(it.tid)}/open`;
      const body = scope === "project" && prj ? { library: it.tid, author: a } : { author: a };
      const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const j = await r.json(); if (!r.ok) throw new Error(j.detail || r.statusText); did = j.id;
      if (scope === "project" && prj) { say({ t: "setchanged", win: P.target }); it.did = did; }   // 그림 창이 묶음을 새로 읽어 이 매크로가 '이 묶음' 것으로
    } catch (e) { fail("열지 못했습니다 — " + e.message); return; }
  }
  if (!did) { fail("이 매크로의 Typical 시트를 찾지 못했습니다."); return; }
  const url = `/logic/draw${location.search}#d=${did}`;
  if (w) w.location.href = url; else window.open(url, "_blank");
  $("#dt-msg").textContent = scope === "project" && prj && !it.tid ? "새 창으로 열었습니다 — 고치고 저장하세요." :
    scope === "project" && prj ? `새 창으로 열었습니다 — ${prj.project || prj.set_name || "이 프로젝트"} 에만 저장됩니다.` : "새 창으로 열었습니다 — 고친 뒤 '사전에 저장' 을 누르세요.";
}
