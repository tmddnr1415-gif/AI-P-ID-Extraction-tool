"""D-4 비용·시간 — 장당 토큰 · 장당 초 · 전량 환산.

값은 두 갈래로 나온다.
  · **본 값**   API 가 돌려준 usage 와 실제 걸린 시간. 실판독을 했을 때만 있다.
  · **어림값**  이미지 기하로 계산한 토큰. API 없이도 나온다.

어림값은 이미지 토큰만 정확하다 (장변 1568px 로 줄여진 뒤 (가로×세로)/750).
출력 토큰과 글 토큰은 실판독을 해야 안다. 섞어 쓰지 않는다.
"""

from __future__ import annotations

import render

# 1M 토큰당 USD. 값이 바뀌면 여기만 고친다.
PRICING = {
    "claude-sonnet-5": {"in": 3.00, "out": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "claude-opus-5":   {"in": 15.00, "out": 75.00, "cache_write": 18.75, "cache_read": 1.50},
    "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00, "cache_write": 1.25, "cache_read": 0.10},
}


def price(model: str) -> dict:
    for k, v in PRICING.items():
        if model.startswith(k) or k.startswith(model):
            return v
    return PRICING["claude-sonnet-5"]


def call_cost(c, model: str) -> float:
    p = price(model)
    return (c.input_tokens * p["in"] + c.output_tokens * p["out"]
            + c.cache_write_tokens * p["cache_write"] + c.cache_read_tokens * p["cache_read"]) / 1e6


def image_token_estimate(page_size_pt, cols: int, rows: int, overlap: float = 0.08) -> dict:
    """API 없이 나오는 장당 이미지 토큰. 순수 기하라 정확하다."""
    W, H = page_size_pt
    edge = render.MODEL_EDGE

    def px(w_pt, h_pt):
        s = edge / max(w_pt, h_pt)
        return (max(1, round(w_pt * s)), max(1, round(h_pt * s)))

    imgs = [px(W, H)]  # 전체 1장
    for t in render.tiles(cols, rows, overlap):
        r = t["region"]
        imgs.append(px(W * (r[2] - r[0]), H * (r[3] - r[1])))
    return {
        "images": len(imgs),
        "image_tokens": sum(render.image_tokens(p) for p in imgs),
        "effective_dpi": render.effective_dpi(page_size_pt, cols, rows, overlap),
    }


def sweep(page_size_pt, grids=((1, 1), (2, 2), (3, 2), (3, 3), (4, 4), (5, 4))) -> list[dict]:
    """해상도 스윕 — 분할 수를 바꿔 가며 실효 해상도와 이미지 토큰을 본다.

    '최소 해상도' 를 고르는 자리다. 계기 버블 글자가 읽히는 가장 성긴 분할이 답이고,
    그 판정은 사람이 렌더를 눈으로 보고 한다. 이 표는 그 대가를 숫자로 붙여 준다.
    """
    out = []
    for cols, rows in grids:
        e = image_token_estimate(page_size_pt, cols, rows)
        out.append({"grid": f"{cols}x{rows}", "cols": cols, "rows": rows, **e})
    return out


def summarize(calls: list, model: str, pages_total: int) -> dict:
    ok = [c for c in calls if c.ok]
    measured = [c for c in ok if c.input_tokens]
    # 성공한 호출이 하나도 없어도 이미지 기하는 남아 있다. 그것만이라도 낸다.
    basis = ok or calls
    n = len(basis) or 1
    secs = sum(c.seconds for c in basis) / n
    body = {
        "pages_run": len(ok), "pages_failed": len(calls) - len(ok),
        "seconds_per_page": round(secs, 1),
        "measured": bool(measured),
    }
    if measured:
        m = len(measured)
        body |= {
            "input_tokens_per_page": round(sum(c.input_tokens for c in measured) / m),
            "output_tokens_per_page": round(sum(c.output_tokens for c in measured) / m),
            "cache_read_per_page": round(sum(c.cache_read_tokens for c in measured) / m),
            "cache_write_per_page": round(sum(c.cache_write_tokens for c in measured) / m),
            "usd_per_page": round(sum(call_cost(c, model) for c in measured) / m, 4),
        }
        body["usd_total_estimate"] = round(body["usd_per_page"] * pages_total, 2)
    else:
        est = round(sum(c.image_tokens_est for c in basis) / n)
        body |= {"image_tokens_per_page_estimate": est,
                 "note": "API usage 가 없어 이미지 토큰 어림값만 있습니다. 출력 토큰은 실판독을 해야 압니다."}
    body["seconds_total_estimate"] = round(secs * pages_total)
    return body
