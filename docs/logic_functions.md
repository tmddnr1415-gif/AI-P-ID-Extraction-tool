# LOGIC 기능 책 — 범례가 정한 동작

`config/logic_functions.yaml` + `config/logic_analog.yaml` 에서 만든 표입니다 (`python -m app.logic.functions`).  화면 근거 패널의 '동작 (범례)' 줄과 같은 사전입니다.

## 논리 기능

| 기능 | 동작 | 범례 원문 | 시뮬레이터 메모 | 입력 → 출력 |
| --- | --- | --- | --- | --- |
| AND (`and`) | 모든 입력이 1 일 때만 출력 1 | OUTPUT TRUE ONLY IF ALL INPUTS ARE TRUE | 입력을 다 읽지 못하면 출력 없음(0) · 연결 안 된 입력은 0 | 2개 이상 → 1 |
| OR (`or`) | 입력 중 하나라도 1 이면 출력 1 | OUTPUT TRUE IF ANY INPUT IS TRUE | 읽힌 입력 하나가 1 이면 나머지를 몰라도 1 | 2개 이상 → 1 |
| NAND (`nand`) | 입력 중 하나라도 0 이면 출력 1 (AND 의 반대) | OUTPUT TRUE IF ANY INPUT IS FALSE |  | 2개 이상 → 1 |
| NOR (`nor`) | 모든 입력이 0 일 때만 출력 1 (OR 의 반대) | OUTPUT TRUE ONLY IF ALL INPUTS ARE FALSE |  | 2개 이상 → 1 |
| NOT (`not`) | 입력이 0 이면 1 · 1 이면 0 | OUTPUT IS THE INVERSE OF THE INPUT | 입력이 연결 안 됐으면 0 으로 보아 출력 1 (L46) | 1 → 1 |
| 투표 (자격 OR · A/B) (`vote`) | B 개 입력 중 1 인 것이 A 개 이상(부호가 있으면 그 부호대로)일 때 출력 1 | A/B: OUTPUT TRUE ONLY IF AT LEAST A OF B INPUTS ARE TRUE · QUALIFIED OR: In > N / ≥ / < / ≤ / = | 부호 ≥ > ≤ < = ≠ (param.op) · 선 글자의 밑줄(_2>3 · 2=3)은 ≥ 로 | B 개 → 1 |
| 메모리 (S-R 래치) (`memory`) | S 가 1 이면 Q=1 로 걸리고 R 이 1 이면 Q=0 · 둘 다 1 이면 우선 칸(SET/RESET 우선)대로, 기본 메모리는 상태가 한 번 바뀜 · Q 와 /Q 는 언제나 반대 | SET: C=1 · RESET: C=0 · BOTH TRUE: SET DOMINANT C=1 / RESET DOMINANT C=0 / BASIC: OUTPUTS CHANGE STATE · D IS ALWAYS OPPOSITE OF C | 입력이 아직 안 정해진 첫 바퀴는 상태를 두고 본다 · S·R 함께 1 은 함께 1 이 되는 순간 한 번만 | S · R → Q · /Q |
| 켜짐 지연 (GT · ON DELAY) (`delay_on`) | 입력이 1 로 바뀌고 t 초 동안 유지되면 출력 1 · 입력 0 또는 R 이면 바로 0 | GT: OUTPUT TRUE AFTER INPUT HAS BEEN TRUE FOR t · RESET BY R | t = 사람 값 → 도면 글자(t= 3sec) → 기본 5초 · 위쪽 단자는 시간값 · 아래쪽은 리셋 (논리 입력 아님) | 1 (+ t · R) → 1 |
| 꺼짐 지연 (DT · OFF DELAY) (`delay_off`) | 입력이 1 이면 바로 1 · 입력이 0 으로 떨어진 뒤 t 초 동안 1 을 붙들다 0 | DT: OUTPUT STAYS TRUE FOR t AFTER INPUT GOES FALSE | t 는 GT 와 같은 순서 | 1 (+ t · R) → 1 |
| 펄스 (PD) (`pulse`) | 입력이 0→1 로 바뀌는 순간부터 t 초 동안만 출력 1 | PD: OUTPUT TRUE FOR t ON RISING EDGE OF INPUT | t 는 GT 와 같은 순서 · 가만히 있으면 0 | 1 (+ t · R) → 1 |
| 토글 (SRST) (`toggle`) | 입력이 1 로 바뀔 때마다 출력이 뒤집힌다 | NOTE: OUTPUT STATE IS INVERTED BY EACH MOMENTARY TRUE SIGNAL (그 장 NOTE 가 정의) | 오르는 변마다 · 거꾸로 맞추기는 입력 한 번 | 1 → 1 |
| STEP (시퀀스 단계) (`step`) | STEP_IN 이 1 이면 C_STEP 1 · CRIT 까지 1 이면 STEP_OUT 1 | STEP 상자 (시퀀스) | 근사 모델 — C_STEP = STEP_IN · STEP_OUT = STEP_IN AND CRIT | STEP_IN · CRIT → C_STEP · STEP_OUT |
| 신호원 · 누름단추 · 상수 (`source`) | 사람이 준 값 · FORCED INPUT 1/0 · ACTIVATION 은 언제나 1 | ACTIVATION: ALWAYS TRUE · FORCED INPUT 1/0 | 들어오는 선 없음 — 사람이 1/0 을 준다 | 없음 → 1 |
| 연결 기호 (`connector`) | 같은 글자의 짝 기호와 한 선 — 어느 하나가 1 이면 전부 1 | SIGNAL CONNECTOR (같은 글자끼리) | 짝 입력이 연결 안 됐으면 0 | 짝 → 짝 |
| 이음점 · 그대로 넘김 (`pass`) | 입력 값을 그대로 출력 | (그림 없음 — 선 위 이음점 · IEC '1') |  | 1 → 1 |
| 경보 · 기록 · 표시 (받기만) (`sink`) | 신호를 받아 표시·기록한다 — 출력 없음 | ALM · SER · DISPLAY · INDICATION | 출력을 내지 않는다 | 1 이상 → 없음 |
| 매크로 블록 (`macro`) | Typical 시트의 내부 로직을 상자 단자로 — 입력 단자 값으로 그 시트를 돌려 출력 단자로 낸다 | MACRO (TYPICAL SHEET 참조) | 같은 시간에 펼쳐 돌린다 (L15) · 여러 장 Typical 은 한 장으로 합침 (L38) | 단자 → 단자 |
| 판정 못 한 블록 (`unknown`) | 출력을 내지 않는다 — 사람이 종류를 정하면 그 기능으로 |  | 그 선을 직접 1 로 줄 수 있다 | ? → ? |

