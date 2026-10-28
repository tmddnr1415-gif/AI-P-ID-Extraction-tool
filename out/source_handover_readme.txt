P&ID 추출 도구 — 개발 이관용 소스 ({DATE} · 기준 커밋 {HEAD} · 브랜치 {BRANCH} · 파일 {N}개)

이 zip 은 운영 폴더에 덮어쓰는 hotfix 꾸러미가 아닙니다.  회사 PC 에서 개발을 이어받을
"개발 폴더" 를 새로 만드는 데 씁니다.  운영 폴더(C:\Claude\PID — 부서원이 쓰는 서버)에 풀지 마세요.

폴더 배치
  C:\Claude\PID\        운영 (서버가 도는 곳 · app\_data\ 에 분석 기록)
  C:\Claude\PID_dev\    개발 (이 zip 을 풀 곳 · 회사 Claude 가 일하는 곳)

1. C:\Claude\PID_dev 폴더를 만들고 이 zip 을 그 안에 풉니다.
   (풀었을 때 C:\Claude\PID_dev\CLAUDE.md 가 보여야 합니다 — 한 겹 더 들어가 있으면 한 단계 위로 꺼내세요)

2. 명령 창(cmd)에서:
     cd /d C:\Claude\PID_dev
     git init
     git add -A
     git commit -m "이관 시점 {HEAD}"
   ※ git 이력은 없습니다.  그 전 이력은 CLAUDE.md 와 docs\ · out\ 의 보고서에 글로 남아 있습니다.
   ※ git 이 "Please tell me who you are" 라고 하면 한 번만:
        git config --global user.name "이름"
        git config --global user.email "메일"

3. 실행 환경 (오프라인 — 설치 파일은 운영 폴더의 wheels 를 빌려 씁니다):
     python -m venv .venv
     .venv\Scripts\python -m pip install --no-index --find-links C:\Claude\PID\wheels -r requirements-win.txt
     .venv\Scripts\python -m pip install --no-index --find-links C:\Claude\PID\wheels_r55 -r requirements-win-dxf.txt
     .venv\Scripts\python -m pip install --no-index --find-links C:\Claude\PID\wheels -r requirements-win-test.txt
   마지막 줄(pytest)은 개발 폴더에만 필요합니다.  playwright 에서 오류가 나면 무시해도 됩니다 (화면 시험용).

4. 도면 자료: C:\Claude\PID\data 를 C:\Claude\PID_dev\data 로 복사합니다.
     robocopy C:\Claude\PID\data C:\Claude\PID_dev\data /E
   이름 규칙은 CLAUDE.md 6절.  SADARA · UAD · TC2 · QFE PDF 가 다른 곳에 있으면 그것도 data\ 에 넣으세요.

5. 확인: .venv\Scripts\python -m pytest -q -m "not slow and not ui"
   (이 zip 을 Linux 에서 풀어 돌렸을 때 전부 통과 · 몇 건은 "건너뜀" 이 정상입니다)

6. 그 폴더에서 Claude Code 를 열고 첫 프롬프트를 넣습니다 (아래).

뺀 것 (용량 때문 · 다시 만들 수 있음):
  out\ 아래 zip · db · pdf · 그림(png/jpg) · 1MB 넘는 json(전량 분석 결과 덤프)
  app\_data\ · data\ · wheels\ (처음부터 저장소에 없음)

첫 프롬프트:
------------------------------------------------------------------
이 폴더(C:\Claude\PID_dev)는 P&ID 계기·밸브 추출 도구의 개발 폴더다.
다른 환경(Linux 클라우드)에서 개발하다 넘어왔다.
1. docs/state_and_roadmap.md 를 먼저, 그다음 CLAUDE.md 를 읽어라.
   §2 진행 원칙, §9 범용성 원칙, §8 대기 루프 규칙을 지켜라.
2. 먼저 빠른 시험(.venv\Scripts\python -m pytest -q -m "not slow and not ui")이
   이 PC(Windows)에서 통과하는지 확인하고, 실패하면 Windows 차이 때문인지 원인을 보고해라.
3. 이 PC 의 data\ 에는 발주처 xlsx 와 도면 PDF 가 있다. 그동안 못 쟀던 축1·축2 와
   SADARA·UAD 기준선을 spike/regression_3p.py 로 재고 결과를 보고해라.
   spike/baselines_3p.json 갱신은 나에게 확인받은 뒤에 해라.
4. 운영 폴더 C:\Claude\PID 는 직접 고치지 마라. 그 폴더의 app\_data\ 는 절대 지우거나 덮지 마라.
   운영 반영은 내가 지시할 때만 하고, 반영 뒤에는 서버를 다시 켜는 법을 알려 줘라.
5. Windows 도구가 읽는 파일(*.bat · requirements*.txt)에는 한글을 넣지 마라 (CLAUDE.md hotfix51·53).
6. 업데이트 전에 나에게 진행할지 물어봐라.
------------------------------------------------------------------
