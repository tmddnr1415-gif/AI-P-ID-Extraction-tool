"""hotfix47 — 같은 도면에 새 태그와 사라진 태그가 함께 남은 것이 화면에서 **전부 MOD** 인지 띄워서 확인.

    python3 spike/ui_audit_hotfix47.py <data_dir> <job_B> <out_dir> [page_mod] [page_add]

① 머리줄 '수정 N (+ 이전 태그 M)' = 서버 counts ② '수정만' 필터 → 행 수 = MODIFIED + MODIFIED_BEFORE ·
개정 열에 '수정 (이전 태그)' ③ 이전 태그 행의 근거 패널 '수정 (이전 태그)' · 삭제 확정 버튼은 남는다
④ 나란히(p41): 오른쪽 도면에 ✕(delmark) 0 · MOD 표식(modmark) = 그 장 이전 태그 수 · 변경 목록 글자
⑤ p89: 같은 태그 PI 는 링 없음(변경 없음) · 20PGD46/56 여섯만 ADD ⑥ 페이지 오류 0.
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
PAGE_MOD = int(sys.argv[4]) if len(sys.argv) > 4 else 41
PAGE_ADD = int(sys.argv[5]) if len(sys.argv) > 5 else 89
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
    pages = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/jobs/{JOB}/pages", timeout=120).read())
    dwg_of = {p["page_no"]: p.get("drawing_no") for p in pages}
    before = [d for d in rev["deleted_candidates"] if d.get("state") == "MODIFIED" and not d.get("confirmed")]
    dels = [d for d in rev["deleted_candidates"] if d.get("state") != "MODIFIED" and not d.get("confirmed")]
    mod_rows = [r for r in rows if (r.get("rev") or {}).get("state") == "MODIFIED"]
    note(f"서버 — 수정 행 {len(mod_rows)} (TYPE 짝 {sum(1 for r in mod_rows if r['rev'].get('basis') == 'TYPE')} · 짝 없음 {sum(1 for r in mod_rows if r['rev'].get('basis') == 'AMBIGUOUS')}) · 이전 태그 {len(before)} · 삭제 후보 {len(dels)}")
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
        head = pg.evaluate("() => document.querySelector('#rev-label').innerText")
        want = f"수정 {counts.get('MODIFIED', 0)} (+ 이전 태그 {counts.get('MODIFIED_BEFORE', 0)})"
        note(f"① 머리줄 — {head!r} · '{want}' — {'맞음' if want in head else '★ 없음'}")
        # ② 필터
        pg.evaluate("() => { const w = document.querySelector('#only-changed-wrap'); if (w) w.classList.remove('hidden'); }")
        pg.select_option("#rev-filter", "MODIFIED"); pg.wait_for_timeout(1200)
        n = pg.evaluate("() => document.querySelectorAll('#grid tbody tr').length")
        cells = pg.evaluate("() => Array.from(document.querySelectorAll('#grid tbody tr td[data-col=rev_state]')).map(t => t.textContent.trim())")
        from collections import Counter
        cnt = Counter(cells)
        exp = counts.get("MODIFIED", 0) + counts.get("MODIFIED_BEFORE", 0)
        note(f"② '수정만' 필터 → 행 {n} (서버 수정 {counts.get('MODIFIED', 0)} + 이전 태그 {counts.get('MODIFIED_BEFORE', 0)} = {exp}) · 개정 열 {dict(cnt)} — {'맞음' if n == exp and cnt.get('수정 (이전 태그)') == counts.get('MODIFIED_BEFORE', 0) else '★ 틀림'}")
        addf = pg.evaluate("() => { const s = document.querySelector('#rev-filter'); s.value = 'ADDED'; s.dispatchEvent(new Event('change')); return 0; }"); pg.wait_for_timeout(800)
        n_add = pg.evaluate("() => document.querySelectorAll('#grid tbody tr').length")
        note(f"   '추가만' 필터 → 행 {n_add} (서버 {counts.get('ADDED', 0)}) — {'맞음' if n_add == counts.get('ADDED', 0) else '★ 틀림'}")
        pg.select_option("#rev-filter", "DELETED"); pg.wait_for_timeout(800)
        n_del = pg.evaluate("() => document.querySelectorAll('#grid tbody tr').length")
        note(f"   '삭제만' 필터 → 행 {n_del} (서버 삭제 후보 {counts.get('DELETED_CANDIDATE', 0)} — 이전 태그는 여기 안 든다) — {'맞음' if n_del == counts.get('DELETED_CANDIDATE', 0) else '★ 틀림'}")
        pg.select_option("#rev-filter", "MODIFIED"); pg.wait_for_timeout(1000)
        pg.screenshot(path=str(OUT / "1_수정만_필터.png"))
        # ③ 이전 태그 행 근거 패널
        if before:
            d = before[0]
            key = f"del:{d['id']}"
            pg.evaluate("(k) => { const tr = document.querySelector(`#grid tbody tr[data-key=\"${k}\"]`); if (tr) tr.scrollIntoView(); }", key)
            pg.click(f'#grid tbody tr[data-key="{key}"] td:nth-child(4)')
            pg.wait_for_function("(k) => S.sel === k && !S.pending", arg=key, timeout=30000); pg.wait_for_timeout(600)
            ev = pg.evaluate("() => (document.querySelector('#evidence') || {}).innerText || ''")
            btn = pg.evaluate("(k) => { const b = document.querySelector(`#grid tbody tr[data-key=\"${k}\"] button.del-confirm`); return b ? b.textContent : null; }", key)
            remark = pg.evaluate("(k) => { const tr = document.querySelector(`#grid tbody tr[data-key=\"${k}\"]`); const td = tr && tr.querySelector('td[data-col=remark]'); return td ? td.textContent.trim() : ''; }", key)
            ok3 = "수정 (이전 태그)" in ev and "같은 도면의 새 태그" in ev and "삭제 후보" not in ev.split("\n")[0]
            note(f"③ 이전 태그 행 {key} ({d['type']} {d['tag_no']}) 근거 패널 머리 {ev.split(chr(10))[0]!r} · 버튼 {btn!r} · Remark {remark[:70]!r} — {'맞음' if ok3 and btn else '★ 틀림'}")
            pg.screenshot(path=str(OUT / "2_이전태그_근거.png"))
        # ④ 나란히 — p41
        pg.select_option("#rev-filter", ""); pg.wait_for_timeout(500)
        pg.select_option("#page-select", str(PAGE_MOD)); pg.wait_for_timeout(1500)
        if not pg.evaluate("() => S.side"): pg.click("#rev-switch button.side")
        pg.wait_for_function("() => S.side && document.querySelector('#cmp-sheet') && document.querySelector('#cmp-sheet').complete && document.querySelector('#cmp-sheet').naturalWidth > 0 && document.querySelectorAll('#cmp-ov rect').length > 0", timeout=90000)
        pg.wait_for_timeout(1500)
        dwg = dwg_of.get(PAGE_MOD)
        exp_before = sum(1 for d in before if d["drawing_no"] == dwg)
        exp_del = sum(1 for d in dels if d["drawing_no"] == dwg)
        st = pg.evaluate("""() => ({dels: document.querySelectorAll('#cmp-ov circle.delmark').length, mods: document.querySelectorAll('#cmp-ov circle.modmark').length,
            modtags: Array.from(document.querySelectorAll('#cmp-ov text.cmp-modtag')).filter(t => t.textContent === 'MOD').length,
            deltags: document.querySelectorAll('#cmp-ov text.deltag').length,
            head: document.querySelector('#cmp-changes .cmp-ch-head').innerText.replace(/\\s+/g, ' '),
            items: Array.from(document.querySelectorAll('#cmp-changes button.cmp-ch')).map(b => b.className.replace('cmp-ch ', '') + ':' + b.innerText.replace(/\\s+/g, ' ')),
            leftAdd: document.querySelectorAll('#ov text.revtag.rev-added').length, leftMod: document.querySelectorAll('#ov text.revtag.rev-modified').length})""")
        ok4 = st["dels"] == exp_del and st["mods"] == exp_before and st["leftAdd"] == 0 and all(not i.startswith("add") and not i.startswith("del") for i in st["items"])
        note(f"④ p{PAGE_MOD} {dwg} 나란히 — 오른쪽 ✕ {st['dels']} (삭제 후보 {exp_del}) · MOD 표식 {st['mods']} (이전 태그 {exp_before}) · DEL 글자 {st['deltags']} · 왼쪽 ADD {st['leftAdd']} · MOD {st['leftMod']} · 머리 {st['head']!r} — {'맞음' if ok4 else '★ 틀림'}")
        note(f"   변경 목록 앞 셋 — {st['items'][:3]}")
        pg.screenshot(path=str(OUT / ("3_나란히_p%d.png" % PAGE_MOD)))
        box = pg.evaluate("""() => { const c = document.querySelector('#cmp-ov circle.modmark'); if (!c) return null; const r = c.getBoundingClientRect(); return {x: Math.max(0, r.x - 120), y: Math.max(0, r.y - 80), w: 300, h: 180}; }""")
        if box: pg.screenshot(path=str(OUT / "3b_MOD표식_크롭.png"), clip={"x": box["x"], "y": box["y"], "width": box["w"], "height": box["h"]})
        # ⑤ p89
        pg.select_option("#page-select", str(PAGE_ADD))
        pg.wait_for_function("(n) => S.page && S.page.page_no === n && document.querySelectorAll('#ov rect.det').length > 0", arg=PAGE_ADD, timeout=60000); pg.wait_for_timeout(2500)
        dwg2 = dwg_of.get(PAGE_ADD)
        srv_add = [r for r in rows if r["page_no"] == PAGE_ADD and (r.get("rev") or {}).get("state") == "ADDED"]
        srv_unch = [r for r in rows if r["page_no"] == PAGE_ADD and (r.get("rev") or {}).get("state") == "UNCHANGED" and (r["rev"].get("moved_pt") or 0) > 100]
        st2 = pg.evaluate("""() => ({add: Array.from(document.querySelectorAll('#ov text.revtag.rev-added')).map(t => t.dataset.key), mod: document.querySelectorAll('#ov text.revtag.rev-modified').length,
            cmpItems: Array.from(document.querySelectorAll('#cmp-changes button.cmp-ch')).map(b => b.innerText.replace(/\\s+/g, ' '))})""")
        ring_unch = [r["key"] for r in srv_unch if r["key"] in st2["add"]]
        note(f"⑤ p{PAGE_ADD} {dwg2} — ADD 라벨 {len(st2['add'])} (서버 추가 {len(srv_add)}: {sorted(r['values'].get('tag_no') for r in srv_add)}) · MOD {st2['mod']} · 100pt 넘게 움직인 변경 없음 행 {len(srv_unch)} 중 링 달린 것 {len(ring_unch)} — {'맞음' if len(st2['add']) == len(srv_add) and not ring_unch and st2['mod'] == 0 else '★ 틀림'}")
        pg.screenshot(path=str(OUT / ("4_p%d_나란히.png" % PAGE_ADD)))
        note(f"⑥ 페이지 오류 {len(errs)}" + (f" — {errs[:3]}" if errs else ""))
        br.close()
finally:
    srv.terminate(); srv.wait(timeout=30)
(OUT / "README.md").write_text("# hotfix47 짝 없는 태그는 전부 MOD — 화면 자기검증\n\n" + "\n".join(f"- {x}" for x in FOUND) + "\n", encoding="utf-8")
