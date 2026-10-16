"""hotfix42 — 품질팀 시뮬레이션: API 전수 · 화면 전수 클릭 · 합성 PDF 전 흐름.

    python3 spike/qa_sim.py <data_dir(복사해서 씀)> <out_dir> [--rounds N] [--e2e] [--no-ui]

A. 모든 GET 경로를 실제 id 로 두드리고, 쓰기 경로는 올바른 입력으로 한 번씩 돈다 — 5xx 는 전부 결함.
B. 결과 화면의 버튼·탭·필터·열 메뉴·행·오버레이·대화상자를 **전부 눌러 본다** (재분석만 뺀다) —
   페이지 오류 · 콘솔 오류 · 서버 5xx 를 센다.  rounds 만큼 장을 바꿔 가며 반복한다.
C. (--e2e) 프로젝트 생성 → 합성 PDF Rev.A 분석 → 편집·마크업·저장·스냅샷 → Rev.B 분석(비교) →
   개정 API · 나란히 · 변경 내역 Excel → 범례 없는 PDF(실패 경로) → 분석 삭제 → 프로젝트 삭제.
실 데이터는 건드리지 않는다 — data_dir 을 통째로 복사해 그 사본에서 돈다.
"""
from __future__ import annotations
import json, os, shutil, socket, subprocess, sys, time, urllib.request, urllib.error, urllib.parse, re, random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
SRC, OUT = Path(args[0]), Path(args[1])
ROUNDS = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 2
E2E = "--e2e" in sys.argv
UI = "--no-ui" not in sys.argv
OUT.mkdir(parents=True, exist_ok=True)
DATA = Path("/tmp/qa_sim_data")
if DATA.exists(): shutil.rmtree(DATA)
shutil.copytree(SRC, DATA)
FOUND: list[str] = []
DEFECTS: list[str] = []
def note(s): print(s, flush=True); FOUND.append(s)
def defect(s): print("★ " + s, flush=True); DEFECTS.append(s); FOUND.append("★ " + s)

s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
BASE = f"http://127.0.0.1:{PORT}"
env = dict(os.environ, PID_DATA_DIR=str(DATA), PYTHONPATH=str(ROOT))
slog = open(OUT / "server.log", "w")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=str(ROOT), env=env, stdout=slog, stderr=subprocess.STDOUT)

def req(method, path, data=None, form=None, files=None, timeout=300, raw=False):
    """(status, body).  form=dict → x-www-form-urlencoded · files → multipart · data → json."""
    url = BASE + path
    body = None; headers = {}
    if files is not None:
        boundary = "----qa" + str(random.randint(1, 10**9))
        parts = []
        for k, v in (form or {}).items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
        for k, (fname, blob) in files.items():
            parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fname}\"\r\nContent-Type: application/octet-stream\r\n\r\n".encode() + blob + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts); headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif form is not None:
        body = urllib.parse.urlencode(form).encode(); headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif data is not None:
        body = json.dumps(data).encode(); headers["Content-Type"] = "application/json"
    rq = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            b = r.read()
            return r.status, (b if raw else _j(b))
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, (b if raw else _j(b))
def _j(b):
    try: return json.loads(b)
    except Exception: return b[:200]

def server_errors():
    slog.flush()
    txt = (OUT / "server.log").read_text(errors="ignore")
    return txt.count("Traceback (most recent call last)"), txt.count(" 500 ")

for _ in range(90):
    try: urllib.request.urlopen(BASE + "/home", timeout=2); break
    except Exception: time.sleep(1)

