# 계기 Datasheet 양식 카드 (빈 양식 '학습' 결과)

받은 빈 양식 14종을 **양식 카드**(칸 번호 ↔ 칸 이름 ↔ 구역 ↔ 값 칸 위치 ↔ 표준 이름)로 만들었습니다.
아직 화면·검토 규칙은 없습니다 — 다음 단계(값이 채워진 샘플로 값 읽기 시험)의 바탕입니다.

- 만드는 법: `python3 spike/valve_form_learn.py <빈 양식 폴더> app/valve/forms/` — PDF 글자층과 선만 씁니다 (OCR · LLM 없음).
  같은 입력이면 같은 카드가 나옵니다. 빈 양식 PDF 는 고객 자료라 저장소에 넣지 않습니다.
- 결과: `app/valve/forms/<form>.json` (양식마다 1개) · `index.json` (한 줄 요약) · `lists.json` (List 머리글).
- 카드에는 발주처·프로젝트 이름을 적지 않습니다 (제목란의 회사·현장 이름은 건너뜀).
- Tag 대조 규칙(나중에 쓸 것): 대문자로 바꾸고 빈칸 · `-` · `_` 를 뺍니다 (`FT-1001A` = `FT 1001 A`).
  'Quantity Tags / Tag quantity' 칸은 모든 카드에서 `tag_qty` 입니다.

## 1. 양식 한눈에

| form | 이름 | kind | 쪽 | 칸 수 | 구역들 (인쇄된 그대로) | 식별 근거 |
|---|---|---|---|---|---|---|
| 80 | On-Off Valve (SDV/BDV) | `onoff` | 2 (A4) | 1~61 | GENERAL · PIPE DATA · PROCESS DATA · VALVE BODY · ACTUATOR · SOLENOID VALVE · ACCESSORIES | Form No 80 · 제목 ON / OFF VALVE (꼬리표 없음) |
| 101 | Control Valve | `cv` | 3 (A4) | 1~100 + 2쪽 1~38 | TAG · VALVE GEN. · GENERAL DESIGN DATA · POSTNR. · BODY/BONNET · VALVE TRIM · ACTUATOR · PAINT · VAL ACC. · PNEUMATIC ACC. · ELECTRICAL ACC. / 2쪽: GEN. · PROCESS/SIZING CALCULATION DATA | Form No 101 · form 101_R9.02 |
| 203 | Analyzer | `analyzer` | 4 (Letter) | 1~40 | TAG · ANALYZER · ENVIRON · UTILITIES · OUTPUT | Form No 203 · form 203_R11 · 'DRAWING NO.' |
| 310 | Restriction Orifice | `ro` | 4 (Letter) | 1~41 | TAG · PROCESS DATA · GENERAL | Form No 310 · 제목 Restriction Orifice (꼬리표는 000_R1.01 뿐) |
| 313 | Flow Transmitter | `ft` | 2 (A4) | 1~48 | TAG · PROC. · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | Form No 313 · form 313_R1.02 · 제목 '… for Flow' |
| 505 | Magnetic Level Gauge | `mlg` | 4 (Letter) | 1~50 | TAG · PROC. · GEN. · CHAMBER · ACCESORY · MATERIAL · INDICATOR · MFR | Form No 505 · form 505_R2.00 |
| 506 | Level Transmitter | `lt` | 4 (Letter) | 1~48 | TAG · PROC. · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | Form No 506 · form 506_R1.03 · 제목 '… for Level' |
| 5063 | GWR (Guided Wave Radar) | `gwr` | 4 (Letter) | 1~50 | TAG · PROC. DATA · GENERAL · SENSOR · TRANSMITTER · MFR | **파일 이름** + 제목 'DATA SHEETS FOR RADAR LEVEL TRANSMITTER' + Probe 칸 |
| 601 | PT / PDT | `pt` | 2 (A4) | 1~48 | TAG · PROC. · GENERAL · ELEMENT · TRANSMITTER · OPTIONS · MFR | Form No 601 · form 601_R2.02 · 제목 '… for Press' |
| 605 | Pressure Gauge | `pg` | 4 (Letter) | 1~47 | TAG · PROC. DATA · GAUGE · OPTIONS · MFR | Form No 605 · 제목 Pressure Gauges · 구역 GAUGE |
| 606 | DP Gauge | `dpg` | 2 (Letter) | 1~47 | TAG · PROC. DATA · METER · OPTIONS · MFR | **파일 이름** · 구역 METER (꼬리표가 605_R2.00) |
| 701 | PSV | `psv` | 2 (A4) | 1~50 | GENERAL · BASIS · VALVE DESIGN · CONN. · VALVE MATERIAL / MAIN · VALVE MATERIAL / PILOT · PROCESS DATA · SIZE/SEL · ACCESS. · MFR | Form No 701 · form 701_R3.02 |
| 801 | Temperature Transmitter | `tt` | 1 (A4) | 1~30 | TAG · GENERAL · INPUT · OUTPUT · MFR | Form No 801 · form 801_R2.00 |
| 803 | Temperature Gauge | `tg` | 4 (Letter) | 1~45 | TAG · PROC. DATA · GEN. · THERMOMETER · WELL · MFR | Form No 803 · form 803_R2.02 |