## 아날로그 · 비교 연산

| 연산 | 식 | 범례 이름 |
| --- | --- | --- |
| 합 (SUMMING) (`sum`) | M = X1 + X2 + … (입력마다 계수 · 부호) | SUMMING · SUM · ADDITION |
| 평균 (AVERAGING) (`mean`) | M = (X1 + X2 + … + Xn) / n | AVERAGING · AVERAGE · AVERAGE SELECTION · DUAL SELECTION · MEAN |
| 차 (DIFFERENCE) (`diff`) | M = X1 − X2 (+ 입력에서 − 입력을 뺀다) | DIFFERENCE · SUBTRACTION |
| 차의 절댓값 (`absdiff`) | M = |X1 − X2| | ABSOLUTE DIFFERENCE |
| 비례 (PROPORTIONAL) (`gain`) | M = K·X | PROPORTIONAL · GAIN |
| 역비례 (REVERSE PROPORTIONAL) (`rgain`) | M = −K·X | REVERSE PROPORTIONAL |
| 적분 (INTEGRAL) (`integral`) | M = (1/T1)∫X dt — 시간에 따라 쌓인다 | INTEGRAL · INTEGRATOR |
| 미분 (DERIVATIVE) (`deriv`) | M = Td·dX/dt — 값이 멈춰 있으면 0 | DERIVATIVE |
| 곱 (MULTIPLYING) (`mul`) | M = X1 × X2 | MULTIPLYING · MULTIPLY · MULTIPLICATION |
| 나눗셈 (DIVIDING) (`div`) | M = X1 ÷ X2 | DIVIDING · DIVIDE · DIVISION |
| 제곱근 (ROOT EXTRACTION) (`sqrt`) | M = √X | ROOT EXTRACTION · SQUARE ROOT |
| 거듭제곱 (EXPONENTIAL) (`pow`) | M = Xⁿ | EXPONENTIAL |
| 함수 발생기 F(X) (`fx`) | M = f(X) — 꺾은선 표 | FUNCTION GENERATOR · CHARACTERIZER |
| 시간 함수 F(T) (`ft`) | M = f(t) | TIME FUNCTION |
| 높은 값 선택 (HIGH SELECTOR) (`max`) | M = 입력 중 큰 값 | HIGH SELECTOR · HIGH SELECTION · HIGH SELECT · MAXIMUM SELECTION |
| 낮은 값 선택 (LOW SELECTOR) (`min`) | M = 입력 중 작은 값 | LOW SELECTOR · LOW SELECTION · LOW SELECT · MINIMUM SELECTION |
| 중간값 선택 (MEDIAN) (`median`) | M = 입력의 중간값 | MEDIAN SELECTION · MEDIAN |
| 상한 제한 (HIGH LIMITING) (`hilim`) | M = X (X < H) · H (X ≥ H) | HIGH LIMITING · HIGH LIMIT · HIGH LIMITER |
| 하한 제한 (LOW LIMITING) (`lolim`) | M = X (X > L) · L (X ≤ L) | LOW LIMITING · LOW LIMIT · LOW LIMITER |
| 절댓값 (ABSOLUTE VALUE) (`abs`) | M = |X| (입력이 둘이면 |X1 − X2|) | ABSOLUTE VALUE · ABSOLUTE |
| 변화율 제한 (VELOCITY LIMITING) (`velim`) | 멈춘 값에서는 M = X | VELOCITY LIMITING · RATE LIMIT · VELOCITY LIMIT |
| 1차 지연 (LAG) (`lag`) | 멈춘 값에서는 M = k·X | FIRST ORDER SIGNAL DELAY · FIRST ORDER LAG · LAG |
| 아날로그 신호 발생 (상수) (`const`) | M = A (도면 'A : 5%' · 운전원이 바꿀 수 있다) | ANALOG SIGNAL GENERATOR · CONSTANT |
| 바이어스 (BIAS) (`bias`) | M = X ± b | BIAS |
| 전환 (TRANSFER) (`transfer`) | M = IN1 (조건 C = 1) · IN2 (C = 0) | TRANSFER · SWITCH · SELECTOR SWITCH |
| PID 제어기 (`pid`) | 출력 = 제어기 계산 — 시뮬레이션에서는 수동 출력값 또는 추종(Tr) 값 | PID · CONTROLLER · PID CONTROLLER |
| 신호 변환 (CONVERTER) (`convert`) | M = X (신호 종류만 바뀐다) | CONVERTER |
| 수식 블록 (`formula`) | OUT = 도면에 인쇄된 식 |  |
| 참 입력 수 (BIT COUNTER) (`count`) | M = 1 인 디지털 입력의 수 (정수) | BIT COUNTER · BIT COUNT |
| 편차 감시 (DEVIATION) (`dev`) | |X1 − X2| > D 이면 1 | DEVIATION |
| 같음 비교 (EQUAL) (`equal`) | IN1 = IN2 이면 1 | EQUAL · EQUALITY |
