# valve37 — Globe · Butterfly · PSV 데이터시트 검토 (Ball Valve 와 같은 화면)

기준판: valve36 (`ccr-efbe7e75-n915ze` b0db9a0d). 만든 곳: S5 세션(2026-11-10, 사용자 요청 — 회사 PC 가 아니라 클라우드에서 개발해 오케스트레이터 통합본으로 전달).

## 1. 무엇이 되나

대시보드 **실행 프로젝트 › CO2 PJT › Datasheet › Globe Valve · Butterfly Valve · PSV** 메뉴가 Ball Valve 와 같은 화면(`/valve/?kind=globe|butterfly|psv`)을 연다.
사용자는 Ball 과 똑같이 Datasheet PDF 여러 개(각 수십 장) · Process Data · (선택) PMS · Valve List 를 드래그앤드롭한다.

| 양식 | 어떤 밸브 | 읽는 방법 |
|---|---|---|
| **Code 80** On/Off (Ball 과 같은 양식) | Butterfly On/Off (SDV · XV …) | 기존 괘선 칸 읽기 + 라벨 7개 추가 · **쪽 아래 제목란**(Sheet · Rev · Revision 줄) · **Notes 만 있는 2쪽** 연결 |
| **Form 101** Control Valve | Globe CV · Butterfly CV | 1쪽 = Form 102 와 같은 2단 'Label : value' → 기존 `read_page_102` 로 읽고 `forms_ext.fix_101` 이 **묶음(세로 글자 띠) · 소제목**으로 다시 분류 · 2쪽 Max/Nor/Min 표의 Sizing 행 · 3쪽 Notes(form 000) |
| **Form 701** Pressure Relief Valve | PSV | 새 `forms_ext.read_page_701` — 번호 1~50 한 열, 굵은 값, **밑줄 = 값 칸**, 작은 부제(Type · Action · Size · Rating …), 'A / B / C' 라벨은 칸마다 다른 키, 단위 칸(bar-g · ºC)은 앞 값의 단위 |

판정 원칙은 Ball 과 같다 — OCR · LLM 없음, 그 쪽에서 잰 괘선 · 밑줄 · 번호 열 · 글자 크기만 사용, 문서에 없는 값은 만들지 않음(빈칸 / review).

## 2. 메뉴 = 프로젝트 공간 · 규칙 묶음

- `?kind=globe` 이면 프로젝트 이름이 `CO2 PJT · Globe Valve` (없으면 만든다). 업로드 · Process Data · 검토 상태가 Ball 과 섞이지 않는다.
- 규칙은 **프로젝트의 종류**로 고른다 (`schema.project_kind`). Ball 프로젝트(이름에 접미사 없음 = valve36 까지의 모든 프로젝트)는 **지금과 똑같이** 돈다.
- Globe · Butterfly · PSV 프로젝트: 필수 칸(DM-01)은 `schema.REQUIRED_BY_KIND`, 빈 Process Data(DM-02) · HOLD/TBC · 문서 안 모순(DE) · Notes 참조 · Revision · Process Data 비교 · Tag 규칙은 Ball 과 같다.
  Ball 전용 규칙(PMS Ball 품목 · MR 재질 · VR 설계 · AC 액세서리 · PC 동료 비교)은 돌리지 않고 Checks 탭에 'Ball Valve rule — not applied to this valve kind' 로 n/a 표시.
- 데이터시트마다 시트가 스스로 말하는 종류(`family`: Valve Type / Body Type / Instrument Type / 제목 / 양식)를 읽어, 다른 메뉴에 올린 시트는 저장하되 업로드 경고와 화면 안내 띠로 알린다.

## 3. 바뀐 파일

