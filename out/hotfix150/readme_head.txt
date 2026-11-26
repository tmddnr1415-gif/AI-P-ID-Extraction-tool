PID 업데이트 hotfix150 (2026-11-26) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 149 어느 판이 있든 적용하면 이 판(150)이 됩니다. (139 ~ 149 를 안 넣었어도 이것 하나 — 내용 포함)
- 대시보드는 v18.68 (2026-11-26 ④) 를 함께 넣어 주세요.

무엇이 바뀌었나 (hotfix149 → 150) — LOGIC (L98 · L99 · 3 세션)
- 남은 판독 빈틈 셋 고침: 긴 기운 파선 · 블록 변 앞의 건너뛰기 · 마름모 빗변으로 들어가는 선.
- 왕복 시뮬레이션: 분석 ↔ 똑같이 그린 그림 ↔ 그린 PDF 를 다시 올린 것을 서로 맞춰 봄 · 2=3 증거에 A/B 꼴.

hotfix149 내용 (148 → 149) — Valve PDS Rev. 비교 (valve44 · 45 · 6 세션)
- PDS Rev. 비교 Excel 이 엔지니어 v2 양식으로 · 공통 자료 PDS 줄에서 한글 · English 골라 받기.
- Tag 변경을 추정하지 않음 — 같은 Tag 번호끼리만 비교 · 이전 Rev. 에만 있으면 Delete · 최신 Rev. 에만 있으면 New.
- PDS 읽기 2건 교정 ('WATER SOUR' → 'SOUR WATER').

hotfix148 내용 (147 → 148)
Valve (valve43 · 6 세션)
- PDS Rev. 비교: 같은 문서 번호의 수정 PDS 를 공통 자료에 올리면 이전 Rev. 과 Tag · 칸별로 비교해
  'PDS Rev. 비교 Excel' (Summary · 문서별 · High 목록 · Sizing 영향) 을 받음.
- PDS 표 읽기 고침 — 예전에 빠지던 Tag 가 모두 읽힘 (Ball 판정 +156 · 없어진 것 0 · 심각도 변화 0). North · South · W15 PDS 를 함께 씀.
LOGIC (L92 ~ L97 · 3 세션)
- 19VA 827장 전수 점검 — 분석기 마름모 기호 · 원본 모양 타이머/펄스/램프 · 모든 기호에 동작(동작 없는 기호 146 → 0).
- 매크로 안쪽(Typical) 선 켜 보기 · 매크로 연산자 전수 채점 · 짧은 파선 판독(출력 없는 연산자 161 → 0 · 못 본 연산자 197 → 6).
- 분석과 함께 똑같이 그리기 · 묶음 PDF 의 FROM/TO 링크 · LOGIC 화면 결(새 색 · 글꼴 정리).

hotfix147 내용 (146 → 147) — Valve (valve42 · 6 세션)
- Valve Spec 근거 검토: 공통 자료 > Valve Specification 칸에 On/Off · MOV · Control Valve Spec PDF 를 올리면,
  해당 종류 Datasheet 마다 Spec 조항(§번호 · 쪽 · 문장)을 근거로 'Spec Compliance' 코멘트가 붙습니다.
- Spec 을 올리지 않으면 지금 판정 그대로 (변화 없음). Spec 원본은 회사에서 올려야 함.

hotfix146 내용 (145 → 146)
P&ID · LOGIC 화면 (2 세션)
- [심볼] 창 준비를 파일에도 기억 → 서버를 다시 켠 뒤에도 바로 열림 (큰 도서는 처음 한 번 약 11초 걸리던 것).
- LOGIC 결과 화면: 도면 그림이 늦거나 못 뜨면 빈 칸 대신 "받는 중" · 실패 사유 · [다시 받기].
도서검토 2026-11-19.1 (5 세션)
- 회사 규칙대로 외부 번역(Claude)은 기본 꺼짐 — 화면에 선택지 없음 · 서버도 막음 (번역은 PC 안에서만).
- 외국어(베트남어 · 포르투갈어 등) 계장 자료도 한국어 질문으로 찾아짐 — 유량 · 포지셔너 · 제어밸브 Cv 질문 개선.

hotfix145 내용 (144 → 145) — P&ID 결과 화면
- 'List 는 나오는데 도면이 안 나온다' 고침: 도면 그림이 무거운 PDF 읽기 뒤에서 최대 60초 기다리던 것 → 따로 처리.
  그래도 늦으면 "도면 그림을 받는 중입니다…" 와 [다시 받기]. 맞춤 배율이 끝없이 커지던 것도 막음.
- 확대한 채 [이전 Rev] ↔ [현재 Rev] 를 오가면 왼쪽 위 빈 구석만 보이던 것 → 보던 자리 그대로.
- 전체화면 권한 경고 없앰.

hotfix144 내용 (143 → 144) — Valve · Instrument (valve41)
- South 도서 읽기: South Control Valve · Regulator 도서의 'INSTRUMENT SPECIFICATION' 양식(번호 2열 · 괘선 칸)을 읽습니다.
  예전에는 40쪽 도서가 Tag 없는 Datasheet 1개로 잡혔음 → 이제 Tag 마다 칸 값을 읽음.
- 다시 올리지 않아도 됨: 서버를 켤 때 Tag 없이 남은 도서를 새 방식으로 한 번 다시 읽습니다 (같은 파일의 옛 읽기 잔재 정리).
- Area 'South' 와 'QS' 가 따로 나오던 것 → 하나로.
- PURCHASE 칸의 TBC 는 Open Item 으로 잡지 않음.
- 읽지 못한 쪽 알림 (모든 타입): 모르는 양식 · 대부분 못 읽은 쪽 · Tag 없는 Datasheet 는 '읽지 못한 쪽' 으로 표시.
  도서 앞 INDEX (LIST OF TAGS) 와 읽은 Tag 를 대조 → Document Management 에 빨간 '일부 못 읽음' / '✓ INDEX n Tag 모두 읽음'.
- 서버를 처음 켤 때 가끔 'database is locked' 가 나던 것 고침.

LOGIC · 판넬 · 도서검토 · 3D
- hotfix143 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat.
2. 화면 위 띠 오른쪽에 '업데이트 150'. 서버 창에 'Restarting' 이 되풀이되지 않으면 정상.
   처음 켤 때 South 도서를 다시 읽느라 조금 걸릴 수 있습니다.
3. Valve: 공통 자료 > Valve Specification 에 Spec PDF 를 올린 뒤 Datasheet 에 'Spec Compliance' 코멘트가 붙는지.
4. P&ID 결과: EPIC 60장 Rev.B vs Rev.A 처럼 큰 도서에서 도면이 나오는지 · 확대한 채 Rev 를 바꿔도 보던 자리인지.
5. Globe Valve 등 South 도서: Tag 가 나오는지 · Document Management 의 '✓ INDEX … 모두 읽음' / '일부 못 읽음' 확인.
