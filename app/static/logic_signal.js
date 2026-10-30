/* L72 — 신호 처리(아날로그 연산자) 시뮬레이션 페이지.
   계산은 서버가 도면 판과 같은 aops.compute 로 한다 (POST /logic/api/aopsim) — 이 화면은 값을 넣고 과정을 그릴 뿐.
   시간 블록(Lag · Lead/Lag · 변화율 제한 · 적분 · 미분)은 POST /logic/api/aopsim/timeline 의 응답을 그래프로.
   도면 연산자 판의 '시뮬레이션에서 열기' 는 ?s=<JSON {op, inputs, params, label, cond, from}> 로 지금 값을 채워 연다. */
"use strict";
const $ = (q) => document.querySelector(q);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v) => (v == null || !isFinite(v) ? "—" : String(Math.abs(v) >= 1000 ? Math.round(v) : Math.round(v * 1000) / 1000));

const GROUPS = [
  ["사칙 연산", ["sum", "diff", "absdiff", "mean", "mul", "div"]],
  ["선택", ["max", "min", "median", "transfer"]],
  ["함수", ["gain", "rgain", "sqrt", "pow", "abs", "fx", "formula", "convert", "const"]],
  ["제한 · 바이어스", ["hilim", "lolim", "bias", "velim"]],
  ["시간", ["lag", "leadlag", "integral", "deriv"]],
  ["감시 · 비교", ["dev", "equal", "count"]],
];
// 입력 모양: multi = 늘이고 줄임 · 숫자 = 고정 개수 · dig = 디지털 1/0
const CFG = {
  sum: { ins: "multi", coef: true }, mean: { ins: "multi", coef: true }, mul: { ins: "multi", coef: true },
  max: { ins: "multi" }, min: { ins: "multi" }, median: { ins: "multi", n: 3 },
  diff: { ins: 2, pins: ["+", "-"] }, absdiff: { ins: 2, pins: ["IN1", "IN2"] }, div: { ins: 2, pins: ["IN1", "IN2"] },
  transfer: { ins: 2, pins: ["IN1", "IN2"], cond: true },
  gain: { ins: 1, p: [["k", "비례 상수 K", 0.8, -5, 5, 0.01]] }, rgain: { ins: 1, p: [["k", "비례 상수 K", 0.8, -5, 5, 0.01]] },
  sqrt: { ins: 1 }, abs: { ins: 1 }, convert: { ins: 1 },
  pow: { ins: 1, p: [["n", "지수 n", 2, 0, 5, 0.1]] },
  fx: { ins: 1, table: true }, formula: { ins: "formula", label: true }, const: { ins: 0, p: [["value", "상수 A", 50, 0, 100, 0.1]] },
  hilim: { ins: 1, p: [["h", "상한 H", 80, 0, 100, 0.1]] }, lolim: { ins: 1, p: [["l", "하한 L", 20, 0, 100, 0.1]] },
  bias: { ins: 1, p: [["b", "바이어스 b", 5, -100, 100, 0.1]], sign: true },
  velim: { ins: 1 }, lag: { ins: 1 }, leadlag: { ins: 1 }, integral: { ins: 1 }, deriv: { ins: 1 },
  dev: { ins: 2, p: [["d", "편차 D", 5, 0, 100, 0.1]] }, equal: { ins: 2, pins: ["IN1", "IN2"] }, count: { ins: "dig" },
};
const TIME_RANGE = { k: [-5, 5, 0.01], t: [0.1, 60, 0.1], tlead: [0, 60, 0.1], tlag: [0.1, 60, 0.1], r: [0.1, 50, 0.1] };
const DEF_VALS = [12, 3.5, 7, 9, 4, 6];

const S = { op: "sum", inputs: [], params: {}, label: "", cond: 1, from: "", time: { kind: "step", x0: 0, x1: 50, t1: 5, T: 60 } };
let META = { ops: {}, time_ops: {} };
let seq = 0, tseq = 0, timer = null;

