/* LOGIC 작도 (L54) — 분석한 로직과 같은 양식으로 그린다.
   좌표는 전부 PDF 포인트 (서버 draw.py 와 같은 수).  기호 기하는 서버 block_geometry 와 같은 규칙(geom()). */
"use strict";
const $ = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
const NS = "http://www.w3.org/2000/svg";

async function api(url, opt) {
  const r = await fetch(url, opt);
  if (!r.ok) { let m = `${r.status}`; try { m = (await r.json()).detail || m; } catch (e) {} throw new Error(m); }
  return r.json();
}
const post = (u, b) => api(u, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) });
const put = (u, b) => api(u, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b || {}) });
function author() {
  const u = new URLSearchParams(location.search).get("user");
  if (u) return u;
  const w = $("#who").value.trim();
  if (w) return w;
  try { return localStorage.getItem("pid.author") || ""; } catch (e) { return ""; }
}
function toast(t, ms) { const el = $("#toast"); el.textContent = t; el.hidden = false; clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, ms || 3200); }
function status(t) { $("#status").textContent = t || ""; }
const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const S = {
  sym: null, lay: null, doc: null, id: null, dirty: false,
  tool: "select", zoom: 1, sel: new Set(), selWire: null, undo: [], redo: [],
  wip: null,            // 그리는 중인 선 {pts, dashed}
  drag: null, verify: null, snap: true,
};

/* ───────── 기하 (서버 draw.block_geometry 와 같은 규칙) ───────── */
function layout() {
  const L = S.lay, N = S.doc ? S.doc.N : L.N;
  return { ...L, N, bottom: L.TOP + N * L.PITCH };
}
function ry(n) { const L = layout(); return L.TOP + ((n - 1) % L.N) * L.PITCH + L.PITCH / 2; }
function geom(b) {
  const spec = S.sym[b.kind], L = S.lay, x = b.x, y = b.y, w = b.w, h = b.h;
  const g = { box: [x, y, x + w, y + h], cells: [], bar: null, circle: null, pointer: null, texts: [] };
  if (spec.circle) {
    const r = Math.min(w, h) / 2, cx = x + w / 2, cy = y + h / 2, a = 0.6;
    g.circle = [cx, cy, r];
    g.pointer = [[cx + r * Math.cos(a), cy - r * Math.sin(a)], [cx + r * Math.cos(a), cy + r * Math.sin(a)], [cx + r * 2.2, cy]];
    g.texts.push([cx, cy, b.text, Math.min(h * 0.7, 7)]);
    return g;
  }
  if (spec.bar) { const Lb = h + L.bar_extra, cy = y + h / 2; g.bar = [x, cy - Lb / 2, x, cy + Lb / 2]; }
  if (spec.cells === 2) {
    g.cells = [[x, y, x + w, y + h / 2], [x, y + h / 2, x + w, y + h]];
    const d = (b.param || {}).dominant;
    const [s, r] = d === "set" ? ["SO", "R"] : d === "reset" ? ["S", "RO"] : ["S", "R"];
    g.texts.push([x + w / 2, y + h / 4, s, Math.min(h / 2 * 0.7, 7)], [x + w / 2, y + 3 * h / 4, r, Math.min(h / 2 * 0.7, 7)]);
    return g;
  }
  if (spec.note) { g.box = null; g.texts.push([x + w / 2, y + h / 2, b.text, Math.min(h * 0.8, 8)]); return g; }
  g.texts.push([x + w / 2, y + h / 2, b.text, Math.min(h * 0.6, 7)]);
  if (spec.time) g.texts.push([x + w / 2, y + h + 6, `${+((b.param || {}).t ?? 5)} sec`, 5]);
  if (spec.label && b.label) g.texts.push([x + w / 2, y + h + 6, b.label, 5]);
  return g;
}
function ports(b) {
  const spec = S.sym[b.kind], L = S.lay, x = b.x, y = b.y, w = b.w, h = b.h;
  if (spec.circle) { const r = Math.min(w, h) / 2; return [[x + w / 2 - r, y + h / 2, "in"], [x + w / 2 + r * 2.2, y + h / 2, "out"]]; }
  if (spec.cells === 2) return [[x, y + h / 4, "in"], [x, y + 3 * h / 4, "in"], [x + w, y + h / 4, "out"], [x + w, y + 3 * h / 4, "out"]];
  if (spec.note) return [];
  const out = [[x + w, y + h / 2, "out"]];
  if (spec.logic === "source") return out;
  if (spec.bar) {
    const Lb = h + L.bar_extra, cy = y + h / 2, k = Math.floor(Lb / L.PITCH);
    const ys = []; for (let i = 0; i < k; i++) ys.push(cy + (i - (k - 1) / 2) * L.PITCH);
    return ys.map(yy => [x, yy, "in"]).concat(out);
  }
  return [[x, y + h / 2, "in"]].concat(out);
}
function bboxOf(b) { const g = geom(b); if (g.circle) { const [cx, cy, r] = g.circle; return [cx - r, cy - r, cx + r * 2.2, cy + r]; } return g.box || [b.x, b.y, b.x + b.w, b.y + b.h]; }

/* ───────── 자석 ───────── */
function snapPt(p, opts) {
  const L = layout(), tol = 4;
  let best = null, bd = tol;
  const cand = (x, y, kind) => { const d = Math.hypot(x - p[0], y - p[1]); if (d < bd) { bd = d; best = { x, y, kind }; } };
  // 행 자리 (LOGIC 영역 좌우의 행 가운데)
  for (let n = 1; n <= L.N; n++) { const yy = ry(n); cand(L.LX0, yy, "row"); cand(L.LX1, yy, "row"); }
  for (const b of S.doc.blocks) if (!(opts && opts.exclude === b.id)) for (const pt of ports(b)) cand(pt[0], pt[1], "port");
  if (best) return [best.x, best.y, best.kind];
  if (S.snap) { const g = L.PITCH / 2; return [Math.round(p[0] / g) * g, Math.round((p[1] - L.TOP) / g) * g + L.TOP, "grid"]; }
  return [p[0], p[1], ""];
}

