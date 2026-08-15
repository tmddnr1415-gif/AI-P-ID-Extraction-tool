#!/usr/bin/env python3
"""검토 UI에서 내보낸 피드백을 review_log.md와 판독 규칙에 반영한다.

리뷰 UI(review-ui/index.html)에서 "피드백 내보내기"로 받은 feedback_*.json을 넣으면:

  1. review_log.md 맨 위에 이번 검토 항목을 타임스탬프와 함께 추가한다.
     (언제 · 누가 · 무엇을 · 왜 고쳤는지)
  2. --apply-rules 를 주면 규칙 코멘트를 rules/extraction_guide.md 하단
     "검토 피드백에서 도출된 규칙" 절에 추가한다. 기본은 화면에 제안만 출력한다.
     규칙 문장을 최종적으로 다듬는 건 사람의 몫이다.

사용:
  python3 scripts/apply_feedback.py ~/Downloads/feedback_run_20260815_2230.json
  python3 scripts/apply_feedback.py feedback.json --apply-rules
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "review_log.md"
GUIDE = ROOT / "rules/extraction_guide.md"
RULE_ANCHOR = "## 검토 피드백에서 도출된 규칙"

CATEGORY_LABEL = {
    "wrong_value": "값 오류", "description_error": "DESCRIPTION 오류", "type_error": "TYPE 오류",
    "qty_error": "수량 오류", "typical_error": "TYPICAL TYPE 오류", "format_error": "형식 오류",
    "other": "기타", "false_positive": "오탐", "miss": "누락",
}


def esc(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "\\|").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("feedback", type=Path)
    ap.add_argument("--apply-rules", action="store_true",
                    help="규칙 코멘트를 rules/extraction_guide.md에 실제로 추가")
    args = ap.parse_args()

    fb = json.loads(args.feedback.read_text(encoding="utf-8"))
    cells = fb.get("cell_corrections", [])
    dels = fb.get("row_deletions", [])
    adds = fb.get("row_additions", [])
    total = fb.get("stats", {}).get("total_rows", 0)

    if not (cells or dels or adds):
        print("[i] 수정 내역이 없는 피드백입니다. 기록할 것이 없습니다.")
        return 0

    # ── 요약 ────────────────────────────────────────────────
    cat = collections.Counter([c["category"] for c in cells]
                              + ["false_positive"] * len(dels) + ["miss"] * len(adds))
    by_col = collections.Counter(c["column_label"] for c in cells)
    by_drawing = collections.Counter(
        [c["row_key"].get("pid_no", "") for c in cells]
        + [d["row_key"].get("pid_no", "") for d in dels]
        + [a["values"].get("pid_no", "") for a in adds])

    print(f"[i] {fb['run_id']} · 검토자 {fb['reviewer']}")
    print(f"[i] 전체 {total}행 중 셀 수정 {len(cells)} · 오탐 {len(dels)} · 누락 {len(adds)}")
    if total:
        touched = len({c["row_index"] for c in cells} | {d["row_index"] for d in dels})
        print(f"[i] 행 정확도(수정 없이 통과한 행 비율): {100 * (total - touched) / total:.1f}%")
    print("[i] 오류 유형:", ", ".join(f"{CATEGORY_LABEL.get(k, k)} {v}" for k, v in cat.most_common()))
    if by_col:
        print("[i] 오류가 잦은 컬럼:", ", ".join(f"{k} {v}" for k, v in by_col.most_common(5)))
    if by_drawing:
        print("[i] 오류가 잦은 도면:", ", ".join(f"{k} {v}" for k, v in by_drawing.most_common(3)))

    # ── review_log.md ───────────────────────────────────────
    entry = render_entry(fb, cells, dels, adds, cat, by_col)
    prepend_entry(LOG, entry)
    print(f"\n[✓] {LOG.relative_to(ROOT)} 에 검토 기록 추가")

    # ── 규칙 제안 ───────────────────────────────────────────
    rules = dedupe_rules(cells, dels, adds)
    print(f"\n[i] 규칙 코멘트 {len(rules)}건 (중복 제거 후):")
    for r in rules:
        print(f"    - {r['rule']}")
        print(f"      근거: {r['count']}건 · {', '.join(sorted(r['categories']))}")

    if args.apply_rules:
        n = append_rules(GUIDE, rules, fb)
        print(f"\n[✓] {GUIDE.relative_to(ROOT)} 에 규칙 {n}건 추가")
        print("[!] 추가된 문장은 초안입니다. 사람이 다듬어 본문 절로 승격시키세요.")
    else:
        print("\n[i] 규칙을 실제로 반영하려면 --apply-rules 를 붙여 다시 실행하세요.")

    print("\n다음: 규칙을 다듬은 뒤 extract_instruments.py 를 다시 돌려 개선 여부를 확인하세요.")
    return 0


def render_entry(fb, cells, dels, adds, cat, by_col) -> str:
    when = fb.get("reviewed_at", dt.datetime.now().isoformat())[:16].replace("T", " ")
    L = [f"## {when} — {fb['run_id']}", "",
         f"- 검토자: {fb['reviewer']}",
         f"- 대상: {fb.get('stats', {}).get('total_rows', '?')}행"
         + (f" (`{fb['source_xlsx']}`)" if fb.get("source_xlsx") else ""),
         f"- 결과: 셀 수정 {len(cells)} · 오탐 삭제 {len(dels)} · 누락 추가 {len(adds)}",
         f"- 오류 유형: " + ", ".join(f"{CATEGORY_LABEL.get(k, k)} {v}" for k, v in cat.most_common()),
         ""]
    if by_col:
        L += [f"- 오류가 잦은 컬럼: " + ", ".join(f"{k}({v})" for k, v in by_col.most_common(5)), ""]

    if cells:
        L += ["### 셀 수정", "",
              "| 도면 | 컬럼 | 모델 출력 | 정확한 값 | 유형 | 사유 | 향후 규칙 |",
              "|---|---|---|---|---|---|---|"]
        for c in cells:
            L.append(f"| {esc(c['row_key'].get('pid_no'))} | {esc(c['column_label'])} "
                     f"| {esc(c['before'])} | {esc(c['after'])} "
                     f"| {CATEGORY_LABEL.get(c['category'], c['category'])} "
                     f"| {esc(c['reason'])} | {esc(c['rule_comment'])} |")
        L.append("")
    if dels:
        L += ["### 오탐 (삭제)", "", "| 도면 | TYPE | DESCRIPTION | 사유 | 향후 규칙 |", "|---|---|---|---|---|"]
        for d in dels:
            k = d["row_key"]
            L.append(f"| {esc(k.get('pid_no'))} | {esc(k.get('type'))} | {esc(k.get('description'))} "
                     f"| {esc(d['reason'])} | {esc(d['rule_comment'])} |")
        L.append("")
    if adds:
        L += ["### 누락 (추가)", "", "| 도면 | TYPE | DESCRIPTION | 사유 | 향후 규칙 |", "|---|---|---|---|---|"]
        for a in adds:
            v = a["values"]
            L.append(f"| {esc(v.get('pid_no'))} | {esc(v.get('type'))} | {esc(v.get('description'))} "
                     f"| {esc(a['reason'])} | {esc(a['rule_comment'])} |")
        L.append("")
    return "\n".join(L)


def dedupe_rules(cells, dels, adds) -> list[dict]:
    """같은 규칙 코멘트를 묶어 근거 건수와 함께 돌려준다."""
    bucket: dict[str, dict] = {}
    for item, cat in ([(c, c["category"]) for c in cells]
                      + [(d, "false_positive") for d in dels]
                      + [(a, "miss") for a in adds]):
        rule = re.sub(r"\s+", " ", item.get("rule_comment", "")).strip()
        if not rule:
            continue
        key = rule.lower()
        e = bucket.setdefault(key, {"rule": rule, "count": 0, "categories": set()})
        e["count"] += 1
        e["categories"].add(CATEGORY_LABEL.get(cat, cat))
    return sorted(bucket.values(), key=lambda e: -e["count"])


def append_rules(guide: Path, rules: list[dict], fb) -> int:
    if not guide.exists():
        print(f"[!] {guide} 가 없습니다.", file=sys.stderr)
        return 0
    text = guide.read_text(encoding="utf-8")
    if RULE_ANCHOR not in text:
        text += f"\n\n{RULE_ANCHOR}\n"
    head, _, tail = text.partition(RULE_ANCHOR)
    tail = tail.replace("_(아직 없음)_\n", "").replace("_(아직 없음)_", "")

    when = fb.get("reviewed_at", dt.datetime.now().isoformat())[:10]
    lines = [f"\n### {when} · {fb['run_id']} 검토 ({fb['reviewer']})", ""]
    for r in rules:
        lines.append(f"- {r['rule']}  \n  _근거: {r['count']}건 · {', '.join(sorted(r['categories']))}_")
    lines.append("")
    guide.write_text(head + RULE_ANCHOR + tail.rstrip() + "\n" + "\n".join(lines), encoding="utf-8")
    return len(rules)


def prepend_entry(log: Path, entry: str) -> None:
    """최신 기록이 위로 오도록 헤더 아래에 끼워 넣는다."""
    if not log.exists():
        log.write_text("# 검토 기록\n\n", encoding="utf-8")
    text = log.read_text(encoding="utf-8")
    marker = "<!-- 새 기록은 이 아래에 추가됩니다 -->"
    if marker in text:
        head, _, tail = text.partition(marker)
        log.write_text(f"{head}{marker}\n\n{entry}\n{tail.lstrip()}", encoding="utf-8")
    else:
        lines = text.splitlines(keepends=True)
        i = 1 if lines and lines[0].startswith("#") else 0
        log.write_text("".join(lines[:i]) + "\n" + entry + "\n" + "".join(lines[i:]), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
