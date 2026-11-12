# Instrument Datasheet 자동 검토 — 기획안 (2026-11-12)

> 상태: **기획안 (아직 만들지 않음)** · 작성: 오케스트레이터 · 근거: 사용자가 준 양식 15종 · Instrument Index 양식 · Process Line List 2개 + 지금 있는 Valve Datasheet 자동 검토(세션 6, valve39)

## 1. 사용자 의도

| # | 하고 싶은 것 |
|---|---|
| 1 | **Valve Datasheet**(지금 있음): PDF 를 넣으면 현황판 + PDS · PMS 기준 Spec 검토 |
| 2 | **다른 Instrument 도 같은 방식**: 양식을 익혀 두고, 사용자가 값이 채워진 Datasheet PDF 수십~수백 장을 **Item 별로** 넣으면 식별 · 읽기 → PDS · PMS 기준 검토 결과 · 현황판 · 문서(Rev) 관리 |
| 3 | **Instrument List · IO List 대조**: 사용자가 넣으면 Tag 별로 Datasheet 와 맞지 않거나 빠진 것을 코멘트. **기준은 Datasheet** — Datasheet 에 있는데 List 에 없음 / 값이 다름 / List 에만 있음 |

## 2. 받은 양식 조사 결과 (빈 양식 — 값은 없음)

모두 같은 계열의 양식입니다: 위 **제목란**(Form No · 문서번호 · Rev · Sheet) → **번호 붙은 칸 1~N**(왼쪽 번호 · 세로 구역 이름 · 칸 이름 · 값) → 아래 **Common / Individual Notes** → 맨 아래 `form NNN_Rx.xx`.
→ 한 가지 읽는 틀(**번호 칸 읽기**)에 **양식 카드**(양식마다 칸 번호 ↔ 칸 이름 ↔ 표준 이름)를 얹으면 됩니다. Valve 의 Form 101 · 701 · 80 은 이미 이 방식으로 읽고 있습니다.

| Item | Form | 칸 | 구역 (세로 글자) | 종이 | 지금 |
|---|---|---|---|---|---|
| Control Valve (PCV) | 101 (R9.02) | 1~100 · 3쪽 | TAG · GENERAL DESIGN · BODY/BONNET · TRIM · ACTUATOR · POSITIONER · ACCESSORIES | A4 | ✅ valve37 |
| On-Off Valve (SDV · BDV) | 80 | 1~61 · 2쪽 | GENERAL · BODY · ACTUATOR · SOLENOID | A4 | ✅ (Ball · Code 80) |
| PSV | 701 (R3.02) | 1~50 · 2쪽 | GENERAL · BASIS · VALVE DESIGN · MATERIAL · PROCESS DATA · SIZE · ACCESSORIES | A4 | ✅ valve37 |
| Analyzer | 203 (R11) | 1~40 · 4쪽 | TAG · ANALYZER · ENVIRON · UTILITIES · OUTPUT | Letter | 새로 |
| Restriction Orifice (RO) | 310 (꼬리표 000_R1.01) | 1~41 · 4쪽 | TAG · PROCESS DATA · GENERAL | Letter | 새로 |
| Flow Transmitter (FT) | 313 (R1.02) | 1~48 · 2쪽 | TAG · PROC · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | A4 | 새로 |
| Mag. Level Gauge | 505 (R2.00) | 1~50 · 4쪽 | TAG · PROC · CHAMBER · ACCESSORY · MATERIAL · INDICATOR · MFR | Letter | 새로 |
| Level Transmitter (LT) | 506 (R1.03) | 1~48 · 4쪽 | TAG · PROC · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | Letter | 새로 |
| GWR (Guided Wave Radar) | 5063 (양식 번호 표시 없음 · 다른 제목란) | 1~50 · 4쪽 | TAG · PRO DATA · GENERAL · SENSOR · TRANSMITTER · MFR | Letter | 새로 — 파일 이름으로 식별 |
| PT · PDT | 601 (R2.02) | 1~48 · 2쪽 | TAG · PRO · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | A4 | 새로 |
| Pressure Gauge (PG) | 605 (R2.00) | 1~47 · 4쪽 | TAG · PRO DATA · GAUGE · OPTIONS · MFR | Letter | 새로 |
| DP Gauge (DPG) | 606 (파일 안 꼬리표는 605_R2.00) | 1~47 · 2쪽 | PG 와 같음 | Letter | 새로 — PG 카드 공유 |
| Temperature Transmitter (TT) | 801 (R2.00) | 1~30 · 1쪽 | TAG · GENERAL · INPUT/OUTPUT · MFR | A4 | 새로 |
| Temperature Gauge (TG) | 803 (R2.02) | 1~45 · 4쪽 | TAG · PRO DATA · THERMOMETER · WELL · MFR | Letter | 새로 |
| **Instrument Index** (양식) | — | 열: Tag · Loop · Instrument Type · Service · P&ID · Line · Equipment · System/Signal In·Out · Range Min/Max/Unit · Hook-up · **Datasheet No.** · Manufacturer · Model · Fluid · Phase · Area | | 가로 A4 | 새로 |
| **Process Line List** (엑셀 2개 · North / South) | — | Line No. · Size · **Pipe Class** · P&ID · From/To · Fluid Phase · Density · **Design / Operating P·T** · Insulation · Tracing … | | | 새로 (Valve 의 Line 대조 확장) |

