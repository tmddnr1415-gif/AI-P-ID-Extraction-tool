/* Review UI.
 *
 * The overlay keeps the structure spike/viewer.py established - the sheet is a
 * backdrop and every box is drawn in the browser from `pages[].layers[].items[]`
 * JSON - with one change: the backdrop now comes from the server rendering the
 * PDF on demand instead of a PNG written to disk beside the data.
 */
const $ = (s) => document.querySelector(s);
const TABS = [
  ["ALL", "전체"], ["FIELD", "Field"], ["BFV", "BFV"], ["MOV", "MOV"],
  ["PNEUMATIC", "Pneumatic"], ["REVIEW", "검토필요"],
];
const COLS = [
  ["page_no", "Page", false], ["pid_no", "P&ID No.", false],
  ["origin", "귀속", false],
  ["type", "Type", true], ["valve_type", "Valve Type", true],
  ["qty", "Q'ty", true], ["system", "System", true],
  ["vendor_supply", "Vendor", true], ["scope", "Scope", true],
  ["tag_no", "Tag No.", true], ["description", "Description", true],
];
// Layer colour by tab, stable so a kind keeps its colour across pages.
const COLOR = {
  FIELD: "#4c8dff", BFV: "#3fb950", MOV: "#f0a132", PNEUMATIC: "#c77dff",
  REVIEW: "#e5484d",
};

const S = {
  job: null, tab: "ALL", rows: [], pages: [], page: null, zoom: 1,
  sel: null, sort: { col: "page_no", dir: 1 }, filter: "", counts: {},
  originFilter: "", originCounts: {},
};

/* ---------------- upload ---------------- */
const drop = $("#drop");
["dragenter", "dragover"].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.add("over");
}));
["dragleave", "drop"].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.remove("over");
}));
drop.addEventListener("drop", ev => {
  const f = ev.dataTransfer.files[0];
  if (f) upload(f);
});
$("#file").addEventListener("change", ev => {
  if (ev.target.files[0]) upload(ev.target.files[0]);
});

async function upload(file) {
  const fd = new FormData();
  fd.append("pdf", file);
  const r = await fetch("/jobs", { method: "POST", body: fd });
  if (!r.ok) { alert((await r.json()).detail || "업로드 실패"); return; }
  const { job_id } = await r.json();
  watch(job_id);
}

async function listJobs() {
  const jobs = await (await fetch("/jobs")).json();
  $("#joblist").innerHTML = jobs.length
    ? "<p class='muted'>이전 분석</p>" + jobs.map(j =>
        `<a href="#${j.id}">${j.pdf_name} <span class="muted">${j.status}</span></a>`).join("")
    : "";
}
listJobs();

/* ---------------- progress ---------------- */
function watch(jobId) {
  drop.classList.add("hidden");
  $("#progress").classList.remove("hidden");
  const src = new EventSource(`/jobs/${jobId}/events`);
  src.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    $("#bar-fill").style.width = `${Math.round(d.progress * 100)}%`;
    $("#prog-msg").textContent = d.message || "";
    if (d.status === "done") { src.close(); open(jobId); }
    if (d.status === "failed") {
      src.close();
      $("#prog-title").textContent = "분석 실패";
      $("#prog-msg").textContent = d.message;
    }
  };
}

window.addEventListener("hashchange", () => {
  if (location.hash.length > 1) open(location.hash.slice(1));
});
if (location.hash.length > 1) open(location.hash.slice(1));

/* ---------------- load ---------------- */
async function open(jobId) {
  const job = await (await fetch(`/jobs/${jobId}`)).json();
  if (job.status !== "done") { watch(jobId); return; }
  S.job = job;
  location.hash = jobId;
  drop.classList.add("hidden");
  $("#progress").classList.add("hidden");
  $("#main").classList.remove("hidden");
  $("#job-name").textContent = job.pdf_name;
  S.pages = await (await fetch(`/jobs/${jobId}/pages`)).json();
  await loadRows();
  buildPageSelect();
  showPage(S.pages.find(p => (p.layers && Object.keys(p.layers).length)) || S.pages[0]);
}

