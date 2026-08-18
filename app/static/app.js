/* Review UI.
 *
 * The overlay keeps the structure spike/viewer.py established - the sheet is a
 * backdrop and every box is drawn in the browser from `pages[].layers[].items[]`
 * JSON - with one change: the backdrop now comes from the server rendering the
 * PDF on demand instead of a PNG written to disk beside the data.
 */
const $ = (s) => document.querySelector(s);
/* A typo'd or renamed id used to return null here, and the `addEventListener`
 * that followed threw during load - which stopped every handler *below* it from
 * binding at all.  The symptom was distant: clicking ＋행 did nothing because an
 * unrelated checkbox in the legend was missing.  Now it says so. */
const $req = (sel) => {
  const n = document.querySelector(sel);
  if (!n) throw new Error(`app.js: ${sel} is not in index.html`);
  return n;
};
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
  // Two columns that exist so a reviewer can see, without opening anything, which
  // rows they have to write themselves.  `등급` is filterable from the toolbar.
  ["description_grade", "등급", false], ["remark", "Remark", true],
];
// What each grade asks of the reviewer, shown in the review tab's grouping.
const GRADES = [
  ["CONFIRMED", "확정", "도면이 이름을 대는 것으로 채워졌습니다"],
  ["LOW", "AI 제안", "후보에서 골랐으나 근거가 약합니다 — 확인 필요"],
  ["PARTIAL", "부분", "단위·계통·변수만 확정 — 중간 서술을 직접 입력"],
  ["NONE", "없음", "근거 없음 — 직접 입력"],
  ["SKIP", "생략", "타사 공급"],
  ["USER_ENTERED", "직접 입력", "사람이 입력했습니다"],
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
  picking: false, feedback: 0, showTrace: true, gradeFilter: "",
  // Which trace layers the reviewer switched off: pipe | up | down | break.
  trOff: new Set(),
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
  S.feedback = (await (await fetch(`/jobs/${S.job.id}/feedback?limit=1`)).json()).count;
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
  // Collection status only.  What the history *means* is a later question and
  // deliberately not answered here.
  const fb = $("#fb-badge");
  fb.textContent = S.feedback ? `수정 이력 ${S.feedback}건 기록됨` : "";
  fb.classList.toggle("hidden", !S.feedback);
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
  // The span label is a project fact from config, so it comes from the run
  // rather than being written twice.
  const ds = (S.job.engine || {}).description_scope || {};
  if (ds.supplier_span_label) SUPPLIER_SPAN_LABEL = ds.supplier_span_label;
  const pt = (S.job.engine || {}).pipe_trace || {};
  const st = pt.per_status || {};
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
    // Two axes, printed apart: how many rows are in the list, and how many of
    // them will ever carry a Description.  The trace rate is stated on the
    // Description-needed denominator, because that is what the stage was asked.
    + row("Description 대상", `${ds.needed ?? "-"}행 · 생략 ${ds.skipped ?? 0}행`
      + (Object.keys(ds.by_reason || {}).length
        ? `<br><span class="muted">${Object.entries(ds.by_reason)
          .map(([k, v]) => `${k}: ${v}`).join("<br>")}</span>` : ""))
    + row("Description 생성", (() => {
      const b = (S.job.engine || {}).description_build || {};
      const m = b.measured_accuracy || {};
      if (!b.pattern) return "기록 없음";
      return `${b.written ?? 0}행 작성 · ${b.blank ?? 0}행 공란`
        + `<br><span class="muted">문형 <code>${b.pattern.template || ""}</code>`
        + ` (${b.pattern.measured_on || ""})`
        + `<br>변수어: 범례 p${(b.isa_table || {}).page_no} ISA 문자표`
        + ` — 첫 문자 ${Object.keys((b.isa_table || {}).first || {}).length}개`
        + `<br>발주처 ${m.lines_compared}행 대조: 완전일치 ${m.exact}행 · `
        + `토큰 정밀도 ${m.token_precision}% / 재현율 ${m.token_recall}%`
        + ` — 중간 서술과 접미는 도면에 없어 만들지 않습니다</span>`;
    })())
    + row("배관 추적", `대상 ${pt.description_needed ?? 0}행 중 `
      + `성공 ${st.TRACED || 0} (${pt.rate_of_needed ?? 0}%) · `
      + `후보다수 ${st.MULTIPLE || 0} · 실패 ${st.FAILED || 0}`
      + `<br><span class="muted">전체 행 기준 ${pt.rate_of_all_rows ?? 0}% · `
      + `추적 생략 ${pt.skipped_not_needed ?? 0}행</span>`)
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
    b.dataset.tab = key;
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
  // Only on 검토필요, where the control that sets it is visible.  Left applied on
  // other tabs it silently hid rows with nothing on screen to explain why.
  if (S.tab === "REVIEW" && S.gradeFilter) {
    rows = rows.filter(r => r.values.description_grade === S.gradeFilter);
  }
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

/* The review tab's own grouping: which rows still need a Description written by
 * hand, split by the reason the tool could not write one.  Clicking a group
 * filters the grid to it, because "which of these 700 rows is mine to do" is the
 * question a reviewer opens this tab with. */
function renderDescriptionGroups() {
  const bar = $("#desc-groups");
  if (S.tab !== "REVIEW") { bar.classList.add("hidden"); return; }
  bar.classList.remove("hidden");
  const counts = {};
  for (const r of S.rows) {
    const g = r.values.description_grade;
    if (g) counts[g] = (counts[g] || 0) + 1;
  }
  const needed = GRADES.filter(([k]) => ["PARTIAL", "LOW", "NONE"].includes(k));
  const total = needed.reduce((n, [k]) => n + (counts[k] || 0), 0);
  bar.innerHTML = `<b>Description 입력 필요</b> <span class="n">${total}행</span>`
    + needed.map(([k, label, why]) => `
        <button class="grp${S.gradeFilter === k ? " on" : ""}" data-g="${k}"
                title="${why}">${label} <span class="n">${counts[k] || 0}</span></button>`).join("")
    + `<button class="grp${S.gradeFilter ? "" : " on"}" data-g="">전체</button>`;
  bar.querySelectorAll("button.grp").forEach(b => {
    b.onclick = () => {
      S.gradeFilter = b.dataset.g === S.gradeFilter ? "" : (b.dataset.g || "");
      renderGrid();
    };
  });
}

/* The Remark a reviewer should see.  A row a person has written needs no note
 * about what the tool could not do, so it shows none - the grade already says
 * USER_ENTERED, and the engine's original note stays in the row's evidence. */
function remarkOf(row) {
  return row.values.description_grade === "USER_ENTERED"
    ? "" : (row.values.remark ?? "");
}

function renderGrid() {
  renderDescriptionGroups();
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
        : key === "remark" ? remarkOf(r)
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
  if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
  updateBadge();
  // Update this cell in place instead of rebuilding the grid.  A save completes
  // after the reviewer has already clicked into the next cell, and a full
  // re-render at that moment replaced the element being typed into - the edit
  // went to a detached node and vanished.
  td.textContent = row.values[field] ?? "";
  td.classList.toggle("edited", !!(row.user && field in row.user));
  td.classList.remove("conflict");
  if (S.sel === row.key) showEvidence(row);
}

/* Writing a Description by hand.
 *
 * A reviewer picks a candidate phrase off the evidence panel, or types one, and
 * the row becomes USER_ENTERED with an empty Remark - the tool stops asking about
 * a row a person has answered.  The same text can be pushed to every row on the
 * same drawing with the same TYPE, because 721 rows share 85 machine-written
 * sentences and retyping the difference by hand is the actual work.
 */
async function setDescription(row, text, opts = {}) {
  const patch = async (r, field, value) => {
    const res = await fetch(`/jobs/${S.job.id}/rows/${r.key}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, value }),
    });
    if (!res.ok) { alert((await res.json()).detail || "저장 실패"); return false; }
    const out = await res.json();
    r.user = out.user;
    r.values[field] = value;
    S.counts.REVIEW = out.review_count;
    if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
    return true;
  };
  const targets = opts.bulk
    ? S.rows.filter(r => !r.deleted && !r.removed
        && r.drawing_no === row.drawing_no && r.values.type === row.values.type)
    : [row];
  for (const r of targets) {
    if (!await patch(r, "description", text)) return;
    // The grade is a user value; the Remark is not patched to empty because an
    // empty edit means "revert to what the engine said" (db.set_user_value), and
    // reverting would put the old "직접 입력" note back.  A USER_ENTERED row simply
    // shows no Remark - see remarkOf().
    await patch(r, "description_grade", "USER_ENTERED");
  }
  updateBadge();
  renderGrid();
  const again = S.rows.find(r => r.key === row.key);
  if (again) showEvidence(again);
  if (opts.bulk) {
    alert(`${targets.length}행에 적용했습니다 — ${row.drawing_no} / ${row.values.type}`);
  }
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
  drawOverlay();          // the traced path belongs to the selected row
  document.querySelectorAll("#body tr").forEach(tr =>
    tr.classList.toggle("sel", tr.dataset.key === key));
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
  drawOverlay();
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
    : row.values.scope === "SCT" ? SUPPLIER_SPAN_LABEL
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

  // --- multi-signal bubble group --------------------------------------------
  // Three bubbles drawn edge-to-edge are three signals off one physical
  // instrument.  The group is shown; the quantity is not touched, because neither
  // the legend nor the client's own list says what the physical count is.
  const grp = e.signal_group;
  if (grp) {
    add("다중 신호 버블", `${grp.members.length}개 버블이 한 묶음으로 그려져 있습니다 — `
      + grp.members.map(m => m.anchor || m.type).join(" / "));
    add("묶음 근거", `테두리 간격 ${(grp.basis.touching_gaps_pt || []).join(", ")}pt `
      + `(허용 ${grp.basis.slack_pt}pt, legend_rules.INDEX_SLACK) · `
      + `첫 문자 '${grp.basis.shared_first_letter}' 공통 · 세로 정렬`);
    add("적용된 수량", `${(grp.basis.qty_applied || []).join(" + ")} — `
      + "합산하지 않았습니다. 범례 p3 은 다기능 계기를 버블 1개로 그리고 "
      + "묶음 표기를 정의하지 않으며, 발주처 리스트는 이 도면들을 다루지 않습니다");
  }

  // --- Description axis (separate from scope) --------------------------------
  const needed = e.description_needed;
  if (needed === false) {
    add("Description 대상", `아님 — ${e.description_note || ""}`);
    add("배관 추적", "수행하지 않았습니다 (Description 대상이 아니므로)");
  } else if (needed === true) {
    add("Description 대상", "예 — 리스트와 Description 모두 대상");
  }
  // Where each part of the sentence came from, and what is still missing.  The
  // column is a partial line by construction, so the panel says so rather than
  // letting it read as finished text.
  if ((e.description_sources || []).length) {
    add("Description 조립 근거", e.description_sources.join(" | "));
  }
  if (e.description_missing) add("Description 미완성 사유", e.description_missing);
  if (row.values.description_grade) {
    const g = GRADES.find(x => x[0] === row.values.description_grade);
    add("Description 등급", g ? `${g[1]} — ${g[2]}` : row.values.description_grade);
  }
  if (remarkOf(row)) add("Remark", remarkOf(row));
  if (e.description_selected) {
    const sel = e.description_selected;
    add("선택된 중간 서술", `“${sel.middle}” (${sel.kind})`
      + (sel.why ? ` — ${sel.why}` : ""));
  }

 // --- pipe connectivity ----------------------------------------------------
  const tr = e.trace || {};
  if (tr.status && tr.status !== "SKIPPED") {
    const names = (list) => (list || []).map(t =>
      `${t.label || t.kind}${t.kind === "EQUIPMENT" ? " (기기)" : ""}`).join(" / ");
    const label = { TRACED: "추적 성공", MULTIPLE: "후보 다수", FAILED: "추적 실패" };
    add("배관 추적", `${label[tr.status] || tr.status}`
      + (tr.attached_by ? ` — 심볼 접점: ${tr.attached_by === "leader"
        ? "리드선" : "배관 위"}` : "")
      + (tr.nodes_walked ? ` · 노드 ${tr.nodes_walked}개 탐색` : ""));
    if ((tr.upstream || []).length) add("upstream 후보", names(tr.upstream));
    if ((tr.downstream || []).length) add("downstream 후보", names(tr.downstream));
    if ((tr.undirected || []).length) add("방향 미상 후보", names(tr.undirected));
    if (tr.status === "FAILED") {
      add("추적 실패 사유", tr.reason || (tr.budget_exhausted
        ? "탐색 한도 초과 — 배관망이 너무 크게 연결돼 있습니다"
        : "이 심볼에서 도달 가능한 커넥터·기기가 없습니다"));
      if ((tr.dead_ends || []).length) {
        add("끊긴 지점", `${tr.dead_ends.length}곳 — 도면에 붉은 X 로 표시했습니다 `
          + `(${tr.dead_ends.slice(0, 3).map(p => `${Math.round(p[0])},${Math.round(p[1])}`)
            .join(" · ")}${tr.dead_ends.length > 3 ? " …" : ""})`);
      }
    }
    add("Description", "이번 회차에서는 문장을 만들지 않습니다 (추적 결과만 기록)");
  }

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
      `<dt>${k}</dt><dd>${escape(String(v))}</dd>`).join("") + "</dl>"
    + candidatePicker(row);
  bindCandidatePicker(row);
}

/* The phrases the drawing prints along this instrument's pipe, nearest first.
 * Clicking one writes it into the Description between the system name and the
 * variable - the place the client's own lines put it - so the reviewer picks
 * rather than types. */
function candidatePicker(row) {
  const e = row.evidence || {};
  const cands = e.candidates || [];
  if (!cands.length && !row.values.description) return "";
  const head = row.values.description || "";
  const rows = cands.map((c, i) => `
    <li><button class="cand" data-i="${i}">
      <span class="cand-kind">${escape(c.kind)}</span>
      <span class="cand-text">${escape(c.text)}</span>
      <span class="muted">${Math.round(c.distance)}pt ${escape(c.direction)}</span>
    </button></li>`).join("");
  return `<div class="cands">
      <h4>후보 텍스트 <span class="muted">— 배관을 따라 수집, 가까운 순</span></h4>
      ${cands.length ? `<ol>${rows}</ol>`
        : `<p class="muted">이 계기가 붙은 배관에 텍스트가 없습니다 — 직접 입력하세요</p>`}
      <div class="cand-actions">
        <input id="cand-input" type="text" value="${escape(head)}"
               placeholder="Description 직접 입력">
        <button id="cand-save" class="ghost">이 행에 적용</button>
        <button id="cand-bulk" class="ghost"
                title="같은 도면·같은 Type 의 모든 행에 적용">일괄 적용</button>
      </div>
    </div>`;
}

function bindCandidatePicker(row) {
  const input = document.querySelector("#cand-input");
  if (!input) return;
  document.querySelectorAll("button.cand").forEach(b => {
    b.onclick = () => {
      const c = (row.evidence.candidates || [])[+b.dataset.i];
      if (!c) return;
      // Insert where the client puts it: after the system name, before the
      // variable word the ISA table supplied.
      const e = row.evidence || {};
      const varWords = (e.description_sources || [])
        .filter(x => x.startsWith("VARIABLE"))
        .map(x => x.split("→").pop().trim())[0] || "";
      // Insert where the client puts the subject: before the variable word,
      // which is not always last - an instrument ordinal can follow it
      // (`... LEVEL A`), so split on the variable rather than on the end.
      const base = (row.values.description || "").trim();
      const at = varWords ? base.lastIndexOf(varWords) : -1;
      input.value = at >= 0
        ? `${base.slice(0, at).trim()} ${c.text} ${base.slice(at).trim()}`
        : `${base} ${c.text}`.trim();
      input.focus();
    };
  });
  document.querySelector("#cand-save").onclick =
    () => setDescription(row, input.value.trim());
  document.querySelector("#cand-bulk").onclick =
    () => setDescription(row, input.value.trim(), { bulk: true });
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
/* The span between two line breakers.  The wording was corrected: it used to read
 * "SCT 배관 제외", which named our own company as the supplier and said the item
 * was out of the list.  A reviewer confirmed the opposite on p20's
 * D00P-11LAB00-M05-0001 - the pipe and the equipment inside the span are the
 * supplier's scope, and the item stays in the list.  The engine's rule name and
 * its behaviour are untouched; `config supplier_interface_span` holds the
 * project's wording, and the server sends it with the result. */
let SUPPLIER_SPAN_LABEL = "공급자 인터페이스 구간 — 배관 및 기기 공급자 범위";

const SCOPE = [
  ["INCLUDED", "포함", "#0a84ff", "우리 공급 범위 — 리스트에 나옴"],
  ["VENDOR_EXCLUDED", "벤더 제외", "#ff9f0a", "기기에 벤더 마크 → 리스트에서 제외"],
  ["SCT", "공급자 인터페이스 구간", "#bf5af2",
   "브레이커 구간 안 — 배관 및 기기 공급자 범위. 행은 리스트에 남고 Description 만 생략"],
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
  drawTrace(ov, scale);
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

/* The selected row's pipe, under the boxes so it never hides one.
 *
 * Four layers, each toggleable, because they answer different questions:
 *
 *   배관 라인   every run the walk reached - the line this instrument hangs off,
 *               which is the thing a reviewer wants lit up on the sheet
 *   upstream    the runs leading to a terminal the drawing printed `FROM`
 *   downstream  the same for `TO`.  Direction is the drawing's own preposition,
 *               never inferred from geometry
 *   끊긴 지점   where the run stopped with nothing further drawn
 *
 * On this document most traces fail, and that last layer is the useful one: it
 * puts the reviewer's eye exactly where the connectivity ran out, so they can see
 * on the drawing whether the pipe really ends there.  Nothing here writes a
 * sentence - that is still not this round's job. */
const TRACE_COLOUR = { pipe: "#5ac8fa", up: "#30d158", down: "#ffd60a",
                       other: "#8e8e93", break: "#ff375f" };

function drawTrace(ov, scale) {
  const row = S.rows.find(r => r.key === S.sel);
  const tr = row && row.evidence && row.evidence.trace;
  if (!tr || !S.showTrace) return;
  const NS = "http://www.w3.org/2000/svg";
  const on = (layer) => !S.trOff.has(layer);
  const line = (run, colour, cls) => {
    const l = document.createElementNS(NS, "line");
    l.setAttribute("x1", run[0] * scale); l.setAttribute("y1", run[1] * scale);
    l.setAttribute("x2", run[2] * scale); l.setAttribute("y2", run[3] * scale);
    l.setAttribute("class", cls);
    l.setAttribute("stroke", colour);
    ov.appendChild(l);
  };

  // 1. the pipe this row is attached to, plus the contact runs, so a failed
  //    trace still shows where the symbol meets the drawing.
  if (on("pipe")) {
    for (const run of tr.contact || []) line(run, TRACE_COLOUR.pipe, "tracecontact");
    for (const run of tr.path || []) line(run, TRACE_COLOUR.pipe, "tracepath");
  }

  // 2. the paths to each terminal, per direction.
  const dirs = [["upstream", "up"], ["downstream", "down"], ["undirected", "other"]];
  for (const [dir, layer] of dirs) {
    const colour = TRACE_COLOUR[layer];
    if (layer !== "other" && !on(layer)) continue;
    for (const t of tr[dir] || []) {
      for (const run of t.path || []) line(run, colour, "tracedir");
      if (!t.rect || t.rect.length !== 4) continue;
      const r = document.createElementNS(NS, "rect");
      r.setAttribute("x", t.rect[0] * scale);
      r.setAttribute("y", t.rect[1] * scale);
      r.setAttribute("width", Math.max(4, (t.rect[2] - t.rect[0]) * scale));
      r.setAttribute("height", Math.max(4, (t.rect[3] - t.rect[1]) * scale));
      r.setAttribute("class", "terminal");
      r.setAttribute("stroke", colour);
      ov.appendChild(r);
    }
  }

  // 3. where it broke off.  Marked with a cross rather than a box: it is a point
  //    on the drawing, not a thing that was found.
  if (on("break") && tr.status === "FAILED") {
    for (const [x, y] of tr.dead_ends || []) {
      for (const [dx, dy] of [[1, 1], [1, -1]]) {
        line([x - 4 * dx, y - 4 * dy, x + 4 * dx, y + 4 * dy],
             TRACE_COLOUR.break, "tracebreak");
      }
    }
  }
}

$req("#ovl-bytab").addEventListener("change", ev => {
  S.byTab = ev.target.checked;
  drawOverlay();
});
document.querySelectorAll(".ovl-tr").forEach(c => {
  c.addEventListener("change", () => {
    if (c.checked) S.trOff.delete(c.value); else S.trOff.add(c.value);
    // The pipe layer is the trace itself; switching it off with the others hides
    // the lot, which is what the old single checkbox did.
    S.showTrace = document.querySelectorAll(".ovl-tr:checked").length > 0;
    drawOverlay();
  });
});
$req("#stage").addEventListener("click", ev => {
  if (S.picking) {
    const p = sheetPoint(ev);
    endPick();
    if (p) createRow(p);
    return;
  }
  // Clicking the sheet itself, away from any box, clears the selection.
  if (ev.target.tagName.toLowerCase() !== "rect") deselect();
});

/* Screen point -> PDF point.  The sheet is rendered at a zoom the server chose
 * and then CSS-scaled, so both factors have to come back out. */
function sheetPoint(ev) {
  const img = $("#sheet");
  if (!img.naturalWidth || !S.page) return null;
  const box = img.getBoundingClientRect();
  const fx = (ev.clientX - box.left) / box.width;
  const fy = (ev.clientY - box.top) / box.height;
  if (fx < 0 || fx > 1 || fy < 0 || fy > 1) return null;
  return [fx * S.page.width, fy * S.page.height];
}
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && !ev.target.isContentEditable) deselect();
});

/* ---------------- filter, gate, export ---------------- */
$req("#filter").addEventListener("input", ev => { S.filter = ev.target.value; renderGrid(); });
$req("#origin-filter").addEventListener("change", ev => {
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

$req("#gate-check").addEventListener("change", async ev => {
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

$req("#excel").addEventListener("click", () => {
  if (!S.revision) return;
  location.href = `/revisions/${S.revision}/excel`;
});

/* ---------------- row add / copy / delete ---------------- */
async function refreshRows(selectKey) {
  await loadRows();
  if (selectKey) select(selectKey, true);
}

/* A row the engine missed is only useful to a later rule pass if we know where
 * on the drawing it should have been, so adding one asks for the place first and
 * the server captures what is drawn there.  The pick can be skipped - the row is
 * still created, and the record then simply has no geometry. */
$req("#row-add").addEventListener("click", () => startPick());

function startPick() {
  S.picking = true;
  $("#stage").classList.add("picking");
  $("#pick-note").classList.remove("hidden");
}

function endPick() {
  S.picking = false;
  $("#stage").classList.remove("picking");
  $("#pick-note").classList.add("hidden");
}

$req("#pick-cancel").addEventListener("click", async ev => {
  ev.stopPropagation();
  endPick();
  await createRow(null);
});

async function createRow(point) {
  const src = S.rows.find(r => r.key === S.sel);
  const body = {
    page_no: point ? S.page.page_no
      : (src ? src.page_no : (S.page ? S.page.page_no : 0)),
    tab: src ? src.tab : (S.tab === "ALL" || S.tab === "REVIEW" ? "FIELD" : S.tab),
    origin: src ? src.origin : "",
    drawing_no: point ? (S.page.drawing_no || "")
      : (src ? src.drawing_no : (S.page ? S.page.drawing_no : "")),
    values: {},
    point: point || undefined,
  };
  const r = await fetch(`/jobs/${S.job.id}/rows`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) { alert("행 추가 실패"); return; }
  const out = await r.json();
  if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
  if (point) {
    const g = out.geometry || {};
    $("#pick-note").textContent =
      `기록: (${Math.round(point[0])}, ${Math.round(point[1])}) 주변 도형 `
      + `${g.path_count || 0}개 · 선분 ${g.segment_count || 0}개`
      + (g.nearest_text ? ` · 인접 텍스트 "${g.nearest_text}"` : "");
  }
  await refreshRows(out.key);
  updateBadge();
}

$req("#row-copy").addEventListener("click", async () => {
  if (!S.sel) { alert("복사할 행을 먼저 선택하세요."); return; }
  const r = await fetch(`/jobs/${S.job.id}/rows/${S.sel}/copy`, { method: "POST" });
  if (!r.ok) { alert("복사 실패"); return; }
  await refreshRows((await r.json()).key);
});

$req("#row-delete").addEventListener("click", async () => {
  if (!S.sel) { alert("삭제할 행을 먼저 선택하세요."); return; }
  const key = S.sel;
  // Optional, and optional on purpose: a reason left blank still records the
  // rule and the measurements that produced the row.
  const reason = window.prompt("삭제 사유 (선택 — 비워도 됩니다)", "") || "";
  const r = await fetch(
    `/jobs/${S.job.id}/rows/${key}?reason=${encodeURIComponent(reason)}`,
    { method: "DELETE" });
  if (!r.ok) { alert("삭제 실패"); return; }
  const out = await r.json();
  if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
  // A detection is struck out, not dropped: the next analysis would find it
  // again, and the reviewer's decision has to outlive that.
  S.sel = out.dropped ? null : key;
  await refreshRows(S.sel);
});

$req("#reanalyse").addEventListener("click", async () => {
  await fetch(`/jobs/${S.job.id}/reanalyse`, { method: "POST" });
  $("#main").classList.add("hidden");
  watch(S.job.id);
});
