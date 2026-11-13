"""Area from the tag's leading number — a rule LEARNED from the project's own documents, never typed into the code.

Evidence (each tag / document whose area a document states):
  · the Valve datasheets of the project family (area from the datasheet title / PDS cover, as the Valve first screen
    shows it: North · South · North Brownfield · South Brownfield · W15)
  · the process datasheets inside the Process Data annexure (each part's own title block)
  · (valve40) the Instrument Index's AREA column, one row per tag — the finer area ('sub-area') of every listed tag
And (valve40, user 2026-11-13) the engineer's own rule table, pasted on the By Area screen (project data, stored as the
project setting 'inst.arearule.table' — never in the code): 'Tag 접두어 · Area · Unit · 메모' rows under section lines
('2. Brownfield QN …' = the group of the rows below).  Each row is checked against the Index rows it covers.

From the evidence these tables are counted:
  prefix → areas       the tag's leading digits ('98' of 98PT-1001, '315' of 315MOV980004, '1' of 1-ZLS-090975)
  key → areas          deeper keys of the tag: prefix + letters ('98GTD'), + two digits ('315GE83') — when a prefix is shared
  system → areas       the first segment of the document / P&ID number ('999' of 999-98-PR-PID-00001, '98' of 98-51-IN-…)
  prefix / key → sub   the Index AREA values of the tags under it
A key whose evidence all says one area decides it.  A prefix used in several areas (one new unit built on two sites)
is decided by a deeper key or by the document / P&ID system of that tag when that says one area.  Otherwise no area — and why.
"""
from __future__ import annotations

import collections
import re

_PRE = re.compile(r"^\s*(\d+)")
_SYS = re.compile(r"^\s*([0-9]{2,4})-")
_SEG = re.compile(r"^(\d+)([A-Z]*)(\d*)")


def prefix(tag: str) -> str:
    m = _PRE.match(tag or "")
    return m.group(1) if m else ""


def system(no: str) -> str:
    """'999-98-PR-PID-00001' → '999' · '98-51-IN-DTS-00002' → '98' · '002-08-84-PR-DR-…' → '002' · 'D-84-1225' → ''."""
    m = _SYS.match(no or "")
    return m.group(1) if m else ""


def _norm(tag: str) -> str:
    return re.sub(r"[\s\-_/.]", "", (tag or "").upper())


def keys(tag: str) -> list[str]:
    """The tag's leading keys, shallow → deep: '1-ZLS-090975' → ['1', '1ZLS', '1ZLS09'] · '315GE83001C' → ['315', '315GE', '315GE83']."""
    m = _SEG.match(_norm(tag))
    if not m:
        return []
    n, a, d = m.groups()
    out = [n]
    if a:
        out.append(n + a)
        if len(d) >= 2:
            out.append(n + a + d[:2])
    return out


def wild(tag: str) -> str:
    """The prefix and the first two digits of the loop number, any letters between: '98PT-980001' → '98*98' — so a rule
    learned on Valve tags (98XV-98…, 98BDV-98…) also reaches an instrument letter code it never saw."""
    m = _SEG.match(_norm(tag))
    return f"{m.group(1)}*{m.group(3)[:2]}" if m and m.group(2) and len(m.group(3)) >= 2 else ""


def same_sub(a: str, b: str) -> bool:
    """'AG1' = 'AG1 BROWNFIELD' (one names the other's start) · 'AG1' ≠ 'AG2'."""
    x, y = _norm(a), _norm(b)
    return bool(x and y) and (x == y or x.startswith(y) or y.startswith(x))


# ── the engineer's rule table (pasted text → rows) ──────────────────────────────────────────────────────────────────
_HEAD = {"pattern": ("tag", "접두어", "prefix", "pattern", "패턴"), "sub": ("area", "구역", "sub"), "unit": ("unit", "유닛"),
         "note": ("exhibit", "메모", "note", "비고", "대응", "dec"), "count": ("건수", "count", "수량"), "group": ("group", "그룹")}
