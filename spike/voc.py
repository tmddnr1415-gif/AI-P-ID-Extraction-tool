"""VOC 함 읽기 · 반영 표시 — 회사 Claude Code 가 회차를 시작할 때 쓰는 도구 (hotfix71).

    python spike/voc.py list              # 아직 반영 안 된 VOC (오래된 것부터)
    python spike/voc.py list --all        # 반영된 것까지 상태와 함께
    python spike/voc.py show VOC-…        # 한 건 전부 (voc.json · crop.png 자리)
    python spike/voc.py brief             # 미반영 전부를 한 장의 마크다운으로 (out/voc_brief.md)
    python spike/voc.py resolve VOC-… [VOC-…] --by 이름 --release hotfix72 --note "무엇을 고쳤나"
    python spike/voc.py dup VOC-… --of VOC-… --by 이름
    python spike/voc.py wontfix VOC-… --by 이름 --note "왜 안 고치나"
    python spike/voc.py needinfo VOC-… --by 이름 --note "무엇이 더 필요한가"

어디를 읽나 (전부 훑고 id 로 하나로 센다 — 같은 VOC 가 두 곳에 있어도 한 건):
  ① `--inbox 경로` (여러 번)  ② `PID_VOC_DIR`/inbox  ③ 이 폴더의 `voc/inbox`
  ④ 옆 폴더 `../PID/voc/inbox` · `../PID_dev/voc/inbox` — 운영 PC 에서 개발 폴더(PID_dev)로
     돌 때 운영 서버(PID) 에 쌓인 VOC 를 찾는다.

장부는 **이 폴더의 `voc/ledger.json`** 하나다 (`--ledger` 로 바꿀 수 있다).  반영 표시는 장부에
적고, 그 VOC 가 있던 inbox 폴더에도 `resolution.json` 을 남긴다 — 그래서 운영 화면의 VOC 목록이
"반영됨" 으로 바뀐다.  **이미 처리된 VOC 는 다시 표시하지 않는다** (`--force` 로만) — 중복 반영 방지.
장부는 지우지 않고 쌓기만 한다.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import voc  # noqa: E402


def inboxes(extra) -> list[Path]:
    out = [Path(p) for p in (extra or [])]
    env = os.environ.get(voc.ENV_DIR)
    if env:
        out.append(Path(env) / "inbox")
    out.append(ROOT / "voc" / "inbox")
    for sib in ("PID", "PID_dev"):
        p = ROOT.parent / sib / "voc" / "inbox"
        if p.resolve() != (ROOT / "voc" / "inbox").resolve():
            out.append(p)
    seen, uniq = set(), []
    for p in out:
        k = str(p.resolve()) if p.exists() else str(p)
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def _where(r: dict) -> str:
    c = r.get("context") or {}
    bits = [c.get("project") or "", c.get("revision") and f"Rev.{c.get('revision')}" or "",
            c.get("pdf_name") or "", c.get("page_no") and f"p{c.get('page_no')}" or "",
            c.get("drawing_no") or ""]
    return " · ".join(b for b in bits if b) or "(분석 없음 — 일반 VOC)"


def _rows_line(r: dict) -> str:
    out = []
    for row in r.get("rows") or []:
        i = row.get("identity") or {}
        out.append(f"{i.get('type') or i.get('valve_type') or '?'} {i.get('tag_no') or ''}"
                   f" [{i.get('tab')}] key={i.get('row_key')}")
    return " | ".join(out)


def cmd_list(a, items, ledger):
    rows = list(items.values()) if a.all else voc.pending(items, ledger)
    rows.sort(key=lambda r: r.get("created_ts") or 0)
    if not rows:
        print("반영할 VOC 가 없습니다." if not a.all else "VOC 가 없습니다.")
        print("읽은 곳: " + (", ".join(str(p) for p in inboxes(a.inbox) if p.exists()) or "(없음)"))
        _say_unreadable(a)
        return 0
    for r in rows:
        st = voc.status_of(r, ledger)
        tag = f"[{st.get('status')} {st.get('release') or ''}]" if st else "[미반영]"
        print(f"{r['id']}  {tag}  {r.get('category_label')}  — {r.get('author') or '(이름 없음)'}"
              f" · {r.get('created_at')}")
        print(f"    {_where(r)}")
        print(f"    사유: {r.get('reason')}")
        if r.get("rows"):
            print(f"    행: {_rows_line(r)}")
        if r.get("has_crop"):
            print(f"    조각: {Path(r['_dir']) / 'crop.png'}")
    open_n = len(voc.pending(items, ledger))
    print(f"\n미반영 {open_n}건 · 전체 {len(items)}건 · 장부 {voc.ledger_path(ROOT / 'voc') if not a.ledger else a.ledger}")
    _say_unreadable(a)
    return 0


def _say_unreadable(a):
    """hotfix74 — 읽지 못한 VOC 폴더 (조용히 건너뛰지 않는다)."""
    bad = voc.unreadable(inboxes(a.inbox))
    if bad:
        print(f"\n⚠ 읽지 못한 VOC {len(bad)}건 — 폴더를 열어 사람이 확인하세요 (사유는 그 폴더의 crop.png 등에 남아 있을 수 있습니다):")
        for b in bad[:20]:
            print(f"    {b['dir']}  ({b['why']})")


def cmd_show(a, items, ledger):
    for vid in a.ids:
        r = items.get(vid)
        if r is None:
            print(f"{vid}: 없음")
            continue
        st = voc.status_of(r, ledger)
        print(json.dumps({k: v for k, v in r.items() if not k.startswith("_")},
                         ensure_ascii=False, indent=1, default=str))
        print(f"폴더: {r['_dir']}" + (f" (+{len(r.get('_also', []))}곳)" if r.get("_also") else ""))
        print("상태: " + (json.dumps(st, ensure_ascii=False) if st else "미반영"))
    return 0


def brief_text(items, ledger) -> str:
    rows = voc.pending(items, ledger)
    lines = [f"# VOC — 미반영 {len(rows)}건", "",
             "회사 Claude Code 용 요약.  한 건씩 원인을 재고(§9 · 렌더로 확인), 고친 뒤 "
             "`python spike/voc.py resolve <id> --by <이름> --release <업데이트> --note <무엇을>` "
             "으로 표시한다.  같은 원인의 VOC 는 함께 resolve 하거나 `dup --of` 로 묶는다.", ""]
    for r in rows:
        lines += [f"## {r['id']} — {r.get('category_label')}", "",
                  f"* 작성: {r.get('author') or '(이름 없음)'} · {r.get('created_at')} · "
                  f"{r.get('source_label')}",
                  f"* 자리: {_where(r)}" + (f" · 사각형 {r.get('rect')}" if r.get("rect") else ""),
                  f"* 사유: {r.get('reason')}"]
        if r.get("rows"):
            lines.append(f"* 행: {_rows_line(r)}")
            for row in r["rows"]:
                ai = row.get("ai_values") or {}
                us = row.get("user_values") or {}
                lines.append(f"  * 엔진 값: type={ai.get('type')} scope={ai.get('scope')} "
                             f"qty={ai.get('qty')} · 사람 값: {us or '없음'} · 규칙: "
                             f"{', '.join(row.get('applied_rules') or []) or '-'}")
        mk = r.get("markup") or {}
        if mk:
            lines.append(f"* 마크업: {json.dumps(mk, ensure_ascii=False)[:600]}")
        fail = (r.get("context") or {}).get("failure")
        if fail:
            lines.append(f"* 실패: {fail.get('message')} · 단계 {fail.get('stopped_stage')}")
        if (r.get("context") or {}).get("pdf_path"):
            lines.append(f"* PDF: `{r['context']['pdf_path']}`")
        if r.get("has_crop"):
            lines.append(f"* 조각: `{Path(r['_dir']) / 'crop.png'}`")
        lines.append("")
    return "\n".join(lines)


def cmd_brief(a, items, ledger):
    text = brief_text(items, ledger)
    out = Path(a.out) if a.out else ROOT / "out" / "voc_brief.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(text)
    print(f"\n→ {out}")
    return 0


def cmd_mark(a, items, ledger, status):
    done = voc.mark(items, a.ids, status=status, by=a.by, release=getattr(a, "release", "") or "",
                    note=a.note or "", duplicate_of=getattr(a, "of", "") or "",
                    ledger_file=Path(a.ledger) if a.ledger else voc.ledger_path(ROOT / "voc"),
                    write_marker=not a.no_marker, force=a.force)
    bad = 0
    for vid, msg in done:
        print(f"{vid}: {msg}")
        bad += msg.startswith("없음")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inbox", action="append", help="더 읽을 inbox 폴더")
    ap.add_argument("--ledger", help="장부 파일 (기본: 이 폴더의 voc/ledger.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("--all", action="store_true")
    p = sub.add_parser("show"); p.add_argument("ids", nargs="+")
    p = sub.add_parser("brief"); p.add_argument("--out")
    for name in ("resolve", "dup", "wontfix", "needinfo"):
        p = sub.add_parser(name)
        p.add_argument("ids", nargs="+")
        p.add_argument("--by", required=True, help="반영한 사람 (또는 'Claude Code (회사)')")
        p.add_argument("--note", default="")
        p.add_argument("--force", action="store_true", help="이미 처리된 VOC 도 다시 표시")
        p.add_argument("--no-marker", action="store_true", help="inbox 폴더에 resolution.json 을 쓰지 않음")
        if name == "resolve":
            p.add_argument("--release", required=True, help="반영된 업데이트 이름 (예: hotfix72)")
        if name == "dup":
            p.add_argument("--of", required=True, help="원본 VOC id")
    a = ap.parse_args(argv)
    items = voc.scan(inboxes(a.inbox))
    try:
        ledger = voc.load_ledger(Path(a.ledger) if a.ledger else voc.ledger_path(ROOT / "voc"))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    if a.cmd == "list":
        return cmd_list(a, items, ledger)
    if a.cmd == "show":
        return cmd_show(a, items, ledger)
    if a.cmd == "brief":
        return cmd_brief(a, items, ledger)
    return cmd_mark(a, items, ledger, {"resolve": "RESOLVED", "dup": "DUPLICATE",
                                        "wontfix": "WONTFIX", "needinfo": "NEED_INFO"}[a.cmd])


if __name__ == "__main__":
    sys.exit(main())
