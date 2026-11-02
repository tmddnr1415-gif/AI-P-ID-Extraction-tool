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

## 24. 상용 수준으로 — 가볍게 · 간결하게 · 시뮬레이션으로 (valve20, 사용자 요청)

요청: "최대한 가볍게 · 끊김 없이 · 글 적게 · UI 개선 · 수천 번 시뮬레이션으로 보완 · 상업 판매 수준".

### 24.1 속도 (실측 · 164 DS → 990 DS 복제본으로도)
- **데이터시트별 검토 캐시** `api._DEEP_CACHE` + 디스크 `valve/cache/review/<id>.json`: 키 = 그 데이터시트의 최신 감사 id · 검토 상태 + 프로젝트 판(`_profile_ver`: 데이터시트 수/id · 문서 수/id · 값 수정 감사 id).
  이슈 상태 · 의견 · 검토 상태 변경은 그 데이터시트만 다시 계산하고, 값 수정 · 업로드만 전체(동료 학습 · Tag 학습이 바뀌므로).
- `_ds_full` 은 캐시 확인을 맨 앞에서(전에는 칸 · 의견 · 이력 · Revision 질의 8개를 먼저 하고 확인했다). 프로젝트 판은 요청당 한 번(`pv=`).
- PMS · Process 프로젝트 화면은 캐시의 `pms` · `process` 를 모아 준다(다시 계산하지 않음). Grid 캐시. **서버 시작 · 분석 끝에 백그라운드 워밍**(`warm`).
- **`_json()`**: 큰 응답은 FastAPI `jsonable_encoder` 를 거치지 않고 바로 직렬화(2,800 지적에서 200 ms 가 20 ms).
- 결과(164 DS): issues 250 → 30 ms · PMS 784 → 21 · Process 530 → 20 · datasheet 23 → 5 · summary 냉간 3.9 s → 0.2 s(디스크 캐시).
  990 DS: 재시작 냉간 summary 36 s → 0.23 s · issues 0.5 s(9 MB) · UI Issue List 6.1 → 2.2 s · Valve List 2.4 → 1.7 s · Review 1.1 → 0.7 s · 다음 Tag 0.35 s.
- UI: 큰 표(Issue List · Valve List)는 250행 먼저, 나머지는 idle 배치(`chunkRows`) — 멈춤 없음. `indexOf` O(n²) 제거. 이슈 응답에서 화면이 안 쓰는 키 제거(-25 %).
- DB: 스키마 초기화는 프로세스당 한 번 · `busy_timeout` · **매일 첫 실행 때 `valve/backups/valve.db.<날짜>.bak`**(7개 보관).

### 24.2 간결한 UI
- 작업대 Issues 탭: 같은 종류 · 같은 이유의 지적은 **한 카드**(칸 chip · 상태 일괄 · 펼치기). 13개 'no value' 카드 → 1개.
- 오른쪽 탭 한 줄(가로 스크롤 · 활성 탭 자동 노출). 설명 문장은 **머리 '?' 단추**로 켤 때만(기본 숨김, `body.hints`). 대시보드 10 → 8 타일(검토 진행은 도넛). 내보내기 카드 한 줄씩. 미리보기 캡션 줄바꿈 깨짐 수정.
- 전역 오류 토스트(`unhandledrejection`) · Settings › 정보에 버전 · 데이터 경로 · 푸터에 버전(`GET /api/valve/version`).

### 24.3 수천 번 시뮬레이션 (`spike/valve_sim.py`)
- 합성 데이터시트 생성기(7 PMS Class · 재질 · 시트 · Stem · 플랜지 · 크기 · Floating/Trunnion · Fail · SIL · 누설 · 보온 · Piggable · 볼트 Note · General Note · HOLD · 빈 공정 · Line/Class 불일치 · 동료 이탈 · Tag 중복 · 4 Area)
  + 같은 손잡이에서 유도한 **엔지니어 기대값(oracle)** 44 규칙 → 엔진 결과와 대조(FN · FP · 수준 차 · 예외), 퍼즈(None · 쓰레기 · 유니코드 · 거대 수 · 틀린 단위).
- 전 3,000건: 예외 0 · recall 0.955 · precision 0.906 · 수준 차 785 → **후 10,000건: 예외 0 · recall 1.000 · precision 1.000 · 수준 차 0** · 퍼즈 2,000 예외 0.
  고친 결함: `R-PTFE` 토큰(실자료 41건이 이 표기) · METAL/NYLON 시트 계열 · LCC/LF2 = LTCS · MR-03 2점 P-T 표(XC0K8) · MR-13 HOLD 제외 · VR-09 크기에 맞는 PMS 품목만.
  실자료 영향: MR-13 Note 11 → 0 · VR-09 Confirm 2 → 20(Fire Safe 빈칸인데 PMS 품목은 Fire tested — 실제 확인 거리). 읽기 지문 불변.
- 시험 게이트 `test_simulation_gate`(400건 seed 7: 예외 0 · recall/precision ≥ 0.99). 한계: oracle 이 엔진과 같은 손잡이에서 나오므로 "규칙이 의도대로 동작한다" 를 재는 것이지 "규칙이 옳다" 를 재지는 않는다 — 규칙의 옳음은 회사 엔지니어 확인(§14.3 · §15 표).

## 25. 두 번째 시뮬레이션 — 실자료 변이 재생 · 그리드 캐시 결함 (valve21)

