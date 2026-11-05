# 출시 전 점검표 — 업데이트 꾸러미를 내기 전에

꾸러미(`PID_dev+ops_…zip`)를 만들기 전에 위에서부터 차례로 합니다.  `spike/pack_delta.py` 는 2번이 이 HEAD 에서
통과하지 않았으면 **만들지 않고 멈춥니다** (끝 코드 3).

## 순서

1. **병합** — `config/release_sources.json` 에 적힌 다른 세션 브랜치를 먼저 합칩니다 (pack_delta 가 덜 합쳐졌으면 끝 코드 2 로 멈춤).
2. **출시 전 검사** — `python3 spike/release_check.py`
   - 빠른 시험 전체(`-m "not slow and not ui"` · Valve 시험은 참고로만) → JS 구문(`node --check`) → 서버 주소 13곳 스모크 →
     화면 12장 눈 점검(`spike/smoke_screens.js` · node 와 playwright 가 있을 때).
   - 결과: `out/release_check.json` (`head` · `ok` · `failures` · `skipped`).  화면 캡처는 `out/release_smoke/`.
   - 회사 PC(도면 자료가 있는 곳)에서는 `--strict`: 도면·결과 자료가 없어 건너뛴 시험이 있으면 실패로 봅니다.
3. **화면 캡처 확인** — `out/release_smoke/*.png` 를 훑어보고 콘솔 오류 0 인지 (`smoke_screens.js` 의 JSON).
   대시보드 안 모습은 `node spike/smoke_screens.js <주소> out/release_smoke_embed --embed`.
4. **회귀 기준선** — 회사 PC 에서 `python spike/regression_3p.py` 를 돌려 통과표를 `out/<꾸러미 이름>/regression.txt` 로 남깁니다.
   기준선(`spike/baselines_3p.json`)이 움직였으면 원인을 칸 단위로 적기 전에는 내지 않습니다.
5. **꾸러미 만들기** — `python3 spike/pack_delta.py --name <이름> --ops --summary "…" --readme out/<이름>/readme_head.txt`
   - 검사 뒤 문서(`out/` · `docs/` · `*.md` · `*.txt`)만 커밋했다면 검사 결과는 그대로 유효합니다.  코드가 바뀌었으면 2번부터 다시.
   - zip 은 `.tmp` 이름으로 쓰고 기준판 트리에 실제로 적용해 본 뒤에만 제 이름이 됩니다.  검증이 실패하면 zip 이 남지 않습니다.
   - 일부러 검사를 건너뛸 때만 `--skip-checks` — 그 사실이 꾸러미의 `1_먼저읽기.txt` 끝에 "[검사 생략]" 으로 남습니다.
   - 다른 세션의 모듈 꾸러미(`--only …`)는 검사 결과가 없어도 참고만 출력하고 만듭니다.
6. **개발 폴더 적용** — 회사 PC 에서 압축을 전부 풀고 `apply_to_PID_dev.bat` → `check_pid_server.bat`.
7. **운영 반영** — `apply_to_PID_ops.bat` → 화면 업데이트 번호 확인 → 문제면 `rollback_PID_ops.bat`.

## 규칙

- `app/static/app.js` · `logic*.js` 처럼 큰 화면 파일을 고친 묶음은 부분 시험이 아니라 **전체 빠른 시험**을 돌립니다.
- 문자열을 찾는 시험이 깨지면, 의도한 변경인지 먼저 적고 시험을 고칩니다.  새 시험은 문자열보다 **동작**을 확인하게 씁니다.
- `timing` 표시가 붙은 시험(시간·소켓에 기대는 5건)만 빨간 줄이면, 그 파일만 한 번 더 돌려 봅니다 (`pytest -m timing`).
- `pytest.ini` 의 `timeout = 300` 은 `pytest-timeout` 이 깔려 있을 때만 작동합니다 — 없으면 "unknown config option" 경고만 나고 무시됩니다.
  회사 PC 는 오프라인이라 휠을 `wheels\` 에 넣어야 설치됩니다 (`requirements-win-test.txt` 주석).
- 이 컨테이너에서 Valve 시험 일부가 빨개도 판정에서 뺍니다 (회사 소유 — `valve_ok` 에 참고로만 적힘).
