/* LOGIC 검토 화면 — 도면 위에 읽은 선 · 블록을 얹고, 선을 따라가거나 강제 신호로 로직을 돌린다.
   판정은 서버(app/logic)가 한다.  이 파일은 그리고 · 누르고 · 움직일 뿐이다. */
"use strict";

const $ = (s) => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const L = {
  job: null, sheets: [], sheet: null, page: null, zoom: 1, mode: "trace",
  forces: {}, state: null, frames: null, values: {}, anim: [], sel: null, busy: false,
  // 묶음 전체 (L4): 장마다 사람이 준 값 · 장마다 상태 · 다른 장에서 연결로 들어온 입력 · 활성 연결 장 목록
  allForces: {}, states: {}, linked: {}, chain: [],
  focus: null, back: [], afterFit: null,          // FROM/TO 로 간 행 · 돌아갈 자리 (L6)
  all: null, allCode: "", allSel: null,            // 묶음 전체 점검 목록 (L7)
};
const SPEED = 900;          // 선 위를 신호가 흐르는 속도 (pt/초)
const STEP_MS = 260;        // 블록 하나를 지날 때마다 기다림
const TIMER_MS = 1100;      // 타이머 경과를 보이는 시간

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
async function api(url, opt) {
  const r = await fetch(url, opt);
  if (!r.ok) {
    let m = r.statusText;
    try { m = (await r.json()).detail || m; } catch (e) { /* 글 아닌 응답 */ }
    throw new Error(m);
  }
  return r.status === 204 ? null : r.json();
}
const post = (url, body) => api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs || {}) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function status(t) { $("#status").textContent = t || ""; }

const FUNC_KO = {
  AND: "AND 게이트", NAND: "NAND 게이트", OR: "OR 게이트", NOR: "NOR 게이트", NOT: "NOT (반전)",
  MEMORY: "메모리", GT: "지연 ON 타이머 (GT)", DT: "지연 OFF 타이머 (DT)", PD: "펄스 타이머 (PD)",
  PB: "누름단추", STEP: "STEP (시퀀스 단계)", CONNECTOR: "연결 기호", LIGHT: "램프", ANN: "경보 (ANN)",
  SOE: "이벤트 기록 (SOE)", SIGNAL: "신호 이름 상자 (입력)", UNKNOWN: "판정 못 함",
};

/* ------------------------------------------------------------------ 묶음 · 시트 */

async function loadJobs(select) {
  const j = await api("/logic/api/jobs");
  const sel = $("#job");
  sel.innerHTML = "";
  if (!j.jobs.length) sel.innerHTML = `<option value="">— 분석한 묶음 없음 —</option>`;
  for (const x of j.jobs) {
    const st = x.state === "done" ? `${x.sheets}장` : x.state === "failed" ? "실패" : "분석 중";
    sel.insertAdjacentHTML("beforeend", `<option value="${x.id}">${esc(x.name)} · ${st}</option>`);
  }
  $("#samples").innerHTML = j.samples.map((n) => `<button data-sample="${esc(n)}" title="data/logic 의 샘플을 분석합니다">샘플: ${esc(n.replace(/\.pdf$/i, ""))}</button>`).join(" ");
  const want = select || (location.hash.match(/job=([0-9a-f]{12})/) || [])[1] || (j.jobs[0] && j.jobs[0].id);
  if (want) { sel.value = want; await openJob(want); }
}

async function openJob(id) {
  L.job = id;
  const st = await api(`/logic/api/jobs/${id}`);
  if (st.state !== "done") {
    if (st.state === "failed") { status(`분석 실패 — ${st.error || ""}`); return; }
    const pct = st.total ? Math.round((100 * st.done) / st.total) : 0;
    status(`분석 중… ${stageKo(st.stage)} ${pct}%`);
    setTimeout(() => L.job === id && openJob(id), 1200);
    return;
  }
  status(`분석 ${st.seconds}초 · ${st.sheets}장`);
  const j = await api(`/logic/api/jobs/${id}/sheets`);
  L.sheets = j.sheets;
  $("#basis").innerHTML = `${esc(j.note)}<br><br>배운 글자: ${Object.keys(j.dictionary).map(esc).join(" ")}`;
  renderSheetList();
  $("#goto").disabled = false;
  const rep = $("#report"); rep.hidden = false; rep.href = `/logic/api/jobs/${id}/report.xlsx`;
  L.all = null; L.allSel = null;
  api(`/logic/api/jobs/${id}/findings`).then((f) => { if (L.job === id) { L.all = f; renderAll(); } }).catch(() => {});
  const p = Number((location.hash.match(/page=(\d+)/) || [])[1]) || (L.sheets[0] && L.sheets[0].page);
  if (p) openSheet(p);
}
/* 묶음 전체 점검 (L7) — 서버가 편 목록을 종류로 걸러 보인다.  누르면 그 시트 · 그 자리로. */
function renderAll() {
  const f = L.all;
  if (!f) { $("#all-count").textContent = ""; return; }
  $("#all-count").textContent = f.total ? `${f.total}건` : "이상 없음";
  const sel = $("#all-code");
  const cur = L.allCode;
  sel.innerHTML = `<option value="">전부 (${f.total})</option>` + f.codes.map((c) => `<option value="${esc(c.code)}">${esc(c.label)} (${c.n})</option>`).join("");
  sel.value = f.codes.some((c) => c.code === cur) ? cur : "";
  L.allCode = sel.value;
  const items = f.items.map((x, i) => ({ ...x, i })).filter((x) => !L.allCode || x.code === L.allCode);
  $("#all-findings").innerHTML = items.map((x) => `<li data-i="${x.i}" class="${x.code === "FT_DESC_DIFF" ? "ok" : ""}${L.allSel === x.i ? " sel" : ""}"><span class="sh">${esc(x.sheet_no || "p" + x.page)}</span>${esc(x.text)}</li>`).join("");
}
function gotoFinding(i) {
  const x = L.all && L.all.items[i];
  if (!x) return;
  L.allSel = i; renderAll();
  const after = () => {
    if (x.row) { L.focus = { page: x.page, row: x.row, side: x.side || "L", at: Date.now() }; drawOverlay(); focusRow(); return; }
    const s = L.sheet;
    const at = x.at || (x.block && s.blocks[x.block] && s.blocks[x.block].bbox.slice(0, 2));
    if (x.block) { L.sel = { block: x.block }; paint(); renderInfo(); }
    if (at) { const st = $("#stage"); setZoom(Math.max(L.zoom, 1.6)); st.scrollLeft = at[0] * L.zoom - st.clientWidth / 2; st.scrollTop = at[1] * L.zoom - st.clientHeight / 2; }
  };
  if (x.page === L.page) after();
  else { L.focus = null; L.afterFit = after; openSheet(x.page); }
}
/* 이동 칸 — `G049-40` 꼴을 읽어 그 시트의 그 행으로 (출력 행 먼저 · 없으면 입력 행) */
function gotoTyped(text) {
  const m = String(text || "").toUpperCase().replace(/\s+/g, "").match(/^([A-Z]\d{3}[A-Z]?)(?:-(\d{1,3}))?$/);
  if (!m) { status("시트-행 꼴이 아닙니다 (예: G049-40)"); return; }
  const t = sheetByNo(m[1]);
  if (!t) { status(`${m[1]} 시트는 이 묶음에 없습니다`); return; }
  if (!m[2]) { L.focus = null; openSheet(t.page); return; }
  goToRef(m[1], Number(m[2]), "R");
}
function stageKo(s) { return { reading: "선 읽는 중", glyphs: "글자 배우는 중", blocks: "블록 판정 중" }[s] || ""; }

