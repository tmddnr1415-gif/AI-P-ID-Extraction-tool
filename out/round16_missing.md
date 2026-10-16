# 16회차 [C] — 미검출 6건 원인 규명

**이 회차에서는 고치지 않았다.**  코드 변경 0.  17회차의 입력이다.

측정 조건은 파이프라인과 같다 — `pipeline._fit_layout(pages)` ·
`dv.derive_layout(pages)` · `dv.analyse_all(...)`(글리프 문자 해독 포함,
`letters={'M': 32, 'H': 4}`).  **이 조건을 맞추기 전에 잰 첫 표는 틀렸다**:
기본 `ValveLayout` 으로 재면 공압 액추에이터가 하나도 안 잡혀
(`PNEUMATIC 0`) XV·TCV·PCV·FCV 가 전부 미검출로 보인다.  실제로는
**XV 12행 · TCV 8행 · PCV 2행 · FCV 2행 · NRV 1행이 이미 나가고 있다.**
스스로 뒤집은 판단이므로 그대로 적는다.

## 0. 답 — 여섯이 하나로 묶이는가

**묶인다.  하나의 문턱이 100건 중 89건을 설명한다.**

```
deliverable_class(body)  (app/engine/detect_valves.py:150)
    if body.actuator in ("NONE", "UNREAD"): return CLASS_EXCLUDED
```

산출물이 되려면 **몸체 자체가 아니라 스템 위의 액추에이터**가 읽혀야 한다.
전 도면 밸브 몸체 **2,821개 중 2,676개(94.9%)가 `actuator=NONE`** 이고,
그 몸체는 어느 산출물에도 담기지 않는다.  10회차 [D] 의 NRV
(CHECK 몸체 264개 중 261개가 `actuator=NONE`) 와 **같은 문턱**이다.

태그가 붙은 밸브 177건 중 행이 되지 않은 것은 **100건**이고 원인은 셋뿐이다.

| 원인 | 건수 | 무엇인가 |
| --- | ---: | --- |
| ① 액추에이터 없음 (`NONE`) | **89** | 스템 위에 아무 심볼도 안 읽혔다.  자기작동(PSV·PRV·BPRV)은 **정의상** 그렇고, 나머지는 읽기 실패다 |
| ② 몸체 종류를 세 산출물이 안 담음 | **1** | p8 의 MOV — 몸체가 `DIAPHRAGM` 으로 읽혔다 (§2) |
| ③ 태그에 몸체가 안 붙음 | **10** | `tag_reach` 안에 아직 안 물린 몸체가 없다 (PSV 9 · PCV 1) |

②는 별건처럼 보이지만 **원인은 [B] 의 17장과 같다 — 개정 클라우드의
빨간 호**다 (§2).  즉 실질적으로 **두 가지**다: 액추에이터 판독과 빨간 덧그림.

## 1. 여섯 건 각각

### 2장 — p8 `D00P-10LBC50-M05-0001` 의 MOV

p8 의 MOV 태그는 **5개이고 4개는 이미 행이다** (GATE/MOTOR 1 · GLOBE/MOTOR 3).
행이 안 된 하나는 버블 `[918.1, 620.8, 986.0, 643.4]` 이고,

```
kind = DIAPHRAGM   actuator = MOTOR   evidence: waist = arc_above, bars = 3
```

즉 **액추에이터(M)는 읽혔다.**  몸체 종류가 틀렸다.  `deliverable_class` 는
`MOTOR` 를 `GATE / GLOBE / BALL` 에서만 MOV 로 보내므로 DIAPHRAGM 은
`CLASS_EXCLUDED` 로 떨어진다.

**왜 DIAPHRAGM 인가** — 몸체 위 6.0pt 안에 호가 있으면 다이어프램 돔으로 본다
(`arc_above`).  그 자리의 path 를 그대로 읽으면:

```
몸체 rect          [901.0, 669.7, 918.0, 679.6]
그 위의 호 6개     y 662.0~664.2   color = (1.0, 0.0, 0.0)   ← 빨강
M 원               [902.4, 640.6, 916.6, 654.8]  color = (0,0,0)
```

빨간 호 여섯 개는 **개정 클라우드**다 (렌더로 확인).  도면 자신의 잉크가
아니라 위에 덧그린 표기이고, 이것이 몸체 종류를 바꿔 놓았다.
**[B] 의 피드백 17장(별표 없는데 VENDOR)과 같은 뿌리**이며, 이번 회차에
계기 쪽에는 잉크 걸림을 넣었고 **밸브 쪽(`detect_valves`)에는 넣지 않았다.**

### 6장 — p10 XV

p10 의 XV 태그는 **6개이고 3개는 이미 행이다** (`GLOBE/PNEUMATIC → XV`,
PNEUMATIC 탭).  행이 안 된 3개는 전부

