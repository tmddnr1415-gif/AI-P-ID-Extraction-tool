# RULE_CHANGELOG — Ball Valve 검토 규칙 변경 기록

규칙(Rule ID)의 판정 논리가 바뀔 때마다 여기에 한 줄씩 남긴다. 변경은 도구 안의 **Rule 변경 기록**(Rule Performance 화면) 절차를 거친다:
① 기존 규칙과 변경안 비교 → ② 변경 이유 → ③ 실자료 Regression(`valve_eval.py --check` · `valve_snapshot_diff.py`) → ④ Simulation(`valve_sim` · `valve_mutate` · `valve_rev_sim`)
→ ⑤ Engineer 승인 → ⑥ 개발 쪽이 코드 변경 후 `app/valve/checks.py` 의 `RULE_VERSION` 을 올리고 여기에 기록 → 도구에서 '적용' 표시.
엔지니어의 결정(Dismissed 등)이 규칙을 자동으로 바꾸지 않는다 — 판정 코드는 결정 기록을 읽지 않는다(`tests/test_valve_feedback.py` AST 시험).

| 날짜 | 꾸러미 | Rule ID | 버전 | 변경 | 판정 결과 변화 | 근거 · 승인 |
|---|---|---|---|---|---|---|
| 2026-11-01 | valve29 | 전체 48 (DM · OI · DE · PMS · PD · MR · VR · PC · TG · REV) | — → **1** | 버전 관리 시작. valve28 의 논리를 버전 1 로 고정. 출처는 모두 **General Engineering Check**(프로젝트 기준 문서가 아직 연결되지 않음) | **없음** — 실자료 2,887 지적 칸 단위 동일(`valve_snapshot_diff.py check` 차이 0) · `valve_eval --check` 지문 불변 | Phase 1 지시서 §1.4 · §5.3 |
| 2026-11-01 | valve29 | **AC-01 ~ AC-05 (신규)** — Accessory | — → **1** | 사용자 요청 "Ball valve · DVC6200 · Position Transmitter · SOL · ASCO 2oo2 · Partial Stroke 스펙 학습". 지식 5개(`acc.positioner` · `acc.pos_tx` · `acc.sov` · `acc.sov_redundant` · `acc.pst`) 추가 후 규칙: AC-01 GN 이 금한 Limit Switch(Action) · AC-02 GN 이 요구한 Position Transmitter 미기재(Confirm) · AC-03 SIL 밸브의 PT SIL 등급 미기재(Note) · AC-04 GN 이 지정한 Positioner(Fisher DVC)와 다른 제조사(Action) · AC-05 SOV 2개 이상인데 1oo2/2oo2/2oo3 미기재(Confirm). 데이터시트와 그 **자체 General Note** 만 비교 — 제조사 · 표결 · SIL 을 가정하지 않음 | 실자료 164 DS: 기존 2,887 지적 **변경 0 · 삭제 0**, 추가 = AC-05 **48**(Issue List) · AC-03 **49**(Expert 탭 Note). AC-01/02/04 = 0(실자료가 GN 을 지킴). eval 지문: 칸 변화 0, 규칙 수 두 줄만 이동 → baseline 갱신 | 출처: General Note 7/13/15/20 (프로젝트 문서) + Emerson DVC6200 SIS bulletin · Fisher 4400 bulletin · ASCO RCS/ARCS · ASCO 327 catalogue · IEC 61508/61511 (General Engineering Check). 시험 `test_accessory_rules_positioner_transmitter_solenoid` |
| 2026-11-02 | valve30 | PMS (Bore 항목) | 1 그대로 | **문구만**: "No PMS item with this bore for this size" → "PMS ball valve for 3\" in class 3C3AS1 is REDUCED PORT (item …, 0.5–6\") — datasheet says FULL BORE; confirm the deviation (FULL PORT only as another valve type, e.g. DBB)". 사용자 질문 "Body Type 의 Error 가 맞나?" — 판정(Review Required)은 맞고 근거가 안 보였음 | 실자료: 28건 설명 문구만 바뀜 · 결과/Severity/상태 변경 0 · 새 스냅샷 `out/valve29/snapshot_valve30.json` | PMS 98-98-PI-SPC-00001 p.306 |

