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

## 2026-10-31 · valve20 — 상용 수준: 속도 · 간결한 UI · 시뮬레이션 (브랜치 ccr-efbe7e75-n915ze)
- 요청: 가볍게 · 끊김 없이 · 글 적게 · UI 개선 · 수천 번 시뮬레이션 · 상업 판매 수준.
- 속도: 데이터시트별 검토 캐시(메모리 + 디스크) · 프로젝트 판 키 · 워밍 · `_json()` · grid 캐시 → issues 250→30 ms · PMS 784→21 · 냉간 3.9 s→0.2 s · 990 DS 재시작 36 s→0.23 s.
- UI: 그룹 이슈 카드 · 한 줄 탭 · '?' 도움말 · 8 타일 · idle 표 렌더(Issue List 6.1→2.2 s @990) · 오류 토스트 · 버전 · DB 백업.
- 시뮬레이션 `spike/valve_sim.py`: 3,000건 recall .955/precision .906 → 10,000건 1.000/1.000 · 퍼즈 0 예외. 결함 6건 수정(R-PTFE · METAL/NYLON · LTCS · MR-03 · MR-13 · VR-09). 실자료 VR-09 2→20(진짜).
- 시험 48 · ui_audit 22/22 · 기준값 저장.

## 2026-10-31 · valve21 — 실자료 변이 재생 · 캐시 결함 · Area/Unit 화면 (브랜치 ccr-efbe7e75-n915ze)
- 시뮬레이션 2차: oracle 55 규칙 · `valve_mutate.py` 실자료 164 × 14 변이 87.8 % → 100 %. 결함: PMS Fire Safe 'HOLD(API 607)' Compliant → Review · 동료 다수 표기 분열 · NACE NA → Review.
- 화면: Grid 캐시 Response 재사용 → gzip 헤더 변조로 Valve List 멈춤(실제 결함) 수정 + 시험. Area/Unit 열·필터·머리·By Area 카드. Expert Note 접힘. 다시 시도 단추.
- 실측: 다음 Tag 55 ms · 쪽 130 ms. eval: PMS Fire Safe 10 Compliant→Review(의도) · 지문 불변 · 기준값 저장. 시험 50+1 · ui_audit 22/22.

## 2026-10-31 · valve22 — 진단 · 가벼운 목록 · 사용 설명서 · 추출 견고성 (브랜치 ccr-efbe7e75-n915ze)
- `/api/valve/health` + Settings 진단 · Issue List 필터 행만 재렌더(0.6→0.35 s) · 캐시 이력 제외(990 DS RSS 489→457 MB) · USER_GUIDE.md.
- 추출 시뮬레이션 `valve_sim_pdf.py` 380장 0.833→0.992(기울기 · Max/Nor/Min 경로 · Note 번호 표기 · NOTES 줄 · 괘선 위 낱말). 실자료 지문 불변 · diff_sim 0.
- 합성 10,000건 seed 23 재확인 1.000/1.000. 시험 53 · ui_audit 22/22.

## 2026-10-31 · valve23 — PDF 주석기 수준 Mark-up (브랜치 ccr-efbe7e75-n915ze)
- 요청: PDF Annotator 같은 주석 기능 · 매우 가볍게.
- 도구 15(밑줄·취소선·물결·스탬프 13종+직접·지우개 추가) · 색 7+분류색 · 굵기 4단 · 즐겨찾기 · '바로'. `comment.style` 열(검증) · PDF 주석 Underline/StrikeOut/Squiggly · 스탬프 Square+FreeText · ✓✗ Ink.
- 가벼움: 그리는 표시만 임시 SVG(rAF) · 펜 곡선. 시험 markup23 · 54 통과 · ui_audit 22/22.

