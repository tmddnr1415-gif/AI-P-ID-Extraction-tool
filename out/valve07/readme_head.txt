valve07 — Valve Datasheet 검토: 화면 개선 + Process Data 비교(Phase 3) + Revision 비교 Excel (+ valve06 까지 전부)

무엇이 달라지나
  1. Datasheet Review 화면: 위에 Tag 요약 띠(Tag · Type · Size · Rating/Class · Rev · 지적 개수 · 검토 상태), 왼쪽 Tag 목록과 오른쪽 패널을
     접고 펼 수 있고([ ] 키), PDF 도구줄이 한 줄로 줄어 PDF 가 더 크게 보입니다. 1366×768 노트북에서도 A4 한 쪽이 100 % 로 들어갑니다.
  2. Data 탭 위에 밸브 그림이 생겼습니다. 칸(Seat Material · Stem · Packing · Actuator …)을 누르면 그 부위가 그림에서 파랗게 표시되고 설명이 나옵니다.
  3. Process Data Verification 이 실제로 비교합니다. Document Management 에 Process Data PDF(Annexure 7)를 올리면 Tag 로 연결해
     공정 항목(유체 · 상 · 압력 · 온도 · 차압 · 작동 시간 · Fail 위치 · 기밀 · Line/P&ID)만 비교합니다. 다른 것은 'Process Mismatch'(주황)로
     Issue List · Mark-up PDF 에 나갑니다. 크기 · 등급 · 재질은 비교하지 않고, 단위 · 기준이 불명확하면 Review Required 로 둡니다.
  4. Dashboard(KPI 5×2 · Issues by Category · KPI 를 누르면 걸러진 화면) · Valve List/Issue List(↑↓ Enter) · Revision Comparison(두 PDF 같이 움직이기 ·
     Revision 비교 Excel) · PMS(행을 고르기 전 안내) · Reports & Export(묶음 · 만들기 전 확인 · 진행/완료/실패 표시).

적용 순서
  1) apply_to_PID_dev.bat → PID_dev 에서 확인 (http://localhost:8000/valve/)
  2) apply_to_PID_ops.bat → 운영 폴더 · 8000 서버 재시작
  3) Document Management 에 Process Data PDF 가 이미 올라가 있으면 바로 비교됩니다 (처음 열 때 자동으로 읽음).
  valve01~06 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
