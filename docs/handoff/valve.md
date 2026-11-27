# 인수인계 — "VALVE Datasheet 검토" 세션 (상한 15KB · 목표 12KB 아래 · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-11-27 · valve48)

- 브랜치 `ccr-efbe7e75-n915ze`. 무엇: P&ID 서버(8000) `/valve/` — 대시보드 **Datasheet** 메뉴의 Valve(Ball · Globe · Butterfly · PSV) ·
  Instrument 14종 · 현황판 · Instrument/IO List · 공통 자료.
- **꾸러미는 오케스트레이터가 만든다** (`session_01Muj82FygSCFAVRooofwhVK`, 통합 hotfixNNN). 이 세션은 개발 · 시험 · 커밋 · 푸시 →
  send_message 로 "커밋 · 바뀐 파일 · 시험 결과 · 회사에 알릴 한 줄". zip 을 직접 만들지 않는다. 회사 최신 = hotfix145 (valve41 · 오케스트레이터 알림) — valve42~48 은 아직 꾸러미 전.
- 대시보드 세션(`session_016Ntz71xxniTkCj7pC8ZpXL`)은 `/api/valve/*` 를 읽는다 — **필드 이름 · Area 값이 바뀌면 알린다**.
- 방향(사용자 지시서): 엔진이 핵심 · 기존 판정 불변 · OCR/LLM 금지 · 문서에 없는 값은 만들지 않음 · 새 규칙마다 Rule ID · 모든 판정에 출처.
- **자료 금지**: 발주처 원본(Datasheet · PMS · PDS · 빈 양식 · List · 그것으로 만든 시험 PDF · 그 화면 캡처)은 저장소에 올리지 않는다.
  시험은 가짜 값으로 그린 PDF. 원본 위치(새 세션이면 다시 받아야 함): `/tmp/forms/` · `/tmp/vt_shot`(실 Ball 164 Tag) · 사용자 업로드 폴더.

### 매 회차 끝 점검 (모두 통과해야 푸시)

- `timeout 1500 python3 -m pytest -q -x` (2026-11-26: 2,111 통과)
- Ball 판정 스냅숏: 8000 = `/tmp/vt_shot` 서버 → `python3 spike/valve_snapshot_diff.py check out/valve29/snapshot_valve45.json` = **3,091 · 변화 0**
  (valve43: PDS 표 읽기 개선으로 30 → 43 에서 +156 · 없어진 것 0 · Data Missing 781건에 PDS 값 추가 — `other_log.md` 2026-11-26)
- 화면: 8002 = `/tmp/vt_ui` → `node spike/valve_ui_audit.cjs http://127.0.0.1:8002` = 25/25
- `tests/test_context_budget.py` (이 파일 ≤ 15,000 B)
- 서버: `(PID_DATA_DIR=<폴더> nohup python3 -m uvicorn app.main:app --port N > /tmp/sN.log 2>&1 &)` — 턴 사이에 죽으니 다시 켠다.

### Valve (Ball · Globe · Butterfly · PSV)

- 읽기 `extract.py`(Form 80 · 102 · 공정표 · Notes) + `forms_ext.py`(Form 101 CV · 701 PSV · 표제 아래 Code 80) +
  **`form_isa.py`(valve41: ISA-20 'INSTRUMENT SPECIFICATION' — 괘선 칸 읽기 · South CV/Regulator 실물 2권 = 19 Tag)**. `PARSER_VERSION extract-v41`.
- 프로젝트 = 종류별: '<이름>' = Ball · '<이름> · Globe Valve | Butterfly Valve | PSV' (`schema.project_kind`, `?kind=`).
- 검토 `issues.py` · `checks.py` · `expert.py` · `matreview.py` · `pms.py` · `process.py` — 캐시 키에 규칙 코드 지문(`_RULES_FP`)이 있어 규칙을 고치면 저절로 다시 계산.
- 결정 5종 · decision_log · Rule Performance · 코멘트 한/영(`i18n.py` — **새 규칙 문장은 `i18n.RULES` + `tests/test_valve_i18n.py` SAMPLES 에 한 줄**) ·
  코멘트 묶음(`digest.py`) · Mark-up PDF · Issue/Valve List Excel(`exports.py` · `tbe.py`) · 밸브 모형(`anatomy.js`, `spike/mk_anatomy.py`).
- 안정성(11-13): 손상 보관본은 MuPDF 에 넘기지 않음(`store.stored_good`) · `extract.PDF_LOCK` · warm-up 한 프로젝트씩 · `VALVE_WARMUP=0` ·
  `logs/crash_*.log` · `logs/warmup.log` · 손상 PDF 는 예전 쪽 그림으로 · 읽은 Datasheet 는 `datasheets/<프로젝트>/<kind>/<Tag>__<Rev>.json`(`dsjson.py`).
