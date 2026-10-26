import json, sys, time, urllib.request, uuid
from playwright.sync_api import sync_playwright
BASE = "http://127.0.0.1:8766"; S = sys.argv[1]; PDF = sys.argv[2]; phase = sys.argv[3]
def upload():
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"TC2.pdf\"\r\nContent-Type: application/pdf\r\n\r\n").encode() + open(PDF,'rb').read() + f"\r\n--{b}--\r\n".encode()
    r = urllib.request.Request(BASE + "/jobs", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.load(urllib.request.urlopen(r, timeout=60))["job_id"]
HOST = """<html><body style='margin:0'><div id=menu><button id=other>다른 메뉴</button><button id=pid>P&ID 분석</button></div><div id=content style='height:900px'></div>
<script>let first=true;function show(){const src=first?"SRC":"SRC2";first=false;document.getElementById('content').innerHTML='<iframe id=f style="width:100%;height:100%;border:0" src="'+src+'"></iframe>'}
document.getElementById('other').onclick=()=>{document.getElementById('content').innerHTML='<p>주간업무</p>'};
document.getElementById('pid').onclick=show; show();</script></body></html>"""
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
    ctx = br.new_context(viewport={"width": 1600, "height": 950})
    pg = ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    def frame():
        for _ in range(100):
            f = pg.frame_locator("#f")
            try:
                if f.locator("body").count(): return pg.frames[-1]
            except Exception: pass
            time.sleep(0.1)
    def state(tag):
        time.sleep(4)
        fr = pg.query_selector("#f").content_frame()
        info = fr.evaluate("""() => ({url: location.href,
            progress: !document.querySelector('#progress').classList.contains('hidden'),
            main: !document.querySelector('#main').classList.contains('hidden'),
            title: document.querySelector('#prog-title').textContent,
            msg: document.querySelector('#prog-msg').textContent,
            elapsed: document.querySelector('#prog-elapsed').textContent,
            now: document.querySelector('#prog-now').textContent,
            key: localStorage.getItem('pid.watching')})""")
        pg.screenshot(path=f"{S}/{tag}.png"); print(tag, json.dumps(info, ensure_ascii=False)); return info
    host = f"{S}/host.html"
    job = open(f"{S}/job.txt").read().strip()
    E = f"{BASE}/?embed=1&user=%ED%99%8D%EA%B8%B8%EB%8F%99"
    open(host, "w").write(HOST.replace("SRC2", E).replace("SRC", E + "#" + job))
    pg.goto("http://127.0.0.1:8767/host.html"); state("1_watching")
    time.sleep(15)
    pg.click("#other"); time.sleep(20); pg.screenshot(path=f"{S}/2_other_menu.png")
    pg.click("#pid"); a = state("3_back_running")
    pg.click("#other"); time.sleep(5); pg.click("#pid"); b = state("4_back_again")
    # 끝날 때까지 다른 메뉴에 있다가 돌아온다
    pg.click("#other")
    for _ in range(120):
        st = json.load(urllib.request.urlopen(f"{BASE}/jobs/{job}"))["status"]
        if st not in ("running", "queued"): break
        time.sleep(10)
    print("final status", st)
    pg.click("#pid"); c = state("5_back_after_done")
    time.sleep(6); c = state("6_results")
    pg.click("#other"); time.sleep(2); pg.click("#pid"); d = state("7_back_after_seen")
    print("errors", errs); br.close()
