"""대시보드 운영 폴더용 꾸러미 — 메뉴 'ROOM SIZE 계산' · '도서검토' 가 여는 apps/ 파일 (hotfix117 · hotfix118 · 적용 단추 hotfix119).

대시보드(v16.43~)의 두 메뉴는 대시보드 폴더의 apps/space/index.html · apps/books/index.html 을 연다.  그 자리에
dashboard_apps/*/index.html (P&ID 서버 :8000 의 /space · /books/ 로 넘겨 주는 파일)을 넣는 zip 을 만든다.
대시보드 쪽 CLAUDE.md: 'ROOM SIZE 계산 · 도서검토 zip 은 이 세션에서 만든다 · 대시보드 zip 에서 apps/ 는 뺀다' (2026-10-25).
    python3 spike/pack_dashboard_apps.py --name hotfix118
"""
from __future__ import annotations

import argparse
import datetime as dt
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPS = ("space", "books")
README = """대시보드 메뉴 연결 파일 ({name}) — 대시보드 운영 폴더에 풉니다

무엇인가
  대시보드의 [ROOM SIZE 계산] · [도서검토] 메뉴는 대시보드 폴더 안의 apps\\space · apps\\books 를 엽니다.
  그 자리가 예전 화면이거나 비어 있어 최신 화면이 안 보이거나 실행되지 않았습니다.
  이 zip 의 두 파일은 메뉴를 누르면 P&ID 서버(같은 PC 포트 8000)의 화면을 띄웁니다 — P&ID 분석 · LOGIC 분석과 같은 방식입니다.
  화면과 저장은 전부 P&ID 서버가 하고, 대시보드는 불러오기만 합니다 (대시보드 코드는 바뀌지 않습니다).

넣는 법
  1. 이 zip 을 대시보드 운영 폴더(dashboard.html · start_server.bat 이 있는 폴더) 안에 풉니다.
     (윈도우 '압축 풀기' 가 zip 이름의 새 폴더를 만들어도 괜찮습니다.)
  2. 풀린 폴더의 apply_dashboard_apps.bat 을 더블클릭합니다.
     — 대시보드 폴더를 스스로 찾아 apps\\space\\index.html · apps\\books\\index.html 을 바꾸고 'OK' 두 줄을 보여 줍니다.
       못 찾으면 대시보드 폴더를 이 bat 위에 끌어다 놓거나 경로를 적으라고 묻습니다.  예전 파일은 index.html.before_hotfix119 로 남습니다.
  3. 대시보드에서 Ctrl+F5 → [ROOM SIZE 계산].  위 도구줄에 🧊 3D · ◧ 2D | 3D · ↗ 3D 새 창 단추가 보이면 된 것입니다.
     ([새 창으로 열기] 를 누르면 주소가 :8000/space 로 바뀝니다.)
  · P&ID 서버 꾸러미(PID_dev+ops_hotfix117 이상)가 운영 PID 에 적용돼 있어야 합니다.  P&ID 서버가 꺼져 있으면 화면이 그렇게 말합니다.

ROOM SIZE 계산 — 예전 자료
  대시보드 서버에 저장해 둔 프로젝트 · 저장본 · 노트는 첫 화면 [대시보드 자료 가져오기] 를 한 번 누르면 같은 ID 로 들어옵니다 (여러 번 눌러도 한 벌).
  브라우저에만 있던 미저장 작업은 옮겨지지 않으니, 넣기 전에 예전 화면에서 [서버에 저장] 하세요.

도서검토 — 처음 한 번 (서버 PC 에서)
  서버 PC 에서 대시보드를 열고 [도서검토] → [📚 도서관] → 도서 폴더 경로 예) D:\\계장도서 → [경로 저장] → [🔄 색인 갱신].
  (대시보드에서 색인을 만들어 두었어도 P&ID 서버에서 한 번 더 색인합니다.  그 뒤 부서원은 바로 검색합니다.)
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    out = ROOT / "out" / f"DASHBOARD_apps_{a.name}_{dt.date.today():%Y-%m-%d}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for app in APPS:
            z.write(ROOT / "dashboard_apps" / app / "index.html", f"apps/{app}/index.html")
        z.write(ROOT / "dashboard_apps" / "apply_dashboard_apps.bat", "apply_dashboard_apps.bat")
        z.writestr("1_먼저읽기_대시보드_메뉴연결.txt", README.format(name=a.name).replace("\n", "\r\n").encode("utf-8-sig"))
    with zipfile.ZipFile(out) as z:
        for app in APPS:
            assert z.read(f"apps/{app}/index.html") == (ROOT / "dashboard_apps" / app / "index.html").read_bytes()
        print(out, out.stat().st_size, "bytes ·", z.namelist())


if __name__ == "__main__":
    main()
