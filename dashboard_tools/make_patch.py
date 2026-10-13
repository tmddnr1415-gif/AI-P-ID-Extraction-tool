r"""dashboard/ 의 바뀐 파일만 담은 회사 PC 적용용 zip 을 만든다.

    python3 dashboard_tools/make_patch.py              # 마지막 전달본(태그) 이후 바뀐 파일
    python3 dashboard_tools/make_patch.py --base REF   # 기준을 직접 지정
    python3 dashboard_tools/make_patch.py --tag        # 만든 뒤 '전달함' 태그를 단다

zip 구성 (최상위 폴더 하나):
    APPLY.bat       ASCII · CRLF · chcp 없음. 회사본이 base\ 와 같을 때만 백업 후 덮어씀,
                    다르면 옆에 .new 로 둔다, 없던 파일은 추가.
    읽어주세요.txt   적용 방법 · 바뀐 파일 목록 (UTF-8 BOM · CRLF, 메모장용)
    new\...         바뀐 파일의 새 내용
    base\...        같은 파일의 기준판 내용 (비교용, 새로 생긴 파일은 없음)

deploy/ 는 server.py 가 dashboard.html 에서 자동으로 만들므로 넣지 않는다.
"""
import argparse, datetime, os, py_compile, re, subprocess, sys, tempfile, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = 'dashboard'
HERE = os.path.dirname(os.path.abspath(__file__))
SKIP_PREFIX = ('deploy/',)


