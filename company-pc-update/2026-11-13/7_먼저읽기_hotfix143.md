# 회사 PC 업데이트 — 2026-11-13 ⑦ 통합 hotfix143 (도서 Area 지정 · North 를 South 로 읽던 것 고침)

| 파일 | 내용 | 크기 |
|---|---|---|
| `7_PID_dev+ops_hotfix143_2026-11-13.zip` | 통합 **hotfix143** = hotfix142 + 도서 Area 지정 · South 오판 고침 · 'QN Greenfield' · 파일 629 | 8.9 MB |
| (대시보드) `6_DASHBOARD_update_v17.48_from_v17.47_2026-11-13.zip` | 대시보드는 **v17.48** 그대로 (⑥ 에서 보낸 것) | 1.3 MB |

**hotfix139 ~ 142 를 안 넣었어도 hotfix143 하나면 됩니다** (내용 포함). hotfix142 는 넣지 않아도 됩니다.

## 적용
1. **통합** — zip 을 전부 풀고 `apply_to_PID_dev.bat` → `apply_to_PID_ops.bat`. 화면 위 띠 `업데이트 143` · 서버 창에 `Restarting` 이 되풀이되지 않으면 정상.
2. **대시보드** — 아직이면 ⑥ 의 v17.48 zip: Edge 대시보드 닫기 → `APPLY.bat` → `Y` → 다시 열기 (왼쪽 아래 `화면 v2026-11-13.2`).
3. 확인:
   - 서버 창에 `[valve] stored PDF check: n good · m damaged` 줄 (사진으로 보내 주세요)
   - 공통 자료 › **Area 규칙 표** (기본값 들어 있음)
   - Document Management › **'이 도서의 Area'** (문서에서 읽기 / North · South · W15) — 이미 올린 도서도 표에서 바꿀 수 있음 · 다시 올리지 않아도 됨
   - Area 값: **QN Greenfield · QN Brownfield N1 · N2 · QS · W15**
4. 다 되면 **"회사 PC 에 적용했다"**

## 달라진 것 (142 → 143)
| 무엇 | 어떻게 |
|---|---|
| 도서 Area 지정 | 올릴 때 고르거나 올린 뒤 표에서 바꿈 → 그 도서의 모든 Tag 에 먼저 씀 |
| Area 정하는 순서 | **올린 도서 Area** → DTS No. (98 QN · 999 QS · 315 W15) → Datasheet 제목 → 규칙 표 |
| North 를 넣어도 South 로 읽음 | 원인: Loop 번호 앞 두 자리로 짐작한 값이 North · South 를 정했음 → 이제 짐작값은 North · South 를 정하지 않음 |
| 이름 | Brownfield 규칙 Tag = QN Brownfield N1 · N2, 나머지 North = **QN Greenfield** · South(QS) · W15 에는 Brownfield 없음 |

## 확인한 것
- 꾸러미 검사 통과 (시험 2,071 · 서버 주소 13곳 · 화면 점검) · 밸브 · 계기 시험 263 통과 (여러 스레드가 동시에 DB 를 처음 쓰는 시험 하나가 가끔 'database is locked' — 예전부터 있던 시간 문제, 다시 돌리면 통과)
- 6 세션 확인: 전체 시험 2,096 · Valve 판정 2,935 변화 0 · 화면 자체점검 25/25
- 회사 상태별 적용: **142 · 141 · 140 · 139 · 138(지금 회사)** · 137 · 136 · 135 · 134 · 133 · 132 · 131 → 모두 최신과 다른 파일 0 · 되돌리기 OK

## 알아 둘 것
- 대시보드 v17.48 은 'QN Greenfield' 를 W15 뒤에 놓습니다 (값은 맞게 나옴 · 순서만). 다음 대시보드 판에서 맨 앞으로 옮깁니다.
