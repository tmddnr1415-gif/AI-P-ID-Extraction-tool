#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
계장ENG그룹 Dashboard 서버 (Python 표준 라이브러리만 사용)

실행:
    python server.py                          # server.py 가 있는 폴더를 운영 폴더로 사용, 포트 8080
    python server.py --root "<운영폴더>" --port 8080 --log server.log --open

- 운영 폴더의 dashboard.html 을 제공하고 data/ history/ trash/ archive/ saves/ 를 그대로 사용
- 모든 파일 쓰기는 서버 내부 잠금(lock) 안에서 수행 → 동시 저장 안전
- 관리자 기능(금주 마감, 휴지통 영구삭제)은 이 PC(localhost)에서 접속할 때만 허용
- 매일 1회 backup/YYYY-MM-DD.zip 자동 백업 (기본 60일 보관)
- 매주 수요일 12:00 자동 주간 저장 archive/YYYY-Www.json (수요일 오전 11:59 기준, 이후 수정은 다음 주)
- 수정 이력(history/)은 7일만 보관, 1시간마다 7일 지난 이력 자동 삭제 (--history-days 로 변경)
- 계정(accounts/): 로그인한 사용자만 수정 가능, 수정자는 계정의 본명으로 기록. 비회원은 보기만 가능
- 쪽지(messages/): 로그인 사용자끼리, 180일 지나면 자동 삭제
"""
import argparse, datetime, hashlib, hmac, io, ipaddress, json, logging, mimetypes, os, re, socket, sys, threading, time, webbrowser, zipfile, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, parse_qs, unquote, quote

SHEETS = ['perform', 'bid', 'issue', 'rnr', 'general', 'unit', 'techshare', 'todo', 'staffing', 'notice', 'task']   # task = 통합 업무
LABEL = {'perform': '수행', 'bid': '입찰', 'issue': '프로젝트 이슈사항', 'rnr': 'PJT R&R', 'general': '일반업무', 'unit': '유닛분장',
         'techshare': '기술공유', 'todo': 'To do list', 'staffing': '계장 투입인력', 'notice': '주간회의 전달사항', 'task': '통합 업무'}
TITLE = {'perform': 'PJT명', 'bid': 'PJT명', 'issue': 'PJT명', 'rnr': 'PJT명', 'general': '업무 내용', 'unit': '유닛',
         'techshare': '발표 내용', 'todo': '지시 사항', 'staffing': '이름', 'notice': '제목', 'task': '업무 내용'}
FILE_TYPES = {'.pdf': 'application/pdf', '.ppt': 'application/vnd.ms-powerpoint',
              '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'}
ID_RE = re.compile(r'^[A-Za-z0-9_\-]{1,80}$')
WEEK_RE = re.compile(r'^\d{4}-W\d{2}$')
MAX_BODY = 30 * 1024 * 1024

SERVER_VERSION = '2026-10-22.1'
ROOT = os.path.dirname(os.path.abspath(__file__))
PORT = 8080
ALLOW_NETS = []          # 사내망: 루프백·사설망 + 서버 IP 대역(/16, 유선·Wi-Fi 등 지금까지 쓴 대역 모두 기억) + --allow 로 추가한 대역
EXTRA_NETS = []          # --allow 로 준 대역
NET_STATE = {'ips': None, 'profiles': [], 'changedAt': ''}   # 지금 IP · Windows 네트워크 종류(공용/개인/도메인) — 관리자 화면 진단용
LOCK = threading.RLock()
log = logging.getLogger('dashboard')


# ---------------------------------------------------------------- 공통
def stamp():
    """브라우저 new Date().toISOString() 과 같은 형식 (UTC, 밀리초, Z)"""
    t = datetime.datetime.now(datetime.timezone.utc)
    return t.strftime('%Y-%m-%dT%H:%M:%S.') + f'{t.microsecond // 1000:03d}Z'


CUTOFF_WEEKDAY, CUTOFF_HOUR = 2, 12          # 수요일(월=0) 12:00 — 수요일 오전 11:59까지가 그 주 데이터


def week_wed(d):
    """날짜 d 가 속한 ISO 주의 수요일"""
    return d - datetime.timedelta(days=d.weekday() - CUTOFF_WEEKDAY)


def week_id(wed):
    y, w, _ = wed.isocalendar()
    return f'{y}-W{w:02d}'


def manual_closed_week():
    """[금주 마감] 으로 앞당겨 마감한 마지막 주차 (state.json manualClosedWeek) — 그 주차까지는 끝난 주"""
    try:
        return (read_json(P('data', '_meta', 'state.json')) or {}).get('manualClosedWeek') or ''
    except Exception:
        return ''


def iso_week(now=None):
    """현재 데이터가 속하는 주차: 수요일 12:00 이후는 다음 주. [금주 마감] 을 누른 주차는 이미 끝났으므로 그다음 주"""
    now = now or datetime.datetime.now()
    wed = week_wed(now.date())
    if now >= datetime.datetime.combine(wed, datetime.time(CUTOFF_HOUR)):
        wed += datetime.timedelta(days=7)
    closed = manual_closed_week()
    while closed and week_id(wed) <= closed:
        wed += datetime.timedelta(days=7)
    return week_id(wed)


def last_cutoff(now=None):
    """가장 최근에 지난 마감 시각(로컬)과 그 주차"""
    now = now or datetime.datetime.now()
    wed = week_wed(now.date())
    cut = datetime.datetime.combine(wed, datetime.time(CUTOFF_HOUR))
    if now < cut:
        cut -= datetime.timedelta(days=7)
    return cut, week_id(cut.date())


def to_z(local_dt):
    t = local_dt.astimezone(datetime.timezone.utc)
    return t.strftime('%Y-%m-%dT%H:%M:%S.') + f'{t.microsecond // 1000:03d}Z'


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|\s]+', '_', str(s or '익명'))[:40] or '익명'


def P(*parts):
    return os.path.join(ROOT, *parts)


def read_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def write_json(path, obj):
    """임시 파일에 쓴 뒤 교체 (쓰는 도중 다른 사람이 읽어도 깨진 파일을 보지 않음)"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f'{path}.{threading.get_ident()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def list_json(d):
    try:
        return sorted(n for n in os.listdir(d) if n.endswith('.json'))
    except FileNotFoundError:
        return []


def flatten(o, pre='', out=None):
    """dashboard.html 의 flatten 과 같은 경로 규칙 (중첩 객체는 a.b)"""
    out = {} if out is None else out
    for k, v in (o or {}).items():
        p = f'{pre}.{k}' if pre else k
        if isinstance(v, dict):
            flatten(v, p, out)
        else:
            out[p] = v if isinstance(v, str) else json.dumps(v if v is not None else '', ensure_ascii=False)
    return out


def diff_paths(a, b):
    x, y = flatten(a), flatten(b)
    return [k for k in sorted(set(x) | set(y)) if x.get(k, '') != y.get(k, '')]


def rec_label(key, f):
    f = f or {}
    if key == 'rnr':
        s = f"{f.get('PJT명', '')} / {f.get('담당자', '')}"
    elif key == 'unit':
        s = f"{f.get('연도', '')} {f.get('유닛', '')}"
    else:
        s = f.get(TITLE[key]) or '(제목 없음)'
    s = re.sub(r'\s+', ' ', str(s)).strip()
    return s if len(s) <= 40 else s[:39] + '…'


# ---------------------------------------------------------------- 데이터 작업 (쓰기는 모두 LOCK 안에서)
_cache = {}   # path -> (mtime, size, obj)


def read_cached(path):
    st = os.stat(path)
    c = _cache.get(path)
    if c and c[0] == st.st_mtime_ns and c[1] == st.st_size:
        return c[2]
    obj = read_json(path)
    _cache[path] = (st.st_mtime_ns, st.st_size, obj)
    return obj


def load_sheet(key):
    d, out = P('data', key), []
    for n in list_json(d):
        try:
            r = read_cached(os.path.join(d, n))
            if r and r.get('fields') is not None:
                out.append(r)
        except Exception as e:
            log.warning('읽기 실패 %s/%s: %s', key, n, e)
    return out


def archives():
    return sorted((n[:-5] for n in list_json(P('archive'))), reverse=True)


def add_history(key, rid, entry):
    name = f"{entry['at'].replace(':', '-').replace('.', '-')}_{safe_name(entry['by'])}.json"
    path = P('history', key, rid, name)
    i = 1
    while os.path.exists(path):                       # 같은 밀리초 충돌 방지
        path = P('history', key, rid, name[:-5] + f'_{i}.json'); i += 1
    write_json(path, {'sheet': key, 'rid': rid, **entry})


def api_all():
    return {'recs': {k: load_sheet(k) for k in SHEETS}, 'sheetCols': sheet_cols(),
            'cols': (read_json(P('data', '_meta', 'staffing-columns.json')) or {}).get('columns', []),
            'state': read_json(P('data', '_meta', 'state.json')) or {},
            'archives': archives()}


def api_create(key, body):
    by, fields = body.get('by') or '익명', body.get('fields') or {}
    with LOCK:
        rid = body.get('id') or f"{key}-{int(time.time() * 1000):x}{os.urandom(2).hex()}"
        if not ID_RE.match(rid):
            raise ApiError(400, '잘못된 ID')
        path = P('data', key, rid + '.json')
        if os.path.exists(path):
            raise ApiError(409, '같은 ID의 행이 이미 존재합니다')
        order = body.get('order')
        if order is None:
            order = max([r.get('order', 0) for r in load_sheet(key)] or [0]) + 10
        now = stamp()
        rec = {'id': rid, 'sheet': key, 'order': order, 'fields': fields,
               'meta': {'createdBy': by, 'createdAt': now, 'updatedBy': by, 'updatedAt': now, 'rev': 1}}
        write_json(path, rec)
        add_history(key, rid, {'action': 'create', 'by': by, 'at': now, 'label': rec_label(key, fields),
                               'before': None, 'after': fields, 'changed': list(flatten(fields))})
    return {'status': 'ok', 'rec': rec}


def api_update(key, rid, body):
    by, nf = body.get('by') or '익명', body.get('fields') or {}
    force, action = bool(body.get('force')), body.get('action') or 'update'
    with LOCK:                                           # 버전 비교 + 쓰기를 한 번에 → 동시 저장 안전
        path = P('data', key, rid + '.json')
        cur = read_json(path)
        if not cur:
            return {'status': 'deleted'}
        mismatch = cur['meta'].get('rev') != body.get('baseRev')
        if mismatch and not force:
            return {'status': 'conflict', 'cur': cur}
        changed = diff_paths(cur['fields'], nf)
        if not changed:
            return {'status': 'nochange', 'cur': cur}
        now = stamp()
        changes = dict(cur['meta'].get('changes') or {})
        for p in changed:
            changes[p] = now
        # 마지막 마감 이후 첫 수정 직전의 내용(orig)을 보관 → 화면/엑셀에서 '추가된 내용'(파란 글씨) 비교 기준
        since = (read_json(P('data', '_meta', 'state.json')) or {}).get('lastClosedAt', '')
        m0 = cur['meta']
        orig = m0['orig'] if m0.get('orig') is not None and m0.get('origSince', '') == since else cur['fields']
        rec = {**cur, 'fields': nf, 'meta': {**m0, 'updatedBy': by, 'updatedAt': now,
                                              'rev': m0.get('rev', 1) + 1, 'changes': changes, 'orig': orig, 'origSince': since}}
        write_json(path, rec)
        add_history(key, rid, {'action': 'overwrite' if (force and mismatch) else action, 'by': by, 'at': now,
                               'label': rec_label(key, nf), 'before': cur['fields'], 'after': nf, 'changed': changed,
                               'prevBy': cur['meta'].get('updatedBy'), 'prevAt': cur['meta'].get('updatedAt')})
    return {'status': 'ok', 'rec': rec}


def api_delete(key, rid, by):
    with LOCK:
        path = P('data', key, rid + '.json')
        cur = read_json(path)
        if not cur:
            return {'status': 'none'}
        now = stamp()
        write_json(P('trash', key, rid + '.json'), {**cur, 'meta': {**cur['meta'], 'deletedBy': by, 'deletedAt': now}})
        os.remove(path)
        add_history(key, rid, {'action': 'delete', 'by': by, 'at': now, 'label': rec_label(key, cur['fields']),
                               'before': cur['fields'], 'after': None, 'changed': []})
    return {'status': 'ok'}


def api_trash():
    items = []
    for k in SHEETS:
        for n in list_json(P('trash', k)):
            r = read_json(P('trash', k, n))
            if r:
                items.append({'key': k, **r})
    items.sort(key=lambda r: r.get('meta', {}).get('deletedAt', ''), reverse=True)
    return items


def api_restore(key, rid, by):
    with LOCK:
        tp, dp = P('trash', key, rid + '.json'), P('data', key, rid + '.json')
        t = read_json(tp)
        if not t:
            return {'status': 'none'}
        if os.path.exists(dp):
            return {'status': 'exists'}
        now = stamp()
        meta = {k: v for k, v in t['meta'].items() if k not in ('deletedBy', 'deletedAt')}
        meta.update(updatedBy=by, updatedAt=now, rev=meta.get('rev', 1) + 1)
        write_json(dp, {**t, 'meta': meta})
        os.remove(tp)
        add_history(key, rid, {'action': 'restore', 'by': by, 'at': now, 'label': rec_label(key, t['fields']),
                               'before': None, 'after': t['fields'], 'changed': []})
    return {'status': 'ok'}


