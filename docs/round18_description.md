# Description 잔여 3건 — 18회차 [F]

3차 피드백이 다시 지목한 셋을 **지금 무엇이 나오고 있나**부터 다시 쟀다.
17회차 결론을 인용하지 않고 이번 빌드의 출력으로 답한다.

---

## ★ 먼저 — [E] 가 만든 결함 하나를 [F] 가 잡았다

[E] 의 ANGLE 몸체 8행이 이런 문장으로 나가고 있었다:

```
p10 ANGLE   HRSG#11 HP STEAM SYSTEM DISCHARGE ANALYSIS ELEMENT
p21 ANGLE   TO CONDENSER OUTLET ANALYSIS ELEMENT
```

**`ANGLE` 이 ISA 조립으로 흘러갔다** — 첫 글자 `A` = ANALYSIS, 끝 글자
`E` = ELEMENT.  `describe_axis._VALVE_BODIES` 에 `ANGLE` 이 없어서다.
같은 이유로 `NEEDLE`·`DIAPHRAGM` 도 빠져 있었다 (이 문서에서는 0행이라
드러나지 않았을 뿐이다).

**뜻이 없는데 문법이 맞아서 눈으로는 안 걸린다.**  그래서 시험이 본다 —
`test_every_body_kind_the_detector_can_emit_has_a_valve_name` 이 검출기가
낼 수 있는 갈래를 소스에서 세어 전부 `<갈래> VALVE` 가 되는지 확인한다.
`BOWTIE_OTHER`("어느 갈래도 아님")만 예외이고, 그것에 이름을 주면 없는
밸브를 만드는 것이므로 **일부러 이름이 없다**.

추가한 세 낱말은 전부 **범례 p2 가 인쇄한 것**이다 (한 세로줄 x=1024.2:
GLOBE 588.8 · ANGLE 628.4 · NEEDLE 826.9 · PLUG 866.5 · DIAPHRAGM 923.2).

고친 뒤: `HRSG#11 HP STEAM SYSTEM DISCHARGE ANGLE VALVE`.

---

## F-1  Bypass Valve 언급 — **답이 바뀌었다.  [E] 가 몸체를 만들었기 때문**

17회차는 "8건이 194~198pt 로 가장 가까운 것은 맞지만 가까운 것은 아니다"
라고 적고 미구현으로 두었다.  **그 8건 중 6건이 p10·p11 이고, [E] 가 그
두 장에 ANGLE 몸체를 3개씩 새로 냈다.**  다시 쟀다.

| 장 | 라벨 | 가장 가까운 몸체 | 거리 | 2위 | 차 |
| --- | --- | --- | ---: | ---: | ---: |
| p10 | HP BYPASS VALVE | ANGLE #0 / PNEUMATIC | **89.5** | 585.5 | 496.0 |
| p10 | HRH BYPASS | ANGLE #1 / PNEUMATIC | **89.5** | 391.2 | 301.7 |
| p10 | LP BYPASS VALVE | ANGLE #2 / PNEUMATIC | **89.5** | 391.2 | 301.7 |
| p11 | HP BYPASS VALVE | ANGLE #0 / PNEUMATIC | **89.3** | 585.3 | 496.0 |
| p11 | HRH BYPASS | ANGLE #1 / PNEUMATIC | **89.3** | 391.5 | 302.2 |
| p11 | LP BYPASS VALVE | ANGLE #2 / PNEUMATIC | **89.2** | 391.4 | 302.2 |

**세 라벨이 세 몸체에 1:1 로 서고, 교차가 없고, 두 장에서 같다.**
17회차의 194~198pt 는 GLOBE 를 가리키던 값이고 그때는 진짜 몸체가
검출되지 않았다 — 거리가 답을 못 준 것이 아니라 **답이 도면에 없었다.**

### 그런데 적용하지 않았다 — 두 가지가 걸린다

1. **거리 89.5pt 는 유도된 `equipment_reach` 45.8pt 의 두 배다.**
   그것을 넓히는 것은 §2.2 "거리 제한 전역 완화" 다.  분리 요구치
   (2위와의 차 301.7pt)만으로 판정하는 규칙은 17회차 C-4 와 같은 모양이고
   만들 수 있지만, **이 회차의 게이트가 그것을 잴 수 없다** — 밸브 행이고
   CZF 양식이 미수령이라 채점되지 않는다.  재지 못하는 규칙은 §2.2 의
   "58장 전수 영향을 세지 않고 고쳤다고 보고" 로 가는 길이다.
2. **여섯 행 모두 현행 문장이 있다** (`HRSG#11 HP STEAM SYSTEM DISCHARGE
   ANGLE VALVE` 등, 판정축 ③).  8·9회차 기준은 축과 무관하게
   **"현행 문장이 있으면 신규 문형을 밀어내지 않는다"** 이다.

