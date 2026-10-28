/* L36 — 블록 그룹 시험 대시보드.  분석한 Logic 의 장비(블록 그룹)마다 원 버튼으로 시험한다.
   판정은 서버(app/logic/grouptest · 같은 묶음 시뮬레이터)가 한다.  이 파일은 표를 그리고 · 누르고 · 차례로 부를 뿐이다. */
"use strict";

const $ = (s) => document.querySelector(s);
const G = { job: null, data: null, learn: {}, filter: "all", q: "", sort: "status", open: null, results: {}, running: null, stop: false };
const ST_KO = { pass: "통과", fail: "실패", warn: "확인 필요", gap: "시험 불가", none: "미시험", skip: "시험 안 함" };
const ST_C = { pass: "var(--pass)", warn: "var(--warn)", fail: "var(--fail)", gap: "var(--gap)", none: "var(--none)" };
const KIND_KO = { on: "켜기", alt: "다른 길", block: "막는 신호", hold: "유지/놓기", stop: "끄는 신호", always: "늘 켜짐",
  tied: "상수 묶임", pair: "반대 명령 동시", cancel: "반대 명령이 끔" };
const RANK = { fail: 0, warn: 1, gap: 2, none: 3, pass: 4, skip: 5 };

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
function author() {
  const u = new URLSearchParams(location.search).get("user");
  if (u) return u;
  try { return localStorage.getItem("pid.author") || ""; } catch (e) { return ""; }
}
function toast(t, ms) {
  const el = $("#toast");
  el.textContent = t; el.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => { el.hidden = true; }, ms || 3200);
}
function when(t) {
  if (!t) return "";
  const d = new Date(t * 1000), p = (n) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}
function stOf(g) { return (G.results[g.equip] && G.results[g.equip].status) || (g.test && g.test.status) || "none"; }
function countsOf(g) { return (G.results[g.equip] && G.results[g.equip].counts) || (g.test && g.test.counts) || null; }

/* ------------------------------------------------------------------ 묶음 고르기 */
async function loadJobs() {
  const j = await api("/logic/api/jobs");
  const sel = $("#job");
  const done = (j.jobs || []).filter((x) => x.state === "done");
  sel.innerHTML = `<option value="">— 묶음 고르기 —</option>` + done.map((x) =>
    `<option value="${x.id}">${esc(x.name)}${x.project ? " · " + esc(x.project) : ""} · ${x.sheets || x.total || ""}장</option>`).join("");
  const want = (location.hash.match(/job=([0-9a-f]{12})/) || [])[1] || (done[0] && done[0].id);
  if (want) { sel.value = want; await openJob(want); }
  else $("#empty").hidden = false, $("#empty").textContent = "분석된 Logic 묶음이 없습니다.";
}
async function openJob(id) {
  G.job = id; G.results = {}; G.open = null; G.learn = {};
  history.replaceState(null, "", `${location.pathname}${location.search}#job=${id}`);
  $("#back").href = `/logic${location.search}#job=${id}`;
  $("#xlsx").href = `/logic/api/jobs/${id}/grouptest.xlsx`;
  await refresh();
}
async function refresh() {
  const id = G.job;
  let d;
  try { d = await api(`/logic/api/jobs/${id}/groups`); }
  catch (e) { $("#empty").hidden = false; $("#empty").textContent = e.message; return; }
  if (id !== G.job) return;
  const same = G.data && G.data.learned_at === d.learned_at && G.data.groups.length === d.groups.length && d.state !== "done";
  G.data = d;
  if (same) { renderLearn(); setTimeout(() => { if (G.job === id && !G.running) refresh(); }, 3000); return; }   // L42 — 배우는 동안 표를 3초마다 다시 만들지 않는다
  $("#sub").textContent = `${d.name || ""}${d.project ? " · " + d.project : ""}`;
  renderLearn(); render();
  if (d.state === "running" || d.state === "none") setTimeout(() => { if (G.job === id && !G.running) refresh(); }, 3000);
}
function renderLearn() {
  const d = G.data, box = $("#learn");
  if (d.state === "done") { box.hidden = true; return; }
  const p = d.progress || {};
  const pct = p.total ? Math.round(100 * p.done / p.total) : 0;
  box.hidden = false;
  box.innerHTML = `🧠 <b>학습 중</b> ${p.total ? `${p.done}/${p.total}` : ""}${d.groups.length ? " · 아래는 지난 학습" : ""}<div class="lp"><i style="width:${pct}%"></i></div>`;
}

