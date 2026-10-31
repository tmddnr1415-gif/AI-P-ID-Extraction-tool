# Valve Datasheet 검토 도구 — 개발 설명서

> EPC Instrument Engineering Review Tool · Module 01 (Ball Valve Datasheet)
> 대상 독자: 이 도구를 이어서 고치거나 넓힐 개발자, 회사 PC 에 설치·운영하는 담당자.
> 기준 판: **valve07** (2026-10-31, 브랜치 `ccr-efbe7e75-n915ze`). UI/UX 개선과 Phase 3 의 근거는 `UI_UX_AUDIT.md` · `UI_UX_CHANGELOG.md`.
> 같은 폴더의 `DESIGN.md` 는 "왜 이렇게 만들었나(분석·결정 기록)", 이 문서는 "어떻게 돌아가고 어떻게 고치나(작동 원리·절차)" 입니다.
> 화면 캡처는 고객 자료가 보이므로 저장소에 넣지 않습니다. 캡처를 다시 만드는 법은 §15.4 에 있습니다. 이 문서에서 `[화면 NN]` 은
> 그 캡처 파일 번호(`out/valve_shots/NN_*.png`)입니다.

---

## 목차

1. 한눈에 보기
2. 빠른 시작 (개발 PC · 회사 PC)
3. 구조 — 구성도 · 파일 지도 · 의존성
4. 데이터 — 폴더 · SQLite 표 · 열 추가 이전
5. 처리 흐름 — 업로드에서 자동 내보내기까지
6. 추출 엔진 `extract.py` — 쪽 판정에서 데이터시트 묶기까지
7. 라벨 사전 `schema.py` — 칸 이름 · 지금 값 · 정규화
8. 지적 엔진 `issues.py` — 규칙 · 색 · 번호 · 상태
9. 재질 비교 `material.py`
10. PMS 읽기와 대조 `pms.py`
11. Valve List(TBE) 채우기 `tbe.py`
12. 내보내기 `exports.py` — Issue List Excel · Mark-up PDF
13. 저장소 `store.py` 와 API `api.py` (API 전체 목록)
14. 화면 — 9개 메뉴와 기능별 동작 (캡처 대응표)
15. 품질 도구 — 시험 · 평가 · 지문 게이트 · 차등 시뮬레이션 · 눈 대조 · 화면 자기검증 · 피드백
16. 개발 규칙 — 반드시 지킬 것
17. 넓히는 법 — 새 양식 · 새 칸 · 새 지적 규칙 · 새 화면
18. 배포 — 꾸러미 만들기 · 회사 적용 · 다른 세션과의 병합
19. 문제 해결 (FAQ)
20. 변경 이력과 남은 일

---

## 1. 한눈에 보기

| 항목 | 내용 |
|---|---|
| 무엇 | Valve Datasheet PDF 를 읽어 칸별 값(쪽·위치 포함)을 뽑고, 오류·누락·PMS 부적합·Revision 변경을 찾아 PDF 위에 표시하고, 회사 Valve List(TBE) 양식을 채우고, 설계사에게 보낼 Issue List Excel · Mark-up PDF 를 만든다 |
| 어디서 | 대시보드(8080) **실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve** = P&ID 서버(8000) 의 `/valve/` 를 iframe 으로 [화면 00] |
| 언어 · 의존성 | Python 3.11+ · FastAPI · PyMuPDF(pymupdf) · openpyxl · SQLite (모두 P&ID 서버가 이미 쓰는 것) · 화면은 빌드 없는 순수 JS/CSS |
| 판정 원칙 | 검출에 LLM·OCR 없음. 규칙과 그 도면에서 잰 값만. 도면에 없는 값은 만들지 않는다(빈칸 + 사유). 원본 PDF 는 절대 고치지 않는다. 사람이 고친 값은 원래 읽은 값과 함께 남는다 |
| 정확도 (실자료 456쪽) | 쪽 그림 대조 21,482항목 중 오류 2 (0.009 %, 남은 2건은 도면 자체의 오타 → 지적으로 보고) · TBE 와 비교 가능한 칸 92.9 % 일치(나머지는 실제 차이) |
| 속도 | 456쪽 11~13초 · 데이터시트당 지적 계산 0.6 ms · Mark-up PDF 데이터시트당 0.04초 · 40 KB |
| 코드 크기 | Python 2,764줄(`app/valve/*.py` 8개) · 화면 1,524줄(`app/static/valve/` 3개) · 시험 36개 |

### 1.1 용어

| 용어 | 뜻 |
|---|---|
| 데이터시트(DS) | Tag 하나의 문서 묶음 (Sheet 1 of 2 …). 한 PDF 에 수백 개가 들어 있다 |
| On/Off 양식 (Form 80) | 괘선 칸 + 왼쪽 행 번호 1~61 의 양식 (ESDV · SDV · XV · BDV) |
| Form 102 | MOV(전동밸브) 양식. 두 번호 열(1~52 · 53~100), `Label : value` 형, 값은 굵은 글씨. sheet 2 는 공정 조건표, sheet 3 은 Notes |
| 칸(field) | 행 번호 + 라벨 + 값 + 단위 + 쪽 + 위치(bbox) + 상태 |
| 상태(status) | `ok` · `placeholder`(VTA/HOLD/TBC 등 자리표시) · `blank`(빈칸 = Not Found) · `review`(짝을 확정 못함 — 내부 확인용) |
| 지적(issue) | 규칙이 찾은 문제 하나. 종류 · 색 · 번호 · 쪽 · 위치 · 설명(영문) · 요구값 · 상태 |
| Mark-up | 검토자가 PDF 위에 직접 그린 표시(사각형 · 구름 · 화살표 · 펜 …). 지적과 같은 목록으로 나간다 |
| TBE | Technical Bid Evaluation — 회사의 Valve List 양식(`CO2S-SSG-IN-TBE-00009`). Appendix 시트에 Tag 별 Requirement 행 |
| PMS | Piping Material Specification (`98-98-PI-SPC-00001`). Class 별 Flange Class · NACE · Trim · Ball Valve 품목 |

---

## 2. 빠른 시작

### 2.1 개발 PC (리눅스 · 클라우드 컨테이너)

```bash
# 저장소 루트에서
pip install -r requirements.txt pytest httpx          # P&ID 서버 의존성과 같다
PID_DATA_DIR=/tmp/vt python3 -m uvicorn app.main:app --port 8000
# 브라우저: http://127.0.0.1:8000/valve/?user=홍길동
```

- `PID_DATA_DIR` 를 주지 않으면 P&ID 서버 기본 데이터 폴더를 쓴다. 개발 중에는 **버려도 되는 폴더**를 준다.
- 서버를 끌 때는 `pkill -f "[u]vicorn app.main"` 를 **따로 한 줄로** 친다 (같은 줄에 시작 명령 문자열이 있으면 셸이 같이 죽는다).
- 사용자 이름: 대시보드 iframe 은 `?user=` 로, 직접 열면 Settings 에서 저장(브라우저 localStorage). 서버는 요청 머리 `X-Author` 로 받아 감사 기록에 남긴다.

### 2.2 시험

```bash
pytest -q tests/test_valve.py                   # 36개 · 약 4초 · 고객 자료 없이 도는 합성 PDF 시험
VALVE_SAMPLES=<Datasheet.pdf 폴더> pytest -q tests/test_valve.py -k real   # 실자료가 있을 때만
pytest -q                                       # 저장소 전체 (약 2분)
```

### 2.3 회사 PC

- 회사 PC 는 오프라인 · Windows · Python 3.11. 이 모듈은 **새 패키지를 요구하지 않는다** (P&ID 서버에 이미 있는 것만).
- 설치는 꾸러미 zip(`out/PID_dev+ops_valveNN_<날짜>.zip`) 의 `apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` → 8000 서버 재시작 (§18).
- `.xls` Valve List 는 회사 PC 의 Excel(COM, PowerShell)로 `.xlsx` 로 바꿔 읽는다. Excel 이 없으면 `.xlsx` 로 저장해 올리라고 안내한다.

---

## 3. 구조

### 3.1 구성도

```
 대시보드 (8080, dashboard/server.py, 표준 라이브러리만)
   └ 메뉴 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve
        └ iframe → P&ID 서버 (8000, FastAPI)  /valve/?embed=1&project=CO2 PJT&user=…
                        │
   app/main.py ── include_router(app.valve.api.router)
                        │
   ┌──────────── app/valve/api.py (라우터 · 작업 스레드 · 캐시) ─────────────┐
   │  업로드 → _process 스레드 ─┬ extract.read_pdf → group_datasheets      │
   │                            ├ tbe.analyse (Valve List 양식)            │
   │                            ├ pms.read_pms (PMS PDF)                   │
   │                            └ _auto_export → tbe.build · exports.*     │
   │  조회 → _ds_full ─ issues.compute ─ pms.check ─ material.compare      │
   │  내보내기 → exports.issues_xlsx · exports.markup_pdf · tbe.build      │
   └────────────── store.py (SQLite · 원본 파일 · 감사 기록) ───────────────┘
                        │
   app/static/valve/ index.html · valve.css · valve.js  (9개 화면 SPA · Viewer · Mark-up)
```

### 3.2 파일 지도

