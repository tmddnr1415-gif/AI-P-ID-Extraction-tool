"""G1 결함 재현 — 발주처 몫만 적은 프로필이 '내 프로필' 로 골라지면 AL NOUF1 좌표로 읽는가."""
import sys, os, collections
sys.path.insert(0, '.'); sys.path.insert(0, 'app/engine')
from pathlib import Path
os.environ.pop("PID_PROJECT_CONFIG", None)
from app import pipeline as P
from app.engine import projectconfig, pidcache
import extract_titleblocks as tb
doc, pages = pidcache.load_pages('data/TC2_260821.pdf', only=tuple(range(1, 13)))
code = P._document_code(pages)
import tempfile
probe = Path(tempfile.mkdtemp()) / 'project_probe.yaml'
probe.write_text(f"project:\n  code: '{code}'\n  name: PROBE (client-only profile)\n")
PC = P.projectconfig
orig = PC.profiles
PC.profiles = lambda *a, **k: orig(*a, **k) + [{"code": code, "path": probe, "name": "PROBE"}]
with P._own_config():
    info = P._select_profile(code); P._rebind_config()
    lay = P._fit_layout(pages)
    lib = tb.build_glyph_library(pages, tb.LAYOUT)
    rows = [tb.extract_page(pd, lib, tb.LAYOUT) for pd in pages]
    print("code", code, "| profile", info["path"], "switched", info["switched"])
    print("same/states_geometry:", lay["reason"][:90])
    print("dwg_no_region now:", tb.LAYOUT.dwg_no_region if hasattr(tb.LAYOUT, "dwg_no_region") else P.CFG.get("title_block.dwg_no_region"))
    print("drawing numbers read:", sum(1 for r in rows if r["drawing_no"]), "/", len(rows))
