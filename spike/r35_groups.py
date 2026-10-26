"""35회차 [E] — 묶음 하나만 지우고 돈다 (되살리기 사슬 없이 · 회당 1번).

    python3 spike/r35_groups.py

되살린 상태(= 전부 복원)에서 **한 묶음만** 지운 채 탐침을 돌린다.  완주하면 지문을
탐침 기준 `0087c236` 과 대조해 ㉠/㉡/㉢, 멈추면 첫 상수 이름으로 ㉣.
20회 상한이 다 찬 뒤 남은 묶음을 [E] 로 가르는 방법이다 — 되살리기가 아니라 "지웠을 때".
"""
from __future__ import annotations

import json, re, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
from r35_replay import run_once  # noqa: E402

lst = (ROOT / "out/round35_strip_list.md").read_text()
MOD = {"app/engine/detect_symbols.py": "ds", "app/engine/detect_valves.py": "dv", "app/engine/extract_titleblocks.py": "tb"}
dc = [f"{MOD[f]}.{field}" for f, _, field, _ in re.findall(r"^\| `([^:`]+):(\d+)` \| `([a-z_]+)` \| `(.+?)` \| ", lst, re.M)]
cfg = ["cfg." + k for k in json.load(open(ROOT / "out/round35/strip_keys.json")) if k != "project.code"]
ALL = dc + cfg
GROUPS = {
    "formats.revision": ["cfg.formats.revision"],
    "anchors(25)": [n for n in cfg if n.startswith("cfg.anchors.")],
    "valves.legend_fallback(15)": [n for n in cfg if n.startswith("cfg.valves.legend_fallback.")],
    "unit_multiplier_fallback(3)": [n for n in cfg if n.startswith("cfg.unit_multiplier_fallback.")],
    "qty_note(3)": [n for n in cfg if n.startswith("cfg.qty_note.")],
    "valves.actuator_reach/offaxis/tag_reach(3)": ["cfg.valves.actuator_reach", "cfg.valves.actuator_offaxis", "cfg.valves.tag_reach"],
    "vendor_marks.glyph_sizes": ["cfg.vendor_marks.glyph_sizes"],
    "vendor_marks.x_slack+note_row_tol": ["cfg.vendor_marks.x_slack", "cfg.vendor_marks.note_row_tol"],
    "dv dataclass(15)": [n for n in dc if n.startswith("dv.")],
    "ds dataclass 나머지": [n for n in dc if n.startswith("ds.") and n not in
        ("ds.cap_span", "ds.side_slack", "ds.mark_side", "ds.brk_min_marks", "ds.brk_max_gap", "ds.brk_bridge", "ds.brk_min_span", "ds.brk_corner_tol", "ds.anchor_slack")],
    "tb.title_line_tol": ["tb.title_line_tol"],
}
out_p = ROOT / "out/round35/groups.json"
out = json.loads(out_p.read_text()) if out_p.exists() else {}
for name, members in GROUPS.items():
    if name in out: continue
    restored = [n for n in ALL if n not in members]
    t0 = time.time()
    r = run_once(str(ROOT.parent.parent / "tmp/r35_probe.pdf") if False else "/tmp/r35_probe.pdf", restored, True)
    dump = r.pop("rows_dump", None)
    if dump is not None:
        (ROOT / "out/round35" / f"rows_group_{re.sub(r'[^A-Za-z0-9_]+', '_', name)}.json").write_text(json.dumps(dump))
    r.pop("trace_tail", None); r.pop("legend_sources", None)
    out[name] = {"members": members, **r}
    out_p.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"group": name, "n": len(members), **{k: v for k, v in r.items() if k in ("ok", "rows", "fingerprint", "qty", "missing", "seconds", "moved")}}, ensure_ascii=False), flush=True)
