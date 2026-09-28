"""hotfix21 — SADARA Typical: 네모 캡션 · 번호끼리 짝 · 부품 점 (스팀 트랩).

사용자: *"Drain Typical configuration 에는 번호가 붙는다 … 서로가 매칭이 되어야 한다.
Drain Typical 에 Number 가 없으면 없는 것이고, 넘버가 있으면 넘버끼리 매칭"* ·
*"ST 와 같은 Steam Trap 은 … 단순히 Steam Trap point 수량만 List 에 산출한다"*.
SADARA PDF 는 이 환경에 없어 그 도면의 **모양**(스크린샷)을 합성 쪽으로 옮겨 잰다.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pymupdf
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "engine")); sys.path.insert(0, str(ROOT))
import typical  # noqa: E402
from app import pipeline as P  # noqa: E402
projectconfig = P.projectconfig   # 파이프라인이 쓰는 그 모듈 (센티널이 같아야 한다)

AREA = pymupdf.Rect(0, 0, 900, 800)
D = 7.1


def _w(x, y, text, h=4):
    return (pymupdf.Rect(x, y - h / 2, x + 4 * len(text), y + h / 2), text)


def _line_words(x, y, text):
    out, cx = [], x
    for t in text.split():
        out.append(_w(cx, y, t)); cx += 4 * len(t) + 3
    return out


class _PC:
    def __init__(self):
        self.words, self._d, self._s = [], [], []
    def circle(self, x, y, word):
        self._d.append({"items": [("c",)] * 4, "bbox": pymupdf.Rect(x - D / 2, y - D / 2, x + D / 2, y + D / 2)})
        self.words.append((pymupdf.Rect(x - 1.5, y - 1.5, x + 1.5, y + 1.5), word))
    def square(self, x, y, word):
        r = pymupdf.Rect(x - D / 2, y - D / 2, x + D / 2, y + D / 2)
        self._d.append({"items": [("re", r, 1)], "bbox": r})
        self.words.append((pymupdf.Rect(x - 2.5, y - 1.5, x + 2.5, y + 1.5), word))
    def seg(self, x0, y0, x1, y1):
        self._s.append((pymupdf.Point(x0, y0), pymupdf.Point(x1, y1)))
    def box(self, x0, y0, x1, y1):
        r = pymupdf.Rect(x0, y0, x1, y1)
        self._d.append({"items": [("re", r, 1)], "bbox": r})
    def drawings(self):
        return self._d
    def segments(self):
        return self._s


def _sadara_like():
    pc = _PC()
    # 본문 드레인 — 배관(y=300)에서 리더가 내려와 원 `D`, 그 아래 `DRAIN n`
    pc.seg(0, 300, 450, 300)
    for x, n in ((100, 1), (200, 5), (300, 9)):
        pc.seg(x, 300, x, 330 - D / 2)
        pc.circle(x, 330, "D")
        pc.words += _line_words(x - 12, 342, f"DRAIN {n}")
    # 상세 띠 — 가로선 둘과 칸막이 세로선 하나, 한 줄에 캡션 둘 (네모 `D`)
    pc.seg(0, 500, 900, 500); pc.seg(0, 780, 900, 780); pc.seg(450, 500, 450, 780)
    pc.square(20, 520, "D")
    pc.words += _line_words(26, 520, ": DETAIL OF DRAIN CONFIGURATION FOR DRAIN 1, 2, 3")
    pc.square(470, 520, "D")
    pc.words += _line_words(476, 520, ": DETAIL OF DRAIN CONFIGURATION FOR DRAIN 4-6")
    # 스팀 트랩 — 상세 상자 안에 같은 `ST` 네모가 배관 위에 부품으로 그려져 있다
    pc.box(600, 100, 850, 250)
    pc.square(612, 112, "ST")
    pc.words += _line_words(618, 112, ": DETAIL OF STEAM TRAP CONFIGURATION")
    pc.seg(650, 184, 750, 184); pc.square(700, 184, "ST")
    pc.seg(480, 350, 620, 350)
    for x, n in ((520, 1), (580, 2)):
        pc.seg(x, 350, x, 380 - D / 2)
        pc.square(x, 380, "ST")
        pc.words += _line_words(x - 20, 392, f"STEAM TRAP {n}")
    pc.words = [(pymupdf.Rect(r), t) for r, t in pc.words]
    return pc


def test_numbers_are_read_from_captions_without_inventing_the_gaps():
    assert typical.numbers_in("FOR DRAIN 1, 2, 3, 4, 5, 6") == frozenset(range(1, 7))
    assert typical.numbers_in("FOR DRAIN 7-12") == frozenset(range(7, 13))
    assert typical.numbers_in("HP TYPICAL DRAIN CONFIGURATION") is None
    assert typical.numbers_in("TO TANK 1A46-10LCM10-M05-0001") is None     # 도면번호 꼬리는 번호가 아니다
    assert typical.numbers_in("COLD REHEAT D2 : …") is None                 # 글자에 붙은 숫자


def test_square_captions_and_numbers_pair_each_drain_with_its_own_detail():
    t = typical.analyse(_sadara_like(), AREA, ceiling=11.4)
    d = [x for x in t.details if x.id == "D"]
    assert len(d) == 2 and not t.ambiguous                       # 같은 글자 둘이지만 번호가 가른다
    left, right = sorted(d, key=lambda x: x.mark.x0)
    assert left.nums == frozenset({1, 2, 3}) and right.nums == frozenset({4, 5, 6})
    assert "4-6" not in left.caption                             # 한 줄의 캡션을 다음 표식 앞에서 끊었다
    assert [round(v) for v in left.box] == [0, 500, 450, 780]    # 칸막이 세로선이 가른 칸
    assert [round(v) for v in right.box] == [450, 500, 900, 780]
    assert (left.refs, right.refs) == (1, 1)                     # DRAIN 1 → 왼쪽 · DRAIN 5 → 오른쪽
    assert t.unpaired.get("D 9") == 1                            # 어느 캡션의 번호에도 없는 DRAIN 9


def test_rows_in_each_drain_detail_take_only_their_own_refs():
    t = typical.analyse(_sadara_like(), AREA, ceiling=11.4)

    class R:
        def __init__(s, rect):
            s.page_no, s.rect, s.qty, s.evidence, s.needs_review = 1, rect, 1, {"qty_basis": "1 symbol x 1"}, ""
    a, b = R((100, 600, 120, 610)), R((600, 600, 620, 610))
    P._apply_typical([a, b], {1: t})
    assert (a.qty, b.qty) == (1, 1)
    assert a.evidence["typical"]["refs"] == 1 and b.evidence["typical"]["refs"] == 1


def test_an_unnumbered_caption_still_pairs_by_letter_alone():
    pc = _sadara_like()
    pc.words = [(r, t) for r, t in pc.words if not (r.y0 > 510 and r.y1 < 530 and t[:1].isdigit())]
    t = typical.analyse(pc, AREA, ceiling=11.4)
    assert t.ambiguous == {"D"}                                  # 번호가 없으면 38회차 그대로 — 모호


def test_steam_trap_detail_is_a_component_and_its_points_become_rows():
    t = typical.analyse(_sadara_like(), AREA, ceiling=11.4)
    st = [x for x in t.details if x.id == "ST"][0]
    assert st.component and st.refs == 2
    assert [lab for _r, lab in st.points] == ["STEAM TRAP 1", "STEAM TRAP 2"]

    class Mult:
        source = projectconfig.SOURCE_CONFIG
        def multiplier(self, unit):
            return projectconfig.UNDEFINED
    meta = {"unit_code": "10", "drawing_no": "1A46-10LBA10-M05-0002", "drawing_title": "HP STEAM"}
    rows = P._typical_point_rows(type("PC", (), {"page_no": 7})(), meta, t, Mult())
    assert [r.type for r in rows] == ["ST", "ST"]
    assert [r.qty for r in rows] == [1, 1]                       # 승수 미상 → x1 (hotfix21)
    assert [r.description for r in rows] == ["STEAM TRAP 1", "STEAM TRAP 2"]
    assert all("TYPICAL_POINT" in r.evidence["review_codes"] for r in rows)
    assert all("MULTIPLIER_DEFAULT_ONE" in r.evidence["review_codes"] for r in rows)

    class R:
        def __init__(s):
            s.page_no, s.rect, s.qty, s.evidence, s.needs_review = 1, (700, 200, 710, 210), 1, {"qty_basis": ""}, ""
    inner = R()
    P._apply_typical([inner], {1: t})
    assert inner.qty == 1                                        # 부품 상세 안은 곱하지 않는다


def test_drains_are_not_components():
    t = typical.analyse(_sadara_like(), AREA, ceiling=11.4)
    assert not any(x.component for x in t.details if x.id == "D")
    assert P._typical_point_rows(None, {}, typical.Typical(), None) == []
