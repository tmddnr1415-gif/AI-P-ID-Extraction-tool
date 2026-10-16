# 31회차 진행 기록 — 승수를 사람이 한 번 지정하는 길 (3급 경로)

```
★ 목표선 AL NOUF1  fb85b039 · 1037 · Q'ty 1931 · 축1 99.3/70.5 · 축2 99.3/94.4
                   축3 95.1 · 양식 885/76/23 · Tag `.....` · REV 58/58 · 글리프 H4/M32
SADARA   82 · 0767ba79 · 축3 75.4 · MULTIPLIER_UNDEFINED 82
TC2      607 · c0a2d29d · Q'ty 3047 · 축3 89.1 · MULTIPLIER_FROM_CONFIG 203
UAD      149 · db1a77d1 · Q'ty 149 · 축3 83.0 · MULTIPLIER_FROM_CONFIG 149
```

| 단계 | 상태 |
| --- | --- |
| [A] 기준선 4종 | **완료** — 넷 전부 재현 |
| [A] 승수 대상 행 | **완료** — AL NOUF1 **0** · SADARA 82(유닛 `10` 하나) · TC2 203(`00`) · UAD 149(`00`) (`out/round31/4_승수_대상행.md`) |
| [B-0] 기존 구조 조사 | **완료** — 둘 다 그대로는 못 쓴다.  자리는 `axis_overrides`, 규율은 전역 심볼 사전에서 반쪽씩 (`3_기존구조_조사.md`) |
| [B] 지정 경로 | **완료** — `app/unit_multipliers.py` · `_note_factor(user=)` · API 셋 · 검토 화면 패널 |
| [B-4] 게이트 | **완료** — 4단계 전부 통과 (`gate_*.json`).  ★ AL NOUF1 에 전 유닛 `x9` 를 넣고도 움직인 칸 0 |
| [C] 경보 접미 | **완료(측정만)** — AL NOUF1 위험 2건이 **사람이 쓴 검토 메모**였다 (`5_alarm_suffix.md`) |
| [D] 회귀 | **완료** — 네 프로젝트 전부 기준선과 같음 (`9_전수대조.txt`) · 빠른 시험 **266** · **UI 24** · 실 DB sha256 불변 |
| [E] 출력 | **완료** — `out/round31_result.zip` · `docs/program_overview.md` 신규 · `docs/state_and_roadmap.md` 갱신 |
| [F] UI 자기검증 | **완료** — 띄워서 눌러 결함 **넷** (`out/round31/8_UI검증/README.md`) · 시험 4건 추가 |
