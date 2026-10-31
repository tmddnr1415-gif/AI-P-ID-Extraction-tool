"""hotfix38 (#39) — 한 가지의 전송기가 물리 계기, 표시기는 신호.

사용자: *"하나의 가지에서 PIT PI 가 있으면 PIT 가 물리적 계기이고 PI 는 시그널이니
PIT 를 식별해야 한다.  TIT TI, PDIT PDI 모두 마찬가지다."*

hotfix31 은 "한 가지" 를 같은 태그로만 읽었다.  QFE 실측(`spike/readout_link_probe.py`):
태그 없이(p6 PI/PIT · TI/TIT) · 태그를 달리 찍고(p23 · p49 · p50) 두 버블을 짧은 선
하나로 잇는 짝 8, 같은 태그인데 `FT` 가 `FI` 를 포함하지 않아 안 접히던 짝 4 (p42).
AL NOUF1 · TC2 는 이어 그린 짝 0 — 2급 문서는 구조적으로 안 움직인다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import pipeline as P                       # noqa: E402
from app.engine import isa_table, pidcache          # noqa: E402

TABLE = isa_table.IsaTable(
    first={"P": ("PRESSURE",), "T": ("TEMPERATURE",), "F": ("FLOW",), "PD": ("PRESSURE", "DIFFERENTIAL")},
    succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",), "C": ("CONTROLLER",), "S": ("SWITCH",)},
    page_no=4, note="test")


def _row(key, anchor, tag="", page=6, rect=(100, 100, 168, 123)):
    return P.Row(key=key, tab=P.TAB_FIELD, page_no=page, drawing_no="D", type=anchor,
                 qty=1, rect=tuple(rect), tag_no=tag,
                 evidence={"anchor": anchor, "tag_no": {"value": tag}})


def test_a_drawn_link_folds_an_untagged_pi_into_the_pit_above_or_below():
    """QFE p6 — PI 가 PIT 위에 쌓여 짧은 선으로 이어져 있고 둘 다 태그가 없다."""
    pi = _row("pi", "PI", rect=(1605, 412, 1673, 435))
    pit = _row("pit", "PIT", rect=(1605, 451, 1673, 473))
    links = {6: [("pi", "pit", "V", 15.5, 0.82)]}
    facts, folded = P._fold_readouts([pi, pit], TABLE, links=links)
    assert folded == {"pi"}
    rec = pit.evidence["readout_folded"][0]
    assert rec["basis"] == "LINK" and "이어 그린 선" in rec["how"] and "15.5" in rec["how"]
    assert facts["folded"][0]["basis"] == "LINK" and facts["folded"][0]["kept"] == "PIT"
    assert "표시기는 신호" in pit.remark
    assert "gauge" not in pi.evidence


def test_a_drawn_link_folds_even_when_the_tags_differ():
    """QFE p23 — `TI 00QUP02CL002` 위 `TIT 00QUP02CT002` (도면이 태그를 달리 찍었다)."""
    ti = _row("ti", "TI", "00QUP02CL002", page=23, rect=(294, 1110, 369, 1136))
    tit = _row("tit", "TIT", "00QUP02CT002", page=23, rect=(295, 1150, 368, 1176))
    _f, folded = P._fold_readouts([ti, tit], TABLE, links={23: [("tit", "ti", "V", 13.8, 0.73)]})
    assert folded == {"ti"}
    assert tit.evidence["readout_folded"][0]["tag_no"] == "00QUP02CL002"


def test_pdit_pdi_is_the_same_rule():
    pdi = _row("a", "PDI", rect=(100, 100, 168, 123))
    pdit = _row("b", "PDIT", rect=(100, 140, 168, 163))
    _f, folded = P._fold_readouts([pdi, pdit], TABLE, links={6: [("a", "b", "V", 17.0, 0.9)]})
    assert folded == {"a"}


def test_a_transmitter_without_the_i_letter_still_wins_on_the_same_tag():
    """QFE p42 — `FI` ↔ `FT` 같은 태그.  `FT` 는 `FI` 를 포함하지 않아 hotfix31 로는
    안 접혔다.  이기는 쪽은 그 표가 TRANSMITTER 로 읽는 글자를 가진 기능이다."""
    fi = _row("fi", "FI", "31GKC71CF002", page=42)
    ft = _row("ft", "FT", "31GKC71CF002", page=42, rect=(200, 100, 268, 123))
    _f, folded = P._fold_readouts([fi, ft], TABLE)
    assert folded == {"fi"}
    assert ft.evidence["readout_folded"][0]["basis"] == "TAG"


def test_without_a_link_or_a_shared_tag_nothing_folds_and_a_lone_pi_is_a_gauge():
    pi = _row("pi", "PI", "11LBB50CP901")
    pit = _row("pit", "PIT", "11LBB50CP001", rect=(100, 140, 168, 163))
    facts, folded = P._fold_readouts([pi, pit], TABLE, links={})
    assert folded == set()
    assert pi.evidence["gauge"]["display"] == "PG"
    assert facts["gauges"] == 1


def test_a_link_to_a_switch_is_not_a_transmitter_and_does_not_fold():
    """이어져 있어도 상대가 전송기가 아니면(PS) 접지 않는다 — 글자 뜻은 표가 정한다."""
    pi = _row("pi", "PI")
    ps = _row("ps", "PS", rect=(100, 140, 168, 163))
    _f, folded = P._fold_readouts([pi, ps], TABLE, links={6: [("pi", "ps", "V", 17.0, 0.9)]})
    assert folded == set()


def _pdf_with(tmp_path, rects, line=None, dashed=False):
    doc = pymupdf.open(); page = doc.new_page(width=800, height=600)
    sh = page.new_shape()
    for r in rects:
        sh.draw_rect(pymupdf.Rect(*r))
    if line:
        sh.draw_line(pymupdf.Point(*line[0]), pymupdf.Point(*line[1]))
    sh.finish(color=(0, 0, 0), width=0.5, dashes="[3 3] 0" if dashed else None)
    sh.commit()
    path = tmp_path / "t.pdf"; doc.save(path); doc.close()
    return pidcache.load_pages(str(path))[1]


def test_bubble_links_read_one_drawn_segment_between_stacked_bubbles(tmp_path):
    """틈 상한은 버블 자신의 긴변이고, 띠 안의 축 방향 잉크가 틈의 절반 이상이어야 한다."""
    a, b = (100, 100, 168, 123), (100, 140, 168, 163)
    pages = _pdf_with(tmp_path, [a, b], line=((134, 123), (134, 140)))
    rows = [_row("pi", "PI", page=1, rect=a), _row("pit", "PIT", page=1, rect=b)]
    links = P._bubble_links(rows, pages)
    assert 1 in links and links[1][0][:2] == ("pi", "pit") and links[1][0][2] == "V"
    assert links[1][0][3] == 17.0 and links[1][0][4] >= 0.99


def test_bubble_links_accept_a_dashed_signal_line(tmp_path):
    a, b = (100, 100, 168, 123), (100, 140, 168, 163)
    pages = _pdf_with(tmp_path, [a, b], line=((134, 123), (134, 140)), dashed=True)
    rows = [_row("pi", "PI", page=1, rect=a), _row("pit", "PIT", page=1, rect=b)]
    assert 1 in P._bubble_links(rows, pages)


def test_bubble_links_need_ink_and_a_gap_no_wider_than_the_bubble(tmp_path):
    a, b = (100, 100, 168, 123), (100, 140, 168, 163)
    pages = _pdf_with(tmp_path, [a, b])                       # 선 없음
    rows = [_row("pi", "PI", page=1, rect=a), _row("pit", "PIT", page=1, rect=b)]
    assert P._bubble_links(rows, pages) == {}
    far = (100, 300, 168, 323)                                 # 틈 177pt > 긴변 68
    pages = _pdf_with(tmp_path, [a, far], line=((134, 123), (134, 300)))
    rows = [_row("pi", "PI", page=1, rect=a), _row("pit", "PIT", page=1, rect=far)]
    assert P._bubble_links(rows, pages) == {}


def test_the_link_is_read_in_the_pipeline_after_the_tags_and_nowhere_else():
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert src.count("_bubble_links(rows, pages)") == 1
    assert src.index("_attach_tags(rows, pages") < src.index("_bubble_links(rows, pages)")
    # 순회 금지 — 선분 하나의 유무만 본다: 찾은 끝에서 다시 선을 찾는 코드가 없다
    body = src[src.index("def _bubble_links"):src.index("def _fold_readouts")]
    assert "while" not in body and "deque" not in body and "visited" not in body
