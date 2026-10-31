"""Special requirements of a datasheet — what its cells, Notes and the document's General Notes ask for beyond the
plain data (sour service, fugitive emission, fire safety, PFP, anti-static, certificates …).

Deterministic: a fixed dictionary of requirement kinds, each found by its own words or standard number.  Every hit
keeps its source ('Note 14', 'Gen Note 8', 'row 29 Packing Type') and the sentence it came from, so a reviewer can
check it in one click.  Nothing is inferred: a requirement is listed only when the text names it.
"""
from __future__ import annotations

import re

# (key, label shown in the Valve List / tool, pattern, detail patterns that sharpen the label)
KINDS = [
    ("nace", "Sour service NACE MR0175 / ISO 15156", re.compile(r"\bNACE\b|MR\s*-?\s*0175|ISO\s*15156", re.I), []),
    ("fugitive", "Fugitive emission ISO 15848-1", re.compile(r"fugitive|ISO\s*15848|TA[- ]?Luft", re.I),
     [re.compile(r"Class\s+[A-C]\b(?:\s*type\s*tested)?", re.I), re.compile(r"endurance\s+class\s+C[OC]\d", re.I)]),   # 'CO2' alone is the fluid
    ("fire_safe", "Fire-safe API 607 / API 6FA / ISO 10497", re.compile(r"fire[- ]?safe|fire[- ]?tested|API\s*607|API\s*6FA|ISO\s*10497", re.I), []),
    ("pfp", "Passive fire protection (PFP)", re.compile(r"\bPFP\b|passive\s+fire|fire[- ]?proof", re.I), []),
    ("antistatic", "Anti-static device", re.compile(r"anti[- ]?static", re.I), []),
    ("blowout", "Blow-out proof stem", re.compile(r"blow[- ]?out", re.I), []),
    ("sil", "SIL", re.compile(r"\bSIL\s*[1-4]\b|\bSIL\b|safety integrity", re.I), [re.compile(r"\bSIL\s*[1-4]\b", re.I)]),
    ("pst", "Partial stroke test", re.compile(r"partial\s+stroke", re.I), []),
    ("hardness", "Hardness limit", re.compile(r"hardness|\bHRC\b|\bHV\s*10\b|\bHBW?\b", re.I), [re.compile(r"\d+\s*(?:HRC|HV\s*10|HBW?)", re.I)]),
    ("cert", "Material certificate EN 10204", re.compile(r"EN\s*10204|\b3\.[12]\s*cert|type\s+3\.[12]", re.I), [re.compile(r"\b3\.[12]\b")]),
    ("pmi", "PMI (positive material identification)", re.compile(r"\bPMI\b|positive\s+material", re.I), []),
    ("impact", "Low-temperature impact test", re.compile(r"impact\s+test|charpy|low[- ]temperature", re.I), []),
    ("dbb", "Double block & bleed / cavity relief", re.compile(r"double\s+block|\bDBB\b|cavity\s+(?:pressure\s+)?relief", re.I), []),
    ("coating", "Painting / coating specification", re.compile(r"painting\s+(?:system|spec)|coating|\bpaint\b", re.I), []),
    ("tightness", "Tight shut-off / leakage class", re.compile(r"tight\s+shut[- ]?off|\bTSO\b|leakage\s+class|ISO\s*5208|API\s*598|FCI\s*70-2", re.I),
     [re.compile(r"Rate\s+[A-G]{1,2}\b|Class\s+(?:VI|V|IV)\b", re.I)]),
]
_NEG = re.compile(r"\b(not\s+required|not\s+applicable|\bN/?A\b|none|no)\b", re.I)


_STOP = re.compile(r"(?<!\b[A-Z])(?<!\bMax)(?<!\bNo)(?<!\bGr)(?<!\bCl)\.(?=\s+[A-Z(]|\s*$)")    # '3.2' · 'Max.' · 'CL.2' are not sentence ends


def _sentence(text: str, m: re.Match, width: int = 170) -> str:
    ends = [x.end() for x in _STOP.finditer(text)]
    a = max([e for e in ends if e <= m.start()], default=0)
    b = min([e for e in ends if e >= m.end()], default=len(text))
    return re.sub(r"\s+", " ", text[a:b]).strip()[:width]


def find(ds: dict, general_notes: dict | None = None) -> list[dict]:
    """[{key, label, detail, source, text, negative}] — one entry per (kind, source)."""
    from app.valve import schema
    fields = ds["fields"] if isinstance(ds["fields"], list) else [dict(f, key=k) for k, f in ds["fields"].items()]
    srcs = []
    for f in fields:
        v = schema.effective(f) if "edited_value" in f else (f.get("value") or "")
        if v and v.strip():
            srcs.append((f"row {f.get('row')} {f.get('display') or f['key']}" if f.get("row") else (f.get("display") or f["key"]), v, f.get("display") or ""))
    for n in ds.get("notes") or []:
        srcs.append((f"{'HOLD' if (n.get('section') or '').upper() == 'HOLD' else 'Note'} {n['no']}", n["text"], ""))
    for no, t in sorted((general_notes or {}).items(), key=lambda kv: int(kv[0])):
        srcs.append((f"Gen Note {no}", t, ""))
    out, seen = [], set()
    for src, text, label in srcs:
        for key, name, pat, details in KINDS:
            m = pat.search(text) or (pat.search(label) if label else None)
            if not m:
                continue
            if key == "tightness" and src.startswith(("Note", "Gen")) and not re.search(r"shall|required|class|rate", text, re.I):
                continue
            if (key, src) in seen:
                continue
            seen.add((key, src))
            body = text if pat.search(text) else f"{label}: {text}"
            dm = [d.search(body) for d in details]
            extra = " ".join(dict.fromkeys(x.group(0) for x in dm if x))
            neg = src.startswith("row") and bool(re.match(r"^\s*(not\s+required|no|n/?a|none|-|—)\s*(\(|$)", text, re.I))
            out.append({"key": key, "label": name + (f" — {extra}" if extra else ""), "detail": extra, "source": src,
                        "text": _sentence(body, pat.search(body) or m), "negative": neg})
    return out


def summary(items: list[dict]) -> str:
    """'NACE MR0175 / ISO 15156 (Note 1, Gen Note 33) · Fugitive emission ISO 15848-1 — Class A type tested (Gen Note 8) · …'"""
    by = {}
    for i in items:
        e = by.setdefault(i["key"], {"label": i["label"], "src": [], "neg": []})
        if len(i["label"]) > len(e["label"]):
            e["label"] = i["label"]
        (e["neg"] if i["negative"] else e["src"]).append(i["source"])
    parts = []
    for k, e in by.items():
        s = e["label"] + (f" ({', '.join(e['src'][:4])}{'…' if len(e['src']) > 4 else ''})" if e["src"] else "")
        if e["neg"]:
            s += f" [datasheet: Not Required — {', '.join(e['neg'][:2])}]"
        parts.append(s)
    return " · ".join(parts)