| 파일 | 내용 |
|---|---|
| `app/valve/forms_ext.py` (새) | `form_no` · `fix_101` · `fix_101_sheet2` · `read_page_701` · `footer`/`apply_footer` · `read_continuation` |
| `app/valve/schema.py` | Code 80 라벨 7개 · `KINDS` · `project_kind` · `family` · `_L101`/`lookup_101` · `SIZING_101`/`SPAN_101`/`PROPS_101` · `_L701`/`SUB_701`/`SUBKEY_701`/`lookup_701` · `REQUIRED_BY_KIND` |
| `app/valve/extract.py` | `PARSER_VERSION extract-v37` · Form 701/101 연결 · 쪽 아래 제목란 · Notes 만 있는 다음 쪽 · Form 101 2쪽 · `ds["form"]`/`ds["family"]` |
| `app/valve/api.py` | `VERSION valve37` · `_proj_kind` · 종류별 규칙 · 다른 메뉴 경고 · `d["kind"]`/`d["family"]` · `ds["form"]` 유지 |
| `app/valve/issues.py` | DM-01 필수 칸을 종류별로 |
| `app/valve/checks.py` | `BALL_ONLY` 묶음 → 다른 종류에서 n/a(이유 표시) |
| `app/static/valve/valve.js` | `?kind=` · 프로젝트 이름 · 머리 · 칸 묶음(Design Basis · Valve Trim · Materials · Sizing · Positioner) · Form 101 Max/Nor/Min 표 · 다른 메뉴 안내 띠 · Ball 3D 모형은 Ball 메뉴에서만 · Expert 탭 안내 |
| `tests/test_valve_kinds.py` (새) | 합성 PDF 3종(PSV 701 · CV 101 · Code 80 아래 제목란) · 도우미 · API 종류별 규칙 · Ball 프로젝트 불변 · 실자료(`VALVE_KIND_SAMPLES`) |

## 4. 시험 · 실측 (2026-11-10)

- `pytest tests/test_valve*.py tests/test_tagged_valves.py tests/test_hotfix58_valve_tag_star.py` — **181 통과**(valve36 173 + 새 8) · 저장소 전체 1,995 통과(실패 1 = Logic 시험의 python-docx 미설치, 무관).
- 샘플 4종(사용자 제공, 저장소에 넣지 않음) — 지금 코드 → valve37:

| 샘플 | 읽힘(ok) | 미등록 라벨 | Notes | 쪽 묶음 |
|---|---|---|---|---|
| Butterfly On/Off (Code 80) | 47 → 50 /91 | 7 → 0 | 0 → 9 | Sheet · Rev 못 읽음 → 1/2 · 2/2 · Rev A |
| Globe CV (Form 101) | 1쪽 65 → 67 | 68+45 → 0 | 0 → 6 | 3쪽 모두 한 Tag |
| Butterfly CV (Form 101) | 61 /120 | 68+45 → 0 | — (샘플 2쪽) | 문서번호 오인(P&ID 번호) → 빈칸 |
| PSV (Form 701) | **2 → 34** /80 (나머지는 실제 빈칸 · VTA) | 79 → 0 (review 1 = 라벨보다 많은 값 칸) | 0 → 5 | 1/2 · 2/2 |

- 15쪽 혼합 PDF(표지 + Globe 3쪽 + Butterfly CV 2쪽(3쪽 빠짐) + PSV + Butterfly On/Off + PSV + Globe) → 데이터시트 6개, 경계 · Notes 모두 정확.
- 실제 지적 예: Globe 샘플 1쪽 Service 'GLOB VLV' ↔ 2쪽 'GLOBE VLV' → Data Error(DE-06).

## 5. 사람이 확인할 것

1. 실제 프로젝트 PDF(각 수십 장)로 첫 적용 후 Tag 수 · 쪽 묶음 · 칸 값을 몇 장 눈으로 대조 (샘플은 양식마다 1~2 장뿐).
2. 종류별 필수 칸 목록(`REQUIRED_BY_KIND`)과 Ball 전용 규칙 제외가 회사 기준과 맞는지 — Globe/PSV 전용 규칙(Cv · Travel · SPL · API 526 Orifice · Back Pressure)은 아직 없음(다음 단계).
3. Process Data 는 Ball 과 같은 'Process Data for On-Off Valve' 표 양식을 읽는다. Control Valve · PSV 전용 표가 따로 있으면 그 양식이 필요.
4. Valve List(TBE) 채우기는 Ball 양식 기준 — 다른 종류는 Tool format Excel 만.

## 6. 대시보드 연결 (S1 DASHBOARD 파일)

`dashboard/dashboard.html` 의 `PID_ROUTES` 에 세 줄 추가(`PID_ROUTES` 가 `MODULES` 보다 먼저 보이므로 '준비 중' 대신 이 화면이 열림) + `APP_VERSION` 올림:

```js
  globev:{ title:'CO2 PJT · Datasheet · Globe Valve', port:PID_PORT, path:'/valve/', q:'embed=1&project=CO2%20PJT&kind=globe&' },
  bflyv:{ title:'CO2 PJT · Datasheet · Butterfly Valve', port:PID_PORT, path:'/valve/', q:'embed=1&project=CO2%20PJT&kind=butterfly&' },
  psv:{ title:'CO2 PJT · Datasheet · PSV', port:PID_PORT, path:'/valve/', q:'embed=1&project=CO2%20PJT&kind=psv&' },
```
