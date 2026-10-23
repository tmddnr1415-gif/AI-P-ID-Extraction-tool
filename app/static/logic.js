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
  timers: {}, defaultT: 5, count: {}, choices: [],              // L15 — 사람이 바꾼 타이머 시간 {쪽: {블록: 초}} · 세는 중인 타이머
  analog: {}, analogRes: {}, analogGiven: {},                    // L26 — 사람이 준 아날로그 값 {쪽: {키: 수}} · 그 결과
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
  VOTE: "투표 (B 개 중 A 개)", CONST: "언제나 같은 값", ANALOG: "아날로그 연산 (이진 아님)",
  DISPLAY: "상태 표시 (받기만)", "PUSH BUTTON": "누름단추",
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

/* L41 — 듀얼 모니터: 검토 결과 창 (pane=review) · 그룹 시험 창이 이 창과 신호를 주고받는다 */
const PANE_REVIEW = /[#&]pane=review(&|$)/.test(location.hash);
const WINS = { review: null, gt: null };
function logicWin() {                     // 검토 결과 창 · 그룹 시험 창이 가리키는 LOGIC 창
  if (window.opener && !window.opener.closed) {
    try { if (window.opener.location.origin === location.origin && /^\/logic\/?$/.test(window.opener.location.pathname)) return window.opener; } catch (e) {}
  }
  return WINS.logic && !WINS.logic.closed ? WINS.logic : null;
}
function tellLogic(msg, fallbackHash) {   // 이어진 LOGIC 창에 보낸다 · 없으면 새 LOGIC 창을 그 자리로 연다
  const w = logicWin();
  if (w) { w.postMessage(msg, location.origin); try { w.focus(); } catch (e) {} return true; }
  if (fallbackHash) WINS.logic = window.open(`/logic${location.search}#${fallbackHash}`, `logic-main-${msg.job}`);
  return false;
}
function popReview() {
  if (!L.job) return;
  const w = window.open(`/logic${location.search}#job=${L.job}&pane=review`, `logic-review-${L.job}`, "width=1400,height=950");
  if (!w) { status("새 창을 열지 못했습니다 — 브라우저의 팝업 차단을 풀어 주세요"); return; }
  WINS.review = w; $("#rv-modal").hidden = true;
  status("검토 결과를 새 창으로 열었습니다 — 항목을 누르면 이 창이 그 자리로 갑니다");
}
function popGroupTest(job) {
  job = job || L.job;
  const w = window.open(`/logic/test${location.search}${job ? "#job=" + job : ""}`, `logic-gt-${job || "home"}`, "width=1500,height=950");
  if (!w) { location.href = `/logic/test${location.search}${job ? "#job=" + job : ""}`; return; }
  WINS.gt = w;
}
/* 다른 창에서 온 요청 — 그 묶음이 아니면 그 묶음을 연다 (hash 에 할 일을 적어 openJob 이 이어 한다) */
async function fromOtherWindow(d) {
  if (d.type === "review-on") { RV.on = !!d.on; lsSet("logic.rvon", RV.on ? "1" : "0"); if (L.sheet) drawOverlay(); return; }
  if (d.type === "review-marks") { if (d.job === L.job) loadReview(L.job); return; }
  if (!/^[0-9a-f]{12}$/.test(d.job || "")) return;
  try { window.focus(); } catch (e) {}
  const want = d.type === "review-go" ? `rvgo=${Number(d.id)}`
    : d.type === "goto" ? `page=${Number(d.page) || ""}&row=${Number(d.row) || ""}&side=${d.side === "R" ? "R" : "L"}${d.key && d.key.startsWith("block:") ? "&blk=" + encodeURIComponent(d.key.slice(6)) : ""}`
    : `page=${Number(d.page) || ""}&test=${encodeURIComponent(d.equip || "")}&chk=${Number(d.chk) || 0}`;
  if (d.job !== L.job || !L.sheets) {
    history.replaceState(null, "", `${location.pathname}${location.search}#job=${d.job}&${want}`);
    hideHome(); $("#job").value = d.job; closeFromTo && closeFromTo();
    await openJob(d.job);
    return;
  }
  if (typeof closeFromTo === "function") closeFromTo();
  if (d.type === "review-go") {
    if (!RV.data) await loadReview(L.job);
    const it = RV.data && RV.data.items.find((x) => x.id === Number(d.id));
    if (it) goReview(it); else status(`검토 항목 ${d.id} 를 찾지 못했습니다 — 검토를 다시 모았을 수 있습니다`);
  } else if (d.type === "goto") goLoc(Number(d.page), Number(d.row) || 0, d.side, d.key || "");
  else applyHashTest(L.job, d.equip, Number(d.chk) || 0);
}
async function startReviewPane() {
  document.body.classList.add("pane-review");
  const id = (location.hash.match(/job=([0-9a-f]{12})/) || [])[1];
  if (!id) { status("묶음이 없습니다"); return; }
  L.job = id;
  document.title = "정합성 검토 결과 — LOGIC";
  await loadReview(id, true);
}

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
  for (const id of ["#ft-report", "#report", "#rv-btn", "#rv-pdf"]) $(id).hidden = true;
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
  api("/logic/api/library").then((lb) => {
    $("#lh-library").innerHTML = `학습 사전 — Signal Processing 기호 <b>${lb.symbols}</b>개 · 그림 기호 ${lb.figures}개 · MACRO Typical <b>${lb.typicals}</b>개`
      + (lb.user_symbols ? ` (사람이 가르친 기호 ${lb.user_symbols}개)` : "")
      + `.  새 프로젝트 Logic 은 그 묶음의 범례가 먼저이고, 범례가 말하지 않은 기호 · 없는 Typical 은 이 사전으로 읽습니다.`;
  }).catch(() => {});
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
  const idr = x.idrate != null ? ` <span class="chip${(x.idrate_low || []).length ? " low" : ""}" title="식별률 — 시트 이름 · FROM/TO 칸 · 연결 · 게이트${(x.idrate_low || []).length ? " (90% 아래 항목 있음 — 열어서 마크업으로 넣으세요)" : ""}">식별 ${(Math.floor(x.idrate * 1000) / 10).toFixed(1)}%</span>` : "";
  const rv = x.review;
  const rvc = rv ? ` <span class="chip rvchip" title="정합성 검토 — 설계 오류 · 설계 확인 · 읽기 빈틈 (툴 판정 ${rv.judged != null ? (rv.judged * 100).toFixed(1) + "%" : "—"})">검토 <b class="e">E${rv.error}</b> <b class="c">C${rv.check}</b> <b class="g">G${rv.gap}</b></span>` : "";
  const st = x.state === "done" ? `<span class="ok">● 완료</span> <span class="chip">${x.sheets}장</span>${idr}${rvc}`
    : x.state === "failed" ? `<span class="bad">● 실패</span>`
    : `<span class="run">● 분석 중 ${(x.progress && x.progress.percent) || 0}%</span>`;
  return `<li data-job="${x.id}"><div class="jn">${esc(x.name || "")}</div>
    <div class="jm">${st} ${mats.map((k) => `<span class="mat">${esc(lab[k] || k)}</span>`).join("")}
    <span class="when">${fmtDate(x.created)}</span>${x.author ? ` <span class="when">· ${esc(x.author)}</span>` : ""}
    ${x.state === "done" ? `<a class="jgt" href="/logic/api/jobs/${x.id}/review.pdf" title="정합성 검토 결과를 입력 PDF 에 마크업한 파일">📋 검토 PDF</a>` : ""}
    ${x.state === "done" ? `<button class="jgt" data-gt="${x.id}" title="장비(블록 그룹)마다 배운 동작을 원 버튼으로 시험합니다">🧪 그룹 시험</button>` : ""}
    ${x.state === "queued" || x.state === "running" ? "" : `<button class="jdel" data-del="${x.id}" title="이 분석 기록을 지웁니다 (분석 결과 · 메모 · 사람이 정한 값)">지우기</button>`}</div>
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
      <div><b>${esc(p.name)}</b> <span class="lh-mode sm">실행</span><br><small>분석 ${js.length}건${last ? ` · 마지막 ${fmtDate(last.created)} · ${last.sheets}장` : ""}</small></div>
      <button class="pjdel" data-pdel="${esc(p.name)}" title="이 프로젝트와 그 안의 분석 전부를 지웁니다">프로젝트 삭제</button></div>
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
    const pdel = e.target.closest("button[data-pdel]");
    if (pdel) { e.stopPropagation(); deleteProject(pdel.dataset.pdel); return; }
    const del = e.target.closest("button[data-del]");
    if (del) { e.stopPropagation(); deleteJob(del.dataset.del); return; }
    const gt = e.target.closest("button[data-gt]");
    if (gt) { e.stopPropagation(); popGroupTest(gt.dataset.gt); return; }
    const li = e.target.closest("li[data-job]");
    if (!li) return;
    hideHome();
    $("#job").value = li.dataset.job;
    openJob(li.dataset.job);
  });
}

/* L22 — 부서원이 첫 화면에서 분석 기록을 지운다 (분석 중이면 서버가 거절 · 누가 지웠는지 남긴다) */
async function deleteJob(id) {
  const x = (L.jobsList || []).find((j) => j.id === id) || {};
  const ans = await askModal({
    title: "분석 기록 지우기", danger: true, ok: "지우기",
    html: `<p><b>'${esc(x.name || id)}'</b> 분석 기록을 지웁니다.</p>
      <p>분석 결과 · 메모 · 사람이 정한 값(게이트 종류 · FM/TO · 시간)이 함께 지워지고 되돌릴 수 없습니다.</p>`,
    fields: authorField(),
  });
  if (!ans) return;
  const who = takeAuthor(ans);
  try {
    await api(`/logic/api/jobs/${id}?author=${encodeURIComponent(who)}`, { method: "DELETE" });
    status(`'${x.name || id}' 를 지웠습니다 (${who})`);
    if (L.job === id) L.job = null;
  } catch (err) { status("지우지 못했습니다 — " + err.message); }
  loadHome();
}
/* 프로젝트 하나와 그 분석 전부를 지운다 — 함께 지워질 것을 먼저 보이고, 이름을 옮겨 적어야 지운다 */
async function deleteProject(name) {
  let pv;
  try { pv = await api(`/logic/api/projects/${encodeURIComponent(name)}/delete_preview`); }
  catch (err) { status("지우지 못했습니다 — " + err.message); return; }
  if (pv.running.length) {
    await askModal({ title: "프로젝트 삭제", ok: "확인", cancel: false,
      html: `<p><b>'${esc(name)}'</b> 에 분석 중인 묶음이 ${pv.running.length}건 있습니다 — 끝난 뒤에 지우세요.</p>` });
    return;
  }
  const who0 = currentAuthor();
  const others = pv.authors.filter((a) => a !== who0);
  const ans = await askModal({
    title: "프로젝트 삭제", danger: true, ok: "프로젝트 지우기",
    html: `<p>프로젝트 <b>'${esc(name)}'</b> 를 지웁니다.</p>
      <p>함께 지워지는 것: 분석 <b>${pv.jobs}건</b> (${pv.sheets}장) · 메모 · 사람이 정한 값(게이트 종류 · FM/TO · 시간 · 가르치기 답)</p>
      ${others.length ? `<p class="warn">⚠ 다른 사람이 올린 분석이 있습니다: ${esc(others.join(", "))}</p>` : ""}
      <p>되돌릴 수 없습니다.  학습 사전(다른 프로젝트도 쓰는 기호)은 남습니다.</p>`,
    fields: [...authorField(), { id: "confirm", label: "확인하려면 프로젝트 이름을 그대로 적으세요", placeholder: name, mustEqual: name }],
  });
  if (!ans) return;
  const who = takeAuthor(ans);
  try {
    const r = await api(`/logic/api/projects/${encodeURIComponent(name)}?author=${encodeURIComponent(who)}&confirm=${encodeURIComponent(ans.confirm)}`, { method: "DELETE" });
    status(`프로젝트 '${name}' 와 분석 ${r.jobs}건을 지웠습니다 (${who})`);
    try { if (localStorage.getItem("logic.project") === name) localStorage.removeItem("logic.project"); } catch (e) {}
    if ($("#lh-project").value === name) $("#lh-project").value = "";
  } catch (err) { status("지우지 못했습니다 — " + err.message); }
  loadHome();
}
/* 누가 정했는지 남긴다 — 대시보드 로그인 · 기억된 이름, 없으면 한 번 묻는다 */
async function needAuthor() {
  const who = currentAuthor();
  if (who) return who;
  const ans = await askModal({ title: "이름", ok: "확인", html: "<p>누가 정했는지 남깁니다.</p>", fields: authorField() });
  return ans ? takeAuthor(ans) : "";
}
function authorField() {
  return currentAuthor() ? [] : [{ id: "author", label: "이름", placeholder: "이름을 적어 주세요", required: true }];
}
function takeAuthor(ans) {
  if (ans.author) { rememberAuthor(ans.author); return ans.author; }
  return currentAuthor();
}
/* 화면 안 대화상자 — 브라우저의 prompt · confirm · alert 는 대시보드 iframe 에서 막혀
   아무 말 없이 null 을 돌려준다 (회사 PC 에서 '프로젝트 삭제' 가 그래서 안 됐다).
   fields: [{id, label, value, placeholder, required, mustEqual}] → 확인이면 {id: 값}, 취소면 null */
function askModal({ title, html = "", fields = [], ok = "확인", cancel = "취소", danger = false }) {
  return new Promise((resolve) => {
    document.querySelectorAll(".lmodal-back").forEach((n) => n.remove());
    const back = document.createElement("div");
    back.className = "lmodal-back";
    back.innerHTML = `<div class="lmodal" role="dialog" aria-modal="true">
      <h3>${esc(title || "")}</h3><div class="lm-body">${html}</div>
      ${fields.map((f) => `<label class="lm-f"><span>${esc(f.label || "")}</span>
        <input data-f="${esc(f.id)}" value="${esc(f.value || "")}" placeholder="${esc(f.placeholder || "")}" autocomplete="off"></label>`).join("")}
      <div class="lm-err"></div>
      <div class="lm-btns">${cancel === false ? "" : `<button data-m="no">${esc(cancel)}</button>`}
        <button data-m="ok" class="${danger ? "danger" : "primary"}">${esc(ok)}</button></div></div>`;
    document.body.appendChild(back);
    const inputs = [...back.querySelectorAll("input[data-f]")];
    const okBtn = back.querySelector('[data-m="ok"]');
    const vals = () => Object.fromEntries(inputs.map((i) => [i.dataset.f, i.value.trim()]));
    const valid = () => fields.every((f) => {
      const v = vals()[f.id] || "";
      if (f.mustEqual != null) return v === f.mustEqual;
      return !f.required || !!v;
    });
    const refresh = () => { okBtn.disabled = !valid(); };
    const done = (v) => { back.remove(); document.removeEventListener("keydown", key, true); resolve(v); };
    const key = (e) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); done(null); }
      else if (e.key === "Enter" && !e.isComposing) { e.preventDefault(); e.stopPropagation(); if (valid()) done(vals()); }
    };
    document.addEventListener("keydown", key, true);
    inputs.forEach((i) => i.addEventListener("input", refresh));
    back.addEventListener("click", (e) => {
      const m = e.target.closest("[data-m]");
      if (m) { if (m.dataset.m === "ok") { if (valid()) done(vals()); } else done(null); return; }
      if (e.target === back) done(null);
    });
    refresh();
    (inputs[0] || okBtn).focus();
  });
}

async function openJob(id) {
  L.job = id;
  await loadTimers();
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
  const opt = $("#job").querySelector(`option[value="${id}"]`);          // 분석 중에 그린 '분석 중 N%' 를 끝난 값으로
  if (opt && st.sheets != null) opt.textContent = `${st.name || ""} · ${st.sheets}장`;
  const j = await api(`/logic/api/jobs/${id}/sheets`);
  L.sheets = j.sheets;
  $("#basis").innerHTML = `${esc(j.note)}<br><br>배운 글자: ${Object.keys(j.dictionary).map(esc).join(" ")}`;
  renderSheetList();
  $("#goto").disabled = false;
  const rep = $("#report"); rep.hidden = false; rep.href = `/logic/api/jobs/${id}/report.xlsx`;
  L.all = null; L.allSel = null;
  api(`/logic/api/jobs/${id}/findings`).then((f) => { if (L.job === id) { L.all = f; renderAll(); } }).catch(() => {});
  L.memos = [];
  loadMemos(id); aopVocab();
  L.idrate = null; L.idrateOpen = false; loadIdrate();
  // L25 — 질문이 있으면 가르치기 창을 연다 (사람이 닫은 묶음은 다시 열지 않는다 · 분석 중에 열어 둔 창은 그대로)
  const teachOpen = !$("#teach").hidden && TEACH.job === id;
  const fromWin = /[#&](test|rvgo|row|blk)=/.test(location.hash);      // L42 — 다른 창(그룹 시험 · 검토)에서 자리를 짚어 왔으면 창을 덮지 않는다
  loadTeach(id, !fromWin && !MACRO_FROM && (teachOpen || lsGet("logic.teachclosed." + id) !== "1"));
  $("#ft-report").hidden = false;
  RV.data = null; $("#rv-btn").hidden = false; $("#rv-pdf").hidden = false;
  $("#rv-pdf").href = `/logic/api/jobs/${id}/review.pdf?author=${encodeURIComponent(lsGet("pid.author") || "")}`;
  loadReview(id);
  // 사용자 규칙 1 — 신호를 주기 전에 From-To 점검 보고를 먼저 (이 묶음을 처음 열 때 · 방금 분석이 끝났을 때)
  let seen = false;
  try { seen = localStorage.getItem("logic.ftseen." + id) === "1"; } catch (e) {}
  const test = location.hash.match(/[#&]test=([^&]+)/);
  const rvgo = Number((location.hash.match(/[#&]rvgo=(\d+)/) || [])[1]);
  if (!MACRO_FROM && !fromWin && (wasRunning || !seen)) showFromTo(id);
  if (rvgo) {                                  // L41 — 검토 결과 창에서 왔다
    await loadReview(id);
    const it = RV.data && RV.data.items.find((x) => x.id === rvgo);
    if (it) { goReview(it); return; }
  }
  const p = Number((location.hash.match(/page=(\d+)/) || [])[1]) || (L.sheets[0] && L.sheets[0].page);
  const hrow = Number((location.hash.match(/[#&]row=(\d+)/) || [])[1]) || 0;     // L42 — 그룹 시험 창의 '시트-행' 에서 왔다
  const hblk = (location.hash.match(/[#&]blk=([^&]+)/) || [])[1];
  if (p && !test && (hrow || hblk)) { await goLoc(p, hrow, (location.hash.match(/[#&]side=([LR])/) || [])[1], hblk ? "block:" + decodeURIComponent(hblk) : ""); return; }
  if (p) { if (test) { await openSheet(p); applyHashTest(id, decodeURIComponent(test[1])); } else openSheet(p); }
}
/* L42 — 시트 · 행(또는 블록) 자리로 간다.  그룹 시험 창이 신호마다 'BL10_P301-112' 를 누르면 여기로 온다 */
async function goLoc(page, row, side, key) {
  if (!page) return;
  if (row) {
    L.focus = { page, row, side: side || "L", at: Date.now() };
    if (page === L.page && L.sheet) { drawOverlay(); focusRow(); } else await openSheet(page);
    return;
  }
  if (page !== L.page || !L.sheet) await openSheet(page);
  const bid = key && key.startsWith("block:") ? key.slice(6).split("/")[0] : null;
  const b = bid && L.sheet && L.sheet.blocks[bid];
  if (!b) return;
  L.sel = { block: bid }; paint(); renderInfo();
  const st = $("#stage");
  setZoom(Math.max(L.zoom, 1.6));
  st.scrollLeft = ((b.bbox[0] + b.bbox[2]) / 2) * L.zoom - st.clientWidth / 2;
  st.scrollTop = ((b.bbox[1] + b.bbox[3]) / 2) * L.zoom - st.clientHeight / 2;
}
/* L36 — 블록 그룹 시험 대시보드에서 '도면에서 보기' 로 왔을 때: 그 시험 항목의 신호를 그대로 주고 흐름을 그린다 */
async function applyHashTest(id, equip, chk) {
  try { await applyHashTest_(id, equip, chk); }
  catch (e) { console.error(e); status(`시험 신호를 그리지 못했습니다 — ${e.message} (${whereErr(e)})`); }
}
/* L42 — 화면 오류가 어디서 났는지 한 마디 (다음 신고 때 바로 찾게) */
function whereErr(e) {
  const m = /at (\S+) \(.*?logic\.js[^:]*:(\d+)/.exec(String((e && e.stack) || ""));
  return m ? `${m[1]} · ${m[2]}줄` : "위치 모름";
}
async function applyHashTest_(id, equip, chk) {
  const ci = chk != null ? chk : Number((location.hash.match(/[#&]chk=(\d+)/) || [])[1] || 0);
  let r;
  try { r = await api(`/logic/api/jobs/${id}/grouptest?equip=${encodeURIComponent(equip)}`); } catch (e) { status(e.message); return; }
  const c = (r.checks || [])[ci];
  if (!c || id !== L.job) return;
  L.allForces = {};
  for (const [pg, f] of Object.entries(c.forces || {})) L.allForces[Number(pg)] = { ...f };
  const at = c.at || {};
  if (at.page && at.page !== L.page) await openSheet(at.page);
  L.forces = L.allForces[L.page] = L.allForces[L.page] || {};
  L.states = {}; L.state = null; L.values = {};
  setMode("sim", true);
  await runSim(true);
  if (at.row) { L.focus = { page: at.page, row: at.row, side: "R", at: Date.now() }; drawOverlay(); focusRow(); }
  status(`🧪 그룹 시험 '${equip}' — ${c.title} · 기대 ${c.expect} → 결과 ${c.got}`);
  renderChain();
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
    ${st.preview ? `<p class="pg-teach">🎓 지금까지 읽은 <b>${st.preview}</b>장으로 질문을 만들었습니다 — 분석이 도는 동안 답하면
      끝난 결과의 모든 장에 들어갑니다. <button id="pg-teach">가르치기 시작</button></p>` : ""}
  </div>`;
  const tb = $("#pg-teach");
  if (tb) tb.onclick = () => { $("#teach").hidden = false; placeTeach(); loadTeach(L.job, true); };
  if (st.preview && st.preview !== TEACH.seenPreview && !$("#teach").hidden) { TEACH.seenPreview = st.preview; loadTeach(L.job); }
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
      <button class="btn" onclick="closeFromTo();renderReview()">📋 정합성 검토 전체 보기</button>
      <button id="ft-close" class="btn primary">확인 — 신호 주며 로직 보기</button></div>`;
  $("#ft-modal").hidden = false;
}
function closeFromTo() { $("#ft-modal").hidden = true; }

/* ------------------------------------------------------------------ 정합성 검토 결과 한 장 (L39) */
const RV = { data: null, cat: "ALL", topic: "", q: "", on: false, focus: null, poll: null, mk: "" };
const RV_VD = { OK: "맞음", WRONG: "툴 오판", HOLD: "보류" };
const RV_KO = { ERROR: "설계 오류", CHECK: "설계 확인", GAP: "읽기 빈틈", INFO: "참고" };
const RV_TAG = { ERROR: "E", CHECK: "C", GAP: "G", INFO: "I" };
const RV_TOPIC = { fromto: "from-to", line: "선 연결", gate: "게이트", command: "명령 동작", pair: "반대 명령", read: "읽기" };
async function loadReview(id, open) {
  id = id || L.job;
  let r;
  try { r = await api(`/logic/api/jobs/${id}/review`); } catch (e) { status(e.message); return; }
  if (L.job !== id) return;
  RV.data = r;
  const c = r.count || {};
  $("#rv-btn").innerHTML = `📋 정합성 검토 <b class="rv-n e">${c.ERROR || 0}</b><b class="rv-n c">${c.CHECK || 0}</b><b class="rv-n g">${c.GAP || 0}</b>`;
  clearTimeout(RV.poll);
  if (r.learning && r.learning.state === "running") RV.poll = setTimeout(() => L.job === id && loadReview(id), 6000);
  if (open || !$("#rv-modal").hidden) renderReview();
  if (L.sheet) drawOverlay();
}
function rvItems() {
  const r = RV.data;
  if (!r) return [];
  const q = RV.q.trim().toUpperCase();
  const vd = (it) => (it.mark && it.mark.verdict) || "";
  return r.items.filter((it) => (RV.cat === "ALL" ? it.cat !== "INFO" : it.cat === RV.cat) && (!RV.topic || it.topic === RV.topic) &&
    (!RV.mk || (RV.mk === "OPEN" ? !vd(it) : vd(it) === RV.mk)) &&
    (!q || `${it.sheet_no} ${it.title} ${it.text}`.toUpperCase().includes(q)));
}
/* 사람 판단 칸 — 맞음 · 툴 오판 · 보류 (다시 누르면 거둔다) */
function rvMarkCell(it) {
  const v = (it.mark && it.mark.verdict) || "";
  const who = it.mark ? `${it.mark.author || ""}${it.mark.note ? " · " + it.mark.note : ""}` : "";
  return `<td class="rv-mk" title="${esc(who)}">${Object.entries(RV_VD).map(([k, t]) =>
    `<button data-mk="${k}" class="${k.toLowerCase()}${v === k ? " on" : ""}">${t}</button>`).join("")}</td>`;
}
async function rvSetMark(it, verdict) {
  if (it.mark && it.mark.verdict === verdict) verdict = null;
  let note = "";
  if (verdict === "WRONG") {
    const ans = await askModal({ title: "툴 오판", ok: "저장", html: "<p>툴이 잘못 본 까닭을 한 줄로 (비워도 됩니다).</p>",
      fields: [...authorField(), { id: "note", label: "까닭", placeholder: "예: 다른 권의 시트" }] });
    if (!ans) return;
    takeAuthor(ans); note = ans.note || "";
  }
  const author = await needAuthor();
  if (!author) return;
  try {
    const r = await post(`/logic/api/jobs/${L.job}/review/mark`, { keys: [it.key], verdict, author, note });
    it.mark = r.set[it.key] || null;
    if (r.marks) RV.data.marks = r.marks;
    renderReview();
    if (PANE_REVIEW) tellLogic({ type: "review-marks", job: L.job });
    else if (WINS.review && !WINS.review.closed) WINS.review.postMessage({ type: "review-marks", job: L.job }, location.origin);
  } catch (e) { status("판단을 저장하지 못했습니다 — " + e.message); }
}
function renderReview() {
  const r = RV.data;
  if (!r) { loadReview(L.job, true); return; }
  const c = r.count, rate = r.rate, tl = rate.tally || {};
  const learning = r.learning && r.learning.state === "running";
  const items = rvItems();
  const shown = items.slice(0, 600);
  const topics = Object.entries(r.by_topic || {});
  $("#rv-box").innerHTML = `<h2>정합성 검토 결과 <small>${esc(r.name || "")} · ${r.sheets}장</small>
      ${PANE_REVIEW ? `<span class="rv-link ${logicWin() ? "on" : ""}">${logicWin() ? "● LOGIC 창과 이어짐 — 항목을 누르면 그 자리로" : "○ LOGIC 창 없음 — 항목을 누르면 새 LOGIC 창을 엽니다"}</span>`
        : `<button id="rv-pop" class="btn" title="듀얼 모니터 — 검토 결과를 다른 창에 띄우고 항목을 누르면 이 창이 그 자리로 갑니다">⧉ 새 창으로</button>`}</h2>
    <div class="rv-cards">
      <div class="rv-c"><b>${pct(rate.read)}</b><span>도면 읽기</span></div>
      <div class="rv-c"><b>${pct(rate.judged)}</b><span>툴 판정</span></div>
      <div class="rv-c e" data-cat="ERROR"><b>${c.ERROR}</b><span>설계 오류</span></div>
      <div class="rv-c c" data-cat="CHECK"><b>${c.CHECK}</b><span>설계 확인</span></div>
      <div class="rv-c g" data-cat="GAP"><b>${c.GAP}</b><span>읽기 빈틈</span></div>
      ${(() => { const dz = (r.marks || {}).design || {}; return `<div class="rv-c m" title="설계 오류 · 설계 확인 중 사람이 '맞음' 으로 본 비율"><b>${dz.precision != null ? pct(dz.precision) : "—"}</b><span>판단 맞음 ${dz.OK || 0} · 오판 ${dz.WRONG || 0}</span></div>`; })()}
    </div>
    <p class="rv-parts">툴 판정 — ${Object.entries(rate.parts || {}).filter(([, v]) => v != null)
      .map(([k, v]) => `${RV_TOPIC[k] || k} <b>${pct(v)}</b> <small>(${tl[k].done}/${tl[k].all})</small>`).join(" · ")}
      ${learning ? `<br><span class="rv-learn">⏳ 동작 학습 중${r.learning.progress && r.learning.progress.total ? ` ${r.learning.progress.done}/${r.learning.progress.total}` : ""} — 끝나면 명령 · 반대 명령 검토가 더해집니다</span>` : ""}
      ${r.behavior && !r.behavior.learned && !learning ? `<br><span class="rv-learn">명령 · 반대 명령 검토는 동작 학습이 끝난 뒤 더해집니다</span>` : ""}</p>
    <div class="rv-legend"><span class="e">E 설계 오류</span> 도면이 어긋남 · <span class="c">C 설계 확인</span> 의도인지 판단 · <span class="g">G 읽기 빈틈</span> 툴이 다 못 읽음 — 가르치기 · 마크업</div>
    <div class="rv-filter">
      ${["ALL", "ERROR", "CHECK", "GAP", "INFO"].map((k) => `<button data-f="${k}" class="${RV.cat === k ? "on" : ""}">${k === "ALL" ? "모두" : RV_KO[k]} ${k === "ALL" ? c.ERROR + c.CHECK + c.GAP : c[k]}</button>`).join("")}
      <select id="rv-topic"><option value="">주제 전부</option>${topics.map(([k, d]) => `<option value="${k}" ${RV.topic === k ? "selected" : ""}>${RV_TOPIC[k] || k} (${d.ERROR + d.CHECK + d.GAP})</option>`).join("")}</select>
      <input id="rv-q" placeholder="시트 · 낱말 찾기" value="${esc(RV.q)}">
      <select id="rv-mk"><option value="">판단 전부</option>${[["OPEN", "미처리"], ["OK", "맞음"], ["WRONG", "툴 오판"], ["HOLD", "보류"]].map(([k, t]) => `<option value="${k}" ${RV.mk === k ? "selected" : ""}>${t}</option>`).join("")}</select>
      <label class="rv-on"><input type="checkbox" id="rv-on" ${RV.on ? "checked" : ""}> 도면에 표시</label>
    </div>
    <div class="ft-scroll rv-scroll"><table class="ft-t rv-t"><tr><th>번호</th><th>분류</th><th>시트</th><th>제목</th><th>내용</th><th>판단</th></tr>
      ${shown.map((it) => `<tr data-rv="${it.id}" class="${it.cat.toLowerCase()}"><td><b class="rv-tag ${it.cat.toLowerCase()}">${RV_TAG[it.cat]}${it.id}</b></td>
        <td>${RV_KO[it.cat]}<br><small>${RV_TOPIC[it.topic] || it.topic}</small></td><td>${esc(it.sheet_no || "p" + it.page)}</td>
        <td>${esc(it.title)}</td><td><small>${esc(it.text)}</small></td>${rvMarkCell(it)}</tr>`).join("") || `<tr><td colspan="6" class="ft-none">없습니다</td></tr>`}
    </table>${items.length > shown.length ? `<p class="ft-none">앞 ${shown.length}건만 보입니다 — 거르거나 Excel · PDF 로 보세요 (모두 ${items.length}건)</p>` : ""}</div>
    <div class="ft-acts"><a class="btn" href="/logic/api/jobs/${L.job}/review.xlsx">Excel</a>
      <a class="btn primary" href="/logic/api/jobs/${L.job}/review.pdf?author=${encodeURIComponent(lsGet("pid.author") || "")}">검토 PDF 내려받기 (마크업)</a>
      <button id="rv-close" class="btn">${PANE_REVIEW ? "창 닫기" : "닫기"}</button></div>`;
  $("#rv-modal").hidden = false;
}
function bindReview() {
  const box = $("#rv-box");
  $("#rv-btn").onclick = () => renderReview();
  $("#rv-modal").addEventListener("click", (e) => { if (e.target.id === "rv-modal") $("#rv-modal").hidden = true; });
  box.addEventListener("click", (e) => {
    const f = e.target.closest("[data-f]");
    if (f) { RV.cat = f.dataset.f; renderReview(); return; }
    const cd = e.target.closest(".rv-c[data-cat]");
    if (cd) { RV.cat = cd.dataset.cat; renderReview(); return; }
    if (e.target.id === "rv-close") { if (PANE_REVIEW) window.close(); else $("#rv-modal").hidden = true; return; }
    if (e.target.id === "rv-pop") { popReview(); return; }
    const mb = e.target.closest("button[data-mk]");
    if (mb) { const it = RV.data.items.find((x) => x.id === Number(mb.closest("tr").dataset.rv)); if (it) rvSetMark(it, mb.dataset.mk); return; }
    const tr = e.target.closest("tr[data-rv]");
    if (tr) {
      const it = RV.data.items.find((x) => x.id === Number(tr.dataset.rv));
      if (!it) return;
      if (!PANE_REVIEW) { goReview(it); return; }
      RV.focus = { id: it.id, at: Date.now() };
      box.querySelectorAll("tr.cur").forEach((x) => x.classList.remove("cur")); tr.classList.add("cur");
      tellLogic({ type: "review-go", job: L.job, id: it.id }, `job=${L.job}&rvgo=${it.id}`);
    }
  });
  box.addEventListener("change", (e) => {
    if (e.target.id === "rv-topic") { RV.topic = e.target.value; renderReview(); }
    if (e.target.id === "rv-mk") { RV.mk = e.target.value; renderReview(); }
    if (e.target.id === "rv-on") { RV.on = e.target.checked; lsSet("logic.rvon", RV.on ? "1" : "0"); if (L.sheet) drawOverlay();
      if (PANE_REVIEW) tellLogic({ type: "review-on", job: L.job, on: RV.on }); }
  });
  box.addEventListener("input", (e) => {
    if (e.target.id !== "rv-q") return;
    RV.q = e.target.value;
    clearTimeout(RV.qt);
    RV.qt = setTimeout(() => { const pos = e.target.selectionStart; renderReview(); const q = $("#rv-q"); q.focus(); q.setSelectionRange(pos, pos); }, 250);
  });
  RV.on = lsGet("logic.rvon") === "1";
}
/* 검토 항목 하나로 — 그 쪽으로 가서 그 자리를 두르고 깜박인다 */
async function goReview(it) {
  $("#rv-modal").hidden = true;
  RV.focus = { id: it.id, at: Date.now() };
  const look = () => {
    if (!it.rect) return;
    const st = $("#stage");
    const [x0, y0, x1, y1] = it.rect;
    setZoom(Math.max(L.zoom, 1.6));
    st.scrollLeft = ((x0 + x1) / 2) * L.zoom - st.clientWidth / 2;
    st.scrollTop = ((y0 + y1) / 2) * L.zoom - st.clientHeight / 2;
  };
  if (it.page !== L.page) {
    if (L.sheet) { const st = $("#stage"); L.back.push({ page: L.page, zoom: L.zoom, sl: st.scrollLeft, stp: st.scrollTop }); $("#go-back").disabled = false; }
    L.focus = null; L.afterFit = look;
    await openSheet(it.page);
  } else { drawOverlay(); look(); }
  status(`${RV_TAG[it.cat]}${it.id} ${RV_KO[it.cat]} — ${it.title} · ${it.text}`);
}
function drawReview() {
  const r = RV.data, s = L.sheet;
  if (!r || !s) return;
  const its = r.items.filter((it) => it.page === s.page && it.rect && it.cat !== "INFO" &&
    (RV.on || (RV.focus && RV.focus.id === it.id)));
  if (!its.length) return;
  const g = el("g", { id: "g-review" }, $("#ov"));
  for (const it of its) {
    const [x0, y0, x1, y1] = it.rect;
    const cls = "rv-box " + it.cat.toLowerCase() + (RV.focus && RV.focus.id === it.id ? (Date.now() - RV.focus.at < 3000 ? " flash" : " sel") : "");
    if (cls.endsWith(" flash")) {                 // L41 — 노란 바탕으로 세 번 (다시 그려도 지난 시간만큼 당긴다)
      const pad = Math.max(6, (x1 - x0) * 0.15);
      el("rect", { x: x0 - pad, y: y0 - pad, width: x1 - x0 + 2 * pad, height: y1 - y0 + 2 * pad, rx: 3, class: "rv-halo",
        style: `animation-delay:-${Date.now() - RV.focus.at}ms` }, g);
    }
    const b = el("rect", { x: x0 - 1.5, y: y0 - 1.5, width: x1 - x0 + 3, height: y1 - y0 + 3, class: cls,
      style: cls.endsWith(" flash") ? `animation-delay:-${Date.now() - RV.focus.at}ms` : "" }, g);
    const t = `${RV_TAG[it.cat]}${it.id}`;
    el("rect", { x: x1 + 1.5, y: y0 - 7, width: t.length * 3.1 + 2, height: 5.6, class: "rv-tagbg " + it.cat.toLowerCase() }, g);
    const tx = el("text", { x: x1 + 2.4, y: y0 - 2.6, class: "rv-tagtx" }, g);
    tx.textContent = t;
    const tip = el("title", {}, b);
    tip.textContent = `${t} ${RV_KO[it.cat]} — ${it.title}\n${it.text}`;
  }
}

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
  // L23 — 이 묶음이 실제로 가진 시트 이름으로 읽는다 (꼴을 외우지 않는다): 시트 이름 그대로 · 시트 이름 + `-`/`/` + 행
  const t0 = String(text || "").toUpperCase().replace(/\s+/g, "");
  const nos = L.sheets.map((x) => x.sheet_no).filter(Boolean).sort((a, b) => b.length - a.length);
  let m = null;
  if (nos.includes(t0)) m = [t0, t0, ""];
  else {
    const hit = nos.find((no) => t0.startsWith(no) && /^[-\/]\d{1,3}$/.test(t0.slice(no.length)));
    if (hit) m = [t0, hit, t0.slice(hit.length + 1)];
    else {
      const r = refsIn(t0)[0] || (t0.match(/^((?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]\d{3}[A-Z]?)$/) ? { sheet: t0, row: "" } : null);
      if (r) m = [t0, r.sheet, String(r.row || "")];
    }
  }
  if (!m) { status(`시트-행 꼴이 아닙니다 (예: ${nos[0] || "G049"}-40)`); return; }
  const t = sheetByNo(m[1]);
  if (!t) { status(`${m[1]} 시트는 이 묶음에 없습니다`); return; }
  if (!m[2]) { L.focus = null; openSheet(t.page); return; }
  goToRef(m[1], Number(m[2]), "R");
}
function stageKo(s) { return { reading: "선 읽는 중", glyphs: "글자 배우는 중", blocks: "블록 판정 중" }[s] || ""; }

// L28 — 827장 목록을 매번 통째로 다시 만들지 않는다: 목록(시트 · 검색어)이 같으면 줄마다 바뀐 칸(고른 장 · 연결 표시 ·
// 점검 · 메모 수)만 고친다.  처음 한 번은 글 한 덩이로 붓는다 (줄마다 createElement 하던 것).
const SL = { sheets: null, q: null, rows: new Map() };
function sheetMeta(s, ch, mc) {
  return `${ch ? `<i class="chain-dot"></i>${ch.hop === 0 ? "지정한 장" : `연결 ${ch.hop}단계`} · ` : ""}블록 ${s.blocks} · 선 ${s.nets}${s.mismatch ? ` · <b>from-to 불일치 ${s.mismatch}</b>` : ""}${s.descdiff ? ` · <i class="dd">설명 다름 ${s.descdiff}</i>` : ""}${s.findings ? ` · <b>점검 ${s.findings}</b>` : ""}${mc ? ` · <i class="mc">✎${mc}</i>` : ""}`;
}
function renderSheetList() {
  const q = $("#sheet-filter").value.trim().toUpperCase();
  const ul = $("#sheet-list");
  $("#sheet-count").textContent = `${L.sheets.length}장`;
  const chains = new Map();
  if (L.mode === "sim") for (const c of L.chain || []) if (c.hop != null && !chains.has(c.page)) chains.set(c.page, c);
  if (SL.sheets !== L.sheets || SL.q !== q || !ul.firstChild && L.sheets.length) {
    SL.sheets = L.sheets; SL.q = q; SL.rows = new Map();
    const list = L.sheets.filter((s) => !q || (s.sheet_no + " " + s.title).toUpperCase().includes(q));
    ul.innerHTML = list.map((s) => `<li data-page="${s.page}"><span class="no">${esc(s.sheet_no || "p" + s.page)}</span><span class="t">${esc(s.title)}</span>
      <span class="meta"></span></li>`).join("");
    const lis = ul.children;
    list.forEach((s, i) => SL.rows.set(s.page, { s, li: lis[i], meta: null, cls: null }));
    if (!ul.dataset.bound) {
      ul.dataset.bound = "1";
      ul.addEventListener("click", (e) => {
        const li = e.target.closest("li[data-page]");
        if (li) { L.focus = null; openSheet(Number(li.dataset.page)); }
      });
    }
  }
  const mcs = new Map();
  for (const m of L.memos || []) if (!m.hidden && !m.done) mcs.set(m.page, (mcs.get(m.page) || 0) + 1);
  for (const [page, r] of SL.rows) {
    const ch = chains.get(page);
    const cls = (page === L.page ? "sel" : "") + (ch ? " chain" : "");
    if (cls !== r.cls) { r.li.className = cls.trim(); r.cls = cls; }
    const meta = sheetMeta(r.s, ch, mcs.get(page) || 0);
    if (meta !== r.meta) { r.li.lastElementChild.innerHTML = meta; r.meta = meta; }
  }
}

/* L31 — 시트 사이 이동을 가볍게: 받은 시트는 기억하고(사람 값을 고치면 refreshSheet 가 비운다) · 앞뒤 시트의 내용과
   그림을 쉬는 동안 미리 받아 풀어 둔다 · 그림은 다 풀린 뒤에 바꿔 끼운다(옛 그림 위에 새 시트의 선이 그려지지 않게). */
const SHEET_KEEP = 60;          // 기억하는 시트 수 (846쪽 묶음에서 한 장 20~100KB)
const IMG_KEEP = 8;             // 미리 풀어 둔 그림 수
const SC = { job: null, map: new Map(), img: new Map() };
function sheetCacheClear() { SC.map.clear(); }
function getSheet(page) {
  if (SC.job !== L.job) { SC.job = L.job; SC.map.clear(); SC.img.clear(); }
  const m = SC.map;
  let p = m.get(page);
  if (p) { m.delete(page); m.set(page, p); return p; }
  p = api(`/logic/api/jobs/${L.job}/sheet/${page}`);
  p.catch(() => { if (m.get(page) === p) m.delete(page); });
  m.set(page, p);
  while (m.size > SHEET_KEEP) m.delete(m.keys().next().value);
  return p;
}
function pageImgUrl(page) { return `/logic/api/jobs/${L.job}/page/${page}.png`; }
function preloadImg(page) {
  if (SC.job !== L.job) { SC.job = L.job; SC.map.clear(); SC.img.clear(); }
  let im = SC.img.get(page);
  if (im) { SC.img.delete(page); SC.img.set(page, im); return im; }
  im = new Image();
  im.decoding = "async";
  im.src = pageImgUrl(page);
  im.ready = (im.decode ? im.decode() : Promise.resolve()).catch(() => {});
  SC.img.set(page, im);
  while (SC.img.size > IMG_KEEP) SC.img.delete(SC.img.keys().next().value);
  return im;
}
function neighbours(page) {
  const list = (L.sheets || []).map((x) => x.page);
  const i = list.indexOf(page);
  if (i < 0) return [];
  return [list[i + 1], list[i - 1], list[i + 2]].filter((x) => x != null);
}
function prefetchAround(page) {
  const job = L.job;
  const go = () => {
    if (L.job !== job || L.page !== page) return;
    for (const q of neighbours(page)) { getSheet(q).catch(() => {}); preloadImg(q); }
  };
  if (window.requestIdleCallback) requestIdleCallback(go, { timeout: 600 }); else setTimeout(go, 150);
}

async function openSheet(page, opt) {
  hidePressCard();
  L.page = page;
  location.hash = `job=${L.job}&page=${page}`;
  renderSheetList();
  const im = preloadImg(page);
  const s = await getSheet(page);
  if (L.page !== page) return;                     // 받는 동안 다른 시트로 옮겼다
  stopAnim();                                      // L43 — 앞 장의 흐름이 이 장의 선을 칠하지 않게 (시트를 바꾸기 전에 멈춘다)
  L.sheet = s;
  L.forces = L.allForces[page] = L.allForces[page] || {};
  L.state = L.states[page] || null; L.values = {}; L.sel = null;
  L.linked = {};
  $("#empty").hidden = true;
  const img = $("#page"), ov = $("#ov");
  // 그림은 풀린 뒤에 바꾼다 — 기다리는 동안은 옛 그림을 숨겨 새 시트의 선이 남의 그림 위에 서지 않게.
  // L43 — 선(#ov)도 그 장의 그림이 실제로 화면에 선 뒤에 보인다 (표 칸은 장마다 같아 표는 맞고 LOGIC 영역 선만 어긋나 보이던 것).
  const url = pageImgUrl(page);
  const shown = () => { if (L.page !== page) return; img.style.visibility = ""; ov.style.visibility = ""; img.dataset.page = page; };
  if (img.getAttribute("src") !== url || img.dataset.page !== String(page)) {
    img.style.visibility = "hidden"; ov.style.visibility = "hidden";
    im.ready.then(() => {
      if (L.page !== page) return;
      if (img.getAttribute("src") !== url) img.src = url;
      (img.decode ? img.decode() : Promise.resolve()).catch(() => {}).then(shown);
    });
  } else shown();
  $("#canvas").style.width = s.size[0] + "px";
  $("#canvas").style.height = s.size[1] + "px";
  ov.setAttribute("viewBox", `0 0 ${s.size[0]} ${s.size[1]}`);
  $("#sheet-head").textContent = `${s.sheet_no} · ${s.title}`;
  drawOverlay();
  renderRows(); renderFindings(); renderInfo(); renderHelp(); renderLatches();
  L.pendingAt = null; L.memoEdit = null; renderMemo();
  // 맞춤은 한 번만 — 그림이 이미 풀려 있으면 곧바로 맞추고 뒤이어 오는 load 는 무시한다 (두 번 맞추면 이동한 자리 · 확대가 지워진다)
  let fitted = false;
  const fitOnce = () => { if (fitted || L.page !== page) return; fitted = true; fit(); };
  img.onload = fitOnce;
  img.onerror = shown;
  if (img.complete && img.getAttribute("src") === url) fitOnce();
  prefetchAround(page);
  if (MACRO_FROM && page === MACRO_FROM.target && !L.macroApplied) {
    L.macroApplied = true;
    // L44 — 부모 시트에 펼쳐 같이 돈 값을 받아 그린다.  부모 창이 없으면(주소로 직접 연 창) 예전처럼 이 Typical 만 돌린다
    if (MACRO_FROM.pending) applyMacroInner(MACRO_FROM.pending, true, MACRO_FROM.pendingForces);
    else if (!askParentMacro()) applyMacroInputs(MACRO_FROM.inputs);
    return;
  }
  if (L.mode === "sim" && !(opt && opt.noSim)) runSim(false, true);   // 순차 동작은 곧이어 자기 계산을 돌린다 — 두 번 보내지 않는다
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
    const cls = "blk" + (b.func === "UNKNOWN" ? " unknown" : "") + (b.func === "MACRO" ? " macro" : "") + (b.user ? " user" : "");
    const r = b.kind === "RECT"
      ? el("rect", { x: x0 - 0.6, y: y0 - 0.6, width: x1 - x0 + 1.2, height: y1 - y0 + 1.2, class: cls, "data-block": bid }, gB)
      : el("circle", { cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, r: (x1 - x0) / 2 + 0.8, class: cls, "data-block": bid }, gB);
    r.addEventListener("click", (e) => { if (L.justPanned) return; e.stopPropagation(); onBlock(bid, e); });
    if (b.func !== "CONNECTOR") {
      const t = badgeText(b);
      const w = t.length * 2.55 + 2.4;
      el("rect", { x: x0, y: y0 - 5.6, width: w, height: 5, rx: 1, class: "badge-bg" + (b.func === "UNKNOWN" ? " unknown" : "") + (b.user ? " user" : "") }, gB);
      const tx = el("text", { x: x0 + 1.2, y: y0 - 1.9, class: "badge" }, gB);
      tx.textContent = t;
    }
  }
  drawConnectorLinks(gB);
  for (const r of s.rows) {
    if (!r.at) continue;                               // L42 — 자리 없는 행(사람이 더한 행 · 예전 결과)은 점을 그리지 않는다
    const c = el("circle", { cx: r.at[0], cy: r.at[1], r: 2.4, class: "rowpin", "data-row": r.n }, gR);
    c.addEventListener("click", (e) => { if (L.justPanned) return; e.stopPropagation(); onRow(r.n, e); });
    const ml = MACRO_FROM && L.macroLink && s.page === MACRO_FROM.target ? macroLinkOf(r.side, r.n) : null;
    if (ml) {                                          // L44 — 매크로 새 창: 이 Typical 행이 이어진 부모 시트의 실제 행
      const pr = (ml.rows || [])[0];
      const h = r.y0 != null && r.y1 != null ? Math.max(3.5, Math.min(7, (r.y1 - r.y0) * 0.62)) : 5;
      const txt = pr ? `${r.side === "L" ? "←" : "→"} ${L.macroLink.sheet_no || ""}-${pr.n}` : `${r.side === "L" ? "←" : "→"} ${ml.src || ml.pin || "단자"}`;
      const w = txt.length * h * 0.56 + 2;
      const x = r.side === "L" ? r.at[0] + 4 : r.at[0] - 4 - w;
      el("rect", { x, y: r.at[1] - h * 0.6, width: w, height: h * 1.2, rx: 1, class: "mlink-bg" + (pr ? "" : " nopin") }, gR);
      const tx = el("text", { x: x + 1, y: r.at[1] + h * 0.35, class: "mlink", "font-size": h }, gR);
      tx.textContent = txt;
      el("title", {}, tx).textContent = pr ? `부모 시트 ${L.macroLink.sheet_no || ""} ${pr.n}행 ${pr.desc} — 매크로 단자 ${ml.pin}` : ml.src ? `부모 시트 ${L.macroLink.sheet_no || ""} 의 ${ml.src} — 매크로 단자 ${ml.pin}` : `매크로 단자 ${ml.pin} — 부모 시트의 행과 바로 이어지지 않음`;
    }
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
  drawReview();
  el("g", { id: "g-sim" }, ov);       // 게이트 단자 1/0 · S-R 표 (L8) — paint 가 채운다
  el("g", { id: "g-count" }, ov);     // L15 — 세는 타이머의 남은 시간
  el("g", { id: "g-need" }, ov);      // L15 — 출력을 활성화했을 때 필요한 입력 (주황 3번 점등)
  drawPins();
  drawMarks();
  $("#ov").classList.toggle("hide-nets", !$("#show-nets").checked);
  $("#ov").classList.toggle("hide-blocks", !$("#show-blocks").checked);
  paint();
}
/* ------------------------------------------------------------------ FROM / TO 표기 · 그 시트 그 행으로 이동 (L6)

   FM 칸 `G049-40` = G049 시트 40행(오른쪽 출력)에서 온 신호 · TO 칸 `G025-7` = G025 시트 7행(왼쪽 입력)으로 가는 신호.
   표기는 표가 적은 그 칸 위에, 누르면 그 시트의 그 행으로 간다. */

const REF_RE = /(?<![A-Z_])((?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]\d{3}[A-Z]?)-(\d{1,3})(?!\d)/g;   // app/logic/refs.py 와 같은 꼴 (L21)
// L23 · L23b — 일반 꼴 `<시트>[-/.:]<행>` (1A5J `0016/72` · `FG_G-301-64` · 1A1Y `HR_G908/75` · `LD.01.001-51`).
// app/logic/refs.py 의 GEN_ANY · _gen_ok · _gen_text · _known 과 같다 — 옛 꼴 → 이 묶음의 시트 이름 → 일반 꼴 순.
const REF_GEN = /(?<![A-Z0-9_\/\-.:])((?=[A-Z0-9_\-.]*\d)[A-Z0-9][A-Z0-9_]+(?:[-.][A-Z0-9_]+)*?)([-\/.:])(\d{1,3})(?![\dA-Z_]|[-\/.:][A-Z0-9])/g;
const REF_OLD_SHAPE = /^(?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]+\d+[A-Z]?$/;
function refGenText(text) {
  let t = String(text || "").toUpperCase().trim();
  t = t.replace(/[()\[\]{}<>]/g, " ");
  t = t.replace(/(?<![A-Z0-9])(?:SHEET|SHT|SH)\.?\s*(?=[A-Z0-9])/g, " ");
  t = t.replace(/\s*(?<![A-Z0-9])(?:NO|ROW|LINE)\.?\s*(?=\d)/g, "-");
  return t.replace(/\s*([-\/:])\s*/g, "$1").trim();
}
const reEsc = (x) => x.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
// L28 — 묶음의 시트 이름 목록과 이름마다의 식은 시트 목록이 바뀔 때만 만든다 (846쪽 묶음에서 칸마다 827개 식을
// 새로 만들어 장 하나 여는 데 0.2초를 썼다).  글에 그 이름이 없으면 식을 돌리지 않는다 — 찾는 결과는 같다.
const REF_KNOWN = { sheets: null, known: [], re: new Map() };
function refKnownList() {
  const sh = (typeof L !== "undefined" && L.sheets) || null;
  if (REF_KNOWN.sheets !== sh) {
    REF_KNOWN.sheets = sh;
    REF_KNOWN.known = [...new Set((sh || []).map((x) => String(x.sheet_no || "").toUpperCase()).filter(Boolean))]
      .sort((a, b) => b.length - a.length);
    REF_KNOWN.re = new Map();
  }
  return REF_KNOWN.known;
}
function refKnown(text) {
  const known = refKnownList();
  if (!known.length) return [];
  const t = refGenText(text);
  const out = [], taken = [];
  for (const no of known) {
    if (!t.includes(no)) continue;
    let re = REF_KNOWN.re.get(no);
    if (!re) {
      re = new RegExp(`(?<![A-Z0-9_])${reEsc(no)}\\s*(?:[-/.:#]|\\s)\\s*(\\d{1,3})(?!\\d)`, "g");
      REF_KNOWN.re.set(no, re);
    }
    re.lastIndex = 0;
    for (const m of t.matchAll(re)) {
      if (taken.some(([a, b]) => a <= m.index && m.index < b)) continue;
      taken.push([m.index, m.index + m[0].length]);
      out.push({ at: m.index, sheet: no, row: Number(m[1]), text: m[0] });
    }
  }
  return out.sort((a, b) => a.at - b.at);
}
function refMatches(text) {
  const raw = String(text || "");
  const old = [...raw.toUpperCase().replace(/\s+/g, "").matchAll(REF_RE)];
  if (old.length) return old.map((m) => ({ sheet: m[1], row: Number(m[2]), text: m[0], old: true }));
  const kn = refKnown(text);
  if (kn.length) return kn;
  const g = refGenText(raw);
  return [...g.matchAll(REF_GEN)]
    .filter((m) => !(m[2] === "-" && REF_OLD_SHAPE.test(m[1])) && !(".:".includes(m[2]) && !/[A-Z]/.test(m[1])))
    .map((m) => ({ sheet: m[1], row: Number(m[3]), text: m[0] }));
}
function refsIn(text) {
  return refMatches(text).map((x) => ({ sheet: x.sheet, row: x.row }));
}
function refRest(text) {
  const ms = refMatches(text);
  let t = ms.length && ms[0].old ? String(text || "").toUpperCase().replace(/\s*([-\/])\s*/g, "$1") : refGenText(text);
  for (const x of ms) t = t.replace(x.text, " ");
  return t.replace(/[\s)(]+/g, " ").trim();
}
function sheetByNo(no) { return L.sheets.find((x) => x.sheet_no === no); }
function drawRefTags(ov) {
  const s = L.sheet;
  const g = el("g", { id: "g-refs" }, ov);
  for (const t of s.table || []) {
    const box = t.side === "L" ? t.fm_box : t.to_box;
    if (!box) continue;
    const field = t.side === "L" ? "fm" : "to";
    const refs = refsIn(t[field]);
    const user = t.user && t.user[field];
    const kind = t.side === "L" ? "from" : "to";
    if (!refs.length) {
      // L22 — 읽지 못한 칸 · 시트-행 꼴이 아닌 칸: 눌러서 값을 적는다 (그 행에 신호가 있을 때만 — 빈 행은 두지 않는다)
      // 칸에 글이 있는데 시트-행 꼴이 아닌 것(DCS · NOTE 3)은 도면이 그렇게 적은 것이다 — 목록의 ✎ 로만 고친다
      if (!user && (!t.desc || (t[field] && !/\?/.test(t[field])))) continue;
      const rc = el("rect", { x: box[0] + 0.4, y: box[1] + 0.4, width: box[2] - box[0] - 0.8, height: box[3] - box[1] - 0.8,
        class: `reftag empty ${kind}${user ? " user" : ""}`, "data-side": t.side, "data-row": t.n }, g);
      el("title", {}, rc).textContent = `${kind === "from" ? "FM" : "TO"} 칸 — ${t[field] ? `'${t[field]}' — 글자를 다 읽지 못했습니다` : "비어 있습니다 (못 읽었거나 도면에 없음)"}.  눌러서 값(예: G031-81)을 적으면 이어집니다`;
      rc.addEventListener("click", (e) => { if (L.justPanned) return; e.stopPropagation(); cellEditor(t, e); });
      continue;
    }
    const ok = refs.some((r) => sheetByNo(r.sheet));
    const bad = L.mode === "sim" && designErrorsOnPage()[t.side].has(t.n);
    const rc = el("rect", { x: box[0] + 0.4, y: box[1] + 0.4, width: box[2] - box[0] - 0.8, height: box[3] - box[1] - 0.8,
      class: `reftag ${kind}${ok ? "" : " other"}${bad ? " design-err" : ""}${user ? " user" : ""}`, "data-side": t.side, "data-row": t.n }, g);
    const tag = (kind === "from" ? "FROM" : "TO") + (user ? " ✎" : "");
    const tx = el("text", { x: kind === "from" ? box[0] - 1 : box[2] + 1, y: (box[1] + box[3]) / 2 + 1.5,
      class: `reftxt ${kind}`, "text-anchor": kind === "from" ? "end" : "start" }, g);
    tx.textContent = tag;
    const list = refs.map((r) => `${r.sheet} 시트 ${r.row}행` + (sheetByNo(r.sheet) ? "" : " (이 묶음에 없음)")).join(", ");
    const why = bad ? (L.design || []).filter((e) => e.kind === "error" && ((t.side === "R" && e.page === L.page && (e.at_row || e.row) === t.n)
      || (t.side === "L" && e.target_page === L.page && e.target_row === t.n))).map((e) => "\n⚠ 설계 오류 — " + e.why).join("") : "";
    el("title", {}, rc).textContent = `${tag} ${refs.map((r) => r.sheet + "-" + r.row).join(", ")} → ${list}${ok ? " — 누르면 그 행으로 갑니다" : ""}${user ? `\n✎ 사람이 적음 (${user.author}) · 도면 글자 '${user.was || ""}'` : ""}\n오른쪽 단추 · Alt+누름 = 값 고치기${why}`;
    rc.addEventListener("click", (e) => {
      if (L.justPanned) return;
      e.stopPropagation();
      if (e.altKey) { cellEditor(t, e); return; }
      chooseRef(refs, t.side === "L" ? "R" : "L", e);
    });
    rc.addEventListener("contextmenu", (e) => { e.preventDefault(); e.stopPropagation(); cellEditor(t, e); });
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
  return badgeBase(b) + (b.user ? " ✎" : b.learned ? " ⓛ" : "");
}
function badgeBase(b) {
  if (b.func === "UNKNOWN") return "?";
  if (b.func === "VOTE") return b.label || "A/B";
  if (b.func === "CONST") return b.label === "0" ? "0" : "1";
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

/* ------------------------------------------------------------------ L15 — 타이머 시간 (사람이 바꿈 · 기본 5초 — L22) · 카운트다운 */

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
/* L22 — 사람이 바꾼 시간은 서버(overrides.json)에 남는다 — 다른 PC · 다른 사람에게도 같은 시간.  기본 5초. */
async function loadTimers() {
  L.timers = {};
  try {
    const o = await api(`/logic/api/jobs/${L.job}/overrides`);
    L.timers = o.timers_flat || {};
    L.defaultT = o.default_t || 5;
    L.choices = o.choices || [];
  } catch (e) { /* 예전 서버 */ }
  // 예전(L15)에 이 브라우저에만 적어 둔 시간은 한 번 서버로 옮긴다
  let old = null;
  try { old = JSON.parse(localStorage.getItem("logic.timers." + L.job) || "null"); } catch (e) { old = null; }
  if (old && typeof old === "object" && !Object.keys(L.timers).length) {
    const who = currentAuthor() || "이 브라우저에 남은 값";
    for (const [pg, m] of Object.entries(old))
      for (const [bid, sec] of Object.entries(m || {})) {
        try {
          await post(`/logic/api/jobs/${L.job}/overrides/timer`, { page: Number(pg), block: bid, sec, author: who });
          (L.timers[pg] = L.timers[pg] || {})[bid] = sec;
        } catch (e) { /* 그 블록이 없어졌다 */ }
      }
    try { localStorage.removeItem("logic.timers." + L.job); } catch (e) {}
  }
}
async function setTimer(bid, sec) {
  const who = await needAuthor();
  if (!who) { status("이름이 없어 저장하지 않았습니다"); return; }
  const p = L.page;
  try {
    await post(`/logic/api/jobs/${L.job}/overrides/timer`, { page: p, block: bid, sec, author: who });
  } catch (err) { status("시간을 저장하지 못했습니다 — " + err.message); return; }
  L.timers[p] = L.timers[p] || {};
  if (sec == null) delete L.timers[p][bid]; else L.timers[p][bid] = sec;
  if (!Object.keys(L.timers[p]).length) delete L.timers[p];
  const ts = timerSec(bid);
  status(`타이머 ${bid} — ${fmtSec(ts.sec)} (${ts.src === "user" ? "사람이 바꿈 · " + who : ts.src === "drawing" ? "도면 값" : "도면에 없음 · 기본"})`);
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
/* ------------------------------------------------------------------ L26 — 아날로그 값 (MED …) · 감시 블록 설정값 (HHH · HH …)

   시뮬레이터는 1/0 이다.  MED 같은 아날로그 블록 뒤의 감시 블록(범례 SIGNAL MONITOR — 글자 HHH/ · HH/ · H/ · /L · /LL)은
   값이 설정값을 넘는지(못 미치는지)로 1/0 을 낸다.  사람이 MED 값을 주면 감시 블록마다 맞대어 —
   HH 는 넘지만 HHH 보다 낮으면 HH 만 1 · HHH 보다 높으면 HH · HHH 둘 다 1 (사용자 지시).  판정은 서버(app/logic/analog.py)가 한다.
   설정값은 사람이 적은 값(서버 · 작성자) → 도면이 블록 위에 인쇄한 값 → 없음. */
const MON_RE = /^\s*(H+)\s*\/\s*$|^\s*\/\s*(L+)\s*$/;
function monKind(b) {
  if (!b) return null;
  const m = MON_RE.exec(String(b.label || b.read || "").toUpperCase());
  if (!m) return null;
  if (b.func !== "SIGNAL MONITOR" && !["source", "unknown"].includes(b.logic)) return null;
  return m[1] ? "high" : "low";
}
function isAnalogBlock(b) {
  return !!b && b.logic === "unknown" && !["UNKNOWN", "MACRO", "XOR"].includes(b.func) && !monKind(b);
}
function monSp(b) {
  const p = (b && b.param) || {};
  if (p.sp_user != null && p.sp_user !== "") return { sp: Number(p.sp_user), src: "user" };
  if (p.sp != null && p.sp !== "") return { sp: Number(p.sp), src: "drawing" };
  return { sp: null, src: null };
}
function fmtNum(v) {
  if (v == null || !isFinite(v)) return "—";
  const a = Math.abs(v);
  return String(a >= 1000 ? Math.round(v) : Math.round(v * 1000) / 1000);
}
function monState(bid) {
  return ((L.analogRes || {}).monitors || []).find((m) => m.block === bid) || null;
}
/* 이 키(블록 · 입력 행)의 값을 받는 감시 블록들 — 아날로그 블록(MED …)을 지나 몇 단계까지 */
function monitorsFrom(key) {
  const s = L.sheet;
  let nets = [];
  if (key.startsWith("row:")) { const r = s.rows.find((x) => x.side === "L" && x.n === Number(key.slice(4))); if (r && r.net != null) nets = [String(r.net)]; }
  else nets = s.ports.filter((p) => p.block === key.slice(6) && p.dir === "out").map((p) => String(p.net));
  const seen = new Set(), mons = [];
  for (let depth = 0; depth < 4 && nets.length; depth++) {
    const next = [];
    for (const n of nets) {
      if (seen.has(n)) continue;
      seen.add(n);
      for (const p of s.ports) {
        if (String(p.net) !== n || p.dir !== "in") continue;
        const b = s.blocks[p.block];
        if (monKind(b)) { if (!mons.includes(p.block)) mons.push(p.block); }
        else if (isAnalogBlock(b)) next.push(...s.ports.filter((q) => q.block === p.block && q.dir === "out").map((q) => String(q.net)));
      }
    }
    nets = next;
  }
  return mons;
}
function analogRow(key) {
  if (!key.startsWith("row:") || !L.sheet) return false;
  const r = L.sheet.rows.find((x) => x.side === "L" && x.n === Number(key.slice(4)));
  if (!r || r.net == null) return false;
  return L.sheet.ports.some((p) => String(p.net) === String(r.net) && p.dir === "in" &&
                                    (monKind(L.sheet.blocks[p.block]) || isAnalogBlock(L.sheet.blocks[p.block])));
}
/* 감시 블록에 들어오는 값을 누가 주나 — 그 선을 모는 아날로그 블록 · 입력 행 (사람이 값을 넣는 자리) */
function analogSourceOf(bid) {
  const s = L.sheet;
  for (const p of s.ports.filter((q) => q.block === bid && q.dir === "in")) {
    const drv = s.ports.find((q) => String(q.net) === String(p.net) && q.dir === "out" && isAnalogBlock(s.blocks[q.block]));
    if (drv) return "block:" + drv.block;
    const r = s.rows.find((x) => x.side === "L" && x.net != null && String(x.net) === String(p.net));
    if (r) return "row:" + r.n;
  }
  return null;
}
/* L27 — 사람이 주는 아날로그 값은 4~20 mA (기본 8 mA).  공학값은 서버가 범위(도면 `0~250 barg` · 사람이 적은 값)로 바꾼다. */
const MA_LO = 4, MA_HI = 20, DEFAULT_MA = 8;
function anKey(key) { return (((L.analogRes || {}).keys) || {})[key] || null; }
function analogValueOf(key) {
  const mine = (L.analog[L.page] || {})[key];
  const k = anKey(key);
  if (mine != null) return { ma: mine, eng: k ? k.eng : null, range: k ? k.range : keyRange(key), src: "user" };
  if (k) return { ma: k.ma, eng: k.eng, range: k.range, src: k.src };
  return { ma: null, eng: null, range: keyRange(key), src: null };
}
/* 그 입력의 범위 — 사람이 적은 것 → 도면이 선 아래 인쇄한 것 (서버 결과가 없을 때 화면이 바로 읽는 자리) */
function keyRange(key) {
  let x = null;
  if (key.startsWith("row:")) x = L.sheet.rows.find((r) => r.side === "L" && r.n === Number(key.slice(4)));
  else x = (L.sheet.blocks[key.slice(6)] || {}).param;
  if (!x) return null;
  const r = x.range_user || x.range;
  return r && r.lo != null ? { lo: Number(r.lo), hi: Number(r.hi), unit: r.unit || "", src: x.range_user ? "user" : "drawing" } : null;
}
function maToEng(ma, rg) { return rg ? rg.lo + (ma - MA_LO) / (MA_HI - MA_LO) * (rg.hi - rg.lo) : null; }
function engToMa(v, rg) { return rg && rg.hi !== rg.lo ? MA_LO + (v - rg.lo) / (rg.hi - rg.lo) * (MA_HI - MA_LO) : null; }
function fmtMa(ma) { return ma == null ? "—" : (Math.round(ma * 100) / 100) + " mA"; }
function engText(v, rg) { return v == null ? "" : `${fmtNum(v)}${rg && rg.unit ? " " + rg.unit : ""}`; }
function keyName(key) {
  if (key.startsWith("row:")) {
    const r = L.sheet.rows.find((x) => x.side === "L" && x.n === Number(key.slice(4)));
    return `입력 ${key.slice(4)}행` + (r && r.desc ? " · " + r.desc : "");
  }
  const b = L.sheet.blocks[key.slice(6)];
  return `${b.label || FUNC_KO[b.func] || b.func} — ${FUNC_KO[b.func] || b.func}`;
}
function monLevel(b) { return (b.param || {}).sp_level || (b.label || "").replace("/", "").trim() || "감시"; }
function monLabel(bid) {
  const b = L.sheet.blocks[bid], k = monKind(b);
  return `${monLevel(b)} ${k === "high" ? "넘으면 1" : "못 미치면 1"}`;
}
/* 감시 블록 설정값 칸 — 도면에서 읽은 수가 기본값.  못 읽었으면 비워 두고 '직접 입력' 이라고 말한다 (지어내지 않는다) */
function spRowHtml(bid, rg) {
  const b = L.sheet.blocks[bid], ms = monSp(b), p = b.param || {};
  const d = p.sp != null ? Number(p.sp) : null;
  const unit = p.sp_unit || (rg && rg.unit) || "";
  const ma = ms.sp != null ? engToMa(ms.sp, rg) : null;
  const why = ms.src === "user" ? `✎ ${esc(p.sp_user_by || "")}${d != null ? " · 도면 " + fmtNum(d) : ""}`
    : d != null ? "도면 값" : p.sp_label ? `도면 표기 '${esc(p.sp_label)}' (수가 아님) — 직접 입력` : "도면에 없음 — 직접 입력";
  return `<label class="fm-t an-sp${ms.sp == null ? " need" : ""}"><span class="an-mon">${esc(monLabel(bid))}</span>
    <input data-sp="${esc(bid)}" type="number" step="any" value="${ms.sp == null ? "" : ms.sp}" placeholder="설정값"> ${esc(unit)}
    <small>${why}${ma != null ? ` · ≈ ${fmtMa(ma)}` : ""}</small></label>`;
}
function rangeRowHtml(key, rg) {
  const p = rg ? (rg.src === "user" ? "사람이 적음" : "도면 값") : "도면에 없음 — 적어 주세요";
  return `<div class="fm-sub">범위 — 4 mA 일 때 · 20 mA 일 때 <small>${p}</small></div>
    <label class="fm-t an-rg${rg ? "" : " need"}"><input data-rg="lo" type="number" step="any" value="${rg ? rg.lo : ""}" placeholder="4 mA">
      ~ <input data-rg="hi" type="number" step="any" value="${rg ? rg.hi : ""}" placeholder="20 mA">
      <input data-rg="unit" class="unit" value="${esc(rg ? rg.unit : "")}" placeholder="단위"></label>`;
}
function menuRange(m) {
  const g = (k) => (m.querySelector(`input[data-rg="${k}"]`) || {}).value;
  const lo = g("lo"), hi = g("hi");
  if (lo == null || String(lo).trim() === "" || String(hi).trim() === "") return null;
  const a = Number(lo), b = Number(hi);
  return isFinite(a) && isFinite(b) && a !== b ? { lo: a, hi: b, unit: String(g("unit") || "").trim() } : null;
}
function maInputHtml(id, cur) {
  const v = cur.src === "user" ? cur.ma : "";
  const ph = cur.ma != null ? fmtNum(cur.ma) : DEFAULT_MA;
  return `<label class="fm-t">값 <input id="${id}" type="number" min="${MA_LO}" max="${MA_HI}" step="0.1" value="${v}" placeholder="${ph}"> mA
    <small>4~20 mA · 비우면 기본 ${DEFAULT_MA} mA</small></label><div class="fm-why an-eng"></div>`;
}
function liveEng(m, inp, cur) {
  const out = m.querySelector(".an-eng");
  const upd = () => {
    const rg = menuRange(m) || cur.range;
    const raw = inp.value.trim();
    const ma = raw === "" ? (cur.src === "user" ? null : (cur.ma != null ? cur.ma : DEFAULT_MA)) : Number(raw);
    if (raw !== "" && !(ma >= MA_LO && ma <= MA_HI)) { out.textContent = "4~20 mA 사이로 적어 주세요"; out.classList.add("bad"); return; }
    out.classList.remove("bad");
    out.textContent = ma == null ? "" : rg ? `= ${engText(maToEng(ma, rg), rg)}  (범위 ${fmtNum(rg.lo)}~${fmtNum(rg.hi)}${rg.unit ? " " + rg.unit : ""})`
      : cur.src === "calc" || cur.src === "linked" || cur.src === "pass" ? `지금 ${engText(cur.eng, cur.range)}` : "범위를 몰라 공학값으로 바꿀 수 없습니다 — 아래 범위를 적어 주세요";
  };
  m.addEventListener("input", upd);
  upd();
}
function analogMenu(key, e) {
  closeForceMenu();
  const mons = monitorsFrom(key);
  const cur = analogValueOf(key);
  const b = key.startsWith("block:") ? L.sheet.blocks[key.slice(6)] : null;
  const how = b && /MEDIAN/.test(b.func) ? "값을 비우면 그 입력들의 중간값 (범례 MEDIAN SELECTION)"
    : cur.src === "pass" ? "보정 계산식은 도면에 없어 주 입력 값을 그대로 넘겼습니다" : "";
  const ownRange = key.startsWith("row:") || !cur.range || (b && (b.param || {}).range_user);
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu an-menu";
  m.innerHTML = `<div class="fm-h">${esc(keyName(key))} — 아날로그 값 (4~20 mA)</div>
    ${maInputHtml("an-v", cur)}
    ${how ? `<div class="fm-why an-why">${how}</div>` : ""}
    ${ownRange ? rangeRowHtml(key, keyRange(key) || (key.startsWith("row:") ? null : cur.range)) : ""}
    ${mons.length ? `<div class="fm-sub">이 값을 받는 감시 블록 — 설정값 (기본 = 도면 값)</div>${mons.map((x) => spRowHtml(x, cur.range)).join("")}`
                  : `<div class="fm-why an-why">이 값을 받는 감시 블록(HH · HHH …)이 이 시트에 없습니다</div>`}
    <button data-a="ok" class="v1">적용 — 동작 시뮬레이션에서 맞대기</button>
    ${cur.src === "user" ? `<button data-a="x" class="vx">기본 ${DEFAULT_MA} mA 로</button>` : ""}
    ${L.mode === "trace" ? `<button data-a="t" class="vt">↪ 연결만 따라가기</button>` : ""}`;
  placeMenu(m, e);
  const inp = m.querySelector("#an-v");
  liveEng(m, inp, cur);
  const first = m.querySelector(".need input") || inp;
  first.focus(); first.select && first.select();
  const ok = async () => {
    const raw = inp.value.trim();
    const v = raw === "" ? null : Number(raw);
    if (raw !== "" && !(v >= MA_LO && v <= MA_HI)) { inp.classList.add("bad"); return; }
    if (ownRange && !(await saveRange(m, key))) return;
    if (!(await saveSetpoints(m))) return;
    closeForceMenu();
    setAnalog(key, v);
  };
  m.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) ok(); });
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const btn = ev.target.closest("button");
    if (!btn) return;
    if (btn.dataset.a === "ok") ok();
    else if (btn.dataset.a === "t") { closeForceMenu(); traceFrom(key, false); }
    else { closeForceMenu(); setAnalog(key, null); }
  });
}
function monitorMenu(bid, e) {
  closeForceMenu();
  const b = L.sheet.blocks[bid];
  const st = monState(bid);
  const src = analogSourceOf(bid);
  const cur = src ? analogValueOf(src) : { ma: null, eng: st && st.value, range: st && st.range, src: null };
  const rg = (st && st.range) || cur.range;
  const v = L.forces["block:" + bid];
  const ms = monSp(b);
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu an-menu";
  m.innerHTML = `<div class="fm-h">${esc(b.label || "")} 신호 감시 (Alarm) — ${monKind(b) === "high" ? "값이 설정값을 넘으면 1" : "값이 설정값에 못 미치면 1"}</div>
    ${ms.sp == null ? `<div class="fm-why">도면에서 설정값을 읽지 못했습니다 — 직접 입력해 주세요</div>` : ""}
    ${spRowHtml(bid, rg)}
    ${src ? `<div class="fm-sub">들어오는 값 — ${esc(keyName(src))}</div>${maInputHtml("an-v", cur)}` : ""}
    ${src && !cur.range ? rangeRowHtml(src, null) : ""}
    <div class="fm-why an-why">${st && st.out != null ? `지금 ${engText(st.value, rg)} ${monKind(b) === "high" ? ">" : "<"} ${fmtNum(st.sp)} → <b>${st.out}</b>` : "값과 설정값이 다 있어야 맞댑니다 — 없으면 1/0 을 직접 줄 수 있습니다"}</div>
    <button data-a="ok" class="v1">적용 — 동작 시뮬레이션에서 맞대기</button>
    ${ms.src === "user" ? `<button data-a="d" class="vx">${(b.param || {}).sp != null ? "도면 설정값으로" : "설정값 지우기"}</button>` : ""}
    <button data-v="1" class="v1${v === 1 ? " on" : ""}"><b>1</b> 활성 (값과 무관하게)</button>
    <button data-v="0" class="v0${v === 0 ? " on" : ""}"><b>0</b> 비활성</button>
    ${v !== undefined ? `<button data-v="x" class="vx">강제 풀기</button>` : ""}
    ${L.mode === "trace" ? `<button data-a="t" class="vt">↪ 연결만 따라가기</button>` : ""}`;
  placeMenu(m, e);
  const vi = m.querySelector("#an-v");
  if (vi) liveEng(m, vi, cur);
  const inp = m.querySelector("input[data-sp]");
  inp.focus(); inp.select();
  const ok = async () => {
    let nv;
    if (vi) {
      const raw = vi.value.trim();
      nv = raw === "" ? null : Number(raw);
      if (raw !== "" && !(nv >= MA_LO && nv <= MA_HI)) { vi.classList.add("bad"); return; }
    }
    if (src && !cur.range && !(await saveRange(m, src))) return;
    if (!(await saveSetpoints(m))) return;
    closeForceMenu();
    if (vi && src && (nv != null || cur.src === "user")) setAnalog(src, nv); else rerunAnalog();
  };
  m.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) ok(); });
  m.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    const btn = ev.target.closest("button");
    if (!btn) return;
    if (btn.dataset.a === "ok") { ok(); return; }
    if (btn.dataset.a === "d") { closeForceMenu(); if (await postSetpoint(bid, null)) rerunAnalog(); return; }
    if (btn.dataset.a === "t") { closeForceMenu(); traceFrom("block:" + bid, false); return; }
    closeForceMenu();
    setForce("block:" + bid, btn.dataset.v === "x" ? null : Number(btn.dataset.v));
  });
}
async function saveRange(m, key) {
  const cur = keyRange(key);
  const lo = m.querySelector('input[data-rg="lo"]'), hi = m.querySelector('input[data-rg="hi"]');
  if (!lo) return true;
  const want = menuRange(m);
  if (!want) {
    if (lo.value.trim() === "" && hi.value.trim() === "") return true;      // 범위 없이 둔다
    lo.classList.add("bad"); hi.classList.add("bad"); return false;
  }
  if (cur && cur.lo === want.lo && cur.hi === want.hi && (cur.unit || "") === want.unit) return true;
  const who = await needAuthor();
  if (!who) { status("이름이 없어 범위를 저장하지 않았습니다"); return false; }
  try {
    await post(`/logic/api/jobs/${L.job}/overrides/range`, { page: L.page, key, lo: want.lo, hi: want.hi, unit: want.unit, author: who });
  } catch (err) { status("범위를 저장하지 못했습니다 — " + err.message); return false; }
  const ent = { lo: want.lo, hi: want.hi, unit: want.unit, by: who };
  if (key.startsWith("row:")) { const r = L.sheet.rows.find((x) => x.side === "L" && x.n === Number(key.slice(4))); if (r) r.range_user = ent; }
  else { const b = L.sheet.blocks[key.slice(6)]; b.param = b.param || {}; b.param.range_user = ent; }
  return true;
}
async function saveSetpoints(m) {
  for (const inp of m.querySelectorAll("input[data-sp]")) {
    const bid = inp.dataset.sp, b = L.sheet.blocks[bid];
    const raw = inp.value.trim();
    const cur = monSp(b);
    if (raw === "" && cur.sp == null) continue;
    const v = raw === "" ? null : Number(raw);
    if (raw !== "" && !isFinite(v)) { inp.classList.add("bad"); return false; }
    if (v != null && cur.sp != null && Math.abs(v - cur.sp) < 1e-9) continue;
    if (v == null && cur.src !== "user") continue;
    if (v != null && cur.src === "drawing" && Math.abs(v - Number(b.param.sp)) < 1e-9) continue;
    if (!(await postSetpoint(bid, v))) return false;
  }
  return true;
}
async function postSetpoint(bid, sp) {
  const who = await needAuthor();
  if (!who) { status("이름이 없어 설정값을 저장하지 않았습니다"); return false; }
  try {
    await post(`/logic/api/jobs/${L.job}/overrides/setpoint`, { page: L.page, block: bid, sp, author: who });
  } catch (err) { status("설정값을 저장하지 못했습니다 — " + err.message); return false; }
  const b = L.sheet.blocks[bid];
  b.param = b.param || {};
  if (sp == null) { delete b.param.sp_user; delete b.param.sp_user_by; }
  else { b.param.sp_user = sp; b.param.sp_user_by = who; }
  status(`${b.label || "감시"} 설정값 — ${sp == null ? (b.param.sp != null ? "도면 값 " + fmtNum(Number(b.param.sp)) : "없음") : fmtNum(sp) + " (" + who + ")"}`);
  return true;
}
function setAnalog(key, v, page) {
  const p = page == null ? L.page : page;
  L.analog[p] = L.analog[p] || {};
  if (v == null) delete L.analog[p][key]; else L.analog[p][key] = v;
  if (!Object.keys(L.analog[p]).length) delete L.analog[p];
  // L29 — 한 입력에는 한 가지만: 아날로그 값을 넣으면 그 입력에 준 디지털 1/0 강제는 푼다
  if (v != null && L.allForces[p] && key in L.allForces[p]) {
    delete L.allForces[p][key];
    if (p === L.page) L.forces = L.allForces[p];
  }
  if (p !== L.page) {
    status(v != null ? `∿ ${p} 쪽 ${key} = ${fmtMa(v)}` : `∿ ${p} 쪽 ${key} — 기본 ${DEFAULT_MA} mA 로`);
    rerunAnalog();
    return;
  }
  status(v != null ? `∿ ${keyName(key)} = ${fmtMa(v)} — 감시 블록이 설정값과 맞댑니다` : `∿ ${keyName(key)} — 기본 ${DEFAULT_MA} mA 로`);
  rerunAnalog();
}
function rerunAnalog() {
  if (L.mode !== "sim") setMode("sim", true);
  L.states = {}; L.state = null; L.values = {};
  runSim(true).then(() => renderInfo());
}
function analogInfoRows(bid) {
  const b = L.sheet.blocks[bid];
  const opRow = b.aop ? (() => {
    const v = (L.aopVocab && ((L.aopVocab.ops || {})[b.aop] || (L.aopVocab.digital_ops || {})[b.aop])) || {};
    const d = L.mode === "sim" && L.analogResPage === L.page ? ((L.analogRes || {}).ops || {})[bid] : null;
    const u = aopUser(b);
    return `<tr><td>연산자</td><td><b>${esc(v.ko || b.aop)}</b>${v.eq ? ` <small>${esc(v.eq)}</small>` : ""}${Object.keys(u).length ? ` <small>✎ ${esc((b.param.a_user || {}).by || "")}</small>` : ""} <button data-opopen="${esc(bid)}">입력 · 설정 보기</button></td></tr>` +
      (d ? `<tr><td>계산</td><td>${(d.inputs || []).map((i) => `${esc(i.pin || "—")} ${opValText(i.value)}`).join(" · ")} → <b>${d.dig != null ? d.dig : opValText(d.out)}</b>${d.why ? ` <small>${esc(d.why)}</small>` : ""}</td></tr>` : "");
  })() : "";
  if (b.aop && !monKind(b)) return opRow;
  if (monKind(b)) {
    const ms = monSp(b), st = monState(bid), p = b.param || {};
    const rg = st && st.range;
    return `<tr><td>설정값</td><td><b>${ms.sp == null ? "없음 — 직접 입력" : fmtNum(ms.sp) + " " + esc(p.sp_unit || (rg && rg.unit) || "")}</b> <small>${ms.src === "user" ? "✎ 사람이 정함 · " + esc(p.sp_user_by || "") + (p.sp != null ? " (도면 " + fmtNum(Number(p.sp)) + ")" : "") : ms.src === "drawing" ? "도면 " + esc(p.sp_text || "") : p.sp_label ? "도면 표기 " + esc(p.sp_label) + " (수가 아님)" : "도면에서 못 읽음"}</small> <button data-an="mon:${esc(bid)}">${ms.sp == null ? "설정값 입력" : "설정값 바꾸기"}</button></td></tr>
      ${L.mode === "sim" && st && st.value != null ? `<tr><td>맞대기</td><td>값 ${engText(st.value, rg)} ${monKind(b) === "high" ? ">" : "<"} ${ms.sp == null ? "?" : fmtNum(ms.sp)} → ${st.out == null ? "설정값 없음" : valTag(st.out)}</td></tr>` : ""}`;
  }
  if (isAnalogBlock(b)) {
    const cur = analogValueOf("block:" + bid);
    const mons = monitorsFrom("block:" + bid);
    return `<tr><td>아날로그 값</td><td><b>${cur.eng == null ? (cur.ma == null ? "없음" : fmtMa(cur.ma)) : engText(cur.eng, cur.range)}</b>${cur.ma != null && cur.eng != null ? ` <small>(${fmtMa(cur.ma)})</small>` : ""} <small>${cur.src === "user" ? "사람이 넣음" : cur.src === "calc" ? "입력에서 계산" : cur.src === "pass" ? "주 입력 그대로" : cur.src === "linked" ? "다른 시트에서" : ""}</small> <button data-an="block:${esc(bid)}">값 넣기 (mA)</button></td></tr>
      ${mons.length ? `<tr><td>감시</td><td>${mons.map((m) => { const st = monState(m); const sp = monSp(L.sheet.blocks[m]).sp; return `${esc(L.sheet.blocks[m].label)} ${sp == null ? "설정값 없음" : fmtNum(sp)}${L.mode === "sim" && st && st.out != null ? " → " + valTag(st.out) : ""}`; }).join(" · ")}</td></tr>` : ""}`;
  }
  return "";
}
/* 도면 위: 아날로그 블록 아래 '= 62.5 barg (8 mA)' · 감시 블록 아래 'SP 191 · 62.5 → 0' · 설정값이 없으면 붉은 'SP ? 직접 입력' */
function drawAnalogMarks(g, fs) {
  const s = L.sheet;
  drawOpMarks(g, fs);                                              // L30 — 연산자 값 · 값이 필요한 자리
  for (const [bid, b] of Object.entries(s.blocks)) {
    const [x0, , x1, y1] = b.bbox || [0, 0, 0, 0];
    if (monKind(b)) {
      const ms = monSp(b), st = monState(bid);
      const parts = [ms.sp == null ? `SP ? 직접 입력${(b.param || {}).sp_label ? " (" + b.param.sp_label + ")" : ""}` : `SP ${fmtNum(ms.sp)}${ms.src === "user" ? " ✎" : ""}`];
      if (L.mode === "sim" && st && st.value != null) parts.push(`${fmtNum(st.value)} → ${st.out == null ? "?" : st.out}`);
      const tx = el("text", { x: (x0 + x1) / 2, y: y1 + fs * 1.6, "font-size": fs * 1.25,
                              class: "ansp" + (st && st.out === 1 && L.mode === "sim" ? " on" : "") + (ms.src === "user" ? " user" : "") + (ms.sp == null ? " need" : "") }, g);
      tx.textContent = parts.join(" · ");
    } else if (isAnalogBlock(b) && L.mode === "sim") {
      const cur = analogValueOf("block:" + bid);
      if (cur.eng == null && cur.ma == null) continue;
      const tx = el("text", { x: (x0 + x1) / 2, y: y1 + fs * 1.7, "font-size": fs * 1.4, class: "anv " + cur.src }, g);
      tx.textContent = `= ${cur.eng != null ? engText(cur.eng, cur.range) : ""}${cur.ma != null ? (cur.eng != null ? " (" + fmtMa(cur.ma) + ")" : fmtMa(cur.ma)) : ""}${cur.src === "user" ? " ✎" : ""}`;
    }
  }
  if (L.mode !== "sim") return;
  // L29 — 입력마다 지금 들어가 있는 것을 꼬리표로: 아날로그(보라 · 내가 넣은 값은 진하게 · 기본값은 테두리만) ·
  // 디지털로 준 1(파랑) / 0(회색).  누르면 그 입력의 메뉴가 열린다.
  for (const r of s.rows) {
    if (r.side !== "L" || !r.at) continue;
    const key = "row:" + r.n;
    const n = signalNow(key);
    if (n.kind !== "analog" && !n.user) continue;
    const label = n.kind === "analog" ? `${n.text}${n.user ? " ✎" : " 기본"}` : `${n.text} ✎`;
    const cls = n.kind === "analog" ? "sigtag an" + (n.user ? " user" : "") : "sigtag dg v" + n.v;
    const fz = (s.pitch || 11.5) * 0.52, w = label.length * fz * 0.6 + fz, h = fz * 1.4;   // 행 높이의 비율 — 맞춤 배율에서도 읽힌다
    const x = r.at[0] + fs * 0.9, y = r.at[1] - h - fs * 0.25;
    const gg = el("g", { class: cls, "data-key": key }, g);
    el("rect", { x, y, width: w, height: h, rx: h / 2 }, gg);
    const tx = el("text", { x: x + w / 2, y: y + h * 0.72, "font-size": fz }, gg);
    tx.textContent = label;
    el("title", {}, gg).textContent = `${r.n}행 · ${n.kind === "analog" ? "아날로그 입력" : "디지털 입력"} — ${n.how} · 눌러서 바꾸기`;
    gg.addEventListener("click", (ev) => { ev.stopPropagation(); forceMenu(key, ev, `입력 ${r.n}` + (r.desc ? " · " + r.desc : "")); });
  }
}
/* ------------------------------------------------------------------ L30 — 아날로그 연산자 (∑ · △ · ÷ · × · A · T · 수식 · PID …)

   식별·계산은 서버(app/logic/aops.py · analog.py)가 한다 — 범례 식 그대로, 입력 이름(IN1 · IN2 : -1 · + · −)과 옆 상수
   (A : 5%)는 도면에서 읽는다.  도면이 말하지 않는 값(K · b · H · L · F(X) 표 · PID 출력 …)은 사람이 이 판에 넣는다
   (작성자와 함께 서버에 남는다 · 다시 분석해도 남는다).  입력 값은 시뮬레이션 입력이라 저장하지 않는다. */
