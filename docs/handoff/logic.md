# 인수인계 — "3. Logic 검토코드" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-10-30)

- 작업 브랜치: `claude/logic-symbol-visualization-sim-2oqbxh` (바뀌면 `docs/handoff/branches.md` · `config/release_sources.json` 같이 고침)
- 마지막 회차: **L82** — 엇갈리는 선이 이어지던 것 고침 (작성 시뮬레이션) · 신호 처리 블록 두 번 누름 → 입력 넣고 계산 과정 보기.  **다음은 L83.**
- L82 의 남은 것: 827장 감사에서 '분석 선 둘 이상을 합친 그물' 69개/9장이 남음 — 0024~0029 화살촉 토막이 같은 블록에 닿는 것이라 동작엔 해가 없음.
  감사 방법: 들여온 선 id `n<분석선>_<k>` 로 그림 그물 하나에 살아 있는 분석 선이 둘 이상 섞였는지 센다.
- 대시보드 하위 메뉴 "신호 처리 시뮬레이션"은 `docs/dashboard_embed.md` §3-3 프롬프트를 대시보드 세션에 줘야 선다.
- ⚠ 회차 번호 충돌: 옛 LOGIC 세션(`bold-einstein`, 은퇴)도 L70~L72 를 썼다.  옛 기록에서 같은 번호가 두 번 나오면
  날짜와 브랜치로 구분한다.  앞으로 번호는 이 브랜치 하나만 매긴다.
- 이 브랜치의 L70~L78 은 PID 브랜치에 hotfix128 로 들어갔다.  **LOGIC 은 zip 을 만들지 않는다** —
  커밋·푸시만 하면 PID 세션이 병합해 꾸러미에 싣는다 (`spike/pack_delta.py` 가 덜 합쳐졌으면 멈춘다).

## 최근 회차 한 줄 요약 (자세한 것은 `docs/history/logic_log.md` · 옛것은 archive 를 grep)

| 회차 | 내용 |
| --- | --- |
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
