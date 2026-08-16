# P&ID Field Instrument 판독 규칙

> 이 문서는 `extract_instruments.py`의 시스템 프롬프트에 **통째로** 들어간다.
> 사람이 검토하면서 발견한 오류를 규칙으로 바꿔 여기에 계속 누적한다.
> 규칙을 고칠 때는 `review_log.md`에 언제·무엇을·왜 고쳤는지 함께 남긴다.

버전: v1 (초기) · 최종 수정: 2026-08-15

---

## 1. 읽는 순서

각 P&ID는 **위 → 아래, 왼쪽 → 오른쪽** 순서로 읽는다. 출력 행 순서도 이 순서를 따른다.
확대 타일이 제공되면 타일 순서(r0c0 → r0c1 → …)가 곧 이 순서다.

## 2. Symbol & Legend 우선

계기를 판독하기 전에 `rules/symbol_legend.md`(기호 정의, 첫 글자/뒤 글자 조합표, 신호선,
밸브 상태 기호 FO/FC/LO)를 먼저 적용한다. 레전드에 없는 기호를 임의로 해석하지 않는다.

## 3. 무엇이 Field Instrument인가

계기는 **원(circle) 또는 태그 박스** 안에 **계기 문자 조합**이 들어 있는 것으로만 식별한다.

계기로 **오인하지 말 것**:

- 배관 치수 표기 (DN 사이즈, `550`, `SPL-THK` 등)
- 라인 브레이크 기호, 연속 도면 참조 화살표
- 장비 심볼(펌프, 열교환기)과 장비 번호
- 밸브 자체, 밸브 액추에이터, `I/P` 변환기

이번 단계 범위에서 **제외**하는 것 (제외한 사실은 `excluded`에 이유와 함께 남긴다):

| 대상 | 이유 |
|---|---|
| `ZS`, `ZSO`, `ZSC` | 밸브 리밋스위치 — Valve 카테고리에서 다룬다 |
| `HS`, `XS` | 수동 스위치 / 기타 — Field Instrument 아님 |
| 벤더 공급 범위 표기가 붙은 계기 | 아래 3.1 |
| 제어밸브에 딸린 포지셔너 | Valve 카테고리 |
| `PSV`, `MOV`, `TW` | 안전밸브 / 전동밸브 / 서모웰 — 계기 아님 |

### 3.1 벤더 공급 범위 표기 — 가장 큰 제외 사유

**이 판단 하나가 도면당 행 수를 좌우한다. 다른 무엇보다 먼저 확인한다.**

각 도면 우측 `GENERAL NOTES` 아래에 기호 각주가 있다. 예:

```
*   DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG.
**  DENOTES EQUIPMENT WILL BE SUPPLIED BY ST SUPPLIER.
*   MARKED ITEM TO BE SUPPLIED BY BFP SUPPLIER.
```

**계기 버블 바로 위에 `*` 또는 `**` 가 찍혀 있으면 그 계기는 목록에서 뺀다.**
점선/일점쇄선 박스에 `*` 가 하나 찍혀 있으면 **박스 안 계기 전부**가 해당된다.
각주 문구는 도면마다 다르므로 그 도면의 각주를 읽고 판단한다.

빼는 이유는 남의 공급 범위라서다. `excluded` 에 어떤 표기 때문인지 반드시 남긴다.

> 실측: `D00P-10LBA10-M05-0001`(HP Steam)은 계기 문자 34건 중 `*`(HRSG) 16건,
> `**`(ST SUPPLIER) 6건이 이 표기 때문에 빠져 **12건만** 목록에 오른다.
> `D00P-11LAB00-M05-0001`(Feedwater)은 `*`(BFP SUPPLIER)가 붙은 PDIT 2건이 빠진다.

`SCT` + 화살표 + 공급자명(`HRSG`, `SUPPLIER`)은 공급 범위 경계선이다. 경계 **바깥**
(우리 범위)의 계기는 표기가 없으므로 포함한다. 경계 자체를 제외 근거로 쓰지 않는다.

## 4. 텍스트 레이어 후보의 사용법

