#!/usr/bin/env python3
"""P&ID 도면을 Claude vision으로 판독해 Field Instrument 목록을 만든다.

도면 한 장당 한 번 호출한다(한꺼번에 넣는 것보다 누락이 적다). 각 호출에는
전체 도면 이미지 + 확대 타일 + PDF 텍스트 레이어에서 뽑은 계기 문자 후보 좌표를
함께 넣는다. 규칙 문서(rules/*.md)는 도면마다 동일하므로 prompt cache에 올라간다.

모델이 채우는 건 excel_format.json에서 source="drawing"인 컬럼뿐이다.
나머지(사양/운전조건)는 build_excel.py가 typical 표와 Design Table에서 채운다.

사용:
  export ANTHROPIC_API_KEY=sk-ant-...
  python3 scripts/extract_instruments.py --pages 20,38
  python3 scripts/extract_instruments.py --pages 20 --dry-run   # API 없이 텍스트레이어 기준선
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _claude import MODEL_DEFAULT, call_structured, image_block  # noqa: E402

RULES = ["rules/extraction_guide.md", "rules/naming_convention.md", "rules/symbol_legend.md"]

# 텍스트 레이어의 원시 문자 → Instrument List의 TYPE. 판독 규칙이 바뀌면 여기도 함께 고친다.
TOKEN_TO_TYPE = {
    "PT": "PIT", "TT": "TIT", "LT": "LIT", "FT": "FIT", "AT": "AIT",
    "PIT": "PIT", "TIT": "TIT", "LIT": "LIT", "FIT": "FIT", "AIT": "AIT",
    "PI": "PI", "TI": "TI", "LI": "LI", "FI": "FI",
    "PDIT": "PDIT", "PDI": "PDIT", "PDT": "PDIT",
    "FE": "FE", "RO": "RO", "LS": "LS", "FS": "FS", "PS": "PS", "TS": "TS",
}
# Field Instrument 카테고리가 아닌 것 (밸브/패키지 쪽) — 오탐으로 걸러낸다.
NOT_FIELD_INSTRUMENT = {"ZS", "ZSC", "ZSO", "HS", "XS"}


def build_schema(fmt: dict) -> dict:
    drawing_cols = [c for c in fmt["columns"] if c["source"] == "drawing"]
    props = {}
    for c in drawing_cols:
        props[c["key"]] = {"type": "string", "description": COL_HINT.get(c["key"], c["label"])}
    props |= {
        "source_tokens": {"type": "string",
                          "description": "이 행의 근거가 된 도면상 계기 문자와 대략 위치. 예: 'PT ×2 @ 좌상단 HP스팀 헤더'"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"],
                       "description": "판독 확신도. 글자가 흐리거나 맥락 추정이 섞였으면 low"},
    }
    order = [c["key"] for c in drawing_cols] + ["source_tokens", "confidence"]
    return {
        "type": "object",
        "properties": {
            "instruments": {
                "type": "array",
                "description": "이 도면에서 판독한 Field Instrument. 도면 위→아래, 좌→우 순서.",
                "items": {"type": "object", "properties": props,
                          "required": order, "additionalProperties": False},
            },
            "excluded": {
                "type": "array",
                "description": "계기 문자로 보였지만 목록에서 제외한 것과 그 이유. 누락 추적용이므로 반드시 남긴다.",
                "items": {"type": "object", "properties": {
                    "token": {"type": "string"},
                    "location": {"type": "string"},
                    "reason": {"type": "string", "description": "예: 밸브 리밋스위치라 Field Instrument 아님 / Vendor package 범위"},
                }, "required": ["token", "location", "reason"], "additionalProperties": False},
            },
            "review_findings": {
                "type": "array",
                "description": "사람이 확인해야 할 사항(판독 불가, 태그 불일치, 규칙 충돌 등)",
                "items": {"type": "object", "properties": {
                    "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                    "location": {"type": "string"},
                    "finding": {"type": "string"},
                    "recommendation": {"type": "string"},
                }, "required": ["severity", "location", "finding", "recommendation"],
                    "additionalProperties": False},
            },
            "page_summary": {"type": "string", "description": "이 도면에서 무엇을 몇 건 뽑았는지 2~3문장"},
        },
        "required": ["instruments", "excluded", "review_findings", "page_summary"],
        "additionalProperties": False,
    }


COL_HINT = {
    "system": "계통명. 도면 제목과 SYSTEM 목록에서 고른다 (예: HP Steam System)",
    "pid_no": "이 도면의 P&ID 도면번호. 타이틀블록 값을 그대로 쓴다",
    "type": "계기 타입 약어 (PIT, TIT, LIT, FIT, PDIT, PI, TI, LI, LS, FS, FE, RO 등)",
    "qty": "같은 사양·같은 용도로 중복 설치되는 수량. 숫자만",
    "description": "UNIT 번호 + 설비/계통 + 측정 대상 + 서브 식별자. 예: 'UNIT #11 HP STEAM PRESSURE A'",
    "inst_typical_type": "INST. TYPICAL TYPE (예: PIT-1, TIT-3). 허용 목록에서만 고른다",
    "remark": "ADD / DEL 등 개정 표기나 Vendor Scope 등 특기사항. 없으면 '-'",
}


def system_prompt(fmt: dict, typicals: dict) -> str:
    parts = ["당신은 P&ID 도면에서 Field Instrument 목록을 뽑아 표준 Instrument List로 옮기는 계장 엔지니어입니다.",
             "이 결과물은 실제 플랜트 설계에 쓰이는 안전 관련 문서입니다. 도면에 없는 것을 만들어내는 것이",
             "빠뜨리는 것보다 훨씬 위험합니다. 확신이 없으면 confidence를 low로 두고 review_findings에 남기세요.",
             ""]
    for rel in RULES:
        p = ROOT / rel
        if p.exists():
            parts += [f"\n{'=' * 70}\n# 규칙 문서: {rel}\n{'=' * 70}", p.read_text(encoding="utf-8")]
        else:
            parts.append(f"\n(경고: {rel} 없음 — 해당 규칙 없이 판독합니다)")

    parts += ["", "=" * 70, "# 출력 대상 컬럼", "=" * 70]
    for c in fmt["columns"]:
        if c["source"] == "drawing":
            parts.append(f"- {c['key']} ({c['label']}): {COL_HINT.get(c['key'], '')}")

    parts += ["", f"허용 TYPE: {', '.join(fmt['instrument_types'])}",
              "", "TYPE별 허용 INST. TYPICAL TYPE:"]
    for t, xs in fmt["type_to_typical_types"].items():
        desc = []
        for x in xs:
            e = typicals.get(x, {})
            desc.append(f"{x}({e.get('element_type', '?')}/{e.get('mounting_type', '?')})")
        parts.append(f"  {t}: {', '.join(desc)}")

    parts += ["", f"허용 SYSTEM(계통명): {', '.join(fmt['systems'])}",
              "", "=" * 70, "# 작업 방식", "=" * 70,
              "1. 첨부된 '텍스트 레이어 계기 문자 후보'는 PDF에서 결정적으로 추출한 것이라 위치와 개수가 정확합니다.",
              "   이 목록을 기준선으로 삼되, 그대로 옮기지는 마세요. 후보 하나하나가 Field Instrument인지",
              "   도면 이미지에서 확인하고, 아니면 excluded에 이유와 함께 넣습니다.",
              "2. 후보에 없더라도 이미지에서 계기를 발견하면 추가하고 source_tokens에 그 사실을 적습니다.",
              "3. 같은 사양·같은 용도로 나란히 설치된 계기는 한 행으로 합치고 qty에 개수를 적습니다.",
              "   서로 다른 측정점(A/B 계열 등 식별자가 다른 것)은 별도 행으로 둡니다.",
              "4. DESCRIPTION은 도면의 From/To 라벨과 설비 이름을 근거로 작성합니다. 영문 대문자로 씁니다.",
              "5. 밸브 리밋스위치(ZS), 밸브 액추에이터, 벤더 패키지 내부 계기는 이번 범위가 아니므로",
              "   excluded에 넣습니다."]
    return "\n".join(parts)


def user_content(page: dict) -> list[dict]:
    cand = page["text_candidates"]
    lines = [f"{c['token']} @ (x={c['x']}, y={c['y']})" for c in cand]
    content: list[dict] = [{"type": "text", "text":
        f"# 판독 대상 도면\n"
        f"- 도면번호: {page['drawing_no']}\n"
        f"- 도면명: {page['title']}\n"
        f"- PDF 페이지: {page['page']}\n"}]
    content.append({"type": "text", "text": "## 전체 도면"})
    content.append(image_block(ROOT / page["image"]))
    for t in page["tiles"]:
        content.append({"type": "text", "text":
                        f"## 확대 타일 r{t['row']}c{t['col']} "
                        f"(도면 내 영역 x {t['region'][0]}~{t['region'][2]}, y {t['region'][1]}~{t['region'][3]})"})
        content.append(image_block(ROOT / t["image"]))
    content.append({"type": "text", "text":
                    f"## 텍스트 레이어 계기 문자 후보 ({len(cand)}건, 좌표는 도면 대비 0~1 정규화, 위→아래 순)\n"
                    + "\n".join(lines)})
    if page.get("notes"):
        content.append({"type": "text", "text": f"## 도면 GENERAL NOTES / NOTES\n{page['notes']}"})
    content.append({"type": "text", "text":
                    "이 도면의 Field Instrument 목록을 만드세요. 제외한 후보는 반드시 excluded에 이유를 남기세요."})
    return content


def baseline_rows(page: dict) -> dict:
    """API 없이 텍스트 레이어만으로 만드는 기준선. 파이프라인 점검과 비교 기준용."""
    counts: dict[str, int] = {}
    excluded = []
    for c in page["text_candidates"]:
        tok = c["token"]
        if tok in NOT_FIELD_INSTRUMENT:
            excluded.append({"token": tok, "location": f"x={c['x']},y={c['y']}",
                             "reason": "밸브 리밋스위치 계열이라 Field Instrument 범위 밖"})
            continue
        t = TOKEN_TO_TYPE.get(tok)
        if not t:
            excluded.append({"token": tok, "location": f"x={c['x']},y={c['y']}",
                             "reason": "TOKEN_TO_TYPE 매핑에 없는 문자"})
            continue
        counts[t] = counts.get(t, 0) + 1
    rows = [{"system": "", "pid_no": page["drawing_no"] or "", "type": t, "qty": str(n),
             "description": "-", "inst_typical_type": "", "remark": "-",
             "source_tokens": f"텍스트 레이어 {t} {n}건", "confidence": "low"}
            for t, n in sorted(counts.items())]
    return {"instruments": rows, "excluded": excluded,
            "review_findings": [{"severity": "high", "location": page["drawing_no"] or "",
                                 "finding": "--dry-run 기준선 결과입니다. DESCRIPTION과 수량 통합이 반영되지 않았습니다.",
                                 "recommendation": "실제 판독은 ANTHROPIC_API_KEY를 설정하고 --dry-run 없이 실행하세요."}],
            "page_summary": f"텍스트 레이어 기준선: 후보 {len(page['text_candidates'])}건 → {len(rows)}행"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=ROOT / "outputs/pages/manifest.json")
    ap.add_argument("--pages", help="판독할 PDF 페이지. 예: 20,38. 생략하면 레전드 제외 전체")
    ap.add_argument("--out", type=Path, help="출력 폴더 (기본 outputs/run_YYYYMMDD_HHMM)")
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--max-tokens", type=int, default=32000)
    ap.add_argument("--dry-run", action="store_true", help="API 호출 없이 텍스트 레이어 기준선만 생성")
    args = ap.parse_args()

    fmt = json.loads((ROOT / "config/excel_format.json").read_text(encoding="utf-8"))
    typicals = json.loads((ROOT / "config/typicals.json").read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    if args.pages:
        want = {int(p) for p in args.pages.split(",") if p.strip()}
        pages = [p for p in manifest["pages"] if p["page"] in want]
    else:
        pages = [p for p in manifest["pages"] if "GEN00" not in (p["drawing_no"] or "")]

    if not pages:
        print("[!] 판독 대상 페이지가 없습니다.", file=sys.stderr)
        return 1

    run_dir = args.out or ROOT / f"outputs/run_{dt.datetime.now():%Y%m%d_%H%M}"
    run_dir.mkdir(parents=True, exist_ok=True)

    schema = build_schema(fmt)
    system = system_prompt(fmt, typicals) if not args.dry_run else ""
    if system:
        print(f"[i] 시스템 프롬프트 {len(system):,}자 (규칙 문서 포함, 캐시 대상)")

    result = {
        "run_id": run_dir.name,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "model": "(dry-run)" if args.dry_run else args.model,
        "effort": args.effort,
        "rules_used": [r for r in RULES if (ROOT / r).exists()],
        "pages": [],
        "instruments": [],
        "excluded": [],
        "review_findings": [],
    }

    for p in pages:
        print(f"\n[>] p{p['page']} {p['drawing_no']} · {p['title']}")
        print(f"    이미지 {1 + len(p['tiles'])}장 · 텍스트 후보 {len(p['text_candidates'])}건")
        if args.dry_run:
            data = baseline_rows(p)
        else:
            data = call_structured(system, user_content(p), schema,
                                   model=args.model, effort=args.effort, max_tokens=args.max_tokens)

        for row in data["instruments"]:
            row.setdefault("pid_no", p["drawing_no"] or "")
            row["_page"] = p["page"]
            if row.get("type") and row["type"] not in fmt["instrument_types"]:
                data["review_findings"].append({
                    "severity": "medium", "location": f"{p['drawing_no']} / {row.get('description', '')}",
                    "finding": f"템플릿에 없는 TYPE '{row['type']}'",
                    "recommendation": "타입 목록에 추가할지, 판독 오류인지 확인 필요"})
            x = row.get("inst_typical_type", "")
            if x and x not in typicals:
                data["review_findings"].append({
                    "severity": "medium", "location": f"{p['drawing_no']} / {row.get('description', '')}",
                    "finding": f"typicals에 없는 INST. TYPICAL TYPE '{x}'",
                    "recommendation": "typical 표를 갱신하거나 판독을 수정"})

        result["instruments"] += data["instruments"]
        result["excluded"] += [e | {"_page": p["page"]} for e in data["excluded"]]
        result["review_findings"] += [f | {"_page": p["page"]} for f in data["review_findings"]]
        result["pages"].append({"page": p["page"], "drawing_no": p["drawing_no"], "title": p["title"],
                                "count": len(data["instruments"]), "summary": data["page_summary"]})
        print(f"    → 계기 {len(data['instruments'])}행 · 제외 {len(data['excluded'])}건 "
              f"· 확인필요 {len(data['review_findings'])}건")

    out = run_dir / "extraction.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    total_qty = sum(int(r.get("qty") or 0) if str(r.get("qty", "")).isdigit() else 0
                    for r in result["instruments"])
    print(f"\n[✓] {out}")
    print(f"[i] 도면 {len(pages)}장 → 행 {len(result['instruments'])}개 (수량 합계 {total_qty}) "
          f"· 확인필요 {len(result['review_findings'])}건")
    print(f"\n다음: python3 scripts/build_excel.py {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
