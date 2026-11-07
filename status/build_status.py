"""세션 현황판 만들기 — 각 세션의 최신 작업 · 미리보기 · 다음 업데이트에 들어갈 것.

    git fetch origin            (먼저)
    python status/build_status.py

읽는 것: 각 세션 브랜치(git) · status/sessions.json(오케스트레이터가 읽은 세션 상태) · status/previews/*.jpg
쓰는 것: status/SESSION_STATUS.html (파일 하나, 외부 라이브러리 없음)
"""
import base64, datetime, html, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True, check=True).stdout.strip()
HERE = os.path.join(ROOT, 'status')


def git(*a):
    r = subprocess.run(['git', '-C', ROOT, '-c', 'core.quotepath=off', *a], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ''


def show(ref, path):
    return git('show', f'{ref}:{path}')


def log(rng, *paths, n=60):
    out = git('log', f'-{n}', '--format=%h\x1f%cs\x1f%s', rng, '--', *paths) if paths else git('log', f'-{n}', '--format=%h\x1f%cs\x1f%s', rng)
    return [dict(zip(('h', 'd', 's'), l.split('\x1f'))) for l in out.splitlines() if l]


def changed(h, cap=30):
    """커밋이 바꾼 파일 (지도의 '변경 파일' 점) — 큰 반입 커밋은 cap 개까지만."""
    fs = [f for f in git('show', '--name-only', '--format=', h).splitlines() if f and not f.startswith('out/')]
    return fs[:cap]


def first(rx, text, g=1, default=''):
    m = re.search(rx, text or '', re.M)
    return m.group(g) if m else default


def tip(ref):
    h, d = (git('log', '-1', '--format=%h\x1f%ci', ref) or '\x1f').split('\x1f')
    return h, d[:16]


# ---- 세션별로 '최신 버전' · '회사에 나간 것' · '다음 업데이트에 들어갈 것' 을 git 에서 읽는다 -------------------
# 2026-11-07 hotfix133 부터 통합 브랜치 = 이 오케스트레이터 브랜치(HEAD). '대기' = 마지막으로 만든 꾸러미 뒤의 커밋.
INTEG = 'HEAD'


def _pkgs():
    p = os.path.join(HERE, 'packages.json')
    return json.load(open(p, encoding='utf-8')).get('packages', []) if os.path.exists(p) else []


def pkg(file):
    ps = [x for x in _pkgs() if x['file'] == file]
    return ps[-1] if ps else None


def made(file):
    k = pkg(file)
    if not k:
        return ''
    st = f"적용 확인 {k['applied']}" if k.get('applied') else '회사 적용 확인 대기'
    return f"{file} {k['name'].split('_20')[0]} 만듦 ({k['made'][5:]}) · {st}"


def s1():
    b = 'origin/ccr-248a5c4d-3dji7g'
    ver = first(r"const APP_VERSION = '([^']+)'", show(b, 'dashboard/dashboard.html'))
    last = (show(b, 'dashboard_tools/delivered.txt').splitlines() or [''])[-1].split(None, 1)
    base = last[0] if last else ''
    k = pkg('①')
    since = (k or {}).get('tips', {}).get('S1') or base
    pend = log(f'{since}..{b}', 'dashboard') if since else []
    newest = first(r'dashboard v(\d+\.\d+)', '\n'.join(c['s'] for c in log(b, n=15)))       # 브랜치 최신 v (커밋 제목)
    sent = first(r"to_v(\d+\.\d+)", last[1] if len(last) > 1 else "")
    return dict(branch=b, ver=f'v{newest or sent} · 회사엔 v{sent}' if newest and newest != sent else f'v{sent} (화면 {ver})',
                shipped=(made('①') + ' · ' if k else '') + f'delivered.txt 마지막: {last[1] if len(last) > 1 else "?"}', pending=pend, file='① DASHBOARD 개별')


def s2():
    b = 'origin/claude/gracious-ride-26nqrf'
    k = pkg('②')
    nm = first(r'(hotfix\d+)', (k or {}).get('name', '')) or '?'
    return dict(branch=b, ver=f'{nm} 만듦 (통합)' if k else '?', shipped=made('②') or '꾸러미 없음',
                pending=log(f'{INTEG}..{b}'), file='② 통합 (기준 브랜치 · 통합은 오케스트레이터)')


def s3():
    b = 'origin/ccr-cc45909d-fjjmrb'
    ver = first(r'^(L\d+)', (log(b, n=1) or [{'s': ''}])[0]['s'])
    return dict(branch=b, ver=ver, shipped=(made('②') + f' · {ver} 까지 병합') if pkg('②') else '통합 전', pending=log(f'{INTEG}..{b}'), file='② 통합 (병합)')


def s4():
    b = 'origin/ccr-d82d97fa-bb3ty3'
    src = json.loads(show(INTEG, 'config/release_sources.json') or '{}').get('sources', {}).get('PANEL', {})
    imp = src.get('imported', '')
    ver = first(r'변경 이력 \((\d+)\)', '\n'.join(c['s'] for c in log(b, n=10)))
    return dict(branch=b, ver=f'변경 이력 ({ver})' if ver else tip(b)[0], shipped=(made('②') + ' · ' if pkg('②') else '') + f'옮겨 온 마지막 커밋 {imp}',
                pending=log(f'{imp}..{b}', 'dashboard/apps/space') if imp else [], file='② 통합 (apps/space → app/static/space)')


def s5():
    b = 'origin/claude/new-session-v23o67'
    ver = first(r"VERSION\s*=\s*'([^']+)'", show(b, 'dashboard/apps/books/index.html'))
    same = all(git('rev-parse', f'{b}:dashboard/apps/books/{f}') == git('rev-parse', f'{INTEG}:app/static/books/{f}') for f in ('index.html', 'kb.js'))
    src = json.loads(show(INTEG, 'config/release_sources.json') or '{}').get('sources', {}).get('BOOKS', {})
    imp = src.get('imported', '')
    pend = [] if same else (log(f'{imp}..{b}', 'dashboard/apps/books', 'dashboard/books_api.py') if imp else log(b, 'dashboard/apps/books', n=5))
    return dict(branch=b, ver=ver, shipped=(made('②') + ' · ' if pkg('②') else '') + ('통합(/books)에 같은 판' if same else '통합(/books)과 다름'),
                pending=pend, file='② 통합 (apps/books → app/static/books)')


def s6():
    b = 'origin/ccr-efbe7e75-n915ze'
    ver = first(r'^VERSION = "([^"]+)"', show(b, 'app/valve/api.py'))
    return dict(branch=b, ver=ver, shipped=(made('②') + f' · {ver} 병합') if pkg('②') else '확인된 회사 적용: valve29 (2026-11-02)',
                pending=log(f'{INTEG}..{b}'), file='② 통합 (병합 · valveNN 폐지)')


def s7():
    b = 'origin/claude/practical-newton-n6bt58'
    paths = ['app', 'ic-3d-builder', 'ic-expert', 'Agent Org Chart', 'Spec for each Item', 'data', 'output']
    why = ((pkg('②') or {}).get('left_out') or {}).get('S7', '')
    return dict(branch=b, ver=tip(b)[0], shipped=f'이번 꾸러미에서 빠짐 — {why}' if why else '아직 회사 경로 없음 (통합 준비 중)',
                pending=log(b, *paths, n=20), file='② 통합 (예정: app/static/ic3d · /ic3d)')


SESS = [('S1', '1. DASHBOARD', s1), ('S2', '2. P&ID 검토', s2), ('S3', '3. LOGIC 검토', s3), ('S4', '4. PANEL (판넬 공간확보)', s4),
        ('S5', '5. 도서 검토', s5), ('S6', '6. Datasheet 자동 검토 (Valve)', s6), ('S7', '7. 3D 계측제어', s7)]
CAPS = {  # 미리보기 이름 — status/previews/<SID>_<n>.jpg
    'S1_1': '홈 (실제 server.py · 예시 PJT)', 'S1_2': '수행 PJT 보드', 'S2_1': 'P&ID 분석 (대시보드 안 · PID 서버)', 'S2_2': '판독 결과 — 공급 범위 표시',
    'S3_1': 'LOGIC 분석 첫 화면', 'S3_2': '신호 처리 — 계산 과정', 'S3_3': '연결 따라가기', 'S4_1': '첫 화면 Phase 1 · 2 (최신 브랜치)',
    'S4_2': '3D 배치 검토', 'S4_3': '대시보드 ROOM SIZE (지금 회사 경로)', 'S5_1': '도서검토 (대시보드 안)', 'S5_2': '답변 · 근거 도서',
    'S6_1': 'Valve Project Dashboard', 'S6_2': 'Datasheet Review', 'S7_1': '조직도 · 에이전트', 'S7_2': 'PSV MR 초안', 'S7_3': '실물 3D — 오프라인 내장 엔진 (CDN 없음)'}
# 세션별 역할 Agent (ORCHESTRATION_PLAN.md 4장 · 세션 검토로 실제 기능에 맞춤) — (이름, 하는 일, 미리보기 키)
ROLES = {
    'S1': [('UI Agent', 'dashboard.html 한 파일 화면 — 주간업무보고 · 유닛분장 · 세계 지도', 'S1_1'),
           ('데이터 Agent', 'server.py — JSON 행 저장 · 주간 마감 · 백업 · 계정', 'S1_2')],
    'S2': [('추출 엔진 Agent', 'P&ID PDF/DXF 판독 — 판정 근거를 도면 위에 표시', 'S2_2'),
           ('판독 규칙 Agent', '범례 · NOTES · 표제란에서 규칙 · 도면 가르치기', 'S2_2'),
           ('Excel 출력 Agent', '고객 서식 계기 · 밸브 리스트 · 변경 내역 Excel', 'S2_1')],
    'S3': [('로직 파싱 Agent', 'Logic Diagram PDF → 블록 · 단자 · 선 · From-To 보고', 'S3_1'),
           ('추적 · 정합성 Agent', '연결 따라가기 — 최종 명령에서 최초 입력까지', 'S3_3'),
           ('시뮬레이션 Agent', '동작 시뮬레이션 · 신호 처리 계산 과정', 'S3_2')],
    'S4': [('배치 Agent', 'Panel Type · Equipment List 자동 배치 · 간섭 · 이격', 'S4_1'),
           ('3D · 출력 Agent', 'WebGL 3D 검토 · PDF · DXF · CSV · 건축 전달 요약', 'S4_2'),
           ('대시보드 연결 Agent', '회사 DASHBOARD 메뉴 ROOM SIZE 계산 경로', 'S4_3')],
    'S5': [('문서 파싱 Agent', 'PDF · DOCX · XLSX · PPTX 본문 색인 · 공용 도서관', 'S5_1'),
           ('답변 Agent', '폴더 원문 인용과 학습 지식을 나눠 답변', 'S5_2')],
    'S6': [('추출 Agent', 'Ball Valve Datasheet PDF 텍스트 → 항목', 'S6_2'),
           ('교차 검증 Agent', 'Valve List · Process Data · PMS 대조 · Typical 묶기', 'S6_1')],
    'S7': [('3D 뷰 Agent', 'Anatomy 개념 · 실물 3D — 내장 엔진으로 오프라인 (three.js · CDN 없음)', 'S7_3'),
           ('MR · 지식 Agent', 'Item Spec · 전문가 지식베이스 · MR 초안', 'S7_2')],
}
AGENT_PV = {'ic-mr-writer': 'S7_2', 'ic-anatomy-viewer': 'S7_3', 'ic-anatomy-link': 'S7_3', 'ic-ga-to-3d': 'S7_3'}
COMMON = ['설계', '구현', '검증', '문서']

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
        for c in g['pending']:
            c['files'] = changed(c['h'])
        h, d = tip(g['branch'])
        s = st['sessions'].get(sid, {})
        pv = sorted(f for f in os.listdir(pv_dir) if f.startswith(sid + '_'))
        data.append(dict(sid=sid, name=name, **g, tip=h, tipdate=d, recent=log(g['branch'], n=6),
                         agents=[dict(a, pv=AGENT_PV.get(a['name'], f'{sid}_1')) for a in agents(g['branch'])],
                         roles=[dict(name=r[0], duty=r[1], pv=r[2]) for r in ROLES.get(sid, [])], common=COMMON,
                         state=s, previews=[dict(key=f[:-4], cap=CAPS.get(f[:-4], f),
                                                 date=datetime.date.fromtimestamp(os.path.getmtime(os.path.join(pv_dir, f))).isoformat()) for f in pv]))
    tpl = open(os.path.join(HERE, 'template.html'), encoding='utf-8').read()
    built = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    import track                                   # 변경 추적 · 결정적 점검 (status/track.py)
    hist = track.update(ROOT, HERE, data, built, st.get('read_at', ''))
    names = {x['sid']: x['name'] for x in data}
    for x in data:                                 # 쉬운 말 커밋 제목 (최근 활동 · 목록용)
        for c in x['recent'] + x['pending']:
            c['p'] = track.short(c['s'], 40)
    for c in hist['changes']:
        c['plain'] = track.plain(c)
    hist['summary'] = track.summarize(hist['changes'])
    chks = track.checks(ROOT, HERE, data)
    for c in chks:
        c['plain'] = track.plain_check(c, names)
    meta = dict(built=built, read_at=st.get('read_at', ''), bucket=BUCKET, history=hist, checks=chks)
    # 프론트엔드(template.html)는 그대로, 데이터만 window.DATA · window.META 로 끼운다
    out = tpl.replace('/*DATA*/', 'window.DATA=' + json.dumps(data, ensure_ascii=False) + ';window.META=' + json.dumps(meta, ensure_ascii=False) + ';')
    # 그림은 맨 끝에 — 앱 파일 미리보기가 큰 파일 끝을 잘라도 지도는 먼저 그려진다
    pv = {}                                       # previews/*.jpg (세션 미리보기) + previews/demo/*.jpg (회사 PC 시연)
    for d, _, fs in os.walk(pv_dir):
        for f in sorted(fs):
            if f.endswith('.jpg'):
                pv[f[:-4]] = img64(os.path.join(d, f))
    out = out.replace('</body>', '<script>window.PV=' + json.dumps(pv) + ';window.dispatchEvent(new Event("pv-ready"));</script>\n</body>')
    path = os.path.join(HERE, 'SESSION_STATUS.html')
    open(path, 'w', encoding='utf-8').write(out)
    print(path, f'{len(out) / 1048576:.1f} MB')
    for x in data:
        print(f"  {x['sid']} {x['ver']:<40} 다음 업데이트 {len(x['pending'])}건")
    new = [c for c in hist['changes'] if c['at'] == hist['latest']]
    print(f"  스냅숏 {len(hist['snapshots'])}개 · 이번 변경 {len(new)}건 · 점검 {len(meta['checks'])}건")


if __name__ == '__main__':
    sys.exit(main())
