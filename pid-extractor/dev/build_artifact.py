#!/usr/bin/env python3
"""index.html → 두 가지 배포본.

`--real` (dist/app.html) — **진짜 앱.** pdf.js 만 심고 나머지는 index.html 그대로다.
    스텁이 없다. 고른 도면을 Claude 가 그 자리에서 읽는다. 인터넷 없이도 열리고,
    Claude 호출만 나간다. 브라우저로 바로 열어 API 키를 넣고 쓰거나 사내 서버에 올린다.

기본 (dist/artifact.html) — **UI 미리보기.** Claude Code publish 형 Artifact 용.
    이 런타임은 CSP 로 외부 호스트를 전부 막아 api.anthropic.com 에 닿지 못하고,
    다운로드 허용 확장자에 xlsx 가 아예 없다. 그래서 실판독도 Excel 저장도 구조적으로
    안 된다. 화면 생김새와 흐름만 보여주려고 미리 기록해 둔 판독 결과를 쓴다.

두 경우 모두 pdf.js 워커를 `<script>` 로 먼저 심어 globalThis.pdfjsWorker 를 채운다.
그러면 pdf.js 가 Worker 를 새로 띄우지 않고 메인 스레드에서 돈다 (blob: 워커가 CSP 에
막힐 수 있어 아예 안 쓴다. 느리지만 확실하다).

claude.ai 대화창에 붙일 파일은 **index.html 원본**이다. 거기서만 키 없이 호출이 열린다.

사용:
  python3 dev/build_artifact.py --vendor ../pid-instrument-tool/web/vendor
  python3 dev/build_artifact.py --vendor ../pid-instrument-tool/web/vendor --real
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CDN = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174"

BANNER = """
<div class="demo-banner">
  <b>UI 미리보기입니다 — 여기서는 Claude 가 도면을 읽지 않습니다.</b>
  이 화면은 외부 호출이 CSP 로 막혀 있어 판독은 <b>미리 기록해 둔 6쪽·38쪽 결과</b>를
  되돌려 줍니다. xlsx 저장도 이 뷰어의 허용 확장자에 없어 안 됩니다.<br />
  <b>고른 도면을 Claude 가 실제로 읽게 하려면</b> claude.ai 대화창에
  <code>index.html</code> 을 붙이고 <i>"첨부한 index.html 을 그대로 아티팩트로 만들어 줘.
  코드는 한 글자도 고치지 말고"</i> 라고 하신 뒤 <b>그 아티팩트 안에서</b> 돌리세요.
  거기서는 아무 도면이나 됩니다.
</div>
"""

BANNER_REAL = """
<div class="demo-banner">
  <b>이 화면은 앱 그대로입니다 — 미리 기록해 둔 결과가 하나도 없습니다.</b>
  PDF 넣기 · 58쪽 훑기 · 도면 고르기 · 타일 만들기 · 타일 확대해 보기는 전부 실제로 돕니다.<br />
  다만 <b>판독 버튼</b>은 이 뷰어가 외부 호출을 막아 "Claude 호출이 막혀 있습니다" 로 멈춥니다.
  <b>Excel 저장</b>도 이 뷰어의 허용 확장자에 xlsx 가 없어 안 됩니다. 둘 다 이 런타임의 제약이지
  앱의 문제가 아닙니다.<br />
  <b>끝까지 돌리려면</b> claude.ai 대화창에 <code>index.html</code> 을 붙이고
  <i>"첨부한 index.html 을 그대로 아티팩트로 만들어 줘. 코드는 한 글자도 고치지 말고"</i>
  라고 하신 뒤 <b>그 아티팩트</b>에서 쓰세요. 거기서는 아무 도면이나 읽힙니다.
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


