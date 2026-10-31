valve04 — Valve Datasheet 검토: 검토 피드백 내보내기 (+ valve03 전부)

무엇이 달라지나
  1. Reports & Export › [⇩ Review Feedback (json)] — 검토자가 지적을 Confirmed / Dismissed 한 것(사유 포함), 고친 값,
     도구가 못 잡아 직접 그린 Error · Missing 표시를 한 파일로 내려받습니다. 이 파일을 개발 쪽에 주면
     규칙마다 맞은 비율과 놓친 것을 재서 고칩니다 (P&ID 의 VOC 와 같은 방식). 고객 값이 들어 있으니 사내 경로로만.
  2. 내부 정리: 판독 문턱을 실측 근거와 함께 이름 붙인 값으로 · 화면 동작은 valve03 과 같습니다.
  valve03 의 내용(정확도 개선 · A3/회전/암호 PDF · Mark-up 도구 · 다시 읽기)이 모두 들어 있습니다.

바뀌는 파일
  app\valve\*.py · app\static\valve\* · tests\test_valve.py · app\main.py (valve01 과 같은 두 줄)
  valve01~03 을 아직 적용하지 않았어도 이것 하나로 됩니다 (hotfix131 기준 누적).

적용 순서
  1) apply_to_PID_dev.bat → PID_dev 에서 확인 (http://localhost:8000/valve/)
  2) apply_to_PID_ops.bat → 운영 폴더 · 8000 서버 재시작
  3) Document Management 에서 Datasheet PDF [다시 읽기] (valve03 이전 분석분만)
  대시보드는 바꿀 것 없음.
