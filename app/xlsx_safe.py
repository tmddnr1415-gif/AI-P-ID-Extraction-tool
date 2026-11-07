"""hotfix133 — 내보내는 엑셀 칸을 안전하게 (Anthropic xlsx 스킬의 '수식 오류 0' 규칙을 우리 내보내기에 맞춘 것).

두 가지를 막는다:
1. **글이 수식이 되는 일** — openpyxl 은 `=` 로 시작하는 글을 수식으로 쓴다.  도면 글자 · 사람이 적은 의견이
   `=` 로 시작하면 엑셀이 계산하려 들어 `#NAME?` 이 되거나, 남이 넣은 `=HYPERLINK(...)` 같은 수식이 열 때 실행된다.
   우리가 만드는 시트에는 의도한 수식이 하나도 없으므로 **글 그대로(문자열)** 쓴다.  보이는 글은 바뀌지 않는다.
2. **보이지 않는 제어 문자로 내보내기가 멈추는 일** — PDF 에서 온 글에 `\\x01` 같은 문자가 섞이면 openpyxl 이
   IllegalCharacterError 를 올려 엑셀 전체가 실패했다.  그 문자만 뺀다 (눈에 보이는 글자는 그대로).

발주처 양식(템플릿)에 원래 들어 있는 수식은 건드리지 않는다 — 우리가 쓰는 칸에만 쓴다(`put`).
"""

from __future__ import annotations

import re

# openpyxl.cell.cell.ILLEGAL_CHARACTERS_RE 와 같은 정의 — 여기서 openpyxl 을 불러오지 않으려고 (화면 모듈의 늦은 불러오기를 지킨다)
ILLEGAL_CHARACTERS_RE = re.compile(r"[\000-\010]|[\013-\014]|[\016-\037]")


def text(v):
    """칸에 넣을 값 — 글이면 제어 문자를 뺀다.  글이 아니면 그대로."""
    return ILLEGAL_CHARACTERS_RE.sub("", v) if isinstance(v, str) else v


def _as_text(cell) -> None:
    if cell.data_type == "f" and isinstance(cell.value, str):
        cell.data_type = "s"


def put(cell, v) -> None:
    """한 칸에 쓴다 (`cell.value = v` 대신)."""
    cell.value = text(v)
    _as_text(cell)


def append(ws, row) -> None:
    """한 줄을 덧붙인다 (`ws.append(row)` 대신)."""
    ws.append([text(v) for v in row])
    for cell in ws[ws.max_row]:
        _as_text(cell)