/* ------------------------------------------------------------------ 위쪽 카드 · 그래프 */
function tally(gs) {
  const n = { pass: 0, fail: 0, warn: 0, gap: 0, none: 0 };
  for (const g of gs) n[stOf(g)] = (n[stOf(g)] || 0) + 1;
  return n;
}
function renderTop() {
  const d = G.data, gs = d.groups, s = d.summary || {};
  const n = tally(gs);
  const cards = [["all", "장비", gs.length, "var(--navy2)"], ["cmd", "서는 명령", `${s.reached ?? "–"}<small>/${s.commands ?? "–"}</small>`, "var(--blue)"],
    ["pass", "통과", n.pass, ST_C.pass], ["warn", "확인 필요", n.warn, ST_C.warn], ["fail", "실패", n.fail, ST_C.fail],
    ["gap", "시험 불가", n.gap, ST_C.gap], ["none", "미시험", n.none, ST_C.none]];
  $("#kpis").innerHTML = cards.map(([k, t, v, c]) => `<div class="gt-kpi ${G.filter === k ? "on" : ""}" data-f="${k}" style="--c:${c}"><b>${v}</b><small>${t}</small></div>`).join("");
  const tot = gs.length || 1;
  $("#bar").innerHTML = ["pass", "warn", "fail", "gap", "none"].map((k) => n[k] ? `<i style="width:${100 * n[k] / tot}%;background:${ST_C[k]}" title="${ST_KO[k]} ${n[k]}"></i>` : "").join("");
  $("#bar-leg").innerHTML = ["pass", "warn", "fail", "gap", "none"].map((k) => `<span style="--c:${ST_C[k]}">${ST_KO[k]} ${n[k]}</span>`).join("");
  $("#kinds").innerHTML = [["latched", "자기유지", "놓아도 남는 명령"], ["momentary", "누르는 동안만", "놓으면 꺼짐"], ["pulse", "펄스", "정해진 시간만"],
    ["with_interlock", "인터록 있음", "막는 신호가 있는 명령"], ["unreached", "안 섬", "도면 읽기 빈틈 · 되먹임"],
    ["both", "반대 명령 동시", "함께 나갈 수 있는 장비"]].map(([k, t, h]) =>
    `<div title="${h}"><b>${k === "both" ? (s.both_on || []).length : (s[k] ?? "–")}</b><small>${t}</small></div>`).join("");
  $("#blockers").innerHTML = (s.common_block || []).map((x) => `<li><b>${esc(x.sheet)}</b> ${esc(x.text)} <em>· ${x.count}개</em></li>`).join("")
    || `<li><em>없음</em></li>`;
}

