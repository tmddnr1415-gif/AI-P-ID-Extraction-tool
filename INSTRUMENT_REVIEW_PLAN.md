# Instrument Datasheet 자동 검토 — 기획안 v2 (2026-11-12)

> 담당: **6. Datasheet 자동 검토 세션** (Valve 검토 valve39 를 넓힘 · 브랜치 `ccr-efbe7e75-n915ze`) · 작성: 오케스트레이터
> 사용자 결정 (2026-11-12): ① 지금 받은 자료로 구축 · 개발 ② **모든 Datasheet 에서 Process Data 의 기준은 PDS** ③ **IO List · Instrument List 도 PDF** — 그 기준으로 개발 ④ List 대조의 기준은 **Datasheet**
> 양식 원본은 저장소에 올리지 않는다 — 사용자가 6 세션에 직접 올림 (발주처 · 프로젝트 이름은 코드 · 시험 · 문서에 넣지 않음)

## 1. 만드는 것 — 한 줄

사용자가 **Item 별 Datasheet PDF**(수십~수백 장)와 **PDS · PMS · Process Line List · Instrument List(PDF) · IO List(PDF)** 를 넣으면,
양식을 알아보고 읽어 **Datasheet 를 기준으로** 검토 · 대조하고, 현황판 · Issue · 문서/Rev 를 관리한다 (지금 Valve 검토와 같은 화면 · 같은 흐름).

```
 입력 (모두 PDF · Line List 는 엑셀도)                     읽기                         검토 (기준 → 대상)                    결과
 ┌──────────────────────────────┐   ① 양식 식별 (Form No ·      ┌──────────────────────────────┐   현황판 (Item · Tag 별)
 │ Datasheet PDF  — Item 별 칸    │      꼬리표 · 제목 · 칸 구성)   │ Datasheet 자체: 빠진 칸 · 값 오류 │   Issue List (근거 쪽 · 칸)
 │  Valve(101·80·701) · FT · PT · │   ② 번호 칸 읽기 + 양식 카드     │ PDS → Datasheet (Process Data)  │   List 대조 표
 │  LT · GWR · TT · TG · PG · DPG │   ③ 표 읽기 (List · Line List)   │ PMS → Datasheet (Class·재질·Rating)│  Mark-up PDF · Excel
 │  · Mag LG · RO · Analyzer      │   ④ 표준 칸으로 맞춤             │ Line List → Datasheet (Line·Class)│   문서 · Rev 관리
 │ PDS · PMS                      │      (tag · pid · service · line │ ★ Datasheet → Instrument List     │   사람 결정 (Accept · Reject)
 │ Process Line List (엑셀/PDF)   │       · class · P·T · range ·   │ ★ Datasheet → IO List             │
 │ ★ Instrument List (PDF)        │       signal · system …)        │ ★ Instrument List ↔ IO List (보조) │
 │ ★ IO List (PDF)                │                                 └──────────────────────────────┘
 └──────────────────────────────┘
```

## 2. 기준 (누가 맞는 쪽인가)

| 무엇을 볼 때 | 기준 | 대상 | 결과 꼴 |
|---|---|---|---|
| Process Data (Operating/Design P·T · Fluid · Phase · Density · Flow · Viscosity …) | **PDS** | 모든 Datasheet | "PDS 값 → Datasheet 값" · PDS 에 Tag 없음 = '없음' |
| 배관 등급 · 재질 · Rating · Flange | **PMS** (Datasheet 의 Pipe Class 로 찾음) | Datasheet | Valve 의 PMS Compliance 와 같음 |
| Line · Pipe Class · Line Design P·T · Size | **Process Line List** (Line No. 로 찾음) | Datasheet | Line 의 Design 이 Datasheet 보다 높으면 지적 |
| Tag 유무 · Instrument Type · Service · P&ID · Line · Equipment · Range · Unit · Manufacturer · Model · Datasheet No. | **Datasheet** | **Instrument List** | Datasheet 에 있는데 List 에 없음 / 값 다름 / List 에만 있음 |
| Tag 유무 · Signal(AI/AO/DI/DO) · System(DCS/SIS/F&G/PLC) · Range · Unit · Service · Loop | **Datasheet** | **IO List** | 같음 (Datasheet 에 Signal · System 이 있는 Item 만 — 예: Transmitter Output · Valve 의 Positioner/Limit Switch/Solenoid) |
| Tag · Loop · System · Signal | Instrument List | IO List | 보조 대조 — Datasheet 에 없는 칸만 (예: Loop No. · IO 카드 위치) |

