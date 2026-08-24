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
//
// The top grade says where the words came from, not that they are the client's
// words, and the label says so.  Against the client's own list, 455 of these rows
// have a counterpart: 27 match it token for token and 338 (74.3%) name the same
// piece of equipment.  Nothing in the run separates the two - agreement sits
// between 63% and 80% in every band of distance, runner-up margin, candidate
// count, direction and noun source - so there is no line to draw that would make
// a smaller, surer grade, and inventing a threshold would be a guess.  Saying the
// number is what can honestly be done.
// 등급을 색으로만 구분하지 않기 위한 글리프.  흑백으로 인쇄해도, 색을 구분하지
// 못해도 배지의 모양과 글자가 등급을 말한다 - 색은 셋째 단서다.
const GRADE_MARK = {
  CONFIRMED: "●", LOW: "◇", PARTIAL: "◐", NONE: "○", SKIP: "×",
  USER_ENTERED: "✎",
};
const GRADES = [
  ["CONFIRMED", "도면 근거 있음",
   "이름·계통·변수를 모두 도면에서 읽었습니다 — 발주처 표기와 같다는 뜻은 아닙니다 "
   + "(대조 가능한 455행 중 주어 일치 74.3%, 문장 완전일치 27행)"],
  // 모델이 만든 것이 아니다 - 배관이 향하는 곳의 표기(오프페이지 커넥터)에서
  // 골랐다는 뜻이다.  이름이 그 사실을 말하게 한다.
  ["LOW", "도착지 표기에서 유추", "배관이 향하는 곳의 표기에서 골랐습니다 — "
   + "기기 이름이 아니므로 확인 필요"],
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
  job: null, tab: "ALL", rows: [], pages: [], page: null, zoom: null,
  sel: null, sort: { col: "page_no", dir: 1 }, filter: "", counts: {},
  originFilter: "", originCounts: {}, showOrigin: false,
  ovOff: new Set(), byTab: false, pending: null, drawings: [],
  // Per-column value filters: {column: [value, ...]}.  Absent means "no filter",
  // which is not the same as "every value ticked" - see setColumnFilter().
  colFilters: {},
  picking: false, feedback: 0, reports: 0, showTrace: true, gradeFilter: "",
  reasonFilter: "",
  // The review filters.  They stack: axis narrows to a decision, code to one
  // reason inside it, and the tab / drawing / grade are the axes the grid
  // already had.  All of them ride in the URL so a reload or a shared link
  // lands on the same view.
  axis: "", code: "", drawing: "", onlyReview: false, review: null,
  // 프로젝트와 리비전.  `rev` 는 이 분석의 대조 결과 요약이다.
  project: "", projects: [], rev: null, onlyChanged: false, setupDone: false,
  deletedRows: [], revByKey: {}, loading: false,
  pageCount: null, sheetTargets: null,
  // Which trace layers the reviewer switched off: pipe | up | down | break.
  trOff: new Set(),
};

/* ---------------- upload ----------------
 *
 * 왼쪽 단이 정해지기 전에는 PDF 를 받지 않는다.  프로젝트와 비교 대상은 분석이
 * 시작된 뒤에는 고칠 수 없는 값이고, 안 고른 채 놓으면 그 분석은 어느 프로젝트
 * 에도 속하지 않은 채로 끝나기 때문이다.  "프로젝트 없이 한 번만"도 하나의
 * 선택지로 두어, 예전 흐름이 사라지지 않으면서도 고르는 행위는 남게 했다. */
const drop = $("#drop");
const dropZone = $req("#drop-zone");
["dragenter", "dragover"].forEach(e => dropZone.addEventListener(e, ev => {
  ev.preventDefault();
  if (S.setupDone) dropZone.classList.add("over");
}));
["dragleave", "drop"].forEach(e => dropZone.addEventListener(e, ev => {
  ev.preventDefault(); dropZone.classList.remove("over");
}));
dropZone.addEventListener("drop", ev => {
  if (!S.setupDone) return;
  const f = ev.dataTransfer.files[0];
  if (f) upload(f);
});
$("#file").addEventListener("change", ev => {
  if (ev.target.files[0]) upload(ev.target.files[0]);
});

/* 왼쪽 단이 정해졌는가.  정해질 때까지 오른쪽은 잠겨 있고, 왜 잠겼는지를 쓴다. */
function setSetupDone(done, why) {
  S.setupDone = !!done;
  dropZone.classList.toggle("disabled", !S.setupDone);
  $("#file").disabled = !S.setupDone;
  const lock = $("#drop-lock");
  lock.textContent = why || "";
  lock.classList.toggle("hidden", S.setupDone);
}

async function upload(file) {
  const fd = new FormData();
  fd.append("pdf", file);
  // 프로젝트를 고른 경우에만 실린다.  안 고르면 예전과 같은 한 번짜리 분석.
  if (S.project) {
    fd.append("project", S.project);
    fd.append("compared_with", $("#rev-base").value || "");
  }
  const r = await fetch("/jobs", { method: "POST", body: fd });
  if (!r.ok) { alert((await r.json()).detail || "업로드 실패"); return; }
  const job = await r.json();
  watch(job.job_id, job.page_count);
}

/* ---------------- projects and revisions ----------------
 *
 * 투입 순서는 프로젝트 -> 리비전 -> PDF 다.  Rev.A 는 이름을 새로 적어 만들고,
 * 그 뒤로는 목록에서 고른다.  비교 대상 기본값은 직전 리비전이고, Rev.C 부터는
 * 그 이전 아무 리비전이나 고를 수 있다.  직전이 없으면 비교 없이 진행하고
 * 그 사실을 화면에 적는다. */
async function loadProjects(select) {
  const list = await (await fetch("/projects")).json();
  S.projects = list;
  const pick = $("#proj-pick");
  // 첫 항목은 고르지 않은 상태다.  "프로젝트 없이 한 번만"은 그 자체로 하나의
  // 선택지이지 기본값이 아니다 - 기본값이면 아무것도 안 고른 사람이 프로젝트
  // 밖에서 분석을 끝내게 된다.
  pick.innerHTML = '<option value="__unset__">(고르세요)</option>'
    + '<option value="">프로젝트 없이 한 번만 분석</option>'
    + list.map(p => `<option value="${escape(p.name)}">${escape(p.name)}`
      + ` — 다음 ${escape(nextRev(p))}</option>`).join("");
  pick.value = select != null ? select : "__unset__";
  chooseProject(pick.value);
}

function nextRev(p) {
  const n = (p.revisions || []).length;
  return "Rev." + "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[Math.min(n, 25)];
}

function chooseProject(name) {
  const unset = name === "__unset__";
  S.project = unset ? "" : (name || "");
  const p = S.projects.find(x => x.name === S.project);
  const box = $("#proj-rev");
  const base = $("#rev-base");
  if (unset) {
    box.classList.add("hidden");
    $("#rev-note").textContent = "";
    $("#proj-msg").textContent = "";
    setSetupDone(false, "왼쪽에서 프로젝트를 먼저 고르세요.");
    return;
  }
  if (!p) {                                 // 프로젝트 없이 한 번만
    box.classList.add("hidden");
    $("#rev-note").textContent = "";
    $("#proj-msg").textContent = "프로젝트 없이 한 번만 분석합니다 — 개정 대조 없음";
    setSetupDone(true);
    return;
  }
  const revs = (p.revisions || []).map(r => r.revision);
  const next = nextRev(p);
  // 비교 상자는 비교할 것이 있을 때만 나온다.  Rev.A 에는 대상이 없고, 없는
  // 것을 고르라고 내밀면 고를 수 있는 것처럼 읽힌다.
  box.classList.toggle("hidden", revs.length === 0);
  base.innerHTML = revs.length
    ? revs.slice().reverse().map(r => `<option value="${escape(r)}">${escape(r)}</option>`).join("")
    : "";
  base.disabled = revs.length < 2;          // Rev.B 는 선택지가 하나뿐이다
  base.value = revs.length ? revs[revs.length - 1] : "";
  $("#rev-note").textContent = revs.length === 0
    ? "이 프로젝트의 첫 리비전입니다 — 비교하지 않고 진행합니다"
    : revs.length === 1
      ? "비교 대상은 Rev.A 하나뿐이라 바꿀 수 없습니다"
      : "기본값은 직전 리비전이고, 그 이전 것으로 바꿀 수 있습니다";
  setSetupDone(true);
  revSummary(p, next);
}

/* 선택 결과 한 줄.  고르기 전에도, 고른 뒤에도 늘 보인다. */
function revSummary(p, next) {
  const base = $("#rev-base");
  const target = base.value;
  $("#proj-msg").textContent = target
    ? `이 PDF 는 ${p.name} 의 ${next} 가 됩니다 — 비교 대상 ${target}`
    : `이 PDF 는 ${p.name} 의 ${next} 가 됩니다 (비교 대상 없음)`;
}
$req("#rev-base").addEventListener("change", () => {
  const p = S.projects.find(x => x.name === S.project);
  if (p) revSummary(p, nextRev(p));
});

$req("#proj-pick").addEventListener("change", ev => chooseProject(ev.target.value));
$req("#proj-new-btn").addEventListener("click", () => {
  $("#proj-new").classList.remove("hidden");
  $("#proj-name").focus();
});
$req("#proj-cancel").addEventListener("click", () => {
  $("#proj-new").classList.add("hidden");
  $("#proj-msg").textContent = "";
});
$req("#proj-save").addEventListener("click", async () => {
  const name = $("#proj-name").value.trim();
  if (!name) { $("#proj-msg").textContent = "이름을 입력하세요."; return; }
  const fd = new FormData();
  fd.append("name", name);
  const r = await fetch("/projects", { method: "POST", body: fd });
  const out = await r.json();
  if (!r.ok) {
    // 같은 이름이 있으면 덮어쓰지 않는다 - 서버가 거절하고 그 사유를 적는다.
    $("#proj-msg").textContent = out.detail || "프로젝트를 만들지 못했습니다.";
    return;
  }
  $("#proj-new").classList.add("hidden");
  $("#proj-name").value = "";
  await loadProjects(out.name);           // 만든 프로젝트가 곧 선택이다
});

/* 위생 통계는 한 문장으로 이어 붙이면 아홉 개 숫자가 한 줄이 된다.  대부분의
 * 날에는 그 아홉 개가 전부 0 이고, 0 을 아홉 번 읽는 것은 읽는 일이 아니다.
 * 그래서 0 이 아닌 항목만 펼치고, 전부 0 이면 "이상 없음" 한 줄로 접는다.
 * 접힌 줄을 열면 원문이 그대로 나온다 - 숨기는 것이 아니라 접는 것이다. */
function auditProblems(lines) {
  const out = [];
  for (const part of lines.join(" · ").split(" · ")) {
    const t = part.trim();
    if (!t) continue;
    const m = /([0-9]+(?:\.[0-9]+)?)\s*(행|개|칸|MB)?$/.exec(t);
    if (m && parseFloat(m[1]) === 0) continue;      // 0 인 항목은 접는다
    out.push(t);
  }
  return out;
}

async function showAudit() {
  try {
    const a = await (await fetch("/audit")).json();
    const box = $("#audit-line");
    // "산출 대상 N행 / job M개" 는 규모이지 이상이 아니다.
    const bad = auditProblems(a.lines).filter(t => !/^산출 대상|^job /.test(t));
    const full = `<div class="audit-full">`
      + a.lines.map(l => `<div>${escape(l)}</div>`).join("") + `</div>`;
    box.innerHTML = bad.length
      ? `<details class="audit" open><summary>데이터 위생 — 확인할 항목 `
        + `${bad.length}건</summary>${full}</details>`
      : `<details class="audit"><summary>데이터 위생 — 이상 없음`
        + `</summary>${full}</details>`;
  } catch (e) { /* 감사는 부가 정보다 - 실패해도 화면을 막지 않는다 */ }
}
loadProjects();
showAudit();

/* 이전 분석 한 줄: 상태 · 장수 · 걸린 시간.  전부 저장된 값이다. */
function jobLine(j) {
  const bits = [j.status === "done" ? "완료" : j.status === "failed" ? "실패" : j.status];
  if (j.page_count) bits.push(`${j.page_count}장`);
  if (j.elapsed_s) bits.push(minsec(j.elapsed_s));
  return bits.join(" · ");
}

async function listJobs() {
  const jobs = await (await fetch("/jobs")).json();
  $("#joblist").innerHTML = jobs.length
    ? "<p class='muted small'>이전 분석</p>" + jobs.map(j =>
        `<a href="#${j.id}">${escape(j.pdf_name)}`
        + `<span class="muted small">${escape(jobLine(j))}</span></a>`).join("")
    : "";
}
listJobs();

