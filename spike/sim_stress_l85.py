"""L85 — 작성 시뮬레이션 누르기 흉내: 묶음의 장을 무작위로 골라 왼쪽 행에 무작위 0/1 을 주고 /simulate 를 부른다
(화면처럼 앞 상태를 이어 준다).  걸린 시간 · 오류 · 모순 · 끝없는 되먹임 알림을 센다.

  python3 spike/sim_stress_l85.py <주소> <묶음 id> [횟수=300] [out.json]"""
import json, random, sys, time, urllib.request
B, sid = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 300
OUT = sys.argv[4] if len(sys.argv) > 4 else "sim_stress.json"


def call(method, u, body=None):
    r = urllib.request.Request(B + u, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json"}, method=method)
    return json.loads(urllib.request.urlopen(r, timeout=600).read())


sheets = call("GET", f"/logic/api/drawings/sets/{sid}")["sheets"]
rng = random.Random(851)
lat, errs, notes, state = [], [], {}, {}
first = None
for k in range(N):
    sh = rng.choice(sheets)
    doc = call("GET", f"/logic/api/drawings/{sh['id']}")
    rows = [int(n) for n, c in (doc.get("left") or {}).items()] or list(range(1, 8))
    forces = {sh["id"]: {f"row:{n}": rng.randint(0, 1) for n in rng.sample(rows, min(len(rows), rng.randint(1, 6)))}}
    t = time.time()
    try:
        r = call("POST", f"/logic/api/drawings/{sh['id']}/simulate", {"forces": forces, "state": state})
    except Exception as e:
        errs.append({"sheet": sh["sheet_no"], "err": repr(e)[:200]}); continue
    dt = time.time() - t
    if first is None:
        first = dt
    lat.append((dt, sh["sheet_no"]))
    if r.get("error"):
        errs.append({"sheet": sh["sheet_no"], "err": r["error"][:200]})
    state = r.get("state") or {}
    for n in r.get("notes") or []:
        key = str(n)[:80]
        notes[key] = notes.get(key, 0) + 1
lat.sort()
v = [x for x, _ in lat]
rep = {"calls": len(lat), "first": round(first or 0, 2), "p50": round(v[len(v) // 2], 3), "p95": round(v[int(len(v) * .95)], 3),
       "max": round(v[-1], 3), "slowest": [(round(x, 2), s) for x, s in lat[-8:]], "errors": errs[:20], "n_errors": len(errs),
       "notes": sorted(notes.items(), key=lambda kv: -kv[1])[:15]}
open(OUT, "w").write(json.dumps(rep, ensure_ascii=False, indent=1))
print(json.dumps(rep, ensure_ascii=False)[:1500])
