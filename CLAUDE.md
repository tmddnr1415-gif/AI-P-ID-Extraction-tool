# 세션 공통 규칙 — "Prompt is too long" 방지

대화 기록이 모델 한도를 넘으면 세션이 `Prompt is too long` 으로 멈추고, 그 뒤엔
`/compact` 도 실패한다. 아래 규칙으로 기록이 불어나지 않게 한다.

## 읽지 말 것 (`.claude/settings.json` 에서 Read 차단)

- `pid-instrument-tool/web/standalone.html` (2MB 빌드 산출물)
- `pid-instrument-tool/web/vendor/**`, `**/*.min.js` (pdf.js 압축본)
- `pid-extractor/dist/**` (빌드 산출물 — 원본은 `pid-extractor/index.html`)
- `*.pdf`, `*.xlsx` — 내용 확인은 스크립트로 필요한 부분만 뽑아 요약 출력

## 큰 파일은 부분만

- 1000줄 넘는 파일(`pid-extractor/index.html`, `dev/notes.md` 등)은 먼저 `grep -n` 으로
  위치를 찾고 `offset`/`limit` 으로 필요한 범위만 읽는다.
- 명령 출력은 `| head`, `| tail -50`, `--quiet` 로 줄인다. 시험은 실패 항목만 출력.
- 같은 파일을 반복해서 통째로 다시 읽지 않는다.
- 스크린샷은 꼭 필요할 때만 읽는다. 이미지 한 장이 수천 토큰이다.

## 세션이 길어지면 넘겨준다

작업 단위(기능 하나, 버그 하나)가 끝나면 `HANDOFF.md` 에 아래를 5~15줄로 갱신하고
커밋한다. 다음 작업은 새 세션에서 "HANDOFF.md 읽고 이어서" 로 시작한다.

- 지금 브랜치 / 마지막 커밋
- 끝난 것, 남은 것, 알려진 문제
- 사용자가 다음에 할 일 (예: `apply_to_PID_dev.bat` 실행)