# ----------------------------------------------------------------------------- A. API
note("## A. API 전수")
st, jobs = req("GET", "/jobs")
done = [j for j in jobs if j.get("status") == "done"]
jobB = max(done, key=lambda j: j.get("created_at") or "")["id"] if done else None
jobA = min(done, key=lambda j: j.get("created_at") or "")["id"] if len(done) > 1 else None
note(f"jobs {len(jobs)} · done {len(done)} · B {jobB} · A {jobA}")
st, rows = req("GET", f"/jobs/{jobB}/rows?tab=ALL")
key = rows[0]["key"]; pageB = rows[0]["page_no"]
tagged = next((r for r in rows if r["values"].get("tag_no")), rows[0])
st, projects = req("GET", "/projects"); pname = (projects[0]["name"] if projects else "")
st, rev = req("GET", f"/jobs/{jobB}/revision")
del_id = (rev.get("deleted_candidates") or [{}])[0].get("id", "")
gets = ["/", "/version", "/home", "/jobs", "/projects", f"/projects/{pname}", f"/projects/{pname}/deletion_preview",
        "/audit", "/deletions", "/symbols/global", "/templates", "/favicon.ico",
        f"/jobs/{jobB}", f"/jobs/{jobB}/pages", f"/jobs/{jobB}/rows?tab=ALL", f"/jobs/{jobB}/rows?tab=REVIEW", f"/jobs/{jobB}/rows?tab=FIELD",
        f"/jobs/{jobB}/review", f"/jobs/{jobB}/revision", f"/jobs/{jobB}/revisions", f"/jobs/{jobB}/drawings", f"/jobs/{jobB}/feedback",
        f"/jobs/{jobB}/feedback?limit=1", f"/jobs/{jobB}/legend_profile", f"/jobs/{jobB}/markup", f"/jobs/{jobB}/measured_config",
        f"/jobs/{jobB}/mode", f"/jobs/{jobB}/multipliers", f"/jobs/{jobB}/notes/{pageB}", f"/jobs/{jobB}/page/{pageB}.png?zoom=0.3",
        f"/jobs/{jobB}/reports", f"/jobs/{jobB}/scope_summary", f"/jobs/{jobB}/sheet_numbers", f"/jobs/{jobB}/titleblock",
        f"/jobs/{jobB}/unjudged", f"/jobs/{jobB}/axis_overrides", f"/jobs/{jobB}/error_detail", f"/jobs/{jobB}/deletion_preview",
        f"/jobs/{jobB}/revision/changes.xlsx", f"/jobs/{jobB}/rows/{key}/history", f"/jobs/{jobB}/rows/{key}/axis_candidates",
        f"/jobs/{jobB}/feedback_export", "/jobs/nope", "/jobs/nope/rows", "/projects/nope", f"/jobs/{jobB}/page/999.png", f"/jobs/{jobB}/notes/999"]
bad = []
for g in gets:
    t0 = time.time(); st, body = req("GET", g, raw=True); dt = time.time() - t0
    if st >= 500: bad.append((g, st)); defect(f"GET {g} → {st} ({dt:.1f}s)")
    elif st >= 400 and "nope" not in g and "999" not in g: note(f"  GET {g} → {st} (유효 id 인데 4xx — 확인) {body[:120]!r}")
    if dt > 5: note(f"  느림 {dt:.1f}s GET {g}")
note(f"GET {len(gets)}개 · 5xx {len(bad)}")

# 쓰기 경로 — 사본이므로 마음껏
def chk(label, st, body, ok=(200, 201)):
    if st >= 500: defect(f"{label} → {st} {str(body)[:160]}")
    elif st not in ok: note(f"  {label} → {st} {str(body)[:160]}")
    else: note(f"  {label} → {st}")
    return st, body
qty0 = rows[0]["values"].get("qty")
chk("PATCH qty", *req("PATCH", f"/jobs/{jobB}/rows/{key}", data={"field": "qty", "value": "7", "author": "QA"}))
chk("PATCH qty 되돌림", *req("PATCH", f"/jobs/{jobB}/rows/{key}", data={"field": "qty", "value": "", "author": "QA"}))
chk("PATCH scope", *req("PATCH", f"/jobs/{jobB}/rows/{key}", data={"field": "scope", "value": "VENDOR(QA)", "author": "QA"}))
chk("PATCH scope 되돌림", *req("PATCH", f"/jobs/{jobB}/rows/{key}", data={"field": "scope", "value": "", "author": "QA"}))
chk("PATCH 없는 칸", *req("PATCH", f"/jobs/{jobB}/rows/{key}", data={"field": "nonsense", "value": "x", "author": "QA"}), ok=(400, 422))
chk("PATCH 없는 행", *req("PATCH", f"/jobs/{jobB}/rows/nokey", data={"field": "qty", "value": "1", "author": "QA"}), ok=(404,))
codes = rows[0].get("review_codes") or []
if codes: chk("PATCH review state", *req("PATCH", f"/jobs/{jobB}/rows/{key}/review/{codes[0]}", data={"state": "CONFIRMED", "note": "qa"}))
st, added = chk("POST rows (마크업)", *req("POST", f"/jobs/{jobB}/rows", data={"page_no": pageB, "tab": "FIELD", "rect": [100, 100, 130, 120], "values": {"type": "PIT", "qty": 1}, "author": "QA", "reason_class": "MISSING", "note": "qa"}))
akey = (added or {}).get("key") if isinstance(added, dict) else None
if akey:
    chk("GET history(추가행)", *req("GET", f"/jobs/{jobB}/rows/{akey}/history"))
    chk("DELETE rows(추가행)", *req("DELETE", f"/jobs/{jobB}/rows/{akey}?reason=qa&reason_class=FALSE_POSITIVE&author=QA"))
    chk("POST restore", *req("POST", f"/jobs/{jobB}/rows/{akey}/restore"))
