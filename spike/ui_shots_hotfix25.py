"""hotfix25 — 전후 스크린샷.  같은 화면 셋을 **커밋된 화면 파일(전)** 과 **지금 파일(후)** 로 찍는다.

    python3 spike/ui_shots_hotfix25.py RESULT.json PDF OUTDIR

  ① Diaphragm Seal 이 있는 PI 행을 고른 도면 (AL NOUF1 p18)
  ② 같은 행의 근거 패널 + 오버레이 범례
  ③ From/To 마크업을 그은 뒤의 도면 (AL NOUF1 p6 PIT)

"전" 은 `git show HEAD:<파일>` 로 화면 파일 셋(app.js · styles.css · index.html)을 잠시 되돌려 찍고
곧바로 되돌린다 — 되돌리기는 `finally` 에서 한다.  ★ 실 DB 는 열지 않는다 (17회차) — sha256 대조.
"""
from __future__ import annotations
import hashlib, json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
STATIC = ["app/static/app.js", "app/static/styles.css", "app/static/index.html"]
FROM_BOX = [90, 535, 200, 565]            # AL NOUF1 p6 `FROM HRSG#12`
TO_BOX = [450, 690, 560, 720]             # AL NOUF1 p6 `TO HRSG#12 BD TANK`
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


blob = json.loads(src.read_text()); result = blob.get("result", blob)
rows = result["rows"]
seal_row = next(r for r in rows if r["page_no"] == 18 and r["type"] == "PI"
                and (r.get("evidence") or {}).get("diaphragm_seal"))
ft_row = next(r for r in rows if r["page_no"] == 6 and r["type"] == "PIT")
note(f"씰 행 {seal_row['key']} p18 PI · From/To 행 {ft_row['key']} p6 PIT")


def make_data():
    from app import db, revisions
    data = Path(tempfile.mkdtemp(prefix="shots25-"))
    os.environ["PID_DATA_DIR"] = str(data)
    con = db.connect(data / "app.db")
    job = "shots2500001"
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    revisions.create_project(data, "AUDIT")
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
                " progress, message, fingerprint, project, revision, input_kind)"
                " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,'PDF')",
                (job, pdf.name, sha, str(pdf.resolve()), time.time(),
                 result.get("fingerprint", ""), "AUDIT", "A"))
    con.commit(); db.store_result(con, job, result); con.commit(); con.close()
    revisions.record_revision(data, "AUDIT", "A", job_id=job, pdf_name=pdf.name, compared_with="",
                              result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})
    return data


