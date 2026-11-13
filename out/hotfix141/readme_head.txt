PID 업데이트 hotfix141 (2026-11-13) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 140 어느 판이 있든 적용하면 이 판(141)이 됩니다. (139 · 140 을 안 넣었어도 이것 하나 — 내용 포함)
- 대시보드는 v17.47 그대로.

무엇이 바뀌었나 (hotfix140 → 141)
Valve · Instrument — Area
- Area 규칙 표를 기본값으로 넣어 두었습니다 — 회사 PC 에서 아무것도 하지 않아도 Tag 앞 번호로 Area · Sub-area · Unit 이 채워집니다
  (예: 52 · 53 → North Brownfield · QG3&4 · Unit 09).
- 표 고치기: 공통 자료 › 'Area 규칙 표' 카드 또는 Instrument › By Area — 줄마다 고치기 · 더하기 · 지우기 · 글 붙여넣기 · [기본값으로 되돌리기].
  저장하고 새로고침하면 Valve · Instrument 현황판 · Issue · Excel 의 Area 가 모두 다시 표시됩니다.
- 문서 제목이 'NORTH' 만 말하면 Site(North)만 채우고 Brownfield 여부는 규칙 표로 정합니다 (전처럼 'North' 로 짐작하지 않음).

hotfix140 까지 들어 있는 것 (아직 안 넣었다면)
- 서버가 켜졌다 꺼지던 것 고침 · 깨진 보관 PDF 는 열지 않고 예전 쪽 그림으로 보기 (다시 올리지 않아도 됨)
- 읽은 Datasheet 를 JSON 파일로 저장 (<자료폴더>\valve\datasheets\…)

P&ID · LOGIC · 판넬 · 도서검토 · 3D
- hotfix138 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat.
2. 화면 위 띠 오른쪽에 '업데이트 141'. 서버 창에 'Restarting' 이 되풀이되지 않으면 정상.
3. Butterfly Valve › Dashboard › Valve Summary 의 Area 가 채워졌는지 확인.