| 파일 | 줄 | 하는 일 |
|---|---|---|
| `app/valve/extract.py` | 947 | PDF → 쪽 판정 → 칸/Notes/General Notes → 데이터시트 묶기. 숨은 글자 · 정규화 · 회전 · 암호/손상 |
| `app/valve/schema.py` | 266 | 라벨 사전(On/Off · Form 102), `lookup` · `lookup_102`, `norm_tag` · `norm_label`, `valve_type`, `effective`(지금 값), 단위 · 자리표시 목록 |
| `app/valve/issues.py` | 186 | 지적 규칙 · 색 · 번호 · 검토자 Mark-up 분류 매핑 |
| `app/valve/material.py` | 136 | 재질 표기 → 토큰(규격 · 등급 · 계열), `same` · `equivalent` · `compare` |
| `app/valve/pms.py` | 245 | PMS PDF 읽기(지역 QN/QS · Class 머리 · Ball Valve 품목), `find_class`, `check` |
| `app/valve/requirements.py` | 92 | **특수 요구사항**(valve10) — 칸 · Note · General Note 에서 NACE · Fugitive(ISO 15848) · Fire-safe · PFP · Anti-static · Blow-out · SIL · PST · 경도 · EN 10204 · PMI · 충격시험 · DBB · 도장 · 기밀 을 낱말/규격 번호로 찾고 출처를 단다 |
| `app/valve/matreview.py` | 약 330 | **재질 검토 의견**(valve10) — 규칙 MR-01~15 · 수준 Action/Confirm/Note · 근거 규격/문서 조항 · 증거(칸 · Note · PMS 쪽 · Process Data 쪽) |
| `app/valve/knowledge.py` | 약 230 | **Ball Valve 지식**(valve11) — 표준 · 설계 · 재질 28항목(무엇 · 데이터시트에서 볼 것 · 근거). `GET /api/valve/knowledge` · `python3 -m app.valve.knowledge > docs/valve/BALL_VALVE_KNOWLEDGE.md` |
| `app/valve/expert.py` | 약 300 | **설계 검토 VR-01~15 + 학습 PC-01**(valve11) — 플랜지 · Floating/Trunnion · Fail/스프링 · SIL · 누설 · Fire-safe · 캐비티 · 보온 · Piggable … / 같은 Piping Class 데이터시트 다수 값과 비교 |
| `app/valve/location.py` | 약 70 | **Area · Site · Unit**(valve14) — 제목 NORTH/SOUTH/W15 · 'SYSTEM xx - UNIT yy' = Brownfield · Unit 은 제목 → P&ID → Tag |
| `app/valve/tagrules.py` | 약 170 | **Tag 번호 규칙**(valve15) — 프로젝트 Tag 에서 Area · Site · Unit 별로 배우고(`learn`) 각 Tag 검사(`check` TG-01~05) |
| `app/valve/process.py` | 약 260 | **Phase 3** — Process Data 표 읽기(괘선 열 띠 · 머리 줄 · 단위 줄 · Sr no. 행) · 공정 항목 비교(`compare_item` · `check`) |
| `app/valve/tbe.py` | 476 | 회사 Valve List(TBE) 양식 분석 · 채우기 · 바뀐 칸 표시 · 링크 · `.xls` 변환 |
| `app/valve/exports.py` | 287 | Issue List Excel · 인쇄용 Mark-up PDF(표지 · 쪽 · Issue Summary · 책갈피) |
| `app/valve/store.py` | 211 | SQLite 연결 · 표 · 열 추가 이전 · 원본 저장 · 감사 · 다시 읽기 · Rev 순서 |
| `app/valve/api.py` | 약 1,000 | `/valve/` 화면 · `/api/valve/*` (§13.3) · 작업 스레드 · 지적 캐시 · 자동 내보내기 |
| `app/static/valve/index.html` | 55 | 뼈대(왼쪽 메뉴 9개 · 머리 · 모달 · 토스트) |
| `app/static/valve/valve.css` | 285 | 밝은 테마 · 어두운 PDF 도구줄 · 표 · 겹침 표시 · Mark-up SVG |
| `app/static/valve/valve.js` | 1,184 | 상태 · API · Viewer(쪽 그림 · 겹침 · Mark-up) · 9개 화면 · 단축키 |
| `tests/test_valve.py` | — | 합성 데이터시트(괘선 칸)로 추출 · 비교 · TBE · API · 재질 · PMS · 지적 · 내보내기 · Mark-up · 다시 읽기 · 숨은 글자 시험 |
| `spike/valve_eval.py` | — | 실자료 평가 · 지문 게이트(§15.2) |
| `spike/valve_diff_sim.py` | — | 차등 시뮬레이션(§15.3) |
| `spike/valve_visual_pack.py` · `valve_visual_score.py` | — | 쪽 그림 눈 대조(§15.4) |
| `spike/valve_ui_audit.cjs` | — | 화면 자기검증(§15.5) |
| `spike/valve_voc.py` | — | 검토 피드백 채점(§15.6) |
| `spike/valve_unegg.py` · `valve_xls2xlsx.py` | — | 받은 자료 풀기(EGG 분할 압축) · 시험용 xls 변환 |
| `docs/valve/DESIGN.md` | — | 설계 기록 · 분석 · 결정 · 실측(§1~12) |
| `docs/handoff/valve.md` | — | 다음 세션이 먼저 읽는 한 장 |

### 3.3 의존 방향 (순환 없음)

```
schema ← material ← pms ← issues ← api
schema ← extract ─────────────────┘
schema · material ← tbe ← api
issues ← exports ← api
store ← api
```

`extract` 는 `issues` 를 모른다(읽기와 판정 분리). 판정 모듈(`extract · schema · material · pms · issues · tbe`)은 검토 피드백을 읽지 않는다 — 시험이 AST 로 지킨다(§15.6).

---

## 4. 데이터

### 4.1 폴더 (`{PID_DATA_DIR}/valve/`)

| 경로 | 내용 |
|---|---|
| `valve.db` | SQLite (WAL) — 아래 표 |
| `files/<sha256>.<확장자>` | 올린 원본 — **읽기만**. 같은 파일을 다시 올리면 같은 해시 |
| `pms/<문서id>.json` | 읽은 PMS (처음 쓸 때 만들고 다음부터 재사용) |
| `exports/<프로젝트id>/` | 분석 끝에 자동으로 만든 Valve List · Issue List (`YYYYMMDD_HHMMSS_…`) |
| `cache/` | 쪽 그림 PNG 캐시 |

### 4.2 SQLite 표

| 표 | 열 | 메모 |
|---|---|---|
| `project` | id · name(유일) · created_at | 화면 위 Project 고르기 |
| `document` | id · project_id · kind(`datasheet`/`valvelist`/`process`/`pms`) · filename · sha256 · path · pages · status · error · info(json) · created_at | info 에 문서별 제목 · Rev · General Notes · 스캔 쪽 수 |
| `datasheet` | id · project_id · document_id · tag · tag_key · valve_type · doc_no · rev · rev_date · title · form · pages(json) · notes(json) · rev_history(json) · review_status · created_at · sheets(json) | `tag_key` = 띄어쓰기 · 하이픈을 지운 Tag (`00XV 921` → `00XV921`). `sheets` = `[[쪽, sheet, of], …]` |
| `field` | id · datasheet_id · key · section · display · label · row · value · unit · page · bbox(json) · status · ref(json) · edited_value · edited_by · edited_at | **value 는 읽은 값 그대로, 고친 값은 edited_value** 에 따로. ref = 값이 가리키는 Note · General Note (+해석한 값 · 엉뚱한 Note 경고) |
| `audit` | id · project_id · datasheet_id · field_key · action · before · after · by · at · comment | 모든 쓰기. 지적 캐시의 판 번호로도 쓴다(§13.2) |
| `issue_state` | datasheet_id · ikey · status · note · by · at | 지적 상태(Open/Confirmed/Dismissed/Resolved) — 지적 자체는 저장하지 않고 매번 계산 |
| `comment` | id · datasheet_id · field_key · text · by · at · page · bbox(json) · category · deleted · kind · points(json) | 의견 + Mark-up. kind = rect/cloud/ellipse/highlight/line/arrow/pen/text/note, category = comment/error/missing/question. 지우기는 deleted=1 (되돌리기 가능) |

### 4.3 열 추가 이전 (`store._ADDED`)

예전 `valve.db` 도 그대로 열린다. 열을 더할 때는 `_SCHEMA` 의 CREATE 문은 건드리지 말고 `_ADDED = {"표": [("열", "형식")]}` 에 넣는다.
`connect()` 가 매번 `PRAGMA table_info` 로 없는 열만 `ALTER TABLE ADD COLUMN` 한다.

---

## 5. 처리 흐름

```
[Document Management] 끌어 놓기 (종류: Datasheet / Valve List / Process Data / PMS)
   → POST /api/valve/projects/{pid}/upload (multipart, files[], kind)
       · 저장(sha256) · 같은 해시면 같은 문서 · 암호 PDF 는 건너뛰고 이유를 돌려줌
       · 작업(job) 하나를 만들고 스레드 _process 시작 → 화면은 GET /jobs/{id} 로 진행률
   _process (종류별)
       datasheet  extract.read_pdf(진행률 콜백) → group_datasheets → 데이터시트·칸 저장
                  (같은 파일을 다시 읽으면 store.refresh_datasheet: 읽은 값만 바꾸고 검토 결과는 보존)
       valvelist  .xls → .xlsx (Excel COM) → tbe.analyse_sheet 로 양식 확인
       pms        pms.read_pms → pms/<id>.json
       process    보관만 (Phase 3)
   _auto_export   Valve List(기준 TBE 양식) + Issue List Excel 을 exports/<pid>/ 에 만들고 job["exports"] 에 링크
   → 화면은 작업이 끝나면 두 파일을 자동으로 내려받는다
```