## valve40 — Instrument 규칙 새로 추가 (IN-1.0 · Valve 판정은 그대로)

Instrument Datasheet 전용 규칙 (`app/valve/instreview.py` · `instlists.py`). 엔지니어 결정(확인 · 문구 수정 · 무시+이유)은 판정을 바꾸지 않고 위에 얹힘 — 무시한 지적은 수 · PDF · CRS 에서 빠지고 감사 기록에 남음. Valve 의 기존 Rule 은 하나도 바뀌지 않음 (스냅숏 2,935 · 변경 0).

| Rule | 내용 | 기준 문서 |
|---|---|---|
| IN-REQ-01 | 필수 칸 빈 곳 (양식 카드 제안 목록 — 프로젝트에서 사용자가 확정) | 양식 카드 |
| IN-PDS-00 · 01 | PDS 에 Tag 없음('없음') · 유체 · 상 · 압력 · 온도 · 밀도 · 유량 다름 (Max/Nor/Min 중 하나와 1 % 안이면 같음) | Process Data |
| IN-PMS-01 · 02 | Pipe Class 가 PMS 에 없음 · Rating ≠ Flange Class | PMS |
| IN-LL-00 ~ 05 | Line 없음 · Class 다름 · Line Design P / T(max) 가 Datasheet 보다 높음 · T(min) 이 낮음 · Size 다름 | Process Line List |
| IN-ITM-01 · 02 | PT/PG/DPG Range 상한 < 최대 운전압력 · PSV Set > Design (같은 Datasheet 값끼리 · 사람 확인) | 같은 Datasheet |
| IN-OPN-01 | 값에 HOLD · TBA · TBC · TBD 가 남아 있음 → 확인 필요 (valve40 추가) | 같은 Datasheet |
| IN-UNIT-01 | 운전압 · 설계압의 게이지/절대 기준이 다름 → 확인 필요 · 사람 확인 (valve40 추가) | 같은 Datasheet |
| IN-CV-01 ~ 04 | Control Valve (101): Rated Cv 대비 계산 Cv · 기체 Cv 재계산(IEC 60534-2-1, Fp=1) · Choked/공동현상/Flashing · 소음 — 사람 확인 (valve40 추가) | 같은 Datasheet · IEC 60534-2-1 |
| IN-PSV-01 ~ 04 | PSV (701): API 526 Orifice 면적 · 필요 ≤ 선택 면적 · Conventional 배압 10 % · 초과압 21 % — 사람 확인 (valve40 추가) | 같은 Datasheet · API 526/520/521 |
| LIST-00 · 01 · 02 | Datasheet → Instrument Index / IO List: 누락 · 값 다름 · List 에만 | Index · IO List |

## valve29 에서 바뀐 것과 바뀌지 않은 것

- 기존 48 규칙 **판정 논리 변경 없음**. 새 규칙은 위 AC-01 ~ AC-05 (Accessory) 뿐 (Phase 2 의 Gasket · Bolting · Cv 는 아직).
- 지적에 붙는 정보만 늘었다: `op`(비교 연산) · `tol`(허용오차, 규칙에 이미 있던 Process Data 1 % 만) · `result`(규칙이 낸 판정 문구) · 엔지니어 결정(`decision` · `reason_cat` · `conclusion`).
- 엔지니어가 **Modified** 로 고친 지적은 출력에 엔지니어 문구 · Severity 가 나간다(도구 원문은 `original_description` · `original_severity` 로 보관). 규칙의 판정은 그대로.

## 이전 판정 변경 이력 (valve28 이전 — 버전 관리 전, 참고)

| 꾸러미 | 내용 |
|---|---|
| valve26 | 설계사 코멘트 말투 'Revise.' → '… shall be reviewed.' (판정 동일) |
| valve25 | 공정 값 의견에 출처 문서 표기 · 공정 값은 Process Data 우선 · 없으면 데이터시트 값 (기준값 불변) |
| valve21 | PMS Fire Safe HOLD → Review · NACE 'NA' → Review · 동료 다수 표기 합침 |
| valve10 | PMS: Ball 품목의 'X BALL/STEM' 이 머리 Trim 보다 우선 (1A1A 거짓 Review 16 → 0) |
| valve08 | 빈 Process Data 항목은 Process DS 참조여도 전부 Data Missing (사용자 요청) |
