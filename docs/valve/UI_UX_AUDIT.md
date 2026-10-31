# Valve Datasheet Review — UI/UX 감사 (Phase A, valve07 작업 전)

기준: valve06 코드(`app/static/valve/`) · 캡처 31장(`reference_screenshots/`, 1680×960) · 1920×1080 / 1600×900 / 1366×768 로 각 메뉴를 다시 열어 잰 값 · 목표 그림 `UI_Improvement_Proposal.png`.
그림의 값·Tag·기능은 예시이며 실제 코드와 `DEVELOPER_GUIDE.md` 를 기준으로 판단했다.

## 0. 구조 확인 (코드 ↔ 설명서)

| 항목 | 확인 결과 |
|---|---|
| 진입점 | `index.html`(메뉴 9개 · `#views` 안 `section.view` 9개) → `valve.js` 의 `RENDER` 표 → 화면 함수. `go(v)` 가 해시 · localStorage(`view`) 로 화면 유지 |
| 공통 PDF Viewer | `class Viewer` 하나 — 도구줄(`.tbar`) + (옵션) Mark-up 줄(`.mkbar`) + `.stage`. 겹침 `.ov` 는 px(확대 × 1.3333), Mark-up 은 SVG viewBox(PDF pt) |
| API 호출부 | `api(method, path, body)` 하나. 설명서 §13.3 의 31개 경로와 코드 일치 |
| 상태 | `S`(전역) · `W`(작업대) · `G`(목록) · `RC`(Revision) · `IF`(Issue 거르기) · `LS`(localStorage) — 설명서와 일치 |
| CSS | `valve.css` 285줄 한 파일. 변수 `--navy/--blue/--pms/--proc/--rev/--usr`. 화면별 예외 규칙은 인라인 style 이 많다(대시보드 카드 max-height, PMS 화면 전체 레이아웃) |
| 설명서와 다른 점 | 없음(기능 범위). Process Data 는 MOCK 버튼으로만 예시 — 설명서와 같음 |

### 31장 분류 — 동작하는 것 / 정적 표시

| 캡처 | 화면 | 동작 | 정적 · 예시 |
|---|---|---|---|
| 00 | 대시보드 iframe | 메뉴 · 임베드 | — |
| 01 | Dashboard | KPI 10(누르면 이동) · 도넛 · 상태표(누르면 열기) · 최근 활동 | 'Process Data Mismatch' = Phase 3 연결 전 표시 |
| 02 | Document Mgmt | 끌어 놓기 · 작업 진행 · 재처리 · 다시 읽기 · 원본 | — |
| 03~04 | Valve List | 필터 · 정렬 · 너비 · 순서 · 다중 선택 · 편집 · 미리 보기 연동 | — |
| 05~06 | Issue List | 거르기 · 상태 변경 · PDF 연동 · 내보내기 | — |
| 07~15 | Review 탭 9 | 모두 실제 데이터 · 편집 · 상태 | Process 탭 판정 열만 MOCK 버튼 |
| 16~18 | Mark-up | 10종 · 분류 · 되돌리기 · 저장 | — |
| 19~20 | Revision | 실제 비교(두 Rev 가 있을 때) | Rev 가 하나뿐이면 MOCK 버튼 |
| 21 | Process | Datasheet 값 · 쪽은 실제 | 판정은 MOCK 버튼으로만 |
| 22~23 | PMS | 실제 | — |
| 24~26 | Export · Settings | 실제 | — |
| 27~30 | 내보낸 파일 | 실제 | — |

## 1. 해상도 실측 (Datasheet Review)

| 해상도 | PDF stage 폭 | 도구줄 높이 | Mark-up 줄 | 오른쪽 패널 폭 | 비고 |
|---|---|---|---|---|---|
| 1920×1080 | 951 px | **61 px (2줄)** | 34 | 432 | 도구줄이 이미 2줄 |
| 1600×900 | 775 | 61 (2줄) | 34 | 352 | 탭 2줄 |
| 1366×768 | **646** | 61 (2줄) | **63 (2줄)** | 294 | 도구줄+Mark-up 124 px · 탭 3줄 · A4 100 % (793 px) 가 안 들어감 |

## 2. 화면별 문제 (현재 → 문제 → 영향 → 개선안 → 파일/API → 검증)

### P0 Datasheet Review Workbench

