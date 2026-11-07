"""2026-11-01 사용자 결정: Valve 분석 툴 = 회사 PC Claude Code 가 개발 → 개인 꾸러미는 Valve 경로를 싣지 않았다.
2026-11-07 사용자 결정(규약 v2): 회사 업데이트 파일은 ① 대시보드 · ② 통합 두 개 — Valve 도 ② 통합에 병합해 싣는다.
그래서 company_owned 는 없고, VALVE 는 release_sources 의 병합 원본이다.  (회사 PC 쪽 배포 도구 valve_deploy_to_ops 는 그대로 남긴다.)"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "spike"))


def test_integrated_package_carries_valve_files():
    import pack_delta
    owned = pack_delta.company_owned()
    assert owned == ()                                       # 통합 꾸러미가 빼는 경로 없음
    for p in ("app/valve/api.py", "app/static/valve/valve.js", "app/main.py", "app/logic/x.py"):
        assert not (owned and p.startswith(owned)), p
    cfg = json.loads((ROOT / "config" / "release_sources.json").read_text(encoding="utf-8"))
    assert "company_owned" not in cfg
    assert cfg["sources"]["VALVE"]["branch"]                 # 통합이 VALVE 브랜치 병합을 확인한다
    assert {"LOGIC", "PANEL", "BOOKS", "VALVE"} <= set(cfg["sources"])


def test_company_deploy_copies_only_valve_files_and_rolls_back(tmp_path):
    import valve_deploy_to_ops as d
    dev, ops = tmp_path / "PID_dev", tmp_path / "PID"
    for root in (dev, ops):
        (root / "app" / "valve").mkdir(parents=True)
        (root / "app" / "static" / "valve").mkdir(parents=True)
        (root / "app" / "main.py").write_text("main " + root.name)
    (dev / "app/valve/api.py").write_text("new api")
    (ops / "app/valve/api.py").write_text("old api")
    (dev / "app/valve/globe.py").write_text("globe")             # new in dev
    (ops / "app/static/valve/old.js").write_text("gone")         # removed in dev
    (dev / "app/static/valve/valve.js").write_text("js")
    (ops / "app/static/valve/valve.js").write_text("js")
    P = d.plan(dev, ops)
    assert P == {"add": ["app/valve/globe.py"], "change": ["app/valve/api.py"], "remove": ["app/static/valve/old.js"]}
    here = tmp_path / "nospike"                                  # no restart tool → only prints
    here.mkdir()
    assert d.deploy(dev, ops, 8000, yes=True, skip_tests=True, here=here) == 0
    assert (ops / "app/valve/api.py").read_text() == "new api" and (ops / "app/valve/globe.py").exists()
    assert not (ops / "app/static/valve/old.js").exists() and (ops / "app/main.py").read_text() == "main PID"   # outside Valve: untouched
    assert d.rollback(ops, 8000, here) == 0
    assert (ops / "app/valve/api.py").read_text() == "old api" and not (ops / "app/valve/globe.py").exists()
    assert (ops / "app/static/valve/old.js").read_text() == "gone"
    shutil.rmtree(tmp_path)