- 결론은 언제나 **"기준 값 → 대상 값 · 다름"** 으로 적고, 고칠 쪽은 사람이 정한다 (대상이 맞아 보여도 "기준 문서 확인 필요").
- 값은 문서에서 읽은 값만 쓴다 — 없으면 만들지 않고 '없음' 으로 지적한다. 검출 · 대조에 LLM 을 쓰지 않는다.

## 3. 입력 양식

### 3-1. Datasheet (사용자가 준 빈 양식 — 모두 같은 계열)

위 **제목란**(Form No · DOCUMENT NO. · SHEET · REV) → **번호 칸 1~N**(왼쪽 번호 · 세로 구역 글자 · 칸 이름 · 값) → **Common / Individual Notes** → 맨 아래 `form NNN_Rx.xx`.

| Item | Form · 꼬리표 | 칸 · 쪽 · 종이 | 구역 | 지금 |
|---|---|---|---|---|
| Control Valve | 101 · R9.02 | 1~100 · 3 · A4 | TAG · DESIGN · BODY/BONNET · TRIM · ACTUATOR · POSITIONER · ACCESSORIES | ✅ |
| On-Off Valve (SDV · BDV) | 80 | 1~61 · 2 · A4 | GENERAL · BODY · ACTUATOR · SOLENOID | ✅ |
| PSV | 701 · R3.02 | 1~50 · 2 · A4 | GENERAL · BASIS · DESIGN · MATERIAL · PROCESS DATA · SIZE · ACCESSORIES | ✅ |
| FT | 313 · R1.02 | 1~48 · 2 · A4 | TAG · PROC · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | 새로 |
| PT / PDT | 601 · R2.02 | 1~48 · 2 · A4 | 〃 | 새로 |
| LT | 506 · R1.03 | 1~48 · 4 · Letter | 〃 | 새로 |
| GWR | 표시 없음 (제목란 다름) | 1~50 · 4 · Letter | TAG · PRO DATA · GENERAL · SENSOR · TRANSMITTER · MFR | 새로 — 칸 구성 · 파일 이름으로 식별 |
| TT | 801 · R2.00 | 1~30 · 1 · A4 | TAG · GENERAL · INPUT/OUTPUT · MFR | 새로 |
| TG | 803 · R2.02 | 1~45 · 4 · Letter | TAG · PRO DATA · THERMOMETER · WELL · MFR | 새로 |
| PG | 605 · R2.00 | 1~47 · 4 · Letter | TAG · PRO DATA · GAUGE · OPTIONS · MFR | 새로 |
| DPG | 606 (꼬리표 605_R2.00) | 1~47 · 2 · Letter | PG 와 같음 | 새로 — PG 카드 공유 |
| Mag. Level Gauge | 505 · R2.00 | 1~50 · 4 · Letter | TAG · PROC · CHAMBER · ACCESSORY · MATERIAL · INDICATOR · MFR | 새로 |
| RO | 310 (꼬리표 000_R1.01) | 1~41 · 4 · Letter | TAG · PROCESS DATA · GENERAL | 새로 |
| Analyzer | 203 · R11 | 1~40 · 4 · Letter | TAG · ANALYZER · ENVIRON · UTILITIES · OUTPUT | 새로 |

### 3-2. List (PDF)

