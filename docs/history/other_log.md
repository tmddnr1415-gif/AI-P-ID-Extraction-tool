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

## 2026-10-31 · valve05 — 456쪽 전수 눈 대조, 오류율 3.54 % → 0.009 % (브랜치 ccr-efbe7e75-n915ze)
- 요청: 모든 쪽을 눈으로 본 것과 프로그램 분석의 오차를 재고 5 % 미만(가능하면 100 %)으로.
- 방법: 쪽 그림 + 읽은 것 꾸러미(`spike/valve_visual_pack.py`) → 검토 에이전트 46묶음이 항목별 판정(오류는 PDF 글자 층으로 확인) → 채점(`valve_visual_score.py`) → 고침 → 바뀐 1,324줄 재판정.
- 1차 21,482항목 760오류(3.54 %) → 2차 오류 0 + 남은 2(도면 Doc. No. 오타, Data Error 로 지적) = 0.009 %.
- 고친 원인: 숨은 글자(그리기 순서) · 겹친 같은 글자 · 3pt 줄 묶기 · Notes 바닥글 · Form 102 단일 열 · 번호 없는 오른쪽 열 · 단위만 있는 칸 · 'Sheet|3|of|3' · 제목 줄바꿈 · ATTACHMENT · HOLD 목록.
- 새 지적: sheet 2 Doc. No. 불일치 · 반복 머리(Tag/PID/Service/Line) 불일치 — 실자료 3건. 시험 36개. 기준값 지문 541753c612ed.

## 2026-10-31 · valve06 — Valve List Excel 에서 Vendor 행 삭제 (브랜치 ccr-efbe7e75-n915ze)
- 요청: 엑셀에서 AMPO · OMS · NEWAY 행을 다 삭제.
- `tbe._drop_vendor_rows`: 기준 TBE 양식을 읽자마자 Tag 블록마다 Requirement 행만 남김(값 · 서식 · 메모 · 행 높이를 한 번에 올리고 병합 재설정 — openpyxl delete_rows 는 병합 · 높이를 안 옮김). `build(vendor_rows=True)` 면 유지.
- 실자료: 164 Tag 모두 한 줄씩, Vendor 칸 0, 링크 · 메모 유지. 시험 36개 통과.

## 2026-10-31 · valve07 — UI/UX 개선 패키지 + Phase 3 Process Data (브랜치 ccr-efbe7e75-n915ze)
- 요청: 개선 패키지(CLAUDE_CODE_UI_IMPROVEMENT_PROMPT · 목표 그림 · 캡처 31장)대로 감사 → P0~P6 구현 · 데이터시트 칸을 누르면 밸브 부위 그림 · 남은 일 전부.
- 감사 `docs/valve/UI_UX_AUDIT.md`(해상도 실측: 1366 에서 도구줄 124 px · PDF 646 px · 탭 3줄) → 변경 `UI_UX_CHANGELOG.md`.
- P0: 머리 띠 · 접이식 px 패널 · 한 줄 도구줄(36 px) · 레이어 칩 · Mark-up 줄 접기 · Tag 목록 2줄 · 탭 배지 · 밸브 부위 SVG(1366 PDF 835 px).
- P1~P6: 대시보드 5×2 + Issues by Category + KPI 필터 이동 · 목록 ↑/↓/Enter · Revision 같이 움직이기 + 비교 Excel · PMS 안내 · 내보내기 묶음/확인/상태 · Settings 단축키.
- P5 실제: `app/valve/process.py`(괘선 열 띠 · 단위 · 기준 규칙) — 68 Tag · Mismatch 42 · 지적 'Process Mismatch'. MOCK 제거.
- 회귀: pytest 38 · 전체 통과 · eval --check 불변 · diff_sim 0 · ui_audit 22/22 · 1920/1600/1366 캡처(out/ui_before · ui_after, 저장소 밖).

## 2026-10-31 · valve08 — 빈 Process Data 항목 전부 지적 (브랜치 ccr-efbe7e75-n915ze)
- 요청: Process Data 가 없는 것은 전부 표기. (valve03 의 'Process DS 참조면 제외' 를 사용자가 뒤집음)
- issues.py: PROCESS DATA 블록 전 항목(section process + Sour/Corrosive/Erosive/Toxic/Stroke) · Max/Nor/Min 은 셋 다 비면 한 건 · 참조 문서 명시 · Process Data 값을 Expected 로.
- 실자료 Data Missing 0 → 2,529 (164 Tag). 읽기 지문 불변(바뀐 칸 0). 시험 38개(옛 'skips' 시험을 새 규칙으로 바꿈). 기준값 다시 저장.

