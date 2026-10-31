# EPC Instrument Engineering Review Tool — Module 01 Valve Datasheet Review · 설계

> 대시보드 메뉴: **실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve**
> 화면: P&ID 서버(8000)의 `/valve/` · 코드: `app/valve/` (엔진) · `app/static/valve/` (화면) · 시험: `tests/test_valve.py`
> 작업 브랜치: `ccr-efbe7e75-n915ze` (세션 "VALVE Datasheet 검토"). 인수인계: `docs/handoff/valve.md`.

## 1. 무엇을 만들었나 (Phase 1 완료 + Phase 2 기본)

| 요구 (사양서 §) | 상태 | 어디 |
|---|---|---|
| Datasheet 업로드 · 일괄 처리 · 진행률 · 실패 재처리 (§3.1, §15) | ✅ | Document Management · `api.upload` `_process` `retry` |
| 문서 자동 식별: Doc No. · Tag · Rev · Sheet · Date · Form (§3.2) | ✅ | `extract._header` `group_datasheets` |
| 병합 PDF 에서 Tag 별 분리 (§3.2) | ✅ | 456쪽 1파일 → 164 데이터시트 |
| 칸 추출 A~F (General · Process · Mechanical · Special · Accessories · Notes) (§3.3) | ✅ | `extract.read_page` · `read_page_102` · `read_process_table` · `schema.LABELS` |
| 원본 쪽 · 위치 표시 · 신뢰도 · 실패 항목 · 사용자 수정 (§3.4) | ✅ | 칸마다 `page` + `bbox` · 상태 `ok / placeholder / blank(Not Found) / review(Review Required)` · 수정은 읽은 값 옆에 |
| Valve List 생성 — 기준 TBE 양식 유지 (§4) | ✅ | `tbe.build` · Reports & Export |
| Revision 연결 · 칸별 비교 · Added/Deleted/Modified (§5.1–5.2) | ✅ | `api.compare` · Revision Comparison 화면 |
| PDF Mark-up (주석 방식, 원본 보존 · **인쇄됨**) (§5.3, §9) | ✅ | `exports.markup_pdf` — 지적 사항마다 색 상자 + 번호 · 데이터시트마다 Issue Summary 쪽 · 표지 · 책갈피 (§9) |
| **오류 · 누락 지적 + 설계사 전달 Issue List Excel** (2026-10-31 요청) | ✅ | `issues.compute` · `exports.issues_xlsx` (§9) |
| **분석 끝나면 Excel 자동 출력 · Excel 칸 ↔ PDF 연동** (2026-10-31 요청) | ✅ | `api._auto_export` · Valve List / Issue List 화면의 PDF 미리보기 · Excel 칸 링크 (§9) |
| Revision Comparison Report (§5.5) | ✅ 화면 | 엑셀 보고서는 다음 회차 |
| Process Data Verification (§6) | ⏳ Phase 3 | 문서 보관 · 화면 틀 · 제외 항목 분리. 판정 엔진 없음 → 'Not Evaluated' |
| PMS Compliance (§7) | ✅ Ball Valve 범위 | `pms.read_pms` · `pms.check` · `material.compare` — Class(지역 QN/QS) · Rating · NACE · Trim · Stem · Body · Seat · Fire test · Bore. Gasket · Bolting 은 아직 |
| Dashboard · Tag 별 검토 · 검토 상태 (§8) | ✅ | Dashboard · Datasheet Review (탭 8개) · 상태 6가지 |
| Audit Trail (§10) | ✅ | `audit` 표 · History 탭 · CSV |

**MOCK 표시 원칙** — Process Data 화면은 실제 Datasheet 값 · 쪽 · 위치만 보여 주고 결과 칸은 `Not Evaluated` 다.
화면 생김새 확인용 예시 판정은 사용자가 **MOCK 예시 판정 보기** 를 눌렀을 때만, 보라색 `MOCK` 딱지와 함께 나온다
(사양서 rule 11 "AI 가 근거 없이 판정하지 않는다"). Revision 이 하나뿐인 프로젝트의 Revision Comparison 도 같은 방식.

## 2. 참조 문서 분석 (2026-10-31 받은 파일)

받은 파일은 EGG(ALZip) 분할 압축이었다. 표준 라이브러리만 쓰는 `spike/valve_unegg.py` (무압축 · deflate 만)로 풀었고
CRC 가 모두 맞았다. **고객 자료이므로 저장소에 넣지 않는다.**

### 2.1 Valve Datasheet — `Datasheet.pdf` (MR CO2S-SSG-IN-REQ-00009 Annexure 6, 456쪽)

- 글자층이 있는 PDF (스캔 아님). 18개 DTS 문서가 이어 붙어 있음. 문서마다 표지 · 목차 · Holds · **INDEX(Tag · Rev · Typical · 쪽)** · **GENERAL NOTES** · 개별 데이터시트.
- 개별 데이터시트 양식 두 가지:
  1. **Form 80 "ON / OFF VALVE"** — 140개 (ESDV 78 · BDV 32 · XV 26 · SDV 4). Sheet 1 = 1~51행(GENERAL · PIPE DATA · PROCESS DATA · VALVE BODY · ACTUATOR · SOLENOID VALVE), Sheet 2 = 52~61행(ACCESSORIES) + **NOTES**.
     행 번호는 같아도 라벨이 문서마다 다르다 (8행 `Typical Detail` / `Typical` / `SIL Rating`, 33행 `SIL Requirement` / `Fire Safe Requirement`) → **라벨로 읽는다.**
  2. **Form 102 "Motor Operated Valve"** — 24개 (MOV). 3장: Sheet 1 = 1~52 · 53~100행 두 열, `라벨 : 값`(값은 굵은 글씨) · Sheet 2 = 공정 조건표(Unit · Max · Nor · Min) · Sheet 3 = 번호 매긴 Notes.
- 값 대신 참조가 많다: `General note - 8`, `Note-1`, `VTA`(Vendor to Advise), `HOLD`, `NA`. 참조는 그 Note 본문을 찾아 붙여 보여 주고(`ref`), VTA 류는 `placeholder` 로 표시한다.
- On/Off 양식의 PROCESS DATA 칸은 이번 판에서 대부분 비어 있다 (공정값은 별도 Process Data 문서 03-02-PR-DTS-00002 참조 — Note 7).

### 2.2 Valve List — `CO2S-SSG-IN-TBE-00009.xls` (Technical Bid Evaluation)

| 시트 | 내용 | Tag 수 |
|---|---|---|
| TBE Tabulation | 입찰자 응답 표 (일반 요구사항) | — |
| TBE Appendix-ESDV & SDV | ESDV · SDV · XV — Pneumatic | 81 |
| TBE Appendix-ESDV | ESDV — Electro Hydraulic | 1 |
| TBE Appendix-BDV | BDV — Pneumatic (Volume Tank 열 추가) | 32 |
| TBE Appendix-XV | XV — Pneumatic | 26 |
| TBE Appendix-MOV | MOV (Body Cover · Mechanical Key Interlock 열) | 24 |

- 머리글 3줄(병합) → 열 경로 예: `Accessories › Solenoid Valve › Body Material`. 데이터는 Tag 마다 **Requirement 1줄 + 입찰자(AMPO · OMS · NEWAY) 줄** 블록.
- `.xls`(BIFF) 는 openpyxl 이 못 연다 → 회사 PC 에서는 **Excel 자체로 .xlsx 변환**(PowerShell COM, `tbe.xls_to_xlsx`), 안 되면 화면이 "Excel 에서 .xlsx 로 저장해 넣으세요" 라고 말한다.
  개발 PC 시험용 변환기: `spike/valve_xls2xlsx.py` (xlrd 필요 · 배포 안 함).

### 2.3 Process Data — `Process_Data_.pdf` (Annexure 7, 61쪽, A3 가로)

