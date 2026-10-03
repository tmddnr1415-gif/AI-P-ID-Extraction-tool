"""hotfix29 — 타이틀블록 칸을 **사람이 도면 위에서 한 번 그어 두는 자리** (§9 ⑤ · §10 3급).

현장: 새 회사 양식이 올 때마다 `TitleBlockUnreadable` 로 멈추면 실효성이 없다.
엔진이 캡션 어휘·구조로 못 찾는 문서(획 글자 · 값이 안 갈리는 번호)에서는
실패 화면에서 사각형을 긋고 저장하면 다음 분석부터 그 칸을 읽는다.

  ① 저장 규율 — 도면번호 칸 필수 · 작성자 필수 · `enabled:false` 면 없던 때와 같다
  ② `_apply_user_cells` — 같은 종이 크기에서만 얹고, `formats.drawing_no` 도 그 칸에서
  ③ 끝에서 끝까지 — 없으면 `TitleBlockUnreadable`, 그으면 그 단계를 지난다
  ④ API — 미리보기(장마다 읽힘 · 형식) · 저장(400 규율) · 지우기 · 파이프라인에 넘기는 곳 하나
합성 PDF 로 돈다 — `data/` 없이.
"""
from __future__ import annotations
import asyncio, inspect, json, os, sys, time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
sys.path.insert(0, str(ROOT / "tests"))
from test_hotfix28_new_form import _new_form, A1     # noqa: E402
from app import title_block_cells as tbc            # noqa: E402

# 엔진이 못 찾는 문서 — 캡션이 없고 번호가 장마다 같아 구조로도 안 갈린다.
DWG_RECT = [A1[0] - 410.0, A1[1] - 296.0, A1[0] - 150.0, A1[1] - 264.0]   # 번호 글자 상자 1391.8~1413.8 을 감싼다


def _cells_json(project, data_dir):
    return json.loads((Path(data_dir) / "projects" / project / tbc.FILENAME).read_text(encoding="utf-8"))


def test_saving_needs_a_drawing_number_cell_and_an_author(tmp_path):
    from app import revisions
    revisions.create_project(tmp_path, "QFE")
    with pytest.raises(ValueError, match="작성자"):
        tbc.set_cells(tmp_path, "QFE", cells_in={"dwg_no_region": DWG_RECT}, size=A1, page_no=3)
    with pytest.raises(ValueError, match="도면번호"):
        tbc.set_cells(tmp_path, "QFE", cells_in={"title_region": DWG_RECT}, size=A1, page_no=3, author="검증")
    with pytest.raises(ValueError, match="크기가 0"):
        tbc.set_cells(tmp_path, "QFE", cells_in={"dwg_no_region": [1, 1, 1, 5]}, size=A1, page_no=3, author="검증")
    with pytest.raises(ValueError, match="프로젝트"):
        tbc.set_cells(tmp_path, "", cells_in={"dwg_no_region": DWG_RECT}, size=A1, page_no=3, author="검증")
    assert tbc.cells(tmp_path, "QFE") == {}                        # 아직 아무것도 없다
    data = tbc.set_cells(tmp_path, "QFE", cells_in={"dwg_no_region": DWG_RECT, "rev_box": None},
                         size=A1, page_no=3, author="검증", note="QFE 양식", job_id="j1")
    assert data["size"] == [A1[0], A1[1]] and data["page_no"] == 3 and data["origin_job"] == "j1"
    got = tbc.cells(tmp_path, "QFE")
    assert got["cells"] == {"dwg_no_region": DWG_RECT} and got["size"] == [A1[0], A1[1]]
    assert got["who"].startswith("검증 · ") and "QFE 양식" in got["who"]
    # 끄면 없던 때와 정확히 같다 — 파일은 남는다
    tbc.set_enabled(tmp_path, "QFE", False)
    assert tbc.cells(tmp_path, "QFE") == {} and _cells_json("QFE", tmp_path)["cells"]
    tbc.set_enabled(tmp_path, "QFE", True)
    assert tbc.cells(tmp_path, "QFE")["cells"]
    assert tbc.clear(tmp_path, "QFE") and tbc.cells(tmp_path, "QFE") == {} and not tbc.clear(tmp_path, "QFE")


def _layout_for(pages):
    from app import pipeline as P
    with P._own_config():
        layout = P._fit_layout(pages)
        yield_layout = dict(layout)
        yield_layout["moved"] = list(layout.get("moved") or [])
    return yield_layout


