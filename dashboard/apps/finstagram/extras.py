# -*- coding: utf-8 -*-
"""주가 · 컨센서스 · 수주현황 (server.py 에서 init() 으로 의존성 주입)"""
import html
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (dart-dashboard)"}

dart_get = fetch_statements = extract_key = None


def init(_dart_get, _fetch_statements, _extract_key):
    global dart_get, fetch_statements, extract_key
    dart_get, fetch_statements, extract_key = _dart_get, _fetch_statements, _extract_key


def http_get(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def _num(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").strip()
    if s in ("", "-"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


# ================================================================ 주가
STOCK_CACHE = {}


def naver_finance(stock_code, period):
    """네이버 증권 실적(억원 단위) + 컨센서스. {key: {"cons": bool, "rows": {title: value}}}"""
    d = json.loads(http_get(f"https://m.stock.naver.com/api/stock/{stock_code}/finance/{period}"))
    info = d.get("financeInfo") or {}
    out = {}
    for t in info.get("trTitleList", []):
        out[t["key"]] = {"cons": t.get("isConsensus") == "Y", "rows": {}}
    for r in info.get("rowList", []):
        for k, c in (r.get("columns") or {}).items():
            if k in out:
                out[k]["rows"][r["title"]] = _num((c or {}).get("value"))
    return out


def stock(stock_code, corp_code):
    ck = (stock_code, time.strftime("%Y%m%d%H") + str(time.localtime().tm_min // 10))
    if ck in STOCK_CACHE:
        return STOCK_CACHE[ck]
    raw = http_get(f"https://fchart.stock.naver.com/sise.nhn?symbol={stock_code}&timeframe=day&count=1250&requestType=0")
    txt = raw.decode("cp949", "ignore")
    prices = []
    for m in re.finditer(r'data="(\d{8})\|([^"]+)"', txt):
        o, h, l, c, v = (float(x) if x not in ("", "null") else None for x in m.group(2).split("|"))
        d = m.group(1)
        prices.append([f"{d[:4]}-{d[4:6]}-{d[6:]}", o, h, l, c, v])
    if not prices:
        return {"error": "주가 정보를 불러오지 못했습니다."}
    res = {"prices": prices, "stock_code": stock_code}
    # 발행주식수 (DART)
    y = time.localtime().tm_year
    for by in (y - 1, y - 2):
        try:
            d = json.loads(dart_get("stockTotqySttus.json", corp_code=corp_code, bsns_year=str(by), reprt_code="11011"))
        except Exception:
            break
        rows = {r.get("se"): r for r in d.get("list", [])}
        if "보통주" in rows:
            res["shares_common"] = _num(rows["보통주"].get("istc_totqy"))
            res["treasury"] = _num(rows["보통주"].get("tesstk_co"))
            res["shares_pref"] = _num((rows.get("우선주") or {}).get("istc_totqy"))
            res["shares_date"] = rows["보통주"].get("stlm_dt")
            break
    # EPS / BPS (네이버, 컨센서스 포함)
    try:
        ann = naver_finance(stock_code, "annual")
        actual = [k for k, v in sorted(ann.items()) if not v["cons"]]
        cons = [k for k, v in sorted(ann.items()) if v["cons"]]
        if actual:
            a = ann[actual[-1]]["rows"]
            res["eps"], res["bps"], res["eps_year"] = a.get("EPS"), a.get("BPS"), actual[-1][:4]
        if cons:
            e = ann[cons[0]]["rows"]
            res["eps_e"], res["eps_e_year"] = e.get("EPS"), cons[0][:4]
    except Exception:
        pass
    STOCK_CACHE[ck] = res
    return res


# ================================================================ 분기 누적 + 컨센서스
import http.cookiejar  # noqa: E402

QTR_CACHE = {}
QTR_REPORTS = [("11013", 1), ("11012", 2), ("11014", 3), ("11011", 4)]
QTR_KEYS = [("revenue", "매출액"), ("operating_income", "영업이익"), ("net_income", "당기순이익"),
            ("net_income_owner", "당기순이익(지배)")]
WISE = "https://navercomp.wisereport.co.kr/v2/company"
WISE_CACHE = {}


def wise_finance(stock_code, fs, freq):
    """FnGuide(WiseReport) 주요재무정보. fs: CFS(IFRS연결) / OFS(IFRS별도), freq: Y/Q. 억원 단위.
    반환 {YYYYMM: {"cons": bool, "rows": {항목: 값}}}"""
    ck = (stock_code, fs, freq, time.strftime("%Y%m%d%H"))
    if ck in WISE_CACHE:
        return WISE_CACHE[ck]
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    main_url = f"{WISE}/c1010001.aspx?cmp_cd={stock_code}"
    op.addheaders = [("User-Agent", UA["User-Agent"]), ("Referer", main_url)]
    main = op.open(main_url, timeout=20).read().decode("utf-8", "ignore")
    enc = re.search(r"encparam: '([^']+)'", main)
    tid = re.search(r"id: '([^']*)' \?", main)
    if not enc:
        raise RuntimeError("컨센서스 페이지 형식이 바뀌었습니다.")
    qs = urllib.parse.urlencode({"cmp_cd": stock_code, "fin_typ": 4 if fs == "CFS" else 3, "freq_typ": freq,
                                 "extY": 0, "extQ": 0, "encparam": enc.group(1), "id": tid.group(1) if tid else ""})
    h = op.open(f"{WISE}/ajax/cF1001.aspx?{qs}", timeout=20).read().decode("utf-8", "ignore")
    out, cols = {}, []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", h, re.S | re.I):
        cells = [_clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S | re.I)]
        heads = [re.search(r"(\d{4})/(\d{2})\s*(\(E\))?", c) for c in cells]
        if sum(1 for m in heads if m) >= 3:
            cols = [(m.group(1) + m.group(2), bool(m.group(3))) if m else None for m in heads]
            cols = [c for c in cols if c]
            for k, e in cols:
                out[k] = {"cons": e, "rows": {}}
            continue
        if cols and cells:
            title, vals = cells[0].replace(" ", ""), cells[1:]
            if len(vals) >= len(cols):
                vals = vals[-len(cols):] if len(vals) > len(cols) else vals
                for (k, _), v in zip(cols, vals):
                    out[k]["rows"].setdefault(title, _num(v))
    WISE_CACHE[ck] = out
    return out


def quarters(corp_code, stock_code, year, fs="CFS"):
    """해당 연도 분기별 실적. DART 공시분은 실적, 미공시 분기는 같은 기준(연결/별도)의 FnGuide 컨센서스."""
    year, fs = str(year), (fs if fs in ("CFS", "OFS") else "CFS")
    ck = (corp_code, year, fs, time.strftime("%Y%m%d%H"))
    if ck in QTR_CACHE:
        return QTR_CACHE[ck]

    def load(rc):
        try:
            _, f, rows, _ = fetch_statements(corp_code, year, rc, fs)
        except Exception:
            return None
        if not rows:
            return None
        k = extract_key(rows, True)
        return {"fs": f, "vals": {m: (k.get(m) or [None])[0] for m, _ in QTR_KEYS}}

    with ThreadPoolExecutor(4) as ex:
        cum = dict(zip([q for _, q in QTR_REPORTS], ex.map(load, [r for r, _ in QTR_REPORTS])))

    qs, prev, filed_upto = [], {m: 0.0 for m, _ in QTR_KEYS}, 0
    for q in (1, 2, 3, 4):
        c = cum.get(q)
        if c and all(cum.get(p) for p in range(1, q)):
            vals = {}
            for m, _ in QTR_KEYS:
                cv = c["vals"].get(m)
                vals[m] = None if cv is None or prev[m] is None else cv - prev[m]
                prev[m] = cv
            qs.append({"q": q, "type": "actual", "vals": vals})
            filed_upto = q
        else:
            qs.append({"q": q, "type": None, "vals": {m: None for m, _ in QTR_KEYS}})

    res = {"year": year, "fs": fs, "filed_upto": filed_upto, "quarters": qs, "annual_cons": None,
           "cons_source": "FnGuide 컨센서스(WiseReport) · " + ("IFRS 연결" if fs == "CFS" else "IFRS 별도")}

    # DART 미공시 분기 중 회사가 IR로 이미 발표한 분기는 회사 발표(잠정) 실적 사용 — IR 자료는 연결 기준
    if filed_upto < 4 and fs == "CFS" and corp_code in IR_ADAPTERS:
        try:
            ir = ir_quarters(corp_code)
            irm = {(x["year"], x["q"]): x for x in ir.get("quarters", [])}
            for item in qs[filed_upto:]:
                x = irm.get((int(year), item["q"]))
                if x and x.get("revenue") is not None:
                    item["type"] = "ir"
                    item["vals"] = {m: x.get(m) for m, _ in QTR_KEYS}
                    item["source"] = x.get("source_report")
            res["ir_source"] = {"name": ir.get("source"), "page": ir.get("page")}
        except Exception as e:  # noqa
            res["ir_error"] = str(e)

    if filed_upto < 4 and stock_code:
        try:
            qn, an = wise_finance(stock_code, fs, "Q"), wise_finance(stock_code, fs, "Y")
        except Exception as e:
            qn, an = {}, {}
            res["cons_error"] = f"컨센서스를 불러오지 못했습니다: {e}"
        def pick(src, t):
            v = src["rows"].get(t)
            return src["rows"].get(t + "(발표기준)") if v is None else v
        has = lambda src: src and any(pick(src, t) is not None for _, t in QTR_KEYS[:2])
        to_won = 1e8  # 억원
        conv = lambda src: {m: (pick(src, t) * to_won if pick(src, t) is not None else None) for m, t in QTR_KEYS}
        annual_e = an.get(year + "12")
        if has(annual_e):
            res["annual_cons"] = conv(annual_e)
        for item in qs[filed_upto:]:
            src = qn.get(f"{year}{item['q'] * 3:02d}")
            if item["type"] is None and has(src):
                item["type"] = "consensus" if src["cons"] else "prelim"
                item["vals"] = conv(src)
        rest = [it for it in qs if it["type"] is None]
        if res["annual_cons"] and rest:
            for m, _ in QTR_KEYS:
                tot = res["annual_cons"].get(m)
                known = [it["vals"][m] for it in qs if it["type"] is not None]
                if tot is None or any(v is None for v in known):
                    continue
                for it in rest:
                    it["vals"][m] = (tot - sum(known)) / len(rest)
            for it in rest:
                it["type"] = "derived"
        if any(it["type"] is None for it in qs) and not res.get("cons_error"):
            res["cons_missing"] = f"{'연결' if fs == 'CFS' else '별도'} 기준 컨센서스가 제공되지 않는 분기가 있습니다."
    QTR_CACHE[ck] = res
    return res


# ================================================================ 수주현황
COUNTRIES = [
    # (표시명, 지도명, lon, lat, 별칭...)
    ("한국", "Korea", 127.8, 36.3, ["한국", "대한민국", "korea"]),
    ("카타르", "Qatar", 51.2, 25.3, ["카타르", "qatar", "dukhan"]),
    ("아랍에미리트", "United Arab Emirates", 54.3, 23.9, ["uae", "아랍에미리트", "아부다비", "두바이", "abu dhabi", "dubai", "fujairah", "푸자이라"]),
    ("사우디아라비아", "Saudi Arabia", 45.0, 24.0, ["사우디", "saudi", "riyadh", "리야드"]),
    ("쿠웨이트", "Kuwait", 47.6, 29.3, ["쿠웨이트", "kuwait"]),
    ("바레인", "Bahrain", 50.6, 26.0, ["바레인", "bahrain"]),
    ("오만", "Oman", 57.0, 21.0, ["오만", "oman"]),
    ("이라크", "Iraq", 43.7, 33.0, ["이라크", "iraq"]),
    ("이란", "Iran", 53.7, 32.4, ["이란", "iran"]),
    ("이스라엘", "Israel", 34.9, 31.0, ["이스라엘", "israel"]),
    ("요르단", "Jordan", 36.2, 31.2, ["요르단", "jordan"]),
    ("튀르키예", "Turkey", 35.2, 39.0, ["튀르키예", "터키", "turkey", "türkiye", "turkiye"]),
    ("이집트", "Egypt", 30.8, 26.8, ["이집트", "egypt"]),
    ("알제리", "Algeria", 2.6, 28.0, ["알제리", "algeria"]),
    ("리비아", "Libya", 17.2, 26.3, ["리비아", "libya"]),
    ("모로코", "Morocco", -7.1, 31.8, ["모로코", "morocco"]),
    ("나이지리아", "Nigeria", 8.7, 9.1, ["나이지리아", "nigeria"]),
    ("모잠비크", "Mozambique", 35.5, -18.7, ["모잠비크", "mozambique"]),
    ("남아프리카공화국", "South Africa", 24.0, -29.0, ["남아공", "남아프리카", "south africa"]),
    ("케냐", "Kenya", 37.9, 0.0, ["케냐", "kenya"]),
    ("가나", "Ghana", -1.0, 7.9, ["가나", "ghana"]),
    ("일본", "Japan", 138.3, 36.2, ["일본", "japan"]),
    ("중국", "China", 104.2, 35.9, ["중국", "china", "서안", "xian", "xi'an", "쑤저우", "suzhou"]),
    ("홍콩", "Hong Kong", 114.2, 22.3, ["홍콩", "hong kong"]),
    ("대만", "Taiwan", 121.0, 23.7, ["대만", "taiwan", "kaohsiung", "taoyuan", "타이베이", "taipei"]),
    ("몽골", "Mongolia", 103.8, 46.9, ["몽골", "mongolia"]),
    ("베트남", "Vietnam", 106.0, 16.0, ["베트남", "vietnam", "하노이", "hanoi", "호치민"]),
    ("필리핀", "Philippines", 122.0, 12.9, ["필리핀", "philippin"]),
    ("인도네시아", "Indonesia", 113.9, -0.8, ["인도네시아", "indonesia", "자카르타", "jakarta"]),
    ("말레이시아", "Malaysia", 102.0, 4.2, ["말레이시아", "말련", "malaysia", "kuala lumpur", "kl118", "petronas"]),
    ("싱가포르", "Singapore", 103.8, 1.35, ["싱가폴", "싱가포르", "singapore"]),
    ("태국", "Thailand", 101.0, 15.9, ["태국", "thailand", "방콕", "bangkok"]),
    ("미얀마", "Myanmar", 96.0, 21.9, ["미얀마", "myanmar"]),
    ("캄보디아", "Cambodia", 104.9, 12.6, ["캄보디아", "cambodia"]),
    ("방글라데시", "Bangladesh", 90.4, 23.7, ["방글라데시", "bangladesh", "dhaka"]),
    ("인도", "India", 78.9, 21.0, ["인도", "india", "noida", "노이다"]),
    ("파키스탄", "Pakistan", 69.3, 30.4, ["파키스탄", "pakistan"]),
    ("스리랑카", "Sri Lanka", 80.8, 7.9, ["스리랑카", "sri lanka"]),
    ("카자흐스탄", "Kazakhstan", 66.9, 48.0, ["카자흐", "kazakhstan"]),
    ("우즈베키스탄", "Uzbekistan", 64.6, 41.4, ["우즈베키", "uzbekistan"]),
    ("투르크메니스탄", "Turkmenistan", 59.6, 38.97, ["투르크메니", "turkmenistan"]),
    ("호주", "Australia", 134.0, -25.3, ["호주", "australia"]),
    ("뉴질랜드", "New Zealand", 172.0, -41.0, ["뉴질랜드", "new zealand"]),
    ("괌", "Guam", 144.8, 13.4, ["괌", "guam"]),
    ("미국", "United States", -98.6, 39.8, ["미국", "usa", "u.s.", "united states", "texas", "텍사스", "austin", "taylor", "테일러"]),
    ("캐나다", "Canada", -106.3, 56.1, ["캐나다", "canada"]),
    ("멕시코", "Mexico", -102.5, 23.6, ["멕시코", "mexico"]),
    ("파나마", "Panama", -80.8, 8.5, ["파나마", "panama"]),
    ("칠레", "Chile", -71.5, -35.7, ["칠레", "chile"]),
    ("페루", "Peru", -75.0, -9.2, ["페루", "peru"]),
    ("브라질", "Brazil", -51.9, -14.2, ["브라질", "brazil"]),
    ("콜롬비아", "Colombia", -74.3, 4.6, ["콜롬비아", "colombia"]),
    ("영국", "United Kingdom", -2.0, 54.0, ["영국", "united kingdom", "london"]),
    ("독일", "Germany", 10.4, 51.2, ["독일", "germany"]),
    ("프랑스", "France", 2.2, 46.2, ["프랑스", "france"]),
    ("네덜란드", "Netherlands", 5.3, 52.1, ["네덜란드", "netherlands"]),
    ("스페인", "Spain", -3.7, 40.5, ["스페인", "spain"]),
    ("이탈리아", "Italy", 12.6, 41.9, ["이탈리아", "italy"]),
    ("폴란드", "Poland", 19.1, 51.9, ["폴란드", "poland"]),
    ("헝가리", "Hungary", 19.5, 47.2, ["헝가리", "hungary"]),
    ("체코", "Czech Rep.", 15.5, 49.8, ["체코", "czech"]),
    ("루마니아", "Romania", 24.97, 45.9, ["루마니아", "romania", "cernavoda"]),
    ("노르웨이", "Norway", 8.5, 60.5, ["노르웨이", "norway"]),
    ("스웨덴", "Sweden", 18.6, 60.1, ["스웨덴", "sweden"]),
    ("러시아", "Russia", 105.3, 61.5, ["러시아", "russia"]),
    ("우크라이나", "Ukraine", 31.2, 48.4, ["우크라이나", "ukraine"]),
]
_ALIAS = sorted(((a.lower(), c) for c in COUNTRIES for a in c[4]), key=lambda x: -len(x[0]))


def find_country(text):
    t = (text or "").lower()
    if not t:
        return None
    for a, c in _ALIAS:
        if re.match(r"[a-z]", a):
            if re.search(r"(?<![a-z])" + re.escape(a), t):
                return c
        elif a in t:
            if a == "인도" and "인도네시아" in t:
                continue
            if a == "한국" and re.search(r"한국(은행|전력|수력|남부|가스|도로|토지|철도|수자원|석유|공항|조폐)", t):
                return c
            return c
    return None


def country_of_client(client):
    m = re.match(r"\s*[\(（]([^\)）]+)[\)）]", client or "")
    if m:
        c = find_country(m.group(1))
        if c:
            return c
    return find_country(client)


HANGUL = re.compile(r"[가-힣]")
KOREA = COUNTRIES[0]


def _clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


CELL_RE = re.compile(r"<(TD|TH|TE|TU)\b([^>]*)>(.*?)</\1>", re.S | re.I)


def table_grid(tbl):
    rows, pending = [], {}
    for tr in re.findall(r"<TR\b[^>]*>(.*?)</TR>", tbl, re.S | re.I):
        cells = CELL_RE.findall(tr)
        row, col, ci = [], 0, 0
        while ci < len(cells) or col in pending:
            if col in pending:
                rem, txt = pending[col]
                row.append(txt)
                if rem > 1:
                    pending[col] = (rem - 1, txt)
                else:
                    del pending[col]
                col += 1
                continue
            _, attrs, inner = cells[ci]
            ci += 1
            txt = _clean(inner)
            rs = int((re.search(r'ROWSPAN="(\d+)"', attrs, re.I) or [0, 1])[1])
            cs = int((re.search(r'COLSPAN="(\d+)"', attrs, re.I) or [0, 1])[1])
            for _ in range(cs):
                row.append(txt)
                if rs > 1:
                    pending[col] = (rs - 1, txt)
                col += 1
        rows.append(row)
    return rows


def unit_of(before):
    m = list(re.finditer(r"단위\s*[:：]?\s*([^)\]<]{1,12})", before))
    if not m:
        return 1e6, "KRW"
    u = m[-1].group(1).replace(" ", "")
    cur = "USD" if ("달러" in u or "USD" in u.upper() or "$" in u) else "KRW"
    for k, v in (("조", 1e12), ("십억", 1e9), ("억", 1e8), ("백만", 1e6), ("천", 1e3)):
        if k in u:
            return v, cur
    return 1.0, cur


def _col(header, *keys, exclude=()):
    for i, h in enumerate(header):
        hh = h.replace(" ", "")
        if any(k in hh for k in keys) and not any(x in hh for x in exclude):
            return i
    return None


def parse_orders_doc(xml):
    tables = [(m.start(), m.group(0)) for m in re.finditer(r"<TABLE\b.*?</TABLE>", xml, re.S | re.I)]
    best = None
    for pos, tbl in tables:
        flat = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", tbl[:6000]))
        if "잔" not in flat or ("공사명" not in flat and "현장명" not in flat and "프로젝트" not in flat):
            continue
        g = table_grid(tbl)
        if len(g) < 3:
            continue
        hi = None
        for i in range(min(3, len(g))):
            hh = "".join(g[i]).replace(" ", "")
            if ("공사명" in hh or "현장명" in hh or "프로젝트" in hh) and ("잔액" in hh or "잔고" in hh):
                hi = i
                break
        if hi is None:
            continue
        h = g[hi]
        cols = {
            "name": _col(h, "공사명", "현장명", "프로젝트명", "프로젝트"),
            "client": _col(h, "발주처", "발주자", "고객"),
            "date": _col(h, "계약일", "수주일", "착공"),
            "end": _col(h, "완공", "준공", "납기", "종료"),
            "amount": _col(h, "도급액", "도급금액", "계약금액", "수주총액", "수주금액", "계약액", exclude=("잔",)),
            "done": _col(h, "완성공사", "기납품", "기성", "누적"),
            "remain": _col(h, "잔액", "잔고"),
            "cat": _col(h, "품목", "구분", "부문"),
        }
        if cols["name"] is None or cols["remain"] is None or cols["amount"] is None:
            continue
        unit, cur = unit_of(xml[max(0, pos - 1500):pos])
        if cur != "KRW":
            continue
        projects, totals, last_cat = [], [], ""
        for r in g[hi + 1:]:
            def cell(k):
                i = cols[k]
                return r[i] if i is not None and i < len(r) else ""
            name, client, cat = cell("name"), cell("client"), cell("cat")
            amt, rem = _num(cell("amount")), _num(cell("remain"))
            joined = "".join(r).replace(" ", "")
            if "합계" in joined or "소계" in joined:
                if amt is not None or rem is not None:
                    # 금액 칸이 밀린 합계행 대비: 마지막 숫자 3개
                    nums = [x for x in (_num(c) for c in r) if x is not None]
                    totals.append({"label": cat if cat and "합계" not in cat.replace(" ", "") else (last_cat or "합계"),
                                   "grand": "총합계" in joined, "amount": (nums[-3] if len(nums) >= 3 else amt) * unit if nums else None,
                                   "remain": (nums[-1] * unit) if nums else None})
                continue
            if amt is None or not name:
                continue
            last_cat = cat if cat and "합계" not in cat.replace(" ", "") else last_cat
            if client.strip() in ("기타", "-") or name.startswith("기타"):
                last_cat = cat if cat and "합계" not in cat.replace(" ", "") else last_cat
                totals.append({"label": "기타", "other": True, "amount": amt * unit, "remain": (rem or 0) * unit})
                continue
            dt = cell("date")
            ym = re.search(r"(19|20)\d{2}", dt)
            projects.append({
                "cat": cat, "client": client, "name": name, "date": dt, "year": int(ym.group(0)) if ym else None,
                "end": cell("end"), "amount": amt * unit,
                "done": (_num(cell("done")) or 0) * unit if cols["done"] is not None else None,
                "remain": (rem or 0) * unit,
            })
        if projects and (best is None or len(projects) > len(best["projects"])):
            best = {"projects": projects, "totals": totals}
    if not best:
        return None
    grand = [t for t in best["totals"] if t.get("grand")]
    subs = [t for t in best["totals"] if not t.get("grand") and not t.get("other")]
    if grand:
        total = grand[-1]
    elif len(subs) == 1:
        total = subs[0]
    else:
        total = {"amount": sum(p["amount"] for p in best["projects"]) + sum(t["amount"] for t in best["totals"] if t.get("other")),
                 "remain": sum(p["remain"] for p in best["projects"]) + sum(t["remain"] for t in best["totals"] if t.get("other"))}
    by_cat = [{"label": t["label"], "amount": t["amount"], "remain": t["remain"]} for t in subs if t["label"] != "합계"] if grand else []
    for p in best["projects"]:
        exec_c = find_country(p["name"]) or country_of_client(p["client"]) or KOREA
        cl = country_of_client(p["client"])
        if not cl:
            cl = KOREA if HANGUL.search(p["client"] or "") and exec_c is KOREA else exec_c
        p["exec"], p["order"] = exec_c[0], cl[0]
    other = [t for t in best["totals"] if t.get("other")]
    return {"projects": best["projects"], "total_amount": total.get("amount"), "total_remain": total.get("remain"),
            "by_cat": by_cat, "other_amount": sum(t["amount"] for t in other), "other_remain": sum(t["remain"] for t in other)}


def annual_reports(corp_code, n=5):
    y = time.localtime().tm_year
    d = json.loads(dart_get("list.json", corp_code=corp_code, bgn_de=f"{y - n - 1}0101", pblntf_detail_ty="A001", page_count="100"))
    out = {}
    for it in d.get("list", []):
        m = re.search(r"\((\d{4})\.\d{2}\)", it.get("report_nm", ""))
        if not m or "첨부" in it.get("report_nm", ""):
            continue
        yr = m.group(1)
        if yr not in out or it["rcept_no"] > out[yr]:
            out[yr] = it["rcept_no"]
    return dict(sorted(out.items())[-n:])


def doc_orders(rcept_no):
    p = os.path.join(CACHE_DIR, f"orders_{rcept_no}.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    raw = dart_get("document.xml", rcept_no=rcept_no)
    res = None
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = sorted(z.namelist(), key=lambda n: ("_" in os.path.basename(n), len(n)))
            b = z.read(names[0])
    except zipfile.BadZipFile:
        return None
    head = b[:200].lower()
    xml = b.decode("cp949" if (b"euc-kr" in head or b"ks_c" in head) else "utf-8", "ignore")
    res = parse_orders_doc(xml) or {"projects": [], "none": True}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    return res


ORD_CACHE = {}


def orders(corp_code):
    if corp_code in ORD_CACHE:
        return ORD_CACHE[corp_code]
    reps = annual_reports(corp_code)
    if not reps:
        return {"error": "사업보고서를 찾지 못했습니다."}
    with ThreadPoolExecutor(5) as ex:
        docs = dict(zip(reps.keys(), ex.map(doc_orders, reps.values())))
    years = []
    union = {}
    for yr in sorted(docs):
        d = docs[yr]
        if not d or d.get("none"):
            continue
        years.append({"year": int(yr), "rcept_no": reps[yr], "total_amount": d.get("total_amount"),
                      "total_remain": d.get("total_remain"), "by_cat": d.get("by_cat", []),
                      "n_projects": len(d["projects"])})
        for p in d["projects"]:
            k = (re.sub(r"[\s\(\)（）㈜(주)]", "", p["client"])[:12], re.sub(r"\s", "", p["name"]))
            union[k] = dict(p, last_seen=int(yr))
    if not years:
        return {"error": "사업보고서에서 프로젝트별 수주현황 표를 찾지 못했습니다."}
    latest = years[-1]["year"]
    projects = sorted(union.values(), key=lambda p: -(p["amount"] or 0))
    for p in projects:
        p["active"] = p["last_seen"] == latest
        if not p["active"]:
            p["remain"] = 0
    # 계약연도별 신규 수주
    first = years[0]["year"]
    intake = {}
    for p in projects:
        y = p.get("year")
        if not y or y < first:
            continue
        e = intake.setdefault(y, {"year": y, "amount": 0, "domestic": 0, "overseas": 0, "count": 0})
        e["amount"] += p["amount"]
        e["count"] += 1
        e["overseas" if p["exec"] != "한국" else "domestic"] += p["amount"]
    cinfo = {c[0]: {"name": c[0], "map": c[1], "lon": c[2], "lat": c[3]} for c in COUNTRIES}
    return_data = {
        "years": years, "intake": [intake[y] for y in sorted(intake)], "projects": projects,
        "countries": cinfo, "latest": latest, "first": first,
        "other_latest": {"amount": docs[str(latest)].get("other_amount"), "remain": docs[str(latest)].get("other_remain")},
    }
    ORD_CACHE[corp_code] = return_data
    return return_data


# ================================================================ 현지 시각 · 날씨
# 국가 → (IANA 시간대, 대표 도시, 위도, 경도)  · 미국/호주/캐나다처럼 시간대가 여러 개인 나라는 대표 도시 기준
TZ = {
    "한국": ("Asia/Seoul", "서울", 37.57, 126.98), "카타르": ("Asia/Qatar", "도하", 25.29, 51.53),
    "아랍에미리트": ("Asia/Dubai", "아부다비", 24.45, 54.38), "사우디아라비아": ("Asia/Riyadh", "리야드", 24.71, 46.68),
    "쿠웨이트": ("Asia/Kuwait", "쿠웨이트시티", 29.38, 47.99), "바레인": ("Asia/Bahrain", "마나마", 26.23, 50.59),
    "오만": ("Asia/Muscat", "무스카트", 23.59, 58.41), "이라크": ("Asia/Baghdad", "바그다드", 33.31, 44.36),
    "이란": ("Asia/Tehran", "테헤란", 35.69, 51.39), "이스라엘": ("Asia/Jerusalem", "텔아비브", 32.09, 34.78),
    "요르단": ("Asia/Amman", "암만", 31.95, 35.93), "튀르키예": ("Europe/Istanbul", "이스탄불", 41.01, 28.98),
    "이집트": ("Africa/Cairo", "카이로", 30.04, 31.24), "알제리": ("Africa/Algiers", "알제", 36.75, 3.06),
    "리비아": ("Africa/Tripoli", "트리폴리", 32.89, 13.19), "모로코": ("Africa/Casablanca", "카사블랑카", 33.57, -7.59),
    "나이지리아": ("Africa/Lagos", "라고스", 6.52, 3.38), "모잠비크": ("Africa/Maputo", "마푸투", -25.97, 32.57),
    "남아프리카공화국": ("Africa/Johannesburg", "요하네스버그", -26.2, 28.05), "케냐": ("Africa/Nairobi", "나이로비", -1.29, 36.82),
    "가나": ("Africa/Accra", "아크라", 5.6, -0.19), "일본": ("Asia/Tokyo", "도쿄", 35.68, 139.69),
    "중국": ("Asia/Shanghai", "상하이", 31.23, 121.47), "홍콩": ("Asia/Hong_Kong", "홍콩", 22.32, 114.17),
    "대만": ("Asia/Taipei", "타이베이", 25.03, 121.57), "몽골": ("Asia/Ulaanbaatar", "울란바토르", 47.89, 106.91),
    "베트남": ("Asia/Ho_Chi_Minh", "하노이", 21.03, 105.85), "필리핀": ("Asia/Manila", "마닐라", 14.6, 120.98),
    "인도네시아": ("Asia/Jakarta", "자카르타", -6.21, 106.85), "말레이시아": ("Asia/Kuala_Lumpur", "쿠알라룸푸르", 3.14, 101.69),
    "싱가포르": ("Asia/Singapore", "싱가포르", 1.35, 103.82), "태국": ("Asia/Bangkok", "방콕", 13.76, 100.5),
    "미얀마": ("Asia/Yangon", "양곤", 16.87, 96.2), "캄보디아": ("Asia/Phnom_Penh", "프놈펜", 11.56, 104.93),
    "방글라데시": ("Asia/Dhaka", "다카", 23.81, 90.41), "인도": ("Asia/Kolkata", "뉴델리", 28.61, 77.21),
    "파키스탄": ("Asia/Karachi", "카라치", 24.86, 67.0), "스리랑카": ("Asia/Colombo", "콜롬보", 6.93, 79.86),
    "카자흐스탄": ("Asia/Almaty", "알마티", 43.24, 76.89), "우즈베키스탄": ("Asia/Tashkent", "타슈켄트", 41.3, 69.24),
    "투르크메니스탄": ("Asia/Ashgabat", "아시가바트", 37.96, 58.33), "호주": ("Australia/Sydney", "시드니", -33.87, 151.21),
    "뉴질랜드": ("Pacific/Auckland", "오클랜드", -36.85, 174.76), "괌": ("Pacific/Guam", "괌", 13.44, 144.79),
    "미국": ("America/Chicago", "텍사스(오스틴)", 30.27, -97.74), "캐나다": ("America/Vancouver", "밴쿠버", 49.28, -123.12),
    "멕시코": ("America/Mexico_City", "멕시코시티", 19.43, -99.13), "파나마": ("America/Panama", "파나마시티", 8.98, -79.52),
    "칠레": ("America/Santiago", "산티아고", -33.45, -70.67), "페루": ("America/Lima", "리마", -12.05, -77.04),
    "브라질": ("America/Sao_Paulo", "상파울루", -23.55, -46.63), "콜롬비아": ("America/Bogota", "보고타", 4.71, -74.07),
    "영국": ("Europe/London", "런던", 51.51, -0.13), "독일": ("Europe/Berlin", "베를린", 52.52, 13.4),
    "프랑스": ("Europe/Paris", "파리", 48.86, 2.35), "네덜란드": ("Europe/Amsterdam", "암스테르담", 52.37, 4.9),
    "스페인": ("Europe/Madrid", "마드리드", 40.42, -3.7), "이탈리아": ("Europe/Rome", "로마", 41.9, 12.5),
    "폴란드": ("Europe/Warsaw", "바르샤바", 52.23, 21.01), "헝가리": ("Europe/Budapest", "부다페스트", 47.5, 19.04),
    "체코": ("Europe/Prague", "프라하", 50.08, 14.44), "루마니아": ("Europe/Bucharest", "부쿠레슈티", 44.43, 26.1),
    "노르웨이": ("Europe/Oslo", "오슬로", 59.91, 10.75), "스웨덴": ("Europe/Stockholm", "스톡홀름", 59.33, 18.07),
    "러시아": ("Europe/Moscow", "모스크바", 55.76, 37.62), "우크라이나": ("Europe/Kyiv", "키이우", 50.45, 30.52),
}
WX_CACHE = {}


def weather(names):
    """국가별 대표 도시 현재 날씨 (Open-Meteo, API 키 불필요). 30분 캐시."""
    names = [n for n in dict.fromkeys(names) if n in TZ]
    slot = int(time.time() // 1800)
    need = [n for n in names if WX_CACHE.get(n, (None, -1))[1] != slot]
    if need:
        lat = ",".join(str(TZ[n][2]) for n in need)
        lon = ",".join(str(TZ[n][3]) for n in need)
        d = json.loads(http_get("https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode({
            "latitude": lat, "longitude": lon, "current": "temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m",
            "timezone": "auto"})))
        d = d if isinstance(d, list) else [d]
        for n, x in zip(need, d):
            c = x.get("current") or {}
            WX_CACHE[n] = ({"temp": c.get("temperature_2m"), "code": c.get("weather_code"),
                            "humidity": c.get("relative_humidity_2m"), "wind": c.get("wind_speed_10m")}, slot)
    return {n: dict(WX_CACHE[n][0], tz=TZ[n][0], city=TZ[n][1]) if n in WX_CACHE else {"tz": TZ[n][0], "city": TZ[n][1]}
            for n in names}


# ================================================================ 회사 CI(로고)
def logo(stock_code, hm_url):
    """상장사: 네이버 증권 종목 로고(SVG) · 비상장: 홈페이지 파비콘. 디스크 캐시. 없으면 None."""
    key = re.sub(r"\W", "", stock_code or "") or re.sub(r"\W", "_", hm_url or "")[:60]
    if not key:
        return None
    for ext, ct in ((".svg", "image/svg+xml"), (".png", "image/png")):
        p = os.path.join(CACHE_DIR, f"logo_{key}{ext}")
        if os.path.exists(p):
            return (open(p, "rb").read(), ct) if os.path.getsize(p) else None
    data, ext, ct = None, ".png", "image/png"
    try:
        if stock_code:
            b = http_get(f"https://ssl.pstatic.net/imgstock/fn/real/logo/stock/Stock{stock_code}.svg", timeout=10)
            if b.lstrip().startswith(b"<svg"):
                data, ext, ct = b, ".svg", "image/svg+xml"
        if not data and hm_url:
            dom = urllib.parse.urlparse(hm_url if "://" in hm_url else "http://" + hm_url).hostname
            if dom:
                b = http_get(f"https://www.google.com/s2/favicons?domain={dom}&sz=128", timeout=10)
                if len(b) > 400:  # 기본 지구본 아이콘(작은 파일) 제외
                    data = b
    except Exception:
        pass
    with open(os.path.join(CACHE_DIR, f"logo_{key}{ext}"), "wb") as f:
        f.write(data or b"")
    return (data, ct) if data else None


# ================================================================ 회사 IR 실적발표 (분기 사업부문별)
# 회사마다 IR 사이트 구조가 달라 회사별 어댑터를 등록한다. 어댑터는 [(year, q, pdf_url)] 를 돌려준다.
IR_DIR = os.path.join(CACHE_DIR, "ir")
os.makedirs(IR_DIR, exist_ok=True)
NUM_TOK = re.compile(r"^[△+\-]?[\d,]+(\.\d+)?$")
PER_TOK = re.compile(r"^'(\d{2})\.(\d)\s*(?:Q|분기)$")
UNIT_MULT = {"십억원": 1e9, "억원": 1e8, "백만원": 1e6}


def _ir_num(t):
    t = t.replace(",", "").replace(" ", "")
    if t in ("-", ""):
        return 0.0
    neg = t.startswith("△") or t.startswith("-")
    return -float(t.lstrip("△+-")) if neg else float(t.lstrip("+"))


def parse_ir_results_page(text):
    """'구분 | 당분기 | 전분기 | 전년동기 ...' 형식의 실적 요약 페이지 → {(y,q): {...}}"""
    # 각주 표시('*', '**')가 별도 토큰으로 떨어지는 경우가 있어 제거
    toks = [t.strip() for t in text.split("\n") if t.strip() and not re.fullmatch(r"\*+", t.strip())]
    pers = []
    for t in toks[:40]:
        m = PER_TOK.match(t)
        if m:
            pers.append((2000 + int(m.group(1)), int(m.group(2))))
    if len(pers) < 3 or "매출" not in toks or not any(t.startswith("영업이익") for t in toks):
        return None
    unit = next((v for k, v in UNIT_MULT.items() if f"({k})" in text), 1e9)
    cols = {0: pers[0], 1: pers[1], 3: pers[2]}  # 값 순서: 당분기, 전분기, 증감, 전년동기, 증감, ...
    out = {p: {"segments": {}, "oi_segments": {}} for p in cols.values()}
    section, i = None, 0
    while i < len(toks):
        label = toks[i].rstrip("*").strip()
        j = i + 1
        if label == "영업이익" and j < len(toks) and toks[j].startswith("(") and not NUM_TOK.match(toks[j].strip("()")):
            j += 1  # '(영업이익률)' 머리글
        vals = []
        while j < len(toks) and (NUM_TOK.match(toks[j].replace(" ", "")) or toks[j] == "-"):
            vals.append(_ir_num(toks[j]))
            j += 1
        if not vals or NUM_TOK.match(label.replace(" ", "")) or label.startswith("("):
            i += 1
            continue
        key = {"매출": "revenue", "매출이익": "gross", "영업이익": "operating_income", "당기순이익": "net_income",
               "└지배지분순이익": "net_income_owner", "지배지분순이익": "net_income_owner"}.get(label)
        if label == "매출":
            section = "rev"
        elif label == "영업이익":
            section = "oi"
        elif key or label in ("판관비", "기타손익", "금융손익", "지분법손익", "세전이익"):
            section = None
        for idx, per in cols.items():
            if idx < len(vals):
                v = vals[idx] * unit
                if key:
                    out[per][key] = v
                elif section == "rev":
                    out[per]["segments"][label] = v
                elif section == "oi":
                    out[per]["oi_segments"][label] = v
        i = j
    if not any(o["segments"] for o in out.values()):
        return None
    return out


def ir_pdf_results(pdf_bytes):
    try:
        import pymupdf
    except ImportError:
        raise RuntimeError("PDF 분석에 PyMuPDF가 필요합니다: pip install pymupdf")
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    for page in doc:
        t = page.get_text()
        if "구분" in t and "매출" in t and "영업이익" in t:
            r = parse_ir_results_page(t)
            if r:
                return r
    return None


def _ir_samsungcnt(years):
    base = "https://www.samsungcnt.com"
    found = []
    for y in years:
        h = http_get(f"{base}/ir/event-earnings/li/earnings-release.do?event_year={y}").decode("utf-8", "ignore")
        for tag in re.findall(r"<a\b[^>]*>", h, re.S):
            if 'data-ga-filetype="report"' not in tag:
                continue
            href = re.search(r'href="([^"]+)"', tag)
            yy = re.search(r'data-ga-year="(\d{4})"', tag)
            qq = re.search(r'data-ga-quarter="(\d)"', tag)
            if href and yy and qq:
                found.append((int(yy.group(1)), int(qq.group(1)), base + html.unescape(href.group(1))))
    return found


IR_ADAPTERS = {
    "00149655": {"name": "삼성물산 IR 실적발표", "page": "https://www.samsungcnt.com/ir/event-earnings/earnings-release.do",
                 "list": _ir_samsungcnt},
}
IR_CACHE = {}


def ir_quarters(corp_code, n_years=3):
    """회사 IR 실적발표 자료의 분기 실적(사업부문별 매출·영업이익). 지원 회사가 아니면 supported=False."""
    ad = IR_ADAPTERS.get(corp_code)
    if not ad:
        return {"supported": False}
    ck = (corp_code, time.strftime("%Y%m%d%H"))
    if ck in IR_CACHE:
        return IR_CACHE[ck]
    y = time.localtime().tm_year
    reports = sorted(ad["list"](range(y - n_years + 1, y + 1)))
    quarters, sources, errors = {}, [], []

    def one(rep):
        yy, qq, url = rep
        p = os.path.join(IR_DIR, f"{corp_code}_{yy}Q{qq}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return rep, json.load(f)
        res = ir_pdf_results(http_get(url, timeout=60))
        data = {f"{k[0]}Q{k[1]}": v for k, v in (res or {}).items()}
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return rep, data

    with ThreadPoolExecutor(4) as ex:
        results = list(ex.map(lambda r: _safe(one, r), reports))
    for rep, data in results:  # 오래된 보고서부터 → 최신 보고서 값(재작성 반영)이 덮어씀
        if isinstance(data, Exception):
            errors.append(f"{rep[0]}년 {rep[1]}분기: {data}")
            continue
        sources.append({"year": rep[0], "q": rep[1], "url": rep[2]})
        for k, v in data.items():
            yy, qq = map(int, k.split("Q"))
            quarters[(yy, qq)] = dict(v, year=yy, q=qq, source_report=f"{rep[0]}년 {rep[1]}분기 실적발표")
    res = {"supported": True, "source": ad["name"], "page": ad["page"], "unit": "원",
           "quarters": [quarters[k] for k in sorted(quarters)], "reports": sources, "errors": errors}
    IR_CACHE[ck] = res
    return res


def _safe(fn, rep):
    try:
        return fn(rep)
    except Exception as e:  # noqa
        return rep, e
