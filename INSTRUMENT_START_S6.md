# 6. Datasheet 자동 검토 세션 — Instrument 검토 개발 시작 지시 (2026-11-12 · 사용자)

> 이 파일은 **사용자가 6 세션에 직접 주는 지시**입니다. 첨부: 빈 양식 PDF 15종 · Process Line List 엑셀 2개 (사용자가 함께 올림).

## 먼저 읽을 것

1. `docs/handoff/valve.md` — 지금 판 **valve39** (브랜치 `ccr-efbe7e75-n915ze`) 에서 이어서 개발
2. `git show origin/claude/trusting-cray-v68axq:INSTRUMENT_REVIEW_PLAN.md` — 기획안 (2장 양식 조사 · 3~6장 할 일 · 단계)
3. `git show origin/claude/trusting-cray-v68axq:CONVENTIONS.md` — 규약 v2: **개발 · 시험 · 커밋 · 푸시만**, zip · 번호 매기기는 오케스트레이터

## 사용자 결정

- **IO List · Instrument List 는 나중에 준다** — 지금은 만들지 않는다.
- **지금 받은 자료로 구축하고 개발한다.**
- **모든 Datasheet 에서 Process Data 의 기준은 PDS 다.**

## 할 일

1. **Valve 검토(/valve, kind=…)를 Instrument 전체로 넓힌다.** 사용자가 Item 칸별로 값이 채워진 Datasheet PDF 수십~수백 장을 넣으면 Valve 처럼 식별 · 읽기 · 검토 · 현황판 · 문서/Rev 관리.
2. **번호 칸 읽기 일반화 + 양식 카드** — 한 틀(번호 행 → 칸 이름 → 값 · Max/Nor/Min/Unit · Yes/No · Notes) + 양식마다 카드(칸 번호 ↔ 칸 이름 ↔ 표준 이름 · 구역 · 꼭 있어야 할 칸). 새 양식은 카드만 더하면 읽히게.

   | 새로 | Form · 꼬리표 · 칸 · 종이 |
   |---|---|
   | FT | 313 · R1.02 · 1~48 · A4 |
   | PT / PDT | 601 · R2.02 · 1~48 · A4 |
   | LT | 506 · R1.03 · 1~48 · Letter |
   | GWR | 번호 표시 없음 · 제목란 다름 · 1~50 · Letter (칸 구성 · 파일 이름으로 식별) |
   | TT | 801 · R2.00 · 1~30 · A4 |
   | TG | 803 · R2.02 · 1~45 · Letter |
   | PG | 605 · R2.00 · 1~47 · Letter |
   | DPG | 606 (파일 안 꼬리표 605_R2.00 — PG 카드 공유) |
   | Mag. Level Gauge | 505 · R2.00 · 1~50 · Letter |
   | RO | 310 · 꼬리표 000_R1.01 · 1~41 · Letter |
   | Analyzer | 203 · R11 · 1~40 · Letter |
   | (유지) | 101 Control Valve · 80 On-Off · 701 PSV |

3. **Process Data = PDS 기준** — 모든 Item 의 Operating/Design P·T · Fluid · Phase · Density · Flow 등을 PDS 의 같은 Tag 와 대조. PDS 에 Tag 가 없으면 '없음'.
4. **공통 검토** — 빠진 칸(카드의 필수 칸) · PMS(Class → Rating · 재질) · **Process Line List 대조**(Datasheet Line No. → Pipe Class · Design P·T · Size; Line 의 Design 이 Datasheet 보다 높으면 지적). Item 별 규칙은 근거 있는 것만 · 사람 확인 표시.
5. **값이 채워진 Datasheet 는 아직 없다** — 빈 양식에 시험 값을 써 넣은 시험 PDF 로 시험한다. 판정 값은 지어내지 않는다 (시험 자료임을 표시).
6. **화면** — 같은 /valve 화면에 Item kind 추가 (프로젝트 공간 분리 · valve37 방식). Document Management 에 Process Line List 칸.
7. **지금 Valve 결과는 그대로** (판정 스냅샷 2,935 · 회귀 시험).

## 알릴 것 (오케스트레이터 세션 `session_01Muj82FygSCFAVRooofwhVK` 에 send_message)

- 화면에 쓸 **kind 키 목록** → 오케스트레이터가 1 세션에 대시보드 메뉴 연결을 요청
- 단계마다 푸시 후 "푸시 · 커밋 · 된 것 · 다음" 한 줄
- 첨부 원본(양식 · Line List)은 저장소에 올리지 않는다 — 시험에는 그 위에 만든 시험 PDF 만 쓰고, 발주처 · 프로젝트 이름은 넣지 않는다.
