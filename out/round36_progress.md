# 36회차 진행 기록 — `type_map` 재바인딩 · 승수 문지기 제거 · 유닛 표기 규칙 · 삭제 38

```
★ 목표선 AL NOUF1  fb85b039 · 1037 · Q'ty 1931 · 축1 99.3/70.5 · 축2 99.3/94.4 · 축3 95.1
                   양식 885/76/23 · Tag `.....` · REV 58/58 · 글리프 H4/M32 · 커넥터 218 · connector_reach 70.2
SADARA   82 · 0767ba79 · Q'ty 0 · 축3 75.4 · MULTIPLIER_UNDEFINED 82
TC2      607 · c0a2d29d · Q'ty 3047 · 축3 89.1 · MULTIPLIER_FROM_CONFIG 203
UAD      149 · db1a77d1 · Q'ty 149 · 축3 83.0 · MULTIPLIER_FROM_CONFIG 149
시험 270 · 합성 8
시작 HEAD 84d192d · 21:07
```

| 단계 | 상태 |
| --- | --- |
| [A] 기준선 4종 + 합성 8 | **완료** — AL NOUF1 은 84d192d 코드의 새 실행(21:17)이 기준선과 같음 · SADARA·TC2·UAD 는 35회차 끝 회귀(엔진 동일 커밋 · 19:41) 로 같음 → `8_regression_4p_start.json` "기준선과 같습니다".  ⚠ 첫 실행이 AL NOUF1 뒤에 멈췄다 — 하네스가 [B] 가 지운 `_V3_FIELD_TYPE_MAP` 을 읽고 있었다(고침).  자식 프로세스가 코드를 새로 import 하므로 그 뒤 세 프로젝트는 [B][C] 코드로 돈다 → [B][C] 게이트 실행으로 잇는다.  합성 8 은 [B][C] 회귀 뒤 |
| [B] type_map 재바인딩 | **완료** — 게이트 회귀 넷 일치(`8_regression_4p_BC.json`) · B-2 재판정: 25 전부 ㉣ (worktree 탐침이 `anchors.type_map.TT` 에서 멈춤) |
| [C] 문지기 제거 | **완료** — 넷 Q'ty 불변(1931·0·3047·149) · TC2 unit_notes 35 · FROM_CONFIG 203 그대로 |
| [D] 유닛 표기 규칙 | **D-1 실측 완료** (`out/round36/5_unit_token.md`) — 문서가 자기 코드 꼴을 말한다(AL NOUF1 `#DD` 25장 · TC2 `D-D` 18장) · 맨 숫자는 오검(문단 번호·날짜) → 배우지 않음 · 예측 TC2 3047→3167 · D-2 는 [E-2] 회귀 뒤 적용 |
| [E] 삭제 38 적용 | **E-1 dataclass 14 적용**(e615003 · 빠른 시험 270 · 탐침 199/`0087c236`) · 회귀 21:48~ · E-2 config 9 는 그 뒤.  ⚠ 38 중 14 는 적용 불가 — 폴백 13 을 SADARA·TC2·UAD 가 읽고(`6_delete.md`), `glyph_sizes` 는 낯선 경로에서만 ㉡ |
| [D-2] | **적용** (ec5fa21) — 빠른 시험 276 · 탐침 199/`0087c236`/398 · 배운 꼴 `#DD`(탐침 5장) · 회귀 F 22:39~ |
| [E-2] | **완료** (87e2705) — 회귀 넷 일치 (`8_regression_4p_E2.json`) |
| [F] 회귀 | **완료** 23:02 — AL NOUF1·SADARA·UAD 불변 · **TC2 `c0a2d29d`→`018315ef` · 3047→3167** (p33·p34 40행 x1→x4 · 폴백 203→163 · 예측과 같음) → `spike/baselines_3p.json` TC2 갱신 · 합성 8: ⑤ `2601598c` ⑦ `fdc5aa79` 같음 · ⑧b 완주 78행 · 순서 바꿔 돌리기 **통과** (SADARA→AL NOUF1 `fb85b039`→TC2 `018315ef`) |
| [G] 출력 | **완료** — 문서 0~7 · 로드맵 §5 · CLAUDE.md · `out/round36_result.zip`.  시작 21:07 → 마감 23:35 (2시간 28분) |
