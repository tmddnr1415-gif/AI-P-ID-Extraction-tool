# Valve Datasheet Review — UI/UX 개선 변경 기록 (valve07, 2026-10-31)

감사 결과(`UI_UX_AUDIT.md`)의 번호(R·D·L·V·M·X·E)를 따라 적는다.  기능 변경 종류: **UI-only** / **기능 추가** / **버그 수정**.

## 1. 수정한 파일

| 파일 | 내용 | 종류 |
|---|---|---|
| `app/static/valve/valve.js` | 작업대 재구성(머리 띠 · 접이식 px 패널 · Tag 목록 · 탭 배지 · 도구줄 한 줄 · Mark-up 줄 접기) · 밸브 부위 그림 · 대시보드 · 목록 키보드 · Revision 동기화 · PMS 안내 · Process 화면/탭 실제 · 내보내기 묶음 · 확인 창 · 상태 · Settings 단축키 | UI + 기능 |
| `app/static/valve/valve.css` | 위 화면들의 스타일(새 클래스만 추가, 기존 선택자 10여 개 조정) | UI-only |
| `app/valve/process.py` | **새 모듈** — Process Data 표 읽기 · 공정 항목 비교(Phase 3 엔진) | 기능 추가 |
| `app/valve/api.py` | Process 문서 파싱 · `_process_for` · `_ds_full` 에 `process` · 요약 KPI `process_mismatch` · `has_process` · `GET /projects/{pid}/process` · `GET /projects/{pid}/revisions.xlsx` · `process_ref` 보정 | 기능 추가 (기존 API 계약 변경 없음 — 응답에 키 추가만) |
| `app/valve/issues.py` | 지적 종류 `Process Mismatch`(주황 · Major) | 기능 추가 |
| `app/valve/exports.py` | Mark-up PDF · Excel 에 `process` 색 · `revisions_xlsx` | 기능 추가 |
| `tests/test_valve.py` | Process 읽기/비교 규칙 · Process API · Revision Excel 시험 (+2 → 38개) | — |
| `docs/valve/UI_UX_AUDIT.md` · `UI_UX_CHANGELOG.md` · `DEVELOPER_GUIDE.md` · `docs/handoff/valve.md` · `docs/history/other_log.md` | 문서 | — |

DB 스키마 · 저장 구조 · 추출(`extract.py`) · 재질 · PMS · TBE 판정 로직: **변경 없음** (평가 지문 `541753c612ed` 그대로 · 차등 시뮬레이션 불일치 0).

## 2. 화면별 개선

### P0 Datasheet Review Workbench (R1~R10)
- **머리 띠**(목표 그림의 상단 요약): Tag · Type · Size · Rating·Class · Body Type · Manufacturer · Revision + Data Error / Missing / PMS / **Process** / Rev Change / Comments 개수 칩(누르면 그 탭) + Review Status + ▲▼ Tag 이동. 좁은 창에서는 Body Type · Manufacturer 를 숨긴다.
- **도구줄 한 줄**(1920 에서 61 → 36 px, 1366 에서 124 → 68 px): 쪽 · 확대 · 폭 · 검색 · **✎ Mark-up(줄 접기, M)** · 표시 레이어 칩 **E M R C** · Rev ◁▷ · ⇩ PDF.
- **패널 접기/펼치기** `[` `]` (세로 레일로 다시 펼침) · **px 한도 끌기**(왼 180~420 · 오른 260~560 · PDF ≥ 480) · 창 크기 변경 때 다시 조임. 첫 실행 기본 폭은 창 크기에서 계산, 1250 px 미만이면 Tag 목록을 접고 시작 → 1366×768 에서 PDF 폭 646 → **835 px**(A4 100 %).
- **Tag 목록** 2줄(Tag + 지적 배지 / Type · Rev · 상태), 'n / N', ▲▼, 선택 띠.
- **탭** 짧은 이름 + 개수 배지(Issues · Process · PMS · Rev · Comments), 1366 에서 3줄 → 2줄. 상태줄 제거(머리 띠로).
- 칸 줄(`.fl`)의 값이 글자 단위로 깨지던 것 수정(상태 pill 을 값 뒤로, 고치기 버튼 22 px).
- **밸브 부위 그림**(사용자 요청): Data 탭 위의 볼밸브 단면 SVG. 칸을 누르면 그 부위(Body · Ball · Seat · Seal · Stem · Packing · Bolting · Flange · Actuator · Spring · SOV · AFR/Tubing · Limit Switch · Pipe · Flow path)가 파랗게, 설명과 값이 아래에. 매핑은 `partOf(key)` 규칙표.
- 겹침·Mark-up 좌표: Viewer 안에서만 계산(바뀌지 않음) · 접기/끌기/창 크기 뒤 `paintOv()` 다시 그림 — 자기검증 22/22.

