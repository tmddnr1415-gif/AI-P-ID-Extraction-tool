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
            if k in b and r.get(k) != b[k]:
                bad.append("%s %s: 기준선 %s → 지금 %s" % (r["name"], k, b[k], r.get(k)))
        for ax, want in (b.get("axes") or {}).items():
            got = (r.get("axes") or {}).get(ax)
            if got != want:
                bad.append("%s 축[%s]: 기준선 %s → 지금 %s" % (r["name"], ax, want, got))
    return bad


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
        base.update({r["name"]: {k: r[k] for k in CHECK if k in r}
                     | ({"axes": r["axes"]} if "axes" in r else {})
                     for r in res if not r.get("error")})
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