- `spike/valve_mutate.py`: 실자료 164 데이터시트마다 엔지니어가 알아보는 단일 변이 14가지(시트 PEEK/메탈 · 설계온도 +80 °C · 본체 WCB · RF↔RTJ · 300# · 10″ Floating · ESDV Fail Open · HOLD · 필수 칸 비움 ·
  Tag 접두 99 · Tag 중복 · Fugitive Note 제거 · 엘라스토머 씰)를 넣고 **지적의 변화가 정확히 기대한 집합인지** 대조. 1,839건 87.8 % → **100 %**.
  고친 결함: PMS Fire Safe 가 'HOLD (… API 607 …)' 를 "607" 때문에 Compliant 로(→ Review) · 동료 다수가 표기('CF8M/CF3M' 32 vs 'CF8M' 9)로 갈려 WCB 본체를 못 잡음(→ 같은 뜻은 합침).
  oracle 도 55 규칙으로 넓힘(VR-08/10/14/15 · MR-12 · TG-02/03 · PMS Trim/Stem/NACE/Fire · Data Error op>design · Fail↔Air failure). 합성 3,000 × 2 seed: 1.000/1.000.
- PMS NACE 'NA'(해당 없음)는 NACE 요구 Class 에서 Non-Compliant 가 아니라 **Review**("N/A 라고 썼지만 Class 는 NACE 요구 — 확인"). 실자료 영향 없음.
- 실자료 영향: PMS Fire Safe Compliant 10 → Review 10(HOLD 인 Fire Safe) · PMS Review 58 → 68. 읽기 지문 불변.
- 화면 결함: Grid 캐시가 `Response` 객체를 저장 → gzip 미들웨어가 헤더를 제자리에서 바꿔 두 번째 요청이 `ERR_CONTENT_LENGTH_MISMATCH`, Valve List 가 '불러오는 중…' 에 멈춤.
  바이트를 저장하고 매번 새 Response(`tests/test_valve_api_cache.py` 가 gzip 아래에서 두 번 요청). 목록 실패 시 '다시 시도' 단추.
- Area · Unit 을 화면에: Valve List 열(필터) · Issue List Area 선택 · 작업대 머리 · 대시보드 'By Area' 카드(`summary.by_area`). Expert 탭 Note 는 접힌 채 시작.
- 검토자 동작 실측(164 DS): 다음 Tag 55 ms · 쪽 넘김 130 ms · 상태 변경 즉시 · 목록 필터 < 0.5 s.

## 26. 지원 · 운영 (valve22)

- `GET /api/valve/health`: DB · files/cache/backups/exports 쓰기 · 디스크 여유(500 MB 미만이면 경고) · 마지막 백업 · 리뷰 캐시 수 · 워밍 중인 프로젝트. Settings › 정보 › **진단** 단추가 보여 준다 — 문제가 있으면 그 화면을 개발 쪽에.
- Issue List 화면의 필터 · 검색은 행만 다시 그린다(도구줄 · 포커스 유지, 0.6 → 0.35 s).
- 사용자용 설명서 `docs/valve/USER_GUIDE.md`(검토 엔지니어 관점 · 5분 시작 · 화면 · 지적 종류 · 작업대 요령 · Excel · FAQ).

## 27. 추출 견고성 시뮬레이션 — 다른 양식에도 읽히나 (valve22)

- `spike/valve_sim_pdf.py --n 380 --seed 2`: Form 80 구조를 흉내 낸 합성 데이터시트 PDF 에 19가지 변형(글꼴 ±2 pt · 열 위치/너비 · 라벨 동의어 · 두 줄 값 · 빈 행 · Max/Nor/Min 블록 · 단위 열/붙임 ·
  'Note-1'/'NOTE-01' · A3 · 90° 회전 · 0.1° 기울기 · 가는/굵은 괘선 · Sheet 2 of 2 · 스캔본 · 행 번호 누락)을 넣고 **놓은 값을 oracle 로** 재읽기 정확도를 잰다.
- 전 0.833 → **후 0.992**(380장 · 오독 0 · 예외 0 · 스캔본 20/20 판별). 고친 것(`extract.py`, 실자료 지문 불변 · diff_sim 불일치 0):
  괘선 직선 판정을 기울기 기준으로(0.1° CAD 출력) · Max/Nor/Min 이 있는 On/Off 장을 Form 102 경로로 보내던 것(번호 행의 70 % 이상이 Unit/Max/Nor/Min 머리 아래일 때만) ·
  'Note-1' · 'NOTE-01' · 'Note 1:' 번호 인식 · 'NOTES :' 줄에서 시작하는 Note · 괘선 위 낱말이 두 칸에 찍히던 것.
- 아직 약한 것(인수인계): **행 번호 없는 행**은 못 읽음(0.86) — 번호 없는 양식은 괘선 띠 읽기가 필요. 라벨 동의어는 `schema._L` 에 더해야 함(없으면 review 로 남김, 오독은 안 함).
  가로 표 · 한 장 여러 Tag · 세로 괘선 없는 탭 정렬 양식은 시뮬레이션 밖. 게이트 `tests/test_valve_extract_sim.py`(36장 recall ≥ 0.98).

## 28. PDF 주석기 수준의 Mark-up · 가벼운 그리기 층 (valve23, 사용자 요청)

