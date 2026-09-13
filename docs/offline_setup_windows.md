# 회사 PC 설치 — Windows x86_64 · 오프라인 (사내 PyPI 차단)

개인 PC(Linux · Python 3.11.15)에서 받아 둔 휠로 회사 PC에 설치하는 절차입니다.
인터넷 없이 끝납니다.

- 대상: **Windows x86_64 · Python 3.11** (3.12/3.13 아님 — 휠이 cp311 입니다)
- 준비물: `wheels/` 폴더(39개 · 75.0MB) + 코드 + 아래 §5 목록
- 걸리는 시간: 설치 5분 · 확인(빠른 테스트) 10초

---

## 1. Python 3.11 설치

python.org 설치본(`python-3.11.x-amd64.exe`)을 **미리 받아** 옮깁니다.
설치할 때 두 가지만 지키면 됩니다.

- ☑ **Add python.exe to PATH**
- ☑ **py launcher** (기본 켜짐) — 다른 버전이 이미 있어도 `py -3.11` 로 고를 수 있습니다

설치 후 확인:

```powershell
py -3.11 --version
# Python 3.11.x   ← 3.11 이면 됩니다 (개인 PC 는 3.11.15)
```

> **왜 3.11 인가**: `wheels/` 안의 C 확장 6개가 `cp311-cp311-win_amd64` 로 빌드돼
> 있습니다. 3.12 에 설치하면 "no matching distribution" 으로 멈춥니다.
> (`pymupdf` 만 `cp310-abi3` 라 3.10 이상 공용입니다.)

## 2. 가상환경과 설치

코드를 둘 폴더(예: `C:\pid\AI-P-ID-Extraction-tool`)에서:

```powershell
cd C:\pid\AI-P-ID-Extraction-tool
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
# PowerShell 실행 정책 때문에 막히면 (한 번만):
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# 또는 활성화 없이 .venv\Scripts\python.exe 를 직접 쓰세요.

python -m pip install --no-index --find-links wheels -r requirements-win.txt
```

`--no-index` 가 PyPI 를 아예 보지 않게 하고 `--find-links wheels` 가 로컬 폴더만
쓰게 합니다. 사내망에서 바깥으로 나가는 요청이 **한 번도** 없습니다.

간접 의존까지 개인 PC 와 똑같이 맞추려면 대신 이것을 쓰세요:

```powershell
python -m pip install --no-index --find-links wheels -r requirements-win.lock.txt
```

설치 확인:

```powershell
python -c "import pymupdf, numpy, fastapi, uvicorn, openpyxl, yaml, multipart; print('ok', pymupdf.version)"
# ok ('1.28.2', '1.28.2', None)
```

### uvloop 이 없는 것은 정상입니다

`requirements.txt` 는 `uvicorn[standard]` 를 쓰지만 **Windows 판에서는 부가 의존을
풀어 적고 uvloop 만 뺐습니다.** 이유와 실측은 `requirements-win.txt` 머리 주석에
있습니다. 요약:

| uvicorn[standard] 부가 의존 | Windows | 비고 |
| --- | --- | --- |
| httptools · websockets · watchfiles · python-dotenv · PyYAML | **포함** | win_amd64 휠 전부 있음 |
| **uvloop** | **제외** | Windows 미지원 (`sys_platform != "win32"`) |

uvloop 은 성능용 이벤트 루프일 뿐이고 없으면 uvicorn 이 asyncio 기본 루프로
돕니다. 이 앱은 로컬 1인 사용이고 시간의 대부분이 PyMuPDF 파싱(58장 약 3분 40초)
이라 체감 차이가 없습니다.

## 3. 실행

```powershell
.\start.bat                 # 8000 포트, 코드 변경 감시(--reload)
.\start.bat 9000            # 다른 포트
.\start.bat --no-reload     # 감시 끄기 (조금 빠름)
```

`start.bat` 은 `.venv\Scripts\python.exe` 가 있으면 자동으로 그것을 씁니다
(활성화하지 않아도 더블클릭으로 됩니다).

**브라우저 주소: <http://127.0.0.1:8000>** (포트를 바꿨으면 그 번호로)

- 처음 켜면 Windows 방화벽이 물을 수 있습니다 — **127.0.0.1 로만 듣기** 때문에
  "액세스 허용" 을 누르지 않아도 동작합니다. 취소해도 됩니다.
- 분석 결과는 `app\_data\app.db` 에 남아 다시 켜면 그대로 열립니다.
- 데이터 위치를 옮기려면: `$env:PID_DATA_DIR = "D:\pid_data"` 를 먼저 실행
  (PowerShell 문법입니다 — `export` 가 아닙니다).

## 4. 정상 확인

### 4-1. 빠른 테스트 (10초) — 이관 확인은 이것으로 충분합니다

