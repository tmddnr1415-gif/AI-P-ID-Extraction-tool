"""hotfix72 — 읽기 쉽게 · 덜 붐비게 (화면 회차 · 판정 0줄).

못박는 것:
  1. 머리줄의 드문 동작(적용 규칙 · 템플릿 · 진단 · 피드백 · 재분석)은 '더보기' 메뉴 하나로 — id 는 그대로다
     (그 id 로 찾는 코드가 조용히 null 을 받지 않게).
  2. 머리줄 판은 바깥을 누르면 닫히고, 메뉴 안의 단추를 누르면 그 일을 하고 닫힌다.  안쪽 판은 하나만.
  3. 화면이 띄우는 범례·프로필 문장에 마크다운 별표(`**`)가 없다 — 화면은 textContent 라 글자 그대로 보였다.
  4. 정보 띠가 같은 사실(대조 못 한 항목)을 두 번 말하지 않는다.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")


def _fn(name):
    m = re.search(rf"(?:async )?function {name}\(.*?\n}}\n", JS, re.S)
    assert m, name
    return m.group(0)


def test_rare_actions_live_in_one_more_menu_and_keep_their_ids():
    a = HTML.index('<details id="more-actions"')
    menu = HTML[a:HTML.index('<span class="act-sep"', a)]
    for i in ("rules", "rules-body", "tmpl", "tmpl-body", "diag", "feedback-export", "reanalyse"):
        assert f'id="{i}"' in menu, i
        assert HTML.count(f'id="{i}"') == 1, i
    # 자주 쓰는 동작은 메뉴 밖에 그대로
    head = HTML[HTML.index('class="head-actions"'):HTML.index('</header>')]
    for i in ("scope", "symbols", "report-list", "voc-btn", "save-final", "excel"):
        assert f'id="{i}"' in head and f'id="{i}"' not in menu, i


def test_header_panels_close_on_outside_click_and_menu_items_close_the_menu():
    i = JS.index("hotfix72 — 머리줄 판")
    block = JS[i:i + 1600]
    assert "header details.scope[open]" in block and "!det.contains(ev.target)" in block
    assert 'button.menu-item' in block and "more.open = false" in block
    assert "o !== inner" in block and "o.open = false" in block          # 안쪽 판은 하나만
    assert 'more.classList.toggle("wide"' in block
    assert "details.more.wide > .scope-body.menu-body" in CSS


def _function_strings(src: str, name: str) -> list[str]:
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name)
    doc = ast.get_docstring(fn, clean=False)
    out = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Constant) and n.value == doc:
            continue
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
    return out


def test_legend_sentences_carry_no_markdown_stars():
    strings = _function_strings(MAIN, "_legend_facts")
    assert strings, "_legend_facts"
    bad = [s for s in strings if "**" in s]
    assert not bad, bad


def test_infobar_does_not_say_the_uncompared_count_twice():
    body = _fn("loadLegendProfile")
    code = "\n".join(l for l in body.splitlines() if not l.strip().startswith("//"))
    assert "대조 못 한 항목" not in code          # 서버 문장(compare_note)이 이미 말한다
    assert "lb-short" in body                    # 접힌 줄은 짧은 말
    assert "#infobars.compact .legend-bar .lb-short" in CSS
