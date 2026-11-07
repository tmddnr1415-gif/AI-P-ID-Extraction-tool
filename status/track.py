"""변경 추적 · 결정적 점검 — build_status.py 가 부른다.

신호 우선순위 (obsidian-daily-review 의 signal hierarchy 를 세션 지도에 맞춤):
  1. git     — 가장 강한 근거. 브랜치 끝이 바뀌면 그 사이 커밋을 그대로 적는다.
  2. 세션 기록 — 세션이 스스로 남긴 보고 · 상태 · 확인 필요 (list_sessions).
  3. 계산    — 위 둘에서 계산한 값 (대기 건수 변화).
추측은 적지 않는다. 확인되는 것만 남긴다.

저장: status/history.json = {"snapshots": [...], "changes": [...]}
  snapshot = {at, read_at, s: {SID: {branch, tip, ver, bucket, needs, recent, pending:[h]}}}
  change   = {at, prev, sid, kind, sig, text, h?, d?}
처음에는 저장소에 커밋된 SESSION_STATUS.html 판들에서 과거 상태를 되살린다 (백필).
"""
import json, os, re, subprocess

SIG = ('git', '세션 기록', '계산')


def _git(root, *a):
    r = subprocess.run(['git', '-C', root, '-c', 'core.quotepath=off', *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def snap_of(data, at, read_at):
    return dict(at=at, read_at=read_at, s={x['sid']: dict(branch=x['branch'], tip=x['tip'], ver=x['ver'],
                                                         bucket=(x.get('state') or {}).get('bucket', ''),
                                                         needs=(x.get('state') or {}).get('needs', ''),
                                                         recent=(x.get('state') or {}).get('recent', ''),
                                                         pending=[c['h'] for c in x.get('pending', [])]) for x in data})


def _parse_board(html):
    m = re.search(r'(?:window\.DATA|const DATA)=(\[.*?\]);(?:window\.META|const META)=(\{.*?\});', html, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1)), json.loads(m.group(2))
    except ValueError:
        return None


def backfill(root, rel='status/SESSION_STATUS.html'):
    """커밋된 현황판 판들에서 과거 스냅숏을 되살린다 (오래된 것 → 새것)."""
    out = []
    for h in reversed(_git(root, 'log', '--format=%h', '--', rel).splitlines()):
        p = _parse_board(_git(root, 'show', f'{h}:{rel}'))
        if not p:
            continue
        data, meta = p
        out.append(snap_of(data, meta.get('built', h), meta.get('read_at', '')))
    # 같은 상태가 이어진 판은 하나로
    uniq = []
    for s in out:
        if not uniq or _key(uniq[-1]) != _key(s):
            uniq.append(s)
    return uniq


def _key(s):
    return json.dumps({k: (v['tip'], v['ver'], v['bucket'], v['needs'], v['recent']) for k, v in s['s'].items()}, sort_keys=True, ensure_ascii=False)


def diff(root, a, b):
    """스냅숏 a → b 사이의 변경 (확인되는 것만)."""
    ch = []
    for sid, cur in b['s'].items():
        old = a['s'].get(sid)
        base = dict(at=b['at'], prev=a['at'], sid=sid)
        if not old:
            ch.append({**base, 'kind': 'new', 'sig': 'git', 'text': '세션 지도에 새로 들어옴'})
            continue
        if old['branch'] != cur['branch']:
            ch.append({**base, 'kind': 'branch', 'sig': 'git', 'text': f"작업 브랜치 바뀜 {old['branch'].replace('origin/', '')} → {cur['branch'].replace('origin/', '')}"})
        if old['tip'] != cur['tip']:
            rng = f"{old['tip']}..{cur['tip']}"
            lines = _git(root, 'log', '-30', '--format=%h\x1f%cs\x1f%s', rng).splitlines()
            if not lines:          # 브랜치가 갈렸거나 되감김
                ch.append({**base, 'kind': 'commit', 'sig': 'git', 'text': f"브랜치 끝 {old['tip']} → {cur['tip']} (이어지지 않음 — 되감김 또는 새 브랜치)"})
            for l in lines:
                h, d, s = l.split('\x1f')
                ch.append({**base, 'kind': 'commit', 'sig': 'git', 'h': h, 'd': d, 'text': s})
        if old['ver'] != cur['ver']:
            ch.append({**base, 'kind': 'version', 'sig': 'git', 'text': f"버전 {old['ver']} → {cur['ver']}"})
        if old['bucket'] != cur['bucket']:
            ch.append({**base, 'kind': 'state', 'sig': '세션 기록', 'text': f"상태 {old['bucket'] or '?'} → {cur['bucket'] or '?'}"})
        if old['needs'] != cur['needs']:
            if old['needs'] and not cur['needs']:
                ch.append({**base, 'kind': 'needs', 'sig': '세션 기록', 'text': f"확인 필요 풀림 — {old['needs']}"})
            elif cur['needs']:
                ch.append({**base, 'kind': 'needs', 'sig': '세션 기록', 'text': f"확인 필요 — {cur['needs']}"})
        if old['recent'] != cur['recent'] and cur['recent']:
            ch.append({**base, 'kind': 'report', 'sig': '세션 기록', 'text': f"세션 보고 — {cur['recent']}"})
        po, pn = len(old['pending']), len(cur['pending'])
        if po != pn:
            ch.append({**base, 'kind': 'pending', 'sig': '계산', 'text': f"다음 업데이트 대기 {po} → {pn}건"})
    return ch


def update(root, here, data, at, read_at):
    """history.json 을 읽고, 지금 상태가 마지막 스냅숏과 다르면 스냅숏 · 변경을 덧붙인다."""
    path = os.path.join(here, 'history.json')
    if os.path.exists(path):
        hist = json.load(open(path, encoding='utf-8'))
    else:
        snaps = backfill(root)
        hist = dict(snapshots=snaps, changes=[])
        for a, b in zip(snaps, snaps[1:]):
            hist['changes'].extend(diff(root, a, b))
    cur = snap_of(data, at, read_at)
    if not hist['snapshots'] or _key(hist['snapshots'][-1]) != _key(cur):
        if hist['snapshots']:
            hist['changes'].extend(diff(root, hist['snapshots'][-1], cur))
        hist['snapshots'].append(cur)
    json.dump(hist, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    last = hist['snapshots'][-1]['at']
    return dict(snapshots=[dict(at=s['at'], read_at=s['read_at']) for s in hist['snapshots']],
                changes=sorted(hist['changes'], key=lambda c: (c['at'], c.get('d', '')), reverse=True)[:400],
                latest=last)


def checks(root, here, data, rule_at='2026-11-07T07:10:00Z'):
    """결정적 점검 — git · 파일로 확인되는 것만."""
    out = []
    man_p = os.path.join(here, 'previews', 'captured.json')
    man = json.load(open(man_p, encoding='utf-8')) if os.path.exists(man_p) else {'captures': {}, 'branches': {}}
    tips = {x['sid']: x for x in data}
    for key, c in man.get('captures', {}).items():
        if not c.get('commit'):
            continue
        br = 'origin/' + man['branches'].get(c['sid'], '')
        n = len(_git(root, 'log', '--format=%h', f"{c['commit']}..{br}").splitlines())
        if n:
            owner = key.split('_')[0]
            out.append(dict(sid=owner, kind='preview', text=f"미리보기 {key} 는 {c['commit']} 에서 찍음 — 그 뒤 커밋 {n}개 ({c['how']})", key=key))
    for x in data:
        zips = [l for l in _git(root, 'log', f'--since={rule_at}', '--diff-filter=A', '--name-only', '--format=', x['branch'], '--', '*.zip').splitlines() if l]
        if zips:
            out.append(dict(sid=x['sid'], kind='zip', text=f"규약 v2(업데이트 파일은 오케스트레이터) 뒤에 zip {len(zips)}개 커밋 — {', '.join(os.path.basename(z) for z in zips[:3])}"))
        st = x.get('state') or {}
        if st.get('needs') and st.get('updated', '') < rule_at.replace('07:10', '08:00'):
            out.append(dict(sid=x['sid'], kind='waiting', text=f"확인 필요가 {st.get('updated', '')[:16].replace('T', ' ')} 부터 그대로"))
    return out


# ---- 쉬운 말 (비전공자용 · 간결) -------------------------------------------------------------
STATE_KO = {'BLOCKED': '확인 기다림', 'COMPLETED': '완료', 'WORKING': '작업 중', 'REVIEW_READY': '검토 준비', 'FAILED': '실패', '': '?'}
_PREFIX = re.compile(r'^(?:(?:dashboard|valve|hotfix)\s*v?[\d.]+(?:\([A-Z]\))?|L\d+|v[\d.]+|hotfix\d+(?:\([A-Z]\))?|valve\d+|'
                     r'feat|fix|docs|chore|build|tools|import|refactor|test|orch)(?:\([^)]*\))?\s*[:：]\s*', re.I)


def short(s, n=42):
    s = (s or '').strip()
    if s.startswith('Merge '):
        return '다른 작업 줄기 합침'
    s = _PREFIX.sub('', s)
    s = _PREFIX.sub('', s)                         # 'hotfix132(D): LOGIC — …' 처럼 두 겹
    for cut in (' — ', ' · ', ' (', ': ', ' - '):
        if len(s) > n and cut in s[8:]:
            s = s[:8 + s[8:].index(cut)]
    return s if len(s) <= n else s[:n - 1].rstrip() + '…'


def _ver(v):
    v = re.split(r' · | \(', v or '')[0].strip()
    return '새 판' if re.fullmatch(r'[0-9a-f]{7,40}', v) else v


def plain(c):
    k, t = c['kind'], c['text']
    if k == 'commit':
        return short(t) if c.get('h') else '코드가 크게 바뀜 (이어지지 않는 변경)'
    if k == 'version':
        a, b = t.replace('버전 ', '', 1).split(' → ', 1)
        return f'버전 {_ver(a)} → {_ver(b)}' if _ver(b) != '새 판' else '코드 새 판'
    if k == 'state':
        a, b = t.replace('상태 ', '', 1).split(' → ', 1)
        return f'상태: {STATE_KO.get(a, a)} → {STATE_KO.get(b, b)}'
    if k == 'needs':
        return '사용자 확인 끝남' if '풀림' in t else '⚠ 사용자 확인 필요 — ' + short(t.split(' — ', 1)[-1], 46)
    if k == 'report':
        return '세션 보고: ' + short(t.split(' — ', 1)[-1], 46)
    if k == 'pending':
        a, b = [int(x) for x in re.findall(r'\d+', t)[:2]]
        return '회사 업데이트 파일에 모두 담김' if b == 0 and a > 0 else f'회사에 보낼 변경 {a} → {b}건'
    if k == 'branch':
        return '작업 줄기(브랜치)가 바뀜'
    if k == 'new':
        return '세션 지도에 새로 들어옴'
    return short(t)


def summarize(changes):
    """(갱신 시점, 세션) 마다 한 줄 요약 + 쉬운 말 목록 (기술 기록은 따로)."""
    groups = {}
    for c in changes:
        groups.setdefault((c['at'], c['sid']), []).append(c)
    out = []
    for (at, sid), cs in groups.items():
        n = sum(1 for c in cs if c['kind'] == 'commit')
        bits = [f'변경 {n}건'] if n else []
        v = [plain(c) for c in cs if c['kind'] == 'version']
        if v and v[0] != '코드 새 판':
            bits.append(v[0].replace('버전 ', ''))
        if any(c['kind'] == 'needs' and '풀림' in c['text'] for c in cs):
            bits.append('확인 끝남')
        if any(c['kind'] == 'needs' and '풀림' not in c['text'] for c in cs):
            bits.append('⚠ 확인 필요')
        p = [c for c in cs if c['kind'] == 'pending']
        if p:
            b = int(re.findall(r'\d+', p[-1]['text'])[1])
            bits.append('회사 업데이트 파일에 담김' if b == 0 else f'회사에 보낼 것 {b}건')
        items = [plain(c) for c in cs if c['kind'] == 'commit'][:5]
        more = n - len(items)
        items += [plain(c) for c in cs if c['kind'] == 'needs' and '풀림' not in c['text']]   # 한 줄에 없는 것만 (새 확인 요청)
        if not bits:                                   # 보고 · 상태만 바뀐 경우
            rep = [plain(c) for c in cs if c['kind'] in ('report', 'state')]
            bits, items = (['세션 알림만'], rep[:2]) if rep else (['상태만 바뀜'], items)
        out.append(dict(at=at, prev=cs[0].get('prev', ''), sid=sid, line=' · '.join(bits), items=items, more=max(0, more)))
    return sorted(out, key=lambda x: (x['at'], x['sid']), reverse=True)


def plain_check(c, names):
    nm = names.get(c['sid'], c['sid'])
    if c['kind'] == 'preview':
        n = re.search(r'커밋 (\d+)개', c['text'])
        return f"{nm}: 미리보기 화면이 최신 코드보다 오래됨 (그 뒤 변경 {n.group(1) if n else '?'}건) — 다시 찍을 것"
    if c['kind'] == 'zip':
        return f"{nm}: 규칙이 바뀐 뒤에도 세션이 업데이트 zip 을 따로 올림 — 회사로는 오케스트레이터 파일만"
    if c['kind'] == 'waiting':
        t = re.search(r'(\d{2}:\d{2})', c['text'])
        return f"{nm}: {t.group(1) if t else '오래'}부터 사용자 답을 기다리는 중"
    return f'{nm}: ' + c['text']