const AOP_NEED_KEYS = { value: "상수", k: "K", b: "b", h: "H", l: "L", n: "n", d: "D", out: "출력", c: "C" };
async function aopVocab() {
  if (!L.aopVocab) { try { L.aopVocab = await api("/logic/api/aops"); } catch (e) { L.aopVocab = { ops: {}, digital_ops: {}, needs: {} }; } }
  return L.aopVocab;
}
function opOf(bid) { const b = L.sheet && L.sheet.blocks[bid]; return b ? b.aop || null : null; }
/* 지금 계산 — 동작 시뮬레이션 중이면 그 결과(다른 장에서 이어진 값까지), 아니면 그 장만 서버가 센다 */
async function opDetail(bid) {
  const ops = L.analogResPage === L.page ? ((L.analogRes || {}).ops || {}) : {};
  if (L.mode === "sim" && ops[bid]) return ops[bid];
  try {
    return await post(`/logic/api/jobs/${L.job}/sheet/${L.page}/aop`, { block: bid, analog: L.analog[L.page] || {} });
  } catch (e) { return null; }
}
function aopUser(b) { const u = ((b && b.param) || {}).a_user || {}; const o = {}; for (const [k, v] of Object.entries(u)) if (k !== "by" && k !== "at") o[k] = v; return o; }
function aopDrawing(b, k) {
  const p = (b && b.param) || {};
  if (k === "value" && p.a_const && p.a_const.v != null) return { v: p.a_const.v, text: p.a_const.text };
  const d = (p.a_drawing || {})[k];
  return d && d.v != null ? { v: d.v, text: d.text } : null;
}
function opValText(v) { return v == null ? "모름" : fmtNum(v); }
function netSource(net, self) {
  const s = L.sheet;
  const r = s.rows.find((x) => x.side === "L" && x.net != null && String(x.net) === String(net));
  if (r) return `입력 ${r.n}행${r.desc ? " · " + r.desc : ""}`;
  const on = s.ports.filter((q) => String(q.net) === String(net) && q.block !== self);
  const p = on.find((q) => (s.blocks[q.block] || {}).aop === "const") || on.find((q) => q.dir === "out");
  if (p) { const b = s.blocks[p.block]; return `${b.label || FUNC_KO[b.func] || b.func} (${p.block})`; }
  return "선 " + net;
}
async function opMenu(bid, e, chooseOp) {
  closeForceMenu();
  const b = L.sheet.blocks[bid];
  const voc = await aopVocab();
  const d = (await opDetail(bid)) || { op: b.aop, inputs: [], out: null, why: "" };
  const op = d.op || b.aop || null;
  const info = (voc.ops || {})[op] || (voc.digital_ops || {})[op] || {};
  const u = aopUser(b);
  const needs = (voc.needs || {})[op] || [];
  const mine = L.analog[L.page] || {};
  const allOps = Object.entries({ ...(voc.ops || {}), ...(voc.digital_ops || {}) });
  const numRow = (k, label) => {
    const dr = aopDrawing(b, k), cur = u[k];
    return `<label class="fm-t op-p"><span>${esc(label)}</span><input data-op="${k}" type="number" step="any" value="${cur == null ? "" : cur}" placeholder="${dr ? fmtNum(dr.v) : "값"}">
      <small>${cur != null ? `✎ ${esc((b.param.a_user || {}).by || "")}${dr ? " · 도면 " + esc(dr.text) : ""}` : dr ? "도면 " + esc(dr.text) : "도면에 없음 — 넣어 주세요"}</small></label>`;
  };
  const ins = d.inputs || [];
  const coefOn = needs.some((x) => x[0] === "coef");
  const insHtml = ins.length ? `<table class="op-io"><tr><th>입력</th><th>어디서</th>${coefOn ? "<th>계수</th>" : ""}<th>값</th></tr>${ins.map((i) => {
      const nk = "net:" + i.net, given = mine[nk];
      const cuc = (u.coef || {})[i.net];
      return `<tr><td><b>${esc(i.pin || "—")}</b>${i.coef != null && !coefOn ? ` <small>×${fmtNum(i.coef)}</small>` : ""}</td><td><small>${esc(netSource(i.net, bid))}</small></td>
        ${coefOn ? `<td><input data-coef="${esc(i.net)}" type="number" step="any" value="${cuc == null ? "" : cuc}" placeholder="${i.coef != null ? fmtNum(i.coef) : 1}"></td>` : ""}
        <td>${String(i.net) === String(d.cond) ? `<b>${L.mode === "sim" ? (L.values[String(i.net)] === 1 ? 1 : 0) : "—"}</b> <small>디지털 조건</small>`
          : `<input data-in="${esc(i.net)}" type="number" step="any" value="${given && given.eng != null ? given.eng : ""}" placeholder="${i.value == null ? "모름" : fmtNum(i.value)}">`}</td></tr>`;
    }).join("")}</table><div class="fm-why">값 칸에 수를 넣으면 그 입력선을 그 값으로 보고 돌립니다 (시뮬레이션 입력 · 저장 안 함)</div>`
    : op === "const" ? "" : `<div class="fm-why">입력선을 도면에서 읽지 못했습니다</div>`;
  let pHtml = "";
  for (const [k, label] of needs) {
    if (AOP_NEED_KEYS[k]) pHtml += k === "c"
      ? `<label class="fm-t op-p"><span>${esc(label)}</span><select data-op="c"><option value="">신호대로</option><option value="1"${u.c === 1 ? " selected" : ""}>1 → IN1</option><option value="0"${u.c === 0 ? " selected" : ""}>0 → IN2</option></select></label>`
      : numRow(k, label);
    else if (k === "table") pHtml += `<label class="fm-t op-p col"><span>${esc(label)}</span><textarea data-op="table" rows="3" placeholder="0, 0&#10;100, 50">${esc((u.table || []).map((p) => p.join(", ")).join("\n"))}</textarea><small>한 줄에 X, Y — 그 사이는 곧은 선으로 잇습니다</small></label>`;
    else if (k === "vars") {
      const vars = (d.why.match(/수식의 (.+?) 값을/) || [])[1];
      const names = Array.from(new Set([...(vars ? vars.split(/,\s*/) : []), ...Object.keys(u.vars || {})]));
      pHtml += names.length ? names.map((nm) => `<label class="fm-t op-p"><span>수식 ${esc(nm)}</span><input data-var="${esc(nm)}" type="number" step="any" value="${(u.vars || {})[nm] == null ? "" : u.vars[nm]}"></label>`).join("")
        : `<div class="fm-why">수식의 글자는 입력선 이름에서 읽었습니다</div>`;
    } else if (k === "order" && ins.length >= 2) {
      const o = u.order || [];
      const opt = (sel) => ins.map((i) => `<option value="${esc(i.net)}"${sel === i.net ? " selected" : ""}>${esc(i.pin || "선 " + i.net)}</option>`).join("");
      pHtml += `<label class="fm-t op-p"><span>${esc(label)}</span><select data-ord="0"><option value="">도면대로</option>${opt(o[0])}</select> · <select data-ord="1"><option value="">도면대로</option>${opt(o[1])}</select></label>`;
    }
  }
  const outTxt = d.dig != null ? `<b>${d.dig}</b> (1/0)` : d.out != null ? `<b>${fmtNum(d.out)}</b>${d.key && d.key.range ? " " + esc(d.key.range.unit || "") : ""}` : "<b>모름</b>";
  const memos = (L.memos || []).filter((m) => m.page === L.page && m.block === bid && !m.hidden);
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu an-menu op-menu";
  m.innerHTML = `<div class="fm-h">${esc(b.label || "")} ${esc(info.ko || "아날로그 연산자")} <small>${esc(bid)}</small></div>
    ${info.eq ? `<div class="op-eq">${esc(info.eq)}</div>` : ""}
    ${!op || chooseOp ? `<label class="fm-t op-p"><span>연산 종류</span><select data-op="op"><option value="">${op ? "그대로" : "고르세요"}</option>${allOps.map(([k, v]) => `<option value="${k}"${u.op === k ? " selected" : ""}>${esc(v.ko)}</option>`).join("")}</select></label>` : ""}
    ${insHtml}
    <div class="op-out">출력 = ${outTxt}${d.why ? ` <small>${esc(d.why)}</small>` : ""}${L.mode === "sim" ? "" : ` <small>(이 장만 — 동작 시뮬레이션에서는 다른 장에서 이어진 값까지)</small>`}</div>
    ${pHtml ? `<div class="fm-sub">값 · 설정 (기본 = 도면 값)</div>${pHtml}` : ""}
    <details class="op-more"><summary>더 — 출력값 고정 · 연산 종류 바꾸기</summary>
      ${needs.some((x) => x[0] === "out") ? "" : numRow("out", "출력값 고정")}
      ${op && !chooseOp ? `<label class="fm-t op-p"><span>연산 종류</span><select data-op="op"><option value="">그대로 (${esc(info.ko || op)})</option>${allOps.map(([k, v]) => `<option value="${k}"${u.op === k ? " selected" : ""}>${esc(v.ko)}</option>`).join("")}</select></label>` : ""}
      ${isAnalogBlock(b) && monitorsFrom("block:" + bid).length ? `<button data-a="ma" class="vt">출력을 mA 로 넣고 감시 블록 설정값 보기</button>` : ""}
    </details>
    ${memos.length ? `<div class="fm-sub">이 연산자 메모</div>${memos.map((x) => `<div class="op-memo" data-memo="${esc(x.id)}"><b>${esc(x.author)}</b> <small>${esc(x.time)}</small><div>${esc(x.text)}</div></div>`).join("")}` : ""}
    <div class="op-btns"><button data-a="ok" class="v1">적용 — 동작 시뮬레이션</button>
    ${Object.keys(u).length ? `<button data-a="reset" class="vx">도면 값으로</button>` : ""}
    <button data-a="memo" class="vt">📌 메모 달기</button></div>`;
  placeMenu(m, e);
  const first = m.querySelector(".op-p input:placeholder-shown[placeholder='값'], .op-p input") || m.querySelector("input[data-in]");
  if (first) first.focus();
  const collect = () => {
    const p = { ...u };
    for (const inp of m.querySelectorAll("[data-op]")) {
      const k = inp.dataset.op, raw = String(inp.value || "").trim();
      if (k === "table") {
        const pts = raw.split(/\n+/).map((ln) => ln.split(/[,\s]+/).filter(Boolean).map(Number)).filter((x) => x.length === 2 && x.every(isFinite));
        if (raw && pts.length < 2) return { bad: inp };
        if (pts.length) p.table = pts; else delete p.table;
      } else if (k === "op") { if (raw) p.op = raw; else if (inp.closest(".op-more") || op) delete p.op; }
      else if (k === "c") { if (raw === "") delete p.c; else p.c = Number(raw); }
      else if (raw === "") delete p[k];
      else if (!isFinite(Number(raw))) return { bad: inp };
      else p[k] = Number(raw);
    }
    const coef = { ...(u.coef || {}) };
    for (const inp of m.querySelectorAll("[data-coef]")) { const raw = inp.value.trim(); if (raw === "") delete coef[inp.dataset.coef]; else if (!isFinite(Number(raw))) return { bad: inp }; else coef[inp.dataset.coef] = Number(raw); }
    if (Object.keys(coef).length) p.coef = coef; else delete p.coef;
    const vars = { ...(u.vars || {}) };
    for (const inp of m.querySelectorAll("[data-var]")) { const raw = inp.value.trim(); if (raw === "") delete vars[inp.dataset.var]; else if (!isFinite(Number(raw))) return { bad: inp }; else vars[inp.dataset.var] = Number(raw); }
    if (Object.keys(vars).length) p.vars = vars; else delete p.vars;
    const o = [...m.querySelectorAll("[data-ord]")].map((x) => x.value);
    if (o.length === 2 && o[0] && o[1] && o[0] !== o[1]) p.order = o; else if (o.length === 2) delete p.order;
    return { p };
  };
  const ok = async () => {
    const c = collect();
    if (c.bad) { c.bad.classList.add("bad"); c.bad.focus(); status("수를 적어 주세요"); return; }
    if (JSON.stringify(sortKeys(c.p)) !== JSON.stringify(sortKeys(u))) {
      if (!(await saveAparam(bid, Object.keys(c.p).length ? c.p : null))) return;
    }
    for (const inp of m.querySelectorAll("[data-in]")) {
      const raw = inp.value.trim(), nk = "net:" + inp.dataset.in;
      L.analog[L.page] = L.analog[L.page] || {};
      if (raw === "") delete L.analog[L.page][nk];
      else if (isFinite(Number(raw))) L.analog[L.page][nk] = { eng: Number(raw) };
      if (!Object.keys(L.analog[L.page]).length) delete L.analog[L.page];
    }
    closeForceMenu();
    rerunAnalog();
  };
  m.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing && ev.target.tagName !== "TEXTAREA") ok(); });
  m.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    const mm = ev.target.closest("[data-memo]");
    if (mm) { closeForceMenu(); selectMemo(mm.dataset.memo, true); return; }
    const btn = ev.target.closest("button[data-a]");
    if (!btn) return;
    if (btn.dataset.a === "ok") ok();
    else if (btn.dataset.a === "reset") { closeForceMenu(); if (await saveAparam(bid, null)) rerunAnalog(); }
    else if (btn.dataset.a === "ma") { closeForceMenu(); analogMenu("block:" + bid, ev); }
    else if (btn.dataset.a === "memo") {
      closeForceMenu();
      const [x0, y0, x1] = b.bbox;
      pinForm([x1, y0], { block: bid, rect: b.bbox, title: `${b.label || info.ko || "연산자"} (${bid}) 메모` }, ev);
    }
  });
}
function sortKeys(o) { return Object.keys(o).sort().reduce((a, k) => { a[k] = o[k]; return a; }, {}); }
async function saveAparam(bid, params) {
  const who = await needAuthor();
  if (!who) { status("이름이 없어 저장하지 않았습니다"); return false; }
  try {
    await post(`/logic/api/jobs/${L.job}/overrides/aparam`, { page: L.page, block: bid, params, author: who });
  } catch (err) { status("저장하지 못했습니다 — " + err.message); return false; }
  status(params ? `연산자 ${bid} 값을 저장했습니다 (${who}) — 다시 분석해도 남습니다` : `연산자 ${bid} — 도면 값으로 되돌렸습니다`);
  await refreshSheet();
  return true;
}
/* 도면 위: 연산자 아래 '= 15 %' (시뮬레이션) · 값이 필요한데 없으면 붉은 '? 값 입력' (어느 모드든 — 상수는 바로 안다) */
function drawOpMarks(g, fs) {
  const s = L.sheet, ops = L.analogResPage === L.page ? ((L.analogRes || {}).ops || {}) : {};
  for (const [bid, b] of Object.entries(s.blocks)) {
    if (!b.aop || !b.bbox) continue;
    const [x0, , x1, y1] = b.bbox;
    const d = L.mode === "sim" ? ops[bid] : null;
    const u = aopUser(b);
    let txt = null, cls = "opv";
    if (d) {
      if (d.dig != null) { txt = `→ ${d.dig}`; cls += d.dig === 1 ? " on" : ""; }
      else if (d.out != null) { if (isAnalogBlock(b) && analogValueOf("block:" + bid).eng != null) continue; txt = `= ${fmtNum(d.out)}`; }
      else if (/눌러서|넣어 주세요/.test(d.why || "")) { txt = "? 값 입력"; cls += " need"; }
    } else if (b.aop === "const" && !aopDrawing(b, "value") && u.value == null) { txt = "? 값 입력"; cls += " need"; }
    if (!txt) continue;
    if (Object.keys(u).length) txt += " ✎";
    const tx = el("text", { x: (x0 + x1) / 2, y: y1 + fs * 1.7, "font-size": fs * 1.35, class: cls }, g);
    tx.textContent = txt;
  }
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

async function runSim(animate, pageOnly) {
  if (macroLinked()) { askParentMacro(); return; }   // L44 — 매크로 새 창의 값은 부모 시트의 묶음 계산이 정한다
  if (!L.sheet || L.sheet.page !== L.page) return;   // L43 — 장을 받는 중(시트와 쪽이 아직 다름)에는 돌리지 않는다 — 받은 뒤 openSheet 가 돌린다
  const askSheet = L.sheet;
  const prev = { ...L.values };
  // 묶음 전체를 함께 돌린다 — 출력 행이 1 이면 그 행을 FM 으로 받는 다른 장의 입력도 1 (서버가 판정)
  const forces = {};
  for (const [p, f] of Object.entries(L.allForces)) if (Object.keys(f).length) forces[p] = f;
  const analog = {};
  for (const [p, a] of Object.entries(L.analog || {})) if (Object.keys(a).length) analog[p] = a;
  const askPage = L.page;
  // L31 — 시트만 옮겼고 준 신호가 그대로면 지난 계산의 입력을 그대로 보낸다: 묶음의 답은 같고 이 장의 결과만 꺼내면 된다
  // (돌려받은 상태를 다시 보내면 서버가 시간을 한 번 더 흘린 것으로 보고 묶음 전체를 다시 센다).
  const inputs = JSON.stringify([forces, L.timers, analog]);
  const last = L.lastSim;
  const state = pageOnly && last && last.job === L.job && last.inputs === inputs ? last.state : L.states;
  L.lastSim = { job: L.job, inputs, state };
  const inner = Object.entries(L.childWins || {}).filter(([, c]) => c.win && !c.win.closed).map(([k]) => k);
  const b = await post(`/logic/api/jobs/${L.job}/simulate`, { forces, state, page: L.page, timers: L.timers, analog, inner });
  if (b.default_t) L.defaultT = b.default_t;
  const r = b.focus;
  if (!r || L.page !== askPage || L.sheet !== askSheet) return;   // 기다리는 동안 다른 장으로 옮겼다 — 그 장의 결과를 이 장에 그리지 않는다
  L.states = b.state || {};
  L.state = L.states[L.page] || r.state;
  L.analogResPage = askPage;
  L.analogRes = r.analog || {};                    // L26 — 아날로그 값 · 감시 블록 (값 · 설정값 · 출력)
  L.analogGiven = b.analog_given || {};
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
  L.macroInner = b.macro_inner || {};               // L44 — 열린 매크로 새 창이 그릴 부모 장의 펼친 값
  sendMacroInputs();
  renderSheetList(); renderChain();
  stopAnim();
  playFrames(r.frames, prev, animate);
  return r;
}
/* 틀을 그린다 — 묶음 계산의 결과든 (runSim) 매크로 새 창이 부모에게서 받은 값이든 (L44) 같은 길 */
function playFrames(frames, prev, animate) {
  const r = { frames };
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
  if (m === "sim") { if (!quiet) runSim(false); } else { L.values = {}; L.linked = {}; hidePressCard(); paint(); }
  renderInfo(); renderRows(); renderChain(); renderSheetList();
}

/* L16 — 강제 신호 전체 리셋: 모든 시트에 사람이 준 1/0 · 거꾸로 맞춘 값 · 동작 예시 · 메모리 · 타이머 상태를 지운다.
   타이머 시간 설정(사람이 바꾼 초)은 신호가 아니라 설정이라 남긴다.  열린 매크로 새 창에도 0 이 된 입력을 보낸다. */
function resetAll() {
  const n = Object.values(L.allForces || {}).reduce((a, f) => a + Object.keys(f || {}).length, 0);
  L.allForces = {}; L.forces = L.allForces[L.page] = {};
  L.analog = {}; L.analogRes = {}; L.analogGiven = {};
  L.states = {}; L.state = null; L.values = {}; L.linked = {}; L.chain = []; L.design = [];
  L.implied = {}; L.scenario = null; L.unmet = [];
  stopAnim();
  const rb = $("#remind"); if (rb) rb.hidden = true;
  hidePressCard();
  renderChain(); renderSheetList();
  if (L.mode === "sim") runSim(false); else paint();
  renderInfo(); renderRows();
  status(n ? `⟲ 강제 신호 ${n}개를 모두 지웠습니다 (모든 시트 · 메모리 · 타이머 상태 포함)` : "⟲ 지울 강제 신호가 없습니다 — 메모리 · 타이머 상태를 처음으로 되돌렸습니다");
}

function setForce(key, v) {
  if (macroLinked()) { macroWindowForce(key, v); return; }   // L44 — 매크로 새 창: 부모 시트의 실제 행으로 준다
  // L15 — 출력(오른쪽 행 · 블록이 모는 선 · 매크로 출력 단자)을 1 로 주면: 그 출력이 서려면 어떤 입력이 1 이어야
  // 하는지 범례 정의로 찾아 그 입력들을 주황으로 3번 점등하고 실제로 활성화한다 (사용자 지시).
  if (v === 1 && wantsScenario(key)) { activateOutput(key); return; }
  // L9 — 따라가기 모드에서 입력 동그라미에 1/0 을 고르면 시뮬레이션으로 넘어가 그 값으로 돈다
  if (L.mode !== "sim") setMode("sim", true);
  if (v === null) delete L.forces[key]; else L.forces[key] = v;
  // L29 — 한 입력에는 한 가지만: 디지털 1/0 을 주면 그 입력에 넣어 둔 아날로그 값은 뺀다
  if (v !== null && (L.analog[L.page] || {})[key] != null) {
    delete L.analog[L.page][key];
    if (!Object.keys(L.analog[L.page]).length) delete L.analog[L.page];
  }
  // L16 — 목표로 둔 출력이 게이트 조건을 못 채웠으면 (사람이 준 입력 0 이 막음) 그렇게 말하고 0 인 입력을 짚는다
  runSim(true).then(() => { if ((L.unmet || []).length) reportUnmet(); });
  // L34 — 누름단추를 1 로 누르면 그 신호가 어디까지 갔는지 · 어디서 왜 멈췄는지 · 누른 채로 동작시키려면 무엇을 더 켤지
  if (v === 1 && isPress(key)) pressReport(key.slice(6), L.page);
  else if (key.startsWith("block:")) hidePressCard();
}

/* ------------------------------------------------------------------ L34 — 누름단추를 누른다

   사용자 지시 "Push button 을 활성 누르면 해당 신호가 동작하도록".  눌러서 생긴 신호는 묶음 시뮬레이션이 범례대로
   퍼뜨린다 (L18 — 게이트는 언제나 논리대로).  그 신호가 출력까지 못 가면 어디서 왜 멈췄는지 말하고, 단추를 누른 채로
   그 동작(단추 이름의 낱말이 든 출력)이 나가려면 어떤 입력을 더 켜야 하는지 서버가 찾아 확인한 조합을 권한다. */
function isPress(key, s) {
  s = s || L.sheet;
  if (!s || !key.startsWith("block:")) return false;
  const bid = key.slice(6), b = s.blocks[bid];
  return !!b && b.logic === "source" && !s.ports.some((p) => p.block === bid && p.dir === "in");
}
function pressLabel(b) {
  const nm = b.label || b.func || "신호원";
  return /PUSH|PB/.test(b.func || "") ? `누름단추 · ${nm}` : nm;
}
function pressCard() {
  let c = document.getElementById("pbcard");
  if (!c) {
    c = document.createElement("div");
    c.id = "pbcard"; c.className = "lg-pbcard"; c.hidden = true;
    const rm = $("#remind");
    (rm ? rm.parentNode : document.body).appendChild(c);
    c.addEventListener("click", onPressCard);
  }
  return c;
}
function hidePressCard() { const c = document.getElementById("pbcard"); if (c) c.hidden = true; L.press = null; }
function keyText(k, s) {
  s = s || L.sheet;
  if (k.startsWith("row:")) {
    const n = Number(k.slice(4)), r = s.rows.find((x) => x.n === n && x.side === "L") || s.rows.find((x) => x.n === n);
    return `입력 ${n}행${r && r.desc ? " · " + r.desc : ""}`;
  }
  if (k.startsWith("block:")) { const b = s.blocks[k.slice(6)]; return b ? pressLabel(b) : k; }
  return "선 " + k.slice(4);
}
async function pressReport(bid, page) {
  const forces = {};
  for (const [p, f] of Object.entries(L.allForces)) if (Object.keys(f).length) forces[p] = f;
  const analog = {};
  for (const [p, a] of Object.entries(L.analog || {})) if (Object.keys(a).length) analog[p] = a;
  const state = (L.lastSim && L.lastSim.job === L.job) ? L.lastSim.state : L.states;
  let r;
  try { r = await post(`/logic/api/jobs/${L.job}/sheet/${page}/press`, { block: bid, forces, state, timers: L.timers, analog }); }
  catch (e) { return; }
  if (L.page !== page || L.forces["block:" + bid] !== 1) return;     // 기다리는 동안 다른 장 · 단추를 뗐다
  L.press = { ...r, page };
  renderPressCard();
}
function stopText(st) {
  const s = L.sheet;
  const where = st.macro ? `매크로 ${esc(st.macro.title || st.macro.sheet || "")} 안의 ` : "";
  const name = esc(st.func || "블록") + (st.label && st.label !== st.func ? ` ${esc(st.label)}` : "");
  if (st.dead_end) return `${where}${name} 까지는 신호가 갔지만 그 뒤 선을 도면에서 더 읽지 못했습니다 (끊긴 연결 — 마크업 · 도면 확인)`;
  if (st.logic === "unknown") return `${where}판정 못 한 블록에서 멈췄습니다 — 그 블록 종류를 정하면 이어집니다`;
  if (st.short) return `${where}${name} — 입력선을 다 읽지 못해 출력을 내지 않습니다 (도면 확인)`;
  if (st.already) return `${where}${name} — 출력이 이미 그 값이라 눌러도 바뀌는 것이 없습니다`;
  const off = (st.inputs || []).filter((x) => x.value !== 1).length;
  return `${where}${name} 에서 멈췄습니다 — 조건: ${esc(gateNeedText(st.logic, 1))}${off ? ` · 0 인 입력 ${off}개 (주황)` : ""}`;
}
function renderPressCard() {
  const r = L.press, c = pressCard();
  if (!r || L.mode !== "sim" || r.page !== L.page) { c.hidden = true; return; }
  const b = L.sheet.blocks[r.block] || {};
  let html = `<div class="pb-h">● 눌렀습니다 — ${esc(pressLabel(b))}<button class="pb-x" title="닫기">✕</button></div><div class="pb-b">`;
  if (r.why) html += `<p>${esc(r.why)}</p>`;
  if (r.ok) {
    html += `<p class="pb-ok">✔ 신호가 동작했습니다 — 눌러서 새로 1 이 된 출력</p><ul>` +
      r.reached.slice(0, 6).map((t, i) => `<li><button data-go="${i}">${esc(t.label)}</button></li>`).join("") + `</ul>`;
  } else if (!r.why) {
    html += `<p class="pb-stop">⛔ 신호가 출력까지 가지 못했습니다 — 게이트가 범례대로 판정한 결과입니다.</p>`;
    if (r.stop) html += `<p>${stopText(r.stop)} <button data-v="stop">그 자리 보기</button></p>`;
    if (r.plan) {
      const t = r.plan.target, keys = Object.keys(r.plan.add);
      html += `<div class="pb-plan"><b>단추를 누른 채로</b> ${keys.length ? "아래 입력도 켜면" : ""} <b>${esc(t.label)}</b> 이 나갑니다${r.plan.steady ? "" : " (잠깐 서는 펄스)"}:
        <ul>${keys.map((k) => `<li>${esc(keyText(k))} = ${r.plan.add[k]}</li>`).join("") || "<li>더 켤 것 없음</li>"}</ul>
        <button data-v="plan" class="pb-go">▶ 조건 채워 동작시키기</button></div>`;
    } else if (r.targets) {
      html += `<p class="pb-none">이 단추에서 닿는 출력 ${r.targets}개 중 누른 채로 서는 조합을 찾지 못했습니다 — 길에 다른 시트의 조건이나 도면 읽기 빈틈이 있습니다 (▶ 순차 동작에서 조건을 하나씩 물어볼 수 있습니다).</p>`;
    } else {
      html += `<p class="pb-none">이 단추에서 연결로 닿는 출력 행 · 매크로 출력이 없습니다.</p>`;
    }
  }
  c.innerHTML = html + `</div>`;
  c.hidden = false;
  if (!r.ok && r.stop && !r.stop.already) flashNeed(stopKeys(r.stop));
}
function stopKeys(st) {
  if (st.macro) return ["block:" + st.macro.block];
  const k = (st.inputs || []).filter((x) => x.value !== 1 && !String(x.net).includes("/")).map((x) => "net:" + x.net);
  return k.length ? k : (st.block && !String(st.block).includes("/") ? ["block:" + st.block] : []);
}
function centerAt(at) {
  if (!at) return;
  const st = $("#stage");
  setZoom(Math.max(L.zoom, 1.6));
  st.scrollLeft = at[0] * L.zoom - st.clientWidth / 2;
  st.scrollTop = at[1] * L.zoom - st.clientHeight / 2;
}
function onPressCard(e) {
  const r = L.press;
  const btn = e.target.closest("button");
  if (!btn || !r) return;
  e.stopPropagation();
  if (btn.classList.contains("pb-x")) { hidePressCard(); return; }
  if (btn.dataset.go != null) {
    const t = r.reached[Number(btn.dataset.go)];
    if (t.kind === "row") { L.focus = { page: L.page, row: t.row, side: "R", at: Date.now() }; drawOverlay(); focusRow(); }
    else if (t.block) { L.sel = { block: t.block }; paint(); renderInfo(); centerAt(L.sheet.blocks[t.block].bbox.slice(0, 2)); }
    return;
  }
  if (btn.dataset.v === "stop" && r.stop) {
    const bid = r.stop.macro ? r.stop.macro.block : r.stop.block;
    const b = bid && L.sheet.blocks[bid];
    if (b) { L.sel = { block: bid }; paint(); renderInfo(); centerAt(b.bbox.slice(0, 2)); }
    flashNeed(stopKeys(r.stop));
    return;
  }
  if (btn.dataset.v === "plan" && r.plan) {
    const add = r.plan.add, keys = Object.keys(add);
    for (const k of keys) L.forces[k] = add[k];
    status(`▶ ${pressLabel(L.sheet.blocks[r.block] || {})} — 누른 채로 ${keys.length}개 입력을 켭니다 — ${r.plan.target.label}`);
    flashNeed(keys.filter((k) => add[k] === 1)).then(() => runSim(true).then(() => pressReport(r.block, r.page)));
  }
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
      parts.push(`${name} 입력선 ${x.unread.length}개가 연결 안 됨 (0 으로 봄) — ${x.want} 이 안 나옴`);
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
      if (row && row.at) {
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
  if (!s) { try { s = await getSheet(page); } catch (e) { return; } }
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
/* L29 — 입력 하나에 지금 무엇이 들어가 있나 — 디지털(1 활성 / 0 비활성) · 아날로그(mA = 공학값) · 내가 준 것인가 기본값인가.
   메뉴 · 오른쪽 행 목록 · 도면 표시가 모두 이것 하나를 읽는다 (서로 다른 말을 하지 않게). */
const MA_PRESETS = [4, 8, 12, 16, 20];
function signalNow(key) {
  const dv = L.forces[key];
  if (dv !== undefined) return { kind: "digital", user: true, v: dv, text: dv === 1 ? "1 활성" : "0 비활성", how: "내가 줌" };
  if (key.startsWith("row:") && analogRow(key)) {
    const a = analogValueOf(key);
    const ma = a.ma != null ? a.ma : DEFAULT_MA;
    const eng = a.eng != null ? a.eng : maToEng(ma, a.range);
    return { kind: "analog", user: a.src === "user", ma, eng, range: a.range,
             text: `∿ ${fmtMa(ma)}${eng != null ? " = " + engText(eng, a.range) : ""}`,
             how: a.src === "user" ? "내가 넣음" : a.src === "linked" ? "다른 시트에서" : `기본값 (${DEFAULT_MA} mA)` };
  }
  if (L.mode !== "sim") return { kind: "digital", user: false, v: null, text: "", how: "" };
  const r = key.startsWith("row:") ? L.sheet.rows.find((x) => x.n === Number(key.slice(4)) && x.side === "L") : null;
  const lk = r && r.n in (L.linked || {});
  const v = r ? (L.values[r.net] === 1 ? 1 : 0) : null;
  return { kind: "digital", user: false, v, text: v == null ? "" : v === 1 ? "1 활성" : "0 비활성",
           how: lk ? `다른 시트에서 (${r.fm || ""})` : "도면 값 (아무도 안 줌)" };
}
function nowLine(key) {
  const n = signalNow(key);
  if (!n.text) return "";
  return `<div class="fm-now ${n.kind}${n.user ? " user" : ""}${n.kind === "digital" && n.v === 1 ? " on" : ""}">지금 <b>${esc(n.text)}</b> <small>${esc(n.how)}</small></div>`;
}
function forceMenu(key, e, label, up) {
  closeForceMenu();
  const v = L.forces[key];
  const isAn = analogRow(key) && key.startsWith("row:");
  const m = document.createElement("div");
  m.id = "force-menu";
  m.className = "force-menu" + (isAn ? " sig-an" : "");
  m.dataset.key = key;
  const cur = isAn ? analogValueOf(key) : null;
  m.innerHTML =
    (label ? `<div class="fm-h">${esc(label)}${isAn ? ` <span class="fm-kind an">아날로그 입력</span>` : key.startsWith("row:") && !isOutRow(key) ? ` <span class="fm-kind dg">디지털 입력</span>` : ""}</div>` : "") +
    nowLine(key) +
    (isAn ? `<div class="fm-sec an">∿ 아날로그 값 넣기 <small>4 ~ 20 mA</small></div>
      <div class="fm-an"><input id="an-q" type="number" min="${MA_LO}" max="${MA_HI}" step="0.1"
        value="${cur.src === "user" ? cur.ma : ""}" placeholder="${cur.ma != null ? fmtNum(cur.ma) : DEFAULT_MA}"> mA
        <span class="an-q-eng"></span></div>
      <div class="fm-chips">${MA_PRESETS.map((x) => `<button data-ma="${x}" class="chip${cur.src === "user" && cur.ma === x ? " on" : ""}">${x}</button>`).join("")}<small>mA</small></div>
      <button data-v="aok" class="va">∿ 이 값 넣기</button>
      ${cur.src === "user" ? `<button data-v="ax" class="vx">기본 ${DEFAULT_MA} mA 로 되돌리기</button>` : ""}
      <button data-v="a" class="vmore">범위 · 감시(HH · HHH) 설정값 자세히 …</button>
      <div class="fm-sec dg">디지털로 강제 <small>값과 무관하게 선을 1 / 0 으로</small></div>` : "") +
    `<div class="fm-dg"><button data-v="1" class="v1${v === 1 ? " on" : ""}"><b>1</b> 활성</button>` +
    `<button data-v="0" class="v0${v === 0 ? " on" : ""}"><b>0</b> 비활성</button>` +
    (v !== undefined ? `<button data-v="x" class="vx">강제 풀기</button>` : "") + `</div>` +
    (L.mode === "trace" ? `<button data-v="t" class="vt">${up ? "↩ 어디서 오는지 거슬러 올라가기" : "↪ 연결만 따라가기"}</button>` : "") +
    (isOutRow(key) ? `<button data-v="s" class="vs">⚡ 이 출력까지 동작 예시 — 입력부터 최종 출력까지</button>` +
      `<button data-v="q" class="vs">▶ 이 출력을 조건부터 차례로 묻기 (순차 동작)</button>` : "");
  document.body.appendChild(m);
  const x = (e && e.clientX) || innerWidth / 2, y = (e && e.clientY) || innerHeight / 2;
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(x + 8, innerWidth - r.width - 4)) + "px";
  m.style.top = Math.max(4, Math.min(y + 8, innerHeight - r.height - 4)) + "px";
  const q = m.querySelector("#an-q");
  const applyAn = (raw) => {
    const val = String(raw).trim() === "" ? null : Number(raw);
    if (val != null && !(val >= MA_LO && val <= MA_HI)) { q.classList.add("bad"); return; }
    closeForceMenu();
    setAnalog(key, val);
  };
  if (q) {
    const out = m.querySelector(".an-q-eng");
    const upd = () => {
      const raw = q.value.trim(), ma = raw === "" ? (cur.ma != null ? cur.ma : DEFAULT_MA) : Number(raw);
      q.classList.remove("bad");
      if (raw !== "" && !(ma >= MA_LO && ma <= MA_HI)) { out.textContent = "4~20 mA 사이"; out.className = "an-q-eng bad"; return; }
      const eng = maToEng(ma, cur.range);
      out.className = "an-q-eng";
      out.textContent = eng != null ? `= ${engText(eng, cur.range)}` : "범위 없음 — '자세히' 에서 적어 주세요";
    };
    q.addEventListener("input", upd);
    q.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) applyAn(q.value); });
    upd();
    q.focus();
  }
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.ma) { applyAn(b.dataset.ma); return; }
    if (b.dataset.v === "aok") { applyAn(q.value); return; }
    closeForceMenu();
    if (b.dataset.v === "ax") { setAnalog(key, null); return; }
    if (b.dataset.v === "t") { traceFrom(key, !!up); return; }
    if (b.dataset.v === "s") { runScenario(key); return; }
    if (b.dataset.v === "q") { const n = Number(key.slice(4)), r = L.sheet.rows.find((x) => x.side === "R" && x.n === n);
      seqStart({ page: L.page, sheet: L.sheet.sheet_no, row: n, desc: (r && r.desc) || "", action: "", kind: "" }); return; }
    if (b.dataset.v === "a") { analogMenu(key, e); return; }
    setForce(key, b.dataset.v === "x" ? null : Number(b.dataset.v));
  });
}

