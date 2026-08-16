#!/usr/bin/env python3
"""로컬에서 index.html 을 확인하기 위한 임시 서버.

index.html 은 pdf.js 를 CDN 에서 가져온다(ensurePdfjs). 개발 컨테이너는 바깥에
닿지 않아 세 CDN 이 모두 시간 초과로 죽는다. 그래서 서빙할 때만 PDFJS_INJECT 자리에
옆에 둔 사본을 심어 CDN 을 아예 건드리지 않게 한다.
**index.html 자체는 건드리지 않는다** — 배포본은 CDN 을 써야 한다.

사용:
  python3 dev/serve_local.py --vendor ../pid-instrument-tool/web/vendor
  → http://localhost:8123/
"""
from __future__ import annotations

import argparse
import http.server
import os
import shutil
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKER = "<!-- PDFJS_INJECT"


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

    def refresh() -> None:
        """요청마다 다시 만든다. 서버를 켜 둔 채 index.html 을 고쳐도 바로 반영된다."""
        # MIN=1 이면 압축본을 대신 서빙한다. 회귀 시험을 압축본에도 그대로 돌린다.
        name = "dist/index.min.html" if os.environ.get("MIN") else "index.html"
        html = (ROOT / name).read_text(encoding="utf-8")
        # 워커를 먼저 실어 globalThis.pdfjsWorker 를 채우면 pdf.js 가 메인 스레드에서
        # 돈다. 배포본(build_artifact.py)이 하는 것과 같은 자리, 같은 방식이다.
        if MARKER not in html:
            raise SystemExit("index.html 에 PDFJS_INJECT 자리가 없다")
        html = html.replace(MARKER, '<script src="pdf.worker.min.js"></script>\n'
                                    '<script src="pdf.min.js"></script>\n' + MARKER, 1)
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
