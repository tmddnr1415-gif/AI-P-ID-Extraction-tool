"""분석 하나가 config 를 바꾼 것이 다음 분석으로 새지 않는가 (22회차).

## 왜 이 파일이 있나

회사 PC 에서 AL NOUF1 이 분석에 실패했고, 예외 문장이 도면번호 칸을
`[963.8, 785.9, 1162.3, 805.5]` 로 적고 있었습니다 — **AL NOUF1 의 값이
아니라 그 전에 분석한 다른 양식의 값**이었습니다.

원인은 `pipeline._fit_layout` 입니다.  프로필이 그 문서의 것이 아니면 잰 값을
`CFG.overlay(...)` 로 **모듈 전역 `CFG.data` 에 제자리 기록**하고 되돌리는
코드가 없었습니다.  그 다음 문서가 AL NOUF1 이면 "내 프로필이 맞다" 고 판단해
**다시 재지 않고** 앞 문서가 남긴 값을 씁니다.

`_HIST_ROWS`(21회차에 고친 것)와 같은 종류의 결함이 한 층 위에 있었습니다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import pipeline                                    # noqa: E402

GEOMETRY = ("regions.drawing_area", "sheet.width_pt", "sheet.height_pt",
            "title_block.dwg_no_region", "title_block.title_region",
            "title_block.rev_box", "title_block.sheet_box")


def _snapshot():
    return {k: pipeline.CFG.get(k) for k in GEOMETRY}


def _stranger(path: Path, width=1191.0, height=842.0, pages=3):
    """다른 회사 양식처럼 생긴 합성 PDF — 이 도구의 A1 좌표가 안 맞는다."""
    doc = pymupdf.open()
    for i in range(pages):
        pg = doc.new_page(width=width, height=height)
        pg.insert_text(pymupdf.Point(80, 80), f"SHEET {i + 1}", fontsize=18)
        pg.draw_line(pymupdf.Point(100, 400), pymupdf.Point(900, 400), width=0.5)
    doc.save(path)
    doc.close()
    return path


def test_a_failed_analysis_leaves_the_config_as_it_found_it(tmp_path):
    """실패해도 되돌린다 — 그러지 않으면 다음 분석이 이유 없이 이상해진다."""
    before = _snapshot()
    with pytest.raises(pipeline.TitleBlockUnreadable):
        pipeline.analyse(_stranger(tmp_path / "stranger.pdf"))
    assert _snapshot() == before


def test_the_module_layouts_are_put_back_too(tmp_path):
    """`CFG` 만 되돌리면 모자란다 — 그 값으로 만들어 둔 것들도 되돌려야 한다."""
    from app.engine import extract_titleblocks as tb
    from app.engine import detect_symbols as ds
    before = (tb.LAYOUT.dwg_no_region, ds.LAYOUT)
    with pytest.raises(pipeline.TitleBlockUnreadable):
        pipeline.analyse(_stranger(tmp_path / "stranger2.pdf"))
    assert (tb.LAYOUT.dwg_no_region, ds.LAYOUT) == before


def test_pidcache_globals_are_put_back_too(tmp_path):
    """★ `CFG` 와 layout 만으로는 모자랍니다 — `pidcache` 도 전역 둘을 듭니다.

    `rename_projects` 가 `global PROJECT_NAME_REGION, PROJECT_NAME_MIN_HEIGHT`
    로 모듈 전역에 영구히 씁니다.  남으면 다음 문서의 프로젝트명을 **남의
    자리**에서 읽고, `analysis_scope` 가 달라지고, 그것을 보는
    `derive_connector_reach` 가 세는 장이 달라집니다.

    실측(22회차): 이것 하나 때문에 커넥터가 218 -> 219 로 세어지고 지문이
    `fb85b039` -> `f21626fd` 로 움직였습니다.  **행 1037개는 전부 같았습니다** —
    판정이 아니라 세는 대상이 달라진 것이라 더 알아채기 어렵습니다.
    """
    import pidcache
    before = (pidcache.PROJECT_NAME_REGION, pidcache.PROJECT_NAME_MIN_HEIGHT)
    with pytest.raises(pipeline.TitleBlockUnreadable):
        pipeline.analyse(_stranger(tmp_path / "stranger3.pdf"))
    assert (pidcache.PROJECT_NAME_REGION, pidcache.PROJECT_NAME_MIN_HEIGHT) == before


def test_every_module_global_the_pipeline_writes_is_restored():
    """되돌려야 하는 것을 빠뜨리지 않는다 — 엔진의 `global` 문을 전수로 센다.

    `detect_valves` 의 것은 `main()`(CLI) 안이라 파이프라인 경로가 아니다.
    새 `global` 이 파이프라인 경로에 생기면 이 시험이 먼저 걸린다.
    """
    import re
    root = ROOT / "app"
    found = []
    for path in sorted(root.rglob("*.py")):
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.match(r"\s+global ", line):
                found.append((path.relative_to(root).as_posix(), i, line.strip()))
    known = {
        ("engine/pidcache.py", "global PROJECT_NAME_REGION, PROJECT_NAME_MIN_HEIGHT"),
        ("engine/detect_valves.py", "global LAYOUT"),   # CLI main() 안 — 파이프라인 아님
    }
    assert {(f, t) for f, _i, t in found} == known, found
    # pidcache 의 둘은 `_rebind_config` 이 되돌린다
    src = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    rebind = src.split("def _rebind_config(")[1].split("\ndef ")[0]
    assert "pidcache.PROJECT_NAME_REGION" in rebind
    assert "pidcache.PROJECT_NAME_MIN_HEIGHT" in rebind


def test_the_guard_is_one_place_and_wraps_the_whole_analysis():
    """되돌리기는 `analyse` **하나**가 한다 — 갈래마다 두면 언젠가 새는 갈래가 생긴다."""
    src = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    guard = src.split("def analyse(")[1].split("\ndef _analyse(")[0]
    assert "copy.deepcopy(CFG.data)" in guard
    assert "finally:" in guard              # 실패해도 되돌린다
    assert "_rebind_config()" in guard
    # 되돌리는 코드는 한 벌만 있다
    assert src.count("copy.deepcopy(CFG.data)") == 1
    # `_rebind_config` 는 `_reconfigure` 도 쓴다 — 두 벌이 아니다
    recfg = src.split("def _reconfigure(")[1].split("\ndef ")[0]
    assert "_rebind_config()" in recfg


def test_the_measured_geometry_is_kept_so_a_new_form_can_be_configured():
    """잰 값을 저장한다 — 새 양식의 설정을 만들려면 그 값이 필요하다."""
    # ★ 저장은 이미 되고 있었다 — `applied_rules` 안이다.  새로 담지 않는다.
    db_src = (ROOT / "app/db.py").read_text(encoding="utf-8")
    store = db_src.split("def store_result(")[1].split("\ndef ")[0]
    assert '"applied_rules"' in store
    pipe = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    assert '"layout": layout,' in pipe and '"applied_rules": applied' in pipe
    main_src = (ROOT / "app/main.py").read_text(encoding="utf-8")
    assert main_src.count('@app.get("/jobs/{job_id}/measured_config")') == 1
    route = main_src.split('@app.get("/jobs/{job_id}/measured_config")')[1] \
                    .split("\n@app.")[0]
    # 재지 못하는 항목은 지어내지 않고 "사람이 재야 한다" 로 이름만 낸다
    assert "must_measure_by_hand" in route
    assert "hist_rule_y" in route
