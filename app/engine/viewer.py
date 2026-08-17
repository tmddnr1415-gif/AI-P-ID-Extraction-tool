"""JSON-driven overlay viewer (docs/design.md Phase 1 PDF viewer, prototyped).

Every spike so far has verified itself by burning boxes into a PNG with
PyMuPDF.  That is a dead end: the picture cannot be filtered, nothing in it can
be clicked, and re-checking one rule means re-rendering the whole sheet.

This writes the two halves separately instead:

    out/viewer/pNNN.png   the sheet, rendered once, with nothing drawn on it
    out/viewer/data.js    every detection as data - rect, kind, evidence
    out/viewer/index.html the viewer

The page is only a backdrop.  All overlays are built in the browser from the
data file, so layers can be toggled, a detection can be clicked to read the
evidence that produced it, and a rule change means rewriting a small JSON file
rather than re-rendering.  That is the structure Phase 1 needs, where the
backdrop becomes a real PDF render and the same overlay layer sits on top of
it unchanged.

The payload is deliberately generic - `pages[].layers[].items[]` with a rect
and a free-form `evidence` dict - so the field-instrument detector can feed the
same viewer without changing it.

Written as `data.js` (`window.PID_DATA = {...}`) rather than `data.json`
because a viewer opened over `file://` cannot `fetch()` a sibling file.  The
content is JSON either way.
"""

from __future__ import annotations

import json
from pathlib import Path

import pymupdf


INDEX_HTML = """<!doctype html>
<meta charset="utf-8">
<title>P&ID detection overlay</title>
<style>
 :root { color-scheme: light dark; --bg:#111; --fg:#eee; --panel:#1c1c1c; }
 * { box-sizing: border-box; }
 body { margin:0; font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;
        background:var(--bg); color:var(--fg); display:flex; height:100vh; }
 #side { width:260px; flex:none; overflow:auto; padding:10px;
         background:var(--panel); border-right:1px solid #333; }
 #stage { flex:1; overflow:auto; position:relative; }
 #wrap { position:relative; transform-origin:0 0; }
 #sheet { display:block; }
 svg { position:absolute; inset:0; width:100%; height:100%; overflow:visible; }
 rect.det { fill:none; stroke-width:1.4; vector-effect:non-scaling-stroke;
            cursor:pointer; }
 rect.det.sel { stroke-width:3; }
 h2 { font-size:12px; text-transform:uppercase; letter-spacing:.08em;
      color:#888; margin:14px 0 6px; }
 label { display:flex; align-items:center; gap:6px; padding:1px 0; }
 .swatch { width:10px; height:10px; flex:none; border:1px solid #0006; }
 select, button { width:100%; background:#262626; color:var(--fg);
                  border:1px solid #444; padding:4px; }
 #evidence { white-space:pre-wrap; word-break:break-word; font-size:12px;
             background:#000; padding:8px; margin-top:6px; min-height:80px; }
 #zoom { display:flex; gap:4px; }
 #zoom button { width:auto; flex:1; }
 .count { color:#888; margin-left:auto; }
</style>
<div id="side">
  <h2>page</h2>
  <select id="page"></select>
  <h2>zoom</h2>
  <div id="zoom">
    <button data-z="-1">&minus;</button>
    <button data-z="0">fit</button>
    <button data-z="1">+</button>
  </div>
  <h2>layers</h2>
  <div id="layers"></div>
  <h2>selection</h2>
  <div id="evidence">click a box</div>
</div>
<div id="stage"><div id="wrap"><img id="sheet"><svg id="ov"></svg></div></div>
<script src="data.js"></script>
<script>
const D = window.PID_DATA;
const $ = s => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
let zoom = 1, page = null, hidden = new Set();

const sel = $("#page");
D.pages.forEach((p, i) => {
  const o = document.createElement("option");
  o.value = i;
  o.textContent = "p" + p.page_no + "  " + (p.label || "");
  sel.appendChild(o);
});
sel.onchange = () => show(+sel.value);

$("#zoom").onclick = e => {
  const z = e.target.dataset.z;
  if (z === undefined) return;
  if (z === "0") zoom = ($("#stage").clientWidth - 20) / page.width;
  else zoom *= (z === "1" ? 1.35 : 1 / 1.35);
  apply();
};

function apply() {
  $("#wrap").style.transform = "scale(" + zoom + ")";
  $("#wrap").style.width = page.width + "px";
  $("#wrap").style.height = page.height + "px";
}

function show(i) {
  page = D.pages[i];
  $("#sheet").src = page.image;
  $("#sheet").width = page.width;
  $("#sheet").height = page.height;
  const ov = $("#ov");
  ov.setAttribute("viewBox", "0 0 " + page.width + " " + page.height);
  ov.innerHTML = "";
  const box = $("#layers");
  box.innerHTML = "";
  for (const layer of page.layers) {
    const g = document.createElementNS(NS, "g");
    g.dataset.layer = layer.name;
    g.style.display = hidden.has(layer.name) ? "none" : "";
    for (const it of layer.items) {
      const r = document.createElementNS(NS, "rect");
      const [x0, y0, x1, y1] = it.rect;
      r.setAttribute("x", x0 * page.scale);
      r.setAttribute("y", y0 * page.scale);
      r.setAttribute("width", Math.max(1, (x1 - x0) * page.scale));
      r.setAttribute("height", Math.max(1, (y1 - y0) * page.scale));
      r.setAttribute("class", "det");
      r.setAttribute("stroke", layer.color);
      r.onclick = ev => {
        document.querySelectorAll("rect.sel").forEach(n => n.classList.remove("sel"));
        r.classList.add("sel");
        $("#evidence").textContent =
          layer.name + "\\n" + JSON.stringify(it, null, 1);
        ev.stopPropagation();
      };
      g.appendChild(r);
    }
    ov.appendChild(g);

    const lab = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !hidden.has(layer.name);
    cb.onchange = () => {
      if (cb.checked) hidden.delete(layer.name); else hidden.add(layer.name);
      g.style.display = cb.checked ? "" : "none";
    };
    const sw = document.createElement("span");
    sw.className = "swatch";
    sw.style.background = layer.color;
    const n = document.createElement("span");
    n.className = "count";
    n.textContent = layer.items.length;
    lab.append(cb, sw, document.createTextNode(layer.name), n);
    box.appendChild(lab);
  }
  zoom = ($("#stage").clientWidth - 20) / page.width;
  apply();
}
show(0);
</script>
"""

