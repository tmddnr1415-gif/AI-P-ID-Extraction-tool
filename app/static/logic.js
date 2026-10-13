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
  memos: [], memoEdit: null, pinMode: false, pendingAt: null, memoFlash: null,   // 메모 (L8)
  timers: {}, defaultT: 10, count: {},              // L15 — 사람이 바꾼 타이머 시간 {쪽: {블록: 초}} · 세는 중인 타이머
};
const SPEED = 900;          // 선 위를 신호가 흐르는 속도 (pt/초)
const STEP_MS = 260;        // 블록 하나를 지날 때마다 기다림
const TIMER_MS = 1100;      // (옛 고정 경과 — L15 부터 타이머는 그 시간만큼 실제로 센다)
const NEED_FLASH = 3;       // L15 — 출력을 활성화했을 때 필요한 입력을 주황으로 몇 번 점등하나 (사용자 지시)
const NEED_MS = 520;        // 점등 한 번의 길이

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
  SOE: "이벤트 기록 (SOE)", SIGNAL: "신호 이름 상자 (입력)", UNKNOWN: "판정 못 함", MACRO: "매크로 블록",
};

/* L12 — 매크로 블록의 새 창: 주소의 macro=<부모 장>:<블록>&in=<행>:<값>,… (부모 창이 입력 단자 값을 보낸다) */
const MACRO_FROM = (() => {
  const m = location.hash.match(/macro=(\d+):([\w-]+)/);
  if (!m) return null;
  const inp = {};
  for (const kv of ((location.hash.match(/[&#]in=([\d:,]+)/) || [])[1] || "").split(",")) {
    const [r, v] = kv.split(":");
    if (r) inp[r] = Number(v) === 1 ? 1 : 0;
  }
  return { parent: Number(m[1]), block: m[2], target: Number((location.hash.match(/page=(\d+)/) || [])[1]),
           from: decodeURIComponent((location.hash.match(/from=([^&]*)/) || [])[1] || ""), inputs: inp };
})();

/* ------------------------------------------------------------------ 묶음 · 시트 */

async function loadJobs(select) {
  const j = await api("/logic/api/jobs");
  const sel = $("#job");
  sel.innerHTML = "";
  if (!j.jobs.length) sel.innerHTML = `<option value="">— 분석한 묶음 없음 —</option>`;
  for (const x of j.jobs) {
    const st = x.state === "done" ? `${x.sheets}장` : x.state === "failed" ? "실패"
      : `분석 중 ${(x.progress && x.progress.percent) || 0}%`;
    sel.insertAdjacentHTML("beforeend", `<option value="${x.id}">${esc(x.name)} · ${st}</option>`);
  }
  $("#samples").innerHTML = j.samples.map((n) => `<button data-sample="${esc(n)}" title="data/logic 의 샘플을 분석합니다">샘플: ${esc(n.replace(/\.pdf$/i, ""))}</button>`).join(" ");
  sel.insertAdjacentHTML("afterbegin", `<option value="">— 묶음 고르기 —</option>`);
  L.jobsList = j.jobs;
  // 주소에 묶음이 있거나 방금 올린 묶음이면 그것을 열고, 아니면 첫 화면 (P&ID 와 같은 꼴 · L14)
  const want = select || (location.hash.match(/job=([0-9a-f]{12})/) || [])[1];
  if (want) { sel.value = want; hideHome(); await openJob(want); }
  else { sel.value = ""; showHome(); }
}

/* ------------------------------------------------------------------ 첫 화면 (L14) — 프로젝트 · 자료 · 분석 이력 */
const HOME = { projects: [], materials: [], files: {}, poll: null };
function author() {
  const u = new URLSearchParams(location.search).get("user");
  if (u) return u;
  try { return localStorage.getItem("pid.author") || ""; } catch (e) { return ""; }
}
function showHome() {
  $("#home").hidden = false;
  document.querySelector(".lg-main").hidden = true;
  stopAnim(); closeForceMenu();
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);
  L.job = null;
  $("#job").value = "";
  for (const id of ["#ft-report", "#report"]) $(id).hidden = true;
  $("#goto").disabled = true;
  status("");
  loadHome();
}
function hideHome() {
  $("#home").hidden = true;
  document.querySelector(".lg-main").hidden = false;
  if (HOME.poll) { clearTimeout(HOME.poll); HOME.poll = null; }
}
async function loadHome() {
  const [p, j] = await Promise.all([api("/logic/api/projects"), api("/logic/api/jobs")]);
  HOME.projects = p.projects; HOME.materials = p.materials; L.jobsList = j.jobs;
  const sel = $("#lh-project"), cur = sel.value || (() => { try { return localStorage.getItem("logic.project") || ""; } catch (e) { return ""; } })();
  sel.innerHTML = `<option value="">(고르세요)</option>` + HOME.projects.map((x) => `<option value="${esc(x.name)}">${esc(x.name)} — 실행</option>`).join("");
  if (HOME.projects.some((x) => x.name === cur)) sel.value = cur;
  renderMaterials(); renderHomeLists(); updateGo();
  if (HOME.poll) clearTimeout(HOME.poll);
  if (j.jobs.some((x) => x.state === "queued" || x.state === "running"))
    HOME.poll = setTimeout(() => { if (!$("#home").hidden) loadHome(); }, 3000);
}
function renderMaterials() {
  $("#lh-materials").innerHTML = HOME.materials.map((m) => {
    const f = HOME.files[m.kind];
    return `<li data-kind="${m.kind}" class="${f ? "has" : ""}">
      <div class="mh"><b>${esc(m.label)}</b> ${m.required ? `<span class="req">필수</span>` : `<span class="opt">선택</span>`}
        <small>${m.ext.join(" · ")}</small></div>
      <label class="drop">${f ? `<span class="fn">📄 ${esc(f.name)}</span> <small>${(f.size / 1048576).toFixed(1)} MB</small>`
        : `여기에 놓거나 <u>파일 선택</u>`}<input type="file" accept="${m.ext.join(",")}" hidden></label>
      ${f ? `<button class="mini clr" title="빼기">✕</button>` : ""}</li>`;
  }).join("");
  for (const li of document.querySelectorAll("#lh-materials li")) {
    const kind = li.dataset.kind, inp = li.querySelector("input");
    inp.onchange = () => { if (inp.files[0]) setMaterial(kind, inp.files[0]); };
    const drop = li.querySelector(".drop");
    drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("over"); };
    drop.ondragleave = () => drop.classList.remove("over");
    drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("over"); const f = e.dataTransfer.files[0]; if (f) setMaterial(kind, f); };
    const c = li.querySelector(".clr");
    if (c) c.onclick = () => { delete HOME.files[kind]; renderMaterials(); updateGo(); };
  }
}
function setMaterial(kind, f) {
  const m = HOME.materials.find((x) => x.kind === kind);
  const ext = (f.name.match(/\.[^.]+$/) || [""])[0].toLowerCase();
  if (m && !m.ext.includes(ext)) { status(`${m.label} 는 ${m.ext.join(" · ")} 파일만 받습니다`); return; }
  HOME.files[kind] = f; renderMaterials(); updateGo();
}
function updateGo() {
  const p = $("#lh-project").value, lg = HOME.files.logic;
  const why = !p ? "① 프로젝트를 먼저 고르세요" : !lg ? "② Logic Diagram PDF 는 필수입니다" : "";
  $("#lh-why").textContent = why;
  $("#lh-analyse").disabled = !!why;
}
async function analyseHome() {
  const fd = new FormData();
  for (const [k, f] of Object.entries(HOME.files)) fd.append(k, f);
  fd.append("project", $("#lh-project").value);
  fd.append("author", author());
  $("#lh-analyse").disabled = true;
  status("올리는 중…");
  try {
    const r = await api("/logic/api/jobs", { method: "POST", body: fd });
    HOME.files = {};
    await loadJobs(r.id);
  } catch (err) { status("올리기 실패 — " + err.message); updateGo(); }
}
function fmtDate(t) {
  if (!t) return "";
  const d = new Date(t * 1000), z = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())} ${z(d.getHours())}:${z(d.getMinutes())}`;
}
function jobLine(x) {
  const mats = Object.keys(x.materials || { logic: 1 });
  const lab = Object.fromEntries(HOME.materials.map((m) => [m.kind, m.label]));
  const st = x.state === "done" ? `<span class="ok">● 완료</span> <span class="chip">${x.sheets}장</span>`
    : x.state === "failed" ? `<span class="bad">● 실패</span>`
    : `<span class="run">● 분석 중 ${(x.progress && x.progress.percent) || 0}%</span>`;
  return `<li data-job="${x.id}"><div class="jn">${esc(x.name || "")}</div>
    <div class="jm">${st} ${mats.map((k) => `<span class="mat">${esc(lab[k] || k)}</span>`).join("")}
    <span class="when">${fmtDate(x.created)}</span>${x.author ? ` <span class="when">· ${esc(x.author)}</span>` : ""}</div>
    ${x.state === "queued" || x.state === "running" ? `<div class="pbar"><i style="width:${(x.progress && x.progress.percent) || 0}%"></i></div>` : ""}</li>`;
}
function renderHomeLists() {
  const jobs = L.jobsList || [];
  const by = {};
  for (const x of jobs) (by[x.project || ""] = by[x.project || ""] || []).push(x);
  const cards = HOME.projects.slice().sort((a, b) => (b.created || 0) - (a.created || 0)).map((p) => {
    const js = by[p.name] || [];
    const last = js.find((x) => x.state === "done");
    return `<div class="pj"><div class="pjh"><span class="ic">${esc(p.name.slice(0, 1).toUpperCase())}</span>
      <div><b>${esc(p.name)}</b> <span class="lh-mode sm">실행</span><br><small>분석 ${js.length}건${last ? ` · 마지막 ${fmtDate(last.created)} · ${last.sheets}장` : ""}</small></div></div>
      <ul class="pjj">${js.map(jobLine).join("") || `<li class="empty">위 ① 에서 이 프로젝트를 고르고 Logic PDF 를 넣으면 첫 분석이 됩니다.</li>`}</ul></div>`;
  });
  if ((by[""] || []).length)
    cards.push(`<div class="pj loose"><div class="pjh"><span class="ic">–</span><div><b>프로젝트에 안 묶인 분석</b><br><small>${by[""].length}건</small></div></div>
      <ul class="pjj">${by[""].map(jobLine).join("")}</ul></div>`);
  $("#lh-projects").innerHTML = cards.join("") || `<p class="lh-help">아직 프로젝트가 없습니다 — 위 ① 의 <b>새 프로젝트</b>.</p>`;
  $("#lh-recent").innerHTML = jobs.slice(0, 10).map(jobLine).join("") || `<li class="empty">분석 이력이 없습니다.</li>`;
}
function bindHome() {
  $("#to-home").onclick = showHome;
  $("#lh-project").onchange = (e) => { try { localStorage.setItem("logic.project", e.target.value); } catch (er) {} updateGo(); };
  $("#lh-newproj").onclick = () => { $("#lh-newbox").hidden = false; $("#lh-newname").focus(); };
  $("#lh-cancel").onclick = () => { $("#lh-newbox").hidden = true; };
  const create = async () => {
    try {
      const p = await post("/logic/api/projects", { name: $("#lh-newname").value, author: author() });
      $("#lh-newbox").hidden = true; $("#lh-newname").value = "";
      try { localStorage.setItem("logic.project", p.name); } catch (e) {}
      $("#lh-project").value = p.name;
      await loadHome(); $("#lh-project").value = p.name; updateGo();
      status(`프로젝트 '${p.name}' 를 만들었습니다 — 실행 프로젝트`);
    } catch (err) { status("만들지 못했습니다 — " + err.message); }
  };
  $("#lh-create").onclick = create;
  $("#lh-newname").onkeydown = (e) => { if (e.key === "Enter" && !e.isComposing) create(); };
  $("#lh-analyse").onclick = analyseHome;
  $("#home").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-job]");
    if (!li) return;
    hideHome();
    $("#job").value = li.dataset.job;
    openJob(li.dataset.job);
  });
}

async function openJob(id) {
  L.job = id;
  loadTimers();
  const st = await api(`/logic/api/jobs/${id}`);
  if (st.state !== "done") {
    if (st.state === "failed") { renderProgress(st); status(`분석 실패 — ${st.error || ""}`); return; }
    renderProgress(st);
    status("");
    setTimeout(() => L.job === id && openJob(id), 1200);
    return;
  }
  const wasRunning = L.progJob === id;
  renderProgress(null);
  status(`분석 ${st.seconds}초 · ${st.sheets}장`);
  const j = await api(`/logic/api/jobs/${id}/sheets`);
  L.sheets = j.sheets;
  $("#basis").innerHTML = `${esc(j.note)}<br><br>배운 글자: ${Object.keys(j.dictionary).map(esc).join(" ")}`;
  renderSheetList();
  $("#goto").disabled = false;
  const rep = $("#report"); rep.hidden = false; rep.href = `/logic/api/jobs/${id}/report.xlsx`;
  L.all = null; L.allSel = null;
  api(`/logic/api/jobs/${id}/findings`).then((f) => { if (L.job === id) { L.all = f; renderAll(); } }).catch(() => {});
  L.memos = [];
  loadMemos(id);
  $("#ft-report").hidden = false;
  // 사용자 규칙 1 — 신호를 주기 전에 From-To 점검 보고를 먼저 (이 묶음을 처음 열 때 · 방금 분석이 끝났을 때)
  let seen = false;
  try { seen = localStorage.getItem("logic.ftseen." + id) === "1"; } catch (e) {}
  if (!MACRO_FROM && (wasRunning || !seen)) showFromTo(id);
  const p = Number((location.hash.match(/page=(\d+)/) || [])[1]) || (L.sheets[0] && L.sheets[0].page);
  if (p) openSheet(p);
}
/* ------------------------------------------------------------------ 분석 진행 (P&ID 와 같은 꼴 · L13) */
function fmtSec(t) {
  if (t == null) return "";
  t = Math.max(0, Math.round(t));
  return t >= 60 ? `${Math.floor(t / 60)}분 ${t % 60}초` : `${t}초`;
}
function renderProgress(st) {
  const box = $("#prog");
  if (!st) { box.hidden = true; $("#canvas").style.visibility = ""; L.progJob = null; return; }
  L.progJob = L.job;
  $("#canvas").style.visibility = "hidden";
  $("#empty").hidden = true;
  box.hidden = false;
  if (st.state === "failed") {
    box.innerHTML = `<div class="pg-card fail"><h2>분석하지 못했습니다</h2><p class="pg-name">${esc(st.name || "")}</p>
      <p>${esc(st.error || "")}</p></div>`;
    return;
  }
  const pr = st.progress || { percent: 0, stage: "기다리는 중" };
  const known = pr.percent > 0 || st.state === "running";
  box.innerHTML = `<div class="pg-card">
    <h2>Logic 분석 중 <b>${pr.percent}%</b></h2>
    <p class="pg-name">${esc(st.name || "")}${st.pages ? ` · ${st.pages}쪽` : ""}</p>
    <div class="pg-bar${known ? "" : " unknown"}"><div class="pg-fill" style="width:${pr.percent}%"></div></div>
    <p class="pg-stage">${esc(pr.stage || "")}</p>
    <p class="pg-time">${pr.elapsed ? `경과 ${fmtSec(pr.elapsed)}` : ""}${pr.remaining != null ? ` · 남은 시간 약 ${fmtSec(pr.remaining)}` : " · 남은 시간은 아직 어림할 수 없습니다"}</p>
    ${pr.basis ? `<p class="pg-basis">어림 근거: ${esc(pr.basis)}</p>` : ""}
    <p class="pg-note">끝나면 <b>From-To 점검 보고</b>를 먼저 보여 드립니다 — 그 뒤 입력 신호를 주어 로직을 확인하세요.</p>
  </div>`;
}

/* ------------------------------------------------------------------ From-To 점검 보고 (사용자 규칙 1 · L13) */
async function showFromTo(id) {
  id = id || L.job;
  let r;
  try { r = await api(`/logic/api/jobs/${id}/fromto`); } catch (e) { return; }
  if (L.job !== id) return;
  try { localStorage.setItem("logic.ftseen." + id, "1"); } catch (e) {}
  L.ftReport = r;
  const c = r.counts;
  const mis = r.items.filter((x) => x.kind === "mismatch"), dif = r.items.filter((x) => x.kind === "desc");
  const li = (x, i) => `<tr data-ft="${i}"><td><b>${esc(x.sheet_no)}-${x.row}</b> <small>${x.side === "L" ? "입력" : "출력"}</small></td>
      <td>${esc(x.desc)}</td><td>${x.side === "L" ? "FM" : "TO"} ${esc(x.ref)}</td><td>${esc(x.why)}</td></tr>`;
  $("#ft-box").innerHTML = `<h2>From-To 점검 보고 <small>${esc((L.sheets.length ? L.sheets.length + "장 · " : ""))}신호를 주기 전에 먼저 확인합니다</small></h2>
    <div class="ft-cards">
      <div class="ft-c ok"><b>${c.ok}</b><span>연결 일치</span></div>
      <div class="ft-c bad"><b>${c.mismatch}</b><span>일치하지 않음</span></div>
      <div class="ft-c warn"><b>${c.desc}</b><span>연결은 맞고 설명 다름</span></div>
      <div class="ft-c"><b>${c.unchecked + c.other}</b><span>확인 못 함 <small>(다른 묶음 ${c.other})</small></span></div>
    </div>
    <h3>일치하지 않음 ${mis.length}건 <small>— 누르면 그 시트 그 행으로 갑니다</small></h3>
    ${mis.length ? `<div class="ft-scroll"><table class="ft-t"><tr><th>시트-행</th><th>설명</th><th>적힌 곳</th><th>사유</th></tr>${mis.map((x) => li(x, r.items.indexOf(x))).join("")}</table></div>` : `<p class="ft-none">없습니다 — 모든 From-To 가 맞대어졌습니다.</p>`}
    <details><summary>연결은 맞고 설명이 다른 것 ${dif.length}건</summary>
      <div class="ft-scroll"><table class="ft-t">${dif.map((x) => li(x, r.items.indexOf(x))).join("")}</table></div></details>
    <div class="ft-acts"><a class="btn" href="/logic/api/jobs/${id}/report.xlsx">Excel 보고서 내려받기</a>
      <button id="ft-close" class="btn primary">확인 — 신호 주며 로직 보기</button></div>`;
  $("#ft-modal").hidden = false;
}
function closeFromTo() { $("#ft-modal").hidden = true; }

/* ------------------------------------------------------------------ 신호를 주는 중의 리마인드 (사용자 규칙 2 · L13) */
function renderRemind(fresh) {
  const box = $("#remind");
  const errs = (L.design || []).filter((e) => e.kind === "error");
  if (!errs.length || L.mode !== "sim") { box.hidden = true; return; }
  if (!fresh.length && box.hidden) return;              // 닫은 뒤 새 것이 없으면 다시 띄우지 않는다
  box.hidden = false;
  const show = fresh.length ? fresh : errs;
  box.innerHTML = `<div class="rm-h">⚠ From-To 가 일치하지 않는 신호 ${errs.length}건${fresh.length ? ` <small>(방금 ${fresh.length}건)</small>` : ""}
      <button class="rm-x" title="닫기">✕</button></div>
    <ul>${show.slice(0, 6).map((e) => `<li data-i="${L.design.indexOf(e)}"><b>${esc(e.sheet_no)}-${e.row}</b> ${esc(e.desc || "")}<br>
      <small>${esc(e.why)}</small><br>
      <button data-go="src">${esc(e.sheet_no)}-${e.at_row || e.row} 로</button>${e.target_page ? `<button data-go="dst">${esc(e.to)} 로</button>` : ""}</li>`).join("")}</ul>
    ${show.length > 6 ? `<p class="rm-more">… 나머지는 오른쪽 '설계 오류' 목록</p>` : ""}`;
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
      <span class="meta">${ch ? `<i class="chain-dot"></i>${ch.hop === 0 ? "지정한 장" : `연결 ${ch.hop}단계`} · ` : ""}블록 ${s.blocks} · 선 ${s.nets}${s.mismatch ? ` · <b>from-to 불일치 ${s.mismatch}</b>` : ""}${s.descdiff ? ` · <i class="dd">설명 다름 ${s.descdiff}</i>` : ""}${s.findings ? ` · <b>점검 ${s.findings}</b>` : ""}${memoCount(s.page) ? ` · <i class="mc">✎${memoCount(s.page)}</i>` : ""}</span>`;
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
  renderRows(); renderFindings(); renderInfo(); renderHelp(); renderLatches();
  L.pendingAt = null; L.memoEdit = null; renderMemo();
  img.onload = () => fit();
  if (img.complete) fit();
  if (MACRO_FROM && page === MACRO_FROM.target && !L.macroApplied) {
    L.macroApplied = true;
    applyMacroInputs(MACRO_FROM.inputs);
    return;
  }
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
    const cls = "blk" + (b.func === "UNKNOWN" ? " unknown" : "") + (b.func === "MACRO" ? " macro" : "");
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
  drawConnectorLinks(gB);
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
  el("g", { id: "g-sim" }, ov);       // 게이트 단자 1/0 · S-R 표 (L8) — paint 가 채운다
  el("g", { id: "g-count" }, ov);     // L15 — 세는 타이머의 남은 시간
  el("g", { id: "g-need" }, ov);      // L15 — 출력을 활성화했을 때 필요한 입력 (주황 3번 점등)
  drawPins();
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
    const bad = L.mode === "sim" && designErrorsOnPage()[t.side].has(t.n);
    const rc = el("rect", { x: box[0] + 0.4, y: box[1] + 0.4, width: box[2] - box[0] - 0.8, height: box[3] - box[1] - 0.8,
      class: `reftag ${kind}${ok ? "" : " other"}${bad ? " design-err" : ""}`, "data-side": t.side, "data-row": t.n }, g);
    const tag = kind === "from" ? "FROM" : "TO";
    const tx = el("text", { x: kind === "from" ? box[0] - 1 : box[2] + 1, y: (box[1] + box[3]) / 2 + 1.5,
      class: `reftxt ${kind}`, "text-anchor": kind === "from" ? "end" : "start" }, g);
    tx.textContent = tag;
    const list = refs.map((r) => `${r.sheet} 시트 ${r.row}행` + (sheetByNo(r.sheet) ? "" : " (이 묶음에 없음)")).join(", ");
    const why = bad ? (L.design || []).filter((e) => e.kind === "error" && ((t.side === "R" && e.page === L.page && (e.at_row || e.row) === t.n)
      || (t.side === "L" && e.target_page === L.page && e.target_row === t.n))).map((e) => "\n⚠ 설계 오류 — " + e.why).join("") : "";
    el("title", {}, rc).textContent = `${tag} ${refs.map((r) => r.sheet + "-" + r.row).join(", ")} → ${list}${ok ? " — 누르면 그 행으로 갑니다" : ""}${why}`;
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