function renderSheetList() {
  const q = $("#sheet-filter").value.trim().toUpperCase();
  const ul = $("#sheet-list");
  ul.innerHTML = "";
  const list = L.sheets.filter((s) => !q || (s.sheet_no + " " + s.title).toUpperCase().includes(q));
  $("#sheet-count").textContent = `${L.sheets.length}장`;
  for (const s of list) {
    const li = document.createElement("li");
    li.dataset.page = s.page;
    if (s.page === L.page) li.className = "sel";
    const ch = L.mode === "sim" && L.chain.find((c) => c.page === s.page && c.hop != null);
    if (ch) li.classList.add("chain");
    li.innerHTML = `<span class="no">${esc(s.sheet_no || "p" + s.page)}</span><span class="t">${esc(s.title)}</span>
      <span class="meta">${ch ? `<i class="chain-dot"></i>${ch.hop === 0 ? "지정한 장" : `연결 ${ch.hop}단계`} · ` : ""}블록 ${s.blocks} · 선 ${s.nets}${s.mismatch ? ` · <b>from-to 불일치 ${s.mismatch}</b>` : ""}${s.descdiff ? ` · <i class="dd">설명 다름 ${s.descdiff}</i>` : ""}${s.findings ? ` · <b>점검 ${s.findings}</b>` : ""}</span>`;
    li.onclick = () => { L.focus = null; openSheet(s.page); };
    ul.appendChild(li);
  }
}

async function openSheet(page) {
  L.page = page;
  location.hash = `job=${L.job}&page=${page}`;
  renderSheetList();
  const s = await api(`/logic/api/jobs/${L.job}/sheet/${page}`);
  L.sheet = s;
  L.forces = L.allForces[page] = L.allForces[page] || {};
  L.state = L.states[page] || null; L.values = {}; L.sel = null; stopAnim();
  L.linked = {};
  $("#empty").hidden = true;
  const img = $("#page");
  img.src = `/logic/api/jobs/${L.job}/page/${page}.png`;
  $("#canvas").style.width = s.size[0] + "px";
  $("#canvas").style.height = s.size[1] + "px";
  $("#ov").setAttribute("viewBox", `0 0 ${s.size[0]} ${s.size[1]}`);
  $("#sheet-head").textContent = `${s.sheet_no} · ${s.title}`;
  drawOverlay();
  renderRows(); renderFindings(); renderInfo(); renderHelp();
  img.onload = () => fit();
  if (img.complete) fit();
  if (L.mode === "sim") runSim();
}

/* ------------------------------------------------------------------ 확대 · 이동 */

function fit() {
  if (!L.sheet) return;
  const st = $("#stage");
  const lg = L.sheet.logic;
  // 표 양쪽(FM · NO. · 설명 · KKS / KKS · 설명 · NO. · TO)까지 보이게 — from-to 는 FM 칸으로 맞추므로 그 칸이 보여야 한다
  const [x0, x1] = tableX();
  const w = x1 - x0 + 20, h = lg[3] - lg[1] + 40;
  L.zoom = Math.min(st.clientWidth / w, st.clientHeight / h);
  setZoom(L.zoom, null, [x0 - 10, lg[1] - 20]);
  if (L.focus && L.focus.page === L.sheet.page) focusRow();
  else if (L.afterFit) { const f = L.afterFit; L.afterFit = null; f(); }
}
function tableX() {
  const s = L.sheet, fr = s.frame, W = (s.size && s.size[0]) || s.logic[2] + 200;
  return fr ? [fr[0], fr[2]] : [0, W];
}
function setZoom(z, at, origin) {
  const st = $("#stage");
  const c = $("#canvas");
  const old = L.zoom;
  let px, py;
  if (at) { px = (st.scrollLeft + at[0]) / old; py = (st.scrollTop + at[1]) / old; }
  L.zoom = Math.max(0.3, Math.min(8, z));
  c.style.transform = `scale(${L.zoom})`;
  c.style.width = L.sheet.size[0] + "px";
  c.style.height = L.sheet.size[1] + "px";
  // 스크롤 영역을 확대 크기에 맞춘다
  c.style.marginRight = (L.sheet.size[0] * (L.zoom - 1)) + "px";
  c.style.marginBottom = (L.sheet.size[1] * (L.zoom - 1)) + "px";
  if (origin) { st.scrollLeft = origin[0] * L.zoom; st.scrollTop = origin[1] * L.zoom; }
  else if (at) { st.scrollLeft = px * L.zoom - at[0]; st.scrollTop = py * L.zoom - at[1]; }
}
function initPan() {
  const st = $("#stage");
  let drag = null;
  st.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    drag = { x: e.clientX, y: e.clientY, sl: st.scrollLeft, st: st.scrollTop, moved: false };
  });
  window.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; st.classList.add("drag"); }
    if (drag.moved) { st.scrollLeft = drag.sl - dx; st.scrollTop = drag.st - dy; }
  });
  window.addEventListener("pointerup", () => { if (drag && drag.moved) L.justPanned = true; drag = null; st.classList.remove("drag"); setTimeout(() => (L.justPanned = false), 0); });
  st.addEventListener("wheel", (e) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const r = st.getBoundingClientRect();
    setZoom(L.zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15), [e.clientX - r.left, e.clientY - r.top]);
  }, { passive: false });
}

/* ------------------------------------------------------------------ 도면 위 그림 */

