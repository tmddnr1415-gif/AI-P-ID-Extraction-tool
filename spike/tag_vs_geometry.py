"""[E-2] 태그가 준 답 ↔ 거리가 준 답 — 몇 %가 같은가 (28회차 · §10).

    python3 spike/tag_vs_geometry.py out/regression_3p/UAD.json

★ 이것이 §3 검증이다.  AL NOUF1 에서 열 회차 동안 거리·기하로 못 풀던
"이 계기는 어느 기기의 것인가" 를, 태그가 있는 도면에서는 도면이 이미 적어 뒤
있다.  두 답을 나란히 놓고 일치율을 낸다 — 다르면 그것이 발견이다.

무엇을 비교하는가
    거리 답:  행 근거의 `SUBJECT: 도면 기기 라벨 "...", 거리 NN pt`
              그 라벨 글에 들어 있는 **기기 코드**
    태그 답:  그 행의 `tag_no` 의 **계통 부분**

계통 부분은 어떻게 가르는가 — **모양이 가른다** (박은 값이 아니다).
    `00GKB01CL001A` 의 모양은 `D2L3D2 | L2D3 | L1` 이고, 마지막 "글자열+숫자열"
    짝이 그 항목의 종류와 일련번호다.  그 앞이 계통이다 → `00GKB01`.
    기기 `00GKB01BB001` 도 같은 방법으로 `00GKB01` 이 된다.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))
import tags as tagsys  # noqa: E402

CODE = re.compile(r"[A-Z0-9]{6,}")
SUBJ = re.compile(r'SUBJECT: 도면 기기 라벨 “(?P<label>[^”]*)”(?:, 거리 (?P<d>[\d.]+))?')


def system_part(code: str) -> str:
    """마지막 `글자열+숫자열` 짝을 떼어 낸 앞부분 — 그 코드의 계통."""
    runs = re.findall(r"[A-Za-z]+|\d+", code)
    if len(runs) < 4:
        return ""
    # 뒤에서부터: (선택) 글자 한 덩이 · 숫자 한 덩이 · 글자 한 덩이 를 뗀다
    keep = runs[:]
    if keep and keep[-1].isalpha():
        keep = keep[:-1]
    if len(keep) >= 2 and keep[-1].isdigit() and keep[-2].isalpha():
        keep = keep[:-2]
    return "".join(keep)


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "out/regression_3p/UAD.json"
    rows = json.load(open(ROOT / path))["result"]["rows"]
    both = agree = disagree = only_tag = only_geo = neither = 0
    examples = []
    for r in rows:
        tag = (r.get("tag_no") or "").strip()
        srcs = " ".join((r.get("evidence") or {}).get("description_sources") or [])
        m = SUBJ.search(srcs)
        label = m.group("label") if m else ""
        geo_codes = [c for c in CODE.findall(label) if system_part(c)]
        tag_sys = system_part(tag) if tag else ""
        geo_sys = system_part(geo_codes[-1]) if geo_codes else ""
        if tag_sys and geo_sys:
            both += 1
            if tag_sys == geo_sys:
                agree += 1
            else:
                disagree += 1
                if len(examples) < 12:
                    examples.append((r["page_no"], r["type"], tag, tag_sys,
                                     geo_sys, label[:60], m.group("d")))
        elif tag_sys:
            only_tag += 1
        elif geo_sys:
            only_geo += 1
        else:
            neither += 1
    out = ["# [E-2] 태그가 준 답 ↔ 거리가 준 답", "",
           "행 %d" % len(rows), "",
           "| 갈래 | 행 |", "| --- | ---: |",
           "| 둘 다 답을 냄 | **%d** |" % both,
           "| └ **같은 계통** | **%d (%.1f%%)** |" % (agree, 100.0 * agree / max(both, 1)),
           "| └ 다른 계통 | **%d (%.1f%%)** |" % (disagree, 100.0 * disagree / max(both, 1)),
           "| 태그만 답을 냄 (거리는 기기를 못 찾음) | **%d** |" % only_tag,
           "| 거리만 답을 냄 (태그 없음) | %d |" % only_geo,
           "| 둘 다 없음 | %d |" % neither, ""]
    if examples:
        out += ["## 다른 답을 낸 행 (숨기지 않는다)", "",
                "| 장 | TYPE | 태그 | 태그 계통 | 거리 계통 | 거리가 고른 라벨 | 거리 |",
                "| --- | --- | --- | --- | --- | --- | ---: |"]
        for pg, ty, tag, ts, gs, lab, d in examples:
            out.append("| p%d | %s | `%s` | `%s` | `%s` | %s | %s |"
                       % (pg, ty, tag, ts, gs, lab, d or "-"))
    (ROOT / "out" / "round29" / "5_tag_vs_geometry.md").write_text(
        "\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
