# LOGIC 검토 메뉴 — 설계 (L1회차 · 2026-10-11 · 샘플 실측 반영)

> 상태: **초안 · 사용자 승인 전.**  제품 코드는 아직 없다 (측정 도구 `spike/logic_survey.py` 만).
> 지시문: `docs/logic_review_kickoff.md`.  원칙: `CLAUDE.md` §2 · §9 · §10, `docs/state_and_roadmap.md` §3 · §4.
>
> **샘플**: `data/logic/HRSG_Logic_rev2.pdf`(53장 · G001~G067) · `data/logic/HRSG_Loop_rev2.pdf`(46장 · P001~P091).
> 둘 다 **TAKHIATASH** (Hyundai Engineering · B-CBA-I-29-001/002 · Rev.2) — hotfix84 의 P&ID 와 **같은 프로젝트**다.
> §1 이 실측이다.  §4 규칙 옆의 *(가설)* 은 아직 선 글자를 못 읽어 도면으로 확인하지 못한 것이다.

---

## 0. 한 장 요약

```
 Logic / Loop / System PDF ──▶ ① 읽기 (pidcache 재사용: 글자 · SHX · 회전 · 선분 · 사각형)
                               ② 유도 (이 묶음이 말하는 것을 잰다: 도면번호 꼴 · 참조 꼴 · 블록 모양 · 선 끊김 분포)
                               ③ 그래프 (블록 · 단자 · 신호선 · 시트 간 참조)
                               ④ 판정 (규칙만 · LLM 없음) ── 연결 적합성 C1~C8 · P&ID 정합성 X1~X4
                               ⑤ 결과 (목록 + 도면 위 표시 + Excel) ── 사람 O/X · 마크업 · VOC
```

* **같은 서버 · 같은 첫 화면 · 같은 프로젝트.**  왼쪽 메뉴에 `LOGIC 검토` 한 줄.  프로젝트 화면에서
  P&ID 리비전 옆에 LOGIC 묶음이 따로 보인다.
* **P&ID 엔진은 부르기만 한다.**  `app/engine/*` · `app/pipeline.py` 는 한 줄도 고치지 않는다.
* 새 코드: `app/logic/*`(서버) · `app/static/logic.js` · `app/static/logic.css`(화면).
  기존 파일에 더하는 것은 §9 의 **다섯 줄 남짓**뿐이다.

---

## 1. 샘플 실태 조사 — 실측 (2026-10-11)

도구 `python3 spike/logic_survey.py <PDF…>` (읽기만) · 렌더는 scratchpad 에서 눈으로 봤다.

| # | 무엇을 | Logic (53장) | Loop (46장) | 뜻 |
| --- | --- | --- | --- | --- |
| S1 | 글자층 | 표지·범례(G004~G006)·타이틀블록만 진짜 글자 (ArialMT) | 표지·범례 2장(P003 · P091)·타이틀블록만 | **본문은 글자층이 없다** |
| S2 | 선으로 그린 글자 | **49/53장**이 본문 글자를 선으로 그림 · SHX 주석 **0** | **41/46장** · SHX 주석 0 | ★ **이 묶음의 가장 큰 벽** (§1-2) |
| S3 | 블록 모양 | AND/NAND = 세로 글자 든 사각형 · OR/NOR/NOT = 원·작은 사각형 · S/R/Ro 메모리 · t PD/GT/DT 타이머 · STEP 상자 · ◆ 입력(현장→DCS) · ■ 출력(인터포징 릴레이) | 측정 스타디움(태그 2줄) · AI/DI 역삼각형 · `H/` `HH/` `L` 비교 사각형 · MED · LEVEL COMPENSATION 상자 | 범례가 정의한다 (G003 · P003~P005) |
| S4 | 블록 안 글자 | 전부 선 글자 (AND·OR·NOT·S·Ro·PD) | 전부 선 글자 | 블록 종류는 **모양으로** 1차, 글자로 확인 |
| S5 | 신호선 | 수평·수직 실선 (굵기 0.48) · 파선 = "논리 연결 아님"(G003) · 점 = 연결 | 실선 = 공정 제어 신호 · 파선 = 전기 신호 (P003) | 끊김 분포는 구현 첫 단계에서 잰다 |
| S6 | 시트 간 참조 | **표 형식**: 왼쪽 입력 행 1~62 (`FM` · `NO.` · `DESCRIPTION` · `KKS NO.`) · 오른쪽 출력 행 63~124 (`KKS NO.` · `DESCRIPTION` · `NO.` · `TO`).  `FM` = `G031-81`(시트-행) · `HMI (PB)` · `SWGR` · `LOGIC`.  `TO` = `SWGR` · `LOGIC` · `HMI` · `NOTE 1` → NOTE 줄이 `G030-32, G032-4, G035-14` 를 늘어놓는다.  시트 안 연결은 동그라미 번호(①~⑨)·글자(A · I · R · S) | 스타디움 `21 / G029`(번호 / 시트 — **Logic 시트를 가리킨다**) · `13 / P032` · `7A / ESD` · 동그라미 A · 삼각 A(경보) | ★ **from-to 가 표로 그려져 있어 규칙이 단단하다** |
| S7 | 범례 시트 | G003(기호 · 선 글자) · G004(약어 · 진짜 글자) · G005/G006(Typical · 설명 칸이 진짜 글자) | P003~P005(기호 · 신호선 종류 · 연산 기호) | 블록 사전은 범례에서 |
| S8 | 타이틀블록 | `SHEET NO.` 칸 진짜 글자 — 모양 `L1D3`(G034) · Loop 는 `L1D3L1`(P020A 꼴 하위 장)도 | 같음 | 시트 번호는 그대로 읽힌다 (51/53 · 39/46 — 나머지는 표지·하위 장) |
| S9 | 계기 표기 | KKS 칸 · 제목에 KKS(`10HAD35AA041`) | 측정 스타디움 1줄 KKS(`10HAD80CL001A`) + 2줄 신호 꼬리(`XQ01`·`XK11`) | P&ID 대조 열쇠 = KKS (TAKHIATASH P&ID 는 1급 — hotfix84 1067/1139행 태그) |
| S10 | 회전 · 크기 | A3 가로 1191×842 · 회전 0 · 표지만 A4 | 같음 | 회전 처리 불필요 |
| + | 개정 표시 | 빨강(1,0,0) 클라우드 + △2 — 11장 | 27장 | 잉크 규칙대로 판정에서 뺀다 · "Rev.2 에서 바뀐 자리" 로 따로 보일 수 있다 |
| + | 도면 목록 | G001 · P001 — **선 글자**로 `NO · DRAWING TITLE · PAGE NO` | 같음 | §1-2 의 열쇠 · 목록 ↔ 실제 장 대조 규칙(D1) |

