"""L81 — 기호 상자 안에 통째로 든 선 토막(들여올 때 옮겨진 ⊠ 안쪽 획)은 신호선이 아니다.
남겨 두면 NOT 의 입력선과 출력선이 상자 한가운데서 만나 자기 입력을 뒤집는 고리가 되고, 시뮬레이션이 MAX_ITER 까지 돈다
(19VA Typical 0013 — 827장 묶음 첫 시뮬레이션 23초)."""
from app.logic import draw_sim as DS


def _doc(inner):
    nb = {"id": "B1", "kind": "NOT", "x": 100.0, "y": 100.0, "w": 6.4, "h": 8.0, "text": "NOT", "label": "", "param": {}}
    cx, top, bot = 103.2, 100.0, 108.0
    wires = [{"id": "in", "pts": [[cx, 150.0], [cx, bot]]}, {"id": "out", "pts": [[cx, top], [cx, 60.0]]}]
    if inner:   # 상자 안 가운데에서 만나는 토막 넷 (옮겨진 ⊠ 획)
        wires += [{"id": "i1", "pts": [[cx, 104.0], [cx, top]]}, {"id": "i2", "pts": [[cx, 104.0], [cx, bot]]},
                  {"id": "i3", "pts": [[106.4, 104.0], [cx, 104.0]]}]
    return {"id": "aaaaaaaaaaaa", "N": 50, "blocks": [nb], "wires": wires, "left": {}, "right": {}}


def test_wires_inside_a_symbol_box_are_not_signal_wires():
    for inner in (False, True):
        s = DS.to_sheet(_doc(inner), 1)
        nets = {p["net"] for p in s["ports"] if p["block"] == "B1"}
        assert len(nets) == 2, f"NOT 의 위 · 아래 선이 한 선이 되었다 (inner={inner}) {nets}"
