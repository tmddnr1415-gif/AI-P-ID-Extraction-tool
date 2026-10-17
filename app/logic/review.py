"""L39 — 정합성 검토 결과 한 장.

엔지니어가 Logic 선도를 앞에 두고 머릿속으로 하던 검토를 툴이 끝까지 한 결과를 **한 곳에** 모은다.
판정 0줄 — 이미 있는 판정(읽기 · from-to · 연결 점검 · 동작 학습 · 묶음 시뮬레이터)을 모아 세 갈래로 가른다.

  ERROR  설계 오류   도면이 실제로 어긋났다 — from-to 연결이 안 맞음 (FM 이 가리키는 행에 신호 없음 · TO 가 다른 곳)
  CHECK  설계 확인   논리상 설계 원칙과 다르다 — 사람이 '의도된 설계인가' 를 판단할 자리
                     (반대 명령 동시 가능 · 늘 켜짐 · 상수로 묶임 · 유지되는데 끄는 신호 없음 · 반대 명령이 못 끔 ·
                      설명만 다름 · 선이 빈 곳에서 끝남 · 짝 없는 연결 기호 · 어느 조합으로도 안 서는 명령)
  GAP    읽기 빈틈   툴이 도면을 다 읽지 못한 자리 — 가르치기 · 마크업으로 메운다
                     (판정 못 한 블록 · 입력을 다 읽지 못한 게이트 · 블록 근처에서 끝난 선 · 시트 이름/FM/TO 못 읽음)
  INFO   참고        사람 몫으로 세지 않는다 (장 밖으로 나가는 연결 기호 · 인터록 없는 명령 …)

검토 대상(목표)마다 툴이 판정을 끝냈는가를 세어 '툴 판정율' 을 낸다:
  from-to 신호 행 · 블록 · 명령 · 반대 명령 짝 — 판정이 섰으면(맞음 · 오류 · 확인) 툴이 끝낸 것, 읽기 빈틈이면 못 끝낸 것.
"""
from __future__ import annotations

import time

from . import behavior as BH
from . import idrate as IDR
from . import report as RP
from . import sequence, sim

VERSION = 1
CANCEL_MAX = 600          # 반대 명령이 끄는가 — 장비 수 상한 (시간)

CAT_KO = {"ERROR": "설계 오류", "CHECK": "설계 확인", "GAP": "읽기 빈틈", "INFO": "참고"}
CAT_ORDER = ["ERROR", "CHECK", "GAP", "INFO"]
TOPIC_KO = {"fromto": "from-to", "line": "선 연결", "gate": "게이트", "command": "명령 동작", "pair": "반대 명령",
            "read": "읽기"}


def _row(s, side, n):
    return next((r for r in s.get("rows", []) if r["side"] == side and r["n"] == n), None) or \
        next((t for t in s.get("table", []) if t["side"] == side and t["n"] == n), None)


def _row_rect(s, side, n):
    """행 하나의 자리 — FM/TO 칸부터 행 번호 칸까지 (표의 그 줄)."""
    r = _row(s, side, n)
    if not r:
        return None
    boxes = [b for b in (r.get("fm_box"), r.get("no_box"), r.get("to_box")) if b]
    if not boxes:
        y0, y1 = r.get("y0"), r.get("y1")
        lg = s.get("logic") or s.get("frame")
        if y0 is None or not lg:
            return None
        x0, x1 = (lg[0] - 60, lg[0]) if side == "L" else (lg[2], lg[2] + 60)
        return [x0, y0, x1, y1]
    return [min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)]


def _pt_rect(at, s, k=0.6):
    p = (s.get("pitch") or 10) * k
    return [at[0] - p, at[1] - p, at[0] + p, at[1] + p]


def _item(cat, topic, code, s, title, text, rect=None, **kw):
    return {"cat": cat, "topic": topic, "code": code, "page": s["page"], "sheet_no": s.get("sheet_no") or "",
            "title": title, "text": text, "rect": rect, **kw}


