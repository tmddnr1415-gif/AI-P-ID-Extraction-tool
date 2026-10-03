"""35회차 [C] — worktree 의 엔진에서 상수를 지운다 (본선은 건드리지 않는다).

    python3 spike/r35_apply.py /tmp/r35_strip out/round35_strip_list.md

한 일 셋 — 전부 worktree 파일만:
  1. 목록의 dataclass 기본값 39 → `_M("<모듈>.<필드>", <원래 값>)`  (복원 목록에
     있으면 원래 값, 아니면 sentinel)
  2. `projectconfig.load()` 가 `R35_STRIP_KEYS`(json 목록)의 잎을 sentinel 로 바꾼다
  3. 조립 함수·`_rebind_config` 의 변환기(float/tuple/int/re.compile)가 sentinel 을
     통과시킨다 — 값으로 *쓰는* 순간에만 터지게
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

wt = Path(sys.argv[1]); lst = Path(sys.argv[2]).read_text()
MOD = {"app/engine/detect_symbols.py": "ds", "app/engine/detect_valves.py": "dv",
       "app/engine/extract_titleblocks.py": "tb"}

# 1. dataclass 기본값
rows = re.findall(r"^\| `([^:`]+):(\d+)` \| `([a-z_]+)` \| `(.+?)` \| ", lst, re.M)
patched = []
for f, line, field, orig in rows:
    p = wt / f; src = p.read_text().splitlines()
    i = int(line) - 1
    l = src[i]
    m = re.match(r"^(\s+%s\s*:\s*\w+\s*=\s*)([^#]+?)(\s*(#.*)?)$" % field, l)
    assert m, (f, line, l)
    src[i] = f'{m.group(1)}_M("{MOD[f]}.{field}", {m.group(2).strip()}){m.group(3)}'
    p.write_text("\n".join(src) + "\n"); patched.append(f"{MOD[f]}.{field}")
for f in MOD:
    p = wt / f; s = p.read_text()
    if "from .missing import" not in s and "from missing import" not in s:
        # 이 파일들은 `import detect_symbols as ds` 처럼 맨 이름으로도 import 된다
        s = s.replace("from __future__ import annotations\n",
                      "from __future__ import annotations\n"
                      "try:\n    from .missing import M as _M, pf as _pf, pi as _pi, pt as _pt\n"
                      "except ImportError:\n    from missing import M as _M, pf as _pf, pi as _pi, pt as _pt\n", 1)
    # 3. 조립 함수의 변환기
    s = re.sub(r"\bfloat\(cfg\.(get_or|get)\(", r"_pf(cfg.\1(", s)
    s = re.sub(r"\btuple\(cfg\.(get_or|get)\(", r"_pt(cfg.\1(", s)
    s = re.sub(r"\bint\(cfg\.(get_or|get)\(", r"_pi(cfg.\1(", s)
    p.write_text(s)

# 2. config 잎 → sentinel (load 안에서)
p = wt / "app/engine/projectconfig.py"; s = p.read_text()
s = s.replace(
    "    data = yaml.safe_load(p.read_text(encoding=\"utf-8\"))\n    if not isinstance(data, dict):\n        raise ConfigError(f\"{p}: expected a mapping at the top level\")\n    return ProjectConfig(p, data)",
    "    data = yaml.safe_load(p.read_text(encoding=\"utf-8\"))\n    if not isinstance(data, dict):\n        raise ConfigError(f\"{p}: expected a mapping at the top level\")\n"
    "    _keys = os.environ.get(\"R35_STRIP_KEYS\")\n    if _keys:\n        import json as _json\n"
    "        try:\n            from .missing import strip_config, restored\n        except ImportError:\n            from missing import strip_config, restored\n"
    "        strip_config(data, _json.loads(Path(_keys).read_text()), restored())\n"
    "    return ProjectConfig(p, data)", 1)
assert "R35_STRIP_KEYS" in s
# rect/pair 도 통과
s = s.replace("    def rect(self, dotted: str) -> tuple:\n        v = self.get(dotted)\n",
              "    def rect(self, dotted: str) -> tuple:\n        v = self.get(dotted)\n        if type(v).__name__ == 'Missing':\n            return v\n", 1)
s = s.replace("    def pair(self, dotted: str) -> tuple:\n        v = self.get(dotted)\n",
              "    def pair(self, dotted: str) -> tuple:\n        v = self.get(dotted)\n        if type(v).__name__ == 'Missing':\n            return v\n", 1)
if "import os" not in s.split("\n\n")[0] and "\nimport os\n" not in s:
    s = s.replace("import yaml\n", "import os\nimport yaml\n", 1)
p.write_text(s)

# 3b. pipeline._rebind_config 의 re.compile / glyph_sizes
p = wt / "app/pipeline.py"; s = p.read_text()
s = s.replace("import detect_symbols as ds        # noqa: E402",
              "import detect_symbols as ds        # noqa: E402\nfrom missing import pre as _pre, Missing as _Missing  # noqa: E402  (35회차 worktree)", 1)
n = 0
for k in ("formats.drawing_no", "formats.date", "formats.revision"):
    old = f're.compile(CFG.get("{k}"))'
    if old in s: s = s.replace(old, f'_pre(CFG.get("{k}"))'); n += 1
s = s.replace('    ds.KNOWN_GLYPH_SIZES = tuple(tuple(float(v) for v in pair)\n                                 for pair in CFG.get("vendor_marks.glyph_sizes"))',
              '    _gs = CFG.get("vendor_marks.glyph_sizes")\n    ds.KNOWN_GLYPH_SIZES = _gs if isinstance(_gs, _Missing) else tuple(tuple(float(v) for v in pair) for pair in _gs)', 1)
p.write_text(s)
print("dataclass patched", len(patched), "| re.compile guarded", n)