function drawOverlay() {
  const s = L.sheet;
  const ov = $("#ov");
  ov.innerHTML = "";
  const gB = el("g", { id: "g-blocks" }, ov);
  const gN = el("g", { id: "g-nets" }, ov);
  const gR = el("g", { id: "g-rows" }, ov);
  const gF = el("g", { id: "g-find" }, ov);
  for (const [nid, segs] of Object.entries(s.order)) {
    const g = el("g", { class: "net", "data-net": nid }, gN);
    for (const [x0, y0, x1, y1, d0] of segs) {
      el("line", { x1: x0, y1: y0, x2: x1, y2: y1, class: "vis" }, g);
    }
    for (const [x0, y0, x1, y1, d0] of segs) {
      const L_ = Math.hypot(x1 - x0, y1 - y0) || 0.01;
      el("line", { x1: x0, y1: y0, x2: x1, y2: y1, class: "fx", "data-d0": d0, "data-len": L_,
        "stroke-dasharray": `${L_} ${L_}`, "stroke-dashoffset": L_ }, g);
    }
    for (const [x0, y0, x1, y1] of segs) el("line", { x1: x0, y1: y0, x2: x1, y2: y1, class: "hit" }, g);
    if (s.nets[nid] && s.nets[nid].dashed) g.classList.add("dashed");
    g.addEventListener("click", (e) => { if (L.justPanned) return; e.stopPropagation(); onNet(nid, e); });
  }
  for (const [bid, b] of Object.entries(s.blocks)) {
    const [x0, y0, x1, y1] = b.bbox;
    const cls = "blk" + (b.func === "UNKNOWN" ? " unknown" : "");
    const r = b.kind === "RECT"
      ? el("rect", { x: x0 - 0.6, y: y0 - 0.6, width: x1 - x0 + 1.2, height: y1 - y0 + 1.2, class: cls, "data-block": bid }, gB)
      : el("circle", { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, r: (x1 - x0) / 2 + 0.8, class: cls, "data-block": bid }, gB);
    r.addEventListener("click", (e) => { if (L.justPanned) return; e.stopPropagation(); onBlock(bid, e); });
    if (b.func !== "CONNECTOR") {
      const t = badgeText(b);
      const w = t.length * 2.55 + 2.4;
      el("rect", { x: x0, y: y0 - 5.6, width: w, height: 5, rx: 1, class: "badge-bg" + (b.func === "UNKNOWN" ? " unknown" : "") }, gB);
      const tx = el("text", { x: x0 + 1.2, y: y0 - 1.9, class: "badge" }, gB);
      tx.textContent = t;
    }
  }
  for (const r of s.rows) {
    const c = el("circle", { cx: r.at[0], cy: r.at[1], r: 2.4, class: "rowpin", "data-row": r.n }, gR);
    c.addEventListener("click", (e) => { if (L.justPanned) return; e.stopPropagation(); onRow(r.n, e); });
    const t = el("title", {}, c); t.textContent = `${r.n}행 · ${r.desc || ""}` + (r.ft && r.ft.ok === false ? `\n✕ from-to 일치하지 않습니다 — ${r.ft.why.join(" · ")}` : r.ft && r.ft.warn && r.ft.warn.length ? `\n⚠ 연결은 맞고 설명만 다릅니다 — ${r.ft.warn.join(" · ")}` : "");
    const ftWarn = r.ft && r.ft.ok !== false && r.ft.warn && r.ft.warn.length;
    if (ftWarn) {
      c.classList.add("ftwarn");
      if (r.y0 != null && r.y1 != null) {
        const lg = s.logic, [fx0, fx1] = tableX();
        const x0 = r.side === "L" ? fx0 : lg[2], x1 = r.side === "L" ? lg[0] : fx1;
        const bx = el("rect", { x: x0, y: r.y0, width: x1 - x0, height: r.y1 - r.y0, class: "ft-row warn" }, gR);
        gR.insertBefore(bx, gR.firstChild);
        el("title", {}, bx).textContent = `${r.n}행 — 연결(FM ${r.fm})은 맞고 설명만 다릅니다: ${r.ft.warn.join(" · ")}`;
      }
    }
    if (r.ft && r.ft.ok === false) {
      // from-to 가 맞지 않는 행 — 붉게 (사용자 지시 L5)
      c.classList.add("ftbad");
      if (r.y0 != null && r.y1 != null) {
        // 그 행의 표 칸을 붉게 두른다 (왼쪽 표는 LOGIC 영역 왼쪽, 오른쪽 표는 오른쪽)
        const lg = s.logic, [fx0, fx1] = tableX();
        const x0 = r.side === "L" ? fx0 : lg[2], x1 = r.side === "L" ? lg[0] : fx1;
        const bx = el("rect", { x: x0, y: r.y0, width: x1 - x0, height: r.y1 - r.y0, class: "ft-row" }, gR);
        gR.insertBefore(bx, gR.firstChild);
        el("title", {}, bx).textContent = c.querySelector("title").textContent;
      }
    }
  }
  drawRefTags(ov);
  for (const f of s.findings) {
    if (f.at) el("circle", { cx: f.at[0], cy: f.at[1], r: 4, class: "find" }, gF);
  }
  if (L.focus && L.focus.page === s.page) drawGoto();
  $("#ov").classList.toggle("hide-nets", !$("#show-nets").checked);
  $("#ov").classList.toggle("hide-blocks", !$("#show-blocks").checked);
  paint();
}
/* ------------------------------------------------------------------ FROM / TO 표기 · 그 시트 그 행으로 이동 (L6)

   FM 칸 `G049-40` = G049 시트 40행(오른쪽 출력)에서 온 신호 · TO 칸 `G025-7` = G025 시트 7행(왼쪽 입력)으로 가는 신호.
   표기는 표가 적은 그 칸 위에, 누르면 그 시트의 그 행으로 간다. */

