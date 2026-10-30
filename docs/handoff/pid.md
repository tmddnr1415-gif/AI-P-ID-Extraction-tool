# 인수인계 — "2. PID 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-10-30 · hotfix130)

- 작업 브랜치: `claude/gracious-ride-26nqrf` (세션 "PID 검토 코드 이관 및 로직 수정").  옛 `ccr-2d6327d0-21i1fr` 는
  대화 한도 초과로 멈춰 은퇴 — 내용은 전부 이 브랜치에 있다.  바뀌면 `docs/handoff/branches.md` · `config/release_sources.json` 같이 고침.
- 마지막 꾸러미: **hotfix130** — LOGIC L79~L82 (731473d) 병합.
  충돌 4곳은 옛 LOGIC(bold-einstein L72) 매크로 팔레트 VOC 와 새 L79 팔레트 개편이 같은 자리를 고친 것:
  매크로 목록 JS·HTML 은 **L79 판**(묶음 없어도 공통 Typical — 옛 VOC 기능을 포함), `draw_sets.macro_types` 는 씨앗까지 보는
  `library.typicals()` + L79 의 `origin` 칸, CSS 는 옛 VOC 의 `h3.stack`(제목 세로 밀림) 만 살림.
  옛 `/logic/api/drawings/macros`(`macros` 키) 중복 경로는 지움 — L79 판(`items` 키) 하나.
- hotfix129: LOGIC·DCS 화면 주소 딱지(`app/page_stamp.py`) · 서비스워커가 서버 재시작 뒤 옛 화면을 내주지 않게.
- 시험: `pytest -q -m "not slow and not ui"` 전부 통과 (1,797).  브라우저로 LOGIC 4화면 · 판넬 오류 0.
- 저장소의 `app/_update.json` 은 옛 값(hotfix54) — 꾸러미 안의 것만 새 번호다 (화면 딱지는 회사 PC 에서 맞게 보인다).
- **다음 꾸러미 번호: hotfix131**

## 최근 hotfix 한 줄 요약 (자세한 것은 `docs/history/pid_log.md` · 옛것은 archive 를 grep)

| hotfix | 내용 |
| --- | --- |
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
