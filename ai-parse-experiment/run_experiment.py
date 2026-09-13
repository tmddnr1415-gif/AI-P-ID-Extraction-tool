#!/usr/bin/env python3
"""AI 파싱 실험 — 5장 최소 실험을 돌려 out/ai_parse_result.zip 을 낸다.

    python3 run_experiment.py --pdf <도면.pdf> --truth <정답지.json> \
        --pages 6,16,20,38,40 --repeats 3

  --pdf 를 주지 않으면 합성 도면으로 **배관만** 확인한다 (성적이 아니다).
  ANTHROPIC_API_KEY 가 없으면 AI 호출 없이 규칙 기준선과 비용 어림만 낸다.

재는 것은 넷이다 — 결정성(D-2) · 정답지 대조(D-1) · 좌표(D-3) · 비용(D-4),
그리고 감사 수확(D-5). 못 잰 것은 '못 쟀다' 고 적는다. 채우지 않는다.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

import analyzer
import baseline as baseline_mod
import compare
import cost as cost_mod
import determinism
import render
import schema as schema_mod

HERE = Path(__file__).resolve().parent
UNKNOWN = "측정 못 함"


# ── 장 고르기 ────────────────────────────────────────────
def pick_pages(doc, want: int, explicit: str | None) -> tuple[list[int], str]:
    """균등 간격으로 고른다. 쉬운 장을 고르지 않는다."""
    if explicit:
        return [int(x) for x in explicit.split(",") if x.strip()], "사용자가 지정"
    body = []
    for n in range(1, doc.page_count + 1):
        s = render.scan_page(doc, n)
        if s.is_legend or not s.drawing_no:
            continue
        body.append(n)
    if not body:
        return list(range(1, min(want, doc.page_count) + 1)), "본문 장을 못 가려 앞에서부터"
    if len(body) <= want:
        return body, f"본문 장이 {len(body)}장뿐이라 전부"
    step = len(body) / want
    return ([body[int(i * step)] for i in range(want)],
            f"본문 {len(body)}장에서 균등 간격 {step:.1f}장마다")


# ── 보고서 ───────────────────────────────────────────────
def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join("" if v is None else str(v) for v in r) + " |")
    return "\n".join(out)


def write_bundle(outdir: Path, ctx: dict) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    files: dict[str, str] = {}

    det = ctx.get("determinism")
    sc_ai = ctx.get("score_ai")
    sc_rule = ctx.get("score_rule")
    aud = ctx.get("audit") or {}
    cst = ctx.get("cost") or {}
    ran_ai = ctx["ran_ai"]

    det_line = det.line() if det else f"결정성 — {UNKNOWN} (AI 호출 없음)"
    acc_line = sc_ai.line("정답지 대조(AI)") if sc_ai else f"정답지 대조 — {UNKNOWN}"
    cost_line = (f"비용 — 장당 {cst.get('seconds_per_page', '?')}초 · "
                 + (f"${cst['usd_per_page']} · 입력 {cst['input_tokens_per_page']:,}토큰"
                    if cst.get("measured") else
                    f"이미지 토큰 어림 {cst.get('image_tokens_per_page_estimate', 0):,}"))
    harvest = aud.get("harvest_count")
    harv_line = (f"감사 수확 — 규칙이 놓치고 AI 가 찾은 것 {harvest}건"
                 if harvest is not None else f"감사 수확 — {UNKNOWN} (정답지 없음)")

    # 0_요약.md — 네 줄
    files["0_요약.md"] = "\n".join([
        "# 0. 요약 — 네 줄",
        "",
        f"1. **{det_line}**",
        f"2. **{acc_line}**",
        f"3. **{cost_line}**",
        f"4. **{harv_line}**",
        "",
        "---",
        "",
        f"- 실행: {ctx['when']}",
        f"- 도면: {ctx['pdf_label']} · 전체 {ctx['page_count']}장 중 {len(ctx['pages'])}장 판독",
        f"- 고른 장: {ctx['pages']} ({ctx['pick_why']})",
        f"- AI 호출: {'했음 — ' + ctx['model'] if ran_ai else '안 함'}",
        f"- 정답지: {'있음' if ctx['has_truth'] else '없음'}",
        "",
        ("> ⚠ 이 실행에는 실제 도면·정답지·API 키 중 일부가 없습니다. "
         "없는 것으로 계산한 숫자는 없습니다. 빈 칸은 빈 칸으로 두었습니다."
         if not (ran_ai and ctx["has_truth"] and ctx["real_pdf"]) else ""),
    ])

    # 2_방법론.md
    files["2_방법론.md"] = ("# 2. 방법론 — AI 에게 준 문서 전문\n\n"
                           "아래가 호출마다 system 프롬프트로 그대로 들어간 문서다.\n\n---\n\n"
                           + ctx["methodology"])

    # 3_대조표.md
    t3 = ["# 3. 대조표 — 장별 (정답지 · 기존 규칙 · AI)", ""]
    rows = []
    for p in ctx["pages"]:
        per = ctx["per_page"][p]
        rows.append([p, per["drawing_no"] or "-",
                     per["truth_rows"] if ctx["has_truth"] else UNKNOWN,
                     per["rule_rows"],
                     per["ai_rows"] if ran_ai else UNKNOWN,
                     per["ai_error"][:40] if per["ai_error"] else ""])
    t3.append(md_table(["PDF p", "도면번호", "정답지 행", "규칙 행", "AI 행", "비고"], rows))
    if sc_ai or sc_rule:
        t3 += ["", "## 재현율 · 정밀도", ""]
        if sc_ai:
            t3.append(f"- {sc_ai.line('AI')}")
        if sc_rule:
            t3.append(f"- {sc_rule.line('기존 규칙 기준선')}")
        t3 += ["", "> 기존 규칙 기준선은 DESCRIPTION 을 비워 두므로 "
                   "DESCRIPTION 까지 견주는 대조에서는 구조적으로 낮게 나온다. "
                   "TYPE 만 견준 값도 함께 본다."]
    else:
        t3 += ["", f"재현율·정밀도 — {UNKNOWN}. "
                   + ("정답지(--truth)가 없습니다. " if not ctx["has_truth"] else "")
                   + ("AI 호출을 하지 않았습니다." if not ran_ai else "")]
    files["3_대조표.md"] = "\n".join(t3)

    # 4_결정성.md
    t4 = ["# 4. 결정성 — 같은 장을 여러 번", ""]
    if det:
        t4 += [f"- {det.line()}", "",
               "## 칸별 일치율", "",
               md_table(["칸", "전 회차 같은 값 비율"],
                        [[f, f"{v * 100:.1f}%"] for f, v in det.field_agreement.items()]),
               "", f"## 회차마다 달라진 행 ({len(det.unstable)}건)", ""]
        if det.unstable:
            t4.append(md_table(["P&ID No.", "TYPE", "DESCRIPTION", "회차별 건수"],
                               [[*u["key"], u["counts"]] for u in det.unstable[:60]]))
        else:
            t4.append("없음 — 모든 회차가 같은 행 집합을 냈다.")
        t4 += ["", "## 이것이 뜻하는 것", "",
               ("완전 일치가 아니면 회귀 시험을 그대로 못 돌린다. "
                "지문 대조 대신 허용 오차를 둔 대조로 바꾸어야 하고, "
                "그러면 '규칙이 회귀를 잡는다' 는 규율이 약해진다.")
               if not det.identical_runs else
               "이 표본에서는 회차 간 차이가 없었다. 표본이 작으므로 장 수를 늘려 다시 본다."]
    else:
        t4 += [f"결정성 — {UNKNOWN}.", "",
               "AI 호출을 하지 않아 반복 판독을 못 했다. "
               "**결정성을 재지 않은 채로는 정확도 숫자도 뜻이 없다** — "
               "같은 입력에 다른 답이 나오면 그 정확도가 다음 회차에 재현된다는 보장이 없기 때문이다."]
    files["4_결정성.md"] = "\n".join(t4)

    # 5_감사수확.md
    t5 = ["# 5. 감사 수확 — 규칙이 놓치고 AI 가 찾은 것", ""]
    if aud.get("has_truth") and ran_ai:
        t5 += [f"**{harvest}건** — 이것이 (b) 의 성적이다.", "",
               "## AI 가 찾고 규칙이 놓쳤고 정답지에도 있는 것", ""]
        t5.append(md_table(["P&ID No.", "TYPE", "건수"],
                           [[*a["key"], a["count"]] for a in aud["ai_found_rule_missed"]])
                  if aud["ai_found_rule_missed"] else "없음")
        t5 += ["", "## 규칙이 찾고 AI 가 놓친 것", ""]
        t5.append(md_table(["P&ID No.", "TYPE", "건수"],
                           [[*a["key"], a["count"]] for a in aud["rule_found_ai_missed"]])
                  if aud["rule_found_ai_missed"] else "없음")
        t5 += ["", "## 둘 다 놓쳤는데 정답지에 있는 것", ""]
        t5.append(md_table(["P&ID No.", "TYPE", "건수"],
                           [[*a["key"], a["count"]] for a in aud["both_missed"]])
                  if aud["both_missed"] else "없음")
    else:
        t5 += [f"AI 대 규칙 감사 수확 — {UNKNOWN}.", "",
               "정답지 없이 '수확' 을 세면 그냥 오탐을 세는 것이다. 세지 않았다."]

    t5 += ["", "---", "", "## AI 없이 나온 규칙 결함", "",
           "이 실험 장치를 만들며 기존 규칙에서 그대로 드러난 것이다. "
           "AI 가 찾은 것이 아니므로 위 수확 수에 넣지 않았다.", ""]
    t5.append(md_table(["NOTES 문장", "옳은 Q'ty", "규칙이 낸 Q'ty", "왜"],
                       [[c["notes"], c["want"], c["got"], c["why"]] for c in ctx["rule_defects"]]))
    t5 += ["",
           "Q'ty 는 그 장 **모든 행에 걸리는 배수**라 한 장이 틀리면 그 장 전체가 틀린다.",
           "",
           "근거: `pid-instrument-tool/web/app.js:544` 의 `qtyFromNotes()`.",
           "- 문자 묶음 `[\\d,\\s#]+` 이 줄바꿈을 넘어가 **다음 번호 문단의 번호를 삼킨다.**",
           "- `IDENTICAL` 만 본다. 방법론이 같다고 못박은 `SIMILAR` · `TYPICAL` · `SAME` 을 못 읽는다."]
    files["5_감사수확.md"] = "\n".join(t5)

    # 6_비용.md
    t6 = ["# 6. 비용 · 시간", ""]
    if cst:
        t6.append(md_table(["항목", "값"], [[k, v] for k, v in cst.items()]))
    t6 += ["", "## 해상도 스윕 — 분할 수가 실효 해상도를 정한다", "",
           "모델이 이미지를 **장변 1568px 로 줄여** 보므로 DPI 인자를 올려도 실효 해상도는",
           "안 올라간다. 올라가는 것은 업로드 바이트뿐이다. 실효 해상도를 올리는 유일한 길은",
           "장을 더 잘게 나누는 것이고, 그 대가가 아래 토큰이다.", ""]
    t6.append(md_table(["분할", "호출당 이미지", "실효 DPI", "이미지 토큰/장"],
                       [[r["grid"], r["images"], r["effective_dpi"], f"{r['image_tokens']:,}"]
                        for r in ctx["sweep"]]))
    t6 += ["", "> 최소 해상도는 이 표로 고르지 않는다. 계기 버블 글자가 **눈으로 읽히는**",
           "> 가장 성긴 분할이 답이고, 이 표는 그 대가를 붙여 줄 뿐이다.",
           "> `7_캡처/` 의 분할별 렌더를 보고 고른다.", "",
           f"## 전량({ctx['page_count']}장) 환산", ""]
    if cst.get("measured"):
        t6 += [f"- 시간 약 {cst['seconds_total_estimate']:,}초 "
               f"({cst['seconds_total_estimate'] / 60:.0f}분)",
               f"- 비용 약 ${cst['usd_total_estimate']}",
               "", "> 기존 규칙 기준선은 API 호출이 없어 비용이 0 이고 장당 1초 아래다. "
                   "곱절이 아니라 **없던 비용이 생기는 것**이다."]
    else:
        t6.append(f"전량 환산 — {UNKNOWN}. 실판독 usage 가 없으면 출력 토큰을 모른다.")
    files["6_비용.md"] = "\n".join(t6)

    # 1_보고서.md
    files["1_보고서.md"] = ctx["report"]

    for name, text in files.items():
        (outdir / name).write_text(text.rstrip() + "\n", encoding="utf-8")

    zpath = outdir / "ai_parse_result.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for name in files:
            z.write(outdir / name, name)
        shots = outdir / "7_캡처"
        if shots.exists():
            for f in sorted(shots.rglob("*")):
                if f.is_file():
                    z.write(f, f"7_캡처/{f.relative_to(shots)}")
        for extra in ("rows_ai.json", "rows_rule.json", "raw_calls.json"):
            if (outdir / extra).exists():
                z.write(outdir / extra, extra)
    return zpath


# ── 본체 ────────────────────────────────────────────────
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="P&ID AI 파싱 실험 — 최소 5장")
    ap.add_argument("--pdf", help="도면 PDF. 없으면 합성 도면으로 배관만 확인한다")
    ap.add_argument("--truth", help="정답지 JSON (rows: [{pid_no,type,description,page}])")
    ap.add_argument("--pages", help="판독할 PDF 쪽 번호. 예 6,16,20,38,40")
    ap.add_argument("--count", type=int, default=5, help="자동으로 고를 장 수 (기본 5)")
    ap.add_argument("--repeats", type=int, default=3, help="결정성 측정 반복 횟수 (기본 3)")
    ap.add_argument("--grid", default="3x2", help="타일 분할. 예 3x2, 4x4")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--model", default=analyzer.DEFAULT_MODEL)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--out", default=str(HERE / "out"))
    ap.add_argument("--no-ai", action="store_true", help="API 를 부르지 않는다")
    ap.add_argument("--all-pages", action="store_true",
                    help="전량 판독. 5장 결과를 보고 나서만 쓴다")
    a = ap.parse_args(argv)

    if a.all_pages and not os.environ.get("AI_PID_CONFIRM_FULL"):
        print("전량 판독은 비용이 선형으로 늘어납니다. 5장 결과를 먼저 보세요.\n"
              "그래도 돌리려면 AI_PID_CONFIRM_FULL=1 을 주세요.", file=sys.stderr)
        return 2

    cols, rows_ = (int(v) for v in a.grid.lower().split("x"))
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    spec = schema_mod.load_spec()
    methodology = analyzer.METHODOLOGY.read_text(encoding="utf-8")
    json_schema = schema_mod.build_json_schema(spec)
    api_key = None if a.no_ai else os.environ.get("ANTHROPIC_API_KEY")

    # 도면
    real_pdf = bool(a.pdf)
    if real_pdf:
        pdf_path = Path(a.pdf)
        if not pdf_path.exists():
            print(f"도면을 찾지 못했습니다: {pdf_path}", file=sys.stderr)
            return 2
        pdf_label = pdf_path.name
    else:
        import make_fixture
        pdf_path = outdir / "fixture" / "synthetic_pid.pdf"
        make_fixture.build(pdf_path)
        pdf_label = "합성 도면 (배관 확인용 — 성적이 아님)"

    doc = pymupdf.open(str(pdf_path))
    pages, pick_why = ((list(range(1, doc.page_count + 1)), "전량")
                       if a.all_pages else pick_pages(doc, a.count, a.pages))
    pages = [p for p in pages if 1 <= p <= doc.page_count]

    legend_pages = render.find_legend_pages(doc)
    legend_imgs = []
    for lp in legend_pages[:1]:
        png, px = render.render(doc, lp, a.dpi)
        legend_imgs.append({"page": lp, "png": png, "px": px})

    truth_rows = compare.load_truth(a.truth) if a.truth else None
    has_truth = truth_rows is not None

    # 판독
    scans, rule_rows, ai_rows, calls, per_page = {}, [], [], [], {}
    det_runs: list[list[dict]] = []
    rect_stats = None

    for p in pages:
        sc = render.scan_page(doc, p)
        scans[p] = sc
        b = baseline_mod.build(sc, spec)
        rule_rows += b["rows"]

        c = analyzer.analyze_page(
            doc, sc, spec, json_schema, api_key=api_key, model=a.model,
            dpi=a.dpi, cols=cols, rows=rows_, legend=legend_imgs,
            max_tokens=a.max_tokens, methodology=methodology)
        calls.append(c)
        rws = analyzer.rows_from(c, spec)
        ai_rows += rws
        per_page[p] = {
            "drawing_no": sc.drawing_no, "rule_rows": len(b["rows"]),
            "ai_rows": len(rws) if c.ok else 0, "ai_error": c.error,
            "truth_rows": sum(1 for r in (truth_rows or [])
                              if (r.get("page") or r.get("_page")) == p),
        }
        print(f"  p{p} {sc.drawing_no or '-'}: 규칙 {len(b['rows'])}행 · "
              f"AI {str(len(rws)) + '행' if c.ok else '실패'} ({c.seconds:.1f}s)", file=sys.stderr)

    ran_ai = any(c.ok and c.data for c in calls)

    # D-2 결정성 — 첫 장을 repeats 회
    det = None
    if ran_ai and a.repeats > 1:
        p0 = pages[0]
        print(f"  결정성: p{p0} 를 {a.repeats}회", file=sys.stderr)
        first = [r for r in ai_rows if r["_page"] == p0]
        det_runs.append(first)
        for i in range(a.repeats - 1):
            c = analyzer.analyze_page(
                doc, scans[p0], spec, json_schema, api_key=api_key, model=a.model,
                dpi=a.dpi, cols=cols, rows=rows_, legend=legend_imgs,
                max_tokens=a.max_tokens, methodology=methodology)
            calls.append(c)
            det_runs.append(analyzer.rows_from(c, spec))
        if all(det_runs):
            det = determinism.agreement(det_runs)

    # D-3 좌표
    if ran_ai:
        p0 = pages[0]
        rect_stats = compare.rect_errors(
            [r for r in ai_rows if r["_page"] == p0],
            scans[p0].candidates, scans[p0].page_size_pt)

    # D-1 / D-5
    score_ai = compare.score(ai_rows, truth_rows) if (has_truth and ran_ai) else None
    score_rule = compare.score(rule_rows, truth_rows, with_desc=False) if has_truth else None
    aud = compare.audit(ai_rows, rule_rows, truth_rows) if ran_ai else {}

    # D-4
    cst = cost_mod.summarize(calls, a.model, doc.page_count) if calls else {}
    sweep = cost_mod.sweep(scans[pages[0]].page_size_pt)

    # 규칙 결함 표 (AI 없이 나온 것)
    defect_cases = [
        ("CONFIGURATION IS IDENTICAL FOR GROUP#20", 2, "단독이면 맞다"),
        ("1. CONFIGURATION IS IDENTICAL FOR GROUP#20 ⏎ 2. GENERATOR …", 2,
         "다음 번호 문단의 '2.' 를 호기로 삼킨다"),
        ("1. CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22 ⏎ 2. REFER TO …", 4,
         "같은 삼킴. 도구 문서가 예시로 든 문장이다"),
        ("THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR FOR 3-2", 2, "SIMILAR 를 못 읽는다"),
        ("CONFIGURATION IS TYPICAL FOR GROUP#20", 2, "TYPICAL 을 못 읽는다"),
    ]
    rule_defects = []
    for notes, want, why in defect_cases:
        got, _ = baseline_mod.qty_from_notes(notes.replace(" ⏎ ", "\n"))
        rule_defects.append({"notes": f"`{notes}`", "want": want,
                             "got": f"**{got}**" if got != want else got, "why": why})

    # 캡처 — 분할별 렌더
    shots = outdir / "7_캡처"
    if shots.exists():
        shutil.rmtree(shots)
    shots.mkdir(parents=True)
    for cc, rr in ((2, 2), (3, 2), (4, 4)):
        png, px = render.render(doc, pages[0], a.dpi,
                                render.tiles(cc, rr)[0]["region"])
        (shots / f"분할{cc}x{rr}_첫타일_{px[0]}x{px[1]}.png").write_bytes(png)
    png, px = render.render(doc, pages[0], a.dpi)
    (shots / f"전체_p{pages[0]}_{px[0]}x{px[1]}.png").write_bytes(png)

    (outdir / "rows_ai.json").write_text(
        json.dumps(ai_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "rows_rule.json").write_text(
        json.dumps(rule_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    (outdir / "raw_calls.json").write_text(json.dumps(
        [{"page": c.page, "ok": c.ok, "seconds": round(c.seconds, 2),
          "input_tokens": c.input_tokens, "output_tokens": c.output_tokens,
          "attempts": c.attempts, "error": c.error} for c in calls],
        indent=2, ensure_ascii=False), encoding="utf-8")

    ctx = {
        "when": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "pdf_label": pdf_label, "real_pdf": real_pdf, "page_count": doc.page_count,
        "pages": pages, "pick_why": pick_why, "model": a.model,
        "methodology": methodology, "per_page": per_page,
        "ran_ai": ran_ai, "has_truth": has_truth,
        "determinism": det, "score_ai": score_ai, "score_rule": score_rule,
        "audit": aud, "cost": cst, "sweep": sweep, "rect": rect_stats,
        "rule_defects": rule_defects,
    }
    ctx["report"] = build_report(ctx)
    z = write_bundle(outdir, ctx)
    doc.close()
    print(f"\n{z}")
    print((outdir / "0_요약.md").read_text(encoding="utf-8"))
    return 0


def build_report(ctx: dict) -> str:
    ran_ai, has_truth = ctx["ran_ai"], ctx["has_truth"]
    det, rect = ctx.get("determinism"), ctx.get("rect")
    L = ["# 1. 보고서", "",
         f"- 실행 {ctx['when']}", f"- 도면 {ctx['pdf_label']}",
         f"- 판독 {len(ctx['pages'])}장 / 전체 {ctx['page_count']}장",
         f"- 모델 {ctx['model'] if ran_ai else '(호출 안 함)'}", "",
         "## 0 재사용 — 스키마·화면·Excel", "",
         "기존 저장소는 읽기만 했다. 고친 파일 없다. 이 실험은 별도 디렉터리에 있다.", "",
         "행 스키마는 `pid-instrument-tool/config/excel_format.json` 을 그대로 읽어 쓴다.",
         "AI 가 채우는 칸은 `source='drawing'` 인 일곱이고, `source='typical'` 인 다섯은",
         "`inst_typical_type` 에서 코드가 결정적으로 파생한다 — AI 에게 맡기지 않는다.",
         "같은 부품에서 매번 같은 값이 나와야 회귀가 성립하기 때문이다.", "",
         "## A 장 고르기", "",
         f"- 고른 장: {ctx['pages']}", f"- 규칙: {ctx['pick_why']}", "",
         "## B 방법론 · 해상도 · JSON 강제", "",
         "- 방법론 문서 전문은 `2_방법론.md`. 호출마다 system 으로 들어가고 캐시가 걸린다.",
         "- 출력은 JSON 스키마로 강제한다. `qty` 와 `rect` 는 **null 을 허용**한다 —",
         "  모른다고 말할 수 있어야 지어내지 않는다.",
         "- 해상도는 DPI 가 아니라 **분할 수**가 정한다. `6_비용.md` 의 스윕 표 참조.", "",
         "## C 기존 화면 · Excel", "",
         "행이 기존 스키마 모양이므로 기존 화면과 Excel 출력기가 그대로 받는다.",
         "`rect` 는 기존 행에 없던 부가 칸이라 기존 코드가 무시한다 — 화면도 Excel 도 안 바뀐다.",
         "", "## D 측정", ""]

    L.append(f"- **결정성(D-2)** — {det.line() if det else UNKNOWN + ' (AI 호출 없음)'}")
    L.append(f"- **정답지 대조(D-1)** — "
             + (ctx['score_ai'].line('AI') if ctx.get('score_ai') else UNKNOWN))
    if rect and rect["stats"].get("n"):
        s = rect["stats"]
        L.append(f"- **좌표(D-3)** — 중앙값 {s['median_pt']}pt · p90 {s['p90_pt']}pt · "
                 f"최대 {s['max_pt']}pt · rect 를 null 로 둔 행 {s['null_rect']}건")
    else:
        L.append(f"- **좌표(D-3)** — {UNKNOWN}")
    c = ctx.get("cost") or {}
    L.append(f"- **비용(D-4)** — 장당 {c.get('seconds_per_page', '?')}초"
             + (f" · ${c['usd_per_page']} · 전량 ${c['usd_total_estimate']}"
                if c.get("measured") else " · 토큰은 어림값만"))
    h = (ctx.get("audit") or {}).get("harvest_count")
    L.append(f"- **감사 수확(D-5)** — " + (f"{h}건" if h is not None else UNKNOWN))

    L += ["", "## E 판정", ""]
    if not ran_ai:
        L += ["**판정을 내리지 않는다.** AI 호출을 하지 않아 (a) 도 (b) 도 잴 수 없었다.",
              "", "빠진 것:",
              "- " + ("도면 — 실제 도면 대신 합성 도면을 썼다" if not ctx["real_pdf"] else "도면은 있었다"),
              "- " + ("정답지 없음" if not has_truth else "정답지는 있었다"),
              "- API 키 없음 (ANTHROPIC_API_KEY)", "",
              "셋을 채우고 같은 명령을 다시 돌리면 위 빈 칸이 숫자로 찬다."]
    else:
        ok_det = det and det.identical_runs
        L += [f"- (a) 대체 — " + ("결정성이 완전하지 않으면 회귀를 못 돌린다. "
                                   "이 표본에서 " + ("완전 일치했다" if ok_det else "회차 간 차이가 있었다") + "."),
              f"- (b) 감사 — 수확 {h if h is not None else UNKNOWN}건."]
    L += ["", "### 폐쇄망", "",
          "회사 PC 는 외부 API 를 못 쓴다. 이 실험 결과가 좋아도 **회사 PC 에 그대로 못 올린다.**",
          "남는 쓰임은 하나다 — 새 프로젝트 온보딩 때 **개발 PC 에서** 한 번 돌려",
          "규칙이 놓치는 자리를 찾아 규칙에 되먹이는 것. 상시 판독 경로가 될 수 없다.",
          "기존 규칙 기반 경로는 API 없이 도는 것이 이 제약 아래에서는 기능이 아니라 전제다.",
          "", "## 규칙에 바로 더할 것", "",
          "AI 없이 이 장치를 만들며 드러난 것이다. `5_감사수확.md` 참조.",
          "`qtyFromNotes()` 가 Q'ty 를 세 갈래로 틀린다. Q'ty 는 그 장 전 행에 걸리는 배수다."]
    return "\n".join(L)


if __name__ == "__main__":
    raise SystemExit(main())
