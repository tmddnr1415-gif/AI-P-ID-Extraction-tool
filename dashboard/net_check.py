"""계장ENG그룹 Dashboard — 부서원 접속 점검 / 방화벽 허용 (서버 PC 에서 실행, Windows)

  python net_check.py            점검만 (관리자 권한 필요 없음) → 화면 + network_check.txt
  python net_check.py --fix      관리자 권한: TCP 포트 인바운드 허용 규칙 추가(모든 네트워크 종류) + python 인바운드 '차단' 규칙 끄기

PowerShell 은 회사 정책으로 막힐 수 있어 쓰지 않음 — Python 표준 라이브러리 + Windows 기본 명령(netsh, ipconfig)만.
check_network.bat / allow_firewall.bat 가 이 파일을 부름.
"""
import argparse, ctypes, datetime, json, os, re, socket, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LINES = []


def say(s=''):
    LINES.append(s)
    try:
        print(s)
    except UnicodeEncodeError:
        print(s.encode('ascii', 'replace').decode())


def run(cmd, timeout=40):
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except Exception as e:
        return f'(실행 실패: {e})', 1
    b = out.stdout + out.stderr
    for enc in ('utf-8', 'cp949'):
        try:
            return b.decode(enc), out.returncode
        except UnicodeDecodeError:
            pass
    return b.decode('utf-8', 'replace'), out.returncode


def is_admin():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


# ---------------------------------------------------------------- 방화벽 규칙 (netsh 출력: 영문·한글 Windows 모두)
KEYS = {'name': ('Rule Name', '규칙 이름'), 'enabled': ('Enabled', '사용'), 'dir': ('Direction', '방향'), 'profiles': ('Profiles', '프로필'),
        'protocol': ('Protocol', '프로토콜'), 'localport': ('LocalPort', '로컬 포트'), 'program': ('Program', '프로그램'), 'action': ('Action', '작업', '동작')}
YES, BLOCK, ALLOW = ('Yes', '예'), ('Block', '차단'), ('Allow', '허용')
PROF_EN = {'공용': 'public', '개인': 'private', '도메인': 'domain', 'public': 'public', 'private': 'private', 'domain': 'domain'}


def rules_inbound():
    txt, _ = run(['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all', 'dir=in', 'verbose'], timeout=90)
    rules, cur = [], None
    for line in txt.splitlines():
        m = re.match(r'^([^:]+?):\s+(.*)$', line.strip())
        if not m:
            continue
        k, v = m[1].strip(), m[2].strip()
        key = next((kk for kk, names in KEYS.items() if k in names), None)
        if key == 'name':
            cur = {'name': v}
            rules.append(cur)
        elif key and cur is not None:
            cur[key] = v
    return rules