- 영역별 "Process Data for On-Off Valve / Control Valve / PRV" 표. 열: Tag Number · Location · P&ID · Line No · Line Size · Valve Size · Pipe Class · Service Fluid · Phase · Flow rate · Max ΔP · Operating/Design Temp · Operating/Design Pressure(bar(g)) · MW · Density · Viscosity · ΔP open/close · Operating Time · Safety Position · Tightness …
- Tag 표기가 데이터시트와 다르다 (`02SDV-952`, `98BDV980002`, `98BDV-003`) → 연결 키는 **영숫자만 남긴 Tag** (`schema.norm_tag`).
- 표 머리 위치가 일정해 Phase 3 에서 열 위치로 결정적으로 읽을 수 있다. Valve Size · Pipe Class 열이 있지만 **Process 검증에서 비교하지 않는다** (§6.3 · `schema.NOT_PROCESS`).

### 2.4 PMS — `98-98-PI-SPC-00001_0001_0.pdf` (374쪽)

- 본문(약어 · 기준 · Class 번호 체계) + **Appendix C: Class 별 시트 37종** (1A1A · 1C0K8 · 1C3AS1 · XC0K8 …, Class 마다 5~12쪽).
- Class 시트 1쪽: Flange Facing · C.A. · PWHT · NACE · Flange Class · Material · **Valve Trim (예 TRIM 12 (316 SS/HF))** · P-T 표 · Service · Schedule 표 · General / Item Notes.
- 이어지는 쪽: 품목 표 `Code · Size Range · Description · Notes · Rev` — Pipe · Fittings · Flanges · Gaskets · Bolting · Gate / Globe / Check / **Ball Valve**.
  Ball Valve 설명 예: `BALL VALVE, 316/316L SS A351-CF8M/CF3M, CL150, RF, B16.47-B, … TRUNNION, API 6D, … 316 SS BALL/STEM, RTFE ST, FIRE TESTED TO API 607, NACE MR0175/ISO 15156`.
- Phase 4 계획: Class 시트를 (Class · 품목 · 크기 범위 · 설명 토큰) 으로 구조화 → Datasheet `Piping class`(또는 Line No. 의 괄호 안 Class) 로 연결 → Body · Trim · Seat · Gasket · Bolting 을 **ASTM 규격 · 등급 토큰** 단위로 비교. 동등 재질은 판정하지 않고 Review Required.

## 3. 추출 방식 (`app/valve/extract.py`)

OCR · LLM 을 쓰지 않는다. PDF 글자층(PyMuPDF words / spans)과 **표 괘선(drawings)** 만 쓴다.

1. **행 번호 열** 찾기: 오른쪽 끝이 맞는 정수 단어 열, 70% 이상 연속. 두 열이면 Form 102.
2. 행마다 그 높이를 지나는 **세로 괘선**으로 칸을 자른다(이중선은 하나로). 값 열 시작(≈x313)과 가운데(≈x438)는 행 대부분이 공유하는 괘선에서 런타임에 잰다.
3. 라벨 칸 1개 → 값 전체 / 2개 → 왼쪽 · 오른쪽 절반 / n개 = 값 칸 n개 → 하나씩. **안 맞으면 `raw.<행>` 으로 남기고 Review Required** (지어내지 않음).
4. 단위만 있는 칸(`bar-g`, `ºC`, `psi`, `in`)은 값의 단위로.
5. 왼쪽 그룹 캡션(GENERAL · ACTUATOR · SOLENOID VALVE …)은 캡션 열의 가로 괘선 사이 띠로 정한다 → 같은 라벨(Manufacturer · Type · Material)이 그룹별 다른 키(`act_manufacturer`, `sov_manufacturer`).
6. Form 102: 굵은 글씨 = 값, 보통 글씨 = 라벨 (`Line Size [2] in Schedule: [80S]`). 세로 글자 캡션(T A G · V A L V E G E N. …)이 그룹.
7. Sheet 2 NOTES / Form 102 Sheet 3 은 번호 문단으로 · 문서의 GENERAL NOTES 는 번호별로 · 칸의 `General note - N` / `Note-N` 은 그 본문에 연결.
8. 한 Tag = (Doc No., Tag, Rev) — Sheet 1 에서 시작해 같은 문서 · 같은 Tag 의 다음 장을 붙인다. 목차 · INDEX 쪽은 데이터시트로 보지 않는다.

**실자료 결과**: 데이터시트 164 (On/Off 140 · MOV 24) · 전부 Notes 있음 · 칸 약 1만 8천 중 Review Required 69 (On/Off 13행 `Fluid State/Corrosive/Erosive/Toxic` 4라벨 행 68 + 1).
TBE 의 Requirement 164행과 **Tag 164/164 일치**.

## 4. Valve List 채우기 (`app/valve/tbe.py`)

- 기준 TBE(.xlsx)를 **그 자리에서** 고친다 — 시트 · 열 순서 · 병합 · 서식 · 필터 · 너비 유지.
- 열 경로 → 데이터시트 칸 대응(`COLUMNS`)은 **TBE 의 Requirement 행과 실제로 맞춰 본 결과**로 정했다:

| TBE 열 | 데이터시트 | 일치 (Requirement 행) |
|---|---|---|
| Piping Class · Body Size · Rating · Body Material · Ball Material | 같은 이름 칸 | 81/81 (ESDV&SDV 시트 등) |
| Leakage Class | **Tightness requirement** (7행) — On/Off · Leakage Class(9행) — MOV | 164/164 |
| Air Failure · Power Failure | Action on Air / Power Failure ('Fail Close' = 'Close' 로 비교) | 164/164 |
| Gasket · Stud Bolt Material & Type | `Bolting / Gasket = Note-1` → Note 1 의 `Gasket material:` · `Stud Bolt material:` 부분 | 내용 다름 다수 → 실제 차이로 표시 |
| Body Type · Full / Reduced Bore | `Ball (Full Bore) - Floating` 에서 단어 | — |
| Solenoid Valve Body / Type / Power / IP | SOV 칸 | 81/81 |

- 결과: 같은 Tag 는 바뀐 칸만 덮고 **노란색 + 'Previous:' 메모**. `VTA` · `General note - 3` 처럼 목록보다 덜 말하는 값은 **덮지 않고 메모만**.
  새 Tag 는 그 밸브 종류 시트 끝에 첫 블록 서식으로 추가(Tool Status = NEW). 모든 칸에 **출처(파일 · 쪽 · 행) 메모**.
  오른쪽 열: DS Document No. · DS Rev. · DS Source · Datasheet Notes · Tool Status · Changed Columns. 새 시트 'Datasheet Notes' (Note 한 줄씩).
- 실자료: 164 Tag 갱신, 실제로 다른 칸 약 570 (예 `1C3AS2 → 1C3AS2-A`, `900# → 1500#`, `120V AC → 24 V DC`, SIL `No → SIL 1`), 목록 값 유지 약 980.
- 정렬: 기존 블록 순서는 바꾸지 않는다(서식 · 병합이 깨진다). 새 Tag 만 Tag 순으로 덧붙인다.

## 5. 데이터 (SQLite `{data}/valve/valve.db` · 원본 `{data}/valve/files/<해시>`)

| 표 | 내용 |
|---|---|
| project | 프로젝트 (CO2 PJT …) |
| document | 올린 파일 — 종류(datasheet · valvelist · process · pms) · 해시 · 쪽 수 · 처리 상태 · 오류 · 요약(info) |
| datasheet | Tag · 정규화 Tag · 밸브 종류 · Doc No. · Rev · 날짜 · 양식 · 쪽 · Notes · Rev 이력 · **검토 상태** |
| field | 키 · 구역 · 라벨 · 행 · **읽은 값** · 단위 · 쪽 · 위치 · 상태 · 참조 Note · **수정 값 · 수정자 · 시각** |
| audit | 모든 변경(업로드 · 수정 · 되돌림 · 상태 · 의견 · 내보내기) — 전/후 · 누가 · 언제 · 사유 |
| comment | 검토 의견 · PDF 주석(쪽 + 위치) · 지움 표시(행은 남김) |