/* ───────── 그리기 ───────── */
function el(tag, attrs, parent) { const e = document.createElementNS(NS, tag); for (const k in attrs || {}) if (attrs[k] != null) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function txt(parent, x, y, t, fs, anchor) { const e = el("text", { x, y, "font-size": fs, "text-anchor": anchor || "start" }, parent); e.textContent = t; return e; }
function render() {
  const svg = $("#svg"); svg.innerHTML = "";
  if (!S.doc) { $("#empty").hidden = false; return; }
  $("#empty").hidden = true;
  const L = layout();
  svg.setAttribute("viewBox", `0 0 ${L.W} ${L.H}`);
  svg.setAttribute("width", L.W * S.zoom); svg.setAttribute("height", L.H * S.zoom);
  el("rect", { x: 0, y: 0, width: L.W, height: L.H, fill: "#fff", id: "paper" }, svg);
  // 격자 (LOGIC 영역 · 반 행)
  const grid = el("g", { class: "grid" }, svg);
  for (let yy = L.TOP; yy <= L.bottom + 0.01; yy += L.PITCH / 2) el("line", { x1: L.LX0, y1: yy, x2: L.LX1, y2: yy }, grid);
  renderTable(svg, L);
  renderTitle(svg, L);
  const wg = el("g", { id: "wires" }, svg);
  for (const w of S.doc.wires) {
    const pts = w.pts.map(p => p.join(",")).join(" ");
    el("polyline", { points: pts, class: "wirehit", "data-id": w.id }, wg);
    el("polyline", { points: pts, class: "wire" + (w.dashed ? " dashed" : "") + (S.selWire === w.id ? " sel" : ""), "data-id": w.id }, wg);
    if (S.selWire === w.id) w.pts.forEach((p, i) => el("circle", { cx: p[0], cy: p[1], r: 1.8, class: "vtx", "data-id": w.id, "data-i": i }, wg));
  }
  const bg = el("g", { id: "blocks" }, svg);
  const bad = new Set((S.verify && S.verify.blocks || []).filter(b => !b.ok).map(b => b.id));
  for (const b of S.doc.blocks) renderBlock(bg, b, bad.has(b.id));
  el("g", { id: "overlay" }, svg);
  renderProps();
}
function renderTable(svg, L) {
  const g = el("g", { class: "tbl" }, svg);
  const cols = L.LCOLS.concat(L.RCOLS);
  for (const x of cols) el("line", { x1: x, y1: L.TOP - 2 * L.PITCH, x2: x, y2: L.bottom }, g);
  for (let k = 0; k <= L.N; k++) {
    el("line", { x1: L.LCOLS[0], y1: L.TOP + k * L.PITCH, x2: L.LX0, y2: L.TOP + k * L.PITCH }, g);
    el("line", { x1: L.LX1, y1: L.TOP + k * L.PITCH, x2: L.RCOLS[4], y2: L.TOP + k * L.PITCH }, g);
  }
  el("line", { x1: L.LCOLS[0], y1: L.TOP - 2 * L.PITCH, x2: L.LX0, y2: L.TOP - 2 * L.PITCH }, g);
  el("line", { x1: L.LX1, y1: L.TOP - 2 * L.PITCH, x2: L.RCOLS[4], y2: L.TOP - 2 * L.PITCH }, g);
  const heads = [[0, 1, "FROM"], [1, 2, "NO."], [2, 3, "TAG NO."], [3, 4, "SERVICE"]];
  for (const [a, b, t] of heads) txt(g, (L.LCOLS[a] + L.LCOLS[b]) / 2, L.TOP - L.PITCH + 2, t, 6, "middle");
  for (const [a, b, t] of [[0, 1, "SERVICE"], [1, 2, "TAG NO."], [2, 3, "NO."], [3, 4, "TO"]]) txt(g, (L.RCOLS[a] + L.RCOLS[b]) / 2, L.TOP - L.PITCH + 2, t, 6, "middle");
  const fields = { left: [["fm", 0, 1], ["kks", 2, 3], ["desc", 3, 4]], right: [["desc", 0, 1], ["kks", 1, 2], ["to", 3, 4]] };
  for (let k = 0; k < L.N; k++) {
    const y = L.TOP + k * L.PITCH, yc = y + L.PITCH / 2 + 1.8;
    txt(g, (L.LCOLS[1] + L.LCOLS[2]) / 2, yc, String(k + 1), 5, "middle");
    txt(g, (L.RCOLS[2] + L.RCOLS[3]) / 2, yc, String(L.N + k + 1), 5, "middle");
    const lrow = S.doc.left[String(k + 1)] || {}, rrow = S.doc.right[String(L.N + k + 1)] || {};
    for (const [f, a, b] of fields.left) {
      el("rect", { x: L.LCOLS[a], y, width: L.LCOLS[b] - L.LCOLS[a], height: L.PITCH, class: "cell", "data-side": "left", "data-n": k + 1, "data-f": f }, g);
      if (lrow[f]) txt(g, L.LCOLS[a] + 2, yc, lrow[f], 5);
    }
    for (const [f, a, b] of fields.right) {
      el("rect", { x: L.RCOLS[a], y, width: L.RCOLS[b] - L.RCOLS[a], height: L.PITCH, class: "cell", "data-side": "right", "data-n": L.N + k + 1, "data-f": f }, g);
      if (rrow[f]) txt(g, L.RCOLS[a] + 2, yc, rrow[f], 5);
    }
    // 행 자리 (선을 여기서 시작하거나 끝낸다)
    el("circle", { cx: L.LX0, cy: y + L.PITCH / 2, r: 1.6, class: "rowstub", "data-n": k + 1 }, g);
    el("circle", { cx: L.LX1, cy: y + L.PITCH / 2, r: 1.6, class: "rowstub", "data-n": L.N + k + 1 }, g);
  }
}
function renderTitle(svg, L) {
  const g = el("g", { class: "title" }, svg);
  el("rect", { x: 560, y: 780, width: 610, height: 50 }, g);
  el("line", { x1: 1060, y1: 780, x2: 1060, y2: 830 }, g);
  el("line", { x1: 560, y1: 795, x2: 1170, y2: 795 }, g);
  txt(g, 620, 808, S.doc.title || "", 8);
  txt(g, 620, 824, S.doc.doc_no || "", 7);
  txt(g, 1070, 792, "SHEET NO.", 5);
  txt(g, 1068, 815, S.doc.sheet_no || "", 9);
}
function renderBlock(parent, b, bad) {
  const g = geom(b);
  const grp = el("g", { class: "blk" + (S.sel.has(b.id) ? " sel" : "") + (bad ? " bad" : ""), "data-id": b.id }, parent);
  const bb = bboxOf(b);
  el("rect", { x: bb[0] - 2, y: bb[1] - 2, width: bb[2] - bb[0] + 4, height: bb[3] - bb[1] + 4, class: "hit" }, grp);
  if (g.circle) {
    el("circle", { cx: g.circle[0], cy: g.circle[1], r: g.circle[2] }, grp);
    el("polygon", { points: g.pointer.map(p => p.join(",")).join(" ") }, grp);
  } else if (g.cells.length) {
    for (const c of g.cells) el("rect", { x: c[0], y: c[1], width: c[2] - c[0], height: c[3] - c[1] }, grp);
  } else if (g.box) {
    el("rect", { x: g.box[0], y: g.box[1], width: g.box[2] - g.box[0], height: g.box[3] - g.box[1] }, grp);
  } else {
    el("rect", { x: b.x, y: b.y, width: b.w, height: b.h, fill: "none", stroke: S.sel.has(b.id) ? "#2f5bd8" : "none", "stroke-dasharray": "1 1" }, grp);
  }
  if (g.bar) el("line", { x1: g.bar[0], y1: g.bar[1], x2: g.bar[2], y2: g.bar[3] }, grp);
  for (const [cx, cy, t, fs] of g.texts) if (t) { const e = el("text", { x: cx, y: cy, "font-size": fs }, grp); e.textContent = t; }
  if (S.tool === "wire" || S.tool === "dash" || S.sel.has(b.id)) for (const p of ports(b)) el("circle", { cx: p[0], cy: p[1], r: 1.4, class: "port" }, grp);
}

/* ───────── 팔레트 ───────── */
function paletteIcon(kind) {
  const spec = S.sym[kind];
  const b = { kind, x: 10, y: 8, w: spec.w, h: spec.h, text: spec.text, label: "", param: { t: 5, a: 2, b: 3, dominant: "" } };
  if (spec.cells === 2) { b.y = 2; }
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", `0 ${spec.cells === 2 ? -4 : -8} 44 ${spec.cells === 2 ? 34 : 40}`);
  const g = el("g", { class: "blk" }, svg);
  const gg = geom(b);
  if (gg.circle) { el("circle", { cx: gg.circle[0], cy: gg.circle[1], r: gg.circle[2] }, g); el("polygon", { points: gg.pointer.map(p => p.join(",")).join(" ") }, g); }
  else if (gg.cells.length) for (const c of gg.cells) el("rect", { x: c[0], y: c[1], width: c[2] - c[0], height: c[3] - c[1] }, g);
  else if (gg.box) el("rect", { x: gg.box[0], y: gg.box[1], width: gg.box[2] - gg.box[0], height: gg.box[3] - gg.box[1] }, g);
  if (gg.bar) el("line", { x1: gg.bar[0], y1: gg.bar[1], x2: gg.bar[2], y2: gg.bar[3] }, g);
  for (const [cx, cy, t, fs] of gg.texts.slice(0, 2)) { const e = el("text", { x: cx, y: cy, "font-size": fs }, g); e.textContent = t; }
  return svg;
}
function buildPalette() {
  const pal = $("#palette"); pal.innerHTML = "";
  for (const kind in S.sym) {
    const btn = document.createElement("button");
    btn.title = `${S.sym[kind].name} — 누르면 가운데에 놓입니다`;
    btn.appendChild(paletteIcon(kind));
    const sp = document.createElement("span"); sp.textContent = S.sym[kind].name; btn.appendChild(sp);
    btn.draggable = true;
    btn.ondragstart = e => { e.dataTransfer.setData("text/kind", kind); };
    btn.onclick = () => { if (!S.doc) return; const L = layout(); addBlock(kind, (L.LX0 + L.LX1) / 2, L.TOP + L.PITCH * 6); };
    pal.appendChild(btn);
  }
}
function newId(prefix) { let i = 1; const ids = new Set([...S.doc.blocks.map(b => b.id), ...S.doc.wires.map(w => w.id)]); while (ids.has(prefix + i)) i++; return prefix + i; }
function addBlock(kind, cx, cy) {
  const spec = S.sym[kind];
  const L = layout(), g = L.PITCH / 2;
  const b = { id: newId("b"), kind, w: spec.w, h: spec.h, text: spec.text, label: "", param: {} };
  if (spec.time) b.param.t = 5;
  if (spec.ab) { b.param.a = 2; b.param.b = 3; b.text = "2/3"; }
  if (spec.cells === 2) b.param.dominant = "";
  b.x = Math.round((cx - b.w / 2) / g) * g; b.y = Math.round((cy - b.h / 2 - L.TOP) / g) * g + L.TOP;
  // 가운데가 행 가운데에 오게 (상자 높이가 행과 어긋나므로 가운데 기준)
  const rowc = ry(Math.max(1, Math.min(L.N, Math.round((cy - L.TOP) / L.PITCH) + 1)));
  b.y = +(rowc - b.h / 2).toFixed(2);
  pushUndo(); S.doc.blocks.push(b); S.sel = new Set([b.id]); S.selWire = null; markDirty(); render();
}

/* ───────── 속성 ───────── */
function renderProps() {
  const card = $("#props-card"), box = $("#props");
  const ids = [...S.sel];
  if (ids.length !== 1 && !S.selWire) { card.hidden = true; return; }
  card.hidden = false; box.innerHTML = "";
  if (S.selWire) {
    const w = S.doc.wires.find(w => w.id === S.selWire);
    if (!w) { card.hidden = true; return; }
    $("#props-kind").textContent = "신호선";
    box.innerHTML = `<label>파선 <input type="checkbox" id="p-dashed" ${w.dashed ? "checked" : ""}></label>
      <p class="dw-hint">점 ${w.pts.length}개 — 점을 끌어 옮기고, Delete 로 지웁니다.</p>`;
    $("#p-dashed").onchange = e => { pushUndo(); w.dashed = e.target.checked; markDirty(); render(); };
    return;
  }
  const b = S.doc.blocks.find(b => b.id === ids[0]); if (!b) { card.hidden = true; return; }
  const spec = S.sym[b.kind];
  $("#props-kind").textContent = spec.name;
  let h = `<label>종류 <select id="p-kind">${Object.keys(S.sym).map(k => `<option value="${k}" ${k === b.kind ? "selected" : ""}>${esc(S.sym[k].name)}</option>`).join("")}</select></label>`;
  if (spec.time) h += `<label>시간 (초) <input id="p-t" type="number" min="0" step="0.5" value="${+(b.param.t ?? 5)}"></label>`;
  if (spec.ab) h += `<label>A / B <span><input id="p-a" type="number" min="1" max="9" value="${b.param.a || 2}" style="width:56px"> / <input id="p-b" type="number" min="1" max="9" value="${b.param.b || 3}" style="width:56px"></span></label>`;
  if (spec.cells === 2) h += `<label>우선 칸 <select id="p-dom"><option value="" ${!b.param.dominant ? "selected" : ""}>기본 (S·R 함께면 바뀜)</option><option value="set" ${b.param.dominant === "set" ? "selected" : ""}>SET 우선 (SO)</option><option value="reset" ${b.param.dominant === "reset" ? "selected" : ""}>RESET 우선 (RO)</option></select></label>`;
  if (spec.label) h += `<label>이름 <input id="p-label" value="${esc(b.label)}" placeholder="START"></label>`;
  if (spec.circle) h += `<label>글자 <input id="p-text" value="${esc(b.text)}" maxlength="2"></label><p class="dw-hint">같은 글자의 연결 기호는 한 신호 — 왼쪽에 닿은 선이 들어가고 꼭지에서 나갑니다.</p>`;
  if (spec.note) h += `<label>글 <input id="p-text" value="${esc(b.text)}"></label>`;
  h += `<label>크기 <span><input id="p-w" type="number" min="4" step="1" value="${b.w}" style="width:56px"> × <input id="p-h" type="number" min="4" step="1" value="${b.h}" style="width:56px"></span></label>
        <label>자리 <span><input id="p-x" type="number" step="1" value="${b.x}" style="width:56px"> , <input id="p-y" type="number" step="1" value="${b.y}" style="width:56px"></span></label>
        <div style="display:flex;gap:6px;margin-top:6px"><button id="p-dup">복사</button><button id="p-del">지우기</button></div>`;
  box.innerHTML = h;
  const upd = fn => { pushUndo(); fn(); markDirty(); render(); };
  $("#p-kind").onchange = e => upd(() => { const k = e.target.value, sp = S.sym[k]; b.kind = k; b.text = sp.text; b.w = sp.w; b.h = sp.h; b.param = {}; if (sp.time) b.param.t = 5; if (sp.ab) { b.param.a = 2; b.param.b = 3; b.text = "2/3"; } if (sp.cells === 2) b.param.dominant = ""; });
  const on = (id, fn) => { const e = $(id); if (e) e.onchange = ev => upd(() => fn(ev.target)); };
  on("#p-t", t => { b.param.t = Math.max(0, +t.value || 0); });
  on("#p-a", t => { b.param.a = Math.max(1, Math.min(9, +t.value || 2)); b.text = `${b.param.a}/${b.param.b}`; });
  on("#p-b", t => { b.param.b = Math.max(1, Math.min(9, +t.value || 3)); b.text = `${b.param.a}/${b.param.b}`; });
  on("#p-dom", t => { b.param.dominant = t.value; });
  on("#p-label", t => { b.label = t.value.trim().slice(0, 60); });
  on("#p-text", t => { b.text = t.value.trim().slice(0, spec.circle ? 2 : 40) || spec.text; });
  on("#p-w", t => { b.w = Math.max(4, +t.value || spec.w); });
  on("#p-h", t => { b.h = Math.max(4, +t.value || spec.h); });
  on("#p-x", t => { b.x = +t.value || 0; });
  on("#p-y", t => { b.y = +t.value || 0; });
  $("#p-dup").onclick = () => duplicateSel();
  $("#p-del").onclick = () => deleteSel();
}

/* ───────── 되돌리기 · 상태 ───────── */
function snapshot() { return JSON.stringify({ blocks: S.doc.blocks, wires: S.doc.wires, left: S.doc.left, right: S.doc.right }); }
function pushUndo() { S.undo.push(snapshot()); if (S.undo.length > 200) S.undo.shift(); S.redo = []; }
function restore(js) { const d = JSON.parse(js); Object.assign(S.doc, d); S.sel = new Set(); S.selWire = null; markDirty(); render(); }
function undo() { if (!S.undo.length) return; S.redo.push(snapshot()); restore(S.undo.pop()); }
function redo() { if (!S.redo.length) return; S.undo.push(snapshot()); restore(S.redo.pop()); }
function markDirty() { S.dirty = true; $("#save").disabled = false; status("저장하지 않은 변경이 있습니다"); }
function deleteSel() {
  if (!S.sel.size && !S.selWire) return;
  pushUndo();
  S.doc.blocks = S.doc.blocks.filter(b => !S.sel.has(b.id));
  if (S.selWire) S.doc.wires = S.doc.wires.filter(w => w.id !== S.selWire);
  S.sel = new Set(); S.selWire = null; markDirty(); render();
}
function duplicateSel() {
  if (!S.sel.size) return;
  pushUndo();
  const L = layout(), nsel = new Set();
  for (const id of S.sel) { const b = S.doc.blocks.find(b => b.id === id); if (!b) continue; const nb = JSON.parse(JSON.stringify(b)); nb.id = newId("b"); nb.y += 2 * L.PITCH; S.doc.blocks.push(nb); nsel.add(nb.id); }
  S.sel = nsel; markDirty(); render();
}
function moveSel(dx, dy) {
  if (!S.sel.size) return;
  pushUndo();
  for (const id of S.sel) { const b = S.doc.blocks.find(b => b.id === id); if (b) { b.x = +(b.x + dx).toFixed(2); b.y = +(b.y + dy).toFixed(2); } }
  markDirty(); render();
}

/* ───────── 마우스 ───────── */
function svgPt(ev) {
  const svg = $("#svg"), r = svg.getBoundingClientRect(), L = layout();
  return [(ev.clientX - r.left) / r.width * L.W, (ev.clientY - r.top) / r.height * L.H];
}
function setTool(t) {
  S.tool = t; S.wip = null;
  $$(".dw-tools button").forEach(b => b.classList.toggle("on", b.dataset.tool === t));
  $("#stage").style.cursor = t === "pan" ? "grab" : t === "select" ? "default" : "crosshair";
  render();
}
function overlay() { return $("#overlay"); }
function drawGhost() {
  const ov = overlay(); if (!ov) return; ov.innerHTML = "";
  if (S.wip && S.wip.pts.length) {
    const pts = S.wip.pts.concat(S.wip.cur ? orth(S.wip.pts[S.wip.pts.length - 1], S.wip.cur) : []);
    el("polyline", { points: pts.map(p => p.join(",")).join(" "), class: "wipline" }, ov);
    if (S.wip.hot) el("circle", { cx: S.wip.hot[0], cy: S.wip.hot[1], r: 2.6, class: "port hot" }, ov);
  }
  if (S.drag && S.drag.marquee) { const m = S.drag.marquee; el("rect", { x: Math.min(m[0], m[2]), y: Math.min(m[1], m[3]), width: Math.abs(m[2] - m[0]), height: Math.abs(m[3] - m[1]), class: "marquee" }, ov); }
}
function orth(a, b) {
  // 직각 꺾임 — 가로 먼저 · 두 좌표가 다 다르면 꺾이는 점을 하나 넣는다 (완전히 가로·세로면 그대로)
  if (Math.abs(a[0] - b[0]) < 0.01 || Math.abs(a[1] - b[1]) < 0.01) return [b];
  return [[b[0], a[1]], b];
}
function finishWire() {
  if (S.wip && S.wip.pts.length >= 2) {
    pushUndo();
    const pts = S.wip.pts.filter((p, i, a) => i === 0 || Math.hypot(p[0] - a[i - 1][0], p[1] - a[i - 1][1]) > 0.01).map(p => [+p[0].toFixed(2), +p[1].toFixed(2)]);
    if (pts.length >= 2) S.doc.wires.push({ id: newId("w"), pts, dashed: S.tool === "dash" });
    markDirty();
  }
  S.wip = null; render();
}
function bindStage() {
  const stage = $("#stage"), svg = $("#svg");
  stage.addEventListener("dragover", e => e.preventDefault());
  stage.addEventListener("drop", e => { const k = e.dataTransfer.getData("text/kind"); if (k && S.doc) { e.preventDefault(); const p = svgPt(e); addBlock(k, p[0], p[1]); } });
  svg.addEventListener("pointerdown", e => {
    if (!S.doc) return;
    stage.focus();
    const p = svgPt(e), t = e.target;
    if (e.button === 1 || S.tool === "pan" || S.space) { S.drag = { pan: true, x: e.clientX, y: e.clientY, sl: $("#scroll").scrollLeft, st: $("#scroll").scrollTop }; e.preventDefault(); return; }
    if (e.button !== 0) return;
    if (S.tool === "wire" || S.tool === "dash") {
      const sp = snapPt(p);
      if (!S.wip) S.wip = { pts: [[sp[0], sp[1]]], cur: null };
      else {
        const last = S.wip.pts[S.wip.pts.length - 1];
        for (const q of orth(last, [sp[0], sp[1]])) S.wip.pts.push(q);
        if (sp[2] === "row" || sp[2] === "port") { finishWire(); return; }
      }
      drawGhost(); return;
    }
    // select
    const blk = t.closest(".blk"), wire = t.classList.contains("wire") || t.classList.contains("wirehit"), vtx = t.classList.contains("vtx");
    if (vtx) { pushUndo(); S.drag = { vtx: true, id: t.dataset.id, i: +t.dataset.i }; return; }
    if (blk) {
      const id = blk.dataset.id;
      if (e.shiftKey) { if (S.sel.has(id)) S.sel.delete(id); else S.sel.add(id); S.selWire = null; render(); return; }
      if (!S.sel.has(id)) { S.sel = new Set([id]); S.selWire = null; render(); }
      S.drag = { move: true, start: p, moved: false, orig: [...S.sel].map(id => { const b = S.doc.blocks.find(b => b.id === id); return [id, b.x, b.y]; }) };
      return;
    }
    if (wire) { S.selWire = t.dataset.id; S.sel = new Set(); render(); return; }
    if (t.classList.contains("cell") || t.classList.contains("rowstub")) return;
    S.sel = new Set(); S.selWire = null; S.drag = { marquee: [p[0], p[1], p[0], p[1]] }; render();
  });
  window.addEventListener("pointermove", e => {
    if (!S.doc) return;
    const p = svgPt(e);
    if (S.wip) { const sp = snapPt(p); S.wip.cur = [sp[0], sp[1]]; S.wip.hot = (sp[2] === "row" || sp[2] === "port") ? sp : null; drawGhost(); return; }
    if (!S.drag) return;
    if (S.drag.pan) { $("#scroll").scrollLeft = S.drag.sl - (e.clientX - S.drag.x); $("#scroll").scrollTop = S.drag.st - (e.clientY - S.drag.y); return; }
    if (S.drag.vtx) { const w = S.doc.wires.find(w => w.id === S.drag.id); if (!w) return; const sp = snapPt(p); w.pts[S.drag.i] = [+sp[0].toFixed(2), +sp[1].toFixed(2)]; S.dirty = true; render(); return; }
    if (S.drag.move) {
      const L = layout(), g = S.snap ? L.PITCH / 2 : 0.01;
      let dx = p[0] - S.drag.start[0], dy = p[1] - S.drag.start[1];
      dx = Math.round(dx / g) * g; dy = Math.round(dy / g) * g;
      if (!S.drag.moved && (Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01)) { S.drag.moved = true; pushUndo(); }
      if (!S.drag.moved) return;
      for (const [id, x0, y0] of S.drag.orig) { const b = S.doc.blocks.find(b => b.id === id); if (b) { b.x = +(x0 + dx).toFixed(2); b.y = +(y0 + dy).toFixed(2); } }
      S.dirty = true; render(); return;
    }
    if (S.drag.marquee) { S.drag.marquee[2] = p[0]; S.drag.marquee[3] = p[1]; drawGhost(); }
  });
  window.addEventListener("pointerup", () => {
    if (!S.drag) return;
    if (S.drag.marquee) {
      const m = S.drag.marquee, x0 = Math.min(m[0], m[2]), x1 = Math.max(m[0], m[2]), y0 = Math.min(m[1], m[3]), y1 = Math.max(m[1], m[3]);
      if (x1 - x0 > 2 && y1 - y0 > 2) { S.sel = new Set(S.doc.blocks.filter(b => { const bb = bboxOf(b); return bb[0] >= x0 && bb[2] <= x1 && bb[1] >= y0 && bb[3] <= y1; }).map(b => b.id)); }
      S.drag = null; render(); return;
    }
    if ((S.drag.move && S.drag.moved) || S.drag.vtx) markDirty();
    S.drag = null; $("#stage").style.cursor = S.tool === "pan" ? "grab" : S.tool === "select" ? "default" : "crosshair";
  });
  svg.addEventListener("dblclick", e => {
    if (!S.doc) return;
    const t = e.target;
    if (S.wip) { S.wip.pts.pop(); finishWire(); return; }
    if (t.classList.contains("cell")) { editCell(t); return; }
    const blk = t.closest(".blk");
    if (blk) { const b = S.doc.blocks.find(b => b.id === blk.dataset.id); const sp = S.sym[b.kind]; const inp = $(sp.label ? "#p-label" : (sp.circle || sp.note) ? "#p-text" : sp.time ? "#p-t" : null); if (inp) { inp.focus(); inp.select(); } }
  });
  svg.addEventListener("contextmenu", e => { if (S.wip) { e.preventDefault(); finishWire(); } });
  stage.addEventListener("wheel", e => {
    if (!e.ctrlKey) return;
    e.preventDefault();
    const sc = $("#scroll"), r = $("#svg").getBoundingClientRect();
    const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
    const z0 = S.zoom; setZoom(S.zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
    const L = layout();
    sc.scrollLeft += (S.zoom - z0) * L.W * fx; sc.scrollTop += (S.zoom - z0) * L.H * fy;
  }, { passive: false });
  document.addEventListener("keydown", e => {            // 문서 전체 — 속성 칸에서 나온 뒤에도 V · W · Delete 가 듣는다
    if (!S.doc) return;
    const inInput = /INPUT|SELECT|TEXTAREA/.test(document.activeElement.tagName);
    if (inInput) return;
    if (!$("#modal").hidden) return;
    const L = layout();
    if (e.key === "Escape") { if (S.wip) { S.wip = null; render(); } else { S.sel = new Set(); S.selWire = null; render(); } }
    else if (e.key === "Enter" && S.wip) { finishWire(); }
    else if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); deleteSel(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") { e.preventDefault(); duplicateSel(); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); moveSel(-(e.shiftKey ? L.PITCH : L.PITCH / 2), 0); }
    else if (e.key === "ArrowRight") { e.preventDefault(); moveSel(e.shiftKey ? L.PITCH : L.PITCH / 2, 0); }
    else if (e.key === "ArrowUp") { e.preventDefault(); moveSel(0, -(e.shiftKey ? L.PITCH : L.PITCH / 2)); }
    else if (e.key === "ArrowDown") { e.preventDefault(); moveSel(0, e.shiftKey ? L.PITCH : L.PITCH / 2); }
    else if (e.key === "v" || e.key === "V") setTool("select");
    else if (e.key === "w" || e.key === "W") setTool("wire");
    else if (e.key === "d" || e.key === "D") setTool("dash");
    else if (e.key === "h" || e.key === "H") setTool("pan");
    else if (e.key === " ") { S.space = true; }
  });
  document.addEventListener("keyup", e => { if (e.key === " ") S.space = false; });
  document.addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); if (S.doc) save(); } });
}
function setZoom(z) { S.zoom = Math.max(0.3, Math.min(6, z)); $("#zval").textContent = Math.round(S.zoom * 100) + "%"; const L = layout(); const svg = $("#svg"); svg.setAttribute("width", L.W * S.zoom); svg.setAttribute("height", L.H * S.zoom); }
function fitZoom() { const sc = $("#scroll"); const L = layout(); setZoom(Math.min((sc.clientWidth - 30) / L.W, (sc.clientHeight - 30) / L.H)); }

