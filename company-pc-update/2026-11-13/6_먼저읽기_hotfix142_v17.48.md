# 회사 PC 업데이트 — 2026-11-13 ⑥ 통합 hotfix142 + 대시보드 v17.48 (Area: DTS No. → QN · QS · W15)

| 파일 | 내용 | 크기 |
|---|---|---|
| `6_PID_dev+ops_hotfix142_2026-11-13.zip` | 통합 **hotfix142** = hotfix141 + Area 정하는 순서 · 이름 바꿈 · 파일 629 | 8.9 MB |
| `6_DASHBOARD_update_v17.48_from_v17.47_2026-11-13.zip` | 대시보드 **v17.48** — v17.47 이후 바뀐 파일 2개 (Area 순서 QN · QS · W15) | 1.3 MB |

**hotfix139 · 140 · 141 을 안 넣었어도 hotfix142 하나면 됩니다** (내용 포함). 대시보드는 v17.47 위에 넣습니다 (회사 v17.47 확인됨).

## 적용
1. **통합** — zip 을 전부 풀고 `apply_to_PID_dev.bat` → `apply_to_PID_ops.bat`. 화면 위 띠 `업데이트 142` · 서버 창에 `Restarting` 이 되풀이되지 않으면 정상.
2. **대시보드** — zip 을 풀고 Edge 의 대시보드를 닫는다 → `APPLY.bat` → `Y` → 다시 연다. 왼쪽 아래 `화면 v2026-11-13.2` (서버 파일은 안 바뀌어 `서버 v2026-11-13.1` 그대로가 정상).
3. 확인: Valve Summary · Instrument › By Area 의 Area 가 **QN · QN Brownfield N1 · N2 · QS · W15** 로 나옴. PDF 를 다시 올릴 필요 없음 (새로고침).
4. 다 되면 **"회사 PC 에 적용했다"** + 서버 창의 `[valve] stored PDF check … damaged` 줄 사진.

## 달라진 것 (141 → 142)
| 무엇 | 어떻게 |
|---|---|
| Area 정하는 순서 | ① **DTS No.** (98 → QN · 999 → QS · 315 → W15) → ② **Datasheet 제목의 Area** → ③ Tag 규칙 (규칙 표 → Instrument Index → 학습) |
| Area 이름 | QN 안의 Brownfield Tag 는 **QN Brownfield N1 · N2** 로 나눔 · QS · W15 에는 Brownfield 없음 · 예전 'North · South' 표기는 바뀜 |
| 이미 읽은 Datasheet | 보관 PDF 가 멀쩡하면 한 번 다시 채움 — 다시 올리지 않아도 됨 |
| 대시보드 | 계기 · 밸브 Area 표가 QN → QS → W15 순서 |

## 확인한 것
- 꾸러미 검사 통과 (시험 2,071 · 밸브 · 계기 시험 283 · 서버 주소 13곳 · 화면 점검) · Area 기본 규칙 표에 발주처 · 프로젝트 이름 없음
- 회사 상태별 적용: **141 · 140 · 139 · 138(지금 회사)** · 137 · 136 · 135 · 134 · 133 · 132 · 131 → 모두 최신과 다른 파일 0 · 회사 수정 파일은 백업 뒤 덮음 · 되돌리기 OK
- 대시보드 새 파일 2개 = 대시보드 브랜치 끝(`c7041153`) 과 바이트 단위로 같음 · 키 값 없음

## 회사에서 확인할 것
1. 실제 Datasheet 의 DTS No. · 제목으로 Area 가 맞게 나오는지 (틀리면 Tag · 문서 번호 사진을 보내 주세요).
