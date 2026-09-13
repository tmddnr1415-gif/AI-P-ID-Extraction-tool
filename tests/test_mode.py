"""38회차 [B] — 입찰(bid) / 실행(epc) 선언.

선언은 프로젝트 장부에, 판정은 도면 실측에, 다른 것은 말한다.  방법은 하나 —
1급(태그) 경로를 켜고 끄는 것뿐이다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import revisions as R          # noqa: E402
from app import pipeline as P           # noqa: E402


# ---------------------------------------------------------------- 장부
def test_set_mode_records_author_and_time_and_clears_on_empty(tmp_path):
    R.create_project(tmp_path, "P1")
    meta = R.set_mode(tmp_path, "P1", "epc", "홍길동")
    assert meta["mode"]["value"] == "epc" and meta["mode"]["author"] == "홍길동"
    assert meta["mode"]["set_at"] > 0
    assert R.declared_mode(R.load_project(tmp_path, "P1")) == "epc"
    meta = R.set_mode(tmp_path, "P1", "", "홍길동")
    assert "mode" not in meta and R.declared_mode(meta) == ""


def test_set_mode_rejects_unknown_values(tmp_path):
    R.create_project(tmp_path, "P2")
    with pytest.raises(ValueError):
        R.set_mode(tmp_path, "P2", "tender", "x")
    with pytest.raises(KeyError):
        R.set_mode(tmp_path, "nope", "bid", "x")


# ---------------------------------------------------------------- 1급 켜고 끄기
class _Row:
    def __init__(self, page_no, rect):
        self.page_no, self.rect, self.tag_no, self.evidence = page_no, rect, "", {}


class _Page:
    def __init__(self, page_no, words):
        self.page_no, self.words = page_no, words


def _tagged_document():
    """두 장 · 네 검출 · 같은 모양(`D2L3D2L2D3`)의 코드가 두 장에 되풀이 → 실측 1급."""
    rows, pages = [], []
    for pno, codes in ((1, ("00GKB01CL001", "00GKB02CL002")),
                       (2, ("00GKB03CL003", "00GKB04CL004"))):
        words = []
        for i, code in enumerate(codes):
            rect = (10 + 100 * i, 10, 40 + 100 * i, 40)
            rows.append(_Row(pno, rect))
            words.append((pymupdf.Rect(rect), code))
        pages.append(_Page(pno, words))
    return rows, pages


def test_auto_mode_follows_the_measurement():
    rows, pages = _tagged_document()
    facts = P._attach_tags(rows, pages)
    assert facts["measured"] == "epc" and facts["effective"] == "epc"
    assert facts["declared"] == "" and facts["conflict"] == ""
    assert facts["tagged_rows"] == 4 and all(r.tag_no for r in rows)


def test_declared_bid_switches_the_first_tier_off_but_says_tags_were_seen():
    rows, pages = _tagged_document()
    facts = P._attach_tags(rows, pages, declared_mode="bid")
    assert facts["effective"] == "bid" and facts["conflict"] == "declared_bid_tags_found"
    assert facts["tags_available"] == 4 and facts["pages_tagged"] == [1, 2]
    assert facts["tagged_rows"] == 0 and not any(r.tag_no for r in rows)
    assert all("tag_no" not in r.evidence for r in rows)


def test_declared_epc_without_tags_falls_back_to_the_second_tier_and_says_so():
    rows = [_Row(1, (10, 10, 40, 40))]
    pages = [_Page(1, [(pymupdf.Rect(10, 10, 40, 40), "PI")])]
    facts = P._attach_tags(rows, pages, declared_mode="epc")
    assert facts["measured"] == "bid" and facts["effective"] == "epc"
    assert facts["conflict"] == "declared_epc_no_tags" and facts["tagged_rows"] == 0


def test_declared_epc_on_a_tagged_document_equals_auto():
    rows_a, pages_a = _tagged_document()
    rows_b, pages_b = _tagged_document()
    fa = P._attach_tags(rows_a, pages_a)
    fb = P._attach_tags(rows_b, pages_b, declared_mode="epc")
    assert [r.tag_no for r in rows_a] == [r.tag_no for r in rows_b]
    assert fa["tagged_rows"] == fb["tagged_rows"] and fb["conflict"] == ""


def test_the_only_switch_is_the_first_tier():
    """선언으로 판정 로직을 둘로 만들지 않는다 — `mode` 를 읽는 곳은 `_attach_tags` 하나."""
    src = (ROOT / "app" / "pipeline.py").read_text()
    start = src.index("def _analyse(")
    body = src[start:src.index("\ndef ", start + 1)]
    assert body.count("declared_mode=declared_mode") == 1, "선언이 _attach_tags 말고 다른 곳에 쓰인다"
    assert body.count("declared_mode") == 3                   # 시그니처 + 호출의 이름·값
    assert '"bid"' not in body and '"epc"' not in body
