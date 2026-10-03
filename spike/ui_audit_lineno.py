"""hotfix36 — 목록의 Tag No. · Line No. 열과 근거 패널을 **실제로 띄워서** 확인한다.

    python3 spike/ui_audit_lineno.py out/hotfix36/QFE_run3.json data/QFE_260326.pdf out/hotfix36/ui [쪽]

확인하는 것: ① 그리드 머리글에 Type · Tag No. · Line No. 가 **그 순서**로 있는가
② 그 장의 행 중 line_no 가 있는 행의 칸에 그 글자가 보이는가 ③ 행을 누르면 근거 패널이
`Line No. 근거` 를 적는가 ④ 페이지 오류 0.  ★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1]); pdf = Path(sys.argv[2]); OUT = Path(sys.argv[3]); PAGE = sys.argv[4] if len(sys.argv) > 4 else "46"
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="linenoui-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "lineaudit001"
sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
revisions.create_project(data, "QFE")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, pdf.name, sha, str(pdf.resolve()), time.time(), result.get("fingerprint", ""), "QFE", "A"))
con.commit(); db.store_result(con, job, result); con.commit(); con.close()
revisions.record_revision(data, "QFE", "A", job_id=job, pdf_name=pdf.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})
port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector("a.revrow")
        if rr is None:
            pg.screenshot(path=str(OUT / "0_첫화면_행없음.png")); note("★ 결과로 들어갈 행이 없다"); raise SystemExit(2)
        rr.click(); pg.wait_for_timeout(8000)
        pg.select_option("#page-select", PAGE); pg.wait_for_timeout(2500)
        heads = pg.evaluate("() => [...document.querySelectorAll('#grid thead th')].map(t => t.textContent.trim())")
        note("머리글: " + repr(heads))
        idx = lambda name: next(i for i, h in enumerate(heads) if h.startswith(name))
        i_type, i_tag, i_line = idx("Type"), idx("Tag No."), idx("Line No.")
        note(f"① 머리글 순서 Type@{i_type} · Tag No.@{i_tag} · Line No.@{i_line} — {'맞음' if i_type < i_tag < i_line else '★ 틀림'}")
        cells = pg.evaluate("""() => [...document.querySelectorAll('#grid tbody tr')].map(tr => ({
            tag: (tr.querySelector('td[data-col=tag_no]')||{}).textContent, line: (tr.querySelector('td[data-col=line_no]')||{}).textContent,
            type: (tr.querySelector('td[data-col=type]')||{}).textContent }))""")
        with_line = [c for c in cells if (c.get("line") or "").strip()]
        with_tag = [c for c in cells if (c.get("tag") or "").strip()]
        note(f"② p{PAGE} 목록 {len(cells)}행 · Tag No. 있는 행 {len(with_tag)} · Line No. 있는 행 {len(with_line)} · 예 {with_line[:3]}")
        pg.screenshot(path=str(OUT / f"1_p{PAGE}_목록.png"))
        # 열 셋만 크롭 — 열의 bounding box 로 (12회차 규칙)
        th = pg.query_selector_all("#grid thead th")
        b0, b1 = th[i_type].bounding_box(), th[i_line].bounding_box()
        grid = pg.query_selector("#grid").bounding_box()
        pg.screenshot(path=str(OUT / f"2_p{PAGE}_열_Type_Tag_Line.png"),
                      clip={"x": b0["x"] - 4, "y": grid["y"], "width": b1["x"] + b1["width"] - b0["x"] + 8, "height": min(grid["height"], 700)})
        key = pg.evaluate("""() => { const tr = [...document.querySelectorAll('#grid tbody tr')].find(tr => ((tr.querySelector('td[data-col=line_no]')||{}).textContent||'').trim());
            return tr ? tr.dataset.key : null; }""")
        if key:
            pg.evaluate(f"() => select({json.dumps(key)}, false)"); pg.wait_for_timeout(800)
            panel = pg.inner_text("#evidence") if pg.query_selector("#evidence") else ""
            has = "Line No. 근거" in panel
            note(f"③ 근거 패널 'Line No. 근거' {'있음' if has else '★ 없음'} — " + repr([l for l in panel.splitlines() if 'Line No' in l][:3]))
            ev = pg.query_selector("#evidence")
            if ev: ev.screenshot(path=str(OUT / "3_근거패널.png"))
        else:
            note("③ ★ line_no 가 있는 행이 이 장에 없다")
        note(f"④ 페이지 오류 {len(errs)}" + (" — " + errs[0][:200] if errs else ""))
        br.close()
finally:
    srv.terminate()
    (OUT / "README.md").write_text("# hotfix36 UI 자기검증 — Line No. 열\n\n" + "\n".join(f"- {s}" for s in FOUND) + "\n", encoding="utf-8")