## 2026-10-31 · valve09 — HOLD / TBC 전부 지적 (브랜치 ccr-efbe7e75-n915ze)
- 요청: HOLD 도 comment — 빨리 HOLD release 하고 값을 입력하게.
- 전: 필수 18칸 · 값이 HOLD 로 시작할 때만 → 실자료 0건. 후: 모든 칸 · Note, 값 어디에 있어도(HOLD (…) · Hold-1 → HOLD 목록 글) · Major · 약어 설명 줄 제외.
- 실자료 Open Item 84 (Area classification 14 · Fire Safe 11 · SOV Tag Hold-1 48 · Typical TBC 7 · Note 4). 읽기 지문 불변. 시험 39개.

## 2026-10-31 · valve10 — PMS 대조 점검 · 특수 요구사항 · 재질 검토 의견 (브랜치 ccr-efbe7e75-n915ze)
- 요청: PMS 기준 검토가 맞는지 학습 · 재질 검토 의견을 전문적으로 · Note 의 Special Requirement(PFP · Fugitive …) 가 Excel 에 잘 나오는지.
- PMS: PDF 와 대조 — Trim/Stem 을 Class 머리 Trim(1A1A '13CR/HF', Gate/Globe 용)과 비교하던 오류 → Ball 품목 '316 SS BALL/STEM' 우선. Review 16 → 0. 남은 지적은 실제 PMS 공백(3R1B3 Ball 없음 · 6C0K8 10" · XC0K8 22" …).
- PMS 머리에서 P-T 표 · Service · Class Notes · Item Notes 도 읽음(READER_VERSION 2, 옛 json 자동 재읽기).
- 특수 요구사항 `requirements.py` 15종 → Valve List 'Special Requirements (Notes)' 열 · Summary 탭. 164 Tag 모두 나옴.
- 재질 검토 `matreview.py` MR-01~15 (시트 온도 · P-T · 저온 본체 · CO2 탄소강 · NACE 316/CS/17-4PH/볼트 · HF · Dual grade · RGD · Fire-safe · Service). 실자료 Action 5 · Confirm 29 → Issue 'Material Review'. Material 탭 · Valve List 열.
- 시험 41 · eval --check: 바뀐 것은 Trim/Stem 16(원인 위) + 새 F 절, 읽기 지문 불변 → 기준값 저장 · diff_sim 0 · ui_audit 22/22.

## 2026-10-31 · valve11 — Ball Valve 엔지니어로서 검토 (브랜치 ccr-efbe7e75-n915ze)
- 요청: 전달한 Datasheet · PMS 를 디테일하게 학습하고 Ball Valve 전문 지식을 기본으로 전문 엔지니어로서 검토.
- LLM 없이(원칙 §4.3): 지식표 `knowledge.py` 28항목(API 6D · ISO 17292 · B16.34 · B16.5/47 · 누설 · Fire · ISO 15848 · NACE · SIL · 설계 · 재질) → BALL_VALVE_KNOWLEDGE.md 생성.
- 설계 규칙 `expert.py` VR-01~15 + 학습 PC-01(같은 Piping Class 데이터시트 다수 값, 5개 이상 80 %). 참조 칸('Note 2')은 Note 글까지 읽음.
- 실자료: VR Action 3(2″ 에 B16.47-B) · Confirm 44 · PC-01 6. 웹으로 17-4PH · 316 한계 · Floating 관행 확인(관행 값은 '회사 사양 우선' 으로 표기).
- 화면: Expert 탭 · Settings › Ball Valve 지식 · Issue 'Valve Review' · Excel 'Expert Review (Tool)'. 시험 42 · eval 은 F 절만 이동(읽기 · PMS 불변) · diff_sim 0.

## 2026-10-31 · valve12 — 설계사 코멘트는 핵심만 (브랜치 ccr-efbe7e75-n915ze)
- 요청: 설계사 주기 위한 코멘트는 핵심만 간결하게.
- MR/VR/PC 규칙마다 `short` 한 줄(문제 · 값 · 할 일, ≤120자 시험) → Issue List · Mark-up PDF · Valve List. 긴 설명 · 근거 · 지식은 Expert 탭만.
- Data Missing · Open Item · Note 참조 오류 · Revision 문구 줄임(`issues._cut` 낱말 단위 자르기).
- 평균 길이 Material/Valve 350→68 · Data Missing 136→80 · Open Item 93→56. eval 기준값 불변 · 시험 42 · 전체 1,872 · ui_audit 22/22.

## 2026-10-31 · valve13 — 설계사용 출력 때 Issue Type 고르기 (브랜치 ccr-efbe7e75-n915ze)
- 요청: PDF 에 설계사 코멘트 · Excel 출력 시 어떤 issue type 을 리스트업할지 선택.
- valve.js `pickTypes`: 종류별 건수 · 한글 설명 · 전체/모두 끄기/설계사용 기본 · 선택 기억(LS valve.xtypes). 출력 단추 5곳 모두 거침. 서버는 기존 `types=`.
- 확인: Material+Valve Review 만 → Excel 89행(그 두 종류만) · PDF 548 → 199쪽. 시험 43 · ui_audit 22/22.

