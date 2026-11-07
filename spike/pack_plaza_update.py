"""부서 대시보드용 가상 광장 업데이트 zip 을 만든다.

    python3 spike/pack_plaza_update.py --rev 1

zip 을 대시보드 폴더에 그대로 풀면 `plaza\\` 하나가 생기거나 갱신된다.  역할 · 얼굴 파일
(`plaza\\plaza_data\\`)과 로그(`plaza\\logs\\`)는 zip 에 없으므로 덮이지 않는다.
만든 뒤 임시 폴더에 풀어 자가 점검(selftest)까지 돌린다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAND = ROOT / "out" / "plaza_handover"

RUN_BAT = r"""@echo off
rem Virtual plaza server for the department dashboard (port 8100).
rem Keeps running: if the server stops it starts again after 10 seconds.
rem Close this window to stop it.  Never kill python by name - the dashboard is python too.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
set PORT=8100
if not "%~1"=="" set PORT=%~1
title Plaza server - port %PORT%
:loop
echo [%date% %time%] Starting plaza server on port %PORT% (log: plaza\logs\plaza_server.log)
python "%~dp0plaza_server.py" --port %PORT% --data "%~dp0plaza_data" --log "%~dp0logs\plaza_server.log"
echo [%date% %time%] Plaza server stopped. Restarting in 10 seconds...
timeout /t 10 /nobreak >nul
goto loop
"""

RESTART_BAT = r"""@echo off
rem Restart the plaza server after applying an update.
rem Stops only the program listening on port 8100 (by PID).  run_plaza_server.bat brings it back.
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
python "%~dp0plaza_restart.py" 8100
pause
"""

README = """가상 광장 업데이트 — {name}  (만든 날 {created})
==================================================================

부서 대시보드 첫 화면 '최근 변경 이력' 아래에 들어가는 가상 광장(바람의나라 부여성 남쪽 느낌)입니다.
캐릭터를 방향키로 움직이고 · Enter 로 말하고 · Space 로 목검을 휘두릅니다.
얼굴은 각자 바꾸고, 머리 장식(그룹장 왕관 · 유닛장 사모 · 부서원 관모 · 운영자 노비 차림)은 운영자가 정합니다.

이 zip 에 든 것
  plaza\\                    광장 서버와 화면 (pip 필요 없음 — 표준 파이썬만)
    run_plaza_server.bat     서버 켜기 (포트 8100 · 멈추면 10초 뒤 다시 켬 · 창을 닫으면 꺼짐)
    restart_plaza_server.bat 업데이트를 푼 뒤 서버를 새 코드로 다시 켜기
    selftest.py              자가 점검 — "모두 통과" 가 나오면 정상
    _update.json             이 업데이트의 이름 · 날짜 (광장 서버의 /version 이 이 값을 보여 줍니다)
  dashboard_snippet\\
    plaza_card.html          dashboard.html 에 넣을 조각 (접기 단추 · 광장 카드 · 서버 확인)
    PROMPT_대시보드_Claude.txt  대시보드 Claude Code 에 붙여 넣을 지시문
  screens\\                  화면 예시 (참고용 — 대시보드 폴더에 넣지 않아도 됩니다)
  README_인계.md             기능 · 규칙 · 앞으로 할 만한 것 전문