원본 파일은 해시 이름으로 한 번만 쓰고 다시 쓰지 않는다. 같은 파일 · 같은 Tag · 같은 Rev 를 다시 올리면 건너뛴다.
Revision 순서: A < B < … < 0 < 1 < 2 (`store.rev_key`). 최신 판 = 가장 높은 Rev.

## 6. 구조

```
대시보드(8080) 메뉴 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve
   └ iframe → P&ID 서버(8000) /valve/?embed=1&project=CO2 PJT&user=<본명>
        app/static/valve/   index.html · valve.css · valve.js   (빌드 · CDN 없음)
        app/valve/api.py    /api/valve/*  (FastAPI 라우터 — main.py 에 두 줄로 붙임)
                 extract.py  PDF → 칸 (PyMuPDF)          schema.py  라벨 사전 · Tag 정규화
                 store.py    SQLite · 원본 보관 · 감사     tbe.py     Valve List(openpyxl)
```

- 왜 P&ID 서버인가: 대시보드 서버는 표준 라이브러리만 쓴다(pip 금지). P&ID 서버는 회사 PC 에 PyMuPDF · openpyxl · FastAPI 가
  오프라인 휠로 이미 설치돼 있고, LOGIC · ROOM SIZE · 도서검토가 같은 방식으로 붙어 있다.
- 사양서의 React / TypeScript 는 쓰지 않았다 — 회사망에서 npm · CDN 을 쓸 수 없다. 같은 일을 하는 순수 JS 한 파일.
- 다른 계기(PT · TT · Flow · Level)로 넓힐 때: `schema` 에 라벨 사전, `extract` 에 양식 판별만 더하면 저장 · 화면 · 감사는 그대로.

## 7. 화면 (사양서 UI/UX · 참조 그림 6장)

왼쪽 고정 메뉴 9개: Dashboard · Document Management · Valve List · Datasheet Review · Revision Comparison · Process Data Verification ·
PMS Compliance · Reports & Export · Settings. 밝은 작업 화면 + 남색 메뉴 + 어두운 PDF 도구줄 (P&ID · LOGIC 과 같은 남색 · 파랑).

- **Datasheet Review**: 왼쪽 Tag 목록(검색 · 종류 · 상태) · 가운데 PDF(쪽 이동 · 확대 · 검색 · 주석 상자 · 표시 켜고 끄기 · 이전/다음 Rev · 표시 PDF) ·
  오른쪽 탭 8개(Summary · Datasheet Data · Process · PMS · Revision · Notes · Comments · History). **칸을 누르면 PDF 그 쪽 · 그 위치가 깜박인다.** 패널 너비 끌어 조절 · 마지막 Tag 기억.
- **Valve List**: 고정 머리 · 열 필터 · 정렬 · Tag 검색 · 다중 선택(Ctrl · Shift) · 두 번 눌러 수정 · 열 너비 · 열 순서(끌기) · 선택 행 상태 일괄 변경 · Excel 내보내기 · Tag 누르면 원본.
- 단축키: ↑↓/J K Tag · PgUp/PgDn 쪽 · + − 확대 · / Tag 검색 · F PDF 검색 · A 주석 · 1~9 메뉴.

## 8. 다음 단계

1. **Phase 3 Process Data** — Process Data PDF 표를 열 위치로 읽기(머리 단어 위치 · 2.3절) + Excel 읽기 · Tag 연결 · 단위 환산(barg↔kPa(g), °F↔°C, kg/h↔t/h; abs↔gauge 는 비교 안 함) · 결과 6종 · 주황 표시.
2. **Phase 4 PMS** — 2.4절 계획대로 Class 구조화 → 비교 → 빨강 표시, PMS 쪽 동시 열기.
3. Revision 비교 Excel 보고서 · Combined Mark-up PDF(4색 한 파일) · 스캔 PDF(OCR 은 회사 PC 에 엔진이 있을 때만).
4. On/Off 13행(4라벨) 칸 나누기 — 지금은 Review Required 로 남김.


## 9. 지적 사항 · 설계사 전달물 (2026-10-31 2차 요청)

### 9.1 무엇을 지적하나 (`app/valve/issues.py`, 규칙만 · 근거 칸의 쪽 · 위치 포함)

| 종류 | 언제 | 색 | 심각도 |
|---|---|---|---|
| Data Missing | 양식에 있는 필수 칸이 비었음 (공정값 칸은 Minor — Process DS 참조 확인) | 주황 | Major / Minor |
| Open Item | 필수 칸이 HOLD / TBC | 주황 | Minor |
| Data Error | Line No. 의 Class ≠ Piping class · Line No. 크기 ≠ Line Size · 운전 > 설계 · Fail 위치 ≠ Air Failure · 없는 General Note / Note 참조 | 빨강 | Major |
| PMS Non-Compliance / PMS Review | `pms.check` 결과 | 빨강 | Major / Minor |
| Revision Change | 같은 Tag 이전 Rev 대비 (표기만 다른 것은 변경 아님) | 노랑 | Info |
| Reviewer Correction / Comment | 검토자가 고친 값 · 남긴 의견 | 파랑 | Major |
| Extraction Review | 도구가 라벨-값 짝을 못 정함 (내부용, 기본은 전달본에서 제외) | 보라 | Internal |

실자료: Data Error 3 (00XV921 · 24XV090092 · 25XV090092 가 문서에 없는 General Note 46 을 참조 — 그 문서의 General Notes 는 1~19),
Data Missing 748 (전부 공정값 칸 · Minor), PMS Review 113, PMS Non-Compliance 0.
번호: 설계사용 지적이 1…n, 내부 확인은 그 뒤 — 화면 · Issue List · 표시 PDF 의 번호가 같다. 상태 Open / Confirmed / Dismissed / Resolved (`issue_state` 표, 사유 · 감사 기록). Dismissed 는 전달본에서 빠진다.

### 9.2 재질 비교 (`app/valve/material.py`) — 표기가 아니라 규격 · 등급

글자를 토큰으로 나누고(`SS316` → 316 + SS, `STAINLESS STEEL` → SS, ASTM · GR · TYPE 무시) 등급을 재질 계열로 묶는다.
`ASTM A351 CF8M` ↔ `316/316L SS A351-CF8M/CF3M` = Compliant(양방향 · dual-grade 표기), `316 SS / HF` = `SS 316/HF`,
`CS A216-WCB` = `Carbon Steel ASTM A216 Grade WCB`. 다른 계열(CF8M vs WCB · RTFE vs PEEK)만 Non-Compliant, 같은 계열 다른 제품 형태(CF8M vs F316) ·
요구 표기 누락(HF) 은 Review Required. Revision 비교 · Valve List 갱신도 같은 기준으로 '표기만 다름' 을 변경으로 보지 않는다.

### 9.3 PMS 읽기 (`app/valve/pms.py`)

Appendix C = QN · W15, Appendix D = QS (같은 Class 코드가 두 지역에 따로 있다). 데이터시트 문서 제목의 NORTH / W15 / SOUTH 로 지역을 고르고,
없으면 다른 지역을 찾아 'please confirm'. Class 머리(Flange Class · NACE · Valve Trim) + Ball Valve 품목(크기 범위 · Bore · Floating/Trunnion 로 고름).
`NACE Requirement: NONE` 은 요구 없음. 실자료: 지역별 Class QN 23 · QS 25, 품목 5,116개, 읽는 데 1.4초.

### 9.4 설계사 전달물 (`app/valve/exports.py`)

- **Issue List Excel**: No · Tag · Valve Type · Doc. No. · Rev · Sheet(x of y) · PDF File · PDF Page · Row · Field · Datasheet Value · Issue Type ·
  Description(영문) · Required/Expected · Severity · Status · Reviewer Note · 링크 2개(도구에서 그 칸 열기 · 원본 PDF 그 쪽). 시트 'Summary by Tag' · 'Info'(범례).
