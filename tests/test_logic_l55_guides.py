"""L55 — 작도 화면의 모눈종이 · 눈금자 · 정렬 안내선은 화면 전용이다.

내보내는 PDF · DXF 는 L54 와 같은 양식이어야 한다 (안내선이 그려지면 분석기가 선으로 읽는다).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/logic_draw.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/logic_draw.html").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/logic_draw.css").read_text(encoding="utf-8")

def test_screen_has_grid_rulers_and_align_guides():
    for name in ("renderGrid", "drawRulers", "alignMove", "drawCross", "drawAlign"):
        assert f"function {name}(" in JS
    for ident in ("ruler-x", "ruler-y", "ruler-corner", "g-grid", "g-ruler", "g-align", "g-cross"):
        assert f'id="{ident}"' in HTML
    for cls in (".grid line.gh", ".grid line.g5", ".align", ".cross", ".dw-ruler-x"):
        assert cls in CSS


def test_guides_never_reach_the_export():
    """PDF · DXF 는 서버 draw.py 가 문서(JSON)에서 그린다 — 화면 안내 요소의 이름이 그쪽에 없어야 한다."""
    src = (ROOT / "app/logic/draw.py").read_text(encoding="utf-8").lower()
    for word in ("ruler", "grid", "gframe", "gnum", "guide", "crosshair"):
        assert word not in src, word


def test_export_pdf_has_no_guide_strokes():
    """같은 문서를 PDF 로 내보내면 선 수는 표 · 타이틀 · 블록 · 선의 것뿐이다 — 모눈이 섞이면 수백 개가 늘어난다."""
    import sys
    sys.path.insert(0, str(ROOT))
    from app.logic import draw
    import fitz

    doc = draw.new_doc("G", "T", "1-1", N=50)
    pdf = draw.to_pdf(doc)
    with fitz.open(stream=pdf, filetype="pdf") as d:
        n = sum(len(p.get_drawings()) for p in d)
    assert n < 400, n   # 모눈종이(반 행 가로 100 + 세로 97 + 틀)가 들어가면 이 수를 훌쩍 넘는다
