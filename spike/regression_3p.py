"""세 프로젝트 회귀 하네스 — 명령 하나로 전부 돌리고 한 표로 낸다.

    python3 spike/regression_3p.py                # 전부 돌리고 기준선과 대조
    python3 spike/regression_3p.py --only TC2     # 하나만
    python3 spike/regression_3p.py --reuse        # 이미 있는 결과 json 으로 다시 채점
    python3 spike/regression_3p.py --write-baseline   # 지금 값을 기준선으로 저장

왜 있는가
    TC2 를 고치기 시작하면 AL NOUF1 이 깨진 것을 모른 채 갈 위험이 크다.
    19·21회차에 실제로 그렇게 됐다 — 한쪽을 고치니 다른 쪽이 **조용히** 틀렸다.
    앞으로 TC2·SADARA 에도 피드백 회차를 돌리므로 위험은 계속 커진다.

규칙
    · **순차로 돈다.**  병렬은 메모리가 위험하다 (TC2 혼자 최대 RSS 7.2GB).
    · 프로젝트마다 **자식 프로세스**를 쓴다 — 메모리를 돌려받고 최대 RSS 를
      따로 재기 위해서다.
    · 기준선은 `spike/baselines_3p.json` 이고, 벗어나면 **실패**한다.
    · 프로젝트 추가는 `spike/projects_3p.json` 에 한 항목이다.
    · 실 DB 를 건드리지 않는다 — `PID_DATA_DIR` 을 버릴 폴더로 돌린다.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "spike"))
import identification  # noqa: E402

PROJECTS = json.loads((ROOT / "spike" / "projects_3p.json").read_text())["projects"]
BASELINES = ROOT / "spike" / "baselines_3p.json"
OUT_JSON = ROOT / "out" / "regression_3p.json"
RUNS = ROOT / "out" / "regression_3p"


def anchors():
    """검출기가 아는 태그 낱말과, 그 낱말이 어느 TYPE 이 되는지의 사전."""
    from app.engine import detect_symbols as ds
    return ds.RULESET_V3.anchors, dict(ds.RULESET_V3.field_type_map)


def run_one(proj, reuse: bool) -> dict:
    pdf = ROOT / proj["pdf"]
    dest = RUNS / (proj["name"].replace(" ", "_") + ".json")
    if not pdf.exists():
        return {"name": proj["name"], "error": "PDF 없음: %s" % proj["pdf"]}
    if not (reuse and dest.exists()):
        env = dict(os.environ)
        env["PID_DATA_DIR"] = tempfile.mkdtemp(prefix="pid3p-")
        env.pop("PID_PROJECT_CONFIG", None)     # 미지정이 기준선이다 (14회차 [8])
        t0 = time.time()
        p = subprocess.run([sys.executable, str(ROOT / "spike" / "analyse_one.py"),
                            str(pdf), str(dest)], env=env, cwd=str(ROOT),
                           capture_output=True, text=True)
        if p.returncode != 0:
            return {"name": proj["name"],
                    "error": (p.stderr or p.stdout or "").strip()[-400:],
                    "seconds": round(time.time() - t0, 1)}
    blob = json.loads(dest.read_text())
    return score(proj, blob)


def score(proj, blob) -> dict:
    result = blob["result"]
    rows = result["rows"]
    words = {int(k): [(tuple(r), t) for r, t in v] for k, v in blob["words"].items()}
    anc, tmap = anchors()
    if result.get("input_kind") == "DXF":
        # 55회차 — DXF 첫 기준선.  축3 채점기는 PDF 의 낱말·타이틀 자리를 전제하므로
        # 여기서는 재지 않는다 (`score: None` · 대조 대상은 rows · fingerprint · qty_sum).
        metrics, total = {}, None
    else:
        metrics, total = identification.measure(result, words, anc, tmap)
    out = {
        "name": proj["name"],
        "rows": len(rows),
        "fingerprint": result.get("fingerprint"),
        "qty_sum": sum(r["qty"] for r in rows if r.get("qty")),
        "tabs": dict(collections.Counter(r.get("tab") for r in rows)),
        "seconds": blob.get("seconds"),
        "max_rss_gb": blob.get("max_rss_gb"),
        "identification": {k: list(v) for k, v in metrics.items()},
        "score": total,
    }
    if proj.get("client_lists") and (ROOT / "data" / "CZE_Field_Instrument.xlsx").exists():
        out["axes"] = client_axes(rows)
    return out


def client_axes(rows) -> dict:
    """축1·축2 — 정의는 `spike/accuracy.py` 하나뿐이고 여기서 부르기만 한다."""
    import accuracy
    out = {}
    for name, keep in accuracy.AXES:
        per, fp, fn = accuracy.score(rows, keep)
        h = sum(x[1] for x in per); g = sum(x[2] for x in per); tp = sum(x[3] for x in per)
        out[name] = {"recall": round(100 * tp / max(h, 1), 1),
                     "precision": round(100 * tp / max(g, 1), 1),
                     "fp": sum(fp.values()), "fn": sum(fn.values())}
    return out


CHECK = ("rows", "fingerprint", "qty_sum", "score")


def compare(now, base) -> list:
    bad = []
    for r in now:
        b = base.get(r["name"])
        if b is None:
            bad.append("%s — 기준선이 없습니다 (--write-baseline 으로 세우세요)" % r["name"])
            continue
        if r.get("error"):
            bad.append("%s — %s" % (r["name"], r["error"]))
            continue
        for k in CHECK:
            if k in b and b[k] is not None and r.get(k) != b[k]:
                bad.append("%s %s: 기준선 %s → 지금 %s" % (r["name"], k, b[k], r.get(k)))
        bad.extend(axis_alarms(r, b))
    return bad


# 52회차 — ★ 축1·축2 는 **게이트가 아니라 참고 지표**다 (사용자 확정:
# *"발주처 xlsx 와 달라도 된다"*).  51회차 프롬프트가 이미 그렇게 정했다 —
# *"축2 는 없애지 않는다.  발주처와 얼마나 다른지는 알아야 한다. 참고 지표로
# 남는다 · 축2 가 내려가는 것은 실패가 아니다.  발주처가 안 센 것이다."*
#
# 지우지 않는 이유: 그 축이 **발주처 리스트와 얼마나 다른가**를 재는 유일한
# 자이고, 도면을 잘못 읽어 수치가 무너지는 것과 발주처가 안 세는 항목을 더
# 넣어 내려가는 것은 **다른 일**이다.  전자를 잡으려고 **바닥값**만 남긴다.
#
# 바닥값 85% 도 사용자가 정했다 (51회차 프롬프트: *"다만 85% 아래로 내려가면
# 멈추고 보고한다 — 뭔가 잘못 잡은 것이다"*).  **이 값은 우리가 고른 것이
# 아니므로 우리가 바꾸지 않는다.**
AXIS_FLOOR_KEY = "axes_floor"


def axis_alarms(now, base) -> list:
    """축1·축2 — 달라졌다고 실패시키지 않고, **바닥 아래일 때만** 실패한다."""
    got = now.get("axes")
    if got is None:                      # 발주처 xlsx 가 없는 기계 — 못 쟀다
        return []
    out = []
    for ax, floor in (base.get(AXIS_FLOOR_KEY) or {}).items():
        val = (got.get(ax) or {}).get("precision")
        if val is None:
            continue
        if val < floor:
            out.append("%s 축[%s] 정밀도 %.1f%% — 바닥 %.1f%% 아래입니다.  "
                       "멈추고 원인을 보세요 (뭔가 잘못 잡은 것입니다)"
                       % (now["name"], ax, val, floor))
    return out


def table(res) -> str:
    w = max(len(r["name"]) for r in res)
    lines = ["%-*s %6s %10s %8s %7s %7s %7s" %
             (w, "프로젝트", "행", "지문", "Q'ty", "초", "RSS", "축3")]
    for r in res:
        if r.get("error"):
            lines.append("%-*s  실패 — %s" % (w, r["name"], r["error"][:60]))
            continue
        lines.append("%-*s %6d %10s %8d %7.0f %6.1fG %6.1f" %
                     (w, r["name"], r["rows"], (r["fingerprint"] or "")[:8], r["qty_sum"],
                      r["seconds"] or 0, r["max_rss_gb"] or 0, r["score"]))
    ref = [r for r in res if not r.get("error") and r.get("axes")]
    if ref:
        lines.append("")
        lines.append("축1·축2 (참고 — 게이트가 아닙니다 · 발주처 리스트와 얼마나 다른가)")
        for r in ref:
            for ax, v in r["axes"].items():
                lines.append("%-*s %s 재현율 %.1f%% · 정밀도 %.1f%% (FP %d · FN %d)"
                             % (w, r["name"], ax, v["recall"], v["precision"],
                                v["fp"], v["fn"]))
    lines.append("")
    lines.append("축3 내역 (지표별 맞춘 수 / 분모)")
    lines.append("%-*s %s" % (w, "", "  ".join("%-11s" % m for m in identification.METRICS)))
    for r in res:
        if r.get("error"):
            continue
        cells = []
        for m in identification.METRICS:
            a, b, _n = r["identification"][m]
            cells.append("%-11s" % ("%d/%d" % (a, b)))
        lines.append("%-*s %s" % (w, r["name"], "  ".join(cells)))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--reuse", action="store_true")
    ap.add_argument("--write-baseline", action="store_true")
    a = ap.parse_args()

    RUNS.mkdir(parents=True, exist_ok=True)
    todo = [p for p in PROJECTS if not a.only or p["name"] == a.only]
    res = []
    for p in todo:
        print("· %s 분석 …" % p["name"], flush=True)
        res.append(run_one(p, a.reuse))
        r = res[-1]
        print("   %s" % (r.get("error") or
                         "행 %d · 지문 %s · 축3 %.1f점" %
                         (r["rows"], (r["fingerprint"] or "")[:8], r["score"])), flush=True)

    print()
    print(table(res))

    base = json.loads(BASELINES.read_text()) if BASELINES.exists() else {}
    if a.write_baseline:
        for r in res:
            if r.get("error"):
                continue
            keep = base.get(r["name"]) or {}
            new = {k: r[k] for k in CHECK if k in r}
            if "axes" in r:
                new["axes_reference"] = r["axes"]      # 참고 · 대조하지 않는다
            if AXIS_FLOOR_KEY in keep:                 # 바닥값은 사람이 정한다
                new[AXIS_FLOOR_KEY] = keep[AXIS_FLOOR_KEY]
            base[r["name"]] = new
        BASELINES.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n")
        print("\n기준선을 저장했습니다: %s" % BASELINES)

    OUT_JSON.write_text(json.dumps(
        {"projects": res, "metrics": list(identification.METRICS)},
        ensure_ascii=False, indent=2, default=str) + "\n")
    print("결과: %s" % OUT_JSON)

    bad = compare(res, base) if not a.write_baseline else []
    if bad:
        print("\n★ 기준선을 벗어났습니다")
        for b in bad:
            print("   " + b)
        return 1
    if not a.write_baseline:
        print("\n기준선과 같습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
