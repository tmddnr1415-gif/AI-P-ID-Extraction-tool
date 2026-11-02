"""Korean wording of the tool's comments (valve31 — user: "코멘트도 한글과 영어로, PDF/Excel 은 선택해서").

    ko(text) -> Korean text, or None when the sentence is not a tool template (then the English stays alone)

Deterministic: every rule writes its comment from a fixed English template, so each template has a fixed Korean
template here (regular expressions — no machine translation, no LLM).  Technical words stay as engineers write them
(field labels · materials · standards · document numbers · values in quotes).  The judging code never imports this
module: it only changes how a finished finding is shown or printed.
"""
from __future__ import annotations

import re

Q = r"'(.*?)'"                                   # a quoted value

# "Based on Ref. Process Data CO2S-… (p.12) fluid 'CO2', design press. 30 barg" → "Ref. Process Data CO2S-… (p.12) 유체 'CO2', 설계 압력 30 barg 기준"
_BASIS_WORDS = [(r"\bdesign press\.", "설계 압력"), (r"\bdesign temp\.", "설계 온도"), (r"\boperating temp\.", "운전 온도"),
                (r"\boperating press\.", "운전 압력"), (r"\bfluid phase\b", "유체 상(phase)"), (r"\bfluid\b", "유체")]


def _basis(s: str) -> str:
    s = re.sub(r"^Based on\s+", "", s.strip())
    for a, b in _BASIS_WORDS:
        s = re.sub(a, b, s)
    return s + " 기준"


def _b(m, i=1):
    return _basis(m.group(i))


