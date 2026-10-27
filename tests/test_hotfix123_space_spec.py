"""hotfix123 — 판넬 화면 10-27 판(b8bcef2): 시야 기준 · Equipment List Excel · 간섭 상세 · 스펙 맞추기. 우리 고침은 그대로."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_spec_fit_and_excel_are_in_and_our_adaptations_kept():
    s = (ROOT / "app/static/space/index.html").read_text(encoding="utf-8")
    assert "function xlsxBlob(" in s and "async function xlsxText(" in s     # 6bfd6b6 — Excel 양식 · 출력 · 읽기
    assert 'id="bFix"' in s and 'id="fixdlg"' in s                            # b8bcef2 — 🛠 스펙 맞추기
    assert "svgLayers(" in s and "dragChk(" in s                              # 093c451 그대로
    assert '<script src="/static/space/ref.js"></script>' in s
    assert '<script src="/static/offline.js" data-app="space"></script>' in s
    assert "confirm(" not in s and "prompt(" not in s
    assert "if(!AUTH_TOKEN)" not in s
    assert "await preflight(" in s