def api_purge(key, rid, by):
    with LOCK:
        tp = P('trash', key, rid + '.json')
        t = read_json(tp)
        if not t:
            return {'status': 'none'}
        os.remove(tp)
        add_history(key, rid, {'action': 'purge', 'by': by, 'at': stamp(), 'label': rec_label(key, t['fields']),
                               'before': t['fields'], 'after': None, 'changed': []})
    return {'status': 'ok'}


def api_history(key, rid):
    d, out = P('history', key, rid), []
    for n in list_json(d):
        e = read_json(os.path.join(d, n))
        if e:
            out.append({'n': n, **e})
    out.sort(key=lambda e: e.get('at', ''), reverse=True)
    return out


def api_recent(limit=10):
    files = []
    for k in SHEETS:
        base = P('history', k)
        try:
            rids = os.listdir(base)
        except FileNotFoundError:
            continue
        for rid in rids:
            for n in list_json(os.path.join(base, rid)):
                files.append((n, k, os.path.join(base, rid, n)))
    files.sort(reverse=True)
    out = []
    for n, k, path in files[:limit]:
        e = read_json(path)
        if e:
            out.append({**e, 'key': k})
    return out


def api_archive(name):
    a = read_json(P('archive', name + '.json'))
    if not a:
        raise ApiError(404, '마감본이 없습니다')
    arcs = archives()
    i = arcs.index(name) if name in arcs else -1
    prev = read_json(P('archive', arcs[i + 1] + '.json')) if 0 <= i < len(arcs) - 1 else None
    return {'arch': a, 'prev': prev}


def api_close(body):
    by, name = body.get('by') or '익명', iso_week()
    with LOCK:
        path = P('archive', name + '.json')
        if os.path.exists(path) and not body.get('overwrite'):
            return {'status': 'exists', 'week': name}
        now, data = stamp(), api_all()
        write_json(path, {'week': name, 'closedAt': now, 'closedBy': by, 'sheets': data['recs'], 'staffingColumns': data['cols']})
        st = read_json(P('data', '_meta', 'state.json')) or {}
        write_json(P('data', '_meta', 'state.json'), {**st, 'lastClosedAt': now, 'lastClosedWeek': name, 'closedBy': by, 'manualClosedWeek': name})
    log.info('금주 마감 %s by %s (바로 다음 주차 %s 로 넘어감)', name, by, iso_week())
    return {'status': 'ok', 'week': name}


def snapshot_at(cz):
    """마감 시각 cz(UTC ISO) 시점의 전체 데이터 — 그 이후 수정은 이력의 '수정 전' 내용으로 되돌림"""
    def at_cutoff(key, rec):
        hd = P('history', key, rec['id'])
        if not os.path.isdir(hd):
            return rec
        after = sorted((e for e in api_history(key, rec['id']) if e.get('at', '') > cz), key=lambda e: e.get('at', ''))
        if not after:
            return rec
        first = after[0]
        if first.get('action') in ('create', 'restore') or first.get('before') is None:
            return None                                   # 마감 시각에는 없던 행
        return {**rec, 'fields': first['before']}

    sheets = {}
    for k in SHEETS:
        out = [r for r in (at_cutoff(k, r) for r in load_sheet(k)) if r]
        live = {r['id'] for r in out}
        for n in list_json(P('trash', k)):                # 마감 이후 삭제된 행은 마감 시점 내용으로 포함
            t = read_json(P('trash', k, n))
            if t and t['meta'].get('deletedAt', '') > cz and t['id'] not in live:
                r = at_cutoff(k, {**t, 'meta': {kk: v for kk, v in t['meta'].items() if kk not in ('deletedBy', 'deletedAt')}})
                if r:
                    out.append(r)
        sheets[k] = sorted(out, key=lambda r: (r.get('order', 0), r['id']))
    return sheets


def auto_close():
    """매주 수요일 12:00(=수요일 오전 11:59 마감) 자동 주간 저장. 서버가 꺼져 있었으면 켜진 뒤 이력으로 마감 시점 복원"""
    cut, week = last_cutoff()
    cz = to_z(cut)
    with LOCK:
        a = read_json(P('archive', week + '.json'))
        if a and a.get('auto') and a.get('closedAt') == cz:   # 이미 마감 시점으로 자동 저장됨
            return
        if a and not a.get('auto') and manual_closed_week() >= week:   # [금주 마감] 으로 이미 앞당겨 마감한 주 → 자동 마감이 덮어쓰지 않음
            return
        cols = (read_json(P('data', '_meta', 'staffing-columns.json')) or {}).get('columns', [])
        write_json(P('archive', week + '.json'), {'week': week, 'closedAt': cz, 'closedBy': '자동 마감(수 11:59)', 'auto': True,
                                                  'cutoff': cut.strftime('%Y-%m-%d %H:%M'), 'sheets': snapshot_at(cz), 'staffingColumns': cols})
        st = read_json(P('data', '_meta', 'state.json')) or {}
        if st.get('lastClosedWeek') in (None, week) or st.get('lastClosedAt', '') <= cz:
            write_json(P('data', '_meta', 'state.json'), {**st, 'lastClosedAt': cz, 'lastClosedWeek': week, 'closedBy': '자동 마감'})
    log.info('주간 자동 저장: archive/%s.json (마감 %s 수요일 11:59)', week, cut.strftime('%Y-%m-%d'))


def weekly_loop():
    while True:
        try:
            refresh_nets()                                # 유선 LAN ↔ Wi-Fi 전환으로 IP 가 바뀌면 허용 대역·배포본 갱신
        except Exception as e:
            log.error('네트워크 확인 실패: %s', e)
        try:
            build_deploy()                                # dashboard.html 이 바뀌면 deploy/ 도 자동 갱신
        except Exception as e:
            log.error('배포 파일 생성 실패: %s', e)
        try:
            auto_close()
        except Exception as e:
            log.error('주간 자동 저장 실패: %s', e)
        time.sleep(30)


def api_add_column(body):
    name, kind, by = (body.get('name') or '').strip(), body.get('kind') or '기타', body.get('by') or '익명'
    if not name:
        raise ApiError(400, 'PJT명이 필요합니다')
    with LOCK:
        path = P('data', '_meta', 'staffing-columns.json')
        cur = read_json(path) or {'columns': []}
        c = next((x for x in cur['columns'] if x['name'] == name), None)
        if not c:
            c = {'id': 'c' + format(int(time.time() * 1000), 'x'), 'name': name, 'kind': kind}
            cur['columns'].append(c)
            cur.update(updatedBy=by, updatedAt=stamp())
            write_json(path, cur)
    return {'column': c, 'columns': cur['columns']}


def api_saveall(body):
    by = body.get('by') or '익명'
    with LOCK:
        now, data = stamp(), api_all()
        tag = datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S') + '_' + safe_name(by)
        counts = {LABEL[k]: len(v) for k, v in data['recs'].items()}
        write_json(P('saves', f'전체저장_{tag}.json'), {'type': 'full-save', 'week': iso_week(), 'savedAt': now, 'savedBy': by,
                                                     'counts': counts, 'sheets': data['recs'], 'staffingColumns': data['cols']})
        st = read_json(P('data', '_meta', 'state.json')) or {}
        write_json(P('data', '_meta', 'state.json'), {**st, 'lastFullSaveAt': now, 'lastFullSaveBy': by, 'lastFullSaveFile': f'전체저장_{tag}'})
    return {'status': 'ok', 'tag': tag}


def save_xlsx(tag, data):
    if not re.fullmatch(r'[\w\-가-힣]{1,80}', tag):
        raise ApiError(400, '잘못된 파일명')
    with LOCK:
        os.makedirs(P('saves'), exist_ok=True)
        tmp = P('saves', f'전체저장_{tag}.xlsx.tmp')
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, P('saves', f'전체저장_{tag}.xlsx'))
    return {'status': 'ok'}


# ---------------------------------------------------------------- 첨부파일 (files/{파일ID}.{확장자} + files/{파일ID}.json)
def api_file_upload(name, data, by):
    name = os.path.basename(str(name or '').replace('\\', '/')).strip()[:120]
    ext = os.path.splitext(name)[1].lower()
    if ext not in FILE_TYPES:
        raise ApiError(400, 'PDF 또는 PowerPoint(ppt, pptx) 파일만 올릴 수 있습니다')
    if not data:
        raise ApiError(400, '빈 파일입니다')
    with LOCK:
        fid = f"f{int(time.time() * 1000):x}{os.urandom(3).hex()}"
        os.makedirs(P('files'), exist_ok=True)
        tmp = P('files', fid + ext + '.tmp')
        with open(tmp, 'wb') as f:
            f.write(data)
        os.replace(tmp, P('files', fid + ext))
        meta = {'id': fid, 'name': name, 'ext': ext, 'size': len(data), 'by': by, 'at': stamp()}
        write_json(P('files', fid + '.json'), meta)
    log.info('첨부파일 업로드: %s (%d bytes) by %s', fid + ext, len(data), by)
    return meta


def file_meta(fid):
    if not ID_RE.match(fid or ''):
        raise ApiError(400, '잘못된 파일 ID')
    m = read_json(P('files', fid + '.json'))
    if not m or not os.path.isfile(P('files', fid + m['ext'])):
        raise ApiError(404, '첨부파일이 없습니다 (삭제되었거나 다른 서버의 파일)')
    return m


# ---------------------------------------------------------------- 익명게시판 (board/{글ID}.json)
# 실명은 받지도 저장하지도 않음. 본인 확인은 글/댓글마다 브라우저가 만든 임의 토큰의 해시로만 함.
def token_hash(t):
    return hashlib.sha256(('dept-board:' + str(t)).encode('utf-8')).hexdigest() if t else ''


def board_nick(b):
    nick = re.sub(r'\s+', ' ', str(b.get('nick') or '')).strip()[:20]
    return '익명' if b.get('anon') or not nick else nick


BOARD_KINDS = ('블라블라', '회식제안', 'VOC')


def board_author(b, acc):
    """(표시 이름, 실명 여부). 실명은 브라우저가 보낸 이름이 아니라 로그인 계정 본명으로만 기록"""
    if b.get('real') and acc:
        return acc['name'], True
    return board_nick(b), False


def board_kind(b):
    k = str(b.get('kind') or '')
    return k if k in BOARD_KINDS else '블라블라'


def board_public(p):
    q = {k: v for k, v in p.items() if k != 'tokenHash'}
    q['comments'] = [{k: v for k, v in c.items() if k != 'tokenHash'} for c in p.get('comments', [])]
    return q


def board_text(b, key, limit, required=True):
    v = str(b.get(key) or '').replace('\r', '').strip()
    if required and not v:
        raise ApiError(400, '내용을 입력하세요')
    if len(v) > limit:
        raise ApiError(400, f'{limit}자 이하로 입력하세요')
    return v


def board_owner(rec, token, admin):
    if admin:
        return
    if not token or token_hash(token) != rec.get('tokenHash'):
        raise ApiError(403, '이 브라우저에서 작성한 글/댓글만 수정·삭제할 수 있습니다')


def board_load(pid):
    if not ID_RE.match(pid):
        raise ApiError(400, '잘못된 ID')
    p = read_json(P('board', pid + '.json'))
    if not p:
        raise ApiError(404, '삭제된 글입니다')
    return p


def api_board_list():
    out = []
    for n in list_json(P('board')):
        p = read_json(P('board', n))
        if p:
            out.append(board_public(p))
    out.sort(key=lambda p: p.get('createdAt', ''), reverse=True)
    return out


def api_board_create(b, acc=None):
    title, body = board_text(b, 'title', 100), board_text(b, 'body', 5000)
    nick, real = board_author(b, acc)
    if not b.get('token'):
        raise ApiError(400, '토큰이 없습니다')
    with LOCK:
        pid = f"b{int(time.time() * 1000):x}{os.urandom(3).hex()}"
        now = stamp()
        p = {'id': pid, 'title': title, 'body': body, 'kind': board_kind(b), 'nick': nick, 'real': real, 'createdAt': now, 'updatedAt': now,
             'tokenHash': token_hash(b['token']), 'comments': []}
        write_json(P('board', pid + '.json'), p)
    return board_public(p)


def api_board_update(pid, b, acc=None):
    nick, real = board_author(b, acc)
    with LOCK:
        p = board_load(pid)
        board_owner(p, b.get('token'), False)
        p.update(title=board_text(b, 'title', 100), body=board_text(b, 'body', 5000), kind=board_kind(b), nick=nick, real=real, updatedAt=stamp())
        write_json(P('board', pid + '.json'), p)
    return board_public(p)


def api_board_delete(pid, b, admin):
    with LOCK:
        p = board_load(pid)
        board_owner(p, b.get('token'), admin)
        os.remove(P('board', pid + '.json'))
    return {'status': 'ok'}


def api_comment_add(pid, b, acc=None):
    body = board_text(b, 'body', 1000)
    nick, real = board_author(b, acc)
    if not b.get('token'):
        raise ApiError(400, '토큰이 없습니다')
    with LOCK:
        p = board_load(pid)
        c = {'id': f"c{int(time.time() * 1000):x}{os.urandom(2).hex()}", 'body': body, 'nick': nick, 'real': real,
             'createdAt': stamp(), 'tokenHash': token_hash(b['token'])}
        p.setdefault('comments', []).append(c)
        write_json(P('board', pid + '.json'), p)
    return board_public(p)