/* ---------------- progress ----------------
 *
 * 이 화면이 말하는 세 값은 전부 문서에서 나온 것이다.  쪽수는 업로드 직후 서버가
 * PDF 에서 세고, 분석 장수의 분모는 파이프라인이 대상 도면을 확정한 순간 한 번
 * 실려 오고, 소요 시간은 시작·종료 시각의 차이다.  남은 시간은 적지 않는다 -
 * 이 문서에서 단계별 소요가 60배까지 차이나므로(도면 한 장 0.3초 ↔ 사전 측정
 * 185초) 어떤 외삽도 추측이 된다. */

// 파이프라인이 보내는 단계 이름을 화면 말로 옮긴 것.  모르는 값은 그대로 쓴다 -
// 없는 뜻을 지어내지 않는다.
const STAGE_KO = {
  "queued": "차례를 기다리는 중",
  "starting": "시작하는 중",
  "opening the document": "문서를 여는 중",
  "measuring the sheet": "도면 치수를 재는 중 — 이 단계가 가장 깁니다",
  "reading title blocks": "타이틀블록을 읽는 중",
  "measuring rules off the legend sheets": "범례에서 규칙을 재는 중",
  "deriving unit multipliers from legend page 5": "유닛 승수를 유도하는 중",
  "valve bodies and actuators": "밸브 몸체·액추에이터를 찾는 중",
  "building overlays": "도면 표시를 만드는 중",
  "tracing pipe connectivity": "배관 연결을 따라가는 중",
  "finding equipment": "기기를 찾는 중",
  "assembling descriptions": "Description 을 조립하는 중",
  "done": "완료",
};

function stageWords(msg) {
  if (!msg) return "";
  if (STAGE_KO[msg]) return STAGE_KO[msg];
  if (/^page \d+ of \d+$/.test(msg)) return "도면을 읽는 중";
  if (/^\d+ sheets to read$/.test(msg)) return "읽을 도면을 세는 중";
  return msg;
}

function minsec(sec) {
  const n = Math.round(sec || 0);
  return n >= 60 ? `${Math.floor(n / 60)}분 ${n % 60}초` : `${n}초`;
}

/* 넣은 쪽수와 분석 대상 장수는 **둘 다** 화면에 남는다.
 *
 * 분석 대상은 업로드 시점에 알 수 없다: 어느 쪽이 범례이고 어느 쪽이 도면인지는
 * 타이틀블록을 읽어야 정해지고, 그 단계는 사전 측정(185초) 뒤에 온다.  그래서
 * 처음에는 쪽수만 적고 "아직 정해지지 않았다"고 쓴 다음, 정해지는 순간 같은
 * 자리에 "58장 중 분석 대상 52장"으로 바뀐다.  추정하지 않는다. */
function showPages(n, targets) {
  const line = $("#prog-pages");
  if (n == null && targets == null) return;
  if (n != null) S.pageCount = n;
  if (targets != null) S.sheetTargets = targets;
  const p = S.pageCount;
  if (!p) { line.textContent = "이 PDF 의 쪽수를 읽지 못했습니다."; return; }
  line.textContent = S.sheetTargets
    ? `${p}장 중 분석 대상 ${S.sheetTargets}장`
    : `${p}장을 읽었습니다 — 분석 대상은 도면을 읽어 봐야 정해집니다.`;
}

function showSheets(done, total) {
  const line = $("#prog-sheets");
  if (!total) { line.textContent = ""; return; }
  line.textContent = `도면 ${total}장 중 ${done}장 완료`;
}

/* 걷지 않는 쪽을 쪽 번호까지 적는다.  묶어서 숨기지 않는다 - 58장을 건넨
 * 사람에게 52 만 보이면 나머지 여섯 장이 어디로 갔는지 알 길이 없다. */
function showSkipped(plan) {
  const box = $("#prog-skip");
  if (!box) return;
  if (!plan || !plan.skipped || !plan.skipped.length) {
    box.classList.add("hidden"); return;
  }
  const n = plan.skipped.reduce((a, g) => a + g.pages.length, 0);
  const unknown = (plan.unknown || []).length;
  box.querySelector("summary").textContent =
    `분석하지 않는 ${n}장 — 사유 보기` + (unknown ? ` (사유 미상 ${unknown}장 포함)` : "");
  $("#prog-skip-body").innerHTML = plan.skipped.map(g =>
    `<div class="skip-row"><span class="skip-why">${escape(g.why)}</span>`
    + `<span class="skip-n">${g.pages.length}장</span>`
    + `<span class="muted small">p${g.pages.join(" · p")}</span></div>`).join("");
  box.classList.remove("hidden");
}

function watch(jobId, pageCount) {
  drop.classList.add("hidden");
  $("#progress").classList.remove("hidden");
  S.pageCount = null; S.sheetTargets = null;
  $("#prog-skip").classList.add("hidden");
  // A previous failure leaves its hint, buttons and job list on this panel; a new
  // analysis has to start from a clean one or the reviewer reads last time's exit
  // routes over this run's progress bar.
  $("#prog-title").textContent = "분석 중";
  $("#prog-sheets").textContent = "";
  $("#prog-pages").textContent = "";
  showPages(pageCount);
  ["#prog-hint", "#prog-actions", "#prog-jobs"].forEach(
    sel => $(sel).classList.add("hidden"));
  const src = new EventSource(`/jobs/${jobId}/events`);
  src.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    $("#bar-fill").style.width = `${Math.round(d.progress * 100)}%`;
    $("#prog-msg").textContent = stageWords(d.message);
    if (d.page_count != null) showPages(d.page_count, null);
    if (d.sheets_total) showPages(null, d.sheets_total);
    if (d.sheets_total != null) showSheets(d.sheets_done || 0, d.sheets_total);
    if (d.sheet_plan) showSkipped(d.sheet_plan);
    if (d.status === "done") { src.close(); open(jobId); }
    if (d.status === "failed") {
      src.close();
      showFailure(d.message, d);
    }
  };
}

/* A failed analysis used to leave the reviewer with nothing: #drop and #main are
 * both hidden while #progress is up, so the screen had a title, a numpy exception
 * and no control of any kind.  The only way out was editing the URL.
 *
 * `message` is now a sentence the server built from what the file contains - the
 * traceback is in the log and the diagnostic export, not here. */
async function showFailure(message, d) {
  $("#bar-fill").style.width = "0%";
  $("#prog-title").textContent = "분석 실패";
  $("#prog-msg").textContent = message || "사유를 특정하지 못했습니다.";
  // 어디까지 갔는지.  실패한 분석에서 사람이 확인할 수 있는 것은 이것뿐이다.
  const far = $("#prog-sheets");
  if (d && d.sheets_total) {
    far.textContent = `도면 ${d.sheets_total}장 중 ${d.sheets_done || 0}장까지 읽고 멈췄습니다`
      + (d.elapsed_s ? ` (${minsec(d.elapsed_s)})` : "");
  } else if (d) {
    far.textContent = "도면을 한 장도 읽기 전에 멈췄습니다"
      + (d.elapsed_s ? ` (${minsec(d.elapsed_s)})` : "");
  }
  const hint = $("#prog-hint");
  hint.textContent = "다른 PDF 로 다시 시도하거나, 아래 이전 분석을 여세요.";
  hint.classList.remove("hidden");
  $("#prog-actions").classList.remove("hidden");
  // The previous analyses, listed here rather than only on the first screen, so
  // getting back to work does not need a second navigation.
  const box = $("#prog-jobs");
  try {
    const jobs = await (await fetch("/jobs")).json();
    const others = jobs.filter(j => j.status === "done");
    box.innerHTML = others.length
      ? "<p class='muted'>이전 분석</p>" + others.map(j =>
          `<a href="#${j.id}">${escape(j.pdf_name)} `
          + `<span class="muted">${escape(j.status)}</span></a>`).join("")
      : "<p class='muted'>이전 분석이 없습니다.</p>";
    box.classList.remove("hidden");
  } catch (e) {
    box.classList.add("hidden");
  }
}

function toFirstScreen() {
  $("#progress").classList.add("hidden");
  $("#prog-hint").classList.add("hidden");
  $("#prog-actions").classList.add("hidden");
  $("#prog-jobs").classList.add("hidden");
  $("#main").classList.add("hidden");
  $("#drop").classList.remove("hidden");
  $("#prog-title").textContent = "분석 중";
  $("#prog-msg").textContent = "";
  $("#prog-sheets").textContent = "";
  $("#prog-pages").textContent = "";
  $("#prog-skip").classList.add("hidden");
  S.pageCount = null; S.sheetTargets = null;
  if (location.hash) history.replaceState(null, "", location.pathname);
  listJobs();
}
$req("#prog-home").addEventListener("click", toFirstScreen);

function hashParts() {
  const raw = location.hash.slice(1);
  const i = raw.indexOf("?");
  return i < 0 ? [raw, ""] : [raw.slice(0, i), raw.slice(i + 1)];
}
window.addEventListener("hashchange", () => {
  const [id, query] = hashParts();
  if (id && (!S.job || S.job.id !== id)) { open(id); return; }
  // Same job, different filters: a shared link has to apply its view without a
  // reload, and the state has to follow the URL rather than the other way round -
  // otherwise navigating back to the bare job id leaves the old filters in place
  // and the next click toggles them off instead of on.
  S.tab = "ALL"; S.axis = ""; S.code = ""; S.drawing = ""; S.gradeFilter = "";
  S.reasonFilter = ""; S.originFilter = ""; S.filter = ""; S.onlyReview = false;
  // Cleared here as well, and not only inside `readUrl`: navigating back to the
  // bare job id has to leave *nothing* standing, which is the defect that was
  // fixed once already for the other filters.
  S.colFilters = {};
  closeColumnMenu();
  readUrl(query);
  const only = $("#only-review"); if (only) only.checked = S.onlyReview;
  const box = $("#filter"); if (box) box.value = S.filter;
  buildTabs(); renderReviewPanel(); renderGrid();
});
if (location.hash.length > 1) open(hashParts()[0]);

/* ---------------- load ---------------- */
async function open(jobId) {
  const job = await (await fetch(`/jobs/${jobId}`)).json();
  if (job.status !== "done") { watch(jobId, job.page_count); return; }
  S.loading = true;
  S.job = job;
  S.zoom = null;                  // a fresh analysis starts fitted, not zoomed
  // 개정 스위치는 그 분석의 것이다.  다른 분석으로 넘어갈 때 남아 있으면
  // 바뀐 행이 없는 리비전에서 화면이 텅 빈 채로 열린다.
  S.onlyChanged = false;
  S.deletedRows = [];
  S.revByKey = {};
  const oc = $("#only-changed"); if (oc) oc.checked = false;

  readUrl(hashParts()[1]);
  if (location.hash.slice(1).split("?")[0] !== jobId) location.hash = jobId;
  drop.classList.add("hidden");
  $("#progress").classList.add("hidden");
  $("#main").classList.remove("hidden");
  $("#job-name").textContent = job.pdf_name;
  // 몇 장을 얼마나 걸려 읽었는지.  둘 다 잰 값이고, 없으면 그 칸은 비운다.
  const meta = [];
  if (job.page_count && job.sheets_total) {
    meta.push(`${job.page_count}장 중 분석 ${job.sheets_total}장`);
  } else if (job.page_count) {
    meta.push(`${job.page_count}장`);
  }
  if (job.elapsed_s) meta.push(minsec(job.elapsed_s));
  const plan = job.sheet_plan;
  if (plan && plan.skipped && plan.skipped.length) {
    const n = plan.skipped.reduce((a, g) => a + g.pages.length, 0);
    meta.push(`제외 ${n}장`);
    $("#job-meta").title = plan.skipped
      .map(g => `${g.why} ${g.pages.length}장 (p${g.pages.join(", p")})`).join("\n");
  } else {
    $("#job-meta").title = "";
  }
  $("#job-meta").textContent = meta.join(" · ");
  S.pages = await (await fetch(`/jobs/${jobId}/pages`)).json();
  await loadRevision();
  await loadRows();
  buildPageSelect();
  S.loading = false;
  updateEmptyNote();
  showPage(S.pages.find(p => (p.layers && Object.keys(p.layers).length)) || S.pages[0]);
}

/* 이 분석이 어느 리비전이고 무엇과 비교했는지.  머리에 "Rev.C vs Rev.A" 로
 * 적는다 - 결과만 보고 무엇과 비교했는지 알 수 없으면 안 된다. */
