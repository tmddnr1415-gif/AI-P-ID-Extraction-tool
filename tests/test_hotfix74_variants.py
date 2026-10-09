"""hotfix74 — 입력 변형 시뮬레이션(`spike/variant_inputs.py` · `spike/dxf_variants.py`)이 잡은 결함.

① 범례 장만 든 PDF 가 행 0개로 조용히 성공했다 → `NoPidSheets` 로 사람 말로 멈춘다.
② DXF 묶음이 전부 깨졌거나 범례가 없으면 행 0개로 조용히 성공했다 → 같은 세 예외로 멈춘다.
③ 같은 DXF 가 두 번 들어오면 행이 갑절이 됐다 · macOS `._` 찌꺼기가 실패 장이 됐다 → 건너뛰고 이름을 남긴다.
"""
from __future__ import annotations

import ast
import io
import zipfile
from pathlib import Path

import pytest

from app import analysis_proc, main, pipeline
from app.engine import dxf_reader

ROOT = Path(__file__).resolve().parent.parent


def _zip(tmp_path, entries, name="s.zip"):
    p = tmp_path / name
    with zipfile.ZipFile(p, "w") as z:
        for n, b in entries:
            z.writestr(n, b)
    return p


def test_identical_dxf_and_macos_junk_are_skipped_with_a_reason(tmp_path):
    a = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"
    p = _zip(tmp_path, [("001. a.dxf", a), ("copy of 001. a.dxf", a), ("002. b.dxf", a + b"\n"),
                        ("__MACOSX/._001. a.dxf", b"\0\5\x16\7junk"), ("readme.txt", b"x")])
    got, skipped = dxf_reader.list_inputs(p)
    names = [n for n, _ in got]
    assert names == ["001. a.dxf", "002. b.dxf"]          # 내용이 1바이트라도 다르면 둘 다 읽는다
    joined = " ".join(skipped)
    assert "copy of 001. a.dxf (내용이 001. a.dxf 와 같음" in joined
    assert "macOS" in joined and "readme.txt" in joined


def test_dxf_bundle_of_garbage_stops_in_words(tmp_path):
    p = _zip(tmp_path, [("a.dxf", b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"),
                        ("b.dxf", b"not a dxf at all")])
    # 다른 시험이 `app.*` 를 다시 읽으면 예외 클래스가 두 벌이 된다 — 이름으로 본다.
    with pytest.raises(Exception) as e:
        pipeline.analyse(p)
    assert type(e.value).__name__ in ("NoTextLayer", "TitleBlockUnreadable", "LegendUnavailable")
    msg = str(e.value)
    assert any("가" <= ch <= "힣" for ch in msg)


def test_dxf_stops_are_checked_before_any_row_is_made():
    src = (ROOT / "app/dxf_pipeline.py").read_text(encoding="utf-8")
    i_raise = src.index("raise P.LegendUnavailable(")
    i_rows = src.index("roles = attribute_roles(")
    assert i_raise < i_rows
    assert '"roles_note"' in src


def test_pdf_with_no_pid_sheet_stops_instead_of_succeeding_empty():
    src = Path(pipeline.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    raised = {ast.unparse(n.exc.func) for n in ast.walk(tree)
              if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call)}
    assert "NoPidSheets" in raised
    i_targets = src.index('targets = [pc for pc in pages')
    i_raise = src.index("raise NoPidSheets(")
    assert 0 < i_raise - i_targets < 1500                  # targets 를 정한 바로 뒤에서


def test_new_known_failure_is_wired_like_the_others():
    msrc = Path(main.__file__).read_text(encoding="utf-8")
    assert "pipeline.NoPidSheets) as exc:" in msrc
    assert "NoPidSheets" in analysis_proc._KNOWN


def test_legend_facts_carry_input_notes():
    import json
    job = {"engine_json": json.dumps({"dxf": {"roles_note": "계기 블록의 TYPE·태그 속성을 배우지 못했습니다",
                                              "skipped_inputs": ["x.dxf (내용이 y.dxf 와 같음 — 한 번만 읽음)"]}}),
           "project": None}
    f = main._legend_facts(job)
    assert len(f["input_notes"]) == 2
    assert "건너뛴 파일 1개" in f["input_notes"][1]
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    assert "f.input_notes" in js


def test_dxf_names_without_leading_numbers_sort_naturally():
    names = ["도면_10_a.dxf", "도면_2_b.dxf", "도면_1_c.dxf", "001. x.dxf"]
    assert sorted(names, key=dxf_reader._order) == ["001. x.dxf", "도면_1_c.dxf", "도면_2_b.dxf", "도면_10_a.dxf"]


def test_sideways_sheet_is_explained_in_the_plan():
    src = Path(pipeline.__file__).read_text(encoding="utf-8")
    assert "이 장만 종이 방향이 다릅니다" in src
    assert '"사유 미상"' in src                       # 모르는 사유는 여전히 모른다고 말한다