```
CHECK / NONE  →  EXCLUDED      버블 [640.7, 254.7 · 750.6 · 1246.6]
```

범례 p4 가 그 심볼을 뭐라고 부르는지 그대로 옮기면
`XV OR NRV` · `2. PNEUMATIC SHUT-OFF VALVE TYPICAL/PNEUMATIC NON-RETURN
VALVE TYPICAL` 이다.  즉 **공압 논리턴 밸브**인데 스템 위 공압 심볼이
읽히지 않아 `NONE` 이 됐다.  10회차 [D] 의 NRV 와 같은 자리다.
전 도면 XV 태그 21건 중 **행 12 · 미행 9**(CHECK/NONE 6 · GLOBE/NONE 3).

### 7장 — PCV

전 도면 PCV 태그 **6건 — 행 2 · 미행 4.**

| 장 | 몸체/액추에이터 | 결말 |
| --- | --- | --- |
| p7 | GLOBE/PNEUMATIC | **행** (PNEUMATIC 탭) |
| p28 | GLOBE/PNEUMATIC | **행** |
| p7 | GATE/NONE | 탈락 ① |
| p21 | GLOBE/NONE | 탈락 ① |
| p33 | GATE/NONE | 탈락 ① |
| p12 | — | 탈락 ③ 태그에 몸체가 안 붙음 |

범례 p3 의 ISA 표가 `P` 행 `CONTROL` 칸에 `PCV` 를 두고, 범례 p4 는
`1. PNEUMATIC CONTROL VALVE DETAIL` · `3. MODULATING` 옆에 PCV 를 그린다.
**정의는 있고, 갈리는 것은 그 장이 액추에이터를 그렸는가뿐이다.**

### 10장 — PRV

전 도면 PRV 태그 **1건**(p17 `D00P-10LCA10-M05-0002`, 버블
`[1220.2, 788.9, 1288.1, 811.5]`) · `GATE/NONE` · 탈락 ①.
BPRV 도 **1건**(p14) · `GATE/NONE` · 탈락 ①.

범례 p3 는 `PRV  S  PRESSURE RELIEF` · `BPRV  BACKPRESSURE` 를
**자기작동(self-actuated) 열**에 둔다.  자기작동 밸브는 스템 위에
액추에이터가 없는 것이 정상이므로, ①은 이 두 건에서 **판독 실패가 아니라
정의상 그렇다.**  그러므로 §12 의 "PRV 와 PSV 를 나누는 기준은 도면·범례에서
유도 불가" 와 직접 이어진다 — 나눌 기준 이전에 **담을 산출물이 없다**
(세 탭은 MOV · BFV · PNEUMATIC 뿐이고 CZF 는 미수령).
PSV 도 같다: 태그 68건이 전부 `NONE`(59) 또는 몸체 미부착(9)이다.

### 11장 — FCV

전 도면 FCV 태그 **6건 — 행 2 · 미행 4.**

| 장 | 몸체/액추에이터 | 결말 |
| --- | --- | --- |
| p21 ×2 | GLOBE/PNEUMATIC | **행** |
| p16 | GATE/NONE | 탈락 ① |
| p21 | CHECK/NONE | 탈락 ① |
| p21 ×2 | GLOBE/NONE | 탈락 ① |

범례 p3 의 `F` 행 `CONTROL` 칸이 `FCV` 다.

### 12장 — p20 `D00P-11LAB00-M05-0001`

**p20 은 38행을 낸다** (PIT 13 · FIT 8 · TIT 6 · FE 4 · MOV 3 · PDIT 2 · RO 2).
그 장에서 행이 안 된 밸브 태그는 셋이다.

| 태그 | 몸체/액추에이터 | 원인 |
| --- | --- | --- |
| PSV | CHECK/NONE | ① (자기작동) |
| PSV | GLOBE/NONE | ① (자기작동) |
| MOV | GLOBE/NONE | ① — 다만 **그 태그는 엉뚱한 몸체에 붙었다** |

마지막 건이 이 장의 진짜 이야기다.  MOV 버블
`[1468.4, 641.0, 1536.4, 663.6]` 이 가리키는 실물은 M 이 달린 보디
`[1451.4, 689.9, 1468.4, 699.8]`(`GATE/MOTOR`)이고 **그 몸체는 MOV 행으로
이미 나가 있다.**  그런데 `attach_tags` 는 **가장 가까운 몸체**에 태그를
주므로(리더선을 따라가지 않는다), 51.0pt 떨어진 수동 GLOBE 가 61.3pt
떨어진 진짜 몸체를 이겼다.  결과는 **행 하나가 태그를 잃고, 수동 밸브 하나가
남의 태그를 받아 탈락**이다.

