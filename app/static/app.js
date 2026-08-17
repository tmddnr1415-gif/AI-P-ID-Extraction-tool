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
  originFilter: "", originCounts: {}, showOrigin: false,
  ovOff: new Set(), byTab: false, pending: null, drawings: [],
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
  await buildScope();
  S.jobReview = await (await fetch(`/jobs/${S.job.id}/review`)).json();
  showAppliedRules();
  await showTemplates();
  buildTabs();
  updateBadge();
  renderGrid();
}

/* Page origin.  MATCHED and PDF_ONLY only exist when the app was given a
 * finished instrument list to attribute drawings against, which is verification
 * mode; a normal run has no such file and every page is DRAWING.  So the panel,
 * the filter and the column are built from what is actually there, and when
 * DRAWING is all there is they are hidden: a choice between one option is not a
 * choice, and showing an empty MATCHED / PDF_ONLY split invites the reader to
 * think the tool compared something it never had. */
const ORIGIN_TEXT = {
  DRAWING: "도면에서 검출 (대조 기준 없음)",
  MATCHED: "대조 리스트에 대응 도면이 있는 페이지",
  REVISION_GAP: "도면에 개정 주석이 있는 페이지",
  PDF_ONLY: "대조 리스트에 행이 없는 도면",
};

function originsPresent() {
  return Object.keys(S.originCounts).filter(o => o && S.originCounts[o]);
}

/* The output scope.  Three axes, and the drawing is the first of them: a
 * contract covers some P&ID numbers and not others, and nothing in the geometry
 * can tell the tool which - so the reviewer says, grouped by system because that
 * is how the client splits its packages.  Everything starts included; a reviewer
 * takes rows out. */
async function buildScope() {
  const present = originsPresent();
  S.showOrigin = present.length > 1;
  $("#origin-filter").classList.toggle("hidden", !S.showOrigin);
  S.drawings = await (await fetch(`/jobs/${S.job.id}/drawings`)).json();

  const bySystem = {};
  for (const d of S.drawings) (bySystem[d.system || "(제목 없음)"] ||= []).push(d);
  const reviewRows = S.counts.REVIEW || 0;

  $("#scope .scope-body").innerHTML =
    `<p class="muted">Excel 에 낼 범위. 기본은 전체 포함이고, 빼는 쪽으로 고릅니다.</p>
     <label class="hold"><input type="checkbox" id="hold-review">
       <b>검토 필요 행 보류</b>
       <span class="muted">판정 보류된 행을 출력에서 뺍니다</span>
       <span class="n">${reviewRows}행</span></label>
     <div class="scope-sec"><b>도면 (P&amp;ID No.)</b>
       <button class="ghost mini" id="dwg-all">전체</button>
       <button class="ghost mini" id="dwg-none">해제</button></div>`
    + Object.entries(bySystem).map(([system, ds]) => `
        <details class="sysgroup" open>
          <summary>${escape(system).slice(0, 46)}
            <span class="n">${ds.reduce((a, d) => a + d.rows, 0)}행</span></summary>
          ${ds.map(d => `<label class="dwg"><input type="checkbox" class="drawing"
              value="${escape(d.drawing_no)}" checked>
            <span class="mono">${escape(d.drawing_no) || "(번호 없음)"}</span>
            <span class="n">${d.rows}행${d.review ? ` · 검토 ${d.review}` : ""}</span>
            </label>`).join("")}
        </details>`).join("")
    + (S.showOrigin
      ? `<div class="scope-sec"><b>귀속</b></div>`
        + present.map(o => `<label><input type="checkbox" class="origin" value="${o}" checked>
            <b>${o}</b> <span class="muted">${ORIGIN_TEXT[o] || ""}</span>
            <span class="n">${S.originCounts[o]}행</span></label>`).join("")
      : "");

  document.querySelectorAll(".origin, .drawing, #hold-review").forEach(
    c => c.addEventListener("change", scopeChanged));
  $("#dwg-all").onclick = () => setAllDrawings(true);
  $("#dwg-none").onclick = () => setAllDrawings(false);
  $("#origin-filter").innerHTML = "<option value=''>귀속 전체</option>" +
    present.map(o => `<option value="${o}">${o}</option>`).join("");
  S.originFilter = "";
}

