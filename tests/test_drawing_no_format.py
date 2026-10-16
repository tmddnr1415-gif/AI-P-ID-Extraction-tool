"""37회차 — 도면번호의 모양도 도면이 말한다 (`derive_layout._drawing_no_pattern`).

TC2 는 56장이 `D02J-00GEN00-M05-0001` 꼴이고 4장이 `D02J-31PGB0-M05-0001`(둘째 자리 6자)이다.
AL NOUF1 에서 옮겨 적은 `formats.drawing_no` 는 뒤의 넷을 못 받아 그 장이 행 0 이었다.
"""
import re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))
import derive_layout as dl     # noqa: E402


class _R:
    def __init__(self, x0, y0, x1=None):
        self.x0, self.y0, self.x1 = x0, y0, (x1 if x1 is not None else x0 + 40)


class _Page:
    def __init__(self, page_no, words):
        self.page_no = page_no
        self.words = [(_R(10.0, 10.0), t) for t in words]


REGION = (0.0, 0.0, 100.0, 100.0)


def test_one_shape_reads_as_the_configured_pattern():
    pages = [_Page(i, ["DWG", "D00P-00GEN00-M05-000%d" % i]) for i in range(1, 4)]
    pat = dl._drawing_no_pattern(dl._drawing_no_shapes(pages, REGION))
    assert pat == r"^[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}-\d{4}$"
    assert re.match(pat, "D00P-10LBA10-M05-0001")


def test_a_second_shape_printed_on_two_sheets_is_accepted_too():
    pages = [_Page(i, ["D02J-00GEN00-M05-000%d" % i]) for i in range(1, 6)]
    pages += [_Page(25, ["D02J-31PGB0-M05-0001"]), _Page(26, ["D02J-31PGB0-M05-0002"])]
    pat = dl._drawing_no_pattern(dl._drawing_no_shapes(pages, REGION))
    assert re.match(pat, "D02J-31PGB0-M05-0001") and re.match(pat, "D02J-00GEN00-M05-0001")
    assert not re.match(pat, "1A5J-00MBA10-M05-001")          # 읽지 않은 모양은 안 받는다


def test_a_shape_seen_on_one_sheet_only_is_not_a_shape():
    pages = [_Page(i, ["D02J-00GEN00-M05-000%d" % i]) for i in range(1, 4)]
    pages += [_Page(32, ["1A5J-00MBA10-M05-001"])]
    pat = dl._drawing_no_pattern(dl._drawing_no_shapes(pages, REGION))
    assert not re.match(pat, "1A5J-00MBA10-M05-001")


def test_dates_and_plain_words_in_the_cell_do_not_become_a_shape():
    pages = [_Page(i, ["26.08.21", "REV", "D02J-00GEN00-M05-000%d" % i]) for i in range(1, 3)]
    shapes = dl._drawing_no_shapes(pages, REGION)
    assert set(shapes) == {"A4-A7-A3-D4"}


def test_nothing_in_the_cell_means_no_derivation():
    pages = [_Page(i, ["TITLE ONLY"]) for i in range(1, 3)]
    assert dl._drawing_no_pattern(dl._drawing_no_shapes(pages, REGION)) is None
