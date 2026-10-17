"""L39 — 정합성 검토 결과를 입력 PDF 에 마크업해서 낸다.

  * 맨 앞에 '정합성 검토 결과' 장(요약 · 시트별 · 항목 목록 — 누르면 그 쪽으로)을 넣는다.
  * 각 쪽의 그 자리에 색 상자(주석 — 뷰어의 주석 목록에 '분류 · 제목 · 내용' 이 남는다)와 번호표(E3 · C12 · G40)를 찍는다.
  * 책갈피: 요약 · 분류별 · 시트별.
판정 0줄 — `review.build` 가 낸 항목을 그 자리에 옮겨 그릴 뿐이다.  원본 PDF 파일은 바꾸지 않는다 (새 파일을 만든다).

좌표: 분석 결과는 화면(회전 뒤) 좌표다.  주석과 글자는 회전 전 좌표로 넣어야 하므로 `derotation_matrix` 를 곱한다.
"""
from __future__ import annotations

import time

import pymupdf

COLOR = {"ERROR": (0.86, 0.10, 0.10), "CHECK": (0.95, 0.55, 0.0), "GAP": (0.25, 0.35, 0.85), "INFO": (0.55, 0.55, 0.55)}
TAG = {"ERROR": "E", "CHECK": "C", "GAP": "G", "INFO": "I"}
CAT_KO = {"ERROR": "설계 오류", "CHECK": "설계 확인", "GAP": "읽기 빈틈", "INFO": "참고"}
TOPIC_KO = {"fromto": "from-to", "line": "선 연결", "gate": "게이트", "command": "명령 동작", "pair": "반대 명령",
            "read": "읽기"}
_FONT = None


def _font():
    global _FONT
    if _FONT is None:
        _FONT = pymupdf.Font("korea")
    return _FONT


def _pct(v):
    return "—" if v is None else f"{v * 100:.1f}%"


class _Writer:
    """요약 장 — 글줄을 위에서 아래로.  넘치면 새 장."""

    def __init__(self, doc, at, size):
        self.doc, self.at, self.size = doc, at, size
        self.pages = []
        self.new()

    def new(self):
        w, h = self.size
        i = self.at + len(self.pages)
        self.doc.new_page(i, width=w, height=h)
        self.doc[i].insert_font(fontname="ko", fontbuffer=_font().buffer)
        self.pages.append(i)
        self.idx, self.y = i, 40
        self.m = 36

    @property
    def page(self):                                   # 쪽을 넣으면 앞서 받은 쪽 객체가 끊긴다 — 늘 새로 받는다
        return self.doc[self.idx]

    def need(self, h):
        if self.y + h > self.size[1] - 30:
            self.new()

    def text(self, s, size=10, color=(0, 0, 0), x=None):
        self.need(size * 1.5)
        self.page.insert_text((x if x is not None else self.m, self.y + size), s, fontname="ko", fontsize=size, color=color)
        self.y += size * 1.55

    def cells(self, vals, xs, size=8.5, color=(0, 0, 0), fill=None, link=None, colors=None):
        self.need(size * 1.6)
        w = self.size[0] - self.m
        if fill:
            self.page.draw_rect(pymupdf.Rect(self.m - 2, self.y, w, self.y + size * 1.5), color=None, fill=fill)
        for i, (v, x) in enumerate(zip(vals, xs)):
            lim = (xs[i + 1] - x - 4) if i + 1 < len(xs) else (w - x)
            s = str(v if v is not None else "")
            while s and _font().text_length(s, size) > lim:
                s = s[:-2] + "…" if len(s) > 2 else ""
            self.page.insert_text((x, self.y + size * 1.1), s, fontname="ko", fontsize=size,
                                  color=(colors[i] if colors and colors[i] else color))
        if link is not None:
            self.page.insert_link({"kind": pymupdf.LINK_GOTO, "page": link,
                                   "from": pymupdf.Rect(self.m - 2, self.y, w, self.y + size * 1.5)})
        self.y += size * 1.5