# ------------------------------------------------------------------ 정적 — 읽기 · from-to · 선 · 게이트

def _static(sheets, items, tally):
    for s in sheets:
        blocks = s.get("blocks", {})
        ins = {}
        for p in s.get("ports", []):
            if p.get("dir") == "in":
                ins.setdefault(p["block"], set()).add(p["net"])
        flagged = set()
        dang = set()
        # from-to — 신호 행마다
        for r in s.get("rows", []):
            ft = r.get("ft")
            if not ft:
                continue
            tally["fromto"][1] += 1
            rect = _row_rect(s, r["side"], r["n"])
            ref = f"{s.get('sheet_no')}-{r['n']}"
            if ft.get("ok") is False:
                tally["fromto"][0] += 1
                items.append(_item("ERROR", "fromto", "FT_MISMATCH", s, f"{ref} from-to 불일치",
                                   f"{'FM' if r['side'] == 'L' else 'TO'} {ft.get('peer') or ''} — " +
                                   " · ".join(ft.get("why") or ["연결이 맞지 않습니다"]),
                                   rect, row=r["n"], side=r["side"], peer=ft.get("peer"), desc=r.get("desc")))
            elif ft.get("warn"):
                tally["fromto"][0] += 1
                items.append(_item("CHECK", "fromto", "FT_DESC_DIFF", s, f"{ref} 설명 다름",
                                   f"{ft.get('peer') or ''} 연결은 맞음 — " + " · ".join(ft["warn"]),
                                   rect, row=r["n"], side=r["side"], peer=ft.get("peer"), desc=r.get("desc")))
            else:
                tally["fromto"][0] += 1
        # 연결 점검
        for f in s.get("findings", []):
            c = f["code"]
            if c.startswith("FT_"):
                continue
            at = f.get("at")
            b = blocks.get(f.get("block")) if f.get("block") else None
            rect = (b or {}).get("bbox") or (_pt_rect(at, s) if at else None)
            if c == "C1_DANGLING":
                # 선 끝이 아무 데도 안 닿음 — 도면에서 정말 끊겼는지, 교차 · 홉 · 기호를 못 읽었는지 툴이 확실히 가르지 못한다
                # (L39 실측: '빈 곳' 으로 보인 것도 표본마다 ANN 원 · 매크로 틀 · 펄스 표시를 못 읽은 자리였다) — 사람이 본다
                dang.add(str(f.get("net")))
                items.append(_item("GAP", "line", c, s, "선 끝 — 이음 못 읽음",
                                   "선 끝이 블록 · 행 · 다른 선에 닿지 않습니다 — 교차 · 홉 · 기호를 못 읽었거나 도면에서 선이 끊김",
                                   rect, net=f.get("net")))
            elif c == "C1_ARROW_NOWHERE":
                items.append(_item("GAP", "line", c, s, "화살촉 — 가리키는 블록 없음", f["text"], rect))
            elif c == "C7_CONNECTOR_NO_SOURCE":
                items.append(_item("CHECK", "line", c, s, f"연결 기호 '{(b or {}).get('label') or ''}' 짝 없음", f["text"],
                                   rect, block=f.get("block")))
            elif c == "C7_CONNECTOR_NO_SOURCE_OUT":
                items.append(_item("INFO", "line", c, s, f"연결 기호 '{(b or {}).get('label') or ''}' 장 밖", f["text"],
                                   rect, block=f.get("block")))
            elif c in ("BLOCK_UNKNOWN", "C3_GATE_NO_INPUT", "C3_BLOCK_UNCONNECTED"):
                flagged.add(f.get("block"))
                label = RP.LABELS.get(c, c)
                items.append(_item("GAP", "gate", c, s, f"{f.get('block')} {label}", f.get("text") or label, rect,
                                   block=f.get("block")))
        # 선 — 그물마다 (선 끝이 매달린 그물은 툴이 끝내지 못한 것)
        for nid in s.get("nets", {}):
            tally["line"][1] += 1
            if str(nid) not in dang:
                tally["line"][0] += 1
        # 게이트 — 종류 · 입력
        for bid, b in blocks.items():
            if b.get("func") == "CONNECTOR":
                continue
            tally["gate"][1] += 1
            lg = b.get("logic")
            short = lg in sim.MIN_INPUTS and len(ins.get(bid, ())) < sim.MIN_INPUTS[lg]
            if b.get("func") == "UNKNOWN" or bid in flagged:
                continue
            if short:
                items.append(_item("GAP", "gate", "GATE_SHORT", s, f"{bid} {b.get('func')} 입력 덜 읽음",
                                   f"{b.get('func')} 입력 {len(ins.get(bid, ()))}개만 읽었습니다 (범례 정의는 {sim.MIN_INPUTS[lg]}개 이상) "
                                   "— 출력을 내지 않습니다", b.get("bbox"), block=bid))
                continue
            tally["gate"][0] += 1