def git(*a, binary=False):
    r = subprocess.run(['git', '-C', ROOT, *a], capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode('utf-8')


def default_base():
    tags = git('tag', '--list', 'dashboard-delivered-*', '--sort=-creatordate').split()
    return tags[0] if tags else 'dashboard-base'


def show(ref, path):
    try:
        return git('show', f'{ref}:{APP}/{path}', binary=True)
    except subprocess.CalledProcessError:
        return None


def crlf(s):
    return s.replace('\r\n', '\n').replace('\n', '\r\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=None)
    ap.add_argument('--out', default=os.path.join(ROOT, 'dashboard_patches'))
    ap.add_argument('--tag', action='store_true', help="만든 뒤 HEAD 에 dashboard-delivered-<이름> 태그")
    a = ap.parse_args()
    base = a.base or default_base()

    if git('status', '--porcelain', '--', APP).strip():
        sys.exit(f'[중단] {APP}/ 에 커밋하지 않은 변경이 있다. 커밋 후 다시 실행.')

    names = git('-c', 'core.quotepath=false', 'diff', '--name-status', '--no-renames',
                f'{base}..HEAD', '--', APP).splitlines()
    changed, deleted, skipped = [], [], []
    for line in names:
        st, p = line.split('\t', 1)
        rel = p[len(APP) + 1:]
        if rel.startswith(SKIP_PREFIX):
            skipped.append(rel)
        elif st == 'D':
            deleted.append(rel)
        else:
            changed.append(rel)
    if not changed:
        sys.exit(f'[중단] {base} 이후 바뀐 파일이 없다.')

    # 버전·문법·문서 점검
    warn = []
    def ver(ref, rel, key):
        m = re.search(key.encode() + rb" = '([^']+)'", show(ref, rel) or b'')
        return m and m[1]
    for rel, key in (('dashboard.html', 'APP_VERSION'), ('server.py', 'SERVER_VERSION')):
        if rel in changed and ver(base, rel, key) == ver('HEAD', rel, key):
            warn.append(f'{rel} 이 바뀌었는데 {key} 가 그대로다.')
    for rel in changed:
        if rel.endswith('.py'):
            with tempfile.NamedTemporaryFile('wb', suffix='.py', delete=False) as t:
                t.write(show('HEAD', rel))
            try:
                py_compile.compile(t.name, doraise=True)
            except py_compile.PyCompileError as e:
                sys.exit(f'[중단] {rel} 문법 오류:\n{e}')
            finally:
                os.unlink(t.name)
        if rel.endswith('.bat'):
            b = show('HEAD', rel)
            if not b.isascii() or b'chcp' in b.lower() or re.search(rb'(?<!\r)\n', b):
                warn.append(f'{rel}: ASCII · CRLF · chcp 없음 규칙에 어긋난다.')
    if 'DASHBOARD_ARCHITECTURE.md' not in changed:
        warn.append('DASHBOARD_ARCHITECTURE.md 끝에 변경 이력을 덧붙이지 않았다.')

    now = datetime.datetime.now()
    name = now.strftime('%Y%m%d_%H%M')
    top = f'dashboard_patch_{name}'
    restart = 'server.py' in changed or 'watchdog.py' in changed
    restart_note = ('echo  * server.py changed: restart the server '
                    '(uninstall_autostart.bat then install_autostart.bat).') if restart else 'rem'

    with open(os.path.join(HERE, 'apply_patch.bat.tmpl'), encoding='ascii') as f:
        bat = f.read().replace('__PATCH_NAME__', name).replace('__RESTART_NOTE__', restart_note)
    bat = crlf(bat).encode('ascii')
    assert b'chcp' not in bat.lower()

    lines = [f'[계장ENG그룹 주간업무 Dashboard 수정본 {name}]', '',
             '■ 적용 방법',
             '  1. 이 zip 을 아무 곳에나 풀고, 대시보드 화면(Edge)을 닫는다.',
             '  2. APPLY.bat 을 더블클릭한다. (C:\\Claude 아래 Dashboard 폴더를 스스로 찾는다.',
             '     못 찾으면 대시보드 폴더를 창에 끌어다 놓고 Enter.)',
             '  3. 결과 표시',
             '     [updated] 원본을 backup\\patch_… 폴더에 백업한 뒤 바꿈',
             '     [added]   없던 파일을 새로 넣음',
             '     [same]    이미 같은 내용이라 건드리지 않음',
             '     [.new]    회사에서 이미 고친 파일이라 덮지 않고 옆에 .new 로 둠',
             '               → 회사 Claude Code 에게 "○○.new 를 합쳐 줘" 라고 맡긴다.']
    if restart:
        lines += ['  4. server.py 가 바뀌었으므로 서버를 다시 켠다',
                  '     (uninstall_autostart.bat → install_autostart.bat).']
    lines += ['  되돌리기: backup\\patch_… 폴더의 파일을 원래 자리로 복사하면 된다.', '',
              f'■ 바뀐 파일 ({len(changed)}개)'] + [f'  - {r}' for r in changed]
    if deleted:
        lines += ['', '■ 기준판에서 없어진 파일 (자동으로 지우지 않음, 필요하면 직접 정리)'] + \
                 [f'  - {r}' for r in deleted]
    lines += ['', '자세한 변경 내용은 DASHBOARD_ARCHITECTURE.md 맨 끝 "변경 이력" 을 본다.', '']
    readme = b'\xef\xbb\xbf' + crlf('\n'.join(lines)).encode('utf-8')

    os.makedirs(a.out, exist_ok=True)
    zpath = os.path.join(a.out, f'{top}.zip')
    with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(f'{top}/APPLY.bat', bat)
        z.writestr(f'{top}/읽어주세요.txt', readme)
        for rel in changed:
            z.writestr(f'{top}/new/{rel}', show('HEAD', rel))
            old = show(base, rel)
            if old is not None:
                z.writestr(f'{top}/base/{rel}', old)

    print(f'기준: {base}  →  HEAD {git("rev-parse", "--short", "HEAD").strip()}')
    print(f'만듦: {zpath}')
    for r in changed:
        print(f'  + {r}')
    for r in skipped:
        print(f'  (제외, 서버 자동 생성) {r}')
    for r in deleted:
        print(f'  (삭제됨, 자동 처리 안 함) {r}')
    for w in warn:
        print(f'[주의] {w}')
    if a.tag:
        git('tag', f'dashboard-delivered-{name}')
        print(f'태그: dashboard-delivered-{name}  (git push origin --tags 로 올릴 것)')


if __name__ == '__main__':
    main()
