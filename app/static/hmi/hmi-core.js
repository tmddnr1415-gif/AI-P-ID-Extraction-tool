/* HMI 화면 엔진 + 패널 — 재사용 부품 (hotfix109).  어느 공정 그림이든 **같은 모델 꼴**이면 그린다.
 *
 * 모델 (HMI.Screen.load 가 받는 것 · 좌표는 모델 단위 · 아래로 갈수록 y 가 크다):
 *   { width, height, title?,
 *     pipes:       [{ id, service: 'process'|'discharge'|'cooling'|'drain'|'steam'|'water'|'air'|'fuel'|'chem'|'other',
 *                     points: [[x,y],…], flow: 'fwd'|'rev'|'none', width?, label?, role? }],
 *     signals:     [{ id, points: [[x,y],…] }]                                — 계기 신호선 (파선)
 *     equipment:   [{ id, kind, x, y, w, h, rot?, name, tag?, state?: 'run'|'standby'|'trip'|'stop'|'oos' }],
 *     instruments: [{ id, tag, fn: 'PT'|'TT'|…, x, y, r?, loc?: 0|1|2, value?, unit?, alarm?, vendor?, face?: 'above'|'below'|'left'|'right' }],
 *     valves:      [{ id, tag, kind, x, y, size?, rot?, state?: 'open'|'closed'|'travel'|'' }],
 *     connectors:  [{ id, text, x, y, dir: 'in'|'out', side?: 'left'|'right' }],
 *     labels:      [{ text, x, y, size? }] }
 * 상태 (setStates): { 태그: { v, u, s, open, alarm, state, mode } } — 태그가 열쇠다 (LOGIC 검토와 같은 글자).
 *
 * 화면이 하는 일: 그리기 · 확대/끌기 · 고르기 · **태그 인라인 편집**(dblclick → 입력 칸 → onTagEdit) · 상태 칠하기.
 * 패널: Legend · Library · Trend · KeyParams · ControlMode · Faceplate · StatusChip — 전부 HMI.Symbols 와 같은 CSS 변수를 읽는다. */
