"""hotfix85 — 도면 가르치기: 새 양식에서 프로그램이 못 찾은 자리를 사람이 짚는다.

* 저장(`app/form_teach.py`) — 작성자 필수 · 프로젝트 필수 · 꺼지면 없던 것과 같다
* 버블 예시 → 같은 그림 찾기 (`detect_symbols.learn_bubble_template` · `taught_bubbles`)
* 범례 칸 머리말 (`legend_rules.TAUGHT`) · NOTES 영역 → CFG 에 얹고 분석 뒤 되돌린다
* 시뮬레이션 스위치 `PID_FORM_AUTO=0` (hotfix84 자동 갈래를 끈다 — 이전 프로그램 재현)
* 화면이 멈춘 이유를 가르는 낱말이 파이프라인 문장에 실제로 있다
"""
import re
import sys
import types
from pathlib import Path

import pymupdf
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app" / "engine"))
sys.path.insert(0, str(ROOT))

import detect_symbols as ds          # noqa: E402
import legend_rules                  # noqa: E402
import pidcache                      # noqa: E402
from app import form_teach           # noqa: E402


# ---------------------------------------------------------------- 저장

def test_store_requires_author_and_project(tmp_path):
    item = {"page_no": 2, "rect": [10, 10, 60, 30], "size": [1191, 842]}
    with pytest.raises(ValueError):
        form_teach.set_items(tmp_path, "P1", notes=item, author="")
    with pytest.raises(ValueError):
        form_teach.set_items(tmp_path, "", notes=item, author="kim")
    with pytest.raises(ValueError):
        form_teach.set_items(tmp_path, "P1", legend={"NOT A HEADING": item}, author="kim")
    assert form_teach.for_pipeline(tmp_path, "P1") == {}


def test_store_round_trip_and_partial_update(tmp_path):
    a = {"page_no": 2, "rect": [10, 10, 60, 30], "size": [1191, 842]}
    b = {"page_no": 6, "rect": [100, 100, 140, 115], "size": [1191, 842]}
    form_teach.set_items(tmp_path, "P1", legend={"VALVES ACTUATORS": a}, author="kim")
    form_teach.set_items(tmp_path, "P1", bubbles=[b, b], author="lee")
    got = form_teach.for_pipeline(tmp_path, "P1")
    assert got["legend"]["VALVES ACTUATORS"]["rect"] == [10.0, 10.0, 60.0, 30.0]
    assert len(got["bubbles"]) == 2 and got["author"] == "lee"
    # 빈 dict 는 그 칸을 지운다
    form_teach.set_items(tmp_path, "P1", legend={"VALVES ACTUATORS": {}}, bubbles=[], author="lee")
    assert form_teach.for_pipeline(tmp_path, "P1") == {}


def test_store_disabled_is_as_if_absent(tmp_path):
    a = {"page_no": 2, "rect": [10, 10, 60, 30], "size": [1191, 842]}
    form_teach.set_items(tmp_path, "P1", notes=a, author="kim")
    assert form_teach.for_pipeline(tmp_path, "P1")
    form_teach.set_enabled(tmp_path, "P1", False)
    assert form_teach.for_pipeline(tmp_path, "P1") == {}


# ---------------------------------------------------------------- 스위치

def test_form_auto_switch(monkeypatch):
    monkeypatch.delenv("PID_FORM_AUTO", raising=False)
    assert pidcache.form_auto() is True
    monkeypatch.setenv("PID_FORM_AUTO", "0")
    assert pidcache.form_auto() is False


# ---------------------------------------------------------------- 버블 예시

def _stub_cap(shape, x, y0, y1, left: bool):
    """Takhiatash 처럼 '짧은 직선 + 곡선 + 짧은 직선' 으로 그린 반원 캡 하나 (한 path)."""
    h = y1 - y0
    stub = 0.1 * h
    bulge = -0.66 * h if left else 0.66 * h
    shape.draw_line((x, y0), (x, y0 + stub))
    shape.draw_bezier((x, y0 + stub), (x + bulge, y0 + stub), (x + bulge, y1 - stub), (x, y1 - stub))
    shape.draw_line((x, y1 - stub), (x, y1))
    shape.finish(color=(0, 0, 0), width=0.5)