const REF_RE = /([A-Z]\d{3}[A-Z]?)-(\d{1,3})(?!\d)/g;
function refsIn(text) {
  const out = [];
  for (const m of String(text || "").replace(/\s+/g, "").matchAll(REF_RE)) out.push({ sheet: m[1], row: Number(m[2]) });
  return out;
}
function sheetByNo(no) { return L.sheets.find((x) => x.sheet_no === no); }
function drawRefTags(ov) {
  const s = L.sheet;
  const g = el("g", { id: "g-refs" }, ov);
  for (const t of s.table || []) {
    const box = t.side === "L" ? t.fm_box : t.to_box;
    if (!box) continue;
    const refs = refsIn(t.side === "L" ? t.fm : t.to);
    if (!refs.length) continue;
    const kind = t.side === "L" ? "from" : "to";
    const ok = refs.some((r) => sheetByNo(r.sheet));
    const rc = el("rect", { x: box[0] + 0.4, y: box[1] + 0.4, width: box[2] - box[0] - 0.8, height: box[3] - box[1] - 0.8,
      class: `reftag ${kind}${ok ? "" : " other"}`, "data-side": t.side, "data-row": t.n }, g);
    const tag = kind === "from" ? "FROM" : "TO";
    const tx = el("text", { x: kind === "from" ? box[0] - 1 : box[2] + 1, y: (box[1] + box[3]) / 2 + 1.5,
      class: `reftxt ${kind}`, "text-anchor": kind === "from" ? "end" : "start" }, g);
    tx.textContent = tag;
    const list = refs.map((r) => `${r.sheet} 시트 ${r.row}행` + (sheetByNo(r.sheet) ? "" : " (이 묶음에 없음)")).join(", ");
    el("title", {}, rc).textContent = `${tag} ${refs.map((r) => r.sheet + "-" + r.row).join(", ")} → ${list}${ok ? " — 누르면 그 행으로 갑니다" : ""}`;
    rc.addEventListener("click", (e) => {
      if (L.justPanned) return;
      e.stopPropagation();
      chooseRef(refs, t.side === "L" ? "R" : "L", e);
    });
  }
}
/* 여러 곳이면 고르는 작은 메뉴, 하나면 바로 */
function chooseRef(refs, side, e) {
  const go = refs.filter((r) => sheetByNo(r.sheet));
  if (!go.length) { status(`${refs.map((r) => r.sheet).join(", ")} 시트는 이 묶음에 없습니다 (다른 묶음 · Loop 등)`); return; }
  if (go.length === 1) { goToRef(go[0].sheet, go[0].row, side); return; }
  closeForceMenu();
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu";
  m.innerHTML = `<div class="fm-h">어느 곳으로 갈까요</div>` + go.map((r, i) => `<button data-i="${i}">${esc(r.sheet)}-${r.row} <small>${esc((sheetByNo(r.sheet) || {}).title || "")}</small></button>`).join("");
  document.body.appendChild(m);
  const rr = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(e.clientX + 8, innerWidth - rr.width - 4)) + "px";
  m.style.top = Math.max(4, Math.min(e.clientY + 8, innerHeight - rr.height - 4)) + "px";
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const b = ev.target.closest("button[data-i]");
    if (!b) return;
    closeForceMenu();
    const r = go[Number(b.dataset.i)];
    goToRef(r.sheet, r.row, side);
  });
}
/* 그 시트 그 행으로 — 지금 자리는 '이전 위치' 로 남긴다 */
function goToRef(sheetNo, row, side) {
  const t = sheetByNo(sheetNo);
  if (!t) { status(`${sheetNo} 시트는 이 묶음에 없습니다`); return; }
  if (L.sheet) {
    const st = $("#stage");
    L.back.push({ page: L.page, zoom: L.zoom, sl: st.scrollLeft, stp: st.scrollTop });
    $("#go-back").disabled = false;
  }
  L.focus = { page: t.page, row, side, at: Date.now() };
  if (t.page === L.page) { drawOverlay(); focusRow(); }
  else openSheet(t.page);
}
function goBack() {
  const b = L.back.pop();
  $("#go-back").disabled = !L.back.length;
  if (!b) return;
  L.focus = null;
  const restore = () => { setZoom(b.zoom); const st = $("#stage"); st.scrollLeft = b.sl; st.scrollTop = b.stp; };
  if (b.page === L.page) { drawOverlay(); restore(); }
  else { L.afterFit = restore; openSheet(b.page); }
}
function focusRow() {
  const f = L.focus, s = L.sheet;
  if (!f || f.page !== s.page) return;
  const t = (s.table || []).find((x) => x.n === f.row && x.side === f.side) || (s.table || []).find((x) => x.n === f.row);
  if (!t) { status(`${s.sheet_no} 시트에 ${f.row}행이 없습니다`); return; }
  const st = $("#stage");
  const [fx0, fx1] = tableX();
  const cx = t.side === "L" ? (fx0 + s.logic[0]) / 2 : (s.logic[2] + fx1) / 2;
  const z = Math.max(L.zoom, 1.6);
  setZoom(z);
  st.scrollLeft = cx * L.zoom - st.clientWidth / 2;
  st.scrollTop = ((t.y0 + t.y1) / 2) * L.zoom - st.clientHeight / 2;
  status(`${s.sheet_no} 시트 ${f.row}행 (${t.side === "L" ? "입력 · FM " + (t.fm || "없음") : "출력 · TO " + (t.to || "없음")}) — ${t.desc || "설명 없음"}`);
  const li = document.querySelector(`#${t.side === "L" ? "in" : "out"}-rows li[data-row="${f.row}"]`);
  if (li) { li.classList.add("goto"); li.scrollIntoView({ block: "nearest" }); setTimeout(() => li.classList.remove("goto"), 2600); }
}
function drawGoto() {
  const f = L.focus, s = L.sheet;
  const t = (s.table || []).find((x) => x.n === f.row && x.side === f.side) || (s.table || []).find((x) => x.n === f.row);
  if (!t) return;
  const [fx0, fx1] = tableX();
  const x0 = t.side === "L" ? fx0 : s.logic[2], x1 = t.side === "L" ? s.logic[0] : fx1;
  const r = el("rect", { x: x0, y: t.y0, width: x1 - x0, height: t.y1 - t.y0, class: "goto" }, $("#ov"));
  if (Date.now() - f.at > 3000) r.classList.add("still");
}
function badgeText(b) {
  if (b.func === "UNKNOWN") return "?";
  if (b.func === "MEMORY") return b.param.dominant === "set" ? "MEM S우선" : b.param.dominant === "reset" ? "MEM R우선" : "MEM";
  if (["GT", "DT", "PD"].includes(b.func)) return `${b.func}${b.param.text ? " " + b.param.text.replace("t=", "") : ""}`;
  if (b.func === "PB") return "PB";
  if (b.func === "SIGNAL") return "입력";
  return b.func;
}

/* ------------------------------------------------------------------ 상태 칠하기 */

function paint() {
  const s = L.sheet;
  if (!s) return;
  $("#ov").classList.toggle("sim", L.mode === "sim");     // 시뮬레이션: 활성(1) 선 말고는 아무 표시도 없다
  for (const g of document.querySelectorAll("#ov .net")) {
    const nid = g.dataset.net;
    g.classList.remove("on", "forced");
    if (L.mode === "sim" && L.values[nid] === 1) {
      g.classList.add("on");
      if (("net:" + nid) in L.forces) g.classList.add("forced");
    }
    g.classList.toggle("sel", L.sel && L.sel.net === nid);
  }
  for (const r of document.querySelectorAll("#ov .rowpin")) {
    const n = Number(r.dataset.row);
    const row = s.rows.find((x) => x.n === n);
    r.classList.toggle("v1", L.mode === "sim" && row && L.values[row.net] === 1);
    r.classList.toggle("forced", ("row:" + n) in L.forces);
    r.classList.toggle("linked", L.mode === "sim" && L.linked[n] === 1 && !(("row:" + n) in L.forces));
  }
  const act = new Set();
  if (L.mode === "sim" && L.state) {
    for (const [bid, q] of Object.entries(L.state.mem || {})) if (q === 1) act.add(bid);
    for (const [bid, t] of Object.entries(L.state.tim || {})) if (t.out === 1) act.add(bid);
    for (const k of Object.keys(L.forces)) if (k.startsWith("block:") && L.forces[k] === 1) act.add(k.slice(6));
  }
  for (const b of document.querySelectorAll("#ov .blk")) {
    b.classList.toggle("act", act.has(b.dataset.block));
    b.classList.toggle("sel", L.sel && L.sel.block === b.dataset.block);
  }
  renderRows();
}