## 2026-10-31 · valve14 — Issue List · 전체 Valve List 를 Area · Unit 별로 (브랜치 ccr-efbe7e75-n915ze)
- 요청: 설계사용 Issue List 와 전체 Valve List 를 Excel 로, Area(North · South · Brownfield) · Unit 별 Excel 필터.
- `location.py`: 제목 NORTH/SOUTH/W15, '(SYSTEM xx – UNIT yy)' = Brownfield(Note 의 'South Brownfield System 19' 근거), Unit = 제목 → P&ID → Tag. 표지/장 번호 불일치 · 표지 없는 Rev 보완.
- Issue List: Area · Site · Unit 맨 앞 + 필터, Summary by Tag 같은 열 + Material/Valve Review. Valve List: 'All Valves' 시트(164행) + 종류 시트 Area/Site/Unit 열 + 필터.
- 실자료 North 74 · South 69 · Brownfield 14 · W15 7. 시험 44 · 전체 1,874 · ui_audit 22/22.

## 2026-10-31 · valve15 — Area · Unit 별 Tag 번호 규칙 학습 (브랜치 ccr-efbe7e75-n915ze)
- 요청: Area 별 Unit 별 Tag numbering procedure 를 학습. 받은 파일에 절차서 문서 없음 → 프로젝트 Tag(데이터시트 164 · Process Data 68)에서 배움.
- `tagrules.py`: 구조 · 접두 출처(Unit / 제목 System / P&ID System) · 번호 자릿수 · 고정 앞자리 · 구분 · A/B · 계열↔P&ID. Brownfield North U84(08SDV) 와 South U84(84XV) 는 Site 로 나눔.
- 결과: North 98+기능+␣980nnn(계열 1~4 = P&ID 띠) · South 98+기능-nnn · W15 315+기능␣980nnn · Brownfield 접두 = 제목 SYSTEM(North) / UNIT(South).
- 검사 TG-01~05 → 실자료 TG-05 4건(ESDV Fail Open). Settings › Tag Numbering 표 · All Valves 에 Tag 부분 열. 시험 45 · 전체 1,875 · eval 불변 · ui_audit 22/22.

## 2026-10-31 · valve16 — No. 열과 Summary 시트 (브랜치 ccr-efbe7e75-n915ze)
- 요청: 앞에 No. 가 있어야 하고 Summary 도 있어야 한다.
- Issue List: 'Summary' 시트(Area · Site · Unit × Issue Type, Major · Minor · Tags, By Area) · Summary by Tag 에 No. · Area 순 정렬.
- Valve List: 'Summary' 시트(Area · Site · Unit × Valve Type, Open Issues · Tags with Action · New/Updated) · All Valves · Datasheet Notes 에 No.
- 실자료 확인(164 Tag · 2,823 지적), 시험 45 · 전체 1,875 · ui_audit 22/22.

## 2026-10-31 · valve17 — Issue List Area 순 · All Valves 요구사항 열 (브랜치 ccr-efbe7e75-n915ze)
- 요청: Issue List 시트도 Area 별 정렬 · Valve List All Tag 에 Note 의 중요 내용(PFP · fugitive class 등)을 각 열로.
- exports: Area → Site → Unit → Tag 정렬(Tag 안 순서 유지). requirements.columns: 종류별 열, 데이터시트 줄 답 우선(PFP 줄 Not Required 면 그 답), 세부(Class A · SIL 2 · 3.2), 출처.
- hardness 세부 'HB 160' 형도 읽음. 시험 46 · 전체 1,876 · ui_audit 22/22.

## 2026-10-31 · valve18 — Issue List 'Summary by Area' 시트 (브랜치 ccr-efbe7e75-n915ze)
- 요청: Issue List 에도 Area 별 Summary 시트 추가.
- exports._area_sheet: Area 한 줄씩(Units · Tags · Total · Major/Minor · 종류별 · Status별) + Area × 종류 × Severity 표. 시트 순서 Issue List · Summary · Summary by Area · Summary by Tag · Info.
- 시험 46 · 전체 1,876 · ui_audit 22/22.

## 2026-10-31 · valve19 — Valve List 'Summary by Area' 시트 (브랜치 ccr-efbe7e75-n915ze)
- 요청: Valve List 에도 Area 별 Summary 시트 추가.
- tbe._area_sheet: Area 한 줄씩(Units · Tags · 종류별 · Open Issues · Action · PFP Required · SIL · Fire Safe HOLD · New/Updated) + Area × Valve Type(Size · Rating). Summary 와 All Valves 사이.
- 시험 46 · 전체 1,876 · ui_audit 22/22.