_SECTION = re.compile(r"^\s*(?:\d+[.)]|#+)\s*(.+?)\s*(?:\(.*)?$")
_LABEL = re.compile(r"^\s*(?:[-*•o◦·]\s+)?([A-Za-z0-9&][\w&\- ]{0,20}?)\s*:\s*(.+)$")
_SUBN = re.compile(r"\s*\((\d+)\)\s*")
_DTS = re.compile(r"^\s*DTS\s*(?:NO\.?)?\s*[:#]?\s*(\d{2,4})\s*-?\s*$", re.I)
_TRAIN = re.compile(r"^([A-Z]{1,2}\d+(?:/\d+)?)\b")


def _cells(line: str) -> list[str]:
    s = line.strip().strip("|")
    for sep in ("|", "\t"):
        if sep in s:
            return [c.strip() for c in s.split(sep)]
    return [c.strip() for c in re.split(r"\s{2,}", s)]


def _patterns(cell: str) -> list[str]:
    out = []
    for p in re.split(r"[,/]", cell or ""):
        p = p.strip().rstrip("-").strip()
        p = re.split(r"x{2,}", p)[0]                       # '315GE83xxxxC' → '315GE83'
        if re.match(r"^\d", p):
            out.append(_norm(p))
    return out


def parse_table(text: str) -> list[dict]:
    """Pasted text → [{patterns, sub, subs, unit, note, group, count}].  Accepts a Markdown / tab / two-space table with a
    header line ('Tag 접두어 | 건수 | Area 컬럼 | Unit | Exhibit 6 대응'), section lines ('2. Brownfield QN (…)' → group)
    and label lines ('QS: 98GTD- / 98SD-' → sub 'QS').  Without a header: pattern · Area · Unit · 메모."""
    rows, group, cols = [], "", None
    for raw in (text or "").splitlines():
        line = raw.rstrip()
        if not line.strip() or re.fullmatch(r"[\s|:\-+=]+", line):
            continue
        cells = _cells(line)
        low = [c.lower() for c in cells]
        md = _DTS.match(cells[0]) if cells else None
        if md and len(cells) >= 2 and cells[1].strip():         # 'DTS 98 | QN' — the datasheet's DTS No. names the site
            rows.append({"doc": md.group(1), "site": cells[1].strip(), "patterns": [f"DTS {md.group(1)}"], "subs": [cells[1].strip()],
                         "sub_n": {}, "sub": "", "unit": "", "note": cells[3] if len(cells) > 3 else "", "group": group, "count": ""})
            continue
        if len(cells) >= 2 and any(any(h in c for h in _HEAD["pattern"]) for c in low) and any(any(h in c for h in _HEAD["sub"]) for c in low):
            cols = {}
            for i, c in enumerate(low):
                for f in ("pattern", "count", "unit", "group", "note", "sub"):
                    if f not in cols and any(h in c for h in _HEAD[f]) and i not in cols.values():
                        cols[f] = i
            continue
        if len(cells) >= 2 and _patterns(cells[(cols or {}).get("pattern", 0)]):
            g = lambda f, d: cells[cols[f]] if cols and f in cols and cols[f] < len(cells) else (cells[d] if not cols and d < len(cells) else "")
            sub_cell = g("sub", 1)
            subs = [(_SUBN.sub("", s).strip(), int(m.group(1)) if (m := _SUBN.search(s)) else 0) for s in re.split(r",\s*", sub_cell) if s.strip()]
            rows.append({"patterns": _patterns(cells[(cols or {}).get("pattern", 0)]), "subs": [s for s, _ in subs], "sub_n": {s: n for s, n in subs if n},
                         "sub": subs[0][0] if len(subs) == 1 else "", "unit": g("unit", 2), "note": g("note", 3),
                         "group": g("group", 99) or group, "count": g("count", 99)})
            continue
        m = _LABEL.match(line)
        if m and _patterns(m.group(2)) and len(cells) < 2:
            rows.append({"patterns": _patterns(m.group(2)), "subs": [m.group(1).strip()], "sub_n": {}, "sub": m.group(1).strip(),
                         "unit": "", "note": "", "group": group, "count": ""})
            continue
        m = _SECTION.match(line)
        if m and len(cells) < 2:
            group, cols = m.group(1).strip(), None
    return rows


