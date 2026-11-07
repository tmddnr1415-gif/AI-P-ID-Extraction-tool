valve10 — PMS 대조 점검 · 특수 요구사항 열 · 재질 검토 의견 (+ valve09 까지 전부)

무엇이 달라지나
  1. PMS 대조 오류 수정: Ball Valve 의 Trim(Ball)/Stem 을 PMS Class 머리의 일반 Trim(예: 1A1A 'TRIM 8 (13CR/HF)' — Gate/Globe 용)이
     아니라, 그 Class 의 Ball Valve 품목에 적힌 '316 SS BALL/STEM' 과 비교합니다. 거짓 'Review Required' 16건이 없어집니다.
  2. PMS 를 더 읽습니다: Class 마다 온도/압력(P-T) 표 · 사용 유체(Service) 목록 · General Class Notes.
     이미 올려 둔 PMS 는 서버가 처음 쓸 때 원본 PDF 에서 자동으로 다시 읽습니다 (다시 올릴 필요 없음).
  3. Valve List Excel 오른쪽에 'Special Requirements (Notes)' 열: NACE · Fugitive Emission(ISO 15848 Class A) · Fire-safe · PFP ·
     Anti-static · Blow-out · SIL · PST · 경도 · EN 10204 3.2 · 기밀 등 — 칸 · Note · General Note 어디서 나왔는지 함께 적습니다.
     데이터시트 칸이 'Not Required' 면 [datasheet: Not Required] 로 따로 보입니다.
  4. 재질 검토 의견(규칙 MR-01~15): 시트 재질 온도 한계(PMS Note · PTFE/RPTFE/PEEK) · PMS P-T 범위 · 저온 배관의 WCB 본체 ·
     CO2 탄소강 · NACE(316 · 탄소강 · 17-4PH · B7/B8M 볼트) · HF 종류 · Dual grade · CO2 급감압(RGD) · Fire-safe · Service 목록.
     - 작업대 오른쪽 'Material' 탭: 조치 필요(Action) · 확인 필요(Confirm) · 참고(Note), 근거 규격과 근거 위치(누르면 이동).
     - Action · Confirm 은 Issue List 에 'Material Review'(청록)로 올라갑니다. Valve List 'Material Review (Tool)' 열에도 적습니다.
     - Process Data PDF 를 올려 두어야 온도 · 압력 규칙이 동작합니다.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  valve01~09 를 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