function cfg(op) { return CFG[op] || { ins: 1 }; }
function paramsOf(op) {
  const c = cfg(op), out = [...(c.p || [])];
  for (const [k, label, d] of META.time_ops[op] || []) {
    if (!out.some((x) => x[0] === k)) { const r = TIME_RANGE[k] || [0, 100, 0.1]; out.push([k, label, d, r[0], r[1], r[2]]); }
  }
  return out;
}
function formulaVars(label) {
  const expr = (String(label).match(/^\s*OUT\s*=\s*(.+)$/i) || [])[1] || "";
  const fn = new Set(["SQRT", "LOG", "LOG10", "LN", "EXP", "ABS", "MIN", "MAX"]);
  return Array.from(new Set((expr.match(/[A-Za-z]\w*/g) || []).map((x) => x.toUpperCase()).filter((x) => !fn.has(x)))).sort();
}
function defaults(op) {
  const c = cfg(op);
  S.params = {}; S.label = ""; S.cond = 1;
  for (const [k, , d] of paramsOf(op)) S.params[k] = d;
  if (c.sign) S.label = "+";
  if (c.table) S.params.table = [[0, 0], [50, 30], [100, 100]];
  if (c.ins === "formula") S.label = "OUT = A * 0.16 - 0.024";
  S.inputs = shapeInputs(op, []);
}
function shapeInputs(op, have) {
  const c = cfg(op);
  const mk = (pin, k) => ({ pin, value: have[k] ? have[k].value : (c.ins === "dig" ? (k % 2 ? 0 : 1) : DEF_VALS[k % DEF_VALS.length]),
    coef: have[k] ? have[k].coef : null, from: have[k] ? have[k].from || "" : "" });
  if (c.ins === 0) return [];
  if (c.ins === 1) return [mk("", 0)];
  if (c.ins === 2) return [0, 1].map((k) => mk((c.pins || ["", ""])[k], k));
  if (c.ins === "formula") return formulaVars(S.label).map((v, k) => { const h = have.find((x) => x.pin === v); return h ? { ...h } : mk(v, k); });
  const n = Math.max(have.length, c.n || 2);
  return Array.from({ length: Math.min(16, n) }, (_, k) => mk(have[k] && have[k].pin || `IN${k + 1}`, k));
}
function rng(v, lo = 0, hi = 100) {
  if (v == null || !isFinite(v)) return [lo, hi];
  return [Math.min(lo, Math.floor(v < 0 ? v * 1.5 : 0)), Math.max(hi, Math.ceil(v > 0 ? v * 1.5 : 0))];
}

