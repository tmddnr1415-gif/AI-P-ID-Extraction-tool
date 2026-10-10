"""후보 병렬 워크북 `out/candidates_nouf1.xlsx` — 10회차 산출물.

**축을 프로그램이 고르지 않는다.**  계산 가능한 축을 나란히 놓고 사람이 고르며,
그 선택이 라벨이 되어 규칙의 근거가 된다 (10회차 프롬프트 §0).

이 스크립트는 **아무것도 새로 추적하지 않는다** — 이미 판정된 축(`evidence.axis`)과
이미 검출된 기기 라벨, 이미 읽은 DN 문자열을 모아 배치할 뿐이다.

조건 열의 값은 전부 실측이다:
  · 기기 근접   계기 중심 → 가장 가까운 기기 라벨 중심의 체비쇼프 거리가
                엔진이 쓰는 것과 같은 한계(전 행 최근접거리의 90분위) 안인가
  · 탭한 라인 DN  탭한 런에서 12.2pt 안의 `DN…` 문자열.  12.2 는 이 문서의
                DN 라벨 1,015개의 라벨→최근접 런 거리 **90분위** 실측값이다
  · DN 계층     그 페이지의 DN 값 분포에서 최대면 본류, 작으면 분기 (상수 없음)

    python3 spike/candidate_workbook.py run.json geometry.json dn.json
"""
import collections
import json
import re
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app" / "engine"))
import describe_axis as daxis  # noqa: E402

HEAD_FILL = PatternFill("solid", fgColor="EFE7D2")
PICK_FILL = PatternFill("solid", fgColor="FFF6DA")      # 사람이 채우는 칸
EXAMPLE_FILL = PatternFill("solid", fgColor="E8F0E4")   # 작성 예시 행
DIM = Font(color="9A9A9A")
BOLD = Font(bold=True)

# 후보 열 ← 판정축.  후보1 은 축이 아니라 "엔진이 쓰던 기기 축 문장"이다.
AXIS_TO_SLOT = {daxis.AX_FROMTO: 2, daxis.AX_FROM_ONLY: 3,
                daxis.AX_TO_ONLY: 4, daxis.AX_EQUIP: 5, daxis.AX_BRANCH: 6}
SLOT_LABEL = {1: "후보1 기기 축", 2: "후보2 라인 FROM-TO", 3: "후보3 라인 FROM만",
              4: "후보4 라인 TO만", 5: "후보5 기기 직결", 6: "후보6 다분기"}
PICKS = ("1", "2", "3", "4", "5", "6", "없음(직접입력)", "보류")
SCOPES = ("이 행만", "이 페이지만", "전 페이지 규칙 후보")
EXAMPLE_NOTE = "◀ 작성 예시 (지우고 쓰세요)"
DN_ATTACH_PT = 12.2      # 실측 90분위 — 머리 주석 참조
BORE = re.compile(r"^DN\s?\d{1,4}$")


def _gap(a, b):
    """두 사각형의 모서리 간격 (체비쇼프).  "윤곽 안에 있나"는 중심 거리가
    아니라 모서리 간격이다 — 기기 라벨은 계기보다 훨씬 크다."""
    dx = max(b[0] - a[2], a[0] - b[2], 0)
    dy = max(b[1] - a[3], a[1] - b[3], 0)
    return max(dx, dy)


def _dn_value(text):
    return int(re.sub(r"[^0-9]", "", text) or 0)