**둘 다 실무 판단이다** (§14.3).  발주처·실사용자가 아래 중 하나를 고르면
그대로 구현된다.

| 안 | 문장 | 바뀌는 행 |
| --- | --- | ---: |
| (가) 현행 유지 (지금) | `HRSG#11 HP STEAM SYSTEM DISCHARGE ANGLE VALVE` | 0 |
| (나) 라벨을 주어로 | `HRSG#11 HP BYPASS VALVE ANGLE VALVE` | 6 |
| (다) 라벨을 덧붙임 | `HRSG#11 HP BYPASS VALVE DISCHARGE ANGLE VALVE` | 6 |

**계기 쪽은 이미 되어 있다** — `BYPASS` 를 쓰는 FIELD 행이 **60행**이다
(`UNIT #11 HP BYPASS VALVE DOWNSTREAM PRESSURE A` 등).  남아 있던 것은
밸브 행뿐이고, 그 밸브가 이제 검출된다.

### 나머지 두 건 (p7)

`HRSG#11 / HRSG#12 HP BYPASS VALVE` 는 가장 가까운 몸체가 **260.2pt 이고
1위와 2위가 같은 거리(둘 다 GLOBE 260.2)** 다.  **갈리지 않으면 고르지
않는다** (9회차 규칙).  그 장에는 ANGLE 몸체가 없다.

---

## F-2  NOTE 언급 밸브 — **이미 나가고 있다** (p12 · 6행)

이번 빌드의 실제 출력:

```
p12 PNEUMATIC  GLOBE   AUX STEAM LETDOWN VALVE #10 GLOBE VALVE
                       등급 ● 도면 근거 있음 · Remark "판정축 ① · 귀속 AUX STEAM LETDOWN VALVE #10"
p12 FIELD      FIT     UNIT #10 AUX STEAM LETDOWN VALVE DOWNSTREAM FLOW
p12 FIELD      PDIT    UNIT #10 AUX STEAM LETDOWN VALVE DOWNSTREAM DIFFERENTIAL PRESSURE
p12 FIELD      FE      UNIT #10 AUX STEAM LETDOWN VALVE DOWNSTREAM FLOW ELEMENT
p12 FIELD      LS      UNIT #10 AUX STEAM LETDOWN VALVE LEVEL A
p12 FIELD      LS      UNIT #10 AUX STEAM LETDOWN VALVE LEVEL B
```

밸브 행은 판정축 ①(기기 직결)이 도면이 인쇄한 이름을 그대로 주어로
쓰고, 계기 5행은 같은 이름을 위치어와 함께 쓴다.  **새 규칙이 필요 없다.**
(17회차가 p14 로 같은 확인을 했고, 이번에는 지목된 p12 로 다시 확인했다.)

---

## F-3  SUPPLY / RETURN — **적용 19 · 보류 14**

17회차 C-4 가 만든 커넥터 짝 규칙의 이번 빌드 실적이다.

### 적용된 19행 — 전부 **2위가 없다**

| 장 | 행 | 낱말 |
| --- | ---: | --- |
| p21 | 7 | DISCHARGE 4 · OUTLET 3 |
| p38 | 12 | SUPPLY 7 · RETURN 5 |

19행 모두 `runner_up = None` 이다 — 그 축에 반대말 커넥터가 **아예 없다**.
즉 "가장 가까운" 이 아니라 **"유일한"** 것이라 거리 크기(124.7~748.7pt)가
판단에 들어가지 않는다.  이것이 17회차가 1195.4 ↔ 1213.7 을 뒤집은 뒤
남은 모양이고, 그 뒤집음이 옳았다는 증거다.

### 보류된 14행 — 두 커넥터가 **거의 같은 거리**

| 장 | 행 | 1위 ↔ 2위 차 |
| --- | ---: | --- |
| p18 | 7 | 12.8 ~ 18.4pt |
| p21 | 7 | 24.6 ~ 24.7pt |

요구치는 `connector_reach` **70.2pt**(런타임 실측)이고, 실제 차는 그
5분의 1 이하다.  오프페이지 커넥터가 시트 가장자리에 모여 있어 거리가
**공통 오프셋에 지배되기** 때문이다 — 18pt 차이는 정보가 아니다.

보류는 **지우지 않고** `evidence["connector_position_withheld"]` 에 낱말 ·
거리 · 2위 · 차 · 요구치 · 사유가 그대로 남는다.  근거 패널에서 읽을 수
있고, 발주처가 "그래도 붙이라" 고 하면 요구치 한 줄이다.

**지목된 행이 어느 쪽인지 확인하려면** 위 두 표의 장 번호를 보면 된다 —
적용은 p21·p38, 보류는 p18·p21 이다.  같은 p21 이 양쪽에 있는 이유는
그 장에 커넥터가 한쪽만 있는 계기와 양쪽 다 있는 계기가 섞여 있어서다.
