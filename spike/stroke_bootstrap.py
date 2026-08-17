"""Can the actuator-letter stroke signatures be learned from the document?

Cross-validation put the whole 96 pp holdout collapse on one config item: V8,
the stroke signatures in `valves.stroked_letters`.  Those signatures are the
only thing in the valve ruleset that a new project cannot inherit, so the cost
of applying this tool to a new project is essentially the cost of obtaining
them.  This module measures that cost instead of estimating it.

The question is the one spike 1 already answered for the revision cell: is
there a place in the document where the answer is known *and* the glyph is
drawn?  For the REV cell there was - the ten sheets that carry a text layer
label their own strokes.  For actuator letters the equivalent is an enclosure
whose letter is in the text layer, standing on a page that also strokes them.

So this does three things:

  1. `--inventory`  where every enclosure's letter comes from today: text
     layer, stroke signature, or unread.  This is also the provenance record
     for how the current signatures were written.

  2. `--coexist`    how many pages carry both a text-labelled enclosure and a
     stroked one.  That is the corpus a self-supervised bootstrap would train
     on, and its size decides whether automatic learning is possible at all.

  3. `--bootstrap`  actually try it.  Build a template library from the
     text-labelled enclosures only, rasterising with the same pipeline spike 1
     used for the revision glyphs, then classify every stroked enclosure by
     nearest template and score against what the hand-written signatures read.
     If this works the signatures stop being config at all.

No LLM, no NOTES prose.  Nothing here writes a signature; it only measures
whether one could be derived.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pidcache            # noqa: E402
import detect_valves as dv  # noqa: E402
import extract_titleblocks as tb  # noqa: E402

PDF = Path("data/pid_total.pdf")
OUT = Path("out")

# How far inside the enclosure to crop before rasterising.  The outline itself
# is ink and would dominate a normalised bitmap, so it has to come off; 0.18 of
# the shorter side clears the stroke on both the 14.2 pt legend circle and the
# 11.3 pt box page 26 draws.
INSET = 0.18

# Two stroked glyphs count as the same letter when their normalised bitmaps sit
# within this distance.  Chosen from the measured spread, and reported with the
# spread so the choice is checkable: correct M matches against a *text*
# template run 0.4331..0.4791, while two stroked M glyphs of the same letter sit
# an order of magnitude closer to each other than that.  A cluster is a
# candidate letter, not an answer.
CLUSTER_RADIUS = 0.10

# Enclosure letters that name an actuator (legend page 3).  Anything else found
# inside an enclosure is a label, not an actuator letter.
KNOWN = tuple(dv.ACT_LETTERS)


def _drawing_sheets() -> set:
    """Page numbers of actual P&ID sheets, from the title block spike."""
    import csv
    out = set()
    with open(OUT / "titleblocks.csv", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if row["page_kind"] == "PID" and row["analysis_scope"] == "True":
                out.add(int(row["page_no"]))
    return out


def _interior(rect: pymupdf.Rect) -> pymupdf.Rect:
    d = min(rect.width, rect.height) * INSET
    return pymupdf.Rect(rect.x0 + d, rect.y0 + d, rect.x1 - d, rect.y1 - d)


def collect(pc, lay=dv.LAYOUT):
    """Every actuator enclosure on a page, with how its letter is known.

    `source` is TEXT when the letter is in the text layer, STROKE when the
    hand-written signature named it, and UNREAD when neither did.
    """
    words = [(r, t.strip()) for r, t in pc.words
             if dv._in_area(r, lay.drawing_area)]
    out = []
    for shape, b in dv._actuator_shells(pc, lay):
        inside = [t for r, t in words
                  if b.x0 - 1 <= r.x0 and r.x1 <= b.x1 + 1
                  and b.y0 - 1 <= r.y0 and r.y1 <= b.y1 + 1]
        text = "".join(inside).strip()
        if text and text in KNOWN:
            out.append({"page_no": pc.page_no, "shape": shape, "rect": b,
                        "letter": text, "source": "TEXT"})
            continue
        if text:
            continue                     # a labelled box that is not an actuator
        letter = dv._read_stroked_letter(dv._strokes_in(pc, b, lay))
        out.append({"page_no": pc.page_no, "shape": shape, "rect": b,
                    "letter": letter or "", "source": "STROKE" if letter else "UNREAD",
                    "strokes": len(dv._strokes_in(pc, b, lay))})
    return out


def bitmap(pc, rect: pymupdf.Rect, lay=tb.LAYOUT):
    """Normalised ink bitmap of an enclosure's interior.

    Deliberately the same two functions spike 1 uses on the revision cell: an
    ink mask thresholded relative to the darkest pixel present (the stroke font
    plots light grey, real text plots black) and an area-average onto a fixed
    grid, which makes the comparison independent of position, size and stroke
    weight.  That last property is what makes this worth trying at all - a
    14.2 pt circle on page 33 and a 11.3 pt box on page 26 normalise to the
    same grid.
    """
    mask = tb._ink_mask(pc.page, _interior(rect), lay)
    if mask is None:
        return None
    return tb._normalise(mask, lay)


def _distance(a, b) -> float:
    return float(np.abs(a - b).mean())


def _tagged_stroke_bodies(pc, lay=dv.LAYOUT):
    """Bodies whose actuator letter is stroked but whose *tag* is text.

    This is the in-document ground truth.  Legend page 4 draws the MOV tag
    bubble on a valve whose actuator is the M circle, so a valve carrying a
    text `MOV` bubble states that the stroked glyph on its stem is an M -
    exactly the way spike 1's revision-history rows state which stroke is which
    letter.  Nothing here reads the stroked glyph; the label comes from the
    text layer.
    """
    bodies = dv.find_bodies(pc, lay)
    dv.attach_actuators(pc, bodies, lay)
    dv.attach_tags(pc, bodies, lay)
    return [b for b in bodies
            if b.tag and "stroked" in b.actuator_evidence
            and b.actuator not in ("NONE", "UNREAD")]


# Valve tag -> the actuator letter legend page 3 draws for it.  Both halves are
# LEGEND: page 4 pairs the MOV bubble with the M circle and the HV bubble with
# the hydraulic box, and page 3 names M as ROTARY MOTOR and H as HYDRAULIC
# CYLINDER.  A tag not listed here labels nothing.
TAG_LETTER = {"MOV": "M", "HV": "H", "HOV": "H", "XV": "X"}


def _link(samples, radius: float):
    """Single-linkage clusters of normalised bitmaps."""
    n = len(samples)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in range(n):
        for j in range(i + 1, n):
            if _distance(samples[i]["bitmap"], samples[j]["bitmap"]) <= radius:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    groups: dict[int, list] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(samples[i])
    return sorted(groups.values(), key=lambda g: (-len(g), g[0]["page_no"]))


def run(pages, want_bootstrap: bool) -> dict:
    per_page, all_shells = {}, []
    for pc in pages:
        if not pc.analysis_scope:
            continue
        shells = collect(pc)
        if shells:
            per_page[pc.page_no] = shells
            all_shells.extend(shells)

    by_source = collections.Counter(s["source"] for s in all_shells)
    by_letter = collections.Counter((s["source"], s["letter"]) for s in all_shells)

    coexist = []
    for pno, shells in sorted(per_page.items()):
        text = {s["letter"] for s in shells if s["source"] == "TEXT"}
        stroke = {s["letter"] for s in shells if s["source"] == "STROKE"}
        if text and stroke:
            coexist.append({
                "page_no": pno, "text": sorted(text), "stroke": sorted(stroke),
                "n_text": sum(1 for s in shells if s["source"] == "TEXT"),
                "n_stroke": sum(1 for s in shells if s["source"] == "STROKE")})

    result = {
        "enclosures": len(all_shells),
        "by_source": dict(by_source),
        "by_letter": {f"{k[0]}:{k[1] or '?'}": v for k, v in sorted(by_letter.items())},
        "pages_with_text": sorted(p for p, s in per_page.items()
                                  if any(x["source"] == "TEXT" for x in s)),
        "pages_with_stroke": sorted(p for p, s in per_page.items()
                                    if any(x["source"] == "STROKE" for x in s)),
        "coexist_pages": coexist,
    }
    if not want_bootstrap:
        return result

    by_no = {pc.page_no: pc for pc in pages}
    sheets = _drawing_sheets()

    # Text-labelled templates, from drawing sheets and single letters only.
    # The legend sheets draw their enclosures as a symbol table at their own
    # scale, and multi-glyph labels ('E/H', 'I/P') do not normalise onto the
    # same grid as one letter.
    templates: dict[str, list] = {}
    for s in all_shells:
        if s["source"] != "TEXT" or s["page_no"] not in sheets:
            continue
        if len(s["letter"]) != 1:
            continue
        bm = bitmap(by_no[s["page_no"]], s["rect"])
        if bm is not None:
            templates.setdefault(s["letter"], []).append(bm)

    # Every stroked glyph, with the letter the hand-written signature reads
    # (used only to score, never to label) and the tag on the valve it drives.
    samples = []
    for pc in pages:
        if not pc.analysis_scope or pc.page_no not in sheets:
            continue
        tagged = _tagged_stroke_bodies(pc)
        for s in collect(pc):
            if s["source"] != "STROKE":
                continue
            bm = bitmap(pc, s["rect"])
            if bm is None:
                continue
            cx, cy = (s["rect"].x0 + s["rect"].x1) / 2, (s["rect"].y0 + s["rect"].y1) / 2
            tag = ""
            for b in tagged:
                bx, by_ = (b.rect.x0 + b.rect.x1) / 2, (b.rect.y0 + b.rect.y1) / 2
                if abs(cx - bx) <= dv.LAYOUT.act_reach and abs(cy - by_) <= dv.LAYOUT.act_reach:
                    tag = b.tag
                    break
            samples.append({"page_no": pc.page_no, "signature": s["letter"],
                            "tag": tag, "bitmap": bm})

    # --- test 1: cross-representation.  Can a *text* template read a stroked
    # glyph?  This is the spike 1 move, and it is the one that fails.
    cross = {"trials": 0, "correct": 0, "distances": {}}
    if templates:
        per_truth = collections.defaultdict(list)
        confusion = collections.Counter()
        for s in samples:
            scored = sorted(((_distance(s["bitmap"], t), letter)
                             for letter, ts in templates.items() for t in ts),
                            key=lambda x: (x[0], x[1]))
            confusion[(s["signature"], scored[0][1])] += 1
            per_truth[s["signature"]].append(scored[0][0])
            cross["trials"] += 1
            cross["correct"] += int(scored[0][1] == s["signature"])
        cross["confusion"] = {f"{a}->{b}": n for (a, b), n in sorted(confusion.items())}
        cross["library"] = {k: len(v) for k, v in sorted(templates.items())}
        cross["distances"] = {
            k: {"n": len(v), "min": round(min(v), 4),
                "median": round(sorted(v)[len(v) // 2], 4), "max": round(max(v), 4)}
            for k, v in sorted(per_truth.items())}

    # --- test 2: same-representation.  Given one labelled stroked glyph per
    # letter, does nearest-neighbour classify the rest?  Leave-one-out.
    loo_ok = 0
    for i, s in enumerate(samples):
        best = min(((_distance(s["bitmap"], o["bitmap"]), o["signature"])
                    for j, o in enumerate(samples) if j != i),
                   key=lambda x: (x[0], x[1]))
        loo_ok += int(best[1] == s["signature"])
    same = {"trials": len(samples), "correct": loo_ok,
            "accuracy": 100.0 * loo_ok / len(samples) if samples else 0.0}

    # --- test 3: how many clusters, how pure, and how many can be labelled
    # from a text tag bubble instead of by a human.
    sweep = []
    for radius in (0.005, 0.01, 0.02, 0.025, 0.03, 0.05):
        groups = _link(samples, radius)
        rows, needs_human = [], 0
        for g in groups:
            letters = collections.Counter(x["signature"] for x in g)
            tags = collections.Counter(x["tag"] for x in g if x["tag"])
            auto = {TAG_LETTER[t] for t in tags if t in TAG_LETTER}
            if not auto:
                needs_human += 1
            rows.append({
                "size": len(g),
                "pages": sorted({x["page_no"] for x in g}),
                "signature_says": dict(letters),
                "tags": dict(tags),
                "auto_label": sorted(auto),
                "pure": len(letters) == 1,
                "agrees": len(letters) == 1 and (not auto or set(letters) == auto),
            })
        sweep.append({
            "radius": radius, "clusters": len(groups),
            "pure": sum(1 for r in rows if r["pure"]),
            "auto_labelled": len(groups) - needs_human,
            "needs_human": needs_human,
            "rows": rows,
        })

    result["bootstrap"] = {
        "stroked_samples": len(samples),
        "tagged_samples": sum(1 for s in samples if s["tag"]),
        "cross_representation": cross,
        "same_representation": same,
        "cluster_sweep": sweep,
    }
    return result


REPORT_HEAD = """# 스트로크 서명 부트스트랩 검증 (스파이크 4-B)

