"""hotfix86 — Symbol & Legend 장의 계기는 추출 목록에 들어가지 않는다 · 가르치기 예시 그림."""
from __future__ import annotations

import re
from pathlib import Path

from app import pipeline

ROOT = Path(__file__).resolve().parent.parent


def _rows(**kinds):
    return {int(k[1:]): {"page_kind": v[0], "drawing_no": v[1]} for k, v in kinds.items()}


def test_sheets_sharing_a_legend_drawing_number_are_legend():
    # Takhiatash: 범례 네 장이 한 도면번호를 쓰고 머리말이 인쇄된 p4 만 LEGEND 였다
    tb = _rows(p1=("UNKNOWN", ""), p2=("PID", "B-VVV-M-32-001"), p3=("PID", "B-VVV-M-32-001"),
               p4=("LEGEND", "B-VVV-M-32-001"), p5=("PID", "B-VVV-M-32-001"),
               p6=("PID", "B-LBA-M-32-001"))
    moved = pipeline.mark_legend_sheets(tb, [])
    assert sorted(moved) == [2, 3, 5]
    assert [tb[n]["page_kind"] for n in range(1, 7)] == ["UNKNOWN", "LEGEND", "LEGEND", "LEGEND", "LEGEND", "PID"]
    assert "p4" in tb[3]["page_kind_basis"]


def test_taught_legend_sheet_and_its_siblings():
    tb = _rows(p2=("PID", "X-001"), p3=("PID", "X-001"), p6=("PID", "Y-001"))
    moved = pipeline.mark_legend_sheets(tb, [2])
    assert sorted(moved) == [2, 3]
    assert tb[6]["page_kind"] == "PID"
    assert tb[2]["page_kind_basis"].startswith("taught")


def test_documents_with_their_own_legend_numbers_do_not_move():
    # AL NOUF1 · TC2 — 범례 장마다 번호가 다르고 P&ID 와 겹치지 않는다
    tb = _rows(p1=("DRAWING_LIST", "D-0001"), p2=("LEGEND", "D-0002"), p3=("LEGEND", "D-0003"),
               p6=("PID", "D-10LBA10-0001"), p7=("PID", "D-10LBA10-0001"))
    assert pipeline.mark_legend_sheets(tb, []) == []
    assert tb[6]["page_kind"] == tb[7]["page_kind"] == "PID"


def test_symbol_sheets_read_by_the_legend_are_marked_before_targets():
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    i = src.index("_symbol_pages = legend_profile_store.read_pages(")
    assert i < src.index("    targets = [pc for pc in pages")
    block = src[i:i + 400]
    # 기기 표 · 부품 낱말 · 선 종류는 P&ID 장의 작은 범례 상자에서도 읽히므로 넣지 않는다
    assert "equipment_symbols" not in block and "line_styles" not in block


def test_heading_alternatives_classify_a_sheet():
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    assert "legend_rules.prints_heading(pc, h)" in src


def test_every_task_has_two_example_pictures_on_disk():
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    block = js[js.index("const TEACH_EXAMPLES"):js.index("function teachExampleHtml")]
    for task in ("dwg_no", "legend", "bubbles", "notes"):
        assert re.search(rf"\b{task}: \{{ how:", block), task
    pics = re.findall(r'"(ex_[a-z_0-9]+\.png)"', block)
    assert len(pics) == 8
    for name in pics:
        path = ROOT / "app" / "static" / "img" / "teach" / name
        assert path.exists() and path.stat().st_size < 80_000, name
    # 지금 할 일에만 예시가 붙고, 누르면 크게 본다
    assert "teachExampleHtml(k)" in js and 'closest("button[data-ex]")' in js
