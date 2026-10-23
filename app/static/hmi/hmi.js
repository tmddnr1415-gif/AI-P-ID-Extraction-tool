/* HMI 그래픽 — 장면 JSON 을 그리고(심볼 사전 hmi_symbols.js) · 끌어 옮기고 · 태그를 고치고 · 값을 데모로 움직인다.
 * 판정은 없다.  장면은 /dcs/api 에서 오고(예시 · 식별 결과 · 저장본) 저장은 POST 한 곳(saveScene)뿐이다.
 *
 * LOGIC 브랜치 H1회차의 화면(hmi.js) 그대로에 hotfix110 이 더한 것:
 *  · 장면은 서버가 실제 P&ID 배치로 만든다 (app/hmi/scene.py — 탭한 런 · 같은 배율) — 크므로 확대 · 이동(휠 · 끌기 · 맞춤)
 *  · 값 상자는 장면이 고른 쪽(face: above/below/left/right)에 — 촘촘한 장에서 서로 덮지 않게
 *  · 라벨(라인 깃발 · TO/FROM 커넥터)
 *  · LOGIC 창과 태그로 연동 — 창이 열어 주면(?logic=&link=) `dcs-ready`(태그 목록)를 보내고 `dcs-states`(태그 → 값)를 받아 칠한다 ·
 *    심볼을 누르면 `dcs-go` 로 LOGIC 이 그 태그 행으로 간다 (logic.js openDcsWindow / dcsStates 와 같은 계약)
 *  · 내려받기(SVG · PNG · 서버 zip) · 절전모드 보관 목록 */