function setAllDrawings(on) {
  document.querySelectorAll(".drawing").forEach(c => { c.checked = on; });
  scopeChanged();
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

/* ---------------- applied rules ----------------
 * Shown because the one bug that mattered so far was an inverted rule set that
 * type-checked and ran. If it happens again it should be readable on screen,
 * not inferable from a row count.
 */
function showAppliedRules() {
  const a = (S.job.engine || {}).applied_rules;
  if (!a) { $("#rules-body").innerHTML = "<p class='muted'>기록 없음</p>"; return; }
  const row = (k, v) => `<dt>${k}</dt><dd>${v}</dd>`;
  $("#rules-body").innerHTML = "<dl class='rules'>"
    + row("계기 룰셋", a.instrument_ruleset)
    + row("제외 스코프", `<b>${a.exclusion_scope_name}</b>`)
    + row("활성 제외규칙", (a.exclusion_rules_active || []).join("<br>") || "-")
    + row("비활성 제외규칙", (a.exclusion_rules_inactive || []).join("<br>") || "-")
    + row("밸브 규칙", (a.valve_rules_active || []).join(", "))
    + row("밸브 비활성", (a.valve_rules_disabled || []).join(", ") || "없음")
    + row("앵커 매핑", `${a.anchor_map_entries}건`)
    + row("Field 비대상", (a.not_field || []).join(", "))
    + row("승수", `${(S.job.engine.multipliers || {}).source} — ${(S.job.engine.multipliers || {}).note || ""}`)
    // A derivation that fell back to config, or gave up, says why right here -
    // the source alone does not tell a reviewer what to do about it.
    + row("범례 유도", Object.entries(S.job.engine.legend || {})
        .map(([k, v]) => `${k}: ${v.source}`
          + (v.source === "LEGEND" ? "" : ` <span class="muted">— ${v.note || ""}</span>`))
        .join("<br>"))
    + "</dl>";
}

/* ---------------- templates ---------------- */
async function showTemplates() {
  const t = await (await fetch("/templates")).json();
  const KIND = { FIELD: "Field Instrument", BFV: "I&C Butterfly Valve",
                 MOV: "MOV (Gate & Globe)", PNEUMATIC: "Control / Shutoff Valve",
                 MASTER: "Valve List (master)" };
  $("#tmpl-body").innerHTML =
    "<p class='muted'>발주처 양식을 올리면 그 산출물이 출력됩니다. 없으면 출력하지 않고 사유를 남깁니다.</p>"
    + Object.entries(KIND).map(([k, label]) => `
      <label class="tmpl-row">
        <span>${label}</span>
        <span class="${t[k] ? "ok" : "muted"}">${t[k] ? "있음" : "없음"}</span>
        <input type="file" accept=".xlsx" data-kind="${k}">
      </label>`).join("");
  $("#tmpl-body").querySelectorAll("input[type=file]").forEach(inp =>
    inp.addEventListener("change", async ev => {
      const f = ev.target.files[0];
      if (!f) return;
      const fd = new FormData();
      fd.append("kind", ev.target.dataset.kind);
      fd.append("file", f);
      const r = await fetch("/templates", { method: "POST", body: fd });
      if (!r.ok) { alert((await r.json()).detail || "업로드 실패"); return; }
      await showTemplates();
      // A new template changes what a snapshot can produce.
      $("#gate-check").checked = false;
      $("#excel").disabled = true;
      S.revision = null;
    }));
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
  // The 귀속 column is dropped when every page has the same origin - see
  // buildScope(): with no answer key there is nothing for it to say.
  const cols = COLS.filter(([key]) => key !== "origin" || S.showOrigin);
  for (const [key, label] of cols) {
    const th = document.createElement("th");
    th.dataset.col = key;
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
    if (r.added) tr.dataset.added = "1";
    if (r.deleted || r.removed) tr.classList.add("deleted");
    if (r.added) tr.classList.add("added");
    if (S.sel === r.key) tr.classList.add("sel");
    for (const [key, , editable] of cols) {
      const td = document.createElement("td");
      const val = key === "page_no" ? r.page_no
        : key === "origin" ? r.origin
        : key === "pid_no" ? (S.pages.find(p => p.page_no === r.page_no) || {}).drawing_no || ""
        : (r.values[key] ?? "");
      td.textContent = val;
      if (key === "origin") td.classList.add(`origin-${r.origin}`);
      if (r.user && key in r.user) td.classList.add("edited");
      if (r.conflict && key in r.conflict) td.classList.add("conflict");
      if (editable && !r.deleted && !r.removed) {
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
    if (r.added) f.innerHTML += '<span class="flag ok" title="검토자 추가 행">＋</span>';
    if (r.removed) f.innerHTML += '<span class="flag" title="검토자 삭제 — 출력 제외">✕</span>';
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

/* ---------------- selection, both ways ----------------
 *
 * From the grid: open the row's page, zoom in far enough to actually see the
 * symbol, centre it and pulse it.  From the drawing: select the row and scroll
 * the grid to it.  Escape, or a click on empty sheet, clears both.
 */
const SYMBOL_ZOOM = 2.2;      // enough to read a 22pt bubble on a 2384pt sheet

function select(key, fromGrid, item) {
  S.sel = key;
  const row = S.rows.find(r => r.key === key);
  if (fromGrid && row && (!S.page || S.page.page_no !== row.page_no)) {
    // The page render is async; centre once the overlay for it exists.
    S.pending = key;
    showPage(S.pages.find(p => p.page_no === row.page_no));
    return;
  }
  document.querySelectorAll("#body tr").forEach(tr =>
    tr.classList.toggle("sel", tr.dataset.key === key));
  document.querySelectorAll("rect.det").forEach(n =>
    n.classList.toggle("sel", n.dataset.key === key));
  if (fromGrid) centreOnSymbol(key);
  else {
    const tr = document.querySelector(`#body tr[data-key="${key}"]`);
    if (tr) tr.scrollIntoView({ block: "center" });
  }
  pulse(key);
  if (row) showEvidence(row);
  else showExcluded(item);       // an excluded symbol has no row to show
}

function deselect() {
  S.sel = null;
  S.pending = null;
  document.querySelectorAll("#body tr.sel").forEach(tr => tr.classList.remove("sel"));
  document.querySelectorAll("rect.det.sel").forEach(n => n.classList.remove("sel"));
  $("#evidence").innerHTML =
    "<p class='muted'>행을 클릭하면 판정 근거가 여기에 표시됩니다.</p>";
}

function centreOnSymbol(key) {
  const box = document.querySelector(`rect.det[data-key="${key}"]`);
  if (!box) return;
  if (S.zoom < SYMBOL_ZOOM) { S.zoom = SYMBOL_ZOOM; applyZoom(); }
  const stage = $("#stage");
  const x = (+box.getAttribute("x") + +box.getAttribute("width") / 2) * S.zoom;
  const y = (+box.getAttribute("y") + +box.getAttribute("height") / 2) * S.zoom;
  stage.scrollTo({
    left: Math.max(0, x - stage.clientWidth / 2),
    top: Math.max(0, y - stage.clientHeight / 2),
    behavior: "smooth",
  });
}

function pulse(key) {
  const box = document.querySelector(`rect.det[data-key="${key}"]`);
  if (!box) return;
  box.classList.remove("pulse");
  void box.getBoundingClientRect();          // restart the animation
  box.classList.add("pulse");
}

function showExcluded(item) {
  if (!item) return;
  const label = (SCOPE.find(s => s[0] === item.scope) || [, item.scope, "", ""]);
  const notes = (item.notes_text || []).map(t => `“${t}”`).join(" / ");
  $("#evidence").innerHTML =
    `<h3>제외된 심볼 — ${escape(item.label || "")} (p${S.page.page_no})</h3><dl>`
    + `<dt>스코프 판정</dt><dd>${label[1]} — ${label[3]}</dd>`
    + `<dt>적용 규칙</dt><dd>${escape(item.reason || "")}</dd>`
    + (notes ? `<dt>NOTES 원문</dt><dd>${escape(notes)}</dd>` : "")
    + `<dt>위치</dt><dd>${escape(S.page.drawing_no || "")} · p${S.page.page_no}`
    + ` · (${item.rect.map(v => Math.round(v)).join(", ")})</dd>`
    + `<dt>리스트 반영</dt><dd>없음 — 제외 규칙이 걸려 행으로 나오지 않습니다</dd></dl>`;
}

/* ---------------- evidence ----------------
 *
 * Everything needed to accept or reject one row, so the reader never has to go
 * back to the drawing to answer "why": what scope it was put in and by which
 * rule, the quantity and where its multiplier came from, how the body and
 * actuator were classified and on what, where it is, and - when the tool held
 * off - what it could not decide.  Order matters: scope first, because that is
 * what decides whether the row exists at all.
 */
function showEvidence(row) {
  const e = row.evidence || {};
  const pairs = [];
  const add = (k, v) => { if (v !== undefined && v !== null && v !== "") pairs.push([k, v]); };
  const hits = e.rules_hit || [];

  // --- scope: included or not, by which rule, in the NOTES' own words -------
  const scopeName = row.needs_review ? "검토 필요"
    : row.values.scope === "SCT" ? "SCT 표시"
    : row.values.vendor_supply === "VENDOR" ? "벤더 공급"
    : row.values.vendor_supply === "UNDEFINED" ? "벤더 마크 (정의 없음)"
    : "포함";
  add("스코프 판정", `${scopeName} — 이 행은 리스트에 ${row.removed ? "제외" : "포함"}됩니다`);
  add("적용 규칙", hits.length ? hits.join(", ") : "제외 규칙 해당 없음");
  add("제외 사유", e.excluded_by);
  // The NOTES line that defined this drawing's vendor mark, verbatim.  Quoted,
  // not interpreted: the tool matches the mark, the reader reads the sentence.
  add("NOTES 원문", (e.notes_text || []).map(t => `“${t}”`).join(" / "));

  // --- quantity -------------------------------------------------------------
  add("수량", row.values.qty);
  add("수량 근거", e.qty_basis);
  add("승수 출처", e.qty_source);

  // --- classification -------------------------------------------------------
  add("앵커", e.anchor);
  add("Type 판정", row.values.type && `${row.values.type}${e.anchor ? ` ← 앵커 ${e.anchor}` : ""}`);
  add("Body 판정", e.body && `${e.body} — ${JSON.stringify(e.body_basis || {})}`);
  add("개폐 상태", e.state);
  add("액추에이터", e.actuator);
  add("액추에이터 근거", e.actuator_basis);
  add("태그 버블", e.tag);
  add("산출물", e.deliverable);
  add("검출 근거", e.detail && JSON.stringify(e.detail));

  // --- where ----------------------------------------------------------------
  const pg = S.pages.find(p => p.page_no === row.page_no) || {};
  add("위치", `${pg.drawing_no || ""} · p${row.page_no}`
    + (row.rect && row.rect.length
      ? ` · (${row.rect.map(v => Math.round(v)).join(", ")})` : " · 좌표 없음"));
  add("귀속", row.origin);
  add("도면 주석", (e.annotations || []).join(" / "));

  // --- what was not decided -------------------------------------------------
  if (row.needs_review) add("검토 필요 — 판단 못한 이유", row.needs_review);
  if (row.deleted) add("검토 필요", "재분석에서 이 검출이 사라졌습니다");
  if (row.conflict && Object.keys(row.conflict).length) {
    add("충돌", Object.entries(row.conflict).map(([f, c]) =>
      `${f}: AI ${c.was_ai} → ${c.now_ai}, 편집값 ${c.user}`).join(" | "));
  }
  if (row.user && Object.keys(row.user).length) {
    add("사람이 고친 값", Object.entries(row.user)
      .map(([f, v]) => `${f} = ${v}`).join(" | "));
  }
  $("#evidence").innerHTML =
    `<h3>판정 근거 — ${escape(row.values.type || row.values.valve_type || "")} `
    + `(p${row.page_no})</h3>`
    + "<dl>" + pairs.map(([k, v]) =>
      `<dt>${k}</dt><dd>${escape(String(v))}</dd>`).join("") + "</dl>";
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
  img.onload = () => {
    fit();
    drawOverlay();
    // A selection made from the grid was waiting for this page to arrive.
    if (S.pending) { const k = S.pending; S.pending = null; select(k, true); }
  };
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

/* ---------------- overlay ----------------
 *
 * The drawing is coloured by *scope*, not by tab, because the question a
 * reviewer asks of the sheet is "why is this one not in my list" - and that is
 * unanswerable when an excluded symbol and a delivered one are the same colour,
 * or when the excluded one is not drawn at all.  Vendor-marked and SCT symbols
 * never become rows, so the pipeline emits them as their own layer.
 *
 * Colour carries the scope and the dash carries the deliverable kind, so the two
 * compose instead of competing: four hues against a white sheet of thin black
 * line work, all of them saturated enough not to read as drawing ink, and none
 * of them grey. Tab colouring is still available as a mode for the old view.
 */
const SCOPE = [
  ["INCLUDED", "포함", "#0a84ff", "우리 공급 범위 — 리스트에 나옴"],
  ["VENDOR_EXCLUDED", "벤더 제외", "#ff9f0a", "기기에 벤더 마크 → 리스트에서 제외"],
  ["SCT", "SCT", "#bf5af2", "공급자 스코프 박스 안 (계약 범위 밖 배관)"],
  ["REVIEW", "검토 필요", "#ff453a", "판정 보류 — 근거 패널의 사유 확인"],
];
const SCOPE_COLOR = Object.fromEntries(SCOPE.map(([k, , c]) => [k, c]));

function overlayItems(page) {
  const out = [];
  for (const [tab, items] of Object.entries(page.layers || {})) {
    for (const it of items) out.push({ ...it, tab });
  }
  return out;
}

function itemVisible(it) {
  if (S.ovOff.has(it.scope || "INCLUDED")) return false;
  if (S.tab === "REVIEW") return !!it.needs_review;
  if (S.tab === "ALL") return true;
  // A deliverable tab shows its own rows, and keeps the excluded symbols on
  // screen: they are the reason a count comes up short.
  return it.tab === S.tab || it.tab === "EXCLUDED";
}

function buildOverlayLegend() {
  const items = S.page ? overlayItems(S.page) : [];
  const counts = {};
  for (const it of items) {
    const k = it.scope || "INCLUDED";
    counts[k] = (counts[k] || 0) + 1;
  }
  $("#ovl-items").innerHTML = SCOPE.map(([key, label, colour, why]) => `
    <label class="ovl-row" title="${why}">
      <input type="checkbox" class="ovl" value="${key}"
             ${S.ovOff.has(key) ? "" : "checked"}>
      <span class="swatch" style="background:${colour}"></span>
      <span class="ovl-label">${label}</span>
      <span class="n">${counts[key] || 0}</span>
    </label>`).join("");
  document.querySelectorAll(".ovl").forEach(c => c.addEventListener("change", () => {
    if (c.checked) S.ovOff.delete(c.value); else S.ovOff.add(c.value);
    drawOverlay();
  }));
}

function drawOverlay() {
  const ov = $("#ov");
  ov.innerHTML = "";
  if (!S.page || !S.natural) return;
  const scale = S.natural.w / (S.page.width || 1);
  ov.setAttribute("viewBox", `0 0 ${S.natural.w} ${S.natural.h}`);
  for (const it of overlayItems(S.page)) {
    if (!itemVisible(it)) continue;
    const [x0, y0, x1, y1] = it.rect;
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("x", x0 * scale);
    r.setAttribute("y", y0 * scale);
    r.setAttribute("width", Math.max(2, (x1 - x0) * scale));
    r.setAttribute("height", Math.max(2, (y1 - y0) * scale));
    r.setAttribute("class", "det"
      + (it.kind === "VALVE" ? " valve" : "")
      + (it.row === false ? " excluded" : "")
      + (S.sel === it.key ? " sel" : ""));
    r.setAttribute("stroke", S.byTab
      ? (COLOR[it.tab] || "#8e8e93")
      : (SCOPE_COLOR[it.scope || "INCLUDED"] || "#8e8e93"));
    r.dataset.key = it.key;
    r.onclick = (ev) => { ev.stopPropagation(); select(it.key, false, it); };
    ov.appendChild(r);
  }
  buildOverlayLegend();
}

$("#ovl-bytab").addEventListener("change", ev => {
  S.byTab = ev.target.checked;
  drawOverlay();
});
// Clicking the sheet itself, away from any box, clears the selection.
$("#stage").addEventListener("click", ev => {
  if (ev.target.tagName.toLowerCase() !== "rect") deselect();
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && !ev.target.isContentEditable) deselect();
});

/* ---------------- filter, gate, export ---------------- */
$("#filter").addEventListener("input", ev => { S.filter = ev.target.value; renderGrid(); });
$("#origin-filter").addEventListener("change", ev => {
  S.originFilter = ev.target.value; renderGrid();
});
const chosenOrigins = () =>
  [...document.querySelectorAll(".origin:checked")].map(c => c.value);

function scopeChanged() {
  // Changing the scope invalidates any snapshot already taken for it.
  $("#gate-check").checked = false;
  $("#excel").disabled = true;
  $("#excel").textContent = "Excel 출력";
  S.revision = null;
}

$("#gate-check").addEventListener("change", async ev => {
  $("#excel").disabled = !ev.target.checked;
  if (!ev.target.checked) return;
  const origins = chosenOrigins();
  if (S.showOrigin && !origins.length) {
    alert("귀속을 하나 이상 선택하세요."); ev.target.checked = false; return;
  }
  const drawings = [...document.querySelectorAll(".drawing:checked")].map(c => c.value);
  if (!drawings.length) {
    alert("도면을 하나 이상 선택하세요."); ev.target.checked = false; return;
  }
  const hold = !!($("#hold-review") || {}).checked;
  const r = await fetch(`/jobs/${S.job.id}/snapshot`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label: new Date().toISOString(), origins,
                           drawings, hold_review: hold }),
  });
  if (!r.ok) {
    alert((await r.json()).detail || "스냅샷 실패");
    ev.target.checked = false; $("#excel").disabled = true; return;
  }
  const out = await r.json();
  S.revision = out.revision_id;
  window.__rev = out.revision_id;      // read by tests/test_ui_edits.py
  $("#excel").disabled = false;
  $("#excel").textContent = `Excel 출력 (rev ${out.revision_id}, ${out.rows}행`
    + (hold ? ", 검토 보류" : "") + ")";
});

$("#excel").addEventListener("click", () => {
  if (!S.revision) return;
  location.href = `/revisions/${S.revision}/excel`;
});

/* ---------------- row add / copy / delete ---------------- */
async function refreshRows(selectKey) {
  await loadRows();
  if (selectKey) select(selectKey, true);
}

$("#row-add").addEventListener("click", async () => {
  const src = S.rows.find(r => r.key === S.sel);
  const body = {
    page_no: src ? src.page_no : (S.page ? S.page.page_no : 0),
    tab: src ? src.tab : (S.tab === "ALL" || S.tab === "REVIEW" ? "FIELD" : S.tab),
    origin: src ? src.origin : "",
    drawing_no: src ? src.drawing_no : (S.page ? S.page.drawing_no : ""),
    values: {},
  };
  const r = await fetch(`/jobs/${S.job.id}/rows`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) { alert("행 추가 실패"); return; }
  await refreshRows((await r.json()).key);
});

$("#row-copy").addEventListener("click", async () => {
  if (!S.sel) { alert("복사할 행을 먼저 선택하세요."); return; }
  const r = await fetch(`/jobs/${S.job.id}/rows/${S.sel}/copy`, { method: "POST" });
  if (!r.ok) { alert("복사 실패"); return; }
  await refreshRows((await r.json()).key);
});

$("#row-delete").addEventListener("click", async () => {
  if (!S.sel) { alert("삭제할 행을 먼저 선택하세요."); return; }
  const key = S.sel;
  const r = await fetch(`/jobs/${S.job.id}/rows/${key}`, { method: "DELETE" });
  if (!r.ok) { alert("삭제 실패"); return; }
  const out = await r.json();
  // A detection is struck out, not dropped: the next analysis would find it
  // again, and the reviewer's decision has to outlive that.
  S.sel = out.dropped ? null : key;
  await refreshRows(S.sel);
});

$("#reanalyse").addEventListener("click", async () => {
  await fetch(`/jobs/${S.job.id}/reanalyse`, { method: "POST" });
  $("#main").classList.add("hidden");
  watch(S.job.id);
});
