"""hotfix77 — 핀 메모: 압정 · 작성칸(날짜·작성자·메모 내용) · 핀↔메모 · 두 번 깜박임 · 개정 요약 줄 정리.

사용자: *"PDF에 핀과 같이 메모누르고 핀을 꼽고, 메모 작성칸에 자동으로 날짜, 메모 내용, 누가 작성했는지.
그리고 pdf의 핀을 누르면 메모장의 그 메모내용으로 이동하고 메모장의 메모내용을 누르면 pdf의 핀이 2번 깜박하고
위치로 이동하게"* · *"추가 74, 삭제 후보 106 ~ 빠진 장 2 는 사용자가 읽지 않는 불필요한 정보다 삭제해줘"*.
화면 동작(깜박임 횟수를 불투명도로 센다)은 `spike/ui_audit_pin_ux.py` 가 띄워서 잰다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")


def _fn(name):
    i = JS.index(f"function {name}(")
    return JS[i:JS.index("\n}\n", i) + 2]


def test_pin_is_a_pushpin_whose_needle_is_the_place():
    pp = _fn("pushpin")
    for part in ("pinshadow", "pinneedle", "pincollar", "pinflag", "pinflag-t"):
        assert part in pp
    draw = _fn("drawPins")
    assert "pushpin(NS, x1 * scale, y0 * scale" in draw          # 바늘 끝 = 점 메모의 점 · 영역의 오른쪽 위
    assert "pushpin(NS, rect[2] * scale, rect[1] * scale" in _fn("pinDialog")   # 작성 중에도 같은 압정
    assert "cursor: url(\"data:image/svg+xml" in CSS              # 핀 모드 커서가 압정


def test_blinks_exactly_twice_and_survives_redraw():
    m = re.search(r"#ov g\.pinmark\.flash \{ animation: pinblink ([\d.]+)s [\w-]+ (\d+); \}", CSS)
    assert m and m.group(2) == "2"
    ms = int(re.search(r"const PIN_FLASH_MS = (\d+);", JS).group(1))
    assert ms == round(float(m.group(1)) * 1000 * 2)              # 두 값을 같이 고친다
    draw = _fn("drawPins")
    assert "pinFlashing(p.id)" in draw and "animationDelay = `-${ft}ms`" in draw   # 다시 그려도 이어 깜박임
    assert "S.pinFlash = { id: p.id, at: Date.now() }" in _fn("focusPin")
    assert re.search(r"\.pin-item\.flash \{ animation: pinitemblink [\d.]+s [\w-]+ 2; \}", CSS)


def test_pin_and_memo_find_each_other():
    sel = _fn("selectPin")
    assert "if (!opts.fromDrawing) focusPin(p);" in sel           # 메모 → 도면의 그 자리
    assert 'li.classList.add("flash")' in sel and "L.scrollTo(" in sel   # 압정 → 메모장의 그 메모 (목록만 굴린다)
    assert ".scrollIntoView(" not in sel


def test_write_box_shows_date_author_content():
    dlg = _fn("pinDialog")
    assert "<dt>날짜</dt>" in dlg and "<dt>작성자</dt>" in dlg and "<dt>메모 내용</dt>" in dlg
    assert "whenWords(Date.now() / 1000)" in dlg and "currentAuthor()" in dlg
    assert "askAuthor(" not in dlg                                # 작성칸이 이름을 받는다 — 따로 묻지 않는다
    assert "rememberAuthor(author)" in dlg                        # 한 번 적으면 다음부터 자동


def test_revision_label_says_only_what_was_compared():
    body = _fn("renderRevLabel")
    assert "el.textContent = S.rev.label;" in body
    assert "bits.join" in body and "el.title" in body            # 수는 지우지 않고 마우스를 올리면
