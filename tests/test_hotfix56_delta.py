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