| # | 현재 화면 | 문제 | 사용자 영향 | 개선안 | 파일 / API | 검증 |
|---|---|---|---|---|---|---|
| R1 | 도구줄(07) | 쪽 · 확대 · 검색 · 표시 토글 4개(체크박스+라벨) · Rev ◁▷ · Mark-up PDF 가 한 줄에 안 들어가 **2줄**(1920 에서도) | PDF 세로 공간 손실, 1366 에선 도구줄 124 px | 자주 쓰는 순서로 재배치(쪽 · 확대 · 폭 · 검색 · Mark-up 토글 · 표시 레이어 칩 · Rev · PDF). 표시 토글은 색 칩 버튼(E/M/R/C)으로 압축, Mark-up 줄은 접을 수 있게 | `valve.js Viewer`, `valve.css .tbar` | 세 해상도에서 `.tbar` 높이 ≤ 38 px |
| R2 | 왼쪽/오른쪽 패널 | 접기 없음 · 끌기 범위 12~40 %(px 하한 없음) | 1366 에선 PDF 646 px — A4 한 쪽을 100 % 로 못 봄 | 접기/펼치기 버튼(`[` `]`), px 하한·상한(왼 180~420 · 오른 260~560 · 가운데 ≥ 420) | `wbLayout`, `.wb-*` | 접은 뒤 stage 폭 ≥ 1000 px(1366) |
| R3 | 창 크기 변경 | % 저장만, 재계산 없음 | 작은 창에서 패널이 PDF 를 눌러 겹침 가능 | `resize` 때 px 한도로 다시 조임 + 겹침 다시 그림 | `wbLayout` | 1920→1366 축소 후 겹침 없음 |
| R4 | Tag List 항목 | Type · Rev · 상태를 한 줄 small 로, 문제 수 배지는 있으나 뜻 설명 없음, 이전/다음 버튼 없음(키만) | 눈으로 훑기 어려움 | 2줄 구성(Tag + 문제 배지 / Type · Rev · 상태 pill), 머리에 'n / N' 와 ◀ ▶ 버튼, 현재 항목 굵은 띠 | `drawTagList` | 캡처 |
| R5 | 오른쪽 탭 9개 | 294 px 에서 **3줄** | 탭 영역이 콘텐츠를 가림 | 짧은 라벨(Data · Rev …) + 개수 배지 · 2줄 상한, 패딩 축소 | `wbLayout`, `.tabs` | 1366 에서 ≤ 2줄 |
| R6 | 탭 'Datasheet Data' 값 칸 | 38 %/1fr 그리드라 좁은 패널에서 값이 글자 단위로 줄바꿈('N/A or othe r') | 읽기 어려움 | 라벨 열 최소폭 고정, 값 `overflow-wrap:anywhere` 대신 `word-break:normal` + 긴 값은 2줄 | `.fl` | 캡처 |
| R7 | 작업대 머리 | Tag · Rev 는 상태줄(오른쪽 아래)에만 | 지금 보는 Tag 의 Size · Class · Rating · 지적 수를 한눈에 못 봄(목표 그림의 상단 요약) | 작업대 위 한 줄 요약 띠(Tag · Type · Size · Class · Rating · Rev · Data Error/Missing/PMS/Rev 개수 · 검토 상태) — `S.ds` 로 계산, API 추가 없음 | `wbLayout` · `drawRight` | 캡처 |
| R8 | Issue 누르기 | 동작함(bbox 이동 · 강조) | — | 유지 · 선택된 Issue 카드 강조색 통일 | — | 자기검증 스크립트 |
| R9 | 확대/축소 | `.ov` 는 다시 그림, SVG 는 viewBox | 정합 OK | 창 크기 변경 때도 `paintOv()` | `Viewer` | 자기검증(bbox 위치 비교) |
| R10 | 데이터시트의 밸브 부위 | 칸 이름만 있고 어느 부위인지 그림이 없음(사용자 요청) | 비전공자가 Seat/Stem/Packing 위치를 모름 | 볼밸브 단면 SVG + 칸→부위 매핑, 칸을 누르면 그 부위 강조 | `valve.js`(SVG) · `valve.css` | 캡처 |

### P1 Dashboard (01)

| # | 현재 | 문제 | 영향 | 개선안 | 파일 | 검증 |
|---|---|---|---|---|---|---|
| D1 | KPI `auto-fit minmax(118px)` | 1366 에서 9+1 로 **고아 카드** | 어색한 빈 줄 | 5열 고정(≥1200) · 작은 창 3~4열, 예외 KPI(값>0: Rev · Error · Missing · PMS · Pending)는 색 테두리 + 숫자 색 | `renderDash`, `.kpis` | 세 해상도 캡처 |
| D2 | 아래 3칸 `330px 1fr 1fr`, 카드 max-height 330 | 화면 아래 **빈 공간**(1366 에서 70 px, 1920 에서 400 px) | 정보 밀도 낮음 | 아래 행을 남은 높이에 맞춤, 'Issues by Category' 카드 추가(요약 API 의 kpi 로, 새 API 없음) | `renderDash`, `.dashrow` | 캡처 |
| D3 | Recent Activity | Date · By 열이 글자 단위로 줄바꿈 | 읽기 어려움 | `white-space:nowrap`, 날짜 짧게 | `renderDash` | 캡처 |
| D4 | KPI 클릭 | Data Errors → Issue List 로 가나 종류 필터는 안 걸림 | 한 번 더 걸러야 함 | Data Errors/Missing → Issue List 의 Type 필터, Pending/Completed → Review 상태 필터 | `renderDash` · `IF` · `W.st` | 눌러 확인 |

### P2 Valve List · Issue List (03~06)