def _reading(res, items):
    """시트 이름 · FM/TO 칸 · 없는 시트 — 식별률이 센 못 읽은 것 중 게이트 아닌 것."""
    m = IDR.measure(res)
    by = {s["page"]: s for s in res.get("sheets", [])}
    for it in m.get("items") or []:
        if it["kind"] == "GATE":
            continue
        s = by.get(it["page"]) or {"page": it["page"], "sheet_no": it.get("sheet_no")}
        cat = "GAP"
        title = {"SHEET": "시트 이름 못 읽음", "FROM": "FM 칸 못 읽음", "TO": "TO 칸 못 읽음", "LINK": "없는 시트"}[it["kind"]]
        items.append(_item(cat, "read", "READ_" + it["kind"], s, title, it["text"], it.get("at"), row=it.get("row")))
    return m


# ------------------------------------------------------------------ 동작 — 동작 학습 결과 + 반대 명령이 끄는가

def _cmd_rect(by, x):
    s = by.get(x["page"])
    return _row_rect(s, "R", x["row"]) if s else None


def _lab(ls, n=4):
    return " + ".join(l["text"] for l in (ls or []) if not l.get("assumed"))[:200] or "신호 없음"


def _behavior(sheets, learned, items, tally, cache, budget):
    by = {s["page"]: s for s in sheets}
    if not learned:
        return {"learned": False}
    for x in learned.get("items") or []:
        s = by.get(x["page"])
        if not s:
            continue
        tally["command"][1] += 1
        name = f"{x.get('equip')} {x.get('action')}"
        rect = _cmd_rect(by, x)
        base = dict(row=x["row"], side="R", equip=x.get("equip"), action=x.get("action"))
        if not x.get("reached"):
            gap = x.get("undriven") or x.get("stuck") or (x.get("blocked_at") or {}).get("label")
            if gap:
                b = x.get("blocked_at") or {}
                items.append(_item("GAP", "command", "CMD_GAP", s, f"{name} — 안 섬 (읽기 빈틈)",
                                   (x.get("why") or "도면 읽기 빈틈") + (f" · 막힌 곳 {b.get('label')}" if b.get("label") else ""),
                                   rect, **base))
            else:
                tally["command"][0] += 1
                items.append(_item("CHECK", "command", "CMD_NEVER", s, f"{name} — 어떤 조합으로도 안 섬",
                                   x.get("why") or "어느 조합으로도 안 섬 — 되먹임 · 다른 시트 조건 확인", rect, **base))
            continue
        tally["command"][0] += 1
        if x.get("always_on"):
            items.append(_item("CHECK", "command", "CMD_ALWAYS", s, f"{name} — 신호 없이 켜짐",
                               "아무 신호를 주지 않아도 1 입니다 — 안전 쪽 설계(건강 신호가 와야 풀림)인지 확인", rect, **base))
        if x.get("tied_off"):
            items.append(_item("CHECK", "command", "CMD_TIED", s, f"{name} — 상수로 막힘",
                               f"도면이 상수(FORCED INPUT)로 묶은 '{x['tied_off'][0]}' 를 뒤집어야만 섭니다", rect, **base))
        if x.get("latch") and not x.get("stoppers"):
            items.append(_item("CHECK", "command", "CMD_NO_STOP", s, f"{name} — 유지되는데 끄는 신호 없음",
                               f"버튼을 놓아도 유지됩니다 ({_lab(x.get('labels'))}) — 끄는 신호를 찾지 못했습니다", rect, **base))
        if x.get("action") in ("START", "OPEN") and not x.get("interlocks") and not x.get("always_on"):
            items.append(_item("INFO", "command", "CMD_NO_INTERLOCK", s, f"{name} — 막는 신호 없음",
                               f"켜는 조건 {_lab(x.get('labels'))} 만 있고 막는 신호(트립 · 인터록)를 찾지 못했습니다", rect, **base))
    # 반대 명령 짝
    opp = sequence.vocab().get("opposites") or []
    eqs = {}
    for x in learned.get("items") or []:
        eqs.setdefault(x["equip"], []).append(x)
    pairs = {(p["equip"], p["a"], p["b"]): p for p in learned.get("pairs") or []}
    cancel_n = 0
    for name, xs in eqs.items():
        act = {x["action"]: x for x in xs if x.get("reached") and x.get("net") is not None}
        for a, b in opp:
            if a not in act or b not in act:
                continue
            A, B = act[a], act[b]
            s = by.get(A["page"])
            if not s:
                continue
            tally["pair"][1] += 1
            tally["pair"][0] += 1
            p = pairs.get((name, a, b)) or {}
            rect = _cmd_rect(by, A)
            base = dict(row=A["row"], side="R", equip=name, action=a, peer_at=[B["page"], B["row"]])
            if p.get("both"):
                items.append(_item("CHECK", "pair", "PAIR_BOTH", s, f"{name} — {a} · {b} 동시 가능",
                                   f"{a} 조건({_lab(A.get('labels'), 3)})과 {b} 조건({_lab(B.get('labels'), 3)})을 함께 주면 "
                                   "두 명령이 함께 나갑니다 — 서로 막는 신호가 없습니다", rect, **base))
            # 자기유지된 a 에 b 조건 → a 가 꺼지는가
            if A.get("latch") and cancel_n < CANCEL_MAX and time.time() < budget:
                cancel_n += 1
                try:
                    kept = _cancel(sheets, A, B, cache)
                except Exception:
                    kept = None
                if kept:
                    items.append(_item("CHECK", "pair", "PAIR_NO_CANCEL", s, f"{name} — {b} 이 {a} 를 못 끔",
                                       f"유지된 {a} 에 {b} 조건을 주어도 {a} 가 남습니다", rect, **base))
    return {"learned": True, "commands": len(learned.get("items") or []), "reached": learned.get("reached"),
            "key": learned.get("key")}