/* L13 — 같은 글자 연결 기호(A ↔ A)를 가상의 점선으로 잇는다.  보내는 기호(들어오는 선이 있는 것)에서 받는 기호로.
   한 신호이므로 그 묶음의 어느 선이든 1 이면 점선도 파랗게 (paint). */
function connectorGroups() {
  const s = L.sheet, g = {};
  for (const [bid, b] of Object.entries(s.blocks)) {
    if (b.func !== "CONNECTOR" || !b.label || b.label === "?") continue;
    (g[b.group || bid] = g[b.group || bid] || []).push(bid);
  }
  return Object.entries(g).filter(([, m]) => m.length >= 2);
}
function drawConnectorLinks(gB) {
  const s = L.sheet;
  const gl = el("g", { id: "g-clink" }, gB);
  gB.insertBefore(gl, gB.firstChild);
  const mid = (b) => [(b.bbox[0] + b.bbox[2]) / 2, (b.bbox[1] + b.bbox[3]) / 2];
  for (const [gid, mem] of connectorGroups()) {
    const hasIn = (bid) => s.ports.some((p) => p.block === bid && p.dir === "in");
    const src = mem.filter(hasIn), dst = mem.filter((m) => !hasIn(m));
    const pairs = src.length ? src.flatMap((a) => dst.map((b) => [a, b])) : mem.slice(1).map((b) => [mem[0], b]);
    for (const [a, b] of pairs) {
      const [x0, y0] = mid(s.blocks[a]), [x1, y1] = mid(s.blocks[b]);
      const ln = el("line", { x1: x0, y1: y0, x2: x1, y2: y1, class: "clink", "data-group": gid }, gl);
      el("title", {}, ln).textContent = `연결 기호 ${s.blocks[a].label} → ${s.blocks[b].label} (같은 신호 — 도면에는 선 대신 같은 글자로 그렸습니다)`;
    }
  }
}
function connectorGroupOn(gid) {
  const s = L.sheet;
  const mem = Object.entries(s.blocks).filter(([bid, b]) => b.func === "CONNECTOR" && (b.group || bid) === gid).map(([bid]) => bid);
  return s.ports.some((p) => mem.includes(p.block) && L.values[p.net] === 1);
}
function paint() {
  const s = L.sheet;
  if (!s) return;
  for (const ln of document.querySelectorAll("#ov .clink"))
    ln.classList.toggle("on", L.mode === "sim" && connectorGroupOn(ln.dataset.group));
  $("#ov").classList.toggle("sim", L.mode === "sim");     // 시뮬레이션: 활성(1) 선 말고는 아무 표시도 없다
  for (const g of document.querySelectorAll("#ov .net")) {
    const nid = g.dataset.net;
    g.classList.remove("on", "forced");
    if (L.mode === "sim" && L.values[nid] === 1) {
      g.classList.add("on");
      if (("net:" + nid) in L.forces) g.classList.add("forced");
    }
    g.classList.toggle("sel", L.sel && L.sel.net === nid);
    // 도면을 다시 그린 뒤(맞춤·메모 등)에도 활성 선은 그대로 보인다 — 흐르는 중이면 흐름에 맡긴다
    if (L.mode === "sim" && Date.now() >= (L.animUntil || 0)) {
      const on = g.classList.contains("on");
      for (const l of g.querySelectorAll(".fx")) { l.style.transition = "none"; l.setAttribute("stroke-dashoffset", on ? 0 : l.dataset.len); }
    }
  }
  for (const r of document.querySelectorAll("#ov .rowpin")) {
    const n = Number(r.dataset.row);
    const row = s.rows.find((x) => x.n === n);
    r.classList.toggle("v1", L.mode === "sim" && row && L.values[row.net] === 1);
    r.classList.toggle("forced", ("row:" + n) in L.forces);
    r.classList.toggle("implied", L.mode === "sim" && ("row:" + n) in (L.implied || {}) && !(("row:" + n) in L.forces));
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
  drawSimMarks();
  renderRows();
  renderLatches();
}

function stopAnim() {
  for (const t of L.anim) clearTimeout(t);
  L.anim = [];
  L.animUntil = 0;
  for (const l of document.querySelectorAll("#ov .fx")) {
    l.style.transition = "none";
    l.setAttribute("stroke-dashoffset", l.dataset.len);
  }
  for (const g of document.querySelectorAll("#ov .net")) g.classList.remove("tr", "tru");
  for (const b of document.querySelectorAll("#ov .blk")) b.classList.remove("tr", "trstop");
  $("#timeline").hidden = true;
  stopCount();
}

/* ------------------------------------------------------------------ L15 — 타이머 시간 (사람이 바꿈 · 기본 10초) · 카운트다운 */

const TIMER_LOGIC = new Set(["delay_on", "delay_off", "pulse"]);
function fmtSec(s) {
  s = Number(s) || 0;
  if (s >= 60) { const m = Math.floor(s / 60), r = Math.round(s - m * 60); return `${m}분${r ? " " + r + "초" : ""}`; }
  return (s >= 10 || Math.abs(s - Math.round(s)) < 0.05 ? Math.round(s) : s.toFixed(1)) + "초";
}
function timerSec(bid, page) {
  page = page ?? L.page;
  const o = (L.timers[page] || {})[bid];
  if (o) return { sec: o, src: "user" };
  const b = L.sheet && L.sheet.blocks[bid];
  const d = b && b.param && Number(b.param.t);
  if (d > 0) return { sec: d, src: "drawing" };
  return { sec: L.defaultT, src: "default" };
}
function timersKey() { return "logic.timers." + L.job; }
function loadTimers() {
  try { L.timers = JSON.parse(localStorage.getItem(timersKey()) || "{}") || {}; } catch (e) { L.timers = {}; }
}
function saveTimers() { try { localStorage.setItem(timersKey(), JSON.stringify(L.timers)); } catch (e) { /* 막힌 저장소 */ } }
function setTimer(bid, sec) {
  const p = L.page;
  L.timers[p] = L.timers[p] || {};
  if (sec == null) delete L.timers[p][bid]; else L.timers[p][bid] = sec;
  if (!Object.keys(L.timers[p]).length) delete L.timers[p];
  saveTimers();
  const ts = timerSec(bid);
  status(`타이머 ${bid} — ${fmtSec(ts.sec)} (${ts.src === "user" ? "사람이 바꿈" : ts.src === "drawing" ? "도면 값" : "도면에 없음 · 기본"})`);
  if (L.mode === "sim") { L.states = {}; L.state = null; L.values = {}; runSim(true); }
  else { paint(); renderInfo(); }
}
function timerMenu(bid, e) {
  closeForceMenu();
  const b = L.sheet.blocks[bid];
  const ts = timerSec(bid);
  const d = b.param && Number(b.param.t);
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu";
  m.innerHTML = `<div class="fm-h">${esc(FUNC_KO[b.func] || b.func)} — 시간</div>
    <label class="fm-t">시간 <input id="fm-sec" type="number" min="0.1" max="86400" step="0.1" value="${ts.sec}"> 초</label>
    <div class="fm-why">${d > 0 ? `도면 값 ${esc(b.param.text || fmtSec(d))}` : `도면에 시간이 없습니다 — 기본 ${fmtSec(L.defaultT)}`}${ts.src === "user" ? " · 지금은 사람이 바꾼 값" : ""}</div>
    <button data-t="ok" class="v1">적용 — 동작 시뮬레이션에서 이 시간만큼 셉니다</button>
    ${ts.src === "user" ? `<button data-t="x" class="vx">${d > 0 ? "도면 값으로" : `기본 ${fmtSec(L.defaultT)}로`}</button>` : ""}`;
  document.body.appendChild(m);
  const x = (e && e.clientX) || innerWidth / 2, y = (e && e.clientY) || innerHeight / 2;
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(x + 8, innerWidth - r.width - 4)) + "px";
  m.style.top = Math.max(4, Math.min(y + 8, innerHeight - r.height - 4)) + "px";
  const inp = m.querySelector("#fm-sec");
  inp.focus(); inp.select();
  const ok = () => {
    const v = Number(inp.value);
    if (!(v > 0 && v <= 86400)) { inp.classList.add("bad"); return; }
    closeForceMenu(); setTimer(bid, v);
  };
  inp.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) ok(); });
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const btn = ev.target.closest("button");
    if (!btn) return;
    if (btn.dataset.t === "ok") ok(); else { closeForceMenu(); setTimer(bid, null); }
  });
}
/* 세는 타이머의 남은 시간을 블록 위에 줄여 간다 (실제 시간) */
function startCount(run) {
  const now = Date.now();
  for (const x of run || []) L.count[x.block] = { end: now + x.left * 1000, T: x.T };
  if (!L.countTick) L.countTick = setInterval(drawCount, 100);
  drawCount();
}
function stopCount() {
  if (L.countTick) clearInterval(L.countTick);
  L.countTick = null; L.count = {};
  const g = $("#g-count"); if (g) g.innerHTML = "";
}
function drawCount() {
  const g = $("#g-count");
  if (!g || !L.sheet) return;
  g.innerHTML = "";
  const now = Date.now();
  let live = 0;
  for (const [bid, c] of Object.entries(L.count)) {
    const b = L.sheet.blocks[bid];
    if (!b) continue;
    const left = (c.end - now) / 1000;
    if (left <= -0.3) { delete L.count[bid]; continue; }
    live++;
    const [x0, y0, x1, y1] = b.bbox;
    const P = L.sheet.pitch || 11.5, fs = Math.max(3, Math.min(6, P * 0.45));
    const w = fs * 4.6, h = fs * 1.5, x = (x0 + x1) / 2 - w / 2, y = y1 + fs * 0.4;
    const gg = el("g", { class: "tcount" }, g);
    el("rect", { x, y, width: w, height: h, rx: fs * 0.3 }, gg);
    const fr = Math.max(0, Math.min(1, left / (c.T || 1)));
    el("rect", { x, y: y + h - fs * 0.22, width: w * fr, height: fs * 0.22, class: "tc-bar" }, gg);
    const tx = el("text", { x: x + w / 2, y: y + h * 0.72, "font-size": fs }, gg);
    tx.textContent = "⏱ " + fmtSec(Math.max(0, left));
  }
  if (!live && L.countTick) { clearInterval(L.countTick); L.countTick = null; }
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
  // L9 — 게이트 정의로 막힌 블록: 붉게 두르고 사유를 적는다 (AND 는 모든 입력이 따라와야 지난다)
  const stops = r.blocked || [];
  for (const b of stops) {
    L.anim.push(setTimeout(() => { const e = document.querySelector(`#ov .blk[data-block="${CSS.escape(b.block)}"]`); if (e) e.classList.add("trstop"); }, t));
  }
  const stopHtml = stops.length
    ? `<ul class="trace-stop">${stops.map((b) => `<li>⛔ <b>${esc((L.sheet.blocks[b.block] || {}).func || b.logic.toUpperCase())}</b> 에서 멈춤 — ${esc(b.reason)}</li>`).join("")}</ul>`
    : "";
  $("#info").insertAdjacentHTML("beforeend", `<p class="trace-sum">${up ? "거슬러 올라가" : "따라가"} 선 ${r.order.length}개 · 블록 ${nb}개를 지났습니다.${
    stops.length ? ` 게이트 ${stops.length}개에서 멈췄습니다.` : ""}</p>${stopHtml}`);
}