(function () {
  "use strict";
  const $ = (s, el) => (el || document).querySelector(s);
  const SYM = window.HMI_SYM, S = window.HMI_SYMBOLS, LINES = window.HMI_LINES, STATUS = window.HMI_STATUS;
  const ST_ORDER = ["running", "standby", "trip", "stopped", "oos"];
  const Q = new URLSearchParams(location.search);
  const A = {
    scene: null, src: "example", job: null, page: null, editing: true, sim: true, sel: null, selKind: null,
    trend: {}, timer: null, drag: null, ctlMode: "AUTO", dirty: false,
    vb: null, pan: null, motorOpen: false, sheets: [], tags: [], logicJob: Q.get("logic") || "", link: Q.get("link") || "",
    lastLogic: null, pending: null
  };
  const nrm = (t) => String(t || "").toUpperCase().replace(/[\s\-]/g, "");

  // ---------------------------------------------------------------- 그리기
  function px(n) { return Math.round(n * 10) / 10; }
  function pts(p) { return p.map((q) => q.join(",")).join(" "); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
  function statusColor(st) { return (STATUS[st] || STATUS.stopped).color; }
  function instrumentsOn(id) { return (A.scene.instruments || []).filter((i) => i.on === id); }
  function equipOf(ins) { return (A.scene.equipment || []).find((e) => e.id === ins.on); }
  function pipeOf(ins) { return (A.scene.pipes || []).find((p) => p.id === ins.on); }
  function isAlarm(ins) {
    const e = equipOf(ins);
    if (e && e.status === "trip") return true;
    if (ins.alarmLive) return true;
    if (ins.live && ins.value == null) return false;
    if (ins.hi != null && ins.value > ins.hi) return true;
    if (ins.lo != null && ins.value < ins.lo) return true;
    return false;
  }

  function drawPipe(p) {
    const L = LINES[p.kind] || LINES.process;
    const marker = p.arrow === false ? "" : ` marker-end="url(#hmi-arrow-${p.kind in LINES ? p.kind : "process"})"`;
    const sig = p.kind === "signal" ? " signal" : "";
    let s = `<g class="pipeg" data-id="${esc(p.id)}">`;
    s += `<polyline class="pipe base${sig}" points="${pts(p.pts)}" stroke="${L.color}"${marker}/>`;
    if (p.kind !== "signal") s += `<polyline class="pipe flow${p.dir === -1 ? " rev" : ""}" points="${pts(p.pts)}"/>`;
    if (p.label) {
      const a = p.pts[0], b = p.pts[p.pts.length - 1];
      const horizontalFirst = p.pts.length > 1 && Math.abs(p.pts[1][1] - a[1]) < 1;
      const lx = horizontalFirst ? a[0] + 4 : b[0] + 6, ly = horizontalFirst ? a[1] - 8 : b[1] - 8;
      s += `<text class="pipe-label" x="${px(lx)}" y="${px(ly)}">${esc(p.label)}</text>`;
    }
    s += p.pts.map((q, i) => `<circle class="vtx" data-pipe="${esc(p.id)}" data-i="${i}" cx="${q[0]}" cy="${q[1]}" r="5"/>`).join("");
    return s + "</g>";
  }
  function statusPill(x, y, st, w) {
    const ww = w || 72;
    return `<g class="stpill" transform="translate(${px(x - ww / 2)} ${px(y)})"><rect width="${ww}" height="16" fill="${statusColor(st)}"/><text x="${ww / 2}" y="12">${esc((STATUS[st] || STATUS.stopped).en.toUpperCase())}</text></g>`;
  }
  function drawEquip(e) {
    const st = e.status || "running";
    let s = `<g class="node equip${A.sel === e.id ? " sel" : ""}" data-kind="equipment" data-id="${esc(e.id)}">`;
    s += `<rect class="statusring" x="${px(e.x - 6)}" y="${px(e.y - 6)}" width="${e.w + 12}" height="${e.h + 12}" stroke="${statusColor(st)}" opacity="${st === "running" ? .35 : .9}"/>`;
    s += S.g(e.sym, e.x, e.y, e.w, e.h, { status: st });
    s += `<text class="tag" data-edit="tag" x="${px(e.x + e.w / 2)}" y="${px(e.y + e.h + 18)}">${esc(e.tag)}</text>`;
    s += statusPill(e.x + e.w / 2, e.y + e.h + 24, st);
    if (e.label && e.label !== e.tag) s += `<text class="eqlabel" x="${px(e.x + e.w / 2)}" y="${px(e.y - 12)}">${esc(e.label)}</text>`;
    return s + "</g>";
  }
  function drawValve(v) {
    const closed = v.state === "closed";
    let s = `<g class="node valve${A.sel === v.id ? " sel" : ""}" data-kind="valves" data-id="${esc(v.id)}" data-tag="${esc(v.tag || "")}">`;
    s += S.g(v.sym, v.x, v.y, v.w || 40, v.h || 40, { closed }, v.rot || 0);
    s += v.tag ? `<text class="tag" data-edit="tag" x="${px(v.x + (v.w || 40) / 2)}" y="${px(v.y - 6)}">${esc(v.tag)}</text>`
               : `<text class="tag notag" data-edit="tag" x="${px(v.x + (v.w || 40) / 2)}" y="${px(v.y - 6)}">(태그 없음)</text>`;
    s += `<text class="valtext" x="${px(v.x + (v.w || 40) / 2)}" y="${px(v.y + (v.h || 40) + 12)}" fill="${closed ? STATUS.stopped.color : STATUS.running.color}">${closed ? "CLOSED" : "OPEN"}</text>`;
    return s + "</g>";
  }
  /** 값 상자 자리 — 장면이 고른 쪽 (app/hmi/scene.py face_box 와 같은 수). */
  function faceBox(i) {
    const r = 20, bw = 76, bh = 34, side = i.face || "above";
    if (side === "below") return [i.x - bw / 2, i.y + r + 10, bw, bh];
    if (side === "right") return [i.x + r + 8, i.y - bh / 2, bw, bh];
    if (side === "left") return [i.x - r - 8 - bw, i.y - bh / 2, bw, bh];
    return [i.x - bw / 2, i.y - r - bh - 10, bw, bh];
  }
  function drawInstrument(i) {
    const r = 20, kind = i.kind || S.instrumentKind(i.func);
    const alarm = isAlarm(i);
    const linked = A.link && i.tag && A.lastLogic && A.lastLogic.has(nrm(i.tag));
    let s = `<g class="node inst${A.sel === i.id ? " sel" : ""}${linked ? " linked" : ""}" data-kind="instruments" data-id="${esc(i.id)}" data-tag="${esc(i.tag || "")}">`;
    s += S.g("instrument", i.x - r, i.y - r, r * 2, r * 2, { letters: i.func, kind });
    // 값 상자 — 장면이 고른 쪽 (태그 · 값 단위)
    const [bx, by, bw, bh] = faceBox(i), side = i.face || "above";
    const lx = side === "right" ? bx : side === "left" ? bx + bw : i.x, ly = side === "below" ? by : side === "above" ? by + bh : i.y;
    const sx = side === "right" ? i.x + r : side === "left" ? i.x - r : i.x, sy = side === "below" ? i.y + r : side === "above" ? i.y - r : i.y;
    s += `<line class="leader" x1="${px(sx)}" y1="${px(sy)}" x2="${px(lx)}" y2="${px(ly)}"/>`;
    const anchor = anchorOf(i);
    if (anchor) s += `<line class="leader" x1="${px(i.x)}" y1="${px(i.y + r)}" x2="${px(anchor[0])}" y2="${px(anchor[1])}"/>`;
    const cx = bx + bw / 2;
    s += `<rect class="valbox${alarm ? " alarm" : ""}" x="${px(bx)}" y="${px(by)}" width="${bw}" height="${bh}"/>`;
    s += i.tag ? `<text class="valtext tagtext" data-edit="tag" x="${px(cx)}" y="${px(by + 13)}">${esc(i.tag)}</text>`
               : `<text class="valtext tagtext notag" data-edit="tag" x="${px(cx)}" y="${px(by + 13)}">(태그 없음)</text>`;
    const dig = i.live && i.value == null && i.dig != null ? (i.dig ? " on" : " off") : "";
    s += `<text class="valtext v${alarm ? " alarm" : ""}${i.live ? " live" : ""}${dig}" data-val="${esc(i.id)}" x="${px(cx)}" y="${px(by + 28)}">${fmt(i)}</text>`;
    return s + "</g>";
  }
  /** 라벨 — 라인 깃발(라인 번호 · 직경) · TO/FROM 커넥터 (도면이 인쇄한 글자 그대로). */
  function drawLabel(l) {
    if (l.kind === "conn") {
      const w = Math.max(60, String(l.text).length * 7 + 18), h = 20, x = l.x - w / 2, y = l.y - h / 2;
      const tip = l.dir === "TO" ? `M${px(x + w)},${px(y)} L${px(x + w + 10)},${px(y + h / 2)} L${px(x + w)},${px(y + h)}` : `M${px(x)},${px(y)} L${px(x - 10)},${px(y + h / 2)} L${px(x)},${px(y + h)}`;
      return `<g class="lbl-conn"><rect x="${px(x)}" y="${px(y)}" width="${px(w)}" height="${h}" rx="3"/><path d="${tip}" fill="#16304f" stroke="#9fb3c8" stroke-width="1.2"/><text x="${px(l.x)}" y="${px(l.y + 4)}" text-anchor="middle">${esc(l.text)}</text></g>`;
    }
    return `<text class="lbl-line" x="${px(l.x)}" y="${px(l.y)}">${esc(l.text)}</text>`;
  }
  /** 계기가 달린 배관·기기의 가장 가까운 자리 — 점선을 긋기 위해 (선분에 수선의 발 · 기기는 가장 가까운 변). */
  function anchorOf(i) {
    const p = pipeOf(i);
    if (p && p.pts.length > 1) {
      let best = null, bd = Infinity;
      for (let k = 0; k + 1 < p.pts.length; k++) {
        const [ax, ay] = p.pts[k], [bx, by] = p.pts[k + 1];
        const dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy || 1;
        const t = Math.max(0, Math.min(1, ((i.x - ax) * dx + (i.y - ay) * dy) / L2));
        const q = [ax + t * dx, ay + t * dy], d = Math.hypot(q[0] - i.x, q[1] - i.y);
        if (d < bd) { bd = d; best = q; }
      }
      return bd > 24 ? best : null;
    }
    const e = equipOf(i);
    if (e) {
      const cx = Math.max(e.x, Math.min(e.x + e.w, i.x)), cy = Math.max(e.y, Math.min(e.y + e.h, i.y));
      return Math.hypot(cx - i.x, cy - i.y) > 24 ? [cx, cy] : null;
    }
    return null;
  }
  function fmt(i) {
    if (i.live && (i.value == null || i.value === "") && i.dig != null) return i.dig ? "ON (1)" : "OFF (0)";
    if (i.value == null || i.value === "") return "—";
    const v = Number(i.value);
    return (Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(1)) + (i.unit ? " " + i.unit : "");
  }
  function render() {
    const sc = A.scene, svg = $("#svg");
    if (!sc) return;
    const [W, H] = sc.size || [1400, 800];
    if (!A.vb) A.vb = [0, 0, W, H];
    svg.setAttribute("viewBox", A.vb.map(px).join(" "));
    let s = S.lineDefs();
    s += `<g id="l-pipes">${(sc.pipes || []).map(drawPipe).join("")}</g>`;
    s += `<g id="l-labels">${(sc.labels || []).map(drawLabel).join("")}</g>`;
    s += `<g id="l-equip">${(sc.equipment || []).map(drawEquip).join("")}</g>`;
    s += `<g id="l-valves">${(sc.valves || []).map(drawValve).join("")}</g>`;
    s += `<g id="l-inst">${(sc.instruments || []).map(drawInstrument).join("")}</g>`;
    svg.innerHTML = s;
    $("#title").textContent = sc.title || "DCS Graphic";
    $("#basis").textContent = sc.basis || "";
    $("#basis").title = sc.basis || "";
    renderPanels();
    renderPlant();
    renderLegend();
  }
  function renderPlant() {
    const sts = (A.scene.equipment || []).map((e) => e.status);
    const st = sts.includes("trip") ? "trip" : sts.includes("standby") ? "standby" : sts.length && sts.every((x) => x === "stopped" || x === "oos") ? "stopped" : "running";
    const el = $("#plant");
    el.className = "pill st-" + st;
    el.textContent = "● " + (st === "running" ? "Plant Normal" : st === "trip" ? "Plant Alarm" : st === "standby" ? "Plant Standby" : "Plant Stopped");
  }

  // ---------------------------------------------------------------- 패널 (제어 모드 · 트렌드 · Key · 모터)
  function findIns(tag) { return (A.scene.instruments || []).find((i) => i.tag === tag || i.id === tag); }
  function renderPanels() {
    const P = A.scene.panels || {};
    // 제어 모드
    const ctl = P.control && findIns(P.control.tag);
    $("#ctl-tag").textContent = ctl ? ctl.tag : "(제어기 없음)";
    A.ctlMode = (P.control && P.control.mode) || A.ctlMode;
    document.querySelectorAll("#modes .mode").forEach((b) => b.classList.toggle("on", b.dataset.mode === A.ctlMode));
    $("#ctl-sp").textContent = ctl ? `SP ${fmt(ctl)} · PV ${fmt(ctl)} · ${A.ctlMode === "AUTO" ? "DCS 가 조절" : A.ctlMode === "MAN" ? "운전원 수동" : "현장 제어"}` : "";
    // 트렌드 선택
    const sel = $("#trend-tag");
    sel.innerHTML = (A.scene.instruments || []).map((i) => `<option value="${esc(i.tag)}">${esc(i.tag)}</option>`).join("");
    const want = (P.trend && P.trend.tag) || (A.scene.instruments[0] || {}).tag;
    if (want) sel.value = want;
    renderTrend();
    // Key
    const keys = (P.key && P.key.length ? P.key : (A.scene.instruments || []).slice(0, 6).map((i) => i.tag));
    $("#key").innerHTML = keys.map((t) => { const i = findIns(t); return i ? `<tr><td>${esc(keyLabel(i))}</td><td data-key="${esc(i.id)}" class="${isAlarm(i) ? "alarm" : ""}">${fmt(i)}</td></tr>` : ""; }).join("") || `<tr><td class="muted">계기가 없습니다</td></tr>`;
    // 모터 팝업
    const m = P.motor && (A.scene.equipment || []).find((e) => e.id === P.motor);
    if (m && m.params && A.motorOpen) {
      $("#motor-panel").hidden = false;
      $("#motor-title").textContent = `${m.label || "Motor"} · ${m.tag}`;
      const run = m.status === "running";
      $("#motor-table").innerHTML = Object.entries(m.params).map(([k, [v, u]]) => `<tr><td>${esc(k)}</td><td>${v == null ? "—" : run ? v : 0} ${esc(u)}</td></tr>`).join("") +
        `<tr><td>Status</td><td style="color:${statusColor(m.status)}">${esc((STATUS[m.status] || STATUS.stopped).en)}</td></tr>`;
    } else $("#motor-panel").hidden = true;
  }
  function keyLabel(i) {
    const f = i.func || "";
    const word = { P: "Pressure", T: "Temp", L: "Level", F: "Flow", A: "Analysis" }[f[0]] || f;
    const where = pipeOf(i) ? (pipeOf(i).label || "") : equipOf(i) ? equipOf(i).tag : "";
    return `${where ? where.split(" ")[0] + " " : ""}${word} (${i.tag})`;
  }
  function renderTrend() {
    const tag = $("#trend-tag").value, i = findIns(tag), svg = $("#trend");
    $("#trend-title").textContent = i ? `${keyLabel(i)}${i.unit ? " · " + i.unit : ""}` : "Trend";
    if (!i) { svg.innerHTML = ""; return; }
    const buf = A.trend[i.id] || [];
    const P = (A.scene.panels || {}).trend || {};
    const lo = P.tag === tag && P.min != null ? P.min : Math.min(i.value * 0.7, ...(buf.length ? buf : [i.value]));
    const hi = P.tag === tag && P.max != null ? P.max : Math.max(i.value * 1.3, ...(buf.length ? buf : [i.value]));
    const W = 380, H = 150, L = 40, B = 20;
    const y = (v) => H - B - (v - lo) / ((hi - lo) || 1) * (H - B - 8);
    const n = Math.max(buf.length, 120);
    const x = (k) => L + (W - L - 6) * (k / (n - 1));
    const start = n - buf.length;
    let s = "";
    for (let g = 0; g <= 4; g++) {
      const v = lo + (hi - lo) * g / 4, yy = y(v);
      s += `<line x1="${L}" y1="${yy}" x2="${W - 6}" y2="${yy}" stroke="#1f3a55"/><text x="${L - 4}" y="${yy + 4}" font-size="10" fill="#8aa0b8" text-anchor="end">${v.toFixed(0)}</text>`;
    }
    const now = new Date();
    for (let g = 0; g <= 3; g++) {
      const t = new Date(now.getTime() - (3 - g) * 40 * 1000);
      s += `<text x="${L + (W - L - 6) * g / 3}" y="${H - 4}" font-size="10" fill="#8aa0b8" text-anchor="middle">${t.toTimeString().slice(0, 5)}</text>`;
    }
    if (buf.length) s += `<polyline fill="none" stroke="${isAlarm(i) ? "#ff3b6b" : "#2ecc71"}" stroke-width="2" points="${buf.map((v, k) => `${x(start + k).toFixed(1)},${y(v).toFixed(1)}`).join(" ")}"/>`;
    svg.innerHTML = s;
  }

  // ---------------------------------------------------------------- 범례 · 라이브러리 (같은 사전)
  function renderLegend() {
    const el = $("#legend");
    let s = `<h2>Symbol &amp; Legend</h2><h3>1. Line / Flow</h3>`;
    const used = new Set(((A.scene && A.scene.pipes) || []).map((p) => p.kind));
    for (const [k, L] of Object.entries(LINES)) {
      if (used.size && !used.has(k) && !["process", "signal"].includes(k)) continue;
      s += `<div class="lg-row"><svg class="lg-line" viewBox="0 0 64 12"><line x1="2" y1="6" x2="54" y2="6" stroke="${L.color}" stroke-width="4" ${L.dash ? `stroke-dasharray="${L.dash}"` : ""}/><path d="M52,1 L63,6 L52,11 Z" fill="${L.color}"/></svg><span>${esc(L.ko)}</span></div>`;
    }
    s += `<h3>2. Equipment</h3>`;
    const syms = new Set([...((A.scene && A.scene.equipment) || []).map((e) => e.sym), ...((A.scene && A.scene.valves) || []).map((v) => v.sym)]);
    const eq = syms.size ? Object.keys(SYM).filter((n) => syms.has(n)) : ["compressor", "separator", "heat_exchanger", "pump", "valve_block", "motor"];
    for (const n of eq) s += `<div class="lg-row">${S.svg(n, {}, 34)}<span>${esc(SYM[n].ko)} <span class="muted">${esc(SYM[n].label)}</span></span></div>`;
    s += `<h3>3. Instrument</h3>`;
    for (const [l, en, ko, kind] of window.HMI_INSTRUMENTS) s += `<div class="lg-row">${S.svg("instrument", { letters: l, kind }, 30)}<span>${esc(ko)} <span class="muted">${esc(en)}</span></span></div>`;
    s += `<h3>Status / Color</h3>`;
    for (const [k, st] of Object.entries(STATUS)) s += `<div class="lg-row"><span class="lg-sw" style="background:${st.color}"></span><span>${esc(st.ko)}</span></div>`;
    s += `<h3>동작</h3><div class="lg-row muted">상태 띠를 누르면 Running → Standby → Trip → Stopped 순으로 바뀝니다 · 밸브를 누르면 열림/닫힘 · 편집 모드에서 끌어 옮기고 태그를 두 번 누르면 고칩니다</div>`;
    el.innerHTML = s;
    if ($("#library").childElementCount) return;
    // 라이브러리
    let lib = "";
    for (const c of window.HMI_SYM_CATS) {
      lib += `<div class="lib-cat"><h3>${esc(c.label)} <span class="muted">${esc(c.ko)}</span></h3>`;
      if (c.key === "line") {
        for (const [k, L] of Object.entries(LINES)) lib += `<div class="lib-item"><svg class="lg-line" viewBox="0 0 64 12" width="64" height="12"><line x1="2" y1="6" x2="54" y2="6" stroke="${L.color}" stroke-width="4" ${L.dash ? `stroke-dasharray="${L.dash}"` : ""}/><path d="M52,1 L63,6 L52,11 Z" fill="${L.color}"/></svg><span>${esc(L.en)} <span class="en">${esc(L.ko)}</span></span></div>`;
        lib += `<div class="lib-item"><svg viewBox="0 0 64 12" width="64" height="12"><line x1="2" y1="6" x2="54" y2="6" stroke="#dbe6f2" stroke-width="3"/><path d="M52,1 L63,6 L52,11 Z" fill="#dbe6f2"/></svg><span>Flow Direction <span class="en">흐름 방향</span></span></div>`;
        lib += `<div class="lib-item"><svg viewBox="0 0 64 12" width="64" height="12"><line x1="2" y1="6" x2="26" y2="6" stroke="#9fb3c8" stroke-width="3"/><line x1="38" y1="6" x2="62" y2="6" stroke="#9fb3c8" stroke-width="3"/><path d="M26,2 L30,10 M34,2 L38,10" stroke="#9fb3c8" stroke-width="2"/></svg><span>Line Break <span class="en">라인 끊김</span></span></div>`;
      } else if (c.key === "instrument") {
        for (const [l, en, ko, kind] of window.HMI_INSTRUMENTS) lib += `<div class="lib-item">${S.svg("instrument", { letters: l, kind }, 36)}<span>${esc(en)} <span class="en">${esc(ko)}</span></span></div>`;
      } else {
        for (const n of Object.keys(SYM).filter((k) => SYM[k].cat === c.key)) lib += `<div class="lib-item">${S.svg(n, {}, 40)}<span>${esc(SYM[n].label)} <span class="en">${esc(SYM[n].ko)}</span></span></div>`;
      }
      lib += `</div>`;
    }
    $("#library").innerHTML = lib;
  }

  // ---------------------------------------------------------------- 데모 시뮬레이션 (값이 움직인다 — 실제 공정값이 아니다)
  function tick() {
    const sc = A.scene;
    if (!sc) return;
    for (const i of sc.instruments || []) {
      if (i.value == null || i.value === "" || i.live) continue;
      if (i.base == null) i.base = Number(i.value);
      const e = equipOf(i), p = pipeOf(i);
      const dead = (e && (e.status === "stopped" || e.status === "oos")) || (p && p.off);
      const target = dead ? 0 : i.base;
      const noise = dead ? 0 : i.base * 0.004 * (Math.random() * 2 - 1);
      i.value = Math.round((i.value + (target - i.value) * 0.15 + noise) * 10) / 10;
      const buf = A.trend[i.id] || (A.trend[i.id] = []);
      buf.push(i.value);
      if (buf.length > 120) buf.shift();
      const t = document.querySelector(`[data-val="${CSS.escape(i.id)}"]`);
      if (t) { t.textContent = fmt(i); t.classList.toggle("alarm", isAlarm(i)); }
      const k = document.querySelector(`#key td[data-key="${CSS.escape(i.id)}"]`);
      if (k) { k.textContent = fmt(i); k.classList.toggle("alarm", isAlarm(i)); }
    }
    renderTrend();
  }
  function setSim(on) {
    A.sim = on;
    $("#sim").classList.toggle("on", on);
    $("#sim").textContent = on ? "▶ 시뮬레이션" : "⏸ 시뮬레이션";
    clearInterval(A.timer);
    if (on) A.timer = setInterval(tick, 1000);
  }

  // ---------------------------------------------------------------- 상호작용 (상태 · 밸브 · 끌기 · 태그 편집)
  function svgPoint(ev) {
    const svg = $("#svg"), pt = svg.createSVGPoint();
    pt.x = ev.clientX; pt.y = ev.clientY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
  }
  function itemOf(kind, id) { return (A.scene[kind] || []).find((o) => o.id === id); }
  // ---------------------------------------------------------------- 확대 · 이동 (viewBox 만 — 장면 좌표는 그대로)
  function setVB(vb) { A.vb = vb; $("#svg").setAttribute("viewBox", vb.map(px).join(" ")); }
  function zoomBy(f, cx, cy) {
    const [x, y, w, h] = A.vb, [W, H] = A.scene.size || [1400, 800];
    const nw = Math.max(120, Math.min(Math.max(W, H) * 3, w / f)), k = nw / w, nh = h * k;
    if (cx == null) { cx = x + w / 2; cy = y + h / 2; }
    setVB([cx - (cx - x) * k, cy - (cy - y) * k, nw, nh]);
  }
  /** 맞춤 — 장면 전체.  실제 P&ID 장은 넓어 전체를 보이면 글자가 읽히지 않으므로, 한 화면 단위가 READABLE px 보다 작아지면
   *  계기가 가장 많이 모인 곳으로 READABLE px 까지만 줄인다 (맞춤을 한 번 더 누르면 전체). */
  function fitView(all) {
    const [W, H] = A.scene.size || [1400, 800], st = $("#stage").getBoundingClientRect();
    setVB([0, 0, W, H]);
    if (all || !st.width) return;
    const READABLE = 0.9, k = Math.min(st.width / W, st.height / H);
    if (k >= READABLE) return;
    const w = st.width / READABLE, h = st.height / READABLE, ins = A.scene.instruments || [];
    // 창 크기만 한 칸 중 계기가 가장 많이 드는 자리 (계기 하나하나를 가운데로 놓아 본다)
    let cx = W / 2, cy = H / 2, best = -1;
    for (const c of ins) {
      const n = ins.filter((i) => Math.abs(i.x - c.x) < w * 0.45 && Math.abs(i.y - c.y) < h * 0.42).length;
      if (n > best) { best = n; cx = c.x; cy = c.y; }
    }
    setVB([Math.max(0, Math.min(W - w, cx - w / 2)), Math.max(0, Math.min(H - h, cy - h / 2)), w, h]);
  }
  function bindStage() {
    const svg = $("#svg");
    svg.addEventListener("pointerdown", (ev) => {
      const vtx = ev.target.closest(".vtx");
      if (vtx && A.editing) {
        const p = (A.scene.pipes || []).find((q) => q.id === vtx.dataset.pipe);
        A.sel = p.id; A.selKind = "pipes"; renderProps();
        A.drag = { kind: "vtx", pipe: p, i: Number(vtx.dataset.i), start: svgPoint(ev), orig: p.pts[Number(vtx.dataset.i)].slice() };
        /* 포인터 캡처를 쓰지 않는다 — 캡처하면 click · dblclick 의 대상이 svg 가 되어 심볼을 못 찾는다 */ return;
      }
      const node = ev.target.closest(".node");
      if (!node) {
        const pg = ev.target.closest(".pipeg");
        if (pg) { A.sel = pg.dataset.id; A.selKind = "pipes"; renderProps(); }
        const m = svg.getScreenCTM();
        A.pan = { x: ev.clientX, y: ev.clientY, vb: A.vb.slice(), k: m ? m.a : 1, moved: false };
        return;
      }
      const o = itemOf(node.dataset.kind, node.dataset.id);
      if (!o) return;
      A.sel = o.id; A.selKind = node.dataset.kind;
      renderProps();
      logicGo(o);
      if (A.editing) {
        A.drag = { kind: "node", o, start: svgPoint(ev), orig: { x: o.x, y: o.y }, moved: false };
        /* 포인터 캡처를 쓰지 않는다 — 캡처하면 click · dblclick 의 대상이 svg 가 되어 심볼을 못 찾는다 */
      }
    });
    window.addEventListener("pointermove", (ev) => {
      if (A.pan) {
        const dx = ev.clientX - A.pan.x, dy = ev.clientY - A.pan.y;
        if (!A.pan.moved && Math.abs(dx) + Math.abs(dy) < 4) return;
        A.pan.moved = true; $("#stage").classList.add("panning");
        setVB([A.pan.vb[0] - dx / A.pan.k, A.pan.vb[1] - dy / A.pan.k, A.pan.vb[2], A.pan.vb[3]]);
        return;
      }
      if (!A.drag) return;
      const p = svgPoint(ev), dx = p.x - A.drag.start.x, dy = p.y - A.drag.start.y;
      if (!dx && !dy) return;                       // 움직이지 않은 pointermove 에 다시 그리면 두 번 누르기가 깨진다
      if (A.drag.kind === "vtx") {
        A.drag.pipe.pts[A.drag.i] = [px(A.drag.orig[0] + dx), px(A.drag.orig[1] + dy)];
      } else {
        A.drag.o.x = px(A.drag.orig.x + dx); A.drag.o.y = px(A.drag.orig.y + dy); A.drag.moved = Math.abs(dx) + Math.abs(dy) > 2;
      }
      markDirty(); render();
    });
    window.addEventListener("pointerup", (ev) => {
      if (A.pan) { if (A.pan.moved) A.justMoved = true; A.pan = null; $("#stage").classList.remove("panning"); return; }
      A.justMoved = !!(A.drag && (A.drag.moved || A.drag.kind === "vtx"));
      if (A.justMoved) renderProps();
      A.drag = null;
    });
    // 화살표 키로 조금씩 (Shift = 10) · Delete 로 지움
    document.addEventListener("keydown", (ev) => {
      if (!A.sel || !A.editing || ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
      const o = itemOf(A.selKind, A.sel);
      if (!o) return;
      const d = ev.shiftKey ? 10 : 2;
      const mv = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, -d], ArrowDown: [0, d] }[ev.key];
      if (!mv) { if (ev.key === "Delete") removeSelected(); return; }
      ev.preventDefault();
      if (A.selKind === "pipes") o.pts = o.pts.map(([x, y]) => [x + mv[0], y + mv[1]]);
      else { o.x += mv[0]; o.y += mv[1]; }
      markDirty(); render(); renderProps();
    });
    svg.addEventListener("wheel", (ev) => {
      ev.preventDefault();
      const p = svgPoint(ev);
      zoomBy(ev.deltaY < 0 ? 1.18 : 1 / 1.18, p.x, p.y);
    }, { passive: false });
    svg.addEventListener("click", (ev) => {
      if (A.justMoved) { A.justMoved = false; return; }
      const pill = ev.target.closest(".stpill");
      const node = ev.target.closest(".node");
      if (!node) return;
      const o = itemOf(node.dataset.kind, node.dataset.id);
      if (!o) return;
      if (node.dataset.kind === "equipment" && pill) {
        o.status = ST_ORDER[(ST_ORDER.indexOf(o.status || "running") + 1) % 4];
        toast(`${o.tag}: ${(STATUS[o.status] || {}).en}`);
        markDirty(); render(); renderProps(); return;
      }
      if (node.dataset.kind === "valves") { o.state = o.state === "closed" ? "open" : "closed"; markDirty(); render(); renderProps(); return; }
      if (node.dataset.kind === "equipment" && (A.scene.panels || {}).motor === o.id) { A.motorOpen = true; renderPanels(); }
      // 고르기만 바뀌면 다시 그리지 않는다 — 두 번 누르기(dblclick)는 같은 요소에 두 번 닿아야 한다
      svg.querySelectorAll(".node.sel").forEach((n) => n.classList.remove("sel"));
      node.classList.add("sel");
    });
    svg.addEventListener("dblclick", (ev) => {
      const t = ev.target.closest("[data-edit]");
      const node = ev.target.closest(".node");
      if (!t || !node) return;
      const o = itemOf(node.dataset.kind, node.dataset.id);
      if (!o) return;
      ev.preventDefault();
      openTagEditor(t, o, node.dataset.kind);
    });
  }
  function openTagEditor(textEl, o, kind) {
    const inp = $("#tagedit"), r = textEl.getBoundingClientRect(), st = $("#stage").getBoundingClientRect();
    inp.hidden = false;
    inp.value = o.tag || "";
    inp.style.left = `${r.left - st.left - 10}px`; inp.style.top = `${r.top - st.top - 4}px`; inp.style.width = `${Math.max(90, r.width + 24)}px`;
    inp.focus(); inp.select();
    const done = (commit) => {
      inp.hidden = true; inp.onblur = null; inp.onkeydown = null;
      if (!commit) return;
      const v = inp.value.trim();
      if (!v || v === o.tag) return;
      const old = o.tag;
      retagPanels(old, v);
      o.tag = v;
      if (kind === "instruments") {           // 태그 머리글자가 바뀌면 버블 글자도 (PT-101 → PT)
        const m = /^([A-Z]{1,4})[-_ ]?\d*/i.exec(v);
        if (m) { o.func = m[1].toUpperCase(); o.kind = S.instrumentKind(o.func); }
      }
      markDirty(); render(); renderProps(); toast(`${old} → ${v}`);
    };
    inp.onkeydown = (e) => { if (e.isComposing) return; if (e.key === "Enter") done(true); if (e.key === "Escape") done(false); };
    inp.onblur = () => done(true);
  }
  // ---------------------------------------------------------------- 속성 판 (고른 항목의 태그 · 종류 · 상태 · 크기)
  const PROPS = {
    instruments: [["tag", "태그", "text"], ["func", "글자", "text"], ["kind", "종류", "select", [["field", "현장 전송기"], ["dcs", "DCS 제어기"], ["local", "현지 표시"]]],
                  ["unit", "단위", "text"], ["base", "기준값", "number"], ["hi", "상한 경보", "number"], ["lo", "하한 경보", "number"], ["on", "달린 곳", "text"], ["x", "x", "number"], ["y", "y", "number"]],
    valves: [["tag", "태그", "text"], ["sym", "심볼", "symsel", "valve"], ["state", "상태", "select", [["open", "열림"], ["closed", "닫힘"]]], ["rot", "회전", "number"], ["w", "폭", "number"], ["h", "높이", "number"], ["x", "x", "number"], ["y", "y", "number"]],
    equipment: [["tag", "태그", "text"], ["label", "이름", "text"], ["sym", "심볼", "symsel", "rotating,vessel"], ["status", "상태", "select", Object.entries(STATUS).map(([k, v]) => [k, v.ko])],
                ["w", "폭", "number"], ["h", "높이", "number"], ["x", "x", "number"], ["y", "y", "number"]],
    pipes: [["id", "라인", "text"], ["label", "표기", "text"], ["kind", "종류", "select", Object.entries(LINES).map(([k, v]) => [k, v.ko])], ["dir", "방향", "select", [["1", "정방향"], ["-1", "역방향"]]], ["arrow", "화살", "select", [["true", "있음"], ["false", "없음"]]]]
  };
  function renderProps() {
    const el = $("#props");
    const o = A.sel && itemOf(A.selKind, A.sel);
    if (!o) { el.innerHTML = `<div class="ph">속성</div><p class="muted">심볼이나 배관을 누르면 여기서 태그 · 종류 · 상태 · 크기를 고칩니다.  끌면 옮겨집니다.</p>`; return; }
    const kindKo = { instruments: "계기", valves: "밸브", equipment: "기기", pipes: "배관" }[A.selKind];
    let s = `<div class="ph">${kindKo} · ${esc(o.tag || o.id)}</div>`;
    for (const [k, ko, ty, opt] of PROPS[A.selKind]) {
      const v = o[k] == null ? "" : o[k];
      let inp;
      if (ty === "select") inp = `<select data-k="${k}">${opt.map(([val, lab]) => `<option value="${esc(val)}"${String(v) === String(val) ? " selected" : ""}>${esc(lab)}</option>`).join("")}</select>`;
      else if (ty === "symsel") inp = `<select data-k="${k}">${Object.keys(SYM).filter((n) => opt.split(",").includes(SYM[n].cat)).map((n) => `<option value="${n}"${v === n ? " selected" : ""}>${esc(SYM[n].ko)}</option>`).join("")}</select>`;
      else inp = `<input data-k="${k}" type="${ty}" value="${esc(v)}"${ty === "number" ? ' step="1"' : ""}>`;
      s += `<label class="f"><span>${ko}</span>${inp}</label>`;
    }
    if (o.pid_rect) s += `<div class="pid">P&amp;ID 자리 [${o.pid_rect.map((n) => Math.round(n)).join(", ")}] pt · 행 ${esc(o.key || "")}${o.scope ? " · SCOPE " + esc(o.scope) : ""}${o.qty != null ? " · Q'ty " + esc(o.qty) : ""}</div>`;
    if (o.line) s += `<div class="pid">라인 ${esc(o.line)}${o.line_size ? " · " + esc(o.line_size) : ""}</div>`;
    if (A.selKind === "instruments" && o.pid_rect) s += `<div class="pid">버블 가운데 선 ${o.loc || 0}줄 — ${o.loc === 1 ? "DCS (ISA 위치 표기)" : o.loc === 2 ? "현장 패널" : "현장"}</div>`;
    if (o.body) s += `<div class="pid">몸체 ${esc(o.body)} · 액추에이터 ${esc(o.actuator || "없음")}</div>`;
    if (o.orig_name && o.orig_name !== o.tag) s += `<div class="pid">도면 이름 ${esc(o.orig_name)}</div>`;
    if (o.description) s += `<div class="pid">${esc(o.description)}</div>`;
    if (A.selKind === "pipes" && o.pid_seg) s += `<div class="pid">P&amp;ID 런 [${o.pid_seg.map((n) => Math.round(n)).join(", ")}] · ${esc(o.role || "")}${o.line ? " · 라인 " + esc(o.line) : ""}</div>`;
    if (A.selKind !== "pipes") {
      const st = o.tag && A.lastLogic ? A.lastLogic.get(nrm(o.tag)) : null;
      s += `<div class="pid">LOGIC 연결: ${!A.link ? "LOGIC 창에서 🖥 DCS 그래픽 으로 열면 같은 태그 값이 칠해집니다" : !o.tag ? "태그가 없어 이을 수 없습니다 — 두 번 눌러 태그를 적으세요" : st ? "이어짐" : "이 태그 값이 아직 오지 않았습니다"}</div>`;
      if (st) s += `<div class="live">LOGIC 값 ${esc(JSON.stringify(st))}</div>`;
    }
    if (A.selKind === "instruments" && o.tag) s += `<div class="row2"><button class="btn" id="props-trend">Trend 로</button><button class="btn" id="props-key">${((A.scene.panels || {}).key || []).includes(o.tag) ? "Key Parameters 에서 빼기" : "Key Parameters 에 넣기"}</button></div>`;
    s += `<button class="btn del" id="props-del">이 항목 지우기</button>`;
    el.innerHTML = s;
    el.querySelectorAll("[data-k]").forEach((inp) => inp.addEventListener("change", () => {
      const k = inp.dataset.k;
      let v = inp.value;
      if (inp.type === "number") { v = v === "" ? null : Number(v); if (v == null && ["x", "y", "w", "h", "rot"].includes(k)) return; }
      if (k === "arrow") v = v === "true";
      if (k === "dir") v = Number(v);
      if (k === "base") { o.base = v; o.value = v; }
      else if (k === "id" && A.selKind === "pipes") { const old = o.id; o.id = v; (A.scene.instruments || []).forEach((i) => { if (i.on === old) i.on = v; }); A.sel = v; }
      else if (k === "func") { o.func = String(v).toUpperCase(); o.kind = S.instrumentKind(o.func); }
      else if (k === "tag") { retagPanels(o.tag, v); o.tag = v; }
      else o[k] = v;
      markDirty(); render(); renderProps();
    }));
    $("#props-del").addEventListener("click", removeSelected);
    const tb = $("#props-trend");
    if (tb) tb.addEventListener("click", () => { A.scene.panels = A.scene.panels || {}; A.scene.panels.trend = { tag: o.tag }; markDirty(); renderPanels(); });
    const kb = $("#props-key");
    if (kb) kb.addEventListener("click", () => {
      const P = (A.scene.panels = A.scene.panels || {});
      const K = P.key && P.key.length ? P.key : (A.scene.instruments || []).slice(0, 6).map((i) => i.tag);
      P.key = K.includes(o.tag) ? K.filter((t) => t !== o.tag) : [...K, o.tag];
      markDirty(); renderPanels(); renderProps();
    });
  }
  function retagPanels(old, v) {
    for (const k of ["trend", "control"]) { const P = (A.scene.panels || {})[k]; if (P && P.tag === old) P.tag = v; }
    const K = (A.scene.panels || {}).key; if (K) K.forEach((t, i) => { if (t === old) K[i] = v; });
  }
  function removeSelected() {
    const o = A.sel && itemOf(A.selKind, A.sel);
    if (!o) return;
    A.scene[A.selKind] = A.scene[A.selKind].filter((x) => x !== o);
    toast(`${o.tag || o.id} 지움 — 저장 전이면 '식별 결과로 다시' 로 되돌릴 수 있습니다`);
    A.sel = null; A.selKind = null; markDirty(); render(); renderProps();
  }
  function addItem(kind) {
    const [W, H] = A.scene.size || [1400, 800];
    const n = (A.scene[kind] = A.scene[kind] || []).length + 1;
    let o;
    if (kind === "instruments") o = { id: `NEW-I${n}`, func: "PT", tag: `PT-NEW${n}`, x: W / 2, y: H / 2, value: 0, base: 0, unit: "", kind: "field", on: "", logic: null };
    else if (kind === "valves") o = { id: `NEW-V${n}`, sym: "valve_manual", tag: `XV-NEW${n}`, x: W / 2 - 20, y: H / 2 - 20, w: 40, h: 40, rot: 0, state: "open", logic: null };
    else if (kind === "equipment") o = { id: `NEW-E${n}`, sym: "pump", tag: `EQ-NEW${n}`, label: "", x: W / 2 - 50, y: H / 2 - 50, w: 100, h: 100, status: "running" };
    else o = { id: `L-NEW${n}`, kind: "process", label: "", pts: [[W / 2 - 120, H / 2 + 60], [W / 2 + 120, H / 2 + 60]], arrow: true };
    A.scene[kind].push(o);
    A.sel = o.id; A.selKind = kind;
    markDirty(); render(); renderProps();
  }
  function markDirty() { A.dirty = true; if (A.src !== "example") $("#save").disabled = false; }
  function stageMsg(t, err) { const m = $("#stage-msg"); m.hidden = !t; m.textContent = t || ""; m.classList.toggle("err", !!err); }
  function setEditing(on) {
    A.editing = on;
    document.body.classList.toggle("editing", on);
    $("#edit").classList.toggle("on", on);
    $("#edit").textContent = on ? "✎ 옮기기" : "🔒 잠금";
  }
  function toast(msg, ms) {
    const t = $("#toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(t._t); t._t = setTimeout(() => { t.hidden = true; }, ms || 2200);
  }

  // ---------------------------------------------------------------- 출처 · 저장
  async function getJSON(u, opt) {
    const r = await fetch(u, Object.assign({ cache: "no-store" }, opt || {}));
    if (!r.ok) {
      const t = await r.text();
      let m = t;
      try { const j = JSON.parse(t); m = j.error || j.detail || t; } catch (e) { /* 글 그대로 */ }
      throw new Error(m || ("서버 응답 " + r.status));
    }
    return r.json();
  }
  async function loadSources() {
    try {
      const jobs = await getJSON("/dcs/api/sources");
      const sel = $("#src");
      for (const j of jobs) {
        const o = document.createElement("option");
        o.value = j.job_id; o.textContent = `${j.project || "(프로젝트 없음)"} · ${j.revision ? (/^rev/i.test(j.revision) ? j.revision : "Rev." + j.revision) + " · " : ""}${j.pdf_name} · 태그 ${j.tagged_rows}행`;
        sel.appendChild(o);
      }
    } catch (e) { /* DB 없는 환경 · 절전모드 — 예시만 */ }
  }
  async function chooseSource(v, page) {
    A.src = v;
    const pg = $("#page");
    $("#dl-zip").hidden = v === "example";
    if (v === "example") {
      pg.hidden = true; A.job = null; A.page = null; A.motorOpen = true;
      await loadScene();
      return;
    }
    A.job = v;
    if (![...$("#src").options].some((o) => o.value === v)) { const o = document.createElement("option"); o.value = v; o.textContent = `분석 ${v}`; $("#src").appendChild(o); }
    $("#src").value = v;
    $("#dl-zip").href = `/dcs/api/jobs/${v}/export.zip`;
    const job = await getJSON(`/dcs/api/jobs/${v}`);
    if (!job.eligible) { pg.hidden = true; A.scene = null; $("#svg").innerHTML = ""; stageMsg(job.reason || "이 분석으로는 그래픽을 만들 수 없습니다", true); return; }
    A.sheets = job.sheets || [];
    if (!A.sheets.length) { pg.hidden = true; stageMsg("식별된 행이 있는 장이 없습니다", true); return; }
    pg.innerHTML = A.sheets.map((p) => `<option value="${p.page_no}">p${p.page_no} · ${esc(p.drawing_no || "")} · 계기 ${p.instruments} · 밸브 ${p.valves}${p.saved ? " · 저장본" : ""}</option>`).join("");
    pg.hidden = false;
    A.page = Number(page) && A.sheets.some((p) => p.page_no === Number(page)) ? Number(page) : A.sheets[0].page_no;
    pg.value = String(A.page);
    try { A.tags = (await getJSON(`/dcs/api/jobs/${v}/tags`)).tags || []; } catch (e) { A.tags = []; }
    await loadScene();
    logicReady();
  }
  async function loadScene(fresh) {
    A.trend = {}; A.sel = null; A.selKind = null; A.dirty = false; A.vb = null; A.fitAll = false;
    stageMsg("");
    let sc;
    try {
      sc = A.src === "example" ? await getJSON("/dcs/api/example") : await getJSON(`/dcs/api/jobs/${A.job}/scene/${A.page}${fresh ? "?fresh=1" : ""}`);
    } catch (e) { A.scene = null; $("#svg").innerHTML = ""; stageMsg("장면을 읽지 못했습니다 — " + e.message, true); return; }
    A.scene = sc;
    A.motorOpen = A.src === "example";
    for (const i of sc.instruments || []) i.base = Number(i.value) || 0;
    $("#save").disabled = true;
    $("#reset").disabled = A.src === "example" || !sc.saved;
    const who = sc.saved ? `저장본 · ${sc.saved_by || ""} ${sc.saved_at || ""}` : sc.generated ? `식별 결과에서 만든 초안 — 계기 ${sc.counts ? sc.counts.instruments : 0}(태그 ${sc.counts ? sc.counts.tagged : 0}) · 밸브 ${sc.counts ? sc.counts.valves : 0} · 기기 ${sc.counts ? sc.counts.equipment : 0} · 배관 ${sc.counts ? sc.counts.pipes : 0}` : "예시 장면";
    $("#who").textContent = who;
    render(); renderProps();
    fitView();
    if (A.lastStates) applyLogic(A.lastStates, A.lastMeta, true);
  }
  function author() {
    const u = Q.get("user");
    if (u) return u;
    let a = "";
    try { a = localStorage.getItem("pid.author") || ""; } catch (e) { /* 저장소 막힘 */ }
    return a;
  }
  async function saveScene() {
    if (A.src === "example") return;
    let a = author();
    if (!a) {
      a = await askName();
      if (!a) { toast("작성자 이름이 있어야 저장됩니다"); return; }
      try { localStorage.setItem("pid.author", a); } catch (e) { /* */ }
    }
    const sc = JSON.parse(JSON.stringify(A.scene));
    for (const i of sc.instruments || []) { i.value = i.base != null ? i.base : i.value; delete i.base; delete i.live; delete i.dig; delete i.alarmLive; }
    sc.panels = sc.panels || {};
    if (sc.panels.control) sc.panels.control.mode = A.ctlMode;
    sc.panels.trend = Object.assign(sc.panels.trend || {}, { tag: $("#trend-tag").value });
    try {
      const r = await getJSON(`/dcs/api/jobs/${A.job}/scene/${A.page}`, { method: "POST", headers: { "Content-Type": "application/json", "X-Author": encodeURIComponent(a) }, body: JSON.stringify({ scene: sc, author: a }) });
      A.dirty = false; $("#save").disabled = true; $("#reset").disabled = false;
      $("#who").textContent = r.offline ? `절전모드 — 보관했습니다 · 서버가 켜지면 저장됩니다 (${a})` : `저장본 · ${r.saved_by} ${r.saved_at}`;
      toast("저장했습니다 — 다음에 열면 이 모양으로 뜹니다");
    } catch (e) { toast("저장 실패: " + e.message, 4000); }
  }
  function askName() {
    return new Promise((res) => {
      const inp = $("#tagedit");
      inp.hidden = false; inp.value = ""; inp.placeholder = "작성자 이름 · Enter";
      inp.style.left = "12px"; inp.style.top = "12px"; inp.style.width = "180px"; inp.focus();
      const done = (ok) => { inp.hidden = true; inp.placeholder = ""; inp.onkeydown = null; inp.onblur = null; res(ok ? inp.value.trim() : ""); };
      inp.onkeydown = (e) => { if (e.isComposing) return; if (e.key === "Enter") done(true); if (e.key === "Escape") done(false); };
      inp.onblur = () => done(true);
    });
  }

  // ---------------------------------------------------------------- 시작
  function bind() {
    document.querySelectorAll("#tabs .tab").forEach((b) => b.addEventListener("click", () => {
      document.querySelectorAll("#tabs .tab").forEach((x) => x.classList.toggle("on", x === b));
      $("#view-overview").hidden = b.dataset.tab !== "overview";
      $("#view-library").hidden = b.dataset.tab !== "library";
    }));
    $("#src").addEventListener("change", (e) => chooseSource(e.target.value).catch((er) => toast(er.message, 4000)));
    $("#page").addEventListener("change", (e) => { A.page = Number(e.target.value); loadScene().catch((er) => toast(er.message, 4000)); });
    $("#fit").addEventListener("click", () => { if (!A.scene) return; A.fitAll = !A.fitAll; fitView(A.fitAll); });
    $("#zin").addEventListener("click", () => A.scene && zoomBy(1.25));
    $("#zout").addEventListener("click", () => A.scene && zoomBy(1 / 1.25));
    $("#dl-svg").addEventListener("click", () => exportSvg());
    $("#dl-png").addEventListener("click", () => exportPng());
    $("#edit").addEventListener("click", () => setEditing(!A.editing));
    document.querySelectorAll(".btn.add").forEach((b) => b.addEventListener("click", () => addItem(b.dataset.add)));
    $("#save").addEventListener("click", saveScene);
    $("#reset").addEventListener("click", async () => {
      if (A.src === "example") return;
      await fetch(`/dcs/api/jobs/${A.job}/scene/${A.page}`, { method: "DELETE" });
      await loadScene(true); toast("식별 결과에서 다시 만들었습니다");
    });
    $("#sim").addEventListener("click", () => setSim(!A.sim));
    $("#flow").addEventListener("change", (e) => document.body.classList.toggle("noflow", !e.target.checked));
    $("#showval").addEventListener("change", (e) => document.body.classList.toggle("noval", !e.target.checked));
    $("#trend-tag").addEventListener("change", renderTrend);
    $("#motor-x").addEventListener("click", () => { A.motorOpen = false; $("#motor-panel").hidden = true; });
    document.querySelectorAll("#modes .mode").forEach((b) => b.addEventListener("click", () => { A.ctlMode = b.dataset.mode; if ((A.scene.panels || {}).control) A.scene.panels.control.mode = A.ctlMode; markDirty(); renderPanels(); }));
    setInterval(() => { const d = new Date(); $("#clock").textContent = d.toISOString().slice(0, 10) + "  " + d.toTimeString().slice(0, 8); }, 1000);
    bindStage();
  }
  async function start() {
    bind();
    window.addEventListener("message", onMessage);
    await loadSources();
    const job = Q.get("job"), page = Q.get("page");
    if (job && Q.get("demo") !== "1" && !location.pathname.endsWith("/demo")) await chooseSource(job, page);
    else await chooseSource("example");
    setSim(true);
    setEditing(!A.link);          // LOGIC 창이 연 그래픽은 보기부터 (끌다가 값을 놓치지 않게) — ✎ 로 켠다
  }

  // ---------------------------------------------------------------- hotfix110 — LOGIC 창과 태그로 연동 (logic.js openDcsWindow · dcsStates · dcsGo 와 같은 계약)
  function logicWin() {
    if (window.opener && !window.opener.closed) { try { if (window.opener.location.origin === location.origin) return window.opener; } catch (e) { /* 다른 출처 */ } }
    return null;
  }
  function logicReady() {
    const w = logicWin();
    if (!w || !A.logicJob || !A.job) return;
    w.postMessage({ kind: "dcs-ready", job: A.job, link: A.link, tags: (A.tags || []).map((t) => ({ tag: t.tag, kind: t.kind, page_no: t.page_no, drawing_no: t.drawing_no })) }, location.origin);
    const li = $("#linkinfo");
    li.classList.add("on"); li.textContent = "LOGIC 창과 연동 — 시뮬레이션 값이 같은 태그에 칠해집니다";
  }
  function logicGo(o) {
    if (!o || !o.tag || !A.logicJob) return;
    const w = logicWin();
    if (w) w.postMessage({ kind: "dcs-go", tag: o.tag, link: A.link }, location.origin);
  }
  function onMessage(e) {
    if (e.origin !== location.origin || !e.data || e.data.kind !== "dcs-states") return;
    if (A.link && e.data.link && e.data.link !== A.link) return;
    applyLogic(e.data.states || {}, e.data.logic || null);
  }
  /** 받은 { 태그: {v, u, s, open, alarm, state} } 중 이 장면에 있는 태그만 칠한다.  맞는 태그가 이 장에 하나도 없고 다른 장에 있으면
   *  그 장으로 옮긴다 (태그 → 장 표 `/dcs/api/jobs/{job}/tags`).  데모 값은 그 태그에서 멈춘다 (i.live). */
  function applyLogic(st, meta, again) {
    A.lastStates = st; A.lastMeta = meta;
    if (!A.scene) return;
    const items = [];
    for (const k of ["instruments", "valves", "equipment"]) for (const o of A.scene[k] || []) if (o.tag) items.push([k, o]);
    const idx = new Map(items.map(([k, o]) => [nrm(o.tag), [k, o]]));
    const keys = Object.keys(st);
    const here = keys.filter((t) => idx.has(nrm(t)));
    if (!again && !here.length && A.job && (A.tags || []).length && keys.length) {
      const want = new Set(keys.map(nrm)), cnt = {};
      for (const t of A.tags) if (want.has(nrm(t.tag))) cnt[t.page_no] = (cnt[t.page_no] || 0) + 1;
      const best = Object.entries(cnt).sort((a, b) => b[1] - a[1])[0];
      if (best && Number(best[0]) !== A.page) {
        A.page = Number(best[0]); $("#page").value = String(A.page);
        if (A.dirty) toast("LOGIC 값이 다른 장의 태그라 그 장으로 옮겼습니다 — 저장하지 않은 편집은 버려졌습니다", 4000);
        loadScene();
        return;
      }
    }
    // 지난번 칠한 것을 걷고 다시 칠한다
    for (const [, o] of items) { if (o.live) { o.live = false; o.dig = null; o.value = o.base; } o.alarmLive = false; }
    A.lastLogic = new Map();
    for (const t of here) {
      const [k, o] = idx.get(nrm(t)), v = st[t] || {};
      A.lastLogic.set(nrm(o.tag), v);
      if (k === "instruments") {
        o.live = true;
        if (typeof v.v === "number") { o.value = v.v; if (v.u) o.unit = v.u; o.dig = null; } else { o.value = null; o.dig = v.s != null ? v.s : null; }
        o.alarmLive = !!v.alarm;
      } else if (k === "valves") {
        if (v.open !== undefined) o.state = v.open ? "open" : "closed";
      } else if (k === "equipment") {
        const m = { run: "running", standby: "standby", trip: "trip", stop: "stopped", oos: "oos" };
        if (v.alarm) o.status = "trip"; else if (v.state && m[v.state]) o.status = m[v.state];
      }
    }
    render(); renderProps();
    const li = $("#linkinfo");
    li.classList.add("on");
    li.textContent = meta ? `LOGIC ${meta.sheet || ""} 시뮬레이션 — 이 장의 태그 ${here.length}개 칠함${keys.length - here.length ? ` · 이 장에 없는 태그 ${keys.length - here.length}개` : ""}${meta.mode && meta.mode !== "sim" ? " (LOGIC 이 시뮬레이션 모드가 아닙니다)" : ""}`
                         : `다른 창이 보낸 값 — 태그 ${here.length}개 칠함`;
  }

  // ---------------------------------------------------------------- 내려받기 (브라우저에서 — 서버가 꺼져도)
  function svgForExport(all) {
    const svg = $("#svg").cloneNode(true), [W, H] = A.scene.size || [1400, 800];
    const vb = all ? [0, 0, W, H] : A.vb;
    svg.setAttribute("viewBox", vb.map(px).join(" "));
    svg.setAttribute("width", Math.round(vb[2])); svg.setAttribute("height", Math.round(vb[3]));
    const css = [...document.styleSheets].map((ss) => { try { return [...ss.cssRules].map((r) => r.cssText).join("\n"); } catch (e) { return ""; } }).join("\n");
    svg.insertAdjacentHTML("afterbegin", `<style>${css}</style><rect x="${vb[0]}" y="${vb[1]}" width="${vb[2]}" height="${vb[3]}" fill="#0b1a2b"/>`);
    return [new XMLSerializer().serializeToString(svg), vb];
  }
  function fname() { return (A.src === "example" ? "compressor_train_example" : (A.scene && (A.scene.drawing_no || A.scene.title)) || ("p" + A.page)).replace(/[^A-Za-z0-9_-]+/g, "_"); }
  function dl(name, blob) { const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); }
  function exportSvg() { if (!A.scene) return; dl(fname() + ".svg", new Blob([svgForExport(true)[0]], { type: "image/svg+xml" })); }
  function exportPng() {
    if (!A.scene) return;
    const [txt, vb] = svgForExport(true), k = Math.min(2, 5000 / vb[2]);
    const img = new Image();
    img.onerror = () => toast("PNG 를 만들지 못했습니다 — SVG 로 받으세요", 4000);
    img.onload = () => { const c = document.createElement("canvas"); c.width = vb[2] * k; c.height = vb[3] * k; const x = c.getContext("2d"); x.fillStyle = "#0b1a2b"; x.fillRect(0, 0, c.width, c.height); x.drawImage(img, 0, 0, c.width, c.height); c.toBlob((b) => dl(fname() + ".png", b), "image/png"); };
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(txt);
  }
  /* hotfix108 — 절전모드: [절전 대비 보관] 이 담을 자료 (장면 · 장 목록 · 태그) */
  if (window.OFFLINE) window.OFFLINE.prefetchUrls = async () => {
    const u = ["/dcs/api/example", "/dcs/api/sources"];
    if (!A.job) return u;
    u.push(`/dcs/api/jobs/${A.job}`, `/dcs/api/jobs/${A.job}/tags`);
    for (const p of A.sheets || []) u.push(`/dcs/api/jobs/${A.job}/scene/${p.page_no}`);
    return u;
  };
  window.HMI = { A, render, tick, loadScene, chooseSource, applyLogic, fitView, zoomBy, setVB };
  start().catch((e) => toast("열지 못했습니다: " + e.message, 5000));
})();