요청: "PDF Annotator 와 같은 주석 마크업 기능 · 동작은 매우 가볍게".

- **도구 15**: 선택 · 사각형 · 구름 · 원 · 형광펜 · **밑줄(U) · 취소선(S) · 물결 밑줄(G)** · 선 · 화살표 · 펜 · 글상자 · 메모 · **스탬프(I)** · **지우개(X)**.
  스탬프: APPROVED · REJECTED · HOLD · CONFIRM · REVISE · CHECKED · AS BUILT · VOID · ✓ ✗ ? ! ★ · 직접 입력(대문자 40자). 누르는 자리에 놓임.
- **색 · 굵기**: 분류 색(Comment 파랑 · Error 빨강 · Missing 주황) 또는 7색 팔레트 · 굵기 4단. 선택한 표시에 바꾸면 그 표시에 적용. `comment.style` JSON {color, width, opacity, size, stamp} — 서버가 검증(hex · 범위 clamp).
- **즐겨찾기 ★**: 지금 도구·색·굵기(·스탬프)를 저장(브라우저, 8개), 누르면 적용, 우클릭 지움. **'바로'** 켜면 의견 창 없이 그려짐(글상자·메모는 항상 묻고, 의견은 Enter 로 나중에).
- **가볍게**: 그리는 중인 표시는 **그 쪽의 작은 임시 SVG** 에만 그리고(`svg.mk-tmp`, rAF 로 한 프레임에 한 번) 끝나면 본 층에 합친다 — 전에는 마우스 이동마다 쪽의 모든 표시를 다시 그렸다. 펜은 1.2 pt 간격 점만 남기고 2차 곡선으로 매끈하게(`penPath`).
  실측(1600×950 · 표시 20여 개 쪽): 펜 300점 드래그 중 프레임 끊김 없음, 표시 추가 1 POST.
- **PDF 내보내기**(`exports._markup`): 밑줄/취소선/물결 → Underline/StrikeOut/Squiggly 주석 · 스탬프 글 → 색 테두리 Square + FreeText(hebo) · ✓ ✗ → Ink(모든 뷰어에서 보이게) · 색·굵기 반영. Acrobat 에서 편집 가능.
- 시험 `tests/test_valve_markup23.py`(스타일 왕복 · 잘못된 색 버림 · 굵기 clamp · 잘못된 kind 400 · PDF 주석 종류).

## 29. 주석 도구 완성 — 타자기 · 말풍선 · 꺾은선 · 다각형 (valve24, 사용자 요청)

- PDF 주석기 도구 목록과 같게: Stamp(DRAFT 추가) · Sticky Note · **Typewriter(Y)** · Text Box · **Callout(B)** · Highlight · Cross Out · Underline · Squiggle · Arrow · Line · Rectangle · Oval · **Polygon Line(O)** · **Polygon(Q)** · Cloud · Pen · Eraser · Select.
- 타자기: 누른 자리에 테두리 없는 글. 말풍선: 가리킬 곳에서 끌어 상자 자리에서 놓음 — 화살표는 상자의 가까운 변에서 나옴(`calloutAttach`, 상자를 옮겨도 따라감).
  꺾은선/다각형: 점마다 누르고 두 번 누르기 또는 Enter 로 끝, Esc 취소 · 그리는 동안 임시 층(rAF).
- PDF 내보내기: Callout = FreeText 의 callout 선 + 열린 화살표 끝(Acrobat 말풍선) · Typewriter = 테두리 없는 FreeText · PolyLine · Polygon 주석.
- 고친 결함 2: ① 화면이 표시의 style 을 받지 않아 모두 분류 색으로 그려짐 ② 그린 직후 선택된 표시가 다음 색 선택에 다시 칠해짐 → 그리기 도구일 때 팔레트는 다음 표시에만, 선택 도구일 때만 선택한 표시에 (스탬프 글은 유지).
  꺾은선의 Enter 가 '선택 표시 고치기' 단축키까지 열던 것도 막음. ui_audit 25/25.

## 30. PDF 에 마크업 · 코멘트 그대로 + 공정 값 출처 문구 (valve25, 사용자 요청)

- 요청: "PDF 출력했을 때 마크업도 그대로, 프로그램이 남긴 코멘트도 PDF 상에" · "공정 값 관련 의견은 Datasheet 상 … 기준 / Ref. Process Data [문서] 기준 … 처럼 어느 문서의 값인지".
- **쪽 옆 코멘트**(`exports._comment_margin`): 지적이 있는 쪽의 mediabox 를 오른쪽으로 250pt 넓혀 번호 · 색 · Issue Type · 칸 · [값] · 설명 · Required · 검토자를
  `insert_htmlbox`(한글 글꼴 대체)로 씀. 넘치면 들어가는 만큼만 쓰고 "… N more on the next page" + 바로 뒤에 같은 크기의 이어지는 쪽(`_comment_page`). 회전된 쪽은 넓히지 않고 이어지는 쪽으로.
- **마크업 고정**: 마지막에 `Document.bake(annots=True, widgets=True)` — 주석이 쪽 내용이 되어 브라우저 · 모바일 뷰어 · 인쇄 어디서나 화면 그대로. `flatten=0` 이면 편집 가능한 주석(Acrobat/Bluebeam).
  화면: 내보내기 선택 창(PDF 일 때)에 두 체크(기억 `LS.pdfopt`) — 모든 Mark-up PDF 내려받기에 `pdfq()` 가 붙는다.
