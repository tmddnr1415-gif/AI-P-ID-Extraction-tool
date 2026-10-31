valve01 — Valve Datasheet 검토 (실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve)

무엇이 생기나
  P&ID 서버(8000)에 새 화면 /valve 가 생깁니다. 대시보드의 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve 메뉴가 이 화면을 엽니다.
  (대시보드 메뉴는 따로 보내는 대시보드 zip(APP_VERSION 2026-10-31.2)으로 생깁니다.)
  - Valve Datasheet PDF(여러 개 · 병합본)를 넣으면 Tag 별로 나눠 칸을 읽고, 읽은 쪽 · 위치를 PDF 위에 보여 줍니다.
  - 기준 Valve List(TBE) 양식 그대로 Valve List Excel 을 채워 내려받습니다 (바뀐 칸 노란색 · 출처 메모).
  - 같은 Tag 의 새 Revision 을 넣으면 칸별로 비교하고 노란 표시 PDF 를 만듭니다.
  - Process Data · PMS 검토는 다음 단계입니다 (지금은 'Not Evaluated').

바뀌는 파일
  새 파일: app\valve\*.py · app\static\valve\* · tests\test_valve.py
  고친 파일: app\main.py (두 줄 추가 — 다른 줄은 hotfix131 그대로)
  데이터는 pid_data\valve\ (또는 app\_data\valve\) 에 새로 생깁니다. 기존 P&ID · LOGIC 자료는 건드리지 않습니다.

적용 순서
  1) apply_to_PID_dev.bat  → PID_dev 에서 확인 (http://localhost:8000/valve/)
  2) apply_to_PID_ops.bat  → 운영 폴더 · 8000 서버 재시작
  3) 대시보드 zip 의 APPLY.bat
  ※ 회사 P&ID 서버가 hotfix131 판이 아니면 app\main.py 가 충돌로 .new 에 남습니다 — 그 경우 알려 주세요.

필요한 것: 새 설치 없음 (PyMuPDF · openpyxl · FastAPI 는 이미 설치된 것 사용).
  Valve List 가 .xls 면 이 PC 의 Excel 로 .xlsx 로 바꿔 읽습니다. 안 되면 Excel 에서 .xlsx 로 저장해 넣으세요.