# (pattern on the whole text, Korean) — first match wins.  \1 … in the Korean are the pattern's groups.
RULES: list[tuple[str, object]] = [
    # ── Data Missing / Open Item / Data Error (issues.py) ─────────────────────────────────────────
    (r"^(.+?): no value( \(Max/Nor/Min\))?; ref\. (\S+) \((Gen\. )?Note (\S+)\)\. Provide value\.$",
     lambda m: f"{m.group(1)}: 값 없음{m.group(2) or ''} — 참조 {m.group(3)} ({'일반 ' if m.group(4) else ''}Note {m.group(5)}). 값을 기입 바랍니다."),
    (r"^(.+?): no value( \(Max/Nor/Min\))?\. Provide value\.$", lambda m: f"{m.group(1)}: 값 없음{m.group(2) or ''}. 값을 기입 바랍니다."),
    (r"^(.+?): no value( \(Max/Nor/Min\))?(.*)$", lambda m: f"{m.group(1)}: 값 없음{m.group(2) or ''}{m.group(3)}"),
    (rf"^{Q} on HOLD/TBC\. Release and give value\.$", r"'\1' 이(가) HOLD/TBC 상태입니다. 확정 값을 기입 바랍니다."),
    (rf"^(HOLD|Note) (\S+) {Q} on HOLD/TBC\. Release and confirm\.$", r"\1 \2 '\3' 이(가) HOLD/TBC 상태입니다. 확정 바랍니다."),
    (rf"^Class in Line No\. {Q} differs from Piping class {Q}$", r"Line No. 의 Class '\1' 이(가) Piping class '\2' 와 다릅니다."),
    (r"^Referenced General Note (\S+) does not exist in (\S+)$", r"참조한 General Note \1 이(가) \2 에 없습니다."),
    (r"^Referenced Note (\S+) does not exist on this datasheet$", r"참조한 Note \1 이(가) 이 데이터시트에 없습니다."),
    (rf"^Refers to Note (\S+) \({Q}\); should be Note (\S+) \({Q}\)\.$", r"Note \1 ('\2') 을(를) 참조하고 있으나 Note \3 ('\4') 이(가) 맞습니다."),
    (rf"^(.+?) on p\.(\d+) is {Q} — sheet (\d+) says {Q}$", r"p.\2 의 \1 이(가) '\3' — sheet \4 에는 '\5'."),
    (rf"^Label/value pairing of {Q} could not be settled by the tool — check$", r"'\1' 의 항목-값 짝을 도구가 확정하지 못했습니다 — 확인 필요"),
    (rf"^(Modified|Added|Deleted): {Q} → {Q}$", lambda m: f"{ {'Modified': '변경', 'Added': '추가', 'Deleted': '삭제'}[m.group(1)]}: '{m.group(2)}' → '{m.group(3)}'"),
    # ── Process Data (process.py reasons, prefixed with the item label) ───────────────────────────────
    (rf"^(.+?): Datasheet {Q} vs Process Data {Q}(.*)$", lambda m: f"{m.group(1)}: Datasheet '{m.group(2)}' ↔ Process Data '{m.group(3)}' 불일치{_ref(m.group(4))}"),
    (rf"^(.+?): Partly the same words: Datasheet {Q} vs Process Data {Q}(.*)$",
     lambda m: f"{m.group(1)}: 일부 단어만 같음 — Datasheet '{m.group(2)}' ↔ Process Data '{m.group(3)}'{_ref(m.group(4))}"),
    (rf"^(.+?): Same line number; only the class qualifier differs \(Datasheet {Q} vs Process Data {Q}\)(.*)$",
     lambda m: f"{m.group(1)}: Line 번호는 같고 Class 표기만 다름 (Datasheet '{m.group(2)}' ↔ Process Data '{m.group(3)}'){_ref(m.group(4))}"),
    (rf"^(.+?): Not a number on one side: Datasheet {Q} vs Process Data {Q}(.*)$",
     lambda m: f"{m.group(1)}: 한쪽이 숫자가 아님 — Datasheet '{m.group(2)}' ↔ Process Data '{m.group(3)}'{_ref(m.group(4))}"),
    (rf"^(.+?): Different basis: {Q} vs {Q} \(no atmospheric correction made\)(.*)$",
     lambda m: f"{m.group(1)}: 기준이 다름 '{m.group(2)}' ↔ '{m.group(3)}' (대기압 보정 안 함){_ref(m.group(4))}"),
    (rf"^(.+?): (?:Flow unit differs or unclear|Unit differs) \({Q} vs {Q}\)(.*)$",
     lambda m: f"{m.group(1)}: 단위가 다르거나 불명확 ('{m.group(2)}' ↔ '{m.group(3)}'){_ref(m.group(4))}"),
    (r"^(.+?): Datasheet fail (\w+), Process Data (\S+) \((.*?)\)(.*)$",
     lambda m: f"{m.group(1)}: Datasheet fail {m.group(2)} ↔ Process Data {m.group(3)} ({m.group(4)}) 불일치{_ref(m.group(5))}"),
    # ── PMS (pms.py / material.py reasons, with ' (Class X)' at the end) ───────────────────────────────
    (r"^(.+?): (.+) \(Class ([^)]+)\)$", lambda m: _pms(m)),
    # ── Material review (matreview.py) ───────────────────────────────────────────────────────────────
    (r"^CS body in CO2 service \((.*?)\)\. Confirm dry CO2 or use SS\.$", lambda m: f"CO2 서비스에 CS body ({m.group(1).replace('no CA', 'CA 없음')}). 건조 CO2 인지 확인하거나 SS 로 변경 바랍니다."),
    (r"^CS body in sour service: max\. 22 HRC, welds max\. 250 HV10, NACE certified\.$", "Sour 서비스의 CS body: 최대 22 HRC, 용접부 최대 250 HV10, NACE 인증 필요."),
    (r"^17-4PH stem: state (\S+), max\. (\d+) HRC \((.*?)\)\.$", r"17-4PH stem: \1 열처리 · 최대 \2 HRC 를 명기 바랍니다 (\3)."),
    (r"^17-4PH stem: state heat treatment\.$", "17-4PH stem: 열처리 조건을 명기 바랍니다."),
    (r"^State hard-facing type and thickness \(e\.g\. (.*?)\)\.$", r"Hard-facing 종류와 두께를 명기 바랍니다 (예: \1)."),
    (r"^Submit API 607 / ISO 10497 fire test certificate covering size and class\.$", "해당 Size · Class 를 포함하는 API 607 / ISO 10497 fire test 인증서를 제출 바랍니다."),
    (r"^(Based on .+?), seat (\S+) \(limit (\S+) °C, PMS (\S+) Note (\S+)\) shall be reviewed\.$",
     lambda m: f"{_b(m)}, seat {m.group(2)} (한계 {m.group(3)} °C, PMS {m.group(4)} Note {m.group(5)}) 검토 바랍니다."),
    (r"^(Based on .+?), exceeds PMS (\S+) max\. (\S+) °C\. Confirm piping class / design temp\.$",
     lambda m: f"{_b(m)}, PMS {m.group(2)} 최대 {m.group(3)} °C 초과. Piping class / 설계 온도를 확인 바랍니다."),
    (r"^Body (.+?) not suitable for low-temp\. line\. Use (.*?) \(impact tested\)\.$", r"Body \1 은(는) 저온 라인에 부적합. \2 (충격시험) 사용 바랍니다."),
    (r"^Body (.+?) vs pipe (.+?): different material\. Confirm\.$", r"Body \1 ↔ 배관 \2: 재질이 다릅니다. 확인 바랍니다."),
    (r"^316/316L in sour service: confirm within ISO 15156-3 limits\.$", "Sour 서비스의 316/316L: ISO 15156-3 한계 이내인지 확인 바랍니다."),
    (r"^B8M CL\.2 bolting not acceptable if exposed \(ISO 15156\)\. Confirm non-exposed or use B8M CL\.1 / B7M\.$",
     "B8M CL.2 볼트는 노출 시 불가 (ISO 15156). 비노출 확인 또는 B8M CL.1 / B7M 사용 바랍니다."),
    (r"^State seal / O-ring materials, RGD qualified \((.*?)\)\.$", r"Seal / O-ring 재질과 RGD 인증 여부를 명기 바랍니다 (\1)."),
    (r"^(Based on .+?): not in PMS (\S+) service list\. Confirm piping class\.$",
     lambda m: f"{_b(m)}: PMS {m.group(2)} 서비스 목록에 없음. Piping class 를 확인 바랍니다."),
    (r"^(Based on .+?), seat (\S+) \(typ\. max\. (\S+) °C\) shall be reviewed or P-T curve submitted\.$",
     lambda m: f"{_b(m)}, seat {m.group(2)} (통상 최대 {m.group(3)} °C) 검토 또는 P-T curve 제출 바랍니다."),
    (r"^PMS (\S+) Note (\S+): dual-grade 316/316L required\. Material shall be reviewed\.$", r"PMS \1 Note \2: dual-grade 316/316L 요구. 재질 검토 바랍니다."),
    (r"^(\S+) bolting in NACE service: use (\S+) \(max\. (\d+) HRC\) if exposed\.$", r"NACE 서비스의 \1 볼트: 노출 시 \2 (최대 \3 HRC) 사용 바랍니다."),
    (r"^(Based on .+?), close to (\S+) seat limit \(~(\S+) °C\)\. Submit seat P-T curve\.$",
     lambda m: f"{_b(m)}, {m.group(2)} seat 한계(약 {m.group(3)} °C)에 근접. Seat P-T curve 제출 바랍니다."),
    (r"^(Based on .+?), exceeds PMS (\S+) rating (\S+) barg\. Confirm\.$", lambda m: f"{_b(m)}, PMS {m.group(2)} 정격 {m.group(3)} barg 초과. 확인 바랍니다."),
    (r"^B7M/L7M bolting: acceptable for sour service\.$", "B7M/L7M 볼트: Sour 서비스에 적합."),
    # ── Valve design / accessories (expert.py) ─────────────────────────────────────────────────────
    (r"^Flange facing (.+?); PMS (\S+) requires (.+?)\. Flange facing shall be reviewed\.$", r"Flange facing \1; PMS \2 는 \3 요구. Flange facing 검토 바랍니다."),
    (r"^(.+?) valve: flanges to ASME B16\.5, not B16\.47\. Flange standard shall be reviewed\.$", r"\1 밸브: 플랜지는 ASME B16.47 이 아니라 B16.5. 플랜지 규격 검토 바랍니다."),
    (r"^(.+?) valve: flanges to ASME B16\.47 Series A/B\. State series\.$", r"\1 밸브: ASME B16.47 Series A/B 중 어느 것인지 명기 바랍니다."),
    (r"^Floating ball (.+?) Class (\S+): confirm torque / design or use trunnion\.$", r"Floating ball \1 Class \2: 토크 / 설계 확인 또는 trunnion 사용 바랍니다."),
    (r"^Fail (.+?) requires spring-return actuator\. Actuator type shall be reviewed\.$", r"Fail \1 은(는) spring-return 액추에이터 필요. 액추에이터 형식 검토 바랍니다."),
    (r"^Fail last with spring specified\. Confirm fail action\.$", "Fail last 인데 spring 이 지정됨. Fail 동작 확인 바랍니다."),
    (r"^(.+?) with fail last\. Confirm fail-safe position\.$", r"\1 인데 fail last. Fail-safe 위치 확인 바랍니다."),
    (r"^(.+?): confirm PST requirement and SIL certificate\.$", r"\1: PST 요구 여부와 SIL 인증서 확인 바랍니다."),
    (r"^Soft seat with (.+?)\. Confirm Rate A\.$", r"Soft seat 인데 \1. Rate A 확인 바랍니다."),
    (r"^TSO specified but (.+?)\. Confirm Rate A\.$", r"TSO 지정인데 \1. Rate A 확인 바랍니다."),
    (r"^State (.+?) \(API 6D / ISO 17292\)\.$", r"\1 명기 바랍니다 (API 6D / ISO 17292)."),
    (r"^(.+?): fire-safe \(API 607\) not stated on datasheet\. State it\.$", lambda m: f"{_why(m.group(1))}: 데이터시트에 fire-safe (API 607) 표기가 없습니다. 명기 바랍니다."),
    (r"^(Based on .+?): state seat design \(SPE/DPE\) and cavity relief\.$", lambda m: f"{_b(m)}: Seat 설계(SPE/DPE)와 cavity relief 를 명기 바랍니다."),
    (r"^(Based on .+?): (.+)$", lambda m: f"{_b(m)}: {ko(m.group(2)) or m.group(2)}"),
    (r"^Cold insulation: specify extended stem / bonnet\.$", "보냉(Cold insulation): extended stem / bonnet 을 명기 바랍니다."),
    (r"^Piggable line: reduced bore not acceptable, use full bore\.$", "Pigging 라인: reduced bore 불가, full bore 사용 바랍니다."),
    (r"^Piggable line: state full bore\.$", "Pigging 라인: full bore 명기 바랍니다."),
    (r"^Valve (.+?) larger than line (.+?)\. Valve size shall be reviewed\.$", r"밸브 \1 이(가) 라인 \2 보다 큽니다. 밸브 Size 검토 바랍니다."),
    (r"^Full-bore valve (.+?) in (.+?) line\. Confirm size\.$", r"\2 라인에 full-bore 밸브 \1. Size 확인 바랍니다."),
    (r"^Erosive service with soft seat (.+?)\. Consider metal seat\.$", r"Erosive 서비스에 soft seat \1. Metal seat 검토 바랍니다."),
    (r"^Actuator safety factor (\S+) below 1\.25\. Confirm\.$", r"액추에이터 안전율 \1 이(가) 1.25 미만. 확인 바랍니다."),
    (r"^(\S+) specified; PMS item (\S+) is (\w+)\. Align with PMS\.$", r"\1 지정; PMS 품목 \2 은(는) \3. PMS 와 맞춰 바랍니다."),
    (rf"^{Q} differs from (\d+)/(\d+) (\S+) datasheets \({Q}\)\. Confirm\.$", r"'\1' 이(가) 같은 \4 데이터시트 \3개 중 \2개('\5')와 다릅니다. 확인 바랍니다."),
    (rf"^(\S+) tag with fail position {Q}\. Confirm tag or fail action\.$", r"\1 Tag 인데 fail 위치 '\2'. Tag 또는 fail 동작 확인 바랍니다."),
    (rf"^Limit switch {Q} specified; General Note (\S+) says limit switches shall not be used\. Shall be reviewed\.$",
     r"Limit switch '\1' 지정 — General Note \2 는 limit switch 사용 금지. 검토 바랍니다."),
    (r"^(.+?) valve: position transmitter SIL rating shall be confirmed \(General Note (\S+)\)\.$", r"\1 밸브: Position transmitter 의 SIL 등급 확인 바랍니다 (General Note \2)."),
    (r"^(\d+) SOVs \((.*?)\): voting \(1oo2 / 2oo2 / 2oo3\) and online test arrangement shall be stated\.$",
     r"SOV \1개 (\2): 표결 방식(1oo2 / 2oo2 / 2oo3)과 온라인 시험 구성을 명기 바랍니다."),
    (r"^No position transmitter on the datasheet; General Note (\S+) requires one for (\S+)\. Shall be reviewed\.$",
     r"데이터시트에 Position transmitter 가 없음 — General Note \1 은 \2 에 요구. 검토 바랍니다."),
    (r"^Positioner in Note (\S+) is not the Fisher DVC required by General Note (\S+)\. Shall be reviewed\.$",
     r"Note \1 의 Positioner 가 General Note \2 이 요구하는 Fisher DVC 가 아님. 검토 바랍니다."),
    (r"^PMS item is fire tested: fire-safe \(API 607\) not stated on datasheet\. State it\.$", "PMS 품목은 fire tested: 데이터시트에 fire-safe (API 607) 표기가 없습니다. 명기 바랍니다."),
    # ── Tag rules (tagrules.py) ────────────────────────────────────────────────────────────────────
    (r"^The tag cannot be split into prefix \(system/unit\) \+ function code \+ loop number \(\+ suffix\) like the other tags\.$",
     "이 Tag 는 다른 Tag 처럼 prefix(시스템/유닛) + 기능 코드 + loop 번호(+ suffix)로 나뉘지 않습니다."),
    (r"^The tag (\S+) appears in documents (.+?): two valves must not share a tag \(or the same valve is specified twice\)\.$",
     r"Tag \1 이(가) 문서 \2 에 함께 있음: 두 밸브가 한 Tag 를 쓰면 안 됩니다 (또는 같은 밸브가 두 번 작성됨)."),
    (r"^In (.+?) Unit (\S+) the tag prefix is the (.+?) \((.+?) tags\); here it is (\S+) while the (.+?) is (\S+)\.$",
     r"\1 Unit \2 의 Tag prefix 는 \3 (Tag \4 개에서 학습); 이 Tag 는 \5, \6 는 \7."),
    (r"^Tags of (.+?) Unit (\S+) use (\d+)-digit numbers(?: starting '(.*?)')? \((.*?)\); this tag's number is (\S+)\.$",
     lambda m: f"{m.group(1)} Unit {m.group(2)} 의 Tag 는 {m.group(3)}자리 번호" + (f" ('{m.group(4)}' 로 시작)" if m.group(4) else "")
     + f" ({m.group(5)}); 이 Tag 번호는 {m.group(6)}."),
    (rf"^(.+?) \((\S+)\) normally fails closed; this datasheet says {Q}\. Either the tag function or the fail position is wrong\.$",
     r"\1 (\2) 은(는) 보통 fail close; 이 데이터시트는 '\3'. Tag 기능 또는 fail 위치가 틀렸습니다."),
    (rf"^(.+?) \((\S+)\) normally fails open \(depressurises on ESD\); this datasheet says {Q}\.$",
     r"\1 (\2) 은(는) 보통 fail open (ESD 시 감압); 이 데이터시트는 '\3'."),
]

