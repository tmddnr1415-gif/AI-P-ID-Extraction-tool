# P&ID → 계기·밸브 리스트 추출

P&ID PDF 를 읽어 발주처 Excel 양식(Field Instrument / I&C Butterfly Valve /
MOV Gate&Globe / Control·Shutoff Valve)을 채웁니다. 도면은 100% 벡터이므로 OCR 을
쓰지 않고 텍스트 앵커와 도형 검증으로 판정하며, 판정 규칙은 문서의 Symbol & Legend
시트에서 런타임에 측정합니다. LLM 을 호출하지 않습니다.

## 처음 한 번 — 내 PC 에 올리기

이 앱은 **띄운 그 컴퓨터에서만** 보입니다. `127.0.0.1` 은 서버가 도는 기계의
루프백이므로, 다른 기계(원격 컨테이너·CI 러너·클라우드 세션)에서 띄운 서버는
내 브라우저로 열리지 않습니다. 열려면 내 PC 에서 아래를 한 번 해 둡니다.

```bash
git clone https://github.com/tmddnr1415-gif/AI-P-ID-Extraction-tool.git
cd AI-P-ID-Extraction-tool
git checkout claude/titleblock-parsing-c5st4x

python3 -m venv .venv && source .venv/bin/activate    # 권장 (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

**파이썬 3.10 이상** (3.11.15 에서 개발·검증). 패키지는 `requirements.txt` 7개
— pymupdf, openpyxl, PyYAML, numpy, fastapi, uvicorn[standard], python-multipart.
테스트까지 돌리려면 `pip install pytest playwright && playwright install chromium`.

**도면과 발주처 양식은 리포지터리에 없습니다.** 용량이 크고 프로젝트별 자료라
`.gitignore` 가 `data/*.pdf` 와 `data/*.xlsx` 를 제외합니다. 원본을 `data/` 에
이 이름 그대로 넣어 주세요.

| 파일 | 쓰이는 곳 | 없으면 |
| --- | --- | --- |
| `data/pid_total.pdf` | 분석 대상 도면 | UI 에 끌어다 놓아도 되므로 필수는 아님 |
| `data/CZE_Field_Instrument.xlsx` | FIELD 출력 양식 | FIELD 가 이유와 함께 건너뛰어짐 |
| `data/CZI_Butterfly_Valve.xlsx` | BFV 출력 양식 | BFV 건너뛰어짐 |
| `data/CZH_MOV_Gate_Globe.xlsx` | MOV 출력 양식 | MOV 건너뛰어짐 |

**세 xlsx 는 데이터가 채워져 있어도 되고 비어 있어도 됩니다** — 앱은 양식(서식·헤더·
열너비·Note)만 쓰고 데이터 영역은 새로 채웁니다. 즉 실사용에서 올릴 것은 **빈 양식**
이면 충분하고, 완성된 리스트는 필요하지 않습니다. `data/` 에 두는 대신 화면의
**템플릿 패널**에서 올려도 됩니다(`app/_data/templates/` 에 저장되고 `data/` 보다
우선합니다). 어느 쪽도 없으면 그 산출물은 **양식을 지어내지 않고** 이유와 함께
건너뜁니다. `data/` 가 통째로 비어 있어도 분석·검토·재분석은 정상 동작합니다.

**분석 결과는 옮겨올 수 없습니다 — 옮겨올 필요도 없습니다.** `app/_data/` 도
`.gitignore` 대상이라 커밋되지 않습니다. 내 PC 에서 PDF 를 한 번 끌어다 놓으면
58장 약 7분이 걸리고, 그 결과는 이전 실행과 **바이트 단위로 동일**합니다
(`tests/test_determinism.py::test_reanalysis_is_byte_identical` 가 보장).
즉 재분석으로 잃는 것은 시간뿐이고, DB 를 옮겨야만 살아나는 것은 **사람이 손으로
고친 값(`user_values`)** 하나입니다. 아직 손편집이 없다면 재분석이 곧 원본입니다.

**Windows** 에서는 `run.sh`(bash) 대신 `start.bat` 을 씁니다. 더블클릭해도 되고,
명령창에서 인자를 줘도 됩니다.

```bat
start.bat                 :: 8000 포트, 코드 수정 시 자동 재시작
start.bat 9000            :: 포트 변경
start.bat --no-reload     :: 파일 감시 끔
start.bat --verify        :: 검증 모드 (아래)
```

`.venv\Scripts\python.exe` 가 있으면 그것을 쓰므로 가상환경을 따로 활성화하지 않아도
됩니다. 로그는 화면에 나오면서 `logs\server.log` 에도 쌓입니다(cmd 에 `tee` 가 없어
같은 일을 파이썬 한 줄로 합니다). uvicorn 을 직접 부르는 것도 됩니다.

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

## 실행

```bash
pip install -r requirements.txt
./run.sh
```

접속: **http://127.0.0.1:8000**

`run.sh` 는 서버 로그를 **화면에 보여주면서 `logs/server.log` 에도 남깁니다**
(`2>&1 | tee -a logs/server.log`). 포트를 바꾸려면 `./run.sh 9000`.

**프론트엔드용 서버는 따로 없습니다.** UI 는 빌드 도구 없는 HTML/JS 이고 같은
FastAPI 프로세스가 `app/static/` 에서 서빙합니다 — 포트 하나, 로그 하나입니다.

**코드 수정 시 자동 재시작됩니다** (`--reload`). 파이썬 파일을 저장하면 서버가 스스로
다시 뜨고, HTML/JS/CSS 는 재시작 없이 브라우저 새로고침만 하면 됩니다. 감시를 끄려면
`./run.sh --no-reload`.

**이미 분석된 결과가 있으면 재분석하지 않습니다.** 결과는 `app/_data/app.db` 에
남아 있고, 첫 화면에 이전 분석 목록이 뜨며 클릭하면 곧바로 그리드로 갑니다
(`http://127.0.0.1:8000/#<job_id>` 로 바로 들어가도 됩니다). 처음부터 다시 하려면
`rm -rf app/_data`.

새 PDF 는 창에 끌어다 놓으면 분석이 시작됩니다(58장 기준 약 7분, 진행률 SSE 실시간).

직접 띄우고 싶다면:

```bash
python3 -m uvicorn app.main:app --reload --port 8000 2>&1 | tee -a logs/server.log
```

## 분석이 느릴 때 — 어디에 시간이 갔는지

분석은 페이지별·단계별 소요시간을 로그에 남깁니다(`logs/server.log`). 페이지마다 한 줄,
끝에 단계별 합계가 붙습니다.

```
  page   6    4.31s   instruments 4.18s annotations 0.13s
  page   7    3.92s   instruments 3.80s annotations 0.12s
analysis took 431.2s, by stage:
  valves.bodies           148.30s   34.4%
  titleblock_glyphs        85.19s   19.8%
  instruments              79.40s   18.4%
  ...
  slowest pages: p16 12.4s, p14 11.0s, ...
```

같은 내용이 `GET /jobs/{id}` 의 `engine.timings` 로도 남으니 나중에 비교할 수 있습니다.
파서는 **PyMuPDF 하나뿐**입니다 — `pdfplumber` 도 `pypdfium2` 도 설치되어 있지 않고
코드에서 부르지도 않습니다(`grep -rn "pdfplumber\|pdfium" app/` → 0건).

## 검증 모드

앱이 실사용에서 받는 입력은 **P&ID PDF** 와 **빈 출력 양식** 둘뿐입니다. 완성된 계기
리스트는 존재하지 않습니다 — 있으면 이 앱이 필요 없습니다. 그래서 도면 귀속은 기본적으로
`DRAWING`(도면에서 검출) 하나이고, 귀속 열과 필터는 화면에 나오지 않습니다.

Phase 0 의 정확도 측정처럼 **완성된 리스트와 대조**하려면 명시적으로 켭니다.

```bash
PID_VERIFY_EXCEL=data/CZE_Field_Instrument.xlsx ./run.sh     # Windows: start.bat --verify
```

이때만 귀속이 `MATCHED` / `PDF_ONLY` 로 갈리고, 귀속 열·필터·출력범위 선택이 나타납니다.
지정한 파일이 없으면 검토 목록에 `ORIGIN_REFERENCE_MISSING` 이 떠서 "대조를 안 했다"와
"대조했더니 없었다"가 구분됩니다. `REVISION_GAP`(도면 안의 개정 주석)은 대조 파일이
필요 없으므로 두 모드 모두에서 판정됩니다.

## 내가 확인할 체크리스트

화면에서 아래가 맞는지 봐 주세요. 괄호 안은 이번 회차 실측값입니다.

- [ ] **p6 오버레이** — 좌측 페이지 선택에서 `p6` 선택. Field 박스 24개 + MOV 8개.
      `Vendor` 열이 `VENDOR` 인 행을 클릭하면 도면 위 해당 박스가 흰 테두리로 강조됩니다.
      (주의: 오버레이 색은 **탭 색**입니다 — Field 파랑 / MOV 주황 / BFV 초록.
      vendor mark 여부는 색이 아니라 `Vendor` 열과 근거 패널의 `VENDOR_MARK_*` 로 봅니다.
      벤더마크가 붙은 심볼은 제외 대상이라 애초에 행으로 나오지 않습니다.)
- [ ] **행 수** — 상단 탭 `전체 892` / `Field 748` / `BFV 23` / `MOV 76` / `Pneumatic 45`.
      `출력 범위` 패널에서 `DRAWING 605행` / `REVISION_GAP 287행`
      (`MATCHED` / `PDF_ONLY` 는 검증 모드에서만 나옵니다 — 위 "검증 모드" 참고)
- [ ] **Pneumatic 탭** — 45행. 아무 행이나 눌러 근거 패널을 보면 액추에이터 근거가
      `legend p3 pneumatic dome, no letter drawn` 또는 `... cylinder ...` 이고,
      `dome` 인 행의 태그는 TCV/FCV/PCV 계열, `cylinder` 인 행은 XV 계열입니다
- [ ] **검토필요 배지** — `검토 필요 38행 + 문서 1건` (배지에 마우스를 올리면 문서 건 내용:
      `SCOPE_OVERRIDE_UNRESOLVED`)
- [ ] **적용 규칙 패널** — 상단 `적용 규칙` 클릭. 제외 스코프가 `glyph+text+box`,
      활성 제외규칙 3종, 비활성 `SCT_SUPPLIER_SCOPE`, 밸브 규칙 7종(`PNEUMATIC_SHELL`
      포함), 범례 유도에 `pneumatic: LEGEND`
- [ ] **Excel 출력** — `전체 검토 완료` 체크 후 `Excel 출력`.
      양식이 있는 산출물만 나옵니다: FIELD 748 / BFV 23 / MOV 76 / PNEUMATIC 45
- [ ] **템플릿 패널** — Pneumatic·Master 는 `없음`. xlsx 를 올리면 다음 출력에 포함됩니다

## 화면

- **탭** 전체 / Field / BFV / MOV / Pneumatic / 검토필요 (각 건수 표시)
- **양방향 선택** 그리드 행 ↔ 도면 위 박스
- **인라인 편집** Type, Q'ty, System, Valve Type, Vendor, Scope, Tag No.,
  Description. 사람이 고친 값은 `user_values` 에 따로 저장되어 **재분석해도
  보존**됩니다
- **판정 근거 패널** 앵커 / Body 판정 / 액추에이터 / 제외 사유 / 수량 근거
- **검토 필요 건수** 상단에 상시 표시

## 출력 게이트

`전체 검토 완료` 를 체크하면 그 시점 데이터가 **revision 스냅샷**으로 저장되고,
Excel 은 **스냅샷에서만** 생성됩니다. 라이브 데이터에서 바로 뽑지 않습니다.
출력은 발주처 파일을 복사한 뒤 데이터 영역만 바꾸므로 서식·필터·열너비·부속시트
5종과 표 하단 기술요구사항 Note 가 그대로 유지됩니다.

## 테스트

```bash
python3 -m pytest -q -m "not slow and not ui"   # 병합·충돌·스냅샷 규칙 (1초)
python3 -m pytest -q -m ui                      # 실제 브라우저 편집 시나리오 (7분)
python3 -m pytest -q                            # 전부, 결정론성 포함 (약 22분)
```

`-m ui` 는 `app/_data/app.db` 의 기존 분석을 재사용하므로 재분석하지 않습니다.
Playwright 가 필요합니다: `pip install playwright`.

## 구조

```
app/engine/   Phase 0 에서 검증된 검출 엔진 (spike/ 에서 git mv, 로직 변경 없음)
app/pipeline  엔진 호출 순서만 담당. 판정은 하지 않음
app/db        ai_values / user_values 분리 저장, revision 스냅샷
app/excel_out 발주처 워크북을 열어 데이터 영역만 교체
app/main      FastAPI: 업로드 / 진행률 SSE / 행 편집 / 스냅샷 / Excel
app/static    리뷰 UI (빌드 도구 없음)
spike/README.md  Phase 0 검증 기록 (수치·근거)
docs/design.md   설계안
```

## 성능 — 알고 있는 개선 여지 (미적용)

`app/engine/pidcache.py` 의 `segments()` 가 좌표를 표시공간으로 옮기려고 선분마다
`pymupdf.Point(...) * matrix` 를 만듭니다. 페이지당 15만~33만 선분이니 파이썬 객체가
페이지마다 30만~66만 개 생기고, 이것이 실행시간의 대부분입니다. 그런데 58장 중 56장은
회전이 0 이라 그 행렬이 **항등**이고, 곱셈이 아무것도 바꾸지 않습니다. 6페이지 실측:

| | 6페이지 합계 |
| --- | --- |
| 현재 `segments()` | 30.8s |
| 항등행렬이면 곱셈 생략 | **1.3s (24배)** |
| `get_cdrawings()` 로 다시 읽기 | 2.8s (11배) |

전체 실행 452초 중 약 265초가 여기이므로, 항등일 때만 생략하면 **3분대**로 내려갑니다.
회전된 2장(p7·p48)은 지금 경로를 그대로 씁니다. 결과는 비트 단위로 같아야 하지만
(항등행렬에서 `Point*m == Point`), 반환하는 Point 가 캐시 안의 객체 자체가 되므로
호출자가 제자리에서 고치지 않는다는 점만 확인하면 됩니다 — 현재 세 곳 모두 읽기만
합니다. **검출 로직 변경이 아니지만 아직 적용하지 않았습니다.**

## 알려진 범위

- **Description** 공란 — 배관 추적이 필요하며 Phase 2 입니다
- **Tag No.** 공란 — 도면 자체가 `.....` 로 미부여 상태입니다
- 마스터 Valve List 는 템플릿이 없어 출력에서 제외됩니다
