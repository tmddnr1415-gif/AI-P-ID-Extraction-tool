"""라벨링 워크북 `out/label_nouf1.xlsx` — 5회차 2부 산출물.

시트1 추출행 824 — 사람이 O/X 로 라벨링한다.  "판정 초안"은 프로그램의
  의견이다: 발주처 대응행과 식별 판정이 통하면 O, 막히면 X, 대응행이 없으면
  공란(드롭다운으로 사람이 채움).  "문형 출처"는 어느 규칙의 산물인지 -
  `신규문형`(판정 트리 ①②③) / `현행유지`(④·⓪) - 를 구분한다.
시트2 누락(FN) — 발주처 리스트에 있는데 우리 행과 짝지어지지 않은 행.
시트3 집계 — 판정축 분포 · 문형 출처 · ④→② 전환율 · 식별 가능성(현행 대비).

결정적이다: 행 순서는 (페이지 · y · x · key), 시각·난수 없음.  같은 입력이면
같은 바이트가 나온다.  발주처 자료가 없는 기계에서는 시트2·판정 초안을 비우고
그렇게 적는다.

    python3 spike/label_workbook.py /tmp/r16/mixed.json [기준선.json]
"""
import collections
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "spike"))

HEAD_FILL = PatternFill("solid", fgColor="EFE7D2")
# 확정 우선순위 1번 시트 — 자동 판정이 막힌 것이 네 번의 실측으로 확정된 도면.
PRIORITY_SHEET = "D00P-10LBA10-M05-0001"

AX_FILL = {"④": "F6DEDE", "①": "E3EDDF", "②": "DFE7F0",
           "②a": "E7EDF4", "②b": "E7EDF4",      # 한쪽만 성립 (7회차)
           "③": "EAE2F0", "⓪": "EEEEEE"}