/* ------------------------------------------------------------------ 동작 시뮬레이션 */

async function runSim(animate) {
  if (!L.sheet) return;
  const prev = { ...L.values };
  // 묶음 전체를 함께 돌린다 — 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력도 1 (서버가 판정)
  const forces = {};
  for (const [p, f] of Object.entries(L.allForces)) if (Object.keys(f).length) forces[p] = f;
  const b = await post(`/logic/api/jobs/${L.job}/simulate`, { forces, state: L.states, page: L.page, timers: L.timers });
  if (b.default_t) L.defaultT = b.default_t;
  const r = b.focus;
  if (!r) return;
  L.states = b.state || {};
  L.state = L.states[L.page] || r.state;
  L.linked = (b.linked || {})[L.page] || {};
  L.chain = b.pages || [];
  // L11 — TO 를 따라 이동하다 만난 설계 오류 (TO 시트·행 없음 · 빈 행 · FM 이 다른 곳 · TO 목록에 없음)
  const prevErr = new Set((L.design || []).filter((e) => e.kind === "error").map((e) => e.page + ":" + e.row + ":" + e.to));
  L.design = b.design_errors || [];
  const fresh = L.design.filter((e) => e.kind === "error" && !prevErr.has(e.page + ":" + e.row + ":" + e.to));
  if (fresh.length) status(`⚠ 설계 오류 ${fresh.length}건 — 신호가 TO 를 따라가다 어긋난 연결을 만났습니다 (오른쪽 '설계 오류')`);
  renderRemind(fresh);
  L.notes = [...(r.notes || []), ...(b.notes || [])];
  L.implied = r.implied || {};                     // L13 — 뒤쪽 값에서 거꾸로 정한 입력 (사람이 준 값이 아니다)
  L.unmet = r.unmet || [];
  L.pulled = b.pulled || [];                         // L16 — 줄줄이 켠 다른 시트의 출력
  L.finalValues = r.frames[r.frames.length - 1].values;   // 흐름 그림이 끝난 뒤의 값 (보고는 이것으로)                          // L16 — 목표로 둔 출력 중 게이트 조건이 맞지 않아 나가지 않은 것
  if ((r.conflicts || []).length) status("⚠ 거꾸로 맞추기 모순 — " + r.conflicts.slice(0, 2).join(" · "));
  L.short = new Set(r.short_gates || []);          // L10 — 입력을 다 읽지 못해 출력을 내지 않는 게이트
  L.macros = b.macros || {};                        // L12 — 매크로 블록마다 Typical 시트의 입력·출력 행 값
  sendMacroInputs();
  renderSheetList(); renderChain();
  stopAnim();
  if (!animate) {
    const last = r.frames[r.frames.length - 1];
    L.values = last.values;
    showAll(Object.keys(L.values), true);
    paint(); renderInfo();
    return r;
  }
  // 틀마다: 값이 바뀐 넷을 깊이 순서로 그리고, 타이머 틀 사이에는 경과를 보인다
  let t = 0;
  let cur = prev;
  r.frames.forEach((fr, i) => {
    const changed = Object.keys(fr.values).filter((n) => fr.values[n] !== cur[n]);
    const startAt = t;
    if (i > 0) {
      // L15 — 타이머는 그 시간만큼 실제로 센다 (앞 틀에서 세기 시작한 타이머가 남은 초를 줄여 간다)
      const label = fr.note;
      const gap = Math.max(0, (fr.t - r.frames[i - 1].t) * 1000);
      const run = r.frames[i - 1].running || [];
      L.anim.push(setTimeout(() => { timelineShow(label, gap, run); startCount(run); }, startAt));
      t += gap;
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
  L.animUntil = Date.now() + t + 50;          // 이 뒤로는 다시 그려도 활성 선을 바로 보인다 (paint)
  return r;
}
function paintNet(nid) {
  const g = document.querySelector(`#ov .net[data-net="${CSS.escape(nid)}"]`);
  if (!g) return;
  g.classList.toggle("on", L.values[nid] === 1);
}
function timelineShow(label, ms, run) {
  const tl = $("#timeline");
  tl.hidden = false;
  const names = (run || []).map((x) => { const b = L.sheet && L.sheet.blocks[x.block]; return `${b && b.func === "MACRO" ? "매크로 안 타이머" : (b && b.func) || "타이머"} ${fmtSec(x.T)}`; });
  const t0 = Date.now();
  const txt = () => `⏱ ${names.length ? names.join(" · ") + " 세는 중 — " : ""}${label} · 남은 ${fmtSec(Math.max(0, (ms - (Date.now() - t0)) / 1000))}`;
  $("#tl-text").textContent = txt();
  const tick = setInterval(() => { if ($("#timeline").hidden) { clearInterval(tick); return; } $("#tl-text").textContent = txt(); }, 200);
  L.anim.push(setTimeout(() => clearInterval(tick), ms + 250));
  const f = $("#tl-fill");
  f.style.transition = "none"; f.style.width = "0";
  requestAnimationFrame(() => { f.style.transition = `width ${ms}ms linear`; f.style.width = "100%"; });
  L.anim.push(setTimeout(() => (tl.hidden = true), ms + 300));
}

function setMode(m, quiet) {
  L.mode = m;
  for (const b of document.querySelectorAll("#mode button")) b.classList.toggle("on", b.dataset.mode === m);
  stopAnim();
  renderHelp();
  if (m === "sim") { if (!quiet) runSim(false); } else { L.values = {}; L.linked = {}; paint(); }
  renderInfo(); renderRows(); renderChain(); renderSheetList();
}

/* L16 — 강제 신호 전체 리셋: 모든 시트에 사람이 준 1/0 · 거꾸로 맞춘 값 · 동작 예시 · 메모리 · 타이머 상태를 지운다.
   타이머 시간 설정(사람이 바꾼 초)은 신호가 아니라 설정이라 남긴다.  열린 매크로 새 창에도 0 이 된 입력을 보낸다. */
function resetAll() {
  const n = Object.values(L.allForces || {}).reduce((a, f) => a + Object.keys(f || {}).length, 0);
  L.allForces = {}; L.forces = L.allForces[L.page] = {};
  L.states = {}; L.state = null; L.values = {}; L.linked = {}; L.chain = []; L.design = [];
  L.implied = {}; L.scenario = null; L.unmet = [];
  stopAnim();
  const rb = $("#remind"); if (rb) rb.hidden = true;
  renderChain(); renderSheetList();
  if (L.mode === "sim") runSim(false); else paint();
  renderInfo(); renderRows();
  status(n ? `⟲ 강제 신호 ${n}개를 모두 지웠습니다 (모든 시트 · 메모리 · 타이머 상태 포함)` : "⟲ 지울 강제 신호가 없습니다 — 메모리 · 타이머 상태를 처음으로 되돌렸습니다");
}

function setForce(key, v) {
  // L15 — 출력(오른쪽 행 · 블록이 모는 선 · 매크로 출력 단자)을 1 로 주면: 그 출력이 서려면 어떤 입력이 1 이어야
  // 하는지 범례 정의로 찾아 그 입력들을 주황으로 3번 점등하고 실제로 활성화한다 (사용자 지시).
  if (v === 1 && wantsScenario(key)) { activateOutput(key); return; }
  // L9 — 따라가기 모드에서 입력 동그라미에 1/0 을 고르면 시뮬레이션으로 넘어가 그 값으로 돈다
  if (L.mode !== "sim") setMode("sim", true);
  if (v === null) delete L.forces[key]; else L.forces[key] = v;
  // L16 — 목표로 둔 출력이 게이트 조건을 못 채웠으면 (사람이 준 입력 0 이 막음) 그렇게 말하고 0 인 입력을 짚는다
  runSim(true).then(() => { if ((L.unmet || []).length) reportUnmet(); });
}

/* ------------------------------------------------------------------ L15 — 출력을 활성화하면 필요한 입력을 찾아 켠다 */

function wantsScenario(key, s) {
  s = s || L.sheet;
  if (!s) return false;
  if (key.startsWith("row:")) return isOutRow(key, s);
  if (!key.startsWith("net:")) return false;
  const nid = key.slice(4);
  return s.ports.some((p) => p.net === nid && p.dir === "out" && s.blocks[p.block] && s.blocks[p.block].logic !== "source");
}
async function findInputs(page, key) {
  try { return await post(`/logic/api/jobs/${L.job}/sheet/${page}/scenario`, { target: key }); }
  catch (e) { return { ok: false, why: e.message }; }
}
function needOf(forces) {
  const need = {};
  for (const [k, v] of Object.entries(forces || {})) if (v === 1 || k.startsWith("net:")) need[k] = v;
  return need;
}
function reachedIn(r, net) { return !!(r && net != null && r.frames.some((fr) => fr.values[net] === 1)); }
async function activateOutput(key) {
  if (L.mode !== "sim") setMode("sim", true);
  const name = key.startsWith("row:") ? `출력 ${key.slice(4)}행` : "선 " + key.slice(4);
  status(`${name} 이 1 이 되려면 어떤 입력이 1 이어야 하는지 찾는 중…`);
  const sc = await findInputs(L.page, key);
  if (!sc.ok) {
    // 찾지 못하면 예전처럼 그 출력만 강제하고 이유를 말한다 (지어내지 않는다)
    // L16 — 출력을 직접 켜지 않는다: 목표로 두면 서버가 범례 조건을 거꾸로 따라 앞쪽 입력을 줄줄이 정하고,
    // 게이트가 판정한다 (조건이 다 맞지 않으면 출력은 나가지 않는다 — 사용자 지시).
    L.forces[key] = 1;
    status(`⚠ ${name} — ${sc.why || "필요한 입력 조합을 찾지 못했습니다"} · 앞쪽 입력을 범례 조건대로 맞춰 봅니다 (조건이 다 맞지 않으면 출력은 나가지 않습니다)`);
    await runSim(true);
    reportUnmet();
    return;
  }
  const need = needOf(sc.forces);
  // 사람이 이미 준 값은 남기되, 필요한 입력과 겹치는 것 · 다른 출력 강제는 뺀다 (출력은 입력이 정한다)
  const keep = {};
  for (const [k, v] of Object.entries(L.forces)) if (!(k in need) && k !== key && !wantsScenario(k)) keep[k] = v;
  // L16 — 다른 시트에서 이어져 오는 입력 행은 여기서 직접 켜지 않는다: 출력을 목표로 두면 서버가 그 행을 보내는
  // 시트의 출력까지 줄줄이 켠다 (게이트가 막으면 거기서 머물고 이 출력도 나가지 않는다).
  const linkedRow = (k) => k.startsWith("row:") && L.sheet.rows.some((r) => r.n === Number(k.slice(4)) && r.side === "L" && r.ref);
  const local = {};
  for (const [k, v] of Object.entries(need)) if (!linkedRow(k)) local[k] = v;
  L.forces = L.allForces[L.page] = { ...keep, ...local, [key]: 1 };
  const on = Object.keys(need).filter((k) => need[k] === 1);
  const names = on.map(scenarioName);
  status(`${name} 을 1 로 — 필요한 입력 ${on.length}개를 주황으로 점등합니다: ${names.join(" · ")}`);
  await flashNeed(on);
  let r = await runSim(true);
  let dropped = false;
  if (!reachedIn(r, sc.net) && Object.keys(local).length !== Object.keys(need).length) {
    // 이어진 시트가 막았다 — 그 입력 행은 이 시트에서 직접 준다 (예전 방식)
    L.forces = L.allForces[L.page] = { ...keep, ...need, [key]: 1 };
    r = await runSim(true);
  }
  if (!reachedIn(r, sc.net) && Object.keys(keep).length) {
    dropped = true;
    // 지금 준 다른 값(예: RESET 입력 1)이 막았다 — 필요한 입력만 두고 다시
    L.forces = L.allForces[L.page] = { ...need, [key]: 1 };
    L.states = {}; L.state = null; L.values = {};
    r = await runSim(true);
    status(`${name} 을 1 로 — 먼저 주었던 다른 값이 이 출력을 막아 풀었습니다 · 필요한 입력: ${names.join(" · ")}`);
  }
  if (!reachedIn(r, sc.net)) reportUnmet();
  else if ((L.pulled || []).length) status(`${name} 을 1 로 — 줄줄이: 다른 시트의 출력 ${L.pulled.length}개도 켰습니다 (${L.pulled.slice(0, 6).map((x) => x.from_sheet + "-" + x.from_row).join(" · ")}${L.pulled.length > 6 ? " …" : ""})`);
  L.scenario = { key, ok: true, forces: need, direct: sc.direct_nets || [], at: sc.at, need: on };
  if (MACRO_FROM && L.page === MACRO_FROM.target && window.opener) {
    // 매크로 새 창: 이 Typical 시트의 입력 행 → 부모 창의 매크로 입력 단자도 같이 활성화 (사용자 지시)
    const rows = {};
    for (const k of on) if (k.startsWith("row:")) rows[k.slice(4)] = 1;
    try { window.opener.postMessage({ type: "macro-need", parent: MACRO_FROM.parent, block: MACRO_FROM.block, rows, fresh: dropped }, location.origin); }
    catch (e) { /* 부모 창이 닫힘 */ }
  }
  renderInfo();
}
/* L16 — 목표로 준 출력이 게이트 조건을 못 채워 나가지 않았으면 그렇게 말하고, 그 게이트에서 0 인 입력을 주황으로 짚는다 */
function reportUnmet() {
  // L17 — 모든 게이트: 원하는 출력에 필요한 입력 조건(범례 G003)을 말하고, 맞지 않는 입력을 주황으로 짚는다
  const u = L.unmet || [];
  if (!u.length || !L.sheet) return;
  const vals = L.finalValues || L.values;
  const keys = [];
  const parts = [];
  for (const x of u) {
    const b = x.block && L.sheet.blocks[x.block];
    const name = (b && b.func) || "게이트";
    const ins = L.sheet.ports.filter((p) => p.block === x.block && p.dir === "in");
    if ((x.unread || []).length) {
      for (const n of x.unread) keys.push("net:" + n);
      parts.push(`${name} 입력선 ${x.unread.length}개를 도면에서 읽지 못해 ${x.want} 을 낼 수 없음`);
      continue;
    }
    const need = gateNeed(x.logic, x.want);
    const off = ins.filter((p) => need == null || (vals[p.net] === 1 ? 1 : 0) !== need).map((p) => p.net);
    for (const n of off) keys.push("net:" + n);
    parts.push(`${name} = ${x.want} 조건: ${gateNeedText(x.logic, x.want)}`);
  }
  status(`⛔ 출력이 나가지 않습니다 — ${parts.join(" · ")} (게이트가 범례대로 판정 · 맞지 않는 입력을 주황으로 짚습니다)`);
  flashNeed(keys);
}
/* 그 출력을 내려면 입력이 모두 이 값이어야 하는 게이트 (정해지지 않으면 null — 모든 입력을 짚는다) */
function gateNeed(lg, want) {
  if ((lg === "and" && want === 1) || (lg === "nand" && want === 0)) return 1;
  if ((lg === "or" && want === 0) || (lg === "nor" && want === 1)) return 0;
  if (lg === "not") return 1 - want;
  return null;
}
function gateNeedText(lg, want) {
  const t = {
    "and:1": "입력이 모두 1", "and:0": "입력 하나가 0", "nand:0": "입력이 모두 1", "nand:1": "입력 하나가 0",
    "or:1": "입력 하나가 1", "or:0": "입력이 모두 0", "nor:1": "입력이 모두 0", "nor:0": "입력 하나가 1",
    "not:1": "입력이 0", "not:0": "입력이 1", "memory:1": "SET 이 1 (RESET 0)", "memory:0": "RESET 이 1 (SET 0)",
    "delay_on:1": "입력이 1 로 t초 유지", "delay_on:0": "입력이 0", "delay_off:1": "입력이 1", "delay_off:0": "입력이 0 으로 t초",
    "pulse:1": "입력이 0 → 1 로 바뀜", "pulse:0": "입력이 0 (또는 t초 경과)", "step:1": "STEP_IN (와 조건) 이 1", "step:0": "STEP_IN 이 0",
    "vote:1": "A/B 중 A 개 이상 1", "vote:0": "1 인 입력이 A 개 미만",
  };
  return t[`${lg}:${want}`] || "앞쪽 입력 조건이 맞지 않음";
}
/* 필요한 입력(행 점 · 블록 · 선)을 주황으로 NEED_FLASH 번 점등 */
function flashNeed(keys, s) {
  s = s || L.sheet;
  const g = $("#g-need");
  if (!g || !s || !keys.length) return Promise.resolve();
  g.innerHTML = "";
  const gg = el("g", { class: "need", style: `animation-duration:${NEED_MS}ms;animation-iteration-count:${NEED_FLASH}` }, g);
  const lis = [];
  for (const k of keys) {
    if (k.startsWith("row:")) {
      const n = Number(k.slice(4));
      const row = s.rows.find((r) => r.n === n && r.side === "L") || s.rows.find((r) => r.n === n);
      if (row) {
        el("circle", { cx: row.at[0], cy: row.at[1], r: 4.8 }, gg);
        if (row.net != null) for (const [x0, y0, x1, y1] of (s.order[row.net] || [])) el("line", { x1: x0, y1: y0, x2: x1, y2: y1 }, gg);
        const li = document.querySelector(`.lg-rows li[data-row="${n}"]`);
        if (li) lis.push(li);
      }
    } else if (k.startsWith("block:")) {
      const b = s.blocks[k.slice(6)];
      if (b) { const [x0, y0, x1, y1] = b.bbox; el("rect", { x: x0 - 2, y: y0 - 2, width: x1 - x0 + 4, height: y1 - y0 + 4, rx: 1.5 }, gg); }
    } else if (k.startsWith("net:")) {
      for (const [x0, y0, x1, y1] of (s.order[k.slice(4)] || [])) el("line", { x1: x0, y1: y0, x2: x1, y2: y1 }, gg);
    }
  }
  for (const li of lis) { li.classList.remove("needli"); void li.offsetWidth; li.classList.add("needli"); }
  const ms = NEED_FLASH * NEED_MS;
  return new Promise((res) => setTimeout(() => {
    gg.remove();
    for (const li of lis) li.classList.remove("needli");
    res();
  }, ms + 60));
}
/* 매크로 새 창이 "이 입력 행들이 1 이어야 한다" 고 알리면 — 부모 창의 매크로 입력 단자를 그 값으로 (앞쪽 입력까지 찾아) */
async function handleMacroNeed(d) {
  if (!L.job || MACRO_FROM) return;
  const page = Number(d.parent);
  let s = L.page === page ? L.sheet : null;
  if (!s) { try { s = await api(`/logic/api/jobs/${L.job}/sheet/${page}`); } catch (e) { return; } }
  const b = s.blocks[d.block];
  const m = (b && b.macro) || {};
  const pins = (m.inputs || []).filter((x) => x.row && d.rows[String(x.row)] === 1 && x.net != null);
  if (!pins.length) return;
  // 새 창이 먼저 있던 값이 출력을 막아 풀었다면(fresh) 부모 장도 필요한 값만으로 다시 시작한다
  const f = d.fresh ? {} : { ...(L.allForces[page] || {}) };
  if (d.fresh) { L.states = {}; L.state = null; L.values = {}; }
  const keys = [];
  for (const x of pins) {
    const sc = await findInputs(page, "net:" + x.net);
    if (sc.ok) { const need = needOf(sc.forces); Object.assign(f, need); keys.push(...Object.keys(need).filter((k) => need[k] === 1)); }
    else { f["net:" + x.net] = 1; keys.push("net:" + x.net); }
  }
  L.allForces[page] = f;
  if (page === L.page) L.forces = f;
  if (L.mode !== "sim") setMode("sim", true);
  status(`매크로 새 창(${m.sheet || ""})이 입력 단자 ${pins.map((x) => x.pin || x.row).join(" · ")} 을 요구 — ${s.sheet_no} 에서 활성화합니다`);
  if (page === L.page) await flashNeed(keys);
  runSim(true);
}

/* L14 — 출력 하나를 고르면 서버가 범례 정의(G003)를 거꾸로 따라 입력 조합을 찾고 앞으로 돌려 확인한다.
   찾은 조합을 이 시트의 강제 신호로 넣고 흐름을 그린다 — 입력부터 최종 출력까지 모든 신호가 서는 모습. */
function isOutRow(key, s) {
  s = s || L.sheet;
  if (!key.startsWith("row:") || !s) return false;
  const n = Number(key.slice(4));
  return s.rows.some((r) => r.n === n && r.side === "R" && r.net != null);
}
async function runScenario(key) {
  status("동작 예시를 찾는 중…");
  let r;
  try { r = await post(`/logic/api/jobs/${L.job}/sheet/${L.page}/scenario`, { target: key }); }
  catch (e) { status("동작 예시를 찾지 못했습니다 — " + e.message); return; }
  if (!r.ok) { status("⚠ " + (r.why || "이 출력까지 가는 입력 조합을 찾지 못했습니다")); L.scenario = { key, ok: false, why: r.why }; renderInfo(); return; }
  if (L.mode !== "sim") setMode("sim", true);
  const f = {};
  for (const [k, v] of Object.entries(r.forces)) if (v === 1 || k.startsWith("net:")) f[k] = v;
  L.forces = L.allForces[L.page] = f;
  L.states = {}; L.state = null; L.values = {};
  L.scenario = { key, ok: true, forces: f, direct: r.direct_nets || [], at: r.at };
  const ins = Object.keys(f).filter((k) => f[k] === 1).map(scenarioName);
  status(`⚡ ${key.replace("row:", "출력 ")} 동작 예시 — 입력 ${ins.length}개: ${ins.join(" · ")}` +
         (r.direct_nets && r.direct_nets.length ? ` (몰이를 못 읽은 선 ${r.direct_nets.length}개는 직접 주었습니다)` : ""));
  await runSim(true);
  renderInfo();
}
function scenarioName(k) {
  if (k.startsWith("row:")) {
    const n = Number(k.slice(4));
    const row = L.sheet.rows.find((r) => r.n === n && r.side === "L");
    return `입력 ${n}` + (row && row.desc ? ` ${row.desc}` : "");
  }
  if (k.startsWith("block:")) { const b = L.sheet.blocks[k.slice(6)]; return (b && (b.label || b.func)) || k; }
  return "선 " + k.slice(4);
}

/* 입력 신호를 누르면 그 자리에 작은 메뉴 — 1 활성 / 0 비활성 / 해제 (사용자 지시 L4) */
function closeForceMenu() {
  const m = document.getElementById("force-menu");
  if (m) m.remove();
}
function forceMenu(key, e, label, up) {
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
    (v !== undefined ? `<button data-v="x" class="vx">강제 풀기</button>` : "") +
    (L.mode === "trace" ? `<button data-v="t" class="vt">${up ? "↩ 어디서 오는지 거슬러 올라가기" : "↪ 연결만 따라가기"}</button>` : "") +
    (isOutRow(key) ? `<button data-v="s" class="vs">⚡ 이 출력까지 동작 예시 — 입력부터 최종 출력까지</button>` : "");
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
    if (b.dataset.v === "t") { traceFrom(key, !!up); return; }
    if (b.dataset.v === "s") { runScenario(key); return; }
    setForce(key, b.dataset.v === "x" ? null : Number(b.dataset.v));
  });
}

/* ------------------------------------------------------------------ 매크로 블록 (L12)

   상자를 누르면 작은 메뉴 — 내부 동작을 정의한 Typical 시트를 새 창으로 연다.  새 창은 이 상자의 입력 단자 값을
   그 시트의 입력 행에 주고 돌린다 (시뮬레이션이 다시 돌 때마다 이 창이 새 값을 보낸다). */
L.childWins = {};
function macroView(bid) { return ((L.macros || {})[L.page] || {})[bid] || null; }
function macroMenu(bid, e) {
  closeForceMenu();
  const b = L.sheet.blocks[bid], m = b.macro || {};
  const box = document.createElement("div");
  box.id = "force-menu"; box.className = "force-menu";
  box.innerHTML = `<div class="fm-h">${esc(b.caption || "매크로 블록")}</div>` +
    (m.page ? `<button data-m="open" class="v1">↗ 내부 동작 보기 (새 창) — ${esc(m.sheet)}</button>`
            : `<div class="fm-why">${esc(m.why || "이 블록의 Typical 시트를 찾지 못했습니다")}</div>`) +
    (L.mode === "trace" ? `<button data-m="trace" class="vt">↪ 연결만 따라가기</button>` : "");
  document.body.appendChild(box);
  const x = (e && e.clientX) || innerWidth / 2, y = (e && e.clientY) || innerHeight / 2;
  const r = box.getBoundingClientRect();
  box.style.left = Math.max(4, Math.min(x + 8, innerWidth - r.width - 4)) + "px";
  box.style.top = Math.max(4, Math.min(y + 8, innerHeight - r.height - 4)) + "px";
  box.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const btn = ev.target.closest("button");
    if (!btn) return;
    closeForceMenu();
    if (btn.dataset.m === "open") openMacro(bid);
    else traceFrom("block:" + bid, false);
  });
}
function macroInputs(bid) {
  const v = macroView(bid);
  if (v) return v.inputs;
  const m = L.sheet.blocks[bid].macro || {};
  const o = {};
  for (const x of m.inputs || []) if (x.row) o[x.row] = L.values[x.net] === 1 ? 1 : 0;
  return o;
}
function openMacro(bid) {
  const b = L.sheet.blocks[bid], m = b.macro || {};
  if (!m.page) return;
  const inp = Object.entries(macroInputs(bid)).map(([r, v]) => `${r}:${v}`).join(",");
  const from = encodeURIComponent(`${L.sheet.sheet_no} · ${b.caption || "매크로"}`);
  const url = `/logic${location.search}#job=${L.job}&page=${m.page}&macro=${L.page}:${bid}&in=${inp}&from=${from}`;
  const key = `${L.page}:${bid}`;
  const w = window.open(url, `macro-${L.job}-${key}`, "width=1500,height=950");
  if (w) L.childWins[key] = { win: w, page: L.page, bid };
  else status("새 창을 열지 못했습니다 — 브라우저의 팝업 차단을 풀어 주세요");
}
function sendMacroInputs() {
  for (const [key, c] of Object.entries(L.childWins)) {
    if (!c.win || c.win.closed) { delete L.childWins[key]; continue; }
    if (c.page !== L.page && !(L.macros || {})[c.page]) continue;
    const v = ((L.macros || {})[c.page] || {})[c.bid];
    if (v) c.win.postMessage({ type: "macro-inputs", key, inputs: v.inputs }, location.origin);
  }
}
window.addEventListener("message", (e) => {
  if (e.origin !== location.origin || !e.data) return;
  if (e.data.type === "macro-need") { handleMacroNeed(e.data); return; }     // L15 — 새 창이 부모에게
  if (e.data.type !== "macro-inputs" || !MACRO_FROM) return;
  applyMacroInputs(e.data.inputs);
});
async function applyMacroInputs(inputs) {
  if (!MACRO_FROM || !L.sheet || L.page !== MACRO_FROM.target) return;
  const f = {};
  // 이 창에서 사람이 준 선 · 블록 값은 남긴다 (입력 행은 부모 창의 단자 값이 정한다)
  for (const [k, v] of Object.entries(L.forces || {})) if (!k.startsWith("row:")) f[k] = v;
  for (const [r, v] of Object.entries(inputs || {})) f["row:" + r] = v === 1 ? 1 : 0;
  // L15 — 부모 창에서 새로 1 이 된 입력 행은 주황으로 3번 점등 (어떤 값이 활성화되어야 하는지)
  const fresh = Object.entries(inputs || {}).filter(([r, v]) => v === 1 && L.forces["row:" + r] !== 1).map(([r]) => "row:" + r);
  L.forces = L.allForces[L.page] = f;
  MACRO_FROM.inputs = inputs;
  renderMacroBanner();
  if (L.mode !== "sim") setMode("sim", true);
  if (fresh.length && L.macroApplied) await flashNeed(fresh);
  runSim(true);
}
function renderMacroBanner() {
  if (!MACRO_FROM) return;
  let el = document.getElementById("macro-banner");
  if (!el) {
    el = document.createElement("div");
    el.id = "macro-banner"; el.className = "macro-banner";
    document.body.prepend(el);
  }
  const on = Object.entries(MACRO_FROM.inputs || {}).filter(([, v]) => v === 1).map(([r]) => r);
  el.innerHTML = `<b>매크로 내부 동작</b> — ${esc(MACRO_FROM.from || "부모 시트")} 의 입력 단자 값으로 이 Typical 시트를 돌립니다 · ` +
    `활성 입력 행 ${on.length ? on.map(esc).join(", ") : "없음"} <small>(부모 창에서 신호를 바꾸면 여기도 바뀝니다)</small>`;
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
  if (b.func === "MACRO") { macroMenu(bid, e); paint(); renderInfo(); return; }
  const hasIn = L.sheet.ports.some((p) => p.block === bid && p.dir === "in");
  if (L.mode === "trace") traceFrom("block:" + bid, e.shiftKey);
  else if (TIMER_LOGIC.has(b.logic)) timerMenu(bid, e);          // L15 — 시간을 바꾼다
  else if (!hasIn || b.logic === "source") forceMenu("block:" + bid, e, b.label || b.func || "신호원");
  paint(); renderInfo();
}
function onRow(n, e) {
  const row = L.sheet.rows.find((r) => r.n === n);
  L.sel = { row: n, net: row && row.net };
  // L9 — 입력 동그라미는 어느 모드에서든 1 활성 / 0 비활성 메뉴 (사용자 지시).  출력 행은 따라가기 그대로.
  if (row) forceMenu("row:" + n, e, `${row.side === "L" ? "입력" : "출력"} ${n}` + (row.desc ? " · " + row.desc : ""),
                     row.side === "R");
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
    const ex = r.side === "R" && r.net != null ? `<button class="mini ex" data-ex="row:${r.n}" title="이 출력까지 입력부터 모든 신호가 서는 동작 예시를 찾아 보여 줍니다">⚡예시</button>` : "";
    const right = (L.mode === "sim" ? forceBtns("row:" + r.n) + valTag(L.values[r.net]) : "") + ex;
    const bad = r.ft && r.ft.ok === false;
    const warn = !bad && r.ft && r.ft.warn && r.ft.warn.length;
    const ftl = r.ft ? `<span class="ftline ${bad ? "bad" : warn ? "warn" : r.ft.ok ? "ok" : ""}">${ftText(r)}</span>` : "";
    return `<li data-row="${r.n}" class="${bad ? "ftbad" : warn ? "ftwarn" : ""}"><span class="n">${r.n}</span><span class="d" title="${esc(r.desc || "")}">${esc(r.desc || "(글 없음)")}${ref}${to}${ins}${lk}${ftl}</span><span>${right}</span></li>`;
  };
  const rows = [...s.rows].sort((a, b) => a.n - b.n);
  $("#in-rows").innerHTML = rows.filter((r) => r.side === "L").map(mk).join("") || "<li>없음</li>";
  $("#out-rows").innerHTML = rows.filter((r) => r.side === "R").map(mk).join("") || "<li>없음</li>";
  for (const b of document.querySelectorAll("#out-rows button[data-ex]"))
    b.onclick = (ev) => { ev.stopPropagation(); runScenario(b.dataset.ex); };
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
function renderDesignErrors() {
  const box = $("#design-err");
  if (!box) return;
  const list = L.mode === "sim" ? (L.design || []) : [];
  const nErr = list.filter((e) => e.kind === "error").length;
  $("#design-h").hidden = box.hidden = !list.length;
  $("#design-n").textContent = nErr ? `오류 ${nErr}` : "";
  const label = { error: "⚠ 설계 오류", warn: "확인 — 설명 다름", other: "다른 묶음" };
  box.innerHTML = list.map((e, i) => `<li class="de ${e.kind}" data-i="${i}">
      <b>${label[e.kind]}</b> <span class="de-at">${esc(e.sheet_no)}-${e.row}${e.desc ? " " + esc(e.desc) : ""}</span>
      <small>${esc(e.why)}</small>
      <span class="de-go">${`<button data-go="src">${esc(e.sheet_no)}-${e.at_row || e.row} 로</button>`}${
        e.target_page ? `<button data-go="dst">${esc(e.to)} 로</button>` : ""}</span></li>`).join("");
}
function refreshDesignMarks() {
  const m = L.mode === "sim" ? designErrorsOnPage() : { R: new Set(), L: new Set() };
  for (const r of document.querySelectorAll("#g-refs rect.reftag"))
    r.classList.toggle("design-err", m[r.dataset.side].has(Number(r.dataset.row)));
}
function designErrorsOnPage() {
  // 이 장에서 그 오류가 걸린 TO 칸(보내는 쪽) · FM 칸(받는 쪽)
  const mark = { R: new Set(), L: new Set() };
  for (const e of L.design || []) {
    if (e.kind !== "error") continue;
    if (e.page === L.page) mark.R.add(e.at_row || e.row);
    if (e.target_page === L.page) mark.L.add(e.target_row);
  }
  return mark;
}
function renderChain() {
  renderDesignErrors();
  refreshDesignMarks();
  const box = $("#chain");
  if (!box) return;
  const list = L.mode === "sim" ? L.chain.filter((c) => c.hop != null).sort((a, b) => a.hop - b.hop || a.page - b.page) : [];
  $("#chain-h").hidden = box.hidden = !list.length;
  box.innerHTML = list.map((c) => {
    const fr = c.from.map(([sh, n]) => `${esc(sh)}-${n}`).join(", ");
    const to = c.to.length ? ` → ${c.to.map(esc).join(", ")}` : " · 끝 (더 넘어가는 연결 없음)";
    return `<li data-page="${c.page}" class="${c.page === L.page ? "sel" : ""}"><b>${esc(c.sheet_no || "p" + c.page)}</b>
      <small>${c.hop === 0 ? (c.user ? "지정한 장" : "줄줄이 켬 — 뒤 시트의 출력 조건") : `연결 ${c.hop}단계 ← ${fr}`}${to} · 활성 선 ${c.on_nets}</small></li>`;
  }).join("");  renderSigPop();
}
/* L19 — 신호 현황 팝업: 사람이 준 신호(모든 시트) · 줄줄이 켠 목표 · 그에 따라 나간 출력.
   값은 서버(simulate_bundle 의 pages)가 낸 그대로 — 화면이 다시 판정하지 않는다.  창은 머리줄을 끌어 옮기고 자리를 기억한다. */
