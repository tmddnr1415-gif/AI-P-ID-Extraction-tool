"""세션 현황판 만들기 — 각 세션의 최신 작업 · 미리보기 · 다음 업데이트에 들어갈 것.

    git fetch origin            (먼저)
    python status/build_status.py

읽는 것: 각 세션 브랜치(git) · status/sessions.json(오케스트레이터가 읽은 세션 상태) · status/previews/*.jpg
쓰는 것: status/SESSION_STATUS.html (파일 하나, 외부 라이브러리 없음)
"""
import base64, datetime, html, json, os, re, subprocess, sys

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
HERE = os.path.join(ROOT, 'status')
PID = 'origin/claude/gracious-ride-26nqrf'          # 통합 파일을 만드는 기준 브랜치


def git(*a):
    r = subprocess.run(['git', '-C', ROOT, '-c', 'core.quotepath=off', *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def show(ref, path):
    return git('show', f'{ref}:{path}')


def log(rng, *paths, n=60):
    out = git('log', f'-{n}', '--format=%h\x1f%cs\x1f%s', rng, '--', *paths) if paths else git('log', f'-{n}', '--format=%h\x1f%cs\x1f%s', rng)
    return [dict(zip(('h', 'd', 's'), l.split('\x1f'))) for l in out.splitlines() if l]


def first(rx, text, g=1, default=''):
    m = re.search(rx, text or '', re.M)
    return m.group(g) if m else default


def tip(ref):
    h, d = (git('log', '-1', '--format=%h\x1f%ci', ref) or '\x1f').split('\x1f')
    return h, d[:16]


# ---- 세션별로 '최신 버전' · '회사에 나간 것' · '다음 업데이트에 들어갈 것' 을 git 에서 읽는다 -------------------
def s1():
    b = 'origin/ccr-248a5c4d-3dji7g'
    ver = first(r"const APP_VERSION = '([^']+)'", show(b, 'dashboard/dashboard.html'))
    last = (show(b, 'dashboard_tools/delivered.txt').splitlines() or [''])[-1].split(None, 1)
    base = last[0] if last else ''
    pend = [c for c in log(f'{base}..{b}', 'dashboard') if base] if base else []
    return dict(branch=b, ver=f'v{first(r"to_v(\d+\.\d+)", last[1] if len(last) > 1 else "")} · 화면 {ver}',
                shipped=f'delivered.txt 마지막: {last[1] if len(last) > 1 else "?"}', pending=pend, file='① DASHBOARD 개별')


def s2():
    b = PID
    zips = sorted(set(re.findall(r'out/PID_dev\+ops_hotfix(\d+)_[\d-]+\.zip', git('ls-tree', '-r', '--name-only', b, 'out/'))), key=int)
    last = zips[-1] if zips else '?'
    added = git('log', '-1', '--format=%h', '--diff-filter=A', b, '--', f'out/PID_dev+ops_hotfix{last}_*.zip')
    nxt = first(r'다음 꾸러미 번호: (hotfix\d+)', show(b, 'docs/handoff/pid.md'), default=f'hotfix{int(last) + 1}' if last != '?' else '?')
    return dict(branch=b, ver=f'hotfix{last} 꾸러미 · 다음 {nxt}', shipped=f'마지막 꾸러미 hotfix{last} (회사 적용 확인 기록 없음)',
                pending=log(f'{added}..{b}') if added else [], file='② 통합')


def s3():
    b = 'origin/ccr-cc45909d-fjjmrb'
    pend = log(f'{PID}..{b}')
    ver = first(r'^(L\d+)', (log(b, n=1) or [{'s': ''}])[0]['s'])
    return dict(branch=b, ver=ver, shipped='통합 브랜치에 병합된 데까지', pending=pend, file='② 통합 (병합)')


def s4():
    b = 'origin/ccr-d82d97fa-bb3ty3'
    src = json.loads(show(PID, 'config/release_sources.json') or '{}').get('sources', {}).get('PANEL', {})
    imp = src.get('imported', '')
    ver = first(r'변경 이력 \((\d+)\)', '\n'.join(c['s'] for c in log(b, n=10)))
    return dict(branch=b, ver=f'변경 이력 ({ver})' if ver else tip(b)[0], shipped=f'통합에 옮겨 온 마지막 커밋 {imp}',
                pending=log(f'{imp}..{b}', 'dashboard/apps/space') if imp else [], file='② 통합 (apps/space → app/static/space)')


def s5():
    b = 'origin/claude/new-session-v23o67'
    ver = first(r"VERSION\s*=\s*'([^']+)'", show(b, 'dashboard/apps/books/index.html'))
    same = all(git('rev-parse', f'{b}:dashboard/apps/books/{f}') == git('rev-parse', f'{PID}:app/static/books/{f}') for f in ('index.html', 'kb.js'))
    since = git('log', '-1', '--format=%cs', PID, '--', 'app/static/books')   # 통합에 도서가 마지막으로 들어간 날
    pend = [] if same else [c for c in log(b, 'dashboard/apps/books', 'dashboard/books_api.py', n=20) if c['d'] >= since]
    return dict(branch=b, ver=ver, shipped='통합(PID 서버 /books)에 같은 판' if same else '통합(PID 서버 /books)과 다름',
                pending=pend, file='② 통합 (apps/books → app/static/books)')


def s6():
    b = 'origin/ccr-efbe7e75-n915ze'
    ver = first(r'^VERSION = "([^"]+)"', show(b, 'app/valve/api.py'))
    return dict(branch=b, ver=ver, shipped='확인된 회사 적용: valve29 (2026-11-02)', pending=log(f'{PID}..{b}'), file='② 통합 (병합 · valveNN 폐지)')


def s7():
    b = 'origin/claude/practical-newton-n6bt58'
    paths = ['app', 'ic-3d-builder', 'ic-expert', 'Agent Org Chart', 'Spec for each Item', 'data', 'output']
    return dict(branch=b, ver=tip(b)[0], shipped='아직 회사 경로 없음 (통합 준비 중)', pending=log(b, *paths, n=20), file='② 통합 (예정: app/static/ic3d · /ic3d)')


SESS = [('S1', '1. DASHBOARD', s1), ('S2', '2. P&ID 검토', s2), ('S3', '3. LOGIC 검토', s3), ('S4', '4. PANEL (판넬 공간확보)', s4),
        ('S5', '5. 도서 검토', s5), ('S6', '6. Datasheet 자동 검토 (Valve)', s6), ('S7', '7. 3D 계측제어', s7)]
CAPS = {  # 미리보기 이름 — status/previews/<SID>_<n>.jpg
    'S1_1': '홈 (실제 server.py · 예시 PJT)', 'S1_2': '수행 PJT 보드', 'S2_1': 'P&ID 분석 (대시보드 안 · PID 서버)', 'S2_2': '판독 결과 — 공급 범위 표시',
    'S3_1': 'LOGIC 분석 첫 화면', 'S3_2': '신호 처리 — 계산 과정', 'S3_3': '연결 따라가기', 'S4_1': '첫 화면 Phase 1 · 2 (최신 브랜치)',
    'S4_2': '3D 배치 검토', 'S4_3': '대시보드 ROOM SIZE (지금 회사 경로)', 'S5_1': '도서검토 (대시보드 안)', 'S5_2': '답변 · 근거 도서',
    'S6_1': 'Valve Project Dashboard', 'S6_2': 'Datasheet Review', 'S7_1': '조직도 · 에이전트', 'S7_2': 'PSV MR 초안', 'S7_3': '실물 3D — CDN 막히면 (고칠 것)'}
BUCKET = {'WORKING': ('info', '작업 중'), 'BLOCKED': ('warn', '사용자 확인 필요'), 'REVIEW_READY': ('ok', '검토 준비'),
          'COMPLETED': ('ok', '완료 · 대기'), 'FAILED': ('bad', '실패')}


def agents(ref):
    """브랜치에 정의된 실제 Agent · Skill (.claude/agents/*.md · .claude/skills/*/SKILL.md) — 이름 · 설명."""
    out = []
    for p in git('ls-tree', '-r', '--name-only', ref).splitlines():
        m = re.search(r'(?:^|/)\.claude/(agents)/([^/]+)\.md$', p) or re.search(r'(?:^|/)\.claude/(skills)/([^/]+)/SKILL\.md$', p)
        if not m:
            continue
        txt = show(ref, p)
        fm = re.search(r'^---\n(.*?)\n---', txt, re.S)
        fm = fm.group(1) if fm else ''
        desc = first(r'^description:\s*"?(.+?)"?\s*$', fm) or first(r'^#\s*(.+)$', txt)
        out.append(dict(kind='agent' if m.group(1) == 'agents' else 'skill', name=first(r'^name:\s*(.+)$', fm) or m.group(2),
                        desc=desc[:400], path=p))
    return out


def img64(p):
    with open(p, 'rb') as f:
        return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode()


def main():
    st = json.load(open(os.path.join(HERE, 'sessions.json'), encoding='utf-8'))
    pv_dir = os.path.join(HERE, 'previews')
    data = []
    for sid, name, fn in SESS:
        g = fn()
        h, d = tip(g['branch'])
        s = st['sessions'].get(sid, {})
        pv = sorted(f for f in os.listdir(pv_dir) if f.startswith(sid + '_'))
        data.append(dict(sid=sid, name=name, **g, tip=h, tipdate=d, recent=log(g['branch'], n=6), agents=agents(g['branch']),
                         state=s, previews=[dict(src=img64(os.path.join(pv_dir, f)), cap=CAPS.get(f[:-4], f),
                                                 date=datetime.date.fromtimestamp(os.path.getmtime(os.path.join(pv_dir, f))).isoformat()) for f in pv]))
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    meta = dict(built=datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), read_at=st.get('read_at', ''), bucket=BUCKET)
    out = tpl.replace('/*DATA*/', 'const DATA=' + json.dumps(data, ensure_ascii=False) + ';const META=' + json.dumps(meta, ensure_ascii=False) + ';')
    path = os.path.join(HERE, 'SESSION_STATUS.html')
    open(path, 'w', encoding='utf-8').write(out)
    print(path, f'{len(out) / 1048576:.1f} MB')
    for x in data:
        print(f"  {x['sid']} {x['ver']:<40} 다음 업데이트 {len(x['pending'])}건")


if __name__ == '__main__':
    sys.exit(main())
