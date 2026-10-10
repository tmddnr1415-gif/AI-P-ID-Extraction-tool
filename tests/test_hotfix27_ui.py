"""hotfix27 — Typical 상자 안 행 누르기 · 수량 승수 판 높이 · From/To 가볍게 + 직접 입력.

실제 동작은 `spike/ui_audit_hotfix27.py`(누르기 · 끌기)와 `spike/ui_time_fromto.py`(시간)가
띄워서 확인한다 — 여기서는 구조와 서버 규칙을 못박는다.
"""
from __future__ import annotations
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
HTML = (ROOT / "app/static/index.html").read_text(encoding="utf-8")


def _fn(name: str) -> str:
    return JS.split(f"function {name}(", 1)[1].split("\nfunction ", 1)[0]


def test_big_boxes_are_drawn_first_so_rows_inside_a_typical_box_take_the_click():
    seg = _fn("drawOverlay")
    assert "area(b[0].rect) - area(a[0].rect)" in seg      # 큰 것부터 — 작은 것이 위에 선다
    assert "for (const it of drawn)" in seg
    # 세는 것은 그대로 — 범례 등식(칸 합 = 상자 수)은 `overlayItems` 가 정한다
    assert "overlayItems(S.page).map((it, i) => [it, i])" in seg


def test_multiplier_panel_has_a_height_cap_a_fold_and_a_gutter():
    assert 'id="gutter-m"' in HTML
    assert HTML.index('id="mult-panel"') < HTML.index('id="gutter-m"') < HTML.index('id="filter"')
    assert ".mult-panel { flex: none; max-height: 170px; overflow: auto;" in CSS
    assert ".mult-panel.folded .mwhy, .mult-panel.folded .mgroup { display: none; }" in CSS
    seg = _fn("loadMultipliers")
    assert 'class="mfold ghost"' in seg and "_multFolded(" in seg and "_multGutter()" in seg
    assert '"pid.mult.fold"' in JS
    split = JS.split('const SPLIT_KEY = "pid.split";', 1)[1]
    assert '_dragGutter(gm, "row"' in split and "share - 120" in split
    assert "g === gm ? { ...state, mult: null }" in split
    assert 'if (v.mult) { mp.style.height' in split


def test_from_to_is_typed_or_marked_and_saving_does_not_redraw_everything():
    blk = _fn("descMarkupBlock")
    assert 'id="dm-${k}-in"' in blk and 'id="dm-who"' in blk and 'id="dm-apply"' in blk
    save = JS.split("async function _ftSave(", 1)[1].split("\nasync function ", 1)[0]
    # 목록 전부 · 오버레이 전부 · 근거 패널 전부를 다시 그리지 않는다
    assert "renderGrid()" not in save and "drawOverlay()" not in save and "showEvidence(" not in save
    assert "_paintDescCells(row)" in save and "_redrawFromTo()" in save and "refreshDescMarkup(row)" in save
    assert "via_from: st.from_via" in save and "via_to: st.to_via" in save
    # 버튼을 누르는 것만으로 근거 패널 전부를 다시 그리지 않는다
    bind = _fn("bindDescMarkup")
    assert "showEvidence(" not in bind and "refreshDescMarkup(row)" in bind
    # 친 글자는 그은 범위가 아니다 — 범위 상자를 걷는다
    assert 'st[`${k}_via`] = "manual"; st[`${k}_rect`] = null;' in bind
    # 작성자 칸이 비어 있을 때만 이름 줄을 띄운다 — 이름을 지어내지 않는다
    who = JS.split("async function _ftAuthor(", 1)[1].split("\n}\n", 1)[0]
    assert "if (v) { rememberAuthor(v);" in who and "askAuthor(what, hint)" in who
    # From/To 판은 패널 위쪽 (수정 이력 아래가 아니다)
    ev = _fn("showEvidence")
    assert ev.index("descMarkupBlock(row)") < ev.index('"<dl>"')


def test_server_records_where_each_side_came_from():
    from app import main
    src = inspect.getsource(main.confirm_axis)
    assert '"직접 입력"' in src and '"마크업 범위"' in src
    assert 'payload.get("via_from") or via' in src and 'payload.get("via_to") or via' in src
    # 범위 상자는 그은 쪽에만 남는다 — 친 쪽에 옛 범위가 붙으면 도면이 거짓말을 한다
    assert 'from_rect=payload.get("from_rect") if source_from == "마크업 범위" else None' in src
    # 한 장만 연다 — 후보를 볼 때마다 PDF 전체를 열던 것(TC2 3.2초)
    page = inspect.getsource(main._axis_page)
    assert "only=(int(page_no),)" in page