async function loadRevision() {
  try {
    S.rev = await (await fetch(`/jobs/${S.job.id}/revision`)).json();
  } catch (e) { S.rev = null; }
  const el = $("#rev-label");
  if (!S.rev || !S.rev.revision) { el.classList.add("hidden"); return; }
  const c = S.rev.counts || {};
  const bits = [];
  if (c.ADDED) bits.push(`추가 ${c.ADDED}`);
  if (c.MODIFIED) bits.push(`수정 ${c.MODIFIED}`);
  if (c.DELETED_CANDIDATE) bits.push(`삭제 후보 ${c.DELETED_CANDIDATE}`);
  if (c.DELETED) bits.push(`삭제 확정 ${c.DELETED}`);
  el.textContent = S.rev.label + (bits.length ? ` — ${bits.join(" · ")}` : "");
  el.classList.remove("hidden");
  // 비교 대상이 있는 리비전에서만 스위치를 보인다 - Rev.A 에는 고를 상태가 없다.
  const w = $("#only-changed-wrap");
  if (w) w.classList.toggle("hidden", !S.rev.compared_with);
  renderDeletedCandidates();
}

/* 삭제 후보 한 건의 근거.  좌표 · 반경 · 가장 가까웠던 후보까지 거리 셋이
 * 있어야 "도면에서 지워졌다" 와 "이번에 못 뽑았다" 를 사람이 가를 수 있다. */
function showDeletedEvidence(d) {
  // 근거 셋을 맨 위에 둔다.  패널이 232px 이라 아래로 밀리면 스크롤해야 보이고,
  // 정작 판단에 쓰는 값이 그 셋이다.
  const rows = [
    ["상태", d.confirmed ? "삭제 확정 — 산출물에 취소선으로 나갑니다"
      : "삭제 후보 — 확정 전에는 산출물에 나가지 않습니다"],
    ["직전 리비전 좌표", `(${d.anchor.join(", ")})`],
    ["매칭 반경", `${d.radius}pt — ${d.radius_source === "DRAWING_BUBBLE"
      ? "이 도면 버블 긴변" : d.radius_source}`],
    ["가장 가까웠던 같은 TYPE 후보",
     d.nearest_distance === null ? "그 도면에 같은 TYPE 이 하나도 없음"
       : `${d.nearest_distance}pt 떨어져 있었습니다`],
    ["안정 ID", `${d.id} · ${d.type || "TYPE 없음"} · ${d.drawing_no} (p${d.page_no})`],
    ["직전 Description", d.description || "(없음)"],
  ];
  $("#evidence").innerHTML =
    `<div class="ev-head"><h3>삭제 후보 — ${escape(d.id)}</h3></div>`
    + `<p class="muted">이번 분석에서 짝을 찾지 못했습니다. 도면에서 지워진 것인지,`
    + ` 이번에 못 뽑은 것인지는 기계가 가르지 못합니다 — 아래 근거를 보고`
    + ` 확정하세요.</p>`
    + "<dl>" + rows.map(([k, v]) =>
      `<dt>${escape(k)}</dt><dd>${escape(String(v))}</dd>`).join("") + "</dl>";
}

function renderDeletedCandidates() {
  // 삭제 후보는 그리드 행으로 서고 근거는 근거 패널이 보인다.  별도 패널을 두면
  // 같은 것을 두 번 그리면서 그리드 높이를 149px 까지 밀어낸다 - 실측하고 뺐다.
  const box = $("#del-cands");
  if (!box) return;
  box.classList.add("hidden");
  box.innerHTML = "";
  return;
  const list = ((S.rev || {}).deleted_candidates) || [];
  if (!list.length) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  box.classList.remove("hidden");
  box.innerHTML = `<h3>삭제 후보 ${list.filter(d => !d.confirmed).length}`
    + ` / 확정 ${list.filter(d => d.confirmed).length}</h3>`
    + `<p class="muted">직전 리비전에 있던 항목이 이번 분석에서 짝을 찾지 못했습니다.`
    + ` 도면에서 지워진 것인지, 이번에 못 뽑은 것인지는 사람이 확인해야 합니다.</p>`
    + list.map(d => `<div class="del-cand${d.confirmed ? " done" : ""}">`
      + `<b>${escape(d.id)}</b> <span class="muted">${escape(d.type || "")}`
      + ` · p${d.page_no || "?"} · ${escape(d.drawing_no || "")}</span>`
      + `<div class="muted">${escape(d.description || "(설명 없음)")}</div>`
      + `<div class="muted">근거 — Rev 좌표 (${d.anchor.join(", ")})`
      + ` · 매칭 반경 ${d.radius}pt (${escape(d.radius_source)})`
      + ` · 가장 가까웠던 후보 ${d.nearest_distance === null ? "없음"
          : d.nearest_distance + "pt"}</div>`
      + `<button data-id="${escape(d.id)}" data-on="${d.confirmed ? 0 : 1}">`
      + `${d.confirmed ? "확정 취소" : "삭제로 확정"}</button></div>`).join("");
  box.querySelectorAll("button").forEach(b => b.addEventListener("click", async () => {
    await fetch(`/jobs/${S.job.id}/deleted/${encodeURIComponent(b.dataset.id)}`
      + `/confirm?confirmed=${b.dataset.on === "1"}`, { method: "POST" });
    await loadRevision();
  }));
}

async function loadRows() {
  S.rows = await (await fetch(`/jobs/${S.job.id}/rows?tab=ALL`)).json();
  // ④ 행의 FROM/TO 확정 장부 - 근거 패널의 "FROM/TO 확정"·"확정 승계" 표시용.
  // 프로젝트가 없는 job 은 빈 객체가 온다.
  try {
    S.axisOv = await (await fetch(`/jobs/${S.job.id}/axis_overrides`)).json();
  } catch (e) { S.axisOv = {}; }
  // 오버레이가 행 상태를 키로 찾을 수 있게.  도면에는 추가·수정만 그린다 -
  // 삭제된 것은 이번 도면에 심볼이 없어 그릴 좌표가 없다.
  S.revByKey = {};
  for (const r of S.rows) {
    const st = (r.rev || {}).state;
    if (st === "ADDED" || st === "MODIFIED") S.revByKey[r.key] = st;
  }
  // 삭제 후보도 리스트에 세운다 - 세 상태가 한 화면에 보여야 한다.  도면에는
  // 그리지 않는다: 이번 리비전에 그 심볼이 없으므로 그릴 좌표가 없다.
  S.deletedRows = ((S.rev || {}).deleted_candidates || []).map(d => ({
    key: `del:${d.id}`, tab: d.tab || "FIELD", page_no: d.page_no || 0,
    drawing_no: d.drawing_no || "", origin: "", rect: [],
    values: { ...(d.values || {}), type: d.type || "",
              description: d.description || "" },
    ai: {}, user: {}, evidence: {}, needs_review: "", annotation: "",
    conflict: {}, deleted: true, added: false, removed: false,
    review_codes: [], review_state: {},
    rev: { id: d.id, state: d.confirmed ? "DELETED" : "DELETED_CANDIDATE" },
    delCand: d,
  }));
  S.counts = { ALL: S.rows.length, REVIEW: 0 };
  S.originCounts = {};
  for (const r of S.rows) {
    S.counts[r.tab] = (S.counts[r.tab] || 0) + 1;
    if (r.needs_review || r.deleted) S.counts.REVIEW++;
    S.originCounts[r.origin] = (S.originCounts[r.origin] || 0) + 1;
  }
  await buildScope();
  S.jobReview = await (await fetch(`/jobs/${S.job.id}/review`)).json();
  S.review = S.jobReview;
  S.feedback = (await (await fetch(`/jobs/${S.job.id}/feedback?limit=1`)).json()).count;
  S.reports = (await (await fetch(`/jobs/${S.job.id}/reports`)).json()).count;
  updateReportBadge();
  showAppliedRules();
  await showTemplates();
  buildTabs();
  updateBadge();
  renderReviewPanel();
  renderGrid();
}

$("#only-changed").onchange = (e) => {
  S.onlyChanged = e.target.checked;
  renderGrid();
};
$("#only-review").onchange = (e) => {
  S.onlyReview = e.target.checked;
  syncUrl(); renderGrid();
};

/* A filter that matches nothing must say so.  An empty table with four chips
 * above it reads as "there is nothing here", which is a different statement. */
function updateEmptyNote() {
  const box = $("#empty-note");
  if (!box) return;
  // 아직 안 불러온 것과 조건에 맞는 것이 없는 것은 다른 상태다.  같은 자리에
  // 다른 문장을 쓴다 - 빈 표만 보여 주면 둘이 구분되지 않는다.
  if (S.loading) {
    box.classList.remove("hidden");
    box.textContent = "행을 불러오는 중입니다…";
    return;
  }
  const n = visibleRows().length;
  box.classList.toggle("hidden", n > 0);
  if (!n) {
    const narrowed = S.filter || S.gradeFilter || S.axis || S.code || S.drawing
      || S.originFilter || S.onlyReview || S.onlyChanged
      || Object.keys(S.colFilters).length;
    box.textContent = narrowed
      ? "이 조건에 맞는 행이 없습니다 — 위의 조건 칩을 하나씩 해제해 보세요."
      : "이 분석에는 행이 없습니다.";
  }
}

function showOpenReview() {
  const box = $("#open-review");
  if (!box) return;
  const open = ((S.review && S.review.axes) || []).reduce((n, a) => n + a.open, 0);
  if (!open) { box.textContent = ""; box.classList.add("hidden"); return; }
  box.classList.remove("hidden");
  // 축별 숫자는 바로 위 검토 축 줄이 축마다 이미 말한다.  여기서 그 목록을 다시
  // 늘어놓으면 같은 다섯 숫자가 위아래로 두 번 나온다 - 실제로 그랬다.  남길 것은
  // 축 줄이 말하지 않는 것 하나뿐이다: 미처리로 두면 산출물에 무엇이 찍히는가.
  box.textContent = `미처리 ${open}건은 Remark 열에 "미처리"로 나갑니다.`;
}

/* ---------------- review axes ----------------
 * Which decision is outstanding, and how much of it is done.  The tabs answer
 * "which deliverable"; this answers "what am I being asked to decide", which is
 * the question someone opens the screen with. */
function axisRows(axis, code) {
  const states = (S.review && S.review.states) || {};
  return S.rows.filter(r => {
    const codes = rowCodes(r);
    if (!codes.length) return false;
    if (code) return codes.includes(code);
    if (!axis) return true;
    return codes.some(c => codeAxis(c) === axis);
  }).filter(r => !S.onlyReview || openCodes(r, states).length);
}

function codeAxis(code) {
  const map = (S.review && S.review.axisOf) || {};
  return map[code] || "OTHER";
}

/* The codes on one row, as the API computed them.  Kept on the row itself so the
 * grid can filter without asking the server again on every click. */
function rowCodes(row) {
  return (row.review_codes || []);
}

function openCodes(row, states) {
  const done = states[row.key] || {};
  return rowCodes(row).filter(c => !done[c]);
}

function renderReviewPanel() {
  showOpenReview();
  const bar = $("#review-panel");
  if (!S.review || !S.review.axes) { bar.innerHTML = ""; return; }
  S.review.axisOf = {};
  for (const a of S.review.axes) {
    for (const c of a.codes) S.review.axisOf[c.code] = a.axis;
  }
  const total = S.review.axes.reduce((n, a) => n + a.open + a.done, 0);
  const done = S.review.axes.reduce((n, a) => n + a.done, 0);
  bar.innerHTML = `<b>검토</b> <span class="n">${done}/${total}</span>`
    + S.review.axes.map(a => {
        const all = a.open + a.done;
        const pct = all ? Math.round(100 * a.done / all) : 0;
        return `<button class="axis${S.axis === a.axis ? " on" : ""}${a.open ? " has-open" : " zero"}"
                  data-axis="${a.axis}" title="${a.label} — 처리 ${a.done} / 남음 ${a.open}">
                  ${a.label} <span class="n">${a.open}</span>
                  <span class="bar"><i style="width:${pct}%"></i></span></button>`;
      }).join("")
    + (S.axis || S.code ? `<button class="axis clear" data-axis="">해제</button>` : "");
  bar.querySelectorAll("button.axis").forEach(b => {
    b.onclick = () => {
      S.axis = b.dataset.axis === S.axis ? "" : b.dataset.axis;
      S.code = "";
      syncUrl(); renderReviewPanel(); renderGrid();
    };
  });
  renderReviewCodes();
}

function renderReviewCodes() {
  const box = $("#review-codes");
  const axis = S.review && S.review.axes.find(a => a.axis === S.axis);
  if (!axis) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  box.classList.remove("hidden");
  box.innerHTML = axis.codes.map(c => `
      <button class="rcode${S.code === c.code ? " on" : ""}" data-code="${c.code}"
              title="${c.label}">${c.label}
        <span class="n">${c.open}</span>
        ${c.done ? `<span class="n done">완료 ${c.done}</span>` : ""}</button>`).join("");
  box.querySelectorAll("button.rcode").forEach(b => {
    b.onclick = () => {
      S.code = b.dataset.code === S.code ? "" : b.dataset.code;
      syncUrl(); renderReviewCodes(); renderGrid(); renderChips();
    };
  });
}

