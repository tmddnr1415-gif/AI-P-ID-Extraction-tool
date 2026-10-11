"""hotfix85 — **가르치기만으로 읽히는가** 를 이미 읽히는 모든 문서에서 잰다.

    python3 spike/teach_sim.py <프로젝트 이름> [--blind bubbles,legend,frame] [--out out/hotfix85/sim]

1. **사람 흉내** (가벼운 자식 프로세스) — 그 문서에서 사람이 그을 자리를 고른다:
   · 도면 영역 = 그 문서의 테두리 · NOTES = 그 문서의 NOTES 영역
   · 범례 칸 제목 셋 = 그 장에 인쇄된 머리말 글자를 감싼 사각형 (+2pt 여유)
   · 버블 예시 = 계기가 가장 많은 장에서 **가장 흔한 버블 모양 둘 + 다른 모양 하나씩**(최대 4) (+2pt)
2. **눈가림 분석** (`PID_TEACH_BLIND`) — 프로그램이 그 항목을 스스로 찾지 않고 가르친 것만 쓴다.
**기본은 최소 입력**(`--full` 이면 위의 사각형 전부) — 화면의 할 일 목록과 같다:
   · 범례 = **장 번호 하나** ([이 장이 범례입니다])
   · 버블 = 계기가 가장 많은 장에서 **버블 하나를 누른 자리** (`detect_symbols.bubble_at` — 서버의 `/teach/click` 과 같은 함수)
   · NOTES = 그 장의 `NOTES` 글자를 누른 자리 → 거기서 테두리 끝까지 (서버와 같은 계산)
   · 도면 영역 · 타이틀블록 = **묻지 않는다** (테두리를 못 찾으면 종이가 테두리다)
3. 기준선(`out/regression_3p/<이름>.json`) 과 행 단위로 맞댄다 — 같은 행 · 기준에만 · 가르치기에만 ·
   SCOPE/Q'ty 가 다른 행 · 지문.

판정 코드를 바꾸지 않는다 — 눈가림은 시뮬레이션 스위치이고, 가르친 값은 화면이 저장하는 모양 그대로다.
"""
from __future__ import annotations

import collections
import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
PROJECTS = {p["name"]: p for p in json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}


def _expand(r, d=2.0):
    return [round(r[0] - d, 1), round(r[1] - d, 1), round(r[2] + d, 1), round(r[3] + d, 1)]


def _heading_rect(pc, key):
    """그 장에 인쇄된 머리말 글자를 감싼 사각형 — 사람이 그을 자리."""
    import legend_rules
    import pidcache
    import pymupdf
    tries = [key.split()] + [a.split() for a in legend_rules.HEADING_ALTERNATIVES.get(key, ())
                             if not a.startswith("§ ")]
    if key == "ELECTRIC SIGNAL":
        tries.append(["ELECTRICAL", "SIGNAL"])
    toks = list(pidcache.tokens(pc.words))
    for want in tries:
        r = legend_rules._line_with(pc, want)
        if r is None:
            continue
        cy = (r.y0 + r.y1) / 2
        row = sorted((w for w in toks if abs((w[0].y0 + w[0].y1) / 2 - cy) < r.height / 2 and w[0].x0 >= r.x0 - 0.5),
                     key=lambda w: w[0].x0)[:len(want)]
        R = pymupdf.Rect(r)
        for w, _t in row:
            R |= w
        return _expand(list(R))
    for alt in legend_rules.HEADING_ALTERNATIVES.get(key, ()):
        if alt.startswith("§ "):
            r = legend_rules._section_heading(pc, alt[2:].split())
            if r is not None:
                return _expand([r.x0 - 1.5 * r.height, r.y0, r.x1, r.y1])
    return None


