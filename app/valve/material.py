"""Material / specification comparison by meaning, not by spelling.

    'ASTM A351 CF8M'  vs '316/316L SS A351-CF8M/CF3M'  -> Compliant   (requirement grades are all present)
    '316 SS / HF'     vs 'SS 316/HF'                   -> Compliant   (same tokens, different order)
    'A351 CF8M'       vs 'A216 WCB'                    -> Non-Compliant (different material family)
    'A351 CF8M'       vs 'A182 F316'                   -> Review Required (same family, other product form —
                                                          equivalence is the engineer's call, spec §7.4)

A text is split into tokens; spelling variants are folded ('SS316' -> 316 + SS, 'STAINLESS STEEL' -> SS,
'GR.'/'GRADE'/'TYPE'/'ASTM' dropped).  Grades are grouped into families so 'different grade' and 'different
material' are told apart.  Nothing here guesses: when the tokens do not decide it, the answer is Review Required.
"""
from __future__ import annotations

import re

COMPLIANT, NON, REVIEW, NOT_DEFINED = "Compliant", "Non-Compliant", "Review Required", "Not Defined in PMS"

_NOISE = {"ASTM", "ASME", "GR", "GRADE", "TYPE", "CL", "CLASS", "AND", "OR", "WITH", "W", "THE", "OF", "MATERIAL",
          "VTA", "BODY", "BALL", "STEM", "SEAT", "DISC", "TRIM", "ST", "BONNET"}
_PHRASES = [(r"STAINLESS\s+STEEL", " SS "), (r"CARBON\s+STEEL", " CS "), (r"LOW\s+TEMP(?:ERATURE)?\s+CARBON\s+STEEL", " LTCS "),
            (r"HARD\s*-?\s*FACED|HARDFACED|HARD\s*FACING", " HF "), (r"\bSS\s*(\d{3}L?)\b", r" SS \1 "),
            (r"\b(\d{3}L?)\s*SS\b", r" \1 SS "), (r"\bTP\s*(\d{3}L?)\b", r" \1 "), (r"\bGR\.", " "),
            (r"17\s*-\s*4\s*PH", " 174PH "), (r"\bTYPE\s+630\b", " 174PH "), (r"\b630\b", " 174PH ")]

FAMILIES = {
    "SS316": {"316", "316L", "CF8M", "CF3M", "F316", "F316L", "316H", "F316H"},
    "SS304": {"304", "304L", "CF8", "CF3", "F304", "F304L"},
    "CS": {"WCB", "WCC", "A105", "A216", "CS", "A106", "A234", "WPB"},
    "LTCS": {"LCC", "LCB", "LF2", "LF6", "A350", "A352", "LTCS", "A333"},
    "DUPLEX": {"F51", "CD3MN", "4A", "2205", "S31803", "S32205"},
    "SDUPLEX": {"F53", "F55", "CD3MWCUN", "6A", "2507", "S32750", "S32760"},
    "PH174": {"174PH"},
    "PTFE": {"PTFE", "RTFE", "RPTFE", "TFE"},
    "PEEK": {"PEEK"},
    "GRAPHITE": {"GRAPHITE", "GRAFOIL", "FG"},
}
_FAM_OF = {g: f for f, gs in FAMILIES.items() for g in gs}
_GRADE = re.compile(r"^(?:\d{3}[LH]?|C[FDA]\w+|F\d{2,3}[LH]?|WC[BC]|LC[BC]|LF\d|174PH|S\d{5})$")
_SPEC = re.compile(r"^A\d{3}$")
_PLACEHOLDER = re.compile(r"^\s*(VTA|TBC|TBA|HOLD|NA|N/A|-|)\s*$", re.I)
_NOTE_REF = re.compile(r"(general\s*)?note\s*[-–:#]?\s*\d+", re.I)


def tokens(text: str) -> set[str]:
    t = " " + str(text or "").upper() + " "
    for pat, rep in _PHRASES:
        t = re.sub(pat, rep, t)
    t = re.sub(r"\b(A\d{3})\s*-\s*", r"\1 ", t)          # 'A351-CF8M' -> A351 CF8M
    out = set()
    for tok in re.split(r"[\s/,;()\[\]+&]+|-(?![0-9])", t):
        tok = tok.strip(".:-")
        if not tok or tok in _NOISE:
            continue
        if re.fullmatch(r"SS(\d{3}L?)", tok):
            out |= {"SS", tok[2:]}
            continue
        if tok in ("RPTFE", "R-PTFE"):
            tok = "RTFE"
        out.add(tok)
    return out


def _grades(ts):
    return {t for t in ts if _GRADE.match(t)}


def same(a: str, b: str) -> bool:
    """Same thing written differently ('316 SS / HF' == 'SS 316/HF').  Empty == empty."""
    ta, tb = tokens(a), tokens(b)
    return ta == tb


def compare(required: str, actual: str) -> tuple[str, str]:
    """(result, reason).  `required` is the reference (PMS), `actual` the datasheet value."""
    if not str(required or "").strip():
        return NOT_DEFINED, "No value defined in PMS"
    if _PLACEHOLDER.match(str(actual or "")) or (_NOTE_REF.search(str(actual or "")) and
                                                 not _grades(tokens(_NOTE_REF.sub(" ", str(actual))))):
        return REVIEW, f"Datasheet value is '{actual or '(blank)'}' — nothing to verify"
    r, d = tokens(required), tokens(actual)
    if r <= d:
        return COMPLIANT, "All required items present" + (" (notation differs only)" if r != d else "")
    gr, gd = _grades(r), _grades(d)
    sr, sd = {t for t in r if _SPEC.match(t)}, {t for t in d if _SPEC.match(t)}
    if gr and gd:
        if gr <= gd and (not sr or not sd or sr & sd):
            extra = sorted((r - d) - gr - sr)
            if not extra:
                return COMPLIANT, "Grade matches" + (f" (spec {'/'.join(sorted(sr))})" if sr else "")
            return REVIEW, f"Grade matches but required {' '.join(extra)} not stated"
        if gr & gd:
            return REVIEW, f"Required grade {'/'.join(sorted(gr - gd))} not stated (partial match)"
        fr, fd = {_FAM_OF.get(g) for g in gr} - {None}, {_FAM_OF.get(g) for g in gd} - {None}
        if fr and fd and not (fr & fd):
            return NON, f"Different material: required {'/'.join(sorted(gr))}, datasheet {'/'.join(sorted(gd))}"
        if fr & fd:
            return REVIEW, "Same material family, different grade / product form — equivalence to be confirmed by engineer"
        return REVIEW, "Grades cannot be compared automatically"
    fr = {_FAM_OF.get(t) for t in r} - {None}
    fd = {_FAM_OF.get(t) for t in d} - {None}
    if fr and fd and not (fr & fd):
        return NON, f"Different material: required {' '.join(sorted(r))}, datasheet {' '.join(sorted(d))}"
    if fr and fd and fr <= fd and not (r - d - {t for t in r if _FAM_OF.get(t)}):
        return COMPLIANT, "Same material (notation differs only)"
    return REVIEW, f"Cannot decide automatically: required '{required}', datasheet '{actual}'"
