12회차 반영 안내 — AI-P-ID-Extraction-tool
=========================================================================

★ 이 꾸러미는 10 + 11 + 12회차 **누적**입니다.
  회사 PC 는 아직 aac64ba 이므로, handover_10 · handover_11 을 따로 넣을
  필요가 없습니다.  이것 하나만 풀면 됩니다.


■ 10회차에서 바뀐 것 (3줄)

  1. TW 15행과 벤더 공급분 204행이 리스트에 나옵니다 (824 → 1029행).
  2. SCOPE 열이 생겼습니다 — SCT / VENDOR(HRSG) 처럼, 이름은 그 장 NOTES
     원문에서 읽습니다.  밸브 TYPE 은 MOV(GLOBE) 로 표기됩니다.
  3. Description 이 비어 있던 밸브 39행이 그 라인에서 가장 가까운
     TO/FROM 문구로 찼습니다 (등급 LOW — 확인 필요).


■ 11회차에서 바뀐 것 (3줄)

  1. 밸브 144행의 SCOPE 가 찼습니다 (SCT 113 · VENDOR(이름) 31 · 공란 0).
  2. ★ 발주처 양식 Excel 이 SCOPE=SCT 만 담습니다.
     CZE 885 → 667 · CZH 76 → 66 · CZI 23 → 22.
  3. 정확도 측정축이 둘이 됐습니다 — 전량 70.5% · SCT 전용 86.8%.
     (개발자용 스크립트입니다.  화면에는 나오지 않습니다.)


■ 12회차에서 바뀐 것 — **화면만** 고쳤습니다 (5줄)

  ※ 검출·수량·판정은 한 줄도 건드리지 않았습니다.
     지문 69ad281f · 1029행 · Q'ty 1911 이 그대로이고,
     1029행 전수 대조에서 **움직인 칸이 0** 입니다.

  1. ★ 근거 패널이 사실대로 말합니다.  전에는 벤더 행에도 "이 행은
     리스트에 포함됩니다" 라고 썼습니다 — 그 말을 믿고 Excel 을 열면
     그 행이 없었습니다.  이제 세 줄로 나눕니다:
         공급 주체    VENDOR 공급 — HRSG
         추출 결과    이 행은 추출 결과에 있습니다
         발주처 양식  나가지 않습니다 — 발주처 양식은 SCT 만 담습니다
  2. 도면 위 색 범례의 라벨과 숫자가 맞습니다 (SCT 공급 범위 /
     VENDOR 공급 (BM 당사) / 판정 없음 / 검토 필요).  전에는 라벨이
     말하는 것과 세는 것이 달랐습니다.
  3. SCOPE 열이 더 이상 잘리지 않습니다
     (VENDOR(SEAWATER INTAKE FACILITY SUPPLIER) 40자가 그대로 보이고,
      마우스를 올리면 전문이 뜹니다).  행 높이는 그대로입니다.
  4. ★ 분석 진행 화면이 실제로 움직입니다.  전에는 두 구간(약 95초 +
     129초)에서 화면이 멈춰 있었습니다.  이제 장마다 진행이 오르고,
     무엇을 하는 중인지 · 몇 번째 장인지 · 경과 시간이 보입니다.
     **[취소] 버튼**이 생겼습니다.
  5. 도면을 **마우스로 끌어서 이동**할 수 있습니다 (드래그 팬).
     확대·선택·오버레이는 그대로이고, 짧게 누르면 예전처럼 계기 선택입니다.


■ ★ 취소를 눌러도 안전합니다 (확인한 사실)

  분석 중에 취소하면 **아무것도 저장되지 않습니다** — 행 0 · 안정 ID 0 ·
  리비전 소비 0.  즉 Rev.B 를 분석하다 취소해도 Rev.B 번호가 없어지지
  않고, 다음에 다시 분석하면 그대로 Rev.B 입니다.
  (행을 쓰는 곳과 ID 를 주는 곳이 분석이 끝난 뒤에만 돌기 때문입니다.)


■ ★ 팀원 안내 문구

  발주처 양식 Excel 은 SCT 공급분만 담습니다.  벤더 공급분(204행)과 TW 는
  **화면에는 그대로 보이고 Excel 에는 나가지 않습니다.**
  어느 행이 왜 빠졌는지는 이제 **근거 패널 세 줄**이 그대로 말해 줍니다.
  분석이 끝나면 완료 화면이 "추출 1029 / 양식에 나감 780 / 빠짐 249" 를
  공급자별로 보여 줍니다.