def sub1(html: str, old: str, new: str, what: str) -> str:
    """한 번만, 반드시 바뀌어야 한다. 조용히 지나가면 배포본이 틀린 채로 나간다."""
    if html.count(old) != 1:
        raise SystemExit(f"{what}: {html.count(old)}번 일치 (1번이어야 함)")
    return html.replace(old, new, 1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vendor", type=Path, required=True)
    ap.add_argument("--standalone", action="store_true",
                    help="브라우저로 바로 여는 자립 파일 dist/app.html")
    ap.add_argument("--stub", action="store_true",
                    help="미리 기록해 둔 판독 결과를 심는다 (dist/preview.html)")
    args = ap.parse_args()
    if args.standalone and args.stub:
        raise SystemExit("--standalone 과 --stub 은 같이 못 쓴다")

    lib = (args.vendor / "pdf.min.js").read_text(encoding="utf-8")
    worker = (args.vendor / "pdf.worker.min.js").read_text(encoding="utf-8")
    html = (ROOT / "index.html").read_text(encoding="utf-8")

    # pdf.js 심기. 워커를 먼저 로드해 globalThis.pdfjsWorker 를 채워 두면 pdf.js 가
    # Worker 를 새로 띄우지 않고 메인 스레드에서 돈다. 심어 두면 ensurePdfjs() 가
    # window.pdfjsLib 를 보고 바로 돌아가므로 CDN 을 아예 건드리지 않는다.
    html = sub1(html, "<!-- PDFJS_INJECT",
                f"<script>{worker}</script>\n<script>{lib}</script>\n<!-- PDFJS_INJECT",
                "pdf.js 심기")

    if not args.standalone:
        # 겉껍데기 제거 — Artifact 가 doctype/html/head/body 를 직접 씌운다.
        html = re.sub(r"^.*?<title>", "<title>", html, flags=re.S)
        html = html.replace("</head>\n<body>\n", "")
        html = re.sub(r"</body>\s*</html>\s*$", "", html)
        html = re.sub(r'<link rel="stylesheet"[^>]*>\n?', "", html)

    if not args.stub:
        # 기록 결과로 새는 길을 아예 끊는다. Claude 를 부르거나 실패하거나 둘뿐이다.
        html = sub1(html, "const stubbing = () => USE_STUB || !!window.__STUB_FIXTURE;",
                    "const stubbing = () => false;   // 진짜 앱 — 기록 결과로 새지 않는다.",
                    "스텁 경로 차단")
        html = sub1(html, "</style>", BANNER_CSS + "</style>", "배너 CSS")
        if not args.standalone:
            html = sub1(html, '<div class="wrap">', f'<div class="wrap">{BANNER_REAL}', "배너")
        out = ROOT / ("dist/app.html" if args.standalone else "dist/artifact.html")
    else:
        html = sub1(html, "const USE_STUB = false;",
                    f"const USE_STUB = false;\nwindow.__STUB_FIXTURE = {fixture_json()};",
                    "기록 결과 심기")
        html = sub1(html, "</style>", BANNER_CSS + "</style>", "배너 CSS")
        html = sub1(html, '<div class="wrap">', f'<div class="wrap">{BANNER}', "배너")

        # 이 뷰어는 페이지발 다운로드를 막고 허용 확장자에 xlsx 가 없다.
        # 눌러 봐야 아무 일도 안 일어나므로 미리 그렇게 말해 둔다.
        html = sub1(html, "    const name = `instrument_list_${stamp()}.xlsx`;",
                    "    throw new Error('이 미리보기 화면은 xlsx 를 내려받을 수 없습니다 — "
                    "뷰어가 페이지발 다운로드를 막고 허용 확장자에 xlsx 가 없습니다. "
                    "판독한 행은 위 표에 그대로 있고, 실제 저장은 claude.ai 아티팩트나 "
                    "app.html 을 직접 열었을 때 됩니다.');\n"
                    "    const name = `instrument_list_${stamp()}.xlsx`;", "다운로드 안내")

        html = sub1(html, "    if (hit === undefined) throw new Error(`스텁에 ${label} 가 없습니다`);",
                    "    if (hit === undefined) throw new Error("
                    "'이 미리보기에는 이 도면의 기록이 없습니다 — 6쪽 HP Steam 과 38쪽 CCW "
                    "두 장뿐입니다. 아무 도면이나 실제로 읽히려면 claude.ai 대화창에서 만든 "
                    "아티팩트에서 돌리세요.');", "기록 없음 안내")
        out = ROOT / "dist/preview.html"

    if not args.stub and ("__STUB_FIXTURE =" in html or "USE_STUB = true" in html):
        raise SystemExit("진짜 앱에 기록 결과가 섞였다 — 중단")

    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    kind = "UI 미리보기 (기록 결과)" if args.stub else "진짜 앱 (스텁 없음)"
    print(f"[✓] {out}  ({out.stat().st_size / 1048576:.1f} MB)  — {kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