**⚠ 피드백 12장은 무엇이 안 나왔는지 심볼을 지정하지 않았다.**
p20 에서 우리가 내지 않는 것은 위 셋과 자기작동 밸브들이며, 어느 것을
말한 것인지는 **실무 판단**이라 스스로 정하지 않았다 (§14.3).
17회차 프롬프트에서 심볼을 지정해 주면 그것을 목표로 잡는다.

## 2. 범례에 정의가 있는가 — 원문

| 심볼 | 범례 원문 (그 장에서 읽은 낱말 그대로) | 쪽 |
| --- | --- | --- |
| MOV | `1. ON-OFF MOV TYPE TYPICAL` · `2. INCHING` · `3. MODULATING` | p4 |
| XV · NRV | `XV OR NRV` · `2. PNEUMATIC SHUT-OFF VALVE TYPICAL/PNEUMATIC NON-RETURN VALVE TYPICAL` · `HV XV : SHUT-OFF VALVE` | p4 |
| PCV | `1. PNEUMATIC CONTROL VALVE DETAIL/PNEUMATIC NON-RETURN VALVE DETAIL` · ISA `P` 행 `PCV` | p4 · p3 |
| FCV · TCV · LCV | ISA 표 `F`/`T`/`L` 행의 `CONTROL` 칸 | p3 |
| PSV · PRV · BPRV | `PSV ... VACUUM RELIEF` · `PRV S PRESSURE RELIEF` · `BPRV BACKPRESSURE` — **자기작동 열** | p3 |
| HV | `HAND CONTROL VALVE IN SIGNAL LINE` · `TWO-WAY HAND CONTROL VALVE` | p4 |

**여섯 심볼 모두 범례에 정의가 있다.**  없는 것은 정의가 아니라
**그것을 담을 산출물**이고(세 탭 + CZF 미수령), 그 앞에 액추에이터 판독이
막고 있다.

## 3. 같은 종류가 다른 장에서는 나오는가 — 58장 전수

| 태그 | 도면 낱말 | 태그 붙은 밸브 | 행이 됨 | 안 됨 |
| --- | ---: | ---: | ---: | ---: |
| MOV | 67회 / 19장 | 53 | **48** | 5 |
| PSV | 70회 / 19장 | 68 | 0 | **68** |
| XV | 21회 / 5장 | 21 | 12 | 9 |
| TCV | 14회 / 6장 | 13 | 8 | 5 |
| HV | 10회 / 3장 | 4 | 4 | 0 |
| PCV | 6회 / 5장 | 6 | 2 | 4 |
| FCV | 6회 / 2장 | 6 | 2 | 4 |
| LCV | 3회 / 2장 | 3 | 0 | 3 |
| NRV | 2회 / 2장 | 1 | 1 | 0 |
| PRV | 1회 / 1장 | 1 | 0 | 1 |
| BPRV | 1회 / 1장 | 1 | 0 | 1 |
| CV | 2회 / 1장 | 0 | — | — |

**검출 자체는 된다.**  이 낱말들은 전부 `detect_symbols` 의 기하 검증을
통과해 `Detection` 이 되고, `category=VALVE · included=False ·
exclude_rule=VALVE` 로 FIELD 목록에서 빠져 밸브 산출물로 넘어간다
(`anchors.not_field` 는 비어 있어 여기서 걸리는 것은 **없다**).
탈락은 전부 그 다음 단계, `deliverable_class` 에서 일어난다.

## 4. 17회차가 짧아지는 지점

1. **①(89건)은 액추에이터 판독 하나다.**  자기작동(PSV 68 · PRV 1 · BPRV 1)
   70건은 "판독 실패"가 아니라 **담을 산출물이 없는 것**이므로, 발주처가
   자기작동 밸브 리스트(CZF 계열)를 줄 때까지는 규칙 문제가 아니다.
   나머지 19건이 실제 판독 대상이다.
2. **②는 이번 회차에 계기 쪽에 넣은 잉크 개념을 밸브 쪽에 옮기는 일**이다.
   `detect_valves` 는 `_glyph_clusters` 를 쓰지 않으므로 이번 변경의 영향을
   전혀 받지 않았다 (밸브 행 144 · 지문의 밸브 칸 전부 불변).
3. **③(10건)은 `attach_tags` 의 최근접 규칙**이고, p20 이 그 반례다 —
   더 가까운 몸체가 정답이 아닐 수 있다.  **반경을 늘리면 더 나빠진다**
   (더 많은 남의 몸체가 후보가 된다).  리더선을 따라가는 것은 §2.2 순회
   금지에 걸리므로, 고치려면 다른 근거가 필요하다.
