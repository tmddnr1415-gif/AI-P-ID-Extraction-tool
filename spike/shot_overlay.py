"""32회차 — 네 프로젝트의 **도면 위 표시**를 같은 조건으로 찍는다.

    python3 spike/shot_overlay.py <프로젝트명> <결과.json> <내보낼 폴더>

장을 **고르지 않는다** — 행이 있는 장을 장번호 순으로 세우고 **균등 간격**으로
여덟을 뽑는다 (여덟보다 적으면 있는 것 전부).  뽑힌 인덱스와 장 번호를 먼저
찍어 두므로 "잘 나온 장을 골랐다" 가 성립하지 않는다.

장마다 둘을 찍는다 — `p<장>_overlay.png` (도면 + 오버레이 + 범례 패널) ·
`p<장>_rows.png` (그 장의 행 그리드).  확대율은 **맞춤**으로 통일한다.

★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PDFS = {p["name"]: p["pdf"] for p in
        json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"


def free_port() -> int:
    s = socket.socket(); s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]; s.close()
    return p


def pick_pages(rows, want: int = 8) -> list[int]:
    """행이 있는 장 · 장번호 순 · **균등 간격**.  고르지 않는다."""
    pages = sorted({int(r["page_no"]) for r in rows})
    if len(pages) <= want:
        return pages
    step = (len(pages) - 1) / (want - 1)
    idx = sorted({round(i * step) for i in range(want)})
    return [pages[i] for i in idx]


def main() -> int:
    name, src, outdir = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    outdir.mkdir(parents=True, exist_ok=True)
    data = Path(tempfile.mkdtemp(prefix="shotov-"))
    os.environ["PID_DATA_DIR"] = str(data)
    from app import db

    blob = json.loads(src.read_text())
    result = blob.get("result", blob)
    pages = pick_pages(result["rows"])
    print(f"[{name}] 행 있는 장 {len({int(r['page_no']) for r in result['rows']})}개 "
          f"→ 뽑은 장 {pages}")

    con = db.connect(data / "app.db")
    job = "shotov" + name.replace(" ", "").lower()[:6].ljust(6, "0")
    pdf = ROOT / PDFS[name]
    sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else ""
    con.execute(
        "INSERT INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at, status,"
        " progress, message, fingerprint, project, revision)"
        " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
        (job, pdf.name, sha, str(pdf), time.time(),
         result.get("fingerprint", ""), name, "A"))
    con.commit()
    db.store_result(con, job, result)
    con.commit(); con.close()

    port = free_port()
    env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
    srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app",
                            "--host", "127.0.0.1", "--port", str(port)],
                           cwd=str(ROOT), env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    facts = {"project": name, "pages": pages, "shots": []}
    try:
        import urllib.request
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/home", timeout=2)
                break
            except Exception:
                time.sleep(1)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            br = pw.chromium.launch(
                executable_path=CHROME if Path(CHROME).exists() else None)
            pg = br.new_page(viewport={"width": 1700, "height": 1050})
            pg.goto(f"http://127.0.0.1:{port}/")
            pg.wait_for_timeout(2500)
            row = (pg.query_selector("a.revrow")
                   or pg.query_selector(f"text={pdf.name}"))
            row.click()
            pg.wait_for_timeout(7000)
            for no in pages:
                pg.select_option("#page-select", str(no))
                pg.wait_for_timeout(2500)
                pg.click("button[data-z='0']")          # 맞춤 — 넷을 같은 조건으로
                pg.wait_for_timeout(1200)
                left = pg.query_selector("#left")
                left.screenshot(path=str(outdir / f"p{no}_overlay.png"))
                # 그 장의 행만 — 검색 상자로 도면번호를 건다 (사람이 하는 그대로)
                dwg = pg.eval_on_selector(
                    "#page-select", "el => el.options[el.selectedIndex].textContent")
                code = (dwg or "").split(None, 1)[-1].strip()
                pg.fill("#filter", code)
                pg.wait_for_timeout(1500)
                right = pg.query_selector("#right") or pg.query_selector("#gridwrap")
                right.screenshot(path=str(outdir / f"p{no}_rows.png"))
                # SCOPE · TAG NO. · DESCRIPTION · 등급 · REMARK 는 오른쪽에 있다 —
                # **그 열의 자리를 읽어** 가로 스크롤을 옮긴다 (§8: 어림해 자르지 않는다)
                pg.evaluate("""() => {
                  const g = document.querySelector('#gridwrap');
                  const th = [...document.querySelectorAll('#grid thead th')]
                      .find(e => /TAG/i.test(e.textContent));
                  if (g && th) g.scrollLeft = th.offsetLeft - 8;
                  else if (g) g.scrollLeft = g.scrollWidth;
                }""")
                pg.wait_for_timeout(700)
                right.screenshot(path=str(outdir / f"p{no}_rows_right.png"))
                pg.evaluate("() => { const g = document.querySelector('#gridwrap');"
                            " if (g) g.scrollLeft = 0; }")
                shown = pg.eval_on_selector_all(
                    "#grid tbody tr", "els => els.length")
                marks = pg.eval_on_selector_all("#ov *", "els => els.length")
                legend = pg.eval_on_selector_all(
                    "#ovl-items .ovl-row",
                    "els => els.map(e => e.textContent.trim().replace(/\\s+/g,' '))")
                facts["shots"].append({"page": no, "drawing": code,
                                       "grid_rows": shown, "svg_nodes": marks,
                                       "legend": legend})
                print(f"  p{no} {code} · 그리드 {shown}행 · SVG {marks}노드 · {legend}")
                # ★ 첫 장에서는 **확대해서** 한 번 더 본다 — 맞춤 배율에서는
                # 상자가 심볼을 덮는지 눈으로 가릴 수 없다 (좌표가 밀렸는지가
                # 이 회차의 물음이고, A3·/Rotate 270 이 그 시험대다).
                if no == pages[0]:
                    tr = pg.query_selector("#grid tbody tr")
                    if tr:
                        tr.click(); pg.wait_for_timeout(800)
                        for _ in range(3):
                            pg.click("button[data-z='1']"); pg.wait_for_timeout(500)
                        pg.query_selector("#stage").screenshot(
                            path=str(outdir / f"p{no}_zoom.png"))
                        pg.click("button[data-z='0']"); pg.wait_for_timeout(600)
                pg.fill("#filter", "")
                pg.wait_for_timeout(400)
            br.close()
    finally:
        srv.terminate()
    (outdir / "facts.json").write_text(
        json.dumps(facts, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
