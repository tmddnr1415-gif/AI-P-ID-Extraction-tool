"""hotfix36 — `line_labels` 모듈을 몇 장에서 돌려 본다.  python3 spike/line_label_probe2.py <pdf> <쪽…>"""
import collections, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "app" / "engine"))
import pidcache, pipe_graph, projectconfig, describe_candidates as dcand, describe_axis as daxis   # noqa
from app.engine import line_labels as LL                                                           # noqa
CFG = projectconfig.load()
pdf = sys.argv[1]; wanted = [int(a) for a in sys.argv[2:]]
_doc, pages = pidcache.load_pages(pdf)
style = dict(pipe_graph.derive_line_styles(pages, CFG).values)
by_no = {pc.page_no: pc for pc in pages}
allp = {}
for pno in wanted:
    pc = by_no[pno]
    runs0, _leaders = dcand.local_runs(pc, style)
    runs = daxis.bridge_collinear(runs0, style["join_slack"], daxis.standard_break(runs0, style["join_slack"]))
    labels = LL.find_labels(pc, runs, style["join_slack"])
    allp[pno] = labels
    print(f"\n== p{pno}: 라벨 {len(labels)} · 런 {len(runs)}")
    for L in labels:
        print(f"   {L.text:22s} dir {L.dir} box {[round(v,1) for v in L.box]} run {L.run and tuple(round(v,1) if isinstance(v,float) else v for v in L.run)} spec {L.spec!r}")
print("\n모양", collections.Counter(L.shape() for ls in allp.values() for L in ls).most_common(8))
print("체계 모양", LL.systematic(allp))
