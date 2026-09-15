# [D-1] 유닛 표기 전수 — 네 프로젝트 NOTES 의 숫자 꼴 · 오검 위험 · 도면에서 읽는 길

도구 `spike/unit_token_survey.py` · `spike/unit_format_probe.py` (읽기 전용 · 번호 붙은 NOTES 문단만).
꼴 표기: `D` = 한 자리 · `DD` = 두 자리 · `D-D` = 붙임표 · `#DD`/`NO.DD` = 접두.  "머리낱말" = 바로 앞에 GROUP/UNIT/TRAIN.

## 1. 어떤 꼴이 실제로 쓰이는가 (원문 인용)

### TC2 — 번호 문단 414 · 도면번호 유닛코드 {'31': 262, '00': 345}
| 꼴 | 머리낱말 | 문단 | 건 | 원문 |
|---|---|---|---:|---|
| `D` | 없음 | 아님 | 365 | p6: …1. REFER TO SYMBOL & LEGEND DWG… |
| `D` | 없음 | 유닛 문단 | 309 | p6: …2. THIS P&ID IS BASED ON CONFIG… |
| `D-D` | 있음 | 유닛 문단 | 225 | p6: …1. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLI… |
| `DD` | 없음 | 아님 | 117 | p6: …SED IN ANY WAY DETRIMENTAL TO THE COMPANY. A 26.08.21 FOR INTERNAL USE REV. D… |
| `DD` | 없음 | 유닛 문단 | 62 | p7: …SED IN ANY WAY DETRIMENTAL TO THE COMPANY. A 26.08.21 FOR INTERNAL USE REV. D… |
| `D-D` | 없음 | 유닛 문단 | 47 | p23: …1. THIS P&ID IS APPLICABLE FOR UNIT 3-1,3-2 AND IS TYPICAL FOR UNITS 4-1,… |
| `D-D` | 없음 | 아님 | 8 | p33: …5. THE P & ID IS TYPICAL FOR 3-1 & 3-2 SIMILAR P & ID SHALL BE… |
| `NO.D-D` | 있음 | 유닛 문단 | 4 | p31: …1. THIS P&ID IS IDENTICAL FOR UNIT NO. 5-1, 5-2 & UNIT NO. 6-1, 6-2.… |
| `D` | 있음 | 유닛 문단 | 2 | p30: …9. THIS P&ID IS APPLICABLE FOR UNIT 3 & 4, SAME WILL BE APPLICABLE … |
| `NO.D` | 있음 | 유닛 문단 | 1 | p29: …7. COLD VENT STACK IS IDENTICAL FOR UNIT NO. 5&6. FOR INTERNAL USE THIS DRAW… |

### AL NOUF1 — 번호 문단 271 · 승수표 {'00': 1, '10': 2, '11': 4, '12': 4, '20': 2, '21': 4, '22': 4} · 도면번호 유닛코드 {'10': 591, '11': 101, '00': 345}
| 꼴 | 머리낱말 | 문단 | 건 | 원문 |
|---|---|---|---:|---|
| `D` | 없음 | 아님 | 259 | p2: …1. THIS DRAWING IS PREPARED FOR… |
| `DD` | 있음 | 유닛 문단 | 50 | p6: …1. THIS P&ID IS FOR GROUP#10, CONFIGURATION IS IDENTICAL F… |
| `D` | 없음 | 유닛 문단 | 28 | p6: …1. THIS P&ID IS FOR GROUP#10, C… |
| `DD` | 없음 | 유닛 문단 | 8 | p13: …T#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22.… |
| `#DD` | 없음 | 아님 | 8 | p25: …1. THE FUEL GAS SUPPLY SYSTEM P&ID FOR GT #11 IS INDENTICAL TO GT #12, #21 … |
| `DD` | 없음 | 아님 | 4 | p16: …10. LOCATION OF RUTURE DISC WILL… |
| `#DD` | 없음 | 유닛 문단 | 3 | p15: …1. THIS P&ID IS IDENTICAL TO UNIT #11, #12, #21 AND #22. FOR INTERNAL US… |
| `#DD` | 있음 | 유닛 문단 | 1 | p15: …1. THIS P&ID IS IDENTICAL TO UNIT #11, #12, #21 AND #22. FOR INTERN… |

