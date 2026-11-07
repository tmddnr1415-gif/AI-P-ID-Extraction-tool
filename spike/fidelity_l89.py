"""L89 — 'Logic 분석에서 불러와 똑같이 그리기' 의 정확도.

시트마다: 분석 결과 A (원본 PDF 를 분석기가 읽은 것) → 그림으로 들여오기 (draw.from_sheet) → 그림을 PDF 로 → 같은 분석기로 다시 읽기 A'.
A 와 A' 를 견준다 (자리는 draw.sheet_maps — 들여오기와 같은 변환으로 A 를 그림 자리로 옮겨 견준다).  잣대는 아래에 고정하고 바꾸지 않는다.

  블록 B   A 의 블록 ↔ A' 의 블록: 가운데가 0.5 행 안에서 가장 가까운 것끼리 짝.  맞음 = 짝이 있고 동작이 같다
           (분석기가 매긴 동작 logic 이 있으면 그것이 같다 — ALM/ANN · PUSH BUTTON/PB 처럼 이름만 다른 것은 같다 · 없으면 기능 이름 func 이 같다).
           정확도 = 2·맞음 / (|A| + |A'|).   (매크로 상자 안의 운전 칸은 양쪽 다 뺀다 — 그림은 그것을 매크로 단자 이름으로 옮긴다)
  표 R     A 의 표 칸(FROM/TO · TAG · 설명) ↔ A' 의 같은 행(옮긴 번호) 같은 칸: 글이 같은가 (공백 · 대소문자 무시).
           칸 = 둘 중 하나라도 글이 있는 칸.  개정 표시(숫자 한두 자리만 있는 FM/TO)는 들여오기처럼 뺀다.
  연결 C   단자 = 블록 단자 + 신호 행.  블록 단자는 짝지은 블록끼리 같은 방향 · 가장 가까운 자리(0.5 행 안)가 같은 단자
           (분석기가 같은 점을 여러 번 적은 겹친 단자는 하나로).  맞음 = 그 단자가 A' 에서 A 와 꼭 같은 단자들과 한 그물.
           정확도 = 맞은 단자 / 모든 단자 (둘 중 하나에라도 있는 단자).
  선 V     원본 쪽 LOGIC 영역의 선(벡터) ↔ 그림 PDF 의 선: 0.5pt 마다 점을 찍어 상대 선이 0.1 행 안에 있으면 덮임.
           LOGIC 영역 = 좌우 LOGIC 경계(LX0 · LX1) 안 × 표 맨 위(TOP)부터 그 장의 마지막 행 아래까지 — 선은 이 사각형으로 잘라 본다.
           재현율 · 정밀도의 조화 평균 (길이 가중).
  글 W     원본 쪽 LOGIC 영역의 낱말 ↔ 그림 PDF 의 낱말: 같은 낱말이 0.6 행 안에.  조화 평균.
           기호(블록) 상자 안의 글은 양쪽 다 뺀다 — 기호 모양의 일부이고 그 뜻은 블록 B 가 잰다.  남는 것은 LOGIC 영역의 자유 글
           (단자 이름 · 상수 · 설정값 · 주석 · 시간 글 …).
  두 층:   '되읽기'(위 · 그림을 PDF 로 내보내 분석기가 다시 읽은 것)와 '직접'(그림을 프로그램이 이해한 것 — 시뮬레이션이 쓰는 draw_sim.to_sheet)
           을 따로 센다 (B · R · C).  선 · 글은 되읽기 PDF 로만.

  python3 spike/fidelity_l89.py <result.json> <원본 PDF> <out.json> [일꾼 수=4] [시트 차례 a:b]
"""
import json, math, os, re, sys, tempfile, time
from collections import defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.logic import draw  # noqa: E402

RES = None
PDF = None
FORM = ""
P = draw.PITCH
L = draw.layout(draw.N_DEFAULT)


def norm(t):
    return re.sub(r"\s+", "", str(t or "")).upper()


def _init(res_path, pdf_path):
    global RES, PDF, FORM
    from app.logic import draw_sets
    RES = json.load(open(res_path))
    PDF = pdf_path
    FORM = draw_sets.source_form(RES)


