"""UAD DXF p11~p15 — 식별 결과 화면 스크린샷 (측정 전용 · 엔진 0줄).

    python3 spike/dxf_shots_p11_p15.py out/round55/UAD_DXF.json out/uad_dxf_p11_p15

55회차 결과를 **그대로 열어** (재분석 없음 · 13회차 프로젝트 영속) 장마다 넷을 찍는다:
  p<n>_1_raw.png            오버레이 칸을 전부 끈 화면 (도면만)
  p<n>_2_overlay.png        오버레이 + 범례 패널 (확대율 "맞춤")
  p<n>_2b_overlay_zoom.png  계기가 가장 몰린 구역 확대 (고르지 않고 계산으로 집는다)
  p<n>_3_grid.png           그 장 행 전부 (검색창에 도면번호를 쳐서 좁힌다)
`p<n>_4_pdf_overlay.png` 는 이 환경에 UAD **PDF 가 없어** 찍지 않는다.
★ 실 DB 를 열지 않는다 (`PID_DATA_DIR` 격리).
"""
from __future__ import annotations
import hashlib, json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/round55/UAD_DXF.json")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/uad_dxf_p11_p15")
OUT.mkdir(parents=True, exist_ok=True)
PAGES = [11, 12, 13, 14, 15]
ZIP = ROOT / "data" / "uad_dxf.zip"


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def dense_window(rects, w, h, span=170.0):
    """계기가 가장 몰린 정사각 구역의 중심.  고르는 것이 아니라 세는 것이다."""
    if not rects:
        return (w / 2, h / 2, span)
    best, cx, cy = -1, w / 2, h / 2
    cs = [((r[0] + r[2]) / 2, (r[1] + r[3]) / 2) for r in rects]
    for x, y in cs:
        n = sum(1 for a, b in cs if abs(a - x) <= span / 2 and abs(b - y) <= span / 2)
        if n > best:
            best, cx, cy = n, x, y
    inside = [(a, b) for a, b in cs if abs(a - cx) <= span / 2 and abs(b - cy) <= span / 2]
    cx = sum(a for a, _ in inside) / len(inside); cy = sum(b for _, b in inside) / len(inside)
    return (cx, cy, span)


