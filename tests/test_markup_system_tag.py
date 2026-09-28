"""hotfix14 — 마크업 추가 행의 SYSTEM · TAG 제안, 그리고 삭제의 붉은 표시.

SYSTEM 은 같은 장 추출 행이 받은 값을 그대로 옮긴다 (그 장 타이틀블록의 도면 제목).
TAG 는 사각형 안 코드 중 **그 문서의 태그 체계와 모양이 같은 것 하나** — 체계가 없는
문서에서는 채우지 않고, 둘 이상이면 고르지 않는다 (§9 ④).
"""
from pathlib import Path

from app import markup


class _Con:
    def __init__(self, title=""):
        self.title = title

    def execute(self, *_a):
        t = self.title

        class _Cur:
            def fetchone(self_):
                return {"title": t}
        return _Cur()


def _row(page, system="", tag="", added=0):
    return {"page_no": page, "added": added, "removed": 0, "deleted": 0,
            "ai": {"system": system, "tag_no": tag}}


def test_system_is_the_value_the_page_rows_carry(monkeypatch):
    rows = [_row(12, "P&ID FOR FUEL OIL"), _row(12, "P&ID FOR FUEL OIL"), _row(13, "OTHER")]
    monkeypatch.setattr(markup.db, "merged_rows", lambda con, j: rows)
    out = markup._system_from_page(_Con(), "j", 12)
    assert out["system"] == "P&ID FOR FUEL OIL" and out["system_source"] == "DRAWING"


def test_system_falls_back_to_page_title_then_blank(monkeypatch):
    monkeypatch.setattr(markup.db, "merged_rows", lambda con, j: [])
    assert markup._system_from_page(_Con("TITLE X"), "j", 3)["system"] == "TITLE X"
    blank = markup._system_from_page(_Con(""), "j", 3)
    assert blank["system"] == "" and blank["system_source"] == "USER"


def test_system_is_not_chosen_when_the_page_disagrees(monkeypatch):
    rows = [_row(5, "A"), _row(5, "B")]
    monkeypatch.setattr(markup.db, "merged_rows", lambda con, j: rows)
    assert markup._system_from_page(_Con("T"), "j", 5)["system"] == ""


def test_tag_uses_the_documents_own_tag_shape(monkeypatch):
    rows = [_row(1, tag="00EGD31CP501"), _row(1, tag="00GHB01CL001")]
    monkeypatch.setattr(markup.db, "merged_rows", lambda con, j: rows)
    words = [{"text": "PDIA+"}, {"text": "00EGD21CP001"}, {"text": "DN25"}]
    out = markup._tag_from_words(None, "j", words)
    assert out["tag_no"] == "00EGD21CP001" and out["tag_source"] == "DRAWING"


def test_tag_is_blank_without_a_tag_system_or_with_two_candidates(monkeypatch):
    monkeypatch.setattr(markup.db, "merged_rows", lambda con, j: [_row(1)])
    assert markup._tag_from_words(None, "j", [{"text": "00EGD21CP001"}])["tag_no"] == ""
    monkeypatch.setattr(markup.db, "merged_rows", lambda con, j: [_row(1, tag="00EGD31CP501")])
    two = markup._tag_from_words(None, "j", [{"text": "00EGD21CP001"}, {"text": "00EGD22CP001"}])
    assert two["tag_no"] == "" and len(two["tag_candidates"]) == 2


JS = (Path(__file__).resolve().parent.parent / "app/static/app.js").read_text(encoding="utf-8")


def test_delete_paths_share_one_helper_and_draw_red():
    assert JS.count("async function deleteRows(keys)") == 1
    assert "deleteRows(rows.map(r => r.key))" in JS            # 묶음 패널
    assert "deleteRows([row.key])" in JS                        # 근거 패널
    tb = JS.split('$req("#row-delete").addEventListener("click"', 1)[1].split("});", 1)[0]
    assert "deleteRows(keys)" in tb
    assert '"delstrike"' in JS and '"delring"' in JS
    assert '"삭제·오검출 (그중)", "#d70015"' in JS


def test_markup_elsewhere_takes_system_and_tag_from_that_page():
    seg = JS.split("다른 장에 남의", 1)[1].split("const r2 = await fetch", 1)[0]
    assert '["scope", "qty", "system", "tag_no"]' in seg and "prop.system" in seg