### 1-2. 선 글자를 읽는 길 — 도면 묶음 안의 짝으로 사전을 만든다

S2 때문에 이대로는 태그·참조·블록 글자를 **한 글자도** 못 읽는다.  P&ID 45회차는 획 글자를 읽다
실패했다 (사전을 *다른 크기의* 글자에서 만들어 획 굵기 비가 갈렸다).  이 묶음은 사정이 다르다 —
**같은 CAD 글꼴 · 같은 높이의 같은 글자는 거의 같은 선으로 그려진다.**  실측(숫자):

* Logic G034 의 `NO.` 열(행 1~62)은 **구조가 답을 준다** — k번째 행의 글자는 `k` 다.  여기서 숫자 0~9 의
  모양을 배워(12×12 래스터) **다른 네 장**(G010 · G030 · G040 · G049)의 같은 열을 읽으니 **248/248 정답**
  (최저 일치도 0.75 · 다른 숫자와의 최고 일치도 0.70 — 빈 띠가 좁다 → 문턱은 구현 때 분포로 다시 잰다).

글자(A~Z · 기호)의 짝도 묶음 안에 있다 — **진짜 글자로 같은 말을 한 자리**:

| 짝 | 선 글자 쪽 | 진짜 글자 쪽 | 주는 것 |
| --- | --- | --- | --- |
| ① 행 번호 | 표의 `NO.` 열 | 행의 순서 (구조) | 숫자 0~9 |
| ② 도면 목록 | G001/P001 의 `PAGE NO` · `DRAWING TITLE` 칸 | 각 장 타이틀블록의 `SHEET NO.` · 부제 (진짜 글자) | `G` `P` · 제목 낱말의 글자 대부분 · 제목 속 KKS(`10HAD35AA041`) |
| ③ Typical | G010~G013 의 설명 칸 (선) | G005/G006 의 같은 칸 (진짜 글자 — `AUTO START` · `LOGIC` · `HMI`) | 설명 낱말 |
| ④ 범례 약어 | 본문 블록의 `A_on` · `OVRID1` · `FDbK1` | G004 약어표 (진짜 글자) | 블록 단자 이름 (대소문자는 주의) |

* 짝을 맺는 열쇠는 **자리(표의 같은 행·같은 칸)와 순서**다 — 글자를 추측하지 않는다.
* 사전에 없는 모양은 **비우고 사유**(`GLYPH_UNKNOWN`)를 남긴다.  남은 모양이 있으면 사람이 **한 번** 이름을
  붙이고(3급 · 31·45회차와 같은 규율 — 작성자 필수), 같은 글꼴을 쓰는 다음 리비전이 그대로 쓴다.
* 판독마다 일치도와 2위와의 차를 근거로 남긴다.  2위와 붙으면 판정하지 않는다.
* LLM · OCR 은 쓰지 않는다.
* **더 싼 길이 있다 (Q13)**: 설계사에 AutoCAD `PDFSHX=1` 로 다시 출력해 달라고 하면 선 글자 원문이
  `AutoCAD SHX Text` 주석으로 들어오고(UAD 가 그랬다), 이 프로그램은 이미 그것을 읽는다
  (`pidcache._shx_entries`).  DWG/DXF 원본을 받아도 된다.  그러면 §1-2 의 사전이 필요 없다.

## 2. 재사용 — 있는 것부터 (§9-3)

| 필요 | 이미 있는 것 | 그대로 부르나 | 주의 |
| --- | --- | --- | --- |
| PDF 열기 · 낱말 · SHX 글자 · 회전 | `pidcache.load_pages(pdf)` → `PageCache` | **예** | import 하면 `projectconfig.load()` 가 돈다(기본 alnouf1).  LOGIC 은 config 를 읽지 않으므로 무해하지만, **`app.engine.pidcache` 로 import 하지 말고** pipeline 처럼 `app/engine` 을 `sys.path` 에 넣고 `import pidcache` (안 그러면 모듈이 둘이 된다) |
| 직선 선분 | `PageCache.segments()` | 예 | `l` 만 — 블록 사각형(`re`)·곡선 게이트는 `drawings()` 에서 직접 · 점은 **캐시 원본**이라 고치지 않는다 |
| 사각형 · 곡선 범위 | `PageCache.drawings()` · `pidcache.round_box` · `curve_extent` | 예 | `drawings()` 의 `items` 는 회전 전 좌표 — `Rot(page.rotation_matrix)` 를 곱한다 |
| 낱말 → 줄 | `pidcache.same_lines` (글자 높이로 줄을 묶는다 · 상수 없음) | 예 | 버킷 5pt 방식(`pipe_graph._connector_labels`)은 **쓰지 않는다** — 실패 유형 ④ |
| 낱말 쪼개기 | `pidcache.tokens` | 예 | |
| 수평·수직 획 색인 · "이 구간이 그려졌나" | `legend_rules.stroke_index` · `covers` | 예 | 수평·수직만.  다 쓰면 `release_stroke_memo()` |
| 끊긴 일직선 잇기 | `describe_axis.standard_break` · `bridge_collinear` | 패턴만 베낀다 | 문턱이 P&ID 범례 값에 묶여 있다 — LOGIC 은 S5 분포로 다시 잰다 |
| 런 병합 · 파선 사슬 · 허용 격자 노드 | `pipe_graph._merge_runs` · `_dashed_chains` · `build` 의 노드 격자 | 패턴만 베낀다 | `build` 는 배관용(신호선은 그래프 밖) · 추적 성공률 10~13% 기록(`docs/from_to_axis.md`) |
| 도면번호 칸 · REV | `derive_layout.derive(pages)` → `Layout` | **예** (순수) | `CFG.overlay` 는 **부르지 않는다** (전역 config 를 바꾼다 — 실패 유형 ⑨) |
| 도면번호 꼴 학습 | `derive_layout._drawing_no_shapes` · `_drawing_no_pattern` (두 장 이상 되풀이되는 모양) | 예 | 시트 간 참조 안의 도면번호를 읽는 데 그대로 쓴다 |
| 도면번호 읽기 | `extract_titleblocks.parse_drawing_no(pd, lay)` | 예 — **`lay` 를 반드시 넘긴다** | 기본값은 AL NOUF1 좌표 · 모듈 전역에 대입하지 않는다 |
| 사람이 고친 도면번호 | `app/sheet_numbers.py` 의 모양 | 패턴만 | 파일은 LOGIC 전용으로 따로 |
| 태그 체계 | `tags.shape` · `tags._is_code` · `tags.grammar` · `code_of` | 예 (순수) | `assign` 은 "검출 사각형" 전제 — LOGIC 은 shape 반복 규칙(두 곳 이상 · 두 장 이상)만 베낀다 |
| ISA 첫 글자 뜻 | `isa_table.derive(pages, cfg)` | 예 | Logic PDF 에는 ISA 표가 없을 것 — 그러면 **같은 프로젝트 P&ID 결과의 ISA 표**를 쓴다(§5) |
| P&ID 행 | `db.merged_rows(con, job_id)` (사람 값 우선) · `revisions.load_project` | 예 (읽기만) | 프로젝트의 최신 P&ID job 은 `_project_public` 과 같은 방식으로 고른다 |
| O/X | `row_verdict` + `db.set_verdict` | 패턴만 — 새 표 `logic_verdict` | `row_verdict` 는 `job` 에 묶여 있다 |
| Excel | `verdict_export.build` (openpyxl) | 패턴만 | 열 목록이 P&ID 전용 |
| VOC | `voc.write(record, crop_png)` (파일 기반) | 예 | `SOURCES` · `CATEGORIES` 가 닫힌 사전 — §8 질문 Q7 |
| 원자적 JSON 저장 | `jsonstore.write` · `read` | 예 | |
| 데이터 폴더 | `paths.data_dir()` (`PID_DATA_DIR` 로 시험 격리) | 예 | LOGIC PDF 는 `{data}/logic/` 에 — `{data}/uploads` 에 두면 `audit.leftovers` 가 고아로 센다 |
| 시험 격리 | `conftest.py` (실 DB 를 열면 실패 · 끝에 sha256 확인) | 그대로 | LOGIC 시험도 `TestClient(main.app)` + 임시 데이터 폴더 |