- 실패하면 문서 `status='error'`, `error` 에 사람이 할 일을 적는다("암호를 풀어 저장한 뒤 다시 올려 주세요" 등). 화면의 [재처리].
- 성공한 Datasheet 문서에는 [다시 읽기] — 새 판 읽기 규칙을 예전 업로드에 적용(검토자 수정 · 의견 · Mark-up · 상태 · 필드 id 유지).

---

## 6. 추출 엔진 `extract.py`

입력: PDF 경로. 출력: `{"pages", "sheets": [쪽별 읽기], "other_pages", "docs": {문서번호: {title, rev, general_notes, …}}, "damaged"}`.
`group_datasheets(result)` 가 쪽들을 데이터시트로 묶는다.

### 6.1 쪽 준비 (`read_pdf`)

1. `open_pdf` — 열 수 없음/암호(빈 암호로 열리지 않는 것)는 `PdfError(사람이 할 일)`. 복구된 파일은 `damaged` 로 알림.
2. 회전 쪽은 회전을 풀고 읽은 뒤 상자를 회전 행렬로 되돌린다(`_place`).
3. `_normalised` — A4 와 8 % 이상 크기가 다른 쪽(A3 · A2)은 A4 크기 쪽에 옮겨 그린 뒤 읽고, 상자는 `1/k` 로 되돌린다. 판독 거리(pt)가 어느 용지든 같은 뜻이 되게.
4. 글자 층이 없는 쪽은 `scanned` (OCR 하지 않음 — 화면이 경고).

### 6.2 보이는 글자만 (`_hidden_boxes` · `_visible`) — valve05

PDF 글자 층에는 **사람 눈에 안 보이는 글자**가 섞여 있다: 엑셀 드롭다운 잔재('N/A or other')를 흰 상자로 덮은 것, 'SHEET 1 OF **2**' 의 2 아래 숨은 4,
'NA' 아래 숨은 'Required' 등. 판단은 쪽의 **그리기 순서**로 한다:

- 글자 조각(span)마다 `seqno`(그린 순서)와 상자. 불투명 채움 사각형도 `seqno` 와 상자.
- 글자보다 **나중에** 그려진 불투명 채움이 그 글자의 몸통(글자 높이의 25 % 안쪽)을 완전히 덮으면 숨은 글자.
- 낱말은 "그 자리 · 그 글자를 찍은 조각이 모두 숨은 것"일 때만 버린다 → 숨은 4 위의 보이는 2 는 남는다. 같은 자리에 같은 글자가 겹치면 한 번만.
- 칸 음영처럼 **글자보다 먼저** 그린 채움은 해당 없음. 괘선(글자 높이보다 얇은 채움)은 미리 뺀다(속도).
- 결과는 쪽마다 캐시(`_HIDDEN_CACHE`). PyMuPDF `Rect.contains` 대신 숫자 비교 — 456쪽 35초 → 11초.

### 6.3 줄 묶기 (`_lines` · `_text`) — valve05

"같은 줄" = 낱말의 세로 가운데가 그 줄이 지금까지 차지한 높이 안에 있다. 고정 칸(예전 3 pt 버킷)은 0.9 pt 어긋난 한 줄을 둘로 나눠
'SWAGELOK (General Note - 7)' 을 뒤집었다(P&ID 실패 유형 ④). 줄 안은 x 순서. Notes 의 단락 묶기(`_numbered`)도 같은 함수를 쓴다.

### 6.4 쪽 종류 판정 (`read_page`)

```
번호 열 둘 이상 (_number_columns)               → Form 102 (read_page_102)
번호 열 하나 + 번호 행의 과반이 'Label :' 형   → Form 102 단일 열 sheet (_colon_rows)
행 번호 열(_row_numbers) 없음                   → Notes 전용 쪽? (read_notes_page) 아니면 None
머리에 Unit · Max · Nor · Min                   → 공정 조건표 (read_process_table)
그 밖                                           → On/Off 양식 (괘선 칸)
```

### 6.5 On/Off 양식 (Form 80)

1. **행 번호 열**: 1~99 정수, 오른쪽 끝(x1)이 한 띠에 모이고, 70 % 이상 연속. 행 높이(pitch) = 번호 간격의 중앙값.
2. **세로 괘선**(`_verticals`)과 그 행 높이에서의 x 들(`_xs_at`) → 칸 경계. 이중 괘선 사이의 좁은 틈은 칸이 아니다:
   `DOUBLE_RULE_GAP = 9 pt` — 실측(456쪽): 틈 5~7 pt, 실제 칸 21 pt 이상, 8~20 pt 비어 있음. 평가 도구가 문서마다 다시 재서 빈 띠 밖이면 알린다.
3. **그룹 머리(캡션)**: 번호 열 왼쪽의 가로 괘선 띠(`_horizontals`) — GENERAL · PIPE DATA · PROCESS DATA · VALVE BODY · ACTUATOR · SOLENOID VALVE · ACCESSORIES.
   같은 라벨(Manufacturer 등)이 그룹마다 다른 키가 되게(`act_` · `sov_` 접두).
4. **라벨/값 짝**: 라벨 열(값 열 시작 x 의 왼쪽) 칸들과 값 칸들. 라벨 n 개 = 값 칸 n 개면 순서대로, 라벨 둘이면 왼쪽/오른쪽 반, 빈 예비 행은 건너뜀.
   못 정하면 `review`(내부 확인 — 설계사 목록에는 안 나감).
5. **단위**: 값 칸이 둘로 나뉘고 하나가 단위 낱말(`bar-g` · `ºC` · `psi` …)이면 `value / unit` 으로. 단위 아닌 조각이 둘 이상이면 나누지 않는다.
6. **상태**: 빈칸 = `blank`, 자리표시(VTA · HOLD · TBC · NA · '-' …) = `placeholder`, 나머지 `ok`.
7. **Notes 블록**(sheet 2): 'NOTES' 캡션 아래, **Notes 테두리의 아래 괘선 안쪽만** — 쪽 바닥글('Page 53 of 569')이 마지막 Note 에 붙지 않게(valve05).
   'HOLD:' 같은 대문자 캡션은 새 목록 시작 → 이어지는 '1.' 은 `section="HOLD"` 로 따로.

### 6.6 Form 102 (MOV)

- 두 번호 열(1~52 왼쪽 · 53~100 오른쪽). 값은 **굵은 글씨**, 라벨은 `…:` 로 끝난다. 세로로 쓴 그룹 머리(G E N. · PROCESS …)는 `_stacks`.
- 한 행에 `Label : value  Label : value` 가 둘이면 짝 둘. **오른쪽 열에 번호가 없는 행**(1~4 행 옆 'Instrument Type :' 등)은 왼쪽 행의 짝으로 읽는다(valve05).
- sheet 2(공정 조건표, `read_process_table`): 머리 줄 `Unit | Max | Nor | Min` 의 x 로 열을 나누고 칸마다 `flow.max` 같은 키.
  표 위 머리 행(Tag · PID · Service · Line · Instrument Type …)은 `_colon_pairs` 로 읽는다 — 낱말 사이 간격이 **글자 높이보다 넓으면** 다른 덩어리,
  `:` 로 끝나는 덩어리가 라벨. 단위나 '/' 만 있는 칸(`__ / __ bar-g` 빈 양식)은 빈칸.
- sheet 3(Notes 전용, `read_notes_page`): 'Tag Number :' 옆 Tag · 번호 단락 · 표제란이 아래. 'Sheet | 3 | of | 3' 처럼 칸이 나뉜 표기도 읽는다.

### 6.7 문서 쪽 (표지 · General Notes)

- `Doc. No.:` 다음 줄 = 문서번호, `Doc. Title:` 다음 줄 + **같은 대문자로 이어지는 줄**(두 줄 제목) = 제목.
- `GENERAL NOTES` 이후 번호 단락 → `{번호: 글}`. 반복되는 쪽 머리(COMPANY: · Doc. No.: …) · 'Page N of M' 은 건너뛰고,
  다음 장('N. ATTACHMENT' · 'ATTACHMENT-01')에서 멈춘다.

### 6.8 머리(표제란)

`_header`: DOCUMENT NO. 칸 **바로 아래 인쇄된 번호**(오타 포함 `doc_no_printed`) · SHEET x OF y · REV. · DATE · 제목(가장 큰 글씨) · 개정 이력 줄.
번호가 형식에 맞으면 그것을, 아니면 쪽 전체에서 찾은 번호를 쓴다.

### 6.9 데이터시트 묶기 (`group_datasheets`)

- Tag 가 있는 sheet 가 새 데이터시트를 시작, 뒤 sheet 는 이어 붙인다(같은 문서번호 · 같은 Tag).
- 같은 키가 두 번 나오면: 앞이 비었으면 뒤 값으로, 둘 다 값이 있으면 뒤 것은 `key.행번호`(예: sheet 2 가 반복한 `line_no.4`).
- sheet 의 인쇄된 문서번호가 sheet 1 과 다르면 `sheet_doc_mismatch` (→ 지적).
- 칸 값이 'Note-8' · 'General Note - 3' 이면 `ref` 에 그 Note 글. 순수 참조이고 Note 가 `X: 값` 이나 `… shall be 값` 꼴이면 `ref.value`(해석 값).
  Note 머리글이 칸 라벨과 단어를 하나도 공유하지 않고 다른 Note 머리글이 공유하면 `ref.mismatch` (엉뚱한 Note 참조 — 지적).