def pick(name: str) -> dict:
    """사람 흉내 — 가르칠 자리를 고른다 (눈가림 없이 읽어서)."""
    import pidcache
    import derive_layout
    import legend_rules
    import detect_symbols as ds
    proj = PROJECTS[name]
    pdf = ROOT / proj["pdf"]
    blob = json.loads((ROOT / "out" / "regression_3p" / (name.replace(" ", "_") + ".json")).read_text())
    rows = blob["result"]["rows"]
    busiest = collections.Counter(r["page_no"] for r in rows if r["tab"] == "FIELD").most_common(1)[0][0]
    _doc, pages = pidcache.load_pages(pdf)
    by = {p.page_no: p for p in pages}
    pc = by[busiest]
    size = [float(pc.width), float(pc.height)]
    teach = {"who": "sim", "notes": None, "legend": {}, "bubbles": [], "drawing": None}
    lay = derive_layout.derive(pages)
    items = {k: v.value for k, v in lay.items.items()}
    fr = derive_layout._frame(derive_layout._form_pages(pages)[0])
    if fr is not None:                    # 사람은 테두리 안쪽 전체를 긋는다 (타이틀블록 포함)
        teach["drawing"] = {"page_no": busiest, "rect": [round(v, 1) for v in fr[:4]], "size": size}
    notes = items.get("regions.notes_area")
    if notes is None:
        from app import pipeline
        notes = pipeline.CFG.get("regions.notes_area")
    teach["notes"] = {"page_no": busiest, "rect": list(notes), "size": size}
    for key in legend_rules.TEACHABLE_HEADINGS:
        lp = legend_rules._page_with(pages, key)
        if lp is None:
            continue
        r = _heading_rect(lp, key)
        if r:
            teach["legend"][key] = {"page_no": lp.page_no, "rect": r,
                                    "size": [float(lp.width), float(lp.height)]}
    outs = [o for o in ds.bubble_outlines(pc) if o.style == "SOLID"]
    shapes = collections.defaultdict(list)
    for o in outs:
        shapes[(round(o.rect.width), round(o.rect.height))].append(o.rect)
    picked = []
    for i, (_shape, rects) in enumerate(sorted(shapes.items(), key=lambda kv: -len(kv[1]))):
        take = 2 if i == 0 else 1
        for r in rects[:take]:
            picked.append({"page_no": busiest, "rect": _expand(list(r)), "size": size})
        if len(picked) >= 4:
            break
    teach["bubbles"] = picked[:4]
    teach["_busiest"] = busiest
    teach["_shapes"] = {f"{k[0]}x{k[1]}": len(v) for k, v in sorted(shapes.items(), key=lambda kv: -len(kv[1]))}
    return teach


