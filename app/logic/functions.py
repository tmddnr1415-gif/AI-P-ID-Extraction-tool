"""기능 책 — 시뮬레이터가 아는 기능마다 범례가 정한 동작 한 줄 (`config/logic_functions.yaml` + `logic_analog.yaml`).

읽기만 한다.  화면 근거 패널 '동작 (범례)' · `/logic/api/functions` · `docs/logic_functions.md` 가 같은 사전을 읽는다.
"""
from __future__ import annotations

from functools import lru_cache

import yaml

from app import paths
from app.logic import aops


@lru_cache(maxsize=1)
def book() -> dict:
    p = paths.resource("config", "logic_functions.yaml")
    base = (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("functions") or {}
    out = {k: dict(v, key=k, kind="logic") for k, v in base.items()}
    v = aops.vocab()
    for group, kind in (("ops", "analog"), ("digital_ops", "digital")):
        for op, d in (v.get(group) or {}).items():
            out["aop:" + op] = {"key": "aop:" + op, "kind": kind, "ko": d.get("ko", op), "does": d.get("eq", ""),
                                "legend": " · ".join(str(n) for n in (d.get("names") or [])), "sim": d.get("sim", ""),
                                "in": "", "out": "값" if kind == "analog" else "1/0"}
    return out


def entry(logic: str = "", aop: str = "", param: dict | None = None) -> dict | None:
    """블록 하나의 책 항목 — 투표 부호 · 메모리 우선 칸을 문장에 넣어 돌려준다."""
    e = None
    if aop:
        e = book().get("aop:" + aop)
    if e is None and logic:
        e = book().get(logic)
    if e is None:
        return None
    e = dict(e)
    pr = param or {}
    if logic == "vote" and pr.get("a") is not None:
        op = pr.get("op", "ge")
        word = {"ge": "이상", "gt": "보다 많이", "le": "이하", "lt": "미만", "eq": "정확히", "ne": "가 아닐 때"}.get(op, "이상")
        e["does"] = f"{pr.get('b')}개 입력 중 1 인 것이 {pr.get('a')}개 {word}일 때 출력 1"
    if logic == "memory":
        dom = pr.get("dominant") or ""
        e["does"] = ("S=1 → Q=1 · R=1 → Q=0 · 둘 다 1 이면 " +
                     {"set": "Q=1 (SET 우선)", "reset": "Q=0 (RESET 우선)"}.get(dom, "상태가 한 번 바뀜 (기본)") + " · /Q 는 언제나 반대")
    return e


def markdown() -> str:
    """`docs/logic_functions.md` 의 본문 — 책을 표로."""
    b = book()
    lines = ["# LOGIC 기능 책 — 범례가 정한 동작", "",
             "`config/logic_functions.yaml` + `config/logic_analog.yaml` 에서 만든 표입니다 (`python -m app.logic.functions`).  "
             "화면 근거 패널의 '동작 (범례)' 줄과 같은 사전입니다.", "",
             "## 논리 기능", "", "| 기능 | 동작 | 범례 원문 | 시뮬레이터 메모 | 입력 → 출력 |", "| --- | --- | --- | --- | --- |"]
    for k, e in b.items():
        if e["kind"] == "logic":
            lines.append(f"| {e['ko']} (`{k}`) | {e['does']} | {e.get('legend', '')} | {e.get('sim', '')} | {e.get('in', '')} → {e.get('out', '')} |")
    lines += ["", "## 아날로그 · 비교 연산", "", "| 연산 | 식 | 범례 이름 |", "| --- | --- | --- |"]
    for k, e in b.items():
        if e["kind"] != "logic":
            lines.append(f"| {e['ko']} (`{k[4:]}`) | {e['does']} | {e.get('legend', '')} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    import sys
    out = paths.resource("docs", "logic_functions.md")
    out.write_text(markdown(), encoding="utf-8")
    print(out, len(book()), file=sys.stderr)