/* ───────── 표 칸 ───────── */
function editCell(rect) {
  const side = rect.dataset.side, n = rect.dataset.n, f = rect.dataset.f;
  const inp = $("#cellin"), svg = $("#svg"), r = svg.getBoundingClientRect(), sc = $("#scroll").getBoundingClientRect();
  const L = layout(), x = +rect.getAttribute("x"), y = +rect.getAttribute("y"), w = +rect.getAttribute("width");
  inp.hidden = false;
  inp.style.left = (r.left - sc.left + $("#scroll").scrollLeft + x / L.W * r.width) + "px";
  inp.style.top = (r.top - sc.top + $("#scroll").scrollTop + y / L.H * r.height) + "px";
  inp.style.width = Math.max(60, w / L.W * r.width) + "px";
  inp.style.height = Math.max(16, L.PITCH / L.H * r.height) + "px";
  inp.value = ((S.doc[side][n] || {})[f]) || "";
  inp.focus(); inp.select();
  const done = commit => {
    inp.hidden = true; inp.onblur = inp.onkeydown = null;
    if (!commit) return;
    const v = inp.value.trim().slice(0, 60);
    const row = S.doc[side][n] || {};
    if ((row[f] || "") === v) return;
    pushUndo(); row[f] = v; S.doc[side][n] = row;
    if (!Object.values(row).some(Boolean)) delete S.doc[side][n];
    markDirty(); render();
  };
  inp.onblur = () => done(true);
  inp.onkeydown = e => {
    if (e.isComposing) return;
    if (e.key === "Enter" || e.key === "Tab") { e.preventDefault(); const next = e.key === "Tab" ? nextCell(side, n, f, e.shiftKey) : nextCell(side, String(+n + 1), f, false, true); done(true); if (next) editCell(next); }
    else if (e.key === "Escape") done(false);
  };
}
function nextCell(side, n, f, back, sameCol) {
  const order = side === "left" ? ["fm", "kks", "desc"] : ["desc", "kks", "to"];
  let i = order.indexOf(f);
  if (!sameCol) { i += back ? -1 : 1; if (i < 0) { i = order.length - 1; n = String(+n - 1); } if (i >= order.length) { i = 0; n = String(+n + 1); } }
  return $(`.cell[data-side="${side}"][data-n="${n}"][data-f="${order[i]}"]`);
}