def pick_min(name: str) -> dict:
    """최소 입력 — 사람이 화면에서 누를 것만 (범례 장 한 번 · 버블 한 번 · NOTES 글자 한 번)."""
    import pidcache
    import derive_layout
    import legend_rules
    import detect_symbols as ds
    proj = PROJECTS[name]
    blob = json.loads((ROOT / "out" / "regression_3p" / (name.replace(" ", "_") + ".json")).read_text())
    rows = blob["result"]["rows"]
    busiest = collections.Counter(r["page_no"] for r in rows if r["tab"] == "FIELD").most_common(1)[0][0]
    _doc, pages = pidcache.load_pages(ROOT / proj["pdf"])
    by = {p.page_no: p for p in pages}
    pc = by[busiest]
    size = [float(pc.width), float(pc.height)]
    teach = {"who": "sim", "legend": {}, "bubbles": [], "notes": None, "drawing": None, "legend_page": None}
    # 사람은 범례 장을 띄우고 버튼 하나.  화면이 빠진 칸을 말하면(범례가 여러 장 — TC2) 그 칸이 있는
    # 장을 띄우고 한 번 더 누른다 — 서버 미리보기와 같은 판정(가르친 장들에서 `_page_with`).
    marked = []
    first = legend_rules._page_with(pages, "VALVES ACTUATORS") or legend_rules._page_with(pages, "LINE VALVES")
    if first is not None:
        marked.append(first)
        for _round in range(2):
            os.environ["PID_TEACH_BLIND"] = "legend"
            legend_rules.TAUGHT_PAGE = [m.page_no for m in marked]
            missing = [h for h in legend_rules.TEACHABLE_HEADINGS
                       if (legend_rules._page_with(pages, h) or types.SimpleNamespace(page_no=None)).page_no
                       not in legend_rules.TAUGHT_PAGE]
            os.environ["PID_TEACH_BLIND"] = ""
            legend_rules.TAUGHT_PAGE = None
            extra = [legend_rules._page_with(pages, h) for h in missing]
            extra = [x for x in extra if x is not None and all(x.page_no != m.page_no for m in marked)]
            if not extra:
                break
            marked.append(extra[0])
        teach["legend_page"] = [{"page_no": m.page_no, "size": [float(m.width), float(m.height)]} for m in marked]
    # 버블 하나 — 그 장의 FIELD 행 중 버블이 선 첫 것의 한가운데를 누른다
    clicked = None
    for r in rows:
        if r["page_no"] != busiest or r["tab"] != "FIELD" or not r.get("rect"):
            continue
        x, y = (r["rect"][0] + r["rect"][2]) / 2, (r["rect"][1] + r["rect"][3]) / 2
        R = ds.bubble_at(pc, x, y)
        if R is not None:
            clicked = [round(R.x0 - 1.5, 1), round(R.y0 - 1.5, 1), round(R.x1 + 1.5, 1), round(R.y1 + 1.5, 1)]
            teach["_bubble_click"] = [round(x, 1), round(y, 1)]
            break
    if clicked:
        teach["bubbles"] = [{"page_no": busiest, "rect": clicked, "size": size}]
    # NOTES 글자 하나 — 서버의 `/teach/click` 과 **같은 함수** (`derive_layout.notes_from_heading`)
    word = next(((r, t) for r, t in pc.words if t.upper() == "NOTES"), None)
    if word is not None:
        form = derive_layout._form_pages(pages)[0]
        same = [p for p in form if abs(p.width - pc.width) <= 1 and abs(p.height - pc.height) <= 1] or [pc]
        teach["notes"] = {"page_no": busiest, "size": size,
                          "rect": [round(v, 1) for v in derive_layout.notes_from_heading(same, word[0], word[0].height)]}
    teach["_busiest"] = busiest
    teach["_shapes"] = {}
    teach["_clicks"] = len(teach["legend_page"] or []) + (1 if clicked else 0) + (1 if teach["notes"] else 0)
    return teach


def pick_propose(name: str) -> dict:
    """hotfix87 — **제안만 확인** — 서버 `/teach/propose` 와 같은 함수(`app/teach_propose.py`)가 고른 답을
    사람이 고치지 않고 [저장하고 다시 분석] 만 누른 것.  누르는 횟수 = 1 (저장)."""
    import pidcache
    import derive_layout
    import detect_symbols as ds
    from app import teach_propose
    proj = PROJECTS[name]
    _doc, pages = pidcache.load_pages(ROOT / proj["pdf"])
    form = derive_layout._form_pages(pages)[0] or pages
    got = teach_propose.propose(pages, form, ds.RULESET_V3.anchors, ["legend", "bubbles", "notes?"])
    by = {p.page_no: p for p in pages}
    size = lambda n: [float(by[n].width), float(by[n].height)]
    teach = {"who": "sim", "legend": {}, "bubbles": [], "notes": None, "drawing": None, "legend_page": None}
    if got["legend_page"]:
        teach["legend_page"] = [{"page_no": n, "size": size(n)} for n in got["legend_page"]["pages"]]
    if got["bubbles"]:
        teach["bubbles"] = [{"page_no": e["page_no"], "rect": e["rect"], "size": size(e["page_no"])}
                            for e in got["bubbles"]["examples"]]
    if got["notes"]:
        teach["notes"] = {"page_no": got["notes"]["page_no"], "rect": got["notes"]["rect"],
                          "size": size(got["notes"]["page_no"])}
    if got.get("drawing"):
        teach["drawing"] = {"page_no": got["drawing"]["page_no"], "rect": got["drawing"]["rect"],
                            "size": size(got["drawing"]["page_no"])}
    teach["_busiest"] = (got["bubbles"] or {}).get("pages", [None])[0]
    teach["_shapes"] = {}
    teach["_proposal"] = got
    teach["_clicks"] = 1
    return teach


