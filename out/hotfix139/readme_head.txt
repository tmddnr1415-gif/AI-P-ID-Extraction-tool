PID 업데이트 hotfix139 (2026-11-13) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- hotfix138 을 넣은 뒤 P&ID 서버가 켜졌다 꺼지기를 되풀이하던 것을 고친 판입니다.
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 138 어느 판이 있든 (rollback 으로 136 에 되돌렸어도) 적용하면 이 판(139)이 됩니다.
- 대시보드는 v17.47 그대로 쓰면 됩니다 (이미 적용함).

무엇이 바뀌었나 (hotfix138 → 139)
Valve · Instrument — 서버가 켜졌다 꺼지던 것
- 원인: 서버를 켤 때 미리 계산하면서, 보관된 원본 PDF 가 깨진 것(회사 보안 프로그램이 바꾼 것으로 보임)을 PDF 엔진으로 열다가 서버 전체가 죽었습니다.
- 이제 깨진 보관 PDF 는 어디서도 열지 않습니다. 값 · 검토 · 현황판은 그대로 보이고, PDF 보기만 '원본 손상' 안내가 나옵니다.
- PDF 를 여는 일은 한 번에 하나씩, 미리 계산은 프로젝트를 차례로 합니다.
- 서버를 켤 때 '[valve] stored PDF check: n good · m damaged' 로 깨진 보관본 수와 앞 32바이트를 보여 줍니다
  (보안 프로그램 때문인지 가리는 데 씁니다 — 이 줄을 사진으로 보내 주세요).
- 혹시 다시 죽으면 원인이 <자료폴더>\valve\logs\crash_날짜.log · warmup.log(마지막 줄 = 멈춘 곳)에 남습니다.
- 비상 스위치: 환경변수 VALVE_WARMUP=0 이면 미리 계산을 끕니다.

P&ID · LOGIC · 판넬 · 도서검토 · 3D · Instrument 기능
- hotfix138 과 같습니다.

다음 판에서 (6 세션 작업 중)
- 읽은 Datasheet 를 JSON 파일로 저장 · 검토가 PDF 없이 DB/JSON 으로 돌게 (다시 올리지 않아도 새로고침으로 반영)
- Area 규칙대로 Valve 화면의 Tag Area 표시

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat (서버 재시작 안내를 따르세요).
2. 화면 위 띠 오른쪽에 '업데이트 139' 가 보이면 새 판입니다. 서버 창이 'Restarting in 10 seconds' 없이 켜져 있으면 정상.
