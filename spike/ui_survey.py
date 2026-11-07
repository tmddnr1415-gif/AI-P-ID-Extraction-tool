"""UI 실태 조사 — 주요 화면을 두 해상도로 찍는다 (hotfix26 · 고치기 전에 본다).

    python3 spike/ui_survey.py RESULT.json PDF OUTDIR [tag]

찍는 것: 첫 화면 · 결과 화면(기본) · 행을 고른 결과 화면 · 근거 패널 전체 · 출력 범위 판 ·
승수 패널 · 검토 필요만 필터.  해상도 1366×768 · 1700×1000.
★ 실 DB 를 열지 않는다 — sha256 대조.
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3])
TAG = sys.argv[4] if len(sys.argv) > 4 else "now"
OUT.mkdir(parents=True, exist_ok=True)
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

from app import db, revisions                                    # noqa: E402
data = Path(tempfile.mkdtemp(prefix="survey-"))
os.environ["PID_DATA_DIR"] = str(data)
con = db.connect(data / "app.db")
job = "survey000001"
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
        for W, H in ((1366, 768), (1700, 1000)):
            pg = br.new_page(viewport={"width": W, "height": H})
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pfx = f"{TAG}_{W}x{H}"
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
            pg.screenshot(path=str(OUT / f"{pfx}_0_home.png"))
            pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
            pg.query_selector("a.revrow").click(); pg.wait_for_timeout(8000)
            pg.screenshot(path=str(OUT / f"{pfx}_1_result.png"))
            # 머리줄이 몇 줄로 꺾이나
            hh = pg.evaluate("() => { const h = document.querySelector('header.head'); return h ? Math.round(h.getBoundingClientRect().height) : null; }")
            wraps = pg.evaluate("""() => [...document.querySelectorAll('header.head > *')].map(e => {
                const r = e.getBoundingClientRect(); return [e.className || e.tagName, Math.round(r.height)]; })""")
            note(f"[{pfx}] 머리줄 높이 {hh} · 층별 {wraps}")
            # 그리드 열 폭 · 가로 스크롤 여부
            gw = pg.evaluate("""() => { const t = document.querySelector('#grid'); const w = t ? t.closest('.gridwrap, .grid, div') : null;
                return t ? [t.scrollWidth, t.clientWidth, (w ? w.clientWidth : null),
                            [...t.querySelectorAll('thead th')].map(th => th.textContent.trim() + ':' + Math.round(th.getBoundingClientRect().width))] : null; }""")
            note(f"[{pfx}] 그리드 폭 {gw}")
            # 행을 고른 화면 + 근거 패널
            pg.evaluate(f"() => select('{seal_row['key']}', true)"); pg.wait_for_timeout(3000)
            pg.screenshot(path=str(OUT / f"{pfx}_2_selected.png"))
            ev = pg.evaluate("() => { const e = document.querySelector('#evidence'); const r = e.getBoundingClientRect(); return [Math.round(r.height), e.scrollHeight, [...e.querySelectorAll('dt')].length]; }")
            note(f"[{pfx}] 근거 패널 보이는 높이 {ev[0]} · 내용 높이 {ev[1]} · 항목 {ev[2]}")
            pg.evaluate("() => { const e = document.querySelector('#evidence'); e.style.maxHeight = 'none'; e.style.overflow = 'visible'; }")
            pg.locator("#evidence").screenshot(path=str(OUT / f"{pfx}_3_evidence_full.png"))
            pg.evaluate("() => { const e = document.querySelector('#evidence'); e.style.maxHeight = ''; e.style.overflow = ''; }")
            # 범례 판 크기
            lg = pg.evaluate("() => { const l = document.querySelector('#ovlegend'); const r = l.getBoundingClientRect(); const st = document.querySelector('#stage').getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height), Math.round(st.width), Math.round(st.height)]; }")
            note(f"[{pfx}] 범례 판 {lg[0]}x{lg[1]} · 도면 창 {lg[2]}x{lg[3]} (판이 창의 {round(100*lg[0]*lg[1]/(lg[2]*lg[3]))}%)")
            # 출력 범위 판
            pg.click("#scope > summary"); pg.wait_for_timeout(500)
            pg.screenshot(path=str(OUT / f"{pfx}_4_scope.png"))
            pg.click("#scope > summary"); pg.wait_for_timeout(200)
            # 검토 필요만
            vis = pg.evaluate("() => { const c = document.querySelector('#only-review'); if (!c) return null; const r = c.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height), innerWidth]; }")
            note(f"[{pfx}] '검토 필요만' 체크 자리 {vis}")
            if vis and vis[2] > 0:
                pg.evaluate("() => document.querySelector('#only-review').click()"); pg.wait_for_timeout(800)
                pg.screenshot(path=str(OUT / f"{pfx}_5_review_only.png"))
                pg.evaluate("() => document.querySelector('#only-review').click()"); pg.wait_for_timeout(300)
            # 검토 탭
            tabs = pg.evaluate("() => [...document.querySelectorAll('#tabs button, #tabs a')].map(b => [b.textContent.trim(), b.dataset.tab || '', Math.round(b.getBoundingClientRect().width)])")
            note(f"[{pfx}] 탭 {tabs}")
            rt = pg.query_selector("#tabs [data-tab='REVIEW']")
            if rt:
                rt.click(); pg.wait_for_timeout(1000)
                pg.screenshot(path=str(OUT / f"{pfx}_6_review_tab.png"))
                at = pg.query_selector("#tabs [data-tab='ALL']")
                if at: at.click(); pg.wait_for_timeout(500)
            # 승수 패널
            mp = pg.query_selector("#mult-panel")
            note(f"[{pfx}] 승수 패널 있음: {bool(mp)} · 보임: {bool(mp and mp.is_visible())}")
            fonts = pg.evaluate("""() => { const g = s => { const e = document.querySelector(s); return e ? getComputedStyle(e).fontSize : null; };
                return {grid: g('#grid td'), evidence: g('#evidence dd'), legend: g('#ovlegend .ovl-label'), head: g('header.head'), body: g('body')}; }""")
            note(f"[{pfx}] 글자 크기 {fonts}")
            note(f"[{pfx}] 페이지 오류: " + (" | ".join(errs) if errs else "없음"))
            pg.close()
        br.close()
finally:
    srv.terminate()
real_after = hashlib.sha256(REAL.read_bytes()).hexdigest() if REAL.exists() else ""
note(f"실 DB sha256 같음: {real_before == real_after}")
(OUT / f"README_{TAG}.txt").write_text("\n".join(FOUND) + "\n", encoding="utf-8")
