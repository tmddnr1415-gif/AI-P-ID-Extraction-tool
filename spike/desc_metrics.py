"""Description 지표 — 식별 가능성(주 지표) · 토큰 F1(참고) · ④→② 전환율.

5회차부터 주 지표는 **식별 가능성**이다: 발주처 문장과 우리 문장을 같은
도면·같은 TYPE 안에서 겹치는 낱말이 가장 많은 순으로 짝짓고, 변수어 ·
위치어 · 나머지 낱말(기기·계통)이 전부 통하면 "그 문장만으로 도면에서 그
계기를 찾아갈 수 있다"로 센다.  F1 은 참고로만 남긴다 — 5회차 프롬프트가
정한 대로, F1 하락은 회귀 실패가 아니다.

원본 채점기(이전 회차, /tmp)는 남아 있지 않아 재구현이다.  그래서 **같은
채점기로 현행과 신규를 다 재고 차이만 읽는다** — 절대값은 이전 기록
(F1 74.6 · 완전일치 34 · 식별 30.9%)과 짝짓기 방식이 달라 어긋날 수 있고,
그 어긋남도 보고에 적는다.

    python3 spike/desc_metrics.py run.json [비교_run.json]
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
import client_lists

VARIABLE = {"PRESSURE", "TEMPERATURE", "LEVEL", "FLOW", "DIFFERENTIAL",
            "ANALYSIS", "SPEED", "VIBRATION", "POSITION"}
POSITION = {"SUCTION", "DISCHARGE", "INLET", "OUTLET", "UPSTREAM",
            "DOWNSTREAM", "RETURN", "SUPPLY"}
ORDINAL = re.compile(r"^[A-Z]$|^\d+$")


def toks(s):
    return [t for t in re.sub(r"[^A-Z0-9#&/]+", " ", str(s or "").upper()).split()
            if t]


def pieces(ts):
    var = {t for t in ts if t in VARIABLE}
    pos = {t for t in ts if t in POSITION}
    rest = [t for t in ts if t not in VARIABLE and t not in POSITION
            and not ORDINAL.match(t)]
    return var, pos, rest


def match_rows(ours, client):
    """(도면, TYPE) 칸 안에서 낱말 겹침이 큰 순으로 짝짓는다 (탐욕)."""
    ours_by = collections.defaultdict(list)
    for r in ours:
        if r.get("tab") and r["tab"] != "FIELD":
            continue
        ours_by[(str(r.get("drawing_no") or "").strip(),
                 str(r.get("type") or "").strip().upper())].append(r)
    pairs, unmatched_client = [], []
    used = set()
    for c in client:
        key = (c["pid"].strip(), str(c["type"]).strip().upper())
        cands = [r for r in ours_by.get(key, ()) if id(r) not in used]
        if not cands:
            unmatched_client.append(c)
            continue
        ct = collections.Counter(toks(c["desc"]))
        best = max(cands, key=lambda r: (
            sum((collections.Counter(toks(r["description"])) & ct).values()),
            -cands.index(r)))
        used.add(id(best))
        pairs.append((c, best))
    return pairs, unmatched_client


def score(ours, client):
    pairs, missing = match_rows(ours, client)
    tp = fp = fn = exact = 0
    ident = 0
    blocked = collections.Counter()
    for c, r in pairs:
        ct, rt = collections.Counter(toks(c["desc"])), \
                 collections.Counter(toks(r["description"]))
        inter = sum((ct & rt).values())
        tp += inter
        fp += sum(rt.values()) - inter
        fn += sum(ct.values()) - inter
        if toks(c["desc"]) == toks(r["description"]):
            exact += 1
        cv, cp, cr = pieces(toks(c["desc"]))
        rv, rp, rr = pieces(toks(r["description"]))
        why = []
        if cv != rv:
            why.append("변수어")
        if cp != rp:
            why.append("위치어")
        cset, rset = set(cr), set(rr)
        if cset and (len(cset & rset) * 2 < len(cset)):
            why.append("기기·계통")
        if not r["description"]:
            why = ["공란"]
        if why:
            blocked[tuple(why)] += 1
        else:
            ident += 1
    fn += sum(len(toks(c["desc"])) for c in missing)
    n = len(pairs) + len(missing)
    P = 100 * tp / (tp + fp) if tp + fp else 0.0
    R = 100 * tp / (tp + fn) if tp + fn else 0.0
    F1 = 2 * P * R / (P + R) if P + R else 0.0
    return {"n_client": n, "paired": len(pairs), "missing": len(missing),
            "exact": exact, "identifiable": ident,
            "identifiable_pct": round(100 * ident / n, 1) if n else 0.0,
            "token_precision": round(P, 1), "token_recall": round(R, 1),
            "token_f1": round(F1, 1),
            "blocked_top": collections.Counter(
                {" · ".join(k): v for k, v in blocked.items()}).most_common(8)}


def main():
    if not (ROOT / "data" / "CZE_Field_Instrument.xlsx").exists():
        print("발주처 리스트가 없습니다 — 이 측정은 발주처 자료를 가진 "
              "기계에서만 됩니다.")
        return
    rows_all, _cols = client_lists.load("FIELD")
    client = [c for c in rows_all
              if c.get("pid") and not c.get("strike")]
    for path in sys.argv[1:]:
        rows = json.load(open(path))["rows"]
        got = score(rows, client)
        print(f"== {path}")
        for k, v in got.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
