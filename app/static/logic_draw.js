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
  guide: { grid: true, ruler: true, align: true, cross: true },   // L55 — 화면 전용 안내 (PDF · DXF 에 안 나간다)
  hover: null, alignLines: null,
};

/* ───────── 기하 (서버 draw.block_geometry 와 같은 규칙) ───────── */
function layout() {
  const L = S.lay, N = S.doc ? S.doc.N : L.N;
  return { ...L, N, bottom: L.TOP + N * L.PITCH };
}
function ry(n) { const L = layout(); return L.TOP + ((n - 1) % L.N) * L.PITCH + L.PITCH / 2; }
const CHAR_W = 0.56;                     // helv 평균 글자 폭 / 글자 크기 (서버 fit_fs 와 같은 어림)
function fitFs(text, width, fs) { const tw = String(text || "").length * fs * CHAR_W; if (tw <= width || tw <= 0) return +fs.toFixed(2); return +Math.max(2.5, fs * width / tw).toFixed(2); }
function tipRatio(b) { const v = +((b.param || {}).tipr || 1.75); return Math.max(1.3, Math.min(2.2, isFinite(v) ? v : 1.75)); }
function barOf(b) {
  const p = b.param || {}, L = S.lay;
  if (Array.isArray(p.bar) && p.bar.length === 2) return [b.x, b.y + +p.bar[0], b.x, b.y + +p.bar[1]];
  const Lb = b.h + L.bar_extra, cy = b.y + b.h / 2; return [b.x, cy - Lb / 2, b.x, cy + Lb / 2];
}
function wrapText(t, n) { const words = String(t || "").split(/\s+/).filter(Boolean), out = []; let cur = ""; for (const w of words) { if (cur && cur.length + 1 + w.length > n) { out.push(cur); cur = w; } else cur = (cur + " " + w).trim(); } if (cur) out.push(cur); return out.length ? out : [""]; }
function geom(b) {                       // L56 — param.above (블록 위 글) 는 어느 종류든 한 줄 더 (서버 block_geometry 와 같은 자리)
  const g = geomCore(b), ab = (b.param || {}).above;
  if (ab) g.texts.push([b.x + b.w / 2, b.y - 0.5 * layout().PITCH, ab, 4.6]);
  return g;
}
function wireLabelPos(w) {               // 서버 wire_label_pos 와 같은 수 — 첫 가로 토막 가운데 · 0.8P 아래
  const P = layout().PITCH, pts = w.pts;
  for (let i = 0; i + 1 < pts.length; i++) { const a = pts[i], b = pts[i + 1]; if (Math.abs(a[1] - b[1]) < 0.2 && Math.abs(b[0] - a[0]) >= 6) return [(a[0] + b[0]) / 2, a[1] + 0.8 * P]; }
  const a = pts[0], b = pts[1]; return [(a[0] + b[0]) / 2, Math.max(a[1], b[1]) + 0.8 * P];
}
function geomCore(b) {
  const spec = S.sym[b.kind], L = S.lay, x = b.x, y = b.y, w = b.w, h = b.h, P = L.PITCH;
  const g = { box: [x, y, x + w, y + h], cells: [], bar: null, circle: null, pointer: null, texts: [] };
  if (spec.circle && spec.lamp) {
    const r = Math.min(w, h) / 2, cx = x + w / 2, cy = y + h / 2;
    g.circle = [cx, cy, r]; g.texts.push([cx, cy, (b.text || "G").slice(0, 2), Math.min(h * 0.7, 7)]);
    return g;
  }
  if (spec.circle) {
    const r = Math.min(w, h) / 2, cx = x + w / 2, cy = y + h / 2, a = 0.6, tr = tipRatio(b);
    const ca = r * Math.cos(a), sa = r * Math.sin(a), pt = (b.param || {}).point || "R";
    g.circle = [cx, cy, r];
    g.pointer = ({ R: [[cx + ca, cy - sa], [cx + ca, cy + sa], [cx + r * tr, cy]], L: [[cx - ca, cy - sa], [cx - ca, cy + sa], [cx - r * tr, cy]],
      T: [[cx - sa, cy - ca], [cx + sa, cy - ca], [cx, cy - r * tr]], B: [[cx - sa, cy + ca], [cx + sa, cy + ca], [cx, cy + r * tr]] })[pt] ||
      [[cx + ca, cy - sa], [cx + ca, cy + sa], [cx + r * tr, cy]];
    g.texts.push([cx, cy, b.text, Math.min(h * 0.7, 7)]);
    return g;
  }
  if (spec.box && (b.param || {}).lines && b.param.lines.length) {
    for (const [dx, dy, t, fs] of b.param.lines) g.texts.push([x + dx, y + dy, t, fs, "start"]);
    return g;
  }
  if (spec.bar) g.bar = barOf(b);
  if (spec.cells === 2) {
    g.cells = [[x, y, x + w, y + h / 2], [x, y + h / 2, x + w, y + h]];
    const d = (b.param || {}).dominant;
    const [s, r] = d === "set" ? ["SO", "R"] : d === "reset" ? ["S", "RO"] : ["S", "R"];
    g.texts.push([x + w / 2, y + h / 4, s, Math.min(h / 2 * 0.7, 7)], [x + w / 2, y + 3 * h / 4, r, Math.min(h / 2 * 0.7, 7)]);
    return g;
  }
  if (spec.note) { g.box = null; g.texts.push([x + w / 2, y + h / 2, b.text, Math.min(h * 0.8, 8)]); return g; }
  if (spec.macro) {
    const p = b.param || {}, title = p.title || b.text || "";
    const big = String(title).includes(" | ");            // L58 — 줄을 명시한 이름(`FG COMPR SYS | GRP`)은 첫 줄을 크게 (서버 _wrap 과 같은 구분자)
    const lines = big ? String(title).split(" | ").map(t => t.trim()).filter(Boolean) : wrapText(title, Math.max(8, Math.floor(w / 2.6)));
    lines.slice(0, 3).forEach((ln, i) => g.texts.push([x + w / 2, y + 0.5 * P + i * 0.6 * P + (big && i ? 0.15 * P : 0), ln, big && i === 0 ? 6.5 : 4.6]));
    for (const q of p.pins_in || []) g.texts.push([x + 1.5, y + q.dy, q.name, 4.2, "start"]);
    for (const q of p.pins_out || []) g.texts.push([x + w - 1.5, y + q.dy, q.name, 4.2, "end"]);
    return g;
  }
  g.texts.push([x + w / 2, y + h / 2, b.text, fitFs(b.text, w - 1.6, Math.min(h * 0.6, 7))]);
  if (spec.time) g.texts.push([x + w / 2, y + h + 6, `${+((b.param || {}).t ?? 5)} sec`, 5]);
  if (spec.label && b.label) g.texts.push([x + w / 2, y + h + 6, b.label, 5]);
  return g;
}
function ports(b) {
  const spec = S.sym[b.kind], L = S.lay, x = b.x, y = b.y, w = b.w, h = b.h;
  if (spec.macro) { const p = b.param || {}; return [...(p.pins_in || []).map(q => [x, y + q.dy, "in", q.name]), ...(p.pins_out || []).map(q => [x + w, y + q.dy, "out", q.name])]; }
  if (spec.circle && spec.lamp) { const r = Math.min(w, h) / 2; return [[x + w / 2 - r, y + h / 2, "in"], [x + w / 2, y + h / 2 - r, "in"], [x + w / 2, y + h / 2 + r, "in"], [x + w / 2 + r, y + h / 2, "in"]]; }
  if (spec.circle) {
    const r = Math.min(w, h) / 2, cx = x + w / 2, cy = y + h / 2, tr = tipRatio(b), pt = (b.param || {}).point || "R";
    const tip = ({ R: [cx + r * tr, cy], L: [cx - r * tr, cy], T: [cx, cy - r * tr], B: [cx, cy + r * tr] })[pt] || [cx + r * tr, cy];
    const edge = ({ R: [cx - r, cy], L: [cx + r, cy], T: [cx, cy + r], B: [cx, cy - r] })[pt] || [cx - r, cy];
    return [[edge[0], edge[1], "in"], [tip[0], tip[1], "out"]];
  }
  if (spec.cells === 2) return [[x, y + h / 4, "in"], [x, y + 3 * h / 4, "in"], [x + w, y + h / 4, "out"], [x + w, y + 3 * h / 4, "out"]];
  if (spec.note) return [];
  const out = [[x + w, y + h / 2, "out"]];
  if (spec.logic === "source") return out;
  if (spec.bar) {
    const [, b0, , b1] = barOf(b), Lb = b1 - b0, cy = (b0 + b1) / 2, k = Math.max(1, Math.floor(Lb / L.PITCH));
    const ys = []; for (let i = 0; i < k; i++) ys.push(cy + (i - (k - 1) / 2) * L.PITCH);
    return ys.map(yy => [x, yy, "in"]).concat(out);
  }
  return [[x, y + h / 2, "in"]].concat(out);
}
function bboxOf(b) { const g = geom(b); if (g.circle) { const [cx, cy, r] = g.circle; let bb = [cx - r, cy - r, cx + r, cy + r]; for (const q of g.pointer || []) bb = [Math.min(bb[0], q[0]), Math.min(bb[1], q[1]), Math.max(bb[2], q[0]), Math.max(bb[3], q[1])]; return bb; } return g.box || [b.x, b.y, b.x + b.w, b.y + b.h]; }

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
  renderGrid(svg, L);
  renderTable(svg, L);
  renderTitle(svg, L);
  renderNotes(svg, L);
  const wg = el("g", { id: "wires" }, svg);
  for (const w of S.doc.wires) {
    const pts = w.pts.map(p => p.join(",")).join(" ");
    el("polyline", { points: pts, class: "wirehit", "data-id": w.id }, wg);
    el("polyline", { points: pts, class: "wire" + (w.dashed ? " dashed" : "") + (S.selWire === w.id ? " sel" : ""), "data-id": w.id }, wg);
    for (const [dx, dy] of w.dots || []) el("circle", { cx: dx, cy: dy, r: 0.12 * layout().PITCH, class: "dot", "data-id": w.id }, wg);
    for (const [mx, my, kind] of w.marks || []) el("polygon", { points: markPolygon(mx, my, kind).map(q => q.join(",")).join(" "), class: "mark", "data-id": w.id }, wg);
    const tri = arrowOf(w); if (tri) el("polygon", { points: tri.map(q => q.join(",")).join(" "), class: "arrow", "data-id": w.id }, wg);
    if (w.label) { const [lx, ly] = wireLabelPos(w); const e = txt(wg, lx, ly, w.label, 4.5, "middle"); e.setAttribute("class", "wlabel"); e.dataset.id = w.id; }
    if (S.selWire === w.id) w.pts.forEach((p, i) => el("circle", { cx: p[0], cy: p[1], r: 1.8, class: "vtx", "data-id": w.id, "data-i": i }, wg));
  }
  const bg = el("g", { id: "blocks" }, svg);
  const bad = new Set((S.verify && S.verify.blocks || []).filter(b => !b.ok).map(b => b.id));
  for (const b of S.doc.blocks) renderBlock(bg, b, bad.has(b.id));
  el("g", { id: "overlay" }, svg);
  drawGhost();
  renderProps();
  drawRulers();
  if (simOn()) simPaint(S.sim.values || {}, S.sim.frames && S.sim.frames.length ? S.sim.frames[S.sim.frames.length - 1] : null);   // L57
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
    const li = linkInfo("left", k + 1), ri = linkInfo("right", L.N + k + 1);
    for (const [f, a, b] of fields.left) {
      const cls = "cell" + (f === "fm" && li && li.ref ? " linked" : "") + (f === "fm" && li && li.ft && li.ft.ok === false ? " ftbad" : "") + (f === "fm" && li && li.ft && li.ft.warn && li.ft.warn.length ? " ftwarn" : "");
      el("rect", { x: L.LCOLS[a], y, width: L.LCOLS[b] - L.LCOLS[a], height: L.PITCH, class: cls, "data-side": "left", "data-n": k + 1, "data-f": f }, g);
      if (lrow[f]) txt(g, L.LCOLS[a] + 2, yc, lrow[f], 5);
      if (f === "fm" && li && li.ref && !li.ref.other) { const e = txt(g, L.LCOLS[b] - 2, yc, li.ref.did ? "↗" : "?", 5.5, "end"); e.setAttribute("class", "golink" + (li.ref.did ? "" : " missing")); e.dataset.side = "left"; e.dataset.n = k + 1; const tt = el("title", {}, e); tt.textContent = li.ref.did ? `${li.ref.sheet} 시트 ${li.ref.src_row || li.ref.row}행 (출력) 으로 — ${li.ft && li.ft.ok === false ? "일치하지 않습니다: " + (li.ft.why || []).join(" · ") : "연결 맞음"}` : `이 묶음에 ${li.ref.sheet} 장이 없습니다`; }
    }
    for (const [f, a, b] of fields.right) {
      const cls = "cell" + (f === "to" && ri && ri.targets && ri.targets.length ? " linked" : "") + (f === "to" && ri && ri.ft && ri.ft.ok === false ? " ftbad" : "");
      el("rect", { x: L.RCOLS[a], y, width: L.RCOLS[b] - L.RCOLS[a], height: L.PITCH, class: cls, "data-side": "right", "data-n": L.N + k + 1, "data-f": f }, g);
      if (rrow[f]) txt(g, L.RCOLS[a] + 2, yc, rrow[f], 5);
      if (f === "to" && ri && ri.targets && ri.targets.length) { const t0 = ri.targets.find(t => t.did) || ri.targets[0]; const e = txt(g, L.RCOLS[b] - 2, yc, t0.did ? "↗" : "?", 5.5, "end"); e.setAttribute("class", "golink" + (t0.did ? "" : " missing")); e.dataset.side = "right"; e.dataset.n = L.N + k + 1; const tt = el("title", {}, e); tt.textContent = t0.did ? `${t0.sheet} 시트 ${t0.row}행 (입력) 으로 — ${ri.ft && ri.ft.ok === false ? "일치하지 않습니다: " + (ri.ft.why || []).join(" · ") : "연결 맞음"}` : `이 묶음에 ${t0.sheet} 장이 없습니다`; }
      if (f === "desc" && ri && ri.refs_in && ri.refs_in.length) { const e = txt(g, L.RCOLS[b] - 2, yc, "←" + ri.refs_in.length, 4.5, "end"); e.setAttribute("class", "refin"); const tt = el("title", {}, e); tt.textContent = "이 신호를 받는 곳: " + ri.refs_in.map(r => `${r.sheet}-${r.row}`).join(", "); }
    }
    // 행 자리 (선을 여기서 시작하거나 끝낸다)
    el("circle", { cx: L.LX0, cy: y + L.PITCH / 2, r: 1.6, class: "rowstub", "data-n": k + 1 }, g);
    el("circle", { cx: L.LX1, cy: y + L.PITCH / 2, r: 1.6, class: "rowstub", "data-n": L.N + k + 1 }, g);
  }
}
function renderNotes(svg, L) {           // L56 — 장 노트 상자 (서버 NOTES_BOX · notes_layout 과 같은 자리)
  const notes = (S.doc.notes || []).filter(Boolean); if (!notes.length) return;
  const g = el("g", { class: "notes" }, svg);
  el("rect", { x: 30, y: 780, width: 510, height: 50 }, g);
  txt(g, 34, 787, "NOTES", 5.5);
  notes.slice(0, 20).forEach((t, i) => { const c = Math.floor(i / 6), r = i % 6; txt(g, 34 + c * 170, 794 + r * 6.2, `${i + 1}. ${t}`, 4.5); });
}
function renderTitleA5j(svg, L) {       // 서버 draw._a5j_frame 과 같은 자리 — LOGIC 머리글 · 테두리 · NOTE · 삼성 C&T 타이틀블록
  const g = el("g", { class: "title" }, svg);
  el("line", { x1: L.LX0, y1: L.TOP - 2 * L.PITCH, x2: L.LX1, y2: L.TOP - 2 * L.PITCH }, g);
  txt(g, (L.LX0 + L.LX1) / 2, L.TOP - L.PITCH + 2.5, "LOGIC", 7, "middle");
  el("rect", { x: 16, y: 16, width: 1175 - 16, height: 836 - 16 }, g);
  el("rect", { x: 23, y: 23, width: 1175 - 30, height: 836 - 30 }, g);
  txt(g, 34, 792, "NOTE :", 8);
  const x0 = 900, y0 = 735, x1 = 1160, y1 = 830, rows = [y0, y0 + 18, y0 + 50, y0 + 78, y1];
  el("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0 }, g);
  for (const yy of rows.slice(1, -1)) el("line", { x1: x0, y1: yy, x2: x1, y2: yy }, g);
  el("line", { x1: x0 + 170, y1: rows[2], x2: x0 + 170, y2: rows[4] }, g); el("line", { x1: x0 + 215, y1: rows[2], x2: x0 + 215, y2: rows[4] }, g);
  const cap = (x, y, t) => txt(g, x + 2, y + 5, t, 3.6);
  cap(x0, rows[0], "PROJECT NAME"); txt(g, (x0 + x1) / 2 + 20, rows[0] + 15, S.doc.project_name || "", 8, "middle");
  cap(x0, rows[1], "DRAWING TITLE"); txt(g, (x0 + x1) / 2 + 20, rows[1] + 11, "CONTROL LOGIC & LOOP DIAGRAM", 5.5, "middle"); txt(g, (x0 + x1) / 2 + 20, rows[1] + 19, S.doc.title || "", 6, "middle");
  cap(x0, rows[2], "PROJECT DWG NO."); txt(g, x0 + 85, rows[2] + 12, S.doc.doc_no || "", 6.5, "middle");
  cap(x0 + 170, rows[2], "SHEET"); txt(g, x0 + 185, rows[2] + 13, S.doc.sheet_no || "", 6.5, "middle");
  cap(x0 + 215, rows[2], "REV."); txt(g, x0 + 237, rows[2] + 13, S.doc.rev || "", 6.5, "middle");
  cap(x0, rows[3] + 7, "PROJECT NO."); txt(g, x0 + 85, rows[3] + 15, S.doc.project || "", 5, "middle");
  cap(x0 + 170, rows[3] + 7, "SCALE"); txt(g, x0 + 205, rows[3] + 15, "NONE", 4.5, "middle");
  cap(x0 + 215, rows[3] + 7, "REF. CODE"); txt(g, x0 + 250, rows[3] + 15, "-", 4.5, "middle");
}
function renderTitle(svg, L) {
  if (S.doc && S.doc.form === "a5j") return renderTitleA5j(svg, L);
  const g = el("g", { class: "title" }, svg);
  el("rect", { x: 560, y: 780, width: 610, height: 50 }, g);
  el("line", { x1: 1060, y1: 780, x2: 1060, y2: 830 }, g);
  el("line", { x1: 560, y1: 795, x2: 1170, y2: 795 }, g);
  txt(g, 620, 808, S.doc.title || "", 8);
  txt(g, 620, 824, S.doc.doc_no || "", 7);
  txt(g, 1070, 792, "SHEET NO.", 5);
  txt(g, 1068, 815, S.doc.sheet_no || "", 9);
}
const SHAPE_KINDS = ["AND", "OR", "NOT"];
function shapeGeom(g, b) {               // L58 — 서버 draw.shape_geometry 와 같은 자 (알다프라 양식: 모양 게이트 · PB 칸 · ANN 타원)
  const x = b.x, y = b.y, w = b.w, h = b.h;
  if (b.kind === "PB") {
    g = { ...g, texts: [[x + 2.2, y + h * 0.3, "P", 3.0], [x + 2.2, y + h * 0.72, "B", 3.0], [x + 5.0 + (w - 5.0) / 2, y + h / 2, b.label || "PB", Math.min(h * 0.6, 5.0)]], lines: [[x + 5.0, y, x + 5.0, y + h]] };
    return g;
  }
  if (b.kind === "ANN") return { ...g, box: null, ellipse: [x, y, x + w, y + h] };
  if (!SHAPE_KINDS.includes(b.kind)) return g;
  g = { ...g, texts: g.texts.filter(t => t[1] !== y + h / 2) };
  if (b.kind === "OR") { const r = Math.min(w, h) / 2; g.circle = [x + r, y + h / 2, r]; g.box = null; g.pointer = null; if (w > 2 * r + 0.5) g.lines = [[x + 2 * r, y + h / 2, x + w, y + h / 2]]; }
  else if (b.kind === "NOT") g.lines = [[x, y, x + w, y + h], [x, y + h, x + w, y]];
  return g;
}
function renderBlock(parent, b, bad) {
  let g = geom(b);
  if (S.doc && S.doc.form === "a5j") g = shapeGeom(g, b);
  for (const ln of g.lines || []) el("line", { x1: ln[0], y1: ln[1], x2: ln[2], y2: ln[3] }, parent);
  if (g.ellipse) el("ellipse", { cx: (g.ellipse[0] + g.ellipse[2]) / 2, cy: (g.ellipse[1] + g.ellipse[3]) / 2, rx: (g.ellipse[2] - g.ellipse[0]) / 2, ry: (g.ellipse[3] - g.ellipse[1]) / 2, class: "blk" }, parent);
  const grp = el("g", { class: "blk" + (S.sel.has(b.id) ? " sel" : "") + (bad ? " bad" : ""), "data-id": b.id }, parent);
  const bb = bboxOf(b);
  el("rect", { x: bb[0] - 2, y: bb[1] - 2, width: bb[2] - bb[0] + 4, height: bb[3] - bb[1] + 4, class: "hit" }, grp);
  if (g.circle) {
    el("circle", { cx: g.circle[0], cy: g.circle[1], r: g.circle[2] }, grp);
    if (g.pointer) el("polygon", { points: g.pointer.map(p => p.join(",")).join(" ") }, grp);
  } else if (g.cells.length) {
    for (const c of g.cells) el("rect", { x: c[0], y: c[1], width: c[2] - c[0], height: c[3] - c[1] }, grp);
  } else if (g.box) {
    el("rect", { x: g.box[0], y: g.box[1], width: g.box[2] - g.box[0], height: g.box[3] - g.box[1] }, grp);
  } else {
    el("rect", { x: b.x, y: b.y, width: b.w, height: b.h, fill: "none", stroke: S.sel.has(b.id) ? "#2f5bd8" : "none", "stroke-dasharray": "1 1" }, grp);
  }
  if (g.bar) el("line", { x1: g.bar[0], y1: g.bar[1], x2: g.bar[2], y2: g.bar[3] }, grp);
  for (const [cx, cy, t, fs, anc] of g.texts) if (t) { const e = el("text", { x: cx, y: cy, "font-size": fs, "text-anchor": anc === "start" ? "start" : anc === "end" ? "end" : "middle", class: anc ? "pin" : null }, grp); e.textContent = t; }
  if (S.sym[b.kind].macro) grp.classList.add("macro");
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
  if (gg.circle) { el("circle", { cx: gg.circle[0], cy: gg.circle[1], r: gg.circle[2] }, g); if (gg.pointer) el("polygon", { points: gg.pointer.map(p => p.join(",")).join(" ") }, g); }
  else if (gg.cells.length) for (const c of gg.cells) el("rect", { x: c[0], y: c[1], width: c[2] - c[0], height: c[3] - c[1] }, g);
  else if (gg.box) el("rect", { x: gg.box[0], y: gg.box[1], width: gg.box[2] - gg.box[0], height: gg.box[3] - gg.box[1] }, g);
  if (gg.bar) el("line", { x1: gg.bar[0], y1: gg.bar[1], x2: gg.bar[2], y2: gg.bar[3] }, g);
  for (const [cx, cy, t, fs] of gg.texts.slice(0, 2)) { const e = el("text", { x: cx, y: cy, "font-size": fs }, g); e.textContent = t; }
  return svg;
}
function buildPalette() {
  const pal = $("#palette"); pal.innerHTML = "";
  for (const kind in S.sym) {
    if (S.sym[kind].macro) continue;                    // 매크로는 Typical 타입마다 — 아래 '매크로' 카드
    const btn = document.createElement("button");
    btn.title = `${S.sym[kind].name} — 누르면 가운데에 놓입니다${S.sym[kind].learned ? ` · 크기는 분석한 로직 ${S.sym[kind].learned}개에서 배운 값` : ""}`;
    btn.appendChild(paletteIcon(kind));
    const sp = document.createElement("span"); sp.textContent = S.sym[kind].name; btn.appendChild(sp);
    btn.draggable = true;
    btn.ondragstart = e => { e.dataTransfer.setData("text/kind", kind); };
    btn.onclick = () => { if (!S.doc) return; const L = layout(); addBlock(kind, (L.LX0 + L.LX1) / 2, L.TOP + L.PITCH * 6); };
    pal.appendChild(btn);
  }
  // L57 — 글자 상자 보기: 뜻은 글자가 정한다 (상수 · ISA 약어 · 이음점 · 토글 · STEP · 감시 · 아날로그 연산 …)
  if (S.presets && S.presets.length) {
    const h = document.createElement("div"); h.className = "dw-palhead"; h.textContent = "글자 상자 — 뜻은 글자가 정합니다"; pal.appendChild(h);
    for (const pr of S.presets) {
      const btn = document.createElement("button");
      btn.title = `${pr.name} — ${pr.hint}${pr.note ? " · 장 NOTE 에 정의 문장을 더합니다" : ""}`;
      const ic = document.createElement("span"); ic.className = "dw-preicon"; ic.textContent = pr.text; btn.appendChild(ic);
      const sp = document.createElement("span"); sp.textContent = pr.name; btn.appendChild(sp);
      btn.draggable = true;
      btn.ondragstart = e => { e.dataTransfer.setData("text/kind", "BOX"); e.dataTransfer.setData("text/preset", pr.text); };
      btn.onclick = () => { if (!S.doc) return; const L = layout(); addPreset(pr, (L.LX0 + L.LX1) / 2, L.TOP + L.PITCH * 6); };
      pal.appendChild(btn);
    }
  }
}
function addPreset(pr, cx, cy) {
  if (!S.doc) return;
  addBlock(pr.kind || "BOX", cx, cy);
  const b = S.doc.blocks[S.doc.blocks.length - 1];
  b.text = pr.text; if (pr.w) b.w = pr.w; if (pr.h) b.h = pr.h; b.param = b.param || {};
  if (pr.time) b.param.t = 5;
  if (pr.lines) b.param.lines = pr.lines.map(x => x.slice());
  if (pr.above) b.param.above = pr.above;
  if (pr.note) { const notes = notesFromForm(); if (!notes.includes(pr.note)) { notes.push(pr.note); $("#f-notes").value = notes.join("\n"); S.doc.notes = notes; } }
  markDirty(); render();
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
      <label>화살촉 <select id="p-arrow"><option value="" ${!w.arrow ? "selected" : ""}>없음</option><option value="end" ${w.arrow === "end" ? "selected" : ""}>끝에 (받는 쪽)</option><option value="start" ${w.arrow === "start" ? "selected" : ""}>처음에</option></select></label>
      <label>선 아래 글 <input id="p-wlabel" value="${esc(w.label || "")}" placeholder="0~250 barg · 신호 이름"></label>
      <label>연결점 <span><button id="p-dot" type="button">끝에 점 찍기</button> ${(w.dots || []).length ? `<button id="p-dot-clear" type="button">점 지우기 (${w.dots.length})</button>` : ""}</span></label>
      <label>인터페이스 표시 <span><button id="p-mark-d" type="button">◆ 처음에</button><button id="p-mark-s" type="button">■ 끝에</button> ${(w.marks || []).length ? `<button id="p-mark-clear" type="button">표시 지우기 (${w.marks.length})</button>` : ""}</span></label>
      <p class="dw-hint">점 ${w.pts.length}개 — 점을 끌어 옮기고, Delete 로 지웁니다.  다른 선의 몸통에 닿는 끝에는 연결점을 찍어야 분석기가 잇습니다 (범례 DOT).</p>`;
    $("#p-dashed").onchange = e => { pushUndo(); w.dashed = e.target.checked; markDirty(); render(); };
    $("#p-wlabel").onchange = e => { pushUndo(); const v = e.target.value.trim().slice(0, 40); if (v) w.label = v; else delete w.label; markDirty(); render(); };
    $("#p-arrow").onchange = e => { pushUndo(); if (e.target.value) w.arrow = e.target.value; else delete w.arrow; markDirty(); render(); };
    $("#p-dot").onclick = () => { pushUndo(); w.dots = (w.dots || []).concat([w.pts[w.pts.length - 1].slice()]); markDirty(); render(); };
    if ($("#p-dot-clear")) $("#p-dot-clear").onclick = () => { pushUndo(); delete w.dots; markDirty(); render(); };
    $("#p-mark-d").onclick = () => { pushUndo(); const p0 = w.pts[0], p1 = w.pts[1] || p0; w.marks = (w.marks || []).concat([[p0[0] + Math.sign(p1[0] - p0[0]) * 0.5 * layout().PITCH, p0[1], "diamond"]]); markDirty(); render(); };
    $("#p-mark-s").onclick = () => { pushUndo(); const n = w.pts.length, p0 = w.pts[n - 1], p1 = w.pts[n - 2] || p0; w.marks = (w.marks || []).concat([[p0[0] + Math.sign(p1[0] - p0[0]) * 0.5 * layout().PITCH, p0[1], "square"]]); markDirty(); render(); };
    if ($("#p-mark-clear")) $("#p-mark-clear").onclick = () => { pushUndo(); delete w.marks; markDirty(); render(); };
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
  if (spec.circle && !spec.lamp) h += `<label>글자 <input id="p-text" value="${esc(b.text)}" maxlength="2"></label>
    <label>꼭지 방향 <select id="p-point">${[["R", "오른쪽 →"], ["L", "왼쪽 ←"], ["T", "위 ↑"], ["B", "아래 ↓"]].map(([k, n]) => `<option value="${k}" ${(b.param.point || "R") === k ? "selected" : ""}>${n}</option>`).join("")}</select></label>
    <p class="dw-hint">같은 글자의 연결 기호는 한 신호 — 원 몸통에 닿은 선이 들어가고 꼭지에서 나갑니다.</p>`;
  if (spec.lamp) h += `<label>글자 <input id="p-text" value="${esc(b.text)}" maxlength="2" placeholder="G"></label><p class="dw-hint">표시등 — 들어오는 선만 (G · R · W · Y …).</p>`;
  if (spec.note || spec.box) h += `<label>글 <input id="p-text" value="${esc(b.text)}"></label>${spec.box ? `<p class="dw-hint">분석기는 상자 안 글자로 뜻을 읽습니다 — 신호 이름(OPEN · REMOTE) · DI · 연산 이름(∑ · T …).</p>` : ""}`;
  if (spec.macro) {
    const p = b.param, ms = (S.setInfo && S.setInfo.macros) || [];
    h += `<label>이름 <input id="p-mtitle" value="${esc(p.title || "")}"></label>
      <label>Typical <select id="p-mtyp"><option value="">(없음)</option>${ms.map(m => `<option value="${esc(m.typ)}" ${m.typ === p.typ ? "selected" : ""}>${esc(m.title)} · ${esc(m.typ)}</option>`).join("")}</select></label>
      <p class="dw-hint">입력 ${(p.pins_in || []).length} · 출력 ${(p.pins_out || []).length} — 단자 이름은 Typical 시트의 TAG NO. 칸(약어)과 같아야 분석기가 잇습니다.</p>
      <div class="dw-pins">${(p.pins_in || []).map((q, i) => `<span class="in"><input data-pin="in:${i}" value="${esc(q.name)}"></span>`).join("")}${(p.pins_out || []).map((q, i) => `<span class="out"><input data-pin="out:${i}" value="${esc(q.name)}"></span>`).join("")}</div>
      ${p.typ && !p.typ.startsWith("lib:") ? `<button id="p-open-typ" type="button">Typical 시트 열기</button>` : ""}`;
  }
  if (!spec.note) h += `<label>위 글 <input id="p-above" value="${esc(b.param.above || "")}" placeholder="설정값 202.4 barg · HH : 191 · 주석"></label><p class="dw-hint">블록 바로 위에 인쇄 — 감시 블록이면 분석기가 설정값으로 읽고 시뮬레이션의 초기값이 됩니다.</p>`;
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
  on("#p-point", t => { b.param.point = t.value; });
  on("#p-above", t => { const v = t.value.trim().slice(0, 40); if (v) b.param.above = v; else delete b.param.above; });
  on("#p-mtitle", t => { b.param.title = t.value.trim().slice(0, 120); });
  on("#p-mtyp", t => { b.param.typ = t.value; const m = ((S.setInfo && S.setInfo.macros) || []).find(m => m.typ === t.value); if (m) { b.param.title = m.title; const L2 = layout(); b.param.pins_in = m.pins_in.map((q, i) => ({ name: q.name, row: q.row, dy: +(1.6 * L2.PITCH + (i + 0.5) * L2.PITCH).toFixed(2) })); b.param.pins_out = m.pins_out.map((q, i) => ({ name: q.name, row: q.row, dy: +(1.6 * L2.PITCH + (i + 0.5) * L2.PITCH).toFixed(2) })); b.h = +(1.6 * L2.PITCH + Math.max(m.pins_in.length, m.pins_out.length, 1) * L2.PITCH + 0.4 * L2.PITCH).toFixed(2); } });
  $$("#props input[data-pin]").forEach(inp => inp.onchange = () => upd(() => { const [side, i] = inp.dataset.pin.split(":"); const arr = side === "in" ? b.param.pins_in : b.param.pins_out; if (arr && arr[+i]) arr[+i].name = inp.value.trim().slice(0, 40); }));
  if ($("#p-open-typ")) $("#p-open-typ").onclick = () => { const sh = ((S.setInfo && S.setInfo.sheets) || []).find(x => x.sheet_no === b.param.typ); if (sh) openDoc(sh.id); else toast("이 묶음에 그 Typical 시트가 없습니다."); };
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
function markDirty() { S.dirty = true; $("#save").disabled = false; status("저장하지 않은 변경이 있습니다"); simSoon(); }
function deleteSel() {
  if (!S.sel.size && !S.selWire) return;
  pushUndo();
  S.doc.blocks = S.doc.blocks.filter(b => !S.sel.has(b.id));
  if (S.selWire) S.doc.wires = S.doc.wires.filter(w => w.id !== S.selWire);
  S.sel = new Set(); S.selWire = null; markDirty(); render();
}
function copySel() {                     // L56 — 고른 블록과 그 사이 선을 복사 (Ctrl+C) · 붙이면 한 행 아래 (Ctrl+V)
  const ids = new Set(S.sel); if (!ids.size) return;
  const blocks = S.doc.blocks.filter(b => ids.has(b.id)).map(b => JSON.parse(JSON.stringify(b)));
  const inside = (p) => blocks.some(b => p[0] >= b.x - 1 && p[0] <= b.x + b.w + 1 && p[1] >= b.y - 1 && p[1] <= b.y + b.h + 1);
  const wires = S.doc.wires.filter(w => inside(w.pts[0]) && inside(w.pts[w.pts.length - 1])).map(w => JSON.parse(JSON.stringify(w)));
  S.clip = { blocks, wires }; status(`복사 — 블록 ${blocks.length} · 선 ${wires.length} (Ctrl+V 붙이기)`);
}
function pasteClip() {
  if (!S.clip || !S.doc) return;
  pushUndo();
  const L = layout(), dy = 2 * L.PITCH, nsel = new Set();
  for (const b of S.clip.blocks) { const nb = JSON.parse(JSON.stringify(b)); nb.id = newId("b"); nb.y += dy; S.doc.blocks.push(nb); nsel.add(nb.id); }
  for (const w of S.clip.wires) { const nw = JSON.parse(JSON.stringify(w)); nw.id = newId("w"); nw.pts = nw.pts.map(p => [p[0], p[1] + dy]); if (nw.dots) nw.dots = nw.dots.map(p => [p[0], p[1] + dy]); S.doc.wires.push(nw); }
  S.clip = { blocks: S.clip.blocks.map(b => ({ ...b, y: b.y + dy })), wires: S.clip.wires.map(w => ({ ...w, pts: w.pts.map(p => [p[0], p[1] + dy]), dots: (w.dots || []).map(p => [p[0], p[1] + dy]) })) };
  S.sel = nsel; S.selWire = null; markDirty(); render();
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
    const last = S.wip.pts[S.wip.pts.length - 1];
    const route = S.wip.cur ? routePick(last, S.wip.cur) : [];
    // L59 — 다른 경로 후보는 옅게, 고른 경로는 진하게 (Tab 으로 바꾼다 · 누르면 그 경로가 선이 된다)
    for (const alt of (S.wip.routes || []).slice(0, 4)) if (alt !== S.wip.routes[S.wip.ri || 0]) el("polyline", { points: [last].concat(alt.slice(1)).map(p => p.join(",")).join(" "), class: "wipalt" }, ov);
    const pts = S.wip.pts.concat(route);
    el("polyline", { points: pts.map(p => p.join(",")).join(" "), class: "wipline" }, ov);
    if (S.wip.hot) el("circle", { cx: S.wip.hot[0], cy: S.wip.hot[1], r: 2.6, class: "port hot" }, ov);
  }
  if (S.drag && S.drag.marquee) { const m = S.drag.marquee; el("rect", { x: Math.min(m[0], m[2]), y: Math.min(m[1], m[3]), width: Math.abs(m[2] - m[0]), height: Math.abs(m[3] - m[1]), class: "marquee" }, ov); }
  drawAlign(ov); drawCross(ov);
}
function markPolygon(x, y, kind) {
  // 서버 draw.mark_polygon 과 같은 자 — 반 폭 0.27P (◆) · 0.8 배 (■)
  const r = 0.27 * layout().PITCH;
  if (kind === "square") { const q = r * 0.8; return [[x - q, y - q], [x + q, y - q], [x + q, y + q], [x - q, y + q]]; }
  return [[x, y - r], [x + r, y], [x, y + r], [x - r, y]];
}

function arrowOf(w) {
  const a = w.arrow, pts = w.pts || []; if ((a !== "start" && a !== "end") || pts.length < 2) return null;
  const AL = 0.22 * layout().PITCH, [tip, back] = a === "start" ? [pts[0], pts[1]] : [pts[pts.length - 1], pts[pts.length - 2]];
  const dx = back[0] - tip[0], dy = back[1] - tip[1], n = Math.hypot(dx, dy) || 1, ux = dx / n, uy = dy / n;
  const bx = tip[0] + ux * AL, by = tip[1] + uy * AL, hx = -uy * AL * 0.5, hy = ux * AL * 0.5;
  return [[tip[0], tip[1]], [bx + hx, by + hy], [bx - hx, by - hy]];
}
/* ───────── L59 — 선 자동 경로 ─────────
   한 점에서 다음 점까지 직각으로 꺾인 경로 후보(ㄱ 둘 · ㄹ 여럿)를 만들고, 블록 상자를 지나지 않고 · 다른 선과 겹치지 않고 ·
   꺾임이 적고 · 단자·행 자리에는 가로로 들어가는 것을 고른다.  고른 경로는 미리보기(점선)로 보이고, 누르면 그대로 선이 된다.
   Tab 이 다음 후보로.  상수는 없다 — 간격은 행 간격(PITCH)의 배율. */
function routeObstacles(a, b) {
  const L = layout(), pad = 0.35 * L.PITCH, out = [];
  for (const blk of S.doc.blocks) {
    if (S.sym[blk.kind].note) continue;
    const bb = bboxOf(blk), box = [bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad];
    const touches = q => q[0] >= bb[0] - 1.2 * L.PITCH && q[0] <= bb[2] + 1.2 * L.PITCH && q[1] >= bb[1] - pad && q[1] <= bb[3] + pad;
    if (touches(a) || touches(b)) continue;                        // 그 끝이 닿는 블록(출발 · 도착 단자)은 장애물이 아니다
    out.push(box);
  }
  return out;
}
function segHitsBox(p, q, box) {
  const x0 = Math.min(p[0], q[0]), x1 = Math.max(p[0], q[0]), y0 = Math.min(p[1], q[1]), y1 = Math.max(p[1], q[1]);
  return x1 > box[0] && x0 < box[2] && y1 > box[1] && y0 < box[3];
}
function segOverlapsWires(p, q) {
  // 같은 직선 위에서 다른 선과 겹치는 길이 (겹쳐 그리면 분석기가 한 선으로 읽는다)
  let ov = 0;
  const hz = Math.abs(p[1] - q[1]) < 0.2, vt = Math.abs(p[0] - q[0]) < 0.2;
  for (const w of S.doc.wires) for (let i = 1; i < w.pts.length; i++) {
    const c = w.pts[i - 1], d = w.pts[i];
    if (hz && Math.abs(c[1] - d[1]) < 0.2 && Math.abs(c[1] - p[1]) < 0.6) ov += Math.max(0, Math.min(Math.max(p[0], q[0]), Math.max(c[0], d[0])) - Math.max(Math.min(p[0], q[0]), Math.min(c[0], d[0])));
    if (vt && Math.abs(c[0] - d[0]) < 0.2 && Math.abs(c[0] - p[0]) < 0.6) ov += Math.max(0, Math.min(Math.max(p[1], q[1]), Math.max(c[1], d[1])) - Math.max(Math.min(p[1], q[1]), Math.min(c[1], d[1])));
  }
  return ov;
}
function routeScore(path, boxes, endKind) {
  let len = 0, hits = 0, ov = 0, cross = 0;
  for (let i = 1; i < path.length; i++) {
    const p = path[i - 1], q = path[i];
    len += Math.abs(q[0] - p[0]) + Math.abs(q[1] - p[1]);
    for (const bx of boxes) if (segHitsBox(p, q, bx)) hits++;
    ov += segOverlapsWires(p, q);
    for (const w of S.doc.wires) for (let j = 1; j < w.pts.length; j++) if (segsCross(p, q, w.pts[j - 1], w.pts[j])) cross++;
  }
  const bends = Math.max(0, path.length - 2);
  const lastHz = path.length >= 2 && Math.abs(path[path.length - 1][1] - path[path.length - 2][1]) < 0.2;
  const firstHz = path.length >= 2 && Math.abs(path[0][1] - path[1][1]) < 0.2;
  let sc = bends * 3 + len * 0.02 + hits * 60 + ov * 4 + cross * 1.5;
  if ((endKind === "row" || endKind === "port") && !lastHz) sc += 6;     // 단자 · 행 자리에는 가로로 들어간다
  if (S.wip && S.wip.startKind && S.wip.startKind !== "grid" && S.wip.pts.length === 1 && !firstHz) sc += 6;
  return sc;
}
function segsCross(p, q, c, d) {
  const hz1 = Math.abs(p[1] - q[1]) < 0.2, hz2 = Math.abs(c[1] - d[1]) < 0.2;
  if (hz1 === hz2) return false;
  const [h0, h1, v0, v1] = hz1 ? [p, q, c, d] : [c, d, p, q];
  const x = v0[0], y = h0[1];
  return Math.min(h0[0], h1[0]) + 0.3 < x && x < Math.max(h0[0], h1[0]) - 0.3 && Math.min(v0[1], v1[1]) + 0.3 < y && y < Math.max(v0[1], v1[1]) - 0.3;
}
function routeCandidates(a, b) {
  const L = layout(), P = L.PITCH, out = [];
  const same = (u, v) => Math.abs(u[0] - v[0]) < 0.01 && Math.abs(u[1] - v[1]) < 0.01;
  const clean = path => path.filter((p, i) => i === 0 || !same(p, path[i - 1]));
  if (Math.abs(a[0] - b[0]) < 0.01 || Math.abs(a[1] - b[1]) < 0.01) {
    // 한 직선 — 그대로가 첫 후보 · 사이에 블록이 있으면 한두 행 비켜 돌아가는 ㄷ 길도 후보
    out.push([a, b]);
    const hz = Math.abs(a[1] - b[1]) < 0.01, sgn = hz ? Math.sign(b[0] - a[0]) : Math.sign(b[1] - a[1]), gap = P / 2 * sgn;
    for (const off of [P, -P, 2 * P, -2 * P]) {
      if (hz) out.push(clean([a, [a[0] + gap, a[1]], [a[0] + gap, a[1] + off], [b[0] - gap, a[1] + off], [b[0] - gap, b[1]], b]));
      else out.push(clean([a, [a[0], a[1] + gap], [a[0] + off, a[1] + gap], [a[0] + off, b[1] - gap], [b[0], b[1] - gap], b]));
    }
    return out;
  }
  out.push(clean([a, [b[0], a[1]], b]), clean([a, [a[0], b[1]], b]));
  const x0 = Math.min(a[0], b[0]), x1 = Math.max(a[0], b[0]), y0 = Math.min(a[1], b[1]), y1 = Math.max(a[1], b[1]);
  const seen = new Set();
  const addX = mx => { const k = "x" + mx.toFixed(1); if (seen.has(k)) return; seen.add(k); out.push(clean([a, [mx, a[1]], [mx, b[1]], b])); };
  const addY = my => { const k = "y" + my.toFixed(1); if (seen.has(k)) return; seen.add(k); out.push(clean([a, [a[0], my], [b[0], my], b])); };
  addX((a[0] + b[0]) / 2); addY((a[1] + b[1]) / 2);
  for (let mx = Math.ceil(x0 / (P / 2)) * (P / 2); mx <= x1; mx += P / 2) if (mx > x0 + 0.5 && mx < x1 - 0.5) addX(mx);
  for (let my = Math.ceil((y0 - L.TOP) / (P / 2)) * (P / 2) + L.TOP; my <= y1; my += P / 2) if (my > y0 + 0.5 && my < y1 - 0.5) addY(my);
  // 두 점을 지나는 띠 밖으로 한 행 돌아가는 길 (사이가 전부 막혔을 때)
  for (const dy of [-P, P, -2 * P, 2 * P]) addY((a[1] < b[1] ? y0 : y1) + dy);
  return out;
}
function routePick(a, b) {
  const sp = S.wip && S.wip.cur ? S.wip.hot : null;
  const endKind = sp ? sp[2] : "grid";
  const boxes = routeObstacles(a, b);
  const cands = routeCandidates(a, b).map(path => ({ path, sc: routeScore(path, boxes, endKind) })).sort((u, v) => u.sc - v.sc);
  const key = a.join(",") + ">" + b.join(",");
  if (!S.wip.routeKey || S.wip.routeKey !== key) { S.wip.routeKey = key; S.wip.ri = 0; }
  S.wip.routes = cands.map(c => c.path);
  const pick = S.wip.routes[Math.min(S.wip.ri || 0, S.wip.routes.length - 1)] || [a, b];
  return pick.slice(1);
}
function orth(a, b) {
  // 직각 꺾임 — 가로 먼저 · 두 좌표가 다 다르면 꺾이는 점을 하나 넣는다 (완전히 가로·세로면 그대로)
  if (Math.abs(a[0] - b[0]) < 0.01 || Math.abs(a[1] - b[1]) < 0.01) return [b];
  return [[b[0], a[1]], b];
}
function onWireBody(pt, skipId) {
  for (const w of S.doc.wires) { if (w.id === skipId) continue; for (let i = 1; i < w.pts.length; i++) { const a = w.pts[i - 1], b = w.pts[i]; const hz = Math.abs(a[1] - b[1]) < 0.2, vt = Math.abs(a[0] - b[0]) < 0.2;
    if (hz && Math.abs(pt[1] - a[1]) < 0.6 && Math.min(a[0], b[0]) + 0.8 < pt[0] && pt[0] < Math.max(a[0], b[0]) - 0.8) return [pt[0], a[1]];
    if (vt && Math.abs(pt[0] - a[0]) < 0.6 && Math.min(a[1], b[1]) + 0.8 < pt[1] && pt[1] < Math.max(a[1], b[1]) - 0.8) return [a[0], pt[1]]; } }
  return null;
}
function finishWire() {
  if (S.wip && S.wip.pts.length >= 2) {
    pushUndo();
    const pts = S.wip.pts.filter((p, i, a) => i === 0 || Math.hypot(p[0] - a[i - 1][0], p[1] - a[i - 1][1]) > 0.01).map(p => [+p[0].toFixed(2), +p[1].toFixed(2)]);
    if (pts.length >= 2) {
      const w = { id: newId("w"), pts, dashed: S.tool === "dash" };
      // 끝이 다른 선의 몸통에 닿으면 연결점 (범례: 점이 연결 · 몸통 교차는 연결 아님) — 사람이 그리면 저절로
      const dots = [];
      for (const e of [pts[0], pts[pts.length - 1]]) { const d = onWireBody(e, null); if (d) dots.push(d); }
      if (dots.length) w.dots = dots;
      S.doc.wires.push(w);
    }
    markDirty();
  }
  S.wip = null; render();
}
function bindStage() {
  const stage = $("#stage"), svg = $("#svg");
  stage.addEventListener("dragover", e => e.preventDefault());
  stage.addEventListener("drop", e => { const k = e.dataTransfer.getData("text/kind"); if (k && S.doc) { e.preventDefault(); const p = svgPt(e); const pt = e.dataTransfer.getData("text/preset"); const pr = pt && (S.presets || []).find(x => x.text === pt); if (pr) addPreset(pr, p[0], p[1]); else addBlock(k, p[0], p[1]); } });
  svg.addEventListener("pointerdown", e => {
    if (!S.doc) return;
    stage.focus();
    const p = svgPt(e), t = e.target;
    if (e.button === 1 || S.tool === "pan" || S.space) { S.drag = { pan: true, x: e.clientX, y: e.clientY, sl: $("#scroll").scrollLeft, st: $("#scroll").scrollTop }; e.preventDefault(); return; }
    if (e.button !== 0) return;
    if (simOn() && S.tool === "select" && !e.shiftKey && simClick(e, p, t)) return;   // L57 — 시뮬레이션: 행 자리 · 신호원 · 게이트 · 선을 눌러 1/0
    if (S.tool === "wire" || S.tool === "dash") {
      const sp = snapPt(p);
      if (!S.wip) { S.wip = { pts: [[sp[0], sp[1]]], cur: null, startKind: sp[2] }; status("선 — 다음 점을 누르면 추천 경로(점선)가 그대로 선이 됩니다 · Tab 다른 경로 · 단자/행 자리에 닿으면 끝"); }
      else {
        const last = S.wip.pts[S.wip.pts.length - 1];
        S.wip.cur = [sp[0], sp[1]]; S.wip.hot = (sp[2] === "row" || sp[2] === "port") ? sp : null;
        for (const q of routePick(last, [sp[0], sp[1]])) S.wip.pts.push(q);          // L59 — 추천 경로가 그대로 선이 된다
        S.wip.routes = null; S.wip.routeKey = null; S.wip.ri = 0;
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
    if (t.classList.contains("golink")) {
      const side = t.dataset.side, n = +t.dataset.n, li = linkInfo(side, n);
      if (side === "left" && li && li.ref && li.ref.did) goRef({ did: li.ref.did, row: li.ref.src_row || li.ref.row });
      else if (side === "right" && li && li.targets) { const t0 = li.targets.find(x => x.did); if (t0) goRef({ did: t0.did, row: t0.row }); }
      return;
    }
    if (t.classList.contains("cell") || t.classList.contains("rowstub")) return;
    S.sel = new Set(); S.selWire = null; S.drag = { marquee: [p[0], p[1], p[0], p[1]] }; render();
  });
  window.addEventListener("pointermove", e => {
    if (!S.doc) return;
    const p = svgPt(e);
    S.hover = p; if (S.guide.ruler) drawRulers();
    if (S.wip) { const sp = snapPt(p); S.wip.cur = [sp[0], sp[1]]; S.wip.hot = (sp[2] === "row" || sp[2] === "port") ? sp : null; drawGhost(); return; }
    if (!S.drag) { if (S.guide.cross) drawGhost(); return; }
    if (S.drag.pan) { $("#scroll").scrollLeft = S.drag.sl - (e.clientX - S.drag.x); $("#scroll").scrollTop = S.drag.st - (e.clientY - S.drag.y); return; }
    if (S.drag.vtx) { const w = S.doc.wires.find(w => w.id === S.drag.id); if (!w) return; const sp = snapPt(p); w.pts[S.drag.i] = [+sp[0].toFixed(2), +sp[1].toFixed(2)]; S.dirty = true; render(); return; }
    if (S.drag.move) {
      const L = layout(), g = S.snap ? L.PITCH / 2 : 0.01;
      let dx = p[0] - S.drag.start[0], dy = p[1] - S.drag.start[1];
      dx = Math.round(dx / g) * g; dy = Math.round(dy / g) * g;
      const raw = Math.abs(dx) > 0.01 || Math.abs(dy) > 0.01;          // 정렬 자석이 되돌려도 '움직였다' 는 사실은 남는다
      [dx, dy] = alignMove([...S.sel], dx, dy);
      if (!S.drag.moved && raw) { S.drag.moved = true; pushUndo(); }
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
    S.drag = null; S.alignLines = null; drawGhost(); $("#stage").style.cursor = S.tool === "pan" ? "grab" : S.tool === "select" ? "default" : "crosshair";
  });
  svg.addEventListener("dblclick", e => {
    if (!S.doc) return;
    const t = e.target;
    if (S.wip) { S.wip.pts.pop(); finishWire(); return; }
    if (t.classList.contains("cell")) { editCell(t); return; }
    const blk = t.closest(".blk");
    if (blk) { const b = S.doc.blocks.find(b => b.id === blk.dataset.id); const sp = S.sym[b.kind]; const inp = $(sp.label ? "#p-label" : (sp.circle || sp.note) ? "#p-text" : sp.time ? "#p-t" : null); if (inp) { inp.focus(); inp.select(); } }
  });
  svg.addEventListener("pointerleave", () => { S.hover = null; drawGhost(); if (S.guide.ruler) drawRulers(); });
  $("#scroll").addEventListener("scroll", () => { if (S.guide.ruler) drawRulers(); });
  window.addEventListener("resize", () => { if (S.guide.ruler) drawRulers(); });
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
    if (e.key === "Escape" && !$("#simmenu").hidden) { simMenuClose(); return; }
    if (e.key === "Escape") { if (S.wip) { S.wip = null; render(); } else { S.sel = new Set(); S.selWire = null; render(); } }
    else if (e.key === "Enter" && S.wip) { finishWire(); }
    else if (e.key === "Tab" && S.wip && S.wip.routes && S.wip.routes.length > 1) { e.preventDefault(); S.wip.ri = ((S.wip.ri || 0) + 1) % S.wip.routes.length; drawGhost(); status(`경로 ${S.wip.ri + 1}/${S.wip.routes.length}`); }
    else if (e.key === "Delete" || e.key === "Backspace") { e.preventDefault(); deleteSel(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "z") { e.preventDefault(); e.shiftKey ? redo() : undo(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "d") { e.preventDefault(); duplicateSel(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "c" && S.sel.size) { e.preventDefault(); copySel(); }
    else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "v" && S.clip) { e.preventDefault(); pasteClip(); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); moveSel(-(e.shiftKey ? L.PITCH : L.PITCH / 2), 0); }
    else if (e.key === "ArrowRight") { e.preventDefault(); moveSel(e.shiftKey ? L.PITCH : L.PITCH / 2, 0); }
    else if (e.key === "ArrowUp") { e.preventDefault(); moveSel(0, -(e.shiftKey ? L.PITCH : L.PITCH / 2)); }
    else if (e.key === "ArrowDown") { e.preventDefault(); moveSel(0, e.shiftKey ? L.PITCH : L.PITCH / 2); }
    else if (e.key === "v" || e.key === "V") setTool("select");
    else if (e.key === "w" || e.key === "W") setTool("wire");
    else if (e.key === "d" || e.key === "D") setTool("dash");
    else if (e.key === "h" || e.key === "H") setTool("pan");
    else if (e.key === "g" || e.key === "G") { S.guide.grid = !S.guide.grid; $("#g-grid").checked = S.guide.grid; saveGuide(); render(); }
    else if (e.key === "r" || e.key === "R") { S.guide.ruler = !S.guide.ruler; $("#g-ruler").checked = S.guide.ruler; saveGuide(); drawRulers(); }
    else if (e.key === " ") { S.space = true; }
  });
  document.addEventListener("keyup", e => { if (e.key === " ") S.space = false; });
  document.addEventListener("keydown", e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") { e.preventDefault(); if (S.doc) save(); } });
}
function setZoom(z) { S.zoom = Math.max(0.3, Math.min(6, z)); $("#zval").textContent = Math.round(S.zoom * 100) + "%"; const L = layout(); const svg = $("#svg"); svg.setAttribute("width", L.W * S.zoom); svg.setAttribute("height", L.H * S.zoom); drawRulers(); }
function fitZoom() { const sc = $("#scroll"); const L = layout(); setZoom(Math.min((sc.clientWidth - 30) / L.W, (sc.clientHeight - 30) / L.H)); }


/* ───────── 모눈종이 (L55 · 화면 전용 — 내보내기에는 없다) ─────────
   가로: 반 행마다 가는 선 · 행마다 중간 선 · 5행마다 굵은 선 (행 번호를 LOGIC 영역 왼쪽 안에 작게)
   세로: 같은 간격(반 행 = 5.65pt)으로 가는 선 · 5행 폭마다 굵은 선.  전부 LOGIC 영역 안에만 그린다. */
function renderGrid(svg, L) {
  if (!S.guide.grid) return;
  const g = el("g", { class: "grid" }, svg), half = L.PITCH / 2;
  for (let k = 0; k <= 2 * L.N; k++) {
    const yy = L.TOP + k * half, row = k % 2 === 0 && (k / 2) % 5 === 0, major = k % 2 === 0;
    el("line", { x1: L.LX0, y1: yy, x2: L.LX1, y2: yy, class: row ? "g5" : major ? "g1" : "gh" }, g);
    if (row && k > 0 && k / 2 < L.N) txt(g, L.LX0 + 1.5, yy - 1, String(k / 2 + 1), 3.6).setAttribute("class", "gnum");
  }
  const nx = Math.floor((L.LX1 - L.LX0) / half);
  for (let k = 0; k <= nx; k++) {
    const xx = L.LX0 + k * half;
    el("line", { x1: xx, y1: L.TOP, x2: xx, y2: L.bottom, class: k % 10 === 0 ? "g5" : k % 2 === 0 ? "g1" : "gh" }, g);
  }
  el("rect", { x: L.LX0, y: L.TOP, width: L.LX1 - L.LX0, height: L.bottom - L.TOP, class: "gframe" }, g);
}

/* ───────── 눈금자 (화면 위에 고정 · 스크롤·확대를 따라간다) ─────────
   위: pt (10pt 눈금 · 50pt 숫자) · 왼쪽: 행 번호 (행마다 눈금 · 5행마다 숫자) + 표 밖은 pt.  마우스 자리는 붉은 표식. */
function drawRulers() {
  const top = $("#ruler-x"), left = $("#ruler-y"), on = !!(S.doc && S.guide.ruler);
  top.hidden = left.hidden = !on; $("#ruler-corner").hidden = !on; $("#stage").classList.toggle("rulers", on);
  if (!on) return;
  const sc = $("#scroll"), L = layout(), z = S.zoom, M = 12;        // #svg 의 margin 12px
  const dpr = window.devicePixelRatio || 1;
  const fit = (c, w, h) => { if (c.width !== Math.round(w * dpr) || c.height !== Math.round(h * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); } c.style.width = w + "px"; c.style.height = h + "px"; const x = c.getContext("2d"); x.setTransform(dpr, 0, 0, dpr, 0, 0); return x; };
  const W = sc.clientWidth, H = sc.clientHeight, RS = 22;
  const toX = v => M + v * z - sc.scrollLeft, toY = v => M + v * z - sc.scrollTop;
  // 위
  let ctx = fit(top, W, RS); ctx.clearRect(0, 0, W, RS); ctx.fillStyle = "#f6f4ec"; ctx.fillRect(0, 0, W, RS);
  ctx.strokeStyle = "#8a93a8"; ctx.fillStyle = "#4a5366"; ctx.font = "9px Helvetica, Arial, sans-serif"; ctx.textAlign = "center"; ctx.lineWidth = 1;
  const step = z >= 2 ? 5 : z >= 0.9 ? 10 : 20, lab = step * 5;
  ctx.beginPath();
  for (let v = 0; v <= L.W; v += step) { const x = Math.round(toX(v)) + 0.5; if (x < 0 || x > W) continue; const big = v % lab === 0; ctx.moveTo(x, RS); ctx.lineTo(x, RS - (big ? 9 : v % (step * 2) === 0 ? 6 : 3)); if (big) ctx.fillText(String(v), x, 9); }
  ctx.stroke();
  // LOGIC 영역 띠
  ctx.fillStyle = "rgba(47,91,216,.10)"; ctx.fillRect(toX(L.LX0), RS - 4, (L.LX1 - L.LX0) * z, 4);
  // 왼쪽
  ctx = fit(left, RS, H); ctx.clearRect(0, 0, RS, H); ctx.fillStyle = "#f6f4ec"; ctx.fillRect(0, 0, RS, H);
  ctx.strokeStyle = "#8a93a8"; ctx.fillStyle = "#4a5366"; ctx.font = "9px Helvetica, Arial, sans-serif"; ctx.textAlign = "right"; ctx.lineWidth = 1;
  ctx.beginPath();
  for (let n = 1; n <= L.N; n++) { const y = Math.round(toY(ry(n))) + 0.5; if (y < 0 || y > H) continue; const big = n % 5 === 0 || n === 1; ctx.moveTo(RS, y); ctx.lineTo(RS - (big ? 9 : 4), y); if (big && z * L.PITCH >= 6) ctx.fillText(String(n), RS - 10, y + 3); }
  for (let v = 0; v <= L.H; v += 50) { if (v >= L.TOP && v <= L.bottom) continue; const y = Math.round(toY(v)) + 0.5; if (y < 0 || y > H) continue; ctx.moveTo(RS, y); ctx.lineTo(RS - 6, y); ctx.fillText(String(v), RS - 8, y + 3); }
  ctx.stroke();
  ctx.fillStyle = "rgba(47,91,216,.10)"; ctx.fillRect(RS - 4, toY(L.TOP), 4, (L.bottom - L.TOP) * z);
  // 마우스 자리
  if (S.hover) {
    const x = toX(S.hover[0]), y = toY(S.hover[1]);
    ctx.fillStyle = "#c2453f"; ctx.fillRect(RS - 12, y - 0.5, 12, 1.2);
    const t = fit(top, W, RS); // 같은 캔버스 다시 — 표식만 얹는다
    const ctx2 = top.getContext("2d"); ctx2.fillStyle = "#c2453f"; ctx2.fillRect(x - 0.5, RS - 12, 1.2, 12);
  }
  const rn = S.hover ? rowAt(S.hover[1]) : null;
  $("#ruler-corner").textContent = S.hover ? `${Math.round(S.hover[0])}, ${Math.round(S.hover[1])}` + (rn ? ` · ${rn}행` : "") : "pt";
}
function rowAt(y) { const L = layout(); if (y < L.TOP || y > L.bottom) return null; return Math.min(L.N, Math.floor((y - L.TOP) / L.PITCH) + 1); }

/* ───────── 십자 안내선 · 정렬 안내선 (overlay 에 그린다) ───────── */
function drawCross(ov) {
  if (!S.guide.cross || !S.hover || S.drag || S.wip) return;
  const L = layout(), [x, y] = S.hover;
  if (x < L.LX0 - 1 || x > L.LX1 + 1 || y < L.TOP - 1 || y > L.bottom + 1) return;
  el("line", { x1: L.LX0, y1: y, x2: L.LX1, y2: y, class: "cross" }, ov);
  el("line", { x1: x, y1: L.TOP, x2: x, y2: L.bottom, class: "cross" }, ov);
  const n = rowAt(y); if (n) { el("circle", { cx: L.LX0, cy: ry(n), r: 2.4, class: "cross-row" }, ov); el("circle", { cx: L.LX1, cy: ry(n), r: 2.4, class: "cross-row" }, ov); }
}
function drawAlign(ov) {
  if (!S.alignLines) return;
  const L = layout();
  for (const a of S.alignLines) {
    if (a.axis === "x") el("line", { x1: a.v, y1: Math.min(a.y0, L.TOP), x2: a.v, y2: Math.max(a.y1, L.bottom), class: "align" }, ov);
    else el("line", { x1: Math.min(a.x0, L.LX0), y1: a.v, x2: Math.max(a.x1, L.LX1), y2: a.v, class: "align" + (a.row ? " row" : "") }, ov);
  }
}
/* 옮기는 블록의 변·가운데를 다른 블록의 변·가운데 · 행 가운데에 맞춘다.  tol 안이면 그 값으로 끌어당기고 안내선을 적는다. */
function alignMove(ids, dx, dy) {
  S.alignLines = null;
  if (!S.guide.align) return [dx, dy];
  const L = layout(), tol = 2.2, moving = new Set(ids);
  const bbs = ids.map(id => { const o = S.drag.orig.find(o => o[0] === id); const b = S.doc.blocks.find(b => b.id === id); return bboxOf({ ...b, x: o[1] + dx, y: o[2] + dy }); });
  const xs = [], ys = [];
  for (const bb of bbs) { xs.push(bb[0], (bb[0] + bb[2]) / 2, bb[2]); ys.push(bb[1], (bb[1] + bb[3]) / 2, bb[3]); }
  const tx = [], ty = [];
  for (const b of S.doc.blocks) { if (moving.has(b.id)) continue; const bb = bboxOf(b); tx.push([bb[0], bb], [(bb[0] + bb[2]) / 2, bb], [bb[2], bb]); ty.push([bb[1], bb, false], [(bb[1] + bb[3]) / 2, bb, false], [bb[3], bb, false]); }
  for (let n = 1; n <= L.N; n++) ty.push([ry(n), [L.LX0, 0, L.LX1, 0], true]);   // 행 가운데 — 선이 행에서 바로 나온다
  let bx = null, by = null;
  for (const x of xs) for (const [v, bb] of tx) { const d = Math.abs(v - x); if (d < tol && (!bx || d < bx.d)) bx = { d, shift: v - x, v, bb }; }
  for (const y of ys) for (const [v, bb, row] of ty) { const d = Math.abs(v - y); if (d < tol && (!by || d < by.d)) by = { d, shift: v - y, v, bb, row }; }
  const lines = [];
  if (bx) { dx += bx.shift; const y0 = Math.min(bx.bb[1], ...bbs.map(b => b[1])), y1 = Math.max(bx.bb[3], ...bbs.map(b => b[3])); lines.push({ axis: "x", v: bx.v, y0, y1 }); }
  if (by) { dy += by.shift; const x0 = Math.min(by.bb[0], ...bbs.map(b => b[0])), x1 = Math.max(by.bb[2], ...bbs.map(b => b[2])); lines.push({ axis: "y", v: by.v, x0, x1, row: by.row }); }
  if (lines.length) S.alignLines = lines;
  return [dx, dy];
}
function saveGuide() { try { localStorage.setItem("logic.draw.guide", JSON.stringify(S.guide)); } catch (e) {} }
function loadGuide() { try { const g = JSON.parse(localStorage.getItem("logic.draw.guide") || "null"); if (g) Object.assign(S.guide, g); } catch (e) {} for (const k in S.guide) { const c = $("#g-" + k); if (c) c.checked = S.guide[k]; } }

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
    N: +$("#f-rows").value || d.N, typical: $("#f-typical").checked, notes: notesFromForm(), left: d.left, right: d.right, blocks: d.blocks, wires: d.wires,
    form: $("#f-form").value, project_name: $("#f-pname").value.trim(), rev: $("#f-rev").value.trim() };
}
function notesFromForm() { return $("#f-notes").value.split("\n").map(t => t.trim()).filter(Boolean).slice(0, 20); }
async function save() {
  if (!S.doc) return;
  const who = author(); if (!who) { toast("이름을 적어 주세요 (머리줄 ✎)."); $("#who").focus(); return; }
  try { localStorage.setItem("pid.author", who); } catch (e) {}
  try {
    const d = await put(`/logic/api/drawings/${S.id}`, { author: who, doc: docOut() });
    S.doc = d; S.dirty = false; $("#save").disabled = true; status(`저장됨 · ${new Date().toLocaleTimeString()} · ${who}`);
    if (S.doc.set) {
      // FROM/TO 자동 잇기 — 이 장이 가리키는 상대 장의 칸을 채운다 (비어 있는 칸만 · 서버가 둘 다 저장)
      try { const r = await post(`/logic/api/drawings/sets/${S.doc.set}/autolink`, { did: S.id, author: who });
        if (r.changed && r.changed.length) { toast(`FROM/TO ${r.changed.length}곳을 이었습니다 — ${r.changed.map(c => c.sheet + "-" + c.n).slice(0, 4).join(", ")}`); S.doc = await api(`/logic/api/drawings/${S.id}`); } } catch (e) {}
    }
    await loadList(S.id); fillForm(); await loadSet(); render();
  } catch (e) { toast("저장 실패 — " + e.message); }
}
function fillForm() {
  const d = S.doc;
  $("#name").value = d.name || ""; $("#name").disabled = false;
  $("#f-sheet").value = d.sheet_no || ""; $("#f-title").value = d.title || ""; $("#f-doc").value = d.doc_no || ""; $("#f-rows").value = d.N;
  $("#f-project").value = d.project || "";
  $("#f-form").value = d.form || ""; $("#f-pname").value = d.project_name || ""; $("#f-rev").value = d.rev || "";
  $("#f-typical").checked = !!d.typical;
  $("#f-notes").value = (d.notes || []).join("\n");
  for (const id of ["verify", "analyse", "del", "simtoggle"]) $(id === "del" ? "#del" : "#" + id).disabled = false;
  $("#pdf").hidden = false; $("#dxf").hidden = false;
  $("#pdf").href = `/logic/api/drawings/${S.id}/export.pdf`; $("#dxf").href = `/logic/api/drawings/${S.id}/export.dxf`;
}
async function openDoc(id) {
  if (S.dirty && !confirm("저장하지 않은 변경이 있습니다.  버리고 열까요?")) return;
  try { S.doc = await api(`/logic/api/drawings/${id}`); } catch (e) { toast(e.message); return; }
  S.id = id; S.dirty = false; S.sel = new Set(); S.selWire = null; S.undo = []; S.redo = []; S.verify = null; $("#verify-card").hidden = true;
  $("#pick").value = id; $("#save").disabled = true;
  fillForm(); await loadSet(); render(); fitZoom(); render();
  if (S.gotoRow) { const n = S.gotoRow; S.gotoRow = null; flashRow(n); }
  if (simOn()) runSim(true);                                      // L57 — 묶음 안에서 장을 옮겨도 준 신호는 남아 그 장의 값이 선다
  status(`${S.doc.name} · 블록 ${S.doc.blocks.length} · 선 ${S.doc.wires.length} · 저장 ${S.doc.saves || 0}번`);
  location.hash = "d=" + id + (S.mparent ? `&mparent=${S.mparent.did}:${S.mparent.bid}` : "");
  if (S.mparent && !simOn()) { toggleSim(); askParent(); }        // L59 — 새 창은 바로 시뮬레이션으로 열고 부모에게 값을 묻는다
}
async function loadList(keep) {
  const r = await api("/logic/api/drawings");
  const sel = $("#pick"); sel.innerHTML = `<option value="">(그림을 고르세요)</option>` + r.items.map(i => `<option value="${i.id}">${i.set_name ? "[" + esc(i.set_name) + "] " : ""}${esc(i.name)}${i.sheet_no ? " · " + esc(i.sheet_no) : ""}${i.typical ? " (Typical)" : ""} — 블록 ${i.blocks} · 선 ${i.wires}</option>`).join("");
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

/* ───────── 묶음 (L56) ───────── */
async function loadSet() {
  // L57 — 시뮬레이션 카드가 묶음의 장 이름을 쓴다 (S.setInfo)
  S.setInfo = null; const card = $("#set-card"); const mc = $("#macro-card");
  if (!S.doc || !S.doc.set) { card.hidden = false; renderSetCard(); renderMacroCard(); return; }
  try { S.setInfo = await api(`/logic/api/drawings/sets/${S.doc.set}`); } catch (e) { S.setInfo = null; }
  card.hidden = false; renderSetCard(); renderMacroCard();
}
function refOf(text) {
  // FM/TO 칸의 참조 → 이 묶음의 장 (서버 links 가 이미 가른 것을 쓴다 · 없으면 간단한 꼴만)
  const m = String(text || "").trim().toUpperCase().match(/^([A-Z0-9_\-.]+?)\s*[-\/:#]\s*0*(\d+)$/);
  if (!m || !S.setInfo) return null;
  const sh = (S.setInfo.sheets || []).find(x => (x.sheet_no || "").toUpperCase() === m[1]);
  return sh ? { did: sh.id, sheet: sh.sheet_no, row: +m[2] } : null;
}
function linkInfo(side, n) {
  const d = S.setInfo && S.setInfo.links && S.setInfo.links.docs[S.id];
  if (!d) return null;
  return side === "left" ? (d.left || {})[n] : (d.right || {})[n];
}
function renderSetCard() {
  const box = $("#set-list"), info = S.setInfo;
  if (!S.doc) { box.innerHTML = `<p class="dw-hint">그림을 열면 그 묶음의 장이 여기 보입니다.</p>`; $("#set-tools").hidden = true; return; }
  $("#set-tools").hidden = false;
  if (!info) { box.innerHTML = `<p class="dw-hint">이 그림은 묶음에 들어 있지 않습니다.  <button id="set-make" type="button">묶음으로 만들기</button></p>`;
    $("#set-make").onclick = async () => { pushUndo(); const sid = crypto.randomUUID().replace(/-/g, "").slice(0, 12); S.doc.set = sid; S.doc.set_name = S.doc.name; await put(`/logic/api/drawings/${S.id}`, { author: author() || "?", doc: docOut(), set: sid, set_name: S.doc.name }); await loadList(S.id); S.doc = await api(`/logic/api/drawings/${S.id}`); await loadSet(); };
    $$("#set-tools button").forEach(b => b.disabled = b.id !== "set-import"); return; }
  $$("#set-tools button").forEach(b => b.disabled = false);
  const bad = {}; for (const f of (info.links && info.links.findings) || []) if (f.code === "FT_MISMATCH") bad[f.did] = (bad[f.did] || 0) + 1;
  box.innerHTML = `<div class="dw-setname">${esc(info.name)} <span class="dw-hint">${info.sheets.length}장</span></div>` +
    `<ul class="dw-sheets">${info.sheets.map(sh => `<li class="${sh.id === S.id ? "on" : ""}" data-id="${sh.id}"><b>${esc(sh.sheet_no || "(이름 없음)")}</b>${sh.typical ? ' <span class="typ">Typical</span>' : ""} <span class="dw-hint">${esc(sh.title || "")}</span>${bad[sh.id] ? ` <span class="bad">✕${bad[sh.id]}</span>` : ""}</li>`).join("")}</ul>`;
  $$("#set-list li[data-id]").forEach(li => li.onclick = () => { if (li.dataset.id !== S.id) openDoc(li.dataset.id); });
}
function renderMacroCard() {
  const box = $("#macro-list"), ms = (S.setInfo && S.setInfo.macros) || [];
  if (!ms.length) { box.innerHTML = `<p class="dw-hint">매크로 타입이 없습니다 — 묶음의 장에 <b>Typical 시트</b> 표시를 하거나(시트 카드) 학습 사전의 Typical 이 쓰입니다.</p>`; return; }
  box.innerHTML = ms.map((m, i) => `<button type="button" data-i="${i}" title="${esc(m.from)} · 입력 ${m.pins_in.length} · 출력 ${m.pins_out.length}">▣ ${esc(m.title)}<span class="dw-hint">${esc(m.typ)} · ${m.pins_in.length}→${m.pins_out.length}</span></button>`).join("");
  $$("#macro-list button").forEach(b => b.onclick = () => addMacro(ms[+b.dataset.i]));
}
async function addMacro(m) {
  if (!S.doc) return;
  let typ = m.typ;
  if (typ.startsWith("lib:") && S.doc.set) {
    // 사전 Typical — 내부 동작이 묶음 안에 있어야 분석기가 잇는다 → 그 Typical 시트를 묶음에 들여온다 (한 번만)
    const have = (S.setInfo.sheets || []).find(x => x.sheet_no && m.sheet && x.sheet_no === m.sheet.sheet_no);
    if (have) typ = have.sheet_no;
    else { try { const d = await post(`/logic/api/drawings/sets/${S.doc.set}/sheet`, { library: typ.slice(4), author: author() || "?" }); typ = d.sheet_no; await loadSet(); toast(`Typical 시트 ${d.sheet_no} 를 묶음에 들여왔습니다.`); } catch (e) { toast(e.message); } }
  }
  const L = layout(), P = L.PITCH, n = Math.max(m.pins_in.length, m.pins_out.length, 1);
  const b = { id: newId("b"), kind: "MACRO", w: S.sym.MACRO.w, h: +(1.6 * P + n * P + 0.4 * P).toFixed(2), text: "", label: "",
    param: { typ, title: m.title, pins_in: m.pins_in.map((q, i) => ({ name: q.name, row: q.row, dy: +(1.6 * P + (i + 0.5) * P).toFixed(2) })),
             pins_out: m.pins_out.map((q, i) => ({ name: q.name, row: q.row, dy: +(1.6 * P + (i + 0.5) * P).toFixed(2) })) } };
  b.x = Math.round(((L.LX0 + L.LX1) / 2 - b.w / 2) / (P / 2)) * (P / 2); b.y = ry(4) - 1.6 * P - P / 2;
  pushUndo(); S.doc.blocks.push(b); S.sel = new Set([b.id]); S.selWire = null; markDirty(); render();
}
function flashRow(n) {
  const L = layout(); const y = ry(n);
  const sc = $("#scroll"); sc.scrollTop = Math.max(0, y * S.zoom - sc.clientHeight / 2 + 12);
  const ov = overlay(); if (!ov) return;
  const side = n <= L.N ? "L" : "R";
  const e = el("rect", { x: side === "L" ? L.LCOLS[0] : L.RCOLS[0], y: y - L.PITCH / 2, width: side === "L" ? L.LX0 - L.LCOLS[0] : L.RCOLS[4] - L.RCOLS[0], height: L.PITCH, class: "rowflash" }, ov);
  setTimeout(() => e.remove(), 2600);
}
function goRef(ref) {
  if (!ref) return;
  if (ref.did === S.id) { flashRow(ref.row); return; }
  S.gotoRow = ref.row; openDoc(ref.did);
}
async function importBundle() {
  let jobs = [];
  try { jobs = await api("/logic/api/jobs"); } catch (e) { toast(e.message); return; }
  jobs = (Array.isArray(jobs) ? jobs : jobs.items || jobs.jobs || []).filter(j => (j.state || j.status || "done") === "done");
  if (!jobs.length) { toast("분석을 끝낸 Logic 묶음이 없습니다."); return; }
  const v = await modal("분석한 묶음을 통째로 들여오기", `<div class="dw-form">
    <label>묶음 <select id="m-job">${jobs.map(j => `<option value="${j.id}">${esc(j.name || j.id)}${j.project ? " · " + esc(j.project) : ""} · ${j.total || j.sheets || ""}장</option>`).join("")}</select></label>
    <label>그림 묶음 이름 <input id="m-name" placeholder="비우면 묶음 이름"></label>
    <label>작성자 <input id="m-who" value="${esc(author())}"></label></div>
    <p class="dw-hint">모든 Logic 시트가 이 양식의 그림이 되고, 매크로가 이어진 시트는 Typical 로 표시됩니다.  FROM/TO 는 그대로 옮겨집니다.</p>`,
    () => { const w = $("#m-who").value.trim(); if (!w) { toast("작성자 이름이 필요합니다."); return false; } return { job: $("#m-job").value, name: $("#m-name").value.trim(), who: w }; });
  if (!v) return;
  status("묶음을 들여오는 중 …");
  try {
    try { localStorage.setItem("pid.author", v.who); $("#who").value = v.who; } catch (e) {}
    const r = await post("/logic/api/drawings/sets/import", { job: v.job, name: v.name, author: v.who, project: $("#f-project").value });
    toast(`${r.sheets}장을 들여왔습니다 (Typical ${r.typicals}장).`, 5000);
    const items = await loadList();
    const first = items.filter(i => i.set === r.id).sort((a, b) => (a.order || 0) - (b.order || 0))[0];
    if (first) await openDoc(first.id);
  } catch (e) { toast(e.message); status(""); }
}
async function addSheet() {
  if (!S.doc || !S.doc.set) return;
  const v = await modal("묶음에 장 더하기", `<div class="dw-form"><label>시트 이름 <input id="m-sheet" placeholder="예: G035"></label><label>그림 이름 <input id="m-name"></label>
    <label>Typical 시트 <input type="checkbox" id="m-typ"></label><label>작성자 <input id="m-who" value="${esc(author())}"></label></div>`,
    () => { const w = $("#m-who").value.trim(); if (!w) { toast("작성자 이름이 필요합니다."); return false; } return { sheet: $("#m-sheet").value.trim(), name: $("#m-name").value.trim(), typical: $("#m-typ").checked, who: w }; });
  if (!v) return;
  try { const d = await post(`/logic/api/drawings/sets/${S.doc.set}/sheet`, { sheet_no: v.sheet, name: v.name || v.sheet || "새 장", typical: v.typical, author: v.who, N: S.doc.N }); await loadList(d.id); await openDoc(d.id); }
  catch (e) { toast(e.message); }
}
async function verifySet() {
  if (!S.doc || !S.doc.set) return;
  if (S.dirty) { toast("먼저 저장하세요."); return; }
  status("묶음 되읽기 검증 중 — 모든 장을 한 PDF 로 내보내 분석기에 넣습니다 …"); $("#set-verify").disabled = true;
  try {
    const v = await post(`/logic/api/drawings/sets/${S.doc.set}/verify`, {});
    const card = $("#verify-card"), out = $("#verify-out"); card.hidden = false;
    $("#verify-sum").textContent = v.ok ? "묶음 전부 같게 읽혔습니다" : "다르게 읽힌 장이 있습니다"; $("#verify-sum").className = "dw-hint " + (v.ok ? "ok" : "bad");
    if (v.why) out.innerHTML = `<p class="bad">${esc(v.why)}</p>`;
    else out.innerHTML = `<p>장 ${v.read}/${v.drawn} 읽음 · FROM/TO 불일치 ${v.fromto_bad} · ${v.seconds || ""}초</p><ul>` +
      v.sheets.map(sh => { const bl = sh.blocks || []; return `<li data-did="${sh.did}" class="${sh.ok ? "ok" : "bad"}">${sh.ok ? "✔" : "✕"} ${esc(sh.sheet_no && sh.sheet_no.drawn || sh.sheet_no || "")}${sh.why ? " — " + esc(sh.why) : ` · 블록 ${bl.filter(b => b.ok).length}/${bl.length} · 행 ${sh.rows ? sh.rows.read + "/" + sh.rows.drawn : ""} · 매달림 ${sh.dangling ?? ""}${bl.filter(b => b.kind === "MACRO").map(b => b.macro ? ` · 매크로→${esc(b.macro.sheet || "없음")}` : "").join("")}`}</li>`; }).join("") +
      (v.fromto || []).map(f => `<li class="${f.code === "FT_MISMATCH" ? "bad" : "warn"}" data-did="${f.did}">${f.code === "FT_MISMATCH" ? "✕" : "△"} ${esc(f.text)}</li>`).join("") + `</ul>`;
    $$("#verify-out li[data-did]").forEach(li => li.onclick = () => { if (li.dataset.did !== S.id) openDoc(li.dataset.did); });
    status(v.ok ? "묶음 검증 — 같게 읽힙니다" : "묶음 검증 — 다른 장이 있습니다");
  } catch (e) { toast("검증 실패 — " + e.message); status(""); }
  $("#set-verify").disabled = false;
}
async function sendSetToAnalyse() {
  if (!S.doc || !S.doc.set) return;
  if (S.dirty) { toast("먼저 저장하세요."); return; }
  if (!confirm("묶음 전체를 PDF 로 내보내 LOGIC 검토 묶음으로 올립니다.  계속할까요?")) return;
  try { const r = await post(`/logic/api/drawings/sets/${S.doc.set}/analyse`, { author: author() }); toast("검토 묶음으로 올렸습니다."); setTimeout(() => { location.href = `/logic#job=${r.id}`; }, 900); }
  catch (e) { toast(e.message); }
}

/* ───────── 시작 ───────── */
/* ───────── L57 — 실시간 시뮬레이션 (그린 그대로 · PDF 를 거치지 않는다 · 판정은 서버 sim 이 한다) ───────── */
const GATE_LOGIC = new Set(["and", "or", "nand", "nor", "not", "vote", "memory", "delay_on", "delay_off", "pulse", "step", "macro", "pass"]);
function simOn() { return !!(S.sim && S.sim.on); }
function simF() { const s = S.sim; return s.forces[S.id] || (s.forces[S.id] = {}); }
function toggleSim() {
  if (!S.doc) return;
  if (simOn()) { S.sim.on = false; simStop(); document.body.classList.remove("sim"); $("#sim-card").hidden = true; simMenuClose(); render(); status("시뮬레이션을 끝냈습니다 — 준 신호는 다시 켤 때까지 남습니다"); return; }
  S.sim = S.sim || { forces: {}, states: {}, timers: {}, analog: {}, res: null, values: {}, sig: null, pins: true };
  S.sim.on = true; document.body.classList.add("sim"); $("#sim-card").hidden = false;
  setTool("select");
  status("시뮬레이션 — 왼쪽 행 자리 · 누름단추 · 선을 눌러 1/0 을 주세요.  고치면 바로 다시 돕니다.");
  runSim(true);
}
function simSoon() { if (!simOn()) return; clearTimeout(S.sim._t); S.sim._t = setTimeout(() => runSim(false), 160); }
async function runSim(animate) {
  if (!simOn() || !S.doc) return;
  const s = S.sim, did = S.id, seq = (s.seq = (s.seq || 0) + 1);
  const body = { doc: docOut(), forces: s.forces, state: s.states, timers: s.timers, analog: s.analog, inner: macroWinKeys() };
  let r;
  try { r = await post(`/logic/api/drawings/${did}/simulate`, body); } catch (e) { status("시뮬레이션 실패 — " + e.message); return; }
  if (!simOn() || seq !== s.seq || did !== S.id) return;         // 기다리는 동안 다른 그림으로 옮겼거나 또 눌렀다
  if (r.error) { status(r.error); s.res = null; renderSimCard(); return; }
  if (s.sig && r.sig !== s.sig) { s.states = {}; }               // 그림의 구조가 바뀌었다 — 묵은 상태(타이머 · 래치)는 버린다
  s.sig = r.sig; s.res = r; s.states = r.state || {};
  const fr = (r.focus && r.focus.frames) || [];
  s.frames = fr; s.values = fr.length ? fr[fr.length - 1].values : {};
  simStop();
  if (S.mparent && S.mparent.inner) { applyParentInner(S.mparent.inner, S.mparent.forces, false); return; }   // L59 — 새 창: 값은 부모 장이 정한다
  if (animate && fr.length > 1) simPlay(fr); else simPaint(s.values, fr.length ? fr[fr.length - 1] : null);
  renderSimCard();
  sendMacroInner(r);
}
/* ───────── L59 — 매크로 내부 동작을 새 창으로 (검토 화면 L44/L45 와 같은 방법) ─────────
   새 창은 그 Typical 그림을 열고 **따로 돌리지 않는다** — 부모 장에 펼쳐 같이 돈 값(틀마다)을 부모가 보내 주면 그대로 그린다.
   새 창에서 행 · 선 · 블록을 누르면 부모 장의 펼친 이름(<상자>/<선>)으로 부모에게 주고, 부모가 묶음을 다시 돌려 되보낸다. */
function macroWinKeys() {
  const w = (S.sim && S.sim.wins) || {}; const out = [];
  for (const [k, c] of Object.entries(w)) { if (!c.win || c.win.closed) { delete w[k]; continue; } out.push(k); }
  return out;
}
function openMacroWin(bid, typDid) {
  if (!S.id) return;
  const key = `${S.id}:${bid}`;
  const url = `/logic/draw#d=${typDid}&mparent=${key}`;
  const w = window.open(url, `dmacro-${key}`, "width=1500,height=950");
  if (!w) { status("새 창을 열지 못했습니다 — 브라우저의 팝업 차단을 풀어 주세요"); return; }
  S.sim.wins = S.sim.wins || {}; S.sim.wins[key] = { win: w, bid, did: S.id };
  status(`매크로 ${bid} 의 내부 동작을 새 창에서 — 부모 장의 값으로 돕니다`);
}
function sendMacroInner(r) {
  const wins = (S.sim && S.sim.wins) || {}, mi = (r && r.macro_inner) || {};
  for (const [key, c] of Object.entries(wins)) {
    if (!c.win || c.win.closed) { delete wins[key]; continue; }
    const inner = mi[key]; if (!inner) continue;
    const F = (S.sim.forces[c.did] || {}), forces = {};
    const back = {}; for (const [tn, nm] of Object.entries(inner.alias || {})) back[nm] = tn;
    for (const [k, v] of Object.entries(F)) {
      const i = k.indexOf(":"), kind = k.slice(0, i), id = k.slice(i + 1);
      if (id.startsWith(c.bid + "/")) forces[`${kind}:${id.slice(c.bid.length + 1)}`] = v;
      else if (kind === "net" && back[id] !== undefined) forces["net:" + back[id]] = v;
    }
    try { c.win.postMessage({ type: "dmacro-inputs", key, inner, forces }, location.origin); } catch (e) {}
  }
}
function macroParentKey(key) {
  // 새 창의 강제 열쇠 → 부모 장에 펼친 이름 (단자 선은 부모 선 이름 그대로)
  const bid = S.mparent.bid, al = (S.mparent.inner && S.mparent.inner.alias) || {};
  const netKey = n => "net:" + (al[String(n)] || `${bid}/${n}`);
  const i = key.indexOf(":"), kind = key.slice(0, i), id = key.slice(i + 1);
  if (kind === "net") return netKey(id);
  if (kind === "block") return `block:${bid}/${id}`;
  if (kind === "row") { const sh = S.sim.res && S.sim.res.sheet; const r = sh && sh.rows.find(x => x.n === +id && x.net != null); return r ? netKey(r.net) : null; }
  return null;
}
function applyParentInner(inner, forces, animate) {
  const s = S.sim; if (!s || !s.on || !s.res || !s.res.sheet) return;
  const sh = s.res.sheet, all = new Set(Object.keys(sh.nets || {}));
  for (const p of sh.ports) all.add(String(p.net));
  for (const r of sh.rows) if (r.net != null) all.add(String(r.net));
  const frames = (inner.frames || []).map(fr => { const v = {}; for (const n of all) v[n] = 0; Object.assign(v, fr.values || {}); return { ...fr, values: v, depth: fr.depth || {} }; });
  if (!frames.length) return;
  s.forces[S.id] = { ...(forces || {}) };
  if (s.res.focus) s.res.focus.unmet = [];
  s.frames = frames; s.values = frames[frames.length - 1].values;
  simStop();
  if (animate && frames.length > 1) simPlay(frames); else simPaint(s.values, frames[frames.length - 1]);
  renderSimCard();
}
window.addEventListener("message", e => {
  if (e.origin !== location.origin || !e.data) return;
  const d = e.data;
  if (d.type === "dmacro-ask") {                                   // 새 창 → 부모: 값을 달라
    if (!S.sim || !S.sim.on || !S.id) return;
    S.sim.wins = S.sim.wins || {}; S.sim.wins[d.key] = { win: e.source, bid: d.key.split(":")[1], did: d.key.split(":")[0] };
    runSim(false); return;
  }
  if (d.type === "dmacro-set") {                                   // 새 창 → 부모: 매크로 안의 이 선/블록을 이 값으로
    if (!S.sim || !S.sim.on) return;
    const F = S.sim.forces[d.did] || (S.sim.forces[d.did] = {});
    if (d.value == null) delete F[d.key]; else F[d.key] = d.value;
    status(`매크로 새 창에서 ${d.key} 을 ${d.value == null ? "풀기" : d.value}`);
    runSim(true); return;
  }
  if (d.type === "dmacro-inputs" && S.mparent && d.key === `${S.mparent.did}:${S.mparent.bid}`) {   // 부모 → 새 창
    const changed = JSON.stringify((d.inner.frames || []).slice(-1)) !== JSON.stringify(((S.mparent.inner || {}).frames || []).slice(-1));
    S.mparent.inner = d.inner; S.mparent.forces = d.forces || {};
    if (S.sim && S.sim.on && S.sim.res) applyParentInner(d.inner, d.forces, changed);
  }
});
function askParent() {
  if (!S.mparent || !window.opener || window.opener.closed) return false;
  try { window.opener.postMessage({ type: "dmacro-ask", key: `${S.mparent.did}:${S.mparent.bid}` }, location.origin); return true; } catch (e) { return false; }
}
function simStop() { if (S.sim && S.sim._anim) { clearTimeout(S.sim._anim); S.sim._anim = null; } }
function simPlay(frames) {
  // 틀 사이를 실제 시간만큼(상한 6초) 기다리며 그린다 — 타이머의 카운트다운이 보인다
  let i = 0;
  const step = () => {
    if (!simOn()) return;
    const f = frames[i]; simPaint(f.values, f);
    i++; if (i >= frames.length) { S.sim._anim = null; return; }
    const wait = Math.min(6, Math.max(0.25, frames[i].t - f.t));
    S.sim._anim = setTimeout(step, wait * 1000);
  };
  step();
}
function simPaint(values, frame) {
  if (!simOn() || !S.sim.res || !S.sim.res.sheet) return;
  const sh = S.sim.res.sheet, F = simF(), svg = $("#svg");
  let ov = svg.querySelector("#simov"); if (ov) ov.remove();
  ov = el("g", { id: "simov" }, svg);
  const unread = new Set((frame && frame.unread) || []);
  // 선
  for (const [k, n] of Object.entries(sh.nets)) {
    const v = values[k], forced = F["net:" + k] != null;
    for (const wid of n.wires) for (const e of svg.querySelectorAll(`.wire[data-id="${wid}"]`)) { e.classList.toggle("on", v === 1); e.classList.toggle("forced", forced); e.classList.toggle("unk", unread.has(k) && v !== 1); }
  }
  // 행 자리
  const linked = (S.sim.res.linked || {})[S.id] || {};
  for (const r of sh.rows) {
    const e = svg.querySelector(`.rowstub[data-n="${r.n}"]`); if (!e) continue;
    const v = r.net != null ? values[r.net] : (F["row:" + r.n] != null ? F["row:" + r.n] : 0);
    e.classList.toggle("v1", v === 1); e.classList.toggle("forced", F["row:" + r.n] != null); e.classList.toggle("linked", linked[r.n] != null && F["row:" + r.n] == null);
    const tt = e.querySelector("title") || el("title", {}, e);
    tt.textContent = `${r.side === "L" ? "입력" : "출력"} ${r.n}행 = ${v == null ? "?" : v}` + (F["row:" + r.n] != null ? " (내가 줌)" : linked[r.n] != null ? " (다른 장에서)" : "") + " — 누르면 1/0";
  }
  // 블록 — 출력 선이 1 이면 활성 · 신호원은 누를 수 있다 · 단자 1/0
  const outs = {}, ins = {};
  for (const p of sh.ports) (p.dir === "out" ? outs : ins)[p.block] = (p.dir === "out" ? outs : ins)[p.block] || [], (p.dir === "out" ? outs : ins)[p.block].push(p);
  const unmet = new Set(((S.sim.res.focus || {}).unmet || []).map(u => u.block).filter(Boolean));
  const showPins = $("#sim-pins").checked;
  for (const b of S.doc.blocks) {
    const g = svg.querySelector(`.blk[data-id="${b.id}"]`); if (!g) continue;
    const sb = sh.blocks[b.id] || {};
    const on = (outs[b.id] || []).some(p => values[p.net] === 1);
    g.classList.toggle("act", on); g.classList.toggle("src", sb.logic === "source"); g.classList.toggle("unmet", unmet.has(b.id));
    g.classList.toggle("on1", sb.logic === "source" && F["block:" + b.id] === 1);
    if (showPins && (GATE_LOGIC.has(sb.logic) || sb.aop)) {
      for (const p of [...(ins[b.id] || []), ...(outs[b.id] || [])]) {
        const d = p.side === "L" ? [-3.2, 0] : p.side === "R" ? [3.2, 0] : p.side === "T" ? [0, -3.2] : [0, 3.2];
        const v = values[p.net], x = p.at[0] + d[0], y = p.at[1] + d[1];
        el("rect", { x: x - 2.1, y: y - 1.9, width: 4.2, height: 3.8, class: "simbox" + (v === 1 ? " v1" : "") }, ov);
        txt(ov, x, y, v == null ? "?" : String(v), 3.4, "middle").setAttribute("class", "simval" + (v === 1 ? " v1" : ""));
      }
    }
    if (S.sym[b.kind].time || sb.logic === "delay_on" || sb.logic === "delay_off" || sb.logic === "pulse") {
      const run = ((frame && frame.running) || []).find(x => x.block === b.id);
      if (run) txt(ov, b.x + b.w / 2, b.y - 2, `⏱ ${Math.max(0, run.left).toFixed(1)}s`, 4.2, "middle").setAttribute("class", "simtimer");
    }
  }
  // 아날로그 값 (MED · 감시 블록 설정값과 비교한 결과)
  const an = (S.sim.res.focus || {}).analog || {};
  for (const [k, info] of Object.entries(an.keys || {})) {
    if (!k.startsWith("block:") || info.eng == null) continue;
    const b = S.doc.blocks.find(x => x.id === k.slice(6)); if (!b) continue;
    txt(ov, b.x + b.w / 2, b.y + b.h + 4.5, `= ${(+info.eng).toFixed(2)}${info.range && info.range.unit ? " " + info.range.unit : ""}`, 4, "middle").setAttribute("class", "simtimer");
  }
  if (frame && frame.t != null) { const e = txt(ov, layout().LX1 - 4, layout().TOP - 2 * layout().PITCH - 3, `t = ${(+frame.t).toFixed(1)} s`, 5, "end"); e.setAttribute("class", "simtimer"); }
}
function flashNeed(nets) {
  const svg = $("#svg"), sh = S.sim && S.sim.res && S.sim.res.sheet; if (!sh) return;
  const ov = svg.querySelector("#simov") || el("g", { id: "simov" }, svg);
  for (const k of nets) for (const wid of (sh.nets[k] || { wires: [] }).wires) { const w = S.doc.wires.find(w => w.id === wid); if (w) el("polyline", { points: w.pts.map(p => p.join(",")).join(" "), class: "simneed" }, ov); }
  setTimeout(() => { for (const e of svg.querySelectorAll(".simneed")) e.remove(); }, 1800);
}
/* 누르기 — 행 자리 · 신호원 블록 · 게이트 · 선 */
function simClick(e, p, t) {
  const sh = S.sim.res && S.sim.res.sheet;
  const F = simF();
  if (t.classList.contains("rowstub")) {
    const n = +t.dataset.n, L = layout(), side = n <= L.N ? "L" : "R";
    const r = sh && sh.rows.find(r => r.n === n);
    const cur = F["row:" + n];
    const items = [];
    if (side === "L") {
      items.push({ t: "1 활성", v: 1, cls: "v1" }, { t: "0 비활성", v: 0, cls: "v0" });
      items.push({ t: "∿ 아날로그 값 (mA)", ana: "row:" + n });
    } else items.push({ t: "1 — 이 출력이 나가게 (조건을 채운다)", v: 1, cls: "v1" }, { t: "0 — 이 출력이 나가지 않게", v: 0, cls: "v0" });
    if (cur != null || (S.sim.analog[S.id] || {})["row:" + n] != null) items.push({ t: "강제 풀기", v: null });
    simMenu(e, `${side === "L" ? "입력" : "출력"} ${n}행 ${r && r.net != null ? "" : "(선이 안 닿았습니다)"}`, items, key => "row:" + n, cur);
    return true;
  }
  const blk = t.closest(".blk");
  if (blk) {
    const b = S.doc.blocks.find(b => b.id === blk.dataset.id); const sb = sh && sh.blocks[b.id];
    if (!sb) return false;
    if (sb.logic === "source") {
      const cur = F["block:" + b.id];
      simMenu(e, `${sb.func} ${b.label || b.text || ""}`, [{ t: "1 누름 · 활성", v: 1, cls: "v1" }, { t: "0 비활성", v: 0, cls: "v0" }, ...(cur != null ? [{ t: "강제 풀기", v: null }] : [])], () => "block:" + b.id, cur);
      return true;
    }
    if (GATE_LOGIC.has(sb.logic) || sb.aop) {
      const cur = F["block:" + b.id];
      const items = [{ t: "출력 1 — 조건을 채워 켠다 (게이트가 판정)", v: 1, cls: "v1" }, { t: "출력 0 — 조건을 깨서 끈다", v: 0, cls: "v0" }];
      if (cur != null) items.push({ t: "목표 풀기", v: null });
      if (sb.aop || ["unknown"].includes(sb.logic)) items.push({ t: "∿ 출력값 넣기 (공학값)", ana: "block:" + b.id });
      if (S.sym[b.kind].time) items.push({ t: `⏱ 시간 ${(b.param || {}).t || 5}초 — 속성에서 바꿉니다`, info: true });
      if (sb.macro && !sb.macro.page) items.push({ t: "⚠ " + (sb.macro.why || "Typical 시트가 없습니다"), info: true });
      if (sb.macro && sb.macro.did) items.push({ t: `↗ 내부 동작 보기 (새 창) — ${sb.macro.sheet || ""}`, act: () => openMacroWin(b.id, sb.macro.did) });   // L59
      simMenu(e, `${sb.func}${sb.aop ? " · " + sb.aop : ""} ${b.text || ""}`, items, () => "block:" + b.id, cur);
      return true;
    }
    return false;                                                    // 램프 · 경보 · 글 — 평소처럼 고른다
  }
  if (t.classList.contains("wire") || t.classList.contains("wirehit")) {
    // 선이 행 자리에서 시작하면 그 자리를 누른 것은 선이 아니라 행이다 (선이 행 자리 위에 그려진다)
    const L = layout(), rn = rowAt(p[1]);
    if (rn && Math.abs(p[1] - ry(rn)) <= 3) {
      for (const [x, n] of [[L.LX0, rn], [L.LX1, rn + L.N]]) if (Math.abs(p[0] - x) <= 3.5) { const st = $(`#svg .rowstub[data-n="${n}"]`); if (st) return simClick(e, p, st); }
    }
    const wid = t.dataset.id; const k = sh && Object.keys(sh.nets).find(k => sh.nets[k].wires.includes(wid));
    if (k == null) return false;
    const cur = F["net:" + k];
    simMenu(e, `선 (그물 ${k}) = ${S.sim.values[k] == null ? "?" : S.sim.values[k]}`, [{ t: "1 활성", v: 1, cls: "v1" }, { t: "0 비활성", v: 0, cls: "v0" }, ...(cur != null ? [{ t: "강제 풀기", v: null }] : [])], () => "net:" + k, cur);
    return true;
  }
  return false;
}
function simMenu(e, title, items, keyOf, cur) {
  const m = $("#simmenu"); m.innerHTML = `<h4>${esc(title)}</h4>`;
  for (const it of items) {
    if (it.ana) {
      const key = it.ana, a = (S.sim.analog[S.id] || {})[key];
      const row = document.createElement("div"); row.className = "ana";
      row.innerHTML = `<span>${esc(it.t)}</span><input type="number" step="0.1" min="${key.startsWith("row:") ? 4 : -1e9}" max="${key.startsWith("row:") ? 20 : 1e9}" value="${a != null ? a : (key.startsWith("row:") ? 8 : "")}"><button type="button">넣기</button>`;
      row.querySelector("button").onclick = () => { const v = parseFloat(row.querySelector("input").value); if (!isFinite(v)) return; setAnalog(S.id, key, v); simMenuClose(); };
      row.querySelector("input").onkeydown = ev => { if (ev.key === "Enter") row.querySelector("button").click(); };
      m.appendChild(row); continue;
    }
    const b = document.createElement("button"); b.type = "button"; b.textContent = it.t; b.className = (it.cls || "") + (it.v !== undefined && it.v === cur ? " cur" : "");
    if (it.info) { b.disabled = true; b.style.opacity = ".7"; }
    else if (it.act) b.onclick = () => { simMenuClose(); it.act(); };
    else b.onclick = () => { setForce(S.id, keyOf(), it.v); simMenuClose(); };
    m.appendChild(b);
  }
  m.hidden = false;
  const x = Math.min(e.clientX + 6, window.innerWidth - m.offsetWidth - 8), y = Math.min(e.clientY + 6, window.innerHeight - m.offsetHeight - 8);
  m.style.left = x + "px"; m.style.top = y + "px";
}
function simMenuClose() { const m = $("#simmenu"); if (m) m.hidden = true; }
function setForce(did, key, v) {
  if (S.mparent && did === S.id) {                                 // L59 — 새 창: 부모 장에 펼친 이름으로 준다
    const pk = macroParentKey(key);
    if (!pk) { status("이 항목은 부모 시트에서 주세요"); return; }
    if (!window.opener || window.opener.closed) { status("부모 창이 닫혔습니다 — 이 창은 Typical 만 따로 돕니다"); S.mparent = null; }
    else { window.opener.postMessage({ type: "dmacro-set", did: S.mparent.did, key: pk, value: v }, location.origin); status(`${v == null ? "풀기" : v + " 로 줌"} — 부모 시트의 매크로 안에서 계산합니다`); return; }
  }
  const F = S.sim.forces[did] || (S.sim.forces[did] = {});
  if (v == null) delete F[key]; else { F[key] = v; const A = S.sim.analog[did]; if (A) delete A[key]; }
  runSim(true);
}
function setAnalog(did, key, ma) {
  const A = S.sim.analog[did] || (S.sim.analog[did] = {});
  A[key] = ma; const F = S.sim.forces[did]; if (F) delete F[key];
  runSim(true);
}
function simReset() { if (!S.sim) return; S.sim.forces = {}; S.sim.states = {}; S.sim.analog = {}; runSim(true); }
function renderSimCard() {
  const out = $("#sim-out"), s = S.sim; if (!s || !s.on) return;
  const r = s.res; if (!r) { out.innerHTML = `<div class="grp bad">결과가 없습니다</div>`; return; }
  const sh = r.sheet, f = r.focus || {}, name = d => { const it = (S.setInfo && S.setInfo.sheets || []).find(x => x.id === d); return it ? (it.sheet_no || it.title || d.slice(0, 6)) : (d === S.id ? (S.doc.sheet_no || "이 장") : d.slice(0, 6)); };
  const rowDesc = (did, key) => {
    if (did !== S.id) return "";
    const m = key.match(/^row:(\d+)$/); if (m) { const n = +m[1]; const L = layout(); const c = n <= L.N ? S.doc.left[String(n)] : S.doc.right[String(n)]; return c && c.desc ? " " + c.desc : ""; }
    const b = key.startsWith("block:") && S.doc.blocks.find(b => b.id === key.slice(6)); return b ? " " + (b.label || b.text || b.kind) : "";
  };
  let h = "";
  if (S.mparent) {                                                  // L59 — 새 창: 부모 장의 매크로 값으로 돈다
    const ln = S.mparent.inner, links = (ln && ln.links) || [];
    h += `<div class="grp" style="background:#eef4ff"><b>↗ 부모 시트 ${esc((ln && ln.sheet_no) || S.mparent.did.slice(0, 6))} 의 매크로 ${esc(S.mparent.bid)} 값으로 돕니다</b>` +
      (ln ? links.filter(x => x.side === "L").map(x => `<div class="row">${x.row}행 ${esc(x.pin || "")} ← ${esc((x.rows || []).map(r => `${r.n}행 ${r.desc || ""}`).join(", ") || x.src || "단자")}</div>`).join("") : `<div class="dw-hint">부모 창의 값을 기다리는 중…</div>`) + `</div>`;
  }
  const given = [];
  for (const [did, F] of Object.entries(s.forces)) for (const [k, v] of Object.entries(F)) given.push({ did, k, v });
  for (const [did, A] of Object.entries(s.analog)) for (const [k, v] of Object.entries(A)) given.push({ did, k, v, ana: true });
  h += `<div class="grp"><b>내가 준 신호 ${given.length}</b>` + (given.length ? given.map(g => `<div class="row" data-did="${g.did}"><span>${esc(name(g.did))} · ${esc(g.k.replace("row:", "행 ").replace("block:", "블록 ").replace("net:", "선 "))}${esc(rowDesc(g.did, g.k))}</span><span><span class="v ${g.ana ? "ana" : "v" + g.v}">${g.ana ? g.v + " mA" : g.v}</span> <button type="button" data-off="${g.did}|${g.k}|${g.ana ? "a" : "f"}">끄기</button></span></div>`).join("") : `<div class="dw-hint">행 자리 · 누름단추 · 선을 눌러 주세요</div>`) + `</div>`;
  const outs = (sh.rows || []).filter(r => r.side === "R").map(r => ({ ...r, v: r.net != null ? s.values[r.net] : null }));
  const on = outs.filter(r => r.v === 1), off = outs.filter(r => r.v !== 1 && r.net != null);
  const rdesc = n => { const c = S.doc.right[String(n)]; return c && c.desc ? c.desc : ""; }, rto = n => { const c = S.doc.right[String(n)]; return c && c.to ? " → " + c.to : ""; };
  h += `<div class="grp"><b>나간 출력 ${on.length} / ${outs.filter(r => r.net != null).length}</b>` + on.map(r => `<div class="row" data-row="${r.n}"><span>${r.n}행 ${esc(rdesc(r.n))}${esc(rto(r.n))}</span><span class="v v1">1</span></div>`).join("") + `</div>`;
  const unmet = f.unmet || [];
  if (unmet.length) h += `<div class="grp warn"><b>목표를 못 채운 출력 ${unmet.length}</b>` + unmet.map(u => `<div class="row">${esc(u.why || u.reason || JSON.stringify(u).slice(0, 80))}</div>`).join("") + `</div>`;
  const macroWhy = Object.entries(sh.blocks || {}).filter(([, b]) => b.macro && !b.macro.page).map(([k, b]) => `${esc(b.label || k)} — ${esc(b.macro.why || "")}`);
  if (macroWhy.length) h += `<div class="grp warn"><b>Typical 을 못 찾은 매크로</b>${macroWhy.map(t => `<div class="row">${t}</div>`).join("")}</div>`;
  const chain = (r.pages || []).filter(p => p.did !== S.id && ((p.outputs || []).length || (p.inputs || []).length));
  if (chain.length) h += `<div class="grp"><b>다른 장으로 넘어간 신호</b>` + chain.map(p => `<div class="row" data-open="${p.did}"><span>${esc(name(p.did))}</span><span>${(p.inputs || []).length ? "입력 " + (p.inputs || []).length : ""} ${(p.outputs || []).length ? "출력 " + (p.outputs || []).length : ""} ↗</span></div>`).join("") + `</div>`;
  const de = r.design_errors || [];
  if (de.length) h += `<div class="grp bad"><b>설계 오류 ${de.length}</b>` + de.slice(0, 6).map(x => `<div class="row">${esc(x.why || x.reason || "")}</div>`).join("") + `</div>`;
  const notes = [...(f.notes || []), ...(r.notes || [])];
  if (notes.length) h += `<div class="grp"><b>메모</b>${notes.slice(0, 6).map(t => `<div class="row">${esc(t)}</div>`).join("")}</div>`;
  out.innerHTML = h;
  $("#sim-sum").textContent = `t=${s.frames && s.frames.length ? (+s.frames[s.frames.length - 1].t).toFixed(1) : 0}s · 선 ${Object.keys(sh.nets || {}).length} · 1 인 선 ${Object.values(s.values).filter(v => v === 1).length}`;
  for (const b of out.querySelectorAll("button[data-off]")) b.onclick = ev => { ev.stopPropagation(); const [did, k, kind] = b.dataset.off.split("|"); if (kind === "a") { const A = S.sim.analog[did]; if (A) delete A[k]; } else { const F = S.sim.forces[did]; if (F) delete F[k]; } runSim(true); };
  for (const r of out.querySelectorAll(".row[data-row]")) r.onclick = () => flashRow(+r.dataset.row);
  for (const r of out.querySelectorAll(".row[data-open]")) r.onclick = () => openDoc(r.dataset.open);
}

async function init() {
  const r = await api("/logic/api/drawings/symbols");
  S.sym = r.symbols; S.lay = r.layout; S.presets = r.presets || [];
  const w = author(); if (w) $("#who").value = w;
  $("#who").onchange = () => { try { localStorage.setItem("pid.author", $("#who").value.trim()); } catch (e) {} };
  buildPalette(); bindStage();
  $$(".dw-tools button").forEach(b => b.onclick = () => setTool(b.dataset.tool));
  $("#zin").onclick = () => setZoom(S.zoom * 1.2); $("#zout").onclick = () => setZoom(S.zoom / 1.2); $("#zfit").onclick = () => fitZoom();
  $("#snap").onchange = e => { S.snap = e.target.checked; };
  loadGuide();
  for (const k of ["grid", "ruler", "align", "cross"]) $("#g-" + k).onchange = e => { S.guide[k] = e.target.checked; saveGuide(); render(); };
  $("#new").onclick = newDoc; $("#import").onclick = importSheet; $("#save").onclick = save; $("#verify").onclick = verify;
  $("#set-import").onclick = importBundle; $("#set-add").onclick = addSheet; $("#set-verify").onclick = verifySet; $("#set-analyse").onclick = sendSetToAnalyse;
  $("#set-pdf").onclick = () => { if (S.doc && S.doc.set) location.href = `/logic/api/drawings/sets/${S.doc.set}/export.pdf`; };
  $("#f-typical").onchange = () => { if (!S.doc) return; S.doc.typical = $("#f-typical").checked; markDirty(); };
  $("#analyse").onclick = sendToAnalyse; $("#del").onclick = delDoc;
  $("#simtoggle").onclick = toggleSim; $("#sim-step").onclick = () => runSim(true); $("#sim-reset").onclick = simReset;
  $("#sim-pins").onchange = () => render();
  document.addEventListener("pointerdown", e => { const m = $("#simmenu"); if (!m.hidden && !m.contains(e.target)) simMenuClose(); }, true);
  $("#pick").onchange = e => { if (e.target.value) openDoc(e.target.value); };
  for (const id of ["#name", "#f-sheet", "#f-title", "#f-doc", "#f-project", "#f-pname", "#f-rev"]) $(id).oninput = () => { if (!S.doc) return; S.doc.sheet_no = $("#f-sheet").value.trim(); S.doc.title = $("#f-title").value.trim(); S.doc.doc_no = $("#f-doc").value.trim(); S.doc.project_name = $("#f-pname").value.trim(); S.doc.rev = $("#f-rev").value.trim(); markDirty(); render(); };
  $("#f-form").onchange = () => { if (!S.doc) return; S.doc.form = $("#f-form").value; markDirty(); render(); };
  $("#f-rows").onchange = () => { if (!S.doc) return; const n = Math.max(45, Math.min(62, +$("#f-rows").value || 50)); $("#f-rows").value = n; pushUndo(); S.doc.N = n; markDirty(); render(); };
  window.addEventListener("beforeunload", e => { if (S.dirty) { e.preventDefault(); e.returnValue = ""; } });
  await loadProjects();
  const items = await loadList();
  const m = location.hash.match(/d=([0-9a-f]{12})/), ms = location.hash.match(/set=([0-9a-f]{12})/), mp = location.hash.match(/mparent=([0-9a-f]{12}):([^&]+)/);
  if (mp) { S.mparent = { did: mp[1], bid: decodeURIComponent(mp[2]), inner: null, forces: {} }; document.title = "LOGIC 작도 — 매크로 내부 동작"; }
  if (m && items.some(i => i.id === m[1])) openDoc(m[1]);
  else if (ms) { const first = items.filter(i => i.set === ms[1]).sort((a, b) => (a.order || 0) - (b.order || 0))[0]; if (first) openDoc(first.id); else { render(); await loadSet(); } }
  else { render(); await loadSet(); }
}
init().catch(e => { toast("화면을 열지 못했습니다 — " + e.message, 8000); console.error(e); });
