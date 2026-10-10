"""위생 경고가 **무엇을 가리키는지** 화면이 말한다 (46회차 [B]).

지키는 것 셋:
    ① 감사기는 여전히 **아무것도 지우지 않는다** (`os.remove`·`rmtree` 없음)
    ② 도면 근거 없는 행을 **한 행씩** 낸다 — job · 장 · 값 · 작성자
    ③ 작성자가 없으면 **없다고 말한다** (지어내지 않는다)
"""
from __future__ import annotations

import inspect
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import audit  # noqa: E402


def _code_only(mod) -> str:
    """문서 문자열을 뺀 코드만.  이 모듈의 머리말은 `os.remove` 도
    `shutil.rmtree` 도 **없다고 적고 있어서**, 글자로 세면 자기 설명에 걸린다
    (44회차 `tests/test_markup.py` 와 같은 함정)."""
    import ast
    tree = ast.parse(inspect.getsource(mod))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:]
    return ast.unparse(tree)


def test_the_auditor_still_deletes_nothing():
    src = _code_only(audit)
    for forbidden in ("os.remove", "shutil.rmtree", "unlink(", "DELETE FROM"):
        assert forbidden not in src


def _con(tmp_path):
    import os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    from app import db
    con = db.connect(tmp_path / "app.db")
    con.execute("INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,"
                "status,progress,message,fingerprint,project,revision)"
                " VALUES ('j1','x.pdf','s','p',?,'done',1.0,'','','P','A')",
                (time.time(),))
    con.commit()
    return con, db


def test_it_names_each_hand_added_row(tmp_path):
    con, db = _con(tmp_path)
    db.add_row(con, "j1", page_no=7, tab="FIELD", drawing_no="D-1",
               values={"type": "PIT", "scope": "SCT", "qty": 1},
               evidence={"markup": {"author": "sc.y", "at": "2026-09-14T00:00:00",
                                    "class": "MISSING", "note": "누락"}})
    con.commit()
    rows = audit.hand_added(con)
    assert len(rows) == 1
    r = rows[0]
    assert (r["page_no"], r["type"], r["author"], r["from_markup"]) == (7, "PIT", "sc.y", True)
    assert r["pdf_name"] == "x.pdf" and r["project"] == "P"


def test_a_row_without_an_author_says_so(tmp_path):
    con, db = _con(tmp_path)
    db.add_row(con, "j1", page_no=3, tab="FIELD", drawing_no="D-1",
               values={"type": "PI"})
    con.commit()
    r = audit.hand_added(con)[0]
    assert r["author"] == "" and r["from_markup"] is False


def test_run_carries_the_detail(tmp_path):
    con, db = _con(tmp_path)
    db.add_row(con, "j1", page_no=3, tab="FIELD", drawing_no="D-1", values={"type": "PI"})
    con.commit()
    out = audit.run(con, tmp_path)
    assert len(out["hand_added"]) == 1
    assert out["provenance"]["hand_added_rows"] == 1


def test_the_screen_reads_the_server_value_not_its_own_count():
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "a.hand_added" in js
    assert "L.orphan_outputs" in js