def in_macro(b, macro_boxes):
    bb = b["bbox"]
    return b.get("func") != "MACRO" and any(m[0] - 1 <= bb[0] and bb[2] <= m[2] + 1 and m[1] - 1 <= bb[1] and bb[3] <= m[3] + 1 for m in macro_boxes)


def blocks_of(s, X=None, Y=None):
    bl = s.get("blocks") or {}
    mbox = [b["bbox"] for b in bl.values() if b.get("func") == "MACRO"]
    out = {}
    for k, b in bl.items():
        if in_macro(b, mbox):
            continue
        x0, y0, x1, y1 = b["bbox"]
        c = ((X(x0) + X(x1)) / 2, (Y(y0) + Y(y1)) / 2) if X else ((x0 + x1) / 2, (y0 + y1) / 2)
        out[k] = {"c": c, "func": b.get("func") or "", "logic": b.get("logic") or "", "bb": [X(x0), Y(y0), X(x1), Y(y1)] if X else [x0, y0, x1, y1]}
    return out


def same(a, b):
    return a["logic"] == b["logic"] if a["logic"] and b["logic"] else a["func"] == b["func"]


def match_blocks(A, B):
    """가운데 거리 0.5 행 안 · 가까운 것부터 하나씩."""
    pairs = []
    for ka, a in A.items():
        for kb, b in B.items():
            d = math.hypot(a["c"][0] - b["c"][0], a["c"][1] - b["c"][1])
            if d <= 0.5 * P:
                pairs.append((d, ka, kb))
    pairs.sort()
    ua, ub, m = set(), set(), {}
    for d, ka, kb in pairs:
        if ka in ua or kb in ub:
            continue
        ua.add(ka); ub.add(kb); m[ka] = kb
    return m


def rows_of(s, rn=None):
    out = {}
    for r in s.get("table") or []:
        n = r.get("n")
        if not n:
            continue
        v = (r.get("fm") or r.get("to") or "").strip()
        if v and v.isdigit() and len(v) <= 2 and not (r.get("desc") or r.get("kks") or r.get("abv")):
            continue                                  # 개정 표시 — 들여오기와 같은 규칙
        side = r["side"]
        key = (side, rn(n) if rn else n)
        ft = "fm" if side == "L" else "to"
        cur = out.setdefault(key, {})
        for f, src in ((ft, r.get(ft)), ("kks", r.get("kks") or r.get("abv")), ("desc", r.get("desc"))):
            if src:
                cur[f] = norm(src)
    return out


def ports_of(s, X=None, Y=None):
    """블록마다 단자 (같은 자리 · 같은 그물 · 같은 방향의 겹친 단자는 하나 — 분석기가 같은 점을 두 번 적은 것)."""
    blocks = s.get("blocks") or {}
    mbox = [b["bbox"] for b in blocks.values() if b.get("func") == "MACRO"]
    out = defaultdict(list); seen = set()
    for pt in s.get("ports") or []:
        b = blocks.get(pt["block"])
        if not b or in_macro(b, mbox) or pt.get("net") is None:
            continue
        x, y = pt["at"]
        if X:
            x, y = X(x), Y(y)
        k = (pt["block"], pt["dir"], str(pt["net"]), round(x, 1), round(y, 1))
        if k in seen:
            continue
        seen.add(k)
        out[pt["block"]].append({"dir": pt["dir"], "net": str(pt["net"]), "at": (x, y)})
    return out


def terminals2(sa, sb, M, m):
    """두 시트의 단자를 같은 이름으로 — 짝지은 블록끼리 같은 방향 · 가장 가까운 자리(0.5 행 안)의 단자가 같은 단자.  행은 (쪽 · 옮긴 번호)."""
    pa, pb = ports_of(sa, M["X"], M["Y"]), ports_of(sb)
    ta, tb = defaultdict(set), defaultdict(set)
    for ka, lst in pa.items():
        kb = m.get(ka); lb = pb.get(kb, []) if kb else []
        pairs = sorted((math.hypot(q["at"][0] - r["at"][0], q["at"][1] - r["at"][1]), i, j) for i, q in enumerate(lst) for j, r in enumerate(lb) if q["dir"] == r["dir"])
        ui, uj = {}, set()
        for d, i, j in pairs:
            if d > 0.5 * P or i in ui or j in uj:
                continue
            ui[i] = j; uj.add(j)
        for i, q in enumerate(lst):
            ta[q["net"]].add(("P", ka, i) if i not in ui else ("P", ka, "=", ui[i]))
        for j, r in enumerate(lb):
            tb[r["net"]].add(("P", ka, "=", j) if j in uj else ("Q", kb, j))
    inv = set(m.values())
    for kb, lb in pb.items():
        if kb in inv:
            continue
        for j, r in enumerate(lb):
            tb[r["net"]].add(("Q", kb, j))
    for r in sa.get("rows") or []:
        if r.get("net") is not None and r.get("n"):
            ta[str(r["net"])].add(("R", r["side"], M["rn"](r["n"])))
    for r in sb.get("rows") or []:
        if r.get("net") is not None and r.get("n"):
            tb[str(r["net"])].add(("R", r["side"], r["n"]))

    def by_term(nets):
        out = {}
        for ts in nets.values():
            fs = frozenset(ts)
            for t in ts:
                out[t] = fs
        return out
    return by_term(ta), by_term(tb)