/* Every filter in force, each removable on its own.  Without this the grid can
 * be showing four rows for a reason that is two clicks back in the history. */
function renderChips() {
  const box = $("#chips");
  const chips = [];
  if (S.tab !== "ALL") chips.push(["tab", `탭 ${S.tab}`]);
  if (S.axis) chips.push(["axis", `축 ${(S.review.axes.find(a => a.axis === S.axis) || {}).label || S.axis}`]);
  if (S.code) chips.push(["code", `사유 ${S.code}`]);
  if (S.drawing) chips.push(["drawing", `도면 ${S.drawing}`]);
  if (S.gradeFilter) chips.push(["gradeFilter", `등급 ${S.gradeFilter}`]);
  if (S.reasonFilter) chips.push(["reasonFilter", `사유 ${S.reasonFilter}`]);
  if (S.originFilter) chips.push(["originFilter", `귀속 ${S.originFilter}`]);
  if (S.onlyReview) chips.push(["onlyReview", "검토 필요만"]);
  if (S.filter) chips.push(["filter", `검색 ${S.filter}`]);
  // One chip per filtered column, carrying its own ×.  The header mark says
  // *that* a column is filtered; the chip says what to, and is where it gets
  // cleared from without hunting for the right dropdown.
  for (const key of FILTER_COLS) {
    const chosen = colChosen(key);
    if (!chosen) continue;
    const label = (COLS.find(([k]) => k === key) || [key, key])[1];
    const shown = chosen.map(v => v === BLANK ? "(공란)" : v);
    const text = shown.length <= 2 ? shown.join(", ") : `${shown[0]} 외 ${shown.length - 1}`;
    chips.push([`col:${key}`, `${label} ${text}`]);
  }
  box.classList.toggle("hidden", !chips.length);
  box.innerHTML = chips.map(([k, label]) =>
    `<span class="chip">${label}<button data-k="${k}" title="이 조건만 해제">×</button></span>`).join("");
  box.querySelectorAll("button").forEach(b => {
    b.onclick = () => {
      const k = b.dataset.k;
      if (k.startsWith("col:")) { setColumnFilter(k.slice(4), null); return; }
      if (k === "tab") S.tab = "ALL";
      else if (k === "onlyReview") { S.onlyReview = false; $("#only-review").checked = false; }
      else if (k === "filter") { S.filter = ""; $("#filter").value = ""; }
      else if (k === "originFilter") { S.originFilter = ""; $("#origin-filter").value = ""; }
      else S[k] = "";
      if (k === "axis") S.code = "";
      syncUrl(); buildTabs(); renderReviewPanel(); renderGrid();
    };
  });
}

/* The view lives in the URL after the job id, so a reload or a link keeps it. */
function syncUrl() {
  const q = new URLSearchParams();
  for (const k of ["tab", "axis", "code", "drawing", "gradeFilter",
                   "reasonFilter", "originFilter", "filter"]) {
    if (S[k] && S[k] !== "ALL") q.set(k, S[k]);
  }
  if (S.onlyReview) q.set("onlyReview", "1");
  // Column filters ride in the URL like every other condition, so a shared link
  // reproduces the grid.  Values are joined with '|' rather than ',' because a
  // System name may contain a comma; the blank choice travels as an empty
  // element, which survives the round trip ('|PIT' -> ['', 'PIT']).
  for (const key of FILTER_COLS) {
    const chosen = colChosen(key);
    if (chosen) q.set("col." + key, chosen.map(v => v === BLANK ? "" : v).join("|"));
  }
  const qs = q.toString();
  const next = S.job.id + (qs ? "?" + qs : "");
  if (location.hash.slice(1) !== next) history.replaceState(null, "", "#" + next);
}

function readUrl(query) {
  const q = new URLSearchParams(query || "");
  for (const k of ["tab", "axis", "code", "drawing", "gradeFilter",
                   "reasonFilter", "originFilter", "filter"]) {
    if (q.has(k)) S[k] = q.get(k);
  }
  S.onlyReview = q.get("onlyReview") === "1";
  S.colFilters = {};
  for (const key of FILTER_COLS) {
    if (!q.has("col." + key)) continue;
    const vals = q.get("col." + key).split("|").map(v => v === "" ? BLANK : v);
    if (vals.length) S.colFilters[key] = vals;
  }
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
  // 문서 단위 지적은 검토필요 탭의 보조줄이 됐다 (buildTabs).  여기 또 쓰면
  // 같은 숫자가 두 곳이므로 이 배지는 완전히 접는다.
  b.textContent = "";
  b.classList.add("hidden");
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
  // Where this run's geometry came from.  A profile that was written for another
  // project is not an error and not a silent substitution: the sheet is measured
  // and every value that moved is named here, so a reviewer can see whether the
  // tool fitted itself to the drawing or was handed the numbers.
  const L = a.layout || {};
  const layoutRow = () => {
    if (!L.reason) return "";
    const moved = (L.moved || []).map(m =>
      `<code>${escape(m.key)}</code> ${escape(JSON.stringify(m.was))} → `
      + `<b>${escape(JSON.stringify(m.now))}</b>`).join("<br>");
    const items = (L.items || []).map(it =>
      `<code>${escape(it.key)}</code> <b>${escape(JSON.stringify(it.value))}</b>`
      + ` <span class="muted">[${it.source}] ${escape(it.evidence || "")}</span>`)
      .join("<br>");
    return row("도면 유도 레이아웃",
      `${L.applied ? "<b>도면에서 측정한 값을 사용</b>" : "프로필 값을 사용"}`
      + ` <span class="muted">— ${escape(L.reason)}</span>`
      + (moved ? `<br><br><b>바뀐 값 ${(L.moved || []).length}개</b><br>${moved}` : "")
      + (items ? `<br><br><b>측정 내역</b><br><span class="muted">${items}</span>` : "")
      + ((L.notes || []).length
        ? `<br><span class="muted">${(L.notes || []).map(escape).join("<br>")}</span>`
        : ""));
  };
  $("#rules-body").innerHTML = "<dl class='rules'>"
    + layoutRow()
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
  // 문서 단위 지적은 검토필요 탭의 보조줄로 들어간다.  행 수는 탭이, 문서
  // 건수는 보조줄이 - 같은 숫자를 두 곳에 쓰지 않는다는 규칙 그대로다.
  const doc = ((S.jobReview && S.jobReview.job_review) || []).length;
  for (const [key, label] of TABS) {
    const b = document.createElement("button");
    b.className = (key === S.tab ? "on" : "")
      + (key === "ALL" ? " tab-all" : "")
      + (key === "REVIEW" ? " tab-review" : "");
    b.dataset.tab = key;
    b.innerHTML = key === "REVIEW" && doc
      ? `<span class="tab-line">${label}<span class="n">${S.counts[key] || 0}</span></span>`
        + `<span class="tab-sub">+ 문서 ${doc}건</span>`
      : `${label}<span class="n">${S.counts[key] || 0}</span>`;
    if (key === "REVIEW" && doc) {
      b.title = ((S.jobReview && S.jobReview.job_review) || [])
        .map(j => `${j.kind} p${(j.pages || []).join(",")}`).join("\n");
    }
    b.onclick = () => { S.tab = key; buildTabs(); renderGrid(); drawOverlay(); };
    $("#tabs").appendChild(b);
  }
}

/* ---------------- grid ---------------- */

/* Which columns carry a dropdown, and the fact that the grid, the sort, the
 * filter and the value list all read a cell the same way.
 *
 * `pid_no` is the reason this function exists: the drawing number is not on the
 * row and never has been - it belongs to the page - so every place that wanted
 * it was looking it up separately, and the top search box was looking in the
 * wrong object entirely (see `#filter` below).  One accessor, four callers, no
 * chance of them disagreeing about what a cell says. */
const FILTER_COLS = ["page_no", "pid_no", "type", "valve_type", "qty",
                     "system", "vendor_supply"];
const BLANK = "\u0000blank";        // the '(공란)' choice, kept out of value space

function cellValue(row, key) {
  if (key === "page_no") return row.page_no;
  if (key === "origin") return row.origin;
  if (key === "pid_no") {
    return (S.pages.find(p => p.page_no === row.page_no) || {}).drawing_no
      || row.drawing_no || "";
  }
  if (key === "remark") return remarkOf(row);
  return row.values[key] ?? "";
}

/* The choices a column offers, taken from the data rather than written down.
 *
 * The list is built from the rows that pass every *other* condition, which is
 * what a spreadsheet does: a value that would show nothing is not offered, and
 * on the MOV tab the Valve Type list is the MOV valve types.  Blank is a choice
 * of its own because on Vendor and Valve Type it is most of the column, and
 * "the ones with nothing in them" is a real question about those two. */
function columnValues(key) {
  const seen = new Map();
  for (const r of visibleRows(key)) {
    const v = cellValue(r, key);
    const k = (v === "" || v === null || v === undefined) ? BLANK : String(v);
    seen.set(k, (seen.get(k) || 0) + 1);
  }
  const numeric = key === "page_no" || key === "qty";
  return [...seen.entries()]
    .sort((a, b) => a[0] === BLANK ? 1 : b[0] === BLANK ? -1
      : numeric ? Number(a[0]) - Number(b[0])
      : (a[0] > b[0] ? 1 : a[0] < b[0] ? -1 : 0));
}

function colChosen(key) {
  return S.colFilters[key] || null;
}

function anyColFilter() {
  return FILTER_COLS.some(k => colChosen(k));
}

function passesColumns(row, except) {
  for (const key of FILTER_COLS) {
    if (key === except) continue;
    const chosen = colChosen(key);
    if (!chosen) continue;
    const v = cellValue(row, key);
    const k = (v === "" || v === null || v === undefined) ? BLANK : String(v);
    if (!chosen.includes(k)) return false;
  }
  return true;
}

/* `except` leaves one column's own filter out, so that column's dropdown can
 * offer every value still reachable rather than only the ones already ticked -
 * otherwise unticking would be the only move a filtered column ever allowed. */
function visibleRows(except) {
  // 삭제 후보는 그 리비전에만 있는 행이므로 본 목록 뒤에 붙인다.  본 목록의
  // 개수(S.rows.length)는 그대로 두어야 "824행" 이 흔들리지 않는다.
  let rows = S.deletedRows && S.deletedRows.length
    ? S.rows.concat(S.deletedRows) : S.rows;
  if (S.tab === "REVIEW") rows = rows.filter(r => r.needs_review || r.deleted);
  else if (S.tab !== "ALL") rows = rows.filter(r => r.tab === S.tab);
  if (S.originFilter) rows = rows.filter(r => r.origin === S.originFilter);
  if (S.drawing) rows = rows.filter(r => r.values.pid_no === S.drawing
                                      || r.drawing_no === S.drawing);
  // The review filters work on every tab, not only 검토필요: the axis is what the
  // reviewer is doing, and it should survive switching deliverable.
  const states = (S.review && S.review.states) || {};
  if (S.code) rows = rows.filter(r => rowCodes(r).includes(S.code));
  else if (S.axis) rows = rows.filter(r => rowCodes(r).some(c => codeAxis(c) === S.axis));
  if (S.onlyReview) rows = rows.filter(r => openCodes(r, states).length);
  if (S.onlyChanged) {
    rows = rows.filter(r => ["ADDED", "MODIFIED", "DELETED_CANDIDATE", "DELETED"]
      .includes((r.rev || {}).state));
  }
  // These used to be limited to 검토필요, because applied elsewhere they hid rows
  // with nothing on screen to say why.  Now every condition in force is a chip
  // above the grid, so the reason is always visible and the filter can work on
  // any tab - which is what a shared link setting `gradeFilter` expects.
  if (S.gradeFilter) {
    rows = rows.filter(r => r.values.description_grade === S.gradeFilter);
  }
  if (S.reasonFilter) rows = rows.filter(r => reasonTag(r) === S.reasonFilter);
  // The column dropdowns AND with everything above and with each other.
  if (anyColFilter()) rows = rows.filter(r => passesColumns(r, except));
  if (S.filter) {
    // Searched over the cells the grid actually shows, one by one.
    //
    // It used to search `JSON.stringify(row.values)`, which had two faults.  The
    // drawing number is not in `values` - it is on the page - so `필터 — 도면번호`
    // matched nothing, ever; and stringifying an object puts the *key names* and
    // the JSON punctuation into the haystack, so a query like `type` or `qty`
    // matched all 826 rows.  Reading the cells removes both.
    const q = S.filter.toLowerCase();
    rows = rows.filter(r => SEARCH_COLS.some(
      k => String(cellValue(r, k)).toLowerCase().includes(q)));
  }
  const { col, dir } = S.sort;
  return rows.slice().sort((a, b) => {
    const av = cellValue(a, col), bv = cellValue(b, col);
    return (av > bv ? 1 : av < bv ? -1 : 0) * dir;
  });
}