모든 양식에서 **칸 번호가 1~N 빠짐없이** 읽혔습니다 (중복 0 · 빠진 번호 0). 칸 수는 인쇄된 마지막 번호와 같습니다.

카드의 칸마다: 번호 · 칸 이름(인쇄 그대로) · 구역 · 쪽 · 이름 위치 · **빈 값 칸 위치** · 하위 칸(Max/Nor/Min/Unit,
Size/Rating/Type, Class/Type/Certificate …) · 같은 줄의 두 번째 이름(예: 80 의 'Tag No. | Item No.') · 상위 칸
(들여 쓴 칸: 'Body Material:' → 'Wetted Part') · 표준 이름(`std_key`) · Process 칸 여부.
`required` 는 **제안(사용자 확인 필요)** 입니다: Tag · Service · P&ID · Line/Equipment · Pipe Class · Fluid · 운전/설계 P·T · 제조사 · 모델 + Process 칸.

표준 이름 예: `tag` · `tag_qty` · `pid_no` · `service` · `line_no` · `equipment_no` · `piping_class` (= Service Class) ·
`line_size` · `fluid` · `fluid_state` (Phase) · `op_pressure` · `design_pressure` · `op_temp` · `design_temp` ·
`density` · `flow` · `mol_weight` · `viscosity` · `manufacturer` · `model`. Valve 양식(80 · 101)은 지금 Valve 읽기의
이름(`app/valve/schema.py`)을 그대로 씁니다. 사전에 없는 칸은 칸 이름에서 만든 이름(`flushing_ring` 등)입니다.

## 2. 어려웠던 것 · 애매한 것

1. **세로 구역 글자** — 한 글자씩 세로로 찍혀 있어 띄어쓰기가 없습니다 ('VALVEMATERIAL'). 구역 선(가로 줄) 사이의
   글자를 위에서 아래로 이어 읽고, 아는 낱말로만 띄어 썼습니다 (`section`; 인쇄 그대로는 `section_printed`).
   701 은 두 줄 구역(바깥 VALVE MATERIAL · 안쪽 MAIN / PILOT, SIZE · /SEL)이라 'VALVE MATERIAL / MAIN' 처럼 적었습니다.
   101 의 'POSTNR.'(Positioner) · 505 의 'ACCESORY'(철자 그대로)는 인쇄된 대로 둡니다.
