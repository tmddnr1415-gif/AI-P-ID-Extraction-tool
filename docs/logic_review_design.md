# LOGIC 검토 메뉴 — 설계 (L1회차 초안 · 2026-10-11)

> 상태: **초안 · 사용자 승인 전.**  코드는 아직 한 줄도 없다.
> 지시문: `docs/logic_review_kickoff.md`.  원칙: `CLAUDE.md` §2 · §9 · §10, `docs/state_and_roadmap.md` §3 · §4.
>
> **★ 이 회차에는 샘플 PDF 가 없었다.**  첫 메시지에 첨부가 오지 않았고 컨테이너의 `data/` 도
> 비어 있다(`data/` 는 gitignore 라 저장소로도 오지 않는다).  그래서 지시 §2-1 *샘플 실태 조사*는
> **하지 못했다.**  아래 판정 규칙의 "모양" 은 전부 **가설**이고, §1 의 측정이 각각을 확정하거나
> 지운다.  측정 없이 규칙을 코드로 옮기지 않는다 (`state_and_roadmap` §4 절차 1 · 3 · 4).

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

## 1. 샘플 실태 조사 — 샘플이 오면 **가장 먼저** 잴 것

`spike/logic_survey.py`(새 스크립트 · 읽기만)로 PDF 마다 아래 표를 만들고, 장마다 렌더(2배)를 찍어
**눈으로** 본다.  결과는 `out/logic_l1/` 에 (도면 조각은 gitignore 대상 — 고객 도면).

| # | 무엇을 | 어떻게 재나 | 왜 — 무엇이 갈리나 |
| --- | --- | --- | --- |
| S1 | **글자층이 있나** | 장마다 `get_text` 낱말 수 · SHX 주석 수(`pidcache._shx_entries`) · 이미지 수와 면적 비 | 셋 다 0 에 가깝고 이미지가 장을 덮으면 **스캔 도면 → 못 읽는 도면**(§6 S-1 멈춤) |
| S2 | **선으로 그린 글자인가** | 낱말 0 · 짧은 선분 수만 많음 · SHX 주석 없음 | SHX 주석 없이 획만 있으면 글리프 사전이 필요 — P&ID UAD p11~17 과 같은 벽(§8 #8) |
| S3 | **블록이 어떻게 그려지나** | `drawings()` 의 `re`/`qu`/`l` 닫힌 사각 · 곡선(게이트 D 모양 · OR 활 모양) 개수와 크기 분포 | `segments()` 는 `l` 만 준다 — 블록이 `re` 면 **사각형 경로를 따로 읽어야** 한다 |
| S4 | **블록 안 글자** | 닫힌 도형 안에 든 낱말 — `AND`/`OR`/`&`/`≥1`/`TON`/`TD`/`SR`/`NOT` 등 무엇이 쓰이나 | 블록 종류를 **글자로** 읽을지 **모양으로** 읽을지 — 범례 시트가 정한다(S7) |
| S5 | **신호선의 꼴** | 선분 각도 분포(수평·수직만인가) · 실선/파선 · 굵기 분포 · 끝점이 도형 테두리에서 얼마나 떨어지나(**끊김 간격 분포**) | C5(끊긴 선) 문턱은 **이 분포의 빈 띠**에서만 세운다.  빈 띠가 없으면 C5 는 "검토" 등급으로만 낸다 |
| S6 | **시트 간 참조의 꼴** | 시트 가장자리 근처의 오각형/화살 도형 + 그 안·옆 글자 — `TO`/`FROM`/`SH.`/`SHEET`/도면번호/좌표(`3-B`)/신호 번호가 어떤 순서로 쓰이나 | C1~C4 의 열쇠가 무엇인지 (시트 번호? 도면번호? 신호 이름?) |
| S7 | **범례·심볼 시트가 있나** | 첫 몇 장의 머리말 · 블록 모양이 표로 늘어선 장 | 있으면 블록 사전을 **거기서 유도**(P&ID 범례와 같은 방식), 없으면 사람에게 묻는 자리 |
| S8 | **타이틀블록** | `derive_layout.derive(pages)` 가 도면번호 칸·REV 를 잡는가 | 시트 간 참조가 가리키는 "그 장" 을 찾는 열쇠 |
| S9 | **Loop 도면의 계기 표기** | 태그 꼴(`FT-1001` · `10LAB10CF001` …) · 한 장에 루프 하나인가 여럿인가 · 단자대·케이블 번호 | X1~X3 대조의 열쇠와 범위 |
| S10 | **페이지 회전 · 크기** | `PageCache.source_rotation` · 장 크기 분포 | 회전은 pidcache 가 처리 — 확인만 |

**조사가 끝나면 이 문서 §4 의 각 규칙 옆에 "확정 / 수정 / 삭제" 를 적고, 그다음에 구현한다.**

---

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
| S-2 글자가 획으로만 있다 (SHX 주석 없음) | "글자가 선으로 그려져 있어 읽을 수 없습니다" | 멈춘다 |
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
| **Q1** | **샘플 PDF** — Logic · Loop · System 각 1~2개를 `data/logic/` 에 (또는 다음 메시지에 첨부) | 이번 회차에 오지 않았다.  §1 측정 전에는 규칙을 코드로 옮기지 않는다 | — (구현 시작 조건) |
| Q2 | 도면의 출처 — DCS 업체 CAD 출력인가, 설계사 AutoCAD 인가, 스캔인가 | 글자층 · 블록 그리는 방식이 출처마다 다르다 | S1~S4 측정으로 판단 |
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
| **L1** | `spike/logic_survey.py` — §1 S1~S10 측정 · 렌더 | 이 문서 §4 규칙마다 확정/수정/삭제 표기 · 사용자 확인 |
| L2 | `app/logic/read.py` — 블록 · 단자 · 신호선 · 참조 · 태그 읽기 | 샘플마다 도면 위 표시를 렌더로 눈 확인 · 놓친 것/잘못 잡은 것 수 보고 |
| L3 | `app/logic/rules.py` — C1~C8 | 규칙마다 합성 PDF 시험(정상 1 · 오류 1) + 샘플 실측 |
| L4 | `app/logic/compare.py` — X1~X4 | 시험용 P&ID job 을 임시 DB 에 만들어 대조 시험 |
| L5 | `app/logic/api.py` · `store.py` · `logic.js` — 화면 · O/X · 마크업 · VOC · Excel | API 시험 + 화면 캡처 |

* 시험은 `tests/test_logic_*.py` — `conftest.py` 격리 그대로, 합성 PDF 는 시험 안에서 pymupdf 로 그린다
  (고객 도면 없이 돈다 · 어떤 데이터에서 도는지 시험 이름이 말한다).
* 판정 모듈이 LLM 을 import 하지 않음을 시험으로 못박는다 (`tests/test_description.py` 와 같은 방식).
* **회귀 기준선 다섯** (`python3 spike/regression_3p.py`) 은 P&ID 엔진을 안 고치므로 움직일 수 없지만,
  `main.py` 를 건드리는 L5 뒤에 한 번 돌린다.  ⚠ 이 컨테이너에는 회귀 PDF 가 없다 — 회사 PC 에서 잰다.
