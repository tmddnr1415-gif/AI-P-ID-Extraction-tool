# 브랜치 지도 — 어느 세션이 어느 브랜치인가 (2026-10-30 기준)

세션을 새로 열면 작업 브랜치 이름이 바뀝니다.  **바뀌면 이 표와 `config/release_sources.json` 을 같이 고칩니다.**

| 세션 (앱 목록) | 지금 작업 브랜치 | 상태 |
| --- | --- | --- |
| 2. PID 검토 4 (NEW) | `claude/gracious-ride-26nqrf` | 사용 중 · hotfix 꾸러미를 만드는 곳 (hotfix129 부터) |
| 3. Logic 검토코드 4 (NEW) | `ccr-cc45909d-fjjmrb` | 사용 중 · L85 까지 · 다음 L86 |
| 4. PANEL 코드 (NEW) | `ccr-d82d97fa-bb3ty3` (`dashboard/apps/space`) | 판넬 화면 원본 · 0943667 까지 PID 에 옮겨 옴 (hotfix131) |
| 1. DASHBOARD 코드 (NEW) | `ccr-248a5c4d-3dji7g` | 대시보드 본체 zip 은 여기서 |
| 프로그램 시연 영상 | `ccr-ee7fd745-5z06vs` | |

## 은퇴한 브랜치 — 여기서 병합하지 않는다

| 브랜치 | 무엇이었나 |
| --- | --- |
| `ccr-2d6327d0-21i1fr` | "2. PID 검토 3 (NEW)" — hotfix125~128.  대화가 한도를 넘어 멈춤(/compact 실패) → 2026-10-30 위 브랜치로 이관 |
| `claude/logic-symbol-visualization-sim-2oqbxh` | "3. Logic 검토코드 3" — LOGIC (L70~L82) — 전부 `ccr-cc45909d-fjjmrb` 에 들어 있음 |
| `claude/bold-einstein-8uibbv` | 옛 LOGIC 세션 (OLD) — L70~L72 를 **새 LOGIC 과 같은 번호로** 따로 매겼다. hotfix127 이 이것만 합쳐 새 LOGIC 변경이 빠졌다. 내용은 PID 브랜치에 전부 들어 있음 |
| `claude/logic-review-design-pd2z75` | 더 옛 LOGIC |
| `claude/pid-extractor-panel-update-nbcrfn` · `…-zrl4qi` · `claude/titleblock-parsing-c5st4x` | 옛 PID (hotfix121~125) |

## 왜 이 표가 필요한가

같은 일을 하는 세션이 OLD/NEW 로 둘 이상 생기면, 꾸러미를 만드는 쪽이 **옛 브랜치를 최신으로 알고** 병합합니다.
hotfix127 이 그랬습니다 (`bold-einstein` L72 만 합침 → 새 LOGIC L73~L78 누락 → hotfix128 에서 바로잡음).
OLD 세션을 닫을 때 이 표의 "은퇴" 칸으로 옮겨 적으세요.