def _bubble(page, x0, y0, w=30.0, h=11.0, text="PIT"):
    sh = page.new_shape()
    _stub_cap(sh, x0 + h / 2, y0, y0 + h, left=True)
    sh.commit()
    sh = page.new_shape()
    _stub_cap(sh, x0 + w - h / 2, y0, y0 + h, left=False)
    sh.commit()
    sh = page.new_shape()
    sh.draw_line((x0 + h / 2, y0), (x0 + w - h / 2, y0))
    sh.draw_line((x0 + h / 2, y0 + h), (x0 + w - h / 2, y0 + h))
    sh.finish(color=(0, 0, 0), width=0.5)
    sh.commit()
    page.insert_text((x0 + w / 2 - 6, y0 + h - 3), text, fontsize=6)


def _vbubble(page, x0, y0, w=11.0, h=30.0):
    """세로로 선 버블 — 위·아래 캡 (같은 그리는 법)."""
    stub = 0.1 * w
    for y, up in ((y0 + w / 2, True), (y0 + h - w / 2, False)):
        sh = page.new_shape()
        bulge = -0.66 * w if up else 0.66 * w
        sh.draw_line((x0, y), (x0 + stub, y))
        sh.draw_bezier((x0 + stub, y), (x0 + stub, y + bulge), (x0 + w - stub, y + bulge), (x0 + w - stub, y))
        sh.draw_line((x0 + w - stub, y), (x0 + w, y))
        sh.finish(color=(0, 0, 0), width=0.5)
        sh.commit()
    sh = page.new_shape()
    sh.draw_line((x0, y0 + w / 2), (x0, y0 + h - w / 2))
    sh.draw_line((x0 + w, y0 + w / 2), (x0 + w, y0 + h - w / 2))
    sh.finish(color=(0, 0, 0), width=0.5)
    sh.commit()


@pytest.fixture()
def stub_pdf(tmp_path):
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=400)
    for i in range(5):
        _bubble(page, 50 + i * 60, 100)
    _bubble(page, 80, 250, text="TIT")
    _bubble(page, 200, 250, w=45.0, text="FIT")          # 더 긴 버블
    _vbubble(page, 400, 200)                              # 세로로 선 버블
    path = tmp_path / "stub.pdf"
    doc.save(path)
    return path


def test_stub_bubbles_invisible_to_old_rule(stub_pdf, monkeypatch):
    monkeypatch.setenv("PID_FORM_AUTO", "0")
    monkeypatch.setattr(ds, "TAUGHT_BUBBLES", [])
    _doc, pages = pidcache.load_pages(stub_pdf)
    assert ds.bubble_outlines(pages[0]) == []


def test_one_example_finds_the_rest(stub_pdf, monkeypatch):
    monkeypatch.setenv("PID_FORM_AUTO", "0")
    _doc, pages = pidcache.load_pages(stub_pdf)
    pc = pages[0]
    t = ds.learn_bubble_template(pc, [47, 97, 83, 114])     # 첫 버블을 넉넉히 감싼 사각형
    assert t is not None and len(t["parts"]) == 2           # 캡 둘 — 글자 획은 안 든다
    assert t["mode"] == "caps"                              # 버블 끝 모양을 배웠다
    found = ds.taught_bubbles(pc, [t])
    # 같은 크기 6 + 더 긴 것 1 + 세로로 선 것 1 — 예시 하나로
    assert len(found) == 8 and all(o.style == "TAUGHT" for o in found)
    assert sum(1 for o in found if o.axis == "V") == 1
    assert any(abs(o.rect.width - 45) < 0.6 for o in found)
    # 버블 사각형은 그려진 곡선의 둘레다 (사람이 그은 사각형이 아니다)
    first = min(found, key=lambda o: (o.rect.y0, o.rect.x0)).rect
    assert abs(first.x0 - 50) < 0.6 and abs(first.x1 - 80) < 0.6
    # 파이프라인이 얹으면 규칙 결과에 더해진다
    monkeypatch.setattr(ds, "TAUGHT_BUBBLES", [t])
    assert len(ds.bubble_outlines(pc)) == 8


def test_example_without_curves_teaches_nothing(stub_pdf):
    _doc, pages = pidcache.load_pages(stub_pdf)
    assert ds.learn_bubble_template(pages[0], [500, 300, 590, 390]) is None


# ---------------------------------------------------------------- 범례 칸 머리말