/* ------------------------------------------------------------------ 그리기 */
function drawTabs() {
  $("#tabs").innerHTML = GROUPS.map(([g, ops]) => `<div class="g">${esc(g)}</div>` + ops.filter((o) => META.ops[o]).map((o) =>
    `<button data-op="${o}" class="${o === S.op ? "on" : ""}" title="${esc(META.ops[o].eq || "")}">${esc(META.ops[o].ko || o)}</button>`).join("")).join("");
}
function numRow(name, key, v, lo, hi, step, extra = "") {
  return `<div class="sp-row" data-k="${esc(key)}"><div class="nm">${name}</div>
    <input type="number" step="any" data-num="${esc(key)}" value="${v == null ? "" : v}">
    <input type="range" data-rng="${esc(key)}" min="${lo}" max="${hi}" step="${step}" value="${v == null ? lo : v}">
    <div class="ex">${extra}</div></div>`;
}
function drawInputs() {
  const c = cfg(S.op);
  $("#label-row").hidden = !(c.label || c.sign);
  if (c.label) { $("#label-cap").textContent = "도면 수식"; $("#label").value = S.label; }
  if (c.sign) { $("#label-cap").textContent = "부호"; }
  $("#label").hidden = !c.label;
  const signSel = $("#label-row select");
  if (signSel) signSel.remove();
  if (c.sign) $("#label-row label").insertAdjacentHTML("beforeend", `<select data-sign><option value="+"${S.label !== "-" ? " selected" : ""}>X + b</option><option value="-"${S.label === "-" ? " selected" : ""}>X − b</option></select>`);
  let h = "";
  S.inputs.forEach((i, k) => {
    const nm = c.ins === "multi" ? `<input data-pin="${k}" value="${esc(i.pin)}" title="입력 이름">` : esc(i.pin || "X");
    const from = i.from ? `<div class="src">← ${esc(i.from)}</div>` : "";
    if (c.ins === "dig") {
      h += `<div class="sp-row dig" data-k="in${k}"><div class="nm">${nm}</div><div class="tg"><button class="sp-tg ${i.value >= 0.5 ? "on" : ""}" data-dig="${k}" data-v="1">1</button>
        <button class="sp-tg ${i.value >= 0.5 ? "" : "on0"}" data-dig="${k}" data-v="0">0</button></div><div></div>
        <div class="ex">${S.inputs.length > 1 ? `<button class="x" data-del="${k}" title="이 입력 빼기">✕</button>` : ""}</div>${from}</div>`;
      return;
    }
    const [lo, hi] = rng(i.value);
    let ex = "";
    if (c.coef) ex += `계수 <input type="number" step="any" data-coef="${k}" value="${i.coef == null ? "" : i.coef}" placeholder="1">`;
    if (c.ins === "multi" && S.inputs.length > 2) ex += `<button class="x" data-del="${k}" title="이 입력 빼기">✕</button>`;
    h += numRow(nm, "in" + k, i.value, lo, hi, 0.1, ex).replace(/<\/div>$/, from + "</div>");
  });
  if (c.cond) h += `<div class="sp-row dig"><div class="nm">C <small>Flag</small></div><div class="tg"><button class="sp-tg ${S.cond === 1 ? "on" : ""}" data-cond="1">1 → IN1</button>
    <button class="sp-tg ${S.cond === 0 ? "on0" : ""}" data-cond="0">0 → IN2</button></div><div></div><div></div></div>`;
  if (!S.inputs.length && !c.cond) h = `<div class="sp-hint">입력이 없는 블록입니다 — 아래 설정값이 출력입니다</div>`;
  $("#inputs").innerHTML = h;
  $("#add-in").hidden = !(c.ins === "multi" || c.ins === "dig") || S.inputs.length >= 16;
}
function drawParams() {
  const c = cfg(S.op);
  let h = paramsOf(S.op).map(([k, label, , lo, hi, step]) => { const v = S.params[k]; const [a, b] = v != null && (v < lo || v > hi) ? rng(v, lo, hi) : [lo, hi]; return numRow(esc(label), "p:" + k, v, a, b, step); }).join("");
  if (c.table) {
    h += `<div class="sp-table"><textarea data-table rows="4" spellcheck="false">${esc((S.params.table || []).map((p) => p.join(", ")).join("\n"))}</textarea>
      <small>한 줄에 X, Y — 그 사이는 곧은 선으로 잇습니다 (도면 판과 같은 보간)</small></div>`;
  }
  $("#params").innerHTML = h;
  $("#p-h").hidden = !h;
}
function drawTimeInputs() {
  const t = S.time, sine = t.kind === "sine";
  $("#time-in").innerHTML = `<label>입력 모양 <select data-t="kind"><option value="step"${t.kind === "step" ? " selected" : ""}>계단</option>
      <option value="ramp"${t.kind === "ramp" ? " selected" : ""}>경사</option><option value="sine"${sine ? " selected" : ""}>사인</option></select></label>
    <label>${sine ? "가운데" : "처음 X₀"} <input type="number" step="any" data-t="x0" value="${t.x0}"></label>
    <label>${sine ? "진폭" : "나중 X₁"} <input type="number" step="any" data-t="x1" value="${t.x1}"></label>
    <label>${sine ? "주기 (s)" : "바뀌는 때 t₁ (s)"} <input type="number" step="any" data-t="t1" value="${t.t1}"></label>
    <label>보는 시간 (s) <input type="number" step="any" data-t="T" value="${t.T}"></label>`;
}
function drawAll() {
  const m = META.ops[S.op] || {};
  $("#op-name").textContent = m.ko || S.op;
  $("#op-eq").textContent = m.eq || "";
  drawTabs(); drawInputs(); drawParams();
  const timed = !!META.time_ops[S.op];
  $("#time-card").hidden = !timed;
  if (timed) drawTimeInputs();
  run();
}