- 'For Process data refer to …-PR-DTS-…' 가 Notes/General Notes 에 있으면 `process_ref` — 공정 칸이 일부러 비어 있으므로 '누락'으로 지적하지 않는다.

---

## 7. 라벨 사전 `schema.py`

- `LABELS` (On/Off) · `_L102` (Form 102): 정규화한 라벨 → `(key, section, display)`. 그룹 머리에 따라 접두(`act_` · `sov_`).
- `lookup(label, group)` · `lookup_102(label, group, heading)`. 사전에 없으면 `x.<라벨>` 키로 **버리지 않고** 보관(화면에 보임).
- `norm_tag` · `norm_label` · `valve_type`(Tag 에서 XV/SDV/ESDV/BDV/MOV) · `UNIT_TOKENS` · `PLACEHOLDERS` · `NOT_PROCESS`.
- **`effective(field)` — 칸의 "지금 값"을 정하는 단 하나의 자리**: 검토자가 고친 값 > Note 를 해석한 값 > 읽은 값.
  지적 · PMS · Valve List · 비교가 모두 이것을 쓴다.

---

## 8. 지적 엔진 `issues.py`

`compute(ds, general_notes, pms, area, prev_cmp, states, pms_rows=None, process_rows=None, material_rows=None) -> [issue]`. 규칙만, 근거 칸의 쪽 · 위치를 단다.

| 종류 | 색 | 심각도 | 규칙 |
|---|---|---|---|
| Data Missing | 주황 missing | Major | 필수 칸(REQUIRED 18)이 비어 있음 · **PROCESS DATA 블록의 모든 빈 항목**(section process + Sour Service · Corrosive · Erosive · Toxic · Stroke Time, Max/Nor/Min 은 셋 다 비면 한 건) — Process DS 를 참조해도 지적하고 참조 문서를 적으며, Process Data 에 값이 있으면 그 값을 Required/Expected 로 (valve08, 사용자 요청). 양식에 없는 칸은 지적하지 않음 |
| Open Item | 주황 | **Major** | **모든 칸과 Note** 의 HOLD / TBC / TBA (값 어디에 있어도: 'HOLD (… API 607)' · 'Note-9, Hold-1' → HOLD 목록 항목 글을 붙임 · HOLD 목록 Note). 'TBC - To be Confirmed' 같은 약어 설명 줄은 제외 (valve09, 사용자 요청) |
| Data Error | 빨강 error | Major | Line No. 의 Class ≠ Piping class(기본 Class 비교, '-QG1' 같은 꼬리 무시) · Line No. 의 크기 ≠ Line Size · 운전 > 설계(같은 단위) · Fail position ≠ Air failure 동작 · 문서에 없는 General Note / 데이터시트에 없는 Note 참조 · 엉뚱한 Note 참조 · **sheet 2 표제란 Doc. No. 불일치 · 뒷장이 반복한 Tag/PID/Service/Line 불일치**(valve05) |
| PMS Non-Compliance | 빨강 | Major | `pms.check` → Non-Compliant |
| PMS Review | 빨강 | Minor | `pms.check` → Review Required / Not Defined in PMS |
| Valve Review | 청록 material | Major / Minor | `expert.review` 의 VR(설계) · PC(다른 데이터시트 대비) Action/Confirm (valve11) |
| Material Review | 청록 material | Major / Minor | `matreview.review` 의 Action → Major, Confirm → Minor (Note 는 지적 아님 — Material 탭 · Valve List 열에만). 설명 = 규칙 번호 · 의견 · [Basis: 규격/조항] (valve10) |
| Revision Change | 노랑 revision | Info | 이전 Rev 와 칸 비교(Modified / Added / Deleted, 재질 표기만 다른 것은 Unchanged) |
| Reviewer Correction | 파랑 comment | Major | 검토자가 고친 칸 (읽은 값 → 고친 값) |
| Reviewer Comment | 파랑 | Major / Minor | 의견 · Mark-up(분류 comment / question) |
| (Mark-up error / missing) | 빨강 / 주황 | Major | 분류 Error → Data Error, Missing → Data Missing ('Reviewer: …') |
| Extraction Review | 보라 extract | Internal | 짝을 못 정한 칸 — 설계사 목록 제외 |

- `ikey = "종류:키"` — 상태(issue_state)의 열쇠. 같은 규칙이 다시 계산돼도 상태가 붙는다.
- 번호: 설계사용 지적을 쪽 · 위→아래 · 왼→오른 순으로 1…n, 내부(Extraction Review)는 그 뒤. **화면 · Excel · PDF 가 같은 번호**.
- 설명은 영문(설계사에게 그대로 보냄). 무엇을 무엇과 비교했는지 쓴다: `Class in Line No. '(1C0K8)' differs from Piping class '1C3AS1'`.

---

## 9. 재질 비교 `material.py`

- `tokens(text)`: 대문자 → 구문 접기(`STAINLESS STEEL`→SS, `CARBON STEEL`→CS, `HARD FACED`→HF, `SS316`→SS+316, `CL1500`/`1500#`→1500, `17-4PH`/`TYPE 630`→174PH)
  → 잡음 낱말(ASTM · GR · TYPE · BODY …) 제거 → `A351-CF8M` → A351 + CF8M. 결과는 frozenset, `lru_cache`.
- `FAMILIES`: SS316(316 · 316L · CF8M · CF3M · F316 …) · SS304 · CS · LTCS · DUPLEX · SDUPLEX · PH174 · PTFE · PEEK · GRAPHITE.
- `same(a, b)` — 토큰이 같다(`316 SS / HF` = `SS 316/HF`). `equivalent(a, b)` — 한쪽이 더 자세할 뿐(부분집합, 단 2글자 꼬리 `-A` 나 등급 손실은 아님).
- `compare(required, actual)` → (결과, 영문 이유):
  - 요구 토큰이 모두 있음 → Compliant(표기만 다르면 그렇다고 씀)
  - 등급이 겹치고 규격이 맞음 → Compliant(이중 등급 `316/316L` · `CF8M/CF3M` 양방향). 요구한 HF 등이 없음 → Review
  - 등급이 다른 계열 → **Non-Compliant**. 같은 계열 다른 등급/제품 형태 → Review(엔지니어 판단)
  - 데이터시트가 VTA · Note 참조뿐 → Review("확인할 것이 없음"). PMS 에 값이 없음 → Not Defined in PMS
- 예: `ASTM A351 CF8M` ↔ `316/316L SS A351-CF8M/CF3M` = Compliant · `A351 CF8M` ↔ `A216 WCB` = Non-Compliant · `RTFE` ↔ `PEEK` = Non-Compliant.

---

## 10. PMS `pms.py`

- `read_pms(path)` → `{"areas": {"QN": {class: {...}}, "QS": {...}}}`. 부록 제목 'APPENDIX C … QN AND W15' = QN, 'APPENDIX D … QS' = QS.
- Class 머리: Flange Class · NACE Requirement(`NONE` 은 요구 없음 → None) · Valve Trim · Rating · 머리 쪽과 위치(PMS 화면이 그 자리를 연다).
- Ball Valve 품목(`parse_item`): 품목 코드 줄 + 크기 줄(`0.5 - 1.5` 범위, `2 - 24 / 0.5 - 1` 주관×지관) + 설명(BALL VALVE, FULL BORE, …).
- `find_class(class, area)`: 그 지역에 없으면 다른 지역에서 찾고 "please confirm".
- Class 머리 목록(`header_blocks`, valve10 · `READER_VERSION = 2`): **P-T 표** `pt=[(°C, barg)…]` · `pt_basis`(ASME B16.5 Group) · **Service 목록** · **General Class Notes** `class_notes={'018': 'RPTFE … MAX. TEMPERATURE OF 230°C', …}` · Item Specific Notes.
  옛 판(v1)으로 저장된 PMS json 은 서버가 처음 쓸 때 원본 PDF 에서 다시 읽는다(`api._pms_for`).
- `check(fields, pms, area, notes)`: Pressure Class · NACE(Notes 의 'NACE MR0175' 도 인정) · **Trim/Stem = 고른 Ball Valve 품목의 'X BALL/STEM'**(없을 때만 머리 Trim — valve10: 1A1A 머리 'TRIM 8 (13CR/HF)' 는 Gate/Globe 용이고 Ball 품목은 '316 SS BALL/STEM') · Body/Seat/Fire Safe(크기 · Bore · Floating/Trunnion 으로 고른 품목) · Bore.
  지역은 데이터시트 문서 제목의 NORTH / W15 / SOUTH 로(`area_of_title`), 못 정하면 두 지역 모두 보고 확인 요청(§16 "말하지 않으면 묻는다").

---

## 11. Valve List(TBE) `tbe.py`

