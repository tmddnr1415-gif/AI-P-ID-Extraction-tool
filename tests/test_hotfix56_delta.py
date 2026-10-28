"""hotfix56 — PID_dev 변경분 적용기: 회사에서 고친 파일은 덮지 않는다."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spike"))
import apply_delta  # noqa: E402


def _h(b):
    return hashlib.sha256(b).hexdigest()


def _setup(tmp_path):
    target = tmp_path / "PID_dev"
    pkg = tmp_path / "pkg"
    (target / "app").mkdir(parents=True)
    (target / "app" / "main.py").write_bytes(b"base main")
    (target / "app" / "lan_check.py").write_bytes(b"edited on company PC")
    (target / "app" / "_update.json").write_bytes(b'{"name": "hotfix55"}')
    files = {"app/main.py": (b"base main", b"new main"),
             "app/lan_check.py": (b"base lan", b"new lan"),
             "app/analysis_proc.py": (None, b"new file"),
             "app/_update.json": (b'{"name": "hotfix54"}', b'{"name": "hotfix56"}'),
             "app/_data/pid.db": (None, b"never")}
    man = {"name": "hotfix56", "files": []}
    for p, (old, new) in files.items():
        (pkg / "files" / p).parent.mkdir(parents=True, exist_ok=True)
        (pkg / "files" / p).write_bytes(new)
        man["files"].append({"path": p, "base_sha256": _h(old) if old else None,
                             "new_sha256": _h(new), "always": p.endswith("_update.json")})
    (pkg / "manifest.json").write_text(json.dumps(man), encoding="utf-8")
    return target, pkg, man


def test_overwrites_only_untouched_files_and_keeps_company_edits(tmp_path):
    target, pkg, man = _setup(tmp_path)
    steps, backup = apply_delta.apply(target, pkg, man)
    act = {s["path"]: s["action"] for s in steps}
    assert act == {"app/main.py": "overwrite", "app/lan_check.py": "conflict",
                   "app/analysis_proc.py": "create", "app/_update.json": "overwrite",
                   "app/_data/pid.db": "refused"}
    assert (target / "app" / "main.py").read_bytes() == b"new main"
    assert (target / "app" / "lan_check.py").read_bytes() == b"edited on company PC"
    assert (target / "app" / "lan_check.py.hotfix56.new").read_bytes() == b"new lan"
    assert (target / "app" / "analysis_proc.py").read_bytes() == b"new file"
    assert not (target / "app" / "_data").exists()
    assert (backup / "app" / "main.py").read_bytes() == b"base main"
    assert (target / "delta_hotfix56_report.txt").is_file()


def test_second_run_is_a_no_op(tmp_path):
    target, pkg, man = _setup(tmp_path)
    apply_delta.apply(target, pkg, man)
    steps, _ = apply_delta.apply(target, pkg, man)
    act = {s["path"]: s["action"] for s in steps}
    assert act["app/main.py"] == act["app/analysis_proc.py"] == "same"


def test_dry_run_changes_nothing(tmp_path):
    target, pkg, man = _setup(tmp_path)
    before = {p: p.read_bytes() for p in target.rglob("*") if p.is_file()}
    apply_delta.apply(target, pkg, man, dry=True)
    after = {p: p.read_bytes() for p in target.rglob("*") if p.is_file()}
    assert before == after


def test_refuses_the_operating_folder(tmp_path, monkeypatch, capsys):
    ops = tmp_path / "PID"
    (ops / "app").mkdir(parents=True)
    (ops / "app" / "main.py").write_text("x")
    monkeypatch.setattr(apply_delta, "HERE", tmp_path)
    (tmp_path / "manifest.json").write_text(json.dumps({"name": "h", "files": []}))
    assert apply_delta.main([str(ops)]) == 1
    assert "운영 폴더" in capsys.readouterr().out


def test_bat_files_stay_ascii():
    src = (ROOT / "spike" / "pack_delta.py").read_text(encoding="utf-8")
    import ast
    bat = next(n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "BAT")
    text = ast.literal_eval(bat.value)
    text.encode("ascii")
    assert "\r\n" in text and "chcp" not in text


def test_a_version_we_delivered_earlier_is_not_a_conflict(tmp_path):
    """hotfix57 — 앞 꾸러미(56)를 적용한 PID_dev 에 누적 꾸러미(57)를 얹어도 충돌이 아니다."""
    target, pkg, man = _setup(tmp_path)
    (target / "app" / "main.py").write_bytes(b"main from hotfix56")
    for f in man["files"]:
        if f["path"] == "app/main.py":
            f["known_sha256"] = [_h(b"main from hotfix56")]
    steps, _ = apply_delta.apply(target, pkg, man)
    assert {s["path"]: s["action"] for s in steps}["app/main.py"] == "overwrite"
    assert (target / "app" / "main.py").read_bytes() == b"new main"


def test_removes_a_file_we_delivered_but_keeps_an_edited_one(tmp_path):
    """hotfix58 — 저장소가 없앤 파일(hotfix57 시험)은 우리가 보낸 판일 때만 지운다."""
    target, pkg, man = _setup(tmp_path)
    (target / "tests").mkdir()
    (target / "tests" / "old.py").write_bytes(b"delivered by hotfix57")
    (target / "tests" / "mine.py").write_bytes(b"company edit")
    man["files"] += [{"path": "tests/old.py", "base_sha256": None, "new_sha256": None,
                      "known_sha256": [_h(b"delivered by hotfix57")], "remove": True},
                     {"path": "tests/mine.py", "base_sha256": None, "new_sha256": None,
                      "known_sha256": [_h(b"delivered")], "remove": True},
                     {"path": "tests/never.py", "base_sha256": None, "new_sha256": None,
                      "known_sha256": [], "remove": True}]
    steps, backup = apply_delta.apply(target, pkg, man)
    act = {s["path"]: s["action"] for s in steps}
    assert act["tests/old.py"] == "remove" and not (target / "tests" / "old.py").exists()
    assert (backup / "tests" / "old.py").read_bytes() == b"delivered by hotfix57"
    assert act["tests/mine.py"] == "kept" and (target / "tests" / "mine.py").exists()
    assert act["tests/never.py"] == "same"


def test_ops_takes_only_server_files_and_all_or_nothing(tmp_path):
    """hotfix60 — 운영 폴더에는 서버가 돌리는 파일(app/…)만 · 하나라도 충돌이면 아무것도 안 바꾼다."""
    target, pkg, man = _setup(tmp_path)
    man["files"].append({"path": "tests/test_x.py", "base_sha256": None, "new_sha256": _h(b"t")})
    (pkg / "files" / "tests").mkdir(parents=True, exist_ok=True)
    (pkg / "files" / "tests" / "test_x.py").write_bytes(b"t")
    before = {p: p.read_bytes() for p in target.rglob("*") if p.is_file()}
    steps, backup = apply_delta.apply(target, pkg, man, runtime_only=True, all_or_nothing=True)
    assert all(s.get("aborted") for s in steps) and backup is None          # lan_check.py 가 회사판 → 멈춤
    assert {p: p.read_bytes() for p in target.rglob("*") if p.is_file()} == before
    (target / "app" / "lan_check.py").write_bytes(b"base lan")              # 회사판이 아니면
    steps, backup = apply_delta.apply(target, pkg, man, runtime_only=True, all_or_nothing=True)
    assert {s["path"] for s in steps} == {p for p in (f["path"] for f in man["files"]) if p.startswith("app/")}
    assert not (target / "tests").exists()                                  # 시험 파일은 운영에 안 간다
    assert (target / "app" / "main.py").read_bytes() == b"new main"


def test_restore_puts_back_replaced_and_removes_created(tmp_path):
    target, pkg, man = _setup(tmp_path)
    (target / "app" / "lan_check.py").write_bytes(b"base lan")
    apply_delta.apply(target, pkg, man, runtime_only=True, all_or_nothing=True)
    assert (target / "app" / "analysis_proc.py").exists()
    b, back, gone = apply_delta.restore(target, man["name"])
    assert b is not None and gone == 1 and not (target / "app" / "analysis_proc.py").exists()
    assert (target / "app" / "main.py").read_bytes() == b"base main"
    assert (target / "app" / "lan_check.py").read_bytes() == b"base lan"


def test_ops_refuses_an_exe_install(tmp_path, monkeypatch, capsys):
    ops = tmp_path / "PID"
    (ops / "app").mkdir(parents=True)
    (ops / "app" / "main.py").write_text("x")
    (ops / "PID_Extract.exe").write_bytes(b"MZ")
    monkeypatch.setattr(apply_delta, "HERE", tmp_path)
    (tmp_path / "manifest.json").write_text(json.dumps({"name": "h", "files": []}))
    assert apply_delta.main([str(ops), "--ops", "--runtime", "--all-or-nothing"]) == 4


def test_restart_finds_only_the_listener_on_the_port():
    import restart_pid_server as r
    text = """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       4120
  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       5000
  TCP    127.0.0.1:8000         127.0.0.1:53111        ESTABLISHED     4120
  TCP    127.0.0.1:53111        127.0.0.1:8000         ESTABLISHED     7777
  TCP    [::]:8000              [::]:0                 수신 대기       4120
  TCP    0.0.0.0:18000          0.0.0.0:0              LISTENING       9999
"""
    assert r.listening_pids(8000, text) == [4120]          # 대시보드(8080) · 손님(7777) · 18000 은 아니다
    src = (ROOT / "spike" / "restart_pid_server.py").read_text(encoding="utf-8")
    assert "taskkill" in src and "/IM" not in src and "python.exe" not in src  # 이름으로 끄지 않는다


def test_ops_bats_stay_ascii():
    import pack_delta
    for t in (pack_delta.OPS_BAT, pack_delta.ROLLBACK_BAT):
        t.encode("ascii")
        assert "\r\n" in t and "chcp" not in t
    assert "--all-or-nothing" in pack_delta.OPS_BAT and "--runtime" in pack_delta.OPS_BAT
