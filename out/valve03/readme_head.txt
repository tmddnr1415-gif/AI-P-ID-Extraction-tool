valve03 — Valve Datasheet 검토: 정확도 · 강건성 · 속도 개선 + 사용자 Mark-up 도구

무엇이 달라지나
  1. 실제 Datasheet 456쪽으로 실패 원인을 찾아 고쳤습니다.
     칸 짝 실패 69 → 1 · 잘못 읽은 값 11 → 0 · 'Data Missing' 잘못 지적 748 → 0 (Process Data 문서를 참조하는 데이터시트) ·
     PMS 확인 필요 113 → 75 · 'Body : Note-8' 처럼 엉뚱한 Note 를 가리키는 오류를 새로 찾습니다.
  2. A3 로 출력된 PDF · 돌아간 쪽 · 암호 걸린 PDF · 깨진 PDF 도 처리하거나, 무엇을 하면 되는지 알려 줍니다.
  3. 빨라짐: 456쪽 약 6초 · Mark-up PDF 크기 약 1/8.
  4. Datasheet Review 화면 PDF 위 'Mark-up' 줄 — 사각형 · 구름 · 원 · 형광펜 · 선 · 화살표 · 펜 · 글상자 · 메모.
     분류(Comment 파랑 · Error 빨강 · Missing 주황 · Question)를 고르면 그대로 Issue List Excel 과 Mark-up PDF 에 번호로 나갑니다.
     선택 도구(V)로 옮기기 · 크기 바꾸기, Delete 지우기, Ctrl+Z 되돌리기 · Ctrl+Y 다시. 내보낸 PDF 의 표시는 Acrobat 에서도 고칠 수 있습니다.

바뀌는 파일
  app\valve\*.py · app\static\valve\* · tests\test_valve.py · app\main.py (valve01 과 같은 두 줄)
  valve01 · valve02 를 아직 적용하지 않았어도 이것 하나로 됩니다 (hotfix131 기준 누적).
  데이터: pid_data\valve\ — 기존 자료는 그대로 쓰입니다 (표 열은 자동 추가). 이미 분석한 PDF 는 [다시 분석] 하면 고친 추출이 적용됩니다.

적용 순서
  1) apply_to_PID_dev.bat → PID_dev 에서 확인 (http://localhost:8000/valve/)
  2) apply_to_PID_ops.bat → 운영 폴더 · 8000 서버 재시작
  대시보드는 바꿀 것 없음 (valve01 의 메뉴 그대로).