- `analyse_sheet`: 회사 양식의 시트마다 머리 줄 · Tag 열 · 'Requirement' 행 · 열 이름을 읽는다(시트 · 열 순서 · 병합 · 서식 · 필터를 그대로 둔다).
- `COLUMNS`: TBE 열 이름 → 데이터시트 칸(들)과 만드는 법(예: 'Stud Bolt Material & Type' 은 Bolting/Gasket Note 에서 Stud 부분만 `_note_part`).
- `build(template, datasheets, docnames, project, link)`:
  - 같은 Tag: **바뀐 칸만** 덮고 노란 칠 + 'Previous: …' 메모. 표기만 같으면(`material.same`) 덮지 않음. 더 자세한 같은 값(`equivalent`)은 목록 값 유지 + 메모
  - 'VTA' · 'General note - 3' 처럼 목록보다 덜 말하는 값은 덮지 않음(메모만)
  - 새 Tag: 밸브 종류 시트 끝에 첫 블록 서식으로 추가(Tool Status = NEW)
  - **Vendor 행(AMPO · OMS · NEWAY …)은 지운다** — Tag 마다 Requirement 한 줄(`_drop_vendor_rows`: 값 · 서식 · 메모 · 행 높이를 한 번에 올리고 병합을 다시 잡음). `build(..., vendor_rows=True)` 면 남긴다 (2026-10-31 사용자 요청)
  - 모든 칸에 출처(파일 · 쪽 · 행) 메모 · 도구로 여는 하이퍼링크 · 오른쪽에 DS Doc No. · Rev. · **Special Requirements (Notes)** · **Material Review (Tool)** · Datasheet Notes · Tool Status 열 · 'Datasheet Notes' 시트
  - Special Requirements = `requirements.summary` ('Fugitive emission ISO 15848-1 — Class A type tested (Gen Note 8) · Passive fire protection (PFP) (Gen Note 26) [datasheet: Not Required — row 23 Fireproofing] · …')
  - Material Review = Action/Confirm 의견 전문(Note 만 있으면 'No action — notes in tool')
  - 기준 양식이 없으면 'Valve List (tool format)' 시트로
- `xls_to_xlsx`: Windows 에서 PowerShell 로 Excel COM 을 불러 변환(회사 PC). 리눅스 개발 PC 는 `spike/valve_xls2xlsx.py`(xlrd)로 시험용 변환.
- `[화면 25]` 미리 보기: 갱신 · 신규 · 변화 없음 · 바뀐 칸 수와 칸별 Previous → New. `[화면 30]` 결과 Excel.

---

## 12. 내보내기 `exports.py`

### 12.1 Issue List Excel `[화면 29]`

- 시트 'Issue List': No. · Tag · Valve Type · Doc. No. · Rev. · Sheet(x of y) · PDF File · PDF Page · Row · Field · Datasheet Value · Issue Type ·
  Description · Required/Expected · Severity · Status · Reviewer Note · **Open in Tool**(도구의 그 칸) · **PDF Page Link**(원본 그 쪽).
- 'Summary by Tag'(Tag 별 종류 개수) · 'Info'(범례 · 출처 파일 · 만든 사람). Dismissed 는 빠진다. 색은 종류별 연한 칠.

### 12.2 Mark-up PDF `[화면 27 · 28]`

- 지적이 있는 데이터시트 쪽만 원본에서 **복사**(원본 불변), 지적마다 색 상자(누락은 연한 칠, Revision 은 형광) + 번호 라벨(같은 색).
- 검토자 Mark-up 은 **같은 종류의 PDF 주석**으로: Square · Square(구름, clouds=2) · Circle · Highlight · Line(화살표는 끝 OpenArrow) · Ink · FreeText(검토자 글 그대로) · Text(스티커).
- 모든 주석에 **인쇄 플래그**(`PDF_ANNOT_IS_PRINT`) — '주석 포함 인쇄'를 몰라도 종이에 나온다. Acrobat · Bluebeam 에서 이어서 고칠 수 있다.
- 데이터시트마다 'Issue Summary' 쪽(번호 · Sheet · 칸 · 값 · 문제 · 요구값), 여러 장이면 표지(Tag 별 개수) · 책갈피.
- `tobytes(garbage=4, deflate=True, use_objstms=1)` — 데이터시트당 40 KB.

---

## 13. 저장소와 API

### 13.1 `store.py`

`connect()`(WAL · 표 만들기 · 열 이전) · `save_original`(sha256) · `insert_datasheet` · `refresh_datasheet`(다시 읽기: 필드 id 유지, edited_* 보존,
읽기에서 사라진 칸은 고친 값이 없을 때만 지움) · `audit` · `rev_key`(A < B < … < 0 < 1 < 2) · `rows` · `one` · `J`/`unJ`(json) · `_LOCK`(쓰기 잠금).

### 13.2 캐시

- 프로젝트 지적 `_ISSUE_CACHE[pid] = (판, 목록)` — 판 = (그 프로젝트 audit 최대 id, 문서 수). 모든 쓰기가 audit 을 남기므로 쓰기 뒤에는 자동으로 다시 계산.
- PMS `_PMS_CACHE[문서id]` · 쪽 그림 PNG 파일 캐시 · 재질 토큰 `lru_cache` · 숨은 글자 쪽 캐시.

### 13.3 API 전체 목록 (`/api/valve`)

| 메서드 | 경로 | 하는 일 |
|---|---|---|
| GET | `/valve/`, `/valve/{name}` | 화면 파일 (index.html · valve.js · valve.css) |
| GET / POST | `/projects` | 프로젝트 목록 / 만들기 `{name}` |
| GET | `/projects/{pid}/summary` | KPI · Tag 목록(문제 수) · 문서 목록 · 최근 활동 |
| POST | `/projects/{pid}/upload` | multipart `files[]`, `kind` → 작업 |
| GET | `/jobs/{jid}` | 진행률 · 메시지 · 경고 · 건너뛴 파일 · 자동 내보내기 링크 |
| POST | `/documents/{doc_id}/retry` | 재처리 / 다시 읽기 |
| GET | `/datasheets/{dsid}` | 데이터시트 전체(칸 · Notes · General Notes · 지적 · PMS 행 · **Process 행 · process_doc · process_ref** · Revision · 의견 · 이력) |
| PUT | `/datasheets/{dsid}/fields/{fid}` | 칸 고치기 `{value, comment}` (읽은 값과 같으면 되돌리기) |
| PUT | `/datasheets/{dsid}/status` | 검토 상태 `{status}` |
| POST | `/datasheets/{dsid}/comments` | 의견 / Mark-up `{text, page, bbox, kind, points, category}` → `new_comment_id` |
| PUT | `/comments/{cid}` | `{delete}` · `{restore}` · `{text?, bbox?, points?, page?, kind?, category?}` |
| GET | `/projects/{pid}/issues` | 프로젝트 지적 (최신 Rev) |
| PUT | `/datasheets/{dsid}/issues/{ikey}` | 지적 상태 `{status, note}` |
| GET | `/compare?prev=&new=` | 두 Rev 칸별 비교 |
| GET | `/documents/{id}/page/{n}.png?zoom=` | 쪽 그림 |
| GET | `/documents/{id}/pageinfo` | 쪽 크기들 |
| GET | `/documents/{id}/search?q=&page=` | 쪽 안 글자 찾기(상자) |
| GET | `/documents/{id}/file` | 원본 PDF (`#page=N`) |
| GET | `/projects/{pid}/grid` | Valve List 화면용 칸 + 쪽 + 상자 |
| POST | `/markup.pdf` | 화면에서 고른 표시로 PDF |
| GET | `/projects/{pid}/valvelist.xlsx` · `/valvelist/preview` | Valve List 만들기 / 바뀔 칸 미리 보기 |
| GET | `/projects/{pid}/pms` | PMS 비교 행 전체 |
| GET | `/projects/{pid}/process` | Process Data 비교 행 전체 (Phase 3) — `process_doc` + rows(결과 · 이유 · DS/PD 쪽 · 상자) |
| GET | `/projects/{pid}/revisions.xlsx` | 모든 Tag 의 Revision 간 바뀐 칸 Excel (`X-Count`) |
| GET | `/projects/{pid}/issues.xlsx` | Issue List Excel (`X-Count` 머리) |
| GET | `/projects/{pid}/markup.pdf?tag=` | 인쇄용 Mark-up PDF (Tag 하나 또는 전체) |
| GET | `/projects/{pid}/exports`, `/exports/{name}` | 자동 내보내기 목록 / 파일 |
| GET | `/projects/{pid}/audit` | 감사 기록 2,000줄 |
| GET | `/projects/{pid}/feedback.json` | 검토 피드백(§15.6) |
| GET | `/projects/{pid}/extracted.csv` | 모든 칸(읽은 값 · 고친 값 · 상태 · 쪽 · 파일) |

오류는 `{"error": "사람이 읽을 말"}` + 400/404. 요청 머리 `X-Author`(URL 인코딩) = 사용자 이름.

---

## 14. 화면

### 14.1 공통

- 왼쪽 메뉴 9개(단축키 1~9), 위 경로 '실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve', 프로젝트 고르기 · 만들기, 사용자.
- `?embed=1` 이면 대시보드 안(바깥 여백 줄임). `?ds=&key=&page=#review` 는 그 데이터시트 · 그 칸을 깜박여 연다(Excel 링크가 이것).
- 상태는 `S`(전역) · `W`(작업대) · `G`(목록) 객체, 사용자 설정은 localStorage(`LS`): 열 너비 · 순서 · 확대 · 탭 · 표시 켜기/끄기 · 분류.
- 모든 화면이 실제 데이터로 동작. Process Data 만 Phase 3 전이라 'Not Evaluated', 예시 화면은 MOCK 버튼으로만(명시 표시).

