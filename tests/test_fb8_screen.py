"""8차 피드백의 화면 넷을 코드로 못박는다 (53회차 · s1 · s3 · s7 · s8).

자기검증(`spike/ui_audit_fb8.py`)이 실제로 눌러 확인한 것을 **되돌아가지 않게**
여기서 지킨다.  화면 동작 자체는 브라우저가 있어야 재지만, *어느 함수가 무엇을
읽는가* 는 소스로 지킬 수 있고 그것이 지금까지 갈린 자리였다.
"""
from __future__ import annotations

import inspect
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import pipeline  # noqa: E402

JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")


# s1 ─ 무엇을 지우든 고르는 상자를 함께 다시 읽는다
def test_both_delete_paths_share_one_refresh():
    assert "async function afterDelete()" in JS
    # 두 벌을 두지 않는다 — 갈라져 있던 것이 이 결함이었다
    assert JS.count("await afterDelete();") >= 2
    assert "loadProjects(still ? was : undefined)" in JS


def test_a_vanished_project_does_not_silently_become_something_else():
    """없는 이름을 `loadProjects` 에 넘기면 브라우저가 value 를 "" 로 떨어뜨려
    '프로젝트 없이 한 번만' 이 된다 — 사람이 고른 적 없는 설정이다."""
    assert "프로젝트가 없어져 선택을 지웠습니다" in JS


# s3 ─ 읽은 것과 **쓴 것**을 갈라 말한다
def test_the_notes_band_separates_read_from_used():
    from app import main
    src = inspect.getsource(main.sheet_notes)
    assert '"used": used' in src
    # 판정 근거는 엔진이 적어 둔 것이지 화면이 다시 정하는 것이 아니다
    assert 'NOTES:' in src and "qty_basis" in src
    assert "d.used" in JS and "읽기만 한 값" in JS


def test_unit_notes_is_stored():
    """27회차가 읽어 놓고 저장하지 않아 화면이 못 봤다 (38회차 evidence_tier 와 같은 결함)."""
    assert '"unit_notes")' in (ROOT / "app" / "db.py").read_text(encoding="utf-8")


# s7 ─ SCOPE 를 바꾸면 색이 따라간다 · VENDOR 이름은 그 도면에서 온다
def test_the_overlay_colour_reads_the_live_scope():
    assert 'if (row) return scopeKeyOf(cellValue(row, "scope"));' in JS
    assert 'if (field === "scope") drawOverlay();' in JS


def test_vendor_names_come_from_this_drawing_only():
    fn = JS[JS.index("function vendorNames()"):JS.index("function scopeEditor(")]
    assert 'cellValue(r, "scope")' in fn
    # 코드에 공급자 이름을 적지 않는다 (10회차 규율)
    for name in ("HRSG", "SIEMENS", "ST SUPPLIER"):
        assert name not in fn


# s8 ─ 빠르게 · 녹색 · 추가한 행으로 이동
def test_the_probe_does_not_rerun_detection():
    src = inspect.getsource(pipeline.probe_point)
    assert "ds.detect(" not in src, "저장된 결과가 있는데 다시 세면 느리고 갈린다"
    assert "near_detections" in src
    # 그 장만 연다 — 이제 제안 캐시가 그 일을 한다 (열쇠를 함께 쓴다)
    assert "only=(page_no,)" in inspect.getsource(pipeline._propose_page)


def test_the_probe_shares_the_proposal_cache_key():
    """열쇠가 다르면 제안이 데워 둔 캐시를 못 쓴다 (실측 5.3초 → 0.2초)."""
    src = inspect.getsource(pipeline.probe_point)
    assert "_propose_page(pdf_path, page_no, layout_moved)" in src
    from app import main
    assert "moved" in inspect.getsource(main._engine_near)


def test_markup_turns_green_and_the_legend_counts_it_once():
    assert "it.manual ? MANUAL_MARK[2]" in JS          # 녹색 선
    assert "tbody tr.added { background: rgba(52, 199, 89" in (
        ROOT / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    # 한 상자가 SCOPE 칸과 사용자 칸에 두 번 세어지면 33회차 등식이 깨진다
    assert "if (it.manual) manual++;\n    else counts[itemScope(it)]" in JS


def test_the_grid_moves_to_the_added_row():
    assert "refreshRows(out.key, { toGrid: true })" in JS
    assert 'tr.scrollIntoView({ block: "center" })' in JS
    assert 'tr.classList.add("justadded")' in JS


def test_the_page_is_prewarmed_when_markup_starts():
    assert "if (S.markup) prewarmMarkup();" in JS
    fn = JS[JS.index("async function prewarmMarkup()"):]
    fn = fn[:fn.index("\n}\n")]
    # 새 서버 코드를 만들지 않는다 — 같은 엔드포인트여야 캐시 열쇠가 같다
    assert "/markup/propose" in fn