def _cancel(sheets, A, B, cache):
    F = {int(p): dict(v) for p, v in (A.get("forces") or {}).items()}
    r = sim.simulate_bundle(sheets, F, None, A["page"], cache=cache)
    fr = (r["focus"] or {}).get("frames") or []
    if not fr or fr[-1]["values"].get(A["net"]) != 1:
        return None
    H = {p: {k: v for k, v in d.items() if not k.startswith("block:")} for p, d in F.items()}
    H = {p: d for p, d in H.items() if d}
    for p, d in (B.get("forces") or {}).items():
        H.setdefault(int(p), {}).update(d)
    r2 = sim.simulate_bundle(sheets, H, r.get("state") or {}, A["page"], cache=cache)
    f2 = (r2["focus"] or {}).get("frames") or []
    return bool(f2) and f2[-1]["values"].get(A["net"]) == 1


# ------------------------------------------------------------------ 모으기

def build(res, learned=None, cache=None, seconds=120):
    """결과(사람 값까지 얹은) + 동작 학습 → 검토 결과."""
    t0 = time.time()
    cache = cache if cache is not None else {}
    sheets = [s for s in res.get("sheets", []) if not s.get("library")]
    allsheets = sheets + list(res.get("library_sheets") or [])
    items = []
    tally = {k: [0, 0] for k in ("fromto", "line", "gate", "command", "pair")}     # [툴이 판정을 끝냄, 모두]
    _static(sheets, items, tally)
    idr = _reading(res, items)
    beh = _behavior(allsheets, learned, items, tally, cache, t0 + seconds)
    items = [it for it in items if it["page"] in {s["page"] for s in sheets}]
    rank = {c: i for i, c in enumerate(CAT_ORDER)}
    items.sort(key=lambda it: (rank[it["cat"]], it["page"], it.get("row") or 0, it["code"]))
    for i, it in enumerate(items, 1):
        it["id"] = i
    count = {c: sum(1 for it in items if it["cat"] == c) for c in CAT_ORDER}
    by_topic = {}
    for it in items:
        if it["cat"] == "INFO":
            continue
        d = by_topic.setdefault(it["topic"], {c: 0 for c in CAT_ORDER[:3]})
        d[it["cat"]] += 1
    done = sum(v[0] for v in tally.values())
    tot = sum(v[1] for v in tally.values())
    sheet_rows = []
    for s in sheets:
        mine = [it for it in items if it["page"] == s["page"]]
        sheet_rows.append({"page": s["page"], "sheet_no": s.get("sheet_no") or "", "title": s.get("title") or "",
                           **{c: sum(1 for it in mine if it["cat"] == c) for c in CAT_ORDER}})
    return {
        "version": VERSION, "at": time.time(), "seconds": round(time.time() - t0, 1),
        "sheets": len(sheets),
        "rate": {"read": idr.get("overall"), "judged": round(done / tot, 4) if tot else None,
                 "parts": {k: (round(v[0] / v[1], 4) if v[1] else None) for k, v in tally.items()},
                 "tally": {k: {"done": v[0], "all": v[1]} for k, v in tally.items()}},
        "count": count, "human": count["ERROR"] + count["CHECK"], "gaps": count["GAP"],
        "by_topic": by_topic, "behavior": beh, "per_sheet": sheet_rows, "items": items,
    }