def num_eq(a: str, b: str) -> bool:
    """'1' = '01' (the Index writes 1-ZLS-…, a Valve datasheet 01-XV-…) · '1' ≠ '19'."""
    return a.isdigit() and b.isdigit() and int(a) == int(b)


def _row_for(table: list[dict], tag: str):
    """The table row whose pattern is the longest start of the tag ('1' matches '1-ZLS-…' but not '19…' or '15…')."""
    ks, nt = keys(tag), _norm(tag)
    best, bl = None, 0
    for r in table or []:
        if r.get("doc"):
            continue
        for p in r["patterns"]:
            hit = num_eq(p, ks[0]) if (ks and p.isdigit()) else (nt.startswith(p) and (p[-1].isdigit() or len(nt) == len(p) or not nt[len(p)].isalpha()))
            if hit and len(p) > bl:
                best, bl = r, len(p)
    return best


# ── learning ───────────────────────────────────────────────────────────────────────────────────────────────────────
def learn(evidence: list[dict], table: list[dict] | None = None) -> dict:
    """evidence: [{tag?, doc_no?, zone?, sub?}] → the counted tables (see the module text) + the engineer's table."""
    P, K, Y, PY = (collections.defaultdict(collections.Counter) for _ in range(4))
    SP, SK = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    index = []
    n = 0
    for e in evidence:
        z, s = e.get("zone") or "", (e.get("sub") or "").strip()
        ks = keys(e.get("tag", ""))
        w = wild(e.get("tag", ""))
        if s and ks:
            SP[ks[0]][s] += 1
            for k in ks[1:] + ([w] if w else []):
                SK[k][s] += 1
            index.append((e["tag"], s))
        if not z or " · " in z or z.startswith("("):       # several areas / '(not stated)' is no evidence for one
            continue
        p, sy = prefix(e.get("tag", "")), system(e.get("doc_no", ""))
        if p:
            P[p][z] += 1
            for k in ks[1:] + ([w] if w else []):
                K[k][z] += 1
        if sy:
            Y[sy][z] += 1
        if p and sy:
            PY[(p, sy)][z] += 1
        n += 1
    rule = {"prefix": {k: dict(v) for k, v in P.items()}, "key": {k: dict(v) for k, v in K.items()},
            "system": {k: dict(v) for k, v in Y.items()}, "pair": {f"{a}|{b}": dict(v) for (a, b), v in PY.items()},
            "sub_prefix": {k: dict(v) for k, v in SP.items()}, "sub_key": {k: dict(v) for k, v in SK.items()},
            "n": n, "n_index": len(index), "table": table or []}
    # the area of each Index sub-area: the one area of the prefixes it is listed under (when those prefixes decide one)
    votes = collections.defaultdict(collections.Counter)
    for t, s in index:
        z = _one(rule["prefix"].get(prefix(t)))
        if z:
            votes[s][z] += 1
    rule["sub_area"] = {s: _one(v) for s, v in votes.items() if _one(v)}
    # the engineer's groups ('Brownfield QS') named as the documents name them ('South Brownfield') when they agree
    alias = collections.defaultdict(collections.Counter)
    for r in rule["table"]:
        if r.get("doc"):
            continue
        for p in r["patterns"]:
            zs = {_one(v) for k, v in rule["prefix"].items() if num_eq(k, p)} if p.isdigit() else {_one(rule["key"].get(p))}
            z = zs.pop() if len(zs) == 1 else ""
            if z and r["group"]:
                alias[r["group"]][z] += 1
    rule["alias"] = {g: _one(v) for g, v in alias.items() if _one(v)}
    rule["index"] = index
    return rule


def _one(c: dict | None) -> str:
    return next(iter(c)) if c and len(c) == 1 else ""


