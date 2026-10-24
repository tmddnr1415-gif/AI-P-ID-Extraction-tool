"""ISA 표로 앵커를 유도하면 무엇이 행이 되는가 — 저장된 결과로 미리 잰다 (50회차).

도면 PDF 없이도 정확히 잴 수 있는 이유는 둘이다:

  * `unjudged_symbols` 의 "사전에 없음" 항목은 `detect()` 가 **버블 검증을 이미
    통과시킨** 낱말이다 (`len(hit) == 1` 뒤에 모은다).  사전에 낱말만 있으면
    같은 자리에서 그대로 검출이 된다.
  * 그 문서의 ISA 문자표가 결과 json 에 통째로 들어 있다
    (`description_build.isa_table.first` / `.succeeding`).

    python3 spike/isa_anchor_sim.py
"""
from __future__ import annotations
import json, pathlib, collections, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "app" / "engine"))
import isa_table  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = [("AL NOUF1", "out/round20/run_base.json"), ("TC2", "out/round47/TC2_after.json")]


def table(isa: dict):
    """저장된 표 → 엔진이 쓰는 그 객체.  **규칙을 두 벌로 두지 않는다.**"""
    return isa_table.IsaTable(first={k: tuple(v) for k, v in (isa.get("first") or {}).items()},
                              succeeding={k: tuple(v) for k, v in (isa.get("succeeding") or {}).items()},
                              page_no=isa.get("page_no", 0))


def main() -> int:
    for name, p in DOCS:
        d = json.loads((ROOT / p).read_text()); r = d.get("result", d)
        isa = (r.get("description_build") or {}).get("isa_table") or {}
        T = table(isa)
        first, succ = T.first, T.succeeding
        u = [x for x in r.get("unjudged_symbols", [])
             if x.get("kind") == "INSTRUMENT_TAG" and "사전에 없" in (x.get("why") or "")]
        take, drop = collections.Counter(), collections.Counter()
        for x in u:
            t = (x.get("label") or "").strip()
            (take if T.decompose(t) else drop)[t] += 1
        rows = len(r["rows"])
        print(f"\n===== {name} — 지금 {rows}행 · ISA 표 first {len(first)} · succeeding {len(succ)} =====")
        print(f"  [행이 된다] {sum(take.values())}건")
        for t, n in take.most_common():
            h, s = T.decompose(t)
            print(f"     {t:<6} {n:3d}   {h}({' '.join(first[h])}) + " +
                  " + ".join(f"{c}({' '.join(succ[c])[:22]})" for c in s))
        print(f"  [그대로 미판정] {sum(drop.values())}건")
        for t, n in drop.most_common():
            why = ("첫 글자 %r 가 FIRST LETTER 에 없음" % t[:1]) if t[:1] not in first and t[:2] not in first \
                  else "뒤 글자 " + ",".join(repr(c) for c in t[1:] if c not in succ) + " 가 SUCCEEDING 에 없음"
            if len(t) < 2: why = "한 글자 — 태그로 보지 않음"
            print(f"     {t:<6} {n:3d}   {why}")
        print(f"  → 예상 행 {rows} + {sum(take.values())} = {rows + sum(take.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