async function loadRows() {
  S.rows = await (await fetch(`/jobs/${S.job.id}/rows?tab=ALL`)).json();
  S.counts = { ALL: S.rows.length, REVIEW: 0 };
  S.originCounts = {};
  for (const r of S.rows) {
    S.counts[r.tab] = (S.counts[r.tab] || 0) + 1;
    if (r.needs_review || r.deleted) S.counts.REVIEW++;
    S.originCounts[r.origin] = (S.originCounts[r.origin] || 0) + 1;
  }
  for (const el of document.querySelectorAll(".scope-body .n"))
    el.textContent = `${S.originCounts[el.dataset.n] || 0}행`;
  S.jobReview = await (await fetch(`/jobs/${S.job.id}/review`)).json();
  buildTabs();
  updateBadge();
  renderGrid();
}

function updateBadge() {
  const rows = S.counts.REVIEW || 0;
  const doc = (S.jobReview && S.jobReview.job_review || []).length;
  const b = $("#review-badge");
  // Document-level findings are counted too: a reviewer's load is not only the
  // rows that happen to have a rectangle.
  b.textContent = doc ? `검토 필요 ${rows}행 + 문서 ${doc}건` : `검토 필요 ${rows}건`;
  b.title = (S.jobReview && S.jobReview.job_review || [])
    .map(j => `${j.kind} p${(j.pages || []).join(",")}`).join("\n");
  b.classList.toggle("warn", rows + doc > 0);
}

/* ---------------- tabs ---------------- */
function buildTabs() {
  $("#tabs").innerHTML = "";
  for (const [key, label] of TABS) {
    const b = document.createElement("button");
    b.className = key === S.tab ? "on" : "";
    b.innerHTML = `${label}<span class="n">${S.counts[key] || 0}</span>`;
    b.onclick = () => { S.tab = key; buildTabs(); renderGrid(); drawOverlay(); };
    $("#tabs").appendChild(b);
  }
}

/* ---------------- grid ---------------- */
function visibleRows() {
  let rows = S.rows;
  if (S.tab === "REVIEW") rows = rows.filter(r => r.needs_review || r.deleted);
  else if (S.tab !== "ALL") rows = rows.filter(r => r.tab === S.tab);
  if (S.originFilter) rows = rows.filter(r => r.origin === S.originFilter);
  if (S.filter) {
    const q = S.filter.toLowerCase();
    rows = rows.filter(r => JSON.stringify(r.values).toLowerCase().includes(q)
      || String(r.page_no).includes(q));
  }
  const { col, dir } = S.sort;
  return rows.slice().sort((a, b) => {
    const av = col === "page_no" ? a.page_no : col === "origin" ? a.origin : (a.values[col] ?? "");
    const bv = col === "page_no" ? b.page_no : col === "origin" ? b.origin : (b.values[col] ?? "");
    return (av > bv ? 1 : av < bv ? -1 : 0) * dir;
  });
}

function renderGrid() {
  const head = $("#head");
  head.innerHTML = "";
  for (const [key, label] of COLS) {
    const th = document.createElement("th");
    th.textContent = label;
    if (S.sort.col === key) {
      const s = document.createElement("span");
      s.className = "dir";
      s.textContent = S.sort.dir > 0 ? " ▲" : " ▼";
      th.appendChild(s);
    }
    th.onclick = () => {
      S.sort = { col: key, dir: S.sort.col === key ? -S.sort.dir : 1 };
      renderGrid();
    };
    head.appendChild(th);
  }
  const flags = document.createElement("th");
  flags.textContent = "";
  head.appendChild(flags);

  const rows = visibleRows();
  $("#count").textContent = `${rows.length}행`;
  const body = $("#body");
  body.innerHTML = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.dataset.key = r.key;
    if (r.deleted) tr.classList.add("deleted");
    if (S.sel === r.key) tr.classList.add("sel");
    for (const [key, , editable] of COLS) {
      const td = document.createElement("td");
      const val = key === "page_no" ? r.page_no
        : key === "origin" ? r.origin
        : key === "pid_no" ? (S.pages.find(p => p.page_no === r.page_no) || {}).drawing_no || ""
        : (r.values[key] ?? "");
      td.textContent = val;
      if (key === "origin") td.classList.add(`origin-${r.origin}`);
      if (r.user && key in r.user) td.classList.add("edited");
      if (r.conflict && key in r.conflict) td.classList.add("conflict");
      if (editable && !r.deleted) {
        td.contentEditable = "true";
        td.addEventListener("blur", () => saveEdit(r, key, td));
        td.addEventListener("keydown", ev => {
          if (ev.key === "Enter") { ev.preventDefault(); td.blur(); }
        });
      }
      tr.appendChild(td);
    }
    const f = document.createElement("td");
    if (r.needs_review) f.innerHTML += '<span class="flag bad" title="검토 필요">●</span>';
    if (r.annotation) f.innerHTML += '<span class="flag" title="도면에 검토 주석">▲</span>';
    tr.appendChild(f);
    tr.onclick = () => select(r.key, true);
    body.appendChild(tr);
  }
}

