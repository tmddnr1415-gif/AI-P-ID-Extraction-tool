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

## hotfix132 (2026-11-05) — 상용 제품 수준 개선 회차
- 요청: "상용 프로그램으로 가기 위한 개선 보완 수정 + 스크린샷". 11개 관점 감사 147건 → 62 백로그 → 48개 반영(검증자 2렌즈 · 21개는 수정안을 고쳐서).
- 6 묶음 병렬 구현(파일 소유 분리): A 공통 셸 · B P&ID 화면 · C 서버 · D LOGIC · E 운영/문서 · F DCS/도서. 사용 한도로 두 번 끊겨 이어받기로 마침.
- 배포 전 적대 리뷰 must 3 · should 8 수정(설명서 HEAD 405 · 운영 폴더에 설명서/백업 경로 · 자료 이동 안내 삭제 · 되돌림 안전 등).
- 판정 로직 diff 0 · 회사 소유/판넬 원본 diff 0. 빠른 시험 2,191 통과. 12화면 × (보통·embed) 콘솔 오류 0.
- 판넬 68c402c6(카드 🗑) 들여옴 · VALVE valve34 라인 병합(ff).

## 2026-11-07 — PDF 스킬 3종 검토 · hotfix133 후보 1건
- 검토: awesomeskill pdf-parser(빈 틀) · ComPDF skills(유료 외부 클라우드 API — 도면 반출·AI 판정이라 불가) ·
  anthropics/skills pdf(pypdf·pdfplumber·OCR·qpdf 안내).  암호·손상·빈 PDF·스캔 PDF 처리는 P&ID `_pdf_problem`
  (hotfix73) · `pipeline` 스캔 판별로 이미 있음 → 엔진 변경 없음.
- 고침: `app/logic/api.py::_check_pdf` 가 연 PDF 를 닫지 않아, 거절 시 Windows 에서 rmtree 가 잠긴 source.pdf 를
  못 지우고 빈 LOGIC 묶음 폴더가 목록에 남을 수 있었다 → finally close.  시험 `tests/test_hotfix133_logic_check_pdf_close.py`.
  (LOGIC 세션 파일 — 다음 L 병합 때 충돌 주의.)  꾸러미는 아직 안 만듦 — 다음 hotfix133 에 실린다.
- 후보(사용자 결정): 스캔 P&ID 글자 인식(로컬 Tesseract) · LOGIC 업로드에도 스캔 PDF 안내.

## 2026-11-07 — anthropics/skills 전체 검토 · 엑셀 내보내기 안전 (hotfix133 후보)
- 19개 중 관련: xlsx · webapp-testing(우리 `spike/smoke_screens.js` 와 같은 방식 — 변경 없음) · frontend-design(hotfix132 셸로 반영됨).
- xlsx 스킬 "수식 오류 0" 을 대조해 2건 발견 → 새 `app/xlsx_safe.py` (`text` · `put` · `append`):
  ① `=` 로 시작하는 도면 글자·의견이 수식으로 저장됨(#NAME? · `=HYPERLINK` 실행) → 글로 저장.
  ② PDF 제어 문자(\x01 등)가 있으면 IllegalCharacterError 로 엑셀 전체 실패 → 그 문자만 뺌 (수정 전 코드로 재현).
- 적용: verdict_export · revision_export · excel_out(우리가 쓰는 칸만 · 발주처 양식의 수식은 그대로) ·
  logic/report · review · grouptest (LOGIC 세션 파일 — `ws.append(` → `xlsx_safe.append(ws, ` 기계적 치환, 병합 때 충돌 주의).
- 시험 `tests/test_hotfix133_xlsx_safe.py` · 빠른 전체 2,199 통과.

## 2026-11-11 — 3D 계측제어 /ic3d 연결 · 규약 v2 반영 (사용자 지시)
- 세션 7 `claude/practical-newton-n6bt58` 865f9297 의 `app/index.html`(1.59MB · 3D 엔진 내장) · `viewer-real.html` → `app/static/ic3d/` (그대로 복사).
  `app/ic3d.py`: `/ic3d` → `/ic3d/` 307(질의 유지) · `/ic3d/` 는 index.html 그대로(공통 띠 없음) · `/ic3d/viewer-real.html` · 그 밖 404.
  `/offline/shell` 에서 ic3d 제외(1.8MB).  release_sources `sources.IC3D`(paths · imported 865f9297).  release_check · smoke_screens 에 /ic3d/.
- 확인: Playwright 로 127.0.0.1 밖 요청을 모두 막고 열기(embed · 일반 · 1366폭) — 외부 요청 0 · 콘솔 오류 0 · Anatomy › 실물 3D 캔버스 그려짐.
  LLM 답변 엔진(api.anthropic.com)은 사용자가 키를 넣고 켤 때만 · 재무(/api/fin) 는 이 서버에 없어 "응답 못 받음(미확인)" 으로 끝남.
- 규약 v2: CLAUDE.md §3 · handoff 고쳐 씀 — 꾸러미는 오케스트레이터만, 이 세션은 개발·커밋·푸시만.