- 공통 칸 (거의 모든 양식): Tag No. · P&ID No. · Service · Line No./Equipment No. · Service Class(Pipe Class) · Operating/Design P·T (Max/Nor/Min/Unit) · Hazardous Area / Enclosure · Process Connection(Size · Rating · Type) · Wetted/Body Material · Manufacturer · Model No. · Notes.
- **아직 받지 못한 것: IO List 양식.** Instrument List 는 위 Instrument Index 양식을 기준으로 잡되, 실제 값이 채워진 List(엑셀이 있으면 엑셀)가 필요합니다.
- 받은 PDF 는 **빈 양식**이라, 값을 읽는 위치 · 단위 · 여러 값 칸(Max/Nor/Min) 처리 · 체크박스(Yes/No) 는 **값이 채워진 샘플 몇 장**으로 맞춰야 합니다.

## 3. 만들 것 — 전체 그림

```
 [Datasheet PDF 수십~수백 장 · Item 칸별]      [기준 문서]                       [List]
   Valve · FT · PT · LT · TT · PSV ·           PDS(Process Data) · PMS(Piping    Instrument List (Index)
   Analyzer · RO · Gauge …                      Material Spec) · Process Line List  IO List
            │                                          │                             │
   ① 양식 식별 (Form No · 꼬리표 · 제목 · 파일 이름)    │                             │
   ② 번호 칸 읽기 + 양식 카드 → 표준 칸 (tag, pid,      │                             │
      service, line, class, op/des P·T, conn, mat …)  │                             │
   ③ Datasheet 나누기 (여러 Tag 가 든 PDF) · Rev       │                             │
            └──────────────┬───────────────────────────┘                             │
                 ④ 검토 규칙 (Item 별 + 공통)  ◀───────────────────────────────────────┘
                   · 빠진 칸 · 값 오류 · PDS 대조 · PMS(Class · 재질 · Rating) · Line List 대조
                   · ★ List 대조: Datasheet 기준 — List 누락 · 값 불일치 · List 에만 있음
                 ⑤ 현황판 · Issue List · Mark-up PDF · Excel · 문서/Rev 관리 (Valve 와 같은 화면)
```

- **'학습' = 양식 카드**: 사람 손으로 만든 이름 없는 양식 카드(칸 번호 ↔ 표준 이름 · 구역 · 값 칸 개수)입니다. LLM 으로 검출하지 않습니다 (P&ID 엔진과 같은 원칙). 새 양식은 카드만 더하면 읽힙니다 — 회사 학습 설계(`LEARNING_DESIGN.md`)의 `config/form_library/` 와 같은 자리.
- **기준은 Datasheet**: 대조 결과는 항상 "Datasheet 값 → List 값" 방향으로 적습니다. List 가 맞는 것 같아도 결론은 "Datasheet 확인 필요" 로 두고 사람이 정합니다.

## 4. 검토 규칙 (처음 판)

| 묶음 | 예 |
|---|---|
| 공통 — 빠진 칸 | Item 별 꼭 있어야 할 칸(카드에 표시)이 비었거나 TBA/TBC |
| 공통 — PDS 대조 | Operating/Design P·T · Fluid · Phase · Density · Flow 를 PDS 의 같은 Tag 와 대조 (Valve 의 Process Data Verification 확장) |
| 공통 — Line List 대조 | Datasheet 의 Line No. → Line List 의 Pipe Class · Design P·T · Size 와 대조 (Design P·T 가 Line 보다 낮으면 지적) |
| 공통 — PMS | Pipe Class → Rating · Flange Face · 접액 재질 · 가스켓 · 볼트 (Valve 의 PMS Compliance 확장) |
| Item 별 | FT/PT/LT: Range ⊇ Operating, Calibration Range 단위 · Output(4-20mA/HART) · Hazardous Area / LT·GWR: Probe 길이 ↔ Vessel 노즐 거리 · 밀도 / TT·TG: Thermowell 재질 · 삽입 길이 / PSV: Set P ≤ Design P (이미 있음) / RO: 차압 · 구멍 수 / Analyzer: Utilities 칸 |
| ★ Instrument List · IO List | Tag 있음/없음 (양쪽) · Instrument Type · Service · P&ID · Line · Range Min/Max/Unit · Signal (AI/AO/DI/DO) · System(DCS/SIS/F&G) · Datasheet No. · Manufacturer/Model 이 Datasheet 와 같은지 |

