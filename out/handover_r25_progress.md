# 회사 PC 업데이트 꾸러미 r25 — 진행 기록

작성 2026-09-09 · 개발 회차가 아니다 — 포장과 검증. 코드 수정 0줄.

```
기준선 (25회차 후 · spike/baselines_3p.json)
  AL NOUF1  지문 fb85b039 · 행 1037 · Q'ty 1931
            축1 99.3% / 70.5%   ·   축2 (SCT) 99.3% / 94.4%  (FP 35 · FN 4)
            축3 95.0 · 발주처 양식 885 / 76 / 23
            분석 649초 · 최대 RSS 7.85GB   ← 25회차 잉크 인덱스로 올랐다
  TC2       607행 · a94bb2ad · SCOPE SCT 555 / VENDOR 52 · 축3 82.0
            분석 608초 · 최대 RSS 8.86GB
  SADARA    82행 · 0767ba79 · 축3 75.3
  테스트     빠른 219 · UI 24 · slow 14
  회사 PC   aac64ba · 824행 DB · 10~25회차 전부 미반영

  ⚠ 프롬프트의 축3 값(TC2 64.8 · SADARA 74.8)은 23회차 값이다.  24회차가
    TC2 REV 0/60 → 60/60 으로 82.0, SADARA 파라미터 지표로 75.3 이 됐고
    그것이 저장된 기준선이다 (spike/baselines_3p.json · 25회차 하네스 실측 동일).
```

| 단계 | 상태 |
| --- | --- |
| A 메모리 판단 | **답 받음 — 16GB 이상 · HEAD `84f90df` 로 진행** (10~25회차 누적) |
| B 기준선 | **통과** — 세 프로젝트 전 항목 기준선과 같음 (`out/round25/harness_r25.log` · `6_regression_3p.json`) |
| C 목록 | **완료** — A 47 · M 21 · D 0 · R 0 (`out/handover_final.txt`) · `app/_data` 목록·zip 두 시점 0건 |
| D 적용 검증 | **14단계 전부 통과** (`out/round25/verify/README.md`) · 실 DB sha256 불변 · RSS 7.90GB |
| E 산출물 | **완료** — `out/PID_update_2026-09-09_r25.zip` 661,737 B · sha256 `a5c1a29cbb8a3736…` |

## A 메모리 판단 — 사실

**RSS 대조 (같은 하네스 · 같은 기계 · 프로젝트마다 자식 프로세스)**

| 프로젝트 | 24회차 HEAD (`d2d21a3`) | 25회차 HEAD (`84f90df`) | 차 |
| --- | --- | --- | --- |
| AL NOUF1 | 425.7초 · **4.80GB** | 648.9초 · **7.85GB** | +3.05GB · +223초 |
| SADARA | 61.1초 · 0.84GB | 71.5초 · 1.01GB | +0.17GB |
| TC2 | 463.3초 · **7.22GB** | 608.1초 · **8.86GB** | +1.64GB · +145초 |

출처: `out/round24/6_regression_3p.json`(24회차 하네스) ↔ `out/regression_3p.json`(25회차 하네스).

**끄는 설정 — 없다.**  `find_marks` 끝에서 `star_marks` 를 조건 없이 부르고
(`detect_symbols.py:692`), `star_marks` · `star_groups` 안에 config 를 읽는 갈래가
없다.  잉크 인덱스(`pc._ink_index`)는 `star_groups` 가 만든다.  코드 수정 없이는
끌 수 없고 이번 작업은 코드 수정 금지이므로 **"8GB 기계에서 끄고 돌리는 안"은
성립하지 않는다.**  끄면 TC2 별표 71개가 다시 0 이 된다 (25회차 전 상태).

**(b) 의 기준 커밋 — `133746b`.**  25회차 엔진 커밋 `3b16867` 의 부모다.
`d2d21a3`(24회차 [F] 끝) 부터 `133746b` 까지는 `app/` `tests/` `config/` 변경이
**0 파일**(문서 · spike 만)이고, `3b16867` 뒤 `84f90df` 까지도 코드 변경 0 이다.
즉 (b) 는 `133746b` = "24회차 엔진 + §9 문서 + [A] 표" 이고, 24회차 [G] 꾸러미
`PID_update_2026-09-09_r24.zip`(기준 `d2d21a3`)과 코드가 바이트 단위로 같다.