def conditions(rows, geo, dn_by_page):
    """행마다 조건 열.  엔진과 같은 방식으로 재고, 한계도 같은 방식으로 유도한다."""
    equip = {int(k): [(tuple(e["rect"]), e["label"]) for e in v["equipment"]]
             for k, v in geo["pages"].items()}
    nearest = {}
    for r in rows:
        rect = tuple(r["rect"] or (0, 0, 0, 0))
        cands = [(_gap(rect, er), lb) for er, lb in equip.get(r["page_no"], ())]
        nearest[r["key"]] = min(cands) if cands else None
    # 이분법으로 가르지 않는다 — 이 문서의 계기→기기 모서리 간격 분포에는
    # 자연스러운 끊김이 없다 (763행 실측: p25 134 · p50 209 · p75 325pt,
    # 기기 도달 거리 45.8pt 안은 3% 뿐).  그래서 **그 분포 자신의 사분위**로
    # 세 층을 만든다: 가까움(≤p25) · 보통(≤p75) · 멂(>p75).  상수가 없고
    # 문서마다 다시 유도된다.
    got = sorted(v[0] for v in nearest.values() if v is not None)
    pick = lambda f: got[min(int(f * len(got)), len(got) - 1)] if got else 0.0
    q25, q50, q75 = pick(.25), pick(.5), pick(.75)

    out = {}
    for r in rows:
        ev = ((r.get("axis") or {}).get("ev")) or {}
        near = nearest.get(r["key"])
        run = ev.get("run")
        dn_txt, dn_val = "", 0
        page_dns = [(_dn_value(t), t) for _rc, t in dn_by_page.get(r["page_no"], ())]
        if run:
            run_t = (run[0], run[1], run[2], run[3])
            best = None
            for rc, t in dn_by_page.get(r["page_no"], ()):
                c = ((rc[0] + rc[2]) / 2, (rc[1] + rc[3]) / 2)
                d = daxis._run_pt_d(run_t, c)
                if d <= DN_ATTACH_PT and (best is None or d < best[0]):
                    best = (d, t)
            if best:
                dn_txt = best[1]
                dn_val = _dn_value(dn_txt)
        page_max = max((v for v, _t in page_dns), default=0)
        if not dn_txt:
            tier = "미상"
        elif page_max and dn_val >= page_max:
            tier = f"본류 (페이지 최대 DN{page_max})"
        else:
            tier = f"분기 (페이지 최대 DN{page_max})"
        ends = [e for e in (ev.get("ends") or []) if e]
        if any(e.get("via") == "mid" for e in ends):
            nature = "중간 접합 경유"
        elif any(e["kind"] == "CONN" for e in ends):
            nature = "목적지 직행"
        elif ev.get("touch") or any(e["kind"] == "EQUIP" for e in ends):
            nature = "기기 접촉"
        else:
            nature = "미상"
        if near is None:
            tier_near = "기기 없음"
        elif near[0] <= q25:
            tier_near = "가까움"
        elif near[0] <= q75:
            tier_near = "보통"
        else:
            tier_near = "멂"
        out[r["key"]] = {
            "near": tier_near,
            "near_label": near[1] if near else "",
            "near_pt": round(near[0], 1) if near else "",
            "dn": dn_txt, "tier": tier, "nature": nature,
            "held": "보류" if (r.get("axis") or {}).get("withheld") else "",
        }
    return out, (round(q25, 1), round(q50, 1), round(q75, 1))


def candidates_of(r):
    """행이 **계산할 수 있는** 문장만 슬롯에 넣는다.  나머지는 공란이다."""
    ax = r.get("axis") or {}
    slots = {i: "" for i in range(1, 7)}
    # 후보1 = 엔진의 기기 축 문장.  신규문형이 덮은 행은 그 이전 문장이 그것이다.
    slots[1] = (ax.get("old_description") if ax.get("source") == "신규문형"
                else r.get("description")) or ""
    slot = AXIS_TO_SLOT.get(ax.get("axis"))
    if slot and ax.get("sentence"):
        slots[slot] = ax["sentence"]
    return slots