_PMS = [  # body of a PMS row reason (pms.py · material.py)
    (rf"^Piping class {Q} not in PMS (\S+) area but found in (\S+) — please confirm$", r"Piping class '\1' 이(가) PMS \2 지역에는 없고 \3 에 있음 — 확인 바랍니다"),
    (rf"^Piping class {Q} is not defined in PMS ?(.*)$", lambda m: f"Piping class '{m.group(1)}' 이(가) PMS{(' ' + m.group(2)) if m.group(2) else ''} 에 없습니다"),
    (rf"^Piping class {Q} not in PMS; used \((\S+)\) from Line No\. — please confirm$", r"Piping class '\1' 이(가) PMS 에 없어 Line No. 의 (\2) 를 사용 — 확인 바랍니다"),
    (rf"^Piping class {Q} not in PMS; matched {Q} — please confirm$", r"Piping class '\1' 이(가) PMS 에 없어 '\2' 로 대응 — 확인 바랍니다"),
    (r"^Datasheet fire-safe is on HOLD / TBC — PMS item requires fire test$", "데이터시트 fire-safe 가 HOLD / TBC — PMS 품목은 fire test 요구"),
    (r"^PMS item requires fire test$", "PMS 품목은 fire test 요구"),
    (r'^PMS ball valve for (.+?) in class (\S+) is (\w+) PORT \(item (\S+), (.+?)\) — datasheet says (\w+) BORE; confirm the deviation(?: \((\w+) PORT only as another valve type, e\.g\. DBB\))?$',
     lambda m: f"Class {m.group(2)} 의 {m.group(1)} 일반 볼밸브는 {m.group(3)} PORT (품목 {m.group(4)}, {m.group(5)}) — 데이터시트는 {m.group(6)} BORE; 차이를 확인 바랍니다"
     + (f" ({m.group(7)} PORT 는 DBB 등 다른 밸브 종류에만 있음)" if m.group(7) else "")),
    (r"^No PMS item with this bore for this size$", "이 Size 에 이 bore 의 PMS 품목 없음"),
    (r'^No ball valve item for size (.+?) in class (\S+)$', r"Class \2 에 Size \1 볼밸브 품목 없음"),
    (r"^Datasheet rating not readable$", "데이터시트 rating 을 읽을 수 없음"),
    (r"^PMS class (\S+) is CLASS (\d+)$", r"PMS class \1 은(는) CLASS \2"),
    (r"^Datasheet says N/A but the PMS class requires NACE — confirm$", "데이터시트는 N/A 이나 PMS class 는 NACE 요구 — 확인 바랍니다"),
    (r"^PMS class requires NACE$", "PMS class 는 NACE 요구"),
    (rf"^Datasheet value is {Q} — nothing to verify(.*)$", lambda m: f"데이터시트 값이 '{m.group(1)}' — 비교할 값이 없음{_item(m.group(2))}"),
    (r"^Grade matches but required (.+?) not stated(.*)$", lambda m: f"Grade 는 같으나 요구 {m.group(1)} 표기 없음{_item(m.group(2))}"),
    (r"^Different material: required (.+?), datasheet (.+?)(\s·.*)?$", lambda m: f"재질 다름: 요구 {m.group(1)}, 데이터시트 {m.group(2)}{_item(m.group(3) or '')}"),
    (r"^Same family, different type: required (.+?), datasheet (.+?)(\s·.*)?$", lambda m: f"같은 계열, 다른 종류: 요구 {m.group(1)}, 데이터시트 {m.group(2)}{_item(m.group(3) or '')}"),
    (rf"^Cannot decide automatically: required {Q}, datasheet {Q}$", r"자동 판정 불가: 요구 '\1', 데이터시트 '\2'"),
    (r"^Datasheet note (\S+) requires NACE$", r"데이터시트 Note \1 이(가) NACE 요구"),
]


