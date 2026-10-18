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

## 회사로 보내는 법 (바뀐 파일만)

1. `dashboard/` 수정을 커밋한다.
2. `python3 dashboard_tools/make_patch.py` → `dashboard_patches/dashboard_patch_<날짜>.zip`
   - `dashboard_tools/delivered.txt` 맨 아래 줄(마지막 전달본) 이후 바뀐 파일만 담는다.
   - 안에 `APPLY.bat`: 회사본이 기준판과 같으면 `backup\patch_…\` 에 백업 후 덮어쓰고, 회사에서 이미 고친 파일은 옆에 `.new` 로 둔다.
   - `[주의]` 가 나오면 (버전 안 올림, 변경 이력 없음 등) 고친 뒤 다시 만든다.
   - 회사가 지금 어느 판인지 모르면 `--any`: 기준 = 원본 기준판, `delivered.txt` 의 모든 전달본 내용을 `known/` 에 넣어 회사본이 그중 하나와 같으면 백업 후 덮는다 (어느 판에서든 한 zip).
3. 건넬 zip 은 `--mark` 를 붙여 만든다 → `delivered.txt` 에 기준점이 한 줄 늘어난다. 이것을 커밋·푸시한다.
