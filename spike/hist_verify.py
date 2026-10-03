"""[D] 이력 표 유도 검증 — 유도값이 손입력값을 재현하는가 · REV 가 읽히는가.

    python3 spike/hist_verify.py <pdf>

두 가지를 나눠 답한다 (이력 표는 **자리**를 주고 글리프 사전은 **문자**를 준다):

  ① 유도된 다섯 칸의 값과 지금 설정값의 대조
  ② 두 경로로 REV 를 읽어 장별 결과를 센다
       · 설정값 그대로 (지금 파이프라인이 AL NOUF1 에서 하는 것)
       · 유도값을 얹고  (지금 파이프라인이 낯선 양식에서 하는 것)

`_fit_layout` 은 프로필이 **그 문서의 것이고 기하를 적고 있으면** 유도값을
쓰지 않는다.  AL NOUF1 이 그 경우이므로 ②의 두 경로가 갈리는 것이 곧
"이 규칙이 손입력값을 재현하는가" 의 답이다.
"""
from __future__ import annotations

import collections
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

# 엔진 모듈은 **맨 이름**으로 가져온다 — `app.engine.x` 로 가져오면 파이프라인이
# 들고 있는 것과 다른 모듈 객체가 되어 `_rebind_config` 이 얹은 값이 안 보인다.
import pidcache                               # noqa: E402
import derive_layout as dl                    # noqa: E402
import extract_titleblocks as tb              # noqa: E402
from app import pipeline                      # noqa: E402

HIST = ("hist_rule_y", "hist_rule_x0_max", "hist_rule_x1_min",
        "hist_rev_col", "hist_date_col", "hist_row_inset")


def read_all(pages, tag: str) -> None:
    lib = tb.build_glyph_library(pages, tb.LAYOUT)
    rows = collections.Counter(len(tb.history_rows(pc, tb.LAYOUT)) for pc in pages)
    revs, conf, method = collections.Counter(), collections.Counter(), collections.Counter()
    for pc in pages:
        row = tb.extract_page(pc, lib, tb.LAYOUT)
        revs[row["rev"] or "(없음)"] += 1
        conf[row["rev_confidence"]] += 1
        method[row["rev_method"]] += 1
    got = sum(v for k, v in revs.items() if k != "(없음)")
    print("### %s" % tag)
    print("   글리프 사전 %s" % ({k: len(v) for k, v in sorted(lib.items())} or "비어 있음"))
    print("   이력 행 수 분포 %s" % dict(sorted(rows.items())))
    print("   REV 읽힌 장 %d/%d — %s" % (got, len(pages), dict(revs)))
    print("   방법 %s · 신뢰도 %s" % (dict(method), dict(conf)))


def main() -> int:
    pdf = sys.argv[1]
    doc, pages = pidcache.load_pages(pdf)
    print("## %s (%d쪽)" % (Path(pdf).name, len(pages)))

    lay = dl.derive(pages, pipeline.CFG)
    vals = lay.values()
    print("### 유도 대 설정")
    derived_hist = {}
    for k in HIST:
        key = "title_block." + k
        got = vals.get(key)
        try:
            cur = pipeline.CFG.get(key)
        except Exception:
            cur = None
        if got is not None:
            derived_hist[key] = got
        print("   %-18s 유도 %-24s 설정 %-24s%s"
              % (k, got, cur, "" if got is not None else "  ← 유도하지 않음"))
    for n in lay.notes:
        if "hist" in n:
            print("   note:", n)

    read_all(pages, "설정값 그대로")

    def apply(values, tag):
        if not values:
            return
        pipeline.CFG.overlay(values)
        pipeline._rebind_config()
        for pc in pages:            # 이력 행 캐시는 쪽 객체가 든다 (21회차)
            if hasattr(pc, "_hist_rows"):
                del pc._hist_rows
        read_all(pages, tag)

    apply(derived_hist, "이력 칸만 유도값으로")
    # 낯선 양식에서 파이프라인이 실제로 하는 것 — `_fit_layout` 은 유도값을
    # **전부** 얹는다 (프로필이 그 문서의 것이 아니면).  AL NOUF1 에서는 하나도
    # 얹지 않으므로, 이 줄은 그 규칙이 맞는지를 재는 것이지 그 문서의 결과가
    # 아니다.
    apply(vals, "유도값 전체를 얹고 (낯선 양식 경로)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