def guide_sheet(wb, n_rows, n_multi, q25, q75):
    ws = wb.create_sheet("0. 작성 안내", 0)
    W = ws.append
    W(["후보 병렬 워크북 — 축을 사람이 고른다"])
    W([])
    W(["· 프로그램은 계산 가능한 축을 나란히 놓기만 합니다. 어느 축이 맞는지는 "
       "도면을 보는 사람이 1초에 압니다."])
    W([f"· {n_rows}행 중 **후보가 2개 이상인 {n_multi}행**만 고를 것이 있습니다. "
       f"나머지는 옅게 처리했습니다."])
    W(["· 선택은 라벨이 됩니다. '적용 범위'를 '전 페이지 규칙 후보'로 두면 "
       "시트3에 모여 규칙의 근거가 됩니다."])
    W([])
    W(["열 설명"]); ws.cell(ws.max_row, 1).font = BOLD
    for k, v in (
        ("현재 Description", "지금 Excel 산출물에 나가는 값"),
        ("판정축", "⓪벤더 ①기기직결 ②FROM-TO ②a출발만 ②b도착만 ③다분기 ④판정불가"),
        ("후보1 기기 축", "기기명 + 위치어 + 변수어 — 엔진이 쓰던 문장"),
        ("후보2 라인 FROM-TO", "FROM {출발} TO {도착} {TYPE풀네임} {Suffix}"),
        ("후보3 라인 FROM만", "FROM {출발} {TYPE풀네임} {Suffix}"),
        ("후보4 라인 TO만", "TO {도착} {TYPE풀네임} {Suffix}"),
        ("후보5 기기 직결", "{기기명·SKID} {TYPE풀네임} {Suffix}"),
        ("후보6 다분기", "{상류} DISCHARGE {TYPE풀네임} {Suffix}"),
        ("기기 근접", f"가장 가까운 기기 라벨까지의 **모서리 간격** 층 — "
                     f"가까움 ≤{q25}pt · 보통 ≤{q75}pt · 멂 >{q75}pt "
                     f"(이 문서 763행 실측 사분위)"),
        ("가까운 기기명 · 거리", "그 라벨과 pt 거리"),
        ("탭한 라인 DN", "탭한 배관에서 12.2pt 안의 DN 문자열 (12.2 = DN 라벨 "
                        "1,015개의 라벨→배관 거리 90분위)"),
        ("DN 계층", "그 페이지의 DN 분포에서 최대면 본류, 작으면 분기"),
        ("라인 성격", "목적지 직행 / 중간 접합 경유 / 기기 접촉 / 미상"),
        ("보류 여부", "판정은 섰으나 현행 문장이 있어 적용하지 않은 행(8·9회차 규칙)"),
    ):
        W([k, v])
    W([])
    W(["작성 순서"]); ws.cell(ws.max_row, 1).font = BOLD
    for i, t in enumerate((
        "후보가 2개 이상인 행만 봅니다 (진하게 표시된 행).",
        "도면을 보고 맞는 후보 번호를 '선택 후보'에서 고릅니다.",
        "어느 후보도 아니면 '없음(직접입력)' 을 고르고 '직접 입력 문장'에 씁니다.",
        "'적용 범위'를 반드시 고릅니다 — 이 행만 / 이 페이지만 / 전 페이지 규칙 후보.",
        "'이유'에 한 줄. 규칙 후보일 때는 **조건**을 적습니다 "
        "(예: 기기가 없고 블로다운 분기 라인일 때).",
    ), 1):
        W([f"{i}.", t])
    W([])
    W(["작성 예시 — 시트1 의 초록색 3행에 실제로 채워 두었습니다. "
       "지우고 쓰세요. 읽어들이기는 '작성 예시' 메모가 있는 행을 건너뜁니다."])
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 96
    for row in ws.iter_rows():
        for c in row:
            c.alignment = Alignment(vertical="top", wrap_text=True)
    ws["A1"].font = Font(bold=True, size=13)
    return ws