/* What the free-text box looks in.  Every column the grid renders as text, so
 * the box is a search over what is on screen - including Description and Remark,
 * which no dropdown can offer because their values are nearly all distinct. */
const SEARCH_COLS = ["page_no", "pid_no", "origin", "type", "valve_type", "qty",
                     "system", "vendor_supply", "scope", "tag_no", "description",
                     "description_grade", "remark"];

/* The review tab's own grouping: which rows still need a Description written by
 * hand, split by the reason the tool could not write one.  Clicking a group
 * filters the grid to it, because "which of these 700 rows is mine to do" is the
 * question a reviewer opens this tab with. */
/* The engine puts a short tag in front of a Remark it wrote for a reason it
 * measured - `[중간 심볼] ...`, `[CCW 방향] ...`.  The tag is generated rather than
 * read back out of the sentence, so grouping on it cannot drift from the text. */
function reasonTag(row) {
  const m = /^\[([^\]]+)\]/.exec(String(row.values.remark || ""));
  return m ? m[1] : "";
}

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
  // A second row for the rows the drawing is measured not to answer: those are
  // not "the tool fell short", they are a known question for a person, and a
  // reviewer wants them together rather than scattered through the grades.
  const reasons = {};
  for (const r of S.rows) {
    const t = reasonTag(r);
    if (t) reasons[t] = (reasons[t] || 0) + 1;
  }
  const keys = Object.keys(reasons).sort();
  if (keys.length) {
    const n = keys.reduce((a, k) => a + reasons[k], 0);
    bar.innerHTML += `<span class="grp-sep"></span><b>도면에서 회수 불가</b>`
      + ` <span class="n">${n}행</span>`
      + keys.map(k => `
        <button class="grp rsn${S.reasonFilter === k ? " on" : ""}" data-r="${k}"
                title="직접 입력이 필요한 사유">${k} <span class="n">${reasons[k]}</span></button>`).join("")
      + `<button class="grp rsn${S.reasonFilter ? "" : " on"}" data-r="">전체</button>`;
  }
  bar.querySelectorAll("button.grp").forEach(b => {
    b.onclick = () => {
      if (b.dataset.r !== undefined) {
        S.reasonFilter = b.dataset.r === S.reasonFilter ? "" : (b.dataset.r || "");
      } else {
        S.gradeFilter = b.dataset.g === S.gradeFilter ? "" : (b.dataset.g || "");
      }
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
  renderChips();
  updateEmptyNote();
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
    if (FILTER_COLS.includes(key)) {
      // The dropdown handle, and the whole of this column's filter state: a
      // filtered column has to be recognisable from the header alone, or the
      // grid is short and nothing on screen says why.
      const chosen = colChosen(key);
      const b = document.createElement("button");
      b.className = "colf" + (chosen ? " on" : "");
      b.dataset.col = key;
      // Not a filled triangle: the sort indicator next to it is ▲/▼, and the two
      // marks read as one arrow when they sit side by side on the same header.
      b.textContent = chosen ? `▾${chosen.length}` : "▾";
      b.title = chosen
        ? `${label}: ${chosen.length}개 값만 표시 — 클릭해 변경`
        : `${label} 값으로 거르기`;
      b.onclick = (ev) => { ev.stopPropagation(); openColumnMenu(key, label, b); };
      th.appendChild(b);
      if (chosen) th.classList.add("filtered");
    }
    head.appendChild(th);
  }
  const flags = document.createElement("th");
  flags.textContent = "";
  head.appendChild(flags);

  const rows = visibleRows();
  // "표시 N / 전체 M" the moment anything is narrowing the grid, because a bare
  // row count next to a filtered table reads as the size of the job.
  const nDel = (S.deletedRows || []).length;
  const tail = nDel ? ` (+ 삭제 후보 ${nDel})` : "";
  $("#count").textContent = (rows.length === S.rows.length + nDel
    ? `${S.rows.length}행`
    : `표시 ${rows.length} / 전체 ${S.rows.length}`) + tail;
  const body = $("#body");
  body.innerHTML = "";
  for (const r of rows) {
    const tr = document.createElement("tr");
    tr.dataset.key = r.key;
    if (r.added) tr.dataset.added = "1";
    if (r.deleted || r.removed) tr.classList.add("deleted");
    if (r.added) tr.classList.add("added");
    // 개정 상태.  BASELINE(Rev.A) 과 UNCHANGED 는 아무 표기도 붙이지 않는다.
    const st = (r.rev || {}).state;
    if (st === "ADDED" || st === "MODIFIED") {
      tr.classList.add(st === "ADDED" ? "rev-added" : "rev-modified");
      tr.dataset.rev = st;
    } else if (st === "DELETED_CANDIDATE" || st === "DELETED") {
      tr.classList.add("rev-deleted");
      tr.dataset.rev = st;
    }
    if (S.sel === r.key) tr.classList.add("sel");
    for (const [key, , editable] of cols) {
      const td = document.createElement("td");
      const val = key === "page_no" ? r.page_no
        : key === "origin" ? r.origin
        : key === "pid_no" ? (S.pages.find(p => p.page_no === r.page_no) || {}).drawing_no || ""
        : key === "remark" ? remarkOf(r)
        : (r.values[key] ?? "");
      if (key === "description_grade" && val) {
        // 배지 하나에 모양·글자·색이 같이 실린다.  모양과 글자만으로도 읽힌다.
        const g = GRADES.find(x => x[0] === val);
        const b = document.createElement("span");
        b.className = `gradge g-${val}`;
        b.innerHTML = `<i class="gm">${GRADE_MARK[val] || "·"}</i>`
          + `<span>${escape(g ? g[1] : val)}</span>`;
        b.title = g ? g[2] : val;
        td.appendChild(b);
      } else {
        td.textContent = val;
      }
      if (key === "origin") td.classList.add(`origin-${r.origin}`);
      // 사람이 고친 칸과 엔진이 채운 칸은 색이 아니라 표시로 갈린다: 사람이 고친
      // 칸에는 연필이 붙는다.  "직접 입력" 등급과 같은 기호를 쓰는 것은 같은
      // 사실을 말하기 때문이다.
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
    // 삭제 후보는 확정 버튼을 달고 나온다.  자동으로 굳지 않는다.
    if (r.delCand) {
      const b = document.createElement("button");
      b.className = "mini-rep del-confirm";
      b.textContent = r.delCand.confirmed ? "확정 취소" : "삭제 확정";
      b.title = `Rev 좌표 (${r.delCand.anchor.join(", ")}) · 반경 `
        + `${r.delCand.radius}pt (${r.delCand.radius_source}) · 가장 가까웠던 후보 `
        + (r.delCand.nearest_distance === null ? "없음"
           : r.delCand.nearest_distance + "pt");
      b.onclick = async (ev) => {
        ev.stopPropagation();
        await fetch(`/jobs/${S.job.id}/deleted/`
          + `${encodeURIComponent(r.delCand.id)}/confirm`
          + `?confirmed=${!r.delCand.confirmed}`, { method: "POST" });
        await loadRevision();
        await loadRows();
      };
      f.appendChild(b);
    }
    if (r.removed) f.innerHTML += '<span class="flag" title="검토자 삭제 — 출력 제외">✕</span>';
    // One click from any row to a report, because a reviewer notices the error
    // while looking at the grid and will not go hunting for a menu.
    const rep = document.createElement("button");
    rep.className = "mini-rep";
    rep.textContent = "신고";
    rep.title = "이 행의 판정이 틀렸다고 신고합니다";
    rep.onclick = (ev) => {
      ev.stopPropagation();
      reportDialog({ rowKey: r.key, pageNo: r.page_no });
    };
    f.appendChild(rep);
    tr.appendChild(f);
    tr.onclick = () => select(r.key, true);
    body.appendChild(tr);
  }
}

/* The dropdown itself.
 *
 * One panel, moved and refilled, rather than one per header: the list can run to
 * fifty-odd drawing numbers and building seven of those on every render would be
 * paid for on every keystroke in a cell.  Nothing is applied until 적용 is
 * pressed, so a reviewer can tick five things without the grid rebuilding five
 * times underneath them. */
function openColumnMenu(key, label, button) {
  const menu = $("#colmenu");
  if (menu.dataset.col === key && !menu.classList.contains("hidden")) {
    closeColumnMenu(); return;
  }
  const values = columnValues(key);
  const chosen = colChosen(key);
  const on = (v) => !chosen || chosen.includes(v);
  menu.dataset.col = key;
  menu.innerHTML =
    `<div class="cm-head"><b>${escape(label)}</b>
       <button class="ghost mini" id="cm-all">전체선택</button>
       <button class="ghost mini" id="cm-none">해제</button></div>
     <div class="cm-list">${values.map(([v, n]) => `
       <label><input type="checkbox" class="cm-v"${on(v) ? " checked" : ""}>
         <span class="cm-text">${v === BLANK ? "<i>(공란)</i>" : escape(v)}</span>
         <span class="n">${n}</span></label>`).join("")}</div>
     <div class="cm-foot">
       <button class="ghost mini" id="cm-clear">이 컬럼 필터 해제</button>
       <button id="cm-apply">적용</button></div>`;
  const box = button.getBoundingClientRect();
  menu.classList.remove("hidden");
  // Placed after it is shown, so its real height is known and a dropdown near
  // the bottom of the window opens upwards instead of off the screen.
  const h = menu.offsetHeight;
  menu.style.left = `${Math.max(4, Math.min(box.left, window.innerWidth - menu.offsetWidth - 4))}px`;
  menu.style.top = `${box.bottom + h > window.innerHeight ? Math.max(4, box.top - h) : box.bottom + 2}px`;

  // The value is put on the element rather than into an attribute: a System
  // name is free text off the drawing and can hold a quote, and the blank
  // sentinel is not a character an attribute should carry at all.
  const boxes = () => [...menu.querySelectorAll(".cm-v")];
  boxes().forEach((c, i) => { c._value = values[i][0]; });
  $("#cm-all").onclick = () => boxes().forEach(c => { c.checked = true; });
  $("#cm-none").onclick = () => boxes().forEach(c => { c.checked = false; });
  $("#cm-clear").onclick = () => { setColumnFilter(key, null); closeColumnMenu(); };
  $("#cm-apply").onclick = () => {
    const picked = boxes().filter(c => c.checked).map(c => c._value);
    // Everything ticked is not a filter, it is the absence of one - storing it
    // would leave a chip and a header mark standing over a grid that is not
    // being narrowed.
    setColumnFilter(key, picked.length === boxes().length ? null : picked);
    closeColumnMenu();
  };
}

function closeColumnMenu() {
  const menu = $("#colmenu");
  menu.classList.add("hidden");
  menu.dataset.col = "";
  menu.innerHTML = "";
}

function setColumnFilter(key, values) {
  if (values && values.length) S.colFilters[key] = values;
  else delete S.colFilters[key];
  syncUrl();
  renderGrid();
}

document.addEventListener("mousedown", ev => {
  const menu = $("#colmenu");
  if (menu.classList.contains("hidden")) return;
  if (menu.contains(ev.target) || ev.target.closest(".colf")) return;
  closeColumnMenu();
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape") closeColumnMenu();
});

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
  // Bulk applies to the rows this one is indistinguishable from: same drawing,
  // same Type, and the same sentence standing in the column right now.  The
  // sentence has to be part of it.  Drawing and Type alone put the 58 PARTIAL
  // rows into 17 groups, not the 25 the reviewer sees, because one drawing's TIT
  // rows can belong to three different units - and worse, on p11 that group also
  // contains 7 rows the engine already filled from the drawing, which one click
  // would have overwritten (p10 TIT: 10 of them).  Matching the sentence too
  // gives exactly the 25 groups and touches nothing outside the one on screen.
  const was = row.values.description || "";
  const targets = opts.bulk
    ? S.rows.filter(r => !r.deleted && !r.removed
        && r.drawing_no === row.drawing_no && r.values.type === row.values.type
        && (r.values.description || "") === was)
    : [row];
  for (const r of targets) {
    if (!await patch(r, "description", text)) return;
    // The grade is a user value; the Remark is not patched to empty because an
    // empty edit means "revert to what the engine said" (db.set_user_value), and
    // reverting would put the old "직접 입력" note back.  A USER_ENTERED row simply
    // shows no Remark - see remarkOf().
    await patch(r, "description_grade", "USER_ENTERED");
  }
  // Writing the sentence answers `DESC_GRADE_PARTIAL` for every row it filled, so
  // the review panel's counts move with it.  They are computed server-side from
  // the merged grade, so they have to be re-read rather than adjusted here.
  S.review = await (await fetch(`/jobs/${S.job.id}/review`)).json();
  updateBadge();
  renderReviewPanel();
  renderGrid();
  const again = S.rows.find(r => r.key === row.key);
  if (again) showEvidence(again);
  if (opts.bulk) {
    alert(`${targets.length}행에 적용했습니다 — ${row.drawing_no} / `
      + `${row.values.type} / “${was}”`);
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
  // 삭제 후보는 `S.rows` 가 아니라 `S.deletedRows` 에 산다 (이번 리비전에 그
  // 심볼이 없으므로 검출 행이 아니다).  둘 다 봐야 근거 패널이 열린다.
  const row = S.rows.find(r => r.key === key)
    || (S.deletedRows || []).find(r => r.key === key);
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
/* One flagged reason and what the reviewer decided about it.  "확인함" counts as
 * work done: judging that the engine's value is right is a review, and a screen
 * that only counts edits tells the reviewer their afternoon did not happen. */
const REVIEW_STATES = [["CONFIRMED", "확인함", "값이 맞다고 판단"],
                       ["EDITED", "수정함", "값을 고침"],
                       ["HELD", "보류", "지금 정할 수 없음"]];

function reviewControls(row) {
  const codes = row.review_codes || [];
  if (!codes.length) return "";
  const state = row.review_state || {};
  const labels = (S.review && S.review.labels) || {};
  return `<div class="review-item"><b>검토 항목</b>` + codes.map(c => {
    const cur = (state[c] || {}).state || "";
    const axis = codeAxis(c);
    const axisLabel = ((S.review.axes || []).find(a => a.axis === axis) || {}).label || axis;
    return `<div class="ritem" data-code="${c}">
        <span class="raxis">${axisLabel}</span>
        <span class="rlabel">${labels[c] || c}</span>
        ${REVIEW_STATES.map(([k, t, why]) =>
          `<button class="rstate${cur === k ? " on" : ""}" data-code="${c}"
                   data-state="${k}" title="${why}">${t}</button>`).join("")}
      </div>`;
  }).join("") + `</div>`;
}

function bindReviewControls(row) {
  document.querySelectorAll("#evidence button.rstate").forEach(b => {
    b.onclick = async () => {
      const code = b.dataset.code;
      const cur = ((row.review_state || {})[code] || {}).state || "";
      const next = cur === b.dataset.state ? "" : b.dataset.state;
      await fetch(`/jobs/${S.job.id}/rows/${row.key}/review/${code}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: next }),
      });
      row.review_state = row.review_state || {};
      if (next) row.review_state[code] = { state: next, note: "" };
      else delete row.review_state[code];
      S.review = await (await fetch(`/jobs/${S.job.id}/review`)).json();
      renderReviewPanel();
      renderGrid();
      showEvidence(row);
    };
  });
}

/* What the reviewer does about this row, put where the reason is.  Each action
 * writes an editable column - the same ones the grid edits - so nothing here
 * changes what the engine decided, only what the deliverable says. */
function axisActions(row) {
  const codes = row.review_codes || [];
  const out = [];
  if (codes.includes("VENDOR_MARK_UNDEFINED")
      || codes.includes("SCOPE_OVERRIDE_UNRESOLVED")) {
    const cur = row.values.vendor_supply || "";
    out.push(`<div class="ract"><span>스코프</span>
      <button class="ract-b${cur === "" ? " on" : ""}" data-act="scope" data-v="">포함</button>
      <button class="ract-b${cur === "VENDOR" ? " on" : ""}" data-act="scope" data-v="VENDOR">벤더 공급(제외)</button>
      </div>`);
  }
  const grp = (row.evidence || {}).signal_group;
  if (codes.includes("MULTI_SIGNAL_BUNDLE") && grp) {
    // `members` is the count of bubbles that touch; whether they are one
    // physical instrument or several is the question, so both answers are here.
    const n = Array.isArray(grp.members) ? grp.members.length : (grp.members || 0);
    const gaps = ((grp.basis || {}).touching_gaps_pt || []).join(", ");
    out.push(`<div class="ract"><span>묶음 ${n}개${gaps ? ` (간격 ${gaps}pt)` : ""}</span>
      <button class="ract-b" data-act="qty" data-v="1">합산 1</button>
      ${n ? `<button class="ract-b" data-act="qty" data-v="${n}">개별 ${n}</button>` : ""}
      </div>`);
  }
  return out.length ? `<div class="ractions">${out.join("")}</div>` : "";
}

function bindAxisActions(row) {
  document.querySelectorAll("#evidence button.ract-b").forEach(b => {
    b.onclick = async () => {
      const field = b.dataset.act === "scope" ? "vendor_supply" : "qty";
      await fetch(`/jobs/${S.job.id}/rows/${row.key}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value: b.dataset.v }),
      });
      await loadRows();
      const again = S.rows.find(r => r.key === row.key);
      if (again) showEvidence(again);
    };
  });
}