- 글 없는 검토자 표시는 "(see mark-up on the PDF)" 대신 "Stamp 'APPROVED' on the PDF (no comment text)" 처럼 무엇인지 적음(`issues.MARK_NAME`).
- **공정 값 출처**: `matreview.proc_value(F, process_rows, key)` → {v, src, ref, what, label, ev, other}. 그 Tag 의 Process Data 행이 우선(예전과 같은 값 — 실자료 기준값 · 시뮬레이션 불변),
  없으면 데이터시트 자신의 값(숫자 칸만, 'Note 8' · 'TBC' · 'Refer …' 는 값이 아님, 'min / max' 는 큰 값). 문구:
  "Based on Ref. Process Data CO2S-SSG-IN-REQ-00009 (p.54) design temp. 260 °C, seat RTFE exceeds its 230 °C limit (PMS 1C3AS2 Note 018). Revise seat material." /
  "Based on Datasheet fluid phase 'Liquid': state seat design (SPE/DPE) and cavity relief." 같은 문서 값 둘은 `basis_text` 로 한 번만 이름.
  둘이 다르면 긴 설명에 "(datasheet shows … — see Process Mismatch)". 적용: MR-01 · 02 · 03 · 07 · 14 · VR-09 · 10. `process.check` 행에 `pd_doc`.
- Process Mismatch: "Datasheet 'A' vs Process Data 'B' (Ref. Process Data <Doc> p.N)". Data Missing 의 Required: "SOUR WATER (Ref. Process Data <Doc> p.N)".
- 리뷰 캐시: `_ds_full` 버전 튜플에 `VERSION` — 규칙 문구가 바뀐 꾸러미를 올리면 디스크 캐시가 다시 계산된다.
- 결과: 실자료 기준값 불변(`--check`) · diff_sim 불일치 0 · 시뮬레이션 3,000 · 변이 · PDF 190 그대로 · 전체 Mark-up PDF(551쪽, 193쪽에 코멘트 여백) 약 21 s · 4.9 MB.

## 31. 코멘트 말투 — 'Revise' 대신 'shall be reviewed' (valve26, 사용자 요청)

- 설계사가 스스로 다시 검토하도록 한 줄 코멘트의 명령형 'Revise.' · '— correct.' 를 '… shall be reviewed.' 로 바꿈:
  MR-01 "Based on Ref. Process Data <Doc> (p.N) design temp. 260 °C, seat RTFE (limit 230 °C, PMS 1C3AS2 Note 018) shall be reviewed." ·
  MR-02 "… seat X (typ. max. N °C) shall be reviewed or P-T curve submitted." · MR-10 · VR(flange facing · flange standard · actuator type · valve size) · TG-04.
- 판정 · 개수는 그대로(기준값 불변 · 시뮬레이션 3,000 · 변이 재생 통과). 새 규칙의 short 도 이 말투로 쓴다.

## 32. 물 흐르듯 · 글자 줄이기 · Rev B/C/D 자동 이어받기 (valve27, 사용자 요청)

- 요청: ① 끊김 없이 더 가볍게 ② 화면 글자는 핵심만 ③ 수천 번 시뮬레이션으로 엔지니어 의견과 비교해 보완, Rev B·C·D 가 계속 와도 자동 검토 ④ 상업 수준으로.
- **실측부터**(Playwright longtask · CPU 프로파일 · 렌더 트레이스, `/tmp` 스크립트): 서버는 모든 화면 ≤ 63 ms 라 병목이 아니었다. 브라우저에서
  990 DS 사본의 Tag 이동이 74~277 ms(긴 작업 250 ms) — 원인은 Tag 를 바꿀 때마다 984행 Tag 목록을 다시 그리고(`drawTagList` 155 ms) `scrollIntoView` 가 강제 레이아웃(60 ms).
  → `selectTagRow` 로 강조만 옮기고 보이지 않을 때만 스크롤, `tagRow` 한 줄만 다시 그림(`refreshTagRow`), 목록은 chunk 로 그림. **결과 4~19 ms · 긴 작업 0**.
  Valve List 필터 340 ms → `chunkRows` 첫 묶음 250→80행(한 화면) · 행 HTML 을 게으르게 만듦(함수) · `Intl.Collator` 하나로 정렬 → 긴 작업 60~90 ms.
  PDF 쪽 그림은 `decoding="async"` · 다음/이전 Tag 의 데이터시트 JSON 과 첫 두 쪽 그림을 idle 에 미리 받음(`prefetchNeighbours`, 쓰기 요청이 있으면 비움).
