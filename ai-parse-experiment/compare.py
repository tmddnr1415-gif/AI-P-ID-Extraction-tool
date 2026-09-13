"""대조 — D-1 정답지 대조 · D-3 좌표 오차 · D-5 감사 수확.

행을 견주려면 같은 행을 같은 행으로 알아봐야 한다. 태그가 없는 입찰 도면이라
비교 키는 `P&ID No. + TYPE + DESCRIPTION` 이고, DESCRIPTION 은 표현이 흔들리므로
정규화한 뒤 **다중집합**으로 견준다 (정렬 순서는 서로 다를 수 있다).

정규화 규칙은 samples/test_set_v1/README.md 가 '먼저 합의해야 한다' 고 남긴 것이다.
여기서 정한 것을 그대로 적어 두니, 합의가 달라지면 이 함수만 고치면 된다.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

# 같은 것을 다르게 부르는 표기. 정답지와 판독 결과 양쪽에 똑같이 건다.
ALIASES = [
    (r"\bBOILER FEED\s*WATER PUMP\b", "BFP"),
    (r"\bCONDENSATE EXTRACTION PUMP\b", "CEP"),
    (r"\bCLOSED COOLING WATER\b", "CCW"),
    (r"\bDIFFERENTIAL PRESSURE\b", "DIFF PRESSURE"),
    (r"\bTEMP\b", "TEMPERATURE"),
    (r"\bPRESS\b", "PRESSURE"),
]


def norm_desc(s: str) -> str:
    """DESCRIPTION 을 견줄 수 있는 모양으로. 'UNIT #11' 과 'UNIT 11' 을 같게 본다."""
    t = (s or "").upper()
    t = t.replace("&", " AND ")
    t = re.sub(r"#\s*(\d)", r"#\1", t)          # '# 11' → '#11'
    t = re.sub(r"\bUNIT\s*#?(\d+)", r"UNIT #\1", t)
    for pat, rep in ALIASES:
        t = re.sub(pat, rep, t)
    t = re.sub(r"[^A-Z0-9#/ ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def row_key(r: dict, with_desc: bool = True) -> tuple:
    k = ((r.get("pid_no") or "").strip().upper(), (r.get("type") or "").strip().upper())
    return (*k, norm_desc(r.get("description", ""))) if with_desc else k


@dataclass
class Score:
    matched: int
    missed: int          # 정답지에 있는데 못 낸 것
    spurious: int        # 냈는데 정답지에 없는 것
    truth_total: int
    got_total: int
    missed_rows: list
    spurious_rows: list

    @property
    def recall(self) -> float:
        return self.matched / self.truth_total if self.truth_total else 0.0

    @property
    def precision(self) -> float:
        return self.matched / self.got_total if self.got_total else 0.0

    def line(self, label: str) -> str:
        return (f"{label}: 재현율 {self.recall * 100:.1f}% ({self.matched}/{self.truth_total}) · "
                f"정밀도 {self.precision * 100:.1f}% ({self.matched}/{self.got_total})")


def score(got: list[dict], truth: list[dict], with_desc: bool = True) -> Score:
    """다중집합 대조. 정렬 순서는 보지 않는다."""
    gc = Counter(row_key(r, with_desc) for r in got)
    tc = Counter(row_key(r, with_desc) for r in truth)
    matched = sum((gc & tc).values())
    miss_keys, spur_keys = tc - gc, gc - tc
    return Score(
        matched=matched,
        missed=sum(miss_keys.values()), spurious=sum(spur_keys.values()),
        truth_total=sum(tc.values()), got_total=sum(gc.values()),
        missed_rows=[{"key": list(k), "count": n} for k, n in sorted(miss_keys.items())],
        spurious_rows=[{"key": list(k), "count": n} for k, n in sorted(spur_keys.items())],
    )


# ── D-3 좌표 ────────────────────────────────────────────
def rect_errors(ai_rows: list[dict], anchors: list[dict], page_size_pt) -> dict:
    """AI 가 준 rect 와 텍스트 레이어 좌표의 차이.

    '기존 도구 rect' 라는 것은 없다 — 기존 행은 좌표를 갖지 않고 화면도 표다.
    대신 **PDF 텍스트 레이어 좌표**를 정답으로 쓴다. 그쪽이 결정적이라 더 믿을 만하다.
    각 AI rect 중심에서 가장 가까운 후보 토큰까지의 거리를 pt 로 잰다.
    """
    W, H = page_size_pt
    out = []
    for r in ai_rows:
        rect = r.get("rect")
        if not rect:
            out.append({"type": r.get("type"), "err_pt": None, "why": "AI 가 rect 를 null 로 두었습니다"})
            continue
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        best, bd = None, None
        for a in anchors:
            ax = (a["rect"][0] + a["rect"][2]) / 2
            ay = (a["rect"][1] + a["rect"][3]) / 2
            d = (((ax - cx) * W) ** 2 + ((ay - cy) * H) ** 2) ** 0.5
            if bd is None or d < bd:
                best, bd = a, d
        out.append({"type": r.get("type"), "err_pt": round(bd, 1) if bd is not None else None,
                    "nearest_token": best["token"] if best else None})
    vals = sorted(e["err_pt"] for e in out if e["err_pt"] is not None)
    stats = {"n": len(vals), "null_rect": sum(1 for e in out if e["err_pt"] is None)}
    if vals:
        stats |= {
            "median_pt": vals[len(vals) // 2],
            "p90_pt": vals[min(len(vals) - 1, int(len(vals) * 0.9))],
            "max_pt": vals[-1],
        }
    return {"per_row": out, "stats": stats}


# ── D-5 감사 수확 ────────────────────────────────────────
def audit(ai_rows: list[dict], rule_rows: list[dict], truth: list[dict] | None) -> dict:
    """AI 가 냈는데 규칙이 놓친 것 — 이것의 개수가 (b) 의 성적이다.

    정답지가 있으면 '정답지에도 있는 것' 만 진짜 수확으로 센다.
    정답지가 없으면 후보로만 남긴다 — 정답지 없이 수확을 세면 그냥 오탐을 세는 것이다.
    """
    with_desc = False   # 규칙 기준선은 DESCRIPTION 이 비어 있어 그 칸으로는 못 견준다
    ai_c = Counter(row_key(r, with_desc) for r in ai_rows)
    rule_c = Counter(row_key(r, with_desc) for r in rule_rows)
    truth_c = Counter(row_key(r, with_desc) for r in truth) if truth is not None else None

    ai_only = ai_c - rule_c
    rule_only = rule_c - ai_c

    def split(keys: Counter) -> tuple[list, list]:
        if truth_c is None:
            return [], [{"key": list(k), "count": n} for k, n in sorted(keys.items())]
        confirmed, unconfirmed = [], []
        for k, n in sorted(keys.items()):
            (confirmed if truth_c.get(k, 0) > 0 else unconfirmed).append(
                {"key": list(k), "count": n})
        return confirmed, unconfirmed

    ai_only_true, ai_only_unconfirmed = split(ai_only)
    rule_only_true, rule_only_unconfirmed = split(rule_only)

    both_missed = []
    if truth_c is not None:
        both_missed = [{"key": list(k), "count": n}
                       for k, n in sorted((truth_c - ai_c - rule_c).items())]

    return {
        "ai_found_rule_missed": ai_only_true,             # ★ (b) 의 성적
        "ai_only_unconfirmed": ai_only_unconfirmed,       # 정답지가 없거나 정답지에 없는 것
        "rule_found_ai_missed": rule_only_true,
        "rule_only_unconfirmed": rule_only_unconfirmed,
        "both_missed": both_missed,
        "has_truth": truth_c is not None,
        "harvest_count": len(ai_only_true) if truth_c is not None else None,
    }


def load_truth(path, pages: list[int] | None = None) -> list[dict]:
    """정답지 JSON → 행 목록. 어떤 모양이든 최소 pid_no·type·description 만 있으면 된다."""
    import json
    from pathlib import Path

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("rows") if isinstance(data, dict) else data
    if rows is None:
        raise ValueError("정답지에서 행 목록을 찾지 못했습니다 (최상위 배열이거나 'rows' 키여야 합니다).")
    out = []
    for r in rows:
        if pages and r.get("page") not in pages and r.get("_page") not in pages:
            continue
        out.append(r)
    return out