const SIGPOP_POS = "logic.sigpop.pos", SIGPOP_CLOSED = "logic.sigpop.closed", SIGPOP_MIN = "logic.sigpop.min";
function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
function lsSet(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* 막힌 저장소 */ } }
function sigItem(page, sheet, x, extra, off) {
  const v = x.value == null ? 1 : x.value;
  const what = x.kind === "block" || x.kind === "net"
    ? `${esc(FUNC_KO[x.func] || x.func || (x.kind === "net" ? "선" : "블록"))}${x.label ? " " + esc(x.label) : ""}${x.kind === "net" ? " 출력 선" : ""}`
    : `${x.row}행 ${esc(x.desc || "(설명 없음)")}`;
  return `<li data-page="${page}" data-sheet="${esc(sheet)}" ${x.row ? `data-row="${x.row}" data-side="${esc(x.side || "L")}"` : ""}
    class="${page === L.page ? "cur" : ""}"><span class="v${v}">${v}</span><span class="sp-sh">${esc(sheet)}</span> <span class="sp-what">${what}${extra || ""}</span>${
    off ? `<button class="sp-off" data-off="${esc(x.key)}" title="이 신호를 끕니다 (강제 풀기 — 도면이 정한 값으로 돌아갑니다)">끄기</button>` : ""}</li>`;
}
function renderSigPop() {
  const pop = $("#sigpop");
  if (!pop) return;
  const tg = $("#sig-toggle");
  const pages = L.mode === "sim" ? (L.chain || []) : [];
  const nUser = pages.reduce((a, c) => a + (c.forced || []).length, 0);
  const open = L.mode === "sim" && lsGet(SIGPOP_CLOSED) !== "1" && (nUser > 0 || L.sigWanted);
  pop.hidden = !open;
  if (tg) tg.classList.toggle("on", open);
  if (!open) return;
  pop.classList.toggle("min", lsGet(SIGPOP_MIN) === "1");
  $("#sigpop-min").textContent = pop.classList.contains("min") ? "＋" : "－";
  const order = [...pages].sort((a, b) => (a.hop ?? 99) - (b.hop ?? 99) || a.page - b.page);
  const forced = [], chained = [], outs = [], stops = [];
  let nOut = 0;
  for (const c of order) {
    const sh = c.sheet_no || "p" + c.page;
    for (const x of c.forced || []) forced.push(sigItem(c.page, sh, x, "", true));
    for (const x of c.chained || []) chained.push(sigItem(c.page, sh, x, ` <small>(뒤 시트 출력 조건)</small>`));
    if (c.hop == null) continue;           // 아무것도 안 줘도 1 인 장(입력 0 의 NOT 등)은 결과로 세지 않는다
    for (const x of c.outputs || []) {
      const to = x.ref ? ` <span class="sp-to">→ TO ${esc(x.ref)}</span>` : ` <span class="sp-end">· 최종 출력 (TO 없음)</span>`;
      outs.push(sigItem(c.page, sh, { ...x, value: 1, kind: "row" }, to));
      nOut++;
    }
    // 신호가 닿았는데 출력이 안 나간 장 — 받은 입력을 적고 거기서 머문다고 말한다
    if (c.hop > 0 && !(c.outputs || []).length)
      for (const x of c.inputs || [])
        stops.push(sigItem(c.page, sh, { ...x, value: 1, kind: "row" }, ` <span class="sp-no">· 출력 없음</span>`));
  }
  const unmet = (L.unmet || []).map((u) => {
    const b = (L.sheet && L.sheet.blocks[u.block]) || {};
    const name = FUNC_KO[b.func] || b.func || (u.logic || "게이트").toUpperCase();
    return `<li data-page="${L.page}"><span class="v0">0</span><span class="sp-sh">${esc((L.sheet || {}).sheet_no || "")}</span>
      <span class="sp-no">${esc(name)} 출력 ${u.want} 이 나가지 않음</span> — ${esc(gateNeedText(u.logic, u.want))}</li>`;
  });
  const sec = (h, sub, items, empty) => `<h4>${h} <small>${sub}</small></h4>` +
    (items.length ? `<ul>${items.join("")}</ul>` : `<div class="sp-empty">${empty}</div>`);
  $("#sigpop-b").innerHTML =
    sec("내가 준 신호", `${forced.length}개 · 모든 시트`, forced, "아직 준 신호가 없습니다 — 입력 행의 동그라미를 눌러 1 을 주세요.") +
    (chained.length ? sec("줄줄이 켬", `${chained.length}개 · 자동`, chained, "") : "") +
    (unmet.length ? sec("나가지 않은 출력", `${unmet.length}개 · 이 시트`, unmet, "") : "") +
    sec("나간 출력", `${nOut}개 · 1 인 출력 행`, outs, "아직 1 이 된 출력 행이 없습니다.") +
    (stops.length ? sec("신호가 닿았지만 멈춘 곳", `${stops.length}개 · 그 시트 게이트 조건이 아직 안 맞음`, stops, "") : "") +
    `<div class="sp-foot">항목을 누르면 그 시트 그 행으로 갑니다 · 오른쪽 '끄기' 로 그 신호만 풉니다 (다른 시트에 있어도).</div>`;
  $("#sigpop-sum").textContent = `신호 ${forced.length} → 출력 ${nOut}`;
  placeSigPop();
}
/* 다른 시트에서 준 신호도 이 창에서 끈다 — 그 시트로 가지 않고 강제만 푼다 (사람이 준 값을 지우면 도면이 정한 값) */
function unforce(page, key) {
  const f = L.allForces[page];
  if (!f || !(key in f)) return;
  delete f[key];
  if (page === L.page) L.forces = f;
  const s = (L.chain || []).find((c) => c.page === page);
  status(`${(s && s.sheet_no) || "p" + page} 의 신호를 껐습니다 — 남은 신호로 다시 돌립니다`);
  runSim(false);
}
function placeSigPop(x, y) {
  const pop = $("#sigpop");
  if (x == null) {
    try { [x, y] = JSON.parse(lsGet(SIGPOP_POS) || "null") || []; } catch (e) { x = y = null; }
    if (x == null) { x = innerWidth - 420 - 340; y = 110; }
  }
  const w = pop.offsetWidth || 380, h = pop.querySelector(".sp-h").offsetHeight || 30;
  x = Math.max(4, Math.min(x, innerWidth - w - 4));
  y = Math.max(4, Math.min(y, innerHeight - h - 4));
  pop.style.left = x + "px"; pop.style.top = y + "px";
  return [x, y];
}
function bindSigPop() {
  const pop = $("#sigpop"), head = $("#sigpop-h");
  if (!pop) return;
  head.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button")) return;
    const r = pop.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    head.setPointerCapture(e.pointerId);
    const move = (ev) => placeSigPop(ev.clientX - dx, ev.clientY - dy);
    const up = () => {
      head.removeEventListener("pointermove", move); head.removeEventListener("pointerup", up);
      const q = pop.getBoundingClientRect();
      lsSet(SIGPOP_POS, JSON.stringify([Math.round(q.left), Math.round(q.top)]));
    };
    head.addEventListener("pointermove", move); head.addEventListener("pointerup", up);
  });
  $("#sigpop-x").onclick = () => { lsSet(SIGPOP_CLOSED, "1"); L.sigWanted = false; renderSigPop(); };
  $("#sigpop-min").onclick = () => { lsSet(SIGPOP_MIN, pop.classList.contains("min") ? null : "1"); renderSigPop(); };
  $("#sig-toggle").onclick = () => {
    if (!pop.hidden) { lsSet(SIGPOP_CLOSED, "1"); L.sigWanted = false; renderSigPop(); return; }
    lsSet(SIGPOP_CLOSED, null); L.sigWanted = true;
    if (L.mode !== "sim") setMode("sim"); else renderSigPop();
  };
  $("#sigpop-b").addEventListener("click", (e) => {
    const off = e.target.closest("button[data-off]");
    if (off) { e.stopPropagation(); unforce(Number(off.closest("li").dataset.page), off.dataset.off); return; }
    const li = e.target.closest("li[data-page]");
    if (!li) return;
    if (li.dataset.row) goToRef(li.dataset.sheet, Number(li.dataset.row), li.dataset.side || "L");
    else if (Number(li.dataset.page) !== L.page) openSheet(Number(li.dataset.page));
  });
  addEventListener("resize", () => { if (!pop.hidden) placeSigPop(); });
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
      ${TIMER_LOGIC.has(b.logic) ? (() => { const ts = timerSec(L.sel.block); return `<tr><td>시간</td><td><b>${fmtSec(ts.sec)}</b> <small>${ts.src === "user" ? "사람이 바꿈" : ts.src === "drawing" ? "도면 " + esc(b.param.text || "") : "도면에 없음 — 기본"}</small> <button data-timer="${esc(L.sel.block)}">시간 바꾸기</button></td></tr>`; })()
        : b.param.text ? `<tr><td>시간</td><td>${esc(b.param.text)}</td></tr>` : ""}
      <tr><td>단자</td><td>들어옴 ${ins.length} · 나감 ${outs.length}</td></tr>
      ${L.mode === "sim" && b.func === "MEMORY" ? `<tr><td>상태</td><td>${valTag(mem || 0)}</td></tr>` : ""}
      ${L.mode === "sim" && GATE_LOGIC.has(b.logic) ? `<tr><td>단자 값</td><td>${portValuesText(L.sel.block)}</td></tr>` : ""}
      ${L.mode === "sim" && L.short && L.short.has(L.sel.block) ? `<tr><td>입력</td><td class="warn">도면에서 입력을 다 읽지 못했습니다 — 범례 조건을 확인할 수 없어 출력을 내지 않습니다</td></tr>` : ""}
      ${L.mode === "sim" && tim ? `<tr><td>타이머</td><td>출력 ${valTag(tim.out)} ${tim.due ? "· 진행 중" : ""}</td></tr>` : ""}
      ${b.func === "STEP" ? `<tr><td>주의</td><td>근사 모델: C_STEP = STEP_IN · STEP_OUT = STEP_IN AND CRIT</td></tr>` : ""}
      ${b.func === "MACRO" ? macroRowsHtml(L.sel.block) : ""}
    </table>
    ${b.func === "MACRO" && (b.macro || {}).page ? `<div class="acts"><button data-macro="${esc(L.sel.block)}">↗ 내부 동작 보기 (새 창) — ${esc(b.macro.sheet)}</button></div>` : ""}
    ${b.func === "MEMORY" ? latchTableHtml(L.sel.block) : ""}
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
    ? "<b>동작 시뮬레이션</b> — 모든 선은 디지털 1/0 입니다. 왼쪽 입력 행의 점, 누름단추(PB), 또는 아무 선이나 누르면 작은 메뉴가 뜹니다 — <b>1 활성</b> / <b>0 비활성</b> / 강제 풀기. 활성인 선만 <b>형광 파랑</b>으로 보이고, 게이트는 범례 G003 정의대로 조건이 맞을 때만 뒤 신호를 내보냅니다 (예: AND 는 입력이 모두 1 · NOT 은 입력 0 이면 1). 출력 행이 1 이 되면 그 행을 FM 으로 받는 <b>다른 장의 입력도 1</b> 이 되고 그 장의 로직도 이어서 돕니다 — 오른쪽 '활성 연결' 에서 그 장으로 갑니다. 타이머는 시간이 흐르는 모습을 아래에 보입니다. 출력 행 동그라미나 오른쪽 출력 행의 <b>⚡예시</b> 를 누르면 그 출력까지 <b>입력부터 최종 출력까지 모든 신호가 서는 입력 조합</b>을 찾아 흐름을 보여 줍니다."
    : "<b>연결 따라가기</b> — 선이나 블록, 행 점을 누르면 그 신호가 어디로 가는지 주황색으로 이어 그립니다. 게이트의 다른 입력이 활성이 아니어도 연결을 따라 끝까지 갑니다 (게이트 조건은 동작 시뮬레이션이 지킵니다). <b>Shift</b>+누름은 거슬러 올라갑니다 (어디서 오는지). 행 동그라미(입력·출력)를 누르면 <b>1 활성 / 0 비활성</b>을 고릅니다 — 출력 행이 1 이면 그 행의 TO·FM 으로 이어진 다른 시트로 계속 이어집니다.";
  $("#legend").innerHTML = sim
    ? `<span><i style="background:var(--active);box-shadow:0 0 4px var(--active-glow)"></i>1 활성</span><span><i style="background:transparent;border:1px dashed #ccc"></i>0 — 표시 없음</span><span><i style="background:rgba(0,180,255,.35)"></i>켜진 메모리·타이머</span>`
    : `<span><i style="background:var(--trace)"></i>따라가는 신호</span><span><i style="background:var(--trace-up)"></i>거슬러 올라감</span><span><i style="background:rgba(47,91,216,.5)"></i>읽은 선</span><span><i style="background:var(--unk)"></i>판정 못 한 블록</span>`;
}

