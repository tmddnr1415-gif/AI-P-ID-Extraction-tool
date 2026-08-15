#!/usr/bin/env python3
"""Symbol & Legend 도면을 판독해 rules/symbol_legend.md 를 만든다.

계기 판독보다 먼저 실행한다. 여기서 만들어진 문서가 extract_instruments.py의
시스템 프롬프트에 통째로 들어가 판독 기준이 된다.

생성한 md는 사람이 계속 고쳐 쓰는 규칙 문서이므로, 기존 파일을 말없이 덮어쓰지
않는다. --force 없이는 기존 파일이 있으면 중단하고, --force를 주면 기존 파일을
타임스탬프 붙여 백업한 뒤 교체한다.

사용:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 scripts/parse_legend.py --pages 2,3,4,5
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _claude import MODEL_DEFAULT, call_structured, image_block  # noqa: E402

SCHEMA = {
    "type": "object",
    "properties": {
        "first_letters": {
            "type": "array",
            "description": "태그 첫 글자와 측정 변수 대조표",
            "items": {"type": "object", "properties": {
                "letter": {"type": "string"},
                "measured_variable": {"type": "string"},
            }, "required": ["letter", "measured_variable"], "additionalProperties": False},
        },
        "succeeding_letters": {
            "type": "array",
            "description": "태그 뒤 글자와 기능 대조표",
            "items": {"type": "object", "properties": {
                "letter": {"type": "string"},
                "function": {"type": "string"},
            }, "required": ["letter", "function"], "additionalProperties": False},
        },
        "instrument_symbols": {
            "type": "array",
            "description": "계기 심볼(원/사각/육각, 테두리선 유무)과 설치 위치 해석",
            "items": {"type": "object", "properties": {
                "symbol": {"type": "string", "description": "심볼 생김새 설명"},
                "meaning": {"type": "string"},
                "mounting": {"type": "string", "description": "Field / Local panel / DCS 등"},
            }, "required": ["symbol", "meaning", "mounting"], "additionalProperties": False},
        },
        "signal_lines": {
            "type": "array",
            "description": "신호선 종류와 의미",
            "items": {"type": "object", "properties": {
                "appearance": {"type": "string"},
                "meaning": {"type": "string"},
            }, "required": ["appearance", "meaning"], "additionalProperties": False},
        },
        "valve_fail_positions": {
            "type": "array",
            "description": "FO / FC / FL / LO / LC 등 밸브 상태 기호",
            "items": {"type": "object", "properties": {
                "code": {"type": "string"},
                "meaning": {"type": "string"},
            }, "required": ["code", "meaning"], "additionalProperties": False},
        },
        "tag_numbering": {
            "type": "string",
            "description": "KKS 태그 넘버링 체계 설명 (브레이크다운 레벨, 예시 포함)",
        },
        "vendor_scope": {
            "type": "string",
            "description": "Vendor Scope / Package 범위를 도면에서 어떻게 표시하는지",
        },
        "abbreviations": {
            "type": "array",
            "description": "도면에서 쓰는 약어",
            "items": {"type": "object", "properties": {
                "abbr": {"type": "string"}, "meaning": {"type": "string"},
            }, "required": ["abbr", "meaning"], "additionalProperties": False},
        },
        "unreadable": {
            "type": "array",
            "description": "해상도 등의 이유로 판독하지 못한 영역",
            "items": {"type": "string"},
        },
    },
    "required": ["first_letters", "succeeding_letters", "instrument_symbols", "signal_lines",
                 "valve_fail_positions", "tag_numbering", "vendor_scope", "abbreviations", "unreadable"],
    "additionalProperties": False,
}

SYSTEM = """당신은 P&ID의 Symbol & Legend 도면을 판독해 기계가 쓸 수 있는 기준표로 옮기는 계장 엔지니어입니다.

첨부된 이미지는 한 프로젝트의 Symbol & Legend 도면 전체입니다(전체 도면 1장 + 확대 타일 여러 장).
타일은 같은 도면의 부분 확대이므로 중복 항목은 한 번만 기재합니다.