### UAD — 번호 문단 313 · 도면번호 유닛코드 {'00': 149}
| 꼴 | 머리낱말 | 문단 | 건 | 원문 |
|---|---|---|---:|---|
| `D` | 없음 | 아님 | 960 | p4: … FOR CONSTRUCTION W.H.PARK I.S.LEE Y.H.JEONG 2 FOR CONSTRUCTION M.H.KIM Y.H.… |
| `DD` | 없음 | 아님 | 140 | p4: …22.MAY.2025 FOR CONSTRUCTION W.H… |
| `DD` | 없음 | 유닛 문단 | 7 | p10: …ATION SHALL BE TAKEN FOR OTHER UNITS 00EKH02/03/04/05AN001 PIPING TAGGING OF … |
| `D` | 없음 | 유닛 문단 | 3 | p10: …3. THE INTERCONNECTION DETAILS … |
| `DD` | 있음 | 유닛 문단 | 2 | p32: …3. P&ID PROVIDED IS ONLY FOR GT UNIT 11. IDENTICAL ARRANGEMENT IS APP… |

### SADARA — 번호 문단 55 · 승수표 {'00': 1} · 도면번호 유닛코드 {'10': 82}
| 꼴 | 머리낱말 | 문단 | 건 | 원문 |
|---|---|---|---:|---|
| `D` | 없음 | 아님 | 61 | p1: …T DWG NO. SHEET REV. 1A46-00GEN00-M05-0001 A 1/1 REF. DRAWING NO. PROJECT NO… |
| `DD` | 없음 | 아님 | 25 | p1: …19.MAR.2026 FOR PROPOSAL HM KANG… |