| 문서 | 형식 | 읽을 열 (양식 머리 그대로) |
|---|---|---|
| **Instrument List** (Instrument Index) | PDF · 가로 A4 · 여러 쪽 표 · 제목 줄(Document No · Rev · Rev Date · Unit · Area · Plant · Domain · Page n of N) | Rev · **Tag No.** · Loop No. · **Instrument Type** · **Service** · **P&ID No.** · **Line No.** · **Equipment No.** · Location · System In · Signal In · System Out · Signal Out · Building · **Range Min / Max / Eng. Unit** · Location Dwg · Process/Pneumatic Hook-up · Installation Dwg · Scope · **Datasheet No.** · Req. No. · **Manufacturer** · **Model No.** · Remark 1 · 2 · Fluid · Phase · Area |
| **IO List** | PDF 표 (양식은 사용자가 6 세션에 줄 것) | 예상: Tag · Loop · Service · **IO Type(AI/AO/DI/DO)** · **System(DCS/SIS/F&G/PLC)** · Signal(4-20mA/HART/24VDC) · Range · Unit · Cabinet/Card/Channel · P&ID · Remark — **실제 PDF 의 머리를 보고 카드로 맞춤** |
| Process Line List | 엑셀 (PDF 도 같은 표) · 머리 7~9 줄 | Line Number · Revision · Service · Serial · Size(mm/inch) · **Pipe Class** · P&ID · From · To · Fluid Phase · Density · **Design P · T(max/min)** · **Operating P · T** · Stress · Test · Insulation · Tracing · PWHT … |

- List 는 **표 읽기**로 읽는다: 쪽마다 머리 줄을 찾아(여러 줄 머리 합치기) 열 이름 → 표준 이름으로 맞추는 **List 카드**. 열 순서가 바뀌어도 이름으로 찾는다 (Valve 의 PSR · TBE 읽기와 같은 방식).
- 쪽이 넘어가도 머리 줄이 반복되면 이어 붙이고, 빈 칸은 위 줄 값을 이어받지 않는다 (지어내지 않음).

## 4. 대조 규칙 — Datasheet 기준

### 4-1. Tag 맞추기
- 표준 Tag: 공백 · 하이픈 · 밑줄을 뺀 대문자 (`FT-1001A` = `FT 1001 A`). **앞 0 차이 · 접미 글자 차이는 '비슷한 Tag' 로 제안만** (자동으로 같다고 보지 않음 — valve39 의 PDS 대조와 같은 규칙).
- 한 Datasheet 에 여러 Tag (Tag Quantity · 'FT-1001A/B') → Tag 마다 나눠 대조.

### 4-2. 결과 종류
| 종류 | 뜻 |
|---|---|
| **List 누락** | Datasheet 에 있는 Tag 가 Instrument List / IO List 에 없음 |
| **List 에만 있음** | List 에 있는데 그 Item 의 Datasheet 가 없음 (Datasheet 를 아직 안 올렸을 수도 — '확인' 등급) |
| **값 다름** | 같은 Tag 의 칸 값이 다름 — 칸마다 (예: Range · Unit · Service · P&ID · Line · Manufacturer) |
| **IO 대상 아님 확인** | Gauge 처럼 신호가 없는 Item 이 IO List 에 있음 (또는 Transmitter 가 IO List 에 없음) |

### 4-3. 값 비교 방법
- 글자: 공백 · 대소문자 · 구두점 무시, 약어 표(예: `TRANSMITTER`/`XMTR`) 는 카드에 — 그래도 다르면 '다름' 으로 두고 원문을 나란히 보여 줌.
- 숫자 · 단위: 단위를 맞춰 비교 (barg ↔ kPa(g) · °C · mm ↔ inch · m3/h). 단위가 없거나 모르면 비교하지 않고 '단위 확인'.
- Range: Min/Max 둘 다. Datasheet 의 Calibration/Scale Range 를 기준으로.
- Signal · System: Datasheet 의 Output/Communication(4-20mA HART · Foundation Fieldbus · Discrete) → IO Type 기대값(AI · AO · DI · DO)을 카드 표로 정해 비교.

