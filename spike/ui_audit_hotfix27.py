"""hotfix27 — 띄워서 눌러 본다.  전(커밋된 화면 파일) · 후(지금 파일) 둘 다.

    python3 spike/ui_audit_hotfix27.py RESULT.json PDF OUTDIR [BEFORE_REF]

  ① Typical 상세 상자 안의 행을 **도면에서 실제로 누른다** — 눌린 상자의 열쇠가 그 행인가
     (사용자: "Typical configuration 안의 TT, MOV 클릭이 안 된다")
  ② 수량 승수 판의 높이 · 접기 · 손잡이로 끌기 (1366×768)
  ③ Description From/To 판 (입력칸 · 작성자 칸) 캡처

"전" 은 `git show <ref>:<파일>` 로 화면 파일 셋을 잠시 되돌려 찍고 `finally` 에서 되돌린다.
★ 실 DB 는 열지 않는다 — sha256 대조.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3])
BEFORE = sys.argv[4] if len(sys.argv) > 4 else "HEAD"
OUT.mkdir(parents=True, exist_ok=True)
STATIC = ["app/static/app.js", "app/static/styles.css", "app/static/index.html"]
FOUND: list[str] = []
REAL = ROOT / "app" / "_data" / "app.db"
real_before = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


blob = json.loads(src.read_text()); result = blob.get("result", blob)

# Typical 상세 상자 안의 행 — 결과 json 에서 찾는다 (장 번호를 적어 두지 않는다)
TARGETS = []
for p, lay in (result.get("layers") or {}).items():
    for bx in lay.get("TYPICAL", []):
        x0, y0, x1, y1 = bx["rect"]
        if (x1 - x0) * (y1 - y0) < 2000:
            continue                                   # 표식(작은 원)이 아니라 상세 상자만
        for r in result["rows"]:
            rr = r.get("rect")
            if (str(r["page_no"]) == str(p) and rr and x0 <= rr[0] and rr[2] <= x1
                    and y0 <= rr[1] and rr[3] <= y1):
                TARGETS.append((int(p), r["key"], r.get("type") or r.get("valve_type") or ""))
note(f"Typical 상세 상자 안의 행 {len(TARGETS)}개 · 장 {sorted({t[0] for t in TARGETS})}")


def make_data():
    from app import db, revisions
    data = Path(tempfile.mkdtemp(prefix="audit27-"))
    os.environ["PID_DATA_DIR"] = str(data)
    con = db.connect(data / "app.db")
    job = "audit2700001"
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
            pg = br.new_page(viewport={"width": 1366, "height": 768})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
            pg.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
            pg.reload(); pg.wait_for_timeout(2500)
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.query_selector("a.revrow").click(); pg.wait_for_timeout(9000)

            # ① Typical 상자 안의 행을 도면에서 누른다
            ok = bad = 0
            shot_done = False
            for page_no, key, typ in TARGETS:
                pg.evaluate("(n) => showPage(S.pages.find(p => p.page_no === n))", page_no)
                pg.wait_for_function(f"() => S.page && S.page.page_no === {page_no} && document.querySelectorAll('#ov rect.det').length > 0", timeout=30000)
                pg.wait_for_timeout(600)
                pg.evaluate("() => { deselect(); window.scrollTo(0, 0); }")
                pt = pg.evaluate("""(k) => { const b = document.querySelector(`#ov rect.det[data-key="${k}"]`);
                    if (!b) return null; b.scrollIntoView({block: 'center', inline: 'center'});
                    const r = b.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }""", key)
                if not pt:
                    note(f"   p{page_no} {typ} {key}: 상자가 화면에 없음"); bad += 1; continue
                pg.wait_for_timeout(250)
                pt = pg.evaluate("""(k) => { const r = document.querySelector(`#ov rect.det[data-key="${k}"]`).getBoundingClientRect();
                    return [r.left + r.width / 2, r.top + r.height / 2]; }""", key)
                hit = pg.evaluate("(p) => { const e = document.elementFromPoint(p[0], p[1]); return e ? (e.getAttribute('class') || e.tagName) + '|' + (e.dataset.key || '') : ''; }", pt)
                pg.mouse.click(pt[0], pt[1]); pg.wait_for_timeout(400)
                sel = pg.evaluate("() => S.sel")
                good = sel == key
                ok += good; bad += (not good)
                note(f"   p{page_no} {typ:6} {key}: 맨 위 {hit[:40]} · 누른 뒤 선택 {'그 행' if good else (sel or '없음')}")
                if good and not shot_done and typ.endswith("IT"):
                    pg.screenshot(path=str(OUT / f"{tag}_typical_click.png")); shot_done = True
                elif not shot_done and not good:
                    pg.screenshot(path=str(OUT / f"{tag}_typical_click.png")); shot_done = True
            note(f"[{tag}] ① Typical 상자 안 행 누르기 — 됨 {ok} · 안 됨 {bad}")

            # ② 수량 승수 판
            pg.evaluate("() => { deselect(); window.scrollTo(0, 0); }")
            h0 = pg.evaluate("() => { const m = document.querySelector('#mult-panel'); return m && !m.classList.contains('hidden') ? Math.round(m.getBoundingClientRect().height) : 0; }")
            gw0 = pg.evaluate("() => Math.round(document.querySelector('#gridwrap').getBoundingClientRect().height)")
            note(f"[{tag}] ② 수량 승수 판 높이 {h0}px · 목록 높이 {gw0}px")
            pg.screenshot(path=str(OUT / f"{tag}_mult.png"))
            if pg.query_selector("#gutter-m:not(.hidden)"):
                g = pg.evaluate("() => { const r = document.querySelector('#gutter-m').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
                pg.mouse.move(g[0], g[1]); pg.mouse.down(); pg.mouse.move(g[0], g[1] - 80, steps=6); pg.mouse.up()
                pg.wait_for_timeout(300)
                h1 = pg.evaluate("() => Math.round(document.querySelector('#mult-panel').getBoundingClientRect().height)")
                gw1 = pg.evaluate("() => Math.round(document.querySelector('#gridwrap').getBoundingClientRect().height)")
                note(f"[{tag}]    손잡이를 위로 80px → 판 {h0} → {h1}px · 목록 {gw0} → {gw1}px")
                pg.screenshot(path=str(OUT / f"{tag}_mult_dragged.png"))
                pg.mouse.move(g[0], g[1] - 80 + (h1 - h0) + 80)
                g2 = pg.evaluate("() => { const r = document.querySelector('#gutter-m').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; }")
                pg.mouse.dblclick(g2[0], g2[1]); pg.wait_for_timeout(300)
                h2 = pg.evaluate("() => Math.round(document.querySelector('#mult-panel').getBoundingClientRect().height)")
                note(f"[{tag}]    두 번 누르면 {h2}px")
                pg.click("#mult-panel .mfold"); pg.wait_for_timeout(600)
                h3 = pg.evaluate("() => Math.round(document.querySelector('#mult-panel').getBoundingClientRect().height)")
                gw3 = pg.evaluate("() => Math.round(document.querySelector('#gridwrap').getBoundingClientRect().height)")
                note(f"[{tag}]    접기 → 판 {h3}px · 목록 {gw3}px · 요약 “{' '.join(pg.text_content('#mult-panel .msum').split())}”")
                pg.screenshot(path=str(OUT / f"{tag}_mult_folded.png"))
                pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
                pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
                pg.query_selector("a.revrow").click(); pg.wait_for_timeout(9000)
                kept = pg.evaluate("() => document.querySelector('#mult-panel').classList.contains('folded')")
                note(f"[{tag}]    새로 고친 뒤 접힘 유지 {kept}")
                pg.click("#mult-panel .mfold"); pg.wait_for_timeout(600)

            # ③ From/To 판
            if TARGETS:
                page_no, key, _t = TARGETS[0]
                pg.evaluate(f"() => select('{key}', true)"); pg.wait_for_timeout(1500)
                pg.evaluate("() => { const d = document.querySelector('#descmk'); if (d) d.scrollIntoView({block: 'start'}); }")
                pg.wait_for_timeout(300)
                pg.screenshot(path=str(OUT / f"{tag}_fromto_panel.png"))
                has_in = bool(pg.query_selector("#dm-from-in"))
                note(f"[{tag}] ③ From/To 입력칸 {'있음' if has_in else '없음'}")
            note(f"[{tag}] 페이지 오류: " + (" | ".join(errs) if errs else "없음"))
            br.close()
    finally:
        srv.terminate()


saved = {f: (ROOT / f).read_bytes() for f in STATIC}
try:
    for f in STATIC:
        (ROOT / f).write_bytes(subprocess.check_output(["git", "show", f"{BEFORE}:{f}"], cwd=ROOT))
    shoot("before", make_data())
finally:
    for f, b in saved.items():
        (ROOT / f).write_bytes(b)
shoot("after", make_data())
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / "README.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
