"""LOGIC L1 — 샘플 실태 조사 (읽기만 · 판정 코드 아님).

    python3 spike/logic_survey.py data/logic/HRSG_Logic_rev2.pdf [더 많은 PDF …]

장마다: 낱말 수(글자층) · SHX 주석 수 · 이미지 수 · 그림 항목 종류(l/c/re/qu) ·
빨강 잉크 그림 수(개정 클라우드) · 타이틀블록 시트 번호(진짜 글자) · 본문 낱말 수.
본문 낱말이 0 에 가깝고 짧은 선이 많으면 "글자가 선으로 그려진 장" 이다.
시트 번호 꼴은 두 장 이상 되풀이되는 모양으로만 고른다 (tags.shape 와 같은 생각).
"""
import collections
import re
import sys

import pymupdf

SHX_AUTHOR = "AutoCAD SHX Text"


def shape(t):
    out, kind, run = [], None, 0
    for ch in t:
        k = "D" if ch.isdigit() else "L" if ch.isalpha() else ch
        if k == kind:
            run += 1
        else:
            if kind:
                out.append("%s%d" % (kind, run))
            kind, run = k, 1
    if kind:
        out.append("%s%d" % (kind, run))
    return "".join(out)


def survey(path):
    doc = pymupdf.open(path)
    rows = []
    for p in doc:
        words = p.get_text("words")
        W, H = p.rect.width, p.rect.height
        kinds = collections.Counter()
        red = short = 0
        for d in p.get_drawings():
            if tuple(round(v, 2) for v in (d.get("color") or ())) == (1.0, 0.0, 0.0):
                red += 1
            for it in d["items"]:
                kinds[it[0]] += 1
                if it[0] == "l" and abs(it[1].x - it[2].x) + abs(it[1].y - it[2].y) < 3:
                    short += 1
        shx = sum(1 for a in p.annots() if (a.info.get("title") or "") == SHX_AUTHOR)
        corner = [w[4] for w in words if w[0] > W * 0.85 and w[1] > H * 0.88]
        body = [w for w in words if W * 0.04 < w[0] < W * 0.96 and H * 0.06 < w[1] < H * 0.87
                and not re.fullmatch(r"[A-Q]|\d{1,2}", w[4])]
        rows.append(dict(page=p.number + 1, size=(round(W), round(H)), rot=p.rotation,
                         words=len(words), body_words=len(body), shx=shx,
                         images=len(p.get_images()), kinds=dict(kinds),
                         short_lines=short, red=red, corner=corner))
    # sheet-number shape that recurs on >= 2 pages in the title-block corner
    votes = collections.Counter()
    for r in rows:
        for t in set(r["corner"]):
            if any(c.isdigit() for c in t) and any(c.isalpha() for c in t):
                votes[shape(t)] += 1
    form = [s for s, n in votes.most_common() if n >= 2]
    for r in rows:
        r["sheet"] = next((t for t in r["corner"] if shape(t) in form[:2]), None)
    return rows, form


def main(paths):
    for path in paths:
        rows, form = survey(path)
        print("==", path, "pages", len(rows), "sheet-number shapes", form[:3])
        stroke = [r["page"] for r in rows if r["body_words"] < 15 and r["short_lines"] > 500]
        print("  pages whose body text is strokes:", len(stroke), stroke)
        print("  pages with SHX annotations:", [r["page"] for r in rows if r["shx"]])
        print("  pages with red ink (revision clouds):", sum(1 for r in rows if r["red"]))
        for r in rows:
            print("  p%-3d %-6s words %-4d body %-4d short %-6d red %-4d img %d %s"
                  % (r["page"], r["sheet"], r["words"], r["body_words"],
                     r["short_lines"], r["red"], r["images"], r["kinds"]))


if __name__ == "__main__":
    main(sys.argv[1:])
