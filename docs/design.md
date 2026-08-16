# P&ID 기반 Instrument 자동 식별 앱 — 설계안 (v1.0)

작성 기준: 업로드된 `[D00P] P&ID_Total_20251125.pdf` (58p) 및 Excel 예시 5종 실측 분석 결과

---

## 0. 요약 — 설계에 결정적인 5가지 발견

실제 입력 파일을 분석한 결과, 원 요구사항의 몇 가지 전제를 수정해야 합니다.

| # | 발견 | 설계에 미치는 영향 |
|---|---|---|
| 1 | PDF가 **100% 벡터**다. 58페이지 전부 이미지 0개, 텍스트 레이어 존재 (샘플 페이지: 문자 1,728 / 선 2,975 / 곡선 17,473 / 이미지 0) | **OCR·비전 모델 불필요.** 좌표 정확도가 mm 단위로 확보된다. 파이프라인을 "벡터 지오메트리 우선"으로 설계 |
| 2 | 도면의 **Tag가 전부 미부여** 상태다. 태그 자리가 `.....` placeholder (샘플 1페이지에 28개). Excel의 `TAG NUMBER`, `UNIT NO.`, `SYSTEM CODE`, `ITEM CODE` 열도 **전부 공란** | **Tag 추출은 MVP 범위에서 제외.** 대신 KKS 규칙 기반 Tag *생성* 기능으로 대체 |
| 3 | 4개 산출물은 **단일 마스터 Valve List의 필터 뷰**다. `Valve_List_2512xx.xlsx`(194행)의 NO 열이 각 산출물에 그대로 승계됨 (I&C BFV는 89번부터, Pneumatic은 33번부터 시작) | 데이터 모델을 "산출물 4개"가 아니라 **마스터 1개 + 뷰 4개**로 설계 |
| 4 | **Q'ty가 심볼 개수가 아니라 P&ID 단위코드 기반 승수**다. 실측 결과가 거의 결정적 | 수량 엔진의 1순위는 심볼 카운팅이 아니라 **Note 파서 + 단위코드 승수** |
| 5 | Instrument Type 분류 기준이 요구사항의 명칭과 다르다. Excel은 **Body × Actuator 조합**으로 분류한다 | 분류 규칙을 아래 §1.3처럼 명시적으로 하드코딩 |

### 발견 4의 근거 (Q'ty 실측)

P&ID 번호 5~6번째 자리(KKS 단위코드)별 Q'ty 분포:

| 단위코드 | 의미 | Field Instrument | Valve List | 도면 Note 문구 |
|---|---|---|---|---|
| `00` | Plant Common | Q'ty=1 (거의 전부) | 1: 41건 / 4: 6건 | (승수 없음) |
| `10` | First Group Common | Q'ty=2 (거의 전부) | 2: 108건 / 1: 1건 | "THIS P&ID IS FOR GROUP#10, CONFIGURATION IS IDENTICAL FOR GROUP#20" |
| `11` | First Group #1 GTG/HRSG | Q'ty=4 (전부) | 4: 22건 | "THIS P&ID IS FOR UNIT#11, CONFIGURATION IS IDENTICAL FOR UNIT#12,21,22" |

