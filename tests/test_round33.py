"""33회차 — 죽는 버그(태그 열쇠 충돌) · 색이 사실을 말하게.

두 결함 모두 32회차가 사람 눈과 합성 도면으로 찾았다.  여기서는 그것이
다시 생기지 않는 것을 코드 수준에서 못박는다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pymupdf

from app import pipeline
from app.engine import tags as tagsys

ROOT = Path(__file__).resolve().parent.parent


class _Page:
    def __init__(self, page_no, words):
        self.page_no, self.words = page_no, words


def _row(page_no, rect, **kw):
    r = pipeline.Row(key=f"k{page_no}-{rect[0]}", page_no=page_no, tab="MOV", drawing_no="",
                     rect=rect, **kw)
    return r


def test_tier1_tag_does_not_collide_with_valve_bubble_letter():
    """밸브 행의 `evidence["tag"]` 는 버블 글자(문자열)다.  1급 태그는 다른
    열쇠(`tag_no`)에 실리고, 둘이 한 행에 같이 있어도 죽지 않는다 (합성 ⑧b)."""
    rows = [_row(1, (0, 0, 10, 10), evidence={"tag": "MOV", "body": "GLOBE"}),
            _row(2, (0, 0, 10, 10), evidence={"tag": "", "body": "GATE"}),
            _row(1, (50, 50, 60, 60), evidence={})]
    words = {1: [(pymupdf.Rect(1, 1, 5, 5), "14LBA14CP039"),
                 (pymupdf.Rect(51, 51, 55, 55), "14LBA10CP001")],
             2: [(pymupdf.Rect(1, 1, 5, 5), "14LBA15CP040")]}
    pages = [_Page(1, words[1]), _Page(2, words[2])]
    facts = pipeline._attach_tags(rows, pages)
    assert facts["tier"] == 1 and facts["tagged_rows"] == 3
    assert rows[0].tag_no == "14LBA14CP039"
    assert rows[0].evidence["tag"] == "MOV"          # 버블 글자는 그대로
    assert rows[1].evidence["tag"] == ""
    assert rows[0].evidence["tag_no"]["value"] == "14LBA14CP039"
    assert rows[0].evidence["tag_no"]["shape"] == tagsys.shape("14LBA14CP039")
    # 표기 함수는 여전히 버블 글자를 읽는다 (10회차 `MOV(GLOBE)`)
    assert pipeline.type_display({"type": "GLOBE"}, rows[0].evidence) == "MOV(GLOBE)"


def test_evidence_tag_key_has_one_writer_per_meaning():
    """`evidence["tag"]` 를 쓰는 곳은 밸브 행 하나, `evidence["tag_no"]` 를 쓰는
    곳은 `_attach_tags` 하나다 — 열쇠 하나에 뜻 하나."""
    src = (ROOT / "app" / "pipeline.py").read_text()
    assert len(re.findall(r'"tag": b\.tag', src)) == 1
    assert len(re.findall(r'r\.evidence\["tag_no"\] = ', src)) == 1
    assert 'setdefault("tag"' not in src


def test_overlay_layer_scope_reads_scope_only():
    """오버레이 층의 `scope` 는 SCOPE 열만 읽는다 — 검토 사유가 덮지 않는다
    (32회차 [B]: SADARA 82/82 · UAD 149/149 가 한 색이었다).  검토는 항목의
    `needs_review` 에 따로 실린다."""
    src = (ROOT / "app" / "pipeline.py").read_text()
    assert "SCOPE_REVIEW" not in src
    js = (ROOT / "app" / "static" / "app.js").read_text()
    assert "REVIEW_MARK" in js and "revbadge" in js
    # 색 갈래는 셋뿐이고 검토는 그 밖의 표식이다
    block = js[js.index("const SCOPE = ["):js.index("];", js.index("const SCOPE = ["))]
    assert block.count('["') == 3


def test_release_ink_drops_the_last_page_index(monkeypatch):
    """분석이 끝나면 마지막 장의 잉크 인덱스를 놓는다 — `_INK_LAST` 가 쪽 객체를
    붙들면 그 쪽이 PyMuPDF 문서 전체를 붙든다 (33회차 [D] tracemalloc 실측)."""
    from app.engine import detect_symbols as ds

    class _PC:
        _ink_index = None
        def drawings(self):
            return []

    pc = _PC()
    monkeypatch.setattr(ds, "_ink_index", lambda pc, m, cell: {"grid": 1})
    ds._ink_cache(pc, None, 10.0)
    assert ds._INK_LAST == [pc] and pc._ink_index is not None
    ds.release_ink()
    assert ds._INK_LAST == [] and pc._ink_index is None
    src = (ROOT / "app" / "pipeline.py").read_text()
    # 46회차 — 장을 여는 입구가 둘이 됐다: 분석(`analyse` 의 finally)과
    # 마크업 제안(`_ProposeCleanup.close`).  **입구마다 반드시 놓는다**가
    # 33회차의 뜻이므로, 수가 아니라 **어디서 부르는지**를 못박는다.
    # ⚠ 글자로 세면 **문서 문자열에 적힌 설명**까지 세어진다 (46회차에 3이 나왔다).
    # 부르는 곳은 AST 로 센다.
    import ast as _ast
    tree = _ast.parse(src)
    calls = [n for n in _ast.walk(tree)
             if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Attribute)
             and n.func.attr == "release_ink"]
    assert len(calls) == 2
    guard = src.split("def analyse(")[1].split("\ndef ")[0]
    assert "ds.release_ink()" in guard and "finally:" in guard
    cleanup = src.split("class _ProposeCleanup:")[1].split("\ndef ")[0]
    assert "ds.release_ink()" in cleanup


# --------------------------------------------------------------------------
# 56회차 — 음영은 **인라인 스타일**로 칠한다 (CSS 가 표현 속성을 이긴다)
# --------------------------------------------------------------------------

def test_the_fill_is_an_inline_style_not_a_presentation_attribute():
    """★ 9차 [3] 의 "반투명 음영" 은 한 번도 칠해진 적이 없었다.

    `styles.css` 의 `rect.det` 이 `fill: transparent` 를 갖고 있고(상자 안쪽까지
    클릭이 통하게 하려고 둔 것), **CSS 규칙은 표현 속성을 언제나 이긴다.**
    그래서 `setAttribute("fill", …)` 은 화면에 닿지 않았다.  DXF 빗금이 한 줄도
    안 그려지는 것을 파다가 드러났다 (같은 패턴을 살아 있는 페이지에 직접
    그리면 멀쩡히 칠해진다).
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    js = (root / "app" / "static" / "app.js").read_text(encoding="utf-8")
    css = (root / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    assert "fill: transparent;" in css                 # 그 줄은 그대로 남는다
    assert "r.style.fill =" in js                      # 칠하는 곳은 인라인이다
    assert 'r.setAttribute("fill"' not in js           # 표현 속성으로 칠하지 않는다