- **글자**: 항상 보이던 긴 문장(Process/PMS 표 안내 · 내보내기 카드 · Settings 원칙 · 빈 상태)을 한 줄로 줄이고 설명은 `.hint`(머리 `?`)로 옮김.
- **Rev B/C/D 자동 이어받기**(`app/valve/revisions.py`, 순수 함수 · 서버 훅 `api._carry_over` · 화면): 새 Revision 이 들어오면 규칙 검토는 전과 같이 자동.
  거기에 ① Rev A 에서 Dismissed 한 지적이 **같은 칸 · 값 그대로** 로 다시 나오면 Dismissed 유지(비고 'Carried from Rev A') ② Confirmed(설계사 전달) 였는데 값 그대로 → Confirmed 유지 ·
  `since` 표시 · 문구 앞에 "Not addressed since Rev A:" · Major ③ 사라진 지적 = 해결, 처음 나온 지적 = 새 것 ④ 칸에 단 글 의견은 칸이 안 바뀌었으면 새 판으로 복사(`comment.origin`='Rev A') ·
  자유 그림은 옛 쪽 것이라 복사하지 않음 ⑤ Resolved 는 이어받지 않음(다시 나오면 다시 Open). 감사 기록 'carry' 한 줄(개수).
  화면: 머리 띠 `Rev A→B ✓해결 ✗미반영 +새로` 칩 · Tag 목록 ✗N · 대시보드 Revision Changes 타일에 '미반영 N' · 의견 카드에 'Rev A' 표.
  `issue_state.since` · `comment.origin` 열(이전 DB 자동 추가). 리뷰 캐시 키에 VERSION.
- **시뮬레이션 `spike/valve_rev_sim.py`**: 합성 PDF Rev A → 엔지니어 검토(Dismiss/Confirm/Resolve 무작위) → 설계사 수정 1~4(빈칸 채움 · 값 변경 · 지움 · 같은 재질 다른 표기 · Note) → Rev B → Rev C,
  실제 리더 · compare · issues · revisions 로 돌리고 엔지니어 기대와 비교(compare 정확 · 이어받기 · 해결/미반영/새것 규칙). 60건×2판 1,506 점검 1.000.
  찾은 것: ① `rev_review` 가 Dismissed 였던 지적을 '새것'으로 세던 것(수정) ② 시뮬레이터가 같은 칸을 두 번 고치던 것(시뮬레이터 수정). 1,500건×3판 결과는 아래 기록.
- 실자료: 00XV921 Rev A→B = 해결 5 · 새 3 · 미반영 0(Rev A 에 Confirmed 없음). 기준값 불변.

## 33. Engineering Verification Engine 이 핵심 — 근거 · 검증 보고 (valve28, 사용자 방향)

- 방향(사용자): "Vendor 가 Datasheet 를 내면 오류 · 누락 · 변경 · 사양 위반을 자동으로 찾고 **근거가 표시된** 검토 결과를 만든다. UI 는 엔진의 결과를 엔지니어가 신뢰하고 검증하게 돕는 수단."
- **실측에서 출발**: 실자료 2,887 지적 모두 데이터시트 쪽·칸(100 %)은 있었지만, **맞대어 본 쪽(PMS 쪽 · Process Data 쪽 · 이전 판 값 · 규칙 근거)은 지적 행에 0 %** — 작업대 탭에만 있어서 Issue List · Mark-up PDF 를 받는 사람은 설명만 본다.
- **모든 지적에 증거**(`issues.add(..., evidence, basis, check)`): `evidence` = [{doc, where, page, bbox, text}] 맞대어 본 쪽 · `basis` = 판정 근거(규칙 · 문서) · `check` = 규칙 번호.
  DM-01/02(Process Data 행 · 참조 Note) · OI-01/02(HOLD note) · DE-01~09(맞대어 본 칸 — Line No. · 설계값 · fail position · sheet 1 · note) · PMS-<item>(PMS 쪽 · 요구값) · PD-<item>(Process Data 쪽 · 값) · MR/VR/PC/TG(규칙의 evidence · basis) · REV-01(이전 판 쪽 · 값).
  Issue List Excel 'Evidence' · 'Basis' 열(`exports.ev_text`) · Mark-up PDF 쪽 옆 코멘트에 Evidence 줄 · 작업대 Issues 카드에 '근거: PMS p.12 · Process Data p.54' 링크(`evLink`, 누르면 그 쪽) · Issue List 표 tooltip.
- **검증 보고 `checks.py`**: 48 항목 레지스트리(Datasheet 13 · PMS · Process · Material 12 · Design 14 · Peer · Tag 5 · Revision) 를 데이터시트마다 걷는다.
  fail = 그 번호의 지적(Dismissed 제외) · **n/a = 자료가 없어 판단하지 못함 + 이유**(PMS 없음 · class 가 PMS 에 없음 · Tag 이 Process Data 에 없음 · 설계 온도 없음 · 첫 판 · 동료 없음 · Area/Unit Tag 3개 미만) — 통과로 치지 않는다 · pass = 입력이 있었고 지적 없음.
  작업대 **Checks 탭**(✓/✗/–, ✗ 누르면 그 지적) · 대시보드 'Verification Coverage' 카드(합계 + n/a 이유 상위) · Issue List Excel **'Verification' 시트**(Tag × 48 ✓/✗/– + n/a 이유 표).
  실자료: 164 Tag × 48 = 7,872 · ✓ 6,806 · ✗ 426 · – 640 (첫 판 163 · 설계온도 없음 294 · Process Data 에 없음 98 · API5L-X65 class 없음 60 …).
- 시험 `tests/test_valve_verification.py`(지적마다 check·basis·evidence · Excel 열 · 레지스트리 판정). Revision 시뮬레이션 1,500 × 3판 = 55,223 점검 1.000.
- 다음(엔진 우선): PMS Gasket · Bolting 품목 대조 · Process Data 의 Cv/소음 · Valve List(TBE) 재사용 열에 check 번호 · 규칙마다 '평가 불가' 를 더 세밀히(MR-04 저온 line 없음 등).

