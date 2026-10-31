# CLAUDE.md — 짧게 유지합니다 (상한 12KB · 시험이 강제)

이 파일은 **모든 요청마다 통째로** 모델에 실립니다.  2026-10-30 까지 회차 기록을 여기에
계속 덧붙여 약 960KB 가 됐고, 그 결과 세션마다 **"Prompt is too long"** 으로 멈췄습니다.
그래서 이 파일에는 **어디를 읽을지와 지킬 규칙만** 둡니다.

## 0. 세션 시작 — 자기 세션의 인수인계 한 장만 읽는다

| 세션 이름 (앱 목록) | 작업 브랜치 | 먼저 읽을 것 |
| --- | --- | --- |
| `2. PID 검토 …` | `docs/handoff/branches.md` 참고 | `docs/handoff/pid.md` |
| `3. Logic 검토코드 …` | 〃 | `docs/handoff/logic.md` |
| VALVE Datasheet 검토 (실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve) | `ccr-efbe7e75-n915ze` | `docs/handoff/valve.md` |
| 그 밖 (DASHBOARD · PANEL · 시연 영상 …) | 〃 | `docs/handoff/branches.md` · `dashboard/` 규칙은 `docs/handoff/dashboard_rules.md` |

- 브랜치 지도(어느 세션이 어느 브랜치인지 · 옛 브랜치)는 **`docs/handoff/branches.md` 하나**에 있습니다.
- P&ID 엔진의 원칙·불변식·로드맵은 `docs/state_and_roadmap.md` (57KB — **목차를 보고 필요한 절만** 읽기).
- 옛 회차 기록 전부: `docs/history/CLAUDE_archive_pid_2026-10-30.md` (약 1MB) ·
  `docs/history/CLAUDE_archive_logic_2026-10-30.md`.  **통째로 Read 하지 말고 `grep -n` 으로 찾아 그 부분만** 읽습니다.

## 1. 기록은 어디에 쓰나 — ★ 이 파일에 회차 기록을 쓰지 않는다

- 회차·hotfix 를 마치면 **자기 세션의 기록 파일 끝에** 5~15줄로 적습니다:
  P&ID → `docs/history/pid_log.md` · LOGIC → `docs/history/logic_log.md` · 그 밖 → `docs/history/other_log.md`.
- 그리고 **자기 인수인계 파일(`docs/handoff/<세션>.md`)의 "지금 상태" 절을 고쳐 씁니다** (덧붙이지 말고 바꿔 씁니다 · 상한 15KB).
  새 세션은 그 한 장만 읽고 이어 갈 수 있어야 합니다.
- 이 `CLAUDE.md` 는 규칙이 바뀔 때만 고칩니다.  `tests/test_context_budget.py` 가 크기를 지킵니다.

## 2. 대화 기록 한도를 아끼는 규칙 (세션이 멈추지 않게)

1. **큰 파일을 통째로 Read 하지 않습니다.**  `out/` 의 json·zip·db, `*.min.js`, `standalone.html`,
   `app/static/*.js`(수천 줄)는 `grep -n` · `sed -n 'A,Bp'` · `jq` · `python -c` 로 **필요한 부분만** 봅니다.
2. **명령 출력은 짧게** — `| tail -20`, `| head -40`, `-q`, `--stat`.  시험은 `pytest -q` 로 돌리고 실패만 봅니다.
3. **이미지·캡처는 꼭 볼 때만** Read 합니다 (한 장이 수천 토큰).
4. 회차가 길어지면(꾸러미 2~3개를 냈거나 대화가 아주 길면) **인수인계 파일을 갱신하고 새 세션으로 넘기라고 사용자에게 말합니다.**
5. 사용자 보고는 계장 엔지니어(개발 비전공)가 읽습니다 — "무엇이 달라졌나 · 어디서 보나 · 무엇을 더 해야 하나" 만, 쉬운 말로.

## 3. 업데이트 꾸러미(zip) 규칙

- **P&ID · LOGIC · 판넬 공간확보 · 도서검토** 의 `PID_dev+ops_hotfixNNN` zip 은 **PID 브랜치**에서만 만듭니다.
  대시보드 본체·광장 zip 은 대시보드 쪽에서 만듭니다.
- 만들기 전에 **다른 세션의 최신 브랜치를 병합**합니다.  `spike/pack_delta.py` 가 `config/release_sources.json`
  에 적힌 브랜치를 확인하고 **덜 합쳐졌으면 멈춥니다** (hotfix127 이 새 LOGIC 변경을 빠뜨린 일 때문).
  세션을 새로 열어 브랜치가 바뀌면 **`config/release_sources.json` 과 `docs/handoff/branches.md` 를 같이** 고칩니다.
- 만드는 법·적용 순서는 `docs/handoff/pid.md` §꾸러미.

## 4. 진행 원칙 (요약 — 근거는 `docs/state_and_roadmap.md` §3·§9)

1. 판정 값은 그 도면의 범례·도면에서 런타임에 잽니다.  코드에 치수·임의값을 박지 않습니다.
2. 도면에 없는 값은 만들지 않습니다 — 비우고 사유를 남깁니다.
3. 검출에 LLM 을 쓰지 않습니다.  측정 정의(분모·대조 집합)를 바꿔 수치를 좋게 만들지 않습니다.
4. 회귀 기준선(`spike/baselines_3p.json`)이 움직이면 원인을 칸 단위로 밝힙니다.
5. **없는 것을 만들기 전에 있는 것을 찾습니다** (이 저장소에서 스무 번 넘게 반복된 교훈).
