valve08 — 빈 Process Data 항목을 전부 지적 (+ valve07 까지 전부)

무엇이 달라지나
  1. 데이터시트 PROCESS DATA 블록의 빈 칸(Fluid · Sour Service · Fluid State · Corrosive · Erosive · Toxic · Operating/Design Pressure ·
     Operating/Design Temperature · Max. Diff. Pressure · Stroke Time Open/Closed, MOV 의 공정 조건표 항목)을 모두 'Data Missing'(주황)으로
     PDF 위에 표시하고 Issue List Excel · Mark-up PDF 에 넣습니다.
  2. 데이터시트가 "For Process data refer to …" 로 별도 문서를 가리켜도 지적하고, 설명에 그 문서 번호를 적습니다.
     Process Data PDF 가 올라가 있으면 그 값을 'Required / Expected' 칸에 보여 줍니다.
  3. 실자료(456쪽)로 2,529건(Tag 당 평균 15) — 필요 없는 것은 Issue 상태를 Dismissed 로 두면 설계사 전달본에서 빠집니다.

적용 순서
  1) apply_to_PID_dev.bat → 확인 → 2) apply_to_PID_ops.bat → 8000 서버 재시작
  3) Document Management 에서 Datasheet PDF [다시 읽기] (valve05 이전에 읽은 것만)
  valve01~07 을 적용하지 않았어도 이것 하나로 됩니다. 대시보드는 바꿀 것 없음.
