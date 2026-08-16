#!/usr/bin/env python3
"""index.html → dist/artifact.html (Claude Code publish 형 Artifact 용 미리보기)

publish 형 Artifact 는 CSP 로 외부 호스트를 전부 막는다. 그래서 두 가지를 바꾼다.

  1. cdnjs 의 pdf.js 를 **파일 안에 심는다.**
     워커도 `<script>` 로 함께 심어 globalThis.pdfjsWorker 를 미리 채운다.
     이러면 pdf.js 가 Worker 를 새로 띄우지 않고 메인 스레드에서 돈다.
     (blob: 워커가 CSP 에 막힐 수 있어 아예 안 쓴다. 느리지만 확실하다.)

  2. Claude 호출을 막고 **미리 기록해 둔 판독 결과**를 쓴다.
     이 런타임에서는 api.anthropic.com 이 CSP 로 차단되므로 실판독이 불가능하다.
     기록이 없는 도면을 고르면 그 사실을 화면에 그대로 말한다.

배포본(claude.ai Artifact 용)은 index.html 그대로다. 이 파일은 **보여주기용**이다.

사용:
  python3 dev/build_artifact.py --vendor ../pid-instrument-tool/web/vendor
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174"
CDN_XLSX = "https://cdnjs.cloudflare.com/ajax/libs/fflate/0.8.2/umd/index.js"

BANNER = """
<div class="demo-banner">
  <b>미리보기</b> — 이 화면에서 <b>PDF 넣기 · 도면 고르기 · 타일 만들기</b>는 실제로 돕니다.
  판독은 <b>미리 기록해 둔 결과</b>를 보여줍니다. Claude 가 그 자리에서 도면을 읽는 것은
  이 런타임이 외부 호출을 막아 안 됩니다.<br />
  PDF 를 넣고 <b>6쪽 HP Steam (D00P-10LBA10-M05-0001)</b> 과
  <b>38쪽 CCW (D00P-10PGB10-M05-0004)</b> 를 <b>둘 다 골라</b> 판독을 눌러 보세요.
  두 도면이 합쳐져 36행이 나옵니다. 이 두 장만 기록이 준비돼 있습니다.
</div>
"""

BANNER_CSS = """
.demo-banner {
  margin:18px 0 0; padding:12px 14px; font-size:13px; line-height:1.6;
  border:1px solid var(--line-strong); border-left:3px solid var(--accent);
  border-radius:var(--radius-sm); background:var(--accent-soft); color:var(--ink);
}
"""


def fixture_json() -> str:
    """dev/fixture_p6.mjs 를 node 로 평가해 JSON 으로 뽑는다."""
    out = subprocess.run(
        ["node", "--input-type=module", "-e",
         f"import {{fixtureMulti}} from '{ROOT / 'dev/fixture_p6.mjs'}';"
         "process.stdout.write(JSON.stringify(fixtureMulti(4, 4)));"],
        capture_output=True, text=True, env={"PATH": "/opt/node22/bin:/usr/bin:/bin"})
    if out.returncode:
        print(out.stderr, file=sys.stderr)
        raise SystemExit("fixture 평가 실패")
    return out.stdout


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vendor", type=Path, required=True)
    args = ap.parse_args()

    lib = (args.vendor / "pdf.min.js").read_text(encoding="utf-8")
    worker = (args.vendor / "pdf.worker.min.js").read_text(encoding="utf-8")
    xlsx = (ROOT / "dev/vendor/fflate.min.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    # 1. 겉껍데기 제거 — Artifact 가 doctype/html/head/body 를 직접 씌운다.
    html = re.sub(r"^.*?<title>", "<title>", html, flags=re.S)
    html = html.replace("</head>\n<body>\n", "")
    html = re.sub(r"</body>\s*</html>\s*$", "", html)
    html = re.sub(r'<link rel="stylesheet"[^>]*>\n?', "", html)

    # 2. pdf.js 심기. 워커를 먼저 로드해 globalThis.pdfjsWorker 를 채워 두면
    #    pdf.js 가 Worker 를 안 띄우고 메인 스레드에서 돈다.
    html = html.replace(
        f'<script src="{CDN}/pdf.min.js"></script>',
        f"<script>{worker}</script>\n<script>{lib}</script>")
    html = html.replace(f'<script src="{CDN_XLSX}"></script>', f"<script>{xlsx}</script>")
    html = html.replace(
        f"""  pdfjsLib.GlobalWorkerOptions.workerSrc =
    '{CDN}/pdf.worker.min.js';""",
        "  // 워커를 위에서 미리 심어 두었으므로 workerSrc 를 두지 않는다.\n"
        "  pdfjsLib.GlobalWorkerOptions.workerSrc = '';")

    # 3. 미리 기록해 둔 판독 결과 + 미리보기 배너
    html = html.replace("const USE_STUB = false;",
                        f"const USE_STUB = false;\nwindow.__STUB_FIXTURE = {fixture_json()};")
    html = html.replace("</style>", BANNER_CSS + "</style>")
    html = html.replace('<div class="wrap">', f'<div class="wrap">{BANNER}')

    # 4. 이 런타임은 페이지발 다운로드를 막고, 허용 확장자에 xlsx 가 아예 없다.
    #    버튼을 눌러 봐야 조용히 아무 일도 안 일어나므로 미리 그렇게 말해 둔다.
    html = html.replace(
        "    const name = `instrument_list_${stamp()}.xlsx`;",
        "    throw new Error('이 미리보기 화면은 xlsx 를 내려받을 수 없습니다 — 뷰어가 "
        "페이지발 다운로드를 막고 허용 확장자에 xlsx 가 없습니다. "
        "판독한 행은 위 표에 그대로 있고, 실제 파일 저장은 claude.ai Artifact 나 "
        "index.html 을 직접 열었을 때 됩니다.');\n"
        "    const name = `instrument_list_${stamp()}.xlsx`;")

    # 5. 기록에 없는 도면을 고르면 왜 안 되는지 그대로 말한다.
    html = html.replace(
        "    if (hit === undefined) throw new Error(`스텁에 ${label} 가 없습니다`);",
        "    if (hit === undefined) throw new Error("
        "'이 미리보기에는 이 도면의 기록이 없습니다. 6쪽 HP Steam 과 38쪽 CCW 두 장만 "
        "준비돼 있습니다. 다른 도면 판독은 claude.ai Artifact 에서 실제 호출로만 됩니다.');")

    out = ROOT / "dist/artifact.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"[✓] {out}  ({out.stat().st_size / 1048576:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