def build(run_path, baseline_path=None, out_path=None):
    data = json.load(open(run_path))
    rows = sorted(data["rows"], key=lambda r: (
        r["page_no"], round(r["rect"][1]) if r.get("rect") else 0,
        round(r["rect"][0]) if r.get("rect") else 0, r["key"]))

    have_client = (ROOT / "data" / "CZE_Field_Instrument.xlsx").exists()
    draft, fn_rows, ident_new, ident_old = {}, [], None, None
    if have_client:
        import client_lists
        import desc_metrics as dm
        rows_all, _ = client_lists.load("FIELD")
        client = [c for c in rows_all if c.get("pid") and not c.get("strike")]
        pairs, missing = dm.match_rows(rows, client)
        for c, r in pairs:
            cv, cp, cr = dm.pieces(dm.toks(c["desc"]))
            rv, rp, rr = dm.pieces(dm.toks(r["description"]))
            ok = (cv == rv and cp == rp
                  and (not set(cr) or len(set(cr) & set(rr)) * 2 >= len(set(cr)))
                  and bool(r["description"]))
            draft[r["key"]] = ("O" if ok else "X",
                              str(c["desc"] or ""), c.get("row"))
        fn_rows = missing
        ident_new = dm.score(rows, client)
        if baseline_path:
            ident_old = dm.score(json.load(open(baseline_path))["rows"], client)

    wb = Workbook()
    ws = wb.active
    ws.title = "추출 824행"
    head = ["페이지", "P&ID No.", "산출물", "TYPE", "Q'ty", "Description(최종)",
            "문형 출처", "판정축", "귀속점", "확정 우선순위", "판정 초안",
            "사람 판정(O/X)", "메모", "현행(교체 전) 문장", "발주처 대응행", "key"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True)
        c.fill = HEAD_FILL
    dv = DataValidation(type="list", formula1='"O,X"', allow_blank=True)
    ws.add_data_validation(dv)
    for r in rows:
        ax = r.get("axis") or {}
        source = ax.get("source") or "현행유지"
        d = draft.get(r["key"], ("", "", None))
        old = (ax.get("old_description")
               if ax.get("source") == "신규문형" else "")
        # 확정 우선순위 — 자동으로는 더 나아지지 않는 시트를 1번으로 세운다.
        # p6 (D00P-10LBA10-M05-0001) 이 그 시트다: 네 번의 실측(13.1% · 4.9% ·
        # 10.4% · 양쪽 실패 540행)이 모두 같은 답을 냈고, 사용자 확정 경로가
        # 유일한 길이다 (docs/from_to_axis.md).  사람의 시간을 여기부터 쓴다.
        prio = ("1 — p6 자동 불가 · 사용자 확정 대상"
                if (r.get("drawing_no") == PRIORITY_SHEET
                    and source != "신규문형") else "")
        ws.append([r["page_no"], r.get("drawing_no") or "", r["tab"],
                   r.get("type") or r.get("valve_type") or "",
                   r.get("qty"), r.get("description") or "",
                   source, ax.get("axis") or "", ax.get("attribution") or "",
                   prio, d[0], "", "", old or "", d[1],
                   r["key"]])
        if ax.get("axis"):
            ws.cell(ws.max_row, 8).fill = PatternFill(
                "solid", fgColor=AX_FILL.get(ax["axis"], "FFFFFF"))
        if prio:
            ws.cell(ws.max_row, 10).fill = PatternFill("solid", fgColor="F6E9C9")
        dv.add(ws.cell(ws.max_row, 12))
    for col, w in zip("ABCDEFGHIJKLMNOP",
                      (7, 22, 10, 7, 5, 46, 10, 7, 26, 26, 9, 12, 18, 40, 40, 18)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A2"

    ws2 = wb.create_sheet("누락(FN)")
    # 이 시트의 모수는 발주처 FIELD 전체(취소선 제외)다 - 회귀 기준선(FN 5,
    # 교집합 도면 · 칸 단위 min)과 정의가 다르므로 "구분" 열로 가른다.
    # 상세는 docs/from_to_axis.md 의 "FN 두 정의".
    ws2.append(["P&ID No.", "TYPE", "발주처 Description", "발주처 행", "구분"])
    for c in ws2[1]:
        c.font = Font(bold=True)
        c.fill = HEAD_FILL
    our_pids = {str(r.get("drawing_no") or "").strip()
                for r in rows if r.get("tab") == "FIELD"}
    if have_client:
        for c in sorted(fn_rows, key=lambda c: (c["pid"], str(c["type"]),
                                                c.get("row") or 0)):
            kind = ("교집합 도면 — 회귀 FN 과 같은 칸" if c["pid"] in our_pids
                    else "대상 외 — 이 도면에 우리 행이 없음")
            ws2.append([c["pid"], c["type"], c.get("desc") or "",
                        c.get("row"), kind])
    else:
        ws2.append(["발주처 리스트가 이 기계에 없어 비웠습니다", "", "", "", ""])
    for col, w in zip("ABCDE", (24, 8, 52, 9, 30)):
        ws2.column_dimensions[col].width = w

    ws3 = wb.create_sheet("집계")
    stats = data.get("axis_stats") or {}
    dist = stats.get("distribution") or {}
    ws3.append(["판정축 분포"])
    ws3.append(["축", "행", "비율"])
    n_all = len(rows)
    for k in sorted(dist):
        ws3.append([k, dist[k], f"{100 * dist[k] / n_all:.1f}%"])
    ws3.append([])
    ws3.append(["문형 출처", "행"])
    src_c = collections.Counter(
        (r.get("axis") or {}).get("source") or "현행유지" for r in rows)
    for k in sorted(src_c):
        ws3.append([k, src_c[k]])
    ws3.append([])
    ws3.append(["④→② 전환율(회차 지표)",
                f'{stats.get("fromto_conversion_pct")}%',
                "② / (② + ④) — 도면 벽(선분 단절) 개선의 측정 축"])
    if ident_new:
        ws3.append([])
        ws3.append(["식별 가능성(주 지표)", "현행", "신규(혼합)"])
        for k, label in (("identifiable", "식별 가능 행"),
                         ("identifiable_pct", "식별 가능 %"),
                         ("exact", "완전일치"), ("token_f1", "토큰 F1(참고)"),
                         ("missing", "대응행 없음")):
            ws3.append([label, (ident_old or {}).get(k, ""), ident_new.get(k)])
    for row in ws3.iter_rows():
        for c in row:
            if c.row in (1,) or (isinstance(c.value, str) and c.column == 1
                                 and c.value.endswith(("분포", "출처"))):
                c.font = Font(bold=True)
    for col, w in zip("ABC", (26, 16, 44)):
        ws3.column_dimensions[col].width = w

    out = Path(out_path or ROOT / "out" / "label_nouf1.xlsx")
    out.parent.mkdir(exist_ok=True)
    wb.save(out)
    return out, {"rows": n_all, "draft": len(draft), "fn": len(fn_rows),
                 "ident_new": ident_new and ident_new.get("identifiable_pct"),
                 "ident_old": ident_old and ident_old.get("identifiable_pct")}


if __name__ == "__main__":
    out, info = build(sys.argv[1],
                      sys.argv[2] if len(sys.argv) > 2 else None)
    print("저장:", out)
    print(info)