def api_comment_delete(pid, cid, b, admin):
    with LOCK:
        p = board_load(pid)
        c = next((x for x in p.get('comments', []) if x['id'] == cid), None)
        if not c:
            raise ApiError(404, '삭제된 댓글입니다')
        board_owner(c, b.get('token'), admin)
        p['comments'] = [x for x in p['comments'] if x['id'] != cid]
        write_json(P('board', pid + '.json'), p)
    return board_public(p)


# ---------------------------------------------------------------- 계정 (accounts/{ID}.json, 세션 accounts/_sessions.json)
# 비밀번호는 PBKDF2-SHA256 해시로만 저장. 메일주소·생년월일도 원문 없이 '비밀번호 재설정 확인용 해시'로만 저장.
# 모든 쓰기 API 의 수정자(by)는 브라우저가 보낸 값이 아니라 로그인 세션의 본명으로 기록.
UID_RE = re.compile(r'^[a-z0-9][a-z0-9_.\-]{2,19}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
PW_ITER = 200_000
SESSION_DAYS = 30
ONLINE_SEC = 75                                         # 마지막 요청 후 이 시간 안이면 '접속 중' (화면이 30초마다 ping)
_sessions = None                                        # sha256(토큰) -> {'id', 'at'}
_presence = {}                                          # ID -> 마지막 요청 시각(time.time)
_fails = {}                                             # (종류, ID) -> [실패 횟수, 첫 실패 시각]


def ago_z(days):
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    return t.strftime('%Y-%m-%dT%H:%M:%S.') + f'{t.microsecond // 1000:03d}Z'


def kdf(secret, salt):
    return hashlib.pbkdf2_hmac('sha256', secret.encode('utf-8'), bytes.fromhex(salt), PW_ITER).hex()


def reset_secret(email, birth):
    return f"{str(email or '').strip().lower()}|{str(birth or '').strip()}"


def acc_path(uid):
    return P('accounts', uid + '.json')


def load_account(uid):
    return read_json(acc_path(uid)) if UID_RE.match(uid or '') else None


def norm_uid(b):
    uid = str(b.get('id') or '').strip().lower()
    if not UID_RE.match(uid):
        raise ApiError(400, 'ID는 영문 소문자·숫자로 시작하는 3~20자 (영문·숫자·_ . -)로 입력하세요')
    return uid


def check_pw(pw):
    pw = str(pw or '')
    if not 8 <= len(pw) <= 64:
        raise ApiError(400, '비밀번호는 8~64자로 입력하세요')
    return pw


def check_reset_info(b):
    email, birth = str(b.get('email') or '').strip(), str(b.get('birth') or '').strip()
    if len(email) > 100 or not EMAIL_RE.match(email):
        raise ApiError(400, '메일주소 형식이 올바르지 않습니다')
    try:
        d = datetime.date.fromisoformat(birth)
    except ValueError:
        raise ApiError(400, '생년월일을 YYYY-MM-DD 로 입력하세요')
    if not datetime.date(1900, 1, 1) <= d <= datetime.date.today():
        raise ApiError(400, '생년월일을 확인하세요')
    return email, birth


def fail_check(key):
    c = _fails.get(key)
    if c and c[0] >= 5 and time.time() - c[1] < 600:
        raise ApiError(429, f'시도 횟수를 초과했습니다. {int((600 - (time.time() - c[1])) // 60) + 1}분 뒤에 다시 시도하세요')


def fail_add(key):
    c = _fails.get(key)
    if not c or time.time() - c[1] >= 600:
        c = _fails[key] = [0, time.time()]
    c[0] += 1


def sessions():
    global _sessions
    if _sessions is None:
        lim = ago_z(SESSION_DAYS)
        _sessions = {k: v for k, v in (read_json(P('accounts', '_sessions.json')) or {}).items() if v.get('at', '') > lim}
    return _sessions


def session_new(uid):
    token = os.urandom(32).hex()
    with LOCK:
        s, lim = sessions(), ago_z(SESSION_DAYS)
        for k in [k for k, v in s.items() if v.get('at', '') <= lim]:
            del s[k]
        s[token_hash(token)] = {'id': uid, 'at': stamp()}
        write_json(P('accounts', '_sessions.json'), s)
    return token


def session_drop(token=None, uid=None):
    with LOCK:
        s = sessions()
        keys = [token_hash(token)] if token else [k for k, v in s.items() if v.get('id') == uid]
        removed = [k for k in keys if s.pop(k, None)]
        if removed:
            write_json(P('accounts', '_sessions.json'), s)


def session_account(token, touch=True):
    if not token:
        return None
    v = sessions().get(token_hash(token))
    if not v or v.get('at', '') <= ago_z(SESSION_DAYS):
        return None
    acc = load_account(v['id'])
    if acc and touch:
        _presence[acc['id']] = time.time()
    return acc


def acc_public(acc):
    return {'id': acc['id'], 'name': acc['name']}


def api_register(b):
    uid = norm_uid(b)
    name = re.sub(r'\s+', ' ', str(b.get('name') or '')).strip()
    if not 2 <= len(name) <= 20:
        raise ApiError(400, '본명을 2~20자로 입력하세요')
    pw = check_pw(b.get('password'))
    email, birth = check_reset_info(b)
    with LOCK:
        if os.path.exists(acc_path(uid)):
            raise ApiError(409, '이미 사용 중인 ID입니다')
        salt, rsalt, now = os.urandom(16).hex(), os.urandom(16).hex(), stamp()
        acc = {'id': uid, 'name': name, 'salt': salt, 'hash': kdf(pw, salt), 'rsalt': rsalt, 'rhash': kdf(reset_secret(email, birth), rsalt),
               'iter': PW_ITER, 'createdAt': now, 'pwChangedAt': now}
        write_json(acc_path(uid), acc)
    log.info('계정 개설: %s', uid)
    return {'token': session_new(uid), 'user': acc_public(acc)}


def api_login(b):
    uid = str(b.get('id') or '').strip().lower()
    fail_check(('login', uid))
    acc = load_account(uid)
    if not acc or not hmac.compare_digest(kdf(str(b.get('password') or ''), acc['salt']), acc['hash']):
        fail_add(('login', uid))
        raise ApiError(401, 'ID 또는 비밀번호가 맞지 않습니다')
    _fails.pop(('login', uid), None)
    return {'token': session_new(uid), 'user': acc_public(acc)}


def api_reset(b):
    uid = str(b.get('id') or '').strip().lower()
    fail_check(('reset', uid))
    email, birth = check_reset_info(b)
    pw = check_pw(b.get('password'))
    with LOCK:
        acc = load_account(uid)
        if not acc or not hmac.compare_digest(kdf(reset_secret(email, birth), acc['rsalt']), acc['rhash']):
            fail_add(('reset', uid))
            raise ApiError(401, 'ID·메일주소·생년월일이 가입 정보와 맞지 않습니다')
        acc['salt'] = os.urandom(16).hex()
        acc.update(hash=kdf(pw, acc['salt']), pwChangedAt=stamp())
        write_json(acc_path(uid), acc)
    _fails.pop(('reset', uid), None)
    session_drop(uid=uid)                                 # 다른 곳에 로그인된 세션은 모두 로그아웃
    log.info('비밀번호 재설정: %s', uid)
    return {'status': 'ok'}


def api_change_pw(acc, b):
    """로그인한 사람이 지금 비밀번호를 알고 새 비밀번호로 바꿈. 다른 곳에 로그인된 세션은 모두 끊고, 이 화면에는 새 로그인 토큰을 줌"""
    uid = acc['id']
    fail_check(('chpw', uid))
    pw = check_pw(b.get('newPassword'))
    with LOCK:
        cur = load_account(uid)
        if not cur or not hmac.compare_digest(kdf(str(b.get('password') or ''), cur['salt']), cur['hash']):
            fail_add(('chpw', uid))
            raise ApiError(401, '지금 비밀번호가 맞지 않습니다')
        if hmac.compare_digest(kdf(pw, cur['salt']), cur['hash']):
            raise ApiError(400, '지금 비밀번호와 다른 비밀번호를 입력하세요')
        cur['salt'] = os.urandom(16).hex()
        cur.update(hash=kdf(pw, cur['salt']), pwChangedAt=stamp())
        write_json(acc_path(uid), cur)
    _fails.pop(('chpw', uid), None)
    session_drop(uid=uid)
    log.info('비밀번호 변경: %s', uid)
    return {'status': 'ok', 'token': session_new(uid), 'user': acc_public(cur)}


def all_accounts():
    out = []
    for n in list_json(P('accounts')):
        a = read_json(P('accounts', n)) if not n.startswith('_') else None
        if a and a.get('id'):
            out.append(a)
    return out


def api_ping(acc, admin=False):
    now = time.time()
    users = [{**acc_public(a), 'online': now - _presence.get(a['id'], 0) < ONLINE_SEC} for a in all_accounts()]
    users.sort(key=lambda u: (not u['online'], u['name']))
    unread = sum(1 for n in list_json(P('messages', acc['id'], 'in')) if not (read_json(P('messages', acc['id'], 'in', n)) or {}).get('read'))
    return {'users': users, 'unread': unread, 'perms': perms_for(acc, admin)}   # 권한이 바뀌면 30초 안에 화면에 반영


# ---------------------------------------------------------------- 사용자가 추가한 열 (data/_meta/sheet-columns.json)
COLNAME_RE = re.compile(r'^[^.<>\r\n]{1,30}$')


def sheet_cols():
    return read_json(P('data', '_meta', 'sheet-columns.json')) or {}


def api_sheetcol_add(b):
    key, name = str(b.get('sheet') or ''), re.sub(r'\s+', ' ', str(b.get('f') or '')).strip()
    if key not in SHEETS or key == 'staffing':
        raise ApiError(400, '열을 추가할 수 없는 시트입니다')
    if not COLNAME_RE.match(name):
        raise ApiError(400, "열 이름은 30자 이내로, 점(.) 없이 입력하세요")
    with LOCK:
        d = sheet_cols()
        cols = d.setdefault(key, [])
        if any(c['f'] == name for c in cols) or name in (b.get('base') or []):
            raise ApiError(409, '같은 이름의 열이 이미 있습니다')
        cols.append({'f': name, 'w': max(60, min(600, int(b.get('w') or 140))), 'long': bool(b.get('long')), 'by': b.get('by'), 'at': stamp()})
        write_json(P('data', '_meta', 'sheet-columns.json'), d)
    log.info('열 추가: %s / %s by %s', key, name, b.get('by'))
    return {'status': 'ok', 'sheetCols': d}


def api_sheetcol_del(key, name, by):
    with LOCK:
        d = sheet_cols()
        before = len(d.get(key, []))
        d[key] = [c for c in d.get(key, []) if c['f'] != name]
        if len(d[key]) == before:
            raise ApiError(404, '없는 열입니다')
        write_json(P('data', '_meta', 'sheet-columns.json'), d)
    log.info('열 삭제(값은 행에 남음): %s / %s by %s', key, name, by)
    return {'status': 'ok', 'sheetCols': d}


# ---------------------------------------------------------------- 월말 시수(Man-hour) 파일 → timesheets/{YYYY}/{ID}_{YYYY-MM}.json
# xlsx 를 표준 라이브러리(zipfile + ElementTree)로 읽는다. 머리글 'Type'·'Project' 가 있는 시트, 그 오른쪽 01~31 날짜 칸의 시간을 합산.
X_NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R_NS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
MONTH_RE = re.compile(r'^(\d{4})\s*[-./년]\s*(\d{1,2})\s*월?$')
TIME_FMT_IDS, DATE_FMT_IDS = {18, 19, 20, 21, 45, 46, 47}, {14, 15, 16, 17, 22}


def xl_col(ref):
    n = 0
    for ch in ref:
        if not ch.isalpha():
            break
        n = n * 26 + ord(ch.upper()) - 64
    return n


def xlsx_sheets(data):
    """[(시트이름, {행: {열: 값}})] — 값: str / float / ('T', 하루비율) 시간서식 / ('D', 일련번호) 날짜서식"""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ApiError(400, '엑셀(.xlsx) 파일만 올릴 수 있습니다 (예전 .xls 는 엑셀에서 .xlsx 로 다시 저장)')
    names = set(z.namelist())
    ss = []
    if 'xl/sharedStrings.xml' in names:
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(X_NS + 'si'):
            ss.append(''.join(t.text or '' for t in si.iter(X_NS + 't')))
    kinds = []                                            # cellXfs 순서대로 'T'(시간) / 'D'(날짜) / ''
    if 'xl/styles.xml' in names:
        st = ET.fromstring(z.read('xl/styles.xml'))
        custom = {int(f.get('numFmtId')): f.get('formatCode', '') for f in st.iter(X_NS + 'numFmt')}
        xfs = st.find(X_NS + 'cellXfs')
        for xf in (list(xfs) if xfs is not None else []):
            i = int(xf.get('numFmtId') or 0)
            code = re.sub(r'"[^"]*"|\\.', '', custom.get(i, '')).lower()
            code = re.sub(r'\[(?!h+\]|m+\]|s+\])[^\]]*\]', '', code)
            tm = i in TIME_FMT_IDS or 'h' in code or '[m' in code
            dt = i in DATE_FMT_IDS or 'y' in code or 'd' in code
            kinds.append('T' if tm and not ('y' in code or 'd' in code) else 'D' if dt else '')
    rels = {}
    if 'xl/_rels/workbook.xml.rels' in names:
        for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')):
            rels[r.get('Id')] = r.get('Target', '')
    out = []
    for sh in ET.fromstring(z.read('xl/workbook.xml')).iter(X_NS + 'sheet'):
        t = rels.get(sh.get(R_NS + 'id'), '')
        path = t.lstrip('/') if t.startswith('/') else 'xl/' + t
        if path not in names:
            continue
        cells = {}
        for c in ET.fromstring(z.read(path)).iter(X_NS + 'c'):
            ref = c.get('r') or ''
            m = re.match(r'([A-Z]+)(\d+)$', ref)
            if not m or int(m[2]) > 3000:
                continue
            typ, v = c.get('t'), c.find(X_NS + 'v')
            if typ == 's' and v is not None:
                val = ss[int(v.text)]
            elif typ == 'inlineStr':
                val = ''.join(x.text or '' for x in c.iter(X_NS + 't'))
            elif typ in ('str', 'e', 'b'):
                val = (v.text or '') if v is not None else ''
            elif v is not None and v.text:
                try:
                    val = float(v.text)
                except ValueError:
                    val = v.text
                k = int(c.get('s') or 0)
                if isinstance(val, float) and k < len(kinds) and kinds[k]:
                    val = (kinds[k], val)
            else:
                continue
            cells.setdefault(int(m[2]), {})[xl_col(m[1])] = val
        out.append((sh.get('name') or '', cells))
    return out


def xl_date(v):
    return datetime.date(1899, 12, 30) + datetime.timedelta(days=int(v))


def ts_text(v):
    if isinstance(v, tuple):
        v = v[1]
    if isinstance(v, float):
        return str(int(v)) if v == int(v) else str(v)
    return re.sub(r'\s+', ' ', str(v or '')).strip()


def parse_timesheet(data):
    for sname, cells in xlsx_sheets(data):
        hdr, cmap = None, {}
        for r in sorted(cells)[:80]:                        # 머리글이 두 줄로 나뉜 양식(1행 Project·Work, 2행 Type·Detail)도 찾음
            cmap = {}
            for rr in (r, r + 1):
                for c, v in cells.get(rr, {}).items():
                    if isinstance(v, str) and v.strip():
                        cmap.setdefault(v.strip().lower(), c)
            if 'type' in cmap and 'project' in cmap:
                hdr = r + 1 if any(isinstance(v, str) and v.strip().lower() in ('type', 'project') for v in cells.get(r + 1, {}).values()) else r
                break
        if not hdr:
            continue
        tc, pc = cmap['type'], cmap['project']
        dc, wc = cmap.get('detail'), cmap.get('work')
        left = max(c for c in (tc, pc, dc, wc) if c)
        days, day_row, month = {}, hdr, ''
        for r in range(max(1, hdr - 5), hdr + 4):           # 01~31 날짜 줄 (숫자·'01' 글자·날짜서식 모두)
            cand = {}
            for c, v in cells.get(r, {}).items():
                if c <= left:
                    continue
                d = None
                if isinstance(v, tuple) and v[0] == 'D' or isinstance(v, float) and v > 20000:
                    dt = xl_date(v[1] if isinstance(v, tuple) else v)
                    d, month = dt.day, month or f'{dt.year}-{dt.month:02d}'
                elif isinstance(v, (float, tuple)):
                    x = v[1] if isinstance(v, tuple) else v
                    d = int(x) if x == int(x) and 1 <= x <= 31 else None
                elif isinstance(v, str) and re.fullmatch(r'\d{1,2}', v.strip()) and 1 <= int(v) <= 31:
                    d = int(v)
                if d:
                    cand[c] = d
            if len(cand) >= 20:
                days, day_row = cand, r
                break
        if not days:
            raise ApiError(400, f"'{sname}' 시트에서 날짜(01~31) 줄을 찾지 못했습니다")
        for r in range(1, max(hdr, day_row) + 1):           # 월: '2026-07' 같은 글자
            for v in cells.get(r, {}).values():
                m = MONTH_RE.match(v.strip()) if isinstance(v, str) else None
                if m and 1 <= int(m[2]) <= 12:
                    month = f'{m[1]}-{int(m[2]):02d}'
        top = max(hdr, day_row)
        nums = [v for r, row in cells.items() if r > top for c, v in row.items() if c in days and isinstance(v, float)]
        frac = all(v <= 1 for v in nums)                     # 서식 정보가 없는 숫자: 모두 1 이하면 '하루 비율'(시간 서식)로 봄

        def hours(v):
            if isinstance(v, tuple):
                return v[1] * 24 if v[0] == 'T' else 0
            if isinstance(v, float):
                return v * 24 if frac else v
            m = re.fullmatch(r'\s*(\d{1,3}):(\d{2})(?::\d{2})?\s*', str(v or ''))
            return int(m[1]) + int(m[2]) / 60 if m else 0
        rows = []
        for r in sorted(cells):
            if r <= top:
                continue
            row = cells[r]
            if any(isinstance(v, str) and v.strip().lower() in ('total', '합계') for c, v in row.items() if c not in days):
                continue
            typ, code = ts_text(row.get(tc)), ts_text(row.get(pc)).upper()
            dh = {}
            for c, d in days.items():
                h = hours(row.get(c))
                if h > 0:
                    dh[str(d)] = round(dh.get(str(d), 0) + h, 4)
            if not typ and not code and not dh:
                continue
            rows.append({'type': typ, 'detail': ts_text(row.get(dc)) if dc else '', 'code': code, 'work': ts_text(row.get(wc)) if wc else '',
                         'days': dh, 'h': round(sum(dh.values()), 4)})
        return {'month': month, 'rows': rows, 'sheet': sname}
    raise ApiError(400, "머리글에 'Type'·'Project' 가 있는 시트를 찾지 못했습니다 (시수 입력 양식인지 확인)")


def ts_path(month, pid, ext='.json'):
    return P('timesheets', month[:4], f'{pid}_{month}{ext}')


def api_ts_put(acc, can_all, q, data):
    pid = str(q.get('person') or acc['id']).strip().lower()
    if pid != acc['id'] and not can_all:
        raise ApiError(403, '다른 부서원의 시수 파일은 Management 권한자만 올릴 수 있습니다')
    target = load_account(pid)
    if not target:
        raise ApiError(404, '없는 계정입니다')
    if not data:
        raise ApiError(400, '빈 파일입니다')
    res = parse_timesheet(data)
    month = str(q.get('month') or '') if q.get('useMonth') == '1' else (res['month'] or str(q.get('month') or ''))   # 화면에서 고른 월을 우선(useMonth=1)
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month):
        raise ApiError(400, '파일에서 월(예: 2026-07)을 찾지 못했습니다. 월을 고르고 다시 올리세요')
    if not res['rows']:
        raise ApiError(400, '시수가 입력된 줄이 없습니다')
    rec = {'person': target['name'], 'personId': pid, 'month': month, 'file': os.path.basename(str(q.get('name') or ''))[:120],
           'sheet': res['sheet'], 'uploadedBy': acc['name'], 'at': stamp(), 'rows': res['rows']}
    with LOCK:
        write_json(ts_path(month, pid), rec)
        os.makedirs(P('timesheets', month[:4], 'raw'), exist_ok=True)
        with open(P('timesheets', month[:4], 'raw', f'{pid}_{month}.xlsx'), 'wb') as f:
            f.write(data)
    log.info('시수 업로드: %s %s (%d줄) by %s', pid, month, len(res['rows']), acc['id'])
    return {'status': 'ok', 'person': target['name'], 'month': month, 'rows': len(res['rows']), 'detected': res['month']}


