# pid 회차 기록 (2026-10-30 부터 · 옛 기록은 같은 폴더의 CLAUDE_archive_*.md)

새 회차를 **끝에** 5~15줄로 덧붙인다.  이 파일은 자동으로 읽히지 않으니 길어져도 된다.

## hotfix128 (2026-10-30) — 새 LOGIC 병합 · CLAUDE.md 다이어트
- 현장: "로직이 최신 로직 변경 내용이 반영 안 된 것 같다" (hotfix127 적용 후).
- 원인: hotfix127 이 옛 LOGIC 브랜치 `bold-einstein`(L72)만 합쳤고, 실제로 쓰는 새 LOGIC 세션 브랜치
  `logic-symbol-visualization-sim` 의 L70~L78(11커밋)이 빠졌다.  두 세션이 같은 회차 번호를 따로 매겨 알아채기 어려웠다.
- 고침: 병합(충돌은 logic.html/js 버튼 줄 하나 — DCS·시운전 둘 다 남김) · `pack_delta.py` 가
  `config/release_sources.json` 의 브랜치가 덜 합쳐졌으면 멈춤 · 브랜치 지도 `docs/handoff/branches.md`.
- 같이: CLAUDE.md 가 960KB 라 매 요청마다 실려 "Prompt is too long" 이 반복됐다 → 짧은 안내판으로 바꾸고
  옛 내용은 `docs/history/CLAUDE_archive_pid_2026-10-30.md` 로.  `tests/test_context_budget.py` 가 크기 상한을 지킨다.
- ⚠ 클라우드에 PyMuPDF 설치가 막혀 Python 시험을 못 돌림 (JS 구문 · 병합 대조만).
