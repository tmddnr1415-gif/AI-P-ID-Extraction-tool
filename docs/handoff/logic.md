# 인수인계 — "3. Logic 검토코드" 세션 (상한 15KB · 덧붙이지 말고 고쳐 쓴다)

## 지금 상태 (2026-11-07)

- 작업 브랜치: `ccr-cc45909d-fjjmrb` (L83 부터 · 그 전 `claude/logic-symbol-visualization-sim-2oqbxh` 는 L82 까지 — 이 브랜치에 다 들어 있음).
  바뀌면 `docs/handoff/branches.md` · `config/release_sources.json` 같이 고침.
- 마지막 회차: **L91** — 매크로 두 번 누름 → '이 프로젝트에서 열기': 공통 사전 매크로면 그 Typical 장을 묶음(프로젝트)에 사본으로 들여와
  새 창으로 연다 · 거기서 시뮬레이션 · 고치기 · 저장 → 그 프로젝트의 매크로만 바뀜 (공통 사전은 '공통 사전을 고치기' 단추로 따로).
  이미 들여온 매크로는 바로 그 장을 연다.  **다음은 L92.**
- 그 앞 L90: 기호 · 매크로 창 두 번 누름 상세 — 기호는 설명 · 직접 해 보기(`draw_sim.symbol_sim`), 매크로는 단자 · 설명 · 내부 동작.
- 그 앞 L89: 분석한 Logic 을 불러와 똑같이 그리기 정확도 95% 이상 (19VA 827장 · 되읽기 블록 99.1 · 표 99.9 · 연결 96.0 · 선 96.3 · 글 96.7 /
  직접 블록 99.6 · 표 100 · 연결 96.2) · 원본 글 · NOTE 를 그 자리에 · 접합 용접 · 분석기 파선≠상자 변 · 씨앗 판 6.
- 정확도 다시 재기: ① 원본 PDF 를 지금 분석기로 분석하고 앱 판(`api._result`, 단자 이름 · 상수 얹음)을 JSON 으로
  (데이터 폴더에 logic/<12자리 id>/source.pdf + result.json 을 두고 `A._result(id)` → {"sheets": …}) ② `python3 spike/fidelity_l89.py <그 JSON> <source.pdf> out.json 6`
  (827장 약 2분).  잣대 정의는 스크립트 머리 — 바꾸면 기록에 이유를 적는다.  원본 19VA egg 는 컨테이너에 남지 않는다 (사용자가 다시 올린다).
- L88 기호 · 매크로 새 창 · L87 draw.io 벤치마킹은 기록(logic_log.md)에.
- 알림(toast)은 누르기를 통과시킨다 — 그림 위에 뜬 알림이 끌기를 가로채 시험이 드물게 엇나갔던 것 (L88).  새 알림을 그림 위에 띄우지 말 것.
- 사람 흐름 시험 다시 돌리기: `PW_CHROME=<chrome> python3 spike/ui_human_draw_l86.py <버릴 데이터 폴더> <캡처 폴더>` (또는 `pytest -q -m ui tests/test_logic_l86_human_draw.py`).
  씨앗이 필요 없다(빈 폴더 · `PID_DRAW_SEED=0`).  새 기능을 넣으면 여기에 단계를 더한다 — 사람이 하는 순서 그대로.
- 남은 차이 21행(7장)은 분석기 쪽: 열린 화살촉(두 획)이 선과 따로 놓여 선이 막대에 못 미친 그림 (19VA 0006 B11 · 0027 · 0015) —
  화살촉 획을 그 선 끝에 잇는 일.  원본은 사용자가 준 19VA egg (컨테이너엔 남지 않는다 — 다시 받아 `spike/diff_sim_l85.py` 로).
- 차등 시뮬레이션 다시 돌리기: 분석 job 을 만들고 `PID_DATA_DIR=<데이터> python3 spike/diff_sim_l85.py <job> - 8 out.json`
  (`-` = 그림을 분석 결과에서 바로 지어 견줌 · 저장 안 함).  누르기 흉내 `spike/sim_stress_l85.py` · 화면 `node spike/ui_sweep_l85.mjs`.
