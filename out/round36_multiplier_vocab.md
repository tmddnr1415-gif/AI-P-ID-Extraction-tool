# 승수 어휘 실측 — IDENTICAL 과 SIMILAR 을 어떻게 다루고 있나

**엔진 코드 0줄.  측정만 했습니다.**  파이프라인을 다시 돌리지 않고 저장된 회귀 결과
(`out/regression_3p/*.json`)와 PDF 의 낱말만 읽었습니다.  도구는 `spike/vocab_*.py` 다섯입니다.

## 0. 한 줄

**코드는 IDENTICAL · SIMILAR · SAME · TYPICAL 을 이미 구분하지 않습니다** — 평평한 낱말 하나짜리
집합이고, 문단에 넷 중 **아무거나 하나** 나오면 그 문단이 열거한 유닛 표기를 셉니다.
그래서 "SIMILAR 을 IDENTICAL 과 같게 본다" 는 **지금 상태**이고 바꿀 것이 없습니다.
더 센 사실이 하나 있습니다 — **네 낱말을 전부 지워도 네 프로젝트의 Q'ty 가 한 칸도 안 움직입니다**
(§5).  판정을 지고 있는 것은 낱말이 아니라 *번호 붙은 NOTES 문단이 유닛 표기를 둘 이상 열거하는가* 입니다.

## 1. 승수를 읽는 코드가 받는 어휘 — 정확한 문자열

`app/engine/projectconfig.py`

```python
_DEFAULT_SAME  = ("IDENTICAL", "SIMILAR", "SAME", "TYPICAL")   # 275줄
_DEFAULT_UNIT  = ("GROUP", "UNIT", "TRAIN")
_DEFAULT_RANGE = ("THRU", "THROUGH", "~")
```

* `note_vocabulary(cfg)` 가 config `qty_note.same_words` 로 **덮어쓸 수** 있고, 비어 있으면 위 기본값입니다.
* 쓰는 법은 `_word_re` → `(?<!\w)(?:IDENTICAL|SIMILAR|SAME|TYPICAL)(?!\w)` **하나의 OR 패턴**입니다.
  **넷 사이에 우선순위도 가중치도 없습니다** — `same_re.search(문단)` 이 참이면 그 문단을 본다, 그뿐입니다.
* 배수는 그 문단이 열거한 유닛 표기의 **개수**입니다 (`len(toks)`, 중복 제거).  낱말은 *문단을 고르는 문지기*이고
  수를 정하는 것은 유닛 표기입니다.
* 읽는 순서(`pipeline._note_factor`): ①범례표 → ②이 NOTES → ③사람 지정 → ④설정 폴백 → ⑤빈칸.
  **범례가 답한 문서에서는 ②를 아예 보지 않습니다.**

## 2. TC2 60장 — 도면 원문

| 낱말 | 배수를 낸 문단 | 장 |
| --- | ---: | --- |
| SIMILAR | 23 | 6·7·8·9·10·12·13·14·15·16·17·18·19·20·21·22·25·28·48·49·50·59·60 |
| IDENTICAL | 7 | 11·26·27·29·31·38·39 |
| TYPICAL | 6 | 23·24·51·52·54·55 |
| SIMILAR + TYPICAL 한 문단 | 3 | 33·34·35 |
| SAME | 2 | 30·32 |
| **합** | **41 문단 / 39 장** | |

원문 (각 갈래 대표 한 줄):