# Stable colours so a kind keeps its colour across pages and across spikes.
PALETTE = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231", "#911eb4", "#42d4f4",
    "#f032e6", "#bfef45", "#fabed4", "#469990", "#dcbeff", "#9a6324",
    "#800000", "#aaffc3", "#808000", "#ffd8b1", "#000075", "#a9a9a9",
]


def colour_for(name: str) -> str:
    return PALETTE[sum(ord(c) for c in name) % len(PALETTE)]


def write(pages_payload: list[dict], out_dir: Path, pages_by_no: dict,
          zoom: float = 1.35) -> Path:
    """Render backdrops and write the viewer.

    `pages_payload` is [{page_no, label, layers:[{name, items:[{rect, ...}]}]}].
    Item rects are in PDF display space; the viewer scales them by the same
    factor the backdrop was rendered at, so the JSON stays resolution-free.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {"pages": []}
    for page in pages_payload:
        pc = pages_by_no[page["page_no"]]
        img = out_dir / f"p{page['page_no']:03d}.png"
        if not img.exists():
            pc.pixmap(pymupdf.Rect(0, 0, pc.width, pc.height), zoom=zoom).save(img)
        layers = []
        for layer in page["layers"]:
            layers.append({
                "name": layer["name"],
                "color": layer.get("color") or colour_for(layer["name"]),
                "items": layer["items"],
            })
        payload["pages"].append({
            "page_no": page["page_no"],
            "label": page.get("label", ""),
            "image": img.name,
            "scale": zoom,
            "width": round(pc.width * zoom),
            "height": round(pc.height * zoom),
            "layers": layers,
        })
    (out_dir / "data.js").write_text(
        "window.PID_DATA = " + json.dumps(payload, indent=1) + ";\n",
        encoding="utf-8")
    (out_dir / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    return out_dir / "index.html"
