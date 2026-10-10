"""[D] 상수 전수 조사 — 코드를 읽어 파라미터를 세고, 어디서 오는지 가른다.

세 갈래로 가른다.
    유도   그 도면에서 재서 정한다 (범례 · 도면틀 · 도면 본문)
    설정   config 파일이 값을 준다 — 사람이 적은 값이다
    상수   코드에 박혀 있고 아무도 안 바꾼다

그리고 **못 쟀을 때 어떻게 되는가**를 함께 적는다.  폴백이면 조용한 실패
지점이고(15회차), 예외면 시끄러운 실패다.  조용한 쪽이 위험하다.

    python3 spike/constant_survey.py           # 표를 낸다
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE = ROOT / "app" / "engine"


def dataclass_fields(path: Path, name: str):
    """dataclass 의 필드 이름과 기본값을 소스에서 읽는다."""
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == name:
            out = []
            for st in node.body:
                if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                    try:
                        val = ast.literal_eval(st.value) if st.value else None
                    except Exception:
                        val = "<식>"
                    out.append((st.target.id, val))
            return out
    return []


def config_backed(path: Path, builder: str):
    """config 가 실제로 덮는 **필드** — 그 모듈의 Layout 조립 함수를 읽는다.

    키 이름으로 찾으면 안 된다: 조립 함수마다 이름 짓는 방식이 달라
    (`vendor_marks.above` → `mark_above`) 키를 세면 0 이 나온다.  그래서
    **필드에 들어가는 식이 config 를 읽는가**를 본다.
    """
    tree = ast.parse(path.read_text())
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == builder), None)
    if fn is None:
        return set()
    out = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.keyword) and node.arg:
            try:
                ast.literal_eval(node.value)        # 리터럴이면 코드 고정
            except Exception:
                out.add(node.arg)                  # 식이면 바깥 값을 읽는다
    return out


def derived_keys(run_json: Path):
    """그 분석이 도면에서 실제로 잰 항목."""
    if not run_json.exists():
        return {}
    blob = json.loads(run_json.read_text())
    r = blob.get("result", blob)
    out = {}
    lay = (r.get("applied_rules") or {}).get("layout") or {}
    for it in lay.get("items") or []:
        out[it["key"]] = it.get("source")
    for k, v in (r.get("legend") or {}).items():
        if isinstance(v, dict):
            out["legend." + k] = v.get("source")
    m = r.get("multipliers") or {}
    if m:
        out["unit_multipliers"] = m.get("source")
    return out


def main() -> int:
    groups = [
        ("계기 검출", ENGINE / "detect_symbols.py", "Layout", "_layout_from_config"),
        ("밸브 검출", ENGINE / "detect_valves.py", "ValveLayout", "_layout"),
        ("타이틀블록", ENGINE / "extract_titleblocks.py", "Layout", "_layout_from_config"),
    ]
    runs = {n: ROOT / "out" / "regression_3p" / (n + ".json")
            for n in ("AL_NOUF1", "SADARA", "TC2")}
    der = {n: derived_keys(p) for n, p in runs.items()}

    total = cfg_total = 0
    print("# 상수 전수 — dataclass 기본값\n")
    for label, path, cls, builder in groups:
        fields = dataclass_fields(path, cls)
        cfg = config_backed(path, builder)
        total += len(fields)
        cfg_total += sum(1 for f, _ in fields if f in cfg)
        print("## %s — `%s.%s` · %d 항목 (config 가 덮을 수 있는 것 %d)"
              % (label, path.name, cls, len(fields),
                 sum(1 for f, _ in fields if f in cfg)))
        for f, v in fields:
            over = f in cfg
            print("   %-26s %-30s %s" % (f, str(v)[:30], "config 가능" if over else "코드 고정"))
        print()
    print("dataclass 기본값 합계 %d · 그중 config 로 덮을 수 있는 것 %d" % (total, cfg_total))
    print()
    print("# 그 도면에서 실제로 잰 것 (분석 결과)\n")
    keys = sorted({k for d in der.values() for k in d})
    if keys:
        print("%-38s %-14s %-14s %-14s" % ("항목", "AL NOUF1", "SADARA", "TC2"))
        for k in keys:
            print("%-38s %-14s %-14s %-14s"
                  % (k, der["AL_NOUF1"].get(k, "-"), der["SADARA"].get(k, "-"),
                     der["TC2"].get(k, "-")))
    else:
        print("(아직 회귀 하네스 결과가 없습니다 — `spike/regression_3p.py` 를 먼저 돌리세요)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
