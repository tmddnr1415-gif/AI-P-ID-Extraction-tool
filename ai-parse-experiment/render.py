"""PDF 장 → AI 에게 줄 이미지 + 결정적 텍스트 레이어.

pid-instrument-tool/web/pdfscan.js 와 **같은 일**을 파이썬으로 한다.
그쪽 코드를 고치지 않고 규칙만 옮겨 왔다 (토큰 목록 · NOTES 찾는 법 · 타이틀블록 위치).

텍스트 레이어가 중요한 이유: PDF 에서 결정적으로 나오므로
**같은 입력이면 같은 출력**이다. 좌표 정확도(D-3)의 정답지가 이것이고,
AI 판독의 기준선도 이것이다.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf as fitz  # PyMuPDF (신 API 이름. fitz 별칭으로 든다)

# 모델이 이미지를 **장변 1568px 로 줄여** 본다. 그보다 크게 그려 보내면
# 정확도는 그대로인데 업로드 바이트만 늘고, 토큰도 줄여진 크기로 계산된다.
# 그래서 '해상도를 올린다' 가 곧 '더 잘 읽힌다' 가 아니다 —
# 실효 해상도를 정하는 것은 DPI 가 아니라 **분할 수**다. effective_dpi() 참조.
MODEL_EDGE = 1568
MAX_EDGE = MODEL_EDGE  # 렌더 상한. pdfscan.js 는 2576 을 쓰지만 그만큼은 버려진다
DRAWING_NO = re.compile(r"D00P-[0-9A-Z]{5,9}-M\d{2}-\d{4}")

# 텍스트 레이어에서 계기로 볼 문자. 긴 것부터 본다. (pdfscan.js TOKENS 와 동일)
TOKENS = [
    "LSHH", "LSLL", "PDIT", "PDSH", "LSH", "LSL", "PSH", "PSL", "TSH", "TSL",
    "PIT", "TIT", "LIT", "FIT", "AIT", "PDI", "PDT", "FQI",
    "PI", "TI", "LI", "FI", "AI", "PT", "TT", "LT", "FT", "AT",
    "PS", "TS", "LS", "FS", "ZS", "FE", "RO", "TE", "PE", "LE", "AE",
]
TOKEN_SET = set(TOKENS)

# 도면 글자 → 출력 TYPE. 전송기 계열을 표준 약어로 옮긴다.
TOKEN_TO_TYPE = {
    "PIT": "PIT", "PT": "PIT", "PE": "PIT",
    "TIT": "TIT", "TT": "TIT", "TE": "TIT",
    "LIT": "LIT", "LT": "LIT", "LE": "LIT",
    "FIT": "FIT", "FT": "FIT",
    "PDIT": "PDIT", "PDT": "PDIT", "PDI": "PDIT",
    "PI": "PI", "TI": "TI", "LI": "LI", "FI": "FIT",
    "LS": "LS", "LSH": "LS", "LSL": "LS", "LSHH": "LS", "LSLL": "LS",
    "FS": "FS", "PS": "FS", "TS": "FS", "PSH": "FS", "PSL": "FS",
    "TSH": "FS", "TSL": "FS", "PDSH": "FS",
    "FE": "FE", "RO": "RO",
}
# 계기 범위 밖 — 밸브 리밋스위치 계열과 분석기
NOT_FIELD = {"ZS", "AT", "AIT", "AI", "AE", "FQI"}


@dataclass
class PageScan:
    page: int
    drawing_no: str | None
    title: str | None
    notes: str
    candidates: list[dict]
    labels: list[dict]
    page_size_pt: tuple[float, float]
    is_legend: bool
    conflicts: list[str] = field(default_factory=list)


def _items(page: fitz.Page) -> list[dict]:
    """텍스트 조각을 0~1 정규화 좌표(원점 좌상단)와 함께 뽑는다.

    **낱말이 아니라 텍스트 런(span) 단위**로 든다. pdfscan.js 가 쓰는
    pdf.js `getTextContent().items` 와 같은 알갱이다. 낱말로 쪼개면
    'P&ID FOR HP STEAM SYSTEM' 같은 제목과 'FROM HRSG#11 MAIN' 같은
    배관 라벨이 한 조각으로 남지 않아 제목도 라벨도 못 읽는다.
    """
    W, H = page.rect.width, page.rect.height
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                s = span["text"].strip()
                if not s:
                    continue
                x0, y0, x1, y1 = span["bbox"]
                out.append(
                    {
                        "str": s,
                        "x": round(x0 / W, 4),
                        "y": round(y0 / H, 4),
                        "rect": [round(x0 / W, 4), round(y0 / H, 4),
                                 round(x1 / W, 4), round(y1 / H, 4)],
                    }
                )
    return out


def _join_region(items, pred) -> str:
    sel = [i for i in items if pred(i)]
    sel.sort(key=lambda i: (i["y"], i["x"]))
    return "\n".join(i["str"] for i in sel)


def _find_notes(items) -> str:
    """NOTES 블록. 좌표를 고정하지 않고 'GENERAL NOTES' / 'NOTES :' 글자를 찾아 따라간다.

    이 블록이 판독의 절반이다 — 별표 뜻과 승수가 여기 있다.
    """
    anchors = [i for i in items if re.fullmatch(r"(GENERAL\s+)?NOTES?\s*:?", i["str"], re.I)]
    if anchors:
        x0 = min(a["x"] for a in anchors) - 0.03
        y0 = min(a["y"] for a in anchors) - 0.01
        block = _join_region(items, lambda i: i["x"] >= x0 and y0 <= i["y"] < y0 + 0.55)
        if len(block) > 40:
            return block[:4000]
    return _join_region(items, lambda i: i["x"] > 0.72 and i["y"] < 0.60)[:4000]


EQUIP_HINT = re.compile(
    r"\b(COOLER|COOLERS|PUMP|TANK|DRUM|SYSTEM|TURBINE|BOILER|HEATER|ECONOMIZER"
    r"|VESSEL|FAN|COMPRESSOR|FILTER|HEADER)\b", re.I)
SECTION = re.compile(r"\b(SUPPLY|RETURN|DRAIN|DISCHARGE|SUCTION|INLET|OUTLET|BYPASS|VENT)\b", re.I)
LABEL_NOISE = re.compile(
    r"SAMSUNG|PROJECT|DRAWING|SHEET|SCALE|PROPERTY|INTERNAL USE|AL NOUF|EMPLOYER|TENDERER"
    r"|PREPARED|REFER TO|DENOTES|CONFIGURATION|THIS DRAWING|MARKED ITEM|NOTES|SHALL BE|IDENTICAL", re.I)


def _sheet_labels(items) -> list[dict]:
    """도면 안쪽 설비명과 배관 행선지 — DESCRIPTION 을 쓸 때 볼 근거."""
    out = []
    for i in items:
        t = i["str"]
        if i["x"] > 0.78 or (i["x"] > 0.55 and i["y"] > 0.78):
            continue  # 노트·타이틀블록
        if len(t) < 6 or DRAWING_NO.search(t) or LABEL_NOISE.search(t):
            continue
        if not re.search(r"[A-Z]{3,}", t):
            continue
        is_line = bool(re.match(r"^(TO|FROM)\b", t, re.I)) or bool(SECTION.search(t))
        is_equip = not re.match(r"^(TO|FROM)\b", t, re.I) and bool(EQUIP_HINT.search(t))
        if not is_line and not is_equip:
            continue
        out.append({"t": t, "x": i["x"], "y": i["y"], "kind": "equip" if is_equip else "line"})
    return out[:80]


def scan_page(doc: fitz.Document, page_no: int) -> PageScan:
    """한 장의 결정적 정보. 이미지는 만들지 않는다(무겁다)."""
    page = doc[page_no - 1]
    items = _items(page)

    tb = _join_region(items, lambda i: i["x"] > 0.55 and i["y"] > 0.78)
    nums = DRAWING_NO.findall(tb)
    title = None
    for line in tb.split("\n"):
        if "P&ID FOR" in line.upper():
            title = re.sub(r"\s+", " ", line).strip()
            break
    if not title:
        k = tb.upper().find("P&ID FOR")
        if k >= 0:
            title = re.sub(r"\s+", " ", tb[k:k + 90]).strip()

    cands = []
    for i in items:
        tok = re.sub(r"[.,;:()\[\]]", "", i["str"])
        if tok in TOKEN_SET:
            cands.append({"token": tok, "x": i["x"], "y": i["y"], "rect": i["rect"]})
    cands.sort(key=lambda c: (c["y"], c["x"]))

    drawing_no = nums[-1] if nums else None
    return PageScan(
        page=page_no,
        drawing_no=drawing_no,
        title=title,
        notes=_find_notes(items),
        candidates=cands,
        labels=_sheet_labels(items),
        page_size_pt=(round(page.rect.width, 1), round(page.rect.height, 1)),
        is_legend=bool(
            (drawing_no and "GEN00" in drawing_no)
            or (title and re.search(r"SYMBOL|LEGEND|DRAWING LIST", title, re.I))
        ),
    )


def render(doc: fitz.Document, page_no: int, dpi: int, region=(0, 0, 1, 1)) -> tuple[bytes, tuple[int, int]]:
    """장(또는 그 일부)을 PNG 로 그린다. 장변이 MAX_EDGE 를 넘지 않게 눌러 준다.

    전체를 크게 그린 뒤 자르지 않는다 — A1 을 300DPI 로 그리면 캔버스가 못 버틴다.
    타일은 영역을 직접 그린다.
    """
    page = doc[page_no - 1]
    x0, y0, x1, y1 = region
    r = page.rect
    clip = fitz.Rect(
        r.x0 + r.width * x0, r.y0 + r.height * y0,
        r.x0 + r.width * x1, r.y0 + r.height * y1,
    )
    scale = dpi / 72.0
    longest_pt = max(clip.width, clip.height)
    if longest_pt * scale > MAX_EDGE:
        # 픽스맵은 정수 픽셀로 올림되므로 딱 MAX_EDGE 로 맞추면 1px 넘어간다.
        # 올림 여유를 빼고 잡은 뒤, 그래도 넘으면 한 번 더 줄인다.
        scale = (MAX_EDGE - 2) / longest_pt
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    if max(pix.width, pix.height) > MAX_EDGE:
        scale *= MAX_EDGE / max(pix.width, pix.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
    return pix.tobytes("png"), (pix.width, pix.height)


def tiles(cols: int, rows: int, overlap: float = 0.08) -> list[dict]:
    """겹침 타일 영역 목록. 좌상 → 우하 (행 우선). 이 순서가 곧 출력 정렬 순서다.

    1x1 은 타일을 만들지 않는다 — 전체 장 이미지와 같은 그림이라 값 없이 토큰만 문다.
    """
    if cols <= 1 and rows <= 1:
        return []
    out = []
    for j in range(rows):
        for i in range(cols):
            out.append({
                "row": j, "col": i,
                "region": (
                    max(0.0, i / cols - overlap / cols),
                    max(0.0, j / rows - overlap / rows),
                    min(1.0, (i + 1) / cols + overlap / cols),
                    min(1.0, (j + 1) / rows + overlap / rows),
                ),
            })
    return out


def effective_dpi(page_size_pt, cols: int, rows: int, overlap: float = 0.08) -> float:
    """분할 수가 실효 해상도를 정한다. DPI 인자가 아니라.

    타일 하나가 장변 MODEL_EDGE 로 줄여지므로, 그 타일이 덮는 도면 영역이
    곧 실효 해상도다. 분할을 늘리면 올라가고, DPI 만 올리면 안 올라간다.
    """
    w, h = page_size_pt
    tile_long_pt = max(w * (1 / cols + 2 * overlap / cols),
                       h * (1 / rows + 2 * overlap / rows))
    return round(MODEL_EDGE / tile_long_pt * 72.0, 1)


def image_tokens(px: tuple[int, int]) -> int:
    """이미지 한 장의 토큰 — (가로×세로)/750. 장변은 이미 MODEL_EDGE 이하다."""
    w, h = px
    return (w * h) // 750


def find_legend_pages(doc: fitz.Document, limit: int = 6) -> list[int]:
    """범례 장을 찾는다. 없으면 빈 목록 — 지어내지 않는다."""
    found = []
    for n in range(1, min(doc.page_count, 12) + 1):
        s = scan_page(doc, n)
        if s.is_legend:
            found.append(n)
        if len(found) >= limit:
            break
    return found
