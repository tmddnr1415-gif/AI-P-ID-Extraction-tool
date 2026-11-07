10회차 반영 안내 — AI-P-ID-Extraction-tool
=========================================================================

■ 이 회차에서 바뀐 것 (3줄)

  1. TW 15행과 벤더 공급분 204행이 리스트에 나옵니다 (824 → 1029행).
  2. SCOPE 열이 찹니다 — SCT / VENDOR(HRSG) 처럼, 이름은 그 장 NOTES 에서
     읽습니다.  밸브 TYPE 은 MOV(GLOBE) 로 표기됩니다 (판정값은 그대로).
  3. Description 이 비어 있던 밸브 39행이 그 라인에서 가장 가까운
     TO/FROM 문구로 찹니다 (등급 LOW — 확인 필요).


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

  ※ handover_10.zip 에는 app\_data\ 가 **한 파일도** 들어 있지 않습니다.
     그래도 백업은 하세요 — 되돌릴 길이 있어야 합니다.


■ 반영 절차

  1. 서버 중지            실행 중인 PowerShell 창에서 Ctrl+C
  2. 압축 해제(덮어쓰기)   handover_10.zip 을 저장소 루트에 풀기
                          (12개 파일, 저장소 루트 기준 상대경로 구조 그대로)
  3. 서버 재시작

       cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
       $env:PYTHONUTF8 = "1"
       .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

     (실행 정책 때문에 Activate.ps1 이 막혀 있으므로 venv 파이썬을 직접 부릅니다.)

  4. 브라우저에서 Ctrl+Shift+R  (app.js 가 바뀌었으므로 강제 새로고침 필수)


■ 반영 후 확인값 — 도면을 **다시 분석**한 뒤의 값입니다

     행 수     1029   (FIELD 885 / MOV 76 / PNEUMATIC 45 / BFV 23)
     Q'ty 합계 1911
     지문      3a57b6b2

  ※ 기존 분석 결과는 예전 값(824행 / 1595 / 91ba3e33)을 그대로 유지합니다.
     새 규칙은 새로 분석한 것부터 적용됩니다.
  ※ 지문은 리눅스에서 잰 값입니다.  Windows 에서 다르게 나오면
     docs\offline_setup_windows.md 의 확인 순서를 따르세요
     (행 수 → Q'ty → 등급 → 판정축 → 라이브러리 버전).

  빠르게 보는 법:
     · 그리드 Scope 열이 전부 차 있는지 (SCT / VENDOR / VENDOR(이름))
     · MOV 탭 Type 이 MOV(GLOBE) 형태인지
     · 등급 LOW 가 51행인지 (예전 12행)


■ 의존성 변경 여부

     없습니다.  추가로 보낼 wheel 이 없고, requirements-win.txt 도
     그대로입니다.  압축만 풀고 서버를 다시 켜면 됩니다.


■ 되돌리기

  세 가지가 전부 config 한두 줄입니다 (config\project_alnouf1.yaml):

     TW 를 다시 빼기        anchors 의 `TW: TW` 삭제 → `not_field: [TW]`
     벤더 공급분 다시 빼기   scope.exclusion_rules: glyph+text+box
     벤더 행 Description    scope.vendor_description: keep  (지금은 skip)

  코드를 통째로 되돌리려면 이전 파일 12개를 다시 덮으면 됩니다.


■ 아직 발주처 확인이 필요한 것 (9건)

     docs\round10_feedback.md 의 §10 표를 보세요.  특히 두 가지가
     정밀도를 84.1% 에서 70.5% 로 내렸고, 둘 다 "요구대로 냈지만
     발주처 리스트에는 없는" 항목입니다:

       · TW 15행       — CZE 에 TW 는 0행
       · 벤더 공급분 204행 — 넣어서 늘어난 정답이 1행, 늘어난 오답이 136행
