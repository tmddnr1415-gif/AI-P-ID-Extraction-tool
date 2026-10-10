# SADARA p7 — 1A46-10LBA10-M05-0002 (STEAM TURBINE 2/3) · 행 25

## ① 눈으로 센 것
PIT 4(SCT 파선 상자) · PIT/TIT(**) 2쌍 · PCV 버블 + 공압 제어 밸브(세로 · `FC`) · NRV(**) 2 · PSV 3 · MOV(M) 5 + 상세 안 2 ·
ESV1/ESV2(ST 공급) · 상세 상자 **둘** — `D : DETAIL … FOR DRAIN 1,2,3,4,5,6`(TIT TIT MOV) · `D : DETAIL … FOR DRAIN 7-12`(LSH LSHH MOV) ·
`DETAIL OF PRESSURE SAFETY VALVE`(글자 캡션 없음) · 본문 `D` 원 표식 + `DRAIN 1~12` 라벨 · `to be deleted` 메모(파랑 FreeText) 4 · 파란 추가분(`DN100`·`DN500` 상자 · 밸브).

## ② 대조
㉠ 25 · ㉡ **1** — PCV 아래 공압 제어 밸브 (행 없음) · ㉢ 0 (`REVIEW` 탭의 `TO BE DELETED` 밸브 5행은 메모를 읽은 결과 — 맞다) ·
㉣ Typical 미적용(상세 두 벌이 DRAIN 12자리에 쓰임) · Q'ty 전부 빈칸(승수).

## ③ 원인
(가) PCV 밸브: 몸체가 **세로 나비를 삼각형 둘로 따로** 그렸다(각 삼각형이 `lll` 칠 + 변 `ll`) — 대각선이 상자를 가로지르지 않아 `_bowtie_bodies` 가 못 잡는다
    (18회차 ANGLE 과 같은 뿌리 — "재는 점" 이 아니라 그리는 방식).  허리 원(5.6) 하나가 `_round_bodies` 로 흘러 **양끝 바를 258·433pt 밖에서 주워
    폭 691·548 의 유령 BUTTERFLY 몸체 둘**을 냈다(액추에이터 NONE 이라 행은 안 됐다).  다이어프램 돔은 몸체 왼쪽에 있다(세로 밸브).
(나) 같은 글자 `D` 캡션 둘 — 38회차 규칙은 `TYPICAL_AMBIGUOUS`.  도면은 캡션이 **열거한 드레인 번호**와 표식 옆 `DRAIN n` 으로 가른다 → **새 종류의 표현**.

## ④ 전수
(가) `body_census.py` (c) 유령 원형 몸체 · (d) 대각선 없이 꼭짓점을 맞댄 삼각형 쌍 — 네 프로젝트 (`3_전수.md`).
(나) 같은 글자 캡션 둘: SADARA p7 (다른 장은 이 회차 표에서).

## ⑤ 보류 — (가)는 몸체 검출기(AL NOUF1 지문 대상) · (나)는 번호 열거 짝 규칙(30분 밖).  둘 다 다음 회차 후보로 `5_미해결.md`.