**8GB 기계라면**: AL NOUF1 7.85GB 는 OS 몫을 빼면 스왑을 쓰고, TC2 8.86GB 는
물리 메모리를 넘는다.  16GB 이상이면 둘 다 단독 실행으로 들어간다.

## B 기준선 — 세 프로젝트 (25회차 HEAD `84f90df` · 순차 · 자식 프로세스)

| 프로젝트 | 행 | 지문 | Q'ty | 축1 | 축2 (SCT) | 축3 | 양식 탭 | 초 | 최대 RSS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AL NOUF1 | 1037 | `fb85b039` | 1931 | 99.3 / 70.5 (FP 249 · FN 4) | 99.3 / 94.4 (FP 35 · FN 4) | 95.0 | FIELD 885 · MOV 76 · BFV 23 · PNEUMATIC 53 | 728 | **7.85GB** |
| SADARA | 82 | `0767ba79` | 0 | — | — | 75.3 | — | 78 | 1.01GB |
| TC2 | 607 | `a94bb2ad` | 345 | — | — | 82.0 | SCOPE **SCT 555 / VENDOR 52** | 654 | **8.86GB** |

하네스 판정: `기준선과 같습니다.` (rc 0).  프롬프트 표의 축3 TC2 64.8 · SADARA 74.8 만
23회차 값이고, 저장된 기준선(82.0 · 75.3)과 실측이 같다 — 어긋남이 아니라 표의 드리프트.
초 수는 직전 실측(649 · 608)보다 80초 안팎 길지만 같은 기계 부하 차이이고 RSS 는 소수 둘째
자리까지 같다.

## C 파일 목록 — 기준 `aac64ba..84f90df`

`git diff --name-status` 전체 449 (A 427 · M 22 · D 0 · R 0).  그중 **소스만**
(`app/` `config/` `docs/` `spike/` `tests/` `conftest.py` `CLAUDE.md` `README.md`)
**68파일 — [A] 47 · [M] 21 · [D] 0 · [R] 0.  수동 삭제 목록: 없음.**
`out/` 381개는 회차 산출물이라 담지 않는다.  r24(62파일)보다 6개 늘었다 —
`detect_symbols.py` 는 이미 M 이었고, 새로 `tests/test_star_marks.py` ·
`spike/legend_star.py` · `spike/mark_probe.py` · `spike/mark_shape.py` 등이다.

`app/_data/` 검사 — 목록 시점 0건 · zip 시점 0건 (`spike/pack_handover_r25.py` `forbidden()`),
그리고 zip 이름을 따로 다시 훑어 0건.

`3_FILES_TO_OVERWRITE.zip` 656,060 bytes · sha256 `e71fd12faaf3173ba2e9ee48c7e73c8d7d935645b324ad6322330cca42f869c2`

## D 적용 검증 — 14단계 (전문 `out/round25/verify/README.md`)

2 옛 코드 824행(466.3초) · 3 편집 5 · 5 68파일 HEAD 와 바이트 동일 · 6 824행 편집 5/5 생존 ·
7 결과 → 첫 화면 버튼 · 8 **1037 · 1931 · fb85b039** · 승계 5/5 · 9 **885/76/23**(실제 xlsx) ·
10 축1 99.3/70.5 · 축2 99.3/94.4 · 11 빠른 216+3skip · UI 24 · slow 14 · 12 실 DB 동일 ·
13 `TitleBlockUnreadable` failed 0행 5.0초 · **14 RSS 7.9GB**.

## E 산출물

| 파일 | 크기 | 파일 수 | sha256 |
|---|---:|---:|---|
| `out/PID_update_2026-09-09_r25.zip` | 661,737 | 3 | `a5c1a29cbb8a3736be345169a22ebef18514e50ea29dc60099834aba610ddbe0` |
| 안쪽 `3_덮어쓸파일.zip` | 656,060 | 68 | `e71fd12faaf3173ba2e9ee48c7e73c8d7d935645b324ad6322330cca42f869c2` |

검증에서 발견한 결함: 없음 (14단계 전부 기대값).  적은 것 하나 — 안쪽 zip 이 아니라
검증 도구 쪽: `error_detail_head` 를 400자로 자르니 예외 클래스명이 잘려 보이지 않아
DB 에서 직접 확인했다 (`TitleBlockUnreadable` 맞음).
