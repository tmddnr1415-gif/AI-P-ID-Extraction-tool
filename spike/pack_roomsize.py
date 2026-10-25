"""ROOM SIZE 계산 — 대시보드 운영 폴더용 꾸러미 (hotfix117).

대시보드 메뉴 'ROOM SIZE 계산' 은 대시보드 폴더의 apps/space/index.html 을 연다.  그 파일을
dashboard_apps/space/index.html (P&ID 서버 :8000/space 로 넘겨 주는 파일)로 바꾸는 zip 을 만든다.
대시보드 쪽 CLAUDE.md: 'ROOM SIZE 계산 업데이트 파일은 P&ID 와 같이 이 세션에서 만든다' (2026-10-25).
    python3 spike/pack_roomsize.py --name hotfix117
"""
from __future__ import annotations

import argparse
import datetime as dt
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = """ROOM SIZE 계산 ({name}) — 대시보드 운영 폴더에 넣는 파일

왜 필요한가
  대시보드의 [ROOM SIZE 계산] 메뉴는 대시보드 폴더 안의 apps\\space\\index.html 을 엽니다.
  그 파일은 예전 판(10-22)이라, P&ID 서버에 올린 최신 화면(룸 · Rev · 3D · Scope · 필요 사이즈 PDF · 지우기)이 안 보였습니다.
  이 zip 의 apps\\space\\index.html 은 메뉴를 누르면 P&ID 서버(같은 PC 포트 8000)의 최신 ROOM SIZE 계산 화면을 띄웁니다.

넣는 법
  1. 이 zip 을 대시보드 운영 폴더(dashboard.html 이 있는 폴더)에 그대로 풉니다 — apps\\space\\index.html 하나가 바뀝니다.
  2. 대시보드에서 [ROOM SIZE 계산] 을 다시 누릅니다 (안 바뀌어 보이면 Ctrl+F5).
  · P&ID 서버 꾸러미(PID_dev+ops_{name})가 운영 PID 에 적용돼 있어야 합니다.  P&ID 서버가 꺼져 있으면 화면이 그렇게 말합니다.

예전 자료
  대시보드 서버에 저장해 둔 판넬 프로젝트 · 저장본 · 노트는 첫 화면의 [대시보드 자료 가져오기] 를 한 번 누르면 같은 ID 로 들어옵니다
  (여러 번 눌러도 한 벌).  서버에 저장하지 않고 브라우저에만 있던 작업은 옮겨지지 않으니, 넣기 전에 예전 화면에서 [서버에 저장] 하세요.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    a = ap.parse_args()
    out = ROOT / "out" / f"ROOMSIZE_dashboard_apps_{a.name}_{dt.date.today():%Y-%m-%d}.zip"
    src = ROOT / "dashboard_apps" / "space" / "index.html"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(src, "apps/space/index.html")
        z.writestr("1_먼저읽기_ROOM_SIZE.txt", README.format(name=a.name).replace("\n", "\r\n").encode("utf-8-sig"))
    with zipfile.ZipFile(out) as z:
        assert z.read("apps/space/index.html") == src.read_bytes()
        print(out, out.stat().st_size, "bytes ·", z.namelist())


if __name__ == "__main__":
    main()