```
p6   1. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO UNIT 3-2, UNIT 4-1,
        UNIT 4-2, UNIT 5-1, UNIT 5-2, UNIT 6-1, UNIT 6-2.                              → x8
p11  1. AUXILIARY STEAM SYSTEM P&ID FOR UNIT 3-2, UNIT 4-1, … UNIT 6-2 WILL BE IDENTICAL
        TO UNIT 3-1 AS SHOWN IN THIS P&ID.                                             → x8
p23  1. THIS P&ID IS APPLICABLE FOR UNIT 3-1,3-2 AND IS TYPICAL FOR UNITS 4-1, 4-2, 5-1,
        5-2, 6-1, AND 6-2.                                                             → x8
p32  10. THIS P&ID IS APPLICABLE FOR UNIT 3-1 ONLY, SAME WILL BE APPLICABLE FOR UNIT 3-2,
        4-1, 4-2, 5-1, 5-2, 6-1 & 6-2.                                                 → x8
p35  5. THE P & ID IS TYPICAL FOR UNIT 3-1 & 3-2, SIMILAR P & ID IS APPLICABLE FOR 4-1 &
        4-2, 5-1 & 5-2 AND 6-1 & 6-2.  NOTES                                           → x8
p38  2. THIS P&ID IS COMMON FOR UNITS NO.3-1 & 3-2. AN IDENTICAL SYSTEM SHALL BE
        DUPLICATED FOR UNIT 4-1 & 4-2, 5-1 & 5-2, …                                    → x8
p29  7. COLD VENT STACK IS IDENTICAL FOR UNIT NO. 5&6.                                 → x2
p30  9. THIS P&ID IS APPLICABLE FOR UNIT 3 & 4, SAME WILL BE APPLICABLE FOR UNIT 5& 6.  → x4
p31  1. THIS P&ID IS IDENTICAL FOR UNIT NO. 5-1, 5-2 & UNIT NO. 6-1, 6-2.               → x4
p51  2. THIS P&ID IS APPLICABLE FOR UNIT 3-1 & 3-2 AND IS TYPICAL FOR UNITS 6-1 AND 6-2.→ x4
```

배수 분포 — x8 28장 · x4 6장 · x2 1장 (행이 있는 장 기준 29장).

**⚠ 세 가지를 같이 적습니다.**

1. **같은 낱말이 다른 뜻으로도 쓰입니다.**  시트 전체로 세면 TC2 는 `TYPICAL` 30 · `SIMILAR` 41 ·
   `SAME` 9 · `IDENTICAL` 10 인데, NOTES 창 안은 각각 9 · 26 · 2 · 7 입니다.  바깥의 것은
   **범례의 그리기 관례**이거나 배관 주석입니다:
   `p4 ( ) TYPICAL SYMBOL …` · `p5 VALVE BODY WITH ACTUATOR-TYPICAL FOR MOTOR OPERATED VALVES` ·
   `(DISTRIBUTION SAME AS UNIT 3-2)` · `DN 1234 (SAME AS ABOVE 3-1)`.
   이것들을 막고 있는 것은 낱말이 아니라 **NOTES 창 + 유닛 표기 2개 이상** 조건입니다.
