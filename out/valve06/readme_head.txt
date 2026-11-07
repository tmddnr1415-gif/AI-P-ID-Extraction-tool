valve06 — Valve List Excel 에서 Vendor 행(AMPO · OMS · NEWAY) 삭제 (+ valve05 전부)

무엇이 달라지나
  1. 도구가 만드는 Valve List Excel(회사 TBE 양식)에서 Tag 마다 붙어 있던 Vendor 행(AMPO · OMS · NEWAY …)을 지우고
     Requirement 한 줄만 남깁니다. 서식 · 메모 · 칸 링크 · 번호는 그대로입니다.
  2. 그 밖은 valve05 와 같습니다 (456쪽 눈 대조로 읽기 정확도 99.99 %, Mark-up 도구 등).

적용 순서
  1) apply_to_PID_dev.bat → PID_dev 에서 확인 (http://localhost:8000/valve/ → Reports & Export → Valve List 내려받기)
  2) apply_to_PID_ops.bat → 운영 폴더 · 8000 서버 재시작
  valve01~05 를 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
