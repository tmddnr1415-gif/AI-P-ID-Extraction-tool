# 꾸러미 r26 — 적용 검증 (14단계)

`git worktree`(aac64ba → `/tmp/v26`) + `PID_DATA_DIR=/tmp/v26_data` 격리로 회사 PC
조건을 재현하고 **꾸러미를 실제로 풀어** 확인했습니다.  ★ 실 DB(`app/_data/app.db`)는
어느 단계에서도 열지 않았습니다 — 시작·끝 sha256 동일.  드라이버 `spike/verify_r26.py`.

| 단계 | 결과 |
|---|---|
| 1 aac64ba 격리 환경 | ✔ worktree `aac64ba` · `PID_DATA_DIR=/tmp/v26_data` |
| 2 옛 코드로 분석 | ✔ **824행** · 327.5초 · SCOPE `{'(빈칸)': 822, 'SCT': 2}` |
| 3 편집 5칸 | ✔ FIELD 5행 description · 작성자 `검증자` · 저장 5/5 |
| 4 DB 백업 | ✔ ['app.db', 'app.db-shm', 'app.db-wal'] |
| 5 꾸러미 풀기 | ✔ **75파일** · D·R 없음 · **HEAD 와 바이트 동일 (다른 파일 0)** |
| 6 첫 화면 → 열기 | ✔ 프로젝트 1개 · **824행** · **편집 5/5 생존** |
| 7 첫 화면 버튼 | ✔ 결과(1037행) → `#to-home` → `#main` 감춤=True · `#drop` 보임=True |
| 8 새 분석 | ✔ **1037행** · Q'ty **1931** · 지문 **fb85b039** · 693.5초 · 승계 **5/5** |
| 9 발주처 양식 | ✔ **FIELD 885 / MOV 76 / BFV 23** — 실제 xlsx 를 열어 셈 |
| 10 두 축 | ✔ 축1 **99.3% / 70.5%** (FP 249 · FN 4) · 축2 **99.3% / 94.4%** (FP 35 · FN 4) |
| 11 시험 전량 (푼 코드로) | ✔ 빠른 **220 passed, 3 skipped, 40 deselected in 13.75s** · UI **24 passed, 239 deselected in 831.18s (0:13:51)** · slow **16 passed, 247 deselected in 3075.87s (0:51:15)** |
| 12 실 DB sha256 | ✔ `643748dc0efe…` — 시작·끝 **동일** (시험 뒤에도 같음) |
| 13 타이틀블록 못 읽는 PDF | ✔ `TitleBlockUnreadable` · `failed` · 행 **0** · 5.0초 · `stopped_stage = reading title blocks` |
| **14 ★ 8단계 최대 RSS** | **4.95GB** (VmHWM) — r25 의 7.90GB 에서 내려왔습니다 |

## 11단계의 "3 건너뜀"

`tests/test_candidate_intake.py` 세 건 — `out/candidates_nouf1.xlsx`(발주처 문장이
들어 있어 저장소에 없는 파일)가 있는 기계에서만 돕니다.  본 저장소에서는 223 통과.
slow 16 에는 26회차의 TC2 재현율·변이 시험 2건이 들어 있고, worktree 에 `data/` 를
링크해 실제로 돌렸습니다 (꾸러미에는 들어가지 않습니다).

## ⚠ 5단계를 두 번 돌렸습니다

첫 zip 이 마지막 커밋보다 **한 파일 낡아** `tests/test_star_marks.py` 가 HEAD 와
달랐습니다.  다시 만들어 **75파일 · 다른 파일 0** 을 확인했습니다.

## 꾸러미 무결성

| 파일 | 크기 | 파일 수 | sha256 |
|---|---:|---:|---|
| `PID_update_2026-09-10_r26.zip` | 696,181 | 3 | `af8f06548206652a0ab665223bc816e83981348b8741b3189780250d1c00e64c` |
| `3_덮어쓸파일.zip` (안쪽, 이름만 바꿔 STORED) | 691,584 | 75 | `9956c99cc74cee4296ddf335b36f970c287b5cbe95823e8af015e8da7c592510` |

`app\_data\` 검사 세 번 — 목록 · 안쪽 zip · 바깥에서 꺼낸 안쪽, 전부 0건.

## 캡처

| 파일 | md5 |
|---|---|
| `s7_1_home.png` 첫 화면 | `451ab2546800` |
| `s7_2_rows.png` 결과 1037행 | `2aea82a7b521` |
| `s7_3_back.png` 첫 화면 버튼 뒤 | `451ab2546800` |

첫째와 셋째가 같은 것이 통과 조건입니다.
