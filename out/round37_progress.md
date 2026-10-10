# 37회차 진행 기록 — 유도 구현 A 9 의 첫째: `formats.drawing_no`

36회차 마감 뒤 "계속 이어서" 지시로 시작 (23:35).  로드맵 §5 유도 구현 목록의 A 9 중 도면번호 형식.

| 단계 | 상태 |
| --- | --- |
| [A] 기준선 | 36회차 [F] 회귀(23:02)가 곧 기준선 — AL NOUF1 `fb85b039`·1037·1931 · SADARA `0767ba79`·82 · TC2 `018315ef`·607·3167 · UAD `db1a77d1`·149 |
| [B-1] 실측 | **완료** `spike/dwgno_survey.py` — 도면번호 칸의 낱말 모양: AL NOUF1 A4-A7-A3-D4 58/58 · SADARA 9/9 · **TC2 56 + A4-A6-A3-D4 4 (p25~28 `D02J-31PGB0-M05-000n`)** · UAD 25 + A4-A7-A3-D3 1 (p32).  칸 안에 도면번호 아닌 낱말 0 |
| [B-2] 구현 | **완료** (eaa8a2f) — `derive_layout._drawing_no_shapes/_drawing_no_pattern` · 두 장 이상 인쇄된 모양만 · `formats.drawing_no` 유도 항목 · `describe_equipment` 는 묶인 `tb.DWG_NO_RE` 를 읽는다 · 시험 276 → 281 · 탐침 199/`0087c236`/398 (자기 프로필 → 얹지 않음) |
| [C] 회귀 | **완료** 00:01 — 예측 그대로: TC2 607→684 · 60/60 · Q'ty 3783 · 축3 90.4 · 나머지 셋 지문 불변 (축3 분모만) → 기준선 갱신 (`out/round37_regression_4p.json` · `out/round37_report.md`) |

## [C] 창 상수 셋 — 실측 (00:05~)

- `spike/window_survey.py` → `out/round37_window_survey.json` (네 문서 · 캡 긴 변 · 선분 길이 · 타이틀블록 픽셀).
- 범례 장이 계기 버블을 그린다 — 비율 창 안 캡의 최빈 크기가 네 문서 전부 한 값 (AL NOUF1 22.62×11.31 ×202 · SADARA 33.55×16.78 ×196 · TC2 11.40×5.70 ×212 · UAD 11.34×5.67 ×212).
- 본문 버블 짧은 변 / 범례 캡 긴 변 = 0.67~1.26 (AL NOUF1 15.1~28.4 · SADARA 25.5~34.1 · TC2 9.9~14.3 · UAD 11.3~12.6).  바로 아래 0.62~0.63 에 공압 돔(범례 14.22 · 7.08 · 7.02)이 있다 → 크기에 빈 띠가 없다.
- 실험: `/tmp/r37_win` worktree 에서 `cap_span=(0,∞)` · `seg_span=(0,∞)` 로 네 프로젝트 회귀 (00:15 시작 · 자식 프로세스 확인).  지문이 넷 다 불변이면 두 창은 판정이 아니라 성능 필터다.
- 00:35 둘 다 해제 회귀 끝 — AL NOUF1 `fb85b039` 불변 · SADARA 불변 · **TC2 685 · UAD 150** (새 행 둘은 높이 2pt 선 = 몸체 검출기 결함 · `seg_span` 상한이 가리고 있었다) · 미판정 VALVE_BODY 만 움직임.  `out/round37_windows.md` §3.
- 00:37 `cap_span` 만 해제 회귀 시작 (`/tmp/r37_win` · `out/r37cap.log`).
- 사용자 요청(중간): `report.md` + 회사 PC 꾸러미 r37 — `report.md` 작성 · `spike/pack_handover_r37.py` · `out/PID_update_2026-09-13_r37.zip` 생성 · aac64ba worktree 에 풀어 HEAD 와 소스 대조 0 · 빠른 시험에서 `test_both_legends_yield_the_same_isa_letters` 가 PDF 없는 PC 에서 실패 → skip 보호 추가 (281 통과 유지).  최종 커밋 뒤 다시 꾸린다.
- 00:59 `cap_span` 만 해제 회귀 끝 — **넷 다 기준선과 같다** (시간 TC2 +17초 · UAD +15초 · RSS 같음).  → `cap_span` 삭제 적용 (`c0882fb` · 시험 283).  `seg_span` 유지(결함 목록) · `zoom` 조사 목록.
- 01:01 본선 끝 회귀 시작 (`out/round37_final.log`).  문서 갱신: `out/round37_windows.md` §4·§7 · `report.md` §5 · 로드맵 §5 · CLAUDE.md.
- 01:23 본선 끝 회귀 — 넷 다 기준선과 같다 (`out/round37_regression_4p_final.json`).  대기 셸은 도구 600초 상한으로 두 번 끊겼고 회귀 자체는 완주했다.
