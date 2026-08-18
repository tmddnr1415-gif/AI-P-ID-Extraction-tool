# 인수인계 — P&ID → 계기·밸브 리스트 추출

이 문서 하나로 다른 PC·다른 계정에서 이어받을 수 있게 쓴 것입니다. 코드보다 먼저
읽으세요. 상세 수치와 근거는 `README.md`, 설계 원본은 `docs/design.md` 입니다.

## 1. 지금 어디까지 와 있나

| 단계 | 상태 |
| --- | --- |
| Phase 0 검증 스파이크 (타이틀블록 · 계기 · 벤더마크 · 밸브) | 완료 |
| Phase 1 MVP (FastAPI + SQLite + 검토 UI + Excel 출력) | 완료 |
| 스코프 판정 · 출력 게이트 · 수정이력 수집 | 완료 |
| 배관 그래프 (Description 준비) | 완료했으나 **추적률 13.1%** 로 실용성 없음 |
| **Description 생성** | 진행 중 — 두 축 + 발주처 557행 유도 규칙으로 **F1 55.0 · 완전일치 21행** |

**확정 지표 (회귀 기준선 — 매 회차 재확인 필수)**

| 항목 | 값 |
| --- | --- |
| 계기 recall / precision | **97.0% / 87.0%** (검출 598 / Excel 536 / TP 520) |
| BFV recall / precision | **85.7% / 81.8%** |
| MOV recall / precision | **90.5% / 82.6%** |
| 액추에이터 | MOTOR 102 / PNEUMATIC 58 / HYDRAULIC 4 / **UNREAD 0** |
| 글리프 문자 | H 4 / M 32 |
| 행 수 | 892 (FIELD 748 / MOV 76 / PNEUMATIC 45 / BFV 23) |
| 분석 시간 | 58장 약 3분 40초 |
| 테스트 | 빠른 39 · UI 8 · slow 6 (전부 통과) |
| `fingerprint` | **be1abf03** |

**Description 지표 (2026-08 회차)**

| 조각 | 값 | 비고 |
| --- | --- | --- |
| 발주처 557행 대조 | 완전일치 **21** · 부분 497 · 미달 0 · 대응행 없음 39 | |
| 토큰 정밀도 / 재현율 / F1 | **51.8% / 58.6% / 55.0** | 직전 회차 43.9 / 58.0 / 50.0 |
| 변수어 | **99.0%** (501/506) | |
| 기기명 | **76.8%** (281/366) | |
| 순번 | **42.4%** (114/269) — 끝 58.3% / 중간 37.0% | 오류의 79% 는 주어 문제 |
| 위치어 | **28.5%** (45/158) — 오답 41 · 미부착 72 | |
| 중간 심볼 | **0%** (0/13) | p33 은 심볼로만 그림 |
| 등급 | CONFIRMED 596 · LOW 131 · PARTIAL 19 · NONE 144 · SKIP 2 | NONE 은 전부 수동 밸브 |
| 서로 다른 문장 | 430 | 발주처도 557행 중 110행(19.7%)이 같은 문장을 반복 |

`fingerprint` 는 엔진 판정 전체의 해시입니다. 검출을 바꾸지 않았는데 바뀌면 원인을
반드시 규명하세요 (보통 `needs_review` 문구나 `legend` 기록이 늘어난 경우입니다).

## 2. 진행 원칙 — 어기면 되돌려야 합니다

1. **범례 유도 우선.** 판정에 쓰는 값은 문서의 Symbol & Legend 시트에서 런타임에
   측정합니다. 코드에 치수를 박지 않습니다.
2. **임의값 금지.** "90pt 반경", "10pt 최소 런" 같은 값은 근거가 없으면 쓰지
   않습니다. 필요하면 그 문서에서 분포를 재고 백분위를 쓰되 분포를 함께 보고합니다.
3. **근거 없는 값 생성 금지.** 도면에 없는 낱말은 만들지 않습니다. 비워 두고 사유를
   남깁니다 (`NEEDS_REVIEW`, Remark, 근거 패널).
