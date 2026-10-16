"""LOGIC L25 — 가르치기: 무리마다 한 번 답하면 모든 장에 (최소한의 질문 · 최소한의 장).

합성 두 장 묶음(spike/logic_variants.py 의 base): A 장 AB_G-101 (게이트 다섯) → B 장 AB_G-102 2행 (FM AB_G-101-51).
읽기가 실패한 상황을 결과에서 지워 흉내 내고, 질문 하나에 답하면 같은 것이 모든 장에서 돌아오는지 본다.
분석 결과 파일은 바뀌지 않는다.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    spec = importlib.util.spec_from_file_location("logic_variants", os.path.join(ROOT, "spike", "logic_variants.py"))
    lv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lv)
    from app.logic import analyse
    p = str(tmp_path_factory.mktemp("l25") / "base.pdf")
    lv.make(next(x for x in lv.VARIANTS if x.name == "base"), p)
    return p, analyse.analyse(p)


def _sheet(res, page):
    return next(s for s in res["sheets"] if s["page"] == page)


def _unknown(res, page, bid, fig="f" * 64):
    b = _sheet(res, page)["blocks"][bid]
    b["func"], b["logic"], b["label"], b["read"] = "UNKNOWN", "unknown", "?", "?"
    b["fig"] = fig
    return b


def _apply(res, d, lib=None):
    from app.logic import fromto, overrides
    out = copy.deepcopy(res)
    fromto.check(out["sheets"])
    overrides.apply(out, overrides.load(d), lib)
    return out


def test_one_answer_fixes_every_block_of_the_same_shape(made, tmp_path):
    from app.logic import idrate, overrides, teach
    _, base = made
    res = copy.deepcopy(base)
    # 같은 모양(같은 크기 · 같은 글자 · 같은 그림)의 블록 둘을 판정 못 한 것으로 — 하나는 다른 장에 둔 셈 치고 같은 장에
    a = _unknown(res, 1, "B1")
    b = _unknown(res, 1, "B4")
    b["bbox"] = [b["bbox"][0], b["bbox"][1], b["bbox"][0] + (a["bbox"][2] - a["bbox"][0]), b["bbox"][1] + (a["bbox"][3] - a["bbox"][1])]
    q = teach.questions(res)
    gates = [x for x in q["questions"] if x["kind"] == "GATE"]
    assert len(gates) == 1 and gates[0]["count"] == 2           # 둘 → 질문 하나
    assert q["pages"] == [1] and q["gain"] > q["now"]
    g = gates[0]
    # 화면을 거치면 1.0 이 1 로 온다 (JSON.stringify) — 같은 무리로 읽어야 한다
    sig_js = {k: (int(v) if isinstance(v, float) and v.is_integer() else v) for k, v in g["sig"].items()}
    overrides.teach_gate(tmp_path, g["id"], sig_js, g["fig"], "AND", "홍길동")
    out = _apply(res, tmp_path)
    s = _sheet(out, 1)
    assert s["blocks"]["B1"]["func"] == "AND" and s["blocks"]["B4"]["func"] == "AND"
    assert s["blocks"]["B4"]["user"]["taught"] == g["id"]
    assert idrate.measure(out)["rate"]["gate"] == 1.0
    assert not [x for x in teach.questions(out)["questions"] if x["kind"] == "GATE"]
    # 사람이 블록 하나를 직접 정한 것이 규칙보다 이긴다
    overrides.set_block(tmp_path, 1, "B4", "OR", "홍길동")
    assert _sheet(_apply(res, tmp_path), 1)["blocks"]["B4"]["func"] == "OR"
    # 그림이 다르면 같은 무리가 아니다
    res2 = copy.deepcopy(res)
    _sheet(res2, 1)["blocks"]["B4"]["fig"] = teach.fig_hex([(0, 0), (15, 15)])
    assert len([x for x in teach.questions(res2)["questions"] if x["kind"] == "GATE"]) == 2
    # 되돌리기
    overrides.teach_gate(tmp_path, g["id"], g["sig"], g["fig"], None, "홍길동")
    assert _sheet(_apply(res, tmp_path), 1)["blocks"]["B1"]["func"] == "UNKNOWN"


def test_taught_rule_reaches_another_project_through_the_library(made, tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path / "data"))
    from app.logic import library, teach
    _, base = made
    res = copy.deepcopy(base)
    _unknown(res, 1, "B1")
    g = next(x for x in teach.questions(res)["questions"] if x["kind"] == "GATE")
    library.learn_rule({"id": g["id"], "sig": g["sig"], "fig": g["fig"], "choice": "NAND", "author": "홍길동"}, "jobA")
    assert library.taught_rules(exclude_bundle="jobA") == []                 # 같은 묶음 것은 그 묶음 규칙이 맡는다
    rules = library.taught_rules(exclude_bundle="jobB")
    out = _apply(res, tmp_path / "jobB", rules)
    b = _sheet(out, 1)["blocks"]["B1"]
    assert b["func"] == "NAND" and b["user"]["from"] == "library"
    assert library.summary()["taught"] == 1


def test_sheet_region_on_one_page_reads_every_page(made, tmp_path):
    from app.logic import idrate, overrides, teach
    pdf, base = made
    res = copy.deepcopy(base)
    for s in res["sheets"]:
        s["sheet_no"] = ""
    from app.logic import fromto
    fromto.check(res["sheets"])
    q = teach.questions(res)
    sq = next(x for x in q["questions"] if x["kind"] == "SHEET")
    assert sq["count"] == 2 and len(q["pages"]) >= 1
    vals = teach.read_region(pdf, res, 1, [1090, 788, 1140, 806])        # 한 장(1쪽)의 시트 이름 자리
    assert vals == {1: "AB_G-101", 2: "AB_G-102"}
    overrides.teach_region(tmp_path, "SHEET", 1, [1090, 788, 1140, 806], vals, "홍길동")
    out = _apply(res, tmp_path)
    assert _sheet(out, 2)["sheet_no"] == "AB_G-102"
    r2 = next(r for r in _sheet(out, 2)["rows"] if r["side"] == "L" and r["n"] == 2)
    assert r2["ref"]["page"] == 1
    assert idrate.measure(out)["rate"]["sheet"] == 1.0


def test_fm_column_on_one_page_reads_the_rows_of_every_page(made, tmp_path):
    from app.logic import overrides, teach
    pdf, base = made
    res = copy.deepcopy(base)
    for s in res["sheets"]:
        for coll in (s["table"], s["rows"]):
            for t in coll:
                if t["side"] == "L":
                    t["fm"] = "?"            # FM 열을 못 읽음
    vals = teach.read_region(pdf, res, 2, [30, 60, 90, 300], side="L")
    assert vals[2]["2"] == "AB_G-101-51" and vals[1]["2"] == "HMI"
    overrides.teach_region(tmp_path, "FROM", 2, [30, 60, 90, 300], vals, "홍길동", side="L")
    out = _apply(res, tmp_path)
    r2 = next(r for r in _sheet(out, 2)["rows"] if r["side"] == "L" and r["n"] == 2)
    assert r2["fm"] == "AB_G-101-51" and r2["ref"]["page"] == 1 and r2["user"]["fm"]["taught"]


def test_missing_sheet_name_is_answered_once(made, tmp_path):
    from app.logic import fromto, idrate, overrides, teach
    _, base = made
    res = copy.deepcopy(base)
    for coll in (_sheet(res, 2)["table"], _sheet(res, 2)["rows"]):
        for t in coll:
            if t["side"] == "L" and t["n"] == 2:
                t["fm"] = "AB_G-109-51"          # 묶음에 없는 시트
    fromto.check(res["sheets"])
    lq = next(x for x in teach.questions(res)["questions"] if x["kind"] == "LINK")
    assert lq["target"] == "AB_G-109" and "AB_G-101" in lq["candidates"]
    overrides.teach_link(tmp_path, "AB_G-109", "OTHER", None, "홍길동")
    out = _apply(res, tmp_path)
    r2 = next(r for r in _sheet(out, 2)["rows"] if r["side"] == "L" and r["n"] == 2)
    assert r2["ref"]["other_bundle"] is True and idrate.measure(out)["counts"]["link"]["all"] == 0
    overrides.teach_link(tmp_path, "AB_G-109", "ALIAS", "AB_G-101", "홍길동")
    out = _apply(res, tmp_path)
    r2 = next(r for r in _sheet(out, 2)["rows"] if r["side"] == "L" and r["n"] == 2)
    assert r2["ref"]["page"] == 1 and not [x for x in teach.questions(out)["questions"] if x["kind"] == "LINK"]
    with pytest.raises(ValueError):
        overrides.teach_link(tmp_path, "AB_G-109", "ALIAS", "", "홍길동")


def test_index_pages_without_the_column_are_not_asked(made):
    """도면 목록 장(블록 없음) · 그 열을 한 칸도 안 그린 장은 FM 열을 묻지 않는다 (1A5J I002~I011 · 1A1Y p2)."""
    from app.logic import teach
    _, base = made
    res = copy.deepcopy(base)
    idx = copy.deepcopy(_sheet(res, 2))
    idx["page"], idx["sheet_no"], idx["blocks"] = 3, "IDX", {}
    idx["table"] = [{"n": i, "side": "L", "y0": 10 * i, "y1": 10 * i + 9, "fm_box": None, "fm": "", "desc": f"{i:03d}", "kks": ""}
                    for i in range(1, 41)]
    res["sheets"].append(idx)
    assert not [x for x in teach.questions(res)["questions"] if x["kind"] in ("FROM", "TO")]


def test_pass_choice_passes_the_signal(made, tmp_path):
    from app.logic import overrides, sim
    _, base = made
    res = copy.deepcopy(base)
    overrides.set_block(tmp_path, 1, "B5", "PASS", "홍길동")
    out = _apply(res, tmp_path)
    s = _sheet(out, 1)
    assert s["blocks"]["B5"]["logic"] == "pass"
    ins = [p["net"] for p in s["ports"] if p["block"] == "B5" and p["dir"] == "in"]
    outs = [p["net"] for p in s["ports"] if p["block"] == "B5" and p["dir"] == "out"]
    assert ins and outs
    for v in (1, 0):
        got = sim.simulate(s, {f"net:{ins[0]}": v})
        fr = got["frames"][-1]["values"]
        assert fr.get(ins[0], fr.get(str(ins[0]))) == v
        assert fr.get(outs[0], fr.get(str(outs[0]))) == v


def test_preview_during_analysis_is_a_copy(made, monkeypatch):
    """분석 중 미리보기는 사본에서 돈다 — 미리보기를 낸 분석과 안 낸 분석의 결과가 같다."""
    from app.logic import analyse
    pdf, base = made
    monkeypatch.setattr(analyse, "_preview_marks", lambda n: {2})
    got = []
    res = analyse.analyse(pdf, partial=got.append)
    assert got and got[0]["partial"] and len(got[0]["sheets"]) == 2
    a, b = copy.deepcopy(res), copy.deepcopy(base)
    a.pop("seconds"), b.pop("seconds")
    assert a == b


def test_api_teach_flow(made, tmp_path, monkeypatch):
    monkeypatch.setenv("PID_DATA_DIR", str(tmp_path))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import shutil
    from app.logic import api, store
    pdf, base = made
    d = store.root() / "a25b25c25d25"
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy(pdf, d / "source.pdf")
    res = copy.deepcopy(base)
    _unknown(res, 1, "B1")
    for s in res["sheets"]:
        s["sheet_no"] = ""
    app = FastAPI()
    app.include_router(api.router)
    c = TestClient(app)
    # 분석 중 — 미리 본 장으로 질문
    (d / "partial.json").write_text(json.dumps({"pdf_pages": 2, "sheets": res["sheets"][:1], "partial": True}), encoding="utf-8")
    q = c.get("/logic/api/jobs/a25b25c25d25/teach").json()
    assert q["final"] is False and any(x["kind"] == "GATE" for x in q["questions"])
    g = next(x for x in q["questions"] if x["kind"] == "GATE")
    r = c.post("/logic/api/jobs/a25b25c25d25/teach", json={"kind": "GATE", "qid": g["id"], "sig": g["sig"], "fig": g["fig"],
                                                          "choice": "AND", "author": "홍길동", "learn": False}).json()
    assert r["saved"]["choice"] == "AND" and "idrate" not in r
    assert c.post("/logic/api/jobs/a25b25c25d25/teach", json={"kind": "GATE", "qid": g["id"], "sig": g["sig"], "fig": g["fig"],
                                                             "choice": "AND", "author": ""}).status_code == 400
    # 분석이 끝남 — 답한 규칙이 끝난 결과에 얹힌다
    (d / "result.json").write_text(json.dumps(res), encoding="utf-8")
    (d / "partial.json").unlink()
    sh = c.get("/logic/api/jobs/a25b25c25d25/sheet/1").json()
    assert sh["blocks"]["B1"]["func"] == "AND"
    q = c.get("/logic/api/jobs/a25b25c25d25/teach").json()
    assert q["final"] is True and q["answered"]["gates"][0]["choice"] == "AND"
    sq = next(x for x in q["questions"] if x["kind"] == "SHEET")
    pv = c.post("/logic/api/jobs/a25b25c25d25/teach/preview", json={"kind": "SHEET", "page": 1, "rect": [1090, 788, 1140, 806]}).json()
    assert pv["fills"] == 2
    r = c.post("/logic/api/jobs/a25b25c25d25/teach", json={"kind": "SHEET", "page": 1, "rect": [1090, 788, 1140, 806],
                                                          "author": "홍길동"}).json()
    assert r["idrate"]["rate"]["sheet"] == 1.0 and sq["count"] == 2
    png = c.get("/logic/api/jobs/a25b25c25d25/teach/crop.png", params={"page": 1, "x0": 480, "y0": 70, "x1": 540, "y1": 110})
    assert png.status_code == 200 and png.content[:4] == b"\x89PNG"
    r = c.post("/logic/api/jobs/a25b25c25d25/teach", json={"kind": "SKIP", "qid": "Qx", "author": "홍길동"}).json()
    assert "Qx" in r["saved"]["skipped"]


def test_known_sheet_names_read_the_same_but_fast():
    """시트 이름이 800개인 묶음(19VA)에서 칸마다 이름마다 정규식을 새로 만들던 것 — 같은 답을 빠르게 (L25 · 19VA 881초 → 277초)."""
    import re
    import time
    from app.logic import refs as RF
    known = {f"HH{i // 100:02d}_G{i:03d}": i for i in range(800)}
    known["0016"] = 1
    known["FG_G-101"] = 2

    def naive(text):
        t = RF._gen_text(text)
        out, taken = [], []
        for no in sorted({k.upper() for k in known if k}, key=len, reverse=True):
            for m in re.finditer(rf"(?<![A-Z0-9_]){re.escape(no)}\s*(?:[-/.:#]|\s)\s*(\d{{1,3}})(?!\d)", t):
                if any(a <= m.start() < b for a, b in taken):
                    continue
                taken.append((m.start(), m.end()))
                out.append((m.start(), no, int(m.group(1))))
        return [(a, b) for _, a, b in sorted(out)]
    texts = ["HH01_G144-72", "0016/72 0016/77", "FG_G-101-15", "FROM DRIVE", "HH07_G777 12 · HH00_G001/3", "LOGIC"]
    for t in texts:
        assert RF._known(t, known) == naive(t)
    t0 = time.time()
    for _ in range(300):
        for t in texts:
            RF._known(t, known)
    assert time.time() - t0 < 2.0
