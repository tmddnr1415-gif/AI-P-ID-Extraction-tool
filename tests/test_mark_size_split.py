"""47회차 [B] — 같은 크기가 반올림 칸에서 갈려 "두 번 그려졌다" 를 못 세던 것.

46회차 [E] ㉣ 가 TC2 p9 에서 찾은 증상: TIT 세 버블 **모두** 위에 `*` 가 있는데
가운데 하나만 `SCT` 로 나간다.  행 수도 지문도 정상으로 보이므로 **도면을 눈으로
세지 않으면 드러나지 않는다.**

원인은 검출이 아니라 **자**였다 — `star_marks` 는 크기를 배울 때 `round(...,1)`
칸(눈금 0.05pt)을, `find_marks` 는 맞출 때 `MARK_SIZE_TOL`(0.6pt)을 썼다.
한 물리 크기 2.88 이 네 칸으로 갈리면 1표짜리 칸이 생기고 그 별표만 빠진다.
"""
import collections

from app.engine import detect_symbols as ds


def test_the_learner_and_the_matcher_use_the_same_ruler():
    """★ 게이트 — 두 자가 갈리면 같은 결함이 다시 난다."""
    src = (ds.__file__ and open(ds.__file__).read()) or ""
    assert "MARK_SIZE_TOL" in src
    # 맞추는 곳도 배우는 곳도 리터럴 0.6 을 다시 적지 않는다
    assert "<= 0.6" not in src, "허용치를 다시 적으면 두 자가 갈린다"


def test_one_size_split_across_rounding_buckets_still_counts_as_drawn_twice():
    """TC2 p9 실측 — 별표 11개가 네 칸으로 갈리고 (2.9,2.9) 이 1표였다."""
    seen = collections.Counter({(2.8, 2.9): 5, (2.8, 2.8): 2,
                                (2.9, 2.8): 3, (2.9, 2.9): 1})
    for key in seen:
        assert ds._drawn_twice(key, seen), key
    # 반올림 칸으로만 세던 옛 규칙은 이 칸을 버렸다 (회귀 증거)
    assert seen[(2.9, 2.9)] < 2


def test_a_size_drawn_only_once_on_the_page_is_still_rejected():
    """규칙 자체는 안 바꿨다 — 한 번뿐인 크기는 여전히 얼룩이다.

    UAD p5 실측: 그 장의 마크 자리 뭉치가 2.82x2.82 **하나뿐**이라 배울 수 없다.
    """
    assert not ds._drawn_twice((2.8, 2.8), collections.Counter({(2.8, 2.8): 1}))


def test_a_size_far_from_every_other_is_not_merged_in():
    """이웃까지 세되 **맞추기 허용치 안**만 센다 — 아무 크기나 합치지 않는다."""
    seen = collections.Counter({(2.8, 2.8): 5, (7.8, 7.8): 1})
    assert ds._drawn_twice((2.8, 2.8), seen)
    assert not ds._drawn_twice((7.8, 7.8), seen)     # 5.0pt 떨어져 있다
    # 18회차 p35(범례 4.0 ↔ 도면 7.8)가 그 간격의 실제 사례다
    assert abs(7.8 - 2.8) > ds.MARK_SIZE_TOL


def test_the_tolerance_is_the_one_find_marks_already_used():
    """새 값이 아니다 — 이름만 줬다 (§9 ②)."""
    assert ds.MARK_SIZE_TOL == 0.6
