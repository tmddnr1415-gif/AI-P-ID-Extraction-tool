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


# ---------------------------------------------------------------- 사람이 그은 테두리

def test_taught_border_still_measures_the_title_column(tmp_path, monkeypatch):
    """사람이 테두리를 그어도 타이틀블록 열은 그 안의 세로 괘선으로 잰다 (TC2 시뮬레이션이 잡은 것 —
    재지 않으면 도면번호 칸이 폭 0 이 된다)."""
    import derive_layout
    doc = pymupdf.open()
    for _ in range(3):
        page = doc.new_page(width=1191, height=842)
        sh = page.new_shape()
        sh.draw_line((1000, 20), (1000, 820))              # 타이틀블록 열 경계 (테두리는 안 그림)
        sh.finish(color=(0, 0, 0), width=0.5)
        sh.commit()
    path = tmp_path / "frame.pdf"
    doc.save(path)
    _doc, pages = pidcache.load_pages(path)
    monkeypatch.setattr(derive_layout, "TAUGHT_FRAME", [20.0, 20.0, 1170.0, 820.0])
    l, t, r, b, column, xs, ys = derive_layout._frame(pages)
    assert (l, t, r, b) == (20.0, 20.0, 1170.0, 820.0)
    assert abs(column - 1000.0) < 1.0
    # 그은 것이 없으면 종이가 테두리다 — 열은 그 안에서 똑같이 잰다
    monkeypatch.setattr(derive_layout, "TAUGHT_FRAME", None)
    l, t, r, b, column, xs, ys = derive_layout._frame(pages)
    assert (l, t, r, b) == (0.0, 0.0, 1191.0, 842.0) and abs(column - 1000.0) < 1.0
    monkeypatch.setattr(derive_layout, "PAPER_STANDS_IN", False)
    assert derive_layout._frame(pages) is None


# ---------------------------------------------------------------- 최소 입력 — 누르기 한 번

def test_click_inside_a_bubble_returns_that_bubble(stub_pdf):
    """버블 안 글자 위를 한 번 누르면 그 버블의 둘레 — 사람이 사각형을 그을 필요가 없다."""
    _doc, pages = pidcache.load_pages(stub_pdf)
    pc = pages[0]
    r = ds.bubble_at(pc, 65, 105.5)                       # 첫 버블의 한가운데
    assert r is not None and abs(r.x0 - 50) < 1.0 and abs(r.x1 - 80) < 1.0
    # 그 둘레로 배운 모양이 나머지를 찾는다 (끌어 그은 것과 같은 길)
    t = ds.learn_bubble_template(pc, [r.x0 - 1.5, r.y0 - 1.5, r.x1 + 1.5, r.y1 + 1.5])
    assert t is not None and len(ds.taught_bubbles(pc, [t])) == 8
    assert ds.bubble_at(pc, 560, 380) is None             # 아무것도 없는 자리


def test_legend_page_button_finds_headings_by_keyword(monkeypatch):
    """[이 장이 범례입니다] 하나로 세 칸 — 그 장에서 VALVES · ACTUATORS · SIGNAL 낱말로 찾는다."""
    p1 = _fake_page(1, [((10, 10, 40, 18), "ACTUATORS")])                     # 범례가 아닌 장
    p2 = _fake_page(2, [((50, 665, 53, 673), "2."), ((54, 665, 80, 673), "VALVES"),
                        ((50, 135, 53, 143), "3."), ((54, 135, 90, 143), "ACTUATORS"),
                        ((84, 201, 130, 212), "ELECTRICAL"), ((132, 201, 160, 212), "SIGNAL")])
    monkeypatch.setenv("PID_FORM_AUTO", "0")
    monkeypatch.setattr(legend_rules, "TAUGHT", {})
    monkeypatch.setattr(legend_rules, "TAUGHT_PAGE", None)
    assert legend_rules._page_with([p1, p2], legend_rules.ACTUATOR_HEADING) is None
    monkeypatch.setattr(legend_rules, "TAUGHT_PAGE", 2)
    for h in legend_rules.TEACHABLE_HEADINGS:
        assert legend_rules._page_with([p1, p2], h) is p2, h
    # 칸 안 자리는 사각형이 없으니 그 낱말이 정한다 — 재는 함수들의 `_label(pc, "ACTUATORS")` 와 같다
    assert legend_rules.taught_word(p2, legend_rules.ACTUATOR_HEADING, "ACTUATORS") is None
    assert round(legend_rules._label(p2, "ACTUATORS").x0) == 54