### P1 Dashboard (D1~D4)
- KPI 10개 **5×2 고정**(1250 px 미만 4열) · 예외 KPI(값 > 0: Revision · Data Error · Missing · PMS · Pending)는 색 테두리 + 숫자 색 · Process Data Mismatch 는 문서가 있을 때 실제 값.
- **KPI 누르면 걸러진 화면**: Data Errors/Missing → Issue List 그 종류, PMS → PMS, Pending/Completed → Review 의 상태 필터, 도넛 범례도 상태 필터.
- 아래 행 4칸(상태 도넛 · **Issues by Category**(요약 API 의 kpi 로, 새 API 없음) · 상태표 · 최근 활동)이 남은 높이를 채움 · 날짜/이름 줄바꿈 없음.

### P2 Valve List · Issue List (L1~L4)
- 고정 열 오른쪽 그림자(`.fzl`) · 스크롤바 보이게 · **↑/↓ 행 이동 + 미리 보기, Enter 로 열기**(두 목록 모두) · 선택 행 고정 열도 강조.

### P3 Revision Comparison (V1~V3)
- **두 PDF 같이 움직이기**(스크롤 비율 · 확대) 토글, 기본 켬 · 예시는 'DEMO DATA' 띠로 명시 · **Revision 비교 Excel**(모든 Tag 의 바뀐 칸 · Summary 시트) 버튼 → `GET /projects/{pid}/revisions.xlsx`.

### P4 PMS Compliance (M1~M2)
- 행을 고르기 전 안내 상태(빈 회색 판 대신) · 결과 칩에 ✖ ? – ✔ 와 설명(Review · Not Defined ≠ 부적합).

### P5 Process Data Verification (X1) — **실제 구현**
- `app/valve/process.py`: 쪽의 세로 괘선으로 열 띠 · 머리 줄 2~3줄 → 열 이름 · 단위 줄 · Sr no. 로 Tag 행. 실자료 Annexure 7: 23표 · 68 Tag · 0.3초.
- 비교는 공정 항목만(유체 · 상 · 운전/설계 압력·온도 · 차압 · 유량 · MW · 밀도 · 점도 · 작동 시간 · Fail 위치 · 기밀 · Line/P&ID). Valve Size · Bore · Rating · Pipe Class · 재질 제외.
- 단위: 차원이 확실할 때만 환산(psi↔bar, °F↔°C, min↔s). 게이지/절대압은 **양쪽에 기준이 적혀 있고 같을 때만** 비교, 아니면 Review Required(대기압 보정 안 함). 불명확하면 Pass/Fail 대신 Review Required. 허용 오차 1 %.
- 결과: Match · **Mismatch(→ 지적 'Process Mismatch', 주황)** · Review Required · Referenced(Datasheet 가 Process DS 를 참조해 비워 둔 칸) · Not in Process Data · Datasheet Blank.
- 실자료: Datasheet 164 중 66 Tag 가 Process Data 에 있음 · Match 215 · **Mismatch 42**(Line No. 32 · P&ID 8 · Fail 위치 2 — 08SDV412A/B 는 Datasheet 'Close' ↔ Process Data 'FO') · Review 2 · Referenced 749.
- 화면: Process 화면(결과 칩 · 항목 · Tag 거르기 · 행 → Datasheet 칸 ↔ Process Data 표 나란히) · Review 의 Process 탭 · 대시보드 KPI · 머리 띠 칩 · Issue List/Excel/Mark-up PDF 에 'Process Mismatch'. 문서가 없으면 'Not Evaluated' (MOCK 제거).

### P6 Reports & Export · Settings (E1~E3)
- 다섯 묶음(① Valve List ② Issue List ③ Mark-up PDF ④ CSV·Revision Excel ⑤ Review Feedback) + 자동 생성 파일.
- **만들기 전 확인 창**(프로젝트 · 파일명 · 범위 · 제외 규칙) → 머리의 상태 줄 ⏳ 만드는 중 / ✔ 완료(파일명 · 시각) / ✖ 실패(사유). 저장 API · 파일 형식 변경 없음.
- Settings: 지금 단축키 표(`[ ]` · M · Mark-up 키 · Ctrl+Z/Y), 초기화 키에 새 설정 추가.