/* ------------------------------------------------------------------ 계산 (서버) */
function body() {
  const c = cfg(S.op), p = { ...S.params };
  for (const k of Object.keys(p)) if (p[k] == null || p[k] === "") delete p[k];
  const ins = S.inputs.map((i, k) => ({ net: "n" + k, pin: c.ins === 1 || (c.ins === "multi" && !i.pin) ? "" : i.pin, value: i.value, coef: i.coef }));
  return { op: S.op, inputs: ins, params: p, label: S.label, cond: c.cond ? S.cond : null };
}
function run() {
  clearTimeout(timer);
  timer = setTimeout(async () => {
    const my = ++seq;
    try {
      const r = await fetch("/logic/api/aopsim", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body()) });
      const d = await r.json();
      if (my !== seq) return;
      if (!r.ok) throw new Error(d.detail || r.status);
      drawTrace(d);
    } catch (e) { if (my === seq) $("#trace").innerHTML = `<div class="note">계산하지 못했습니다 — ${esc(e.message)}</div>`; }
    if (META.time_ops[S.op]) runTime();
    saveUrl();
  }, 40);
}
function drawTrace(d) {
  const t = d.trace || {}, c = cfg(S.op);
  const chips = S.inputs.map((i, k) => `<span class="chip">${esc(c.ins === 1 ? "X" : i.pin || "X" + (k + 1))}<b>${esc(fmt(i.value))}</b>${i.coef != null && i.coef !== 1 ? ` <small>×${esc(fmt(i.coef))}</small>` : ""}</span>`).join("")
    + (c.cond ? `<span class="chip">C<b>${S.cond}</b></span>` : "");
  const ps = (t.params || []).map(([k, v]) => `<span class="chip">${esc(k)}<b>${esc(v)}</b></span>`).join("");
  const res = d.dig != null ? String(d.dig) : t.res;
  let n = 0;
  const step = (h, inner) => `<div class="st"><i>${++n}</i><div class="bd"><div class="h">${h}</div>${inner}</div></div>`;
  $("#trace").innerHTML = (chips ? step("들어오는 값", `<div class="chips">${chips}</div>`) : "")
    + (ps ? step("설정값", `<div class="chips">${ps}</div>`) : "")
    + step("범례 식", `<div class="eq">${esc(t.sym || "")}</div>`)
    + step("값을 넣은 식", `<div class="eq sub">= ${esc(t.sub || "?")}</div>`)
    + step("출력", `<div class="eq res${res === "?" ? " unk" : ""}">= <b>${esc(res)}</b>${d.dig != null ? " <small>(1/0)</small>" : ""}</div>`
      + (t.note ? `<div class="note">${esc(t.note)}</div>` : ""));
}
async function runTime() {
  const my = ++tseq;
  try {
    const r = await fetch("/logic/api/aopsim/timeline", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ op: S.op, params: S.params, input: S.time, T: S.time.T }) });
    const d = await r.json();
    if (my !== tseq) return;
    if (!r.ok) throw new Error(d.detail || r.status);
    $("#time-eq").textContent = d.eq || "";
    drawChart(d);
  } catch (e) { if (my === tseq) $("#time-eq").textContent = "그리지 못했습니다 — " + e.message; }
}
let CH = null;
function drawChart(d) {
  const svg = $("#chart"), W = svg.clientWidth || 800, H = svg.clientHeight || 280;
  const L = 46, R = 24, T = 12, B = 28;
  const all = d.x.concat(d.y).filter(isFinite);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-9) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const tm = d.t[d.t.length - 1] || 1;
  const X = (t) => L + (W - L - R) * t / tm, Y = (v) => T + (H - T - B) * (1 - (v - lo) / (hi - lo));
  const path = (arr) => arr.map((v, i) => `${i ? "L" : "M"}${X(d.t[i]).toFixed(1)},${Y(v).toFixed(1)}`).join("");
  const ticks = (a, b, n) => { const s = Math.pow(10, Math.floor(Math.log10((b - a) / n))); const st = [1, 2, 5, 10].map((m) => m * s).find((x) => (b - a) / x <= n) || s * 10; const o = []; for (let v = Math.ceil(a / st) * st; v <= b + 1e-9; v += st) o.push(+v.toFixed(10)); return o; };
  let g = "";
  for (const v of ticks(lo, hi, 5)) g += `<line class="gr" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${fmt(v)}</text>`;
  for (const t of ticks(0, tm, 8)) g += `<text x="${X(t)}" y="${H - 9}" text-anchor="middle">${fmt(t)}</text>`;
  g += `<line class="ax" x1="${L}" x2="${W - R}" y1="${H - B}" y2="${H - B}"/><line class="ax" x1="${L}" x2="${L}" y1="${T}" y2="${H - B}"/>
    <text x="${W - 2}" y="${H - B + 4}" text-anchor="end">s</text>
    <path class="px" d="${path(d.x)}"/><path class="py" d="${path(d.y)}"/><line class="cur" id="cur" y1="${T}" y2="${H - B}" x1="-9" x2="-9"/>`;
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  svg.innerHTML = g;
  CH = { d, X, L, R, W, tm };
}
function chartHover(e) {
  if (!CH) return;
  const svg = $("#chart"), r = svg.getBoundingClientRect();
  const px = (e.clientX - r.left) * (CH.W / r.width);
  const t = Math.max(0, Math.min(CH.tm, (px - CH.L) / (CH.W - CH.L - CH.R) * CH.tm));
  const i = Math.round(t / CH.tm * (CH.d.t.length - 1));
  const cur = $("#cur"); cur.setAttribute("x1", CH.X(CH.d.t[i])); cur.setAttribute("x2", CH.X(CH.d.t[i]));
  const tip = $("#tip"); tip.hidden = false;
  tip.textContent = `t = ${fmt(CH.d.t[i])} s · X = ${fmt(CH.d.x[i])} · M = ${fmt(CH.d.y[i])}`;
  tip.style.left = Math.min(r.width - tip.offsetWidth - 4, Math.max(0, e.clientX - r.left + 10)) + "px";
}