- **Mark-up PDF**: 지적이 있는 데이터시트 쪽만 원본에서 복사(원본 그대로), 색 상자 + 번호 라벨 — **인쇄 플래그**라 '주석 포함 인쇄' 없이도 종이에 나온다.
  데이터시트마다 'Issue Summary' 쪽(번호 · Sheet · 칸 · 값 · 문제 · 요구값), 여러 장이면 표지(Tag 별 개수) · Tag 별 책갈피.
- **분석 끝 자동 출력**: Datasheet 분석 작업이 끝나기 전에 Valve List(기준 TBE 양식) · Issue List 를 만들어 `{data}/valve/exports/<pid>/` 에 두고,
  화면은 끝나자마자 둘 다 내려받는다 (Reports & Export 에 이력).
- **Excel ↔ PDF**: Valve List 의 채운 칸 · DS Source 칸, Issue List 의 Tag · Open 칸은 하이퍼링크 → 이 도구가 `?ds=&key=&page=#review` 로 그 칸을 깜박여 연다.
  도구 안의 Valve List · Issue List 화면은 오른쪽 PDF 미리보기와 실시간 연동(한 번 누르면 그 장 · 그 위치). 데스크톱 Excel 의 셀 선택 자체를
  브라우저가 실시간으로 따라가게 하는 것은 Excel 추가 기능 없이 불가능하다 — 그래서 '칸 = 링크' 와 '도구 안 엑셀식 목록' 두 길로 했다.

## 10. 상용 수준 다듬기 — 실패 원인 분석 · 강건성 · 사용자 Mark-up (valve03, 2026-10-31 3차 요청)

### 10.1 평가 도구 `spike/valve_eval.py` (실자료로 재고, 기준값 `spike/valve_eval_baseline.json` = 개수만)

`python3 -W ignore spike/valve_eval.py --ds <Datasheet.pdf> --tbe <TBE.xlsx> --pms <PMS.pdf> [--save-baseline]`
A 추출(상태별 칸 수) · B TBE 와 칸별 일치(exact / same 표기만 다름 / soft 자리표시 / tbe_vta / **misread 쪽 글자에 TBE 값이 있는데 다르게 읽음** / different) ·
C PMS 결과 · D 지적 · E 속도.  보고서(`report.md`)에는 고객 값이 들어가니 저장소에 넣지 않는다.

| 항목 | valve02 | valve03 | 원인 → 고친 것 |
|---|---|---|---|
| 짝 못 지은 칸 (Extraction Review) | 69 | 1 | 이중 괘선 사이 좁은 칸(<9pt)을 값 칸으로 셈 · 빈 예비 행 · 단위 칸 분리 과잉 → `read_page` |
| 오독 (TBE 값이 쪽에 있는데 다른 값) | 11 | 0 | 번호 열 군집 · Form 102 굵은 글자 값 · 세로 머리글 · 'Gen Note-30' 을 Note 30 으로 읽음 |
| Data Missing 오탐 | 748 | 0 | 'For Process data refer to …-PR-DTS-…' 데이터시트는 공정 칸이 일부러 비어 있음 → `process_reference` (Phase 3 에서 대조) |
| PMS Review | 113 | 75 | PMS 품목 배치(run×branch) · 2글자 Class('A1') · NACE 를 Notes 에서 · 'Note 8' 처럼 값이 Note 에 있으면 Note 값으로 비교(`schema.effective`) |
| Valve List 비교 가능 칸 일치 | — | 3,975 / 4,278 (92.9 %) | 나머지 303 은 실제 차이(TBE 가 나중에 고친 값 등) — 도구가 고치지 않는다 |
| 새 Data Error | — | 2 | 'Body : Note-8' 인데 Note 8 머리가 'Bolting' → 잘못된 Note 참조 (`wrong_note`, 머리글 단어가 겹칠 때만) |

### 10.2 강건성 (`extract.read_pdf`)

- A4 가 아닌 쪽(A3 · A2 · 플로터 출력)은 A4 크기로 옮겨 읽고 상자는 원래 크기로 되돌린다 (`_normalised`, 차이 8 % 이상일 때만) — 판정 거리(pt)가 같은 뜻이 되게.
- 회전(90/270) 쪽은 회전을 풀고 읽은 뒤 상자를 회전 행렬로 되돌린다.
- 암호 PDF · 깨진 PDF · 복구된 PDF 는 `PdfError` 로 사용자가 할 수 있는 말("암호를 풀어 저장한 뒤 …")을 문서 오류에 남긴다. 글자 층이 없는 스캔 쪽은 'scan' 으로 표시(OCR 하지 않음).
- 속도: 456쪽 6초(13 ms/쪽) · 데이터시트 지적 0.5 ms · 프로젝트 지적은 캐시(쓰기 = 감사 행이 생길 때만 다시) · Mark-up PDF 데이터시트당 40 KB(전엔 314 KB, `garbage=4 · deflate`).

### 10.3 사용자 Mark-up (Datasheet Review 화면 PDF 위 'Mark-up' 줄)

| 도구 (단축키) | 저장 | Mark-up PDF 에 나가는 PDF 주석 |
|---|---|---|
| ⬚ 선택 (V) — 누르면 고르기, 끌면 옮기기, 모서리 · 선 끝 손잡이로 크기 | — | — |
| ▭ 사각형 (R · A) · ☁ 구름 (C) · ◯ 원 (E) | bbox | Square · Square(clouds=2) · Circle |
| ▆ 형광펜 (H) | bbox | Highlight |
| ╱ 선 (L) · ↗ 화살표 (W) | points = 두 끝 | Line (화살표는 끝 OpenArrow) |
| ✎ 펜 (P) | points = 획 목록 | Ink |
| T 글상자 (T) · 🗨 메모 (N) | bbox + 글 | FreeText(글 그대로) · Text(스티커) |

- 분류(Comment 파랑 · Error 빨강 · Missing 주황 · Question 파랑)를 고르면 색과 **Issue 종류**가 정해진다: Error → Data Error, Missing → Data Missing,
  Comment/Question → Reviewer Comment (Question 은 Minor, 'Question:' 머리). 그래서 검토자 표시가 자동 지적과 **같은 Issue List · 같은 번호**로 설계사에게 나간다.
- 모든 변경은 바로 저장(`comment` 행: kind · points · category, 지우기는 deleted=1) · 감사 기록 · ↶ 되돌리기(Ctrl+Z) / ↷ 다시(Ctrl+Y) 는 반대 요청을 보낸다
  (지우기 되돌리기 = `{restore:true}`).  Delete = 지우기, Enter = 의견 · 분류 고치기, Esc = 선택 도구.
- 화면은 쪽 그림 위 SVG(단위 = PDF pt) 라 확대해도 어긋나지 않고, 내보낸 PDF 주석은 Acrobat · Bluebeam 에서 그대로 고칠 수 있다. 모든 주석에 인쇄 플래그.

## 11. P&ID · LOGIC 개발 원리에서 빌려 온 것 (valve04)

출처: `docs/state_and_roadmap.md` §3 불변 · §4 실패 유형 · §6 단일 판정 자리 · §9 원칙, hotfix82(VOC · 재학습 경로), LOGIC L84(화면 자기검증) · L85(차등 시뮬레이션).

