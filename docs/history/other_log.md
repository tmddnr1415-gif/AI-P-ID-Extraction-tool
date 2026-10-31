# other 회차 기록 (2026-10-30 부터 · 옛 기록은 같은 폴더의 CLAUDE_archive_*.md)

새 회차를 **끝에** 5~15줄로 덧붙인다.  이 파일은 자동으로 읽히지 않으니 길어져도 된다.

## 2026-10-31 · VALVE 세션 시작 — valve01 (브랜치 ccr-efbe7e75-n915ze)
- 새 모듈 Valve Datasheet 검토: P&ID 서버 `/valve` (app/valve · app/static/valve), 대시보드 메뉴 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve (APP 2026-10-31.2).
- 참조 자료(EGG 분할) 분석: Datasheet 456쪽 = 164 데이터시트(On/Off 140 · MOV 24), TBE 5개 Appendix 시트 164 Tag(164/164 일치), Process Data 61쪽, PMS 374쪽(Class 37종). → docs/valve/DESIGN.md
- Phase 1 + Revision 비교 기본. Process/PMS 는 화면 틀(Not Evaluated · MOCK 은 버튼으로만).
- spike/pack_delta.py 에 `--only` (모듈 꾸러미: 딱지 · 기준 파일 안 건드림). config/release_sources.json 에 VALVE.
- 시험 tests/test_valve.py 7개 · 전체 1,836 통과.

## 2026-10-31 · valve02 — 지적 사항 · 설계사 전달물 · 실제 PMS (브랜치 ccr-efbe7e75-n915ze)
- 요청: 잘못되거나 없는 Data 를 PDF 에 표시해 같이 출력 · Excel(Tag · Doc · Sheet · Page · 무엇이 문제) 로 설계사에게 · 분석 끝나면 Excel 도 · Excel 칸 → PDF 그 자리 · 재질 표기 차이를 같게.
- issues.py(규칙) · exports.py(Issue List xlsx · 인쇄 플래그 Mark-up PDF + Issue Summary 쪽) · material.py(규격·등급 비교) · pms.py(실제 PMS · 지역 QN/QS).
- 화면: Valve List / Issue List + PDF 미리보기 실시간 연동, Issues 탭, 실제 PMS 화면(데이터시트 · PMS 나란히), 분석 끝 자동 내려받기, ?ds=&key=&page= 바로 열기.
- 실자료: Data Error 3 (없는 General Note 46) · PMS 재질 Non-Compliant 0 · Body Review 32→15 · Valve List 실제 차이 571→539.
- 시험 21개 · 전체 1,850 통과.

## 2026-10-31 · valve03 — 실패 원인 분석 · 성능 · 사용자 Mark-up (브랜치 ccr-efbe7e75-n915ze)
- 요청: 시간이 걸려도 실패 원인을 분석해 상용 수준으로 · 사용자가 직접 마크업.
- 평가 도구 spike/valve_eval.py(실자료 · 기준값은 개수만) 로 재고 고침: 짝 실패 69→1 · 오독 11→0 · Data Missing 오탐 748→0(Process DS 참조 데이터시트) ·
  PMS Review 113→75 · TBE 비교 가능 칸 일치 92.9 % · 잘못된 Note 참조 2건 새로 잡음 (DESIGN §10.1).
- 강건성: A3 등 크기 다른 쪽 정규화 · 회전 쪽 · 암호/손상 PDF 안내. 속도: 13 ms/쪽 · 지적 캐시 · Mark-up PDF 314→40 KB/데이터시트.
- Mark-up 도구 10종(선택 · 사각형 · 구름 · 원 · 형광펜 · 선 · 화살표 · 펜 · 글상자 · 메모), 분류 → Issue 종류(Error=Data Error …), 옮기기 · 크기 · 지우기 ·
  되돌리기/다시, PDF 주석 종류 그대로 내보냄 (DESIGN §10.3).
- 시험 30개 · 전체 1,860 통과. 꾸러미 valve03.

## 2026-10-31 · valve04 — P&ID · LOGIC 개발 원리 차용 (브랜치 ccr-efbe7e75-n915ze)
- 요청: PID 분석 · LOGIC 분석 개발 원리에서 빌릴 것이 있으면 참조.
- 지문 게이트(`valve_eval.py --check`, 17,207칸) · 이중 괘선 문턱을 상수로 빼고 빈 띠 실측(틈 5~7 · 칸 21+ pt) · 'TBE 와 다름'을 쪽 글자로 독립 확인 ·
  사전 밖 라벨 1,920칸 = MOV 항목(버려지지 않음) 확인.
- 검토 피드백(VOC): `/api/valve/projects/{pid}/feedback.json` + Reports 버튼 · `spike/valve_voc.py` 채점(규칙별 정밀도 · 다시 돌리기) · 판정 모듈이 안 읽음을 AST 시험.
- 차등 시뮬레이션 `spike/valve_diff_sim.py`: 140장 12,470칸 불일치 0. 화면 자기검증 `spike/valve_ui_audit.cjs` 22/22.
- DESIGN §11 (차용표 · 단일 판정 자리). 시험 33개.