- **모르는 양식 안전망(valve41)**: `extract.unread_pages`(번호 줄 양식인데 읽힌 줄 40% 미만 · Tag 없는 DS) · `index_tags/index_check`(도서 INDEX 와 읽은 Tag 대조) →
  작업 창 경고(`_job_warn`) · `document.info.unread_pages/.index` · Document Management 빨간 표시. 시작 때 Tag 없는 DS 를 남긴 문서는 자동 다시 읽기(`_auto_reread`).

### Instrument (14종 · `?kind=ft|pt|lt|gwr|tt|tg|pg|dpg|mlg|ro|analyzer|cv|onoff` · `all` 현황판 · `instindex|iolist`)

- 지시 원문: `git show origin/claude/trusting-cray-v68axq:INSTRUMENT_REVIEW_PLAN.md`. 결정: List 는 PDF · 기준 Datasheet → List · 공정 기준 = PDS.
- 카드 `app/valve/forms/*.json` · 읽기 `instrument.py` · 검토 `instreview.py`(IN-REQ/PDS/PMS/LL/ITM/OPN/UNIT) + `instcalc.py`(IN-CV IEC 60534 · IN-PSV API 526) ·
  Line List `linelist.py` · List `instlists.py`(LIST-00/01/02) · API `inst_api.py` · 화면 `app/static/valve/instrument.js`(valve.js 는 `window.VALVE` 다리).
- 지적별 결정(`inst_decision`) · Review Code(`inst.codes`) · CRS 내보내기/회신(`inst_reply`) · `/inst/progress` · Mark-up PDF(`instmarkup.py`, 영어 설명선) · 필수 칸은 사용자 확정(`inst.required`).
- 시험: `spike/valve_inst_scenario.py <dir> [--forms /tmp/forms] [--keep]` — 14종 × (정상 · 오류 심은 Tag) = **심은 오류 74/74 · 오탐 0 · List 29/29**.
- **★ 실물 검증 0건**: 빈 양식과 시험값뿐. 카드는 모두 'Form No' 양식 — 실제 계기 도서가 ISA 'INSTRUMENT SPECIFICATION' 계열이면 못 읽는다(이제 경고는 뜸).
  실물을 받으면: 읽히는지 → 안 읽히면 `form_isa.py` 방식으로 양식 추가.

- **PDS Rev. 비교 (valve43)**: 같은 문서 번호의 수정 PDS 를 공통 자료에 올리면 `pdsrev.compare`(이전 Rev. ↔ 최신, Tag · 칸별 High/Med/Min ·
  Changed/No Change/New/Delete) → 작업 창 · Document Management 에 요약 + 'PDS Rev. 비교 Excel'
  (`GET /projects/{pid}/pds_revcompare.xlsx`, 사용자 예시 양식: Summary · 문서별 시트 3행 · High 변경 목록 · Sizing 영향). 칸별 중요도는 예시 Excel 과 같음.
  ★ valve44 사용자: **Tag 변경 추정 안 함** — 같은 Tag 번호끼리만 비교, 이전에만 있으면 Delete · 최신에만 있으면 New.
  ★ valve45: 사용자 v2 양식(No·Status·Tag·(예비)·Rev.·Row · Status/Tag/종합 중요도는 1행에만 · A/AL/AM 3행 병합 · 집계는 Row='이전')
  · **한글/영어** `?lang=ko|en` (`pdsrev.T` 에 모든 문구 · 화면 버튼 두 개). v2 예시와 194 Tag 블록 모든 칸 · Summary · Sizing 숫자 같음.
- **PDS 분석 메뉴 (valve46)**: `/valve/?kind=pds` (`app/static/valve/pds.js`, 메뉴 PDS 현황 · PDS Tag 목록 · Rev. 비교 · PDS 올리기) ·
  API `GET /projects/{pid}/pds/summary|tags|compare?doc_no=&old=&new=` · Excel 에 `doc_no/old/new` 선택. 대시보드 실행 프로젝트 › CO2 PJT › **PDS 분석**
  (route `pdsv`, 권한 runpjt). 공통 자료 화면에 'PDS 분석 열기 →'.
  valve47: Rev. 비교 · Tag 목록 = 엑셀 모양(열 문자 · 행 번호 · 격자 · 머리/Tag 고정 · Tag 당 3행) · **바뀐 셀 노랑 음영 · 바뀐 값 붉은 글씨** · '바뀐 열만'.
  valve48: 메뉴 **변경 Summary**(`pds/change_summary`, `pdsrev.change_summary` · `SIZING`) = Excel Summary · Sizing 시트 숫자(v2 예시와 모두 같음) + Size 변경 · High 목록, 숫자 누르면 Rev. 비교에서 그 Tag 만. PDS 는 여기서 올려도 공통 자료와 같은 곳(기준 프로젝트)에 보관. 검토는 이제 **문서 번호마다 최신 Rev.** 을 합쳐 씀
  (`api._process_for` — 98 · 999 · 315 동시). PDS 표 읽기: 칸마다 끊긴 세로 괘선 이어 붙임 · 가로 괘선으로 줄 나눔(`process._rebox`, `READER_V=2` → 예전 읽음은 자동 다시 읽기).