| 빌려 온 원리 | 밸브 도구에서 | 실측 결과 |
|---|---|---|
| §3 지문 게이트 — 지문이 움직이면 칸 단위 원인 전에 다음으로 가지 않는다 | `valve_eval.py --check`: 읽은 칸 전부(tag·rev·key·값·상태·쪽)의 지문 + 품질 개수. 움직이면 실패하고 바뀐 칸을 `--out/cells_diff.txt` 로 (고객 값이라 저장소 밖) | 지문 `spike/valve_eval_baseline.json` · 17,207칸 |
| §4-② 외워둔 값 · 절차 3 "문턱은 분포의 빈 띠에서만" | 이중 괘선 문턱 `extract.DOUBLE_RULE_GAP` 을 이름 붙인 상수로 · 평가가 문서마다 다시 재서 빈 띠 안인지 알린다 (다음 폭이 마지막 틈의 2배 이상 = 빈 띠) | 456쪽: 틈 5~7 pt · 칸 21 pt 부터 · 8~20 pt 비어 있음 → 9 pt 는 빈 띠 안 |
| §4-③ 검사기가 판정기와 같은 눈 | 'TBE 와 다름' 303칸을 규칙이 아니라 **쪽 글자**로 다시 확인 | 예: Stem `…Type 630` 은 쪽에 그대로 — 실제 차이 (TBE 가 덧붙임) |
| §4-① 찾고 있는데 안 쓴다 | 사전에 없는 라벨 1,920칸 조사 | 전부 MOV(Form 102) 항목 — 버리지 않고 제 라벨로 보관 · 화면에 보임. Valve List 열을 비게 만드는 것은 없음 |
| hotfix82 VOC → 재학습 경로 · "판정 코드는 정답지를 읽지 않는다" | Reports & Export › **Review Feedback (json)**: Confirmed/Dismissed(+사유) · 고친 값 · 직접 그린 Error/Missing(=놓친 것). `spike/valve_voc.py <파일> [--ds PDF]` 가 규칙별 맞은 비율 · 잘못 읽은 칸 · 놓친 것 + 지금 코드로 다시 돌린 결과. 판정 모듈이 이 파일을 안 읽는 것은 시험(AST)이 지킨다 | 참고축(게이트 아님) — 한 프로젝트 판정이 모든 프로젝트 정답은 아니다 |
| LOGIC L85 차등 시뮬레이션 (분석 → 다시 그림 → 다시 분석) | `spike/valve_diff_sim.py`: 읽은 값을 깨끗한 괘선 양식에 다시 그려 다시 읽는다 — 다르면 값 글자를 다루는 읽기의 약점 | On/Off 140장 · 12,470칸 **불일치 0** (그리기 쪽 한계였던 넷째 라벨 · 쪽 넘침 · 굽은 따옴표는 고쳐 뺐다) |
| LOGIC L84 화면 자기검증 · §4-⑪ "표시에는 독립 감사가 없다" | `spike/valve_ui_audit.cjs`: 9개 화면 · Mark-up 9종 그리기 · 옮기기 · 되돌리기/다시 · 지우기/복구 · Issue 연결 · PDF/Excel/피드백 — 서버 상태로 확인 · 캡처. **데이터 사본으로** 돌린다 | 22/22 통과 |

**판정이 일어나는 단 하나의 자리 (§6 방식)** — 같은 판정을 두 곳에서 하지 않는다.

| 판정 | 한 곳 |
|---|---|
| 칸의 '지금 값' (고친 값 > 해석한 Note 값 > 읽은 값) | `schema.effective` |
| 재질 같음 · 더 자세한 같은 값 · PMS 적합 | `material.same` · `material.equivalent` · `material.compare` |
| Tag 같음 · Rev 순서 | `schema.norm_tag` · `store.rev_key` |
| 지적 종류 → 색 · 검토자 분류 → 지적 종류 | `issues.COLOR` · `issues.MARK_TYPE` (PDF 색 `exports.RGB`, 화면 색 `valve.css` 변수 · `valve.js MKCOL` — 색값만 따로, 뜻은 issues 하나) |
| PMS 지역 | `pms.area_of_title` (못 정하면 다른 지역도 찾아 'please confirm' — §9 "도면이 말하지 않으면 묻는다") |
| 이중 괘선 문턱 | `extract.DOUBLE_RULE_GAP` |

## 12. 눈으로 본 것과 대조 — 456쪽 전수 (valve05)

**방법**: `spike/valve_visual_pack.py` 가 쪽마다 그림(위·아래 반쪽, 144 dpi) + 도구가 그 쪽에서 읽은 것(머리 · 칸 · Notes · General Notes)을 만들고,
검토 에이전트가 그림을 보며 항목마다 OK / WRONG / FALSE_BLANK / SPURIOUS / MISSING / WRONG_NOTE / HEADER 로 판정한다.
**오류로 셀 때는 반드시 PDF 글자 층으로 다시 확인**(눈의 오독을 도구 탓으로 세지 않게) · 그림과 글자 층이 다르면 그림을 따른다(사람이 보는 것이 기준).
2차는 고친 도구가 **바꾼 줄만** 다시 판정(바뀌지 않은 줄은 1차 판정 유지). 채점 `spike/valve_visual_score.py`. 결과(개수만) `spike/valve_visual_result.json`.
판정 파일 · 그림에는 고객 값이 있어 저장소 밖(`/tmp/vis*`).

| | 항목 | 오류 | 오류율 |
|---|---|---|---|
| 1차 (고치기 전) | 21,482 | 760 | 3.54 % |
| 2차 (고친 뒤) | 21,482 (바뀐 1,324줄 재판정 — 오류 0) | 2 | **0.009 %** |

남은 2 = 두 데이터시트의 sheet 2 표제란이 Doc. No. 끝자리를 빠뜨려 인쇄(도면 오타) — 도구는 sheet 1 번호를 유지하고 **Data Error 로 설계사에게 지적**한다.

**고친 원인 (모두 일반 규칙 — 특정 칸 맞춤 없음)**
1. 보이지 않는 글자: 나중에 그려진 불투명 채움이 덮은 글자(엑셀 드롭다운 잔재 'N/A or other' · 'SHEET 1 OF 2' 의 2 아래 숨은 4 · 'NA' 아래 숨은 'Required')는 읽지 않는다 — 판단은 쪽의 그리기 순서(seqno), 같은 자리 같은 글자 겹침은 한 번만. 칸 음영처럼 글자보다 먼저 그린 채움은 해당 없음.
2. 줄 묶기: 3 pt 칸(bucket) 대신 '낱말 가운데가 그 줄의 높이 안' (P&ID 실패 유형 ④) — 두 부분 값의 순서 뒤바뀜 · Notes 줄 묶기.
3. 쪽 바닥글 'Page N of M' 이 마지막 Note 에 붙던 것 — Notes 는 자기 테두리(가로 괘선) 안에서만.
4. Form 102(MOV): 번호 열이 하나인 sheet 2 도 'Label : value' 행이 과반이면 Form 102 로 · 오른쪽 열에 번호 없는 'Instrument Type : …' 은 그 행의 짝 · 공정표 sheet 의 머리 행(Tag/PID/Service/Line …)도 읽음 · 단위나 '/' 만 있는 칸은 빈칸.
5. 'Sheet | 3 | of | 3' 처럼 칸이 나뉜 표기 · 두 줄로 넘어간 문서 제목 · 'N. ATTACHMENT' 를 삼킨 마지막 General Note · 'HOLD:' 목록을 Notes 와 분리(section).

**새 지적(설계사용)**: sheet 2 표제란 Doc. No. 가 sheet 1 과 다름 · 뒷장이 반복한 Tag/PID/Service/Line 이 sheet 1 과 다름 — 실자료에서 3건(그중 1건은 MOV 한 Tag 의 Line No. 가 sheet 1 · 2 에서 다름).
속도: 456쪽 11~13초(숨은 글자 판단 포함, 처음 구현 35초를 순수 산술로 줄임).

## 13. Phase 3 — Process Data 비교 (valve07)

- 읽기(`process.read_page`): 쪽의 세로 괘선 중 표 높이의 30 % 이상 걸친 것으로 열 띠를 만들고, 'Process Data …' 제목 줄과 단위 줄 사이의 모든 줄을 머리로 모아 열 이름(`COLUMNS` 구절표 → 키)을 정한다.
  단위 줄은 단위 낱말이 4개 이상인 줄. 데이터 행은 첫 띠가 정수(Sr no.)인 줄이고, 다음 줄의 낱말은 40 pt 안에서 같은 행의 이어진 칸으로 본다. Tag 는 `schema.norm_tag`.
  실자료 Annexure 7(61쪽, A3 가로): On-Off · MOV 표 23장 · 68 Tag(0.3초). Control Valve · PRV 표는 머리가 달라 읽지 않는다(범위 밖).