```powershell
python -m pip install --no-index --find-links wheels -r requirements-win-test.txt
pytest -q -m "not slow and not ui"
# 116 passed, 30 deselected
```

빠진 것이 있으면 여기서 바로 드러납니다 (import 실패 · 경로 · 인코딩).

### 4-2. 전 문서 분석 (약 4분) — 실제 값 확인

```powershell
pytest -q -m slow
# 10 passed
```

### 4-3. UI 테스트 — **브라우저를 따로 옮겨야 합니다**

`pytest -q -m ui` 는 playwright 와 **크로미움 브라우저**가 둘 다 있어야 합니다.
브라우저는 PyPI 휠이 아니라 별도 다운로드(약 150MB)라 `pip download` 로 따라오지
않고, 오프라인에서는 `playwright install` 도 실패합니다.

옮기려면 개인 PC(또는 인터넷 되는 Windows PC)에서:

```powershell
playwright install chromium          # 인터넷 되는 곳에서
# 받아진 폴더: %USERPROFILE%\AppData\Local\ms-playwright\
```

그 폴더를 통째로 회사 PC의 같은 경로에 복사하고, 테스트가 쓰는 경로를 알려줍니다:

```powershell
$env:CHROMIUM_PATH = "$env:USERPROFILE\AppData\Local\ms-playwright\chromium-XXXX\chrome-win\chrome.exe"
pytest -q -m ui
```

> `tests/test_ui_edits.py:45` 의 기본값이 `/opt/pw-browsers/chromium` (리눅스 경로)
> 이므로 **Windows 에서는 `CHROMIUM_PATH` 를 반드시 지정**해야 합니다.
> UI 테스트를 안 돌릴 거라면 `requirements-win-test.txt` 에서 playwright 줄을
> 지우고 4-1 만 하세요 — 이관 확인 목적에는 충분합니다.

### 4-4. 지문(fingerprint)은 **값이 달라도 정상일 수 있습니다**

개인 PC(Linux) 기준선은 **`91ba3e33`** 입니다. 회사 PC 에서 전 문서를 분석했을 때
같은 값이 나오면 이관이 완벽한 것이고, **달라도 곧바로 오류는 아닙니다** — 지문은
엔진 판정 전체의 해시라 부동소수 반올림이나 PyMuPDF/MuPDF 빌드 차이 같은 것도
값을 움직입니다.

다르면 이 순서로 좁히세요. **먼저 무엇이 같은지 확인하는 것이 핵심입니다.**

| 확인 | 기대값 | 다르면 |
| --- | --- | --- |
| 1. 행 수 | **824** (FIELD 680 / MOV 76 / PNEUMATIC 45 / BFV 23) | 검출이 달라진 것 — PyMuPDF 버전을 먼저 보세요 |
| 2. Q'ty 합계 | **1595** | 〃 |
| 3. 등급 분포 | CONFIRMED 704 · PARTIAL 47 · LOW 12 · NONE 61 · SKIP 0 | Description 경로 차이 |
| 4. 판정축 분포 | ⓪14 · ①127 · ②35 · ②a 9 · ②b 84 · ③32 · ④523 | 〃 |
| 5. 라이브러리 버전 | `pymupdf 1.28.2` · `numpy 2.4.6` | **여기서 갈리는 경우가 대부분입니다** |

1~4가 전부 같은데 지문만 다르면 **부동소수·정렬 차이**이므로 산출물은 신뢰할 수
있습니다. 이 경우 회사 PC 의 지문을 새 기준선으로 적어 두고 쓰세요 (그 PC 안에서
재현되는지가 실제로 중요한 성질입니다).

1~4 중 하나라도 다르면 이관 문제입니다:

```powershell
python -c "import pymupdf, numpy; print(pymupdf.version, numpy.__version__)"
# ('1.28.2', '1.28.2', None) 2.4.6   ← 이것과 달라야 원인입니다
```

확인 명령 (전 문서 분석 후 값 출력):

```powershell
python -c "import sys; sys.path.insert(0,'.'); from app import pipeline; import collections; r=pipeline.analyse('data/pid_total.pdf'); print('fingerprint', pipeline.fingerprint(r)[:8]); print('rows', len(r['rows']), dict(collections.Counter(x['tab'] for x in r['rows']))); print('qty', sum(int(x['qty'] or 0) for x in r['rows'])); print('grades', dict(collections.Counter(x['description_grade'] for x in r['rows'])))"
```

## 5. Windows 에서 조심할 것 (코드 검토 결과)

리눅스에서만 돌려 봤으므로 **실행이 아니라 코드 검토로** 추린 목록입니다.
심각도 순이고, 각 항목에 근거 위치를 적었습니다.

### 높음 — 실제로 겪을 가능성이 큽니다

