# -*- coding: utf-8 -*-
"""계장도서검토 — 공용 도서관 API (/api/books/…)   표준 라이브러리만 사용

부서장(운영자)이 서버 PC 의 도서 폴더 경로를 정해 두면
  · 그 폴더의 책 파일 목록 · 원본 파일을 부서원 화면(미리보기 · 원본 열기)에 내주고
  · 운영자 브라우저가 뽑은 본문 색인(책 1권 = gzip JSON 1개)을 받아 보관했다가
  · 부서원 브라우저가 내려받아 각자 PC 에서 검색한다 (검색 계산은 서버가 하지 않음 → 서버 부담 없음)

server.py 연결 (3 곳):
  import books_api
  books_api.setup(P=P, LOCK=LOCK, ApiError=ApiError, read_json=read_json, write_json=write_json)   # main() 에서 ROOT 정한 뒤
  if head == 'books': return books_api.handle(self, m, seg[1:], q)                                # Handler.api() 안
저장 위치: 운영 폴더 books/config.json (폴더 경로 · 관리자) · books/index/<id>.json.gz (책 색인) · books/index/manifest.json (목록)
"""
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import quote

SUPPORTED = {'.pdf': 'application/pdf', '.epub': 'application/epub+zip',
             '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
             '.hwpx': 'application/octet-stream', '.txt': 'text/plain; charset=utf-8', '.md': 'text/plain; charset=utf-8'}
ID_RE = re.compile(r'^[0-9a-f]{24}$')
MAX_FILES = 20000
MAX_BOOK_JSON = 400 * 1024 * 1024        # 풀었을 때 크기 상한 (3,000쪽 책도 수십 MB)
X = {}                                   # setup() 이 넣는 server.py 의 도구들

# ---------------------------------------------------------------- 번역 (선택 기능 — 운영자가 켜야 동작)
# 고른 글을 Claude(Anthropic API)로 한국어 번역. 글이 회사 밖(Anthropic)으로 나가므로 기본은 꺼짐.
# 켜기 · API 키 · 모델은 운영자(서버 PC)만 [📚 도서관] 화면에서 정함 → books/config.json 의 translate (키는 화면에 다시 내보내지 않음)
# 같은 글은 books/tcache/ 에 보관해 다시 보내지 않음 (부서원끼리 공유).
API_URL = os.environ.get('BOOKS_ANTHROPIC_URL', 'https://api.anthropic.com/v1/messages')   # 시험할 때만 바꿈
API_VERSION = '2026-10-21'
DEFAULT_MODEL = 'claude-opus-5-5'
MAX_TR_CHARS = 12000                      # 한 번에 번역할 글 길이 상한 (쪽 하나 · 고른 글)
TR_SEM = threading.Semaphore(3)          # 동시에 API 로 보내는 번역 수
TR_SYSTEM = """You translate passages from technical books for Korean instrumentation & control (계장, I&C) engineers at an EPC power/plant company.

Translate the user's passage into natural, precise Korean as a senior Korean I&C engineer would write it.

Rules:
- Output only the Korean translation. No preface, no notes, no quotation marks around the whole text.
- Keep the paragraph and line structure of the source (one output line per source line where reasonable; keep bullets, numbering and table-like rows aligned).
- Keep unchanged: instrument tags (PT-101, FIT-2001A, LT-2001), model numbers, units (mA, kPa, °C, bar), numbers, formulas, code, standard names (IEC 61511, ISA-5.1), protocol and product names (HART, Modbus, Foundation Fieldbus, PROFIBUS, OPC UA, DCS, PLC, SIS, SIL).
- For key technical terms, use the established Korean term and add the English in parentheses the first time it appears in the passage, e.g. 전송기(Transmitter), 차압 전송기(DP Transmitter), 포지셔너(Positioner). Use the glossary below.
- If the passage is not in English (Portuguese, Spanish, Russian, Vietnamese, ...), translate it into Korean the same way.
- If a part is garbled PDF text, translate what is understandable and keep the rest as is.

Glossary (English -> Korean):
transmitter 전송기 | pressure transmitter 압력 전송기 | differential pressure (DP) transmitter 차압 전송기 | temperature transmitter 온도 전송기 | level transmitter 레벨 전송기 | flow transmitter 유량 전송기
sensor 센서 | transducer 변환기 | primary element 1차 요소 | thermocouple 열전대 | RTD 측온저항체 | cold junction 냉접점 | thermowell 써모웰(보호관)
flowmeter 유량계 | orifice plate 오리피스 판 | magnetic flowmeter 전자식 유량계 | Coriolis meter 코리올리 유량계 | vortex flowmeter 와류 유량계 | level gauge 레벨 게이지 | displacer 디스플레이서
control valve 제어밸브(조절밸브) | positioner 포지셔너 | actuator 액추에이터(구동부) | valve trim 밸브 트림 | fail open/close 고장 시 열림/닫힘 | I/P converter 전공 변환기
calibration 교정 | zero and span 영점 및 스팬 | as-found / as-left 교정 전 / 교정 후 | range 측정 범위 | turndown 턴다운 | accuracy 정확도 | live zero 라이브 제로
loop 루프 | loop diagram 루프도 | hook-up 계기 설치 상세도(Hook-up) | impulse line 도압관(임펄스 라인) | manifold 매니폴드 | junction box 정션 박스(단자함) | marshalling 마샬링
interlock 인터록 | trip 트립 | emergency shutdown (ESD) 비상 정지(ESD) | safety instrumented system (SIS) 안전계장시스템(SIS) | safety integrity level (SIL) 안전무결성등급(SIL) | proof test 보증 시험(Proof test) | voting 보팅
hazardous area 위험장소 | intrinsically safe 본질안전 | explosion-proof / flameproof 내압방폭 | setpoint 설정값 | process variable (PV) 공정 변수(PV) | controller output 제어기 출력 | cascade control 캐스케이드 제어
"""