def test_paper_stands_in_for_a_missing_border(tmp_path, monkeypatch):
    """테두리를 못 찾으면 종이가 테두리다 — 그래도 타이틀블록 열은 안쪽 괘선으로 잰다.
    그래서 사람에게 도면 영역을 묻지 않는다 (Takhiatash 에서 타이틀블록 묻기가 사라진 이유)."""
    import derive_layout
    doc = pymupdf.open()
    for _ in range(3):
        page = doc.new_page(width=1191, height=842)
        sh = page.new_shape()
        sh.draw_line((1000, 2), (1000, 840))
        sh.finish(color=(0, 0, 0), width=0.5)
        sh.commit()
    path = tmp_path / "noframe.pdf"
    doc.save(path)
    _doc, pages = pidcache.load_pages(path)
    monkeypatch.setenv("PID_FORM_AUTO", "0")
    monkeypatch.setattr(derive_layout, "TAUGHT_FRAME", None)
    got = derive_layout._frame(pages)
    assert got is not None
    l, t, r, b = got[:4]
    assert (l, t, r, b) == (0, 0, 1191.0, 842.0)
    monkeypatch.setattr(derive_layout, "PAPER_STANDS_IN", False)
    assert derive_layout._frame(pages) is None            # 끄면 예전처럼 못 찾는다


def test_screen_asks_only_what_is_needed_and_by_click():
    """화면은 서버가 미리 본 것(needs)만 할 일로 세우고, 할 일 하나는 누르기 한 번이다."""
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    main_src = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    assert 'id="tbfix-tasks"' in html and 'id="tbfix-adv"' in html            # 사각형 긋기는 접혀 있다
    assert "TB.needs = (TB.tstate && TB.tstate.needs)" in js
    assert "/teach/click" in js and '@app.post("/jobs/{job_id}/teach/click")' in main_src
    for k in ("dwg_no", "legend", "bubbles", "notes"):
        assert f"  {k}: {{ title:" in js, k
    # 할 일의 이름과 서버의 needs 가 같은 낱말이다
    for k in ('"dwg_no"', '"legend"', '"bubbles"', '"notes?"'):
        assert f"needs.append({k})" in main_src, k


def _rules_pdf(tmp_path, verticals):
    doc = pymupdf.open()
    for _ in range(3):
        page = doc.new_page(width=1191, height=842)
        sh = page.new_shape()
        sh.draw_rect(pymupdf.Rect(20, 20, 1171, 822))
        for x in verticals:
            sh.draw_line((x, 20), (x, 822))
        sh.finish(color=(0, 0, 0), width=0.5)
        sh.commit()
    path = tmp_path / "rules.pdf"
    doc.save(path)
    _doc, pages = pidcache.load_pages(path)
    return pages


def test_notes_click_in_the_title_column_takes_the_whole_column(tmp_path, monkeypatch):
    """노트가 타이틀블록 열에 사는 양식(AL NOUF1) — 왼쪽은 그 열의 괘선 (글 왼쪽에 그린 별표가 들어온다)."""
    import derive_layout
    monkeypatch.setattr(derive_layout, "TAUGHT_FRAME", None)
    pages = _rules_pdf(tmp_path, [990])
    r = derive_layout.notes_from_heading(pages, pymupdf.Rect(1010, 300, 1040, 308), 8)
    # 열 전체 — 위도 테두리 (제목이 장마다 다른 높이에 있어도 그 위의 별표 정의가 들어온다 · QFE)
    assert abs(r[0] - 990) < 1 and abs(r[1] - 20) < 1 and abs(r[2] - 1171) < 1 and abs(r[3] - 822) < 1


def test_notes_click_inside_the_drawing_starts_at_the_heading(tmp_path, monkeypatch):
    """노트가 도면 안에 사는 양식(Takhiatash) — 가장 가까운 괘선이 테두리라 그것을 쓰면 도면 전체가 노트다."""
    import derive_layout
    monkeypatch.setattr(derive_layout, "TAUGHT_FRAME", None)
    pages = _rules_pdf(tmp_path, [])
    r = derive_layout.notes_from_heading(pages, pymupdf.Rect(970, 22, 990, 30), 8)
    assert abs(r[0] - 962) < 1 and r[1] == 18


def test_size_band_is_half_to_double_the_example():
    """사람은 아무 버블이나 누른다 — 가장 큰 것이든 가장 작은 것이든 (AL NOUF1 22.6 ↔ RO 17.0 ↔ 세로 15.1)."""
    lo, hi = ds.TEACH_CAP_SIZE
    assert lo <= 15.1 / 22.6 and hi >= 22.6 / 15.1 and lo > 0 and hi <= 2.0


