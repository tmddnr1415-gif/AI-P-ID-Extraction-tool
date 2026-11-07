"""hotfix125 — 판넬 화면 10-28 판(0869426): 실 출입문 — 2D · 3D · DXF 표시 · 검토 · 편집 · 자동 배치가 문을 피함. 우리 고침은 그대로."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_room_doors_are_in_and_our_adaptations_kept():
    s = (ROOT / "app/static/space/index.html").read_text(encoding="utf-8")
    assert "function roomDoors(" in s and "function rdSvg(" in s              # d92f636 — 실 출입문
    assert "function aDoorFree(" in s and "function aWithDoors(" in s         # d92f636 — 자동 배치가 문을 피함
    assert "function rdProps(" in s and 'id="rdpDel"' in s                    # 0869426 — 문 클릭 → 속성 고치기
    assert "function xlsxBlob(" in s and 'id="fixdlg"' in s                   # hotfix123 그대로
    assert '<script src="/static/space/ref.js"></script>' in s
    assert '<script src="/static/offline.js" data-app="space"></script>' in s
    assert "confirm(" not in s and "prompt(" not in s
    assert "if(!AUTH_TOKEN)" not in s
    assert "await preflight(" in s