function stopAnim() {
  for (const t of L.anim) clearTimeout(t);
  L.anim = [];
  for (const l of document.querySelectorAll("#ov .fx")) {
    l.style.transition = "none";
    l.setAttribute("stroke-dashoffset", l.dataset.len);
  }
  for (const g of document.querySelectorAll("#ov .net")) g.classList.remove("tr", "tru");
  for (const b of document.querySelectorAll("#ov .blk")) b.classList.remove("tr");
  $("#timeline").hidden = true;
}

/* 넷 하나를 몰이 자리부터 바깥으로 그린다 (선이 쭉 이어지는 모습) */
function wipe(nid, delay, show) {
  const g = document.querySelector(`#ov .net[data-net="${CSS.escape(nid)}"]`);
  if (!g) return 0;
  let maxEnd = 0;
  for (const l of g.querySelectorAll(".fx")) {
    const d0 = Number(l.dataset.d0), len = Number(l.dataset.len);
    const t0 = delay + (d0 / SPEED) * 1000, dur = (len / SPEED) * 1000;
    maxEnd = Math.max(maxEnd, t0 + dur);
    l.style.transition = "none";
    l.setAttribute("stroke-dashoffset", show ? len : 0);
    L.anim.push(setTimeout(() => {
      l.style.transition = `stroke-dashoffset ${Math.max(40, dur)}ms linear`;
      l.setAttribute("stroke-dashoffset", show ? 0 : len);
    }, t0));
  }
  return maxEnd;
}
function showAll(nids, on) {
  for (const nid of nids) {
    const g = document.querySelector(`#ov .net[data-net="${CSS.escape(nid)}"]`);
    if (!g) continue;
    for (const l of g.querySelectorAll(".fx")) { l.style.transition = "none"; l.setAttribute("stroke-dashoffset", on ? 0 : l.dataset.len); }
  }
}

/* ------------------------------------------------------------------ 연결 따라가기 */

async function traceFrom(start, up) {
  stopAnim();
  const r = await post(`/logic/api/jobs/${L.job}/sheet/${L.page}/trace`, { start, direction: up ? "up" : "down" });
  const cls = up ? "tru" : "tr";
  // 깊이마다 순서대로 — 앞 깊이의 선이 다 그려진 뒤 다음 블록을 지난다
  const byDepth = {};
  for (const o of r.order) (byDepth[o.depth] = byDepth[o.depth] || []).push(o.net);
  const bDepth = {};
  for (const b of r.blocks) (bDepth[b.depth] = bDepth[b.depth] || []).push(b.block);
  let t = 0;
  const depths = Object.keys(byDepth).map(Number).sort((a, b) => a - b);
  for (const d of depths) {
    for (const bid of bDepth[d] || []) {
      L.anim.push(setTimeout(() => { const e = document.querySelector(`#ov .blk[data-block="${CSS.escape(bid)}"]`); if (e) e.classList.add("tr"); }, t));
    }
    let end = t;
    for (const nid of byDepth[d]) {
      const g = document.querySelector(`#ov .net[data-net="${CSS.escape(nid)}"]`);
      if (g) g.classList.add(cls);
      end = Math.max(end, wipe(nid, t, true));
    }
    t = end + STEP_MS;
  }
  const nb = r.blocks.length;
  $("#info").insertAdjacentHTML("beforeend", `<p class="trace-sum">${up ? "거슬러 올라가" : "따라가"} 선 ${r.order.length}개 · 블록 ${nb}개를 지났습니다.</p>`);
}

/* ------------------------------------------------------------------ 동작 시뮬레이션 */

async function runSim(animate) {
  if (!L.sheet) return;
  const prev = { ...L.values };
  // 묶음 전체를 함께 돌린다 — 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력도 1 (서버가 판정)
  const forces = {};
  for (const [p, f] of Object.entries(L.allForces)) if (Object.keys(f).length) forces[p] = f;
  const b = await post(`/logic/api/jobs/${L.job}/simulate`, { forces, state: L.states, page: L.page });
  const r = b.focus;
  if (!r) return;
  L.states = b.state || {};
  L.state = L.states[L.page] || r.state;
  L.linked = (b.linked || {})[L.page] || {};
  L.chain = b.pages || [];
  L.notes = [...(r.notes || []), ...(b.notes || [])];
  renderSheetList(); renderChain();
  stopAnim();
  if (!animate) {
    const last = r.frames[r.frames.length - 1];
    L.values = last.values;
    showAll(Object.keys(L.values), true);
    paint(); renderInfo();
    return;
  }
  // 틀마다: 값이 바뀐 넷을 깊이 순서로 그리고, 타이머 틀 사이에는 경과를 보인다
  let t = 0;
  let cur = prev;
  r.frames.forEach((fr, i) => {
    const changed = Object.keys(fr.values).filter((n) => fr.values[n] !== cur[n]);
    const startAt = t;
    if (i > 0) {
      const label = fr.note;
      L.anim.push(setTimeout(() => timelineShow(label, TIMER_MS), startAt));
      t += TIMER_MS;
    }
    const base = t;
    const depths = {};
    for (const n of changed) (depths[fr.depth[n] || 0] = depths[fr.depth[n] || 0] || []).push(n);
    const ds = Object.keys(depths).map(Number).sort((a, b) => a - b);
    let tt = base;
    const snap = fr.values;
    L.anim.push(setTimeout(() => {
      L.values = { ...L.values };
      // 꺼지는 선은 바로, 켜지는 선은 흘러가며
      for (const n of changed) if (snap[n] !== 1) L.values[n] = snap[n];   // 꺼지는 선은 바로 사라진다
      paint();
    }, base));
    for (const d of ds) {
      let end = tt;
      for (const n of depths[d]) {
        if (snap[n] === 1) {
          L.anim.push(setTimeout(() => { L.values[n] = 1; paintNet(n); }, tt));
          end = Math.max(end, wipe(n, tt, true));
        }
      }
      tt = end + STEP_MS;
    }
    t = tt;
    L.anim.push(setTimeout(() => { L.values = { ...snap }; showAll(Object.keys(snap), true); paint(); renderInfo(); }, t));
    cur = fr.values;
  });
}
function paintNet(nid) {
  const g = document.querySelector(`#ov .net[data-net="${CSS.escape(nid)}"]`);
  if (!g) return;
  g.classList.toggle("on", L.values[nid] === 1);
}
function timelineShow(label, ms) {
  const tl = $("#timeline");
  tl.hidden = false;
  $("#tl-text").textContent = `⏱ ${label}`;
  const f = $("#tl-fill");
  f.style.transition = "none"; f.style.width = "0";
  requestAnimationFrame(() => { f.style.transition = `width ${ms}ms linear`; f.style.width = "100%"; });
  L.anim.push(setTimeout(() => (tl.hidden = true), ms + 300));
}