def api_ts_preview(data):
    """저장하지 않고 읽기만 — 올리기 전에 화면에서 월·줄·시간을 확인 (본인 손에 있는 파일이라 시간 그대로)"""
    if not data:
        raise ApiError(400, '빈 파일입니다')
    res = parse_timesheet(data)
    return {'month': res['month'], 'sheet': res['sheet'], 'rows': [{k: r[k] for k in ('type', 'detail', 'code', 'work', 'h')} | {'days': len(r['days'])} for r in res['rows']],
            'total': round(sum(r['h'] for r in res['rows']), 4)}


def api_ts_list(year, can_hours):
    """시수 목록. Management 권한이 없으면 실제 시간 대신 '사람·연도별 합계 = 100' 비율 단위(v)로만 보냄"""
    if not re.fullmatch(r'\d{4}', year or ''):
        raise ApiError(400, '잘못된 연도')
    lst = [x for x in (read_json(P('timesheets', year, n)) for n in list_json(P('timesheets', year))) if x]
    tot = {}
    for x in lst:
        tot[x['personId']] = tot.get(x['personId'], 0) + sum(r.get('h', 0) for r in x['rows'])
    out = []
    for x in sorted(lst, key=lambda x: (x['person'], x['month'])):
        k = 1 if can_hours else (100 / tot[x['personId']] if tot[x['personId']] else 0)
        out.append({**{f: x.get(f) for f in ('person', 'personId', 'month', 'file', 'uploadedBy', 'at')},
                    'rows': [{'type': r['type'], 'detail': r.get('detail', ''), 'code': r['code'], 'work': r.get('work', ''), 'v': round(r.get('h', 0) * k, 4),
                              **({'days': r.get('days') or {}} if can_hours else {})} for r in x['rows']]})   # 일별 시간(날짜 → h)은 Management 권한자만 (근무시간 화면)
    try:
        years = sorted(n for n in os.listdir(P('timesheets')) if re.fullmatch(r'\d{4}', n))
    except FileNotFoundError:
        years = []
    return {'year': year, 'canHours': can_hours, 'list': out, 'years': years}


def api_ts_delete(acc, can_all, pid, month):
    if not (UID_RE.match(pid or '') and re.fullmatch(r'\d{4}-\d{2}', month or '')):
        raise ApiError(400, '잘못된 요청')
    if pid != acc['id'] and not can_all:
        raise ApiError(403, '본인 것 또는 Management 권한자만 지울 수 있습니다')
    with LOCK:
        if not os.path.exists(ts_path(month, pid)):
            raise ApiError(404, '없는 시수 파일입니다')
        os.remove(ts_path(month, pid))
        raw = P('timesheets', month[:4], 'raw', f'{pid}_{month}.xlsx')     # 올린 원본 엑셀도 함께 지움
        if os.path.exists(raw):
            os.remove(raw)
    log.info('시수 삭제: %s %s by %s', pid, month, acc['id'])
    return {'status': 'ok'}


# ---------------------------------------------------------------- 행 순서 바꾸기 (수행·입찰·통합 업무: 선택한 행 위로/아래로) — 내용(rev)은 그대로, order 만
def api_reorder(key, b, by):
    orders = b.get('orders') or {}
    if not isinstance(orders, dict) or not 0 < len(orders) <= 50:
        raise ApiError(400, '잘못된 요청')
    with LOCK:
        recs = {}
        for rid, o in orders.items():
            if not ID_RE.match(str(rid)) or not isinstance(o, (int, float)):
                raise ApiError(400, '잘못된 요청')
            cur = read_json(P('data', key, rid + '.json'))
            if not cur:
                raise ApiError(404, '삭제된 행이 있습니다. 새로고침하세요')
            recs[rid] = cur
        for rid, cur in recs.items():
            write_json(P('data', key, rid + '.json'), {**cur, 'order': orders[rid]})
    log.info('행 순서 변경: %s %s by %s', key, ','.join(orders), by)
    return {'status': 'ok'}


# ---------------------------------------------------------------- 부서원 생일 (profiles/_birthdays.json) — 하루 전·당일 축하 팝업, 당일 고깔모자
# Management 권한자가 엑셀(이름 · 직급 · 생일 '10월 13일' · 양력 '생일(양)/생일(음)')을 올리거나 화면에서 고침. 연도는 저장하지 않음(월·일만)
BDAY_RE = re.compile(r'(\d{1,2})\s*(?:월|[-./])\s*(\d{1,2})')


def bday_path():
    return P('profiles', '_birthdays.json')


def bday_clean(lst):
    out = []
    for x in (lst or [])[:300]:
        if not isinstance(x, dict):
            continue
        name = re.sub(r'\s+', ' ', str(x.get('name') or '')).strip()[:40]
        m = BDAY_RE.search(str(x.get('md') or ''))
        if not name or not m or not (1 <= int(m[1]) <= 12 and 1 <= int(m[2]) <= 31):
            continue
        out.append({'name': name, 'title': re.sub(r'\s+', ' ', str(x.get('title') or '')).strip()[:20],
                    'md': f'{int(m[1]):02d}-{int(m[2]):02d}', 'lunar': bool(x.get('lunar'))})
    return out


def parse_birthdays(data):
    for sname, cells in xlsx_sheets(data):
        for r in sorted(cells)[:40]:
            hm = {re.sub(r'\s+', '', v): c for c, v in cells[r].items() if isinstance(v, str)}
            nc = hm.get('이름') or hm.get('성명')
            bc = hm.get('생일') or hm.get('생년월일')
            if not (nc and bc):
                continue
            tc, lc = hm.get('직급') or hm.get('직책'), hm.get('양력') or hm.get('음력') or hm.get('양력/음력') or hm.get('구분')
            out = []
            for rr in sorted(x for x in cells if x > r):
                row = cells[rr]
                name, v = ts_text(row.get(nc)), row.get(bc)
                if not name or v in (None, ''):
                    continue
                if isinstance(v, tuple) or isinstance(v, float) and v > 20000:
                    d = xl_date(v[1] if isinstance(v, tuple) else v)
                    md = f'{d.month:02d}-{d.day:02d}'
                else:
                    md = ts_text(v)
                kind = ts_text(row.get(lc)) if lc else ''
                out.append({'name': name, 'title': ts_text(row.get(tc)) if tc else '', 'md': md, 'lunar': '음' in kind})
            return bday_clean(out)
    raise ApiError(400, "머리글에 '이름'·'생일' 이 있는 시트를 찾지 못했습니다")


