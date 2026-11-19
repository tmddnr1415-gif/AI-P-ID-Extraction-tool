# 인수인계 — 5. 도서 검토 (계장도서검토) · 상한 15KB · 덧붙이지 말고 고쳐 쓴다

## 지금 상태 (2026-11-19 · 화면 VERSION `2026-11-19.1`)

- **무엇**: 서버 PC 의 공용 도서 폴더(PDF · Word · Excel · PPT · EPUB · HWPX · TXT · MD · CSV)를 한 번 색인하면 부서원이 말하듯 검색한다.
  결과마다 '왜 관련 있나'(근거 구절 · 쪽 · 핵심 항목 · 종류/분야) · 📚 추천 읽기 순서 · 📍 바로 볼 곳 · 💬 답변(폴더 원문 인용 #도서번호 · 쪽 ↔ 내장 학습 지식 분리) ·
  미리보기(원본 쪽/글자 · 책 안 찾기 · 연관 검색 새 창 · 복사) · 번역(PC 안 번역 · 용어 풀이).
- **어디서**: 회사 PC = P&ID 서버(8000)의 `/books/` (대시보드 메뉴 '도서검토', hotfix115 부터). 개발 원본 = 이 브랜치 `claude/new-session-v23o67` 의
  `dashboard/apps/books/{index.html, kb.js, vendor/}` · `dashboard/books_api.py`. 오케스트레이터가 통합 브랜치의 `app/static/books/` · `app/books_api.py` 로 옮겨 싣는다
  (통합 시험 `tests/test_hotfix115_books.py` 가 "API 파일은 대시보드 파일 그대로" 를 확인).
- **회사판 규칙(2026-11-19)**: 외부 번역(Claude · api.anthropic.com)은 **기본 꺼짐**. 화면에 Claude 선택지 · 설정 칸이 없고 `/api/books/translate` · `translate-config` 는 403.
  코드는 남김 — 서버 PC 환경변수 `BOOKS_EXTERNAL_TRANSLATE=1` 일 때만 열림. 시험 `tests/test_books_external_off.py`(통합 브랜치용, `dist/books_integration/` 패치에 들어 있음).
- **검색 품질** (`tools/books_sim`, 인터넷 공개 도서 67권 · 12,240쪽, nDCG@10 / MRR):

  | 묶음 | 2026-10-24 | 2026-11-19 |
  |---|---|---|
  | 조정용 48문 | 0.895 / 0.969 | **0.915 / 1.000** |
  | 시험용 20문 (조정에 안 씀) | 0.917 / 0.975 | 0.917 / 0.975 |
  | 발전 · 플랜트 15문 | 0.726 / 0.723 | **0.749 / 0.773** |

  11-19 개선: 부서 폴더에 섞인 외국어 자료(베트남어 강의 · 포르투갈어/스페인어 매뉴얼 · 러시아어 문서)의 계장 용어를 사전에 보강(`THES_I18N`) —
  유량 4문 0.73~0.85 → 0.86, 포지셔너 3문 +0.18, 압력 전송기 +0.06, 제어밸브 Cv +0.34. **내려간 질문 0**(질문별 전후 비교).
  뜻이 넓은 외국어 단독 낱말(vazão · nível · уровень · transmissor …)은 엉뚱한 책을 올려서 넣지 않음.
- **지식 베이스** `kb.js`: 발전 · 플랜트 계장 개념 49개(터빈 · HRSG · DCS · PLC · 펌프 · 써모웰 · 게이지 · 스위치 · 차단밸브 · MOV · 국제 규격) + 학습 노트 118개(출처 표시).

## 파일

| 파일 | 하는 일 |
|---|---|
| `dashboard/apps/books/index.html` | 화면 + 검색 엔진(BM25 + 개념 사전 THES · THES_ADD · THES_I18N · 한영 용어집 GLOSS_SRC) + 번역 + 💬 답변 · 한 파일 |
| `dashboard/apps/books/kb.js` | 발전 · 플랜트 지식 베이스(개념 · 분야 · 학습 노트) |
| `dashboard/books_api.py` | 공용 도서관 API(표준 라이브러리만) · 폴더 지정은 서버 PC 만 · 키는 `books/secret.json` · 회사판 외부 번역 차단 |
| `dashboard/apps/books/INTEGRATION.md` | 대시보드 연결 안내 |
| `tools/books_sim/` | 검색 품질 시뮬레이션(`sim.js dev|test|pp|tune`) · 질문 · 라벨 · `SIMULATION.md` |
| `dist/books_integration/` | 통합 브랜치(`app/…`)에 그대로 적용하는 패치 — API · 화면 · 시험 |
| `dist/valve_kinds/` | (끝난 일) valve37 패치 — 통합 440a3bb1 에 적용됨, Valve 는 S6 담당 |

## 회사에서 확인할 것

1. 도서검토 화면 왼쪽 아래(또는 Settings)의 버전이 `2026-11-19.1` 인지 · [🌐 번역] 엔진 목록에 Claude 가 **없는지**.
2. 실제 부서 도서 폴더로 색인 → 레벨 · 유량 · 전송기 질문 몇 개로 상위 5권이 맞는지 (시뮬레이션은 인터넷 공개 도서).
3. 외국어(베트남어 · 포르투갈어) 자료가 폴더에 있으면 그 책이 한국어 질문에 잡히는지.
4. 브라우저 내장 번역은 Edge 버전에 따라 없을 수 있음 — 그때는 용어 풀이만.

## 다음에 할 일

1. 실제 부서 도서로 질문 20~30개 라벨(`queries_test.json` 형식) → `sim.js` 로 다시 조정.
2. 발전 · 플랜트 묶음의 약한 주제(케이블 스케줄 · 보일러 연소 · DCS 캐비닛 · 제어밸브 사이징) — 시험 도서에 정답 책이 없어 상한이 낮음. 실제 도서가 오면 그때.
3. 스캔본(그림만 있는 PDF)은 파일명으로만 찾음 — OCR 은 회사 규칙상 보류.

## 시험

- 통합 브랜치에서: `pytest tests/test_books_external_off.py tests/test_hotfix115_books.py tests/test_wpc_server.py tests/test_shell.py tests/test_wpe_backup.py` → 79 통과(2026-11-19).
- 검색 품질: 시험 서버(대시보드 server.py + 이 브랜치 파일, 도서 폴더 지정) 뒤 `cd tools/books_sim && node sim.js dev && node sim.js test && node sim.js pp`.