결과는 Valve 와 같은 꼴: Tag 별 Issue (Data Error · Missing · PDS · PMS · List) · 근거(어느 문서 몇 쪽 · 어느 칸) · 사람 결정(Accept/Reject/Comment) · Rev 비교 · Excel/PDF 출력.

## 5. 화면 (Valve 화면을 그대로 넓힘)

- 대시보드 › 실행 프로젝트 › CO2 PJT › **Datasheet** 아래에 Item 메뉴 추가: Ball · Globe · Butterfly · PSV(지금) + **FT · PT/PDT · LT · GWR · TT · TG · PG · DPG · Mag. Level Gauge · RO · Analyzer**. 같은 `/valve/?kind=…` 화면(P&ID 서버)에 Item 이름만 다르게 — Valve 의 kind 방식 그대로.
- Document Management 에 칸 추가: **Instrument List** · **IO List** · **Process Line List** (엑셀 · PDF).
- 첫 화면(Dashboard): Item 별 Tag 수 · 검토 상태 · Issue 수 + **List 대조 요약** (Datasheet 에 있는데 List 에 없음 N · List 에만 있음 N · 값 다름 N).
- 새 보기 **"List 대조"**: Tag × (Datasheet · Instrument List · IO List) 표 — 다른 칸만 빨강, 누르면 근거 쪽.

## 6. 단계 (각 단계 끝에 회사 PC 업데이트 1번)

| 단계 | 내용 | 필요한 것 | 담당 |
|---|---|---|---|
| **0. 샘플** | Item 별 **값이 채워진 Datasheet 2~3장** + 실제 Instrument List · **IO List** 각 1개 (회사 자료면 회사 PC 의 회사 Claude 로 — 아래 7장) | 사용자 | 사용자 |
| **1. 번호 칸 읽기 일반화 + 양식 카드 13종** | 양식 식별 · 칸 읽기 · 표준 칸 · 여러 Tag PDF 나누기 · Rev. 빈 양식으로 '칸 이름 위치' 시험, 샘플로 '값' 시험 | 0 | 6 (Valve) |
| **2. Item 메뉴 · 공통 규칙** | 빠진 칸 · PDS · Line List · PMS 대조를 모든 Item 에 · 현황판 Item 별 | 1 | 6 · 1 (대시보드 메뉴) |
| **3. Instrument List · IO List 대조** | List 읽기(엑셀 · PDF Index) · Datasheet 기준 대조 · "List 대조" 보기 · Excel | 0 의 List | 6 |
| **4. Item 별 규칙** | Range ⊇ Operating · Probe 길이 · Thermowell … (전문가 확인 받은 것만) | 2 | 6 · 사람 확인 |
| 5. 3D 연결 (선택) | 세션 7 Anatomy 에 Item 모형이 있는 것만 Valve 처럼 Data 칸 ↔ 부위 | 2 | 7 |

- 판정 값은 문서에서 읽은 값으로만 잽니다 (코드에 박지 않음). 문서에 없는 값은 만들지 않고 비워 둔 뒤 "없음" 으로 지적합니다.
- 지금 Valve 결과(판정 스냅샷 2,935)는 그대로여야 합니다 — 매 단계 회귀 확인.

## 7. 회사 자료 · 보안

- 받은 15종은 **빈 양식**이라 이 저장소에서 양식 카드를 만들 수 있습니다 (자료 내용이 아님). 원본 PDF 는 저장소에 올리지 않았습니다.
- 값이 채워진 Datasheet · List 가 **회사 자료**라 밖으로 낼 수 없으면: 회사 PC 의 회사 Claude Code 로 단계 1 의 카드 · 읽기를 맞추고, **엔진 개선값(카드 · 코드)만** 가져옵니다 (`company-pc-update/회사_Claude_학습_프롬프트.md` A 흐름 — 그대로 쓸 수 있음).
- Process Line List 엑셀에는 발주처 · 프로젝트 이름이 들어 있습니다 → 시험용으로 쓰면 저장소에 올리지 않고, 카드에는 열 이름만 남깁니다.

## 8. 사용자가 정할 것

1. **IO List 양식** — 엑셀인지 PDF 인지, 열 구성 (한 장 보내 주세요).
2. **값이 채워진 샘플** — 이 세션으로 보낼 수 있는지, 아니면 회사 Claude 로 맞출지.
3. **우선순위** — Item 13종을 한꺼번에 할지, 많이 쓰는 것부터(예: PT · FT · LT · TT · PSV → Gauge · RO · Analyzer) 할지.
4. **List 대조의 '같음' 기준** — Tag 표기(공백 · 하이픈 · 앞 0), Range 단위 변환, Service 글자 차이를 어디까지 같다고 볼지.
5. 담당 — 6 세션(Valve) 이 모두 맡을지, Instrument 용 새 세션을 열지.
