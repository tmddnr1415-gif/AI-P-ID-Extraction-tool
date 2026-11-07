# 오케스트레이션 진행 현황 — 2026-11-07

> 기획: [`ORCHESTRATION_PLAN.md`](ORCHESTRATION_PLAN.md) · 규약: [`CONVENTIONS.md`](CONVENTIONS.md) · 시연: [`company-pc-update/DEMO_company_pc.html`](company-pc-update/DEMO_company_pc.html)

## 단계

| Phase | 상태 | 내용 |
|---|---|---|
| 0 확인 | 완료 | 7개 세션 모두 존재 · 같은 저장소 · 세션별 브랜치 (기획안 3.1절) |
| 1 규약 | 완료 | `CONVENTIONS.md` — `dist/company_pc/<SID>/` · MANIFEST 양식 |
| 2 지시 | 완료 | 7개 세션에 "기능 변경 없이 배포물 정리" 전달 |
| 3 점검 | 진행 | 아래 표 · 각 브랜치 전수 검토 (세션별 검토 Agent 7개) |
| 4 통합 | 진행 | 시연 HTML 완료 · 통합 zip 은 아래 "결정 필요" 뒤 |

## 세션 응답과 실제 배포물

| SID | 세션 응답 | 회사 PC 배포물 (실제) | 이번 반영 |
|---|---|---|---|
| S1 | `dist/company_pc/S1/` 푸시 (5f2de9b) | `UPDATE_from_v16.57_to_v16.58.zip` 714,059 B | 반영 |
| S2 | 응답 없음 · dist 없음 | `out/PID_dev+ops_hotfix132_2026-11-05.zip` 7,237,795 B (491 파일) | 반영 |
| S3 | 세션 규칙(CLAUDE.md §3: LOGIC 은 zip 을 만들지 않음)으로 보류 — 오케스트레이터가 수용 | S2 꾸러미에 포함. **hotfix132 에는 L86 까지, L87–L91 7개 커밋 빠짐** | 일부 |
| S4 | 응답 없음 · dist 없음 | 없음. 최신 판넬 공간확보(Phase 1/2 · 3D 사람)는 브랜치에만 | 미반영 |
| S5 | `dist/company_pc/S5/` 푸시 (a6550c6) | `BOOKS_full_2026-10-24.1_2026-11-07.zip` 568,477 B · sha256 b6034228… | 준비 · 연결 필요 |
| S6 | 사용자 승인 없이 커밋 안 함 — 조사 결과만 회신 · 오케스트레이터가 수용 | `out/PID_dev+ops_valve35_2026-11-07.zip` 424,919 B | 반영 (hotfix132 다음) |
| S7 | 응답 없음 · dist 없음 | `IC_Dashboard.zip` 은 브랜치에 없음 (app/index.html 은 있음) | 별도 실행 |

## 통합하며 찾은 문제

1. **LOGIC 누락** — S3 브랜치 L91 중 L87–L91 이 PID 꾸러미(hotfix132)에 없음.
2. **판넬 공간확보 두 갈래** — DASHBOARD v16.58 메뉴 "ROOM SIZE 계산"은 PID 서버 `/space`(Phase 2 없음)를 띄움. S4 최신판은 `dashboard/apps/space` 에 있고 회사로 안 나감.
3. **도서검토 두 갈래** — 메뉴는 PID 서버 `/books/` 를 띄움. S5 꾸러미는 `apps/books` + `books_api.py` 로 가고 DASHBOARD 2곳 연결 필요(INTEGRATION.md 2장).
4. **Valve 순서** — valve35 와 hotfix132 는 형제. hotfix132 → valve35 순서 필수, `app/main.py` 기준판 불일치 사람 확인.
5. **3D 오프라인** — S7 실물 3D 가 cdnjs 에서 three.js 를 받음. 이 세션에서 실제로 띄워 보니 "three.js could not be loaded" — 회사망에서도 같음. Claude 답변 엔진은 api.anthropic.com 직접 호출(기본 꺼짐).
6. S2·S3·S4·S6·S7 은 `dist/company_pc/` 를 만들지 않음 — 오케스트레이터가 브랜치에서 직접 수집.

## 사용자 결정 필요

1. ROOM SIZE · 도서검토를 DASHBOARD `apps\` 로 옮길지, PID 서버 화면을 계속 쓸지
2. 이번 통합 zip 을 지금 4개(S1·S2·S6·S5)로 만들지, S2 hotfix133(L87–L91 병합) 뒤로 미룰지
3. S7 을 DASHBOARD 메뉴에 붙일지

## 시연 HTML 만드는 법

실제 코드를 띄워 찍은 캡처 + 세션 브랜치의 캡처 + 시연 영상 세션 캡처를 한 파일에 넣는다.

- DASHBOARD: S1 `dashboard/server.py --root <임시> --port 8777` (예시 PJT 7행)
- PID 서버: S2 코드 + S6 `app/valve*` 덮어쓰기 → `uvicorn app.main:app --port 8000`
- 3D: S7 `app/index.html` 을 file:// 로 열기

```
python company-pc-update/demo_build/build_demo.py <캡처 폴더>
```