/* ------------------------------------------------------------------ 게이트 단자 1/0 · S-R 래치 표 (L8)

   시뮬레이션에서 활성 신호가 지나는 게이트의 앞(입력)·뒤(출력) 단자마다 1/0 을 적는다.
   값은 화면이 지금 그리는 L.values 그대로라 흐르는 모습(애니메이션)과 같이 움직인다.
   '모든 게이트' 를 켜면 활성이 아닌 게이트도 적는다.  S-R(메모리)은 진리표에 지금 줄을 칠한다. */

const GATE_LOGIC = new Set(["and", "nand", "or", "nor", "not", "memory", "delay_on", "delay_off", "pulse", "step"]);
function portVal(p) { return L.values[p.net] === 1 ? 1 : 0; }
function latchState(bid) {
  const s = L.sheet;
  const ps = s.ports.filter((p) => p.block === bid);
  const S = ps.some((p) => p.dir === "in" && p.role === "set" && portVal(p) === 1) ? 1 : 0;
  const R = ps.some((p) => p.dir === "in" && p.role === "reset" && portVal(p) === 1) ? 1 : 0;
  const Q = L.state && L.state.mem && L.state.mem[bid] === 1 ? 1 : 0;
  const dom = (s.blocks[bid].param || {}).dominant || "";
  return { S, R, Q, dom };
}
function latchRows(dom) {
  // 범례 G003 의 메모리 정의 — S·R 둘 다 1 이면 우선 칸이 정한다 (우선 없음: 그대로 둔다)
  return [
    { S: 0, R: 0, q: "유지", why: "그대로" },
    { S: 1, R: 0, q: "1", why: "SET" },
    { S: 0, R: 1, q: "0", why: "RESET" },
    { S: 1, R: 1, q: dom === "set" ? "1" : dom === "reset" ? "0" : "유지", why: dom === "set" ? "SET 우선" : dom === "reset" ? "RESET 우선" : "우선 없음" },
  ];
}
function latchTableHtml(bid) {
  const st = latchState(bid);
  const sim = L.mode === "sim";
  const rows = latchRows(st.dom).map((r) => {
    const cur = sim && r.S === st.S && r.R === st.R;
    const q = cur && r.S === 0 && r.R === 0 ? `${r.q} (=${st.Q})` : r.q;   // 유지 줄은 지금 붙든 값을 함께
    return `<tr class="${cur ? "cur" : ""}"><td>${r.S}</td><td>${r.R}</td><td>${esc(q)}</td><td>${esc(r.why)}</td></tr>`;
  }).join("");
  return `<table class="latch"><tr><th>S</th><th>R</th><th>Q</th><th></th></tr>${rows}</table>
    <p class="latch-q">${sim ? `지금: S=${st.S} · R=${st.R} → <b>Q=${st.Q}</b>` : "동작 시뮬레이션에서 지금 값이 칠해집니다."}</p>`;
}
function renderLatches() {
  const box = $("#latches");
  if (!box || !L.sheet) return;
  const mems = Object.entries(L.sheet.blocks).filter(([, b]) => b.func === "MEMORY");
  $("#latch-h").hidden = box.hidden = !mems.length;
  if (!mems.length) { box.innerHTML = ""; return; }
  box.innerHTML = mems.map(([bid, b]) => {
    const st = latchState(bid);
    const dom = b.param.dominant === "set" ? "SET 우선" : b.param.dominant === "reset" ? "RESET 우선" : "기본";
    return `<div class="latch-card${L.mode === "sim" && (st.Q || st.S || st.R) ? " live" : ""}${L.sel && L.sel.block === bid ? " sel" : ""}" data-latch="${esc(bid)}">
      <div class="lc-h"><b>${esc(bid)}</b> <small>${dom}</small>${L.mode === "sim" ? ` <span class="val v${st.Q}">Q ${st.Q}</span>` : ""}</div>
      ${latchTableHtml(bid)}</div>`;
  }).join("");
}
function macroRowsHtml(bid) {
  const b = L.sheet.blocks[bid], m = b.macro || {};
  if (!m.page) return `<tr><td>Typical</td><td class="warn">${esc(m.why || "찾지 못함")}</td></tr>`;
  const v = macroView(bid) || { inputs: {}, outputs: {} };
  const row = (x, side) => `<tr><td>${esc(x.pin || "?")}</td><td>${x.row ? `${esc(m.sheet)}-${x.row} ${esc(x.desc)}` : `<span class="warn">연결 못 함</span>`}${
    L.mode === "sim" && x.row ? " " + valTag((side === "in" ? v.inputs : v.outputs)[x.row]) : ""}</td></tr>`;
  return `<tr><td>이름</td><td>${esc(b.caption || "")}</td></tr>
    <tr><td>Typical</td><td><b>${esc(m.sheet)}</b> ${esc(m.title || "")}</td></tr>
    <tr><td colspan="2"><small>입력 단자 → 그 시트의 입력 행</small></td></tr>${(m.inputs || []).map((x) => row(x, "in")).join("")}
    <tr><td colspan="2"><small>그 시트의 출력 행 → 출력 단자</small></td></tr>${(m.outputs || []).map((x) => row(x, "out")).join("")}`;
}
function portValuesText(bid) {
  const ps = L.sheet.ports.filter((p) => p.block === bid);
  const ins = ps.filter((p) => p.dir === "in").map((p) => `${p.role ? p.role.toUpperCase() + " " : ""}${portVal(p)}`);
  const outs = ps.filter((p) => p.dir === "out").map((p) => `${p.role ? p.role.toUpperCase() + " " : ""}${portVal(p)}`);
  return `입력 ${esc(ins.join(" · ") || "없음")} → 출력 ${esc(outs.join(" · ") || "없음")}`;
}
function drawSimMarks() {
  const g = $("#g-sim");
  if (!g) return;
  g.innerHTML = "";
  if (L.mode !== "sim" || !L.sheet) return;
  const s = L.sheet;
  const showAllGates = $("#show-all-gates") && $("#show-all-gates").checked;
  const showVals = !$("#show-ports") || $("#show-ports").checked;
  const showTables = !$("#show-latch") || $("#show-latch").checked;
  const P = s.pitch || 11.5;
  const fs = Math.max(2.4, Math.min(4.6, P * 0.34));     // 글자 크기 = 행 간격의 비율 (절대 pt 아님)
  const byBlock = {};
  for (const p of s.ports) (byBlock[p.block] = byBlock[p.block] || []).push(p);
  // L15 — 타이머 블록마다 지금 쓰는 시간 (사람이 바꾼 값은 ✎) — 누르면 바꾼다
  for (const [bid, b] of Object.entries(s.blocks)) {
    if (!TIMER_LOGIC.has(b.logic) || L.count[bid]) continue;
    const ts = timerSec(bid);
    const [x0, , x1, y1] = b.bbox;
    const tx = el("text", { x: (x0 + x1) / 2, y: y1 + fs * 1.3, "font-size": fs * 0.95, class: "tsec " + ts.src }, g);
    tx.textContent = `t=${fmtSec(ts.sec)}${ts.src === "user" ? " ✎" : ts.src === "default" ? " (기본)" : ""}`;
  }
  for (const [bid, ps] of Object.entries(byBlock)) {
    const b = s.blocks[bid];
    if (!b || !GATE_LOGIC.has(b.logic)) continue;
    const live = ps.some((p) => portVal(p) === 1) || (b.logic === "memory" && latchState(bid).Q === 1);
    if (!live && !showAllGates) continue;
    if (showVals) {
      for (const p of ps) {
        const v = portVal(p);
        const w = fs * 1.15, h = fs * 1.2, pad = fs * 0.25;
        const x = p.dir === "in" ? p.at[0] - pad - w : p.at[0] + pad;
        const y = p.at[1] - h - fs * 0.15;
        const gg = el("g", { class: "pv v" + v }, g);
        el("rect", { x, y, width: w, height: h, rx: fs * 0.25 }, gg);
        const t = el("text", { x: x + w / 2, y: y + h * 0.8, "font-size": fs }, gg);
        t.textContent = String(v);
        el("title", {}, gg).textContent = `${FUNC_KO[b.func] || b.func} ${p.dir === "in" ? "입력" : "출력"}${p.role ? " " + p.role.toUpperCase() : ""} = ${v}`;
      }
    }
    if (b.logic === "memory" && showTables && (live || showAllGates)) drawLatchTable(g, bid, fs);
  }
}
function drawLatchTable(g, bid, fs) {
  const b = L.sheet.blocks[bid];
  const st = latchState(bid);
  const rows = latchRows(st.dom);
  const cw = [fs * 1.3, fs * 1.3, fs * 2.9], ch = fs * 1.35;
  const W = cw[0] + cw[1] + cw[2], H = ch * (rows.length + 1);
  const [x0, y0] = b.bbox;
  const x = x0, y = y0 - 6.2 - H;                         // 블록 이름표(위 5.6) 바로 위
  const gg = el("g", { class: "lt" }, g);
  el("rect", { x, y, width: W, height: H, class: "lt-bg" }, gg);
  const head = ["S", "R", "Q"];
  const cells = [head, ...rows.map((r) => [String(r.S), String(r.R), r.S === st.S && r.R === st.R && !r.S && !r.R ? `${r.q}=${st.Q}` : r.q])];
  cells.forEach((row, i) => {
    const cy = y + ch * i;
    const cur = i > 0 && rows[i - 1].S === st.S && rows[i - 1].R === st.R;
    if (cur) el("rect", { x, y: cy, width: W, height: ch, class: "lt-cur" }, gg);
    let cx = x;
    row.forEach((txt, j) => {
      const t = el("text", { x: cx + cw[j] / 2, y: cy + ch * 0.75, "font-size": fs * (j === 2 && txt.length > 1 ? 0.8 : 0.9), class: i === 0 ? "lt-h" : "" }, gg);
      t.textContent = txt;
      cx += cw[j];
    });
    if (i > 0) el("line", { x1: x, y1: cy, x2: x + W, y2: cy, class: "lt-ln" }, gg);
  });
  el("line", { x1: x + cw[0], y1: y, x2: x + cw[0], y2: y + H, class: "lt-ln" }, gg);
  el("line", { x1: x + cw[0] + cw[1], y1: y, x2: x + cw[0] + cw[1], y2: y + H, class: "lt-ln" }, gg);
  el("title", {}, gg).textContent = `S-R 래치 ${bid} — 지금 S=${st.S} · R=${st.R} → Q=${st.Q}`;
}