def setup(P, LOCK, ApiError, read_json, write_json):
    X.update(P=P, LOCK=LOCK, ApiError=ApiError, read_json=read_json, write_json=write_json)


def err(code, msg):
    return X['ApiError'](code, msg)


def book_id(sig):
    return hashlib.sha1(sig.encode('utf-8')).hexdigest()[:24]


def cfg():
    return X['read_json'](X['P']('books', 'config.json')) or {}


def manifest():
    return X['read_json'](X['P']('books', 'index', 'manifest.json')) or {'books': []}


def root_dir():
    r = cfg().get('root') or ''
    return r if r and os.path.isdir(r) else ''


def who(h):
    """색인 · 폴더 설정 권한: 운영자(서버 PC) · 그룹장(SUPER) · config.json 의 managers 에 있는 본명"""
    if h.is_admin():
        return '운영자'
    acc = h.need_user(False)
    if h.is_super() or (acc.get('name') or '') in (cfg().get('managers') or []):
        return acc.get('name') or '?'
    raise err(403, '공용 도서관 색인 · 폴더 설정은 운영자(서버 PC) · 그룹장 · 지정된 관리자만 할 수 있습니다')


def can_manage(h):
    try:
        who(h)
        return True
    except Exception:
        return False


def safe_join(root, rel):
    """rel = '폴더이름/하위/책.pdf' (목록이 준 그대로). 폴더 밖 · 지원하지 않는 형식은 거부"""
    parts = [p for p in (rel or '').replace('\\', '/').split('/') if p]
    if len(parts) < 2 or parts[0] != os.path.basename(os.path.normpath(root)) or any(p in ('.', '..') for p in parts):
        raise err(400, '잘못된 경로')
    full = os.path.realpath(os.path.join(root, *parts[1:]))
    base = os.path.realpath(root)
    if not full.startswith(base + os.sep):
        raise err(403, '허용되지 않은 경로')
    if os.path.splitext(full)[1].lower() not in SUPPORTED:
        raise err(400, '지원하지 않는 형식')
    if not os.path.isfile(full):
        raise err(404, '파일이 없습니다 (폴더에서 지워졌거나 옮겨졌을 수 있습니다)')
    return full