def analyse(name: str, teach: dict, blind: str) -> dict:
    os.environ["PID_TEACH_BLIND"] = blind
    from app import pipeline
    proj = PROJECTS[name]
    t0 = time.time()
    try:
        res = pipeline.analyse(ROOT / proj["pdf"], form_teach={k: v for k, v in teach.items() if not k.startswith("_")})
    except Exception as e:                       # noqa: BLE001
        return {"ok": False, "type": type(e).__name__, "msg": str(e)[:400], "secs": round(time.time() - t0)}
    return {"ok": True, "secs": round(time.time() - t0), "fingerprint": pipeline.fingerprint(res),
            "rows": [{k: r.get(k) for k in ("page_no", "tab", "type", "tag_no", "qty", "scope", "rect",
                                            "description", "line_no", "line_size", "valve_type")} for r in res["rows"]],
            "taught": ((res.get("applied_rules") or {}).get("layout") or {}).get("taught")}


def _match(base_rows, got_rows):
    """같은 행 짝짓기 — 태그가 있으면 (장 · 탭 · TYPE · 태그), 없으면 자리.  자리는 **2pt 안**이면 같다
    (가르친 버블의 둘레는 그려진 곡선이라 규칙의 둘레와 1pt 남짓 다를 수 있다 — 같은 계기다)."""
    def tagged(r):
        return (r["page_no"], r["tab"], r["type"], r.get("tag_no") or "")
    pairs, left_b = [], []
    pool = collections.defaultdict(list)
    for i, r in enumerate(got_rows):
        pool[tagged(r)].append(i)
    used = set()
    for b in base_rows:
        cands = [i for i in pool.get(tagged(b), []) if i not in used]
        if not b.get("tag_no") and b.get("rect"):
            cands = [i for i in cands if got_rows[i].get("rect")
                     and max(abs(x - y) for x, y in zip(b["rect"], got_rows[i]["rect"])) <= 2.0]
        if b.get("rect") and cands:
            cands.sort(key=lambda i: sum(abs(x - y) for x, y in zip(b["rect"], got_rows[i]["rect"] or b["rect"])))
        if cands:
            used.add(cands[0]); pairs.append((b, got_rows[cands[0]]))
        else:
            left_b.append(b)
    left_t = [r for i, r in enumerate(got_rows) if i not in used]
    return pairs, left_b, left_t


def compare(name: str, got: dict) -> dict:
    base = json.loads((ROOT / "out" / "regression_3p" / (name.replace(" ", "_") + ".json")).read_text())["result"]
    pairs, only_b, only_t = _match(base["rows"], got["rows"])
    nb, nt, same = len(base["rows"]), len(got["rows"]), len(pairs)
    diff_scope = sum((b.get("scope") or "") != (r.get("scope") or "") for b, r in pairs)
    diff_qty = sum(str(b.get("qty")) != str(r.get("qty")) for b, r in pairs)
    diff_desc = sum((b.get("description") or "") != (r.get("description") or "") for b, r in pairs if "description" in r)
    diff_line = sum((b.get("line_no") or "") != (r.get("line_no") or "") for b, r in pairs if "line_no" in r)
    key = lambda r: [r["page_no"], r["tab"], r["type"], r.get("tag_no") or "", [round(v) for v in (r.get("rect") or [])]]
    return {"base_rows": nb, "taught_rows": nt, "same": same,
            "recall": round(same / max(1, nb) * 100, 1),
            "precision": round(same / max(1, nt) * 100, 1),
            "only_base": len(only_b), "only_taught": len(only_t),
            "scope_diff": diff_scope, "qty_diff": diff_qty, "description_diff": diff_desc, "line_no_diff": diff_line,
            "qty_sum_base": sum(int(r.get("qty") or 0) for r in base["rows"]),
            "qty_sum_taught": sum(int(r.get("qty") or 0) for r in got["rows"]),
            "same_fingerprint": got["fingerprint"] == base.get("fingerprint"),
            "only_base_types": collections.Counter(r["type"] for r in only_b).most_common(8),
            "only_taught_types": collections.Counter(r["type"] for r in only_t).most_common(8),
            "only_base_pages": collections.Counter(r["page_no"] for r in only_b).most_common(8),
            "only_taught_pages": collections.Counter(r["page_no"] for r in only_t).most_common(8),
            "only_base_sample": [key(r) for r in only_b[:20]], "only_taught_sample": [key(r) for r in only_t[:20]]}


