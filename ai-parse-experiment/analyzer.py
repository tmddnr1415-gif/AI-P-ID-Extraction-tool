"""AI 분석기 — PDF 장 하나 → 기존 스키마의 행 목록.

이 실험이 바꾸는 것은 **읽는 부분 하나**다. 화면·Excel·행 구조는 기존 것을 그대로 쓴다.

호출 하나에 주는 것:
    system   방법론 문서 전문 + 출력 칸 정의 + 허용 TYPE/TYPICAL/SYSTEM  (캐시 대상)
    user     범례 장 이미지 + 그 장 전체 이미지 + 확대 타일 + 텍스트 레이어 후보 + NOTES

출력은 JSON 스키마로 강제한다. 자유 서술을 받지 않는다.
"""

from __future__ import annotations

import base64
import json
import os
import random
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import render
import schema as schema_mod

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
METHODOLOGY = Path(__file__).resolve().parent / "methodology" / "pid_reading.md"


@dataclass
class Call:
    """호출 한 번의 결과와 값. 비용(D-4)은 이 기록에서만 나온다."""
    page: int
    ok: bool
    data: dict | None
    seconds: float
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    attempts: int = 1
    error: str = ""
    image_px: list[tuple[int, int]] = field(default_factory=list)

    @property
    def image_tokens_est(self) -> int:
        """이미지 토큰 어림 — 장당 (가로×세로)/750. 본 값이 없을 때만 쓴다."""
        return sum(render.image_tokens(px) for px in self.image_px)


# ── 프롬프트 ─────────────────────────────────────────────
def system_prompt(spec: schema_mod.Spec, methodology: str) -> str:
    L = [
        "당신은 P&ID 도면에서 Field Instrument 목록을 뽑아 표준 Instrument List 로 옮기는 계장 엔지니어입니다.",
        "아래 방법론 문서는 이 도면 계열을 여러 회차에 걸쳐 판독하며 밝혀낸 규율입니다. 그대로 따르세요.",
        "",
        "=" * 70, "# 방법론", "=" * 70,
        methodology.strip(),
        "",
        "=" * 70, "# 출력 대상 칸", "=" * 70,
    ]
    for k in spec.drawing_keys:
        L.append(f"- {k} ({spec.label(k)}): {schema_mod.COL_HINT.get(k, '')}")
    L.append("- rect: 심볼을 감싸는 정규화 상자 [x0,y0,x1,y1]. 모르면 null")
    L.append("- source_tokens: 이 행의 근거가 된 도면상 글자와 위치")
    L.append("- confidence: high / medium / low")

    L += ["", f"허용 TYPE: {', '.join(spec.instrument_types)}", "", "TYPE 별 허용 INST. TYPICAL TYPE:"]
    for t, xs in spec.type_to_typical_types.items():
        desc = []
        for x in xs:
            e = spec.typicals.get(x, {})
            desc.append(f"{x}({e.get('element_type', '?')}/{e.get('mounting_type', '?')})")
        L.append(f"  {t}: {', '.join(desc)}")
    L += ["", f"허용 SYSTEM(계통명): {', '.join(spec.systems)}"]
    return "\n".join(L)


def _img(png: bytes) -> dict:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png",
                   "data": base64.b64encode(png).decode("ascii")},
    }


def user_content(scan: render.PageScan, images: dict, legend: list[dict]) -> list[dict]:
    c: list[dict] = []
    if legend:
        c.append({"type": "text", "text": "## 범례 장 (먼저 읽는다 — 심볼이 무엇인지)"})
        for lg in legend:
            c.append(_img(lg["png"]))
    c.append({
        "type": "text",
        "text": (f"# 판독 대상 도면\n- 도면번호: {scan.drawing_no}\n"
                 f"- 도면명: {scan.title}\n- PDF 페이지: {scan.page}\n"
                 f"- 장 크기: {scan.page_size_pt[0]} × {scan.page_size_pt[1]} pt"),
    })
    c.append({"type": "text", "text": "## 전체 도면"})
    c.append(_img(images["full"]["png"]))
    for t in images["tiles"]:
        r = t["region"]
        c.append({"type": "text", "text": (
            f"## 확대 타일 r{t['row']}c{t['col']} "
            f"(도면 내 영역 x {r[0]:.3f}~{r[2]:.3f}, y {r[1]:.3f}~{r[3]:.3f})")})
        c.append(_img(t["png"]))

    lines = [f"{c_['token']} @ (x={c_['x']}, y={c_['y']})" for c_ in scan.candidates]
    c.append({"type": "text", "text": (
        f"## 텍스트 레이어 계기 문자 후보 ({len(scan.candidates)}건, 좌표는 도면 대비 0~1 정규화, 위→아래 순)\n"
        + ("\n".join(lines) if lines else "(없음 — 이미지에서만 판독하세요)"))})
    if scan.labels:
        lab = "\n".join(f"[{l['kind']}] {l['t']} @ (x={l['x']}, y={l['y']})" for l in scan.labels)
        c.append({"type": "text", "text": f"## 도면 안쪽 라벨 (설비명·배관 행선지)\n{lab}"})
    if scan.notes:
        c.append({"type": "text", "text": f"## 도면 GENERAL NOTES / NOTES\n{scan.notes}"})
    c.append({"type": "text", "text": (
        "이 도면의 Field Instrument 목록을 만드세요. "
        "제외한 후보는 반드시 excluded 에 이유를 남기고, "
        "못 읽은 것은 비운 채 review_findings 에 남기세요. 지어내지 마세요.")})
    return c


