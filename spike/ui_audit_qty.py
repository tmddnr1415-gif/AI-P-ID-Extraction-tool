"""hotfix32 — 식별 표기 옆의 수량 x N 과 도면 위 수량 편집을 **실제로 눌러서** 확인한다.

    python3 spike/ui_audit_fb8.py out/regression_3p/AL_NOUF1.json out/hotfix32/ui

확인하는 것 넷 — 코드가 도는 것과 화면이 그렇게 말하는 것은 다른 일이다:
    s1  분석/프로젝트를 지우면 **고르는 상자**에서도 사라지는가
    s3  그 장 NOTES 에서 읽은 **식별 값과 해석**이 보이는가
    s7  SCOPE 를 바꾸면 **색이 따라가는가** · VENDOR 이름을 고를 수 있는가
    s8  마크업 제안·행추가가 **얼마나 걸리는가** · 녹색 선/음영 · 추가 행으로 이동

★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix32/ui")
OUT.mkdir(parents=True, exist_ok=True)
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/AL_NOUF1.json")
FOUND: list[str] = []


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="qtyui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "qtyaudit0001"
pdf = ROOT / "data" / "pid_total.pdf"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "AL NOUF1")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(),
             result.get("fingerprint", ""), "AL NOUF1", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
# ★ 31회차 [9] 와 같은 픽스처 결함을 피한다 — `GET /home` 은 `job.project` 열이
# 아니라 **프로젝트 장부**를 읽는다.  열만 채우면 "묶이지 않은 분석" 으로 뜨고
# `a.revrow` 가 없어 결과 화면에 못 들어간다.
revisions.record_revision(data, "AL NOUF1", "A", job_id=job,
                          pdf_name=pdf.name, compared_with="",
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

        # 결과 화면으로 — `a.revrow` 하나뿐이다 (20회차 [12]).
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_첫화면_행없음.png"))
            note("★ 결과로 들어갈 행이 없다: " + pg.inner_text("#joblist")[:300])
            raise SystemExit(2)
        rr.click()
        pg.wait_for_timeout(8000)
        pg.select_option("#page-select", "6")
        pg.wait_for_timeout(2500)

        # ── ① 라벨이 있는가 · 수가 맞는가 ───────────────────────────────
        n_tags = pg.evaluate("() => document.querySelectorAll('g.qtytag').length")
        n_rows = pg.evaluate("() => overlayItems(S.page).filter(it => qtyTagRow(it)).length")
        n_det = pg.evaluate("() => document.querySelectorAll('rect.det:not(.excluded):not(.seal):not(.typical)').length")
        labels = pg.evaluate("() => [...document.querySelectorAll('g.qtytag text')].map(t => t.textContent)")
        from collections import Counter
        note(f"① p6 수량 라벨 {n_tags}개 = 행인 상자 {n_rows}개 (행 상자 {n_det}) · 라벨 분포 {dict(Counter(labels))}")
        leg = pg.query_selector("#ovl-items")
        if leg:
            leg.screenshot(path=str(OUT / "1_범례.png"))
            note("① 범례: " + repr(leg.inner_text()[:260]))
        pg.screenshot(path=str(OUT / "1_p6_라벨.png"))

        # ── ② 라벨을 눌러 고친다 ───────────────────────────────────────
        key = pg.evaluate("""() => {
            const it = overlayItems(S.page).find(it => qtyTagRow(it) && S.rowByKey[it.key].tab === 'FIELD');
            return it ? it.key : null; }""")
        if not key:
            note("② ★ 고칠 행이 없다"); raise SystemExit(3)
        q0 = pg.evaluate(f"() => cellValue(S.rowByKey[{json.dumps(key)}], 'qty')")
        pg.evaluate(f"() => select({json.dumps(key)}, false)")
        pg.wait_for_timeout(600)
        g = pg.query_selector(f'g.qtytag[data-key="{key}"]')
        box = g.bounding_box()
        # 라벨이 화면 밖이면 그리로 스크롤
        pg.evaluate(f"""() => {{ const g = document.querySelector('g.qtytag[data-key={json.dumps(key)}]');
            g.scrollIntoView({{block: 'center', inline: 'center'}}); }}""")
        pg.wait_for_timeout(300)
        g = pg.query_selector(f'g.qtytag[data-key="{key}"]')
        g.click()
        pg.wait_for_timeout(400)
        inp = pg.query_selector("input.qtyedit")
        if not inp:
            note("② ★ 라벨을 눌렀는데 입력 상자가 안 뜬다"); raise SystemExit(4)
        pg.screenshot(path=str(OUT / "2_입력상자.png"))
        new_q = str(int(q0 or 0) + 3)
        inp.fill(new_q)
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(500)
        ab = pg.query_selector(".author-bar")
        if not ab:
            note("② ★ 작성자 확인 줄이 안 뜬다"); raise SystemExit(5)
        ab.screenshot(path=str(OUT / "2_작성자.png"))
        ab.query_selector("input").fill("감사")
        ab.query_selector("button.ok").click()
        pg.wait_for_timeout(1500)

        # ── ③ 세 곳이 같은 값을 말하는가 — 도면 라벨 · 목록 칸 · 근거 패널 · 서버 ──
        lab = pg.evaluate(f"() => document.querySelector('g.qtytag[data-key={json.dumps(key)}] text').textContent")
        cls = pg.evaluate(f"() => document.querySelector('g.qtytag[data-key={json.dumps(key)}]').getAttribute('class')")
        cell = pg.evaluate(f"""() => {{ const td = document.querySelector('#body tr[data-key={json.dumps(key)}] td[data-col=qty]');
            return td ? [td.textContent, td.className] : null; }}""")
        ev = pg.inner_text("#evidence")
        srv_user = pg.evaluate(f"""async () => {{ const r = await fetch('/jobs/' + S.job.id + '/rows'); const j = await r.json();
            const row = (j.rows || j).find(x => x.key === {json.dumps(key)}); return row ? [row.user, row.values.qty] : null; }}""")
        note(f"② 행 {key}: Q'ty {q0} → {new_q}")
        note(f"③ 도면 라벨 {lab!r} (class {cls}) · 목록 칸 {cell} · 서버 user/values {srv_user}")
        note(f"③ 근거 패널에 '사람이 고침' 이 있나: {'사람이 고침' in ev} · 줄: "
             + repr([l for l in ev.splitlines() if '수량' in l][:3]))
        pg.screenshot(path=str(OUT / "3_고친뒤.png"))
        td = pg.query_selector(f'#body tr[data-key="{key}"] td[data-col=qty]')
        if td:
            pg.evaluate(f"""() => document.querySelector('#body tr[data-key={json.dumps(key)}]').scrollIntoView({{block:'center'}})""")
            pg.wait_for_timeout(300)
            pg.query_selector(f'#body tr[data-key="{key}"]').screenshot(path=str(OUT / "3_목록행.png"))

        # ── ③-b 확대해서 라벨이 읽히는지 (상자 둘레 크롭) ──
        for _ in range(4):
            pg.click("#zoom-in") if pg.query_selector("#zoom-in") else pg.evaluate("() => zoomBy(1.3)")
            pg.wait_for_timeout(250)
        pg.evaluate(f"""() => document.querySelector('g.qtytag[data-key={json.dumps(key)}]')
            .scrollIntoView({{block: 'center', inline: 'center'}})""")
        pg.wait_for_timeout(600)
        bb = pg.query_selector(f'g.qtytag[data-key="{key}"]').bounding_box()
        if bb:
            clip = {"x": max(0, bb["x"] - 220), "y": max(0, bb["y"] - 120), "width": 440, "height": 240}
            pg.screenshot(path=str(OUT / "3_확대_라벨.png"), clip=clip)
            note(f"③-b 확대 크롭 저장 (라벨 {bb['width']:.0f}x{bb['height']:.0f}px)")
        # ── ④ Excel — 이 환경에는 발주처 양식(data/*.xlsx)이 없어 못 잰다 ──
        # 고친 값이 Excel 에 나가는 길은 hotfix24 가 이미 둔 것(최종 저장 → 스냅샷 →
        # `/revisions/{id}/excel`)이고 이 편집은 그 길의 **같은 `user` 칸**에 적힌다.
        n_tpl = len(list((ROOT / "data").glob("*.xlsx")))
        note(f"④ Excel: 발주처 양식 {n_tpl}개 — " + ("못 잼 (양식 없음 · hotfix24 의 길 그대로)" if not n_tpl else "양식 있음"))
        if errs:
            note("★ 화면 오류: " + " | ".join(errs[:5]))
        else:
            note("화면 오류 없음")
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=10)

(OUT / "README.md").write_text(
    "# hotfix32 화면 자기검증 — 식별 표기 옆 수량 x N · 도면 위 편집\n\n"
    + "\n".join("- " + x for x in FOUND) + "\n", encoding="utf-8")
print("\n=> " + str(OUT / "README.md"))