def build(run_path, geo_path, dn_path, out_path=None):
    run = json.load(open(run_path))
    rows = sorted(run["rows"], key=lambda r: (
        r["page_no"], round((r["rect"] or [0, 0])[1]),
        round((r["rect"] or [0, 0])[0]), r["key"]))
    geo = json.load(open(geo_path))
    dn_by_page = {int(k): [(tuple(rc), t) for rc, t in v]
                  for k, v in json.load(open(dn_path)).items()}
    cond, (q25, q50, q75) = conditions(rows, geo, dn_by_page)

    wb = Workbook()
    ws = wb.active
    ws.title = "1. 후보와 선택"
    head = ["No", "P&ID No.", "Page", "산출물", "TYPE", "Q'ty",
            "현재 Description", "판정축",
            "후보1 기기 축", "후보2 라인 FROM-TO", "후보3 라인 FROM만",
            "후보4 라인 TO만", "후보5 기기 직결", "후보6 다분기", "후보 수",
            "기기 근접", "가까운 기기명", "기기까지 거리(pt)", "탭한 라인 DN",
            "DN 계층", "라인 성격", "보류 여부",
            "선택 후보", "직접 입력 문장", "적용 범위", "이유", "메모", "key"]
    ws.append(head)
    for c in ws[1]:
        c.font = BOLD
        c.fill = HEAD_FILL
        c.alignment = Alignment(vertical="center", wrap_text=True)
    dv_pick = DataValidation(type="list", formula1='"%s"' % ",".join(PICKS),
                             allow_blank=True, showDropDown=False)
    dv_scope = DataValidation(type="list", formula1='"%s"' % ",".join(SCOPES),
                              allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv_pick)
    ws.add_data_validation(dv_scope)

    counts = collections.Counter()
    multi_keys = []
    for i, r in enumerate(rows, 1):
        ax = r.get("axis") or {}
        slots = candidates_of(r)
        n = sum(1 for v in slots.values() if v)
        counts[min(n, 3)] += 1
        if n >= 2:
            multi_keys.append(r["key"])
        c = cond[r["key"]]
        axis_txt = (f'{ax.get("axis", "")}'
                    + (f' · {ax.get("source")}' if ax.get("source") else ""))
        ws.append([i, r.get("drawing_no") or "", r["page_no"], r["tab"],
                   r.get("type") or r.get("valve_type") or "", r.get("qty"),
                   r.get("description") or "", axis_txt,
                   slots[1], slots[2], slots[3], slots[4], slots[5], slots[6], n,
                   c["near"], c["near_label"], c["near_pt"], c["dn"],
                   c["tier"], c["nature"], c["held"],
                   "", "", "", "", "", r["key"]])
        row_i = ws.max_row
        for col in (23, 24, 25, 26, 27):
            ws.cell(row_i, col).fill = PICK_FILL
        dv_pick.add(ws.cell(row_i, 23))
        dv_scope.add(ws.cell(row_i, 25))
        if n < 2:                      # 고를 것이 없는 행은 옅게
            for col in range(1, 23):
                ws.cell(row_i, col).font = DIM
    widths = (5, 22, 6, 10, 7, 5, 44, 16, 44, 46, 40, 40, 40, 40, 6,
              9, 26, 12, 12, 22, 16, 8, 14, 40, 18, 40, 26, 18)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(head))}{ws.max_row}"

    examples = fill_examples(ws, rows)

    # 시트2 집계
    ws2 = wb.create_sheet("2. 집계")
    ws2.append(["후보 개수", "행"])
    for k, label in ((0, "0개"), (1, "1개"), (2, "2개"), (3, "3개 이상")):
        ws2.append([label, counts.get(k, 0)])
    ws2.append(["**후보 2개 이상 (사람이 고를 대상)**", len(multi_keys)])
    ws2.append([])
    ws2.append(["기기 근접 × 판정축 교차표"])
    axes = ["⓪", "①", "②", "②a", "②b", "③", "④"]
    ws2.append(["기기 근접"] + axes + ["합계"])
    cross = collections.Counter()
    for r in rows:
        cross[(cond[r["key"]]["near"], (r.get("axis") or {}).get("axis"))] += 1
    for near in ("가까움", "보통", "멂", "기기 없음"):
        line = [cross[(near, a)] for a in axes]
        ws2.append([near] + line + [sum(line)])
    ws2.append(["합계"] + [sum(cross[(n, a)] for n in
                               ("가까움", "보통", "멂", "기기 없음"))
                          for a in axes] + [len(rows)])
    ws2.append([])
    ws2.append(["보류 53행 (8·9회차 규칙으로 적용하지 않은 행) 의 기기 근접"])
    held_cross = collections.Counter(
        (cond[r["key"]]["near"], (r.get("axis") or {}).get("axis"))
        for r in rows if cond[r["key"]]["held"])
    ws2.append(["기기 근접"] + axes + ["합계"])
    for near in ("가까움", "보통", "멂", "기기 없음"):
        line = [held_cross[(near, a)] for a in axes]
        ws2.append([near] + line + [sum(line)])
    ws2.append([])
    ws2.append([f"기기 근접 층 — 이 문서 실측 사분위: 가까움 ≤{q25}pt · "
                f"보통 ≤{q75}pt · 멂 >{q75}pt (중앙값 {q50}pt)"])
    ws2.append(["이분법을 쓰지 않은 이유: 계기→기기 모서리 간격 분포에 "
                "자연스러운 끊김이 없습니다 (기기 도달 45.8pt 안은 3%뿐)"])
    ws2.append([f"DN 라벨 부착 한계 {DN_ATTACH_PT}pt (DN 라벨 1,015개의 "
                f"라벨→배관 거리 90분위 · 실측)"])
    for c in ws2[1]:
        c.font = BOLD
    ws2.column_dimensions["A"].width = 40
    for col in "BCDEFGHI":
        ws2.column_dimensions[col].width = 8

    # 시트3 규칙 후보 — 사람이 채우면 모인다
    ws3 = wb.create_sheet("3. 규칙 후보")
    ws3.append(["Page", "P&ID No.", "TYPE", "선택 후보", "선택 문장", "이유",
                "기기 근접", "기기까지 거리(pt)", "탭한 라인 DN", "DN 계층",
                "라인 성격", "판정축", "key"])
    for c in ws3[1]:
        c.font = BOLD
        c.fill = HEAD_FILL
    collected = collect_rules(ws, ws3)
    if not collected:
        ws3.append(["— 아직 없습니다. 시트1 에서 '적용 범위' 를 "
                    "'전 페이지 규칙 후보' 로 고르면 여기에 모입니다 "
                    "(워크북을 다시 생성하거나 읽어들이기를 돌릴 때)."])
    for col, w in zip("ABCDEFGHIJKLM",
                      (6, 22, 7, 14, 46, 40, 9, 12, 12, 22, 16, 10, 18)):
        ws3.column_dimensions[col].width = w

    out = Path(out_path or ROOT / "out" / "candidates_nouf1.xlsx")
    out.parent.mkdir(exist_ok=True)
    guide_sheet(wb, len(rows), len(multi_keys), q25, q75)
    wb.save(out)
    return out, {"rows": len(rows), "multi": len(multi_keys),
                 "counts": dict(counts), "quartiles": [q25, q50, q75],
                 "examples": examples,
                 "cross": {f"{n}·{a}": v for (n, a), v in cross.items()}}