def segs_of(page, X=None, Y=None):
    out = []
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] == "l":
                pts = [(it[1].x, it[1].y), (it[2].x, it[2].y)]
            elif it[0] == "re":
                r = it[1]; pts = [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1), (r.x0, r.y0)]
            elif it[0] == "qu":
                q = it[1]; pts = [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y), (q.ul.x, q.ul.y)]
            else:
                continue
            if X:
                pts = [(X(x), Y(y)) for x, y in pts]
            for a, b in zip(pts, pts[1:]):
                out.append((a, b))
    return out


def clip_area(segs, N=None):
    """LOGIC 영역(LX0..LX1 × TOP..그 장의 마지막 행 아래)으로 선을 잘라 낸다 — 표 · 테두리 · 타이틀블록은 영역 밖."""
    x0, x1 = L["LX0"] + 0.5, L["LX1"] - 0.5
    y0, y1 = L["TOP"] + 0.5, L["TOP"] + (N or draw.N_DEFAULT) * P - 0.5
    out = []
    for a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        t0, t1 = 0.0, 1.0
        ok = True
        for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if abs(p_) < 1e-12:
                if q_ < 0:
                    ok = False; break
                continue
            r = q_ / p_
            if p_ < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                ok = False; break
        if not ok:
            continue
        c = (a[0] + t0 * dx, a[1] + t0 * dy); d = (a[0] + t1 * dx, a[1] + t1 * dy)
        if math.hypot(d[0] - c[0], d[1] - c[1]) > 0.05:
            out.append((c, d))
    return out


