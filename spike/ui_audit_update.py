"""hotfix34 — 첫 화면 오른쪽 아래의 업데이트 딱지를 **실제로 띄워서** 찍는다.

    python3 spike/ui_audit_update.py out/hotfix34/ui

딱지가 있을 때(이번 꾸러미)와 없을 때("기록 없음") 두 상태를 같은 서버로 찍는다 —
`app/_update.json` 을 잠시 옮겼다가 되돌린다.  ★ 실 DB 를 열지 않는다 (17회차 격리).
"""
from __future__ import annotations
import json, os, shutil, socket, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "out/hotfix34/ui"); OUT.mkdir(parents=True, exist_ok=True)
STAMP = ROOT / "app" / "_update.json"
FOUND: list[str] = []


def note(s):
    print(s, flush=True); FOUND.append(s)


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def shoot(pg, port, tag):
    pg.goto(f"http://127.0.0.1:{port}/"); pg.wait_for_timeout(2500)
    txt = pg.inner_text("#build-text"); title = pg.get_attribute("#build-text", "title")
    box = pg.query_selector("#build").bounding_box(); vw = pg.viewport_size
    right = vw["width"] - (box["x"] + box["width"]); bottom = vw["height"] - (box["y"] + box["height"])
    note(f"{tag}: 바닥줄 {txt!r} · 오른쪽 여백 {right:.0f}px · 아래 여백 {bottom:.0f}px")
    note(f"{tag}: 툴팁 {title!r}")
    pg.screenshot(path=str(OUT / f"{tag}_첫화면.png"))
    clip = {"x": max(0, box["x"] - 10), "y": max(0, box["y"] - 10), "width": box["width"] + 20, "height": box["height"] + 20}
    pg.screenshot(path=str(OUT / f"{tag}_바닥줄.png"), clip=clip)


data = Path(tempfile.mkdtemp(prefix="updui-")); os.environ["PID_DATA_DIR"] = str(data)
port = free_port()
env = dict(os.environ, PID_DATA_DIR=str(data), PYTHONPATH=str(ROOT))
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                        "--port", str(port)], cwd=str(ROOT), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
backup = None
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
        pg = br.new_page(viewport={"width": 1500, "height": 900})
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        v = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/version").read())
        note(f"/version.update = {v.get('update')}")
        if STAMP.exists():
            shoot(pg, port, "1_딱지있음")
            backup = STAMP.read_bytes(); STAMP.unlink()
            shoot(pg, port, "2_딱지없음")
        else:
            shoot(pg, port, "2_딱지없음")
        note("화면 오류 없음" if not errs else "★ 화면 오류: " + " | ".join(errs[:5]))
        br.close()
except Exception as exc:                                     # noqa: BLE001
    note(f"★ 중단: {type(exc).__name__}: {str(exc)[:300]}")
finally:
    if backup is not None:
        STAMP.write_bytes(backup)
    srv.terminate(); srv.wait(timeout=10)
(OUT / "README.md").write_text("# hotfix34 화면 자기검증 — 첫 화면 오른쪽 아래 업데이트 딱지\n\n"
                               + "\n".join("- " + x for x in FOUND) + "\n", encoding="utf-8")
print("\n=> " + str(OUT / "README.md"))
