━━ 이 꾸러미는 무엇인가
   10 ~ 55 회차 누적입니다.  앞의 꾸러미(r41 · r44 · r48 · r50 · r52 · r53)를 따로
   넣을 필요 없습니다.  기준 커밋 aac64ba(회사 PC 가 마지막으로 맞춘 것) 이후
   바뀐 소스만 담았습니다.
   ★ 이번에 처음으로 **DXF 입력**이 들어갑니다.
   ★ 그래서 이번에는 **설치 파일(wheel)** 이 함께 갑니다 — 사내망에서 pip 로 받을
     수 없으므로, 이것을 넣지 않으면 DXF 가 돌지 않습니다.

   파일 셋(또는 넷)입니다
     PID_update_2026-09-21_r55.zip     ← 안내문 · 파일목록 · 3_덮어쓸파일.zip
     4_설치파일_wheels_part00.zip      ← ezdxf 계열 (도면을 **읽는** 데 필요)
     4_설치파일_wheels_part01.zip      ← matplotlib 계열 (화면에 **그리는** 데 필요)
   메일 한 통에 20MB 가 넘어 나눴습니다.  두 part 를 **같은 폴더**에 풀면 됩니다.

━━ ★ 크게 달라지는 것
   · 추출 정확도가 올랐습니다 — AL NOUF1 824행 → **1137행**
   · ★ **DXF 를 넣을 수 있습니다** (zip 하나 또는 .dxf 여러 장)
       CAD 에서 DXF 로 저장한 도면은 PDF 보다 훨씬 잘 읽힙니다.
       UAD 도면은 PDF 로 거의 못 읽던 장(p11~p15)이 DXF 로 **105행** 나옵니다
       (같은 다섯 장을 PDF 로 읽으면 1행입니다).  32장 전체로는 449행입니다.
   · 마크업 — 안 나온 것을 도면에서 직접 찍어 추가할 수 있습니다
     (다른 색으로 보이고, 발주처 양식 REMARK 열에도 나갑니다)
   · 피드백 내보내기 — 표시한 것을 zip 하나로
   · 프로젝트 완전 삭제 — 기록은 남기고 분석·행·업로드만 지웁니다
   · 입찰 / 실행 선택 — 업로드 전에 고릅니다 (안 고르면 도면을 보고 자동 판정)
   · 첫 화면에서 저장된 프로젝트를 바로 열기 (재분석 없이 1~3초)
   · 값을 고치면 저장되고 다른 팀원에게도 보입니다

━━ ★ DXF 를 쓸 때 알아 둘 것
   · CAD 에서 "다른 이름으로 저장 → AutoCAD 2018 DXF" 로 저장하시면 됩니다
     (2013 · 2010 · R12 도 읽힙니다)
   · 한 도면에 여러 장이면 **zip 으로 묶어** 올리면 됩니다.  .dxf 파일을 여러 개
     한꺼번에 골라 올려도 됩니다
   · ⚠ **PDF 를 CAD 로 가져와 만든 도면은 DXF 여도 잘 안 읽힙니다.**
     글자가 선으로 변해 있기 때문입니다 (UAD 32장 중 3장이 그렇습니다)
   · ⚠ **같은 프로젝트에 PDF 와 DXF 를 섞지 마세요.**  프로그램이 막습니다
   · DXF 에서 아직 안 되는 것 — Description · Typical 표식 · 마크업 제안값

━━ 넣기 전에 — 백업 (건너뛰지 마세요)
   cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
   mkdir "$env:USERPROFILE\Desktop\pid_backup_2026-09-21"
   Copy-Item app\_data\app.db* "$env:USERPROFILE\Desktop\pid_backup_2026-09-21\"
   Copy-Item app\_data\uploads "$env:USERPROFILE\Desktop\pid_backup_2026-09-21\" -Recurse
   확인 — 네 가지가 다 있어야 합니다: uploads · app.db · app.db-shm · app.db-wal