def _fake_page(no, words):
    return types.SimpleNamespace(page_no=no, width=1191.0, height=842.0, analysis_scope="PID",
                                 words=[(pymupdf.Rect(*r), t) for r, t in words])


def test_taught_heading_finds_page_and_word(monkeypatch):
    p1 = _fake_page(1, [((10, 10, 40, 18), "NOTHING")])
    p2 = _fake_page(2, [((50, 665, 53, 673), "3."), ((54, 665, 80, 673), "ACTUATORS")])
    monkeypatch.setenv("PID_FORM_AUTO", "0")            # 이전 프로그램 — `3. ACTUATORS` 를 못 알아본다
    monkeypatch.setattr(legend_rules, "TAUGHT", {})
    assert legend_rules._page_with([p1, p2], legend_rules.ACTUATOR_HEADING) is None
    monkeypatch.setattr(legend_rules, "TAUGHT",
                        {legend_rules.ACTUATOR_HEADING: {"page_no": 2, "rect": [48, 663, 82, 675]}})
    assert legend_rules._page_with([p1, p2], legend_rules.ACTUATOR_HEADING) is p2
    w = legend_rules.taught_word(p2, legend_rules.ACTUATOR_HEADING, "ACTUATORS")
    assert round(w.x0) == 54
    assert legend_rules.taught_word(p1, legend_rules.ACTUATOR_HEADING) is None


# ---------------------------------------------------------------- 파이프라인 — 얹고 되돌린다

def test_apply_and_restore(monkeypatch):
    from app import pipeline as P
    p6 = _fake_page(6, [])
    p2 = _fake_page(2, [])
    before = P.CFG.get("regions.notes_area")
    teach = {"who": "kim",
             "notes": {"page_no": 6, "rect": [968, 20, 1184, 400], "size": [1191.0, 842.0]},
             "legend": {"ELECTRIC SIGNAL": {"page_no": 2, "rect": [84, 201, 130, 212], "size": [1191.0, 842.0]},
                        "LINE VALVES": {"page_no": 2, "rect": [1, 1, 9, 9], "size": [841.0, 595.0]}},
             "bubbles": []}
    monkeypatch.setattr(P, "_reconfigure", lambda pages: P._rebind_config())
    with P._own_config():
        out = P._apply_form_teach([p2, p6], {}, teach)
        assert P.CFG.get("regions.notes_area") == [968.0, 20.0, 1184.0, 400.0]
        assert P.ds.LAYOUT.notes_area == (968.0, 20.0, 1184.0, 400.0)
        assert "ELECTRIC SIGNAL" in legend_rules.TAUGHT
        # 다른 종이에서 그은 칸은 얹지 않고 사유를 남긴다
        assert "LINE VALVES" not in legend_rules.TAUGHT
        assert any("LINE VALVES" in s for s in out["skipped"])
    assert P.CFG.get("regions.notes_area") == before
    assert legend_rules.TAUGHT == {} and P.ds.TAUGHT_BUBBLES == []


def test_nothing_taught_changes_nothing():
    from app import pipeline as P
    out = P._apply_form_teach([], {}, None)
    assert out["applied"] == [] and out["skipped"] == []


# ---------------------------------------------------------------- 멈춤 · 화면

def test_bubbles_unreadable_is_a_known_stop():
    from app import analysis_proc, pipeline
    assert "BubblesUnreadable" in analysis_proc._KNOWN
    assert issubclass(pipeline.BubblesUnreadable, RuntimeError)
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert "pipeline.BubblesUnreadable) as exc:" in main_src


def test_screen_recognises_each_stop_message():
    """화면이 멈춘 이유를 가르는 낱말이 파이프라인이 쓰는 문장에 그대로 있다."""
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    flat = re.sub(r'"\s*\n\s*"', "", src)                    # 줄로 나뉜 문자열 잇기
    cases = re.findall(r'kind: "(\w+)", re: /(.+?)/, item:', js)
    assert {k for k, _ in cases} == {"titleblock", "legend", "bubbles"}
    for _kind, rx in cases:
        lit = rx.replace("\\(", "(").replace("\\)", ")")
        assert lit in flat, lit


def test_teach_values_reach_the_child():
    """서버가 가르친 값을 분석 자식에게 넘긴다 — 읽는 곳은 `_user_form_teach` 하나."""
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert main_src.count("form_teach=_user_form_teach(") == 1
    assert main_src.count("form_teach.for_pipeline(") == 1
