"""hotfix132 — P&ID 화면 다듬기 (실패가 묻히지 않음 · 브라우저 대화상자 없음 · 삭제 한 창 · 꼬리줄 · 용어 · 첫 화면)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _fn(start):
    i = JS.index(start)
    return JS[i:JS.index("\n}\n", i) + 3]


def _code(js):
    """주석을 뺀 코드 (// 꼬리 · /* */ 블록)."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", ln) for ln in js.split("\n"))


def _visible_html(html):
    return re.sub(r"<!--.*?-->", "", html, flags=re.S)


# ---------------- B1 실패가 조용히 묻히지 않는다
def test_global_error_handlers_are_throttled_and_skip_offline():
    assert 'addEventListener("unhandledrejection"' in JS and 'addEventListener("error"' in JS
    g = JS[JS.index("(function globalErrors()"):JS.index("})();", JS.index("(function globalErrors()"))]
    assert "AbortError" in g and "OFFLINE.down" in g and "NET.down" in g and "8000" in g
    assert "preventDefault" not in g          # 콘솔 기록은 그대로 남긴다


def test_fetch_json_keeps_the_server_detail_and_names_three_failures():
    f = _fn("async function fetchJson(")
    assert "body.detail" in f and "서버 오류 (${r.status})" in f
    assert "서버가 올바른 응답을 주지 않았습니다" in f and "서버에 연결할 수 없습니다" in f
    assert "err.net = true" in f              # 띠는 offline.js · hookFetch 몫 — 여기서 새로 만들지 않는다


def test_lists_and_project_create_say_why_in_place():
    home = JS[JS.index("async function listHome("):JS.index("const listJobs = listHome;")]
    assert 'fetchJson("/home")' in home and "loadFailHtml(" in home and "joblist-retry" in home
    lp = _fn("async function loadProjects(")
    assert 'fetchJson("/projects")' in lp and "proj-retry" in lp
    save = JS[JS.index('$req("#proj-save")'):JS.index('$req("#proj-save")') + 1500]
    assert "서버에 연결할 수 없어 프로젝트를 만들지 못했습니다" in save
    rc = _fn("async function recompare(")
    assert "fetchJson(`/jobs/${jobId}/revision`" in rc


def test_watch_reports_a_lost_connection_and_a_missing_job():
    w = JS[JS.index("function watch(jobId, pageCount, what)"):JS.index("src.onmessage = (ev) =>")]
    assert "src.onerror" in w and "EventSource.CLOSED" in w
    assert "분석 기록이 서버에 없습니다" in w and "서버와 연결이 끊겼습니다" in w
    assert "e.status === 404" in w and "fetchJson(`/jobs/${jobId}`)" in w


# ---------------- B2 브라우저 대화상자 대신 화면 안 창
def test_no_browser_dialogs_remain():
    code = _code(JS)
    assert not re.search(r"(?<![\w.])alert\(", code)
    assert not re.search(r"(?<![\w.])prompt\(", code)
    assert not re.search(r"window\.(confirm|prompt|alert)\(", code)
    # 남은 confirm( 은 셸에 맡기는 SH.confirm 하나뿐
    assert [m.group(0) for m in re.finditer(r"[\w.]*confirm\(", code) if not m.group(0).startswith("askConfirm")] \
        == ["SH.confirm("]


def test_helpers_delegate_to_the_shell_when_present_and_unblock_on_close():
    assert "function notify(" in JS and "function askConfirm(" in JS and "function askText(" in JS
    for name in ("function notify(", "function askConfirm(", "function askText("):
        assert "window.PID_SHELL" in _fn(name)          # 부를 때마다 읽는다 (셸이 뒤에 실려도)
    close = _fn("function closeModal(")
    assert "S.modalPending" in close and "S.modalPrev" in close
    opn = _fn("function openModal(")
    assert "S.modalPending" in opn


def test_in_modal_deletes_ask_inline_not_in_a_new_modal():
    assert "function armDelete(" in JS
    rep = JS[JS.index("async function showReportList("):JS.index('$req("#report-list")')]
    assert "armDelete(btn)" in rep and "inlineEdit(row" in rep
    sym = JS[JS.index("async function showSymbolRegister("):JS.index("function symbolForm(")]
    assert "armDelete(btn)" in sym


# ---------------- B3 삭제는 창 하나
def test_delete_is_one_dialog_with_copy_and_the_server_contract_kept():
    d = _fn("function deleteDialog(")
    assert "del-copy" in d and "navigator.clipboard" in d and "del-typed" in d and "del-author" in d
    assert 'class="danger"' in d and "typed !== o.expected" in d
    rq = _fn("async function deleteRequest(")
    assert 'body.append("confirm", typed)' in rq and "지워지지 않았습니다" in rq
    job = _fn("async function askDelete(")
    assert "expected: String(jobId)" in job and "rememberAuthor(author)" in job and "afterDelete()" in job
    proj = _fn("async function askDeleteProject(")
    assert "expected: String(pv.project)" in proj and 'localStorage.setItem("pid.author"' in proj
    assert "다른 사람이 만든 기록이 있습니다" in proj


# ---------------- B4 꼬리줄
def test_footer_is_version_and_update_date_only():
    blk = JS[JS.index("/* ---------------- which build this is ---------------- */"):]
    blk = blk[:blk.index("})();") + 5]
    assert "버전 ${ver}" in blk and "업데이트 ${String(d).slice(0, 10)}" in blk
    for gone in ("u.zip", "u.rev", "base_commit", "branch", "(source)", "hotfix34 이전"):
        assert gone not in blk
    assert "v.ui.app_js" in blk               # 캐시 진단용 화면 파일 딱지는 툴팁에만
    assert "window.PID_SHELL && !EMBED.on" in blk


# ---------------- B5 개발 용어 정리
BAD = re.compile(r"hotfix\d+|회차|자칭|\bDashboard\b|홈 \(대시보드\)|개발팀|>VOC<|VOC 로|데이터 위생|학습 자료")


def test_visible_html_has_no_developer_words():
    vis = _visible_html(HTML)
    hits = [ln.strip() for ln in vis.split("\n") if BAD.search(ln)]
    assert hits == [], hits
    assert "<title>P&amp;ID 리스트 추출 · 계장 설계 도구</title>" in HTML
    assert 'href="/dcs"' in HTML and "DCS 그래픽" in HTML and "LOGIC 작도" in HTML
    assert "SAMSUNG C&amp;T" not in HTML and "P&amp;ID EXTRACTOR" not in HTML   # 이름은 product.json 한 곳에서
    for keep in ('id="home-voc"', 'id="voc-btn"', 'id="prog-voc"', 'id="audit-line"', 'id="build-text"', 'id="file"'):
        assert keep in HTML


def test_js_strings_have_no_developer_words():
    code = _code(JS)
    strs = re.findall(r'"(?:[^"\\\n]|\\.)*"|`(?:[^`\\]|\\.)*`', code)
    bad = [s[:80] for s in strs if re.search(r"hotfix\d+|자칭|개발팀|VOC 함|VOC \$\{|데이터 위생|학습 자료|판정 지문", s)]
    assert bad == [], bad
    assert '["VOC", "식별 평가"]' in JS        # 키는 그대로 · 이름표만


def test_audit_card_hides_when_clean():
    a = _fn("async function showAudit(")
    assert "보관 자료 점검" in a and 'card.classList.toggle("hidden", !bad.length)' in a
    assert 'class="card note-card hidden"' in HTML
    dash = _fn("function renderDashboard(")
    assert "이상 없음" not in dash


# ---------------- B6 첫 화면 · 키보드
def test_first_screen_empty_state_and_keyboard_file_pick():
    home = JS[JS.index("async function listHome("):JS.index("const listJobs = listHome;")]
    assert "아직 프로젝트가 없습니다" in home
    assert '<button type="button" id="file-btn" class="link" disabled>파일 선택</button>' in HTML
    assert re.search(r'id="drop-zone"[^>]*tabindex="0"', HTML)
    assert '$("#file-btn").disabled = !S.setupDone' in JS
    assert 'ev.target.value = ""' in JS
    assert "button.link" in CSS and ".drop-zone:focus-visible" in CSS
    assert "window.innerWidth < 1280" in JS
    assert 'id="excel" disabled title="[전체 검토 완료] 에 체크하면 출력할 수 있습니다"' in HTML


def test_embed_padding_rule_is_untouched():
    assert "body.embed, body.embed.nav-collapsed { padding-left: 0; }" in CSS