/* ------------------------------------------------------------------ 매크로 블록 (L12)

   상자를 누르면 작은 메뉴 — 내부 동작을 정의한 Typical 시트를 새 창으로 연다.  새 창은 이 상자의 입력 단자 값을
   그 시트의 입력 행에 주고 돌린다 (시뮬레이션이 다시 돌 때마다 이 창이 새 값을 보낸다). */
L.childWins = {};
function macroName(b) {
  // 상자 글줄에 단자 이름이 섞여 있으면 (1A5J 'FG COMPR SYS GRP A_MODE S_AUTO …') 그 낱말을 뗀다 — 이름만 남긴다
  const pins = new Set(((b.macro || {}).inputs || []).concat((b.macro || {}).outputs || [])
    .map((x) => String(x.pin || "").toUpperCase()).filter(Boolean));
  const words = String(b.caption || "").split(/\s+/).filter(Boolean);
  const keep = [];
  for (const w of words) {
    if (pins.has(w.toUpperCase()) || /^[A-Z]{1,4}_[A-Z0-9]+$/.test(w)) break;      // 첫 단자 이름부터는 단자 줄
    keep.push(w);
  }
  return keep.join(" ") || b.caption || "";
}
function macroView(bid) { return ((L.macros || {})[L.page] || {})[bid] || null; }
function macroMenu(bid, e) {
  closeForceMenu();
  const b = L.sheet.blocks[bid], m = b.macro || {};
  const box = document.createElement("div");
  box.id = "force-menu"; box.className = "force-menu";
  box.innerHTML = `<div class="fm-h">${esc(macroName(b) || "매크로 블록")}</div>` +
    (m.page ? `<button data-m="open" class="v1">↗ 내부 동작 보기 (새 창) — ${esc(m.sheet)}</button>`
            : `<div class="fm-why">${esc(m.why || "이 블록의 Typical 시트를 찾지 못했습니다")}</div>`) +
    `<button data-m="needs" class="vt">🔍 출력마다 필요한 신호 — 무엇이 켜져야 나가나</button>` +
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
    else if (btn.dataset.m === "needs") needsOpen("block:" + bid);
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
  const from = encodeURIComponent(`${L.sheet.sheet_no} · ${macroName(b) || "매크로"}`);
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
    const inner = (L.macroInner || {})[key] || null;
    const forces = inner ? macroChildForces(L.allForces[c.page], c.bid, inner.alias) : null;
    if (v) c.win.postMessage({ type: "macro-inputs", key, inputs: v.inputs, inner, forces }, location.origin);
  }
}
window.addEventListener("message", (e) => {
  if (e.origin !== location.origin || !e.data) return;
  if (e.data.type === "macro-need") { handleMacroNeed(e.data); return; }     // L15 — 새 창이 부모에게
  if (e.data.type === "macro-ask") { handleMacroAsk(e.data, e.source); return; }   // L44
  if (e.data.type === "macro-set") { handleMacroSet(e.data); return; }             // L44
  if (PANE_REVIEW) { if (e.data.type === "review-marks" && e.data.job === L.job) loadReview(L.job, true); return; }
  if (["review-go", "review-on", "review-marks", "grouptest-apply", "goto"].includes(e.data.type)) {
    fromOtherWindow(e.data).catch((er) => { console.error(er); status(`다른 창에서 온 신호를 그리지 못했습니다 — ${er.message} (${whereErr(er)})`); });
    return;
  }
  if (e.data.type !== "macro-inputs" || !MACRO_FROM) return;
  if (e.data.inner) applyMacroInner(e.data.inner, false, e.data.forces);
  else applyMacroInputs(e.data.inputs);
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
/* L44 — 매크로 새 창은 Typical 을 따로 돌리지 않는다 (사용자 지시: "Logic Sheet 상의 실제 Input 과 Output 의 행과
   연결시키고 그 값을 띄워라").  엔지니어는 Typical 을 참조해 실제 시트에서 행 번호를 마음대로 배치한다 — 그래서
   Typical 입력 행마다 부모 시트의 실제 행(예: 14행 OP REQ → 단자 A_OPN)을 붙이고, 값은 부모 장에 펼쳐 같이 돈
   묶음 계산을 그대로 그린다 (펄스 · 지연도 같은 시간으로). */
function macroLinked() { return !!(MACRO_FROM && L.macroLink && L.page === MACRO_FROM.target); }
function askParentMacro() {
  if (!MACRO_FROM || !window.opener || window.opener.closed) return false;
  try { window.opener.postMessage({ type: "macro-ask", parent: MACRO_FROM.parent, block: MACRO_FROM.block }, location.origin); return true; }
  catch (e) { return false; }
}
function macroLinkOf(side, n) {
  return ((L.macroLink && L.macroLink.links) || []).find((x) => x.side === side && x.row === n) || null;
}
function macroRowLabel(x) {
  const pr = (x.rows || [])[0];
  return pr ? `${x.row}행 ← ${L.macroLink.sheet_no || ""}-${pr.n}${pr.desc ? " " + pr.desc : ""}` : `${x.row}행 ← ${x.src || x.pin || "단자"}`;
}
function macroRowOn(n) {
  const r = L.sheet && L.sheet.rows.find((x) => x.side === "L" && x.n === n);
  return !!(r && L.values[r.net] === 1);
}
async function applyMacroInner(inner, first, forces) {
  if (!MACRO_FROM) return;
  if (!L.sheet || L.page !== MACRO_FROM.target) { MACRO_FROM.pending = inner; MACRO_FROM.pendingForces = forces; return; }
  const was = L.macroLink;
  const lastJson = was ? JSON.stringify(was.frames[was.frames.length - 1].values) : null;
  L.macroLink = inner;
  if (L.mode !== "sim") setMode("sim", true);
  const s = L.sheet;
  const all = new Set(Object.keys(s.nets || {}));
  for (const p of s.ports) all.add(String(p.net));
  for (const r of s.rows) if (r.net != null) all.add(String(r.net));
  const frames = (inner.frames || []).map((fr) => {
    const v = {};
    for (const n of all) v[n] = 0;
    Object.assign(v, fr.values || {});
    return { ...fr, values: v, depth: fr.depth || {} };
  });
  if (!frames.length) return;
  // 값은 부모 시트가 정한다 — 강제 표시만 부모 장의 강제(이 매크로 안쪽)를 옮겨 그린다 (L45)
  L.forces = L.allForces[L.page] = { ...(forces || {}) };
  L.implied = {}; L.unmet = []; L.short = new Set(); L.design = []; L.chain = []; L.linked = {};
  L.notes = []; L.pulled = [];
  L.finalValues = frames[frames.length - 1].values;
  const prev = { ...L.values };
  const changed = lastJson !== JSON.stringify(inner.frames[inner.frames.length - 1].values) || frames.length > 1;
  // 부모 시트에서 새로 1 이 된 입력 행은 주황으로 3번 점등 (L15)
  const fresh = s.rows.filter((r) => r.side === "L" && r.net != null && frames[frames.length - 1].values[r.net] === 1 && prev[r.net] !== 1)
    .map((r) => "row:" + r.n);
  renderMacroBanner(); renderRows();
  stopAnim();
  if (!was) drawOverlay();
  if (fresh.length && !first && was) await flashNeed(fresh);
  playFrames(frames, prev, changed);
  renderMacroBanner(); renderRows();
}
async function macroWindowForce(key, v) {
  const ln = L.macroLink;
  if (key.startsWith("row:")) {
    const n = Number(key.slice(4));
    const inRow = L.sheet.rows.find((r) => r.side === "L" && r.n === n);
    if (inRow) {
      const x = macroLinkOf("L", n);
      if (!x) { status(`${n}행은 부모 시트의 매크로 입력 단자와 이어지지 않았습니다 — 부모 시트에서 주세요`); return; }
      window.opener.postMessage({ type: "macro-set", parent: MACRO_FROM.parent, block: MACRO_FROM.block, row: n, value: v }, location.origin);
      status(`${macroRowLabel(x)} 을 ${v === null ? "풀기" : v} — 부모 시트(${ln.sheet_no || ""})에 줍니다`);
      return;
    }
    if (v === 1 && isOutRow(key)) {
      status(`출력 ${n}행이 1 이 되려면 어떤 입력이 1 이어야 하는지 찾는 중…`);
      const sc = await findInputs(L.page, key);
      if (!sc.ok) { status("⚠ " + (sc.why || "이 출력까지 가는 입력 조합을 찾지 못했습니다")); return; }
      const rows = {}, keys = [];
      for (const [k, val] of Object.entries(needOf(sc.forces))) if (k.startsWith("row:") && val === 1) { rows[k.slice(4)] = 1; keys.push(k); }
      await flashNeed(keys);
      window.opener.postMessage({ type: "macro-need", parent: MACRO_FROM.parent, block: MACRO_FROM.block, rows, fresh: false }, location.origin);
      return;
    }
  }
  // L45 — Typical 안의 선 · 블록(S-R 래치 앞뒤 게이트 …)도 부모 장에 펼친 이름으로 준다.  값은 그 묶음 계산이 정한다
  const pk = macroParentKey(key);
  if (!pk) { status(`이 항목은 부모 시트(${ln.sheet_no || ""})에서 주세요`); return; }
  window.opener.postMessage({ type: "macro-set", parent: MACRO_FROM.parent, block: MACRO_FROM.block, key: pk, value: v }, location.origin);
  status(`${v === null ? "풀기" : v + " 로 줌"} — 부모 시트(${ln.sheet_no || ""})의 매크로 안에서 계산합니다`);
}
/* 새 창의 강제 열쇠 → 부모 장에 펼친 이름 (단자 선은 부모 선 이름 그대로) */
function macroParentKey(key) {
  const bid = MACRO_FROM.block, al = (L.macroLink || {}).alias || {};
  const netKey = (n) => "net:" + (al[String(n)] || `${bid}/${n}`);
  const i = key.indexOf(":"), kind = key.slice(0, i), id = key.slice(i + 1);
  if (kind === "net") return netKey(id);
  if (kind === "block" || kind === "hold") return `${kind}:${bid}/${id}`;
  if (kind === "row") {
    const r = L.sheet.rows.find((x) => x.n === Number(id) && x.net != null);
    return r ? netKey(r.net) : null;
  }
  return null;
}
/* 부모 장의 강제 → 새 창(Typical) 열쇠 — 새 창이 강제 표시를 그리게 */
function macroChildForces(f, bid, alias) {
  const back = {};
  for (const [tn, nm] of Object.entries(alias || {})) back[nm] = tn;
  const out = {};
  for (const [k, v] of Object.entries(f || {})) {
    const i = k.indexOf(":"), kind = k.slice(0, i), id = k.slice(i + 1);
    if (id.startsWith(bid + "/")) out[`${kind}:${id.slice(bid.length + 1)}`] = v;
    else if (kind === "net" && back[id] !== undefined) out["net:" + back[id]] = v;
  }
  return out;
}
/* 부모 창 쪽 — 새 창이 값을 달라 할 때 · 새 창의 입력 행을 부모 시트의 실제 행으로 줄 때 */
async function handleMacroAsk(d, src) {
  if (!L.job || MACRO_FROM) return;
  const key = `${d.parent}:${d.block}`;
  if (src && (!L.childWins[key] || L.childWins[key].win !== src)) L.childWins[key] = { win: src, page: Number(d.parent), bid: d.block };
  if (L.mode !== "sim") { setMode("sim"); return; }          // runSim → sendMacroInputs
  if ((L.macroInner || {})[key]) sendMacroInputs();
  else runSim(false);
}
async function handleMacroSet(d) {
  if (!L.job || MACRO_FROM) return;
  const page = Number(d.parent);
  let s = L.page === page ? L.sheet : null;
  if (!s) { try { s = await getSheet(page); } catch (e) { return; } }
  const m = ((s.blocks[d.block] || {}).macro) || {};
  let x = null, pr = null, k = d.key || null;            // L45 — 새 창이 펼친 이름으로 준 열쇠
  if (!k) {
    x = (m.inputs || []).find((p) => p.row === Number(d.row) && p.net != null);
    if (!x) return;
    pr = s.rows.find((r) => r.side === "L" && r.net === x.net);
    k = pr ? "row:" + pr.n : "net:" + x.net;
  }
  const f = { ...(L.allForces[page] || {}) };
  if (d.value === null || d.value === undefined) delete f[k]; else f[k] = d.value === 1 ? 1 : 0;
  L.allForces[page] = f;
  if (page === L.page) L.forces = f;
  if (L.mode !== "sim") setMode("sim", true);
  status(`매크로 새 창 — ${s.sheet_no} ${pr ? pr.n + "행" : x ? "단자 " + (x.pin || "") : "매크로 안 " + k.split(":")[0]} 을 ${d.value == null ? "풀기" : d.value}`);
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
  if (L.macroLink) {
    const ln = L.macroLink, on = (ln.links || []).filter((x) => x.side === "L" && macroRowOn(x.row));
    el.innerHTML = `<b>매크로 내부 동작</b> — ${esc(MACRO_FROM.from || ln.sheet_no || "부모 시트")} 의 실제 입력·출력 행과 이어져 있습니다 · ` +
      `켜진 입력 ${on.length ? on.map((x) => esc(macroRowLabel(x))).join(", ") : "없음"} <small>(값은 부모 시트의 계산 그대로 · 입력 행을 누르면 부모 시트의 그 행에 줍니다)</small>`;
    return;
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
  if (b.func === "UNKNOWN" || (b.user && e.altKey)) { gateMenu(bid, e); paint(); renderInfo(); return; }   // L22
  const hasIn = L.sheet.ports.some((p) => p.block === bid && p.dir === "in");
  if (monKind(b)) monitorMenu(bid, e);                             // L26 — 감시 블록 (HHH · HH …) 설정값 (어느 모드든)
  else if (b.aop) opMenu(bid, e);                                  // L30 — 아날로그 연산자 판 (어느 모드든)
  else if (isAnalogBlock(b)) analogMenu("block:" + bid, e);        // L26 — MED 같은 아날로그 블록 값 (어느 모드든)
  // L34 — 누름단추 · 신호원은 어느 모드에서든 1 활성 / 0 비활성 메뉴 (입력 행 동그라미와 같다 · 따라가기는 메뉴 안에)
  else if (!hasIn && b.logic === "source") forceMenu("block:" + bid, e, pressLabel(b));
  else if (L.mode === "trace" && e.shiftKey) traceFrom("block:" + bid, true);
  else if (!hasIn || b.logic === "source") forceMenu("block:" + bid, e, b.label || b.func || "신호원");
  else gateOutMenu(bid, e);                                        // L49 — 모든 게이트: 이 출력이 켜지려면 (어느 모드든)
  paint(); renderInfo();
}
/* L49 — 입력이 있는 게이트를 누르면: 이 출력이 켜지려면 무엇이 필요한가 · 따라가기 · 시간 */
function gateOutMenu(bid, e) {
  closeForceMenu();
  const b = L.sheet.blocks[bid];
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu";
  m.innerHTML = `<div class="fm-h">${esc(b.label || b.func || "게이트")}${b.logic && GATE_KO_SHORT[b.logic] ? ` <span class="fm-kind dg">${esc(GATE_KO_SHORT[b.logic])}</span>` : ""}</div>` +
    `<button data-g="needs" class="v1">🔍 이 출력이 켜지려면 — 필요한 신호</button>` +
    (TIMER_LOGIC.has(b.logic) ? `<button data-g="timer" class="vt">⏱ 시간 바꾸기</button>` : "") +
    (L.mode === "trace" ? `<button data-g="down" class="vt">↪ 연결만 따라가기</button><button data-g="up" class="vt">↩ 거슬러 올라가기</button>` : "");
  placeMenu(m, e);
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const btn = ev.target.closest("button");
    if (!btn) return;
    closeForceMenu();
    if (btn.dataset.g === "needs") needsOpen("block:" + bid);
    else if (btn.dataset.g === "timer") timerMenu(bid, ev);
    else traceFrom("block:" + bid, btn.dataset.g === "up");
  });
}
const GATE_KO_SHORT = { and: "AND", nand: "NAND", or: "OR", nor: "NOR", not: "NOT", memory: "메모리", delay_on: "켜짐 지연", delay_off: "꺼짐 지연", pulse: "펄스", step: "STEP", source: "신호원" };
function onRow(n, e) {
  const row = L.sheet.rows.find((r) => r.n === n);
  L.sel = { row: n, net: row && row.net };
  // L9 — 입력 동그라미는 어느 모드에서든 1 활성 / 0 비활성 메뉴 (사용자 지시).  출력 행은 따라가기 그대로.
  if (row) forceMenu("row:" + n, e, `${row.side === "L" ? "입력" : "출력"} ${n}` + (row.desc ? " · " + row.desc : ""),
                     row.side === "R");
  paint(); renderInfo();
}

/* ------------------------------------------------------------------ L22 — 사람이 정한다: 게이트 종류 · FM/TO 칸

   도면에서 판정하지 못한 블록은 눌러서 종류를 고르면 그 게이트로 그려지고 그대로 시뮬레이션된다.  값은 서버
   (overrides.json)에 남아 다른 사람 · 다시 분석해도 그대로이고, 블록 안에 글자가 있으면 그 모양이 학습 사전에 들어가
   다른 프로젝트의 같은 모양도 그 기준으로 읽힌다.  FM / TO 칸을 못 읽었으면 그 칸을 눌러 값을 적으면 이어진다. */
const GATE_GROUPS = [["게이트", ["AND", "OR", "NOT", "NAND", "NOR", "VOTE"]], ["타이머", ["GT", "DT", "PD"]],
  ["메모리", ["MEMORY", "MEMORY_S", "MEMORY_R"]], ["입력 · 출력", ["PB", "SIGNAL", "CONST1", "CONST0", "ANN", "ANALOG"]]];
function keySpecific(k) {
  const tx = String(k || "").split("|")[1];
  return tx != null && tx.trim() !== "" && tx.trim() !== "?";
}
function choiceLabel(c) { const x = (L.choices || []).find((y) => y.key === c); return x ? x.label : c; }
function placeMenu(m, e) {
  document.body.appendChild(m);
  const x = (e && e.clientX) || innerWidth / 2, y = (e && e.clientY) || innerHeight / 2;
  const r = m.getBoundingClientRect();
  m.style.left = Math.max(4, Math.min(x + 8, innerWidth - r.width - 4)) + "px";
  m.style.top = Math.max(4, Math.min(y + 8, innerHeight - r.height - 4)) + "px";
}
function gateMenu(bid, e) {
  closeForceMenu();
  const b = L.sheet.blocks[bid];
  const u = b.user;
  const same = keySpecific(b.key) ? Object.values(L.sheet.blocks).filter((x) => x.key === b.key && (x.user ? x.user.was_func : x.func) === "UNKNOWN").length : 0;
  const vote = String(b.label || "").match(/(\d+)\D+(\d+)/);
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu gate-menu";
  m.innerHTML = `<div class="fm-h">이 블록은 무엇인가요?</div>
    <div class="fm-why">${u ? `지금: <b>${esc(choiceLabel(u.choice))}</b> — ${esc(u.author)} 이 정함 · 도면 판정은 ${esc(FUNC_KO[u.was_func] || u.was_func || "")}`
      : `도면에서 판정하지 못했습니다${b.read ? ` — 읽은 글자 '${esc(b.read)}'` : ""}`}</div>` +
    GATE_GROUPS.map(([g, cs]) => `<div class="gm-g"><span>${g}</span>${cs.map((c) =>
      `<button data-c="${c}" class="${u && u.choice === c ? "on" : ""}">${esc(choiceLabel(c))}</button>`).join("")}</div>`).join("") +
    `<label class="fm-t gm-vote">투표 <input id="gm-a" type="number" min="1" max="32" value="${vote ? vote[1] : 2}"> / <input id="gm-b" type="number" min="1" max="32" value="${vote ? vote[2] : 3}"> <small>B 개 중 A 개 이상이면 1</small></label>` +
    (keySpecific(b.key) ? `<label class="fm-t"><input id="gm-same" type="checkbox" checked> 같은 모양 · 같은 글자('${esc(String(b.key).split("|")[1])}')의 판정 못 한 블록에도${same > 1 ? ` (이 장 ${same}개 · 다른 장 포함)` : " (다른 장 포함)"} — 학습 사전에 남겨 다른 프로젝트도 이 기준으로</label>` : "") +
    `<button data-aop="1" class="vt">∿ 아날로그 연산자 (∑ · △ · ÷ · × · A · T …) 로 정하기</button>` +
    (u ? `<button data-c="x" class="vx">도면 판정으로 되돌리기</button>` : "");
  placeMenu(m, e);
  m.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    if (ev.target.closest("button[data-aop]")) { closeForceMenu(); opMenu(bid, ev, true); return; }   // L30
    const btn = ev.target.closest("button[data-c]");
    if (!btn) return;
    const c = btn.dataset.c === "x" ? null : btn.dataset.c;
    const param = c === "VOTE" ? { a: Number(m.querySelector("#gm-a").value), b: Number(m.querySelector("#gm-b").value) } : undefined;
    const sameOn = !!(m.querySelector("#gm-same") || {}).checked;
    closeForceMenu();
    await saveGate(bid, c, param, sameOn);
  });
}
async function saveGate(bid, choice, param, same) {
  const who = await needAuthor();
  if (!who) { status("이름이 없어 저장하지 않았습니다"); return; }
  try {
    const r = await post(`/logic/api/jobs/${L.job}/overrides/block`, { page: L.page, block: bid, choice, author: who, param, same_shape: same });
    const n = (r.set || []).length;
    status(choice ? `${n}개 블록을 ${choiceLabel(choice)} 로 정했습니다 (${who})` + (r.learned ? " · 학습 사전에 남겼습니다 — 다른 프로젝트의 같은 모양도 이 기준으로 읽습니다" : "")
      : `블록 ${bid} 를 도면 판정으로 되돌렸습니다`);
  } catch (err) { status("저장하지 못했습니다 — " + err.message); return; }
  await refreshSheet();
}
function cellEditor(t, e) {
  closeForceMenu();
  const field = t.side === "L" ? "fm" : "to";
  const name = t.side === "L" ? "FM (어디서 오는 신호)" : "TO (어디로 가는 신호)";
  const u = t.user && t.user[field];
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu";
  m.innerHTML = `<div class="fm-h">${t.n}행 ${name}</div>
    <div class="fm-why">${u ? `사람이 적음 — ${esc(u.author)} · 도면 글자 '${esc(u.was || "(비어 있음)")}'` : `도면 글자: '${esc(t[field] || "(읽지 못함)")}'`}</div>
    <label class="fm-t">값 <input id="fm-cell" type="text" maxlength="120" value="${esc(t[field] || "")}" placeholder="예: G031-81" style="width:160px"></label>
    <div class="fm-why" style="color:var(--soft)">시트-행 꼴(G031-81)이면 그 행과 이어지고 From-To 점검이 다시 돕니다.  여럿은 쉼표로.</div>
    <button data-t="ok" class="v1">저장 — 이 값으로 잇기</button>
    ${u ? `<button data-t="x" class="vx">도면 글자로 되돌리기</button>` : ""}`;
  placeMenu(m, e);
  const inp = m.querySelector("#fm-cell");
  inp.focus(); inp.select();
  const ok = () => { const v = inp.value.trim(); closeForceMenu(); saveCell(t.side, t.n, v); };
  inp.addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) ok(); if (ev.key === "Escape") closeForceMenu(); });
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const btn = ev.target.closest("button");
    if (!btn) return;
    if (btn.dataset.t === "ok") ok(); else { closeForceMenu(); saveCell(t.side, t.n, null); }
  });
}
async function saveCell(side, n, value) {
  const who = await needAuthor();
  if (!who) { status("이름이 없어 저장하지 않았습니다"); return; }
  try {
    const r = await post(`/logic/api/jobs/${L.job}/overrides/cell`, { page: L.page, side, row: n, value, author: who });
    const f = r.ft;
    const what = side === "L" ? "FM" : "TO";
    status(value == null ? `${n}행 ${what} 을 도면 글자로 되돌렸습니다`
      : `${n}행 ${what} = ${value} (${who})` + (f ? (f.ok === false ? ` — ✕ 아직 맞지 않습니다: ${(f.why || []).join(" · ")}` : f.ok ? " — ✓ 연결이 맞습니다" : "") : " — 시트-행 꼴이 아니라 잇지 못했습니다"));
  } catch (err) { status("저장하지 못했습니다 — " + err.message); return; }
  await refreshSheet();
}
/* 사람이 정한 값이 바뀌면 지금 장 · 장 목록 · 묶음 점검을 다시 받는다 (확대 · 위치는 그대로) */
async function refreshSheet() {
  const id = L.job, page = L.page;
  sheetCacheClear();                               // L31 — 사람 값은 다른 시트에도 얹힐 수 있다 (같은 모양 전부 · 가르치기)
  const [j, s] = await Promise.all([api(`/logic/api/jobs/${id}/sheets`), getSheet(page)]);
  if (L.job !== id || L.page !== page) return;
  if (j.sheets) { L.sheets = j.sheets; renderSheetList(); }
  L.sheet = s;
  $("#sheet-head").textContent = `${s.sheet_no} · ${s.title}`;      // 시트 이름을 가르치거나 마크업하면 머리도 (L25)
  L.states = {}; L.state = null; L.values = {};
  drawOverlay(); renderRows(); renderFindings(); renderInfo(); renderLatches();
  api(`/logic/api/jobs/${id}/findings`).then((f) => { if (L.job === id) { L.all = f; renderAll(); } }).catch(() => {});
  if (L.mode === "sim") runSim();
}

