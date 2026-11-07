# 인수인계 — "2. PID 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-11-05 · hotfix132 — 상용 제품 수준 개선 회차)

- 작업 브랜치: `claude/gracious-ride-26nqrf` (앱 목록 "2. PID 검토 4 (NEW)").  VALVE 라인(valve34)까지 병합됨 — Valve 경로는 꾸러미에 안 실림(company_owned).
- 판넬: `imported` = 68c402c6 (프로젝트 카드 🗑).  옮기는 법은 이전과 같다 (원본 diff 를 경로만 바꿔 apply).
- **hotfix132 에서 새로 생긴 것 — 다음 세션이 알아야 할 자리**
  - 공통 셸 `app/static/shell.{js,css}` — `app/page_stamp.py` 한 곳에서 모든 화면(P&ID `/` 포함 · Valve 제외)에 주입. `?embed=1` 이면 띠 숨김.
    `window.PID_SHELL`(user/setUser=`pid.author` · toast · confirm · help · version) · 띠가 그려지면 `body.pid-shell-on`.
  - 제품 이름·버전·문의처는 `config/product.json` 한 곳. 화면 버전 글 `버전 1.0.0 · 업데이트 N · 날짜`(N = _update.json rev).
  - 사용 설명서 `config/user_manual.md` → `/help/manual` (운영 업데이트에도 실림). 출시 점검 `docs/release_checklist.md`.
  - **꾸러미 전에 `python3 spike/release_check.py` 필수** — pack_delta 가 `out/release_check.json`(ok · dirty=false · head) 없으면 멈춤.
  - 백업·복구 `spike/backup_data.py` + `backup_pid_data.bat`(기본 운영 자료) · DB 하루 한 판 자동 백업(`PID_BACKUP_DIR`).
  - 시험은 `PID_STARTUP_TASKS=0`(conftest) — 기동 감사·백업 루프·씨앗 스레드 안 띄움.
- 감사 결과·남은 일: 62개 백로그 중 48개 반영. 다음 회차 후보(사용자 결정 필요): 로그인/권한(대시보드 토큰) · P&ID·LOGIC 휴지통 ·
  /plaza 제거 여부 · Valve 화면 띠 · LOGIC 분석 취소 · 작도/신호/시운전에 offline.js(쓰기 규칙은 이미 넣음) · 설명서 P&ID 결과 캡처 2장(회사 PC).
- 회사 PC 에서만 확인 가능: `spike/regression_3p.py` 기준선 · `release_check.py --strict` · 대시보드 안 띠(LOGIC·작도를 embed 없이 열면 띠가 보임).
- **다음 꾸러미 번호: hotfix133**
- hotfix133 에 실을 것(아직 꾸러미 없음): LOGIC `_check_pdf` PDF 닫기 (pid_log 2026-11-07).

## 최근 hotfix 한 줄 요약 (자세한 것은 `docs/history/pid_log.md` · 옛것은 archive 를 grep)

| hotfix | 내용 |
| --- | --- |
| 132 | 상용 수준 개선 — 공통 셸·제품 이름 · P&ID/LOGIC 오류 안내 · 서버 보안·백업 · 설명서 · 운영 도구 · 판넬 카드 삭제 |
| 131 | LOGIC L83~L85 (19VA 들여온 그림 = 검토 화면 값 · 파선 입력 · 작성 가볍게) · 판넬 3D 사람 움직임 |
| 130 | LOGIC L79~L82 (Logic 작성 첫 화면 · Typical 팔레트 · 작성 시뮬레이션 23초→0.3초 · 엇갈림≠연결) |
| 129 | LOGIC·DCS 화면 주소 딱지 · 오른쪽 아래 업데이트 이름 · 서비스워커가 옛 화면을 내주지 않게 |
| 128 | 새 LOGIC L70~L78 병합 (시운전 단계별 시뮬레이션 · System Description Word · 신호 처리 시뮬레이션 · 아미랄 827장) |
| 127 | 옛 LOGIC L72 병합 (작도 팔레트 잘림 · 매크로 공통 Typical) |
| 126 | 판넬 화면 ref.js·offline.js 주소에 내용 딱지 · 오른쪽 아래 업데이트 이름 |
| 125 | 판넬 10-28 판(실 출입문) · 옛 LOGIC L70·L71 |
| 121~123 | 판넬 10-26·10-27 판 |
| 115~119 | LOGIC L47~L67 · 도서검토 같은 서버 · 대시보드 apps 꾸러미 |

## 꾸러미(zip) 만드는 법

1. 다른 세션 브랜치 병합: `git fetch origin <브랜치>` → `git merge origin/<브랜치>` (목록은 `config/release_sources.json`).
   판넬은 병합이 아니라 `origin/ccr-d82d97fa-bb3ty3:dashboard/apps/space/` → `app/static/space/` 로 옮기고 `imported` 를 갱신.
2. 머리글 `out/hotfixNNN/readme_head.txt` (현장 사람이 읽는 말 · 무엇이 바뀌었나 · 적용 순서) 를 커밋.
3. `python3 spike/pack_delta.py --name hotfixNNN --base 97a8732 --readme out/hotfixNNN/readme_head.txt --ops`
   → `out/PID_dev+ops_hotfixNNN_<날짜>.zip`.  97a8732 기준 **누적**이다 (회사 PC 가 어느 판이든 덮을 수 있게).
   덜 합쳐진 브랜치가 있으면 멈춘다 — 일부러 뺄 때만 `--allow-unmerged`.
4. zip 과 `out/PID_dev_delta_base.txt` 를 커밋·푸시하고 사용자에게 zip 을 보낸다.
5. 현장 적용: `apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` (서버 재시작 안내대로) → 화면 오른쪽 아래 `업데이트 hotfixNNN` 확인.
   "반영이 안 됐다" 고 하면 ① 어느 브랜치를 합쳤는지 ② 서버 재시작 ③ 브라우저 캐시(Ctrl+F5) 순서로 본다.

## 시작할 때 볼 것

- 부서원 VOC: `python spike/voc.py list` → `brief` → 고친 뒤 `resolve` (`docs/voc.md`).
- 엔진 원칙·불변식·로드맵: `docs/state_and_roadmap.md` (목차 보고 필요한 절만).
- 회귀: `python3 spike/regression_3p.py` (PDF 가 있는 회사 PC) · 기준선 `spike/baselines_3p.json`.