chk("DELETE 검출행(오검출 표시)", *req("DELETE", f"/jobs/{jobB}/rows/{key}?reason=qa&reason_class=WRONG_VALUE&author=QA&exclude=false"))
chk("POST restore 검출행", *req("POST", f"/jobs/{jobB}/rows/{key}/restore"))
chk("POST copy", *req("POST", f"/jobs/{jobB}/rows/{key}/copy"))
chk("POST propose", *req("POST", f"/jobs/{jobB}/markup/propose", data={"page_no": pageB, "rect": [100, 100, 130, 120]}))
chk("POST axis_text", *req("POST", f"/jobs/{jobB}/axis_text", data={"page_no": pageB, "rect": [100, 100, 400, 300]}), ok=(200, 400, 422))
st, rep = chk("POST reports", *req("POST", f"/jobs/{jobB}/reports", data={"row_key": key, "kind": "ROW", "what": "QTY", "detail": "qa", "author": "QA"}))
rid = (rep or {}).get("id") if isinstance(rep, dict) else None
if rid:
    chk("PATCH report", *req("PATCH", f"/reports/{rid}", data={"detail": "qa2"}))
    chk("DELETE report", *req("DELETE", f"/reports/{rid}"))
chk("POST multipliers", *req("POST", f"/jobs/{jobB}/multipliers", form={"unit": "00", "multiplier": 2, "author": "QA"}), ok=(200, 400))
chk("DELETE multipliers", *req("DELETE", f"/jobs/{jobB}/multipliers/00"), ok=(200, 404, 400))
chk("POST sheet_numbers", *req("POST", f"/jobs/{jobB}/sheet_numbers", form={"page": 1, "drawing_no": "QA-1", "author": "QA"}), ok=(200, 400))
chk("DELETE sheet_numbers", *req("DELETE", f"/jobs/{jobB}/sheet_numbers/1"), ok=(200, 404, 400))
chk("POST titleblock/preview", *req("POST", f"/jobs/{jobB}/titleblock/preview", data={"cells": {"dwg_no_region": [100, 100, 300, 120]}, "page_no": pageB}), ok=(200, 400, 422))
chk("POST titleblock", *req("POST", f"/jobs/{jobB}/titleblock", data={"cells": {"dwg_no_region": [100, 100, 300, 120]}, "page_no": pageB, "author": "QA"}), ok=(200, 400, 422))
chk("DELETE titleblock", *req("DELETE", f"/jobs/{jobB}/titleblock"), ok=(200, 404, 400))
chk("POST snapshot", *req("POST", f"/jobs/{jobB}/snapshot", data={"author": "QA"}))
chk("POST save", *req("POST", f"/jobs/{jobB}/save", data={"author": "QA"}))
st, snaps = req("GET", f"/jobs/{jobB}/revisions")
if snaps: chk("GET revisions/{id}/excel", *req("GET", f"/revisions/{snaps[-1]['id']}/excel", raw=True), ok=(200, 400))
if del_id:
    chk("POST deleted confirm", *req("POST", f"/jobs/{jobB}/deleted/{del_id}/confirm?confirmed=true"))
    chk("POST deleted unconfirm", *req("POST", f"/jobs/{jobB}/deleted/{del_id}/confirm?confirmed=false"))
chk("PATCH project mode", *req("PATCH", f"/projects/{pname}/mode", form={"mode": "epc", "author": "QA"}))
chk("PATCH project mode auto", *req("PATCH", f"/projects/{pname}/mode", form={"mode": "", "author": "QA"}))
chk("POST symbols/global", *req("POST", "/symbols/global", form={"symbol_id": "QA-SYM", "kind": "INSTRUMENT", "name": "qa", "author": "QA", "meaning": "qa", "text": "QA"}), ok=(200, 400, 422))
chk("POST symbols/global/enabled", *req("POST", "/symbols/global/enabled", form={"on": "true"}))
chk("DELETE symbols/global", *req("DELETE", "/symbols/global/QA-SYM"), ok=(200, 404))
chk("POST diagnostic", *req("POST", f"/jobs/{jobB}/diagnostic"))
chk("POST projects 중복", *req("POST", "/projects", form={"name": pname}), ok=(409,))
chk("POST projects 새", *req("POST", "/projects", form={"name": "QA-TMP"}))
chk("DELETE projects 확인없이", *req("DELETE", "/projects/QA-TMP", form={"author": "QA", "confirm": "wrong"}), ok=(400, 409, 422))
chk("DELETE projects", *req("DELETE", "/projects/QA-TMP", form={"author": "QA", "confirm": "QA-TMP"}))
chk("POST jobs 빈 파일", *req("POST", "/jobs", form={"project": ""}, files={"pdf": ("x.pdf", b"not a pdf")}), ok=(400, 415, 422))
tb, s500 = server_errors(); note(f"A 끝 — 서버 Traceback {tb} · 500 {s500}")