### 14.2 Viewer (PDF 보기 — 모든 화면 공용)

- 서버가 그린 쪽 PNG(확대에 맞춰 해상도 선택) + 그 위 겹침(`.ov` div: 지적 상자 · 번호 · 찾은 글자 · 고른 칸) + Mark-up SVG(PDF pt 단위 viewBox → 확대해도 정확).
- 도구줄: 쪽 이동 · 확대/축소/폭 맞춤 · PDF 안 찾기 · 표시 켜기/끄기(Error · Missing · Rev · Comment).
- `focus(page, bbox)` 로 그 자리로 스크롤하고 깜박임.

### 14.3 화면별

| 캡처 | 화면 | 기능 |
|---|---|---|
| 00 | 대시보드 메뉴 | 실행 프로젝트 › CO2 PJT › Datasheet › **Ball Valve** — 도구가 오른쪽에 열린 모습 |
| 01 | Dashboard | KPI 10개(Tag · DS · 신규 · Revision 변경 · Data Error · Data Missing · PMS 부적합 · Process 불일치 · 검토 대기 · 완료), 상태 도넛, Tag 상태표, 최근 활동 |
| 02 | Document Management | 종류별 끌어 놓기 칸, 작업 진행 카드(쪽 단위 진행률 · 경고 · 자동 내려받기), 문서 표(상태 · 재처리 · 다시 읽기 · 원본) |
| 03 | Valve List — 표 | 엑셀식 표: 고정 열 · 열 필터 · 정렬 · 너비 조절 · 열 순서 끌기 · 여러 줄 선택(Shift/Ctrl) · 두 번 눌러 고치기 · 상태 일괄 변경 · Excel 내보내기 |
| 04 | Valve List — 칸 → PDF | 칸 하나를 누르면 오른쪽 미리 보기가 **그 쪽 · 그 자리**로 가서 깜박임(실시간 연동) |
| 05 · 06 | Issue List | 지적 목록(종류 · 심각도 · 상태 거르기), 행을 누르면 PDF 그 자리, 상태 바꾸기(이유 입력), Issue List Excel / Mark-up PDF 내보내기 |
| 07 | Datasheet Review — Issues | **머리 띠**(Tag · Type · Size · Rating·Class · Rev + Data Error/Missing/PMS/Process/Rev/Comments 칩 · 상태 · ▲▼) + 3단 작업대: Tag 목록(2줄 · n/N · 접기 `[`) │ PDF(한 줄 도구줄 · 레이어 칩 E M R C · ✎ Mark-up 줄 접기 M) │ 오른쪽 탭(개수 배지 · 접기 `]`). 패널은 px 한도로 끌기, 창 크기 변경 때 다시 조임 |
| 08 | — Summary | Tag 요약 · 종류별 지적 수 · 주요 칸 |
| 09 | — Data | 위에 **Valve Part 그림**(볼밸브 단면 SVG · 칸을 누르면 그 부위가 파랗게 + 설명, 스크롤해도 고정) + 그룹별 칸 표 — 누르면 PDF 그 칸, ✎ 고치기(읽은 값 보존 · 감사) |
| 10 | — Process | Process Data 표와 항목별 비교(Match · Mismatch · Review · Referenced · Not in PD), PD 쪽 열기. 문서가 없으면 Not Evaluated |
| 11 | — PMS | 그 Tag 의 PMS 비교 행(요구값 · DS 값 · 결과 · 이유 · PMS 쪽 열기) |
| 12 | — Notes | 데이터시트 Notes · 문서 General Notes (누르면 PDF 그 자리) |
| 13 | — Comments | 의견 목록(분류 색 · 모양 · 쪽 링크 · 고치기 · 지우기), 새 의견 |
| 14 | — History | 감사 기록(누가 · 언제 · 무엇을 · 전 → 후 · 이유) |
| 15 | 지적 누르기 | 그 상자가 굵게, PDF 가 그 자리로 |
| 16~18 | **Mark-up** | 도구줄(선택 · 사각형 · 구름 · 원 · 형광펜 · 선 · 화살표 · 펜 · 글상자 · 메모 · 분류 · ↶ · ↷ · 의견 · 지우기), 그리고 나면 의견/분류 창, PDF 위 표시와 Comments 목록 |
| 19 | — Revision 탭 | 이전 Rev 대비 바뀐 칸 표 |
| 20 | Revision Comparison | 두 Rev 나란히 — **같이 움직이기**(스크롤 비율 · 확대) 토글, 바뀐 칸 노랑, 종류 거르기, 고른 것만 Mark-up PDF, **Revision 비교 Excel** |
| 21 | Process Data Verification | **실제**: 결과 칩(Mismatch · Review · Match · Referenced · Not in PD · DS blank) · 항목 · Tag 거르기 · 행을 누르면 Datasheet 칸 ↔ Process Data 표 나란히. 문서가 없으면 Not Evaluated |
| 22 · 23 | PMS Compliance | 결과 개수 칩(Non-Compliant · Review · Not Defined · Compliant) · 거르기 · 행을 누르면 아래에 **데이터시트 그 칸 ↔ PMS 그 쪽** 나란히 |
| 24 · 25 | Reports & Export | 다섯 묶음(Valve List · Issue List · Mark-up PDF · CSV + Revision Excel · Review Feedback) · 만들기 전 확인 창(프로젝트 · 파일명 · 범위) · 상태 줄(만드는 중 / 완료 / 실패) · 자동 내보내기 이력 |
| 26 | Settings | 사용자 이름 · 화면 설정 초기화 · 단축키 안내 |

### 14.4 Mark-up (valve03)

- 도구(단축키): 선택 V · 사각형 R(A) · 구름 C · 원 E · 형광펜 H · 선 L · 화살표 W · 펜 P · 글상자 T · 메모 N. Esc = 선택 도구.
- 분류: Comment(파랑) · Error(빨강 → Data Error) · Missing(주황 → Data Missing) · Question(파랑, Minor).
- 선택 도구: 누르면 고르기(점선 테두리 + 손잡이), 끌면 옮기기, 모서리 손잡이로 크기(펜은 획을 비율로), 선 끝 손잡이. Delete 지우기 · Enter 의견/분류 고치기.
- 모든 변경은 즉시 저장(PUT/POST) · 감사 기록. **되돌리기/다시(Ctrl+Z / Ctrl+Y)** 는 반대 요청을 보낸다(만들기 ↔ 지우기/복구, 옮기기 ↔ 이전 상자). 다른 Tag 에서 한 작업은 그 Tag 에서만.
- 저장 모양: `bbox`(PDF pt) + 선/화살표는 `points=[[x,y],[x,y]]`, 펜은 `points=[[[x,y],…], …]`(획 목록, 서버가 5,000점 · 200획으로 제한).
- 구름 테두리는 SVG 호(arc)를 바깥으로 볼록하게 이어 그린다(`cloudPath`), PDF 에서는 `set_border(clouds=2)`.

### 14.5 단축키

| 키 | 동작 |
|---|---|
| 1~9 | 메뉴 |
| [ · ] | (Review) Tag List · Review Panel 접기/펼치기 |
| M | Mark-up 도구 줄 보이기/숨기기 |
| ↑/↓ · Enter | (Valve List · Issue List) 행 이동 · 열기 |
| ↑/↓ · j/k | (Review) 이전/다음 Tag |
| PgUp/PgDn | 쪽 |
| + / - | 확대/축소 |
| / | Tag 찾기 |
| f | PDF 안 찾기 |
| V R C E H L W P T N A | Mark-up 도구 |
| Ctrl+Z / Ctrl+Y | 되돌리기 / 다시 |
| Delete · Enter · Esc | 지우기 · 고치기 · 선택 도구(창 닫기) |

---

## 15. 품질 도구

### 15.1 시험 `tests/test_valve.py` (36개)

합성 데이터시트(`make_pdf` — 괘선 칸 · 연속 행 · ACTUATOR 띠 · Notes)로: 추출 위치·Notes · Rev 순서 · 비교 · TBE 채우기 서식 보존 · API 흐름 ·
재질 13가지 · PMS 합성 Class · 지적 규칙 · 설계사 내보내기(인쇄 플래그) · Note 도우미 · Process 참조 · 등가 · PMS 품목 배치 · A3/손상 PDF ·
Mark-up 9종 API·PDF · 피드백 · 판정 모듈이 피드백을 안 읽음(AST) · 다시 읽기 보존 · 줄 묶기 · `Label : value` 덩어리 · 숨은 글자 · 표제란/반복 머리 지적.

### 15.2 평가와 지문 게이트 `spike/valve_eval.py`

```bash
python3 -W ignore spike/valve_eval.py --ds Datasheet.pdf --tbe TBE.xlsx --pms PMS.pdf            # 보고서 /tmp/valve_eval/report.md
python3 -W ignore spike/valve_eval.py ... --check           # 지문 · 품질 개수가 움직이면 실패 + 바뀐 칸 목록(cells_diff.txt)
python3 -W ignore spike/valve_eval.py ... --save-baseline   # 원인을 칸 단위로 밝힌 뒤에만
```

