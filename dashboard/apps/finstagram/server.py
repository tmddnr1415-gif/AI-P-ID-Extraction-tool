# -*- coding: utf-8 -*-
"""
DART 공시 재무제표 대시보드 - 로컬 서버 (Python 표준 라이브러리만 사용)

실행:  python server.py   → 브라우저에서 http://localhost:8765 접속
API 키: 환경변수 DART_API_KEY · DART_KEY_FILE(키 파일 경로) 또는 같은 폴더의 dart_api_key.txt

계장ENG그룹 Dashboard 에 포함 (2026-11-07): 대시보드 server.py 가 이 서버를 함께 띄운다
  (FIN_HOST=0.0.0.0 · PORT · DART_KEY_FILE = 서버 PC 키 파일 · FIN_NETS_FILE = 대시보드 사내 대역 파일).
  메뉴 '재무스타그램' → http://<서버>:8765/ 를 iframe 으로. 사내망 주소만 접속 허용. 라이브러리는 vendor/ (CDN 안 씀).
"""
import ipaddress
import mimetypes
import io
import json
import re
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8765"))
HOST = os.environ.get("FIN_HOST", "127.0.0.1")
APP_VERSION = "2026-11-09.1"
DART = os.environ.get("FIN_DART_BASE", "").strip() or "https://opendart.fss.or.kr/api"   # FIN_DART_BASE = 시험용
CORP_CACHE = os.path.join(BASE, "corp_codes.json")


def key_file():
    return os.environ.get("DART_KEY_FILE", "").strip() or os.path.join(BASE, "dart_api_key.txt")


KEY_NAMES = ("DART_API_KEY", "OPENDART_API_KEY", "DART_KEY", "CRTFC_KEY")


def parse_key(text):
    """.env 또는 키 한 줄 파일 → DART 키. DART_API_KEY= (OPENDART_API_KEY · DART_KEY · CRTFC_KEY) 줄 먼저, 없으면 키만 적힌 한 줄.
    대시보드 server.py 의 parse_dart_key 와 같은 규칙 (고치면 둘 다)"""
    plain = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$", line)
        if m:
            name = m.group(1).upper()
            if name in KEY_NAMES or 'API_KEY' in name or 'DART' in name or 'CRTFC' in name:   # 2026-11-09 DATA_API_KEY= 처럼 이름이 달라도 API 키 줄이면 받음
                return re.sub(r"\s+#.*$", "", m.group(2)).strip().strip("\"'").strip("{}").strip()
        else:
            plain.append(line)
    if len(plain) == 1:
        return plain[0]
    kv = [ln for ln in (text or "").splitlines() if re.match(r"\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*\s*=\s*\S", ln) and not ln.strip().startswith("#")]
    if len(kv) == 1:                                       # 이름=값 줄이 하나뿐이면 그것이 키
        return kv[0].split("=", 1)[1].strip().strip('\"')
    return ""


def load_key():
    """키 = 환경변수 DART_API_KEY → 키 파일(DART_KEY_FILE = 운영자가 대시보드에서 지정한 .env, 또는 같은 폴더 dart_api_key.txt). 없으면 '' (서버는 켜 두고 화면에 안내)"""
    k = os.environ.get("DART_API_KEY", "").strip()
    if not k:
        try:
            with open(key_file(), encoding="utf-8-sig") as f:
                k = parse_key(f.read(20000))
        except OSError:
            pass
    return k


API_KEY = load_key()


