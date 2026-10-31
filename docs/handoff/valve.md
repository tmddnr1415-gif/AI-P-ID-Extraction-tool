# 인수인계 — "VALVE Datasheet 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-10-31 · valve20)

- 작업 브랜치: `ccr-efbe7e75-n915ze`. 이 브랜치는 PID(`claude/gracious-ride-26nqrf`, hotfix131) 와 DASHBOARD(`ccr-248a5c4d-3dji7g`, v16.51) 를 병합한 위에 있다.
- 무엇: 대시보드 **실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve** = P&ID 서버(8000) `/valve/` — Valve Datasheet 검토 도구.
  설계 · 분석 · 남은 일: `docs/valve/DESIGN.md` (먼저 §1 표, §8, §10). **작동 원리 · API · 화면 · 확장 · 배포: `docs/valve/DEVELOPER_GUIDE.md`**.
- Phase 1(추출 · Valve List) + Phase 2 기본(Revision) + 지적 사항 · Issue List Excel · 인쇄용 Mark-up PDF · Excel ↔ PDF 연동 · 실제 PMS 비교 (valve02, §9)
  + 실패 원인 분석 · 강건성(A3 · 회전 · 암호/손상) · 사용자 Mark-up 도구 10종 → Issue List · Mark-up PDF (valve03, §10)
  + P&ID · LOGIC 원리 차용: 지문 게이트 · 문턱 빈 띠 실측 · 검토 피드백(VOC) · 차등 시뮬레이션 · 화면 자기검증 (valve04, §11)
  + **456쪽 전수 눈 대조: 오류율 3.54 % → 0.009 % (남은 2 = 도면 오타, Data Error 로 지적)** (valve05, §12).
  + Valve List Excel 은 Vendor 행 없이 Tag 마다 Requirement 한 줄 (valve06).
  + **UI/UX 개선(감사 `docs/valve/UI_UX_AUDIT.md` → 변경 `UI_UX_CHANGELOG.md`): 작업대 머리 띠 · 접이식 px 패널(`[` `]`) · 한 줄 도구줄 · 밸브 부위 그림(칸 → 부위) ·
  대시보드 5×2 + Issues by Category · 목록 키보드 · Revision 같이 움직이기 · PMS 안내 · 내보내기 묶음/확인/상태**
  + **Phase 3 Process Data 실제 비교** (`app/valve/process.py` · `GET /projects/{pid}/process` · 지적 'Process Mismatch' 주황) · Revision 비교 Excel (valve07).
  + **HOLD / TBC 는 모든 칸 · Note 에서 Open Item(Major)** — 실자료 84건 (valve09, 사용자 요청)
  + **valve10 (DESIGN §14)**: PMS 대조 점검 — Ball 품목의 'X BALL/STEM' 이 머리 Trim 보다 우선(1A1A 거짓 Review 16 → 0) · PMS 머리에서 P-T 표 · Service · Class Notes 도 읽음(`READER_VERSION 2`, 옛 json 은 자동 재읽기).
    **특수 요구사항**(`requirements.py`: PFP · Fugitive · NACE … 15종, 출처 포함) → Valve List 열 · Summary 탭.
    **재질 검토 의견**(`matreview.py` MR-01~15, Action/Confirm/Note, 근거 규격 · 증거) → Issue 'Material Review'(청록). 실자료 Action 5 · Confirm 29.
  + **valve11 (DESIGN §15) Ball Valve 엔지니어 검토**: 지식 `knowledge.py`(28항목 → `docs/valve/BALL_VALVE_KNOWLEDGE.md`) · 설계 규칙 `expert.py` VR-01~15 ·
    프로젝트 데이터시트 학습 PC-01(같은 Piping Class 다수 값) → 작업대 **Expert 탭**(재질+설계+학습, 지식 펼치기) · Settings › Ball Valve 지식 · Issue 'Valve Review' · Valve List 'Expert Review (Tool)' 열.
    LLM 없이 결정적 규칙 — '전문가' 는 지식표 + 규칙 + 프로젝트 학습이다. 새 지식은 KB 에, 새 규칙은 VR 로.
  + **valve12 (DESIGN §16) 설계사 코멘트는 핵심만**: 규칙마다 `short` 한 줄(≤120자, 시험) → Issue List · Mark-up PDF · Valve List. 긴 설명은 Expert 탭에만. 새 규칙을 만들 때 short 도 반드시.
  + **valve13 (DESIGN §17)**: Issue List Excel · Mark-up PDF 를 만들 때 **Issue Type 선택 창**(`pickTypes`, 고른 것 기억). 새 Issue 종류를 만들면 `TYPE_KO` 에 한글 설명을 더한다.
  + **valve14 (DESIGN §18)**: Area(North · South · Brownfield · W15) · Site · Unit 을 문서에서 읽어(`location.py`) Issue List Excel 맨 앞 열과 Valve List Excel('All Valves' 시트 + 종류 시트 열)에 넣고 Excel 필터.
  + **valve15 (DESIGN §19)**: Area · Site · Unit 별 Tag 번호 규칙을 프로젝트 Tag 에서 배움(`tagrules.py`, 절차서 문서 없음) → Settings › Tag Numbering · TG 검사(중복 · 접두 · 번호 · 기능↔Fail).
    회사 Tag Numbering Procedure 를 받으면 배운 표와 대조할 것.
  + **valve16 (DESIGN §20)**: 두 Excel 의 목록 시트 첫 열 No. · Summary 시트(Area · Site · Unit × Issue Type / Valve Type + By Area, `exports.summary_sheet`).
  + **valve17 (DESIGN §21)**: Issue List 시트 Area → Site → Unit → Tag 순 · All Valves 에 Note 요구사항 종류별 열(PFP · Fugitive class · Fire safe · NACE · SIL … `requirements.columns`).
  + **valve18 · 19 (DESIGN §22 · §23)**: Issue List · Valve List 에 'Summary by Area' 시트(`exports._area_sheet` · `tbe._area_sheet`).
  + **valve20 (DESIGN §24) 상용 수준**: 데이터시트별 검토 캐시(메모리 + `valve/cache/review/`) · 워밍 · `_json()` · 큰 표 idle 렌더 → 990 DS 에서도 끊김 없음 ·
    간결한 UI(그룹 카드 · 한 줄 탭 · '?' 도움말 · 8 타일) · 매일 DB 백업 · 버전 표시 · **시뮬레이션 `spike/valve_sim.py`**(10,000건 recall/precision 1.000 · 퍼즈 0 예외) + 게이트 시험.
    규칙 코드를 고치면 `python3 spike/valve_sim.py --n 3000` 도 돌린다.
  + **빈 Process Data 항목은 전부 Data Missing**(Process DS 참조여도 — 사용자 요청, valve08) → 실자료 2,529건 · Process Data 값을 Required 로.
  실자료: Process Data(Annexure 7) 68 Tag 중 Datasheet 66 연결 · Match 215 · Mismatch 42(Line No. 32 · P&ID 8 · Fail 위치 2) · Review 2 · Referenced 749.
  새 양식 · 새 자료가 오면 같은 방법으로: `valve_visual_pack.py` → 검토(지시문은 §12) → `valve_visual_score.py`.
  PMS 의 Gasket · Bolting 품목 대조는 아직(볼트는 데이터시트 Note 로 재질 검토 MR-11 만).
