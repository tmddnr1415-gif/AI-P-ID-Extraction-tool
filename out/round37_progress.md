# 37회차 진행 기록 — 유도 구현 A 9 의 첫째: `formats.drawing_no`

36회차 마감 뒤 "계속 이어서" 지시로 시작 (23:35).  로드맵 §5 유도 구현 목록의 A 9 중 도면번호 형식.

| 단계 | 상태 |
| --- | --- |
| [A] 기준선 | 36회차 [F] 회귀(23:02)가 곧 기준선 — AL NOUF1 `fb85b039`·1037·1931 · SADARA `0767ba79`·82 · TC2 `018315ef`·607·3167 · UAD `db1a77d1`·149 |
| [B-1] 실측 | **완료** `spike/dwgno_survey.py` — 도면번호 칸의 낱말 모양: AL NOUF1 A4-A7-A3-D4 58/58 · SADARA 9/9 · **TC2 56 + A4-A6-A3-D4 4 (p25~28 `D02J-31PGB0-M05-000n`)** · UAD 25 + A4-A7-A3-D3 1 (p32).  칸 안에 도면번호 아닌 낱말 0 |
| [B-2] 구현 | **완료** (eaa8a2f) — `derive_layout._drawing_no_shapes/_drawing_no_pattern` · 두 장 이상 인쇄된 모양만 · `formats.drawing_no` 유도 항목 · `describe_equipment` 는 묶인 `tb.DWG_NO_RE` 를 읽는다 · 시험 276 → 281 · 탐침 199/`0087c236`/398 (자기 프로필 → 얹지 않음) |
| [C] 회귀 | **완료** 00:01 — 예측 그대로: TC2 607→684 · 60/60 · Q'ty 3783 · 축3 90.4 · 나머지 셋 지문 불변 (축3 분모만) → 기준선 갱신 (`out/round37_regression_4p.json` · `out/round37_report.md`) |
