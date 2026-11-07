valve05 — Valve Datasheet 검토: 456쪽 전수 눈 대조로 읽기 정확도 96.5 % → 99.99 %

무엇이 달라지나
  1. Datasheet 456쪽을 한 쪽씩 눈으로 보고 도구가 읽은 21,482항목과 대조했습니다.
     고치기 전 오류 760(3.54 %) → 고친 뒤 2(0.009 %).  남은 2건은 도면 자체의 Doc. No. 오타이고, 도구가 지적으로 올립니다.
  2. 고친 것: 화면에 안 보이는 숨은 글자(흰 상자에 덮인 글)를 읽지 않음 · 같은 줄 낱말 순서 · Notes 끝에 붙던 쪽 번호 ·
     MOV(Form 102) sheet 1 오른쪽 열(Instrument Type 등)과 sheet 2 머리 행 · 단위만 있는 칸 · 'Sheet 3 of 3' · 두 줄 제목 등.
  3. 새 지적: sheet 2 표제란 Doc. No. 가 sheet 1 과 다름 · 뒷장의 Tag/PID/Service/Line 이 sheet 1 과 다름 (실자료 3건).

적용 순서
  1) apply_to_PID_dev.bat → PID_dev 에서 확인 (http://localhost:8000/valve/)
  2) apply_to_PID_ops.bat → 운영 폴더 · 8000 서버 재시작
  3) Document Management 에서 Datasheet PDF [다시 읽기] — 검토자가 고친 값 · 의견 · Mark-up 은 그대로 남습니다.
  valve01~04 를 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
