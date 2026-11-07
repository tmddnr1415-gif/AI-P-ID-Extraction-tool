"""액추에이터 크기 띠 8.0~40.0 이 TC2(A3·절반 축척)에서 무엇을 막는가.

저장소 파일은 고치지 않는다 — `derive_actuator_stem` 한 함수만 메모리에서
띠를 바꿔 다시 실행하고 그 차이를 보고한다.
"""
import sys, os, json, inspect
sys.path.insert(0, os.getcwd())
from app import pipeline
from app.engine import pidcache, legend_rules as lr

lay_items = json.load(open("out/tc2/head.json"))["applied_rules"]["layout"]["items"]
pipeline.CFG.overlay({it["key"]: it["value"] for it in lay_items if it["source"] == "DERIVED"})
pipeline._rebind_config()
doc, pages = pidcache.load_pages("data/TC2_260821.pdf")

fn_src = inspect.getsource(lr.derive_actuator_stem)
BAND = "if not (8.0 <= min(b.width, b.height) <= 40.0):"
assert BAND in fn_src

def measure(lo):
    patched = fn_src.replace(BAND, "if not (%s <= min(b.width, b.height) <= 40.0):" % lo)
    patched = patched.replace("def derive_actuator_stem(", "def _probe(")
    ns = dict(lr.__dict__)
    exec(compile(patched, "<probe>", "exec"), ns)
    return ns["_probe"](pages, pipeline.CFG)

for lo in ("8.0", "4.0"):
    d = measure(lo)
    print("크기 띠 %s~40.0 → source=%-16s" % (lo, d.source))
    print("   values:", d.values)
    print("   note  :", (d.note or "")[:100])
print()
print("AL NOUF1 이 실제로 유도한 값 (r20 결과):",
      json.load(open("out/round20/run_base.json"))["legend"]["actuator_stem"]["values"])