/* ───────── 저장 · 목록 · 가져오기 ───────── */
function docOut() {
  const d = S.doc;
  return { name: $("#name").value.trim() || d.name, project: $("#f-project").value, sheet_no: $("#f-sheet").value.trim(), title: $("#f-title").value.trim(), doc_no: $("#f-doc").value.trim(),
    N: +$("#f-rows").value || d.N, left: d.left, right: d.right, blocks: d.blocks, wires: d.wires };
}
async function save() {
  if (!S.doc) return;
  const who = author(); if (!who) { toast("이름을 적어 주세요 (머리줄 ✎)."); $("#who").focus(); return; }
  try { localStorage.setItem("pid.author", who); } catch (e) {}
  try {
    const d = await put(`/logic/api/drawings/${S.id}`, { author: who, doc: docOut() });
    S.doc = d; S.dirty = false; $("#save").disabled = true; status(`저장됨 · ${new Date().toLocaleTimeString()} · ${who}`);
    await loadList(S.id); fillForm(); render();
  } catch (e) { toast("저장 실패 — " + e.message); }
}
function fillForm() {
  const d = S.doc;
  $("#name").value = d.name || ""; $("#name").disabled = false;
  $("#f-sheet").value = d.sheet_no || ""; $("#f-title").value = d.title || ""; $("#f-doc").value = d.doc_no || ""; $("#f-rows").value = d.N;
  $("#f-project").value = d.project || "";
  for (const id of ["verify", "analyse", "del"]) $(id === "del" ? "#del" : "#" + id).disabled = false;
  $("#pdf").hidden = false; $("#dxf").hidden = false;
  $("#pdf").href = `/logic/api/drawings/${S.id}/export.pdf`; $("#dxf").href = `/logic/api/drawings/${S.id}/export.dxf`;
}
async function openDoc(id) {
  if (S.dirty && !confirm("저장하지 않은 변경이 있습니다.  버리고 열까요?")) return;
  try { S.doc = await api(`/logic/api/drawings/${id}`); } catch (e) { toast(e.message); return; }
  S.id = id; S.dirty = false; S.sel = new Set(); S.selWire = null; S.undo = []; S.redo = []; S.verify = null; $("#verify-card").hidden = true;
  $("#pick").value = id; $("#save").disabled = true;
  fillForm(); render(); fitZoom(); render();
  status(`${S.doc.name} · 블록 ${S.doc.blocks.length} · 선 ${S.doc.wires.length} · 저장 ${S.doc.saves || 0}번`);
  location.hash = "d=" + id;
}
async function loadList(keep) {
  const r = await api("/logic/api/drawings");
  const sel = $("#pick"); sel.innerHTML = `<option value="">(그림을 고르세요)</option>` + r.items.map(i => `<option value="${i.id}">${esc(i.name)}${i.sheet_no ? " · " + esc(i.sheet_no) : ""} — 블록 ${i.blocks} · 선 ${i.wires}</option>`).join("");
  if (keep) sel.value = keep;
  return r.items;
}
async function loadProjects() {
  try { const r = await api("/logic/api/projects"); $("#f-project").innerHTML = `<option value="">(없음)</option>` + (r.projects || []).map(p => `<option value="${esc(p.name)}">${esc(p.name)}</option>`).join(""); } catch (e) {}
}
function modal(title, bodyHtml, onOk) {
  $("#m-title").textContent = title; $("#m-body").innerHTML = bodyHtml; $("#modal").hidden = false;
  return new Promise(res => {
    const close = v => { $("#modal").hidden = true; res(v); };
    $("#m-cancel").onclick = () => close(null);
    $("#m-ok").onclick = async () => { const v = onOk ? await onOk() : true; if (v !== false) close(v); };
    $("#modal").onkeydown = e => { if (e.key === "Escape") close(null); };
  });
}
async function newDoc() {
  const who = author();
  const v = await modal("새 그림", `<div class="dw-form">
    <label>이름 <input id="m-name" placeholder="예: 급수펌프 A 기동"></label>
    <label>시트 이름 <input id="m-sheet" placeholder="예: LD-001"></label>
    <label>행 수 (한쪽) <input id="m-rows" type="number" min="20" max="64" value="50"></label>
    <label>작성자 <input id="m-who" value="${esc(who)}"></label></div>`,
    () => { const w = $("#m-who").value.trim(); if (!w) { toast("작성자 이름이 필요합니다."); return false; } return { name: $("#m-name").value.trim(), sheet: $("#m-sheet").value.trim(), N: +$("#m-rows").value || 50, who: w }; });
  if (!v) return;
  try { localStorage.setItem("pid.author", v.who); $("#who").value = v.who; } catch (e) {}
  try {
    const d = await post("/logic/api/drawings", { name: v.name || "새 로직", author: v.who, N: v.N, project: $("#f-project").value });
    if (v.sheet) { d.sheet_no = v.sheet; await put(`/logic/api/drawings/${d.id}`, { author: v.who, doc: d }); }
    await loadList(d.id); await openDoc(d.id);
  } catch (e) { toast(e.message); }
}
async function importSheet() {
  let jobs = [];
  try { jobs = await api("/logic/api/jobs"); } catch (e) { toast(e.message); return; }
  jobs = (Array.isArray(jobs) ? jobs : jobs.items || jobs.jobs || []).filter(j => (j.state || j.status || "done") !== "running");
  if (!jobs.length) { toast("분석한 Logic 묶음이 없습니다."); return; }
  let picked = null;
  const v = modal("분석 시트에서 가져오기", `<div class="dw-form">
    <label>묶음 <select id="m-job">${jobs.map(j => `<option value="${j.id}">${esc(j.name || j.id)}${j.project ? " · " + esc(j.project) : ""}</option>`).join("")}</select></label>
    <label>작성자 <input id="m-who" value="${esc(author())}"></label></div>
    <div id="m-sheets" style="max-height:300px;overflow:auto;margin-top:8px"><p class="dw-hint">시트를 고르세요 …</p></div>`,
    () => { const w = $("#m-who").value.trim(); if (!w) { toast("작성자 이름이 필요합니다."); return false; } if (!picked) { toast("시트를 고르세요."); return false; } return { job: $("#m-job").value, page: picked, who: w }; });
  async function fill() {
    picked = null;
    const job = $("#m-job").value;
    try {
      const sh = await api(`/logic/api/jobs/${job}/sheets`);
      const list = Array.isArray(sh) ? sh : (sh.sheets || sh.items || []);
      $("#m-sheets").innerHTML = `<table><tr><th>시트</th><th>제목</th><th>블록</th></tr>${list.map(s => `<tr class="pick" data-page="${s.page}"><td>${esc(s.sheet_no)}</td><td>${esc(s.title || "")}</td><td>${Object.values(s.funcs || {}).reduce((a, b) => a + b, 0) || s.blocks || ""}</td></tr>`).join("")}</table>`;
      $$("#m-sheets tr.pick").forEach(tr => tr.onclick = () => { $$("#m-sheets tr.pick").forEach(x => x.classList.remove("on")); tr.classList.add("on"); picked = +tr.dataset.page; });
    } catch (e) { $("#m-sheets").innerHTML = `<p class="bad">${esc(e.message)}</p>`; }
  }
  $("#m-job").onchange = fill; fill();
  const r = await v;
  if (!r) return;
  try {
    try { localStorage.setItem("pid.author", r.who); $("#who").value = r.who; } catch (e) {}
    const d = await post("/logic/api/drawings", { author: r.who, from_job: r.job, from_page: r.page, project: $("#f-project").value });
    await loadList(d.id); await openDoc(d.id);
    toast("가져왔습니다 — 선은 분석기가 읽은 그물의 선분이라 손볼 자리가 있을 수 있습니다.", 5000);
  } catch (e) { toast(e.message); }
}
async function verify() {
  if (!S.doc) return;
  status("되읽기 검증 중 — PDF 로 내보내 분석기에 넣습니다 …");
  $("#verify").disabled = true;
  try {
    const v = await post(`/logic/api/drawings/${S.id}/verify`, { doc: docOut() });
    S.verify = v;
    const card = $("#verify-card"), out = $("#verify-out");
    card.hidden = false;
    $("#verify-sum").textContent = v.ok ? "전부 같게 읽혔습니다" : "다르게 읽힌 자리가 있습니다";
    $("#verify-sum").className = "dw-hint " + (v.ok ? "ok" : "bad");
    if (v.why) { out.innerHTML = `<p class="bad">${esc(v.why)}</p>`; }
    else {
      const bl = v.blocks || [];
      out.innerHTML = `<p>시트 이름 <b class="${v.sheet_no.read === v.sheet_no.drawn ? "ok" : "bad"}">${esc(v.sheet_no.read || "(못 읽음)")}</b> ·
        블록 ${bl.filter(b => b.ok).length}/${bl.length} · 표 행 ${v.rows.read}/${v.rows.drawn} (선이 닿은 행 ${v.rows.wired}) · 그물 ${v.nets} · 매달린 선 끝 ${v.dangling}</p>
        <ul>${bl.map(b => `<li data-id="${b.id}" class="${b.ok ? "ok" : "bad"}">${b.ok ? "✔" : "✕"} ${esc(b.kind)} → ${esc(b.read || "(없음)")} · 입력 ${b.inputs} · 출력 ${b.outputs}${b.why ? " — " + esc(b.why) : ""}</li>`).join("")}
        ${(v.rows.bad || []).map(r => `<li class="bad">✕ 행 ${r.side}${r.n}: 적은 것 "${esc(r.want)}" ↔ 읽은 것 "${esc(r.read)}"${r.desc_ok ? "" : " · 설명 다름"}</li>`).join("")}
        ${(v.extra_blocks || []).map(e => `<li class="bad">✕ 그리지 않은 블록이 읽혔습니다: ${esc(e.func)} @ ${e.bbox.map(Math.round).join(",")}</li>`).join("")}</ul>
        ${(v.findings || []).length ? `<p class="dw-hint">분석기 점검: ${v.findings.map(f => esc(f.text || f.code)).join(" · ")}</p>` : ""}`;
      $$("#verify-out li[data-id]").forEach(li => li.onclick = () => { S.sel = new Set([li.dataset.id]); S.selWire = null; render(); });
    }
    status(v.ok ? "되읽기 검증 — 같게 읽힙니다" : "되읽기 검증 — 다른 자리를 붉게 표시했습니다");
    render();
  } catch (e) { toast("검증 실패 — " + e.message); status(""); }
  $("#verify").disabled = false;
}
async function sendToAnalyse() {
  if (!S.doc) return;
  if (S.dirty) { toast("먼저 저장하세요."); return; }
  if (!confirm("그린 것을 PDF 로 내보내 LOGIC 검토 묶음으로 올립니다.  계속할까요?")) return;
  try { const r = await post(`/logic/api/drawings/${S.id}/analyse`, { author: author() }); toast("검토 묶음으로 올렸습니다 — LOGIC 검토 화면에서 열립니다."); setTimeout(() => { location.href = `/logic#job=${r.id}`; }, 900); }
  catch (e) { toast(e.message); }
}
async function delDoc() {
  if (!S.doc) return;
  const who = author(); if (!who) { toast("이름을 적어 주세요."); return; }
  const v = await modal("그림 지우기", `<p><b>${esc(S.doc.name)}</b> 을 지웁니다.  기록(누가 · 언제)은 남습니다.  그림 이름을 그대로 적으세요.</p><input id="m-confirm" style="width:100%">`,
    () => $("#m-confirm").value.trim() === S.doc.name ? true : (toast("이름이 다릅니다."), false));
  if (!v) return;
  try { await api(`/logic/api/drawings/${S.id}?author=${encodeURIComponent(who)}`, { method: "DELETE" }); S.doc = null; S.id = null; S.dirty = false; await loadList(); render(); $("#name").value = ""; $("#name").disabled = true; ["verify", "analyse", "del"].forEach(i => $("#" + i).disabled = true); $("#pdf").hidden = $("#dxf").hidden = true; status("지웠습니다"); }
  catch (e) { toast(e.message); }
}