# ------------------------------------------------------------------ 저장 (분석 폴더 review.json — 결과 · 사람 값 · 학습이 같을 때만 다시 씀)

FILE = "review.json"


def key_of(d):
    lb = BH.load(d) or {}
    return f"v{VERSION}:{BH.key_of(d)}:{lb.get('key')}"


def load(d):
    import json
    try:
        return json.loads((d / FILE).read_text(encoding="utf-8"))
    except Exception:
        return None


def build_dir(d, res=None, cache=None):
    import json
    from . import api, store
    job = d.name
    res = res or api._result(job)
    lb = BH.load(d)
    if lb and lb.get("key") != BH.key_of(d):
        lb = None                                   # 다른 결과 · 사람 값으로 배운 것 — 쓰지 않는다
    out = build(res, lb, cache if cache is not None else {})
    out["key"] = key_of(d)
    store._atomic(d / FILE, json.dumps(out, ensure_ascii=False))
    return out


PDF = "review.pdf"
PDF_META = "review_pdf.json"


def pdf_dir(d, review_out=None, include_info=False, author=""):
    """검토 결과를 원본 PDF 에 마크업한 파일 — 검토 결과와 넣는 범위가 같으면 다시 만들지 않는다."""
    import json
    from . import markup_pdf, store
    rv = review_out or load(d)
    if not rv:
        return None
    want = {"key": rv.get("key"), "at": rv.get("at"), "info": bool(include_info), "author": author or ""}
    try:
        meta = json.loads((d / PDF_META).read_text(encoding="utf-8"))
    except Exception:
        meta = None
    out = d / (PDF if not include_info else "review_info.pdf")
    if meta and out.exists() and all(meta.get(k) == v for k, v in want.items()):
        return out
    name = store.read_status(d).get("name") or d.name
    tmp = out.with_suffix(".tmp.pdf")
    info = markup_pdf.build(d / "source.pdf", rv, str(tmp), name=name, include_info=include_info, author=author)
    store._replace(tmp, out)
    store._atomic(d / PDF_META, json.dumps({**want, **info}, ensure_ascii=False))
    return out


