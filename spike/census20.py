"""51회차 [B] — 요구 20종을 네 프로젝트에서 센다.

세 갈래로 가른다
    ㉠ 도면에 인쇄돼 있고 행도 있다
    ㉡ 도면에 인쇄돼 있는데 행이 없다      <- 고칠 자리
    ㉢ 도면에 인쇄돼 있지 않다             <- 없는 것이다

★ ㉢ 를 무엇으로 증명하는가
    50회차가 PG·TG 에 쓴 방법 그대로다 — 버블 안 1~5글자 낱말은 앵커가
    아니어도 전부 `unjudged_symbols` 에 담기므로, **그 목록에 0건이면
    버블 안에는 없다.**  다만 그것만으로는 "도면 어디에도 없다" 가 아니다
    (버블 밖 주석일 수 있다).  그래서 PDF 가 있는 문서에서는 **인쇄된 낱말을
    직접 세어** 두 번째 증거로 삼는다 (`--pdf`).

    python3 spike/census20.py                      # 저장된 결과로
    python3 spike/census20.py --pdf data/pid_total.pdf --name "AL NOUF1"
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 사용자 지시의 20종.  **판정 어휘가 아니다** — 세는 표의 머리글일 뿐이고,
# 검출이 무엇을 태그로 보는지는 여전히 그 도면의 ISA 문자표가 정한다 (50회차).
WANT = ["PIT", "TIT", "TI", "PI", "TG", "PG", "FE", "FIT", "SG", "LIT", "LS",
        "MOV", "XV", "PCV", "PV", "LV", "TV", "FV", "AIT", "TW"]
# 사용자가 같은 것이라고 확인해 준 짝 (PV=PCV · LV=LCV · TV=TCV · FV=FCV).
SAME = {"PV": "PCV", "LV": "LCV", "TV": "TCV", "FV": "FCV"}

STORED = [("AL NOUF1", "out/round20/run_base.json", "20회차 · 1037행"),
          ("SADARA", "out/round20/run_sadara.json", "20회차 · 82행 ⚠ 지금 기준선은 86"),
          ("TC2", "out/round47/TC2_after.json", "47회차 · 811행"),
          ("UAD", "out/round45/UAD_before.json", "43회차 · 192행 ⚠ 지금 기준선은 198")]


def displayed(r: dict) -> str:
    from app import pipeline
    return pipeline.type_display(r, r.get("evidence") or {})


def count_rows(res: dict) -> collections.Counter:
    c = collections.Counter()
    for x in res.get("rows", []):
        c[displayed(x)] += 1
    return c


def for_type(c: collections.Counter, t: str) -> int:
    """`MOV(GLOBE)` 꼴을 접어 그 TYPE 의 행 수."""
    if t == "AIT":                      # 발주처 표기 선택으로 Analyzer 가 된다
        return c.get("Analyzer", 0) + c.get("AIT", 0)
    return sum(n for k, n in c.items() if k == t or k.startswith(t + "("))


def unjudged(res: dict) -> collections.Counter:
    return collections.Counter((x.get("label") or "").strip()
                               for x in res.get("unjudged_symbols", []))


def printed_words(pdf: str) -> collections.Counter:
    """그 PDF 가 **인쇄한** 낱말 (도면 영역 안).  ㉢ 의 두 번째 증거."""
    from app.engine import pidcache
    _d, pages = pidcache.load_pages(pdf)
    c = collections.Counter()
    for pc in pages:
        for _r, t in pidcache.tokens(pc.words):
            if re.fullmatch(r"[A-Z]{1,5}", t or ""):
                c[t] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf")
    ap.add_argument("--name", default="")
    a = ap.parse_args()

    if a.pdf:
        w = printed_words(a.pdf)
        print("# %s — 인쇄된 낱말 (1~5 대문자 · 전 장)" % (a.name or a.pdf))
        for t in WANT + sorted(SAME.values()):
            print("  %-5s %5d" % (t, w.get(t, 0)))
        out = ROOT / "out" / "round51" / ("printed_%s.json" % (a.name or "doc").replace(" ", "_"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(w), ensure_ascii=False, indent=1))
        print("→", out)
        return 0

    for name, path, note in STORED:
        f = ROOT / path
        if not f.exists():
            print("\n===== %s — 저장된 결과 없음 (%s)" % (name, path))
            continue
        res = json.loads(f.read_text())
        res = res.get("result", res)
        rows, uj = count_rows(res), unjudged(res)
        print("\n===== %s  (%s · 미판정 %d)" % (name, note, sum(uj.values())))
        print("  %-6s %6s %6s  %s" % ("TYPE", "행", "미판정", "판정"))
        for t in WANT:
            n = for_type(rows, t)
            u = uj.get(t, 0)
            mark = "㉠ 행 있음" if n else ("㉡ 인쇄됐는데 행 0" if u else "㉢ 버블 안 0건")
            extra = ""
            if t in SAME:
                alt = SAME[t]
                extra = "  (같은 것: %s 행 %d · 미판정 %d)" % (
                    alt, for_type(rows, alt), uj.get(alt, 0))
            print("  %-6s %6d %6d  %s%s" % (t, n, u, mark, extra))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
