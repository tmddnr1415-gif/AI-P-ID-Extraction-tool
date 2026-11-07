# TC2 범례 — 정답지의 판정 기준 (46회차 [E-1])

문서 `data/TC2_260821.pdf` · TAICHUNG CCPP PHASE II · 범례 4장
(p2 `D02J-00GEN00-M05-0002` ~ p5 `…-0005`) · 렌더 `캡처/legend_p2~5.png`.

**이 문서에 없는 형상은 "범례에 없음" 으로 적는다.  눈에 밸브로 보인다는 것은
판정 근거가 아니다** (43·41회차가 그렇게 두 번 틀렸다).

## p2 — 기기 · 배관 · 라인 밸브 · 밸브 상태 · 기타

### LINE VALVES (몸체)
GATE · GLOBE · ANGLE · THREE-WAY · FOUR-WAY · NEEDLE · PLUG(2·3·4-WAY) ·
DIAPHRAGM · BALL(2-WAY·3-WAY) · BUTTERFLY · HOSE · PINCH · CHECK · FOOT ·
FLOW LIMITING(EXCESS FLOW) CHECK · POWER ACTUATED NON-RETURN VALVE ·
BACKFLOW PREVENTER · STOP CHECK · ANGLE CHECK · TANDEM BLOW DOWN ·
MOTOR OPERATED VALVE(`M`) · SOLENOID VALVE(`S`) · CONTROL VALVE WITH POSITIONER ·
WATER SEAL(`WS`) · BELLOWS SEALED VALVE · PRESSURE BALANCING / RELIEVING
EXTERNAL PIPE WITH SMALL VALVE

**ACTUATOR 글자** (몸체 위에 붙는 한 글자): `G`=GEAR(도시됨) · `A`=AIR WRENCH ·
`C`=CHAIN · `X`=EXTENSION STEM · `B`=WITH INTEGRAL BYPASS VALVE ·
`D`=DEEP STUFFING BOX AND LANTERN GLAND · `T`=TAP IN BOTTOM OF BODY (ASME TEST)

### VALVE STATUS SYMBOLS
OPEN DURING NORMAL OPERATION(속 빈 나비) · `LO` LOCKED OPEN ·
CLOSED(속 채운 나비) · `LC` LOCKED CLOSED · `L` THROTTLE ·
`NO`/`NC` (버터플라이 전용)

### MISCELLANEOUS
SPECTACLE BLIND · CIRCULAR/HAMMER BLIND · SIMPLEX/DUPLEX BASKET STRAINER ·
Y-TYPE/T-TYPE STRAINER · TEMPORARY STARTUP STRAINER · SCREEN TYPE STRAINER ·
FILTER(`F`) · FLAME ARRESTER · TRAP(`ST` 증기 · `AT` · `DT` · `RT` · `WT`) ·
PIPE CLASS CHANGE · BUILDING PENETRATION · DEBRIS FILTER · BALL SCREEN ·
BIRD SCREEN · VACUUM BREAKER · DIAPHRAGM SEAL · VORTEX BREAKER · FLOW GLASS ·
SEAL PIT · SPRAY NOZZLE/SPARGER · PROCESS LINE BREAK · **SUPPLIER INTERFACE
(`SCT` ↔ `SUPPLIER` 화살표)** · HIGH POINT VENT(V)/LOW POINT DRAIN(D) ·
SLIDING GATE · INSTRUMENTATION LINE BREAK · **BOUNDARY OF EQUIPMENT PACKAGE
PROVIDED BY SUPPLIER (체인 파선 상자)** · DRAIN LEG/DRIP POT

### UNIT IDENTIFICATION NUMBERS
`PLANT COMMON = 00` · `GTG / HRSG UNITS = 31` · `STG UNIT = -`
→ **이 표에 배수가 없다.**  그래서 TC2 의 Q'ty 는 27·36회차의 **그 장 NOTES**
(유닛 열거)로 정해지고, 노트도 없으면 설정 폴백이며 행이 그렇게 말한다.

## p3 — HVAC · 팬 · 댐퍼 · 소화 · 배수
계기 판정에는 쓰이지 않는다 (P&ID 본문에 HVAC 계통이 나오면 그때 본다).
`XSH` 화재감지기(S 연기 · X 화염 · F/D/C 열)만 계기로 올 수 있다.

## p4 — ★ ISA 문자표와 계기 심볼 (정답지의 핵심)

