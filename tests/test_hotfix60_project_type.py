"""hotfix60 — 프로젝트가 입찰인지 실행인지 화면 곳곳에 분명히 적는다.

새 프로젝트 이름을 적는 동안 고른 종류는 **만들 프로젝트**의 것이다 — 예전에는 앞서 고른 다른
프로젝트의 선언을 바꾸거나 [만들기] 뒤 '자동' 으로 되돌아갔다.  눌러서 확인한 것은
`spike/ui_audit_project_type.py` → `out/hotfix60/ui/`.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")


def _block(start: str, n: int = 2500) -> str:
    i = JS.index(start)
    return JS[i:i + n]


def test_one_chip_reads_the_ledger_value():
    assert "function modeChip(" in JS and "function projectMode(" in JS
    assert "p.mode && p.mode.value" in _block("function projectMode(", 200)
    assert 'id="proj-type"' in HTML


def test_chip_is_shown_in_every_place_a_project_appears():
    assert "projectOptionText(p)" in _block("async function loadProjects(")       # 고르는 상자
    assert "modeChip(projectMode(p))" in _block("async function listHome(")       # 저장된 프로젝트
    assert JS.count("modeChip(projectMode(p))") >= 2                              # + 왼쪽 메뉴
    assert "renderProjectType()" in _block("function chooseProject(", 3000)


def test_mode_chosen_while_creating_belongs_to_the_new_project():
    radio = _block('document.querySelectorAll(\'input[name="mode"]\').forEach', 1600)
    assert '!$("#proj-new").classList.contains("hidden")' in radio              # 고른 다른 프로젝트를 안 건드린다
    save = _block('$req("#proj-save").addEventListener', 2600)
    assert 'const chosen = (modeRadio() && modeRadio().value) || EMBED.mode' in save
    assert "/mode`" in save and "askAuthor(" in save