function setForce(key, v) {
  if (v === null) delete L.forces[key]; else L.forces[key] = v;
  runSim(true);
}

/* 입력 신호를 누르면 그 자리에 작은 메뉴 — 1 활성 / 0 비활성 / 해제 (사용자 지시 L4) */
function closeForceMenu() {
  const m = document.getElementById("force-menu");
  if (m) m.remove();
}
function forceMenu(key, e, label) {
  closeForceMenu();
  const v = L.forces[key];
  const m = document.createElement("div");
  m.id = "force-menu";
  m.className = "force-menu";
  m.dataset.key = key;
  m.innerHTML =
    (label ? `<div class="fm-h">${esc(label)}</div>` : "") +
    `<button data-v="1" class="v1${v === 1 ? " on" : ""}"><b>1</b> 활성 (activate)</button>` +
    `<button data-v="0" class="v0${v === 0 ? " on" : ""}"><b>0</b> 비활성 (deactivate)</button>` +
    (v !== undefined ? `<button data-v="x" class="vx">강제 풀기</button>` : "");
  document.body.appendChild(m);
  const x = (e && e.clientX) || innerWidth / 2, y = (e && e.clientY) || innerHeight / 2;
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(x + 8, innerWidth - r.width - 4)) + "px";
  m.style.top = Math.max(4, Math.min(y + 8, innerHeight - r.height - 4)) + "px";
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const b = ev.target.closest("button");
    if (!b) return;
    closeForceMenu();
    setForce(key, b.dataset.v === "x" ? null : Number(b.dataset.v));
  });
}

/* ------------------------------------------------------------------ 누르기 */

function onNet(nid, e) {
  L.sel = { net: nid };
  if (L.mode === "trace") traceFrom("net:" + nid, e.shiftKey);
  else forceMenu("net:" + nid, e, "선 신호");
  paint(); renderInfo();
}
function onBlock(bid, e) {
  L.sel = { block: bid };
  const b = L.sheet.blocks[bid];
  const hasIn = L.sheet.ports.some((p) => p.block === bid && p.dir === "in");
  if (L.mode === "trace") traceFrom("block:" + bid, e.shiftKey);
  else if (!hasIn || b.logic === "source") forceMenu("block:" + bid, e, b.label || b.func || "신호원");
  paint(); renderInfo();
}
function onRow(n, e) {
  const row = L.sheet.rows.find((r) => r.n === n);
  L.sel = { row: n, net: row && row.net };
  if (L.mode === "trace") traceFrom("row:" + n, row && row.side === "R");
  else if (row && row.side === "L") forceMenu("row:" + n, e, `입력 ${n}` + (row.desc ? " · " + row.desc : ""));
  paint(); renderInfo();
}

/* ------------------------------------------------------------------ 오른쪽 판 */