- 비교(`compare_item`): 공정 항목만. Fail 위치(FC/FO/FL ↔ Close/Open/Last) · 기밀(TSO ↔ Tight Shut-Off) · 상(Vapor ↔ Gas) · 유체(낱말 포함) · Line No.(Class 꼬리 `-QG1` 만 다르면 Review) ·
  P&ID(둘 중 하나와 같으면 Match) · 수치는 단위 차원이 확실할 때만 환산(psi→bar · °F→°C · min→s), 게이지/절대압은 양쪽에 기준이 적혀 있고 같을 때만, 허용 오차 1 %. 나머지는 Review Required.
- 결과 6가지: Match · Mismatch(→ 지적) · Review Required · Referenced(Datasheet 가 Process DS 를 참조해 비워 둔 칸 — `process_ref`) · Not in Process Data · Datasheet Blank.
- 실자료 결과: Datasheet 164 중 66 Tag 연결 · Match 215 · Mismatch 42 = Line No. 32(Class 코드 `1C0K8` ↔ `1C0KL-A`, 꼬리 `-5` ↔ `-N`) · P&ID 8 · Fail 위치 2(08SDV412A/B: Datasheet Close ↔ Process FO) · Review 2 · Referenced 749.
  모두 설계사에게 물을 실제 차이다 — 도구는 어느 쪽이 옳은지 정하지 않는다.

### 13.1 빈 Process Data 는 전부 지적 (valve08, 사용자 결정)

valve03 에서 'Process DS 를 참조하는 데이터시트의 빈 공정 칸' 748건을 오탐으로 보고 지적에서 뺐으나, 사용자가 **"없는 것은 전부 표기"** 로 정했다.
이제 PROCESS DATA 블록의 빈 항목은 참조 여부와 관계없이 Data Missing(Major)이고, 설명에 참조 문서(예: 03-02-PR-DTS-00002, Note 7)를,
Required/Expected 에 Process Data 표의 값(있으면)을 적는다. 실자료 2,529건(164 Tag, 평균 15). 읽기 지문은 그대로(바뀐 칸 0).

## 14. PMS 검토 점검 · 특수 요구사항 · 재질 검토 의견 (valve10)

요청: "PMS 기준으로 검토가 제대로 되는지 · 재질 검토 의견을 전문적으로 · Note 의 Special Requirement(PFP · Fugitive …) 가 Excel 에 잘 나오는지".

### 14.1 PMS 대조가 맞는지 — PMS PDF 와 한 줄씩 대조한 결과

- 맞게 읽음: Class 머리(Rating · NACE · Trim · CA) · Ball Valve 품목의 크기 범위 · Bore · Floating/Trunnion · 지역 QN/QS.
- **고친 오류 1건**: Trim(Ball)/Stem 을 Class 머리의 일반 Trim 과 비교했다. 1A1A 머리는 'TRIM 8 (13CR/HF)'(Gate/Globe 용)인데 Ball Valve 품목은 '316 SS BALL/STEM' → 316 SS 데이터시트 8개가 거짓 Review.
  이제 **고른 Ball 품목의 'X BALL/STEM' 이 우선**, 품목에 없을 때만 머리 Trim. 결과 Trim/Stem Review 8+8 → 0 (나머지 결과 그대로, 지문 불변).
- 남은 PMS 지적은 실제 문서 차이: 3R1B3 에 Ball Valve 품목 없음(2) · 6C0K8 에 10" 품목 없음(4) · XC0K8 에 22" 없음(1) · PMS 에 없는 Piping Class 13(API5L-X65 등) · 지역/Line No. 로 찾은 Class 확인 8 · RED PORT 인데 Full Port 품목만 28.
- Class 머리에서 더 읽는 것: P-T 표 · ASME Group · Service 목록 · General Class Notes · Item Specific Notes (재질 검토가 쓴다).

### 14.2 특수 요구사항 (`requirements.py`)

칸 · 데이터시트 Note · 문서 General Note 의 글에서 낱말/규격 번호로만 찾는다(추측 없음). 종류 15: NACE · Fugitive(ISO 15848-1, Class A-C, endurance class) · Fire-safe · PFP · Anti-static · Blow-out · SIL · PST · 경도 · EN 10204 3.1/3.2 · PMI · 충격시험 · DBB · 도장 · 기밀(Rate/Class).
칸 값이 'Not Required / No / NA' 면 '[datasheet: Not Required — 출처]' 로 따로 적는다 (예: Gen Note 26 은 PFP 를 말하지만 그 데이터시트 Fireproofing 칸은 Not Required → 둘 다 보여 엔지니어가 판단).
실자료 164 Tag 모두 한 줄 이상: NACE 589 · Fugitive 189 · PFP 305(+122 Not Required) · Anti-static 148 · Blow-out 141 · EN 10204 139 · SIL 312 · PST 128 · Fire-safe 140 · 경도 59 (출처 수).
→ Valve List 'Special Requirements (Notes)' 열 · 작업대 Summary 탭(출처를 누르면 그 Note/칸으로).

### 14.3 재질 검토 의견 (`matreview.py`)

| 규칙 | 수준 | 내용 | 근거 |
|---|---|---|---|
| MR-01 | Action | 시트 재질이 PMS Class Note 의 온도 한계를 넘음 (예: RPTFE 230 °C ↔ 설계 260 °C) | PMS General Class Note |
| MR-02 | Action / Confirm | 시트 수지의 일반 사용 한계 초과(Action) · 30 °C 안쪽(Confirm — 시트 P-T 곡선 요구). PTFE 200 · RPTFE 230 · PEEK 260 · Nylon 93 °C | 제조사 시트 P-T · 데이터시트 'non-metallic suitable for design condition' |
| MR-03 | Action | Process 설계온도가 PMS Class P-T 표 밖 · 설계압력 > 그 온도의 Class 허용압 | PMS P-T Limits (ASME B16.5) |
| MR-04 | Action | 저온 배관(A333 · LTCS · PMS 'LOW TEMP')에 WCB/A105 본체 (-29 °C 한계) | ASME B16.34 / B31.3 |
| MR-05 | Confirm | 본체와 배관 계열이 다름(SS ↔ CS) | 이종 용접 · PMS |
| MR-06 | Confirm / Note | CO2 에 탄소강 본체 — 부식여유 없음 Confirm, 있으면 Note | 탄산 부식 |
| MR-07 | Note | NACE 에 316/316L — 용체화 · 22 HRC · ISO 15156-3 Table A.2 한계, 설계 60 °C 초과면 재질선정보고서 확인 | ISO 15156-3 |
| MR-08 | Confirm / Note | 17-4PH(A564 630) Stem — NACE 면 H1150D · 33 HRC 명기 요구 | ISO 15156-3 |
| MR-09 | Note | HF(경화육성) 종류 · 두께 미기재 | API 6D · ISO 15156-3 |
| MR-10 | Confirm | PMS 'DUAL GRADE' Note 인데 316L 만 기재 | PMS Class Note |
| MR-11 | Confirm / Note | NACE 에 B7(비 M) 볼트 · B8M CL.2(노출 볼트 불가 — 볼트 사양이 NACE 를 적었으면 Note) · B7M/L7M 은 Note | ISO 15156-2 §A.2.2.4 |
| MR-12 | Confirm / Note | CO2 에서 엘라스토머 · O-ring 의 급감압(RGD) 자격 | ISO 23936-2 · NORSOK M-710 · Gen Note |
| MR-13 | Note | Fire-safe 연질 시트 — API 607 / ISO 10497 시험 인증 범위 | API 607 |
| MR-14 | Confirm | Process 유체가 PMS Class Service 목록에 없음 | PMS Service |
| MR-15 | Note | NACE 에 탄소강 본체 — 22 HRC · 용접부 250 HV10 | ISO 15156-2 A.2.1 |

