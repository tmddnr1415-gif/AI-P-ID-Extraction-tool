# 인수인계 — "3. Logic 검토코드" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-10-30)

- 작업 브랜치: `ccr-cc45909d-fjjmrb` (L83 부터 · 그 전 `claude/logic-symbol-visualization-sim-2oqbxh` 는 L82 까지 — 이 브랜치에 다 들어 있음).
  바뀌면 `docs/handoff/branches.md` · `config/release_sources.json` 같이 고침.
- 마지막 회차: **L84** — Logic 작성 가볍게(들여온 선 토막 묶기 `app/logic/draw_compact.py` · 화면 다시 짓기 줄임) · 휠로 장 넘기기 · 저장된 프로젝트 · 묶음 · 그림 지우기.
  **다음은 L85.**
- 선 묶기 규율: 같은 분석 그물 안에서만 · 묶은 뒤 연결(선 단위 그물 + 시뮬레이터 꼴)이 다르면 그 그물은 묶지 않는다.  묶은 선은 `fx` (곧게 펴기에서 붙듦).
  씨앗을 다시 만들면 `python3 spike/compact_draw_seed.py config/logic_draw_seed/<씨앗>.json.gz` (판이 하나 오른다).
- 화면 자기검증: `PW_CHROME=<chrome> python3 spike/ui_audit_l84.py <버릴 데이터 사본> <캡처 폴더>` (지우기를 하므로 사본으로).
  이 컨테이너에서는 `PW_CHROME=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`.
- 기호 동작: 씨앗 827장 기호 8,550 중 못 읽은 것 294 (선 닿은 것 272) — 대부분 분석이 `UNKNOWN`·`?` 로 들인 기호 (원본 PDF 로 다시 읽어야 함).
- 그물 감사: `python spike/audit_l83_nets.py` (시드 827장).  남은 것은 분석 결과에서 두 분석 선이 같은 자리에 겹쳐 나온 것 — 분석기(`graph.py`) 쪽 일.
- 대시보드 하위 메뉴 "신호 처리 시뮬레이션"은 `docs/dashboard_embed.md` §3-3 프롬프트를 대시보드 세션에 줘야 선다.
- ⚠ 회차 번호 충돌: 옛 LOGIC 세션(`bold-einstein`, 은퇴)도 L70~L72 를 썼다.  옛 기록에서 같은 번호가 두 번 나오면
  날짜와 브랜치로 구분한다.  앞으로 번호는 지금 LOGIC 작업 브랜치 하나만 매긴다.
- **LOGIC 은 zip 을 만들지 않는다** — 커밋·푸시만 하면 PID 세션이 병합해 꾸러미에 싣는다 (`spike/pack_delta.py` 가 덜 합쳐졌으면 멈춘다).
- 시험 돌리기: `pip install -r requirements.txt pytest httpx` 뒤 `pytest -q -m "not slow and not ui"` (약 2분 · 1626 통과).

## 최근 회차 한 줄 요약 (자세한 것은 `docs/history/logic_log.md` · 옛것은 archive 를 grep)

| 회차 | 내용 |
| --- | --- |
| L84 | 작성 가볍게 (선 115k→29k · 장 넘기기 3배) · 휠로 장 넘기기 · 프로젝트 지우기 |
| L83 | 엇갈리는 두 파선 ≠ 연결 · 그물 감사 스크립트 |
| L82 | 엇갈림 ≠ 연결 · 신호 처리 블록 두 번 누름 계산 판 |
| L81 | 분석 · 작성 가볍게 (작성 시뮬레이션 23초 → 0.3초) |
| L80 | Logic 작성 가볍게 · 매크로 설명 (MACRO - SWGR / MCC <…>) |
| L79 | Logic 작성 첫 화면 · Typical 기호 팔레트 · 매크로 내부 새 창 · 신호 처리 메뉴 |
| L78 | 시운전 단계별 시뮬레이션 · System Description(Word) · 다시 그린 선 끊긴 끝 잇기 |
| L77 | 다시 그린 아미랄 827장을 로직 그리기 AMIRAL 프로젝트로 · 타이틀블록 칸 |
| L76 | 묶음 들여오기 a5j 양식 · 아미랄 블록 88.7→97.9% |
| L75 | 작도 — 꺾인 선 토막 끌어 옮기기 |
| L72~L74 | 신호 처리 시뮬레이션 페이지 · 연산자 기호 · 도면에서 '시뮬레이션에서 열기' |
| L70~L71 | 최종 명령→최초 입력 거슬러 올라가기 · 연산자 계산 과정 |

## 시작할 때 볼 것

- 설계: `docs/logic_review_design.md` · 지시: `docs/logic_review_kickoff.md` · 기능 목록: `docs/logic_functions.md`
- 옛 회차 전부: `docs/history/CLAUDE_archive_logic_2026-10-30.md` 의 `## LOGIC 회차 기록` 절 (grep 으로)
- 큰 파일 주의: `app/static/logic.js`(수천 줄)·`logic_draw.js` 는 `grep -n` 으로 자리를 찾고 그 부분만 읽는다.