def summary_of(rv):
    """첫 화면 · 상태 줄에 싣는 몇 숫자."""
    if not rv:
        return None
    return {"error": rv["count"].get("ERROR", 0), "check": rv["count"].get("CHECK", 0), "gap": rv["count"].get("GAP", 0),
            "judged": rv["rate"].get("judged"), "read": rv["rate"].get("read"), "learned": (rv.get("behavior") or {}).get("learned")}


def after_learning(d):
    """분석 · 동작 학습이 끝난 뒤 — 검토 결과와 마크업 PDF 를 만들어 두고 상태에 숫자를 적는다.  실패해도 분석은 그대로."""
    from . import store
    rv = build_dir(d)
    try:
        pdf_dir(d, rv)
    except Exception:
        pass
    try:
        st = store.read_status(d)
        st["review"] = summary_of(rv)
        store.write_status(d, st)
    except Exception:
        pass
    return rv


def workbook(rv, name=""):
    """같은 검토 결과를 표로 — 요약 · 항목 (사람이 판단을 적을 칸 '판단' · '메모' 를 비워 둔다)."""
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "요약"
    rate = rv.get("rate") or {}
    pct = lambda v: "" if v is None else round(v * 100, 1)
    ws.append(["LOGIC 정합성 검토", name])
    ws.append(["도면 읽기 %", pct(rate.get("read")), "툴 판정 %", pct(rate.get("judged"))])
    ws.append(["설계 오류", rv["count"].get("ERROR", 0), "설계 확인", rv["count"].get("CHECK", 0),
               "읽기 빈틈", rv["count"].get("GAP", 0), "참고", rv["count"].get("INFO", 0)])
    ws.append([])
    ws.append(["툴 판정", "끝냄", "모두", "%"])
    for k, v in (rate.get("tally") or {}).items():
        ws.append([TOPIC_KO.get(k, k), v["done"], v["all"], pct(v["done"] / v["all"]) if v["all"] else ""])
    ws.append([])
    ws.append(["시트", "쪽", "제목", "설계 오류", "설계 확인", "읽기 빈틈"])
    for r in rv.get("per_sheet") or []:
        ws.append([r["sheet_no"], r["page"], r["title"], r["ERROR"], r["CHECK"], r["GAP"]])
    ws2 = wb.create_sheet("항목")
    head = ["번호", "분류", "주제", "시트", "쪽", "행", "제목", "내용", "판단", "메모"]
    ws2.append(head)
    for c in ws2[1]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="DDE6F7")
    fill = {"ERROR": "F8D7D7", "CHECK": "FFF1C2", "GAP": "DCE3FA", "INFO": "EEEEEE"}
    tag = {"ERROR": "E", "CHECK": "C", "GAP": "G", "INFO": "I"}
    for it in rv.get("items") or []:
        ws2.append([f"{tag[it['cat']]}{it['id']}", CAT_KO[it["cat"]], TOPIC_KO.get(it["topic"], it["topic"]), it["sheet_no"],
                    it["page"], it.get("row"), it["title"], it["text"], "", ""])
        ws2.cell(ws2.max_row, 2).fill = PatternFill("solid", fgColor=fill[it["cat"]])
    for i, w in enumerate((8, 10, 10, 12, 6, 6, 40, 90, 14, 30)):
        ws2.column_dimensions[chr(65 + i)].width = w
    ws2.freeze_panes = "A2"
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