## 2026-11-01 · valve24 — 주석 도구 완성 · 메뉴별/시연별 화면 (브랜치 ccr-efbe7e75-n915ze)
- 요청: PDF 주석기 목록(Stamp · Sticky Note · Typewriter · Text Box · Callout · Highlight · Cross Out · Underline · Arrow · Line · Rectangle · Oval · Polygon Line · Polygon) 전부 + 메뉴별 · 시연별 화면 한 장씩.
- 추가: 타자기 · 말풍선(callout 선 + 화살표) · 꺾은선 · 다각형 · DRAFT. PDF 주석 PolyLine/Polygon/Callout FreeText.
- 결함 3 수정: 화면 style 누락 · 팔레트가 직전 표시 재칠 · 꺾은선 Enter 가 편집 창까지. 시험 markup23 확장 · ui_audit 25/25.
- 화면 55장(메뉴·기능 31 + Mark-up 시연 24, 내보낸 PDF 포함) — 저장소 밖 zip.

## 2026-11-01 · valve25 — PDF 에 마크업 · 코멘트 그대로 · 공정 값 출처 문구 (브랜치 ccr-efbe7e75-n915ze)
- 요청: PDF 출력 시 마크업과 프로그램 코멘트가 PDF 위에 그대로 · 공정 값 의견은 "Datasheet 상 … 기준 / Ref. Process Data [문서] 기준 …" 으로.
- Mark-up PDF: 쪽 오른쪽 250pt 여백에 번호별 코멘트(넘치면 이어지는 쪽) + `bake()` 로 마크업 고정(기본). 선택 창에 두 옵션(기억).
- `matreview.proc_value`: Process Data 행 우선, 없으면 데이터시트 값 — MR-01·02·03·07·14 · VR-09·10 문구 "Based on Ref. Process Data <Doc> (p.N) …". Process Mismatch · Data Missing Required 에 문서 번호.
- 글 없는 마크업은 "Stamp 'APPROVED' on the PDF" 처럼. 리뷰 디스크 캐시 키에 VERSION. short 상한 120→160.
- 기준값 불변 · diff_sim 0 · sim 3,000 · mutate · sim_pdf 190 · ui_audit 25/25 · 시험 86(valve).

## 2026-11-01 · valve26 — 코멘트 말투 'shall be reviewed' (브랜치 ccr-efbe7e75-n915ze)
- 요청: "Revise 보단 설계사가 다시 검토할 수 있도록 shall be reviewed 느낌으로".
- 한 줄 코멘트의 'Revise.'(8곳) · '— correct.' → '… shall be reviewed.' MR-01·02 는 160자 안에 들도록 괄호로 줄임.
- 기준값 불변 · sim 3,000 · mutate · 시험 86(valve) 통과.

## 2026-11-01 · valve27 — 물 흐르듯 · 글자 줄임 · Rev B/C/D 자동 이어받기 (브랜치 ccr-efbe7e75-n915ze)
- 실측: 서버 ≤ 63 ms. 브라우저 990 DS Tag 이동 74~277 ms → 4~19 ms(Tag 목록 재생성 제거 · scrollIntoView 조건부). 필터 긴 작업 193 → 60~90 ms(chunk 80 · 게으른 행 · Collator). prefetch · decoding=async.
- 글자: 항상 보이던 긴 안내문을 한 줄로, 설명은 `?` 로.
- `revisions.py`: Dismissed/Confirmed 이어받기 · 'Not addressed since Rev A' · 칸 의견 복사 · rev_review(해결/미반영/새것). 화면 칩 · 목록 ✗N · 대시보드 '미반영'. `tests/test_valve_revision.py`.
- `spike/valve_rev_sim.py` 1,506 점검 1.000(발견: Dismissed 였던 지적을 새것으로 세던 것 수정). 실자료 00XV921 A→B 해결 5 · 새 3.

## 2026-11-01 · valve28 — Verification Engine: 모든 지적에 근거 · 48 항목 검증 보고 (브랜치 ccr-efbe7e75-n915ze)
- 방향(사용자): 엔진이 핵심, UI 는 신뢰·검증 수단. 실측: 지적 행에 맞대어 본 쪽 근거 0 % → `issues.add(evidence, basis, check)` 로 전 종류에 붙임.
- Excel Evidence/Basis 열 · PDF 코멘트 Evidence 줄 · Issues 카드 근거 링크. `checks.py` 레지스트리 48 → Checks 탭 · 대시보드 Coverage · Excel Verification 시트(n/a 이유 표).
- 실자료 164 × 48 = 7,872 (✓6,806 ✗426 –640). 시험 `test_valve_verification.py`. Revision 시뮬 1,500×3 = 55,223 점검 1.000.

