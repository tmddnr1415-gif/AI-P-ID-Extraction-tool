"""hotfix81 — 새 프로젝트 점검표.

점검표는 **판정하지 않는다** — 저장된 사실만 읽어 `유도 / 폴백 / 사람 몫` 으로 가르고,
사람 몫마다 어느 판에서 답하는지를 적는다.  엔진 모듈을 import 하지 않는다.
"""
from __future__ import annotations

import ast
import json
import pathlib
import re
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")
MAIN = (ROOT / "app/main.py").read_text(encoding="utf-8")
DB = (ROOT / "app/db.py").read_text(encoding="utf-8")
DOC = (ROOT / "docs/new_form_checklist.md").read_text(encoding="utf-8")


def _engine(**over):
    e = {
        "profile": {"path": "project_alnouf1.yaml", "code": "D00P", "name": "AL NOUF1 PROJECT",
                    "document_code": "9Z9Z", "matched": False, "borrowed_from": "project_alnouf1.yaml"},
        "borrowed": {"count": 3, "read": 10, "from": "project_alnouf1.yaml",
                     "keys": ["formats.date", "anchors.type_map", "title_block.hist_row_inset"],
                     "by_section": {"formats": 1, "anchors": 1, "title_block": 1}, "replaced_by_sheet": ["x"]},
        "applied_rules": {"layout": {"items": [
            {"key": "regions.drawing_area", "source": "DERIVED"},
            {"key": "broken_line.brk_max_mark", "source": "UNAVAILABLE"}],
            "notes": ["mixed page sizes: 2384.0x1684.0 pt x2, 1191.0x842.0 pt x1; measured on the 2 majority-size pages only"]}},
        "legend": {"butterfly": {"source": "LEGEND", "note": ""},
                   "pneumatic": {"source": "CONFIG_FALLBACK", "note": "no legend sheet prints it; using valves.legend_fallback.pneumatic"}},
        "legend_profile": {"mode": "derived", "legend_sheets": [2]},
        "multipliers": {"source": "CONFIG_FALLBACK", "note": "legend table not found", "table": {"00": 1}},
        "evidence_tier": {"tier": 2, "rows": 3, "tagged_rows": 0},
        "valve_layout": {"legend_scale": 2.0, "legend_scale_source": "A3 legend on A1 sheets",
                         "act_box_source": "LEGEND", "source": "LEGEND"},
        "description_build": {"isa_table": {"page_no": 2, "first": {"P": ["PRESSURE"]}, "succeeding": {}}},
    }
    e.update(over)
    return e


PAGES = [{"page_no": 1, "page_kind": "PID", "drawing_no": "9Z9Z-00AAA10-M05-0001", "rev": "A", "width": 2384, "height": 1684},
         {"page_no": 2, "page_kind": "UNKNOWN", "drawing_no": "", "rev": "", "width": 2384, "height": 1684},
         {"page_no": 3, "page_kind": "UNKNOWN", "drawing_no": "", "rev": "", "width": 1191, "height": 842}]
ROWS = [{"key": "a", "page_no": 1, "tab": "FIELD", "values": {"scope": "SCT", "type": "PI"},
         "evidence": {"review_codes": ["MULTIPLIER_FROM_CONFIG"]}},
        {"key": "b", "page_no": 1, "tab": "FIELD", "values": {"scope": "VENDOR", "type": "TI"},
         "evidence": {"review_codes": ["VENDOR_MARK_UNDEFINED", "MULTIPLIER_FROM_CONFIG"]}},
        {"key": "c", "page_no": 1, "tab": "REVIEW", "values": {"scope": "", "type": "MOV"},
         "evidence": {"review_codes": ["TAGGED_VALVE_NO_ACTUATOR"]}}]


def test_the_report_splits_derived_fallback_and_human_work():
    from app import intake
    out = intake.build(_engine(), PAGES, ROWS)
    by = {s["key"]: s for s in out["sections"]}
    assert out["verdict"] == "todo"
    # 양식: 프로필 없음 → 새 프로젝트 · 못 읽은 장 하나(범례 장 2 는 뺀다) → 장 도면번호 판
    tb = by["titleblock"]
    assert tb["status"] == "todo"
    assert tb["facts"]["unknown_pages"] == [3]
    assert any("project_<이름>.yaml" in t["what"] for t in tb["todo"])
    assert any("장 도면번호 판" in t["where"] for t in tb["todo"])
    assert any("brk_max_mark" in l for l in tb["lines"])
    # 범례: 폴백 하나 → warn · 누구의 값인지 · ISA SUCCEEDING 0 → 경고
    lg = by["legend"]
    assert lg["status"] == "warn"
    assert any("CONFIG_FALLBACK" in l and "project_alnouf1.yaml" in l for l in lg["lines"])
    assert any("x2.0" in l for l in lg["lines"])
    assert any("SUCCEEDING 열을 못 읽었다" in l for l in lg["lines"])
    # 승수: 묻는 행 2 → 수량 승수 판
    mu = by["multipliers"]
    assert mu["status"] == "todo" and mu["facts"]["asking"] == {"MULTIPLIER_FROM_CONFIG": 2}
    assert mu["todo"][0]["where"].startswith("수량 승수 판")
    # SCOPE: 정의되지 않은 별표 1 → 근거 패널
    sc = by["scope"]
    assert sc["facts"]["undefined"] == 1 and sc["status"] == "todo"
    # 검토: 승수·SCOPE 는 자기 섹션이 말하고 여기서는 TAGGED_VALVE_NO_ACTUATOR 만 todo 로
    rv = by["review"]
    assert [t["what"].split(" ")[0] for t in rv["todo"]] == ["TAGGED_VALVE_NO_ACTUATOR"]
    # 사람 몫 묶음과 글
    assert len(out["todo"]) >= 5 and all(t["where"] for t in out["todo"])
    assert "## 사람 몫" in out["text"] and "★ 양식" in out["text"]


