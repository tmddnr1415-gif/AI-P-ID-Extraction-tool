"""hotfix38 — 개정 대조 화면을 **실제로 띄워서** 확인한다 (추가 라벨 · 삭제 필터 · Remark).

    python3 spike/ui_audit_revision.py <data_dir> <job_B> <out_dir>

`data_dir` 은 `spike/rev_flow_qfe.py` 가 남긴 디렉터리다 (프로젝트 QFE · Rev.A · Rev.B).
확인하는 것: ① 머리줄 개정 라벨(추가 · 삭제 후보 · 짝 태그/기하) ② 개정 필터 '추가만' 의 행이
전부 '개정' 열 = 추가 ③ '삭제만' 의 행이 전부 삭제이고 Remark 에 '대비 삭제' 가 있다
④ 추가 행이 있는 장의 도면에 `text.revtag` = ADD 가 추가 행 수만큼 ⑤ 추가 행을 누르면 근거
패널에 '개정 상태 · 추가 근거' ⑥ 페이지 오류 0.  ★ 실 DB 를 열지 않는다.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
FOUND: list[str] = []


def note(s):
    print(s, flush=True); FOUND.append(s)


s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(90):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2); break
        except Exception:
            time.sleep(1)
    rows = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/rows?tab=ALL", timeout=300).read())
    rev = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/revision", timeout=60).read())
    added = [r for r in rows if (r.get("rev") or {}).get("state") == "ADDED"]
    by_page = {}
    for r in added:
        by_page[r["page_no"]] = by_page.get(r["page_no"], 0) + 1
    page = max(by_page, key=by_page.get) if by_page else None
    note(f"서버 — 추가 {len(added)} · 삭제 후보 {rev['counts'].get('DELETED_CANDIDATE', 0)} · 짝 {rev.get('matched_by')} · 추가가 가장 많은 장 p{page} ({by_page.get(page)})")
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
        pg.screenshot(path=str(OUT / "0_첫화면.png"))
        link = pg.query_selector(f"a.revrow[href='#{JOB}']")
        if link is None:
            note("★ 첫 화면에 Rev.B 행이 없다"); raise SystemExit(2)
        link.click(); pg.wait_for_timeout(12000)
        label = pg.inner_text("#rev-label")
        note(f"① 머리줄: {label!r} — {'맞음' if '추가' in label and '삭제 후보' in label and '짝 태그' in label else '★ 빠진 말이 있다'}")
        # ② 추가만
        pg.select_option("#rev-filter", "ADDED"); pg.wait_for_timeout(1500)
        got = pg.evaluate("() => [...document.querySelectorAll('#grid tbody tr')].map(tr => (tr.querySelector('td[data-col=rev_state]')||{}).textContent)")
        note(f"② '추가만' 필터 — 표시 {len(got)}행 · 개정 열 값 {sorted(set(got))} · 서버 추가 {len(added)} — {'맞음' if len(got) == len(added) and set(got) == {'추가'} else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "1_추가만.png"))
        # ③ 삭제만
        pg.select_option("#rev-filter", "DELETED"); pg.wait_for_timeout(1500)
        dels = pg.evaluate("() => [...document.querySelectorAll('#grid tbody tr')].map(tr => ({st: (tr.querySelector('td[data-col=rev_state]')||{}).textContent, rm: (tr.querySelector('td[data-col=remark]')||{}).textContent, tag: (tr.querySelector('td[data-col=tag_no]')||{}).textContent}))")
        ok3 = dels and all(d["st"].startswith("삭제") and "대비 삭제" in (d["rm"] or "") for d in dels)
        note(f"③ '삭제만' 필터 — 표시 {len(dels)}행 · 서버 삭제 후보 {rev['counts'].get('DELETED_CANDIDATE', 0)} · Remark 예 {[(d['tag'], d['rm'][:60]) for d in dels[:2]]} — {'맞음' if ok3 and len(dels) == rev['counts'].get('DELETED_CANDIDATE', 0) else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "2_삭제만.png"))
        th = pg.query_selector_all("#grid thead th")
        heads = [t.text_content().strip() for t in th]
        i0 = next(i for i, h in enumerate(heads) if h.startswith("개정")); i1 = next(i for i, h in enumerate(heads) if h.startswith("Remark"))
        b0, b1 = th[i0].bounding_box(), th[i1].bounding_box(); grid = pg.query_selector("#grid").bounding_box()
        pg.screenshot(path=str(OUT / "3_삭제만_열_개정~Remark.png"), clip={"x": b0["x"] - 4, "y": grid["y"], "width": b1["x"] + b1["width"] - b0["x"] + 8, "height": min(grid["height"], 600)})
        # ④ 도면 위 ADD 라벨
        pg.select_option("#rev-filter", ""); pg.wait_for_timeout(800)
        if page is not None:
            pg.select_option("#page-select", str(page)); pg.wait_for_timeout(3000)
            # <text> 안의 <title>(툴팁)도 textContent 에 들어오므로 글자 노드만 읽는다
            n_add = pg.evaluate("() => [...document.querySelectorAll('text.revtag')].filter(t => [...t.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue).join('') === 'ADD').length")
            rings = pg.evaluate("() => document.querySelectorAll('rect.revring.rev-added').length")
            note(f"④ p{page} 도면 — 'ADD' 글자 {n_add} · 추가 링 {rings} · 서버 추가 행 {by_page[page]} — {'맞음' if n_add == rings == by_page[page] else '★ 틀림'}")
            pg.screenshot(path=str(OUT / f"4_p{page}_도면_ADD.png"))
            # 확대해서 ADD 글자가 읽히는지 — 3배로 키우고 첫 링이 보이게 스크롤한 뒤 그 둘레를 자른다
            pg.evaluate("() => { zoomBy(3); const r = document.querySelector('rect.revring.rev-added'); const st = document.getElementById('stage');"
                        " const b = r.getBoundingClientRect(), s = st.getBoundingClientRect();"
                        " st.scrollLeft += b.x - s.x - st.clientWidth / 2; st.scrollTop += b.y - s.y - st.clientHeight / 2; }")
            pg.wait_for_timeout(1200)
            bb = pg.evaluate("() => { const r = document.querySelector('rect.revring.rev-added'); const b = r.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; }")
            if bb:
                pg.screenshot(path=str(OUT / f"5_p{page}_ADD_확대.png"), clip={"x": max(0, bb[0] - 120), "y": max(0, bb[1] - 70), "width": bb[2] + 240, "height": bb[3] + 140})
            # ⑤ 근거 패널
            key = next(r["key"] for r in added if r["page_no"] == page)
            pg.evaluate(f"() => select({json.dumps(key)}, false)"); pg.wait_for_timeout(800)
            panel = pg.inner_text("#evidence")
            note(f"⑤ 근거 패널 — '개정 상태' {'있음' if '개정 상태' in panel else '★ 없음'} · '추가 근거' {'있음' if '추가 근거' in panel else '★ 없음'} — {[l for l in panel.splitlines() if '추가' in l][:2]}")
            pg.query_selector("#evidence").screenshot(path=str(OUT / "6_근거패널_추가.png"))
        note(f"⑥ 페이지 오류 {len(errs)}" + (" — " + errs[0][:200] if errs else ""))
        br.close()
finally:
    srv.terminate()
    (OUT / "README.md").write_text("# hotfix38 UI 자기검증 — 개정 대조 화면\n\n" + "\n".join(f"- {s}" for s in FOUND) + "\n", encoding="utf-8")
