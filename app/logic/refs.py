"""시트 이름 · 시트-행 참조의 꼴 — 한 곳에 둔다 (analyse · fromto · sim · 화면이 같은 꼴을 쓴다).

HRSG 묶음:  시트 `G031` · 참조 `G031-81`
19VA 묶음:  시트 `HH10_G144` (계통 접두 + 밑줄) · 참조 `GT11_G001-74` (L21)
1A5J 묶음:  시트 `0016` · `FG_G-101` · 참조 `0016/72` · `FG_G-301-64` (L23)
1A1Y 묶음:  시트 `HR_G902` · 참조 `HR_G908/75` · 다른 문서 `HRSG_036/117` · `GT_G910/37` (L23)

L23 — 묶음마다 꼴이 다르다.  그래서 **옛 꼴을 먼저** 보고(HRSG · 19VA 는 한 글자도 안 바뀐다), 못 찾으면
일반 꼴 `<시트>[-/]<행>` 로 읽는다: 시트는 숫자가 하나 이상 든 글자·숫자·밑줄 덩어리(안에 `-` 허용),
행은 끝의 숫자 1~3자리.  시트가 이 묶음에 있는지는 부르는 쪽이 **그 묶음이 실제로 가진 시트 이름**으로 가른다
(`Bundle`) — 시트 이름의 모양을 코드에 외워두지 않는다.
"""
from __future__ import annotations

import functools
import re

SHEET = r"(?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]\d{3}[A-Z]?"
SHEET_RE = re.compile(rf"^{SHEET}$")
REF = re.compile(rf"^({SHEET})-(\d{{1,3}})$")
REF_ANY = re.compile(rf"(?<![A-Z_])({SHEET})-(\d{{1,3}})(?!\d)")
# 시뮬레이션의 TO 따라가기는 묶음에 실제로 있는 시트 이름으로 거르므로 꼴을 넓게 받는다 (글자들 + 숫자들 — 예전 꼴 그대로)
TO_ANY = re.compile(r"(?<![A-Z_])((?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]+\d+[A-Z]?)-(\d+)(?!\d)")
_SERIES = re.compile(r"([A-Z])\d{3}[A-Z]?$")

# 일반 꼴 (L23 · L23b): 시트 = 숫자가 든 덩어리(밑줄 · 안쪽 `-`/`.` 허용) · 구분 `-` `/` `.` `:` · 행 = 끝 숫자 1~3자리.
# 행 뒤에 구분+글자/숫자가 이어지면 그것까지 시트다 (`FG_G-301-64` → 시트 FG_G-301 · 행 64 · `LD.01.001-51`).
_GSHEET = r"(?=[A-Z0-9_\-.]*\d)[A-Z0-9][A-Z0-9_]+(?:[-.][A-Z0-9_]+)*?"
GEN_ANY = re.compile(rf"(?<![A-Z0-9_/\-.:])({_GSHEET})([-/.:])(\d{{1,3}})(?![\dA-Z_]|[-/.:][A-Z0-9])")
GEN_FULL = re.compile(rf"({_GSHEET})([-/.:])(\d{{1,3}})")


_OLD_SHAPE = re.compile(r"(?:[A-Z][A-Z0-9]{0,5}_)?[A-Z]+\d+[A-Z]?")


def _gen_ok(m):
    """일반 꼴이 옛 꼴의 땅을 넘보지 않는다 — `글자+숫자-행` 은 옛 꼴이 정하는 자리다 (`G54-85` 는 `G054-85` 를 잘못 읽은 것 ·
    HRSG 불변).  `.` · `:` 구분은 시트에 글자가 있을 때만 (`10.5 SEC` 같은 숫자를 참조로 읽지 않는다)."""
    sh, sep = m.group(1), m.group(2)
    if sep == "-" and _OLD_SHAPE.fullmatch(sh):
        return False
    if sep in ".:" and not re.search(r"[A-Z]", sh):
        return False
    return True


def _gen_text(text):
    """구분 기호 둘레의 빈칸만 지운다 — 낱말 사이 빈칸은 참조 목록의 경계다 (`0016/72 0016/77`).
    괄호는 벗기고, `SH.` `SHT` `SHEET` 머리말과 행 앞의 `NO.` `ROW` `LINE` 은 구분 기호로 읽는다 (`SH.AB-101 NO.51`)."""
    t = (text or "").upper().strip()
    t = re.sub(r"[()\[\]{}<>]", " ", t)
    t = re.sub(r"(?<![A-Z0-9])(?:SHEET|SHT|SH)\.?\s*(?=[A-Z0-9])", " ", t)
    t = re.sub(r"\s*(?<![A-Z0-9])(?:NO|ROW|LINE)\.?\s*(?=\d)", "-", t)
    return re.sub(r"\s*([-/:])\s*", r"\1", t).strip()


_NAMES = [None, 0, ()]                  # 마지막 묶음 하나만 든다 (결과를 붙들어 메모리를 늘리지 않게)


