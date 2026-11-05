# 계장 설계 도구 (Instrumentation Design Suite)

계장 설계 부서가 함께 쓰는 도구 모음입니다.  서버 PC 한 대(Windows)에서 프로그램을 켜 두면 부서원은 브라우저(Edge)로
`http://<서버 PC 주소>:8000/` 에 들어와 씁니다.  부서 대시보드 안(`?embed=1&user=이름`)에서도 같은 화면이 열립니다.

| 화면 | 주소 | 하는 일 |
| --- | --- | --- |
| P&ID 리스트 추출 | `/` | P&ID 도면(PDF · DXF)에서 계기·밸브 리스트를 뽑아 검토하고 발주처 양식 Excel 로 냄 |
| LOGIC 검토 · 작도 · 신호 처리 · 시운전 · 블록 시험 | `/logic` `/logic/draw` `/logic/signal` `/logic/commission` `/logic/test` | Logic 도면 검토와 작도 · 시험 |
| 판넬 공간확보 | `/space` (`?view=3d`) | 판넬 치수·수량으로 전기실·계기실 면적 계산 · 배치 |
| DCS 그래픽 | `/dcs` | P&ID · Logic 자료로 DCS 운전 화면 초안 |
| 계장 도서검토 | `/books/` | 사내 계장 도서 검색 · 번역 |

검출은 도면의 글자와 도형을 규칙으로 읽습니다 (OCR · LLM 을 쓰지 않습니다).  판정 기준은 그 도면의 범례에서 실행 중에 잽니다.
제품 이름 · 버전 · 문의처는 `config/product.json` 한 곳에 있습니다.

**사용 설명서: [docs/user_manual.md](docs/user_manual.md)** — 화면별 사용법 · 끄기/켜기 · 자료 위치 · 업데이트 · 백업/복구 · 자주 생기는 문제.
서버가 켜져 있으면 화면의 **?** 단추 → 설명서, 또는 `/help/manual` 로도 봅니다.

## 설치 (서버 PC 한 대)

1. **Python 3.11** 설치 (휠이 cp311 이라 3.12 · 3.13 아님).  인터넷이 막힌 회사 PC 는 [docs/offline_setup_windows.md](docs/offline_setup_windows.md).
2. 프로그램 폴더에서 **`setup.bat`** 더블클릭 — `.venv` 를 만들고, `wheels\` 가 있으면 오프라인으로, 없으면 인터넷으로
   `requirements*.txt` 를 설치한 뒤 점검(`python -m app.lan_check`)까지 합니다.
3. 다른 PC 에서 들어오려면 **`open_firewall_8000.bat`** 을 관리자 권한으로 한 번.

리눅스 · 개발 PC:

```bash
python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --port 8000        # 또는 ./run.sh
```

## 실행

| 무엇 | bat (Windows) |
| --- | --- |
| 부서 공용 서버 켜기 (사내망 · 포트 8000 · 죽으면 다시 켬) | `run_lan_service.bat` |
| 로그온 때 자동으로 켜기 · 그만두기 | `install_autostart_lan.bat` · `uninstall_autostart_lan.bat` |
| 이 PC 에서만 (개발 · 시연) | `start.bat` (`start.bat 9000` · `--lan` · `--reload`) |
| 상태 보기 · 끄기 · 다시 켜기 | `check_pid_server.bat` · `stop_pid_server.bat` · `restart_pid_server.bat` |
| 전체 자료 백업 · 복구 | `backup_pid_data.bat D:\pid_backup` · `backup_pid_data.bat --restore <폴더>` |
| 단일 exe 만들기 | `build.bat` (시험을 통과해야 만든다) |

자료는 모두 `app\_data\` (다른 드라이브: `PID_DATA_DIR`) · 로그는 `logs\server.log` (20MB × 3 회전).
상태 확인 주소: `/version` (제품 · 업데이트 번호) · `/running` (지금 분석 중인 것).

## 업데이트 · 백업

- 업데이트는 zip 꾸러미로 옵니다: 압축을 전부 풀고 → `apply_to_PID_dev.bat` → `apply_to_PID_ops.bat` → 화면의 업데이트 번호 확인 → 문제면 `rollback_PID_ops.bat`.
  도중에 실패하면 자동으로 원래대로 돌립니다.  자세히: 설명서 [업데이트](docs/user_manual.md#업데이트).
- 서버는 `app.db` 를 매일 한 판 떠 둡니다 (7일치 · `PID_BACKUP_DIR`).  나머지 자료까지는 `backup_pid_data.bat` — 설명서 [백업과 복구](docs/user_manual.md#백업과-복구).

## 개발하는 사람에게

- 시험: `python3 -m pytest -q -m "not slow and not ui"` (약 2분).  화면 JS 구문 시험은 node 가 있을 때만 돕니다.
- 꾸러미를 만들기 전: **`python3 spike/release_check.py`** (시험 · JS 구문 · 서버 주소 스모크 · 화면 점검) → `spike/pack_delta.py`.
  순서와 규칙은 [docs/release_checklist.md](docs/release_checklist.md).
- 세션 · 브랜치 지도: [docs/handoff/branches.md](docs/handoff/branches.md) (이 판의 작업 브랜치: `claude/gracious-ride-26nqrf`).
  작업 규칙은 `CLAUDE.md`.
- P&ID 엔진의 원칙 · 로드맵: [docs/state_and_roadmap.md](docs/state_and_roadmap.md) · 엔진 연구 기록(옛 README): [docs/pid_engine_notes.md](docs/pid_engine_notes.md).
- 구조: `app/main.py`(FastAPI 서버 · P&ID API) · `app/engine/`(검출 엔진) · `app/logic/`(LOGIC) · `app/space.py` · `app/dcs.py` · `app/books*.py` · `app/static/`(화면).

## 문의

`config/product.json` 의 `support` 에 적힌 곳으로 (비어 있으면 부서 관리자).