처음 넣을 때 (한 번)
  1. 이 zip 을 대시보드 폴더(예: C:\\Claude\\Dashboard)에 풉니다 → plaza\\ 폴더가 생깁니다.
  2. 명령창에서  python plaza\\selftest.py   → 마지막 줄 "모두 통과" 확인.
  3. plaza\\run_plaza_server.bat 을 더블클릭해 켭니다.
     (처음 켜면 plaza\\plaza_data\\roles.json 이 빈 틀로 생깁니다)
  4. plaza\\plaza_data\\roles.json 의 "operators": [] 안에 운영자 이름 하나를 적습니다
     예)  "operators": ["홍길동"]     — 이름은 대시보드 로그인 이름 그대로.
     그 뒤로는 운영자가 광장 화면의 [역할 지정] 에서 그룹장 · 유닛장을 바꿉니다.
  5. 대시보드 화면 쪽은 dashboard.html 을 고쳐야 합니다 (이 zip 이 직접 고치지 않습니다 —
     대시보드 파일이 이 개발 환경에 없기 때문입니다).
     dashboard_snippet\\PROMPT_대시보드_Claude.txt 를 대시보드 Claude Code 에 붙여 넣으면
     plaza_card.html 조각을 넣어 줍니다.  손으로 넣어도 됩니다 (조각 맨 위 설명대로).
  6. 다른 PC 에서 보려면 방화벽에 8100 을 열어야 할 수 있습니다 (사내망에서만 열립니다).
  7. 서버 PC 가 켜질 때 함께 켜려면 run_plaza_server.bat 을 작업 스케줄러(로그온 시)에 넣습니다.

다음 업데이트를 받았을 때
  1. 새 zip 을 같은 대시보드 폴더에 풀고 "덮어쓰기" — 역할 · 얼굴 파일(plaza_data)은 zip 에 없어 그대로 남습니다.
  2. plaza\\restart_plaza_server.bat 을 더블클릭 → "다시 떴습니다 — 적용된 업데이트: ..." 가 보이면 끝.
  3. 브라우저에서 대시보드를 새로고침(Ctrl+F5).

알아 둘 것
  - 대화 · 위치는 서버 메모리에만 있어 서버를 다시 켜면 광장이 빕니다 (역할 · 얼굴은 남습니다).
  - 서버를 끄는 것은 run_plaza_server.bat 창을 닫는 것입니다.  python 을 이름으로 한꺼번에 끄지 마세요
    (대시보드 서버도 python 입니다).
  - 문제가 생기면 plaza\\logs\\plaza_server.log 를 보세요.
"""

PROMPT = """첨부한 업데이트 zip 은 부서원용 가상 광장(바람의나라 '부여성 남쪽' 느낌의 도트 메타버스)이다.
광장 서버는 dashboard 폴더의 plaza\\ 에 이미 풀려 있고 plaza\\run_plaza_server.bat 으로 포트 8100 에서 돈다
(표준 라이브러리만 — pip 금지 규칙 그대로).  너는 dashboard.html 쪽만 고친다.  먼저 plaza 폴더 옆의
README_인계.md 와 dashboard_snippet\\plaza_card.html 을 끝까지 읽어라.

1. 메뉴 항목은 만들지 않는다.  홈 화면 '최근 변경 이력' 카드를 반으로 접을 수 있게 한다
   (기본 접힘 · 단추 "펼치기 ▾ / 반으로 접기 ▴" · localStorage 로 기억).
2. 그 카드 바로 아래 '가상 광장' 카드에 iframe 하나 —
   <같은 호스트>:8100/plaza?embed=1&user=<localStorage dept-dashboard-user 를 encodeURIComponent>.
   띄우기 전에 /version 을 3초 안에 fetch 해 보고 실패하면 "가상 광장 서버가 꺼져 있습니다" 한 줄.
   iframe 높이 약 470px · 테두리 없음 · sandbox 쓰지 않음.
3. 홈을 다시 그려도 iframe 을 새로 만들지 않는다 (새로 만들면 캐릭터가 나갔다 다시 들어온다).
   plaza_card.html 의 plazaMount() 를 그대로 쓰거나 같은 규칙으로 짠다.  HIST_SELECTOR 는 실제 목록 요소로.
4. 사람이 적은 글을 HTML 로 넣지 않는다 (textContent) · prompt/confirm/alert 를 쓰지 않는다.
5. 배포 전 운영 폴더의 dashboard.html 을 deploy_backup\\ 에 백업하고 APP_VERSION 을 올린다.
   이 작업으로 바뀌는 파일은 dashboard.html 하나여야 한다.
6. 고친 뒤 실제 브라우저로 두 사람 이상 띄워 걷기(방향키) · Enter 대화 · Space 공격 · 얼굴 바꾸기와
   '최근 변경 이력' 접기/펼치기를 확인하고 스크린샷을 남긴다.
