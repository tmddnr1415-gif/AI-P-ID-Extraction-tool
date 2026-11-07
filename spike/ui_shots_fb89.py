"""8·9차 피드백 항목을 **그 심볼로 확대해** 찍는다 (54회차 뒤 확인).

    python3 spike/ui_shots_fb89.py out/round54/ui89

`spike/ui_audit_fb89.py` 는 *숫자가 맞는가* 를 묻고, 이 도구는 *눈으로 보이는가*
를 찍는다.  확대·가운데 맞춤은 화면이 이미 하는 것을 그대로 쓴다 —
`select(key, true)` 가 그 장을 열고 SYMBOL_ZOOM(2.2배)으로 심볼을 가운데 둔다.

★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/round54/ui89")
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []

DOCS = [("TC2", "out/regression_3p/TC2.json", "data/TC2_260821.pdf"),
        ("AL NOUF1", "out/regression_3p/AL_NOUF1.json", "data/pid_total.pdf")]
# (문서, 장, 태그, 그림 이름, 무엇을 보이려는가)
SHOTS = [
    ("TC2", 10, "XV",  "9A_TC2_p10_XV",  "9차 [A] — 지시선으로 짝지은 XV"),
    ("TC2", 10, "PCV", "9A_TC2_p10_PCV", "9차 [A] — 몸체를 못 읽어 버블 자리에 선 PCV"),
    ("TC2", 10, "TCV", "9A_TC2_p10_TCV", "9차 [A] — TCV"),
    ("AL NOUF1", 8,  "MOV", "8s4_NOUF1_p8_MOV",  "8차 s4 — p8 MOV"),
    ("AL NOUF1", 12, "PCV", "8s5_NOUF1_p12_PCV", "8차 s5 — p12 PCV"),
    ("AL NOUF1", 21, "XV",  "8s6_NOUF1_p21_XV",  "8차 s6 — p21 XV"),
    ("AL NOUF1", 21, "FCV", "8s6_NOUF1_p21_FCV", "8차 s6 — p21 FCV"),
]


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="fb89shot-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

con = db.connect(data / "app.db"); jobs = {}
for i, (name, res_p, pdf_p) in enumerate(DOCS):
    src, pdf = ROOT / res_p, ROOT / pdf_p
    if not src.exists() or not pdf.exists():
        note(f"⚠ {name}: 자료 없음 — 건너뛴다"); continue
    result = json.loads(src.read_text()); result = result.get("result", result)
    job = f"fb89shot{i:04d}"; jobs[name] = job
    revisions.create_project(data, name)
    con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
                " progress, message, fingerprint, project, revision)"
                " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
                (job, pdf.name, hashlib.sha256(pdf.read_bytes()).hexdigest(),
                 str(pdf.resolve()), time.time() + i,
                 result.get("fingerprint", ""), name, "A"))
    con.commit(); db.store_result(con, job, result); con.commit()
    revisions.record_revision(data, name, "A", job_id=job, pdf_name=pdf.name,
                              compared_with="",
                              result={"counts": {}, "states": {}, "radii": {},
                                      "deleted_candidates": []})
con.close()

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
        for doc in ("TC2", "AL NOUF1"):
            if doc not in jobs:
                continue
            pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2200)
            pg.evaluate("() => document.querySelectorAll('details.pjt')"
                        ".forEach(d => d.open = true)")
            pg.wait_for_timeout(400)
            rr = pg.query_selector(f"a.revrow[href*='{jobs[doc]}']")
            if rr is None:
                note(f"★ {doc}: 결과 행 없음"); continue
            rr.click(); pg.wait_for_timeout(9000)
            # 범례 상자는 그림을 가리므로 접는다
            # 범례 상자는 그림을 가리므로 **찍는 동안만** 숨긴다 (판정에 안 닿는다)
            pg.add_style_tag(content="#ovlegend { display: none !important; }")
            for d, page_no, tag, fname, why in SHOTS:
                if d != doc:
                    continue
                hit = pg.evaluate("""([pno, tag]) => {
                    const r = (S.rows || []).find(x => x.page_no === pno &&
                        ((x.evidence || {}).tag) === tag);
                    if (!r) return null;
                    select(r.key, true);
                    const e = r.evidence || {};
                    return {key: r.key, type: (r.values||{}).type,
                            valve: (r.values||{}).valve_type || "(빈칸)",
                            body: e.body || "(몸체 없음)",
                            basis: JSON.stringify(e.body_basis ?? "").slice(0, 160)};
                }""", [page_no, tag])
                if hit is None:
                    note(f"★ {doc} p{page_no} {tag}: 행 없음"); continue
                pg.wait_for_timeout(3500)
                note(f"{why} — TYPE {hit['type']} · VALVE {hit['valve']}"
                     f" · 몸체 {hit['body']} · 근거 {hit['basis']}")
                pg.locator("#stage").screenshot(path=str(OUT / f"{fname}.png"))
        note("페이지 오류: " + (errs[0] if errs else "없음"))
        br.close()
finally:
    srv.terminate()
(OUT / "확대그림.txt").write_text("\n".join(FOUND) + "\n", encoding="utf8")
print("\n".join(FOUND))
