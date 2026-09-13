"""D-2 결정성 — 이 실험에서 가장 중요한 측정.

기존 도구의 규율은 '같은 입력 → 같은 지문' 이다. 회귀 시험이 그것으로 결함을 잡는다.
AI 는 같은 장을 두 번 읽으면 다른 답을 낼 수 있다. 그러면 회귀를 못 돌린다.

여기서 일치율이 낮으면 (a) 대체는 **불가능**하다. 정확도가 아무리 좋아도 그렇다.
그래서 정확도보다 먼저 이것을 잰다.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import compare


@dataclass
class Agreement:
    runs: int
    row_counts: list[int]
    identical_runs: bool          # 모든 회차가 완전히 같은가
    row_count_same: bool
    jaccard_mean: float           # 회차 쌍끼리 다중집합 자카드 평균
    stable_rows: int              # 모든 회차에 나온 행
    total_distinct: int
    field_agreement: dict         # 칸별 일치율
    unstable: list                # 회차마다 달라진 행

    def line(self) -> str:
        return (f"{self.runs}회 반복 · 행 수 {self.row_counts} · "
                f"완전 일치 {'예' if self.identical_runs else '아니오'} · "
                f"행 일치율 {self.jaccard_mean * 100:.1f}% "
                f"({self.stable_rows}/{self.total_distinct} 행이 전 회차 공통)")


# 회차끼리 견줄 칸. qty 와 remark(SCOPE 판정)가 흔들리면 Excel 값이 흔들린다.
FIELDS = ["system", "type", "qty", "description", "inst_typical_type", "remark"]


def _key(r: dict) -> tuple:
    return compare.row_key(r, with_desc=True)


def agreement(runs: list[list[dict]]) -> Agreement:
    """회차별 행 목록을 받아 일치율을 낸다."""
    counters = [Counter(_key(r) for r in rows) for rows in runs]
    counts = [len(rows) for rows in runs]

    # 회차 쌍끼리 다중집합 자카드
    pairs, total = [], 0.0
    for i in range(len(counters)):
        for j in range(i + 1, len(counters)):
            inter = sum((counters[i] & counters[j]).values())
            union = sum((counters[i] | counters[j]).values())
            pairs.append(inter / union if union else 1.0)
            total += pairs[-1]
    jac = total / len(pairs) if pairs else 1.0

    common = counters[0].copy()
    for c in counters[1:]:
        common &= c
    allk = counters[0].copy()
    for c in counters[1:]:
        allk |= c

    # 칸별 일치 — 전 회차 공통인 행만 두고, 그 행의 각 칸이 회차마다 같은지 본다
    field_hits = {f: [0, 0] for f in FIELDS}
    by_key: dict[tuple, list[dict]] = {}
    for rows in runs:
        seen: dict[tuple, int] = {}
        for r in rows:
            k = _key(r)
            seen[k] = seen.get(k, 0) + 1
            by_key.setdefault((k, seen[k]), []).append(r)
    for (_k, _n), group in by_key.items():
        if len(group) != len(runs):
            continue
        for f in FIELDS:
            vals = {str(g.get(f, "")) for g in group}
            field_hits[f][1] += 1
            if len(vals) == 1:
                field_hits[f][0] += 1

    unstable = [{"key": list(k), "counts": [c.get(k, 0) for c in counters]}
                for k in sorted(allk - common)]

    return Agreement(
        runs=len(runs), row_counts=counts,
        identical_runs=all(c == counters[0] for c in counters) and len(set(counts)) == 1,
        row_count_same=len(set(counts)) == 1,
        jaccard_mean=jac,
        stable_rows=sum(common.values()), total_distinct=sum(allk.values()),
        field_agreement={f: (h / n if n else 1.0) for f, (h, n) in field_hits.items()},
        unstable=unstable,
    )