## 5. 화면 (지금 /valve 화면을 넓힘)

- 대시보드 › 실행 프로젝트 › CO2 PJT › **Datasheet** 아래: Ball · Globe · Butterfly · PSV(지금) + **FT · PT/PDT · LT · GWR · TT · TG · PG · DPG · Mag. Level Gauge · RO · Analyzer** — 같은 P&ID 서버 `/valve/?kind=…` (kind 키는 6 세션이 정해 오케스트레이터에 알림 → 1 세션이 메뉴 연결).
- **Document Management** 칸: Datasheet PDF · PDS · PMS · Process Line List · **Instrument List (PDF)** · **IO List (PDF)**. List 는 프로젝트 공통(모든 Item 이 함께 씀).
- 첫 화면: Item 별 Tag 수 · 검토 상태 · Issue 수 + **List 대조 요약** (List 누락 N · List 에만 있음 N · 값 다름 N).
- 새 보기 **"List 대조"**: Tag × [Datasheet · Instrument List · IO List] 표 — 다른 칸만 빨강, 누르면 각 문서의 그 쪽 · 그 줄. 필터: Item · 결과 종류 · 칸. Excel 내보내기 (코멘트 열 포함).
- Issue 는 Valve 와 같은 꼴: 근거(문서 · 쪽 · 칸) · 사람 결정(Accept/Reject/Comment) · Rev 비교 · Mark-up PDF.

## 6. 단계 (단계 끝마다 푸시 → 오케스트레이터가 회사 업데이트에 실음)

| 단계 | 내용 | 시험 |
|---|---|---|
| **1. 양식 읽기** | 번호 칸 읽기 일반화 + Datasheet 양식 카드 11종(새) · 양식 식별 · 여러 Tag 나누기 · Rev | 빈 양식으로 칸 이름 위치 · 빈 양식에 **시험 값을 써 넣은 시험 PDF** 로 값 읽기 |
| **2. Datasheet 검토** | Item kind 추가 · 빠진 칸 · **PDS 대조(모든 Item)** · PMS · Process Line List 대조 · 현황판 | 시험 PDF + 시험 PDS · Line List 엑셀 |
| **3. List 읽기** | Instrument List PDF(Index 양식) · IO List PDF 표 읽기 · List 카드 · Document Management 칸 | 양식 위에 시험 줄을 써 넣은 시험 PDF |
| **4. List 대조** | Datasheet 기준 → Instrument List · IO List · 보조 대조 · "List 대조" 보기 · Excel | 일부러 누락 · 다름 · 단위 차이 · 비슷한 Tag 를 넣은 시험 자료 |
| **5. Item 별 규칙** | Range ⊇ Operating · Probe 길이 · Thermowell · Utilities … (근거 문서가 있는 것만 · 사람 확인 표시) | |

- 매 단계: **지금 Valve 결과(판정 스냅샷 2,935)는 그대로** · 회귀 시험 · 외부로 나가는 요청 0.
- 실제 값이 든 Datasheet · List 로 맞추는 일은 회사 PC 의 회사 Claude 로 하고 **엔진 개선값(카드 · 코드)만** 가져올 수 있다 (`company-pc-update/회사_Claude_학습_프롬프트.md` A 흐름).

## 7. 사용자가 줄 것 · 정할 것

1. **IO List PDF 양식** (빈 양식 또는 몇 줄 든 것) — 6 세션에 직접.
2. Instrument List 가 Index 양식과 다르면 그 PDF 한 장.
3. List 대조의 '같음' 기준 — 위 4-1 · 4-3 이 맞는지 (특히 비슷한 Tag · 약어 · 단위).
4. 우선순위 — Item 을 한꺼번에, 또는 많이 쓰는 것부터(PT · FT · LT · TT · PSV → Gauge · RO · Analyzer).
