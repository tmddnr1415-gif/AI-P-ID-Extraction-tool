"""시트 이름 · 시트-행 참조의 꼴 — 한 곳에 둔다 (analyse · fromto · sim · 화면이 같은 꼴을 쓴다).

HRSG 묶음:  시트 `G031` · 참조 `G031-81`
19VA 묶음:  시트 `HH10_G144` (계통 접두 + 밑줄) · 참조 `GT11_G001-74` (L21)
둘 다 '글자 하나 + 숫자 셋' 이 시트의 몸이고(G = Logic · P = Loop 처럼 글자가 묶음의 종류), 앞에 계통 접두가 붙을 수 있다.
"""
from __future__ import annotations

import re

SHEET = r"(?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]\d{3}[A-Z]?"
SHEET_RE = re.compile(rf"^{SHEET}$")
REF = re.compile(rf"^({SHEET})-(\d{{1,3}})$")
REF_ANY = re.compile(rf"(?<![A-Z_])({SHEET})-(\d{{1,3}})(?!\d)")
# 시뮬레이션의 TO 따라가기는 묶음에 실제로 있는 시트 이름으로 거르므로 꼴을 넓게 받는다 (글자들 + 숫자들 — 예전 꼴 그대로)
TO_ANY = re.compile(r"(?<![A-Z_])((?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]+\d+[A-Z]?)-(\d+)(?!\d)")
_SERIES = re.compile(r"([A-Z])\d{3}[A-Z]?$")


def series(sheet_id: str) -> str:
    """시트 이름의 종류 글자 (G031 → G · HH10_P003 → P)."""
    m = _SERIES.search(sheet_id or "")
    if m:
        return m.group(1)
    m = re.search(r"([A-Z])[A-Z]*\d+[A-Z]?$", sheet_id or "")       # 예전 꼴 (G31 · B1) — 첫 글자
    return (sheet_id or "")[:1] if not m else re.sub(r"^(?:[A-Z][A-Z0-9]{0,5}_)", "", sheet_id)[:1]
