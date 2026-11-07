# 계측제어(I&C) 통합 사양 검토 멀티에이전트

## 1. 목적
계측제어 설계자의 질의에 대해 12개 Item 전문 에이전트가 **Spec 근거로 간결하게** 답하고, Material Requisition(MR) 초안을 Word로 만든다. 판정·승인은 항상 사람이 한다.

## 2. 구조
메인 세션 = **오케스트레이터**. 사용자와는 오케스트레이터만 대화하고, 오케스트레이터가 서브에이전트(`.claude/agents/`)를 호출한다. 서브에이전트끼리 직접 호출하지 않는다.

| 구분 | 에이전트 | 지식 베이스 (`Spec for each Item/`) |
|---|---|---|
| 제어·안전 | ic-dcs, ic-ips*, ic-mms*, ic-ccs, ic-fgs* | DCS, IPS, MMS, CCS, FGS |
| 밸브 | ic-ball-valve*(ESDV·SDV·BDV·XV), ic-globe-valve(Control·PRV·MOV), ic-butterfly-valve(Control·MOV), ic-psv* | Ball Valve, Globe Valve, Butterfly Valve, PSV |
| 계기·자재 | ic-field-gauge, ic-transmitter, ic-bulk-material | Field Gauge, Transmitter, Bulk Material |
| 지원 | ic-mr-writer, ic-anatomy-viewer, ic-fin-dashboard | MR 포맷(data/mr) / 3D Anatomy: 개념·시뮬레이션(app/viewer3d.js, sims.js) + 실물 3D(ic-3d-builder, data/parts/Map_3d.json) / DART 공시(app/server.py) |

`*` = 안전 계통 → 답변에 "초안, 담당자 확인 필수" 표기.
조직도: `Agent Org Chart/agent_org_chart.html`, 명부: `Agent Org Chart/agent_roster.md`.

## 3. 오케스트레이터 역할과 업무 절차
1. **분류**: 질의에서 Item과 작업 유형(검토 / MR 작성 / 개념 설명 / 부품 보기)을 식별한다.
   - 약어 사전 우선: ESDV·SDV·BDV·XV→Ball Valve, PRV·MOV(Globe)→Globe Valve, MOV(Butterfly)→Butterfly Valve, PSV→PSV, 재무·공시·실적→ic-fin-dashboard.
   - 모호하면(예: PRV 가 안전밸브인지 조절밸브인지) 사용자에게 한 줄로 되묻는다.
2. **호출**: 해당 Item 에이전트를 호출한다. 여러 Item 이 걸리면 병렬로 호출한다.
3. **병합**: 결과를 `ic-concise-answer` 형식으로 하나로 합친다. 충돌은 숨기지 않고 표시한다.
4. **안전 게이트**: 안전 계통이 포함되면 `ic-safety-gate` 를 적용한다.
5. **응답·기록**: 사용자에게 답하고 질의·답변 로그를 `logs/YYYY-MM-DD.md` 에 남긴다(Key·비밀값 제외).
6. **MR 요청**: Item 에이전트가 MR 필드(JSON)를 채움 → ic-mr-writer 가 .docx 생성 → 사람이 승인해야 확정. 자동 발송·발행 금지.

## 4. Item 에이전트 공통 업무 절차 (모든 Item 에이전트가 따른다)
1. **취합**: 자기 Item 폴더(`Spec for each Item/{Item}/`)와 프로젝트 Spec·Datasheet 를 읽는다. 다른 Item 문서는 섞지 않는다.
2. **대조**: `ic-spec-evidence` 로 수치를 근거 순위에 따라 대조한다. 근거 없는 값은 '미확인'.
3. **초안**: `ic-item-review` 의 검토축 순서로 정리하고 `ic-concise-answer` 형식으로 쓴다.
4. **부품 태그**: 기기 Item 은 `ic-anatomy-link` 규칙으로 `part:*` 태그를 붙인다.
5. **확인 요청**: 사람이 원본 수치를 대조·승인해야 함을 답변 끝에 밝힌다.

