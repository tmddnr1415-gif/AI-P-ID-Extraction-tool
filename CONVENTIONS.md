# 세션 공통 규약 (오케스트레이터 Phase 1)

> 적용 대상: S1~S7 모든 작업 세션 · 작성: 오케스트레이터 세션 · 2026-11-07
> 기획 원문: [`ORCHESTRATION_PLAN.md`](ORCHESTRATION_PLAN.md)

## 1. 역할 분담

- **각 세션**: 자기 업무의 기능 개발 · 테스트 · 자기 배포물(zip) 제작
- **오케스트레이터**: 7개 배포물을 모아 **회사 PC 통합 업데이트 파일 한 개**로 묶음
- 각 세션은 회사 PC 에 바로 전달하는 최종 통합본을 만들지 않는다. 자기 배포물만 아래 자리에 둔다.

## 2. 회사 PC 제약 (모든 세션 공통 · 1. DASHBOARD 의 `DASHBOARD_ARCHITECTURE.md` 기준)

| 항목 | 제약 |
|---|---|
| OS / 브라우저 | Windows · Edge (file:// 실행 포함) |
| Python | 3.11 **표준 라이브러리만** (pip 설치 불가) |
| 외부 의존성 | CDN · npm · 외부 서비스 전송 **금지** — 라이브러리는 파일 안에 포함 |
| Node.js | 회사 PC 에 없음 |
| 데이터 | 사내 기밀 — 외부 전송 금지 |
| API 키 | 배포물에 넣지 않는다 |
| 연결 | 별도 프로그램은 DASHBOARD 의 `apps\` 폴더에 넣어 메뉴로 연결 |

## 3. 배포물 자리 — `dist/company_pc/<SID>/`

각 세션은 **자기 브랜치**의 아래 경로에 현재 회사 PC 배포물을 둔다.

```
dist/company_pc/<SID>/          SID = S1 … S7
├── MANIFEST.json               아래 4장 양식
├── STATUS.md                   진행 현황 · 사람 검토 필요 항목
└── <배포 zip 1개>              기존에 쓰던 이름 그대로 (예: UPDATE_from_v16.57_to_v16.58.zip)
```

- zip 은 기존 관행(`APPLY.bat` + `base/` + `new/`, 또는 FULL 꾸러미)을 그대로 쓴다.
- zip 이 50MB 를 넘으면 zip 대신 MANIFEST 의 `artifact.path` 에 저장소 안 실제 경로만 적는다.
- 회사 PC 기준점은 기존 `delivered.txt` 를 그대로 쓴다. 오케스트레이터가 통합본을 전달한 뒤에 각 세션이 맨 아래 줄을 추가한다.

## 4. `MANIFEST.json` 양식

```json
{
  "sid": "S2",
  "session": "2. PID 검토 4 (NEW)",
  "branch": "claude/gracious-ride-26nqrf",
  "commit": "<배포물을 만든 커밋 해시>",
  "version": "hotfix132",
  "date": "2026-11-07",
  "artifact": { "path": "dist/company_pc/S2/PID_dev+ops_hotfix132_2026-11-05.zip", "bytes": 0, "sha256": "" },
  "kind": "update | full",
  "base_version": "회사 PC 에 이미 있는 버전 (update 일 때)",
  "install_to": "회사 PC 의 설치 위치 (예: C:\\Claude\\계장ENG그룹 주간업무 Dashboard\\apps\\pid)",
  "entry": "실행 방법 (예: dashboard 메뉴 'P&ID' · 또는 start.bat 더블클릭)",
  "apply": "적용 방법 (예: zip 풀고 APPLY.bat 실행)",
  "depends_on": ["S1:v16.58"],
  "overlaps_with": ["다른 세션과 같은 파일을 건드리면 그 세션 SID와 파일"],
  "tests": "실행한 검사와 결과 (예: 1,989 tests pass)",
  "human_review_needed": ["사람이 꼭 확인해야 할 것"],
  "changes": ["회사 PC 사용자에게 보일 변경점 3~7줄"]
}
```

## 5. 진행 현황 `STATUS.md`

```
# <SID> <세션 이름> — 상태
- 상태: 진행 중 | 배포물 준비 완료 | 막힘
- 마지막 갱신: YYYY-MM-DD HH:MM
- 막힌 이유 / 필요한 결정:
- 사람 검토 필요:
```

## 6. 오케스트레이터 통합 절차

1. 각 세션 브랜치에서 `dist/company_pc/<SID>/MANIFEST.json` 수집
2. `sha256` · `depends_on` · `overlaps_with` 확인 — 겹치는 파일이 있으면 해당 세션에 조정 요청
3. `company-pc-update/YYYYMMDD/` 에 7개 zip + `APPLY_ALL.bat` + `UPDATE_GUIDE.md` + `MANIFEST.json`(통합) 생성
4. 사용자 승인 후 회사 PC 전달 → 각 세션 `delivered.txt` 갱신 요청

## 7. 안전 문서 원칙

P&ID · Logic · Datasheet · 도서 검토 결과는 플랜트 설계 안전 문서다.
자동 판독 결과는 **사람 검토 전에는 확정본이 아니다.** 각 세션은 `human_review_needed` 를 비워 두지 않는다.
