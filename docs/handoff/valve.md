# 인수인계 — "VALVE Datasheet 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-11-07 · valve35 — valve29 Phase 1 완료 + 후속 요청들)

- ★★★ **2026-11-02 사용자: "우선 여기 개인 클로드에서 개발을 이어서 진행한다"** — 이 세션(클라우드)이 계속 개발하고 valveNN 꾸러미를 낸다. 회사 PC 는 적용만(회사에서 Valve 를 고치면 다음 꾸러미가 충돌).
  아래 2026-11-01 '회사 PC 개발' 장치(devkit · valve_deploy_to_ops)는 그대로 두되 지금은 쓰지 않는다.
- (옛) 2026-11-01 사용자 결정: Valve 분석 툴은 회사 PC Claude Code 가 개발한다. 클라우드 · 개인 세션은 `app/valve` · `app/static/valve` · `tests/test_valve*` · `docs/valve` 를
  고치지 않고 꾸러미에도 싣지 않는다(`config/release_sources.json` company_owned · `spike/pack_delta.py`). 회사 쪽 운영 반영 = `spike/valve_deploy_to_ops.bat`(시험 → 백업 → Valve 만 복사 → 8000 재시작) · 되돌리기 `valve_rollback_ops.bat`.

- 작업 브랜치: `ccr-efbe7e75-n915ze` (PID hotfix131 · DASHBOARD v16.51 병합 위). **회사 PC 에서 이어 갈 때는 `docs/handoff/VALVE_COMPANY_START.md`** (폴더 · 지시문).
- 무엇: 대시보드 **실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve** = P&ID 서버(8000) `/valve/`. 같은 줄에 Globe Valve · Butterfly Valve · PSV 메뉴(준비 중 화면, `dashboard.html MODULES`).
- ★ 방향(사용자 지시서 "Engineering Intelligence Upgrade"): 엔진이 핵심 · 기존 판정 불변 · OCR/LLM 금지 · 근거 없으면 Review Required/Not Defined · 새 규칙마다 Rule ID ·
  모든 판정에 출처 문서 · 쪽 · 기준값 · 실제값 · 근거. Phase: 1 운영 신뢰성(완료) → 2 PMS Gasket/Bolting · 프로젝트 기준 문서 · 교차 검증 → 3 Cv/ΔP → 4 다른 Vendor 양식 · Tag 절차 · 워크플로.
- valve29 에 들어간 것 (DESIGN §32~§34-5):
  결정 5종 + 사유 분류 · decision_log · Rule Performance · 규칙 버전/출처 · 근거 추적 / 코멘트 고치기(✎ 이동 · 크기) · 나란히 비교(⇆) · 새 창 실시간 연동(BroadcastChannel) /
  Special Req. 탭 + Excel · Dense CO2 요구사항 / Excel 같은 열 필터(xfApply · xfDom) / 입체 화면(body.d3, Settings 끔) · 대시보드 카드 크게 보기 /
  액세서리 지식 acc.* + 규칙 AC-01~05 (AC-05 = SOV 2개 이상인데 1oo2/2oo2 미기재, 실자료 48건) / 첫 화면 '기준 문서' 줄(`docrev.py`: PMS · Process Data · Datasheet Rev · 날짜) /
  속도 · 가볍게(화면 답 `_cached` 재사용 + gzip + ETag, 정적 파일 해시 캐시, Process/PMS 가상 행, 캐시 객체 공유) / 결함: 새 설치 첫 요청 500 · 검색 후 Excel 옛 검색어.
- 검토 캐시 키 = (audit · 상태 · 프로젝트 판 · VERSION · **규칙 코드 지문 `_RULES_FP`**) — 규칙 파일을 고치면 저절로 다시 계산.
- 품질 기준값: `spike/valve_eval.py --check`(AC 규칙 수까지 갱신됨) · 판정 스냅샷 `spike/valve_snapshot_diff.py check out/valve29/snapshot_valve28.json` = 기존 2,887 변경 0 · 추가 48(AC-05).
- 매 회차 끝 점검: `pytest -q`(1,906 통과) · `tests/ -k valve`(108) · `valve_eval --check` · `valve_sim --n 3000` · `valve_mutate` · `valve_rev_sim --n 300` · `valve_snapshot_diff check` ·
  `node spike/valve_ui_audit.cjs`(25/25) · `valve_link_check.cjs` · `valve_filter_check.cjs` · 속도 `valve_speed.cjs`(동작 60개, 최장 멈춤 ≤ 0.37 s).