프롬프트에 함께 들어오는 "텍스트 레이어 계기 문자 후보"는 PDF에서 결정적으로 추출한
것이라 **위치와 개수가 정확하다**. 이것을 기준선으로 삼되 그대로 옮기지 않는다.

- 후보 하나하나를 이미지에서 확인해 Field Instrument인지 판단한다.
- 후보에 없어도 이미지에서 계기를 발견하면 추가하고 `source_tokens`에 그 사실을 적는다.
- 후보 문자와 최종 TYPE은 다를 수 있다. 도면에는 전송기를 `PT`로 그려도
  Instrument List의 TYPE은 `PIT`로 쓴다.

### 도면 문자 → TYPE 매핑

| 도면 문자 | Instrument List TYPE |
|---|---|
| PT, PIT | PIT |
| TT, TIT | TIT |
| LT, LIT | LIT |
| FT, FIT | FIT |
| PDT, PDI, PDIT | PDIT |
| AT, AIT | AIT |
| PI / TI / LI / FI | 그대로 (지시계) |
| FE | FE (오리피스 등 유량 요소) |
| RO | RO (제한 오리피스) |
| LS, FS, PS, TS | 그대로 (스위치) |

## 5. Q'ty (수량) 규칙

`Q'ty`는 **이 도면이 대표하는 호기 수**다. 도면에 그려진 계기 개수가 아니다.

### 5.1 "CONFIGURATION IS IDENTICAL FOR ..." 노트가 Q'ty를 정한다

각 도면 `NOTES` 1번에 거의 항상 이런 문장이 있다.

```
THIS P&ID IS FOR GROUP#10, CONFIGURATION IS IDENTICAL FOR GROUP#20.
THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22.
```

이때 **행을 호기별로 나누지 않는다. 한 행으로 두고 `qty`에 호기 수를 적는다.**

| 노트 | qty |
|---|---|
| `FOR GROUP#10 … IDENTICAL FOR GROUP#20` | **2** |
| `FOR UNIT#11 … IDENTICAL FOR UNIT#12,21,22` | **4** |
| 그런 노트가 없음 | 1 |

**예외 — 호기 공용 설비는 qty 1.** 설비명에 `PLANT COMMON`이 붙어 있거나 전 호기가
같은 것 하나를 쓰는 설비(예: `AUXILIARY BOILER COOLER (PLANT COMMON)`)는 복제되지
않으므로 노트와 무관하게 `qty = 1`이다.

### 5.2 도면 안에서 합치지 않는다

같은 도면에 나란히 그려진 계기는 각각 **별도 행**이다. 합쳐서 qty를 올리지 않는다.

- 오리피스(FE) 하나에 전송기(FIT) 2개 → FE 1행 + FIT 2행 (DESCRIPTION 끝에 A / B)
- 펌프 A 라인과 펌프 B 라인 → 각각 별도 행
- 공급/회수, 입구/출구 → 각각 별도 행

> 실측: `D00P-10PGB10-M05-0004`(CCW)는 계기 24건이 모두 별도 행 24행이고,
> `PLANT COMMON` 냉각기 3행만 qty 1, 나머지 21행이 qty 2다.

## 6. DESCRIPTION 작성 기준

`UNIT 번호 + 설비/계통 + 측정 대상 + 서브 식별자` 순서로 **영문 대문자**로 쓴다.
각 라인의 From/To 라벨(예: `TO HRSG#11 BD TANK`)을 근거로 삼는다.

```
UNIT #11 HP STEAM PRESSURE A
UNIT #11 BOILER FEED WATER PUMP B SUCTION PRESSURE A
UNIT #11 BFP A/B COOLER CCW RETURN TEMPERATURE
UNIT #11 BOILER FEED WATER PUMP B DISCHARGE IP FLOW ELEMENT
```

- 유량 요소(FE)는 끝에 `FLOW ELEMENT`를 붙여 전송기(FIT)와 구분한다.
- 도면에서 설비 이름을 읽을 수 없으면 지어내지 말고 confidence를 `low`로 둔다.

### 6.1 자리별로 뜯어보면

```
UNIT #11   BOILER FEED WATER PUMP   A    DISCHARGE HP   FLOW   B
└ 호기      └ 설비 (약어 금지)        └ 설비  └ 구간·계통    └ 측정  └ 중복
                                      서브                    대상    식별자
```