(function () {
  "use strict";
  const H = (window.HMI = window.HMI || {});
  const S = H.Symbols;
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  H.esc = esc;
  const SERVICES = (H.SERVICES = {
    process: "Process (Process Fluid)", discharge: "Discharge (High Pressure)", cooling: "Cooling Water / Utility", drain: "Drain / Waste",
    steam: "Steam", water: "Water / Condensate", air: "Air / Gas", fuel: "Fuel", chem: "Chemical", other: "Other",
  });
  const STATES = (H.STATES = { run: "Running / Normal", standby: "Standby", trip: "Trip / Alarm", stop: "Stopped", oos: "Not In Service" });
  const num = (v, d) => (typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? (Math.abs(v) >= 100 ? 0 : Math.abs(v) >= 10 ? 1 : 2) : d) : "");

  /* ---------------- 화면 */
  class Screen {
    constructor(el, opts) {
      this.el = el; this.opts = opts || {}; this.model = null; this.states = {}; this.zoom = 1; this.pan = { x: 0, y: 0 };
      this.sel = null; this.onSelect = this.opts.onSelect || null; this.onTagEdit = this.opts.onTagEdit || null;
      el.classList.add("hmi-stage");
      this._bind();
    }
    load(model) { this.model = model; this.sel = null; this.render(); this.fit(); }
    setStates(states) { this.states = states || {}; this.render(); }
    stateOf(tag) { return (tag && this.states[tag]) || {}; }
    /* ---- 그리기 */
    render() {
      const m = this.model; if (!m) return;
      const v = this.view();                                 // 보이는 창 — model.view 가 있으면 그 사각형(식별된 것 둘레)만
      const [vx, vy, W, Hh] = v;
      let g = "";
      const gs = Math.max(50, Math.round(Math.max(W, Hh) / 24 / 50) * 50);
      for (let x = Math.floor(vx / gs) * gs; x <= vx + W; x += gs) g += `<line class="hmi-grid" x1="${x}" y1="${vy}" x2="${x}" y2="${vy + Hh}"/>`;
      for (let y = Math.floor(vy / gs) * gs; y <= vy + Hh; y += gs) g += `<line class="hmi-grid" x1="${vx}" y1="${y}" x2="${vx + W}" y2="${y}"/>`;
      const parts = [`<svg class="hmi-svg" xmlns="http://www.w3.org/2000/svg" viewBox="${vx} ${vy} ${W} ${Hh}" width="${W * this.zoom}" height="${Hh * this.zoom}">`, S.defs(), `<g class="hmi-gridlayer">${g}</g>`];
      parts.push('<g class="layer-signals">' + (m.signals || []).map((s) => `<polyline class="hmi-signal-line" points="${pts(s.points)}"/>`).join("") + "</g>");
      parts.push('<g class="layer-pipes">' + (m.pipes || []).map((p) => this._pipe(p)).join("") + "</g>");
      parts.push('<g class="layer-equip">' + (m.equipment || []).map((e) => this._equip(e)).join("") + "</g>");
      parts.push('<g class="layer-valves">' + (m.valves || []).map((v) => this._valve(v)).join("") + "</g>");
      parts.push('<g class="layer-conn">' + (m.connectors || []).map((c) => this._conn(c)).join("") + "</g>");
      parts.push('<g class="layer-labels">' + (m.labels || []).map((l) => `<text class="hmi-pipe-label" x="${l.x}" y="${l.y}" font-size="${l.size || 11}">${esc(l.text)}</text>`).join("") + "</g>");
      parts.push('<g class="layer-inst">' + (m.instruments || []).map((i) => this._inst(i)).join("") + "</g>");
      parts.push("</svg>");
      this.el.innerHTML = parts.join("");
      this.svg = this.el.querySelector("svg");
      this._applyPan();
      if (this.sel) this._mark(this.sel);
    }
    _pipe(p) {
      const w = p.width || 5, id = esc(p.id || "");
      const flow = p.flow === "fwd" ? ' marker-end="url(#hmi-arrow)"' : p.flow === "rev" ? ' marker-start="url(#hmi-arrow)"' : "";
      const mid = p.points.length >= 2 ? midpoint(p.points) : null;
      return `<polyline class="hmi-pipe svc-${p.service || "other"} role-${p.role || "main"}" data-id="${id}" points="${pts(p.points)}" stroke-width="${w}"${flow}><title>${esc(p.label || SERVICES[p.service] || "")}</title></polyline>`
        + (p.label && mid ? `<text class="hmi-pipe-label" x="${mid[0] + 4}" y="${mid[1] - 6}">${esc(p.label)}</text>` : "");
    }
    _equip(e) {
      const st = this.stateOf(e.tag).state || e.state || "";
      const w = e.w || 80, h = e.h || 60;
      const name = e.name ? `<text class="hmi-equip-name" x="${w / 2}" y="${h + 14}">${esc(e.name)}</text>` : "";
      const tag = e.tag && e.tag !== e.name ? `<text class="hmi-equip-tag" x="${w / 2}" y="${h + (e.name ? 27 : 14)}">${esc(e.tag)}</text>` : "";
      const sb = st ? `<rect class="hmi-status-box st-${st}" x="${w / 2 - 34}" y="${-20}" width="68" height="15" rx="3"/><text class="hmi-status-tag" x="${w / 2}" y="-9" fill="#fff">${esc((STATES[st] || st).split(" ")[0].toUpperCase())}</text>` : "";
      return S.use(e.kind, { x: e.x, y: e.y, w, h, rot: e.rot, cls: (st ? "st-" + st : "") + " hmi-item", attrs: ` data-id="${esc(e.id)}" data-tag="${esc(e.tag || "")}" data-kind="equipment"`, extra: name + tag + sb });
    }
    _valve(v) {
      const st = this.stateOf(v.tag);
      const open = st.open === true || st.s === 1 ? "open" : st.open === false || st.s === 0 ? "closed" : st.travel ? "travel" : v.state || "";
      const size = v.size || 26;
      const tag = v.tag ? `<text class="hmi-valve-tag" x="${size / 2}" y="${-8}">${esc(v.tag)}</text>` : "";
      return S.use(v.kind || "valve-manual", { x: v.x, y: v.y, w: size, h: size, rot: v.rot, cls: (open ? "v-" + open : "") + " hmi-item", attrs: ` data-id="${esc(v.id)}" data-tag="${esc(v.tag || "")}" data-kind="valve"`, extra: tag });
    }
    _inst(i) {
      const st = this.stateOf(i.tag);
      const r = i.r || 13, kind = i.loc === 2 ? "inst-panel" : i.loc === 1 ? "inst-dcs" : "inst-field";
      const alarm = !!st.alarm, vendor = !!i.vendor;
      const [val, unit] = fmtVal(st, i);
      const faceW = Math.max(56, (String(i.tag || "").length * 6.2) + 14), faceH = 28;
      const side = i.face || "above";
      let fx = -faceW / 2 + r, fy = -faceH - 6;                                   // 기본: 버블 위
      if (side === "below") fy = r * 2 + 6; else if (side === "left") { fx = -faceW - 8; fy = r - faceH / 2; } else if (side === "right") { fx = r * 2 + 8; fy = r - faceH / 2; }
      const face = `<g class="facebox" transform="translate(${fx} ${fy})"><rect class="face" x="0" y="0" width="${faceW}" height="${faceH}" rx="3"/>`
        + `<text class="tag" x="${faceW / 2}" y="11">${esc(i.tag || "(no tag)")}</text>`
        + `<text class="val${val ? "" : " dim"}" x="${faceW / 2}" y="24">${esc(val ? `${val} ${unit}`.trim() : "----")}</text></g>`;
      const lines = i.loc === 2 ? `<line x1="${r * 0.2}" y1="${r - 2}" x2="${r * 1.8}" y2="${r - 2}" stroke="var(--hmi-face-line)" stroke-width="1.2"/><line x1="${r * 0.2}" y1="${r + 2}" x2="${r * 1.8}" y2="${r + 2}" stroke="var(--hmi-face-line)" stroke-width="1.2"/>`
        : i.loc === 1 ? `<line x1="${r * 0.15}" y1="${r}" x2="${r * 1.85}" y2="${r}" stroke="var(--hmi-face-line)" stroke-width="1.2"/>` : "";
      const link = i.link ? `<line class="hmi-signal-line" x1="${r}" y1="${r}" x2="${i.link[0] - i.x}" y2="${i.link[1] - i.y}"/>` : "";
      return `<g class="hmi-inst hmi-item${alarm ? " alarm" : ""}${vendor ? " vendor" : ""}${i.tag ? "" : " untagged"}" transform="translate(${i.x} ${i.y})" data-id="${esc(i.id)}" data-tag="${esc(i.tag || "")}" data-kind="instrument" data-sym="${kind}">`
        + link + `<circle class="face" cx="${r}" cy="${r}" r="${r}"/>${lines}<text class="fn" x="${r}" y="${r + 3.5}">${esc(i.fn || "")}</text>` + face + "</g>";
    }
    _conn(c) {
      const w = Math.max(60, String(c.text || "").length * 6.5 + 26), h = 20;
      const out = c.dir === "out";
      const pts2 = out ? `0,0 ${w - 10},0 ${w},${h / 2} ${w - 10},${h} 0,${h}` : `10,0 ${w},0 ${w},${h} 10,${h} 0,${h / 2}`;
      const x = c.side === "left" ? c.x - w : c.x;
      return `<g class="hmi-item" transform="translate(${x} ${c.y - h / 2})" data-id="${esc(c.id)}" data-kind="connector"><polygon class="hmi-conn" points="${pts2}"/><text class="hmi-conn-text" x="${out ? 6 : 14}" y="14">${esc(c.text)}</text></g>`;
    }
    /* ---- 고르기 · 편집 */
    _bind() {
      const el = this.el;
      el.addEventListener("click", (ev) => {
        const g = ev.target.closest(".hmi-item"); if (!g) { this.select(null); return; }
        this.select(g.dataset.id, g);
      });
      el.addEventListener("dblclick", (ev) => {
        const g = ev.target.closest(".hmi-item[data-kind]"); if (!g || !this.onTagEdit) return;
        if (g.dataset.kind !== "instrument" && g.dataset.kind !== "valve" && g.dataset.kind !== "equipment") return;
        ev.preventDefault(); this.editTag(g.dataset.id);
      });
      // 끌기 · Ctrl+휠 확대
      let drag = null;
      el.addEventListener("mousedown", (ev) => { if (ev.button !== 0 || ev.target.closest(".hmi-inline-edit")) return; drag = { x: ev.clientX, y: ev.clientY, px: this.pan.x, py: this.pan.y, moved: false }; });
      window.addEventListener("mousemove", (ev) => { if (!drag) return; const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y; if (Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; el.classList.add("dragging"); } this.pan = { x: drag.px + dx, y: drag.py + dy }; this._applyPan(); });
      window.addEventListener("mouseup", () => { if (drag && drag.moved) this._swallow = true; drag = null; el.classList.remove("dragging"); });
      el.addEventListener("click", (ev) => { if (this._swallow) { this._swallow = false; ev.stopPropagation(); } }, true);
      el.addEventListener("wheel", (ev) => { if (!ev.ctrlKey) return; ev.preventDefault(); this.zoomBy(ev.deltaY < 0 ? 1.15 : 1 / 1.15, ev.clientX, ev.clientY); }, { passive: false });
      new ResizeObserver(() => { if (this.model && !this._userZoom) this.fit(); }).observe(el);
    }
    select(id, g) {
      this.sel = id; this.el.querySelectorAll(".hmi-sel").forEach((x) => x.classList.remove("hmi-sel"));
      this.el.querySelectorAll(".sel-ring").forEach((x) => x.remove());
      if (id) this._mark(id);
      if (this.onSelect) this.onSelect(id ? this.find(id) : null, g || null);
    }
    _mark(id) {
      const g = this.el.querySelector(`.hmi-item[data-id="${cssEsc(id)}"]`); if (!g) return;
      g.classList.add("hmi-sel");
      const b = g.getBBox();
      const ring = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      ring.setAttribute("class", "sel-ring"); ring.setAttribute("x", b.x - 4); ring.setAttribute("y", b.y - 4); ring.setAttribute("width", b.width + 8); ring.setAttribute("height", b.height + 8); ring.setAttribute("rx", 4);
      g.appendChild(ring);
    }
    /* 모델 안의 그 객체 자신 (고칠 때) */
    item(id) {
      const m = this.model; if (!m) return null;
      for (const k of ["instruments", "valves", "equipment", "connectors", "pipes"]) { const it = (m[k] || []).find((x) => x.id === id); if (it) return it; }
      return null;
    }
    find(id) {
      const m = this.model; if (!m) return null;
      const one = { instruments: "instrument", valves: "valve", equipment: "equipment", connectors: "connector", pipes: "pipe" };
      for (const k of Object.keys(one)) { const it = (m[k] || []).find((x) => x.id === id); if (it) return Object.assign({ kind_: one[k] }, it); }
      return null;
    }
    editTag(id) {
      const it = this.find(id); if (!it) return;
      const g = this.el.querySelector(`.hmi-item[data-id="${cssEsc(id)}"]`); if (!g) return;
      const tagEl = g.querySelector(".tag, .hmi-valve-tag, .hmi-equip-tag, .hmi-equip-name");
      const box = (tagEl || g).getBoundingClientRect(), host = this.el.getBoundingClientRect();
      const inp = document.createElement("input");
      inp.className = "hmi-inline-edit"; inp.value = it.tag || (it.kind_ === "equipment" ? it.name : "") || "";
      inp.style.left = `${box.left - host.left + this.el.scrollLeft}px`; inp.style.top = `${box.top - host.top + this.el.scrollTop - 2}px`; inp.style.minWidth = `${Math.max(90, box.width + 20)}px`;
      this.el.appendChild(inp); inp.focus(); inp.select();
      let closed = false;
      const done = (save) => {
        if (closed) return; closed = true;                       // Enter → remove → blur 가 다시 부른다 — 한 번만
        const v = inp.value.trim(); inp.remove();
        if (save && v !== (it.tag || "")) { const field = it.kind_ === "equipment" && !it.tag ? "name" : "tag"; this.onTagEdit(it, v, field); }
      };
      inp.addEventListener("keydown", (ev) => { if (ev.isComposing) return; if (ev.key === "Enter") done(true); else if (ev.key === "Escape") done(false); });
      inp.addEventListener("blur", () => done(true));
    }
    /* ---- 확대 · 끌기 */
    _applyPan() { if (this.svg) this.svg.style.transform = `translate(${this.pan.x}px, ${this.pan.y}px)`; }
    view() { const m = this.model; return m.view && m.view.length === 4 ? m.view : [0, 0, m.width || 1200, m.height || 700]; }
    fit() {
      const m = this.model; if (!m || !this.svg) return;
      const [, , W, Hh] = this.view();
      this.zoom = Math.max(0.05, Math.min((this.el.clientWidth - 16) / W, (this.el.clientHeight - 16) / Hh));
      this.pan = { x: (this.el.clientWidth - W * this.zoom) / 2, y: (this.el.clientHeight - Hh * this.zoom) / 2 };
      this._userZoom = false; this._size();
    }
    _size() { const [, , W, Hh] = this.view(); this.svg.setAttribute("width", W * this.zoom); this.svg.setAttribute("height", Hh * this.zoom); this._applyPan(); }
    zoomBy(f, cx, cy) {
      const r = this.el.getBoundingClientRect(); const px = cx == null ? r.width / 2 : cx - r.left, py = cy == null ? r.height / 2 : cy - r.top;
      this.pan = { x: px - (px - this.pan.x) * f, y: py - (py - this.pan.y) * f }; this.zoom *= f; this._userZoom = true; this._size();
    }
    exportSvg() { return this.svg ? this.svg.outerHTML.replace(/ style="[^"]*"/, "") : ""; }
  }
  H.Screen = Screen;
  function pts(a) { return (a || []).map((p) => `${p[0]},${p[1]}`).join(" "); }
  function midpoint(a) { const i = Math.floor((a.length - 1) / 2); return [(a[i][0] + a[i + 1][0]) / 2, (a[i][1] + a[i + 1][1]) / 2]; }
  function cssEsc(s) { return window.CSS && CSS.escape ? CSS.escape(String(s)) : String(s).replace(/["\\]/g, "\\$&"); }
  function fmtVal(st, i) {
    if (st.v !== undefined && st.v !== null && st.v !== "") return [typeof st.v === "number" ? num(st.v) : String(st.v), st.u || i.unit || ""];
    if (st.s === 1 || st.s === 0) return [st.s === 1 ? "ON" : "OFF", ""];
    if (st.open === true || st.open === false) return [st.open ? "OPEN" : "CLOSED", ""];
    if (i.value !== undefined && i.value !== null && i.value !== "") return [typeof i.value === "number" ? num(i.value) : String(i.value), i.unit || ""];
    return ["", ""];
  }
  H.fmtVal = fmtVal;

  /* ---------------- 패널들 */
  /* Symbol & Legend — 그 화면에 실제로 쓰인 서비스 · 기기 · 계기만 (없으면 전부) */
  H.Legend = function (el, model) {
    const used = model ? {
      svc: [...new Set((model.pipes || []).map((p) => p.service || "other"))],
      eq: [...new Set((model.equipment || []).map((e) => e.kind))],
      inst: [...new Set((model.instruments || []).map((i) => i.fn).filter(Boolean))],
      valves: [...new Set((model.valves || []).map((v) => v.kind))],
    } : null;
    const svc = used && used.svc.length ? used.svc : Object.keys(SERVICES).slice(0, 4);
    const eq = used && used.eq.length ? used.eq : ["compressor", "drum", "heat-exchanger", "pump", "valve-pneumatic", "motor"];
    const vk = used ? used.valves : [];
    const fns = used && used.inst.length ? used.inst : ["PT", "TT", "LT", "FT", "PIC", "TIC", "FIC", "TI"];
    const row = (sw, text) => `<div class="row">${sw}<span>${esc(text)}</span></div>`;
    el.className = "hmi-panel hmi-legend";
    el.innerHTML = `<svg width="0" height="0" style="position:absolute">${S.defs()}</svg><h3>Symbol &amp; Legend</h3>`
      + `<h4>1. Line / Flow</h4>` + svc.map((s) => row(`<span class="sw" style="background:var(--hmi-svc-${s})"></span>`, SERVICES[s] || s)).join("")
      + row(`<span class="icon-wrap">${S.icon("signal", 30)}</span>`, "Instrument Signal (Electrical / Pneumatic)") + row(`<span class="icon-wrap">${S.icon("flow", 30)}</span>`, "Flow Direction")
      + `<h4>2. Equipment</h4>` + eq.concat(vk).map((k) => row(`<span class="icon-wrap">${S.icon(k, 34)}</span>`, (S.get(k) || { label: k }).label)).join("")
      + `<h4>3. Instrument</h4>` + fns.map((f) => row(`<span class="icon-wrap"><svg class="hmi-icon" width="30" height="30" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="var(--hmi-face)" stroke="var(--hmi-face-line)" stroke-width="4"/><text x="50" y="58" font-size="26" font-weight="700" text-anchor="middle" fill="var(--hmi-face-ink)">${esc(f)}</text></svg></span>`, fnLabel(f))).join("")
      + row('<span class="icon-wrap"><span class="sw-box" style="background:var(--hmi-face);border:1px solid var(--hmi-face-line)"></span></span>', "Tag / Value Box (editable — dblclick)");
  };
  const FN = { P: "Pressure", T: "Temperature", L: "Level", F: "Flow", A: "Analysis", Z: "Position", S: "Speed", X: "On-Off / Misc", V: "Vibration", W: "Weight", H: "Hand", E: "Voltage", I: "Current", J: "Power", Q: "Quantity", K: "Time", M: "Moisture", D: "Density", N: "User", Y: "Event", C: "Conductivity", B: "Burner", G: "Gauging", R: "Radiation", U: "Multivariable", O: "Other" };
  const SUF = { T: "Transmitter", I: "Indicator", C: "Controller", S: "Switch", E: "Element", V: "Valve", R: "Recorder", A: "Alarm", Y: "Relay / Computer", Z: "Final Control", G: "Glass / Gauge", W: "Well", Q: "Totalizer", K: "Control Station", L: "Light", H: "High", LL: "Low" };
  function fnLabel(fn) {
    const u = String(fn || "").toUpperCase(); if (!u) return "";
    const first = u[0], rest = u.slice(1).replace(/^D/, (m) => (u[0] === "P" ? "Differential " : m));
    const words = []; for (const ch of rest.replace(/^Differential /, "")) if (SUF[ch]) words.push(SUF[ch]);
    const mid = rest.startsWith("Differential ") ? "Differential " : "";
    return `${FN[first] || first} ${mid}${words.join(" ") || "Instrument"}`.replace("Indicator Controller", "Indicating Controller").replace("Indicator Transmitter", "Indicating Transmitter");
  }
  H.fnLabel = fnLabel;

  /* Symbol Library (Detailed) — 등록표 전부 */
  H.Library = function (el) {
    el.className = "hmi-panel";
    const groups = Object.entries(S.groups).map(([g, title]) => `<div><h4>${esc(title)}</h4>` + S.list().filter((r) => r.group === g).map((r) => `<div class="row">${S.icon(r.kind, 34)}<span>${esc(r.label)}</span></div>`).join("") + "</div>");
    el.innerHTML = `<svg width="0" height="0" style="position:absolute">${S.defs()}</svg><h3>Symbol Library (Detailed)</h3><div class="hmi-library">${groups.join("")}</div>`;
  };

  /* Status / Color */
  H.StatusLegend = function (el) {
    el.className = "hmi-panel";
    el.innerHTML = `<h3>Status / Color</h3><div class="hmi-legend" style="display:grid;grid-template-columns:1fr 1fr;gap:4px 10px">`
      + Object.entries(STATES).map(([k, v]) => `<div><span class="sw-box" style="background:var(--hmi-${k})"></span>${esc(v)}</div>`).join("") + "</div>";
  };

  /* Control Mode */
  H.ControlMode = function (el, opts) {
    const o = Object.assign({ modes: ["AUTO", "MAN", "LOCAL"], value: "AUTO", title: "Control Mode" }, opts || {});
    el.className = "hmi-panel";
    const paint = () => { el.innerHTML = `<h3>${esc(o.title)}</h3><div class="hmi-modes">` + o.modes.map((m) => `<button data-m="${esc(m)}" class="${m === o.value ? "on " + m.toLowerCase() : ""}">${esc(m)}</button>`).join("") + "</div>"; };
    paint();
    el.addEventListener("click", (ev) => { const b = ev.target.closest("button[data-m]"); if (!b) return; o.value = b.dataset.m; paint(); if (o.onChange) o.onChange(o.value); });
    return { set: (v) => { o.value = v; paint(); }, get: () => o.value };
  };

  /* Key Parameters — rows: [{label, tag, unit}] · values 는 states 에서 */
  H.KeyParams = function (el, opts) {
    const o = Object.assign({ title: "Key Parameters", rows: [] }, opts || {});
    el.className = "hmi-panel";
    const api = {
      update(states) {
        el.innerHTML = `<h3>${esc(o.title)}<span class="sp"></span>${o.onPick ? '<button class="hmi-btn" data-pick>고르기</button>' : ""}</h3><table class="hmi-kv">`
          + o.rows.map((r) => { const st = (states && states[r.tag]) || {}; const [v, u] = fmtVal(st, r); return `<tr class="${st.alarm ? "alarm" : ""}"><td>${esc(r.label || r.tag)}${r.tag && r.label ? ` <span style="color:var(--hmi-muted)">(${esc(r.tag)})</span>` : ""}</td><td class="${v ? "" : "dim"}">${esc(v ? `${v} ${u}`.trim() : "----")}</td></tr>`; }).join("")
          + "</table>" + (o.rows.length ? "" : '<p style="color:var(--hmi-muted);margin:6px 0 0">태그를 고르면 여기 값이 섭니다.</p>');
        const b = el.querySelector("[data-pick]"); if (b) b.onclick = () => o.onPick();
      },
      setRows(rows, states) { o.rows = rows; api.update(states); },
      rows: () => o.rows,
    };
    api.update({});
    return api;
  };

  /* Trend — 태그 하나의 시계열.  push(t, v) 로 쌓는다 (모델이 아니라 화면의 기억) */
  H.Trend = function (el, opts) {
    const o = Object.assign({ title: "Trend", tag: "", unit: "", window: 30 * 60 * 1000, max: 600 }, opts || {});
    el.className = "hmi-panel hmi-trend"; const data = [];
    const api = {
      setTag(tag, unit, label) { o.tag = tag; o.unit = unit || ""; o.label = label; data.length = 0; api.draw(); },
      push(v, t) { if (typeof v !== "number" || !isFinite(v)) return; data.push([t || Date.now(), v]); while (data.length > o.max) data.shift(); api.draw(); },
      data: () => data.slice(),
      draw() {
        const W = 400, Hh = 150, L = 38, R = 8, T = 10, B = 22;
        const now = Date.now(), t0 = now - o.window;
        const pts2 = data.filter((d) => d[0] >= t0);
        let lo = Math.min(...pts2.map((d) => d[1]), Infinity), hi = Math.max(...pts2.map((d) => d[1]), -Infinity);
        if (!isFinite(lo)) { lo = 0; hi = 100; } if (hi - lo < 1e-9) { lo -= 1; hi += 1; } const pad = (hi - lo) * 0.15; lo -= pad; hi += pad;
        const X = (t) => L + ((t - t0) / o.window) * (W - L - R), Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (Hh - T - B);
        let g = "";
        for (let k = 0; k <= 4; k++) { const y = T + (k / 4) * (Hh - T - B); g += `<line class="grid" x1="${L}" y1="${y}" x2="${W - R}" y2="${y}"/><text class="lb" x="${L - 4}" y="${y + 3}" text-anchor="end">${num(hi - (k / 4) * (hi - lo), hi - lo < 8 ? 1 : 0)}</text>`; }
        for (let k = 0; k <= 3; k++) { const t = t0 + (k / 3) * o.window, x = X(t); const d = new Date(t); g += `<line class="grid" x1="${x}" y1="${T}" x2="${x}" y2="${Hh - B}"/><text class="lb" x="${x}" y="${Hh - 6}" text-anchor="middle">${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}</text>`; }
        const line = pts2.length ? `<polyline class="ln" points="${pts2.map((d) => `${X(d[0]).toFixed(1)},${Y(d[1]).toFixed(1)}`).join(" ")}"/>` : "";
        const last = pts2.length ? pts2[pts2.length - 1][1] : null;
        el.innerHTML = `<h3>${esc(o.title)}${o.label || o.tag ? ` <span style="color:var(--hmi-muted);font-weight:400">(${esc(o.label || o.tag)})</span>` : ""}<span class="sp"></span>${last != null ? `<span class="cur" style="font-family:Consolas,monospace">${num(last)} ${esc(o.unit)}</span>` : ""}</h3>`
          + `<svg viewBox="0 0 ${W} ${Hh}" preserveAspectRatio="none">${g}<line class="ax" x1="${L}" y1="${T}" x2="${L}" y2="${Hh - B}"/><line class="ax" x1="${L}" y1="${Hh - B}" x2="${W - R}" y2="${Hh - B}"/>${line}</svg>`
          + (pts2.length ? "" : `<p style="color:var(--hmi-muted);margin:4px 0 0;font-size:11px">${o.tag ? "값이 들어오면 선이 그려집니다 (칠하기 · 로직 연동)" : "그림의 계기를 누르면 그 태그의 추이를 봅니다"}</p>`);
      },
    };
    api.draw();
    return api;
  };

  /* Faceplate — 요소를 누르면 옆에 뜨는 작은 창 */
  H.Faceplate = function (host, item, states, opts) {
    const o = opts || {}; host.querySelectorAll(".hmi-faceplate").forEach((x) => x.remove());
    if (!item) return null;
    const st = (states && item.tag && states[item.tag]) || {};
    const kind = item.kind_;
    const title = kind === "equipment" ? (item.name || item.kind) : kind === "valve" ? (item.tag || "Valve") : (item.tag || item.fn || "Instrument");
    const stt = st.state || item.state || "";
    const rows = [];
    if (kind === "instrument") { const [v, u] = fmtVal(st, item); rows.push(["Tag", item.tag || "—"], ["Function", `${item.fn || ""} — ${fnLabel(item.fn)}`], ["Value", v ? `${v} ${u}` : "----"], ["Alarm", st.alarm ? "ACTIVE" : "—"]); if (item.lineNo) rows.push(["Line", `${item.lineNo} ${item.lineSize || ""}`]); if (item.scope) rows.push(["Supply", item.scope]); }
    else if (kind === "valve") { const open = st.open === true || st.s === 1 ? "OPEN" : st.open === false || st.s === 0 ? "CLOSED" : "—"; rows.push(["Tag", item.tag || "—"], ["Type", (S.get(item.kind) || {}).label || item.kind], ["Position", open]); if (item.body) rows.push(["Body", `${item.body} · ${item.actuator || "manual"}`]); }
    else if (kind === "equipment") { rows.push(["Name", item.name || "—"], ["Tag", item.tag || "—"], ["Status", stt ? STATES[stt] : "—"]); for (const [k, v] of Object.entries(st.params || item.params || {})) rows.push([k, v]); }
    else rows.push(["Text", item.text || item.label || ""]);
    const fp = document.createElement("div"); fp.className = "hmi-faceplate";
    fp.innerHTML = `<h3 class="${stt === "trip" || st.alarm ? "trip" : stt === "standby" ? "standby" : ""}">${esc(title)}<span class="sp"></span><span class="x" title="닫기">✕</span></h3>`
      + `<table>${rows.map(([k, v]) => `<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("")}</table>`
      + (o.tools ? `<div class="tools">${o.tools}</div>` : "");
    const r = host.getBoundingClientRect(); const ax = o.anchor ? o.anchor.getBoundingClientRect() : null;
    fp.style.left = `${ax ? Math.min(ax.right - r.left + 10, r.width - 230) : 16}px`; fp.style.top = `${ax ? Math.max(8, ax.top - r.top) : 16}px`;
    host.appendChild(fp);
    fp.querySelector(".x").onclick = () => fp.remove();
    return fp;
  };

  /* Plant 상태 칩 */
  H.StatusChip = function (el, states) {
    const vals = Object.values(states || {});
    const alarm = vals.some((s) => s && (s.alarm || s.state === "trip")), warn = !alarm && vals.some((s) => s && s.state === "standby");
    el.className = "hmi-chip" + (alarm ? " alarm" : warn ? " warn" : "");
    el.innerHTML = `<i></i>${alarm ? "Alarm Active" : warn ? "Standby" : "Plant Normal"}`;
  };
})();