/* ------------------------------------------------------------------ 주소 (도면에서 열기 · 나눠 보기) */
function saveUrl() {
  const o = { op: S.op, inputs: S.inputs, params: S.params, label: S.label, cond: S.cond, from: S.from || undefined };
  try { history.replaceState(null, "", "?s=" + encodeURIComponent(JSON.stringify(o))); } catch (e) { /* 주소를 못 바꿔도 계산은 된다 */ }
}
function loadUrl() {
  const q = new URLSearchParams(location.search);
  let o = null;
  try { o = q.get("s") ? JSON.parse(q.get("s")) : null; } catch (e) { o = null; }
  const op = (o && o.op) || q.get("op");
  if (!op || !META.ops[op]) return false;
  S.op = op;
  defaults(op);
  if (o) {
    if (o.label != null && o.label !== "") S.label = String(o.label);
    if (o.params && typeof o.params === "object") for (const [k, v] of Object.entries(o.params)) if (v != null) S.params[k] = v;
    if (o.cond === 0 || o.cond === 1) S.cond = o.cond;
    if (Array.isArray(o.inputs)) {
      const have = o.inputs.slice(0, 16).map((i) => ({ pin: String(i.pin || "").toUpperCase(), value: isFinite(Number(i.value)) && i.value !== null && i.value !== "" ? Number(i.value) : null,
        coef: i.coef == null || i.coef === "" ? null : Number(i.coef), from: String(i.from || "") }));
      const c = cfg(op);
      S.inputs = c.ins === "multi" || c.ins === "dig" ? have.map((h, k) => ({ ...h, pin: h.pin || `IN${k + 1}` })) : shapeInputs(op, have);
      if (c.ins === 2 && c.pins) S.inputs.forEach((x, k) => { x.pin = have[k] && have[k].pin ? have[k].pin : c.pins[k]; });
    }
    if (o.from) { S.from = String(o.from); $("#from").hidden = false; $("#from").textContent = "도면에서 — " + S.from; }
  }
  const x = S.inputs[0] && S.inputs[0].value;
  if (x != null) S.time = { ...S.time, x0: x, x1: Math.round((x + (Math.abs(x) > 1 ? Math.abs(x) * 0.5 : 50)) * 100) / 100 };
  return true;
}

