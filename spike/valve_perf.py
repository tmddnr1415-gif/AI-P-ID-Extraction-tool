#!/usr/bin/env python3
"""Performance measurement — API time AND time until the screen shows the result, cold and warm (valve29 Phase 1).

    python3 spike/valve_perf.py --data /tmp/vt_shot --label 164 [--port 8003] [--markup-all] [--out out/valve29/perf]

For one data copy (PID_DATA_DIR) it runs the server three times:
  cold    disk review cache deleted, fresh server  — the first day after an update (everything recomputed)
  restart fresh server, disk cache kept            — an ordinary morning
  warm    the same server again                    — during the day
and measures, each time, the API calls a screen makes and (Playwright, spike/valve_perf_screen.cjs) the time from the
menu click until the view is drawn and the network is idle.  Run it on COPIES of the data: it only reads, but the
cold run deletes the disk review cache of that copy.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _get(url, timeout=600):
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            b = r.read()
    except urllib.error.HTTPError:                          # an older version without this endpoint
        return None, 0, b"{}"
    return round((time.perf_counter() - t) * 1000, 1), len(b), b


def _start(data, port):
    env = dict(os.environ, PID_DATA_DIR=data)
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t = time.perf_counter()
    for _ in range(600):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/valve/version", timeout=2).read()
            return p, round((time.perf_counter() - t) * 1000)
        except Exception:                                   # noqa: BLE001
            time.sleep(0.1)
    p.kill()
    raise SystemExit("server did not start")


def api_round(base, markup_all):
    out = {}
    ms, n, b = _get(f"{base}/api/valve/projects")
    pid = json.loads(b)["projects"][0]["id"]
    out["summary"], _, b = _get(f"{base}/api/valve/projects/{pid}/summary")
    tags = json.loads(b)["tags"]
    out["issues"], size, _ = _get(f"{base}/api/valve/projects/{pid}/issues")
    out["issues_kb"] = round(size / 1024)
    out["grid"], _, _ = _get(f"{base}/api/valve/projects/{pid}/grid")
    ds = [t["id"] for t in tags[:20]]
    t = [_get(f"{base}/api/valve/datasheets/{i}")[0] for i in ds]
    out["datasheet_first"], out["datasheet_median_20"] = t[0], sorted(t)[len(t) // 2]
    rv = next((t for t in tags if len(t.get("revs") or []) > 1), None)
    if rv:
        d = json.loads(_get(f"{base}/api/valve/datasheets/{rv['id']}")[2])
        r = d["revisions"]
        out["revision_compare"], _, _ = _get(f"{base}/api/valve/compare?prev={r[-2]['id']}&new={r[-1]['id']}")
    out["process"], _, _ = _get(f"{base}/api/valve/projects/{pid}/process")
    out["pms"], _, _ = _get(f"{base}/api/valve/projects/{pid}/pms")
    out["rules_performance"], _, _ = _get(f"{base}/api/valve/projects/{pid}/rules/performance")
    out["issue_list_xlsx"], _, _ = _get(f"{base}/api/valve/projects/{pid}/issues.xlsx")
    out["valve_list_xlsx"], _, _ = _get(f"{base}/api/valve/projects/{pid}/valvelist.xlsx")
    out["markup_pdf_one_tag"], _, _ = _get(f"{base}/api/valve/projects/{pid}/markup.pdf?tag={tags[0]['tag_key']}")
    if markup_all:
        out["markup_pdf_all"], size, _ = _get(f"{base}/api/valve/projects/{pid}/markup.pdf", timeout=1800)
        out["markup_pdf_all_mb"] = round(size / 1048576, 1)
    return out


def screen_round(base):
    r = subprocess.run(["node", str(ROOT / "spike" / "valve_perf_screen.cjs"), base], capture_output=True, text=True, timeout=1800)
    line = [x for x in r.stdout.splitlines() if x.startswith("{")]
    return json.loads(line[-1]) if line else {"error": (r.stderr or r.stdout)[-400:]}


def rss_mb(pid):
    try:
        return round(int(open(f"/proc/{pid}/status").read().split("VmRSS:")[1].split()[0]) / 1024)
    except Exception:                                       # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--port", type=int, default=8003)
    ap.add_argument("--markup-all", action="store_true")
    ap.add_argument("--out", default="out/valve29/perf")
    a = ap.parse_args()
    base = f"http://127.0.0.1:{a.port}"
    res = {"label": a.label, "data": a.data}
    cache = Path(a.data) / "valve" / "cache" / "review"
    p = None
    for phase in ("cold", "restart", "warm"):
        if phase == "cold" and cache.exists():
            shutil.rmtree(cache)                            # nothing precomputed: the first day after an update
        ready = None
        if phase in ("cold", "restart"):
            if p:
                p.terminate()
                p.wait(timeout=30)
            p, ready = _start(a.data, a.port)
        res[phase] = {"server_ready_ms": ready, "api": api_round(base, a.markup_all and phase == "warm"),
                      "screen": screen_round(base), "rss_mb": rss_mb(p.pid)}
        print(phase, json.dumps(res[phase]), flush=True)
    p.terminate()
    p.wait(timeout=30)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"perf_{a.label}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res))


if __name__ == "__main__":
    main()