## 34. Phase 1 (valve29) — Engineering Feedback Loop · 근거 추적 · 990 DS 성능 (지시서 "Engineering Intelligence Upgrade")

- 계획 · 분석: `docs/valve/PHASE1_PLAN.md`. 보고서 다섯: `docs/valve/valve29/` (IMPLEMENTATION · REGRESSION · RULE_CHANGELOG · PERFORMANCE · USER_GUIDE_UPDATE).
- **결정은 status 옆에**: `issue_state.decision` 등 + `decision_log`(덧붙이기만). 결정 → 기존 status(`store.DECISION_STATUS`) 로 대응해 출력 · 이어받기 · 수 계산은 valve28 그대로.
  Modified 는 출력 문구만 엔지니어 것으로(원문 보관). 사유 분류 7종(Dismissed · N/A · Modified 필수).
- **Rule Performance**(`ruleperf.py`, 통계만) · **규칙 버전 · 출처**(`checks.RULE_VERSION` 전부 1 · `RULE_SOURCE` 전부 General Engineering Check) · **변경 절차**(`rule_change`: 제안 → Tested(Regression+Simulation) → 승인 → Applied 는 코드 버전이 같을 때만).
  판정 코드(extract · schema · material · pms · issues · tbe · matreview · expert · tagrules · process · requirements · checks · revisions · knowledge)는 결정 · 변경 기록 · 설정 · feedback 을 읽지 않는다 — AST 시험.
- **근거 추적**: `datasheet.parser_version`(`extract.PARSER_VERSION`) · 지적의 op · tol · result · 칸 출처 줄 · PDF 빈 곳 → 칸 → 지적.
- **판정 불변 확인 장치** `spike/valve_snapshot_diff.py`: valve28 실자료 지적 2,887건 칸 단위 비교 → 차이 0.
- **성능**(`spike/valve_perf.py` · `valve_perf_screen.cjs`, cold/restart/warm × API · 화면 완료): 측정이 찾은 것과 고친 것 —
  ① Issue List Excel: openpyxl 이 셀마다 새 스타일 객체를 해시 · 행마다 `ws.max_row`/`ws[r]` 재주사 → 스타일 한 번 만들어 복사(`exports._proto`) · 행 번호 직접. 500 DS 105 s → 6 s.
  ② Valve List Excel: 템플릿 스타일 복사를 StyleArray 로 · 시트 끝 · 병합 · S.No. 를 매번 다시 찾지 않음 · 검토가 이미 찾은 특수 요구사항 재사용. 500 DS 28 s → 5.6 s.
  ③ Mark-up PDF: 커지는 출력 문서에 주석을 달 때마다 쪽을 다시 읽어 **2차 증가**(500 DS 182 s) → 데이터시트마다 작은 문서에서 만들어 한 번에 붙임(42 s, 선형).
  ④ 화면 Issue List 가 **최대 6,000행만**(PMS 3,000 · Process 4,000) 보여 주던 결함 → 전부, 쉬는 시간에 나눠 그림 · 행 클릭은 위임.
  ⑤ 지적 목록 API `?compact=1`(화면용: 근거 필드 빼고 데이터시트 공통값은 한 번) 8.2 → 3.5 MB · 인코딩 결과 캐시(이슈 캐시 버전 키).
  위 ①②③ 는 결과가 같은지 셀 · 쪽 단위로 비교했다(값 · 스타일 · 쪽 글자 · 그림 · 주석 · 책갈피).
- **새 창 · 실시간 연동 (사용자 요청 "새창 띄우기 · 새창과 실시간 링크 · 매우 가볍게")**: 같은 브라우저 창끼리 `BroadcastChannel('valve-link')` — 서버 왕복 · 폴링 없음.
  보내는 것: Tag(`ds`) · 칸(`field`) · 지적(`iss`) · 바뀜(`changed`, 쓰기 요청이 성공하면 자동). 받는 창은 '🔗 연동' 이 켜져 있으면 따라가고(Datasheet Review 화면), 바뀜은 250 ms 묶어 그 화면만 다시 읽는다.
  ⧉(PDF 도구줄) = **PDF 만 새 창**(`?pop=pdf` — 목록 · 요약을 읽지 않는 가벼운 창, 0.8 s · JS 10 MB): 메인의 Tag · 칸 · 지적을 따라가고, 거기서 누른 지적 상자 · 칸을 메인에 보낸다.
  머리 '⧉ 새 창' = 지금 화면을 새 창으로(예: 한 창 Issue List, 다른 창 작업대). 되돌이 방지: 남의 메시지를 적용하는 동안(`LINKING`) 보내지 않고, 이미 같은 선택이면 무시.
  점검 `spike/valve_link_check.cjs` (데이터 사본 서버): 메인 → 새 창 Tag · 칸, 새 창 → 메인 지적, 두 번째 창 Issue List → 메인 · 새 창, 두 번째 창의 결정 → 메인 반영 — LINK OK.