# ----------------------------------------------------------------------------- B. UI
if UI:
    note("## B. 화면 전수 클릭")
    from playwright.sync_api import sync_playwright
    exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append("pageerror: " + str(e)[:300]))
        pg.on("console", lambda m: errs.append("console: " + m.text[:300]) if m.type == "error" and "favicon" not in m.text else None)
        pg.on("dialog", lambda d: d.accept("QA") if d.type in ("prompt",) else d.accept())
        def step(label, fn, settle=600):
            n0 = len(errs); tb0, _ = server_errors()
            try: fn()
            except Exception as e:
                note(f"  {label}: 동작 실패 — {str(e)[:160]}")
                # 무엇이 가리고 있나 — 첫 실패마다 화면과 가리는 요소를 남긴다
                try:
                    cover = pg.evaluate("""() => { const el = document.querySelector('#body tr'); if (!el) return 'no rows';
                        const r = el.getBoundingClientRect(); const top = document.elementFromPoint(r.x + 20, r.y + 5);
                        return {row: [r.x, r.y, r.width, r.height], top: top ? (top.tagName + '#' + top.id + '.' + top.className) : null,
                                rightCompare: document.querySelector('#right').className, modal: document.querySelector('#modal').className}; }""")
                    note(f"     가림: {cover}")
                    pg.screenshot(path=str(OUT / f"fail_{re.sub(r'[^a-zA-Z0-9가-힣]+', '_', label)[:40]}.png"))
                except Exception: pass
            pg.wait_for_timeout(settle)
            tb1, _ = server_errors()
            if len(errs) > n0 or tb1 > tb0:
                defect(f"{label}: 페이지 오류 {errs[n0:][:2]} · 서버 Traceback +{tb1 - tb0}")
                pg.screenshot(path=str(OUT / f"err_{re.sub(r'[^a-zA-Z0-9가-힣]+', '_', label)[:40]}.png"))
        def ready():
            pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        def close_overlays():
            pg.keyboard.press("Escape")
            # 신고·심볼·템플릿 등은 #modal 하나를 쓴다 — 열려 있으면 닫는다 (그 위에서는 목록을 못 누른다)
            try: pg.evaluate("() => { if (typeof closeModal === 'function') closeModal(); }")
            except Exception: pass
            for sel in ["#dlg button.close", ".dialog button.close", "button:has-text('닫기')", "#tbfix-close", "#pick-cancel"]:
                for el in pg.query_selector_all(sel):
                    try:
                        if el.is_visible(): el.click(timeout=800)
                    except Exception: pass
        # 첫 화면
        step("첫 화면 열기", lambda: (pg.goto(BASE + "/"), pg.wait_for_selector("#home, .intake, #drop", timeout=60000)))
        step("첫 화면 버튼들", lambda: [b.click(timeout=800) for b in pg.query_selector_all("#proj-new-btn, #proj-cancel") if b.is_visible()])
        step("결과 열기 (최신)", lambda: (pg.goto(f"{BASE}/#{jobB}"), ready()))
        for rnd in range(ROUNDS):
            note(f"-- round {rnd + 1}")
            pages = pg.evaluate("() => S.pages.filter(p => p.layers && Object.keys(p.layers).length).map(p => p.page_no)")
            target = pages[(rnd * 7) % len(pages)]
            step(f"장 선택 p{target}", lambda: (pg.select_option("#page-select", str(target)), pg.wait_for_timeout(1500)))
            # 나란히 보기가 켜져 있으면 목록이 숨는다 (설계) — 목록·필터를 누르려면 끈다
            if pg.evaluate("() => !!S.side"): step("나란히 끔(목록 보려고)", lambda: pg.click("#rev-switch button.side"), settle=800)
            for bid in ["save-final", "excel", "symbols", "report-list", "diag", "feedback-export", "infobars-toggle", "markup-toggle", "markup-toggle", "ovl-fold", "ovl-fold", "row-add", "pick-cancel", "row-copy", "row-delete", "to-home"]:
                if bid == "to-home": continue
                el = pg.query_selector(f"#{bid}")
                if not el or not el.is_visible(): continue
                if el.get_attribute("disabled") is not None: note(f"  버튼 #{bid} 비활성"); continue
                step(f"버튼 #{bid}", lambda bid=bid: pg.click(f"#{bid}", timeout=3000), settle=900)
                close_overlays()
            ntabs = pg.locator("#tabs button, #tabs a, #tabs .tab").count()
            for i in range(min(ntabs, 8)):
                step(f"탭 {i}", lambda i=i: pg.locator("#tabs button, #tabs a, #tabs .tab").nth(i).click(timeout=2000), settle=500)
            step("검토 필요만", lambda: pg.click("#only-review"), settle=500)
            step("검토 필요만 해제", lambda: pg.click("#only-review"), settle=500)
            if pg.query_selector("#only-changed") and pg.is_visible("#only-changed"):
                step("개정된 행만", lambda: pg.click("#only-changed")); step("개정된 행만 해제", lambda: pg.click("#only-changed"))
            if pg.query_selector("#rev-filter") and pg.is_visible("#rev-filter"):
                for v in ["ADDED", "MODIFIED", "DELETED", ""]:
                    step(f"개정 필터 {v or '전체'}", lambda v=v: pg.select_option("#rev-filter", v), settle=400)
            step("검색어", lambda: pg.fill("#filter", "PIT"), settle=600); step("검색어 지움", lambda: pg.fill("#filter", ""), settle=400)
            nh = pg.locator("#grid thead th").count()
            for i in range(min(nh, 12)):
                step(f"열 머리 {i}", lambda i=i: pg.locator("#grid thead th").nth(i).click(timeout=1500), settle=350); close_overlays()
            nb = pg.locator("#grid thead th button").count()
            for i in range(min(nb, 6)):
                step(f"열 메뉴 {i}", lambda i=i: pg.locator("#grid thead th button").nth(i).click(timeout=1500), settle=350); close_overlays()
            for i in range(min(pg.locator("#body tr").count(), 5)):
                step(f"행 클릭 {i}", lambda i=i: pg.locator("#body tr").nth(i).click(timeout=2000), settle=700)
                # hotfix73 — 손잡이를 쥐고 있지 않는다.  패널이 누를 때마다 다시 그려져 옛 손잡이는
                # "not attached" 가 되고, 그 거짓 경보가 진짜 결함을 가린다 (73회차 첫 실행).  매번 다시 찾는다.
                n_ev = len([b for b in pg.query_selector_all("#evidence button") if b.is_visible()])
                for j in range(min(n_ev, 6)):
                    evb = [b for b in pg.query_selector_all("#evidence button") if b.is_visible()]
                    if j >= len(evb): break
                    txt = (evb[j].inner_text() or "")[:14]
                    if any(x in txt for x in ("삭제", "지우", "확정", "다시 분석", "재분석")): continue
                    step(f"근거 패널 버튼 {j} '{txt}'", lambda j=j: [b for b in pg.query_selector_all("#evidence button") if b.is_visible()][j].click(timeout=1500), settle=500); close_overlays()
            step("셀 편집 qty", lambda: (pg.dblclick("#body tr:first-child td[data-col=qty]"), pg.keyboard.type("3"), pg.keyboard.press("Enter")), settle=1200)
            step("셀 편집 qty 되돌림", lambda: (pg.dblclick("#body tr:first-child td[data-col=qty]"), pg.keyboard.press("Control+A"), pg.keyboard.press("Backspace"), pg.keyboard.press("Enter")), settle=1200)
            for z in ["1", "1", "-1", "0"]:
                step(f"확대 {z}", lambda z=z: pg.click(f"#left .toolbar button[data-z='{z}']"), settle=300)
            step("도면 상자 클릭", lambda: pg.click("#ov rect.det >> nth=0", timeout=3000), settle=700)
            if pg.evaluate("() => document.querySelector('#ovlegend')?.classList.contains('folded')"):
                step("범례 판 펼침", lambda: pg.click("#ovl-fold"), settle=300)
            for k in range(min(6, len(pg.query_selector_all("#ovl-items input[type=checkbox]")))):
                sel = f"#ovl-items input[type=checkbox] >> nth={k}"
                step("오버레이 토글", lambda sel=sel: pg.click(sel, timeout=1000), settle=250)
                step("오버레이 토글 복귀", lambda sel=sel: pg.click(sel, timeout=1000), settle=250)
            step("탭 색으로", lambda: pg.click("#ovl-bytab"), settle=400); step("탭 색 해제", lambda: pg.click("#ovl-bytab"), settle=300)
            if pg.query_selector("#rev-switch button.side") and pg.is_visible("#rev-switch button.side"):
                if not pg.evaluate("() => S.side"): step("나란히 켬", lambda: pg.click("#rev-switch button.side"), settle=3000)
                if pg.query_selector("#cmp-changes button[data-step='1']"):     # 변경 없는 장에는 단추가 없다
                    step("변경 ▶", lambda: pg.click("#cmp-changes button[data-step='1']"), settle=800)
                    step("변경 ◀", lambda: pg.click("#cmp-changes button[data-step='-1']"), settle=800)
                step("Alt+→", lambda: pg.keyboard.press("Alt+ArrowRight"), settle=600)
                opts = pg.evaluate("() => Array.from(document.querySelectorAll('#cmp-pick option')).map(o => o.value)")
                if len(opts) > 2: step("오른쪽 장 고름", lambda: pg.select_option("#cmp-pick", opts[2]), settle=2500)
                step("오른쪽 장 자동", lambda: pg.select_option("#cmp-pick", ""), settle=2000)
                step("오른쪽 상자 클릭", lambda: pg.click("#cmp-ov rect.cdet >> nth=0", timeout=3000), settle=500)
                step("나란히 끔", lambda: pg.click("#rev-switch button.side"), settle=800)
                step("이전 결과로", lambda: (pg.click("#rev-switch button.prev"), ready()), settle=2500)
                step("현재 결과로", lambda: pg.click("#rev-switch button.cur"), settle=2000)
            for pid in ["mult-panel", "sheet-panel", "review-codes", "legend-bar", "mode-bar", "notes-band"]:
                el = pg.query_selector(f"#{pid}")
                if el and el.is_visible():
                    vis = lambda: [b for b in pg.query_selector_all(f"#{pid} button, #{pid} summary") if b.is_visible()]
                    for k in range(min(4, len(vis()))):
                        cur = vis()
                        if k >= len(cur): break
                        txt = (cur[k].inner_text() or "")[:14]
                        if any(x in txt for x in ("지우", "되돌리", "다시 분석", "바꾸기")): continue
                        step(f"{pid} 버튼 '{txt}'", lambda k=k, vis=vis: vis()[k].click(timeout=1500), settle=500); close_overlays()
            step("리뷰 띠 버튼들", lambda: [b.click(timeout=1000) for b in pg.query_selector_all("#review-panel button")[:5] if b.is_visible()], settle=600)
        step("첫 화면으로", lambda: pg.click("#to-home"), settle=1500)
        step("첫 화면에서 다시 열기", lambda: (pg.click("a.revrow >> nth=0", timeout=5000), ready()), settle=2000)
        pg.screenshot(path=str(OUT / "B_end.png"))
        br.close()
    tb, s500 = server_errors(); note(f"B 끝 — 페이지/콘솔 오류 누적 {len(errs)} · 서버 Traceback {tb} · 500 {s500}")
    (OUT / "B_errors.txt").write_text("\n".join(errs), encoding="utf-8")

