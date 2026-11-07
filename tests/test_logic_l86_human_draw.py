"""L86 — 사람이 Logic 작성 화면에서 처음부터 한 프로젝트를 그리는 흐름 (마우스 · 키보드만).

`spike/ui_human_draw_l86.py` 가 실제 브라우저로 새 프로젝트 → 기호 놓고 끌기 → 표 칸 → 선 → 속성 → 저장 → 새로 고침 → 되읽기 검증 →
시뮬레이션(타이머 · 메모리) → 묶음 · 둘째 장 · FROM/TO 자동완성 · 묶음 시뮬레이션 → 되돌리기 · 복사 → PDF/DXF 까지 L86 · L87 · L88 단계 110가지를 확인한다.
L86 에서 고친 것 — 기호를 옮기면 붙은 선이 따라옴 · 매달린 선 끝 고리 · 장 더하기 뒤 묶음 카드 · 단자가 표 위(0행)로 나가지 않음 — 도 여기서 잡힌다.

브라우저가 있어야 한다 (`pytest -q -m ui`).  `PW_CHROME` 으로 chrome 경로를 줄 수 있다."""
import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.ui
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_human_draws_a_project_end_to_end(tmp_path):
    pytest.importorskip("playwright")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "spike", "ui_human_draw_l86.py"), str(tmp_path / "data"), str(tmp_path / "cap")],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    tail = "\n".join(r.stdout.splitlines()[-40:])
    assert r.returncode == 0, "사람이 그리는 흐름에서 어긋난 것:\n" + tail + "\n" + r.stderr[-2000:]
    assert "실패 0" in tail
