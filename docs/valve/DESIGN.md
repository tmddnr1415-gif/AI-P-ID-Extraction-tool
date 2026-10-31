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
