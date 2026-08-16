#!/usr/bin/env python3
"""공유 링크 서버(Cloudflare Worker) 배포본을 만든다.

  web/           → server/public/          브라우저로 내려갈 파일
  Excel 템플릿   → server/src/template.b64.js   서버 안에만 두고 로그인 후에만 내려준다

템플릿을 정적 파일로 두면 비밀번호 없이도 받아갈 수 있으므로 워커 코드에 심는다.

사용:
  python3 scripts/build_server.py
  python3 scripts/build_server.py --template inputs/다른템플릿.xlsx
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SERVER = ROOT / "server"
PUBLIC = SERVER / "public"

# 브라우저로 내려보낼 파일. standalone.html은 서버 모드에서 쓰지 않는다.
ASSETS = ["index.html", "styles.css", "rules.gen.js", "xlsx.js", "pdfscan.js", "claude.js", "app.js",
          "vendor/pdf.min.js", "vendor/pdf.worker.min.js", "vendor/fflate.min.js"]


def find_template(explicit: Path | None) -> Path | None:
    if explicit:
        return explicit if explicit.exists() else None
    candidates = sorted((ROOT / "inputs").glob("*.xlsx"))
    for c in candidates:
        if "Field_Instrument" in c.name:
            return c
    return candidates[0] if candidates else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, help="심을 Excel 템플릿 (기본: inputs/ 에서 자동 선택)")
    args = ap.parse_args()

    # 규칙 번들이 최신인지 먼저 확인
    if not (WEB / "rules.gen.js").exists():
        print("[!] web/rules.gen.js 가 없습니다. 먼저 build_web.py 를 실행하세요.", file=sys.stderr)
        return 1

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    for rel in ASSETS:
        src = WEB / rel
        if not src.exists():
            print(f"[!] {src} 없음", file=sys.stderr)
            return 1
        dst = PUBLIC / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    total = sum(p.stat().st_size for p in PUBLIC.rglob("*") if p.is_file())
    print(f"[✓] server/public/  ({len(ASSETS)}개 파일, {total / 1048576:.1f} MB)")

    tpl = find_template(args.template)
    out = SERVER / "src/template.b64.js"
    out.parent.mkdir(parents=True, exist_ok=True)
    if tpl:
        b64 = base64.b64encode(tpl.read_bytes()).decode()
        out.write_text(
            f"/* {tpl.name} 을 심은 파일입니다. scripts/build_server.py 가 만듭니다.\n"
            f"   생성: {dt.datetime.now():%Y-%m-%d %H:%M} */\n"
            f"export const TEMPLATE_NAME = {json.dumps(tpl.name)};\n"
            f'export const TEMPLATE_B64 = "{b64}";\n',
            encoding="utf-8")
        print(f"[✓] server/src/template.b64.js  ({tpl.name}, {len(b64) / 1024:.0f} KB)")
    else:
        out.write_text('export const TEMPLATE_NAME = "";\nexport const TEMPLATE_B64 = "";\n',
                       encoding="utf-8")
        print("[!] inputs/ 에서 템플릿을 찾지 못했습니다. 사용자가 직접 올려야 합니다.")

    print("\n다음:")
    print("  cd server")
    print("  wrangler secret put ANTHROPIC_API_KEY")
    print("  wrangler secret put APP_PASSWORD")
    print("  wrangler secret put SESSION_SECRET")
    print("  wrangler deploy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
