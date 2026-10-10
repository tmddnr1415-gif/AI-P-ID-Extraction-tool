"""꾸러미 r55 적용 검증 — 단계마다 사실만 적는다 (48회차 방식).

    python3 spike/verify_r55.py <단계...>

단계는 이름으로 부른다.  각 단계는 `out/round55/verify/<이름>.json` 에 결과를
쓰고, 안 돌린 단계는 파일이 없어 README 가 **"안 돌림"** 으로 적는다.
★ 실 DB 를 열지 않는다 — `PID_DATA_DIR` 을 워크트리 밖 임시 폴더로 돌린다.
"""
from __future__ import annotations
import hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path

ROOT = Path("/home/user/AI-P-ID-Extraction-tool")
TREE = Path("/tmp/v55_tree")
DATA = Path("/tmp/v55_data")
OUT = ROOT / "out" / "round55" / "verify"
OUT.mkdir(parents=True, exist_ok=True)
REAL = ROOT / "app" / "_data" / "app.db"


def save(name, **facts):
    facts["at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (OUT / f"{name}.json").write_text(json.dumps(facts, ensure_ascii=False, indent=1))
    print(name, json.dumps(facts, ensure_ascii=False)[:400], flush=True)


def run(cmd, cwd, env=None, timeout=2400):
    e = dict(os.environ, PID_DATA_DIR=str(DATA), PYTHONPATH=str(cwd), **(env or {}))
    t = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    p = subprocess.run(cmd, cwd=str(cwd), env=e, capture_output=True, text=True, timeout=timeout)
    rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return p, time.perf_counter() - t, max(rss, before) / 1024 / 1024


ANALYSE = """
import json, sys, time
sys.path.insert(0, %r)
from app import pipeline
t = time.time()
res = pipeline.analyse(%r)
res["fingerprint"] = pipeline.fingerprint(res)
rows = res["rows"]
print(json.dumps({"rows": len(rows), "fp": res.get("fingerprint"),
                  "qty": sum((r.get("qty") or 0) for r in rows),
                  "sec": round(time.time() - t, 1)}))
json.dump(res, open(%r, "w"))
"""


def step_old_analyse():
    """① 옛 코드(aac64ba)로 AL NOUF1 — 824행이 나오는가."""
    code = ANALYSE % (str(TREE), str(ROOT / "data" / "pid_total.pdf"), "/tmp/v55_old.json")
    p, sec, rss = run([sys.executable, "-c", code], TREE)
    save("1_old_analyse", ok=p.returncode == 0, out=p.stdout.strip()[-300:],
         err=p.stderr.strip()[-400:], sec=round(sec), rss_gb=round(rss, 2))


def step_unpack():
    """⑤ 꾸러미를 그 워크트리에 풀고 HEAD 와 바이트로 대조한다."""
    import zipfile
    inner = ROOT / "out" / "round55" / "3_FILES_TO_OVERWRITE.zip"
    names, diff = [], []
    with zipfile.ZipFile(inner) as z:
        names = z.namelist()
        z.extractall(TREE)
    for n in names:
        a = (TREE / n).read_bytes()
        b = subprocess.run(["git", "show", f"HEAD:{n}"], cwd=str(ROOT),
                           capture_output=True).stdout
        if a != b:
            diff.append(n)
    save("5_unpack", files=len(names), different=len(diff), which=diff[:10],
         forbidden=[n for n in names if n.startswith("app/_data")])


def step_new_analyse():
    code = ANALYSE % (str(TREE), str(ROOT / "data" / "pid_total.pdf"), "/tmp/v55_new.json")
    p, sec, rss = run([sys.executable, "-c", code], TREE)
    save("8_new_analyse", ok=p.returncode == 0, out=p.stdout.strip()[-300:],
         err=p.stderr.strip()[-400:], sec=round(sec), rss_gb=round(rss, 2))


def step_dxf_zip():
    """⑪ 푼 그 코드로 DXF zip — 449행 · 003078d7."""
    code = ANALYSE % (str(TREE), str(ROOT / "data" / "uad_dxf.zip"), "/tmp/v55_dxf.json")
    p, sec, rss = run([sys.executable, "-c", code], TREE)
    save("11_dxf_zip", ok=p.returncode == 0, out=p.stdout.strip()[-300:],
         err=p.stderr.strip()[-400:], sec=round(sec), rss_gb=round(rss, 2))


def step_tests():
    p, sec, _ = run([sys.executable, "-m", "pytest", "-q", "-m", "not slow and not ui",
                     "--no-header"], TREE, timeout=1800)
    tail = [l for l in p.stdout.splitlines() if "passed" in l or "failed" in l]
    save("15_tests", ok=p.returncode == 0, line=tail[-1] if tail else p.stdout[-200:],
         sec=round(sec))


def step_realdb():
    save("17_realdb", sha256=hashlib.sha256(REAL.read_bytes()).hexdigest())



EDIT_CODE = """
import json, sys, time
sys.path.insert(0, %r)
from app import db, revisions
from app.paths import data_dir
DATA_DIR = data_dir()
res = json.load(open(%r))
con = db.connect(DATA_DIR / "app.db")
job = "v55oldjob0001"
revisions.create_project(DATA_DIR, "AL NOUF1")
con.execute("INSERT OR REPLACE INTO job (id, pdf_name, pdf_sha256, pdf_path, created_at,"
            " status, progress, message, fingerprint, project, revision)"
            " VALUES (?,?,?,?,?,'done',1.0,'',?,?,?)",
            (job, "pid_total.pdf", "x" * 64, %r, time.time(),
             res.get("fingerprint", ""), "AL NOUF1", "A"))
con.commit()
db.store_result(con, job, res)
con.commit()
keys = [r["key"] for r in res["rows"][:5]]
for i, k in enumerate(keys):
    db.set_user_value(con, job, k, "remark", "검증 편집 %%d" %% i)
con.commit()
got = [r for r in db.merged_rows(con, job) if r["key"] in keys]
print(json.dumps({"rows": len(res["rows"]), "edited": sum(
    1 for r in got if (r.get("user") or {}).get("remark", "").startswith("검증 편집"))}))
"""


def step_edits():
    """②③ 옛 분석본을 DB 에 넣고 다섯 칸을 사람이 고친 것으로 만든다."""
    code = EDIT_CODE % (str(TREE), "/tmp/v55_old.json", str(ROOT / "data" / "pid_total.pdf"))
    p, sec, _ = run([sys.executable, "-c", code], TREE)
    save("2_edits", ok=p.returncode == 0, out=p.stdout.strip()[-200:], err=p.stderr.strip()[-400:])


OPEN_CODE = """
import json, sys
sys.path.insert(0, %r)
from app import db
from app.paths import data_dir
DATA_DIR = data_dir()
con = db.connect(DATA_DIR / "app.db")
rows = db.merged_rows(con, "v55oldjob0001")
kept = [r for r in rows if (r.get("user") or {}).get("remark", "").startswith("검증 편집")]
print(json.dumps({"rows": len(rows), "edits_alive": len(kept),
                  "remarks": sorted(r["user"]["remark"] for r in kept),
                  "values_show_it": sum(1 for r in kept if r["values"]["remark"] == r["user"]["remark"])}))
"""


def step_open():
    """⑥⑦ 새 코드로 그 분석을 다시 연다 — 행도 편집도 살아 있는가 (재분석 없이)."""
    code = OPEN_CODE % str(TREE)
    p, sec, _ = run([sys.executable, "-c", code], TREE)
    save("6_open_after_upgrade", ok=p.returncode == 0, out=p.stdout.strip()[-300:],
         err=p.stderr.strip()[-400:], sec=round(sec, 1))


STEPS = {"old": step_old_analyse, "edits": step_edits, "unpack": step_unpack,
         "open": step_open, "new": step_new_analyse,
         "dxf": step_dxf_zip, "tests": step_tests, "realdb": step_realdb}

if __name__ == "__main__":
    for name in sys.argv[1:]:
        STEPS[name]()