- 품질 기준값: `spike/valve_eval.py` → `spike/valve_eval_baseline.json` (지문 541753c612ed · 17,471칸 · Extraction Review 1 · 오독 0 · TBE 일치 92.9 % · PMS Review 58 · F 절 재질 규칙 개수 — `--pd <Process Data PDF>` 를 같이 줘야 온도 규칙이 돈다).
  추출 · PMS 코드를 고치면 `--check` 로 돌린다 — 움직이면 실패하고 바뀐 칸을 보여 준다 (먼저 `--save-baseline` 을 한 번 돌려 둔 `--out` 폴더가 있어야 칸 비교가 나온다). 원인을 칸 단위로 밝힌 뒤에만 `--save-baseline`.
- 매 회차 끝 점검 다섯(valve20: `valve_sim.py --n 3000` 추가): `pytest -q tests/test_valve.py` · `valve_eval.py --check` · `valve_diff_sim.py` (불일치 0) · `node spike/valve_ui_audit.cjs` (데이터 **사본**으로 띄운 서버, 22/22).
- 회사에서 검토가 쌓이면 Review Feedback json 을 받아 `spike/valve_voc.py <파일> --ds <PDF>` — 기각(Dismissed) 많은 규칙부터 고친다.
- 실자료(고객 파일 · 저장소에 없음): Datasheet.pdf 456쪽 → 164 데이터시트(On/Off 140 · MOV 24) · TBE 164/164 Tag 일치.
  자료를 다시 받으면 EGG 는 `python3 spike/valve_unegg.py <폴더> *.egg`, TBE .xls 는 시험용으로 `spike/valve_xls2xlsx.py`(xlrd 필요).