# ── 이미지 준비 ──────────────────────────────────────────
def prepare_images(doc, page_no: int, dpi: int, cols: int, rows: int, overlap: float = 0.08) -> dict:
    full_png, full_px = render.render(doc, page_no, dpi)
    out = {"full": {"png": full_png, "px": full_px}, "tiles": []}
    for t in render.tiles(cols, rows, overlap):
        png, px = render.render(doc, page_no, dpi, t["region"])
        out["tiles"].append({**t, "png": png, "px": px})
    return out


def all_px(images: dict, legend: list[dict]) -> list[tuple[int, int]]:
    return ([images["full"]["px"]] + [t["px"] for t in images["tiles"]]
            + [lg["px"] for lg in legend])


# ── 호출 ────────────────────────────────────────────────
def _post(body: dict, api_key: str, timeout: int) -> dict:
    req = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"content-type": "application/json", "x-api-key": api_key,
                 "anthropic-version": API_VERSION},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def analyze_page(
    doc, scan: render.PageScan, spec: schema_mod.Spec, json_schema: dict,
    *, api_key: str | None = None, model: str = DEFAULT_MODEL,
    dpi: int = 200, cols: int = 3, rows: int = 2,
    legend: list[dict] | None = None, max_tokens: int = 8000,
    temperature: float = 0.0, retries: int = 3, timeout: int = 300,
    methodology: str | None = None, stub=None,
) -> Call:
    """장 하나를 판독한다. `stub` 을 주면 API 없이 그 함수의 반환을 쓴다(배관 시험용)."""
    legend = legend or []
    t0 = time.monotonic()
    images = prepare_images(doc, scan.page, dpi, cols, rows)
    px = all_px(images, legend)

    if stub is not None:
        data = stub(scan, spec)
        return Call(page=scan.page, ok=True, data=data, seconds=time.monotonic() - t0,
                    image_px=px)

    if not api_key:
        return Call(page=scan.page, ok=False, data=None, seconds=time.monotonic() - t0,
                    error="ANTHROPIC_API_KEY 가 없습니다. 실판독을 하려면 키가 필요합니다.",
                    image_px=px)

    md = methodology if methodology is not None else METHODOLOGY.read_text(encoding="utf-8")
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": [{"type": "text", "text": system_prompt(spec, md),
                    "cache_control": {"type": "ephemeral"}}],
        "output_config": {"format": {"type": "json_schema", "schema": json_schema}},
        "messages": [{"role": "user", "content": user_content(scan, images, legend)}],
    }

    last = ""
    for attempt in range(1, retries + 1):
        try:
            res = _post(body, api_key, timeout)
            if res.get("stop_reason") == "max_tokens":
                raise RuntimeError("최대 출력 토큰에 도달해 응답이 잘렸습니다. --max-tokens 를 올리세요.")
            text = "".join(b.get("text", "") for b in res.get("content", []) if b.get("type") == "text")
            data = json.loads(text)
            u = res.get("usage") or {}
            return Call(
                page=scan.page, ok=True, data=data, seconds=time.monotonic() - t0,
                input_tokens=u.get("input_tokens", 0), output_tokens=u.get("output_tokens", 0),
                cache_read_tokens=u.get("cache_read_input_tokens", 0),
                cache_write_tokens=u.get("cache_creation_input_tokens", 0),
                attempts=attempt, image_px=px)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                json.JSONDecodeError, RuntimeError) as e:
            if isinstance(e, urllib.error.HTTPError):
                last = f"HTTP {e.code} — {e.read().decode('utf-8', 'replace')[:300]}"
                if e.code in (400, 401, 403, 404):
                    break  # 재시도해도 같다
            else:
                last = f"{type(e).__name__}: {e}"
            if attempt < retries:
                time.sleep(min(2 ** attempt + random.random(), 30))

    return Call(page=scan.page, ok=False, data=None, seconds=time.monotonic() - t0,
                attempts=retries, error=last, image_px=px)


def rows_from(call: Call, spec: schema_mod.Spec) -> list[dict]:
    """AI 응답 → 기존 스키마의 행 목록. 스키마를 바꾸지 않는다."""
    if not call.ok or not call.data:
        return []
    return [schema_mod.normalize_row(r, spec, call.page)
            for r in (call.data.get("instruments") or [])]