## 2026-11-01 · valve29 — Phase 1 운영 신뢰성 (지시서 "Engineering Intelligence Upgrade") (브랜치 ccr-efbe7e75-n915ze)
- 계획 `docs/valve/PHASE1_PLAN.md` → 결정 5종 + 사유 분류(status 옆) · decision_log · Rule Performance · 규칙 버전/출처 · 변경 절차(자동 변경 없음) · 근거 추적.
- 판정 불변: `valve_snapshot_diff.py` 실자료 2,887 지적 차이 0 · eval 지문 불변.
- 성능 측정(`valve_perf.py`, 164/500/990 · cold/warm · 화면)이 찾은 것: Issue Excel 500 DS 105 → 6 s · Valve List 28 → 5.6 s · Mark-up PDF 2차 증가 182 → 42 s · 목록 화면 6,000행 상한(결함) 제거.
- 보고서 다섯 `docs/valve/valve29/`. 시험 99(valve).

## 2026-11-01 · valve29 — 특수 요구사항 한눈에 + Excel (사용자 요청)
- Valve List › **Special Req.** 탭: Area 합계(숫자 누르면 거름) + Tag × 요구사항 표(● / Not Req., 원문은 툴팁) + Excel(거른 그대로).
- API `/requirements` · `/requirements.xlsx` (Summary by Area · by Unit · By Tag · Info). 계산은 Valve List 와 같은 함수 — 수 일치 확인.
- 시험 +1 (전체 1,901 통과) · UI 25/25 · LINK OK.


## 2026-11-01 · valve29 — 메뉴별 화면 캡처 + 새 설치 첫 실행 결함 수정
- `spike/valve_menu_shots.cjs`: 빈 서버에 실자료 4종 Import → 메뉴 16화면 캡처 (out/valve29/menus, 저장소 제외).
- 결함: **새 설치의 첫 요청이 500** — 서버 준비 스레드와 첫 화면 요청이 빈 DB 에 같은 열을 동시에 추가(duplicate column: since). `store.connect` 첫 준비를 잠금 + 중복 열 무시. 시험 +1.

## 2026-11-01 · valve29 — "모든 동작이 빠르게" (사용자 요청)
- 측정 도구 `spike/valve_speed.cjs`: 동작 60여 개(메뉴 · 탭 · 검색 · 행 클릭 · Tag 넘기기 · 비교 창 · 확대)를 클릭→화면 안정 · 최장 멈춤으로 잼.
- 서버: 화면 답(summary · PMS · Process · 특수요구 · Rule Performance · Tag 규칙)을 **쓰기 전까지 재사용**(store.WRITES 커밋 카운터 + DB 최신 행 키) · 서버 켤 때 전부 미리 계산.
  990 DS 첫 진입 Rule Performance 1.5 s → 0.1 s · Settings 2.4 s → 0.1 s · summary 0.25 s → 0.005 s.
- 화면: Valve List 검색 · 필터는 행만 다시 그림(머리줄 · 미리보기 유지) · 입력 대기 200–250 → 90 ms · 가상 행 여백 축소 · 행 높이 기억 · 목록 둘을 한가할 때 미리 받음.
  990 DS Valve List 검색 0.5 s(멈춤 0.21 s) → 0.2 s(멈춤 0) · 탭 전환 멈춤 0.27 → 0.08 s.
- 숨은 결함: Issue List 에서 검색을 바꾼 뒤 Excel/PDF 를 받으면 **이전 검색어**가 적용되던 것 → 누를 때의 검색어로.
- 시험 +1(캐시가 결정 · 상태 변경 직후 바로 갱신) · 전체 1,903 통과 · UI 25/25 · LINK OK · 판정 스냅샷 차이 0.