/* ------------------------------------------------------------------ 손 */
function onInput(ev) {
  const t = ev.target;
  const num = t.dataset.num || t.dataset.rng;
  if (num != null) {
    const raw = t.value.trim(), v = raw === "" ? null : Number(raw);
    if (raw !== "" && !isFinite(v)) { t.classList.add("bad"); return; }
    t.classList.remove("bad");
    const row = t.closest(".sp-row");
    const other = row.querySelector(t.dataset.num != null ? "[data-rng]" : "[data-num]");
    if (t.dataset.rng != null) other.value = v;
    else if (v != null) {
      if (v < Number(other.min) || v > Number(other.max)) { const [a, b] = rng(v, Number(other.min), Number(other.max)); other.min = a; other.max = b; }
      other.value = v;
    }
    if (num.startsWith("in")) {
      S.inputs[Number(num.slice(2))].value = v;
      if (num === "in0" && v != null && META.time_ops[S.op]) { S.time.x0 = v; const x0 = $('[data-t="x0"]'); if (x0) x0.value = v; }   // 시간 그래프는 지금 입력에서 시작
    }
    else S.params[num.slice(2)] = v;
    run(); return;
  }
  if (t.dataset.coef != null) { const raw = t.value.trim(); S.inputs[Number(t.dataset.coef)].coef = raw === "" ? null : Number(raw); run(); return; }
  if (t.dataset.pin != null) { S.inputs[Number(t.dataset.pin)].pin = t.value.trim().toUpperCase(); run(); return; }
  if (t.id === "label") {
    S.label = t.value;
    if (cfg(S.op).ins === "formula") {
      const before = S.inputs.map((x) => x.pin).join();
      S.inputs = shapeInputs(S.op, S.inputs);
      if (S.inputs.map((x) => x.pin).join() !== before) drawInputs();
    }
    run(); return;
  }
  if (t.dataset.table != null) {
    const pts = t.value.split(/\n+/).map((ln) => ln.split(/[,\s]+/).filter(Boolean).map(Number)).filter((x) => x.length === 2 && x.every(isFinite));
    t.classList.toggle("bad", pts.length < 2);
    if (pts.length >= 2) { S.params.table = pts; run(); }
    return;
  }
  if (t.dataset.sign != null) { S.label = t.value; run(); return; }
  if (t.dataset.t) {
    const k = t.dataset.t;
    if (k === "kind") { S.time.kind = t.value; drawTimeInputs(); }
    else { const v = Number(t.value); if (t.value.trim() === "" || !isFinite(v)) { t.classList.add("bad"); return; } t.classList.remove("bad"); S.time[k] = v; }
    runTime(); saveUrl();
  }
}
function onClick(ev) {
  const tab = ev.target.closest("[data-op]");
  if (tab && tab.closest("#tabs")) {
    const keep = cfg(S.op).ins === "dig" ? [] : S.inputs.map((i) => ({ value: i.value }));
    S.op = tab.dataset.op; S.from = ""; $("#from").hidden = true;
    defaults(S.op);
    S.inputs.forEach((x, k) => { if (keep[k] && cfg(S.op).ins !== "dig") { x.value = keep[k].value; } });   // 다른 연산으로 넘어가도 넣던 아날로그 입력 값은 그대로
    drawAll(); return;
  }
  const dg = ev.target.closest("[data-dig]");
  if (dg) { S.inputs[Number(dg.dataset.dig)].value = Number(dg.dataset.v); drawInputs(); run(); return; }
  const cd = ev.target.closest("[data-cond]");
  if (cd) { S.cond = Number(cd.dataset.cond); drawInputs(); run(); return; }
  const del = ev.target.closest("[data-del]");
  if (del) { S.inputs.splice(Number(del.dataset.del), 1); drawInputs(); run(); return; }
  if (ev.target.closest("#add-in")) {
    const k = S.inputs.length, dig = cfg(S.op).ins === "dig";
    S.inputs.push({ pin: `IN${k + 1}`, value: dig ? 0 : DEF_VALS[k % DEF_VALS.length], coef: null, from: "" });
    drawInputs(); run(); return;
  }
  if (ev.target.closest("#reset")) { S.from = ""; $("#from").hidden = true; defaults(S.op); drawAll(); }
}

async function init() {
  try { META = await (await fetch("/logic/api/aopsim")).json(); } catch (e) { $("#trace").textContent = "연산 목록을 읽지 못했습니다"; return; }
  if (!loadUrl()) { S.op = "sum"; defaults("sum"); }
  document.addEventListener("input", onInput);
  document.addEventListener("click", onClick);
  $("#chart").addEventListener("mousemove", chartHover);
  $("#chart").addEventListener("mouseleave", () => { $("#tip").hidden = true; });
  window.addEventListener("resize", () => { if (CH) drawChart(CH.d); });
  drawAll();
}
init();