def api_bday_get(acc=None):
    d = read_json(bday_path()) or {}
    out = {'list': d.get('list', []), 'updatedAt': d.get('updatedAt', ''), 'updatedBy': d.get('updatedBy', '')}
    if acc:                                               # 로그인한 사람이 '오늘 하루 안 보기' 를 누른 키 (다른 PC 에서 누른 것도)
        out['hidden'] = (read_json(P('profiles', '_bdhide.json')) or {}).get(acc['id'], [])
    return out


def api_bday_hide(acc, b):
    """생일 팝업 '오늘 하루 안 보기' — 계정마다 서버에 기록 (키 = 'YYYY-MM-DD|생일자|계정ID', 화면이 만듦). 오늘·어제 것만 남김"""
    key = str(b.get('key') or '')[:300]
    m = re.match(r'^(\d{4}-\d{2}-\d{2})\|', key)
    if not m:
        raise ApiError(400, '잘못된 요청')
    keep = {m[1], (datetime.date.fromisoformat(m[1]) - datetime.timedelta(days=1)).isoformat()}
    with LOCK:
        d = read_json(P('profiles', '_bdhide.json')) or {}
        lst = [k for k in d.get(acc['id'], []) if k[:10] in keep and k != key] + [key]
        d[acc['id']] = lst[-20:]
        d = {u: v for u, v in d.items() if any(k[:10] in keep for k in v)}
        write_json(P('profiles', '_bdhide.json'), d)
    return {'status': 'ok', 'hidden': d.get(acc['id'], [])}


def api_bday_put(b, by):
    lst = bday_clean(b.get('list'))
    with LOCK:
        write_json(bday_path(), {'list': lst, 'updatedAt': stamp(), 'updatedBy': by})
    log.info('부서원 생일 저장: %d명 by %s', len(lst), by)
    return api_bday_get()


# ---------------------------------------------------------------- 근로시간 관리 (worktime/uploads/{ID}.json) — 회사 근태 시스템의 월별 근무시간 엑셀
# 양식: 1~2행 머리글(작업년월 · 성명 · 사번 · 부서명 · 직급명 · … · 실근무(평일+휴일) 상태/시간 · 주평균근무 상태/시간 · 연장 · 심야 · 휴일 · 휴일연장 · 탄력 · 월잔여 …)
# 같은 사람·같은 달이 여러 파일에 있으면 화면에서 나중에 올린 파일 값을 씀. 파일을 지우면 그 파일 값만 빠짐
WT_COLS = {'작업년월': 'month', '성명': 'name', '사번': 'empNo', '부서명': 'dept', '직급명': 'title', '근무스케줄타입': 'sched', '근무조': 'shift',
           '근무상태': 'state', '평일의무근로시간': 'wdReq', '평일근무시간': 'wdWork', '실근무(평일+휴일)|상태': 'realState', '실근무(평일+휴일)|시간': 'realH',
           '주평균근무|상태': 'wkState', '주평균근무|시간': 'wkH', '연장근로시간': 'ot', '심야근무시간': 'night', '휴일근무시간': 'hol', '휴일연장근로시간': 'holOt',
           '탄력': 'flex', '탄력근무(+)': 'flexP', '탄력근무(-)': 'flexM', '월잔여최대근무가능시간': 'remainMax', '월잔여소정근로시간': 'remainStd'}
WT_TEXT = {'month', 'name', 'empNo', 'dept', 'title', 'sched', 'shift', 'state', 'realState', 'wkState'}
WT_ID_RE = re.compile(r'^wt-[0-9a-f]{6,40}$')


def wt_hours(v):
    if isinstance(v, tuple):
        return round(v[1] * 24, 4) if v[0] == 'T' else None
    if isinstance(v, float):
        return v
    s = str(v or '').strip()
    m = re.fullmatch(r'(-?\d{1,4}):(\d{2})(?::\d{2})?', s)
    if m:
        h = abs(int(m[1])) + int(m[2]) / 60
        return round(-h if s.startswith('-') else h, 4)
    try:
        return float(s.replace(',', ''))
    except ValueError:
        return None


def wt_month(v):
    if isinstance(v, tuple) or isinstance(v, float) and v > 20000:
        d = xl_date(v[1] if isinstance(v, tuple) else v)
        return f'{d.year}-{d.month:02d}'
    if isinstance(v, float):                              # 2026.1 = 2026.10 (숫자로 저장된 경우)
        y, mm = int(v), round((v - int(v)) * 100)
        return f'{y}-{mm:02d}' if 1 <= mm <= 12 else ''
    m = re.search(r'(\d{4})\s*[-./년]\s*(\d{1,2})', str(v or ''))
    return f'{m[1]}-{int(m[2]):02d}' if m and 1 <= int(m[2]) <= 12 else ''


def parse_worktime(data):
    for sname, cells in xlsx_sheets(data):
        for r in sorted(cells)[:20]:
            top = {c: re.sub(r'\s+', '', v) for c, v in cells[r].items() if isinstance(v, str)}
            if '성명' not in top.values() or '작업년월' not in top.values():
                continue
            sub = {c: re.sub(r'\s+', '', v) for c, v in cells.get(r + 1, {}).items() if isinstance(v, str)}
            two = '작업년월' in sub.values() or '상태' in sub.values()
            cmap, last = {}, ''
            for c in sorted(set(top) | set(sub)):
                h1 = top.get(c) or ''
                h1 = h1 or (last if two else '')
                last = h1 or last
                h2 = sub.get(c, '') if two else ''
                for k in ((h1 + '|' + h2) if h2 in ('상태', '시간') else '', h2, h1):
                    if k and k in WT_COLS and WT_COLS[k] not in cmap.values():
                        cmap[c] = WT_COLS[k]
                        break
            if 'name' not in cmap.values():
                continue
            start, rows = r + (2 if two else 1), []
            for rr in sorted(x for x in cells if x >= start):
                row, o = cells[rr], {}
                for c, f in cmap.items():
                    v = row.get(c)
                    if v in (None, ''):
                        continue
                    o[f] = wt_month(v) if f == 'month' else ts_text(v)[:60] if f in WT_TEXT else wt_hours(v)
                if not o.get('name') or not o.get('month'):
                    continue
                rows.append({k: v for k, v in o.items() if v not in (None, '', '-')})
            if rows:
                return {'sheet': sname, 'rows': rows}
    raise ApiError(400, "머리글에 '작업년월'·'성명' 이 있는 근무시간 표를 찾지 못했습니다")


def api_wt_list():
    ups = [x for x in (read_json(P('worktime', 'uploads', n)) for n in list_json(P('worktime', 'uploads'))) if x]
    return {'uploads': sorted(ups, key=lambda x: x.get('at', ''))}


def api_wt_put(acc, q, data):
    if not data:
        raise ApiError(400, '빈 파일입니다')
    res = parse_worktime(data)
    uid = 'wt-' + os.urandom(6).hex()
    rec = {'id': uid, 'file': os.path.basename(str(q.get('name') or ''))[:120], 'sheet': res['sheet'], 'by': acc['name'], 'at': stamp(),
           'months': sorted({r['month'] for r in res['rows']}), 'people': len({r['name'] for r in res['rows']}), 'rows': res['rows']}
    with LOCK:
        write_json(P('worktime', 'uploads', uid + '.json'), rec)
        os.makedirs(P('worktime', 'raw'), exist_ok=True)
        with open(P('worktime', 'raw', uid + '.xlsx'), 'wb') as f:
            f.write(data)
    log.info('근무시간 엑셀 업로드: %s (%d줄) by %s', uid, len(res['rows']), acc['id'])
    return {'status': 'ok', 'id': uid, 'rows': len(res['rows']), 'months': rec['months'], 'people': rec['people']}


def api_wt_delete(uid, by):
    if not WT_ID_RE.match(uid or ''):
        raise ApiError(400, '잘못된 요청')
    with LOCK:
        p = P('worktime', 'uploads', uid + '.json')
        if not os.path.exists(p):
            raise ApiError(404, '없는 파일입니다')
        os.remove(p)
        raw = P('worktime', 'raw', uid + '.xlsx')
        if os.path.exists(raw):
            os.remove(raw)
    log.info('근무시간 엑셀 삭제: %s by %s', uid, by)
    return {'status': 'ok'}

# ---------------------------------------------------------------- 부서원 프로필 (profiles/{ID}.json) — 유닛분장 조직도에 표시
PHOTO_RE = re.compile(r'^data:image/(?:jpeg|png|webp);base64,[A-Za-z0-9+/=]+$')
PHONE_RE = re.compile(r'^[^<>\r\n]{0,30}$')                     # 예: 010-1234-5678, 내선 1234


def prof_path(uid):
    return P('profiles', uid + '.json')


def api_profiles(logged_in):
    """모든 계정의 프로필. 전화번호는 로그인한 사람에게만"""
    out = []
    for a in all_accounts():
        p = read_json(prof_path(a['id'])) or {}
        d = {'id': a['id'], 'name': a['name'], 'duty': p.get('duty', ''), 'run': p.get('run', []), 'bid': p.get('bid', []),
             'photo': p.get('photo', ''), 'updatedAt': p.get('updatedAt', '')}
        if logged_in:
            d['phone'] = p.get('phone', '')
        out.append(d)
    return {'profiles': out}


def prof_list(v):
    if not isinstance(v, list):
        return []
    out = []
    for x in v[:40]:
        x = re.sub(r'\s+', ' ', str(x or '')).strip()[:100]
        if x and x not in out:
            out.append(x)
    return out


def api_profile_put(acc, b):
    phone = str(b.get('phone') or '').strip()
    if not PHONE_RE.match(phone):
        raise ApiError(400, '전화번호는 30자 이내로 입력하세요')
    duty = re.sub(r'\s+', ' ', str(b.get('duty') or '')).strip()[:100]
    with LOCK:
        cur = read_json(prof_path(acc['id'])) or {}
        photo = cur.get('photo', '')
        if 'photo' in b:
            photo = str(b.get('photo') or '')
            if photo and (len(photo) > 400_000 or not PHOTO_RE.match(photo)):
                raise ApiError(400, '사진은 JPG·PNG 이미지만, 300KB 이하로 올릴 수 있습니다')
        rec = {'id': acc['id'], 'phone': phone, 'duty': duty, 'run': prof_list(b.get('run')), 'bid': prof_list(b.get('bid')),
               'photo': photo, 'updatedAt': stamp()}
        write_json(prof_path(acc['id']), rec)
    log.info('프로필 저장: %s', acc['id'])
    return {'status': 'ok'}


# ---------------------------------------------------------------- 메뉴 권한 (accounts/_perms.json) — 운영자(서버 PC)만 변경
MENUS = [('weekly', '주간업무보고'), ('pid', 'P&ID 분석'), ('logic', 'LOGIC 분석'), ('bidpjt', '입찰 프로젝트'), ('runpjt', '실행 프로젝트'),
         ('board', '익명게시판'), ('mgmt', 'Management')]
MENU_KEYS = [k for k, _ in MENUS]
DEFAULT_PERMS = {k: k != 'mgmt' for k in MENU_KEYS}
SUPER_NAMES = ('구종현',)   # 2026-10-22 그룹장: 운영자와 같은 권한 (금주 마감 · 휴지통 영구삭제 · 게시판 관리 삭제 · 모든 메뉴) — 메뉴 권한 설정(부서원 권한 주기)만 운영자   # 기본: 모두 허용, Management 만 권한 부여 필요


def perms_file():
    return read_json(P('accounts', '_perms.json')) or {}


def perms_for(acc, admin=False):
    """메뉴별 접근 권한. 운영자(서버 PC 접속)는 전부 허용. acc=None 이면 비회원"""
    if admin:
        return {k: True for k in MENU_KEYS}
    f = perms_file()
    own = (f.get('users') or {}).get(acc['id']) if acc else f.get('guest')
    return {k: bool((own or {}).get(k, DEFAULT_PERMS[k])) for k in MENU_KEYS}


def api_perms_get():
    f = perms_file()
    users = [{**acc_public(a), 'perms': perms_for(a)} for a in sorted(all_accounts(), key=lambda a: a['name'])]
    return {'menus': [{'k': k, 'l': l} for k, l in MENUS], 'defaults': DEFAULT_PERMS, 'users': users,
            'guest': perms_for(None), 'updatedAt': f.get('updatedAt'), 'updatedBy': f.get('updatedBy')}


def api_perms_put(b, by):
    clean = lambda p: {k: bool((p or {}).get(k, DEFAULT_PERMS[k])) for k in MENU_KEYS}
    ids = {a['id'] for a in all_accounts()}
    with LOCK:
        f = {'users': {uid: clean(p) for uid, p in (b.get('users') or {}).items() if uid in ids},
             'guest': clean(b.get('guest')), 'updatedAt': stamp(), 'updatedBy': by}
        write_json(P('accounts', '_perms.json'), f)
    log.info('메뉴 권한 변경 by %s', by)
    return api_perms_get()