## 2026-11-01 · valve29 — 입체 화면(시안 A) + 대시보드 카드 크게 보기 (사용자 선택)
- 시안 3종(A Soft Depth · B Glass · C Control Panel) 캡처 → 사용자가 A 선택. `body.d3` CSS 로 적용, Settings 에서 끌 수 있음.
- 대시보드 카드 제목/빈 곳 클릭 → 큰 화면(Esc · 바깥 · ✕), Review Status Table 은 전체 Tag. 큰 화면 행 클릭 → 그 데이터시트.
- 색 버튼(.on/.pri/레이어) 덮지 않게 범위 제한. UI 25/25 · LINK OK · 동작 측정 최장 멈춤 156 ms(전과 같은 범위).

## 2026-11-01 · valve29 — Excel 같은 열 필터를 모든 목록에 (사용자 요청)
- ▾ 팝업(정렬 · 검색 · 값 체크 · 건수 · 모두 선택 · 지우기). 큰 목록 5개는 데이터 단위, 나머지 표는 자동 장착(xfDom).
- 실자료 확인: Issue Type=Data Error 7 · Process Mismatch 42 · North 74 Tag — KPI 와 일치. 메뉴 이동 후 필터 유지.
- 990 DS 필터 ≈ 0.2 s. 정렬을 값 순위 방식으로(17k 행 JS 25 ms) · 가상 행 높이 재측정 생략.
- UI 25/25 · LINK OK · valve 시험 105 통과. `spike/valve_filter_check.cjs`.

## 2026-11-01 · valve29 — Accessory 지식 · 규칙 AC-01~05 (사용자 요청: Ball valve · DVC6200 · PT · SOL · ASCO 2oo2 · PST)
- 실자료 노트/GN 조사: GN15 Fisher DVC · GN13/7 PST+온라인 SOV 시험(DVC 경유) · GN20 PT 기본·Limit Switch 금지·안전계통 PT SIL2 · GN11/12/37 SOV de-energize-to-trip·Class H·potted.
- 지식 5개 추가(knowledge.KB acc.*) — 공개 제조사 문서 · IEC 61508/61511 근거, 값은 '현행 bulletin 확인' 명시. emerson.com 직접 열기는 세션 네트워크에서 막힘(검색 요약만 사용).
- 규칙 AC-01~05(데이터시트 + 자체 GN 만 비교). 실자료: AC-05 48(SOV 2~3개, 표결 미기재) · AC-03 49(Note) · 나머지 0. 기존 지적 변경 0.
- 검토 캐시 키에 규칙 코드 지문(`_RULES_FP`) 추가 — 규칙이 바뀐 꾸러미는 VERSION 그대로여도 다시 계산(옛 캐시가 새 지적을 가리는 일 방지).
- 시험 +1 · valve 106 · eval baseline 갱신(AC 두 줄만) · sim 1.000 · mutate 100% · rev_sim 7,175/7,175.

## 2026-11-01 · valve29 — 검증 + 가볍게 (사용자 요청)
- 검증: pytest 1,904 통과 · UI 25/25 · LINK OK · 판정 스냅샷(기존 2,887 변경 0) · 필터 점검 · 동작 60개 속도(최장 멈춤 0.37 s = Valve List 재진입, 나머지 ≤ 0.14 s).
- 가볍게: Process/PMS 가상 행(990 DS DOM 22만 → 3만) · 정적 파일 해시 캐시 + 화면 답 gzip 보관 + ETag 304(재방문 229 KB → 2 KB) · 서버 메모리 −12 %(990 DS). 자세히 DESIGN §34-5.
- 측정 도구: /tmp 의 weight2.cjs(전송량) · nodes.cjs(요소 수) 는 임시 — 필요하면 spike 로 옮길 것.