**없는 것 (새로 만든다)**: 블록 검출 · 단자(입출력 점) 찾기 · 신호선 그래프(대각선 포함) ·
시트 간 참조 파싱과 짝 맞추기 · LOGIC 결과 화면 · LOGIC Excel.

---

## 3. 데이터 구조

### 3-1. 엔진 결과 (JSON 한 파일 · `{data}/logic/{job_id}/result.json`)

P&ID 와 같은 원칙: **사실만 저장하고 문장은 화면이 그때 만든다** (CLAUDE.md §8 "화면이 말할 문장을 데이터에 저장하지 마세요").

```jsonc
{
  "schema": 1,
  "job_id": "…", "project": "…", "kind": "LOGIC|LOOP|SYSTEM|MIXED",
  "sheets": [ { "page_no": 3, "drawing_no": "…|null", "drawing_no_source": "TITLEBLOCK|USER|null",
                "rev": "…|null", "readable": true, "unreadable_reason": null,
                "text_source": {"words": 812, "shx": 0, "image_area_ratio": 0.0} } ],
  "derived": { /* 이 묶음에서 잰 값과 근거 — P&ID legend_rules.Derived 와 같은 꼴 */
    "ref_pattern":   {"values": {...}, "source": "DERIVED|USER|MISSING", "note": "…", "evidence": [...]},
    "gap_threshold": {"values": {"bridge": 0.0}, "source": "…", "histogram": [...]},
    "block_kinds":   {"values": {...}, "source": "LEGEND|BODY|USER|MISSING"} },
  "blocks":  [ { "id": "p3:b12", "page_no": 3, "rect": [x0,y0,x1,y1], "kind": "AND|OR|NOT|TIMER|FUNC|UNKNOWN",
                 "kind_source": "TEXT|SHAPE|LEGEND|null", "label": "…", "tags": ["…"],
                 "ports": [ {"id": "p3:b12:i0", "side": "IN|OUT|null", "xy": [x,y]} ] } ],
  "signals": [ { "id": "p3:s40", "page_no": 3, "polyline": [[x,y],…], "ends": ["p3:b12:o0", "p3:r5" | null] } ],
  "refs":    [ { "id": "p3:r5", "page_no": 3, "rect": [...], "dir": "TO|FROM|null",
                 "target_sheet": "…|null", "target_grid": "3-B|null", "ref_no": "…|null",
                 "signal_name": "…|null", "raw": "TO SH.5 (3-B) A-102" } ],
  "tags":    [ { "tag": "FT-1001", "page_no": 3, "rect": [...], "role": "BLOCK|LOOP_INSTRUMENT|REF|FREE" } ],
  "findings": [ { "key": "C1:p3:r5", "rule": "C1", "grade": "ERROR|REVIEW", "page_no": 3, "rect": [...],
                  "subject": ["p3:r5"], "facts": { "target_sheet": "5", "looked_in": [5] } } ],
  "pid_compare": { "pid_job_id": "…|null", "coverage": {...}, "unreadable": "…|null" }
}
```

* `findings[].key` 는 **규칙 + 대상 id** 로 만든다 — 같은 PDF 를 다시 돌려도 같은 열쇠가 나와 O/X 가 이어진다.
* `facts` 는 판정에 쓴 숫자·낱말 그대로.  "왜 오류인가" 문장은 화면의 `explain(rule, facts)` 하나가 만든다.
* 못 읽은 값은 `null` + 같은 자리의 `*_source: null` · 사유는 `unreadable_reason` 또는 `derived.*.note`.

### 3-2. DB — **새 표만** (기존 표·열 변경 없음)

`app/logic/store.py` 가 시작할 때 `CREATE TABLE IF NOT EXISTS` 로 만든다 (`db.py` 를 고치지 않는다).

