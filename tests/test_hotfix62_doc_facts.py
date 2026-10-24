"""hotfix62 — 카드의 도면 사실: PDF 프로젝트 제목 · 이력 표의 개정 순서 · 최상위 Rev+날짜 ·
같은 Rev 면 PDF 날짜로 신·구 판정 · 나가는 계기 Q'ty · 지표 카드 삭제."""
from pathlib import Path

import pymupdf
import pytest

from app import pdf_facts, revisions

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")


def _words(lines):
    out = []
    for x, y, h, t in lines:
        out.append((pymupdf.Rect(x, y, x + 6 * len(t), y + h), t))
    return out


def test_parse_date_never_invents_an_iso():
    assert pdf_facts.parse_date("26.MAR.2026") == (True, "2026-03-26")
    assert pdf_facts.parse_date("19. SEP.2025") == (True, "2025-09-19")
    assert pdf_facts.parse_date("2026-01-08") == (True, "2026-01-08")
    assert pdf_facts.parse_date("26.08.21") == (True, None)        # YY.MM.DD ↔ DD.MM.YY 를 모른다
    assert pdf_facts.parse_date("03.04.2026") == (True, None)      # 일·월이 갈리지 않는다
    assert pdf_facts.parse_date("25.04.2026") == (True, "2026-04-25")
    assert pdf_facts.parse_date("1A") == (False, None)


def test_project_title_is_the_larger_line_under_the_caption():
    w = _words([(10, 100, 8, "PROJECT"), (60, 100, 8, "TITLE"),
                (40, 112, 14, "QATAR"), (90, 112, 14, "FACILITY"), (150, 112, 14, "E"), (170, 112, 14, "IWPP"),
                (10, 140, 8, "EPC"), (40, 140, 8, "CONTRACTOR")])
    assert pdf_facts.project_title(w) == "QATAR FACILITY E IWPP"


def test_history_reads_the_rev_column_found_by_the_current_rev():
    w = _words([(200, 10, 8, "26.MAR.2026"), (300, 10, 8, "FOR"), (100, 10, 8, "1B"),
                (200, 25, 8, "14.NOV.2025"), (300, 25, 8, "FOR"), (100, 25, 8, "1A"),
                (200, 40, 8, "04.SEP.2025"), (100, 40, 8, "0"),
                (200, 55, 8, "06.AUG.2025"), (100, 55, 8, "B"), (330, 55, 8, "A")])  # 설명 칸의 A 는 Rev 열이 아니다
    rows = pdf_facts.history(w, "1B")
    assert ("1B", "26.MAR.2026", "2026-03-26") in rows and ("B", "06.AUG.2025", "2025-08-06") in rows
    assert pdf_facts.rev_date(rows, "1B")[:2] == ("26.MAR.2026", "2026-03-26")


def test_top_revision_follows_the_drawn_order_not_the_alphabet():
    facts = {"rev_before": [["A", "B"], ["B", "C"], ["C", "0"], ["0", "1A"], ["1A", "1B"]],
             "pages": {1: {"rev": "1B", "kind": "PID", "date": "26.MAR.2026", "iso": "2026-03-26"},
                       2: {"rev": "C", "kind": "PID", "date": "29.SEP.2025", "iso": "2025-09-29"},
                       3: {"rev": "A", "kind": "PID", "date": "08.JAN.2026", "iso": "2026-01-08"}}}
    top = pdf_facts.top_revision(facts, doc_rev="C")
    assert top["rev"] == "1B" and top["date"] == "26.MAR.2026" and top["basis"] == "HISTORY"
    # 이력 표에 없는 Rev 가 섞이면 순서를 모른다 — 예전 규칙으로 돌아가고 그렇게 말한다
    facts["pages"][4] = {"rev": "D", "kind": "PID", "date": "", "iso": None}
    top = pdf_facts.top_revision(facts, doc_rev="D")
    assert top["rev"] == "D" and top["basis"] == "RULE" and top["unordered"] == ["D"]


def test_same_rev_is_decided_by_the_pdf_date():
    c = revisions.compare_document_revision
    assert c("C", "C", now_date="2026-03-26", before_date="2026-01-12")["verdict"] == "NEWER"
    assert c("C", "C", now_date="2026-01-12", before_date="2026-03-26")["verdict"] == "OLDER"
    assert c("C", "C")["verdict"] == "SAME"                                   # 날짜가 없으면 예전 그대로
    assert c("1B", "C", order=[["C", "1B"]])["verdict"] == "NEWER"            # 이력 표가 앞뒤를 말한다
    assert c("B", "C")["verdict"] == "OLDER"                                  # 아무것도 없으면 글자 순서


def test_kpi_cards_are_gone_and_cards_read_the_output_qty():
    dash = JS[JS.index("function renderDashboard()"):JS.index("function renderDashboard()") + 4000]
    assert '$("#home-kpis").innerHTML = "";' in dash and "kpi(" not in dash
    assert "function kpi(" not in JS
    home = JS[JS.index("async function listHome("):JS.index("const listJobs = listHome;")]
    assert "p.pdf_title || p.name" in home and "qtyOf(last)" in home and "top.rev" in home
    main = (ROOT / "app/main.py").read_text(encoding="utf-8")
    body = main[main.index("def _output_qty("):main.index("def _json(")]
    assert "excel_out.DELIVERABLES" in body and "excel_out.in_client_scope" in body   # Excel 과 같은 기준


def test_output_qty_counts_user_edits_and_skips_removed(tmp_path):
    from app import db
    con = db.connect(tmp_path / "a.db")
    con.execute("INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status) VALUES ('j','a','x','/x',1,'done')")
    for key, tab, qty, user, removed in (("1", "FIELD", 2, "{}", 0), ("2", "FIELD", 2, '{"qty": 5}', 0),
                                         ("3", "FIELD", 2, "{}", 1), ("4", "REVIEW", 9, "{}", 0),
                                         ("5", "MOV", None, "{}", 0)):
        con.execute("INSERT INTO item (job_id,key,tab,page_no,ai_json,user_json,removed) VALUES (?,?,?,?,?,?,?)",
                    ("j", key, tab, 1, '{"qty": %s}' % ("null" if qty is None else qty), user, removed))
    con.commit()
    out = db.output_qty(con, "j", {"FIELD", "MOV"})
    assert out == {"qty": 7, "rows": 3, "qty_missing": 1}


@pytest.mark.skipif(not (ROOT / "data/QFE_260326.pdf").exists(), reason="QFE PDF 없음")
def test_qfe_reads_title_and_top_revision_from_the_pdf():
    import fitz  # noqa: F401
    doc = pymupdf.open(str(ROOT / "data/QFE_260326.pdf"))
    pages = [{"page_no": 10, "page_kind": "PID", "rev": "1B", "rev_date": ""},
             {"page_no": 46, "page_kind": "PID", "rev": "0", "rev_date": ""}]
    doc.close()
    f = pdf_facts.read(ROOT / "data/QFE_260326.pdf", pages)
    assert f["project_title"] == "QATAR FACILITY E IWPP"
    assert f["pages"][10]["date"] == "26.MAR.2026" and f["pages"][46]["date"] == "15.OCT.2025"
    assert pdf_facts.top_revision(f)["rev"] == "1B"
