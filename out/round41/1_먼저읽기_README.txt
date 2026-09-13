━━ 이 꾸러미는 무엇인가
   10 ~ 41 회차 누적입니다.  앞의 꾸러미(r17~r37)를 따로 넣을 필요 없습니다.
   기준 커밋 aac64ba(회사 PC 가 마지막으로 맞춘 것) 이후 바뀐 소스만 담았습니다.

━━ ★ 크게 달라지는 것
   · 추출 정확도가 올랐습니다 — 당사 공급분 기준 정밀도 84.1% → 94.4%
   · 발주처 양식이 전량(1037행)을 담습니다. 벤더 공급분도 포함됩니다
     (SCT 가 Bulk material 을 공급하므로 물량 산출이 필요합니다)
     SCT 만 담으려면 config/project_alnouf1.yaml 의 client_form.scope_filter 를 sct 로 바꿉니다
   · 첫 화면에서 저장된 프로젝트를 클릭해 바로 열 수 있습니다 (재분석 불필요, 1~3초)
   · 결과 화면에서 첫 화면으로 돌아가는 버튼이 생겼습니다
   · 값을 고치면 저장되고 다른 팀원에게도 보입니다. 처음 고칠 때 이름을 묻습니다
   · 분석 기록을 삭제할 수 있습니다 — 되돌릴 수 없으니 자기가 만든 것만 지우세요
   · SCOPE 열이 공급 주체를 구분합니다 (SCT / VENDOR(이름) / VENDOR)
   · 분석이 실패하면 어디서 왜 멈췄는지 말합니다
   · ★ 업로드 전에 입찰 / 실행을 고를 수 있습니다
     입찰 = 태그가 인쇄되지 않은 도면 · 실행 = 태그가 인쇄된 도면
     안 고르면 도면을 보고 자동 판정합니다
   · 파선으로 그린 계기 버블(벤더 스키드 안)도 행이 됩니다 — 검토 사유 "버블이 파선" 으로 올라옵니다

━━ ★ 다른 프로젝트 도면에 대해
   AL NOUF1 외의 도면(다른 종이 크기 · 다른 회사 양식)도 분석됩니다.
   한 파일에 회사 양식이 둘 이상 섞여 있어도 장마다 읽습니다.
   다만 아직 식별률이 낮습니다 — 도면틀 치수 일부가 AL NOUF1 기준이기 때문입니다.
   지금 그것을 하나씩 그 도면에서 읽도록 바꾸는 중입니다.

━━ ★ 메모리 — 반드시 읽으세요
   분석에 메모리를 많이 씁니다 (실측: AL NOUF1 {{RSS_NOUF1}}GB · 큰 도면 최대 {{RSS_TC2}}GB).
   · 이 PC 메모리가 8GB 면 큰 도면은 매우 느리거나 실패할 수 있습니다
   · 창을 여러 개 띄워 동시에 분석하지 마세요 — 프로그램은 하나씩 돌립니다
   · 분석 중에는 다른 무거운 프로그램을 닫아 두세요
   {{MEM_NOTE}}

━━ 넣기 전에 — 백업 (건너뛰지 마세요)
   cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
   mkdir "$env:USERPROFILE\Desktop\pid_backup_2026-09-13"
   Copy-Item app\_data\app.db* "$env:USERPROFILE\Desktop\pid_backup_2026-09-13\"
   Copy-Item app\_data\uploads "$env:USERPROFILE\Desktop\pid_backup_2026-09-13\" -Recurse
   확인 — 네 가지가 다 있어야 합니다: uploads · app.db · app.db-shm · app.db-wal

━━ 넣는 순서
   1. 쓰는 사람이 없는지 확인
   2. 서버 중지 — Ctrl + C
   3. 3_덮어쓸파일.zip 을 저장소 루트에 덮어쓰기 (같은 이름은 덮어씁니다)
   4. 삭제할 파일 없음 (기준 aac64ba 이후 지워지거나 이름이 바뀐 파일이 없습니다)
   5. 서버 시작
        cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
        $env:PYTHONUTF8 = "1"
        .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   6. 브라우저에서 Ctrl + Shift + R

━━ 넣고 나서 확인
   1. 첫 화면에 기존 프로젝트가 보이는가
   2. 클릭해서 열리는가 — 824행이 나옵니다 (옛 분석본이라 정상)
   3. 새로 분석하면 1037행 · 약 {{MIN_NOUF1}}분
   ※ 824 → 1037 로 늘어나는 것이 정상입니다
   ※ 재분석해야 새 값이 적용됩니다

━━ 아직 남은 것 (물어보실 수 있어 적어 둡니다)
   · 같은 도면번호를 두 장이 쓰는 건 16행 — 어느 장이 유효한지 실무 판단 대기
   · PI 10행 (00PAB10 세 장) — 발주처 회신 대기
   · p8 MOV — 우리 6행 ↔ 발주처 CZH 5행
   · p17 PRV · p12 PCV — 별도 회차
   · AIT — 발주처 리스트에 A 계열이 0행이라 미적용
   · 미판정 심볼 — 등록 화면에서 사람이 지정합니다
   · 유닛 승수 — 도면에 표가 없으면 검토 화면에서 넣어야 합니다
   · 파선 버블의 뜻(벤더인가) — 범례가 정의하지 않아 검토 사유로만 올라옵니다

━━ 되돌리려면
   1. 서버 중지 — Ctrl + C
   2. 백업한 app\_data 되돌리기
        Copy-Item "$env:USERPROFILE\Desktop\pid_backup_2026-09-13\app.db*" app\_data\ -Force
        Copy-Item "$env:USERPROFILE\Desktop\pid_backup_2026-09-13\uploads" app\_data\ -Recurse -Force
   3. 코드를 이전 커밋으로
        git checkout aac64ba -- app config docs spike tests conftest.py CLAUDE.md README.md
   4. 서버 시작 (위 5번)

━━ 문제가 생기면
   터미널 화면을 사진으로 찍어 둡니다.  화면의 "예외 원문 펼치기" 도 함께 찍어 주세요.