async function saveEdit(row, field, td) {
  const value = td.textContent.trim();
  const current = row.values[field] ?? "";
  if (String(current) === value) return;
  const r = await fetch(`/jobs/${S.job.id}/rows/${row.key}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ field, value }),
  });
  if (!r.ok) { alert((await r.json()).detail || "저장 실패"); td.textContent = current; return; }
  const out = await r.json();
  row.user = out.user;
  row.values[field] = value === "" ? row.ai[field] : (field === "qty" ? Number(value) : value);
  delete (row.conflict || {})[field];
  S.counts.REVIEW = out.review_count;
  updateBadge();
  renderGrid();
  showEvidence(row);
}

/* ---------------- selection, both ways ---------------- */
function select(key, fromGrid) {
  S.sel = key;
  const row = S.rows.find(r => r.key === key);
  if (!row) return;
  if (fromGrid && (!S.page || S.page.page_no !== row.page_no)) {
    showPage(S.pages.find(p => p.page_no === row.page_no));
  }
  document.querySelectorAll("#body tr").forEach(tr =>
    tr.classList.toggle("sel", tr.dataset.key === key));
  document.querySelectorAll("rect.det").forEach(n =>
    n.classList.toggle("sel", n.dataset.key === key));
  const box = document.querySelector(`rect.det[data-key="${key}"]`);
  if (box) box.scrollIntoView({ block: "center", inline: "center" });
  if (!fromGrid) {
    const tr = document.querySelector(`#body tr[data-key="${key}"]`);
    if (tr) tr.scrollIntoView({ block: "center" });
  }
  showEvidence(row);
}