- 선 묶기 규율: 같은 분석 그물 안에서만 · 묶은 뒤 연결(선 단위 그물 + 시뮬레이터 꼴)이 다르면 그 그물은 묶지 않는다.  묶은 선은 `fx` (곧게 펴기에서 붙듦).
  씨앗을 다시 만들면 `python3 spike/compact_draw_seed.py config/logic_draw_seed/<씨앗>.json.gz` (판이 하나 오른다).
- 화면 자기검증: `PW_CHROME=<chrome> python3 spike/ui_audit_l84.py <버릴 데이터 사본> <캡처 폴더>` (지우기를 하므로 사본으로).
  이 컨테이너에서는 `PW_CHROME=/opt/pw-browsers/chromium` (기본 headless-shell 이 없어 꼭 준다).
- 기호 동작: 씨앗 827장 기호 8,550 중 못 읽은 것 294 (선 닿은 것 272) — 대부분 분석이 `UNKNOWN`·`?` 로 들인 기호 (원본 PDF 로 다시 읽어야 함).
- 그물 감사: `python spike/audit_l83_nets.py` (시드 827장).  남은 것은 분석 결과에서 두 분석 선이 같은 자리에 겹쳐 나온 것 — 분석기(`graph.py`) 쪽 일.
- 대시보드 하위 메뉴 "신호 처리 시뮬레이션"은 `docs/dashboard_embed.md` §3-3 프롬프트를 대시보드 세션에 줘야 선다.
- ⚠ 회차 번호 충돌: 옛 LOGIC 세션(`bold-einstein`, 은퇴)도 L70~L72 를 썼다.  옛 기록에서 같은 번호가 두 번 나오면
  날짜와 브랜치로 구분한다.  앞으로 번호는 지금 LOGIC 작업 브랜치 하나만 매긴다.
- **LOGIC 은 zip 을 만들지 않는다** — 커밋·푸시만 하면 PID 세션이 병합해 꾸러미에 싣는다 (`spike/pack_delta.py` 가 덜 합쳐졌으면 멈춘다).
- 시험 돌리기: `pip install -r requirements.txt pytest httpx` 뒤 `pytest -q -m "not slow and not ui"` (약 2분 · 1655 통과).

## 최근 회차 한 줄 요약 (자세한 것은 `docs/history/logic_log.md` · 옛것은 archive 를 grep)

| 회차 | 내용 |
| --- | --- |
| L91 | 매크로를 이 프로젝트에만 고치기 (사전 Typical → 묶음 사본 · 시뮬레이션 · 저장) · 사람 흐름 125가지 |
| L90 | 기호 · 매크로 창 두 번 누름 상세 — 기호 해 보기(작성 시뮬레이션) · 매크로 상세 · 고치기 |
| L89 | 분석→작도 정확도 95%↑ (827장 · 되읽기 블록 99.1 · 연결 96.0 · 선 96.3 · 글 96.7) · 원본 글 · NOTE 옮기기 · 접합 용접 · 씨앗 판 6 |
| L88 | 기호 · 매크로를 새 창으로 (누르고 놓기 · 이어 놓기 · 끌어 놓기) · 사람 흐름 110가지 |
| L87 | draw.io 벤치마킹 — 끌어 선 · ＋ 잇기 · 찾기 · 미니맵 · 메뉴 · 임시 저장 · 갈라진 선 따라오기 (사람 흐름 102가지) |
| L86 | 사람이 그리는 흐름 흉내 68가지 — 선 따라오기 · 매달린 끝 고리 · 장 더하기 · 단자 행 안 |
| L85 | 19VA 차등 시뮬레이션 — 들여오기 · 분석기 결함 (다른 출력 386 → 21) · 씨앗 판 4 · 들여오기 진행 표시 |
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
