"""hotfix40 — 나란히 보기(왼쪽 최신 Rev · 오른쪽 직전 Rev 도면)를 **실제로 띄워서** 확인한다.

    python3 spike/ui_audit_sidebyside.py <data_dir> <job_B> <out_dir> [page_no]

① Rev.B 를 열면 스위치에 '나란히' 버튼 ② 누르면 오른쪽 목록이 숨고 직전 Rev 의 같은 도면번호
장이 상자와 함께 선다 ③ 장을 바꾸면 오른쪽도 따라간다 ④ 확대하면 둘 다 같은 배율 ⑤ 왼쪽을
스크롤하면 오른쪽도 ⑥ 삭제 후보가 있는 장에서 붉은 DEL 표식 ⑦ 끄면 목록이 돌아온다 ⑧ 페이지 오류 0.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
PAGE = sys.argv[4] if len(sys.argv) > 4 else None
OUT.mkdir(parents=True, exist_ok=True)
FOUND = []
def note(s): print(s, flush=True); FOUND.append(s)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(90):
        try: urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception: time.sleep(1)
    rev = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/revision", timeout=60).read())
    prev = rev.get("previous_job_id"); note(f"서버 — previous_job_id {prev!r} · compared_with {rev.get('compared_with')}")
    dels = rev.get("deleted_candidates") or []
    by_dwg = {}
    for d in dels: by_dwg[d.get("drawing_no")] = by_dwg.get(d.get("drawing_no"), 0) + 1
    best_dwg = max(by_dwg, key=by_dwg.get) if by_dwg else None
    note(f"삭제 후보 {len(dels)} · 가장 많은 장 {best_dwg} ({by_dwg.get(best_dwg)})")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1800, "height": 1000})
        errs = []; reqs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.on("request", lambda r: reqs.append(r.url))
        pg.goto(f"http://127.0.0.1:{port}/#{JOB}")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=120000); pg.wait_for_timeout(1500)
        # 왼쪽 도면 창을 넓힌다 — 나란히 볼 때 둘이 비슷한 폭이 되게
        sw = pg.inner_text("#rev-switch")
        note(f"① 스위치: {sw!r} — {'맞음' if '나란히' in sw else '★ 없음'}")
        # 장 선택 — 삭제 후보가 가장 많은 장 (없으면 인자/첫 장)
        target = None
        pages = pg.evaluate("() => S.pages.map(p => ({n: p.page_no, d: p.drawing_no}))")
        if PAGE: target = int(PAGE)
        else:
            # 삭제 후보가 가장 많은 **이번 결과에 있는** 장 (장부에만 있는 장은 왼쪽에 띄울 수 없다)
            have = {p["d"] for p in pages}
            cand = sorted(((n, d) for d, n in by_dwg.items() if d in have), reverse=True)
            target = next((p["n"] for p in pages if cand and p["d"] == cand[0][1]), None)
        if target: pg.select_option("#page-select", str(target)); pg.wait_for_timeout(2000)
        before = pg.evaluate("() => ({rows: document.querySelectorAll('#grid tbody tr').length, gridVisible: !!(document.querySelector('#grid') && document.querySelector('#grid').offsetParent)})")
        n0 = len(reqs); t = time.time()
        pg.click("#rev-switch button.side")
        pg.wait_for_function("() => S.side && document.querySelector('#cmp-sheet') && document.querySelector('#cmp-sheet').complete && document.querySelector('#cmp-sheet').naturalWidth > 0", timeout=60000)
        pg.wait_for_timeout(1200)
        st = pg.evaluate("""() => ({side: S.side, compare: document.querySelector('#right').classList.contains('compare'),
            gridVisible: !!(document.querySelector('#grid') && document.querySelector('#grid').offsetParent),
            head: document.querySelector('#cmp-head').innerText, foot: document.querySelector('#cmp-foot').innerText,
            leftDwg: S.page.drawing_no, leftPage: S.page.page_no, rightDwg: S.cmpPage && S.cmpPage.drawing_no, rightPage: S.cmpPage && S.cmpPage.page_no,
            boxes: document.querySelectorAll('#cmp-ov rect.cdet').length, gone: document.querySelectorAll('#cmp-ov rect.cdet.gone').length,
            dels: document.querySelectorAll('#cmp-ov circle.delmark').length,
            leftBoxes: document.querySelectorAll('#ov rect.det').length,
            zl: getComputedStyle(document.querySelector('#wrap')).transform, zr: getComputedStyle(document.querySelector('#cmp-wrap')).transform})""")
        dt = round((time.time() - t) * 1000)
        note(f"② 나란히 켬 — {dt}ms · 요청 {len(reqs) - n0} · 오른쪽 목록 숨음 {not st['gridVisible']} · 왼쪽 {st['leftDwg']} p{st['leftPage']} ↔ 오른쪽 {st['rightDwg']} p{st['rightPage']} · 오른쪽 상자 {st['boxes']} (삭제 후보 상자 {st['gone']} · ✕ {st['dels']}) · 왼쪽 상자 {st['leftBoxes']} — {'맞음' if st['compare'] and not st['gridVisible'] and (st['leftDwg'] == st['rightDwg'] or '도면번호 바뀜' in st['head']) and st['dels'] > 0 else '★ 틀림'}")
        note(f"   머리줄: {st['head']!r}")
        note(f"   바닥줄: {st['foot']!r}")
        note(f"④ 배율 왼쪽 {st['zl']} = 오른쪽 {st['zr']} — {'맞음' if st['zl'] == st['zr'] else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "1_나란히.png"))
        # 확대 두 번 + 왼쪽 스크롤 → 오른쪽 따라오나
        pg.click("#left .toolbar button[data-z='1']"); pg.click("#left .toolbar button[data-z='1']"); pg.wait_for_timeout(400)
        pg.evaluate("() => { const s = document.querySelector('#stage'); s.scrollLeft = 600; s.scrollTop = 350; }")
        pg.wait_for_timeout(500)
        sc = pg.evaluate("() => { const a = document.querySelector('#stage'), b = document.querySelector('#cmp-stage'); return {al: a.scrollLeft, at: a.scrollTop, bl: b.scrollLeft, bt: b.scrollTop, zl: getComputedStyle(document.querySelector('#wrap')).transform, zr: getComputedStyle(document.querySelector('#cmp-wrap')).transform}; }")
        note(f"⑤ 확대 뒤 왼쪽 스크롤 ({sc['al']},{sc['at']}) → 오른쪽 ({sc['bl']},{sc['bt']}) · 배율 같음 {sc['zl'] == sc['zr']} — {'맞음' if abs(sc['al'] - sc['bl']) <= 2 and abs(sc['at'] - sc['bt']) <= 2 and sc['zl'] == sc['zr'] else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "2_확대_동기.png"))
        # 삭제 표식 확대 크롭 — 첫 ✕ 자리
        # 삭제 표식 확대 크롭 — 첫 ✕ 를 오른쪽 창 가운데로 스크롤해(왼쪽도 따라온다) 두 창을 함께 찍는다
        box = pg.evaluate("""() => { const c = document.querySelector('#cmp-ov circle.delmark'); if (!c) return null;
            const cs = document.querySelector('#cmp-stage'); const r = c.getBoundingClientRect(), s = cs.getBoundingClientRect();
            cs.scrollLeft += (r.x + r.width / 2) - (s.x + s.width / 2); cs.scrollTop += (r.y + r.height / 2) - (s.y + s.height / 2);
            return {x: s.x, y: s.y, w: s.width, h: s.height}; }""")
        pg.wait_for_timeout(600)
        note(f"   ✕ 크롭 자리 {box}")
        if box:
            pg.screenshot(path=str(OUT / "3_삭제표식_두창.png"))
            pg.screenshot(path=str(OUT / "3_삭제표식_크롭.png"), clip={"x": box["x"], "y": box["y"], "width": box["w"], "height": box["h"]})
        # 장 바꾸기 → 오른쪽도
        have = {p["d"] for p in pages}
        cand2 = sorted(((n, d) for d, n in by_dwg.items() if d in have), reverse=True)
        other = next((p for p in pages if len(cand2) > 2 and p["d"] == cand2[2][1]), None) \
            or next((p for p in pages if p["n"] != (target or pages[0]["n"]) and p["d"]), None)
        if other:
            pg.select_option("#page-select", str(other["n"]))
            pg.wait_for_function("() => S.cmpPage === null || (S.cmpPage && S.cmpPage.drawing_no === S.page.drawing_no && document.querySelector('#cmp-sheet').complete)", timeout=60000); pg.wait_for_timeout(800)
            fo = pg.evaluate("() => ({l: S.page.drawing_no, r: S.cmpPage && S.cmpPage.drawing_no, head: document.querySelector('#cmp-head').innerText})")
            note(f"③ 장 바꿈 → 왼쪽 {fo['l']} · 오른쪽 {fo['r']} — {'맞음' if fo['l'] == fo['r'] or fo['r'] is None else '★ 틀림'} · {fo['head']!r}")
        # 끄기
        pg.click("#rev-switch button.side"); pg.wait_for_timeout(600)
        after = pg.evaluate("() => ({side: S.side, gridVisible: !!(document.querySelector('#grid') && document.querySelector('#grid').offsetParent), rows: document.querySelectorAll('#grid tbody tr').length, cmpHidden: document.querySelector('#cmp').classList.contains('hidden')})")
        note(f"⑦ 끔 — 목록 보임 {after['gridVisible']} · 행 {after['rows']} (전 {before['rows']}) · 비교 창 숨음 {after['cmpHidden']} — {'맞음' if after['gridVisible'] and after['rows'] == before['rows'] and after['cmpHidden'] else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "4_끈뒤.png"))
        # '이전' 을 누르면 나란히가 꺼지고, 이전 보기에서 '나란히' 를 누르면 현재로 돌아와 켜진다
        pg.click("#rev-switch button.prev"); pg.wait_for_function("() => S.job && S.job.id === %r && !S.loading" % prev, timeout=60000); pg.wait_for_timeout(1000)
        pg.click("#rev-switch button.side")
        pg.wait_for_function("() => S.side && S.job.id === %r && S.cmpPage !== undefined" % JOB, timeout=60000); pg.wait_for_timeout(1000)
        bk = pg.evaluate("() => ({job: S.job.id, side: S.side})")
        note(f"⑥ 이전 보기에서 '나란히' → 왼쪽이 현재({bk['job'] == JOB})로 돌아와 켜짐({bk['side']}) — {'맞음' if bk['job'] == JOB and bk['side'] else '★ 틀림'}")
        note(f"⑧ 페이지 오류 {len(errs)}" + (" — " + errs[0][:300] if errs else ""))
        br.close()
finally:
    srv.terminate()
(OUT / "README.md").write_text("# hotfix40 나란히 보기 자기검증\n\n" + "\n".join(f"- {x}" for x in FOUND) + "\n", encoding="utf-8")