# ---------------------------------------------------------------- 쪽지 (messages/{ID}/in|sent/{쪽지ID}.json)
def api_msg_list(acc):
    def box(kind):
        d = P('messages', acc['id'], kind)
        return sorted((m for m in (read_json(os.path.join(d, n)) for n in list_json(d)) if m), key=lambda m: m.get('at', ''), reverse=True)[:200]
    return {'inbox': box('in'), 'sent': box('sent')}


def api_msg_send(acc, b):
    to = load_account(str(b.get('to') or '').strip().lower())
    if not to:
        raise ApiError(404, '받는 사람 계정이 없습니다')
    body = board_text(b, 'body', 1000)
    with LOCK:
        mid = f"m{int(time.time() * 1000):x}{os.urandom(3).hex()}"
        m = {'id': mid, 'from': acc['id'], 'fromName': acc['name'], 'to': to['id'], 'toName': to['name'], 'body': body, 'at': stamp(), 'read': False}
        write_json(P('messages', to['id'], 'in', mid + '.json'), m)
        write_json(P('messages', acc['id'], 'sent', mid + '.json'), m)
    return {'status': 'ok', 'msg': m}


def api_msg_read(acc, mid):
    if not ID_RE.match(mid):
        raise ApiError(400, '잘못된 ID')
    with LOCK:
        path = P('messages', acc['id'], 'in', mid + '.json')
        m = read_json(path)
        if not m:
            raise ApiError(404, '삭제된 쪽지입니다')
        if not m.get('read'):
            m.update(read=True, readAt=stamp())
            write_json(path, m)
            sp = P('messages', m['from'], 'sent', mid + '.json')   # 보낸 사람 쪽에도 '읽음' 표시
            s = read_json(sp)
            if s:
                write_json(sp, {**s, 'read': True, 'readAt': m['readAt']})
    return {'status': 'ok'}


def api_msg_delete(acc, kind, mid):
    if kind not in ('in', 'sent') or not ID_RE.match(mid):
        raise ApiError(400, '잘못된 요청')
    with LOCK:
        path = P('messages', acc['id'], kind, mid + '.json')
        if os.path.exists(path):
            os.remove(path)
    return {'status': 'ok'}


def prune_messages(days):
    """쪽지는 days 일 지나면 자동 삭제"""
    lim = ago_z(days)
    with LOCK:
        for uid in (os.listdir(P('messages')) if os.path.isdir(P('messages')) else []):
            for kind in ('in', 'sent'):
                d = P('messages', uid, kind)
                for n in list_json(d):
                    if (read_json(os.path.join(d, n)) or {}).get('at', '') < lim:
                        os.remove(os.path.join(d, n))


# ---------------------------------------------------------------- 자동 백업
def make_backup(keep_days):
    day = datetime.date.today().isoformat()
    dest = P('backup', f'{day}.zip')
    if os.path.exists(dest):
        return
    os.makedirs(P('backup'), exist_ok=True)
    tmp = dest + '.tmp'
    with LOCK:                                            # 백업 중에는 쓰기를 잠시 멈춰 일관된 스냅샷 확보
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
            for top in ('data', 'history', 'archive', 'trash', 'saves', 'board', 'accounts', 'messages', 'files', 'profiles', 'timesheets', 'worktime'):
                for dirpath, _, files in os.walk(P(top)):
                    for fn in files:
                        if fn.endswith('.tmp'):
                            continue
                        full = os.path.join(dirpath, fn)
                        z.write(full, os.path.relpath(full, ROOT))
    os.replace(tmp, dest)
    log.info('자동 백업 완료: backup/%s.zip', day)
    limit = datetime.date.today() - datetime.timedelta(days=keep_days)
    for n in os.listdir(P('backup')):
        m = re.fullmatch(r'(\d{4}-\d{2}-\d{2})\.zip', n)
        if m and datetime.date.fromisoformat(m[1]) < limit:
            os.remove(P('backup', n))
            log.info('오래된 백업 삭제: %s', n)


def prune_history(days):
    """수정 이력은 days 일만 보관: 파일명 앞 24자(저장 시각, UTC)가 기준보다 오래되면 삭제"""
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    cutoff = t.strftime('%Y-%m-%dT%H-%M-%S-') + f'{t.microsecond // 1000:03d}Z'
    removed = 0
    with LOCK:
        for k in SHEETS:
            base = P('history', k)
            if not os.path.isdir(base):
                continue
            for rid in os.listdir(base):
                d = os.path.join(base, rid)
                if not os.path.isdir(d):
                    continue
                for n in list_json(d):
                    if n[:24] < cutoff:
                        os.remove(os.path.join(d, n)); removed += 1
                if not os.listdir(d):
                    os.rmdir(d)
    if removed:
        log.info('수정 이력 정리: %d일 지난 이력 %d건 삭제', days, removed)


def backup_loop(keep_days, history_days):
    while True:
        try:
            make_backup(keep_days)
        except Exception as e:
            log.error('백업 실패: %s', e)
        try:
            prune_history(history_days)
        except Exception as e:
            log.error('이력 정리 실패: %s', e)
        try:
            prune_messages(180)
        except Exception as e:
            log.error('쪽지 정리 실패: %s', e)
        time.sleep(3600)                                  # 1시간마다 확인 (백업은 하루 1개)


# ---------------------------------------------------------------- HTTP
def server_urls():
    """부서원 사본이 접속할 주소: PC 이름 주소 → IP 주소"""
    return [f'http://{socket.gethostname()}:{PORT}'] + [f'http://{ip}:{PORT}' for ip in lan_ips()]


def html_bytes():
    """dashboard.html 을 읽어 기본 서버 주소를 이 PC 기준으로 바꿔 제공 (부서원 배포본과 동일)"""
    with open(P('dashboard.html'), encoding='utf-8') as f:
        s = f.read()
    s = re.sub(r"const DEFAULT_SERVERS = \[[^\]]*\];", 'const DEFAULT_SERVERS = ' + json.dumps(server_urls()) + ';', s, count=1)
    return s.encode('utf-8')


_deploy_mtime = None
_deploy_lock = threading.Lock()


def build_deploy():
    with _deploy_lock:                                    # 시작 시·주기 점검이 겹쳐도 한 번에 하나씩
        _build_deploy()


def _build_deploy():
    """운영 폴더 deploy/ 에 부서원 배포용 dashboard.html 과 사용법 안내문 생성 (원본이 바뀌면 다시 생성)"""
    global _deploy_mtime
    m = (os.path.getmtime(P('dashboard.html')), tuple(server_urls()))   # 화면 파일이 바뀌거나 서버 주소(IP)가 바뀌면 다시 만듦
    if m == _deploy_mtime and os.path.exists(P('deploy', 'dashboard.html')):
        return
    os.makedirs(P('deploy'), exist_ok=True)
    tmp = P('deploy', 'dashboard.html.tmp')
    with open(tmp, 'wb') as f:
        f.write(html_bytes())
    os.replace(tmp, P('deploy', 'dashboard.html'))
    urls = server_urls()
    guide = (f'[계장ENG그룹 Dashboard 사용법]  (화면 v{html_version()})\n'
             f'1. 이 폴더의 dashboard.html 을 내 PC(바탕화면 등)에 복사한 뒤 Edge로 엽니다.\n'
             f'2. 처음에 [계정 개설]로 ID·본명·비밀번호를 만들고 로그인합니다. (비회원은 보기만 가능, 수정 이력에는 본명이 기록됩니다)\n'
             f'3. 서버 {urls[0]} 에 자동 연결됩니다. 안 되면 왼쪽 아래 [서버 주소 설정]에 {urls[-1]} 을 입력하세요.\n'
             f'   (서버 PC 가 유선 LAN ↔ 사내 Wi-Fi 로 바뀌면 IP 가 바뀝니다. 한 번 연결된 주소는 내 PC 가 기억해 두고 차례로 시도합니다)\n'
             f'4. 서버가 꺼져 있어도 입력은 내 PC에 보관되며, 서버가 켜지면 자동으로 올라갑니다.\n'
             f'5. 화면 위에 "새 버전이 있습니다"가 뜨면 [다운로드]한 파일로 내 PC의 dashboard.html 을 바꾸세요.\n')
    with open(P('deploy', '부서원_사용법.txt'), 'w', encoding='utf-8-sig') as f:
        f.write(guide)
    _deploy_mtime = m
    log.info('배포 파일 생성: deploy/dashboard.html (v%s), deploy/부서원_사용법.txt', html_version())


def nets_file():
    return P('data', '_meta', 'server-nets.json')


def net_profiles():
    """Windows: 연결된 네트워크마다 종류(Public 공용 / Private 개인 / DomainAuthenticated 도메인). 공용이면 방화벽이 부서원 접속을 막는 경우가 많음"""
    if os.name != 'nt':
        return []
    import subprocess
    try:
        out = subprocess.run(['powershell', '-NoProfile', '-Command',
                              'Get-NetConnectionProfile | Select-Object InterfaceAlias,Name,@{n="Cat";e={[string]$_.NetworkCategory}} | ConvertTo-Json -Compress'],
                             capture_output=True, timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            txt = out.stdout.decode('utf-8').strip()
        except UnicodeDecodeError:                        # 한글 네트워크 이름: 콘솔 코드페이지(cp949)
            txt = out.stdout.decode('cp949', 'replace').strip()
        d = json.loads(txt) if txt else []
        d = d if isinstance(d, list) else [d]
        return [{'alias': x.get('InterfaceAlias') or '', 'name': x.get('Name') or '', 'category': x.get('Cat') or ''} for x in d]
    except Exception as e:
        log.warning('네트워크 종류 확인 실패: %s', e)
        return []


def refresh_nets(first=False):
    """서버 PC 의 IP 가 바뀌었는지(유선 LAN ↔ 사내 Wi-Fi) 확인: 새 IP 의 /16 대역을 허용 목록에 더해 파일에 기억(예전 대역도 계속 허용),
    부서원 배포본(deploy/dashboard.html)의 서버 주소를 새로 만들고, 네트워크 종류를 로그에 남김"""
    global ALLOW_NETS
    ips = lan_ips()
    if ips == NET_STATE['ips'] and not first:
        return
    old = NET_STATE['ips']
    known = set()
    try:
        known = set((read_json(nets_file()) or {}).get('nets') or [])
    except Exception:
        pass
    now = {str(ipaddress.ip_network(f'{ip}/16', strict=False)) for ip in ips}
    if not now <= known:
        known |= now
        try:
            os.makedirs(os.path.dirname(nets_file()), exist_ok=True)
            with open(nets_file(), 'w', encoding='utf-8') as f:
                json.dump({'nets': sorted(known), 'updatedAt': datetime.datetime.now().isoformat(timespec='seconds')}, f, ensure_ascii=False, indent=1)
        except OSError as e:
            log.warning('허용 대역 저장 실패: %s', e)
    ALLOW_NETS = [ipaddress.ip_network(n) for n in sorted(known)] + EXTRA_NETS
    NET_STATE['ips'] = ips
    NET_STATE['profiles'] = net_profiles()
    if old is not None:
        NET_STATE['changedAt'] = datetime.datetime.now().isoformat(timespec='seconds')
        log.warning('서버 PC 의 IP 가 바뀌었습니다: %s → %s (유선/Wi-Fi 전환 등). 부서원 접속 주소: %s', ', '.join(old) or '-', ', '.join(ips) or '-', ', '.join(server_urls()))
    for p_ in NET_STATE['profiles']:
        warn = p_['category'] == 'Public'
        (log.warning if warn else log.info)('네트워크 %s (%s): %s%s', p_['alias'], p_['name'], p_['category'],
                                            ' ← 공용 네트워크: Windows 방화벽이 부서원 접속을 막을 수 있음 → allow_firewall.bat (관리자 권한) 실행' if warn else '')
    log.info('허용 대역: 루프백·사설망 + %s', ', '.join(map(str, ALLOW_NETS)) or '-')


def ip_allowed(ip):
    try:
        a = ipaddress.ip_address(ip.split('%')[0])
    except ValueError:
        return False
    if getattr(a, 'ipv4_mapped', None):
        a = a.ipv4_mapped
    return a.is_loopback or a.is_private or a.is_link_local or any(a in n for n in ALLOW_NETS)


def html_version():
    """운영 폴더 dashboard.html 의 APP_VERSION (부서원 사본과 비교해 새 버전 안내)"""
    try:
        with open(P('dashboard.html'), encoding='utf-8') as f:
            m = re.search(r"const APP_VERSION = '([^']+)'", f.read(200000))
        return m[1] if m else ''
    except OSError:
        return ''


class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg); self.code = code; self.msg = msg