function valTag(v) {
  if (L.mode !== "sim") return "";
  return v === 1 ? `<span class="val v1">1</span>` : `<span class="val v0">0</span>`;
}
function forceBtns(key) {
  const v = L.forces[key];
  return `<span class="force" data-key="${esc(key)}"><button class="v1 ${v === 1 ? "on" : ""}" data-v="1" title="1 로 강제">1</button><button class="v0 ${v === 0 ? "on" : ""}" data-v="0" title="0 으로 강제">0</button><button data-v="x" title="강제 풀기">×</button></span>`;
}
function renderRows() {
  const s = L.sheet;
  if (!s) return;
  const mk = (r) => {
    const ref = r.ref ? ` <span class="ref from" data-ref-sheet="${esc(r.ref.sheet)}" data-ref-row="${r.ref.row}" data-ref-side="R" title="FROM — ${esc(r.ref.sheet)} 시트 ${r.ref.row}행으로 갑니다">FROM ${esc(r.fm)}</span>`
      : r.fm ? ` <small>${esc(r.fm)}</small>` : "";
    const hot = L.mode === "sim" && L.values[r.net] === 1 ? " hot" : "";
    const toRefs = r.side === "R" ? refsIn(r.to) : [];
    const seen = new Set(toRefs.map((x) => x.sheet + "-" + x.row));
    const extra = (r.refs_in || []).filter((x) => !seen.has(x.sheet + "-" + x.row));
    const ins = [...toRefs, ...extra].map((x) => ` <span class="ref to${hot}" data-ref-sheet="${esc(x.sheet)}" data-ref-row="${x.row}" data-ref-side="L" title="TO — ${esc(x.sheet)} 시트 ${x.row}행으로 갑니다">TO ${esc(x.sheet)}-${x.row}</span>`).join("");
    const lk = L.mode === "sim" && r.side === "L" && r.n in L.linked && !(("row:" + r.n) in L.forces)
      ? ` <span class="lk${L.linked[r.n] === 1 ? " hot" : ""}" title="다른 장의 출력이 이 입력을 몹니다">← ${esc(r.fm)} = ${L.linked[r.n]}</span>` : "";
    const toRest = String(r.to || "").replace(REF_RE, "").replace(/[\s)(]+/g, " ").trim();
    const to = r.side === "R" && toRest ? ` <small>TO ${esc(toRest)}</small>` : "";
    const right = L.mode === "sim" ? (r.side === "L" ? forceBtns("row:" + r.n) + valTag(L.values[r.net]) : valTag(L.values[r.net])) : "";
    const bad = r.ft && r.ft.ok === false;
    const warn = !bad && r.ft && r.ft.warn && r.ft.warn.length;
    const ftl = r.ft ? `<span class="ftline ${bad ? "bad" : warn ? "warn" : r.ft.ok ? "ok" : ""}">${ftText(r)}</span>` : "";
    return `<li data-row="${r.n}" class="${bad ? "ftbad" : warn ? "ftwarn" : ""}"><span class="n">${r.n}</span><span class="d" title="${esc(r.desc || "")}">${esc(r.desc || "(글 없음)")}${ref}${to}${ins}${lk}${ftl}</span><span>${right}</span></li>`;
  };
  const rows = [...s.rows].sort((a, b) => a.n - b.n);
  $("#in-rows").innerHTML = rows.filter((r) => r.side === "L").map(mk).join("") || "<li>없음</li>";
  $("#out-rows").innerHTML = rows.filter((r) => r.side === "R").map(mk).join("") || "<li>없음</li>";
}
/* from-to 대조 한 줄 — 서버(app/logic/fromto.py)가 판정한 그대로 */
function ftText(r) {
  const f = r.ft;
  if (!f) return "";
  const by = r.side === "L" ? `FM ${esc(r.fm || "")}` : `TO ${esc(f.peer || "")}`;
  const peer = r.side === "L" && r.ref ? ` → ${esc(r.ref.sheet)} 시트 ${r.ref.row}행${r.ref.src_row && r.ref.src_row !== r.ref.row ? ` (신호 ${r.ref.src_row}행)` : ""}` : "";
  if (f.ok === false) return `✕ 일치하지 않습니다 · ${by}${peer} — ${f.why.map(esc).join(" · ")}`;
  const back = r.side === "L" && f.back == null ? " (상대 TO 가 NOTE · 거꾸로는 확인 못 함)" : "";
  if (f.ok && f.warn && f.warn.length) return `✓ 연결 일치 · ${by}${peer} — ⚠ ${f.warn.map(esc).join(" · ")}`;
  if (f.ok) return `✓ 일치 · ${by}${peer}${back}`;
  return `확인 못 함 · ${by}${peer} — 상대 TO 가 NOTE 이거나 글자를 못 읽음`;
}
/* 활성이 연결을 따라 닿은 장 — 사람이 준 장에서부터 몇 장째인가 */
function renderChain() {
  const box = $("#chain");
  if (!box) return;
  const list = L.mode === "sim" ? L.chain.filter((c) => c.hop != null).sort((a, b) => a.hop - b.hop || a.page - b.page) : [];
  $("#chain-h").hidden = box.hidden = !list.length;
  box.innerHTML = list.map((c) => {
    const fr = c.from.map(([sh, n]) => `${esc(sh)}-${n}`).join(", ");
    const to = c.to.length ? ` → ${c.to.map(esc).join(", ")}` : " · 끝 (더 넘어가는 연결 없음)";
    return `<li data-page="${c.page}" class="${c.page === L.page ? "sel" : ""}"><b>${esc(c.sheet_no || "p" + c.page)}</b>
      <small>${c.hop === 0 ? "지정한 장" : `연결 ${c.hop}단계 ← ${fr}`}${to} · 활성 선 ${c.on_nets}</small></li>`;
  }).join("");
}
function renderFindings() {
  const f = L.sheet.findings;
  $("#find-count").textContent = f.length ? `${f.length}건` : "이상 없음";
  $("#findings").innerHTML = f.map((x, i) => `<li data-i="${i}">${esc(x.text)} <code>${esc(x.code)}</code></li>`).join("");
}
function renderInfo() {
  const s = L.sheet;
  const box = $("#info");
  if (!s || !L.sel) { box.innerHTML = "도면에서 선이나 블록을 누르세요."; return; }
  if (L.sel.block) {
    const b = s.blocks[L.sel.block];
    const ports = s.ports.filter((p) => p.block === L.sel.block);
    const ins = ports.filter((p) => p.dir === "in"), outs = ports.filter((p) => p.dir === "out");
    const mem = L.state && L.state.mem && L.state.mem[L.sel.block];
    const tim = L.state && L.state.tim && L.state.tim[L.sel.block];
    box.innerHTML = `<table>
      <tr><td>종류</td><td><b>${esc(FUNC_KO[b.func] || b.func)}</b> ${b.func === "MEMORY" ? `(${b.param.dominant === "set" ? "SET 우선" : b.param.dominant === "reset" ? "RESET 우선" : "기본"})` : ""}</td></tr>
      <tr><td>도면 글자</td><td>${esc(b.label || "")} <small>(읽은 그대로: ${esc(b.read || "—")})</small></td></tr>
      ${b.score ? `<tr><td>맞음</td><td>${Math.round(b.score * 100)}% <small>범례 어휘와 글자 모양</small></td></tr>` : ""}
      ${b.param.text ? `<tr><td>시간</td><td>${esc(b.param.text)}</td></tr>` : ""}
      <tr><td>단자</td><td>들어옴 ${ins.length} · 나감 ${outs.length}</td></tr>
      ${L.mode === "sim" && b.func === "MEMORY" ? `<tr><td>상태</td><td>${valTag(mem || 0)}</td></tr>` : ""}
      ${L.mode === "sim" && tim ? `<tr><td>타이머</td><td>출력 ${valTag(tim.out)} ${tim.due ? "· 진행 중" : ""}</td></tr>` : ""}
      ${b.func === "STEP" ? `<tr><td>주의</td><td>근사 모델: C_STEP = STEP_IN · STEP_OUT = STEP_IN AND CRIT</td></tr>` : ""}
    </table>
    <div class="acts">${L.mode === "sim" && (!ins.length || b.logic === "source") ? forceBtns("block:" + L.sel.block) : ""}
      ${L.mode === "trace" ? `<button data-act="up">거슬러 올라가기</button><button data-act="down">따라가기</button>` : ""}</div>`;
    return;
  }
  const nid = L.sel.net;
  const ports = s.ports.filter((p) => p.net === nid);
  const rows = s.rows.filter((r) => r.net === nid);
  const drv = ports.filter((p) => p.dir === "out").map((p) => FUNC_KO[s.blocks[p.block].func] || p.block)
    .concat(rows.filter((r) => r.side === "L").map((r) => `입력 ${r.n}행`));
  const snk = ports.filter((p) => p.dir === "in").map((p) => FUNC_KO[s.blocks[p.block].func] || p.block)
    .concat(rows.filter((r) => r.side === "R").map((r) => `출력 ${r.n}행`));
  box.innerHTML = `<table>
    <tr><td>선</td><td>#${esc(nid)} ${s.nets[nid] && s.nets[nid].dashed ? "(파선)" : ""}</td></tr>
    <tr><td>보내는 곳</td><td>${esc(drv.join(", ") || "없음")}</td></tr>
    <tr><td>받는 곳</td><td>${esc(snk.join(", ") || "없음")}</td></tr>
    ${L.mode === "sim" ? `<tr><td>값</td><td>${valTag(L.values[nid])} ${("net:" + nid) in L.forces ? "(강제)" : ""}</td></tr>` : ""}
    ${rows.filter((r) => r.ft).map((r) => `<tr><td>from-to ${r.n}행</td><td>${ftText(r)}</td></tr>`).join("")}
  </table>
  <div class="acts">${L.mode === "sim" ? forceBtns("net:" + nid) : `<button data-act="up">거슬러 올라가기</button><button data-act="down">따라가기</button>`}</div>
  ${L.notes && L.notes.length && L.mode === "sim" ? `<p class="lg-basis">${L.notes.map(esc).join("<br>")}</p>` : ""}`;
}
function renderHelp() {
  const sim = L.mode === "sim";
  $("#help").innerHTML = sim
    ? "<b>동작 시뮬레이션</b> — 모든 선은 디지털 1/0 입니다. 왼쪽 입력 행의 점, 누름단추(PB), 또는 아무 선이나 누르면 작은 메뉴가 뜹니다 — <b>1 활성</b> / <b>0 비활성</b> / 강제 풀기. 활성인 선만 <b>형광 파랑</b>으로 보이고, 게이트는 범례 G003 정의대로 조건이 맞을 때만 뒤 신호를 내보냅니다 (예: AND 는 입력이 모두 1 · NOT 은 입력 0 이면 1). 출력 행이 1 이 되면 그 행을 FM 으로 받는 <b>다른 장의 입력도 1</b> 이 되고 그 장의 로직도 이어서 돕니다 — 오른쪽 '활성 연결' 에서 그 장으로 갑니다. 타이머는 시간이 흐르는 모습을 아래에 보입니다."
    : "<b>연결 따라가기</b> — 선이나 블록, 행 점을 누르면 그 신호가 어디로 가는지 주황색으로 이어 그립니다. <b>Shift</b>+누름은 거슬러 올라갑니다 (어디서 오는지).";
  $("#legend").innerHTML = sim
    ? `<span><i style="background:var(--active);box-shadow:0 0 4px var(--active-glow)"></i>1 활성</span><span><i style="background:transparent;border:1px dashed #ccc"></i>0 — 표시 없음</span><span><i style="background:rgba(0,180,255,.35)"></i>켜진 메모리·타이머</span>`
    : `<span><i style="background:var(--trace)"></i>따라가는 신호</span><span><i style="background:var(--trace-up)"></i>거슬러 올라감</span><span><i style="background:rgba(47,91,216,.5)"></i>읽은 선</span><span><i style="background:var(--unk)"></i>판정 못 한 블록</span>`;
}

