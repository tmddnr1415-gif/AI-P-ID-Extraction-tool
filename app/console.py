"""hotfix54 — 출력할 수 없는 글자 하나가 서버를 죽이지 않게 한다.

현장(회사 PC): hotfix52 가 서버 출력을 창이 아니라 `logs\\server.log` 로 보냈다.  한국어
Windows 에서 파이썬은 **파일로 돌린** 표준 출력을 로캘 코드페이지(cp949)로 쓰고, cp949 에는
`—` 가 없다.  서버는 켜질 때 감사 결과를 출력하는데(`main._audit_on_start`), 사람이 손으로
더한 행이 있는 DB 에서는 `—` 가 든 한 줄이 더 붙는다 → `UnicodeEncodeError` → 서버가 켜지는
도중에 죽고 서비스가 10초마다 다시 켜고 또 죽었다.  창에 쓸 때(hotfix51 까지)는 Windows 가
글자를 그대로 받아 드러나지 않았다.

막는 것은 둘이다 — 서비스 파일이 `PYTHONUTF8=1` 로 로그를 UTF-8 로 쓰게 하고(글자가 산다),
그래도 다른 길(손으로 띄운 창 · 다른 bat)로 cp949 가 오면 못 쓰는 글자를 `?` 로 바꿔 쓴다
(서버가 산다).  인코딩은 바꾸지 않는다 — 콘솔과 로그가 읽는 방식이 그대로다.
"""
from __future__ import annotations

import sys


def safe_stdio() -> None:
    """표준 출력·오류를 '못 쓰는 글자는 바꿔 쓴다' 로.  여러 번 불러도 같다."""
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            if getattr(stream, "errors", None) == "strict":
                reconfigure(errors="replace")
        except (ValueError, OSError):
            pass
