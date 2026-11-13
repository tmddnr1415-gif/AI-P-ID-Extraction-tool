# 회사 PC 업데이트 — 2026-11-13 ④ 통합 hotfix140 (서버 재시작 고침 + Datasheet JSON · Area 규칙 · 다시 올리지 않아도 됨)

| 파일 | 내용 | 크기 |
|---|---|---|
| `4_PID_dev+ops_hotfix140_2026-11-13.zip` | 통합 **hotfix140** = hotfix138 + **139(서버 재시작 반복 고침)** + JSON 저장 · Area 규칙 · 깨진 PDF 를 쪽 그림으로 · 파일 628 | 8.9 MB |

**hotfix139 대신 이것 하나**만 넣으면 됩니다 (139 내용 포함). 대시보드는 **v17.47 그대로**.

## 적용
1. zip 을 전부 풀고 `apply_to_PID_dev.bat` → `apply_to_PID_ops.bat` — 회사가 hotfix138 이든, 136 으로 되돌렸든, 139 든 140 이 됨.
2. 서버 창에 `Restarting in 10 seconds` 가 되풀이되지 않으면 정상 · 화면 위 띠 `업데이트 140`.
3. 서버 창의 `[valve] stored PDF check: … damaged` 와 '손상 저장본 … 앞 32바이트' 줄을 **사진으로 보내 주세요** (보안 프로그램 여부 확인).
4. **Area**: Valve 화면 Dashboard › By Area 의 **[규칙 표 넣기]** 에 Brownfield 구역 표를 한 번 붙여 넣기 → Valve Summary 의 '(not stated)' 가 채워짐 (한 번 넣으면 Ball · Globe · Butterfly · PSV · Instrument 공통).

## 달라진 것
| 무엇 | 어떻게 |
|---|---|
| 서버가 켜졌다 꺼짐 (hotfix138) | 깨진 보관 PDF 를 어디서도 열지 않음 → 서버 유지. 혹시 죽으면 `<자료폴더>\valve\logs\crash_날짜.log` · `warmup.log` · 비상 스위치 `VALVE_WARMUP=0` |
| **이전에 올린 PDF 를 다시 올려야 하나?** | **아니요.** 값 · 검토 · 현황판은 DB · JSON 으로 돌아 새로고침하면 그대로 · 깨진 PDF 는 **예전에 그려 둔 쪽 그림으로 보여 줌** ('그림으로 보는 중'). 그림이 남지 않은 쪽만 '원본 손상' — 그 문서만 골라 다시 올리면 됨 |
| **Datasheet JSON 저장** | `<자료폴더>\valve\datasheets\<프로젝트>\<종류>\<Tag>__<Rev>.json` (칸 값 · 단위 · 쪽 · 위치 · 상태 · 검토자 수정 · Notes · Rev 표 · 원본 이름 · 올린 사람/때) + `_documents\` 문서별 묶음. 올릴 때 · 다시 읽을 때 쓰고, **서버를 켤 때 이미 들어 있는 Datasheet 도 빠진 것만 씀** |
| **Area 규칙** | Valve Summary · By Area · Issue 목록 · Excel · Valve List · 특수요구사항 표에 규칙 표 → Instrument Index AREA → Tag 앞 번호 순으로 Area · Sub-area · 출처 표시 |

## 확인한 것
- 꾸러미 검사 통과 (시험 2,071 · 밸브 · 계기 시험 280)
- 회사 상태별 적용: **139 · 138(지금) · 137 · 136(되돌린 경우)** · 135 · 134 · 133 · 132 · 131 → 모두 최신과 다른 파일 0 · 되돌리기 OK
- 살아 있는 서버로: 쪽 그림을 한 번 그린 뒤 보관 PDF 를 보안 프로그램처럼 깨뜨리고 서버를 다시 켬 → **서버 유지 · '1 damaged (not opened)' · PDF 쪽 정보 · 쪽 그림 200(그림으로 보임) · 값 화면 200 · JSON 파일 자동 생성**(`P\ball\00XV_921__A.json` · `_documents\1__Datasheet2.json`)
- 15개 깨진 보관본으로 서버 유지 (hotfix139 시험)