- **Project Valve Specification (valve42)**: 공통 자료 종류 'vspec' → `vspec.read_spec`(조항) · `vspec.findings` SP-01~15(조항 문구로 찾고 값은 조항에서) →
  지적 'Spec Compliance'(근거 §조항 · 쪽). On/Off · MOV · CV Spec 실물로 확인(Ball 추가 5 · 기존 변화 0). 새 검사는 `CHECKS` + `TITLES` + i18n 틀.

### 공통 자료 · Area

- **공통 자료 `?kind=refdocs`**: PDS · PMS · Line List · Index/IO List 는 여기서만 올림 → 기준 프로젝트(`api.ref_pid`)에 1벌, family 전체가 씀. 페이지별 올리기 칸 = `window.DOC_KINDS`.
- **Area 순서**(`arearule.resolve`): 올린 도서의 Area(`document.area`, Document Management 에서 고름) → DTS No.(규칙 표 'DTS 98 | QN | | North') → 표제 → 규칙 표 줄.
  학습 추정은 Site 를 정하지 않는다. 라벨 `QN Brownfield N1` · `QN Greenfield` · `QS` · `W15` (QS · W15 는 Brownfield 없음).
  기본 표 `app/valve/arearule_default.txt` · 고친 표 = family 설정 `inst.arearule.table`(공통 자료 / By Area 에서 편집).

## 다음에 할 일 (2026-11-19 오케스트레이터 전달 — 사용자 "세션 2~7 검토해 개선 보완" · 순서대로)

1. **List 대조 보강** (`INSTRUMENT_REVIEW_PLAN` §4 · `instlists.py` compare): 비슷한 Tag 제안(valve39 '비슷한 번호' 재사용) ·
   단위 맞춰 비교(못 맞추면 '단위 확인' — 지금은 단위가 다르면 바로 '값 다름') · Signal → IO Type(AI/AO/DI/DO) 비교 · 'IO 대상 아님' 확인.
   각각 `valve_inst_scenario` 에 오류를 심어 다 잡히는지.
2. **5단계 규칙**: `instreview.py` 머리 설명은 압력 · 레벨 · 유량인데 코드는 pt/pg/dpg 만 → IN-ITM-03(TT/TG Range ⊇ 운전온도) ·
   IN-ITM-04(FT Range ⊇ 최대 유량). 같은 단위일 때만 · 사람 확인 표시 · 설명 문구 · i18n 같이.
3. `app/static/valve/anatomy.js` 가 S7 af748c7 기준 — S7 865f9297 의 분해 맞춤 · 휠 수정이 빠짐 → `spike/mk_anatomy.py` 로 다시 만들기.
4. (여유) Valve 화면 Globe/Butterfly/PSV 에서도 `instcalc` 쓰기 + `forms_ext` 리더와 카드 101/701 을 같은 시험 PDF 로 견주는 시험. Ball 스냅숏 변화 0.
5. 사용자에게 받을 것: 채워진 Instrument Datasheet 종류별 1권 · 채워진 Instrument Index/IO List · Butterfly/PSV 의 South 도서 ·
   회사 사진의 'South' PCV 4개가 든 도서 · 필수 칸 확정 · CV/On-Off/PSV 를 Valve · Instrument 어느 쪽에서 볼지.
6. 오래된 숙제: valve37 'HTTP 500' 원인(회사 `valve\logs\errors_*.log`) · Phase 2(PMS Gasket/Bolting · 프로젝트 기준 문서 · 교차 검증 — 회사 Valve Spec 필요) ·
   재질 규칙(MR/VR)을 회사 엔지니어에게 확인받기 · 받은 PDF 의 기존 주석 읽기.

## 다른 세션과의 약속

- 공용 파일 두 곳을 건드린다: `app/main.py` 두 줄(라우터 등록) · `dashboard/dashboard.html` 메뉴. 꾸러미 전에 이 브랜치가 병합돼야 한다
  (`config/release_sources.json` 의 `VALVE` — `spike/pack_delta.py` 가 덜 합쳐지면 멈춘다).
- P&ID hotfix 꾸러미는 Valve 경로를 싣지 않는다(`company_owned`) — Valve 는 통합 꾸러미에서 오케스트레이터가 싣는다.

## 어디에 더 있나

- 회차 기록: `docs/history/other_log.md` (끝에 5~15줄씩) · 설계: `docs/valve/DESIGN.md`(§32~§44) · 사용법 `docs/valve/USER_GUIDE.md` · 규칙 변경 `docs/valve/valve29/RULE_CHANGELOG.md`.
- 회사 PC 에서 이어 갈 때: `docs/handoff/VALVE_COMPANY_START.md` (지금은 쓰지 않음 — 2026-11-02 사용자: 개발은 이 클라우드 세션에서).