def _deep(rule: dict, tag: str, what: str) -> tuple[str, str]:
    """A deeper key of the tag whose evidence says one value ('98GTD' → South while '98' is on both sites)."""
    for k in list(reversed(keys(tag)[1:])) + ([wild(tag)] if wild(tag) else []):
        z = _one(rule.get(what, {}).get(k))
        if z:
            return z, k
    return "", ""


SITES = ("North", "South")                                  # a site alone (Greenfield or Brownfield not said)


def area_for(rule: dict, tag: str, doc_no: str = "", pid_no: str = "") -> tuple[str, str]:
    """(area, basis) for one tag from the documents' evidence; ('', why) when the evidence does not decide."""
    if not rule or not rule.get("n"):
        return "", ""
    p = prefix(tag)
    pc = rule["prefix"].get(p) if p else None
    if pc and len(pc) == 1:
        z = _one(pc)
        return z, f"Tag 앞 '{p}' = {z} (근거 {sum(pc.values())}건)"
    for no in (pid_no, doc_no):                             # the same prefix on two sites: the document / P&ID system decides
        s = system(no)
        if not s:
            continue
        z = _one(rule["pair"].get(f"{p}|{s}")) or (_one(rule["system"].get(s)) if pc else "")
        if z and (not pc or z in pc):
            return z, f"Tag 앞 '{p}' 는 {' · '.join(pc)} 에 다 쓰임 → 번호 '{s}-…' = {z}" if pc else f"번호 '{s}-…' = {z}"
    z, k = _deep(rule, tag, "key")                           # … or a deeper key of the tag ('98GTD')
    if z and (not pc or z in pc):
        kk = f"{k.split('*')[0]}-◦-{k.split('*')[1]}…" if "*" in k else k
        return z, f"Tag '{kk}' = {z}" + (f" ('{p}' 는 {' · '.join(pc)} 에 다 쓰임)" if pc else "")
    if not pc and p and _one(rule["system"].get(p)):        # the unit number also leads the documents ('03-02-PR-DTS-…')
        z = _one(rule["system"][p])
        if z in SITES:                                       # valve40: a title naming only the site says nothing of Brownfield
            return "", f"Tag 앞 '{p}' = 문서 번호 '{p}-…' 의 Site {z} — Brownfield 여부 근거 없음 (규칙 표로 정하기)"
        return z, f"Tag 앞 '{p}' = 문서 번호 '{p}-…' 의 {z}"
    if not pc:
        s = system(pid_no) or system(doc_no)
        z = _one(rule["system"].get(s)) if s else ""
        if z in SITES:
            return "", f"Tag 앞 '{p}' 는 근거 없음 · 번호 '{s}-…' 의 Site {z} — Brownfield 여부 근거 없음"
        if z:
            return z, f"Tag 앞 '{p}' 는 근거 없음 · 번호 '{s}-…' = {z}"
        return "", f"Tag 앞 '{p}' 의 Area 근거가 없음" if p else ""
    return "", f"Tag 앞 '{p}' 는 {' · '.join(pc)} 에 다 쓰임 — 문서 / P&ID 번호로 가를 수 없음"