/* ------------------------------------------------------------------ 전체창 보기 (L8 · P&ID hotfix64 와 같은 생각) */

function setFull(on) {
  document.body.classList.toggle("lg-full", on);
  $("#full").textContent = on ? "⤢ 전체창 끝" : "⛶ 전체창";
  if (on && document.documentElement.requestFullscreen && !document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});   // 허락 안 되면 화면 안 전체창만
  }
  if (!on && document.fullscreenElement) document.exitFullscreen().catch(() => {});
  setTimeout(() => { if (L.sheet) fit(); }, 60);
}

/* ------------------------------------------------------------------ 메모 · 핀 메모 (L8 · P&ID hotfix63/76/77 과 같은 규율)

   장마다 메모를 쌓는다 (지우지 않는다 — 고치면 앞 글은 이력, '완료'·'숨김' 은 표시뿐).
   📌 를 누르고 도면을 한 번 누르면 그 자리에 핀 — 메모를 누르면 그 자리로 가서 핀이 두 번 깜박인다. */

function currentAuthor() {
  const q = new URLSearchParams(location.search).get("user");
  if (q && q.trim()) return q.trim();
  try { return (localStorage.getItem("pid.author") || "").trim(); } catch (e) { return ""; }
}
function rememberAuthor(name) { try { localStorage.setItem("pid.author", name); } catch (e) { /* 막힌 저장소 */ } }
async function loadMemos(job) {
  try {
    const m = await api(`/logic/api/jobs/${job}/memo`);
    if (L.job !== job) return;
    L.memos = m.items || [];
  } catch (e) { L.memos = []; }
  renderMemo(); renderSheetList(); if (L.sheet) drawPins();
}
function memoCount(page) { return L.memos.filter((m) => m.page === page && !m.hidden && !m.done).length; }
function pageMemos() {
  const showHidden = $("#memo-hidden") && $("#memo-hidden").checked;
  return L.memos.filter((m) => L.sheet && m.page === L.sheet.page && (showHidden || !m.hidden));
}
function pinNo(m) {
  const pins = L.memos.filter((x) => L.sheet && x.page === L.sheet.page && x.at && !x.hidden);
  return pins.indexOf(m) + 1;
}
function renderMemo() {
  const box = $("#memo-list");
  if (!box) return;
  const who = currentAuthor();
  $("#memo-author").hidden = !!who;
  $("#memo-who").textContent = who ? `작성자 ${who}` : "작성자 이름을 적어 주세요 (한 번만)";
  const pinBtn = $("#memo-pin");
  pinBtn.classList.toggle("on", L.pinMode || !!L.pendingAt);
  pinBtn.textContent = L.pendingAt ? "📌 자리 지정됨 (Esc 취소)" : L.pinMode ? "📌 도면을 누르세요" : "📌 핀 메모";
  $("#memo-save").textContent = L.memoEdit ? "고친 글 저장" : "저장";
  const items = pageMemos();
  $("#memo-count").textContent = items.length ? `${items.length}건` : "";
  if (!L.sheet) { box.innerHTML = ""; return; }
  box.innerHTML = items.length ? items.slice().reverse().map((m) => {
    const n = m.at ? pinNo(m) : 0;
    return `<li data-memo="${esc(m.id)}" class="${m.done ? "done" : ""}${m.hidden ? " hid" : ""}${L.memoFlash === m.id ? " flash" : ""}">
      <div class="mh">${n ? `<span class="pinno" title="도면 위 핀 번호">${n}</span>` : ""}<b>${esc(m.author)}</b> <small>${esc(m.time)}${m.history && m.history.length ? ` · 고친 이력 ${m.history.length}` : ""}</small></div>
      <div class="mt">${esc(m.text)}</div>
      <div class="ma"><button data-mact="edit">고치기</button><button data-mact="done">${m.done ? "완료 풀기" : "완료"}</button><button data-mact="hide">${m.hidden ? "다시 보기" : "숨김"}</button></div>
    </li>`;
  }).join("") : `<li class="empty">이 장의 메모가 없습니다.</li>`;
}
function drawPins() {
  const ov = $("#ov");
  if (!ov || !L.sheet) return;
  const old = $("#g-pins");
  if (old) old.remove();
  const g = el("g", { id: "g-pins" }, ov);
  const P = L.sheet.pitch || 11.5;
  const r = Math.max(2.6, P * 0.42);
  const one = (x, y, label, cls, m) => {
    const gg = el("g", { class: "pin " + cls, "data-memo": m ? m.id : "" }, g);
    const hx = x + r * 1.4, hy = y - r * 2.6;          // 바늘 끝 = 메모의 자리
    el("line", { x1: x, y1: y, x2: hx, y2: hy, class: "needle" }, gg);
    el("circle", { cx: hx, cy: hy, r, class: "head" }, gg);
    const t = el("text", { x: hx, y: hy + r * 0.38, "font-size": r * 1.05 }, gg);
    t.textContent = label;
    if (m) {
      el("title", {}, gg).textContent = `${m.author} · ${m.time}\n${m.text}`;
      gg.addEventListener("click", (e) => { e.stopPropagation(); selectMemo(m.id, false); });
      if (L.memoFlash === m.id) gg.classList.add("flash");
    }
  };
  for (const m of L.memos) {
    if (m.page !== L.sheet.page || !m.at || m.hidden) continue;
    one(m.at[0], m.at[1], String(pinNo(m)), m.done ? "done" : "", m);
  }
  if (L.pendingAt) one(L.pendingAt[0], L.pendingAt[1], "+", "pending", null);
}
function setPinMode(on) {
  L.pinMode = on;
  $("#stage").classList.toggle("pinning", on);
  renderMemo();
}
function sheetPoint(e) {
  const r = $("#ov").getBoundingClientRect();
  const [W, H] = L.sheet.size;
  return [Math.round(((e.clientX - r.left) * W / r.width) * 100) / 100, Math.round(((e.clientY - r.top) * H / r.height) * 100) / 100];
}
async function saveMemo() {
  if (!L.sheet) return;
  const text = $("#memo-text").value.trim();
  if (!text) { status("메모 내용을 적어 주세요"); $("#memo-text").focus(); return; }
  let author = currentAuthor();
  if (!author) {
    author = $("#memo-author").value.trim();
    if (!author) { status("작성자 이름을 적어 주세요"); $("#memo-author").focus(); return; }
    rememberAuthor(author);
  }
  try {
    if (L.memoEdit) {
      const m = await api(`/logic/api/jobs/${L.job}/memo/${L.memoEdit}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, author }) });
      L.memos = L.memos.map((x) => (x.id === m.id ? m : x));
    } else {
      const m = await post(`/logic/api/jobs/${L.job}/memo`, { page: L.sheet.page, sheet_no: L.sheet.sheet_no, text, author, at: L.pendingAt });
      L.memos.push(m);
    }
  } catch (err) { status("메모 저장 실패 — " + err.message); return; }
  $("#memo-text").value = "";
  L.memoEdit = null; L.pendingAt = null; setPinMode(false);
  drawPins(); renderMemo(); renderSheetList();
  status("메모를 저장했습니다");
}
async function memoAction(id, act) {
  const m = L.memos.find((x) => x.id === id);
  if (!m) return;
  if (act === "edit") { L.memoEdit = id; $("#memo-text").value = m.text; $("#memo-text").focus(); renderMemo(); return; }
  const author = currentAuthor() || $("#memo-author").value.trim();
  if (!author) { status("작성자 이름을 적어 주세요"); $("#memo-author").focus(); return; }
  const body = act === "done" ? { done: !m.done, author } : { hidden: !m.hidden, author };
  try {
    const u = await api(`/logic/api/jobs/${L.job}/memo/${id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    L.memos = L.memos.map((x) => (x.id === id ? u : x));
  } catch (err) { status("메모 고치기 실패 — " + err.message); return; }
  drawPins(); renderMemo(); renderSheetList();
}
/* 메모 ↔ 핀.  fromList: 목록에서 눌렀으면 도면을 그 자리로, 핀에서 눌렀으면 목록을 그 메모로 */
function selectMemo(id, fromList) {
  const m = L.memos.find((x) => x.id === id);
  if (!m) return;
  L.memoFlash = id;
  clearTimeout(L._memoFlashT);
  L._memoFlashT = setTimeout(() => { L.memoFlash = null; drawPins(); renderMemo(); }, 1300);
  const go = () => {
    if (fromList && m.at) {
      const st = $("#stage");
      setZoom(Math.max(L.zoom, 1.6));
      st.scrollLeft = m.at[0] * L.zoom - st.clientWidth / 2;
      st.scrollTop = m.at[1] * L.zoom - st.clientHeight / 2;
    }
    drawPins(); renderMemo();
    if (!fromList) {
      const li = document.querySelector(`#memo-list li[data-memo="${CSS.escape(id)}"]`);
      const box = $("#memo-list");
      if (li && box) box.scrollTop = li.offsetTop - box.offsetTop - 8;
    }
  };
  if (L.sheet && m.page !== L.sheet.page) { L.focus = null; L.afterFit = go; openSheet(m.page); }
  else go();
}
function bindExtras() {
  $("#full").onclick = () => setFull(!document.body.classList.contains("lg-full"));
  document.addEventListener("fullscreenchange", () => { if (!document.fullscreenElement && document.body.classList.contains("lg-full")) setFull(false); });
  for (const id of ["show-ports", "show-latch", "show-all-gates"]) { const c = $("#" + id); if (c) c.onchange = () => drawSimMarks(); }
  $("#memo-save").onclick = saveMemo;
  $("#memo-text").onkeydown = (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); saveMemo(); } };
  $("#memo-pin").onclick = () => {
    if (L.pendingAt || L.pinMode) { L.pendingAt = null; setPinMode(false); drawPins(); return; }
    if (!L.sheet) { status("먼저 시트를 고르세요"); return; }
    setPinMode(true);
  };
  $("#memo-hidden").onchange = renderMemo;
  $("#memo-list").addEventListener("click", (e) => {
    const li = e.target.closest("li[data-memo]");
    if (!li) return;
    const b = e.target.closest("button[data-mact]");
    if (b) { memoAction(li.dataset.memo, b.dataset.mact); return; }
    selectMemo(li.dataset.memo, true);
  });
  $("#latches").addEventListener("click", (e) => {
    const c = e.target.closest("[data-latch]");
    if (!c) return;
    const bid = c.dataset.latch, b = L.sheet.blocks[bid];
    L.sel = { block: bid }; paint(); renderInfo();
    const st = $("#stage");
    setZoom(Math.max(L.zoom, 1.6));
    st.scrollLeft = ((b.bbox[0] + b.bbox[2]) / 2) * L.zoom - st.clientWidth / 2;
    st.scrollTop = ((b.bbox[1] + b.bbox[3]) / 2) * L.zoom - st.clientHeight / 2;
  });
  // 핀 자리 고르기 — 선·블록 누르기보다 먼저 (붙잡는 단계)
  $("#stage").addEventListener("click", (e) => {
    if (!L.pinMode || L.justPanned || !L.sheet) return;
    e.stopPropagation(); e.preventDefault();
    L.pendingAt = sheetPoint(e);
    setPinMode(false);
    drawPins(); renderMemo();
    $("#memo-text").focus();
    status("자리를 골랐습니다 — 메모 내용을 적고 저장하세요 (Ctrl+Enter)");
  }, true);
}

/* ------------------------------------------------------------------ 이벤트 */

function bind() {
  $("#job").onchange = (e) => { if (e.target.value) { hideHome(); openJob(e.target.value); } else showHome(); };
  $("#sheet-filter").oninput = renderSheetList;
  $("#ft-report").onclick = () => showFromTo();
  $("#ft-modal").onclick = (e) => {
    if (e.target.id === "ft-modal" || e.target.id === "ft-close") { closeFromTo(); return; }
    const tr = e.target.closest("tr[data-ft]");
    if (tr && L.ftReport) {
      const x = L.ftReport.items[Number(tr.dataset.ft)];
      closeFromTo();
      goToRef(x.sheet_no, x.row, x.side);
    }
  };
  $("#remind").onclick = (e) => {
    if (e.target.closest(".rm-x")) { $("#remind").hidden = true; return; }
    const b = e.target.closest("button[data-go]");
    if (!b) return;
    const d = (L.design || [])[Number(b.closest("li").dataset.i)];
    if (!d) return;
    if (b.dataset.go === "src") goToRef(d.sheet_no, d.at_row || d.row, d.side === "L" ? "L" : "R");
    else goToRef(d.target_sheet, d.target_row, "L");
  };
  $("#samples").onclick = async (e) => {
    const n = e.target.dataset.sample;
    if (!n) return;
    try { const r = await post("/logic/api/jobs/sample", { name: n }); await loadJobs(r.id); }
    catch (err) { status("샘플 실패 — " + err.message); }
  };
  $("#mode").onclick = (e) => {
    const m = e.target.dataset.mode;
    if (m) setMode(m);
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
  $("#reset").onclick = resetAll;
  bindSigPop();
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
    const tb = e.target.closest("button[data-timer]");
    if (tb) { timerMenu(tb.dataset.timer, e); return; }
    const mb = e.target.closest("button[data-macro]");
    if (mb) { openMacro(mb.dataset.macro); return; }
    const dg = e.target.closest("#design-err button[data-go]");
    if (dg) {
      const d = (L.design || [])[Number(dg.closest("li").dataset.i)];
      if (d && dg.dataset.go === "src") goToRef(d.sheet_no, d.at_row || d.row, "R");
      else if (d) goToRef(d.target_sheet, d.target_row, "L");
      return;
    }
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
  window.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (document.querySelector("#force-menu")) { closeForceMenu(); return; }
    if (L.pinMode || L.pendingAt) { setPinMode(false); L.pendingAt = null; drawPins(); renderMemo(); return; }
    stopAnim();
    if (document.body.classList.contains("lg-full")) setFull(false);
  });
  bindExtras();
}

bind();
bindHome();
initPan();
renderHelp();
loadJobs().catch((e) => status(e.message));