def shoot(tag: str, data: Path):
    port = free_port()
    env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                            "--port", str(port)], cwd=str(ROOT), env=env,
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
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.query_selector("a.revrow").click(); pg.wait_for_timeout(8000)

            def pick(key, zoom_box):
                pg.evaluate(f"() => select('{key}', true)"); pg.wait_for_timeout(2500)
                # 절대 좌표로 놓는다 — `select` 의 부드러운 스크롤이 아직 도는 중이면 delta 는 밀린다
                pg.evaluate("""(b) => { const st = document.querySelector('#stage'); const img = document.querySelector('#sheet');
                    const sx = img.offsetLeft + (b[0]+b[2])/2 / S.page.width * img.clientWidth;
                    const sy = img.offsetTop + (b[1]+b[3])/2 / S.page.height * img.clientHeight;
                    st.scrollTo({left: sx - st.clientWidth/2, top: sy - st.clientHeight/2, behavior: 'instant'}); }""", zoom_box)
                pg.wait_for_timeout(800)

            def stage_clip():
                b = pg.evaluate("() => { const r = document.querySelector('#left').getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; }")
                return {"x": b[0], "y": b[1], "width": b[2], "height": b[3]}

            # ① · ② 씰 행 — 씰 자리를 가운데 두고 두 단계 확대
            pick(seal_row["key"], seal_row["rect"])
            pg.evaluate("() => fit()"); pg.wait_for_timeout(300)
            for _ in range(2):
                pg.evaluate("() => zoomBy(1.3)"); pg.wait_for_timeout(200)
            srect = (seal_row["evidence"]["diaphragm_seal"]["rects"] or [seal_row["rect"]])[0]
            centre = [(srect[0] + seal_row["rect"][0]) / 2, (srect[1] + seal_row["rect"][1]) / 2] * 2
            pick(seal_row["key"], centre)
            pg.screenshot(path=str(OUT / f"{tag}_1_seal_sheet.png"), clip=stage_clip())
            legend = pg.evaluate("() => [...document.querySelectorAll('#ovl-items .ovl-row')].map(r => r.textContent.replace(/\\s+/g,' ').trim())")
            ev = pg.evaluate("() => [...document.querySelectorAll('#evidence dt')].map(d => d.textContent + ': ' + d.nextElementSibling.textContent)")
            note(f"[{tag}] 범례: {legend}")
            note(f"[{tag}] 근거 패널 Diaphragm 줄: {[e for e in ev if 'Diaphragm' in e]}")
            seal_boxes = pg.evaluate("() => document.querySelectorAll('rect.det.seal').length")
            note(f"[{tag}] 도면의 씰 상자: {seal_boxes}")
            pg.evaluate("() => { const e = document.querySelector('#evidence'); e.style.maxHeight = 'none'; e.style.overflow = 'visible'; }")
            pg.wait_for_timeout(300)
            pg.locator("#evidence dl").first.screenshot(path=str(OUT / f"{tag}_2_seal_evidence.png"))
            # ③ From/To — 맞춤에서 한 단계 확대, 두 범위의 가운데를 보이게
            pick(ft_row["key"], ft_row["rect"])
            pg.evaluate("() => fit()"); pg.wait_for_timeout(300)
            pg.evaluate("() => zoomBy(1.3)"); pg.wait_for_timeout(200)
            if pg.query_selector("#dm-from"):
                def drag(box):
                    pt = pg.evaluate("""(b) => { const img = document.querySelector('#sheet'); const r = img.getBoundingClientRect();
                        const fx = x => r.left + x / S.page.width * r.width, fy = y => r.top + y / S.page.height * r.height;
                        return [fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])]; }""", box)
                    pg.evaluate("""(b) => { const st = document.querySelector('#stage'); const sr = st.getBoundingClientRect();
                        st.scrollLeft += ((b[0]+b[2])/2 - (sr.left + sr.width/2)); st.scrollTop += ((b[1]+b[3])/2 - (sr.top + sr.height/2)); }""", pt)
                    pg.wait_for_timeout(400)
                    pt = pg.evaluate("""(b) => { const img = document.querySelector('#sheet'); const r = img.getBoundingClientRect();
                        const fx = x => r.left + x / S.page.width * r.width, fy = y => r.top + y / S.page.height * r.height;
                        return [fx(b[0]), fy(b[1]), fx(b[2]), fy(b[3])]; }""", box)
                    pg.mouse.move(pt[0], pt[1]); pg.mouse.down()
                    pg.mouse.move((pt[0] + pt[2]) / 2, (pt[1] + pt[3]) / 2, steps=5)
                    pg.mouse.move(pt[2], pt[3], steps=5); pg.mouse.up(); pg.wait_for_timeout(2500)
                    pg.wait_for_selector(".author-bar input", timeout=8000)
                    pg.fill(".author-bar input", "감사자"); pg.click(".author-bar .ok"); pg.wait_for_timeout(2500)
                pg.click("#dm-from"); pg.wait_for_timeout(400); drag(FROM_BOX)
                pg.click("#dm-to"); pg.wait_for_timeout(400); drag(TO_BOX)
                d = pg.evaluate(f"() => S.rows.find(x => x.key === '{ft_row['key']}').values.description")
                note(f"[{tag}] From/To 뒤 Description: {d}")
                ftb = pg.evaluate("() => [...document.querySelectorAll('rect.ftbox')].map(b => b.getAttribute('class'))")
                note(f"[{tag}] 도면의 From/To 범위 상자: {ftb}")
                pick(ft_row["key"], [80, 520, 570, 730])
                pg.screenshot(path=str(OUT / f"{tag}_3_fromto_sheet.png"), clip=stage_clip())
                # 다시 열어도 남는가
                pg.reload(); pg.wait_for_timeout(2500)
                if not pg.is_visible("#stage"):
                    pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
                    pg.query_selector("a.revrow").click()
                pg.wait_for_timeout(7000)
                pick(ft_row["key"], [80, 520, 570, 730])
                ftb2 = pg.evaluate("() => [...document.querySelectorAll('rect.ftbox')].map(b => b.getAttribute('class'))")
                note(f"[{tag}] 새로 연 뒤 From/To 범위 상자: {ftb2}")
                # 대기 중에 장을 옮기면 취소되는가
                pg.click("#dm-from"); pg.wait_for_timeout(300)
                pg.select_option("#page-select", index=8); pg.wait_for_timeout(2500)
                pno = pg.evaluate("() => S.page && S.page.page_no")
                armed = pg.evaluate("() => S.ftMark")
                notes = pg.evaluate("() => [...document.querySelectorAll('.edit-note')].map(e => e.textContent)")
                note(f"[{tag}] 다른 장(p{pno})으로 옮긴 뒤 From 대기: {armed} · 안내 {notes}")
            else:
                note(f"[{tag}] From/To 마크업 없음 (옛 화면)")
                pick(ft_row["key"], [80, 520, 570, 730])
                pg.screenshot(path=str(OUT / f"{tag}_3_fromto_sheet.png"), clip=stage_clip())
            note(f"[{tag}] 페이지 오류: " + (" | ".join(errs) if errs else "없음"))
            br.close()
    finally:
        srv.terminate()


keep = {f: (ROOT / f).read_bytes() for f in STATIC}
try:
    for f in STATIC:
        (ROOT / f).write_bytes(subprocess.check_output(["git", "show", f"HEAD:{f}"], cwd=str(ROOT)))
    shoot("before", make_data())
finally:
    for f, b in keep.items():
        (ROOT / f).write_bytes(b)
shoot("after", make_data())

# 나란히
try:
    from PIL import Image
    for n in ("1_seal_sheet", "2_seal_evidence", "3_fromto_sheet"):
        a, b = Image.open(OUT / f"before_{n}.png"), Image.open(OUT / f"after_{n}.png")
        w = a.width + b.width + 20; h = max(a.height, b.height) + 30
        c = Image.new("RGB", (w, h), "white")
        from PIL import ImageDraw
        d = ImageDraw.Draw(c); d.text((10, 8), "BEFORE", fill="black"); d.text((a.width + 30, 8), "AFTER", fill="black")
        c.paste(a, (0, 30)); c.paste(b, (a.width + 20, 30)); c.save(OUT / f"pair_{n}.png")
except Exception as exc:                                  # noqa: BLE001
    note(f"나란히 붙이기 실패: {exc}")
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
