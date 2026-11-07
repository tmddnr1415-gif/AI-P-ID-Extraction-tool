"""hotfix79 — 오버레이를 **고친 것만** 다시 그려도 전부 다시 그린 것과 같은 그림인지 띄워서 맞댄다.

    python3 spike/ui_audit_overlay_incr.py <data_dir 사본> <job> <out_dir>

★ 실 DB 를 열지 않는다 — 넘긴 데이터 폴더(사본)를 PID_DATA_DIR 로 가리킨다.

동작마다: (가) 화면이 한 그대로의 #ov 를 떠 두고 (나) `drawOverlay()` 로 전부 다시 그린 #ov 와 맞댄다.
맞대는 단위는 요소 하나 — 이름 · 속성(class 는 낱말 집합) · 글자.  순서도 본다 (상자는 면적 순으로
겹쳐 있어 순서가 클릭을 정한다).  단 수량 라벨(`g.qtytag`)끼리의 순서는 보지 않는다 — 모두 상자 위의
자기 층이고 서로 겹치지 않는다.
동작: 행 고르기 · 다른 행 · Shift 묶음 · 묶음 풀기 · 고르기 풀기 · SCOPE 고침 · Q'ty 고침 ·
묶음 SCOPE 일괄 · 위치 메모 다시 그리기 · 화살표 칸 이동(멈춘 뒤 행이 골라진다).
"""
from __future__ import annotations
import json, os, socket, subprocess, sys, time, urllib.request
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
data, JOB, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT), PID_PAGE_WARM="0", PID_RENDER_POOL="0")
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f"http://127.0.0.1:{port}"
FOUND, BAD = [], []
def note(x): print(x, flush=True); FOUND.append(x)
def check(ok, what):
    note(("  ✔ " if ok else "  ✘ ") + what)
    if not ok: BAD.append(what)

SNAP = """() => {
  const ov = document.querySelector('#ov');
  const walk = (n) => {
    if (n.nodeType === 3) return n.textContent.trim() ? ['#t', n.textContent] : null;
    if (n.nodeType !== 1) return null;
    const at = {};
    // 'pulse' 는 고른 순간 잠깐 붙는 깜박임이다 — 그림이 아니다
    for (const a of n.attributes) at[a.name] = a.name === 'class' ? a.value.split(/\\s+/).filter(c => c && c !== 'pulse').sort().join(' ') : a.value;
    // 깜박임의 지난 시간(animation-delay)은 그린 순간마다 다르다 — 그림이 아니다
    if (at.style) at.style = at.style.replace(/animation-delay:[^;]*;?/g, '').trim();
    return [n.nodeName, at, [...n.childNodes].map(walk).filter(Boolean)];
  };
  return [...ov.childNodes].map(walk).filter(Boolean);
}"""


def same(name):
    a = pg.evaluate(SNAP)
    pg.evaluate("() => drawOverlay()")
    b = pg.evaluate(SNAP)
    def split(lst):
        rest = [x for x in lst if not (x[0] == "g" and "qtytag" in x[1].get("class", ""))]
        q = sorted(json.dumps(x, sort_keys=True, ensure_ascii=False)
                   for x in lst if x[0] == "g" and "qtytag" in x[1].get("class", ""))
        return [json.dumps(x, sort_keys=True, ensure_ascii=False) for x in rest], q
    ra, qa = split(a); rb, qb = split(b)
    ok = ra == rb and qa == qb
    if not ok:
        diff = next((i for i, (x, y) in enumerate(zip(ra, rb)) if x != y), min(len(ra), len(rb)))
        (OUT / f"diff_{name}.txt").write_text(
            f"len {len(ra)} vs {len(rb)} · qty {len(qa)} vs {len(qb)}\nfirst diff at {diff}\n"
            f"INCR {ra[diff] if diff < len(ra) else None}\nFULL {rb[diff] if diff < len(rb) else None}\n", encoding="utf-8")
    check(ok, f"{name} — 고친 것만 다시 그린 그림 = 전부 다시 그린 그림 (요소 {len(a)})")