/* ---------------- evidence ---------------- */
function showEvidence(row) {
  const e = row.evidence || {};
  const pairs = [];
  const add = (k, v) => { if (v !== undefined && v !== null && v !== "") pairs.push([k, v]); };
  add("앵커", e.anchor);
  add("Body 판정", e.body && `${e.body} — ${JSON.stringify(e.body_basis || {})}`);
  add("개폐 상태", e.state);
  add("액추에이터", e.actuator);
  add("액추에이터 근거", e.actuator_basis);
  add("태그 버블", e.tag);
  add("산출물", e.deliverable);
  add("적용 규칙", (e.rules_hit || []).join(", "));
  add("제외 사유", e.excluded_by);
  add("수량 근거", e.qty_basis);
  add("검출 근거", e.detail && JSON.stringify(e.detail));
  add("도면 주석", (e.annotations || []).join(" / "));
  if (row.needs_review) add("검토 필요", row.needs_review);
  if (row.conflict && Object.keys(row.conflict).length) {
    add("충돌", Object.entries(row.conflict).map(([f, c]) =>
      `${f}: AI ${c.was_ai} → ${c.now_ai}, 편집값 ${c.user}`).join(" | "));
  }
  $("#evidence").innerHTML =
    `<h3>판정 근거 — ${row.values.type || row.values.valve_type || ""} (p${row.page_no})</h3>` +
    "<dl>" + pairs.map(([k, v]) => `<dt>${k}</dt><dd>${escape(String(v))}</dd>`).join("") + "</dl>";
}
const escape = (s) => s.replace(/[<>&]/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" }[c]));

/* ---------------- viewer ---------------- */
function buildPageSelect() {
  const sel = $("#page-select");
  sel.innerHTML = "";
  for (const p of S.pages) {
    const o = document.createElement("option");
    o.value = p.page_no;
    o.textContent = `p${p.page_no}  ${p.drawing_no || ""}`;
    sel.appendChild(o);
  }
  sel.onchange = () => showPage(S.pages.find(p => p.page_no === +sel.value));
}

function showPage(page) {
  if (!page) return;
  S.page = page;
  $("#page-select").value = page.page_no;
  $("#page-note").textContent = page.in_scope ? "" : `분석 제외: ${page.scope_reason}`;
  const img = $("#sheet");
  img.onload = () => { fit(); drawOverlay(); };
  img.src = `/jobs/${S.job.id}/page/${page.page_no}.png?zoom=1.6`;
}

function fit() {
  const img = $("#sheet");
  S.natural = { w: img.naturalWidth, h: img.naturalHeight };
  $("#wrap").style.width = `${S.natural.w}px`;
  $("#wrap").style.height = `${S.natural.h}px`;
  S.zoom = ($("#stage").clientWidth - 16) / S.natural.w;
  applyZoom();
}
function applyZoom() { $("#wrap").style.transform = `scale(${S.zoom})`; }
$(".toolbar").addEventListener("click", ev => {
  const z = ev.target.dataset.z;
  if (z === undefined) return;
  if (z === "0") fit(); else { S.zoom *= z === "1" ? 1.3 : 1 / 1.3; applyZoom(); }
});

function drawOverlay() {
  const ov = $("#ov");
  ov.innerHTML = "";
  if (!S.page || !S.natural) return;
  const scale = S.natural.w / (S.page.width || 1);
  ov.setAttribute("viewBox", `0 0 ${S.natural.w} ${S.natural.h}`);
  const layers = S.page.layers || {};
  for (const [tab, items] of Object.entries(layers)) {
    if (S.tab !== "ALL" && S.tab !== "REVIEW" && tab !== S.tab) continue;
    for (const it of items) {
      if (S.tab === "REVIEW" && !it.needs_review) continue;
      const [x0, y0, x1, y1] = it.rect;
      const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      r.setAttribute("x", x0 * scale);
      r.setAttribute("y", y0 * scale);
      r.setAttribute("width", Math.max(2, (x1 - x0) * scale));
      r.setAttribute("height", Math.max(2, (y1 - y0) * scale));
      r.setAttribute("class", "det" + (it.needs_review ? " review" : "")
        + (S.sel === it.key ? " sel" : ""));
      r.setAttribute("stroke", COLOR[tab] || "#888");
      r.dataset.key = it.key;
      r.onclick = () => select(it.key, false);
      ov.appendChild(r);
    }
  }
}

/* ---------------- filter, gate, export ---------------- */
$("#filter").addEventListener("input", ev => { S.filter = ev.target.value; renderGrid(); });
$("#origin-filter").addEventListener("change", ev => {
  S.originFilter = ev.target.value; renderGrid();
});
const chosenOrigins = () =>
  [...document.querySelectorAll(".origin:checked")].map(c => c.value);
document.querySelectorAll(".origin").forEach(c => c.addEventListener("change", () => {
  // Changing the scope invalidates any snapshot already taken for it.
  $("#gate-check").checked = false;
  $("#excel").disabled = true;
  $("#excel").textContent = "Excel 출력";
  S.revision = null;
}));

$("#gate-check").addEventListener("change", async ev => {
  $("#excel").disabled = !ev.target.checked;
  if (!ev.target.checked) return;
  const origins = chosenOrigins();
  if (!origins.length) { alert("출력 범위를 하나 이상 선택하세요."); ev.target.checked = false; return; }
  const r = await fetch(`/jobs/${S.job.id}/snapshot`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label: new Date().toISOString(), origins }),
  });
  const out = await r.json();
  S.revision = out.revision_id;
  $("#excel").disabled = false;
  $("#excel").textContent = `Excel 출력 (rev ${out.revision_id}, ${out.rows}행)`;
});

$("#excel").addEventListener("click", () => {
  if (!S.revision) return;
  location.href = `/revisions/${S.revision}/excel`;
});

$("#reanalyse").addEventListener("click", async () => {
  await fetch(`/jobs/${S.job.id}/reanalyse`, { method: "POST" });
  $("#main").classList.add("hidden");
  watch(S.job.id);
});
