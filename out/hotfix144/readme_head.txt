PID 업데이트 hotfix144 (2026-11-18) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 143 어느 판이 있든 적용하면 이 판(144)이 됩니다. (139 ~ 143 을 안 넣었어도 이것 하나 — 내용 포함)
- 대시보드는 v17.64 (2026-11-18 ①) 를 함께 넣어 주세요.

무엇이 바뀌었나 (hotfix143 → 144) — Valve · Instrument (valve41)
- South 도서 읽기: South Control Valve · Regulator 도서의 'INSTRUMENT SPECIFICATION' 양식(번호 2열 · 괘선 칸)을 읽습니다.
  예전에는 40쪽 도서가 Tag 없는 Datasheet 1개로 잡혔음 → 이제 Tag 마다 칸 값을 읽음.
- 다시 올리지 않아도 됨: 서버를 켤 때 Tag 없이 남은 도서를 새 방식으로 한 번 다시 읽습니다 (같은 파일의 옛 읽기 잔재 정리).
- Area 'South' 와 'QS' 가 따로 나오던 것 → 하나로.
- PURCHASE 칸의 TBC 는 Open Item 으로 잡지 않음.
- 읽지 못한 쪽 알림 (모든 타입): 모르는 양식 · 대부분 못 읽은 쪽 · Tag 없는 Datasheet 는 '읽지 못한 쪽' 으로 표시.
  도서 앞 INDEX (LIST OF TAGS) 와 읽은 Tag 를 대조 → Document Management 에 빨간 '일부 못 읽음' / '✓ INDEX n Tag 모두 읽음'.
- 서버를 처음 켤 때 가끔 'database is locked' 가 나던 것 고침.

P&ID · LOGIC · 판넬 · 도서검토 · 3D
- hotfix143 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat.
2. 화면 위 띠 오른쪽에 '업데이트 144'. 서버 창에 'Restarting' 이 되풀이되지 않으면 정상.
   처음 켤 때 South 도서를 다시 읽느라 조금 걸릴 수 있습니다.
3. Globe Valve 등 South 도서: Tag 가 나오는지 · Document Management 의 '✓ INDEX … 모두 읽음' / '일부 못 읽음' 확인.