/* ------------------------------------------------------------------ 오른쪽 판 */

function valTag(v) {
  if (L.mode !== "sim") return "";
  return v === 1 ? `<span class="val v1">1</span>` : `<span class="val v0">0</span>`;
}
/* L29 — 행 목록의 입력 칩: 아날로그 입력은 '∿ 12 mA = 125 barg' (누르면 값 넣기) · 디지털로 준 것은 '1 활성 ✎' */
function sigChip(key) {
  const n = signalNow(key);
  if (n.kind === "analog")
    return `<button class="sigchip an${n.user ? " user" : ""}" data-an-row="${esc(key)}" title="아날로그 입력 — ${esc(n.how)} · 눌러서 값 넣기">${esc(n.text)}${n.user ? " ✎" : ""}</button>`;
  if (n.user) return `<span class="sigchip dg v${n.v}" title="디지털 — 내가 줌">${esc(n.text)} ✎</span>`;
  return "";
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
    const toRest = refRest(r.to);
    const to = r.side === "R" && toRest ? ` <small>${/^TO\b/.test(toRest) ? "" : "TO "}${esc(toRest)}</small>` : "";   // 도면이 'TO DRIVE' 로 적으면 그대로 (L23)
    const tr = (s.table || []).find((x) => x.side === r.side && x.n === r.n);
    const uc = tr && tr.user && tr.user[r.side === "L" ? "fm" : "to"];
    const ed = tr ? `<button class="mini ed${uc ? " on" : ""}" data-cell="${r.side}:${r.n}" title="${r.side === "L" ? "FM" : "TO"} 칸 값 적기 · 고치기${uc ? ` — 사람이 적음 (${esc(uc.author)})` : ""}">✎${r.side === "L" ? "FM" : "TO"}</button>` : "";
    const ex = r.side === "R" && r.net != null ? `<button class="mini ex" data-ex="row:${r.n}" title="이 출력까지 입력부터 모든 신호가 서는 동작 예시를 찾아 보여 줍니다">⚡예시</button>` : "";
    const right = (L.mode === "sim" ? (r.side === "L" ? sigChip("row:" + r.n) : "") + forceBtns("row:" + r.n) + valTag(L.values[r.net]) : "") + ex + ed;
    const bad = r.ft && r.ft.ok === false;
    const warn = !bad && r.ft && r.ft.warn && r.ft.warn.length;
    const ftl = r.ft ? `<span class="ftline ${bad ? "bad" : warn ? "warn" : r.ft.ok ? "ok" : ""}">${ftText(r)}</span>` : "";
    const ml = MACRO_FROM && L.macroLink && s.page === MACRO_FROM.target ? macroLinkOf(r.side, r.n) : null;
    const pr = ml && (ml.rows || [])[0];
    const mlk = ml ? ` <span class="mlk${L.values[r.net] === 1 ? " hot" : ""}" title="매크로 단자 ${esc(ml.pin)}">${r.side === "L" ? "←" : "→"} ${pr ? `${esc(L.macroLink.sheet_no || "")}-${pr.n} ${esc(pr.desc)}` : ml.src ? `${esc(L.macroLink.sheet_no || "")} ${esc(ml.src)}` : "단자"} (${esc(ml.pin)})</span>` : "";
    return `<li data-row="${r.n}" class="${bad ? "ftbad" : warn ? "ftwarn" : ""}"><span class="n">${r.n}</span><span class="d" title="${esc(r.desc || "")}">${esc(r.desc || "(글 없음)")}${mlk}${ref}${to}${ins}${lk}${ftl}</span><span>${right}</span></li>`;
  };
  const rows = [...s.rows].sort((a, b) => a.n - b.n);
  $("#in-rows").innerHTML = rows.filter((r) => r.side === "L").map(mk).join("") || "<li>없음</li>";
  $("#out-rows").innerHTML = rows.filter((r) => r.side === "R").map(mk).join("") || "<li>없음</li>";
  for (const b of document.querySelectorAll("#in-rows button[data-an-row]"))
    b.onclick = (ev) => {
      ev.stopPropagation();
      const k = b.dataset.anRow, r = s.rows.find((x) => x.side === "L" && x.n === Number(k.slice(4)));
      forceMenu(k, ev, `입력 ${k.slice(4)}` + (r && r.desc ? " · " + r.desc : ""));
    };
  for (const b of document.querySelectorAll("#out-rows button[data-ex]"))
    b.onclick = (ev) => { ev.stopPropagation(); runScenario(b.dataset.ex); };
  for (const b of document.querySelectorAll(".lg-rows button[data-cell]"))
    b.onclick = (ev) => {
      ev.stopPropagation();
      const [side, n] = b.dataset.cell.split(":");
      const tr = (s.table || []).find((x) => x.side === side && x.n === Number(n));
      if (tr) cellEditor(tr, ev);
    };
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
  const anList = L.mode === "sim" ? analogGivenItems() : [];
  const nUser = pages.reduce((a, c) => a + (c.forced || []).length, 0) + anList.length;
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
    sec("내가 준 디지털 신호", `${forced.length}개 · 1 활성 / 0 비활성 · 모든 시트`, forced, "아직 준 신호가 없습니다 — 입력 행의 동그라미를 눌러 1 을 주세요.") +
    (anList.length ? sec("내가 넣은 아날로그 값", `${anList.length}개 · 4~20 mA · 모든 시트`, anList, "") : "") +
    (chained.length ? sec("줄줄이 켬", `${chained.length}개 · 자동`, chained, "") : "") +
    (unmet.length ? sec("나가지 않은 출력", `${unmet.length}개 · 이 시트`, unmet, "") : "") +
    sec("나간 출력", `${nOut}개 · 1 인 출력 행`, outs, "아직 1 이 된 출력 행이 없습니다.") +
    (stops.length ? sec("신호가 닿았지만 멈춘 곳", `${stops.length}개 · 그 시트 게이트 조건이 아직 안 맞음`, stops, "") : "") +
    `<div class="sp-foot">항목을 누르면 그 시트 그 행으로 갑니다 · 오른쪽 '끄기' 로 그 신호만 풉니다 (다른 시트에 있어도).</div>`;
  $("#sigpop-sum").textContent = `신호 ${forced.length}${anList.length ? ` · 아날로그 ${anList.length}` : ""} → 출력 ${nOut}`;
  placeSigPop();
}
/* L29 — 사람이 넣은 아날로그 값 (모든 시트) — 신호 현황 창의 한 구획 */
function analogGivenItems() {
  const out = [];
  for (const [p, vals] of Object.entries(L.analog || {})) {
    const page = Number(p), sh = ((L.sheets || []).find((x) => x.page === page) || {}).sheet_no || "p" + page;
    for (const [key, ma] of Object.entries(vals)) {
      if (key.startsWith("net:")) {            // L30 — 연산자 판에서 그 입력선에 바로 넣은 공학값
        out.push(`<li data-page="${page}" data-sheet="${esc(sh)}" class="${page === L.page ? "cur" : ""}"><span class="van">∿</span><span class="sp-sh">${esc(sh)}</span> <span class="sp-what">선 ${esc(key.slice(4))} — <b>${fmtNum((ma || {}).eng)}</b></span><button class="sp-off" data-an-off="${esc(key)}" title="이 값을 뺍니다">끄기</button></li>`);
        continue;
      }
      let what = key.startsWith("row:") ? `${key.slice(4)}행` : `블록 ${key.slice(6)}`, eng = "";
      if (page === L.page && L.sheet) {
        if (key.startsWith("row:")) { const r = L.sheet.rows.find((x) => x.side === "L" && x.n === Number(key.slice(4))); if (r && r.desc) what += " " + r.desc; }
        else { const b = L.sheet.blocks[key.slice(6)]; if (b) what = `${b.label || FUNC_KO[b.func] || b.func}`; }
        const a = analogValueOf(key);
        if (a.eng != null) eng = ` = ${engText(a.eng, a.range)}`;
      }
      const rowAttr = key.startsWith("row:") ? `data-row="${key.slice(4)}" data-side="L"` : "";
      out.push(`<li data-page="${page}" data-sheet="${esc(sh)}" ${rowAttr} class="${page === L.page ? "cur" : ""}"><span class="van">∿</span><span class="sp-sh">${esc(sh)}</span> <span class="sp-what">${esc(what)} — <b>${fmtMa(ma)}${esc(eng)}</b></span><button class="sp-off" data-an-off="${esc(key)}" title="이 값을 뺍니다 (기본 ${DEFAULT_MA} mA 로)">끄기</button></li>`);
    }
  }
  return out;
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
    const aoff = e.target.closest("button[data-an-off]");
    if (aoff) { e.stopPropagation(); setAnalog(aoff.dataset.anOff, null, Number(aoff.closest("li").dataset.page)); return; }
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
/* ------------------------------------------------------------------ L32 — 순차 동작 시뮬레이션

   START · STOP · RUN · OPEN · CLOSE · TRIP 한 동작을 고르면 서버가 그 출력의 조건 나무를 낸다 (범례 정의를 거꾸로 —
   판정은 하지 않는다).  화면은 그 나무를 위에서부터 한 단계씩 묻고, 답마다 강제 신호를 주어 같은 시뮬레이터로 돌린다.
   OR 는 '하나를 고르세요' · 다른 시트에서 오는 조건은 '그 시트 조건부터' · from-to 가 어긋난 자리 · 새로 생긴 설계 오류 ·
   읽지 못한 게이트 입력에서는 멈춰 어떻게 할지 묻는다.  끝나면 처음부터 흐름을 그려 그 명령이 나가는지 말한다. */
const SEQ = { job: null, cmds: null, q: "", open: null, plan: null, target: null, ans: {}, sub: {}, hist: [], tries: {}, hint: {}, nofollow: {}, eff: {},
  learn: null, learnState: null, learnMap: {},
  view: "pick", cur: null, err: null, done: null, busy: false };
const ACT_KO = { START: "기동", RUN: "운전", STOP: "정지", OPEN: "열림", CLOSE: "닫힘", TRIP: "트립" };
const KIND_KO = { command: "명령", request: "요청", action: "동작", state: "상태" };
const SEQ_SKIP = new Set(["const", "loop", "default0"]);
function seqLink(p) {
  // 서버는 같은 마디를 여러 자리에서 쓰므로 마디 표 + id 로 보낸다 — 같은 id 는 같은 객체로 잇는다 (한 번 답하면 모든 자리)
  if (!p || !p.ok) return p;
  const N = p.nodes;
  for (const n of Object.values(N)) if (n.kids && typeof n.kids[0] !== "object") n.kids = n.kids.map((id) => N[id]);
  p.tree = N[p.root];
  return p;
}
function seqKeyOf(n) { return n.key ? n.page + "|" + n.key : null; }
function seqAsks(n) { return !(n.auto || SEQ_SKIP.has(n.kind) || (n.kind === "zero" && !(n.items || []).length)); }
function seqKeyAnswer(n) {
  // 같은 신호가 나무의 다른 자리에 또 나오면 (REMOTE 처럼) 같은 값을 바라는 한 다시 묻지 않는다
  const k = seqKeyOf(n);
  if (!k) return null;
  for (const id of SEQ.hist) {
    const a = SEQ.ans[id];
    if (a && a.key === k && a.want === n.want && (a.v === "yes" || a.v === "no")) return a;
  }
  return null;
}
function seqWalk() {
  // gate = 이 단계에 가장 가까운 게이트 (L37 안내 — '왜 필요한가' · '켜면 그 게이트 입력이 몇 개 차나')
  function visit(n, gates, gate) {
    const g = n.gate ? [...gates, n.gate.label] : n.via ? [...gates, n.via.text] : gates;
    const gt = n.gate ? { ...n.gate, page: n.page } : gate;
    if (n.t === "leaf") {
      if (!seqAsks(n)) return null;
      const a = SEQ.ans[n.id];
      if (!a) return seqKeyAnswer(n) ? null : { node: n, gates: g, gate: gt };
      if (a.v === "follow") {
        const sp = SEQ.sub[n.id];
        if (sp && sp.tree) return visit(sp.tree, [...g, `${n.ref.sheet}-${n.ref.row} 의 조건`], null);
      }
      return null;
    }
    if (n.t === "any") {
      const a = SEQ.ans[n.id];
      if (!a) return { node: n, gates: g, gate: gt };
      return visit(n.kids[a.v], g, gt);
    }
    for (const k of n.kids) { const r = visit(k, g, gt); if (r) return r; }
    return null;
  }
  return SEQ.plan && SEQ.plan.tree ? visit(SEQ.plan.tree, [], null) : null;
}
function seqRemain() {
  // 아직 답하지 않은 단계 수 (고른 갈래 · 권하는 갈래를 따라 — 대략의 총 단계)
  const seen = new Set();
  let c = 0;
  function visit(n) {
    if (n.t === "leaf") {
      if (!seqAsks(n) || SEQ.ans[n.id] || seqKeyAnswer(n)) {
        const a = SEQ.ans[n.id];
        if (a && a.v === "follow") { const sp = SEQ.sub[n.id]; if (sp && sp.tree) visit(sp.tree); }
        return;
      }
      const k = seqKeyOf(n) || n.id;
      if (!seen.has(k)) { seen.add(k); c++; }
      return;
    }
    if (n.t === "any") {
      const a = SEQ.ans[n.id];
      if (!a) c++;
      return visit(n.kids[a ? a.v : SEQ.hint[n.id] != null ? SEQ.hint[n.id] : (n.pick || 0)]);
    }
    n.kids.forEach(visit);
  }
  if (SEQ.plan && SEQ.plan.tree) visit(SEQ.plan.tree);
  return c;
}
async function seqEffect(st) {
  // L37 — 이 신호를 지금 켜면 무엇이 달라지나: 지금까지의 답 + 이 신호만으로 묶음을 돌려 앞뒤 차이를 받는다 (짐작 없음)
  const n = st.node;
  if (SEQ.eff[n.id] || !n.key) return;
  SEQ.eff[n.id] = "busy";
  try {
    SEQ.eff[n.id] = await post(`/logic/api/jobs/${L.job}/sequence/effect`, { page: SEQ.target.page, net: SEQ.target.net, want: SEQ.target.want,
      forces: seqForces(), add: { [n.page]: { [n.key]: n.want } }, timers: L.timers,
      gate: st.gate && st.gate.block ? { block: st.gate.block, page: st.gate.page } : null });
  } catch (e) { SEQ.eff[n.id] = "fail"; }
  if (SEQ.cur && SEQ.cur.node.id === n.id) renderSeq();
}
const SEQ_KIND_SAY = {
  row: "다른 곳에서 들어오는 입력 신호", button: "운전원이 누르는 단추 · HMI 명령", monitor: "아날로그 값이 설정값을 넘는지 보는 감시 신호",
  net: "도면에서 어디서 오는지 읽지 못한 선", held: "매크로(Typical) 안쪽 선", terminal: "매크로 입력 — 상자에 단자가 안 그려짐",
  stuck: "도면 읽기 빈틈 — 이 자리 값을 정할 수 없음" };
function seqGuideHtml(st) {
  // L37 — 안내 카드: 이 신호가 무엇인지 · 왜 필요한지 · 켜면 어떻게 되는지
  const n = st.node, g = st.gate;
  const what = [`<div class="gd-row"><span class="gd-k">무엇</span><span>${esc(SEQ_KIND_SAY[n.kind] || "조건")}`];
  if (n.kind === "row") {
    if (n.fm) what.push(` — <b>${esc(n.fm)}</b> 에서 옴${n.ref && n.ref.other ? " (다른 문서)" : ""}`);
    else if (n.ref && n.ref.sheet) what.push(` — <b>${esc(n.ref.sheet)}-${n.ref.row}</b> 에서 옴`);
    if (n.kks) what.push(` · <small>${esc(n.kks)}</small>`);
  }
  what.push(`</span></div>`);
  let why = "";
  if (g) {
    const need = g.logic ? gateNeedText(g.logic, g.want) : "";
    why = `<div class="gd-row"><span class="gd-k">왜</span><span><b>${esc(g.label)}</b>${need ? ` — ${esc(need)}이어야 출력 ${g.want}` : ""}</span></div>`;
  }
  const e = SEQ.eff[n.id];
  let then = "";
  if (e === "busy") then = `<span class="gd-dim">미리 돌려 보는 중…</span>`;
  else if (e === "fail" || !e) then = n.key ? `<span class="gd-dim">미리 돌려 보지 못했습니다</span>` : `<span class="gd-dim">값을 줄 자리가 없음</span>`;
  else {
    const parts = [];
    if (e.gate) {
      const gg = e.gate;
      parts.push(`<li>그 게이트 입력 ${gg.inputs}개 중 1 인 것 <b>${gg.on_before} → ${gg.on_after}</b> · 출력 <b class="v${gg.out_after}">${gg.out_before} → ${gg.out_after}</b></li>`);
    }
    const tgt = e.target || {};
    if (tgt.after === SEQ.target.want && tgt.before !== SEQ.target.want) parts.push(`<li class="gd-goal">✔ 최종 출력 <b>${esc(SEQ.target.desc)}</b> 이(가) 이것으로 나갑니다${tgt.steady ? "" : " (잠깐 · 펄스)"}</li>`);
    else if (tgt.after === SEQ.target.want) parts.push(`<li class="gd-goal">최종 출력은 이미 ${SEQ.target.want}</li>`);
    const rest = seqRemain() - 1;
    if (tgt.after !== SEQ.target.want) parts.push(`<li>최종 출력은 아직 — 남은 단계 약 ${Math.max(rest, 0)}개</li>`);
    const gn = (e.gained || []).filter((x) => !(x.page === SEQ.target.page && x.row === SEQ.target.row));
    if (gn.length) parts.push(`<li>새로 켜지는 출력: ${gn.slice(0, 4).map((x) => `<b>${esc(x.sheet)}-${x.row}</b> ${esc(x.desc)}`).join(" · ")}${gn.length > 4 ? ` 외 ${gn.length - 4}` : ""}</li>`);
    if ((e.linked || []).length) parts.push(`<li>다른 시트로 넘어감: ${e.linked.slice(0, 3).map((x) => `<b>${esc(x.sheet)}-${x.row}</b>`).join(" · ")}${e.linked.length > 3 ? ` 외 ${e.linked.length - 3}` : ""}</li>`);
    if (!parts.length || (!e.gate && !gn.length && !(e.linked || []).length && e.nets === 0 && tgt.after !== SEQ.target.want)) parts.push(`<li class="gd-dim">혼자서는 아직 바뀌는 것 없음 — 다른 조건과 함께 필요</li>`);
    then = `<ul class="gd-list">${parts.join("")}</ul>`;
  }
  return `<div class="sq-guide">${what.join("")}${why}<div class="gd-row"><span class="gd-k">${n.want ? "켜면" : "0 이면"}</span><div>${then}</div></div></div>`;
}
function seqForces(assume) {
  // assume = {id, i} — 갈래를 미리 돌려 볼 때: 아직 답하지 않은 조건은 모두 '만족' 으로, 그 갈래 고르기는 i 번으로 본다
  const F = {};
  const put = (p, k, v) => { if (k) (F[p] = F[p] || {})[k] = v; };
  function visit(n) {
    if (n.t === "leaf") {
      const a = (assume && assume.leaf && assume.leaf.id === n.id ? assume.leaf : null) || SEQ.ans[n.id] || seqKeyAnswer(n);
      if (!a) {
        // 미리 돌려 볼 때 '만족' 으로 보는 것은 실제 신호(입력 행 · 누름단추 · 감시)와 읽지 못한 게이트(hold)뿐 —
        // 매크로 안쪽의 몰이를 못 읽은 선은 짐작하지 않는다 (그 선이 AUTO 모드처럼 다른 길을 막을 수 있다)
        if (assume && n.key && ["row", "button", "monitor", "stuck", "terminal", "net"].includes(n.kind) && ((F[n.page] || {})[n.key] !== 1)) put(n.page, n.key, n.want);
        return;
      }
      if (a.v === "follow") { const sp = SEQ.sub[n.id]; if (sp && sp.tree) visit(sp.tree); return; }
      if (n.kind === "zero") { if (a.item != null) { const it = n.items[a.item]; put(n.page, it.key, 1); } return; }
      if (a.v === "yes") put(n.page, n.key, n.want);
      else if (a.v === "no" && !(n.key || "").startsWith("hold:")) put(n.page, n.key, 1 - n.want);
      return;
    }
    if (n.t === "any") {
      const a = SEQ.ans[n.id];
      if (a) visit(n.kids[a.v]);
      else if (assume) visit(n.kids[assume.id === n.id ? assume.i : (assume.choice && assume.choice[n.id] != null ? assume.choice[n.id]
        : SEQ.hint[n.id] != null ? SEQ.hint[n.id] : (n.pick || 0))]);
      return;
    }
    n.kids.forEach(visit);
  }
  if (SEQ.plan && SEQ.plan.tree) visit(SEQ.plan.tree);
  return F;
}
async function seqTryLeaf(n) {
  // 이 단계의 답마다 (만족 · 만족 안 됨 · 건너뛰기) — 남은 조건은 모두 만족으로 보고 미리 돌려 본다
  if (SEQ.tries[n.id]) return;
  SEQ.tries[n.id] = "busy";
  const vs = ["yes", "no", "skip"];
  try {
    const r = await post(`/logic/api/jobs/${L.job}/sequence/try`, { page: SEQ.target.page, net: SEQ.target.net, want: SEQ.target.want,
      forces: {}, options: vs.map((v) => seqForces({ leaf: { id: n.id, v } })), timers: L.timers });
    const o = {};
    vs.forEach((v, i) => { o[v] = (r.options || [])[i] || {}; });
    SEQ.tries[n.id] = o;
  } catch (e) { SEQ.tries[n.id] = "fail"; }
  if (SEQ.cur && SEQ.cur.node.id === n.id) renderSeq();
}
async function seqTry(n) {
  // 갈래마다 — 지금까지의 답 + 이 갈래 + 남은 조건은 모두 만족 으로 같은 시뮬레이터에 돌려 본다 (짐작이 아니라 시험)
  if (SEQ.tries[n.id]) return;
  SEQ.tries[n.id] = "busy";
  // 갈래 안에 또 갈래가 있으면 그 조합도 몇 개 함께 돌려 본다 (갈래마다 TRY_PER 개까지) — 선 조합은 다음 단계의 권장이 된다
  const TRY_PER = 12;
  const variants = [];
  n.kids.forEach((k, i) => {
    const inner = [];
    const walk = (x) => { if (inner.length >= 5) return; if (x.t === "any") inner.push(x); (x.kids || []).forEach(walk); };
    walk(k);
    let combos = [{}];
    for (const a of inner) {
      const next = [];
      for (const c of combos) for (let j = 0; j < a.kids.length; j++) next.push({ ...c, [a.id]: j });
      combos = next;
      if (combos.length >= TRY_PER) break;
    }
    // 서버가 권한 갈래 조합을 맨 앞에
    combos.sort((x, y) => Object.entries(x).filter(([id, j]) => (seqNodeById(id) || {}).pick !== j).length -
                          Object.entries(y).filter(([id, j]) => (seqNodeById(id) || {}).pick !== j).length);
    for (const c of combos.slice(0, TRY_PER)) variants.push({ i, choice: c });
  });
  try {
    const r = await post(`/logic/api/jobs/${L.job}/sequence/try`, { page: SEQ.target.page, net: SEQ.target.net, want: SEQ.target.want,
      forces: {}, options: variants.map((v) => seqForces({ id: n.id, i: v.i, choice: v.choice })), timers: L.timers });
    const out = n.kids.map(() => ({ reached: false, steady: false }));
    (r.options || []).forEach((o, j) => {
      const v = variants[j], cur = out[v.i];
      if (o.reached && (!cur.reached || (o.steady && !cur.steady))) { out[v.i] = { ...o, choice: v.choice }; }
    });
    SEQ.tries[n.id] = out;
  } catch (e) { SEQ.tries[n.id] = "fail"; }
  if (SEQ.cur && SEQ.cur.node.id === n.id) renderSeq();
}
function seqSheetName(page) { const s = (L.sheets || []).find((x) => x.page === page); return s ? s.sheet_no || "p" + page : "p" + page; }
async function seqOpen() {
  const box = $("#seq");
  if (!L.job) return;
  box.hidden = false;
  $("#seq-btn").classList.add("on");
  if (SEQ.job !== L.job) { Object.assign(SEQ, { job: L.job, cmds: null, plan: null, view: "pick", hist: [], ans: {}, sub: {} }); }
  placeSeq();
  if (!SEQ.cmds) {
    $("#seq-b").innerHTML = `<div class="sp-empty">묶음에서 START · STOP · OPEN · CLOSE · TRIP 행을 찾는 중…</div>`;
    try { SEQ.cmds = (await api(`/logic/api/jobs/${L.job}/commands`)).items || []; }
    catch (e) { $("#seq-b").innerHTML = `<div class="sp-empty">${esc(e.message)}</div>`; return; }
  }
  renderSeq();
  seqLoadLearn();
}
/* L33 — 동작 학습: 서버가 모든 명령을 시뮬레이터로 켜고 꺼 보며 배운 것 (명령마다 선다/안 선다 · 꼭 필요한 신호 · 막힌 자리).
   없거나 결과 · 사람 값이 바뀌었으면 서버가 뒤에서 다시 배우고, 화면은 그동안 몇 개째인지 보인다. */
async function seqLoadLearn() {
  if (!L.job) return;
  const job = L.job;
  let r;
  try { r = await api(`/logic/api/jobs/${job}/behavior`); } catch (e) { return; }
  if (job !== L.job) return;
  SEQ.learnState = r;
  SEQ.learn = r.result && r.state === "done" ? r.result : (r.result || null);
  SEQ.learnMap = {};
  for (const x of (SEQ.learn && SEQ.learn.items) || []) SEQ.learnMap[x.page + ":" + x.row] = x;
  renderSeq();
  if (r.state === "running" && !$("#seq").hidden) setTimeout(seqLoadLearn, 3000);
}
function seqLearned(page, row) { return SEQ.learnMap[page + ":" + row] || null; }
function seqLearnLine() {
  const st = SEQ.learnState;
  if (!st) return "";
  const r = SEQ.learn;
  if (st.state === "running") {
    const p = st.progress || {};
    return `<div class="sq-learn">🧠 동작을 배우는 중… ${p.total ? `${p.done}/${p.total}` : ""} — 모든 명령을 시뮬레이터로 켜고 꺼 보는 중입니다${r ? " (아래 표시는 지난번 학습)" : ""}</div>`;
  }
  if (!r) return "";
  return `<div class="sq-learn">🧠 학습한 동작 <b>${r.reached}/${r.total}</b> 이 섭니다${r.with_hold ? ` · 그중 ${r.with_hold}개는 도면 읽기 빈틈을 '만족' 으로 보고` : ""} <small>(✔ 선다 · ⛔ 안 선다 — 동작 단추에 표시)</small>
    ${r.summary ? `<button data-a="insight" class="pri sq-insbtn">🔎 이 묶음의 로직 이해 — 무엇이 켜고 · 막고 · 유지하는가</button>` : ""}</div>`;
}
/* L35 — 로직 이해: 동작 학습이 명령마다 시뮬레이터로 켜고 · 막고 · 놓아 보고 · 꺼 본 결과를 사람 말로.
   판정은 서버 학습(behavior.understand)이 이미 했다 — 화면은 옮겨 적기만 한다. */
function lblList(ls, cls) {
  return `<ul class="${cls || ""}">${(ls || []).map((l) => `<li><span class="v${l.value}">${l.value}</span> <b>${esc(l.sheet || "")}</b> ${esc(l.text)}${l.assumed ? " <small>(빈틈)</small>" : ""}</li>`).join("")}</ul>`;
}
function understandHtml(x) {
  if (!x || !x.reached || !("always_on" in x)) return "";
  const parts = [];
  if (x.always_on) parts.push(`<div class="un-warn">⚠ <b>신호 없이도 켜져 있음</b> — 아래 신호가 와야 꺼짐 (확인)</div>`);
  if (x.tied_off) parts.push(`<div class="un-warn">⚠ <b>상수로 막힌 길뿐</b> — ${esc(x.tied_off[0])}</div>`);
  if (x.latch === true) parts.push(`<div class="un-ok">● <b>자기유지</b> — ${x.latch_released === "buttons" ? "단추를 놓아도" : "신호를 거둬도"} 유지</div>`);
  else if (x.latch === false) parts.push(`<div class="un-mid">○ <b>누르는 동안만</b> — ${x.latch_released === "buttons" ? "단추를 놓으면" : "신호를 거두면"} 꺼짐</div>`);
  else if ("latch" in x) parts.push(`<div class="un-mid">⏱ <b>펄스</b> — 정해진 시간만 나가고 꺼짐</div>`);
  if ((x.interlocks || []).length) parts.push(`<div class="un-h">⛔ 막는 신호 (1 이면 안 섬)</div>${lblList(x.interlocks, "un-l")}`);
  if ((x.stoppers || []).length) parts.push(`<div class="un-h">■ 끄는 신호</div>${lblList(x.stoppers, "un-l")}`);
  if ((x.drops || []).length) parts.push(`<div class="un-h">↓ 0 이 되면 꺼지는 허가</div>${lblList(x.drops, "un-l")}`);
  if (!parts.length) return "";
  return `<div class="sq-under"><div class="un-t">🔎 로직 이해</div>${parts.join("")}</div>`;
}
function seqInsightHtml() {
  const r = SEQ.learn, s = r && r.summary;
  if (!s) return `<div class="sp-empty">아직 배운 것이 없습니다.</div><div class="sq-foot"><button data-a="pickagain">◀ 동작 고르기</button></div>`;
  const items = r.items || [];
  const idx = (e) => items.findIndex((x) => x.page === e.page && x.row === e.row);
  const go = (e, t) => `<li data-li="${idx(e)}">${t}</li>`;
  const pairBoth = (s.both_on || []).map((p) => `<li class="ins-pair"><b>${esc(p.equip)}</b> — ${p.a} · ${p.b} 동시 가능
      <div class="ins-c"><span class="ins-a" data-li="${idx({ page: p.a_at[0], row: p.a_at[1] })}">${p.a}: ${esc((p.a_need || []).join(" · ") || "—")}</span>
      <span class="ins-a" data-li="${idx({ page: p.b_at[0], row: p.b_at[1] })}">${p.b}: ${esc((p.b_need || []).join(" · ") || "—")}</span></div></li>`).join("");
  const sigs = (ls, unit) => (ls || []).map((x) => `<li><b>${esc(x.sheet)}</b> ${esc(x.text)} <small>· ${x.count}개</small></li>`).join("");
  return `<div class="sq-ins">
    <div class="ins-top">🔎 <b>로직 이해</b> — 명령 ${s.commands}개</div>
    <div class="ins-cards">
      <div><b>${s.reached}</b><small>서는 명령</small></div>
      <div><b>${s.latched}</b><small>자기유지</small></div>
      <div><b>${s.momentary}</b><small>누르는 동안만</small></div>
      <div><b>${s.pulse}</b><small>펄스</small></div>
      <div><b>${s.with_interlock}</b><small>인터록 있음</small></div>
      <div class="${s.unreached ? "bad" : ""}"><b>${s.unreached}</b><small>안 섬</small></div></div>
    ${pairBoth ? `<div class="ins-h warn">⚠ 반대 명령 동시 가능 ${s.both_on.length}</div><ul>${pairBoth}</ul>` : ""}
    ${(s.always_on || []).length ? `<div class="ins-h warn">⚠ 신호 없이 켜짐 ${s.always_on.length}</div><ul>${s.always_on.map((e) => go(e, `<b>${esc(e.equip)}</b> ${e.action} <small>${esc(e.sheet)}-${e.row}</small>`)).join("")}</ul>` : ""}
    ${(s.tied_off || []).length ? `<div class="ins-h warn">⚠ 상수로 막힌 길뿐 ${s.tied_off.length}</div><ul>${s.tied_off.map((e) => go(e, `<b>${esc(e.equip)}</b> ${e.action} <small>${esc(e.sheet)}-${e.row} — ${esc(e.text)}</small>`)).join("")}</ul>` : ""}
    ${(s.common_need || []).length ? `<div class="ins-h">공통 허가</div><ul class="ins-sig">${sigs(s.common_need, "에 필요")}</ul>` : ""}
    ${(s.common_block || []).length ? `<div class="ins-h">공통 트립 · 정지</div><ul class="ins-sig">${sigs(s.common_block, "을 막음")}</ul>` : ""}
    <div class="ins-note">누르면 그 명령을 차례로 묻습니다.</div>
  </div><div class="sq-foot"><button data-a="pickagain">◀ 동작 고르기</button></div>`;
}
function seqLearnCard(t) {
  const x = seqLearned(t.page, t.row);
  if (!x) return "";
  if (!x.reached) {
    const b = x.blocked_at;
    return `<div class="sq-learncard no">🧠 <b>안 섬</b> — ${esc(x.why || "")}${
      b ? `<br><small>막힌 곳: ${esc(b.label)}</small>` : ""}</div>`;
  }
  const real = (x.labels || []).filter((l) => !l.assumed), assumed = (x.labels || []).filter((l) => l.assumed);
  return `<div class="sq-learncard">🧠 필요한 신호 <b>${real.length}개</b>${assumed.length ? ` + 빈틈 ${assumed.length}` : ""} → ${x.steady ? "섬" : "펄스"}
    <ul>${(x.labels || []).map((l) => `<li><span class="v${l.value}">${l.value}</span> <b>${esc(l.sheet || "")}</b> ${esc(l.text)}${l.assumed ? " <small>(빈틈)</small>" : ""}</li>`).join("")}</ul>
    ${understandHtml(x)}
    <button data-a="learned" class="pri">▶ 이 조합으로 돌리기</button></div>`;
}
async function seqRunLearned() {
  const x = seqLearned(SEQ.target.page, SEQ.target.row);
  if (!x || !x.reached) return;
  const F = {};
  for (const [p, fs] of Object.entries(x.forces || {})) F[Number(p)] = { ...fs };
  SEQ.ans = {}; SEQ.hist = []; SEQ.sub = {}; SEQ.tries = {};
  await seqFinish(false, F, "학습한 조합");
}
function seqClose() { $("#seq").hidden = true; $("#seq-btn").classList.remove("on"); }
function placeSeq(x, y) {
  const pop = $("#seq");
  if (x == null) {
    try { [x, y] = JSON.parse(lsGet("logic.seq.pos") || "null") || []; } catch (e) { x = y = null; }
    if (x == null) { x = innerWidth - 470 - 30; y = 96; }
  }
  const w = pop.offsetWidth || 460, h = pop.querySelector(".sp-h").offsetHeight || 30;
  pop.style.left = Math.max(4, Math.min(x, innerWidth - w - 4)) + "px";
  pop.style.top = Math.max(4, Math.min(y, innerHeight - h - 4)) + "px";
}
function seqPickHtml() {
  const q = SEQ.q.trim().toUpperCase();
  const list = (SEQ.cmds || []).filter((e) => !q || e.equip.includes(q) || e.titles.some((t) => t.toUpperCase().includes(q)) ||
    e.actions.some((a) => a.action.includes(q) || (ACT_KO[a.action] || "").includes(SEQ.q.trim())));
  const shown = list.slice(0, 120);
  const items = shown.map((e, i) => {
    const gi = SEQ.cmds.indexOf(e);
    const acts = e.actions.map((a) => {
      const lx = seqLearned(a.rows[0].page, a.rows[0].row);
      const mk = lx ? (lx.reached ? `<i class="lk ok" title="섬 · 필요 신호 ${lx.signals}개">✔</i>` : `<i class="lk no" title="안 섬 — ${esc(lx.why || "")}">⛔</i>`) : "";
      return `<button class="sq-act a-${a.action}" data-eq="${gi}" data-act="${a.action}" title="${esc(a.rows.map((r) => `${r.sheet}-${r.row} ${r.desc} (${KIND_KO[r.kind] || r.kind})`).join("\n"))}">${a.action}<small>${ACT_KO[a.action] || ""}</small>${mk}</button>`;
    }).join("");
    const open = SEQ.open && SEQ.open.eq === gi ? (e.actions.find((a) => a.action === SEQ.open.act) || {}).rows || [] : [];
    const rows = open.length ? `<ul class="sq-rows">${open.map((r, j) => `<li data-eq="${gi}" data-act="${SEQ.open.act}" data-j="${j}"><span class="sq-k k-${r.kind}">${KIND_KO[r.kind] || r.kind}</span> <b>${esc(r.sheet)}-${r.row}</b> ${esc(r.desc)}</li>`).join("")}</ul>` : "";
    return `<li class="sq-eq"><div class="sq-name">${esc(e.equip)}</div>${e.titles.length ? `<div class="sq-title">${esc(e.titles[0])}</div>` : ""}<div class="sq-acts">${acts}</div>${rows}</li>`;
  }).join("");
  return seqLearnLine() + `<div class="sq-intro">기기 · 밸브의 동작을 고르면 그 동작에 필요한 조건을 <b>도면 순서대로 하나씩</b> 묻고, 답한 대로 신호를 주며
      끝까지 시뮬레이션합니다.  중간에 정합성 오류가 있으면 그 단계에서 어떻게 할지 묻습니다.</div>
    <input id="seq-q" class="sq-q" placeholder="기기 이름 · 태그 · START/OPEN … 검색" value="${esc(SEQ.q)}">
    <div class="sq-count">장비 ${list.length}개${list.length > shown.length ? ` (앞 ${shown.length}개만 — 검색으로 좁히세요)` : ""} · 동작 단추를 누르면 그 동작의 행(명령 · 요청 · 상태)을 고릅니다</div>
    <ul class="sq-list">${items || `<li class="sp-empty">찾은 동작 행이 없습니다.</li>`}</ul>`;
}
function seqWhere(n) {
  const sh = seqSheetName(n.page);
  if (n.kind === "row") return `${sh} ${n.n}행 (입력)` + (n.fm ? ` · FM <b>${esc(n.fm)}</b>` : "");
  if (n.block) return `${sh} · 블록 ${esc(n.block)}`;
  return sh;
}
function seqWant(n) { return n.want === 1 ? `<span class="v1">1</span> 활성이어야 합니다` : `<span class="v0">0</span> 이어야 합니다 (없어야 함)`; }
function seqStepHtml() {
  const st = SEQ.cur, n = st.node;
  const crumbs = st.gates.slice(-3).map(esc).join(" › ");
  const conflict = (() => {
    const k = seqKeyOf(n);
    if (!k) return "";
    for (const id of SEQ.hist) { const a = SEQ.ans[id]; if (a && a.key === k && a.want !== n.want) return `<div class="sq-warn">앞 단계에서 이 신호를 ${a.v === "yes" ? a.want : 1 - a.want} 으로 주었습니다 — 여기서는 ${n.want} 이 필요합니다.  두 조건이 서로 반대입니다.</div>`; }
    return "";
  })();
  let body = "", btns = "";
  if (n.t === "any") {
    const tr = SEQ.tries[n.id];
    const res = Array.isArray(tr) ? tr : null;
    const okFirst = res ? res.findIndex((x) => x.reached) : -1;
    const rec = res ? okFirst : n.pick;
    body = `<div class="sq-q-t">갈래 고르기 — 다음 중 <b>하나</b>가 만족되면 됩니다</div>
      <div class="sq-note">${tr === "busy" ? "갈래마다 미리 돌려 보는 중…" : res ? (okFirst >= 0 ? "★ 는 미리 돌려 보니 목표 출력까지 서는 갈래입니다 (남은 조건은 모두 만족한다고 보고)" :
        "어느 갈래도 미리 돌려 본 결과 목표 출력이 서지 않습니다 — 도면 읽기 빈틈이나 다른 조건이 막고 있습니다") : ""}</div><ol class="sq-opts">` + n.kids.map((k, i) => {
      const s = (k.summary || []).filter(Boolean);
      const badge = res && res[i] ? (res[i].reached ? `<span class="sq-ok">✔ 서는 갈래${res[i].steady ? "" : " (잠깐 섬)"}</span>` : `<span class="sq-no">✕ 서지 않음</span>`) : "";
      return `<li><button data-a="pick" data-i="${i}" class="${i === rec ? "rec" : ""}">${i === rec ? "★ " : ""}${s.length ? s.map(esc).join(" · ") : "추가 조건 없음"}</button>
        <small>${badge} ${k.asks || 0}단계${k.viable ? "" : " · ⚠ 도면에서 다 읽지 못한 자리가 있음"}</small></li>`;
    }).join("") + `</ol>`;
    if (!tr) setTimeout(() => seqTry(n), 0);
  } else if (n.kind === "zero") {
    body = `<div class="sq-q-t">아래 신호가 <b>없어야</b> 합니다 (고장 · 트립 · 반대 명령 · 인터록) — 아무것도 주지 않으면 0 입니다</div>
      <ul class="sq-zero">${n.items.map((it, i) => `<li><span class="v0">0</span> ${esc(it.text || it.key)} <small>${esc(seqSheetName(n.page))}</small>
        <button data-a="zero1" data-i="${i}" title="이 신호를 1 로 주어 동작이 막히는지 봅니다">1 로 해서 막히는지 보기</button></li>`).join("")}</ul>`;
    btns = `<button data-a="yes" class="pri">✔ 모두 없음 — 다음</button>`;
  } else {
    const kindT = { row: "입력 신호", button: "누름단추 · HMI", monitor: "아날로그 감시", net: "도면에서 몰이를 못 읽은 선",
      held: "매크로 안쪽 선", terminal: "매크로 단자 없음", stuck: "도면 읽기 빈틈", deep: "조건이 깊음" }[n.kind] || "조건";
    body = `<div class="sq-q-t"><span class="sq-kind">${kindT}</span> ${esc(n.text)}</div>
      <div class="sq-where">${seqWhere(n)} — ${seqWant(n)}</div>` + seqGuideHtml(st);
    if (n.key && !SEQ.eff[n.id]) setTimeout(() => seqEffect(st), 0);
    if (n.ft) body += `<div class="sq-err">⚠ 정합성 오류 — ${(n.ft.why || []).map(esc).join(" · ")}${n.ft.peer ? ` <small>(${esc(n.ft.peer)})</small>` : ""}<br>
        이 신호가 FM 대로 오는지 도면이 어긋납니다.  어떻게 할까요?</div>`;
    if (n.ref && n.ref.other) body += `<div class="sq-note">다른 묶음(${esc(n.ref.sheet)})에서 오는 신호입니다 — 여기서 직접 답합니다.</div>`;
    if (n.kind === "stuck" || n.kind === "deep") body += `<div class="sq-err">도면 읽기 빈틈 — 값을 정할 수 없습니다.  어떻게 할까요?</div>`;
    const follow = n.ref && !n.ref.other && n.ref.page != null && !SEQ.nofollow[n.id];
    if (SEQ.nofollow[n.id]) body += `<div class="sq-err">${esc(n.ref.sheet)}-${n.ref.row} 의 조건을 따라갈 수 없습니다 — ${esc(SEQ.nofollow[n.id])}.  이 조건에 직접 답하거나 여기서 멈추세요.</div>`;
    const tl = SEQ.tries[n.id];
    const tr = tl && typeof tl === "object" ? tl : null;
    const canTry = ["row", "button", "monitor", "net", "held", "terminal", "stuck"].includes(n.kind) && n.key;
    if (canTry && !tl) setTimeout(() => seqTryLeaf(n), 0);
    const mark = (v) => (tr && tr[v] ? (tr[v].reached ? ` <span class="sq-ok">✔</span>` : ` <span class="sq-no">✕</span>`) : "");
    const best = tr ? ["yes", "no", "skip"].find((v) => tr[v] && tr[v].reached) : null;
    if (canTry) body += `<div class="sq-note">${tl === "busy" ? "답마다 미리 돌려 보는 중…" : tr ? (best ? `✔ 는 미리 돌려 보니 목표 출력까지 서는 답입니다 (남은 조건은 모두 만족한다고 보고)` :
      "어느 답으로도 미리 돌려 본 결과 목표 출력이 서지 않습니다 — 다른 단계에서 막히고 있을 수 있습니다") : ""}</div>`;
    const pri = (v) => (best ? best === v : v === "yes") ? "pri" : "";
    const yesT = n.kind === "button" ? (n.want ? "누르기 (1)" : "누르지 않음 (0)") : n.kind === "monitor" ? (n.want ? "설정값을 넘김 (1)" : "넘지 않음 (0)")
      : n.kind === "stuck" ? "만족으로 보고 넘어가기" : n.want ? "활성 (1)" : "없음 (0) 으로 둠";
    if (n.key && n.kind !== "deep") body += `<div class="sq-ask">${n.kind === "stuck" ? "이 자리를 만족으로 보고 넘어갈까요?" : n.want ? "이 신호를 활성시키겠습니까?" : "이 신호를 0 (없음) 으로 두겠습니까?"}</div>`;
    btns = (follow ? `<button data-a="follow" class="pri">⤵ ${n.ft ? "FM 대로 " : ""}그 시트(${esc(n.ref.sheet)}-${n.ref.row}) 조건부터 차례로</button>` : "") +
      (n.kind !== "deep" && n.key ? `<button data-a="yes" class="${follow ? "" : pri("yes")}">▶ ${yesT}${mark("yes")}</button>` : "") +
      (n.kind !== "stuck" && n.kind !== "deep" && n.key ? `<button data-a="no" class="${follow ? "" : pri("no")}">✕ 아니오 — ${1 - n.want} 로${mark("no")}</button>` : "") +
      `<button data-a="skip" class="${follow ? "" : pri("skip")}">건너뛰기${mark("skip")}</button>`;
  }
  const answered = SEQ.hist.length;
  return `<div class="sq-target"><b>${esc(SEQ.target.label)}</b> <small>${esc(SEQ.target.where)}</small></div>
    ${seqBarHtml(answered)}
    <div class="sq-prog">단계 ${answered + 1} · ${crumbs ? `<span class="sq-crumb">${crumbs}</span>` : "맨 위 조건"}</div>
    <div class="sq-card">${body}${conflict}<div class="sq-btns">${btns}
      <button data-a="look" class="ghost">🔍 도면에서 보기</button></div></div>
    <div class="sq-foot"><button data-a="back" ${answered ? "" : "disabled"}>◀ 이전 단계</button>
      <button data-a="restart">처음부터</button><button data-a="stop">여기서 멈추고 결과 보기</button><button data-a="pickagain">다른 동작 고르기</button></div>
    ${answered === 0 ? seqLearnCard(SEQ.target) : ""}
    ${seqHistHtml()}`;
}
function seqBarHtml(answered) {
  const total = answered + Math.max(seqRemain(), 1);
  const pct = Math.round(100 * answered / total);
  return `<div class="sq-bar" title="답한 단계 ${answered} · 남은 단계 약 ${total - answered}"><i style="width:${pct}%"></i><span>${answered} / 약 ${total}단계</span></div>`;
}
function seqAnsText(n, a) {
  if (!a) return "";
  if (a.v === "follow") return "그 시트 조건부터";
  if (a.v === "skip") return "건너뜀";
  if (n.t === "any") return `갈래 ${a.v + 1}`;
  if (n.kind === "zero") return a.item != null ? `${(n.items[a.item] || {}).text || ""} 를 1 로` : "모두 없음";
  if (a.v === "yes") return `${n.want} 로 줌`;
  if (a.v === "no") return `${1 - n.want} 로 줌 (만족 안 됨)`;
  return a.v;
}
function seqNodeById(id) {
  if (SEQ.plan && SEQ.plan.nodes && SEQ.plan.nodes[id]) return SEQ.plan.nodes[id];
  for (const sp of Object.values(SEQ.sub)) if (sp && sp.nodes && sp.nodes[id]) return sp.nodes[id];
  return null;
}
function seqHistHtml() {
  if (!SEQ.hist.length) return "";
  return `<h4>답한 단계 <small>${SEQ.hist.length}개 · 누르면 그 자리</small></h4><ol class="sq-hist">` + SEQ.hist.map((id) => {
    const n = seqNodeById(id); if (!n) return "";
    const a = SEQ.ans[id];
    const what = n.t === "any" ? "갈래 고르기" : (n.text || n.kind);
    return `<li data-id="${id}"><span class="sq-hs">${esc(seqSheetName(n.page))}</span> ${esc(what)} → <b>${esc(seqAnsText(n, a))}</b></li>`;
  }).join("") + `</ol>`;
}
function seqDoneHtml() {
  const d = SEQ.done;
  const ok = d.value === SEQ.target.want;
  const unmet = (d.unmet || []).map((u) => `<li>${esc((u.logic || "게이트").toUpperCase())} 출력 ${u.want} 이 나가지 않음 — ${esc(gateNeedText(u.logic, u.want))}</li>`).join("");
  return `<div class="sq-target"><b>${esc(SEQ.target.label)}</b> <small>${esc(SEQ.target.where)}</small></div>
    <div class="sq-result ${ok ? "ok" : "no"}">${SEQ.via ? `<small>${esc(SEQ.via)}으로 돌렸습니다</small><br>` : ""}${ok ? `<span class="sq-big">✔ 최종 출력 활성</span><br>${esc(SEQ.target.desc)} = <b>${SEQ.target.want}</b> — ${SEQ.hist.length}단계${SEQ.reachedEarly ? " (남은 조건 없이 섬)" : ""} · 처음부터 흐름을 그렸습니다` :
      `⛔ ${esc(SEQ.target.desc)} 이(가) ${SEQ.target.want} 이 되지 않습니다${d.stopped ? " (중간에 멈춤)" : ""}`}</div>
    ${!ok && unmet ? `<div class="sq-note">막힌 자리 (이 시트):</div><ul class="sq-unmet">${unmet}</ul>` : ""}
    ${!ok ? seqWhyNot() : ""}
    ${!ok && !SEQ.via ? seqLearnCard(SEQ.target) : ""}
    ${(d.design || []).length ? `<div class="sq-err">설계 오류 ${d.design.length}건 — 신호가 TO 를 따라가다 어긋난 연결을 만났습니다 (오른쪽 '설계 오류')</div>` : ""}
    <div class="sq-foot"><button data-a="replay" class="pri">↻ 흐름 다시 보기</button><button data-a="back" ${SEQ.hist.length ? "" : "disabled"}>◀ 마지막 단계 고치기</button>
      <button data-a="restart">처음부터</button><button data-a="pickagain">다른 동작 고르기</button></div>
    ${seqHistHtml()}`;
}
function seqWhyNot() {
  // 출력이 서지 않았을 때 — 답한 단계 가운데 무엇이 그 길을 막았을 수 있는지 (판정이 아니라 답의 목록)
  const no = [], skip = [], left = [];
  for (const id of SEQ.hist) {
    const n = seqNodeById(id), a = SEQ.ans[id];
    if (!n || !a) continue;
    const name = `${seqSheetName(n.page)} ${n.text || ""}`;
    if (a.v === "no" || (n.kind === "zero" && a.item != null)) no.push(name);
    else if (a.v === "skip") skip.push(name);
  }
  const rest = seqWalk();
  if (rest) left.push(rest.node.t === "any" ? "갈래 고르기" : `${seqSheetName(rest.node.page)} ${rest.node.text || ""}`);
  const li = (xs) => xs.slice(0, 6).map((x) => `<li>${esc(x)}</li>`).join("");
  return (no.length ? `<div class="sq-note">'만족 안 됨' 으로 답한 조건 ${no.length}개:</div><ul class="sq-unmet">${li(no)}</ul>` : "") +
    (skip.length ? `<div class="sq-note">건너뛴 조건 ${skip.length}개 (주지 않음 — 0):</div><ul class="sq-unmet">${li(skip)}</ul>` : "") +
    (left.length ? `<div class="sq-note">아직 답하지 않은 단계가 남아 있습니다: ${esc(left[0])}</div>` : "") +
    (!no.length && !skip.length && !left.length ? `<div class="sq-note">모든 조건에 답했는데도 서지 않았습니다 — 되먹임 · 타이머 · 도면 읽기 빈틈(Typical 안 게이트)을 보세요.  '◀ 마지막 단계 고치기' 로 다른 갈래를 골라 볼 수 있습니다.</div>` : "");
}
function seqErrHtml() {
  const e = SEQ.err;
  return `<div class="sq-target"><b>${esc(SEQ.target.label)}</b> <small>${esc(SEQ.target.where)}</small></div>
    <div class="sq-card"><div class="sq-err">⚠ 이 단계에서 정합성 오류 ${e.length}건이 생겼습니다 — 신호가 TO 를 따라가다 어긋난 연결을 만났습니다.</div>
    <ul class="sq-unmet">${e.slice(0, 6).map((x, i) => `<li data-ei="${i}"><b>${esc(x.sheet_no || "")}-${x.at_row || x.row}</b> ${esc(x.desc || "")} — ${esc(x.why || "")}</li>`).join("")}</ul>
    <div class="sq-q-t">어떻게 할까요?</div>
    <div class="sq-btns"><button data-a="errgo" class="pri">계속 — 다음 단계로</button><button data-a="errlook">그 행 보기</button>
      <button data-a="back">이 단계 되돌리기</button><button data-a="stop">여기서 멈추고 결과 보기</button></div></div>
    ${seqHistHtml()}`;
}
function renderSeq() {
  const b = $("#seq-b");
  if (!b || $("#seq").hidden) return;
  $("#seq").classList.toggle("min", lsGet("logic.seq.min") === "1");
  $("#seq-min").textContent = $("#seq").classList.contains("min") ? "＋" : "－";
  if (SEQ.busy) { b.innerHTML = `<div class="sp-empty">${esc(SEQ.busy)}</div>`; return; }
  b.innerHTML = SEQ.view === "pick" ? seqPickHtml() : SEQ.view === "insight" ? seqInsightHtml() : SEQ.view === "err" ? seqErrHtml() : SEQ.view === "done" ? seqDoneHtml()
    : SEQ.view === "fail" ? `<div class="sq-err">${esc(SEQ.failWhy || "")}</div><div class="sq-foot"><button data-a="pickagain">다른 동작 고르기</button></div>` : seqStepHtml();
  $("#seq-sum").textContent = SEQ.target && SEQ.view !== "pick" ? `${SEQ.target.act || ""} · ${SEQ.hist.length}단계 답함` : "";
  const q = $("#seq-q");
  if (q) { q.oninput = () => { SEQ.q = q.value; const pos = q.selectionStart; renderSeq(); const q2 = $("#seq-q"); q2.focus(); q2.setSelectionRange(pos, pos); }; }
  placeSeq(parseFloat($("#seq").style.left), parseFloat($("#seq").style.top));
}
async function seqStart(t) {
  if (!L.job) return;
  if ($("#seq").hidden) { $("#seq").hidden = false; $("#seq-btn").classList.add("on"); placeSeq(); }
  SEQ.job = L.job;
  const r = (L.sheets || []).find((x) => x.page === t.page);
  const want = 1;
  SEQ.target = { page: t.page, row: t.row, want, desc: t.desc || `${t.row}행`, act: t.action, label: t.equip ? `${t.equip} — ${t.action} ${ACT_KO[t.action] || ""}` : t.desc || `${t.row}행`,
    where: `${t.sheet || (r && r.sheet_no) || ""}-${t.row} ${t.desc || ""}${t.kind ? " · " + (KIND_KO[t.kind] || t.kind) : ""}` };
  Object.assign(SEQ, { plan: null, ans: {}, sub: {}, hist: [], tries: {}, eff: {}, hint: {}, nofollow: {}, via: null, reachedEarly: false, err: null, done: null, view: "step", busy: "조건을 도면에서 거꾸로 읽는 중…" });
  renderSeq();
  let plan;
  try { plan = await post(`/logic/api/jobs/${L.job}/sequence`, { page: t.page, row: t.row, value: want }); }
  catch (e) { plan = { ok: false, why: e.message }; }
  seqLink(plan);
  if (!plan.ok) { SEQ.busy = false; SEQ.view = "fail"; SEQ.failWhy = plan.why || "조건 나무를 만들지 못했습니다"; renderSeq(); return; }
  SEQ.plan = plan;
  SEQ.target.net = plan.net;
  // 순차 동작은 처음 상태에서 시작한다 — 사람이 앞서 준 신호 · 메모리 · 타이머 상태를 지운다 (타이머 시간 설정은 남는다)
  const had = Object.values(L.allForces || {}).reduce((a, f) => a + Object.keys(f || {}).length, 0);
  L.allForces = {}; L.forces = L.allForces[L.page] = {}; L.analog = {}; L.states = {}; L.state = null; L.values = {};
  if (L.mode !== "sim") setMode("sim", true);
  status(`▶ 순차 동작 — ${SEQ.target.label}${had ? ` · 앞서 준 강제 신호 ${had}개를 지우고 처음 상태에서 시작합니다` : ""}`);
  await seqApply(true);
  SEQ.busy = false;
  seqNext();
}
async function seqApply(quiet, animate) {
  const before = new Set((L.design || []).filter((e) => e.kind === "error").map((e) => e.page + ":" + e.row + ":" + e.to));
  L.allForces = seqForces();
  L.forces = L.allForces[L.page] = L.allForces[L.page] || {};
  await runSim(!!animate);
  if (quiet) return [];
  return (L.design || []).filter((e) => e.kind === "error" && !before.has(e.page + ":" + e.row + ":" + e.to));
}
async function seqLocate(n) {
  if (!n) return;
  const page = n.page;
  if (page !== L.page) { await openSheet(page); await new Promise((r) => setTimeout(r, 120)); }
  if (!L.sheet || L.sheet.page !== page) return;
  if (n.t === "any") {
    const g = (SEQ.cur.gates || []);
    status(`▶ 갈래 고르기 — ${g[g.length - 1] || ""}`);
    return;
  }
  if (n.kind === "row") { L.focus = { page, row: n.n, side: "L", at: Date.now() }; drawOverlay(); focusRow(); }
  const keys = n.kind === "zero" ? (n.items || []).map((x) => x.key) : n.key ? [n.key.replace(/^hold:/, "net:")] : [];
  const local = keys.filter((k) => !k.includes("/"));
  if (n.block && !n.block.includes("/") && L.sheet.blocks[n.block]) {
    const bb = L.sheet.blocks[n.block].bbox, st = $("#stage");
    st.scrollLeft = ((bb[0] + bb[2]) / 2) * L.zoom - st.clientWidth / 2;
    st.scrollTop = ((bb[1] + bb[3]) / 2) * L.zoom - st.clientHeight / 2;
  }
  if (local.length) flashNeed(local);
  else if (n.at) { const g = $("#g-need"); if (g) { g.innerHTML = ""; const gg = el("g", { class: "need", style: `animation-duration:${NEED_MS}ms;animation-iteration-count:${NEED_FLASH}` }, g);
    el("circle", { cx: n.at[0], cy: n.at[1], r: 9 }, gg); setTimeout(() => gg.remove(), NEED_FLASH * NEED_MS + 60); } }
}
function seqNext() {
  const st = seqWalk();
  if (!st) { seqFinish(false); return; }
  SEQ.cur = st; SEQ.view = "step";
  renderSeq();
  seqLocate(st.node);
}
async function seqAnswer(a) {
  const n = SEQ.cur.node;
  a.key = seqKeyOf(n); a.want = n.want;
  if (a.v === "follow") {
    SEQ.busy = `${n.ref.sheet}-${n.ref.row} 의 조건을 읽는 중…`; renderSeq();
    let sp;
    try { sp = await post(`/logic/api/jobs/${L.job}/sequence`, { page: n.ref.page, row: n.ref.row, value: n.want }); }
    catch (e) { sp = { ok: false, why: e.message }; }
    SEQ.busy = false;
    if (!sp.ok) {
      // 따라갈 수 없다 — 그 사유를 이 단계에 남기고 다시 묻지 않는다 (직접 답하거나 멈춘다)
      SEQ.nofollow[n.id] = sp.why || "조건을 읽지 못했습니다";
      renderSeq(); return;
    }
    SEQ.sub[n.id] = seqLink(sp);
  }
  const eff = SEQ.eff[n.id];
  SEQ.ans[n.id] = a;
  SEQ.hist.push(n.id);
  SEQ.tries = {}; SEQ.eff = {};
  SEQ.busy = a.v === "yes" ? `${n.want ? "활성" : "0 으로"} — 신호가 흐르는 것을 그립니다…` : "시뮬레이션 중…"; renderSeq();
  // L37 — 활성은 그 장에서 흐름을 그린다 (다음 단계가 다른 장이면 잠깐 보여 준 뒤 옮긴다)
  if (a.v === "yes" && n.page !== L.page && !n.key.includes("/")) await openSheet(n.page, { noSim: true });
  const fresh = await seqApply(false, a.v === "yes");
  SEQ.busy = false;
  if (fresh.length) { SEQ.err = fresh; SEQ.view = "err"; renderSeq(); return; }
  // 지금까지의 답만으로 최종 출력이 선다 (미리 돌려 본 결과) — 남은 질문 없이 끝을 보인다
  if (a.v === "yes" && eff && typeof eff === "object" && eff.target && eff.target.after === SEQ.target.want && eff.target.steady) {
    SEQ.reachedEarly = true;
    await new Promise((r) => setTimeout(r, 900));
    seqFinish(false); return;
  }
  const nx = seqWalk();
  if (a.v === "yes" && nx && nx.node.page !== L.page) await new Promise((r) => setTimeout(r, 1100));
  seqNext();
}
async function seqBack() {
  const id = SEQ.hist.pop();
  if (!id) return;
  delete SEQ.ans[id]; delete SEQ.sub[id];
  SEQ.tries = {}; SEQ.eff = {}; SEQ.reachedEarly = false;
  for (const k of Object.keys(SEQ.sub)) if (!SEQ.ans[k]) delete SEQ.sub[k];
  L.states = {}; L.state = null;                 // 메모리 · 타이머 상태도 처음부터 (되돌린 신호가 래치에 남지 않게)
  SEQ.busy = "되돌리는 중…"; renderSeq();
  await seqApply(true);
  SEQ.busy = false;
  seqNext();
}
async function seqFinish(stopped, forced, via) {
  const t = SEQ.target;
  SEQ.busy = "처음부터 흐름을 그리는 중…"; renderSeq();
  if (t.page !== L.page) await openSheet(t.page, { noSim: true });
  L.allForces = forced || seqForces(); L.forces = L.allForces[L.page] = L.allForces[L.page] || {};
  SEQ.via = via || null;
  L.states = {}; L.state = null; L.values = {};
  const r = await runSim(true);
  const vals = (r && r.frames && r.frames.length) ? r.frames[r.frames.length - 1].values : (L.finalValues || {});
  SEQ.busy = false;
  SEQ.done = { value: vals[t.net] === 1 ? 1 : 0, unmet: L.unmet || [], design: (L.design || []).filter((e) => e.kind === "error"), stopped };
  SEQ.view = "done";
  renderSeq();
  L.focus = { page: t.page, row: t.row, side: "R", at: Date.now() }; drawOverlay(); focusRow();
  status(SEQ.done.value === t.want ? `✔ ${t.label} — 조건을 모두 주었고 ${t.desc} 이(가) 나갑니다` : `⛔ ${t.label} — ${t.desc} 이(가) 나가지 않습니다 (패널의 막힌 자리를 보세요)`);
}
/* ------------------------------------------------------------------ L49 — 게이트 · 매크로를 누르면: 이 출력이 켜지려면

   로직을 잘 모르는 사람도 "이 명령이 나가려면 앞에서 무엇이 켜져야 하나" 를 보고 로직이 맞게 짜였는지 검토한다.
   나무는 서버가 순차 동작(L32)과 같은 길로 만든다 — AND 는 모두 · OR 는 하나 · NOT 은 반대 · 메모리 SET+RESET 0 ·
   매크로는 Typical 시트 안 조건까지.  화면은 그리고 · 누르면 그 자리로 · 주황으로 짚고 · '조건 채워 켜기' 만 한다. */
const ND = { target: null, page: null, data: null, busy: false, open: {}, tree: {}, value: 1 };
async function needsOpen(target, value) {
  const pop = $("#needs");
  if (!pop) return;
  ND.target = target; ND.page = L.page; ND.data = null; ND.busy = true; ND.open = {}; ND.tree = {}; ND.value = value == null ? 1 : value;
  pop.hidden = false; placeNeeds();
  renderNeeds();
  try { ND.data = await post(`/logic/api/jobs/${L.job}/needs`, { page: L.page, target, value: ND.value }); }
  catch (e) { ND.data = { ok: false, why: e.message }; }
  ND.busy = false;
  if (ND.target !== target) return;
  renderNeeds();
}
function needsClose() { const pop = $("#needs"); if (pop) pop.hidden = true; }
function placeNeeds(x, y) {
  const pop = $("#needs");
  if (x == null) {
    try { [x, y] = JSON.parse(lsGet("logic.needs.pos") || "null") || []; } catch (e) { x = y = null; }
    if (x == null) { x = innerWidth - 470 - 30; y = 140; }
  }
  const w = pop.offsetWidth || 460, h = pop.querySelector(".sp-h").offsetHeight || 30;
  pop.style.left = Math.max(4, Math.min(x, innerWidth - w - 4)) + "px";
  pop.style.top = Math.max(4, Math.min(y, innerHeight - h - 4)) + "px";
}
const ND_KIND = { row: "입력", button: "누름단추", monitor: "감시", net: "선 (몰이 못 읽음)", held: "매크로 안 선", terminal: "매크로 단자 없음",
  stuck: "읽기 빈틈", deep: "더 깊음", loop: "되먹임", zero: "없어야", const: "조건 없음", default0: "" };
function ndWant(w) { return w === 1 ? `<span class="v1">1</span>` : `<span class="v0">0</span>`; }
function ndLeafHtml(n, pg) {
  const sh = seqSheetName(n.page != null ? n.page : pg);
  const kind = ND_KIND[n.kind] != null ? ND_KIND[n.kind] : (n.kind || "");
  let where = "";
  if (n.kind === "row") where = `<span class="nd-loc" data-go="row" data-page="${n.page}" data-row="${n.n}" title="그 행으로">${esc(sh)}-${n.n}</span>`;
  else if (n.block && n.at) where = `<span class="nd-loc" data-go="block" data-page="${n.page}" data-block="${esc(String(n.block).split("/")[0])}" title="그 블록으로">${esc(sh)} · ${esc(n.block)}</span>`;
  else if (n.key && n.key.startsWith("net:") && !n.key.includes("/")) where = `<span class="nd-loc" data-go="net" data-page="${n.page}" data-net="${esc(n.key.slice(4))}" title="그 선으로">${esc(sh)} · 선</span>`;
  let ref = "";
  if (n.ref && n.ref.sheet) ref = `<span class="nd-ref${n.ref.other ? " other" : ""}" data-ref-sheet="${esc(n.ref.sheet)}" data-ref-row="${n.ref.row || ""}" title="${n.ref.other ? "다른 묶음에서 오는 신호" : "보내는 시트의 그 행으로"}">← ${esc(n.ref.sheet)}${n.ref.row ? "-" + n.ref.row : ""}</span>`;
  const ft = n.ft ? `<span class="nd-ft" title="${esc((n.ft.why || []).join(" · "))}">⚠ from-to 어긋남</span>` : "";
  const gap = n.kind === "stuck" || n.kind === "deep" || n.kind === "held" || n.kind === "terminal";
  if (n.kind === "zero") {
    const items = (n.items || []);
    if (!items.length) return "";
    return `<li class="nd-leaf nd-zero"><span class="nd-k">없어야</span> <span class="nd-t">고장 · 트립 · 인터록 — 아래 신호가 <b>0</b> 이어야 합니다</span>
      <ul>${items.map((it) => `<li>${ndWant(0)} ${esc(it.text || it.key)} ${it.n != null ? `<span class="nd-loc" data-go="row" data-page="${pg}" data-row="${it.n}">${esc(seqSheetName(pg))}-${it.n}</span>` : ""}
        ${it.ref && it.ref.sheet ? `<span class="nd-ref" data-ref-sheet="${esc(it.ref.sheet)}" data-ref-row="${it.ref.row || ""}">← ${esc(it.ref.sheet)}${it.ref.row ? "-" + it.ref.row : ""}</span>` : ""}</li>`).join("")}</ul></li>`;
  }
  if (n.auto && n.kind !== "loop") return "";
  if (n.kind === "loop") return `<li class="nd-leaf nd-auto"><span class="nd-k">되먹임</span> <span class="nd-t">${esc(n.text)}</span></li>`;
  return `<li class="nd-leaf${gap ? " nd-gap" : ""}" data-key="${esc(n.key || "")}" data-page="${n.page}">${gap ? `<span class="nd-k gap">${esc(kind)}</span>` : `${ndWant(n.want)} <span class="nd-k">${esc(kind)}</span>`}
    <span class="nd-t">${esc(n.text || "")}</span> ${where} ${n.fm ? `<small>FM ${esc(n.fm)}</small>` : ""} ${ref} ${ft}</li>`;
}
function ndTreeHtml(plan, id, pg, depth) {
  const n = plan.nodes[id];
  if (!n) return "";
  if (n.t === "leaf") return ndLeafHtml(n, pg);
  const kids = (n.kids || []).map((k) => plan.nodes[k]).filter(Boolean);
  const inner = n.t === "any"
    ? `<ol class="nd-any">${kids.map((k, i) => `<li class="nd-alt${i === n.pick ? " rec" : ""}"><span class="nd-alt-h">${i === n.pick ? "★ " : ""}갈래 ${i + 1}${k.viable === false ? " · ⚠ 읽기 빈틈" : ""}</span><ul class="nd-all">${k.t === "leaf" ? ndLeafHtml(k, pg) : ndTreeHtml(plan, k.id, pg, depth + 1)}</ul></li>`).join("")}</ol>`
    : `<ul class="nd-all">${kids.map((k) => k.t === "leaf" ? ndLeafHtml(k, pg) : ndTreeHtml(plan, k.id, pg, depth + 1)).join("")}</ul>`;
  const g = n.gate;
  const head = g ? `<div class="nd-gate"${g.block && g.at ? ` data-go="block" data-page="${pg}" data-block="${esc(String(g.block).split("/")[0])}"` : ""}>
      <span class="nd-gk">${esc(g.func === "MACRO" ? "매크로" : (GATE_KO_SHORT[g.logic] || g.func || "게이트"))}</span> ${esc(g.label || "")} ${g.want != null ? ndWant(g.want) : ""}</div>` : "";
  const wrap = n.t === "any" ? `<div class="nd-anyh">다음 중 <b>하나</b></div>` : (kids.length > 1 ? `<div class="nd-allh">모두</div>` : "");
  return `<li class="nd-node${depth ? "" : " root"}">${head}${wrap}${inner}</li>`;
}
function ndKeysOnPage(sig, pg) {
  const ks = [];
  for (const x of (sig.need || [])) if ((x.page == null || x.page === pg) && x.key && !x.key.includes("/") && !x.key.startsWith("hold:")) ks.push(x.key);
  return ks;
}
function renderNeeds() {
  const pop = $("#needs"), b = $("#needs-b");
  if (!pop || pop.hidden) return;
  pop.classList.toggle("min", lsGet("logic.needs.min") === "1");
  $("#needs-min").textContent = pop.classList.contains("min") ? "＋" : "－";
  const d = ND.data;
  $("#needs-t").textContent = ND.value === 1 ? "🔍 이 출력이 켜지려면" : "🔍 이 출력이 꺼지려면";
  $("#needs-val").textContent = ND.value === 1 ? "↔ 0" : "↔ 1";
  if (ND.busy || !d) { $("#needs-sum").textContent = ""; b.innerHTML = `<div class="sp-empty">조건을 범례대로 거꾸로 읽는 중…</div>`; return; }
  if (!d.ok) { $("#needs-sum").textContent = d.label || ""; b.innerHTML = `<div class="sp-empty">⚠ ${esc(d.why || "조건을 찾지 못했습니다")}</div>`; return; }
  $("#needs-sum").textContent = `${d.sheet || ""} · ${d.label || ""}`;
  const unjudged = d.kind === "gate" && (!d.logic || d.logic === "unknown");
  const outs = d.outputs || [];
  const multi = outs.length > 1;
  let html = `<div class="nd-intro">${d.kind === "macro" ? "매크로 출력 단자마다" : multi ? "나가는 선마다" : "이 출력이"} <b>${ND.value}</b> 이 되려면 앞에서 무엇이 ${ND.value === 1 ? "켜져야" : "켜지고 꺼져야"} 하는지 — 범례 정의를 거꾸로 읽은 것입니다.  항목을 누르면 그 자리로 갑니다.</div>` +
    (unjudged ? `<div class="nd-none gap">판정 못 한 블록 — 종류를 정하면(블록 누름 → 종류 정하기) 조건을 셀 수 있습니다</div>` : "");
  outs.forEach((o, i) => {
    const p = o.plan || {};
    const sig = p.signals || {};
    const open = ND.open[i] != null ? ND.open[i] : (!multi || i === 0);
    const title = d.kind === "macro" ? `${esc(o.pin || "")} ${o.desc ? "· " + esc(o.desc) : ""}` : (o.desc ? `→ ${esc(o.desc)}` : "출력 선");
    const nowTxt = o.now == null ? "" : ` · <span class="nd-now${o.now === ND.value ? " on" : ""}" title="아무것도 주지 않은 상태(이 시트만)에서 이 선의 값">지금 ${o.now}</span>`;
    const testedTxt = sig.tested === 1 ? ` · <span class="nd-now on" title="요약의 신호를 그대로 주고 시뮬레이터로 돌려 이 출력이 ${ND.value} 이 되는 것을 확인했습니다">✔ 시험 확인</span>`
      : sig.tested === 0 ? ` · <span class="nd-gapn" title="요약의 신호를 그대로 주고 돌려도 이 출력이 ${ND.value} 이 되지 않았습니다 — 읽기 빈틈 · 되먹임 · 다른 갈래일 수 있습니다">⚠ 시험에서 안 섬</span>` : "";
    const sum = p.ok ? (sig.already ? `<span class="nd-now on">이미 ${ND.value} — 아무것도 주지 않아도</span>` : `꼭 필요 ${(sig.need || []).length} · 없어야 ${(sig.zero || []).length}${sig.forks ? ` · 갈래 ${sig.forks}` : ""}${(sig.gaps || []).length ? ` · <span class="nd-gapn">읽기 빈틈 ${sig.gaps.length}</span>` : ""}${p.truncated ? " · 일부만" : ""}${nowTxt}${testedTxt}`) : `⚠ ${esc(p.why || "")}`;
    html += `<div class="nd-out${open ? " open" : ""}" data-i="${i}">
      <div class="nd-oh" data-toggle="${i}"><span class="nd-arrow">${open ? "▾" : "▸"}</span> <b>${title}</b> <small>${sum}</small></div>` +
      (open && p.ok ? `<div class="nd-acts">
        <button data-flash="${i}" title="이 시트에 있는 꼭 필요한 신호를 주황으로 3번 짚습니다">주황으로 짚기</button>
        ${ND.value === 1 ? `<button data-on="${i}" class="pri" title="필요한 입력을 실제로 켜고 흐름을 그립니다 (게이트가 범례대로 판정 — 조건이 안 맞으면 출력은 나가지 않습니다)">▶ 조건 채워 켜기</button>`
                           : `<button data-off="${i}" class="pri" title="요약의 신호를 그 값으로 주고 흐름을 그립니다 (게이트가 범례대로 판정)">▶ 조건 채워 끄기</button>`}</div>
        ${ndSummaryHtml(sig, p.page)}
        <div class="nd-th" data-tree="${i}"><span class="nd-arrow">${ndTreeOpen(i, p) ? "▾" : "▸"}</span> 게이트 단계로 보기 <small>AND 는 모두 · OR 는 하나 · NOT 은 반대 — 범례 정의 그대로</small></div>
        ${ndTreeOpen(i, p) ? `<ul class="nd-tree">${ndTreeHtml(p, p.root, p.page, 0)}</ul>` : ""}` : "") + `</div>`;
  });
  b.innerHTML = html;
}
/* 나무를 권하는 갈래로 접은 한 장 요약 — 로직을 모르는 사람이 먼저 보는 자리 */
function ndTreeOpen(i, p) { return ND.tree[i] != null ? ND.tree[i] : Object.keys(p.nodes || {}).length <= 12; }
function ndSummaryHtml(sig, pg) {
  const chip = (x) => {
    const sh = seqSheetName(x.page != null ? x.page : pg);
    const loc = x.n != null ? `<span class="nd-loc" data-go="row" data-page="${x.page != null ? x.page : pg}" data-row="${x.n}">${esc(sh)}-${x.n}</span>`
      : x.block && x.at ? `<span class="nd-loc" data-go="block" data-page="${x.page != null ? x.page : pg}" data-block="${esc(String(x.block).split("/")[0])}">${esc(sh)} · ${esc(x.block)}</span>` : "";
    const ref = x.ref && x.ref.sheet ? `<span class="nd-ref${x.ref.other ? " other" : ""}" data-ref-sheet="${esc(x.ref.sheet)}" data-ref-row="${x.ref.row || ""}">← ${esc(x.ref.sheet)}${x.ref.row ? "-" + x.ref.row : ""}</span>` : "";
    const ft = x.ft ? `<span class="nd-ft" title="${esc((x.ft.why || []).join(" · "))}">⚠ from-to</span>` : "";
    const cst = x.const != null ? (x.const === x.want ? `<span class="nd-k">상수 ${x.const}</span>` : `<span class="nd-k gap">상수 ${x.const} — 도면이 ${x.const} 으로 묶어 둠 · ${x.want === 1 ? "켤" : "끌"} 수 없음</span>`) : "";
    return `<li>${ndWant(x.want)} ${esc(x.text || x.key || "")} ${cst} ${loc} ${ref} ${ft}</li>`;
  };
  const need = sig.need || [], zero = sig.zero || [], gaps = sig.gaps || [];
  return `<div class="nd-sum">
    <div class="nd-sh">꼭 켜져야 하는 신호 <small>${need.length}${sig.forks ? ` · 갈래가 있는 곳은 ★ 권하는 갈래로` : ""}</small></div>
    ${need.length ? `<ul>${need.map(chip).join("")}</ul>` : `<div class="nd-none">${sig.already ? "없음 — 아무것도 주지 않아도 이미 이 값입니다 (앞 게이트가 기본 상태에서 그렇게 냅니다)" : (sig.asks || 0) === 0 && !gaps.length ? "없음 — 언제나 만족 (조건 없음)" : "없음"}</div>`}
    ${zero.length ? `<div class="nd-sh">없어야 하는 신호 <small>${zero.length} · 고장 · 트립 · 인터록 · 반대 명령</small></div><ul>${zero.map(chip).join("")}</ul>` : ""}
    ${gaps.length ? `<div class="nd-sh gap">도면에서 읽지 못한 자리 <small>${gaps.length} — 이 길의 값을 정할 수 없습니다</small></div><ul>${gaps.map((g) => `<li class="nd-gap">${esc(g.text || "")} ${g.block && g.at ? `<span class="nd-loc" data-go="block" data-page="${pg}" data-block="${esc(String(g.block).split("/")[0])}">${esc(seqSheetName(pg))} · ${esc(g.block)}</span>` : ""}</li>`).join("")}</ul>` : ""}
  </div>`;
}
function bindNeeds() {
  const pop = $("#needs"), head = $("#needs-h");
  if (!pop) return;
  head.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button")) return;
    const r = pop.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    head.setPointerCapture(e.pointerId);
    const move = (ev) => placeNeeds(ev.clientX - dx, ev.clientY - dy);
    const up = () => {
      head.removeEventListener("pointermove", move); head.removeEventListener("pointerup", up);
      const q = pop.getBoundingClientRect();
      lsSet("logic.needs.pos", JSON.stringify([Math.round(q.left), Math.round(q.top)]));
    };
    head.addEventListener("pointermove", move); head.addEventListener("pointerup", up);
  });
  $("#needs-x").onclick = needsClose;
  $("#needs-val").onclick = () => { if (ND.target) needsOpen(ND.target, ND.value === 1 ? 0 : 1); };
  $("#needs-min").onclick = () => { lsSet("logic.needs.min", pop.classList.contains("min") ? null : "1"); renderNeeds(); };
  $("#needs-b").addEventListener("click", async (e) => {
    const d = ND.data;
    if (!d || !d.ok) return;
    const tt = e.target.closest("[data-tree]");
    if (tt) { const i = Number(tt.dataset.tree); ND.tree[i] = !ndTreeOpen(i, d.outputs[i].plan || {}); renderNeeds(); return; }
    const tg = e.target.closest("[data-toggle]");
    if (tg) { const i = Number(tg.dataset.toggle); ND.open[i] = !(ND.open[i] != null ? ND.open[i] : (d.outputs.length === 1 || i === 0)); renderNeeds(); return; }
    const fl = e.target.closest("button[data-flash]");
    if (fl) {
      const o = d.outputs[Number(fl.dataset.flash)];
      if (ND.page !== L.page) await openSheet(ND.page);
      const ks = ndKeysOnPage((o.plan || {}).signals || {}, L.page);
      if (!ks.length) { status("이 시트에서 짚을 신호가 없습니다 — 다른 시트 · 매크로 안쪽 조건입니다"); return; }
      status(`필요한 신호 ${ks.length}개를 주황으로 짚습니다`);
      flashNeed(ks); return;
    }
    const on = e.target.closest("button[data-on]");
    if (on) {
      const o = d.outputs[Number(on.dataset.on)];
      if (o.net == null) return;
      if (ND.page !== L.page) await openSheet(ND.page);
      await activateOutput("net:" + o.net); return;
    }
    const off = e.target.closest("button[data-off]");
    if (off) {
      // L50 — 꺼지려면: 요약(권하는 갈래)의 신호를 그 값으로 주고 출력은 0 을 목표로 (게이트가 판정 · 직접 끄지 않는다)
      const o = d.outputs[Number(off.dataset.off)];
      if (o.net == null) return;
      if (ND.page !== L.page) await openSheet(ND.page);
      if (L.mode !== "sim") setMode("sim", true);
      const sig = (o.plan || {}).signals || {};
      const give = {};
      for (const x of [...(sig.need || []), ...(sig.zero || [])]) if ((x.page == null || x.page === L.page) && x.key && !x.key.includes("/") && x.const == null) give[x.key] = x.want;
      const keep = {};
      for (const [k, v] of Object.entries(L.forces)) if (!(k in give) && k !== "net:" + o.net) keep[k] = v;
      L.forces = L.allForces[L.page] = { ...keep, ...give, ["net:" + o.net]: 0 };
      const on = Object.keys(give).filter((k) => give[k] === 1);
      status(`출력을 0 으로 — 신호 ${Object.keys(give).length}개를 요약대로 줍니다${on.length ? ` (켜는 것 ${on.length})` : ""}`);
      if (on.length) await flashNeed(on);
      await runSim(true); reportUnmet(); return;
    }
    const ref = e.target.closest(".nd-ref");
    if (ref) { if (!ref.classList.contains("other")) goToRef(ref.dataset.refSheet, Number(ref.dataset.refRow) || 0, "R"); return; }
    const go = e.target.closest("[data-go]");
    if (go) {
      const pg = Number(go.dataset.page) || ND.page;
      if (go.dataset.go === "row") goLoc(pg, Number(go.dataset.row), "L");
      else if (go.dataset.go === "block") goLoc(pg, 0, null, "block:" + go.dataset.block);
      else if (go.dataset.go === "net") { if (pg !== L.page) await openSheet(pg); L.sel = { net: go.dataset.net }; paint(); renderInfo(); flashNeed(["net:" + go.dataset.net]); }
      return;
    }
  });
}
function bindSeq() {
  const pop = $("#seq"), head = $("#seq-h");
  if (!pop) return;
  head.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button")) return;
    const r = pop.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    head.setPointerCapture(e.pointerId);
    const move = (ev) => placeSeq(ev.clientX - dx, ev.clientY - dy);
    const up = () => {
      head.removeEventListener("pointermove", move); head.removeEventListener("pointerup", up);
      const q = pop.getBoundingClientRect();
      lsSet("logic.seq.pos", JSON.stringify([Math.round(q.left), Math.round(q.top)]));
    };
    head.addEventListener("pointermove", move); head.addEventListener("pointerup", up);
  });
  $("#seq-x").onclick = seqClose;
  $("#seq-min").onclick = () => { lsSet("logic.seq.min", pop.classList.contains("min") ? null : "1"); renderSeq(); };
  $("#gt-btn").onclick = () => popGroupTest(L.job);
  $("#seq-btn").onclick = () => { if (!pop.hidden) seqClose(); else seqOpen(); };
  $("#seq-b").addEventListener("click", (e) => {
    if (SEQ.busy) return;
    const act = e.target.closest("button.sq-act");
    if (act) {
      const gi = Number(act.dataset.eq), a = act.dataset.act, eq = SEQ.cmds[gi];
      const rows = (eq.actions.find((x) => x.action === a) || {}).rows || [];
      if (rows.length === 1) { const r = rows[0]; seqStart({ ...r, equip: eq.equip, action: a }); return; }
      SEQ.open = SEQ.open && SEQ.open.eq === gi && SEQ.open.act === a ? null : { eq: gi, act: a };
      renderSeq(); return;
    }
    const rl = e.target.closest(".sq-rows li");
    if (rl) {
      const eq = SEQ.cmds[Number(rl.dataset.eq)], r = (eq.actions.find((x) => x.action === rl.dataset.act) || {}).rows[Number(rl.dataset.j)];
      seqStart({ ...r, equip: eq.equip, action: rl.dataset.act }); return;
    }
    const il = e.target.closest(".sq-ins [data-li]");
    if (il) {
      const x = ((SEQ.learn && SEQ.learn.items) || [])[Number(il.dataset.li)];
      if (x) seqStart({ page: x.page, row: x.row, sheet: x.sheet, desc: x.desc, kind: x.kind, equip: x.equip, action: x.action });
      return;
    }
    const hl = e.target.closest(".sq-hist li");
    if (hl) { seqLocate(seqNodeById(hl.dataset.id)); return; }
    const el_ = e.target.closest(".sq-unmet li[data-ei]");
    if (el_) { const x = SEQ.err[Number(el_.dataset.ei)]; if (x) goToRef(x.sheet_no || seqSheetName(x.page), x.at_row || x.row, "R"); return; }
    const b = e.target.closest("button[data-a]");
    if (!b) return;
    const a = b.dataset.a;
    if (a === "look") { seqLocate(SEQ.cur && SEQ.cur.node); return; }
    if (a === "learned") { seqRunLearned(); return; }
    if (a === "insight") { SEQ.view = "insight"; renderSeq(); return; }
    if (a === "pick") {
      const tr = SEQ.cur && SEQ.tries[SEQ.cur.node.id];
      const o = Array.isArray(tr) ? tr[Number(b.dataset.i)] : null;
      if (o && o.reached && o.choice) Object.assign(SEQ.hint, o.choice);   // 미리 돌려 본 조합 — 안쪽 갈래의 권장이 된다
      seqAnswer({ v: Number(b.dataset.i) }); return;
    }
    if (a === "zero1") { seqAnswer({ v: "yes", item: Number(b.dataset.i) }); return; }
    if (["yes", "no", "skip", "follow"].includes(a)) { seqAnswer({ v: a }); return; }
    if (a === "back") { if (SEQ.view === "done" || SEQ.view === "err") SEQ.view = "step"; seqBack(); return; }
    if (a === "restart") { seqStart({ ...SEQ.target, sheet: (SEQ.target.where || "").split("-")[0], desc: SEQ.target.desc, equip: (SEQ.target.label || "").split(" — ")[0], action: SEQ.target.act }); return; }
    if (a === "stop") { seqFinish(true); return; }
    if (a === "replay") { seqFinish(SEQ.done && SEQ.done.stopped); return; }
    if (a === "pickagain") { SEQ.view = "pick"; renderSeq(); return; }
    if (a === "errgo") { SEQ.err = null; seqNext(); return; }
    if (a === "errlook") { const x = (SEQ.err || [])[0]; if (x) goToRef(x.sheet_no || seqSheetName(x.page), x.at_row || x.row, "R"); return; }
  });
  addEventListener("resize", () => { if (!pop.hidden) placeSeq(parseFloat(pop.style.left), parseFloat(pop.style.top)); });
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
      ${(() => { const f = funcBookEntry(b); return f ? `<tr><td>동작 (범례)</td><td>${esc(f.does)}${f.legend ? ` <small title="${esc(f.legend)}">(범례)</small>` : ""}${f.sim ? ` <small class="muted">· ${esc(f.sim)}</small>` : ""}</td></tr>` : ""; })()}
      ${b.user ? `<tr><td>사람이 정함</td><td>✎ ${esc(choiceLabel(b.user.choice))} — ${esc(b.user.author)} · ${esc(b.user.at)} <small>(도면 판정: ${esc(FUNC_KO[b.user.was_func] || b.user.was_func || "")})</small></td></tr>` : ""}
      ${b.learned && !b.user ? `<tr><td>판정 근거</td><td>ⓛ 학습 사전 <small>(${esc(b.learned)} 에서 배운 기준 — 이 묶음 범례에는 없음)</small></td></tr>` : ""}
      ${b.score ? `<tr><td>맞음</td><td>${Math.round(b.score * 100)}% <small>범례 어휘와 글자 모양</small></td></tr>` : ""}
      ${TIMER_LOGIC.has(b.logic) ? (() => { const ts = timerSec(L.sel.block); return `<tr><td>시간</td><td><b>${fmtSec(ts.sec)}</b> <small>${ts.src === "user" ? "사람이 바꿈" : ts.src === "drawing" ? "도면 " + esc(b.param.text || "") : "도면에 없음 — 기본"}</small> <button data-timer="${esc(L.sel.block)}">시간 바꾸기</button></td></tr>`; })()
        : b.param.text ? `<tr><td>시간</td><td>${esc(b.param.text)}</td></tr>` : ""}
      ${analogInfoRows(L.sel.block)}
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
    ${ins.length || b.func === "MACRO" || (b.logic && b.logic !== "unknown" && b.logic !== "source" && L.sheet.ports.some((p) => p.block === L.sel.block && p.dir === "out")) ? `<div class="acts"><button data-needs="${esc(L.sel.block)}">🔍 이 출력이 켜지려면 — 필요한 신호</button></div>` : ""}
    ${b.func !== "CONNECTOR" && b.func !== "MACRO" ? `<div class="acts"><button data-gate="${esc(L.sel.block)}">${b.func === "UNKNOWN" ? "이 블록의 종류 정하기" : "종류 바꾸기 (사람이 정함)"}</button></div>` : ""}
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
    ? "<b>동작 시뮬레이션</b> — 모든 선은 디지털 1/0 입니다. 왼쪽 입력 행의 점, 누름단추(PB), 또는 아무 선이나 누르면 작은 메뉴가 뜹니다 — <b>1 활성</b> / <b>0 비활성</b> / 강제 풀기.  누름단추를 1 로 누르면 그 신호가 어디까지 갔는지, 못 갔으면 어디서 왜 멈췄는지 카드로 알리고 <b>누른 채로 조건을 채워 동작시키기</b>를 권합니다. 활성인 선만 <b>형광 파랑</b>으로 보이고, 게이트는 범례 G003 정의대로 조건이 맞을 때만 뒤 신호를 내보냅니다 (예: AND 는 입력이 모두 1 · NOT 은 입력 0 이면 1). 출력 행이 1 이 되면 그 행을 FM 으로 받는 <b>다른 장의 입력도 1</b> 이 되고 그 장의 로직도 이어서 돕니다 — 오른쪽 '활성 연결' 에서 그 장으로 갑니다. 타이머는 시간이 흐르는 모습을 아래에 보입니다. 출력 행 동그라미나 오른쪽 출력 행의 <b>⚡예시</b> 를 누르면 그 출력까지 <b>입력부터 최종 출력까지 모든 신호가 서는 입력 조합</b>을 찾아 흐름을 보여 줍니다."
    : "<b>연결 따라가기</b> — 선이나 블록, 행 점을 누르면 그 신호가 어디로 가는지 주황색으로 이어 그립니다. 게이트의 다른 입력이 활성이 아니어도 연결을 따라 끝까지 갑니다 (게이트 조건은 동작 시뮬레이션이 지킵니다). <b>Shift</b>+누름은 거슬러 올라갑니다 (어디서 오는지). 행 동그라미(입력·출력)를 누르면 <b>1 활성 / 0 비활성</b>을 고릅니다 — 출력 행이 1 이면 그 행의 TO·FM 으로 이어진 다른 시트로 계속 이어집니다.";
  $("#legend").innerHTML = sim
    ? `<span><i style="background:var(--active);box-shadow:0 0 4px var(--active-glow)"></i>1 활성</span><span><i style="background:transparent;border:1px dashed #ccc"></i>0 — 표시 없음</span><span><i style="background:rgba(0,180,255,.35)"></i>켜진 메모리·타이머</span>`
    : `<span><i style="background:var(--trace)"></i>따라가는 신호</span><span><i style="background:var(--trace-up)"></i>거슬러 올라감</span><span><i style="background:rgba(47,91,216,.5)"></i>읽은 선</span><span><i style="background:var(--unk)"></i>판정 못 한 블록</span>`;
}

