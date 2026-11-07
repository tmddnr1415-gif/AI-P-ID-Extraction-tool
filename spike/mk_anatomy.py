"""Bundle session 7's Anatomy engine (ic-3d-builder: refdata.js + anatomy.js + viewer.js) into app/static/valve/anatomy.js.

Changes to the engine (kept small, all marked 'valve36'):
  · the viewer is exposed as AnatomyViewer (valve.js already has a PDF `Viewer` class)
  · select() takes one id or a list → several parts highlighted at once; the rest turn see-through (ghost) so a part inside the body shows
"""
import sys
from pathlib import Path

src, out, commit = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
ref = (src / "refdata.js").read_text(encoding="utf-8")
ana = (src / "anatomy.js").read_text(encoding="utf-8")
vw = (src / "viewer.js").read_text(encoding="utf-8")


def rep(s, old, new, count=1):
    assert s.count(old) >= count, old
    return s.replace(old, new)


vw = rep(vw, "const Viewer = (() => {", "const AnatomyViewer = (() => {")
vw = rep(vw, "window.Viewer = Viewer;", "window.AnatomyViewer = AnatomyViewer;")
vw = rep(vw, "  function select(id) { S.selected = id; dirty = true; }",
         "  function select(id) {   // valve36: one id or a list of ids\n"
         "    S.selected = Array.isArray(id) ? (id.length ? new Set(id) : null) : id; dirty = true;\n  }")
vw = rep(vw, "  const balloons = new Map();",
         "  const balloons = new Map();\n"
         "  const isSel = (id) => S.selected instanceof Set ? S.selected.has(id) : id === S.selected;   // valve36")
vw = rep(vw, "    if (id === S.selected) out = out.map((v, i) => v * 0.6 + [224, 165, 38][i] * 0.4);",
         "    if (isSel(id)) out = out.map((v, i) => v * 0.55 + [232, 120, 20][i] * 0.45);")
vw = rep(vw, "      const ghost = !!S.focus && id !== S.focus;",
         "      const ghost = (!!S.focus && id !== S.focus) || (S.selected instanceof Set && !isSel(id));   // valve36: the rest is see-through, so a part inside (ball, seats) shows")
for a, b in (("id === S.selected || id === S.hovered", "isSel(id) || id === S.hovered"),
             ("b.dot.classList.toggle('sel', id === S.selected)", "b.dot.classList.toggle('sel', isSel(id))"),
             ("bl.label.classList.toggle('sel', it.id === S.selected)", "bl.label.classList.toggle('sel', isSel(it.id))"),
             ("it.id === S.selected ? 'sel' : ''", "isSel(it.id) ? 'sel' : ''")):
    vw = rep(vw, a, b)
assert vw.count("=== S.selected") == 1      # only inside isSel

head = f"""/* Anatomy valve model — the engine of session 7 (3D 계측제어 도구, branch claude/practical-newton-n6bt58, ic-3d-builder/src,
 * commit {commit}): refdata.js + anatomy.js + viewer.js in one file, no library, no CDN, works offline.
 * Built by spike/mk_anatomy.py — do not edit by hand; take a newer engine from session 7 and rebuild.
 * Dimensions are reference / proportional values (RefData 'standard' / 'estimate'): the model shows WHERE a part is, not its size.
 */
"""
out.write_text(head + "\n".join(x.replace("if (typeof module !== 'undefined' && module.exports)", "if (typeof module !== 'undefined' && module.exports && false)")
                                for x in (ref, ana, vw)), encoding="utf-8")
print(out, out.stat().st_size)