def test_a_document_that_answered_everything_is_ok():
    from app import intake
    e = _engine(profile={"path": "project_x.yaml", "code": "9Z9Z", "name": "X", "matched": True},
                borrowed={"count": 0, "read": 10, "keys": []},
                legend={"butterfly": {"source": "LEGEND"}},
                multipliers={"source": "LEGEND", "table": {"00": 1}},
                valve_layout={"legend_scale": 1.0, "act_box_source": "LEGEND", "source": "LEGEND"},
                description_build={"isa_table": {"first": {"P": []}, "succeeding": {"I": []}}})
    pages = [dict(PAGES[0])]
    rows = [{"key": "a", "page_no": 1, "tab": "FIELD", "values": {"scope": "SCT"}, "evidence": {"review_codes": []}}]
    out = intake.build(e, pages, rows)
    assert out["verdict"] == "ok" and out["todo"] == []


def test_the_report_imports_no_engine_and_decides_nothing():
    src = (ROOT / "app/intake.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
            assert not any(n.startswith("app") for n in names), names
    # 좌표·반경·문턱이 없다 — 사실을 옮겨 적는 모듈이다
    assert "pymupdf" not in src and "fitz" not in src


def test_the_api_builds_the_report_from_the_stored_facts(tmp_path):
    import os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from fastapi.testclient import TestClient
    from app import main, db
    c = TestClient(main.app)
    job = "jin"
    main.CON.execute(
        "INSERT INTO job (id,pdf_name,pdf_sha256,pdf_path,created_at,status,progress,message,"
        "fingerprint,project,revision,engine_json)"
        " VALUES (?,?,?,?,?,'done',1.0,'','','','A',?)",
        (job, "x.pdf", job, str(tmp_path / "x.pdf"), time.time(), json.dumps(_engine())))
    for p in PAGES:
        main.CON.execute("INSERT INTO pid_page (job_id,page_no,drawing_no,title,page_kind,in_scope,scope_reason,"
                         "width,height,layers_json,rev,rev_method,rev_confidence,rev_date)"
                         " VALUES (?,?,?,?,?,1,'',?,?,'{}',?,'','','')",
                         (job, p["page_no"], p["drawing_no"], "", p["page_kind"], p["width"], p["height"], p["rev"]))
    db.add_row(main.CON, job, page_no=1, tab="FIELD", drawing_no="9Z9Z-00AAA10-M05-0001",
               values={"type": "PI", "qty": 1, "scope": "SCT"}, rect=[1, 2, 3, 4],
               evidence={"review_codes": ["MULTIPLIER_FROM_CONFIG"]})
    main.CON.commit()
    r = c.get(f"/jobs/{job}/intake")
    assert r.status_code == 200
    out = r.json()
    assert out["job_id"] == job and out["verdict"] == "todo"
    assert any(s["key"] == "multipliers" and s["status"] == "todo" for s in out["sections"])
    assert any("수량 승수 판" in t["where"] for t in out["todo"])
    t = c.get(f"/jobs/{job}/intake?format=text")
    assert t.status_code == 200 and "# 새 프로젝트 점검표" in t.text
    assert c.get("/jobs/nope/intake").status_code == 404


def test_the_screen_has_one_entry_in_the_menu_and_one_chip_on_the_band():
    assert 'id="intake-btn"' in HTML
    assert "async function showIntake" in JS and "function loadIntakeChip" in JS
    assert "/intake" in JS
    # 띠는 범례 띠가 선 뒤에 붙는다 (같은 함수의 끝)
    i = JS.index("async function loadLegendProfile")
    j = JS.index("loadIntakeChip();", i)
    assert j > i


def test_the_three_facts_the_report_needs_are_stored_outside_the_fingerprint():
    for key in ("valve_layout", "isa_anchors", "unit_forms"):
        assert f'"{key}"' in DB
    # 지문 재료는 그대로 — fingerprint() 가 읽는 키는 바뀌지 않았다
    pipe = (ROOT / "app/pipeline.py").read_text(encoding="utf-8")
    m = re.search(r"def fingerprint\(.*?\n(?:.*\n){0,40}", pipe)
    assert m and "valve_layout" not in m.group(0) and "isa_anchors" not in m.group(0)


def test_must_measure_by_hand_is_the_one_undrawn_value():
    # 24회차가 이력 표 다섯 칸을 유도로 바꿨다 — API 와 문서가 여섯을 적던 것을 하나로
    m = re.search(r'"must_measure_by_hand": \[(.*?)\]', MAIN, re.S)
    assert m and m.group(1).strip() == '"title_block.hist_row_inset"'
    assert '"unavailable"' in MAIN
    assert "`title_block.hist_row_inset`" in DOC
    assert "| `title_block.hist_rev_col` |" not in DOC      # 옛 여섯 줄 표는 없다
