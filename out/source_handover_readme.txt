P&ID 추출 도구 — 개발 이관용 소스 ({DATE} · 기준 커밋 {HEAD} · 브랜치 {BRANCH} · 파일 {N}개)

이 zip 은 운영 폴더에 덮어쓰는 hotfix 꾸러미가 아닙니다.  회사 PC 에서 개발을 이어받을
"개발 폴더" 를 새로 만드는 데 씁니다.  운영 폴더(지금 서버가 도는 곳)에 풀지 마세요.

1. 새 폴더를 만들고 이 zip 을 풉니다.  예) C:\Users\SAMSUNG\pid_dev\
2. 그 폴더에서 명령 창(또는 Git Bash):
     git init
     git add -A
     git commit -m "이관 시점 {HEAD}"
   ※ 이 zip 에는 git 이력이 없습니다.  그 전 이력은 CLAUDE.md 와 docs/·out/ 의 보고서에 글로 남아 있습니다.
3. 실행 환경:
     python -m venv .venv
     .venv\Scripts\pip install -r requirements.txt
4. data\ 폴더를 만들고 회사 PC 에 있는 도면 PDF · 발주처 xlsx 를 넣습니다 (이름 규칙 CLAUDE.md 6절).
5. 그 폴더에서 Claude Code 를 열고 첫 프롬프트를 넣습니다 (아래).

뺀 것 (용량 때문 · 다시 만들 수 있음):
  out/ 아래 zip · db · pdf · 그림(png/jpg) · 1MB 넘는 json(전량 분석 결과 덤프)
  app\_data\ · data\ (처음부터 저장소에 없음)
  → 그래서 "저장된 결과로 다시 채점" 하는 몇몇 시험은 건너뛰어집니다.  회사 PC 에서
    spike/regression_3p.py 를 한 번 돌리면 결과가 다시 생깁니다.

첫 프롬프트:
------------------------------------------------------------------
이 폴더는 P&ID 계기·밸브 추출 도구다. 다른 환경(Linux 클라우드)에서 개발하다 넘어왔다.
1. docs/state_and_roadmap.md 를 먼저, 그다음 CLAUDE.md 를 읽어라.
   §2 진행 원칙, §9 범용성 원칙, §8 대기 루프 규칙을 지켜라.
2. 먼저 빠른 시험(pytest -q -m "not slow and not ui")이 이 PC(Windows)에서 통과하는지
   확인하고, 실패하면 Windows 차이 때문인지 원인을 보고해라.
3. 이 PC 의 data\ 에는 발주처 xlsx 와 SADARA·UAD 등 PDF 가 있다. 그동안 못 쟀던
   축1·축2 와 SADARA·UAD 기준선을 spike/regression_3p.py 로 재고 결과를 보고해라.
   spike/baselines_3p.json 갱신은 나에게 확인받은 뒤에 해라.
4. 운영 중인 서버 폴더(C:\Users\SAMSUNG\.claude\pid\AI-P-ID-Extraction-tool)는
   직접 고치지 마라. 그 폴더의 app\_data\ 는 절대 지우거나 덮지 마라.
   운영 반영은 내가 지시할 때만 하고, 반영 뒤에는 서버를 다시 켜는 법을 알려 줘라.
5. 업데이트 전에 나에게 진행할지 물어봐라.
------------------------------------------------------------------