def main() -> int:
    args = sys.argv[1:]
    name = args[0]
    blind = "bubbles,legend,frame"
    out = ROOT / "out" / "hotfix85" / "sim"
    if "--blind" in args:
        blind = args[args.index("--blind") + 1]
    if "--out" in args:
        out = Path(args[args.index("--out") + 1])
    out.mkdir(parents=True, exist_ok=True)
    stem = name.replace(" ", "_") + "_" + (blind.replace(",", "-") or "none")
    full = "--full" in args
    prop = "--propose" in args
    if prop:
        stem += "_propose"
    if full:
        out = out / "full"
        out.mkdir(parents=True, exist_ok=True)
    if "--rescore" in args:                       # 저장된 실행으로 다시 채점만 (분석 없이)
        rep = json.loads((out / f"{stem}.report.json").read_text())
        got = json.loads((out / f"{stem}.run.json").read_text())
        if got.get("ok"):
            rep.update(compare(name, got))
            (out / f"{stem}.report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
        print(json.dumps({k: v for k, v in rep.items() if not k.endswith("_sample")}, ensure_ascii=False)[:1500])
        return 0
    if "--pick-only" in args:
        print(json.dumps(pick_propose(name) if "--propose" in args else pick(name) if full else pick_min(name),
                         ensure_ascii=False))
        return 0
    if "--run" in args:
        teach = json.loads((out / f"{stem}.teach.json").read_text())
        got = analyse(name, teach, blind)
        (out / f"{stem}.run.json").write_text(json.dumps(got, ensure_ascii=False))
        return 0
    # 1) 사람 흉내 (가벼운 자식) → 2) 눈가림 분석 (자식) → 3) 맞대기
    teach = json.loads(subprocess.run([sys.executable, __file__, name, "--pick-only"] + (["--full"] if full else [])
                                      + (["--propose"] if prop else []), capture_output=True,
                                      text=True, check=True, cwd=str(ROOT)).stdout.strip().splitlines()[-1])
    (out / f"{stem}.teach.json").write_text(json.dumps(teach, ensure_ascii=False, indent=1))
    subprocess.run([sys.executable, __file__, name, "--blind", blind, "--out", str(out.parent if full else out), "--run"]
                   + (["--full"] if full else []) + (["--propose"] if prop else []),
                   check=True, cwd=str(ROOT))
    got = json.loads((out / f"{stem}.run.json").read_text())
    if not got.get("ok"):
        rep = {"project": name, "blind": blind, "failed": got}
    else:
        rep = {"project": name, "blind": blind, "secs": got["secs"], "taught": got["taught"],
               "busiest_page": teach["_busiest"], "bubble_shapes_on_page": teach["_shapes"],
               "examples": len(teach["bubbles"]), "legend_taught": sorted(teach["legend"]),
               "legend_page": [x["page_no"] for x in (teach.get("legend_page") or [])], "clicks": teach.get("_clicks"),
               "notes_taught": bool(teach.get("notes")), "drawing_taught": bool(teach.get("drawing")),
               **compare(name, got)}
    (out / f"{stem}.report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if not k.endswith("_sample")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
