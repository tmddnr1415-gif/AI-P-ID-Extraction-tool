"""hotfix87 — 가르치기 **제안** (사람이 누를 자리를 프로그램이 먼저 고른다) · Symbol & Legend 문구.

* 제안은 판정이 아니다 — 엔진은 `app/teach_propose.py` 를 모른다 (사람이 저장해야 쓰인다).
* Symbol & Legend 장 제안은 머리말을 인쇄된 그대로(2점) · 핵심 낱말(1점)로 가장 많이 담은 장부터.
* NOTES 제안은 두 장 이상 같은 자리의 제목만 · 서버 `/teach/click` 과 같은 함수(`notes_rect`).
* 화면은 제안을 미리 채우고 [저장하고 다시 분석] 한 번이면 되게 말한다.
"""
from __future__ import annotations

import ast
import re
import sys
import types
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))

from app import teach_propose  # noqa: E402

APP_JS = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
MAIN = (ROOT / "app" / "main.py").read_text(encoding="utf-8")


def _page(no, lines, w=1190.0, h=842.0):
    """`lines` = [(y, [낱말…])] — 낱말을 x 순으로 한 줄에 놓는다."""
    words = []
    for y, ws in lines:
        x = 50.0
        for t in ws:
            words.append((pymupdf.Rect(x, y, x + 8 * len(t), y + 6), t))
            x += 8 * len(t) + 4
    return types.SimpleNamespace(page_no=no, words=words, width=w, height=h, analysis_scope=True)