- **두 모니터 작업 (사용자 요청 "새 창에서도 마크업 · 반응 매우 빠르게 · 왼쪽 list 오른쪽 새 창")**: PDF 창(`?pop=pdf`)에 작업대와 **같은 Mark-up 함수**(addMark · changeMark · eraseMark · markCmd —
  `W.viewer` 를 PDF 창의 뷰어로) — 같은 대화창 · 되돌리기 · 지우개 · 스탬프. Valve List(행 · 셀) · Issue List · PMS · Process 행을 누르면 `ds`/`field`/`iss` 를 보내고,
  **다음 줄 둘의 데이터시트 · 첫 쪽 그림을 함께 알려 PDF 창이 미리 받는다**(`near`) → 다음 줄로 갈 때 PDF 창 표시 ≈ 0.1 s(측정 중앙 140 ms, Playwright 포함).
  PDF 창의 J/K · ▲▼ → `nav` → 메인 창이 목록이면 다음 줄, 작업대면 다음 Tag. 머리 '⧉ PDF' 로 어느 화면에서나 연다.
- **어디와 다른가 · 코멘트 고치기 · Dense CO2 (사용자 요청)**: ⇆ = `renderCompare` — 왼쪽 데이터시트 칸, 오른쪽 근거 문서 쪽(`refDocOf`: PMS · Process Data · 이전 판 · 같은 데이터시트의 다른 칸), 두 값 · 문서 · 쪽 ·
  올린 날 · **이전 판**(`api._doc_ref`: 같은 종류의 최신 업로드가 기준, 나머지는 earlier). 새 창 `?pop=cmp` 은 `iss`/`ds`/`changed` 를 따라간다.
  ✎ = `PUT /datasheets/{id}/issues-text/{ikey}` {text, expected} → `issue_state.modified_text/modified_expected` — 결정 · status 는 그대로, 원문은 `original_*`, `decision_log` 에 'Edited',
  뒤의 결정 · Rev 이어받기에도 유지. 판정이 아니라 문구만 바뀌므로 지적 스냅샷의 description 은 엔지니어가 고친 것이 나간다(스냅샷 비교는 고치지 않은 사본에서).
  `requirements` 에 `dense_co2`(데이터시트 Note · 칸, General Note 는 'Fluid phase:' 처럼 이 밸브의 상을 말할 때만 — "for dense/supercritical service shall…" 은 조건이라 제외) —
  실자료 45 Tag(Note 9 등). Valve List 'All Valves' 열 · Summary 와 Summary by Area 에 PFP · Fugitive · Fire Safe · Dense Phase CO2 · NACE Tag 수(`tbe.SUMMARY_REQS`).

### 34-1. 특수 요구사항 요약 (valve29, 사용자 요청 "summary 한눈에 · 엑셀 출력")
- 새로 계산하지 않는다 — Valve List Excel 과 같은 `requirements.columns()`(최신 Rev)를 `_req_rows` 가 Area / Unit / Tag 로 묶는다. 그래서 화면 · 이 Excel · Valve List Excel 의 수가 같다(실자료 PFP 42 · Fugitive 162 · Fire Safe 137 · Dense 45 · NACE 155 · SIL 116).
- 'Not Required…' 로 시작하는 칸은 요구 아님. API `GET /projects/{pid}/requirements` · `requirements.xlsx?area=&req=`.

### 34-2. 화면 답 재사용 (valve29, 사용자 요청 "모든 동작이 빠르게")
- `api._cached(name, pid, build)`: 인코딩한 응답을 `(store.WRITES, 최신 audit id, 문서 수·완료 수, 데이터시트 수)` 가 같을 때만 재사용. WRITES 는 이 서버의 모든 commit 마다 +1(`store._Con`), DB 행 값은 다른 프로세스의 쓰기도 잡는다. 계산 중에 쓰기가 있으면 저장하지 않는다.
- Rule Performance 는 날짜도 키(3개월 추세). 서버 시작 warm-up 이 이 답들을 미리 만든다.
- 화면: 필터 · 검색은 행만 다시 그림(G.rowsOnly · IF.L), 클릭 핸들러는 현재 목록(G.rows · IF.L)을 읽음. 쓰기(api 의 GET 아닌 호출) 뒤 미리 받은 목록은 버림(S.wgen).

### 34-3. 입체 화면 · 카드 크게 보기 (valve29, 사용자 선택 시안 A "Soft Depth")
- `body.d3` 아래 CSS 만 — 기능 · 배치 불변. 그림자는 큰 판(카드 · 도구줄 · 표 틀)에만, 표의 행 · 목록 줄에는 넣지 않아 스크롤 비용이 같다(동작 측정 최장 멈춤 변화 없음). 색이 있는 버튼(.on · .pri · 레이어 E/M/R/C · 칩)은 제 색 유지.
- 카드 크게 보기: 카드를 복제해 화면 위에 띄움(뒤 격자는 안 움직임 · 클릭은 문서 위임이라 그대로 동작). Review Status Table 은 큰 화면에서 전체 Tag(`dashTagRows`).
- Settings › 입체 화면 끄기 = `LS.flat`.

### 34-4. Excel 같은 열 필터 (valve29, 사용자 요청 "모든 리스트 화면에")
- 큰 목록(Valve List · Issue List · Special Req. · Process · PMS)은 **데이터를 거른다**(`xfApply(key, rows, cols, redraw)`): 가상 행 · 나눠 그리기여도 모든 행에 즉시. 정렬은 값 종류만 collator 로 정렬 → 순위(정수)로 행 정렬(17k 행 ≈ 20 ms).
- 통째로 그린 작은 표(`table.t`, ≤ 3000행)는 MutationObserver 가 자동으로 ▾ 를 달고(`xfDom`) 행 숨김 · 재배치로 거른다. 큰 목록 표는 `data-xfdata` 로 제외.
- 값 목록은 다른 열 필터에 남은 행에서 센다(Excel 방식). 처음 120개만 바로 그리고 나머지는 잠시 뒤(최대 1,500).
- 990 DS(지적 17,512) 측정: 필터 적용 ≈ 0.2 s · 정렬 ≈ 0.2–0.3 s(JS 25 ms, 나머지는 표 배치) · 열기 0.1–0.25 s. 확인: `spike/valve_filter_check.cjs`.