function showEvidence(row) {
  // 삭제 후보는 이번 리비전에 심볼이 없는 행이다.  근거 패널이 보여야 하는 것은
  // 검출 근거가 아니라 **왜 짝을 못 찾았는가** 이고, 그것이 사람이 '검출 실패'
  // 와 '실제 삭제' 를 가르는 재료다.
  if (row.delCand) { showDeletedEvidence(row.delCand); return; }
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
  // Bubbles drawn edge-to-edge are several signals off one physical instrument.
  // The user confirmed that against plant practice, so the stack is one row and
  // the panel says which signals it stands for - the reviewer is signing off on a
  // fold, and has to be able to see what was folded.
  const grp = e.signal_group;
  if (grp) {
    const members = e.signal_members || grp.members.map(m => m.anchor || m.type);
    add("다중 신호 버블", `${grp.members.length}개 버블이 한 묶음으로 그려져 있습니다 — `
      + members.join(" / "));
    add("묶음 근거", `테두리 간격 ${(grp.basis.touching_gaps_pt || []).join(", ")}pt `
      + `(허용 ${grp.basis.slack_pt}pt, legend_rules.INDEX_SLACK) · `
      + `첫 문자 '${grp.basis.shared_first_letter}' 공통 · 세로 정렬`);
    if (grp.basis.merged) {
      add("합산 판정", `물리 기기 1개로 접었습니다 — 버블 ${grp.members.length}개 중 `
        + `${grp.basis.folded_rows}행이 이 행에 흡수됐습니다 `
        + `(config multi_signal_bundle.merge_quantity)`);
      add("접기 전 수량", `${(grp.basis.qty_applied || []).join(" + ")} → `
        + `${row.values.qty} (1 x 시트 승수)`);
    } else {
      add("적용된 수량", `${(grp.basis.qty_applied || []).join(" + ")} — `
        + "합산하지 않았습니다 (config multi_signal_bundle.merge_quantity: false)");
    }
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
  // --- ④ 행의 FROM/TO 확정 (6회차) --------------------------------------
  const ov = (S.axisOv || {})[row.key];
  if (ov) {
    add("FROM/TO 확정", `FROM ${bareName(ov.from)} → TO ${bareName(ov.to)} `
      + `(FROM ${ov.source_from} · TO ${ov.source_to})`);
    if (ov.inherited) add("확정 출처", "이전 리비전 확정 승계 — 같은 안정 ID "
      + `${ov.stable_id} 가 매칭돼 자동으로 이어받았습니다`);
  }
  const ax = e.axis || {};
  if (ax.axis) {
    add("판정축", `${ax.axis}` + (ax.source === "신규문형"
      ? ` — 신규문형 (귀속 ${ax.attribution || ""})`
      : ax.axis === "④" ? " — 판정 불가, 현행 문장 유지" : ""));
  }
  // The button used to sit *inside* the h3, so the heading read
  // "판정 근거 — LS (p7)신고" - one string, no separator, and a screen reader
  // announcing the button as part of the title.  It is a sibling now; the row
  // that holds them carries the margin the h3 used to have.
  $("#evidence").innerHTML =
    `<div class="ev-head">`
    + `<h3>판정 근거 — ${escape(row.values.type || row.values.valve_type || "")} `
    + `(p${row.page_no})</h3>`
    + `<button id="ev-report" class="mini-rep" title="이 판정이 틀렸다고 신고합니다">신고</button>`
    + `</div>`
    + reviewControls(row) + axisActions(row)
    + "<dl>" + pairs.map(([k, v]) =>
      `<dt>${k}</dt><dd>${escape(String(v))}</dd>`).join("") + "</dl>"
    + fromToPicker(row)
    + candidatePicker(row);
  bindCandidatePicker(row);
  bindFromToPicker(row);
  bindReviewControls(row);
  bindAxisActions(row);
  const evb = $("#ev-report");
  if (evb) evb.onclick = () => reportDialog({ rowKey: row.key, pageNo: row.page_no });
}

/* The phrases the drawing prints along this instrument's pipe, nearest first.
 * Clicking one writes it into the Description between the system name and the
 * variable - the place the client's own lines put it - so the reviewer picks
 * rather than types. */
/* The rows this one is indistinguishable from - the reach of `일괄 적용`, shown
 * before it is pressed rather than reported after.  The 58 PARTIAL rows fall into
 * 25 such groups; drawing and Type alone would give 17 and would also sweep up
 * rows the engine had already filled. */
function sameSentence(row) {
  const text = row.values.description || "";
  return S.rows.filter(r => !r.deleted && !r.removed
    && r.drawing_no === row.drawing_no && r.values.type === row.values.type
    && (r.values.description || "") === text);
}

/* ---------------- ④ 행의 FROM/TO 지정 (6회차) ----------------
 *
 * 자동 추적의 세 실측(배관 그래프 13.1% · 국소 연결 4.9% · 무제한 순회 10.4%)이
 * 막은 자리를 사람이 확정한다.  후보는 그 도면에서 이미 읽은 텍스트 세 층
 * (커넥터 문구 · 기기 라벨 · 도면 텍스트)뿐이고, 고르면 입력칸에 실려 다듬을
 * 수 있다 - 후보 그대로면 "후보선택", 일부만 쓰면 "후보선택(부분)", 후보에
 * 없으면 "자유입력"으로 서버가 출처를 기록한다.  확정 전에는 현행 문장이
 * 그대로 남고, 같은 런의 다른 ④ 행에는 "같은 값 적용"을 제안만 한다.
 */
/* 후보 문구는 도면 원문이라 `FROM HRSG#12` 처럼 방향어를 이미 달고 있다.
 * 문장 조립이 그것을 벗기듯(describe_axis._strip_conn) 화면 표시도 벗긴다 -
 * 안 그러면 "FROM FROM HRSG#12" 로 읽힌다. */
function bareName(text) {
  return String(text || "").replace(/^\s*(FROM|TO)\b\s*/i, "").trim();
}

function fromToPicker(row) {
  const e = row.evidence || {};
  const ax = e.axis || {};
  if (ax.axis !== "④" || e.description_needed === false) return "";
  const ov = (S.axisOv || {})[row.key];
  return `<div class="cands" id="fromto">
      <h4>FROM/TO 지정 <span class="muted">— 판정 불가(④) 행을 사람이 확정합니다</span>
        <button id="ft-all" class="ghost mini-rep" aria-pressed="false"
          title="도면번호·치수·그리드 셀 같은 주석은 기본으로 접혀 있습니다. 정답이 그런 덩어리에 섞여 인쇄된 경우를 위해 펼쳐 볼 수 있습니다">전체 후보 보기</button></h4>
      <p class="muted" id="ft-status">${ov
        ? `확정됨: FROM ${escape(bareName(ov.from))} → TO ${escape(bareName(ov.to))}`
        : "후보를 불러오는 중…"}</p>
      <div class="cand-actions"><input id="ft-from" type="text" placeholder="FROM — 후보를 고르거나 입력"
        value="${escape(ov ? ov.from : "")}"></div>
      <div id="ft-from-cands"></div>
      <div class="cand-actions"><input id="ft-to" type="text" placeholder="TO — 후보를 고르거나 입력"
        value="${escape(ov ? ov.to : "")}"></div>
      <div id="ft-to-cands"></div>
      <div class="cand-actions">
        <button id="ft-save" class="ghost">FROM/TO 확정 — ② 문형 생성</button>
        ${ov ? `<button id="ft-clear" class="ghost" title="확정을 걷어내고 현행 문장으로 되돌립니다">확정 해제</button>` : ""}
      </div>
      <div id="ft-suggest"></div>
    </div>`;
}

function bindFromToPicker(row) {
  const box = document.querySelector("#fromto");
  if (!box) return;
  // 네 번째 층은 필터가 걸러낸 것이다.  기본으로 접혀 있고 토글로 펼친다 -
  // 버리지 않는 이유는 정답이 주석 덩어리에 섞여 인쇄되는 일이 있기 때문이다.
  const groups = [["커넥터 문구", "connectors"], ["기기 라벨", "equipment"],
                  ["도면 텍스트", "texts"], ["걸러낸 텍스트", "texts_filtered"]];
  let showAll = false, cache = null;
  const renderCands = (data, side) => {
    const holder = box.querySelector(`#ft-${side}-cands`);
    holder.innerHTML = groups.map(([label, k]) => {
      if (k === "texts_filtered" && !showAll) return "";
      return (data[k] || []).length
        ? `<div class="ft-group${k === "texts_filtered" ? " ft-dim" : ""}">`
          + `<span class="cand-kind">${label}</span>`
          + data[k].map(t => `<button class="ftc" data-side="${side}"
              data-t="${escape(t)}">${escape(t)}</button>`).join("") + `</div>`
        : "";
    }).join("");
    holder.querySelectorAll("button.ftc").forEach(b => {
      b.onclick = () => { box.querySelector(`#ft-${b.dataset.side}`).value = b.dataset.t; };
    });
  };
  const say = (data) => {
    const st = box.querySelector("#ft-status");
    if (!st || ((S.axisOv || {})[row.key])) return;
    const n = (data.connectors || []).length + (data.equipment || []).length
      + (data.texts || []).length
      + (showAll ? (data.texts_filtered || []).length : 0);
    st.textContent = `후보 ${n}건 — 커넥터 ${(data.connectors || []).length} · `
      + `기기 라벨 ${(data.equipment || []).length} · `
      + `도면 텍스트 ${(data.texts || []).length}`
      + ((data.texts_filtered || []).length
        ? (showAll ? ` · 걸러낸 텍스트 ${(data.texts_filtered || []).length}`
                   : ` · 접어 둔 주석 ${(data.texts_filtered || []).length}건`)
        : "");
  };
  fetch(`/jobs/${S.job.id}/rows/${row.key}/axis_candidates`)
    .then(r => r.json()).then(data => {
      cache = data;
      say(data);
      renderCands(data, "from");
      renderCands(data, "to");
    });
  const allBtn = box.querySelector("#ft-all");
  if (allBtn) allBtn.onclick = () => {
    showAll = !showAll;
    allBtn.setAttribute("aria-pressed", String(showAll));
    allBtn.textContent = showAll ? "주석 다시 접기" : "전체 후보 보기";
    if (cache) { say(cache); renderCands(cache, "from"); renderCands(cache, "to"); }
  };
  const apply = async (targetRow, fromText, toText) => {
    const res = await fetch(`/jobs/${S.job.id}/rows/${targetRow.key}/axis`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ from_text: fromText, to_text: toText }),
    });
    if (!res.ok) { alert((await res.json()).detail || "저장 실패"); return null; }
    const out = await res.json();
    if (out.cleared) {
      delete targetRow.user.description;
      delete targetRow.user.description_grade;
      const eng = (targetRow.ai || {}).description;
      targetRow.values.description = eng === undefined
        ? targetRow.values.description : eng;
      targetRow.values.description_grade = (targetRow.ai || {}).description_grade
        || targetRow.values.description_grade;
      delete (S.axisOv || {})[targetRow.key];
    } else {
      targetRow.user.description = out.sentence;
      targetRow.user.description_grade = "USER_ENTERED";
      targetRow.values.description = out.sentence;
      targetRow.values.description_grade = "USER_ENTERED";
      if (out.saved_to_project) {
        S.axisOv = S.axisOv || {};
        S.axisOv[targetRow.key] = { from: fromText, to: toText,
          source_from: out.source_from, source_to: out.source_to,
          stable_id: out.stable_id, inherited: false };
      }
    }
    return out;
  };
  const saveBtn = box.querySelector("#ft-save");
  if (saveBtn) saveBtn.onclick = async () => {
    const f = box.querySelector("#ft-from").value.trim();
    const t = box.querySelector("#ft-to").value.trim();
    if (!f || !t) { alert("FROM 과 TO 를 모두 고르거나 입력하세요"); return; }
    const out = await apply(row, f, t);
    if (!out) return;
    renderGrid();
    const sug = box.querySelector("#ft-suggest");
    // 같은 런의 다른 ④ 행 - 제안까지다.  행마다 사람이 누른다.
    if ((out.suggestions || []).length) {
      sug.innerHTML = `<p class="muted">같은 런으로 판정된 ④ 행이 `
        + `<b>${out.suggestions.length}행</b> 있습니다 — 같은 값 적용?</p>`
        + out.suggestions.map(s => `<button class="ftc ft-sg" data-key="${s.key}">
            ${escape(s.type)} — ${escape(s.description || "(공란)")}</button>`).join("");
      sug.querySelectorAll("button.ft-sg").forEach(b => {
        b.onclick = async () => {
          const r2 = S.rows.find(x => x.key === b.dataset.key);
          if (!r2) return;
          const o2 = await apply(r2, f, t);
          if (o2) { b.disabled = true; b.textContent += " ✓"; renderGrid(); }
        };
      });
    } else {
      sug.innerHTML = `<p class="muted">확정했습니다 — “${escape(out.sentence)}”`
        + `${out.saved_to_project ? " · 프로젝트 장부에 저장" : ""}</p>`;
    }
    const again = S.rows.find(r2 => r2.key === row.key);
    if (again && !(out.suggestions || []).length) showEvidence(again);
  };
  const clearBtn = box.querySelector("#ft-clear");
  if (clearBtn) clearBtn.onclick = async () => {
    const out = await apply(row, "", "");
    if (!out) return;
    renderGrid();
    const again = S.rows.find(r2 => r2.key === row.key);
    if (again) showEvidence(again);
  };
}

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
                title="같은 도면·같은 Type 이고 지금 같은 문장인 행에 모두 적용">일괄 적용</button>
      </div>
      ${sameSentence(row).length > 1
        ? `<p class="muted">이 문장을 그대로 쓰는 행이 `
          + `<b>${sameSentence(row).length}행</b> 있습니다 — `
          + `${escape(row.drawing_no)} / ${escape(row.values.type || "")}. `
          + `일괄 적용은 그 ${sameSentence(row).length}행만 바꿉니다.</p>`
        : ""}
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
    // The magnification is the reviewer's, not the page's: moving to the next
    // sheet keeps it, and only opening a job (which is also what re-analysis
    // ends in) starts fitted again.  See `open()`.
    measure();
    if (S.zoom) applyZoom(); else fit();
    drawOverlay();
    // A selection made from the grid was waiting for this page to arrive.
    if (S.pending) { const k = S.pending; S.pending = null; select(k, true); }
  };
  img.src = `/jobs/${S.job.id}/page/${page.page_no}.png?zoom=1.6`;
}

