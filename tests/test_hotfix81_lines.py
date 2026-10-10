"""hotfix81 [D] — 줄 묶기는 버킷이 아니라 글자 높이로 · 범례 종이 배율을 신호선 길이에도.

두 버킷(`_notes_lines` 7pt · `_connector_labels` 5pt)은 roadmap §4 ④ 의 "아직 남아 있는" 자리였다 —
줄 간격이 버킷보다 촘촘한 문서(UAD)에서 서로 다른 줄을 섞고, 한 줄이 버킷 경계에 걸리면 둘로 갈랐다.
`pidcache.same_lines` 는 그 낱말 자신의 높이만 쓴다 (상수 0).
"""
from __future__ import annotations

import pathlib
import re
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

R = pymupdf.Rect


def _texts(lines):
    return [[t for _r, t in ln] for ln in lines]


def test_two_tight_lines_stay_two_lines_where_a_bucket_merged_them():
    import pidcache
    # 글자 높이 2.5pt · 줄 간격 3pt (UAD 꼴).  y0 98 과 101 은 5pt·7pt 버킷에서 같은 칸이다.
    words = [(R(10, 98, 20, 100.5), "A"), (R(25, 98, 35, 100.5), "B"), (R(10, 101, 20, 103.5), "C")]
    assert round(98 / 7) == round(101 / 7) and round(98 / 5) == round(101 / 5)
    assert _texts(pidcache.same_lines(words)) == [["A", "B"], ["C"]]


def test_one_line_straddling_a_bucket_boundary_stays_one_line():
    import pidcache
    words = [(R(30, 101.6, 40, 109.6), "Y"), (R(10, 101.4, 20, 109.4), "X")]
    assert round(101.4 / 7) != round(101.6 / 7)          # 옛 버킷은 둘로 갈랐다
    assert _texts(pidcache.same_lines(words)) == [["X", "Y"]]   # x 순으로


def test_lines_come_back_in_reading_order_and_the_first_word_sets_the_line():
    import pidcache
    # 중심이 조금씩 흘러가는 낱말들 — 기준은 줄의 첫 낱말이라 옆 줄을 삼키지 않는다
    words = [(R(0, 100, 5, 110), "a"), (R(10, 102, 15, 112), "b"), (R(20, 104, 25, 114), "c"),
             (R(30, 106, 35, 116), "d"), (R(0, 120, 5, 130), "e")]
    got = _texts(pidcache.same_lines(words))
    assert got[0][0] == "a" and got[-1] == ["e"]
    assert all(len(ln) >= 1 for ln in got)


def test_the_two_buckets_are_gone_and_both_readers_use_the_one_helper():
    ds = (ROOT / "app/engine/detect_symbols.py").read_text(encoding="utf-8")
    pg = (ROOT / "app/engine/pipe_graph.py").read_text(encoding="utf-8")
    assert "round(r.y0 / 7)" not in ds
    assert "pidcache.same_lines(" in ds
    # ⚠ `_connector_labels` 의 5pt 버킷은 **남겨 두었다** — 세로만 고치면 멀리 떨어진 낱말이 가로로
    # 섞이는 다른 결함이 드러나고(AL NOUF1 커넥터 218 → 194 · 잃은 63 · 얻은 39), 낱말 간격/글자
    # 높이 분포에 빈 띠가 없어(0.25h 최빈 뒤 연속) 가로 문턱을 세울 근거가 없다.  roadmap §4 ④.
    assert "round(r.y0 / 5)" in pg
    helper = (ROOT / "app/engine/pidcache.py").read_text(encoding="utf-8")
    body = helper[helper.index("def same_lines"):helper.index("def tokens")]
    body = re.sub(r'"""[\s\S]*?"""', "", body)          # 설명글의 보기 숫자는 뺀다
    # 상수 0 — 절대 pt 가 없다 (0.5 는 "절반" 이라는 비율이다)
    assert not re.search(r"\b[1-9]\d*\.\d+\b", body.replace("0.5", "")), "절대 pt 가 들어갔다"


def test_line_styles_are_scaled_only_when_the_legend_is_on_a_different_paper():
    from app import pipeline
    from app.engine import legend_rules

    class _Pg:
        def __init__(self, w, h, no, words=()):
            self.width, self.height, self.page_no = w, h, no
            self.words = list(words)
            self.analysis_scope = True
    style = legend_rules.Derived(values={"dash_len": 7.2, "dash_gap": 3.6, "min_run": 16.97, "join_slack": 1.5},
                                 source="LEGEND", note="legend p2", evidence={"page_no": 2})
    # 같은 종이 — 객체 그대로 (곱하지도, note 를 적지도 않는다)
    same = pipeline._scale_line_styles(style, [_Pg(2384, 1684, 1), _Pg(2384, 1684, 2)])
    assert same is style
    # 폴백은 범례 길이가 아니다 — 곱하지 않는다
    fb = legend_rules.Derived(values={"min_run": 16.97}, source="CONFIG_FALLBACK", note="x")
    assert pipeline._scale_line_styles(fb, [_Pg(1191, 842, 1), _Pg(2384, 1684, 2)]) is fb
    # 범례(A3) ↔ 본문(A1) — 범례 장은 머리말로 찾는다.  `legend_paper_scale` 를 직접 흉내 내
    # 네 값이 같은 배율로 곱해지는지만 본다 (범례 장 탐색은 legend_rules 의 시험 몫).
    lr = pipeline.legend_rules                                # pipeline 이 실제로 부르는 모듈 객체
    orig = lr.legend_paper_scale
    try:
        lr.legend_paper_scale = lambda pages: (2.0, "A3 legend on A1 sheets")
        out = pipeline._scale_line_styles(style, [_Pg(2384, 1684, 1)])
    finally:
        lr.legend_paper_scale = orig
    assert out is not style
    assert out.values == {"dash_len": 14.4, "dash_gap": 7.2, "min_run": 33.94, "join_slack": 3.0}
    assert out.evidence["legend_scale"] == 2.0 and "x 2.0" in out.note
    assert style.values["min_run"] == 16.97                   # 원본은 그대로


def test_scaling_happens_right_after_the_legend_is_read_and_before_the_profile_is_captured():
    src = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    i = src.index("m_style = _scale_line_styles(pipe_graph.derive_line_styles(pages, CFG), pages)")
    j = src.index("measured_profile = legend_profile_store.capture(")
    assert i < j
