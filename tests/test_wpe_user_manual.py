"""hotfix132 — 사용 설명서(config/user_manual.md — 운영 폴더 업데이트가 싣는 곳) · README · 시작하기.txt 가 실제와 맞는가."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = (ROOT / "config" / "user_manual.md").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")
START = (ROOT / "시작하기.txt").read_text(encoding="utf-8")

# 도움말·README 가 가리키는 절 — 제목을 바꾸면 주소(#…)가 바뀌므로 고정한다
SECTIONS = ["화면별 사용법", "설치와 처음 켜기", "자동 시작", "끄기 · 다시 켜기 · 상태 보기", "자료가 있는 곳", "로그",
            "업데이트", "백업과 복구", "자주 생기는 문제", "용어", "문의"]
SCREENS = ["P&ID 리스트 추출", "LOGIC 검토", "LOGIC 작도", "신호 처리", "시운전", "블록 시험", "판넬 공간확보", "DCS 그래픽",
           "계장 도서검토"]
IN_ZIP = {"apply_to_PID_dev.bat", "apply_to_PID_ops.bat", "rollback_PID_ops.bat"}   # 꾸러미 안에만 있는 단추


def _anchor(title: str) -> str:
    """app/main.py `_anchor` 와 같은 규칙 (설명서 화면의 제목 id)."""
    return re.sub(r"[^\w가-힣-]+", "-", title.strip().lower()).strip("-") or "section"


def test_product_name_and_the_eleven_sections():
    assert MANUAL.startswith("# 계장 설계 도구 사용 설명서")
    heads = re.findall(r"^## (.+)$", MANUAL, re.M)
    assert heads == SECTIONS
    subs = re.findall(r"^### (.+)$", MANUAL, re.M)
    assert subs == SCREENS                                      # 화면 이름 한 벌 그대로


def test_internal_links_point_at_real_sections():
    ids = {_anchor(t) for t in re.findall(r"^#{1,6} (.+)$", MANUAL, re.M)}
    for doc in (MANUAL, README):
        for target in re.findall(r"\]\((?:config/user_manual\.md)?#([^)]+)\)", doc):
            assert target in ids, target


def test_every_bat_the_manual_names_exists():
    named = set(re.findall(r"[\w-]+\.bat", MANUAL + README + START))
    assert {"setup.bat", "run_lan_service.bat", "check_pid_server.bat", "stop_pid_server.bat", "restart_pid_server.bat",
            "backup_pid_data.bat", "install_autostart_lan.bat"} <= named
    missing = [b for b in named - IN_ZIP if not (ROOT / b).is_file()]
    assert not missing, missing
    sys.path.insert(0, str(ROOT / "spike"))
    import pack_delta                                          # 꾸러미 안 단추는 pack_delta 가 싣는 이름이어야 한다
    src = (ROOT / "spike" / "pack_delta.py").read_text(encoding="utf-8")
    assert all(b in src for b in IN_ZIP) and pack_delta.OPS_README


def test_addresses_and_paths_the_manual_names_exist():
    main = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    for ep in ("/version", "/running"):
        assert f'@app.get("{ep}"' in main, ep
    assert '@app.api_route("/help/manual", methods=["GET", "HEAD"]' in main
    for rel in ("docs/offline_setup_windows.md", "config/product.json", "spike/backup_data.py", "docs/release_checklist.md",
                "docs/pid_engine_notes.md"):
        assert (ROOT / rel).is_file(), rel
    assert "schtasks /Query /TN PID_Extract_LAN" in MANUAL
    assert "PID_Extract_LAN" in (ROOT / "install_autostart_lan.bat").read_text(encoding="ascii")
    assert '"integrity": "ok"' in MANUAL                        # 정상 백업의 표시 (backup_data 의 manifest.json)


def test_no_internal_words_for_the_engineer():
    for doc in (MANUAL, START):
        low = doc.lower()
        for w in ("hotfix", "회차", "커밋", "브랜치"):
            assert w not in low, w
        assert not re.search(r"\bVOC\b", doc)                  # 폴더 이름 voc\ 는 괜찮다 — 용어 'VOC' 는 '의견 보내기'


def test_readme_is_short_and_points_to_the_right_places():
    assert len(README.encode("utf-8")) < 12_000
    assert "titleblock-parsing" not in README and "setup.bat" in README and "Python 3.11" in README
    assert "config/user_manual.md" in README and "docs/pid_engine_notes.md" in README
    notes = (ROOT / "docs" / "pid_engine_notes.md").read_text(encoding="utf-8")
    assert "## Description — 기기 축과 라인 축" in notes            # 옛 본문은 지우지 않고 옮겼다