1. **Excel 을 열어 둔 채 다시 내보내면 실패합니다.**
   `GET /revisions/{id}/excel` 은 호출할 때마다 `pid_data\outputs\rev{N}\*.xlsx` 를
   **덮어씁니다** (`app/main.py` 의 `revision_excel`). 리눅스는 열려 있어도 덮이지만
   **Windows 는 파일 잠금이 걸려 `PermissionError [WinError 32]`** 가 납니다.
   → **내보내기 전에 그 xlsx 를 Excel 에서 닫으세요.**
2. **`pid_data` 를 네트워크 드라이브(사내 공유 폴더)에 두지 마세요.**
   SQLite 를 WAL 모드로 씁니다 (`app/db.py` 의 `PRAGMA journal_mode=WAL`).
   WAL 은 SMB 공유에서 잠금이 깨져 DB 손상이 납니다. 로컬 디스크에 두세요.
3. **엔진 CLI 회귀 스크립트는 한국어 콘솔에서 깨질 수 있습니다.**
   `python app\engine\detect_all.py --compare ...` 같은 개발용 스크립트의 보고문
   9곳에 `—`(em dash)가 있는데 cp949 로 인코딩되지 않아 `UnicodeEncodeError` 가
   납니다 (crossval · detect_all · detect_symbols · extract_titleblocks ·
   parse_notes). **서버 경로에는 없습니다** — `app/main.py` · `app/pipeline.py` ·
   `app/desktop.py` 의 출력은 전부 cp949 안전입니다.
   → 그 스크립트를 쓸 때만 `$env:PYTHONUTF8 = "1"` 을 먼저 실행하세요.
   (아예 `setx PYTHONUTF8 1` 로 걸어 두어도 부작용이 없습니다.)

### 중간

4. **프로젝트 이름에 Windows 예약어를 쓰지 마세요** — `CON` · `PRN` · `AUX` ·
   `NUL` · `COM1`~`COM9` · `LPT1`~`LPT9`. `safe_name` 은 `/ \ : * ? " < > |` 은
   막지만(`app/revisions.py`) 예약어와 끝의 마침표·공백은 막지 않아, 그 이름으로
   폴더를 만들 때 실패합니다. 한글 이름은 문제없습니다.
5. **경로 길이.** 바탕화면 깊은 곳에 풀면 `pid_data\outputs\rev12\...` 가 260자
   제한에 닿을 수 있습니다. `C:\pid\` 처럼 짧은 경로에 두세요.
6. **UI 테스트의 브라우저 경로가 리눅스 기본값**입니다 (§4-3).

### 낮음 — 검토했고 문제 없었습니다

7. **POSIX 전용 모듈 0곳** — `fcntl` · `pwd` · `grp` 등을 import 하는 곳이 없습니다.
8. **경로 결합은 전부 `pathlib`** 입니다. `os.path.join` 이나 `"..." + "/"` 로 만든
   경로가 `app/` 에 없습니다. 하드코딩된 `/tmp` · `/usr` · `/home` 도 0곳입니다.
9. **텍스트 파일 쓰기에 인코딩 누락 0곳** — `write_text` · `open` 호출을 AST 로
   전수 확인했고, 인코딩이 없는 6곳은 전부 `pymupdf.open()` · `webbrowser.open()`
   이었습니다. JSON 장부(`axis_overrides.json` · `project.json` · `id_registry.json`)는
   읽기·쓰기 모두 `encoding="utf-8"` 로 대칭입니다.
10. **파일 삭제·이동이 없습니다** — `app/audit.py` 는 세기만 하고 `os.remove` 도
    `shutil.rmtree` 도 코드에 없습니다. Windows 의 "사용 중인 파일 삭제 불가"에
    걸릴 자리가 없습니다.
11. **`PID_DATA_DIR`** 은 `Path(...).expanduser().resolve()` 로 처리해
    (`app/paths.py`) 드라이브 문자·역슬래시를 그대로 받습니다.
    `$env:PID_DATA_DIR = "D:\pid_data"` 로 쓰면 됩니다.
12. **임시 디렉터리를 앱이 직접 만들지 않습니다** — `tempfile` 사용처가 `app/` 에
    0곳입니다 (테스트만 pytest `tmp_path` 를 씁니다).
13. **`--reload`** 는 watchfiles 로 돌고 Windows 휠이 있습니다. 문제 없습니다.

## 6. 옮길 것 목록

`docs/transfer_manifest.md` 를 보세요 — 경로·크기·꼭 필요한지가 표로 있습니다.
요약하면 **코드(1.9MB) + wheels(75MB) + Python 설치본(25MB)** 이고, 발주처 자료와
도면은 회사 PC 에 이미 있는 것을 쓰거나 별도 반출 절차를 따르세요.
