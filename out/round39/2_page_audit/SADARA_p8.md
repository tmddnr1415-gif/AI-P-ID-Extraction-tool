# SADARA p8 — 1A46-10LBA10-M05-0003 (HP STEAM HEADER 1/3) · 행 17

## ① 눈으로 센 것
PIT TIT · PIT PIT TIT TIT · PDIT FIT FE · PIT PIT TIT TIT · 상세 TIT TIT · MOV(M) 2 = 17 ✓ · PCV 2 · TCV 1 · XV(**) 1(파란 클라우드 `XV will be applied instead of manual valve`) ·
PSV 4 · 증기 트랩 `ST` 5(네모 표식) · `D` 원 표식 5(DRAIN 1~5) · 상세 상자 셋 — PSV(글자 없음) · `D : DETAIL OF DRAIN CONFIGURATION`(TIT TIT MOV) · `ST : DETAIL OF STEAM TRAP CONFIGURATION`(밸브·트랩만).
## ② 대조
㉠ 17 · ㉡ **4** — PCV 2 · TCV 1 · XV 1 (전부 다이어프램/`FC` 제어 밸브) · ㉢ 0 · ㉣ Typical 미적용(D ×5 · ST ×5) · Q'ty 빈칸.
## ③ 원인
제어 밸브 몸체가 **삼각형 둘로 따로** 그려져(p7 과 같음) `_bowtie_bodies` 가 못 잡고, 허리 원이 `_round_bodies` 로 흘러 유령 BUTTERFLY(폭 842pt · `[1753,445,1764,1287]`)가 된다.
`ST` 상세는 캡션도 본문 표식도 **네모** — 원만 받는 38회차 규칙 밖.  ST 상세 안에는 계기 행이 없어 Q'ty 에는 안 닿는다(트랩·밸브뿐).
## ④ 전수 → `3_전수.md` (body_census · SADARA: 유령 원형 몸체 8 · 안 덮인 삼각형 쌍 7 · 몸체 겹침 8).
## ⑤ 보류(몸체 검출기) / 수정(Typical 테두리 모양).
