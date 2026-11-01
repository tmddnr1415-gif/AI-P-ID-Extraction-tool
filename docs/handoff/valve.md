# 인수인계 — "VALVE Datasheet 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-11-01 · valve29 = Phase 1 완료)

- 작업 브랜치: `ccr-efbe7e75-n915ze` (PID `claude/gracious-ride-26nqrf` hotfix131 · DASHBOARD `ccr-248a5c4d-3dji7g` v16.51 병합 위).
- 무엇: 대시보드 **실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve** = P&ID 서버(8000) `/valve/`. 설계 `docs/valve/DESIGN.md`(§1 표 · §33 검증 엔진 · §34 Phase 1) · 개발 `DEVELOPER_GUIDE.md` · 사용 `USER_GUIDE.md` · 현황 `STATUS_REPORT.md`.
- ★ **방향(사용자 지시서 "Engineering Intelligence Upgrade")**: 엔진이 핵심, UI 는 신뢰 · 검증 수단. 기존 판정을 바꾸지 않는다 · OCR/LLM 금지 · 근거 없으면 Review/Not Defined ·
  새 규칙마다 Rule ID · 모든 판정에 출처 문서 · 쪽 · 기준값 · 실제값 · 근거. **Phase 순서: 1 운영 신뢰성(완료) → 2 PMS Gasket/Bolting · 프로젝트 기준 문서 · 문서 간 교차 검증 → 3 Cv/차압/사이징 → 4 다중 Vendor 양식 · Tag 절차 · Workflow.**
  Phase 마다: 계획 문서 → 구현 → 회귀 → 보고서 다섯(`docs/valve/valve29/` 양식) → 꾸러미.
- **valve29 (Phase 1, DESIGN §34)**: 결정 5종 + 사유 분류(`issue_state` 옆 열 · `decision_log`) · Rule Performance 화면 · 규칙 버전/출처(`checks.RULE_VERSION`/`RULE_SOURCE`) · 변경 절차(`rule_change`) ·
  근거 추적(parser_version · op/tol/result · 칸 출처 · PDF 빈 곳 → 칸) · 성능(Excel 2개 · Mark-up PDF 선형화 · 목록 6,000행 상한 제거 · compact API). **판정 변경 0**(`valve_snapshot_diff.py`).
  새 규칙을 만들면: `checks.REGISTRY` 한 줄 + `RULE_VERSION`/`RULE_SOURCE` + `add(..., check=id, basis=, evidence=)` + `RULE_CHANGELOG.md`. 규칙을 바꾸면 버전을 올리고 도구의 변경 기록과 맞춘다.
- 그 전(요약): 추출 · Valve List(valve01~09) · PMS/재질/전문가/Tag 규칙(valve10~15) · 출력 시트들(valve16~19) · 상용화 · 시뮬레이션(valve20~22) · Mark-up(valve23~25) ·
  코멘트 말투(26) · Rev B/C/D 이어받기 `revisions.py`(27) · 근거 · 48 항목 검증 보고 `checks.py`(28). 자세한 것은 DESIGN §14~§33.
- 품질 기준값: `spike/valve_eval.py --check`(지문 541753c612ed · 17,471칸) — `--pd` 를 같이. 판정 스냅샷: `spike/valve_snapshot_diff.py save|check`(실자료 사본 서버 대상, 결과 파일은 out/ — 고객 값).
- **매 회차 끝 점검**: 전체 `pytest -q` · `valve_eval.py --check` · `valve_diff_sim.py`(불일치 0) · `valve_sim.py --n 3000` · `valve_mutate.py` · `valve_sim_pdf.py --n 190` · `valve_rev_sim.py --n 300` ·
  `valve_snapshot_diff.py check` · `node spike/valve_ui_audit.cjs`(데이터 **사본** 서버, 25/25) · 성능은 `spike/valve_perf.py --data <사본> --label N`(164 · 500 · 990 사본: `/tmp/vt_shot` · `/tmp/vt_500` · `/tmp/vt_big` — 세션마다 다시 만들어야 함).
- 실자료(고객 파일 · 저장소에 없음): Datasheet.pdf 456쪽 → 164 데이터시트 · TBE 164/164. EGG 는 `spike/valve_unegg.py`, .xls 는 `spike/valve_xls2xlsx.py`.
- 시험: `pytest -q tests/ -k valve` (99개). 전체 pytest 통과.
- 마지막 꾸러미: **valve29** (P&ID 서버용만). valve01~29 모두 회사 적용 확인 전 — 누적이라 valve29 하나만 적용하면 된다.

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
