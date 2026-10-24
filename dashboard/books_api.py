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
import time
from urllib.parse import quote

SUPPORTED = {'.pdf': 'application/pdf', '.epub': 'application/epub+zip',
             '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
             '.hwpx': 'application/octet-stream', '.txt': 'text/plain; charset=utf-8', '.md': 'text/plain; charset=utf-8'}
ID_RE = re.compile(r'^[0-9a-f]{24}$')
MAX_FILES = 20000
MAX_BOOK_JSON = 400 * 1024 * 1024        # 풀었을 때 크기 상한 (3,000쪽 책도 수십 MB)
X = {}                                   # setup() 이 넣는 server.py 의 도구들


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
def handle(h, m, seg, q):
    if m == 'GET' and seg == ['info']:
        c, man, r = cfg(), manifest(), root_dir()
        out = {'enabled': bool(r), 'folder': os.path.basename(os.path.normpath(r)) if r else '', 'count': len(man.get('books') or []),
               'at': man.get('at') or '', 'by': man.get('by') or '', 'canManage': can_manage(h), 'rootSet': bool(c.get('root'))}
        if out['canManage']:
            out.update(root=c.get('root') or '', rootOk=bool(r), managers=c.get('managers') or [])
        return out
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