/* ------------------------------------------------------------------ 표 */
function visible() {
  const q = G.q.trim().toUpperCase();
  let gs = G.data.groups.filter((g) => {
    const st = stOf(g);
    if (G.filter !== "all" && G.filter !== "cmd" && st !== G.filter) return false;
    if (!q) return true;
    return g.equip.toUpperCase().includes(q) || g.sheets.some((x) => String(x).toUpperCase().includes(q)) ||
      g.actions.some((a) => a.action.includes(q) || String(a.desc || "").toUpperCase().includes(q));
  });
  const key = { status: (g) => [RANK[stOf(g)], g.equip], name: (g) => [g.equip], sheet: (g) => [String(g.sheets[0] || ""), g.equip] }[G.sort];
  gs = gs.slice().sort((a, b) => { const x = key(a), y = key(b); for (let i = 0; i < x.length; i++) { if (x[i] < y[i]) return -1; if (x[i] > y[i]) return 1; } return 0; });
  return gs;
}
function holdTag(g) {
  const ok = g.actions.filter((a) => a.reached);
  const l = ok.filter((a) => a.latch === true).length, m = ok.filter((a) => a.latch === false).length, p = ok.filter((a) => a.latch == null && a.pulse_s != null).length;
  return [l ? `<span class="tag l" title="놓아도 남는 명령 ${l}">자기유지 ${l}</span>` : "", m ? `<span class="tag m" title="놓으면 꺼지는 명령 ${m}">누르는 동안 ${m}</span>` : "",
    p ? `<span class="tag p" title="펄스 ${p}">펄스 ${p}</span>` : ""].join(" ");
}
function miniBar(c) {
  if (!c) return `<span class="cnt">—</span>`;
  const t = (c.pass || 0) + (c.warn || 0) + (c.fail || 0) + (c.gap || 0) || 1;
  return `<div class="mb">${["pass", "warn", "fail", "gap"].map((k) => c[k] ? `<i style="width:${100 * c[k] / t}%;background:${ST_C[k]}"></i>` : "").join("")}</div>
    <div class="cnt">통과 ${c.pass || 0}${c.warn ? ` · 확인 ${c.warn}` : ""}${c.fail ? ` · 실패 ${c.fail}` : ""}${c.gap ? ` · 불가 ${c.gap}` : ""}</div>`;
}
function rowHtml(g, i) {
  const st = G.running === g.equip ? "run" : stOf(g);
  const r = G.results[g.equip] || g.test;
  const sum = (k) => g.actions.reduce((a, x) => a + (x[k] || 0), 0);
  const acts = g.actions.map((a) => `<span class="act ${a.reached ? "ok" : "no"}" title="${esc(`${a.sheet}-${a.row} ${a.desc}`)}${a.reached ? "" : " — 안 섬"}">${esc(a.action)}</span>`).join("");
  const open = G.open === g.equip;
  return `<tr class="g ${open ? "open" : ""}" data-i="${i}">
    <td><span class="st ${st}">${st === "run" ? "시험 중" : ST_KO[st]}</span></td>
    <td class="nm">${esc(g.equip)}</td>
    <td>${esc(g.sheets.slice(0, 3).join(" · "))}${g.sheets.length > 3 ? " …" : ""}</td>
    <td><div class="acts">${acts}</div></td>
    <td>${holdTag(g)}</td>
    <td class="num"><b>${sum("interlocks")}</b></td><td class="num"><b>${sum("alts")}</b></td><td class="num"><b>${sum("effects")}</b></td>
    <td>${miniBar(countsOf(g))}</td>
    <td class="last">${r && r.at ? `${esc(r.author || "이름 없음")} · ${when(r.at)}${r.stale ? ` <span class="stale" title="그 뒤 분석 · 사람 값이 바뀌어 다시 배웠습니다">· 다시 시험</span>` : ""}` : ""}</td>
    <td><button class="go" data-run="${i}" ${G.running ? "disabled" : ""}>▶ 시험</button></td></tr>
    ${open ? `<tr class="det"><td colspan="11">${detailHtml(g)}</td></tr>` : ""}`;
}
/* L42 — 393 장비짜리 묶음(19VA)에서 누를 때마다 표 전체를 다시 만들던 것을: 위 카드 · 칩만 다시 세고 바뀐 줄만 바꾼다 */
function renderHead() {
  renderTop();
  const n = tally(G.data.groups);
  $("#chips").innerHTML = [["all", "전체", G.data.groups.length], ["fail", "실패", n.fail], ["warn", "확인 필요", n.warn], ["gap", "시험 불가", n.gap],
    ["none", "미시험", n.none], ["pass", "통과", n.pass]].map(([k, t, c]) => `<button data-f="${k}" class="${G.filter === k || (k === "all" && G.filter === "cmd") ? "on" : ""}">${t}<i>${c}</i></button>`).join("");
  $("#run-all").textContent = G.running ? "■ 멈추기" : `▶ 모두 시험 (${(G.shown || []).length})`;
  $("#run-all").className = "gt-btn " + (G.running ? "stop" : "pri");
  $("#run-all").disabled = !(G.shown || []).length && !G.running;
}
function paintRow(g) {
  if (!G.data) return;
  const i = (G.shown || []).indexOf(g);
  const tr = i < 0 ? null : document.querySelector(`#rows tr.g[data-i="${i}"]`);
  if (!tr) return;
  const nx = tr.nextElementSibling;
  if (nx && nx.classList.contains("det")) nx.remove();
  tr.insertAdjacentHTML("afterend", rowHtml(g, i));
  tr.remove();
}
function setRunning(v) {               // ▶ 시험 단추의 막힘만 바꾼다 (줄을 다시 만들지 않는다)
  G.running = v;
  for (const b of document.querySelectorAll("#rows button[data-run]")) b.disabled = !!v;
}
function render() {
  if (!G.data) return;
  renderTop();
  const gs = visible();
  G.shown = gs;
  const n = tally(G.data.groups);
  $("#chips").innerHTML = [["all", "전체", G.data.groups.length], ["fail", "실패", n.fail], ["warn", "확인 필요", n.warn], ["gap", "시험 불가", n.gap],
    ["none", "미시험", n.none], ["pass", "통과", n.pass]].map(([k, t, c]) => `<button data-f="${k}" class="${G.filter === k || (k === "all" && G.filter === "cmd") ? "on" : ""}">${t}<i>${c}</i></button>`).join("");
  $("#rows").innerHTML = gs.map(rowHtml).join("");
  const em = $("#empty");
  em.hidden = gs.length > 0;
  if (!gs.length) em.textContent = G.data.groups.length ? "조건에 맞는 장비가 없습니다." : (G.data.state === "done" ? "이 묶음에서 START · STOP · OPEN · CLOSE · TRIP 명령 행을 찾지 못했습니다." : "동작을 배우는 중입니다…");
  $("#run-all").textContent = G.running ? "■ 멈추기" : `▶ 모두 시험 (${gs.length})`;
  $("#run-all").className = "gt-btn " + (G.running ? "stop" : "pri");
  $("#run-all").disabled = !gs.length && !G.running;
}