/* The sheet's own size, and the frame it is drawn into.  Split out of `fit()`
 * because changing page has to re-measure without also throwing away the zoom
 * the reviewer set: they are two different things and only one of them is a
 * property of the new page. */
function measure() {
  const img = $("#sheet");
  S.natural = { w: img.naturalWidth, h: img.naturalHeight };
  $("#wrap").style.width = `${S.natural.w}px`;
  $("#wrap").style.height = `${S.natural.h}px`;
}

function fit() {
  measure();
  S.zoom = ($("#stage").clientWidth - 16) / S.natural.w;
  applyZoom();
}
function applyZoom() { $("#wrap").style.transform = `scale(${S.zoom})`; }

/* The zoom step is the one the '+' / '-' buttons already used - 1.3 per click,
 * and 1/1.3 back - so the wheel and the keys land on exactly the magnifications
 * the buttons do.  There is no minimum or maximum in this code and none is
 * introduced here: the buttons have never clamped, and a bound picked now would
 * be a number with nothing behind it.  `ZOOM_STEP` exists so the four ways of
 * zooming cannot drift apart, not to add a value. */
const ZOOM_STEP = 1.3;

/* Zoom about a point rather than about the middle.
 *
 * `#wrap` is scaled with `transform-origin: 0 0` inside `#stage`, which is the
 * scroll container, so the document coordinate under the cursor is
 * `(scroll + offset) / zoom`.  Keeping that coordinate under the same screen
 * offset after the scale is one line of arithmetic, and it is the difference
 * between zooming *into* a symbol and zooming into the middle of the sheet and
 * then hunting for it again.  With no anchor given the viewport centre is used,
 * which is what the buttons and the keyboard do.
 */
function zoomBy(factor, anchor) {
  const stage = $("#stage");
  // Nothing to zoom until the sheet has loaded and been measured.  `S.zoom` is
  // null between opening a job and the image arriving, and multiplying that
  // would put NaN into the transform.
  if (!S.natural || !S.zoom) return;
  const box = stage.getBoundingClientRect();
  const ax = anchor ? anchor.x - box.left : stage.clientWidth / 2;
  const ay = anchor ? anchor.y - box.top : stage.clientHeight / 2;
  const docX = (stage.scrollLeft + ax) / S.zoom;
  const docY = (stage.scrollTop + ay) / S.zoom;
  S.zoom *= factor;
  applyZoom();
  stage.scrollLeft = docX * S.zoom - ax;
  stage.scrollTop = docY * S.zoom - ay;
}

$(".toolbar").addEventListener("click", ev => {
  const z = ev.target.dataset.z;
  if (z === undefined) return;
  if (z === "0") fit(); else zoomBy(z === "1" ? ZOOM_STEP : 1 / ZOOM_STEP);
});

/* Ctrl + wheel zooms about the cursor; a bare wheel is left alone, so the sheet
 * still scrolls the way every other scrollable thing on the page does.  The
 * listener is not passive because the browser's own page zoom has to be
 * prevented, and only for the modified case. */
$req("#stage").addEventListener("wheel", ev => {
  if (!ev.ctrlKey && !ev.metaKey) return;
  ev.preventDefault();
  zoomBy(ev.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, { x: ev.clientX, y: ev.clientY });
}, { passive: false });

/* Ctrl + '+' / '-' / '0', but only while the viewer holds focus.
 *
 * The listener sits on `#stage` (which carries `tabindex` so it can be focused)
 * rather than on the document, so a reviewer typing in a Description cell or in
 * the filter box keeps the browser's own zoom and its own text handling.  That
 * is the whole reason it is not a document-level handler.
 */