A 추출(상태별 · 짝 실패 · 사전 밖 라벨 · 문턱 빈 띠 재측정) · B TBE 와 칸별 일치(exact · same · soft · tbe_vta · **misread**(쪽 글자에 TBE 값이 있는데 다르게 읽음) · different) ·
C PMS · D 지적 · E 속도. 기준값 `spike/valve_eval_baseline.json` 은 **개수와 지문만**(지금 `541753c612ed`, 17,471칸). 보고서는 고객 값 — 저장소 밖.

### 15.3 차등 시뮬레이션 `spike/valve_diff_sim.py` (LOGIC L85 방식)

읽은 값을 깨끗한 괘선 양식에 다시 그려 다시 읽는다 → 다르면 값 글자를 다루는 읽기의 약점. 지금 On/Off 140장 12,470칸 불일치 0.

### 15.4 쪽 그림 눈 대조 `spike/valve_visual_pack.py` · `valve_visual_score.py` (valve05)

1. `python3 spike/valve_visual_pack.py --ds <PDF> --out /tmp/vis` — 쪽마다 `pNNN_1.png`/`pNNN_2.png`(위·아래 반, 144 dpi) + `pNNN.txt`(읽은 것).
2. 검토(사람 또는 에이전트): 지시문 `docs/valve/visual_check_instructions.md`. 항목마다 OK/WRONG/FALSE_BLANK/SPURIOUS/MISSING/WRONG_NOTE/HEADER,
   **오류는 PDF 글자 층으로 다시 확인**, 그림과 다르면 그림을 따른다. 결과 `res/pNNN.json`.
3. `python3 spike/valve_visual_score.py /tmp/vis/res` — 오류율 · 종류별 · 라벨별.
4. 고친 뒤에는 새 꾸러미를 만들어 **바뀐 줄만** 다시 판정(지시문 2부).
실적(2026-10-31): 1차 21,482항목 760오류(3.54 %) → 2차 바뀐 1,324줄 오류 0, 남은 2(도면 오타) = 0.009 %. 결과 개수 `spike/valve_visual_result.json`.

캡처 다시 만들기(이 문서의 `[화면 NN]`): 데이터 **사본**으로 서버를 띄우고 Playwright 로 9개 화면 · 탭 · Mark-up · 내보내기를 찍는다(세션 기록의
`/tmp/tools/vguide.cjs` 방식, `out/valve_shots/` 는 `.git/info/exclude` — 고객 값이 보이므로 커밋하지 않는다).

### 15.5 화면 자기검증 `spike/valve_ui_audit.cjs` (LOGIC L84 방식)

데이터 사본으로 서버를 띄우고 `node spike/valve_ui_audit.cjs` — 9개 화면 · Mark-up 9종 그리기 · 옮기기 · 되돌리기/다시 · 지우기/복구 · Issue 연결 ·
PDF/Excel/피드백을 **서버 상태로** 확인, 캡처 저장, 그린 것은 지운다. 22/22.

### 15.6 검토 피드백 `spike/valve_voc.py` (P&ID hotfix82 방식)

회사에서 Reports & Export › Review Feedback(json) — Confirmed/Dismissed(+사유) · 고친 값 · 직접 그린 Error/Missing(= 규칙이 놓친 것).
`python3 spike/valve_voc.py <파일> --ds <같은 PDF>` → 규칙별 맞은 비율 · 잘못 읽은 칸 · 놓친 것 + 지금 코드로 다시 돌린 결과.
참고축(게이트 아님). **판정 코드는 이 파일을 읽지 않는다**(시험이 지킨다) — 정답지를 보고 맞추는 일을 막기 위해.

### 15.7 회차 끝 점검 넷

`pytest -q tests/test_valve.py` · `valve_eval.py --check` · `valve_diff_sim.py`(불일치 0) · `valve_ui_audit.cjs`(22/22). 읽기를 고쳤다면 + 눈 대조(바뀐 줄).

---

## 16. 개발 규칙 — 반드시 지킬 것

1. **판정 값은 그 도면에서 잰다.** 코드에 치수를 박지 않는다. 문턱이 필요하면 분포의 빈 띠에서만(예: `DOUBLE_RULE_GAP`), 아니면 글자 높이처럼 그 쪽의 상대값으로.
2. **도면에 없는 값은 만들지 않는다.** 빈칸 + 사유. 못 정하면 `review` / 'please confirm'.
3. **검출에 LLM · OCR 을 쓰지 않는다.** 측정 정의(분모 · 대조 집합)를 바꿔 수치를 좋게 만들지 않는다.
4. **원본 PDF · 회사 양식은 읽기만.** 내보내기는 복사본. 사람이 고친 값은 읽은 값과 함께.
5. **같은 판정은 한 곳에서** (단일 판정 자리):

   | 판정 | 한 곳 |
   |---|---|
   | 칸의 지금 값 | `schema.effective` |
   | Process 항목 비교 · 단위/기준 규칙 | `process.compare_item` |
   | 재질 같음 · 등가 · 적합 | `material.same` · `equivalent` · `compare` |
   | Tag 같음 · Rev 순서 | `schema.norm_tag` · `store.rev_key` |
   | 지적 종류 → 색 · Mark-up 분류 → 지적 종류 | `issues.COLOR` · `issues.MARK_TYPE` |
   | PMS 지역 | `pms.area_of_title` |
   | 보이는 글자 · 줄 | `extract._visible` · `extract._lines` |
   | 이중 괘선 문턱 | `extract.DOUBLE_RULE_GAP` |

6. **고객 자료는 저장소에 넣지 않는다**: Datasheet · TBE · PMS · Process PDF, 평가 보고서, 눈 대조 그림·판정, 화면 캡처. 저장소에는 개수 · 지문만.
7. **기준값이 움직이면 칸 단위로 원인을 밝힌 뒤에만** 새 기준값을 저장한다(`--check` → `cells_diff.txt`).
8. **없는 것을 만들기 전에 있는 것을 찾는다** — 이미 계산하고 버리는 값이 있는지(P&ID 실패 유형 ①).
9. 사용자에게 보이는 말: 화면 · 안내는 쉬운 한국어, 설계사에게 가는 지적 설명 · Excel 머리는 영어.
10. 저장소 규칙(`CLAUDE.md`): CLAUDE.md 에 회차 기록을 쓰지 않는다 → `docs/history/other_log.md` 끝에 5~15줄, `docs/handoff/valve.md` 의 '지금 상태' 를 고쳐 쓴다.

---

## 17. 넓히는 법

### 17.1 새 데이터시트 양식(다른 벤더 · 다른 밸브)

1. 표본 PDF 를 받아 `spike/valve_visual_pack.py` 로 몇 장 보고, `read_page` 의 판정 순서(§6.4) 중 어디로 가는지 확인.
2. 괘선 칸 양식이면 대개 그대로 읽힌다 — 사전에 없는 라벨은 `x.*` 로 나오니 `schema.LABELS` 에 키를 더한다.
3. 새 배치면 `read_page_<양식>` 을 만들고 판정 조건을 **그 쪽에서 잴 수 있는 특징**으로(번호 열 수 · `Label :` 비율 · 머리 낱말).
4. 시험: 그 배치를 흉내 낸 합성 쪽을 `tests/test_valve.py` 에 · 실자료로 `valve_eval.py`(TBE 가 있으면) · 눈 대조 · `--save-baseline`.

### 17.2 새 칸(라벨) — `schema.LABELS` / `_L102` 에 `정규화 라벨: (key, section, display)`. 필수로 볼 칸이면 `issues.REQUIRED`. TBE 열과 잇는다면 `tbe.COLUMNS`.

### 17.3 새 지적 규칙 — `issues.compute` 안에 `add(종류, 키, 영문 설명, expected=…, f=근거 칸)`. 무엇과 무엇을 비교했는지 설명에 쓴다.
새 종류면 `COLOR` · `CONTRACTOR_TYPES` · 화면 거르기 · `exports` 범례. 실자료에서 몇 건이 나오는지 `valve_eval.py` D 절로 보고, 오탐이면 규칙을 좁힌다.

### 17.4 새 PMS 항목(Gasket · Bolting) — `pms.parse_item` 이 다른 품목 코드도 읽게 하고 `pms.check` 에 행을 더한다. 비교는 반드시 `material.compare`.

### 17.5 Phase 3 Process Data — `app/valve/process.py` 가 한다(valve07). 새 표 양식이 오면 `read_page` 의 머리 인식(`COLUMNS` 구절표)을 넓히고, 비교 항목은 `DS_KEYS`(Process 열 → Datasheet 칸) · `compare_item`(단위 · 기준 규칙)에 더한다. Control Valve · PRV 표는 아직 읽지 않는다.

### 17.5b 새 재질 규칙 — `matreview.review` 안에 `add(규칙번호, 수준, 제목, 칸 키, 영문 의견, 근거 규격/조항, [증거…])`.
규칙은 **필요한 값이 문서에 있을 때만** 낸다. 프로젝트 값(설계온도 · P-T · Class Note)은 문서에서 읽고, 일반 재질 지식(시트 수지 한계 `SEAT_LIMITS` · 본체 최저온도 `BODY_MIN_T`)은 표에 조항과 함께 둔다.
Action 은 문서 한계를 넘을 때만(PMS Note · P-T 표 · B16.34). 조건부 허용은 Confirm, 검토 기록은 Note. 시험 `test_material_review_rules` 에 한 줄 더한다.