def test_engine_never_imports_the_proposals():
    """제안은 사람 눈을 한 번 거친다 — 판정 코드가 그것을 부르면 짐작이 곧 판정이 된다."""
    for p in list((ROOT / "app" / "engine").glob("*.py")) + [ROOT / "app" / "pipeline.py"]:
        tree = ast.parse(p.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                assert not any("teach_propose" in n for n in names), p.name


def test_legend_page_prefers_printed_headings_then_neighbours():
    """P&ID 장 노트의 `VALVES` 한 낱말(1점)이 아니라 머리말을 인쇄한 장 — 빠진 칸은 고른 장에 가까운 장."""
    pages = [
        _page(1, [(100, ["COVER"])]),
        _page(2, [(100, ["LINE", "VALVES"])]),
        _page(3, [(100, ["VALVES", "ACTUATORS"]), (200, ["ELECTRIC", "SIGNAL"])]),
        _page(9, [(100, ["ISOLATION", "VALVES"]), (200, ["SIGNAL"])]),     # 도면 장 노트
    ]
    got = teach_propose.legend_pages(pages)
    assert got["pages"] == [3, 2]
    assert got["found"] == {"LINE VALVES": 2, "VALVES ACTUATORS": 3, "ELECTRIC SIGNAL": 3}


def test_legend_page_keyword_only_form():
    """머리말을 다른 말로 인쇄한 양식(Takhiatash `2. VALVES` · `3. ACTUATORS`)은 핵심 낱말로."""
    pages = [_page(2, [(100, ["2.", "VALVES"]), (200, ["3.", "ACTUATORS"]), (300, ["ELECTRICAL", "SIGNAL", "LINE"])]),
             _page(6, [(100, ["NOTES"])])]
    got = teach_propose.legend_pages(pages)
    assert got["pages"] == [2] and all(v == 2 for v in got["found"].values())


def test_no_legend_words_no_proposal():
    assert teach_propose.legend_pages([_page(1, [(10, ["PUMP"])])]) is None


def test_notes_needs_the_heading_on_two_pages(monkeypatch):
    """한 장에만 있는 NOTES 는 도면 안 주석일 수 있다 — 제안하지 않는다."""
    import derive_layout
    monkeypatch.setattr(derive_layout, "notes_from_heading", lambda pages, w, h: [w.x0, w.y0, 1190, 842])
    one = [_page(1, [(40, ["NOTES"])]), _page(2, [(400, ["PUMP"])])]
    assert teach_propose.notes(one) is None
    two = [_page(1, [(40, ["NOTES"])]), _page(2, [(40, ["NOTES:"])]), _page(3, [(700, ["NOTES"])])]
    got = teach_propose.notes(two, prefer_page=2)
    assert got["page_no"] == 2 and got["pages_with_heading"] == 2


def test_notes_rect_samples_few_pages_clicked_first(monkeypatch):
    """테두리는 양식이 정한다 — 같은 크기 장 몇 개면 같은 답이고, 전부 재면 A1 54장에 94초 (AL NOUF1)."""
    import derive_layout
    seen = {}

    def fake(pages, w, h):
        seen["pages"] = [p.page_no for p in pages]
        return [0, 0, 1, 1]
    monkeypatch.setattr(derive_layout, "notes_from_heading", fake)
    form = [_page(n, []) for n in range(1, 20)]
    teach_propose.notes_rect(form, form[9], pymupdf.Rect(0, 0, 10, 6), prefer=[3, 4])
    assert seen["pages"][:3] == [10, 3, 4]
    assert len(seen["pages"]) == teach_propose.FRAME_SAMPLE


def test_click_and_proposal_share_one_notes_function():
    """NOTES 제목을 누른 자리와 제안이 같은 함수로 영역을 짓는다 — 두 벌이면 갈린다."""
    body = MAIN[MAIN.index("def teach_click"):MAIN.index("def teach_save")]
    assert "teach_propose.notes_rect(" in body
    assert "notes_from_heading(" not in body


def test_proposal_endpoint_is_separate_and_never_saves():
    """제안은 서버 밖 일꾼이 계산하고(대시보드의 3초 확인이 막히지 않게) 저장하지 않는다."""
    slot = MAIN[MAIN.index("def _proposal_slot"):MAIN.index("def _prefetch_proposals")]
    assert "page_warm.call(teach_propose.propose_pdf" in slot
    assert "teach_propose.propose(" in slot                 # 일꾼이 없을 때만 서버 안에서
    body = MAIN[MAIN.index('@app.get("/jobs/{job_id}/teach/propose")'):MAIN.index('@app.post("/jobs/{job_id}/teach/click")')]
    assert "form_teach.set_items" not in body and "form_teach.set_items" not in slot


def test_known_failure_starts_the_proposal_right_away():
    """가르칠 수 있는 멈춤이면 판을 열기 전에 계산을 시작한다."""
    branch = MAIN[MAIN.index("except (pipeline.LegendUnavailable,"):MAIN.index("except Exception as exc:  ", MAIN.index("except (pipeline.LegendUnavailable,"))]
    assert "_prefetch_proposals(job_id, exc)" in branch
    pre = MAIN[MAIN.index("def _prefetch_proposals"):MAIN.index('@app.get("/jobs/{job_id}/teach/propose")')]
    for name in ("LegendUnavailable", "TitleBlockUnreadable", "BubblesUnreadable"):
        assert name in pre
    assert "NoTextLayer" not in pre                         # 글자가 없으면 가르칠 것도 없다 (DXF 안내)


def test_panel_prefills_proposals_and_says_one_click():
    assert "/teach/propose?needs=" in APP_JS
    fn = APP_JS[APP_JS.index("async function tbLoadProposals"):APP_JS.index("const TB_PROP_SUMMARY")]
    assert "TB.dirty.legend_page = true" in fn and "TB.dirty.bubbles = true" in fn
    assert "프로그램이 답을 골라 두었습니다" in APP_JS
    assert "프로그램 제안을 확인하고 저장" in APP_JS      # 저장 기록에 남는다
    assert "function tbRedo(" in APP_JS


def test_teach_wording_says_symbol_and_legend():
    """사용자 지시 — '범례' 대신 'Symbol & Legend'.  가르치기 판의 글자에 '범례' 가 남지 않는다."""
    block = APP_JS[APP_JS.index("const TB_LABEL"):APP_JS.index("function teachExampleHtml")]
    strings = re.findall(r'"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`', block)
    assert strings and not [s for s in strings if "범례" in s]
    assert "이 장이 Symbol & Legend입니다" in block
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "Symbol &amp; Legend 장으로" in html
    pipe = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    msg = pipe[pipe.index("raise LegendUnavailable("):pipe.index("legend_derived[\"line_styles\"] = pipe_style")]
    assert "범례" not in msg and "Symbol & Legend" in msg