- 시험: `pytest -q tests/test_valve.py` (48개, 실자료는 `VALVE_SAMPLES=<Datasheet.pdf 폴더>`). 전체 1,860 통과 (2026-10-31).
- 마지막 꾸러미: **valve20** (P&ID 서버용만 — 대시보드는 valve01 의 메뉴 그대로). valve01~20 모두 회사 적용 확인 전. 각 꾸러미는 hotfix131 기준 누적이라 valve20 하나만 적용해도 된다.

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
  `python3 spike/pack_delta.py --name valve20 --base 9429f4f --only app/valve/,app/static/valve/,app/main.py,tests/test_valve.py --readme out/valve20/readme_head.txt --ops`
  → `out/PID_dev+ops_valve20_<날짜>.zip`. `--only` 는 딱지(`app/_update.json`)와 기준 파일(`out/PID_dev_delta_base.txt`)을 건드리지 않는다 (PID 세션 번호와 안 섞이게).
  기준 9429f4f = hotfix131 전달본. 회사가 다른 판이면 `--base` 를 그 판으로.
- 대시보드용: `python3 dashboard_tools/make_patch.py --out dashboard_patches --mark` (기준 = `delivered.txt` 맨 아래). `--out` 은 폴더. 첫 전달: `dashboard_patches/UPDATE_from_v16.51_VALVE_menu.zip` (기준 v16.51).
- 적용 순서(회사): ① PID 꾸러미 `apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` (8000 서버 재시작) ② 대시보드 zip `APPLY.bat` (서버 재시작 필요 없음, 화면 새 버전 배너) ③ 대시보드 → 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve.

## 다음에 할 일

1. 회사 적용 확인: .xls 자동 변환(Excel COM)이 되는지, 456쪽 처리 시간, 화면 글꼴, Mark-up 도구(Edge)와 내보낸 PDF 를 Acrobat 에서 열어 보기.
2. Process Data: Control Valve · PRV 표(범위 밖) · Excel 판 · PMS Gasket · Bolting 품목 대조 (§2.4).
4. 재질 · 설계 검토: 회사 재질 · 밸브 엔지니어에게 MR(§14.3) · VR(§15) 규칙과 `BALL_VALVE_KNOWLEDGE.md` 를 보여 회사 사양 값(Floating 한계 · 시트 한계 · PST 정책)으로 맞추고, 기준(시트 한계 · B8M CL.2 해석 · 316 60 °C 문구)을 확인받기. Process Data 에 최저 설계온도가 생기면 저온(MR-04)을 온도로도.
3. 받은 PDF 에 이미 있는 주석(설계사 Mark-up) 읽어 오기 · 1366×768 노트북에서 작업대 사용감 확인.
