# 태그 넘버링 규칙 (KKS / ISA 5.1)

> 출처: `D00P-00GEN00-M05-0005` (P&ID FOR SYMBOLS & LEGENDS 4) 텍스트 레이어에서 발췌.
> 원문 근거가 있는 내용만 적었다. 확장할 때도 도면·기준서 근거를 함께 남긴다.
> 프로젝트 기준서: `19K9-00GEN00-G02-0002` (KKS NUMBERING SYSTEM)

---

## 1. KKS 식별 체계

태그 넘버링은 **KKS(Kraftwerk-Kennzeichensystem)** 기준을 따른다.
브레이크다운 레벨 4단계로 구성된다.

| 레벨 | 자리 | 의미 |
|---|---|---|
| 0 | `U` `U` | Plant Unit (호기 구분) |
| 1 | `S` `S` `S` + 숫자 | 시스템 코드 + 시스템 내 순번 (예: `LAB01`) |
| 2 | `A` `A` + 숫자 | 설비 유닛 코드 + 설비 순번 (예: `AP001`) |
| 3 | `-M` 등 | 컴포넌트 코드 |

**적용 예시 (도면 원문):**

```
20LAB31AP001      COGENERATION FEEDWATER PUMP A
20LAB11AP001-M    COGENERATION FEEDWATER PUMP A MOTOR
```

## 2. 호기(Plant Unit) 코드

| 코드 | 의미 |
|---|---|
| `00` | POWER PLANT COMMON |
| `10` | FIRST GROUP COMMON (INCL. FIRST GROUP STG) |
| `11` | FIRST GROUP #1 GTG / HRSG |
| `12` | FIRST GROUP #2 GTG / HRSG |
| `20` / `21` / `22` | SECOND GROUP (동일 구조) |

도면번호 `D00P-11LAB00-M05-0001`의 `11`이 이 호기 코드이며, DESCRIPTION의
`UNIT #11`과 대응한다.

## 3. 도면번호 체계

```
D00P - 11LAB00 - M05 - 0001
 │       │        │      └ 도면 일련번호
 │       │        └ 도면 종류 (M05 = P&ID)
 │       └ 호기(2) + 시스템 코드(3) + 시스템 순번(2)
 └ 프로젝트 코드
```

## 4. 계기 회로 번호 범위

계기류는 KKS 번호 범위 중 `191-199`(INSTRUMENTATION), `201-250`(INSTRUMENT ISOLATION)
구간을 사용한다. 밸브류는 `001-100`(주배관 밸브), `101-190`(밸브 일반),
`301-399`(제어밸브/댐퍼), `401-499`(안전밸브) 등 별도 구간이다.

## 5. 이 프로젝트에서 태그 번호를 쓰지 않는 이유

제안(proposal) 단계 도면이라 계기 버블 안의 태그 번호 자리가 점선(`.....`)으로
비어 있다. 정답 Instrument List의 `TAG` 열도 563행 전부 비어 있다.

→ **판독 단계에서 태그 번호를 생성하지 않는다.**
→ 행의 식별자는 `P&ID No. + TYPE + DESCRIPTION` 조합이다.

상세설계 단계 도면으로 넘어가 태그가 부여되면 이 절을 개정하고, `extraction_guide.md`
7절도 함께 고친다.

## 6. ISA 5.1 문자 조합

첫 글자(측정 변수)와 뒤 글자(기능)의 조합표는 Symbol & Legend 도면에서 추출해
`rules/symbol_legend.md`에 둔다. 이 프로젝트에서 실제로 나타나는 조합은 다음과 같다
(정답 Instrument List 563행 기준).

| TYPE | 조합 해석 |
|---|---|
| `PI` / `TI` / `LI` | 압력 / 온도 / 레벨 지시계 |
| `PIT` / `TIT` / `LIT` / `FIT` | 지시 + 전송기 |
| `PDIT` | 차압 지시 전송기 |
| `LS` / `FS` | 레벨 / 유량 스위치 |
| `FE` | 유량 요소 (오리피스 등) |
| `RO` | 제한 오리피스 (Restriction Orifice) |

`AIT`(분석), `LSH`/`LSHH`/`LSL`(레벨 스위치 하이/로우) 등은 템플릿에는 예시로
언급되어 있으나 현재 정답 목록에는 나타나지 않는다. 새로 발견되면 `review_findings`로
보고하고 이 표에 추가한다.