* **FIRST LETTER**: A 분석 · B 버너화염 · C 전도도 · D 밀도 · E 전압 · F 유량 ·
  G 게이징 · H 수동 · I 전류 · J 전력 · K 시간 · L 레벨 · M 수분 · P 압력 ·
  **PD 차압** · Q 수량 · S 속도 · T 온도 · U 다변수 · V 진동 · W 중량 ·
  X 미분류 · Y 이벤트 · Z 위치
* **SUCCEEDING**: E 1차소자 · T 전송기 · I 지시 · R 기록 · QI 적산지시 ·
  AL/AH/AHL 경보 · K 제어스테이션 · C 컨트롤러 · CV 제어밸브 · Z 기타최종제어 ·
  S 스위치 · G 국소관찰유리 · Y 솔레노이드/포지셔너 · P 테스트포인트 ·
  N 사용자선택 · X 미분류
  → `PIT`=압력전송기 · `PDIT`=차압전송기 · `TIT` · `LIT` · `FIT` · `LS` ·
  `PSV` · `ZSO/ZSC` 등이 전부 이 표에서 나온다.
* **GENERAL INSTRUMENTS (버블 모양)**: 민 스타디움 = 국소 설치 ·
  가로줄 하나 = 국소 패널 · 가로줄 둘 = 주 제어반 · 점선 = 성능시험용 ·
  **파선(뒤쪽 설치)** 구분이 있다.
* **SENSOR 별 도시**: FLOW(FE 오리피스 · 벤투리 · 피토 · 볼텍스 · 터빈 ·
  로타미터 · 코리올리 · 자기 · 초음파) · LEVEL(DIS 변위 · BNN · DP 차압 ·
  FLO 플로트 · REF 반사식 · GWR/RAD 레이더) · PRESSURE(직결 · 다이어프램 실) ·
  TEMPERATURE(**TW 서모웰** · TE · TIT · 이중센서 RTD/K · 충만식) · ANALYSIS
* **VALVE BODIES & FAILURE MODES**: TWO-WAY(글로브 도시) · THREE-WAY ·
  FO 개방고장 · FC 폐쇄고장 · FL 잠김 · FI 불확정
* **VALVES ACTUATORS**: 공압 다이어프램(포지셔너) · 압력평형 다이어프램 ·
  **로터리 모터 `M`** · 공압 실린더 단동/복동 · **유압 실린더 `H`** ·
  파일럿 밸브 복동 · **솔레노이드 `S`** · **전기/유압 `EH`** · 수동 `T` ·
  미분류 `X`
* **SELF-ACTUATED**: PRV · PSV · VRV · BPRV · PSE(파열판) · FRV · LRV · TRV

## p5 — 전형 루프와 공급자 표시
* MOV 전형(ON-OFF / INCHING / MODULATING) · 유압·공압 차단밸브 전형 ·
  공압 제어밸브 전형 · 모터(MCC) 전형
* **HAND ACTUATED**: `HCV`(공정선 수동제어밸브) · `HV` · `HS`
* **★ SUPPLIER DESIGNATOR — 버블에 `*` 가 붙으면 `FURNISHED BY EQUIPMENT
  SUPPLIER`.**  TC2 의 SCOPE 판정은 이 표시와 그 장 NOTES 가 정한다.
* LOGIC & SEQUENCE CONTROL: 마름모(국소 보조제어) · 마름모 안 사각(접근 불가
  PLC) · 사각 안 마름모(접근 가능 PLC)

## 정답지에서 쓰는 판정 규칙 (이 문서로부터)

1. **계기** = p4 의 버블 모양 + 그 안의 ISA 글자.  글자가 표에 없으면
   `범례에 없음` 으로 적고 확신도는 HIGH 가 아니다.
2. **밸브** = p2 LINE VALVES 의 몸체 형상.  액추에이터는 p4 VALVES ACTUATORS
   의 글자(`M`·`S`·`H`·`EH`·`T`·`X`)나 도시로 판정한다.
3. **SCOPE** = 버블·몸체의 `*`(p5) 와 그 장 NOTES 의 정의줄.  **못 읽으면 비운다.**
4. **Q'ty** = 그 장 NOTES 가 열거한 유닛 수.  범례 표에는 배수가 없다.
5. **발주처가 무엇을 계상하는가는 도면 밖이다 — 정답지에 넣지 않는다.**