즉 **`Q'ty = 도면상 심볼 수 × Note 승수`**이고, 승수는 Note 텍스트가 1순위·P&ID 단위코드가 검증용입니다. 예외(같은 도면 안에 승수가 다른 항목)는 실제로 존재하며(`10PGB10-M05-0004`의 Auxiliary Boiler Cooler 3건이 Q'ty=1, 도면에 `(PLANT COMMON)` 주기), 이 예외는 **항목 Description의 스코프 키워드**로 잡아야 합니다.

---

## 1. 입력 자료 실측 분석

### 1.1 P&ID PDF

- 58 페이지, A1 (2384 × 1684 pt)
- 벡터 전용. 심볼은 line/curve(Bezier) 조합, 텍스트는 개별 char 객체로 좌표 보유
- Symbol & Legend 4장 (`00GEN00-M05-0002~0005`), Drawing List 1장, 실 공정도 약 53장
- 태그 번호 미부여 (`.....`), 계장 심볼 안의 **기능문자(TT, PT, FT, LIT, PI, PDIT …)는 텍스트로 추출 가능**

### 1.2 Excel 산출물 구조

| 파일 | 시트 | 유효행 | 항목수 | Q'ty 합 |
|---|---|---|---|---|
| Field Instrument (CZE) | `2.0_Instrument List` (A~AO, 42열) | 563 | 563 | 1,120 |
| I&C Butterfly Valve (CZI) | `3.0_Valve List` (A~AN, 40열) | 21 | 21 | — |
| MOV Gate & Globe (CZH) | `3.0_Valve List` (A~AM, 39열) | 63 | 63 | 121 |
| Pneumatic Valve (CZF) | `3.0_Valve List` | 26 | 26 | 81 |
| **Master Valve List** | `3.0_Valve List` | 194 | 194 | 370 |

공통 부속 시트 5종(`5.2.0 PKG Inter. Typical`, `5.2.1 PKG Inter. Cable`, `5.3.1 Comm. Cable`, `5.4.2 Raceway`, `5.5 Cable Routing`)은 4개 파일에 **동일하게 복제**되어 있음 → 출력 시 템플릿으로 그대로 복사.

표 하단에는 기술요구사항 Note 행(12~15줄)이 붙어 있음 → 출력 시 보존 필요.

### 1.3 Instrument Type 분류 규칙 (역공학 결과)

Master Valve List의 `VALVE TYPE`(C열) / `ACTUATOR`(Y열) / `OPERATION MODE`(Z열) / `BODY`(AA열) 조합:

```
I&C Butterfly Valve  ←  BODY == BUTTERFLY
                        (액추에이터 무관: MOTOR 14 / HYDRAULIC 6 / PNEUMATIC 1)
                        (VALVE TYPE: MOV_I, MOV, HOV, CV 혼재)

MOV (Gate & Globe)   ←  ACTUATOR == MOTOR  AND  BODY ∈ {GATE, GLOBE, BALL}
                        (BALL 4건 포함됨 — 제목과 달리 Ball도 들어감)

Pneumatic Valve      ←  ACTUATOR == PNEUMATIC
                        · OPERATION MODE == MODULATING → Control Valve (CV, 18건)
                        · OPERATION MODE == ON-OFF     → On/Off Valve (XV, 8건)

미포함 (4개 산출물 어디에도 안 들어감)
                     ←  ACTUATOR == SELF ACTING (68건: PSV 66, BPV 1, PRV 1)
```

**중요:** `VALVE TYPE` 열 값(MOV/MOV_I/HOV/CV/XV/PSV)은 분류의 *결과*이지 기준이 아닙니다. 기준은 Body × Actuator입니다.

### 1.4 Field Instrument Type 분포

`PI` 111 / `PIT` 108 / `TIT` 99 / `TI` 60 / `PDIT` 53 / `FIT` 31 / `LIT` 29 / `LS` 22 / `RO` 19 / `FE` 18 / `LI` 10 / `FS` 3 (총 12종)

→ 요구사항 §3.1의 세부 분류(Analyzer, Switch, Gauge 등)는 **불필요**. 실제 산출물은 ISA 기능문자 12종을 그대로 `TYPE` 열에 씁니다. `INST. TYPICAL TYPE`(X열)에 `PIT-1`, `TIT-3` 같은 프로젝트 Typical 코드가 따로 붙습니다 (Design Table 참조).

---

## 2. 권장 기술 스택

| 레이어 | 선택 | 이유 |
|---|---|---|
| PDF 파싱 | **PyMuPDF (fitz)** + pdfplumber 보조 | 벡터 path/text를 좌표와 함께 추출. fitz가 Bezier 세그먼트 접근에 유리 |
| 지오메트리 엔진 | **Shapely** + NetworkX | 심볼 바운딩박스 교차 판정 / 라인 그래프 순회 |
| 심볼 매칭 | 자체 룰 엔진 (텍스트 앵커 + 지오메트리 검증). 보조로 OpenCV template matching | §6 참조. 딥러닝 불필요 |
| LLM | **Claude (Anthropic API)** — Note 해석, Description 생성, 애매 케이스 판정 전용 | 심볼 검출에는 쓰지 않음 (결정론적 처리가 정확·저렴) |
| 백엔드 | **FastAPI** (Python 3.11+) | 파싱 라이브러리와 같은 런타임 |
| 작업 큐 | Celery + Redis (또는 소규모면 FastAPI BackgroundTasks) | 58p 분석은 수 분 소요 |
| DB | **PostgreSQL** + JSONB | 관계형 + evidence/원본값 JSON 보관 |
| 프론트 | **React + TypeScript**, Vite | |
| 테이블 | **AG Grid** (Community) | 수백~수천 행 인라인 편집·필터·다중선택 필수 |
| PDF 뷰어 | **PDF.js** + canvas 오버레이 | Bounding Box 하이라이트/수정 |
| Excel 출력 | **openpyxl** (템플릿 복사 방식) | 서식·필터·부속시트 보존 |
| 배포 | Docker Compose | |

> LLM을 심볼 검출에 쓰지 않는 것이 이 설계의 핵심 판단입니다. 벡터 도면에서 `TT` 텍스트를 찾는 건 결정론적으로 100% 정확한 반면, 비전 모델은 90%대에 머물고 페이지당 비용·시간이 수십 배입니다. LLM은 "Note 문장 해석"과 "Description 문장 생성"처럼 **자연어가 개입하는 지점에만** 투입합니다.

---

## 3. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  React SPA                                                   │
│  업로드 │ PDF뷰어(PDF.js) │ 결과그리드(AG Grid) │ 상세검토    │
└───────────────────────────┬─────────────────────────────────┘
                            │ REST + WebSocket(진행률)
┌───────────────────────────┴─────────────────────────────────┐
│  FastAPI                                                     │
│  ProjectAPI │ AnalysisAPI │ ItemAPI │ ExportAPI │ RuleAPI    │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│  Analysis Worker (Celery)                                    │
│                                                              │
│  ①추출  PdfExtractor      : page → texts[], paths[], bbox    │
│  ②분류  PageClassifier    : Legend / DrawingList / P&ID      │
│  ③검출  SymbolDetector    : 텍스트앵커 + 지오메트리 검증      │
│  ④연결  LineTracer        : 배관 그래프 + From-To            │
│  ⑤규칙  NoteParser        : General/Page Note → 승수·Scope   │
│  ⑥수량  QuantityEngine    : 심볼수 × 승수 (+근거 저장)        │
│  ⑦서술  DescriptionGen    : LLM + 기존 Excel 패턴 few-shot   │
│  ⑧판정  ScopeResolver     : Vendor/Scope/중복/Confidence     │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│  PostgreSQL  │  파일스토리지(PDF/Excel/템플릿)                 │
└─────────────────────────────────────────────────────────────┘
```

각 단계는 **독립 실행·재실행 가능**해야 합니다. ⑦Description만 다시 돌리는 경우가 실무에서 가장 흔합니다.

---

## 4. 데이터베이스 스키마

```sql
-- 프로젝트 -----------------------------------------------------------
project(id, code, name, kks_ruleset_id, created_at)

-- 원본 파일 ----------------------------------------------------------
source_file(id, project_id, kind, filename, storage_path, sha256, uploaded_at)
  -- kind: PID_PDF | LEGEND | EXCEL_TEMPLATE | NOTE_DOC

pid_page(id, project_id, source_file_id,
         page_no,              -- PDF 물리 페이지 (1-based)
         drawing_no,           -- D00P-10LBA10-M05-0001
         drawing_title, revision, rev_date,
         unit_code,            -- KKS 5~6자리: '00'|'10'|'11'|...
         system_name,          -- 'HP Steam System'
         page_kind,            -- PID | LEGEND | DRAWING_LIST | COVER
         width_pt, height_pt)

-- Note / 규칙 --------------------------------------------------------
pid_note(id, pid_page_id, note_kind, note_no, raw_text,
         parsed_multiplier,    -- 2 | 4 | null
         parsed_scope,         -- VENDOR_SUPPLY | EXCLUDE | null
         applies_to,           -- JSONB: 적용 대상 조건
         confidence)

symbol_rule(id, project_id, instrument_type, valve_type,
            anchor_text,       -- 'MOV' | 'TT' | 'FCV' ...
            geometry_spec,     -- JSONB: 원/삼각형/나비형 판정 파라미터
            include_cond, exclude_cond, note, is_active)

-- 검출 결과 ----------------------------------------------------------
detection(id, pid_page_id,
          anchor_text, bbox,          -- JSONB [x0,y0,x1,y1] PDF 좌표계
          symbol_rule_id,
          raw_evidence)               -- JSONB: 매칭된 path/text id 목록

-- 최종 항목 (마스터 1개, 산출물은 뷰) ----------------------------------
item(id, project_id, detection_id, pid_page_id,
     seq_no,                          -- Excel NO 열 (마스터 기준 연번)

     -- AI 값 / 사용자 값 분리 저장
     ai_values     JSONB,             -- 분석 직후 원본
     user_values   JSONB,             -- 사용자 수정분만
     final_values  JSONB GENERATED,   -- user 우선 병합 (조회용)

     -- 인덱싱·필터용 비정규화 컬럼
     instrument_type,                 -- FIELD_INST | BFV_IC | MOV | PNEUMATIC | OTHER
     valve_type, body_type, actuator, operation_mode,
     type_code,                       -- PIT / TIT / MOV / CV ...
     pid_no, system_name, qty,
     description, tag_no,
     vendor_supply, scope, remark,
     sort_x, sort_y,                  -- 위→아래, 좌→우 정렬키
     confidence,                      -- HIGH | MEDIUM | LOW
     review_status,                   -- AUTO | NEEDS_REVIEW | CONFIRMED
     dup_group_id)

item_evidence(id, item_id, kind, payload)
  -- kind: QTY_BASIS | DESC_TRACE | SCOPE_BASIS | VENDOR_BASIS | DUP_BASIS

item_revision(id, item_id, field, old_value, new_value,
              changed_by, changed_at, reason)

-- 배관 그래프 (From-To 추적용) ----------------------------------------
line_segment(id, pid_page_id, geom, line_no, dn_size, flow_dir)
line_node(id, pid_page_id, node_kind, ref_id, bbox)
  -- node_kind: EQUIPMENT | OFF_PAGE_CONNECTOR | INSTRUMENT | VALVE | JUNCTION
line_edge(id, from_node_id, to_node_id, line_segment_id)

-- 학습 후보 ----------------------------------------------------------
rule_candidate(id, project_id, pattern JSONB, occurrence_count,
               status,          -- PROPOSED | APPROVED | REJECTED
               approved_by, approved_at)
```

**핵심 설계 결정 3가지**

1. `ai_values` / `user_values` 분리 → 재분석 시 사용자 수정값이 덮어써지지 않음 (요구사항 §17 마지막 항목 충족).
2. `item`은 마스터 테이블 하나. 4개 산출물은 `instrument_type` 필터 뷰. 실제 Excel이 그렇게 만들어져 있음(§0 발견 3).
3. 모든 판단에 `item_evidence` 행이 붙음. 근거 없는 값은 저장하지 않음.

---

## 5. P&ID 분석 파이프라인

```
[1] 페이지 추출        → PyMuPDF로 page별 text span + drawing path 수집
[2] 타이틀블록 파싱     → 우하단 고정영역에서 DWG NO / TITLE / REV 추출
                          → drawing_no에서 unit_code(5~6자리) 파싱
[3] 페이지 분류        → LEGEND / DRAWING_LIST / PID
[4] Legend 학습        → Legend 4장에서 심볼-의미 매핑 후보 추출 (사용자 승인)
[5] Note 추출          → 'GENERAL NOTES :' / 'NOTES :' 블록 파싱 → 승수/스코프
[6] 심볼 검출          → §6
[7] 라인 그래프 구축    → §7
[8] From-To 추적       → §7
[9] 수량 산정          → §8
[10] Description 생성  → §9
[11] Vendor/Scope 판정 → §10
[12] 중복 판정         → §11
[13] 정렬 & 연번 부여   → sort_y ASC, sort_x ASC (위→아래, 좌→우)
[14] Confidence 산정   → §12
```

정렬(13)은 요구사항 §4대로 하되, PDF 좌표계는 y축이 아래에서 위로 증가하므로 `sort_y = page_height - y0`로 변환해야 합니다. 또한 "같은 높이"는 완전 일치가 아니라 **밴드 단위**(±15pt)로 묶어 좌→우 정렬해야 실무 감각과 맞습니다.

---

## 6. Symbol 식별 방식

### 6.1 기본 전략 — 텍스트 앵커 우선

벡터 PDF에서는 심볼 안의 텍스트가 정확히 추출됩니다. 따라서:

```
1단계: 텍스트 앵커 스캔
   앵커 사전 = {PI, PIT, TI, TIT, PDIT, FIT, LIT, LI, LS, LSH, LSHH, LSL,
                FE, RO, FS, AIT, ZS, ZT, PT, TT, FT, ...,
                MOV, HV, HOV, XV, NRV, FCV, TCV, PCV, LCV, HCV, PSV, PRV, BPRV}

2단계: 지오메트리 검증 (오탐 제거)
   - 계장 버블: 앵커 텍스트를 감싸는 원/타원 존재 여부
     (Bezier 곡선 4개가 닫힌 원을 이루는지 판정)
   - 밸브 바디: 앵커 아래/위에 삼각형 2개(bow-tie) = Globe/Gate
                렌즈형(타원+수직선) = Butterfly
   - 액추에이터: 버블 위 'M' = Motor / 'S' = Solenoid
                'I/P' 사각형 = Pneumatic positioner
                'H' = Hydraulic

3단계: 제외 필터
   - 타이틀블록 영역(우하단), Note 영역(우상단) 내부 텍스트는 제외
   - Off-page connector 박스 안의 도면번호는 제외
   - Legend 페이지는 전체 제외
```

### 6.2 4개 타입별 판정 로직

```python
# Field Instrument
if anchor in ISA_FUNCTION_CODES and has_enclosing_circle(anchor):
    type_code = anchor            # 'PIT', 'TIT' 등을 그대로 사용
    instrument_type = FIELD_INST

# Valve — Body 판정
body = detect_body_geometry(bbox)   # BUTTERFLY | GATE | GLOBE | BALL | ANGLE
actuator = detect_actuator(bbox)    # MOTOR | PNEUMATIC | HYDRAULIC | SELF_ACTING

# §1.3 분류 규칙 그대로 적용
if body == BUTTERFLY:                         → BFV_IC
elif actuator == MOTOR and body in (GATE,GLOBE,BALL) → MOV
elif actuator == PNEUMATIC:                   → PNEUMATIC
                                                 (MODULATING→CV / ON-OFF→XV)
elif actuator == SELF_ACTING:                 → OTHER (4개 산출물 제외)
```

Butterfly와 Gate/Globe 구분이 지오메트리 판정의 정확도를 좌우합니다. 이 프로젝트 도면에서 Butterfly는 21건뿐이므로, **초기에는 21건 전수 수동 검증**으로 룰을 튜닝하는 게 현실적입니다.

### 6.3 Legend 학습

Legend 4장은 "심볼 + 옆에 설명 텍스트" 구조입니다. 자동 추출 후 **사용자 승인 화면**을 반드시 거칩니다. 자동 확정하지 않습니다.

---

## 7. Line From–To 추적

```
[1] 배관 선 후보 추출
    - 수평/수직 line 객체 중 길이 > 20pt
    - 계장 신호선(점선/사선 해칭)은 별도 레이어로 분리
[2] 세그먼트 병합
    - 끝점 거리 < 2pt 이면 동일 노드로 스냅
    - NetworkX 그래프 구성 (node=교차점/끝점, edge=세그먼트)
[3] 노드 태깅
    - Equipment 박스(사각형+텍스트) → EQUIPMENT 노드
    - '. TO XXX .' / '. FROM XXX .' 텍스트 블록 → OFF_PAGE_CONNECTOR 노드
    - 검출된 심볼 bbox → INSTRUMENT / VALVE 노드
[4] 흐름 방향
    - Piping designation flag(화살표 삼각형) 방향 판독
    - 방향 미확인 시 Off-page connector의 TO/FROM 텍스트로 보정
[5] From-To 결정
    - 심볼 노드에서 그래프 양방향 BFS
    - upstream 첫 EQUIPMENT/CONNECTOR, downstream 첫 EQUIPMENT/CONNECTOR
    - 도면 경계를 넘으면 Off-page connector의 도면번호로 다음 페이지 이어붙임
```

**Off-page 추적**: 도면에 `D00P-10MAN10-M05-0001` 같은 참조번호가 커넥터 옆에 붙어 있어, 페이지 간 연결은 문자열 매칭으로 안정적으로 됩니다. 다만 대응 지점의 grid 좌표(`(G-8)` 등)까지 일치시켜야 오연결이 없습니다.

**한계 인정**: 라인 추적은 이 시스템에서 가장 실패율이 높은 모듈입니다. 실패 시 Description을 추측하지 말고 `검토 필요`로 넘기는 것이 정답입니다 (§16).

---

## 8. Note 기반 수량 산정

### 8.1 승수 테이블 (실측 기반)

```
NoteParser 정규식 패턴:
  r'IDENTICAL FOR GROUP\s*#?(\d+)'      → 대상 그룹 수 +1 배
  r'IDENTICAL FOR UNIT\s*#?([\d,\s#]+)' → 나열된 유닛 수 +1 배
  r'TYPICAL FOR (\d+)'                  → n 배
  r'\((\d+)\s*[xX]\s*\d+%\)'            → 대수 (2X100%, 3X50%)
  r'PER (UNIT|TRAIN|PUMP)'              → 대응 설비 수

검증용 fallback (Note 파싱 실패 시):
  unit_code '00' → ×1
  unit_code '10' → ×2
  unit_code '11' → ×4
```

### 8.2 산정 절차

```
qty = symbol_count_on_page × note_multiplier

1. 페이지 Note에서 승수 M 추출
2. P&ID 번호 unit_code로 예상 승수 M' 산출
3. M == M' 이면 Confidence HIGH
   M != M' 이면 Confidence LOW + 검토 필요
   Note 없고 M'만 있으면 M' 채택 + Confidence MEDIUM
4. 항목별 예외 검사:
   Description/주변 텍스트에 '(PLANT COMMON)', 'AUX. BOILER',
   'COMMON' 키워드 → 승수 강제 1
5. evidence 저장:
   {"symbol_count": 1, "note_multiplier": 2,
    "note_ref": "NOTES:1 IDENTICAL FOR GROUP#20",
    "unit_code_check": "10 → ×2 (일치)", "result": 2}
```

### 8.3 절대 원칙

수량 산정이 불확실하면 **값을 비우고** `review_status = NEEDS_REVIEW`. 임의 확정 금지. Instrument List는 발주 수량에 직결되므로 "그럴듯한 오답"이 "빈칸"보다 훨씬 위험합니다.

---

## 9. Description 생성

기존 Excel의 Description은 일관된 문형을 갖습니다:

```
UNIT #11 HP STEAM PRESSURE A
UNIT #11 HP STEAM TO HRSG DBL VALVE
UNIT #10 CONDENSER NORMAL MAKE-UP CONTROL VALVE
UNIT #10 AUX CIRCULATING WATER PUMP DISCHARGE VALVE
UNIT #10 CIRCULATING WATER PUMP DISCHARGE VALVE
```

패턴: `UNIT #{unit} + {system/line 대상} + {측정변수 or 기능} + {설비유형}`

### 생성 절차

```
1. Rule 기반 뼈대 생성
   unit    ← P&ID unit_code + 도면상 #11/#12 라벨
   subject ← From-To 추적 결과의 upstream/downstream Equipment
   variable← type_code 매핑 (PIT→PRESSURE, TIT→TEMPERATURE, FIT→FLOW)
   suffix  ← 밸브면 VALVE / 계기면 생략

2. LLM 정제 (Claude)
   프롬프트에 동일 System의 기존 Excel Description 5~10건을 few-shot으로 제시
   "아래 기존 작성 예시와 동일한 용어·어순·대문자 규칙을 따라
    이 항목의 Description을 한 줄로 작성하라.
    근거가 부족하면 생성하지 말고 INSUFFICIENT 를 반환하라."

3. 검증
   LLM이 INSUFFICIENT 반환 또는 From-To 미확정 → NEEDS_REVIEW
   생성된 문자열이 기존 어휘 사전에 없는 단어 포함 → Confidence MEDIUM
```

**용어 사전은 프로젝트별로 구축**합니다. 업로드된 Excel 563 + 194행에서 명사구를 추출하면 초기 사전이 자동으로 만들어집니다.

---

## 10. Vendor 공급 및 Scope 판정

### 10.1 이 프로젝트의 실제 마크 체계

도면에서 확인된 공급주체 표기 (페이지마다 정의가 다름 — 반드시 페이지 Note 우선 참조):

| 표기 | 의미 | 출처 |
|---|---|---|
| `SCT SUPPLIER` 박스 | Supplier 공급 경계 | 전 페이지 공통 |
| `SCT HRSG` / `SCT ADNOC` | 특정 공급자 경계 | 페이지별 |
| `(*)` | "MARKED ITEMS TO BE PROVIDED BY FUEL OIL PUMP SUPPLIER" | `00EGD00-M05-0001` Note 1 |
| `(**)` | "FURNISHED BY CHLORINATION SYSTEM SUPPLIER" / "BY TANK VENDOR" | `00PAB10-*` Note 5 / `00GHB10-*` |
| 해칭 삼각형 | "DENOTES EQUIPMENT WILL BE SUPPLIED BY HRSG / ST SUPPLIER" | 스팀계통 도면 |
| 점선 박스 | Vendor package boundary | Legend 정의 |

**같은 `(*)`가 페이지마다 다른 의미**입니다. 따라서 마크 사전은 전역이 아니라 **페이지 스코프**로 관리해야 합니다.

### 10.2 판정 로직

```
1. 페이지 Note에서 마크 정의 파싱 → page_mark_dictionary
2. 심볼 bbox 주변 30pt 내 마크 텍스트 탐색
3. 심볼이 Vendor boundary(점선박스/SCT 박스) 내부인지 Shapely로 판정
4. 마크 O + 정의 O → vendor_supply = Yes, remark = 정의 문구, HIGH
   마크 O + 정의 X → NEEDS_REVIEW (자동 확정 금지)
   마크 X + boundary 내부 → vendor_supply = Yes, MEDIUM
   충돌(마크는 A공급자, boundary는 B공급자) → NEEDS_REVIEW
```

---

## 11. 중복 항목 처리

동일 기기가 여러 페이지에 나타나는 경우 판정 키:

```
중복 후보 = 다음 조건을 2개 이상 만족
  · 동일 line_no
  · 동일 upstream/downstream Equipment 조합
  · 한쪽이 Off-page connector로 상대 도면을 참조
  · 동일 type_code + 동일 system

처리: 자동 삭제 절대 금지
      dup_group_id 부여 → UI에서 나란히 표시
      "병합 / 개별 유지" 사용자 선택
      선택 결과를 item_evidence(DUP_BASIS)에 기록
```

---

## 12. Confidence 산정

```
score = 100
  심볼 지오메트리 미확정        -30
  Note 승수와 unit_code 불일치  -30
  From-To 추적 실패            -25
  Description LLM INSUFFICIENT -25
  Vendor 마크 정의 없음         -20
  중복 후보                    -15
  Body/Actuator 판정 애매       -20

HIGH ≥ 80 / MEDIUM 50~79 / LOW < 50
LOW 또는 필수항목 미확정 → review_status = NEEDS_REVIEW
```

UI에서 `NEEDS_REVIEW` 행은 상단 고정 + 색상 강조. 이 목록이 0이 되기 전에는 Excel 출력 버튼을 비활성화하는 것을 권장합니다.

---

## 13. 화면 구성

```
① 프로젝트 / 업로드
   PDF · Legend · Excel 템플릿 업로드, 파일별 상태 배지

② Legend 검토              ← 요구사항에 없지만 필수 추가
   자동 추출된 심볼-의미 매핑을 사용자가 승인/수정
   이 단계 승인 전에는 본 분석 실행 불가

③ 분석 진행
   단계별 진행률 (WebSocket), 페이지별 검출 수 실시간 표시

④ 메인 작업 화면 (분할 뷰)
   ┌────────────────┬──────────────────────────┐
   │  PDF 뷰어       │  결과 그리드 (AG Grid)     │
   │  · 확대/이동     │  탭: 전체 / Field / BFV   │
   │  · Bbox 오버레이 │      / MOV / Pneumatic    │
   │  · 타입별 색상   │      / 검토필요           │
   │  · 클릭→행 선택  │  인라인 편집, 필터, 정렬   │
   │  · 드래그→행 추가│  행 추가/삭제/복사/다중선택│
   └────────────────┴──────────────────────────┘
   양방향 연동: 행 선택 → 도면 위치 하이라이트 (역방향도)

⑤ 상세 검토 패널 (행 선택 시 하단 슬라이드업)
   원본 크롭 이미지 │ 인식 심볼 │ 연결 Line │ From-To 경로
   적용 Note 원문   │ 수량 근거 │ Vendor 근거 │ Scope 근거
   AI 원본값 vs 현재값 diff │ 수정 이력

⑥ 검토 필요 항목 전용 화면
   근거 유형별 그룹핑 → 같은 원인끼리 일괄 처리

⑦ Excel 출력
   Revision / 작성일자 입력, 개별 4종 + 통합 1종 선택
```

②Legend 검토 단계를 원 요구사항에 추가할 것을 권합니다. Legend 해석이 틀리면 이후 전 단계가 함께 틀립니다.

---

## 14. Excel 출력 방식

**템플릿 복사 방식**을 씁니다. 새로 만들지 않습니다.

```python
# 1. 업로드된 원본 Excel을 템플릿으로 복사
wb = openpyxl.load_workbook(template_path)   # 서식·필터·열너비·부속시트 보존
ws = wb['3.0_Valve List']                    # 또는 '2.0_Instrument List'

# 2. 데이터 영역만 삭제 (8행 ~ 표 끝)
#    주의: 표 하단의 기술요구사항 Note 행(12~15줄)은 보존해야 함
#    → 표 끝 판정은 'A열이 정수인 마지막 행'으로

# 3. 확정 데이터 write-back
#    셀 스타일은 기존 행에서 복사하여 적용

# 4. 헤더 갱신
#    A3: RFQ NO. / A4: DESCRIPTION / 파일명 Revision·날짜
```

### 출력물

| 파일 | 내용 |
|---|---|
| `D00P-00CZE00-J30-0001_RC_Field Instrument_YYYYMMDD.xlsx` | Field Instrument (`2.0_Instrument List`) |
| `D00P-00CZI00-J30-0001_RC_I&C Butterfly Valve_YYYYMMDD.xlsx` | BODY=BUTTERFLY |
| `D00P-00CZH00-J30-0001_RC_MOV (Gate & Globe)_YYYYMMDD.xlsx` | MOTOR × GATE/GLOBE/BALL |
| `D00P-00CZF00-J30-0001_RC_Pneumatic Valve (Control & Onoff)_YYYYMMDD.xlsx` | PNEUMATIC |
| `Valve_List_YYYYMMDD.xlsx` | 마스터 (NO 연번 기준) |
| `..._Integrated_YYYYMMDD.xlsx` | Summary / 4종 / Review Required / Revision History |

**NO 열 채번 규칙**: 마스터 Valve List에서 부여한 연번을 각 산출물에 그대로 승계합니다 (I&C BFV가 89번부터 시작하는 현재 구조와 일치).

**AI 전용 필드**(Page No., Drawing Coordinate, Confidence, 근거)는 기존 양식에 열을 추가하지 않고, 통합 파일의 `Review Required` 시트에만 넣습니다.

---

## 15. 개발 단계별 계획

### Phase 0 — 검증 스파이크 (1주) ★ 코딩 전 필수

본격 개발 전에 다음 3가지를 먼저 확인합니다. 하나라도 실패하면 설계를 바꿔야 합니다.

1. 58페이지 전체에서 타이틀블록 파싱 성공률 → 목표 100%
2. 1개 페이지(`10LBA10-M05-0001`)에서 계장 심볼 검출 결과를 기존 Excel 12행과 대조 → 목표 재현율 90% 이상
3. Note 파싱으로 승수 추출 → 41개 P&ID 전부에서 정답 도출 확인

### Phase 1 — MVP (4~6주)

```
· PDF 업로드 & 페이지 메타 추출
· Legend 등록/승인 화면
· 심볼 검출 (Field Instrument + 4개 밸브 타입)
· Note 기반 Q'ty 산정 + 근거 저장
· System / P&ID No. / Valve Type 자동 채움
· PDF 뷰어 ↔ 결과 그리드 양방향 연동
· 인라인 편집 + AI/사용자 값 분리 저장
· 검토 필요 항목 표시
· Excel 출력 (템플릿 복사, 4종)
```

Description은 이 단계에서 **rule 기반 뼈대까지만** 만들고 공란 허용. From-To 추적을 MVP에 넣으면 일정이 깨집니다.

### Phase 2 — 연결관계 (4주)

```
· 라인 그래프 구축 + From-To 추적
· Off-page connector 페이지 간 추적
· LLM Description 생성 (few-shot)
· Vendor / Scope 판정
· 중복 항목 판정 및 병합 UI
```

### Phase 3 — 운영 (3주)

```
· 수정 이력 기반 규칙 후보 제안 (사용자 승인 후 반영)
· 프로젝트별 Symbol Library 분리 관리
· Revision 간 변경점 비교
· 통합 Excel / Dashboard
```

### Phase 4 — 확장

Tag 자동 생성(KKS 규칙), Line List·Equipment List 연계, Instrument Index 대조, 권한·승인 Workflow.

---

## 16. 예상 기술적 한계와 대응

| 한계 | 실제 위험도 | 대응 |
|---|---|---|
| **Tag가 도면에 없음** (`.....`) | 확실 | Tag 추출 기능을 만들지 않는다. Phase 4에서 KKS 규칙 기반 *생성*으로 전환 |
| Butterfly vs Gate/Globe 지오메트리 오판 | 높음 | Butterfly 21건 전수 수동 검증으로 룰 튜닝. 애매하면 NEEDS_REVIEW |
| 라인 추적 실패 (교차·점프·해칭) | 높음 | 실패를 정상 상태로 취급. Description 공란 + 검토 필요. 추측 생성 금지 |
| Note 문구 변형 (프로젝트마다 다름) | 중간 | 정규식 + LLM 이중 파싱. 두 결과 불일치 시 사용자 확인 |
| 마크(`*`, `**`) 의미가 페이지마다 다름 | 확실 | 마크 사전을 페이지 스코프로 관리. 전역 사전 금지 |
| Vendor package 내부 항목 포함/제외 판단 | 중간 | 기본 정책을 프로젝트 설정으로 노출. 자동 판단하지 않음 |
| 58p × 수천 객체 처리 성능 | 낮음 | 페이지 단위 병렬 처리. 목표 전체 5분 이내 |
| 다른 프로젝트 도면 적용성 | 중간 | 룰을 DB(`symbol_rule`)에 두고 코드에 하드코딩하지 않음 |
| LLM 비결정성 | 중간 | temperature 0, 동일 입력 캐싱, Description 외 용도 금지 |

### 정확도 목표 (현실적 수치)

| 항목 | MVP 목표 | Phase 2 목표 |
|---|---|---|
| 심볼 검출 재현율 | 90% | 96% |
| Instrument Type 분류 정확도 | 92% | 97% |
| Q'ty 정확도 | 85% | 95% |
| Description 자동 생성률 | — | 70% (나머지 검토 필요) |

**100%는 목표가 아닙니다.** 요구사항 §17대로 목적은 검토 제거가 아니라 입력 시간 단축입니다. 563행을 수기 입력하던 작업이 "AI 초안 + 100행 검토"로 바뀌면 성공입니다.

---

## 17. 원 요구사항 대비 수정 제안

| 요구사항 | 수정 제안 | 사유 |
|---|---|---|
| §2.1 "스캔 이미지 판별, OCR 수행" | 벡터 전용으로 한정. OCR 미구현 | 대상 PDF가 100% 벡터 |
| §3.1 Field Instrument 세부분류 10종 | ISA 기능문자 12종(PI/PIT/TIT/…) 직접 사용 | 기존 Excel이 그렇게 작성됨 |
| §5 "Tag No. — 도면에서 식별된 태그" | MVP 제외. Phase 4 생성 기능 | 도면·Excel 모두 태그 미부여 |
| §3.3 "MOV — Gate/Globe" | Ball Valve 포함 | 실제 MOV 산출물에 BALL 4건 포함 |
| §12 화면 구성 | **Legend 검토·승인 화면 추가** | Legend 오해석이 전 단계로 전파 |
| §15 "Instrument Type별 개별 파일" | 마스터 Valve List 파일 추가 출력 | 4개 산출물이 마스터의 필터 뷰 |
| §18 MVP 범위 | Description·From-To를 Phase 2로 이동 | MVP 일정 현실화 |

---

## 부록 A — Phase 0 검증 스크립트 실행 순서

```bash
# 1. 타이틀블록 파싱 전수 검증
python spike/extract_titleblocks.py  --pdf pid_total.pdf  --out titleblocks.csv
#    → 58행 중 drawing_no 파싱 실패 건수 확인

# 2. 단일 페이지 심볼 검출 → 기존 Excel 대조
python spike/detect_symbols.py  --pdf pid_total.pdf  --page 6 \
       --compare "D00P-00CZE00-J30-0001_RC_Field_Instrument_2512xx.xlsx"
#    → D00P-10LBA10-M05-0001 의 12건과 대조

# 3. Note 승수 파싱 전수 검증
python spike/parse_notes.py  --pdf pid_total.pdf \
       --expect-from "Valve_List_2512xx.xlsx"
#    → unit_code별 승수(00→1, 10→2, 11→4)와 일치 여부
```

이 3개가 통과하면 Phase 1 착수, 하나라도 실패하면 해당 모듈 설계를 재검토합니다.