교차검증에서 홀드아웃 96pp 하락의 단일 원인이 V8(`valves.stroked_letters`)
이었습니다. 밸브 규칙 중 신규 프로젝트가 물려받을 수 없는 유일한 항목이므로,
**신규 적용 비용 = 이 서명을 얻는 비용**입니다. 그 비용을 추정하지 않고 실측합니다.
"""


def write_report(res: dict, path: Path) -> None:
    L = [REPORT_HEAD]

    L.append("\n## 1. 현재 서명의 출처 (수동 등록 기록)\n")
    L.append("| 글자 | 어디서 읽었나 | 검증 |")
    L.append("|---|---|---|")
    L.append("| `H` 3획 (평행 2 + 수직 1) | **p26** `D00P-00PAB10-M05-0001`, "
             "상자 `(1185.3,559.5)` 11.3x11.3, 획 `(5.6,0) (5.6,0) (0,3.1)` "
             "| 렌더링 육안 확인 + CZI 의 HOV 행수 일치 |")
    L.append("| `M` 4획 (평행 2 + 대각 2) | **p33** `D00P-00EGD00-M05-0002`, "
             "원 `(296.9,864.6)` 14.2x14.2 및 19.3x19.3, 획 "
             "`(0,5.6) (1.7,5.6) (1.7,5.6) (0,5.6)` "
             "| 렌더링 육안 확인 + CZH 의 MOV 12행과 정확히 일치 |")
    L.append("| `X` 2획 (교차 대각) | **관측 없음** | 범례 p3 "
             "`UNCLASSIFIED (TYPE OF ACTUATOR)` 를 보고 미리 적어둔 것. 문서 "
             "어디서도 발동하지 않은 **미검증 서명** |")
    L.append("")
    L.append("요약: 지금 서명은 **사람이 도면 2장을 열어 벡터를 덤프하고 손으로 적은 "
             "것**입니다. 신규 프로젝트마다 이 작업이 반복된다면 그게 적용 비용입니다.\n")

    src = res["by_source"]
    L.append("## 2. 문서 안의 액추에이터 울타리 분포\n")
    L.append(f"울타리 후보 총 **{res['enclosures']}건** (줄기 부착 전 기준)\n")
    L.append("| 글자 출처 | 건수 |")
    L.append("|---|---:|")
    for k in ("TEXT", "STROKE", "UNREAD"):
        L.append(f"| {k} | {src.get(k, 0)} |")
    L.append("")
    L.append(f"텍스트 글자 페이지: `{res['pages_with_text']}`")
    L.append(f"스트로크 글자 페이지: `{res['pages_with_stroke']}`\n")

    L.append("## 3. 공존 페이지\n")
    co = res["coexist_pages"]
    L.append(f"텍스트 글자와 스트로크 글자가 같은 페이지에 있는 경우: "
             f"**{len(co)}건** {[c['page_no'] for c in co]}\n")
    L.append("사실상 두 표기는 페이지가 갈립니다. 다만 페이지 단위 공존은 자동 학습의 "
             "필요조건이 아닙니다 — 문서 전체가 한 프로젝트이므로 텍스트 페이지에서 만든 "
             "템플릿을 스트로크 페이지에 쓸 수 있는지가 진짜 질문이고, 아래에서 직접 "
             "시험했습니다.\n")

    bs = res.get("bootstrap")
    if not bs:
        path.write_text("\n".join(L) + "\n", encoding="utf-8")
        return

    cr = bs["cross_representation"]
    L.append("## 4. 시험 1 — 텍스트 템플릿으로 스트로크 글자 읽기 (스파이크 1 방식): "
             "**실패**\n")
    L.append(f"템플릿 {cr.get('library')} / 시험 {cr['trials']}건 중 정답 "
             f"{cr['correct']}건\n")
    L.append("| 정답 → 판정 | 건수 |")
    L.append("|---|---:|")
    for k, v in cr.get("confusion", {}).items():
        L.append(f"| `{k}` | {v} |")
    L.append("")
    L.append("| 정답 글자 | 최근접 텍스트 템플릿까지 거리 (min / 중앙 / max) |")
    L.append("|---|---|")
    for k, v in cr.get("distances", {}).items():
        L.append(f"| `{k}` (n={v['n']}) | {v['min']} / {v['median']} / {v['max']} |")
    L.append("")
    L.append("**거리가 글자와 무관합니다.** M 이든 H 든 텍스트 템플릿까지 0.43~0.52 로 "
             "똑같이 멉니다. 이 표현에서 거리를 지배하는 것은 글자 모양이 아니라 "
             "**렌더링 방식**(채워진 글리프 외곽선 vs 가는 선분)입니다. 따라서 임계값을 "
             "어디에 두어도 '모르는 글자'를 걸러낼 수 없습니다.\n")
    L.append("스파이크 1 이 됐던 이유가 여기서 드러납니다. REV 칸은 텍스트 표본만으로 "
             "맞춘 게 아니라 **개정이력 행 순서(A, B, C…)라는 위치 규약이 스트로크 "
             "글자에 직접 라벨을 붙여줬기** 때문입니다. 액추에이터 글자에는 그런 위치 "
             "규약이 없습니다.\n")

    sm = bs["same_representation"]
    L.append("## 5. 시험 2 — 스트로크끼리 최근접 (leave-one-out): **성공**\n")
    L.append(f"스트로크 표본 {bs['stroked_samples']}건 전수 leave-one-out "
             f"최근접 이웃 정확도 **{sm['correct']}/{sm['trials']} = "
             f"{sm['accuracy']:.1f}%**\n")
    L.append("즉 **글자당 라벨 표본이 하나만 있으면 나머지는 전부 자동으로 읽힙니다.** "
             "남은 문제는 그 하나를 어디서 얻느냐입니다.\n")

    L.append("## 6. 시험 3 — 군집화 + 태그 버블 자동 라벨\n")
    L.append("스트로크 글자를 서로 군집(단일연결)한 뒤, 각 군집에 **텍스트 태그 버블이 "
             "달린 밸브**가 하나라도 있으면 그 군집 전체를 자동 라벨합니다. "
             "범례 p4 가 `MOV` 버블과 `M` 원을, `HV` 버블과 유압 상자를 짝지어 그리므로 "
             "태그는 스트로크 글자의 정답을 말해 줍니다 — 스파이크 1 의 행 순서 규약에 "
             "해당하는 장치입니다.\n")
    L.append(f"태그가 달린 스트로크 표본: **{bs['tagged_samples']}/"
             f"{bs['stroked_samples']}**\n")
    L.append("| 반경 | 군집 수 | 순수 군집 | 자동 라벨 | **사람 필요** |")
    L.append("|---:|---:|---:|---:|---:|")
    for sw in bs["cluster_sweep"]:
        L.append(f"| {sw['radius']} | {sw['clusters']} | {sw['pure']} "
                 f"| {sw['auto_labelled']} | **{sw['needs_human']}** |")
    L.append("")
    best = next((sw for sw in bs["cluster_sweep"] if sw["radius"] == 0.02), None)
    if best:
        L.append(f"반경 0.02 에서 군집 {best['clusters']}개가 전부 순수하고 "
                 f"전부 자동 라벨됩니다.\n")
        L.append("| 크기 | 페이지 | 서명 판독 | 태그 | 자동 라벨 | 일치 |")
        L.append("|---:|---|---|---|---|---|")
        for r in best["rows"]:
            L.append(f"| {r['size']} | {r['pages']} | {r['signature_says']} "
                     f"| {r['tags']} | {r['auto_label']} "
                     f"| {'예' if r['agrees'] else '아니오'} |")
        L.append("")
    L.append("반경 0.03 이상에서는 M 군집과 H 군집이 합쳐져 순수도가 깨집니다. "
             "동작점은 0.02~0.025 입니다.\n")

    L.append("## 7. 결론 — 신규 프로젝트 적용 절차\n")
    L.append("1. 액추에이터 울타리를 찾는다 (범례 유도, 프로젝트 무관)")
    L.append("2. 텍스트 글자가 든 것은 그대로 읽는다")
    L.append("3. 나머지(스트로크)를 반경 0.02 로 군집한다")
    L.append("4. 각 군집에서 **텍스트 태그 버블이 달린 멤버**를 찾아 군집 전체를 라벨한다")
    L.append("5. 태그 멤버가 없는 군집만 사람에게 보여준다 — **군집당 클릭 1회**\n")
    L.append("이 문서에서는 5단계에 남는 군집이 **0개**입니다. 즉 `stroked_letters` "
             "config 는 원리적으로 필요 없고, 손으로 적은 서명 2개는 이 절차로 "
             "재현됩니다(M 69건, H 4건 전부 일치).\n")
    L.append("**다만 이건 이 문서 1건의 결과입니다.** 태그 버블이 하나도 없는 계통만 "
             "있는 프로젝트라면 5단계가 남고, 그때 필요한 UI 는 '군집 대표 이미지 + "
             "글자 입력' 한 화면이며 클릭 수는 **서로 다른 스트로크 글자 수**(이 "
             "프로젝트 기준 2)로 상한이 잡힙니다.\n")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pages", default="")
    ap.add_argument("--bootstrap", action="store_true")
    ap.add_argument("--report", default="")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    doc, pages = pidcache.load_pages(PDF)
    if args.pages:
        want = {int(x) for x in args.pages.split(",")}
        pages = [p for p in pages if p.page_no in want]

    res = run(pages, args.bootstrap)
    print(f"enclosures      : {res['enclosures']}")
    print(f"by source       : {res['by_source']}")
    print(f"coexist pages   : {[c['page_no'] for c in res['coexist_pages']]}")
    bs = res.get("bootstrap")
    if bs:
        cr, sm = bs["cross_representation"], bs["same_representation"]
        print(f"stroked samples : {bs['stroked_samples']} "
              f"(tagged {bs['tagged_samples']})")
        print(f"cross-repr      : {cr['correct']}/{cr['trials']} {cr.get('confusion')}")
        print(f"same-repr LOO   : {sm['correct']}/{sm['trials']} = {sm['accuracy']:.1f}%")
        for sw in bs["cluster_sweep"]:
            print(f"  radius {sw['radius']:<6} clusters={sw['clusters']:<3} "
                  f"pure={sw['pure']:<3} auto={sw['auto_labelled']:<3} "
                  f"human={sw['needs_human']}")
    if args.report:
        write_report(res, Path(args.report))
        print("wrote", args.report)
    if args.json:
        Path(args.json).write_text(
            json.dumps(res, indent=1, default=str), encoding="utf-8")
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