data = Path(tempfile.mkdtemp(prefix="dxfp11-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

res = json.loads(src.read_text()); res = res.get("result", res)
con = db.connect(data / "app.db")
job = "dxfp11p15001"
revisions.create_project(data, "UAD-DXF")
con.execute("INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
            " progress, message, fingerprint, project, revision, input_kind)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?,'DXF')",
            (job, ZIP.name, hashlib.sha256(ZIP.read_bytes()).hexdigest(), str(ZIP.resolve()),
             time.time(), res.get("fingerprint", ""), "UAD-DXF", "A"))
con.commit(); db.store_result(con, job, res); con.commit(); con.close()
revisions.record_revision(data, "UAD-DXF", "A", job_id=job, pdf_name=ZIP.name, compared_with="",
                          result={"counts": {}, "states": {}, "radii": {}, "deleted_candidates": []})

port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
facts = []
try:
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    rows = res["rows"]
    pages = {p["page_no"]: p for p in res["pages"]}
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1760, "height": 1180})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
        pg.evaluate("() => document.querySelectorAll('details.pjt').forEach(d => d.open = true)")
        pg.wait_for_timeout(400)
        rr = pg.query_selector(f"a.revrow[href*='{job}']") or pg.query_selector("a.revrow")
        assert rr is not None, "결과 행 없음"
        rr.click(); pg.wait_for_timeout(9000)
        pg.add_style_tag(content="#ovlegend { font-size: 11px; }")
        for n in PAGES:
            p = pages[n]
            mine = [r for r in rows if r["page_no"] == n]
            pg.select_option("#page-select", str(n))
            # ⚠ `S.natural` 만 보면 안 된다 — 앞 장의 값이 남아 있어 조건이 곧바로
            # 통과하고, 그 사이 `fit()` 이 `naturalWidth = 0` 으로 돌아 확대율이 inf 가
            # 된다 (첫 실행에서 p12·p13·p14 가 실제로 그랬다).  **그 장의 그림이
            # 실렸는지**를 `#sheet` 자신에게 묻는다.
            pg.wait_for_function(
                "() => { const i = document.querySelector('#sheet');"
                " return S.page && S.page.page_no === %d && i.complete && i.naturalWidth > 0"
                " && i.src.includes('/page/%d.png'); }" % (n, n), timeout=120000)
            pg.wait_for_timeout(1500)
            # ── ① 도면만 — 오버레이 칸을 전부 끈다 (실제 체크박스를 누른다)
            pg.eval_on_selector_all(".ovl", "els => els.forEach(e => { if (e.checked) e.click(); })")
            pg.wait_for_timeout(500)
            pg.click("[data-z='0']"); pg.wait_for_timeout(600)
            pg.locator("#stage").screenshot(path=str(OUT / f"p{n}_1_raw.png"))
            # ── ② 오버레이 + 범례 (맞춤)
            pg.eval_on_selector_all(".ovl", "els => els.forEach(e => { if (!e.checked) e.click(); })")
            pg.wait_for_timeout(600)
            pg.click("[data-z='0']"); pg.wait_for_timeout(600)
            seen = pg.evaluate("""() => {
                const legend = [...document.querySelectorAll('.ovl-row')]
                    .filter(r => !/\\(그중\\)/.test(r.innerText) && /\\d+\\s*$/.test(r.innerText.trim()))
                    .map(r => r.innerText.replace(/\\s+/g, ' ').trim());
                const nums = legend.map(t => Number((t.match(/(\\d+)\\s*$/) || [0, 0])[1]));
                return {legend, sum: nums.slice(0, 5).reduce((a, b) => a + b, 0),
                        all_sum: nums.reduce((a, b) => a + b, 0),
                        boxes: document.querySelectorAll('#ov rect.det').length,
                        natural: [S.natural.w, S.natural.h],
                        page: [S.page.width, S.page.height], zoom: S.zoom};
            }""")
            pg.locator("#left").screenshot(path=str(OUT / f"p{n}_2_overlay.png"))
            # ── ②b 계기가 가장 몰린 구역 (세어서 집는다)
            cx, cy, span = dense_window([r["rect"] for r in mine], p["width"], p["height"])
            zoomed = pg.evaluate("""([cx, cy, span]) => {
                const stage = document.querySelector('#stage');
                const scale = S.natural.w / (S.page.width || 1);
                const want = Math.min(stage.clientWidth / (span * scale),
                                      stage.clientHeight / (span * scale));
                zoomBy(want / S.zoom);
                stage.scrollLeft = cx * scale * S.zoom - stage.clientWidth / 2;
                stage.scrollTop = cy * scale * S.zoom - stage.clientHeight / 2;
                return S.zoom;
            }""", [cx, cy, span])
            pg.wait_for_timeout(900)
            pg.locator("#stage").screenshot(path=str(OUT / f"p{n}_2b_overlay_zoom.png"))
            pg.click("[data-z='0']"); pg.wait_for_timeout(400)
            # ── ③ 그 장 행 전부 — 검색창에 도면번호
            pg.fill("#filter", p["drawing_no"] or "")
            pg.wait_for_timeout(900)
            grid = pg.evaluate("""() => ({
                rows: document.querySelectorAll('#body tr').length,
                count: (document.querySelector('#count') || {}).textContent || '',
                chips: (document.querySelector('#chips') || {}).innerText || ''})""")
            pg.add_style_tag(content="#gridwrap { overflow: visible; }")
            pg.wait_for_timeout(300)
            pg.locator("#grid").screenshot(path=str(OUT / f"p{n}_3_grid.png"))
            pg.fill("#filter", ""); pg.wait_for_timeout(500)
            types = {}
            for r in mine:
                t = (r.get("values") or {}).get("type") or "?"
                types[t] = types.get(t, 0) + 1
            facts.append({"page": n, "drawing_no": p["drawing_no"], "kind": p["page_kind"],
                          "tier": (res["dxf"]["tiers"].get(str(n)) or {}).get("tier", "-"),
                          "rows": len(mine), "grid_rows": grid["rows"], "count_text": grid["count"].strip(),
                          "boxes": seen["boxes"], "legend_sum": seen["sum"], "legend": seen["legend"],
                          "natural": seen["natural"], "page_size": seen["page"],
                          "zoom_fit": seen["zoom"], "zoom_dense": zoomed,
                          "dense_centre": [round(cx, 1), round(cy, 1), span],
                          "types": dict(sorted(types.items(), key=lambda kv: -kv[1])),
                          "tagged": sum(1 for r in mine if (r.get("values") or {}).get("tag_no")
                                        not in (None, "", "....."))})
            print(f"p{n} rows {len(mine)} grid {grid['rows']} boxes {seen['boxes']} "
                  f"legend {seen['sum']} zoom {seen['zoom']:.2f}→{zoomed:.2f}", flush=True)
        print("페이지 오류:", errs[:3] or "없음")
        br.close()
finally:
    srv.terminate()
    (OUT / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1))
print("→", OUT)
