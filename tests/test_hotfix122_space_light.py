"""hotfix122 — 판넬 화면 10-26 셋째 판(093c451 '가볍게'): 2D 도면을 층으로 나눠 바뀐 것만 다시 그림. 우리 고침은 그대로."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_light_render_is_in_and_our_adaptations_kept():
    s = (ROOT / "app/static/space/index.html").read_text(encoding="utf-8")
    assert "svgLayers(" in s and "let VPC=null" in s and "dragChk(" in s   # 093c451 이 들어왔다
    assert '<script src="/static/space/ref.js"></script>' in s
    assert '<script src="/static/offline.js" data-app="space"></script>' in s
    assert "confirm(" not in s and "prompt(" not in s
    assert "if(!AUTH_TOKEN)" not in s
    assert "await preflight(" in s
