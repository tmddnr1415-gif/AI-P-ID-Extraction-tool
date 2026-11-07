"""CLAUDE.md 와 인수인계 파일이 다시 커지지 않게 (hotfix128).

CLAUDE.md 는 Claude Code 가 모든 요청마다 통째로 싣는다.  회차 기록을 여기에 덧붙여
약 960KB 가 됐을 때 세션마다 "Prompt is too long" 으로 멈췄다.  기록은 docs/history/ 에,
현재 상태는 docs/handoff/<세션>.md 에 고쳐 쓴다 (CLAUDE.md §1).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD_MAX = 12_000      # bytes — 한국어 약 4천 자
HANDOFF_MAX = 15_000


def test_claude_md_stays_small():
    size = (ROOT / "CLAUDE.md").stat().st_size
    assert size <= CLAUDE_MD_MAX, (
        f"CLAUDE.md 가 {size:,} bytes 입니다 (상한 {CLAUDE_MD_MAX:,}).  회차 기록은 "
        "docs/history/<세션>_log.md 에, 현재 상태는 docs/handoff/<세션>.md 에 적으세요.")


def test_handoff_files_stay_small():
    for p in sorted((ROOT / "docs" / "handoff").glob("*.md")):
        size = p.stat().st_size
        assert size <= HANDOFF_MAX, (
            f"{p.name} 가 {size:,} bytes 입니다 (상한 {HANDOFF_MAX:,}).  덧붙이지 말고 "
            "'지금 상태' 절을 고쳐 쓰고, 지난 이야기는 docs/history/ 로 옮기세요.")


def test_no_other_auto_loaded_claude_md_is_huge():
    # 하위 폴더의 CLAUDE.md 도 그 폴더 파일을 읽을 때 자동으로 실린다
    for p in ROOT.rglob("CLAUDE.md"):
        if ".git" in p.parts or "history" in p.parts:
            continue
        assert p.stat().st_size <= 30_000, f"{p.relative_to(ROOT)} 가 너무 큽니다"
