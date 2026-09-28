"""hotfix19 — 발주처 몫만 적은 프로필을 얹어도 도면 기하는 **그 도면이** 답한다.

현장: SADARA 45장이 `TitleBlockUnreadable` 로 멈췄다.  56회차 [G1] 이
`project_sadara.yaml`(도면번호 코드 1A46 · 기하 없음)을 AL NOUF1 **위에 얹었고**,
`_fit_layout` 이 병합된 `CFG.data` 로 "이 프로필이 도면 영역을 적었나" 를 물어
AL NOUF1 의 도면번호 칸으로 읽었다.  답은 파일이 적은 잎(`CFG.states`)이다.
"""
import types

from app import pipeline as P


class _FakeLayout:
    def __init__(self, vals):
        self._v = vals

    def values(self):
        return dict(self._v)

    def as_dict(self):
        return {"items": dict(self._v)}


def test_client_only_profile_that_matches_still_takes_the_sheets_geometry(tmp_path, monkeypatch):
    prof = tmp_path / "project_probe.yaml"
    prof.write_text("project:\n  code: 'ZZ99'\n  name: probe\n", encoding="utf-8")
    measured = {"regions.drawing_area": [10.0, 10.0, 900.0, 700.0],
                "title_block.dwg_no_region": [700.0, 650.0, 890.0, 690.0]}
    monkeypatch.setattr(P.derive_layout, "derive", lambda pages, cfg: _FakeLayout(measured))
    monkeypatch.setattr(P, "_document_code", lambda pages: "ZZ99")
    monkeypatch.setattr(P, "_reconfigure", lambda pages: None)
    with P._own_config():
        # 얹기 전: 바탕(AL NOUF1)은 도면 영역을 **데이터로** 갖고 있다
        assert P._configured("regions.drawing_area")
        P._switch_profile(prof)
        assert P._configured("regions.drawing_area")          # 병합본에는 여전히 있다
        assert not P.CFG.states("regions.drawing_area")        # 그러나 이 파일은 적지 않았다
        out = P._fit_layout([types.SimpleNamespace()])
        assert "states no geometry" in out["reason"]
        assert P.CFG.get("title_block.dwg_no_region") == measured["title_block.dwg_no_region"]
        moved = {m["key"] for m in out["moved"]}
        assert {"regions.drawing_area", "title_block.dwg_no_region"} <= moved
    # 되돌린 뒤에는 바탕의 값
    assert P.CFG.get("title_block.dwg_no_region") != measured["title_block.dwg_no_region"]


def test_own_profile_that_states_geometry_is_left_alone(monkeypatch):
    """AL NOUF1 — 자기 프로필이 기하를 적었으면 재기만 하고 얹지 않는다 (지문 불변의 이유)."""
    code = str(P.CFG.data["project"]["code"])
    monkeypatch.setattr(P.derive_layout, "derive",
                        lambda pages, cfg: _FakeLayout({"title_block.dwg_no_region": [1, 2, 3, 4]}))
    monkeypatch.setattr(P, "_document_code", lambda pages: code)
    monkeypatch.setattr(P, "_reconfigure", lambda pages: None)
    with P._own_config():
        before = P.CFG.get("title_block.dwg_no_region")
        out = P._fit_layout([types.SimpleNamespace()])
        assert out["moved"] == [] and P.CFG.get("title_block.dwg_no_region") == before


def test_fit_layout_asks_the_file_not_the_merged_data():
    import inspect
    src = inspect.getsource(P._fit_layout)
    assert 'CFG.states("regions.drawing_area")' in src and "not CFG.states(k)" in src
    assert "_configured(" not in src.split('"""', 2)[2]