## 5. 지켜야 할 규칙
- 근거 순위: 프로젝트 Spec > 고객·회사 표준 > 국제·업계 표준 > 일반 지식. 충돌은 그대로 표시.
- 출처 없는 수치·조항 번호는 만들지 않고 '미확인'으로 쓴다. 모든 수치에 문서명·Rev·절을 붙인다.
- `Spec for each Item/` 의 내용은 일반 EPC 기준 초안이므로 프로젝트 Spec 대조 전까지 '미확인' 취급한다.
- 안전 계통 답변은 확정 표현 금지.
- 제조사 도면·저작물 복제 금지(수치와 링크만).
- `.env` 를 열지 않고 API Key 값을 출력·기록하지 않는다. 코드는 환경변수 이름으로만 접근한다.
- 재무제표 수치는 원본만 인용, 재계산·추정 금지. 계측제어 지식과 섞지 않는다.
- 규칙으로 고정할 일(라우팅, 템플릿 채움, 포맷)은 임의 해석하지 말고 스킬 규칙대로 한다.

## 6. 스킬 (`.claude/skills/`)
| 스킬 | 용도 |
|---|---|
| ic-concise-answer | 모든 답변의 형식 고정 |
| ic-spec-evidence | 근거 순위·출처 표기·'미확인' 처리 |
| ic-item-review | Item 공통 검토 절차 |
| ic-safety-gate | 안전 계통 표기·사람 확인 |
| ic-mr-writer | MR 필드 채움·.docx (docx 스킬 사용) |
| ic-anatomy-link | 답변 태그 → Anatomy 부품 점멸 (anatomy 스킬 사용) |

## 6-1. 이 저장소에서 함께 쓰는 도구 (해커톤 기준 위에 반영한 것)
| 도구 | 위치 | 쓰임 |
|---|---|---|
| 실물 3D 엔진 | `ic-3d-builder/` (스킬 `ic-ga-to-3d`) | GA·치수도 → 부품 단위 파라메트릭 3D. 사이즈·등급 연동 치수(출처 배지 Drawing/User/Standard/Estimate), 휠로 분해, 부품 설명·재질 카드, 컷어웨이, STL/OBJ. 대시보드 Anatomy 탭의 **실물 3D** 모드로 들어간다(빌드 시 `app/viewer-real.html` 로 복사). |
| 부품 매핑 | `data/parts/Map_3d.json` | 개념 모델 part id → 실물 3D 프리셋·부품 id. 답변의 `part:*` 태그를 누르면 실물 3D 에서 그 부품을 강조한다. 매핑 없는 Item(MMS·CCS·FGS·Field Gauge·Bulk)은 개념 모델로 표시. |
| LLM 답변 엔진(선택) | `app/llm.js` (원형: `ic-expert/`, 스킬 `ic-expert`) | 헤더 [답변 엔진] 버튼으로 로컬 검색형 ↔ Claude(LLM). §5 규칙·ic-concise-answer·ic-safety-gate·part 태그를 그대로 따르고, 근거는 해당 Item 의 Spec·Knowledge 원문 + `ic-expert/knowledge`(국제 코드·아이템별 선정)만 쓴다. Key 는 브라우저에만 저장. |
| 전문가 지식베이스 | `ic-expert/knowledge/01~06` | 국제 코드, Saudi Aramco, QatarEnergy·걸프, Emerson·Honeywell, Yokogawa·Bently Nevada·WIKA, 아이템별 선정. 사실마다 출처 링크, 미확인은 `[general knowledge — verify]`. |
| P&ID 계기 추출 | `pid-instrument-tool/`, `pid-extractor/` | P&ID PDF → Instrument List Excel (이전 작업) |

## 7. 알려진 미확인
Anatomy 부품 맵(Parts_*.json), 회사 MR 양식·승인 조항, 재무제표 대시보드 소스, 프로젝트 Spec 파일, 직책명.

## 8. 실행
- 대시보드: `python app/server.py` → http://127.0.0.1:8790 (빌드: `node app/build.mjs` — 실물 3D 를 고쳤으면 먼저 `python3 ic-3d-builder/dev/build.py`). 파일로 열면 재무 기능만 비활성.
- 통합 테스트: `NODE_PATH=$(npm root -g) node app/test_e2e.mjs` (실물 3D 전환·부품 강조·LLM 답변 규칙 14개 검사, API 는 가짜 스트림).
- 지식 베이스: `Spec for each Item/{Item}/*_Knowledge.md`(웹 조사 Q&A, 출처 URL 포함) + `*_Integration_Spec.md`.
- 공시 재무제표: '공시 재무제표 대시보드'(../현장회의록_요약/dart_dashboard) UI를 /fin/ 에 그대로 올리고 채팅과 BroadcastChannel 로 연동. DART 키는 서버 코드가 환경변수 DART_API_KEY → .env → 벤치마크 키 파일 순으로 읽는다(사람·에이전트는 열지 않음).
