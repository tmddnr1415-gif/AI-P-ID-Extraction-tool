"""hotfix71 — VOC 를 화면의 입구마다 실제로 눌러 남기고, 운영 폴더 함에 쌓이는지 · 반영 표시 뒤 다시 안 보이는지 확인.

    python3 spike/ui_audit_voc.py <data_dir 사본> <job> out/hotfix71/ui

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.  VOC 함도 그 밑(`voc/`)에 쌓인다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from urllib.parse import quote
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
INBOX = data / "voc" / "inbox"
LEDGER = OUT / "ledger.json"
if LEDGER.exists():
    LEDGER.unlink()
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND = []
def note(x): print(x, flush=True); FOUND.append(x)
def inbox():
    return sorted(p.name for p in INBOX.iterdir()) if INBOX.exists() else []
def rec(vid):
    return json.loads((INBOX / vid / "voc.json").read_text(encoding="utf-8"))
def newest(before):
    new = [v for v in inbox() if v not in before]
    return new[-1] if new else None
def cli(*args):
    return subprocess.run([sys.executable, str(ROOT / "spike" / "voc.py"), "--inbox", str(INBOX),
                           "--ledger", str(LEDGER), *args], capture_output=True, text=True,
                          encoding="utf-8", env=dict(os.environ, PYTHONUTF8="1")).stdout

try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        pg = br.new_page(viewport={"width": 1920, "height": 1080}); errs = []
        alerts = []
        pg.on("dialog", lambda d: (alerts.append(d.message), d.accept()))
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(base + "/?embed=1&mode=epc&user=" + quote("홍길동")); pg.wait_for_timeout(1500)

        # ① 첫 화면의 VOC — 분석 없이
        b0 = inbox()
        pg.click("#home-voc"); pg.wait_for_selector("#vc-note")
        pg.select_option("#vc-class", "FEATURE")
        pg.fill("#vc-note", "첫 화면에서 프로젝트를 이름으로 찾고 싶습니다")
        pg.screenshot(path=str(OUT / "1_첫화면_VOC.png"))
        pg.click("#vc-save"); pg.wait_for_timeout(1500)
        v1 = newest(b0)
        r1 = rec(v1) if v1 else {}
        rows_in_list = pg.eval_on_selector_all("#vc-list tr", "t => t.length")
        note(f"① 첫 화면 VOC → 함 {v1} · 분류 {r1.get('category')} · 작성자 {r1.get('author')} · 분석 {r1.get('context', {}).get('job_id')} · 목록 줄 {rows_in_list - 1}")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)

        # ② 결과 화면 머리줄의 VOC — 지금 장을 함께
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=180000)
        pg.wait_for_timeout(2500)
        pg.evaluate("() => { if (S.side) toggleSide(); }"); pg.wait_for_timeout(500)
        b0 = inbox()
        pg.click("#voc-btn"); pg.wait_for_selector("#vc-note")
        ctx_line = pg.inner_text(".voc-check") if pg.query_selector(".voc-check") else ""
        pg.select_option("#vc-class", "SLOW")
        pg.fill("#vc-note", "이 장에서 확대하면 버벅입니다")
        pg.click("#vc-save"); pg.wait_for_timeout(1500)
        v2 = newest(b0); r2 = rec(v2) if v2 else {}
        note(f"② 결과 화면 VOC → {v2} · '{ctx_line.strip()[:70]}' · 장 p{r2.get('context', {}).get('page_no')} {r2.get('context', {}).get('drawing_no')} · 프로젝트 {r2.get('context', {}).get('project')} {r2.get('context', {}).get('revision')}")
        pg.keyboard.press("Escape"); pg.wait_for_timeout(300)

        # ③ 마크업 — 누락 행 추가 (사유 비우면 막힘 → 적으면 VOC)
        row = pg.evaluate("() => { const r = S.rows.find(r => r.page_no === S.page.page_no && r.rect && !r.removed); return {key: r.key, rect: r.rect}; }")
        x0, y0, x1, y1 = row["rect"]
        rect = [x0 + 60, y0, x1 + 60, y1]
        b0 = inbox()
        pg.evaluate("r => { setMarkup(true); markupDialog(r); }", rect)
        pg.wait_for_selector("#mk-voc", timeout=60000); pg.wait_for_timeout(500)
        default_on = pg.is_checked("#mk-voc")
        pg.fill("#mk-type", "PIT")
        n_alert = len(alerts)
        pg.click("#mk-save"); pg.wait_for_timeout(800)
        blocked = len(alerts) > n_alert and not newest(b0)
        pg.fill("#mk-note", "버블이 파선이라 못 읽은 PIT")
        pg.screenshot(path=str(OUT / "3_마크업_VOC.png"))
        pg.click("#mk-save"); pg.wait_for_timeout(2500)
        v3 = newest(b0); r3 = rec(v3) if v3 else {}
        note(f"③ 마크업 추가 → 기본 켜짐 {default_on} · 사유 비우면 막힘 {blocked} · {v3} · 출처 {r3.get('source')} · 분류 {r3.get('category')}"
             f" · 행 {len(r3.get('rows') or [])} · 조각 {r3.get('has_crop')} · 편집 안내 '{(pg.inner_text('.edit-note') if pg.query_selector('.edit-note') else '')[-30:]}'")

        # ④ 마크업 — 기존 상자를 오검출로
        b0 = inbox()
        pg.evaluate("k => rejectDialog({key: k})", row["key"])
        pg.wait_for_selector("#rj-voc")
        pg.select_option("#rj-class", "FALSE_POSITIVE")
        pg.fill("#rj-note", "배관 주석의 PI 글자를 계기로 읽음")
        pg.uncheck("#rj-exclude")
        pg.click("#rj-save"); pg.wait_for_timeout(2500)
        v4 = newest(b0); r4 = rec(v4) if v4 else {}
        note(f"④ 오검출 표시 → {v4} · 출처 {r4.get('source')} · 분류 {r4.get('category')} · 행 {((r4.get('rows') or [{}])[0].get('identity') or {}).get('row_key') == row['key']}")
        pg.evaluate("() => setMarkup(false)")

        # ⑤ 오류 신고 — 신고 목록과 VOC 함 둘 다
        b0 = inbox()
        pg.evaluate("k => reportDialog({rowKey: k, pageNo: S.page.page_no})", row["key"])
        pg.wait_for_selector("#rep-detail")
        pg.fill("#rep-detail", "Q'ty 는 x2 여야 합니다")
        pg.click("#rep-save"); pg.wait_for_timeout(2000)
        v5 = newest(b0); r5 = rec(v5) if v5 else {}
        note(f"⑤ 오류 신고 → {v5} · 출처 {r5.get('source')} · 작성자 {r5.get('author')} · 신고 번호 {r5.get('report_id')}")

        # ⑥ 실패 화면 — VOC 로 신고 단추
        pg.evaluate(f"() => {{ document.querySelector('#main').classList.add('hidden'); document.querySelector('#progress').classList.remove('hidden'); showFailure('도면번호를 읽지 못했습니다', {{stopped_stage: 'titleblocks', pdf_name: 'x.pdf'}}, '{JOB}'); }}")
        pg.wait_for_timeout(800)
        vis = pg.is_visible("#prog-voc")
        b0 = inbox()
        pg.click("#prog-voc"); pg.wait_for_selector("#vc-note")
        cls = pg.eval_on_selector("#vc-class", "s => s.value")
        pg.fill("#vc-note", "새 양식 PDF 가 타이틀블록 단계에서 멈춥니다")
        pg.click("#vc-save"); pg.wait_for_timeout(1500)
        v6 = newest(b0); r6 = rec(v6) if v6 else {}
        note(f"⑥ 실패 화면 → 단추 보임 {vis} · 분류 기본 {cls} · {v6} · 출처 {r6.get('source')} · 분석 {r6.get('context', {}).get('job_id')}")
        pg.keyboard.press("Escape")

        # ⑦ 회사 Claude Code — 목록 · 반영 · 다시 안 보임
        lst = cli("list")
        n_open = lst.count("[미반영]")
        res = cli("resolve", v3, v4, "--by", "Claude Code (회사)", "--release", "hotfix72", "--note", "파선 버블 · 배관 주석 규칙")
        lst2 = cli("list")
        again = cli("resolve", v3, "--by", "다른 사람", "--release", "hotfix73")
        note(f"⑦ CLI list 미반영 {n_open} → resolve {res.strip().splitlines()} → list 미반영 {lst2.count('[미반영]')} · 그 둘 안 보임 {v3 not in lst2 and v4 not in lst2} · 다시 반영 '{again.strip()[:60]}'")
        (OUT / "cli_list_before.txt").write_text(lst, encoding="utf-8")
        (OUT / "cli_list_after.txt").write_text(lst2, encoding="utf-8")
        cli("brief", "--out", str(OUT / "voc_brief.md"))

        # ⑧ 화면이 '반영됨' 을 보인다
        pg.goto(base + "/?embed=1&user=" + quote("홍길동")); pg.wait_for_timeout(1500)
        pg.click("#home-voc"); pg.wait_for_selector("#vc-list"); pg.wait_for_timeout(500)
        states = pg.eval_on_selector_all("#vc-list .voc-state", "els => els.map(e => e.innerText.split('\\n')[0])")
        pg.screenshot(path=str(OUT / "8_목록_반영됨.png"))
        note(f"⑧ 화면 목록 상태 {states}")
        note(f"화면 오류 {len(errs)} {errs[:3]} · 경고창 {alerts}")
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "result.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