4. **회귀 확인 필수.** 위 표의 수치가 하나라도 움직이면 원인을 보고하고 되돌립니다.
5. **검출에 LLM 금지.** 심볼 검출·수량·스코프는 규칙만 씁니다. LLM 은 Description
   중간 서술 *선택*에만, 기본 꺼짐으로 존재합니다
   (`tests/test_description.py` 가 검출 모듈의 import 문을 검사해 강제).
6. **측정 정의 변경 금지.** 분모·대조 집합을 바꿔 수치를 좋게 만들지 않습니다.
7. **발주처 리스트는 검증 전용.** 실사용 입력은 PDF + 빈 양식뿐입니다
   (`PID_VERIFY_EXCEL` 로만 대조 모드가 켜집니다).

## 3. 실패한 접근과 이유 — 다시 시도하지 마세요

| 접근 | 결과 | 왜 |
| --- | --- | --- |
| 배관 그래프로 Description 근거 확보 | 추적 성공 **13.1%** | 페이지당 약 320조각으로 분절. 원인은 좌표 오차가 아니라 최소 런 16.97pt 미만 스터브가 버려지는 것. 낮추면 조각이 폭발하고 F1 개선은 +4.2pp 뿐 |
| 근접 텍스트 반경으로 중간 서술 수집 | 정밀도 57.3% → **17.6%** | 240pt 원 안에 도면번호·DN 치수·그리드 좌표·ASME 코드가 들어옴 |
| LLM 선택기로 중간 서술 선택 | 30행 중 **채택 4 / 보류 26** | 모델이 아니라 후보가 부족. 후보의 대부분이 옆 계기 태그나 배관 치수 |
| 범례 기기 형상으로 도면 기기 검출 | 펌프 **0개** 검출, 5×10 잡음 161건 | 단일 축척이 없음 (범례 40.5×38.5 ↔ p26 46.2×44.0, 비율 ×0.42~×2.00 산포) |
| 범례 STRAINER 형상으로 중간 심볼 검출 | 글자 외곽선만 매칭 | 같은 이유 |
| 기기 라벨을 노운 단위로 붙이기 (위치어를 기기 명사로 판단) | PI·TI 에 없는 SUCTION 이 붙음 | 위치어는 **기기가 아니라 계기 TYPE** 이 정함 (PIT 70.8% ↔ PI 6.3%) |
| 같은 베이스라인의 낱말 간격이 행간(11.8pt)보다 넓으면 라벨을 자르기 | 재현율 −4.3pp / 정밀도 +3.4pp, 완전일치 21→15 | `#10 ST HYDRAULIC OIL COOLER` 가 `HYDRAULIC` + `COOLER` 로 잘림. 나란히 인쇄된 두 라벨 병합 문제는 **미해결** |

**대신 통하는 것**: 기기는 **도면이 인쇄한 이름**으로 찾습니다(332건/47장). 문형과
낱말 규칙은 **발주처 557행에서 센 값**을 config 에 근거 수치와 함께 적습니다.

**국소 연결의 실측 한계 (이번 회차에 측정)**: 리드선 → 첫 배관 런까지는 788행 전부
성공합니다. 그러나 그 런이 기기까지 닿는 경우는 **44/890 (4.9%)** 이고, 그중 최근접
기기와 다른 답을 낸 것은 **7건**, F1 변화는 **0.0** 입니다. 라벨-런 간격 허용치를
문서에서 실측한 90분위 **48.4pt** 로 넓혀 7→44 로 늘린 뒤의 값입니다. 나머지 94% 는
기기까지 가는 길에 **엘보가 한 번 이상** 있어, 그래프 순회 없이는 닿지 않습니다
(순회는 금지 사항). 즉 국소 연결은 **규격대로 구현했고, 이 문서에서의 천장이 4.9%**
입니다. 나머지는 최근접 거리 폴백입니다.

## 4. 미해결 과제 (다음 단계 후보) — 우선순위 순

