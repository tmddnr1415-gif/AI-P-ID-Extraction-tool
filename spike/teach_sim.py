"""hotfix85 — **가르치기만으로 읽히는가** 를 이미 읽히는 모든 문서에서 잰다.

    python3 spike/teach_sim.py <프로젝트 이름> [--blind bubbles,legend,frame] [--out out/hotfix85/sim]

1. **사람 흉내** (가벼운 자식 프로세스) — 그 문서에서 사람이 그을 자리를 고른다:
   · 도면 영역 = 그 문서의 테두리 · NOTES = 그 문서의 NOTES 영역
   · 범례 칸 제목 셋 = 그 장에 인쇄된 머리말 글자를 감싼 사각형 (+2pt 여유)
   · 버블 예시 = 계기가 가장 많은 장에서 **가장 흔한 버블 모양 둘 + 다른 모양 하나씩**(최대 4) (+2pt)
2. **눈가림 분석** (`PID_TEACH_BLIND`) — 프로그램이 그 항목을 스스로 찾지 않고 가르친 것만 쓴다.
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
    if items.get("regions.drawing_area"):
        teach["drawing"] = {"page_no": busiest, "rect": items["regions.drawing_area"], "size": size}
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
            "rows": [{k: r.get(k) for k in ("page_no", "tab", "type", "tag_no", "qty", "scope", "rect")} for r in res["rows"]],
            "taught": ((res.get("applied_rules") or {}).get("layout") or {}).get("taught")}


def compare(name: str, got: dict) -> dict:
    base = json.loads((ROOT / "out" / "regression_3p" / (name.replace(" ", "_") + ".json")).read_text())["result"]
    key = lambda r: (r["page_no"], r["tab"], r["type"], r.get("tag_no") or "", tuple(round(v) for v in (r["rect"] or [])))
    B = collections.Counter(key(r) for r in base["rows"])
    T = collections.Counter(key(r) for r in got["rows"])
    same = sum((B & T).values())
    bmap = {key(r): r for r in base["rows"]}
    diff_scope = diff_qty = 0
    for r in got["rows"]:
        b = bmap.get(key(r))
        if b is None:
            continue
        diff_scope += (b.get("scope") or "") != (r.get("scope") or "")
        diff_qty += str(b.get("qty")) != str(r.get("qty"))
    only_b = list((B - T).elements())
    only_t = list((T - B).elements())
    return {"base_rows": sum(B.values()), "taught_rows": sum(T.values()), "same": same,
            "recall": round(same / max(1, sum(B.values())) * 100, 1),
            "precision": round(same / max(1, sum(T.values())) * 100, 1),
            "only_base": len(only_b), "only_taught": len(only_t),
            "scope_diff": diff_scope, "qty_diff": diff_qty,
            "same_fingerprint": got["fingerprint"] == base.get("fingerprint"),
            "only_base_types": collections.Counter(k[2] for k in only_b).most_common(8),
            "only_taught_types": collections.Counter(k[2] for k in only_t).most_common(8),
            "only_base_sample": [list(k) for k in only_b[:12]], "only_taught_sample": [list(k) for k in only_t[:12]]}


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
    if "--pick-only" in args:
        print(json.dumps(pick(name), ensure_ascii=False))
        return 0
    if "--run" in args:
        teach = json.loads((out / f"{stem}.teach.json").read_text())
        got = analyse(name, teach, blind)
        (out / f"{stem}.run.json").write_text(json.dumps(got, ensure_ascii=False))
        return 0
    # 1) 사람 흉내 (가벼운 자식) → 2) 눈가림 분석 (자식) → 3) 맞대기
    teach = json.loads(subprocess.run([sys.executable, __file__, name, "--pick-only"], capture_output=True,
                                      text=True, check=True, cwd=str(ROOT)).stdout.strip().splitlines()[-1])
    (out / f"{stem}.teach.json").write_text(json.dumps(teach, ensure_ascii=False, indent=1))
    subprocess.run([sys.executable, __file__, name, "--blind", blind, "--out", str(out), "--run"],
                   check=True, cwd=str(ROOT))
    got = json.loads((out / f"{stem}.run.json").read_text())
    if not got.get("ok"):
        rep = {"project": name, "blind": blind, "failed": got}
    else:
        rep = {"project": name, "blind": blind, "secs": got["secs"], "taught": got["taught"],
               "busiest_page": teach["_busiest"], "bubble_shapes_on_page": teach["_shapes"],
               "examples": len(teach["bubbles"]), "legend_taught": sorted(teach["legend"]),
               **compare(name, got)}
    (out / f"{stem}.report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if not k.endswith("_sample")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
