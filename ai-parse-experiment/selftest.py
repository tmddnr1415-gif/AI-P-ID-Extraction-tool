#!/usr/bin/env python3
"""배관 시험 — API 없이 측정 장치가 실제로 도는지 확인한다.

**여기서 나오는 숫자는 판독 성적이 아니다.** 모델이 아니라 스텁이 답을 낸다.
확인하는 것은 하나다 — 결정성·대조·좌표·비용 코드가 진짜로 계산을 하는가.

특히 D-2 는 '흔들리는 스텁' 으로 **흔들림을 잡아내는지**까지 본다.
측정 장치가 차이를 못 잡으면 나중에 나올 '일치율 100%' 도 믿을 수 없다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pymupdf

import analyzer
import baseline as baseline_mod
import compare
import cost as cost_mod
import determinism
import make_fixture
import render
import schema as schema_mod

HERE = Path(__file__).resolve().parent
FAIL = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'OK  ' if cond else 'FAIL'} {name}{(' — ' + detail) if detail else ''}")
    if not cond:
        FAIL.append(name)


def steady_stub(scan, spec):
    """같은 장이면 언제나 같은 답. 결정적 모델을 흉내 낸다."""
    rows = []
    for c in scan.candidates:
        t = baseline_mod.TOKEN_TO_TYPE.get(c["token"])
        if not t or t not in spec.instrument_types:
            continue
        rows.append({
            "system": baseline_mod.system_from_title(scan.title, spec.systems),
            "pid_no": scan.drawing_no or "", "type": t, "qty": "2",
            "description": f"UNIT #11 STUB {t} @{c['x']:.2f}",
            "inst_typical_type": spec.top_typical(t), "remark": "-",
            "rect": c["rect"], "source_tokens": f"stub {c['token']}", "confidence": "high",
        })
    return {"instruments": rows, "excluded": [], "review_findings": [],
            "scope_notes": "", "qty_basis": "스텁", "page_summary": "스텁"}


def make_drifting_stub():
    """부를 때마다 한 행씩 덜 내는 스텁. 결정성 측정이 이것을 잡아야 한다."""
    state = {"n": 0}

    def stub(scan, spec):
        out = steady_stub(scan, spec)
        k = state["n"]
        state["n"] += 1
        if k:
            out["instruments"] = out["instruments"][:-k] or out["instruments"][:1]
            if out["instruments"]:
                out["instruments"][0] = {**out["instruments"][0], "qty": str(2 + k)}
        return out
    return stub


def main() -> int:
    outdir = HERE / "out" / "selftest"
    outdir.mkdir(parents=True, exist_ok=True)
    pdf = outdir / "synthetic_pid.pdf"
    make_fixture.build(pdf)
    doc = pymupdf.open(str(pdf))
    spec = schema_mod.load_spec()
    js = schema_mod.build_json_schema(spec)

    print("\n[1] 결정적 추출 — 같은 입력 두 번")
    a = render.scan_page(doc, 1)
    b = render.scan_page(doc, 1)
    check("텍스트 레이어가 두 번 같다", a.candidates == b.candidates,
          f"{len(a.candidates)}건")
    check("도면번호를 읽었다", a.drawing_no == "D00P-10LBA10-M05-0001", str(a.drawing_no))
    check("NOTES 를 읽었다", "DENOTES" in a.notes.upper())

    print("\n[2] 규칙 기준선")
    rule = baseline_mod.build(a, spec)
    check("행이 나왔다", len(rule["rows"]) == 6, f"{len(rule['rows'])}행")
    check("ZS 를 제외했다", any(e["token"] == "ZS" for e in rule["excluded"]))
    check("모든 행이 기존 스키마 칸을 갖췄다",
          all(all(k in r for k in spec.drawing_keys) for r in rule["rows"]))
    check("typical 칸이 결정적으로 찼다",
          all(r.get("sensing_type") for r in rule["rows"]))

    print("\n[3] AI 경로 (스텁) — 행이 같은 스키마로 나오는가")
    call = analyzer.analyze_page(doc, a, spec, js, stub=steady_stub, dpi=150, cols=2, rows=2)
    ai_rows = analyzer.rows_from(call, spec)
    check("스텁 호출이 성공했다", call.ok)
    check("행이 나왔다", len(ai_rows) == 6, f"{len(ai_rows)}행")
    check("칸 이름이 규칙 기준선과 똑같다",
          set(ai_rows[0]) == set(rule["rows"][0]),
          f"{len(set(ai_rows[0]) ^ set(rule['rows'][0]))}개 차이")
    check("이미지가 모델 상한 안이다",
          all(max(px) <= render.MODEL_EDGE for px in call.image_px),
          f"최대 장변 {max(max(px) for px in call.image_px)}px")

    print("\n[4] 결정성 측정이 '같음' 과 '다름' 을 가르는가")
    steady = [analyzer.rows_from(
        analyzer.analyze_page(doc, a, spec, js, stub=steady_stub, dpi=150, cols=2, rows=2), spec)
        for _ in range(3)]
    d1 = determinism.agreement(steady)
    check("안 흔들리는 스텁 → 완전 일치", d1.identical_runs and d1.jaccard_mean == 1.0,
          d1.line())

    drift = make_drifting_stub()
    drifted = [analyzer.rows_from(
        analyzer.analyze_page(doc, a, spec, js, stub=drift, dpi=150, cols=2, rows=2), spec)
        for _ in range(3)]
    d2 = determinism.agreement(drifted)
    check("흔들리는 스텁 → 불일치를 잡아냈다", not d2.identical_runs and d2.jaccard_mean < 1.0,
          d2.line())
    check("달라진 행을 지목했다", len(d2.unstable) > 0, f"{len(d2.unstable)}건")
    check("qty 가 흔들린 것을 칸별로 잡았다", d2.field_agreement["qty"] < 1.0,
          f"qty 일치 {d2.field_agreement['qty'] * 100:.0f}%")

    print("\n[5] 정답지 대조")
    truth = [{"pid_no": r["pid_no"], "type": r["type"], "description": r["description"],
              "page": 1} for r in ai_rows[:4]]
    s = compare.score(ai_rows, truth)
    check("재현율 100% · 정밀도 66.7%", abs(s.recall - 1.0) < 1e-9 and abs(s.precision - 4 / 6) < 1e-9,
          s.line("대조"))
    s2 = compare.score(ai_rows[:2], truth)
    check("놓친 것을 센다", s2.missed == 2, f"missed={s2.missed}")

    print("\n[6] 감사 수확 — 규칙이 놓치고 AI 가 찾은 것")
    thin_rule = rule["rows"][:3]
    truth_all = [{"pid_no": r["pid_no"], "type": r["type"],
                  "description": r["description"], "page": 1} for r in ai_rows]
    aud = compare.audit(ai_rows, thin_rule, truth_all)
    check("수확을 셌다", aud["harvest_count"] is not None and aud["harvest_count"] > 0,
          f"{aud['harvest_count']}건")
    aud_no_truth = compare.audit(ai_rows, thin_rule, None)
    check("정답지 없으면 수확을 세지 않는다", aud_no_truth["harvest_count"] is None)

    print("\n[7] 좌표")
    rect = compare.rect_errors(ai_rows, a.candidates, a.page_size_pt)
    check("좌표 오차를 쟀다", rect["stats"].get("n") == len(ai_rows), str(rect["stats"]))
    check("스텁은 텍스트 좌표를 그대로 써서 오차가 0 이다",
          rect["stats"].get("max_pt", 999) < 1.0, f"max {rect['stats'].get('max_pt')}pt")
    holed = [{**r, "rect": None} for r in ai_rows[:2]] + ai_rows[2:]
    check("rect 가 null 인 행을 따로 센다",
          compare.rect_errors(holed, a.candidates, a.page_size_pt)["stats"]["null_rect"] == 2)

    print("\n[8] 비용 — 이미지 기하")
    sw = cost_mod.sweep(a.page_size_pt)
    check("분할을 늘리면 실효 해상도가 오른다",
          all(sw[i]["effective_dpi"] < sw[i + 1]["effective_dpi"] for i in range(len(sw) - 1)))
    check("분할을 늘리면 토큰도 오른다",
          all(sw[i]["image_tokens"] < sw[i + 1]["image_tokens"] for i in range(len(sw) - 1)))
    c = cost_mod.summarize([call], "claude-sonnet-5", doc.page_count)
    check("usage 가 없으면 어림값이라고 밝힌다",
          not c["measured"] and "image_tokens_per_page_estimate" in c,
          f"{c.get('image_tokens_per_page_estimate'):,} 토큰/장")

    print("\n[9] 기존 저장소를 건드리지 않았는가")
    import subprocess
    r = subprocess.run(["git", "status", "--porcelain",
                        "pid-instrument-tool", "pid-extractor", "app.js", "index.html",
                        "styles.css", "README.md"],
                       cwd=HERE.parent, capture_output=True, text=True)
    check("기존 파일에 변경이 없다", r.stdout.strip() == "",
          r.stdout.strip()[:120] or "깨끗함")

    doc.close()
    print()
    if FAIL:
        print(f"실패 {len(FAIL)}건: {FAIL}")
        return 1
    print("배관 시험 전부 통과. — 이것은 판독 성적이 아니라 장치가 돈다는 확인이다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
