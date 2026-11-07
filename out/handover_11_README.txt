11회차 반영 안내 — AI-P-ID-Extraction-tool
=========================================================================

★ 이 꾸러미는 10회차 + 11회차 **누적**입니다.
  회사 PC 에는 10회차가 반영돼 있지 않으므로(현재 커밋 aac64ba),
  handover_10 을 따로 넣을 필요가 없습니다.  이것 하나만 푸시면 됩니다.


■ 10회차에서 바뀐 것 (3줄)

  1. TW 15행과 벤더 공급분 204행이 리스트에 나옵니다 (824 → 1029행).
  2. SCOPE 열이 생겼습니다 — SCT / VENDOR(HRSG) 처럼, 이름은 그 장 NOTES
     원문에서 읽습니다.  밸브 TYPE 은 MOV(GLOBE) 로 표기됩니다.
  3. Description 이 비어 있던 밸브 39행이 그 라인에서 가장 가까운
     TO/FROM 문구로 찼습니다 (등급 LOW — 확인 필요).


■ 11회차에서 바뀐 것 (3줄)

  1. 밸브 144행의 SCOPE 가 찼습니다 (SCT 113 · VENDOR(이름) 31 · 공란 0).
     별표가 밸브 몸체가 아니라 액추에이터 심볼 위에 찍히는 것을 반영했습니다.
  2. ★ 발주처 양식 Excel 이 이제 SCOPE=SCT 만 담습니다.
     CZE 885 → 667 · CZH 76 → 66 · CZI 23 → 22.
  3. 정확도 측정축이 둘이 됐습니다 — 전량 70.5% · SCT 전용 86.8%.
     (개발자용 스크립트입니다.  화면에는 나오지 않습니다.)


■ ★ 팀원 안내 문구

  발주처 양식 Excel 이 이제 SCT 공급분만 담습니다.
  벤더 공급분(204행)과 TW 는 **화면에서는 그대로 보이고 Excel 에는
  나가지 않습니다.**  화면·검토 UI 는 1029행 전량을 유지합니다.
  어느 행이 왜 빠졌는지는 SCOPE 열과 근거 패널이 말합니다.
  빠진 행 수는 Excel 내보내기 zip 의 MANIFEST.json 에 적힙니다.


■ ★ 기존 프로젝트는 **다시 분석해야** 새 값이 나옵니다

  저장된 예전 분석에는 SCOPE 열 자체가 없습니다.  그 상태로 Excel 을 내면
  옛 행들은 "판정한 적 없음"으로 보아 **그대로 담깁니다** (빈 파일이 되지
  않도록 일부러 그렇게 했습니다).  즉 필터가 걸리지 않은 옛 결과가 나갑니다.

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

  ※ handover_11.zip 에는 app\_data\ 가 **한 파일도** 들어 있지 않습니다.
     그래도 백업은 하세요 — 되돌릴 길이 있어야 합니다.


■ 반영 절차

  1. 서버 중지            실행 중인 PowerShell 창에서 Ctrl+C
  2. 압축 해제(덮어쓰기)   handover_11.zip 을 저장소 루트에 풀기
                          (16개 파일, 저장소 루트 기준 상대경로 구조 그대로)
  3. 서버 재시작

       cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
       $env:PYTHONUTF8 = "1"
       .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

     (실행 정책 때문에 Activate.ps1 이 막혀 있으므로 venv 파이썬을 직접 부릅니다.)

  4. 브라우저에서 Ctrl+Shift+R  (app.js 가 바뀌었으므로 강제 새로고침 필수)
  5. 도면을 **다시 분석**  (위 "기존 프로젝트는 다시 분석해야" 참조)


■ 반영 후 확인값 — 다시 분석한 뒤의 값입니다

     행 수     1029   (Field 885 / MOV 76 / Pneumatic 45 / BFV 23)
     Q'ty 합계 1911
     지문      69ad281f

  ※ 회사 PC 는 지금까지 824행이었으므로 1029 로 늘어나는 것이 정상입니다.
  ※ 지문은 리눅스에서 잰 값입니다.  Windows 에서 다르게 나오면
     docs\offline_setup_windows.md 의 확인 순서를 따르세요
     (행 수 → Q'ty → 등급 → 판정축 → 라이브러리 버전).

  빠르게 보는 법:
     · 그리드 SCOPE 열이 **밸브 행까지** 전부 차 있는지
     · MOV 탭 Type 이 MOV(GLOBE) 형태인지
     · Excel 출력 후 CZE 행수가 667 인지 (화면은 885)


■ 의존성 변경 여부

     없습니다.  추가로 보낼 wheel 이 없고, requirements-win.txt 도
     그대로입니다.  압축만 풀고 서버를 다시 켜면 됩니다.


■ 되돌리기

  발주처 양식 필터를 끄려면 app\excel_out.py 의 `in_client_scope` 가
  항상 True 를 돌려주게 하면 됩니다 (한 줄).
  TW · 벤더 계상은 config\project_alnouf1.yaml 에서:
     TW 를 다시 빼기        anchors 의 `TW: TW` 삭제 → `not_field: [TW]`
     벤더 공급분 다시 빼기   scope.exclusion_rules: glyph+text+box


■ 아직 발주처 확인이 필요한 것

     docs\round11_scope_axis.md §7 (8건) · docs\round10_feedback.md §10 (9건).
     특히 화면의 **오버레이 색**이 이번 회차 이후 사실과 어긋납니다 —
     SCT 행을 "공급자 인터페이스 구간"으로 칠합니다.  다음 회차에서
     범례 색상 설명과 함께 고칩니다 (docs\round11_scope_axis.md §6-2).
