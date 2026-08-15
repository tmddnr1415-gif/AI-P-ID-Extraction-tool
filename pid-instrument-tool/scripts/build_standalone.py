#!/usr/bin/env python3
"""review-ui를 파일 하나짜리 HTML로 합친다.

review-ui/index.html + styles.css + app.js → review-ui/standalone.html

설치도 서버도 없이 브라우저로 바로 열 수 있고, 메일이나 메신저로 그대로 보낼 수
있다. 기능은 원본과 완전히 동일하다 — 이 스크립트가 매번 원본에서 다시 만들기
때문에 따로 손볼 사본이 생기지 않는다.

사용:
  python3 scripts/build_standalone.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UI = ROOT / "review-ui"

BANNER = """<!--
  Instrument List 검토 UI — 단일 파일 빌드
  생성: scripts/build_standalone.py · {when}
  원본: review-ui/index.html + styles.css + app.js
  이 파일은 자동 생성됩니다. 고칠 때는 원본을 고치고 다시 빌드하세요.
-->
"""


def main() -> int:
    html = (UI / "index.html").read_text(encoding="utf-8")
    css = (UI / "styles.css").read_text(encoding="utf-8")
    js = (UI / "app.js").read_text(encoding="utf-8")

    link = '<link rel="stylesheet" href="styles.css" />'
    script = '<script src="app.js"></script>'
    for needle in (link, script):
        if needle not in html:
            print(f"[!] index.html에서 {needle} 를 찾지 못했습니다.", file=sys.stderr)
            return 1

    # </script> 가 문자열 안에 있으면 HTML 파서가 스크립트를 일찍 닫아버린다.
    js = js.replace("</script>", "<\\/script>")

    html = html.replace(link, f"<style>\n{css}\n</style>")
    html = html.replace(script, f"<script>\n{js}\n</script>")
    html = html.replace("<!DOCTYPE html>", "<!DOCTYPE html>\n" + BANNER.format(
        when=f"{dt.datetime.now():%Y-%m-%d %H:%M}"), 1)

    out = UI / "standalone.html"
    out.write_text(html, encoding="utf-8")
    print(f"[✓] {out.relative_to(ROOT)}  ({len(html) / 1024:.0f} KB)")
    print("    브라우저로 바로 열면 됩니다. 서버도 설치도 필요 없습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
