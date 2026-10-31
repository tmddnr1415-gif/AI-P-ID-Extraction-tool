valve02 — Valve Datasheet 검토: 지적 사항(오류 · 누락) 표시 · 설계사 전달 Excel · 실제 PMS 비교

무엇이 달라지나
  1. 잘못되거나 없는 Data 를 찾아 PDF 위에 색 상자 + 번호로 표시합니다 (빨강 오류/PMS 부적합 · 주황 누락/HOLD · 노랑 Revision 변경 · 파랑 검토자).
     [⇩ Mark-up PDF] = 그 표시가 인쇄되는 PDF + 데이터시트마다 'Issue Summary' 쪽. 원본 PDF 는 그대로.
  2. [⇩ Issue List Excel] = Tag · Doc. No. · Rev · Sheet · PDF Page · 칸 · 값 · 무엇이 문제인지 · 요구값 — 설계사에게 바로 보낼 수 있게 영어로.
  3. Datasheet PDF 분석이 끝나면 Valve List(기준 TBE 양식) 와 Issue List Excel 이 같이 만들어져 바로 내려받아집니다.
  4. Excel 의 칸(링크)을 누르면 이 도구가 그 PDF 장 · 그 위치를 엽니다. 도구 안 Valve List / Issue List 화면은 오른쪽 PDF 미리보기와 실시간 연동됩니다.
  5. PMS 비교가 실제 PMS(98-98-PI-SPC-00001)로 됩니다. 재질은 표기가 아니라 규격 · 등급으로 비교합니다
     (ASTM A351 CF8M = 316/316L SS A351-CF8M/CF3M, 316 SS / HF = SS 316/HF → 같음).

바뀌는 파일
  app\valve\*.py (새 파일 material · pms · issues · exports 포함) · app\static\valve\* · tests\test_valve.py · app\main.py (valve01 과 같은 두 줄)
  valve01 을 아직 적용하지 않았어도 이것 하나로 됩니다 (hotfix131 기준 누적).
  데이터: pid_data\valve\ (내보낸 파일은 pid_data\valve\exports\). 기존 자료는 그대로 쓰입니다 (표 열은 자동 추가).

적용 순서
  1) apply_to_PID_dev.bat → PID_dev 에서 확인 (http://localhost:8000/valve/)
  2) apply_to_PID_ops.bat → 운영 폴더 · 8000 서버 재시작
  3) valve01 때 올린 PMS PDF 는 다시 올릴 필요 없습니다 (처음 쓸 때 자동으로 읽습니다).
  대시보드는 바꿀 것 없음 (valve01 의 메뉴 그대로).