def test_manual_side_is_saved_with_its_own_source(tmp_path, monkeypatch):
    """한 쪽은 긋고 한 쪽은 친다 — 출처가 쪽마다 따로 적힌다."""
    import asyncio, os
    os.environ["PID_DATA_DIR"] = str(tmp_path)
    for mod in [m for m in list(sys.modules) if m.startswith("app")]:
        del sys.modules[mod]
    from app import db, main
    db.create_job(main.CON, "j", "p.pdf", "sha", tmp_path / "p.pdf")
    db.store_result(main.CON, "j", {
        "pages": [], "layers": {}, "multipliers": {}, "legend": {}, "glyphs": {"letters": {}},
        "fingerprint": "f",
        "rows": [{"key": "k1", "tab": "FIELD", "page_no": 6, "rect": [0, 0, 1, 1], "drawing_no": "D",
                  "type": "PIT", "qty": 1, "system": "", "valve_type": "", "vendor_supply": "",
                  "scope": "SCT", "description": "", "tag_no": "", "needs_review": "",
                  "annotation": "", "evidence": {}}]})
    main.CON.commit()
    out = asyncio.run(main.confirm_axis("j", "k1", {
        "from_text": "FROM HRSG HP STEAM", "to_text": "TO HAND TYPED",
        "via": "markup", "via_from": "markup", "via_to": "manual", "author": "검증",
        "from_rect": [6, 1, 2, 3, 4], "to_rect": [6, 9, 9, 9, 9]}))
    assert out["source_from"] == "마크업 범위" and out["source_to"] == "직접 입력"
    assert out["sentence"] == "FROM HRSG HP STEAM TO HAND TYPED PRESSURE TRANSMITTER"
    fb = db.feedback_rows(main.CON, "j", limit=5)[0]
    assert fb["basis"].get("from_rect") == [6, 1, 2, 3, 4] and "to_rect" not in fb["basis"]
    assert fb["author"] == "검증"
    # 직접 입력은 한 쪽만으로도 된다
    one = asyncio.run(main.confirm_axis("j", "k1", {"from_text": "", "to_text": "TO X",
                                                     "via_from": "manual", "via_to": "manual"}))
    assert one["source_to"] == "직접 입력" and one["sentence"] == "TO X PRESSURE TRANSMITTER"


def _ls(anchor, y, scope="SCT", hits=(), meaning=""):
    from app import pipeline as P
    r = P.Row(key=anchor, tab="FIELD", page_no=6, drawing_no="D", type="LS", qty=1,
              scope=scope, vendor_supply=("VENDOR" if hits and hits[0] != "VENDOR_MARK_UNDEFINED"
                                          else "UNDEFINED" if hits else ""),
              rect=(100.0, y, 140.0, y + 12.0),
              description_needed=not (hits and hits[0] != "VENDOR_MARK_UNDEFINED"),
              description_note=("타사 공급 — Description 생략" if hits and hits[0] != "VENDOR_MARK_UNDEFINED" else ""),
              evidence={"anchor": anchor, "rules_hit": list(hits), "review_codes": [],
                        "detail": ({"vendor_mark": {"meaning": meaning}} if meaning else {})})
    return r


class _Isa:                          # 그 도면의 ISA 표가 L 을 변수로, S 를 SWITCH 로 읽는다
    first = {"L": ("LEVEL",)}
    succeeding = {"S": ("SWITCH",)}


def test_ls_bundle_follows_a_star_on_any_of_its_signals():
    """hotfix27 — LSHH·LSH·LSL 은 물리 LS 하나다.  별표가 LSL 옆에만 있어도 남는 행(LSHH)이 따른다."""
    from app import pipeline as P
    rows = [_ls("LSHH", 100.0), _ls("LSH", 112.0),
            _ls("LSL", 124.0, "VENDOR(HRSG)", ("VENDOR_MARK_GLYPH",), "* BY HRSG")]
    groups, folded = P._signal_groups(rows, _Isa())
    assert len(groups) == 1 and groups[0]["basis"]["scope_from"]["anchor"] == "LSL"
    top = rows[0]
    assert top.key not in folded
    assert top.scope == "VENDOR(HRSG)" and top.vendor_supply == "VENDOR"
    assert "VENDOR_MARK_GLYPH" in top.evidence["rules_hit"] and not top.description_needed
    assert top.evidence["bundle_scope"]["own_scope"] == "SCT"


def test_ls_bundle_without_any_star_stays_sct_and_undefined_is_flagged():
    from app import pipeline as P
    rows = [_ls("LSHH", 100.0), _ls("LSH", 112.0), _ls("LSL", 124.0)]
    P._signal_groups(rows, _Isa())
    assert rows[0].scope == "SCT" and "bundle_scope" not in rows[0].evidence
    rows = [_ls("LSHH", 100.0), _ls("LSH", 112.0, "VENDOR", ("VENDOR_MARK_UNDEFINED",)), _ls("LSL", 124.0)]
    P._signal_groups(rows, _Isa())
    # hotfix83 — 뜻 없는 별표는 사용자 확정으로 그냥 VENDOR 이고 검토 사유를 달지 않는다
    assert rows[0].scope == "VENDOR" and "VENDOR_MARK_UNDEFINED" not in rows[0].evidence.get("review_codes", [])