### 34-5. 가볍게 (valve29, 사용자 요청 "검증하고 가볍게")
- **잰 것**: 화면 DOM 요소 수(990 DS 에서 메뉴를 다 돌면 22만 개) · 첫/재방문 전송량(387 KB 매번) · 서버 RSS(164 DS 286 MB · 990 DS 512 MB, 그중 pymupdf import 125 MB).
- **브라우저**: Process · PMS 표를 가상 행으로(`.vscroll` + 한 줄 셀, 원문은 툴팁) → 990 DS 27k/43k → 600 요소. 메뉴 진입 410/328 → 87/73 ms.
- **전송**: `valve.js?v=<내용 해시>` + `immutable` 1년 캐시(index.html 은 no-store 라 꾸러미가 바뀌면 바로 새 해시). 화면 답(summary · grid · issues · pms · process · requirements · rules · tagging)은 **한 번 gzip 해 두고** ETag 로 304 → 재방문 229 KB → 2 KB.
- **서버 메모리**: 문서별 General Notes 를 한 객체로 공유(`_intern_gn`) · Expert 지적의 kb_text/kb_title 은 캐시에 두지 않고 서빙 때 붙임(`_fat`) · 지적 목록 행이 캐시의 지적 dict 를 그대로 가리킴(복사 없음) · 응답 본문은 gz 로만 보관 · 큰 재계산 뒤 `malloc_trim`. 990 DS 490 → 431 MB(−12 %). 남은 큰 덩어리는 pymupdf import(125 MB, 손 못 댐)와 검토 캐시의 파이썬 객체(84 MB JSON ≈ 200 MB) — 더 줄이려면 압축 JSON 으로 보관하고 필요할 때 풀어야 하는데, 쓰기 뒤 첫 화면이 ~0.7 s 느려져 보류.

### 35. valve30 — 회사 PC 사진 피드백 다섯 (2026-11-02)
- 입체 화면 규칙(`body.d3 #main button…`)이 어두운 `.tbar`(PDF 도구줄 · Mark-up 줄) 버튼까지 흰 버튼으로 덮어 흰 글씨가 안 보였다 → 일반 규칙에서 `:not(.tbar button)`, `.tbar` 는 어두운 버튼.
- Ctrl+휠: `wheel` (passive:false) 에서 ctrlKey 일 때만 막고 rAF 로 모아 `zoomAt(z, x, y)` — 마우스 아래 점이 그 자리에 남도록 scroll 보정. 브라우저 전체 확대는 일어나지 않음.
- 미리보기 화질: `imgZoom` = zoom × 1.3333 × devicePixelRatio × 1.25 를 0.25 단위로 올림(1.5~4). 예전 식은 화면 픽셀과 거의 1:1 이라 글자가 뿌옜다.
- PMS · Process 아래 미리보기: `.hsplit`(높이) · `.vsplit`(좌우) 손잡이, `LS pvh_/pvw_<pane>` 기억. 끄는 동안 `body.dragging` 으로 글자 선택 · 그림 끌림 막음.
- PMS Bore 문구: 판정은 맞음(3C3AS1 3" 일반 볼밸브는 REDUCED PORT 품목뿐, FULL PORT 는 IDBB) — 이유에 품목 코드 · 크기 범위 · 다른 밸브 종류에만 있는 bore 를 적음.

### 36. valve31 — 코멘트 한글 · 영어, 출력 언어 선택 (사용자 요청)
- `app/valve/i18n.py`: 규칙마다 영어 문장 틀이 정해져 있으므로 틀마다 한국어 틀을 둔다(정규식 · 고정 문장 — 기계번역 · LLM 없음). 기술 용어 · 따옴표 값 · 문서 번호는 그대로. 틀에 없는 문장(검토자 글)은 None → 영어만.
- 실자료 프로그램 코멘트 2,891건 전부 한글 있음(누락 0). 시험 `tests/test_valve_i18n.py`: 규칙 문장 75종 + 따옴표 값 보존 + 출력 언어.
- 판정 코드는 i18n 을 모른다: `_ds_deep` 가 issues 계산 뒤 `i18n.attach()` 로 `description_ko` 만 붙임(스냅샷 변경 0). 엔지니어가 고친 문구 · 검토자 코멘트에는 붙이지 않음.
- 출력: `issues.xlsx?lang=` · `markup.pdf?lang=` (en · ko · both). both = 같은 칸에 영어 줄 + 한글 줄(열 구성 그대로). PDF 는 insert_htmlbox / Story 가 한글 글꼴(Droid Sans Fallback)을 스스로 넣는다.
- 화면: `clang`(표시, 기본 both) · `outlang`(출력, 기본 en — 설계사 제출본이 기본 영어) — 출력 창 라디오 · Settings 선택. `download()` 가 두 출력 주소에 lang 을 붙임.