def _item(tail: str) -> str:
    tail = (tail or "").strip()
    return "" if not tail else " " + re.sub(r"^·\s*PMS item", "· PMS 품목", re.sub(r"^· PMS class header trim", "· PMS class 머리 trim", tail))


def _ref(tail: str) -> str:
    t = (tail or "").strip()
    return "" if not t else " " + t.replace("(Ref. ", "(참조: ")


def _why(s: str) -> str:
    return _basis(s) if s.startswith("Based on") else ("PMS 품목은 fire tested" if s == "PMS item is fire tested" else s)


def _pms(m) -> str | None:
    label, body, cls = m.group(1), m.group(2), m.group(3)
    for pat, rep in _PMS:
        mm = re.match(pat, body)
        if mm:
            body_ko = rep(mm) if callable(rep) else mm.expand(rep)
            return f"{label}: {body_ko}" + ("" if f"Class {cls}" in body_ko else f" (Class {cls})")
    return None


_COMPILED = [(re.compile(p, re.S), r) for p, r in RULES]


def ko(text: str | None) -> str | None:
    """Korean of a tool comment; None when the text is not one of the tool's templates (a reviewer's own words)."""
    if not text:
        return None
    t = str(text).strip()
    for pat, rep in _COMPILED:
        m = pat.match(t)
        if m:
            out = rep(m) if callable(rep) else m.expand(rep)
            if out:
                return out
    return None


def pick(en: str | None, kr: str | None, lang: str) -> str:
    """The text an export prints: 'en' · 'ko' (English when there is no Korean) · 'both' (English, then Korean)."""
    en = en or ""
    if lang == "ko":
        return kr or en
    if lang == "both" and kr and kr != en:
        return f"{en}\n{kr}"
    return en


def attach(issues: list[dict]) -> list[dict]:
    """Add description_ko to tool findings (not to reviewer comments or an engineer's edited wording)."""
    for i in issues or []:
        if i.get("comment_id") or i.get("edited") or i.get("type") == "Reviewer Comment":
            continue
        k = ko(i.get("description"))
        if k:
            i["description_ko"] = k
    return issues