try:
    for _ in range(90):
        try: urllib.request.urlopen(base + "/version", timeout=2); break
        except Exception: time.sleep(1)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
        ctx = br.new_context(viewport={"width": 1920, "height": 1080})
        ctx.add_init_script("try{localStorage.setItem('pid.side.off','1');localStorage.removeItem('pid.split')}catch(e){}")
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("console", lambda m: errs.append("console:" + m.text) if m.type == "error" else None)
        pg.goto(f"{base}/?embed=1&user={quote('홍길동')}"); pg.wait_for_timeout(1500)
        pg.evaluate(f"open('{JOB}')")
        pg.wait_for_function("() => typeof S !== 'undefined' && S.job && !S.loading && S.vlist && S.vlist.length > 3", timeout=180000)
        pg.wait_for_timeout(2000)
        if pg.evaluate("() => !!S.side"):
            pg.evaluate("() => toggleSide(false)"); pg.wait_for_timeout(500)
        # 행이 가장 많은 장으로 (태그 버블 고리 · 수량 라벨이 있는 행이 많다)
        pno = pg.evaluate("""() => { const c = {}; for (const r of S.rows) if (!r.removed && !r.deleted) c[r.page_no] = (c[r.page_no] || 0) + 1;
            return +Object.entries(c).sort((a, b) => b[1] - a[1])[0][0]; }""")
        pg.evaluate(f"() => showPage(S.pages.find(p => p.page_no === {pno}))")
        pg.wait_for_function(f"() => document.querySelector('#ov').dataset.page === '{pno}' && document.querySelectorAll('#ov rect.det').length > 5", timeout=60000)
        pg.wait_for_timeout(1200)
        keys = pg.evaluate(f"""() => S.rows.filter(r => r.page_no === {pno} && !r.removed && !r.deleted && r.rect && r.rect.length === 4)
            .sort((a, b) => ((b.evidence || {{}}).tag_rect ? 1 : 0) - ((a.evidence || {{}}).tag_rect ? 1 : 0)).map(r => r.key).slice(0, 8)""")
        nbox = pg.evaluate("() => document.querySelectorAll('#ov rect.det').length")
        note(f"장 p{pno} · 상자 {nbox} · 고를 행 {len(keys)}")
        box = lambda k: f'#ov rect.det[data-key="{k}"]'
        click = lambda k, shift=False: pg.evaluate(
            """([k, sh]) => document.querySelector(`#ov rect.det[data-key="${k}"]`).dispatchEvent(new MouseEvent('click', {bubbles: true, shiftKey: sh}))""", [k, shift])

        note("① 고르기")
        click(keys[0]); pg.wait_for_timeout(700); pg.evaluate("() => closeScopePop && closeScopePop()")
        check(pg.evaluate(f"() => S.sel === '{keys[0]}'"), "상자 누름 → 행 골라짐")
        same("select_a")
        click(keys[1]); pg.wait_for_timeout(700); pg.evaluate("() => closeScopePop && closeScopePop()")
        same("select_b")
        note("② Shift 묶음")
        click(keys[2], True); click(keys[3], True); pg.wait_for_timeout(400)
        nm = pg.evaluate("() => S.multi.size")
        check(nm == 3, f"묶음 {nm}")
        same("multi")
        pg.evaluate("() => clearMulti()"); pg.wait_for_timeout(300)
        same("clear_multi")
        pg.evaluate("() => deselect()"); pg.wait_for_timeout(300)
        same("deselect")
        note("③ 고침 — SCOPE · Q'ty · 묶음 SCOPE")
        click(keys[4]); pg.wait_for_timeout(700); pg.evaluate("() => closeScopePop && closeScopePop()")
        pg.evaluate(f"async () => {{ const r = S.rowByKey['{keys[4]}']; await saveField(r, 'scope', String(cellValue(r, 'scope')) === 'SCT' ? 'VENDOR' : 'SCT'); }}")
        pg.wait_for_timeout(500)
        same("edit_scope")
        pg.evaluate(f"async () => {{ await saveField(S.rowByKey['{keys[4]}'], 'qty', '7'); }}"); pg.wait_for_timeout(500)
        lab = pg.evaluate(f"""() => (document.querySelector('#ov g.qtytag[data-key="{keys[4]}"] text') || {{}}).textContent || ''""")
        uq = pg.evaluate("k => JSON.stringify((S.rowByKey[k].user || {}).qty)", keys[4])
        check(lab.startswith("x7"), f"Q'ty 고침 → 라벨 x7 ({lab!r} · 사람 값 {uq})")
        same("edit_qty")
        click(keys[5], True); click(keys[6], True); pg.wait_for_timeout(300)
        pg.evaluate("async () => { await applyScopeToMulti('VENDOR'); }"); pg.wait_for_timeout(800)
        same("bulk_scope")
        pg.evaluate("() => clearMulti()"); pg.wait_for_timeout(300)
        note("④ 위치 메모만 다시 그리기")
        pg.evaluate("() => redrawPins()"); pg.wait_for_timeout(200)
        same("pins")
        note("⑤ 화살표 칸 이동")
        k0 = keys[0]
        pg.evaluate(f"() => revealRow('{k0}').scrollIntoView({{block:'center'}})")
        pg.click(f'#body tr[data-key="{k0}"] td[data-col="line_no"]'); pg.wait_for_timeout(500)
        for _ in range(6): pg.keyboard.press("ArrowDown")
        moved = pg.evaluate("() => S.cell && S.cell.key")
        check(pg.evaluate("() => document.querySelector('#body tr.sel') && document.querySelector('#body tr.sel').dataset.key") == moved,
              "누르는 동안 목록의 행 표시는 바로 따라온다")
        pg.wait_for_timeout(1500)
        check(pg.evaluate("() => S.sel") == moved, f"멈춘 뒤 그 행이 골라진다 ({moved})")
        same("arrows")
        pg.screenshot(path=str(OUT / "overlay_incr.png"))
        check(not errs, f"페이지 오류 {len(errs)} {errs[:3]}")
        br.close()
finally:
    srv.terminate()
    try: srv.wait(10)
    except Exception: srv.kill()
(OUT / "audit.txt").write_text("\n".join(FOUND) + f"\n\n결함 {len(BAD)}\n", encoding="utf-8")
print("BAD", len(BAD))
sys.exit(1 if BAD else 0)
