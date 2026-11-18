# 회사 PC 업데이트 — 2026-11-18 ② 통합 hotfix144 (South 도서 읽기 · 읽지 못한 쪽 알림)

| 파일 | 내용 | 크기 |
|---|---|---|
| `2_PID_dev+ops_hotfix144_2026-11-18.zip` | 통합 **hotfix144** = hotfix143 + Valve · Instrument valve41 · 파일 631 | 8.9 MB |
| (대시보드) `1_DASHBOARD_update_v17.64_from_v17.47_2026-11-18.zip` | 대시보드 **v17.64** (오늘 ①) | 1.4 MB |

**hotfix139 ~ 143 을 안 넣었어도 hotfix144 하나면 됩니다** (내용 포함).

## 적용
1. zip 을 전부 풀고 `apply_to_PID_dev.bat` → `apply_to_PID_ops.bat`. 화면 위 띠 `업데이트 144` · 서버 창에 `Restarting` 이 되풀이되지 않으면 정상.
   - 처음 켤 때 South 도서를 새 방식으로 한 번 다시 읽느라 조금 걸릴 수 있음 (다시 올리지 않아도 됨)
2. 대시보드 v17.64 (오늘 ①) 도 아직이면 함께.
3. 확인:
   - Globe Valve 등에 올린 **South Control Valve · Regulator 도서**에서 Tag 가 나오는지
   - Document Management 에 **'✓ INDEX n Tag 모두 읽음'** 또는 빨간 **'일부 못 읽음'** 표시
   - Area 에 'South' 와 'QS' 가 따로 나오지 않는지
4. 다 되면 **"회사 PC 에 적용했다"** — '일부 못 읽음' 이 나온 도서가 있으면 그 화면 사진을.

## 달라진 것 (143 → 144)
| 무엇 | 어떻게 |
|---|---|
| South 도서를 못 읽음 | South Control Valve(40쪽) · Regulator 도서는 처음 보는 'INSTRUMENT SPECIFICATION' 양식이라 Tag 없는 Datasheet 1개로 잡혔음 → 이 양식을 읽게 함 (6 세션: 첨부 2권 = Tag 19개 · Tag 마다 120여 칸) |
| 이미 올린 도서 | 서버를 켤 때 Tag 없이 남은 도서를 한 번 다시 읽음 · 옛 읽기 잔재 정리 |
| 모르는 양식이 조용히 '완료' 로 끝나던 것 (모든 타입) | 읽지 못한 쪽 표시 · 도서 앞 INDEX (LIST OF TAGS) 와 읽은 Tag 대조 → 빨간 '일부 못 읽음' / '✓ INDEX n Tag 모두 읽음' |
| Area 'South' · 'QS' 따로 | 하나로 |
| PURCHASE 칸 TBC | Open Item 아님 |
| 처음 켤 때 가끔 'database is locked' | 고침 |

## 확인한 것
- 꾸러미 검사 통과 (시험 2,071 · 밸브 · 계기 시험 288 · 서버 주소 13곳 · 화면 점검) · 새 파일 `form_isa.py` 들어 있음
- 6 세션 확인: 전체 시험 2,100 · Valve 판정 2,935 변화 0 · 실 Ball 456쪽 읽기 결과 예전과 같음 · INDEX 대조 Ball 164/164 · South 15/15 · 4/4
- 회사 상태별 적용: **143 · 142 · 141 · 140 · 139 · 138(회사 확인 판)** · 137 · 136 · 135 · 134 · 133 · 132 · 131 → 모두 최신과 다른 파일 0 · 되돌리기 OK
- 시험은 프로그램이 만든 시험 PDF 로 함 — 회사 원본 PDF 는 저장소에 없음
