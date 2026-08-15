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
| 벤더 패키지 내부 계기 | 패키지 공급 범위. GT/ST/HRSG 스킨 내부 등 |
| 제어밸브에 딸린 포지셔너 | Valve 카테고리 |

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

## 5. Q'ty (수량) 통합 규칙

**같은 사양 · 같은 용도**로 중복 설치된 계기는 **한 행으로 합치고** `qty`에 개수를 적는다.

- 2-out-of-3, 이중화(A/B) 등으로 나란히 붙은 동일 계기 → 한 행, qty=2 또는 3
- UNIT #11 / #12 처럼 **호기가 다르면 별도 행**으로 둔다 (DESCRIPTION이 다르므로)
- 측정점이 다르면(공급/회수, 입구/출구) 별도 행

## 6. DESCRIPTION 작성 기준

`UNIT 번호 + 설비/계통 + 측정 대상 + 서브 식별자` 순서로 **영문 대문자**로 쓴다.
각 라인의 From/To 라벨(예: `TO HRSG#11 BD TANK`)을 근거로 삼는다.

```
UNIT #11 HP STEAM PRESSURE A
UNIT #11 BOILER FEED WATER PUMP B SUCTION PRESSURE A
UNIT #11 BFP A/B COOLER CCW RETURN TEMPERATURE
UNIT #11 BOILER FEED WATER PUMP B DISCHARGE IP FLOW ELEMENT
```

- 서브 식별자 `A`/`B`는 **이중화된 측정점을 구분할 때만** 붙인다.
- 유량 요소(FE)는 끝에 `FLOW ELEMENT`를 붙여 전송기(FIT)와 구분한다.
- 도면에서 설비 이름을 읽을 수 없으면 지어내지 말고 confidence를 `low`로 둔다.

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

도면에 `*` 또는 별도 심볼로 벤더 공급 범위가 표시된 계기는 `REMARK`에
`Vendor Scope`(또는 확인되는 벤더명)를 명시한다. 패키지 내부 계기라 목록에서
제외한 경우에는 `excluded`에 그 이유를 적는다.

## 10. 도면 Note 반영

각 도면 좌측의 `GENERAL NOTES` / `NOTES`를 읽고 계기에 영향을 주는 내용이면 REMARK에 반영한다.
예: `THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22` →
같은 계기가 다른 호기에도 있다는 뜻이므로, 호기별 행 분리 여부를 확인해야 한다(→ review_findings).

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

_(아직 없음)_
