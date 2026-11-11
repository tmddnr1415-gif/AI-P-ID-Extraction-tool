PID 업데이트 hotfix137 (2026-11-11) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · 3D 계측제어)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 136 어느 판이 있든, 적용하면 이 판(137)이 됩니다.
  회사 PC 에서 따로 고친 파일도 원본을 backup\hotfix137_<시각>\ 에 둔 뒤 새 판으로 덮습니다.
- 회사 Claude Code 로 엔진을 고친 것이 있으면 적용하기 전에 '엔진 개선값' md 를 먼저 뽑아 보내 주세요.

무엇이 바뀌었나 (hotfix136 → 137)
Valve (Datasheet 자동 검토) — Datasheet Review 에서 PDF 가 빈 화면(1 / 0 쪽)으로 뜨던 것
- 원인: 서버에 보관된 원본 PDF(app\_data\valve\files\....pdf)가 올린 뒤에 PDF 가 아닌 내용으로 바뀌어 열리지 않았습니다.
- 이제 빈 화면 대신 "서버에 저장된 원본 PDF 를 열 수 없습니다 — 같은 파일을 다시 올리세요" 안내와
  [Document Management 열기] 단추가 나오고, Document Management 목록에 '⚠ 원본 손상 — 같은 파일 다시 올리기' 가 표시됩니다.
- ★ 할 일: Document Management 에서 Datasheet2.pdf 를 한 번 다시 올려 주세요. Tag · 지적 · 검토 기록은 그대로이고 PDF 가 다시 보입니다.
- 재발 방지: 보관 원본을 .pdf 대신 .bin 이름으로 둡니다. 서버를 처음 켤 때 한 번, 멀쩡한 옛 .pdf 보관본을 .bin 으로 옮깁니다
  (복사 · 확인 뒤 옛 파일 삭제 — 문서가 많으면 처음 켤 때 조금 걸릴 수 있음).
- 진단: 열리지 않은 파일의 크기 · 머리 32바이트를 <자료폴더>\valve\logs\errors_날짜.log 에 남깁니다 (문서 내용은 남기지 않음).
  다시 생기면 이 log 를 6 세션에 보내 주세요 — 회사 보안 프로그램이 파일을 바꾼 것인지 가릴 수 있습니다.

P&ID · LOGIC · 판넬 · 도서검토 · 3D 계측제어 · Valve Globe/Butterfly/PSV
- hotfix136 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat (서버 재시작 안내를 따르세요).
2. 화면 위 띠 오른쪽에 '업데이트 137' 이 보이면 새 판입니다. 안 보이면 서버를 다시 켜고 Ctrl+F5 한 번.
3. Ball Valve › Document Management 에서 Datasheet2.pdf 를 다시 올린 뒤 Datasheet Review 에서 PDF 가 보이는지 확인.
