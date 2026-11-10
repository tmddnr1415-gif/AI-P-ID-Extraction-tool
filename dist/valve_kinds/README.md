# valve37 — Globe · Butterfly · PSV Datasheet 검토 (오케스트레이터 통합용)

S5 세션이 사용자 요청(2026-11-10)으로 만든 Valve 모듈 변경분이다. Valve 원본은 S6(`ccr-efbe7e75-n915ze`)이므로 **S6 의 valve36(b0db9a0d) 위에 적용**하는 패치로 둔다.
고객 자료(샘플 PDF · 화면 캡처)는 넣지 않았다.

| 파일 | 무엇 |
|---|---|
| `valve37_from_valve36.patch` | `git am` 용 패치 (기준 b0db9a0d). `app/valve` 6개 + 새 `forms_ext.py` · `app/static/valve/valve.js` · 새 `tests/test_valve_kinds.py` · 새 `docs/valve/VALVE_KINDS.md` |
| `dashboard_valve_menus.patch` | S1 `dashboard/dashboard.html`(APP_VERSION 2026-11-10.12) 의 `PID_ROUTES` 에 Globe · Butterfly · PSV 세 줄 — '준비 중' 대신 `/valve/?kind=…` |
| `files/` | 위 패치를 적용한 결과 파일 그대로 (패치가 안 맞을 때 비교용) |
| `SHA256SUMS.txt` | 위 파일들의 sha256 |

## 적용 순서 (오케스트레이터)

1. S6 브랜치(또는 S6 최신 valve 위)에 `git am dist/valve_kinds/valve37_from_valve36.patch` — S6 가 그 사이 valve 를 더 고쳤으면 S6 와 병합 조정.
2. P&ID 꾸러미(`PID_dev+ops_…`)에 `app/valve/forms_ext.py` 와 새 시험 `tests/test_valve_kinds.py` 가 들어가는지 확인 (`spike/pack_delta.py --only` 목록에 `tests/test_valve_kinds.py` 추가).
3. 대시보드(S1)에 `dashboard_valve_menus.patch` 적용 + `APP_VERSION` 올림.
4. 회사 PC: P&ID 서버 8000 재시작 → 대시보드 실행 프로젝트 › CO2 PJT › Datasheet › Globe Valve / Butterfly Valve / PSV.

새 Python 패키지 없음 (PyMuPDF · FastAPI 등 P&ID 서버에 이미 있는 것만). DB 열 추가 없음.

## 확인한 것

- `pytest tests/test_valve*.py tests/test_tagged_valves.py tests/test_hotfix58_valve_tag_star.py` → 181 통과 (valve36 173 + 새 8). 저장소 전체 1,995 통과, 실패 1 은 Logic 시험의 `python-docx` 미설치(무관).
- 사용자 샘플 4종(Globe CV Form 101 · Butterfly CV Form 101 · Butterfly On/Off Code 80 · PSV Form 701)과 이들을 섞은 15쪽 PDF — 데이터시트 경계 · Notes 연결 · 칸 값 눈 대조. 수치는 `files/docs/valve/VALVE_KINDS.md` 4장.
- Ball 프로젝트(메뉴 kind 없음)는 규칙 · 결과가 valve36 과 같다 (`test_ball_project_unchanged_kind` + 기존 173 시험).

## 사람이 확인할 것

`files/docs/valve/VALVE_KINDS.md` 5장 — 실제 수십 장 PDF 로 첫 적용 대조 · 종류별 필수 칸 목록 · Process Data 양식(Control Valve / PSV 전용 표 여부) · Globe/PSV 전용 규칙은 다음 단계.