## 2026-11-01 · valve29 — 첫 화면 기준 문서 Rev · 날짜 + 대시보드 Globe/Butterfly/PSV 메뉴 (사용자 요청)
- `app/valve/docrev.py`: PDF 머리(Doc. No. · Rev.)와 개정표(같은 줄의 Rev 토큰 + 날짜, 가장 늦은 날짜 행)를 글자층에서 읽음. Process Data 묶음 안의 PR-DTS 17종도 각각. 업로드마다 한 번 읽어 document.info['rev'] 에 보관.
- 실자료: PMS 98-98-PI-SPC-00001 Rev 0 · 20/Sep/2026 · Approved For Construction with Hold / Process CO2S-SSG-IN-REQ-00009 Rev 0, DS 17종(A 8 · B 9, 최신 08/09/2026) / Datasheet Rev 0 139 · A 13 · B 12, 최신 19/9/2026.
- 대시보드 dashboard.html: CO2 PJT › Datasheet 아래 Globe Valve · Butterfly Valve · PSV (준비 중 화면). APP_VERSION 2026-11-01.1, 변경 이력 기록. 대시보드 zip 은 DASHBOARD 세션이 병합해 냄.
- 시험 +2 (1,906 통과) · UI 25/25 · LINK OK.


## 2026-11-01 · valve29 — 회사 전달 꾸러미 3개 + 회사 Claude Code 인계 (사용자 요청)
- P&ID 서버: `out/PID_dev+ops_valve29_2026-11-01.zip` (pack_delta, 기준 9429f4f → e39cfda, 32 파일, 기준판 적용 충돌 0).
- 대시보드: `dashboard_patches/UPDATE_from_v16.51_VALVE2_menu.zip` (make_patch --any --mark, delivered.txt 기록).
- 회사 개발용: `out/VALVE_devkit_valve29_2026-11-01.zip` (docs/valve · handoff · other_log · spike/valve_* · CLAUDE.md 는 넣지 않음) — `C:\Claude\PID_dev` 에 풀기.
- 안내 · 첫 지시문: `docs/handoff/VALVE_COMPANY_START.md`. 인수인계 '지금 상태' 를 valve29 끝 기준으로 고쳐 씀.

## 2026-11-01 · 개발 담당 나눔 (사용자 결정)
- 대시보드 · P&ID · LOGIC · PANEL = 개인 Claude Code 개발 + zip 전달. Valve 분석 툴(Ball · Globe · Butterfly · PSV) = 회사 PC Claude Code 가 회사 PC 에서 개발.
- `config/release_sources.json`: VALVE 병합 대기 제거 · `company_owned` 경로 추가 → `spike/pack_delta.py` 가 개인 꾸러미에서 Valve 경로를 뺌(--only 로 명시할 때만 예외). CLAUDE.md §0 표 · §3, branches.md 갱신.
- 회사 운영 반영 도구 `spike/valve_deploy_to_ops.py` + `.bat`(시험 → 백업 → app/valve · app/static/valve 만 복사 → 8000 재시작) · `valve_rollback_ops.bat`. 시험 `tests/test_company_owned.py`.
- devkit 다시 만듦(위 도구 + restart_pid_server.py + 안내문 §5~7).

## 2026-11-02 · 회사 적용 확인 (사용자)
- valve29(P&ID 서버) · UPDATE_from_v16.51_VALVE2_menu(대시보드) · VALVE_devkit_valve29 · 안내문 — 모두 적용했다고 사용자 확인. 대시보드 기준점은 delivered.txt 마지막 줄(e39cfda).

## 2026-11-02 · valve30 — 회사 PC 사진 피드백 다섯 + 개발 위치 되돌림 (사용자)
- 사용자: "우선 여기 개인 클로드에서 개발을 이어서 진행한다" → CLAUDE.md 표 · §3, release_sources 설명, 인수인계 갱신 (hotfix 에 Valve 를 싣지 않는 규칙은 그대로).
- 고침: Mark-up/PDF 도구줄 흰 바탕 흰 글씨 · Ctrl+휠 확대 · PMS/Process 미리보기 높이/폭 끌기 · 미리보기 화질 · Bore 지적 문구(판정 동일, 28건 문구만).
- 점검: valve 시험 114 · eval baseline unchanged · 스냅샷 changed 28(문구만) → snapshot_valve30 저장 · UI 25/25 · LINK OK. VERSION valve30.

