"""기존 규칙 기반 기준선 — pid-instrument-tool/web/app.js 의 baseline() 을 그대로 옮겼다.

**규칙을 고치지 않았다.** 좁은 정규식과 빈 DESCRIPTION 까지 그대로 둔다.
고쳐서 옮기면 AI 와의 대조(D-5 감사 수확)가 거짓이 된다 —
규칙이 무엇을 놓치는지가 이 실험이 재려는 것이기 때문이다.

원본과 같은 것:
    TOKEN_TO_TYPE · NOT_FIELD (app.js 531~538)
    qtyFromNotes  'CONFIGURATION IS IDENTICAL FOR' 만 본다 (app.js 544~552)
    systemFromTitle  낱말 60% 이상 겹칠 때만 (app.js 555~564)
    describeHints  DESCRIPTION 을 짓지 않고 근거 라벨만 붙인다 (app.js 572~584)
"""

from __future__ import annotations

import re

import render
import schema as schema_mod

# app.js 531~537 과 같은 표. render.py 의 것과 다르다 — 원본을 그대로 옮긴다.
TOKEN_TO_TYPE = {
    "PT": "PIT", "TT": "TIT", "LT": "LIT", "FT": "FIT", "AT": "AIT",
    "PIT": "PIT", "TIT": "TIT", "LIT": "LIT", "FIT": "FIT", "AIT": "AIT",
    "PI": "PI", "TI": "TI", "LI": "LI", "FI": "FI",
    "PDIT": "PDIT", "PDI": "PDIT", "PDT": "PDIT",
    "FE": "FE", "RO": "RO", "LS": "LS", "FS": "FS", "PS": "PS", "TS": "TS",
}
NOT_FIELD = {"ZS", "ZSC", "ZSO", "HS", "XS"}

_QTY_RE = re.compile(r"CONFIGURATION IS IDENTICAL FOR\s+((?:GROUP|UNIT)?\s*#?\s*[\d,\s#]+)")


def qty_from_notes(notes: str) -> tuple[int, str]:
    flat = re.sub(r"\s+", " ", notes or "").upper()
    m = _QTY_RE.search(flat)
    if not m:
        return 1, "IDENTICAL FOR 노트 없음"
    others = len(re.findall(r"\d+", m.group(1)))
    if others:
        return others + 1, f"NOTES: IDENTICAL FOR ... 다른 호기 {others}개 → 이 도면 포함 {others + 1}"
    return 1, "IDENTICAL FOR 노트를 읽었지만 호기 번호를 못 찾음"


def system_from_title(title: str | None, systems: list[str]) -> str:
    t = re.sub(r"^P&ID FOR\s+", "", (title or "").upper())
    best, score = "", 0.0
    for s in systems or []:
        words = [w for w in s.upper().split() if len(w) > 2]
        if not words:
            continue
        hit = sum(1 for w in words if w in t) / len(words)
        if hit > score:
            score, best = hit, s
    return best if score >= 0.6 else ""


def describe_hints(scan: render.PageScan, c: dict) -> str:
    def near(kind: str, wx: float, wy: float):
        pool = [l for l in scan.labels if l["kind"] == kind]
        if not pool:
            return None
        return min(pool, key=lambda l: ((l["x"] - c["x"]) * wx) ** 2 + ((l["y"] - c["y"]) * wy) ** 2)

    eq = near("equip", 3, 1)   # 설비 박스는 세로 열로 서 있어 x 를 크게 본다
    ln = near("line", 1, 1.5)
    bits = [f"'{c['token']}' @ x={c['x']} y={c['y']}"]
    if eq:
        bits.append(f"설비 '{eq['t']}'")
    if ln:
        bits.append(f"배관 '{ln['t']}'")
    return " · ".join(bits)


def build(scan: render.PageScan, spec: schema_mod.Spec) -> dict:
    """API 없이 텍스트 레이어와 NOTES 만으로 만드는 기준선.

    DESCRIPTION 과 벤더 공급 범위 제외는 도면 그림을 봐야 하는 판단이라 채우지 않는다.
    """
    qty, why = qty_from_notes(scan.notes)
    system = system_from_title(scan.title, spec.systems)

    rows, excluded = [], []
    for c in scan.candidates:
        if c["token"] in NOT_FIELD:
            excluded.append({"token": c["token"], "location": f"x={c['x']},y={c['y']}",
                             "reason": "밸브 리밋스위치 계열이라 Field Instrument 범위 밖"})
            continue
        type_ = TOKEN_TO_TYPE.get(c["token"])
        if not type_:
            excluded.append({"token": c["token"], "location": f"x={c['x']},y={c['y']}",
                             "reason": "매핑에 없는 문자"})
            continue
        if type_ not in spec.instrument_types:
            excluded.append({"token": c["token"], "location": f"x={c['x']},y={c['y']}",
                             "reason": f"'{type_}' 는 출력 TYPE 목록 밖"})
            continue
        rows.append(schema_mod.normalize_row({
            "system": system, "pid_no": scan.drawing_no or "", "type": type_,
            "qty": str(qty), "description": "",       # 사람이 채울 칸
            "inst_typical_type": spec.top_typical(type_), "remark": "-",
            "rect": c["rect"],                        # 텍스트 레이어 좌표 — 결정적
            "source_tokens": describe_hints(scan, c), "confidence": "low",
        }, spec, scan.page))

    findings = [{
        "severity": "high", "location": scan.drawing_no or "",
        "finding": f"API 없이 만든 기준선입니다. 계기 {len(rows)}건의 SYSTEM · P&ID No. · TYPE · "
                   f"Q'ty · INST. TYPICAL TYPE 은 도면에서 결정적으로 읽어 채웠고, DESCRIPTION 은 비어 있습니다.",
        "recommendation": "DESCRIPTION 은 각 행의 근거 칸을 보고 사람이 씁니다.",
    }, {
        "severity": "high", "location": scan.drawing_no or "",
        "finding": f"Q'ty {qty} — {why}",
        "recommendation": "호기 공용 설비는 이 배수에서 빼고 1 로 고치세요.",
    }]
    if re.search(r"DENOTES|MARKED ITEM|SUPPLIED BY", scan.notes or "", re.I):
        lines = " / ".join(l for l in (scan.notes or "").split("\n")
                           if re.search(r"DENOTES|MARKED ITEM|SUPPLIED BY", l, re.I))
        findings.append({
            "severity": "high", "location": scan.drawing_no or "",
            "finding": f"이 도면에 공급 범위 각주가 있습니다 — {lines}",
            "recommendation": "도면에서 * / ** 표기가 붙은 계기를 찾아 목록에서 지우세요. "
                              "기준선은 표기를 못 읽으므로 그 계기들이 아직 남아 있습니다.",
        })
    if not system:
        findings.append({
            "severity": "medium", "location": scan.drawing_no or "",
            "finding": f"제목('{scan.title or '—'}')이 템플릿 SYSTEM 목록과 맞지 않아 SYSTEM 을 비웠습니다.",
            "recommendation": "검토 UI 에서 SYSTEM 을 골라 주세요.",
        })

    return {
        "rows": rows, "excluded": excluded, "review_findings": findings,
        "qty_basis": why,
        "page_summary": f"API 없이 만든 기준선 — 후보 {len(scan.candidates)}건 중 {len(rows)}건을 행으로, "
                        f"{len(excluded)}건 제외. Q'ty {qty}. DESCRIPTION 은 비어 있습니다.",
    }
