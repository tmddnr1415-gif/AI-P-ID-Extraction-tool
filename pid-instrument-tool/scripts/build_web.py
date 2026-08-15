#!/usr/bin/env python3
"""웹 앱을 빌드한다.

1. rules/*.md → web/rules.gen.js
   판독 규칙을 앱에 심는다. 앱에서 고친 내용은 브라우저에 저장되고, 여기서 만든
   값은 "기본값으로 되돌리기"의 기준이 된다.

2. web/*.{html,css,js} + vendor → web/standalone.html
   파일 하나로 합친다. 서버 없이 브라우저로 바로 열 수 있다.
   pdf.js 워커는 file:// 에서 fetch가 막히므로 base64로 심어 blob URL로 올린다.

사용:
  python3 scripts/build_web.py
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
RULES = ["extraction_guide.md", "naming_convention.md", "symbol_legend.md"]


def build_rules() -> Path:
    bundle = {}
    for name in RULES:
        p = ROOT / "rules" / name
        if not p.exists():
            print(f"[!] rules/{name} 없음 — 건너뜁니다", file=sys.stderr)
            continue
        bundle[name] = p.read_text(encoding="utf-8")

    out = WEB / "rules.gen.js"
    out.write_text(
        "/* rules/*.md 에서 자동 생성됩니다. 직접 고치지 마세요.\n"
        f"   생성: scripts/build_web.py · {dt.datetime.now():%Y-%m-%d %H:%M} */\n"
        "const RULES_DEFAULT = " + json.dumps(bundle, ensure_ascii=False, indent=2) + ";\n"
        "if (typeof module !== 'undefined' && module.exports) module.exports = RULES_DEFAULT;\n",
        encoding="utf-8")
    total = sum(len(v) for v in bundle.values())
    print(f"[✓] web/rules.gen.js  ({len(bundle)}개 문서, {total:,}자)")
    return out


def build_standalone() -> Path:
    html = (WEB / "index.html").read_text(encoding="utf-8")

    # pdf.js 워커는 base64로 심는다 (file:// 에서 fetch 불가)
    worker_b64 = base64.b64encode((WEB / "vendor/pdf.worker.min.js").read_bytes()).decode()
    inline_scripts = [f'<script>window.PDF_WORKER_B64="{worker_b64}";</script>']

    order = ["vendor/pdf.min.js", "vendor/fflate.min.js",
             "rules.gen.js", "xlsx.js", "pdfscan.js", "claude.js", "app.js"]
    for rel in order:
        src = (WEB / rel).read_text(encoding="utf-8")
        src = src.replace("</script>", "<\\/script>")
        inline_scripts.append(f"<!-- {rel} -->\n<script>\n{src}\n</script>")
        tag = f'<script src="{rel}"></script>'
        if tag not in html:
            print(f"[!] index.html에서 {tag} 를 찾지 못했습니다.", file=sys.stderr)
            return None
        html = html.replace(tag, "")

    css = (WEB / "styles.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="styles.css" />', f"<style>\n{css}\n</style>")
    html = html.replace("</body>", "\n".join(inline_scripts) + "\n</body>")
    html = re.sub(r"\n{3,}", "\n\n", html)

    banner = (f"<!--\n  P&ID Instrument List — 단일 파일 빌드\n"
              f"  생성: scripts/build_web.py · {dt.datetime.now():%Y-%m-%d %H:%M}\n"
              f"  원본: web/index.html + styles.css + *.js + vendor/\n"
              f"  자동 생성 파일입니다. 고칠 때는 원본을 고치고 다시 빌드하세요.\n-->")
    html = html.replace("<!DOCTYPE html>", "<!DOCTYPE html>\n" + banner, 1)

    out = WEB / "standalone.html"
    out.write_text(html, encoding="utf-8")
    print(f"[✓] web/standalone.html  ({len(html) / 1048576:.1f} MB)")
    print("    브라우저로 바로 열면 됩니다. 서버도 설치도 필요 없습니다.")
    return out


def main() -> int:
    if not WEB.exists():
        print(f"[!] {WEB} 없음", file=sys.stderr)
        return 1
    build_rules()
    return 0 if build_standalone() else 1


if __name__ == "__main__":
    raise SystemExit(main())
