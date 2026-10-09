"""hotfix18 — 목록 행 음영(사람이 한 일) · 경계를 끌면 도면이 창에 맞춰 커진다."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def test_row_state_order_delete_then_added_then_edit():
    seg = JS.split("function rowUserState(r) {", 1)[1].split("\n}\n", 1)[0]
    i_del, i_add, i_edit = seg.index('"userdel"'), seg.index('"added"'), seg.index('"useredit"')
    assert i_del < i_add < i_edit


def test_row_state_is_painted_on_render_and_after_every_edit_path():
    assert "paintRowState(tr, r);" in JS
    assert JS.count("repaintRow(") >= 4          # 정의 + 칸 편집 · 일괄 문장 · 공급 주체 일괄


def test_row_shading_colours():
    assert "tbody tr.useredit { background: rgba(255, 214, 10" in CSS      # 연한 노랑
    assert "tbody tr.userdel { background: rgba(255, 59, 48" in CSS        # 연한 붉음
    assert "tbody tr.userdel td { text-decoration: line-through" in CSS    # 취소선
    assert "tbody tr.added { background: rgba(52, 199, 89" in CSS          # 연한 녹색


def test_gutter_drag_refits_and_caps_at_full_drawing_width():
    seg = JS.split('const SPLIT_KEY = "pid.split";', 1)[1]
    assert "fit();" in seg and "requestAnimationFrame" in seg
    # hotfix63 — 사용자 요구 *"칸 조절을 최대로"* 로 도면 폭 상한(leftCap)을 뺐다.  끝까지 가고,
    # 남기는 것은 손잡이를 다시 잡을 폭 하나다 (tests/test_hotfix63_memo_split.py).
    assert "leftCap()" not in seg and "GRIP" in seg
