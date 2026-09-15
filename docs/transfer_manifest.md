# 회사 PC 로 옮길 것 — 경로 · 크기 · 필요 여부

설치 절차는 `docs/offline_setup_windows.md` 입니다. 여기는 **무엇을 담아 가는가**만
적습니다. 측정일 기준 실제 크기입니다.

## 1. 반드시 옮기는 것 — 약 **101MB**

| 항목 | 경로 | 크기 | 파일 | 비고 |
| --- | --- | ---: | ---: | --- |
| **코드 전체** | git 추적분 (`git archive` 권장) | **11.0MB** | 189 | 아래 §1-1 참조 |
| **Windows 휠** | `wheels/` | **75.0MB** | 39 | 이번에 받은 것. 재다운로드 불필요 |
| **Python 설치본** | `python-3.11.x-amd64.exe` | 약 25MB | 1 | python.org 에서 미리 받아 둘 것 |

### 1-1. 코드에서 꼭 필요한 부분

`git archive --format=zip -o pid-tool.zip HEAD` 한 줄이면 아래가 그대로 담깁니다
(`.gitignore` 대상은 자동으로 빠집니다).

| 경로 | 크기 | 파일 | 없으면 |
| --- | ---: | ---: | --- |
| `app/` (엔진·UI·서버) | 1.9MB | 54 | 앱이 없습니다 |
| `config/` | 60KB | 3 | 판정 규칙이 없어 분석이 안 됩니다 |
| `tests/` | 754KB | 19 | 이관 확인(빠른 테스트)을 못 합니다 |
| `spike/` | 616KB | 22 | 정확도 재측정·워크북 생성을 못 합니다 |
| `docs/` | 108KB | 7 | 근거 문서. 없어도 돌지만 인수인계가 끊깁니다 |
| `requirements-win*.txt` | 5KB | 3 | 설치 명령이 참조합니다 |
| `start.bat` · `run.sh` · `build.bat` · `pid_extract.spec` | 10KB | 4 | `start.bat` 이 실행 진입점입니다 |
| `CLAUDE.md` · `README.md` | 109KB | 2 | 인수인계 문서 |

> `app/` 폴더를 **통째로 복사하면 87MB** 가 됩니다 — `app/_data/` 안에 이전 분석
> 결과(DB 16MB)와 업로드된 도면(69MB)이 들어 있기 때문입니다. `git archive` 를
> 쓰면 그것들이 자동으로 빠집니다. 손으로 복사한다면 **`app/_data/` 와
> `__pycache__/` 는 빼세요.**

## 2. 옮길지 정해야 하는 것

| 항목 | 경로 | 크기 | 판단 |
| --- | --- | ---: | --- |
| 이전 분석 결과 | `app/_data/app.db` | 16MB | **권장하지 않음.** 회사 PC 에서 새로 분석하는 편이 낫습니다 (지문 대조도 그래야 의미가 있습니다). 발주처 도면 내용이 들어 있으니 반출 절차도 확인하세요 |
| 업로드된 원본 PDF | `app/_data/uploads/` | 69MB | 위와 같음. DB 만 옮기고 PDF 를 안 옮기면 페이지 뷰어가 열리지 않습니다 |
| 산출물·워크북 | `out/` | 23.5MB (git 추적분 37개) | 참고 자료. `out/label_nouf1.xlsx` · `out/candidates_nouf1.xlsx` 는 발주처 문장이 들어 있어 `.gitignore` 대상이고 `git archive` 에 안 담깁니다 — 필요하면 따로 챙기세요 |
| 크로미움 브라우저 | `%USERPROFILE%\AppData\Local\ms-playwright\` | 약 150MB | UI 테스트(20건)를 회사 PC 에서 돌릴 때만. 안 돌릴 거면 불필요 |

## 3. 발주처 자료 — **목록만** (반출 여부는 회사 규정에 따르세요)

| 파일 | 크기 | 용도 |
| --- | ---: | --- |
| `data/pid_total.pdf` | 19.5MB | 분석 대상 도면 |
| `data/CZE_Field_Instrument.xlsx` | 0.2MB | FIELD 양식 + 검증 대조본 |
| `data/CZH_MOV_Gate_Globe.xlsx` | 0.1MB | MOV 양식 |
| `data/CZI_Butterfly_Valve.xlsx` | 0.1MB | BFV 양식 |

- 이 넷은 `.gitignore` 대상이라 `git archive` 에 담기지 않습니다.
- **양식 세 개는 비어 있어도 됩니다** — 서식만 씁니다. 없으면 그 산출물은 사유와
  함께 건너뜁니다 (`MANIFEST.json` 에 기록).
- `data/` 없이도 앱은 뜨고, 회사 PC 에 이미 있는 도면을 업로드하면 그대로 돕니다.

## 4. 옮기지 않는 것

| 항목 | 왜 |
| --- | --- |
| `.venv/` | 리눅스 바이너리입니다. 회사 PC 에서 새로 만듭니다 (§설치 2) |
| `__pycache__/` · `*.pyc` | 재생성됩니다 |
| `logs/` | 실행 기록 |
| `dist/` · `build/` | exe 빌드 산출물. 필요하면 회사 PC 에서 `build.bat` |
| `.git/` | 필요하면 리포지터리째 클론하세요. 이관만이면 `git archive` 로 충분합니다 |

## 5. 담는 명령 (개인 PC 에서)

```bash
# 코드 (11.0MB · .gitignore 대상 자동 제외)
git archive --format=zip -o /tmp/pid-tool.zip HEAD

# 휠 (75.0MB)
zip -r /tmp/pid-wheels.zip wheels/

# 확인
unzip -l /tmp/pid-tool.zip | tail -1
unzip -l /tmp/pid-wheels.zip | tail -1
```

회사 PC 에서 둘 다 같은 폴더에 풀면 `wheels/` 가 코드 옆에 오고, 설치 문서의
`--find-links wheels` 가 그대로 맞습니다.
