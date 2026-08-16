#!/usr/bin/env python3
"""로컬에서 index.html 을 확인하기 위한 임시 서버.

index.html 은 CLAUDE.md §2 대로 cdnjs 를 쓴다. 개발 컨테이너에서는 cdnjs 에
닿지 않으므로, 서빙할 때만 CDN 주소를 옆에 둔 사본으로 바꿔치기한다.
**index.html 자체는 건드리지 않는다** — 배포본은 스펙대로 cdnjs 를 써야 한다.

사용:
  python3 dev/serve_local.py --vendor ../pid-instrument-tool/web/vendor
  → http://localhost:8123/
"""
from __future__ import annotations

import argparse
import http.server
import shutil
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174"
CDN_XLSX = "https://cdnjs.cloudflare.com/ajax/libs/fflate/0.8.2/umd/index.js"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vendor", type=Path, required=True,
                    help="pdf.min.js / pdf.worker.min.js 가 있는 폴더")
    ap.add_argument("--port", type=int, default=8123)
    args = ap.parse_args()

    out = ROOT / "dev/_local"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("pdf.min.js", "pdf.worker.min.js"):
        src = args.vendor / name
        if not src.exists():
            print(f"[!] {src} 없음")
            return 1
        shutil.copy2(src, out / name)
    shutil.copy2(ROOT / "dev/vendor/fflate.min.js", out / "fflate.min.js")

    def refresh() -> None:
        """요청마다 다시 만든다. 서버를 켜 둔 채 index.html 을 고쳐도 바로 반영된다."""
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        html = html.replace(f"{CDN}/pdf.worker.min.js", "pdf.worker.min.js")
        html = html.replace(f"{CDN}/pdf.min.js", "pdf.min.js")
        html = html.replace(CDN_XLSX, "fflate.min.js")
        (out / "index.html").write_text(html, encoding="utf-8")

    refresh()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(out), **kw)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                refresh()
            super().do_GET()

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def log_message(self, *a):
            pass

    print(f"[✓] http://localhost:{args.port}/   (dev/_local, cdnjs → 로컬 사본)")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", args.port), Handler) as srv:
        srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