def test_user_cells_overlay_only_on_the_same_paper_and_derive_the_number_format(tmp_path):
    from app import pipeline as P
    from app.engine.pidcache import load_pages
    pdf = _new_form(tmp_path / "same.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
    _doc, pages = load_pages(pdf)
    user = {"cells": {"dwg_no_region": DWG_RECT,
                      "title_region": [A1[0] - 410.0, A1[1] - 172.0, A1[0] - 150.0, A1[1] - 148.0]},
            "size": [A1[0], A1[1]], "who": "검증 · 2026-09-29"}
    with P._own_config():
        layout = P._fit_layout(pages)
        assert "title_block.dwg_no_region" not in {m["key"] for m in layout.get("moved", [])}
        before = P.CFG.get("formats.drawing_no")
        out = P._apply_user_cells(pages, layout, user)
        assert out["reason"] == "" and out["who"] == "검증 · 2026-09-29"
        assert set(out["applied"]) == {"title_block.dwg_no_region", "title_block.title_region",
                                       "title_block.title_min_height", "formats.drawing_no"}
        users = [m for m in layout["moved"] if m.get("source") == "USER"]
        assert {m["key"] for m in users} >= {"title_block.dwg_no_region", "formats.drawing_no"}
        assert P.CFG.get("title_block.dwg_no_region") == DWG_RECT
        pat = P.CFG.get("formats.drawing_no")
        assert pat != before and P.re.match(pat, "QFE-P1-PID-001") and not P.re.match(pat, "QFE-2026-001")
        assert P.tb.DWG_NO_RE.pattern == pat                       # 정규식도 다시 만들어졌다
        assert P.CFG.get("title_block.title_min_height") == 0.0
    # 되돌려졌다 — 다음 분석으로 새지 않는다
    assert P.CFG.get("formats.drawing_no") == before and P.tb.DWG_NO_RE.pattern == before
    # 다른 종이에서 그은 칸은 얹지 않고 사유를 말한다
    with P._own_config():
        layout = P._fit_layout(pages)
        out = P._apply_user_cells(pages, layout, dict(user, size=[1191.0, 842.0]))
        assert out["applied"] == [] and "1191.0x842.0" in out["reason"] and "not applied" in out["reason"]
        assert not [m for m in layout.get("moved", []) if m.get("source") == "USER"]
    # 빈 값은 이 기능이 없던 때와 정확히 같다
    with P._own_config():
        layout = P._fit_layout(pages)
        n = len(layout.get("moved", []))
        assert P._apply_user_cells(pages, layout, {}) == {"applied": [], "reason": "", "who": ""}
        assert len(layout.get("moved", [])) == n


def test_drawn_cell_without_a_recurring_number_keeps_the_config_format(tmp_path):
    from app import pipeline as P
    from app.engine.pidcache import load_pages
    pdf = _new_form(tmp_path / "same.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
    _doc, pages = load_pages(pdf)
    with P._own_config():
        layout = P._fit_layout(pages)
        before = P.CFG.get("formats.drawing_no")
        out = P._apply_user_cells(pages, layout, {"cells": {"dwg_no_region": [10.0, 10.0, 30.0, 20.0]},
                                                  "size": [A1[0], A1[1]]})
        assert "formats.drawing_no" not in out["applied"] and "no hyphenated number" in out["reason"]
        assert P.CFG.get("formats.drawing_no") == before


@pytest.mark.slow
def test_end_to_end_a_drawn_cell_gets_past_the_title_block_stage(tmp_path):
    from app import pipeline as P
    pdf = _new_form(tmp_path / "same.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
    with pytest.raises(P.TitleBlockUnreadable) as exc:
        P.analyse(pdf)
    assert "도면번호를 읽지 못했습니다" in str(exc.value)
    user = {"cells": {"dwg_no_region": DWG_RECT}, "size": [A1[0], A1[1]], "who": "검증"}
    with pytest.raises(P.LegendUnavailable):                    # 타이틀블록 단계를 지났다
        P.analyse(pdf, title_block_cells=user)
    # 다른 종이 크기로 적힌 칸은 아무것도 바꾸지 않는다
    with pytest.raises(P.TitleBlockUnreadable):
        P.analyse(pdf, title_block_cells=dict(user, size=[1191.0, 842.0]))


def test_pipeline_has_one_place_that_overlays_user_cells():
    from app import pipeline as P, main
    body = inspect.getsource(P._analyse)
    assert body.count("_apply_user_cells(") == 1
    assert body.index("_apply_user_cells(") < body.index("raise TitleBlockUnreadable(")
    # 파이프라인에 넘기는 곳 하나 — 프로젝트에 안 묶이면 빈 값
    src = inspect.getsource(main._worker)
    assert "title_block_cells=_user_title_block(" in src
    assert main._user_title_block("") == {}
    assert inspect.getsource(main._user_title_block).count("title_block_cells.cells(") == 1


def _isolated_main(tmp_path):
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from app import db, main, revisions
    return db, main, revisions


def test_api_preview_save_and_clear(tmp_path):
    db, main, revisions = _isolated_main(tmp_path)
    from fastapi import HTTPException
    pdf = _new_form(tmp_path / "same.pdf", numbers=["QFE-P1-PID-001"] * 6, caption="", title_caption="")
    revisions.create_project(tmp_path, "QFE")
    for jid, project in (("j1", "QFE"), ("j0", "")):
        db.create_job(main.CON, jid, pdf.name, "sha", pdf)
        main.CON.execute("UPDATE job SET project=?, status='failed', message=? WHERE id=?",
                         (project, "이 PDF 의 8장 어디에서도 도면번호를 읽지 못했습니다.", jid))
    main.CON.commit()
    st = main.titleblock_state("j1")
    assert st["supported"] and st["project"] == "QFE" and st["page_count"] == 8
    assert st["form_size"] == [A1[0], A1[1]] and st["form_pages"] == [3, 4, 5, 6, 7, 8]
    assert st["suggested_page"] == 3 and st["saved"] is None and st["derived"] == {}
    assert st["sizes"][0] == {"size": [A1[0], A1[1]], "pages": 6}
    # 미리보기 — 같은 크기의 장 전부에서 읽고 형식을 낸다 · 코드 낱말만
    pv = main.titleblock_preview("j1", {"cell": "dwg_no_region", "rect": DWG_RECT})
    assert pv["read"] == 6 and pv["total"] == 6 and pv["distinct"] == 1
    assert all(g["text"] == "QFE-P1-PID-001" for g in pv["pages"]) and [g["page_no"] for g in pv["pages"]] == [3, 4, 5, 6, 7, 8]
    assert pv["pattern"] and pv["shapes"] == {"L3-A2-L3-D3": 6}
    empty = main.titleblock_preview("j1", {"cell": "dwg_no_region", "rect": [10, 10, 30, 20]})
    assert empty["read"] == 0 and empty["pattern"] is None
    title = main.titleblock_preview("j1", {"cell": "title_region",
                                           "rect": [A1[0] - 410.0, A1[1] - 172.0, A1[0] - 150.0, A1[1] - 148.0]})
    assert title["read"] == 6 and title["distinct"] == 6 and "FUEL GAS SYSTEM 1" in title["pages"][0]["text"] and "pattern" not in title
    with pytest.raises(HTTPException) as e:
        main.titleblock_preview("j1", {"cell": "bogus", "rect": DWG_RECT})
    assert e.value.status_code == 400
    # 저장 규율은 서버에서도 400 으로 선다
    for payload, word in (({"cells": {"dwg_no_region": DWG_RECT}, "page_no": 3}, "작성자"),
                          ({"cells": {"title_region": DWG_RECT}, "page_no": 3, "author": "검증"}, "도면번호")):
        with pytest.raises(HTTPException) as e:
            main.titleblock_save("j1", payload)
        assert e.value.status_code == 400 and word in e.value.detail
    with pytest.raises(HTTPException) as e:                       # 프로젝트 없는 분석은 저장할 자리가 없다
        main.titleblock_save("j0", {"cells": {"dwg_no_region": DWG_RECT}, "page_no": 3, "author": "검증"})
    assert e.value.status_code == 400 and "프로젝트" in e.value.detail
    out = main.titleblock_save("j1", {"cells": {"dwg_no_region": DWG_RECT}, "page_no": 3, "author": "검증", "note": "QFE"})
    assert out["saved"]["size"] == [A1[0], A1[1]] and out["saved"]["origin_job"] == "j1" and "다시 분석" in out["applies"]
    # 파이프라인에 넘기는 값 — 크기가 그 종이의 것이다
    user = main._user_title_block("QFE")
    assert user["cells"] == {"dwg_no_region": DWG_RECT} and user["size"] == [A1[0], A1[1]]
    st = main.titleblock_state("j1")
    assert st["saved"]["author"] == "검증" and st["saved"]["cells"]["dwg_no_region"] == DWG_RECT
    assert main.titleblock_clear("j1") == {"cleared": True} and main._user_title_block("QFE") == {}
    assert main.titleblock_state("j1")["saved"] is None
    with pytest.raises(HTTPException):
        main.titleblock_state("nope")


def test_failure_screen_offers_the_panel_only_for_the_title_block_case():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    html = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
    fail = js.split("async function showFailure(", 1)[1].split("\nfunction ", 1)[0]
    assert "/도면번호를 읽지 못했습니다/.test(message" in fail and "#prog-tbfix" in fail
    assert 'id="prog-tbfix"' in html and 'id="tbfix"' in html and 'name="tbfix-cell"' in html
    save = js.split("async function tbSave(", 1)[1].split("\n}\n", 1)[0]
    # 작성자 없이 저장하지 않는다 · 저장 뒤 "다시 분석해야" 를 말한다
    assert "작성자를 적어야 저장됩니다" in save and "out.applies" in save
    run = js.split('$req("#tbfix-save-run")', 1)[1].split("\n});", 1)[0]
    assert "/reanalyse" in run and "watch(id, null, {})" in run
    # 좌표는 화면 배율을 되돌린 도면 pt 다 — 이미지 픽셀을 저장하지 않는다
    assert "(ev.clientX - b.left) / TB.zoom" in js and "(ev.clientY - b.top) / TB.zoom" in js
    assert "titleblock" in js.split("const _MUTATES", 1)[1].split("\n", 1)[0]