def build(src_pdf, review, out_pdf, name="", include_info=False, author=""):
    doc = pymupdf.open(src_pdf)
    items = [it for it in review.get("items") or [] if include_info or it["cat"] != "INFO"]
    n0 = doc.page_count
    first = doc[0].rect
    size = (max(first.width, 842.0), max(first.height, 595.0))
    # ---- 각 쪽에 마크업 (요약 장을 넣기 전 — 쪽 번호가 그대로일 때)
    by_page = {}
    for it in items:
        by_page.setdefault(it["page"], []).append(it)
    for pg, its in by_page.items():
        if not (1 <= pg <= n0):
            continue
        page = doc[pg - 1]
        dm = page.derotation_matrix
        for it in its:
            if not it.get("rect"):
                continue
            col = COLOR[it["cat"]]
            R = pymupdf.Rect(it["rect"])
            pad = 1.5
            R = pymupdf.Rect(R.x0 - pad, R.y0 - pad, R.x1 + pad, R.y1 + pad)
            Ru = R * dm
            Ru.normalize()
            a = page.add_rect_annot(Ru)
            a.set_colors(stroke=col)
            a.set_border(width=1.4 if it["cat"] != "INFO" else 0.8, dashes=None if it["cat"] in ("ERROR", "CHECK") else [3, 2])
            a.set_opacity(0.95)
            a.set_info(title=f"{TAG[it['cat']]}{it['id']} {CAT_KO[it['cat']]}", subject=TOPIC_KO.get(it["topic"], it["topic"]),
                       content=f"{it['title']}\n{it['text']}")
            a.update()
            # 번호표 — 상자 오른쪽 위 (화면 좌표로 정하고 회전 전으로)
            tag = f"{TAG[it['cat']]}{it['id']}"
            fs = 6.5
            tw = pymupdf.get_text_length(tag, "helv", fs) + 3
            box = pymupdf.Rect(R.x1, R.y0 - fs - 2, R.x1 + tw, R.y0)
            bu = box * dm
            bu.normalize()
            page.draw_rect(bu, color=col, fill=col, width=0.3, overlay=True)
            org = pymupdf.Point(box.x0 + 1.5, box.y1 - 1.6) * dm
            page.insert_text(org, tag, fontname="helv", fontsize=fs, color=(1, 1, 1), rotate=page.rotation, overlay=True)
    # ---- 앞에 요약 장
    W = _Writer(doc, 0, size)
    cnt = review.get("count") or {}
    rate = review.get("rate") or {}
    W.text("LOGIC 정합성 검토 결과", 20, (0.1, 0.2, 0.45))
    W.text(f"{name}    ·    {time.strftime('%Y-%m-%d %H:%M')}" + (f"    ·    {author}" if author else ""), 9.5, (0.35, 0.35, 0.35))
    W.y += 6
    W.text(f"도면 읽기 {_pct(rate.get('read'))}     툴 판정 {_pct(rate.get('judged'))}     "
           f"설계 오류 {cnt.get('ERROR', 0)}     설계 확인 {cnt.get('CHECK', 0)}     읽기 빈틈 {cnt.get('GAP', 0)}", 12)
    parts = rate.get("parts") or {}
    tl = rate.get("tally") or {}
    W.text("툴 판정 — " + "   ".join(
        f"{TOPIC_KO.get(k, k)} {_pct(v)} ({(tl.get(k) or {}).get('done', 0)}/{(tl.get(k) or {}).get('all', 0)})"
        for k, v in parts.items() if v is not None), 9.5, (0.3, 0.3, 0.3))
    W.text("빨강 E = 설계 오류 (도면이 어긋남)   주황 C = 설계 확인 (의도인지 판단)   파랑 G = 읽기 빈틈 (툴이 다 읽지 못함 — 가르치기 · 마크업)",
           9, (0.3, 0.3, 0.3))
    note_page, note_y = W.idx, W.y                     # 안내 한 줄 — 요약 장 수를 안 뒤 쓴다
    W.y += 9 * 1.55
    W.y += 8
    # 주제별
    W.text("주제별", 12, (0.1, 0.2, 0.45))
    xs = [W.m, W.m + 140, W.m + 230, W.m + 320, W.m + 410]
    W.cells(["주제", "설계 오류", "설계 확인", "읽기 빈틈"], xs, 9, fill=(0.88, 0.91, 0.97))
    for k, d in (review.get("by_topic") or {}).items():
        W.cells([TOPIC_KO.get(k, k), d.get("ERROR", 0), d.get("CHECK", 0), d.get("GAP", 0)], xs, 9)
    W.y += 8
    # 시트별
    W.text("시트별 (누르면 그 쪽)", 12, (0.1, 0.2, 0.45))
    xs = [W.m, W.m + 90, W.m + 130, W.m + 520, W.m + 590, W.m + 660, W.m + 730]
    W.cells(["시트", "쪽", "제목", "설계 오류", "설계 확인", "읽기 빈틈"], xs, 8.5, fill=(0.88, 0.91, 0.97))
    links = []
    for r in review.get("per_sheet") or []:
        if not (r["ERROR"] or r["CHECK"] or r["GAP"]):
            continue
        W.cells([r["sheet_no"], r["page"], r["title"], r["ERROR"] or "", r["CHECK"] or "", r["GAP"] or ""], xs, 8.5,
                colors=[None, None, None, COLOR["ERROR"], COLOR["CHECK"], COLOR["GAP"]])
        links.append((W.idx, W.y - 8.5 * 1.5, r["page"]))
    W.y += 8
    # 항목
    W.text("항목 (누르면 그 쪽)", 12, (0.1, 0.2, 0.45))
    xs = [W.m, W.m + 48, W.m + 112, W.m + 170, W.m + 420]
    W.cells(["번호", "분류", "시트", "제목", "내용"], xs, 8, fill=(0.88, 0.91, 0.97))
    for it in items:
        W.cells([f"{TAG[it['cat']]}{it['id']}", CAT_KO[it["cat"]], it["sheet_no"] or f"p{it['page']}", it["title"], it["text"]],
                xs, 8, colors=[COLOR[it["cat"]], COLOR[it["cat"]], None, None, (0.3, 0.3, 0.3)])
        links.append((W.idx, W.y - 8 * 1.5, it["page"]))
    n = len(W.pages)
    doc[note_page].insert_text((W.m, note_y + 9), f"각 쪽의 색 상자를 누르면 내용이 보입니다.  맨 앞 {n} 장이 이 요약이라 "
                          f"원래 쪽 번호에 {n} 을 더한 쪽이 그 도면입니다.", fontname="ko", fontsize=9, color=(0.45, 0.45, 0.45))
    for p, y, pg in links:
        if 1 <= pg <= n0:
            doc[p].insert_link({"kind": pymupdf.LINK_GOTO, "page": pg - 1 + n,
                           "from": pymupdf.Rect(W.m - 2, y, size[0] - W.m, y + 12)})
    # ---- 책갈피
    toc = [[1, "정합성 검토 결과", 1]]
    for cat in ("ERROR", "CHECK", "GAP"):
        its = [it for it in items if it["cat"] == cat and 1 <= it["page"] <= n0]
        if its:
            toc.append([1, f"{CAT_KO[cat]} {len(its)}", its[0]["page"] + n])
            for it in its[:400]:
                toc.append([2, f"{TAG[cat]}{it['id']} {it['sheet_no']} {it['title']}"[:120], it["page"] + n])
    toc.append([1, "시트", n + 1])
    for r in review.get("per_sheet") or []:
        if 1 <= r["page"] <= n0:
            toc.append([2, f"{r['sheet_no'] or 'p' + str(r['page'])} {r['title']}"[:120], r["page"] + n])
    try:
        doc.set_toc(toc)
    except Exception:
        pass
    doc.subset_fonts()
    doc.save(out_pdf, garbage=3, deflate=True)
    doc.close()
    return {"cover_pages": n, "marked": sum(1 for it in items if it.get("rect")), "items": len(items)}

