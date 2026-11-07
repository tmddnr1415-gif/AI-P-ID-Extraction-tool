#!/usr/bin/env python3
"""src/ 를 단일 파일 ic-3d-builder/index.html 로 합친다 (더블클릭으로 열리게).

three.js 는 cdnjs 에서 그대로 불러온다. 나머지 로컬 css/js 는 인라인한다.
    python3 ic-3d-builder/dev/build.py
"""
import pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
html = (SRC / 'index.html').read_text(encoding='utf-8')

def css(m):
    return '<style>\n' + (SRC / m.group(1)).read_text(encoding='utf-8') + '\n</style>'

def js(m):
    code = (SRC / m.group(1)).read_text(encoding='utf-8').replace('</script', '<\\/script')
    return f'<script>/* {m.group(1)} */\n{code}\n</script>'

html = re.sub(r'<link rel="stylesheet" href="\./([\w.-]+)">', css, html)
html = re.sub(r'<script src="\./([\w.-]+)"></script>', js, html)
banner = '<!-- 생성 파일: ic-3d-builder/src/ 를 고치고 dev/build.py 로 다시 만드세요 -->\n'
out = ROOT / 'index.html'
out.write_text(html.replace('<!doctype html>\n', '<!doctype html>\n' + banner, 1), encoding='utf-8')
print(f'{out.relative_to(ROOT.parent)}  {out.stat().st_size/1024:.0f} KB')