**A/B가 두 자리에 나온다. 뜻이 다르므로 섞지 않는다.**

| 자리 | 뜻 | 예 |
|---|---|---|
| 설비명 **뒤** | 어느 설비인가 | `PUMP A SUCTION PRESSURE` |
| 문장 **끝** | 같은 지점의 몇 번째 계기인가 | `SUCTION PRESSURE A` / `... B` |

둘 다 필요하면 둘 다 쓴다 — `BOILER FEED WATER PUMP A SUCTION PRESSURE B`
(A펌프 흡입에 붙은 두 압력전송기 중 두 번째).

### 6.2 설비 이름은 그 도면의 설비 박스에 적힌 대로 쓴다

지어내거나 임의로 줄이거나 늘리지 않는다. 같은 설비라도 도면이 다르게 부르면 다르게 쓴다.

| 도면의 설비 박스 | DESCRIPTION |
|---|---|
| `FEEDWATER PUMP FOR HRSG UNIT #11 (A/B)` | `BOILER FEED WATER PUMP A` |
| `#11 BFP A/B COOLERS` | `BFP A/B COOLER` |

계통 약어 `HRSG` `CCW` `HP` `IP` `LP` `STG` 는 항상 그대로 둔다.

### 6.3 설비 하나를 여러 갈래가 공유하면 설비 이름을 그대로 쓴다

도면 설비 박스가 `#11 BFP A/B COOLERS` 처럼 A/B를 묶어 부르면 **묶은 이름 그대로**
`UNIT #11 BFP A/B COOLER ...` 로 쓴다. 갈래마다 행은 따로 만들되 이름은 쪼개지 않는다.
같은 DESCRIPTION이 두 행 나오는 것은 정상이다.

마찬가지로 `#11 HRSG COOLERS (CPH. HGCF)` 는 괄호 안을 풀지 말고
`UNIT #11 HRSG COOLERS ...` 로 쓴다.

### 6.4 공용 헤더는 설비 서브 식별자를 뺀다

펌프 A/B가 공유하는 흡입·토출 헤더의 계기는 설비 서브를 붙이지 않는다.

```
UNIT #11 BOILER FEED WATER PUMP SUCTION PRESSURE              ← 공용 흡입 헤더
UNIT #11 BOILER FEED WATER PUMP A SUCTION PRESSURE A          ← A펌프 개별
UNIT #11 BOILER FEED WATER PUMP DISCHARGE HEADER HP PRESSURE A ← 공용 토출 헤더
```

### 6.5 구간 이름은 도착지에서 가져온다

배관에 적힌 치수(`DN200`)나 선 이름(`MINIMUM FLOW RECIRCULATION LINE`)이 아니라
**그 갈래가 어디로 가는지**로 이름 붙인다. `TO HRSG#11 HP ECONOMIZER` 로 가는
유량계는 `DISCHARGE HP FLOW`, IP 이코노마이저로 가면 `DISCHARGE IP FLOW` 다.

### 6.6 호기 공용은 그룹 번호를 쓴다

특정 호기에 속하지 않고 그룹이 공유하는 계기는 그룹 번호를 호기 자리에 쓴다.
GROUP#10 도면의 공통 헤더 → `UNIT #10 HP STEAM DRAIN TEMPERATURE`.

## 7. TAG 열은 비운다

제안 단계 도면의 계기 버블은 태그 번호 자리가 점선(`.....`)으로 비어 있다.
템플릿의 `TAG` 열도 전 행이 비어 있다. **태그 번호를 만들어내지 않는다.**
행의 식별은 `P&ID No. + TYPE + DESCRIPTION` 조합으로 한다.

## 8. INST. TYPICAL TYPE 선택

TYPE이 정해지면 허용된 TYPICAL TYPE 중에서 고른다(프롬프트에 목록이 들어온다).
선택 기준은 도면에서 읽히는 설치 형태다.

- 다이어프램 실(remote seal)/캐필러리가 그려져 있으면 `-2`/`-3` 계열
- 일반 직결/원격 전송이면 `-1` 계열
- 온도계는 열전대(T/C)면 `TIT-3`, RTD면 `TIT-5`
- 판단 근거가 도면에 없으면 가장 흔한 계열을 고르고 confidence를 `medium` 이하로 둔다

