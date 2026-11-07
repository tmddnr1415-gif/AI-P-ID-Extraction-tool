"""hotfix59 — 도면의 x N 라벨로 승수를 고친다: 이 태그만 · 이 페이지 전체 · Shift 로 묶은 범위.

    python3 spike/ui_audit_fb8.py out/regression_3p/AL_NOUF1.json out/hotfix59/ui

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
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "out/hotfix59/ui")
OUT.mkdir(parents=True, exist_ok=True)
src = Path(sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/AL_NOUF1.json")
FOUND: list[str] = []


def note(s):
    print(s, flush=True)
    FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


data = Path(tempfile.mkdtemp(prefix="qtyscope-"))
os.environ["PID_DATA_DIR"] = str(data)
from app import db, revisions                                    # noqa: E402

blob = json.loads(src.read_text()); result = blob.get("result", blob)
con = db.connect(data / "app.db")
job = "qtyscope0001"
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
        from collections import Counter

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

        J = json.dumps
        def labels():
            return pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('g.qtytag')].map(g => [g.dataset.key, g.querySelector('text').textContent]))")
        def grid(keys):
            return pg.evaluate(f"() => {J(keys)}.map(k => {{ const td = document.querySelector('#body tr[data-key=\"'+k+'\"] td[data-col=qty]'); return td ? td.textContent : null; }})")
        def server(keys):
            return pg.evaluate(f"""async () => {{ const j = await (await fetch('/jobs/' + S.job.id + '/rows?tab=ALL')).json();
                const m = Object.fromEntries(j.map(r => [r.key, r.values.qty])); return {J(keys)}.map(k => m[k]); }}""")
        def click_tag(key, shift=False):
            pg.evaluate(f"() => document.querySelector('g.qtytag[data-key={J(key)}]').scrollIntoView({{block:'center', inline:'center'}})")
            pg.wait_for_timeout(250)
            pg.query_selector(f'g.qtytag[data-key="{key}"]').click(modifiers=["Shift"] if shift else [])
            pg.wait_for_timeout(400)
        def author():
            ab = pg.query_selector(".author-bar")
            if not ab:
                note("★ 작성자 확인 줄이 안 뜬다"); raise SystemExit(5)
            ab.query_selector("input").fill("감사")
            ab.query_selector("button.ok").click()
            pg.wait_for_timeout(2500)

        keys = pg.evaluate("() => overlayItems(S.page).filter(it => qtyTagRow(it)).map(it => it.key)")
        page_no = pg.evaluate("() => S.page.page_no")
        note(f"p{page_no} 라벨 {len(labels())}개 · 라벨을 가진 행 {len(keys)}개 · 처음 분포 {dict(Counter(labels().values()))}")

        # ① 라벨을 누르면 고르는 판 — 버튼 셋
        k1 = keys[0]
        click_tag(k1)
        pop = pg.query_selector(".qtypop")
        if not pop:
            note("① ★ 라벨을 눌렀는데 판이 안 뜬다"); raise SystemExit(4)
        btns = [b.inner_text() for b in pop.query_selector_all("button")]
        note(f"① 판의 버튼: {btns}")
        pg.screenshot(path=str(OUT / "1_판_한태그.png"))
        bb = pop.bounding_box()
        pg.screenshot(path=str(OUT / "1_판_확대.png"), clip={"x": max(0, bb["x"] - 160), "y": max(0, bb["y"] - 40),
                                                         "width": bb["width"] + 200, "height": bb["height"] + 80})

        # ② 이 태그만 → x5
        pop.query_selector("input").fill("5")
        pop.query_selector('button[data-scope="one"]').click()
        pg.wait_for_timeout(400); author()
        L = labels()
        note(f"② 이 태그만 x5 → 그 라벨 {L.get(k1)!r} · 목록 {grid([k1])} · 서버 {server([k1])} · 다른 라벨 분포 {dict(Counter(v for k, v in L.items() if k != k1))}")
        pg.screenshot(path=str(OUT / "2_한태그_뒤.png"))

        # ③ 다른 라벨 → 이 페이지 전체 x3
        k2 = keys[1]
        click_tag(k2)
        pop = pg.query_selector(".qtypop")
        pop.query_selector("input").fill("3")
        page_btn = pop.query_selector('button[data-scope="page"]')
        note(f"③ 페이지 버튼: {page_btn.inner_text()!r}")
        page_btn.click(); pg.wait_for_timeout(400); author()
        L = labels()
        note(f"③ 페이지 전체 x3 → 라벨 분포 {dict(Counter(L.values()))} · 목록 {Counter(grid(keys))} · 서버 {Counter(server(keys))}")
        pg.screenshot(path=str(OUT / "3_페이지전체_뒤.png"))

        # ④ Shift + 끌기로 범위를 묶고 그 안의 라벨을 누른다 → 선택에 x7
        rects = pg.evaluate("() => overlayItems(S.page).filter(it => qtyTagRow(it)).map(it => [it.key, it.rect])")
        # 왼쪽 위에서부터 가까운 상자 셋을 덮는 띠
        rects.sort(key=lambda kr: (kr[1][1], kr[1][0]))
        pick = rects[:3]
        x0 = min(r[0] for _, r in pick) - 4; y0 = min(r[1] for _, r in pick) - 4
        x1 = max(r[2] for _, r in pick) + 4; y1 = max(r[3] for _, r in pick) + 4
        pg.evaluate(f"() => {{ const s = $('#stage'); const sc = S.scale || 1; }}")
        p0 = pg.evaluate(f"() => {{ const svg = document.querySelector('#ov'); const b = svg.getBoundingClientRect(); const sc = b.width / S.page.width;"
                         f" return [b.left + {x0} * sc, b.top + {y0} * sc, b.left + {x1} * sc, b.top + {y1} * sc]; }}")
        pg.evaluate(f"() => {{ const svg = document.querySelector('#ov'); const b = svg.getBoundingClientRect(); const sc = b.width / S.page.width;"
                    f" $('#stage').scrollLeft += b.left + {x0} * sc - 300; $('#stage').scrollTop += b.top + {y0} * sc - 300; }}")
        pg.wait_for_timeout(400)
        p0 = pg.evaluate(f"() => {{ const svg = document.querySelector('#ov'); const b = svg.getBoundingClientRect(); const sc = b.width / S.page.width;"
                         f" return [b.left + {x0} * sc, b.top + {y0} * sc, b.left + {x1} * sc, b.top + {y1} * sc]; }}")
        pg.keyboard.down("Shift")
        pg.mouse.move(p0[0], p0[1]); pg.mouse.down()
        pg.mouse.move((p0[0] + p0[2]) / 2, (p0[1] + p0[3]) / 2, steps=5)
        pg.mouse.move(p0[2], p0[3], steps=5); pg.mouse.up()
        pg.keyboard.up("Shift")
        pg.wait_for_timeout(600)
        multi = pg.evaluate("() => [...S.multi]")
        note(f"④ Shift 띠로 묶음 {len(multi)}개 (겨냥 {len(pick)}개)")
        pg.screenshot(path=str(OUT / "4_띠선택.png"))
        if multi:
            click_tag(multi[0])
            pop = pg.query_selector(".qtypop")
            btns = [b.inner_text() for b in pop.query_selector_all("button")] if pop else []
            note(f"④ 묶음 안 라벨을 누른 판: {btns}")
            pg.screenshot(path=str(OUT / "4_판_묶음.png"))
            pop.query_selector("input").fill("7")
            pg.keyboard.press("Enter"); pg.wait_for_timeout(400); author()
            L = labels()
            note(f"④ 선택 x7 → 묶음 라벨 {[L.get(k) for k in multi]} · 목록 {grid(multi)} · 서버 {server(multi)} · 묶음 밖 분포 {dict(Counter(v for k, v in L.items() if k not in multi))}")
            pg.screenshot(path=str(OUT / "5_묶음_뒤.png"))
            # ⑤ 오른쪽 묶음 판에서도 같은 일 — 비우고 적용 = 도면 값으로
            mq = pg.query_selector("#mq-val")
            note(f"⑤ 오른쪽 묶음 판 승수 칸: {bool(mq)} · placeholder {mq.get_attribute('placeholder') if mq else None!r}")
            pg.query_selector("#evidence").screenshot(path=str(OUT / "5_오른쪽_묶음판.png"))
            if mq:
                mq.fill(""); pg.query_selector("#mq-apply").click(); pg.wait_for_timeout(400); author()
                L = labels()
                note(f"⑤ 비우고 적용 → 묶음 라벨 {[L.get(k) for k in multi]} · 서버 {server(multi)} (도면 값으로)")
        if errs:
            note("★ 화면 오류: " + " | ".join(errs[:5]))
        else:
            note("화면 오류 없음")
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=10)

(OUT / "README.md").write_text(
    "# hotfix59 화면 자기검증 — 승수: 이 태그만 · 이 페이지 전체 · Shift 범위\n\n"
    + "\n".join("- " + x for x in FOUND) + "\n", encoding="utf-8")
print("\n=> " + str(OUT / "README.md"))
