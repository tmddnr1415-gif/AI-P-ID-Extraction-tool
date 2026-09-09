# 꾸러미 r25 — 적용 검증 (14단계)

`git worktree`(aac64ba → `/tmp/v25`) + `PID_DATA_DIR=/tmp/v25_data` 격리로 회사 PC
조건을 재현하고, **꾸러미를 실제로 풀어** 확인했습니다.  ★ 실 DB(`app/_data/app.db`)는
어느 단계에서도 열지 않았습니다 — 시작·끝 sha256 동일 (`643748dc0efe…`).
드라이버 `spike/verify_r25.py` · 코드 수정 0줄.

| 단계 | 결과 |
|---|---|
| 1 aac64ba 격리 환경 | ✔ worktree `aac64ba` · `PID_DATA_DIR=/tmp/v25_data` |
| 2 옛 코드로 분석 | ✔ **824행** · 466.3초 · SCOPE `{'(빈칸)': 822, 'SCT': 2}` (회사 PC 조건 — SCOPE 없는 DB) |
| 3 편집 5칸 | ✔ FIELD 5행의 description · 작성자 `검증자` · 저장 5/5 |
| 4 DB 백업 | ✔ ['app.db', 'app.db-shm', 'app.db-wal'] |
| 5 꾸러미 풀기 | ✔ **68파일** · D·R 없음 · **푼 파일이 HEAD 와 바이트 동일 (다른 파일 0)** |
| 6 첫 화면 → 열기 | ✔ 프로젝트 1개 · **824행** · **편집 5/5 생존** |
| 7 첫 화면 버튼 | ✔ 눌러서 결과(1037행) → `#to-home` → `#main` 감춤=True · `#drop` 보임=True |
| 8 새 분석 | ✔ **1037행** · Q'ty **1931** · 지문 **fb85b039** · 713.3초 · 편집 **5/5 승계** |
| 9 발주처 양식 | ✔ **FIELD 885 / MOV 76 / BFV 23** — 서버가 만든 **실제 xlsx 를 열어 셈** |
| 10 두 축 | ✔ 축1 **99.3% / 70.5%** (FP 249 · FN 4) · 축2 **99.3% / 94.4%** (FP 35 · FN 4) |
| 11 시험 전량 (푼 코드로) | ✔ 빠른 **216 passed, 3 skipped** (17.6초) · UI **24 passed, 233 deselected in 862.07s (0:14:22)** · slow **14 passed, 243 deselected in 2818.43s (0:46:58)** |
| 12 실 DB sha256 | ✔ `643748dc0efe…` — 시작·끝 **동일** (시험 뒤에도 같음) |
| 13 타이틀블록 못 읽는 PDF | ✔ `app.pipeline.TitleBlockUnreadable` · `failed` · 행 **0** · 5.0초 · `stopped_stage = reading title blocks` · `ValueError` 아님 |
| **14 ★ 8단계 최대 RSS** | **7.9GB** (uvicorn 프로세스 `/proc/<pid>/status` VmHWM — 분석은 그 프로세스의 스레드) |

## 11단계의 "3 건너뜀"

`tests/test_candidate_intake.py` 세 건 — `out/candidates_nouf1.xlsx`(발주처 문장이
들어 있어 저장소에 없는 파일)가 있는 기계에서만 도는 시험입니다.  같은 코드가 본
저장소에서는 219 통과입니다.  UI 24 는 `PID_UI_DB=out/round25/ui.db`(SCOPE 있는 데이터,
24회차 것을 복사)로, slow 14 는 `data/` 를 worktree 에 링크해 돌렸습니다 — 둘 다
꾸러미에는 들어가지 않습니다.

## 14단계 — README 에 적은 값

8단계(이 꾸러미를 푼 코드로 AL NOUF1 58장)의 프로세스 최고 RSS **7.9GB**.
하네스(자식 프로세스 · `ru_maxrss`)의 7.85GB 와 0.05GB 차이 — 서버 프로세스가 화면
응답까지 들고 있어서입니다.  24회차 HEAD 는 같은 하네스에서 4.80GB 였습니다.

## 13단계

이력 괘선 간격 2.0pt 짜리 합성 PDF(A1 12장)를 올렸습니다.
사유 첫 줄: `이 PDF 의 12장 어디에서도 도면번호를 읽지 못했습니다. 도면번호 칸의 자리를 [1950.0, 1560.0, 2384.0, 1600.0] 로 보고 있는데 종이 안이지만 비어 있습니다 (이 문서의 쪽 크기: 238…`

## 꾸러미 무결성

| 파일 | 크기 | 파일 수 | sha256 |
|---|---:|---:|---|
| `PID_update_2026-09-09_r25.zip` | 661,737 | 3 | `a5c1a29cbb8a3736be345169a22ebef18514e50ea29dc60099834aba610ddbe0` |
| `3_덮어쓸파일.zip` (안쪽 = `3_FILES_TO_OVERWRITE.zip`, 이름만 바꿔 STORED 로 담음) | 656,060 | 68 | `e71fd12faaf3173ba2e9ee48c7e73c8d7d935645b324ad6322330cca42f869c2` |

안쪽 zip 은 **재압축하지 않았습니다** — 바깥 zip 에서 꺼낸 바이트가 원본과 같음을 확인했습니다.
`app\_data\` 검사 세 번 — 목록 시점 · 안쪽 zip 이름 · 바깥 zip 에서 꺼낸 안쪽 이름, 전부 0건.

## 캡처

| 파일 | md5 |
|---|---|
| `s7_1_home.png` 첫 화면 | `d03361d2a118` |
| `s7_2_rows.png` 결과 1037행 | `7c808a1cf9f1` |
| `s7_3_back.png` 첫 화면 버튼 뒤 | `d03361d2a118` |

첫째와 셋째가 같은 것이 통과 조건입니다 (첫 화면으로 정확히 돌아왔다).
