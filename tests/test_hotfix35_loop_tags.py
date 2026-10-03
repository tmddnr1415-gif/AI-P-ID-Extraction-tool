"""hotfix35 — 한 루프가 공유하는 태그 · Tag No. 열 자리 (QFE p46 사진).

  ① 같은 장의 서로 다른 종류(PI ↔ PIT)가 같은 코드를 들면 **한 루프의 이름**이고
     둘 다 그 태그를 받는다.  같은 종류 둘 · 다른 장에 걸친 공유는 예전대로
     이름이 아니다 (관경 `DN150` · 배관 번호).
  ② `kinds` 를 안 넘기면 옛 판정과 글자 그대로 같다.
  ③ PDF · DXF 두 `_attach_tags` 가 모두 종류를 넘긴다 (소스 검사).
  ④ 그 태그로 hotfix31 접기가 실제로 돈다 — PI 가 접히고 PIT 가 남는다.
  ⑤ 그리드의 Tag No. 열은 Type 바로 옆이다.
"""
from __future__ import annotations

import ast
import pathlib
import sys

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
import isa_table                 # noqa: E402
import tags as T                 # noqa: E402
from app import pipeline as P    # noqa: E402

R = pymupdf.Rect


def _page_words(tagged):
    """`[(x, y, 글자)]` → 버블 안에 인쇄된 낱말."""
    return [(R(x, y, x + 60, y + 8), t) for x, y, t in tagged]


def _world():
    """p6: PI·PIT 가 `11LBB50CP001` 을 공유 · TI·TIT 가 `11LBB50CT001` 을 공유.
    p7: 혼자 든 태그 둘 (체계를 세우는 두 번째 장).  p8: 같은 종류 둘이 같은
    코드(`DN150`)를 들고, PI 가 p7 FIT 의 코드를 되풀이한다 (장을 넘는 공유)."""
    items = [(6, R(100, 100, 160, 120)), (6, R(100, 140, 160, 160)),   # PI · PIT
             (6, R(300, 100, 360, 120)), (6, R(300, 140, 360, 160)),   # TI · TIT
             (7, R(100, 100, 160, 120)), (7, R(300, 100, 360, 120)),   # LIT · FIT
             (8, R(100, 100, 160, 120)), (8, R(100, 140, 160, 160)),   # PIT · PIT (DN150)
             (8, R(300, 100, 360, 120))]                               # PI (p6 태그 재인쇄)
    kinds = ["PI", "PIT", "TI", "TIT", "LIT", "FIT", "PIT", "PIT", "PI"]
    words = {6: _page_words([(100, 105, "11LBB50CP001"), (100, 145, "11LBB50CP001"),
                             (300, 105, "11LBB50CT001"), (300, 145, "11LBB50CT001")]),
             7: _page_words([(100, 105, "11LBB50CL001"), (300, 105, "11LBB50CF001")]),
             8: _page_words([(100, 105, "DN150"), (100, 145, "DN150"),
                             (300, 105, "11LBB50CF001")])}
    return items, kinds, words


def test_loop_shared_code_is_a_tag_for_both_bubbles():
    items, kinds, words = _world()
    tags, facts = T.assign(items, words, kinds=kinds)
    assert tags[0] == tags[1] == "11LBB50CP001"
    assert tags[2] == tags[3] == "11LBB50CT001"
    assert tags[4] == "11LBB50CL001" and 5 not in tags     # FIT 의 코드는 p8 에도 있다
    assert facts["tier"] == 1 and "D2L3D2L2D3" in facts["shapes"]
    assert set(facts["loop_shared"]) == {"11LBB50CP001", "11LBB50CT001"}


def test_same_kind_or_cross_page_sharing_is_still_not_a_name():
    items, kinds, words = _world()
    tags, _f = T.assign(items, words, kinds=kinds)
    assert 6 not in tags and 7 not in tags          # DN150 — 같은 종류 둘
    assert 8 not in tags and 5 not in tags          # p7 FIT 의 코드를 p8 이 되풀이 — 장이 다르다


def test_without_kinds_the_old_judgement_is_unchanged():
    items, _kinds, words = _world()
    tags, facts = T.assign(items, words)
    # 혼자 든 코드가 p7 의 LIT 하나뿐이라 체계가 서지 않는다 — 옛 규칙 그대로
    assert facts["loop_shared"] == [] and facts["tier"] == 2 and tags == {}


def test_both_pipelines_hand_the_kinds_over():
    for name in ("app/pipeline.py", "app/dxf_pipeline.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        tree = ast.parse(src)
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "assign"
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == "tagsys"]
        assert calls, name
        for c in calls:
            assert any(k.arg == "kinds" for k in c.keywords), name


TABLE = isa_table.IsaTable(
    first={"P": ("PRESSURE",), "T": ("TEMPERATURE",), "L": ("LEVEL",), "F": ("FLOW",)},
    succeeding={"I": ("INDICATOR",), "T": ("TRANSMITTER",)},
    page_no=4, note="test")


class _Page:
    def __init__(self, no, words):
        self.page_no, self.words = no, words


def _row(key, anchor, page, rect):
    return P.Row(key=key, tab=P.TAB_FIELD, page_no=page, drawing_no="D", type=anchor,
                 qty=1, rect=tuple(rect), evidence={"anchor": anchor})


def test_shared_tag_lets_the_readout_fold_run_end_to_end():
    items, kinds, words = _world()
    rows = [_row(f"k{i}", kinds[i], pg, rc) for i, (pg, rc) in enumerate(items)]
    facts = P._attach_tags(rows, [_Page(n, w) for n, w in words.items()])
    assert facts["effective"] == "epc" and facts["tagged_rows"] == 5
    assert rows[0].tag_no == rows[1].tag_no == "11LBB50CP001"
    rfacts, folded = P._fold_readouts(rows, TABLE)
    assert folded == {"k0", "k2"}                  # PI · TI 가 접히고 PIT · TIT 가 남는다
    kept = {f["kept"] for f in rfacts["folded"]}
    assert kept == {"PIT", "TIT"}
    assert rows[8].tag_no == ""                    # p8 의 PI 는 태그가 없어 그대로


def test_tag_no_column_sits_next_to_type():
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    cols = js[js.index("const COLS = ["):js.index("];", js.index("const COLS = ["))]
    assert cols.index('["type", "Type"') < cols.index('["tag_no", "Tag No."') < cols.index('["valve_type"')
