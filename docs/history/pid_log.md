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

## hotfix129 (2026-10-30) — 세션 이관 · LOGIC 화면이 옛 판으로 뜨는 길 막기
- "2. PID 검토 3 (NEW)" 세션이 대화 한도 초과로 멈춤 → 새 세션 브랜치 `claude/gracious-ride-26nqrf` 로 이관.
- LOGIC 변경 전수 대조: 새 LOGIC(`logic-symbol-visualization-sim`)·옛 LOGIC(`bold-einstein`) 둘 다 HEAD 에 0커밋 남음.
  hotfix128 병합(502a0bf)을 처음부터 다시 해 맞대 봄 → 충돌 두 줄(버튼, 둘 다 남김) 말고 같음.  zip 에 빠진 LOGIC 파일은 캡처·기록(out/ · docs/)뿐.
- 원인 후보 두 가지를 코드에서 찾아 고침: LOGIC·DCS 화면만 고정 스크립트 주소(브라우저 캐시) → `app/page_stamp.py` 내용 딱지 ·
  서비스워커가 서버 재시작 사이 "꺼짐" 을 기억하면 옛 화면 보관본을 먼저 내줌 → 화면은 서버에 1.5초 먼저.
- 시험: hotfix128 때 못 돌린 Python 시험을 이번에 돌림 — 전부 통과.  `tests/test_hotfix129_logic_asset_tag.py`.

## hotfix130 (2026-10-30) — LOGIC L79~L82 병합
- 사용자 요청은 "hotfix129" 였으나 129 는 이미 냈으므로 130 으로 (같은 이름 다른 파일이 생기지 않게).
- 충돌 4곳 (draw_sets.py · logic_draw.css/html/js) — 옛 LOGIC VOC(매크로 팔레트) vs 새 L79 팔레트. L79 판을 쓰고
  옛 VOC 의 씨앗 포함(`library.typicals`) · 제목 줄바꿈(`h3.stack`)만 살림.  중복 `/drawings/macros` 경로 하나 지움, 시험 키 macros→items.
- 시험 전부 통과 · 작도 화면 매크로 타일 24개(19VA 8 · 알다프라 10 · HRSG 6) 오류 0.

## hotfix131 (2026-10-31) — LOGIC L83~L85 · 판넬 3D 사람 움직임
- LOGIC 이 새 세션 브랜치 `ccr-cc45909d-fjjmrb` 로 옮겨 감 (L83~L85, L82 포함).  branches.md 충돌은 두 쪽 행을 다 살려 풂.
- 판넬 0869426→0943667 diff 를 app/static/space/index.html 에 apply (깨끗) · imported 갱신.
- L85 graph.py 접합 규칙이 실선에도 걸려 L71 퍼징 실패 → 파선 한정.  19VA 실도면 재측정은 LOGIC 세션 몫.