| 표 | 열 | 뜻 |
| --- | --- | --- |
| `logic_job` | `id` PK · `project` · `kind` · `pdf_name` · `pdf_path` · `status` · `stage` · `error` · `created_at` · `finished_at` · `result_path` · `pid_job_id` | 업로드 한 번 = 한 줄.  `pid_job_id` 는 대조에 쓴 P&ID job (그때의 것을 기록) |
| `logic_sheet` | `job_id` · `page_no` · `drawing_no` · `rev` · `readable` · `reason` | 장 목록 (화면의 장 넘김 · Excel 시트 목록) |
| `logic_finding` | `job_id` · `key` · `rule` · `grade` · `page_no` · `rect_json` · `facts_json` · `added`(사람이 더함) · `deleted` | 판정 목록.  사람이 마크업으로 더한 지적도 같은 표(`added=1`) |
| `logic_verdict` | `job_id` · `key` · `verdict`(O/X/'') · `author` · `note` · `updated_at` | 사람의 O/X — `row_verdict` 와 같은 꼴 |
| `logic_user_value` | `job_id` · `subject_id` · `field` · `value` · `author` · `updated_at` | 사람이 고친 값(도면번호 · 참조 대상 · 블록 종류) — 엔진 값을 덮지 않고 옆에 둔다 |

* 프로젝트·job 을 지울 때 LOGIC 표도 지워야 한다 — 기존 `delete_job`/`delete_project` 는 LOGIC 표를
  모른다.  **LOGIC 쪽 삭제 API 를 따로** 두고, 프로젝트 삭제와 엮는 한 줄은 §8 Q8 로 묻는다.

---

## 4. 판정 규칙 — 무엇을 오류로 보나

공통:
* **등급 둘** — `ERROR`(도면 근거로 확정) · `REVIEW`(규칙은 걸렸지만 읽기가 불확실 · 사람이 본다).
  읽기 자체가 실패한 자리는 판정을 **내지 않고** 사유만 남긴다 (오류를 지어내지 않는다).
* **문턱은 그 묶음의 분포에서** 잰다.  빈 띠가 없으면 그 규칙은 `REVIEW` 로만 낸다 (§4 절차 3).
* 모든 지적은 **도면 위 자리(rect)** 를 갖는다.  자리가 없는 지적은 만들지 않는다 (X2 는 예외 — P&ID 쪽 자리를 단다).

### 4-1. 연결 적합성 (도면 안)

