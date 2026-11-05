"""hotfix132 — 화면 JS 의 구문 검사.  괄호 하나가 빠져도 화면 전체가 하얘지는데, 문자열 시험은 그것을 못 잡는다.

* app/static/**/*.js (*.min.js · vendor/ · valve/ 제외) 를 `node --check`.
* *.html 안의 `<script>` (src 없고 module 아닌 것) 는 `new Function(글)` 로 파싱만.
node 가 없으면 건너뛴다 (회사 PC 에 node 22 LTS 를 깔면 돈다 — docs/offline_setup_windows.md).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "app" / "static"


def _skip_rel(rel: str) -> bool:
    return rel.startswith("valve/") or "/vendor/" in "/" + rel or rel.endswith(".min.js")


JS = [p for p in sorted(STATIC.rglob("*.js")) if not _skip_rel(p.relative_to(STATIC).as_posix())]
HTML = [p for p in sorted(STATIC.rglob("*.html")) if not _skip_rel(p.relative_to(STATIC).as_posix())]
_SCRIPT = re.compile(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", re.S | re.I)


def _node():
    node = shutil.which("node")
    if not node:
        pytest.skip("node 없음 — JS 구문 시험")
    return node


def test_there_is_something_to_check():
    names = {p.name for p in JS}
    assert {"app.js", "logic.js"} <= names


@pytest.mark.parametrize("path", JS, ids=lambda p: p.relative_to(STATIC).as_posix())
def test_js_file_parses(path):
    node = _node()
    r = subprocess.run([node, "--check", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-800:]


def inline_scripts(html: str) -> list[str]:
    out = []
    for m in _SCRIPT.finditer(html):
        attrs = m.group("attrs").lower()
        if "src=" in attrs or "module" in attrs or ("type=" in attrs and "javascript" not in attrs):
            continue
        if m.group("body").strip():
            out.append(m.group("body"))
    return out


def test_inline_script_picker_skips_src_module_and_data():
    html = ('<script src="a.js"></script><script type="module">import x from "y"</script>'
            '<script type="application/json">{"a":1}</script><script>var ok = 1;</script>')
    assert inline_scripts(html) == ["var ok = 1;"]


@pytest.mark.parametrize("path", HTML, ids=lambda p: p.relative_to(STATIC).as_posix())
def test_inline_scripts_in_html_parse(path):
    node = _node()
    bodies = inline_scripts(path.read_text(encoding="utf-8", errors="replace"))
    if not bodies:
        pytest.skip("inline script 없음")
    code = ("const src = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
            "for (const [i, s] of src.entries()) { try { new Function(s); } "
            "catch (e) { console.error('script #' + i + ': ' + e.message); process.exitCode = 1; } }")
    r = subprocess.run([node, "-e", code], input=json.dumps(bodies), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[-800:]
