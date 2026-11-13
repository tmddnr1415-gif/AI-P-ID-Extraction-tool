PID 업데이트 hotfix143 (2026-11-13) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 142 어느 판이 있든 적용하면 이 판(143)이 됩니다. (139 ~ 142 를 안 넣었어도 이것 하나 — 내용 포함)
- 대시보드도 v17.48 로 함께 올려 주세요 (Area 순서).

무엇이 바뀌었나 (hotfix142 → 143)
- Document Management 에 '이 도서의 Area' (문서에서 읽기 / North · South · W15) — 올릴 때 고르거나, 이미 올린 도서도 표에서 바꿈 (다시 올리지 않음).
- North 를 넣어도 South 로 읽던 것 고침 (Loop 번호로 짐작한 값은 이제 North · South 를 정하지 않음).
- 'QN' 이 'QN Greenfield' 로 바뀜.

hotfix142 내용 (141 → 142)
Valve · Instrument — Area 정하는 순서와 이름
- 순서: ⓪ 올린 도서 Area → ① DTS No. (98 → QN · 999 → QS · 315 → W15) → ② Datasheet 제목의 Area → ③ Tag 규칙 (규칙 표 → Instrument Index → 학습).
- QN 안에서 Brownfield Tag 는 'QN Brownfield N1 · N2' 로 나눕니다. QS · W15 에는 Brownfield 가 없습니다.
- 화면 Area 값: QN Greenfield · QN Brownfield N1 · QN Brownfield N2 · QS · W15 (예전 'North · South' 표기가 바뀜).
- 이미 읽은 Instrument Datasheet 도 보관 PDF 가 멀쩡하면 한 번 다시 채웁니다 (다시 올리지 않아도 됨).

hotfix141 까지 들어 있는 것 (아직 안 넣었다면)
- 서버가 켜졌다 꺼지던 것 고침 · 깨진 보관 PDF 는 예전 쪽 그림으로 보기 · Datasheet JSON 저장 · Area 규칙 표 기본값 · 화면에서 편집

P&ID · LOGIC · 판넬 · 도서검토 · 3D
- hotfix138 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat.
2. 화면 위 띠 오른쪽에 '업데이트 143'. 서버 창에 'Restarting' 이 되풀이되지 않으면 정상.
3. Valve Summary · Instrument By Area 의 Area 가 QN Greenfield · QN Brownfield · QS · W15 로 나오는지 확인.