## 9. Vendor Scope 표기

3.1이 판단 기준이다. 표기가 붙은 계기는 목록에서 빼고 `excluded`에 어떤 표기 때문인지
적는다. 빼지 않기로 한 경계 근처 계기는 `REMARK`에 `Vendor Scope`(또는 벤더명)를 남긴다.

## 10. 도면 Note 반영

판독을 시작하기 전에 도면 우측 `GENERAL NOTES` / `NOTES` / 기호 각주를 **먼저** 읽는다.
행 수와 Q'ty가 여기서 결정되기 때문이다.

| 읽을 것 | 결정되는 것 |
|---|---|
| `*` / `**` 공급 범위 각주 | 어느 계기를 뺄지 (→ 3.1) |
| `CONFIGURATION IS IDENTICAL FOR ...` | Q'ty (→ 5.1) |
| 그 외 계기에 영향 주는 노트 | REMARK |

## 11. REMARK / 개정 표기

- 개정으로 추가된 계기: `ADD`
- 개정으로 삭제된 계기: `DEL` (행은 남기고 REMARK에 표기)
- 해당 없음: `-`

## 12. 채우지 않는 컬럼

다음은 도면에서 읽을 수 없으므로 **비워 둔다**. 억지로 채우지 않는다.

- `UNIT`, `SYSTEM CODE`, `SYSTEM SEQUENCE`, `TAG` — 템플릿에서 전 행 비어 있음
- `Design table No.`, 운전/설계 조건, 배관 정보, `Rating`, `Velocity Criteria`, `Fluid`
  — 별도 Design Table에서 조인
- `REQUIRED CALIBRATION RANGE`, `UNIT`, `ELEM. MATERIAL`, `Connection Type`,
  `TW / CHAMBER SPECIFICATION`, `EXPLOSION PROOF` — 서비스 조건에 따라 달라져
  TYPICAL TYPE만으로 결정되지 않음
- `BODY MATERIAL`, `Scope of Supply`, `MAKER`, `MODEL`, `STATUS`

## 13. 확신도와 검토 의견

- `confidence`: 글자가 흐리거나 맥락 추정이 섞였으면 `low`
- 판독 불가 영역, 도면 간 태그 충돌, 규칙으로 판단이 안 되는 경우는 반드시
  `review_findings`에 남긴다. 조용히 넘어가지 않는다.

---

## 검토 피드백에서 도출된 규칙

> `scripts/apply_feedback.py --apply-rules` 가 이 아래에 규칙을 추가한다.
> 사람이 문장을 다듬어 위 본문으로 승격시키는 것을 권장한다.

**2026-08-16 · 1차 시험판독 (p6 / p20 / p38) 결과 반영 — 본문으로 승격 완료**

정답 대조에서 나온 것들이며 각각 위 본문에 반영했다.

| 발견 | 반영 위치 |
|---|---|
| `*` / `**` 공급 범위 표기가 최대 제외 사유 (p6는 34건 중 22건이 이 사유) | 3.1 |
| `CONFIGURATION IS IDENTICAL FOR ...` 는 행 분리가 아니라 Q'ty 배수 | 5.1 |
| `PLANT COMMON` 설비는 그 배수에서 제외 (qty 1) | 5.1 |
| 도면 안 병렬 계기는 합치지 않는다 (FE 1 + FIT 2 = 3행) | 5.2 |
| A/B가 설비 자리와 문장 끝 자리에서 뜻이 다르다 | 6.1 |
| `BFP` → `BOILER FEED WATER PUMP` 로 풀어 쓴다 | 6.2 |
| 설비 박스가 `A/B COOLERS` 면 이름을 쪼개지 않는다 | 6.3 |
| 공용 헤더는 설비 서브 식별자를 뺀다 | 6.4 |
| 구간 이름은 배관 치수가 아니라 도착지에서 (`DISCHARGE HP FLOW`) | 6.5 |
| 그룹 공용 계기는 그룹 번호를 호기 자리에 (`UNIT #10`) | 6.6 |
