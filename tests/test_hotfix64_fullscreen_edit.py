"""hotfix64 — 도면 전체화면(또는 목록을 끝까지 접은 때)에서도 도면 위에서 고치고, 목록에 저절로 반영된다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def _block(start, end):
    return JS[JS.index(start):JS.index(end, JS.index(start))]


def test_one_save_path_for_grid_and_drawing():
    core = _block("async function saveField(", "function syncRowCell(")
    assert core.count("fetch(`/jobs/${S.job.id}/rows/${row.key}`") == 1 and "askAuthor(" in core
    assert "syncRowCell(row, field)" in core and "renderFloatEdit()" in core     # 목록 칸 · 카드가 같은 값으로
    grid = _block("async function saveEdit(", "/* ---------------- hotfix64")
    assert "saveField(row, field, td.textContent.trim())" in grid and "fetch(" not in grid
    card = _block("function renderFloatEdit()", "function setFull(")
    assert "saveField(r, f, inp.value)" in card and "fetch(" not in card


def test_card_fields_are_the_grid_editable_columns():
    assert "const FEDIT_FIELDS = COLS.filter(c => c[2]);" in JS          # 칸 목록은 머리글과 같은 표


def test_card_shows_when_the_list_is_not_visible():
    assert 'document.body.classList.contains("pid-full") || listHidden()' in JS
    assert "renderFloatEdit();             // hotfix64" in _block("function select(", "function deselect(")
    assert 'id="full-toggle"' in HTML and 'id="fedit"' in HTML


def test_escape_leaves_fullscreen_only_when_nothing_is_selected():
    esc = JS[JS.index('if (ev.key !== "Escape" || ev.target.isContentEditable) return;'):][:400]
    assert 'if (!S.sel && document.body.classList.contains("pid-full")) { setFull(false); return; }' in esc
    assert "fullscreenchange" in JS
