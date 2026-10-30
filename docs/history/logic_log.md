# logic 회차 기록 (2026-10-30 부터 · 옛 기록은 같은 폴더의 CLAUDE_archive_*.md)

새 회차를 **끝에** 5~15줄로 덧붙인다.  이 파일은 자동으로 읽히지 않으니 길어져도 된다.

## L79 — Logic 작성 첫 화면 · Typical 기호 팔레트 · 매크로 내부 열기 · 신호 처리 메뉴 (2026-10-30 · 판정 0줄)

* 사용자 지시 넷 (회사 PC 대시보드 사진): *Logic 작성도 Logic 분석처럼 첫 화면 · 시스템 매크로 내부를 보고 고침 · 신호 처리 시뮬레이션 메뉴 ·
  19VA 처럼 Typical 타입별 기호를 왼쪽에서 눌러 붙이고 두 번 누르면 내부.*
* **첫 화면** (`logic_draw.html #home` · `showHome` · `renderHome`) — 그림을 고르지 않고 들어오면(`/logic/draw`) ① 어디에 그릴지(프로젝트 · 새 프로젝트 · 작성자)
  ② 시작하기(새 그림 · 분석 시트에서 · 묶음 통째로 · Typical 사전 · 신호 처리) ③ 저장된 프로젝트(묶음 · 그림 · 공통 Typical 사전에서 꺼낸 그림) · 최근 그린 그림.
  머리줄 `⌂ 첫 화면` · 그림을 지우면 첫 화면.  새로 세는 값 없음 — 그림 목록 · 프로젝트 장부 그대로.
* **Typical 팔레트** (`renderMacroCard` · `macroThumb`) — 타입마다 매크로 상자 그림(이름 · 입력/출력 단자) · 출처별 묶음(이 묶음 · 19VA · 알다프라 · HRSG — 처음엔 이 묶음 · 19VA 만 펼침) · 찾기.
  **묶음 없는 그림도** 공통 Typical 사전을 쓴다 (`GET /logic/api/drawings/macros` · `macro_types` 에 `tid` · `origin`).  누르면 놓기(260ms 뒤 — 두 번 누름과 가름) · 끌어 놓기(첫 단자가 놓은 행에).
* **매크로 내부** (`openMacroInside` · `macroOfBlock`) — 팔레트 타일 · 그림의 매크로 블록을 두 번 누르거나 속성의 `▣ 내부 동작 열기` → 새 창에 그 Typical 그림.
  이 묶음의 Typical 장이면 그 장, 아니면 공통 사전에서 꺼낸 그림(L63 — 고치고 `사전에 저장`).  창은 누른 순간 열어 팝업 차단을 피한다.  시뮬레이션 중에는 L59 그대로.
* **신호 처리 메뉴** — 작성 머리줄 `∿ 신호 처리` · 첫 화면 카드 · P&ID 화면 왼쪽 메뉴 `#nav-logic-signal` · 신호 처리 화면에 `✎ Logic 작성` (?user= 유지) ·
  대시보드 하위 메뉴는 `docs/dashboard_embed.md` §3-3 프롬프트 (dashboard.html 은 이 저장소 밖).
* 화면 자기검증 `spike/ui_audit_l79.py` → `out/l79/` 16항목 통과 · 페이지 오류 0 · 시험 `tests/test_logic_l79_draw_home.py` 2 · 빠른 시험 1582 통과.

