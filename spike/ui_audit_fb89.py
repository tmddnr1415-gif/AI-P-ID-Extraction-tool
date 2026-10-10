"""8·9차 피드백을 **화면에서 눌러** 확인하고 그림으로 남긴다 (54회차 뒤 확인).

    python3 spike/ui_audit_fb89.py out/round54/ui89

세 가지를 찍는다 — 코드가 도는 것과 화면이 그렇게 말하는 것은 다른 일이다:
    ① 식별 결과   8차(AL NOUF1 p8·p12·p21 태그 밸브) · 9차(TC2 p10·p11·p12)
    ② 마크업       사각형을 실제로 끌어 그리고 제안·저장·녹색 표기
    ③ 사용자 수정값  작성자 확인 줄 · ✎ 표식 · 근거 패널 · SCOPE 색 따라가기

★ 실 DB 를 열지 않는다 (17회차 격리 — `PID_DATA_DIR` 을 임시 폴더로 돌린다).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/round54/ui89")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []

DOCS = [
    ("TC2", "out/regression_3p/TC2.json", "data/TC2_260821.pdf"),
    ("AL NOUF1", "out/regression_3p/AL_NOUF1.json", "data/pid_total.pdf"),
]


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="fb89ui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

con = db.connect(data / "app.db")
jobs = {}
for i, (name, res_p, pdf_p) in enumerate(DOCS):
    src = ROOT / res_p
    pdf = ROOT / pdf_p
    if not src.exists() or not pdf.exists():
        note(f"⚠ {name}: 자료 없음 — 건너뛴다 ({res_p} / {pdf_p})")
        continue
    result = json.loads(src.read_text())
    result = result.get("result", result)
    job = f"fb89audit{i:04d}"
    jobs[name] = job
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    revisions.create_project(data, name)
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
                " progress, message, fingerprint, project, revision)"
                " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
                (job, pdf.name, sha, str(pdf.resolve()), time.time() + i,
                 result.get("fingerprint", ""), name, "A"))
    con.commit(); db.store_result(con, job, result); con.commit()
    revisions.record_revision(data, name, "A", job_id=job, pdf_name=pdf.name,
                              compared_with="",
                              result={"counts": {}, "states": {}, "radii": {},
                                      "deleted_candidates": []})
con.close()
if not jobs:
    raise SystemExit("자료가 하나도 없다")

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                        "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def open_job(pg, job):
    """첫 화면에서 그 분석의 행을 눌러 결과로 들어간다 (20회차 [12] — a.revrow 뿐)."""
    pg.goto(f"http://127.0.0.1:{port}/")
    pg.wait_for_timeout(2200)
    pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
    pg.wait_for_timeout(400)
    rr = pg.query_selector(f"a.revrow[href*='{job}']") or pg.query_selector("a.revrow")
    if rr is None:
        return False
    rr.click()
    pg.wait_for_timeout(9000)
    return True


def goto_page(pg, n):
    pg.select_option("#page-select", str(n))
    pg.wait_for_timeout(2600)


def tag_facts(pg, page_no):
    return pg.evaluate("""(pno) => {
        const items = overlayItems(S.page);
        const rows = (S.rows || []).filter(r => r.page_no === pno);
        const byTag = {};
        for (const r of rows) {
            const t = (r.evidence || {}).tag;
            if (typeof t !== 'string' || !t) continue;
            byTag[t] = byTag[t] || {rows: 0, boxes: 0, noBody: 0};
            byTag[t].rows++;
            if (items.some(i => i.key === r.key)) byTag[t].boxes++;
            if (!(r.evidence || {}).body) byTag[t].noBody++;
        }
        const legend = [...document.querySelectorAll('.ovl-row')]
            .map(r => r.innerText.replace(/\\s+/g, ' ').trim());
        return {rows: rows.length, byTag, legend,
                boxes: document.querySelectorAll('#ov rect.det').length};
    }""", page_no)


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
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)

        # ══ ① 식별 결과 — 9차 (TC2) ═════════════════════════════════════
        if "TC2" in jobs:
            assert open_job(pg, jobs["TC2"]), "TC2 결과 행 없음"
            for n, why in ((10, "9차 [A] XV·PCV·TCV"), (11, "9차 [B] Typical"),
                           (12, "9차 [C] 별표 VENDOR")):
                goto_page(pg, n)
                f = tag_facts(pg, n)
                note(f"① TC2 p{n} ({why}) — 행 {f['rows']} · 태그별 "
                     f"{json.dumps(f['byTag'], ensure_ascii=False)}")
                note(f"   범례 {f['legend']}")
                pg.screenshot(path=str(OUT / f"1_식별_TC2_p{n}.png"))
            # 9차 [B] 등식과 표식 사유
            goto_page(pg, 11)
            eq = pg.evaluate("""() => {
                // 33회차 등식은 **색 칸**만 센다 — "(그중)" 줄(검토·오검출)은
                // 그 칸들 안의 몫이라 더하면 두 번 세는 것이다.
                const legend = [...document.querySelectorAll('.ovl-row')]
                    .filter(r => !/\\(그중\\)/.test(r.innerText))
                    .map(r => Number((r.innerText.match(/(\\d+)\\s*$/) || [0,0])[1]));
                return {sum: legend.reduce((a,b)=>a+b,0),
                        boxes: document.querySelectorAll('#ov rect.det').length,
                        typical: document.querySelectorAll('#ov rect.det.typical').length};
            }""")
            note(f"① TC2 p11 33회차 등식 — 칸 합 {eq['sum']} ↔ 상자 {eq['boxes']}"
                 f" · {'같다' if eq['sum'] == eq['boxes'] else '★ 다르다'}"
                 f" · Typical 표식 {eq['typical']}")

        # ══ ② 마크업 · ③ 사용자 수정값 (TC2 p12 에서) ═══════════════════
        if "TC2" in jobs:
            goto_page(pg, 12)
            pg.click("#markup-toggle")
            pg.wait_for_timeout(7000)          # 그 장을 미리 읽는다 (예열)
            note("② 마크업 켬 — " + pg.inner_text("#markup-note")[:120].replace("\n", " "))
            # 별표가 있는 자리에 사각형을 **실제로 끌어** 그린다
            box = pg.evaluate("""() => {
                const img = document.querySelector('#sheet');
                const b = img.getBoundingClientRect();
                return {left: b.left, top: b.top, w: b.width, h: b.height,
                        pw: S.page.width, ph: S.page.height};
            }""")
            # 시트 좌표 → 화면 좌표 (sheetPoint 의 역)
            def scr(x, y):
                return (box["left"] + x / box["pw"] * box["w"],
                        box["top"] + y / box["ph"] * box["h"])
            x0, y0 = scr(300.0, 470.0)
            x1, y1 = scr(370.0, 525.0)
            pg.mouse.move(x0, y0); pg.mouse.down()
            pg.mouse.move((x0 + x1) / 2, (y0 + y1) / 2, steps=6)
            pg.mouse.move(x1, y1, steps=6); pg.mouse.up()
            pg.wait_for_timeout(3000)
            dlg = pg.query_selector(".modal") or pg.query_selector("#modal")
            note("② 마크업 대화상자: " + (pg.inner_text("#modal")[:400].replace("\n", " · ")
                                          if dlg else "★ 안 열렸다"))
            pg.screenshot(path=str(OUT / "2_마크업_대화상자.png"))
            if dlg:
                pg.fill("#mk-type", "PIT")
                pg.fill("#mk-author", "감사")
                pg.fill("#mk-note", "화면 확인용")
                before = pg.evaluate("() => (S.rows || []).length")
                pg.click("#mk-save")
                pg.wait_for_timeout(3500)
                after = pg.evaluate("""() => {
                    const added = (S.rows || []).filter(r => r.added);
                    const items = overlayItems(S.page);
                    return {rows: (S.rows||[]).length, added: added.length,
                        manualBoxes: document.querySelectorAll('#ov rect.det.manual').length,
                        greenRows: document.querySelectorAll('tr.added, tr.manual').length,
                        note: (document.querySelector('.edit-note')||{}).textContent || "",
                        legend: [...document.querySelectorAll('.ovl-row')]
                            .map(r => r.innerText.replace(/\\s+/g,' ').trim())};
                }""")
                note(f"② 저장 뒤 — 행 {before} → {after['rows']} · 추가 표시 {after['added']}"
                     f" · 녹색 상자 {after['manualBoxes']} · 녹색 행 {after['greenRows']}")
                note(f"   안내 {after['note'][:160]}")
                note(f"   범례 {after['legend']}")
                pg.screenshot(path=str(OUT / "3_마크업_추가행.png"))
            pg.click("#markup-toggle")         # 마크업 끄기
            pg.wait_for_timeout(800)

            # ── ③ 사용자 수정값 ─────────────────────────────────────────
            # SCOPE 가 SCT 인 행 하나를 골라 VENDOR 로 고친다 (8차 s7 — 색이 따라가나)
            picked = pg.evaluate("""() => {
                const r = (S.rows || []).find(x => x.page_no === 12 &&
                    (x.values||{}).scope === 'SCT' && !x.added);
                if (!r) return null;
                select(r.key, true);
                return {key: r.key, type: (r.values||{}).type, qty: (r.values||{}).qty};
            }""")
            note(f"③ 고칠 행: {json.dumps(picked, ensure_ascii=False)}")
            pg.wait_for_timeout(1200)
            # 그 행의 SCOPE 칸을 눌러 값을 바꾼다
            # 합성 blur 를 쓰지 않는다 — `td.focus()` 뒤에 확인 줄이 초점을
            # 가져가면서 **진짜 blur 가 한 번 더** 나 두 번 저장된다.
            # 사람이 하듯 칸을 눌러 고치고 밖을 누른다.
            cell = pg.query_selector(f'#body tr[data-key="{picked["key"]}"] td.col-scope')
            cell.click()
            pg.wait_for_timeout(300)
            pg.keyboard.press("Control+A")
            pg.keyboard.type("VENDOR")
            pg.click("#filter")                      # 칸 밖을 누른다 → blur 한 번
            pg.wait_for_timeout(1800)
            bars = pg.eval_on_selector_all(".author-bar", "n => n.length")
            note(f"③ 확인 줄 개수 {bars} · {'하나다' if bars == 1 else '★ 겹쳐 쌓였다'}")
            bar = pg.query_selector(".author-bar")
            note("③ 작성자 확인 줄: " + (pg.inner_text(".author-bar")[:200].replace("\n", " ")
                                          if bar else "★ 안 떴다"))
            pg.screenshot(path=str(OUT / "4_수정_작성자확인.png"))
            if bar:
                pg.query_selector(".author-bar input").fill("감사")
                pg.query_selector(".author-bar .ok").click()
                pg.wait_for_timeout(3000)
                after = pg.evaluate("""(key) => {
                    const tr = [...document.querySelectorAll('#body tr')]
                        .find(t => t.dataset.key === key);
                    const td = tr && tr.querySelector('td.col-scope');
                    const row = S.rowByKey[key] || {};
                    const items = overlayItems(S.page);
                    const it = items.find(i => i.key === key);
                    return {cell: td && td.textContent.trim(),
                            edited: td && td.classList.contains('edited'),
                            user: row.user || null,
                            colour: it ? itemScope(it) : null,
                            note: (document.querySelector('.edit-note')||{}).textContent || "",
                            evidence: (document.querySelector('#evidence')||{}).innerText
                                        .replace(/\\s+/g,' ').slice(0, 400)};
                }""", picked["key"])
                note(f"③ 고친 뒤 — 칸 {after['cell']!r} · edited 표식 {after['edited']}"
                     f" · user {json.dumps(after['user'], ensure_ascii=False)}"
                     f" · 오버레이 갈래 {after['colour']}")
                note(f"   안내 {after['note'][:200]}")
                note(f"   근거 패널 {after['evidence'][:300]}")
                pg.screenshot(path=str(OUT / "5_수정_반영.png"))

        # ══ ① 식별 결과 — 8차 (AL NOUF1) ═══════════════════════════════
        if "AL NOUF1" in jobs:
            assert open_job(pg, jobs["AL NOUF1"]), "AL NOUF1 결과 행 없음"
            for n, why in ((8, "8차 s4 MOV"), (12, "8차 s5 PCV"),
                           (21, "8차 s6 XV·PCV·FCV")):
                goto_page(pg, n)
                f = tag_facts(pg, n)
                note(f"① AL NOUF1 p{n} ({why}) — 행 {f['rows']} · 태그별 "
                     f"{json.dumps(f['byTag'], ensure_ascii=False)}")
                pg.screenshot(path=str(OUT / f"6_식별_NOUF1_p{n}.png"))

        note("페이지 오류: " + (errs[0] if errs else "없음"))
        br.close()
finally:
    srv.terminate()
(OUT / "감사결과.txt").write_text("\n".join(FOUND) + "\n", encoding="utf8")
print("\n=== 정리 ===")
print("\n".join(FOUND))
