# 인수인계 — "2. PID 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-11-11 · 규약 v2 — 꾸러미는 오케스트레이터가 만든다)

- 작업 브랜치: `claude/gracious-ride-26nqrf` (앱 목록 "2. PID 검토 4 (NEW)").
- ★ **규약 v2 (2026-11-07 사용자 결정)**: 회사 업데이트 zip 은 **오케스트레이터 세션**(`claude/trusting-cray-v68axq`)이 만든다 —
  hotfix133 · 134 를 그쪽이 냈고 다음 번호(hotfix135)도 그쪽이 매긴다.  **이 세션은 개발 · 시험 · 커밋 · 푸시 · 이 문서 갱신만**.
  zip · 번호 · 다른 브랜치 병합 금지.  규약: `git show origin/claude/trusting-cray-v68axq:CONVENTIONS.md`.  끝나면 오케스트레이터
  (session_01Muj82FygSCFAVRooofwhVK)에 send_message 로 "푸시 완료 · 커밋 · 바뀐 파일 수" 한 줄.
- 3D 계측제어 `/ic3d` (2026-11-11): 세션 7(`claude/practical-newton-n6bt58`) `app/index.html` · `viewer-real.html` → `app/static/ic3d/`
  (`imported` 865f9297 · server.py 는 안 가져옴) · `app/ic3d.py` (`/ic3d` → `/ic3d/` 307 · 공통 띠 없음 · 파일 그대로) ·
  절전 보관 목록에서 뺌 · release_check/smoke_screens 에 /ic3d/.  외부 요청 0 · 실물 3D 그려짐 확인. 시험 `tests/test_ic3d_route.py`.
- 판넬: `imported` = 68c402c6 (프로젝트 카드 🗑).  옮기는 법은 이전과 같다 (원본 diff 를 경로만 바꿔 apply).
- **hotfix132 에서 새로 생긴 것 — 다음 세션이 알아야 할 자리**
  - 공통 셸 `app/static/shell.{js,css}` — `app/page_stamp.py` 한 곳에서 모든 화면(P&ID `/` 포함 · Valve 제외)에 주입. `?embed=1` 이면 띠 숨김.
    `window.PID_SHELL`(user/setUser=`pid.author` · toast · confirm · help · version) · 띠가 그려지면 `body.pid-shell-on`.
  - 제품 이름·버전·문의처는 `config/product.json` 한 곳. 화면 버전 글 `버전 1.0.0 · 업데이트 N · 날짜`(N = _update.json rev).
  - 사용 설명서 `config/user_manual.md` → `/help/manual` (운영 업데이트에도 실림). 출시 점검 `docs/release_checklist.md`.
  - 백업·복구 `spike/backup_data.py` + `backup_pid_data.bat`(기본 운영 자료) · DB 하루 한 판 자동 백업(`PID_BACKUP_DIR`).
  - 시험은 `PID_STARTUP_TASKS=0`(conftest) — 기동 감사·백업 루프·씨앗 스레드 안 띄움.
- 감사 결과·남은 일: 62개 백로그 중 48개 반영. 다음 회차 후보(사용자 결정 필요): 로그인/권한(대시보드 토큰) · P&ID·LOGIC 휴지통 ·
  /plaza 제거 여부 · Valve 화면 띠 · LOGIC 분석 취소 · 작도/신호/시운전에 offline.js(쓰기 규칙은 이미 넣음) · 설명서 P&ID 결과 캡처 2장(회사 PC).
- 회사 PC 에서만 확인 가능: `spike/regression_3p.py` 기준선 · `release_check.py --strict` · 대시보드 안 띠(LOGIC·작도를 embed 없이 열면 띠가 보임).
- 회사에 보일 변경 (다음 통합본 `1_먼저읽기` 용):
  - 3D 계측제어 화면을 P&ID 서버 `/ic3d` 에서 연다 (대시보드 메뉴에서 열림 · 인터넷 없이 동작).
  - 엑셀 내보내기: `=` 로 시작하는 글은 글 그대로 · PDF 의 보이지 않는 문자로 엑셀이 실패하지 않음 (`app/xlsx_safe.py` · LOGIC 엑셀 3종 포함).
  - LOGIC: 암호·빈 PDF 를 거절할 때 빈 묶음이 목록에 남지 않음.
  (11-07 두 항목이 hotfix133/134 에 실렸는지는 오케스트레이터 `status/packages.json` 으로 확인.)
- 진행 중: LOGIC 분석 → 그리기 변환 정확도 검사 (사용자 요청 · 무작위 장 · 캡처 · 장별 안 되는 것).

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

## 꾸러미(zip) — 이 세션은 만들지 않는다 (규약 v2)

- 만드는 법은 오케스트레이터 규약 `CONVENTIONS.md` §5-1 · §6 (통합 브랜치에서 `release_check.py` → `pack_delta.py --base 97a8732 … --ops`).
- 현장 적용: `apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` → 화면 띠의 `업데이트 N` 확인.
  "반영이 안 됐다" 고 하면 ① 꾸러미에 그 커밋이 들었나 ② 서버 재시작 ③ 브라우저 캐시(Ctrl+F5) 순서로 본다.

## 시작할 때 볼 것

- 부서원 VOC: `python spike/voc.py list` → `brief` → 고친 뒤 `resolve` (`docs/voc.md`).
- 엔진 원칙·불변식·로드맵: `docs/state_and_roadmap.md` (목차 보고 필요한 절만).
- 회귀: `python3 spike/regression_3p.py` (PDF 가 있는 회사 PC) · 기준선 `spike/baselines_3p.json`.