/* ------------------------------------------------------------------ 펼친 장비 — 로직 이해 + 시험 항목 */
/* L42 — 신호마다 '어느 시트 어느 행' (BL10_P301-112) · 누르면 LOGIC 창이 그 자리로 간다.  행이 아닌 블록은 '시트 · 블록' */
function rowOf(l) { return l.row != null ? l.row : (/^row:(\d+)$/.exec(l.key || "") || [])[1]; }
function locHtml(l, side) {
  if (!l || !l.page) return "";
  const r = rowOf(l), sh = esc(l.sheet || `p${l.page}`);
  const blk = !r && /^block:/.test(l.key || "");
  const t = r ? `${sh}-${r}` : blk ? `${sh} · 블록` : sh;
  return `<a class="loc" data-pg="${l.page}" data-row="${r || ""}" data-side="${side || "L"}" data-key="${esc(l.key || "")}" title="LOGIC 창에서 ${t} 로 갑니다">${t}</a>`;
}
function lbl(ls) { return (ls || []).map((l) => `<li><span class="vb v${l.value}">${l.value}</span> ${locHtml(l)} ${esc(l.text)}${l.assumed ? " <small>(빈틈)</small>" : ""}</li>`).join(""); }
function sigsHtml(c) {
  const ss = c.signals || [];
  if (!ss.length) return "";
  return `<div class="sigs">${ss.map((l) => `<span class="sg${c.key && l.key === c.key && l.page === (c.at || {}).page ? " key" : ""}${l.assumed ? " gap" : ""}" title="${esc(l.text)}"><i class="v${l.value}">${l.value}</i>${locHtml(l)} <em>${esc(l.text)}</em></span>`).join("")}</div>`;
}
function understandOf(x) {
  if (!x) return "";
  if (!x.reached) {
    const b = x.blocked_at || {};
    return `<div class="u"><h4>${esc(x.action)} — 안 섬 <small>${locHtml({ page: x.page, sheet: x.sheet, row: x.row }, "R")}</small></h4><div class="why">${esc(x.why || "")}${b.label ? ` · 막힌 곳 ${esc(b.label)}` : ""}</div></div>`;
  }
  const hold = x.latch === true ? "● 자기유지" : x.latch === false ? "○ 누르는 동안만" : x.pulse_s != null ? `⏱ 펄스 ${x.pulse_s}초` : "";
  return `<div class="u"><h4>${esc(x.action)} <small>${locHtml({ page: x.page, sheet: x.sheet, row: x.row }, "R")}${hold ? " · " + esc(hold) : ""}</small></h4>
    <b>켜는 신호</b><ul>${lbl(x.labels) || "<li>신호 없이 섬</li>"}</ul>
    ${(x.alts || []).map((a, i) => `<b>다른 길 ${i + 1}</b><ul>${lbl(a.labels)}</ul>`).join("")}
    ${(x.interlocks || []).length ? `<b>막는 신호</b><ul>${lbl(x.interlocks)}</ul>` : ""}
    ${(x.stoppers || []).length ? `<b>끄는 신호</b><ul>${lbl(x.stoppers)}</ul>` : ""}
    ${(x.effects || []).length ? `<b>함께 켜짐</b><ul>${x.effects.slice(0, 8).map((e) => `<li>${locHtml(e, "R")} ${esc(e.text)}${e.to ? ` <small>→ ${esc(e.to)}</small>` : ""}</li>`).join("")}</ul>` : ""}</div>`;
}
/* L41 — 듀얼 모니터: 이 창이 LOGIC 창과 이어져 있으면 시험 신호를 그 창으로 보낸다 */
const LINK = { win: null };
function logicWin() {
  if (window.opener && !window.opener.closed) {
    try { if (window.opener.location.origin === location.origin && /^\/logic\/?$/.test(window.opener.location.pathname)) return window.opener; } catch (e) {}
  }
  return LINK.win && !LINK.win.closed ? LINK.win : null;
}
function renderLink() {
  const w = logicWin(), el = $("#link");
  if (!el) return;
  el.className = "gt-link" + (w ? " on" : "");
  el.textContent = w ? "● LOGIC 창과 이어짐" : "○ LOGIC 창 없음";
  el.title = w ? "시험하면 LOGIC 창이 그 신호를 받아 흐름을 그립니다" : "도면 → 을 누르면 LOGIC 창을 새로 엽니다 — 그 뒤로는 이어집니다";
}
/* 시험 항목 하나를 LOGIC 창에서 — 이어진 창이 있으면 보내고, 없으면 새 LOGIC 창을 그 자리로 연다 (open=false 면 열지 않는다) */
function showInLogic(equip, i, c, open = true) {
  const at = (c && c.at) || {};
  const w = logicWin();
  if (w) {
    w.postMessage({ type: "grouptest-apply", job: G.job, equip, chk: i, page: at.page || null }, location.origin);
    try { w.focus(); } catch (e) {}
    toast(`LOGIC 창에 보냄 — ${equip} · ${c ? c.title : ""}`);
  } else if (open) {
    LINK.win = window.open(simLink(i, c, equip), `logic-main-${G.job}`);
    if (!LINK.win) toast("새 창을 열지 못했습니다 — 팝업 차단을 풀어 주세요", 5000);
  }
  renderLink();
}
/* L42 — 시트 · 행 하나로 LOGIC 창을 옮긴다 (신호는 주지 않는다) */
function goInLogic(page, row, side, key) {
  if (!page) return;
  const w = logicWin();
  const msg = { type: "goto", job: G.job, page, row: row || null, side: side || "L", key: key || "" };
  if (w) { w.postMessage(msg, location.origin); try { w.focus(); } catch (e) {} }
  else {
    const h = `job=${G.job}&page=${page}${row ? `&row=${row}&side=${side || "L"}` : ""}${/^block:/.test(key || "") ? "&blk=" + encodeURIComponent(key.slice(6)) : ""}`;
    LINK.win = window.open(`/logic${location.search}#${h}`, `logic-main-${G.job}`);
    if (!LINK.win) toast("새 창을 열지 못했습니다 — 팝업 차단을 풀어 주세요", 5000);
  }
  renderLink();
}
function simLink(i, c, equip) {
  const at = c.at || {};
  return `/logic${location.search}#job=${G.job}&page=${at.page || ""}&test=${encodeURIComponent(equip || G.open)}&chk=${i}`;
}
function detailHtml(g) {
  const items = G.learn[g.equip] || null;
  const und = items ? `<div class="understand">${items.map(understandOf).join("")}</div>` : `<div class="det-h">불러오는 중…</div>`;
  const r = G.results[g.equip];
  if (!r) return und + `<div class="det-h">${g.test ? "시험 결과를 불러오는 중…" : "미시험 — <b>▶ 시험</b> 을 누르세요."}</div>`;
  const rows = (r.checks || []).map((c, i) => `<tr class="${c.status}">
      <td><span class="st ${c.status}">${ST_KO[c.status]}</span></td><td>${esc(c.action || "")}</td><td>${esc(KIND_KO[c.kind] || c.kind)}</td>
      <td class="loc-c">${locHtml(c.cmd || ((c.at || {}).row ? c.at : null), "R")}</td>
      <td>${esc(c.title)}${c.why ? `<div class="why">${esc(c.why)}</div>` : ""}${sigsHtml(c)}</td><td>${esc(c.expect)}</td><td>${esc(c.got)}</td>
      <td>${c.at && c.at.page ? `<a href="${simLink(i, c)}" data-chk="${i}" title="LOGIC 창에서 이 시험의 신호를 주고 흐름을 봅니다 (듀얼 모니터면 다른 창)">도면 →</a>` : ""}</td></tr>`).join("");
  return und + `<div class="det-h"><b>시험 항목 ${(r.checks || []).length}</b> · ${esc(r.author || "이름 없음")} · ${when(r.at)} · ${r.seconds ?? ""}초
      ${r.learned_fresh === false ? " · ⚠ 다시 학습 중" : ""}</div>
    <table class="ck"><thead><tr><th>판정</th><th>동작</th><th>항목</th><th title="그 명령이 나가는 출력 행">명령 자리</th><th>내용 · 준 신호</th><th>기대</th><th>결과</th><th></th></tr></thead><tbody>${rows}</tbody></table>`;
}
async function ensureLearn(equip) {          // L42 — 펼친 장비 하나만 받는다
  if (G.learn[equip] || !G.job) return;
  const id = G.job;
  try { const b = await api(`/logic/api/jobs/${id}/behavior?start=0&equip=${encodeURIComponent(equip)}`); if (id === G.job) G.learn[equip] = (b.result || {}).items || []; }
  catch (e) { G.learn[equip] = []; }
}
async function toggle(g) {
  const prev = G.open && G.data.groups.find((x) => x.equip === G.open);
  G.open = G.open === g.equip ? null : g.equip;
  if (prev && prev !== g) paintRow(prev);
  paintRow(g);
  if (!G.open) return;
  await Promise.all([ensureLearn(g.equip),
    !G.results[g.equip] && g.test ? api(`/logic/api/jobs/${G.job}/grouptest?equip=${encodeURIComponent(g.equip)}`).then((r) => { G.results[g.equip] = r; }).catch(() => {}) : null]);
  if (G.open === g.equip) paintRow(g);
}