2. **p33 · p34 는 낱말이 있는데 배수가 안 섭니다** (각 20행 · Q'ty 20 = x1 설정 폴백).
   원문 `5. THE P & ID IS TYPICAL FOR 3-1 & 3-2 SIMILAR P & ID SHALL BE APPLICABLE FOR 4-1 & 4-2.`
   — **`UNIT` 이라는 낱말 없이** 숫자만 적어서 `_unit_tokens` 의 머리 규칙(`UNIT|GROUP|TRAIN` + 번호)에
   걸리지 않습니다.  바로 옆 p35 는 `TYPICAL FOR UNIT 3-1 & 3-2` 라 x8 입니다.
   **어휘 문제가 아니라 유닛 표기 규칙 문제입니다.**
3. **p25·p26·p27·p28 은 배수를 읽었는데 쓰이지 않습니다** — 그 네 장이 분석 대상이 아니기 때문입니다
   (도면번호 형식 · 26회차 [11]).  넷 다 x8 입니다.

## 3. 네 프로젝트

| 프로젝트 | 쪽 | 배수를 낸 NOTES 장 | IDENTICAL | SIMILAR | SAME | TYPICAL | 실제로 쓰이나 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| AL NOUF1 | 58 | 26 | **26** | 0 | 0 | 0 | **아니오** — 범례표가 코드 일곱을 다 덮습니다 |
| SADARA | 9 | 0 | 0 | 0 | 0 | 0 | 아니오 — 노트에 그런 문장이 없습니다 |
| TC2 | 60 | 39 (행 있는 장 29) | 7 | 26 | 2 | 9 | **예** — 607행 중 404행 |
| UAD | 32 | 1 (p32) | 1 | 1 | 0 | 0 | **아니오** — p32 가 분석 대상이 아닙니다 |

원문:

```
AL NOUF1 p6  1. THIS P&ID IS FOR GROUP#10, CONFIGURATION IS IDENTICAL FOR GROUP#20.      (x2, 21장)
AL NOUF1     1. THIS P&ID IS IDENTICAL TO UNIT #11, #12, #21 AND #22.                     (x4, 5장)
UAD p32      3. P&ID PROVIDED IS ONLY FOR GT UNIT 11. IDENTICAL ARRANGEMENT IS APPLICABLE
                FOR GT UNIT 12,13 & 14.                                                   (x4 · 안 쓰임)
SADARA       — 넷 중 어느 낱말도 NOTES 에 없습니다 (TYPICAL 16회는 전부 범례의 `(TYPICAL)`)
```

**AL NOUF1 은 IDENTICAL 한 낱말만 씁니다 — SIMILAR 은 0회입니다.**  그래서 SIMILAR 을 어떻게 다루든
AL NOUF1 에는 닿을 길이 없고, 그 위에 범례표가 한 겹 더 막고 있습니다 (§4).

## 4. SIMILAR 을 IDENTICAL 과 같게 보면 — 계산으로만

**이미 같게 보고 있으므로 변화는 0 입니다.**  값어치를 재려면 반대로 빼 봐야 하므로 세 경우를 계산했습니다.
Q'ty 모형은 저장된 결과로 검산했습니다 — 모든 행이 `1 symbol` 이라 **Q'ty = Σ(그 장의 배수)** 이고,
TC2 는 `301x8 + 187x1 + 66x4 + 28x4 + 16x1 + 6x8 + 2x2 + 1x8 = 3047` 로 저장값과 정확히 같습니다.

| | AL NOUF1 | SADARA | TC2 | UAD |
| --- | ---: | ---: | ---: | ---: |
| **현행 (넷 다 같게)** | **1931** | 0 | **3047** | 149 |
| SIMILAR 제외 | 1931 | 0 | **1263** | 149 |
| IDENTICAL 만 | 1931 | 0 | **739** | 149 |

TC2 세부:

| | 현행 | SIMILAR 제외 | IDENTICAL 만 |
| --- | ---: | ---: | ---: |
| 노트로 배수를 받은 행 | 404 | 181 | 59 |
| **설정 폴백 행 (`MULTIPLIER_FROM_CONFIG`)** | **203** | **426** | 548 |
| Q'ty 빈칸 행 (유닛코드 31 · `MULTIPLIER_UNDEFINED`) | 0 | **223** | 237 |
| Q'ty | 3047 | 1263 | 739 |

즉 **TC2 Q'ty 3047 중 1784(58.5%)가 SIMILAR 한 낱말에 걸려 있습니다.**

**★ AL NOUF1 Q'ty 1931 은 세 경우 모두 불변이고, 이유는 둘입니다** (둘 중 하나만으로도 충분합니다):

1. **어휘가 닿지 않습니다** — 그 문서의 NOTES 는 `IDENTICAL` 만 쓰고 `SIMILAR` 은 0회입니다.
2. **구조가 막습니다** — `multipliers.source = LEGEND` 이고 표가 `00 10 11 12 20 21 22` 일곱을
   전부 갖는데 행에 실제로 나오는 코드는 `10`(591행) · `11`(101행) · `00`(345행) 셋뿐입니다.
   `undefined` 도 `borrowed` 도 아니므로 `_note_factor` 가 **노트를 보기 전에 돌아갑니다.**

## 5. 그 어휘를 도면에서 읽는 길이 있는가

**(가) 정의를 주는 문서는 하나도 없습니다.**  네 문서 전체에서 `MEANS · DENOTES · INDICATES ·
DEFINED · STANDS FOR · ABBREV` 중 하나와 네 낱말 중 하나가 **같은 줄에 있는 경우 0건**입니다.
범례의 약어표에도 없습니다.  더 나쁜 것은 **범례가 `TYPICAL` 을 아예 다른 뜻으로 쓴다**는 것입니다 —
`TYPICAL SYMBOL` · `PANEL (TYPICAL)` · `VALVE BODY WITH ACTUATOR-TYPICAL FOR MOTOR OPERATED VALVES`.
그러므로 **"범례가 정의하니 거기서 읽는다" 는 길은 없습니다.**

**(나) 그런데 낱말이 필요 없습니다.**  낱말 조건만 빼고 *번호 붙은 NOTES 문단이 유닛 표기를
둘 이상 열거하면 그 개수를 배수로 본다* 로 두고 다시 계산하면:

| | AL NOUF1 | SADARA | TC2 | UAD |
| --- | ---: | ---: | ---: | ---: |
| 어휘 없이 Q'ty | **1931** | **0** | **3047** | **149** |
| 판정이 달라진 장 | **0** | **0** | **0** | **0** |

전수로 더 직접 셌습니다 — **유닛 표기를 2개 이상 열거한 NOTES 문단 중 네 낱말이 하나도 없는 것은
네 문서에 0개**입니다 (AL NOUF1 26/26 · TC2 39/39 · UAD 1/1 · SADARA 0).
**지금 그 낱말 목록은 한 문단도 거르지 않습니다 — 판정은 전부 유닛 표기가 지고 있습니다.**

**(다) 그래서 두 갈래입니다 (실무 판단 — §14.3).**

* **갈래 ① 낱말 조건을 없앤다.**  §9 2 의 "외워둔 값" 하나가 줄고, 넷째·다섯째 도면이
  `ALIKE`·`REPEATED`·`MIRRORED` 라고 써도 그냥 됩니다.  네 문서 실측으로 지금 결과가 한 칸도
  안 움직입니다.  **위험**: `SEE P&ID FOR UNIT 3-1 AND 3-2` 처럼 배수와 무관하게 유닛 둘을
  열거한 NOTES 문단이 있으면 그것을 배수로 읽습니다 (네 문서에는 0건이지만 다음 문서는 모릅니다).
* **갈래 ② 지금대로 둔다.**  낱말이 안전장치로 남되, **지금은 아무 일도 하지 않는 안전장치**라는
  것을 알고 둡니다.

어느 쪽이든 **먼저 고칠 것은 낱말이 아니라 유닛 표기 규칙**입니다 — p33·p34 40행이
`UNIT` 이라는 낱말이 없다는 이유 하나로 x1 을 받고 있습니다 (§2-2).

## 6. 이 회차에 만든 도구

| 파일 | 무엇을 재나 |
| --- | --- |
| `spike/vocab_census.py` | 네 문서의 시트 전체 · NOTES 창 안 낱말 수 · 문단 원문 |
| `spike/vocab_definition.py` | 네 낱말이 든 **모든 줄**과 그 문맥 (정의 동사 검색) |
| `spike/vocab_what_if.py` | 어휘를 바꾸면 Q'ty · 폴백 행 · 빈칸이 어떻게 되나 (재실행 없음) |
| `spike/vocab_no_words.py` | 낱말 조건을 아예 뺀 경우 |
| `spike/vocab_risk.py` | 낱말 조건이 실제로 거르는 문단 수 |

기록: `out/round36_vocab_census.json` · `out/round36_defn.json` · `out/round36_what_if.json` ·
`out/round36_no_words.json`.
