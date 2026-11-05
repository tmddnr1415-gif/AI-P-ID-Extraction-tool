"""hotfix132 — 출시 전 검사(spike/release_check.py) 와 꾸러미 게이트(spike/pack_delta.py)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))
import pack_delta  # noqa: E402
import release_check as rc  # noqa: E402


# ---------------------------------------------------------------- release_check
def test_parse_pytest_reads_summary_skips_and_failures():
    out = """
..s.F
SKIPPED [1] tests/test_determinism.py:12: sample PDF not present
SKIPPED [2] tests/test_x.py:3: node 없음
FAILED tests/test_a.py::test_b - AssertionError: x
=================== 1 failed, 3 passed, 3 skipped in 2.0s ===================
"""
    r = rc.parse_pytest(out)
    assert r["summary"].startswith("1 failed, 3 passed")
    assert r["skipped"] == ["tests/test_determinism.py:12: sample PDF not present", "tests/test_x.py:3: node 없음"]
    assert r["failed"] == ["tests/test_a.py::test_b"]


def test_strict_fails_on_missing_drawing_data_only():
    steps = {"pytest": {"ok": True, "summary": "10 passed", "skipped": ["t.py:1: sample PDF not present", "u.py:2: node 없음"]},
             "node": {"ok": True, "checked": 3, "failed": []}, "smoke": {"ok": True, "failed": []},
             "screens": {"ok": True, "skipped": "playwright 없음 — 화면 점검을 건너뜀"}}
    ok, failures, skipped = rc.judge(steps, strict=False)
    assert ok and not failures and len(skipped) == 3
    ok, failures, _ = rc.judge(steps, strict=True)
    assert not ok and "--strict" in failures[0] and "PDF" in failures[0]


def test_a_failed_step_fails_the_whole_check():
    steps = {"pytest": {"ok": True, "skipped": []}, "node": {"ok": False, "failed": ["app/static/x.js: SyntaxError"]},
             "smoke": {"ok": True, "failed": []}}
    ok, failures, _ = rc.judge(steps, strict=False)
    assert not ok and failures == ["node: app/static/x.js: SyntaxError"]


def test_js_targets_skip_minified_vendor_and_company_files():
    files = [p.relative_to(rc.STATIC).as_posix() for p in rc.js_files()]
    assert "app.js" in files and "logic.js" in files
    assert not any(f.endswith(".min.js") or f.startswith("valve/") or "/vendor/" in f for f in files)


def test_main_writes_the_result_with_head_and_uses_a_temp_data_folder(tmp_path, monkeypatch):
    seen = {}

    def fake_pytest(env, extra=None):
        seen["data"] = env["PID_DATA_DIR"]
        return {"ok": True, "summary": "5 passed", "skipped": [], "failed": []}

    monkeypatch.setattr(rc, "run_pytest", fake_pytest)
    monkeypatch.setattr(rc, "run_valve", lambda env: True)
    monkeypatch.setattr(rc, "run_node_check", lambda: {"ok": True, "checked": 1, "failed": []})
    monkeypatch.setattr(rc, "run_smoke", lambda env: {"ok": True, "pages": [], "failed": []})
    out = tmp_path / "rc.json"
    assert rc.main(["--no-screens", "--out", str(out)]) == 0
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["ok"] and r["head"] == rc.git_head() and r["valve_ok"] is True
    assert "app" not in Path(seen["data"]).parts[-3:] and not Path(seen["data"]).exists()   # 임시 폴더 · 끝나면 지움


# ---------------------------------------------------------------- pack_delta 게이트
def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()


def test_gate_blocks_without_a_result(tmp_path):
    reasons = pack_delta.release_gate(_head(), tmp_path / "none.json")
    assert reasons and "release_check" in reasons[0]


def test_gate_blocks_a_failed_result_and_passes_a_good_one(tmp_path):
    f = tmp_path / "rc.json"
    f.write_text(json.dumps({"head": _head(), "ok": False, "dirty": False, "failures": ["pytest: 1 failed"]}),
                 encoding="utf-8")
    reasons = pack_delta.release_gate(_head(), f)
    assert len(reasons) == 1 and "1 failed" in reasons[0]
    f.write_text(json.dumps({"head": _head(), "ok": True, "dirty": False}), encoding="utf-8")
    assert pack_delta.release_gate(_head(), f) == []


def test_gate_refuses_a_check_run_on_uncommitted_changes(tmp_path):
    f = tmp_path / "rc.json"
    f.write_text(json.dumps({"head": _head(), "ok": True, "dirty": True, "dirty_files": ["app/main.py"]}), encoding="utf-8")
    reasons = pack_delta.release_gate(_head(), f)
    assert len(reasons) == 1 and "커밋하지 않은 변경" in reasons[0] and "app/main.py" in reasons[0]
    f.write_text(json.dumps({"head": _head(), "ok": True}), encoding="utf-8")       # 옛 결과(기록 없음)도 다시 검사
    assert pack_delta.release_gate(_head(), f) and "dirty" in pack_delta.release_gate(_head(), f)[0]


def test_release_check_records_the_dirty_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(rc, "run_pytest", lambda env, extra=None: {"ok": True, "summary": "1 passed", "skipped": [], "failed": []})
    monkeypatch.setattr(rc, "run_valve", lambda env: True)
    monkeypatch.setattr(rc, "run_node_check", lambda: {"ok": True, "checked": 1, "failed": []})
    monkeypatch.setattr(rc, "run_smoke", lambda env: {"ok": True, "pages": [], "failed": []})
    monkeypatch.setattr(rc, "git_dirty", lambda: ["app/main.py"])
    out = tmp_path / "rc.json"
    rc.main(["--no-screens", "--out", str(out)])
    r = json.loads(out.read_text(encoding="utf-8"))
    assert r["dirty"] is True and r["dirty_files"] == ["app/main.py"]
    monkeypatch.setattr(rc, "git_dirty", lambda: [])
    rc.main(["--no-screens", "--out", str(out)])
    assert json.loads(out.read_text(encoding="utf-8"))["dirty"] is False


def test_git_dirty_ignores_out_folder(tmp_path, monkeypatch):
    _git(tmp_path, "init", "-q")
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "x.json").write_text("{}")
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    assert rc.git_dirty() == []
    (tmp_path / "a.py").write_text("x")
    assert rc.git_dirty() == ["a.py"]


def test_gate_blocks_when_code_changed_after_the_check(tmp_path):
    first = subprocess.check_output(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=ROOT, text=True).split()[0][:9]
    f = tmp_path / "rc.json"
    f.write_text(json.dumps({"head": first, "ok": True, "dirty": False}), encoding="utf-8")
    reasons = pack_delta.release_gate(_head(), f)
    assert reasons and "다시 검사" in reasons[0]


def test_doc_only_difference_keeps_the_check_valid():
    assert pack_delta._doc_only(["out/hotfix132/readme_head.txt", "docs/handoff/pid.md", "README.md"])
    assert not pack_delta._doc_only(["docs/a.md", "app/main.py"])


def _git(cwd, *a):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def two_repos(tmp_path, monkeypatch):
    """origin(다른 세션 브랜치 흉내) 과 그것을 받은 작업 저장소."""
    origin, work = tmp_path / "origin", tmp_path / "work"
    origin.mkdir()
    _git(origin, "init", "-q", "-b", "main")
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        _git(origin, "config", k, v)
    (origin / "a.txt").write_text("1")
    _git(origin, "add", "a.txt")
    _git(origin, "commit", "-q", "-m", "one")
    _git(origin, "branch", "logic-session")
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        _git(work, "config", k, v)
    (work / "config").mkdir()
    (work / "config" / "release_sources.json").write_text(json.dumps({"sources": {"LOGIC": {"branch": "logic-session"}}}))
    monkeypatch.setattr(pack_delta, "ROOT", work)
    monkeypatch.setattr(pack_delta, "SOURCES_FILE", work / "config" / "release_sources.json")
    monkeypatch.setattr(pack_delta, "CHECK_FILE", tmp_path / "release_check.json")
    return origin, work


def test_unmerged_sources_counts_commits_not_in_head(two_repos):
    origin, work = two_repos
    assert pack_delta.unmerged_sources() == []
    _git(origin, "checkout", "-q", "logic-session")
    (origin / "b.txt").write_text("2")
    _git(origin, "add", "b.txt")
    _git(origin, "commit", "-q", "-m", "logic change")
    missing = pack_delta.unmerged_sources()
    assert len(missing) == 1 and "1개" in missing[0] and "logic change" in missing[0]


def test_main_stops_with_2_when_unmerged_and_3_without_a_check(two_repos, monkeypatch, capsys):
    origin, work = two_repos
    _git(origin, "checkout", "-q", "logic-session")
    (origin / "b.txt").write_text("2")
    _git(origin, "add", "b.txt")
    _git(origin, "commit", "-q", "-m", "logic change")
    monkeypatch.setattr(sys, "argv", ["pack_delta.py", "--name", "hotfix999", "--ops"])
    assert pack_delta.main() == 2
    monkeypatch.setattr(sys, "argv", ["pack_delta.py", "--name", "hotfix999", "--ops", "--allow-unmerged"])
    assert pack_delta.main() == 3
    assert "만들지 않습니다" in capsys.readouterr().out
    assert not list((ROOT / "out").glob("*hotfix999*"))