def _names(known):
    """그 묶음의 시트 이름 — 긴 것부터 (한 묶음에서 수만 번 불린다 · 같은 목록이면 다시 정렬하지 않는다)."""
    if _NAMES[0] is known and _NAMES[1] == len(known):
        return _NAMES[2]
    names = sorted({k.upper() for k in known if k}, key=len, reverse=True)
    _NAMES[:] = [known, len(known), names]
    return names


@functools.lru_cache(maxsize=8192)
def _name_re(no):
    return re.compile(rf"(?<![A-Z0-9_]){re.escape(no)}\s*(?:[-/.:#]|\s)\s*(\d{{1,3}})(?!\d)")


def _known(text, known):
    """그 묶음이 가진 시트 이름이 글에 그대로 있고 뒤에 행 번호가 붙은 것 — 꼴을 몰라도 읽는다."""
    if not known:
        return []
    t = _gen_text(text)
    out = []
    taken = []
    for no in _names(known):
        if no not in t:
            continue                       # 글에 그 이름이 없으면 맞대지 않는다 (같은 답 · 큰 묶음에서 빠르게 — L25)
        for m in _name_re(no).finditer(t):
            if any(a <= m.start() < b for a, b in taken):
                continue
            taken.append((m.start(), m.end()))
            out.append((m.start(), no, int(m.group(1))))
    return [(a, b) for _, a, b in sorted(out)]


def find(text, wide=False, known=None):
    """글 안의 시트-행 참조 [(시트, 행)].  옛 꼴이 하나라도 맞으면 옛 꼴 그대로 (HRSG · 19VA 불변).
    다음은 그 묶음의 시트 이름(known)으로, 그다음 일반 꼴로."""
    old = TO_ANY if wide else REF_ANY
    got = [(m.group(1), int(m.group(2))) for m in old.finditer((text or "").upper().replace(" ", ""))]
    if got:
        return got
    kn = _known(text, known)
    if kn:
        return kn
    return [(m.group(1), int(m.group(3))) for m in GEN_ANY.finditer(_gen_text(text)) if _gen_ok(m)]


def full(text, known=None):
    """칸 전체가 참조 하나면 (시트, 행) — 아니면 None (`HMI` · `FROM DRIVE` · `THIS SHEET. 100`)."""
    s = (text or "").upper().replace(" ", "")
    m = REF_ANY.fullmatch(s)
    if m:
        return m.group(1), int(m.group(2))
    g = _gen_text(text)
    kn = _known(text, known)
    if len(kn) == 1 and re.fullmatch(rf"{re.escape(kn[0][0])}\s*(?:[-/.:#]|\s)\s*{kn[0][1]:d}|"
                                    rf"{re.escape(kn[0][0])}\s*(?:[-/.:#]|\s)\s*0*{kn[0][1]}", g):
        return kn[0]
    m = GEN_FULL.fullmatch(g)
    if m and _gen_ok(m):
        return m.group(1), int(m.group(3))
    return None


def series(sheet_id: str) -> str:
    """시트 이름의 종류 글자 (G031 → G · HH10_P003 → P)."""
    m = _SERIES.search(sheet_id or "")
    if m:
        return m.group(1)
    m = re.search(r"([A-Z])[A-Z]*\d+[A-Z]?$", sheet_id or "")       # 예전 꼴 (G31 · B1) — 첫 글자
    return (sheet_id or "")[:1] if not m else re.sub(r"^(?:[A-Z][A-Z0-9]{0,5}_)", "", sheet_id)[:1]


def family(sheet_id: str) -> str:
    """시트 이름의 계열.  옛 꼴(글자 + 숫자 셋)이면 종류 글자, 아니면 숫자를 지운 모양 (`0016` → `#` · `FG_G-101` → `FG_G-#`)."""
    s = sheet_id or ""
    if SHEET_RE.match(s) or re.fullmatch(r"[A-Z]+\d+[A-Z]?", s):
        return series(s)
    return re.sub(r"\d+", "#", s)


def _system(sheet_id: str) -> str:
    m = re.match(r"([A-Z][A-Z0-9]{0,5})_", sheet_id or "")
    return m.group(1) if m else ""


class Bundle:
    """그 묶음이 실제로 가진 시트 이름들 — 참조가 이 묶음 것인지 다른 문서 것인지를 가른다."""

    def __init__(self, sheet_ids):
        ids = [x for x in sheet_ids if x]
        self.families = {family(x) for x in ids}
        self.systems = {_system(x) for x in ids if _system(x)}

    def other(self, sheet_id) -> bool:
        """다른 묶음(다른 문서) — 계열이 이 묶음에 없거나, 계통 접두가 있는데 그 접두를 쓰는 시트가 이 묶음에 하나도 없다
        (`GT_G910` 은 HR_… 묶음의 G 계열처럼 보여도 GT 문서다 · L23)."""
        if family(sheet_id) not in self.families:
            return True
        sy = _system(sheet_id)
        return bool(sy and self.systems and sy not in self.systems)

    def mine(self, sheet_id) -> bool:
        return not self.other(sheet_id)