| 규칙 | 조건 | 등급 | 근거 · 가정 (S# = §1 측정) |
| --- | --- | --- | --- |
| **C1 짝 없는 시트 간 참조** | 시트 A 의 `TO <B>` 가 있는데 B 장에 A 를 가리키는 `FROM` 이 없다 (또는 그 반대) | ERROR — 두 장 다 읽혔을 때만 | 짝의 열쇠(시트 번호 · 도면번호 · 신호 번호 · 좌표)는 **S6 이 정한다**.  열쇠가 셋 중 하나만 읽히면 REVIEW |
| **C2 대상 시트가 묶음에 없음** | `TO <B>` 의 B 가 업로드 묶음의 어느 장에도 없다 | REVIEW | 다른 PDF 에 있을 수 있다 — "없음" 이 아니라 "**이 묶음에서 못 찾음**".  여러 PDF 를 한 묶음으로 올리면 줄어든다 |
| **C3 참조 번호 중복** | 같은 참조 번호(또는 같은 `TO B · 3-B`)가 한 장 안 두 자리, 또는 같은 방향으로 두 장에서 쓰인다 | ERROR | 한 신호가 여러 곳으로 가는 표기(1:N)가 정상인 도면이 있을 수 있다 — **범례/주석이 1:N 을 말하면 제외**, 말하지 않으면 Q4 |
| **C4 짝은 있으나 내용이 다름** | 짝이 맞은 TO/FROM 의 신호 이름·태그가 서로 다르다 | ERROR | 비교는 정규화 없이 글자 그대로 → 다르면 지적, 구분자만 다르면 REVIEW (Q5) |
| **C5 끊긴 선** | 신호선 끝이 블록 단자 · 참조 기호 · 다른 선(접합) 어디에도 닿지 않는다 | ERROR / REVIEW | "닿음" 의 거리는 S5 **끊김 간격 분포의 빈 띠**로 정한다.  빈 띠가 없으면 REVIEW.  절대 pt 를 박지 않는다 |
| **C6 연결 안 된 단자** | 블록의 입출력 단자(짧은 꼬리선 또는 단자 표시)에 선이 없다 | ERROR | 단자를 **도면이 그리면**(꼬리선·점) 읽는다.  안 그리면 단자 수를 알 수 없으므로 이 규칙은 **꺼진다**(사유 표시) |
| **C7 입력 없는 블록 / 출력 없는 블록** | 논리 게이트·타이머의 입력이 0, 또는 출력이 어디에도 안 간다 | ERROR | 블록 종류가 읽혔을 때만.  `UNKNOWN` 블록은 REVIEW |
| **C8 출력끼리 이어짐** | 한 신호선이 두 블록의 **출력**을 잇는다 | REVIEW | 단자의 입출력 방향을 도면이 말할 때만(화살표 · 좌입력/우출력이 범례로 정의됨).  방향을 **위치로 추측하지 않는다** |

**입출력 방향을 어디서 읽나** — ① 범례 시트의 블록 그림(입력 쪽 · 출력 쪽) ② 선 끝 화살표
③ 블록 안 단자 글자(`IN`/`OUT`/`Q`) — 셋 다 없으면 C6~C8 의 방향 판정을 하지 않는다 (Q6).

### 4-1b. 이 양식(표 형식 Logic · 스타디움 참조 Loop)에서 C 규칙이 서는 모양 — 실측 반영

S6 이 보여 준 대로 TAKHIATASH Logic 은 **from-to 를 표로 그린다**.  그래서 C1~C7 이 "선을 따라가는" 일보다
**표의 칸을 맞대는** 일이 된다 — 선 추적(P&ID 성공률 10~13%)에 기대지 않는다.  아래 규칙의 **표 모양**
(입력 1~62 · 출력 63~124 · 칸 이름)은 코드에 적지 않는다 — 표 머리말 줄(`FM` · `NO.` · `TO`)과 행 번호 열이
**그 장에서** 칸 경계와 행 높이를 준다 (모든 장이 같은 모양이면 그 사실이 근거).

| 규칙 | 이 양식에서의 조건 | 근거 |
| --- | --- | --- |
| **L-C1 짝 없는 시트 간 참조** | 입력 행의 `FM` 이 `G031-81` 이면 G031 의 **출력 행 81** 이 있어야 하고 그 행의 `TO`(또는 `NOTE k` 가 늘어놓은 목록)에 `G034-7`(이 장-이 행)이 있어야 한다.  반대 방향도 | 행 번호 = 위치(표) · 시트 번호 = 타이틀블록 진짜 글자 |
| **L-C2 대상 시트가 묶음에 없음** | `G039-8` 처럼 가리킨 시트가 묶음에도 도면 목록(G001)에도 없다 · 목록에는 있는데 묶음에 없다 | 실측 *(가설 — 눈으로 읽음)*: G034 NOTE 2 가 `G039-8` 을 적는데 G039 는 목록·묶음 어디에도 없다 |
| **L-C3 참조 번호 중복** | 한 출력 행을 둘 이상이 가리키는 것은 정상(1:N · NOTE 목록) — 대신 **같은 입력 행에 FM 이 둘**, 또는 **두 출력 행이 같은 곳을 가리킴**을 본다 | 1:N 은 도면이 NOTE 로 정의한다 |
| **L-C4 짝은 있으나 설명이 다름** | 짝이 맞은 두 행의 `DESCRIPTION` · `KKS NO.` 가 글자 그대로 다르다 → REVIEW(낱말 수준 차이를 보인다) | 판정하지 않고 보인다 |
| **L-C6 연결 안 된 행** | 설명이 있는 입력/출력 행인데 그 행 높이에서 LOGIC 칸 경계를 지나는 신호선이 없다 · 반대로 설명이 빈 행에 선이 들어온다 | 순수 기하 — 행 띠와 LOGIC 칸 테두리의 교차.  글자를 몰라도 "설명 칸에 잉크가 있나" 로 1차 판정 가능 |
| **L-C7 시트 안 연결 기호 짝** | 동그라미 번호·글자(①~⑨ · A · I · R · S) 가 한 장 안에서 **들어가는 쪽(화살촉)** 과 **나오는 쪽**을 다 갖는다 | 화살촉이 방향을 준다 (G003 범례) |
| **L-C5 끊긴 선** | 신호선 끝이 블록·연결 기호·점·다른 선·표 칸 경계 어디에도 안 닿는다 | 끊김 분포는 L2 첫 단계에서 잰다 |
| **D1 도면 목록 ↔ 실제 장** | 목록(G001 · P001)의 `PAGE NO` 가 묶음에 없음 · 묶음의 장이 목록에 없음 · 목록 제목 ≠ 타이틀블록 부제 | 실측 *(눈)*: 목록 `LV SWITCHGEAR BLOCK` ↔ G010 타이틀블록 `LV SWITHGEAR BLOCK` (철자) |
| **L-P1 Loop → Logic 참조** | Loop 스타디움 `21 / G029` → Logic G029 에 **행 21** 이 있고 그 행의 FM/TO 가 이 Loop 장(`P030`)을 말한다 | *(가설)* 번호의 뜻(행 번호인지 신호 번호인지)을 선 글자를 읽은 뒤 확인한다 — 틀리면 이 규칙을 지운다 (Q15) |
| **L-P2 Loop 측정 ↔ I/O 기호** | 측정 스타디움 2줄 꼬리(`XQ01` · `XK11`)와 그 아래 AI/DI 삼각형이 범례(P004/P005)가 정한 짝과 다르다 | 범례가 짝을 정의할 때만 · 아니면 끈다 (Q16) |

* **개정 클라우드(빨강)는 판정에 넣지 않는다** — P&ID 잉크 규칙과 같다.  다만 "Rev.2 에서 바뀐 자리" 로
  지적 옆에 표시해 두면 검토자가 바뀐 곳부터 본다 (Logic 11장 · Loop 27장).

### 4-2. 정합성 (같은 프로젝트 P&ID 와 대조)

| 규칙 | 조건 | 등급 | 근거 |
| --- | --- | --- | --- |
| **X1 LOGIC/Loop 에만 있는 태그** | 태그가 이 묶음에 있는데 프로젝트 최신 P&ID 결과에 없다 | REVIEW | P&ID 가 일부러 빼는 것이 있다 — PSV(`policy.not_identified_tags`) · 제어실 기능 버블(`policy.control_room_functions`).  **그 정책으로 빠진 태그는 "P&ID 정책 제외" 로 따로 센다** — 오류가 아니다 |
| **X2 P&ID 에만 있는 계기** | P&ID 계기 태그가 Loop 묶음에 없다 | REVIEW | Loop 묶음이 전체인지 일부인지 도면이 말하지 않는다 → 범위를 사람이 정한다 (Q3).  자리는 P&ID 쪽(장·사각형) |
| **X3 같은 루프, 다른 기능** | 루프 번호가 같은데 기능 글자가 다르다 (`FT-1001` ↔ `FIT-1001`) | REVIEW | 루프 번호 / 기능 글자 분해는 `tags.grammar` + ISA 표로.  분해가 안 되는 태그 체계(KKS 등)는 이 규칙이 꺼진다 |
| **X4 Loop 계기 ≠ P&ID 계기** | Loop 도면의 계기 태그가 P&ID 에 있는데 종류(TYPE)가 다르다 | ERROR | 태그가 글자 그대로 같고 양쪽 TYPE 이 둘 다 읽혔을 때만 |

### 4-3. 태그를 어떻게 맞추나

1. **열쇠는 글자 그대로**(앞뒤 공백만 뺀다) — `revisions._tag_key` 와 같은 태도.
2. 글자 그대로 안 맞고 **구분자(`-` `_` 공백 `.`)만 빼면 맞는** 경우는 "**표기만 다름**" 으로 따로 모은다 — 같은 것으로 치지 않는다 (Q5 답 전까지).
3. 짝은 **양쪽에서 유일할 때만** 맺는다 (`revisions._tag_matches` 와 같은 원칙 — 짝이 여럿이면 판정하지 않는다).
4. P&ID 쪽 태그는 `db.merged_rows` 의 **사람 값 우선** `values.tag_no`.
   ⚠ **2급 프로젝트(AL NOUF1 · TC2 · SADARA)는 P&ID 행에 태그가 없다**(Tag 칸 `.....`).  그러면
   대조를 하지 않고 "**P&ID 결과에 태그가 없어 대조 불가 — N행 중 태그 있는 행 M**" 을 화면 첫 줄에 말한다.
   태그가 인쇄된 1급 프로젝트(UAD 등)에서만 X1~X4 가 의미 있다.
5. LOGIC 쪽 "태그" 는 `tags.shape` 반복 규칙으로 고른다 — **같은 모양이 두 곳 이상 · 두 장 이상**.
   한 번만 나오는 낱말은 태그로 치지 않는다 (CLAUDE.md §10 "태그는 사고가 아니라 체계다").
   추가로 P&ID 결과의 태그 모양 집합과 겹치는 모양이면 신뢰를 올린다(근거에 적는다).

---

## 5. 처리 순서 (`app/logic/analyse.py`)

```
업로드 ─▶ load_pages(pdf)                                  (pidcache — 그대로)
       ─▶ 장마다 글자 출처 재기 (S1/S2)  ── 읽을 글자가 없으면  LogicUnreadable(사유) 로 멈춤
       ─▶ derive_layout.derive(pages) → 도면번호 칸 · 도면번호 꼴 (S8)
       ─▶ 범례 장 찾기 (S7) → 블록 사전 · 방향 규칙 · 참조 기호 모양   (없으면 MISSING · 사유)
       ─▶ 장마다: 블록(닫힌 도형) · 단자 · 신호선(병합 · 끊김 다리) · 참조 기호 · 태그
       ─▶ 분포에서 문턱 재기 (S5 끊김 간격)  — 빈 띠 없으면 C5 는 REVIEW 로만
       ─▶ 묶음 전체: 참조 짝 맞추기 → C1~C4 · 장마다 C5~C8
       ─▶ 프로젝트 최신 P&ID job 읽기 → X1~X4 (P&ID 태그 없음이면 대조 불가 사유)
       ─▶ result.json · logic_* 표 저장
```

* 분석은 **별도 스레드/프로세스** 하나 — P&ID 분석과 같은 대기열을 쓰지 않는다(서로 막지 않게).
  진행 단계(`stage`)를 `logic_job` 에 적어 화면이 보여 준다.
* **config 를 건드리지 않는다.**  LOGIC 은 `projectconfig` 의 어떤 값도 읽지 않고 쓰지 않는다
  (P&ID 의 `_own_config` 같은 장치가 필요 없게).  pidcache import 때 도는 `load()` 는 읽기만이다.

### 못 읽으면 멈춘다 (§9-4)

| 사유 | 화면 문장(예) | 다음 |
| --- | --- | --- |
| S-1 글자가 없다 (스캔 · 이미지) | "이 PDF 는 글자층이 없고 그림으로만 되어 있어 읽을 수 없습니다 (장 N 중 N)" | 멈춘다 · OCR 은 하지 않는다(Q9) |
| S-2 글자가 획으로만 있다 (SHX 주석 없음) | "본문 글자가 선으로 그려져 있습니다 — 이 묶음의 글자 사전으로 N개 중 M개를 읽었습니다" | **멈추지 않는다** (§1-2 사전).  사전에 없는 모양은 비우고 사유 · 그 칸에 걸린 규칙은 REVIEW · 사전이 아예 서지 않으면(짝이 없음) 그때 멈춘다 |
| S-3 도면번호를 한 장도 못 읽음 | "시트 번호를 읽지 못해 시트 간 참조를 확인할 수 없습니다" | C1~C4 끄고 C5~C8 만 · 사람이 장마다 번호를 넣으면 다시 판정 |
| S-4 참조 기호를 한 개도 못 찾음 | "시트 간 참조 표기를 찾지 못했습니다" | C1~C4 끄고 계속 · 사유 표시 |
| S-5 같은 프로젝트에 P&ID 결과가 없음 | "같은 프로젝트에 P&ID 분석이 없어 대조하지 않았습니다" | X1~X4 끄고 계속 |

---

## 6. 화면 흐름

```
첫 화면 왼쪽 메뉴:  홈 · 프로젝트 · [LOGIC 검토]  ← 한 줄 추가
  └ LOGIC 검토 첫 화면: 프로젝트 고르기 → PDF 올리기(여러 개 = 한 묶음) → 진행 막대
      └ 결과 화면 (P&ID 결과 화면과 같은 배치)
         ┌ 머리줄: 프로젝트 · 묶음 이름 · 대조한 P&ID 리비전 · 못 읽은 것 요약 · [Excel] [VOC]
         ├ 왼쪽: 지적 목록 — 규칙별 묶음(C1…X4) · 등급 · O/X 칸 · 비고 · 필터(미확인만 / X 만)
         ├ 가운데: 도면 — 지적 자리에 상자(빨강=ERROR · 주황=REVIEW · 회색=사람이 O 처리)
         │         시트 간 참조는 짝을 선으로 이어 보이기(누르면 상대 장으로 이동)
         └ 오른쪽: 근거 패널 — 그 지적의 facts 를 문장으로 · 관련 블록/선/참조 강조
      마크업: 도면에 사각형 → "놓친 지적 추가" (사유 필수 · VOC 로 같이 보내기 기본 켬)
              기존 상자 누르고 "오지적" → O/X 의 X 와 같은 뜻으로 저장
```

* 화면 파일: `app/static/logic.js` · `logic.css`.  `app.js` 의 해시 라우팅이 `#logic/…` 를 job id 로
  오해하지 않게 하는 **가드 한 줄**만 `app.js` 에 넣는다.
* 도면 그림: LOGIC 전용 `GET /logic/jobs/{id}/page/{n}.png` (P&ID 쪽은 `job` 표에 묶여 있어 못 쓴다).
* 대시보드 임베드(`?embed=1&mode=&user=`)는 같은 index.html 이므로 그대로 따라온다 — 작성자 이름도 같은 곳에서.

## 7. Excel

시트 셋: **① 지적 목록**(규칙 · 등급 · 장 · 도면번호 · 대상 · 사실 · O/X · 확인자 · 비고)
**② 시트 간 참조 표**(장 · 방향 · 대상 장 · 좌표 · 번호 · 짝 상태) **③ P&ID 대조표**(태그 · LOGIC 장 ·
P&ID 장 · 상태: 양쪽/LOGIC만/P&ID만/정책제외/표기만 다름).  첫 줄에 "못 읽은 것" 요약.
openpyxl 로 새로 만든다(발주처 양식 아님) — 양식이 정해져 있으면 Q10.

---

## 8. 도면이 답하지 않는 것 — 사람에게 묻는 자리 (질문 목록)

| # | 물음 | 왜 도면이 답하지 못하나 | 답이 없을 때 기본값 |
| --- | --- | --- | --- |
| ~~Q1~~ | ~~샘플 PDF~~ | **받음** — HRSG Logic · Loop Rev.2 (TAKHIATASH).  System Diagram 샘플은 아직 없다 | System 은 같은 틀로 받으면 그때 잰다 |
| ~~Q2~~ | ~~도면의 출처~~ | **답이 나왔다** — 설계사(Hyundai Engineering) AutoCAD 2018 출력 · SHX 글자가 획으로 | — |
| Q3 | **X2 의 범위** — Loop 묶음은 프로젝트 전체 루프인가, 일부(한 계통)인가 | 묶음이 전체인지 도면이 말하지 않는다 | 묶음에 나온 **루프 번호 범위/계통** 밖의 P&ID 계기는 X2 로 내지 않는다 |
| Q4 | 한 시트 간 참조가 여러 장으로 가는 표기(1:N)가 정상인가 | 회사·업체 관행 | 범례가 말하지 않으면 C3 을 REVIEW 로 |
| Q5 | `FT-1001` 과 `FT1001` 을 같은 태그로 볼 것인가 | 표기 관행 | 같지 않음 · "표기만 다름" 으로 따로 보여 줌 |
| Q6 | 블록 입출력 방향을 도면이 안 그릴 때 "왼쪽 입력 · 오른쪽 출력" 을 가정해도 되나 | 방향 가정은 도면 밖 지식 | 가정하지 않음 · C8 끔 |
| Q7 | VOC 분류에 `LOGIC` 입구 하나를 더해도 되나 (`app/voc.py` 의 사전에 한 줄) | 기존 파일 수정 | 더하지 않고 `GENERAL` + 본문 머리 `[LOGIC]` |
| Q8 | P&ID 프로젝트를 지울 때 LOGIC 결과도 같이 지울 것인가 (`delete_project` 에 한 줄) | 기존 파일 수정 | 같이 지우지 않음 · LOGIC 화면에서 따로 지움 |
| Q9 | 스캔 도면이 오면 — 멈출 것인가, OCR 을 붙일 것인가 | 글자를 지어낼 위험 | 멈춘다 |
| Q10 | LOGIC Excel 에 정해진 양식이 있나 | — | §7 의 새 양식 |
| Q11 | 정합성에서 제어실 기능(LICA 등)·PSV 처럼 **P&ID 가 정책으로 뺀 태그**를 LOGIC 에서는 어떻게 보이나 | 정책은 P&ID 산출물용 | "정책 제외" 로 따로 세고 오류로 내지 않음 |
| Q12 | 리비전 비교(LOGIC Rev.A ↔ Rev.B) 가 필요한가 | — | 첫 판은 하지 않음 |
| **Q13** | **선 글자를 어떻게 읽을까** — (가) 설계사에 AutoCAD `PDFSHX=1` 로 다시 출력해 달라고 하거나 DWG/DXF 를 받는다 (권장 · 가장 확실) (나) §1-2 의 "묶음 안 짝" 으로 글자 사전을 만든다 (다) 둘 다 — (가)를 요청해 두고 (나)로 먼저 간다 | 글자가 선이라 도면이 원문을 주지 않는다 | (다) |
| Q14 | 사전에 없는 선 글자 모양에 사람이 **한 번** 이름을 붙이는 화면을 둘까 (31·45회차와 같은 규율 · 작성자 필수) | 짝이 없는 글자(희귀 기호)는 도면이 이름을 주지 않는다 | 둔다 |
| Q15 | Loop 스타디움 `21 / G029` 의 `21` 은 Logic G029 의 **행 번호**인가 (실측으로 확인하겠지만 관행을 알면 빠르다) | 범례가 그 기호를 정의하지 않는다 | 선 글자를 읽은 뒤 맞대 보고 맞으면 L-P1 을 켠다 |
| Q16 | Loop 측정 꼬리 `XQ01`(아날로그) · `XK11`(디지털) 같은 신호 꼬리 체계를 검사 대상으로 볼까 | 회사 체계 | 범례가 정의하면 켜고 아니면 끈다 |
| Q17 | 개정 클라우드(빨강) 안의 지적을 따로 표시할까 | — | 표시만 (판정에는 안 넣는다) |
| Q18 | P&ID 대조 상대 — 같은 프로젝트 TAKHIATASH P&ID 분석(hotfix84 binder)을 이 서버의 같은 프로젝트에 두면 X1~X4 가 돈다.  Logic 의 KKS(`10HAD35AA041` 밸브 · `10HAD80CL001A` 계기)를 P&ID 의 계기·밸브 태그와 둘 다 대조할까 | — | 둘 다 |

---

## 9. 기존 파일에 손대는 자리 (전부)

| 파일 | 무엇을 | 줄 |
| --- | --- | --- |
| `app/main.py` | `from app.logic import api as logic_api` · `app.include_router(logic_api.router)` (static mount 앞) | 2 |
| `app/static/index.html` | 메뉴 `<a class="nav-item" href="#logic">LOGIC 검토</a>` · `logic.js`/`logic.css` 태그 | 3 |
| `app/static/app.js` | 해시 라우팅이 `#logic` 을 넘기는 가드 | 1~2 |
| `.gitignore` | `data/logic/` 확인 — 이미 `data/**/*.pdf` 로 걸린다 · 렌더 조각 폴더 추가 | 1 |
| (Q7 · Q8 승인 시) `app/voc.py` · `app/db.py` | 각 한 줄 | — |

`app/engine/*` · `app/pipeline.py` · 기존 DB 표 — **0 줄**.

## 10. 구현 단계 (승인 뒤)

| 단계 | 내용 | 끝났다는 기준 |
| --- | --- | --- |
| ~~L1~~ | `spike/logic_survey.py` — §1 측정 · 렌더 | **끝** (이 문서 §1) |
| **L1b** | `app/logic/glyphs.py` — §1-2 선 글자 사전 (짝 ①~④ · 일치도 · 2위와의 차 · 모르는 모양은 비움) | 두 샘플에서 표 칸(FM · NO. · TO · 시트 참조)을 읽어 **눈으로 맞댄 표본**의 정답률과 못 읽은 칸 수 보고 · Q13 답에 따라 범위 조정 |
| L2 | `app/logic/read.py` — 표 칸 · 블록 · 단자 · 신호선 · 연결 기호 · 태그 읽기 | 샘플마다 도면 위 표시를 렌더로 눈 확인 · 놓친 것/잘못 잡은 것 수 보고 |
| L3 | `app/logic/rules.py` — L-C1~L-C7 · D1 · L-P1/2 (그다음 일반 C5·C8) | 규칙마다 합성 PDF 시험(정상 1 · 오류 1) + 샘플 실측 |
| L4 | `app/logic/compare.py` — X1~X4 | 시험용 P&ID job 을 임시 DB 에 만들어 대조 시험 |
| L5 | `app/logic/api.py` · `store.py` · `logic.js` — 화면 · O/X · 마크업 · VOC · Excel | API 시험 + 화면 캡처 |

* 시험은 `tests/test_logic_*.py` — `conftest.py` 격리 그대로, 합성 PDF 는 시험 안에서 pymupdf 로 그린다
  (고객 도면 없이 돈다 · 어떤 데이터에서 도는지 시험 이름이 말한다).
* 판정 모듈이 LLM 을 import 하지 않음을 시험으로 못박는다 (`tests/test_description.py` 와 같은 방식).
* **회귀 기준선 다섯** (`python3 spike/regression_3p.py`) 은 P&ID 엔진을 안 고치므로 움직일 수 없지만,
  `main.py` 를 건드리는 L5 뒤에 한 번 돌린다.  ⚠ 이 컨테이너에는 회귀 PDF 가 없다 — 회사 PC 에서 잰다.

---

## 11. L2 구현 — Logic 신호 연결도 · 따라가기 · 강제 신호 시뮬레이션 (2026-10-11)

사용자 요청: *"선이 from-to 로 제대로 이어지는지 · 버튼을 누르면 라인이 highlight 되며 쭉 이어지게 ·
논리회로를 만나면 다른 입력도 forcing 해서 1 로 살리면 계속 이어지게 · 우선 Logic Diagram 부터 ·
forcing 하면 실제 logic 이 동작하는 것처럼."*  → §10 의 L1b~L3 를 Logic 묶음에 한해 앞당겼다.
Loop · P&ID 대조(L4) · 사람 O/X · VOC · Excel(L5 일부)은 아직이다.

| 모듈 | 하는 일 |
| --- | --- |
| `app/logic/geom.py` | 그림 요소 갈래: 꺾은선 · 칠한 화살촉(삼각) · 원(곡선 · 굵게 칠한 고리) · 사각형(re · qu · 닫힌 4선) · ◆ ■ 표시 · 칠 조각 · 도면 테두리.  표의 세로 괘선 중 가장 넓은 사이 = LOGIC 영역 · 행 간격 P |
| `app/logic/graph.py` | 넷 · 블록 · 단자.  허용치는 전부 P 의 배율.  끝점·T 접합만 잇고 몸통 교차는 잇지 않는다(범례 G003 "BROKEN LINE = NO CONNECTION") · 연결점(점·속 빈 작은 원)은 잇는다 · 끊어 그린 교차는 틈을 건너 같은 선으로 · 파선(고른 토막) · 입력 막대(화살촉 꼭지가 닿는 막대) · ㄷ자+막대 상자 · 흩어진 선분 상자 · 빗금 ■/◆ · 연결 기호(원+꼭지 삼각형) |
| `app/logic/glyphs.py` | 선 글자 사전 — ① 표 NO. 열(k 번째 행 = k) ② 도면 목록 ↔ 각 장 타이틀블록(진짜 글자), 세 칸 글자 수가 다 맞는 행만.  래스터는 가로·세로를 따로 늘린다(칸마다 글자 폭 비가 다르다 — 실측 H 2.28 ↔ 4.9).  맞댐은 numpy 거리 지도 |
| `app/logic/blocks.py` | 블록 뜻 — 범례 어휘(`config/logic_symbols.yaml`, ISA-S5.2)에 **같은 글자 수** 낱말로 맞댄다.  메모리 우선 칸(So/Ro) · 타이머 · PB · STEP 단자 이름 · 연결 기호 묶음 · 램프 |
| `app/logic/analyse.py` | 묶음 전체 → 결과 JSON · 행 칸 글자(FM · DESCRIPTION · KKS · TO) · `t= 3sec` · 시트 간 참조(FM `G031-81` → G031 81행) · 점검(C1 끊긴 끝 · 가리킬 곳 없는 화살촉 · C3 · C7 · L-C2) |
| `app/logic/sim.py` | `simulate(forces, state)` — 0/1/알 수 없음, 범례 정의대로.  틀(frame) = 누른 순간 + 타이머가 끝날 때마다.  넷마다 **깊이**(블록 몇 개를 지났나).  `trace` 는 논리와 무관한 연결 따라가기 |
| `app/logic/api.py` · `store.py` · `run.py` | `/logic` 화면 · `/logic/api/*`.  저장은 `{data}/logic/<job>/` 파일 (DB 표 추가 없음).  분석은 별도 프로세스 |
| `app/static/logic.{html,js,css}` | 도면 PNG 위 SVG.  연결 따라가기(주황 · Shift = 거슬러) · 동작 시뮬레이션(입력 1/0/풀기 · 깊이 순서로 선이 몰이 자리부터 그려진다 · 타이머 경과 막대) |

**실측 (HRSG Logic rev2 · 53장 → Logic 표 50장 · 46초)**: AND 191 · OR 169 · PD 111 · NOT 86 · GT 59 · 메모리 55 ·
STEP 16 · PB 16 · 연결 기호 237 · 판정 못 함 39.  G034 는 블록 19 개 전부 맞고(눈 대조) 행 글자 13행 · FM 참조 9 개가 전부
그 장으로 이어진다.  점검 220건: C7(연결 기호 짝이 장 안에 없음) 88 · C1 끊긴 끝 45 · 판정 못 한 블록 39 ·
게이트 입력 못 찾음 25 · 연결 없는 블록 22 · **FM G019-95 (G035 7행) — 묶음과 도면 목록에 G019 가 없다** 1.
Logic 의 `P0xx-n` 참조는 Loop 묶음이라 점검하지 않고 표시만 한다.

**근사 · 한계 (화면이 말한다)**: STEP 상자 = `C_STEP = STEP_IN` · `STEP_OUT = STEP_IN AND CRIT` · 타이머 시간을 못 읽으면 1초 ·
Typical 큰 블록(G011 등 단자 이름이 여럿인 상자)은 판정 못 함 · 시트 사이 시뮬레이션은 아직 (행 참조를 눌러 그 장으로 이동만) ·
C7 의 상당수는 장 밖으로 나가는 연결 기호(`I` 등)일 수 있다 — 사람 판단 필요.