- ✅ **회사 적용 확인 (2026-11-02 사용자)**: valve29 · 대시보드 VALVE2 메뉴 zip · devkit 모두 적용. 이후 Valve 는 회사 PC 가 원본.
- **valve30 (2026-11-02, 회사 PC 사진 피드백)**: 입체 화면에서 PDF 도구줄 · Mark-up 줄 버튼이 흰 바탕 흰 글씨 → 어두운 버튼 유지 · Ctrl+휠 = PDF 확대/축소(마우스 자리 중심, `Viewer.zoomAt`) ·
  PMS/Process 아래 미리보기 높이 · 좌우 폭 끌어서 조절(`splitPanes`, LS 기억) · 미리보기 화질(그림 = 화면 픽셀 × 1.25, 최대 4배) · PMS Bore 지적 문구에 PMS 품목 · 크기 범위(28건 문구만).
  판정 스냅샷은 `out/valve29/snapshot_valve30.json`(2,935) 기준.
- **valve31**: 코멘트 한글 · 영어(`i18n.py` 규칙별 고정 틀 · `description_ko`) · 화면 표시 언어 · Excel/PDF 출력 언어(lang=en|ko|both). **새 규칙 문장을 만들면 `i18n.RULES` 에 한국어 틀도 추가**하고 `tests/test_valve_i18n.py` SAMPLES 에 한 줄.
- **valve32**: 올린 문서 지우기(🗑 · 확인 창 · `valve/trash/<p>/` JSON) · 휴지통 되돌리기(같은 id) — DESIGN §37.
- **valve33**: 첫 화면 Valve Summary 표(`/valve-summary` · `drawVsum` · `vsTags`) — DESIGN §38.
- **valve34**: FileDataError 반복(깨진 저장본 재사용) 고침 · 저장본 해시 검증 · open_pdf 재시도/이유 · 작업 상태 창 닫기 — DESIGN §39.
- **valve35**: 코멘트 정리 — 블럭(한 쪽에 붙은 Data Missing 3개+ = 한 코멘트) · Typical(같은 코멘트 2 Tag+ = 한 줄) · ▸ 상세 · 묶음 일괄 결정 ·
  Excel 'Comments (Typical)' 시트 · PDF 블럭 박스(`digest.py`, `/issues/digest`, `group=1`) — DESIGN §40. 판정 불변(스냅샷 0). 실자료 2,935 → 276.
- **valve36**: 밸브 모형 = 세션 7 Anatomy 엔진(`app/static/valve/anatomy.js`, `spike/mk_anatomy.py` 로 묶음 · 오프라인) — 칸 ↔ 부위 양방향 · DESIGN §41.
- **valve37** (2026-11-11 회사 PC 사진 'HTTP 500', 새 창 ds=74): 검토 계산 예외 → 그 Tag 만 지적 없이 열림 + review_error · 모든 /valve 오류 JSON + `valve\logs\errors_*.log` — DESIGN §42.
  **원인은 아직 모름** — 사용자에게 로그 파일(`C:\Claude\PID\app\_data\valve\logs\errors_*.log` 또는 화면에 나온 위치) 내용을 받아 고칠 것.
- ★ 2026-11-07 오케스트레이터(세션 메시지): "Valve 도 통합 PID_dev+ops_hotfixNNN 에 싣고 valveNN 별도 꾸러미 폐지" — **사용자 확인 전**이라 규칙은 아직 그대로.
- 꾸러미: **valve37** = `out/PID_dev+ops_valve37_2026-11-11.zip` (누적 · valve36 Anatomy 포함, 회사 HTTP 500 대응). 그 전 valve35. 그 전 **valve30** = `out/PID_dev+ops_valve30_2026-11-02.zip`. 그 전 **valve29** = `out/PID_dev+ops_valve29_2026-11-01.zip`(P&ID 서버, 누적 — 이것 하나) · 대시보드 = `dashboard_patches/UPDATE_from_v16.51_VALVE2_menu.zip`(--any) ·
  회사 개발용 = `out/VALVE_devkit_valve29_2026-11-01.zip`(문서 · 점검 도구).
- 남은 일: PERFORMANCE_REPORT.md(측정은 끝 — DESIGN §34-2 · §34-5 · other_log 수치) · Globe/Butterfly/PSV 검토(양식 · 기준 필요) · Phase 2(회사 Valve Spec · Gasket/Bolting PMS · Process DS 원본 필요) ·
  실사용 결정 쌓기(Rule Performance 정밀도) · 다른 Vendor 양식 시험.

## 파일

