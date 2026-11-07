"""I&C 멀티에이전트 대시보드 로컬 서버 (Python 표준 라이브러리만).

- http://127.0.0.1:8790/          → app/index.html (대시보드)
- /output/*.docx                  → MR 초안 다운로드
- /api/fin/status                 → DART 키 연결 여부(값은 절대 반환·출력하지 않음)
- /api/fin/ask?q=현대건설 실적      → 공시 재무제표 에이전트: DART OpenAPI 원본 값 인용

'공시 재무제표 대시보드'(dart_dashboard/server.py) 구조를 벤치마킹했다.
API 키는 코드로만 읽는다(사람·에이전트가 파일을 열지 않음). 우선순위:
  1) 환경변수 DART_API_KEY
  2) 프로젝트 루트 .env 의 DART_API_KEY=...
  3) 환경변수 DART_KEY_FILE 이 가리키는 파일
  4) 벤치마크 대시보드의 dart_api_key.txt (../현장회의록_요약/dart_dashboard/)
규칙: 재무 수치는 DART 원본 문자열만 인용, 재계산·추정 금지. 계측제어 지식과 섞지 않는다.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PORT = int(os.environ.get("PORT") or os.environ.get("IC_PORT") or "8790")
DART = "https://opendart.fss.or.kr/api"
BENCH = os.path.join(os.path.dirname(ROOT), "현장회의록_요약", "dart_dashboard")
CACHE = os.path.join(ROOT, "data", "fin")
os.makedirs(CACHE, exist_ok=True)


def load_key():
    k = os.environ.get("DART_API_KEY", "").strip()
    if k:
        return k, "환경변수 DART_API_KEY"
    envp = os.path.join(ROOT, ".env")
    if os.path.exists(envp):
        for line in open(envp, encoding="utf-8"):
            m = re.match(r"\s*DART_API_KEY\s*=\s*['\"]?([^'\"\s#]+)", line)
            if m:
                return m.group(1), ".env (DART_API_KEY)"
    for p, label in ((os.environ.get("DART_KEY_FILE", ""), "DART_KEY_FILE"), (os.path.join(BENCH, "dart_api_key.txt"), "벤치마크 대시보드 키 파일")):
        if p and os.path.exists(p):
            k = open(p, encoding="utf-8").read().strip()
            if k:
                return k, label
    return "", "없음"


API_KEY, KEY_SRC = load_key()


def safe(s):
    s = str(s)
    return s.replace(API_KEY, "***") if API_KEY else s


def dart_get(path, **params):
    params["crtfc_key"] = API_KEY
    url = f"{DART}/{path}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read()


CORPS = None


def corps():
    global CORPS
    if CORPS is not None:
        return CORPS
    for p in (os.path.join(BENCH, "corp_codes.json"), os.path.join(CACHE, "corp_codes.json")):
        if os.path.exists(p) and time.time() - os.path.getmtime(p) < 30 * 86400:
            CORPS = json.load(open(p, encoding="utf-8"))
            return CORPS
    raw = dart_get("corpCode.xml")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xml = z.read(z.namelist()[0])
    CORPS = [{k: (el.findtext(k) or "").strip() for k in ("corp_code", "corp_name", "stock_code", "modify_date")} for el in ET.fromstring(xml).iter("list")]
    json.dump(CORPS, open(os.path.join(CACHE, "corp_codes.json"), "w", encoding="utf-8"), ensure_ascii=False)
    return CORPS


STOPW = r"(공시|재무제표|재무|실적|최근|매출액?|영업이익|순이익|당기순이익|자산|부채|자본|알려\s*줘|알려|주세요|보여\s*줘|해\s*줘|어때|어떤가요|은|는|이|가|의|좀|요약|현황|연간|올해|작년|\?|！|!|\.)"


def find_corp(q):
    name = re.sub(STOPW, " ", q).strip().split()
    name = max(name, key=len) if name else ""
    key = name.lower().replace(" ", "")
    if not key:
        return None, name
    hits = []
    for c in corps():
        n = c["corp_name"].lower().replace(" ", "")
        if key in n or c["stock_code"] == key:
            hits.append(((0 if n == key or c["stock_code"] == key else 1 if n.startswith(key) else 2), 0 if c["stock_code"] else 1, -int(c.get("modify_date") or 0), len(n), c))
    hits.sort(key=lambda x: x[:4])
    return (hits[0][4] if hits else None), name


KEYS = [("매출액", ["ifrs-full_Revenue"], ["매출액", "수익(매출액)", "영업수익", "매출"], ("IS", "CIS")),
        ("영업이익", ["dart_OperatingIncomeLoss"], ["영업이익", "영업이익(손실)"], ("IS", "CIS")),
        ("당기순이익", ["ifrs-full_ProfitLoss"], ["당기순이익", "당기순이익(손실)"], ("IS", "CIS")),
        ("자산총계", ["ifrs-full_Assets"], ["자산총계"], ("BS",)),
        ("부채총계", ["ifrs-full_Liabilities"], ["부채총계"], ("BS",)),
        ("자본총계", ["ifrs-full_Equity"], ["자본총계"], ("BS",))]


def ask(q):
    if not API_KEY:
        return {"ok": False, "msg": "DART API 키가 연결되지 않았습니다. 프로젝트 .env 에 DART_API_KEY=... 를 넣거나 환경변수를 설정하세요(값은 화면·로그에 표시하지 않습니다)."}
    c, name = find_corp(q)
    if not c:
        return {"ok": False, "msg": f"'{name}' 에 해당하는 DART 등록 회사를 찾지 못했습니다(미확인)."}
    y0 = time.localtime().tm_year
    for y in (str(y0 - 1), str(y0 - 2)):
        for fs in ("CFS", "OFS"):
            d = json.loads(dart_get("fnlttSinglAcntAll.json", corp_code=c["corp_code"], bsns_year=y, reprt_code="11011", fs_div=fs))
            if d.get("status") == "000" and d.get("list"):
                rows = d["list"]
                out = []
                for label, ids, names, sjs in KEYS:
                    r = next((r for r in rows if r["sj_div"] in sjs and r.get("account_id") in ids), None) or \
                        next((r for r in rows if r["sj_div"] in sjs and (r.get("account_nm") or "").replace(" ", "") in [n.replace(" ", "") for n in names]), None)
                    if r:
                        out.append({"label": label, "account_nm": r.get("account_nm"), "sj_nm": r.get("sj_nm"),
                                    "thstrm_nm": r.get("thstrm_nm"), "thstrm": r.get("thstrm_amount"),
                                    "frmtrm_nm": r.get("frmtrm_nm"), "frmtrm": r.get("frmtrm_amount"), "currency": r.get("currency", "KRW")})
                    else:
                        out.append({"label": label, "missing": True})
                return {"ok": True, "corp": c, "year": y, "fs": "연결" if fs == "CFS" else "별도", "rcept_no": rows[0].get("rcept_no"),
                        "report": "사업보고서", "rows": out, "source": "DART OpenAPI fnlttSinglAcntAll.json", "key_src": KEY_SRC}
    return {"ok": False, "msg": f"{c['corp_name']} 의 최근 사업보고서 재무제표를 DART 에서 받지 못했습니다(미확인)."}


# ---- 벤치마크 '공시 재무제표 대시보드' UI 를 /fin/ 에 그대로 올린다(그 서버 모듈의 Handler 를 상속) ----
BENCH_OK = False
Base = BaseHTTPRequestHandler
if os.path.exists(os.path.join(BENCH, "server.py")):
    try:
        sys.path.insert(0, BENCH)
        import server as bench  # noqa: E402  (키는 그 모듈의 load_key 가 코드로 읽음)
        Base = bench.Handler
        BENCH_OK = True
    except BaseException as e:  # sys.exit 포함
        sys.stderr.write("벤치마크 대시보드 로드 실패: " + safe(e) + chr(10))

BRIDGE = b"""<script>/* I&C chat bridge */
(function(){function go(c){try{if(c&&c.corp_code&&typeof pick==='function')pick(c)}catch(e){}}
var bc=('BroadcastChannel' in window)?new BroadcastChannel('ic-fin'):null;
if(bc)bc.onmessage=function(e){if(!e.data)return;if(e.data.type==='pick')go(e.data.corp);if(e.data.type==='theme')document.documentElement.dataset.theme=e.data.theme};
window.addEventListener('message',function(e){if(e.origin===location.origin&&e.data&&e.data.type==='pick')go(e.data.corp)});
var u=new URLSearchParams(location.search);if(u.get('corp_code'))setTimeout(function(){go({corp_code:u.get('corp_code'),corp_name:u.get('corp_name')||'',stock_code:u.get('stock_code')||''})},300);
})();</script>"""


class H(Base):
    def log_message(self, fmt, *a):
        sys.stderr.write(safe(fmt % a) + "\n")

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, open(os.path.join(HERE, "index.html"), "rb").read(), "text/html; charset=utf-8")
            if u.path == "/viewer-real.html":  # 실물 3D 엔진(ic-3d-builder), build.mjs 가 복사
                p = os.path.join(HERE, "viewer-real.html")
                if os.path.exists(p):
                    return self.send(200, open(p, "rb").read(), "text/html; charset=utf-8")
            if u.path == "/api/fin/status":
                return self.send(200, {"key": bool(API_KEY), "key_src": KEY_SRC, "dashboard": BENCH_OK})
            if False:
                return self.send(200, {"key": bool(API_KEY), "key_src": KEY_SRC})
            if u.path == "/api/fin/ask":
                return self.send(200, ask(q.get("q", "")))
            if u.path in ("/fin", "/fin/"):
                if not BENCH_OK:
                    return self.send(200, "<p style='font-family:sans-serif'>공시 재무제표 대시보드 코드를 찾지 못했습니다(미확인).</p>".encode("utf-8"), "text/html; charset=utf-8")
                html = open(os.path.join(BENCH, "index.html"), "rb").read()
                i = html.rfind(b"</body>")
                html = html[:i] + BRIDGE + html[i:] if i >= 0 else html + BRIDGE
                return self.send(200, html, "text/html; charset=utf-8")
            if u.path.startswith("/output/"):
                fn = os.path.basename(urllib.parse.unquote(u.path))
                p = os.path.join(ROOT, "output", fn)
                if fn.endswith(".docx") and os.path.exists(p):
                    return self.send(200, open(p, "rb").read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                     {"Content-Disposition": "attachment; filename*=UTF-8''" + urllib.parse.quote(fn)})
            if BENCH_OK and u.path.startswith("/api/"):
                return Base.do_GET(self)  # 벤치마크 API(/api/search, /api/fin, /api/stock ...)
            self.send(404, {"error": "not found"})
        except Exception as e:  # 키가 메시지에 섞이지 않도록 마스킹
            self.send(500, {"ok": False, "msg": "서버 오류: " + safe(e)})


if __name__ == "__main__":
    print(f"I&C 대시보드: http://127.0.0.1:{PORT}  (DART 키: {'연결됨 - ' + KEY_SRC if API_KEY else '없음'})", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
