PID 업데이트 hotfix138 (2026-11-13) — 통합 업데이트 (P&ID · LOGIC · 판넬 · 도서검토 · Valve · Instrument · 3D)

먼저 읽어 주세요
- 덮어쓰기: 회사 PC 에 hotfix131 ~ 137 어느 판이 있든, 적용하면 이 판(138)이 됩니다.
  회사 PC 에서 따로 고친 파일도 원본을 backup\hotfix138_<시각>\ 에 둔 뒤 새 판으로 덮습니다.
- hotfix137 을 넣지 않았어도 이것 하나면 됩니다 (137 내용 포함).
- 대시보드도 v17.47 이상으로 함께 올려야 Instrument 메뉴 · CO2 PJT 현황판이 보입니다.
- 회사 Claude Code 로 엔진을 고친 것이 있으면 적용하기 전에 '엔진 개선값' md 를 먼저 뽑아 보내 주세요.

무엇이 바뀌었나 (hotfix136 → 138)
Instrument Datasheet 자동 검토 (새로 · Valve 검토를 넓힘)
- 계기 13종 양식을 알아보고 읽습니다: FT · PT/PDT · LT · GWR · TT · TG · PG · DPG · Mag. Level Gauge · RO · Analyzer · Control Valve · On-Off Valve.
- 검토: 빠진 필수 칸 · Process Data 는 PDS 기준 대조 · PMS · Process Line List(Line 의 Design P·T) · Control Valve Cv(IEC 60534) 계산 확인.
- Instrument List · IO List (PDF) 를 Datasheet 기준으로 대조 — List 누락 · 값 다름 · List 에만 있음, Excel 내보내기.
- 공통 자료 메뉴: PDS · PMS · Line List · Instrument Index · IO List 를 한 번 올리면 모든 Valve · Instrument 화면이 함께 씁니다.
- 현황판 · Item 별 화면 · 문서 / Revision 현황 · 검토자 도구(지적마다 확인 · 고쳐 쓰기 · 사유 달고 빼기 — 다음 Rev 로 이어짐) · Mark-up PDF.
- Area 규칙: Tag 앞 번호 · Instrument Index AREA 로 Area · Sub-area · Unit 를 나눕니다.
- 값이 채워진 실제 Datasheet · List 로는 아직 확인하지 못했습니다 — 회사에서 처음 넣어 볼 때 결과를 사람이 확인해 주세요.

Valve
- Datasheet Review 에서 PDF 가 빈 화면으로 뜨던 것(hotfix137): 저장본을 못 열면 안내 + [Document Management 열기], 목록에 '원본 손상',
  같은 파일을 다시 올리면 복구, 보관본을 .bin 이름으로(처음 켤 때 한 번 옮김). ★ Datasheet2.pdf 를 한 번 다시 올려 주세요.
- 첫 화면: Datasheet Tag 가 Process Data 에 있는지 · 문서 Rev · 구역(valve39).
- Globe · Butterfly · PSV 는 지금처럼 Valve 화면에서 (PSV 는 Valve 쪽이 맡음).

P&ID · LOGIC · 판넬 · 도서검토 · 3D 계측제어
- hotfix136 과 같습니다.

적용
1. 압축을 전부 푼 뒤 apply_to_PID_dev.bat → 확인 → apply_to_PID_ops.bat (서버 재시작 안내를 따르세요).
2. 화면 위 띠 오른쪽에 '업데이트 138' 이 보이면 새 판입니다. 안 보이면 서버를 다시 켜고 Ctrl+F5 한 번.
3. 대시보드 › 실행 프로젝트 › CO2 PJT › Datasheet › ▸ INSTRUMENT 에서 계기 화면이 열리는지 확인.