def fill_examples(ws, rows):
    """예시 3행 — **실제 데이터 행**에 채운다.  가상 행을 만들지 않는다."""
    by_key = {}
    for i, r in enumerate(rows, 2):          # 머리행 다음부터
        by_key[r["key"]] = i
    picks = []

    def find(pred):
        for r in rows:
            if pred(r):
                return r
        return None

    # A — 라인 축이 이기는 경우: p6 클라우드 TT 첫 행
    a = find(lambda r: r.get("drawing_no") == "D00P-10LBA10-M05-0001"
             and r.get("type") == "TIT" and round((r["rect"] or [0, 0])[1]) == 600)
    # B — 기기 축이 이기는 경우: p33 PDIT (9회차 후퇴 사례)
    b = find(lambda r: r["page_no"] == 33 and r.get("type") == "PDIT"
             and (r.get("axis") or {}).get("withheld"))
    # C — 어느 후보도 맞지 않는 경우: 커넥터 문구가 두 화살표 라벨을 한 줄로
    #     읽어 후보가 그대로 쓸 수 없는 행 (p8, `... BD TANK TO CLEAN DRAIN TANK`)
    c = find(lambda r: "BD TANK TO CLEAN DRAIN TANK"
             in ((r.get("axis") or {}).get("sentence") or ""))
    for r, pick, direct, scope, why in (
        (a, "4", "", "전 페이지 규칙 후보",
         "블로다운 분기 라인이고 근처에 기기가 없다. 목적지가 곧 정체성이다"),
        (b, "1", "", "전 페이지 규칙 후보",
         "펌프 흡입측이고 근처에 기기가 있다. 기기와 위치가 정체성이다"),
        (c, "없음(직접입력)", "TO HRSG#11 BD TANK TEMPERATURE TRANSMITTER A",
         "이 행만",
         "도면 표기가 한 덩어리로 인쇄돼 후보로 잡히지 않는다 "
         "(화살표 두 개의 라벨이 한 줄로 읽힘)"),
    ):
        if r is None:
            continue
        i = by_key[r["key"]]
        ws.cell(i, 23).value = pick
        ws.cell(i, 24).value = direct
        ws.cell(i, 25).value = scope
        ws.cell(i, 26).value = why
        ws.cell(i, 27).value = EXAMPLE_NOTE
        for col in range(1, 28):
            ws.cell(i, col).fill = EXAMPLE_FILL
        picks.append({"row": i, "key": r["key"], "page": r["page_no"],
                      "type": r.get("type") or r.get("valve_type"),
                      "pick": pick, "scope": scope})
    return picks


def collect_rules(ws, ws3) -> int:
    """시트1 에서 '전 페이지 규칙 후보' 로 표시된 행을 시트3 에 모은다.

    '작성 예시' 행은 건너뛴다 — 읽어들이기와 같은 규칙이다.
    """
    n = 0
    for i in range(2, ws.max_row + 1):
        if ws.cell(i, 25).value != "전 페이지 규칙 후보":
            continue
        if EXAMPLE_NOTE in str(ws.cell(i, 27).value or ""):
            continue
        pick = str(ws.cell(i, 23).value or "")
        sentence = (ws.cell(i, 24).value if pick.startswith("없음")
                    else ws.cell(i, 8 + int(pick)).value if pick.isdigit() else "")
        ws3.append([ws.cell(i, 3).value, ws.cell(i, 2).value, ws.cell(i, 5).value,
                    pick, sentence, ws.cell(i, 26).value, ws.cell(i, 16).value,
                    ws.cell(i, 18).value, ws.cell(i, 19).value,
                    ws.cell(i, 20).value, ws.cell(i, 21).value,
                    ws.cell(i, 8).value, ws.cell(i, 28).value])
        n += 1
    return n


if __name__ == "__main__":
    out, info = build(sys.argv[1], sys.argv[2], sys.argv[3])
    print("저장:", out)
    print(json.dumps(info, ensure_ascii=False)[:600])
