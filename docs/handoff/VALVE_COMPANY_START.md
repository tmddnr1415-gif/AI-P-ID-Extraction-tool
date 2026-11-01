# 회사 PC 에서 VALVE(Ball Valve Datasheet 검토) 개발을 이어 가기

회사 PC 의 Claude Code 가 이 한 장과 `docs/handoff/valve.md` 를 읽고 이어 갑니다.

## 1. 받은 zip 세 개와 푸는 곳

| zip | 무엇 | 어디에 · 어떻게 |
|---|---|---|
| `PID_dev+ops_valve29_2026-11-01.zip` | Ball Valve 검토 프로그램 (P&ID 서버 8000 의 `/valve/`) | 아무 곳(예: `C:\Claude\updates\valve29\`)에 풀고 **`apply_to_PID_dev.bat` → 확인 → `apply_to_PID_ops.bat` → 8000 서버 재시작**. `C:\Claude\PID_dev` 와 운영 폴더에 들어감 |
| `UPDATE_from_v16.51_VALVE2_menu.zip` | 대시보드 메뉴 (Globe · Butterfly · PSV) | 아무 곳에 풀고 대시보드 화면을 닫은 뒤 **`APPLY.bat`** 더블클릭 (C:\Claude 아래 Dashboard 폴더를 스스로 찾음) |
| `VALVE_devkit_valve29_2026-11-01.zip` | 개발을 이어 갈 문서 · 점검 도구 | **`C:\Claude\PID_dev` 에 그대로 풀기** (폴더 구조 유지 · 같은 이름이 있으면 덮어쓰기). 프로그램 코드는 첫 번째 zip 이 이미 넣음 |

순서: ① valve29 적용 → ② 대시보드 적용 → ③ devkit 을 `C:\Claude\PID_dev` 에 풀기 → ④ `C:\Claude\PID_dev` 에서 Claude Code 실행.

## 2. 회사 Claude Code 에 줄 첫 지시문 (그대로 붙여 넣기)

```
C:\Claude\PID_dev 는 P&ID 추출 도구이고, 그 안의 app/valve · app/static/valve 가
"Ball Valve Datasheet 검토" 프로그램이다 (P&ID 서버 8000 의 /valve/, 대시보드 메뉴 실행 프로젝트 › CO2 PJT › Datasheet › Ball Valve).
먼저 docs/handoff/VALVE_COMPANY_START.md 와 docs/handoff/valve.md 의 '지금 상태' 절을 읽어라.
큰 파일(app/static/valve/valve.js 등)은 통째로 읽지 말고 grep 으로 필요한 부분만 본다.

지킬 것:
- 기존 판정을 바꾸지 않는다. 새 규칙은 Rule ID 를 붙이고 checks.REGISTRY · RULE_VERSION · RULE_SOURCE · docs/valve/valve29/RULE_CHANGELOG.md 에 적는다.
- 검출 · 판정에 OCR · LLM 을 쓰지 않는다. 문서에 없는 값은 만들지 않고 비우거나 Review Required 로 둔다.
- 모든 지적에 출처 문서 · 쪽 · 기준값 · 실제값 · 근거를 붙인다.
- 고객 자료(Datasheet · PMS · Process Data PDF, 엑셀)는 저장소에 커밋하지 않는다.
- 고친 뒤 반드시: python -m pytest -q tests -k valve 가 모두 통과해야 한다.
  실자료가 있으면 python spike/valve_eval.py --ds <Datasheet.pdf> --tbe <TBE.xlsx> --pms <PMS.pdf> --pd <Process_Data.pdf> --check 로 기준값이 그대로인지 본다.
- 회차를 마치면 docs/history/other_log.md 끝에 5~15줄, docs/handoff/valve.md '지금 상태' 를 고쳐 쓴다.
- 나는 계장 엔지니어(개발 비전공)다. 보고는 "무엇이 달라졌나 · 어디서 보나 · 무엇을 더 해야 하나" 만 쉬운 말로.

이번에 할 일: (여기에 요청을 적는다 — 예: "Globe Valve 검토를 Ball Valve 와 같은 방식으로 만들어라. 샘플 데이터시트는 C:\Claude\samples\globe\ 에 있다")
```

## 3. 개발 PC 에서 돌려 보는 법

- 서버: `C:\Claude\PID_dev` 에서 `.venv\Scripts\python -m uvicorn app.main:app --port 8000` → 브라우저 `http://localhost:8000/valve/`.
  **실데이터 폴더를 쓰지 말고 사본으로**: `set PID_DATA_DIR=C:\Claude\valve_test_data` 를 먼저(시험용 결정 · 수정이 운영 DB 에 섞이지 않게).
- 시험: `.venv\Scripts\python -m pytest -q tests -k valve` (108개).
- 화면 자기점검(선택 · Node.js + Playwright 가 있을 때): `node spike/valve_ui_audit.cjs http://127.0.0.1:8000` (25/25) · `node spike/valve_filter_check.cjs <주소> <캡처폴더>`.
- 판정이 그대로인지(선택): 서버를 켠 채 `python spike/valve_snapshot_diff.py save base.json` (고치기 전) → 고친 뒤 `... check base.json` → 추가 · 삭제 · 변경 건수.

## 4. 어디를 보면 되나

| 알고 싶은 것 | 파일 |
|---|---|
| 지금 상태 · 남은 일 · 점검 목록 | `docs/handoff/valve.md` |
| 설계 이유 (회차별 §) | `docs/valve/DESIGN.md` (§32 이후가 최근) |
| 사용법 | `docs/valve/USER_GUIDE.md` |
| 규칙 목록 · 변경 기록 | `app/valve/checks.py` (REGISTRY) · `docs/valve/valve29/RULE_CHANGELOG.md` |
| 볼밸브 · 액세서리 지식 | `docs/valve/BALL_VALVE_KNOWLEDGE.md` (`app/valve/knowledge.py` 에서 생성) |
| 회차 기록 | `docs/history/other_log.md` |
| Phase 1 보고서 | `docs/valve/valve29/` (IMPLEMENTATION · REGRESSION · RULE_CHANGELOG · USER_GUIDE_UPDATE) |

## 5. 회사에서 업데이트 꾸러미를 직접 만들 때

회사 PC 에서 고친 것은 회사 폴더에 바로 반영되므로 꾸러미가 필요 없습니다. 클라우드 세션과 다시 합칠 때는
바뀐 파일(app/valve · app/static/valve · tests/test_valve* · docs)을 zip 으로 묶어 클라우드 세션에 올려 주면 그 위에서 이어 갑니다.
