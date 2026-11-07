"""L61 — FROM/TO 칸 시트 · 행 자동완성 (화면 코드 검사 · 판정 0줄)."""
from pathlib import Path

JS = (Path(__file__).resolve().parent.parent / "app/static/logic_draw.js").read_text(encoding="utf-8")
HTML = (Path(__file__).resolve().parent.parent / "app/static/logic_draw.html").read_text(encoding="utf-8")


def test_fm_to_cells_get_sheet_autocomplete():
    assert 'id="cellac"' in HTML
    assert "refAC(inp, side, f" in JS                         # FM · TO 칸에서만
    assert '(f === "fm" || f === "to")' in JS


def test_sheet_match_prefix_first_then_contains():
    body = JS[JS.index("function refMatch"):JS.index("async function refDoc")]
    assert "startsWith(q)" in body and "includes(q)" in body   # G → G123 먼저, 그다음 이름 안에 G 가 든 시트


def test_rows_come_from_the_other_sheet_opposite_side():
    body = JS[JS.index("function refAC"):JS.index("function nextCell")]
    assert 'f === "fm" ? "right" : "left"' in body             # FM = 상대 장의 출력 행 · TO = 상대 장의 입력 행
    assert "prompt(" not in body and "confirm(" not in body and "alert(" not in body


def test_separator_is_learned_not_fixed():
    body = JS[JS.index("function refSep"):JS.index("function refMatch")]
    assert "cnt" in body and '|| "-"' in body
