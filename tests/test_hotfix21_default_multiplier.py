"""hotfix21 — 승수를 가늠할 수 없으면 x1 로 센다 (사용자 확정 2026-09-28).

읽는 순서 ①범례 → ②NOTES → ③사람 → ④설정 폴백 → ⑤ **x1 + 사유**.  예전 ⑤ 는
빈칸이었고 Excel 이 0 으로 읽어 SADARA 45장 유닛 10 454행이 Q'ty 0 이었다.
사유(`MULTIPLIER_DEFAULT_ONE`)는 지우지 않는다 — 도면이 말한 값이 아니다.
"""
import inspect

from app import dxf_pipeline, main, pipeline as P
from app.engine import projectconfig


def test_unknown_multiplier_defaults_to_one_and_can_be_switched_off(monkeypatch):
    assert P.unknown_multiplier() == 1
    monkeypatch.setitem(P.CFG.data, "qty_note", {"unknown_multiplier": None})
    assert P.unknown_multiplier() is None
    assert P._default_multiplier(projectconfig.UNDEFINED, True) == (projectconfig.UNDEFINED, True, False)


def test_default_only_fills_what_nothing_else_answered():
    assert P._default_multiplier(projectconfig.UNDEFINED, True) == (1, False, True)
    assert P._default_multiplier(4, False) == (4, False, False)          # 범례·노트·사람·설정이 답함


def test_user_answer_still_wins_over_the_default():
    f, und, _b, _n, from_user = P._note_factor(projectconfig.UNDEFINED, True, False, None, user=3)
    assert (f, und, from_user) == (3, False, True)
    assert P._default_multiplier(f, und) == (3, False, False)


def test_every_row_builder_applies_the_rule_and_says_so():
    for fn in (P._field_rows, P._valve_rows):
        src = inspect.getsource(fn)
        assert "_default_multiplier(factor, undefined)" in src
        assert "DEFAULT_MULT_CODE" in src
    assert "P.unknown_multiplier()" in inspect.getsource(dxf_pipeline)
    assert "MULTIPLIER_DEFAULT_ONE" in main.REVIEW_LABELS
    assert "MULTIPLIER_DEFAULT_ONE" in inspect.getsource(main._multiplier_targets)


def test_review_axis_is_quantity_in_both_profiles():
    import yaml
    for name in ("project_alnouf1.yaml", "project_sadara.yaml"):
        data = yaml.safe_load(open(f"config/{name}", encoding="utf-8"))
        assert data["review_axes"]["codes"]["MULTIPLIER_DEFAULT_ONE"] == "QUANTITY"