# ---------------------------------------------------------------- 인터넷 연결 (2026-11-09: 회사 PC 에서 검색이 조용히 실패 → 이유를 한국어로 알려 줌)
def proxy_url():
    """프록시: 환경변수 FIN_PROXY → 대시보드가 넘긴 FIN_PROXY_FILE(운영 폴더 fin_proxy.txt). 없으면 윈도 인터넷 설정 · HTTPS_PROXY (urllib 기본)"""
    v = os.environ.get("FIN_PROXY", "").strip()
    if not v:
        try:
            with open(os.environ.get("FIN_PROXY_FILE", "") or os.path.join(BASE, "proxy.txt"), encoding="utf-8-sig") as f:
                v = next((ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")), "")
        except OSError:
            v = ""
    if v and not re.match(r"^https?://", v):
        v = "http://" + v
    return v


def opener():
    px = proxy_url()
    return urllib.request.build_opener(urllib.request.ProxyHandler({"http": px, "https": px})) if px else urllib.request.build_opener()


DART_ERR = {"010": "등록되지 않은 DART 키입니다 (키를 다시 확인하세요)", "011": "사용할 수 없는 DART 키입니다", "012": "DART 에서 이 PC 의 IP 접근을 막았습니다",
            "020": "DART 요청 한도(하루 2만 건)를 넘었습니다 — 내일 다시", "021": "DART 조회 가능 회사 수를 넘었습니다", "100": "DART 요청 값이 잘못되었습니다",
            "101": "DART 에 등록되지 않은 접근입니다", "800": "DART 가 시스템 점검 중입니다", "900": "DART 쪽 알 수 없는 오류입니다", "901": "DART 키(개인정보) 보유기간이 끝났습니다 — 키를 다시 발급하세요"}


def net_reason(e, host="opendart.fss.or.kr"):
    """urlopen 예외 → 사람이 읽는 이유 (host = 접속하려던 곳)"""
    t = repr(getattr(e, "reason", e))
    if "CERTIFICATE_VERIFY_FAILED" in t or "SSL" in t:
        return "보안 인증서(SSL) 확인 실패 — 회사 보안 프로그램이 HTTPS 를 검사하는 것 같습니다 (IT 에 " + host + " 예외 요청 또는 회사 인증서 설치)"
    if "Tunnel connection failed" in t:
        return "회사 프록시가 " + host + " 접속을 막았습니다 (" + (re.search(r"\d{3}[^'\")]*", t.split("failed:")[-1]) or [""])[0].strip() + ") — IT 에 " + host + " 허용 요청 또는 프록시 계정 설정"
    if isinstance(e, urllib.error.HTTPError):
        return f"DART 서버 응답 {e.code}" + (" — 프록시 인증이 필요합니다" if e.code == 407 else "")
    if "getaddrinfo" in t or "Name or service" in t or "11001" in t or "11004" in t:
        return host + " 주소를 찾지 못했습니다 — 서버 PC 인터넷(DNS) 또는 프록시 설정 확인"
    if "timed out" in t or "10060" in t:
        return host + " 응답이 없습니다(시간 초과) — 회사망이 막았거나 프록시가 필요합니다"
    if "10061" in t or "refused" in t or "10013" in t:
        return "연결이 거부되었습니다 — 회사망 방화벽 또는 프록시 설정 확인"
    return "인터넷 연결 실패: " + t[:160]


def dart_get(path, **params):
    global API_KEY
    if not API_KEY:
        API_KEY = load_key()          # 서버를 켠 뒤에 키 파일을 두어도 바로 쓰게
    if not API_KEY:
        raise RuntimeError(f"DART API 키가 없습니다 — 대시보드 재무스타그램 화면 ⚙ 에서 키 파일(.env) 경로를 지정하세요 (지금: {key_file()})")
    params["crtfc_key"] = API_KEY
    url = f"{DART}/{path}?{urllib.parse.urlencode(params)}"
    try:
        with opener().open(url, timeout=30) as r:
            raw = r.read()
    except Exception as e:  # noqa
        raise RuntimeError(net_reason(e)) from None
    head = raw[:400].lstrip()
    st = None
    if head[:1] == b"{":
        m = re.search(rb'"status"\s*:\s*"(\d+)"', head)
        st = m and m.group(1).decode()
    elif head[:5] == b"<?xml" or head[:8] == b"<result>":
        m = re.search(rb"<status>(\d+)</status>", head)
        st = m and m.group(1).decode()
    if st in DART_ERR:
        raise RuntimeError(f"{DART_ERR[st]} (DART {st})")
    if path.endswith(".xml") and path in ("corpCode.xml", "document.xml", "fnlttXbrl.xml") and raw[:2] != b"PK" and st and st != "000":
        m = re.search(rb"<message>(.*?)</message>", raw[:2000], re.S)
        raise RuntimeError(f"DART 응답 {st}: {(m.group(1).decode('utf-8', 'replace') if m else '')}")
    return raw


def diag():
    """연결 점검 — 키 유무(값은 숨김) · 프록시 · DART 접속 · 회사 목록 캐시"""
    k = API_KEY or load_key()
    out = {"ver": APP_VERSION, "keyFile": key_file(), "key": bool(k), "keyLen": len(k), "keyOk": bool(re.fullmatch(r"[0-9A-Za-z]{40}", k or "")),
           "proxy": proxy_url() or (lambda g: ("윈도 · 환경 설정: " + ", ".join(f"{a}={b}" for a, b in g.items())) if g else "없음(직접 연결)")({a: b for a, b in urllib.request.getproxies().items() if a in ("http", "https")}),
           "corpCache": os.path.exists(CORP_CACHE), "corps": len(CORPS)}
    t0 = time.time()
    try:
        d = json.loads(dart_get("company.json", corp_code="00126380"))
        out.update(dart=True, msg=f"DART 접속 정상 ({d.get('corp_name', '')} 조회 {time.time() - t0:.1f}초)")
    except Exception as e:  # noqa
        out.update(dart=False, msg=str(e))
    return out


# ---------------------------------------------------------------- 회사 코드
def load_corps():
    if os.path.exists(CORP_CACHE) and time.time() - os.path.getmtime(CORP_CACHE) < 7 * 86400:
        with open(CORP_CACHE, encoding="utf-8") as f:
            return json.load(f)
    print("고유번호(corpCode) 목록을 내려받는 중...")
    raw = dart_get("corpCode.xml")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xml = z.read(z.namelist()[0])
    corps = []
    for el in ET.fromstring(xml).iter("list"):
        corps.append({
            "corp_code": (el.findtext("corp_code") or "").strip(),
            "corp_name": (el.findtext("corp_name") or "").strip(),
            "stock_code": (el.findtext("stock_code") or "").strip(),
            "modify_date": (el.findtext("modify_date") or "").strip(),
        })
    with open(CORP_CACHE, "w", encoding="utf-8") as f:
        json.dump(corps, f, ensure_ascii=False)
    print(f"{len(corps):,}개 회사 로드 완료")
    return corps


CORPS = []


def search(q):
    global CORPS
    q = q.strip().lower().replace(" ", "")
    if not q:
        return []
    if not CORPS:                     # 처음 검색할 때 받음 (키 · 인터넷이 없어도 서버는 켜지게)
        CORPS = load_corps()
    hits = []
    for c in CORPS:
        name = c["corp_name"].lower().replace(" ", "")
        if q in name or (c["stock_code"] and q == c["stock_code"]):
            score = (
                0 if name == q or c["stock_code"] == q else 1 if name.startswith(q) else 2,
                0 if c["stock_code"] else 1,  # 상장사 우선
                -int(c.get("modify_date") or 0),  # 최근 갱신(존속) 회사 우선
                len(name),
            )
            hits.append((score, c))
    hits.sort(key=lambda x: x[0])
    result = [dict(c) for _, c in hits[:20]]
    add_ceo_for_duplicates(result)
    return result


CEO_CACHE = {}


def get_ceo(corp_code):
    if corp_code not in CEO_CACHE:
        try:
            d = json.loads(dart_get("company.json", corp_code=corp_code))
            CEO_CACHE[corp_code] = (d.get("ceo_nm") or "").strip() if d.get("status") == "000" else ""
        except Exception:  # noqa
            return ""
    return CEO_CACHE[corp_code]


def add_ceo_for_duplicates(items):
    """검색 결과 중 회사명이 같은 항목에만 대표이사명을 붙인다."""
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    counts = Counter(c["corp_name"].replace(" ", "") for c in items)
    dups = [c for c in items if counts[c["corp_name"].replace(" ", "")] > 1]
    if not dups:
        return
    with ThreadPoolExecutor(max_workers=8) as ex:
        for c, ceo in zip(dups, ex.map(lambda c: get_ceo(c["corp_code"]), dups)):
            c["ceo_nm"] = ceo


# ---------------------------------------------------------------- 재무제표
REPRT_NAMES = {"11011": "사업보고서", "11012": "반기보고서", "11013": "1분기보고서", "11014": "3분기보고서"}

# 핵심 계정: (키, account_id 후보, 계정명 후보, 재무제표 구분)
KEY_ACCOUNTS = [
    ("revenue", ["ifrs-full_Revenue"], ["매출액", "수익(매출액)", "영업수익", "매출"], ("IS", "CIS")),
    ("gross_profit", ["ifrs-full_GrossProfit"], ["매출총이익"], ("IS", "CIS")),
    ("operating_income", ["dart_OperatingIncomeLoss"], ["영업이익", "영업이익(손실)"], ("IS", "CIS")),
    ("net_income", ["ifrs-full_ProfitLoss"], ["당기순이익", "당기순이익(손실)", "분기순이익", "반기순이익"], ("IS", "CIS")),
    ("net_income_owner", ["ifrs-full_ProfitLossAttributableToOwnersOfParent"], [], ("IS", "CIS")),
    ("assets", ["ifrs-full_Assets"], ["자산총계"], ("BS",)),
    ("current_assets", ["ifrs-full_CurrentAssets"], ["유동자산"], ("BS",)),
    ("liabilities", ["ifrs-full_Liabilities"], ["부채총계"], ("BS",)),
    ("current_liabilities", ["ifrs-full_CurrentLiabilities"], ["유동부채"], ("BS",)),
    ("equity", ["ifrs-full_Equity"], ["자본총계"], ("BS",)),
    ("cash", ["ifrs-full_CashAndCashEquivalents"], ["현금및현금성자산"], ("BS",)),
    ("ocf", ["ifrs-full_CashFlowsFromUsedInOperatingActivities"], ["영업활동현금흐름", "영업활동으로인한현금흐름"], ("CF",)),
    ("icf", ["ifrs-full_CashFlowsFromUsedInInvestingActivities"], ["투자활동현금흐름"], ("CF",)),
    ("fcf_fin", ["ifrs-full_CashFlowsFromUsedInFinancingActivities"], ["재무활동현금흐름"], ("CF",)),
    ("capex", ["ifrs-full_PurchaseOfPropertyPlantAndEquipment"], ["유형자산의취득"], ("CF",)),
]


def num(v):
    if v in (None, "", "-"):
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def row_values(r, is_flow, cumulative):
    """당기/전기/전전기 값. 분·반기 손익은 누적 금액 사용."""
    if is_flow and cumulative:
        cur = num(r.get("thstrm_add_amount")) if r.get("thstrm_add_amount") else num(r.get("thstrm_amount"))
        prev = num(r.get("frmtrm_add_amount")) if r.get("frmtrm_add_amount") else num(r.get("frmtrm_amount"))
    else:
        cur, prev = num(r.get("thstrm_amount")), num(r.get("frmtrm_amount"))
    return [cur, prev, num(r.get("bfefrmtrm_amount"))]


def fetch_statements(corp_code, year, reprt, fs_pref):
    tried = []
    for y in ([year] if year else [str(time.localtime().tm_year - 1), str(time.localtime().tm_year - 2)]):
        for fs in ([fs_pref] if fs_pref else ["CFS", "OFS"]):
            d = json.loads(dart_get("fnlttSinglAcntAll.json", corp_code=corp_code, bsns_year=y,
                                   reprt_code=reprt, fs_div=fs))
            tried.append(f"{y}/{fs}: {d.get('message')}")
            if d.get("status") == "000" and d.get("list"):
                return y, fs, d["list"], tried
    return None, None, [], tried


def extract_key(rows, cumulative):
    key = {}
    for k, ids, names, sjs in KEY_ACCOUNTS:
        found = None
        for r in rows:
            if r["sj_div"] in sjs and r.get("account_id") in ids:
                found = r
                break
        if not found and names:
            norm = [n.replace(" ", "") for n in names]
            for r in rows:
                if r["sj_div"] in sjs and (r.get("account_nm") or "").replace(" ", "") in norm:
                    found = r
                    break
        if found:
            key[k] = row_values(found, found["sj_div"] != "BS", cumulative)
            key[k + "__bs"] = found["sj_div"] == "BS"
    return key


HIST_CACHE = {}


def history(corp_code, year, reprt, fs, n=5):
    """최근 n개 연도 핵심 계정. 각 보고서의 당기·전기·전전기 값을 이용해 호출 수를 줄인다."""
    ck = (corp_code, year, reprt, fs)
    if ck in HIST_CACHE:
        return HIST_CACHE[ck]
    cumulative = reprt != "11011"
    years = [str(int(year) - i) for i in range(n)]
    data = {y: {} for y in years}
    fetched = set()
    for _ in range(n):
        missing = [y for y in years if not (data[y].get("revenue") and data[y].get("assets")) and y not in fetched]
        if not missing:
            break
        fy = max(missing, key=int)
        fetched.add(fy)
        try:
            d = json.loads(dart_get("fnlttSinglAcntAll.json", corp_code=corp_code, bsns_year=fy, reprt_code=reprt, fs_div=fs))
        except Exception:  # noqa
            continue
        if d.get("status") != "000" or not d.get("list"):
            continue
        key = extract_key(d["list"], cumulative)
        for k, vals in key.items():
            if k.endswith("__bs"):
                continue
            is_bs = key.get(k + "__bs")
            for i, v in enumerate(vals):
                if cumulative and is_bs and i > 0:
                    break  # 분기 재무상태표의 전기 값은 전년말이라 동기 비교 불가
                ty = str(int(fy) - i)
                if ty in data and v is not None and data[ty].get(k) is None:
                    data[ty][k] = v
    res = {"years": years, "data": data, "reprt_name": REPRT_NAMES.get(reprt, reprt),
           "fs_name": "연결재무제표" if fs == "CFS" else "별도재무제표", "cumulative": cumulative}
    HIST_CACHE[ck] = res
    return res


def build(corp_code, year, reprt, fs_pref):
    info = json.loads(dart_get("company.json", corp_code=corp_code))
    y, fs, rows, tried = fetch_statements(corp_code, year, reprt, fs_pref)
    if not rows:
        return {"company": info, "error": "재무제표 데이터를 찾지 못했습니다. (" + " | ".join(tried) + ")"}

    cumulative = reprt != "11011"
    yi = int(y)
    periods = [str(yi), str(yi - 1), str(yi - 2)]

    statements = {}
    for r in sorted(rows, key=lambda r: (r["sj_div"], int(r.get("ord") or 9999))):
        sj = r["sj_div"]
        flow = sj in ("IS", "CIS", "CF")
        statements.setdefault(sj, {"name": r.get("sj_nm", sj), "rows": []})
        statements[sj]["rows"].append({
            "id": r.get("account_id"),
            "name": r.get("account_nm"),
            "detail": r.get("account_detail") if r.get("account_detail") not in (None, "-") else "",
            "values": row_values(r, flow, cumulative),
        })

    key = extract_key(rows, cumulative)

    return {
        "company": info,
        "year": y,
        "reprt_code": reprt,
        "reprt_name": REPRT_NAMES.get(reprt, reprt),
        "fs_div": fs,
        "fs_name": "연결재무제표" if fs == "CFS" else "별도재무제표",
        "currency": rows[0].get("currency", "KRW"),
        "rcept_no": rows[0].get("rcept_no"),
        "periods": periods,
        "key": key,
        "summary": summarize(key, periods, cumulative),
        "statements": statements,
        "employees": employees(corp_code, y, reprt),
    }


# ---------------------------------------------------------------- 사업부문 (XBRL)
SEG_CACHE = {}
XI = "{http://www.xbrl.org/2003/instance}"
XDI = "{http://xbrl.org/2006/xbrldi}"
XL = "{http://www.w3.org/1999/xlink}"
REV_TAGS = ("Revenue", "RevenueFromContractsWithCustomers")
OI_TAGS = ("OperatingIncomeLoss",)


def _labels(xml_bytes):
    root = ET.fromstring(xml_bytes)
    loc, lab, arcs = {}, {}, {}
    for el in root.iter():
        t = el.tag.split("}")[-1]
        if t == "loc":
            loc[el.get(XL + "label")] = el.get(XL + "href", "").split("#")[-1]
        elif t == "label" and el.get(XL + "role", "").endswith("/role/label"):
            lab[el.get(XL + "label")] = (el.text or "").strip()
        elif t == "labelArc":
            arcs[el.get(XL + "from")] = el.get(XL + "to")
    return {loc[f]: lab[to] for f, to in arcs.items() if f in loc and to in lab}


def _member_name(qname, labels):
    lid = qname.replace(":", "_")
    clean = lambda t: re.sub(r"\s*\[.*?\]\s*", "", t).strip()
    if lid in labels:
        return clean(labels[lid])
    local = qname.split(":")[-1]
    prefix = local.split("Of")[0]
    for k, v in labels.items():  # 같은 부문의 다른 표 라벨 재사용
        if k.split("_", 1)[-1].split("Of")[0] == prefix and k.endswith("Member") or k.split("_", 1)[-1].startswith(prefix + "Of"):
            return clean(v)
    local = re.sub(r"Of(Reportable|Operating)?Segments?Member.*$|Member$", "", local)
    return re.sub(r"(?<!^)([A-Z])", r" \1", local)


def segments(rcept_no, reprt, fs):
    ck = (rcept_no, reprt, fs)
    if ck in SEG_CACHE:
        return SEG_CACHE[ck]
    try:
        raw = dart_get("fnlttXbrl.xml", rcept_no=rcept_no, reprt_code=reprt)
        z = zipfile.ZipFile(io.BytesIO(raw))
    except Exception as e:  # noqa
        return {"error": f"XBRL 파일을 받지 못했습니다: {e}"}
    names = z.namelist()
    xb = [n for n in names if n.endswith(".xbrl")]
    if not xb:
        return {"error": "XBRL 원본이 없습니다."}
    lab = [n for n in names if n.endswith("lab-ko.xml")]
    labels = _labels(z.read(lab[0])) if lab else {}
    root = ET.fromstring(z.read(xb[0]))
    want_cs = "ConsolidatedMember" if fs == "CFS" else "SeparateMember"

    ctx = {}
    for c in root.iter(XI + "context"):
        dims = {m.get("dimension"): (m.text or "").strip() for m in c.iter(XDI + "explicitMember")}
        seg = dims.pop("ifrs-full:SegmentsAxis", None)
        if not seg or re.search(r"ReportableSegmentsMember$|Total", seg.split(":")[-1]):
            continue
        cs = dims.pop("ifrs-full:ConsolidatedAndSeparateFinancialStatementsAxis", "")
        if cs and not cs.endswith(want_cs):
            continue
        item = dims.pop("ifrs-full:SegmentConsolidationItemsAxis", "ifrs-full:OperatingSegmentsMember")
        if not item.endswith("OperatingSegmentsMember") or dims:
            continue
        per = c.find(XI + "period")
        start, end = per.findtext(XI + "startDate"), per.findtext(XI + "endDate")
        if not end:
            continue
        ctx[c.get("id")] = (seg, start, end)

    data, periods = {}, set()
    for el in root:
        cid = el.get("contextRef")
        if cid not in ctx:
            continue
        tag = el.tag.split("}")[-1]
        key = "revenue" if tag in REV_TAGS else "operating_income" if tag in OI_TAGS else None
        if not key:
            continue
        v = num(el.text)
        if v is None:
            continue
        seg, start, end = ctx[cid]
        periods.add((start, end))
        d = data.setdefault(seg, {}).setdefault((start, end), {})
        if key not in d or tag == "Revenue":
            d[key] = v

    if not data:
        res = {"error": "공시에 사업부문별 매출·영업이익(XBRL) 정보가 없습니다."}
        SEG_CACHE[ck] = res
        return res
    # 가장 긴(연간·누적) 기간 기준으로 당기·전기 선택
    def length(p):
        return (time.mktime(time.strptime(p[1], "%Y-%m-%d")) - time.mktime(time.strptime(p[0], "%Y-%m-%d"))) if p[0] else 0
    maxlen = max(length(p) for p in periods)
    use = sorted([p for p in periods if abs(length(p) - maxlen) < 86400 * 5], key=lambda p: p[1], reverse=True)[:2]

    # 같은 부문이 여러 주석 표에 반복되므로, 영업이익이 가장 많이 공시된 표 하나만 사용
    table = lambda q: q.split("MemberOf")[-1] if "MemberOf" in q else ""
    score = {}
    for seg, byp in data.items():
        sc = score.setdefault(table(seg), [0, 0])
        for d in byp.values():
            sc[0] += "operating_income" in d
            sc[1] += "revenue" in d
    best = max(score, key=lambda t: (score[t][0], score[t][1]))
    data = {k: v for k, v in data.items() if table(k) == best}

    rows = []
    for seg, byp in data.items():
        cur, prev = byp.get(use[0], {}), byp.get(use[1], {}) if len(use) > 1 else {}
        if not any(cur.get(k) for k in ("revenue", "operating_income")) and not any(prev.get(k) for k in ("revenue", "operating_income")):
            continue
        rows.append({"name": _member_name(seg, labels),
                     "revenue": cur.get("revenue"), "operating_income": cur.get("operating_income"),
                     "revenue_prev": prev.get("revenue"), "operating_income_prev": prev.get("operating_income")})
    rows.sort(key=lambda r: -(r["revenue"] or 0))
    res = {"segments": rows, "period": use[0][1][:4], "period_prev": use[1][1][:4] if len(use) > 1 else None,
           "fs_name": "연결" if fs == "CFS" else "별도"}
    SEG_CACHE[ck] = res
    return res


# ---------------------------------------------------------------- 미래 지속가능성 (규칙 기반)
def sustainability(corp_code, year, reprt, fs, rcept_no):
    h = history(corp_code, year, reprt, fs)
    years = [y for y in reversed(h["years"])]  # 오래된 → 최근
    D = h["data"]
    ser = lambda k: [D[y].get(k) for y in years]
    rev, oi, ni = ser("revenue"), ser("operating_income"), ser("net_income")
    liab, eq, ocf, capex = ser("liabilities"), ser("equity"), ser("ocf"), ser("capex")
    items = []

    def grade(label, g, text, value=""):
        items.append({"label": label, "grade": g, "text": text, "value": value})

    # 1) 성장 지속성
    rv = [(y, v) for y, v in zip(years, rev) if v]
    if len(rv) >= 3:
        span = int(rv[-1][0]) - int(rv[0][0])
        cagr = ((rv[-1][1] / rv[0][1]) ** (1 / span) - 1) * 100 if rv[0][1] > 0 and rv[-1][1] > 0 and span else None
        declines = sum(1 for a, b in zip(rv, rv[1:]) if b[1] < a[1])
        g = "상" if cagr is not None and cagr >= 7 and declines <= 1 else "하" if cagr is None or cagr < 0 else "중"
        grade("성장 지속성", g, f"최근 {span}년 매출 연평균 성장률 {cagr:+.1f}%, 역성장 {declines}회." if cagr is not None else "매출 추이를 계산할 수 없습니다.",
              f"CAGR {cagr:+.1f}%" if cagr is not None else "-")
    # 2) 수익 안정성
    mg = [o / r * 100 for o, r in zip(oi, rev) if o is not None and r]
    if len(mg) >= 3:
        avg = sum(mg) / len(mg)
        sd = (sum((m - avg) ** 2 for m in mg) / len(mg)) ** 0.5
        loss = sum(1 for m in mg if m < 0)
        g = "상" if loss == 0 and avg >= 5 and sd < 3 else "하" if loss >= 2 or avg < 2 else "중"
        grade("수익 안정성", g, f"영업이익률 평균 {avg:.1f}%, 변동폭(표준편차) {sd:.1f}%p, 적자 연도 {loss}회.", f"평균 {avg:.1f}%")
    # 3) 재무 건전성
    dr = [l / e * 100 for l, e in zip(liab, eq) if l is not None and e and e > 0]
    if dr:
        trend = dr[-1] - dr[0]
        g = "상" if dr[-1] < 100 and trend < 30 else "하" if dr[-1] > 200 or (eq[-1] is not None and eq[-1] <= 0) else "중"
        grade("재무 건전성", g, f"부채비율 {dr[0]:.0f}% → {dr[-1]:.0f}% ({'상승' if trend > 0 else '하락'} {abs(trend):.0f}%p).", f"부채비율 {dr[-1]:.0f}%")
    # 4) 현금 창출력
    oc = [v for v in ocf if v is not None]
    if len(oc) >= 3:
        neg = sum(1 for v in oc if v < 0)
        fcf = sum((o or 0) - abs(c or 0) for o, c in zip(ocf, capex) if o is not None)
        g = "상" if neg == 0 and fcf > 0 else "하" if neg >= 2 or fcf < 0 and neg >= 1 else "중"
        grade("현금 창출력", g, f"영업현금흐름 적자 {neg}회, {len(oc)}년 누적 잉여현금흐름(영업CF−설비투자) {fmt_won(fcf)}.", f"누적 FCF {fmt_won(fcf)}")
    # 5) 재투자
    cp = [(abs(c), o) for c, o in zip(capex, ocf) if c is not None and o]
    if len(cp) >= 3:
        reinv = sum(c for c, _ in cp) / sum(o for _, o in cp) * 100 if sum(o for _, o in cp) > 0 else None
        if reinv is None:
            grade("미래 투자", "하", "영업현금흐름이 누적 적자여서 재투자 여력이 부족합니다.", "-")
        else:
            g = "상" if 30 <= reinv <= 100 else "중"
            msg = ("벌어들인 현금의 상당 부분을 설비에 재투자하고 있습니다." if 30 <= reinv <= 100 else
                   "재투자 비중이 낮아 성장 투자가 제한적일 수 있습니다." if reinv < 30 else
                   "영업현금보다 많은 투자를 집행 중이라 외부 자금 의존도를 확인할 필요가 있습니다.")
            grade("미래 투자", g, f"영업현금흐름 대비 설비투자 비율 {reinv:.0f}%. {msg}", f"재투자율 {reinv:.0f}%")
    # 6) 사업 다각화
    seg = segments(rcept_no, reprt, fs) if rcept_no else {"error": "-"}
    if not seg.get("error") and seg["segments"]:
        tot = sum(max(r["revenue"] or 0, 0) for r in seg["segments"])
        top = seg["segments"][0]
        share = (top["revenue"] or 0) / tot * 100 if tot else 0
        ois = [r for r in seg["segments"] if r["operating_income"] is not None]
        oi_tot = sum(max(r["operating_income"], 0) for r in ois)
        oi_top = max(ois, key=lambda r: r["operating_income"]) if ois else None
        oi_share = oi_top["operating_income"] / oi_tot * 100 if oi_top and oi_tot > 0 else None
        n = len(seg["segments"])
        g = "하" if n == 1 or share >= 80 or (oi_share or 0) >= 85 else "상" if share < 50 and (oi_share is None or oi_share < 60) else "중"
        txt = f"{n}개 부문. 매출 최대 부문 '{top['name']}' 비중 {share:.0f}%"
        if oi_share is not None:
            txt += f", 영업이익 최대 부문 '{oi_top['name']}' 비중 {oi_share:.0f}%"
            if oi_share >= 60:
                txt += "로 이익이 한 부문에 집중되어 있습니다."
            else:
                txt += "."
        else:
            txt += "."
        grade("사업 다각화", g, txt, f"최대부문 {share:.0f}%")
    # 7) 인적 기반
    emp = employees(corp_code, year, reprt)
    if not emp.get("error") and emp["total"]["total"]:
        t = emp["total"]
        cr = t["contract"] / t["total"] * 100
        g = "상" if cr < 10 and (t["tenure"] or 0) >= 10 else "하" if cr >= 30 or (t["tenure"] or 99) < 5 else "중"
        grade("인적 기반", g, f"비정규직 비율 {cr:.1f}%, 평균 근속 {t['tenure'] if t['tenure'] is not None else '-'}년.", f"비정규 {cr:.1f}%")

    pts = {"상": 2, "중": 1, "하": 0}
    score = round(sum(pts[i["grade"]] for i in items) / (2 * len(items)) * 100) if items else None
    head = ("지속 성장 기반이 탄탄한 편입니다." if score is not None and score >= 70 else
            "전반적으로 무난하지만 일부 점검이 필요한 영역이 있습니다." if score is not None and score >= 45 else
            "중장기 지속가능성에 주의가 필요한 신호가 여러 영역에서 보입니다." if score is not None else "평가에 필요한 데이터가 부족합니다.")
    return {"score": score, "headline": head, "items": items,
            "strengths": [i["label"] for i in items if i["grade"] == "상"],
            "risks": [i["label"] for i in items if i["grade"] == "하"], "years": [years[0], years[-1]]}


# ---------------------------------------------------------------- 직원 현황
def employees(corp_code, year, reprt):
    try:
        d = json.loads(dart_get("empSttus.json", corp_code=corp_code, bsns_year=year, reprt_code=reprt))
    except Exception as e:  # noqa
        return {"error": str(e)}
    rows = d.get("list") or []
    if d.get("status") != "000" or not rows:
        return {"error": d.get("message", "직원 현황 데이터가 없습니다.")}

    def n(v):
        x = num(v)
        return x or 0

    divs, totals_by_sex = {}, {}
    for r in rows:
        div = re.sub(r"\s+", "", r.get("fo_bbm") or "") or "전체"
        sex = (r.get("sexdstn") or "").strip()
        rec = {
            "regular": n(r.get("rgllbr_co")),
            "regular_part": n(r.get("rgllbr_abacpt_labrr_co")),
            "contract": n(r.get("cnttk_co")),
            "contract_part": n(r.get("cnttk_abacpt_labrr_co")),
            "total": n(r.get("sm")),
            "tenure": num(r.get("avrg_cnwk_sdytrn")),
            "salary_total": num(r.get("fyer_salary_totamt")),
            "salary_avg": num(r.get("jan_salary_am")),
        }
        if rec["total"] == 0:
            rec["total"] = rec["regular"] + rec["contract"]
        if div in ("성별합계", "합계", "총계"):
            totals_by_sex[sex] = rec
            continue
        dv = divs.setdefault(div, {"name": div, "regular": 0, "contract": 0, "total": 0,
                                    "male": 0, "female": 0, "_ten": 0.0, "_tenw": 0})
        dv["regular"] += rec["regular"]
        dv["contract"] += rec["contract"]
        dv["total"] += rec["total"]
        if sex.startswith("남"):
            dv["male"] += rec["total"]
        elif sex.startswith("여"):
            dv["female"] += rec["total"]
        if rec["tenure"] is not None and rec["total"]:
            dv["_ten"] += rec["tenure"] * rec["total"]
            dv["_tenw"] += rec["total"]

    divisions = []
    for dv in divs.values():
        dv["tenure"] = round(dv["_ten"] / dv["_tenw"], 1) if dv["_tenw"] else None
        del dv["_ten"], dv["_tenw"]
        divisions.append(dv)
    divisions.sort(key=lambda x: -x["total"])

    # 전체 합계: 성별합계 행 우선, 없으면 부문 합산
    src = list(totals_by_sex.values())
    if src:
        tot = {k: sum(x[k] for x in src) for k in ("regular", "regular_part", "contract", "contract_part", "total")}
        tw = sum(x["total"] for x in src if x["tenure"] is not None)
        tot["tenure"] = round(sum(x["tenure"] * x["total"] for x in src if x["tenure"] is not None) / tw, 1) if tw else None
        st = [x["salary_total"] for x in src if x["salary_total"]]
        tot["salary_total"] = sum(st) if st else None
        tot["salary_avg"] = tot["salary_total"] / tot["total"] if st and tot["total"] else None
        tot["male"] = sum(x["total"] for s_, x in totals_by_sex.items() if s_.startswith("남"))
        tot["female"] = sum(x["total"] for s_, x in totals_by_sex.items() if s_.startswith("여"))
        by_sex = [{"sex": s_, **x} for s_, x in totals_by_sex.items()]
    else:
        tot = {k: sum(x[k] for x in divisions) for k in ("regular", "contract", "total", "male", "female")}
        tot.update(regular_part=None, contract_part=None, tenure=None, salary_total=None, salary_avg=None)
        by_sex = []
    return {"total": tot, "divisions": divisions, "by_sex": by_sex,
            "stlm_dt": rows[0].get("stlm_dt"), "rcept_no": rows[0].get("rcept_no")}


# ---------------------------------------------------------------- 요약 (규칙 기반)
def fmt_won(v):
    if v is None:
        return "-"
    a = abs(v)
    s = "-" if v < 0 else ""
    if a >= 1e12:
        return f"{s}{a / 1e12:,.1f}조원"
    if a >= 1e8:
        return f"{s}{a / 1e8:,.0f}억원"
    return f"{s}{a:,.0f}원"


def pct(a, b):
    if a is None or b in (None, 0):
        return None
    return a / b * 100


def growth(cur, prev):
    if cur is None or prev in (None, 0):
        return None
    return (cur - prev) / abs(prev) * 100


def g(key, k, i=0):
    v = key.get(k)
    return v[i] if v else None


def summarize(key, periods, cumulative):
    lines, tags = [], []
    rev, rev_p = g(key, "revenue"), g(key, "revenue", 1)
    op, op_p = g(key, "operating_income"), g(key, "operating_income", 1)
    ni, ni_p = g(key, "net_income"), g(key, "net_income", 1)
    period_lbl = "누적" if cumulative else f"{periods[0]}년"

    ratios = {
        "op_margin": pct(op, rev),
        "net_margin": pct(ni, rev),
        "debt_ratio": pct(g(key, "liabilities"), g(key, "equity")),
        "current_ratio": pct(g(key, "current_assets"), g(key, "current_liabilities")),
        "equity_ratio": pct(g(key, "equity"), g(key, "assets")),
        "roe": None if cumulative else pct(ni, ((g(key, "equity") or 0) + (g(key, "equity", 1) or g(key, "equity") or 0)) / 2 or None),
        "roa": None if cumulative else pct(ni, ((g(key, "assets") or 0) + (g(key, "assets", 1) or g(key, "assets") or 0)) / 2 or None),
        "rev_growth": growth(rev, rev_p),
        "op_growth": growth(op, op_p),
        "ni_growth": growth(ni, ni_p),
    }

    # 1) 성장성
    if rev is not None:
        gr = ratios["rev_growth"]
        s = f"{period_lbl} 매출액은 {fmt_won(rev)}"
        if gr is not None:
            s += f"으로 전년 동기 대비 {abs(gr):.1f}% {'증가' if gr >= 0 else '감소'}했습니다."
            tags.append(("매출 성장" if gr >= 5 else "매출 정체" if gr > -5 else "매출 감소", "good" if gr >= 5 else "neutral" if gr > -5 else "bad"))
        else:
            s += "입니다."
        lines.append(s)

    # 2) 수익성
    if op is not None:
        s = f"영업이익 {fmt_won(op)}"
        if op_p is not None:
            if op_p < 0 <= op:
                s += " (흑자 전환)"
                tags.append(("영업 흑자전환", "good"))
            elif op < 0 <= op_p:
                s += " (적자 전환)"
                tags.append(("영업 적자전환", "bad"))
            elif op < 0 and op_p < 0:
                s += " (적자 지속)"
                tags.append(("영업 적자지속", "bad"))
            elif ratios["op_growth"] is not None:
                s += f" (전년 대비 {ratios['op_growth']:+.1f}%)"
        if ratios["op_margin"] is not None:
            m = ratios["op_margin"]
            s += f", 영업이익률 {m:.1f}%로 " + ("높은 수익성을 보입니다." if m >= 15 else "양호한 수준입니다." if m >= 7 else "보통 수준입니다." if m >= 3 else "수익성이 낮습니다." if m >= 0 else "영업 손실 상태입니다.")
            if m >= 15:
                tags.append(("고수익성", "good"))
        else:
            s += "입니다."
        lines.append(s)
    if ni is not None:
        s = f"당기순이익은 {fmt_won(ni)}"
        if ratios["ni_growth"] is not None and ni_p is not None and ni_p > 0 and ni > 0:
            s += f"(전년 대비 {ratios['ni_growth']:+.1f}%)"
        if ratios["roe"] is not None:
            s += f", ROE {ratios['roe']:.1f}%"
        lines.append(s + "입니다.")

    # 3) 안정성
    dr, cr = ratios["debt_ratio"], ratios["current_ratio"]
    if dr is not None:
        s = f"부채비율 {dr:.0f}%"
        if cr is not None:
            s += f", 유동비율 {cr:.0f}%"
        if dr < 100 and (cr is None or cr >= 150):
            s += "로 재무구조가 매우 안정적입니다."
            tags.append(("재무 안정", "good"))
        elif dr < 200:
            s += "로 재무구조는 무난한 편입니다."
        else:
            s += "로 부채 부담이 큰 편이니 유의가 필요합니다."
            tags.append(("부채 부담", "bad"))
        lines.append(s)

    # 4) 현금흐름
    ocf, capex = g(key, "ocf"), g(key, "capex")
    if ocf is not None:
        s = f"영업활동현금흐름 {fmt_won(ocf)}"
        if capex is not None:
            fcf = ocf - abs(capex)
            ratios["fcf"] = fcf
            s += f", 유형자산 투자({fmt_won(abs(capex))})를 차감한 잉여현금흐름(FCF)은 {fmt_won(fcf)}"
        if ni and ni > 0 and ocf > 0:
            q = ocf / ni
            s += f". 순이익 대비 영업현금흐름 {q:.1f}배로 " + ("이익의 질이 양호합니다." if q >= 1 else "이익 대비 현금 창출이 다소 약합니다.")
        elif ocf < 0:
            s += ". 영업에서 현금이 유출되고 있어 점검이 필요합니다."
            tags.append(("영업현금 유출", "bad"))
        else:
            s += "입니다."
        lines.append(s)

    # 한 줄 총평
    score = sum(1 if t[1] == "good" else -1 if t[1] == "bad" else 0 for t in tags)
    headline = ("성장성과 수익성, 안정성이 고르게 양호한 실적입니다." if score >= 2 else
                "전반적으로 무난한 실적입니다." if score >= 0 else
                "실적 또는 재무구조에 주의가 필요한 신호가 있습니다.")
    return {"headline": headline, "lines": lines, "tags": [{"label": a, "tone": b} for a, b in tags], "ratios": ratios}


# ---------------------------------------------------------------- 주가·컨센서스·수주
import extras  # noqa: E402
extras.init(dart_get, fetch_statements, extract_key)


# ---------------------------------------------------------------- HTTP
NETS = {"file": os.environ.get("FIN_NETS_FILE", ""), "mtime": None, "nets": []}


def extra_nets():
    """대시보드가 기억하는 사내 대역 ({"nets": [...]}) — 사설망이 아닌 회사 대역(예: 65.3.0.0/16)도 허용"""
    try:
        mt = os.path.getmtime(NETS["file"])
    except OSError:
        return []
    if mt != NETS["mtime"]:
        nets = []
        try:
            with open(NETS["file"], encoding="utf-8") as f:
                for n in json.load(f).get("nets") or []:
                    try:
                        nets.append(ipaddress.ip_network(str(n), strict=False))
                    except ValueError:
                        pass
        except (OSError, ValueError):
            pass
        NETS.update(mtime=mt, nets=nets)
    return NETS["nets"]


def allowed(host):
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    if getattr(ip, "ipv4_mapped", None):
        ip = ip.ipv4_mapped
    return ip.is_loopback or ip.is_private or ip.is_link_local or any(ip in n for n in extra_nets())


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass                          # 대시보드가 띄울 때는 조용히 (오류만 finstagram.log)

    def send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")   # 대시보드(다른 포트)가 /version 으로 켜졌는지 확인
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        if not allowed(self.client_address[0]):
            return self.send(403, {"error": "사내망에서만 열립니다."})
        try:
            if u.path == "/version":
                return self.send(200, {"app": "finstagram", "ver": APP_VERSION, "key": bool(API_KEY or load_key()), "keyFile": key_file()})
            if u.path.startswith("/vendor/"):          # 차트 · 지구본 라이브러리와 그림 (CDN 대신)
                base = os.path.realpath(os.path.join(BASE, "vendor"))
                full = os.path.realpath(os.path.join(base, urllib.parse.unquote(u.path[len("/vendor/"):])))
                if not full.startswith(base + os.sep) or not os.path.isfile(full):
                    return self.send(404, {"error": "not found"})
                with open(full, "rb") as f:
                    return self.send(200, f.read(), mimetypes.guess_type(full)[0] or "application/octet-stream")
            if u.path in ("/", "/index.html"):
                with open(os.path.join(BASE, "index.html"), "rb") as f:
                    return self.send(200, f.read(), "text/html; charset=utf-8")
            if u.path == "/api/diag":
                return self.send(200, diag())
            if u.path == "/api/search":
                return self.send(200, search(q.get("q", "")))
            if u.path == "/api/segments":
                return self.send(200, segments(q["rcept_no"], q.get("reprt", "11011"), q.get("fs", "CFS")))
            if u.path == "/api/sustain":
                return self.send(200, sustainability(q["corp_code"], q["year"], q.get("reprt", "11011"), q.get("fs", "CFS"), q.get("rcept_no", "")))
            if u.path == "/api/stock":
                return self.send(200, extras.stock(q["stock_code"], q["corp_code"]))
            if u.path == "/api/quarters":
                return self.send(200, extras.quarters(q["corp_code"], q.get("stock_code", ""), q["year"], q.get("fs", "CFS")))
            if u.path == "/api/ir":
                return self.send(200, extras.ir_quarters(q["corp_code"]))
            if u.path == "/api/logo":
                lg = extras.logo(q.get("stock_code", ""), q.get("hm_url", ""))
                return self.send(200, lg[0], lg[1]) if lg else self.send(404, {"error": "no logo"})
            if u.path == "/api/weather":
                return self.send(200, extras.weather([x for x in q.get("names", "").split(",") if x]))
            if u.path == "/api/orders":
                return self.send(200, extras.orders(q["corp_code"]))
            if u.path == "/api/history":
                return self.send(200, history(q["corp_code"], q["year"], q.get("reprt", "11011"), q.get("fs", "CFS")))
            if u.path == "/api/fin":
                return self.send(200, build(q["corp_code"], q.get("year", ""), q.get("reprt", "11011"), q.get("fs", "")))
            self.send(404, {"error": "not found"})
        except Exception as e:  # noqa
            if isinstance(e, OSError) or "urlopen error" in str(e):   # 주가(네이버) · 컨센서스 · 날씨 등 바깥 사이트 연결 실패 → 이유를 한국어로
                host = {"/api/stock": "네이버 증권(fchart.stock.naver.com)", "/api/quarters": "컨센서스(navercomp.wisereport.co.kr)", "/api/weather": "날씨(api.open-meteo.com)",
                        "/api/ir": "삼성물산 IR(www.samsungcnt.com)", "/api/logo": "네이버(회사 로고)"}.get(u.path, "opendart.fss.or.kr")
                return self.send(500, {"error": net_reason(e, host)})
            self.send(500, {"error": str(e)})


if __name__ == "__main__":
    if proxy_url():
        urllib.request.install_opener(opener())   # extras(주가 · 날씨 …)도 같은 프록시
    print(f"재무스타그램 실행 중: http://localhost:{PORT} (주소 {HOST}) · 키 {'있음' if API_KEY else '없음 — ' + key_file()}", flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
