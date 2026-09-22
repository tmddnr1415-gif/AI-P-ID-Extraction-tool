"""41회차 [C] — 범례 유도가 회전 장의 획을 표시 좌표로 읽는다.

SADARA·TC2·UAD 는 `/Rotate 270` 이고 `d["items"]` 의 점은 회전 전 좌표라, 원 중심(표시 좌표)과
획이 서로 다른 자리에 있었다 → 끝막대를 못 찾고 표 괘선을 잡아 `bar_reach_radii` 가 87·84·116.
"""
import pymupdf
from app.engine import legend_rules as lr


def _stadium_page(rotate):
    doc = pymupdf.open(); page = doc.new_page(width=300, height=200)
    sh = page.new_shape(); sh.draw_line((100, 100), (130, 100)); sh.finish(width=0.3, closePath=False); sh.commit()
    page.set_rotation(rotate)
    return doc, page


def test_straight_items_follow_the_page_rotation():
    for rot in (0, 90, 270):
        doc, page = _stadium_page(rot)
        d = page.get_drawings()[0]
        raw = lr._straight_items(d)[0]
        disp = lr._straight_items(d, m=page.rotation_matrix)[0]
        exp0, exp1 = pymupdf.Point(100, 100) * page.rotation_matrix, pymupdf.Point(130, 100) * page.rotation_matrix
        assert abs(disp[0][0] - exp0.x) < 1e-6 and abs(disp[0][1] - exp0.y) < 1e-6
        assert abs(disp[1][0] - exp1.x) < 1e-6 and abs(disp[1][1] - exp1.y) < 1e-6
        if rot == 0:
            assert raw == disp                     # 회전 0 은 항등 — AL NOUF1 이 한 점도 안 움직이는 근거
        else:
            assert raw != disp
        doc.close()
