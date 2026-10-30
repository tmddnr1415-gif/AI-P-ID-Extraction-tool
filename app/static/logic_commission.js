/* L78 — 시운전 단계.  계통 → 장비(선행 순서) → 단계.  판정은 서버(app/logic/commission · 같은 묶음 시뮬레이터)가 한다.
   이 파일은 목록을 그리고 · 단계를 돌리고 · LOGIC 창에 그 단계의 신호를 보낸다. */
"use strict";

const $ = (s) => document.querySelector(s);
const C = { job: null, data: null, equip: null, steps: null, results: null, running: false, stop: false, q: "", doc: null };
const ST_KO = { pass: "맞음", fail: "다름", warn: "확인", gap: "시험 불가", skip: "—" };
const ST_C = { pass: "var(--pass)", warn: "var(--warn)", fail: "var(--fail)", gap: "var(--gap)" };
const PH_KO = { base: "신호 없음", perm: "조건 넣기", alt: "다른 길", hold: "유지 확인", stop: "정지", block: "인터록", pair: "반대 명령", gap: "시험 불가" };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
async function api(url, opt) {
  const r = await fetch(url, opt);
  if (!r.ok) {
    let m = r.statusText;
    try { m = (await r.json()).detail || m; } catch (e) {}
    throw new Error(m);
  }
  return r.json();
}
function post(url, body) {
  return api(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
}
function toast(t, ms) {
  const el = $("#toast");
  el.textContent = t; el.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, ms || 3200);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ------------------------------------------------------------------ LOGIC 창과 잇기 (L41 과 같은 길) */
const LINK = { win: null };
function logicWin() {
  if (window.opener && !window.opener.closed) {
    try { if (window.opener.location.origin === location.origin && /^\/logic\/?$/.test(window.opener.location.pathname)) return window.opener; } catch (e) {}
  }
  return LINK.win && !LINK.win.closed ? LINK.win : null;
}
function renderLink() {
  const w = logicWin(), el = $("#link");
  el.className = "gt-link" + (w ? " on" : "");
  el.textContent = w ? "● LOGIC 창과 이어짐" : "○ LOGIC 창 없음";
}
function sendStep(s, open) {
  const msg = { type: "commission-apply", job: C.job, equip: C.equip, title: s.title, forces: s.forces, chain: s.chain || [],
    page: (s.cmd || {}).page || null, row: (s.cmd || {}).row || null };
  const w = logicWin();
  if (w) { w.postMessage(msg, location.origin); return true; }
  if (!open) return false;
  LINK.win = window.open(`/logic${location.search}#job=${C.job}&page=${msg.page || ""}&cm=1`, `logic-main-${C.job}`);
  if (!LINK.win) { toast("새 창을 열지 못했습니다 — 팝업 차단을 풀어 주세요", 5000); return false; }
  LINK.pending = msg;                 // 새 창이 묶음을 다 열면 'commission-ready' 로 알린다 — 그때 보낸다
  renderLink();
  return true;
}
function gotoLogic(page, row, side) {
  const w = logicWin();
  const msg = { type: "goto", job: C.job, page, row: row || null, side: side || "L" };
  if (w) { w.postMessage(msg, location.origin); return; }
  LINK.win = window.open(`/logic${location.search}#job=${C.job}&page=${page}${row ? `&row=${row}&side=${side || "L"}` : ""}`, `logic-main-${C.job}`);
  renderLink();
}

/* ------------------------------------------------------------------ 묶음 · 목록 */
async function loadJobs() {
  const j = await api("/logic/api/jobs");
  const sel = $("#job");
  const done = (j.jobs || []).filter((x) => x.state === "done");
  sel.innerHTML = `<option value="">— 묶음 고르기 —</option>` + done.map((x) =>
    `<option value="${x.id}">${esc(x.name)}${x.project ? " · " + esc(x.project) : ""} · ${x.sheets || ""}장</option>`).join("");
  const want = (location.hash.match(/job=([0-9a-f]{12})/) || [])[1] || (done[0] && done[0].id);
  if (want) { sel.value = want; await openJob(want); }
}
async function openJob(id) {
  C.job = id; C.equip = null; C.steps = null; C.results = null;
  history.replaceState(null, "", `${location.pathname}${location.search}#job=${id}`);
  $("#back").href = `/logic${location.search}#job=${id}`;
  $("#doc-get").href = `/logic/api/jobs/${id}/sysdesc.docx`;
  renderStepsEmpty();
  await refresh();
}
async function refresh() {
  const id = C.job;
  let d;
  try { d = await api(`/logic/api/jobs/${id}/commission`); }
  catch (e) { $("#tree").innerHTML = `<div class="gt-empty">${esc(e.message)}</div>`; return; }
  if (id !== C.job) return;
  C.data = d;
  $("#sub").textContent = `${d.name || ""}${d.project ? " · " + d.project : ""}`;
  renderLearn(); renderFacts(); renderTree(); renderDoc();
  if (d.state !== "done") setTimeout(() => { if (C.job === id) refresh(); }, 4000);
}
function renderLearn() {
  const d = C.data, box = $("#learn");
  if (d.state === "done" || !d.state) { box.hidden = true; return; }
  const p = d.progress || {};
  const pct = p.total ? Math.round(100 * p.done / p.total) : 0;
  box.hidden = false;
  box.innerHTML = `<b>동작을 배우는 중</b> — 명령 ${p.done || 0}/${p.total || "?"} · 끝나면 장비와 단계가 섭니다
    <div class="lp"><i style="width:${pct}%"></i></div>`;
}
function renderFacts() {
  const d = C.data, s = d.summary || {};
  const ne = (d.systems || []).reduce((a, x) => a + x.equips.length, 0);
  $("#facts").innerHTML = `계통 <b>${(d.systems || []).length}</b> · 장비 <b>${ne}</b> · 명령 <b>${s.commands || 0}</b>
    (시뮬레이션으로 섬 <b>${s.reached || 0}</b>)<br>연결 안 된 선 끝: ${esc(d.dangling || "")}`;
}
function renderTree() {
  const d = C.data, q = C.q.trim().toUpperCase();
  const html = (d.systems || []).map((S) => {
    const es = S.equips.filter((e) => !q || e.equip.toUpperCase().includes(q) || S.code.includes(q) || (S.name || "").toUpperCase().includes(q));
    if (!es.length) return "";
    return `<div class="cm-sys${q ? "" : " shut"}" data-sys="${esc(S.code)}"><h4><code>${esc(S.code)}</code>${esc(S.name)}<small>${S.equips.length}</small></h4><ul>${
      es.map((e) => `<li data-eq="${esc(e.equip)}" class="${e.equip === C.equip ? "on" : ""}" title="${esc(e.sheets.join(", "))}${e.deps.length ? " · 먼저: " + esc(e.deps.join(", ")) : ""}">
        <i>${e.no}</i><span class="dot" style="--c:${e.reached === e.commands ? "var(--pass)" : e.reached ? "var(--warn)" : "var(--gap)"}"></span>${esc(e.equip)}<em>${esc(e.actions.join(" · "))}</em></li>`).join("")}</ul></div>`;
  }).join("");
  $("#tree").innerHTML = html || `<div class="gt-empty">${d.state === "done" ? "장비가 없습니다." : "동작을 배우는 중입니다…"}</div>`;
  if (C.equip) { const li = $(`#tree li[data-eq="${CSS.escape(C.equip)}"]`); if (li) li.closest(".cm-sys").classList.remove("shut"); }
}
function renderDoc() {
  const d = C.data, s = d.sysdesc;
  const make = $("#doc-make"), get = $("#doc-get");
  get.hidden = !(d.sysdesc_file || (s && s.state === "done"));
  if (s && s.state === "running") {
    make.disabled = true;
    make.textContent = `📄 만드는 중 ${s.total ? Math.round(100 * s.done / s.total) : 0}%`;
    setTimeout(() => { if (C.job && C.data === d) refresh(); }, 2500);
  } else {
    make.disabled = d.state !== "done";
    make.textContent = d.sysdesc_file ? "📄 다시 만들기" : "📄 System Description 만들기";
    if (s && s.state === "failed") toast(`Word 를 만들지 못했습니다 — ${s.error}`, 6000);
  }
}

/* ------------------------------------------------------------------ 장비 · 단계 */
function renderStepsEmpty() {
  $("#head").innerHTML = ""; $("#steps").innerHTML = ""; $("#tools").hidden = true; $("#empty").hidden = false;
}
async function openEquip(name) {
  C.equip = name; C.steps = null; C.results = null;
  document.querySelectorAll("#tree li").forEach((li) => li.classList.toggle("on", li.dataset.eq === name));
  $("#empty").hidden = true;
  $("#head").innerHTML = `<h2>${esc(name)}</h2><p>단계를 만드는 중…</p>`;
  $("#steps").innerHTML = "";
  let r;
  try { r = await api(`/logic/api/jobs/${C.job}/commission/steps?equip=${encodeURIComponent(name)}`); }
  catch (e) { $("#head").innerHTML = `<h2>${esc(name)}</h2><p>${esc(e.message)}</p>`; return; }
  if (C.equip !== name) return;
  C.steps = r.steps;
  $("#tools").hidden = false;
  renderHead(r); renderSteps();
}
function renderHead(r) {
  const n = {};
  for (const x of C.results || []) n[x.status] = (n[x.status] || 0) + 1;
  $("#head").innerHTML = `<h2>${esc(C.equip)}</h2>
    <p>시트 ${(r || C.head).sheets.map((s) => esc(s)).join(", ")}${(r || C.head).deps.length ? ` · 먼저 시운전할 장비: <b>${(r || C.head).deps.map(esc).join(", ")}</b>` : ""}</p>
    <p>단계 ${C.steps.length} · 각 단계의 <b>▶</b> 를 누르면 그 단계까지 차례로 시뮬레이션합니다 (앞 단계의 상태를 이어서).</p>
    ${C.results ? `<p class="cnt">${Object.entries(n).map(([k, v]) => `<span style="--c:${ST_C[k] || "var(--soft)"}">${ST_KO[k] || k} ${v}</span>`).join("")}</p>` : ""}`;
  C.head = r || C.head;
}
function sigHtml(s, added) {
  if (!s.at && !s.text) return "";
  const m = /^(.+?)-(\d+)/.exec(s.at || "");
  return `<a class="${added && added.key === s.key && added.page === s.page ? "new" : ""}${s.value === 0 ? " v0" : ""}" data-page="${s.page || ""}" data-row="${s.row || ""}"
    title="${esc(s.text)}${s.via && s.via.length ? " · 앞 시트: " + esc(s.via.join(" ← ")) : ""} — 누르면 LOGIC 창이 그 자리로">${esc((s.text || "").slice(0, 46))}${m ? ` <b>${esc(s.at.split(" ")[0])}</b>` : ""} = ${s.value}</a>`;
}
function expectKo(s) {
  if (s.mode === "none") return "—";
  if (s.mode === "pair") return "하나만";
  if (s.kind === "block") return `${s.action} 막힘 (0)`;
  return `${s.action} ${s.expect === 1 ? "켜짐 (1)" : "꺼짐 (0)"}`;
}
function renderSteps(cur) {
  const res = C.results || [];
  $("#steps").innerHTML = C.steps.map((s, i) => {
    const r = res[i];
    const st = r ? r.status : (s.mode === "none" ? "gap" : "");
    return `<li class="cm-step${cur === i ? " cur" : ""}" data-i="${i}" style="--c:${ST_C[st] || "var(--none)"}">
      <div class="no">${s.no}</div>
      <div><div class="ph">${PH_KO[s.kind] || s.kind}</div></div>
      <div class="tt">${esc(s.title)}${s.note ? `<small>${esc(s.note)}</small>` : ""}${r && r.why ? `<small style="color:${ST_C[st]}">${esc(r.why)}</small>` : ""}
        <div class="sigs">${(s.signals || []).map((x) => sigHtml(x, s.added)).join("")}</div></div>
      <div class="ex"><b>기대</b>${esc(expectKo(s))}${r ? `<b>시뮬레이션</b><span class="got">${esc(r.got)}${r.pulse ? " (펄스)" : ""} · ${ST_KO[st] || ""}</span>` : ""}</div>
      <div class="act">${s.mode !== "none" ? `<button class="run" data-run="${i}" title="1단계부터 이 단계까지 차례로 시뮬레이션">▶ 이 단계까지</button>
        <button data-show="${i}" title="LOGIC 창에 이 단계의 신호를 주고 흐름을 봅니다 (듀얼 모니터면 다른 창)">도면에서 보기 →</button>` : ""}
        ${s.cmd && s.cmd.page ? `<button data-cmd="${i}" title="명령이 나가는 출력 행으로">명령 자리</button>` : ""}</div>
    </li>`;
  }).join("");
}
async function runUpto(n, opt) {
  if (!C.equip || C.running) return;
  const equip = C.equip;
  C.running = true; C.stop = false;
  $("#run-all").hidden = true; $("#run-stop").hidden = false;
  try {
    $("#runline").textContent = "시뮬레이션 중…";
    const r = await post(`/logic/api/jobs/${C.job}/commission/run`, { equip, upto: n });
    if (C.equip !== equip) return;
    const reveal = opt && opt.animate;
    C.results = reveal ? [] : r.steps;
    for (let i = 0; i < r.steps.length; i++) {
      if (C.stop || C.equip !== equip) break;
      if (reveal) {
        C.results = r.steps.slice(0, i + 1);
        renderSteps(i); renderHead();
        const li = $(`.cm-step[data-i="${i}"]`); if (li) li.scrollIntoView({ block: "nearest", behavior: "smooth" });
        $("#runline").textContent = `${i + 1}/${r.steps.length} 단계 — ${r.steps[i].title}`;
        if ($("#follow").checked && r.steps[i].mode !== "none") { sendStep(r.steps[i], false); await sleep(1600); }
        else await sleep(450);
      }
    }
    if (!reveal) { renderSteps(n - 1); renderHead(); }
    const k = r.counts || {};
    $("#runline").textContent = `${r.steps.length} 단계 · ${r.seconds}초 — 맞음 ${k.pass || 0}${k.warn ? ` · 확인 ${k.warn}` : ""}${k.fail ? ` · 다름 ${k.fail}` : ""}${k.gap ? ` · 시험 불가 ${k.gap}` : ""}`;
    if (opt && opt.show && r.steps[n - 1]) sendStep(r.steps[n - 1], true);
  } catch (e) { toast(e.message, 5000); $("#runline").textContent = ""; }
  finally { C.running = false; $("#run-all").hidden = false; $("#run-stop").hidden = true; renderLink(); }
}

/* ------------------------------------------------------------------ 이벤트 */
$("#job").onchange = (e) => { if (e.target.value) openJob(e.target.value); };
$("#q").oninput = (e) => { C.q = e.target.value; renderTree(); };
$("#tree").onclick = (e) => {
  const li = e.target.closest("li[data-eq]");
  if (li) { openEquip(li.dataset.eq); return; }
  const h = e.target.closest(".cm-sys > h4");
  if (h) h.parentElement.classList.toggle("shut");
};
$("#steps").onclick = (e) => {
  const b = e.target.closest("button");
  if (b && b.dataset.run != null) { runUpto(Number(b.dataset.run) + 1, { show: $("#follow").checked }); return; }
  if (b && b.dataset.show != null) { const s = (C.results && C.results[Number(b.dataset.show)]) || C.steps[Number(b.dataset.show)]; sendStep(s, true); toast(`LOGIC 창에 보냄 — ${s.title}`); return; }
  if (b && b.dataset.cmd != null) { const s = C.steps[Number(b.dataset.cmd)]; gotoLogic(s.cmd.page, s.cmd.row, "R"); return; }
  const a = e.target.closest(".sigs a");
  if (a && a.dataset.page) gotoLogic(Number(a.dataset.page), Number(a.dataset.row) || 0, "L");
};
$("#run-all").onclick = () => runUpto(C.steps ? C.steps.length : 0, { animate: true });
$("#run-stop").onclick = () => { C.stop = true; };
$("#doc-make").onclick = async () => {
  try { await post(`/logic/api/jobs/${C.job}/sysdesc`); toast("Word 를 만드는 중입니다 — 약 1분"); refresh(); }
  catch (e) { toast(e.message, 5000); }
};
window.addEventListener("message", (e) => {
  if (e.origin !== location.origin || !e.data || e.data.type !== "commission-ready") return;
  if (LINK.pending && e.source) { e.source.postMessage(LINK.pending, location.origin); LINK.pending = null; }
});
setInterval(renderLink, 2000);
renderLink();
loadJobs().catch((e) => toast(e.message, 6000));
