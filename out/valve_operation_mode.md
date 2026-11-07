# [0-2] 밸브 산출물의 빈 칸 — 조사 결과

이번 회차에서 **고치지 않았습니다.**  아래는 조사와 측정뿐입니다.

## 무엇이 비어 있나

`bfv_pid_total.xlsx` · `mov_pid_total.xlsx` 에서 채워지는 열은
A(NO) · B(P&ID No.) · D(Q'ty) · E(SYSTEM) · Y(ACTUATOR) · AA(BODY) · AM(REMARK)
입니다.  비어 있는 것은 **C(VALVE TYPE) · K(TAG NUMBER) · L(DESCRIPTION)** 입니다.

---

## 1. OPERATION MODE 를 도면에서 유도할 수 있는가 — **예, 유도됩니다**

### 1-1. 발주처 리스트에서 액추에이터와 동작방식이 어떻게 묶이나

| 파일 | ACTUATOR | OPERATION MODE | VALVE TYPE | 행 |
| --- | --- | --- | --- | ---: |
| BFV | HYDRAULIC | ON-OFF | HOV | 4 |
| BFV | MOTOR | INCHING | MOV_I | 6 |
| BFV | MOTOR | ON-OFF | MOV | 8 |
| BFV | PNEUMATIC | MODULATING | CV | 1 |
| MOV | MOTOR | INCHING | MOV_I | 2 |
| MOV | MOTOR | ON-OFF | MOV | 61 |

액추에이터가 동작방식을 정하는가:

| ACTUATOR | 갈래 | |
| --- | --- | --- |
| HYDRAULIC | ON-OFF (HOV) 하나 | 결정됨 (n=4) |
| PNEUMATIC | MODULATING (CV) 하나 | 결정됨 (**n=1 — 근거가 얇습니다**) |
| MOTOR | ON-OFF (MOV) 와 INCHING (MOV_I) **둘로 갈림** | 결정 불가 |

즉 갈리는 곳은 **MOTOR 하나**뿐입니다.

### 1-2. 도면이 그 하나를 낱말로 인쇄합니다

전 도면에서 해당 낱말의 출현: `INCH` 8회 · `INCHING` 3회 · `MODULATING` 1회 ·
`ON-OFF` 1회 (뒤의 셋은 범례).

`INCH` 8회는 **전부 MOTOR 밸브 옆**에 있고, 거리는 밸브 긴변의 1배 안입니다
(실측 6.4 · 13.2 · 13.3pt).  도면별로 맞춰 보면:

| P&ID No. | 도면의 INCH 밸브 | 발주처 MOV_I 행 |
| --- | ---: | ---: |
| D00P-10LBC50-M05-0001 | 2 | 2 |
| D00P-00PAB10-M05-0001 | 2 | 2 |
| D00P-00PAB10-M05-0002 | 2 | 2 |
| D00P-00PAB10-M05-0003 | 2 | 2 |
| **합계** | **8 / 4장** | **8 / 4장** |

INCH 가 있는데 MOV_I 가 없는 도면 **0장**, MOV_I 가 있는데 INCH 가 없는 도면
**0장**.  반례가 없습니다.

### 1-3. 그러므로 유도 규칙은 이렇게 됩니다 (구현하지 않음)

```
PNEUMATIC                        -> MODULATING   (CV)     발주처 1/1  <- n=1
HYDRAULIC                        -> ON-OFF       (HOV)    발주처 4/4
MOTOR + 밸브 긴변 1배 안에 'INCH' -> INCHING      (MOV_I)  도면 8/8 · 4장/4장
MOTOR (그 밖)                     -> ON-OFF       (MOV)    발주처 69/69
```

**주의할 점 두 가지.**
- PNEUMATIC → MODULATING 은 발주처 행이 **1행**뿐입니다.  우리 PNEUMATIC 탭은
  46행이므로, 1행으로 46행을 판정하는 셈이 됩니다.  이 한 갈래는 발주처 확인이
  필요합니다.
- 'INCH' 는 낱말이지 기호가 아니므로, 다른 프로젝트가 같은 낱말을 쓴다는
  보장은 이 문서에서 나오지 않습니다.  다만 범례가 `INCHING` 을 정의하고
  있으므로, 범례에서 낱말을 읽어 오는 방식이면 이관됩니다.

---

## 2. 액추에이터만으로 VALVE TYPE 을 어디까지 채울 수 있나

| ACTUATOR | 우리 행 | 액추에이터만으로 |
| --- | ---: | --- |
| HYDRAULIC | 4 | HOV 로 결정됨 |
| PNEUMATIC | 46 | CV 로 결정됨 (근거 n=1) |
| MOTOR | 94 | **결정 불가** — MOV / MOV_I 두 갈래 |

즉 액추에이터만으로는 **144행 중 50행(34.7%)** 만 결정되고, MOTOR 94행은
남습니다.  위 §1-2 의 INCH 규칙을 얹으면 그 94행도 갈립니다.

---

## 3. 공란이 원칙에 맞는가

| 열 | 현재 | 판단 |
| --- | --- | --- |
| C VALVE TYPE | 공란 | **원칙에 맞지 않습니다.**  §1 에서 보듯 도면에서 유도됩니다.  "도면에서 읽을 수 없는 항목은 공란" 이 원칙인데, 이것은 읽을 수 있습니다 |
| K TAG NUMBER | 공란 | **맞습니다.**  도면이 `.....` 로 미부여이고 발주처 부여 규칙이 없습니다 (인수인계 §4-11) |
| L DESCRIPTION | 공란 | **맞습니다.**  발주처 마스터 밸브 리스트가 없고, CZH·CZI 리스트에는 DESCRIPTION 열 자체가 채워져 있지 않습니다.  우리 144행은 전부 수동 밸브이므로 두 리스트 어디에도 대응이 없습니다 (인수인계 §4-8) |

**요약**: 세 열 중 둘은 공란이 정답이고, **VALVE TYPE 하나만 채울 수 있습니다.**
채우는 작업은 이번 회차의 지시 범위 밖이므로 하지 않았습니다.
