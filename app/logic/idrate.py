"""식별률 — 이 묶음을 얼마나 읽었나, 무엇을 못 읽었나 (L24).

예전에는 읽기가 실패해도 조용했다 — 1A5J 를 옛 코드로 읽으면 시트 이름 10/63 · FM/TO 칸이 다른 칸 글자로 뒤섞이고
· 시트 사이 연결 0 인데 분석은 '완료' 로 끝났다.  그래서 분석이 끝날 때마다(그리고 사람이 마크업을 얹을 때마다)
네 가지를 세어 화면 첫 줄에 말한다.  하나라도 90% 아래면 붉게 말하고, 못 읽은 것 하나하나를 목록으로 내 사람이
그 자리로 가서 마크업으로 넣게 한다.

  * 시트 이름 — Logic 표 시트 중 시트 이름을 읽은 장
  * FROM/TO 칸 — 신호가 있는 행(설명 · KKS 가 있는 행)의 FM/TO 칸 중 뜻이 읽힌 칸 (시트-행 참조 · 낱말).
    비어 있는 칸은 도면이 안 적은 것일 수 있어 비율에 넣지 않고 따로 센다.
  * 연결 — 이 묶음을 가리키는 참조 중 가리킨 시트가 묶음에 있는 것
  * 게이트 — 블록 중 종류를 정한 것 (연결 기호 제외)

판정을 하지 않는다 — 결과를 세기만 한다.
"""
from __future__ import annotations

import re

from . import refs as RF

TARGET = 0.90
MAX_ITEMS = 400


def _readable(v: str) -> bool:
    """낱말로 읽힌 칸인가 — `?` 가 없고 글자가 둘 이상 (`HMI` · `FROM DRIVE` · `LOGIC`)."""
    v = (v or "").strip()
    return bool(v) and "?" not in v and len(re.sub(r"[^A-Z0-9]", "", v.upper())) >= 2


def measure(res: dict) -> dict:
    sheets = [s for s in res.get("sheets", []) if not s.get("library")]
    by_no = {s["sheet_no"]: s for s in sheets if s.get("sheet_no")}
    bundle = RF.Bundle(by_no)
    items = []
    c = {k: [0, 0] for k in ("sheet", "cell", "link", "gate")}       # [읽음, 모두]
    empty = 0
    for s in sheets:
        pg = s["page"]
        c["sheet"][1] += 1
        if s.get("sheet_no"):
            c["sheet"][0] += 1
        else:
            items.append({"kind": "SHEET", "page": pg, "text": "시트 이름을 읽지 못했습니다", "at": None})
        for t in s.get("table", []):
            field = "fm" if t["side"] == "L" else "to"
            if not (t.get("desc") or t.get("kks")):
                continue
            box = t.get(field + "_box")
            v = (t.get(field) or "").strip()
            if not v:
                if box:
                    empty += 1
                continue
            c["cell"][1] += 1
            if RF.find(v, known=by_no) or _readable(v):
                c["cell"][0] += 1
            else:
                items.append({"kind": "FROM" if t["side"] == "L" else "TO", "page": pg, "row": t["n"],
                              "text": f"{t['n']}행 {'FM' if t['side'] == 'L' else 'TO'} 칸 '{v}' 을 읽지 못했습니다",
                              "at": box})
        for r in s.get("rows", []):
            if r["side"] != "L":
                continue
            ref = r.get("ref")
            if not ref or ref.get("other_bundle"):
                continue
            c["link"][1] += 1
            if ref.get("page") is not None:
                c["link"][0] += 1
            else:
                t = next((x for x in s.get("table", []) if x["side"] == "L" and x["n"] == r["n"]), {})
                items.append({"kind": "LINK", "page": pg, "row": r["n"],
                              "text": f"{r['n']}행 FM {r.get('fm')} — 묶음에 {ref.get('sheet')} 장이 없습니다",
                              "at": t.get("fm_box")})
        for bid, b in s.get("blocks", {}).items():
            if b.get("func") == "CONNECTOR":
                continue
            c["gate"][1] += 1
            if b.get("func") != "UNKNOWN":
                c["gate"][0] += 1
            else:
                items.append({"kind": "GATE", "page": pg, "block": bid, "text": f"블록 {bid} 종류를 정하지 못했습니다",
                              "at": b.get("bbox")})
    for it in items:
        s = next((x for x in sheets if x["page"] == it["page"]), {})
        it["sheet_no"] = s.get("sheet_no") or ""
    rate = {k: (round(v[0] / v[1], 4) if v[1] else None) for k, v in c.items()}
    if not c["link"][1] and len(sheets) >= 2 and c["cell"][1]:
        # 표는 읽었는데 시트 사이 연결이 하나도 없다 — 참조 꼴이나 시트 이름을 못 읽은 것이다 (옛 1A5J 가 이랬다)
        rate["link"] = 0.0
        items.insert(0, {"kind": "LINK", "page": sheets[0]["page"], "sheet_no": "", "at": None,
                         "text": "시트 사이 연결(FM → 다른 시트의 행)을 하나도 찾지 못했습니다 — 시트 이름 또는 참조 꼴을 못 읽었습니다"})
    got = sum(v[0] for v in c.values())
    tot = sum(v[1] for v in c.values())
    overall = round(got / tot, 4) if tot else None
    low = [k for k, v in rate.items() if v is not None and v < TARGET]
    return {"rate": rate, "counts": {k: {"ok": v[0], "all": v[1]} for k, v in c.items()},
            "overall": overall, "target": TARGET, "low": low, "empty_cells": empty,
            "unread": len(items), "items": items[:MAX_ITEMS]}