# ---------------------------------------------------------------- 처리
def tr_cfg():
    t = cfg().get('translate') or {}
    key = t.get('apiKey') or os.environ.get('ANTHROPIC_API_KEY') or ''
    return {'enabled': bool(t.get('enabled')) and bool(key), 'on': bool(t.get('enabled')), 'key': key, 'keySet': bool(key),
            'model': t.get('model') or DEFAULT_MODEL, 'effort': t.get('effort') or 'low'}


def translate(text, src, title, by):
    """Claude 로 한국어 번역. 같은 글(모델 · 원문)은 보관본을 돌려줌"""
    t = tr_cfg()
    if not t['enabled']:
        raise err(403, 'Claude 번역이 꺼져 있습니다 (운영자가 [📚 도서관] → 번역 설정에서 켤 수 있습니다)')
    text = str(text or '').strip()
    if not text:
        raise err(400, '번역할 글이 없습니다')
    if len(text) > MAX_TR_CHARS:
        raise err(413, f'한 번에 {MAX_TR_CHARS:,}자까지 번역합니다 — 나눠서 번역해 주세요')
    h = hashlib.sha256((t['model'] + '\n' + text).encode('utf-8')).hexdigest()[:32]
    cpath = X['P']('books', 'tcache', h[:2], h + '.json')
    hit = X['read_json'](cpath)
    if hit and hit.get('text'):
        return {'text': hit['text'], 'model': hit.get('model'), 'cached': True}
    body = {
        'model': t['model'], 'max_tokens': 16000,
        'output_config': {'effort': t['effort']},                  # 번역은 깊은 추론보다 속도 — 기본 low
        'fallbacks': 'default',                                     # 정책상 거절되면 서버가 알맞은 모델로 다시 (beta 헤더 필요)
        'system': [{'type': 'text', 'text': TR_SYSTEM, 'cache_control': {'type': 'ephemeral'}}],   # 고정 지시 · 용어집은 캐시
        'messages': [{'role': 'user', 'content': (f'Source: "{title}"\n' if title else '') + (f'Language hint: {src}\n' if src else '') + '\n<passage>\n' + text + '\n</passage>'}],
    }
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode('utf-8'), method='POST', headers={
        'content-type': 'application/json', 'x-api-key': t['key'], 'anthropic-version': API_VERSION,
        'anthropic-beta': 'server-side-fallback-2026-07-01'})
    with TR_SEM:
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                res = json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode('utf-8')).get('error', {}).get('message', '')
            except Exception:
                msg = ''
            if e.code in (401, 403):
                raise err(502, f'번역 API 인증 실패 — 운영자가 API 키를 확인해 주세요 ({e.code})')
            if e.code == 429 or e.code >= 500:
                raise err(503, f'번역 API 가 바쁩니다 — 잠시 뒤 다시 해 주세요 ({e.code})')
            raise err(502, f'번역 API 오류 {e.code}: {msg[:200]}')
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise err(504, f'번역 API 에 연결하지 못했습니다 — 서버 PC 에서 api.anthropic.com 접속이 막혔을 수 있습니다 ({e})')
    if res.get('stop_reason') == 'refusal':
        raise err(422, '이 글은 번역 API 가 처리를 거절했습니다 — 브라우저 내장 번역이나 용어 풀이를 써 주세요')
    out = ''.join(b.get('text', '') for b in res.get('content') or [] if b.get('type') == 'text').strip()
    if not out:
        raise err(502, '번역 결과가 비었습니다')
    if res.get('stop_reason') == 'max_tokens':
        out += '\n…(길어서 일부만 번역됨)'
    u = res.get('usage') or {}
    rec = {'text': out, 'model': res.get('model') or t['model'], 'by': by, 'at': time.strftime('%Y-%m-%dT%H:%M:%S'),
           'chars': len(text), 'in': u.get('input_tokens'), 'out': u.get('output_tokens'), 'cacheRead': u.get('cache_read_input_tokens')}
    with X['LOCK']:
        X['write_json'](cpath, rec)
    return {'text': out, 'model': rec['model'], 'cached': False}


