"""L76 — 묶음 들여오기는 원본이 모양 게이트(막대+네모 · 막대+원 · ⊠ · 둥근 상자)로 그렸으면 같은 결의 양식(a5j)으로 옮긴다.

아미랄(19VA) 827장 실측: 기본 양식으로 옮기면 받기만 하는 경보 상자(선 없는 ANN)가 네모로 그려져 되읽기에서 신호 상자로
읽혔다 (블록 88.7%) → a5j 양식(둥근 ANN · 모양 게이트)으로 97.9%.
"""
from __future__ import annotations

from app.logic import draw_sets


def _res(keys_and_logic):
    return {"sheets": [{"page": 1, "blocks": {f"B{i}": {"key": k, "logic": lg, "read": r} for i, (k, lg, r) in enumerate(keys_and_logic)}}]}


def test_shape_gate_bundle_imports_in_shape_form():
    res = _res([("BAR_BOX|", "and", ""), ("BAR_CIRCLE|", "or", ""), ("CROSS_BOX|", "not", ""), ("ROUND_BOX|ANN", "sink", "ANN")])
    assert draw_sets.source_form(res) == "a5j"


def test_text_gate_bundle_keeps_default_form():
    res = _res([("", "and", "AND"), ("", "or", "OR"), ("", "not", "NOT"), ("BAR_BOX|", "and", "")])
    assert draw_sets.source_form(res) == ""
    assert draw_sets.source_form({"sheets": []}) == ""
