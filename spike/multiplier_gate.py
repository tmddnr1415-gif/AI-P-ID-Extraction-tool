"""[31-B4] 승수 지정 게이트 — 사람 값을 넣고 전량 분석해서 무엇이 움직이나.

    python3 spike/multiplier_gate.py "AL NOUF1" 9      # 유닛 전부에 x9 를 넣어 본다
    python3 spike/multiplier_gate.py SADARA 4 10       # 유닛 10 에만 x4

왜 하네스(`regression_3p.py`)로 안 하나 — 그 하네스는 **아무 것도 넘기지
않는다**.  그것이 게이트 1(사람 값 없을 때 불변)의 보장이므로 건드리지 않고,
사람 값이 있는 경우는 여기서 따로 잰다.

실 DB 를 건드리지 않는다 — `PID_DATA_DIR` 을 버릴 폴더로 돌린다 (17회차).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("PID_DATA_DIR", tempfile.mkdtemp(prefix="pid-gate-"))
os.environ.pop("PID_PROJECT_CONFIG", None)
sys.path.insert(0, str(ROOT))

from app import pipeline  # noqa: E402
sys.path.insert(0, str(ROOT / "spike"))
import identification  # noqa: E402

PROJECTS = {p["name"]: p for p in
            json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]}


def main() -> int:
    name = sys.argv[1]
    mult = int(sys.argv[2])
    units = sys.argv[3:] or None
    proj = PROJECTS[name]
    base = json.loads((ROOT / "out" / "regression_3p" /
                       (name.replace(" ", "_") + ".json")).read_text())["result"]

    # 어느 유닛에 넣을 것인가 — 지정하지 않으면 그 문서의 **모든** 유닛코드
    if units is None:
        units = sorted({t.get("unit_code", "") for t in base["titleblocks"]
                        if t.get("unit_code")})
    table = {u: mult for u in units}
    who = {u: f"시험값 · gate" for u in units}
    print(f"== {name} ==  넣는 값 {table}")

    out = pipeline.analyse(ROOT / proj["pdf"],
                           unit_multipliers={"table": table, "who": who})
    out["fingerprint"] = pipeline.fingerprint(out)

    FP = ("key", "tab", "type", "qty", "valve_type", "vendor_supply",
          "scope", "needs_review", "rect")
    o = {r["key"]: r for r in base["rows"]}
    n = {r["key"]: r for r in out["rows"]}
    moved = {}
    for k in set(o) & set(n):
        for c in FP:
            if o[k].get(c) != n[k].get(c):
                moved[c] = moved.get(c, 0) + 1
    qty_o = sum(int(r["qty"] or 0) for r in base["rows"])
    qty_n = sum(int(r["qty"] or 0) for r in out["rows"])
    filled_o = sum(1 for r in base["rows"] if r["qty"])
    filled_n = sum(1 for r in out["rows"] if r["qty"])
    codes = {}
    for r in out["rows"]:
        for c in (r["evidence"].get("review_codes") or []):
            if "MULTIPLIER" in c:
                codes[c] = codes.get(c, 0) + 1
    print(f"   행 {len(base['rows'])} → {len(out['rows'])}"
          f" · 지문 {base['fingerprint'][:8]} → {out['fingerprint'][:8]}")
    print(f"   Q'ty 합계 {qty_o} → {qty_n} · 값이 있는 행 {filled_o} → {filled_n}")
    print(f"   움직인 칸(지문 대상 열): {moved or '없음'}")
    print(f"   승수 사유: {codes or '없음'}")
    # 축3 을 다시 잰다 — 하네스와 **같은 채점기**를 쓴다 (측정 정의 불변).
    from app.engine import detect_symbols as ds
    anc, tmap = ds.RULESET_V3.anchors, dict(ds.RULESET_V3.field_type_map)
    words = {pc["page_no"]: [] for pc in out.get("pages", [])} or {}
    try:
        base_words = json.loads((ROOT / "out" / "regression_3p" /
                                 (name.replace(" ", "_") + ".json")).read_text())["words"]
        words = {int(k): [(tuple(w[0]), w[-1]) for w in v] for k, v in base_words.items()}
    except Exception:
        pass
    metrics, total = identification.measure(out, words, anc, tmap)
    print(f"   축3 {total} · {{{', '.join(f'{k} {v[0]}/{v[1]}' for k, v in metrics.items())}}}")
    dest = ROOT / "out" / "round31" / f"gate_{name.replace(' ', '_')}.json"
    dest.write_text(json.dumps({"project": name, "table": table,
                                "rows": len(out["rows"]),
                                "fingerprint": out["fingerprint"],
                                "qty_before": qty_o, "qty_after": qty_n,
                                "filled_before": filled_o, "filled_after": filled_n,
                                "moved": moved, "codes": codes,
                                "score": total,
                                "metrics": {k: list(v) for k, v in metrics.items()}},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
