"""L60 — 작도 화면: Shift 를 누른 채 끌면 이웃 기호 · 선에 맞춘다 · 고른 기호의 정렬 · 균등 간격.

전부 화면(`logic_draw.js`)에서만 일어난다 — 서버 `draw.py` 는 그리는 자리를 모른다.  여기서는 화면 코드에 그 길이 있는지와
PDF/DXF 쪽에 새 말이 섞이지 않았는지만 본다 (실제 동작은 `spike/ui_audit_l60.py` 가 크롬으로 확인한다).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/logic_draw.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/logic_draw.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/logic_draw.css").read_text(encoding="utf-8")


def test_shift_drag_aligns_to_neighbours_and_wires():
    for name in ("alignTargets", "alignFit", "alignBlockNow", "arrangeSel"):
        assert f"function {name}(" in JS
    assert "const strong = !!e.shiftKey" in JS                       # 끌 때 Shift
    assert 'alignMove([...S.sel], dx, dy, strong)' in JS
    assert 'if (strong) for (const w of S.doc.wires' in JS            # 선의 토막에도
    assert 'for (const pt of ports(b)) { tx.push' in JS               # 이웃 단자 높이에도
    assert "if (!strong && !S.guide.align && !S.rg.v.length && !S.rg.h.length) return [dx, dy];" in JS   # 안내선을 꺼 두어도 Shift · 가이드선(L66)은 듣는다
    assert "if (e.shiftKey) { const nb = S.doc.blocks[S.doc.blocks.length - 1]; alignBlockNow(nb)" in JS   # 팔레트에서 놓을 때


def test_arrange_buttons_and_shortcuts():
    for op in ("left", "hcenter", "right", "top", "vcenter", "bottom", "disth", "distv"):
        assert f'data-op="{op}"' in HTML
        assert f'"{op}"' in JS or f"op === \"{op}\"" in JS
    assert 'arrangeSel("disth")' in JS and 'arrangeSel("distv")' in JS
    assert ".dw-arrange" in CSS and ".align.wire" in CSS


def test_distribute_keeps_ports_on_half_rows_when_snapping():
    """자석이 켜져 있으면 틈을 반 행의 배수로 — 단자가 행 자리에 남는다."""
    i = JS.index("function arrangeSel(")
    body = JS[i:JS.index("\n}\n", i)]
    assert "Math.round(gap / g) * g" in body and "L.PITCH / 2" in body
    assert "pushUndo();" in body and "markDirty();" in body          # 되돌릴 수 있고 저장 대상이다


def test_server_export_knows_nothing_about_arranging():
    src = (ROOT / "app/logic/draw.py").read_text(encoding="utf-8").lower()
    for word in ("arrange", "distribute", "alignfit", "shiftkey"):
        assert word not in src, word
