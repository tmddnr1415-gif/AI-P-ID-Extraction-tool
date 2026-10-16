# 프로젝트 종속 값 인벤토리

`spike/` 전체를 훑어 프로젝트에 종속된 값을 목록화했습니다. **아직 config 파일로
빼지 않았습니다** — 목록·위치·판정만입니다.

판정 기준:

| 판정 | 의미 |
|---|---|
| `LEGEND` | Symbol & Legend(p2~p5)에서 유도 가능 → 코드 유지, 프로젝트 무관 |
| `PROJECT` | NOTES / KKS / 타이틀블록 / Excel 양식에서 유도 → config 후보 |
| `UNKNOWN` | 출처 불명 → 조사 필요 |

**집계: `LEGEND` 10건 / `PROJECT` 18건 / `UNKNOWN` 5건 (총 33건)**

판정 근거는 전부 실측입니다. 추정만 있는 항목은 `UNKNOWN` 으로 넘겼습니다.

---

## LEGEND — 코드 유지 (10건)

| # | 항목 | 위치 | 근거 |
|---|---|---|---|
| L1 | **계장 버블 형상 규칙** (원호 캡 2개 + 캡을 잇는 직선 변 2개) | `detect_symbols.find_bubbles` | 범례 p3·p4 가 같은 스타디움을 직접 그립니다 — 실측 p3 43개, p4 45개, 전부 68.0×22.6. 형상 규칙이 범례에 있으므로 코드 유지 |
| L2 | **앵커 어휘** (ISA 기능문자 TT/PT/FE/FT/LG/PDT/LS…) | `_V3_FIELD_TYPE_MAP` 의 키, `ISA_LIKE_RE` | 범례 p3 이 `FIRST LETTER` × `SUCCEEDING LETTERS` 전체 행렬을 정의합니다 (F=FLOW, L=LEVEL, P=PRESSURE, T=TEMPERATURE, PD=PRESSURE DIFFERENTIAL / E=PRIMARY ELEMENT, T=TRANSMITTER, I=INDICATOR, G=GLASS). `FE`=Flow Element, `LG`=Level Glass 가 여기서 나옵니다 |
| L3 | **밸브 앵커 집합** (MOV/HCV/PCV/FCV/LCV/PSV/PRV/BPRV) | `VALVE_ANCHORS` | 범례 p3 `SELF-ACTUATED DEVICES`·p4 `VALVE BODY WITH ACTUATOR` 에 전부 표기 |
| L4 | **SCT 공급자 인터페이스 심볼** | `find_sct_scopes` | 범례 p2 에 `SCT` / `SUPPLIER INTERFACE` / `SUPPLIER` 항목이 정의되어 있습니다 |
| L5 | **점선·사슬점선 라인 스타일 판정** | `Layout.brk_max_mark/brk_max_gap/brk_bridge/brk_min_marks/brk_min_span` | 범례 p2 가 `MAIN PROCESS LINE`·`SECONDARY PROCESS LINE`·`PROCESS LINE BREAK`·`INSTRUMENTATION LINE BREAK` 견본을 그립니다. p2 에서 broken run 373개가 실제로 검출됩니다 → 대시 주기를 범례에서 측정 가능 |
| L6 | **unit_code 의미** (00/10/11/12/20/21/22) | `extract_titleblocks.parse_unit_code` | 범례 p5 `UNIT IDENTIFICATION NUMBERS` 표: `POWER PLANT COMMON 00` / `FIRST GROUP COMMON 10` / `FIRST GROUP #1 GTG/HRSG 11` / `#2 12` / `SECOND GROUP COMMON 20` / `#1 21` / `#2 22` |
| L7 | **unit_code → 승수** (00→1, 10→2, 11→4) | design.md §8.1 (미구현) | L6 의 표에서 **유도됩니다**: 표에 그룹이 2개(10·20), 그룹당 유닛이 2개(11·12 / 21·22) 로 명시되어 있으므로 `00`=×1, `10`=×2, `11`=×4. **상수로 박지 말고 p5 표를 파싱해 유도할 것** — 그렇게 하면 그룹/유닛 수가 다른 프로젝트에도 그대로 적용됩니다 |
| L8 | **ISA 태그 형태 정규식** | `ISA_LIKE_RE = ^[A-Z]{1,5}$` | ISA 기능문자는 최대 5자(`LSHH`, `PDAHL`). 범례 p3 행렬의 최대 길이와 일치 |
| L9 | **analysis_scope 다수결 방식** | `pidcache.load_pages` | 프로젝트 데이터가 아니라 판정 *방법*입니다. 값(프로젝트명)은 런타임에 읽습니다 |
| L10 | **글리프 래스터화 파라미터** (`zoom`, `grid`, `min_ink_px`, `char_gap_px`) | `extract_titleblocks.Layout` | 프로젝트 의미가 없는 알고리즘 파라미터. `char_gap_px` 는 `zoom` 에 종속 |

---

