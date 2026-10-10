"""hotfix34 — 첫 화면 오른쪽 아래의 **적용된 업데이트 딱지**.

사용자: *"업데이트가 되면 첫화면 맨 오른쪽 하단에 update 기준을 적어달라 — 언제 생성된
zip 인지, 업데이트 rev number 는 무엇인지."*  값은 꾸러미 생성기(`spike/pack_hotfix.py`)가
적는 `app/_update.json` 그대로이고, 없으면 "기록 없음" 이다 — 화면도 서버도 지어내지 않는다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


def test_a_missing_or_broken_stamp_is_none(tmp_path):
    from app import version
    assert version.update_info(tmp_path / "nope.json") is None
    bad = tmp_path / "bad.json"; bad.write_text("{not json", encoding="utf-8")
    assert version.update_info(bad) is None
    empty = tmp_path / "empty.json"; empty.write_text("{}", encoding="utf-8")
    assert version.update_info(empty) is None, "이름 없는 딱지는 딱지가 아니다"


def test_the_stamp_is_returned_as_written(tmp_path):
    from app import version
    f = tmp_path / "u.json"
    f.write_text(json.dumps({"name": "hotfix34", "rev": 34, "zip": "PID_hotfix34_2026-10-01.zip",
                             "created_at": "2026-10-01 15:00", "base_commit": "d87c758",
                             "branch": "x"}), encoding="utf-8")
    u = version.update_info(f)
    assert u == {"name": "hotfix34", "rev": 34, "zip": "PID_hotfix34_2026-10-01.zip",
                 "created_at": "2026-10-01 15:00", "base_commit": "d87c758", "branch": "x"}


def test_the_packer_writes_the_stamp_and_ships_it():
    src = (ROOT / "spike" / "pack_hotfix.py").read_text(encoding="utf-8")
    assert 'STAMP_REL = "app/_update.json"' in src
    assert "write_stamp(a.name" in src and "a.files.append(STAMP_REL)" in src
    # 딱지의 커밋은 꾸러미 자신의 커밋이 아니다 — 이름이 그렇게 말한다.
    assert '"base_commit"' in src


def test_the_version_endpoint_carries_the_stamp_and_the_footer_reads_it():
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    body = main[main.index("def build_version"):main.index("# Diagnostic export")]
    assert 'out["update"] = version.update_info()' in body
    foot = re.search(r"which build this is.*?\}\)\(\);", JS, re.S).group(0)
    assert "v.update" in foot and "업데이트 기록 없음" in foot
    assert "u.rev" in foot and "u.zip" in foot and "u.created_at" in foot
    # 딱지가 없을 때 화면이 값을 지어내지 않는다 — "기록 없음" 갈래가 있다.
    assert "hotfix34 이전" in foot


def test_the_footer_sits_bottom_right():
    css = (ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    rule = re.search(r"\.build \{ position: fixed;[^}]*\}", css).group(0)
    assert "right: 10px" in rule and "bottom: 6px" in rule and "text-align: right" in rule