## 2026-11-02 · valve31 — 코멘트 한글 · 영어 + 출력 언어 선택 (사용자 요청)
- `app/valve/i18n.py`(규칙별 고정 한국어 틀) · `description_ko` · 화면 영어+한글 · Settings 표시 언어 · Excel/PDF 출력 창 언어(en/ko/both).
- 실자료 2,891건 한글 100 % · PDF 옆 코멘트 한글 글꼴 확인 · 스냅샷 변경 0 · eval unchanged · 전체 1,984 통과 · UI 25/25 · LINK OK. VERSION valve31.

## 2026-11-02 · valve32 — 올린 문서 지우기 · 휴지통 · 되돌리기 (사용자 요청)
- 🗑 → 함께 빠지는 것 확인 창 → 휴지통(JSON) · 되돌리기(같은 id) · 원본 파일 보존 · audit 'delete-doc'/'restore-doc'.
- 실화면(vt_ui 사본): 문서 7 → 6 → 되돌리기 7 · 시험 +1 (전체 1,985) · 스냅샷 변경 0 · UI 25/25 · LINK OK. VERSION valve32.

## 2026-11-02 · valve33 — 첫 화면 Valve Summary 표 (사용자 요청)
- API valve-summary + 대시보드 카드: 묶기 3종 · 색 농도 · 비율 · 특수요구 모두 · 숫자 → Tag 목록 → Valve/Issue List 걸러 열기 · Excel · 접기.
- 실자료 합계 = Valve List Excel Summary 와 같음. 시험 +1 (1,986) · 스냅샷 0 · UI 25/25 · LINK OK. VERSION valve33.

## 2026-11-02 · valve34 — FileDataError 반복(저장본 재사용) 고침 + 상태 창 닫기 (회사 PC 사진)
- 원인: 내용 해시 저장본이 깨져도 같은 내용 업로드마다 재사용. 업로드 시 크기 · 해시 검증 후 다시 씀, 처리 전 해시 확인, open_pdf 재시도 + 실제 이유 표시.
- 상태 창 ✕ · 모두 닫기 · 오류 시 자동 내려받기 안 함. 시험 +1 (1,987) · 스냅샷 0 · UI 25/25 · LINK OK. VERSION valve34.


## 2026-11-07 · valve35 — 코멘트 정리: Typical · 블럭 · 상세보기 (사용자 요청)
- `digest.py`: 한 쪽에 붙은 Data Missing(DM-01/02) 3개+ = 블럭 코멘트 하나 ('Process data missing — N items (…); ref. …') · 같은 코멘트 2 Tag+ = Typical 한 줄.
- Issue List '정리 보기 | 낱개 전체' · ▸ 상세 · 묶음 일괄 결정 · Excel 'Comments (Typical)' 시트 · Mark-up PDF 블럭 박스 (group=1, 기본 켬).
- 실자료 2,935 → 276. 판정 스냅샷 변경 0 · 시험 +2 (1,989) · UI 25/25 · 필터 · LINK OK. VERSION valve35.
- 같은 날 답: Fugitive 카운트 = 칸 · Note · General Note 의 fugitive/ISO 15848/TA-Luft (조건부 GN 미구분 — 사용자 결정 대기).

## 2026-11-07 · valve36 — 밸브 모형을 Anatomy 방식으로 (사용자 요청 "세션 7 참조")
- 세션 7 ic-3d-builder 엔진(af748c7: refdata · anatomy · viewer)을 `app/static/valve/anatomy.js` 한 파일로(`spike/mk_anatomy.py`) — 이름 AnatomyViewer · 여러 부품 강조 + 나머지 반투명.
- Data 탭 Valve Part: 데이터시트 크기 · CL · Bore · 구동기로 모형, 칸 → 부위 주황 · 부품 → 관련 칸. 평면 SVG 삭제.
- 시험 +1 · 판정 변경 없음. VERSION valve36. 꾸러미는 통합 방식(오케스트레이터) 사용자 확인 대기.