/* ───────── 시작 ───────── */
async function init() {
  const r = await api("/logic/api/drawings/symbols");
  S.sym = r.symbols; S.lay = r.layout;
  const w = author(); if (w) $("#who").value = w;
  $("#who").onchange = () => { try { localStorage.setItem("pid.author", $("#who").value.trim()); } catch (e) {} };
  buildPalette(); bindStage();
  $$(".dw-tools button").forEach(b => b.onclick = () => setTool(b.dataset.tool));
  $("#zin").onclick = () => setZoom(S.zoom * 1.2); $("#zout").onclick = () => setZoom(S.zoom / 1.2); $("#zfit").onclick = () => fitZoom();
  $("#snap").onchange = e => { S.snap = e.target.checked; };
  $("#new").onclick = newDoc; $("#import").onclick = importSheet; $("#save").onclick = save; $("#verify").onclick = verify;
  $("#analyse").onclick = sendToAnalyse; $("#del").onclick = delDoc;
  $("#pick").onchange = e => { if (e.target.value) openDoc(e.target.value); };
  for (const id of ["#name", "#f-sheet", "#f-title", "#f-doc", "#f-project"]) $(id).oninput = () => { if (!S.doc) return; S.doc.sheet_no = $("#f-sheet").value.trim(); S.doc.title = $("#f-title").value.trim(); S.doc.doc_no = $("#f-doc").value.trim(); markDirty(); render(); };
  $("#f-rows").onchange = () => { if (!S.doc) return; const n = Math.max(20, Math.min(64, +$("#f-rows").value || 50)); $("#f-rows").value = n; pushUndo(); S.doc.N = n; markDirty(); render(); };
  window.addEventListener("beforeunload", e => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });
  await loadProjects();
  const items = await loadList();
  const m = location.hash.match(/d=([0-9a-f]{12})/);
  if (m && items.some(i => i.id === m[1])) openDoc(m[1]);
  else render();
}
init().catch(e => { toast("화면을 열지 못했습니다 — " + e.message, 8000); console.error(e); });
