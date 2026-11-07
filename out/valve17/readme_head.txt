valve17 — Issue List 를 Area 순으로 · All Valves 에 Note 요구사항 열 (+ valve16 까지 전부)

무엇이 달라지나
  1. Issue List Excel 의 'Issue List' 시트가 Area → Site → Unit → Tag 순서입니다 (North · South · Brownfield · W15).
     한 Tag 안의 지적 순서는 데이터시트 순서 그대로이고, No. 는 1 부터 다시 매깁니다.
  2. Valve List Excel 'All Valves' 시트에 Note · General Note 의 중요 요구사항이 종류마다 한 열로 나옵니다 (청록 머리):
     PFP · Fugitive Emission (ISO 15848) · Fire Safe · NACE / Sour · SIL · Partial Stroke Test · Tightness / Leakage ·
     Anti-static · Blow-out Proof Stem · Hardness Limit · Material Cert. (EN 10204) (+ PMI · Impact Test · DBB · Painting — 있을 때만)
     예) PFP: Not Required (row 23 Fireproofing (PFP); GN 22; GN 26)
         Fugitive Emission: Yes — Class A type tested (GN 31)
         Material Cert.: Yes — 3.2 (Note 3)
     데이터시트의 칸(예: Fireproofing)이 답을 주면 그 답이 먼저입니다. Excel 필터로 'PFP Required' 등을 바로 고를 수 있습니다.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~16 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