# ----------------------------------------------------------------------------- C. E2E
if E2E:
    note("## C. 합성 PDF 전 흐름")
    SYN = ROOT / "tests/data/synthetic"
    def wait_done(jid, limit=900):
        t0 = time.time()
        while time.time() - t0 < limit:
            st, j = req("GET", f"/jobs/{jid}")
            if j.get("status") in ("done", "failed", "cancelled"): return j
            time.sleep(5)
        return {"status": "timeout"}
    chk("C 프로젝트 생성", *req("POST", "/projects", form={"name": "QA-SYN"}))
    st, j = req("POST", "/jobs", form={"project": "QA-SYN"}, files={"pdf": ("08b_tagged_same_size.pdf", (SYN / "08b_tagged_same_size.pdf").read_bytes())})
    jA = (j.get("job_id") or j.get("id")) if isinstance(j, dict) else None; note(f"  Rev.A 업로드 → {st} {jA}")
    if not jA: defect(f"Rev.A 업로드 실패: {st} {str(j)[:200]}")
    t0 = time.time(); ja = wait_done(jA) if jA else {"status": "upload-failed"}; note(f"  Rev.A 분석 {ja.get('status')} · {round(time.time() - t0)}초 · 행 {ja.get('row_count')}")
    if ja.get("status") != "done": defect(f"Rev.A 분석 실패: {ja.get('message')}")
    else:
        st, rowsA = req("GET", f"/jobs/{jA}/rows?tab=ALL"); kA = rowsA[0]["key"]; pA = rowsA[0]["page_no"]
        chk("C PATCH qty", *req("PATCH", f"/jobs/{jA}/rows/{kA}", data={"field": "qty", "value": "5", "author": "QA"}))
        chk("C 마크업 추가", *req("POST", f"/jobs/{jA}/rows", data={"page_no": pA, "tab": "FIELD", "rect": [300, 300, 330, 320], "values": {"type": "TIT", "qty": 1}, "author": "QA", "reason_class": "MISSING"}))
        chk("C 최종 저장", *req("POST", f"/jobs/{jA}/save", data={"author": "QA"}))
        chk("C 변경 내역(비교 대상 없음 → 400)", *req("GET", f"/jobs/{jA}/revision/changes.xlsx", raw=True), ok=(400,))
        st, j = req("POST", "/jobs", form={"project": "QA-SYN", "compared_with": "Rev.A"}, files={"pdf": ("05_legend_last.pdf", (SYN / "05_legend_last.pdf").read_bytes())})
        jB = (j.get("job_id") or j.get("id")) if isinstance(j, dict) else None; note(f"  Rev.B 업로드 → {st} {jB}")
        t0 = time.time(); jb = wait_done(jB); note(f"  Rev.B 분석 {jb.get('status')} · {round(time.time() - t0)}초 · 행 {jb.get('row_count')}")
        if jb.get("status") != "done": defect(f"Rev.B 분석 실패: {jb.get('message')}")
        else:
            st, rv = chk("C GET revision", *req("GET", f"/jobs/{jB}/revision"))
            note(f"  대조: {rv.get('label')} · counts {rv.get('counts')} · matched_by {rv.get('matched_by')} · previous_job_id={rv.get('previous_job_id') == jA}")
            if rv.get("previous_job_id") != jA: defect("previous_job_id 가 Rev.A job 이 아니다")
            chk("C 변경 내역 Excel", *req("GET", f"/jobs/{jB}/revision/changes.xlsx", raw=True))
            st, rowsB = req("GET", f"/jobs/{jB}/rows?tab=ALL")
            carried = [r for r in rowsB if (r.get("user") or {}).get("qty") == 5]
            note(f"  Rev.A 편집 승계: qty=5 행 {len(carried)}")
            if UI:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as pw:
                    exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
                    br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
                    pg = br.new_page(viewport={"width": 1700, "height": 1000}); errs2 = []
                    pg.on("pageerror", lambda e: errs2.append(str(e)[:200])); pg.on("dialog", lambda d: d.accept("QA"))
                    pg.goto(f"{BASE}/#{jB}"); pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000); pg.wait_for_timeout(2500)
                    side = pg.evaluate("() => ({side: S.side, sw: !!document.querySelector('#rev-switch button.side'), label: document.querySelector('#rev-label').textContent})")
                    note(f"  C 화면: {side} · 오류 {len(errs2)}")
                    if errs2: defect("C 화면 오류: " + errs2[0])
                    pg.screenshot(path=str(OUT / "C_revB.png")); br.close()
            chk("C DELETE job Rev.B 확인없이", *req("DELETE", f"/jobs/{jB}", form={"author": "QA", "confirm": "x"}), ok=(400, 409, 422))
            chk("C DELETE job Rev.B", *req("DELETE", f"/jobs/{jB}", form={"author": "QA", "confirm": jB}))
            st, pj = req("GET", "/projects/QA-SYN")
            st, home = req("GET", "/home")
            qa = next((p for p in (home.get("projects") or []) if p.get("name") == "QA-SYN"), {})
            revB = next((r for r in (qa.get("revisions") or []) if r.get("revision") == "Rev.B"), {})
            note(f"  삭제 뒤 — 기본 비교 대상 {pj.get('default_compare')!r} · 선택지 {pj.get('compare_choices')} · 첫 화면 Rev.B missing={revB.get('missing')} deleted={bool(revB.get('deleted'))}")
            if pj.get("default_compare") == "Rev.B" or "Rev.B" in (pj.get("compare_choices") or []): defect("지워진 Rev.B 가 비교 대상으로 남아 있다")
            if not (revB.get("missing") or revB.get("deleted")): defect("지워진 Rev.B 가 첫 화면에 살아 있는 분석처럼 남아 있다")
            chk("C 지워진 리비전과 비교 요청 → 400", *req("POST", "/jobs", form={"project": "QA-SYN", "compared_with": "Rev.B"}, files={"pdf": ("x.pdf", b"%PDF-1.4 junk")}), ok=(400,))
    # 범례 없는 PDF — **프로젝트 안**에서는 저장된 범례 프로필로 완주해야 하고(15회차), **프로젝트 밖**에서는
    # 범례도 프로필도 없으므로 사유를 말하고 멈춰야 한다 (LegendUnavailable · 행 0 으로 조용히 성공하면 결함).
    st, j = req("POST", "/jobs", form={"project": "QA-SYN"}, files={"pdf": ("06_no_legend.pdf", (SYN / "06_no_legend.pdf").read_bytes())})
    jC = (j.get("job_id") or j.get("id")) if isinstance(j, dict) else None
    jc = wait_done(jC, 600); note(f"  범례 없는 PDF (프로젝트 안 · 프로필 재사용) → {jc.get('status')} · 행 {jc.get('rows')}")
    if jc.get("status") != "done": defect(f"프로젝트의 범례 프로필이 있는데 범례 없는 개정본이 완주하지 못했다: {jc.get('status')} {jc.get('message')}")
    st, j = req("POST", "/jobs", form={"project": ""}, files={"pdf": ("06_no_legend.pdf", (SYN / "06_no_legend.pdf").read_bytes())})
    jC = (j.get("job_id") or j.get("id")) if isinstance(j, dict) else None
    jc = wait_done(jC, 600); note(f"  범례 없는 PDF (프로젝트 밖) → {jc.get('status')} · 사유 {str(jc.get('message'))[:120]!r} · stopped_stage {jc.get('stopped_stage')!r}")
    if jc.get("status") != "failed": defect(f"범례도 프로필도 없는 PDF 가 실패로 멈추지 않았다: {jc.get('status')}")
    chk("C 실패한 분석 삭제", *req("DELETE", f"/jobs/{jC}", form={"author": "QA", "confirm": jC}))
    chk("C error_detail", *req("GET", f"/jobs/{jC}/error_detail"))
    # 분석 중 취소 — running 이 되면 cancel · cancelled 로 끝나야 하고 행 0 · 지울 수 있어야 한다
    st, j = req("POST", "/jobs", form={"project": ""}, files={"pdf": ("01_a0.pdf", (SYN / "01_a0.pdf").read_bytes())})
    jD = (j.get("job_id") or j.get("id")) if isinstance(j, dict) else None
    t0 = time.time(); st_now = ""
    while time.time() - t0 < 120:
        st, jj = req("GET", f"/jobs/{jD}"); st_now = jj.get("status")
        if st_now == "running" and (jj.get("progress") or 0) > 0.05: break
        time.sleep(2)
    chk("C 분석 중 취소", *req("POST", f"/jobs/{jD}/cancel"))
    jd = wait_done(jD, 180); note(f"  취소 뒤 상태 {jd.get('status')} · 행 {jd.get('rows')} · {round(time.time() - t0)}초")
    if jd.get("status") != "cancelled": defect(f"분석 중 취소가 cancelled 로 끝나지 않았다: {jd.get('status')}")
    chk("C 취소된 분석 삭제", *req("DELETE", f"/jobs/{jD}", form={"author": "QA", "confirm": jD}))
    st, prev = chk("C 프로젝트 삭제 미리보기", *req("GET", "/projects/QA-SYN/deletion_preview"))
    chk("C 프로젝트 삭제", *req("DELETE", "/projects/QA-SYN", form={"author": "QA", "confirm": "QA-SYN"}))
    st, home = req("GET", "/home"); note(f"  삭제 뒤 /home 에 QA-SYN 남음: {'QA-SYN' in json.dumps(home)}")
    if "QA-SYN" in json.dumps(home): defect("프로젝트 삭제 뒤 첫 화면에 남아 있다")
    tb, s500 = server_errors(); note(f"C 끝 — 서버 Traceback {tb} · 500 {s500}")

srv.terminate()
(OUT / "README.md").write_text("# QA 시뮬레이션\n\n" + "\n".join(f"- {x}" for x in FOUND) + f"\n\n## 결함 {len(DEFECTS)}\n" + "\n".join(f"- {x}" for x in DEFECTS) + "\n", encoding="utf-8")
print(f"\n결함 {len(DEFECTS)} · {OUT / 'README.md'}")