2. **이름이 없는 칸** (`label: ""`, 카드 `ambiguous` 에 이유 기록):
   - 비어 있는 줄: 80 #8·19·20·32·33 · 101 #11, 2쪽 #28·30·33·37·38 · 605/606 #45 · 5063 #50.
   - 머리글 줄(Max/Nor/Min/Unit 만): 313 · 506 · 601 #6, 203 #20 — 아래 칸들이 이 하위 칸을 물려받습니다(`subcols_from`).
   - 하위 칸 이름만 있는 줄: 701 #13 (Sensing / Vent — #12 Pilot 의 둘째 줄) · 605/606 #22 (Location / Shape — #21
     Connection 의 둘째 줄) · 203 #29 (Max/Min Pressure / Max/Min Temperature — Utilities 머리글).
3. **여러 값 칸 줄** — 하위 칸 이름이 작은 글씨로 값 칸 안에 찍혀 있습니다 (`subcols`). 'Design Pressure  /' 처럼
   '/' 만 찍힌 칸은 값 두 개(예: 최대/최소) 자리로 보고 `subcols` 에 넣지 않았습니다. 'Name Plate : Yes, No' 는
   `options: ["Yes","No"]`. 단위가 인쇄된 칸(101 2쪽 '%' · 'dBA')은 `unit_printed`.
4. **한 줄에 이름 두 개** — 101 은 선 없이 'Model No :  ……  Ser No. :' 로 찍혀 있어 넓은 틈에서 나눴습니다
   (`sublabels`, 값 칸은 이름 사이 빈 곳). 101 #1~4 의 오른쪽(Instrument Type · Valve Type · Valve Service ·
   Quantity Tags)은 오른쪽 번호 칸(53~)이 시작하기 전이라 왼쪽 줄에 붙였습니다.
5. **양식 식별** — 313 · 506 · 601 은 칸 구성이 거의 같아 Form No 와 제목('for Flow / Level / Press')으로 가립니다.
   605 와 606 은 칸이 같고 606 은 제목란이 아예 없으며 꼬리표도 605_R2.00 → 606 은 **파일 이름**과 구역 'METER' 로만 가립니다.
   5063 은 Form No 없음 · 다른 제목란 → 파일 이름 + Probe 칸. 310 꼬리표는 공통 000_R1.01 뿐, 80 은 꼬리표가 없습니다.