## PROJECT — config 후보 (18건)

| # | 항목 | 위치 | 근거 |
|---|---|---|---|
| P1 | **앵커 → Excel TYPE 매핑** (`TT`→`TIT`, `PT`→`PIT`, `FT`→`FIT`, `LG`→`LI`, `DPIT`→`PDIT`, `LSH/LSHH/LSL`→`LS`, `FE`→`FE`) | `_V3_FIELD_TYPE_MAP` | 범례 p3 에는 `TIT`·`PIT`·`FIT`·`LI` 가 **없습니다**. 범례는 `T`(transmitter)와 `I`(indicator)를 별도 열로 정의할 뿐이고, 둘을 합친 `TIT` 표기는 **Excel 쪽 관행**입니다. 도면 어휘(L2)는 범례, 대응표는 Excel 양식 |
| P2 | **Field 비대상 집합** `{TW}` | `_V3_NOT_FIELD` | Excel `TYPE` 열에 `TW` 0행이라는 사실에서만 나옵니다. 범례에는 thermowell 심볼이 있고 비대상이라는 말은 없습니다 |
| P3 | **Excel 시트명·열 매핑** (`2.0_Instrument List`, A=NO, F=SYSTEM, G=P&ID No., H=TYPE, I=Q'ty, J=DESCRIPTION, 헤더 6행 / 데이터 8행부터) | `detect_all.load_excel` | 발주처 Excel 양식. design.md §1.2 기준 밸브 산출물은 시트명이 `3.0_Valve List` 로 다름 |
| P4 | **타이틀블록 셀 좌표 전부** (`dwg_no_region`, `title_region`, `rev_box`, `sheet_box`, `hist_*`) | `extract_titleblocks.Layout` | 이 회사 A1 도면 양식에서 실측한 절대 pt 값. 양식이 바뀌면 전부 무효 |
| P5 | **PROJECT NAME 셀 영역** | `pidcache.PROJECT_NAME_REGION` | 위와 동일 |
| P6 | **도면 영역 / NOTES 영역 분할** (`drawing_area` x<1960, `notes_area` x>1960, `notes_text_x_max` 2330) | `detect_symbols.Layout` | 타이틀블록 프레임 세로선 x=1969.6 에서 유래. 양식 종속 |
| P7 | **시트 크기 2384×1684 (A1) 전제** | 모든 절대 좌표 | 좌표를 비율이 아니라 절대 pt 로 씁니다. 다른 도면 크기면 전부 깨집니다 |
| P8 | **도면번호 형식** `[A-Z0-9]{4}-[A-Z0-9]{7}-[A-Z0-9]{3}-\d{4}` | `DWG_NO_RE` | 범례 p5 는 KKS 태그 체계를 설명하지만 이 4-7-3-4 **문서번호** 형식은 정의하지 않습니다 |
| P9 | **타이틀블록 날짜 형식** `\d{1,2}.[A-Z]{3}.\d{4}` | `DATE_RE` | 양식 종속 |
| P10 | **Revision 표기 형식** `^[A-Z][0-9]?$` | `REV_TEXT_RE` | p48 이 `A1` 이라 숫자 접미가 필요했습니다. 프로젝트마다 다릅니다 |
| P11 | **벤더 마크 의미의 출처가 페이지 NOTES 라는 사실** | `read_mark_dictionary` | 범례 p2~p5 에 마크 범례가 **하나도 없습니다**(실측: 4개 페이지 모두 `mark_dict={}`). design.md §10.1 대로 페이지 스코프. 값 자체는 런타임 파싱이라 안전하지만, "범례가 아니라 NOTES 에 있다"는 전제가 프로젝트 관행 |
| P12 | **글리프 마크 크기 목록** `KNOWN_GLYPH_SIZES = ((4.0,4.0),(5.2,5.2))` | `detect_symbols` | 이 문서의 범례 페이지들에서 관찰한 값. **교차검증에서 과적합으로 확인됨** — 5.2 를 빼면 PAB 정밀도가 30.5pp 떨어집니다 |
| P13 | **마크 부착 위치 파라미터** (`mark_above` 25, `mark_x_slack` 6, `note_mark_row_tol` 6, `note_line_gap` 20) | `detect_symbols.Layout` | p6·p26 실측(버블 위 8.5~12pt). 작도 관행 종속 |
| P14 | **텍스트형 마크 표기와 범례 문형 6종** | `MARK_TEXT_RE`, `read_mark_dictionary` | `(*) SYMBOL INDICATES…`, `(*)MARKED ITEMS…`, `* TO BE SUPPLIED BY…`, `MARKED WITH * …` 등. 전부 이 프로젝트 작성자의 문형 |
| P15 | **패키지 경계 박스 파라미터** (`box_edge_cover` 0.35, `box_mark_margin` 20) | `find_package_boxes` | p6 HRSG 패키지 1건에서 유도 |
| P16 | **SCT 스코프 지오메트리 파라미터** (`scope_text_tol` 30, `drop_x_tol` 2.0, `drop_end_tol` 1.5) | `find_sct_scopes`, `lands_on_run` | 심볼 자체는 범례(L4)지만 이 수치는 p6 실측 |
| P17 | **Excel SYSTEM ↔ 도면명 매칭 불용어** | `detect_all.STOPWORDS` | 이 Excel·도면명 어휘에서 유도 |
| P18 | **검토 주석 언어** `[가-힣]` | `detect_all.HANGUL_RE` | 이 프로젝트 검토자가 한국어를 씁니다. 언어가 바뀌면 무효 |

**미구현이지만 이미 PROJECT 로 확정된 것**: Note 승수 정규식
(`IDENTICAL FOR GROUP #`, `TYPICAL FOR n`, `PER UNIT` 등, design.md §8.1).
범례에 없는 **자유 문장**이고 작성자마다 표현이 다릅니다. 스파이크 3 착수 시
config 로 시작해야 합니다.

---

## UNKNOWN — 조사 필요 (5건)

| # | 항목 | 위치 | 왜 불명인가 | 조사 방법 |
|---|---|---|---|---|
| U1 | **잉크 임계값** `ink_frac` 0.75, `blank_above` 245 | `extract_titleblocks` | 이 도면의 스트로크 폰트가 **연회색**(최암 픽셀 182)으로 플롯된 데 맞춰 잡은 값입니다. 회색도가 플로터·PDF 생성기 설정에서 오는지, 원본 CAD 레이어 색에서 오는지 확인하지 못했습니다 | 다른 프로젝트 P&ID PDF 1부에서 타이틀블록 최암 픽셀값 분포를 측정. 값이 다르면 상대 임계(현재 방식)가 맞고, 같으면 표준 플롯 설정이라 상수화 가능 |
| U2 | **Confidence 임계** `ratio_high` 2.5 / `ratio_medium` 1.5 | `extract_titleblocks` | 글리프 매칭 마진 구간인데 유도 근거가 없습니다. 관측 마진(텍스트 0.15~0.55, 스트로크 0.02~0.06)을 보고 임의로 잡았습니다 | 58페이지 REV 판독의 마진 분포를 히스토그램으로 보고, 오판이 시작되는 지점을 실측해 경계를 재설정 |
| U3 | **캡 후보 범위** `cap_span` (7.0, 50.0), `cap_ratio` (1.6, 2.4) | `find_bubbles` | 관측된 두 계열(11.3×22.6, 14.2×28.4)을 덮도록 넓게 잡았을 뿐, 상·하한이 어디서 와야 하는지 근거가 없습니다. 범례에는 68.0×22.6 한 계열만 있어 85.1×28.4 의 출처도 불명입니다 | 범례 p3·p4 의 버블과 도면의 두 계열이 왜 다른지 확인(축척? 다른 작성자?). 도면별 축척 표기(`SCALE NONE`)와 대조 |
| U4 | **마크 클러스터링 임계** `mark_blob` (1.5,8.0), `mark_glyph_span` (3.0,8.0), `mark_cluster_gap` 2.0 | `_glyph_clusters` | `2.0` 이 동작하는 이유는 p6 에서 두 별표가 4.5pt 떨어져 있고 p49 별표 조각이 붙어 있기 때문입니다. 이 두 값의 관계가 작도 표준인지 우연인지 모릅니다 | 별표 심볼의 CAD 블록 정의(문자 크기·자간)를 발주처에 확인. 또는 다른 프로젝트에서 `**` 간격을 실측 |
| U5 | **기하 허용오차** `anchor_slack` 3.0, `side_tol` 0.8, `side_slack` 1.5 | `find_bubbles`, 앵커 판정 | 벡터 좌표가 정확한데도 여유를 준 값입니다. 필요한 이유(폰트 bbox 여백? 회전 변환 오차?)를 규명하지 않았습니다 | 허용오차를 0 으로 두고 실패 건을 수집해 실제 편차 분포를 측정. 편차 원인이 텍스트 bbox 라면 bbox 대신 글리프 잉크 범위를 쓰는 쪽이 정답 |

---

## config 로 뺄 때의 우선순위

교차검증(`out/crossval.md`)에서 실제로 성능을 좌우한 순서입니다.

1. **P12 글리프 마크 크기** — 단독으로 PAB 정밀도 30.5pp
2. **P14 텍스트형 마크 문형** — EGD 정밀도 기여
3. **P1 앵커→TYPE 매핑** — EGD 재현율 6.1pp (`LG`→`LI`)
4. **P3 Excel 시트·열** — 산출물 4종이 시트명이 달라 즉시 필요
5. **P4~P7 타이틀블록·시트 좌표** — 양식이 바뀌는 순간 전부 실패. 다만 프레임
   선을 런타임에 검출해 유도하는 편이 config 보다 낫습니다(현재 리비전 이력
   행은 이미 그렇게 찾고 있습니다)
