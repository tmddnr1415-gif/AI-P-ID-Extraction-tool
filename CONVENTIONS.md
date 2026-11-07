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

## 5. 덮어쓰기 원칙 — 회사 PC 에 무엇이 깔려 있든 최신으로 (2026-11-07 사용자 결정)

회사 PC 에 hotfix132 가 적용됐는지와 **무관하게**, 두 파일 모두 적용하면 각 세션 최신판이 된다.

| 파일 | 방법 |
|---|---|
| ① DASHBOARD | 기준판 비교형(`UPDATE_from_vA_to_vB`) 대신 **어느 버전에서든 적용되는 판**(S1 의 `--any` / FULL 꾸러미)으로 만든다 |
| ② 통합 | `pack_delta.py --base` 를 **마지막으로 적용 확인된 시점**(지금: 2026-11-02 valve29 · 대시보드 v16.51 → 그때 PID 기준 커밋)으로 잡는다. 그 뒤 바뀐 파일을 **전부** 싣고, `apply_delta.py` 는 그 사이 우리가 보낸 어느 버전이든(known) 덮는다 → 131 이든 132 든 최신으로 |
| ② 회사에서 고친 파일 | 지금 적용기는 `.new` 로 비켜 두거나(개발 폴더) 전체를 멈춘다(운영 `--all-or-nothing`). 이번부터는 **백업 뒤 최신으로 덮는 방식**(`--overwrite` 신설: conflict → `backup\<꾸러미>_<시각>\` 에 원본 → 새 판으로 교체 · `1_먼저읽기` 에 덮은 파일 목록)으로 바꾼다. 되돌리기는 기존 `--restore` 그대로 |

- 회사 쪽 수정이 지워질 수 있는 파일(예: 11-01~02 회사 PC 에서 고친 `app/valve/*`)은 백업 위치와 함께 `1_먼저읽기` 맨 위에 적는다.
- 실패하면 반쪽 업데이트를 남기지 않는 hotfix132 안전장치(자동 되돌림)는 그대로 둔다.
- 도구 고침(`--overwrite`, base 선택)은 **업데이트 파일을 만들 때** 통합 브랜치에서 한다 — 요청 전에는 만들지 않는다.

## 6. 오케스트레이터 절차 (사용자가 "회사 업데이트 파일 만들어 줘" 할 때만)

1. 7개 브랜치 fetch · 각 브랜치 끝 커밋과 인수인계의 변경점 확인
2. 기준점 = 마지막 **적용 확인** 시점 (5장 덮어쓰기 원칙) — 확인 안 된 꾸러미는 깔렸다고 보지 않는다
3. ① 대시보드가 바뀌었으면 S1 도구로 UPDATE zip
4. ② S2 브랜치 기준 통합 브랜치에 3~7 을 위 표대로 싣고 → 시험 → `release_check.py` → `pack_delta.py`
5. 두 zip 과 `1_먼저읽기` 를 사용자에게 전달 → **사용자가 회사 PC 적용을 알려 주면** 기준점 갱신

## 7. 세션 현황판 — `status/SESSION_STATUS.html`

오케스트레이터가 따로 만드는 HTML. 각 세션의 **최신 작업 현황 · 미리보기 · 다음 업데이트에 들어갈 것**을 한 장에 보여 준다.

- 만들기: `git fetch origin` → 세션 상태를 `status/sessions.json` 에 갱신(list_sessions) → `python status/build_status.py`
- 숫자 · 커밋은 각 브랜치(git)에서 자동으로 읽는다: ① DASHBOARD 는 `delivered.txt` 마지막 줄 이후, ② 통합은 마지막 hotfix 꾸러미 · `release_sources.json` imported · PID 브랜치에 아직 없는 커밋
- 미리보기는 `status/previews/<SID>_<n>.jpg` — 오케스트레이터가 최신 코드를 실제로 띄워 찍어 갈아 끼운다 (날짜 표시)
- 업데이트 파일 만들기와는 별개 — 현황판은 언제든 다시 만들 수 있다