/* ------------------------------------------------------------------ 원 버튼 시험 · 모두 시험 */
async function runOne(g, many) {
  setRunning(g.equip); paintRow(g);
  try {
    const r = await post(`/logic/api/jobs/${G.job}/grouptest`, { equip: g.equip, author: author() });
    G.results[g.equip] = r;
    g.test = { status: r.status, counts: r.counts, author: r.author, at: r.at, stale: false };
    return r;
  } catch (e) { toast(`${g.equip} — ${e.message}`, 5000); return null; }
  finally { setRunning(many ? "__all" : null); paintRow(g); renderHead(); }
}
async function runAll() {
  if (G.running) { G.stop = true; return; }
  const list = G.shown.slice();
  if (!list.length) return;
  G.stop = false;
  setRunning("__all"); renderHead();
  const line = $("#runline");
  line.hidden = false;
  const t0 = Date.now();
  let k = 0;
  for (const g of list) {
    if (G.stop) break;
    k++;
    line.innerHTML = `▶ ${k}/${list.length} — <b>${esc(g.equip)}</b> 시험 중<div class="rp"><i style="width:${100 * (k - 1) / list.length}%"></i></div>`;
    await runOne(g, true);                                // 사이사이 다른 단추를 막는다 (줄은 그 줄만 바꾼다)
  }
  setRunning(null);
  const n = tally(list);
  line.innerHTML = `${G.stop ? "■ 멈춤" : "✔ 끝"} — ${k}개 시험 · ${Math.round((Date.now() - t0) / 1000)}초 · 통과 ${n.pass} · 확인 ${n.warn} · 실패 ${n.fail} · 불가 ${n.gap}
    <div class="rp"><i style="width:100%"></i></div>`;
  G.stop = false;
  render();
}

