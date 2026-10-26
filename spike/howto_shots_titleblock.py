"""사용자 안내용 캡처 — 실패 화면 → 칸 지정 패널 → 끄는 중 → 미리보기 → 저장.  번호 말풍선을 얹는다."""
import json, os, socket, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path("/home/user/AI-P-ID-Extraction-tool"); sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
from test_hotfix28_new_form import _new_form, A1
data = Path(tempfile.mkdtemp(prefix="howto-")); os.environ["PID_DATA_DIR"] = str(data)
pdf = _new_form(data / "QFE_PID.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
from app import revisions; revisions.create_project(data, "QFE")
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
                       cwd=str(ROOT), env=dict(os.environ, PYTHONPATH=str(ROOT)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/nanum/NanumSquareRoundB.ttf", 22)

def callout(img, xy, n, text, dx=40, dy=-60):
    d = ImageDraw.Draw(img)
    x, y = xy; tx, ty = x + dx, y + dy
    d.line([(x, y), (tx, ty)], fill=(220, 40, 40), width=3)
    d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(220, 40, 40))
    w = d.textlength(text, font=FONT) + 46
    d.rounded_rectangle([tx, ty - 18, tx + w, ty + 18], radius=10, fill=(255, 245, 235), outline=(220, 40, 40), width=2)
    d.ellipse([tx + 6, ty - 13, tx + 32, ty + 13], fill=(220, 40, 40))
    d.text((tx + 19, ty), str(n), font=FONT, fill="white", anchor="mm")
    d.text((tx + 40, ty), text, font=FONT, fill=(60, 30, 20), anchor="lm")

try:
    base = f"http://127.0.0.1:{port}"
    for _ in range(90):
        try: urllib.request.urlopen(base + "/home", timeout=2); break
        except Exception: time.sleep(1)
    b = "----howto"; body = b""
    for k, v in (("project", "QFE"), ("compared_with", ""), ("input_kind", "PDF")):
        body += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
    body += (f"--{b}\r\nContent-Disposition: form-data; name=\"pdf\"; filename=\"{pdf.name}\"\r\nContent-Type: application/pdf\r\n\r\n").encode() + pdf.read_bytes() + f"\r\n--{b}--\r\n".encode()
    job = json.loads(urllib.request.urlopen(urllib.request.Request(base + "/jobs", data=body, method="POST", headers={"Content-Type": f"multipart/form-data; boundary={b}"}), timeout=30).read())["job_id"]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        exe = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
        br = pw.chromium.launch(executable_path=exe if Path(exe).exists() else None)
        pg = br.new_page(viewport={"width": 1366, "height": 1000})
        pg.goto(f"{base}/#{job}")
        pg.wait_for_function("() => document.querySelector('#prog-title') && document.querySelector('#prog-title').textContent === '분석 실패'", timeout=120000)
        pg.wait_for_timeout(500)
        # ① 실패 화면 — 버튼
        r = pg.evaluate("() => { const b = document.querySelector('#prog-tbfix').getBoundingClientRect(); return [b.left, b.top, b.width, b.height]; }")
        pg.screenshot(path=str(OUT / "_1.png"))
        im = Image.open(OUT / "_1.png"); callout(im, (r[0] + r[2] / 2, r[1] + r[3] / 2), 1, "분석 실패 화면에서 [타이틀블록 칸 지정] 을 누른다", dx=60, dy=70); im.save(OUT / "1_실패화면_버튼.png")
        pg.click("#prog-tbfix")
        pg.wait_for_function("() => { const i = document.querySelector('#tbfix-img'); return i && i.complete && i.naturalWidth > 0 && TB.state; }", timeout=60000)
        pg.wait_for_timeout(300)
        pg.evaluate("() => document.querySelector('#tbfix').scrollIntoView({block: 'start'})")
        pg.evaluate("() => { const s = document.querySelector('#tbfix-stage'); s.scrollLeft = s.scrollWidth; s.scrollTop = s.scrollHeight; }")
        pg.wait_for_timeout(300)
        R = [A1[0] - 410.0, A1[1] - 296.0, A1[0] - 150.0, A1[1] - 264.0]
        z = pg.evaluate("() => TB.zoom")
        ib = pg.evaluate("() => { const r = document.querySelector('#tbfix-img').getBoundingClientRect(); return [r.left, r.top]; }")
        p0 = (ib[0] + R[0] * z, ib[1] + R[1] * z); p1 = (ib[0] + R[2] * z, ib[1] + R[3] * z)
        # ② 패널 — 칸 고르기
        rad = pg.evaluate("() => { const b = document.querySelector('input[name=\"tbfix-cell\"]:checked').parentElement.getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; }")
        pg.screenshot(path=str(OUT / "_2.png"))
        im = Image.open(OUT / "_2.png")
        callout(im, rad, 2, "그을 칸을 고른다 — 도면번호 (필수)", dx=-420, dy=-40)
        callout(im, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), 3, "도면번호가 인쇄된 자리를 마우스로 끌어 감싼다", dx=-560, dy=-70)
        im.save(OUT / "2_패널_어디를_끌까.png")
        # ③ 끄는 중 (고무줄 상자)
        pg.mouse.move(*p0); pg.mouse.down(); pg.mouse.move(p1[0], p1[1], steps=8)
        pg.wait_for_timeout(150)
        clip = {"x": p0[0] - 120, "y": p0[1] - 90, "width": (p1[0] - p0[0]) + 240, "height": (p1[1] - p0[1]) + 200}
        pg.screenshot(path=str(OUT / "_3.png"), clip=clip)
        pg.mouse.up()
        pg.wait_for_function("() => /장 중/.test(document.querySelector('#tbfix-preview').textContent)", timeout=30000)
        pg.wait_for_timeout(200)
        pg.screenshot(path=str(OUT / "_3b.png"), clip=clip)
        a = Image.open(OUT / "_3.png"); c = Image.open(OUT / "_3b.png")
        a = a.resize((a.width * 2, a.height * 2), Image.LANCZOS); c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
        pair = Image.new("RGB", (a.width + c.width + 30, a.height + 50), "white")
        pair.paste(a, (0, 50)); pair.paste(c, (a.width + 30, 50))
        d = ImageDraw.Draw(pair)
        d.text((10, 14), "끄는 중 — 사각형이 번호를 감싸도록", font=FONT, fill=(60, 30, 20))
        d.text((a.width + 40, 14), "놓은 뒤 — '도면번호' 칸으로 저장됨", font=FONT, fill=(60, 30, 20))
        pair.save(OUT / "3_끌기_확대.png")
        # ④ 미리보기 + ⑤ 작성자·저장
        pg.fill("#tbfix-who", "홍길동")
        pg.evaluate("() => document.querySelector('#tbfix-preview').scrollIntoView({block: 'center'})")
        pg.wait_for_timeout(300)
        pv = pg.evaluate("() => { const b = document.querySelector('#tbfix-preview p').getBoundingClientRect(); return [b.left + 60, b.top + b.height/2]; }")
        who = pg.evaluate("() => { const b = document.querySelector('#tbfix-who').getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; }")
        run = pg.evaluate("() => { const b = document.querySelector('#tbfix-save-run').getBoundingClientRect(); return [b.left + b.width/2, b.top + b.height/2]; }")
        pg.screenshot(path=str(OUT / "_4.png"))
        im = Image.open(OUT / "_4.png")
        callout(im, pv, 4, "같은 크기의 모든 장에서 읽힌 값이 표로 보인다 — 장 수·형식을 확인", dx=520, dy=-40)
        callout(im, who, 5, "작성자 이름을 적는다 (없으면 저장되지 않음)", dx=40, dy=-56)
        callout(im, run, 6, "[저장하고 다시 분석] — 이 칸으로 다시 읽는다", dx=200, dy=-100)
        im.save(OUT / "4_미리보기_저장.png")
        br.close()
finally:
    srv.terminate()
for f in OUT.glob("_*.png"): f.unlink()
print(sorted(p.name for p in OUT.glob("*.png")))
