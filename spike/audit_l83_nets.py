"""L83 — 그림 그물 감사 (시드 묶음 config/logic_draw_seed/amiral_19va_r1.json.gz · 827장).

들여온 선 id `n<분석선>_<k>` 로, 작성 시뮬레이션의 그물 하나에 분석 선 둘 이상이 섞였는지 센다.
섞인 그물마다 '화살촉 토막'(같은 직선 위에 겹친 짧은 토막 — 같은 블록에 닿아 동작엔 해가 없음)으로만 이어졌는지 가른다.
    python spike/audit_l83_nets.py            # 요약
    python spike/audit_l83_nets.py 0006 0007  # 그 장들의 '화살촉 아닌' 이음 자세히
"""
import gzip
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.logic import draw_sim as ds  # noqa: E402

SEED = ROOT / "config" / "logic_draw_seed" / "amiral_19va_r1.json.gz"


def src(w):
    m = re.match(r"n(\d+)_", w["id"])
    return m.group(1) if m else w["id"]


def overlap(a, b):
    """두 곧은 토막이 같은 직선 위에서 겹치는가 (화살촉 토막)."""
    if len(a["pts"]) != 2 or len(b["pts"]) != 2:
        return False
    (ax0, ay0), (ax1, ay1) = a["pts"]
    (bx0, by0), (bx1, by1) = b["pts"]
    if abs(ax0 - ax1) < .3 and abs(bx0 - bx1) < .3 and abs(ax0 - bx0) < .6:
        return min(max(ay0, ay1), max(by0, by1)) > max(min(ay0, ay1), min(by0, by1)) + .3
    if abs(ay0 - ay1) < .3 and abs(by0 - by1) < .3 and abs(ay0 - by0) < .6:
        return min(max(ax0, ax1), max(bx0, bx1)) > max(min(ax0, ax1), min(bx0, bx1)) + .3
    return False


def main(only):
    docs = json.load(gzip.open(SEED))["docs"]
    mixed, extra, real = 0, 0, []
    for doc in docs:
        if only and doc["name"] not in only:
            continue
        wires = ds._drop_inside([w for w in doc["wires"] if len(w.get("pts") or []) >= 2], doc.get("blocks") or [])
        _, members = ds._nets_of(wires)
        bad = [k for k, ms in members.items() if len({src(wires[i]) for i in ms}) > 1]
        if not bad:
            continue
        ends = [[tuple(w["pts"][0]), tuple(w["pts"][-1])] for w in wires]
        segs = [ds._segs(w) for w in wires]
        inner = ds._DashInner(wires, ends)
        for k in bad:
            ms = members[k]
            lab = {s: s for s in {src(wires[i]) for i in ms}}

            def f(x):
                while lab[x] != x:
                    x = lab[x]
                return x
            joins = []
            for a in ms:
                for b in ms:
                    if a < b and src(wires[a]) != src(wires[b]) and ds._pair_joined(a, b, wires, ends, segs, None, inner):
                        if overlap(wires[a], wires[b]):
                            lab[f(src(wires[a]))] = f(src(wires[b]))
                        else:
                            joins.append((wires[a]["id"], wires[a]["pts"], wires[b]["id"], wires[b]["pts"]))
            mixed += 1
            extra += len(lab) - 1
            if len({f(s) for s in lab}) > 1:
                real.append((doc["name"], k, joins))
    print(f"섞인 그물 {mixed} · 더 붙은 분석 선 {extra} · 화살촉 토막만이 아닌 것 {len(real)}", dict(Counter(r[0] for r in real)))
    if only:
        for r in real:
            print(r[0], r[1])
            for j in r[2][:6]:
                print("   ", j)


if __name__ == "__main__":
    main(sys.argv[1:])