/* ------------------------------------------------------------------ 묶기 */
function bind() {
  $("#job").onchange = (e) => { if (e.target.value) openJob(e.target.value); };
  $("#q").oninput = (e) => { G.q = e.target.value; render(); };
  $("#sort").onchange = (e) => { G.sort = e.target.value; render(); };
  $("#run-all").onclick = runAll;
  // 브라우저 대화상자(prompt)는 대시보드 iframe 이 막는다 (L25c) — 이름은 머리줄 칸에서
  const who = $("#who");
  who.value = author();
  if (new URLSearchParams(location.search).get("user")) who.disabled = true;
  who.onchange = () => { try { localStorage.setItem("pid.author", who.value.trim()); } catch (e) {} };
  document.addEventListener("click", (e) => {
    const f = e.target.closest("[data-f]");
    if (f) { G.filter = f.dataset.f === G.filter ? "all" : f.dataset.f; render(); return; }
    const b = e.target.closest("button[data-run]");
    if (b) { e.stopPropagation(); const g = G.shown[Number(b.dataset.run)]; if (g && !G.running) runOne(g).then((r) => {
      if (G.open !== g.equip) toggle(g);
      const cs = (r && r.checks) || [];
      const i = Math.max(0, cs.findIndex((c) => c.kind === "on" && c.at && c.at.page));
      if (cs[i] && cs[i].at && cs[i].at.page) showInLogic(g.equip, i, cs[i], false);
    }); return; }
    const lc = e.target.closest("a.loc");
    if (lc) {
      e.preventDefault(); e.stopPropagation();
      goInLogic(Number(lc.dataset.pg), Number(lc.dataset.row) || 0, lc.dataset.side, lc.dataset.key || "");
      return;
    }
    const a = e.target.closest("a[data-chk]");
    if (a) {
      e.preventDefault();
      const r = G.results[G.open], i = Number(a.dataset.chk);
      if (r && r.checks[i]) showInLogic(G.open, i, r.checks[i]);
      return;
    }
    if (e.target.closest("#back") && logicWin()) { e.preventDefault(); try { logicWin().focus(); } catch (er) {} return; }
    const tr = e.target.closest("tr.g");
    if (tr && !e.target.closest("a")) { const g = G.shown[Number(tr.dataset.i)]; if (g) toggle(g); }
  });
}
bind();
loadJobs();
renderLink(); setInterval(renderLink, 2000);