6. **INSTRUMENT_REVIEW_PLAN.md §2 와 다른 점** (PDF 기준으로 고침):
   - 101: '1~100 · 3쪽' → 1쪽 1~100(두 단) + **2쪽 Process/Sizing 표 1~38**(꼬리표 101+102_R6.04) + 3쪽 Notes. 구역도 더 잘게 나뉨.
   - 80: 구역 4개 → 7개 (PIPE DATA · PROCESS DATA · ACCESSORIES 추가). 'form …' 꼬리표 없음, Notes 는 2쪽 'NOTES :'.
   - 701: CONN. · MAIN/PILOT · SIZE/SEL · ACCESS. · MFR 구역이 따로 있음.
   - 505: GEN. 구역 있음, 'ACCESORY' 철자. 803: GEN.(#17~18) 구역 있음. 801: INPUT 과 OUTPUT 이 선으로 나뉜 두 구역.
   - 606: 구역 GAUGE 대신 METER, 제목란 없음 ('PG 카드 공유' 가 아니라 따로 카드).
   - 5063 인쇄 제목은 'RADAR LEVEL TRANSMITTER' (GWR 라는 말은 파일 이름에만).
7. Letter 양식(203 · 310 · 505 · 506 · 5063 · 605 · 606 · 803)은 A4 양식을 Letter 에 찍은 것이라 꼬리표가 다음 쪽으로
   넘어가 '꼬리표만 있는 쪽'이 생깁니다 (`page_roles`). 칸은 모두 1쪽에 있습니다.

## 3. List 양식 (`lists.json` — 머리글만)

- **Instrument Index** (A4 가로, 머리글 4줄): Rev. · Tag No./Loop No./Instrument Type/Service · P&ID No./Line No./
  Equipment No./Location · Fluid/Phase/Area · System In/Signal In/Location · System Out/Signal Out/Location ·
  Range Min/Max/Eng. Unit · Location Dwg./Process Hook-up/Pneumatic Hook-up/Installation Dwg. ·
  Scope/**Datasheet No.**/Req. No. · Manufacturer/Model No. · Remark1/2.
- **IO List** (A4 가로, 머리글 5줄): Rev. · Tag/Loop/Instrument Type/Service · P&ID/Line/Equipment/Location ·
  IO Typical/Redundant I/O (Y/N)/IS·Non-IS · System In… · System Out… · Loop Powered/Externally Powered/Power Supply ·
  Range Min/Max/Eng. Unit · Logic No. · JB Wiring/Interconnection/Loop Drawing No. · Remark1/2.
  두 List 모두 읽지 못한 머리글 글자는 없습니다. 칸 하나에 여러 항목이 위아래로 쌓여 있어 `lines` 로 따로 남겼습니다.
- **Process Data 샘플**: 표지(A4 세로) + Notes 쪽, 그 뒤 A3 가로 표 — 머리글 3줄 + 단위 1줄, Tag 한 줄씩 'Sr no.' 번호.
  표 제목 'Process Data for On-Off Valve / Control Valve / Pressure Relief Valve / Motor Operated Valve'. 지금 `app/valve/process.py` 가 읽는 꼴.

## 4. Process Line List (North · South 엑셀)

- 시트: 'COVER SHT' + 표 시트 1개. 머리글 **7~9행**(7행 이름 · 8행 세부 · 9행 단위), 자료는 10행부터, 아래에 'NOTES:' 블록.
  받은 파일은 North 3줄 · South 4줄만 채워져 있습니다 (나머지 빈 줄).
- 열: A Line Number · B Revision · C Service · D Serial No. · E Line Size (mm) · F Line Size (inch) · G **Pipe Class** ·
  H P&ID Number · I From · J To · K **Fluid Phase** · L Fluid Density (kg/m3) · M **Design Pressure (barg)** ·
  N **Design Temp. Max (°C)** · O Design Temp. Min (°C) · P Operating Pressure (barg) · Q Operating Temp. (°C) ·
  R/S Stress Analysis · T Test Medium · U Test Pressure · V/W Insulation Type/Thickness · X Electric Trace · Y PWHT ·
  Z Hardness · AA~AD NDE · AE Remarks.
- **검토에 쓸 열**: Datasheet 의 Line No. → A Line Number 로 찾아 → G Pipe Class (↔ `piping_class`) ·
  E/F Size (↔ `line_size`) · M Design P · N/O Design T (↔ `design_pressure` · `design_temp`; Datasheet 가 Line 보다
  낮으면 지적) · P/Q 운전 P·T (↔ `op_pressure` · `op_temp`) · K Fluid Phase (↔ `fluid_state`) · L Density (↔ `density`).
  'Fluid' 이름 열은 따로 없고 C Service 코드(예: AG)가 그 역할입니다.
- 주의: South 시트는 E/F 열 값이 머리글과 반대(E 에 inch, F 에 mm)로 들어 있습니다 — 읽을 때 단위로 가려야 합니다.
  Line Number 표기도 North 'AG1442-24"(1C3AS-A)E(…)' · South '12DHC-1001-2"-1C3AS2-A-N' 로 꼴이 달라, 대조는
  A 열 전체 문자열이 아니라 C·D(Service·Serial) 조합이나 정규화로 맞춰야 합니다.

## 5. 다음에 할 것

1. 값이 채워진 Datasheet 2~3장(Item 별)으로 '값 칸 위치 → 값' 읽기 시험 (카드의 `value_bbox` · `subcols` 확인).
2. `required` 제안 목록 확인 (사용자).
3. 실제 Instrument List · IO List(값 있는 것)로 'List 카드'(머리글 → 표준 이름) 만들기.