def coverage(src, dst, tol):
    """src 선 길이 중 dst 선이 tol 안에 있는 몫 (0.5pt 마다 점)."""
    g = defaultdict(list); cell = 4.0
    for a, b in dst:
        for gx in range(int(min(a[0], b[0]) // cell) - 1, int(max(a[0], b[0]) // cell) + 2):
            for gy in range(int(min(a[1], b[1]) // cell) - 1, int(max(a[1], b[1]) // cell) + 2):
                g[(gx, gy)].append((a, b))

    def near(p):
        for a, b in g.get((int(p[0] // cell), int(p[1] // cell)), ()):
            dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
            t = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
            if math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy) <= tol:
                return True
        return False
    tot = cov = 0.0
    for a, b in src:
        ln = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, int(ln / 0.5))
        for i in range(n):
            t = (i + 0.5) / n
            if near((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))):
                cov += ln / n
        tot += ln
    return cov, tot


def words_of(page, X=None, Y=None, inside=()):
    """LOGIC 영역의 낱말 (글 · 가운데).  inside = 기호 상자들 — 그 안의 글은 뺀다 (그림 자리)."""
    out = []
    for w in page.get_text("words"):
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        if X:
            cx, cy = X(cx), Y(cy)
        if any(bb[0] - 0.5 <= cx <= bb[2] + 0.5 and bb[1] - 0.5 <= cy <= bb[3] + 0.5 for bb in inside):
            continue
        if L["LX0"] + 0.5 <= cx <= L["LX1"] - 0.5 and L["TOP"] <= cy <= L["TOP"] + 64 * P and norm(w[4]):
            out.append((norm(w[4]), cx, cy))
    return out


def word_match(A, B):
    used = set(); m = 0
    by = defaultdict(list)
    for j, (t, x, y) in enumerate(B):
        by[t].append(j)
    for t, x, y in A:
        best = None
        for j in by.get(t, ()):
            if j in used:
                continue
            d = math.hypot(B[j][1] - x, B[j][2] - y)
            if d <= 0.6 * P and (best is None or d < best[0]):
                best = (d, j)
        if best:
            used.add(best[1]); m += 1
    return m


_SRC = None


def _src():
    global _SRC
    if _SRC is None:
        import pymupdf
        _SRC = pymupdf.open(PDF)
    return _SRC


def one(i):
    import pymupdf
    from app.logic import analyse as AN
    s = RES["sheets"][i]
    t0 = time.time()
    out = {"i": i, "page": s["page"], "sheet_no": s.get("sheet_no") or ""}
    try:
        M = draw.sheet_maps(s)
        spage = _src()[s["page"] - 1]
        doc = draw.from_sheet(s, s.get("sheet_no") or f"p{s['page']}", "fidelity", page=spage)   # 들여오기와 같이 원본 PDF 쪽을 준다
        if FORM:
            doc["form"] = FORM                            # 들여오기(묶음 · 한 장)와 같은 양식 — draw_sets.source_form
        doc = {**doc, **draw.clean(doc)}
        pdf = draw.to_pdf(doc)
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "d.pdf")
            open(p, "wb").write(pdf)
            try:
                r2 = AN.analyse(p)
                s2 = r2["sheets"][0] if r2.get("sheets") else None
            except Exception as e:
                s2 = None; out["why"] = repr(e)[:160]
            dpage = pymupdf.open(p)[0]
            # 선 · 글
            sseg = clip_area(segs_of(spage, M["X"], M["Y"]), M["N"]); dseg = clip_area(segs_of(dpage), M["N"])
            c1, t1 = coverage(sseg, dseg, 0.1 * P); c2, t2 = coverage(dseg, sseg, 0.1 * P)
            out["V"] = [c1, t1, c2, t2]
            sbox = [[M["X"](b["bbox"][0]), M["Y"](b["bbox"][1]), M["X"](b["bbox"][2]), M["Y"](b["bbox"][3])] for b in (s.get("blocks") or {}).values()]
            dbox = []
            for b in doc["blocks"]:
                if (draw.SYMBOLS.get(b["kind"]) or {}).get("note"):
                    continue
                g = draw.block_geometry(b)
                dbox.append(g["box"] or ([g["circle"][0] - g["circle"][2], g["circle"][1] - g["circle"][2], g["circle"][0] + g["circle"][2], g["circle"][1] + g["circle"][2]] if g.get("circle") else [b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]]))
            sw, dw = words_of(spage, M["X"], M["Y"], inside=sbox), words_of(dpage, inside=dbox)
            out["W"] = [word_match(sw, dw), len(sw), len(dw)]
        from app.logic import draw_sim
        s3 = draw_sim.to_sheet({**doc, "id": "fid"}, 1)
        out.update({k + "d": v for k, v in compare(s, M, s3).items()})
        if s2 is None:
            A = blocks_of(s, M["X"], M["Y"])
            out.update({"B": [0, len(A), 0], "R": [0, 1], "C": [0, 1]})
            return out
        out.update(compare(s, M, s2))
    except Exception as e:
        out["err"] = repr(e)[:200]
    out["sec"] = round(time.time() - t0, 2)
    return out


def compare(s, M, s2):
    out = {}
    if True:
        A, B = blocks_of(s, M["X"], M["Y"]), blocks_of(s2)
        m = match_blocks(A, B)
        ok = sum(1 for ka, kb in m.items() if same(A[ka], B[kb]))
        out["B"] = [ok, len(A), len(B)]
        out["Bbad"] = [[ka, A[ka]["func"], A[ka]["logic"], (B[m[ka]]["func"], B[m[ka]]["logic"]) if ka in m else None] for ka in A if ka not in m or not same(A[ka], B[m[ka]])][:12]
        out["Bextra"] = [[kb, B[kb]["func"]] for kb in B if kb not in set(m.values())][:8]
        ra, rb = rows_of(s, M["rn"]), rows_of(s2)
        tot = good = 0; rbad = []
        for key in set(ra) | set(rb):
            fa, fb = ra.get(key, {}), rb.get(key, {})
            for f in set(fa) | set(fb):
                tot += 1
                if fa.get(f) == fb.get(f):
                    good += 1
                elif len(rbad) < 10:
                    rbad.append([key[0], key[1], f, fa.get(f), fb.get(f)])
        out["R"] = [good, tot]; out["Rbad"] = rbad
        ta, tb = terminals2(s, s2, M, m)
        allt = set(ta) | set(tb)
        cg = sum(1 for t in allt if t in ta and t in tb and ta[t] == tb[t])
        out["C"] = [cg, len(allt)]
        out["Cbad"] = [[str(t), sorted(map(str, ta.get(t, ())))[:4], sorted(map(str, tb.get(t, ())))[:4]] for t in allt if not (t in ta and t in tb and ta[t] == tb[t])][:8]
        pa = {frozenset((x, y)) for fs in set(ta.values()) for x in fs for y in fs if x != y}
        pb = {frozenset((x, y)) for fs in set(tb.values()) for x in fs for y in fs if x != y}
        out["Cp"] = [len(pa & pb), len(pa), len(pb)]                 # 짝 단위 (진단용)
    return out


def summarize(rows):
    def f1(a, b, c):
        return 2 * a / (b + c) if (b + c) else 1.0
    B = [sum(r["B"][k] for r in rows if "B" in r) for k in range(3)]
    R = [sum(r["R"][k] for r in rows if "R" in r) for k in range(2)]
    C = [sum(r["C"][k] for r in rows if "C" in r) for k in range(2)]
    Bd = [sum(r["Bd"][k] for r in rows if "Bd" in r) for k in range(3)]
    Rd = [sum(r["Rd"][k] for r in rows if "Rd" in r) for k in range(2)]
    Cd = [sum(r["Cd"][k] for r in rows if "Cd" in r) for k in range(2)]
    Cp = [sum(r["Cp"][k] for r in rows if "Cp" in r) for k in range(3)]
    V = [sum(r["V"][k] for r in rows if "V" in r) for k in range(4)]
    W = [sum(r["W"][k] for r in rows if "W" in r) for k in range(3)]
    rec, pre = V[0] / max(1e-9, V[1]), V[2] / max(1e-9, V[3])
    wr, wp = W[0] / max(1, W[1]), W[0] / max(1, W[2])
    return {"sheets": len(rows), "errors": sum(1 for r in rows if r.get("err") or r.get("why")),
            "B": round(100 * f1(B[0], B[1], B[2]), 2), "B_n": B,
            "R": round(100 * R[0] / max(1, R[1]), 2), "R_n": R,
            "C": round(100 * C[0] / max(1, C[1]), 2), "C_n": C,
            "V": round(100 * 2 * rec * pre / max(1e-9, rec + pre), 2), "V_recall": round(100 * rec, 2), "V_precision": round(100 * pre, 2),
            "W": round(100 * 2 * wr * wp / max(1e-9, wr + wp), 2), "W_recall": round(100 * wr, 2), "W_precision": round(100 * wp, 2),
            "C_pairs": round(100 * f1(Cp[0], Cp[1], Cp[2]), 2),
            "직접": {"B": round(100 * f1(Bd[0], Bd[1], Bd[2]), 2), "R": round(100 * Rd[0] / max(1, Rd[1]), 2), "C": round(100 * Cd[0] / max(1, Cd[1]), 2)}}


if __name__ == "__main__":
    res_path, pdf_path, out_path = sys.argv[1:4]
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    n = len(json.load(open(res_path))["sheets"])
    a, b = (map(int, sys.argv[5].split(":")) if len(sys.argv) > 5 else (0, n))
    t = time.time()
    with Pool(workers, initializer=_init, initargs=(res_path, pdf_path)) as pool:
        rows = []
        for k, r in enumerate(pool.imap_unordered(one, range(a, min(b, n)), chunksize=2)):
            rows.append(r)
            if (k + 1) % 50 == 0:
                print(f"{k + 1}/{min(b, n) - a} · {time.time() - t:.0f}s", flush=True)
    rows.sort(key=lambda r: r["i"])
    sm = summarize(rows)
    json.dump({"summary": sm, "rows": rows}, open(out_path, "w"), ensure_ascii=False)
    print(json.dumps(sm, ensure_ascii=False, indent=1))
    print(f"{time.time() - t:.0f}s")