/* ------------------------------------------------------------------ 게이트 단자 1/0 · S-R 래치 표 (L8)

   시뮬레이션에서 활성 신호가 지나는 게이트의 앞(입력)·뒤(출력) 단자마다 1/0 을 적는다.
   값은 화면이 지금 그리는 L.values 그대로라 흐르는 모습(애니메이션)과 같이 움직인다.
   '모든 게이트' 를 켜면 활성이 아닌 게이트도 적는다.  S-R(메모리)은 진리표에 지금 줄을 칠한다. */

/* L51 — 기능 책: 블록의 범례 동작 한 줄 (서버 `functions.entry` 와 같은 규칙 — 투표 부호 · 메모리 우선 칸) */
function funcBookEntry(b) {
  const fb = L.funcBook || {};
  let e = (b.aop && fb["aop:" + b.aop]) || fb[b.logic] || null;
  if (!e) return null;
  e = Object.assign({}, e);
  const pr = b.param || {};
  if (b.logic === "vote" && pr.a != null) {
    const w = { ge: "이상", gt: "보다 많이", le: "이하", lt: "미만", eq: "정확히", ne: "가 아닐 때" }[pr.op || "ge"] || "이상";
    e.does = `${pr.b}개 입력 중 1 인 것이 ${pr.a}개 ${w}일 때 출력 1`;
  }
  if (b.logic === "memory") e.does = "S=1 → Q=1 · R=1 → Q=0 · 둘 다 1 이면 " + ({ set: "Q=1 (SET 우선)", reset: "Q=0 (RESET 우선)" }[pr.dominant] || "상태가 한 번 바뀜 (기본)") + " · /Q 는 언제나 반대";
  return e;
}
const GATE_LOGIC = new Set(["and", "nand", "or", "nor", "not", "memory", "delay_on", "delay_off", "pulse", "step"]);
function portVal(p) { return L.values[p.net] === 1 ? 1 : 0; }
function latchState(bid) {
  const s = L.sheet;
  const ps = s.ports.filter((p) => p.block === bid);
  const S = ps.some((p) => p.dir === "in" && p.role === "set" && portVal(p) === 1) ? 1 : 0;
  const R = ps.some((p) => p.dir === "in" && p.role === "reset" && portVal(p) === 1) ? 1 : 0;
  let Q = L.state && L.state.mem && L.state.mem[bid] === 1 ? 1 : 0;
  // L45 — 매크로 새 창은 상태를 갖지 않는다 (부모 장이 센다) — Q 출력 선의 값이 그 상태다
  if (macroLinked()) Q = ps.some((p) => p.dir === "out" && p.role === "q" && portVal(p) === 1) ? 1 : 0;
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
  if (!L.sheet) return;
  drawAnalogMarks(g, Math.max(2.4, Math.min(4.6, (L.sheet.pitch || 11.5) * 0.34)));   // L27 — 설정값(SP)은 어느 모드든
  if (L.mode !== "sim") return;
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
        if (!p.at) continue;
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
  }
  // L24 — 래치는 실시간 값 표를 언제나 단다 (사용자 지시: "Latch 는 실시간 값 테이블이 있어야 한다").
  // 예전에는 1 이 하나라도 있는 래치에만 그려, 처음(S=0 · R=0 · Q=0)에는 표가 없어 래치가 무엇을 기다리는지 안 보였다.
  // 단자 역할을 못 읽은 래치(사람이 메모리로 정한 블록 등)도 표는 선다.
  if (showTables) for (const [bid, b] of Object.entries(s.blocks)) if (b.logic === "memory") drawLatchTable(g, bid, fs);
}
function drawLatchTable(g, bid, fs) {
  const b = L.sheet.blocks[bid];
  const st = latchState(bid);
  const rows = latchRows(st.dom);
  const cw = [fs * 1.3, fs * 1.3, fs * 2.9], ch = fs * 1.35;
  const W = cw[0] + cw[1] + cw[2], H = ch * (rows.length + 1);
  const [x0, y0] = b.bbox;
  const x = x0, y = y0 - 6.2 - H;                         // 블록 이름표(위 5.6) 바로 위
  const gg = el("g", { class: "lt" + (st.Q ? " q1" : "") }, g);
  // 맨 위 한 줄 = 지금 값 (실시간 — 시뮬레이션 틀마다 바뀐다)
  const nowY = y - ch * 1.05;
  el("rect", { x, y: nowY, width: W, height: ch, rx: fs * 0.2, class: "lt-now" + (st.Q ? " q1" : "") }, gg);
  const nt = el("text", { x: x + W / 2, y: nowY + ch * 0.75, "font-size": fs * 0.85, class: "lt-nowt" }, gg);
  nt.textContent = `S${st.S} R${st.R} → Q${st.Q}`;
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
    L.memoOthers = m.others || [];                 // L30 — 같은 프로젝트 다른 분석의 같은 시트 메모
  } catch (e) { L.memos = []; L.memoOthers = []; }
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
  pinBtn.textContent = L.pendingAt ? "📌 자리 지정됨 (Esc 취소)" : L.pinMode ? "📌 도면을 누르세요 (끌면 영역)" : "📌 핀 메모";
  $("#memo-save").textContent = L.memoEdit ? "고친 글 저장" : "저장";
  const items = pageMemos();
  $("#memo-count").textContent = items.length ? `${items.length}건` : "";
  if (!L.sheet) { box.innerHTML = ""; return; }
  box.innerHTML = items.length ? items.slice().reverse().map((m) => {
    const n = m.at ? pinNo(m) : 0;
    return `<li data-memo="${esc(m.id)}" class="${m.done ? "done" : ""}${m.hidden ? " hid" : ""}${L.memoFlash === m.id ? " flash" : ""}">
      <div class="mh">${n ? `<span class="pinno" title="도면 위 핀 번호">${n}</span>` : ""}<b>${esc(m.author)}</b> <small>${esc(m.time)}${m.history && m.history.length ? ` · 고친 이력 ${m.history.length}` : ""}</small></div>
      ${m.block ? `<div class="mb">⊡ ${esc(blockName(m.block))}${m.rect ? " · 영역" : ""}</div>` : m.rect ? `<div class="mb">▭ 영역 메모</div>` : ""}
      <div class="mt">${esc(m.text)}</div>
      ${L.memoHist === m.id && m.history && m.history.length ? `<div class="mhist">${m.history.slice().reverse().map((h) => `<div><small>${esc(h.author)} · ${esc(h.time)}</small><div>${esc(h.text)}</div></div>`).join("")}</div>` : ""}
      <div class="ma"><button data-mact="edit">고치기</button><button data-mact="done">${m.done ? "완료 풀기" : "완료"}</button><button data-mact="hide">${m.hidden ? "다시 보기" : "숨김"}</button>${m.history && m.history.length ? `<button data-mact="hist">${L.memoHist === m.id ? "이력 닫기" : "고친 이력"}</button>` : ""}</div>
    </li>`;
  }).join("") : `<li class="empty">이 장의 메모가 없습니다.</li>`;
  const oth = otherMemos();
  if (oth.length) box.innerHTML += `<li class="oth-h">같은 프로젝트 다른 분석의 이 시트 메모 ${oth.length}건 (읽기만)</li>` + oth.map((m) =>
    `<li class="oth" data-oth="${esc(m.id)}"><div class="mh"><span class="pinno oth">R</span><b>${esc(m.author)}</b> <small>${esc(m.time)} · ${esc(m.from_name)}</small></div><div class="mt">${esc(m.text)}</div></li>`).join("");
}
function blockName(bid) {
  const b = L.sheet && L.sheet.blocks[bid];
  return b ? `${b.label || FUNC_KO[b.func] || b.func} (${bid})` : bid;
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
  const box = (r, cls) => el("rect", { x: r[0], y: r[1], width: r[2] - r[0], height: r[3] - r[1], class: "pinarea " + cls }, g);
  for (const m of L.memos) {
    if (m.page !== L.sheet.page || !m.at || m.hidden) continue;
    if (m.rect) box(m.rect, (m.done ? "done" : "") + (L.memoFlash === m.id ? " flash" : ""));
    one(m.at[0], m.at[1], String(pinNo(m)), m.done ? "done" : "", m);
  }
  // L30 — 같은 프로젝트의 다른 분석(Rev)에서 같은 시트에 단 메모 — 파란 핀 (읽기만)
  for (const m of otherMemos()) {
    if (!m.at) continue;
    if (m.rect) box(m.rect, "other");
    one(m.at[0], m.at[1], "R", "other", null);
    const gg = g.lastChild;
    el("title", {}, gg).textContent = `다른 분석 '${m.from_name}' 에서 — ${m.author} · ${m.time}\n${m.text}`;
  }
  if (L.pinDraft) box(L.pinDraft, "pending");
  if (L.pendingRect) box(L.pendingRect, "pending");
  if (L.pendingAt) one(L.pendingAt[0], L.pendingAt[1], "+", "pending", null);
}
function otherMemos() {
  return (L.memoOthers || []).filter((m) => L.sheet && m.sheet_no && m.sheet_no === L.sheet.sheet_no);
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
  if (act === "hist") { L.memoHist = L.memoHist === id ? null : id; renderMemo(); return; }
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
    const lo = e.target.closest("li[data-oth]");
    if (lo) {
      const m = otherMemos().find((x) => x.id === lo.dataset.oth);
      if (m && m.at) { const st = $("#stage"); setZoom(Math.max(L.zoom, 1.6)); st.scrollLeft = m.at[0] * L.zoom - st.clientWidth / 2; st.scrollTop = m.at[1] * L.zoom - st.clientHeight / 2; }
      return;
    }
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
  // 핀 자리 고르기 — 선·블록 누르기보다 먼저 (붙잡는 단계).  L30 — 누르면 그 점 · 끌면 영역 (P&ID hotfix76 · 77 처럼)
  let pinStart = null;
  $("#stage").addEventListener("pointerdown", (e) => {
    if (!L.pinMode || e.button !== 0 || !L.sheet) return;
    e.stopPropagation(); e.preventDefault();
    pinStart = sheetPoint(e);
  }, true);
  window.addEventListener("pointermove", (e) => {
    if (!pinStart) return;
    const p = sheetPoint(e);
    L.pinDraft = [Math.min(pinStart[0], p[0]), Math.min(pinStart[1], p[1]), Math.max(pinStart[0], p[0]), Math.max(pinStart[1], p[1])];
    drawPins();
  });
  window.addEventListener("pointerup", (e) => {
    if (!pinStart) return;
    const p = sheetPoint(e), s0 = pinStart;
    pinStart = null; L.pinDraft = null;
    L.pinJust = true; setTimeout(() => (L.pinJust = false), 0);
    const r = [Math.min(s0[0], p[0]), Math.min(s0[1], p[1]), Math.max(s0[0], p[0]), Math.max(s0[1], p[1])];
    setPinMode(false);
    if (r[2] - r[0] > 3 && r[3] - r[1] > 3) pinForm([r[2], r[1]], { rect: r }, e);
    else pinForm(s0, {}, e);
  });
  $("#stage").addEventListener("click", (e) => { if (L.pinJust) { e.stopPropagation(); e.preventDefault(); } }, true);
}
/* L30 — 핀 메모 작성칸 (P&ID hotfix77): 날짜(지금) · 작성자(로그인 이름 · 기억된 이름) · 메모 내용.  핀 옆에 뜬다. */
function pinForm(at, opts, e) {
  closePinForm();
  opts = opts || {};
  L.pendingAt = at; L.pendingRect = opts.rect || null; L.pendingBlock = opts.block || null;
  drawPins(); renderMemo();
  const who = currentAuthor();
  const f = document.createElement("div");
  f.id = "pin-form"; f.className = "force-menu pin-form";
  const now = () => { const d = new Date(), z = (x) => String(x).padStart(2, "0"); return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())} ${z(d.getHours())}:${z(d.getMinutes())}`; };
  f.innerHTML = `<div class="fm-h">📌 ${esc(opts.title || (opts.rect ? "영역 메모" : "핀 메모"))} <small>${esc(L.sheet.sheet_no || "")}</small></div>
    <div class="pf-row"><span>날짜</span><b class="pf-date">${now()}</b></div>
    <div class="pf-row"><span>작성자</span>${who ? `<b>${esc(who)}</b>` : `<input id="pf-who" placeholder="이름 (한 번만 적으면 기억합니다)">`}</div>
    <textarea id="pf-text" rows="4" placeholder="메모 내용 (Ctrl+Enter 저장)"></textarea>
    <div class="op-btns"><button data-a="save" class="v1">저장</button><button data-a="x" class="vx">취소 (Esc)</button></div>`;
  placeMenu(f, e);
  const tick = setInterval(() => { const d = f.querySelector(".pf-date"); if (!document.body.contains(f)) clearInterval(tick); else d.textContent = now(); }, 15000);
  const ta = f.querySelector("#pf-text");
  (f.querySelector("#pf-who") || ta).focus();
  const save = async () => {
    const text = ta.value.trim();
    let author = who;
    if (!author) { author = (f.querySelector("#pf-who").value || "").trim(); if (!author) { status("작성자 이름을 적어 주세요"); f.querySelector("#pf-who").focus(); return; } rememberAuthor(author); }
    if (!text) { status("메모 내용을 적어 주세요"); ta.focus(); return; }
    try {
      const m = await post(`/logic/api/jobs/${L.job}/memo`, { page: L.sheet.page, sheet_no: L.sheet.sheet_no, text, author,
                                                            at: L.pendingAt, rect: L.pendingRect, block: L.pendingBlock });
      L.memos.push(m);
      closePinForm();
      drawPins(); renderMemo(); renderSheetList();
      status("메모를 저장했습니다");
      selectMemo(m.id, false);
    } catch (err) { status("메모 저장 실패 — " + err.message); }
  };
  f.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); save(); }
    if (ev.key === "Escape") { ev.stopPropagation(); closePinForm(); }
  });
  f.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const b = ev.target.closest("button[data-a]");
    if (!b) return;
    if (b.dataset.a === "save") save(); else closePinForm();
  });
}
function closePinForm() {
  const f = document.getElementById("pin-form");
  if (f) f.remove();
  if (L.pendingAt || L.pendingRect) { L.pendingAt = null; L.pendingRect = null; L.pendingBlock = null; if (L.sheet) drawPins(); renderMemo(); }
}

/* ------------------------------------------------------------------ 식별률 · 마크업 (L24)

   식별률: 분석이 이 묶음을 얼마나 읽었나 (시트 이름 · FROM/TO 칸 · 연결 · 게이트).  90% 아래면 붉게 말하고
   못 읽은 것을 하나씩 늘어놓는다 — 누르면 그 자리로 가서 마크업 창이 열린다.
   마크업: P&ID 마크업과 같은 방법.  ✎ 마크업 을 누르고 도면에 사각형을 그으면 무엇인지(FROM · TO · 시트 이름 ·
   게이트 종류) 고르고 값을 적는다.  저장한 값은 분석 결과와 따로 남고(다시 분석해도 남는다) 연결 · From-To 점검 ·
   시뮬레이션 · 이동이 그 값을 쓴다.  FROM/TO 마크업을 누르면 그 시트 그 행으로 간다. */

const IDR_KO = { sheet: "시트 이름", cell: "FROM/TO 칸", link: "시트 사이 연결", gate: "게이트" };
const MARK_KO = { FROM: "FROM", TO: "TO", SHEET: "시트 이름", GATE: "게이트" };
const pct = (v) => (v == null ? "—" : (Math.floor(v * 1000) / 10).toFixed(1) + "%");
async function loadIdrate() {
  const id = L.job;
  try {
    const r = await api(`/logic/api/jobs/${id}/idrate`);
    if (L.job !== id) return;
    L.idrate = r;
  } catch (e) { L.idrate = null; }
  renderIdrate();
}
function renderIdrate() {
  const box = $("#idrate");
  const r = L.idrate;
  if (!box) return;
  if (!r) { box.hidden = true; return; }
  box.hidden = false;
  const low = r.low && r.low.length;
  const parts = Object.keys(IDR_KO).map((k) => {
    const c = r.counts[k] || {};
    const v = r.rate[k];
    return `<li class="${v != null && v < r.target ? "low" : ""}"><span>${IDR_KO[k]}</span><b>${pct(v)}</b><small>${c.ok || 0}/${c.all || 0}</small></li>`;
  }).join("");
  const open = L.idrateOpen;
  const items = (r.items || []).map((it, i) =>
    `<li data-i="${i}" title="누르면 그 자리로 가서 마크업 창을 엽니다"><b>${esc(it.sheet_no || "p" + it.page)}</b> ${esc(it.text)}</li>`).join("");
  box.className = "lg-idrate" + (low ? " low" : "");
  box.innerHTML = `<div class="idr-h">식별률 <b>${pct(r.overall)}</b>
      <small>${low ? `⚠ ${r.low.map((k) => IDR_KO[k]).join(" · ")} 가 ${Math.round(r.target * 100)}% 아래입니다` : `목표 ${Math.round(r.target * 100)}% 이상`}</small></div>
    <ul class="idr-parts">${parts}</ul>
    ${teachLine()}
    <div class="idr-un">못 읽은 것 <b>${r.unread}</b>${r.empty_cells ? ` <small>· 비어 있는 FM/TO 칸 ${r.empty_cells} (도면에 안 적혔거나 못 읽음)</small>` : ""}
      ${r.unread ? `<button class="mini" id="idr-toggle">${open ? "접기" : "펼치기"}</button>` : ""}</div>
    ${open && r.unread ? `<ul class="idr-items" id="idr-items">${items}</ul><p class="idr-help">먼저 🎓 가르치기 — 한 번 답하면 모든 장에 들어갑니다.  그래도 남은 것만 ✎ 마크업 으로 하나씩 넣습니다.</p>` : ""}`;
}
function gotoIdItem(it) {
  const go = () => {
    const at = it.at;
    if (at) {
      const st = $("#stage");
      setZoom(Math.max(L.zoom, 1.8));
      st.scrollLeft = ((at[0] + at[2]) / 2) * L.zoom - st.clientWidth / 2;
      st.scrollTop = ((at[1] + at[3]) / 2) * L.zoom - st.clientHeight / 2;
      L.markHint = { rect: at, until: Date.now() + 2500 };
      drawMarks();
      setTimeout(drawMarks, 2600);
      if (it.look) return;                 // 가르치기 '도면에서 보기' — 자리만 보인다
      const kind = it.kind === "LINK" ? "FROM" : it.kind;
      const r = $("#ov").getBoundingClientRect(), [W, H] = L.sheet.size;
      const e = { clientX: r.left + at[2] * r.width / W, clientY: r.top + at[3] * r.height / H };
      if (it.kind === "GATE" && it.block) { gateMenu(it.block, e); return; }
      markDialog(at.slice(), e, { kind, n: it.row });
    } else {
      markDialog(null, null, { kind: it.kind === "SHEET" ? "SHEET" : "FROM" });
    }
  };
  if (!L.sheet || L.sheet.page !== it.page) { L.focus = null; L.afterFit = go; openSheet(it.page); }
  else go();
}

function setMarkMode(on) {
  L.markMode = on;
  $("#stage").classList.toggle("marking", on);
  $("#markup").classList.toggle("on", on);
  if (on) { setPinMode(false); status("마크업 — 도면에서 못 읽은 자리를 사각형으로 끌어 그으세요 (Esc 로 끝)"); }
}
function guessKind(rect) {
  const s = L.sheet, lg = s.logic || [0, 0, 0, 0];
  const cx = (rect[0] + rect[2]) / 2;
  if (cx < lg[0]) return "FROM";
  if (cx > lg[2]) return "TO";
  const hit = Object.values(s.blocks).some((b) => b.bbox[0] < rect[2] && b.bbox[2] > rect[0] && b.bbox[1] < rect[3] && b.bbox[3] > rect[1]);
  return hit ? "GATE" : "FROM";
}
function rowAt(rect, side) {
  if (!rect) return null;
  const cy = (rect[1] + rect[3]) / 2;
  return (L.sheet.table || []).find((t) => t.side === side && t.y0 != null && t.y0 <= cy && cy <= t.y1) || null;
}
function markDialog(rect, e, preset) {
  closeForceMenu();
  preset = preset || {};
  const s = L.sheet;
  const old = preset.mark || null;
  let kind = (old && old.kind) || preset.kind || (rect ? guessKind(rect) : "SHEET");
  if (!rect) rect = old ? old.rect : [s.size[0] * 0.85, s.size[1] * 0.9, s.size[0] * 0.95, s.size[1] * 0.95];
  const choices = (L.choices || []).map((c) => `<option value="${esc(c.key)}">${esc(c.label)}</option>`).join("");
  const m = document.createElement("div");
  m.id = "force-menu"; m.className = "force-menu mk-menu";
  m.innerHTML = `<div class="fm-h">${old ? "마크업 고치기" : "마크업 — 이 자리는 무엇인가요"}</div>
    <div class="mk-kinds">${Object.keys(MARK_KO).map((k) => `<label><input type="radio" name="mk-k" value="${k}"> ${MARK_KO[k]}</label>`).join("")}</div>
    <div class="mk-f mk-val"><label>값 <input id="mk-v" type="text" maxlength="120" placeholder="예: 0016/72 · G031-81" style="width:150px"></label></div>
    <div class="mk-f mk-row"><label>행 번호 <input id="mk-n" type="number" min="1" style="width:70px"></label> <small id="mk-rowhint"></small></div>
    <div class="mk-f mk-gate"><label>종류 <select id="mk-c">${choices}</select></label>
      <span id="mk-vote" hidden> A <input id="mk-a" type="number" min="1" value="2" style="width:40px"> / B <input id="mk-b" type="number" min="1" value="3" style="width:40px"></span></div>
    <div class="fm-why" id="mk-why"></div>
    <button data-t="ok" class="v1">저장</button>
    ${old ? `<button data-t="del" class="vx">이 마크업 지우기</button>` : ""}
    <button data-t="cancel">취소</button>`;
  placeMenu(m, e);
  const q = (x) => m.querySelector(x);
  const refresh = () => {
    kind = (m.querySelector("input[name=mk-k]:checked") || {}).value || kind;
    q(".mk-val").hidden = kind === "GATE";
    q(".mk-row").hidden = !(kind === "FROM" || kind === "TO");
    q(".mk-gate").hidden = kind !== "GATE";
    q("#mk-vote").hidden = q("#mk-c").value !== "VOTE";
    const side = kind === "FROM" ? "L" : "R";
    const t = (kind === "FROM" || kind === "TO") ? rowAt(rect, side) : null;
    q("#mk-rowhint").textContent = t ? `표의 ${t.n}행 (${t.desc || "설명 없음"})` : "표에서 행을 못 찾았습니다 — 행 번호를 적어 주세요";
    if (t && !q("#mk-n").value) q("#mk-n").placeholder = String(t.n);
    q("#mk-v").placeholder = kind === "SHEET" ? `예: ${(L.sheets.find((x) => x.sheet_no) || {}).sheet_no || "G031"}` : "예: 0016/72 · G031-81";
    q("#mk-why").textContent = kind === "FROM" ? "FROM = 이 행의 신호가 어디(시트-행)에서 오는가.  저장하면 그 행과 이어지고 누르면 그리로 갑니다."
      : kind === "TO" ? "TO = 이 행의 신호가 어디(시트-행)로 가는가.  여럿은 쉼표로."
      : kind === "SHEET" ? "이 장의 시트 이름 — 다른 장의 FM/TO 가 이 이름으로 이 장을 찾습니다."
      : "사각형 안 블록의 종류 — 그 게이트로 시뮬레이션합니다.";
  };
  for (const r of m.querySelectorAll("input[name=mk-k]")) { r.checked = r.value === kind; r.onchange = refresh; }
  q("#mk-c").onchange = refresh;
  if (old) {
    if (old.value) q("#mk-v").value = old.value;
    if (old.n) q("#mk-n").value = old.n;
    if (old.choice) q("#mk-c").value = old.choice;
    if (old.param) { q("#mk-a").value = old.param.a; q("#mk-b").value = old.param.b; }
  } else if (preset.n) q("#mk-n").value = preset.n;
  refresh();
  (kind === "GATE" ? q("#mk-c") : q("#mk-v")).focus();
  const save = async (del) => {
    const who = await needAuthor();
    if (!who) { status("이름이 없어 저장하지 않았습니다"); return; }
    const body = { page: s.page, id: old ? old.id : undefined, kind, rect, author: who };
    if (!del) {
      if (kind === "GATE") {
        body.choice = q("#mk-c").value;
        if (body.choice === "VOTE") body.param = { a: Number(q("#mk-a").value), b: Number(q("#mk-b").value) };
      } else {
        body.value = q("#mk-v").value.trim();
        if (!body.value) { status("값을 적어 주세요"); q("#mk-v").focus(); return; }
        const n = q("#mk-n").value || ((kind === "FROM" || kind === "TO") && rowAt(rect, kind === "FROM" ? "L" : "R") || {}).n;
        if (n) body.row = Number(n);
      }
    }
    closeForceMenu();
    try {
      const r = await post(`/logic/api/jobs/${L.job}/overrides/mark`, body);
      const mk = r.mark;
      if (del) status("마크업을 지웠습니다 — 도면 판정으로 돌아갑니다");
      else if (mk && mk.ok === false) status(`저장했지만 닿지 못했습니다 — ${mk.why}`);
      else {
        const f = r.ft;
        status(`${MARK_KO[kind]} 마크업 저장 (${who})` + (kind === "SHEET" ? ` — 이 장은 이제 ${r.sheet_no}` : "")
          + (mk && mk.n ? ` — ${mk.n}행` : "") + (mk && mk.made_row ? " (표에 없던 행을 만들었습니다)" : "")
          + (f ? (f.ok === false ? ` — ✕ 아직 맞지 않습니다: ${(f.why || []).join(" · ")}` : f.ok ? " — ✓ 연결이 맞습니다" : "") : ""));
      }
    } catch (err) { status("저장하지 못했습니다 — " + err.message); return; }
    setMarkMode(false);
    await refreshSheet();
    loadIdrate();
  };
  q("#mk-v").addEventListener("keydown", (ev) => { if (ev.key === "Enter" && !ev.isComposing) save(false); if (ev.key === "Escape") closeForceMenu(); });
  m.addEventListener("click", (ev) => {
    ev.stopPropagation();
    const b = ev.target.closest("button[data-t]");
    if (!b) return;
    if (b.dataset.t === "ok") save(false);
    else if (b.dataset.t === "del") save(true);
    else { closeForceMenu(); L.markDraft = null; drawMarks(); }
  });
}
function drawMarks() {
  const ov = $("#ov");
  if (!ov || !L.sheet) return;
  const old = $("#g-marks");
  if (old) old.remove();
  const g = el("g", { id: "g-marks" }, ov);
  if ($("#show-marks") && !$("#show-marks").checked) return;
  const P = L.sheet.pitch || 11.5;
  const fs = Math.max(2.6, Math.min(4.4, P * 0.32));
  for (const mk of L.sheet.marks || []) {
    const [x0, y0, x1, y1] = mk.rect;
    const gg = el("g", { class: `mk ${mk.kind.toLowerCase()}${mk.ok === false ? " bad" : ""}`, "data-mark": mk.id }, g);
    el("rect", { x: x0, y: y0, width: x1 - x0, height: y1 - y0, class: "mk-box" }, gg);
    const label = mk.kind === "GATE" ? `게이트 ${choiceLabel(mk.choice)}` : `${MARK_KO[mk.kind]} ${mk.value}`;
    const tw = label.length * fs * 0.55 + fs;
    el("rect", { x: x0, y: y0 - fs * 1.35, width: tw, height: fs * 1.25, rx: fs * 0.25, class: "mk-tag" }, gg);
    const t = el("text", { x: x0 + fs * 0.4, y: y0 - fs * 0.4, "font-size": fs }, gg);
    t.textContent = label + " ✎";
    const refs = (mk.kind === "FROM" || mk.kind === "TO") ? refsIn(mk.value) : [];
    el("title", {}, gg).textContent = `마크업 — ${label}${mk.n ? ` (${mk.n}행)` : ""} · ${mk.author} · ${mk.at}`
      + (mk.ok === false ? `\n⚠ ${mk.why}` : "") + (refs.length ? "\n누르면 그 시트 그 행으로 갑니다 · 오른쪽 단추 = 고치기" : "\n누르면 고칩니다");
    gg.addEventListener("click", (e) => {
      if (L.justPanned) return;
      e.stopPropagation();
      if (refs.length && !e.altKey) chooseRef(refs, mk.kind === "FROM" ? "R" : "L", e);
      else markDialog(mk.rect.slice(), e, { mark: mk });
    });
    gg.addEventListener("contextmenu", (e) => { e.preventDefault(); e.stopPropagation(); markDialog(mk.rect.slice(), e, { mark: mk }); });
  }
  const d = L.markDraft;
  if (d) el("rect", { x: Math.min(d[0], d[2]), y: Math.min(d[1], d[3]), width: Math.abs(d[2] - d[0]), height: Math.abs(d[3] - d[1]), class: "mk-draft" }, g);
  const h = L.markHint;
  if (h && h.until > Date.now()) {
    const [x0, y0, x1, y1] = h.rect;
    el("rect", { x: x0 - 2, y: y0 - 2, width: x1 - x0 + 4, height: y1 - y0 + 4, class: "mk-hint" }, g);
  }
}
function bindMarkup() {
  $("#markup").onclick = () => { if (!L.sheet) { status("먼저 시트를 고르세요"); return; } setMarkMode(!L.markMode); };
  $("#show-marks").onchange = drawMarks;
  const st = $("#stage");
  let start = null;
  st.addEventListener("pointerdown", (e) => {
    if ((!L.markMode && !TEACH.draw) || e.button !== 0 || !L.sheet) return;
    e.stopPropagation(); e.preventDefault();
    start = sheetPoint(e);
    L.markDraft = [start[0], start[1], start[0], start[1]];
  }, true);
  window.addEventListener("pointermove", (e) => {
    if (!start) return;
    const p = sheetPoint(e);
    L.markDraft = [start[0], start[1], p[0], p[1]];
    drawMarks();
  });
  window.addEventListener("pointerup", (e) => {
    if (!start) return;
    const p = sheetPoint(e);
    const r = [Math.min(start[0], p[0]), Math.min(start[1], p[1]), Math.max(start[0], p[0]), Math.max(start[1], p[1])];
    start = null;
    L.markJust = true; setTimeout(() => (L.markJust = false), 0);
    if (r[2] - r[0] < 1.5 || r[3] - r[1] < 1.5) { L.markDraft = null; drawMarks(); status("사각형이 너무 작습니다 — 끌어서 그으세요"); return; }
    if (TEACH.draw) { teachRegion(r); return; }
    markDialog(r, e);
  });
  st.addEventListener("click", (e) => { if (L.markJust || L.markMode || TEACH.draw) { e.stopPropagation(); e.preventDefault(); } }, true);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && L.markMode) { setMarkMode(false); L.markDraft = null; drawMarks(); status(""); } });
  $("#idrate").addEventListener("click", (e) => {
    if (e.target.closest("#idr-toggle")) { L.idrateOpen = !L.idrateOpen; renderIdrate(); return; }
    if (e.target.closest("#idr-teach")) { $("#teach").hidden = false; placeTeach(); loadTeach(L.job, true); return; }
    const li = e.target.closest("#idr-items li[data-i]");
    if (li && L.idrate) gotoIdItem(L.idrate.items[Number(li.dataset.i)]);
  });
}

/* ------------------------------------------------------------------ L25 가르치기 — 최소한의 질문으로 전 장을

   못 읽은 것은 대개 같은 것의 되풀이다.  모양 · 글자 · 크기 · 그림이 같은 판정 못 한 블록 무리마다 질문 하나,
   시트 이름 자리 · FM/TO 열은 한 장에서 두르면 모든 장의 같은 자리, 없는 시트 이름은 이름마다 한 번.
   보기 장은 질문들을 가장 적은 장에 몰아서 고른다 (서버 teach.questions).  답은 규칙으로 남아 다시 분석해도 ·
   분석이 끝나기 전에 답해도(분석 중 미리본 장) 끝난 결과 전체에 들어간다.  마크업은 이것으로 안 되는 것만. */
const TEACH = { job: null, data: null, cur: 0, draw: null, preview: null, openAns: false, busy: false };
const TC_KIND = { GATE: "판정 못 한 모양", SHEET: "시트 이름 자리", FROM: "FM 열", TO: "TO 열", LINK: "묶음에 없는 시트" };
const TC_FIRST = ["AND", "OR", "NOT", "NAND", "NOR", "GT", "DT", "PD", "MEMORY", "MEMORY_S", "MEMORY_R", "VOTE",
                  "PASS", "ANN", "SIGNAL", "PB", "CONST1", "CONST0", "ANALOG"];
const TEACH_POS = "logic.teach.pos";

async function loadTeach(id, open) {
  id = id || L.job;
  if (!id) return;
  let r = null;
  try { r = await api(`/logic/api/jobs/${id}/teach`); } catch (e) { r = null; }
  if (L.job && L.job !== id) return;
  if (TEACH.job !== id) { TEACH.cur = 0; TEACH.preview = null; TEACH.draw = null; TEACH.msg = ""; }
  TEACH.job = id;
  TEACH.data = r;
  if (r && TEACH.cur >= r.questions.length) TEACH.cur = Math.max(0, r.questions.length - 1);
  renderTeachBtn();
  if (open && r && r.questions.length) { $("#teach").hidden = false; placeTeach(); }
  renderTeach();
  renderIdrate();
}
function renderTeachBtn() {
  const n = TEACH.data ? TEACH.data.questions.length : 0;
  $("#teach-n").textContent = n ? String(n) : "";
  $("#teach-btn").classList.toggle("has", n > 0);
}
function teachLine() {
  const r = TEACH.data;
  if (!r || !r.questions.length || TEACH.job !== L.job) return "";
  return `<div class="idr-teach">🎓 질문 <b>${r.questions.length}</b>개 · 보기 <b>${r.pages.length}</b>장에 답하면
    ${pct(r.now)} → <b>${pct(r.gain)}</b> <button class="mini" id="idr-teach">가르치기</button></div>`;
}
function clipOf(at, P) {
  const w = at[2] - at[0], h = at[3] - at[1];
  const pad = Math.max(2.2 * Math.max(w, h), 2 * (P || 11.5));
  return [at[0] - pad, at[1] - pad, at[2] + pad, at[3] + pad];
}
function cropHtml(page, at, P) {
  if (!at) return "";
  const c = clipOf(at, P);
  const cw = c[2] - c[0], ch = c[3] - c[1];
  const q = `page=${page}&x0=${c[0].toFixed(1)}&y0=${c[1].toFixed(1)}&x1=${c[2].toFixed(1)}&y1=${c[3].toFixed(1)}`;
  const hl = `left:${((at[0] - c[0]) / cw * 100).toFixed(2)}%;top:${((at[1] - c[1]) / ch * 100).toFixed(2)}%;`
    + `width:${((at[2] - at[0]) / cw * 100).toFixed(2)}%;height:${((at[3] - at[1]) / ch * 100).toFixed(2)}%`;
  return `<div class="tc-crop"><img src="/logic/api/jobs/${TEACH.job}/teach/crop.png?${q}" alt=""><i style="${hl}"></i></div>`;
}
function renderTeach() {
  const box = $("#teach");
  if (box.hidden) return;
  const r = TEACH.data;
  const body = $("#teach-b");
  if (!r) { $("#teach-sum").textContent = ""; body.innerHTML = `<p class="tc-empty">질문을 불러오지 못했습니다 — 분석이 조금 더 진행된 뒤에 다시 여세요.</p>`; return; }
  const qs = r.questions;
  $("#teach-sum").textContent = qs.length ? `질문 ${qs.length}개 · 보기 ${r.pages.length}장 · ${pct(r.now)} → ${pct(r.gain)}` : `식별 ${pct(r.now)}`;
  const head = r.final ? "" : `<p class="tc-part">⏳ 분석 중 — 지금까지 읽은 <b>${r.partial ? r.partial.sheets : 0}</b>장으로 낸 질문입니다.
     답은 분석이 끝난 결과의 <b>모든 장</b>에 들어갑니다.</p>`;
  let main;
  if (!qs.length) {
    main = `<p class="tc-empty">더 물을 것이 없습니다 — 남은 것은 마크업(✎)으로 하나씩 넣습니다.</p>`;
  } else {
    const q = qs[TEACH.cur];
    const ex = q.example || {};
    const where = `${esc(ex.sheet_no || "p" + ex.page)}`;
    const nav = `<div class="tc-nav"><button data-tc="prev" ${TEACH.cur ? "" : "disabled"}>◀</button>
       <span>${TEACH.cur + 1} / ${qs.length} · ${TC_KIND[q.kind] || q.kind} · 보기 ${where}</span>
       <button data-tc="next" ${TEACH.cur < qs.length - 1 ? "" : "disabled"}>▶</button></div>`;
    main = nav + teachCard(q, r);
  }
  const lib = r.from_library ? `<p class="tc-lib">📚 학습 사전(다른 묶음에서 가르친 답)으로 <b>${r.from_library}</b>개를 이미 읽었습니다 —
     틀렸으면 그 블록을 눌러 종류를 고치면 됩니다.</p>` : "";
  body.innerHTML = head + lib + (TEACH.msg ? `<p class="tc-msg">✓ ${esc(TEACH.msg)}</p>` : "") + main + teachAnswered(r);
}
function teachCard(q, r) {
  const ex = q.example || {};
  const P = ((L.sheets || []).find((s) => s.page === ex.page) || {}).pitch || 11.5;
  const look = r.final ? `<button data-tc="look">도면에서 보기</button>` : "";
  const skip = `<button data-tc="skip" class="tc-skip" title="이 질문은 묻지 않습니다 (되돌릴 수 있습니다)">모르겠음 · 건너뛰기</button>`;
  if (q.kind === "GATE") {
    const order = TC_FIRST.filter((k) => r.choices.some((c) => c.id === k));
    const label = (k) => (r.choices.find((c) => c.id === k) || {}).ko || k;
    return `${cropHtml(ex.page, ex.at, P)}
      <p class="tc-q">이 모양이 <b>${q.count}</b>개 · <b>${q.sheets}</b>장에 있습니다${q.text ? ` <small>(안 글자 '${esc(q.text)}')</small>` : ""}.<br>
      무엇입니까?  한 번 고르면 <b>모든 장의 같은 모양</b>에 들어가고 학습 사전에도 남아 다른 프로젝트에서도 씁니다.</p>
      <div class="tc-choices">${order.map((k) => `<button data-choice="${k}">${esc(label(k))}</button>`).join("")}</div>
      <div class="tc-foot">${look}${skip}</div>`;
  }
  if (q.kind === "SHEET") {
    return `<p class="tc-q">시트 이름을 못 읽은 장이 <b>${q.count}</b>장입니다.<br>
      한 장에서 <b>시트 이름이 인쇄된 자리</b>를 사각형으로 두르면 모든 장의 같은 자리를 읽습니다
      ${q.named_example ? ` <small>(다른 장은 '${esc(q.named_example)}' 처럼 읽었습니다)</small>` : ""}.</p>
      ${teachDrawPart(q, r)}<div class="tc-foot">${skip}</div>`;
  }
  if (q.kind === "FROM" || q.kind === "TO") {
    return `${cropHtml(ex.page, ex.at, P)}
      <p class="tc-q">${q.kind === "FROM" ? "FM(어디서 오는 신호)" : "TO(어디로 가는 신호)"} 칸을 못 읽은 행이 <b>${q.count}</b>개 · <b>${q.sheets}</b>장입니다.<br>
      보기 장에서 <b>그 열 전체</b>를 위에서 아래로 사각형으로 두르면 모든 장의 같은 열을 행마다 읽습니다.</p>
      ${teachDrawPart(q, r)}<div class="tc-foot">${skip}</div>`;
  }
  if (q.kind === "LINK") {
    const opts = (q.candidates || []).map((n) => `<option>${esc(n)}</option>`).join("");
    return `${cropHtml(ex.page, ex.at, P)}
      <p class="tc-q">FM <b>${q.count}</b>개가 <b>${esc(q.target)}</b> 을 가리키는데 이 묶음에 그 시트가 없습니다
      <small>(예: ${esc(ex.sheet_no || "")} ${ex.row || ""}행 · '${esc(ex.fm || "")}')</small>.</p>
      <div class="tc-choices"><button data-link="OTHER" title="다른 도면 묶음(문서)의 시트입니다 — 불일치로 세지 않습니다">다른 문서의 시트입니다</button></div>
      <div class="tc-alias">이 묶음의 <select id="tc-alias"><option value="">시트 고르기…</option>${opts}</select> 입니다
        <button data-link="ALIAS">저장</button></div>
      <div class="tc-foot">${look}${skip}</div>`;
  }
  return "";
}
function teachDrawPart(q, r) {
  if (!r.final) return `<p class="tc-wait">이 질문은 분석이 끝나면 도면에서 답합니다.</p>`;
  const pv = TEACH.preview;
  if (pv && pv.qid === q.id) {
    const p = pv.data;
    const rows = q.kind === "SHEET"
      ? p.sample.slice(0, 12).map((x) => `<li><b>p${x.page}</b> ${esc(x.value)}${x.now ? ` <small>(지금 ${esc(x.now)})</small>` : ""}</li>`).join("")
      : p.sample.slice(0, 12).map((x) => `<li><b>p${x.page}</b> ${x.row}행 ${esc(x.value)}</li>`).join("");
    const warn = q.kind === "SHEET" && p.same_everywhere && p.same_everywhere.length
      ? `<p class="tc-warn">⚠ '${esc(p.same_everywhere[0])}' 가 여러 장에 똑같이 나옵니다 — 시트 이름이 아니라 문서 번호일 수 있습니다.</p>` : "";
    const cnt = q.kind === "SHEET" ? `모든 장에서 ${p.read}장을 읽었습니다 — 못 읽은 ${p.missing}장 중 <b>${p.fills}</b>장을 채웁니다.`
      : `${p.pages}장에서 <b>${p.read}</b>칸을 읽었습니다 (읽힌 칸은 덮지 않고 빈 칸 · 못 읽은 칸만 채웁니다).`;
    return `<div class="tc-pv"><p>${cnt}</p>${warn}<ul>${rows}</ul>
      <button data-tc="region-save" class="v1">이대로 저장</button> <button data-tc="draw">다시 두르기</button></div>`;
  }
  const on = TEACH.draw && TEACH.draw.qid === q.id;
  return `<div class="tc-choices"><button data-tc="draw" class="${on ? "on" : ""}">${on ? "도면에서 사각형을 끌어 그으세요…" : "▭ 도면에서 두르기"}</button></div>`;
}
function teachAnswered(r) {
  const a = r.answered || {};
  const items = [];
  for (const g of a.gates || []) {
    items.push(`<li>모양${g.text ? ` '${esc(g.text)}'` : ""} → <b>${esc(((r.choices || []).find((c) => c.id === g.choice) || {}).ko || g.choice)}</b>
      <small>${esc(g.author || "")}</small> <button class="mini" data-undo="gate" data-id="${esc(g.id)}">되돌리기</button></li>`);
  }
  if (a.sheet) items.push(`<li>시트 이름 자리 <button class="mini" data-undo="sheet">되돌리기</button></li>`);
  for (const c of a.cols || []) items.push(`<li>${c === "L" ? "FM" : "TO"} 열 <button class="mini" data-undo="col" data-side="${c}">되돌리기</button></li>`);
  for (const [k, v] of Object.entries(a.links || {}))
    items.push(`<li>${esc(k)} → ${v.mode === "OTHER" ? "다른 문서" : esc(v.sheet)} <button class="mini" data-undo="link" data-id="${esc(k)}">되돌리기</button></li>`);
  for (const s of a.skipped || []) items.push(`<li>건너뛴 질문 <button class="mini" data-undo="skip" data-id="${esc(s)}">다시 묻기</button></li>`);
  if (!items.length) return "";
  return `<div class="tc-ans"><button class="mini" data-tc="ans">답한 것 ${items.length} ${TEACH.openAns ? "접기" : "보기"}</button>
    ${TEACH.openAns ? `<ul>${items.join("")}</ul>` : ""}</div>`;
}
async function teachPost(body, msg) {
  const who = await needAuthor();
  if (!who) { status("이름이 없어 저장하지 않았습니다"); return null; }
  if (TEACH.busy) return null;
  TEACH.busy = true;
  try {
    const before = TEACH.data ? TEACH.data.now : null;
    const r = await post(`/logic/api/jobs/${TEACH.job}/teach`, { ...body, author: who });
    const after = r.idrate ? r.idrate.overall : null;
    TEACH.msg = msg + (after != null ? ` — 식별 ${pct(before)} → ${pct(after)}` : " — 분석이 끝나면 모든 장에 들어갑니다");
    status(TEACH.msg);
    TEACH.preview = null; TEACH.draw = null;
    setTeachDraw(null);
    await loadTeach(TEACH.job);
    if (L.sheet && TEACH.data && TEACH.data.final) { await refreshSheet(); loadIdrate(); }
    return r;
  } catch (err) { status("저장하지 못했습니다 — " + err.message); return null; }
  finally { TEACH.busy = false; }
}
function teachLook(q) {
  const ex = q.example || {};
  gotoIdItem({ kind: "LOOK", look: true, page: ex.page, at: ex.at });
}
function setTeachDraw(d) {
  TEACH.draw = d;
  $("#stage").classList.toggle("marking", !!d || !!L.markMode);
}
async function teachRegion(rect) {
  const d = TEACH.draw;
  if (!d) return;
  setTeachDraw(null);
  status("모든 장의 같은 자리를 읽는 중…");
  try {
    const p = await post(`/logic/api/jobs/${TEACH.job}/teach/preview`, { kind: d.kind, page: L.sheet.page, rect });
    TEACH.preview = { qid: d.qid, kind: d.kind, page: L.sheet.page, rect, data: p };
    status("");
  } catch (err) { status("읽지 못했습니다 — " + err.message); }
  L.markDraft = null; drawMarks();
  $("#teach").hidden = false;
  renderTeach();
}
function placeTeach(x, y) {
  const box = $("#teach");
  if (x == null) {
    try { [x, y] = JSON.parse(lsGet(TEACH_POS) || "null") || []; } catch (e) { x = y = null; }
    if (x == null) { x = innerWidth - 400 - 24; y = 120; }
  }
  const w = box.offsetWidth || 390, h = (box.querySelector(".tc-h") || {}).offsetHeight || 30;
  x = Math.max(4, Math.min(x, innerWidth - w - 4));
  y = Math.max(4, Math.min(y, innerHeight - h - 4));
  box.style.left = x + "px"; box.style.top = y + "px";
}
function bindTeach() {
  const box = $("#teach"), head = $("#teach-h");
  head.addEventListener("pointerdown", (e) => {
    if (e.target.closest("button")) return;
    const r = box.getBoundingClientRect(), dx = e.clientX - r.left, dy = e.clientY - r.top;
    head.setPointerCapture(e.pointerId);
    const move = (ev) => placeTeach(ev.clientX - dx, ev.clientY - dy);
    const up = () => {
      head.removeEventListener("pointermove", move); head.removeEventListener("pointerup", up);
      const q = box.getBoundingClientRect();
      lsSet(TEACH_POS, JSON.stringify([Math.round(q.left), Math.round(q.top)]));
    };
    head.addEventListener("pointermove", move); head.addEventListener("pointerup", up);
  });
  $("#teach-x").onclick = () => { box.hidden = true; setTeachDraw(null); if (TEACH.job) lsSet("logic.teachclosed." + TEACH.job, "1"); };
  $("#teach-btn").onclick = () => {
    if (!box.hidden) { box.hidden = true; setTeachDraw(null); return; }
    box.hidden = false; placeTeach(); loadTeach(L.job, true);
  };
  box.addEventListener("click", async (e) => {
    const r = TEACH.data;
    if (!r) return;
    const q = r.questions[TEACH.cur];
    const b = e.target.closest("button");
    if (!b) return;
    e.stopPropagation();
    const t = b.dataset.tc;
    if (t) TEACH.msg = "";
    if (t === "prev") { TEACH.cur = Math.max(0, TEACH.cur - 1); TEACH.preview = null; renderTeach(); return; }
    if (t === "next") { TEACH.cur = Math.min(r.questions.length - 1, TEACH.cur + 1); TEACH.preview = null; renderTeach(); return; }
    if (t === "ans") { TEACH.openAns = !TEACH.openAns; renderTeach(); return; }
    if (t === "look" && q) { teachLook(q); return; }
    if (t === "skip" && q) { await teachPost({ kind: "SKIP", qid: q.id }, "건너뛰었습니다"); return; }
    if (t === "draw" && q) {
      TEACH.preview = null;
      const ex = q.example || {};
      const go = () => {
        setTeachDraw({ kind: q.kind, qid: q.id });
        status(q.kind === "SHEET" ? "시트 이름이 인쇄된 자리를 사각형으로 두르세요 (Esc 로 취소)"
          : `${q.kind === "FROM" ? "FM" : "TO"} 열 전체를 위에서 아래로 사각형으로 두르세요 (Esc 로 취소)`);
        renderTeach();
      };
      if (ex.page && (!L.sheet || L.sheet.page !== ex.page)) { L.focus = null; L.afterFit = go; openSheet(ex.page); }
      else go();
      return;
    }
    if (t === "region-save" && TEACH.preview) {
      const pv = TEACH.preview;
      await teachPost({ kind: pv.kind, page: pv.page, rect: pv.rect },
        pv.kind === "SHEET" ? `시트 이름 자리를 가르쳤습니다 — ${pv.data.fills}장을 채웠습니다` : `${pv.kind === "FROM" ? "FM" : "TO"} 열을 가르쳤습니다`);
      return;
    }
    if (b.dataset.choice && q) {
      const choice = b.dataset.choice;
      let param;
      if (choice === "VOTE") {
        const va = await askModal({ title: "투표 블록", ok: "확인",
          fields: [{ id: "v", label: "B 개 중 A 개 이상 (예: 2/3)", value: "2/3", required: true }] });
        const v = ((va && va.v) || "").match(/(\d+)\s*\/\s*(\d+)/);
        if (!v) return;
        param = { a: Number(v[1]), b: Number(v[2]) };
      }
      const lab = b.textContent;
      await teachPost({ kind: "GATE", qid: q.id, sig: q.sig, fig: q.fig, choice, param,
                        example: { page: q.example.page, block: q.example.block } },
        `같은 모양 ${q.count}개에 '${lab}' 를 넣었습니다`);
      return;
    }
    if (b.dataset.link && q) {
      const mode = b.dataset.link;
      const sheet = mode === "ALIAS" ? ($("#tc-alias") || {}).value : null;
      if (mode === "ALIAS" && !sheet) { status("이 묶음의 어느 시트인지 고르세요"); return; }
      await teachPost({ kind: "LINK", target: q.target, mode, sheet },
        mode === "OTHER" ? `${q.target} 는 다른 문서로 봅니다 (FM ${q.count}개)` : `${q.target} = ${sheet} 로 잇습니다 (FM ${q.count}개)`);
      return;
    }
    const u = b.dataset.undo;
    if (u) {
      const a = r.answered || {};
      if (u === "gate") {
        const g = (a.gates || []).find((x) => x.id === b.dataset.id);
        if (g) await teachPost({ kind: "GATE", qid: g.id, sig: g.sig, fig: g.fig, choice: null }, "가르친 모양을 되돌렸습니다");
      } else if (u === "sheet") await teachPost({ kind: "SHEET", rect: null }, "시트 이름 자리를 되돌렸습니다");
      else if (u === "col") await teachPost({ kind: b.dataset.side === "L" ? "FROM" : "TO", rect: null }, "열을 되돌렸습니다");
      else if (u === "link") await teachPost({ kind: "LINK", target: b.dataset.id, mode: null }, "되돌렸습니다");
      else if (u === "skip") await teachPost({ kind: "SKIP", qid: b.dataset.id, undo: true }, "다시 묻습니다");
    }
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && TEACH.draw) { setTeachDraw(null); L.markDraft = null; drawMarks(); status(""); renderTeach(); } });
  addEventListener("resize", () => { if (!box.hidden) placeTeach(); });
}

/* ------------------------------------------------------------------ 이벤트 */

function bind() {
  $("#job").onchange = (e) => { if (e.target.value) { hideHome(); openJob(e.target.value); } else showHome(); };
  $("#sheet-filter").oninput = renderSheetList;
  $("#ft-report").onclick = () => showFromTo();
  bindReview();
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
  bindSeq();
  bindNeeds();
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
    const gb = e.target.closest("button[data-gate]");
    if (gb) { gateMenu(gb.dataset.gate, e); return; }
    const ob = e.target.closest("button[data-opopen]");
    if (ob) { opMenu(ob.dataset.opopen, e); return; }
    const ab = e.target.closest("button[data-an]");
    if (ab) { const k = ab.dataset.an; if (k.startsWith("mon:")) monitorMenu(k.slice(4), e); else analogMenu(k, e); return; }
    const mb = e.target.closest("button[data-macro]");
    if (mb) { openMacro(mb.dataset.macro); return; }
    const nb = e.target.closest("button[data-needs]");
    if (nb) { needsOpen("block:" + nb.dataset.needs); return; }
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
    if (document.getElementById("pin-form")) { closePinForm(); return; }
    if (L.pinMode || L.pendingAt) { setPinMode(false); L.pendingAt = null; drawPins(); renderMemo(); return; }
    stopAnim();
    if (document.body.classList.contains("lg-full")) setFull(false);
  });
  bindExtras();
  bindMarkup();
  bindTeach();
}

bind();
bindHome();
initPan();
renderHelp();
/* L51 — 기능 책(범례 동작 한 줄)은 어느 길로 열려도 한 번 받는다 (첫 화면을 거치지 않고 주소로 묶음을 열어도) */
api("/logic/api/functions").then((fb) => { L.funcBook = fb || {}; }).catch(() => { L.funcBook = {}; });
if (PANE_REVIEW) startReviewPane().catch((e) => status(e.message));
else loadJobs().catch((e) => { console.error(e); status(`화면 오류 — ${e.message} (${whereErr(e)})`); });