def classify(rule: dict, tag: str, doc_no: str = "", pid_no: str = "", index_sub: str = "") -> dict:
    """{area, sub, unit, basis} — the engineer's table first, then the tag's own Index AREA, then the learned evidence."""
    rule = rule or {}
    row = _row_for(rule.get("table"), tag)
    why = []
    sub = (index_sub or "").strip()
    if sub:
        why.append(f"Instrument Index AREA = {sub}")
    elif row and row["sub"]:
        sub = row["sub"]
    elif row and row["subs"]:
        why.append(f"규칙 표: {' · '.join(row['subs'])} 중 하나 — Index 에 이 Tag 가 없어 가를 수 없음")
    if not sub and not row:
        s, k = (_one(rule.get("sub_prefix", {}).get(prefix(tag))), prefix(tag))
        if not s:
            s, k = _deep(rule, tag, "sub_key")
        if s:
            sub = s
            why.append(f"Index 에서 Tag 앞 '{k}' = {s}")
    area = ""
    if row:
        g = row["group"]
        area = rule.get("alias", {}).get(g, g) if g else ""
        pats = ", ".join(p for p in row["patterns"] if keys(tag) and (_norm(tag).startswith(p) or p == keys(tag)[0]))
        why.insert(0, f"규칙 표: '{pats}' → {row['sub'] or ' · '.join(row['subs'])}" + (f" ({g})" if g else "") + (f" · Unit {row['unit']}" if row["unit"] else ""))
    if not area and sub:
        area = next((z for s, z in rule.get("sub_area", {}).items() if same_sub(s, sub)), "")
    if not area:
        area, b = area_for(rule, tag, doc_no, pid_no)
        if b:
            why.append(b)
    au = area.upper()
    site = "North" if "NORTH" in au else "South" if "SOUTH" in au else ""
    if not site:                                             # only the site is known ('Site North — Brownfield 여부 근거 없음')
        m = re.search(r"Site (North|South)", " ".join(why))
        site = m.group(1) if m else ""
    return {"area": area, "sub": sub, "unit": (row or {}).get("unit", ""), "basis": " · ".join(x for x in why if x),
            "note": (row or {}).get("note", ""), "site": site}


# ── for the screen ─────────────────────────────────────────────────────────────────────────────────────────────────
def table(rule: dict) -> list[dict]:
    """The learned rule as rows for the screen: prefix · areas with counts · decided area or how it is split · Index sub-areas."""
    rows = []
    pre = set((rule or {}).get("prefix", {})) | set((rule or {}).get("sub_prefix", {}))
    for p in sorted(pre, key=lambda x: (len(x), x)):
        c = rule.get("prefix", {}).get(p, {})
        split, bykey = {}, {}
        if len(c) > 1:
            for k, v in rule["pair"].items():
                a, s = k.split("|")
                if a == p and len(v) == 1:
                    split[s] = next(iter(v))
            K = rule.get("key", {})
            ws = {k: _one(v) for k, v in K.items() if "*" in k and k.split("*")[0] == p and _one(v)}
            for k, v in K.items():                              # letters / letters+digits keys the digit rule does not already say
                if "*" in k or not keys(k) or keys(k)[0] != p or not _one(v):
                    continue
                w = f"{p}*{k[len(keys(k)[1]):][:2]}" if len(keys(k)) > 2 else ""
                if ws.get(w) != _one(v):
                    bykey[k] = _one(v)
            bykey.update(ws)
        subs = rule.get("sub_prefix", {}).get(p, {})
        how = [f"번호 '{s}-…' → {z}" for s, z in sorted(split.items())] + [
            (f"Tag {k.split('*')[0]}-◦-{k.split('*')[1]}… → {z}" if "*" in k else f"Tag '{k}…' → {z}") for k, z in sorted(bykey.items())]
        rows.append({"prefix": p, "areas": c, "n": sum(c.values()), "area": _one(c), "by_system": split, "by_key": bykey, "subs": subs,
                     "rule": _one(c) or (" · ".join(how) or ("가를 수 없음" if c else ""))})
    return rows


def check_table(rule: dict) -> list[dict]:
    """Each row of the engineer's table against the Index rows it covers: '20 / 20' = 20 of the 20 listed tags agree."""
    out = []
    for r in (rule or {}).get("table", []):
        if r.get("doc"):
            out.append(dict(r, area=r["site"], n_index=0, n_ok=0, other={}, examples=[]))
            continue
        hit = [(t, s) for t, s in rule.get("index", []) if _row_for([r], t)]
        ok = [x for x in hit if any(same_sub(x[1], s) for s in r["subs"])]
        other = collections.Counter(s for t, s in hit if not any(same_sub(s, x) for x in r["subs"]))
        out.append(dict(r, area=rule.get("alias", {}).get(r["group"], r["group"]), n_index=len(hit), n_ok=len(ok),
                        other=dict(other.most_common(5)), examples=[t for t, _ in hit if (t, _) not in ok][:5]))
    return out


