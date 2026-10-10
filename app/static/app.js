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
  // hotfix38 — 개정 상태 열 (추가 · 수정 · 삭제 후보 · 삭제 확정).  값은 행의
  // `rev.state` 에서 `revLabel()` 이 만든다 — 줄 색·＋ 기호와 같은 접근자다.
  // 열이라서 필터·검색이 걸린다 (사용자 요구: 삭제를 "필터 걸어서 확인").
  ["rev_state", "개정", false],
  // hotfix35 — Tag No. 는 Type 바로 옆이다.  열은 처음부터 있었지만 열 번째라
  // 오른쪽 목록을 좁게 쓰면 가로 스크롤 밖에 있었다 (QFE p46 사진).  값은 행의
  // `values.tag_no` 그대로이고(1급 태그 · 마크업 · 편집), 자리만 옮긴다.
  ["type", "Type", true], ["tag_no", "Tag No.", true],
  // hotfix36 — 탭한 배관의 라인 번호 (도면의 깃발 라벨 · 지문 밖 · 편집 가능).
  ["line_no", "Line No.", true], ["line_size", "Line Size", true], ["valve_type", "Valve Type", true],
  ["qty", "Q'ty", true], ["system", "System", true],
  ["vendor_supply", "Vendor", true], ["scope", "Scope", true],
  ["description", "Description", true],
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
  // 44회차 — 마크업 모드.  `rowByKey` 는 오버레이가 행 상태(추가·오검출)를
  // 키로 찾는 지도이고 `markupSummary` 는 서버 집계(`GET /jobs/{id}/markup`).
  markup: false, rowByKey: {}, markupSummary: null,
  // 56회차 — Shift 로 도면 위에서 여러 개를 고른 것.  `sel` 은 그대로 **하나**다
  // (근거 패널 · 배관 추적 · 가운데 맞추기가 전부 한 행을 전제한다).  여럿은
  // *공급 주체를 한 번에 바꾸는* 일에만 쓰이므로 자기 칸에 따로 둔다.
  multi: new Set(),
  reasonFilter: "",
  // The review filters.  They stack: axis narrows to a decision, code to one
  // reason inside it, and the tab / drawing / grade are the axes the grid
  // already had.  All of them ride in the URL so a reload or a shared link
  // lands on the same view.
  axis: "", code: "", drawing: "", onlyReview: false, review: null,
  // 프로젝트와 리비전.  `rev` 는 이 분석의 대조 결과 요약이다.
  project: "", projects: [], rev: null, onlyChanged: false, setupDone: false,
  deletedRows: [], revByKey: {}, loading: false,
  // hotfix39 — 직전/현재 결과 전환.  `viewCache` 는 job id → 그 결과의 화면 상태 전부.
  viewCache: {}, revPair: null,
  // hotfix40 — 나란히 보기 (왼쪽 최신 Rev · 오른쪽 직전 Rev 도면).  `cmp` 는 job id → 이전 결과의 장·층.
  side: false, cmp: {},
  pageCount: null, sheetTargets: null,
  // Which trace layers the reviewer switched off: pipe | up | down | break.
  trOff: new Set(),
};

/* hotfix50 — 부서 대시보드 안에서 열릴 때 (주소 뒤 `?embed=1&mode=bid|epc&user=이름`).
 * 대시보드가 iframe 으로 띄우며 넘기는 세 값을 **한 번** 읽는다.  읽기만 하고 판정은 하지 않는다:
 *   embed=1  — 이 화면의 왼쪽 메뉴를 숨긴다 (대시보드 메뉴가 이미 왼쪽에 있다)
 *   mode     — 새 프로젝트를 입찰(bid) / 실행(epc · run) 으로 시작한다 (이미 있는 프로젝트의 선언은 안 건드린다)
 *   user     — 편집 · 저장 기록의 이름 (대시보드에 적은 이름 · 자칭이라는 사실은 그대로다)
 * 해시(#job?tab=…)는 화면 상태이고 이 값들은 주소의 query 에 있어 화면을 오가도 남는다. */
const EMBED = (function readEmbed() {
  let q;
  try { q = new URLSearchParams(location.search); } catch (e) { q = new URLSearchParams(""); }
  const m = (q.get("mode") || "").trim().toLowerCase();
  const mode = m === "bid" ? "bid" : (m === "epc" || m === "run") ? "epc" : "";
  return { on: q.get("embed") === "1", mode, user: (q.get("user") || "").trim().slice(0, 40) };
})();

/* hotfix68 — 듀얼 모니터.  이 창이 도면만 / 목록만 보이는 **새 창**으로 열렸는가 (`?pane=drawing|list&link=…`).
 * 새 창도 같은 화면 전체를 싣는다 — 기능을 다시 만들지 않고 보이는 칸만 고른다.  두 창은 `link` 로 이름 붙인
 * BroadcastChannel 하나로 선택 · 편집 · 결과 전환을 주고받는다 (아래 "도면 · 목록을 새 창으로").
 * BOOT_JOB — 주소가 결과(#job)를 가리키며 열렸다.  첫 화면 목록·위생 감사는 결과를 다 연 **뒤**에 읽는다
 * (서버에서 `/home`·`/audit` 이 `/rows` 와 CPU 를 다퉜다 — QFE 실측 각 0.17 · 0.19초). */
const PANE = (function readPane() {
  let q;
  try { q = new URLSearchParams(location.search); } catch (e) { q = new URLSearchParams(""); }
  const r = (q.get("pane") || "").toLowerCase();
  return { role: r === "drawing" || r === "list" ? r : "",
           link: (q.get("link") || "").replace(/[^A-Za-z0-9]/g, "").slice(0, 24) };
})();
const BOOT_JOB = location.hash.length > 1;
const _afterOpen = [];
let _afterOpenDone = false;
function afterFirstOpen(fn) {
  // 결과를 열며 시작한 창은 첫 결과가 선 뒤에, 아니면 바로.  새 창(PANE)은 첫 화면을 쓰지 않으므로 아예 안 읽는다.
  if (PANE.role) return;
  if (!BOOT_JOB || _afterOpenDone) { fn(); return; }
  _afterOpen.push(fn);
}
function _runAfterOpen() {
  if (_afterOpenDone) return;
  _afterOpenDone = true;
  for (const fn of _afterOpen.splice(0)) { try { fn(); } catch (e) { /* 부가 정보 — 화면을 막지 않는다 */ } }
}
if (BOOT_JOB) setTimeout(_runAfterOpen, 6000);     // 결과가 끝내 안 열려도(분석 중 · 실패) 첫 화면 정보는 읽는다
// 두 창의 연동 상태 — 함수들은 파일 끝 "도면 · 목록을 새 창으로" 에 있다 (여기 두는 것은 부팅 중에 불릴 수 있어서).
const SYNC = { link: "", peer: null, peerRole: "", poll: 0, muted: 0, selQueued: false, alone: false,
               me: Math.random().toString(36).slice(2, 10),
               dirty: { keys: new Set(), all: false, t: 0 } };

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
  const fs = [...ev.dataTransfer.files];
  if (fs.length) upload(fs);
});
$("#file").addEventListener("change", ev => {
  const fs = [...ev.target.files];
  if (fs.length) upload(fs);
});

/* 55회차 — 입력 종류.  서버는 파일이 말하는 종류로 가르므로 여기서는 받는 파일
 * 종류(accept · multiple)와 안내 문장만 바꾼다.  DXF 는 zip 하나 또는 .dxf 여러 장. */
function inputKind() {
  const r = document.querySelector('input[name="input_kind"]:checked');
  return r ? r.value : "PDF";
}
document.querySelectorAll('input[name="input_kind"]').forEach(r => r.addEventListener("change", () => {
  const dxf = inputKind() === "DXF";
  const f = $("#file");
  f.accept = dxf ? ".dxf,.zip,application/zip" : "application/pdf,.pdf";
  f.multiple = dxf;
  $("#drop-head").textContent = dxf ? "여기에 DXF zip 하나 또는 .dxf 여러 장을 놓으세요"
                                    : "여기에 PDF 를 놓으세요";
}));

/* 왼쪽 단이 정해졌는가.  정해질 때까지 오른쪽은 잠겨 있고, 왜 잠겼는지를 쓴다. */
function setSetupDone(done, why) {
  S.setupDone = !!done;
  dropZone.classList.toggle("disabled", !S.setupDone);
  $("#file").disabled = !S.setupDone;
  const lock = $("#drop-lock");
  lock.textContent = why || "";
  lock.classList.toggle("hidden", S.setupDone);
}

async function upload(files) {
  const fd = new FormData();
  const list = Array.isArray(files) ? files : [files];
  for (const f of list) fd.append("pdf", f);        // 필드 이름은 옛 것 그대로 — 서버가 종류를 가른다
  fd.append("input_kind", inputKind());
  // 프로젝트를 고른 경우에만 실린다.  안 고르면 예전과 같은 한 번짜리 분석.
  if (S.project) {
    fd.append("project", S.project);
    fd.append("compared_with", $("#rev-base").value || "");
  } else if (S.mode) {
    fd.append("mode", S.mode);              // 프로젝트 없는 분석의 선언
  }
  // hotfix73 — 서버가 JSON 아닌 응답(프록시 오류 · 500 HTML)을 주거나 연결이 끊겨도
  // 조용히 멈추지 않는다.  사유 문장은 서버가 쓴 것(`detail`)을 그대로 보인다.
  let r;
  try {
    r = await fetch("/jobs", { method: "POST", body: fd });
  } catch (e) {
    alert("서버에 올리지 못했습니다 — 서버가 꺼져 있거나 연결이 끊겼습니다. 잠시 뒤 다시 시도해 주세요.");
    return;
  }
  if (!r.ok) {
    let why = "";
    try { why = (await r.json()).detail || ""; } catch (e) { why = ""; }
    alert(why || `업로드 실패 (서버 응답 ${r.status})`);
    return;
  }
  const job = await r.json();
  // hotfix74 — 같은 파일(바이트까지 같음)을 이미 분석한 적이 있으면 말한다.  막지는 않는다.
  if (job.duplicate_of) {
    const d = job.duplicate_of;
    const where = d.project ? `${d.project} ${d.revision || ""}`.trim() : "프로젝트 없이 올린 분석";
    alert(`이 파일은 이미 분석한 적이 있습니다 — ${where} (${d.pdf_name}) 와 바이트까지 같습니다.\n`
      + (job.project && d.project === job.project
         ? `개정본을 올리려던 것이라면 파일을 확인해 주세요.  분석은 그대로 ${job.revision} 로 진행합니다.`
         : "분석은 그대로 진행합니다."));
  }
  watch(job.job_id, job.page_count, job);
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
    + list.map(p => `<option value="${escape(p.name)}">${escape(projectOptionText(p))}</option>`).join("");
  pick.value = select != null ? select : "__unset__";
  chooseProject(pick.value);
}

/* 38회차 — 입찰 / 실행 선언.  프로젝트가 있으면 장부에 저장(작성자 함께)하고
 * 없으면 이번 업로드에만 실린다.  방법은 하나(1급 경로 켜고 끄기)라 화면도
 * 라디오 하나다.  "자동" 은 선언을 비우는 것이지 세 번째 방법이 아니다. */
const MODE_WORD = { "": "자동", bid: "입찰", epc: "실행" };
const MODE_NOTE = {
  "": "자동 — 태그가 인쇄된 장이 있으면 실행, 없으면 입찰로 읽고 그렇게 적습니다.",
  bid: "입찰 — 태그가 인쇄되지 않은 도면. 범례·NOTES·기하로 식별합니다 (태그가 보이면 결과 화면이 말합니다).",
  epc: "실행 — 태그가 인쇄된 도면. 태그로 귀속하고 범례·NOTES 도 함께 씁니다 (SCOPE·수량은 여전히 별표·NOTES).",
};
/* hotfix60 — 프로젝트의 도면 종류를 **눈에 띄게** 적는다 (사용자: *"새 프로젝트를 누르고 입찰/실행을 누르면
 * 그 프로젝트가 입찰인지 실행인지 명확하게 선정된 타입을 표기"*).  읽는 곳은 장부의 `p.mode` 하나이고
 * (38회차 PATCH 가 적는 그 값), 첫 화면 설정 카드 · 프로젝트 고르는 상자 · 저장된 프로젝트 목록 ·
 * 왼쪽 메뉴가 같은 `modeChip` 을 쓴다. */
function projectMode(p) {
  const v = (p && p.mode && p.mode.value) || "";
  return v === "run" ? "epc" : v;
}
function modeChip(v, opts = {}) {
  const word = v === "bid" ? "입찰" : v === "epc" ? "실행" : "자동";
  const tip = v ? `${word} 프로젝트로 선언됨` : "선언 없음 — 도면에 태그가 인쇄됐는지로 정합니다";
  return `<span class="mode-chip ${v || "auto"}${opts.big ? " big" : ""}" title="${escape(tip)}">`
    + `${word}${opts.big && v ? " 프로젝트" : ""}</span>`;
}
function renderProjectType() {
  const box = $("#proj-type");
  if (!box) return;
  const creating = !$("#proj-new").classList.contains("hidden");
  const p = S.projects && S.projects.find(x => x.name === S.project);
  if (creating) {
    const v = modeRadio() ? modeRadio().value : "";
    box.innerHTML = `새 프로젝트 도면 종류 ${modeChip(v, { big: true })}`
      + `<span class="muted small"> — 아래에서 고르면 [만들기] 때 함께 저장합니다</span>`;
    box.classList.remove("hidden");
    return;
  }
  if (!p) { box.innerHTML = ""; box.classList.add("hidden"); return; }
  const v = projectMode(p);
  const m = p.mode || {};
  const who = v ? [m.author ? `${escape(m.author)}` : "", m.set_at ? escape(whenWords(m.set_at)) : ""].filter(Boolean).join(" · ") : "";
  box.innerHTML = `${escape(p.name)} 도면 종류 ${modeChip(v, { big: true })}`
    + `<span class="muted small"> ${v ? `— 선언됨${who ? " (" + who + ")" : ""} · 다음 분석부터 적용` : "— 선언 없음 · 태그가 인쇄된 장이 있으면 실행, 없으면 입찰로 읽습니다"}</span>`;
  box.classList.remove("hidden");
}

function modeRadio() { return document.querySelector('input[name="mode"]:checked'); }
function showMode(v) {
  const r = document.querySelector(`input[name="mode"][value="${v || ""}"]`);
  if (r) r.checked = true;
  $("#mode-note").textContent = MODE_NOTE[v || ""];
}
document.querySelectorAll('input[name="mode"]').forEach(r => r.addEventListener("change", async () => {
  const v = modeRadio().value;
  S.mode = v;
  $("#mode-note").textContent = MODE_NOTE[v];
  // hotfix60 — 새 프로젝트 이름을 적는 중이면 **고른 프로젝트가 아니라 만들 프로젝트**의 종류다.
  // 예전에는 여기서 앞서 고른 다른 프로젝트의 선언을 바꿨고, [만들기] 뒤 라디오가 '자동' 으로
  // 되돌아가 고른 종류가 사라졌다.
  if (!$("#proj-new").classList.contains("hidden")) { renderProjectType(); return; }
  const p = S.projects && S.projects.find(x => x.name === S.project);
  if (!p) { renderProjectType(); return; }   // 프로젝트 없으면 업로드에만 실린다
  const author = await askAuthor(`${p.name} 도면 종류 → ${MODE_WORD[v]}`);
  if (author === null) { showMode(p.mode && p.mode.value || ""); S.mode = p.mode && p.mode.value || ""; return; }
  const fd = new FormData(); fd.append("mode", v); fd.append("author", author || "");
  const res = await fetch(`/projects/${encodeURIComponent(p.name)}/mode`, { method: "PATCH", body: fd });
  if (!res.ok) { $("#mode-note").textContent = "저장하지 못했습니다."; return; }
  const meta = await res.json();
  p.mode = meta.mode || null;
  $("#mode-note").textContent = MODE_NOTE[v] + (v ? ` 저장됨 — 다음 분석부터 적용` : " 선언을 지웠습니다 — 다음 분석부터 자동");
  refreshProjectLabels();
  revSummary(p, nextRev(p));
}));

/* 선언이 바뀌면 그 프로젝트가 보이는 곳(고르는 상자 · 목록 · 메뉴)을 같은 값으로 다시 적는다. */
function refreshProjectLabels() {
  const pick = $("#proj-pick");
  for (const o of pick.options) {
    const p = (S.projects || []).find(x => x.name === o.value);
    if (p) o.textContent = projectOptionText(p);
  }
  renderProjectType();
  listHome();
}
function projectOptionText(p) {
  const v = projectMode(p);
  return `${p.name} — ${v === "bid" ? "입찰" : v === "epc" ? "실행" : "자동"} · 다음 ${nextRev(p)}`;
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
    renderProjectType();
    return;
  }
  if (!p) {                                 // 프로젝트 없이 한 번만
    box.classList.add("hidden");
    $("#rev-note").textContent = "";
    $("#proj-msg").textContent = "프로젝트 없이 한 번만 분석합니다 — 개정 대조 없음";
    if (EMBED.mode) { S.mode = EMBED.mode; showMode(S.mode); }   // hotfix50 — 대시보드 메뉴가 정한 종류
    setSetupDone(true);
    renderProjectType();
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
  // 이 프로젝트의 선언을 라디오에 보인다 — 개정본은 같은 값을 승계한다.
  S.mode = projectMode(p);
  showMode(S.mode);
  setSetupDone(true);
  revSummary(p, next);
  renderProjectType();
}

/* 선택 결과 한 줄.  고르기 전에도, 고른 뒤에도 늘 보인다. */
function revSummary(p, next) {
  const base = $("#rev-base");
  const target = base.value;
  const v = projectMode(p);
  const kind = v === "bid" ? "입찰 프로젝트" : v === "epc" ? "실행 프로젝트" : "자동(도면이 정함)";
  $("#proj-msg").textContent = (target
    ? `이 PDF 는 ${p.name} 의 ${next} 가 됩니다 — 비교 대상 ${target}`
    : `이 PDF 는 ${p.name} 의 ${next} 가 됩니다 (비교 대상 없음)`) + ` · ${kind}`;
}
$req("#rev-base").addEventListener("change", () => {
  const p = S.projects.find(x => x.name === S.project);
  if (p) revSummary(p, nextRev(p));
});

$req("#proj-pick").addEventListener("change", ev => chooseProject(ev.target.value));
$req("#proj-new-btn").addEventListener("click", () => {
  $("#proj-new").classList.remove("hidden");
  // hotfix60 — 새 프로젝트의 종류는 대시보드 메뉴가 정했으면 그것, 아니면 자동에서 시작한다
  // (앞서 고른 다른 프로젝트의 선언이 라디오에 남아 새 프로젝트로 옮겨 붙지 않게).
  S.mode = EMBED.mode || "";
  showMode(S.mode);
  renderProjectType();
  $("#proj-name").focus();
});

/* 같은 이름이 이미 있으면 **적기 전에** 알린다 (13회차 [C]).
 *
 * 서버는 예전부터 409 로 거절해 왔다 - 덮어쓰지 않는 것이 맞다.  문제는 그
 * 사실을 [만들기] 를 누른 뒤에야 알게 되는 것이고, 진짜 하려던 일이 대개
 * "그 프로젝트에 개정본을 더하는 것" 이라는 점이다.  그래서 막지 않고
 * **그쪽으로 가는 버튼을 같이 준다.**  §7.3 의 안정 ID 계보가 프로젝트
 * 단위 약속이므로, 같은 도면을 새 이름으로 또 올리면 계보가 갈라진다. */
function sameNameHint() {
  const typed = $("#proj-name").value.trim().toLowerCase();
  const box = $("#proj-dup");
  const hit = (S.projects || []).find(p => (p.name || "").toLowerCase() === typed);
  if (!typed || !hit) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  const n = (hit.revisions || []).length;
  box.innerHTML =
    `<b>${escape(hit.name)}</b> 프로젝트가 이미 있습니다 (리비전 ${n}개). `
    + `같은 이름으로 새로 만들 수는 없습니다 — 기존 것을 덮어쓰지 않기 때문입니다.`
    + `<button type="button" id="proj-dup-use">그 프로젝트에 개정본으로 추가</button>`;
  box.classList.remove("hidden");
  $("#proj-dup-use").onclick = () => {
    $("#proj-new").classList.add("hidden");
    box.classList.add("hidden");
    $("#proj-pick").value = hit.name;
    chooseProject(hit.name);
  };
}
$req("#proj-name").addEventListener("input", sameNameHint);
$req("#proj-cancel").addEventListener("click", () => {
  $("#proj-new").classList.add("hidden");
  $("#proj-msg").textContent = "";
  chooseProject($("#proj-pick").value);      // 고른 프로젝트의 종류로 라디오·표기를 되돌린다
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
  // hotfix50 — 대시보드의 입찰 / 실행 메뉴에서 만든 프로젝트는 그 종류로 시작한다.  선언은 장부에
  // 작성자와 함께 적히고(38회차 PATCH 그대로) 화면 라디오로 언제든 바꿀 수 있다.
  // hotfix60 — 이름을 적는 동안 라디오에서 고른 종류가 먼저다 (사람이 이 화면에서 고른 것).
  const chosen = (modeRadio() && modeRadio().value) || EMBED.mode || "";
  $("#proj-new").classList.add("hidden");
  $("#proj-name").value = "";
  if (chosen && !(out.mode && out.mode.value)) {
    // 이 화면에서 고른 종류는 누가 정했는지 적는다 (라디오를 바꿀 때와 같은 확인 줄).  대시보드 메뉴가
    // 정한 종류는 `?user=` 가 이미 이름을 채워 두었다.
    let who = lastAuthor() || "";
    if (!EMBED.mode || modeRadio().value !== EMBED.mode) {
      const a = await askAuthor(`새 프로젝트 ${out.name} — ${MODE_WORD[chosen] || chosen}`);
      if (a !== null) who = a;
    }
    const fm = new FormData(); fm.append("mode", chosen); fm.append("author", who);
    try { await fetch(`/projects/${encodeURIComponent(out.name)}/mode`, { method: "PATCH", body: fm }); } catch (e) {}
  }
  await loadProjects(out.name);           // 만든 프로젝트가 곧 선택이다
  const made = (S.projects || []).find(x => x.name === out.name);
  if (made) editNotice(`${made.name} 프로젝트를 ${projectMode(made) === "bid" ? "입찰" : projectMode(made) === "epc" ? "실행" : "자동(도면이 정함)"}으로 만들었습니다`);
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

/* 위생 경고가 가리키는 것이 **무엇인지** — 서버가 이미 내고 있던 값만 편다.
 * 판정을 여기서 새로 하지 않는다 (문장은 `audit.summary` 가 쥔다). */
function auditDetail(a) {
  const out = [];
  const rows = a.hand_added || [];
  if (rows.length) {
    const li = rows.map(r => {
      const who = r.author ? `${escape(r.author)}${r.at ? " · " + escape(r.at.slice(0, 10)) : ""}`
                           : "작성자 기록 없음 (마크업 이전에 만든 행)";
      const what = [r.type, r.scope].filter(Boolean).map(escape).join(" · ");
      return `<li>${escape(r.pdf_name)}${r.project ? " · " + escape(r.project) : ""}`
        + ` · p${r.page_no} · ${what || "값 없음"} · ${who}`
        + `${r.reason_class ? " · " + escape(r.reason_class) : ""}</li>`;
    }).join("");
    out.push(`<div class="audit-detail"><b>도면 근거 없는 행 ${rows.length}</b>`
      + `<ul>${li}</ul>`
      + `<p>사람이 넣은 행입니다 — 검토자가 추가한 것이면 그대로 두고, `
      + `시험 흔적이면 그 분석에서 지우십시오. 산출물에는 REMARK 에 `
      + `<i>사용자 추가</i> 로 나갑니다.</p></div>`);
  }
  const L = a.leftovers || {};
  const files = [["고아 출력", L.orphan_outputs], ["고아 업로드", L.orphan_uploads],
                 ["고아 진단", L.orphan_diagnostics], ["고아 그림 캐시", L.orphan_page_cache]]
    .filter(([, v]) => (v || []).length);
  if (files.length) {
    out.push(`<div class="audit-detail">` + files.map(([name, v]) =>
      `<b>${name} ${v.length}</b><ul>`
      + v.map(x => `<li>${escape(x)}</li>`).join("") + `</ul>`).join("")
      + `<p>어느 분석도 가리키지 않는 파일입니다. 디스크만 차지하고 결과에는 `
      + `닿지 않습니다 — 지우는 것은 되돌릴 수 없으므로 확인 뒤 손으로 지우거나, `
      + `그 프로젝트를 삭제할 때 함께 지워집니다.</p></div>`);
  }
  return out.join("");
}

async function showAudit() {
  try {
    const a = await (await fetch("/audit")).json();
    const box = $("#audit-line");
    // "산출 대상 N행 / job M개" 는 규모이지 이상이 아니다.
    const bad = auditProblems(a.lines).filter(t => !/^산출 대상|^job /.test(t));
    const full = `<div class="audit-full">`
      + a.lines.map(l => `<div>${escape(l)}</div>`).join("") + `</div>`;
    // 46회차 — 합계 옆에 **무엇인지**를 적는다.  서버가 이미 job 단위 개수와
    // 고아 파일 이름을 내고 있었는데(`provenance.jobs`·`leftovers.orphan_*`)
    // 화면이 총계만 보여, 팀원이 "5행" 을 보고도 확인할 길이 없었다.
    const detail = auditDetail(a);
    DASH.audit = { bad: bad.length, lines: a.lines || [] };
    renderDashboard();
    box.innerHTML = bad.length
      ? `<details class="audit" open><summary>데이터 위생 — 확인할 항목 `
        + `${bad.length}건</summary>${full}${detail}</details>`
      : `<details class="audit"><summary>데이터 위생 — 이상 없음`
        + `</summary>${full}${detail}</details>`;
  } catch (e) { /* 감사는 부가 정보다 - 실패해도 화면을 막지 않는다 */ }
}
loadProjects();
afterFirstOpen(showAudit);

/* 이전 분석 한 줄: 상태 · 장수 · 걸린 시간.  전부 저장된 값이다. */
/* 분석 상태의 화면 말.  **모르는 값은 그대로 쓴다** - 없는 뜻을 지어내지
 * 않는다.  `cancelled` 가 12회차에 생겼는데 이 표에 빠져 있어서 첫 화면에
 * 영어로 나가고 있었다 (13회차 조사가 잡았다). */
const JOB_STATUS_KO = {
  done: "완료", failed: "실패", cancelled: "취소됨",
  running: "분석 중", queued: "차례 기다리는 중",
};

function whenWords(ts) {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  const p = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} `
    + `${p(d.getHours())}:${p(d.getMinutes())}`;
}

function jobLine(j) {
  const bits = [JOB_STATUS_KO[j.status] || j.status];
  if (j.rows) bits.push(`${j.rows}행`);
  if (j.page_count) bits.push(`${j.page_count}장`);
  if (j.analysed_at || j.finished_at || j.created_at)
    bits.push(whenWords(j.analysed_at || j.finished_at || j.created_at));
  if (j.edits) bits.push(`수정 ${j.edits}칸`);
  if (j.last_save) bits.push(saveWords(j.last_save));
  return bits.join(" · ");
}

/* hotfix23 — 최종 저장 기록 한 줄.  이름은 자기신고 (13회차) — 없으면 "이름 없음". */
function saveWords(sv) {
  if (!sv) return "";
  const what = [sv.edits ? `수정 ${sv.edits}칸` : "", sv.added ? `추가 ${sv.added}행` : "",
                sv.removed ? `삭제 ${sv.removed}행` : ""].filter(Boolean).join(" · ");
  return `최종 저장 ${whenWords(sv.at)} · ${sv.author || "이름 없음"}`
    + (what ? ` (${what})` : "");
}

/* 개정 판정 배지.  넷뿐이고 추정하지 않는다 - 못 읽으면 못 읽었다고 쓴다. */
const REV_VERDICT = {
  NEWER: ["개정본", "rv-new"],
  SAME: ["같은 개정", "rv-same"],
  OLDER: ["이전 개정", "rv-old"],
  UNKNOWN: ["개정 판별 불가", "rv-unknown"],
};

/* 이 리비전이 직전 리비전보다 나중인가.  **문서 대표 Rev 끼리** 견준다.
 * 대표값을 접는 규칙은 도면에서 유도되지 않아 config 에 있고(사용자 확정
 * `max`), 그래서 배지 옆에 그 규칙이 접기 전 무엇이었는지도 함께 적는다. */
function revVerdict(now, before) {
  const n = (now || "").trim(), b = (before || "").trim();
  if (!n) return "UNKNOWN";
  if (!b) return "";                       // 견줄 대상이 없다 - 첫 리비전
  return n > b ? "NEWER" : n === b ? "SAME" : "OLDER";
}

/* hotfix61 — 저장된 프로젝트 목록을 카드 + 리비전 타임라인으로.
 * 값은 전부 `/home` 이 이미 주는 것(상태 · 행 · 장 · 일시 · 수정 칸 · 도면 Rev)이고 새로 세는 것이 없다.
 * 직전 리비전 대비 행 수 차이만 화면에서 뺀다 (둘 다 그 응답에 있는 수). */
const fmtCount = n => Number(n || 0).toLocaleString("ko-KR");
const RV_STATUS = { done: "ok", failed: "bad", cancelled: "off", running: "live", queued: "wait" };

/* hotfix62 — 행 수가 아니라 **발주처 양식에 나가는 계기·밸브의 Q'ty 합** (`r.output.qty` — 서버가
 * Excel 출력과 같은 탭·같은 SCOPE 판정으로 센다 · 사람이 고친 Q'ty 반영).  직전 리비전 대비 차이도 그 수로. */
function qtyOf(r) { return r && r.output ? r.output.qty : null; }
function qtyDelta(now, before) {
  if (!before || before.missing || before.deleted || qtyOf(now) == null || qtyOf(before) == null) return "";
  const d = qtyOf(now) - qtyOf(before);
  if (!d) return `<em class="rv-delta same" title="직전 ${escape(before.revision || "")} 과 계기 수량이 같습니다">±0</em>`;
  return `<em class="rv-delta ${d > 0 ? "up" : "down"}" title="직전 ${escape(before.revision || "")} 대비 계기 수량">`
    + `${d > 0 ? "▲" : "▼"}${fmtCount(Math.abs(d))}</em>`;
}

/* 도면이 인쇄한 개정과 그 날짜 — `Rev.1C · 26.MAR.2026`.  날짜를 못 읽었으면 그렇게 말한다. */
const TOP_BASIS = {
  HISTORY: "도면 이력 표의 개정 순서로 정함",
  "HISTORY+DATE": "도면 이력 표의 개정 순서로 정하고, 순서를 모르는 둘은 PDF 날짜로 정함",
  RULE: "이력 표에 날짜가 글자로 없어 장마다 읽은 Rev 중 가장 앞선 것 (config revision.document_rule)",
  NONE: "개정을 읽지 못함",
};
function drawnRev(rev, date, basis) {
  if (!rev) return `<span class="rv-doc muted">도면 개정 못 읽음</span>`;
  const tip = TOP_BASIS[basis] || "";
  return `<span class="rv-doc" title="${escape(tip)}">도면 <b>Rev.${escape(rev)}</b>`
    + (date ? ` <span class="rv-date">${escape(date)}</span>`
            : ` <span class="rv-date none" title="이력 표의 날짜가 글자로 인쇄되지 않았습니다 (획으로 그린 표)">날짜 없음</span>`)
    + `</span>`;
}

function revRow(r, prevDocRev, opts = {}) {
  // 개정 판정은 서버 한 곳(`revisions.compare_document_revision`)이 — Rev 가 같으면 PDF 날짜가 정한다.
  const v = r.verdict ? r.verdict.verdict : (r.top_rev ? "" : revVerdict(r.doc_rev, prevDocRev));
  const badge = v && REV_VERDICT[v]
    ? `<span class="rvbadge ${REV_VERDICT[v][1]}" title="${escape((r.verdict && r.verdict.label) || "")}`
      + `${r.verdict && r.verdict.basis === "DATE" ? " (PDF 날짜로 판정)" : ""}">${REV_VERDICT[v][0]}</span>` : "";
  const doc = r.facts_state === "pending"
    ? `<span class="rv-doc muted">도면 정보 읽는 중…</span>`
    : drawnRev(r.top_rev || r.doc_rev, r.top_date, r.top_basis || (r.doc_rev ? "RULE" : "NONE"));
  // hotfix42 — 분석 기록이 지워진 리비전은 링크도 삭제 버튼도 없이 사실만 적는다
  if (r.missing || r.deleted) {
    const d = r.deleted || {};
    const who = d.author ? ` · ${escape(d.author)}` : "";
    const when = d.at ? ` · ${escape(whenWords(d.at))}` : "";
    return `<div class="revwrap rv-tl"><span class="revrow missing" title="이 리비전의 분석 기록은 지워졌습니다 — 안정 ID 장부와 대조 기록만 남아 있습니다">`
      + `<span class="rv-dot off"></span>`
      + `<span class="rv-name"><span class="rv-tag">${escape(r.revision)}</span> <span class="muted">분석 기록 지워짐${who}${when}</span></span>`
      + `<span class="muted small">${escape(r.pdf_name || "")}</span></span></div>`;
  }
  const st = r.status || "";
  const chips = [`<span class="rv-st ${RV_STATUS[st] || "off"}">${escape(JOB_STATUS_KO[st] || st || "—")}</span>`];
  const q = qtyOf(r);
  if (q != null) chips.push(`<span class="rv-chip qty" title="발주처 양식에 나가는 계기·밸브 ${fmtCount(r.output.rows)}행의 Q'ty 합`
    + `${r.output.qty_missing ? ` (Q'ty 빈칸 ${r.output.qty_missing}행은 0 으로 셈)` : ""}">계기 <b>${fmtCount(q)}</b>${opts.delta || ""}</span>`);
  if (r.page_count) chips.push(`<span class="rv-chip"><b>${fmtCount(r.page_count)}</b>장</span>`);
  if (r.edits) chips.push(`<span class="rv-chip edit" title="사람이 고친 칸"><b>${fmtCount(r.edits)}</b>칸 수정</span>`);
  const when = r.analysed_at || r.finished_at || r.created_at;
  if (when) chips.push(`<span class="rv-when" title="분석한 때">${escape(whenWords(when))}</span>`);
  const saved = r.last_save ? `<span class="rv-saved">${escape(saveWords(r.last_save))}</span>` : "";
  const latest = opts.latest ? `<span class="rv-latest">최신</span>` : "";
  const file = r.pdf_name ? `<span class="rv-file-sm" title="${escape(r.pdf_name)}">${escape(r.pdf_name)}</span>` : "";
  return `<div class="revwrap rv-tl${opts.latest ? " is-latest" : ""}"><a href="#${escape(r.job_id)}" class="revrow"`
    + ` title="${escape(jobLine(r))} — 눌러서 엽니다 (재분석하지 않습니다)">`
    + `<span class="rv-dot ${RV_STATUS[st] || "off"}"></span>`
    + `<span class="rv-name"><span class="rv-tag">${escape(r.revision)}</span>${latest} ${doc} ${badge}${file}</span>`
    + `<span class="rv-meta">${chips.join("")}${saved}</span>`
    + `<span class="rv-open">열기 →</span></a>`
    + delButton(r.job_id) + `</div>`;
}

/* 이전 기록 삭제 (17회차 [E]).
 *
 * ⚠ 되돌릴 수 없고, 이 호스트에는 팀원 여러 명의 프로젝트가 함께 있다.
 * 그래서 화면이 하는 일은 셋이다: (1) 지우기 **전에** 무엇이 사라지는지
 * 서버에서 받아 보여 준다, (2) 확인을 두 번 받는다 — 누른 것 + 분석 id 를
 * 그대로 옮겨 적는 것, (3) 이름을 묻는다 (13회차 자기신고 그대로, 비우면
 * 비운 채로 저장되고 화면이 "자칭" 이라고 적는다).
 *
 * 지우는 단위는 **분석 하나**다.  프로젝트 전체를 지우는 버튼은 없다 — 그
 * 폴더에 안정 ID 장부가 있고 그것이 사라지면 번호가 1부터 다시 나간다
 * (docs/round17_delete.md). */
function delButton(jobId) {
  return `<button class="ghost mini del-job" data-job="${escape(jobId)}"`
    + ` title="이 분석 기록을 지웁니다 — 되돌릴 수 없습니다">삭제</button>`;
}

/* 46회차 [C] — 프로젝트 통째 삭제.  분석 하나 삭제와 **같은 규율**이다:
 * 먼저 무엇이 사라지는지 보이고 · 이름을 옮겨 적게 하고 · 누가 지웠는지 남긴다.
 * 다른 점 하나는 **안정 ID 장부는 남는다**는 사실을 먼저 말하는 것이다 (§7.3). */
async function askDeleteProject(name) {
  let pv;
  try {
    pv = await (await fetch(`/projects/${encodeURIComponent(name)}/deletion_preview`)).json();
  } catch (e) { alert("무엇이 사라지는지 확인하지 못했습니다."); return; }
  const mine = (currentAuthor() || "").trim();   // hotfix74 — 저장소가 막힌 iframe 에서도 (읽기 예외 없음)
  const others = (pv.authors || []).filter(a => a && a !== mine);
  const bits = [
    `프로젝트  ${pv.project}`,
    `분석            ${pv.job_count}개`,
    `추출한 행        ${pv.rows}행`,
    `사람이 고친 칸    ${pv.edited_cells}칸`,
    `수정 이력        ${pv.feedback}건`,
    `산출물 스냅샷     ${pv.revision_snapshots}개`,
    `업로드 PDF       ${(pv.uploads_to_remove || []).length}개 함께 지웁니다`,
    `안정 ID 장부      남깁니다 (같은 이름으로 다시 만들면 이어받습니다)`,
  ];
  if (others.length) {
    bits.unshift(`⚠ 다른 사람이 만든 기록이 있습니다 — ${others.join(", ")}`);
  }
  if (!confirm("지우면 아래가 사라집니다. 되돌릴 수 없습니다.\n\n"
      + bits.join("\n") + "\n\n계속할까요?")) return;
  const typed = prompt("실수로 지워지지 않게, 프로젝트 이름을 그대로 옮겨 적으세요:\n"
    + pv.project);
  if (typed === null) return;
  const author = prompt("누가 지웁니까? (비워도 됩니다 — 화면이 '자칭' 이라고 적습니다)",
    mine) ?? "";
  if (author) { try { localStorage.setItem("pid.author", author); } catch (e) {} }
  const body = new FormData();
  body.append("confirm", typed);
  body.append("author", author);
  const res = await fetch(`/projects/${encodeURIComponent(name)}`, { method: "DELETE", body });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    alert(d.detail || "지우지 못했습니다.");
    return;
  }
  // 새로고침 없이 사라진다 — 목록과 고르는 상자와 위생 경고를 함께 다시 읽는다.
  await afterDelete();
}

async function askDelete(jobId) {
  let pv;
  try {
    pv = await (await fetch(`/jobs/${jobId}/deletion_preview`)).json();
  } catch (e) { alert("무엇이 사라지는지 확인하지 못했습니다."); return; }
  const bits = [
    `분석  ${pv.pdf_name}${pv.project ? `  ·  ${pv.project} ${pv.revision}` : ""}`,
    `추출한 행        ${pv.rows}행`,
    `사람이 고친 칸    ${pv.edited_cells}칸`,
    `검토 표시        ${pv.review_marks}건`,
    `수정 이력        ${pv.feedback}건`,
    `오류 신고        ${pv.reports}건`,
    `산출물 스냅샷     ${pv.revision_snapshots}개`,
    `업로드 PDF       ${pv.pdf_shared_with.length
        ? "남깁니다 (다른 분석도 같은 파일을 씁니다)" : "함께 지웁니다"}`,
    `안정 ID 장부      ${pv.id_registry}`,
  ];
  if (!confirm("지우면 아래가 사라집니다. 되돌릴 수 없습니다.\n\n"
      + bits.join("\n") + "\n\n계속할까요?")) return;
  const typed = prompt("실수로 지워지지 않게, 이 분석의 id 를 그대로 옮겨 적으세요:\n"
    + jobId);
  if (typed === null) return;
  const author = prompt("누가 지웁니까? (비워도 됩니다 — 화면이 '자칭' 이라고 적습니다)",
    currentAuthor() || "") ?? "";
  if (author) rememberAuthor(author);
  const body = new FormData();
  body.append("confirm", typed);
  body.append("author", author);
  const res = await fetch(`/jobs/${jobId}`, { method: "DELETE", body });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    alert("지우지 못했습니다: " + (d.detail || res.status));
    return;
  }
  const out = await res.json();
  alert(`지웠습니다 — ${out.rows}행 · 편집 ${out.edited_cells}칸`
    + (out.pdf_removed ? " · 업로드 PDF 도 지웠습니다" : ""));
  await afterDelete();
}

/* 53회차 [H] — 무엇을 지우든 **화면 셋을 함께** 다시 읽는다.
 *
 * 8차 피드백 s1: *"저장된 프로젝트가 삭제되면 프로젝트 선택 란에서 해당 이력도
 * 같이 삭제되어야 한다."*  원인은 분석 삭제(`askDelete`)가 `listHome()` 만
 * 부르고 고르는 상자를 그대로 둔 것이다 — 리비전을 지워도 상자는 "다음 Rev.B"
 * 라고 계속 말한다.  프로젝트 삭제 쪽은 셋을 다 부르고 있었으므로, **갈라져
 * 있던 것을 한 함수로 되돌린다** (두 벌을 두면 또 갈린다).
 *
 * 고르고 있던 프로젝트가 사라졌으면 **말없이 다른 값으로 넘어가지 않는다** —
 * `loadProjects(없는 이름)` 은 브라우저가 value 를 ""(프로젝트 없이 한 번만)로
 * 떨어뜨리므로, 사람이 고른 적 없는 설정으로 조용히 바뀐다. */
async function afterDelete() {
  const was = S.project;
  await listHome();
  const live = await (await fetch("/projects")).json();
  const still = was && live.some(p => p.name === was);
  await loadProjects(still ? was : undefined);
  if (was && !still) {
    // 고르는 상자 옆 줄에 **그 사실을 적는다** — 조용히 다른 값으로 넘어가면
    // 사람이 고르지 않은 설정으로 분석이 돌아간다.
    $("#proj-msg").textContent =
      `'${was}' 프로젝트가 없어져 선택을 지웠습니다 — 다시 고르세요.`;
  }
  await showAudit();
}

document.addEventListener("click", ev => {
  const b = ev.target.closest && ev.target.closest(".del-job");
  if (!b) return;
  ev.preventDefault();
  askDelete(b.dataset.job);
});

$req("#joblist").addEventListener("click", ev => {
  const b = ev.target.closest(".del-project");
  if (!b) return;
  ev.preventDefault();
  ev.stopPropagation();                  // <summary> 가 접히지 않게
  askDeleteProject(b.dataset.project);
});

async function listHome() {
  const home = await (await fetch("/home")).json();
  const box = $("#joblist");
  const parts = [];
  if (home.projects.length) {
    parts.push("<p class='muted small'>저장된 프로젝트 — 눌러서 다시 엽니다 "
      + "(재분석하지 않습니다)</p>");
    for (const p of home.projects) {
      const revs = p.revisions || [];
      // 최근순으로 왔으므로 "직전"은 배열의 다음 항목이다.
      const rows = revs.map((r, i) => revRow(r, (revs[i + 1] || {}).doc_rev,
        { latest: i === 0 && revs.length > 1, delta: qtyDelta(r, revs[i + 1]) })).join("");
      const last = revs.find(r => !r.missing && !r.deleted && r.status === "done") || null;
      const mode = projectMode(p);
      // hotfix62 — 제목은 **PDF 타이틀블록에 인쇄된 프로젝트 제목**.  못 읽었으면 이 프로그램의
      // 프로젝트 이름을 쓰되 그렇다고 적는다 (지어내지 않는다).
      const title = p.pdf_title || p.name;
      const titleTip = p.pdf_title ? "PDF 타이틀블록의 PROJECT NAME/TITLE 칸"
        : (p.facts_pending ? "PDF 에서 프로젝트 제목을 읽는 중" : "PDF 에서 프로젝트 제목을 읽지 못해 이 프로그램의 프로젝트 이름을 씁니다");
      const sub = [p.pdf_title ? `<span class="pj-key" title="이 프로그램에 만든 프로젝트 이름">${escape(p.name)}</span>` : "",
        revs.length ? `${revs.length}개 리비전 · 최신 <b>${escape(revs[0].revision)}</b>` : "아직 분석 없음"];
      if (last && (last.analysed_at || last.created_at)) sub.push(`마지막 분석 ${escape(whenWords(last.analysed_at || last.created_at))}`);
      if (!p.pdf_title && last) sub.push(`<span class="muted" title="${escape(titleTip)}">PDF 프로젝트 제목 ${p.facts_pending ? "읽는 중" : "못 읽음"}</span>`);
      const saved = p.last_save
        ? `<span class="saved small">${escape(saveWords(p.last_save))}`
          + `${p.last_save.revision ? ` — ${escape(p.last_save.revision)}` : ""}</span>` : "";
      const stat = (n, unit, cls = "", tip = "") => `<span class="pj-stat ${cls}"${tip ? ` title="${escape(tip)}"` : ""}>`
        + `<b>${n}</b><i>${unit}</i></span>`;
      const top = p.top;
      const stats = last
        ? (top && top.rev ? stat(`Rev.${escape(top.rev)}`, top.date ? escape(top.date) : "날짜 없음", "rev",
              `분석된 모든 PDF 중 최상위 개정 (${top.revision}) — ${TOP_BASIS[top.basis] || ""}`) : "")
          + (qtyOf(last) != null ? stat(fmtCount(qtyOf(last)), "계기", "qty",
              `최신 ${last.revision} 에서 발주처 양식에 나가는 계기·밸브 Q'ty 합 (${fmtCount(last.output.rows)}행)`) : "")
          + stat(fmtCount(last.page_count), "장")
        : "";
      const empty = revs.length ? ""
        : `<div class="pj-empty">위 <b>① 어디에 넣을지</b> 에서 이 프로젝트를 고르고 PDF 를 넣으면 `
          + `<b>${escape(p.next_revision || "Rev.A")}</b> 가 됩니다.</div>`;
      parts.push(`<details class="pjt pj-card ${mode || "auto"}" open>`
        + `<summary><span class="pj-icon" aria-hidden="true">${escape((title || "?").trim().charAt(0).toUpperCase())}</span>`
        + `<span class="pj-title"><span class="pj-line"><b class="pj-name" title="${escape(titleTip)}">${escape(title)}</b>${modeChip(projectMode(p))}</span>`
        + `<span class="pj-sub">${sub.filter(Boolean).join(" · ")}</span>${saved}</span>`
        + `<span class="pj-stats">${stats}</span>`
        + `<button class="ghost mini del-project" data-project="${escape(p.name)}"`
        + ` title="이 프로젝트를 통째로 지웁니다 — 되돌릴 수 없습니다">프로젝트 삭제</button>`
        + `</summary><div class="pj-revs">` + rows + empty + "</div></details>");
    }
  }
  if (home.loose.length) {
    parts.push(`<div class="pj-loose-head">프로젝트에 묶이지 않은 분석 <span class="pj-count">${home.loose.length}</span></div>`
      + `<div class="pj-loose">` + home.loose.map(j => {
          const st = j.status || "";
          const when = j.analysed_at || j.finished_at || j.created_at;
          return `<div class="revwrap rv-tl"><a href="#${j.id}" class="revrow loose"`
            + ` title="${escape(jobLine(j))}">`
            + `<span class="rv-dot ${RV_STATUS[st] || "off"}"></span>`
            + `<span class="rv-name"><span class="rv-file">${escape(j.pdf_title || j.pdf_name || "")}</span>`
            + (j.top_rev ? ` ${drawnRev(j.top_rev, j.top_date, j.top_basis)}` : "")
            + (j.pdf_title ? `<span class="rv-file-sm">${escape(j.pdf_name || "")}</span>` : "")
            // hotfix74 — 프로젝트 장부를 읽지 못해 여기로 떨어진 분석 (데이터 위생이 사유를 말한다)
            + (j.ledger_missing ? `<span class="rv-file-sm" style="color:#b42318">프로젝트 '${escape(j.ledger_missing)}' 장부를 읽지 못해 여기 보입니다 — 아래 데이터 위생 참고</span>` : "")
            + `</span>`
            + `<span class="rv-meta"><span class="rv-st ${RV_STATUS[st] || "off"}">${escape(JOB_STATUS_KO[st] || st)}</span>`
            + (qtyOf(j) != null ? `<span class="rv-chip qty">계기 <b>${fmtCount(qtyOf(j))}</b></span>` : "")
            + (j.page_count ? `<span class="rv-chip"><b>${fmtCount(j.page_count)}</b>장</span>` : "")
            + (j.edits ? `<span class="rv-chip edit"><b>${fmtCount(j.edits)}</b>칸 수정</span>` : "")
            + (when ? `<span class="rv-when">${escape(whenWords(when))}</span>` : "")
            + `</span><span class="rv-open">열기 →</span></a>`
            + delButton(j.id) + `</div>`;
        }).join("") + `</div>`);
  }
  box.innerHTML = parts.join("");
  // hotfix49 — 대시보드 · 왼쪽 메뉴가 같은 응답을 읽는다 (한 번 받고 둘이 쓴다)
  DASH.home = home;
  renderDashboard();
  renderNav();
  // hotfix62 — 예전 분석의 도면 사실은 서버가 뒤에서 한 번 채운다 (분석 하나 2~5초).  다 찰 때까지 가끔 다시 묻는다.
  const pending = home.projects.some(p => p.facts_pending) || (home.loose || []).some(j => j.facts_state === "pending");
  clearTimeout(listHome._t);
  if (pending) listHome._t = setTimeout(() => { if (!drop.classList.contains("hidden")) listHome(); }, 8000);
}
const listJobs = listHome;      // 예전 이름으로 부르는 곳이 있다
afterFirstOpen(listHome);

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
  const m = /^measuring sheet (\d+) of (\d+)$/.exec(msg);
  if (m) return `도면 치수를 재는 중 — ${m[1]} / ${m[2]}쪽`;
  if (/^\d+ sheets to read$/.test(msg)) return "읽을 도면을 세는 중";
  return msg;
}

/* 경과 시간 — 초마다 바뀌는 **참인 값** 하나.
 *
 * 남은 시간은 여전히 적지 않는다 (§7.2: 단계별 소요가 60배까지 차이나므로
 * 어떤 외삽도 추측이 된다).  경과는 외삽이 아니라 관측이고, 그래서 서버가
 * 조용한 구간에서도 화면이 멈춘 것이 아님을 말할 수 있다 — 12회차 캡처가
 * 13초와 60초 화면이 **바이트까지 같은 것**을 잡았고, 그 구간이 치수 재기
 * 190초의 뒤쪽 절반이다. */
let _tick = null;
function startElapsed(already) {
  stopElapsed();
  // hotfix57 — 다시 붙은 화면은 서버가 잰 경과(`running_s`)에서 이어 센다.
  const t0 = Date.now() - Math.max(0, already || 0) * 1000;
  const line = $("#prog-elapsed");
  const paint = () => {
    if (line) line.textContent = `경과 ${minsec((Date.now() - t0) / 1000)}`;
  };
  paint();
  _tick = setInterval(paint, 1000);
}
function stopElapsed() {
  if (_tick) { clearInterval(_tick); _tick = null; }
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

/* 진행 눈금 — **분모는 분석 대상 장수**이고 넣은 쪽수는 그 옆에 함께 적는다.
 *
 * 사용자 원문은 `1/58` 이었다.  그런데 이 문서는 58쪽 중 52장만 분석 대상이라
 * (도면 목록 1 · 범례 4 · 범위 밖 1), `n/58` 로 세면 진행이 52/58 에서 끝나
 * "여섯 장이 안 끝났다"로 읽힌다.  그래서 비율은 52 로 세고 58 을 같은 줄에
 * 남긴다 — 두 숫자가 다 보이므로 어느 쪽도 감춰지지 않는다.  `/58` 로
 * 되돌리려면 이 함수 한 곳만 고치면 된다. */
function showSheets(done, total) {
  const line = $("#prog-sheets");
  if (!total) { line.textContent = ""; return; }
  const p = S.pageCount;
  const tail = p ? `  ·  넣은 PDF ${p}쪽 중 제외 ${Math.max(p - total, 0)}쪽` : "";
  line.textContent = `분석 ${done} / ${total}장${tail}`;
}

/* 무엇을 분석하고 있는지 — 프로젝트와 파일명.  둘 다 업로드 응답 값 그대로다. */
function showWhat(project, pdfName) {
  const line = $("#prog-what");
  if (!line) return;
  const bits = [];
  if (project) bits.push(`PJT ${project}`);
  if (pdfName) bits.push(pdfName);
  line.textContent = bits.join("  ·  ");
}

/* 지금 읽고 있는 도서 번호.  파이프라인이 장마다 보내 주는 값이고, 없으면
 * 줄을 비운다 — 직전 장의 번호를 남겨 두면 멈춘 것처럼 읽힌다. */
function showNow(drawingNo) {
  const line = $("#prog-now");
  if (line) line.textContent = drawingNo ? `현재 도서  ${drawingNo}` : "";
}

/* 완료 화면 — 무엇을 받았는지.
 *
 * "완료" 한 마디로는 결과를 알 수 없고, 11회차부터 **화면에 있는 행과 발주처
 * 양식에 나가는 행이 다르다**.  빠지는 행은 사유별로 적는다 — 왜 빠졌는지
 * 화면에서 알 수 있어야 한다(근거 패널과 같은 이유). */
function showDone(summary, elapsed) {
  const box = $("#prog-done");
  if (!box) return;
  const sc = (summary || {}).scope;
  if (!sc) { box.classList.add("hidden"); return; }
  const reasons = Object.entries(sc.by_reason || {})
    .sort((a, b) => b[1] - a[1])
    .map(([why, n]) => `<div class="dn-row"><span>${escape(why || "(판정 없음)")}`
      + `</span><span class="n">${n}행</span></div>`).join("");
  const tabs = Object.entries(sc.by_tab || {})
    .sort((a, b) => b[1] - a[1])
    .map(([tab, n]) => `${tab} ${n}`).join("  ·  ");
  box.innerHTML =
    `<div class="dn-head">분석 완료${elapsed ? ` — ${minsec(elapsed)}` : ""}</div>`
    + `<div class="dn-row big"><span>추출한 행</span>`
    + `<span class="n">${sc.total}행</span></div>`
    + `<div class="dn-row big"><span>발주처 양식에 나가는 행</span>`
    + `<span class="n">${sc.delivered}행</span></div>`
    + (tabs ? `<div class="dn-sub">${escape(tabs)}</div>` : "")
    // 18회차 — **두 사실을 나눠 말한다.**  전량 모드에서는 벤더 공급분도
    // 양식에 나가므로 "빠지는 행"이 0 이다.  그때 260행을 "빠진다"고 적으면
    // 거짓말이고, 아예 안 적으면 공급 주체를 구분한다는 사실이 사라진다.
    + (sc.held ? `<div class="dn-row big"><span>발주처 양식에서 빠지는 행</span>`
        + `<span class="n">${sc.held}행</span></div>${reasons}` : "")
    + (!sc.held && sc.vendor
        ? `<div class="dn-note">그 중 타사 공급분 ${sc.vendor}행도 함께 나갑니다 — `
          + `설치 자재(Bulk material)는 SCT 공급이라 물량 산출에 필요합니다. `
          + `공급 주체는 SCOPE 열이 계속 구분합니다</div>` : "")
    + (sc.legacy_no_scope
        ? `<div class="dn-note">SCOPE 판정이 없는 행 ${sc.legacy_no_scope}행 — `
          + `이 열이 생기기 전의 분석입니다</div>` : "")
    + legendDoneLines(summary || {})
    + revisionLines(summary || {});
  box.classList.remove("hidden");
}

/* 범례를 재서 왔나 물려받아 왔나 — 완료 화면에서도 말한다 (15회차).
 *
 * 문장은 서버의 `_legend_facts` 가 쓴 것을 그대로 쓴다.  화면이 같은 판단을
 * 다시 하지 않는다. */
function legendDoneLines(summary) {
  const f = summary.legend;
  if (!f || f.mode === "unknown") return "";
  const n = (f.summary && f.summary.item_count) || 0;
  let out = `<div class="dn-row big"><span>범례</span>`
    + `<span class="n">${f.mode === "reused" ? "재사용" : "이 문서에서 유도"}</span></div>`
    + `<div class="dn-sub">${escape(f.line || "")}`
    + (n ? ` — ${n}항목` : "") + `</div>`;
  if (f.change_count) {
    out += `<div class="dn-note">이 개정본의 범례가 프로필과 ${f.change_count}칸 `
      + `다릅니다 — 자동으로 갱신하지 않았습니다. 결과 화면 위쪽에서 고르세요</div>`;
  } else if (f.mode === "reused" && !f.compared) {
    out += `<div class="dn-note">${escape(f.compare_note || "")}</div>`;
  }
  return out;
}

/* 개정과 승계 — 완료 화면에서도 말한다 (13회차).
 *
 * 첫 화면 목록이 이미 구분해 보이지만, 방금 분석을 건 사람은 결과 화면을
 * 먼저 본다.  대표 Rev 하나만 적지 않고 **접기 전 분포**를 같이 적는다:
 * 이 문서는 장마다 Rev 가 다르고(A~D), 대표값을 접는 규칙은 도면에서
 * 유도되지 않아 config 에 있기 때문이다. */
function revisionLines(summary) {
  const out = [];
  const dr = summary.doc_rev;
  if (dr && dr.rev) {
    const dist = Object.entries(dr.distribution || {})
      .sort((a, b) => (a[0] < b[0] ? -1 : 1))
      .map(([r, n]) => `${r} ${n}장`).join(" · ");
    out.push(`<div class="dn-row big"><span>도면이 말하는 개정</span>`
      + `<span class="n">Rev.${escape(dr.rev)}</span></div>`
      + `<div class="dn-sub">${escape(dr.why || "")}${dist ? ` — ${escape(dist)}` : ""}</div>`);
  } else if (dr) {
    out.push(`<div class="dn-row big"><span>도면이 말하는 개정</span>`
      + `<span class="n">읽지 못함</span></div>`);
  }
  const rev = summary.revision || {};
  const c = rev.carried;
  if (c && c.matched) {
    out.push(`<div class="dn-row big"><span>이전 리비전에서 이어받은 수정</span>`
      + `<span class="n">${c.filled}칸</span></div>`
      + `<div class="dn-sub">${escape(c.from || "")} 의 ${c.matched}행과 짝이 맞았습니다`
      + (c.conflicts ? ` · 그중 ${c.conflicts}행은 이번 도면이 다르게 읽어 검토로 올렸습니다` : "")
      + `</div>`);
  }
  const sr = rev.sheet_revisions;
  if (sr && (sr.raised || sr.lowered || sr.ambiguous)) {
    const bits = [];
    if ((sr.raised || []).length) bits.push(`${sr.raised.length}장 개정`);
    if (sr.unchanged) bits.push(`${sr.unchanged}장 그대로`);
    if ((sr.lowered || []).length) bits.push(`${sr.lowered.length}장 역행`);
    if (sr.new_sheets) bits.push(`${sr.new_sheets}장 신규`);
    if (sr.unreadable) bits.push(`${sr.unreadable}장 판별 불가`);
    // 도면번호가 장을 유일하게 가리키지 않는 경우.  판정하지 않았다는 사실을
    // 숨기지 않는다 - 이 문서에는 그런 도면번호가 3개 있다.
    if ((sr.ambiguous || []).length)
      bits.push(`${sr.ambiguous.length}개 도면번호는 장이 여럿이라 판정 안 함`);
    out.push(`<div class="dn-row big"><span>장 단위 개정 대조</span>`
      + `<span class="n">${escape(bits.join(" · "))}</span></div>`
      + ((sr.raised || []).length
         ? `<div class="dn-sub">${escape(sr.raised.slice(0, 4).map(
             r => `${r.drawing_no} ${r.before}→${r.now}`).join(" · "))}`
           + `${sr.raised.length > 4 ? " …" : ""}</div>` : ""));
  }
  return out.join("");
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

/* hotfix58 — **P&ID 분석 메뉴는 언제나 첫 화면으로 연다.**
 *
 * hotfix57 은 이 브라우저가 지켜보던 분석을 적어 두고 다시 열리면 그 진행 화면으로 끌고
 * 갔는데, 사용자 요구는 반대였다: *다른 메뉴에 다녀오거나 · 진행 화면에서 나가거나 ·
 * 메뉴를 다시 불러도 첫 화면으로 온다 — 대신 첫 화면이 분석 중 현황을 보인다.*  분석은
 * 서버(자식 프로세스)에서 계속 돌므로 화면이 떠나도 멈추지 않는다.  돌고 있는 분석은
 * '최근 분석 이력' 맨 위에서 진행 막대 · % · 남은 시간으로 보이고, 누르면 진행 화면으로
 * 간다 (`liveRow` · `pollRunning`). */
function watch(jobId, pageCount, what) {
  drop.classList.add("hidden");
  $("#progress").classList.remove("hidden");
  S.pageCount = null; S.sheetTargets = null;
  S.watching = jobId;
  $("#prog-skip").classList.add("hidden");
  $("#prog-done").classList.add("hidden");
  showWhat((what || {}).project, (what || {}).pdf_name);
  showNow("");
  startElapsed((what || {}).running_s);
  const cb = $("#prog-cancel");
  cb.disabled = false; cb.textContent = "분석 취소";
  $("#prog-cancelwrap").classList.remove("hidden");
  // A previous failure leaves its hint, buttons and job list on this panel; a new
  // analysis has to start from a clean one or the reviewer reads last time's exit
  // routes over this run's progress bar.
  $("#prog-title").textContent = "분석 중";
  $("#prog-sheets").textContent = "";
  $("#prog-pages").textContent = "";
  showPages(pageCount);
  ["#prog-hint", "#prog-actions", "#prog-jobs"].forEach(
    sel => $(sel).classList.add("hidden"));
  $("#prog-leave").classList.remove("hidden");
  $("#prog-eta").textContent = "";
  if (!_pollTimer) pollRunning();            // hotfix58 — 예상 퍼센트·남은 시간
  if (S.watchSrc) { try { S.watchSrc.close(); } catch (e) {} }
  const src = new EventSource(`/jobs/${jobId}/events`);
  S.watchSrc = src;
  src.onmessage = (ev) => {
    const d = JSON.parse(ev.data);
    // hotfix58 — 이 서버의 지난 분석으로 예상이 서면 막대는 그 예상(시간 비례)을 따른다 —
    // 첫 화면과 같은 퍼센트.  예상이 없을 때만 단계 비율을 그린다.
    if (!(DASH.live[jobId] && DASH.live[jobId].percent != null))
      $("#bar-fill").style.width = `${Math.round(d.progress * 100)}%`;
    $("#prog-msg").textContent = stageWords(d.message);
    if (d.page_count != null) showPages(d.page_count, null);
    if (d.sheets_total) showPages(null, d.sheets_total);
    if (d.sheets_total != null) showSheets(d.sheets_done || 0, d.sheets_total);
    if (d.sheet_plan) showSkipped(d.sheet_plan);
    if (d.drawing_no !== undefined) showNow(d.drawing_no);
    if (d.status === "done" || d.status === "failed" || d.status === "cancelled") {
      $("#prog-leave").classList.add("hidden");
      $("#prog-eta").textContent = "";
    }
    if (d.status === "done" && !d.summary) {
      // 다시 붙었는데 그 사이 끝났다 — 요약은 끝나는 순간에만 실리므로 결과로 바로 간다.
      src.close(); stopElapsed(); open(jobId); return;
    }
    if (d.status === "done") {
      src.close();
      $("#prog-hint").classList.add("hidden");
      // 완료 요약을 먼저 보이고, 누르면 그리드로 간다.  바로 넘어가면 결과를
      // 읽을 틈이 없다 - "분석 완료 사유를 명확히" 가 그 요구다.
      $("#prog-cancelwrap").classList.add("hidden");
      stopElapsed();
      // 완료 상자가 소요 시간을 적으므로 위의 경과 줄은 지운다 - 같은 값을
      // 두 곳에 쓰면 둘이 1~2초 어긋나 보인다 (실제로 5분 58초 ↔ 6분 0초).
      // 남기는 쪽은 **서버가 잰 값**이다.
      $("#prog-elapsed").textContent = "";
      $("#prog-title").textContent = "분석 완료";
      $("#prog-msg").textContent = "";
      showNow("");
      showDone(d.summary, d.elapsed_s);
      $("#prog-actions").classList.remove("hidden");
      $("#prog-home").textContent = "결과 보기";
      $("#prog-home").onclick = () => { $("#prog-home").onclick = null; open(jobId); };
    }
    if (d.status === "cancelled") {
      src.close();
      $("#prog-cancelwrap").classList.add("hidden");
      stopElapsed();
      $("#prog-title").textContent = "분석 취소됨";
      $("#prog-msg").textContent =
        "저장된 것은 없습니다 — 행 0건, 번호도 쓰지 않았습니다. "
        + "같은 PDF 를 다시 올리면 처음부터 분석합니다.";
      showNow("");
      $("#bar-fill").style.width = "0%";
      $("#prog-sheets").textContent = "";
      // 실패 화면과 같은 탈출구를 준다 - #drop 도 #main 도 숨겨져 있으므로
      // 여기서 길을 주지 않으면 URL 을 고치는 수밖에 없다 (§7.2).
      const hint = $("#prog-hint");
      hint.textContent = "다시 분석하려면 첫 화면에서 PDF 를 올리세요.";
      hint.classList.remove("hidden");
      $("#prog-actions").classList.remove("hidden");
      $("#prog-home").textContent = "첫 화면으로";
    }
    if (d.status === "failed") {
      src.close();
      $("#prog-cancelwrap").classList.add("hidden");
      stopElapsed();
      showFailure(d.message, d, jobId);
    }
  };
}

/* A failed analysis used to leave the reviewer with nothing: #drop and #main are
 * both hidden while #progress is up, so the screen had a title, a numpy exception
 * and no control of any kind.  The only way out was editing the URL.
 *
 * `message` is now a sentence the server built from what the file contains - the
 * traceback is in the log and the diagnostic export, not here. */
async function showFailure(message, d, jobId) {
  $("#bar-fill").style.width = "0%";
  $("#prog-title").textContent = "분석 실패";
  $("#prog-msg").textContent = message || "사유를 특정하지 못했습니다.";
  /* 어디까지 갔는지 — 21회차부터 **어느 단계에서** 멈췄는지도 말한다.
   *
   * 그 전에는 "도면을 한 장도 읽기 전에 멈췄습니다" 가 전부였는데, 그 문장이
   * 덮는 구간이 실제로는 여섯 단계다 (문서 열기 · 치수 재기 · 타이틀블록 ·
   * 범례 규칙 · 유닛 승수 · 대상 선별).  17분을 기다린 사람에게 그 여섯 중
   * 어디인지를 말해 주지 않으면 다음에 할 일이 서지 않는다.
   *
   * 단계 이름은 서버가 **사실 그대로**(`measuring sheet 37 of 60`) 보내고,
   * 한국어 문장은 여기서 `stageWords()` 가 만든다 — 모르는 값은 그대로 쓴다. */
  const far = $("#prog-sheets");
  const stage = d && d.stopped_stage ? stageWords(d.stopped_stage) : "";
  const took = d && d.elapsed_s ? ` (${minsec(d.elapsed_s)})` : "";
  if (d && d.sheets_total) {
    far.textContent = `도면 ${d.sheets_total}장 중 ${d.sheets_done || 0}장까지 읽고 멈췄습니다`
      + took + (stage ? ` — 마지막 단계: ${stage}` : "");
  } else if (d) {
    far.textContent = stage
      ? `도면을 읽기 전, ${stage} 단계에서 멈췄습니다${took}`
      : "도면을 한 장도 읽기 전에 멈췄습니다" + took;
  }
  const hint = $("#prog-hint");
  hint.textContent = "다른 PDF 로 다시 시도하거나, 아래 이전 분석을 여세요.";
  hint.classList.remove("hidden");
  $("#prog-actions").classList.remove("hidden");
  // hotfix29 — 타이틀블록을 못 읽고 멈춘 분석에는 **사람이 칸을 그어 주는 길**이 있다.
  const tbBtn = $("#prog-tbfix");
  const tbCase = !!(jobId && /도면번호를 읽지 못했습니다/.test(message || ""));
  tbBtn.classList.toggle("hidden", !tbCase);
  if (tbCase) {
    hint.textContent = "이 양식의 도면번호 칸을 아래 [타이틀블록 칸 지정] 으로 알려 주면 그 칸으로 다시 분석할 수 있습니다.";
    tbBtn.onclick = () => openTbFix(jobId);
  }
  $("#tbfix").classList.add("hidden");
  // hotfix71 — 실패도 VOC 로 남긴다 (실패 사유 · 멈춘 단계 · 예외 원문을 서버가 담는다)
  const vb = $("#prog-voc");
  if (vb) {
    vb.classList.toggle("hidden", !jobId);
    vb.onclick = () => vocDialog({ jobId, source: "ANALYSIS_FAILED", category: "ANALYSIS_FAILED",
                                   jobName: (d && d.pdf_name) || jobId });
  }
  /* 예외 원문 — 접어 두되 버리지 않는다 (21회차).
   *
   * 예전에는 진단 내보내기 zip 안에만 있었다.  "그대로 노출하지 않는다" 는
   * 뜻으로는 맞았지만, 회사 PC 에서 실패한 사람이 개발자에게 보낼 것을
   * 만들려면 zip 을 내려받아 풀어야 했다 — 이번 회차의 원본 예외도 사용자가
   * 터미널에서 떠다 준 것이다.
   *
   * 펼치기 전에는 받아 오지 않는다.  기본 응답(`_job_public`)은 그대로다. */
  const err = $("#prog-error");
  const errBody = $("#prog-error-body");
  errBody.textContent = "";
  err.open = false;
  err.classList.toggle("hidden", !jobId);
  if (jobId) {
    err.ontoggle = async () => {
      if (!err.open || errBody.textContent) return;
      errBody.textContent = "불러오는 중…";
      try {
        const r = await (await fetch(`/jobs/${jobId}/error_detail`)).json();
        errBody.textContent = r.detail || "예외 원문이 저장되지 않았습니다.";
      } catch (e) {
        errBody.textContent = "예외 원문을 불러오지 못했습니다.";
      }
    };
  }
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
  if (document.body.classList.contains("pid-full")) setFull(false);   // hotfix64
  _runAfterOpen();                          // hotfix68 — 결과를 열며 시작한 창이면 첫 화면 정보를 지금 읽는다
  if (SYNC.peer) rejoin();                  // hotfix68 — 결과를 떠나면 새 창도 닫는다
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
  $("#prog-done").classList.add("hidden");
  $("#prog-cancelwrap").classList.add("hidden");
  $("#prog-what").textContent = "";
  $("#prog-now").textContent = "";
  $("#prog-home").textContent = "첫 화면으로";
  // hotfix58 — 분석 중에 나가도 분석은 서버에서 계속된다.  이 화면만 닫는다 (진행 소식 ·
  // 경과 시계).  첫 화면의 '최근 분석 이력' 이 그 분석의 현황을 이어서 보인다.
  if (S.watchSrc) { try { S.watchSrc.close(); } catch (e) {} S.watchSrc = null; }
  stopElapsed();
  $("#prog-leave").classList.add("hidden");
  $("#prog-eta").textContent = "";
  S.pageCount = null; S.sheetTargets = null; S.watching = null;
  if (location.hash) history.replaceState(null, "", location.pathname + location.search);  // hotfix50 — ?embed 등을 지우지 않는다
  listJobs();
}
$req("#prog-home").addEventListener("click", toFirstScreen);
$req("#prog-leave").addEventListener("click", toFirstScreen);   // hotfix58 — 분석은 계속된다
// 18회차 — 결과 화면에서도 같은 함수를 부른다.  판정도 초기화도 한 곳에만
// 있어야 두 경로가 갈리지 않는다 (12회차 `toFirstScreen` 을 그대로 쓴다).
$req("#to-home").addEventListener("click", toFirstScreen);

function hashParts() {
  const raw = location.hash.slice(1);
  const i = raw.indexOf("?");
  return i < 0 ? [raw, ""] : [raw.slice(0, i), raw.slice(i + 1)];
}
window.addEventListener("hashchange", () => {
  const [id, query] = hashParts();
  if (id && (!S.job || S.job.id !== id)) { open(id); return; }
  // hotfix45 — `open()` 이 주소를 바꾸는 중이면 아무것도 하지 않는다.  그 전에는 이 갈래가
  // **옛 결과의 행으로** 목록을 한 번 더 그렸다 (QFE 2,041행 · 레이아웃 0.9초) — 읽기가
  // 끝나면 `open()` 이 어차피 다시 그린다.
  if (S.loading) return;
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
/* hotfix74 — 결과를 여는 도중 요청 하나가 끊기면(망 순단 · 서버 재시작) 화면이 반쯤 선 채로 남았다 — 목록 0행 ·
 * `S.loading` 이 켜진 채라 다음 그리기도 막히고, 위쪽 연결 띠는 다음 확인에서 사라져 **아무 말도 남지 않았다**
 * (실측: `/rows` 나 `/pages` 를 한 번 끊으면).  그 자리에서 말하고 [다시 열기] 를 둔다.  다시 열면 정상으로 선다. */
async function open(jobId) {
  const old = document.getElementById("open-err");
  if (old) old.remove();
  try {
    return await _open(jobId);
  } catch (e) {
    S.loading = false;
    const why = String((e && e.message) || e || "");
    const onResult = !$("#main").classList.contains("hidden") && S.job && S.job.id === jobId;
    if (!onResult) {
      alert("결과를 열지 못했습니다 — 서버에 연결할 수 없거나 응답이 끊겼습니다.  잠시 뒤 다시 눌러 주세요.\n(" + why + ")");
      return;
    }
    const box = document.createElement("div");
    box.id = "open-err";
    box.className = "open-err";
    box.innerHTML = `<b>결과를 다 받지 못했습니다</b> — 여는 도중 연결이 끊겼습니다 (${escape(why)}).
      목록·도면이 비어 있거나 일부만 보일 수 있습니다.  <button type="button">다시 열기</button>`;
    box.querySelector("button").onclick = () => open(jobId);
    const right = $("#right");
    right.insertBefore(box, right.firstChild);
  }
}

async function _open(jobId) {
  const job = await (await fetch(`/jobs/${jobId}`)).json();
  if (job.status !== "done") { _runAfterOpen(); watch(jobId, job.page_count, job); return; }
  S.loading = true;
  S.job = job;
  S.zoom = null;                  // a fresh analysis starts fitted, not zoomed
  // 개정 스위치는 그 분석의 것이다.  다른 분석으로 넘어갈 때 남아 있으면
  // 바뀐 행이 없는 리비전에서 화면이 텅 빈 채로 열린다.
  S.onlyChanged = false;
  S.revFilter = "";
  S.deletedRows = [];
  S.revByKey = {};
  const oc = $("#only-changed"); if (oc) oc.checked = false;
  if (S.side) { S.side = false; $("#right").classList.remove("compare"); $("#cmp").classList.add("hidden"); }
  const rf = $("#rev-filter"); if (rf) rf.value = "";

  readUrl(hashParts()[1]);
  if (location.hash.slice(1).split("?")[0] !== jobId) location.hash = jobId;
  drop.classList.add("hidden");
  $("#progress").classList.add("hidden");
  $("#main").classList.remove("hidden");
  renderNav();
  $("#job-name").textContent = job.pdf_name + (job.input_kind === "DXF" ? "  [DXF]" : "");
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
  // hotfix68 — 서로 기다릴 이유가 없는 읽기는 **같이** 보낸다.  예전에는 장 → 범례 → 모드 → 개정 → 행 →
  // (행 뒤) 마크업 · 확정 · 검토 · 이력 · 신고 · 미판정 · 템플릿을 하나씩 기다렸다 (QFE 2,041행 · 요청 열넷이 줄지어).
  // 가장 큰 `/rows`(압축 뒤 1.2MB)를 맨 먼저 띄워 두고, 나머지 작은 것들이 그 사이에 온다.
  const rowsP = fetch(`/jobs/${jobId}/rows?tab=ALL&slim=1`).then(r => r.json());
  const sideP = rowSideFetches(jobId);      // 행 큰 본문을 푸는 동안(주 스레드가 막힌다) 이미 날아가 있게
  const pagesP = fetch(`/jobs/${jobId}/pages`).then(r => r.json());
  await Promise.all([loadLegendProfile(), loadModeBar(), loadRevision()]);
  S.pages = await pagesP;
  await loadRows(rowsP, sideP);
  buildPageSelect();
  S.loading = false;
  updateEmptyNote();
  S.pageMult = { checked: new Set(), vals: {}, last: null };   // hotfix65 — 페이지별 승수 (분석마다 새로)
  S.pinSel = null; S.pinEditing = null; if (S.pinMode) setPinMode(false); closePinPop();   // hotfix76
  S.memo = null; S.memoDraft = {};        // hotfix63 — 장별 메모 (다른 분석의 저장 안 한 글은 들고 오지 않는다)
  showPage(S.pages.find(p => (p.layers && Object.keys(p.layers).length)) || S.pages[0]);
  loadMemoSummary();
  autoSide();
  syncPost({ t: "job", id: jobId });        // hotfix68 — 다른 창도 같은 결과로
  _runAfterOpen();
}

/* hotfix40 — 이전 대비 **변경(추가·수정·삭제)이 있는** 결과를 열면 나란히 보기를 바로 켠다 —
 * 목적이 그 변경을 이전 도면과 눈으로 대조하는 것이기 때문이다.  사람이 한 번 끄면
 * (`pid.side.off`) 그 브라우저에서는 자동으로 켜지 않는다.  변경이 없으면 켜지 않는다. */
function autoSide() {
  if (paneSplit()) return;                            // hotfix68 — 두 창으로 나뉘어 있으면 목록 창을 가리지 않는다
  if (!S.rev || !S.rev.compared_with || !S.revPair || S.job.id !== S.revPair.current) return;
  if (S.rev.compare_basis !== "TAG") return;          // hotfix46 — 나란히 대조는 실행 프로젝트만
  const c = S.rev.counts || {};
  if (!((c.ADDED || 0) + (c.MODIFIED || 0) + (c.DELETED_CANDIDATE || 0) + (c.DELETED || 0))) return;
  let off = false; try { off = localStorage.getItem("pid.side.off") === "1"; } catch (e) {}
  if (!off) toggleSide(true);
}

/* 이 결과가 어느 범례로 나왔나 — 재사용인가 유도인가 (15회차).
 *
 * 판정은 서버의 `_legend_facts` **하나**가 한다.  화면이 같은 판단을 다시
 * 하면 언젠가 갈린다 (11·14 회차가 같은 실패를 두 번 잡았다).  여기서 하는
 * 일은 서버가 준 문장을 놓는 것과, 달라진 항목이 있을 때 **고르게 하는**
 * 것뿐이다 — 자동으로 갱신하지 않는다.
 */
/* 38회차 — 이 분석이 어느 모드로 돌았나.  서버(`_mode_facts`)가 쓴 문장을
 * 놓기만 한다.  선언과 실측이 다르면 그 띠가 붉고 바꾸는 버튼이 붙는다 —
 * 바꿔도 이번 결과는 그대로이고 다음 분석부터다 (15·31회차 규율). */
async function loadModeBar() {
  const bar = $("#mode-bar");
  if (!bar) return;
  let f = null;
  try { f = await (await fetch(`/jobs/${S.job.id}/mode`)).json(); } catch (e) { f = null; }
  if (!f || !f.recorded) { bar.classList.add("hidden"); bar.innerHTML = ""; return; }
  const tag = f.effective === "epc" ? "실행 · 1급+2급" : "입찰 · 2급";
  let html = `<div class="lb-main"><span class="lb-tag ${f.conflict ? "conflict" : f.effective}">${tag}</span>`
    + `<span class="lb-line">${escape(f.line || "")}</span>`;
  if (f.conflict && f.project) {
    const to = f.conflict === "declared_bid_tags_found" ? "epc" : "bid";
    html += `<button type="button" class="ghost small" id="mode-switch" data-to="${to}">`
      + `프로젝트 모드를 실측대로(${MODE_WORD[to]}) 바꾸기 — 다음 분석부터</button>`;
  }
  html += `</div>`;
  bar.innerHTML = html;
  bar.classList.remove("hidden");
  bar.classList.toggle("changed", !!f.conflict);
  const b = $("#mode-switch");
  if (b) b.addEventListener("click", async () => {
    const author = await askAuthor(`${f.project} 도면 종류 → ${MODE_WORD[b.dataset.to]}`);
    if (author === null) return;
    const fd = new FormData(); fd.append("mode", b.dataset.to); fd.append("author", author || "");
    const res = await fetch(`/projects/${encodeURIComponent(f.project)}/mode`, { method: "PATCH", body: fd });
    b.textContent = res.ok ? `바꿨습니다 — 다음 분석부터 ${MODE_WORD[b.dataset.to]}` : "바꾸지 못했습니다";
    b.disabled = true;
  });
}

async function loadLegendProfile() {
  const bar = $("#legend-bar");
  if (!bar) return;
  let f = null;
  try {
    f = await (await fetch(`/jobs/${S.job.id}/legend_profile`)).json();
  } catch (e) { f = null; }
  S.legend = f;
  const pr = (f && f.profile) || {}, bo = (f && f.borrowed) || {};
  if (!f || f.mode === "unknown" && !f.has_stored_profile && !pr.path && !(f.input_notes || []).length) {
    bar.classList.add("hidden"); bar.innerHTML = ""; return;
  }
  const n = (f.summary && f.summary.item_count) || 0;
  const failed = ((f.summary && f.summary.failed) || []).length;
  const bits = [`<span class="lb-tag ${f.mode}">`
    + `${f.mode === "reused" ? "범례 재사용" : f.mode === "derived"
        ? "범례 유도" : "기록 없음"}</span>`,
    `<span class="lb-line">${escape(f.line || "")}</span>`];
  if (n) bits.push(`<span class="lb-n">${n}항목`
    + (failed ? ` · 유도 실패 ${failed}` : "") + `</span>`);
  // hotfix72 — 대조 못 한 항목 수는 서버 문장(`compare_note`)이 이미 말한다.  예전에는 같은
  // 사실을 여기서 한 번 더 적어 띠 한 줄에 같은 말이 두 번 있었다.
  if (f.compare_note) bits.push(`<span class="lb-note">${escape(f.compare_note)}</span>`);
  const fullLegend = [f.line, f.compare_note].filter(Boolean).join(" · ");
  let html = `<div class="lb-main" title="${escape(fullLegend)}">${bits.join("")}</div>`;
  // 56회차 [G1] — 어느 프로필로 돌았나.  "새 프로젝트" 면 무엇을 빌렸는지 편다.
  if (pr.path) {
    // 접힌 띠에는 짧은 말만 (`lb-short`), 펼치면 온 문장 (`lb-line`).
    const short = pr.matched ? (pr.name || pr.code || "")
      : `새 프로젝트${(bo.count ? ` · 기본 설정 ${bo.count}칸 빌림` : "")}`;
    html += `<div class="lb-main" title="${escape(f.profile_line || "")}">`
      + `<span class="lb-tag ${pr.matched ? "matched" : "stranger"}">`
      + `${pr.matched ? "프로필 일치" : "프로필 없음"}</span>`
      + `<span class="lb-short">${escape(short)}</span>`
      + `<span class="lb-line">${escape(f.profile_line || "")}</span></div>`;
    if ((bo.keys || []).length) {
      const sec = Object.entries(bo.by_section || {}).map(([k, n]) => `${k} ${n}`).join(" · ");
      html += `<details class="lb-saved"><summary>빌려 쓴 설정 ${bo.count}칸 — ${escape(sec)}</summary>`
        + `<pre>${escape(bo.keys.join("\n"))}</pre>`
        + `<div class="muted small">${escape(bo.not_counted || "")}</div></details>`;
    }
  }
  // hotfix74 — DXF 묶음에서 건너뛴 파일 · 태그 속성을 못 배운 사실 (서버 문장 그대로)
  if ((f.input_notes || []).length) {
    html += `<div class="lb-main" title="${escape(f.input_notes.join("\n"))}">`
      + `<span class="lb-tag stranger">입력</span>`
      + `<span class="lb-short">${escape(f.input_notes[0].split(" — ")[0])}</span>`
      + `<span class="lb-line">${escape(f.input_notes.join(" · "))}</span></div>`;
  }
  if ((f.stored_lines || []).length) {
    html += `<details class="lb-saved"><summary>저장된 범례 프로필 보기</summary>`
      + `<div class="lb-path">${escape(f.stored_path || "")}</div>`
      + `<pre>${escape((f.stored_lines || []).join("\n"))}</pre></details>`;
  }
  if (f.change_count) html += legendChangeBlock(f);
  bar.innerHTML = html;
  bar.classList.remove("hidden");
  bar.classList.toggle("changed", !!f.change_count);
  bindLegendAdopt();
}

/* 달라진 곳 — 무엇이 무엇에서 무엇으로.  **자동 갱신은 없다.** */
function legendChangeBlock(f) {
  const byItem = {};
  (f.changes || []).forEach(c => {
    (byItem[c.item] = byItem[c.item] || {label: c.label, rows: []}).rows.push(c);
  });
  const rows = Object.entries(byItem).map(([key, g]) =>
    `<div class="lb-item"><label><input type="checkbox" class="lb-pick" `
    + `value="${escape(key)}" checked> ${escape(g.label)}</label>`
    + `<div class="lb-cells">` + g.rows.slice(0, 6).map(c =>
        `<div><code>${escape(c.key)}</code> `
        + `<s>${escape(String(c.was === null ? "(없음)" : c.was))}</s> → `
        + `<b>${escape(String(c.now === null ? "(없음)" : c.now))}</b></div>`).join("")
    + (g.rows.length > 6 ? `<div>… 그 밖에 ${g.rows.length - 6}칸</div>` : "")
    + `</div></div>`).join("");
  return `<div class="lb-changes">`
    + `<div class="lb-warn">이 개정본의 범례가 저장된 프로필과 `
    + `<b>${f.change_count}칸</b> 다릅니다. 이번 분석은 <b>프로필</b>로 했습니다 — `
    + `자동으로 갱신하지 않았습니다.</div>`
    + rows
    + `<div class="lb-act">`
    + `<button id="lb-adopt"${f.can_adopt ? "" : " disabled"}>고른 항목을 새 범례로 갱신</button>`
    + `<button id="lb-keep" class="ghost">옛 프로필 유지</button>`
    + `<span id="lb-said" class="lb-said"></span></div></div>`;
}

function bindLegendAdopt() {
  const adopt = $("#lb-adopt"), keep = $("#lb-keep"), said = $("#lb-said");
  if (keep) keep.onclick = () => {
    said.textContent = "옛 프로필을 그대로 씁니다. 프로필 파일은 바뀌지 않았습니다.";
  };
  if (adopt) adopt.onclick = async () => {
    const picked = [...document.querySelectorAll(".lb-pick")]
      .filter(c => c.checked).map(c => c.value);
    if (!picked.length) { said.textContent = "고른 항목이 없습니다."; return; }
    const body = new FormData(); body.append("keys", picked.join(","));
    const res = await fetch(`/jobs/${S.job.id}/legend_profile/adopt`,
                            {method: "POST", body});
    const out = await res.json();
    if (!res.ok) { said.textContent = out.detail || "갱신하지 못했습니다."; return; }
    said.textContent = `${out.adopted.join(", ")} 갱신했습니다 — ${out.note}`;
    adopt.disabled = true;
  };
}

/* 이 분석이 어느 리비전이고 무엇과 비교했는지.  머리에 "Rev.C vs Rev.A" 로
 * 적는다 - 결과만 보고 무엇과 비교했는지 알 수 없으면 안 된다. */
async function loadRevision() {
  try {
    S.rev = await (await fetch(`/jobs/${S.job.id}/revision`)).json();
  } catch (e) { S.rev = null; }
  renderRevLabel();
  renderDeletedCandidates();
  // hotfix39 — 직전 ↔ 현재 결과 스위치.  짝은 서버가 장부에서 읽은 id 둘이다.
  if (S.rev && S.rev.compared_with && S.rev.previous_job_id) {
    S.revPair = { current: S.job.id, currentLabel: S.rev.revision,
                  previous: S.rev.previous_job_id, previousLabel: S.rev.compared_with };
  } else if (S.rev && (S.rev.next_jobs || []).length && S.revPair && S.revPair.previous === S.job.id) {
    // 직전 결과를 보는 중 — 짝은 그대로 둔다
  } else if (S.rev && (S.rev.next_jobs || []).length) {
    const n = S.rev.next_jobs[0];
    S.revPair = { current: n.job_id, currentLabel: n.revision,
                  previous: S.job.id, previousLabel: S.rev.revision };
  } else {
    S.revPair = null;
  }
  renderRevSwitch();
}

/* 머리줄의 개정 라벨 — `S.rev` 하나에서 그린다.  열기(`loadRevision`)와 메모리 복원
 * (`restoreView`)이 같은 함수를 부른다 (두 벌을 두면 갈린다). */
function renderRevLabel() {
  const el = $("#rev-label");
  if (!S.rev || !S.rev.revision) { el.classList.add("hidden"); el.textContent = ""; return; }
  const c = S.rev.counts || {};
  const bits = [];
  if (c.ADDED) bits.push(`추가 ${c.ADDED}`);
  // hotfix47 — 같은 도면에 짝 없는 태그가 양쪽에 남은 것은 전부 '수정' 이다 (태그 변경인지
  // 추가/삭제인지 도면이 가르지 않는다).  사라진 태그 쪽은 '이전 태그' 로 따로 센다.
  if (c.MODIFIED || c.MODIFIED_BEFORE) bits.push(`수정 ${c.MODIFIED || 0}` + (c.MODIFIED_BEFORE ? ` (+ 이전 태그 ${c.MODIFIED_BEFORE})` : ""));
  if (c.DELETED_CANDIDATE) bits.push(`삭제 후보 ${c.DELETED_CANDIDATE}`);
  if (c.DELETED) bits.push(`삭제 확정 ${c.DELETED}`);
  // hotfix38 — 짝을 태그로 지은 행 수.  태그가 있는 문서에서 이 수가 곧 대조의
  // 신뢰도다 (태그 짝은 거리를 안 본다 · 기하 짝만 반경에 걸린다).
  const mb = S.rev.matched_by || {};
  const tagOnly = S.rev.compare_basis === "TAG";
  if (S.rev.compared_with && tagOnly) {
    // hotfix46 — 짝은 태그로만.  대조하지 않은 행(태그 없음)은 그 수를 따로 말한다.
    bits.push(`짝 태그 ${mb.TAG || 0}` + (mb.GEOMETRY ? ` · 기하 ${mb.GEOMETRY} (옛 대조)` : "")
      + (mb.NOT_COMPARED ? ` · 대조 안 함(태그 없음) ${mb.NOT_COMPARED}` : ""));
  } else if (S.rev.compared_with && S.rev.compare_basis === "NONE") {
    bits.push("개정 대조 안 함 — 입찰 프로젝트 (태그가 없어 비교할 열쇠가 없고, 위치로는 비교하지 않습니다)");
  }
  // 도면번호가 바뀐 장 · 한쪽에만 있는 장 — 장 단위 사실이라 행 수와 따로 말한다.
  const sh = S.rev.sheets || {};
  if ((sh.renumbered || []).length) bits.push(`도면번호 바뀐 장 ${sh.renumbered.length}`);
  if ((sh.only_now || []).length) bits.push(`새 장 ${sh.only_now.length}`);
  if ((sh.only_before || []).length) bits.push(`빠진 장 ${sh.only_before.length}`);
  el.textContent = S.rev.label + (bits.length ? ` — ${bits.join(" · ")}` : "");
  el.title = S.rev.compared_with
    ? `${S.rev.compared_with} 와 비교한 결과입니다.  짝은 같은 TYPE 의 같은 태그로만 — 위치로는 비교하지 않습니다.  `
      + `추가 = 이번에 새로 선 태그(그 도면에서 사라진 태그가 없을 때), 삭제 후보 = 직전 리비전에 있었는데 이번에 없는 태그(그 도면에 새 태그가 없을 때 · 사람이 확정합니다).  `
      + `같은 도면에 새 태그와 사라진 태그가 함께 있으면 태그 변경인지 추가/삭제인지 도면이 가르지 않으므로 전부 '수정' 으로만 표기합니다.  `
      + `목록의 '개정' 열과 개정 필터로 좁힐 수 있습니다.`
      + ((sh.renumbered || []).map(e => `\n도면번호 바뀐 장: ${e.before} → ${e.now} (태그 ${e.shared}개 공유)`).join(""))
      + ((sh.only_now || []).length ? `\n새 장: ${sh.only_now.join(", ")}` : "")
      + ((sh.only_before || []).length ? `\n빠진 장: ${sh.only_before.join(", ")}` : "")
    : "";
  el.classList.remove("hidden");
  // 비교 대상이 있는 리비전에서만 스위치를 보인다 - Rev.A 에는 고를 상태가 없다.
  const w = $("#only-changed-wrap");
  if (w) w.classList.toggle("hidden", !S.rev.compared_with);
  // hotfix41 — 변경 내역 Excel.  서버가 저장된 판정을 그대로 옮겨 적는다.
  const ex = $("#rev-export");
  if (ex) { ex.classList.toggle("hidden", !S.rev.compared_with); ex.href = `/jobs/${S.job.id}/revision/changes.xlsx`; }
}

/* hotfix39 — 직전/현재 결과 스위치와 전환.
 *
 * 사용자 요구: *"개정된 P&ID 가 들어오면 오른쪽 list 및 속성란을 … 이전 직전 P&ID 를
 * 불러와서 선택 가능하도록 — 오른쪽 상단에 이전 P&ID 표기와 현재 P&ID 출력 결과 표기 —
 * 화면 전환이 무겁지 않고 가볍고 빠르게."*
 *
 * 방법: 결과 하나의 화면 상태(행 · 검토 · 개정 · 장 목록 · 선택 · 배율)를 **통째로 메모리에
 * 둔다** (`S.viewCache[jobId]`).  처음 가는 결과는 보통의 열기(`open`)로 읽고 — 그 비용은
 * 한 번이다 — 돌아올 때는 캐시를 되살려 그리기만 한다 (결과 요청 0 · 도면 그림은 브라우저
 * 캐시).  장은 **같은 도면번호**를 따라간다 — 쪽 번호가 아니라 (13회차: 개정 때 장 순서가
 * 바뀐다).  필터·선택은 결과마다 따로 산다.  */
const VIEW_KEYS = ["job", "pages", "rows", "rowByKey", "revByKey", "deletedRows", "counts",
  "originCounts", "review", "jobReview", "rev", "axisOv", "markupSummary", "unjudged",
  "unjudgedKnown", "feedback", "reports", "legend", "mult", "pageMult", "sheetNos", "sheetTargets",
  "byTab", "drawings", "page", "sel", "zoom", "mode", "tab", "axis", "code", "drawing",
  "gradeFilter", "reasonFilter", "originFilter", "filter", "onlyReview", "onlyChanged",
  "revFilter", "colFilters", "natural"];

function snapshotView() {
  if (!S.job) return;
  const snap = {};
  for (const k of VIEW_KEYS) snap[k] = S[k];
  snap._bars = { mode: $("#mode-bar") ? $("#mode-bar").innerHTML : "",
                 modeHidden: $("#mode-bar") ? $("#mode-bar").classList.contains("hidden") : true,
                 legend: $("#legend-bar") ? $("#legend-bar").innerHTML : "",
                 legendHidden: $("#legend-bar") ? $("#legend-bar").classList.contains("hidden") : true,
                 jobName: $("#job-name").textContent, jobMeta: $("#job-meta").textContent };
  S.viewCache[S.job.id] = snap;
}

function restoreView(snap) {
  for (const k of VIEW_KEYS) S[k] = snap[k];
  const b = snap._bars || {};
  if ($("#mode-bar")) { $("#mode-bar").innerHTML = b.mode || ""; $("#mode-bar").classList.toggle("hidden", !!b.modeHidden); }
  if ($("#legend-bar")) { $("#legend-bar").innerHTML = b.legend || ""; $("#legend-bar").classList.toggle("hidden", !!b.legendHidden); }
  $("#job-name").textContent = b.jobName || "";
  $("#job-meta").textContent = b.jobMeta || "";
  const oc = $("#only-changed"); if (oc) oc.checked = !!S.onlyChanged;
  const rf = $("#rev-filter"); if (rf) rf.value = S.revFilter || "";
  const only = $("#only-review"); if (only) only.checked = !!S.onlyReview;
  const box = $("#filter"); if (box) box.value = S.filter || "";
  // 주소는 보는 결과를 가리키되, hashchange 로 다시 열지 않는다
  history.replaceState(null, "", "#" + S.job.id);
  renderRevLabel();
  buildTabs(); updateBadge(); renderReviewPanel(); showAppliedRules(); buildPageSelect(); renderGrid();
  renderRevSwitch();
}

function renderRevSwitch() {
  const box = $("#rev-switch");
  if (!box) return;
  const pr = S.revPair;
  if (!pr || !S.job || (S.job.id !== pr.current && S.job.id !== pr.previous)) {
    box.classList.add("hidden"); box.innerHTML = ""; return;
  }
  const viewingPrev = S.job.id === pr.previous;
  // hotfix46 — 나란히 대조는 실행 프로젝트(태그 대조)만.  입찰 프로젝트에는 버튼 대신 사유 한 줄.
  const tagOnly = (S.rev || {}).compare_basis === "TAG";
  box.innerHTML = `<span class="rs-cap">결과</span>`
    + `<button type="button" class="prev${viewingPrev ? " on" : ""}" data-job="${escape(pr.previous)}" title="직전 P&ID 결과를 봅니다 — 오른쪽 목록·검토·근거와 왼쪽 도면이 그 결과로 바뀝니다">이전 ${escape(pr.previousLabel)}</button>`
    + `<button type="button" class="cur${viewingPrev ? "" : " on"}" data-job="${escape(pr.current)}" title="현재 P&ID 출력 결과">현재 ${escape(pr.currentLabel)}</button>`
    + (tagOnly ? `<button type="button" class="side${S.side ? " on" : ""}" title="나란히 보기 — 왼쪽은 최신 ${escape(pr.currentLabel)} 도면, 오른쪽은 직전 ${escape(pr.previousLabel)} 의 같은 도면번호 장.  대조는 같은 TYPE 의 같은 태그로만 (위치로는 비교하지 않습니다).  확대·스크롤이 함께 움직입니다">나란히</button>` : "")
    // hotfix44 — 재분석 없이 대조만 다시 한다 (업데이트로 판정 규칙이 바뀌었을 때 — 옛 판정이 DB 에 남는다).
    + `<button type="button" class="recmp" title="재분석 없이 ${escape(pr.previousLabel)} 대비 대조만 다시 합니다 — 업데이트로 개정 판정 규칙이 바뀌었을 때 (분석 결과·편집은 그대로)">대조 다시</button>`
    + `<span class="rs-note">${S.side ? `왼쪽 ${escape(pr.currentLabel)} · 오른쪽 ${escape(pr.previousLabel)} — 같은 도면번호 장 · 태그로 대조 · 확대와 스크롤이 함께 움직입니다`
        : viewingPrev ? "직전 결과를 보는 중 — 편집은 그 결과에 저장됩니다"
        : (!tagOnly && (S.rev || {}).compare_basis === "NONE") ? "입찰 프로젝트 — 태그가 없어 개정 대조(나란히)를 하지 않습니다"
        : (S.viewCache[pr.previous] ? "이전 결과는 메모리에 있어 바로 전환됩니다" : "")}</span>`;
  box.classList.remove("hidden");
  box.classList.toggle("viewing-prev", viewingPrev);
  box.querySelectorAll("button[data-job]").forEach(b => b.onclick = () => switchView(b.dataset.job));
  const sb = box.querySelector("button.side");
  if (sb) sb.onclick = () => toggleSide(!S.side, true);
  const rb = box.querySelector("button.recmp");
  if (rb) rb.onclick = () => recompare(pr.current, pr.previousLabel);
}

/* hotfix44 — 대조만 다시.  서버의 `POST /jobs/{id}/revision` 은 13회차부터 "비교 대상을
 * 바꿔 다시 보고 싶을 때 — 재분석 없이 대조만" 을 위해 있었는데 화면에서 부르는 곳이
 * 없었다.  판정은 서버(`revisions.compare`)가 하고 여기서는 묻고 → 부르고 → 다시 연다. */
async function recompare(jobId, against) {
  if (!jobId || S.loading) return;
  const job = S.job && S.job.id === jobId ? S.job : await (await fetch(`/jobs/${jobId}`)).json();
  if (!job.project) { alert("프로젝트에 묶인 분석이 아니라 대조할 수 없습니다."); return; }
  if (!confirm(`${against || "직전 리비전"} 대비 대조를 다시 합니다 (재분석 없음 · 분석 결과와 편집은 그대로).  진행할까요?`)) return;
  const body = new URLSearchParams({ project: job.project, compared_with: job.compared_with || "" });
  const res = await fetch(`/jobs/${jobId}/revision`, { method: "POST", body });
  if (!res.ok) { alert(`대조에 실패했습니다: ${(await res.json()).detail || res.status}`); return; }
  const out = await res.json();
  // 옛 화면 상태(메모리 캐시)는 옛 판정을 들고 있다 — 버리고 다시 연다
  S.viewCache = {};
  const want = S.page ? (S.page.drawing_no || "") : "";
  await open(jobId);
  const page = want && S.pages.find(p => p.drawing_no === want);
  if (page) showPage(page);
  const c = out.counts || {};
  editNotice(`대조를 다시 했습니다 — 추가 ${c.ADDED || 0} · 수정 ${c.MODIFIED || 0}${c.MODIFIED_BEFORE ? ` (+ 이전 태그 ${c.MODIFIED_BEFORE})` : ""} · 삭제 후보 ${c.DELETED_CANDIDATE || 0}`);
}

async function switchView(jobId) {
  if (!jobId || !S.job || S.job.id === jobId || S.loading) return;
  if (S.side) toggleSide(false);          // 나란히 보기는 "왼쪽 = 현재" 를 전제한다
  const want = S.page ? (S.page.drawing_no || "") : "";
  const pair = S.revPair;
  snapshotView();
  const t0 = performance.now();
  const snap = S.viewCache[jobId];
  if (snap) {
    restoreView(snap);
  } else {
    await open(jobId);          // 처음 한 번은 보통의 열기 — 그 뒤로는 캐시
    S.revPair = pair;
    renderRevSwitch();
    snapshotView();
  }
  // 같은 도면번호의 장으로 — 없으면 그 결과의 첫 장
  const page = (want && S.pages.find(p => p.drawing_no === want))
    || (snap ? S.page : null) || S.pages.find(p => (p.layers && Object.keys(p.layers).length)) || S.pages[0];
  if (page) showPage(page);
  S.lastSwitchMs = Math.round(performance.now() - t0);
  const note = $("#rev-switch .rs-note");
  if (note) note.textContent = (S.job.id === (pair || {}).previous ? "직전 결과를 보는 중 — 편집은 그 결과에 저장됩니다 · " : "")
    + `전환 ${S.lastSwitchMs}ms${snap ? " (메모리)" : " (처음 읽음)"}`;
  syncPost({ t: "job", id: S.job.id });     // hotfix68 — 다른 창도 같은 결과로
}

/* hotfix40 — 나란히 보기.
 *
 * 사용자 요구: *"좌측 화면은 최신 rev P&ID 가 출력되고 우측은 이전 rev P&ID 가 출력될 수
 * 있는 기능."*  hotfix39 의 스위치는 화면 전체를 **오가는** 것이었고, 이것은 **동시에**
 * 보는 것이다.  방법:
 *   · 왼쪽은 그대로 현재 결과(최신 Rev).  오른쪽 목록·검토·근거를 숨기고(`#right.compare`)
 *     그 자리에 직전 Rev 의 **같은 도면번호 장**을 그 결과의 상자(층)와 함께 그린다.
 *   · 이전 결과의 장·층은 `/jobs/{prev}/pages` 한 번 — `S.cmp[prevId]` 에 둔다 (행은 읽지
 *     않는다: 상자의 색·종류·검토는 층이 이미 들고 있다).  수정된 행의 이전 자리는
 *     `/jobs/{prev}/anchors`(ID → 장·사각형 · hotfix45).  그림은 서버 디스크 캐시 + 브라우저 캐시.
 *   · 확대(`S.zoom`)와 스크롤은 왼쪽을 따라간다 (오른쪽을 끌면 왼쪽도 따라온다).
 *   · **삭제 후보는 이전 도면 위에** 붉은 ✕ 로 — 그 심볼은 이번 도면에 없어 왼쪽에는
 *     그릴 자리가 없다 (hotfix38 이 목록에만 세운 이유).  자리는 장부의 `anchor` 이고,
 *     그 점을 품는 이전 층 상자가 있으면 그 상자를 붉게 두른다.  판정은 서버의
 *     `deleted_candidates` 그대로이고 여기서 다시 하지 않는다.
 *   · 왼쪽이 직전 결과를 보는 중이면(스위치 '이전') 먼저 현재로 돌아온다 — "왼쪽 = 최신"
 *     이 이 보기의 전제다.  */
function toggleSide(on, manual) {
  const pr = S.revPair;
  if (on && (!pr || !S.job)) return;
  // hotfix46 — 나란히 대조는 실행 프로젝트(태그 대조)만.  입찰 프로젝트는 비교할 열쇠가 없다.
  if (on && (S.rev || {}).compare_basis !== "TAG") return;
  // hotfix68 — 두 창으로 나뉘어 있는 동안 나란히 보기는 목록 창을 통째로 가린다 (도면은 다른 창에 있다).
  if (on && paneSplit()) {
    editNotice("도면 · 목록이 두 창으로 나뉘어 있는 동안에는 나란히 보기를 쓸 수 없습니다 — '한 창으로' 를 누른 뒤 켜세요", "out");
    return;
  }
  // 사람이 끈 것은 기억한다 — 변경이 있는 결과를 열 때 자동으로 켜는 것(`open`)을 그 사람에게는 하지 않는다.
  if (manual) { try { if (on) localStorage.removeItem("pid.side.off"); else localStorage.setItem("pid.side.off", "1"); } catch (e) {} }
  if (on && S.job.id === pr.previous) {
    // 왼쪽이 이전 결과면 현재로 돌아온 뒤 켠다 (switchView 는 side 를 끄므로 끝에 다시 켠다)
    switchView(pr.current).then(() => toggleSide(true));
    return;
  }
  S.side = !!on;
  $("#right").classList.toggle("compare", S.side);
  $("#cmp").classList.toggle("hidden", !S.side);
  // 두 도면이 같은 폭이 되게 경계를 가운데로 — 끄면 사람이 끌어 둔 폭으로 돌아간다.
  const root = document.documentElement;
  if (S.side) { S._leftW = root.style.getPropertyValue("--left-w"); root.style.setProperty("--left-w", "1fr"); }
  else if (S._leftW !== undefined) { if (S._leftW) root.style.setProperty("--left-w", S._leftW); else root.style.removeProperty("--left-w"); S._leftW = undefined; }
  const lt = $("#side-left-tag");
  if (lt) { lt.classList.toggle("hidden", !S.side); lt.textContent = S.side ? `최신 ${pr.currentLabel} — 이번 분석` : ""; }
  renderRevSwitch();
  if (S.side) cmpShow();
}

async function cmpLoad(jobId) {
  if (S.cmp[jobId]) return S.cmp[jobId];
  if (S._cmpLoading && S._cmpLoading.id === jobId) return S._cmpLoading.p;   // 같은 결과를 두 번 읽지 않는다
  const t0 = performance.now();
  // hotfix45 — **수정된 행의 이전 자리**(MOD 고리)는 안정 ID 로 찾는데, 그에 필요한 것은
  // ID 마다 장·사각형 하나뿐이다 (`/anchors` · 약 60KB).  hotfix40 은 그것을 위해 직전
  // 결과의 `/rows?tab=ALL`(QFE 13.7MB · evidence 가 82%)을 통째로 읽어 켤 때 4.6초가
  // 걸리고 힙이 +30MB 였다 — "너무 오래 걸리고 렉 걸린다" 의 첫째 원인.  `/jobs/{id}`
  // 도 쓰는 곳이 없어 뺐다.  층(`/pages`)은 그대로 — 상자의 색·종류·검토는 층이 든다.
  const p = (async () => {
    const [pages, byId] = await Promise.all([
      fetch(`/jobs/${jobId}/pages`).then(r => r.json()),
      fetch(`/jobs/${jobId}/anchors`).then(r => r.ok ? r.json() : {}).catch(() => ({}))]);
    S.cmp[jobId] = { pages, byId: byId || {}, ms: Math.round(performance.now() - t0) };
    S._cmpLoading = null;
    return S.cmp[jobId];
  })();
  S._cmpLoading = { id: jobId, p };
  return p;
}

/* 이 장의 변경 — 왼쪽(현재) 행의 추가·수정과 이 도면번호의 삭제 후보를 한 목록으로.
 * 판정은 서버(`row.rev.state` · `deleted_candidates`) 그대로이고 여기서는 모으기만 한다. */
// hotfix43 — 개정 '수정' 은 태그가 달라진 행뿐이다.  바뀐 태그의 전/후를 상태 기록에서 읽는다.
function tagChange(rev, side) {
  const c = ((rev || {}).changed || []).find(x => x && typeof x === "object" && x.field === "tag_no");
  return c ? (c[side] || "") : "";
}

/* hotfix47 — 짝 없는 기록의 상태 하나.  서버 payload 의 `state`(MODIFIED = 같은 도면에 새 태그가
 * 서서 변경으로만 표기 · 없으면 삭제 후보) 와 `confirmed` 를 읽는다.  옛 대조는 `state` 가 없다. */
function delState(d) {
  if (!d) return "";
  if (d.confirmed) return "DELETED";
  return d.state === "MODIFIED" ? "MODIFIED" : "DELETED_CANDIDATE";
}

function pageChanges(page, dels, prev) {
  const out = [];
  for (const r of S.rows || []) {
    if (r.page_no !== page.page_no) continue;
    const st = (r.rev || {}).state;
    if (st !== "ADDED" && st !== "MODIFIED") continue;
    const was = st === "MODIFIED" && prev && r.rev.id ? prev.byId[r.rev.id] : null;
    out.push({ state: st, key: r.key, row: r, rect: r.rect, prevRect: was ? was.rect : null,
               label: `${r.values.type || r.values.valve_type || ""} ${r.values.tag_no || ""}`.trim(),
               // 바뀐 칸은 서버가 {field, was, now} 로 주거나 이름만 준다 — 이름만 쓴다
               changed: ((r.rev || {}).changed || []).map(x => typeof x === "string" ? x : (x && x.field) || ""),
               // hotfix43 — 수정은 태그가 달라진 것뿐이므로 전 → 후 태그를 함께 든다
               tagWas: tagChange(r.rev, "was"), tagNow: tagChange(r.rev, "now") });
  }
  for (const d of dels || []) {
    // hotfix47 — 같은 도면에 새 태그가 선 기록은 삭제 후보가 아니라 '수정 (이전 태그)' 다
    out.push({ state: delState(d), key: `del:${d.id}`, del: d,
               anchor: d.anchor, label: `${d.type || ""} ${d.tag_no || ""}`.trim() });
  }
  const order = { ADDED: 0, MODIFIED: 1, DELETED_CANDIDATE: 2, DELETED: 2 };
  const y = e => e.rect ? e.rect[1] : (e.anchor ? e.anchor[1] : 0);
  out.sort((a, b) => (order[a.state] - order[b.state]) || (y(a) - y(b)));
  return out;
}

/* 오른쪽 창을 지금 왼쪽 장의 도면번호로 맞춘다.  장이 없으면 그렇게 말한다 (새 장). */
async function cmpShow() {
  const pr = S.revPair;
  if (!S.side || !pr || !S.page) return;
  const head = $("#cmp-head"), foot = $("#cmp-foot"), img = $("#cmp-sheet"), ov = $("#cmp-ov");
  // hotfix45 — 장을 빠르게 넘기면 앞 장의 읽기가 뒤 장 위에 그려질 수 있다.  번호표를 들고
  // 가서 그 사이에 다른 장이 왔으면 그만둔다 (그림 onload 까지).
  const seq = (S._cmpSeq = (S._cmpSeq || 0) + 1);
  head.innerHTML = `<span class="cmp-rev">이전 ${escape(pr.previousLabel)}</span><span class="muted">읽는 중…</span>`;
  const data = await cmpLoad(pr.previous);
  if (!S.side || seq !== S._cmpSeq) return;
  const want = S.page.drawing_no || "";
  // 도면번호가 바뀐 장(hotfix38 `sheets.renumbered`)은 이전 결과에서 **옛 번호**로 찾는다.
  const ren = (((S.rev || {}).sheets || {}).renumbered || []).find(e => e.now === want);
  const auto = (want && data.pages.find(p => p.drawing_no === want))
    || (ren && data.pages.find(p => p.drawing_no === ren.before)) || null;
  // hotfix41 — **사람이 오른쪽 장을 고를 수 있다** (왼쪽 장마다 기억).  직전 리비전에만 있는 장
  // (빠진 장 — 왼쪽에 세울 장이 없어 hotfix40 으로는 볼 수 없었다)과, 태그를 하나도 공유하지
  // 않아 짝이 안 된 장(`-0004` ↔ `-0204`)을 사람이 맞대 보는 길이다.  고른 것은 사실로만 쓴다 —
  // 대조 판정(짝 · 삭제 후보)은 서버 그대로이고 바뀌지 않는다.
  S.cmpPick = S.cmpPick || {};
  const pickNo = S.cmpPick[want];
  const page = (pickNo && data.pages.find(p => p.page_no === pickNo)) || auto;
  S.cmpPage = page;
  const onlyBefore = new Set((((S.rev || {}).sheets || {}).only_before) || []);
  const pickOpts = `<option value="">자동 — 같은 도면번호${auto ? ` (p${auto.page_no})` : " (없음)"}</option>`
    + data.pages.filter(p => p.drawing_no).map(p => `<option value="${p.page_no}"${page && !(!pickNo) && p.page_no === page.page_no ? " selected" : ""}>p${p.page_no} ${escape(p.drawing_no)}${onlyBefore.has(p.drawing_no) ? " — 직전에만 있는 장" : ""}</option>`).join("");
  // 삭제 후보의 도면번호는 장부가 옮긴 **새 번호**다 (hotfix38) — 옛 번호 장에도 그 후보가 선다.
  // 사람이 다른 장을 골랐으면 그 장의 삭제 후보만 — 왼쪽 장의 것을 남의 도면 위에 그리지 않는다
  const manual = !!(pickNo && page && (!auto || page.page_no !== auto.page_no));
  const dels = ((S.rev || {}).deleted_candidates || []).filter(d => manual
    ? d.drawing_no === page.drawing_no
    : (d.drawing_no === want || (page && d.drawing_no === page.drawing_no)));
  const n = page ? Object.values(page.layers || {}).reduce((a, v) => a + v.length, 0) : 0;
  const changes = pageChanges(S.page, dels, data);
  S.cmpChanges = changes;
  const nAdd = changes.filter(c => c.state === "ADDED").length;
  const nMod = changes.filter(c => c.state === "MODIFIED").length;
  const nDel = changes.length - nAdd - nMod;
  head.innerHTML = `<span class="cmp-rev">이전 ${escape(pr.previousLabel)}</span>`
    + (page ? `<span class="cmp-dwg">${escape(page.drawing_no || "")}</span><span class="muted">p${page.page_no}</span>`
              + (manual ? `<span class="muted">사람이 고른 장 — 삭제 후보는 이 장의 것</span>`
                 : (ren && page.drawing_no !== want ? `<span class="muted">도면번호 바뀜 → ${escape(want)} (태그 ${ren.shared}개 공유)</span>` : ""))
            : `<span class="muted">같은 도면번호(${escape(want || "없음")}) 장이 이전 결과에 없습니다 — 이번 리비전에서 새로 든 장</span>`)
    + `<select id="cmp-pick" class="cmp-pick" title="오른쪽에 띄울 직전 Rev 의 장 — 기본은 같은 도면번호.  직전에만 있는 장(빠진 장)도 고를 수 있습니다">${pickOpts}</select>`
    + `<span class="cmp-n">${page ? `상자 ${n}` : ""}</span>`;
  const pk = $("#cmp-pick");
  if (pk) pk.onchange = () => { S.cmpPick[want] = pk.value ? +pk.value : undefined; cmpShow(); };
  foot.textContent = `왼쪽 최신 ${pr.currentLabel} p${S.page.page_no} ↔ 오른쪽 이전 ${pr.previousLabel}`
    + (page ? ` p${page.page_no}` : "") + ` · 같은 도면번호 · 확대·스크롤 공유`
    + (data.ms ? ` · 이전 결과 ${data.ms}ms 에 읽음` : "");
  renderCmpChanges(changes, { add: nAdd, mod: nMod, del: nDel });
  ov.innerHTML = "";
  if (!page) { img.removeAttribute("src"); img.style.display = "none"; return; }
  img.style.display = "";
  img.decoding = "async";          // 큰 그림의 디코드가 화면을 멈추지 않게
  img.onload = () => {
    if (seq !== S._cmpSeq) return;
    S.cmpNatural = { w: img.naturalWidth, h: img.naturalHeight };
    $("#cmp-wrap").style.width = `${S.cmpNatural.w}px`;
    $("#cmp-wrap").style.height = `${S.cmpNatural.h}px`;
    cmpApplyZoom();
    drawCmpOverlay(page, dels, changes);
    cmpSyncScroll();
    cmpPrefetch(data, page);
  };
  img.src = `/jobs/${pr.previous}/page/${page.page_no}.png?zoom=1.6`;
}

/* hotfix45 — 다음·앞 장의 그림(양쪽 결과)을 **화면이 쉬는 동안** 미리 받아 둔다 (브라우저
 * 캐시에만 · 그리지 않는다).  바로 받으면 사람이 곧장 다음 장으로 갈 때 그 장의 그림과
 * 서버에서 겨룬다 (실측: 캐시가 빈 첫 장 바꾸기가 1.7 → 3.3초로 늘었다) — 그래서 1.2초
 * 뒤에, 그 사이 다른 장이 오면 취소한다.  서버 쪽은 디스크 캐시(`page_cache`)가 한 번 그린
 * 장을 다시 그리지 않으므로 둘이 합쳐 "장 바꾸기" 가 90~105ms 가 된다 (QFE 실측). */
function cmpPrefetch(data, page) {
  const pr = S.revPair;
  if (!pr || !data || !page) return;
  if (S._cmpPrefetch) clearTimeout(S._cmpPrefetch);
  const seq = S._cmpSeq;
  S._cmpPrefetch = setTimeout(() => {
    S._cmpPrefetch = 0;
    if (!S.side || seq !== S._cmpSeq) return;
    const want = [];
    const idx = data.pages.findIndex(p => p.page_no === page.page_no);
    for (const k of [1, -1]) { const q = idx >= 0 && data.pages[idx + k]; if (q) want.push([pr.previous, q.page_no]); }
    const cur = (S.pages || []).findIndex(p => S.page && p.page_no === S.page.page_no);
    for (const k of [1, -1]) { const q = cur >= 0 && S.pages[cur + k]; if (q && S.job) want.push([S.job.id, q.page_no]); }
    for (const [job, n] of want) {
      const im = new Image();
      im.decoding = "async";
      im.src = `/jobs/${job}/page/${n}.png?zoom=1.6`;
    }
  }, 1200);
}

function cmpApplyZoom() {
  if (!S.side || !S.zoom) return;
  $("#cmp-wrap").style.transform = `scale(${S.zoom})`;
}

/* 이전 결과의 상자 — 색은 그 결과의 SCOPE 층 그대로(`SCOPE_COLOR`), 파선은 밸브.
 * 행은 읽지 않으므로 사람이 그 결과에서 고친 SCOPE 는 모른다 — 머리줄에 그렇게 적지 않고
 * 상자 툴팁에 "분석 때 층" 이라고 적는다. */
function drawCmpOverlay(page, dels, changes) {
  const ov = $("#cmp-ov");
  ov.innerHTML = "";
  if (!S.cmpNatural) return;
  const scale = S.cmpNatural.w / (page.width || 1);
  ov.setAttribute("viewBox", `0 0 ${S.cmpNatural.w} ${S.cmpNatural.h}`);
  const items = [];
  for (const [tab, arr] of Object.entries(page.layers || {})) for (const it of arr) items.push({ ...it, tab });
  const area = r => Math.abs((r[2] - r[0]) * (r[3] - r[1]));
  items.sort((a, b) => area(b.rect) - area(a.rect));
  const inside = (r, x, y) => r && x >= r[0] && x <= r[2] && y >= r[1] && y <= r[3];
  const gone = new Set(), goneMod = new Set();
  for (const d of dels || []) {
    const [ax, ay] = d.anchor || [];
    const hit = items.filter(it => inside(it.rect, ax, ay)).sort((a, b) => area(a.rect) - area(b.rect))[0];
    if (hit) { gone.add(hit.key); if (delState(d) === "MODIFIED") goneMod.add(hit.key); }
  }
  for (const it of items) {
    const [x0, y0, x1, y1] = it.rect;
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("x", x0 * scale); r.setAttribute("y", y0 * scale);
    r.setAttribute("width", Math.max(2, (x1 - x0) * scale));
    r.setAttribute("height", Math.max(2, (y1 - y0) * scale));
    r.setAttribute("class", "cdet" + (it.kind === "VALVE" ? " valve" : "")
      + (it.row === false ? " excluded" : "") + (gone.has(it.key) ? " gone" : ""));
    r.setAttribute("stroke", SCOPE_COLOR[it.scope || "INCLUDED"] || "#8e8e93");
    const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
    tip.textContent = `${it.label || ""} · ${it.tab || ""} · 분석 때 층 ${it.scope || "INCLUDED"}`
      + (gone.has(it.key) ? (goneMod.has(it.key) ? " · 이번 분석에 이 태그가 없음 — 같은 도면에 새 태그가 서서 '수정 (이전 태그)'" : " · 이번 분석에서 짝이 없는 삭제 후보") : "");
    r.appendChild(tip);
    ov.appendChild(r);
  }
  // 수정된 행 — 이전 자리(안정 ID 로 찾은 이전 행의 상자)에 초록 고리와 MOD 글자.
  // 추가된 행 — 이전 도면에는 없으므로 **현재 자리에 점선 유령 상자**와 'ADD (이전엔 없음)'.
  const svgText = (x, y, size, cls, str) => {
    const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.setAttribute("x", x); t.setAttribute("y", y); t.setAttribute("font-size", size);
    t.setAttribute("class", cls); t.textContent = str; return t;
  };
  for (const c of changes || []) {
    if (c.state === "MODIFIED" && c.prevRect && c.prevRect.length === 4) {
      const [x0, y0, x1, y1] = c.prevRect;
      const g = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      g.setAttribute("x", x0 * scale - 3); g.setAttribute("y", y0 * scale - 3);
      g.setAttribute("width", Math.max(2, (x1 - x0) * scale) + 6); g.setAttribute("height", Math.max(2, (y1 - y0) * scale) + 6);
      g.setAttribute("class", "cmp-mod" + (S.sel === c.key ? " sel" : ""));
      const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
      tip.textContent = `수정 — ${c.label} · ${c.tagWas || "(태그 없음)"} → ${c.tagNow || "(태그 없음)"}`;
      g.appendChild(tip);
      g.onclick = (ev) => { ev.stopPropagation(); focusChange(c); };
      ov.appendChild(g);
      ov.appendChild(svgText(x0 * scale, y0 * scale - 4, Math.max(9, (y1 - y0) * scale * 0.35), "cmp-modtag", "MOD"));
    } else if (c.state === "ADDED" && c.rect && c.rect.length === 4) {
      const [x0, y0, x1, y1] = c.rect;
      const g = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      g.setAttribute("x", x0 * scale); g.setAttribute("y", y0 * scale);
      g.setAttribute("width", Math.max(2, (x1 - x0) * scale)); g.setAttribute("height", Math.max(2, (y1 - y0) * scale));
      g.setAttribute("class", "cmp-add" + (S.sel === c.key ? " sel" : ""));
      const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
      tip.textContent = `추가 — ${c.label} · 이전 ${(S.revPair || {}).previousLabel || ""} 에는 이 자리에 행이 없었습니다`;
      g.appendChild(tip);
      g.onclick = (ev) => { ev.stopPropagation(); focusChange(c); };
      ov.appendChild(g);
      ov.appendChild(svgText(x0 * scale, y0 * scale - 4, Math.max(9, (y1 - y0) * scale * 0.35), "cmp-addtag", "ADD (이전엔 없음)"));
    }
  }
  // 삭제 후보 — 붉은 ✕ 와 'DEL' 글자.  자리는 장부의 anchor (이전 Rev 좌표).
  for (const d of dels || []) {
    const [ax, ay] = d.anchor || [];
    if (ax === undefined) continue;
    const cx = ax * scale, cy = ay * scale;
    const hit = items.filter(it => inside(it.rect, ax, ay)).sort((a, b) => area(a.rect) - area(b.rect))[0];
    const h = hit ? (hit.rect[3] - hit.rect[1]) * scale : 24;
    const rad = Math.max(6, h * 0.22);
    const stt = delState(d);
    // hotfix47 — 같은 도면에 새 태그가 선 기록은 삭제가 아니라 **변경** — 초록 MOD 고리로
    // (붉은 ✕ 는 삭제 후보·확정에만).  판정은 서버 payload 의 `state` 그대로.
    const isMod = stt === "MODIFIED";
    const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    const px = hit ? hit.rect[2] * scale : cx, py = hit ? hit.rect[1] * scale : cy;
    dot.setAttribute("cx", px); dot.setAttribute("cy", py); dot.setAttribute("r", rad);
    dot.setAttribute("class", isMod ? "modmark" : "delmark");
    const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
    t.setAttribute("x", px); t.setAttribute("y", py); t.setAttribute("font-size", rad * 1.5);
    t.setAttribute("class", isMod ? "modmark-t" : "delmark-t"); t.textContent = isMod ? "≠" : "✕";
    const tag = document.createElementNS("http://www.w3.org/2000/svg", "text");
    tag.setAttribute("x", (hit ? hit.rect[0] * scale : cx - rad)); tag.setAttribute("y", (hit ? hit.rect[1] * scale : cy) - 3);
    tag.setAttribute("font-size", Math.max(9, rad * 1.6)); tag.setAttribute("class", isMod ? "cmp-modtag" : "deltag");
    tag.textContent = isMod ? "MOD" : (d.confirmed ? "DEL" : "DEL?");
    const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
    tip.textContent = deletedRemark(d, (S.rev || {}).compared_with || "") + (d.type ? ` · ${d.type}` : "") + (d.tag_no ? ` ${d.tag_no}` : "");
    dot.appendChild(tip);
    for (const el of [dot, t]) el.onclick = (ev) => { ev.stopPropagation(); focusChange((S.cmpChanges || []).find(c => c.key === `del:${d.id}`) || { state: stt, key: `del:${d.id}`, anchor: d.anchor, del: d }); };
    ov.appendChild(dot); ov.appendChild(t); ov.appendChild(tag);
  }
}

/* 비교 창 아래의 **변경 목록** — 이 장에서 이전 대비 추가·수정·삭제된 것만.  누르면 두 창이
 * 그 자리로 간다 (왼쪽은 그 행을 고르고, 오른쪽은 스크롤 동기로 따라온다).  ◀ ▶ 로 차례로. */
function renderCmpChanges(changes, n) {
  const box = $("#cmp-changes");
  if (!box) return;
  S.cmpIdx = -1;
  if (!changes.length) {
    box.innerHTML = `<div class="cmp-ch-head"><b>이 장 변경 없음</b><span class="muted">이전 대비 추가·수정·삭제된 행이 없습니다 — 두 도면이 같은 결과입니다</span></div>`;
    return;
  }
  const mark = { ADDED: ["＋", "add"], MODIFIED: ["≠", "mod"], DELETED_CANDIDATE: ["－", "del"], DELETED: ["－", "del"] };
  box.innerHTML = `<div class="cmp-ch-head"><b>이 장 변경 ${changes.length}</b>`
    + `<span class="add">추가 ${n.add}</span><span class="mod">수정 ${n.mod}</span><span class="del">삭제 ${n.del}</span>`
    + `<span class="sp"></span><button type="button" class="ghost mini" data-step="-1" title="앞 변경으로">◀</button>`
    + `<button type="button" class="ghost mini" data-step="1" title="다음 변경으로 (Alt+→)">▶</button></div>`
    + `<div class="cmp-ch-list">` + changes.map((c, i) => {
        const [g, cls] = mark[c.state];
        // hotfix47 — 수정은 셋: 태그가 바뀐 짝(전 → 후) · 짝 없이 변경으로만 표기한 새 태그 ·
        // 같은 도면에 새 태그가 서서 변경으로만 표기한 이전 태그(기록)
        const why = c.state === "MODIFIED"
          ? (c.del ? `이전 태그 — 이번 분석에 없음 (같은 도면에 새 태그 ${(c.del.tag_candidates || []).length}개 · 태그 변경인지 삭제인지 도면이 가르지 않음)`
             : ((c.row && (c.row.rev || {}).basis === "AMBIGUOUS")
                ? "태그 변경 또는 추가 — 같은 도면에서 사라진 태그가 있어 도면이 가르지 않음"
                : `태그 ${c.tagWas || "(없음)"} → ${c.tagNow || "(없음)"}`))
          : c.state === "ADDED" ? "이전엔 없음"
          : (c.del && c.del.confirmed ? "삭제 확정" : "삭제 후보");
        return `<button type="button" class="cmp-ch ${cls}" data-i="${i}" title="${escape(why)}"><span class="g">${g}</span>${escape(c.label || c.key)}<span class="muted"> ${escape(why)}</span></button>`;
      }).join("") + `</div>`;
  box.querySelectorAll("button.cmp-ch").forEach(b => b.onclick = () => focusChange(changes[+b.dataset.i], +b.dataset.i));
  box.querySelectorAll("button[data-step]").forEach(b => b.onclick = () => {
    const i = (S.cmpIdx + (+b.dataset.step) + changes.length) % changes.length;
    focusChange(changes[i], i);
  });
}

/* 변경 하나로 두 창을 맞춘다.  추가·수정은 왼쪽 행을 고른다(→ 가운데로 · 오른쪽은 동기);
 * 삭제는 왼쪽에 자리가 없으므로 오른쪽을 이전 자리로 옮기고(왼쪽이 따라온다) 목록의 삭제 행을 고른다. */
function focusChange(c, idx) {
  if (!c) return;
  if (idx === undefined) idx = (S.cmpChanges || []).indexOf(c);
  S.cmpIdx = idx;
  document.querySelectorAll("#cmp-changes button.cmp-ch").forEach((b, i) => b.classList.toggle("on", i === idx));
  if (!c.del) {
    select(c.key, true);
  } else {
    // 기록(이전 태그 · 삭제 후보)은 왼쪽에 자리가 없다 — 오른쪽을 이전 자리로
    const [ax, ay] = c.anchor || [];
    if (ax !== undefined && S.cmpNatural && S.cmpPage) {
      if (S.zoom < SYMBOL_ZOOM) { S.zoom = SYMBOL_ZOOM; applyZoom(); }
      const scale = S.cmpNatural.w / (S.cmpPage.width || 1);
      const cs = $("#cmp-stage");
      cs.scrollLeft = ax * scale * S.zoom - cs.clientWidth / 2;
      cs.scrollTop = ay * scale * S.zoom - cs.clientHeight / 2;
      cmpSyncScroll("cmp");
    }
    // 목록의 삭제 행을 고른다 (fromGrid=false — 왼쪽에는 그 심볼이 없어 가운데로 옮길 것이 없다)
    if ((S.deletedRows || []).some(r => r.key === c.key)) select(c.key, false);
  }
  if (S.cmpPage) drawCmpOverlay(S.cmpPage, (S.cmpChanges || []).filter(x => x.del).map(x => x.del), S.cmpChanges);
}

/* 스크롤 동기 — 왼쪽이 움직이면 오른쪽이, 오른쪽을 끌면 왼쪽이.  되돌이는 깃발로 막는다. */
function cmpSyncScroll(from) {
  if (!S.side || S._cmpSyncing) return;
  // hotfix45 — 스크롤 이벤트마다 바로 쓰지 않고 **프레임에 한 번**만 쓴다.  휠·끌기는 한
  // 프레임에 여러 번 오고, 그때마다 반대쪽을 옮기면 두 창이 번갈아 레이아웃을 다시 해
  // 끊긴다.  마지막 값만 남기고 다음 프레임에 한 번 옮긴다 (같으면 안 쓴다).
  S._cmpFrom = from;
  if (S._cmpRaf) return;
  S._cmpRaf = requestAnimationFrame(() => {
    S._cmpRaf = 0;
    if (!S.side) return;
    const a = $("#stage"), b = $("#cmp-stage");
    const [src, dst] = S._cmpFrom === "cmp" ? [b, a] : [a, b];
    S._cmpSyncing = true;
    if (dst.scrollLeft !== src.scrollLeft) dst.scrollLeft = src.scrollLeft;
    if (dst.scrollTop !== src.scrollTop) dst.scrollTop = src.scrollTop;
    requestAnimationFrame(() => { S._cmpSyncing = false; });
  });
}
(() => {
  const st = $("#stage"), cs = $("#cmp-stage");
  if (!st || !cs) return;
  st.addEventListener("scroll", () => cmpSyncScroll("stage"), { passive: true });
  cs.addEventListener("scroll", () => cmpSyncScroll("cmp"), { passive: true });
  // 오른쪽 창도 끌어서 팬 — 왼쪽과 같은 규칙(스크롤만 옮긴다 · 12회차).
  let drag = null;
  cs.addEventListener("mousedown", (e) => { if (e.button !== 0) return; drag = { x: e.clientX, y: e.clientY, l: cs.scrollLeft, t: cs.scrollTop }; cs.classList.add("panning"); });
  window.addEventListener("mousemove", (e) => { if (!drag) return; cs.scrollLeft = drag.l - (e.clientX - drag.x); cs.scrollTop = drag.t - (e.clientY - drag.y); });
  window.addEventListener("mouseup", () => { drag = null; cs.classList.remove("panning"); });
  // 휠 확대도 왼쪽과 같은 배율로 — 왼쪽의 zoomBy 를 그대로 부른다.
  cs.addEventListener("wheel", (e) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    if (typeof zoomBy === "function") zoomBy(e.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, null);
  }, { passive: false });
})();

/* 삭제 후보 한 건의 근거.  좌표 · 반경 · 가장 가까웠던 후보까지 거리 셋이
 * 있어야 "도면에서 지워졌다" 와 "이번에 못 뽑았다" 를 사람이 가를 수 있다. */
function showDeletedEvidence(d) {
  // 근거 셋을 맨 위에 둔다.  패널이 232px 이라 아래로 밀리면 스크롤해야 보이고,
  // 정작 판단에 쓰는 값이 그 셋이다.
  const isMod = delState(d) === "MODIFIED";
  const rows = [
    ["상태", d.confirmed ? "삭제 확정 — 산출물에 취소선으로 나갑니다"
      : (isMod ? "수정 (이전 태그) — 같은 도면에 새 태그가 서서 삭제 후보가 아니라 변경으로 표기 · 산출물에 나가지 않습니다"
         : "삭제 후보 — 확정 전에는 산출물에 나가지 않습니다")],
    // hotfix47 — 같은 도면의 새 태그.  이 기록의 태그가 그중 하나로 바뀐 것일 수 있다 — 고르지 않는다
    ...(isMod ? [["같은 도면의 새 태그", (d.tag_candidates || []).join(", ") || "(없음)"]] : []),
    ...(isMod && (d.same_tag_now || []).length ? [["같은 태그의 이번 표기", `${d.same_tag_now.join("/")} — 표기(abbreviation)가 바뀐 것일 수 있습니다 · 고르지 않습니다`]] : []),
    // hotfix38 — 태그가 있던 기록이면 그 태그가 이번 분석 어디에도 없는지(또는
    // 다른 도면에 섰는지)가 첫 근거다.  좌표·반경은 태그 없는 기록의 근거다.
    ...(d.tag_no ? [["태그", `${d.tag_no} — ${(d.tag_elsewhere || []).length
      ? "이번 분석에서 다른 도면(" + d.tag_elsewhere.join(", ") + ")에 섰습니다 — 옮김일 수 있습니다"
      : "이번 분석 어디에도 없습니다"}`]] : []),
    ["직전 리비전 자리", `(${(d.anchor || []).join(", ")}) — 표식을 그리는 자리일 뿐 판정에 쓰지 않습니다`],
    // hotfix46 — 반경·최근접은 위치 비교의 근거였다.  옛 대조(hotfix46 이전)가 남긴 값만 보인다.
    ...(d.radius ? [["매칭 반경 (옛 대조)", `${d.radius}pt — ${d.radius_source === "DRAWING_BUBBLE"
      ? "이 도면 버블 긴변" : d.radius_source}`],
    ["가장 가까웠던 같은 TYPE 후보 (옛 대조)",
     d.nearest_distance === null ? "그 도면에 같은 TYPE 이 하나도 없음"
       : `${d.nearest_distance}pt 떨어져 있었습니다`]] : []),
    ["안정 ID", `${d.id} · ${d.type || "TYPE 없음"} · ${d.drawing_no} (p${d.page_no})`],
    ["직전 Description", d.description || "(없음)"],
  ];
  $("#evidence").innerHTML =
    `<div class="ev-head"><h3>${isMod ? "수정 (이전 태그)" : "삭제 후보"} — ${escape(d.id)}</h3></div>`
    + (isMod
       ? `<p class="muted">이번 분석에 이 태그(같은 TYPE)가 없는데 같은 도면에 새 태그가 섰습니다.`
         + ` 태그가 바뀐 것인지 지워지고 새로 선 것인지 도면이 가르지 않아 변경으로만 표기합니다 —`
         + ` 삭제였다면 '삭제 확정' 으로 굳히세요.</p>`
       : `<p class="muted">이번 분석에 이 태그(같은 TYPE)가 없습니다. 도면에서 지워진 것인지,`
         + ` 이번에 못 뽑은 것인지는 기계가 가르지 못합니다 — 아래 근거를 보고`
         + ` 확정하세요.</p>`)
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

/* hotfix38 — 삭제 행 Remark 한 줄.  Excel 의 `revision_remark` 와 같은 낱말을 쓴다. */
function deletedRemark(d, against) {
  const vs = against ? `${against} 대비 ` : "";
  // hotfix47 — 같은 도면에 새 태그가 선 기록은 '수정 (이전 태그)' (Excel 변경 내역과 같은 낱말)
  if (!d.confirmed && delState(d) === "MODIFIED") {
    const nt = d.tag_candidates || [];
    return `${vs}수정 (이전 태그) · 태그 ${d.tag_no} 가 이번 분석에 없고 같은 도면에 새 태그 ${nt.length}개(${nt.join(", ")})가 섰습니다 — 태그 변경인지 삭제인지 도면이 가르지 않아 수정으로만 표기`
      + ((d.same_tag_now || []).length ? ` · 같은 태그가 이번에는 ${d.same_tag_now.join("/")} 로 섰습니다 (표기가 바뀐 것일 수 있음)` : "");
  }
  const head = d.confirmed ? `${vs}삭제 (확정)` : `${vs}삭제 후보 — 확정 전`;
  const why = d.tag_no
    ? ((d.tag_elsewhere || []).length
        ? `태그 ${d.tag_no} 가 이번 분석에서 다른 도면(${d.tag_elsewhere.join(", ")})에 섰습니다 — 옮김일 수 있습니다`
        : `태그 ${d.tag_no} 가 이번 분석 어디에도 없습니다`)
    : (d.nearest_distance === null || d.nearest_distance === undefined
        ? "그 도면에 같은 TYPE 이 하나도 없습니다"
        : `가장 가까운 같은 TYPE 이 ${d.nearest_distance}pt (반경 ${d.radius}pt)`);
  return `${head} · ${why}`;
}

/* hotfix68 — 행에 딸린 작은 읽기 다섯은 행을 기다리지 않고 같이 띄운다 (각자 실패해도 화면은 선다). */
function rowSideFetches(id) {
  const J = (u, dflt) => fetch(u).then(r => r.json()).catch(() => dflt);
  return Promise.all([J(`/jobs/${id}/markup`, null), J(`/jobs/${id}/axis_overrides`, {}),
                      J(`/jobs/${id}/review`, null), J(`/jobs/${id}/feedback?limit=1`, {}),
                      J(`/jobs/${id}/reports`, {})]);
}
async function loadRows(pre, sidePre) {
  const id = S.job.id;
  const side = sidePre || rowSideFetches(id);
  S.rows = await (pre || fetch(`/jobs/${id}/rows?tab=ALL&slim=1`).then(r => r.json()));
  S.rowByKey = Object.fromEntries(S.rows.map(r => [r.key, r]));
  const [markup, axisOv, review, feedback, reports] = await side;
  S.markupSummary = markup;
  updateMarkupNote();
  // ④ 행의 FROM/TO 확정 장부 - 근거 패널의 "FROM/TO 확정"·"확정 승계" 표시용.
  // 프로젝트가 없는 job 은 빈 객체가 온다.
  S.axisOv = axisOv || {};
  // 오버레이가 행 상태를 키로 찾을 수 있게.  도면에는 추가·수정만 그린다 -
  // 삭제된 것은 이번 도면에 심볼이 없어 그릴 좌표가 없다.
  S.revByKey = {};
  for (const r of S.rows) {
    const st = (r.rev || {}).state;
    if (st === "ADDED" || st === "MODIFIED") S.revByKey[r.key] = st;
  }
  // 삭제 후보도 리스트에 세운다 - 세 상태가 한 화면에 보여야 한다.  도면에는
  // 그리지 않는다: 이번 리비전에 그 심볼이 없으므로 그릴 좌표가 없다.
  // hotfix38 — 삭제 행의 Remark 는 **그 사실**을 적는다 (사용자 요구: "List 에서
  // 삭제 표기만 해주고 remark 에 표기").  확정 전후를 가르고, 태그가 있던 행이면
  // 그 태그가 이번 분석 어디에도 없다는 것(또는 다른 도면에 섰다는 것)까지 말한다.
  const against = (S.rev || {}).compared_with || "";
  S.deletedRows = ((S.rev || {}).deleted_candidates || []).map(d => ({
    key: `del:${d.id}`, tab: d.tab || "FIELD", page_no: d.page_no || 0,
    drawing_no: d.drawing_no || "", origin: "", rect: [],
    values: { ...(d.values || {}), type: d.type || "",
              tag_no: (d.values || {}).tag_no || d.tag_no || "",
              description: d.description || "",
              remark: deletedRemark(d, against) },
    ai: {}, user: {}, evidence: {}, needs_review: "", annotation: "",
    conflict: {}, deleted: true, added: false, removed: false,
    review_codes: [], review_state: {},
    rev: { id: d.id, state: delState(d), role: "before" },
    delCand: d,
  }));
  S.counts = { ALL: S.rows.length, REVIEW: 0 };
  S.originCounts = {};
  for (const r of S.rows) {
    S.counts[r.tab] = (S.counts[r.tab] || 0) + 1;
    if (r.needs_review || r.deleted) S.counts.REVIEW++;
    S.originCounts[r.origin] = (S.originCounts[r.origin] || 0) + 1;
  }
  S.jobReview = review || await (await fetch(`/jobs/${id}/review`)).json();
  S.review = S.jobReview;
  S.feedback = (feedback || {}).count;
  S.reports = (reports || {}).count;
  updateReportBadge();
  await Promise.all([buildScope(), loadUnjudged(), showTemplates()]);
  showAppliedRules();
  buildTabs();
  updateBadge();
  renderReviewPanel();
  renderGrid();
}

$("#only-changed").onchange = (e) => {
  S.onlyChanged = e.target.checked;
  renderGrid();
};
/* hotfix38 — 개정 상태로 좁히는 선택 상자.  "개정된 행만" 체크와 함께 쓸 수 있고
 * 선택이 있으면 그 상태만 남는다 (추가만 · 삭제만 · 수정만). */
$("#rev-filter").onchange = (e) => {
  S.revFilter = e.target.value || "";
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
      || S.originFilter || S.onlyReview || S.onlyChanged || S.revFilter
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
  loadMultipliers();
  loadSheetNumbers();
}

/* ---------------------------------------------------------------------------
 * 유닛 승수 — 도면이 말하지 않을 때 **사람이 한 번 답하는 자리** (31회차)
 *
 * 행마다 묻지 않는다.  SADARA 는 유닛 `10` 하나에 82행이고, 82번 묻는 화면은
 * 자리를 만든 것이 아니라 일을 만든 것이다.  그래서 **유닛코드로 묶고**
 * 누르기 전에 적용 범위(몇 장 · 몇 행)와 Q'ty 전/후를 먼저 보인다.
 *
 * 넣어도 지금 결과는 바뀌지 않는다 — 다시 분석해야 반영된다.  15회차
 * `adopt_legend_profile` 과 같은 규율이다: 바꿨다고 말하면서 바꾸지 않으면
 * 화면이 거짓말을 한다.
 * ------------------------------------------------------------------------- */
/* ---------------------------------------------------------------------------
 * hotfix65 — 페이지별 승수: 여러 장을 고르고 장마다 승수를 적어 **바로** 적용한다.
 *
 * 사용자: *"수량 승수는, 사용자가 여러 page 를 선택할 수 있게 하고, 해당 page 별
 * 승수를 입력해서 적용할 수 있게 해줘.  그리고 적용되면 수량이 자동으로 바껴야 해."*
 *
 * 아래 유닛코드 승수(31회차)와 **다른 길**이다 — 그것은 프로젝트에 적혀 *다음
 * 분석부터* 쓰이고, 이것은 지금 결과의 행에 사람이 고친 Q'ty 로 적힌다
 * (hotfix59 `x N` 라벨 편집과 같은 칸 · 같은 ✎ · 다음 리비전에 안정 ID 로 승계).
 *
 * 새 Q'ty = 그 행의 **기본 개수** × 사람이 적은 승수.  기본 개수는 엔진이 적은
 * 근거(`qty_basis` 의 `N symbol x F` — 도면 Q'ty ÷ 도면 승수)에서 읽는다 — Typical
 * 상세 한 벌(x4)처럼 승수가 아닌 곱은 그대로 남는다.  근거를 못 읽으면 1 이다
 * (LS 묶음 `1 x 시트 승수` 도 1).  계산은 여기 한 곳이고 서버는 받은 정수를 적기만
 * 한다 (`POST /jobs/{id}/qty_bulk` — PATCH 와 같은 db 함수 · 같은 편집 이력).
 * ------------------------------------------------------------------------- */
function qtyBase(row) {
  const ai = (row.ai || {}).qty;
  const b = String(((row.evidence || {}).qty_basis) || "");
  const m = b.match(/^\s*(\d+)\s+(?:symbol|point)s?\s+x\s+(\d+)/);
  if (m && ai != null && ai !== "" && +m[2] > 0) {
    const base = Math.round(Number(ai) / +m[2]);
    return base >= 1 ? base : 1;
  }
  return 1;
}
function rowMultiplier(row) {
  const q = cellValue(row, "qty");
  if (q === "" || q == null || isNaN(Number(q))) return null;
  const b = qtyBase(row);
  return Number(q) / b;
}
function pageMultPages() {
  const by = new Map();
  for (const r of S.rows || []) {
    if (r.deleted || r.removed || r.delCand) continue;
    if (!by.has(r.page_no)) by.set(r.page_no, []);
    by.get(r.page_no).push(r);
  }
  const pgs = new Map((S.pages || []).map(p => [p.page_no, p]));
  return [...by.keys()].sort((a, b) => a - b).map(no => {
    const rows = by.get(no);
    const mults = new Map();
    let qty = 0, human = 0;
    for (const r of rows) {
      const m = rowMultiplier(r);
      const k = m == null ? "?" : String(Math.round(m * 100) / 100);
      mults.set(k, (mults.get(k) || 0) + 1);
      qty += Number(cellValue(r, "qty")) || 0;
      if (r.user && r.user.qty !== undefined) human += 1;
    }
    const pg = pgs.get(no) || {};
    return { no, rows, qty, human, drawing: pg.drawing_no || "",
             mults: [...mults.entries()].sort((a, b) => b[1] - a[1]) };
  });
}
/* 고른 장 · 적은 승수로 무엇이 바뀌는지 — 누르기 전에 보인다 (31회차 규율). */
function pageMultPlan() {
  const st = S.pageMult;
  const plan = [], missing = [];
  let before = 0, after = 0;
  for (const p of pageMultPages()) {
    if (!st.checked.has(p.no)) continue;
    const v = String(st.vals[p.no] ?? "").trim();
    if (!/^\d+$/.test(v) || +v < 1) { missing.push(p.no); continue; }
    const m = +v;
    for (const r of p.rows) {
      const now = cellValue(r, "qty");
      const nq = qtyBase(r) * m;
      before += Number(now) || 0; after += nq;
      if (String(now ?? "") !== String(nq)) plan.push({ row: r, page: p.no, m, value: nq });
    }
  }
  return { plan, missing, before, after };
}
function renderPageMult(box) {
  const st = S.pageMult || (S.pageMult = { checked: new Set(), vals: {}, last: null });
  const pages = pageMultPages();
  const wrap = box.querySelector(".pmult");
  if (!wrap) return;
  if (!pages.length) { wrap.innerHTML = ""; return; }
  const nChk = pages.filter(p => st.checked.has(p.no)).length;
  const { plan, missing, before, after } = pageMultPlan();
  const multTxt = (p) => p.mults.map(([k, n]) => (k === "?" ? "?" : "x" + k) + (p.mults.length > 1 ? `(${n})` : "")).join(" · ");
  wrap.innerHTML = `<div class="mhead pm-head">페이지별 승수 <span class="muted">— 여러 장을 고르고
        장마다 승수를 적으면 <b>지금 결과의 Q'ty 가 바로</b> 바뀝니다 (Q'ty = 기본 개수 × 승수)</span></div>
      <div class="pm-tools">
        <label class="pm-all"><input type="checkbox" class="pm-chkall"
          ${nChk && nChk === pages.length ? "checked" : ""}> 전체 선택</label>
        <span class="muted">선택 ${nChk}장</span>
        <label>선택한 장에 같은 승수 x<input class="pm-fillv" type="number" min="1" step="1" placeholder="예: 2"></label>
        <button class="pm-fill ghost" ${nChk ? "" : "disabled"}>채우기</button>
        <button class="pm-apply primary" ${plan.length ? "" : "disabled"}>적용 (${plan.length}행)</button>
        <button class="pm-revert ghost" ${nChk ? "" : "disabled"}
          title="고른 장에서 사람이 고친 Q'ty 를 도면 값으로 되돌립니다">도면 값으로</button>
      </div>
      <div class="pm-preview muted">${nChk
        ? (plan.length || missing.length
            ? `고른 장 Q'ty <b>${before}</b> → 적용하면 <b>${after}</b>`
              + (missing.length ? ` · 승수를 안 적은 장 ${missing.map(n => "p" + n).join(", ")} 은 건너뜁니다` : "")
            : "고른 장의 승수 칸을 채우면 바뀔 Q'ty 가 여기 보입니다")
        : "장을 고르세요 — Shift 를 누른 채 고르면 사이의 장이 모두 골라집니다"}</div>
      <div class="pm-list">${pages.map(p => {
        const on = st.checked.has(p.no);
        const v = st.vals[p.no] ?? "";
        const nv = /^\d+$/.test(String(v)) && +v >= 1
          ? p.rows.reduce((a, r) => a + qtyBase(r) * +v, 0) : null;
        return `<div class="pm-row${on ? " on" : ""}" data-page="${p.no}">
          <input type="checkbox" class="pm-chk" ${on ? "checked" : ""}>
          <a class="pm-p" title="이 장을 도면 창에 띄웁니다">p${p.no}</a>
          <span class="pm-dwg" title="${attr(p.drawing)}">${escape(p.drawing || "")}</span>
          <span class="pm-n muted">${p.rows.length}행</span>
          <span class="pm-now" title="지금 승수 (Q'ty ÷ 기본 개수) · 괄호는 행 수">지금 ${multTxt(p)}${p.human ? ` <i class="pm-ed" title="사람이 고친 Q'ty ${p.human}행">✎${p.human}</i>` : ""}</span>
          <label class="pm-x">x<input class="pm-val" type="number" min="1" step="1" value="${attr(v)}"></label>
          <span class="pm-after muted">Q'ty ${p.qty}${nv != null ? ` → <b>${nv}</b>` : ""}</span>
        </div>`;
      }).join("")}</div>`;
  const rerender = () => { renderPageMult(box); };
  wrap.querySelector(".pm-chkall").onchange = (ev) => {
    st.checked = ev.target.checked ? new Set(pages.map(p => p.no)) : new Set();
    rerender();
  };
  wrap.querySelectorAll(".pm-row").forEach((el, i) => {
    const no = +el.dataset.page;
    const chk = el.querySelector(".pm-chk");
    chk.onclick = (ev) => {
      const want = chk.checked;
      // Shift — 직전에 누른 장과 이 장 사이를 같은 상태로 (목록 순서 기준).
      if (ev.shiftKey && st.last != null) {
        const a = pages.findIndex(p => p.no === st.last);
        const lo = Math.min(a, i), hi = Math.max(a, i);
        if (a >= 0) for (let k = lo; k <= hi; k++) want ? st.checked.add(pages[k].no) : st.checked.delete(pages[k].no);
      } else {
        want ? st.checked.add(no) : st.checked.delete(no);
      }
      st.last = no;
      rerender();
    };
    el.querySelector(".pm-p").onclick = () => {
      const pg = (S.pages || []).find(p => p.page_no === no);
      if (pg) showPage(pg);
    };
    const val = el.querySelector(".pm-val");
    // 칸에 적으면 그 장이 골라진다 — 적고 나서 또 고르지 않게.  다시 그리면 입력이 끊기므로
    // 이 줄과 위 요약만 고친다.
    val.oninput = () => {
      st.vals[no] = val.value.trim();
      if (st.vals[no] !== "") { st.checked.add(no); chk.checked = true; el.classList.add("on"); }
      const p = pages.find(x => x.no === no);
      const v = st.vals[no];
      const nv = /^\d+$/.test(v) && +v >= 1 ? p.rows.reduce((a, r) => a + qtyBase(r) * +v, 0) : null;
      el.querySelector(".pm-after").innerHTML = `Q'ty ${p.qty}${nv != null ? ` → <b>${nv}</b>` : ""}`;
      _pageMultSummary(wrap, pages);
    };
    val.onkeydown = (ev) => { if (ev.key === "Enter") { ev.preventDefault(); applyPageMult(); } };
  });
  wrap.querySelector(".pm-fill").onclick = () => {
    const v = wrap.querySelector(".pm-fillv").value.trim();
    if (!/^\d+$/.test(v) || +v < 1) { editNotice("승수는 1 이상의 정수입니다", "out"); return; }
    for (const no of st.checked) st.vals[no] = v;
    rerender();
  };
  wrap.querySelector(".pm-fillv").onkeydown = (ev) => {
    if (ev.key === "Enter") { ev.preventDefault(); wrap.querySelector(".pm-fill").click(); }
  };
  wrap.querySelector(".pm-apply").onclick = () => applyPageMult();
  wrap.querySelector(".pm-revert").onclick = () => revertPageMult();
}
function _pageMultSummary(wrap, pages) {
  const st = S.pageMult;
  const nChk = pages.filter(p => st.checked.has(p.no)).length;
  const { plan, missing, before, after } = pageMultPlan();
  const ap = wrap.querySelector(".pm-apply");
  ap.textContent = `적용 (${plan.length}행)`; ap.disabled = !plan.length;
  wrap.querySelector(".pm-fill").disabled = !nChk;
  wrap.querySelector(".pm-revert").disabled = !nChk;
  wrap.querySelector(".pm-tools .muted").textContent = `선택 ${nChk}장`;
  wrap.querySelector(".pm-preview").innerHTML = nChk
    ? `고른 장 Q'ty <b>${before}</b> → 적용하면 <b>${after}</b>`
      + (missing.length ? ` · 승수를 안 적은 장 ${missing.map(n => "p" + n).join(", ")} 은 건너뜁니다` : "")
    : "장을 고르세요 — Shift 를 누른 채 고르면 사이의 장이 모두 골라집니다";
}
/* 저장 — 한 요청 · 작성자 한 번.  뒤에 목록과 도면을 같은 Q'ty 값에서 다시 그린다
 * (`applyQtyToRows` 와 같은 뒤처리). */
async function _saveQtyItems(items, what, reasonOf) {
  const author = await askAuthor(`승수 — ${what}`);
  if (author === null) return 0;                       // 취소 — 한 행도 안 고친다
  const res = await fetch(`/jobs/${S.job.id}/qty_bulk`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ author, items: items.map(it => ({ key: it.row.key, value: it.value,
                                                             reason: reasonOf(it) })) }),
  });
  if (!res.ok) { editNotice((await res.json()).detail || "저장하지 못했습니다", "out"); return 0; }
  const out = await res.json();
  let done = 0;
  for (const it of items) {
    const r = it.row;
    if (!(r.key in out.users)) continue;
    r.user = out.users[r.key];
    stampEditor(r, "qty", author);
    r.values.qty = it.value === "" ? (r.ai || {}).qty : Number(it.value);
    delete (r.conflict || {}).qty;
    done += 1;
  }
  S.counts.REVIEW = out.review_count;
  if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
  updateBadge();
  renderGrid();                                       // 오른쪽 — 같은 Q'ty 값
  markMultiRows();
  drawOverlay();                                      // 왼쪽 — x N 라벨이 같은 값을 다시 읽는다
  const cur = S.sel && S.rowByKey[S.sel];
  if (S.multi.size) showMultiScope(); else if (cur) showEvidence(cur);
  if (typeof renderFloatEdit === "function") renderFloatEdit();
  return done;
}
async function applyPageMult() {
  const { plan, missing } = pageMultPlan();
  if (!plan.length) {
    editNotice(missing.length ? "고른 장의 승수 칸이 비어 있습니다" : "바뀔 행이 없습니다 — 이미 그 승수입니다", "out");
    return;
  }
  const byPage = new Map();
  for (const it of plan) byPage.set(it.page, it.m);
  const what = [...byPage.entries()].map(([p, m]) => `p${p} x${m}`).join(" · ");
  const done = await _saveQtyItems(plan, `${byPage.size}장 ${plan.length}행 (${what})`,
                                   it => `PAGE_MULTIPLIER: p${it.page} x${it.m}`);
  if (!done) return;
  for (const p of byPage.keys()) delete S.pageMult.vals[p];
  S.pageMult.checked = new Set();
  editNotice(`${byPage.size}장 ${done}행의 Q'ty 를 바꿨습니다 (${what}) — 도면 라벨과 목록에 같이 반영`, "in");
  const box = $("#mult-panel"); if (box) renderPageMult(box);
}
async function revertPageMult() {
  const st = S.pageMult;
  const items = [];
  for (const p of pageMultPages()) {
    if (!st.checked.has(p.no)) continue;
    for (const r of p.rows) if (r.user && r.user.qty !== undefined) items.push({ row: r, page: p.no, value: "" });
  }
  if (!items.length) { editNotice("고른 장에 사람이 고친 Q'ty 가 없습니다", "out"); return; }
  const pages = new Set(items.map(it => it.page));
  const done = await _saveQtyItems(items, `${pages.size}장 ${items.length}행 도면 값으로`,
                                   it => `PAGE_MULTIPLIER: p${it.page} 도면 값으로`);
  if (!done) return;
  S.pageMult.checked = new Set();
  editNotice(`${pages.size}장 ${done}행의 Q'ty 를 도면 값으로 되돌렸습니다`, "out");
  const box = $("#mult-panel"); if (box) renderPageMult(box);
}

async function loadMultipliers() {
  const box = $("#mult-panel");
  if (!box || !S.job || !S.job.id) return;
  let out;
  try {
    out = await (await fetch(`/jobs/${S.job.id}/multipliers`)).json();
  } catch (e) { return; }
  S.mult = out;
  const groups = out.groups || [];
  // hotfix65 — 유닛 승수가 없는 문서(도면이 승수를 다 말한 AL NOUF1)에도 페이지별 승수는 있다.
  const hasRows = (S.rows || []).some(r => !r.deleted && !r.removed && !r.delCand);
  if (!groups.length && !hasRows) { box.classList.add("hidden"); box.innerHTML = ""; _multGutter(); return; }
  box.classList.remove("hidden");
  /* 이 분석이 프로젝트에 안 묶여 있으면 **저장할 자리가 없다** — 누르고 나서
   * 400 으로 알리지 않고 먼저 말한다 (31회차 UI 자기검증).  승수는 프로젝트의
   * 사실이므로 job 하나에 매달아 둘 수 없다. */
  const bound = !!out.project;
  /* hotfix27 — 유닛이 여럿이면(EPIC2: 00 · 10 · 11 · 12) 이 판이 목록 자리를 다
   * 먹었다.  머리줄에 **접기**와 한 줄 요약을 두고, 판 아래 손잡이(#gutter-m)로
   * 높이를 끈다.  접힘은 브라우저가 기억한다 (범례 판 접기와 같은 규칙). */
  const nSet = groups.filter(g => g.set).length;
  const folded = _multFolded();
  box.classList.toggle("folded", folded);
  box.innerHTML = `<div class="mtop"><b title="페이지별 승수는 지금 결과에 바로 · 유닛 승수는 도면이 말하지 않은 유닛을 다음 분석부터">수량 승수</b>
      <span class="msum">페이지별 바로 적용${groups.length ? ` · 유닛 ${groups.length}개 · 지정 ${nSet} · 미지정 ${groups.length - nSet}
        · ${groups.reduce((a, g) => a + (g.rows || 0), 0)}행` : ""}</span>
      <button class="mfold ghost" title="접으면 요약 한 줄만 남습니다">${folded ? "펼치기" : "접기"}</button></div>`
    + `<div class="mgroup pmult"></div>`
    + (groups.length ? `<div class="mgroup mu-head"><div class="mhead">유닛코드 승수 <span class="muted">— 도면이
         승수를 말하지 않은 유닛 · 프로젝트에 적혀 <b>다음 분석부터</b> 쓰입니다</span></div></div>` : "")
    + (bound || !groups.length ? "" : `<div class="mwhy muted">이 분석은 프로젝트에 묶여 있지 않아
         유닛 승수를 저장할 자리가 없습니다 — 프로젝트를 고르고 다시 올리면 지정할 수 있습니다</div>`)
    + groups.map(g => {
        const set = g.set;
        const after = set ? g.rows * (set.multiplier || 0) : null;
        /* 유닛코드가 비어 있으면 열쇠가 없다 — 그 도면의 도면번호를 못 읽은 것이다. */
        const keyed = !!g.unit;
        return `<div class="mgroup" data-unit="${attr(g.unit || "")}">
          <div class="mhead">유닛 <b>${escape(String(g.unit || "(빈칸)"))}</b>
            <span class="muted">${g.sheets}장 ${g.rows}행에 적용됩니다
              (${g.pages.map(p => "p" + p).join(", ")})</span></div>
          <div class="mwhy muted">${escape((g.codes || []).join(" · "))}</div>
          ${set ? `<div class="mset">지정됨 <b>x${set.multiplier}</b>
              — ${escape(String(set.author || "이름 없음"))} · ${escape(String(set.set_at || "").slice(0, 10))}
              ${set.note ? " · " + escape(String(set.note)) : ""}
              <button class="mclear">되돌리기</button>
              <div class="mpending">아직 이 결과에는 반영되지 않았습니다 —
                다시 분석하면 ${g.rows}행에 적용됩니다</div></div>` : ""}
          ${keyed && bound ? `<div class="mform">
            <label>승수 <input class="mval" type="number" min="1" step="1"
                   value="${set ? set.multiplier : ""}" placeholder="예: 4"></label>
            <label>근거 <input class="mnote" type="text"
                   placeholder="예: 발주처 회신 2026-09-11" value="${attr(set ? (set.note || "") : "")}"></label>
            <button class="mset-btn">지정</button>
            <span class="mpreview muted">지금 Q'ty ${g.qty_now}
              ${after !== null ? ` · 다시 분석하면 <b>${after}</b>` : " · 다시 분석하면 ?"}</span>
          </div>` : (keyed ? "" : `<div class="mwhy muted">이 장들의 도면번호에서
             유닛코드를 읽지 못해 지정할 열쇠가 없습니다</div>`)}</div>`;
      }).join("");
  box.querySelector(".mfold").onclick = () => {
    _multFolded(!box.classList.contains("folded"));
    loadMultipliers();
  };
  _multGutter();
  renderPageMult(box);
  box.querySelectorAll(".mgroup[data-unit]").forEach(el => {
    const unit = el.dataset.unit;
    const val = el.querySelector(".mval");
    const pv = el.querySelector(".mpreview");
    const g = groups.find(x => x.unit === unit) || { rows: 0, qty_now: 0 };
    /* 넣기 전에 무엇이 바뀌는지 보인다 — 누르고 나서 아는 것이 아니다. */
    if (val) val.oninput = () => {
      const n = parseInt(val.value, 10);
      /* "→" 만 쓰면 이미 바뀐 것처럼 읽힌다.  바뀌는 것은 **다시 분석한 뒤**다. */
      pv.innerHTML = `지금 Q'ty ${g.qty_now}` +
        (n >= 1 ? ` · 다시 분석하면 <b>${g.rows * n}</b> (${g.rows}행 x ${n})` : " · 다시 분석하면 ?");
    };
    const btn = el.querySelector(".mset-btn");
    if (btn) btn.onclick = async () => {
      const n = parseInt(val.value, 10);
      if (!(n >= 1)) { editNotice("승수는 1 이상의 정수입니다", "out"); return; }
      /* 13회차 작성자 기록 — 팀이 공유하는 값이므로 누가 넣었는지가 값의 일부다. */
      const who = await askAuthor("승수 지정", `유닛 ${unit} → x${n}`);
      if (who === null) return;
      const body = new FormData();
      body.append("unit", unit); body.append("multiplier", String(n));
      body.append("author", who || "");
      body.append("note", el.querySelector(".mnote").value || "");
      const r = await fetch(`/jobs/${S.job.id}/multipliers`, { method: "POST", body });
      if (!r.ok) { editNotice((await r.json()).detail || "저장하지 못했습니다", "out"); return; }
      /* `editNotice` 는 textContent 다 — 마크다운 별표를 쓰면 별표가 그대로 보인다
       * (31회차 UI 자기검증 캡처가 잡았다). */
      editNotice(`유닛 ${unit} → x${n} 지정했습니다 — 다시 분석하면 ${g.rows}행에 적용됩니다`, "in");
      loadMultipliers();
    };
    const clr = el.querySelector(".mclear");
    if (clr) clr.onclick = async () => {
      await fetch(`/jobs/${S.job.id}/multipliers/${encodeURIComponent(unit)}`,
                  { method: "DELETE" });
      editNotice(`유닛 ${unit} 지정을 되돌렸습니다`, "out");
      loadMultipliers();
    };
  });
}

/* ---------------------------------------------------------------------------
 * 장 도면번호 — 타이틀블록이 글자가 아니라 획이라 읽히지 않은 장에 **사람이
 * 한 번 적는 자리** (45회차 경로 · hotfix33 화면).
 *
 * 저장·엔진·API 는 45회차부터 있었고(`app/sheet_numbers.py` ·
 * `GET/POST/DELETE /jobs/{id}/sheet_numbers`), 없던 것은 화면뿐이었다.  규율은
 * 승수 판과 같다 — 서버가 **도면번호가 빈 장만** 목록에 낸다(읽힌 장은 사람이
 * 적어도 쓰이지 않는다 · 도면이 이긴다) · 작성자 필수 · 적은 값은 **다시
 * 분석해야** 반영된다(그 사실은 사라지는 안내가 아니라 판에 상주한다).
 * ------------------------------------------------------------------------- */
const attr = (s) => escape(String(s == null ? "" : s)).replace(/"/g, "&quot;");
async function loadSheetNumbers() {
  const box = $("#sheet-panel");
  if (!box || !S.job || !S.job.id) return;
  let out;
  try {
    out = await (await fetch(`/jobs/${S.job.id}/sheet_numbers`)).json();
  } catch (e) { return; }
  S.sheetNos = out;
  const sheets = out.sheets || [];
  if (!sheets.length) { box.classList.add("hidden"); box.innerHTML = ""; return; }
  box.classList.remove("hidden");
  const bound = !!out.project;
  const nSet = sheets.filter(s => s.set).length;
  const folded = _sheetFolded();
  box.classList.toggle("folded", folded);
  /* 이 문서가 다른 장에서 읽은 도면번호 꼴 — 적는 사람이 맞춰 쓰라고 보인다 (지어내지 않는다:
   * 같은 문서의 읽힌 장이 인쇄한 값 그대로다). */
  const sample = (S.pages || []).map(p => p.drawing_no).filter(Boolean)[0] || "";
  box.innerHTML = `<div class="mtop"><b title="타이틀블록이 글자가 아니라 획으로 그려져 도면번호를 읽지 못한 장 — 사람이 적으면 다시 분석할 때 그 장이 분석 대상이 됩니다">장 도면번호</b>
      <span class="msum">못 읽은 장 ${sheets.length} · 지정 ${nSet} · 미지정 ${sheets.length - nSet}</span>
      <button class="mfold ghost" title="접으면 요약 한 줄만 남습니다">${folded ? "펼치기" : "접기"}</button></div>`
    + (out.enabled === false ? `<div class="mwhy muted">이 프로젝트의 장 도면번호 지정이 꺼져 있습니다 (enabled: false) — 적어도 쓰이지 않습니다</div>` : "")
    + (bound ? "" : `<div class="mwhy muted">이 분석은 프로젝트에 묶여 있지 않아
         도면번호를 저장할 자리가 없습니다 — 프로젝트를 고르고 다시 올리면 지정할 수 있습니다</div>`)
    + `<div class="mwhy muted">도면에서 읽힌 장은 여기 없습니다 — 사람은 도면을 이기지 않습니다.
         ${sample ? `이 문서의 읽힌 번호 꼴: <code>${escape(sample)}</code>` : ""}</div>`
    + sheets.map(sh => {
        const set = sh.set;
        return `<div class="mgroup sgroup" data-page="${sh.page_no}">
          <div class="mhead">p<b>${sh.page_no}</b>
            <span class="muted">${sh.page_kind ? `종류 ${escape(sh.page_kind)}` : "종류 미상"}
              ${sh.from_user ? " · 이번 분석은 사람이 적은 번호로 읽었습니다" : " · 이번 분석에서 대상 밖"}</span>
            <button class="sview ghost" title="그 장을 도면 창에 띄웁니다">보기</button></div>
          ${set ? `<div class="mset">지정됨 <b>${escape(set.drawing_no || "")}</b>
              — ${escape(set.author || "이름 없음")} · ${(set.set_at || "").slice(0, 10)}
              ${set.note ? " · " + escape(set.note) : ""}
              <button class="mclear">되돌리기</button>
              ${sh.from_user ? "" : `<div class="mpending">아직 이 결과에는 반영되지 않았습니다 —
                다시 분석하면 이 장이 분석 대상이 됩니다</div>`}</div>` : ""}
          ${bound ? `<div class="mform">
            <label>도면번호 <input class="sval" type="text" spellcheck="false"
                   value="${attr(set ? (set.drawing_no || "") : "")}" placeholder="${attr(sample || "도면에 인쇄된 번호 그대로")}"></label>
            <label>근거 <input class="mnote" type="text"
                   placeholder="예: 타이틀블록 육안 판독" value="${attr(set ? (set.note || "") : "")}"></label>
            <button class="sset-btn">지정</button>
          </div>` : ""}</div>`;
      }).join("");
  box.querySelector(".mfold").onclick = () => {
    _sheetFolded(!box.classList.contains("folded"));
    loadSheetNumbers();
  };
  box.querySelectorAll(".sgroup").forEach(el => {
    const pno = +el.dataset.page;
    el.querySelector(".sview").onclick = () => {
      const pg = (S.pages || []).find(p => p.page_no === pno);
      if (pg) showPage(pg); else editNotice(`p${pno} 은 이 분석의 장 목록에 없습니다`, "out");
    };
    const btn = el.querySelector(".sset-btn");
    if (btn) btn.onclick = async () => {
      const val = (el.querySelector(".sval").value || "").trim();
      if (!val) { editNotice("도면번호를 비워 둘 수 없습니다", "out"); return; }
      /* 13회차 작성자 기록 — 팀이 공유하는 값이므로 누가 적었는지가 값의 일부다. */
      const who = await askAuthor("장 도면번호 지정", `p${pno} → ${val}`);
      if (who === null) return;
      const body = new FormData();
      body.append("page", String(pno)); body.append("drawing_no", val);
      body.append("author", who || "");
      body.append("note", el.querySelector(".mnote").value || "");
      const r = await fetch(`/jobs/${S.job.id}/sheet_numbers`, { method: "POST", body });
      if (!r.ok) { editNotice((await r.json()).detail || "저장하지 못했습니다", "out"); return; }
      editNotice(`p${pno} → ${val} 지정했습니다 — 다시 분석하면 이 장이 분석 대상이 됩니다`, "in");
      loadSheetNumbers();
    };
    const clr = el.querySelector(".mclear");
    if (clr) clr.onclick = async () => {
      await fetch(`/jobs/${S.job.id}/sheet_numbers/${pno}`, { method: "DELETE" });
      editNotice(`p${pno} 지정을 되돌렸습니다`, "out");
      loadSheetNumbers();
    };
  });
}

const SHEET_FOLD_KEY = "pid.sheet.fold";
function _sheetFolded(v) {
  try {
    // hotfix42 — 사람이 정한 적이 없으면 **짧은 화면에서는 접힌 채로** 시작한다 (1366×768 에서 두 판이
    // 목록을 화면 밖으로 밀었다 — QA 시뮬레이션).  한 번 펼치거나 접으면 그 선택이 남는다.
    if (v === undefined) { const v0 = localStorage.getItem(SHEET_FOLD_KEY); return v0 === null ? window.innerHeight < 860 : v0 === "1"; }
    localStorage.setItem(SHEET_FOLD_KEY, v ? "1" : "0");
  } catch (e) { /* 저장 못 해도 이번 화면은 그대로 */ }
  return !!v;
}

const MULT_FOLD_KEY = "pid.mult.fold";
function _multFolded(v) {
  try {
    // hotfix42 — 사람이 정한 적이 없으면 **짧은 화면에서는 접힌 채로** 시작한다 (1366×768 에서 두 판이
    // 목록을 화면 밖으로 밀었다 — QA 시뮬레이션).  한 번 펼치거나 접으면 그 선택이 남는다.
    if (v === undefined) { const v0 = localStorage.getItem(MULT_FOLD_KEY); return v0 === null ? window.innerHeight < 860 : v0 === "1"; }
    localStorage.setItem(MULT_FOLD_KEY, v ? "1" : "0");
  } catch (e) { /* 저장 못 해도 이번 화면은 그대로 */ }
  return !!v;
}
/* 판이 보이고 펼쳐져 있을 때만 손잡이를 둔다 — 접힌 한 줄을 끌 까닭이 없다. */
function _multGutter() {
  const box = $("#mult-panel"), g = document.getElementById("gutter-m");
  if (!box || !g) return;
  g.classList.toggle("hidden", box.classList.contains("hidden") || box.classList.contains("folded"));
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
  if (S.onlyChanged) chips.push(["onlyChanged", "개정된 행만"]);
  if (S.revFilter) chips.push(["revFilter", `개정 ${
    { ADDED: "추가만", MODIFIED: "수정만", DELETED: "삭제만" }[S.revFilter] || S.revFilter}`]);
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
      else if (k === "onlyChanged") { S.onlyChanged = false; $("#only-changed").checked = false; }
      else if (k === "revFilter") { S.revFilter = ""; $("#rev-filter").value = ""; }
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
    if (!b.title) b.title = `${label} ${S.counts[key] || 0}`;   // hotfix49 — 접힌 메뉴에서 이름이 잘린다
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
const FILTER_COLS = ["page_no", "pid_no", "rev_state", "type", "valve_type", "qty",
                     "system", "vendor_supply"];
const BLANK = "\u0000blank";        // the '(공란)' choice, kept out of value space

/* hotfix38 — 개정 상태의 한글 표기.  그리드 열 · 필터 · 근거 패널이 **이 하나**를
 * 읽는다.  BASELINE(Rev.A)·UNCHANGED 는 빈 문자열 — 표기가 붙지 않는다. */
// hotfix46 — NOT_COMPARED(태그 없어 대조 안 함)는 표기가 없다 — 추가도 삭제도 아니다.
const REV_STATE_KO = { ADDED: "추가", MODIFIED: "수정",
                       DELETED_CANDIDATE: "삭제 후보", DELETED: "삭제 확정" };
function revLabel(row) {
  const rv = (row || {}).rev || {};
  // hotfix47 — 기록 쪽의 '수정' 은 이전 태그다 (이번 분석에 그 태그가 없다)
  if (rv.state === "MODIFIED" && rv.role === "before") return "수정 (이전 태그)";
  return REV_STATE_KO[rv.state] || "";
}

function cellValue(row, key) {
  if (key === "page_no") return row.page_no;
  if (key === "origin") return row.origin;
  if (key === "rev_state") return revLabel(row);
  if (key === "pid_no") {
    return (S.pages.find(p => p.page_no === row.page_no) || {}).drawing_no
      || row.drawing_no || "";
  }
  if (key === "remark") return remarkOf(row);
  /* TYPE 표기 — 도면이 버블에 인쇄한 기능 문자가 있으면 `MOV(GLOBE)`.
   * 판정값(row.values.type)은 그대로이고 보이는 글자만 다르다.  규칙은
   * 서버(`pipeline.type_display`)에만 있고 여기는 그 결과를 받아 쓴다 —
   * 밸브 어휘를 화면에도 적으면 두 곳이 갈린다.  `type_display` 가 없는 응답
   * (이전 분석 등)에서는 판정값 그대로다. */
  if (key === "type") return row.type_display ?? row.values.type ?? "";
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
  if (S.revFilter) {
    const want = S.revFilter === "DELETED"
      ? ["DELETED_CANDIDATE", "DELETED"] : [S.revFilter];
    rows = rows.filter(r => want.includes((r.rev || {}).state));
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
const SEARCH_COLS = ["page_no", "pid_no", "origin", "rev_state", "type", "valve_type", "qty",
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
  const cols = gridCols();
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
  // hotfix47 — 기록 행은 삭제 후보와 '이전 태그(수정)' 둘이다
  const nBefore = (S.deletedRows || []).filter(r => (r.rev || {}).state === "MODIFIED").length;
  const tail = nDel ? ` (+ ${nBefore ? `이전 태그 ${nBefore}${nDel - nBefore ? " · " : ""}` : ""}${nDel - nBefore ? `삭제 후보 ${nDel - nBefore}` : ""})` : "";
  $("#count").textContent = (rows.length === S.rows.length + nDel
    ? `${S.rows.length}행`
    : `표시 ${rows.length} / 전체 ${S.rows.length}`) + tail;
  const body = $("#body");
  body.innerHTML = "";
  // hotfix68 — 한 행을 만드는 일은 `buildRowTr` 하나 (다른 창에서 고친 행을 제자리에서 바꿀 때도 같은 함수)
  // hotfix69 — 목록은 **보이는 행만** 그린다 (`paintWindow`).  2,000행을 다 그리면 검색 한 글자에 목록 배치가
  // 1.2초 · 굴리기 한 번에 고정 열 4,000칸을 다시 칠했다 (QFE 실측 — spike/perf_sim.py).  행이 어느 줄에 서는지는
  // `S.vlist` 가 말하고, 화면 밖 행은 굴리면 그때 그린다.
  S.vlist = rows;
  S.vcols = cols;
  VROW.measure = _measureRowHtml(rows, cols);
  VROW.start = VROW.end = -1;
  paintWindow(true);
}

/* hotfix69 — 보이는 행만 그리기.
 *
 * 행 높이는 하나다 (칸이 한 줄 · 넘치면 말줄임 — styles.css `th, td`).  그래서 i 번째 행의 자리는 i × 높이이고,
 * 화면에 보이는 줄 ± 여유(`VROW.buf`)만 그리고 위·아래는 빈 칸(높이만 가진 줄)으로 채운다 — 굴림막대의 길이와
 * 자리는 2,000행을 다 그렸을 때와 같다.  열 폭이 굴릴 때마다 흔들리지 않도록 **열마다 가장 긴 값을 담은 숨은 줄**
 * 하나(`visibility: collapse` — 높이 0, 폭에는 든다)를 늘 맨 위에 둔다.
 * 사람이 칸에 타자 중이면 다시 그리지 않는다 (그 칸이 사라지면 편집이 사라진다).
 * 여유 16행 · 8행마다 다시 그리기 — 굴리기 실측(spike 굴림 시험, 30걸음)에서 40/20 은 50ms 넘는 작업 3~5건,
 * 16/8 은 0건이었다 (한 번에 그리는 줄이 적을수록 그리기 한 번이 짧다 · 그리기 한 번은 4~5ms). */
const VROW = { h: 0, buf: 16, step: 8, start: -1, end: -1, raf: 0, measure: "" };
function _measureRowHtml(rows, cols) {
  const longest = cols.map(() => "");
  for (const r of rows) {
    for (let i = 0; i < cols.length; i++) {
      const key = cols[i][0];
      if (key === "description_grade") continue;
      const v = key === "page_no" ? r.page_no : key === "origin" ? r.origin
        : key === "pid_no" ? _pidOf(r.page_no) : key === "remark" ? remarkOf(r)
        : key === "rev_state" ? revLabel(r) : (r.values[key] ?? "");
      const t = v === null || v === undefined ? "" : String(v);
      if (t.length > longest[i].length) longest[i] = t;
    }
  }
  const grade = rows.find(r => r.values.description_grade);
  return '<tr class="vmeasure" aria-hidden="true">' + cols.map(([key], i) =>
    `<td data-col="${key}">` + (key === "description_grade"
      ? (grade ? _gradeBadgeHtml(grade.values.description_grade) : "")
      : escape(longest[i])) + "</td>").join("")
    + '<td><button class="mini-rep" tabindex="-1">삭제 확정</button><button class="mini-rep" tabindex="-1">되돌리기</button>'
    + '<button class="mini-rep" tabindex="-1">신고</button></td></tr>';
}
function _vpad(px, n) {
  return px > 0 ? `<tr class="vpad" aria-hidden="true"><td colspan="${n}" style="height:${px}px"></td></tr>` : "";
}
function paintWindow(force) {
  const body = $("#body"), gw = $("#gridwrap");
  const rows = S.vlist || [], cols = S.vcols || gridCols();
  if (!body || !gw) return;
  if (!force && body.contains(document.activeElement) && document.activeElement !== body) return;
  const h = VROW.h || 29;
  const view = Math.max(gw.clientHeight, 600);
  const first = Math.max(0, Math.floor(gw.scrollTop / h));
  const last = Math.min(rows.length, Math.ceil((gw.scrollTop + view) / h));
  // 그린 범위가 보이는 줄 ± 한 걸음(`step`)을 아직 덮으면 다시 그리지 않는다
  if (!force && VROW.start >= 0 && VROW.start <= Math.max(0, first - VROW.step)
      && VROW.end >= Math.min(rows.length, last + VROW.step)) return;
  const start = Math.max(0, Math.floor((first - VROW.buf) / VROW.step) * VROW.step);
  const end = Math.min(rows.length, Math.ceil((last + VROW.buf) / VROW.step) * VROW.step);
  if (!force && start === VROW.start && end === VROW.end) return;
  VROW.start = start; VROW.end = end;
  const n = cols.length + 1;
  // 숨은 측정 줄은 **맨 끝**에 둔다 — 맨 앞에 두면 "첫 줄" 을 찾는 곳(`#body tr`)이 그 줄을 집는다 (UI 시험이 잡았다)
  let html = _vpad(start * h, n);
  for (let i = start; i < end; i++) html += rowHtml(rows[i], cols);
  html += _vpad((rows.length - end) * h, n) + VROW.measure;
  body.innerHTML = html;
  if (!VROW.h) {
    const tr = body.querySelector("tr[data-key]");
    const rh = tr ? tr.getBoundingClientRect().height : 0;
    if (rh > 10) { VROW.h = rh; if (Math.abs(rh - h) > 0.5) { paintWindow(true); return; } }
  }
  // 묶음 표시는 다시 그린 뒤에도 남는다 — 판정하는 곳은 `S.multi` 하나다.
  markMultiRows();
}
/* 그 행이 지금 그려져 있지 않으면 그 자리로 굴려 그린다.  행 `<tr>` 를 돌려준다 (목록에 없는 행이면 null). */
function revealRow(key) {
  let tr = document.querySelector(`#body tr[data-key="${CSS.escape(key)}"]`);
  if (tr) return tr;
  const i = (S.vlist || []).findIndex(r => r.key === key);
  if (i < 0) return null;
  const gw = $("#gridwrap");
  if (gw) gw.scrollTop = Math.max(0, i * (VROW.h || 29) - gw.clientHeight / 2);
  paintWindow(true);
  return document.querySelector(`#body tr[data-key="${CSS.escape(key)}"]`);
}
(function bindGridScroll() {
  const gw = document.getElementById("gridwrap");
  if (!gw) return;
  const later = () => { if (!VROW.raf) VROW.raf = requestAnimationFrame(() => { VROW.raf = 0; paintWindow(false); }); };
  gw.addEventListener("scroll", later, { passive: true });
  window.addEventListener("resize", later);
  // 칸 편집이 끝나면 미뤄 둔 그리기를 한다
  gw.addEventListener("focusout", () => setTimeout(later, 0));
})();

function gridCols() { return COLS.filter(([key]) => key !== "origin" || S.showOrigin); }

/* hotfix68 — 한 행을 만든다.  2,000행 목록에서 칸마다 createElement · dataset · innerHTML 을 부르던 것이
 * 목록 그리기의 대부분이었다 (QFE 실측 renderGrid 514ms — 그중 칸 하나하나의 DOM 호출이 대부분).  그래서 행을
 * **글 한 줄**로 만들어 몸통에 한 번 붓는다 (브라우저의 HTML 해석기가 칸 수만큼의 DOM 호출보다 훨씬 빠르다).
 * 보이는 모습 · 칸 · 제목 · 깃발 · 단추는 예전과 같고, 단추 누르기는 몸통의 듣는 이가 받는다 (`bindGridBody`). */
let _pidMapOf = null, _pidMap = null;
function _pidOf(pageNo) {
  if (_pidMapOf !== S.pages) {
    _pidMapOf = S.pages;
    _pidMap = new Map((S.pages || []).map(p => [p.page_no, p.drawing_no || ""]));
  }
  return _pidMap.get(pageNo) || "";
}
const _gradeHtml = {};
function _gradeBadgeHtml(val) {
  if (!(val in _gradeHtml)) {
    // 배지 하나에 모양·글자·색이 같이 실린다.  모양과 글자만으로도 읽힌다.
    const g = GRADES.find(x => x[0] === val);
    _gradeHtml[val] = `<span class="gradge g-${escAttr(val)}" title="${escAttr(g ? g[2] : val)}">`
      + `<i class="gm">${GRADE_MARK[val] || "·"}</i><span>${escape(String(g ? g[1] : val))}</span></span>`;
  }
  return _gradeHtml[val];
}
const _flagHtml = (cls, title, text) => `<span class="${cls}" title="${escAttr(title)}">${text}</span>`;

function rowHtml(r, cols) {
  const cls = [];
  const attrs = [`data-key="${escAttr(r.key)}"`];
  if (r.added) attrs.push('data-added="1"');
  if (r.deleted || r.removed) cls.push("deleted");
  const ust = rowUserState(r);                 // paintRowState 와 같은 판정
  if (ust) cls.push(ust);
  // 개정 상태.  BASELINE(Rev.A) 과 UNCHANGED 는 아무 표기도 붙이지 않는다.
  const st = (r.rev || {}).state;
  if (st === "ADDED" || st === "MODIFIED") { cls.push(st === "ADDED" ? "rev-added" : "rev-modified"); attrs.push(`data-rev="${st}"`); }
  else if (st === "DELETED_CANDIDATE" || st === "DELETED") { cls.push("rev-deleted"); attrs.push(`data-rev="${st}"`); }
  if (S.sel === r.key) cls.push("sel");
  if (S.multi && S.multi.has(r.key)) cls.push("multi");
  let h = `<tr ${attrs.join(" ")}${cls.length ? ` class="${cls.join(" ")}"` : ""}>`;
  const canEdit = !r.deleted && !r.removed;
  for (const [key, , editable] of cols) {
    const val = key === "page_no" ? r.page_no
      : key === "origin" ? r.origin
      : key === "pid_no" ? _pidOf(r.page_no)
      : key === "remark" ? remarkOf(r)
      : key === "rev_state" ? revLabel(r)          // hotfix38 — 필터와 같은 접근자
      : (r.values[key] ?? "");
    const has = val !== "" && val !== null && val !== undefined;
    const tc = [];
    // SCOPE 열은 폭을 따로 준다 (styles.css `.col-scope`).
    if (key === "scope") tc.push("col-scope");
    if (key === "origin") tc.push(`origin-${r.origin}`);
    // 잘리는 칸은 마우스를 올리면 전문이 보인다 — 밀도(§7.2 의 29.0px / 15행)를 깨지 않는 유일한 방법이다.
    let title = has ? String(val) : "";
    // 사람이 고친 칸과 엔진이 채운 칸은 색이 아니라 표시로 갈린다: 사람이 고친 칸에는 연필이 붙는다.
    if (r.user && key in r.user) { tc.push("edited"); title = editedTitle(r, key, val); }
    if (r.conflict && key in r.conflict) tc.push("conflict");
    h += `<td data-col="${key}"`
      + (tc.length ? ` class="${tc.join(" ")}"` : "")
      + (title ? ` title="${escAttr(title)}"` : "")
      // 저장 · Enter 는 목록 몸통 하나가 받는다 (`bindGridBody`)
      + (editable && canEdit ? ' contenteditable="true"' : "")
      + ">"
      + (key === "description_grade" && has ? _gradeBadgeHtml(val) : has ? escape(String(val)) : "")
      + "</td>";
  }
  h += "<td>";
  if (r.needs_review) h += _flagHtml("flag bad", "검토 필요", "●");
  if (r.annotation) h += _flagHtml("flag", "도면에 검토 주석", "▲");
  if (r.added) h += _flagHtml("flag ok", "검토자 추가 행", "＋");
  // 삭제 후보는 확정 버튼을 달고 나온다.  자동으로 굳지 않는다.
  if (r.delCand) {
    const t = deletedRemark(r.delCand, (S.rev || {}).compared_with || "")
      + ` · Rev 좌표 (${(r.delCand.anchor || []).join(", ")})`
      + (r.delCand.radius ? ` · 반경 ${r.delCand.radius}pt (${r.delCand.radius_source}) — 옛 대조` : "");
    h += `<button class="mini-rep del-confirm" data-act="del-confirm" title="${escAttr(t)}">`
      + (r.delCand.confirmed ? "확정 취소" : "삭제 확정") + "</button>";
  }
  if (r.removed) h += _flagHtml("flag", "검토자 삭제 — 출력 제외", "✕");
  // 44회차 — 오검출 표시(Excel 유지)와 되돌리기.  표시된 행은 어느 쪽이든
  // 사람이 되돌릴 수 있어야 한다 — API 는 처음부터 있었고 버튼이 없었다.
  const rejected = r.reject && Object.keys(r.reject).length;
  if (rejected && !r.removed)
    h += _flagHtml("flag", `오검출 의심 표시 — Excel 유지 · ${r.reject.class || ""} ${r.reject.note || ""}`, "✕?");
  if (r.removed || rejected)
    h += '<button class="mini-rep" data-act="restore" title="오검출 표시를 지우고 행을 되살립니다">되돌리기</button>';
  // One click from any row to a report, because a reviewer notices the error
  // while looking at the grid and will not go hunting for a menu.
  h += '<button class="mini-rep" data-act="report" title="이 행의 판정이 틀렸다고 신고합니다">신고</button>';
  return h + "</td></tr>";
}
const _rowTpl = document.createElement("template");
function buildRowTr(r, cols) {
  _rowTpl.innerHTML = rowHtml(r, cols);
  return _rowTpl.content.firstElementChild;
}

/* hotfix68 — 목록 몸통의 듣는 이 셋.  칸마다 달던 blur · keydown 과 행마다 달던 click 을 한 곳에서 받는다 —
 * 하는 일은 같다 (칸을 떠나면 `saveEdit` · Enter 는 칸 떠나기 · 행 누르기는 고르기 / Shift 는 묶음).
 * 행은 `S.rowByKey` 에서 찾는다 — 다른 창에서 고친 행도 같은 객체를 제자리에서 바꾸므로 같은 행이다. */
function _gridRow(tr) {
  const k = tr && tr.dataset.key;
  return k ? (S.rowByKey && S.rowByKey[k]) || (S.deletedRows || []).find(r => r.key === k) || null : null;
}
(function bindGridBody() {
  const body = document.getElementById("body");
  if (!body) return;
  body.addEventListener("focusout", ev => {
    const td = ev.target;
    if (!td || td.tagName !== "TD" || td.contentEditable !== "true") return;
    const r = _gridRow(td.parentElement);
    if (r) saveEdit(r, td.dataset.col, td);
  });
  body.addEventListener("keydown", ev => {
    const td = ev.target;
    if (ev.key === "Enter" && td && td.tagName === "TD" && td.contentEditable === "true") { ev.preventDefault(); td.blur(); }
  });
  body.addEventListener("click", ev => {
    const tr = ev.target.closest ? ev.target.closest("tr") : null;
    if (!tr || !body.contains(tr)) return;
    const r = _gridRow(tr);
    if (!r) return;
    const act = ev.target.closest("[data-act]");
    if (act) {
      const what = act.dataset.act;
      if (what === "report") reportDialog({ rowKey: r.key, pageNo: r.page_no });
      else if (what === "restore") {
        fetch(`/jobs/${S.job.id}/rows/${r.key}/restore`, { method: "POST" }).then(() => refreshRows(r.key, { keys: [r.key] }));
      } else if (what === "del-confirm" && r.delCand) {
        fetch(`/jobs/${S.job.id}/deleted/${encodeURIComponent(r.delCand.id)}/confirm`
              + `?confirmed=${!r.delCand.confirmed}`, { method: "POST" })
          .then(() => loadRevision()).then(() => loadRows());
      }
      return;
    }
    if (isAddClick(ev)) { toggleMulti(r.key); return; }
    select(r.key, true);
  });
})();

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
  if (ev.key === "Escape") { closeColumnMenu(); if (typeof closeScopePop === "function") closeScopePop(); }
  // hotfix41 — 나란히 보기에서 Alt+← / Alt+→ 로 변경을 차례로 (◀ ▶ 버튼과 같은 함수)
  if (S.side && ev.altKey && (ev.key === "ArrowLeft" || ev.key === "ArrowRight") && (S.cmpChanges || []).length) {
    ev.preventDefault();
    const n = S.cmpChanges.length;
    const i = ((S.cmpIdx === undefined || S.cmpIdx < 0 ? -1 : S.cmpIdx) + (ev.key === "ArrowRight" ? 1 : -1) + n) % n;
    focusChange(S.cmpChanges[i], i);
  }
});

/* ---------------- 작성자 (13회차 [D]) ----------------
 *
 * 팀 여럿이 같은 서버를 쓴다.  그런데 편집 이력(`feedback`)에 **누구**를
 * 가리키는 칸이 하나도 없었다 (13회차 조사).  인증을 만들 자리가 아니므로
 * 자기신고로 하되, 사용자가 "매 편집마다 이름 확인"을 택했다.
 *
 * 그래서 **확인은 매번 하고 타자는 한 번만** 친다: 지난 이름이 채워진 채로
 * 뜨고 Enter 로 넘어간다.  비워서 넘기면 비운 채로 저장되고 화면이
 * "이름 없음" 이라고 적는다 - 서버도 화면도 이름을 지어내지 않는다. */
const AUTHOR_KEY = "pid.author";

function lastAuthor() {
  try { return localStorage.getItem(AUTHOR_KEY) || ""; } catch (e) { return ""; }
}
function rememberAuthor(name) {
  try { localStorage.setItem(AUTHOR_KEY, name); } catch (e) { /* 사생활 모드 */ }
}

/* 한 번에 하나만 뜬다.  뜬 동안 그리드를 다시 그리지 않는다 - 12회차의
 * "저장이 끝나기 전에 다음 칸으로 넘어간다" 와 같은 문제를 만들지 않기 위해
 * 이 줄은 그리드 밖(fixed)에 산다.
 *
 * ★ "한 번에 하나" 를 **코드가 지키게** 한다.  이 주석은 처음부터 그렇게
 * 적혀 있었지만 `done()` 말고는 줄을 치우는 곳이 없어, 앞 칸에 이름을 적지
 * 않은 채 다음 칸을 고치면 **두 줄이 겹쳐 쌓였다** — 둘 다 "누가 고쳤나요?"
 * 라고만 하고 어느 행 이야기인지 말하지 않아, 14회차가 `.edit-note` 에서
 * 고친 것과 같은 구조다 (서로 다른 행의 말이 동시에 화면에 있다).
 *
 * 지우기만 하면 그 편집의 `await` 가 영영 안 끝나므로 **취소로 닫는다** —
 * `saveEdit` 의 null 갈래가 칸을 원래 값으로 돌려놓고, 무엇이 취소됐는지
 * 새 줄이 뜬 뒤에 한 줄로 말한다 (말없이 버리지 않는다). */
let _authorPending = null;

/* hotfix66 — **편집마다 묻지 않는다.**  사용자: *"수정할 때마다 누가 고쳤나요 띄워서 확인하지 말고
 * 대시보드 로그인할 때의 정보로 누가 고쳤는지 자동으로 마크업/라벨링하도록."*
 *
 * 이름의 출처는 하나다 (`currentAuthor`):
 *   ① 대시보드가 iframe 주소에 실어 보낸 로그인 이름 (`?user=` — `EMBED.user`) — 언제나 이긴다
 *   ② 이 브라우저가 기억하는 이름 (대시보드 밖에서 직접 열었을 때 · 첫 편집 때 **한 번만** 묻는다)
 * 둘 다 없을 때만 이름 줄을 띄운다.  13회차의 "매번 확인" 은 사용자가 거둬들였다.
 * 고친 칸에는 그 이름이 붙는다 (`row.edited_by` · ✎ 툴팁 · 도면의 `x N ✎이름` 라벨). */
function currentAuthor() { return (EMBED.user || lastAuthor() || "").trim(); }
function authorSource() { return EMBED.user ? "대시보드 로그인" : (lastAuthor() ? "이 브라우저에 기억된 이름" : ""); }
function askAuthor(what, hint) {
  const known = currentAuthor();
  if (known) { renderWhoChip(); return Promise.resolve(known); }
  // 이름을 묻는 순간 앞 편집의 안내는 지운다 - 그것은 이미 다른 행 이야기다.
  const dropped = _authorPending ? _authorPending() : null;
  document.querySelectorAll(".edit-note").forEach(n => n.remove());
  if (dropped) setTimeout(() => editNotice(`${dropped} 은 이름을 적지 않아 취소했습니다`, "out"), 0);
  return new Promise(resolve => {
    const bar = document.createElement("div");
    bar.className = "author-bar" + (hint ? " with-hint" : "");
    bar.innerHTML =
      (hint ? `<span class="ab-hint">${escape(hint)}</span>` : "")
      + `<span class="muted small">${escape(what)} — 누가 고쳤나요?</span>`
      + `<input type="text" placeholder="이름 (자칭)" >`
      + `<button type="button" class="ok">확인</button>`
      + `<button type="button" class="ghost cancel">취소</button>`;
    document.body.appendChild(bar);
    const box = bar.querySelector("input");
    box.value = lastAuthor();
    box.select();
    const done = v => { _authorPending = null; bar.remove(); resolve(v); };
    // 앞 줄을 닫을 때 쓰는 손잡이.  무엇을 취소했는지 이름째 돌려준다.
    _authorPending = () => { done(null); return what; };
    bar.querySelector(".ok").onclick = () => {
      const v = box.value.trim();
      rememberAuthor(v);
      done(v);
    };
    bar.querySelector(".cancel").onclick = () => done(null);
    box.addEventListener("keydown", ev => {
      if (ev.key === "Enter") { ev.preventDefault(); bar.querySelector(".ok").click(); }
      if (ev.key === "Escape") { ev.preventDefault(); done(null); }
    });
    box.focus();
  });
}

/* hotfix66 — 결과 머리에 지금 누구 이름으로 기록되는지.  대시보드 안에서는 왼쪽 메뉴(사용자 칸)가
 * 숨겨지므로 여기가 그 사실을 말하는 자리다. */
function renderWhoChip() {
  const el = document.getElementById("who-chip");
  if (!el) return;
  const who = currentAuthor();
  el.textContent = who ? `✎ ${who}` : "✎ 이름 없음";
  el.title = who
    ? `고친 칸은 "${who}" 이름으로 기록되고 표시됩니다 — ${authorSource()}`
    : "첫 편집 때 이름을 한 번 묻고, 그 뒤로는 묻지 않습니다 (대시보드에서 열면 로그인 이름을 씁니다)";
  el.classList.toggle("login", !!EMBED.user);
}

/* 그 칸을 마지막으로 고친 사람 — `/rows` 의 `edited_by` (서버 `db.last_editors`) 와 이번 화면에서 저장한 것. */
function editorOf(row, field) {
  const e = row && row.edited_by && row.edited_by[field];
  return e && e.author ? e : null;
}
function stampEditor(row, field, author) {
  row.edited_by = row.edited_by || {};
  row.edited_by[field] = { author: author || "", at: Date.now() / 1000 };
}
function editedTitle(row, field, val) {
  const e = editorOf(row, field);
  const base = val !== "" && val != null ? String(val) : "";
  if (!(row.user && field in row.user)) return base;
  const when = e && e.at ? new Date(e.at * 1000).toLocaleString("ko-KR", { hour12: false }) : "";
  return (base ? base + "\n" : "") + `✎ ${e ? e.author : "이름 없음"}${when ? " · " + when : ""} 고침`;
}

/* 편집이 발주처 양식에 어떻게 닿는지 — 고친 **그 순간** 말한다 (14회차).
 *
 * 12회차의 근거 패널은 행을 **누른** 사람에게만 말한다.  칸을 바로 고치는
 * 사람은 패널을 안 볼 수 있고, 갈음 검증에서 드러난 것이 정확히 그 경우다:
 * 벤더 행의 값을 고쳐도 발주처 양식에는 안 실리는데 화면이 조용했다.
 *
 * **막지 않는다.**  화면·DB 에는 남아야 하고, 그 행의 SCOPE 가 나중에 SCT 로
 * 바뀔 수도 있다.  알리기만 한다.
 *
 * 판정은 `scopeFacts` 하나에서 온다(근거 패널과 같은 함수).  행수는 서버의
 * `/scope_summary` 에서 오고, 그 응답은 산출 필터와 같은 판정을 쓴다 - 화면이
 * 말하는 수와 파일에 들어가는 수가 갈리면 안 된다. */
function editNotice(text, tone) {
  // 한 번에 한 줄만 둔다.  14회차 캡처가 잡은 것: 앞 편집의 "나갑니다" 가
  // 남아 있는 채로 다음 행의 "나가지 않습니다" 가 떠서, **서로 반대인 두
  // 문장이 동시에** 화면에 있었다.  둘 다 각자의 행에 대해서는 맞는 말이라
  // 더 나쁘다 - 어느 행 이야기인지 화면이 말하지 않는다.
  document.querySelectorAll(".edit-note").forEach(n => n.remove());
  const bar = document.createElement("div");
  bar.className = "edit-note" + (tone ? ` ${tone}` : "");
  bar.textContent = text;
  document.body.appendChild(bar);
  setTimeout(() => bar.classList.add("go"), 4200);
  setTimeout(() => bar.remove(), 4900);
  return bar;
}

async function formRowCount() {
  try {
    const r = await fetch(`/jobs/${S.job.id}/scope_summary`);
    if (!r.ok) return null;
    return (await r.json()).delivered;
  } catch (e) { return null; }       // 숫자는 곁들이는 말이다 - 없으면 뺀다
}

/* 편집 뒤 한 줄.  SCOPE 를 고쳤으면 그 행이 양식에 드나든 것을 세어 말하고,
 * 다른 칸을 고쳤으면 그 행이 애초에 양식 밖인지를 말한다. */
async function noticeAfterEdit(row, field, before, after) {
  const was = scopeFacts(before, { needsReview: row.needs_review });
  const now = scopeFacts(after, { needsReview: row.needs_review });
  if (field === "scope" && was.inForm !== now.inForm) {
    const n = await formRowCount();
    const moved = now.inForm ? "발주처 양식에 들어갑니다" : "발주처 양식에서 빠집니다";
    editNotice(`${moved}${n === null ? "" : ` — 지금 ${n}행`}`,
               now.inForm ? "in" : "out");
    return;
  }
  if (field === "scope") {           // 갈래가 안 바뀐 SCOPE 편집
    editNotice(`${now.supplierName} — ${now.formLine}`, now.inForm ? "in" : "out");
    return;
  }
  // 세 갈래 모두 말한다.  "나간다" 도 사실이고, 그것을 안 적으면 침묵이
  // "나간다" 를 뜻하게 된다 - 14회차에 고친 결함이 정확히 그 구조였다.
  //
  // 18회차 — 문장을 여기서 다시 쓰지 않고 `scopeFacts` 의 것을 그대로 쓴다.
  // 전량 모드에서는 벤더 행도 나가므로, 여기 "나가지 않습니다" 를 박아 두면
  // 근거 패널과 편집 안내가 **서로 다른 말**을 한다.
  editNotice(`저장했습니다. 이 행은 발주처 양식에 ${now.formLine}`,
             now.inForm ? (now.state === "vendor" ? "unjudged" : "in")
                        : "out");
}

/* hotfix64 — 칸 하나를 저장하는 **단 하나의 길**.  목록 칸(`saveEdit`)과 도면 위 편집 카드(`floatEdit`)가
 * 같이 부른다 — 어디서 고쳤든 같은 PATCH · 같은 작성자 확인 · 같은 뒤처리(목록 칸 · 줄 표시 · 근거 패널 ·
 * 도면 표시 · 양식 안내)이고, 그래서 도면에서 고친 값이 목록에 **저절로** 같은 값으로 선다.
 * 돌려주는 값: true 저장 · false 실패 · null 취소 · undefined 바뀐 것 없음. */
async function saveField(row, field, value) {
  value = String(value ?? "").trim();
  const current = row.values[field] ?? "";
  if (String(current) === value) return undefined;
  const scopeBefore = row.values.scope;
  // 저장하기 **전에** 알린다 - 이 행이 발주처 양식 밖이면 고친 값이 파일에
  // 닿지 않는다는 것을 그 순간 아는 편이 낫다.  막지는 않는다.
  const before = scopeFacts(scopeBefore, { needsReview: row.needs_review });
  // 18회차 — 여기도 `scopeFacts` 가 쓴 문장을 그대로 쓴다.  저장 전과 저장
  // 후가 다른 말을 하면 안 되고, 전량 모드에서는 벤더 행도 나간다.
  const hint = field === "scope" || before.state === "delivered" ? ""
    : `이 행은 발주처 양식에 ${before.formLine}`;
  const author = await askAuthor(`${field} 수정`, hint);
  if (author === null) return null;                         // 취소
  // hotfix74 — 서버가 꺼졌거나 연결이 끊기면 **칸을 원래 값으로 돌리고 그렇게 말한다**.  돌발상황
  // 시뮬레이션(U2): 예외가 그대로 올라가 칸은 새 값을 보이고 아무 말이 없었다 — 저장된 줄 알고 넘어간다.
  let r;
  try {
    r = await fetch(`/jobs/${S.job.id}/rows/${row.key}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, value, author }),
    });
  } catch (e) {
    alert("저장하지 못했습니다 — 서버에 연결할 수 없습니다.  칸은 원래 값으로 돌아갑니다.\n"
      + "서버(P&ID 분석 프로그램)가 켜져 있는지 확인한 뒤 다시 고쳐 주세요.");
    return false;
  }
  if (!r.ok) {
    let msg = "저장 실패 (서버 응답 " + r.status + ")";
    try { msg = (await r.json()).detail || msg; } catch (e) { /* 본문이 JSON 이 아니다 */ }
    // hotfix74 — 다른 창(다른 사람)이 이 분석을 지운 뒤 고치면 영문 "no such job" 한 줄만 떴다.
    if (r.status === 404 && /no such (job|row)/i.test(String(msg))) {
      msg = "저장하지 못했습니다 — 이 분석(또는 이 행)이 서버에 없습니다.  다른 창이나 다른 사람이 지웠을 수 있습니다.  "
        + "첫 화면에서 다시 열어 주세요.";
    }
    alert(msg); return false;
  }
  const out = await r.json();
  row.user = out.user;
  stampEditor(row, field, author);
  row.values[field] = value === "" ? row.ai[field] : (field === "qty" ? Number(value) : value);
  delete (row.conflict || {})[field];
  S.counts.REVIEW = out.review_count;
  if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
  updateBadge();
  syncRowCell(row, field);            // 오른쪽 목록 — 그 칸만 제자리에서 (아래 주석)
  repaintRow(row);
  if (S.sel === row.key) showEvidence(row);
  // 53회차 [F] — SCOPE 를 고쳤으면 **그 자리에서 색이 따라간다** (8차 s7).  hotfix64 — Q'ty 라벨(x N) ·
  // TYPE 도 도면 위에 서 있으므로 같이 다시 그린다.  색·라벨을 정하는 곳은 그대로 `itemScope`·`cellValue` 다.
  if (field === "scope" || field === "qty" || field === "type" || field === "tag_no") drawOverlay();
  if (field === "qty") _refreshPageMult();
  renderFloatEdit();
  noticeAfterEdit(row, field, scopeBefore, row.values.scope);
  return true;
}

/* 목록의 그 행 그 칸을 지금 값으로.  행을 다시 그리지 않는다 — 저장은 사람이 이미 다음 칸을 누른 뒤에 끝나고,
 * 그 순간 목록을 통째로 다시 그리면 타자 중인 칸이 떨어져 나가 편집이 사라졌다. */
function syncRowCell(row, field) {
  const td = document.querySelector(`#body tr[data-key="${CSS.escape(row.key)}"] td[data-col="${field}"]`);
  if (!td) return;
  // 목록이 그 칸을 그릴 때와 같은 값 (renderGrid — Remark 만 `remarkOf`, 나머지는 행의 값 그대로)
  const v = field === "remark" ? remarkOf(row) : (row.values[field] ?? "");
  td.textContent = v ?? "";
  td.title = editedTitle(row, field, v);
  td.classList.toggle("edited", !!(row.user && field in row.user));
  td.classList.remove("conflict");
}

async function saveEdit(row, field, td) {
  const current = row.values[field] ?? "";
  const ok = await saveField(row, field, td.textContent.trim());
  if (ok === null || ok === false) td.textContent = current;      // 취소 · 실패 — 칸을 원래 값으로
}

/* ---------------- hotfix64 — 전체화면에서도 도면 위에서 고친다 ----------------
 *
 * 사용자: *"P&ID 가 전체화면이 되어도 사용자가 수정할 수 있어야 하고 수정된 값은 List 에 자동으로 반영되어야 한다."*
 * 목록이 안 보이는 두 경우 — ⛶ 전체화면 · 경계를 끝까지 밀어 목록이 접힌 것(hotfix63) — 에 도면에서 상자를 누르면
 * 그 자리에 편집 카드가 뜬다.  칸 목록은 목록 머리글과 **같은 표**(`COLS` 의 편집 가능 칸)이고, 저장은
 * `saveField` 하나라 목록 칸이 같은 값으로 저절로 바뀐다 — 화면을 다시 열거나 새로고침할 필요가 없다. */
const FEDIT_FIELDS = COLS.filter(c => c[2]);
const FEDIT_LONG = new Set(["description", "remark"]);
/* hotfix69 — 목록 칸 폭은 크기가 바뀔 때만 잰다 (`ResizeObserver`).  예전에는 상자를 누를 때마다 폭을 물어 브라우저가
 * 그 자리에서 배치를 다시 해야 했다 (행 누르기 한 번에 70ms — perf_sim 프로파일). */
let _rightW = null;
(function watchRight() {
  const rg = document.getElementById("right");
  if (!rg || typeof ResizeObserver === "undefined") return;
  new ResizeObserver(ents => { for (const e of ents) _rightW = e.contentRect.width; }).observe(rg);
})();
function listHidden() {
  const rg = document.getElementById("right");
  if (!rg) return true;
  if (_rightW === null) _rightW = rg.getBoundingClientRect().width;
  return _rightW < 320;
}
function floatEditWanted() { return document.body.classList.contains("pid-full") || listHidden(); }
function _feditRow() {
  if (!S.sel || !S.rows) return null;
  return (S.rowByKey && S.rowByKey[S.sel]) || S.rows.find(r => r.key === S.sel) || null;
}
function _feditPageRows(row) {
  // 같은 장의 행을 도면 위 자리 순서로 (위→아래 · 왼→오) — ◀ ▶ 가 도면을 훑는 순서
  const at = r => Array.isArray(r.rect) && r.rect.length >= 4 ? r.rect : [0, 0, 0, 0];
  return S.rows.filter(r => r.page_no === row.page_no && !r.deleted && !r.removed && !r.delCand)
    .sort((a, b) => (at(a)[1] - at(b)[1]) || (at(a)[0] - at(b)[0]));
}
function renderFloatEdit() {
  const box = document.getElementById("fedit");
  if (!box) return;
  const row = _feditRow();
  if (!row || !floatEditWanted() || row.deleted || row.removed || row.delCand || (S.multi && S.multi.size)) {
    box.classList.add("hidden"); box.dataset.key = ""; return;
  }
  const same = box.dataset.key === row.key && !box.classList.contains("hidden");
  if (same) {
    // 같은 행 — 칸을 다시 만들지 않고 값만 맞춘다 (사람이 다음 칸에 타자 중일 수 있다)
    box.querySelectorAll("[data-f]").forEach(inp => {
      const f = inp.dataset.f;
      if (document.activeElement !== inp) inp.value = row.values[f] ?? "";
      inp.closest(".fe-row").classList.toggle("edited", !!(row.user && f in row.user));
    });
    return;
  }
  box.dataset.key = row.key;
  const list = _feditPageRows(row);
  const i = list.findIndex(r => r.key === row.key);
  const pid = (S.pages.find(p => p.page_no === row.page_no) || {}).drawing_no || "";
  const head = `${escape(String(cellValue(row, "type") || "?"))}`
    + (row.values.tag_no ? ` <span class="fe-tag">${escape(String(row.values.tag_no))}</span>` : "");
  box.innerHTML = `<div class="fe-head"><b>${head}</b>`
    + `<span class="muted small">p${row.page_no} ${escape(pid)} · ${i + 1}/${list.length}</span>`
    + `<span class="fe-nav"><button type="button" class="ghost mini" data-nav="-1" title="이 장의 앞 항목 (도면 위→아래 순)">◀</button>`
    + `<button type="button" class="ghost mini" data-nav="1" title="이 장의 다음 항목">▶</button>`
    + `<button type="button" class="ghost mini" data-nav="0" title="닫기 (Esc)">✕</button></span></div>`
    + `<div class="fe-body">` + FEDIT_FIELDS.map(([f, label]) => {
        const v = row.values[f] ?? "";
        const ai = (row.ai || {})[f];
        const who = editorOf(row, f);
        const tip = row.user && f in row.user ? `${who ? who.author : "이름 없음"} 고침 — 도면 값은 ${ai ?? "(없음)"} · 비우고 저장하면 도면 값으로` : "도면에서 읽은 값";
        const input = FEDIT_LONG.has(f)
          ? `<textarea data-f="${f}" rows="2" spellcheck="false">${escape(String(v))}</textarea>`
          : `<input data-f="${f}" type="text" value="${escAttr(String(v))}" spellcheck="false">`;
        return `<label class="fe-row${row.user && f in row.user ? " edited" : ""}" title="${escAttr(tip)}">`
          + `<span class="fe-l">${escape(label)}</span>${input}</label>`;
      }).join("") + `</div>`
    + `<div class="fe-foot muted small">Enter 저장 (긴 칸은 Ctrl+Enter) · 고친 값은 오른쪽 목록에 바로 반영됩니다 · ${escape(currentAuthor() || "이름 없음")} 이름으로 기록`
    + ` · ✎ 사람이 고친 칸</div>`;
  box.classList.remove("hidden");
  box.querySelectorAll("[data-f]").forEach(inp => {
    const f = inp.dataset.f;
    const commit = async () => {
      const r = _feditRow();
      if (!r || r.key !== row.key) return;
      const ok = await saveField(r, f, inp.value);
      if (ok === null || ok === false) inp.value = r.values[f] ?? "";
    };
    inp.addEventListener("keydown", ev => {
      if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); inp.value = row.values[f] ?? ""; inp.blur(); }
      else if (ev.key === "Enter" && (!FEDIT_LONG.has(f) || ev.ctrlKey || ev.metaKey)) { ev.preventDefault(); inp.blur(); }
    });
    inp.addEventListener("blur", commit);
  });
  box.querySelectorAll("[data-nav]").forEach(b => b.onclick = () => {
    const step = +b.dataset.nav;
    if (!step) { deselect(); return; }
    const pool = _feditPageRows(row);
    const j = pool.findIndex(r => r.key === row.key);
    const next = pool[(j + step + pool.length) % pool.length];
    if (next) select(next.key, true);
  });
}
function setFull(on) {
  document.body.classList.toggle("pid-full", !!on);
  const b = document.getElementById("full-toggle");
  if (b) { b.setAttribute("aria-pressed", on ? "true" : "false"); b.textContent = on ? "⤡ 전체화면 끝" : "⛶ 전체화면"; }
  // 브라우저 전체화면도 청한다 (주소줄·탭이 사라진다).  대시보드 iframe 처럼 허락되지 않은 곳에서는
  // 조용히 실패하고 화면 안 전체화면만 된다 — 편집은 어느 쪽이든 같다.
  try {
    if (on && !document.fullscreenElement && document.documentElement.requestFullscreen)
      document.documentElement.requestFullscreen().catch(() => {});
    else if (!on && document.fullscreenElement && document.exitFullscreen)
      document.exitFullscreen().catch(() => {});
  } catch (e) { /* 허락 안 됨 — 화면 안 전체화면만 */ }
  window.dispatchEvent(new Event("resize"));
  renderFloatEdit();
}
document.addEventListener("fullscreenchange", () => {
  // 브라우저 Esc 로 전체화면이 풀리면 화면 안 전체화면도 같이 푼다 — 둘이 갈리면 안 된다
  if (!document.fullscreenElement && document.body.classList.contains("pid-full")) setFull(false);
});
window.addEventListener("resize", () => renderFloatEdit());
$req("#full-toggle").addEventListener("click", () => setFull(!document.body.classList.contains("pid-full")));

/* Writing a Description by hand.
 *
 * A reviewer picks a candidate phrase off the evidence panel, or types one, and
 * the row becomes USER_ENTERED with an empty Remark - the tool stops asking about
 * a row a person has answered.  The same text can be pushed to every row on the
 * same drawing with the same TYPE, because 721 rows share 85 machine-written
 * sentences and retyping the difference by hand is the actual work.
 */
async function setDescription(row, text, opts = {}) {
  // 44회차 UI 시험이 잡은 옛 결함 — 일괄 적용의 마무리 alert 가 정의되지 않은
  // `was` 를 읽어 ReferenceError 를 냈다 (적용은 이미 끝난 뒤라 눈에 안 띄었다).
  // 묶음이 공유하던 문장은 고치기 **전**에 잡아 둔다.
  const was = row.values.description ?? "";
  const patch = async (r, field, value) => {
    const res = await fetch(`/jobs/${S.job.id}/rows/${r.key}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      // hotfix66 — 이 길은 작성자를 싣지 않고 있었다 (이력에 이름 없음).  묻지 않고 로그인 이름을 싣는다.
      body: JSON.stringify({ field, value, author: currentAuthor() }),
    });
    if (!res.ok) { alert((await res.json()).detail || "저장 실패"); return false; }
    const out = await res.json();
    r.user = out.user;
    stampEditor(r, field, currentAuthor());
    r.values[field] = value;
    S.counts.REVIEW = out.review_count;
    if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
    repaintRow(r);
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
  //
  // ⚠ 18회차 [I]: 사정거리를 여기서 **다시 계산하고 있었다.**  화면이 누르기
  // 전에 "N행 있습니다" 라고 말할 때는 `sameSentence` 를 쓰고, 실제로 누르면
  // 이 복사본이 돌았다 — 접미(17회차 C-1)가 붙자 둘이 갈려서 화면은 3행이라고
  // 하고 파일은 1행만 바뀌었다.  **판정하는 곳은 하나여야 한다** (11회차 교훈).
  const targets = opts.bulk ? sameSentence(row) : [row];
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
const SYMBOL_ZOOM = 2.2;

/* hotfix13 — **더하기 키는 Shift 와 Ctrl(맥은 Cmd) 둘이다.**  요구: *"컨트롤 누르고
 * 식별된 것 클릭하면 복수 선택"*.  탐색기·엑셀에서 손에 익은 쪽이 사람마다 달라
 * 둘 다 받는다.  뜻은 하나 — 묶음에 더하거나 뺀다.  끌기(띠)는 Shift 만이다
 * (Ctrl + 휠은 이미 확대다). */
function isAddClick(ev) { return !!(ev && (ev.shiftKey || ev.ctrlKey || ev.metaKey)); }      // enough to read a 22pt bubble on a 2384pt sheet

function select(key, fromGrid, item) {
  // 그냥 누르면 묶음은 풀린다 (더하려면 Shift).
  S.multi.clear();
  S.sel = key;
  syncSel();                                // hotfix68 — 다른 창(도면 · 목록)도 같은 행으로
  // 삭제 후보는 `S.rows` 가 아니라 `S.deletedRows` 에 산다 (이번 리비전에 그
  // 심볼이 없으므로 검출 행이 아니다).  둘 다 봐야 근거 패널이 열린다.
  const row = S.rows.find(r => r.key === key)
    || (S.deletedRows || []).find(r => r.key === key);
  // hotfix68 — 도면이 다른 창에 있으면 이 창은 장을 그리지 않는다 (그 창이 장을 옮긴다).  "이 장" 기능이
  // 따라가도록 지금 장만 조용히 바꾼다.
  if (row && drawingHidden() && (!S.page || S.page.page_no !== row.page_no)) {
    const pg = S.pages.find(p => p.page_no === row.page_no);
    if (pg) { S.page = pg; S.imgStale = true; }
  }
  if (fromGrid && row && (!S.page || S.page.page_no !== row.page_no) && !drawingHidden()) {
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
    const tr = revealRow(key);              // hotfix69 — 화면 밖 행은 그 자리로 굴려 그린다
    if (tr) tr.scrollIntoView({ block: "center" });
  }
  pulse(key);
  if (row) showEvidence(row);
  else showExcluded(item);       // an excluded symbol has no row to show
  renderFloatEdit();             // hotfix64 — 목록이 안 보이면 도면 위 편집 카드
}

function deselect() {
  S.sel = null;
  S.pending = null;
  S.multi.clear();
  syncSel();
  document.querySelectorAll("#body tr.sel").forEach(tr => tr.classList.remove("sel"));
  document.querySelectorAll("rect.det.sel").forEach(n => n.classList.remove("sel"));
  drawOverlay();
  renderFloatEdit();             // hotfix64 — 편집 카드도 닫힌다
  $("#evidence").innerHTML =
    "<p class='muted'>행을 클릭하면 판정 근거가 여기에 표시됩니다. <b>Shift</b> 또는 <b>Ctrl</b> 을 누른 채 도면의 상자(또는 목록의 행)를 누르면 여러 개를 골라 <b>공급 주체를 한 번에</b> 바꿀 수 있습니다.</p>";
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
  // 9차 피드화 [B] — Typical 표식은 **제외된 심볼이 아니다.**  그 자리에 품목이
  // 있는 것이 아니라 "이 자리는 저 상세와 같다" 는 도면의 말이고, SCOPE 도 제외
  // 규칙도 걸리지 않는다.  54회차 캡처가 잡았다 — 패널이 "스코프 판정: 판정 없음
  // — SCOPE 열이 비어 있습니다(이 열이 생기기 전의 분석)" 라고 **없는 사실**을
  // 말하고 있었다.
  if (item.typical) {
    $("#evidence").innerHTML =
      `<h3>Typical 표식 — ${escape(item.label || "")} (p${S.page.page_no})</h3><dl>`
      + `<dt>무엇인가</dt><dd>${escape(item.reason || "")}</dd>`
      + `<dt>위치</dt><dd>${escape(S.page.drawing_no || "")} · p${S.page.page_no}`
      + ` · (${item.rect.map(v => Math.round(v)).join(", ")})</dd>`
      + `<dt>리스트 반영</dt><dd>이 표식 자체는 행이 아닙니다 — 표식 아래 이름표(예: DRAIN 3)가`
      + ` 있으면 상세 상자 안의 행이 <b>표식마다 한 행</b>으로 나가고 Description 에 그 이름표가 붙습니다.`
      + ` 이름표가 없으면 상자 안 행의 수량이 참조 수만큼 곱해집니다 (근거는 그 행의 <b>수량 근거</b>)</dd>`
      + `</dl>`;
    return;
  }
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

/* 53회차 [F] — 공급 주체를 바로 고르는 자리 (8차 피드백 s7).
 *
 * 요구 둘: *"SCOPE 를 변경하면 SCT, VENDOR 에 따라 색상이 변하게 하라"* 와
 * *"VENDOR 로 선택했을 때 괄호 안에 어느 VENDOR 인지 작성하거나 **추출된
 * VENDOR 목록들 중에서 선택**할 수 있도록"*.
 *
 * 목록은 **그 도면에서 나온 것만** 쓴다 — 공급자 이름은 그 장 NOTES 가 정하고
 * (10회차) 코드에도 config 에도 이름을 두지 않는다는 규칙 그대로다.  그래서
 * 후보는 지금 결과의 `VENDOR(...)` 값을 모은 것이고, 그 도면이 한 번도 말하지
 * 않은 이름은 목록에 없다.  직접 적는 칸은 남겨 둔다 — 도면이 안 쓴 이름을
 * 사람이 아는 경우가 있고, 그때 값의 출처는 사람이다(편집 이력에 남는다). */
function vendorNames() {
  const out = new Set();
  for (const r of (S.rows || [])) {
    const v = String(cellValue(r, "scope") || "");
    const m = /^VENDOR\((.+)\)$/.exec(v);
    if (m && m[1].trim()) out.add(m[1].trim());
  }
  return [...out].sort();
}

function scopeEditor(row) {
  const cur = String(cellValue(row, "scope") || "");
  const isVen = cur.startsWith(SCOPE_VENDOR_PREFIX);
  const name = (/^VENDOR\((.+)\)$/.exec(cur) || [, ""])[1];
  const names = vendorNames();
  return `<div class="ractions"><div class="ract scopeed"><span>공급 주체</span>
    <button class="ract-b sc-b${cur === SCOPE_DELIVERED ? " on" : ""}" data-sc="SCT">SCT</button>
    <button class="ract-b sc-b${isVen ? " on" : ""}" data-sc="VENDOR">VENDOR</button>
    <button class="ract-b sc-none danger" title="그려진 것은 맞지만 공급 대상이 아님 — 식별을 지웁니다 (Excel 에서 빠짐 · 되돌릴 수 있음)"${row.removed ? " disabled" : ""}>둘 다 아님 — 식별 지우기</button>
    <span class="sc-ven${isVen ? "" : " hidden"}">
      <select id="sc-name"><option value="">(이름 없음)</option>${
        names.map(n => `<option value="${escape(n)}"${n === name ? " selected" : ""}>${escape(n)}</option>`).join("")
      }<option value="__other__">직접 입력…</option></select>
      <input id="sc-other" class="hidden" placeholder="VENDOR 이름" value="">
    </span></div>
    <p class="muted small">이 도면에서 읽은 VENDOR ${names.length}종 · 고르면 바로 저장되고 왼쪽 색이 따라갑니다</p>
    </div>`;
}

function bindScopeEditor(row) {
  const wrap = document.querySelector("#evidence .scopeed");
  if (!wrap) return;
  const sel = wrap.querySelector("#sc-name");
  const other = wrap.querySelector("#sc-other");
  const ven = wrap.querySelector(".sc-ven");
  const save = async value => {
    const td = document.querySelector(`#body tr[data-key="${CSS.escape(row.key)}"] td.col-scope`);
    if (td) { td.textContent = value; await saveEdit(row, "scope", td); return; }
    // 그리드에 그 칸이 안 보이는 경우(필터·스크롤)도 같은 경로로 저장한다.
    const shim = document.createElement("td");
    shim.textContent = value;
    await saveEdit(row, "scope", shim);
    renderGrid();
  };
  const none = wrap.querySelector("button.sc-none");
  if (none) none.onclick = () => dismissRows([row.key]);
  wrap.querySelectorAll("button.sc-b").forEach(b => {
    b.onclick = async () => {
      if (b.dataset.sc === "SCT") { ven.classList.add("hidden"); await save(SCOPE_DELIVERED); return; }
      ven.classList.remove("hidden");
      await save(SCOPE_VENDOR_PREFIX);      // 이름은 그 다음에 고른다
    };
  });
  if (sel) sel.onchange = async () => {
    if (sel.value === "__other__") { other.classList.remove("hidden"); other.focus(); return; }
    other.classList.add("hidden");
    await save(sel.value ? `${SCOPE_VENDOR_PREFIX}(${sel.value})` : SCOPE_VENDOR_PREFIX);
  };
  if (other) other.onchange = async () => {
    const v = other.value.trim();
    await save(v ? `${SCOPE_VENDOR_PREFIX}(${v})` : SCOPE_VENDOR_PREFIX);
  };
}

/* 56회차 — Shift 로 여러 개를 고르고 **공급 주체를 한 번에** 바꾼다.
 *
 * 요구(TC2 9차): *"Shift 를 누르면 왼쪽 P&ID 에서 여러 개를 클릭할 수 있고
 * 한 번에 공급 주체를 바꿀 수 있도록"*.
 *
 * 세 가지를 지킨다:
 *
 *  ① `S.sel`(한 행)은 건드리지 않는다.  근거 패널 · 배관 추적 · 가운데 맞추기가
 *    전부 한 행을 전제하고, 여럿을 그 칸에 밀어 넣으면 그 셋이 함께 흔들린다.
 *  ② 저장하는 길은 **한 행짜리와 같은 PATCH** 다 (`field: "scope"`).  묶음
 *    전용 엔드포인트를 만들면 편집 이력·검토 수·충돌 판정이 두 벌이 된다.
 *  ③ 작성자는 **한 번만** 묻고 모든 행에 같이 적는다 (13회차 — 확인은 매번,
 *    타자는 한 번).  묶음이라고 이름을 비우지 않는다.
 */
function multiRows() {
  return [...S.multi].map(k => S.rows.find(r => r.key === k)).filter(Boolean);
}

function markMultiRows() {
  document.querySelectorAll("#body tr").forEach(tr =>
    tr.classList.toggle("multi", S.multi.has(tr.dataset.key)));
}

function toggleMulti(key) {
  // 첫 Shift 클릭은 **이미 고른 행과 둘**을 뜻한다 — 사람이 하나를 눌러 보고
  // "이것도" 라고 더하는 것이 이 동작의 실제 쓰임이다.
  if (!S.multi.size && S.sel && S.sel !== key) S.multi.add(S.sel);
  if (S.multi.has(key)) S.multi.delete(key); else S.multi.add(key);
  if (S.multi.size === 1) S.multi.clear();     // 하나만 남으면 묶음이 아니다
  syncSel();
  drawOverlay();
  markMultiRows();
  if (S.multi.size) showMultiScope();
  else if (S.sel) {
    const row = S.rows.find(r => r.key === S.sel);
    if (row) showEvidence(row);
  } else deselect();
}

function clearMulti() {
  S.multi.clear();
  syncSel();
  drawOverlay();
  markMultiRows();
  const row = S.sel && S.rows.find(r => r.key === S.sel);
  if (row) showEvidence(row); else deselect();
}

/* hotfix14 — **잘못 추출된 행을 지운다** (요구: *"잘못 추출된 것은 삭제 가능하도록 ·
 * 오른쪽에서 삭제하면 왼쪽 P&ID 에서 붉은 선으로 삭제되었음을 식별"*).
 * 행은 지워지지 않고 `removed` 표시만 남는다 (44회차 — 다음 분석이 그 자리를 다시
 * 찾아도 사람의 판단이 살아 있어야 한다).  Excel 에서는 빠지고 되돌릴 수 있다.
 * 부르는 곳은 셋(목록 위 단추 · 근거 패널 · 묶음 패널)이고 하는 일은 여기 하나다. */
async function deleteRows(keys, opts = {}) {
  keys = keys.filter(k => S.rowByKey[k] && !S.rowByKey[k].removed);
  if (!keys.length) { alert("지울 행이 없습니다 (이미 지운 행은 되돌리기로 살립니다)."); return; }
  // hotfix66 — '공급 대상 아님' 처럼 사유가 정해진 길은 묻지 않는다 (opts.reason).
  const reason = opts.reason !== undefined ? opts.reason
    : window.prompt(`${keys.length}개 행을 오검출로 지웁니다 — 사유 (선택 · 비워도 됩니다)`, "");
  if (reason === null) return;
  const author = await askAuthor(`${keys.length}개 행 삭제`);
  if (author === null) return;
  // hotfix75 — 행마다 DELETE(한 번 0.4초 · 30행이면 13초) 를 요청 하나로, 그 뒤 목록 전체(7MB)를 다시 받던 것을
  // **지운 행만** 다시 받는다 (`refreshRows(..., {keys})`).  서버가 하는 일은 DELETE 와 같은 함수다.
  let r;
  try {
    r = await fetch(`/jobs/${S.job.id}/rows_delete`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keys, reason: String(reason).trim(), reason_class: opts.klass || "FALSE_POSITIVE",
                             author, exclude: true }),
    });
  } catch (e) { alert("삭제하지 못했습니다 — 서버에 연결할 수 없습니다."); return; }
  if (!r.ok) { alert("삭제 실패"); return; }
  const out = await r.json();
  if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
  const done = Object.keys(out.rows || {}).length;
  S.multi.clear();
  await refreshRows(keys.length === 1 ? keys[0] : null, { keys });
  // 고른 행이 없으면 `refreshRows` 는 목록만 다시 읽는다 — 붉은 표시가 다음 동작
  // 뒤에야 서던 것을 그 자리에서 그린다 (자기검증이 잡았다).
  if (keys.length === 1) drawOverlay(); else deselect();   // 묶음 패널은 이제 빈 묶음을 말한다
  markMultiRows();
  editNotice(opts.klass === "NOT_SUPPLY"
    ? `${done}개 식별을 지웠습니다 — SCT 도 VENDOR 도 아님 · 도면에 붉은 ✕ 로 남고 Excel 에서 빠집니다 (눌러서 되돌릴 수 있습니다)`
    : `${done}개 행을 지웠습니다 — 도면에 붉은 ✕ 로 남고 Excel 에서 빠집니다 (되돌릴 수 있습니다)`, "out");
}

/* hotfix66 — **SCT 도 VENDOR 도 아닌 것은 식별을 지운다** (사용자: *"식별된 것들을 클릭해서 Vendor 도 SCT
 * 공급도 아닌 것으로 식별을 지울 수 있는 기능"*).  하는 일은 위 `deleteRows` 그대로 — 행은 남고 `removed` 표시 ·
 * Excel 에서 빠짐 · 도면 붉은 ✕ · 되돌리기 — 이고, 사유 분류만 `NOT_SUPPLY`(오검출 ㉢ 과 다르다: 그 자리에
 * 그려진 것은 맞는데 세지 않는다) 이며 사유를 묻지 않는다. */
const NOT_SUPPLY_NOTE = "SCT 도 VENDOR 도 아님";
function dismissRows(keys) {
  return deleteRows(keys, { klass: "NOT_SUPPLY", reason: NOT_SUPPLY_NOTE });
}

/* 도면에서 상자를 누르면 그 옆에 뜨는 작은 판 — SCT · VENDOR · 둘 다 아님.  저장은 목록 칸과 같은 `saveField`
 * (SCOPE) · 지우기는 `dismissRows` · 되돌리기는 `restoreRow` — 판은 고르기만 한다. */
function closeScopePop() {
  document.querySelectorAll(".scopepop").forEach(n => n.remove());
  if (closeScopePop._off) { document.removeEventListener("pointerdown", closeScopePop._off, true); closeScopePop._off = null; }
}
function scopePop(key) {
  closeScopePop();
  const row = S.rowByKey && S.rowByKey[key];
  if (!row || row.deleted) return;
  const box = document.querySelector(`rect.det[data-key="${CSS.escape(key)}"]`);
  if (!box) return;
  const ab = box.getBoundingClientRect();
  const cur = String(cellValue(row, "scope") || "");
  const names = vendorNames();
  const pop = document.createElement("div");
  pop.className = "scopepop";
  pop.setAttribute("role", "dialog");
  const head = `${escape(String(cellValue(row, "type") || ""))} ${escape(String(cellValue(row, "tag_no") || ""))}`.trim();
  pop.innerHTML = row.removed
    ? `<div class="sp-h">${head || "이 항목"} — 지운 식별</div>`
      + `<div class="sp-btns"><button type="button" class="sp-b" data-sp="restore">되돌리기</button>`
      + `<button type="button" class="sp-b ghost" data-sp="close">닫기</button></div>`
    : `<div class="sp-h">${head || "이 항목"} · 지금 ${escape(cur || "(비어 있음)")}</div>`
      + `<div class="sp-btns">`
      + `<button type="button" class="sp-b sct${cur === SCOPE_DELIVERED ? " on" : ""}" data-sp="sct">SCT 공급</button>`
      + `<button type="button" class="sp-b ven${cur.startsWith(SCOPE_VENDOR_PREFIX) ? " on" : ""}" data-sp="vendor">VENDOR</button>`
      + (names.length ? `<select class="sp-name" title="VENDOR 이름 (이 도면에서 읽은 것)"><option value="">(이름 없음)</option>${
          names.map(n => `<option value="${escAttr(n)}">${escape(n)}</option>`).join("")}</select>` : "")
      + `<button type="button" class="sp-b none" data-sp="none" title="그려진 것은 맞지만 공급 대상이 아님 — 식별을 지웁니다 (Excel 에서 빠짐 · 되돌릴 수 있음)">둘 다 아님 — 식별 지우기</button>`
      + `</div><div class="sp-note muted small">Esc 닫기 · 지운 것은 다시 눌러 되돌립니다</div>`;
  document.body.appendChild(pop);
  const pw = pop.offsetWidth, ph = pop.offsetHeight;
  let left = ab.right + 8, top = ab.top - 6;
  if (left + pw > window.innerWidth - 8) left = Math.max(8, ab.left - pw - 8);
  if (top + ph > window.innerHeight - 8) top = Math.max(8, window.innerHeight - ph - 8);
  pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  pop.querySelectorAll("button.sp-b").forEach(b => {
    b.onclick = async (ev) => {
      ev.stopPropagation();
      const what = b.dataset.sp;
      closeScopePop();
      if (what === "close") return;
      if (what === "restore") return restoreRow(key);
      if (what === "none") return dismissRows([key]);
      if (what === "sct") { await saveField(row, "scope", SCOPE_DELIVERED); return; }
      const sel = pop.querySelector(".sp-name");
      const name = sel ? sel.value : "";
      await saveField(row, "scope", name ? `${SCOPE_VENDOR_PREFIX}(${name})` : SCOPE_VENDOR_PREFIX);
    };
  });
  const sel = pop.querySelector(".sp-name");
  if (sel) sel.onclick = (ev) => ev.stopPropagation();
  closeScopePop._off = (ev) => { if (!pop.contains(ev.target)) closeScopePop(); };
  setTimeout(() => document.addEventListener("pointerdown", closeScopePop._off, true), 0);
}

async function restoreRow(key) {
  await fetch(`/jobs/${S.job.id}/rows/${key}/restore`, { method: "POST" });
  await refreshRows(key, { keys: [key] });
  drawOverlay();
  editNotice("되돌렸습니다 — 다시 결과와 Excel 에 들어갑니다", "in");
}

function qtySummary(rows) {
  const by = {};
  for (const r of rows) { const q = cellValue(r, "qty"); const k = q === "" || q == null ? "?" : q; by[k] = (by[k] || 0) + 1; }
  return "지금 " + Object.entries(by).map(([k, n]) => `x${k} ${n}`).join(" · ");
}

function showMultiScope() {
  const rows = multiRows();
  const by = {};
  for (const r of rows) {
    const v = String(cellValue(r, "scope") || "") || "(비어 있음)";
    by[v] = (by[v] || 0) + 1;
  }
  const names = vendorNames();
  const pages = [...new Set(rows.map(r => r.page_no))].sort((a, b) => a - b);
  $("#evidence").innerHTML =
    `<h3>선택 ${rows.length}개 — 공급 주체 · 승수를 한 번에</h3>`
    + `<p class="muted small">p${pages.join(" · p")} · Shift 또는 Ctrl + 클릭으로 더하거나 뺍니다</p>`
    + `<p class="small">지금 값 — ${Object.entries(by)
        .map(([k, n]) => `${escape(k)} ${n}`).join(" · ")}</p>`
    + `<div class="ractions"><div class="ract scopemulti"><span>바꿀 값</span>
        <button class="ract-b mc-b" data-mc="SCT">SCT</button>
        <button class="ract-b mc-b" data-mc="VENDOR">VENDOR</button>
        <button class="ract-b danger" id="mc-none" title="고른 것 전부 — 공급 대상이 아님 · 식별을 지웁니다 (되돌릴 수 있음)">둘 다 아님 — 식별 지우기</button>
        <select id="mc-name"><option value="">(이름 없음)</option>${
          names.map(n => `<option value="${escape(n)}">${escape(n)}</option>`).join("")
        }<option value="__other__">직접 입력…</option></select>
        <input id="mc-other" class="hidden" placeholder="VENDOR 이름">
      </div>
      <p class="muted small">VENDOR 는 이름을 고른 뒤 적용됩니다 · 이 도면에서 읽은 ${names.length}종</p>
      <div class="ract qtymulti"><span>승수 (Q'ty)</span>
        <input id="mq-val" type="number" min="0" step="1" placeholder="${escape(qtySummary(rows))}">
        <button class="ract-b" id="mq-apply">선택 ${rows.length}개에 적용</button></div>
      <p class="muted small">비우고 적용하면 도면 값으로 되돌립니다 · 도면의 x N 라벨을 눌러도 같습니다</p>
      <div class="ract"><button class="ract-b" id="mc-clear">선택 해제</button>
        <button class="ract-b danger" id="mc-delete" title="고른 행을 오검출로 지웁니다 — 도면에 붉은 ✕ 로 남고 Excel 에서 빠집니다">선택 ${rows.length}개 삭제</button></div>
      </div>`;
  const wrap = document.querySelector("#evidence .scopemulti");
  const sel = wrap.querySelector("#mc-name");
  const other = wrap.querySelector("#mc-other");
  wrap.querySelectorAll("button.mc-b").forEach(b => {
    b.onclick = () => {
      if (b.dataset.mc === "SCT") return applyScopeToMulti(SCOPE_DELIVERED);
      const v = other.classList.contains("hidden") ? sel.value : other.value.trim();
      return applyScopeToMulti(v ? `${SCOPE_VENDOR_PREFIX}(${v})` : SCOPE_VENDOR_PREFIX);
    };
  });
  sel.onchange = () => {
    if (sel.value === "__other__") { other.classList.remove("hidden"); other.focus(); }
    else other.classList.add("hidden");
  };
  const mcn = document.querySelector("#mc-none");
  if (mcn) mcn.onclick = () => dismissRows(multiRows().map(r => r.key));
  const mq = document.querySelector("#mq-val");
  const mqGo = () => {
    const v = mq.value.trim();
    if (v !== "" && !/^\d+$/.test(v)) { mq.classList.add("bad"); return; }
    applyQtyToRows(multiRows().filter(r => !r.deleted && !r.removed), v, `선택 ${rows.length}개`);
  };
  document.querySelector("#mq-apply").onclick = mqGo;
  mq.addEventListener("keydown", ev => { if (ev.key === "Enter") { ev.preventDefault(); mqGo(); } });
  document.querySelector("#mc-clear").onclick = clearMulti;
  document.querySelector("#mc-delete").onclick = () => deleteRows(rows.map(r => r.key));
}

async function applyScopeToMulti(value) {
  const rows = multiRows();
  if (!rows.length) return;
  const author = await askAuthor(`${rows.length}개 공급 주체 → ${value}`);
  if (author === null) return;                       // 취소 — 한 행도 안 고친다
  // hotfix75 — 행마다 PATCH 를 보내던 것을 요청 하나로 (`rows_edit` — 서버는 행마다 PATCH 와 같은 함수).
  const todo = rows.filter(r => String(cellValue(r, "scope") || "") !== value);
  const out = await editRowsBulk(todo, "scope", () => value, author);
  if (!out) return;
  updateBadge();
  renderGrid();
  markMultiRows();
  drawOverlay();          // 색은 `itemScope` 하나가 정한다 — 여기서는 다시 그릴 뿐
  editNotice(`${rows.length - out.missing.length}개 행의 공급 주체를 ${value} 로 바꿨습니다`);
  showMultiScope();
}

/* hotfix75 — 여러 행의 같은 칸을 **요청 하나**로 저장하고 행 객체를 PATCH 뒤와 똑같이 고친다 (`row.user` · 고친
 * 사람 · `values` · 충돌 풀기 · 검토 수 · 이력 수).  다시 그리는 일은 부른 쪽이 한 번 한다 — 행마다 그리면 그것이
 * 다시 느려진다.  `valueOf(row)` 는 그 행에 적을 값 (빈 값이면 도면 값으로 되돌린다).  실패면 null. */
async function editRowsBulk(rows, field, valueOf, author, reasonOf) {
  const out = { missing: [] };
  if (!rows.length) return out;
  let res;
  try {
    res = await fetch(`/jobs/${S.job.id}/rows_edit`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ field, author, items: rows.map(r => ({ key: r.key, value: valueOf(r),
                                                                    reason: reasonOf ? reasonOf(r) : undefined })) }),
    });
  } catch (e) {
    alert("저장하지 못했습니다 — 서버에 연결할 수 없습니다.  한 행도 바뀌지 않았습니다."); return null;
  }
  if (!res.ok) {
    let msg = "저장 실패 (서버 응답 " + res.status + ")";
    try { msg = (await res.json()).detail || msg; } catch (e) { /* 본문이 JSON 이 아니다 */ }
    alert(msg); return null;
  }
  const got = await res.json();
  for (const r of rows) {
    if (!(r.key in got.users)) continue;
    const v = String(valueOf(r) ?? "").trim();
    r.user = got.users[r.key];
    stampEditor(r, field, author);
    r.values[field] = v === "" ? (r.ai || {})[field] : (field === "qty" ? Number(v) : v);
    delete (r.conflict || {})[field];
  }
  S.counts.REVIEW = got.review_count;
  if (got.feedback_count !== undefined) S.feedback = got.feedback_count;
  out.missing = got.missing || [];
  if (out.missing.length) alert(`${out.missing.length}개 행은 서버에 없어 바꾸지 못했습니다 — 다른 창이나 다른 사람이 지웠을 수 있습니다.`);
  return out;
}

function bindAxisActions(row) {
  document.querySelectorAll("#evidence button.ract-b").forEach(b => {
    b.onclick = async () => {
      const field = b.dataset.act === "scope" ? "vendor_supply" : "qty";
      await fetch(`/jobs/${S.job.id}/rows/${row.key}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value: b.dataset.v }),
      });
      await reloadKeys([row.key]);
      const again = S.rows.find(r => r.key === row.key);
      if (again) showEvidence(again);
    };
  });
}

/* hotfix69 — 목록은 근거 칸 셋(후보 · 경로 · 판정축 — 서버 `SLIM_DROP`)을 빼고 받는다 (`_slim`).  그 셋은 고른
 * 행 하나에만 쓰이므로, 근거 패널을 열 때 그 행만 온전히 받아 같은 행 객체에 채우고 패널 · 경로 선을 다시
 * 그린다.  같은 행을 두 번 받지 않는다. */
const _fullP = new Map();
function ensureFull(row) {
  if (!row || !row._slim || !S.job) return Promise.resolve(row);
  if (_fullP.has(row.key)) return _fullP.get(row.key);
  const job = S.job.id;
  const p = fetch(`/jobs/${job}/rows?tab=ALL&keys=${encodeURIComponent(row.key)}`)
    .then(r => r.json())
    .then(list => {
      const full = Array.isArray(list) && list[0];
      if (full && S.job && S.job.id === job && row._slim) { row.evidence = full.evidence || {}; delete row._slim; }
      return row;
    })
    .catch(() => row)
    .finally(() => _fullP.delete(row.key));
  _fullP.set(row.key, p);
  return p;
}

function showEvidence(row) {
  if (row && row._slim) {
    ensureFull(row).then(r => {
      if (!r._slim && S.sel === r.key && !(S.multi && S.multi.size)) { showEvidence(r); drawOverlay(); }
    });
  }
  // 삭제 후보는 이번 리비전에 심볼이 없는 행이다.  근거 패널이 보여야 하는 것은
  // 검출 근거가 아니라 **왜 짝을 못 찾았는가** 이고, 그것이 사람이 '검출 실패'
  // 와 '실제 삭제' 를 가르는 재료다.
  if (row.delCand) { showDeletedEvidence(row.delCand); return; }
  const e = row.evidence || {};
  const pairs = [];
  const add = (k, v) => { if (v !== undefined && v !== null && v !== "") pairs.push([k, v]); };
  // hotfix26 — 구획 머리글.  25항목이 한 줄로 흘러 어디가 수량이고 어디가 Description 인지
  // 눈으로 갈라야 했다.  값을 바꾸지 않고 사이에 제목만 둔다.
  const sec = (t) => pairs.push(["§" + t, "§"]);
  const hits = e.rules_hit || [];
  // hotfix38 — 개정 근거를 맨 위에.  추가는 왜 추가인지(태그가 장부에 없었다 /
  // 반경 안에 기록이 없었다), 수정은 어느 칸이 어떻게 바뀌었는지, 짝은 태그로
  // 지었는지 기하로 지었는지.  값은 `row.rev` 하나에서 온다.
  const rv = row.rev || {};
  if (rv.state === "NOT_COMPARED") {
    // hotfix46 — 대조하지 않은 행.  추가도 삭제도 아니고 왜 대조하지 않았는지만 말한다.
    sec("개정");
    add("개정 상태", `대조 안 함 — ${(S.rev || {}).compared_with || "직전 리비전"} 대비 · ${rv.reason || "태그 없음"}`);
  } else if (rv.state && rv.state !== "BASELINE" && rv.state !== "UNCHANGED") {
    sec("개정");
    const vs = (S.rev || {}).compared_with || "직전 리비전";
    add("개정 상태", `${revLabel(row)} — ${vs} 대비` + (rv.id ? ` · 안정 ID ${rv.id}` : ""));
    if (rv.sheet_renumbered_from) add("도면번호 바뀐 장", `${rv.sheet_renumbered_from} → 이 장 (태그로 같은 장임을 확인)`);
    if (rv.reason) add(rv.state === "ADDED" ? "추가 근거" : "근거", rv.reason);
    if (rv.state === "MODIFIED" && rv.basis === "AMBIGUOUS") {
      // hotfix47 — 짝 없이 변경으로만 표기한 행.  전 → 후를 지어내지 않는다.
      add("짝 근거", "없음 — 같은 도면에 새 태그와 사라진 태그가 함께 있어 태그 변경인지 추가인지 도면이 가르지 않음 (위치로는 비교하지 않음)");
    } else if (rv.state === "MODIFIED") {
      add("짝 근거", rv.basis === "TAG" ? "같은 태그 (거리와 무관)"
        : rv.basis === "TYPE" ? "같은 도면의 유일한 같은 TYPE 끼리 (태그가 바뀐 한 항목 · 위치는 보지 않음)"
        : `같은 TYPE · 반경 안 최근접 (${rv.moved_pt ?? 0}pt 이동) — hotfix46 이전 대조 (위치로는 더 비교하지 않습니다 · '대조 다시')`);
      add("바뀐 태그", (rv.changed || []).map(c =>
        `${c.field === "tag_no" ? "태그" : c.field}: ${c.was || "(없음)"} → ${c.now || "(없음)"}`).join(" · ") || "(기록 없음)");
    }
    // hotfix43 — 상태를 정하지 않은 값 차이는 참고로만 보인다
    if ((rv.field_diffs || []).length) {
      add("값이 다른 칸 (개정 판정에는 쓰지 않음)", rv.field_diffs.map(c =>
        `${c.field}: ${c.was ?? "(빈칸)"} → ${c.now ?? "(빈칸)"}`).join(" · "));
    }
  } else if (rv.state === "UNCHANGED" && rv.basis) {
    sec("개정");
    add("개정 상태", `변경 없음 — ${(S.rev || {}).compared_with || "직전 리비전"} 대비`
      + ` · 짝 ${rv.basis === "TAG" ? "태그" : "기하"}` + (rv.id ? ` · 안정 ID ${rv.id}` : "")
      + ((rv.moved_pt || 0) > 0 ? ` · ${rv.moved_pt}pt 이동 (자리 이동은 수정이 아님)` : ""));
    if (rv.sheet_renumbered_from) add("도면번호 바뀐 장", `${rv.sheet_renumbered_from} → 이 장 (태그로 같은 장임을 확인)`);
    if ((rv.field_diffs || []).length) {
      add("값이 다른 칸 (개정 판정에는 쓰지 않음)", rv.field_diffs.map(c =>
        `${c.field}: ${c.was ?? "(빈칸)"} → ${c.now ?? "(빈칸)"}`).join(" · "));
    }
  }
  sec("공급 · 수량");

  /* 편집값과 엔진 근거를 **구분해서** 말한다 (13회차).
   *
   * 13회차 조사가 잡은 것: 한 행을 고치고 나면 패널이 `수량 7`(편집값)과
   * `수량 근거 1 symbol x 2`(엔진 근거)를 나란히 놓고 둘을 구분하지 않아
   * 서로 모순되게 읽혔다.  12회차가 스코프 축에서 고친 것과 같은 종류다.
   * 값을 바꾸지 않고 **어디서 온 값인지**를 붙인다. */
  const wasEdited = f => !!(row.user && f in row.user);
  const mark = (f, v) => wasEdited(f)
    ? `${v}  ✎ ${(editorOf(row, f) || {}).author || "사람"} 고침 (도면 근거는 ${
        row.ai && row.ai[f] !== undefined && row.ai[f] !== null && row.ai[f] !== ""
          ? row.ai[f] : "비어 있음"})`
    : v;

  // --- scope: who supplies it, and where the row does and does not go -------
  //
  // 두 질문을 **나눠서** 말한다 (12회차).  11회차부터 발주처 양식은
  // SCOPE=SCT 만 담으므로, 한 문장으로 "리스트에 포함됩니다" 라고 하면
  // 화면에는 있고 Excel 에는 없는 행이 거짓말을 하게 된다 — 11회차 캡처가
  // 실제로 그것을 잡았다.
  //
  //   추출 결과   1029행 기준.  삭제 표시된 행만 빠진다
  //   발주처 양식  SCOPE=SCT 기준.  값이 없으면 "판정한 적 없음"이다
  //
  // 문구는 그 행의 실제 SCOPE 값에서 만든다.  고정 문자열이 아니다.
  // 판정은 `scopeFacts` 하나에서 온다 — 편집 안내도 같은 함수를 읽는다(14회차).
  const facts = scopeFacts(row.values.scope, { needsReview: row.needs_review,
                                               manualBlank: !!(row.added && e.markup) });
  add("공급 주체", mark("scope", facts.supplierName));
  // hotfix27 — 맞닿은 스위치 묶음(물리 LS 1개)은 **어느 신호 버블의 별표든** 따른다.
  // 이 행(맨 위 버블)에 별표가 없어도 VENDOR 인 까닭을 적는다.
  if (e.bundle_scope && e.bundle_scope.anchor) {
    const bs = e.bundle_scope;
    add("묶음 별표", `물리 기기 1개의 신호 ${(bs.marked_members || []).join(" · ")} 에 별표 — `
      + `묶음 전체가 ${bs.scope} 를 따릅니다`
      + (bs.own_scope && bs.own_scope !== bs.scope ? ` (이 버블만 보면 ${bs.own_scope})` : "")
      + (bs.disagree ? ` · ⚠ 신호마다 다른 별표 (${bs.disagree.join(", ")})` : ""));
  }
  add("추출 결과", row.removed ? "이 행은 결과에서 빠졌습니다"
                              : "이 행은 추출 결과에 있습니다");
  add("발주처 양식", row.removed ? "빠집니다 (결과에서 빠진 행)" : facts.formLine);
  // 44회차 — 사용자 마크업.  어느 칸이 도면 값이고 어느 칸이 사람 값인지,
  // 그리고 제안 때 도면이 무엇을 말했는지를 그대로 적는다.
  const mk = e.markup;
  if (row.added) {
    add("사용자 추가", mk
      ? `${mk.author || "이름 없음"} (자칭) · ${mk.at ? new Date(mk.at * 1000).toLocaleString("ko-KR") : ""}`
        + ` · 사유 ${mk.class || ""}${mk.note ? ` · ${mk.note}` : ""}`
      : "＋행 으로 만든 행 (사각형 없음)");
    if (mk) {
      const pr = mk.proposal || {};
      add("SCOPE 출처", mk.scope_source === "DRAWING"
        ? `도면 (별표·NOTES 를 읽음${pr.scope_evidence && pr.scope_evidence.text ? ` — ${pr.scope_evidence.text}` : ""})`
        : `사람 값${pr.scope_source === "DRAWING" ? ` (도면 제안 ${pr.scope} 을 바꿈)` : " (도면에서 못 읽음)"}`);
      add("수량 출처", mk.qty_source === "DRAWING"
        ? `도면 — ${pr.qty_basis || ""}`
        : `사람 값 (${pr.qty_basis || "도면에서 못 읽음"})`);
      add("안정 ID", mk.stable_id || "없음 — 프로젝트에 묶이지 않은 분석");
      if (pr.anchor) add("Type 제안", `사각형 안 낱말 ${pr.anchor}`);
    }
  }
  if (row.reject && Object.keys(row.reject).length) {
    add("오검출 표시", `${row.reject.class || ""}${row.reject.note ? ` · ${row.reject.note}` : ""} — `
      + `${row.reject.author || "이름 없음"} (자칭)`
      + (row.reject.at ? ` · ${new Date(row.reject.at * 1000).toLocaleString("ko-KR")}` : "")
      + (row.removed ? " · Excel 제외" : " · Excel 유지"));
  }
  add("적용 규칙", hits.length ? hits.join(", ") : "제외 규칙 해당 없음");
  add("제외 사유", e.excluded_by);
  // The NOTES line that defined this drawing's vendor mark, verbatim.  Quoted,
  // not interpreted: the tool matches the mark, the reader reads the sentence.
  add("NOTES 원문", (e.notes_text || []).map(t => `“${t}”`).join(" / "));

  // --- quantity -------------------------------------------------------------
  add("수량", mark("qty", row.values.qty));
  add("수량 근거", e.qty_basis);
  // hotfix25 — 격막 씰은 Remark 의 글자와 도면의 청록 상자가 **같은 값**을 말한다.
  if (e.diaphragm_seal && Array.isArray(e.diaphragm_seal.rects)) {
    add("Diaphragm Seal", `임펄스 라인에 격막 씰 ${e.diaphragm_seal.rects.length}개 — `
      + `도면의 청록 상자 · Remark 에 "${e.diaphragm_seal.remark || "Diaphragm Seal"}"`);
  }
  add("승수 출처", e.qty_source);

  // --- classification -------------------------------------------------------
  sec("검출 · 위치");
  add("앵커", e.anchor);
  add("Type 판정", row.values.type
    && mark("type", `${row.values.type}${e.anchor ? ` ← 앵커 ${e.anchor}` : ""}`));
  add("Body 판정", e.body && `${e.body} — ${JSON.stringify(e.body_basis || {})}`);
  add("개폐 상태", e.state);
  add("액추에이터", e.actuator);
  add("액추에이터 근거", e.actuator_basis);
  // `evidence.tag` 는 밸브에 붙은 버블 글자(MOV/HOV — 문자열)다.  33회차 이전
  // 분석은 1급 태그 판정을 같은 열쇠에 dict 로 넣어 두었으므로 그것도 받는다.
  add("태그 버블", typeof e.tag === "string" ? e.tag : undefined);
  // hotfix39 — 태그 교차 검증 · 태그가 증거인 행.  값은 엔진이 적은 사실 그대로다.
  if (e.tag_check) {
    add("태그 교차 검증", `기능코드 ${e.tag_check.code} 는 이 도면에서 ${e.tag_check.expected} `
      + `(${e.tag_check.n}/${e.tag_check.of}행)인데 버블 글자는 ${e.tag_check.seen} — 도면이 두 말을 합니다`);
  }
  if (e.tag_evidence) {
    add("태그가 증거", `${(e.tag_evidence.words || []).join(" · ")} — ${e.tag_evidence.why || ""}`
      + (e.tag_evidence.code ? ` · 기능코드 ${e.tag_evidence.code}` : "")
      + (e.tag_evidence.qty_from ? " · 수량은 같은 장 행의 값" : " · 수량 미정") + " · 공급 주체 미판정");
  }
  const tagNo = e.tag_no || (e.tag && typeof e.tag === "object" ? e.tag : null);
  if (tagNo && tagNo.value) {
    add("Tag No. 근거", `${tagNo.value} — 도면 인쇄 (모양 ${tagNo.shape || ""})`);
    add("Tag No. 규칙", tagNo.rule);
  }
  // hotfix36 — 탭한 배관의 라인 번호 깃발.  뜻은 안 읽고 글자 그대로 (spec 은 런 건너편 글줄).
  if (e.line && e.line.line_no) {
    add("Line No. 근거", `${e.line.line_no} — 도면 깃발 라벨 (사각형 안)` + (e.line.pipe_no ? ` · 배관 번호 ${e.line.pipe_no}` : "")
      + (e.line.spec ? ` · 건너편 ${e.line.spec}` : "")
      + (e.line.candidates > 1 ? ` · 같은 런에 라벨 ${e.line.candidates}개 (가장 가까운 것)` : ""));
    if (e.line.size) {
      // hotfix37 — 형식의 출처를 그대로 말한다: 보온 글자는 범례 글줄, 직경 접두는 범례 예시가 글자면 범례,
      // 획이면(QFE) 본문 깃발 다수.  둘 다 없으면 구조만으로 가른 것이라 그렇게 적는다.
      const f = e.line.format || {};
      const src = f.source === "LEGEND"
        ? `범례 p${f.legend_page || "?"} 의 깃발 정의 (보온 글자)` + (f.prefix_source === "BODY" ? " · 직경 접두는 본문 깃발 다수" : f.prefix_source === "LEGEND" ? " · 직경 접두는 범례 예시" : "")
        : "범례 정의 없음 — 글자+숫자 구조로만 가름";
      add("Line Size 근거", `${e.line.size}` + (e.line.insulation ? ` · 보온 ${e.line.insulation}` : "")
        + (e.line.design_code ? ` · 설계 코드 ${e.line.design_code}` : "") + ` — ${src}`);
    }
    add("Line No. 규칙", e.line.rule);
  }
  // hotfix31 — 한 라인(같은 태그)의 표시기를 전송기로 접은 것 · 표시기만 있는 라인은 게이지.
  if (Array.isArray(e.readout_folded) && e.readout_folded.length) {
    add("접은 표시기", e.readout_folded.map(f => `${f.anchor} (${f.tag_no})`
      + (f.basis === "TAG_LOCATION" ? ` — ${f.how}` : "")).join(", ")
      + (e.readout_folded.every(f => f.basis === "TAG_LOCATION") ? "" : " — 같은 태그 한 라인이라 이 행이 우선 (사용자 규칙)"));
  }
  // hotfix73 — 버블이 도면에서 말한 것: 가운데 선(ISA 위치 표기) · 겹쳐 인쇄 · 버블 밖 이웃 라벨
  const det = e.detail || {};
  if (det.bubble_lines) {
    add("버블 가운데 선", `${det.bubble_lines}줄 — ISA 위치 표기 (뜻은 범례 GENERAL INSTRUMENTS · 선 없음 = 현장)`);
  }
  if (det.overprinted) add("겹쳐 인쇄", `같은 글자가 이 버블에 ${det.overprinted}번 찍혀 있습니다 — 한 계기로 셉니다`);
  if (Array.isArray(det.outside_labels) && det.outside_labels.length) {
    add("버블 밖 라벨", det.outside_labels.map(o => o.anchor).join(", ") + " — 버블 사각형 밖이라 이 계기의 글자로 보지 않았습니다");
  }
  if (e.gauge && e.gauge.display) {
    add("게이지", `${e.gauge.display} = ${e.gauge.word} — ${e.gauge.basis || ""}`);
  }
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
  sec("Description");
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
  sec("검토 · 편집");
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
    // 워크북에서 고른 확정은 FROM/TO 가 아니라 **문장**이 온다 (10회차).
    // 그때 "FROM  → TO " 를 찍으면 빈칸만 보이므로, 있는 것을 말한다.
    if (ov.from || ov.to) {
      add("FROM/TO 확정", `FROM ${bareName(ov.from)} → TO ${bareName(ov.to)} `
        + `(FROM ${ov.source_from} · TO ${ov.source_to})`);
    } else if (ov.sentence) {
      add("확정 문장", `${ov.sentence} (${ov.source_from}`
        + (ov.candidate ? ` · 후보${ov.candidate}` : "")
        + (ov.applies_to ? ` · ${ov.applies_to}` : "") + ")");
    }
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
    + (row.removed
       ? `<button id="ev-restore" class="mini-rep" title="지운 행을 되살립니다">되돌리기</button>`
       : `<button id="ev-delete" class="mini-rep danger" title="잘못 추출된 행 — 도면에 붉은 ✕ 로 남고 Excel 에서 빠집니다">삭제</button>`)
    + (row.added && row.rect && row.rect.length === 4
       ? `<button id="ev-elsewhere" class="mini-rep" title="같은 마크업을 다른 장에도 — 장마다 다시 읽어 제안하고 고른 장에만 넣습니다">다른 장에도…</button>`
       : "")
    + `</div>`
    + reviewControls(row) + scopeEditor(row) + axisActions(row)
    // hotfix27 — From/To 입력은 패널 **위쪽**에 둔다.  예전에는 25항목과 수정 이력 아래라
    // 1366×768 에서 매번 스크롤해 내려가야 했다.
    + descMarkupBlock(row)
    + "<dl>" + pairs.map(([k, v]) => k.startsWith("§")
      ? `<dt class="ev-sec">${escape(k.slice(1))}</dt><dd class="ev-sec"></dd>`
      : `<dt>${k}</dt><dd>${escape(String(v))}</dd>`).join("") + "</dl>"
    + `<div id="ev-hist"></div>`
    + fromToPicker(row)
    + candidatePicker(row);
  bindCandidatePicker(row);
  bindDescMarkup(row);
  bindFromToPicker(row);
  bindReviewControls(row);
  bindAxisActions(row);
  bindScopeEditor(row);
  showHistory(row);
  const evb = $("#ev-report");
  if (evb) evb.onclick = () => reportDialog({ rowKey: row.key, pageNo: row.page_no });
  const ewb = $("#ev-elsewhere");
  if (ewb) ewb.onclick = () => markupElsewhere(row);
  const edb = $("#ev-delete");
  if (edb) edb.onclick = () => deleteRows([row.key]);
  const erb = $("#ev-restore");
  if (erb) erb.onclick = () => restoreRow(row.key);
}

/* 누가 · 언제 · 무엇에서 무엇으로 (13회차 [D]).
 *
 * 편집 이력은 `feedback` 표에 처음부터 전부 있었고 없던 것은 **누구** 하나였다.
 * 그것을 채웠으니 이제 보인다.  이름은 자기신고이므로 화면이 그렇게 적는다 -
 * 인증된 신원인 것처럼 보이면 안 된다.  이름 없이 저장된 편집은 "이름 없음"
 * 이라고 쓰고, 없는 이름을 지어내지 않는다. */
async function showHistory(row) {
  const box = $("#ev-hist");
  if (!box) return;
  let hist = [];
  try {
    const r = await fetch(`/jobs/${S.job.id}/rows/${row.key}/history`);
    if (r.ok) hist = (await r.json()).history || [];
  } catch (e) { return; }
  if (!hist.length) { box.innerHTML = ""; return; }
  // 패널을 다시 그리는 사이에 응답이 오면 엉뚱한 행에 붙는다.
  if (S.sel !== row.key) return;
  box.innerHTML = `<p class="muted small hist-head">수정 이력 ${hist.length}건 `
    + `— 이름은 <b>자칭</b>입니다 (이 앱에는 로그인이 없습니다)</p>`
    + `<div class="hist">` + hist.map(h =>
        `<div class="hist-row">`
        + `<span class="hist-who">${escape(h.author || "이름 없음")}</span>`
        + `<span class="hist-when">${escape(whenWords(h.at))}</span>`
        + `<span class="hist-what">${escape(h.field)} : `
        + `${escape(h.from === "" ? "(비어 있음)" : h.from)} → `
        + `${escape(h.to === "" ? "(지움)" : h.to)}`
        + `${h.reason ? ` — ${escape(h.reason)}` : ""}</span></div>`).join("")
    + `</div>`;
}

/* The phrases the drawing prints along this instrument's pipe, nearest first.
 * Clicking one writes it into the Description between the system name and the
 * variable - the place the client's own lines put it - so the reviewer picks
 * rather than types. */
/* The rows this one is indistinguishable from - the reach of `일괄 적용`, shown
 * before it is pressed rather than reported after.  The 58 PARTIAL rows fall into
 * 25 such groups; drawing and Type alone would give 17 and would also sweep up
 * rows the engine had already filled. */
/* ★ 18회차 [I]: 17회차 C-1 이 이 묶음을 **1행으로 만들어 놓고 있었다.**
 * 묶음의 정의가 "지금 같은 문장" 인데, C-1 이 같은 도면 안의 중복 문장에
 * A·B·C 를 붙이면서 그 같음이 사라졌다 - UI 스위트의
 * `test_step11_bulk_apply_fills_its_group_and_nothing_else` 가 "1행보다 큰
 * PARTIAL 묶음이 없다" 로 그것을 잡았다.  12회차가 센 25묶음이 25×1 이 된 것이다.
 *
 * 그래서 **접미를 뗀 문장**으로 묶는다.  떼는 값을 지어내지 않는다 - 엔진이
 * `duplicate_suffix.sentence` 에 접미 전 원문을 그대로 남겨 두었고, 그것이
 * 지금 문장과 실제로 이어지는지(원문 + 공백 + 그 한 글자)를 확인한 뒤에만
 * 쓴다.  사람이 문장을 고쳤으면 그 확인이 깨지므로 고친 문장 그대로 묶인다. */
function baseSentence(row) {
  const text = (row.values || {}).description || "";
  const dup = ((row.evidence || {}).duplicate_suffix) || null;
  if (dup && dup.sentence && dup.letter
      && text === `${dup.sentence} ${dup.letter}`) return dup.sentence;
  return text;
}

function sameSentence(row) {
  const text = baseSentence(row);
  return S.rows.filter(r => !r.deleted && !r.removed
    && r.drawing_no === row.drawing_no && r.values.type === row.values.type
    && baseSentence(r) === text);
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

/* hotfix23 — Description From/To 마크업.
 *
 * 사용자: *"Tag 를 PID 에서 선택하거나 List 에서 선택하면 Description From 마크업을 해서 범위를
 * 지정하면 그 범위에 있는 description 을 따고, To 마크업을 누르면 똑같이 따서 Description 이
 * From-To 로 이어지도록 … 하나만 마크업하더라도 그 Description 이 나타나면 된다."*
 *
 * 엔진이 라인을 타고 쓴 문장은 그대로 두고(현행 기준), 사람이 범위를 그으면 **그 범위 안에
 * 도면이 인쇄한 글자**를 서버가 읽어(`POST /jobs/{id}/axis_text`) 6회차 확정 경로
 * (`POST …/axis`, via=markup)로 문장을 쓴다.  문형은 엔진 ② · ②a · ②b 와 같다.
 * 목적은 *"어떤 system, line 의 계기인지 식별"* 이므로 읽은 글자를 다듬지 않는다 —
 * 도면번호 · NOTE · 치수 줄만 뺀다 (뺀 줄은 화면에 적는다). */
S.ftPending = S.ftPending || {};
S.ftMark = null;

/* 출처 문자열 → 이 쪽 값을 어디서 얻었나.  장부 값을 그대로 두면 `keep` 이라 서버가 옛 출처를
 * 잇는다 (후보선택 값을 한 번도 안 건드렸는데 "직접 입력" 으로 바뀌지 않게). */
function _ftState(row) {
  if (!S.ftPending[row.key]) {
    const ov = (S.axisOv || {})[row.key];
    S.ftPending[row.key] = ov
      ? { from: bareName(ov.from), to: bareName(ov.to),
          from_rect: ov.from_rect || null, to_rect: ov.to_rect || null,
          from_via: ov.from ? "keep" : "", to_via: ov.to ? "keep" : "" }
      : { from: "", to: "", from_via: "", to_via: "" };
  }
  return S.ftPending[row.key];
}

/* hotfix27 — **가볍게 · 직접 입력도.**
 *
 * 사용자: *"From/To 마크업 너무 무겁고 오래 걸린다 가볍게해줘.  그리고 마크업하지 않고 사용자가
 * From To 를 입력할 수 있도록도 해줘"*.  TC2 실측(spike/ui_time_fromto.py · out/hotfix27):
 *   · 한 쪽마다 세 번 눌렀다 (버튼 · 끌기 · 이름 확인) — 이름 줄이 매번 떴다
 *   · 확인 → Description 바뀜 1.1~1.4초 인데 서버 저장은 0.11초였다.  나머지는 화면이
 *     **목록 전부(902행) · 도면 오버레이 전부 · 근거 패널 전부**를 다시 그리고 수정 이력까지
 *     다시 받던 것이다
 *   · 버튼을 누르는 것만으로도 근거 패널 전부를 다시 그렸다
 * 그래서: 칸은 **입력칸**이고(그으면 읽은 글자가 칸에 들어가고, 쳐도 된다), 작성자는 이 판 안에
 * 늘 보이는 칸이며(비어 있을 때만 이름 줄을 띄운다 — 이름을 지어내지 않는다), 저장 뒤에는
 * **그 행의 두 칸 · 이 판 · 범위 상자**만 고친다. */
function descMarkupBlock(row) {
  if (row.removed) return "";
  const st = _ftState(row);
  const cur = (S.ftMark && S.ftMark.key === row.key) ? S.ftMark.side : "";
  const side = (k, label) => `
      <div class="dm-row">
        <label for="dm-${k}-in">${label}</label>
        <input id="dm-${k}-in" type="text" value="${escape(st[k] || "")}"
               placeholder="${label} — 직접 입력하거나 범위를 그으세요" autocomplete="off">
        <button id="dm-${k}" class="ghost${cur === k ? " on" : ""}" aria-pressed="${cur === k}"
                title="도면에서 끌어 범위를 그으면 그 안의 글자를 읽어 넣고 바로 적용합니다">범위</button>
      </div>`;
  return `<div class="cands" id="descmk">
      <h4>Description From/To <span class="muted">— 직접 입력하거나 도면에서 범위를 그으세요 · 하나만 있어도 됩니다</span></h4>
      ${side("from", "From")}
      ${side("to", "To")}
      <div class="dm-row dm-foot">
        <label for="dm-who">작성자</label>
        <input id="dm-who" type="text" value="${escape(S.ftWho ?? lastAuthor())}" placeholder="이름 (자칭)" autocomplete="off">
        <button id="dm-apply" class="ghost" title="입력한 From/To 로 Description 을 씁니다 (Enter)">적용</button>
        ${(st.from || st.to) ? `<button id="dm-clear" class="ghost" title="From/To 를 지우고 엔진 문장으로 되돌립니다">지우기</button>` : ""}
      </div>
      <p class="muted" id="dm-note">${cur ? `도면에서 ${cur === "from" ? "From" : "To"} 범위를 끌어 지정하세요 — Esc 취소` : ""}</p>
    </div>`;
}

/* 이 판만 다시 그린다 — 근거 패널 전부를 다시 그리면 수정 이력·후보를 다시 받는다. */
function refreshDescMarkup(row) {
  const old = document.querySelector("#descmk");
  if (!old || S.sel !== row.key) return;
  const tmp = document.createElement("div");
  tmp.innerHTML = descMarkupBlock(row);
  const nu = tmp.firstElementChild;
  if (nu) { old.replaceWith(nu); bindDescMarkup(row); }
}

/* 작성자 — 판 안의 칸이 채워져 있으면 그 이름으로, 비어 있으면 이름 줄을 띄운다. */
async function _ftAuthor(what, hint) {
  if (EMBED.user) { S.ftWho = EMBED.user; return EMBED.user; }   // hotfix66 — 대시보드 로그인 이름이 이긴다
  const box = document.querySelector("#dm-who");
  const v = box ? box.value.trim() : "";
  if (v) { rememberAuthor(v); S.ftWho = v; return v; }
  const who = await askAuthor(what, hint);
  if (who) S.ftWho = who;          // 이름 줄에 적은 이름이 판의 칸에도 들어간다
  return who;
}

function bindDescMarkup(row) {
  const box = document.querySelector("#descmk");
  if (!box) return;
  const st = _ftState(row);
  const arm = side => {
    if (S.markup) setMarkup(false);
    S.ftMark = (S.ftMark && S.ftMark.key === row.key && S.ftMark.side === side) ? null
      : { key: row.key, side };
    $("#stage").classList.toggle("markup", !!S.ftMark);
    refreshDescMarkup(row);
  };
  box.querySelector("#dm-from").onclick = () => arm("from");
  box.querySelector("#dm-to").onclick = () => arm("to");
  for (const k of ["from", "to"]) {
    const inp = box.querySelector(`#dm-${k}-in`);
    // 친 글자는 그은 범위의 글자가 아니다 — 범위 상자를 걷고 출처를 "직접 입력" 으로.
    inp.oninput = () => { st[k] = inp.value.trim(); st[`${k}_via`] = "manual"; st[`${k}_rect`] = null; };
    inp.onkeydown = ev => { if (ev.key === "Enter") { ev.preventDefault(); applyTyped(); } };
  }
  const applyTyped = async () => {
    if (!st.from && !st.to) { editNotice("From 이나 To 중 하나는 적어야 합니다 — 지우려면 [지우기]", "out"); return; }
    const who = await _ftAuthor("Description From/To");
    if (who === null) return;
    await _ftSave(row, who);
  };
  box.querySelector("#dm-apply").onclick = applyTyped;
  // 판을 다시 그려도 친 이름이 남는다 (저장할 때 브라우저가 기억한다).
  box.querySelector("#dm-who").oninput = ev => { S.ftWho = ev.target.value; };
  box.querySelector("#dm-who").onkeydown = ev => {
    if (ev.key === "Enter") { ev.preventDefault(); applyTyped(); }
  };
  const clr = box.querySelector("#dm-clear");
  if (clr) clr.onclick = async () => {
    const who = await _ftAuthor("Description From/To 지우기");
    if (who === null) return;
    S.ftPending[row.key] = { from: "", to: "", from_via: "", to_via: "" };
    await _ftSave(row, who);
  };
}

function endFtMark() {
  if (!S.ftMark) return;
  S.ftMark = null;
  $("#stage").classList.remove("markup");
}
document.addEventListener("keydown", ev => {
  if (ev.key === "Escape" && S.ftMark) {
    const row = S.rows.find(r => r.key === S.ftMark.key);
    endFtMark();
    if (row) refreshDescMarkup(row);
  }
});

/* 목록에서 그 행의 Description · 등급 두 칸만 고친다 (목록 전부를 다시 그리지 않는다). */
function _paintDescCells(row) {
  const tr = document.querySelector(`#body tr[data-key="${CSS.escape(row.key)}"]`);
  if (!tr) return;
  const cols = COLS.filter(([key]) => key !== "origin" || S.showOrigin);
  cols.forEach(([key], i) => {
    if (key !== "description" && key !== "description_grade") return;
    const td = tr.children[i];
    if (!td) return;
    const val = row.values[key] ?? "";
    if (key === "description_grade") {
      td.innerHTML = "";
      if (val) {
        const g = GRADES.find(x => x[0] === val);
        const b = document.createElement("span");
        b.className = `gradge g-${val}`;
        b.innerHTML = `<i class="gm">${GRADE_MARK[val] || "·"}</i><span>${escape(g ? g[1] : val)}</span>`;
        b.title = g ? g[2] : val;
        td.appendChild(b);
      }
    } else {
      td.textContent = val;
    }
    td.title = val ? String(val) : "";
    td.classList.toggle("edited", !!(row.user && key in row.user));
  });
  repaintRow(row);
}

/* 범위 상자만 다시 그린다 — 오버레이 전부(수백 상자)를 다시 만들지 않는다. */
function _redrawFromTo() {
  const ov = $("#ov");
  if (!ov || !S.page || !S.natural) return;
  ov.querySelectorAll("rect.ftbox, text.ftlabel").forEach(n => n.remove());
  drawFromTo(ov, S.natural.w / (S.page.width || 1));
}

async function _ftSave(row, author) {
  const st = _ftState(row);
  const res = await fetch(`/jobs/${S.job.id}/rows/${row.key}/axis`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from_text: st.from, to_text: st.to, via: "markup", author,
                           via_from: st.from_via || "manual", via_to: st.to_via || "manual",
                           from_rect: st.from_rect || null, to_rect: st.to_rect || null }),
  });
  if (!res.ok) { alert((await res.json()).detail || "저장 실패"); return null; }
  const out = await res.json();
  row.user = row.user || {};
  if (out.cleared) {
    delete row.user.description; delete row.user.description_grade;
    const eng = (row.ai || {}).description;
    if (eng !== undefined) row.values.description = eng;
    const engG = (row.ai || {}).description_grade;
    if (engG !== undefined) row.values.description_grade = engG;
    delete (S.axisOv || {})[row.key];
    editNotice("From/To 를 지웠습니다 — 엔진 문장으로 돌아갑니다", "in");
  } else {
    row.user.description = out.sentence; row.user.description_grade = "USER_ENTERED";
    row.values.description = out.sentence; row.values.description_grade = "USER_ENTERED";
    if (out.saved_to_project) {
      S.axisOv = S.axisOv || {};
      S.axisOv[row.key] = { from: st.from, to: st.to, source_from: out.source_from,
                            source_to: out.source_to, stable_id: out.stable_id, inherited: false,
                            from_rect: st.from_rect || null, to_rect: st.to_rect || null };
    }
    // 저장된 값은 이제 장부의 값이다 — 다음 저장에서 안 건드린 쪽은 출처를 잇는다.
    if (st.from) st.from_via = st.from_via === "markup" ? "markup" : "keep";
    if (st.to) st.to_via = st.to_via === "markup" ? "markup" : "keep";
    editNotice(`Description — “${out.sentence}”`, "in");
  }
  if (out.review_count !== undefined) { S.counts.REVIEW = out.review_count; updateBadge(); }
  _paintDescCells(row);
  _redrawFromTo();          // hotfix25 — 그은 From/To 범위가 도면에 남는다
  if (S.sel === row.key) {
    refreshDescMarkup(row);
    showHistory(row);       // 이력 한 줄이 늘었다 — 이것만 다시 받는다
  }
  return out;
}

async function descMarkupEnd(rect) {
  const mk = S.ftMark;
  const row = mk && S.rows.find(r => r.key === mk.key);
  endFtMark();
  if (!row) return;
  // hotfix25 — 범위는 **그 행의 장**에서만.  다른 장의 글자를 이 계기의 Description 으로
  // 쓰면 도면이 말하지 않은 것을 적는 것이다 (§2.1 ③).
  if (row.page_no !== S.page.page_no) {
    editNotice(`이 행은 p${row.page_no} 의 계기입니다 — 그 장에서 범위를 그으세요 (지금 p${S.page.page_no})`, "out");
    refreshDescMarkup(row);
    return;
  }
  const res = await fetch(`/jobs/${S.job.id}/axis_text`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ page_no: S.page.page_no, rect }),
  });
  if (!res.ok) { alert((await res.json()).detail || "글자를 읽지 못했습니다"); refreshDescMarkup(row); return; }
  const got = await res.json();
  if (!got.text) {
    editNotice("그은 범위 안에 읽을 글자가 없습니다" + ((got.dropped || []).length
      ? ` (도면번호·주석 줄 ${got.dropped.length}개는 뺐습니다)` : ""), "out");
    refreshDescMarkup(row);
    return;
  }
  const st = _ftState(row);
  st[mk.side] = got.text;
  st[`${mk.side}_via`] = "markup";
  st[`${mk.side}_rect`] = [S.page.page_no, ...rect.map(v => Math.round(v * 10) / 10)];
  refreshDescMarkup(row);   // 읽은 글자가 칸에 먼저 보인다
  const who = await _ftAuthor(`Description ${mk.side === "from" ? "From" : "To"}`,
                              `읽은 글자: ${got.text}`);
  if (who === null) return;   // 칸에 남아 있다 — [적용] 으로 다시 저장할 수 있다
  await _ftSave(row, who);
}

/* hotfix25 — 사람이 그은 From/To 범위를 **고른 행에서** 도면에 다시 그린다.
 * 값은 이 세션의 `S.ftPending` 이 먼저이고, 없으면 프로젝트 장부(`S.axisOv`)다 —
 * 장부에 적히므로 다음에 열어도, 다음 리비전에서도 어느 범위를 읽었는지 보인다.
 * 범위는 `[장, x0, y0, x1, y1]` 이라 다른 장의 범위는 그리지 않는다. */
function ftRects(row) {
  const st = (S.ftPending || {})[row.key] || {};
  const ov = (S.axisOv || {})[row.key] || {};
  return [["from", st.from_rect || ov.from_rect], ["to", st.to_rect || ov.to_rect]]
    .filter(([, r]) => Array.isArray(r) && r.length === 5 && r[0] === S.page.page_no);
}

function drawFromTo(ov, scale) {
  const row = S.sel && S.rowByKey[S.sel];
  if (!row || !S.page) return;
  const ns = "http://www.w3.org/2000/svg";
  for (const [side, r] of ftRects(row)) {
    const [, x0, y0, x1, y1] = r;
    const b = document.createElementNS(ns, "rect");
    b.setAttribute("x", x0 * scale); b.setAttribute("y", y0 * scale);
    b.setAttribute("width", Math.max(2, (x1 - x0) * scale));
    b.setAttribute("height", Math.max(2, (y1 - y0) * scale));
    b.setAttribute("class", `ftbox ${side}`);
    const t = document.createElementNS(ns, "text");
    t.setAttribute("x", x0 * scale); t.setAttribute("y", y0 * scale - 3);
    t.setAttribute("class", `ftlabel ${side}`);
    t.textContent = side === "from" ? "Description From" : "Description To";
    ov.appendChild(b); ov.appendChild(t);
  }
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
// hotfix74 — 따옴표도 바꾼다.  이 함수의 결과가 `title="…"` 같은 속성 안에도 들어가는데, 따옴표를 두면 사람이 적은
// 이름·메모가 속성을 깨고 처리기를 심었다 (spike/ui_xss.py: 첫 화면 리비전 줄의 저장자 이름 → onmouseover).
const escape = (s) => s.replace(/[<>&"']/g, c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[c]));

/* ---------------- hotfix63 — 장별 메모 ----------------
 *
 * 도면 아래 메모장.  열쇠는 **도면번호**(서버 `sheet_memo.key_of`)라 같은 프로젝트의 다른 Rev 에서도 같은 장의
 * 메모가 이력과 함께 보인다.  저장 한 번이 판 하나이고 지우지 않는다 (비워서 저장해도 앞 판은 남는다).
 * 저장 안 한 글은 장을 옮겨도 이 화면이 들고 있다가(`S.memoDraft`) 그 장으로 돌아오면 되살린다. */
const MEMO_KEY = "pid.memo";            // { open: bool, h: px } — 이 브라우저의 펼침·높이만
function _memoPref() { try { return JSON.parse(localStorage.getItem(MEMO_KEY) || "{}") || {}; } catch (e) { return {}; } }
function _memoPrefSave(v) { try { localStorage.setItem(MEMO_KEY, JSON.stringify(v)); } catch (e) {} }
function memoLayout() {
  const box = $("#memo"), lf = $("#left");
  if (!box || !lf) return;
  const pref = _memoPref();
  const open = !box.classList.contains("folded");
  box.style.height = open ? `${Math.round(pref.h || 240)}px` : "";
  $("#memo-toggle").setAttribute("aria-expanded", open ? "true" : "false");
  $("#gutter-n").classList.toggle("hidden", !open);
  lf.style.setProperty("--memo-h", `${box.offsetHeight + (open ? 6 : 0)}px`);
}
function memoOpen(open) {
  const box = $("#memo");
  if (!box || !S.job) return;
  if (open === !box.classList.contains("folded")) return;
  box.classList.toggle("folded", !open);
  _memoPrefSave({ ..._memoPref(), open });
  memoLayout();
  window.dispatchEvent(new Event("resize"));
  if (open && S.memoPage) $("#memo-text").focus({ preventScroll: true });
}
async function loadMemoSummary() {
  if (!S.job) return;
  try { S.memo = await (await fetch(`/jobs/${S.job.id}/memo`)).json(); } catch (e) { S.memo = null; return; }
  const keep = S.page && S.page.page_no;
  buildPageSelect();
  if (keep) $("#page-select").value = keep;
}
function memoWhen(e) {
  const who = e.author ? escape(e.author) : `<span class="muted">이름 없음</span>`;
  const here = S.job && e.job_id === S.job.id;
  const rev = e.revision ? `<span class="rv-tag mini">${escape(e.revision)}</span>` : "";
  return `${rev}${here ? "" : ` <span class="memo-other" title="다른 리비전의 분석에서 적은 메모">다른 Rev 에서</span>`}`
    + ` <b>${who}</b> · ${escape(whenWords(e.at))}`
    + (e.key && S.memoView && e.key !== S.memoView.key ? ` · <span class="muted" title="도면번호가 바뀐 장 — 옛 번호로 적은 메모">옛 번호 ${escape(e.key)}</span>` : "");
}
function renderMemo() {
  const v = S.memoView, pg = S.memoPage;
  if (!v) return;
  const cur = v.current;
  const draft = S.memoDraft && S.memoDraft[pg];
  const ta = $("#memo-text");
  ta.value = draft != null ? draft : (cur ? cur.text : "");
  $("#memo-count").textContent = v.history.length ? `${v.history.length}` : "";
  $("#memo-count").classList.toggle("hidden", !v.history.length);
  const where = v.scope === "project"
    ? `${escape(v.drawing_no || "도면번호 없음 (이 장 번호로만)")} · 프로젝트 ${escape(v.project)} 의 모든 Rev 에서 보입니다`
    : "프로젝트에 묶이지 않은 분석 — 이 분석에서만 보입니다";
  $("#memo-sum").innerHTML = (cur && cur.text ? `지금 메모: ${memoWhen(cur)} · ` : "") + where;
  $("#memo-msg").textContent = draft != null && (!cur || draft !== cur.text) ? "저장 안 한 글이 있습니다" : "";
  $("#memo-hist-n").textContent = v.history.length ? `${v.history.length}판` : "아직 없음";
  $("#memo-list").innerHTML = v.history.map((e, i) => `<li class="memo-item${i === 0 ? " now" : ""}">`
    + `<div class="memo-meta">${i === 0 ? `<span class="memo-now">지금</span>` : ""}${memoWhen(e)}`
    + (i ? ` <button type="button" class="ghost mini memo-use" data-i="${i}" title="이 판의 글을 메모장에 불러옵니다 (저장해야 지금 메모가 됩니다)">불러오기</button>` : "")
    + `</div><div class="memo-txt">${e.text ? escape(e.text) : `<span class="muted">(비움)</span>`}</div></li>`).join("")
    || `<li class="muted small">이 장에는 아직 메모가 없습니다.</li>`;
  renderPins();
}
async function showMemo(pageNo) {
  if (!S.job) return;
  S.memoPage = pageNo;
  try {
    const v = await (await fetch(`/jobs/${S.job.id}/memo/${pageNo}`)).json();
    if (S.memoPage !== pageNo) return;        // 그 사이 다른 장으로 갔다
    S.memoView = v;
  } catch (e) { return; }
  renderMemo();
  memoLayout();
  // hotfix76 — 위치 메모는 도면 위에도 선다 (그 장의 메모를 받은 뒤에 그린다)
  if (S.page && S.page.page_no === pageNo && !drawingHidden()) drawOverlay();
  tryPinPending();
}
async function saveMemo() {
  // hotfix74 — 저장 단추를 두 번 누르거나 Ctrl+Enter 를 연달아 치면 같은 판이 두 번 쌓였다.  하나가 끝날 때까지 다음은 무시한다.
  if (S._memoBusy) return;
  S._memoBusy = true;
  try { return await _saveMemo(); } finally { S._memoBusy = false; }
}
async function _saveMemo() {
  const pg = S.memoPage, ta = $("#memo-text");
  if (!S.job || !pg) return;
  const author = await askAuthor("메모");
  if (author === null) return;
  const res = await fetch(`/jobs/${S.job.id}/memo/${pg}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: ta.value, author }) });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    $("#memo-msg").textContent = d.detail || "저장하지 못했습니다";
    return;
  }
  const v = await res.json();
  if (S.memoDraft) delete S.memoDraft[pg];
  S.memoView = v;
  renderMemo();
  $("#memo-msg").textContent = "저장했습니다 — 같은 프로젝트의 다른 Rev 에서도 보입니다";
  loadMemoSummary();
}
(function initMemo() {
  const ta = $("#memo-text");
  if (!ta) return;
  if (_memoPref().open) $("#memo").classList.remove("folded");
  $("#memo-toggle").onclick = () => memoOpen($("#memo").classList.contains("folded"));
  $("#memo-save").onclick = saveMemo;
  $("#memo-revert").onclick = () => {
    if (S.memoDraft) delete S.memoDraft[S.memoPage];
    renderMemo();
  };
  ta.addEventListener("input", () => {
    S.memoDraft = S.memoDraft || {};
    S.memoDraft[S.memoPage] = ta.value;
    const cur = S.memoView && S.memoView.current;
    $("#memo-msg").textContent = (!cur || ta.value !== cur.text) ? "저장 안 한 글이 있습니다" : "";
  });
  ta.addEventListener("keydown", ev => {
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "Enter" || ev.key === "s")) { ev.preventDefault(); saveMemo(); }
  });
  $("#memo-list").addEventListener("click", ev => {
    const b = ev.target.closest(".memo-use");
    if (!b || !S.memoView) return;
    const e = S.memoView.history[+b.dataset.i];
    if (!e) return;
    ta.value = e.text || "";
    ta.dispatchEvent(new Event("input"));
    ta.focus();
  });
  // 메모 칸 높이 — 위로 끌면 커진다.  상한은 도면 창에 머리줄 하나는 남게(#left 높이 − 120).
  _dragGutter($("#gutter-n"), "row", (e) => {
    const box = $("#memo"), lf = $("#left");
    const h = Math.max(110, Math.min(box.getBoundingClientRect().bottom - e.clientY, lf.clientHeight - 120));
    _memoPrefSave({ ..._memoPref(), h });
    memoLayout();
  });
  $("#gutter-n").addEventListener("dblclick", () => {
    const p = _memoPref(); delete p.h; _memoPrefSave(p); memoLayout();
    window.dispatchEvent(new Event("resize"));
  });
  memoLayout();
})();

/* ---------------- 위치 메모 (hotfix76) ----------------
 *
 * 사용자: *"메모가 pdf 상에 어떤 곳에 대한 메모인지, 마이크로소프트 프로그램의 메모 기능과 같이 메모를 클릭하면
 * pdf 위치를 보여주고 메모표기를 하는 기능."*
 *
 * 메모장(위)은 장 하나에 한 판씩 쌓이는 글이고, 위치 메모는 **장 안의 자리 하나**에 붙는 글이다 — Word 메모처럼
 * 여럿이 나란히 산다.  자리는 그 장의 PDF 좌표(오버레이 상자와 같은 좌표계 · `sheetPoint`)이고, 저장·이력·
 * 다른 Rev 공유는 메모장과 같은 파일·같은 열쇠(도면번호)다 (`app/sheet_memo.py`).
 *   · 목록의 메모를 누르면 → 도면이 그 자리로 가서(확대·가운데) 깜빡이고, 자리 옆에 말풍선이 선다.
 *   · 도면의 번호 깃발을 누르면 → 메모 판이 열리고 그 메모가 골라진다.
 *   · 글을 고치면 앞 글은 이력으로 · '완료' · '숨김' 은 표시일 뿐 지우지 않는다.
 * 행이 아니므로 SCOPE 색 칸에 섞지 않고 범례에 자기 칸을 둔다 (33회차 등식 *칸 합 = 상자 수* 유지).
 * 도면 위 깃발은 자리의 오른쪽 위 — 범례 판(왼쪽 아래)에 가려지지 않게 (자기검증 캡처가 잡았다). */
const PIN_MARK = ["PIN", "위치 메모 (행 아님)", "#e0a32e",
                  "사람이 도면의 한 자리에 단 메모 — 번호 깃발을 누르면 메모가, 메모를 누르면 그 자리가 보입니다"];
function pagePins() {
  const v = S.memoView;
  if (!v || !S.page || S.memoPage !== S.page.page_no) return [];
  return v.pins || [];
}
function pinShown(p) {
  return (p.state || "open") !== "hidden" || !!S.pinShowHidden;
}
function pinNumber(id) {
  const i = pagePins().findIndex(p => p.id === id);
  return i < 0 ? "?" : i + 1;
}
function pinWhen(p) {
  const who = p.author ? escape(p.author) : `<span class="muted">이름 없음</span>`;
  const rev = p.revision ? `<span class="rv-tag mini">${escape(p.revision)}</span>` : "";
  return `${rev}${p.here ? "" : ` <span class="memo-other" title="다른 분석에서 단 메모 — 그때의 도면 자리입니다">${p.other_rev ? "다른 Rev 에서" : "다른 분석에서"}</span>`}`
    + ` <b>${who}</b> · ${escape(whenWords(p.at))}`
    + (p.edited_at ? ` · <span class="muted" title="고친 글 — 앞 글은 이력에 남습니다">${escape(p.edited_by || "이름 없음")} 고침 ${escape(whenWords(p.edited_at))}</span>` : "");
}
function pinWarn(p) {
  const w = [];
  if (!p.here) w.push("다른 판에서 단 자리 — 이 판의 도면이 바뀌었으면 자리가 맞지 않을 수 있습니다");
  if (p.renumbered) w.push(`도면번호가 바뀐 장 — 옛 번호 ${p.key} 에서 단 메모`);
  if (p.scaled) w.push("종이 크기가 다른 판에서 단 자리 — 비례로 옮겨 그렸습니다");
  return w;
}
const PIN_STATE_WORD = { open: "", resolved: "완료", hidden: "숨김" };

function renderPins() {
  const box = $("#pin-list");
  if (!box) return;
  const all = pagePins();
  const shown = all.filter(pinShown);
  const open = all.filter(p => (p.state || "open") === "open").length;
  const hid = all.length - all.filter(p => (p.state || "open") !== "hidden").length;
  $("#pin-n").textContent = all.length ? `${open}개 열림${all.length - open ? ` · 완료/숨김 ${all.length - open}` : ""}` : "";
  $("#pin-showhidden").closest("label").classList.toggle("hidden", !hid && !S.pinShowHidden);
  const cnt = $("#memo-count");
  const nMemo = S.memoView ? (S.memoView.history || []).length : 0;
  cnt.textContent = nMemo || open ? `${nMemo || ""}${open ? `${nMemo ? " · " : ""}📍${open}` : ""}` : "";
  cnt.classList.toggle("hidden", !nMemo && !open);
  if (!shown.length) {
    box.innerHTML = `<li class="muted small">${all.length ? "보이는 위치 메모가 없습니다 (숨긴 것만 있음)."
      : "아직 없습니다 — 위의 <b>📍 도면에 메모 달기</b> 를 누르고 도면에서 자리를 끌거나 누르세요."}</li>`;
    return;
  }
  box.innerHTML = shown.map(p => {
    const st = p.state || "open";
    const warn = pinWarn(p);
    const editing = S.pinEditing === p.id;
    return `<li class="pin-item${S.pinSel === p.id ? " sel" : ""}${st === "resolved" ? " resolved" : ""}${st === "hidden" ? " hidden-state" : ""}" data-pin="${escAttr(p.id)}">`
      + `<div class="memo-meta"><span class="pin-no">${pinNumber(p.id)}</span>${pinWhen(p)}`
      + (PIN_STATE_WORD[st] ? ` <span class="pin-state">${PIN_STATE_WORD[st]}</span>` : "")
      + `<span class="pin-acts">`
      + `<button type="button" class="ghost mini" data-pa="go" title="도면에서 이 자리를 보여 줍니다">위치</button>`
      + `<button type="button" class="ghost mini" data-pa="edit" title="글을 고칩니다 (앞 글은 이력에 남습니다)">고치기</button>`
      + (st === "open" ? `<button type="button" class="ghost mini" data-pa="resolved" title="다 본 메모 — 흐리게 남습니다">완료</button>`
                       : `<button type="button" class="ghost mini" data-pa="open" title="다시 열린 메모로">다시 열기</button>`)
      + (st !== "hidden" ? `<button type="button" class="ghost mini" data-pa="hidden" title="목록과 도면에서 감춥니다 (기록은 남습니다)">숨김</button>` : "")
      + `</span></div>`
      + (editing ? `<textarea class="pin-edit">${escape(p.text)}</textarea><div class="pin-edit-acts">`
          + `<button type="button" class="primary mini" data-pa="save">저장</button><button type="button" class="ghost mini" data-pa="cancel">취소</button></div>`
        : `<div class="memo-txt">${escape(p.text)}</div>`)
      + (warn.length ? `<div class="pin-warn" title="${escAttr(warn.join(" · "))}">⚠ ${escape(warn[0])}</div>` : "")
      + (p.history && p.history.length ? `<details class="small muted"><summary>이력 ${p.history.length}</summary>`
          + p.history.slice().reverse().map(h => `<div>${escape(whenWords(h.at))} · ${escape(h.author || "이름 없음")} — ${
              h.to ? `상태 ${escape(PIN_STATE_WORD[h.state] || "열림")} → ${escape(PIN_STATE_WORD[h.to] || "열림")}` : `앞 글: ${escape(h.text || "")}`}</div>`).join("")
          + `</details>` : "")
      + `</li>`;
  }).join("");
  if (S.pinEditing) {
    const ta = box.querySelector(`li[data-pin="${CSS.escape(S.pinEditing)}"] .pin-edit`);
    if (ta && document.activeElement !== ta) { ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); }
  }
}

/* 도면 위 표식: 자리 사각형(파선 · 옅은 칠)과 번호 깃발.  점 메모는 깃발만. */
function drawPins(ov, scale) {
  if (S.ovOff.has(PIN_MARK[0])) return;
  const pins = pagePins().filter(pinShown);
  if (!pins.length) return;
  const NS = "http://www.w3.org/2000/svg";
  // 깃발 크기는 화면에서 같은 크기로 보이게 배율을 되돌린다 (확대해도 도면을 덮지 않는다)
  const z = S.zoom || 1;
  const rad = Math.max(7, 11 / z);
  for (const p of pins) {
    const [x0, y0, x1, y1] = p.rect;
    const st = p.state || "open";
    const cls = (st === "resolved" ? " resolved" : "") + (st === "hidden" ? " hid" : "") + (S.pinSel === p.id ? " sel" : "");
    const area = (x1 - x0) > 0.5 && (y1 - y0) > 0.5;
    if (area) {
      const b = document.createElementNS(NS, "rect");
      b.setAttribute("x", x0 * scale); b.setAttribute("y", y0 * scale);
      b.setAttribute("width", (x1 - x0) * scale); b.setAttribute("height", (y1 - y0) * scale);
      b.setAttribute("class", "pinbox" + cls);
      b.dataset.pin = p.id;
      ov.appendChild(b);
    }
    // 깃발은 자리의 **오른쪽 위** — 도면 범례 판이 왼쪽 아래에 떠 있어 왼쪽 모서리는 가려지기 쉽다
    const cx = x1 * scale, cy = y0 * scale;
    const g = document.createElementNS(NS, "g");
    g.setAttribute("class", "pinmark");
    g.dataset.pin = p.id;
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", cx); c.setAttribute("cy", cy); c.setAttribute("r", rad);
    c.setAttribute("class", "pinflag" + cls);
    const t = document.createElementNS(NS, "text");
    t.setAttribute("x", cx); t.setAttribute("y", cy); t.setAttribute("font-size", rad * 1.15);
    t.setAttribute("class", "pinflag-t");
    t.textContent = pinNumber(p.id);
    const tip = document.createElementNS(NS, "title");
    tip.textContent = `위치 메모 ${pinNumber(p.id)} — ${p.author || "이름 없음"}: ${p.text}`;
    c.appendChild(tip);
    g.appendChild(c); g.appendChild(t);
    g.onclick = (ev) => { ev.stopPropagation(); selectPin(p.id, { fromDrawing: true }); };
    g.onpointerdown = (ev) => ev.stopPropagation();          // 팬·띠 선택이 가로채지 않게
    ov.appendChild(g);
  }
}

/* 메모 하나를 고른다 — 목록에서 누르면 도면이 그 자리로 가고, 도면에서 누르면 목록이 그 메모로 간다.
 * 어느 쪽이든 자리 옆에 말풍선이 선다 (Word 메모처럼 글과 자리가 한눈에). */
function selectPin(id, opts = {}) {
  const p = pagePins().find(x => x.id === id);
  if (!p) return;
  S.pinSel = id;
  if ($("#memo").classList.contains("folded")) memoOpen(true);
  renderPins();
  const li = document.querySelector(`#pin-list li[data-pin="${CSS.escape(id)}"]`);
  if (li) li.scrollIntoView({ block: "nearest" });
  if (drawingHidden()) { syncPost({ t: "pin", page: S.page && S.page.page_no, id }); return; }
  drawOverlay();
  if (!opts.fromDrawing) focusPin(p);
  showPinPop(p);
}

function focusPin(p) {
  if (!S.natural || !S.page) return;
  const stage = $("#stage");
  const scale = S.natural.w / (S.page.width || 1);
  const [x0, y0, x1, y1] = p.rect;
  const w = Math.max(1, (x1 - x0) * scale), h = Math.max(1, (y1 - y0) * scale);
  // 자리가 화면의 반쯤을 차지하게 — 점 메모는 계기 하나 볼 때와 같은 배율 (SYMBOL_ZOOM)
  let want = Math.min(stage.clientWidth * 0.5 / w, stage.clientHeight * 0.5 / h);
  if (!(w > 2 && h > 2) || !isFinite(want)) want = SYMBOL_ZOOM;
  want = Math.max(Math.min(want, SYMBOL_ZOOM * 2), S.zoom || 0.1);
  if (want !== S.zoom) { S.zoom = want; applyZoom(); drawOverlay(); }
  const cx = (x0 + x1) / 2 * scale * S.zoom, cy = (y0 + y1) / 2 * scale * S.zoom;
  stage.scrollTo({ left: Math.max(0, cx - stage.clientWidth / 2), top: Math.max(0, cy - stage.clientHeight / 2) });
  const b = document.querySelector(`#ov .pinbox[data-pin="${CSS.escape(p.id)}"]`);
  if (b) { b.classList.remove("flash"); void b.getBoundingClientRect(); b.classList.add("flash"); }
}

function closePinPop() {
  const old = document.querySelector(".pinpop");
  if (old) old.remove();
  if (closePinPop._off) { document.removeEventListener("pointerdown", closePinPop._off, true); closePinPop._off = null; }
}
function _pinPopAt(pop, flag) {
  document.body.appendChild(pop);
  const ab = flag ? flag.getBoundingClientRect() : $("#stage").getBoundingClientRect();
  const pw = pop.offsetWidth, ph = pop.offsetHeight;
  let left = ab.right + 10, top = ab.top - 4;
  if (left + pw > window.innerWidth - 8) left = Math.max(8, ab.left - pw - 10);
  if (top + ph > window.innerHeight - 8) top = Math.max(8, window.innerHeight - ph - 8);
  pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  closePinPop._off = (ev) => { if (!pop.contains(ev.target)) closePinPop(); };
  setTimeout(() => document.addEventListener("pointerdown", closePinPop._off, true), 0);
}
function showPinPop(p) {
  closePinPop();
  const flag = document.querySelector(`#ov g.pinmark[data-pin="${CSS.escape(p.id)}"] circle`);
  if (!flag) return;
  const pop = document.createElement("div");
  pop.className = "pinpop";
  pop.setAttribute("role", "dialog");
  const st = p.state || "open";
  const warn = pinWarn(p);
  pop.innerHTML = `<div class="pp-h"><span class="pin-no">${pinNumber(p.id)}</span>${pinWhen(p)}${PIN_STATE_WORD[st] ? ` <span class="pin-state">${PIN_STATE_WORD[st]}</span>` : ""}</div>`
    + `<div class="pp-t">${escape(p.text)}</div>`
    + (warn.length ? `<div class="pin-warn">⚠ ${escape(warn.join(" · "))}</div>` : "")
    + `<div class="pp-b"><button type="button" class="ghost mini" data-pa="edit">고치기</button>`
    + (st === "open" ? `<button type="button" class="ghost mini" data-pa="resolved">완료</button>`
                     : `<button type="button" class="ghost mini" data-pa="open">다시 열기</button>`)
    + `<button type="button" class="ghost mini" data-pa="close">닫기</button></div>`;
  pop.querySelectorAll("button[data-pa]").forEach(b => b.onclick = (ev) => {
    ev.stopPropagation();
    const a = b.dataset.pa;
    closePinPop();
    if (a === "edit") { S.pinEditing = p.id; renderPins(); }
    else if (a === "resolved" || a === "open") pinUpdate(p.id, { state: a });
  });
  _pinPopAt(pop, flag);
}

/* 자리를 고른 뒤 글을 적는 말풍선.  자리 옆에 뜨고, 저장하면 서버가 그 장의 메모를 새로 돌려준다. */
function pinDialog(rect) {
  closePinPop();
  if (!S.page || !S.job) return;
  const pageNo = S.page.page_no;
  // 그 자리에 임시 깃발을 세워 말풍선이 붙을 곳을 만든다 (저장하지 않으면 다음 그리기에서 사라진다)
  const ov = $("#ov"), scale = S.natural.w / (S.page.width || 1);
  const NS = "http://www.w3.org/2000/svg";
  if (rect[2] - rect[0] > 0.5 && rect[3] - rect[1] > 0.5) {
    const b = document.createElementNS(NS, "rect");
    b.setAttribute("x", rect[0] * scale); b.setAttribute("y", rect[1] * scale);
    b.setAttribute("width", (rect[2] - rect[0]) * scale); b.setAttribute("height", (rect[3] - rect[1]) * scale);
    b.setAttribute("class", "pinbox sel");
    ov.appendChild(b);
  }
  const tmp = document.createElementNS(NS, "circle");
  tmp.setAttribute("cx", rect[2] * scale); tmp.setAttribute("cy", rect[1] * scale);
  tmp.setAttribute("r", Math.max(7, 11 / (S.zoom || 1)));
  tmp.setAttribute("class", "pinflag sel");
  ov.appendChild(tmp);
  const pop = document.createElement("div");
  pop.className = "pinpop";
  pop.setAttribute("role", "dialog");
  pop.innerHTML = `<div class="pp-h"><b>이 자리에 메모</b> <span class="muted">p${pageNo}${S.page.drawing_no ? " · " + escape(S.page.drawing_no) : ""}</span></div>`
    + `<textarea placeholder="무엇을 볼 자리인가 — 확인할 것 · 발주처 회신 · 개정 때 볼 것 …  (Ctrl+Enter 저장 · Esc 취소)"></textarea>`
    + `<div class="pp-b"><button type="button" class="primary mini" data-pa="save">저장</button>`
    + `<button type="button" class="ghost mini" data-pa="cancel">취소</button><span class="pp-msg"></span></div>`;
  const ta = pop.querySelector("textarea");
  const done = () => { closePinPop(); drawOverlay(); };
  const save = async () => {
    const text = ta.value.trim();
    if (!text) { pop.querySelector(".pp-msg").textContent = "글을 적어 주세요"; ta.focus(); return; }
    const author = await askAuthor("위치 메모");
    if (author === null) return;
    const before = new Set(pagePins().map(x => x.id));
    const res = await fetch(`/jobs/${S.job.id}/memo/${pageNo}/pins`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rect, text, author }) });
    const d = await res.json().catch(() => ({}));
    if (!res.ok) { pop.querySelector(".pp-msg").textContent = d.detail || "저장하지 못했습니다"; return; }
    closePinPop();
    if (S.memoPage === pageNo) S.memoView = d;
    const made = (d.pins || []).find(x => !before.has(x.id));
    renderMemo();
    loadMemoSummary();
    if (made) selectPin(made.id, { fromDrawing: true });
    else drawOverlay();
    editNotice("위치 메모를 달았습니다 — 같은 프로젝트의 다른 Rev 에서도 이 자리에 보입니다", "in");
  };
  pop.querySelector('[data-pa="save"]').onclick = guarded(save);
  pop.querySelector('[data-pa="cancel"]').onclick = done;
  ta.addEventListener("keydown", ev => {
    if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") { ev.preventDefault(); pop.querySelector('[data-pa="save"]').click(); }
    if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); done(); }
  });
  _pinPopAt(pop, tmp);
  ta.focus();
}

async function pinUpdate(id, body) {
  if (!S.job || !S.memoPage) return false;
  const author = await askAuthor("위치 메모");
  if (author === null) return false;
  const pageNo = S.memoPage;
  const res = await fetch(`/jobs/${S.job.id}/memo/${pageNo}/pins/${encodeURIComponent(id)}`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, author }) });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) { editNotice(d.detail || "위치 메모를 바꾸지 못했습니다", "out"); return false; }
  if (S.memoPage === pageNo) S.memoView = d;
  if (body.state === "hidden" && S.pinSel === id && !S.pinShowHidden) S.pinSel = null;
  renderMemo();
  loadMemoSummary();
  if (!drawingHidden()) drawOverlay();
  return true;
}

/* 장을 옮겨야 고를 수 있는 위치 메모(다른 창이 고른 것) — 그 장의 그림과 메모가 둘 다 선 뒤에 고른다. */
function tryPinPending() {
  const w = S.pinPending;
  if (!w || !S.page || S.page.page_no !== w.page) return;
  if (S.pinImgPage !== w.page || S.memoPage !== w.page || !S.memoView) return;
  S.pinPending = null;
  if (pagePins().some(x => x.id === w.id)) selectPin(w.id);
}

function setPinMode(on) {
  S.pinMode = !!on && !!S.page;
  if (S.pinMode) {
    if (S.markup) setMarkup(false);
    if (S.picking) endPick();
    closePinPop();
  }
  $("#stage").classList.toggle("pinning", S.pinMode);
  $("#memo-pin").classList.toggle("on", S.pinMode);
  $("#pin-note").classList.toggle("hidden", !S.pinMode);
}

(function initPins() {
  // 자리를 고른 그 클릭이 아래 상자(행)를 고르거나 공급 주체 판을 띄우지 않게 한 번 삼킨다
  $("#stage").addEventListener("click", ev => {
    if (S.pinJust && Date.now() - S.pinJust < 600) { S.pinJust = 0; ev.stopPropagation(); ev.preventDefault(); }
  }, true);
  $("#memo-pin").onclick = (ev) => { ev.stopPropagation(); setPinMode(!S.pinMode); };
  $("#pin-cancel").onclick = (ev) => { ev.stopPropagation(); setPinMode(false); };
  $("#pin-showhidden").onchange = (ev) => { S.pinShowHidden = ev.target.checked; renderPins(); drawOverlay(); };
  document.addEventListener("keydown", ev => {
    if (ev.key !== "Escape") return;
    if (S.pinMode) { setPinMode(false); ev.preventDefault(); }
    closePinPop();
  });
  $("#pin-list").addEventListener("click", ev => {
    const li = ev.target.closest("li[data-pin]");
    if (!li) return;
    const id = li.dataset.pin;
    const b = ev.target.closest("button[data-pa]");
    if (ev.target.closest("textarea, details")) return;
    if (!b) { selectPin(id); return; }
    ev.stopPropagation();
    const a = b.dataset.pa;
    if (a === "go") selectPin(id);
    else if (a === "edit") { S.pinEditing = id; renderPins(); }
    else if (a === "cancel") { S.pinEditing = null; renderPins(); }
    else if (a === "save") {
      const ta = li.querySelector(".pin-edit");
      const text = ta ? ta.value.trim() : "";
      if (!text) { ta && ta.focus(); return; }
      guarded(async () => { if (await pinUpdate(id, { text })) S.pinEditing = null; renderPins(); })();
    }
    else pinUpdate(id, { state: a });
  });
  $("#pin-list").addEventListener("keydown", ev => {
    const ta = ev.target.closest(".pin-edit");
    if (!ta) return;
    if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") { ev.preventDefault(); ta.closest("li").querySelector('[data-pa="save"]').click(); }
    if (ev.key === "Escape") { ev.preventDefault(); ev.stopPropagation(); S.pinEditing = null; renderPins(); }
  });
})();

/* ---------------- viewer ---------------- */
function buildPageSelect() {
  const sel = $("#page-select");
  sel.innerHTML = "";
  // hotfix40 — 이전 대비 변경이 있는 장은 장 목록에 그 수를 적는다 (＋추가 ≠수정 －삭제).
  // 판정은 행의 `rev.state` 와 서버의 삭제 후보 그대로 — 어느 장을 봐야 하는지 고르는 길이다.
  const ch = {};
  if (S.rev && S.rev.compared_with) {
    for (const r of S.rows || []) {
      const st = (r.rev || {}).state; if (st !== "ADDED" && st !== "MODIFIED") continue;
      (ch[r.page_no] = ch[r.page_no] || { a: 0, m: 0, d: 0 })[st === "ADDED" ? "a" : "m"]++;
    }
    const byDwg = {}; for (const p of S.pages) if (p.drawing_no) byDwg[p.drawing_no] = p.page_no;
    for (const d of S.rev.deleted_candidates || []) {
      const pn = byDwg[d.drawing_no]; if (!pn) continue;
      // hotfix47 — 이전 태그(수정)는 ≠ 에, 삭제 후보·확정은 － 에
      (ch[pn] = ch[pn] || { a: 0, m: 0, d: 0 })[delState(d) === "MODIFIED" ? "m" : "d"]++;
    }
  }
  for (const p of S.pages) {
    const o = document.createElement("option");
    o.value = p.page_no;
    const c = ch[p.page_no];
    const memo = S.memo && S.memo.pages && S.memo.pages[p.page_no];   // hotfix63 — 메모가 있는 장
    o.textContent = `p${p.page_no}  ${p.drawing_no || ""}`
      + (c ? `   ${c.a ? "＋" + c.a + " " : ""}${c.m ? "≠" + c.m + " " : ""}${c.d ? "－" + c.d : ""}`.replace(/\s+$/, "") : "")
      + (memo && memo.count ? `   ✎${memo.count}` : "")
      + (memo && memo.pins ? `   📍${memo.pins}` : "");
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
  // hotfix68 — 도면이 다른 창에 있으면 이 창은 장 그림을 받지 않는다 (A1 한 장 그림 · 근거 패널은 행에서 읽는다).
  // 다시 한 창으로 합치면 `setPane` 이 그 장을 그린다.
  S.imgStale = drawingHidden();
  img.onload = () => {
    // The magnification is the reviewer's, not the page's: moving to the next
    // sheet keeps it, and only opening a job (which is also what re-analysis
    // ends in) starts fitted again.  See `open()`.
    measure();
    if (S.zoom) applyZoom(); else fit();
    drawOverlay();
    // A selection made from the grid was waiting for this page to arrive.
    if (S.pending) { const k = S.pending; S.pending = null; select(k, true); }
    S.pinImgPage = page.page_no; tryPinPending();   // hotfix76 — 다른 창이 고른 위치 메모가 이 장을 기다리고 있었다
    prefetchNeighbours(page);               // hotfix69 — 다음 · 이전 장 그림을 쉬는 동안 받아 둔다
  };
  if (!S.imgStale) swapSheet(img, `/jobs/${S.job.id}/page/${page.page_no}.png?zoom=1.6`);
  syncPage();                               // hotfix68 — 목록 창의 "이 장" 이 도면 창의 장을 따른다
  showSheetNotes(page.page_no);
  showMemo(page.page_no);                 // hotfix63 — 이 장 메모 (같은 프로젝트의 모든 Rev)
  if (S.side) cmpShow();                  // hotfix40 — 오른쪽 창도 같은 도면번호 장으로
  if (S.markup) prewarmMarkup();          // 장이 바뀌면 그 장을 미리 읽는다
  // hotfix25 — From/To 범위는 그 행의 장에서만 긋는다.  장을 옮기면 대기를 풀고 말한다.
  if (S.ftMark) {
    const m = S.ftMark; endFtMark();
    const r0 = S.rowByKey[m.key];
    if (r0 && r0.page_no !== page.page_no)
      editNotice(`장을 옮겨 ${m.side === "from" ? "From" : "To"} 범위 지정을 취소했습니다 — 그 행은 p${r0.page_no} 입니다`, "out");
  }
}

/* hotfix69 — 장 그림(A1 이면 3,815×2,695 픽셀)을 **풀어 놓은 뒤** 화면에 건다.  `img.src` 를 바로 바꾸면 브라우저가
 * 첫 그리기 때 주 스레드에서 그림을 풀어 행을 누를 때마다 화면이 0.1~0.4초 멈췄다 (spike/perf_sim.py 의 rowclick ·
 * 프로파일 "(program)").  `decode()` 는 다른 스레드에서 풀고, 다 풀린 같은 주소를 걸면 그 결과를 그대로 쓴다.
 * 빨리 넘기면 마지막 장만 건다 (번호표). */
let _sheetSeq = 0;
function swapSheet(img, url) {
  const seq = ++_sheetSeq;
  const pre = new Image();
  pre.decoding = "async";
  pre.src = url;
  const go = () => { if (seq === _sheetSeq) img.src = url; };
  const box = $("#sheet-err");
  if (box) box.classList.add("hidden");
  // hotfix74 — 그림을 못 받으면 빈 자리만 남았다 (원본 PDF 가 지워진 경우 등 · state_chaos K2).
  // 서버가 이유를 말하므로(410 · 사람 말) 그 문장을 도면 자리 위에 띄운다.
  const failed = async () => {
    go();
    if (seq !== _sheetSeq || !box) return;
    let msg = "도면 그림을 불러오지 못했습니다.";
    try {
      const r = await fetch(url);
      if (!r.ok) { const j = await r.json().catch(() => ({})); if (j.detail) msg = j.detail; }
      else return;                                    // 받아졌다 — 일시적이었다
    } catch (e) { msg = "도면 그림을 불러오지 못했습니다 — 서버에 연결할 수 없습니다."; }
    if (seq !== _sheetSeq) return;
    box.textContent = msg;
    box.classList.remove("hidden");
  };
  if (pre.decode) pre.decode().then(go, failed); else go();
}

/* hotfix69 — 장을 넘길 때 기다리지 않게: 지금 장이 뜬 뒤 **쉬는 동안** 다음 · 이전 장 그림을 받아 둔다.
 * 브라우저가 그 그림을 캐시에 두므로(`Cache-Control: max-age=3600`) 넘기는 순간 바로 뜬다.  서버는 결과를 처음
 * 열 때부터 모든 장을 미리 그리고 있다 (`app/page_warm.py`).  받기만 하고 화면은 건드리지 않는다. */
const _prefetched = new Set();
function prefetchNeighbours(page) {
  if (!S.job || !S.pages || drawingHidden()) return;
  const i = S.pages.findIndex(p => p.page_no === page.page_no);
  const want = [S.pages[i + 1], S.pages[i - 1], S.pages[i + 2]].filter(Boolean);
  const go = () => {
    for (const p of want) {
      const url = `/jobs/${S.job.id}/page/${p.page_no}.png?zoom=1.6`;
      if (_prefetched.has(url)) continue;
      _prefetched.add(url);
      const im = new Image();
      im.decoding = "async";
      im.src = url;
      if (im.decode) im.decode().catch(() => {});     // 받아 둘 뿐 아니라 풀어 둔다 — 넘기는 순간 멈추지 않게
    }
  };
  if (window.requestIdleCallback) requestIdleCallback(go, { timeout: 1500 }); else setTimeout(go, 300);
}

/* 53회차 [E] — 이 장의 NOTES 판독 (8차 피드백 s3).
 *
 * 세 가지를 나눠 적는다: 도면이 **인쇄한 원문** · 거기서 읽은 **식별 값**
 * (유닛 표기) · 그것의 **해석**(배수).  그리고 그 해석을 실제로 썼는지까지
 * 적는다 — §9 읽는 순서가 ①범례 → ②NOTES 라서, 범례 승수표가 답한 문서에서는
 * 노트를 읽고도 쓰지 않는다.  그 사실을 감추면 "왜 x2 가 아니지" 를 물을 수
 * 없다.  판정은 서버가 준 `counted` 하나이고 여기서 다시 하지 않는다. */
async function showSheetNotes(pageNo) {
  const band = $("#notes-band");
  band.classList.add("hidden");
  let d;
  try { d = await (await fetch(`/jobs/${S.job.id}/notes/${pageNo}`)).json(); }
  catch (e) { return; }
  if (!d || d.known === false) return;
  if (!d.found) {
    $("#notes-sum").textContent = "NOTES — 유닛 문단 없음";
    $("#notes-body").innerHTML = `<p class="muted small">${escape(d.note || "")}</p>`;
    band.classList.remove("hidden");
    return;
  }
  // 읽은 것과 **쓴 것**을 갈라 말한다 — 판정은 서버가 준 `used` 하나다.
  const used = d.used
    ? "이 장의 수량 배수로 <b>썼습니다</b>"
    : `이 장의 수량은 <b>범례 승수표</b>가 정했습니다 (${escape(d.source || "LEGEND")}) — `
      + "도면이 두 곳에서 말하면 범례가 이깁니다. 위 해석은 <b>읽기만 한 값</b>입니다";
  $("#notes-sum").textContent =
    `NOTES 판독 — 유닛 ${d.units.join(" · ")} → 배수 x${d.factor}`
    + (d.used ? " (적용됨)" : " (읽기만 — 범례가 정함)");
  $("#notes-body").innerHTML =
    `<p class="nq">${escape(d.text)}</p>`
    + `<p class="small"><b>식별 값</b> ${escape(d.units.join(", "))} `
    + `(${d.units.length}개) &nbsp;·&nbsp; <b>해석</b> 이 도면은 유닛 ${d.units.length}개에 `
    + `같이 쓰이므로 심볼 1개당 x${d.factor}</p>`
    + `<p class="small muted">${used}</p>`;
  band.classList.remove("hidden");
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
  if ($("#stage").clientWidth < 20) return;     // hotfix68 — 도면이 다른 창에 있어 이 칸이 숨었다 (배율을 음수로 만들지 않는다)
  measure();
  S.zoom = ($("#stage").clientWidth - 16) / S.natural.w;
  applyZoom();
}
function applyZoom() { $("#wrap").style.transform = `scale(${S.zoom})`; cmpApplyZoom(); }

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
  if (!ev.ctrlKey && !ev.metaKey) {
    // hotfix63 — 도면을 끝까지 내린 뒤 휠을 더 내리면 이 장 메모가 열린다 (사용자 요구).
    const st = ev.currentTarget;
    if (ev.deltaY > 0 && st.scrollTop + st.clientHeight >= st.scrollHeight - 2) memoOpen(true);
    return;
  }
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

/* SCOPE 열의 값 — 서버(`pipeline.COL_VENDOR` · `COL_SCT`)와 같은 글자여야 한다.
 * 근거 패널과 범례가 같은 값을 읽으므로 한 곳에만 적는다. */
const SCOPE_DELIVERED = "SCT";
const SCOPE_VENDOR_PREFIX = "VENDOR";
// 서버 `excel_out.FORM_SCOPE_SCT` 와 같은 문자열.  화면은 이 값을 **판정하지
// 않고 받아 쓴다** — 필터를 실제로 거는 곳은 서버 하나다 (18회차).
const SCOPE_FILTER_SCT = "sct";

/* SCOPE 한 값이 무엇을 뜻하는가 — **화면에서 이 판정을 하는 곳은 여기 하나다**
 * (14회차).
 *
 * 12회차에 근거 패널이 세 질문을 나눠 답하게 됐는데, 그 판정이 패널 안에만
 * 있었다.  그래서 **편집하는 순간**에는 아무 말도 못 했다: 팀원이 벤더 행의
 * 값을 고쳐도 발주처 양식에는 안 실리는데 화면이 그 사실을 말하지 않았다
 * (갈음 검증에서 실제로 드러났다 — 첫 다섯 FIELD 행 중 3행이 VENDOR 였다).
 *
 * 판정을 두 벌 만들면 언젠가 갈리므로, 패널·편집 안내·SCOPE 변경 안내가
 * 전부 이 함수 하나를 읽는다.  서버 쪽 한 벌은 `excel_out.in_client_scope`
 * 이고 이 함수는 그것과 **같은 세 갈래**다:
 *
 *     SCT        →  delivered   양식에 나간다
 *     그 밖의 값   →  vendor      양식에 안 나간다 (타사 공급)
 *     빈 값       →  unjudged    양식에 나간다 — "판정한 적 없음"이라서
 *
 * 마지막 갈래가 뒤집힌 것처럼 보이지만 서버가 그렇게 판정한다(11회차):
 * 없는 판정을 "타사 공급"으로 읽으면 발주처 양식 네 개가 통째로 빈 파일이
 * 된다.  회사 PC 는 재분석 전까지 822행이 이 상태다. */
function scopeFacts(scopeVal, opts = {}) {
  const v = String(scopeVal ?? "").trim();
  const supplier = v.startsWith(SCOPE_VENDOR_PREFIX)
    ? (v.slice(SCOPE_VENDOR_PREFIX.length).replace(/^\(|\)$/g, "") || "이름 미상")
    : "";
  const state = v === SCOPE_DELIVERED ? "delivered" : v ? "vendor" : "unjudged";
  // 44회차 — 사람이 추가한 행의 빈 SCOPE 는 "옛 분석의 판정 없음" 이 아니라 **사람이
  // 비워 둔 칸**이다.  판정(state · inForm)은 같고 문장만 다르다 — 이 함수 안에서.
  const manualBlank = !!opts.manualBlank && state === "unjudged";
  const supplierName = opts.needsReview ? "검토 필요"
    : state === "delivered" ? "SCT 공급"
    : supplier ? `VENDOR 공급 — ${supplier}`
    : state === "vendor" ? v
    : manualBlank ? "SCOPE 비워 둠 — 별표를 못 읽어 사람이 정할 칸"
    : "판정 없음";
  // 18회차 — 양식이 무엇을 담는지는 **설정**이고 서버가 말해 준다
  // (`/jobs/{id}` 의 `form_scope`).  화면이 그것을 스스로 정하면 서버가
  // 실제로 쓰는 필터와 갈린다.  모르면 전량으로 본다 — 기본값이 그것이고,
  // 옛 응답(그 필드가 없는)에서 "빠집니다"라고 겁주지 않는다.
  const allRows = (S.job && S.job.form_scope) !== SCOPE_FILTER_SCT;
  const inForm = allRows || state !== "vendor";
  const formLine = allRows
    ? (state === "delivered" ? "나갑니다"
       : state === "vendor"
         ? `나갑니다 — 양식은 전량을 담습니다 (공급은 ${supplier || v}, `
           + "설치 자재는 SCT 몫이라 물량 산출에 필요합니다)"
         : manualBlank
           ? "나갑니다 — SCOPE 는 비워 두었습니다 (적으면 그 값으로 판정됩니다)"
         : "나갑니다 — SCOPE 를 판정한 적은 없습니다 "
           + "(이 열이 생기기 전의 분석입니다)")
    : (state === "delivered" ? "나갑니다"
       : state === "vendor"
         ? `나가지 않습니다 — 발주처 양식은 ${SCOPE_DELIVERED} 만 담습니다`
         : manualBlank
           ? "나갑니다 — 빈 값은 판정 없음으로 담깁니다 (SCOPE 를 적으면 그 값으로 판정됩니다)"
         : "판정한 적 없음 — 다시 분석하면 정해집니다 "
           + "(SCOPE 열이 생기기 전의 분석입니다)");
  return { value: v, state, supplier, supplierName, inForm, formLine, allRows };
}

/* 오버레이 범례 — **라벨과 세는 대상이 같아야 한다** (12회차).
 *
 * 11회차 캡처가 어긋남을 잡았다: p6 범례가 `공급자 인터페이스 구간 18` 이라고
 * 했는데 그 18 은 SCT **행 수**(계기 12 + 밸브 6)였다.  `SCT` 라는 오버레이
 * 키가 두 가지를 뜻하게 됐기 때문이다 — 원래는 `SCT_SUPPLIER_SCOPE` 규칙(파선
 * 브레이커 구간, 이 문서에서 2행)이었는데, 10회차에 SCOPE **열**이 생기면서
 * 우리 공급 전체(780행)가 같은 키를 받았다.
 *
 * 두 안 중 (a) 를 택했다 — 세는 대상은 SCOPE 열 그대로 두고 라벨을 거기 맞춘다.
 * (b)(세는 대상을 파선 구간으로 되돌리기)는 발주처가 요구한 표기와 어긋난다:
 * 피드백 5장이 "파랑 = SCT 공급 범위 · 주황 = VENDOR 공급 (BM 당사)" 라고
 * 못박았고, 그것은 열 값을 세라는 뜻이다.  파선 구간 자체는 근거 패널의
 * `적용 규칙`(`SCT_SUPPLIER_SCOPE`)에 그대로 남는다.
 *
 * 색: 발주처 요구대로 SCT 가 파랑이다.  이전에는 파랑이 `INCLUDED`, 보라가
 * `SCT` 였다 — 값만 옮겼고 **색 자체는 새로 고르지 않았다**(발주처가 이미 본
 * 색이다). */
// 18회차 — 설명이 **공급 주체**를 말하고, 양식에 나가는지는 그 뒤에 붙인다.
// 이 열이 세는 것은 공급 주체이고(11회차 라벨 규칙), 양식 범위는 설정이라
// 달라진다.  둘을 한 문장에 못박아 두면 설정을 바꾼 순간 범례가 거짓말한다.
const SCOPE = [
  ["SCT", "SCT 공급 범위", "#0a84ff", "SCOPE 열이 SCT — 우리 공급"],
  ["VENDOR_EXCLUDED", "VENDOR 공급 (BM 당사)", "#ff9f0a",
   "SCOPE 열이 VENDOR — 계기는 타사 공급, 설치 자재는 SCT 공급"],
  ["INCLUDED", "판정 없음", "#bf5af2",
   "SCOPE 열이 비어 있습니다 — 이 열이 생기기 전의 분석. 다시 분석하면 정해집니다"],
];
/* 33회차 — 검토 필요는 **색이 아니라 표식**이다.
 *
 * 32회차 [B] 가 잡은 것: 색이 SCOPE 를 읽되 `needs_review` 가 먼저였다
 * (`pipeline._layers`, 2026-08-17 부터).  검토 행이 드물 때는 "판정을 보류한
 * 행을 눈에 띄게" 였는데, 31회차 승수 사유가 SADARA 82/82 · UAD 149/149 에
 * 붙자 도면이 한 색이 되고 범례가 `SCT 0` 이라고 말했다 — 그 행들은 SCT 다.
 * "누가 공급하는가" 와 "사람이 봐야 하는가" 는 다른 축이므로 하나가 다른
 * 하나를 덮으면 안 된다.  색은 SCOPE, 검토는 상자 모서리의 붉은 ● 표식 —
 * §7.2 (색 + 형태 + 라벨).  세 색 칸의 합 = 상자 수 = 그리드 행 수이고,
 * 검토 칸은 **그중** 몇인가를 센다. */
const REVIEW_MARK = ["REVIEW", "검토 필요 (그중)", "#ff453a",
                     "판정 보류 — 상자 모서리의 ● 표식. 근거 패널의 사유 확인"];
/* 44회차 — 사용자 마크업도 색이 아니라 **표식**이다 (E-1 (b)).  색은 SCOPE 가
 * 그대로 갖고, 추가 행은 점선 테두리 + 왼쪽 위 초록 ✚, 오검출 표시는 오른쪽
 * 아래 회색 ✕ 다.  검토 ● 는 오른쪽 위 — 세 표식이 서로 다른 모서리라 겹치지
 * 않는다.  둘 다 "(그중)" 으로 센다 — 세 색 칸의 합은 그대로다. */
/* 53회차 — 사용자 요구로 **자기 색 칸**이 됐다 (8차 s8).  "(그중)" 이 아니므로
 * 세 색 칸이 넷이 되고, 합은 그대로 상자 수다 (33회차 등식 유지). */
const MANUAL_MARK = ["MANUAL", "사용자 추가", "#34c759",
                     "사람이 도면에서 추가한 행 — 녹색 선과 왼쪽 위 ✚"];
const REJECT_MARK = ["REJECT", "삭제·오검출 (그중)", "#d70015",
                     "사람이 지운(오검출) 행 — 붉은 파선 테두리와 대각선 ✕. 행은 남고 되돌릴 수 있으며 Excel 에서 빠집니다"];
/* 9차 피드백 [B] — Typical 표식(`D` · `D1` …)과 상세 상자.  **행이 아니다** —
 * 그 자리에 품목이 있는 것이 아니라 "이 자리는 저 상세와 같다" 는 도면의 말이고,
 * 수량은 그 상세 안의 행이 받는다 (38회차 [D]).  그래서 SCOPE 색 칸에 섞지 않고
 * 자기 칸을 갖는다 — 33회차 등식(칸 합 = 상자 수)은 그대로다. */
const TYPICAL_MARK = ["TYPICAL", "Typical 표식 (행 아님)", "#5e5ce6",
                      "도면이 선언한 Typical 표식과 상세 상자 — 상자 안의 행 수량이 참조 수만큼 곱해집니다"];
/* hotfix25 — Diaphragm Seal.  **행이 아니다** — 그 계기의 임펄스 라인에 붙은 부속이고
 * Remark 에 적힌다 (hotfix22~24).  글자로만 있으면 도면에서 "어느 것" 인지 안 보인다 —
 * 사용자 요구는 늘 식별 **표기**였다.  값은 행의 근거(`evidence.diaphragm_seal.rects`)
 * 에서 읽는다 — Remark 가 읽는 그 값이다 (11회차: 화면이 데이터와 같은 접근자를 읽는다).
 * 자기 칸이라 33회차 등식(색 칸 합 = 상자 수)은 그대로다. */
/* hotfix32 — **식별 표기 옆의 수량** (사용자 요구: *"각 식별된 계기, 식별 표기 옆에
 * x1, x2 와 같이 note 에 따른, 즉 출력된 수량을 표기하고, 사용자가 수량을 바꾸면
 * 그 값이 list 에도 변경 표기와 함께 반영되게"*).  행이 아니라 **행의 Q'ty 칸**이
 * 도면 위에 선 것이다 — 값은 그리드와 **같은 접근자**(`cellValue(row,"qty")`)에서
 * 오고, 누르면 **그리드와 같은 저장 길**(`saveEdit` → PATCH · 작성자 · ✎)로 간다.
 * 두 벌을 두면 갈린다 (11회차).  "(그중)" 이라 33회차 등식(색 칸 합 = 상자 수)은
 * 그대로다. */
const QTY_MARK = ["QTY", "수량 x N (그중)", "#1c1c1e",
                  "식별 표기 옆의 x N — 그 행의 Q'ty (NOTES 승수 반영). 누르면 그 자리에서 고치고, 고친 값은 목록·Excel 에 ✎ 와 함께 반영됩니다"];
const SEAL_MARK = ["SEAL", "Diaphragm Seal (행 아님)", "#0d9488",
                   "계기 임펄스 라인의 격막 씰 — 그 계기의 Remark 에 'Diaphragm Seal' 이 적힙니다. 누르면 그 계기 행이 골라집니다"];

/* 범례 설명 뒤에 "양식에 나가는가" 한 마디를 붙인다.  판정은 `scopeFacts`
 * 하나에서 오고 여기서 다시 하지 않는다 (12회차 규칙). */
function scopeTip(key, tip) {
  const sample = key === "SCT" ? SCOPE_DELIVERED
    : key === "VENDOR_EXCLUDED" ? "VENDOR" : "";
  if (key === "REVIEW") return tip;
  return `${tip}. 발주처 양식에 ${scopeFacts(sample).formLine}`;
}
const SCOPE_COLOR = Object.fromEntries(SCOPE.map(([k, , c]) => [k, c]));

/* 상자 하나의 SCOPE 갈래.  33회차 이전 분석은 검토 행을 `REVIEW` 로 저장해
 * 두어 공급 주체를 잃었으므로, 그런 항목은 **그리드 행의 SCOPE 열**에서 되찾는다
 * (같은 접근자 `cellValue` 가 읽는 값이다).  새 분석은 `scope` 가 곧 갈래다. */
function itemScope(it) {
  // 53회차 [F] — **그리드의 지금 SCOPE 가 먼저다.**
  //
  // 8차 피드백 s7: *"사용자가 왼쪽에서 Label 을 클릭하고 오른쪽 SCOPE 를
  // 변경하면 SCT, VENDOR 에 따라 색상이 변하게 하라."*  `it.scope` 는 **분석
  // 때 적힌 층**이라 사람이 고친 값을 모른다.  이전에는 `REVIEW` 인 항목만
  // 행에서 되찾았는데, 그러면 편집이 색에 닿지 않는다.
  //
  // 읽는 곳은 여전히 하나다 — `cellValue(row,"scope")` 는 그리드·필터·근거
  // 패널이 쓰는 그 접근자다.  행이 없는 항목만 층 값으로 떨어진다.
  const row = (S.rows || []).find(r => r.key === it.key);
  if (row) return scopeKeyOf(cellValue(row, "scope"));
  return it.scope || "INCLUDED";
}

/* 44회차 — 오버레이 항목 = 분석 때의 층(`page.layers`) **+ 사용자 추가 행**.
 *
 * 추가 행은 `pid_page.layers_json` 에 없다(그 층은 분석 때 한 번 적힌다).  그래서
 * 여기서 `S.rows` 의 `added` 행을 **같은 얼굴**로 합친다 — 색 갈래는 그리드
 * SCOPE 열과 같은 값(`scopeKeyOf`)에서 온다.  세 색 칸의 합 = 상자 수 =
 * 그리드 행 수 (33회차 등식)가 추가 행까지 포함해 그대로 성립한다.
 * 오검출 표시(`reject`·`removed`)는 층 항목이 그대로 있으므로 상자도 행도
 * 남고, 표식만 더한다.  등식 불변. */
function scopeKeyOf(v) {
  v = String(v || "");
  return v === SCOPE_DELIVERED ? "SCT"
    : v.startsWith(SCOPE_VENDOR_PREFIX) ? "VENDOR_EXCLUDED" : "INCLUDED";
}

function overlayItems(page) {
  const out = [];
  for (const [tab, items] of Object.entries(page.layers || {})) {
    for (const it of items) {
      const row = S.rowByKey[it.key];
      out.push({ ...it, tab,
                 rejected: !!(row && (row.removed || (row.reject && Object.keys(row.reject).length))) });
    }
  }
  for (const r of S.rows) {
    if (!r.added || r.page_no !== page.page_no || !(r.rect && r.rect.length === 4)) continue;
    out.push({ key: r.key, rect: r.rect, label: r.values.type || r.values.valve_type || "",
               needs_review: !!r.needs_review, scope: scopeKeyOf(r.values.scope),
               kind: r.tab === "FIELD" ? "INSTRUMENT" : "VALVE", row: true,
               reason: r.needs_review, tab: r.tab, manual: true });
  }
  // hotfix25 — 격막 씰: 그 장 행의 근거에서 읽는다.  행이 아니므로 `row: false` 이고
  // 열쇠는 **그 계기 행**이다 — 씰을 누르면 그 행이 골라진다.
  for (const r of S.rows) {
    if (r.page_no !== page.page_no) continue;
    const ds = (r.evidence || {}).diaphragm_seal;
    if (!ds || !Array.isArray(ds.rects)) continue;
    ds.rects.forEach((rc, i) => out.push({
      key: r.key, rect: rc, label: ds.remark || "Diaphragm Seal", seal: true, row: false,
      kind: "INSTRUMENT", tab: r.tab, needs_review: false, sealIndex: i,
      reason: `${ds.remark || "Diaphragm Seal"} — ${r.values.type || ""} 의 임펄스 라인` }));
  }
  return out;
}

function itemVisible(it) {
  // 53회차 — 사용자 추가는 자기 색 칸이므로 그 칸을 끄면 상자도 숨는다
  // (범례 라벨과 세는 대상과 그리는 대상이 같아야 한다 — 11회차 캡처).
  if (it.seal) return !S.ovOff.has(SEAL_MARK[0]) && S.tab !== "REVIEW";
  if (it.typical) { if (S.ovOff.has(TYPICAL_MARK[0])) return false; }
  else if (it.manual) { if (S.ovOff.has(MANUAL_MARK[0])) return false; }
  else if (S.ovOff.has(itemScope(it))) return false;
  // Typical 표식은 어느 산출물 탭에도 속하지 않는다 — 검토 탭 말고는 늘 보인다.
  if (it.typical) return S.tab !== "REVIEW";
  if (S.tab === "REVIEW") return !!it.needs_review;
  if (S.tab === "ALL") return true;
  // A deliverable tab shows its own rows, and keeps the excluded symbols on
  // screen: they are the reason a count comes up short.
  return it.tab === S.tab || it.tab === "EXCLUDED";
}

function buildOverlayLegend() {
  const items = S.page ? overlayItems(S.page) : [];
  const counts = {};
  let review = 0, manual = 0, rejected = 0, typical = 0, seal = 0, qtyTags = 0;
  for (const it of items) {
    if (qtyTagRow(it)) qtyTags++;
    // 53회차 — 사용자 추가는 **자기 칸**이다 (상자도 녹색으로 그린다).  SCOPE
    // 칸에도 세면 한 상자가 두 번 세어져 33회차 등식이 깨진다.
    if (it.seal) seal++;
    else if (it.typical) typical++;
    else if (it.manual) manual++;
    else counts[itemScope(it)] = (counts[itemScope(it)] || 0) + 1;
    if (it.needs_review) review++;
    if (it.rejected) rejected++;
  }
  const row = (key, label, colour, why, n, swatch) => `
    <label class="ovl-row" title="${escape(scopeTip(key, why))}">
      <input type="checkbox" class="ovl" value="${key}"
             ${S.ovOff.has(key) ? "" : "checked"}>
      <span class="swatch ${swatch}" style="background:${colour}"></span>
      <span class="ovl-label">${label}</span>
      <span class="n">${n}</span>
    </label>`;
  $("#ovl-items").innerHTML = SCOPE.map(([key, label, colour, why]) =>
    row(key, label, colour, why, counts[key] || 0, "")).join("")
    + row(...MANUAL_MARK, manual, "")
    + row(...TYPICAL_MARK, typical, "")
    + row(...SEAL_MARK, seal, "")
    + row(...REVIEW_MARK, review, "badge")
    + row(...REJECT_MARK, rejected, "badge")
    + row(...QTY_MARK, qtyTags, "badge")
    + row(...PIN_MARK, pagePins().filter(pinShown).length, "");
  document.querySelectorAll(".ovl").forEach(c => c.addEventListener("change", () => {
    if (c.checked) S.ovOff.delete(c.value); else S.ovOff.add(c.value);
    drawOverlay();
  }));
  // hotfix26 — 접힌 판의 한 줄 요약.  세는 값은 위 칸들과 **같은 변수**다.
  const sum = $("#ovl-sum");
  if (sum) sum.textContent = `SCT ${counts.SCT || 0} · VENDOR ${counts.VENDOR_EXCLUDED || 0}`
    + ` · 판정없음 ${counts.INCLUDED || 0}` + (manual ? ` · 추가 ${manual}` : "")
    + (typical ? ` · Typical ${typical}` : "") + (seal ? ` · 씰 ${seal}` : "") + ` · 검토 ${review}`;
}

/* 56회차 — **DXF 는 빗금으로 칠한다** (현장 보고: *"식별 표기를 위해 표기된
 * 네모난 박스 내부에 빗금을 쳐 달라"*).
 *
 * 왜 DXF 만인가: DXF 도면은 층마다 색이 다르다(파랑 배관 · 초록 신호 · 자홍
 * 경계).  평평한 음영은 그 색들 위에서 "덧칠한 색" 과 구별되지 않지만, 빗금은
 * **도면에 없는 무늬**라 무엇이 우리 표시인지 한눈에 갈린다.  PDF 도면은
 * 검은 잉크뿐이라 평평한 음영으로 충분하고, 바꾸면 여덟 회차를 눈으로 맞춰 둔
 * 화면이 같이 움직인다.
 *
 * 색은 **그대로 테두리와 같은 값**이다 — 빗금은 무늬이지 색이 아니다
 * (11회차 — 색과 SCOPE 열은 같은 값을 읽는다).  무늬는 색마다 하나씩 그 자리에서
 * 만들고, `drawOverlay` 가 매번 `ov` 를 비우므로 `defs` 도 그때 다시 선다. */
function isDxfJob() {
  // 두 곳을 본다 — 분석 기록(`job.input_kind`)과 **엔진이 결과에 적은 것**
  // (`engine.input_kind` · `dxf_pipeline.INPUT_KIND`).  옛 분석은 job 열이
  // 비어 있을 수 있고, 그때도 결과는 자기가 무엇이었는지 알고 있다.
  const a = String((S.job || {}).input_kind || "").toUpperCase();
  const b = String(((S.job || {}).engine || {}).input_kind || "").toUpperCase();
  return a === "DXF" || b === "DXF";
}

function hatchFill(ov, colour) {
  const id = "hatch-" + String(colour).replace(/[^0-9a-zA-Z]/g, "");
  if (!ov.querySelector("#" + id)) {
    let defs = ov.querySelector("defs");
    if (!defs) {
      defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
      ov.insertBefore(defs, ov.firstChild);
    }
    const pat = document.createElementNS("http://www.w3.org/2000/svg", "pattern");
    pat.setAttribute("id", id);
    pat.setAttribute("patternUnits", "userSpaceOnUse");
    pat.setAttribute("width", HATCH_STEP); pat.setAttribute("height", HATCH_STEP);
    pat.setAttribute("patternTransform", "rotate(45)");
    const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
    ln.setAttribute("x1", 0); ln.setAttribute("y1", 0);
    ln.setAttribute("x2", 0); ln.setAttribute("y2", HATCH_STEP);
    ln.setAttribute("stroke", colour);
    ln.setAttribute("stroke-width", HATCH_WIDTH);
    pat.appendChild(ln);
    defs.appendChild(pat);
  }
  return `url(#${id})`;
}

const HATCH_STEP = 7;     // 무늬 간격 (오버레이 좌표) — 확대하면 같이 커진다
const HATCH_WIDTH = 1.6;  // 테두리와 같은 굵기라 한 벌로 읽힌다

function drawOverlay() {
  const ov = $("#ov");
  ov.innerHTML = "";
  if (!S.page || !S.natural) return;
  const scale = S.natural.w / (S.page.width || 1);
  ov.setAttribute("viewBox", `0 0 ${S.natural.w} ${S.natural.h}`);
  drawTrace(ov, scale);
  // hotfix27 — **큰 상자를 먼저, 작은 상자를 나중에** 그린다.  SVG 는 나중에 그린 것이
  // 위에 서서 클릭을 받는다.  Typical 상세 상자(`D HRH TYPICAL DRAIN CONFIGURATION`)는
  // 층 목록 끝에 있어 **안쪽 TT · MOV 상자 위에** 덮였고, 칠이 투명해도 클릭을
  // 가로채 그 행들을 누를 수 없었다.  면적 순서는 어느 층이 뒤에 오든 성립한다
  // (상자 안에 든 것은 늘 그 상자보다 작다).  세는 것(`overlayItems`)은 그대로다.
  const area = r => Math.abs((r[2] - r[0]) * (r[3] - r[1]));
  const drawn = overlayItems(S.page).map((it, i) => [it, i])
    .sort((a, b) => (area(b[0].rect) - area(a[0].rect)) || (a[1] - b[1]))
    .map(p => p[0]);
  for (const it of drawn) {
    if (!itemVisible(it)) continue;
    const [x0, y0, x1, y1] = it.rect;
    const r = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    r.setAttribute("x", x0 * scale);
    r.setAttribute("y", y0 * scale);
    r.setAttribute("width", Math.max(2, (x1 - x0) * scale));
    r.setAttribute("height", Math.max(2, (y1 - y0) * scale));
    // 세 축이 한 테두리를 두고 다투지 않게 갈라 놓는다:
    //   색      = SCOPE 열 (#0a84ff SCT 공급 · #ff9f0a VENDOR 공급) — 의미 그대로
    //   파선    = 종류 (밸브)
    //   바깥 링 = 개정 (추가 · 수정)
    // 개정을 같은 테두리의 굵기·파선으로 말하면 밸브의 파선과 "제외는 얇게"가
    // 둘 다 지워진다.  실제로 그랬다: `.det.rev-added` 가 뒤에 있어 `.det.valve`
    // 와 `.det.excluded` 를 이겼다.  그래서 개정은 자기 도형을 따로 그린다.
    const rev = (S.revByKey || {})[it.key];
    r.setAttribute("class", "det"
      + (it.seal ? " seal" : "")
      + (it.typical ? " typical" : "")
      + (it.kind === "VALVE" ? " valve" : "")
      + (it.row === false ? " excluded" : "")
      + (it.manual ? " manual" : "")
      + (it.rejected ? " rejected" : "")
      + (S.multi.has(it.key) ? " multi" : "")
      + (S.sel === it.key ? " sel" : ""));
    // 53회차 [G] — **사용자 마크업 상자는 녹색 선**이다 (8차 피드백 s8:
    // *"사용자가 마크업 Block 을 녹색 Line 으로 표기하라"*).
    //
    // 44회차는 색을 SCOPE 에 두고 표식(모서리 ✚)만 더했다 — 그 판단을 사용자가
    // 뒤집었으므로 따른다.  대신 **33회차 등식이 깨지지 않게** 범례를 같이
    // 고친다: 사용자 추가는 "(그중)" 이 아니라 자기 색 칸이 되고, 합은
    // `SCT + VENDOR + 판정없음 + 사용자추가 = 상자 수` 다.
    // 탭 색 보기(`S.byTab`)에서는 탭이 색을 정하므로 건드리지 않는다.
    const stroke = it.seal ? SEAL_MARK[2]
      : it.typical ? TYPICAL_MARK[2]
      : S.byTab ? (COLOR[it.tab] || "#8e8e93")
      : it.manual ? MANUAL_MARK[2]
      : (SCOPE_COLOR[itemScope(it)] || "#8e8e93");
    r.setAttribute("stroke", stroke);
    // ★ 식별된 것은 **반투명 음영**으로도 말한다 (DXF 9차 피드백 3번).
    // DXF 도면은 층마다 색이 달라서(파랑 배관 · 초록 테두리 · 자홍 상자) 가는
    // 테두리 하나로는 "이건 우리가 잡은 것" 이 도면 색에 묻힌다.  같은 색을
    // 아주 옅게 깔면 도면 글자는 그대로 읽히면서 잡힌 자리가 한눈에 보인다.
    // 색은 테두리와 **같은 값**이다 — 색이 둘이면 SCOPE 가 두 말을 하게 된다.
    // 제외된 심볼(행이 아닌 것)은 칠하지 않는다: 잡은 것과 같은 얼굴이 된다.
    if (it.row !== false) {
      // ★ 56회차 — **인라인 스타일로 칠한다.**  `styles.css` 의 `rect.det` 이
      // `fill: transparent` 를 갖고 있고(상자 안쪽까지 클릭이 통하게 하려고 둔
      // 것), CSS 규칙은 **표현 속성(`setAttribute('fill', …)`)을 이긴다**.
      // 그래서 9차 [3] 의 "반투명 음영" 은 코드가 도는데도 **한 번도 칠해진 적이
      // 없었다** — 패턴이 안 보이는 것을 파다가 드러났다 (살아 있는 페이지에
      // 같은 패턴을 직접 그려 보니 멀쩡히 칠해진다: out/round56/patprobe).
      r.style.fill = isDxfJob() ? hatchFill(ov, stroke) : stroke;
      if (isDxfJob()) r.classList.add("hatch");
    }
    // 53회차 [B] — 밸브 행의 **태그 버블**에도 가는 고리를 그린다
    // (8차 피드백 s6 · TC2 9차: 버블에 아무 표시가 없어 "XV·MOV·TCV·PCV 가
    // 식별되지 않는다" 로 읽힌다).  행의 상자는 **몸체** 위에 서므로, 도면에서
    // 이름을 읽는 사람은 버블을 보는데 그 자리에 아무 것도 없었다.
    //
    // ★ 예전에는 **고른 행에만** 그렸다 — 누르기 전에는 안 보이니 "안 잡혔다"
    // 와 구별되지 않는다.  이제 늘 그리고, 고른 행에서만 진해진다.
    // 상자를 하나 더 세지 않는다 — `rect.det` 이 아니라 장식이라 33회차
    // 등식(색 칸 합 = 상자 수)은 그대로다.  잇는 선은 고른 행에서만 그린다
    // (전부 그리면 도면이 선으로 덮인다).
    if (!it.seal) {
      // 56회차 — 층이 실어 주면 그것을 쓰고, 옛 분석이면 행에서 찾는다.
      const tr = it.tag_rect
        || ((S.rowByKey[it.key] || {}).evidence || {}).tag_rect;
      if (tr && (Math.round(tr[0]) !== Math.round(it.rect[0])
                 || Math.round(tr[1]) !== Math.round(it.rect[1]))) {
        const tb = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        tb.setAttribute("x", tr[0] * scale); tb.setAttribute("y", tr[1] * scale);
        tb.setAttribute("width", Math.max(2, (tr[2] - tr[0]) * scale));
        tb.setAttribute("height", Math.max(2, (tr[3] - tr[1]) * scale));
        tb.setAttribute("class", "tagbub" + (S.sel === it.key ? " sel" : ""));
        tb.setAttribute("stroke", stroke);
        if (S.sel === it.key) {
          const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
          ln.setAttribute("x1", (tr[0] + tr[2]) / 2 * scale);
          ln.setAttribute("y1", (tr[1] + tr[3]) / 2 * scale);
          ln.setAttribute("x2", (x0 + x1) / 2 * scale);
          ln.setAttribute("y2", (y0 + y1) / 2 * scale);
          ln.setAttribute("class", "tagbub-l");
          ln.setAttribute("stroke", stroke);
          ov.appendChild(ln);
        }
        ov.appendChild(tb);
      }
    }
    // 검토 필요는 색을 바꾸지 않고 **모서리 표식**으로 말한다 (33회차).  표식은
    // 자기 층이라 범례에서 따로 끄고, 상자와 같은 키로 클릭이 통한다.
    if (it.needs_review && !S.ovOff.has(REVIEW_MARK[0])) {
      const rad = Math.max(4, (y1 - y0) * scale * 0.2);
      const cx = x1 * scale, cy = y0 * scale;
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", cx); dot.setAttribute("cy", cy); dot.setAttribute("r", rad);
      dot.setAttribute("class", "revbadge");
      const bang = document.createElementNS("http://www.w3.org/2000/svg", "text");
      bang.setAttribute("x", cx); bang.setAttribute("y", cy);
      bang.setAttribute("font-size", rad * 1.5);
      bang.setAttribute("class", "revbadge-t");
      bang.textContent = "!";
      const tip = document.createElementNS("http://www.w3.org/2000/svg", "title");
      tip.textContent = `검토 필요 — ${it.reason || ""}`;
      dot.appendChild(tip);
      for (const el of [dot, bang]) {
        el.dataset.key = it.key;
        el.onclick = (ev) => { ev.stopPropagation(); select(it.key, false, it); };
      }
      ov.appendChild(dot); ov.appendChild(bang);
    }
    // hotfix32 — 식별 표기 옆의 수량 `x N`.  상자 오른쪽 가운데 (검토 ● 는 오른쪽
    // 위 · 오검출 ✕ 는 오른쪽 아래라 모서리가 겹치지 않는다).
    if (!S.ovOff.has(QTY_MARK[0])) {
      const qrow = qtyTagRow(it);
      if (qrow) drawQtyTag(ov, scale, it, qrow, stroke);
    }
    // 44회차 — 사용자 추가 ✚(왼쪽 위) · 오검출 ✕(오른쪽 아래).  검토 ● 와
    // 모서리가 다르다.  범례에서 따로 끌 수 있고 상자와 같은 키로 클릭이 통한다.
    const badge = (cx, cy, cls, glyph, tip) => {
      const rad = Math.max(4, (y1 - y0) * scale * 0.2);
      const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      dot.setAttribute("cx", cx); dot.setAttribute("cy", cy); dot.setAttribute("r", rad);
      dot.setAttribute("class", cls);
      const t = document.createElementNS("http://www.w3.org/2000/svg", "text");
      t.setAttribute("x", cx); t.setAttribute("y", cy);
      t.setAttribute("font-size", rad * 1.5);
      t.setAttribute("class", "revbadge-t");
      t.textContent = glyph;
      const ti = document.createElementNS("http://www.w3.org/2000/svg", "title");
      ti.textContent = tip;
      dot.appendChild(ti);
      for (const el of [dot, t]) {
        el.dataset.key = it.key;
        el.onclick = (ev) => { ev.stopPropagation(); select(it.key, false, it); };
      }
      ov.appendChild(dot); ov.appendChild(t);
    };
    if (it.manual && !S.ovOff.has(MANUAL_MARK[0])) {
      const mk = ((S.rowByKey[it.key] || {}).evidence || {}).markup || {};
      badge(x0 * scale, y0 * scale, "manbadge", "+",
            `사용자 추가 — ${mk.author || "이름 없음"}`);
    }
    if (it.rejected && !S.ovOff.has(REJECT_MARK[0])) {
      // hotfix14 — **지운 자리는 붉은 선으로 말한다.**  흐리게만 하면(44회차) 도면
      // 색 위에서 "지웠다" 가 안 읽혔다.  붉은 파선 테두리 + 대각선 두 줄.  칸은
      // 여전히 SCOPE 색이 센다 (33회차 등식) — 이 표시는 범례의 "(그중)" 칸이다.
      const sx0 = x0 * scale, sy0 = y0 * scale, sx1 = x1 * scale, sy1 = y1 * scale;
      const ring = document.createElementNS("http://www.w3.org/2000/svg", "rect");
      ring.setAttribute("x", sx0 - 2); ring.setAttribute("y", sy0 - 2);
      ring.setAttribute("width", Math.max(2, sx1 - sx0) + 4);
      ring.setAttribute("height", Math.max(2, sy1 - sy0) + 4);
      ring.setAttribute("class", "delring");
      ov.appendChild(ring);
      for (const [ax, ay, bx, by] of [[sx0, sy0, sx1, sy1], [sx0, sy1, sx1, sy0]]) {
        const ln = document.createElementNS("http://www.w3.org/2000/svg", "line");
        ln.setAttribute("x1", ax); ln.setAttribute("y1", ay);
        ln.setAttribute("x2", bx); ln.setAttribute("y2", by);
        ln.setAttribute("class", "delstrike");
        ov.appendChild(ln);
      }
      const rj = (S.rowByKey[it.key] || {}).reject || {};
      badge(x1 * scale, y1 * scale, "rejbadge", "×",
            `오검출 표시 — ${rj.class || "삭제"}${rj.note ? " · " + rj.note : ""}`);
    }
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
      // hotfix38 — 식별 표기 **위에 글자**로도 말한다 (사용자 요구: "추가된 것은
      // 식별 표기 위에 label 을 add 로 표기").  링은 색·파선이고 글자는 셋째 단서다.
      // 값은 그리드와 같은 `rev.state` 에서 온다 — 두 벌을 두지 않는다.
      const tag = document.createElementNS("http://www.w3.org/2000/svg", "text");
      const fs = Math.max(9, Math.min(16, (y1 - y0) * scale * 0.45));
      tag.setAttribute("x", x0 * scale - pad);
      tag.setAttribute("y", y0 * scale - pad - 2);
      tag.setAttribute("font-size", fs);
      tag.setAttribute("class", "revtag " + (rev === "ADDED" ? "rev-added" : "rev-modified"));
      tag.textContent = rev === "ADDED" ? "ADD" : "MOD";
      tag.dataset.key = it.key;
      tag.dataset.rev = rev;
      const st = (S.rowByKey[it.key] || {}).rev || {};
      const tt = document.createElementNS("http://www.w3.org/2000/svg", "title");
      tt.textContent = rev === "ADDED"
        ? `${(S.rev || {}).compared_with || "직전 리비전"} 대비 추가` + (st.reason ? ` — ${st.reason}` : "")
        : `${(S.rev || {}).compared_with || "직전 리비전"} 대비 수정 — `
          + (st.basis === "AMBIGUOUS" ? (st.reason || "태그 변경 또는 추가 — 도면이 가르지 않음")
             : ((st.changed || []).map(c => `${c.field === "tag_no" ? "태그" : c.field}: ${c.was || "(없음)"} → ${c.now || "(없음)"}`).join(" · ") || "태그 변경"));
      tag.appendChild(tt);
      ov.appendChild(tag);
    }
    r.dataset.key = it.key;
    r.onclick = (ev) => {
      ev.stopPropagation();
      // 56회차 — Shift 를 누르고 누르면 **더한다**.  행이 아닌 것(제외 심볼)은
      // 고칠 SCOPE 칸 자체가 없으므로 묶음에 넣지 않는다.
      if (isAddClick(ev) && it.row !== false) { toggleMulti(it.key); return; }
      select(it.key, false, it);
      // 마크업 모드에서 기존 상자를 누르면 오검출 표시 대화상자다 ([D-3]).
      if (S.markup && it.row !== false) rejectDialog(it);
      // hotfix66 — 그 밖에는 상자 옆에 SCT · VENDOR · 둘 다 아님(식별 지우기) 판
      else if (it.row !== false) scopePop(it.key);
    };
    // Right-click on the symbol itself: the same dialog the grid opens, so the
    // reviewer reports from wherever they noticed it.
    r.oncontextmenu = (ev) => {
      ev.preventDefault(); ev.stopPropagation();
      // hotfix13 — 맥의 Ctrl + 클릭은 브라우저가 오른쪽 클릭으로 바꿔 보낸다
      // (왼쪽 단추 · ctrlKey).  사람이 뜻한 것은 신고가 아니라 더하기다.
      if (ev.ctrlKey && ev.button === 0) {
        if (it.row !== false) toggleMulti(it.key);
        return;
      }
      select(it.key, false, it);
      reportDialog({ rowKey: it.key, pageNo: S.page.page_no, fromDrawing: true });
    };
    ov.appendChild(r);
  }
  // hotfix59 — `x N` 라벨은 모든 상자 **위**에 둔다.  상자를 그리는 순서대로 두면 뒤에 그린
  // 큰 상자(밸브 울타리 · 묶음 버블)가 앞 행의 라벨을 덮어 눌러도 그 상자가 잡혔다
  // (자기검증 — AL NOUF1 p6 두 번째 라벨이 36×108 상자에 가려 눌리지 않았다).
  ov.querySelectorAll("g.qtytag").forEach(g => ov.appendChild(g));
  drawFromTo(ov, scale);
  drawPins(ov, scale);                    // hotfix76 — 위치 메모는 맨 위 (눌러야 하므로)
  buildOverlayLegend();
}

/* hotfix32 — 수량 라벨을 달 행.  행인 상자(제외 심볼 · 씰 · Typical 표식은 아니다)
 * 이고 그 행이 목록에 있을 때.  Q'ty 가 비어 있어도(승수 미정 — 검토 사유) 단다:
 * 빈 것도 사람이 채울 자리다. */
function qtyTagRow(it) {
  if (it.row === false || it.seal || it.typical || it.rejected) return null;
  const row = S.rowByKey[it.key];
  if (!row || row.deleted || row.removed) return null;
  return row;
}

function qtyEdited(row) {
  return !!(row.user && "qty" in row.user && row.user.qty !== null && row.user.qty !== undefined);
}

function drawQtyTag(ov, scale, it, row, stroke) {
  const NS = "http://www.w3.org/2000/svg";
  const [x0, y0, x1, y1] = it.rect;
  const qty = cellValue(row, "qty");
  const edited = qtyEdited(row);
  // hotfix66 — 고친 라벨에는 고친 사람 이름이 붙는다 (`x5 ✎홍길동`).  이름은 `edited_by` 하나에서 온다.
  const ed = edited ? editorOf(row, "qty") : null;
  const label = `x${qty === "" || qty === null || qty === undefined ? "?" : qty}${edited ? " ✎" + (ed ? ed.author : "") : ""}`;
  const fs = Math.max(9, Math.min(16, (y1 - y0) * scale * 0.55));
  // 한글(넓은 글자)은 한 칸을 다 쓴다 — 0.62 로만 세면 이름이 상자 밖으로 나간다 (hotfix66 자기검증)
  const em = [...label].reduce((a, ch) => a + (ch.charCodeAt(0) > 0x2e80 ? 1.0 : 0.62), 0);
  const w = em * fs + 6, h = fs * 1.35;
  const gx = x1 * scale + 3, gy = (y0 + y1) / 2 * scale - h / 2;
  const g = document.createElementNS(NS, "g");
  g.setAttribute("class", "qtytag" + (edited ? " edited" : "") + (S.sel === it.key ? " sel" : ""));
  g.dataset.key = it.key;
  const bg = document.createElementNS(NS, "rect");
  bg.setAttribute("x", gx); bg.setAttribute("y", gy);
  bg.setAttribute("width", w); bg.setAttribute("height", h);
  bg.setAttribute("rx", 3);
  bg.setAttribute("stroke", stroke);
  const t = document.createElementNS(NS, "text");
  t.setAttribute("x", gx + 3); t.setAttribute("y", gy + h * 0.76);
  t.setAttribute("font-size", fs);
  t.textContent = label;
  const e = row.evidence || {};
  const tip = document.createElementNS(NS, "title");
  tip.textContent = `Q'ty ${qty === "" ? "(비어 있음)" : qty}`
    + (edited ? ` — ${ed ? ed.author : "이름 없음"} 고침${ed && ed.at ? " · " + new Date(ed.at * 1000).toLocaleString("ko-KR", { hour12: false }) : ""} (도면 근거는 ${(row.ai || {}).qty ?? "없음"})` : "")
    + (e.qty_basis ? `\n근거: ${e.qty_basis}` : "")
    + "\n누르면 승수를 고칩니다 — 이 태그만 · 이 페이지 전체 · Shift 로 묶은 범위";
  g.appendChild(tip); g.appendChild(bg); g.appendChild(t);
  g.onclick = (ev) => {
    ev.stopPropagation();
    // hotfix59 — Shift 로 묶은 범위 안의 라벨을 누르면 그 범위의 승수를 한 번에 고친다.
    // 묶음 밖의 라벨을 Shift 로 누르면 상자와 같이 묶음에 더하거나 뺀다.
    if (isAddClick(ev)) { toggleMulti(it.key); return; }
    if (S.multi.size > 1 && S.multi.has(it.key)) { editQtyOnDrawing(row, g, { multi: true }); return; }
    select(it.key, false, it);
    editQtyOnDrawing(row, g);
  };
  ov.appendChild(g);
}

/* 도면 위에서 승수(Q'ty)를 고친다 — hotfix32 의 입력 상자를 hotfix59 에서 고르는 판으로 넓혔다.
 *
 * 사용자 요구: *"tag 의 오른쪽(x N)을 누르면 승수를 변경 · 해당 tag 만인지 해당 page 전체인지
 * 선택 · Shift 로 범위를 지정하고 누르면 범위에 선택된 항목의 승수를 변경 · 왼쪽 오른쪽 모두
 * 반영."*  적용 범위는 셋이고 고르는 판은 하나다:
 *   ① 이 태그만        — 누른 라벨의 행
 *   ② 이 페이지 전체    — 그 장의 행 전부 (`pageQtyRows` — 라벨이 서는 행과 같은 조건)
 *   ③ Shift 로 묶은 범위 — `S.multi` (56회차 묶음 · 띠 선택과 같은 묶음)
 * **저장은 한 행짜리와 같은 PATCH** (`field: "qty"`) 이고 작성자는 한 번만 묻는다 (56회차
 * 묶음 규율 · 편집 이력·검토 수가 두 벌이 되지 않게).  비우면 도면 값으로 되돌린다
 * (`db.set_user_value` 의 빈 값 규칙).  저장 뒤 목록(`renderGrid`)과 도면(`drawOverlay`)을
 * **같은 Q'ty 값** 에서 다시 그린다 — 라벨과 칸이 한 값을 말한다. */
async function applyQtyToRows(rows, value, what) {
  rows = rows.filter(r => String(cellValue(r, "qty") ?? "") !== value);
  if (!rows.length) { editNotice("바뀔 행이 없습니다 — 이미 그 승수입니다"); return; }
  const author = await askAuthor(`승수 x${value || "(도면 값)"} — ${what} · ${rows.length}행`);
  if (author === null) return;                       // 취소 — 한 행도 안 고친다
  // hotfix75 — 행마다 PATCH(46행이면 46번 왕복)를 요청 하나로.  같은 PATCH 칸(`field: "qty"`) · 같은 작성자.
  const out = await editRowsBulk(rows, "qty", () => value, author);
  if (!out) return;
  const done = rows.length - out.missing.length;
  updateBadge();
  renderGrid();                                       // 오른쪽 — 같은 Q'ty 값
  markMultiRows();
  drawOverlay();                                      // 왼쪽 — 라벨이 같은 값을 다시 읽는다
  const cur = S.sel && S.rowByKey[S.sel];
  if (S.multi.size) showMultiScope(); else if (cur) showEvidence(cur);
  _refreshPageMult();
  editNotice(value === ""
    ? `${what} ${done}행의 승수를 도면 값으로 되돌렸습니다`
    : `${what} ${done}행의 승수를 x${value} 로 바꿨습니다 — 도면 라벨과 목록에 같이 반영`);
}

/* hotfix65 — Q'ty 가 다른 길(라벨 · 목록 칸 · 도면 위 카드)로 바뀌어도 페이지별 승수 판의
 * '지금 xN' 이 같은 값을 말하게 한다. */
function _refreshPageMult() {
  const box = $("#mult-panel");
  if (box && !box.classList.contains("hidden") && box.querySelector(".pmult")) renderPageMult(box);
}

function pageQtyRows(pageNo) {
  return S.rows.filter(r => r.page_no === pageNo && !r.deleted && !r.removed && !r.delCand);
}

function closeQtyPop() {
  document.querySelectorAll(".qtypop").forEach(n => n.remove());
  if (closeQtyPop._off) { document.removeEventListener("pointerdown", closeQtyPop._off, true); closeQtyPop._off = null; }
}

function editQtyOnDrawing(row, anchor, opts = {}) {
  // 라벨을 누르면 `select` 가 오버레이를 다시 그려 누른 요소가 문서에서 빠진다 — 판이 화면
  // 왼쪽 위(0,0)에 떴다 (자기검증).  같은 행의 **지금 그려진** 라벨에 붙인다.
  const live = document.querySelector(`g.qtytag[data-key="${CSS.escape(row.key)}"]`);
  if (live) anchor = live;
  if (!anchor) return;
  closeQtyPop();
  const multi = opts.multi ? multiRows().filter(r => !r.deleted && !r.removed) : [];
  const page = pageQtyRows(row.page_no);
  const ab = anchor.getBoundingClientRect();
  const pop = document.createElement("div");
  pop.className = "qtypop";
  pop.setAttribute("role", "dialog");
  const now = cellValue(row, "qty");
  const head = multi.length
    ? `선택 ${multi.length}개의 승수 (Q'ty)`
    : `승수 (Q'ty) — ${escape(String(cellValue(row, "type") || ""))} ${escape(String(cellValue(row, "tag_no") || ""))}`;
  const buttons = multi.length
    ? `<button class="qp-b primary" data-scope="multi">선택 ${multi.length}개에 적용</button>`
    : `<button class="qp-b primary" data-scope="one">이 태그만</button>`
      + `<button class="qp-b" data-scope="page" title="p${row.page_no} 의 행 ${page.length}개 전부에 같은 승수를 적습니다">이 페이지 전체 (${page.length}행)</button>`;
  pop.innerHTML = `<div class="qp-h">${head}</div>`
    + `<div class="qp-row"><span class="qp-x">x</span><input class="qtyedit" type="number" min="0" step="1"></div>`
    + `<div class="qp-btns">${buttons}<button class="qp-b ghost" data-scope="cancel">취소</button></div>`
    + `<div class="qp-note muted small">지금 x${now === "" || now == null ? "?" : escape(String(now))} · Enter = ${multi.length ? "선택에 적용" : "이 태그만"} · Esc 취소 · 비우면 도면 값으로</div>`;
  document.body.appendChild(pop);
  const inp = pop.querySelector("input");
  inp.value = now ?? "";
  // 라벨 오른쪽에 붙이되 화면 밖으로 나가면 안쪽으로 접는다.
  const pw = pop.offsetWidth, ph = pop.offsetHeight;
  let left = ab.right + 6, top = ab.top - 4;
  if (left + pw > window.innerWidth - 8) left = Math.max(8, ab.left - pw - 6);
  if (top + ph > window.innerHeight - 8) top = Math.max(8, window.innerHeight - ph - 8);
  pop.style.left = `${left}px`; pop.style.top = `${top}px`;
  const go = async (scope) => {
    if (scope === "cancel") { closeQtyPop(); return; }
    const value = inp.value.trim();
    if (value !== "" && !/^\d+$/.test(value)) { inp.classList.add("bad"); inp.focus(); return; }
    const rows = scope === "multi" ? multi : scope === "page" ? page : [row];
    closeQtyPop();
    await applyQtyToRows(rows, value, scope === "multi" ? `선택 ${rows.length}개`
      : scope === "page" ? `p${row.page_no} 전체 ${rows.length}행` : "이 태그");
  };
  pop.querySelectorAll("button.qp-b").forEach(b => { b.onclick = () => go(b.dataset.scope); });
  inp.addEventListener("keydown", ev => {
    if (ev.key === "Enter") { ev.preventDefault(); go(multi.length ? "multi" : "one"); }
    if (ev.key === "Escape") { ev.preventDefault(); closeQtyPop(); }
  });
  // 판 밖을 누르면 닫는다 (저장하지 않는다 — 고르는 판이므로 범위를 고르지 않은 채 저장하지 않는다).
  closeQtyPop._off = (ev) => { if (!pop.contains(ev.target)) closeQtyPop(); };
  setTimeout(() => document.addEventListener("pointerdown", closeQtyPop._off, true), 0);
  inp.focus(); inp.select();
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
/* 드래그로 도면 옮기기 (12회차, 피드백 4장).
 *
 * `#stage` 는 `overflow: auto` 인 상자이고 `#wrap` 이 그 안에서 확대된다.
 * 그래서 옮기는 것은 좌표 변환이 아니라 **스크롤**이다 — 오버레이 좌표계를
 * 건드리지 않으므로 확대·검출 상자·클릭 판정이 전부 그대로다.
 *
 * 클릭과 드래그를 가르는 것은 **움직인 거리**다.  `PAN_SLOP` 이하로 움직였으면
 * 클릭으로 보고 계기를 고른다.  값 4px 은 임의값이 아니라 브라우저가 `click`
 * 을 취소하는 기본 문턱(대부분 3~5px)과 같은 자리에 둔 것이고, 이 값 하나만
 * 여기 있다.  마우스를 뗀 뒤 판정하므로 "누르자마자 선택" 이 사라지지 않는다.
 *
 * 오른쪽 버튼(미검출 신고)과 픽 모드는 건드리지 않는다 — 왼쪽 버튼만 본다. */
/* ---------------- 마크업 모드 (44회차) ----------------
 *
 * 빈 자리를 **드래그**하면 사각형이 되고, 그 사각형이 "누락 행" 이 된다.  좌표는
 * `sheetPoint` 그대로(표시 좌표 pt · 검출 rect 와 같은 좌표계).  저장 전에
 * 서버가 그 자리에서 별표·NOTES·낱말·같은 장의 수량을 **먼저 읽어** 제안하고
 * (§9 ①②), 사람은 채워진 값을 바꾸거나 빈칸을 적는다.  어느 칸이 도면 값이고
 * 어느 칸이 사람 값인지(`scope_source` · `qty_source`)를 같이 보낸다.
 * 기존 상자를 누르면 오검출 표시다 (`rejectDialog`).  팬은 이 모드에서 꺼진다. */
let _rubber = null;

$req("#markup-toggle").addEventListener("click", () => setMarkup(!S.markup));

function setMarkup(on) {
  S.markup = !!on;
  if (S.markup && S.picking) endPick();
  if (S.markup && S.pinMode) setPinMode(false);
  $("#stage").classList.toggle("markup", S.markup);
  $("#markup-toggle").classList.toggle("on", S.markup);
  $("#markup-toggle").setAttribute("aria-pressed", S.markup ? "true" : "false");
  updateMarkupNote();
  if (S.markup) prewarmMarkup();
}

/* 53회차 [G] — 마크업을 켜면 **그 장을 미리 읽어 둔다** (8차 피드백 s8:
 * *"마크업 이후 → 누락 행 추가까지의 시간이 너무 오래 걸린다"*).
 *
 * 값이 비싼 것이 아니라 **그 장을 처음 읽는 것**이 비싸다 (A1 장 약 5초:
 * 버블 윤곽 · 파선 버블 · 마크 · 패키지 상자).  한 번 읽으면 그 장 안에서는
 * 0.1초다 (실측 제안 5265 → 88ms · 행추가 199ms).  그래서 사람이 사각형을
 * 그리기 **전에** 읽어 둔다 — 마크업을 켜는 순간이 그 자리다.
 *
 * 새 서버 코드를 만들지 않는다: 제안 경로를 그대로 부르되 답을 버린다.
 * 캐시 열쇠가 같아야 뜻이 있으므로 **같은 엔드포인트**여야 한다.
 * 실패해도 조용하다 — 미리 읽기는 거들 뿐이고 못 해도 예전만큼 걸린다. */
let _prewarmed = null;
async function prewarmMarkup() {
  if (!S.job || !S.page) return;
  const tag = `${S.job.id}:${S.page.page_no}`;
  if (_prewarmed === tag) return;
  _prewarmed = tag;
  const n = $("#markup-note");
  const was = n ? n.textContent : "";
  if (n) n.textContent = "도면을 읽는 중… (처음 한 번만 걸립니다)";
  try {
    await fetch(`/jobs/${S.job.id}/markup/propose`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ page_no: S.page.page_no, rect: [0, 0, 1, 1] }) });
  } catch (e) { _prewarmed = null; }
  if (n && n.textContent.startsWith("도면을 읽는 중")) { n.textContent = was; updateMarkupNote(); }
}

function updateMarkupNote() {
  const n = $("#markup-note");
  if (!n) return;
  const m = S.markupSummary || {};
  const tail = (m.added || m.rejected)
    ? ` · 이 분석: 추가 ${m.added || 0}${m.scope_user ? ` (SCOPE 사람 값 ${m.scope_user}` : ""}${
        m.qty_user ? `${m.scope_user ? " · " : " ("}수량 사람 값 ${m.qty_user}` : ""}${
        (m.scope_user || m.qty_user) ? ")" : ""} · 오검출 표시 ${m.rejected || 0}`
    : "";
  n.textContent = S.markup
    ? `마크업: 빈 자리를 드래그하면 누락 행 · 상자를 누르면 오검출 표시${tail}`
    : (tail ? tail.slice(3) : "");
  n.classList.toggle("hidden", !S.markup && !tail);
}

$req("#stage").addEventListener("pointerdown", ev => {
  if (!(S.markup || S.ftMark || S.pinMode) || ev.button !== 0) return;
  // 상자는 자기 onclick — 단 From/To 범위를 긋는 중이거나 위치 메모를 다는 중이면 상자 위에서 시작해도 긋는다
  if (!S.ftMark && !S.pinMode && ev.target.tagName.toLowerCase() === "rect") return;
  const p = sheetPoint(ev);
  if (!p) return;
  _rubber = { x: ev.clientX, y: ev.clientY, p0: p, id: ev.pointerId, el: null };
  ev.preventDefault();
}, true);

$req("#stage").addEventListener("pointermove", ev => {
  if (!_rubber || ev.pointerId !== _rubber.id) return;
  const p = sheetPoint(ev);
  if (!p) return;
  const stage = $("#stage");
  if (!stage.hasPointerCapture(ev.pointerId)) stage.setPointerCapture(ev.pointerId);
  const ov = $("#ov");
  const scale = S.natural.w / (S.page.width || 1);
  if (!_rubber.el) {
    _rubber.el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    _rubber.el.setAttribute("class", "rubber");
    ov.appendChild(_rubber.el);
  }
  const [x0, y0, x1, y1] = normRect(_rubber.p0, p);
  _rubber.el.setAttribute("x", x0 * scale); _rubber.el.setAttribute("y", y0 * scale);
  _rubber.el.setAttribute("width", (x1 - x0) * scale);
  _rubber.el.setAttribute("height", (y1 - y0) * scale);
  ev.preventDefault();
}, true);

function normRect(a, b) {
  return [Math.min(a[0], b[0]), Math.min(a[1], b[1]),
          Math.max(a[0], b[0]), Math.max(a[1], b[1])];
}

async function _rubberEnd(ev) {
  if (!_rubber || ev.pointerId !== _rubber.id) return;
  const stage = $("#stage");
  if (stage.hasPointerCapture(ev.pointerId)) stage.releasePointerCapture(ev.pointerId);
  const r = _rubber; _rubber = null;
  if (r.el) r.el.remove();
  const p = sheetPoint(ev) || r.p0;
  const rect = normRect(r.p0, p);
  // hotfix76 — 위치 메모: 끌면 그 사각형, 누르기만 하면 그 점 (점 메모는 깃발만 선다)
  if (S.pinMode) {
    S.panned = true;
    const click = Math.abs(ev.clientX - r.x) <= PAN_SLOP && Math.abs(ev.clientY - r.y) <= PAN_SLOP;
    setPinMode(false);
    S.pinJust = Date.now();          // 뒤따르는 click 이 상자를 고르지 않게 (아래 capture 에서 삼킨다)
    pinDialog(click ? [r.p0[0], r.p0[1], r.p0[0], r.p0[1]] : rect);
    return;
  }
  // 드래그가 아니라 클릭이면(4px 이하 — 팬과 같은 문턱) 아무것도 만들지 않는다.
  if (Math.abs(ev.clientX - r.x) <= PAN_SLOP && Math.abs(ev.clientY - r.y) <= PAN_SLOP) {
    S.panned = true;          // 뒤따르는 click 이 선택을 지우지 않게
    return;
  }
  S.panned = true;
  if (S.ftMark) { await descMarkupEnd(rect); return; }
  await markupDialog(rect);
}
$req("#stage").addEventListener("pointerup", _rubberEnd, true);
$req("#stage").addEventListener("pointercancel", ev => {
  if (_rubber && ev.pointerId === _rubber.id) { if (_rubber.el) _rubber.el.remove(); _rubber = null; }
}, true);

const MARKUP_CLASSES = [
  ["MISSING", "㉡ 미검출 — 도면에 있는데 행이 없음"],
  ["FALSE_POSITIVE", "㉢ 오검출 — 행이 있는데 도면에 없음"],
  ["WRONG_VALUE", "㉣ 값 틀림 — 행은 맞는데 칸이 틀림"],
  ["UNKNOWN_SYMBOL", "미지정 심볼 — 범례에 없어 사람이 정함"],
  ["NOT_SUPPLY", "공급 대상 아님 — SCT 도 VENDOR 도 아님"],
  ["OTHER", "기타"],
];
const SCOPE_CHOICES = [SCOPE_DELIVERED, "VENDOR"];

function _sourceLine(src, evidence, what) {
  if (src === "DRAWING") return `<span class="src drawing">도면에서 읽음 — ${escape(evidence || "")}</span>`;
  return `<span class="src user">도면에서 못 읽음 — ${escape(evidence || `${what} 을(를) 직접 적으세요`)}</span>`;
}

async function markupDialog(rect) {
  const page = S.page;
  const body = { page_no: page.page_no, rect };
  let prop = {};
  try {
    const r = await fetch(`/jobs/${S.job.id}/markup/propose`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body) });
    if (r.ok) prop = await r.json();
    else prop = { error: (await r.json()).detail || r.statusText };
  } catch (e) { prop = { error: String(e) }; }
  const scopeEv = prop.scope_evidence || {};
  const scopeVal = prop.scope || "";
  const scopeOpts = [...new Set([...SCOPE_CHOICES, scopeVal].filter(Boolean))];
  const tabOpts = ["FIELD", "MOV", "BFV", "PNEUMATIC"];
  const tab0 = prop.tab || (S.tab === "ALL" || S.tab === "REVIEW" ? "FIELD" : S.tab);
  const words = (prop.words || []).map(w => w.text).filter(Boolean);
  openModal("누락 행 추가 — 마크업",
    `<p class="muted small">${escape(page.drawing_no || "(도면번호 없음)")} · p${page.page_no}
       · 사각형 (${rect.map(v => Math.round(v)).join(", ")})
       ${prop.error ? `<br><b class="bad">제안값을 읽지 못했습니다: ${escape(prop.error)}</b>` : ""}</p>
     <div class="mk-form">
       <label>산출물 <select id="mk-tab">${tabOpts.map(t => `<option${t === tab0 ? " selected" : ""}>${t}</option>`).join("")}</select></label>
       <label>Type <input id="mk-type" type="text" value="${escape(prop.type || "")}" placeholder="예: PIT">
         ${prop.anchor ? `<span class="src drawing">사각형 안 낱말 ${escape(prop.anchor)} — 앵커 사전에 있음</span>`
           : `<span class="src user">사각형 안 낱말: ${escape(words.slice(0, 8).join(" ") || "없음")}${(prop.candidates || []).length > 1 ? ` · 앵커 후보 ${escape(prop.candidates.join(", "))} — 하나를 고르세요` : ""}</span>`}</label>
       <label>SCOPE <select id="mk-scope"><option value="">(빈칸)</option>${
         scopeOpts.map(v => `<option value="${escape(v)}"${v === scopeVal ? " selected" : ""}>${escape(v)}</option>`).join("")}</select>
         <input id="mk-scope-name" type="text" placeholder="VENDOR 이면 공급자 이름 (선택)" class="mini">
         ${_sourceLine(prop.scope_source, scopeEv.text, "SCOPE")}</label>
       <label>Q'ty <input id="mk-qty" type="number" min="0" step="1" value="${prop.qty ?? ""}">
         ${_sourceLine(prop.qty_source, prop.qty_basis, "수량")}</label>
       <label>SYSTEM <input id="mk-system" type="text" value="${escape(prop.system || "")}" placeholder="그 장의 도면 제목">
         ${_sourceLine(prop.system_source, prop.system_basis, "SYSTEM")}</label>
       <label>TAG No. <input id="mk-tag" type="text" value="${escape(prop.tag_no || "")}" placeholder="예: 00EGD21CP501"
         list="mk-tag-cands"><datalist id="mk-tag-cands">${(prop.tag_candidates || []).map(t => `<option value="${escape(t)}">`).join("")}</datalist>
         ${_sourceLine(prop.tag_source, prop.tag_basis, "TAG")}</label>
       <label>Description <input id="mk-desc" type="text" placeholder="(선택)"></label>
       <label>분류 <select id="mk-class">${MARKUP_CLASSES.map(([v, l]) => `<option value="${v}"${v === "MISSING" ? " selected" : ""}>${escape(l)}</option>`).join("")}</select></label>
       <label>사유 <input id="mk-note" type="text" placeholder="왜 프로그램이 못 읽었나 / 무엇이 맞나 — 한 줄"></label>
       ${vocCheckHtml("mk")}
       <label>작성자 <input id="mk-author" type="text" value="${escape(currentAuthor())}" placeholder="이름 (자칭)"></label>
     </div>
     <div class="modal-actions">
       <button id="mk-cancel" class="ghost">취소</button>
       <button id="mk-save">행 추가</button>
     </div>`);
  $("#mk-cancel").onclick = closeModal;
  $("#mk-save").onclick = guarded(async () => {      // hotfix74 — 두 번 눌러도 행은 하나
    if (!vocReasonOk("mk")) return;
    const scopeSel = $("#mk-scope").value;
    const name = $("#mk-scope-name").value.trim();
    const scope = scopeSel === "VENDOR" && name ? `VENDOR(${name})` : scopeSel;
    const qtyRaw = $("#mk-qty").value.trim();
    const values = {};
    const type = $("#mk-type").value.trim();
    if (type) values.type = type;
    if (scope) values.scope = scope;
    if (qtyRaw !== "") values.qty = Number(qtyRaw);
    const desc = $("#mk-desc").value.trim();
    if (desc) { values.description = desc; values.description_grade = "USER_ENTERED"; }
    // hotfix14 — SYSTEM 은 그 장의 값, TAG 는 사각형 안 코드 (제안값 · 사람이 고칠 수 있다)
    const system = $("#mk-system").value.trim();
    if (system) values.system = system;
    const tagNo = $("#mk-tag").value.trim();
    if (tagNo) values.tag_no = tagNo;
    const author = $("#mk-author").value.trim();
    rememberAuthor(author);
    // 출처: 제안값을 그대로 두었으면 도면, 바꿨거나 빈칸을 채웠으면 사람.
    const scope_source = (prop.scope_source === "DRAWING" && scope === scopeVal) ? "DRAWING" : "USER";
    const qty_source = (prop.qty_source === "DRAWING" && qtyRaw !== "" && Number(qtyRaw) === prop.qty) ? "DRAWING" : "USER";
    const payload = {
      page_no: page.page_no, tab: $("#mk-tab").value, drawing_no: page.drawing_no || "",
      rect, values, author, scope_source, qty_source,
      reason_class: $("#mk-class").value, note: $("#mk-note").value.trim(),
      proposal: { type: prop.type || "", anchor: prop.anchor || "", scope: scopeVal,
                  scope_source: prop.scope_source || "", scope_evidence: scopeEv,
                  qty: prop.qty ?? null, qty_source: prop.qty_source || "",
                  qty_basis: prop.qty_basis || "", words: words.slice(0, 20),
                  system: prop.system || "", system_source: prop.system_source || "",
                  tag_no: prop.tag_no || "", tag_source: prop.tag_source || "",
                  tag_candidates: prop.tag_candidates || [] },
    };
    const r = await fetch(`/jobs/${S.job.id}/rows`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload) });
    if (!r.ok) { alert((await r.json()).detail || "행 추가 실패"); return; }
    const out = await r.json();
    if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
    const vocId = $("#mk-voc").checked ? await vocSend({
      source: "MARKUP_ADD", category: payload.reason_class, reason: payload.note, author,
      page_no: page.page_no, drawing_no: page.drawing_no || "", rect, row_keys: [out.key],
      markup: { tab: payload.tab, values, scope_source, qty_source, proposal: payload.proposal } }) : "";
    closeModal();
    clearFiltersForNewRow();
    await refreshRows(out.key, { toGrid: true, keys: [out.key] });
    updateBadge();
    // 빈 SCOPE 는 "판정한 적 없음(옛 분석)" 이 아니라 **사람이 비워 둔 것**이다 — 문장은
    // `scopeFacts` 한 곳이 쓴다 (근거 패널과 같은 문장).
    const facts = scopeFacts(scope, { manualBlank: true });
    const formLine = facts.formLine;
    editNotice(`추가했습니다 (${out.stable_id ? `ID ${out.stable_id}` : out.id_note || "ID 없음"}) · `
      + `SCOPE ${scope || "(빈칸)"} [${scope_source === "DRAWING" ? "도면" : "사람"}] · `
      + `Q'ty ${qtyRaw === "" ? "(빈칸)" : qtyRaw} [${qty_source === "DRAWING" ? "도면" : "사람"}] · `
      + `발주처 양식에 ${formLine}` + (vocId ? ` · VOC ${vocId} 접수` : ""), "in");
  });
  $("#mk-type").focus();
}

/* 오검출 표시 — 기존 상자를 마크업 모드에서 눌렀을 때 ([D-3] · [D-4]).
 * 행은 지워지지 않는다.  Excel 제외는 선택이고 되돌릴 수 있다. */
function rejectDialog(it) {
  const row = S.rowByKey[it.key];
  if (!row) return;
  const already = row.removed || (row.reject && Object.keys(row.reject).length);
  openModal("오검출 표시 — 이 상자",
    `<p class="muted small">${escape(row.drawing_no || "")} · p${row.page_no} · ${escape(row.values.type || row.values.valve_type || "")}
       · (${(row.rect || []).map(v => Math.round(v)).join(", ")})
       ${already ? `<br><b>이미 표시된 행입니다 — ${escape((row.reject || {}).class || "삭제")} ${escape((row.reject || {}).note || "")}</b>` : ""}</p>
     <div class="mk-form">
       <label>사유 <select id="rj-class">${MARKUP_CLASSES.filter(([v]) => v !== "MISSING").map(([v, l]) => `<option value="${v}">${escape(l)}</option>`).join("")}</select></label>
       <div id="rj-wrong" class="hidden">
         <label>칸 <select id="rj-field">${["type", "qty", "scope", "system", "valve_type", "tag_no", "description"].map(f => `<option>${f}</option>`).join("")}</select></label>
         <label>올바른 값 <input id="rj-value" type="text"></label>
         <p class="muted small">값 틀림은 행을 빼지 않고 그 칸을 고칩니다 — 편집 이력에 남고 Excel 에는 고친 값이 나갑니다.</p>
       </div>
       <label id="rj-exclude-wrap"><input id="rj-exclude" type="checkbox" checked> Excel 에서 제외 (행은 화면에 남습니다)</label>
       <label>사유 <input id="rj-note" type="text" placeholder="왜 틀렸나 — 한 줄"></label>
       ${vocCheckHtml("rj")}
       <label>작성자 <input id="rj-author" type="text" value="${escape(currentAuthor())}" placeholder="이름 (자칭)"></label>
     </div>
     <div class="modal-actions">
       ${already ? `<button id="rj-restore" class="ghost">되돌리기</button>` : ""}
       <button id="rj-cancel" class="ghost">취소</button>
       <button id="rj-save">표시</button>
     </div>`);
  const cls = $("#rj-class");
  const sync = () => {
    const wrong = cls.value === "WRONG_VALUE";
    $("#rj-wrong").classList.toggle("hidden", !wrong);
    $("#rj-exclude-wrap").classList.toggle("hidden", wrong);
    $("#rj-save").textContent = wrong ? "칸 고치기" : "표시";
  };
  cls.onchange = sync; sync();
  $("#rj-cancel").onclick = closeModal;
  if ($("#rj-restore")) $("#rj-restore").onclick = async () => {
    await fetch(`/jobs/${S.job.id}/rows/${row.key}/restore`, { method: "POST" });
    closeModal(); await refreshRows(row.key, { keys: [row.key] });
  };
  $("#rj-save").onclick = async () => {
    if (!vocReasonOk("rj")) return;
    const author = $("#rj-author").value.trim();
    rememberAuthor(author);
    const note = $("#rj-note").value.trim();
    const wantVoc = $("#rj-voc").checked;
    const sendVoc = (extra) => wantVoc ? vocSend(Object.assign({
      source: "MARKUP_REJECT", category: cls.value, reason: note, author,
      page_no: row.page_no, drawing_no: row.drawing_no || "", rect: row.rect, row_keys: [row.key] }, extra)) : "";
    if (cls.value === "WRONG_VALUE") {
      const field = $("#rj-field").value, value = $("#rj-value").value.trim();
      if (!value) { alert("올바른 값을 적어 주세요."); return; }
      const r = await fetch(`/jobs/${S.job.id}/rows/${row.key}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field, value, author, reason: `WRONG_VALUE: ${note}` }) });
      if (!r.ok) { alert((await r.json()).detail || "저장 실패"); return; }
      const vocId = await sendVoc({ markup: { field, value } });
      closeModal(); await refreshRows(row.key, { keys: [row.key] });
      if (vocId) editNotice(`${field} 을(를) 고쳤습니다 · VOC ${vocId} 접수`, "in");
      return;
    }
    const q = new URLSearchParams({ reason: note, reason_class: cls.value, author,
                                    exclude: $("#rj-exclude").checked ? "true" : "false" });
    const r = await fetch(`/jobs/${S.job.id}/rows/${row.key}?${q}`, { method: "DELETE" });
    if (!r.ok) { alert("표시 실패"); return; }
    const out = await r.json();
    if (out.feedback_count !== undefined) S.feedback = out.feedback_count;
    const vocId = await sendVoc({ markup: { exclude: $("#rj-exclude").checked } });
    closeModal();
    await refreshRows(out.dropped ? null : row.key, { keys: [row.key] });
    if (vocId) { editNotice(`표시했습니다 · VOC ${vocId} 접수 — 개발팀 함에 쌓였습니다`, "in"); return; }
    if (cls.value === "UNKNOWN_SYMBOL") {
      editNotice("미지정 심볼로 표시했습니다 — 무엇으로 볼지는 [심볼] 화면에서 등록합니다", "unjudged");
    } else {
      editNotice($("#rj-exclude") && $("#rj-exclude").checked
        ? "오검출로 표시했습니다 — Excel 에서 빠집니다 (되돌릴 수 있습니다)"
        : "오검출 의심으로 표시했습니다 — Excel 에는 그대로 나갑니다", "out");
    }
  };
}

/* 같은 마크업을 다른 장에도 — **제안만** 한다 (31회차 규율).  장마다 서버가
 * 다시 읽어 제안하고 사람이 고른 장에만 넣는다.  자동 복제가 아니다. */
async function markupElsewhere(row) {
  const pages = S.pages.filter(p => p.in_scope && p.page_no !== row.page_no && p.page_kind === "PID");
  if (!pages.length) { alert("다른 분석 대상 장이 없습니다."); return; }
  const mk = (row.evidence || {}).markup || {};
  openModal("같은 마크업을 다른 장에도",
    `<p class="muted small">고른 장마다 같은 자리 (${(row.rect || []).map(v => Math.round(v)).join(", ")}) 에
       같은 값(Type ${escape(row.values.type || "")} · Description)으로 행을 만듭니다.
       SCOPE 와 Q'ty 는 **그 장에서 다시 읽어** 채우고, 못 읽으면 이 행의 값을 사람 값으로 둡니다.</p>
     <div class="mk-pages">${pages.map(p => `<label><input type="checkbox" value="${p.page_no}"> p${p.page_no} ${escape(p.drawing_no || "")}</label>`).join("")}</div>
     <div class="modal-actions"><button id="me-cancel" class="ghost">취소</button><button id="me-save">고른 장에 추가</button></div>`);
  $("#me-cancel").onclick = closeModal;
  $("#me-save").onclick = async () => {
    const chosen = [...document.querySelectorAll(".mk-pages input:checked")].map(c => +c.value);
    if (!chosen.length) { alert("장을 고르세요."); return; }
    let made = 0, lastKey = null; const madeKeys = [];
    for (const pno of chosen) {
      const pg = S.pages.find(p => p.page_no === pno);
      let prop = {};
      try {
        const r = await fetch(`/jobs/${S.job.id}/markup/propose`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ page_no: pno, rect: row.rect }) });
        if (r.ok) prop = await r.json();
      } catch (e) { prop = {}; }
      // SYSTEM · TAG 는 **그 장의** 것이다 — 원래 행의 값을 복사하면 다른 장에 남의
      // 도면 제목과 남의 태그가 붙는다 (hotfix14).
      const values = { ...Object.fromEntries(Object.entries(row.values).filter(([k, v]) =>
        v !== null && v !== "" && !["scope", "qty", "system", "tag_no"].includes(k))) };
      const scope = prop.scope_source === "DRAWING" && prop.scope ? prop.scope : (row.values.scope || "");
      const qty = prop.qty_source === "DRAWING" && prop.qty != null ? prop.qty : row.values.qty;
      if (scope) values.scope = scope;
      if (qty !== null && qty !== undefined && qty !== "") values.qty = qty;
      if (prop.system) values.system = prop.system;
      if (prop.tag_source === "DRAWING" && prop.tag_no) values.tag_no = prop.tag_no;
      const r2 = await fetch(`/jobs/${S.job.id}/rows`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ page_no: pno, tab: row.tab, drawing_no: pg.drawing_no || "",
          rect: row.rect, values, author: mk.author || lastAuthor(),
          scope_source: prop.scope_source === "DRAWING" && prop.scope ? "DRAWING" : "USER",
          qty_source: prop.qty_source === "DRAWING" && prop.qty != null ? "DRAWING" : "USER",
          reason_class: mk.class || "MISSING", note: `p${row.page_no} 마크업에서 같이 적용`,
          proposal: prop.error ? {} : { type: prop.type, scope: prop.scope, scope_source: prop.scope_source,
                                        qty: prop.qty, qty_source: prop.qty_source, qty_basis: prop.qty_basis } }) });
      if (r2.ok) { made++; lastKey = (await r2.json()).key; madeKeys.push(lastKey); }
    }
    closeModal();
    await refreshRows(lastKey, { keys: madeKeys });
    editNotice(`${made}장에 추가했습니다 — 장마다 SCOPE·Q'ty 출처는 근거 패널에 있습니다`, "in");
  };
}

/* 피드백 내보내기 — 서버가 zip 을 만들고 브라우저가 받는다. */
$req("#feedback-export").addEventListener("click", () => {
  if (!S.job) return;
  const by = window.prompt("내보내는 사람 이름 (자칭 · 비워도 됩니다)", lastAuthor()) ;
  if (by === null) return;
  rememberAuthor(by.trim());
  downloadUrl(`/jobs/${S.job.id}/feedback_export?by=${encodeURIComponent(by.trim())}`, "feedback.zip");
});

/* 56회차 — **Shift 를 누른 채 끌면 그 안의 검출이 전부 묶인다.**
 *
 * 요구: *"마우스 왼쪽 누르고 블록을 지정하면 식별된 계기들이 다 선택될 수
 * 있도록"*.  그냥 끄는 것은 **팬**이고 마크업 모드의 끌기는 **누락 행**이라
 * 둘 다 이미 임자가 있다.  그래서 Shift 를 쓴다 — Shift + 클릭이 "더한다" 인
 * 것과 같은 뜻이고, 손가락 하나로 둘을 익힌다.
 *
 * 무엇이 잡히는가: **지금 화면에 보이는 것**이다.  띠와 겹치는 상자 중
 * `itemVisible`(범례에서 켠 층)을 지나고 행인 것(`row !== false`)만 — 화면에서
 * 꺼 둔 층이 조용히 묶이면 사람이 고른 것과 바뀌는 것이 달라진다.
 * 겹치기(교차)로 잡는다 — CAD 의 crossing window 와 같고, 상자가 작아 완전히
 * 감싸려면 띠를 지나치게 크게 그려야 한다.
 */
let _band = null;

/* 56회차 hotfix12 — **Shift + 누르기는 브라우저에게도 뜻이 있다.**  기본 동작은
 * "선택을 여기까지 넓힌다" 여서, 도면 위에서 누르면 그림(#sheet)과 오버레이가
 * 통째로 선택되어 파랗게 칠해졌다 (현장 캡처: 장 전체가 파랗고 검출 상자가 안
 * 보였다).  우리 띠·묶음과는 무관한 **브라우저 선택 표시**였다.
 * 막는 자리는 mousedown 하나다 — pointerdown 을 막으면 click(더하기)이 안 온다.
 * 이미 걸린 선택은 지운다.  그리드 행도 같다 (Shift + 클릭이 표 글자를 긁는다). */
function _noNativeShiftSelect(ev) {
  // hotfix13 — Ctrl 도 같다: Firefox 는 Ctrl + 누르기로 표 칸을 파랗게 고른다.
  if (!isAddClick(ev) || ev.button !== 0) return;
  const t = ev.target;
  if (t && t.closest && t.closest("input, textarea, select, [contenteditable]")) return;
  ev.preventDefault();
  const sel = window.getSelection && window.getSelection();
  if (sel && sel.rangeCount) sel.removeAllRanges();
}
$req("#stage").addEventListener("mousedown", _noNativeShiftSelect, true);
$req("#grid").addEventListener("mousedown", _noNativeShiftSelect, true);

$req("#stage").addEventListener("pointerdown", ev => {
  if (ev.button !== 0 || !ev.shiftKey || S.markup || S.ftMark || S.picking || !S.page) return;
  // ⚠ 상자 위에서 시작해도 띠를 연다.  붐비는 장에서는 빈 자리를 찾기가 더
  // 어렵고, 처음 판이 상자 위를 빼는 바람에 "Shift 끌기가 안 된다" 로 보였다.
  // 끌지 않았으면(4px 이하) 아무 것도 하지 않으므로 Shift + 클릭(더하기)은
  // 그대로다 — `_bandEnd` 가 그때 `S.panned` 도 세우지 않는다.
  const p = sheetPoint(ev);
  if (!p) return;
  _band = { x: ev.clientX, y: ev.clientY, p0: p, id: ev.pointerId, el: null };
  // preventDefault 는 여기서 하지 않는다 — 클릭(더하기)이 막힌다.
}, true);

$req("#stage").addEventListener("pointermove", ev => {
  if (!_band || ev.pointerId !== _band.id) return;
  const p = sheetPointClamped(ev);
  if (!p) return;
  const stage = $("#stage");
  if (!stage.hasPointerCapture(ev.pointerId)) stage.setPointerCapture(ev.pointerId);
  const scale = S.natural.w / (S.page.width || 1);
  if (!_band.el) {
    _band.el = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    _band.el.setAttribute("class", "band");
    $("#ov").appendChild(_band.el);
  }
  const [x0, y0, x1, y1] = normRect(_band.p0, p);
  _band.el.setAttribute("x", x0 * scale); _band.el.setAttribute("y", y0 * scale);
  _band.el.setAttribute("width", (x1 - x0) * scale);
  _band.el.setAttribute("height", (y1 - y0) * scale);
  ev.preventDefault();
}, true);

function _bandEnd(ev) {
  if (!_band || ev.pointerId !== _band.id) return;
  const stage = $("#stage");
  if (stage.hasPointerCapture(ev.pointerId)) stage.releasePointerCapture(ev.pointerId);
  const b = _band; _band = null;
  if (b.el) b.el.remove();
  const tiny = Math.abs(ev.clientX - b.x) <= PAN_SLOP
            && Math.abs(ev.clientY - b.y) <= PAN_SLOP;
  if (tiny) return;                    // 끌지 않았으면 띠가 아니다 — 클릭을 살린다
  S.panned = true;                     // 뒤따르는 click 이 선택을 지우지 않게
  const [x0, y0, x1, y1] = normRect(b.p0, sheetPointClamped(ev) || b.p0);
  let added = 0;
  for (const it of overlayItems(S.page)) {
    if (it.row === false || !itemVisible(it)) continue;
    const [a0, c0, a1, c1] = it.rect;
    if (a1 < x0 || a0 > x1 || c1 < y0 || c0 > y1) continue;   // 안 겹친다
    if (!S.multi.has(it.key)) { S.multi.add(it.key); added++; }
  }
  // 띠로 하나만 잡혔으면 그것은 묶음이 아니라 그 행을 고른 것이다.
  if (S.multi.size === 1) {
    const only = [...S.multi][0];
    S.multi.clear();
    const row = S.rows.find(r => r.key === only);
    if (row) select(only, false);
    return;
  }
  syncSel();
  drawOverlay();
  markMultiRows();
  if (S.multi.size) showMultiScope();
  editNotice(added
    ? `띠 안의 ${added}개를 묶었습니다 — 모두 ${S.multi.size}개`
    : "띠 안에 고를 것이 없습니다", added ? "in" : "out");
}
$req("#stage").addEventListener("pointerup", _bandEnd, true);
$req("#stage").addEventListener("pointercancel", ev => {
  if (_band && ev.pointerId === _band.id) {
    if (_band.el) _band.el.remove();
    _band = null;
  }
}, true);

const PAN_SLOP = 4;
let _pan = null;

$req("#stage").addEventListener("pointerdown", ev => {
  // 56회차 — Shift 를 누른 채 끄는 것은 팬이 아니라 **선택 띠**다.
  if (ev.button !== 0 || S.picking || S.markup || S.ftMark || ev.shiftKey) return;
  const stage = $("#stage");
  _pan = { x: ev.clientX, y: ev.clientY, moved: 0,
           sl: stage.scrollLeft, st: stage.scrollTop, id: ev.pointerId };
});

$req("#stage").addEventListener("pointermove", ev => {
  if (!_pan || ev.pointerId !== _pan.id) return;
  const dx = ev.clientX - _pan.x, dy = ev.clientY - _pan.y;
  _pan.moved = Math.max(_pan.moved, Math.abs(dx), Math.abs(dy));
  if (_pan.moved <= PAN_SLOP) return;
  const stage = $("#stage");
  if (!stage.hasPointerCapture(ev.pointerId)) {
    stage.setPointerCapture(ev.pointerId);
    stage.classList.add("panning");
  }
  ev.preventDefault();
  stage.scrollLeft = _pan.sl - dx;
  stage.scrollTop = _pan.st - dy;
});

function _panEnd(ev) {
  if (!_pan) return;
  const stage = $("#stage");
  if (stage.hasPointerCapture(ev.pointerId)) stage.releasePointerCapture(ev.pointerId);
  stage.classList.remove("panning");
  // 끌었으면 그 다음 `click` 은 선택이 아니다 - 삼켜서 계기가 안 바뀌게 한다.
  S.panned = _pan.moved > PAN_SLOP;
  _pan = null;
}
$req("#stage").addEventListener("pointerup", _panEnd);
$req("#stage").addEventListener("pointercancel", _panEnd);

$req("#stage").addEventListener("click", ev => {
  if (S.panned) { S.panned = false; return; }
  if (S.picking) {
    const p = sheetPoint(ev);
    endPick();
    if (p) createRow(p);
    return;
  }
  // Clicking the sheet itself, away from any box, clears the selection.
  // 더하기 키를 누른 채 빗맞힌 것은 "비운다" 가 아니다 — 묶음을 지키고 넘긴다.
  if (isAddClick(ev)) return;
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
/* hotfix12 — 띠의 **끝**은 그림 밖으로 나가도 가장자리에 붙는다.  `sheetPoint` 는
 * 밖이면 null 이고, 그 null 이 띠를 시작점 하나로 줄여 "띠 안에 고를 것이
 * 없습니다" 가 떴다 (도면 가장자리까지 끌면 손이 그림 밖에서 떨어지기 쉽다).
 * 시작점은 여전히 그림 안이어야 한다 — 그것은 `sheetPoint` 가 지킨다. */
function sheetPointClamped(ev) {
  const img = $("#sheet");
  if (!img.naturalWidth || !S.page) return null;
  const box = img.getBoundingClientRect();
  const fx = Math.min(1, Math.max(0, (ev.clientX - box.left) / box.width));
  const fy = Math.min(1, Math.max(0, (ev.clientY - box.top) / box.height));
  return [fx * S.page.width, fy * S.page.height];
}
document.addEventListener("keydown", ev => {
  if (ev.key !== "Escape" || ev.target.isContentEditable) return;
  // hotfix64 — 고른 것이 없을 때의 Esc 는 전체화면에서 나간다 (고른 것이 있으면 먼저 그것을 푼다)
  if (!S.sel && document.body.classList.contains("pid-full")) { setFull(false); return; }
  deselect();
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

/* 분석 취소 (12회차).
 *
 * 서버는 표시만 하고, 실제로 멈추는 것은 진행 보고 콜백이다 — 그래서 누른
 * 직후가 아니라 **지금 읽는 장이 끝나는 순간** 멈춘다.  한 장이 0.3초쯤이므로
 * 사람이 기다린다고 느낄 시간은 아니고, 그 사이에 DB 에 쓰이는 것은 진행률뿐
 * 이라 저장된 결과가 반쯤 남는 일이 없다. */
$req("#prog-cancel").addEventListener("click", async () => {
  const id = S.watching;
  if (!id) return;
  const btn = $("#prog-cancel");
  btn.disabled = true;
  // 즉시 멈추지 않는다는 것을 그대로 적는다.  취소는 진행 보고에서만 걸리므로
  // 지금 돌고 있는 계산이 끝나야 듣는다 — 도면을 읽는 중이면 1초 안쪽이고,
  // 치수 재기의 뒤쪽 구간(실측 129초)에서는 그 계산이 끝날 때까지 기다린다.
  btn.textContent = "취소하는 중 — 지금 단계가 끝나면 멈춥니다";
  try {
    const r = await fetch(`/jobs/${id}/cancel`, { method: "POST" });
    if (!r.ok) {
      alert((await r.json()).detail || "취소하지 못했습니다");
      btn.disabled = false; btn.textContent = "분석 취소";
    }
  } catch (e) {
    btn.disabled = false; btn.textContent = "분석 취소";
  }
});

/* hotfix15 — **Excel 은 지금의 데이터로 나간다.**  요구: *"마크업으로 추가된 항목은
 * excel 에 나와야 하며, 취소/삭제된 항목은 excel 에서 삭제되어야 한다 · 사용자가 변경한
 * Scope · Description · 수량도 모두 반영"*.
 * 서버는 처음부터 그렇게 쓰고 있었다 — 스냅샷은 사람 편집이 덮은 값(`merged_rows`)을
 * 담고 지운 행(`removed`)을 뺀다.  **어긋난 곳은 화면**이었다: 검토 완료를 체크한
 * 순간 찍은 스냅샷을 Excel 단추가 계속 내려받아, 그 뒤의 편집·삭제·마크업이 파일에
 * 없었다.  이제 체크 뒤에 데이터가 바뀌면(행을 바꾸는 요청이 성공하면) 스냅샷이 낡았다고
 * 적고, Excel 단추가 같은 조건으로 **새로 찍은 뒤** 내려받는다. */
S.snapParams = null;
S.snapStale = false;

async function takeSnapshot(params) {
  const r = await fetch(`/jobs/${S.job.id}/snapshot`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(Object.assign({ label: new Date().toISOString() }, params)),
  });
  if (!r.ok) { alert((await r.json()).detail || "스냅샷 실패"); return null; }
  const out = await r.json();
  S.revision = out.revision_id;
  S.snapStale = false;
  window.__rev = out.revision_id;      // read by tests/test_ui_edits.py
  $("#excel").textContent = `Excel 출력 (rev ${out.revision_id}, ${out.rows}행`
    + (params.hold_review ? ", 검토 보류" : "") + ")";
  return out;
}

function markSnapshotStale() {
  if (!S.revision || S.snapStale) return;
  S.snapStale = true;
  $("#excel").textContent = "Excel 출력 (편집 반영 — 누르면 새로 만듭니다)";
}

// 행을 바꾸는 요청은 여러 곳에서 나간다 (칸 편집 · 공급 주체 · 삭제 · 되돌리기 · 마크업 ·
// ＋행 · 복사 · 승수 · FROM/TO 확정).  한 곳에서 본다 — 곳마다 부르면 하나를 빠뜨린다.
const _rawFetch = window.fetch.bind(window);
const _MUTATES = /\/jobs\/[^/]+\/(rows|axis|axis_overrides|deleted|review|multipliers|sheet_numbers|titleblock)(\/|\?|$)/;
window.fetch = (url, opts) => {
  const p = _rawFetch(url, opts);
  const method = String((opts && opts.method) || "GET").toUpperCase();
  if (method !== "GET" && _MUTATES.test(String(url))) {
    p.then(r => { if (r.ok) markSnapshotStale(); }).catch(() => {});
  }
  return p;
};

$req("#gate-check").addEventListener("change", async ev => {
  $("#excel").disabled = !ev.target.checked;
  if (!ev.target.checked) { S.snapParams = null; return; }
  const origins = chosenOrigins();
  if (S.showOrigin && !origins.length) {
    alert("귀속을 하나 이상 선택하세요."); ev.target.checked = false; return;
  }
  const drawings = [...document.querySelectorAll(".drawing:checked")].map(c => c.value);
  if (!drawings.length) {
    alert("도면을 하나 이상 선택하세요."); ev.target.checked = false; return;
  }
  const hold = !!($("#hold-review") || {}).checked;
  S.snapParams = { origins, drawings, hold_review: hold };
  const out = await takeSnapshot(S.snapParams);
  if (!out) { ev.target.checked = false; $("#excel").disabled = true; return; }
  // Say what is still open, and do not stand in the way.  Whether an unanswered
  // question is a reason to hold the workbook back is the reviewer's call - but
  // they should not learn about it from the client.  A blocking dialog was tried
  // and rejected: it turns "you should know" into "you may not proceed".
  showOpenReview();
  $("#excel").disabled = false;
});

$req("#excel").addEventListener("click", async () => {
  if (!S.revision) return;
  if (S.snapStale && S.snapParams) {
    const out = await takeSnapshot(S.snapParams);
    if (!out) return;
    editNotice(`체크 뒤의 편집·삭제·추가를 반영해 스냅샷을 새로 만들었습니다 (rev ${out.revision_id} · ${out.rows}행)`, "in");
  }
  // hotfix74 — 예전에는 `location.href` 로 바로 갔다.  서버가 400(양식 없음 · 깨진 양식)을 내면 브라우저가
  // **이 화면을 떠나 JSON 글자만 보여 줬다** (돌발상황 시뮬레이션).  받아 보고, 되면 내려받고 아니면 말한다.
  await downloadUrl(`/revisions/${S.revision}/excel`, `rev${S.revision}_deliverables.zip`, $("#excel"));
});

/* hotfix74 — 내려받기 한 곳.  `location.href` 로 바로 가면 서버가 400(양식 없음 · 깨진 양식)을 낼 때
 * 브라우저가 **이 화면을 떠나 JSON 글자만** 보여 줬다 (돌발상황 시뮬레이션).  받아 보고, 되면 내려받고,
 * 아니면 서버 문장을 그대로 말한다.  `btn` 을 주면 받는 동안 "만드는 중…" 으로 묶어 둔다. */
async function downloadUrl(url, fallbackName, btn) {
  const label = btn ? btn.textContent : "";
  if (btn) { btn.disabled = true; btn.textContent = "만드는 중…"; }
  try {
    const r = await fetch(url);
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      const d = j.detail;
      const msg = typeof d === "string" ? d
        : (d && d.error ? d.error + ((d.skipped || []).length
            ? "\n\n건너뛴 산출물:\n" + d.skipped.map(x => `· ${x.kind || ""} ${x.reason || ""}`).join("\n") : "")
          : `내려받지 못했습니다 (${r.status})`);
      alert(msg);
      return false;
    }
    const blob = await r.blob();
    const cd = r.headers.get("content-disposition") || "";
    const m = /filename\*=UTF-8''([^;]+)/i.exec(cd) || /filename="?([^";]+)"?/i.exec(cd);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = m ? decodeURIComponent(m[1]) : fallbackName;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 30000);
    return true;
  } catch (e) {
    alert("내려받지 못했습니다 — 서버에 연결할 수 없습니다.");
    return false;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = label; }
  }
}

/* ---------------- row add / copy / delete ---------------- */
async function refreshRows(selectKey, opts = {}) {
  if (opts.keys && opts.keys.length) await reloadKeys(opts.keys); else await loadRows();
  if (!selectKey) return;
  // 53회차 [G] — 마크업으로 행을 더한 뒤에는 **오른쪽 목록이 그 행으로
  // 간다** (8차 피드백 s8: *"마크업이 완료되면 오른쪽 화면은 추가된 행으로
  // 이동 및 표기해라"*).  `select(key, true)` 는 도면 쪽만 가운데로 옮기고
  // 목록은 그대로 두므로, 추가한 행이 1,000행 어딘가에 묻힌다.
  select(selectKey, !opts.toGrid);
  // hotfix70 — 목록은 보이는 행만 그리므로(hotfix69) 새 행이 화면 밖이면 그려지지도 않는다.  추가·복사한 행은
  // 언제나 목록에 세운다 (예전에는 모든 행이 그려져 있어 따로 할 일이 없었다 — UI 시험 step5 가 잡았다).
  const tr = revealRow(selectKey);
  if (!opts.toGrid || !tr) return;
  tr.scrollIntoView({ block: "center" });
  tr.classList.add("justadded");          // 잠깐 밝게 — 어디에 생겼는지 보인다
  setTimeout(() => tr.classList.remove("justadded"), 2000);
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
  // hotfix75 — 사람이 점을 고르는 동안 그 장을 미리 읽는다 (마크업과 같은 캐시 — 행을 더할 때 주변 도형을 재는
  // `probe_point` 가 같은 것을 쓴다).  안 그러면 처음 더하는 행이 그 장을 읽느라 2초 넘게 멈췄다.
  prewarmMarkup();
  if (S.pinMode) setPinMode(false);
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
  await refreshRows(out.key, { keys: [out.key] });
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
  const ck = (await r.json()).key;
  await refreshRows(ck, { keys: [ck] });
});

$req("#row-delete").addEventListener("click", async () => {
  // hotfix14 — 묶음이 있으면 묶음을, 없으면 고른 행을 지운다.  하는 일은 `deleteRows` 하나.
  const keys = S.multi.size ? [...S.multi] : (S.sel ? [S.sel] : []);
  if (!keys.length) { alert("삭제할 행을 먼저 선택하세요."); return; }
  await deleteRows(keys);
});

/* ---------------- hotfix29 — 타이틀블록 칸 지정 ----------------
 *
 * 새 양식마다 `TitleBlockUnreadable` 로 멈추면 프로그램의 실효성이 없다.  엔진이 캡션
 * 표기 여러 벌과 구조로 칸을 찾고도 남는 문서에서는 **사람이 도면 위에 사각형 하나를
 * 끌어** 그 칸을 알려 준다.  서버가 같은 종이 크기의 모든 장에서 그 칸을 읽어 미리
 * 보여 주고, 저장은 프로젝트 단위(`title_block_cells.json`) · 작성자 필수 · 다시 분석해야
 * 반영된다 (31회차 승수 · 45회차 도면번호 지정과 같은 규율).
 *
 * 좌표: 화면 픽셀 ÷ 확대율 = PDF pt (`/page/{n}.png?zoom=`).  `S` 를 건드리지 않는다 —
 * 이 화면은 결과 화면 앞에 선다. */
const TB = { job: null, page: 1, zoom: 0.5, cells: {}, derived: {}, state: null, drag: null };
const TB_LABEL = { dwg_no_region: "도면번호", title_region: "제목", rev_box: "REV", sheet_box: "SHEET" };

async function openTbFix(jobId) {
  TB.job = jobId; TB.cells = {}; TB.derived = {}; TB.state = null;
  const box = $("#tbfix");
  box.classList.remove("hidden");
  const msg = $("#tbfix-msg"); msg.textContent = "불러오는 중…"; msg.classList.remove("out");
  $("#tbfix-preview").innerHTML = "";
  $("#tbfix-who").value = lastAuthor();
  let st;
  try { st = await (await fetch(`/jobs/${jobId}/titleblock`)).json(); }
  catch (e) { msg.textContent = "불러오지 못했습니다"; msg.classList.add("out"); return; }
  if (!st.supported) { msg.textContent = st.note || "이 입력에는 쓸 수 없습니다"; msg.classList.add("out"); return; }
  TB.state = st;
  TB.page = st.suggested_page || 1;
  $("#tbfix-page").max = st.page_count;
  $("#tbfix-sizes").textContent = "쪽 크기 " + (st.sizes || []).map(z => `${z.size[0]}x${z.size[1]}pt ${z.pages}장`).join(" · ")
    + ` — 다수 크기의 장 ${(st.form_pages || []).length}장에 적용됩니다`;
  if (st.saved && st.saved.cells) TB.cells = { ...st.saved.cells };
  TB.derived = st.derived || {};
  msg.textContent = st.saved
    ? `저장된 지정이 있습니다 (${st.saved.author || "이름 없음"} · ${(st.saved.set_at || "").slice(0, 10)}) — 다시 그으면 바뀝니다`
    : (st.project ? "" : "⚠ 이 분석은 프로젝트에 묶여 있지 않아 저장할 자리가 없습니다 — 프로젝트를 고르고 다시 올리세요");
  if (!st.project) msg.classList.add("out");
  tbRender();
  box.scrollIntoView({ block: "start", behavior: "smooth" });
}

function tbRender() {
  const img = $("#tbfix-img");
  $("#tbfix-page").value = TB.page;
  img.onload = tbDrawBoxes;
  img.src = `/jobs/${TB.job}/page/${TB.page}.png?zoom=${TB.zoom}`;
}

function tbDrawBoxes() {
  const holder = $("#tbfix-boxes");
  holder.innerHTML = "";
  const put = (name, r, cls) => {
    const d = document.createElement("div");
    d.className = `tbbox ${name} ${cls || ""}`;
    d.style.left = `${r[0] * TB.zoom}px`; d.style.top = `${r[1] * TB.zoom}px`;
    d.style.width = `${(r[2] - r[0]) * TB.zoom}px`; d.style.height = `${(r[3] - r[1]) * TB.zoom}px`;
    d.innerHTML = `<span class="tblbl">${TB_LABEL[name] || name}${cls === "derived" ? " (도면이 답한 칸)" : ""}</span>`;
    holder.appendChild(d);
  };
  for (const [name, r] of Object.entries(TB.derived)) if (!TB.cells[name]) put(name, r, "derived");
  for (const [name, r] of Object.entries(TB.cells)) put(name, r, "");
}

function tbCell() { return (document.querySelector('input[name="tbfix-cell"]:checked') || {}).value || "dwg_no_region"; }

function tbPoint(ev) {
  const img = $("#tbfix-img");
  const b = img.getBoundingClientRect();
  return [(ev.clientX - b.left) / TB.zoom, (ev.clientY - b.top) / TB.zoom];
}

$req("#tbfix-stage").addEventListener("pointerdown", ev => {
  if (ev.button !== 0 || !TB.job) return;
  ev.preventDefault();
  const p = tbPoint(ev);
  const el = document.createElement("div");
  el.className = `tbbox rubber ${tbCell()}`;
  $("#tbfix-boxes").appendChild(el);
  TB.drag = { p0: p, el, id: ev.pointerId };
  $("#tbfix-stage").setPointerCapture(ev.pointerId);
});
$req("#tbfix-stage").addEventListener("pointermove", ev => {
  if (!TB.drag) return;
  const p = tbPoint(ev);
  const r = [Math.min(TB.drag.p0[0], p[0]), Math.min(TB.drag.p0[1], p[1]),
             Math.max(TB.drag.p0[0], p[0]), Math.max(TB.drag.p0[1], p[1])];
  const el = TB.drag.el;
  el.style.left = `${r[0] * TB.zoom}px`; el.style.top = `${r[1] * TB.zoom}px`;
  el.style.width = `${(r[2] - r[0]) * TB.zoom}px`; el.style.height = `${(r[3] - r[1]) * TB.zoom}px`;
});
$req("#tbfix-stage").addEventListener("pointerup", async ev => {
  if (!TB.drag) return;
  const d = TB.drag; TB.drag = null;
  d.el.remove();
  const p = tbPoint(ev);
  const r = [Math.min(d.p0[0], p[0]), Math.min(d.p0[1], p[1]), Math.max(d.p0[0], p[0]), Math.max(d.p0[1], p[1])]
    .map(v => Math.round(v * 10) / 10);
  if (r[2] - r[0] < 4 || r[3] - r[1] < 2) return;           // 클릭은 사각형이 아니다
  const cell = tbCell();
  TB.cells[cell] = r;
  tbDrawBoxes();
  await tbPreview(cell, r);
});

async function tbPreview(cell, rect) {
  const out = $("#tbfix-preview");
  out.innerHTML = `<span class="muted">${TB_LABEL[cell]} 칸을 같은 크기의 장 전부에서 읽는 중…</span>`;
  let got;
  try {
    got = await (await fetch(`/jobs/${TB.job}/titleblock/preview`, { method: "POST",
      headers: { "Content-Type": "application/json" }, body: JSON.stringify({ cell, rect }) })).json();
  } catch (e) { out.textContent = "읽지 못했습니다"; return; }
  const rows = (got.pages || []).slice(0, 12).map(g =>
    `<tr><td>p${g.page_no}</td><td>${g.text ? escape(g.text) : '<span class="muted">(비어 있음)</span>'}</td></tr>`).join("");
  const more = (got.pages || []).length > 12 ? `<tr><td colspan="2" class="muted">… ${got.pages.length - 12}장 더</td></tr>` : "";
  const bad = got.read < got.total;
  out.innerHTML = `<p><b>${TB_LABEL[cell]}</b> — ${got.total}장 중 <b>${got.read}장</b>에서 읽힘 · 서로 다른 값 ${got.distinct}`
    + (cell === "dwg_no_region" ? (got.pattern ? ` · 도면번호 형식 <code>${escape(got.pattern)}</code>` : ' · <span class="out">⚠ 두 장 이상에서 되풀이되는 번호 모양이 없습니다 — 사각형이 번호를 감싸는지 확인하세요</span>') : "")
    + (bad && got.read ? ` · <span class="muted">안 읽힌 장은 그 자리가 비었거나 글자가 획으로 그려진 장입니다</span>` : "")
    + `</p><table>${rows}${more}</table>`;
}

async function tbSave(thenRun) {
  const msg = $("#tbfix-msg"); msg.classList.remove("out");
  if (!TB.cells.dwg_no_region) { msg.textContent = "도면번호 칸을 먼저 그으세요"; msg.classList.add("out"); return false; }
  const who = $("#tbfix-who").value.trim();
  if (!who) { msg.textContent = "작성자를 적어야 저장됩니다 (팀이 공유하는 값입니다)"; msg.classList.add("out"); $("#tbfix-who").focus(); return false; }
  rememberAuthor(who);
  const r = await fetch(`/jobs/${TB.job}/titleblock`, { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cells: TB.cells, page_no: TB.page, author: who }) });
  if (!r.ok) { msg.textContent = (await r.json()).detail || "저장하지 못했습니다"; msg.classList.add("out"); return false; }
  const out = await r.json();
  msg.textContent = thenRun ? "저장했습니다 — 다시 분석합니다" : `저장했습니다 — ${out.applies}`;
  return true;
}
$req("#tbfix-save").addEventListener("click", () => tbSave(false));
$req("#tbfix-save-run").addEventListener("click", async () => {
  if (!(await tbSave(true))) return;
  const id = TB.job;
  $("#tbfix").classList.add("hidden");
  if (!(await askReanalyse(id))) return;
  watch(id, null, {});
});
$req("#tbfix-clear").addEventListener("click", async () => {
  await fetch(`/jobs/${TB.job}/titleblock`, { method: "DELETE" });
  TB.cells = {}; tbDrawBoxes();
  $("#tbfix-msg").textContent = "지정을 지웠습니다 — 다시 분석하면 도면이 답한 칸으로 돌아갑니다";
});
$req("#tbfix-close").addEventListener("click", () => $("#tbfix").classList.add("hidden"));
$req("#tbfix-page").addEventListener("change", ev => {
  const n = Math.max(1, Math.min(+ev.target.value || 1, (TB.state || {}).page_count || 1));
  TB.page = n; tbRender();
});
$req("#tbfix-prev").addEventListener("click", () => { if (TB.page > 1) { TB.page--; tbRender(); } });
$req("#tbfix-next").addEventListener("click", () => { if (TB.page < ((TB.state || {}).page_count || 1)) { TB.page++; tbRender(); } });

/* hotfix74 — 다시 분석을 청한다.  서버가 거절하면(이미 분석 중 409 · 원본 PDF 없음 410) 그 문장을 말하고
 * 화면을 바꾸지 않는다 — 예전에는 응답을 보지 않고 진행 화면으로 넘어가 아무 일도 없는 진행을 보였다. */
async function askReanalyse(id) {
  try {
    const r = await fetch(`/jobs/${id}/reanalyse`, { method: "POST" });
    if (r.ok) return true;
    const j = await r.json().catch(() => ({}));
    alert(typeof j.detail === "string" ? j.detail : `다시 분석을 시작하지 못했습니다 (${r.status})`);
  } catch (e) {
    alert("다시 분석을 시작하지 못했습니다 — 서버에 연결할 수 없습니다.");
  }
  return false;
}

$req("#reanalyse").addEventListener("click", async () => {
  if (!(await askReanalyse(S.job.id))) return;
  $("#main").classList.add("hidden");
  watch(S.job.id, S.job.page_count, S.job);
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
    add("Line No.", row.values.line_no || "(없음)");
    add("Line Size", row.values.line_size || "(없음)");
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
  const save = guarded(async () => {           // hotfix74 — 두 번 눌러도(Enter 연타) 신고는 한 건
    const what = (document.querySelector('input[name="rep-what"]:checked') || {}).value;
    const detail = $("#rep-detail").value.trim();
    if (!detail) { alert("왜 틀렸는지 한 줄만 적어 주세요."); return; }
    const body = {
      kind: opts.point ? "MISSED" : (opts.fromDrawing ? "SYMBOL" : "ROW"),
      what, detail, row_key: opts.rowKey || "",
      page_no: opts.pageNo || null, point: opts.point || null,
      author: currentAuthor(), screen: vocScreen(),
    };
    const r = await fetch(`/jobs/${S.job.id}/reports`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok) { alert((await r.json()).detail || "신고 저장 실패"); return; }
    const rep = await r.json();
    S.reports = rep.report_count;
    updateReportBadge();
    closeModal();
    if (rep.voc_id) editNotice(`신고 접수 · VOC ${rep.voc_id} — 개발팀 함에도 쌓였습니다`, "in");
  });
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

/* ---------------- VOC (hotfix71) ----------------
 *
 * 부서원이 남긴 오류·요청을 **개발 쪽(회사 Claude Code)이 읽는 함**에 쌓는다.  서버는 한 건을
 * 운영 폴더의 `voc/inbox/<VOC-id>/` 에 쓰고(`app/voc.py`), 회사 Claude Code 는
 * `python spike/voc.py list` 로 읽고 고친 뒤 `resolve` 로 장부에 적는다 — 반영된 VOC 는
 * 다시 목록에 오르지 않는다 (중복 반영 방지).  화면이 적는 것은 셋뿐(분류 · 사유 · 이름)이고
 * 어느 분석 · 어느 장 · 어느 행 · 이 서버의 업데이트는 서버가 담는다.
 *
 * 입구: 마크업(누락 추가 · 기존 상자 표시)의 "VOC 로 신고" · 오류 신고 · 머리줄/첫 화면의
 * [VOC] 버튼 · 분석 실패 화면.  쓰는 길은 `vocSend` 하나다. */
function vocCheckHtml(prefix) {
  return `<label class="voc-check"><input id="${prefix}-voc" type="checkbox" checked>
    개발팀에 <b>VOC</b> 로 신고 — 프로그램이 못 읽었거나 잘못 읽은 것으로 남깁니다 (사유 필수)</label>`;
}
function vocReasonOk(prefix) {
  const on = $(`#${prefix}-voc`) && $(`#${prefix}-voc`).checked;
  const note = ($(`#${prefix}-note`) || {}).value || "";
  if (on && !note.trim()) {
    alert("VOC 로 신고하려면 사유를 한 줄 적어 주세요 (또는 'VOC 로 신고' 를 끄세요).");
    $(`#${prefix}-note`).focus();
    return false;
  }
  return true;
}
function vocScreen() {
  return { hash: location.hash || "", tab: S.tab || "", page_no: S.page ? S.page.page_no : null,
           viewport: [window.innerWidth, window.innerHeight], pane: PANE.role || "",
           embed: !!(EMBED && EMBED.on), ui: (document.querySelector('script[src*="app.js"]') || {}).src || "" };
}
async function vocSend(body) {
  const payload = Object.assign({ job_id: S.job ? S.job.id : "", author: currentAuthor(),
                                  screen: vocScreen() }, body);
  try {
    const r = await fetch("/voc", { method: "POST", headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify(payload) });
    if (!r.ok) { alert("VOC 저장 실패: " + ((await r.json()).detail || r.statusText)); return ""; }
    return (await r.json()).id || "";
  } catch (e) { alert("VOC 저장 실패: " + e); return ""; }
}
const VOC_GENERAL = ["UI", "SLOW", "FEATURE", "MISSING", "FALSE_POSITIVE", "WRONG_VALUE", "UNKNOWN_SYMBOL",
                     "SCOPE", "QTY", "TYPE", "DESCRIPTION", "ANALYSIS_FAILED", "OTHER"];

function vocListHtml(items) {
  if (!items.length) return `<p class="muted small">아직 접수된 VOC 가 없습니다.</p>`;
  return `<table class="voc-list"><thead><tr><th>접수</th><th>분류 · 사유</th><th>자리</th><th>상태</th></tr></thead><tbody>`
    + items.map(v => `<tr class="voc-${escape((v.state || "").toLowerCase())}">
        <td class="small">${escape((v.created_at || "").replace("T", " "))}<br><span class="muted">${escape(v.author || "이름 없음")}</span></td>
        <td><b>${escape(v.category_label || v.category)}</b><br>${escape(v.reason || "")}
          ${v.has_crop ? `<br><a href="/voc/${encodeURIComponent(v.id)}/crop.png" target="_blank" rel="noopener">도면 조각</a>` : ""}</td>
        <td class="small">${escape([v.project, v.pdf_name, v.page_no ? `p${v.page_no}` : "", v.drawing_no].filter(Boolean).join(" · ") || "—")}<br>
          <span class="muted">${escape(v.id)}</span></td>
        <td class="small voc-state">${escape(v.state_label || "")}${v.resolution && v.resolution.note ? `<br><span class="muted">${escape(v.resolution.note)}</span>` : ""}</td>
      </tr>`).join("") + `</tbody></table>`;
}

/* 일반 VOC — 어디서든.  결과 화면이면 지금 분석·장을 함께 담고, 실패 화면이면 그 실패를 담는다. */
async function vocDialog(opts) {
  opts = opts || {};
  let info = { categories: {}, items: [], counts: {}, voc_dir: "" };
  try { info = await (await fetch("/voc?limit=30")).json(); } catch (e) { /* 목록 없이도 쓴다 */ }
  const cats = info.categories || {};
  const pick = opts.category || (S.job ? "WRONG_VALUE" : "UI");
  const jobId = opts.jobId || (S.job && !opts.noJob ? S.job.id : "");
  const where = opts.jobId ? `분석 ${opts.jobName || opts.jobId} — 실패 사유와 멈춘 단계를 함께 담습니다`
    : S.job ? `${S.job.pdf_name || ""}${S.page ? ` · p${S.page.page_no} ${S.page.drawing_no || ""}` : ""}` : "";
  openModal("VOC — 개발팀에 남기기",
    `<p class="muted small">프로그램이 못 읽었거나 잘못 읽은 것, 불편한 점, 바라는 기능을 적어 주세요.
       이 PC 의 VOC 함(<code>${escape(info.voc_dir || "voc/inbox")}</code>)에 쌓이고, 개발하는 쪽이 읽고 고친 뒤
       <b>반영됨</b> 으로 표시합니다 — 한 번 반영된 VOC 는 다시 반영되지 않습니다.</p>
     <div class="mk-form">
       <label>분류 <select id="vc-class">${VOC_GENERAL.filter(k => cats[k] || !Object.keys(cats).length)
         .map(k => `<option value="${k}"${k === pick ? " selected" : ""}>${escape(cats[k] || k)}</option>`).join("")}</select></label>
       <label>내용 <textarea id="vc-note" rows="4" placeholder="무엇이 · 어디서 · 어떻게 되어야 하나">${escape(opts.reason || "")}</textarea></label>
       ${where ? `<label class="voc-check"><input id="vc-ctx" type="checkbox" checked> 지금 보고 있는 것을 함께 담기 — ${escape(where)}</label>` : ""}
       <label>작성자 <input id="vc-author" type="text" value="${escape(currentAuthor())}" placeholder="이름"></label>
     </div>
     <div class="modal-actions">
       <button id="vc-cancel" class="ghost">닫기</button>
       <button id="vc-save">VOC 접수</button>
     </div>
     <h4 class="voc-h">최근 VOC <span class="muted small">— 미반영 ${(info.counts || {}).open || 0} · 전체 ${(info.counts || {}).total || 0}${(info.counts || {}).unreadable ? ` · <span class="voc-bad">읽지 못한 ${info.counts.unreadable}건 (운영 PC 의 voc 폴더 확인)</span>` : ""}</span></h4>
     <div id="vc-list">${vocListHtml(info.items || [])}</div>`);
  $("#vc-cancel").onclick = closeModal;
  $("#vc-note").focus();
  $("#vc-save").onclick = guarded(async () => {       // hotfix74 — 두 번 눌러도 VOC 는 한 건
    const reason = $("#vc-note").value.trim();
    if (!reason) { alert("내용을 적어 주세요."); $("#vc-note").focus(); return; }
    const author = $("#vc-author").value.trim();
    if (author && !EMBED.user) rememberAuthor(author);
    const withCtx = !$("#vc-ctx") || $("#vc-ctx").checked;
    const body = { source: opts.source || "GENERAL", category: $("#vc-class").value, reason, author,
                   job_id: withCtx ? jobId : "" };
    if (withCtx && !opts.jobId && S.page) { body.page_no = S.page.page_no; body.drawing_no = S.page.drawing_no || ""; }
    if (withCtx && !opts.jobId && S.sel) body.row_keys = [S.sel];
    const id = await vocSend(body);
    if (!id) return;
    $("#vc-note").value = "";
    editNotice(`VOC ${id} 접수 — 개발팀 함에 쌓였습니다`, "in");
    try { info = await (await fetch("/voc?limit=30")).json(); $("#vc-list").innerHTML = vocListHtml(info.items || []); }
    catch (e) { /* 목록은 덤 */ }
  });
}
for (const id of ["#voc-btn", "#home-voc"]) {
  const b = document.querySelector(id);
  if (b) b.addEventListener("click", () => vocDialog(id === "#home-voc" ? { noJob: true } : {}));
}

/* ---------------- 전역 심볼 사전 (18회차 [D]) ----------------
 *
 * ★ 이 화면은 **묻기만 한다**.  그 심볼이 무엇인지는 사람이 적고, 화면도
 * 서버도 추측하지 않는다 — 추측해서 채워 두면 사람은 그것을 확인하지 않고
 * 넘긴다 (§2.1 ③).  그래서 TYPE·산출물 칸의 기본값이 비어 있고, "이것은
 * 아마 XV 입니다" 같은 문장이 없다.
 *
 * 우선순위도 화면이 말한다: 그 프로젝트 범례가 정의한 것이 있으면 사전은
 * 지고, 사전은 **범례에 없는 것만** 채운다.
 *
 * 목록은 분석할 때 모아 둔 것을 그대로 읽는다 (`GET /jobs/{id}/unjudged`).
 * 여기서 다시 세지 않는다 — 58장을 다시 읽으면 3분이 걸린다. */

function updateSymbolBadge() {
  const n = $("#symbol-n");
  if (!n) return;
  n.textContent = S.unjudged || 0;
  n.classList.toggle("zero", !S.unjudged);
}

async function loadUnjudged() {
  if (!S.job) return { known: false, items: [] };
  const out = await (await fetch(`/jobs/${S.job.id}/unjudged`)).json();
  S.unjudged = (out.items || []).length;
  S.unjudgedKnown = !!out.known;
  updateSymbolBadge();
  return out;
}

/* 같은 모양이 여러 장에 나오면 한 줄로 묶는다 - 사람이 같은 판단을 열 번
 * 하지 않게.  묶는 키는 **종류 + 라벨**이고, 그것이 곧 등록 키가 된다. */
function groupUnjudged(items) {
  const by = new Map();
  for (const it of items) {
    const key = `${it.kind}:${(it.label || "(이름 없음)")}`;
    if (!by.has(key)) by.set(key, { key, kind: it.kind, label: it.label || "",
                                    why: it.why || "", pages: [], items: [] });
    const g = by.get(key);
    g.items.push(it);
    if (!g.pages.includes(it.page_no)) g.pages.push(it.page_no);
  }
  return [...by.values()].sort((a, b) => b.items.length - a.items.length);
}

async function showSymbolRegister() {
  const [un, dict] = await Promise.all([
    loadUnjudged(),
    (await fetch("/symbols/global")).json(),
  ]);
  const groups = groupUnjudged(un.items || []);
  const known = (dict.symbols || []);

  const head = un.known
    ? `<p class="muted small">이 분석이 <b>판정하지 못한</b> 심볼 ${(un.items || []).length}건
       · ${groups.length}종류입니다. 무엇인지 <b>사람이 적어야</b> 등록됩니다 —
       화면도 서버도 뜻을 짐작하지 않습니다.</p>`
    : `<p class="muted small">${escape(un.note || "이 분석에는 미판정 목록이 없습니다.")}</p>`;

  const dictLine =
    `<p class="muted small">전역 사전 ${known.length}건 ·
     <b>${dict.enabled ? "켜짐" : "꺼짐"}</b>
     <button id="sym-toggle" class="ghost mini">${dict.enabled ? "끄기" : "켜기"}</button>
     <br>${escape(dict.note || "")}<br>저장 위치: ${escape(dict.path || "")}</p>`;

  const list = groups.length
    ? groups.map(g => `<div class="sym-row" data-key="${escape(g.key)}">
        <div><b>${escape(g.label || "(이름 없음)")}</b>
          <span class="muted small">${escape(g.kind)}</span>
          <div class="meta">${escape(g.why)} · ${g.items.length}건 ·
            p${g.pages.slice(0, 6).join(", p")}${g.pages.length > 6 ? " …" : ""}</div></div>
        <div class="acts"><button class="ghost mini sym-add">등록…</button></div>
      </div>`).join("")
    : `<p class="muted">판정하지 못한 심볼이 없습니다.</p>`;

  const mine = known.length
    ? `<h4 class="small">등록된 심볼</h4>` + known.map(sy =>
        `<div class="sym-row" data-id="${escape(sy.id)}">
          <div><b>${escape(sy.name)}</b>
            <span class="muted small">${escape(sy.kind)}${sy.type ? " · " + escape(sy.type) : ""}</span>
            <div class="meta">${escape(sy.registered_by)} (자칭) ·
              ${new Date((sy.registered_at || 0) * 1000).toLocaleString("ko-KR")}</div></div>
          <div class="acts"><button class="ghost mini sym-del">삭제</button></div>
        </div>`).join("")
    : "";

  openModal("심볼 등록",
    head + dictLine + list + mine
    + `<div class="modal-actions"><button id="sym-close" class="ghost">닫기</button></div>`);

  $("#sym-close").onclick = closeModal;
  $("#sym-toggle").onclick = async () => {
    const body = new FormData();
    body.append("on", dict.enabled ? "false" : "true");
    await fetch("/symbols/global/enabled", { method: "POST", body });
    showSymbolRegister();
  };
  document.querySelectorAll(".sym-del").forEach(b => b.onclick = async (ev) => {
    const id = ev.target.closest(".sym-row").dataset.id;
    if (!window.confirm("이 심볼을 전역 사전에서 지울까요?")) return;
    await fetch(`/symbols/global/${encodeURIComponent(id)}`, { method: "DELETE" });
    showSymbolRegister();
  });
  document.querySelectorAll(".sym-add").forEach(b => b.onclick = (ev) => {
    const key = ev.target.closest(".sym-row").dataset.key;
    symbolForm(groups.find(g => g.key === key));
  });
}

/* 등록 폼 - **빈 칸으로 연다.**  이름을 못 적으면 등록되지 않는다: 서버도
 * 같은 것을 요구하므로(`global_symbols.register`), 화면을 지나쳐도 막힌다. */
function symbolForm(g) {
  if (!g) return;
  const sample = g.items[0] || {};
  openModal(`심볼 등록 — ${g.label || "(이름 없음)"}`,
    `<p class="muted small">p${g.pages.join(", p")} 에서 ${g.items.length}건 ·
      ${escape(g.why)}<br>
      <b>이 심볼이 무엇인지는 도면을 보고 사람이 적습니다.</b>
      비워 두면 등록되지 않습니다.</p>
     <div class="modal-field"><label>이름 (무엇인가)</label>
       <input id="sym-name" type="text" placeholder="예: ANGLE VALVE"></div>
     <div class="modal-field"><label>종류</label>
       <select id="sym-kind">
         <option value="VALVE_BODY"${g.kind === "VALVE_BODY" ? " selected" : ""}>밸브 몸체</option>
         <option value="INSTRUMENT_TAG"${g.kind === "INSTRUMENT_TAG" ? " selected" : ""}>계기 태그</option>
         <option value="ACTUATOR">액추에이터</option>
       </select></div>
     <div class="modal-field"><label>TYPE (비워도 됩니다)</label>
       <input id="sym-type" type="text" value="${escape(g.label || "")}"></div>
     <div class="modal-field"><label>산출물 배분 (비워도 됩니다)</label>
       <input id="sym-deliv" type="text" placeholder="예: PNEUMATIC"></div>
     <div class="modal-field"><label>비고</label>
       <input id="sym-note" type="text" placeholder="어디를 보고 판단했는지"></div>
     <div class="modal-actions">
       <button id="sym-save">등록</button>
       <button id="sym-back" class="ghost">취소</button>
     </div>`);
  $("#sym-back").onclick = showSymbolRegister;
  $("#sym-save").onclick = async () => {
    const name = $("#sym-name").value.trim();
    if (!name) { alert("이 심볼이 무엇인지 적어야 등록됩니다."); return; }
    // 13회차 작성자 기록을 그대로 쓴다 - 확인은 매번, 타자는 한 번.
    const author = await askAuthor(`전역 심볼 등록 — ${name}`);
    if (author === null) return;
    const body = new FormData();
    body.append("symbol_id", g.key);
    body.append("kind", $("#sym-kind").value);
    body.append("name", name);
    body.append("type_value", $("#sym-type").value.trim());
    body.append("deliverable", $("#sym-deliv").value.trim());
    body.append("author", author);
    body.append("source_page", String(sample.page_no || 0));
    body.append("note", $("#sym-note").value.trim());
    body.append("signature", JSON.stringify(
      { label: g.label, why: g.why, center: sample.center || null,
        rect: sample.rect || null }));
    const r = await fetch("/symbols/global", { method: "POST", body });
    if (!r.ok) {
      const out = await r.json().catch(() => ({}));
      alert(out.detail || "등록하지 못했습니다.");
      return;
    }
    showSymbolRegister();
  };
}

$req("#symbols").addEventListener("click", showSymbolRegister);

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
    // 56회차 — 화면 파일 딱지를 같이 적는다.  꾸러미를 덮어썼는데 브라우저가
    // 옛 `app.js` 를 캐시로 쓰고 있으면 그것을 알 길이 없었다 (현장 보고 두 번).
    const ui = v.ui ? ` · 화면 ${v.ui.app_js}` : "";
    // hotfix34 — 첫 화면 오른쪽 아래에 **어느 업데이트가 적용돼 있는가** 를 적는다:
    // 꾸러미 이름(rev 번호) · zip 파일명 · zip 을 만든 시각.  값은 꾸러미 생성기가
    // 적어 둔 `app/_update.json` 그대로이고, 없으면 "기록 없음" (지어내지 않는다).
    const u = v.update;
    const upd = u
      ? `업데이트 ${u.name}${u.rev != null ? ` (rev ${u.rev})` : ""} · ${u.zip || "zip 이름 없음"} · 생성 ${u.created_at || "시각 없음"}`
      : "업데이트 기록 없음 (hotfix34 이전 꾸러미)";
    $("#build-text").textContent =
      `${upd}  |  v${v.version} · ${v.built_at || "날짜 없음"}`
      + (v.kind === "exe" ? "" : " (source)") + ui;
    $("#build-text").title =
      (u ? `적용된 꾸러미 ${u.zip} · 기준 커밋 ${u.base_commit || "?"}${u.branch ? " (" + u.branch + ")" : ""} · ` : "")
      + `버전 ${v.version} · 빌드일 ${v.built_at} (${v.dated}) · Python ${v.python}`
      + (v.ui ? ` · app.js ${v.ui.app_js} · styles.css ${v.ui.styles_css}` : "");
  } catch (e) { /* the footer is a label, not a feature */ }
})();

/* hotfix18 — 목록 행 음영은 **사람이 한 일**을 말한다.
 *   사람이 삭제(오검출)     → 연한 붉은 음영 + 취소선   (`userdel`)
 *   마크업으로 사람이 추가  → 연한 녹색 음영             (`added` — 마크업 상자와 같은 녹색)
 *   사람이 칸을 고침        → 연한 노랑 음영             (`useredit`)
 *   셋이 겹치면 이 순서가 이긴다 (삭제가 가장 먼저 보여야 한다).
 *   판정은 행 데이터에서만 읽는다 — 그리드·근거 패널·오버레이가 같은 값을 본다. */
function rowUserState(r) {
  if (!r) return "";
  if (r.removed || (r.reject && Object.keys(r.reject).length)) return "userdel";
  if (r.added) return "added";
  if (r.user && Object.values(r.user).some(v => v !== null && v !== undefined)) return "useredit";
  return "";
}
function paintRowState(tr, r) {
  if (!tr) return;
  tr.classList.remove("userdel", "added", "useredit");
  const st = rowUserState(r);
  if (st) tr.classList.add(st);
  if (r && r.added) tr.dataset.added = "1";
}
function repaintRow(r) {
  if (!r) return;
  const tr = document.querySelector(`#body tr[data-key="${CSS.escape(r.key)}"]`);
  paintRowState(tr, r);
}

/* hotfix17 — 도면 창 경계를 끌어 크기를 바꾼다.
 *   가운데 손잡이(#gutter-v): 도면 ↔ 목록 폭.  위 손잡이(#gutter-h): 안내 띠 높이
 *   (위로 끌면 띠가 접히고 그만큼 도면이 커진다).  크기는 이 브라우저에만 기억하고
 *   (localStorage — 없으면 기본 크기), 손잡이를 두 번 누르면 처음 크기로 돌아간다.
 *   도면 좌표·확대·선택은 건드리지 않는다 — 스크롤 창의 크기만 바뀐다. */
const SPLIT_KEY = "pid.split";
function _splitLoad() {
  try { return JSON.parse(localStorage.getItem(SPLIT_KEY) || "{}") || {}; } catch (e) { return {}; }
}
function _splitSave(v) { try { localStorage.setItem(SPLIT_KEY, JSON.stringify(v)); } catch (e) {} }
function _splitApply(v) {
  const split = document.getElementById("split");
  const bars = document.getElementById("infobars");
  if (split) {
    // hotfix63 — 0 도 값이다 (왼쪽 끝까지 끈 것).  없을 때(null)만 기본 크기.
    if (v.left != null) split.style.setProperty("--left-w", `${Math.round(v.left)}px`);
    else split.style.removeProperty("--left-w");
  }
  if (bars) bars.style.maxHeight = (v.bars === undefined || v.bars === null) ? "" : `${Math.round(v.bars)}px`;
  // hotfix27 — 수량 승수 판 높이 (pid.split.mult).  없으면 CSS 기본(상한 170px).
  const mp = document.getElementById("mult-panel");
  if (mp) {
    if (v.mult) { mp.style.height = `${Math.round(v.mult)}px`; mp.style.maxHeight = "none"; }
    else { mp.style.height = ""; mp.style.maxHeight = ""; }
  }
  // hotfix26 — 근거 패널 높이 (pid.split.ev).  없으면 CSS 기본(232px).
  const ev = document.getElementById("evidence");
  if (ev) {
    if (v.ev) { ev.style.height = `${Math.round(v.ev)}px`; ev.style.maxHeight = "none"; }
    else { ev.style.height = ""; ev.style.maxHeight = ""; }
  }
}
function _dragGutter(g, axis, onMove) {
  if (!g) return;
  g.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    ev.preventDefault();
    g.setPointerCapture(ev.pointerId);
    g.classList.add("dragging");
    document.body.classList.add("resizing", axis);
    const move = (e) => onMove(e);
    const up = () => {
      g.classList.remove("dragging");
      document.body.classList.remove("resizing", axis);
      g.removeEventListener("pointermove", move);
      g.removeEventListener("pointerup", up);
      g.removeEventListener("pointercancel", up);
      window.dispatchEvent(new Event("resize"));
    };
    g.addEventListener("pointermove", move);
    g.addEventListener("pointerup", up);
    g.addEventListener("pointercancel", up);
  });
}
(function initSplit() {
  const split = document.getElementById("split");
  const bars = document.getElementById("infobars");
  const gv = document.getElementById("gutter-v");
  const gh = document.getElementById("gutter-h");
  const ge = document.getElementById("gutter-r");     // hotfix26 — 목록 ↔ 근거 패널
  const gm = document.getElementById("gutter-m");     // hotfix27 — 수량 승수 판 ↔ 목록
  if (!split) return;
  let state = _splitLoad();
  _splitApply(state);
  // hotfix63 — 사용자 요구 *"왼쪽 P&ID 든 오른쪽 List 든 칸 조절을 최대로"*.  예전에는 두 창 모두 260px
  // 아래로 못 줄였고, 왼쪽은 도면이 창을 꽉 채우는 폭(leftCap)보다 넓힐 수 없었다.  이제 끝까지 간다 —
  // 남기는 것은 손잡이를 다시 잡을 수 있는 폭(GRIP) 하나뿐이다.  두 번 누르면 예전 기본 크기로 돌아온다.
  const MIN = 0, GRIP = 7;
  // hotfix18 — 끄는 동안 도면이 **창에 맞춰** 커진다 ("맞춤" 과 같은 함수 `fit`).
  // 그리고 왼쪽 창은 도면이 창을 **꽉 채우는 폭**보다 넓어지지 않는다 — 그보다
  // 넓히면 도면은 더 커질 수 없고(높이가 먼저 찬다) 오른쪽에 빈 띠만 생긴다.
  // 그 폭은 도면 자신의 가로세로 비와 지금 창 높이에서 나온다 (숫자를 적지 않는다).
  let raf = 0;
  const refit = () => {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = 0;
      if (S.natural && S.natural.w && document.getElementById("sheet").src) fit();
    });
  };
  // #split 의 안쪽 여백을 뺀 폭 — 빼지 않으면 끝까지 끌었을 때 손잡이가 화면 밖으로 밀려나 다시 못 잡는다
  // (hotfix63 자기검증이 잡았다: 손잡이 x=1925 ↔ 창 폭 1920).
  const inner = () => {
    const r = split.getBoundingClientRect(), cs = getComputedStyle(split);
    const pl = parseFloat(cs.paddingLeft) || 0, pr = parseFloat(cs.paddingRight) || 0;
    return { x0: r.left + pl, w: r.width - pl - pr };
  };
  const clampLeft = () => {
    if (state.left == null) return;
    const box = inner();
    const left = Math.max(MIN, Math.min(state.left, box.w - MIN - GRIP));
    if (left !== state.left) { state = { ...state, left }; _splitApply(state); _splitSave(state); }
  };
  _dragGutter(gv, "col", (e) => {
    const box = inner();
    const left = Math.max(MIN, Math.min(e.clientX - box.x0, box.w - MIN - GRIP));
    state = { ...state, left }; _splitApply(state); _splitSave(state);
    refit();
  });
  _dragGutter(gh, "row", (e) => {
    if (!bars) return;
    const top = bars.getBoundingClientRect().top;
    const full = bars.scrollHeight;
    const h = Math.max(0, Math.min(e.clientY - top, full));
    state = { ...state, bars: h >= full ? null : h }; _splitApply(state); _splitSave(state);
    clampLeft();
    refit();
  });
  _dragGutter(ge, "row", (e) => {
    const ev = document.getElementById("evidence");
    const rg = document.getElementById("right");
    if (!ev || !rg) return;
    // 위로 끌면 패널이 커진다.  하한 80 · 상한은 목록에 네 줄(120px)은 남게 —
    // 목록과 패널이 나눠 갖는 높이 안에서만 (검토 칩 · 검색 줄은 그대로다)
    const gw = document.getElementById("gridwrap");
    const bottom = ev.getBoundingClientRect().bottom;
    const share = ev.getBoundingClientRect().height + (gw ? gw.getBoundingClientRect().height : rg.clientHeight);
    const h = Math.max(80, Math.min(bottom - e.clientY, share - 120));
    state = { ...state, ev: h }; _splitApply(state); _splitSave(state);
  });
  // hotfix27 — 수량 승수 판 ↔ 목록.  아래로 끌면 판이 커지고 위로 끌면 줄어든다.
  // 하한 60(머리줄 + 한 유닛 머리) · 상한은 목록에 네 줄(120px)은 남게 (ev 손잡이와 같은 규칙).
  _dragGutter(gm, "row", (e) => {
    const mp = document.getElementById("mult-panel");
    const gw = document.getElementById("gridwrap");
    if (!mp) return;
    const top = mp.getBoundingClientRect().top;
    const share = mp.getBoundingClientRect().height + (gw ? gw.getBoundingClientRect().height : 0);
    const h = Math.max(60, Math.min(e.clientY - top, share - 120));
    state = { ...state, mult: h }; _splitApply(state); _splitSave(state);
  });
  // 창이 줄면 저장된 폭이 새 창보다 클 수 있다 — 손잡이가 화면 밖으로 나가지 않게 다시 맞춘다.
  window.addEventListener("resize", () => clampLeft());
  requestAnimationFrame(clampLeft);
  for (const g of [gv, gh, ge, gm]) {
    if (!g) continue;
    g.addEventListener("dblclick", () => {
      state = g === gv ? { ...state, left: null } : g === gh ? { ...state, bars: null }
        : g === gm ? { ...state, mult: null } : { ...state, ev: null };
      _splitApply(state); _splitSave(state);
      window.dispatchEvent(new Event("resize"));
      refit();
    });
  }
})();

// hotfix22 — 머리줄의 펼침 판(출력 범위 · 적용 규칙 · 템플릿)은 **열 때 화면 안쪽으로**
// 붙인다.  CSS 는 `right:0` 로 오른쪽 끝을 버튼에 맞추는데, 버튼이 화면 왼쪽에 있으면
// 380px 판이 왼쪽 밖으로 나가 잘렸다 (사용자 캡처: 출력 범위).  오른쪽으로 펼쳐도 넘치면
// 왼쪽 정렬을 그대로 두고, 둘 다 넘치면 더 많이 보이는 쪽을 고른다.
function placeScope(det) {
  const body = det.querySelector(":scope > .scope-body");
  if (!body || !det.open) return;
  body.classList.remove("to-left");
  const r = body.getBoundingClientRect();
  if (r.left >= 8) return;
  body.classList.add("to-left");
  const r2 = body.getBoundingClientRect();
  if (r2.right > window.innerWidth - 8 && (window.innerWidth - r2.left) < r.right) {
    body.classList.remove("to-left");
  }
}
document.querySelectorAll("details.scope").forEach((det) => {
  det.addEventListener("toggle", () => placeScope(det));
});
window.addEventListener("resize", () => {
  document.querySelectorAll("details.scope[open]").forEach(placeScope);
});

/* hotfix72 — 머리줄 판(출력 범위 · 더보기 …)은 바깥을 누르면 닫힌다.  판 안을 누르는 것은
 * (체크 · 안쪽 판 열기) 닫지 않는다.  '더보기' 안의 단추를 누르면 그 일을 하고 메뉴를 닫는다. */
document.addEventListener("click", (ev) => {
  document.querySelectorAll("header details.scope[open]").forEach((det) => {
    if (!det.contains(ev.target)) det.open = false;
  });
});
(function () {
  const more = document.getElementById("more-actions");
  if (!more) return;
  more.querySelectorAll("button.menu-item").forEach((b) =>
    b.addEventListener("click", () => { more.open = false; }));
  // 안쪽 판(적용 규칙 · 템플릿)은 하나만 펼친다 — 둘 다 길어서 메뉴가 화면을 넘는다.
  more.querySelectorAll(":scope > .scope-body > details.scope").forEach((inner) =>
    inner.addEventListener("toggle", () => {
      if (inner.open) {
        more.querySelectorAll(":scope > .scope-body > details.scope[open]").forEach((o) => {
          if (o !== inner) o.open = false;
        });
      }
      // 안쪽 판이 열려 있는 동안만 메뉴를 넓힌다 — 규칙 표가 240px 안에서 한 글자씩 접혔다.
      more.classList.toggle("wide",
        !!more.querySelector(":scope > .scope-body > details.scope[open]"));
    }));
})();

// hotfix26 — 범례 판 접기 (pid.ovl.fold).  접히면 한 줄 요약만 남는다 (`buildOverlayLegend` 가 채운다).
(function () {
  const lg = document.getElementById("ovlegend"), b = document.getElementById("ovl-fold");
  if (!lg || !b) return;
  const apply = (f) => { lg.classList.toggle("folded", f); b.textContent = f ? "펼치기" : "접기"; };
  // hotfix73 — 기억된 선택이 없으면 **도면 창이 낮을 때 접힌 채로** 시작한다.  품질 시뮬레이션이
  // 잡았다: 1366×768 에서 펼친 범례 판이 도면 창 왼쪽 아래의 약 1/4 을 덮어 그 밑의 상자를 누를
  // 수 없었다.  접힌 줄도 세는 수를 그대로 말하고, 한 번 펼치면 그 선택을 기억한다.
  let folded = false, stored = null;
  try { stored = localStorage.getItem("pid.ovl.fold"); } catch (e) {}
  if (stored === "1" || stored === "0") folded = stored === "1";
  else folded = window.innerHeight < 900;
  apply(folded);
  b.addEventListener("click", () => {
    folded = !folded; apply(folded);
    try { localStorage.setItem("pid.ovl.fold", folded ? "1" : "0"); } catch (e) {}
  });
})();

// hotfix26 — 정보 띠 접기 (pid.infobars.open).  기본은 한 줄.  범례가 달라졌거나 모드가
// 충돌한 띠(.changed)가 있으면 접지 않는다 — 그 사실이 화면에 자리가 없으면 반드시 묻힌다 (15회차).
function applyInfobars() {
  const bars = document.getElementById("infobars"), t = document.getElementById("infobars-toggle");
  if (!bars || !t) return;
  let open = false;
  try { open = localStorage.getItem("pid.infobars.open") === "1"; } catch (e) {}
  const changed = !!bars.querySelector(".legend-bar.changed:not(.hidden)");
  const any = !!bars.querySelector(".legend-bar:not(.hidden)");
  bars.classList.toggle("compact", !open && !changed);
  bars.classList.toggle("empty", !any);
  t.textContent = (open || changed) ? "접기" : "자세히";
  t.disabled = changed;
  t.title = changed ? "범례가 달라졌거나 모드가 충돌해 접지 않습니다" : "분석 정보 띠 펼치기 / 접기";
}
(function () {
  const t = document.getElementById("infobars-toggle");
  if (!t) return;
  t.addEventListener("click", () => {
    let open = false;
    try { open = localStorage.getItem("pid.infobars.open") === "1"; } catch (e) {}
    try { localStorage.setItem("pid.infobars.open", open ? "0" : "1"); } catch (e) {}
    applyInfobars();
    window.dispatchEvent(new Event("resize"));
  });
  for (const id of ["legend-bar", "mode-bar"]) {
    const el = document.getElementById(id);
    if (el) new MutationObserver(() => applyInfobars())
      .observe(el, { childList: true, attributes: true, attributeFilter: ["class"] });
  }
  applyInfobars();
})();

// hotfix26 — 목록 첫 두 열 고정: 둘째 열의 왼쪽 자리는 첫 열의 실제 폭이다 (열 폭은 내용이 정한다)
(function () {
  const head = document.getElementById("head"), grid = document.getElementById("grid");
  if (!head || !grid) return;
  const measure = () => {
    const th = grid.querySelector("thead th");
    if (th) grid.style.setProperty("--c1w", `${th.getBoundingClientRect().width}px`);
  };
  // hotfix45 — 머리글이 바뀐 **직후** 재면 방금 세운 2,000행 표의 레이아웃을 그 자리에서
  // 강제한다 (QFE 실측 한 번에 0.9초 · 전환마다 두 번).  한 프레임 뒤(그려진 뒤)에 재면 그
  // 레이아웃은 이미 끝나 있어 읽기만 한다.  여러 번 바뀌어도 한 번만 잰다.
  let pending = 0;
  const later = () => { if (pending) return; pending = requestAnimationFrame(() => requestAnimationFrame(() => { pending = 0; measure(); })); };
  new MutationObserver(later).observe(head, { childList: true });
  window.addEventListener("resize", later);
  later();
})();

// hotfix26 — ↑ ↓ 로 목록의 앞뒤 행을 고른다.  입력칸 · 선택상자에서는 잡지 않는다.
document.addEventListener("keydown", (ev) => {
  if (ev.key !== "ArrowDown" && ev.key !== "ArrowUp") return;
  const t = ev.target, tag = ((t && t.tagName) || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select" || (t && t.isContentEditable)) return;
  const st = document.getElementById("stage");
  // hotfix68 — 목록만 보이는 창(도면은 다른 창)에서도 위·아래 화살표로 행을 옮긴다 — 도면 창이 따라온다
  if (!S.job || !st || (!st.offsetParent && !drawingHidden())) return;
  // hotfix69 — 목록은 보이는 행만 그리므로 순서는 그린 줄이 아니라 목록(`S.vlist`)에서 읽는다
  const list = S.vlist || [];
  if (!list.length) return;
  let i = list.findIndex(r => r.key === S.sel);
  i = i < 0 ? (ev.key === "ArrowDown" ? 0 : list.length - 1)
    : Math.max(0, Math.min(list.length - 1, i + (ev.key === "ArrowDown" ? 1 : -1)));
  ev.preventDefault();
  const k = list[i].key;
  const tr = revealRow(k);
  if (tr) tr.scrollIntoView({ block: "nearest" });
  select(k, true);
});

// hotfix23 — 최종 저장.  편집은 칸마다 곧바로 저장되고 있다 — 이 버튼은 "이 상태로 저장했다"
// 를 누가 · 언제 남기는 것이고, 첫 화면이 프로젝트마다 마지막 기록을 보인다.
(function () {
  const btn = document.getElementById("save-final");
  if (!btn) return;
  btn.addEventListener("click", async () => {
    if (!S.job) return;
    const who = await askAuthor("최종 저장");
    if (who === null) return;
    const r = await fetch(`/jobs/${S.job.id}/save`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ author: who }),
    });
    if (!r.ok) { alert("저장 기록을 남기지 못했습니다"); return; }
    const sv = await r.json();
    editNotice(`저장했습니다 — ${saveWords(sv)}`, "in");
  });
})();

/* ---------------- hotfix68 — 도면 · 목록을 새 창으로 (듀얼 모니터) ----------------
 *
 * 사용자: *"좌측 화면과 우측 화면을 새창으로 띄워서 듀얼 모니터를 사용하는 사람들이 각 화면에 하나씩 전체 화면으로
 * 볼 수 있도록 · 각 화면에서는 기존 기능들과 서로간의 연동도 모두 되어야 한다 · 무겁지 않아야 한다."*
 *
 * 방법 — **기능을 다시 만들지 않는다.**  새 창은 같은 화면 전체를 싣고 보이는 칸만 고른다
 * (`body.pane-drawing` · `body.pane-list`).  본 창은 나머지 칸만 남긴다.  그래서 도면 창에서는 상자 누르기 · 공급
 * 주체 판 · x N 라벨 · 마크업 · 도면 위 편집 카드가, 목록 창에서는 칸 편집 · 필터 · 승수 판 · 근거 패널 · Excel 이
 * 그대로 돈다.  두 창 사이에 오가는 것은 **사실 몇 개**뿐이다 (`window.postMessage` — 대시보드 iframe 에서 띄운 창도
 * 같은 길로 닿는다):
 *   job   — 어느 결과를 보는가 (한쪽이 다른 결과를 열거나 이전/현재를 바꾸면 다른 쪽도)
 *   sel   — 고른 행 · Shift 묶음 (도면 창은 그 자리로 가고, 목록 창은 그 행으로 내려가 근거를 보인다)
 *   page  — 도면 창의 장 (목록 창의 "이 장" 기능이 따른다 · 목록 창에서 장을 옮기면 도면 창이 따른다)
 *   rows  — 저장이 끝난 행의 열쇠 (받은 창은 **그 행만** `/rows?keys=` 로 다시 받아 제자리에서 바꾼다 —
 *           어느 저장 길이든 같다: 저장 함수마다 알리는 대신 서버에 쓰는 요청이 끝난 것을 본다)
 *   memo · reopen · gone · bye — 장 메모 · 다시 대조/분석 · 분석 삭제 · 창 닫힘
 * 판정은 어느 창에서도 다시 하지 않는다 — 받은 창은 서버가 준 행을 그대로 놓는다. */
function paneRole() {
  const b = document.body.classList;
  return b.contains("pane-drawing") ? "drawing" : b.contains("pane-list") ? "list" : "";
}
function paneSplit() { return !!paneRole(); }
function drawingHidden() { return document.body.classList.contains("pane-list"); }

function setPane(role) {
  const b = document.body.classList;
  b.toggle("pane-drawing", role === "drawing");
  b.toggle("pane-list", role === "list");
  renderPaneBar();
  window.dispatchEvent(new Event("resize"));
  // 도면이 다시 보이면 지금 장을 그린다 (안 보이는 동안에는 그림을 받지 않았다).
  if (role !== "list" && S.job && S.page && S.imgStale) showPage(S.page);
  else if (role !== "list" && S.natural && S.natural.w && $("#sheet").getAttribute("src")) requestAnimationFrame(() => fit());
  renderFloatEdit();
}

function _peer() {
  if (!SYNC.link) return null;
  const w = PANE.role ? window.opener : SYNC.peer;
  return w && !w.closed ? w : null;
}
function syncPost(m) {
  if (!SYNC.link || SYNC.muted) return;
  const w = _peer();
  if (!w) return;
  try {
    w.postMessage({ ...m, __pid: SYNC.link, from: SYNC.me, job: m.job || (S.job ? S.job.id : "") }, location.origin);
  } catch (e) { /* 다른 출처로 옮겨 간 창 — 연동만 끊긴다 */ }
}
function syncSel() {
  if (!SYNC.link || SYNC.muted || SYNC.selQueued) return;
  SYNC.selQueued = true;
  queueMicrotask(() => {
    SYNC.selQueued = false;
    syncPost({ t: "sel", key: S.sel || null, multi: [...S.multi] });
  });
}
function syncPage() {
  if (!SYNC.link || SYNC.muted || !S.page) return;
  syncPost({ t: "page", page: S.page.page_no });
}
window.addEventListener("message", (ev) => {
  if (ev.origin !== location.origin) return;
  const d = ev.data;
  if (!d || !SYNC.link || d.__pid !== SYNC.link || d.from === SYNC.me) return;
  syncReceive(d).catch(() => {});
});

async function syncReceive(m) {
  if (m.t === "bye") {
    // 본 창이 닫히거나 새로 읽혔다 → 이 새 창은 혼자 계속 쓴다 (두 칸을 다 보인다).
    // 새 창이 보낸 bye 는 본 창이 기다리지 않는다 — 새 창을 새로 읽은 것일 수 있고, 닫혔으면 감시가 잡는다.
    if (PANE.role) {
      SYNC.alone = true; SYNC.link = ""; setPane("");
      editNotice("본 창이 닫혀 연동이 끊겼습니다 — 이 창은 혼자 계속 쓸 수 있습니다", "out");
    }
    return;
  }
  if (m.t === "job") {
    if (!S.job || S.job.id !== m.id) {
      const pr = S.revPair;
      if (pr && S.viewCache && S.viewCache[m.id] && (m.id === pr.current || m.id === pr.previous)) await switchView(m.id);
      else await open(m.id);
    } else if (!PANE.role) {
      // 새 창이 결과를 다 열었다 — 본 창이 지금 보는 장과 고른 것을 알려 준다 (새 창은 이 답을 하지 않는다: 메아리 없음)
      syncPost({ t: "state", page: S.page ? S.page.page_no : 0, key: S.sel || null, multi: [...S.multi] });
    }
    return;
  }
  if (!S.job || m.job !== S.job.id || S.loading) return;
  if (m.t === "state") { if (m.page) applyPage(m.page); applySel(m); return; }
  if (m.t === "page") { applyPage(m.page); return; }
  if (m.t === "sel") { applySel(m); return; }
  if (m.t === "rows") { await syncRows(m); return; }
  if (m.t === "memo") { if (S.page && S.page.page_no === m.page) showMemo(m.page); loadMemoSummary(); return; }
  // hotfix76 — 목록 창에서 위치 메모를 고르면 도면 창이 그 자리로 간다
  if (m.t === "pin") {
    S.pinPending = { page: m.page, id: m.id };
    if (!S.page || S.page.page_no !== m.page) {
      const pg = S.pages.find(x => x.page_no === m.page);
      if (pg) showPage(pg);                 // 그림과 메모가 둘 다 오면 tryPinPending 이 고른다
    } else showMemo(m.page);
    return;
  }
  if (m.t === "reopen") { await open(S.job.id); return; }
  if (m.t === "gone") { if (PANE.role) window.close(); else toFirstScreen(); return; }
}

function applyPage(pageNo) {
  const pg = (S.pages || []).find(p => p.page_no === pageNo);
  if (!pg || (S.page && S.page.page_no === pageNo)) return;
  SYNC.muted++;
  try {
    if (drawingHidden()) {
      // 그림은 받지 않는다 — 이 창의 "이 장" 기능(페이지별 승수 · 장 메모)이 따라갈 장만 바꾼다
      S.page = pg; S.imgStale = true;
      const ps = $("#page-select"); if (ps) ps.value = pg.page_no;
      _refreshPageMult();
    } else showPage(pg);
  } finally { SYNC.muted--; }
}

function applySel(m) {
  if (!S.rows) return;
  SYNC.muted++;
  try {
    const multi = (m.multi || []).filter(k => S.rowByKey[k]);
    if (multi.length > 1) {
      S.multi.clear(); multi.forEach(k => S.multi.add(k));
      S.sel = m.key || null;
      drawOverlay(); markMultiRows(); showMultiScope(); renderFloatEdit();
      return;
    }
    if (!m.key) { if (S.sel || S.multi.size) deselect(); return; }
    if (S.sel === m.key && !S.multi.size) return;
    const known = S.rowByKey[m.key] || (S.deletedRows || []).some(r => r.key === m.key);
    if (!known) return;
    // 도면 창은 그 자리로 가고(장이 다르면 장을 옮긴다), 목록 창은 그 행으로 내려가 근거를 보인다
    select(m.key, !drawingHidden());
  } finally { SYNC.muted--; }
}

/* 다른 창에서 저장한 행만 다시 받아 **제자리에서** 바꾼다.  행을 통째로 다시 읽지 않는다 (QFE 2,041행이면
 * 13.7MB · 목록 다시 그리기 0.9초).  사람이 지금 그 행의 칸에 타자 중이면 그 칸은 건드리지 않고 값만 맞춘다. */
async function syncRows(m) {
  const keys = Array.isArray(m.keys) ? m.keys : null;
  if (!keys || !keys.length || keys.length > 300 || keys.some(k => !S.rowByKey[k])) { await reloadRowsKeepView(); return; }
  let fresh;
  try {
    fresh = await (await fetch(`/jobs/${S.job.id}/rows?tab=ALL&keys=${keys.map(encodeURIComponent).join(",")}`)).json();
  } catch (e) { return; }
  if (!Array.isArray(fresh) || fresh.length !== keys.length) { await reloadRowsKeepView(); return; }
  const cols = gridCols();
  for (const r of fresh) {
    const old = S.rowByKey[r.key];
    for (const k of Object.keys(old)) if (!(k in r)) delete old[k];
    Object.assign(old, r);
    const tr = document.querySelector(`#body tr[data-key="${CSS.escape(r.key)}"]`);
    if (!tr) continue;
    if (tr.contains(document.activeElement)) {
      for (const [f, , editable] of cols) if (editable && document.activeElement.dataset.col !== f) syncRowCell(old, f);
      repaintRow(old);
    } else {
      const nt = buildRowTr(old, cols);
      if (S.sel === old.key) nt.classList.add("sel");
      tr.replaceWith(nt);
    }
  }
  markMultiRows();
  if (m.review != null && S.counts) S.counts.REVIEW = m.review;
  if (m.feedback != null) S.feedback = m.feedback;
  updateBadge();
  drawOverlay();
  if (S.sel && keys.includes(S.sel) && !S.multi.size && S.rowByKey[S.sel]) showEvidence(S.rowByKey[S.sel]);
  else if (S.multi.size && keys.some(k => S.multi.has(k))) showMultiScope();
  renderFloatEdit();
  _refreshPageMult();
}
/* hotfix75 — 몇 행이 바뀌었을 때(지움 · 마크업 추가 · 되살림) 목록 전체(QFE 2천 행 · 7MB · 0.2초 + 파싱)를
 * 다시 받지 않고 **그 행만** 받아 지금 목록에 끼워 넣은 뒤, 목록을 세우는 일은 예전과 같은 `loadRows` 가 한다
 * (`pre` 로 넘긴다 — 개수 · 개정 · 검토 · 탭 · 범례 · 그리드를 세우는 곳은 그대로 하나다).  서버에서 사라진 행
 * (사람이 만든 행을 지움)은 빼고, 새 행은 서버 목록과 같은 자리(장 · 열쇠 순)에 둔다.  못 받으면 예전처럼 전부 받는다. */
async function reloadKeys(keys) {
  let fresh;
  try {
    const res = await fetch(`/jobs/${S.job.id}/rows?tab=ALL&keys=${keys.map(encodeURIComponent).join(",")}`);
    if (!res.ok) throw new Error(res.status);
    fresh = await res.json();
  } catch (e) { await loadRows(); return; }
  if (!Array.isArray(fresh)) { await loadRows(); return; }
  const want = new Set(keys), got = new Map(fresh.map(r => [r.key, r]));
  const list = [];
  for (const r of S.rows) {
    if (got.has(r.key)) { list.push(got.get(r.key)); got.delete(r.key); }
    else if (!want.has(r.key)) list.push(r);
  }
  // 새 행 — 서버 목록과 같은 자리 (`merged_rows` 의 ORDER BY page_no, key)
  const before = (x, y) => x.page_no < y.page_no || (x.page_no === y.page_no && x.key < y.key);
  for (const r of got.values()) {
    const at = list.findIndex(x => !x.key.startsWith("del:") && before(r, x));
    if (at < 0) list.push(r); else list.splice(at, 0, r);
  }
  await loadRows(Promise.resolve(list));
}
async function reloadRowsKeepView() {
  const gw = $("#gridwrap"); const top = gw ? gw.scrollTop : 0;
  await loadRows();
  if (gw) gw.scrollTop = top;
  drawOverlay();
  SYNC.muted++;
  try {
    if (S.multi.size > 1) showMultiScope();
    else if (S.sel && S.rowByKey[S.sel]) showEvidence(S.rowByKey[S.sel]);
  } finally { SYNC.muted--; }
  renderFloatEdit();
}

/* 서버에 쓰는 요청이 끝나면 다른 창에 "이 행이 바뀌었다" 를 알린다.  저장 길이 마흔 곳 넘게 흩어져 있어
 * 저장 함수마다 알림을 다는 대신, 요청 하나를 본다 — 새 저장 길이 생겨도 연동이 저절로 따라온다.
 * 열쇠는 주소(`/rows/{key}`)나 본문(`key` · `keys` · `items[].key`)에서 읽고, 못 읽으면 "전부" 로 보낸다. */
function _bodyKeys(body) {
  let b = body;
  if (typeof b === "string") { try { b = JSON.parse(b); } catch (e) { return null; } }
  else if (b instanceof FormData) { const k = b.get("key") || b.get("row_key"); return k ? [String(k)] : null; }
  if (!b || typeof b !== "object") return null;
  const out = [];
  for (const f of ["key", "row_key"]) if (typeof b[f] === "string") out.push(b[f]);
  for (const f of ["keys", "row_keys"]) if (Array.isArray(b[f])) b[f].forEach(k => typeof k === "string" && out.push(k));
  for (const f of ["items", "rows"]) if (Array.isArray(b[f])) b[f].forEach(it => it && typeof it.key === "string" && out.push(it.key));
  return out.length ? out : null;
}
function syncNoteMutation(url, init) {
  if (!SYNC.link || !S.job) return;
  let u;
  try { u = new URL(url, location.href); } catch (e) { return; }
  const mm = u.pathname.match(/^\/jobs\/([^/]+)(?:\/(.*))?$/);
  if (!mm) return;                                   // 프로젝트 · 템플릿 · 심볼 사전 — 행에 안 닿는다
  const job = decodeURIComponent(mm[1]), rest = mm[2] || "";
  if (job !== S.job.id) return;
  if (rest === "") { syncPost({ t: "gone", job }); return; }                  // 분석 삭제
  if (/^(cancel|diagnostic|feedback_export|titleblock)/.test(rest)) return;
  if (rest === "reanalyse" || rest === "revision") { syncPost({ t: "reopen", job }); return; }
  if (rest.startsWith("memo/")) { syncPost({ t: "memo", job, page: +rest.split("/")[1] || 0 }); return; }
  let keys = null;
  const rm = rest.match(/^rows\/([^/]+)(?:\/([a-z_]+))?$/);
  if (rm && rm[2] !== "copy") keys = [decodeURIComponent(rm[1])];
  else if (!rm && rest !== "rows") keys = _bodyKeys(init && init.body);
  const d = SYNC.dirty;
  if (!keys) d.all = true; else keys.forEach(k => d.keys.add(k));
  clearTimeout(d.t);
  // 저장한 창이 응답을 다 받아 자기 화면을 고친 뒤에 보낸다 (검토 수 · 이력 수를 함께 실어 보낸다)
  d.t = setTimeout(() => {
    const all = d.all, ks = [...d.keys];
    SYNC.dirty = { keys: new Set(), all: false, t: 0 };
    syncPost({ t: "rows", job, keys: all ? null : ks,
               review: S.counts ? S.counts.REVIEW : null, feedback: S.feedback ?? null });
  }, 180);
}
/* hotfix74 — 서버와 연결이 끊기면 화면 위에 띠 하나로 말한다.  어느 요청이 실패했든 같은 띠이고, 5초마다
 * `/version` 을 물어 돌아오면 스스로 사라진다.  돌발상황 시뮬레이션(U2): 서버가 꺼진 동안 화면은 아무 말이
 * 없었고 페이지 오류(`Failed to fetch`)만 남았다. */
const NET = { down: false, timer: null };
function netDown() {
  if (NET.down) return;
  NET.down = true;
  let b = document.getElementById("net-banner");
  if (!b) {
    b = document.createElement("div");
    b.id = "net-banner";
    b.setAttribute("role", "alert");
    b.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99999;background:#b42318;color:#fff;"
      + "padding:8px 16px;font-size:14px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,.25)";
    document.body.appendChild(b);
  }
  b.textContent = "서버에 연결할 수 없습니다 — 고친 값이 저장되지 않습니다.  P&ID 분석 서버가 켜져 있는지 확인해 "
    + "주세요.  연결되면 이 줄은 저절로 사라집니다.";
  b.hidden = false;
  NET.timer = setInterval(async () => {
    try {
      const r = await _fetch0("/version", { cache: "no-store" });
      if (r.ok) netUp();
    } catch (e) { /* 아직 꺼져 있다 */ }
  }, 5000);
}
function netUp() {
  NET.down = false;
  checkStaleUi();                     // 서버가 다시 켜졌다면 업데이트였을 수 있다
  if (NET.timer) { clearInterval(NET.timer); NET.timer = null; }
  const b = document.getElementById("net-banner");
  if (b) b.hidden = true;
}
let _fetch0 = window.fetch.bind(window);

/* hotfix74 — 서버가 업데이트됐는데 이 화면은 옛 판일 때 말한다.  운영 서버에 꾸러미를 적용해도 열어 둔
 * 탭은 옛 `app.js` 로 새 서버와 이야기한다 (밤새 켜 둔 탭 · 대시보드 iframe).  내 딱지는 이 스크립트 주소의
 * `?v=` 이고(서버가 내용으로 만든다 · 56회차), 2분마다 · 연결이 돌아올 때 `/version` 의 딱지와 맞대 다르면
 * 노란 띠와 [새로고침].  고친 값은 칸마다 이미 저장돼 있으므로 새로고침해도 잃지 않는다. */
/* hotfix74 — 한글 입력기(IME) 조합 중의 Enter 는 글자를 **확정**하는 키이지 저장하라는 키가 아니다.
 * 이 화면의 Enter 처리 열한 곳(칸 · 이름 줄 · 승수 · 검색 · 메모 …)이 그것을 가리지 않아, 이름 `홍길동` 을
 * 치고 바로 Enter 를 누르면 마지막 글자가 조합 중인 채로 저장되거나(빠짐) 저장 뒤 한 번 더 들어간다(겹침).
 * 곳곳을 고치지 않고 창에서 한 번 거른다 — 조합 중의 Enter 는 처리기에 닿지 않고 입력기만 받는다.
 * (기본 동작은 막지 않는다 — 입력기가 글자를 확정해야 한다.)  조합이 끝난 다음 Enter 는 예전 그대로다. */
window.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter" && (ev.isComposing || ev.keyCode === 229)) ev.stopImmediatePropagation();
}, true);

/* hotfix74 — 기록을 하나 만드는 단추(VOC 접수 · 마크업 저장 …)를 사람이 두 번 누르면(더블클릭 · 느린 망에서 다시 누름)
 * 같은 기록이 두 개 생겼다.  처리 중에는 단추를 잠그고 다음 누름은 무시한다 — 끝나면(성공이든 실패든) 다시 풀린다. */
function guarded(fn) {
  let busy = false;
  return async function (...args) {
    if (busy) return;
    busy = true;
    const btn = this instanceof HTMLElement ? this : null;
    if (btn) btn.disabled = true;
    try { return await fn.apply(this, args); }
    finally { busy = false; if (btn) btn.disabled = false; }
  };
}

const MY_UI_TAG = (() => {
  try {
    const m = /[?&]v=([^&]+)/.exec((document.currentScript && document.currentScript.src) || "");
    return m ? m[1] : "";
  } catch (e) { return ""; }
})();
async function checkStaleUi() {
  if (!MY_UI_TAG) return;
  try {
    const v = await (await _fetch0("/version", { cache: "no-store" })).json();
    const now = v && v.ui && v.ui.app_js;
    if (!now || now === MY_UI_TAG || document.getElementById("stale-banner")) return;
    const b = document.createElement("div");
    b.id = "stale-banner";
    b.setAttribute("role", "status");
    b.style.cssText = "position:fixed;bottom:34px;left:50%;transform:translateX(-50%);z-index:99998;"
      + "background:#fff4d6;color:#5c3d00;border:1px solid #e0a35a;border-radius:8px;padding:8px 14px;"
      + "font-size:13px;box-shadow:0 2px 8px rgba(0,0,0,.18)";
    const name = v.update && v.update.name ? ` (${v.update.name})` : "";
    b.textContent = `서버가 업데이트됐습니다${name} — 이 화면은 옛 판입니다.  고친 값은 저장돼 있으니 새로고침하세요. `;
    const btn = document.createElement("button");
    btn.textContent = "새로고침";
    btn.style.marginLeft = "8px";
    btn.onclick = () => location.reload();
    b.appendChild(btn);
    document.body.appendChild(b);
  } catch (e) { /* 꺼져 있으면 연결 끊김 띠가 말한다 */ }
}
setInterval(checkStaleUi, 120000);

(function hookFetch() {
  const f0 = window.fetch.bind(window);
  _fetch0 = f0;
  window.fetch = function (input, init) {
    const p = f0(input, init);
    p.then(() => { if (NET.down) netUp(); },
           e => { if (e && e.name !== "AbortError") netDown(); });
    try {
      const method = String((init && init.method) || (input && input.method) || "GET").toUpperCase();
      if (method !== "GET" && method !== "HEAD" && SYNC.link) {
        const url = typeof input === "string" ? input : (input && input.url) || String(input);
        p.then(res => { if (res && res.ok) syncNoteMutation(url, init); }).catch(() => {});
      }
    } catch (e) { /* 연동은 부가 기능 — 요청 자체를 막지 않는다 */ }
    return p;
  };
})();

/* 새 창 열기 · 닫기 */
async function popOut(role) {
  if (!S.job) return;
  if (SYNC.peer && !SYNC.peer.closed) { try { SYNC.peer.focus(); } catch (e) {} return; }
  if (S.side) toggleSide(false);
  if (document.body.classList.contains("pid-full")) setFull(false);
  const link = Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
  const q = new URLSearchParams(location.search);
  q.set("pane", role); q.set("link", link);
  const url = `${location.pathname}?${q.toString()}#${S.job.id}`;
  const w0 = Math.round((screen.availWidth || 1600) * 0.92), h0 = Math.round((screen.availHeight || 900) * 0.92);
  const w = _nativeOpen(url, `pid-${role}-${link}`, `popup=yes,width=${w0},height=${h0}`);
  if (!w) {
    alert("새 창이 막혔습니다 — 주소줄 오른쪽의 팝업 차단 표시에서 이 주소를 허용한 뒤 다시 눌러 주세요.");
    return;
  }
  SYNC.link = link; SYNC.peer = w; SYNC.peerRole = role; SYNC.alone = false;
  setPane(role === "drawing" ? "list" : "drawing");
  clearInterval(SYNC.poll);
  SYNC.poll = setInterval(() => { if (!SYNC.peer || SYNC.peer.closed) rejoin(); }, 700);
  placeOnOtherScreen(w);
}
/* 이 파일의 `open(jobId)` (결과 열기) 가 전역 함수라 브라우저의 `window.open` 을 덮는다 — `window.open(url)` 은 결과 열기를
 * 부르고 404 를 낸다 (자기검증이 잡았다).  이름을 바꾸면 부르는 곳 수십 군데와 시험이 따라 바뀌므로, 숨은 빈 iframe 의
 * 손대지 않은 `open` 을 이 창을 주인으로 부른다 — 새 창의 `opener` 는 이 창이다. */
let _openFrame = null;
function _nativeOpen(url, name, features) {
  if (!_openFrame || !_openFrame.isConnected) {
    _openFrame = document.createElement("iframe");
    _openFrame.style.display = "none";
    _openFrame.setAttribute("aria-hidden", "true");
    _openFrame.title = "새 창 열기 도우미";
    document.body.appendChild(_openFrame);
  }
  return _openFrame.contentWindow.open.call(window, url, name, features);
}
async function placeOnOtherScreen(w) {
  // 브라우저가 창 배치를 허락하면 다른 모니터에 꽉 차게 놓는다.  허락이 없거나(처음 한 번 묻는다) 대시보드 iframe 처럼
  // 막힌 곳에서는 그대로 둔다 — 사람이 그 창을 다른 모니터로 끌어 ⛶ 를 누르면 된다.
  try {
    if (!("getScreenDetails" in window)) return;
    const d = await window.getScreenDetails();
    const other = (d.screens || []).find(sc => sc !== d.currentScreen);
    if (!other || !w || w.closed) return;
    w.moveTo(other.availLeft, other.availTop);
    w.resizeTo(other.availWidth, other.availHeight);
  } catch (e) { /* 권한 없음 — 그대로 */ }
}
function rejoin() {
  clearInterval(SYNC.poll); SYNC.poll = 0;
  if (PANE.role) { syncPost({ t: "bye" }); window.close(); return; }
  const w = SYNC.peer;
  SYNC.peer = null; SYNC.peerRole = ""; SYNC.link = "";
  if (w && !w.closed) { try { w.close(); } catch (e) {} }
  setPane("");
}
function renderPaneBar() {
  const role = paneRole();
  const pop = PANE.role && !SYNC.alone;               // 이 창이 새 창인가
  const linked = !!SYNC.link && !SYNC.alone;
  document.querySelectorAll(".pop-btn").forEach(b => b.classList.toggle("hidden", !!role || !!PANE.role));
  document.querySelectorAll(".pane-join").forEach(b => {
    b.classList.toggle("hidden", !role || !linked);
    b.textContent = pop ? "⇆ 한 창으로 (이 창 닫기)" : "⇆ 한 창으로";
    b.title = pop ? "이 새 창을 닫고 본 창에서 도면 · 목록을 함께 봅니다"
                  : "새 창을 닫고 이 창에서 도면 · 목록을 함께 봅니다";
  });
  const other = role === "drawing" ? "목록" : "도면";
  document.querySelectorAll(".pane-chip").forEach(c => {
    c.classList.toggle("hidden", !role || !linked);
    c.textContent = `⧉ ${other} 창과 연동 중`;
    c.title = "고르기 · 장 옮기기 · 편집 · 삭제 · 승수가 두 창에 같이 반영됩니다";
  });
  const fl = document.getElementById("full-list");
  if (fl) fl.classList.toggle("hidden", role !== "list");
}
document.querySelectorAll(".pop-btn").forEach(b => b.addEventListener("click", () => popOut(b.dataset.pane)));
document.querySelectorAll(".pane-join").forEach(b => b.addEventListener("click", rejoin));
(function () {
  const fl = document.getElementById("full-list");
  if (!fl) return;
  fl.addEventListener("click", () => {
    // 목록 창은 화면 안 전체화면이 따로 없다 — 브라우저 전체화면만 (도면 창은 ⛶ 가 같은 일을 한다)
    try {
      if (!document.fullscreenElement) document.documentElement.requestFullscreen().catch(() => {});
      else document.exitFullscreen().catch(() => {});
    } catch (e) {}
  });
  document.addEventListener("fullscreenchange", () => {
    fl.textContent = document.fullscreenElement ? "⤡ 전체화면 끝" : "⛶ 전체화면";
  });
})();
window.addEventListener("pagehide", () => { if (SYNC.link) syncPost({ t: "bye" }); });
(function bootPane() {
  if (!PANE.role) { renderPaneBar(); return; }
  document.body.classList.add("popout");
  SYNC.link = PANE.link;
  if (!window.opener || !SYNC.link) { SYNC.alone = true; SYNC.link = ""; renderPaneBar(); return; }
  const slot = $("#embed-tabs"), tabs = $("#tabs");
  if (PANE.role === "list" && slot && tabs && !slot.contains(tabs)) { slot.appendChild(tabs); slot.classList.remove("hidden"); }
  setPane(PANE.role);
  document.title = (PANE.role === "drawing" ? "도면 — " : "목록 — ") + document.title;
})();

/* =====================================================================
 * hotfix49 — 대시보드형 화면: 왼쪽 메뉴 · 첫 화면 지표 · 그래프
 * ---------------------------------------------------------------------
 * 새로 세는 값이 없다.  전부 서버가 이미 내던 `/home` · `/audit` · `/version`
 * 을 다시 읽어 늘어놓는다 — 화면이 하는 말과 데이터가 같은 접근자에서 나와야
 * 한다 (11회차 규칙).  판정하는 곳도 없다: 개정 수(추가·수정·삭제 후보)는
 * 서버의 `counts` 그대로이고, 위생 건수는 `showAudit` 가 센 그 수다.
 * ===================================================================== */
const DASH = { home: null, audit: null, live: {}, pace: {} };
const NAV_KEY = "pid.nav.collapsed";
const escAttr = (v) => String(v ?? "").replace(/[<>&"']/g,
  c => ({ "<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;", "'": "&#39;" }[c]));
const fmtN = (n) => (n == null ? "—" : Number(n).toLocaleString("ko-KR"));

/* ---- 메뉴 접기 ---- */
(function navCollapse() {
  let v = null;
  try { v = localStorage.getItem(NAV_KEY); } catch (e) {}
  const collapsed = v === null ? window.innerWidth < 1500 : v === "1";
  document.body.classList.toggle("nav-collapsed", collapsed);
  document.addEventListener("click", ev => {
    if (!ev.target.closest(".nav-toggle")) return;
    const now = !document.body.classList.contains("nav-collapsed");
    document.body.classList.toggle("nav-collapsed", now);
    try { localStorage.setItem(NAV_KEY, now ? "1" : "0"); } catch (e) {}
    // 도면 창 폭이 바뀐다 — 맞춤 배율 · 손잡이가 크기 변화를 다시 읽게 한다
    setTimeout(() => window.dispatchEvent(new Event("resize")), 180);
  });
})();

/* ---- 결과 화면이 열려 있는가 — 메뉴의 결과 탭을 그때만 보인다.  `:has()` 없이 (오래된 브라우저)
   #main 의 hidden 을 지켜보고 body 에 한 낱말을 둔다.  #main 을 여닫는 곳이 여럿이라 그 곳들을
   고치지 않고 결과(클래스)만 본다. ---- */
(function watchMain() {
  const m = document.getElementById("main");
  if (!m) return;
  const sync = () => document.body.classList.toggle("in-results", !m.classList.contains("hidden"));
  sync();
  new MutationObserver(sync).observe(m, { attributes: true, attributeFilter: ["class"] });
})();

/* ---- 왼쪽 메뉴 ---- */
function latestJobOf(p) {
  return (p.revisions || []).find(r => r.job_id && !r.missing && !r.deleted) || null;
}
function renderNav() {
  const box = $("#nav-projects");
  const home = DASH.home;
  const inMain = !$("#main").classList.contains("hidden");
  const cur = inMain && S.job ? S.job.id : null;
  $("#nav-home").classList.toggle("on", !inMain);
  if (box && home) {
    const items = home.projects.map(p => {
      const last = latestJobOf(p);
      const mine = (p.revisions || []).some(r => r.job_id && r.job_id === cur);
      const c = (last && last.counts) || {};
      const changes = last && last.compared_with
        ? (c.ADDED || 0) + (c.MODIFIED || 0) + (c.DELETED_CANDIDATE || 0) : 0;
      const pill = changes ? `<span class="nav-pill" title="최신 리비전의 개정 변경 (추가 · 수정 · 삭제 후보)">변경 ${fmtN(changes)}</span>` : "";
      const n = (p.revisions || []).length;
      return `<a class="nav-item${mine ? " on" : ""}" href="${last ? "#" + escAttr(last.job_id) : "#"}"`
        + ` data-project="${escAttr(p.name)}" title="${escAttr(p.name)} — 리비전 ${n}개${last ? " · 최신 " + escAttr(last.revision) : ""}">`
        + `<span class="nav-ico" aria-hidden="true">${escAttr(p.name.slice(0, 2))}</span>`
        + `<span class="nav-text">${escAttr(p.name)}</span>${modeChip(projectMode(p))}${pill}<span class="nav-n">${n}</span></a>`;
    });
    if (home.loose && home.loose.length) {
      items.push(`<a class="nav-item" href="#" data-loose="1" title="프로젝트에 묶이지 않은 분석">`
        + `<span class="nav-ico" aria-hidden="true">…</span><span class="nav-text">묶이지 않은 분석</span>`
        + `<span class="nav-n">${home.loose.length}</span></a>`);
    }
    box.innerHTML = items.join("") || `<span class="nav-item" style="cursor:default;opacity:.7"><span class="nav-ico">·</span><span class="nav-text">프로젝트 없음</span></span>`;
  }
  const who = (typeof currentAuthor === "function" ? currentAuthor() : "") || "이름 없음";
  const u = $("#nav-user"); if (u) u.textContent = who;
}
$req("#nav-home").addEventListener("click", ev => {
  ev.preventDefault();
  if (!$("#main").classList.contains("hidden") || !$("#progress").classList.contains("hidden")) {
    toFirstScreen();      // hotfix58 — 분석 중에도 첫 화면으로 (분석은 계속되고 첫 화면이 현황을 보인다)
  } else {
    $("#drop").scrollTo({ top: 0, behavior: "smooth" });
  }
});
$req("#nav-projects").addEventListener("click", ev => {
  const a = ev.target.closest("a.nav-item");
  if (!a) return;
  if (a.getAttribute("href") === "#") {
    ev.preventDefault();
    if (!$("#main").classList.contains("hidden")) toFirstScreen();
    setTimeout(() => {
      const card = document.querySelector(".list-card");
      if (card) { card.scrollIntoView({ behavior: "smooth", block: "start" }); card.classList.add("home-highlight"); setTimeout(() => card.classList.remove("home-highlight"), 1500); }
    }, 60);
  }
});
$req("#nav-rename").addEventListener("click", () => {
  if (EMBED.user) { editNotice(`대시보드 로그인 이름(${EMBED.user})으로 기록됩니다 — 바꾸려면 대시보드에서 다시 로그인하세요`); return; }
  const now = (typeof lastAuthor === "function" ? lastAuthor() : "") || "";
  const v = prompt("이름 (자칭) — 편집 · 저장 기록에 적힙니다", now);
  if (v == null) return;
  if (typeof rememberAuthor === "function") rememberAuthor(v.trim());
  renderNav(); renderWhoChip();
});
window.addEventListener("storage", ev => { if (ev.key === "pid.author") renderNav(); });
async function pingServer() {
  const box = $("#nav-server"), t = $("#nav-server-text");
  try {
    const r = await fetch("/version", { cache: "no-store" });
    if (!r.ok) throw new Error(String(r.status));
    box.className = "sb-server ok"; t.textContent = `서버 연결됨 · ${location.host}`;
  } catch (e) {
    box.className = "sb-server bad"; t.textContent = "서버 응답 없음";
  }
}
pingServer();
setInterval(pingServer, 60000);

/* ---- 첫 화면 머리 · 버튼 ---- */
$req("#home-new").addEventListener("click", () => {
  const card = document.querySelector(".intake-card");
  if (!card) return;
  card.scrollIntoView({ behavior: "smooth", block: "start" });
  card.classList.add("home-highlight"); setTimeout(() => card.classList.remove("home-highlight"), 1500);
  const pick = $("#proj-pick"); if (pick) setTimeout(() => pick.focus(), 300);
});
$req("#home-refresh").addEventListener("click", () => { listHome(); showAudit(); pingServer(); });

/* ---- 대시보드 ---- */
function allRuns(home) {
  // 프로젝트 리비전 + 묶이지 않은 분석.  지운 기록(missing)은 셈에서 뺀다.
  const out = [];
  for (const p of home.projects) {
    for (const r of p.revisions || []) {
      if (r.missing || r.deleted) continue;
      out.push({ project: p.name, revision: r.revision, job_id: r.job_id, pdf: r.pdf_name,
                 status: r.status, rows: r.rows, at: r.analysed_at, edits: r.edits,
                 counts: r.counts || {}, compared_with: r.compared_with, page_count: r.page_count });
    }
  }
  for (const j of home.loose || []) {
    out.push({ project: "", revision: "", job_id: j.id, pdf: j.pdf_name, status: j.status, rows: j.rows,
               at: j.analysed_at || j.finished_at || j.created_at, edits: j.edits, counts: {}, compared_with: "",
               page_count: j.page_count });
  }
  return out.sort((a, b) => (b.at || 0) - (a.at || 0));
}
function renderDashboard() {
  const home = DASH.home;
  if (!home) return;
  const runs = allRuns(home);
  const done = runs.filter(r => r.status === "done");
  const running = runs.filter(r => r.status === "running" || r.status === "queued");
  const failed = runs.filter(r => r.status === "failed");
  const latestPer = home.projects.map(p => ({ name: p.name, last: latestJobOf(p) })).filter(x => x.last);
  const cmp = runs.find(r => r.compared_with && r.counts && Object.keys(r.counts).length);
  const cc = (cmp && cmp.counts) || {};
  const changes = (cc.ADDED || 0) + (cc.MODIFIED || 0) + (cc.DELETED_CANDIDATE || 0);
  const newest = runs[0];
  const audit = DASH.audit;

  $("#home-sub").textContent = [
    `프로젝트 ${home.projects.length}`, `분석 ${runs.length}건`,
    newest ? `마지막 분석 ${whenWords(newest.at)}${newest.project ? ` (${newest.project} ${newest.revision})` : ""}` : "분석 기록 없음",
  ].join(" · ");

  const pills = [];
  if (audit && audit.bad) pills.push(`<a class="pill" data-go="audit">데이터 위생 확인 <b>${audit.bad}</b></a>`);
  if (failed.length) pills.push(`<a class="pill" data-go="list">분석 실패 <b>${failed.length}</b></a>`);
  // hotfix57 — 분석 중인 것이 하나면 그 분석의 진행 화면으로 바로 간다.
  if (running.length) pills.push(`<a class="pill info" data-go="${running.length === 1 && running[0].job_id ? "#" + escAttr(running[0].job_id) : "list"}">분석 중 <b>${running.length}</b></a>`);
  if (cmp && changes) pills.push(`<a class="pill info" data-go="#${escAttr(cmp.job_id)}">${escAttr(cmp.project)} ${escAttr(cmp.revision)} 개정 변경 <b>${fmtN(changes)}</b></a>`);
  if (audit && !audit.bad) pills.push(`<span class="pill ok">데이터 위생 이상 없음 <b>0</b></span>`);
  $("#home-pills").innerHTML = pills.join("");

  // hotfix62 — 지표 카드 여섯(프로젝트 · 분석 · 산출 행 · 최근 개정 변경 · 사람이 고친 칸 · 데이터 위생)은
  // 사용자 요청으로 뺐다.  같은 사실은 위 알림 알약 · 저장된 프로젝트 카드 · 데이터 위생 카드가 말한다.
  $("#home-kpis").innerHTML = "";

  $("#home-charts").innerHTML = [
    chartCard("프로젝트별 산출 행 (최신 리비전)", vbars(latestPer.map(x => ({ label: x.name, value: x.last.rows || 0,
      tip: `${x.name} ${x.last.revision} · ${fmtN(x.last.rows)}행 · ${x.last.page_count || "?"}장` })), "행")),
    chartCard("리비전별 산출 행 (최근 12)", hbars(done.slice(0, 12).map(r => ({
      label: r.project ? `${r.project} ${r.revision}` : r.pdf, value: r.rows || 0,
      tip: `${r.project ? r.project + " " + r.revision + " · " : ""}${r.pdf} · ${fmtN(r.rows)}행 · ${whenWords(r.at)}` })))),
    chartCard(cmp ? `개정 변경 내역 — ${cmp.project} ${cmp.revision} vs ${cmp.compared_with}` : "개정 변경 내역", donut(cc)),
  ].join("");

  // hotfix58 — 돌고 있거나 기다리는 분석은 맨 위에 둔다 (시각이 아직 없어 정렬로는 밑으로 간다).
  const live = r => r.status === "running" || r.status === "queued";
  // 도는 것이 먼저, 기다리는 것은 그 뒤 (서버 /running 의 줄 순서와 같다).
  const recent = runs.filter(r => r.status === "running").concat(
    runs.filter(r => r.status === "queued"), runs.filter(r => !live(r))).slice(0, 8);
  $("#home-recent").innerHTML = recent.map(r => {
    const st = r.status === "done" ? `<span class="tagchip ok">${fmtN(r.rows)}행</span>`
      : `<span class="tagchip ${r.status === "failed" ? "bad" : "rev"}">${escAttr(JOB_STATUS_KO[r.status] || r.status)}</span>`;
    return `<a class="recent-row${live(r) ? " is-live" : ""}" href="#${escAttr(r.job_id)}"`
      + `${live(r) ? ` data-live="${escAttr(r.job_id)}" title="누르면 진행 화면으로 갑니다"` : ""}>`
      + `<span class="when">${escAttr(live(r) ? "지금" : whenWords(r.at))}</span>`
      + `<span><b>${escAttr(r.project || "—")}</b> ${r.revision ? `<span class="tagchip rev">${escAttr(r.revision)}</span>` : ""}</span>`
      + `<span class="muted" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${escAttr(r.pdf)}`
      + `${r.page_count ? ` · ${r.page_count}장` : ""}${r.edits ? ` · 수정 ${r.edits}칸` : ""}</span>${st}`
      + `${live(r) ? `<span class="run-live"></span>` : ""}</a>`;
  }).join("") || `<p class="muted small">아직 분석이 없습니다 — 위의 <b>새 분석</b> 에서 PDF 를 넣으세요.</p>`;
  renderLive();
  if (runs.some(live)) pollSoon();
}

/* hotfix58 — **분석 중 현황**: 진행 막대 · 예상 퍼센트 · 남은 시간 · 지금 단계.
 *
 * 값은 전부 서버의 `GET /running` 이다 (`main._run_status`).  퍼센트·남은 시간은 단계
 * 번호가 아니라 **이 서버에서 끝난 분석이 장당 걸린 시간의 중앙값 × 이 PDF 의 장수**
 * 에서 낸 추정이다 — 단계로 세면 '도면 치수 재기' 하나가 절반을 넘게 쓰는 동안 0% 에
 * 머문다.  근거(지난 분석 몇 건 · 장당 몇 초)를 같이 적고, 끝난 분석이 없으면 추정할 수
 * 없다고 말한다 (지어낸 속도는 없다).  예상보다 길어지면 99% 에서 멈추고 그렇게 적는다. */
const RUN_POLL_MS = 3000;
function etaWords(sec) {
  const n = Math.round(sec || 0);
  if (n < 60) return "1분 미만";
  const h = Math.floor(n / 3600), m = Math.round((n % 3600) / 60);
  return h ? `약 ${h}시간 ${m}분` : `약 ${m}분`;
}
function liveFacts(j) {
  /* 한 분석의 현황을 화면 말로 — 첫 화면과 진행 화면이 같이 읽는다. */
  if (!j) return { pct: null, eta: "현황을 받아 오는 중…", stage: "", basis: "" };
  if (j.status === "queued")
    return { pct: 0, waiting: true, stage: "",
             eta: (j.queue_ahead ? `앞에 ${j.queue_ahead}건 — 그 분석이 끝나면 시작합니다` : "곧 시작합니다")
               + (j.expected_s ? ` (시작하면 예상 소요 ${etaWords(j.expected_s)})` : ""),
             basis: j.basis ? `이 서버의 지난 분석 ${j.basis.jobs}건 · 장당 ${j.basis.sec_per_page}초 기준 추정` : "" };
  const stage = stageWords(j.message || "");
  const sheets = j.sheets_total ? ` · 도면 ${j.sheets_done}/${j.sheets_total}장` : "";
  const basis = j.basis ? `이 서버의 지난 분석 ${j.basis.jobs}건 · 장당 ${j.basis.sec_per_page}초 기준 추정` : "";
  if (j.percent == null)
    return { pct: null, stage: stage + sheets, basis,
             eta: `경과 ${minsec(j.running_s)} · 남은 시간은 아직 예상할 수 없습니다`
               + (j.page_count ? " (이 서버에서 끝난 분석이 아직 없습니다)" : "") };
  if (j.over)
    return { pct: j.percent, stage: stage + sheets, basis,
             eta: `경과 ${minsec(j.running_s)} · 예상(${etaWords(j.expected_s).replace("약 ", "")})보다 오래 걸리는 중` };
  return { pct: j.percent, stage: stage + sheets, basis,
           eta: `남은 시간 ${etaWords(j.eta_s)} · 경과 ${minsec(j.running_s)}` };
}
function liveBar(f) {
  const pct = f.pct == null ? null : Math.max(0, Math.min(100, f.pct));
  return `<span class="runbar${pct == null ? " unknown" : ""}${f.waiting ? " waiting" : ""}" role="progressbar" aria-valuemin="0" aria-valuemax="100"`
    + `${pct == null ? "" : ` aria-valuenow="${pct}"`}><span class="runbar-fill" style="width:${pct == null ? 100 : pct}%"></span></span>`
    + `<span class="runpct">${f.waiting ? "대기" : pct == null ? "—" : pct + "%"}</span>`;
}
function renderLive() {
  for (const el of document.querySelectorAll("#home-recent [data-live]")) {
    const slot = el.querySelector(".run-live");
    if (!slot) continue;
    const f = liveFacts(DASH.live[el.dataset.live]);
    slot.innerHTML = liveBar(f)
      + `<span class="runtext"><b>${escAttr(f.eta)}</b>${f.stage ? ` · ${escAttr(f.stage)}` : ""}`
      + `${f.basis ? `<span class="muted"> · ${escAttr(f.basis)}</span>` : ""}</span>`;
  }
  // 진행 화면이 열려 있으면 같은 값으로 — 막대도 같은 퍼센트를 그린다.
  if (S.watching && !$("#progress").classList.contains("hidden")) {
    const j = DASH.live[S.watching];
    const eta = $("#prog-eta");
    if (j && eta) {
      const f = liveFacts(j);
      eta.textContent = (f.pct != null ? `${f.pct}% · ` : "") + f.eta + (f.basis ? ` (${f.basis})` : "");
      if (f.pct != null) $("#bar-fill").style.width = `${f.pct}%`;
    }
  }
}
let _pollTimer = null;
async function pollRunning() {
  _pollTimer = null;
  let res;
  try { res = await (await fetch("/running")).json(); } catch (e) { pollSoon(); return; }
  const before = Object.keys(DASH.live);
  DASH.live = {};
  for (const j of res.jobs || []) DASH.live[j.id] = j;
  DASH.pace = res.pace || {};
  // 목록에서 빠진 분석은 끝났다 (완료 · 실패 · 취소) — 이력을 다시 받아 행 수·상태를 고친다.
  // 새로 생긴 분석도 첫 화면 목록에 없으면 다시 받는다.
  const shown = new Set([...document.querySelectorAll("#home-recent [data-live]")].map(e => e.dataset.live));
  const changed = before.some(id => !DASH.live[id]) || Object.keys(DASH.live).some(id => !before.includes(id) && !shown.has(id));
  if (changed && !$("#drop").classList.contains("hidden")) listHome();
  else renderLive();
  if (Object.keys(DASH.live).length || (S.watching && !$("#progress").classList.contains("hidden"))) pollSoon();
}
function pollSoon() {
  if (_pollTimer) return;
  _pollTimer = setTimeout(pollRunning, document.hidden ? RUN_POLL_MS * 4 : RUN_POLL_MS);
}
function chartCard(title, body) {
  return `<section class="card chart-card"><h3 class="card-title">${escAttr(title)}</h3>${body}</section>`;
}
function niceMax(v) {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p;
  return 10 * p;
}
/* 세로 막대 — 한 계열이라 범례 없이 제목이 이름을 댄다.  끝 4px 둥글게 · 기준선에 붙는다. */
function vbars(items, unit) {
  if (!items.length) return `<div class="chart-empty">분석한 프로젝트가 없습니다</div>`;
  const W = 420, H = 190, L = 40, B = 34, T = 14, R = 8;
  const max = niceMax(Math.max(...items.map(i => i.value)));
  const n = items.length, slot = (W - L - R) / n, bw = Math.min(46, slot * 0.6);
  const ticks = [0, max / 2, max];
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="세로 막대 그래프">`;
  for (const t of ticks) {
    const y = H - B - (t / max) * (H - B - T);
    svg += `<line class="grid-l" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/>`
      + `<text class="axis-t" x="${L - 6}" y="${y + 3}" text-anchor="end">${fmtN(Math.round(t))}</text>`;
  }
  items.forEach((it, i) => {
    const h = Math.max(1, (it.value / max) * (H - B - T));
    const x = L + slot * i + (slot - bw) / 2, y = H - B - h;
    const r = Math.min(4, h / 2);
    svg += `<path class="bar" fill="#2f5bd8" data-tip="${escAttr(it.tip || `${it.label} ${fmtN(it.value)}${unit || ""}`)}" `
      + `d="M${x},${H - B} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${H - B} Z"/>`
      + `<text class="val-t" x="${x + bw / 2}" y="${y - 4}" text-anchor="middle">${fmtN(it.value)}</text>`
      + `<text class="axis-t" x="${x + bw / 2}" y="${H - B + 14}" text-anchor="middle">${escAttr(it.label.length > 12 ? it.label.slice(0, 11) + "…" : it.label)}</text>`;
  });
  return svg + `</svg>`;
}
/* 가로 막대 — 이름이 긴 리비전 목록에 맞다. */
function hbars(items) {
  if (!items.length) return `<div class="chart-empty">완료된 분석이 없습니다</div>`;
  const W = 420, rowH = 20, T = 6, L = 120, R = 46;
  const H = T * 2 + rowH * items.length;
  const max = niceMax(Math.max(...items.map(i => i.value)));
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="가로 막대 그래프">`;
  items.forEach((it, i) => {
    const y = T + rowH * i + 4, bh = rowH - 8;
    const w = Math.max(1, (it.value / max) * (W - L - R));
    const r = Math.min(4, bh / 2);
    const lab = it.label.length > 18 ? it.label.slice(0, 17) + "…" : it.label;
    svg += `<text class="axis-t" x="${L - 8}" y="${y + bh / 2 + 3}" text-anchor="end">${escAttr(lab)}</text>`
      + `<path class="bar" fill="#2f5bd8" data-tip="${escAttr(it.tip)}" d="M${L},${y} H${L + w - r} Q${L + w},${y} ${L + w},${y + r} V${y + bh - r} Q${L + w},${y + bh} ${L + w - r},${y + bh} H${L} Z"/>`
      + `<text class="val-t" x="${L + w + 5}" y="${y + bh / 2 + 3}">${fmtN(it.value)}</text>`;
  });
  return svg + `</svg>`;
}
/* 도넛 — 서버 counts 그대로.  색은 검증기 통과 (blue · amber · teal · red, 대조 안 함은 회색). */
const DONUT_PARTS = [
  ["UNCHANGED", "변경 없음", "#2f5bd8"],
  ["ADDED", "추가", "#b07614"],
  ["MODIFIED", "수정", "#0f8f80"],
  ["DELETED_CANDIDATE", "삭제 후보", "#c2453f"],
  ["NOT_COMPARED", "대조 안 함 (태그 없음)", "#a3acbd"],
];
function donut(c) {
  const parts = DONUT_PARTS.map(([k, label, color]) => ({
    label, color, value: (c[k] || 0) + (k === "MODIFIED" ? (c.MODIFIED_BEFORE || 0) : 0) })).filter(p => p.value > 0);
  const total = parts.reduce((a, p) => a + p.value, 0);
  if (!total) return `<div class="chart-empty">비교한 리비전이 아직 없습니다 — 같은 프로젝트에 두 번째 리비전을 넣으면 여기에 섭니다</div>`;
  const R = 60, r = 40, cx = 75, cy = 75;
  let a0 = -Math.PI / 2, svg = `<svg viewBox="0 0 150 150" role="img" aria-label="개정 변경 도넛">`;
  for (const p of parts) {
    const frac = p.value / total, a1 = a0 + frac * Math.PI * 2;
    const gap = parts.length > 1 ? 0.012 : 0;
    const s0 = a0 + gap, s1 = Math.max(s0 + 0.001, a1 - gap), large = s1 - s0 > Math.PI ? 1 : 0;
    const P = (rad, a) => `${(cx + rad * Math.cos(a)).toFixed(2)},${(cy + rad * Math.sin(a)).toFixed(2)}`;
    const d = frac >= 0.9999
      ? `M${cx - R},${cy} A${R},${R} 0 1 1 ${cx + R},${cy} A${R},${R} 0 1 1 ${cx - R},${cy} M${cx - r},${cy} A${r},${r} 0 1 0 ${cx + r},${cy} A${r},${r} 0 1 0 ${cx - r},${cy} Z`
      : `M${P(R, s0)} A${R},${R} 0 ${large} 1 ${P(R, s1)} L${P(r, s1)} A${r},${r} 0 ${large} 0 ${P(r, s0)} Z`;
    svg += `<path class="bar" fill="${p.color}" fill-rule="evenodd" data-tip="${escAttr(`${p.label} ${fmtN(p.value)} (${(frac * 100).toFixed(1)}%)`)}" d="${d}"/>`;
    a0 = a1;
  }
  svg += `<text x="${cx}" y="${cy + 2}" text-anchor="middle" style="font-size:20px;font-weight:700;fill:var(--fg)">${fmtN(total)}</text>`
    + `<text x="${cx}" y="${cy + 18}" text-anchor="middle" class="axis-t">행</text></svg>`;
  const legend = `<ul class="legend">` + parts.map(p => `<li><span class="sw" style="background:${p.color}"></span>${escAttr(p.label)}`
    + `<span class="lv">${fmtN(p.value)} · ${(p.value / total * 100).toFixed(0)}%</span></li>`).join("") + `</ul>`;
  return `<div class="donut-wrap">${svg}${legend}</div>`;
}
/* 마우스를 올리면 값 — 모든 그래프가 같은 말풍선 하나를 쓴다 */
(function chartTips() {
  const tip = $("#chart-tip");
  const host = $("#home-charts");
  if (!tip || !host) return;
  host.addEventListener("mousemove", ev => {
    const m = ev.target.closest("[data-tip]");
    if (!m) { tip.classList.add("hidden"); return; }
    tip.textContent = m.getAttribute("data-tip");
    tip.classList.remove("hidden");
    const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = `${x}px`; tip.style.top = `${ev.clientY + 14}px`;
  });
  host.addEventListener("mouseleave", () => tip.classList.add("hidden"));
})();
/* 바로가기 · 알림 알약 */
document.addEventListener("click", ev => {
  const g = ev.target.closest("#home-kpis [data-go], #home-pills [data-go]");
  if (!g) return;
  ev.preventDefault();
  const go = g.dataset.go;
  if (go.startsWith("#")) { location.hash = go.slice(1); return; }
  const target = go === "audit" ? ".note-card" : go === "recent" ? ".recent-card" : ".list-card";
  const el = document.querySelector(target);
  if (el) { el.scrollIntoView({ behavior: "smooth", block: "start" }); el.classList.add("home-highlight"); setTimeout(() => el.classList.remove("home-highlight"), 1500); }
});

/* hotfix50 — 대시보드 안 (EMBED 는 파일 머리에서 읽었다).
 * 왼쪽 메뉴를 숨기고, 메뉴에 있던 결과 탭은 결과 머리 아래 줄로 옮긴다 — 요소를 옮길 뿐이라
 * `buildTabs` 는 그대로다 (hotfix49 가 머리줄에서 메뉴로 옮길 때와 같은 방식).  첫 화면으로는
 * 결과 머리의 `← 첫 화면` 으로 간다. */
(function applyEmbed() {
  if (EMBED.user) { rememberAuthor(EMBED.user); renderNav(); }
  renderWhoChip();
  if (EMBED.mode && !S.project) { S.mode = EMBED.mode; showMode(S.mode); }
  const from = $("#embed-from");
  if (from && EMBED.mode) {
    const w = MODE_WORD[EMBED.mode];
    from.textContent = `${w} 프로젝트 메뉴에서 열림 — 새 프로젝트는 ${w}${EMBED.mode === "bid" ? "로" : "으로"} 시작합니다`;
    from.classList.remove("hidden");
  }
  if (!EMBED.on) return;
  document.body.classList.add("embed");
  const slot = $("#embed-tabs"), tabs = $("#tabs");
  if (slot && tabs) { slot.appendChild(tabs); slot.classList.remove("hidden"); }
  setTimeout(() => window.dispatchEvent(new Event("resize")), 0);   // 도면 창 폭이 메뉴만큼 넓어졌다
})();