■ ★ 기존 프로젝트는 **다시 분석해야** 새 값이 나옵니다

  저장된 예전 분석에는 SCOPE 열 자체가 없습니다.  그 상태로 Excel 을 내면
  옛 행들은 "판정한 적 없음"으로 보아 **그대로 담깁니다** (빈 파일이 되지
  않도록 일부러 그렇게 했습니다).

  구분하는 법: 내보낸 zip 의 MANIFEST.json 에서
      "legacy_no_scope_rows": 0   → 새 코드로 분석한 결과. 필터가 걸림
      "legacy_no_scope_rows": 900 → 옛 결과. 다시 분석하세요

  다시 분석은 화면 오른쪽 위 [재분석] 버튼입니다.  사람이 고친 칸은
  그대로 보존됩니다.


■ 반영 전 백업 (반드시 먼저)

  PowerShell 에서:

    cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
    $stamp = Get-Date -Format "yyyyMMdd_HHmm"
    New-Item -ItemType Directory -Path "..\backup_$stamp" | Out-Null
    Copy-Item app\_data\app.db      "..\backup_$stamp\" -ErrorAction Stop
    Copy-Item app\_data\app.db-wal  "..\backup_$stamp\" -ErrorAction SilentlyContinue
    Copy-Item app\_data\app.db-shm  "..\backup_$stamp\" -ErrorAction SilentlyContinue
    Copy-Item app\_data\uploads     "..\backup_$stamp\uploads" -Recurse -ErrorAction SilentlyContinue
    dir "..\backup_$stamp"

  ※ handover_12.zip 에는 app\_data\ 가 **한 파일도** 들어 있지 않습니다.
     그래도 백업은 하세요 — 되돌릴 길이 있어야 합니다.


■ 반영 절차

  1. 서버 중지            실행 중인 PowerShell 창에서 Ctrl+C
  2. 압축 해제(덮어쓰기)   handover_12.zip 을 저장소 루트에 풀기
                          (20개 파일, 저장소 루트 기준 상대경로 구조 그대로)
  3. 서버 재시작

       cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
       $env:PYTHONUTF8 = "1"
       .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

     (실행 정책 때문에 Activate.ps1 이 막혀 있으므로 venv 파이썬을 직접 부릅니다.)

  4. 브라우저에서 Ctrl+Shift+R
     ★ 이번 회차는 app.js · index.html · styles.css 가 **셋 다** 바뀌었으므로
       강제 새로고침이 반드시 필요합니다.  안 하면 진행 화면과 취소 버튼이
       나타나지 않습니다.
  5. 도면을 **다시 분석**  (위 "기존 프로젝트는 다시 분석해야" 참조)


■ 반영 후 확인값 — 다시 분석한 뒤의 값입니다

     행 수     1029   (Field 885 / MOV 76 / Pneumatic 45 / BFV 23)
     Q'ty 합계 1911
     지문      69ad281f      ← 11회차와 **같습니다** (화면만 고쳤으므로)

  ※ 회사 PC 는 지금까지 824행이었으므로 1029 로 늘어나는 것이 정상입니다.
  ※ 지문은 리눅스에서 잰 값입니다.  Windows 에서 다르게 나오면
     docs\offline_setup_windows.md 의 확인 순서를 따르세요
     (행 수 → Q'ty → 등급 → 판정축 → 라이브러리 버전).

  화면에서 빠르게 보는 법:
     · 분석을 걸어 두고 진행 줄이 **장마다 오르는지** (멈춰 있으면 실패)
     · 벤더 행을 눌러 근거 패널에 "발주처 양식 … 나가지 않습니다" 가 뜨는지
     · SCOPE 열의 VENDOR(SEAWATER INTAKE FACILITY SUPPLIER) 가 안 잘리는지
     · 도면을 마우스로 끌면 움직이는지


■ 의존성 변경 여부

     없습니다.  추가로 보낼 wheel 이 없고, requirements-win.txt 도
     그대로입니다.  압축만 풀고 서버를 다시 켜면 됩니다.


■ 되돌리기

  화면만 되돌리려면 app\static\ 세 파일(app.js · index.html · styles.css)을
  이전 것으로 되돌리면 됩니다.  파이썬 쪽은 그대로 둬도 동작합니다.
  발주처 양식 필터를 끄려면 app\excel_out.py 의 `in_client_scope` 가
  항상 True 를 돌려주게 하면 됩니다 (한 줄).
  TW · 벤더 계상은 config\project_alnouf1.yaml 에서:
     TW 를 다시 빼기        anchors 의 `TW: TW` 삭제 → `not_field: [TW]`
     벤더 공급분 다시 빼기   scope.exclusion_rules: glyph+text+box


■ 아직 발주처 · 실무 판단이 필요한 것

     docs\round12_ui.md §2 (오버레이 주황색 `#ff9f0a` 는 대비 미달이지만
       발주처가 이미 본 색이라 **바꾸지 않았습니다**)
     docs\round12_annotation_design.md (도면 주석 기능 — 리비전 승계 방식과
       작성자 표기 두 문항에 답이 서면 그대로 구현합니다.  이번 회차는
       설계안만 냈습니다)
     docs\round11_scope_axis.md §7 (8건) · docs\round10_feedback.md §10 (9건)