def test_legend_over_several_pages(monkeypatch):
    """범례가 여러 장(TC2 p2~p4) — 액추에이터 장의 `VALVES ACTUATORS` 는 밸브 칸이 아니다.
    두 장을 다 알려 주면 각 칸이 제 장에서 찾힌다."""
    p2 = _fake_page(2, [((50, 60, 70, 68), "LINE"), ((72, 60, 100, 68), "VALVES")])
    p4 = _fake_page(4, [((50, 60, 80, 68), "VALVES"), ((82, 60, 120, 68), "ACTUATORS")])
    monkeypatch.setenv("PID_TEACH_BLIND", "legend")
    monkeypatch.setattr(legend_rules, "TAUGHT", {})
    monkeypatch.setattr(legend_rules, "TAUGHT_PAGE", [4])
    assert legend_rules._page_with([p2, p4], "LINE VALVES") is None          # 밸브 칸이 아니다
    assert legend_rules._page_with([p2, p4], "VALVES ACTUATORS") is p4
    monkeypatch.setattr(legend_rules, "TAUGHT_PAGE", [4, 2])
    assert legend_rules._page_with([p2, p4], "LINE VALVES") is p2
    monkeypatch.setattr(legend_rules, "TAUGHT_PAGE", 2)                     # 옛 꼴(번호 하나)도 읽는다
    assert legend_rules._page_with([p2, p4], "LINE VALVES") is p2
    # 겹쳐 인쇄한 범례(QFE) — `VALVES VALVES VALVES ACTUATORS` 도 액추에이터 칸 제목이다
    p3 = _fake_page(3, [((50 + 0.01 * i, 60, 80, 68), "VALVES") for i in range(3)]
                    + [((82 + 0.01 * i, 60, 120, 68), "ACTUATORS") for i in range(3)])
    monkeypatch.setattr(legend_rules, "TAUGHT_PAGE", [3])
    assert legend_rules._page_with([p3], "LINE VALVES") is None


def test_legend_pages_are_stored_as_a_list(tmp_path):
    data = form_teach.set_items(tmp_path, "P", author="kim",
                                legend_page=[{"page_no": 4, "size": [1191, 842]}, {"page_no": 2, "size": [1191, 842]},
                                             {"page_no": 4, "size": [1191, 842]}])
    assert [x["page_no"] for x in data["legend_page"]] == [4, 2]
    data = form_teach.set_items(tmp_path, "P", author="kim", legend_page={"page_no": 3, "size": [1191, 842]})
    assert [x["page_no"] for x in data["legend_page"]] == [3]


# ---------------------------------------------------------------- 읽을 수 없는 PDF → DXF 안내

def _text_and_strokes_pdf(tmp_path):
    """글자가 있는 장 넷 + 글자를 선으로만 그린 장 하나."""
    doc = pymupdf.open()
    for i in range(4):
        page = doc.new_page(width=600, height=400)
        for k in range(40):
            page.insert_text((20 + (k % 8) * 70, 30 + (k // 8) * 20), f"PIT-{i}{k:02d}", fontsize=6)
    page = doc.new_page(width=600, height=400)
    sh = page.new_shape()
    for k in range(60):                                   # 글자 대신 획
        sh.draw_line((20 + k * 8, 50), (24 + k * 8, 60))
    sh.finish(color=(0, 0, 0), width=0.5)
    sh.commit()
    path = tmp_path / "strokes.pdf"
    doc.save(path)
    return path


def test_stroke_only_pages_are_found_against_the_document_itself(tmp_path):
    from app import main
    path = _text_and_strokes_pdf(tmp_path)
    job = {"pdf_path": str(path)}
    assert main._stroke_only_pages(job, [1, 2, 3, 4, 5]) == {5}       # 모든 장을 물어도
    assert main._stroke_only_pages(job, [5]) == {5}
    assert main._stroke_only_pages(job, [1]) == set()
    assert main._stroke_only_pages({"pdf_path": str(tmp_path / "none.pdf")}, [1]) == set()


def test_unreadable_pdf_opens_the_dxf_guide():
    """글자를 한 글자도 못 읽는 실패는 가르치기 판이 아니라 DXF 안내창이다 — 그 갈림이 파이프라인 문장과 맞는다."""
    js = (ROOT / "app" / "static" / "app.js").read_text(encoding="utf-8")
    src = (ROOT / "app" / "pipeline.py").read_text(encoding="utf-8")
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert "function showDxfGuide(" in js and "function unreadableCase(" in js
    assert "글자층이 없습니다" in src and "선(획)으로" in src and "스캔 이미지" in src
    assert 'id="prog-dxf"' in html and 'id="tbfix-stroke"' in html
    # 가르치기의 멈춤 셋과 겹치지 않는다 (글자층 없음은 TEACH_CASES 에 없다)
    cases = re.findall(r'kind: "(\w+)", re: /(.+?)/, item:', js)
    assert all("글자층" not in rx for _k, rx in cases)
