# 44회차 [C] — AL NOUF1 p48 (PORT DICKSON 양식 장) 확인만

43회차 [D] 가 "다른 프로젝트 이름의 장" 을 새 종류로 적어 두었다.  **고치지
않았다 · 엔진 코드 0줄 · 지문 `fb85b039` 그대로** (기준선 체인 A44 가 그것을
잰다).  근거는 43회차 최종 결과 json(`AL_NOUF1_A43.json`)과 p48 렌더
(`out/round44/9_캡처/p48_titleblock.png`)다.

## 1. 지금 어떻게 판정되나

| 항목 | 값 |
| --- | --- |
| 도면번호 | `D00P-00GHC10-M05-0002` · Rev **A1** (`FOR PROPOSAL · 10.MAY.2025`) · 회전 270 |
| 제목 | `P&ID FOR DEMINERALIZED WATER DISTRIBUTION SYSTEM (2/2)` |
| PROJECT NAME 칸 | **`PORT DICKSON 1400MW CCGT`** (EMPLOYER `PDP GEN TWO SDN BHD`) |
| `page_kind` | `PID` (타이틀블록은 정상으로 읽혔다 — `status OK`) |
| `analysis_scope` | **False** · `scope_reason = FOREIGN_PROJECT:PORT DICKSON 1400MW CCGT` |
| 행 | **0** (계기 · 밸브) — `targets` 에서 빠져 검출 자체를 안 한다 |

**판정하는 곳은 38회차가 아니다.**  38회차 [C] 는 "장 단위 양식 판정" 을
**만들지 않았다** (`docs/state_and_roadmap.md` §8 7번 — UAD p11~17 이 다중 양식이
아니라 획 글자였기 때문).  p48 을 가르는 것은 그보다 오래된 규칙
`pidcache._scope_by_project` 다 — **PROJECT NAME 칸의 다수결**: 58장 중 57장이
`AL NOUF1 PROJECT` 이고 1장이 다른 이름이면 그 1장은 범위 밖
(`FOREIGN_PROJECT:<이름>`).  이름을 읽는 칸은 `title_block.project_name_region`
(AL NOUF1 프로필 값 · 22회차부터 `rename_projects` 로 유도값을 다시 적용한다).

## 2. 양식이 다른가 — 아니다, **양식은 같고 프로젝트가 다르다**

렌더로 확인했다: 도면틀은 AL NOUF1 과 같은 Samsung C&T 양식(REV/DATE/
DESCRIPTION 이력 표 · EMPLOYER · TENDERER · PROJECT NAME · DRAWING TITLE ·
PROJECT DWG NO. · SHEET · REV)이고, 칸의 자리도 같아 타이틀블록 유도값이 그대로
읽힌다.  그래서 "다른 양식의 장" 이 아니라 **"같은 양식 · 다른 프로젝트의 장"**
이다 — 43회차의 이름 "다른 프로젝트 이름의 장" 이 맞고, "PORT DICKSON 양식" 은
틀린 이름이다 (이 문서에서 정정한다).

## 3. 58장 전수 — 다른 프로젝트 이름의 장은 몇 장인가

| PROJECT NAME | 장 |
| --- | ---: |
| `AL NOUF1 PROJECT` | **57** (PID 52 · LEGEND 4 · DRAWING_LIST 1) |
| `PORT DICKSON 1400MW CCGT` | **1** (p48) |

이름을 못 읽은 장 **0**.  즉 범위 밖은 p48 하나이고 규칙은 그 한 장에서만
발동한다.

## 4. 같이 드러난 사실 둘 (판단은 사용자 몫)

1. **p48 은 AL NOUF1 의 (2/2) 자리에 들어온 남의 장이다.**  p47 이
   `D00P-00GHC10-M05-0001 · DEMINERALIZED WATER DISTRIBUTION SYSTEM (1 OF 2)`
   (AL NOUF1 · Rev B) 이고 p48 이 같은 계통의 `(2/2)` 인데 프로젝트가 PORT
   DICKSON 이다.  **AL NOUF1 의 진짜 (2/2) 는 이 PDF 에 없다** — 도면 묶음의
   결락일 수 있다.  발주처 확인 항목 후보.
2. **30회차 [10] 의 "REV `A1` 이 한 장 있다" 가 이 장이다.**  `formats.revision`
   유도값 `^[A-Z]$` 가 A1 을 못 받는데 프로필이 지켰다고 적었던 그 장이
   **범위 밖 장**이다.  즉 범위 안 57장의 REV 는 전부 한 글자이고, 유도값이
   실제 대상 장에서는 틀리지 않는다 — 다만 축3 개정 지표(58/58)가 p48 을
   분모에 넣는지는 아래 5 를 보라.

## 5. 축3 와 p48 — **실측: 한 칸도 안 움직인다**

`spike/identification.py` 는 `page_kind == "PID"` 인 장 전부를 `태그→행` 의
분모로 쓰므로 p48 도 들어간다.  43회차 결과 json 으로 p48 을 분모에서 뺀
채점을 같은 함수(`identification.measure`)로 다시 재 보았다:

| 지표 | p48 포함 (기준선) | p48 제외 |
| --- | --- | --- |
| 도면번호 | 58/58 | 58/58 |
| 개정 | 58/58 | 58/58 |
| 태그→행 | 247/272 | **247/272** |
| 수량 · 심볼판정 · 파라미터 | 1037/1037 · 1037/1206 · 30/32 | 같음 |
| 총점 | 95.1 | **95.1** |

p48 은 도면 영역 안에 앵커 낱말이 **0** 이라(회전 270 장 · 검출을 안 한 장)
분모에 기여하지 않는다.  즉 축3 정의를 바꿀 이유도, 바꾸지 않아 손해 보는
것도 없다 — **측정 정의 불변** (§2.2).

## 6. 고치지 않은 것 · 다음 회차 후보

* 규칙(다수결)은 옳게 동작한다.  고칠 것이 없고, 있다면 **화면**이다 — 첫
  화면·완료 화면이 "범위 밖 1장(다른 프로젝트: PORT DICKSON …)" 을 말하는지
  확인 대상 (`page-note` 는 이미 `분석 제외: FOREIGN_PROJECT:…` 를 쓴다 —
  원문 그대로라 한국어 문장은 `stageWords` 류 갈래가 없다).
* 다수결은 **두 프로젝트가 반반이면** 임의로 하나를 고른다 (`max`).  이 문서에는
  그런 경우가 없고, 생기면 사람에게 물어야 한다 — 규칙 후보로만 적는다.
