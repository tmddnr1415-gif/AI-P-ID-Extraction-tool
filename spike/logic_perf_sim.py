"""LOGIC 검토 — 사용자가 하는 일을 되풀이해 시간 · 메모리를 잰다 (L47).

    PID_DATA_DIR=<사본> python3 spike/logic_perf_sim.py <job> [--rounds 3] [--out <json>]

서버 안의 라우터를 TestClient 로 직접 부른다 (판정 0줄 · 사본 데이터에서만).  재는 것:
결과 처음 읽기 · 시트 목록 · 시트 열기 · 그림 · 묶음 시뮬레이션(처음 · 같은 입력 · 입력 바꿈 · 시트 옮김) ·
누름단추 · 예시 · 순차 동작(명령 목록 · 조건 나무 · 한 단계 효과) · 점검 · 검토 · 식별률 · 가르치기 · 그룹 ·
사람 값 저장 뒤 다시 읽기 · 메모.
"""
from __future__ import annotations

import argparse
import json
import os
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("PID_LOGIC_WARM", "0")

from fastapi import FastAPI                    # noqa: E402
from fastapi.testclient import TestClient      # noqa: E402

from app.logic import api, store              # noqa: E402


def rss_mb():
    return int(open("/proc/self/statm").read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1e6


class T:
    def __init__(self):
        self.rows = []

    def __call__(self, name, fn, n=1):
        ts = []
        out = None
        for _ in range(n):
            t0 = time.perf_counter()
            out = fn()
            ts.append(time.perf_counter() - t0)
        ts.sort()
        self.rows.append({"name": name, "n": n, "med_ms": round(ts[len(ts) // 2] * 1000, 1),
                          "max_ms": round(ts[-1] * 1000, 1), "rss_mb": round(rss_mb())})
        print(f"{name:48s} {self.rows[-1]['med_ms']:9.1f} ms  (max {self.rows[-1]['max_ms']:.1f})  rss {self.rows[-1]['rss_mb']} MB", flush=True)
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("job")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    job = a.job
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    t = T()
    base = f"/logic/api/jobs/{job}"

    def get(url):
        r = c.get(base + url)
        assert r.status_code == 200, (url, r.status_code, r.text[:200])
        return r

    def post(url, body):
        r = c.post(base + url, json=body)
        assert r.status_code == 200, (url, r.status_code, r.text[:200])
        return r

    print(f"rss at start {rss_mb():.0f} MB")
    t("결과 처음 읽기 (/sheets cold)", lambda: get("/sheets").json())
    sh = t("시트 목록 (/sheets warm)", lambda: get("/sheets").json(), a.rounds)
    sheets = sh["sheets"]
    pages = [s["page"] for s in sheets]
    pick = pages[:: max(1, len(pages) // 12)][:12] or pages
    t("시트 열기 ×12 (/sheet)", lambda: [get(f"/sheet/{p}").json() for p in pick])
    t("시트 열기 다시 ×12", lambda: [get(f"/sheet/{p}").json() for p in pick], a.rounds)
    t("그림 ×4 (/page.png)", lambda: [get(f"/page/{p}.png") for p in pick[:4]])
    # 첫 입력 행이 있는 장
    first = None
    for p in pick:
        s = get(f"/sheet/{p}").json()
        rows = [r for r in s.get("rows", []) if r.get("side") == "L"]
        if rows:
            first = (p, rows[0]["n"], s)
            break
    if first is None:
        first = (pick[0], 1, get(f"/sheet/{pick[0]}").json())
    p0, n0, s0 = first
    body = {"forces": {str(p0): {f"row:{n0}": 1}}, "page": p0}
    t("묶음 시뮬레이션 처음 (/simulate)", lambda: post("/simulate", body).content)
    t("묶음 시뮬레이션 같은 입력", lambda: post("/simulate", body).content, a.rounds)
    t("묶음 시뮬레이션 시트 옮김", lambda: post("/simulate", {**body, "page": pick[1]}).content, a.rounds)
    other = {"forces": {str(p0): {f"row:{n0}": 0}}, "page": p0}
    t("묶음 시뮬레이션 입력 바꿈", lambda: post("/simulate", other).content, a.rounds)
    t("시트 시뮬레이션 (/sheet/simulate)", lambda: post(f"/sheet/{p0}/simulate", {"forces": {f"row:{n0}": 1}}).content, a.rounds)
    t("따라가기 (/trace)", lambda: post(f"/sheet/{p0}/trace", {"start": f"row:{n0}", "direction": "down"}).content, a.rounds)
    outs = [r for r in s0.get("rows", []) if r.get("side") == "R"]
    if outs:
        t("예시 (/scenario)", lambda: post(f"/sheet/{p0}/scenario", {"target": f"row:{outs[0]['n']}"}).content, a.rounds)
    pbs = [bid for bid, b in s0.get("blocks", {}).items() if b.get("func") in ("PB", "BUTTON", "PUSHBUTTON")]
    if pbs:
        t("누름단추 (/press)", lambda: post(f"/sheet/{p0}/press", {"block": pbs[0], "forces": {}}).content, a.rounds)
    cmds = t("명령 목록 (/commands)", lambda: get("/commands").json(), a.rounds)
    cl = cmds.get("commands") or cmds.get("items") or []
    if cl:
        c0 = cl[0]["actions"][0]["rows"][0]
        print("   첫 명령:", cl[0]["equip"], c0["sheet"], c0["row"])
        t("순차 동작 조건 나무 (/sequence)", lambda: post("/sequence", {"page": c0["page"], "row": c0["row"]}).json(), a.rounds)
        t("순차 동작 미리 돌리기 (/sequence/try ×4)", lambda: post("/sequence/try", {"page": c0["page"], "net": "row:%d" % c0["row"], "forces": {}, "options": [{} for _ in range(4)]}).content, a.rounds)
        t("순차 동작 한 단계 효과 (/sequence/effect)", lambda: post("/sequence/effect", {"page": c0["page"], "net": "row:%d" % c0["row"], "forces": {}, "add": {str(p0): {"row:%d" % n0: 1}}}).content, a.rounds)
    t("점검 목록 (/findings)", lambda: get("/findings").json(), a.rounds)
    t("From-To 보고 (/fromto)", lambda: get("/fromto").json(), a.rounds)
    t("식별률 (/idrate)", lambda: get("/idrate").json(), a.rounds)
    t("가르치기 (/teach)", lambda: get("/teach").json(), a.rounds)
    t("검토 결과 (/review)", lambda: get("/review").json(), a.rounds)
    t("그룹 (/groups)", lambda: get("/groups").json(), a.rounds)
    t("Excel 보고서 (/report.xlsx)", lambda: get("/report.xlsx").content)
    t("메모 (/memo)", lambda: get("/memo").json(), a.rounds)
    # 사람 값 저장 뒤
    bl = next(iter(s0.get("blocks", {})), None)
    if bl:
        tm = {"page": p0, "block": bl, "sec": 7, "author": "perf"}
        t("타이머 저장 (/overrides/timer)", lambda: post("/overrides/timer", tm).content)
        t("저장 뒤 시트 다시 (/sheet)", lambda: get(f"/sheet/{p0}").json())
        t("저장 뒤 묶음 시뮬레이션", lambda: post("/simulate", body).content)
        t("저장 뒤 시트 목록", lambda: get("/sheets").json())
    print(f"rss at end {rss_mb():.0f} MB · maxrss {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MB")
    if a.out:
        Path(a.out).write_text(json.dumps(t.rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
