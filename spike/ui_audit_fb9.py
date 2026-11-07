"""9차 피드백 화면 항목을 **실제로 눌러서** 확인한다 (54회차).

    python3 spike/ui_audit_fb9.py out/round54/TC2_final.json out/round54/ui

확인하는 것 — 코드가 도는 것과 화면이 그렇게 말하는 것은 다른 일이다:
    [B] Typical 표식(`D`·`D1`)이 **그려지는가** · 범례가 **자기 칸**으로 세는가
        · 33회차 등식(칸 합 = 상자 수)이 그대로인가 · 눌렀을 때 사유를 말하는가
    [A] `PCV`·`XV`·`TCV` 행이 **버블 자리**에 상자를 갖는가
    [C] p12 의 `PI` 넷이 VENDOR 색으로 그려지는가

★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/round54/TC2_final.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/round54/ui")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="fb9ui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "fb9audit0001"
pdf = ROOT / "data" / "TC2_260821.pdf"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "TC2")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(),
             result.get("fingerprint", ""), "TC2", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "TC2", "A", job_id=job, pdf_name=pdf.name,
                          compared_with="",
                          result={"counts": {}, "states": {}, "radii": {},
                                  "deleted_candidates": []})

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1700, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text)
              if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/")
        pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt')"
                    ".forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_첫화면_행없음.png"))
            note("★ 결과로 들어갈 행이 없다: " + pg.inner_text("#joblist")[:300])
            raise SystemExit(2)
        rr.click()
        pg.wait_for_timeout(9000)

        # ── [B] Typical 표식 ──────────────────────────────────────────────
        pg.select_option("#page-select", "11")
        pg.wait_for_timeout(2500)
        box = pg.evaluate("""() => {
            const items = overlayItems(S.page);
            const typ = items.filter(i => i.typical);
            const drawn = document.querySelectorAll('#ov rect.det.typical').length;
            const legend = [...document.querySelectorAll('.ovl-row')].map(
                r => r.innerText.replace(/\\s+/g, ' ').trim());
            const boxes = document.querySelectorAll('#ov rect.det').length;
            const nums = legend.map(t => Number((t.match(/(\\d+)\\s*$/) || [0, 0])[1]));
            return {typical: typ.length, drawn, legend, boxes,
                    sum: nums[0] + nums[1] + nums[2] + nums[3] + nums[4],
                    ids: typ.slice(0, 6).map(i => i.label)};
        }""")
        note(f"[B] p11 Typical 항목 {box['typical']} · 그려진 상자 {box['drawn']}"
             f" · 라벨 {box['ids']}")
        note(f"[B] 범례 = {box['legend']}")
        note(f"[B] 33회차 등식 — 색 칸 합 {box['sum']} ↔ 상자 수 {box['boxes']}"
             f" · {'같다' if box['sum'] == box['boxes'] else '★ 다르다'}")
        pg.screenshot(path=str(OUT / "b_typical_p11.png"))
        # 표식을 눌러 사유가 나오나
        pg.evaluate("() => { const r = document.querySelector('#ov rect.det.typical');"
                    " if (r) r.dispatchEvent(new MouseEvent('click', {bubbles: true})); }")
        pg.wait_for_timeout(900)
        why = pg.inner_text("#evidence")[:260].replace("\n", " ")
        note(f"[B] 표식을 누르면: {why}")
        # 칸을 끄면 상자가 사라지나
        pg.evaluate("""() => { const c = [...document.querySelectorAll('.ovl')]
            .find(x => x.value === 'TYPICAL'); c.checked = false;
            c.dispatchEvent(new Event('change')); }""")
        pg.wait_for_timeout(700)
        off = pg.eval_on_selector_all("#ov rect.det.typical", "n => n.length")
        note(f"[B] 칸을 끄면 그려진 표식 {off}")

        # ── [A] 태그 행이 버블 자리에 ─────────────────────────────────────
        pg.select_option("#page-select", "10")
        pg.wait_for_timeout(2500)
        a = pg.evaluate("""() => {
            const items = overlayItems(S.page);
            const want = ['PCV', 'XV', 'TCV'];
            const out = {};
            for (const t of want) {
                const rows = (S.rows || []).filter(r => r.page_no === 10 &&
                    ((r.evidence || {}).tag) === t);
                out[t] = {rows: rows.length,
                          boxes: rows.filter(r => items.some(i => i.key === r.key)).length,
                          noBody: rows.filter(r => !((r.evidence || {}).body)).length};
            }
            return out;
        }""")
        note(f"[A] p10 — {json.dumps(a, ensure_ascii=False)}")
        pg.screenshot(path=str(OUT / "a_p10.png"))

        # ── [C] p12 VENDOR 색 ─────────────────────────────────────────────
        pg.select_option("#page-select", "12")
        pg.wait_for_timeout(2500)
        c = pg.evaluate("""() => {
            const items = overlayItems(S.page);
            const cnt = {};
            for (const i of items) { const k = itemScope(i); cnt[k] = (cnt[k]||0)+1; }
            const orange = [...document.querySelectorAll('#ov rect.det')]
                .filter(r => r.getAttribute('stroke') === '#ff9f0a').length;
            return {scope: cnt, orange};
        }""")
        note(f"[C] p12 — 층 갈래 {json.dumps(c['scope'], ensure_ascii=False)}"
             f" · 주황(VENDOR) 상자 {c['orange']}")
        pg.screenshot(path=str(OUT / "c_p12.png"))

        note("페이지 오류: " + (errs[0] if errs else "없음"))
        br.close()
finally:
    srv.terminate()
(OUT / "감사결과.txt").write_text("\n".join(FOUND) + "\n", encoding="utf8")
print("\n".join(FOUND))
