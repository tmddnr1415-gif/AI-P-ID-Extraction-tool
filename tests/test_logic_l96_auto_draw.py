"""L96 — PDF 를 넣으면 분석과 함께 '똑같이 그린 묶음' 이 생긴다 · 묶음 PDF 의 FROM/TO 를 누르면 그 장으로 간다."""
import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.logic import analyse as AN
from app.logic import api, draw, draw_sets, store


@pytest.fixture(autouse=True)
def _own_data(tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PID_LOGIC_WARM", "0")
    monkeypatch.setenv("PID_DRAW_SEED", "0")
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()
    yield
    api._SP.clear(); api._APPLIED.clear(); api._BUNDLE.clear(); store._RES.clear()


def _sheet(name, sheet_no):
    """AND 하나 — 왼쪽 두 행 → 오른쪽 한 행."""
    doc = draw.new_doc(name, "t", "", 50)
    doc["sheet_no"] = sheet_no
    T, P = draw.TOP, draw.PITCH
    y1, y2 = T + 2 * P + P / 2, T + 4 * P + P / 2
    doc["left"] = {"3": {"desc": "PUMP A RUNNING", "kks": "", "fm": ""}, "5": {"desc": "PUMP B RUNNING", "kks": "", "fm": ""}}
    doc["right"] = {"53": {"desc": "BOTH RUNNING", "kks": "", "to": ""}}
    doc["blocks"] = [{"id": "a", "kind": "AND", "x": 600, "y": y1 - 2, "param": {"inputs": 2}}]
    doc["wires"] = [{"id": "w1", "pts": [[draw.LX0, y1], [600, y1]]}, {"id": "w2", "pts": [[draw.LX0, y2], [560, y2], [560, y1 + 4], [600, y1 + 4]]},
                    {"id": "w3", "pts": [[616, y1], [draw.LX1, y1]]}]
    return {**doc, **draw.clean(doc)}


def _job_from_pdf(tmp_path, pdf_bytes, name="toy.pdf"):
    job, d = store.new_job(name)
    (d / "source.pdf").write_bytes(pdf_bytes)
    res = AN.analyse(str(d / "source.pdf"))
    store.write_result(d, res)
    st = store.read_status(d)
    st.update({"state": "done", "sheets": len(res["sheets"]), "seconds": 1, "author": "kim", "project": "P1"})
    store.write_status(d, st)
    return job, d, res


def test_analysis_also_makes_the_drawing_bundle_once(tmp_path, monkeypatch):
    a, b = _sheet("A", "G001"), _sheet("B", "G002")
    job, d, res = _job_from_pdf(tmp_path, draw_sets.to_pdf_set([a, b]))
    assert len(res["sheets"]) == 2
    # 꺼 두면(시험 기본) 아무것도 안 만든다
    monkeypatch.setenv("PID_LOGIC_AUTODRAW", "0")
    assert draw_sets.auto_import(d) == {} and draw_sets.auto_state(d) == {}
    monkeypatch.setenv("PID_LOGIC_AUTODRAW", "1")
    st = draw_sets.auto_import(d)
    assert st["state"] == "done" and st["sheets"] == 2 and st["first"]
    docs = list(draw_sets.set_docs(st["set"]))
    assert sorted(x["sheet_no"] for x in docs) == ["G001", "G002"]
    assert all(x["source"]["job"] == job and x["project"] == "P1" for x in docs)
    assert all(len(x["blocks"]) == 1 and x["blocks"][0]["kind"] == "AND" for x in docs)          # 그림이 분석한 그대로
    # 두 번째는 다시 만들지 않는다 (사람이 고친 그림을 덮지 않는다)
    again = draw_sets.auto_import(d)
    assert again["set"] == st["set"] and len(list(draw_sets.set_docs(st["set"]))) == 2
    app = FastAPI(); app.include_router(api.router)
    r = TestClient(app).get(f"/logic/api/jobs/{job}/drawing").json()
    assert r["state"] == "done" and r["set"] == st["set"]


def test_run_calls_auto_draw_after_the_result_is_written():
    """분석 차례(run.run) 안에서 결과가 선 바로 뒤에 그린다 — 실패해도 분석 결과는 그대로 (try 안)."""
    import inspect
    from app.logic import run
    src = inspect.getsource(run.run)
    assert src.index("_final(d, st)") < src.index("draw_sets.auto_import(d)") < src.index("_prerender(d, res)")


def test_bundle_pdf_from_to_cells_jump_to_the_other_sheet():
    a, b = _sheet("A", "G001"), _sheet("B", "G002")
    for i, x in enumerate((a, b)):
        x.update({"set": "s" * 12, "set_name": "S", "order": i + 1})
    a["right"]["53"]["to"] = draw_sets.ref_text("G002", 3)
    b["left"]["3"]["fm"] = draw_sets.ref_text("G001", 53)
    pdf = pymupdf.open("pdf", draw_sets.to_pdf_set([a, b]))
    la, lb = pdf[0].get_links(), pdf[1].get_links()
    assert len(la) == 1 and len(lb) == 1
    # 1쪽 TO 칸 → 2쪽 · 2쪽 FROM 칸 → 1쪽
    assert la[0]["kind"] == pymupdf.LINK_GOTO and la[0]["page"] == 1 and la[0]["from"].x0 >= draw.RCOLS[3] - 0.1
    assert lb[0]["kind"] == pymupdf.LINK_GOTO and lb[0]["page"] == 0 and lb[0]["from"].x1 <= draw.LCOLS[1] + 0.1
    y = draw.ry(53, 50)
    assert abs((la[0]["from"].y0 + la[0]["from"].y1) / 2 - y) < 0.01
    # 링크는 주석이다 — 그림(선 · 글)은 링크가 없는 것과 같다 (다시 분석해도 같다)
    assert len(pdf[0].get_drawings()) == len(pymupdf.open("pdf", draw.to_pdf(a))[0].get_drawings())


def test_no_link_to_a_sheet_that_is_not_in_the_bundle():
    a = _sheet("A", "G001")
    a.update({"set": "s" * 12, "set_name": "S", "order": 1})
    a["right"]["53"]["to"] = draw_sets.ref_text("G009", 3)
    assert pymupdf.open("pdf", draw_sets.to_pdf_set([a]))[0].get_links() == []