1. **주어(기기) 귀속이 남은 병목입니다.** 순번 오류 258건을 원인별로 분류하면
   **204건(79%)이 순번이 아니라 주어가 틀린 것**입니다 (정렬축·시작점 11건,
   수량주기 불일치 5건). 위치어 오류도 같은 원인입니다. 순번·위치어 로직을 더
   고쳐도 소용이 없고, **주어를 고쳐야 세 조각이 동시에 올라갑니다.**
   - 남은 수단: 나란히 인쇄된 두 라벨의 분리(§3 실패표 참고), 계통 접두어
     (AUX / GT) 를 계기 태그의 계통 코드와 대조하는 방법.
   - 금지: 전체 배관 그래프 순회, 최소 런 임계값 변경.
2. **UNIT 번호가 시트 코드와 다른 계통** — 스팀 도면은 한 장이 HRSG #11·#12 를
   함께 그리는데 우리는 시트의 unit code(#10) 를 씁니다. 발주처는 계기가 붙은
   HRSG 번호를 씁니다. 도면 안의 `#11` / `#12` 표기와 계기의 위치를 대조해야 합니다.
3. **경보 접미 (LEVEL HIGH HIGH / HIGH)** — LS 22행. 도면의 알람 표기에서 유도해야
   하며 아직 손대지 않았습니다.
4. **중간 심볼(SUCTION STRAINER)** — 발주처 13행, 전부 PDIT. 현재 정확도 **0/13**.
   도면이 낱말을 인쇄한 6장에서만 가능하고, 목표 도면 p33 은 심볼로만 그려 불가.
   config `description.between_symbol_types: [PDIT]` 로 **PDIT 외에는 아예 제안하지
   않게** 막아 뒀습니다 (그 전에는 PI·BALL·BUTTERFLY 에 붙어 전부 오답이었습니다).
5. **밸브 Description 144행** — 발주처 마스터 밸브 리스트가 없어 문형 기준이 없음.
   확인된 사실: CZH(MOV)·CZI(BFV) 리스트에는 **Description 열 자체가 없고**
   SYSTEM / UNIT NO. 열만 있습니다. 그리고 우리 144행은 전부 **수동 밸브**
   (GLOBE 68 · GATE 38 · BUTTERFLY 23 · BALL 13 · CHECK 2) 로, 두 리스트 어디에도
   없습니다. 즉 **NONE 은 결함이 아니라 정답**입니다.
4. **다중 신호 버블 102행** — 합산 여부가 발주처 확인 대기
   (`out/ls_bundle_question.md`, `config multi_signal_bundle.merge_quantity`).
5. **UNKNOWN 6종** (`out/valve_project_deps.md`) — Phase 3.
6. **Tag No.** — 도면이 `.....` 로 미부여. 발주처 규칙 필요.

## 5. 발주처 확인 대기 항목

| 문서 | 내용 |
| --- | --- |
| `out/description_question.md` | 기기 명명 규칙 · 위치 관계어 · UNIT 접두어 · A/B/C 순번 (각 항목이 몇 행을 채우는지 포함) |
| `out/ls_bundle_question.md` | 맞닿은 LSHH/LSH/LSL 34묶음 102버블의 물리 수량 |
| 마스터 밸브 리스트 | 밸브 Description 문형 기준 (미수령) |

## 6. 파일과 실행

**`data/` 규칙** (리포지터리에 없음 — `.gitignore` 대상)

| 파일 | 용도 |
| --- | --- |
| `data/pid_total.pdf` | 분석 대상 도면 |
| `data/CZE_Field_Instrument.xlsx` | FIELD 양식 + 검증 모드 대조본 |
| `data/CZI_Butterfly_Valve.xlsx` | BFV 양식 |
| `data/CZH_MOV_Gate_Globe.xlsx` | MOV 양식 |

양식은 **비어 있어도 됩니다** — 서식만 씁니다. 없으면 그 산출물은 사유와 함께
건너뜁니다.

**실행**

```bash
pip install -r requirements.txt
./run.sh                 # Linux/macOS — http://127.0.0.1:8000
start.bat                # Windows (포트/--no-reload/--verify 인자 지원)
PID_VERIFY_EXCEL=data/CZE_Field_Instrument.xlsx ./run.sh   # 검증 모드
```

**테스트**

```bash
pytest -q -m "not slow and not ui"    # 36건, 5초
pytest -q -m ui                       # 8건, 4분 (playwright + chromium 필요)
pytest -q -m slow                     # 전 문서 분석 포함, 각 4분
```

**회귀 스크립트**

```bash
python app/engine/detect_all.py --pdf data/pid_total.pdf --compare data/CZE_Field_Instrument.xlsx
python app/engine/detect_valves.py --report out/valve/report.md
```

## 7. 코드 지도

| 모듈 | 역할 |
| --- | --- |
| `app/engine/pidcache.py` | PDF 페이지 캐시. `segments()` 는 캐시 객체를 그대로 넘기므로 **제자리 수정 금지** |
| `app/engine/legend_rules.py` | 범례에서 치수 유도 (`Derived`: values/source/note/evidence) |
| `app/engine/detect_symbols.py` · `detect_all.py` | 계기 검출·스코프. **여기 손대면 회귀 필수** |
| `app/engine/detect_valves.py` | 밸브 몸체·액추에이터 |
| `app/engine/isa_table.py` | 범례 p3 ISA 문자표 런타임 파싱 |
| `app/engine/describe_equipment.py` | 기기 표 유도 · 도면 기기 라벨 검출 · 순번 |
| `app/engine/describe_candidates.py` | 두 축 후보 + 국소 연결 주어 판정 |
| `app/engine/describe.py` | 문형 조립 (config `description`) |
| `app/engine/describe_llm.py` | 중간 서술 선택기 (기본 꺼짐, 6개 제약 코드 강제) |
| `app/engine/pipe_graph.py` | 배관 그래프 — **Description 경로에서는 쓰지 않습니다** |
| `app/pipeline.py` | 오케스트레이션 + 등급/Remark |
| `app/db.py` · `app/main.py` · `app/static/` | 저장·API·검토 UI |
| `config/project_alnouf1.yaml` | PROJECT 종속값 전부. 각 항목에 근거 수치 주석 |

## 8. 다음 프롬프트를 쓸 때

- 목표 문장(발주처 실제 표기)을 먼저 제시하고, 조각별 현재 정확도를 근거로
  개선 대상을 지정하세요. 집계 지표만으로는 실무 가치가 보이지 않습니다.
- 새 규칙은 **범례에서 유도**하거나 **발주처 557행에서 센 값**이어야 합니다.
  어느 쪽도 아니면 "유도 불가"로 보고하게 하세요.
- 회귀 항목(2절 표)을 프롬프트에 그대로 넣어 매번 확인시키세요.
- 발주처 557행에서 이미 센 값(다시 세지 마세요):
  구두점 `.`/`(` **0회** · 위치어 부착률 PIT 70.8 / PDIT 67.3 / FS 100 / FIT 41.9 /
  FE 38.9 / TIT 32.0 / TI 11.9 / PI 6.3 / LIT·LS·LI 0 ·
  끝 순번 PIT 44 / TIT 36 / FIT 26 / PDIT 6 / LIT 5 / 나머지 0 ·
  같은 도면 안 문장 반복 110행(19.7%) · 중간 심볼 13행(전부 PDIT `SUCTION STRAINER`).
- 계기가 기기의 **위·아래**에 있을 때 발주처가 쓰는 낱말은 유도되지 않습니다:
  위 = 없음 60 / DISCHARGE 24 / SUCTION 12 / OUTLET 2, 아래 = 없음 115 / OUTLET 9 /
  INLET 6 / DISCHARGE 5. 다수는 **아무 낱말도 쓰지 않는 것**이므로 붙이지 않습니다.