| # | 현재 | 문제 | 영향 | 개선안 | 파일 | 검증 |
|---|---|---|---|---|---|---|
| L1 | 고정 열(체크 · # · Tag) | 고정 열 경계가 안 보임, 가로 스크롤 존재가 불명확 | 열이 잘린 줄 모름 | 고정 열 오른쪽 그림자, 스크롤바 보이게 | `.xg` | 캡처 |
| L2 | 긴 값 | nowrap + ellipsis(행 높이 OK), 전체 값은 title 로만 | 값 비교 어려움 | 셀 더블클릭 편집 외에 hover 툴팁 유지 + 셀 선택 시 아래 미리 보기 cap 에 값 전체 | `renderList` | 눌러 확인 |
| L3 | 키보드 | 행 이동 키 없음 | 마우스 필수 | ↑/↓ 로 선택 이동 + 미리 보기, Enter 로 Review 열기 | `renderList` | 눌러 확인 |
| L4 | Issue List 거르기 | Type · Severity · Status · 검색 있음 | — | 유지, 선택 행 강조 통일, 행 ↑/↓ | `renderIssues` | — |

### P3 Revision Comparison (20)

| # | 현재 | 문제 | 영향 | 개선안 | 파일 | 검증 |
|---|---|---|---|---|---|---|
| V1 | 두 Viewer | 쪽·확대가 따로 움직임 | 같은 자리를 맞추기 번거로움 | 'Sync' 토글(기본 켬): 한쪽 스크롤·확대 → 다른 쪽 비율로 | `renderRev` · `Viewer.opts.onScroll` | 눌러 확인 |
| V2 | 변경 없음 안내 | Rev 하나뿐이면 MOCK 버튼 | 예시가 실제처럼 보일 위험 | 'DEMO DATA' 띠 명시 + 예시 행 배경 구분 | `renderRev` | 캡처 |
| V3 | 선택한 변경만 PDF | HL 체크 → Export 됨 | — | 유지 | — | — |

### P4 PMS Compliance (22~23)

| # | 현재 | 문제 | 영향 | 개선안 | 파일 | 검증 |
|---|---|---|---|---|---|---|
| M1 | 아래 두 Viewer | 행을 고르기 전에는 **빈 회색 판** | 무엇을 하라는지 모름 | 안내 상태("표의 행을 누르면 Datasheet 칸과 PMS 쪽이 여기 나란히 열립니다") | `renderPms` | 캡처 |
| M2 | 결과 색 | Review Required(주황) · Not Defined(회색) · Non-Compliant(빨강) 구분됨 | — | 유지 + 칩에 아이콘 글자(✖ · ? · – · ✔) | `renderPms`, `.p-*` | 캡처 |

### P5 Process Data (21)

| # | 현재 | 문제 | 영향 | 개선안 |
|---|---|---|---|---|
| X1 | MOCK 버튼 · 'Phase 3 연결 전' | 예시 판정이 실제처럼 보일 수 있음 | 오판 | 'Not Evaluated' 기본, 예시는 'DEMO DATA' 띠로 시각 구분. 실제 엔진은 `process_ref` 가 가리키는 문서와 Tag 를 잇고 공정 항목만 비교(이번 작업 §P5 참조) |

### P6 Reports & Export · Settings (24~26)

| # | 현재 | 문제 | 영향 | 개선안 | 파일 |
|---|---|---|---|---|---|
| E1 | 카드 4개에 버튼 흩어짐 | 종류별 묶음이 약함 | 찾기 어려움 | Valve List / Issue List / Mark-up PDF / CSV / Audit·Feedback 으로 묶음 | `renderExport` |
| E2 | 내려받기 | 누르면 바로 생성, 범위 확인 없음 | 전체 Mark-up PDF(1분)를 실수로 | 확인 창(파일명 · 프로젝트 · Tag 범위 · 제외되는 Dismissed 수) → 진행 · 성공 · 실패 상태 줄 | `renderExport` · `download` |
| E3 | Settings 단축키 표 | 'A 주석 상자' 등 옛 설명 | 혼동 | 지금 단축키(V R C E H L W P T N · Ctrl+Z/Y · [ ]) | `renderSettings` |

## 3. 기능 버그 vs 디자인 문제 (분리)

- **기능 버그**: 없음이 확인됨(모든 버튼 동작 · 자기검증 22/22). Settings 의 단축키 표가 옛 설명(E3)인 것은 문서 오류.
- **디자인 문제**: R1~R7, D1~D4, L1~L3, V1~V2, M1, E1~E2.

## 4. 위험

- 겹침(`.ov`)과 Mark-up(SVG) 좌표는 Viewer 안에서만 계산 → 레이아웃 변경이 좌표에 영향을 주지 않는다. 다만 접기/펼치기 뒤 `paintOv()` 를 불러 다시 그려야 한다.
- localStorage 키(`wbw` · `zoom` · `wtab` · `ovshow2` · `gorder` · `gw` · `mkcat`)는 그대로 둔다. 새 키: `wbc`(패널 접힘).
- API · DB · 추출 · 판정은 손대지 않는다(P5 실제 엔진은 별도 모듈 + 새 조회 API 로만).