### 17.5c 새 설계 규칙 · 지식 — 지식은 `knowledge.KB` 에 항목(title · text · check · ref)을 더하고 문서를 다시 만든다. 규칙은 `expert.review` 에
`add("VR-nn", 수준, 제목, 칸, 설계사용 한 줄(short ≤120자), 긴 의견, "지식 키", [증거…])` — 지식 키가 없으면 시험이 실패한다. 학습 대상 칸은 `expert.PEER_FIELDS`, 문턱은 `PEER_MIN` · `PEER_SHARE`.

### 17.6 새 화면 — `index.html` 메뉴 버튼 + `<section id="v-키">`, `valve.js` 의 `VIEWS` · `RENDER` 에 함수. PDF 가 필요하면 `new Viewer(host, opts)`.
Mark-up 이 필요하면 `opts.tools=true` 와 `onMark` · `onMarkChange` · `onMarkSelect` · `onMarkCmd`.

---

## 18. 배포

### 18.1 꾸러미 (P&ID 서버용 — 이 브랜치에서 만든다)

```bash
python3 spike/pack_delta.py --name valve05 --base 9429f4f \
  --only app/valve/,app/static/valve/,app/main.py,tests/test_valve.py \
  --readme out/valve05/readme_head.txt --ops
# → out/PID_dev+ops_valve05_<날짜>.zip · "기준판에 적용 → 충돌 0" 을 확인 · git add -f 로 커밋
```

- `--only` 는 딱지(`app/_update.json`)와 기준 파일을 건드리지 않는다(PID 세션 hotfix 번호와 섞이지 않게). 기준 `9429f4f` = hotfix131 전달본.
- 각 valve 꾸러미는 hotfix131 기준 **누적** — 최신 하나만 적용하면 된다.
- 대시보드 메뉴는 valve01 의 `dashboard_patches/UPDATE_from_v16.51_VALVE_menu.zip` (그 뒤 바뀐 것 없음).

### 18.2 회사 적용

1. `apply_to_PID_dev.bat` → PID_dev 에서 `http://localhost:8000/valve/` 확인
2. `apply_to_PID_ops.bat` → 운영 폴더 · 8000 서버 재시작
3. (읽기 규칙이 바뀐 판) Document Management › Datasheet PDF [다시 읽기]

### 18.3 다른 세션과의 병합 ★

이 모듈은 공용 파일 두 군데를 건드린다: `app/main.py` 두 줄(PID 세션) · `dashboard/dashboard.html` 메뉴(DASHBOARD 세션).
그쪽이 이 브랜치를 병합하지 않고 다음 꾸러미를 내면 되돌아간다 → "VALVE 브랜치 `ccr-efbe7e75-n915ze` 를 병합한 뒤 꾸러미를 만들어 줘".
`config/release_sources.json` 의 `VALVE` 항목 덕분에 PID 쪽 `pack_delta.py` 가 덜 합쳐졌으면 멈춘다.

---

## 19. 문제 해결 (FAQ)

| 증상 | 원인 · 할 일 |
|---|---|
| 업로드했는데 '암호가 걸린 PDF' | 소유자 암호가 아닌 열기 암호 — Acrobat 에서 암호 없이 저장해 다시 올림 |
| '손상된 파일 — 복구해 읽었지만 N쪽…' | 다운로드가 깨짐 — 원본을 다시 받아 올림 |
| '글자층이 없는 쪽 N장 (스캔본)' | 이 판은 OCR 을 하지 않는다 — 원본(전자 PDF)을 요청 |
| .xls Valve List 가 안 읽힘 | 회사 PC 에 Excel 이 없거나 COM 차단 — Excel 에서 .xlsx 로 저장해 올림 |
| 예전에 올린 PDF 에 새 고침이 안 보임 | Document Management › [다시 읽기] (검토 결과 보존) |
| 지적 숫자가 화면과 Excel 이 다름 | Dismissed 는 Excel 에서 빠진다 · 내부(Extraction Review)는 설계사 목록 제외 |
| PMS 'please confirm' 이 많음 | 데이터시트 제목에서 지역(NORTH/W15/SOUTH)을 못 정함 — 제목 확인 |
| Mark-up 이 안 보임 | PDF 도구줄의 Comment/Error/Missing 표시가 꺼져 있음 |
| Ctrl+Z 가 '다른 Tag 에서 한 작업' | 되돌리기는 그 Tag 를 연 상태에서만 |
| 서버를 껐더니 셸도 같이 꺼짐(개발) | `pkill` 을 시작 명령과 다른 줄에서, 패턴은 `"[u]vicorn app.main"` |
| 평가 `--check` 가 MOVED | `cells_diff.txt` 로 바뀐 칸을 보고 원인을 밝힌 뒤에만 `--save-baseline` |

---

## 20. 변경 이력과 남은 일

| 판 | 날짜 | 내용 |
|---|---|---|
| valve01 | 2026-10-31 | 모듈 시작: 추출(On/Off · Form 102) · Valve List(TBE) 채우기 · Revision 비교 · 9개 화면 · 대시보드 메뉴 |
| valve02 | 〃 | 지적 엔진 · Issue List Excel · 인쇄용 Mark-up PDF · 자동 내보내기 · Excel ↔ PDF 연동 · 실제 PMS · 재질 규격/등급 비교 |
| valve03 | 〃 | 실패 원인 분석(짝 실패 69→1 · 오독 11→0 · 누락 오탐 748→0) · A3/회전/암호/손상 · 성능 · 사용자 Mark-up 10종 · 다시 읽기 |
| valve04 | 〃 | P&ID · LOGIC 원리 차용: 지문 게이트 · 문턱 빈 띠 · 검토 피드백(VOC) · 차등 시뮬레이션 · 화면 자기검증 |
| valve05 | 〃 | 456쪽 전수 눈 대조 3.54 % → 0.009 % (숨은 글자 · 줄 묶기 · Notes 테두리 · Form 102 · 단위만 칸 · 제목/Sheet 표기 · 새 지적 2종) |
| valve06 | 〃 | Valve List Excel 에서 Vendor 행 삭제 |
| valve07 | 〃 | UI/UX 개선(작업대 머리 띠 · 접이식 패널 · 한 줄 도구줄 · 밸브 부위 그림 · 대시보드 · 목록 키보드 · Revision 동기화 · PMS 안내 · 내보내기 확인/상태) + **Phase 3 Process Data 실제 비교** + Revision 비교 Excel |
| valve08 | 〃 | 빈 Process Data 항목 전부 Data Missing (Process DS 참조여도 · 사용자 결정) |
| valve09 | 〃 | HOLD / TBC / TBA 를 모든 칸 · Note 에서 Open Item(Major) |
| valve10 | 〃 | **PMS 검토 점검**(Ball 품목 Trim 우선 · P-T 표 · Service · Class Notes 읽기) · **특수 요구사항 열**(PFP · Fugitive · NACE …) · **재질 검토 엔진 MR-01~15**(Material 탭 · Issue 'Material Review' · Valve List 열) |
| valve11 | 〃 | **Ball Valve 엔지니어 검토**: 지식 28항목(`knowledge.py`) · 설계 규칙 VR-01~15 · 프로젝트 데이터시트 학습 PC-01 · Expert 탭 · Settings › Ball Valve 지식 |
| valve12 | 〃 | 설계사 코멘트 핵심만: 규칙별 `short` 한 줄(≤120자) → Issue List · Mark-up PDF · Valve List, 긴 설명은 Expert 탭 · 다른 지적 문구도 줄임 |
| valve13 | 〃 | 설계사용 출력(Issue List Excel · Mark-up PDF) 전에 Issue Type 선택 창 — 건수 · 전체/끄기/기본 · 선택 기억 (`pickTypes` · `TYPE_KO`) |
| valve14 | 〃 | Area · Site · Unit(`location.py`, 문서 제목 · P&ID) → Issue List Excel 맨 앞 열 · Valve List 'All Valves' 시트와 종류 시트 열 · Excel 필터 |
| valve15 | 〃 | Tag 번호 규칙 학습(`tagrules.py`: Area · Site · Unit 별 접두 출처 · 번호 · 구분 · 계열↔P&ID) · TG-01~05 · Settings › Tag Numbering · All Valves 에 Tag Prefix/Function/Loop No. |
| valve16 | 〃 | 목록 시트 첫 열 No. · Summary 시트(Area · Site · Unit × Issue Type / Valve Type, By Area — `exports.summary_sheet`) |
| valve17 | 〃 | Issue List 시트 Area 순 정렬 · All Valves 에 요구사항 종류별 열(`requirements.columns`, 데이터시트 줄 답 우선 · 세부 · 출처) |

**남은 일**
1. 회사 적용 확인: .xls 자동 변환, 456쪽 처리 시간, 화면 글꼴, Edge 에서 Mark-up · 패널 접기, 내보낸 PDF 를 Acrobat 에서 열기, 1366×768 노트북에서 작업대.
2. Process Data: Control Valve · PRV 표 읽기(범위 밖) · Excel 판 Process Data · PMS Gasket · Bolting.
3. 받은 PDF 에 이미 있는 설계사 주석(PDF annotation) 읽어 오기(다시 읽기와 중복 처리 설계 필요).
4. 회사 검토가 쌓이면 Review Feedback 을 받아 `valve_voc.py` 로 기각 많은 규칙부터 고치기.
