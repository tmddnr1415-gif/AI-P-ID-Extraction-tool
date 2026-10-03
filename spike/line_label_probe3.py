"""hotfix36 — 저장된 결과의 행에 라인 번호를 붙여 본다 (전량 재분석 없이 · 파이프라인 함수 그대로).
    python3 spike/line_label_probe3.py <result.json> <pdf> <쪽…>"""
import json, pathlib, sys, dataclasses
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app" / "engine"))
import pidcache, pipe_graph, projectconfig, describe_axis as daxis, line_labels as LL   # noqa
from app import pipeline as P                                                             # noqa
CFG = projectconfig.load()
res = json.load(open(sys.argv[1]))["result"]; pdf = sys.argv[2]; wanted = [int(a) for a in sys.argv[3:]]
_doc, pages = pidcache.load_pages(pdf)
style = dict(pipe_graph.derive_line_styles(pages, CFG).values)
area = CFG.rect("regions.drawing_area")
by_no = {pc.page_no: pc for pc in pages}
fields = {f.name for f in dataclasses.fields(P.Row)}
rows = [P.Row(**{k: v for k, v in r.items() if k in fields}) for r in res["rows"] if r["page_no"] in wanted]
for r in rows:
    r.rect = tuple(r.rect); r.line_no = ""; r.evidence.pop("line", None)
labels_by_page, geo, tap_of = {}, {}, {}
for pno in wanted:
    pc = by_no[pno]
    g = daxis.page_runs(pc, style); geo[pno] = (g[0], daxis.bridge_collinear(g[1], style['join_slack'], g[2]))
    labels_by_page[pno] = LL.find_labels(pc, g[0], style["join_slack"], area)
    for r in rows:
        if r.page_no == pno and not ((r.evidence.get("axis") or {}).get("ev") or {}).get("run"):
            run, _how = daxis.pick_tap(r.rect, g[0], g[1], style["join_slack"], style.get("min_run") or style["join_slack"])
            if run: tap_of[r.key] = run
facts = P._attach_line_numbers(rows, labels_by_page, style["join_slack"], tap_of, geo)
print("facts", {k: v for k, v in facts.items() if k != "pages"})
for pno in wanted:
    print(f"\n-- p{pno}  라벨 {len(labels_by_page[pno])} (깃대로 런 정한 것 {sum(1 for L in labels_by_page[pno] if L.pole)})")
    for r in sorted([r for r in rows if r.page_no == pno], key=lambda r: (r.rect[1], r.rect[0])):
        L = r.evidence.get("line") or {}
        print(f"  {r.type:6s} {r.tag_no or '-':14s} rect={[round(v) for v in r.rect]} line={r.line_no or '-':16s} via={L.get('via','')!s:6s} cand={L.get('candidates','')} spec={L.get('spec','')!r}")