# ── valve40 (user 2026-11-13): Site from the DTS No. · Brownfield + train inside a site that has Brownfield ─────────────
def site_map(rule: dict) -> dict:
    """What the documents call a site ('North' · 'South' · 'W15') → the table's site code ('QN' · 'QS' · 'W15'), learned
    from the DTS rows and the documents' own areas by document number ('98-…' documents say North and DTS 98 = QN)."""
    m = {}
    for r in (rule or {}).get("table", []):
        if r.get("doc"):
            m[r["site"]] = r["site"]
            z = _one((rule.get("system") or {}).get(r["doc"]))
            if z:
                m.setdefault(z.split()[0], r["site"])
    return m


def resolve(rule: dict, tag: str, doc_no: str = "", pid_no: str = "", doc_zone: str = "", index_sub: str = "") -> dict:
    """{label, site, brown, train, sub, unit, basis} — label 'QN' · 'QN Brownfield N1' · 'QS' · 'W15'; '' when the table has
    no DTS rows (then the older area words stay).  Site: the DTS No. → else the datasheet title → else the tag rule.
    Brownfield only in a site the table gives a 'Brownfield <site>' group; the train = the first word of that row's note."""
    rule = rule or {}
    rows = rule.get("table") or []
    docs = [r for r in rows if r.get("doc")]
    if not docs:
        return {"label": "", "site": "", "brown": False, "train": "", "sub": "", "unit": "", "basis": ""}
    codes = {r["site"] for r in docs}
    smap = site_map(rule)
    C = classify(rule, tag, doc_no, pid_no, index_sub)
    row = _row_for(rows, tag)
    why, site = [], ""
    sy = system(doc_no)
    d = next((r for r in docs if r["doc"] == sy), None)
    if d:
        site = d["site"]
        why.append(f"DTS No. '{sy}-…' = {site}")
    elif doc_zone and doc_zone != "Brownfield":
        site = smap.get(doc_zone.split()[0], "")
        if site:
            why.append(f"Datasheet 표제 = {doc_zone}")
    if not site and row:                                      # the tag rule: a row naming a site, or its group
        site = next((x for x in row["subs"] if x in codes), "") or next((c for c in codes if re.search(rf"\b{re.escape(c)}\b", row["group"] or "")), "")
        if site:
            why.append(f"Tag 규칙 '{', '.join(row['patterns'])}' = {site}")
    if not site and C["area"]:
        site = smap.get(C["area"].split()[0], "") or next((c for c in codes if re.search(rf"\b{re.escape(c)}\b", C["area"])), "")
        if site:
            why.append(C["basis"])
    brown_sites = {c for c in codes for r in rows if not r.get("doc") and "BROWNFIELD" in (r["group"] or "").upper()
                   and re.search(rf"\b{re.escape(c)}\b", r["group"])}
    says = ("BROWNFIELD" in (doc_zone or "").upper()) or bool(row and "BROWNFIELD" in (row["group"] or "").upper())
    brown = bool(site) and site in brown_sites and says
    train = ""
    if brown and row:
        m = _TRAIN.match((row.get("note") or "").strip())
        train = m.group(1) if m else ""
        why.append(f"Brownfield: Tag 규칙 '{', '.join(row['patterns'])}'" + (f" · {row['note']}" if row.get("note") else ""))
    elif brown:
        why.append(f"Brownfield: Datasheet 표제 = {doc_zone}")
    elif says and site and site not in brown_sites:
        why.append(f"{'표제' if 'BROWNFIELD' in (doc_zone or '').upper() else 'Tag 규칙'}는 Brownfield — {site} 에는 Brownfield 구분 없음 (규칙 표)")
    label = site + ((" Brownfield" + (f" {train}" if train else "")) if brown else "")
    return {"label": label, "site": site, "brown": brown, "train": train, "sub": "" if C["sub"] in codes else C["sub"], "unit": C["unit"],
            "basis": " · ".join(x for x in why if x), "note": C["note"]}