| 파일 | 하는 일 |
|---|---|
| `app/valve/extract.py` | PDF → 칸 (On/Off Form 80 · MOV Form 102 · 공정 조건표 · Notes · General Notes) |
| `app/valve/schema.py` | 라벨 사전 · Tag 정규화 · 밸브 종류 · 공정이 아닌 칸 목록 |
| `app/valve/store.py` | SQLite `{data}/valve/valve.db` · 원본 `{data}/valve/files/` · 감사 · Rev 순서 · 열 추가 이전(_migrate) |
| `app/valve/tbe.py` | Valve List(TBE Appendix) 채우기 · .xls → .xlsx (회사 PC 의 Excel) · 칸 링크 |
| `app/valve/material.py` | 재질 비교 (표기 아닌 규격 · 등급 · 계열) |
| `app/valve/pms.py` | PMS Class 시트 읽기(지역 QN/QS) · 데이터시트 비교 |
| `app/valve/issues.py` | 오류 · 누락 · PMS · Revision · 검토자 지적 (번호 · 색) |
| `app/valve/exports.py` | Issue List Excel · 인쇄용 Mark-up PDF (검토자 Mark-up 은 같은 종류의 PDF 주석으로) |
| `app/valve/api.py` | `/valve/` 화면 · `/api/valve/*` (업로드 작업 · 칸 수정 · 비교 · 쪽 그림 · 검색 · 주석 · 표시 PDF · 내보내기) |
| `app/static/valve/` | 화면 (index.html · valve.css · valve.js — 빌드 없음) |
| `app/main.py` | 두 줄: `from app.valve import api as _valve_api` · `app.include_router(...)` |
| `dashboard/dashboard.html` | `PID_ROUTES.valve` · `ROUTES` · `menuOf` · `NAV_LS` · `renderMenu` 의 `runTree` (APP_VERSION 2026-10-31.2) |

## 다른 세션과의 약속 ★

이 모듈은 **두 군데의 공용 파일**을 건드린다. 그쪽 세션이 이 브랜치를 병합하지 않고 다음 꾸러미를 내면 되돌아간다.

1. **PID 세션** (`claude/gracious-ride-26nqrf`): `app/main.py` 두 줄 + `app/valve/` · `app/static/valve/` · `tests/test_valve.py`.
   → `config/release_sources.json` 에 `VALVE` 를 넣어 두었다. PID 세션이 이 브랜치를 병합하면 그 뒤 `pack_delta.py` 가 덜 합쳐진 VALVE 를 잡아 준다.
2. **DASHBOARD 세션** (`ccr-248a5c4d-3dji7g`): `dashboard/dashboard.html` 의 메뉴 (APP_VERSION 2026-10-31.2) + `DASHBOARD_ARCHITECTURE.md` 변경 이력.
   → 다음 대시보드 zip 전에 이 브랜치의 `dashboard/dashboard.html` 변경을 병합해야 한다 (안 하면 메뉴가 사라진다 — make_patch 가 `.new` 로 두어 덮지는 않음).

사용자에게 두 세션에 전할 말: "VALVE 세션 브랜치 `ccr-efbe7e75-n915ze` 를 병합한 뒤 꾸러미를 만들어 줘."

## 꾸러미

- P&ID 서버용 (밸브 모듈만):
  `python3 spike/pack_delta.py --name valveNN --base 9429f4f --only app/valve/,app/static/valve/,app/main.py,tests/test_valve.py,tests/test_valve_api_cache.py,tests/test_valve_extract_sim.py,tests/test_valve_markup23.py,tests/test_valve_revision.py,tests/test_valve_verification.py,tests/test_valve_feedback.py --readme out/valveNN/readme_head.txt --ops`
  → `out/PID_dev+ops_valveNN_<날짜>.zip`. `--only` 는 딱지(`app/_update.json`)와 기준 파일(`out/PID_dev_delta_base.txt`)을 건드리지 않는다 (PID 세션 번호와 안 섞이게).
  기준 9429f4f = hotfix131 전달본. 회사가 다른 판이면 `--base` 를 그 판으로.
- 대시보드용: `python3 dashboard_tools/make_patch.py --out dashboard_patches --mark` (기준 = `delivered.txt` 맨 아래). `--out` 은 폴더. 첫 전달: `dashboard_patches/UPDATE_from_v16.51_VALVE_menu.zip` (기준 v16.51).
- 적용 순서(회사): ① PID 꾸러미 `apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` (8000 서버 재시작) ② 대시보드 zip `APPLY.bat` (서버 재시작 필요 없음, 화면 새 버전 배너) ③ 대시보드 → 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve.

## 다음에 할 일

1. 회사 적용 확인: .xls 자동 변환(Excel COM)이 되는지, 456쪽 처리 시간, 화면 글꼴, Mark-up 도구(Edge)와 내보낸 PDF 를 Acrobat 에서 열어 보기.
2. **Phase 2** (지시서 §2 · §4 · §5): PMS Gasket · Bolting 대조 · 프로젝트 기준 문서 등록 · Rule Source 연결 · 문서 간 교차 검증 · Document Hierarchy. 필요한 자료: API5L-X65 PMS · 정식 Process DS · Tag Numbering Procedure · 회사 Valve Spec.
4. 재질 · 설계 검토: 회사 재질 · 밸브 엔지니어에게 MR(§14.3) · VR(§15) 규칙과 `BALL_VALVE_KNOWLEDGE.md` 를 보여 회사 사양 값(Floating 한계 · 시트 한계 · PST 정책)으로 맞추고, 기준(시트 한계 · B8M CL.2 해석 · 316 60 °C 문구)을 확인받기. Process Data 에 최저 설계온도가 생기면 저온(MR-04)을 온도로도.
3. 받은 PDF 에 이미 있는 주석(설계사 Mark-up) 읽어 오기 · 1366×768 노트북에서 작업대 사용감 확인.
