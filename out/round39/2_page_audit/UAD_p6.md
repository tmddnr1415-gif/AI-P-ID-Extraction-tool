# UAD p6 — 1A5J-00EKG00-M05-0001 (FUEL GAS 1/5) · 39회차
캡처 `캡처/UAD_p6_원본.png` · `캡처/UAD_p6_오버레이.png` · `캡처/crop_uad_p6_skid_lit.png`(파선 버블) · `캡처/crop_uad_p6_pit_row.png`(실선 버블)
## ① 눈으로 센 것
PIT 4 · TIT 1 · **LIT 7 · PDIT 3** (필터 세퍼레이터 3기 + 드레인 탱크 — 벤더 스키드 안, 파선) · PIA 1 (경보 접미).
## ② 대조 (행 5)
㉠ 5 (PIT 4·TIT 1) · ㉡ **LIT 6 · PDIT 3** (= 미판정 `버블 기하 검증 실패` 9 · 낱말은 SHX 로 읽힌다) + PIA 1(경보 접미 — 30회차 규명·31회차 [C]) · ㉢ 0 · ㉣ 0.
## ③ 원인
스키드 안 계기의 버블은 **파선** 으로 그려져 있다(NOTE 1 `REFER TO VENDOR DRAWING FOR DETAIL WITHIN VENDOR SUPPLIED SKID`).  `find_bubbles` 는 *마주 본 호 캡 둘 + 곧은 옆면* 을 찾는데 파선 캡은 1~5pt 토막이라 캡이 없다.  단계: 검출(`find_bubbles`).  §4 유형: 도면이 말하는 것(파선 = 공급자 범위)을 읽지 않음.
## ④ 전수 (미판정 `버블 기하 검증 실패` · 파선 버블)
UAD **48** (LIT 27 · PDIT 13 · RO 6 · PI 2 — p6 10 · p8 14 · p9 14 · p19 7 · p21 3) · TC2 0 (TC2 의 59 는 `CHEMICAL SUMP PIT` 의 낱말 `PIT` 47 + 밸브 태그 12 — 버블이 아니라 낱말이다, `캡처/crop_tc2_p51_pit.png`) · AL NOUF1 44 는 별개(PIT 15·MOV 8… — 다음 회차 확인) · SADARA 4.
→ 여러 건 · 방법론.
## ⑤ 고침 — 보류 (30분 초과)
파선 캡을 이어 붙여 버블로 세우는 것은 검출기 변경이고 AL NOUF1 게이트가 필요하다.  이 행들은 공급자 범위(VENDOR) 로 나가야 할 행이다(18회차 [B] 전량 담기).  다음 회차 1순위 후보.
