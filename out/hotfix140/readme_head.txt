PID 업데이트 hotfix140 (2026-11-13) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 139 어느 판이 있든 적용하면 이 판(140)이 됩니다. (139 를 아직 안 넣었어도 이것 하나 — 139 내용 포함)
- 대시보드는 v17.47 그대로.

무엇이 바뀌었나 (hotfix139 → 140)
Valve · Instrument
- 읽은 Datasheet 를 JSON 파일로 저장합니다: <자료폴더>\valve\datasheets\<프로젝트>\<종류>\<Tag>__<Rev>.json
  (칸 값 · 단위 · 쪽 · 위치 · 상태 · 검토자 수정 · Notes · Rev 표 · 원본 이름 · 올린 사람/때). 문서별 묶음은 _documents 폴더.
  - 서버를 켤 때 이미 들어 있는 Datasheet 도 빠진 것만 JSON 으로 씁니다 → 다시 올리지 않아도 됩니다.
  - 검토 · 현황판 · 대조는 DB · JSON 으로 돌아 보관 PDF 가 깨져도 그대로 보입니다 (새로고침).
- 보관 PDF 가 깨졌으면 예전에 서버가 그려 둔 쪽 그림으로 PDF 를 보여 줍니다 (다시 올리지 않아도 됨 · '그림으로 보는 중' 표시).
  그림이 남아 있지 않은 쪽만 '원본 손상' — 그 문서만 골라 다시 올리면 됩니다.
- Area 규칙대로 Tag Area 를 채웁니다: Valve Summary · By Area · Issue 목록 · Excel · Valve List · 특수요구사항 표.
  순서 = 규칙 표 → Instrument Index AREA → Tag 앞 번호. 데이터시트 제목에 Area 가 있으면 그대로, 없거나 'Brownfield' 만이면 규칙 값 + 출처.
  ★ 회사 PC 에서 한 번: Dashboard › By Area 의 [규칙 표 넣기] 에 Brownfield 구역 표를 붙여 넣어야 '(not stated)' 가 채워집니다
    (한 번 넣으면 Ball · Globe · Butterfly · PSV · Instrument 공통).
- (hotfix139) 깨진 보관 PDF 를 열지 않아 서버가 켜졌다 꺼지지 않음.

P&ID · LOGIC · 판넬 · 도서검토 · 3D
- hotfix138 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat.
2. 화면 위 띠 오른쪽에 '업데이트 140'. 서버 창에 'Restarting' 이 되풀이되지 않으면 정상.
3. Dashboard › By Area 에 규칙 표 넣기 → Valve Summary 의 Area 확인.
