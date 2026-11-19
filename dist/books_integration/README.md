# 도서검토 2026-11-19.1 — 통합 브랜치용 패치

`books_2026-11-19.1_on_integration.patch` = 통합 브랜치(`claude/trusting-cray-v68axq`)에 `git apply` (적용 확인함).

| 파일 | 바뀐 것 |
|---|---|
| `app/books_api.py` | 회사판 기본: 외부 번역(Claude) 꺼짐 — `BOOKS_EXTERNAL_TRANSLATE=1` 일 때만 열림. 기본값에서 `translate` · `translate-config` 403, info 에 `translate.external=false`, 설정 칸 숨김 |
| `app/static/books/index.html` | VERSION 2026-11-19.1 · 외부 번역이 막혀 있으면 Claude 선택지 · 설정을 숨기고 PC 안 번역만 · 외국어 계장 용어 사전 `THES_I18N` (레벨 · 유량 등) |
| `tests/test_books_external_off.py` (새) | 기본값 차단 · 키 저장 안 됨 · 외부 호출 없음 · 환경변수로만 열림 |
| `tests/test_wpc_server.py` | 키 보관 시험에 `BOOKS_EXTERNAL_TRANSLATE=1` (허가된 경우를 시험) |

원본은 이 브랜치 `dashboard/books_api.py` · `dashboard/apps/books/index.html` (통합본의 hotfix115 · 132 수정을 먼저 받아 맞춘 뒤 고침 — 두 파일은 패치 결과와 바이트 단위로 같음).
시험: 위 테스트 + `test_hotfix115_books.py` · `test_shell.py` · `test_wpe_backup.py` → 79 통과.