def profiles_en(v):
    out = []
    for p in re.split(r'[,\s]+', v or ''):
        p = PROF_EN.get(p.strip().lower()) or PROF_EN.get(p.strip())
        if p and p not in out:
            out.append(p)
    return ','.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--fix', action='store_true')
    a = ap.parse_args()
    port = a.port
    say(f'=== 계장ENG그룹 Dashboard 접속 점검  {datetime.datetime.now():%Y-%m-%d %H:%M}  PC={socket.gethostname()}  포트={port}  관리자권한={"예" if is_admin() else "아니요"} ===')
    if os.name != 'nt':
        say('Windows 에서 실행하세요.')
        return

    # 1. IP 주소
    say('\n[1] 이 PC 의 IP 주소 (부서원은 http://IP:%d/ 로 접속)' % port)
    txt, _ = run(['ipconfig'])
    adapter, ips = '', []
    for line in txt.splitlines():
        if line and not line.startswith(' ') and line.rstrip().endswith(':'):
            adapter = line.strip().rstrip(':')
        m = re.search(r'IPv4[^:]*:\s*([\d.]+)', line)
        if m:
            ips.append(m[1])
            say(f'    {adapter}  →  {m[1]}')
    if not ips:
        say('    (IPv4 주소 없음 — 네트워크 연결 확인)')

    # 2. Wi-Fi
    txt, _ = run(['netsh', 'wlan', 'show', 'interfaces'])
    ssid = next((m[1].strip() for m in (re.match(r'\s*SSID\s*:\s*(.+)$', l) for l in txt.splitlines()) if m), '')
    say(f'\n[2] Wi-Fi: {ssid or "(연결 안 됨 또는 유선만)"}')

    # 3. 방화벽 지금 프로필
    say('\n[3] Windows 방화벽 — 지금 적용 중인 프로필')
    txt, _ = run(['netsh', 'advfirewall', 'show', 'currentprofile'])
    cats = []
    for line in txt.splitlines():
        t = line.strip()
        if t.endswith(':') and re.search(r'Profile|프로필', t):
            c = 'public' if re.search(r'Public|공용', t) else 'private' if re.search(r'Private|개인', t) else 'domain' if re.search(r'Domain|도메인', t) else ''
            if c:
                cats.append(c)
                say(f'    {t.rstrip(":")}  ({c})')
        elif re.match(r'(State|상태)\b', t) or re.search(r'(Firewall Policy|방화벽 정책)', t):
            say(f'      {t}')
    if not cats:
        say('    (확인 못 함)\n' + '\n'.join('      ' + l for l in txt.strip().splitlines()[:8]))

    # 4. 서버 응답
    say('\n[4] 대시보드 서버 응답')
    up = False
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))   # 회사 프록시를 거치지 않고 바로
    for host in ['localhost'] + ips:
        try:
            with opener.open(f'http://{host}:{port}/api/info', timeout=5) as r:
                d = json.loads(r.read().decode('utf-8'))
            say(f'    OK  http://{host}:{port}/  (화면 v{d.get("version")}, 서버 v{d.get("serverVersion")})')
            up = True
        except Exception as e:
            say(f'    --  http://{host}:{port}/  응답 없음 ({type(e).__name__})')
    txt, _ = run(['netstat', '-ano', '-p', 'TCP'])
    lis = [l.split() for l in txt.splitlines() if re.search(rf':{port}\s', l) and re.search(r'LISTEN', l)]
    say('    대기(LISTEN): ' + (', '.join(x[1] for x in lis) if lis else '없음 — 서버가 안 켜져 있음'))

    # 5. 방화벽 규칙
    say(f'\n[5] 방화벽 인바운드 규칙 — python 프로그램 또는 포트 {port} 관련 (차단이 허용보다 우선)')
    rules = [r for r in rules_inbound() if 'python' in (r.get('program', '') + r.get('name', '')).lower() or str(port) in re.split(r'[,\s]+', r.get('localport', ''))]
    blocks = [r for r in rules if r.get('enabled') in YES and r.get('action') in BLOCK]
    allows = [r for r in rules if r.get('enabled') in YES and r.get('action') in ALLOW]
    for r in rules:
        say(f'    [{"차단" if r.get("action") in BLOCK else "허용" if r.get("action") in ALLOW else r.get("action", "?")}·{"켬" if r.get("enabled") in YES else "끔"}] {r.get("name")}  프로필={r.get("profiles", "")}  {r.get("protocol", "")} 포트={r.get("localport", "")}  {r.get("program", "")}')
    if not rules:
        say('    (관련 규칙 없음 — 처음 "액세스 허용?" 창에서 허용하지 않았거나 회사 정책으로 관리됨)')

    def covers(r, c):
        p = profiles_en(r.get('profiles', '')) or ''
        return not p or c in p.split(',') or r.get('profiles', '').strip().lower() in ('all', '모두', 'any')
    # 6. 판정
    say('\n[6] 판정')
    probs = []
    if not up:
        probs.append('서버가 이 PC 에서 응답하지 않습니다 → start_server.bat 로 서버를 켜세요 (또는 자동 시작 확인).')
    bad = [r for r in blocks if any(covers(r, c) for c in cats)]
    if bad:
        probs.append('지금 네트워크에 python 을 막는 "차단" 규칙이 있습니다: ' + ', '.join(f'{r["name"]}({r.get("profiles", "")})' for r in bad) + ' → allow_firewall.bat 를 관리자 권한으로 실행.')
    if cats and not any(any(covers(r, c) for c in cats) for r in allows):
        probs.append(f'지금 프로필({", ".join(cats)})에서 python/포트 {port} 를 허용하는 규칙이 없습니다 → allow_firewall.bat 를 관리자 권한으로 실행.')
    if 'public' in cats:
        probs.append('지금 네트워크가 "공용" 입니다 — 회사 Wi-Fi 가 공용으로 잡히면 방화벽이 대부분 막습니다.')
    if probs:
        for p in probs:
            say('  ✗ ' + p)
        say('  관리자 권한이 없으면 IT 에 "이 PC 로 들어오는 TCP %d 인바운드 허용(공용·개인·도메인 모두)"을 요청하세요.' % port)
    else:
        say('  ✓ 이 PC 쪽(서버 · 방화벽)은 문제가 보이지 않습니다.')
        say('    그래도 부서원이 못 붙으면 회사망에서 Wi-Fi ↔ 유선 PC 간 통신이 막혀 있을 가능성 → IT 문의, 또는 서버 PC 는 유선 LAN 사용.')
        say(f'    부서원 PC 에서 브라우저로 http://{socket.gethostname()}:{port}/ 와 ' + ', '.join(f'http://{i}:{port}/' for i in ips) + ' 를 열어 보세요.')

    # --fix
    if a.fix:
        say('\n[고치기]')
        if not is_admin():
            say('  ✗ 관리자 권한이 아닙니다. allow_firewall.bat 를 마우스 오른쪽 → [관리자 권한으로 실행]')
        else:
            name = f'DeptDashboard {port}'
            run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name={name}'])
            txt, rc = run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', f'name={name}', 'dir=in', 'action=allow', 'protocol=TCP', f'localport={port}', 'profile=any'])
            say(f'  {"✓" if rc == 0 else "✗"} 포트 {port} 인바운드 허용 규칙 추가 (모든 네트워크 종류): {txt.strip().splitlines()[-1] if txt.strip() else rc}')
            for r in blocks:
                cmd = ['netsh', 'advfirewall', 'firewall', 'set', 'rule', f'name={r["name"]}', 'dir=in']
                if r.get('program'):
                    cmd.append(f'program={r["program"]}')
                pe = profiles_en(r.get('profiles', ''))
                if pe:
                    cmd.append(f'profile={pe}')
                cmd += ['new', 'enable=no']
                txt, rc = run(cmd)
                say(f'  {"✓" if rc == 0 else "✗"} 차단 규칙 끔: {r["name"]} ({r.get("profiles", "")}) {txt.strip().splitlines()[-1] if txt.strip() else ""}')
            say('  → 부서원 PC 에서 다시 접속해 보세요. 그래도 안 되면 회사망(Wi-Fi ↔ 유선) 문제 → IT 문의.')

    try:
        with open(os.path.join(HERE, 'network_check.txt'), 'w', encoding='utf-8-sig') as f:
            f.write('\n'.join(LINES) + '\n')
        say(f'\n저장: {os.path.join(HERE, "network_check.txt")}  (이 파일이나 화면 사진을 보내 주세요)')
    except OSError as e:
        say(f'\n(파일 저장 실패: {e})')


if __name__ == '__main__':
    main()
