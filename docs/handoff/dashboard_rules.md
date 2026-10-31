# 저장소 안내

이 저장소에는 두 가지가 같이 있다.
- 루트·`pid-extractor/`·`pid-instrument-tool/` : P&ID 추출 도구
- `dashboard/` : 회사 PC 의 **계장ENG그룹 주간업무 Dashboard** 코드 사본 (구조는 `dashboard/DASHBOARD_ARCHITECTURE.md`)

## dashboard/ 작업 규칙

- 기준판 = 커밋 `54f2837` (`dashboard_tools/delivered.txt` 첫 줄, 회사에서 받은 EGG 압축을 그대로 푼 것). `*.bat.txt` 는 `*.bat` 로 되돌려 둠.
- 계정·업무자료 폴더(`accounts/ data/ history/ trash/ archive/ saves/ board/ messages/ files/ backup/ apps/`)는 사본에 없다. 만들거나 지어내지 않는다. 시험이 필요하면 임시 폴더에서만.
- `DASHBOARD_ARCHITECTURE.md` 의 제약을 따른다: 외부 라이브러리·CDN 금지, Python 3.11 표준 라이브러리만, `dashboard.html` 바꾸면 `APP_VERSION`, `server.py` 바꾸면 `SERVER_VERSION` 을 올린다.
- 새로 만들거나 고치는 `.bat` 는 ASCII · CRLF · `chcp` 없음. (기준판의 bat 는 LF 이고 `start_server.bat` 에 `chcp 65001` 이 있다 — 고칠 일이 생기면 그때 맞춘다.)
- 바꾼 내용은 `DASHBOARD_ARCHITECTURE.md` 맨 끝 `## 변경 이력` 에 날짜별로 덧붙인다. 회사 Claude Code 가 읽고 이어갈 수 있게:
  ```
  ### 2026-10-13 (APP_VERSION 2026-10-13.1 / SERVER_VERSION 그대로)
  - 무엇을: …  왜: …
  - 바뀐 곳: dashboard.html `함수이름` / server.py `함수이름`
  - 확인한 것: … / 회사에서 확인할 것: …
  ```
- `deploy/` 는 서버가 자동으로 만든다. 직접 고치지 않는다.

## 이 작업 줄기가 맡는 것 (2026-10-22 사용자 지시)

- 사용자가 부르는 세션 이름 (2026-10-26): **1. DASHBOARD 코드 = 여기** · 2. PID 코드 · 3. LOGIC 검토 코드 · 4. PANEL 코드(ROOM SIZE 계산) · 5. 도서 검토. **2~5 에서 개발한 것은 모두 '2. PID 코드' 가 한 꾸러미 zip 으로 낸다.** 여기서는 대시보드 zip 만 낸다.

- 여기서는 **대시보드(`dashboard.html` · `server.py` · bat)와 계장 광장(`dashboard/plaza/`)만** 고친다.
- **P&ID 분석 · LOGIC 분석(LOGIC 작성 포함) · ROOM SIZE 계산(옛 판넬 공간확보, `dashboard/apps/space/`) · 도서검토(`dashboard/apps/books/` · `dashboard/books_api.py`)** 는 다른 곳(다른 세션 · 브랜치, 예: `ccr-d82d97fa-bb3ty3` · `claude/logic-review-design-pd2z75` · `claude/titleblock-parsing-c5st4x` · 도서검토 `claude/new-session-v23o67`)에서 만들고 zip 도 거기서 낸다. 여기서는 그 내용을 고치지 않는다. (2026-10-25 사용자 지시: 대시보드 zip 에는 대시보드만)
  - **ROOM SIZE 계산** 업데이트 파일(zip)은 P&ID 와 같이 **'2. PID 코드' 세션**에서 만든다 (2026-10-25 사용자 지시). 여기서는 메뉴 이름 · 연결만.
  - **ROOM SIZE 계산 · 도서검토는 P&ID · LOGIC 과 같이 P&ID 서버(run_lan_service.bat, 8000)에서 동작** (2026-10-26 사용자 지시) → 대시보드는 `PID_ROUTES` 의 `/space` · `/books/` 로 연결만. 대시보드 zip 에 `apps/` 는 넣지 않는다(make_patch 가 뺌).
  - 대시보드는 그 도구들을 메뉴에서 **보여 주기(연결 · 출력)만** 한다 (`PID_ROUTES` · `APP_ROUTES` · 메뉴 권한 `MENUS`).
  - 다른 곳에서 낸 zip 을 회사가 적용했다고 하면, 그 zip 의 파일로 이 저장소를 맞추고(`delivered.txt` 에 기준 줄 추가) 그 위에서 이어 간다. 대시보드 파일(`dashboard.html` · `server.py`)에 그쪽 변경이 섞여 있으면 그대로 두고 함께 이어 간다.

## 회사로 보내는 법 (바뀐 파일만)

1. `dashboard/` 수정을 커밋한다.
2. `python3 dashboard_tools/make_patch.py` → `dashboard_patches/dashboard_patch_<날짜>.zip`
   - `dashboard_tools/delivered.txt` 맨 아래 줄(마지막 전달본) 이후 바뀐 파일만 담는다.
   - 안에 `APPLY.bat`: 회사본이 기준판과 같으면 `backup\patch_…\` 에 백업 후 덮어쓰고, 회사에서 이미 고친 파일은 옆에 `.new` 로 둔다.
   - `[주의]` 가 나오면 (버전 안 올림, 변경 이력 없음 등) 고친 뒤 다시 만든다.
   - 회사가 지금 어느 판인지 모르면 `--any`: 기준 = 원본 기준판, `delivered.txt` 의 모든 전달본 내용을 `known/` 에 넣어 회사본이 그중 하나와 같으면 백업 후 덮는다 (어느 판에서든 한 zip).
3. 건넬 zip 은 `--mark` 를 붙여 만든다 → `delivered.txt` 에 기준점이 한 줄 늘어난다. 이것을 커밋·푸시한다.