- 프로젝트 값(설계온도 · 압력 · P-T · Class Note · 유체)은 문서에서 읽고, 일반 재질 지식만 표로 둔다(조항과 함께). 값이 없으면 그 규칙은 말하지 않는다.
- 실자료(164 DS · PMS · Process Data): **Action 5**(MR-01 98ESDV009 RTFE 230 °C ↔ 260 °C · MR-03 98BDV101/301 211 °C > 3C0K8 209 °C · 98ESDV015/016 98 barg > 3R1B 43.8 barg@195 °C),
  Confirm 29(시트 근접 7 · CO2 탄소강 4 · 17-4PH 5 · B7 10 · Service 3), Note 다수. Issue List 에는 Action/Confirm 만 'Material Review'(청록).
- 화면: 작업대 오른쪽 **Material 탭**(수준별 카드 · 근거 · 증거를 누르면 칸/Note/PMS 쪽/Process Data 쪽) · 머리 띠 'Material' 칩. Valve List 'Material Review (Tool)' 열.
- 품질: `valve_eval.py --pd <Process Data PDF>` 의 F 절이 규칙×수준 개수를 기준값에 둔다.

## 15. Ball Valve 엔지니어로서 검토 (valve11)

요청: "Ball Valve 전문가가 되어야 한다 — 전달한 Datasheet · PMS 를 디테일하게 학습하고, Ball Valve 전문 지식을 기본으로, 전문 엔지니어로서 검토".
원칙은 그대로다: 검출에 LLM 을 쓰지 않는다(CLAUDE.md §4). 그래서 '전문가' 는 세 겹의 결정적 규칙으로 만든다.

1. **지식** `app/valve/knowledge.py` (28항목 → `docs/valve/BALL_VALVE_KNOWLEDGE.md` 로 생성) — API 6D / ISO 14313 · ISO 17292 · ASME B16.34 · B16.5/B16.47 · B16.10 ·
   API 598 / ISO 5208 · API 607 / 6FA / ISO 10497 · ISO 15848 · NACE MR0175 / ISO 15156 · IEC 61508/61511 · Floating/Trunnion · SPE/DPE · DBB/DIB · 캐비티 릴리프 ·
   시트 수지 · 메탈 시트 · HF · Stem(Blow-out · Anti-static) · 본체 구조 · Drain/Vent · Bore · 보온 · 액추에이터 · 탄소강 최저온도 · CO2 · RGD · Dual grade · 증명서.
   출처끼리 다른 값(Floating 한계 크기 등)은 "통상 관행 — 회사 사양 우선" 으로 적었다. 웹 확인: 17-4PH(2020판 50 % SMYS 단서) · 316 의 60 °C / 100 kPa · Floating 크기 관행.
2. **설계 규칙** `app/valve/expert.py` VR-01~15: 플랜지 면(PMS RF/RTJ) · 플랜지 규격 대 크기(B16.5 ≤ 24″, B16.47 > 24″) · Floating 크기×Class · PMS 품목과 Floating/Trunnion ·
   Fail 위치 대 스프링 · SIL(Fail-last · PST) · 누설 등급 대 시트/TSO · Anti-static/Blow-out · 가연·독성 유체의 Fire-safe · Trunnion 시트 구성/캐비티 릴리프(액상·Dense CO2 면 Confirm) ·
   Cold 보온 확장 Stem · Piggable Full bore · 밸브 크기 대 배관 · Erosive 연질 시트 · 액추에이터 계수. 'Note 2' 같은 참조 칸은 그 Note 글까지 읽는다.
3. **학습** PC-01: 프로젝트의 모든 데이터시트(Tag 별 최신 Rev)를 Piping Class 로 묶어 칸마다 다수 값을 익히고, 5개 이상 중 80 % 이상이 같은데 혼자 다르면 Confirm
   (표기만 다르거나 더 자세히 쓴 것은 제외). 데이터시트를 올리거나 값을 고치면 다시 익힌다(`api._peers_for` 캐시 키 = 데이터시트 수·id · 감사 id).

