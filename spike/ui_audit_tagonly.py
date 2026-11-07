"""hotfix43 — 개정 '수정' 이 태그가 달라진 행뿐인지 **띄워서** 확인한다.

    python3 spike/ui_audit_tagonly.py <data_dir> <job_B> <out_dir>

① 머리줄 수정 수 = 서버 counts.MODIFIED ② '수정만 (태그 바뀜)' 필터 → 행 수 같음 · 모든 행의
바뀐 칸이 tag_no 뿐 ③ 수정 행 근거 패널에 '바뀐 태그 … → …' ④ 변경 없음인데 값이 다른 행의
근거 패널에 '값이 다른 칸 (개정 판정에는 쓰지 않음)' ⑤ 자리 이동만 있는 행은 변경 없음
⑥ 나란히 보기의 변경 목록 '수정' 항목 글자가 '태그 … → …' ⑦ 페이지 오류 0.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
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
    counts = rev.get("counts") or {}
    note(f"서버 counts — {counts}")
    rows = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/rows?tab=ALL", timeout=120).read())
    rows = rows if isinstance(rows, list) else rows.get("rows", rows)
    mods = [r for r in rows if (r.get("rev") or {}).get("state") == "MODIFIED"]
    bad = [r for r in mods if [c.get("field") for c in r["rev"].get("changed") or []] != ["tag_no"]]
    note(f"② 서버 수정 행 {len(mods)} · 바뀐 칸이 tag_no 가 아닌 행 {len(bad)} — {'맞음' if not bad else '★ 틀림'}")
    unc_diff = [r for r in rows if (r.get("rev") or {}).get("state") == "UNCHANGED" and (r["rev"].get("field_diffs") or [])]
    moved = [r for r in rows if (r.get("rev") or {}).get("state") == "UNCHANGED" and (r["rev"].get("moved_pt") or 0) > 10
             and not (r["rev"].get("field_diffs") or [])]
    note(f"   변경 없음인데 값이 다른 행 {len(unc_diff)} · 10pt 넘게 움직였는데 변경 없음 {len(moved)}")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1800, "height": 1000})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(f"http://127.0.0.1:{port}/#{JOB}")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.pages && S.pages.length > 0", timeout=120000); pg.wait_for_timeout(1500)
        if pg.evaluate("() => S.side"): pg.click("#rev-switch button.side"); pg.wait_for_timeout(800)
        head = pg.evaluate("() => (document.querySelector('#rev-summary') || document.querySelector('header.head') || document.body).innerText")
        ok1 = f"수정 {counts.get('MODIFIED', 0)}" in head
        note(f"① 머리줄에 '수정 {counts.get('MODIFIED', 0)}' — {'맞음' if ok1 else '★ 없음'}")
        # 필터
        pg.evaluate("() => { const w = document.querySelector('#only-changed-wrap'); if (w) w.classList.remove('hidden'); }")
        opt = pg.evaluate("() => Array.from(document.querySelectorAll('#rev-filter option')).map(o => o.textContent)")
        note(f"   필터 선택지 {opt}")
        pg.select_option("#rev-filter", "MODIFIED"); pg.wait_for_timeout(1200)
        n = pg.evaluate("() => document.querySelectorAll('#grid tbody tr').length")
        cells = pg.evaluate("() => Array.from(document.querySelectorAll('#grid tbody tr td.col-rev_state, #grid tbody tr td[data-col=rev_state]')).map(t => t.textContent.trim())")
        note(f"② '수정만 (태그 바뀜)' 필터 → 행 {n} (서버 {len(mods)}) · 개정 열 {sorted(set(cells))} — {'맞음' if n == len(mods) else '★ 틀림'}")
        pg.screenshot(path=str(OUT / "1_수정만_필터.png"))
        # 수정 행 하나 골라 근거 패널
        first = pg.evaluate("() => { const tr = document.querySelector('#grid tbody tr'); return tr ? tr.dataset.key : null; }")
        pg.click("#grid tbody tr:first-child td:nth-child(4)")
        # 다른 장의 행이면 장을 바꾼 뒤 근거 패널이 선다 (`S.pending`) — 그때까지 기다린다
        pg.wait_for_function("(k) => S.sel === k && !S.pending && document.querySelector('#evidence').innerText.indexOf('행을 클릭하면') < 0",
                             arg=first, timeout=30000); pg.wait_for_timeout(500)
        ev = pg.evaluate("() => (document.querySelector('.evidence') || {}).innerText || ''")
        ok3 = "바뀐 태그" in ev and "→" in ev
        line = next((l for l in ev.split("\n") if "바뀐 태그" in l), "")
        note(f"③ 수정 행 {first} 근거 패널 — {line!r} — {'맞음' if ok3 else '★ 없음'}")
        tip = pg.evaluate("() => { const t = document.querySelector('#ov text.revtag.rev-modified title'); return t ? t.textContent : ''; }")
        note(f"   도면 위 MOD 툴팁 — {tip!r}")
        pg.screenshot(path=str(OUT / "2_수정행_근거.png"))
        # 변경 없음인데 값이 다른 행
        pg.select_option("#rev-filter", ""); pg.wait_for_timeout(600)
        if unc_diff:
            r = unc_diff[0]
            pg.select_option("#page-select", str(r["page_no"])); pg.wait_for_timeout(1500)
            pg.evaluate("(k) => { const tr = document.querySelector(`#grid tbody tr[data-key=\"${k}\"]`); if (tr) tr.scrollIntoView(); }", r["key"])
            pg.click(f'#grid tbody tr[data-key="{r["key"]}"] td:nth-child(4)')
            pg.wait_for_function("(k) => S.sel === k && !S.pending && document.querySelector('#evidence').innerText.indexOf('행을 클릭하면') < 0",
                                 arg=r["key"], timeout=30000); pg.wait_for_timeout(500)
            ev = pg.evaluate("() => (document.querySelector('.evidence') || {}).innerText || ''")
            ok4 = "값이 다른 칸 (개정 판정에는 쓰지 않음)" in ev and "변경 없음" in ev
            line = next((l for l in ev.split("\n") if "값이 다른 칸" in l), "")
            note(f"④ 변경 없음 행 {r['key']} (field_diffs {[c['field'] for c in r['rev']['field_diffs']]}) 근거 패널 — {line[:120]!r} — {'맞음' if ok4 else '★ 없음'}")
            badge = pg.evaluate("(k) => { const tr = document.querySelector(`#grid tbody tr[data-key=\"${k}\"]`); const td = tr && (tr.querySelector('td[data-col=rev_state]') || tr.querySelector('td.col-rev_state')); return td ? td.textContent.trim() : null; }", r["key"])
            note(f"   그 행의 개정 열 — {badge!r} (수정이 아니어야 함) — {'맞음' if badge in (None, '', '변경 없음') else '★ 틀림'}")
            pg.screenshot(path=str(OUT / "3_변경없음_값차이.png"))
        if moved:
            r = moved[0]
            note(f"⑤ 자리만 {r['rev']['moved_pt']}pt 움직인 행 {r['key']} — 상태 {r['rev']['state']} — {'맞음' if r['rev']['state'] == 'UNCHANGED' else '★ 틀림'}")
        # 나란히 변경 목록
        tgt = mods[0]["page_no"] if mods else None
        if tgt:
            pg.select_option("#page-select", str(tgt)); pg.wait_for_timeout(1200)
            if not pg.evaluate("() => S.side"): pg.click("#rev-switch button.side")
            pg.wait_for_function("() => S.side && document.querySelector('#cmp-changes') && document.querySelector('#cmp-changes').innerText.length > 0", timeout=60000)
            pg.wait_for_timeout(1000)
            items = pg.evaluate("() => Array.from(document.querySelectorAll('#cmp-changes button.cmp-ch.mod')).map(b => b.innerText.replace(/\\s+/g, ' '))")
            ok6 = items and all("태그" in t and "→" in t for t in items)
            note(f"⑥ 나란히 변경 목록의 수정 항목 {len(items)} — {items[:3]} — {'맞음' if ok6 else '★ 틀림'}")
            pg.screenshot(path=str(OUT / "4_나란히_수정항목.png"))
        note(f"⑦ 페이지 오류 {len(errs)}" + (f" — {errs[:3]}" if errs else ""))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=30)
(OUT / "README.md").write_text("# hotfix43 태그만 수정 — 화면 자기검증\n\n" + "\n".join(f"- {x}" for x in FOUND) + "\n", encoding="utf-8")