## 3. 테스트 결과

| 명령 | 결과 |
|---|---|
| `pytest -q tests/test_valve.py` | **38 passed**, 1 skipped (실자료 시험은 `VALVE_SAMPLES` 없을 때 건너뜀) |
| `pytest -q` (저장소 전체) | **1,868 passed**, 42 skipped (2분 21초) |
| `spike/valve_eval.py --check` (실자료) | **baseline unchanged** — 지문 541753c612ed · 17,471칸 · 품질 개수 그대로 |
| `spike/valve_diff_sim.py` (실자료) | 140 datasheets · 12,470 cells · **no disagreement** |
| `node spike/valve_ui_audit.cjs` (데이터 사본) | **22/22** (화면 9 · Mark-up 9종 · 옮기기 · 되돌리기/다시 · 지우기/복구 · 지적 연결 · PDF/Excel/피드백) |
| Excel/PDF 내보내기 회귀 | Valve List · Issue List · Mark-up PDF · Feedback 생성 확인(자기검증 + 수동) · 새로 Revision Excel |

## 4. 해상도 검증 (`out/ui_after/<w>x<h>_<screen>.png`, 저장소 밖)

| | 1920×1080 | 1600×900 | 1366×768 |
|---|---|---|---|
| Review PDF 폭 | 950 px (전: 951) | 775 (전: 775) | **835 (전: 646)** — Tag 목록 접힘 기본 |
| Review 도구줄+Mark-up 높이 | 68 px (전: 95) | 68 (전: 95) | **68 (전: 124)** |
| 패널 겹침 · 잘림 | 없음 | 없음 | 없음 (1100 px 까지 px 한도로 조임 확인) |
| 대시보드 | 5×2 · 아래 4칸 채움 | 5×2 | 5×2 · 빈 공간 없음 |
| 모달 | 화면 안 · `min(520px, 92vw)` | 〃 | 〃 |
| embed=1 | 캡처 전부 embed=1 로 찍음 | 〃 | 〃 |

브라우저 확대 90/100/125 % 는 px 한도가 CSS px 기준이라 같은 규칙으로 조여진다(125 % 에서 1366 은 1093 CSS px → 자동 조임 경로, 1100 px 창 검증과 같음).

## 5. 전/후 비교 (바뀐 화면)

`out/ui_before/` ↔ `out/ui_after/` 같은 이름끼리. 바뀐 화면: dash · list(키보드 · 고정 열 그림자) · review(전부) · rev(동기화 · Excel) · proc(실제 엔진) · pms(안내) · export(묶음 · 확인) · settings(단축키). docs 는 그대로.

## 6. 아직 하지 않은 것과 이유

- Process Data 표 중 **Control Valve · PRV 표**는 읽지 않는다(볼밸브 범위 밖, 헤더가 다름). 읽기에 실패한 쪽은 조용히 건너뛰고 `pages` 에 표 수만 적는다 — 새 양식이 오면 `process.read_page` 의 머리 인식을 넓힌다.
- Process Data 의 Excel 판은 보관만(PDF 만 읽음) — 양식 표본이 없어서.
- 받은 PDF 에 이미 들어 있는 설계사 주석(PDF annotation) 읽어 오기 — 다시 읽기와의 중복 처리 설계가 필요해 다음 판으로.
- 'Issues by Category' 의 Open Item 은 kpi 에 있으나 Issue List 거르기 값 'Open Item' 으로만 연결(세부 분리 없음).

## 7. 회사 PC 적용 시 주의

- localStorage 새 키(`wbpx` `wbc` `mkbar` `vpart` `rcsync`) — 예전 `wbw`(%) 는 더 안 쓰지만 지우지 않는다. 이상하면 Settings › 처음대로.
- Process Data PDF 를 Document Management 에 올리면 바로 비교된다(이미 올려 둔 것은 처음 열 때 자동으로 읽음). 대시보드 'Process Data Mismatch' 가 숫자로 바뀐다.
- 1366×768 노트북은 Tag 목록이 접힌 채 시작한다 — `[` 또는 왼쪽 세로 레일로 펼친다.