class Handler(BaseHTTPRequestHandler):
    server_version = 'DeptDashboard/1.0'
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *args):
        # 익명게시판 요청은 접속 IP를 남기지 않음 (작성자 추정 방지)
        who = '-' if '/api/board' in (self.path or '') else self.client_address[0]
        log.info('%s %s', who, fmt % args)

    def is_admin(self):
        return self.client_address[0] in ('127.0.0.1', '::1')

    def is_super(self):
        """운영자(서버 PC) 또는 SUPER_NAMES 계정 — 금주 마감 · 휴지통 영구삭제 · 게시판 관리 삭제 · 모든 메뉴 (메뉴 권한 설정만 운영자)"""
        if self.is_admin():
            return True
        acc = session_account(self.token(), False)
        return bool(acc and (acc.get('name') or '').strip() in SUPER_NAMES)

    def origin_ok(self):
        """허용 출처: 없음(직접 접속) / null(부서원 PC의 file:// 사본) / 이 서버 자신의 주소. 그 외 웹페이지에서의 호출은 거부"""
        o = self.headers.get('Origin')
        if not o or o == 'null':
            return True
        u = urlsplit(o)
        if u.netloc.lower() == (self.headers.get('Host') or '').lower():   # 같은 주소로 연 서버 화면 (도메인 별칭 포함)
            return True
        names = {'localhost', '127.0.0.1', socket.gethostname().lower(), *lan_ips()}
        return (u.hostname or '').lower() in names and (u.port or 80) == PORT

    def cors(self):
        # 부서원 PC의 dashboard.html 사본(file:// → Origin: null)과 이 서버 화면에서만 API 호출 허용
        o = self.headers.get('Origin')
        if not o or not self.origin_ok():
            return
        self.send_header('Access-Control-Allow-Origin', o)
        self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Auth-Token')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('Access-Control-Max-Age', '600')

    def send(self, code, body, ctype='application/json; charset=utf-8', extra=None):
        data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.cors()
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        if not ip_allowed(self.client_address[0]) or not self.origin_ok():
            return self.send(403, {'error': '허용되지 않은 접속입니다'})
        self.send_response(204)
        self.cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def raw_body(self):
        if self._raw is None:
            n = int(self.headers.get('Content-Length') or 0)
            if n > MAX_BODY:
                self.close_connection = True                 # 읽지 않은 큰 본문이 남으므로 연결 종료
                raise ApiError(413, '요청이 너무 큽니다')
            self._raw = self.rfile.read(n) if n else b''
        return self._raw

    def json_body(self):
        b = self.raw_body()
        try:
            return json.loads(b.decode('utf-8')) if b else {}
        except ValueError:
            raise ApiError(400, 'JSON 형식 오류')

    def do_GET(self): self.dispatch('GET')
    def do_POST(self): self.dispatch('POST')
    def do_PUT(self): self.dispatch('PUT')
    def do_DELETE(self): self.dispatch('DELETE')

    def dispatch(self, method):
        u = urlsplit(self.path)
        path, q = unquote(u.path), {k: v[0] for k, v in parse_qs(u.query).items()}
        self._raw = None
        try:
            self._dispatch(method, path, q)
        finally:
            # 요청 본문을 읽지 않고 응답한 경우(본문 없는 처리, 401/403 등)에도 남은 본문을 비움
            # → keep-alive 연결에서 다음 요청 앞에 붙어 '{}GET' 처럼 깨지는 것 방지
            if self._raw is None and not self.close_connection:
                try:
                    self.raw_body()
                except ApiError:
                    pass

    def _dispatch(self, method, path, q):
        try:
            if not ip_allowed(self.client_address[0]):              # 사내망 접속만 허용
                raise ApiError(403, f'사내망에서만 접속할 수 있습니다 (이 PC 주소 {self.client_address[0]} 가 허용 대역이 아님 — 서버 관리자: server.py --allow 로 대역 추가)')
            if not self.origin_ok():                                 # 다른 웹페이지에서 API 호출 차단
                raise ApiError(403, '허용되지 않은 출처입니다')
            if method == 'GET' and path in ('/', '/dashboard.html'):
                extra = {'Content-Disposition': "attachment; filename*=UTF-8''dashboard.html"} if 'download' in q else None
                return self.send(200, html_bytes(), 'text/html; charset=utf-8', extra)
            if method == 'GET' and path.startswith('/apps/'):   # 연결 프로그램 정적 파일 (운영 폴더 apps/)
                return self.send_app_file(path[len('/apps/'):])
            if not path.startswith('/api/'):
                raise ApiError(404, '없는 경로')
            r = self.api(method, path[5:].strip('/').split('/'), q)
            if r is not None:                                       # None = 이미 직접 응답함 (첨부파일 내려받기)
                self.send(200, r)
        except ApiError as e:
            self.send(e.code, {'error': e.msg})
        except FileNotFoundError as e:
            self.send(404, {'error': str(e)})
        except Exception as e:
            log.exception('처리 오류')
            self.send(500, {'error': f'서버 오류: {e}'})

    def send_app_file(self, rel):
        """apps/ 아래 파일만 제공 (상위 폴더 접근 차단). 폴더면 index.html"""
        base = os.path.realpath(P('apps'))
        full = os.path.realpath(os.path.join(base, rel))
        if full != base and not full.startswith(base + os.sep):
            raise ApiError(403, '허용되지 않은 경로')
        if os.path.isdir(full):
            full = os.path.join(full, 'index.html')
        if not os.path.isfile(full):
            raise ApiError(404, '없는 파일')
        ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript', 'application/json'):
            ctype += '; charset=utf-8'
        with open(full, 'rb') as f:
            self.send(200, f.read(), ctype)

    def need_admin(self):
        if not self.is_admin():
            raise ApiError(403, '관리자(서버 PC)에서만 사용할 수 있습니다')

    def need_super(self):
        if not self.is_super():
            raise ApiError(403, '관리자(서버 PC) 또는 그룹장만 사용할 수 있습니다')

    def token(self):
        return (self.headers.get('X-Auth-Token') or '').strip()

    def need_user(self, touch=True):
        """로그인한 계정 (비회원은 보기만 가능). touch=False: 접속 표시 시각을 갱신하지 않음(익명게시판)"""
        acc = session_account(self.token(), touch)
        if not acc:
            raise ApiError(401, '로그인이 필요합니다 (비회원은 보기만 할 수 있습니다)')
        return acc

    def body_by(self, menu='weekly'):
        """쓰기 요청 본문 + 수정자 = 로그인 계정의 본명 (브라우저가 보낸 by 는 무시). 해당 메뉴 권한도 확인"""
        name = self.need_menu(menu)['name']
        return {**self.json_body(), 'by': name}

    def need_menu(self, menu, touch=True):
        """로그인 + 메뉴 권한 (운영자가 accounts/_perms.json 으로 부여)"""
        acc = self.need_user(touch)
        if not perms_for(acc, self.is_super()).get(menu):
            raise ApiError(403, f"'{dict(MENUS)[menu]}' 메뉴 권한이 없습니다 (운영자에게 요청하세요)")
        return acc

    def api(self, m, seg, q):
        def sheet(i):
            if len(seg) <= i or seg[i] not in SHEETS:
                raise ApiError(400, '잘못된 시트')
            return seg[i]

        def rid(i):
            if len(seg) <= i or not ID_RE.match(seg[i]):
                raise ApiError(400, '잘못된 ID')
            return seg[i]

        head = seg[0] if seg else ''
        if m == 'GET' and head == 'info':
            return {'mode': 'server', 'admin': self.is_admin(), 'super': self.is_super(), 'week': iso_week(), 'root': os.path.basename(ROOT), 'auth': True,
                    'perms': perms_for(session_account(self.token(), False), self.is_super()),   # 지금 접속한 계정(없으면 비회원)의 메뉴 권한
                    'host': socket.gethostname(), 'version': html_version(), 'serverVersion': SERVER_VERSION, 'urls': server_urls(), 'plazaPort': PLAZA['port'],
                    **({'net': {'ips': NET_STATE['ips'] or [], 'profiles': NET_STATE['profiles'], 'changedAt': NET_STATE['changedAt'],
                                'allow': [str(n) for n in ALLOW_NETS]}} if self.is_admin() else {})}
        if head == 'auth':
            if m == 'POST' and seg[1:] == ['register']:
                return api_register(self.json_body())
            if m == 'POST' and seg[1:] == ['login']:
                return api_login(self.json_body())
            if m == 'POST' and seg[1:] == ['reset']:
                return api_reset(self.json_body())
            if m == 'POST' and seg[1:] == ['password']:            # 로그인한 상태에서 비밀번호 변경
                return api_change_pw(self.need_user(), self.json_body())
            if m == 'POST' and seg[1:] == ['logout']:
                acc = session_account(self.token())
                session_drop(token=self.token())
                if acc:
                    _presence.pop(acc['id'], None)
                return {'status': 'ok'}
            if m == 'GET' and seg[1:] == ['me']:
                return acc_public(self.need_user())
            if m == 'POST' and seg[1:] == ['ping']:
                return {**api_ping(self.need_user(), self.is_super()), 'super': self.is_super()}
        if head == 'admin' and seg[1:] == ['perms']:             # 메뉴 권한 설정: 운영자(서버 PC)만
            self.need_admin()
            if m == 'GET':
                return api_perms_get()
            if m == 'PUT':
                acc = session_account(self.token(), False)
                return api_perms_put(self.json_body(), acc['name'] if acc else '운영자')
        if head == 'msg':
            acc = self.need_user()
            if m == 'GET' and len(seg) == 1:
                return api_msg_list(acc)
            if m == 'POST' and len(seg) == 1:
                return api_msg_send(acc, self.json_body())
            if m == 'POST' and len(seg) == 3 and seg[2] == 'read':
                return api_msg_read(acc, seg[1])
            if m == 'DELETE' and len(seg) == 3:
                return api_msg_delete(acc, seg[1], seg[2])
        if m == 'GET' and head == 'all':
            return api_all()
        if head == 'timesheet' or head == 'timesheets':          # 월말 시수: 로그인 필요, 실제 시간은 Management 권한자만
            acc = self.need_user()
            can_all = bool(perms_for(acc, self.is_super()).get('mgmt'))
            if m == 'GET' and head == 'timesheets':
                return api_ts_list(q.get('year', ''), can_all)
            if m == 'POST' and head == 'timesheet' and seg[1:] == ['preview']:
                return api_ts_preview(self.raw_body())
            if m == 'PUT' and head == 'timesheet' and len(seg) == 1:
                self.need_menu('weekly')
                return api_ts_put(acc, can_all, q, self.raw_body())
            if m == 'DELETE' and head == 'timesheet' and len(seg) == 3:
                return api_ts_delete(acc, can_all, seg[1], seg[2])
        if head == 'order' and m == 'PUT' and len(seg) == 2:          # 행 순서 바꾸기 (선택한 행 위로/아래로)
            return api_reorder(sheet(1), self.json_body(), self.need_menu('weekly')['name'])
        if head == 'birthdays':                                     # 부서원 생일: 보기 = 누구나(비회원 화면에도 축하 팝업), 고치기·엑셀 = Management 권한
            if m == 'GET' and len(seg) == 1:
                return api_bday_get(session_account(self.token(), False))
            if m == 'POST' and seg[1:] == ['hide']:
                return api_bday_hide(self.need_user(), self.json_body())
            if m == 'PUT' and len(seg) == 1:
                return api_bday_put(self.json_body(), self.need_menu('mgmt')['name'])
            if m == 'POST' and seg[1:] == ['preview']:
                self.need_menu('mgmt')
                return {'list': parse_birthdays(self.raw_body())}
        if head == 'worktime':                                      # 근로시간 관리: Management 권한자만 (보기·올리기·지우기)
            acc = self.need_menu('mgmt')
            if m == 'GET' and len(seg) == 1:
                return api_wt_list()
            if m == 'PUT' and len(seg) == 1:
                return api_wt_put(acc, q, self.raw_body())
            if m == 'DELETE' and len(seg) == 2:
                return api_wt_delete(seg[1], acc['name'])
        if head == 'sheetcols':                                     # 사용자가 추가한 열
            if m == 'POST' and len(seg) == 1:
                return api_sheetcol_add(self.body_by())
            if m == 'DELETE' and len(seg) == 2:
                return api_sheetcol_del(seg[1], q.get('f', ''), self.need_menu('weekly')['name'])
        if m == 'GET' and head == 'profiles':
            return api_profiles(bool(session_account(self.token(), False)))
        if m == 'PUT' and head == 'profile':
            return api_profile_put(self.need_user(), self.json_body())
        if head == 'rec':
            if m == 'GET' and len(seg) == 3:
                r = read_json(P('data', sheet(1), rid(2) + '.json'))
                if not r:
                    raise ApiError(404, '삭제된 행입니다')
                return r
            if m == 'POST' and len(seg) == 2:
                return api_create(sheet(1), self.body_by())
            if m == 'PUT' and len(seg) == 3:
                return api_update(sheet(1), rid(2), self.body_by())
            if m == 'DELETE' and len(seg) == 3:
                return api_delete(sheet(1), rid(2), self.need_menu('weekly')['name'])
        if head == 'trash':
            if m == 'GET' and len(seg) == 1:
                return api_trash()
            if m == 'POST' and len(seg) == 4 and seg[3] == 'restore':
                return api_restore(sheet(1), rid(2), self.need_menu('weekly')['name'])
            if m == 'DELETE' and len(seg) == 3:
                self.need_super()
                return api_purge(sheet(1), rid(2), self.need_menu('weekly')['name'])
        if m == 'GET' and head == 'history' and len(seg) == 3:
            return api_history(sheet(1), rid(2))
        if m == 'GET' and head == 'recent':
            return api_recent()
        if m == 'GET' and head == 'archive' and len(seg) == 2:
            if not WEEK_RE.match(seg[1]):
                raise ApiError(400, '잘못된 주차')
            return api_archive(seg[1])
        if m == 'POST' and head == 'close':
            self.need_super()
            return api_close(self.body_by())
        if m == 'POST' and head == 'columns':
            return api_add_column(self.body_by())
        if m == 'POST' and head == 'saveall':
            return api_saveall(self.body_by())
        if head == 'files':                                       # 첨부파일: 올리기(로그인+주간업무보고 권한) / 내려받기
            if m == 'PUT' and len(seg) == 1:
                by = self.need_menu('weekly')['name']
                return api_file_upload(q.get('name', ''), self.raw_body(), by)
            if m == 'GET' and len(seg) == 2:
                fm = file_meta(seg[1])
                with open(P('files', fm['id'] + fm['ext']), 'rb') as f:
                    data = f.read()
                disp = 'inline' if fm['ext'] == '.pdf' and 'download' not in q else 'attachment'
                self.send(200, data, FILE_TYPES[fm['ext']], {'Content-Disposition': f"{disp}; filename*=UTF-8''{quote(fm['name'])}"})
                return None
        if m == 'PUT' and head == 'saves':
            self.need_menu('weekly')
            return save_xlsx(q.get('tag', ''), self.raw_body())
        if head == 'board':
            if m == 'GET' and len(seg) == 1:
                return api_board_list()
            acc = self.need_menu('board', touch=False)        # 글·댓글 쓰기는 로그인 + 게시판 권한 필요. 실명을 고른 경우에만 계정 본명을 기록
            if m == 'POST' and len(seg) == 1:
                return api_board_create(self.json_body(), acc)
            if m == 'PUT' and len(seg) == 2:
                return api_board_update(seg[1], self.json_body(), acc)
            if m == 'DELETE' and len(seg) == 2:
                return api_board_delete(seg[1], self.json_body(), self.is_super())
            if m == 'POST' and len(seg) == 3 and seg[2] == 'comments':
                return api_comment_add(seg[1], self.json_body(), acc)
            if m == 'DELETE' and len(seg) == 4 and seg[2] == 'comments':
                return api_comment_delete(seg[1], seg[3], self.json_body(), self.is_super())
        raise ApiError(404, '없는 API')