def handle(h, m, seg, q):
    if m == 'GET' and seg == ['info']:
        c, man, r, t = cfg(), manifest(), root_dir(), tr_cfg()
        out = {'enabled': bool(r), 'folder': os.path.basename(os.path.normpath(r)) if r else '', 'count': len(man.get('books') or []),
               'at': man.get('at') or '', 'by': man.get('by') or '', 'canManage': can_manage(h), 'rootSet': bool(c.get('root')),
               'translate': {'claude': t['enabled'], 'model': t['model'] if t['enabled'] else ''}}
        if out['canManage']:
            out.update(root=c.get('root') or '', rootOk=bool(r), managers=c.get('managers') or [])
        if h.is_admin():                                   # 번역 설정은 운영자(서버 PC)만 — 키 자체는 내보내지 않음
            out['translateCfg'] = {'on': t['on'], 'keySet': t['keySet'], 'model': t['model'], 'effort': t['effort']}
        return out
    if m == 'PUT' and seg == ['translate-config']:
        if not h.is_admin():
            raise err(403, '번역 설정은 운영자(서버 PC)만 바꿀 수 있습니다')
        b = h.json_body()
        with X['LOCK']:
            c = cfg(); t = dict(c.get('translate') or {})
            if 'enabled' in b:
                t['enabled'] = bool(b['enabled'])
            if str(b.get('apiKey') or '').strip():
                t['apiKey'] = str(b['apiKey']).strip()
            if b.get('clearKey'):
                t.pop('apiKey', None)
            if b.get('model'):
                t['model'] = str(b['model']).strip()[:60]
            if b.get('effort') in ('low', 'medium', 'high'):
                t['effort'] = b['effort']
            c['translate'] = t
            X['write_json'](X['P']('books', 'config.json'), c)
        tc = tr_cfg()
        return {'ok': True, 'on': tc['on'], 'keySet': tc['keySet'], 'model': tc['model'], 'effort': tc['effort']}
    if m == 'POST' and seg == ['translate']:                  # 로그인한 부서원 (비용이 드는 기능이라 비회원 제외)
        if h.is_admin():
            by = '운영자'
        else:
            by = h.need_user().get('name') or '?'
        b = h.json_body()
        return translate(b.get('text'), str(b.get('src') or '')[:20], str(b.get('title') or '')[:120], by)
    if m == 'PUT' and seg == ['root']:                       # 공용 도서관 폴더 경로 (서버 PC 기준, 예: D:\계장도서)
        by, b = who(h), h.json_body()
        path = os.path.normpath(os.path.expanduser(str(b.get('root') or '').strip().strip('"')))
        if not path or not os.path.isdir(path):
            raise err(400, f'서버 PC 에 그 폴더가 없습니다: {path}')
        with X['LOCK']:
            c = cfg()
            c.update(root=path, setBy=by, setAt=time.strftime('%Y-%m-%dT%H:%M:%S'))
            if isinstance(b.get('managers'), list) and h.is_admin():
                c['managers'] = [str(x).strip() for x in b['managers'] if str(x).strip()][:20]
            X['write_json'](X['P']('books', 'config.json'), c)
        return {'ok': True, 'root': path, 'folder': os.path.basename(path)}
    if m == 'GET' and seg == ['files']:                       # 폴더 안 책 파일 목록 (하위 폴더 포함)
        r = root_dir()
        if not r:
            raise err(404, '공용 도서관 폴더가 정해지지 않았습니다')
        top, out = os.path.basename(os.path.normpath(r)), []
        for dirpath, dirs, files in os.walk(r):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not d.startswith('~'))
            for fn in sorted(files):
                ext = os.path.splitext(fn)[1].lower()
                if ext not in SUPPORTED or fn.startswith('~$') or fn.startswith('.'):
                    continue
                full = os.path.join(dirpath, fn)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                rel = '/'.join([top] + os.path.relpath(full, r).replace('\\', '/').split('/'))
                out.append({'rel': rel, 'size': st.st_size, 'mtime': int(st.st_mtime * 1000)})
                if len(out) >= MAX_FILES:
                    return {'folder': top, 'files': out, 'truncated': True}
        return {'folder': top, 'files': out}
    if m == 'GET' and seg == ['file']:                        # 원본 파일 (미리보기 · 원본 열기)
        r = root_dir()
        if not r:
            raise err(404, '공용 도서관 폴더가 정해지지 않았습니다')
        full = safe_join(r, q.get('rel'))
        size, name = os.path.getsize(full), os.path.basename(full)
        h.send_response(200)
        h.send_header('Content-Type', SUPPORTED[os.path.splitext(full)[1].lower()])
        h.send_header('Content-Length', str(size))
        h.send_header('Content-Disposition', f"inline; filename*=UTF-8''{quote(name)}")
        h.send_header('Cache-Control', 'private, max-age=300')
        h.cors()
        h.end_headers()
        with open(full, 'rb') as f:
            shutil.copyfileobj(f, h.wfile, 1024 * 256)
        return None
    if m == 'GET' and seg == ['manifest']:
        return manifest()
    if m == 'GET' and len(seg) == 2 and seg[0] == 'book':   # 색인(본문) — gzip 그대로 보냄, 브라우저가 풀어 줌
        if not ID_RE.match(seg[1]):
            raise err(400, '잘못된 ID')
        try:
            with open(X['P']('books', 'index', seg[1] + '.json.gz'), 'rb') as f:
                data = f.read()
        except FileNotFoundError:
            raise err(404, '색인이 없습니다')
        return h.send(200, data, 'application/json; charset=utf-8', {'Content-Encoding': 'gzip'})
    if m == 'PUT' and seg == ['book']:                        # 운영자 브라우저가 뽑은 색인 올리기 (gzip JSON) — ID 는 서버가 sig 로 정함
        by, raw = who(h), h.raw_body()
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as g:
                js = g.read(MAX_BOOK_JSON + 1)
            if len(js) > MAX_BOOK_JSON:
                raise err(413, '색인이 너무 큽니다')
            rec = json.loads(js.decode('utf-8'))
        except (OSError, ValueError, EOFError):
            raise err(400, '색인 형식 오류 (gzip JSON 이어야 합니다)')
        if not isinstance(rec, dict) or not isinstance(rec.get('pages'), list) or not rec.get('sig'):
            raise err(400, '색인 내용이 맞지 않습니다')
        bid = book_id(str(rec['sig']))
        path = X['P']('books', 'index', bid + '.json.gz')
        with X['LOCK']:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = f'{path}.{os.getpid()}.tmp'
            with open(tmp, 'wb') as f:
                f.write(raw)
            os.replace(tmp, path)
        return {'ok': True, 'id': bid, 'by': by}
    if m == 'PUT' and seg == ['manifest']:                    # 색인 목록 확정 (목록에 없는 색인 파일은 정리)
        by, b = who(h), h.json_body()
        books, keep = [], set()
        for e in b.get('books') or []:
            sig = str(e.get('sig') or '')
            bid = book_id(sig)
            if not sig or not os.path.exists(X['P']('books', 'index', bid + '.json.gz')):
                continue
            keep.add(bid)
            books.append({k: e.get(k) for k in ('sig', 'rel', 'ext', 'size', 'mtime', 'nPages', 'chars', 'err', 'title', 'v')} | {'id': bid})
        with X['LOCK']:
            X['write_json'](X['P']('books', 'index', 'manifest.json'), {'books': books, 'at': time.strftime('%Y-%m-%dT%H:%M:%S'), 'by': by, 'folder': b.get('folder') or ''})
            if b.get('final'):
                d = X['P']('books', 'index')
                for fn in os.listdir(d):
                    if fn.endswith('.json.gz') and fn[:-8] not in keep:
                        try:
                            os.remove(os.path.join(d, fn))
                        except OSError:
                            pass
        return {'ok': True, 'count': len(books)}
    raise err(404, '없는 경로')