읽는 법 — **한 자리 맨 숫자(`D`)의 대부분은 문단 번호(`1.`·`2.`)이고, 두 자리 맨 숫자(`DD`)는 날짜·REV·문단 번호 10 이상**이다.
유닛은 세 꼴로만 인쇄된다: TC2 `D-D`(3-1) · AL NOUF1 `#DD`(#10) · UAD `UNIT DD`(GT UNIT 11).  SADARA 는 NOTES 에 유닛 표기가 없다.

## 2. 머리낱말이 있는 경우와 없는 경우

| 문서 | 낱말 뒤 | 낱말 없이 (유닛 문단 안 — 꼬리) | 낱말 없이 (유닛 문단 밖) |
|---|---:|---:|---|
| TC2 `D-D` | 225 | 47 (`UNITS 4-1, 4-2, 5-1 …` 꼬리) | **8 = p33·p34** (`TYPICAL FOR 3-1 & 3-2 … FOR 4-1 & 4-2`) |
| AL NOUF1 `#DD` | 1 (`UNIT #11`) | 3 (`#12, #21 AND #22` 꼬리) | **8 = p25** (`GT #11 IS INDENTICAL TO GT #12, #21 AND GT #22` — 머리가 `GT`) |
| AL NOUF1 `DD` (뒤 `#`) | 50 (`GROUP#10`) | 8 (`UNIT#12,21,22` 꼬리) | 4 = `10. LOCATION OF …` **문단 번호** |
| UAD `DD` | 2 (`GT UNIT 11`) | 7 (`00EKH02/03/04/05AN001` KKS 태그 조각) | — |

**지금 놓치는 것은 TC2 p33·p34(40행)와 AL NOUF1 p25(범례가 답하므로 영향 0)** 이고, 원인은 어휘가 아니라 `_unit_tokens` 가
**낱말 바로 뒤의 표기만** 줍기 때문이다.

## 3. 오검 위험 — 숫자인데 유닛이 아닌 것 (유닛 문단 밖 · 상위)

TC2:
| 앞¦숫자¦뒤 | 건 | 원문 |
|---|---:|---|
| `¦N¦. REFER` | 54 | p6: …1. REFER TO SYMBOL & LEGEND DWG… |
| `¦N¦. LOCATI` | 53 | p6: …3. LOCATION AND NUMBER OF HIGH … |
| `¦N¦. THIS D` | 52 | p6: …4. THIS DRAWING IS PREPARED FOR… |
| `¦N¦.N.N F` | 31 | p13: …26.08.21 FOR INTERNAL USE A REV.… |
| `N.¦N¦.N FOR` | 31 | p13: …26.08.21 FOR INTERNAL USE A REV. DA… |
| `N.N.¦N¦ FOR INT` | 31 | p13: …26.08.21 FOR INTERNAL USE A REV. DATE … |
| `¦N¦. DELETE` | 18 | p15: …6. DELETED.… |
| `SYSTEM (¦N¦/N) PROJ` | 16 | p25: … TITLE P&ID FOR CLOSED COOLING WATER SYSTEM (1/4) PROJECT DWG NO. SHEET REV.… |

AL NOUF1:
| 앞¦숫자¦뒤 | 건 | 원문 |
|---|---:|---|
| `¦N¦. THIS D` | 57 | p2: …1. THIS DRAWING IS PREPARED FOR… |
| `¦N¦. REFER` | 55 | p6: …1. REFER TO SYMBOL & LEGEND DWG… |
| `¦N¦. LOCATI` | 14 | p16: …10. LOCATION OF RUTURE DISC WILL… |
| `N-N~¦N¦` | 11 | p7: …MBOL & LEGEND DWG. NO. D00P-00GEN00-M05-0002~3… |
| `¦N¦. DRAIN` | 8 | p6: …2. DRAIN POT AND WARM-UP LINE S… |
| `¦N¦. MINIMU` | 6 | p17: …4. MINIMUM DISTANCE OR STRAIGHT… |

UAD:
| 앞¦숫자¦뒤 | 건 | 원문 |
|---|---:|---|
| `¦N¦.N P&ID` | 129 | p6: …1.1 P&ID FOR SYMBOL & LEGEND (1… |
| `N.¦N¦ P&ID FO` | 115 | p6: …1.1 P&ID FOR SYMBOL & LEGEND (1/4… |
| `LEGEND (¦N¦/N) - NA` | 38 | p6: …1.1 P&ID FOR SYMBOL & LEGEND (1/4) - 1A5J-00GEN00-M05-0002… |
| `GEND (N/¦N¦) - NANJ` | 38 | p6: …1.1 P&ID FOR SYMBOL & LEGEND (1/4) - 1A5J-00GEN00-M05-0002… |
| `LEGEND (¦N¦/N)- NAN` | 31 | p6: …1.3 P&ID FOR SYMBOL & LEGEND (3/4)- 1A5J-00GEN00-M05-0004… |
| `GEND (N/¦N¦)- NANJ-` | 31 | p6: …1.3 P&ID FOR SYMBOL & LEGEND (3/4)- 1A5J-00GEN00-M05-0004… |

**맨 숫자를 유닛으로 보면 이것들이 전부 잡힌다** — 문단 번호 · 날짜 `26.08.21` · `LEGEND (1/2)` · 도면번호 참조 `00GEN00-M05-0002~0005` ·
`20 DIAMETERS` · `ONE (1)`.  그래서 **맨 숫자는 절대 유닛이 아니다**가 이 항목의 첫 규칙이다.
반대로 **표식이 붙은 꼴**(`D-D` · `#DD`)은 네 문서의 번호 문단에서 유닛 아닌 것에 쓰인 예가 **0건**이다
(`D-D` 8건은 전부 p33·p34 의 유닛, `#DD` 8건은 전부 p25 의 GT 유닛).  범위꼴 `D-D~D`(AL NOUF1 11건)는 도면번호
참조 `M05-0002~3` 이고 `~` 는 `range_words` 가 이미 거른다.

## 4. 그 도면에서 읽는 길 — 있다

장마다 도면번호의 유닛 자리(두 자리, `extract_titleblocks` 가 이미 읽는다)가 있고, **그 장의 NOTES 가 유닛 낱말 뒤에 자기 코드를
어떤 꼴로 적는지**를 세면 문서마다 꼴이 나온다 (`spike/unit_format_probe.py`):

| 문서 | 코드 | NOTES 가 적은 꼴 | 장 | 원문 |
|---|---|---|---:|---|
| AL NOUF1  10 | `#DD` | 20 | p6: 1. THIS P&ID IS FOR GROUP#10, CONFIGURATION IS IDENTICAL FOR GROUP#20. |
| AL NOUF1  11 | `#DD` | 5 | p13: 1. THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22. |
| AL NOUF1  10 | `bare DD` | 1 | p16: 10. LOCATION OF RUTURE DISC WILL BE DECIDED BASED ON OEM'S EQUIPMENT. |
| TC2  00 | `NO.DD` | 26 | p23: 1. REFER TO SYMBOL & LEGEND DWG.NO. 00GEN00-M05-0002~0005. |
| TC2  31 | `D-D` | 18 | p6: 1. THIS P&ID IS FOR UNIT 3-1. AND, SIMILAR SCHEME IS APPLICABLE TO UNIT 3-2, UNIT 4-1, |
| SADARA  10 | `bare DD` | 1 | p7: 10. THE WARM-UP LINE WILL BE DESIGNED AS SYMMETRICAL. |
| UAD  — | — | 0 | (NOTES 가 자기 코드를 적지 않는다) |

* **AL NOUF1** — 코드 `10`·`11` 을 `GROUP#10`·`UNIT#11` 로 25장.  꼴 `#DD`.  (`bare DD` 1건은 `10. LOCATION …` 문단 번호 — 맨 숫자를
  배우면 안 되는 증거)
* **TC2** — 코드 `31` 을 `UNIT 3-1` 로 18장.  꼴 `D-D`.  코드 `00` 의 `NO.DD` 26장은 `DWG.NO. 00GEN00` 도면번호 참조라 **유닛 낱말 뒤가
  아니다** → 배우지 않는다 (낱말 뒤로 한정하는 이유).
* **UAD** — 코드 `00`(플랜트 공통)이라 NOTES 가 자기 코드를 유닛으로 적지 않는다 → 꼴 없음 → 낱말 뒤 표기만 (지금과 같음).
* **SADARA** — NOTES 에 유닛 표기 없음 → 꼴 없음.

그러므로 **꼴을 코드에 나열할 필요가 없다.**  규칙은 셋이고 값이 아니다:
① 유닛 낱말 뒤에 **그 장의 코드**가 인쇄된 꼴을 문서에서 배운다 (두 장 이상 — 18회차 규칙)
② 배운 꼴이면 같은 번호 문단 안에서 낱말 없이 나와도 유닛이다
③ **맨 숫자는 배우지 않는다** — 표식(`#` · `NO.` · 붙임표)이 있는 꼴만 (거절 규칙 · §3 의 오검 목록이 근거)

## 5. p33·p34 는 몇 벌인가

원문: `5. THE P & ID IS TYPICAL FOR 3-1 & 3-2 SIMILAR P & ID SHALL BE APPLICABLE FOR 4-1 & 4-2.` (p34 는 5-1·5-2 / 6-1·6-2)
같은 문서의 p35: `5. THE P & ID IS TYPICAL FOR UNIT 3-1 & 3-2, SIMILAR P & ID IS APPLICABLE FOR 4-1 & 4-2, 5-1 & 5-2 AND 6-1 & 6-2.` → **엔진이 이미 x8**.
같은 문장 꼴을 같은 규칙(열거된 표기를 센다 · 해석하지 않는다 — 27회차)으로 세면 p33·p34 는 **4** 다.  "SIMILAR P&ID 가 같은 계기를
갖는가" 라는 의심은 p35 와 SIMILAR 23장에 이미 똑같이 걸려 있는 것이라 이 두 장만의 문제가 아니다 → **4 로 두되 실무 판단 목록에 올린다**
(SIMILAR 장 전체와 한 묶음으로).

## 6. 예측 (D-2 를 넣으면)

TC2 p33·p34 40행 x1 → x4: **Q'ty 3047 → 3167** · `MULTIPLIER_FROM_CONFIG` 203 → **163** · 지문 `c0a2d29d` → 움직임 (qty 열).
AL NOUF1 — 범례가 답하므로 노트를 보기 전에 돌아간다 → **불변**.  SADARA·UAD — 배운 꼴 없음 → **불변**.