$req("#stage").addEventListener("keydown", ev => {
  if (!ev.ctrlKey && !ev.metaKey) return;
  if (ev.key === "+" || ev.key === "=") { ev.preventDefault(); zoomBy(ZOOM_STEP); }
  else if (ev.key === "-") { ev.preventDefault(); zoomBy(1 / ZOOM_STEP); }
  else if (ev.key === "0") { ev.preventDefault(); fit(); }
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
    // 세 축이 한 테두리를 두고 다투지 않게 갈라 놓는다:
    //   색      = scope (#0a84ff 포함 · #ff9f0a 벤더 제외) — 의미 그대로
    //   파선    = 종류 (밸브)
    //   바깥 링 = 개정 (추가 · 수정)
    // 개정을 같은 테두리의 굵기·파선으로 말하면 밸브의 파선과 "제외는 얇게"가
    // 둘 다 지워진다.  실제로 그랬다: `.det.rev-added` 가 뒤에 있어 `.det.valve`
    // 와 `.det.excluded` 를 이겼다.  그래서 개정은 자기 도형을 따로 그린다.
    const rev = (S.revByKey || {})[it.key];
    r.setAttribute("class", "det"
      + (it.kind === "VALVE" ? " valve" : "")
      + (it.row === false ? " excluded" : "")
      + (S.sel === it.key ? " sel" : ""));
    const stroke = S.byTab
      ? (COLOR[it.tab] || "#8e8e93")
      : (SCOPE_COLOR[it.scope || "INCLUDED"] || "#8e8e93");
    r.setAttribute("stroke", stroke);
    if (rev === "ADDED" || rev === "MODIFIED") {
      const pad = 4;
      const ring = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      ring.setAttribute("x", x0 * scale - pad);
      ring.setAttribute("y", y0 * scale - pad);
      ring.setAttribute("width", Math.max(2, (x1 - x0) * scale) + pad * 2);
      ring.setAttribute("height", Math.max(2, (y1 - y0) * scale) + pad * 2);
      ring.setAttribute("class", "revring "
        + (rev === "ADDED" ? "rev-added" : "rev-modified"));
      ring.dataset.rev = rev;
      ov.appendChild(ring);
    }
    r.dataset.key = it.key;
    r.onclick = (ev) => { ev.stopPropagation(); select(it.key, false, it); };
    // Right-click on the symbol itself: the same dialog the grid opens, so the
    // reviewer reports from wherever they noticed it.
    r.oncontextmenu = (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      select(it.key, false, it);
      reportDialog({ rowKey: it.key, pageNo: S.page.page_no, fromDrawing: true });
    };
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

/* Right-click on bare drawing: something is here and the engine did not find it.
 *
 * The overlay boxes stop this event themselves, so reaching here means the point
 * carries no detection - which is exactly the case that has no row to report
 * against.  The point goes with the record and the server probes the geometry
 * around it, the same probe the '＋행' flow uses, because "nothing was detected
 * at (x, y)" is only actionable if what *was* drawn there was written down. */
$req("#stage").addEventListener("contextmenu", ev => {
  if (S.picking || !S.page) return;
  if (ev.target.tagName.toLowerCase() === "rect") return;   // handled on the box
  const p = sheetPoint(ev);
  if (!p) return;
  ev.preventDefault();
  reportDialog({ pageNo: S.page.page_no, point: p, what: "OTHER" });
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
$req("#filter").addEventListener("input", ev => {
  S.filter = ev.target.value; syncUrl(); renderGrid();
});
$req("#origin-filter").addEventListener("change", ev => {
  S.originFilter = ev.target.value; syncUrl(); renderGrid();
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
  // Say what is still open, and do not stand in the way.  Whether an unanswered
  // question is a reason to hold the workbook back is the reviewer's call - but
  // they should not learn about it from the client.  A blocking dialog was tried
  // and rejected: it turns "you should know" into "you may not proceed".
  showOpenReview();
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
$req("#row-add").addEventListener("click", () => {
  clearFiltersForNewRow();
  startPick();
});

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

/* A row you just made has to be on screen.  The review filters are deliberately
 * sticky across tabs now, and a new row carries none of the reasons they select
 * on, so making one clears them - otherwise the row is created into a view that
 * cannot show it and the button looks broken. */
function clearFiltersForNewRow() {
  if (!(S.axis || S.code || S.gradeFilter || S.reasonFilter || S.onlyReview)) return;
  S.axis = ""; S.code = ""; S.gradeFilter = ""; S.reasonFilter = "";
  S.onlyReview = false;
  const only = $("#only-review"); if (only) only.checked = false;
  syncUrl(); renderReviewPanel();
}

$req("#row-copy").addEventListener("click", async () => {
  if (!S.sel) { alert("복사할 행을 먼저 선택하세요."); return; }
  const r = await fetch(`/jobs/${S.job.id}/rows/${S.sel}/copy`, { method: "POST" });
  if (!r.ok) { alert("복사 실패"); return; }
  clearFiltersForNewRow();
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

/* ---------------- error reports ----------------
 *
 * A report asks a person for two things: which axis is wrong, and one line
 * saying why or what the right value is.  Everything else - the drawing, the
 * page, the coordinates, the TYPE and tag, the whole judgement evidence, the
 * rules that fired, the engine's values and the reviewer's - is taken by the
 * server at the moment the button is pressed.  It is shown in the dialog so the
 * reporter can see what is going with it, and it is not editable: it is what the
 * engine said, and letting it be rewritten would turn the record into a story.
 */
const REPORT_WHAT = [
  ["SCOPE", "Scope 판정"], ["QTY", "Q'ty"], ["TYPE", "Type / Valve Type"],
  ["DESCRIPTION", "Description"], ["OTHER", "기타"],
];

function closeModal() {
  $("#modal").classList.add("hidden");
  $("#modal-body").innerHTML = "";
}
$req("#modal").addEventListener("click", ev => {
  if (ev.target.id === "modal") closeModal();
});
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && !$("#modal").classList.contains("hidden")) closeModal();
});

function openModal(title, html) {
  $("#modal-title").textContent = title;
  $("#modal-body").innerHTML = html;
  $("#modal").classList.remove("hidden");
}

/* What the report will carry, written out before it is sent.  Read off what the
 * screen already has, so the dialog opens without a round trip; the server
 * captures the same facts again from its own copy when it stores the record. */
function reportPreview(opts) {
  const row = opts.rowKey && S.rows.find(r => r.key === opts.rowKey);
  const pg = S.pages.find(p => p.page_no === (opts.pageNo || (row || {}).page_no)) || {};
  const pairs = [];
  const add = (k, v) => { if (v !== undefined && v !== null && v !== "") pairs.push([k, v]); };
  add("도면", `${pg.drawing_no || "(도면번호 없음)"} · p${opts.pageNo || (row || {}).page_no || "?"}`);
  if (row) {
    add("좌표", (row.rect || []).map(v => Math.round(v)).join(", ") || "좌표 없음");
    add("Type", row.values.type || row.values.valve_type || "(없음)");
    add("Tag No.", row.values.tag_no || "(미부여)");
    add("Q'ty · Scope", `${row.values.qty ?? ""} · ${row.values.scope || ""}`);
    add("Description", row.values.description || "(비어 있음)");
    add("적용 규칙", (row.evidence.rules_hit || []).join(", ") || "제외 규칙 해당 없음");
    const edited = Object.entries(row.user || {}).filter(([, v]) => v !== null);
    add("사람이 고친 값", edited.map(([f, v]) => `${f} = ${v}`).join(" | ") || "없음");
  }
  if (opts.point) {
    add("클릭 위치", opts.point.map(v => Math.round(v)).join(", "));
    add("검출", "이 위치에는 검출된 항목이 없습니다 — 주변 도형을 함께 저장합니다");
  }
  add("판정 지문", (S.job && S.job.fingerprint || "").slice(0, 8) || "(없음)");
  return `<div class="rep-auto"><b class="muted">함께 저장되는 내용 (자동)</b><dl>`
    + pairs.map(([k, v]) => `<dt>${k}</dt><dd>${escape(String(v))}</dd>`).join("")
    + `</dl></div>`;
}

function reportDialog(opts) {
  const title = opts.rowKey ? "오류 신고 — 이 행"
    : opts.point ? "오류 신고 — 검출되지 않은 위치" : "오류 신고";
  openModal(title,
    `<p class="muted">두 가지만 적으시면 됩니다.</p>
     <b>무엇이 틀렸습니까</b>
     <div class="rep-what">${REPORT_WHAT.map(([v, l], i) =>
       `<label><input type="radio" name="rep-what" value="${v}"${i === 0 && !opts.what ? " checked" : (opts.what === v ? " checked" : "")}>${l}</label>`).join("")}</div>
     <b>왜 틀렸습니까 / 올바른 값</b>
     <input id="rep-detail" type="text" class="rep-detail" placeholder="한 줄로 적어 주세요" value="${escape(opts.detail || "")}">
     ${reportPreview(opts)}
     <div class="modal-actions">
       <button id="rep-cancel" class="ghost">취소</button>
       <button id="rep-save">신고 접수</button>
     </div>`);
  $("#rep-detail").focus();
  $("#rep-cancel").onclick = closeModal;
  const save = async () => {
    const what = (document.querySelector('input[name="rep-what"]:checked') || {}).value;
    const detail = $("#rep-detail").value.trim();
    if (!detail) { alert("왜 틀렸는지 한 줄만 적어 주세요."); return; }
    const body = {
      kind: opts.point ? "MISSED" : (opts.fromDrawing ? "SYMBOL" : "ROW"),
      what, detail, row_key: opts.rowKey || "",
      page_no: opts.pageNo || null, point: opts.point || null,
    };
    const r = await fetch(`/jobs/${S.job.id}/reports`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) { alert((await r.json()).detail || "신고 저장 실패"); return; }
    S.reports = (await r.json()).report_count;
    updateReportBadge();
    closeModal();
  };
  $("#rep-save").onclick = save;
  $("#rep-detail").addEventListener("keydown", ev => {
    if (ev.key === "Enter") { ev.preventDefault(); save(); }
  });
}

function updateReportBadge() {
  const n = $("#report-n");
  if (!n) return;
  n.textContent = S.reports || 0;
  n.classList.toggle("zero", !S.reports);
}

async function loadReports() {
  if (!S.job) return { count: 0, reports: [] };
  const out = await (await fetch(`/jobs/${S.job.id}/reports`)).json();
  S.reports = out.count;
  updateReportBadge();
  return out;
}

/* The list screen: read it back, fix a wording, withdraw one.  The capture is
 * shown but never editable - see the note on the dialog. */
async function showReportList() {
  const out = await loadReports();
  const labels = out.labels || {};
  const body = out.reports.length
    ? out.reports.map(r => {
        const cap = r.capture || {};
        const ident = (cap.row || {}).identity || {};
        const where = `${r.drawing_no || "(도면번호 없음)"} · p${r.page_no ?? "?"}`
          + (ident.type ? ` · ${ident.type}` : "")
          + (r.kind === "MISSED" ? " · 미검출 위치" : "");
        return `<div class="rep-row" data-id="${r.id}">
          <div><b>${escape(labels[r.what] || r.what)}</b> — ${escape(r.detail)}
            <div class="meta">${escape(where)} · ${new Date(r.created_at * 1000)
              .toLocaleString("ko-KR")}</div></div>
          <div class="acts">
            <button class="ghost mini rep-edit">수정</button>
            <button class="ghost mini rep-del">삭제</button>
          </div></div>`;
      }).join("")
    : `<p class="muted">접수된 신고가 없습니다.</p>`;
  openModal(`오류 신고 ${out.count}건`,
    body + `<div class="modal-actions"><button id="rep-close" class="ghost">닫기</button></div>`);
  $("#rep-close").onclick = closeModal;
  document.querySelectorAll(".rep-del").forEach(b => b.onclick = async (ev) => {
    const id = ev.target.closest(".rep-row").dataset.id;
    if (!window.confirm("이 신고를 삭제할까요?")) return;
    await fetch(`/reports/${id}`, { method: "DELETE" });
    showReportList();
  });
  document.querySelectorAll(".rep-edit").forEach(b => b.onclick = async (ev) => {
    const id = ev.target.closest(".rep-row").dataset.id;
    const rec = out.reports.find(r => String(r.id) === String(id));
    const detail = window.prompt("사유 / 올바른 값", rec.detail);
    if (detail === null) return;
    await fetch(`/reports/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ detail }),
    });
    showReportList();
  });
}

$req("#report-list").addEventListener("click", showReportList);

/* ---------------- diagnostic export ----------------
 * Built on this machine, written beside the data, and downloaded from there.
 * Nothing leaves the PC until the person saves the file somewhere themselves. */
$req("#diag").addEventListener("click", async () => {
  const btn = $("#diag");
  btn.disabled = true;
  btn.textContent = "만드는 중…";
  try {
    const r = await fetch(`/jobs/${S.job.id}/diagnostic`, { method: "POST" });
    if (!r.ok) { alert("진단 파일을 만들지 못했습니다."); return; }
    const out = await r.json();
    const mb = (out.bytes / 1048576).toFixed(2);
    const c = out.counts || {};
    openModal("진단 내보내기",
      `<p><b>${escape(out.filename)}</b> — ${mb} MB (${out.bytes.toLocaleString()} bytes)</p>
       <div class="rep-auto"><b class="muted">담긴 것</b><dl>
         <dt>신고</dt><dd>${c.reports ?? 0}건</dd>
         <dt>분석 결과</dt><dd>${c.rows ?? 0}행 · ${c.pages ?? 0}장</dd>
         <dt>사용자 수정</dt><dd>${c.edits ?? 0}건</dd>
         <dt>수정 이력</dt><dd>${c.feedback ?? 0}건</dd>
         <dt>유도된 layout</dt><dd>이 PDF 에서 실측 ${c.derived_layout_measured ?? 0}개 ·
           프로필을 덮어쓴 값 ${c.derived_layout_applied ?? 0}개</dd>
         <dt>그 밖에</dt><dd>applied_rules · fingerprint · 버전 · 빌드일 · logs/server.log</dd>
       </dl></div>
       <div class="rep-auto"><b class="muted">빠진 것 (의도적으로)</b>
         <ul>${(out.excluded || []).map(x => `<li>${escape(x)}</li>`).join("")}</ul></div>
       <div class="modal-actions">
         <button id="diag-close" class="ghost">닫기</button>
         <a id="diag-dl" class="ghost" style="padding:4px 14px;border:1px solid var(--line);border-radius:6px;text-decoration:none;color:inherit"
            href="/jobs/${S.job.id}/diagnostic/${encodeURIComponent(out.filename)}"
            download="${escape(out.filename)}">저장</a>
       </div>`);
    $("#diag-close").onclick = closeModal;
  } finally {
    btn.disabled = false;
    btn.textContent = "진단 내보내기";
  }
});

/* ---------------- which build this is ---------------- */
(async () => {
  try {
    const v = await (await fetch("/version")).json();
    $("#build-text").textContent =
      `v${v.version} · ${v.built_at || "날짜 없음"}`
      + (v.kind === "exe" ? "" : " (source)");
    $("#build-text").title =
      `버전 ${v.version} · 빌드일 ${v.built_at} (${v.dated}) · Python ${v.python}`;
  } catch (e) { /* the footer is a label, not a feature */ }
})();
