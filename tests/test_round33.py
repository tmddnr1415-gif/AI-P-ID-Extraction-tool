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
    assert len(re.findall(r'evidence\["tag_no"\]', src)) == 1
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