원칙:
- 도면에 실제로 적힌 것만 옮깁니다. 일반적인 ISA 관례로 보충하지 않습니다.
- 표(첫 글자/뒤 글자 조합표)는 빠짐없이 전부 옮깁니다.
- 글자가 뭉개져 확신할 수 없으면 추측하지 말고 unreadable에 그 항목을 적습니다."""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=ROOT / "outputs/pages/manifest.json")
    ap.add_argument("--pages", default="2,3,4,5", help="Symbol & Legend 페이지 번호")
    ap.add_argument("--out", type=Path, default=ROOT / "rules/symbol_legend.md")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--effort", default="high")
    ap.add_argument("--force", action="store_true", help="기존 symbol_legend.md를 백업 후 교체")
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 요청 구성만 점검")
    args = ap.parse_args()

    if args.out.exists() and not args.force and not args.dry_run:
        print(f"[!] {args.out} 가 이미 있습니다. 사람이 고친 규칙을 덮어쓰지 않기 위해 중단합니다.\n"
              f"    교체하려면 --force 를 붙이세요 (기존 파일은 백업됩니다).", file=sys.stderr)
        return 1

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    want = {int(p) for p in args.pages.split(",") if p.strip()}
    pages = [p for p in manifest["pages"] if p["page"] in want]
    if not pages:
        print(f"[!] manifest에 {sorted(want)} 페이지가 없습니다. pdf_to_images.py 를 먼저 실행하세요.", file=sys.stderr)
        return 1

    content = []
    for p in pages:
        content.append({"type": "text", "text": f"── {p['drawing_no']} · {p['title']} (p{p['page']}) 전체 ──"})
        content.append(image_block(ROOT / p["image"]))
        for t in p["tiles"]:
            content.append({"type": "text", "text": f"   확대 타일 r{t['row']}c{t['col']}"})
            content.append(image_block(ROOT / t["image"]))
    content.append({"type": "text", "text":
                    "위 Symbol & Legend 도면에서 계기 판독에 필요한 기준표를 모두 추출하세요."})

    n_img = sum(1 for c in content if c["type"] == "image")
    print(f"[i] 레전드 {len(pages)}쪽 · 이미지 {n_img}장 전송")
    if args.dry_run:
        print("[dry-run] API 호출 없이 종료합니다.")
        return 0

    data = call_structured(SYSTEM, content, SCHEMA, model=args.model, effort=args.effort)

    if args.out.exists():
        bak = args.out.with_suffix(f".{dt.datetime.now():%Y%m%d_%H%M}.bak.md")
        shutil.copy2(args.out, bak)
        print(f"[i] 기존 파일 백업: {bak.name}")

    args.out.write_text(render_md(data, pages), encoding="utf-8")
    jpath = args.out.with_suffix(".json")
    jpath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[✓] {args.out}")
    print(f"[✓] {jpath}")
    if data["unreadable"]:
        print("[!] 판독 실패 항목이 있습니다. 사람이 확인해서 md에 직접 채워 넣으세요:")
        for u in data["unreadable"]:
            print(f"      - {u}")
    return 0


def render_md(d: dict, pages: list[dict]) -> str:
    def table(rows, headers, keys):
        if not rows:
            return "_(항목 없음)_\n"
        out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
        for r in rows:
            out.append("| " + " | ".join(str(r.get(k, "")).replace("|", "\\|") for k in keys) + " |")
        return "\n".join(out) + "\n"

    src = ", ".join(f"{p['drawing_no']}(p{p['page']})" for p in pages)
    L = [
        "# Symbol & Legend",
        "",
        f"> 생성: `scripts/parse_legend.py` · 원본 도면: {src}",
        f"> 생성 시각: {dt.datetime.now():%Y-%m-%d %H:%M}",
        ">",
        "> 이 파일은 자동 생성된 초안입니다. **사람이 검토하고 직접 고쳐 쓰는 규칙 문서**이며,",
        "> 재생성하면 기존 내용은 `.bak.md`로 백업됩니다.",
        "",
        "## 태그 첫 글자 (측정 변수)", "", table(d["first_letters"], ["글자", "측정 변수"], ["letter", "measured_variable"]),
        "## 태그 뒤 글자 (기능)", "", table(d["succeeding_letters"], ["글자", "기능"], ["letter", "function"]),
        "## 계기 심볼과 설치 위치", "", table(d["instrument_symbols"], ["심볼", "의미", "설치 위치"], ["symbol", "meaning", "mounting"]),
        "## 신호선", "", table(d["signal_lines"], ["형태", "의미"], ["appearance", "meaning"]),
        "## 밸브 상태 기호", "", table(d["valve_fail_positions"], ["기호", "의미"], ["code", "meaning"]),
        "## 약어", "", table(d["abbreviations"], ["약어", "의미"], ["abbr", "meaning"]),
        "## 태그 넘버링 체계 (KKS)", "", d["tag_numbering"], "",
        "## Vendor Scope 표기", "", d["vendor_scope"], "",
    ]
    if d["unreadable"]:
        L += ["## 판독하지 못한 항목 (사람이 채워야 함)", ""] + [f"- [ ] {u}" for u in d["unreadable"]] + [""]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
