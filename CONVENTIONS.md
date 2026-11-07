# 세션 공통 규약 v2 — 회사 PC 업데이트 파일 (2026-11-07 사용자 결정)

> 기획: [`ORCHESTRATION_PLAN.md`](ORCHESTRATION_PLAN.md) · 현황: [`ORCHESTRATION_STATUS.md`](ORCHESTRATION_STATUS.md)
> v1 의 `dist/company_pc/<SID>/` 규칙은 **폐지** — 세션은 배포물을 만들지 않는다.

## 1. 역할

| 누가 | 하는 일 | 하지 않는 일 |
|---|---|---|
| **각 세션 (1~7)** | 기능 개발 · 시험 · 자기 브랜치에 커밋·푸시 · 인수인계 문서 갱신 | 회사 업데이트 zip 만들기, hotfix/valve/v 번호 매기기 |
| **오케스트레이터 세션** | 사용자가 요청하면 7개 브랜치를 모아 **회사 업데이트 파일 2개**를 만든다 · 번호 · 기준점(delivered) 관리 · 브랜치 지도 관리 | 각 세션의 기능 코드 고치기 |

## 2. 회사 업데이트 파일 = 2개

| 파일 | 담는 것 | 만드는 법 (기존 도구 그대로) |
|---|---|---|
| ① `UPDATE_from_vA_to_vB.zip` (+ `1_DASHBOARD_update_vX_날짜.zip`) | **1. DASHBOARD** | S1 브랜치 기준 · `dashboard_tools/delivered.txt` 마지막 줄 대비. 대시보드가 바뀐 때만 |
| ② `PID_dev+ops_hotfixNNN_날짜.zip` | **2. P&ID · 3. LOGIC · 4. PANEL · 5. 도서 · 6. Valve · 7. 3D** | S2 브랜치 기준 통합 → `spike/release_check.py` → `spike/pack_delta.py` |

②에 다른 세션을 싣는 방법 (`config/release_sources.json`, 통합할 때 오케스트레이터가 고친다):

| 세션 | 브랜치 | 싣는 방법 |
|---|---|---|
| 3. LOGIC | `ccr-cc45909d-fjjmrb` | 병합 |
| 4. PANEL | `ccr-d82d97fa-bb3ty3` | `dashboard/apps/space` → `app/static/space` 옮김 (`imported` 갱신) |
| 5. 도서 | `claude/new-session-v23o67` | `dashboard/apps/books` → `app/static/books` 옮김 (`imported` 갱신) |
| 6. Valve | `ccr-efbe7e75-n915ze` | 병합 — **`company_owned` 규칙 삭제** (더는 따로 내지 않음 · valveNN 꾸러미 폐지) |
| 7. 3D | `claude/practical-newton-n6bt58` | `app/` (IC 화면) → `app/static/ic3d` 옮김 + PID 서버 `/ic3d` 주소 (S2) · DASHBOARD 메뉴 (S1) |

## 3. 회사 PC 제약 (모든 세션 공통)

Windows · Edge · Python 3.11 · CDN/npm/외부 서비스 금지 (라이브러리는 파일 안에) · 사내 데이터 외부 전송 금지 · API 키를 넣지 않는다.

## 4. 각 세션이 지킬 것

1. 작업이 끝나면 자기 브랜치에 커밋·푸시. 회사에 줄 zip 은 만들지 않는다.
2. 브랜치를 바꾸면(새 세션) 오케스트레이터에 알린다 — 브랜치 지도(`docs/handoff/branches.md` · `release_sources.json`)는 오케스트레이터가 고친다.
3. 회사에 보일 변경점은 인수인계 문서(`docs/handoff/<세션>.md` 또는 세션 보고서)에 한 줄씩 남긴다 — 통합본의 `1_먼저읽기.txt` 를 여기서 모은다.
4. 다른 세션 경로는 건드리지 않는다 (공유 파일 `app/main.py` · `dashboard.html` 은 꼭 필요한 줄만, 인수인계에 적는다).
5. 안전 문서 원칙: 자동 판독 결과는 사람 검토 전 확정본이 아니다.

## 5. 오케스트레이터 절차 (사용자가 "회사 업데이트 파일 만들어 줘" 할 때)

1. 7개 브랜치 fetch · 각 브랜치 끝 커밋과 인수인계의 변경점 확인
2. 회사 PC 기준점 확인 — 대시보드 `delivered.txt` · PID 는 마지막 **적용 확인** hotfix (사용자 확인)
3. ① 대시보드가 바뀌었으면 S1 도구로 UPDATE zip
4. ② S2 브랜치 기준 통합 브랜치에 3~7 을 위 표대로 싣고 → 시험 → `release_check.py` → `pack_delta.py`
5. 두 zip 과 `1_먼저읽기` 를 사용자에게 전달 → **사용자가 회사 PC 적용을 알려 주면** 기준점 갱신
