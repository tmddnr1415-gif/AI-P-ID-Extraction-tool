PID 업데이트 hotfix136 (2026-11-11) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · 3D 계측제어)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 135 어느 판이 있든, 적용하면 이 판(136)이 됩니다.
  회사 PC 에서 따로 고친 파일도 원본을 backup\hotfix136_<시각>\ 에 둔 뒤 새 판으로 덮습니다.
- 6 세션이 따로 만든 PID_dev+ops_valve37 zip 은 넣지 않아도 됩니다 — 그 내용이 이 꾸러미에 들어 있습니다.
- 회사 Claude Code 로 엔진을 고친 것이 있으면 적용하기 전에 '엔진 개선값' md 를 먼저 뽑아 보내 주세요.

무엇이 바뀌었나 (hotfix135 → 136)
Valve (Datasheet 자동 검토)
- 회사 PC 에서 Datasheet(ds=74)를 열 때 'HTTP 500' 만 나오던 문제:
  검토 규칙이 그 Datasheet 에서 멈춰도 이제 PDF 와 칸 값은 그대로 열리고, 검토가 안 된 이유를 보여 줍니다.
- /valve 의 예상 못 한 오류는 이유(JSON)로 답하고, 자세한 기록을 <자료폴더>\valve\logs\errors_날짜.log 에 남깁니다.
  → 다시 생기면 그 log 파일을 6 세션에 보내 주세요 (진짜 원인을 고칠 수 있습니다).

P&ID · LOGIC · 판넬 · 도서검토 · 3D 계측제어 · Valve Globe/Butterfly/PSV
- hotfix135 와 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat (서버 재시작 안내를 따르세요).
2. 화면 위 띠 오른쪽에 '업데이트 136' 이 보이면 새 판입니다. 안 보이면 서버를 다시 켜고 Ctrl+F5 한 번.
3. 대시보드 › 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve 에서 전에 HTTP 500 이 나던 Datasheet(ds=74)를 다시 열어 보세요.
