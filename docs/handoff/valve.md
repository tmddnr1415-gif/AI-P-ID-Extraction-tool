# 인수인계 — "VALVE Datasheet 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-10-31 · valve01)

- 작업 브랜치: `ccr-efbe7e75-n915ze`. 이 브랜치는 PID(`claude/gracious-ride-26nqrf`, hotfix131) 와 DASHBOARD(`ccr-248a5c4d-3dji7g`, v16.51) 를 병합한 위에 있다.
- 무엇: 대시보드 **실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve** = P&ID 서버(8000) `/valve/` — Valve Datasheet 검토 도구.
  설계 · 분석 · 남은 일: `docs/valve/DESIGN.md` (먼저 §1 표와 §8).
- Phase 1(추출 · Valve List) 완료 + Phase 2 기본(Revision 칸별 비교 · 노랑 표시 PDF). Phase 3(Process) · 4(PMS)는 화면 틀만 — 결과 'Not Evaluated', 예시는 MOCK 버튼.
- 실자료(고객 파일 · 저장소에 없음): Datasheet.pdf 456쪽 → 164 데이터시트(On/Off 140 · MOV 24) · TBE 164/164 Tag 일치 · Review Required 69칸.
  자료를 다시 받으면 EGG 는 `python3 spike/valve_unegg.py <폴더> *.egg`, TBE .xls 는 시험용으로 `spike/valve_xls2xlsx.py`(xlrd 필요).
- 시험: `pytest -q tests/test_valve.py` (7개, 실자료는 `VALVE_SAMPLES=<Datasheet.pdf 폴더>`). 전체 1,836 통과 (2026-10-31).
- 마지막 꾸러미: **valve01** (아래 §꾸러미). 회사 적용 확인 전.

## 파일

| 파일 | 하는 일 |
|---|---|
| `app/valve/extract.py` | PDF → 칸 (On/Off Form 80 · MOV Form 102 · 공정 조건표 · Notes · General Notes) |
| `app/valve/schema.py` | 라벨 사전 · Tag 정규화 · 밸브 종류 · 공정이 아닌 칸 목록 |
| `app/valve/store.py` | SQLite `{data}/valve/valve.db` · 원본 `{data}/valve/files/` · 감사 · Rev 순서 · 열 추가 이전(_migrate) |
| `app/valve/tbe.py` | Valve List(TBE Appendix) 채우기 · .xls → .xlsx (회사 PC 의 Excel) |
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
  `python3 spike/pack_delta.py --name valve01 --base 9429f4f --only app/valve/,app/static/valve/,app/main.py,tests/test_valve.py --readme out/valve01/readme_head.txt --ops`
  → `out/PID_dev+ops_valve01_<날짜>.zip`. `--only` 는 딱지(`app/_update.json`)와 기준 파일(`out/PID_dev_delta_base.txt`)을 건드리지 않는다 (PID 세션 번호와 안 섞이게).
  기준 9429f4f = hotfix131 전달본. 회사가 다른 판이면 `--base` 를 그 판으로.
- 대시보드용: `python3 dashboard_tools/make_patch.py` (기준 = `dashboard_tools/delivered.txt` 맨 아래 = v16.51) → `dashboard_patches/…zip`. 건넬 것은 `--mark`.
- 적용 순서(회사): ① PID 꾸러미 `apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` (8000 서버 재시작) ② 대시보드 zip `APPLY.bat` (서버 재시작 필요 없음, 화면 새 버전 배너) ③ 대시보드 → 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve.

## 다음에 할 일

1. 회사 적용 확인: .xls 자동 변환(Excel COM)이 되는지, 456쪽 처리 시간, 화면 글꼴.
2. Phase 3 Process Data (DESIGN §2.3 · §8) → Phase 4 PMS (§2.4).
3. Revision 비교 Excel 보고서 · Combined Mark-up PDF.
