#!/usr/bin/env python3
"""P&ID PDF를 도면 단위 이미지로 변환하고 manifest.json을 만든다.

대형 도면(33"×23")을 통째로 모델 최대 해상도(2576px)에 밀어넣으면 계기 버블의
글자가 뭉개진다. 그래서 두 가지를 함께 만든다:

  1. 전체 도면 이미지 1장  — 배치와 맥락 파악용
  2. 겹침 타일 N장          — 작은 글자를 읽을 수 있는 실효 해상도 확보용

또한 PDF 텍스트 레이어에서 계기 문자(PIT, TIT, PT, ...)를 좌표와 함께 결정적으로
추출해 manifest에 넣는다. 이 후보 목록은 판독 단계에서 모델에게 함께 제공되어
"눈으로만 세다가 빠뜨리는" 오류를 크게 줄인다.

사용:
  python3 scripts/pdf_to_images.py inputs/D00P_PID_Total_20251125.pdf
  python3 scripts/pdf_to_images.py inputs/x.pdf --pages 6,20,38 --tiles 3x2
  python3 scripts/pdf_to_images.py inputs/x.pdf --drawings D00P-11LAB00-M05-0001
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
MAX_EDGE = 2576                      # 모델이 지원하는 이미지 최대 장변(px)
DRAWING_NO = re.compile(r"D00P-[0-9A-Z]{5,9}-M\d{2}-\d{4}")

# 텍스트 레이어에서 계기로 볼 문자. 긴 것부터 매칭한다.
DEFAULT_TOKENS = [
    "LSHH", "LSLL", "PDIT", "PDSH", "LSH", "LSL", "PSH", "PSL", "TSH", "TSL",
    "PIT", "TIT", "LIT", "FIT", "AIT", "PDI", "PDT", "FQI",
    "PI", "TI", "LI", "FI", "AI", "PT", "TT", "LT", "FT", "AT",
    "PS", "TS", "LS", "FS", "ZS", "FE", "RO", "TE", "PE", "LE", "AE",
]


def parse_tiles(spec: str) -> tuple[int, int]:
    m = re.fullmatch(r"(\d+)\s*[xX*]\s*(\d+)", spec.strip())
    if not m:
        raise argparse.ArgumentTypeError("타일 형식은 '3x2' 처럼 지정하세요")
    return int(m.group(1)), int(m.group(2))


def title_block(page: pymupdf.Page) -> tuple[str | None, str | None]:
    """우하단 타이틀블록에서 도면번호와 도면명을 읽는다."""
    r = page.rect
    clip = pymupdf.Rect(r.width * 0.55, r.height * 0.78, r.width, r.height)
    text = page.get_text("text", clip=clip)
    nums = DRAWING_NO.findall(text)
    title = None
    for line in text.splitlines():
        if "P&ID FOR" in line.upper():
            title = " ".join(line.split())
            break
    return (nums[-1] if nums else None), title


def norm_title(s: str) -> set[str]:
    """도면명을 비교 가능한 토큰 집합으로 정규화한다 ('&'→'AND', 번호/괄호 무시)."""
    s = (s or "").upper().replace("&", " AND ")
    tokens = re.findall(r"[A-Z]+", s)
    drop = {"P", "ID", "FOR", "AND", "OF", "THE", "GROUP", "UNIT"}
    return {t for t in tokens if t not in drop and len(t) > 1}


def titles_agree(a: str, b: str) -> bool:
    ta, tb = norm_title(a), norm_title(b)
    if not ta or not tb:
        return True
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return overlap >= 0.6


def drawing_list(page: pymupdf.Page) -> dict[str, str]:
    """1페이지 DRAWING LIST에서 도면번호 → 도면명 대조표를 만든다."""
    words = page.get_text("words")
    lines: dict[int, list] = {}
    for w in words:
        lines.setdefault(round(w[1] / 6), []).append(w)     # y좌표 6pt 단위로 행 묶기
    out: dict[str, str] = {}
    for _, ws in lines.items():
        ws.sort(key=lambda w: w[0])
        joined = " ".join(w[4] for w in ws)
        m = DRAWING_NO.search(joined)
        if m:
            title = joined[m.end():].strip(" -–—")
            if title:
                out[m.group()] = " ".join(title.split())
    return out


def instrument_candidates(page: pymupdf.Page, tokens: list[str]) -> list[dict]:
    """텍스트 레이어에서 계기 문자를 좌표와 함께 추출한다."""
    tokenset = set(tokens)
    r = page.rect
    out = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        t = word.strip().strip(".,;:()[]")
        if t in tokenset:
            out.append({
                "token": t,
                "x": round((x0 + x1) / 2 / r.width, 4),      # 0~1 정규화 좌표
                "y": round((y0 + y1) / 2 / r.height, 4),
            })
    out.sort(key=lambda c: (c["y"], c["x"]))
    return out


def render_at_edge(page: pymupdf.Page, max_edge: int) -> pymupdf.Pixmap:
    """장변이 정확히 max_edge가 되도록 배율을 계산해 렌더링한다(재샘플링 없음)."""
    r = page.rect
    scale = max_edge / max(r.width, r.height)
    return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "outputs/pages", help="이미지 출력 폴더")
    ap.add_argument("--pages", help="1-기준 페이지 번호. 예: 6,20,38 또는 6-12")
    ap.add_argument("--drawings", help="도면번호로 선택. 쉼표 구분")
    ap.add_argument("--dpi", type=int, default=200, help="타일 렌더링 DPI (기본 200)")
    ap.add_argument("--tiles", type=parse_tiles, default=(0, 0), metavar="CxR",
                    help="가로x세로 타일 분할. 예: 3x2. 생략하면 전체 이미지만 생성")
    ap.add_argument("--overlap", type=float, default=0.08, help="타일 겹침 비율 (기본 0.08)")
    args = ap.parse_args()

    doc = pymupdf.open(args.pdf)
    args.out.mkdir(parents=True, exist_ok=True)

    listing = drawing_list(doc[0]) if doc.page_count else {}
    print(f"[i] PDF {doc.page_count}쪽 · 1쪽 DRAWING LIST에서 도면 {len(listing)}건 확인")

    selected = select_pages(doc, args)
    print(f"[i] 변환 대상 {len(selected)}쪽: {[p + 1 for p in selected]}")

    manifest = {"pdf": str(args.pdf), "page_count": doc.page_count,
                "dpi": args.dpi, "tiles": list(args.tiles), "drawing_list": listing, "pages": []}

    for pno in selected:
        page = doc[pno]
        number, title = title_block(page)
        stem = f"p{pno + 1:03d}_{number or 'UNKNOWN'}"

        full_path = args.out / f"{stem}.png"
        pix = render_at_edge(page, MAX_EDGE)
        pix.save(full_path)

        entry = {
            "page": pno + 1,
            "drawing_no": number,
            "title": title,
            "title_from_drawing_list": listing.get(number or ""),
            "image": str(full_path.relative_to(ROOT)),
            "image_size": [pix.width, pix.height],
            "page_size_pt": [round(page.rect.width, 1), round(page.rect.height, 1)],
            "tiles": [],
            "text_candidates": instrument_candidates(page, DEFAULT_TOKENS),
            "notes": page_notes(page),
            "conflicts": [],
        }
        if number and number in listing and title:
            if not titles_agree(title, listing[number]):
                entry["conflicts"].append(
                    f"타이틀블록 제목('{title}')과 DRAWING LIST('{listing[number]}')가 다릅니다. 사람이 확인 필요")

        cols, rows = args.tiles
        if cols and rows:
            entry["tiles"] = make_tiles(page, args, stem)

        manifest["pages"].append(entry)
        nc = len(entry["text_candidates"])
        print(f"  p{pno + 1:>3} {number or '???':24} 계기후보 {nc:>3}건  타일 {len(entry['tiles'])}장"
              + ("  ⚠ " + entry["conflicts"][0] if entry["conflicts"] else ""))

    mpath = args.out / "manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[✓] {mpath}")
    return 0


NOTES_ANCHOR = re.compile(r"^(GENERAL\s+)?NOTES?\s*:?$", re.I)


def page_notes(page: pymupdf.Page) -> str:
    """GENERAL NOTES / NOTES 블록을 텍스트로 뽑는다.

    이 블록이 판독의 절반이다. `* DENOTES ... SUPPLIED BY HRSG` 같은 공급 범위 각주와
    `CONFIGURATION IS IDENTICAL FOR GROUP#20` 이 여기 있고, 각각 어느 계기를 뺄지와
    Q'ty를 정한다. 위치를 놓치면 모델이 그 판단 근거를 아예 못 본다.

    좌표를 고정하지 않고 `GENERAL NOTES` / `NOTES :` 글자를 찾아 그 아래·오른쪽을 딸려
    온다. 못 찾으면 우상단을 넓게 훑는다.
    """
    r = page.rect
    anchors = [b for b in page.get_text("blocks")
               if any(NOTES_ANCHOR.match(ln.strip()) for ln in b[4].splitlines() if ln.strip())]
    if anchors:
        x0 = min(b[0] for b in anchors) - r.width * 0.03
        y0 = min(b[1] for b in anchors) - r.height * 0.01
        clip = pymupdf.Rect(max(0, x0), max(0, y0), r.width, min(r.height, y0 + r.height * 0.55))
        text = page.get_text("text", clip=clip).strip()
        if len(text) > 40:
            return text[:4000]
    clip = pymupdf.Rect(r.width * 0.72, 0, r.width, r.height * 0.60)
    return page.get_text("text", clip=clip).strip()[:4000]


def make_tiles(page: pymupdf.Page, args, stem: str) -> list[dict]:
    cols, rows = args.tiles
    r = page.rect
    tw, th = r.width / cols, r.height / rows
    ox, oy = tw * args.overlap, th * args.overlap
    out = []
    for j in range(rows):
        for i in range(cols):
            clip = pymupdf.Rect(max(0, i * tw - ox), max(0, j * th - oy),
                                min(r.width, (i + 1) * tw + ox), min(r.height, (j + 1) * th + oy))
            scale = min(args.dpi / 72, MAX_EDGE / max(clip.width, clip.height))
            pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip, alpha=False)
            path = args.out / f"{stem}_t{j}{i}.png"
            pix.save(path)
            out.append({
                "row": j, "col": i,
                "image": str(path.relative_to(ROOT)),
                "size": [pix.width, pix.height],
                "region": [round(clip.x0 / r.width, 4), round(clip.y0 / r.height, 4),
                           round(clip.x1 / r.width, 4), round(clip.y1 / r.height, 4)],
            })
    return out


def select_pages(doc, args) -> list[int]:
    if args.pages:
        out = []
        for part in args.pages.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-")
                out.extend(range(int(a) - 1, int(b)))
            elif part:
                out.append(int(part) - 1)
        return [p for p in out if 0 <= p < doc.page_count]
    if args.drawings:
        want = {d.strip() for d in args.drawings.split(",") if d.strip()}
        out = []
        for i in range(doc.page_count):
            n, _ = title_block(doc[i])
            if n in want:
                out.append(i)
        missing = want - {title_block(doc[i])[0] for i in out}
        if missing:
            print(f"[!] PDF에서 찾지 못한 도면번호: {sorted(missing)}", file=sys.stderr)
        return out
    return list(range(doc.page_count))


if __name__ == "__main__":
    raise SystemExit(main())