"""


def crlf_ascii(text: str) -> bytes:
    text.encode("ascii")                       # 배치 파일은 ASCII 만 (cmd 가 UTF-8 을 줄 가운데부터 읽는다)
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("ascii")


def build(rev: int) -> Path:
    created = time.strftime("%Y-%m-%d %H:%M")
    name = f"plaza-update-{rev}"
    try:
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                                text=True).stdout.strip()
    except OSError:
        commit = ""
    stamp = {"name": name, "rev": rev, "created": created, "base_commit": commit}
    out = ROOT / "out" / f"Dashboard_plaza_update_{rev}_{time.strftime('%Y-%m-%d')}.zip"
    files: dict[str, bytes] = {
        "1_먼저읽기.txt": README.format(name=name, created=created).encode("utf-8"),
        "README_인계.md": (HAND / "README_인계.md").read_bytes(),
        "plaza/plaza_server.py": (HAND / "plaza_server.py").read_bytes(),
        "plaza/plaza_restart.py": (HAND / "plaza_restart.py").read_bytes(),
        "plaza/selftest.py": (HAND / "selftest.py").read_bytes(),
        "plaza/run_plaza_server.bat": crlf_ascii(RUN_BAT),
        "plaza/restart_plaza_server.bat": crlf_ascii(RESTART_BAT),
        "plaza/_update.json": json.dumps(stamp, ensure_ascii=False, indent=1).encode("utf-8"),
        "dashboard_snippet/plaza_card.html": (HAND / "dashboard_snippet" / "plaza_card.html").read_bytes(),
        "dashboard_snippet/PROMPT_대시보드_Claude.txt": PROMPT.encode("utf-8"),
    }
    for n in ("plaza.html", "plaza.js", "plaza.css"):      # 화면은 저장소의 원본에서 (P&ID 서버 판과 같은 파일)
        files[f"plaza/static/{n}"] = (ROOT / "app" / "static" / n).read_bytes()
    for png in sorted((HAND / "screens").glob("*.png")):
        files[f"screens/{png.name}"] = png.read_bytes()
    bad = [k for k in files if "plaza_data" in k or "_data/" in k or k.startswith("data/")]
    assert not bad, bad
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in files.items():
            z.writestr(k, v)
    return out


def verify(zpath: Path) -> bool:
    tmp = Path(tempfile.mkdtemp(prefix="plaza_update_check_"))
    try:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(tmp)
        ok = True
        for bat in (tmp / "plaza").glob("*.bat"):
            b = bat.read_bytes()
            good = b.isascii() and b"\r\n" in b and b"\n" not in b.replace(b"\r\n", b"") and b"chcp" not in b.lower()
            print(("통과 " if good else "실패 ") + f"배치 파일 ASCII · CRLF · chcp 없음 — {bat.name}")
            ok &= good
        r = subprocess.run([sys.executable, "-I", str(tmp / "plaza" / "selftest.py")], capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:])
        ok &= r.returncode == 0
        sys.path.insert(0, str(tmp / "plaza"))
        import plaza_restart
        sample = ("  TCP    0.0.0.0:8100           0.0.0.0:0              LISTENING       4120\n"
                  "  TCP    [::]:8100              [::]:0                 \xbc\xf6\xbd\xc5 \xb4\xeb\xb1\xe2  4120\n"
                  "  TCP    10.0.0.5:8100          10.0.0.9:51000         ESTABLISHED     4120\n"
                  "  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       777\n")
        good = plaza_restart.listening_pids(sample, 8100) == {4120}
        print(("통과 " if good else "실패 ") + "다시 켜기 — 8100 을 잡은 PID 하나만 (대시보드 8080 은 안 건드림)")
        ok &= good
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", type=int, default=1)
    a = ap.parse_args()
    z = build(a.rev)
    print(z, z.stat().st_size, "bytes")
    sys.exit(0 if verify(z) else 1)
