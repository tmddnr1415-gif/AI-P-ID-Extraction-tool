"""hotfix58 — 첫 화면의 '분석 중 현황' 을 띄워서 눌러 확인한다 (실 DB 를 안 연다).

    PID_DATA_DIR=<사본> uvicorn app.main:app --port 8766 &   python3 -m http.server 8767 -d <S> &
    python3 spike/ui_audit_running.py <S> <작은 PDF> <큰 PDF>

① 끝난 분석이 없을 때 — 막대는 '알 수 없음' 무늬, 남은 시간은 "아직 예상할 수 없습니다".
② 작은 PDF 가 끝나 장당 시간이 서면 — 큰 PDF 는 % · 남은 시간 · 근거, 셋째는 "앞에 1건".
③ 대시보드 흉내 페이지에서 다른 메뉴 → P&ID 메뉴 = 첫 화면 (진행 화면으로 끌고 가지 않는다).
④ 분석 중인 행을 누르면 진행 화면 (같은 % · 남은 시간) → "첫 화면으로 — 분석은 계속됩니다".
⑤ 같은 분석의 두 시점 캡처가 바이트로 다르다 (막대가 움직인다).
"""
import hashlib
import json
import sys
import time
import urllib.request
import uuid

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8766"
S, SMALL, BIG = sys.argv[1:4]
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
HOST = """<html><head><meta charset=utf-8></head><body style='margin:0;font-family:sans-serif'><div id=menu style='padding:6px;background:#1e2a4a'>
<button id=other>주간업무 (다른 메뉴)</button> <button id=pid>P&ID 분석</button></div>
<div id=content style='height:1000px'></div>
<script>function show(){document.getElementById('content').innerHTML='<iframe id=f style="width:100%;height:100%;border:0" src="SRC"></iframe>'}
document.getElementById('other').onclick=()=>{document.getElementById('content').innerHTML='<p style="padding:20px">주간업무</p>'};
document.getElementById('pid').onclick=show; show();</script></body></html>"""


def upload(path, name):
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"{name}\"\r\n"
            "Content-Type: application/pdf\r\n\r\n").encode() + open(path, "rb").read() + f"\r\n--{b}--\r\n".encode()
    r = urllib.request.Request(BASE + "/jobs", data=body,
                               headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(r, timeout=120))["job_id"]


def running():
    return json.load(urllib.request.urlopen(BASE + "/running"))


def status(job):
    return json.load(urllib.request.urlopen(f"{BASE}/jobs/{job}"))["status"]


out = {}
with sync_playwright() as p:
    br = p.chromium.launch(executable_path=CHROME)
    pg = br.new_page(viewport={"width": 1600, "height": 1060})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    open(f"{S}/host.html", "w").write(HOST.replace("SRC", BASE + "/?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"))

    def fr():
        return pg.query_selector("#f").content_frame()

    def screen(tag, wait=4):
        time.sleep(wait)
        f = fr()
        info = f.evaluate("""() => ({
            home: !document.querySelector('#drop').classList.contains('hidden'),
            progress: !document.querySelector('#progress').classList.contains('hidden'),
            live: [...document.querySelectorAll('#home-recent [data-live]')].map(e => e.innerText.replace(/\\s+/g,' ')),
            bars: [...document.querySelectorAll('#home-recent .runbar')].map(b => b.getAttribute('aria-valuenow')),
            eta: document.querySelector('#prog-eta').textContent,
            leave: !document.querySelector('#prog-leave').classList.contains('hidden'),
            url: location.href})""")
        card = f.query_selector(".recent-card")
        if info["home"] and card:
            card.scroll_into_view_if_needed()
            card.screenshot(path=f"{S}/{tag}_card.png")
        pg.screenshot(path=f"{S}/{tag}.png")
        out[tag] = info
        print(tag, json.dumps(info, ensure_ascii=False))
        return info

    pg.goto("http://127.0.0.1:8767/host.html")
    small = upload(SMALL, "TC2_12.pdf")
    time.sleep(3)
    fr().evaluate("() => toFirstScreen()")          # 업로드는 API 로 했으니 첫 화면을 다시 그린다
    screen("1_no_history", 6)
    for _ in range(90):
        if status(small) not in ("running", "queued"):
            break
        time.sleep(5)
    print("small", status(small), running()["pace"])
    big = upload(BIG, "TC2_260821.pdf")
    third = upload(SMALL, "TC2_12_again.pdf")
    pg.click("#other"); time.sleep(2); pg.click("#pid")
    a = screen("2_estimate", 25)
    b = screen("3_estimate_later", 20)
    h = [hashlib.md5(open(f"{S}/{t}_card.png", "rb").read()).hexdigest() for t in ("2_estimate", "3_estimate_later")]
    out["card_md5_differs"] = h[0] != h[1]
    # 진행 화면으로 들어갔다가 나온다
    fr().click(f'#home-recent a[data-live="{big}"]')
    screen("4_progress_screen", 6)
    fr().click("#prog-leave")
    screen("5_left_to_home", 4)
    # 진행 화면에 있다가 다른 메뉴 → 다시 P&ID 메뉴 = 첫 화면
    fr().click(f'#home-recent a[data-live="{big}"]'); time.sleep(3)
    pg.click("#other"); time.sleep(3); pg.click("#pid")
    screen("6_menu_again_is_home", 6)
    out["status_after"] = {"big": status(big), "third": status(third)}
    out["errors"] = errs
    br.close()
json.dump(out, open(f"{S}/result.json", "w"), ensure_ascii=False, indent=2)
print("errors", errs)