실자료(164 DS): VR Action 3(19XV122 등 2″ 에 ASME B16.47-B) · Confirm 44(Dense CO2 Trunnion 캐비티 33 · Rate B 연질 시트 4 · Cold 보온 4 · Fire-safe 2 · Piggable bore 1) ·
Note 113 · PC-01 Confirm 6(3C0K8 의 '316 SS/FHF' 2개 · API5L-X65 MOV 1500# ↔ 다수 900# 2개 …).
화면: 작업대 **Expert 탭**(재질 · 설계 · 다른 데이터시트 대비, 의견마다 '지식' 펼치기) · Settings › **Ball Valve 지식** · Issue 'Valve Review' · Valve List 'Expert Review (Tool)' 열.

## 16. 설계사에게 가는 코멘트는 핵심만 (valve12, 사용자 요청)

- 규칙마다 `short`(한 줄 · 120자 이하 · 시험이 지킴) = **무엇이 문제 · 값 · 할 일**. 예: "Seat RTFE limited to 230 °C (PMS 1C3AS2 Note 018); design temp. 260 °C. Revise seat material."
- Issue List Excel · Mark-up PDF · Valve List 'Expert Review (Tool)' 은 short 만 쓴다. 긴 설명 · 근거 규격 · 지식은 도구의 Expert 탭에만(카드 안 '▸' 줄이 설계사에게 가는 글).
- 다른 지적도 줄임: Data Missing "Fluid: no value; ref. 03-02-PR-DTS-00002 (Note 7). Provide value." · Open Item "'HOLD' on HOLD/TBC. Release and give value." ·
  Note 참조 오류 · Revision 인용은 낱말 단위로 40~70자에서 자름(`issues._cut`).
- 실자료 평균 길이: Material/Valve Review 350 → 68자 · Data Missing 136 → 80 · Open Item 93 → 56. 판정 · 개수는 그대로(eval 기준값 불변).

## 17. 설계사용 출력 때 Issue Type 고르기 (valve13, 사용자 요청)

- Issue List Excel · Mark-up PDF 를 만드는 모든 단추(Reports & Export 의 둘 · Issue List 화면의 둘 · Datasheet Review 의 한 Tag PDF · 분석 끝 'Mark-up PDF')가
  먼저 **Issue Type 선택 창**(`valve.js pickTypes`)을 연다: 종류마다 한글 설명 · 건수, '전체 / 모두 끄기 / 설계사용 기본', 고른 종류 · 건수 합계. 아무것도 안 고르면 '만들기' 가 꺼진다.
- 고른 종류는 다음 출력 때 그대로 기억한다(브라우저 `valve.xtypes`). Issue List 화면에서 종류 필터를 걸어 둔 채 누르면 그 종류가 미리 골라진다(이때는 기억을 덮지 않음).
- 서버는 원래 `types=` 를 받는다(`api._select`) — 바뀐 것은 화면뿐. Dismissed 는 언제나 빠진다. 분석 끝에 자동으로 만드는 Issue List 는 그대로 설계사용 기본 종류.
- 실자료: 전체 2,819건 · PDF 548쪽 → Material + Valve Review 만 89건 · 199쪽.

## 18. Area · Unit 로 나누어 보는 Excel (valve14, 사용자 요청)

- `app/valve/location.py`: **Area** = 데이터시트 문서 제목의 QELNG NORTH / QELNG SOUTH / W15 INJECTION AREA → North / South / W15,
  제목이 기존 플랜트 시스템을 말하면('(SYSTEM 999 – UNIT 19)' — 데이터시트 Note 가 'QELNG South Brownfield System 19' 라고 부름) 또는 Note 에 'brownfield' 가 있으면 **Brownfield**.
  **Site** 는 Brownfield 여도 North / South 를 남긴다. **Unit** = 제목의 UNIT nn → 없으면 P&ID 번호(98-**98**-PR-PID · 002-08-**84**-PR-DR) → 없으면 Tag 앞 숫자.
  표지와 장 번호가 다른 문서(02-09-IN-DTS-00003 표지 ↔ 장 -00006)는 같은 System-Unit 표지의 제목을 쓰고, 표지 없는 한 장짜리 Revision 은 같은 Doc. No. 의 다른 업로드에서 찾는다. 문서에 없으면 비워 둔다.
- Issue List Excel: 맨 앞 **Area · Site · Unit** 열 + 필터 · Summary by Tag 도 같은 열 · Material/Valve Review 열 추가. 열 번호는 이름으로(`exports.CI`).
- Valve List Excel: **'All Valves' 시트**(전체 Tag 한 줄씩 — Area · Site · Unit · Tag · 종류 · Doc · Rev · Service · P&ID · Line · Class · Size · Rating · Body Type · 연결 · 재질 4 · Fail · 누설 · NACE ·
  특수 요구사항 · Expert Review · 열린 지적 수 · 어느 시트 · Tool Status · 출처, 정렬 North → South → Brownfield → W15 · Unit · Tag) + 밸브 종류 시트마다 Area · Site · Unit 열과 머리 줄 필터.
- 실자료 164 Tag: North 74 · South 69 · Brownfield 14(North 7: Unit 09 · 84 / South 7: Unit 19 · 29 · 39 · 84 · 85) · W15 7.

## 19. Area · Unit 별 Tag 번호 규칙 — 프로젝트 Tag 에서 배움 (valve15, 사용자 요청)

- 받은 파일에 Tag Numbering Procedure 문서는 없다(PMS 의 'numbering philosophy' 는 Pipe Class 번호 규칙). 그래서 `app/valve/tagrules.py` 가
  올린 데이터시트의 Tag(전 Revision)를 Area · Site · Unit 별로 묶어 규칙을 배운다(80 % 이상이 따르는 것만): 구조 접두 + 기능 코드 + 구분 + 번호 + 끝 글자,
  **접두가 무엇과 같은지**(Unit · 제목 System · P&ID System · Doc. No. System), 번호 자릿수 · 고정 앞자리(번호 끝 3자리는 늘 자유), 구분(없음 · 공백 · '-'), 끝 글자(A/B), **계열 → P&ID 장**.
- 배운 결과(실자료): North U98 `98 + ESDV/BDV/MOV/XV + ␣ + 980nnn[A/B]`(계열 1 → P&ID 2~13, 2 → 16~27, 3 → 30~41, 4 → 44~55, 0 → 공통) ·
  South U98 `98 + 기능 + '-' + nnn[A/B]`(계열 0 · 1 · 3) · W15 `315(P&ID System) + MOV/ESDV + ␣ + 980nnn` · Brownfield North 접두 = 제목 SYSTEM(00/01/02/24/25 · 08) ·
  Brownfield South 접두 = 제목 UNIT(19 · 29 · 39 · 84 · 85).
- 검사(Expert 탭 'Tag 번호' · Issue 'Valve Review'): TG-01 구조 아님 · TG-02 접두 ≠ 그 그룹의 출처 값 · TG-03 번호 자릿수/앞자리 다름 · **TG-04 같은 Tag 가 두 문서에(Action)** ·
  TG-05 기능 코드 ↔ Fail 동작(ESDV/SDV 보통 Fail Close, BDV Fail Open — 일반 관행, 프로젝트 사양 우선). 실자료: TG-05 4건(North ESDV-xx10 계열이 Fail Open) · 나머지 0.
- 화면: Settings › **Tag Numbering** 표(Area · Site · Unit · 수 · 형식 · 접두 출처 · 기능 코드 · 번호 · 계열 → P&ID · 예 · 중복). `GET /api/valve/projects/{pid}/tagging`.
  Valve List 'All Valves' 에 Tag Prefix · Function · Loop No. 열(필터). 지식 `tag.numbering`.

## 20. No. 열과 Summary 시트 (valve16, 사용자 요청)

- 두 Excel 모든 목록 시트의 첫 열 = **No.** (Issue List · Summary by Tag · All Valves · Datasheet Notes). Issue List 의 No. 는 화면 · Mark-up PDF 와 같은 번호(순서 그대로).
- **Summary 시트**(`exports.summary_sheet`, 두 파일 공용): No. · Area · Site · Unit × 분류 · Total (+ 추가 열), 필터 · Total 줄 · 아래에 'By Area' 표.
  Issue List = Issue Type 별 건수 + Major · Minor · Tags (두 번째 시트). Valve List = Valve Type 별 수 + Open Issues · Tags with Action · New / Updated Tags ('All Valves' 앞).
- Summary by Tag 는 Area → Site → Unit → Tag 순.

## 21. Issue List Area 순 · All Valves 에 Note 요구사항 열 (valve17, 사용자 요청)

- Issue List 시트: **Area → Site → Unit → Tag** 순(North · South · Brownfield · W15), 한 Tag 안은 데이터시트 순서 그대로, No. 1…n 다시 매김.
- All Valves: Notes · General Notes · 칸에서 찾은 요구사항을 **종류마다 한 열**(청록 머리): PFP · Fugitive Emission (ISO 15848) · Fire Safe · NACE / Sour · SIL · Partial Stroke Test ·
  Tightness / Leakage · Anti-static · Blow-out Proof Stem · Hardness Limit · Material Cert. (EN 10204) · (PMI · Impact Test · DBB · Painting — 어느 밸브에라도 있을 때만).
  칸 값 = **데이터시트 줄의 답이 먼저**(그 밸브를 정함 — 예: Gen Note 26 이 PFP 를 말해도 Fireproofing 줄이 Not Required 면 'Not Required'), 다음 Note 의 세부(Class A type tested · SIL 2 · 3.2 · Rate A · 22 HRC),
  끝에 출처(row · Note · GN). `requirements.columns` · `requirements.COLUMNS`. 'Special Requirements' 한 칸 · NACE · Leakage 칸은 All Valves 에서 이 열들로 바뀜(종류 시트는 그대로).
- 실자료(164 Tag): PFP Required 42 / Not Required 122 · Fugitive Class A type tested 144 (+ Class A 7) · SIL 2 114 · EN 10204 3.2 128 / 3.1 11 · Fire Safe HOLD 11.
  데이터시트 줄과 Note 가 다르면 둘 다: 'SIL 1 · notes: SIL 2' (2) · 'Tight Shut-Off — Rate B · notes: Rate A' (1) — 설계사 확인 거리.

## 22. Issue List 'Summary by Area' 시트 (valve18, 사용자 요청)

- Issue List Excel 세 번째 시트 **Summary by Area**(`exports._area_sheet`): Area 마다 한 줄 — Units(Brownfield 는 Site-Unit) · Tags · Total · Major · Minor · Issue Type 별 · 검토 상태(Status) 별, 필터 · Total 줄.
  아래 표 'By Area × Issue Type × Severity'(Area · 종류 · Major · Minor · Info · Total · Tags).
- 시트 순서: Issue List · Summary(Area · Site · Unit 세부) · Summary by Area · Summary by Tag · Info.
- 실자료: North 74 Tag · 1,167 · South 69 · 1,184 · Brownfield 14 · 254 · W15 7 · 218 = 2,823.

## 23. Valve List 'Summary by Area' 시트 (valve19, 사용자 요청)

- Valve List Excel 시트 순서: TBE Tabulation · Summary · **Summary by Area** · All Valves · 종류 시트 · Datasheet Notes.
- Summary by Area(`tbe._area_sheet`): Area 마다 한 줄 — Units(Brownfield 는 Site-Unit) · Tags · Valve Type 별 수 · Open Issues · Tags with Action · PFP Required · SIL · Fire Safe on HOLD · New / Updated, 필터 · Total.
  아래 'By Area × Valve Type' 표: Tags · Sizes · Ratings · Open Issues · Tags with Action · PFP Required.
- 실자료: North 74(ESDV 45 · BDV 18 · XV 5 · MOV 6, PFP 31) · South 69 · Brownfield 14(SDV 4 · XV 10, Fire Safe HOLD 11) · W15 7 = 164.