/* ------------------------------------------------------------------ 이벤트 */

function bind() {
  $("#job").onchange = (e) => e.target.value && openJob(e.target.value);
  $("#sheet-filter").oninput = renderSheetList;
  $("#upload").onchange = async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    status("올리는 중…");
    try { const r = await api("/logic/api/jobs", { method: "POST", body: fd }); await loadJobs(r.id); }
    catch (err) { status("올리기 실패 — " + err.message); }
    e.target.value = "";
  };
  $("#samples").onclick = async (e) => {
    const n = e.target.dataset.sample;
    if (!n) return;
    try { const r = await post("/logic/api/jobs/sample", { name: n }); await loadJobs(r.id); }
    catch (err) { status("샘플 실패 — " + err.message); }
  };
  $("#mode").onclick = (e) => {
    const m = e.target.dataset.mode;
    if (!m) return;
    L.mode = m;
    for (const b of document.querySelectorAll("#mode button")) b.classList.toggle("on", b.dataset.mode === m);
    stopAnim();
    renderHelp();
    if (m === "sim") runSim(false); else { L.values = {}; L.linked = {}; paint(); }
    renderInfo(); renderRows(); renderChain(); renderSheetList();
  };
  $("#zoom-in").onclick = () => setZoom(L.zoom * 1.25, [$("#stage").clientWidth / 2, $("#stage").clientHeight / 2]);
  $("#zoom-out").onclick = () => setZoom(L.zoom / 1.25, [$("#stage").clientWidth / 2, $("#stage").clientHeight / 2]);
  $("#zoom-fit").onclick = () => { L.focus = null; drawOverlay(); fit(); };
  $("#go-back").onclick = goBack;
  $("#goto").onkeydown = (e) => { if (e.key === "Enter" && !e.isComposing) { gotoTyped(e.target.value); e.target.select(); } };
  $("#all-toggle").onclick = () => { const b = $("#all-box"); b.hidden = !b.hidden; $("#all-toggle").textContent = b.hidden ? "펼치기" : "접기"; };
  $("#all-code").onchange = (e) => { L.allCode = e.target.value; renderAll(); };
  $("#show-nets").onchange = () => $("#ov").classList.toggle("hide-nets", !$("#show-nets").checked);
  $("#show-blocks").onchange = () => $("#ov").classList.toggle("hide-blocks", !$("#show-blocks").checked);
  $("#reset").onclick = () => { L.allForces = {}; L.forces = L.allForces[L.page] = {}; L.states = {}; L.linked = {}; L.chain = []; renderChain(); renderSheetList(); L.state = null; L.values = {}; stopAnim(); if (L.mode === "sim") runSim(false); else paint(); renderInfo(); };
  document.body.addEventListener("click", (e) => {
    if (!e.target.closest("#force-menu")) closeForceMenu();
    const fb = e.target.closest(".force button");
    if (fb) {
      const key = fb.parentElement.dataset.key;
      const v = fb.dataset.v === "x" ? null : Number(fb.dataset.v);
      setForce(key, v);
      return;
    }
    const ref = e.target.closest(".ref");
    if (ref && ref.dataset.refSheet) { goToRef(ref.dataset.refSheet, Number(ref.dataset.refRow), ref.dataset.refSide || "R"); return; }
    const al = e.target.closest("#all-findings li[data-i]");
    if (al) { gotoFinding(Number(al.dataset.i)); return; }
    const cl = e.target.closest("#chain li[data-page]");
    if (cl) { L.focus = null; openSheet(Number(cl.dataset.page)); return; }
    const li = e.target.closest(".lg-rows li[data-row]");
    if (li) { onRow(Number(li.dataset.row), e); return; }
    const act = e.target.closest("[data-act]");
    if (act && L.sel) {
      const start = L.sel.block ? "block:" + L.sel.block : L.sel.row ? "row:" + L.sel.row : "net:" + L.sel.net;
      traceFrom(start, act.dataset.act === "up");
      return;
    }
    const fi = e.target.closest("#findings li");
    if (fi) {
      const f = L.sheet.findings[Number(fi.dataset.i)];
      const at = f.at || (f.block && L.sheet.blocks[f.block] && L.sheet.blocks[f.block].bbox.slice(0, 2));
      if (f.block) { L.sel = { block: f.block }; paint(); renderInfo(); }
      if (at) { const st = $("#stage"); st.scrollLeft = at[0] * L.zoom - st.clientWidth / 2; st.scrollTop = at[1] * L.zoom - st.clientHeight / 2; }
    }
  });
  $("#stage").addEventListener("click", () => { if (L.justPanned) return; L.sel = null; paint(); renderInfo(); });
  window.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeForceMenu(); stopAnim(); } });
}

bind();
initPan();
renderHelp();
loadJobs().catch((e) => status(e.message));
