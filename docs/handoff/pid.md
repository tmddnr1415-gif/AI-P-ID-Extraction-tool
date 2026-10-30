# 인수인계 — "2. PID 검토" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-10-30 · hotfix128)

- 작업 브랜치: `ccr-2d6327d0-21i1fr` (바뀌면 `docs/handoff/branches.md` · `config/release_sources.json` 같이 고침)
- 마지막 꾸러미: **hotfix128** — 새 LOGIC 브랜치(`logic-symbol-visualization-sim`)의 L70~L78 병합.
  hotfix127 은 옛 LOGIC 브랜치(L72)만 합쳐서 새 LOGIC 변경이 빠져 있었다.
  병합 충돌은 `logic.html`/`logic.js` 의 버튼 줄 하나 — **🖥 DCS 그래픽(PID 쪽)과 📘 시운전(LOGIC L78) 둘 다 남김.**
- **다음 꾸러미 번호: hotfix129**
- 이 회차에 함께 바꾼 것: `CLAUDE.md` 를 짧게(옛 내용은 `docs/history/`) · `pack_delta.py` 병합 확인 · `tests/test_context_budget.py`.
- ⚠ hotfix128 은 클라우드 환경에 PyMuPDF·fastapi 를 설치할 수 없어 **Python 시험을 못 돌렸다**
  (JS 구문 검사와 "LOGIC 변경이 전부 들어왔는지" 대조만 함).  다음 세션에서 `python -m pytest -q -m "not slow and not ui"` 를 한 번 돌릴 것.

## 최근 hotfix 한 줄 요약 (자세한 것은 `docs/history/pid_log.md` · 옛것은 archive 를 grep)

| hotfix | 내용 |
| --- | --- |
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