class Server(ThreadingHTTPServer):
    # Windows 에서 SO_REUSEADDR 는 이미 사용 중인 포트에도 bind 를 허용하므로 끄고, 배타적 사용을 요청
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def port_in_use(port):
    """이미 누가 듣고 있으면 무엇인지 반환: 'dashboard' / 'other' / None"""
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            pass
    except OSError:
        return None
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/info', timeout=2) as r:
            if json.loads(r.read()).get('mode') == 'server':
                return 'dashboard'
    except Exception:
        pass
    return 'other'


def port_busy_exit(port, who):
    msg = (f'[포트 사용 중] 대시보드 서버가 이미 포트 {port} 에서 실행 중입니다. 브라우저에서 http://localhost:{port}/ 로 접속하세요.'
           if who == 'dashboard' else
           f'[포트 사용 중] 포트 {port} 을(를) 다른 프로그램이 사용하고 있습니다. 해당 프로그램을 종료하거나 --port 로 다른 포트를 지정하세요.')
    log.error(msg)
    if any(isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers):
        print(msg)                                        # 로그를 파일로 보낼 때도 콘솔에 안내
    sys.exit(2)


def lan_ips():
    ips = set()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    return sorted(ip for ip in ips if not ip.startswith('127.'))


def keep_awake_loop():
    """서버가 켜져 있는 동안 서버 PC 가 절전(대기) 모드로 들어가지 않게 함 — 화면 끄기·화면 잠금은 그대로 됨. Windows 전용.
    (절전되면 부서원은 서버에 못 붙고 '오프라인 모드'가 됨. 노트북 덮개 닫기·전원 단추로 직접 재우는 것은 막지 못함)"""
    if os.name != 'nt':
        return
    import ctypes
    ES_SYSTEM_REQUIRED = 0x00000001                       # 1분마다 '시스템 사용 중' 알림 → 유휴 절전 타이머 초기화
    first = True
    while True:
        try:
            ok = ctypes.windll.kernel32.SetThreadExecutionState(ES_SYSTEM_REQUIRED)
            if first:
                log.info('절전 방지: %s (서버가 켜져 있는 동안 이 PC 는 절전 모드로 들어가지 않음 · 화면 끄기는 됨 · 끄려면 --allow-sleep)', '켜짐' if ok else '실패')
                first = False
        except Exception as e:
            log.warning('절전 방지 실패: %s', e)
            return
        time.sleep(60)


# ---------------------------------------------------------------- 계장 광장 (plaza/plaza_server.py, 포트 8100) — 대시보드 서버가 함께 띄움
# 꺼지면 30초 안에 다시 띄우고, 대시보드 서버가 끝날 때 그 PID 하나만 끔 (python 일괄 종료 안 함).
# 이미 그 포트에서 광장이 돌고 있으면(예: 지난번에 창을 닫아 남은 것) 그대로 씀. 역할·얼굴 = data/plaza/
PLAZA = {'proc': None, 'port': 8100, 'fails': 0}


def plaza_info(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/version', timeout=2) as r:
            d = json.loads(r.read())
            return d if d.get('app') == 'plaza' else None
    except Exception:
        return None


def plaza_alive(port):
    return plaza_info(port) is not None


def plaza_file_ver():
    try:
        with open(P('plaza', 'plaza_server.py'), encoding='utf-8') as f:
            m = re.search(r"^PLAZA_VERSION = '([^']+)'", f.read(), re.M)
        return m[1] if m else ''
    except OSError:
        return ''


def plaza_retire(port):
    """돌고 있는 옛 판 광장 서버를 끔 (업데이트 뒤 새 판으로 바꾸려고). ① /plaza/api/quit ② 그게 없는 옛 판이면
    Windows netstat 으로 그 포트를 듣는 PID 하나를 찾아 python 인지 확인하고 그 PID 만 taskkill (python 일괄 종료 안 함)"""
    import subprocess
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{port}/plaza/api/quit', data=b'{}', headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=3).read()
    except Exception:
        if os.name == 'nt':
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                out = subprocess.run(['netstat', '-ano', '-p', 'TCP'], capture_output=True, text=True, creationflags=flags, timeout=15).stdout
                pids = {ln.split()[-1] for ln in out.splitlines() if 'LISTENING' in ln and re.search(rf':{port}\s', ln)}
                for pid in pids:
                    img = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'], capture_output=True, text=True, creationflags=flags, timeout=15).stdout
                    if 'python' in img.lower():
                        subprocess.run(['taskkill', '/PID', pid, '/F'], capture_output=True, creationflags=flags, timeout=15)
                        log.info('옛 판 계장 광장 서버(PID %s)를 끔', pid)
            except Exception as e:
                log.warning('옛 판 계장 광장 서버를 끄지 못함: %s', e)
    for _ in range(10):
        if not plaza_alive(port):
            return True
        time.sleep(0.5)
    return False


def plaza_loop():
    import subprocess
    port, script = PLAZA['port'], P('plaza', 'plaza_server.py')
    if not os.path.isfile(script):
        log.info('계장 광장: plaza/plaza_server.py 가 없어 띄우지 않음')
        return
    while True:
        p = PLAZA['proc']
        info, want = plaza_info(port), plaza_file_ver()
        if info and want and info.get('ver') != want:            # 돌고 있는 게 옛 판(업데이트 전 · 지난번에 남은 것) → 끄고 새 판으로
            log.info('계장 광장 서버가 옛 판(%s)이라 새 판(%s)으로 바꿉니다', info.get('ver') or '-', want)
            if p is not None and p.poll() is None:
                plaza_stop()
            else:
                plaza_retire(port)
            info = plaza_info(port)
            if info and info.get('ver') != want:
                log.warning('옛 판 계장 광장 서버가 꺼지지 않습니다 — PC 를 다시 켜거나 작업 관리자에서 그 python 을 끄세요')
                time.sleep(600)
                continue
        if (p is None or p.poll() is not None) and not info:
            if p is not None:
                PLAZA['fails'] += 1
                log.warning('계장 광장 서버가 꺼졌습니다 (종료 코드 %s, 이유는 plaza.log) — 다시 띄웁니다', p.returncode)
            if PLAZA['fails'] >= 3:                              # 포트를 다른 프로그램이 쓰는 등 → 10분 쉬고 다시
                log.warning('계장 광장 서버가 계속 꺼집니다 (포트 %d 를 다른 프로그램이 쓰는지 확인) — 10분 뒤 다시 시도', port)
                PLAZA['fails'] = 0
                time.sleep(600)
                continue
            args = [sys.executable, script, '--port', str(port), '--data', P('data', 'plaza'), '--nets-file', nets_file()]
            for n in EXTRA_NETS:
                args += ['--allow', str(n)]
            try:                                                 # 광장 서버가 꺼진 이유는 plaza.log 에 (2MB 넘으면 새로)
                if os.path.getsize(P('plaza.log')) > 2_000_000:
                    os.replace(P('plaza.log'), P('plaza.log.old'))
            except OSError:
                pass
            errf = open(P('plaza.log'), 'ab')
            errf.write(f"\n--- {datetime.datetime.now():%Y-%m-%d %H:%M:%S} 시작 (포트 {port})\n".encode('utf-8'))
            errf.flush()
            env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}       # 한글 Windows(cp949)에서 출력 글자 때문에 꺼지지 않게
            PLAZA['proc'] = subprocess.Popen(args, cwd=P('plaza'), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0), env=env,
                                             stdin=subprocess.DEVNULL, stdout=errf, stderr=errf)
            errf.close()
            log.info('계장 광장 서버 시작: 포트 %d (PID %d) · 기록 plaza.log', port, PLAZA['proc'].pid)
        elif p is not None and p.poll() is None:
            PLAZA['fails'] = 0
        time.sleep(30)


def plaza_stop():
    p = PLAZA['proc']
    if p is not None and p.poll() is None:                     # 내가 띄운 그 프로세스(PID)만
        p.terminate()
        try:
            p.wait(5)
        except Exception:
            p.kill()


def main():
    global ROOT, PORT, ALLOW_NETS
    ap = argparse.ArgumentParser(description='계장ENG그룹 Dashboard 서버')
    ap.add_argument('--root', default=ROOT, help='운영 폴더 (dashboard.html, data/ 가 있는 폴더)')
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--log', help='로그 파일 (지정하지 않으면 콘솔)')
    ap.add_argument('--open', action='store_true', help='서버 시작 후 브라우저로 http://localhost:포트 열기')
    ap.add_argument('--backup-keep', type=int, default=60, help='백업 보관 일수')
    ap.add_argument('--history-days', type=int, default=7, help='수정 이력 보관 일수 (지나면 자동 삭제)')
    ap.add_argument('--allow-sleep', action='store_true', help='서버 PC 절전 방지를 끔 (기본: 서버가 켜져 있는 동안 절전 모드 막음)')
    ap.add_argument('--allow', action='append', default=[], help='추가로 접속을 허용할 사내망 대역 (예: 65.3.0.0/16), 여러 번 지정 가능')
    ap.add_argument('--plaza-port', type=int, default=8100, help='계장 광장 서버 포트 (0 = 띄우지 않음)')
    a = ap.parse_args()
    PLAZA['port'] = a.plaza_port

    ROOT, PORT = os.path.abspath(a.root), a.port
    # 사내망 = 루프백·사설망 + 이 서버 IP 가 속한 /16 대역 + --allow 대역
    EXTRA_NETS[:] = [ipaddress.ip_network(n, strict=False) for n in a.allow]
    handlers = [logging.FileHandler(os.path.join(ROOT, a.log), encoding='utf-8')] if a.log else [logging.StreamHandler(sys.stdout)]
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=handlers)
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    if not os.path.isfile(P('dashboard.html')):
        sys.exit(f'dashboard.html 이 없습니다: {ROOT}')
    for d in ('data', 'history', 'trash', 'archive', 'saves', 'backup', 'board', 'apps', 'accounts', 'messages', 'files', 'profiles', 'timesheets', 'worktime', os.path.join('data', '_meta')):
        os.makedirs(P(d), exist_ok=True)
    refresh_nets(first=True)                              # 허용 대역(지금까지 쓴 유선·Wi-Fi 대역 모두) · 네트워크 종류 확인

    who = port_in_use(a.port)
    if who:
        port_busy_exit(a.port, who)
    try:
        srv = Server((a.host, a.port), Handler)
    except OSError:
        port_busy_exit(a.port, port_in_use(a.port) or 'other')
    threading.Thread(target=backup_loop, args=(a.backup_keep, a.history_days), daemon=True).start()
    threading.Thread(target=weekly_loop, daemon=True).start()
    if not a.allow_sleep:
        threading.Thread(target=keep_awake_loop, daemon=True).start()
    if a.plaza_port:
        import atexit
        atexit.register(plaza_stop)
        threading.Thread(target=plaza_loop, daemon=True).start()
    try:
        build_deploy()
    except Exception as e:
        log.error('배포 파일 생성 실패: %s', e)
    log.info('서버 v%s · 운영 폴더: %s', SERVER_VERSION, ROOT)
    log.info('부서원 배포 파일: %s', P('deploy'))
    log.info('접속 주소(이 PC, 관리자): http://localhost:%d/', a.port)
    for ip in lan_ips():
        log.info('접속 주소(부서원):       http://%s:%d/', ip, a.port)
    log.info('종료: Ctrl+C')
    if a.open:
        threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{a.port}/')).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log.info('서버 종료')


if __name__ == '__main__':
    main()