━━ 넣는 순서
   1. 쓰는 사람이 없는지 확인
   2. 서버 중지 — Ctrl + C
   3. ★ 설치 파일 넣기 (처음 한 번만)
        4_설치파일_wheels_part00.zip 과 part01.zip 을 **같은 폴더**에 풉니다.
        풀면 wheels_r55 폴더 하나가 되고 그 안에 .whl 이 10개 있습니다.
        cd C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool
        .\.venv\Scripts\python.exe -m pip install --no-index `
            --find-links <wheels_r55 폴더 경로> ezdxf matplotlib
        확인:
        .\.venv\Scripts\python.exe -c "import ezdxf, matplotlib; print('ok')"
        ※ "ok" 가 나와야 합니다.  numpy · packaging · typing_extensions 는 이미
          깔려 있어 담지 않았습니다 (9/3 이관 때 들어간 버전과 같습니다).
   4. 3_덮어쓸파일.zip 을 저장소 루트에 덮어쓰기 (같은 이름은 덮어씁니다)
   5. 삭제할 파일 없음 — 기준 aac64ba 이후 지워지거나 이름이 바뀐 파일이 없습니다
   6. 서버 시작
        $env:PYTHONUTF8 = "1"
        .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
   7. 브라우저에서 Ctrl + Shift + R

━━ 넣고 나서 확인
   1. 첫 화면에 기존 프로젝트가 보이고 클릭하면 열리는가
      (824행이 나옵니다 — 옛 분석본이라 정상입니다)
   2. 새로 분석하면 **1137행 · Q'ty 2140** (AL NOUF1 · 약 13분)
   3. ★ 업로드 화면 왼쪽에 **PDF / DXF** 고르는 칸이 있는가
      DXF 를 고르고 CAD 원본이 있는 도면을 한 장 올려 보세요
   ※ 824 → 1137 로 늘어나는 것이 정상입니다.  재분석해야 새 값이 적용됩니다

━━ ★ 메모리
   분석에 메모리를 많이 씁니다 (실측: AL NOUF1 PDF 4.9GB · 큰 PDF 7.5GB ·
   UAD DXF 32장 1.2GB — DXF 가 훨씬 가볍습니다).
   · 8GB 면 큰 PDF 도면은 매우 느리거나 실패할 수 있습니다.  16GB 이상 권합니다
   · 창을 여러 개 띄워 동시에 분석하지 마세요

━━ 팀원에게 부탁할 것
   1. 안 나온 계기·밸브가 보이면 [마크업] 을 켜고 드래그해 주세요
   2. SCOPE 가 비어 있으면 도면을 보고 채워 주세요
   3. 잘못 잡은 상자는 "오검출" 로 표시해 주세요.  지우지 마세요
   4. ★ CAD 원본이 있는 도면은 **DXF 로도 한 번** 넣어 보세요 — 어느 쪽이 더 잘
      읽히는지가 도면마다 다릅니다
   5. 한 도면을 다 보고 나면 [피드백 내보내기] 로 zip 을 받아 공유 폴더에 올려 주세요

━━ 아직 남은 것
   · 유닛 승수 — 도면에 표가 없으면 검토 화면에서 넣어야 합니다
   · DXF 에서 아직 안 되는 것 — Description · Typical · 마크업 제안값
   · p8 MOV (우리 6행 ↔ 발주처 5행) · PCV · PRV 일부 · RO — 실무 판단 대기
   · 획으로 그린 타이틀블록의 P&ID No. 사람 지정 — 화면 패널이 아직 없습니다
   · PV · LV · TV · FV 를 어느 이름으로 낼지 — 정해 주셔야 합니다

━━ ⚠ 회사 PC 에서 다시 재 주셔야 하는 것
   이 작업 환경에는 **발주처 xlsx 세 개와 SADARA · UAD 의 PDF 가 없습니다.**
   그래서 발주처 대조 정확도(축1 · 축2)와 그 두 도면의 행 수를 못 쟀습니다.
   회사 PC 에서
       python3 spike/regression_3p.py --write-baseline
   을 한 번 돌려 주시면 기준선이 실측으로 갱신됩니다.

━━ 되돌리려면
   1. 서버 중지 — Ctrl + C
   2. 백업한 app\_data 되돌리기
        Copy-Item "$env:USERPROFILE\Desktop\pid_backup_2026-09-21\app.db*" app\_data\ -Force
        Copy-Item "$env:USERPROFILE\Desktop\pid_backup_2026-09-21\uploads" app\_data\ -Recurse -Force
   3. 코드를 이전 커밋으로
        git checkout aac64ba -- app config docs spike tests conftest.py CLAUDE.md README.md
   4. 서버 시작 (위 6번)
   ※ 설치한 wheel 은 남아도 옛 코드에 해가 없습니다 — 옛 코드는 부르지 않습니다

━━ 문제가 생기면
   터미널 화면을 사진으로 찍어 둡니다.  화면의 "예외 원문 펼치기" 도 함께 찍어
   주세요.
